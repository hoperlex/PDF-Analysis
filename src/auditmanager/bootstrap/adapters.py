"""The six port adapters: frozen API shapes on one side, real modules on the other.

`B6` wrote `build_router` to take six protocols and construct none of them, so this is the
only place that knows both the wire shape and the module that answers it. Each adapter is
thin on purpose - it opens a session, calls one module, maps the result into the view the
frozen schema declares, and does nothing else. A rule that lives here rather than in a
module is a rule the module's own tests cannot reach.

Every adapter takes its session factory rather than building one, so the whole application
shares one engine and the composition root remains the only thing that reads configuration.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.schemas.decisions import DecisionEventView
from auditmanager.api.schemas.documents import DocumentVersionView, ManifestEntryView
from auditmanager.api.schemas.findings import (
    EvidenceView,
    FindingDetailView,
    FindingView,
    ObservationView,
    ProvenanceView,
)
from auditmanager.api.schemas.projects import ProjectView
from auditmanager.api.schemas.runs import RunStatusView, StageStateView
from auditmanager.shared.errors import DomainError, ErrorCode


class _SessionHolder:
    """Opens one session per call and commits on a clean return.

    The modules are written so the *caller* owns the transaction; the API is the outermost
    caller, so ownership stops here.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def _write(self, work: Any) -> Any:
        with self._sessions() as session:
            result = work(session)
            session.commit()
            return result

    def _read(self, work: Any) -> Any:
        with self._sessions() as session:
            return work(session)


def _not_found(what: str) -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=what)


class ProjectAdapter:
    """Projects. ``IngestService`` owns its own sessions, so this adapter opens none.

    The first version of this class wrapped every call in a session and passed it in, which
    raised a TypeError on the real signature and surfaced as a 500. Nothing caught it: the
    composition suite proves the application *builds*, and until the router was driven end to
    end nothing proved it *answers*. That gap is what session `C2` exists for, and it was
    found by driving the router once before dispatching.
    """

    def __init__(self, service: Any) -> None:
        self._service = service

    def create_project(self, *, name: str, idempotency_key: str) -> ProjectView:
        # The key is claimed, not validated and discarded. Until `create_project_under_key`
        # existed, the edge checked the header the frozen document requires and the key
        # stopped there, so a repeat created a second project with a second identity.
        record, _replayed = self._service.create_project_under_key(
            name=name, idempotency_key=idempotency_key
        )
        return ProjectView(
            project_uid=str(record.project_uid),
            name=record.name,
            created_at=record.created_at,
        )

    def list_projects(self) -> Sequence[ProjectView]:
        return tuple(
            ProjectView(
                project_uid=str(r.project_uid), name=r.name, created_at=r.created_at
            )
            for r in self._service.list_projects()
        )


def _version_view(record: Any) -> DocumentVersionView:
    return DocumentVersionView(
        version_uid=str(record.version_uid),
        document_uid=str(record.document_uid),
        project_uid=str(record.project_uid),
        version_ordinal=record.version_ordinal,
        byte_size=record.byte_size,
        page_count=record.page_count,
        published_at=record.published_at,
        media_type=record.media_type,
        input_manifest=tuple(
            ManifestEntryView(
                role=e.role,
                sha256=e.sha256,
                size_bytes=e.size_bytes,
                media_type=e.media_type,
            )
            for e in record.manifest
        ),
    )


class DocumentAdapter:
    """Documents. Like :class:`ProjectAdapter`, the service owns its sessions."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def upload_document(
        self,
        *,
        project_uid: str,
        content: bytes,
        source_filename: str | None = None,
        display_title: str | None = None,
        idempotency_key: str = "",
    ) -> Any:
        """The port declares ``source_filename``; this method called it ``filename``.

        The router passed the declared name, no parameter matched, and it fell into a
        ``**kwargs`` that discarded it - so every upload was stored under a default name and
        nothing said so. A parameter renamed in an adapter is not a rename, it is a deletion
        with a plausible signature.
        """
        from auditmanager.shared.identity import IdempotencyKey, ProjectUid

        name = source_filename or "upload.pdf"
        outcome = self._service.upload_single_pdf(
            project_uid=ProjectUid.parse(project_uid),
            content=content,
            source_filename=name,
            display_title=display_title or name,
            idempotency_key=IdempotencyKey(idempotency_key),
        )
        return _Uploaded(
            _version_view(outcome.version), bool(getattr(outcome, "replayed", False))
        )

    def get_version(self, *, version_uid: str) -> DocumentVersionView:
        from auditmanager.shared.identity import VersionUid

        return _version_view(self._service.get_version(VersionUid.parse(version_uid)))

    def read_content(self, *, version_uid: str) -> bytes:
        from auditmanager.shared.identity import VersionUid

        return self._service.read_source_bytes(VersionUid.parse(version_uid))


class _Uploaded:
    __slots__ = ("_version", "_replayed")

    def __init__(self, version: DocumentVersionView, replayed: bool) -> None:
        self._version, self._replayed = version, replayed

    @property
    def version(self) -> DocumentVersionView:
        return self._version

    @property
    def replayed(self) -> bool:
        return self._replayed


class RunAdapter(_SessionHolder):
    """Starts and reports runs. Execution itself is synchronous in PC-01."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        blob_store: Any,
        adapter: Any,
        provider_config: Any,
        provider_mode: str,
        analysis_profile_id: str,
        prompt_bundle_id: str,
    ) -> None:
        super().__init__(session_factory)
        self._blob_store = blob_store
        self._model_adapter = adapter
        self._provider_config = provider_config
        self._provider_mode = provider_mode
        self._profile = analysis_profile_id
        self._bundle = prompt_bundle_id

    def start_run(
        self,
        *,
        version_uid: str,
        idempotency_key: str,
        provider_mode: str | None = None,
    ) -> Any:
        """A caller-supplied provider mode is refused, never silently overridden.

        The port declares the parameter and this method used to swallow it, always using
        the configured mode instead. That is the right *outcome* and the wrong way to reach
        it: a client asking for `live` against a recorded deployment was told nothing and
        got a recorded run. Silently substituting a mode is the same failure class as
        publishing a recorded run as live, which `B-III` found one level down.
        """
        from auditmanager.runs import execute_run, start_audit_run

        if provider_mode is not None and provider_mode != self._provider_mode:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=(
                    "the requested provider mode is not the one this deployment is "
                    "configured to provide; a run is never silently given a different one"
                ),
            )

        def work(session: Session) -> Any:
            started = start_audit_run(
                session,
                version_uid=version_uid,
                analysis_profile_id=self._profile,
                prompt_bundle_id=self._bundle,
                # The configured mode, never a caller-supplied one. execute_run refuses a
                # run whose declared mode disagrees with the adapter it is given, and the
                # composition root is the one place that knows both - so passing the
                # configured value here means the refusal can only fire on a wiring fault,
                # not on a request.
                provider_mode=self._provider_mode,
                idempotency_key=idempotency_key,
            )
            if not started.replayed:
                execute_run(
                    session,
                    started.run_id,
                    blob_store=self._blob_store,
                    adapter=self._model_adapter,
                    provider_config=self._provider_config,
                )
            return started

        started = self._write(work)
        return _StartedRunView(str(started.run_id), bool(started.replayed))

    def get_run_status(self, *, run_id: str) -> RunStatusView:
        from auditmanager.runs import RunRepository

        def work(session: Session) -> RunStatusView:
            run = RunRepository().get(session, run_id)
            stages = getattr(run, "stages", ()) or ()
            return RunStatusView(
                run_id=str(run.run_id),
                project_uid=str(run.project_uid),
                version_uid=str(run.version_uid),
                state=run.state,
                provider_mode=run.provider_mode,
                created_at=run.created_at,
                analysis_profile_id=getattr(run, "analysis_profile_id", None),
                prompt_bundle_id=getattr(run, "prompt_bundle_id", None),
                degradation_set=tuple(getattr(run, "degradation_set", ()) or ()),
                terminal_reason=getattr(run, "terminal_reason", None),
                interrupted_reason=getattr(run, "interrupted_reason", None),
                terminal_at=getattr(run, "terminal_at", None),
                stages=tuple(
                    StageStateView(
                        stage_id=s.stage_id,
                        status=s.status,
                        error_code=getattr(s, "error_code", None),
                        started_at=getattr(s, "started_at", None),
                        finished_at=getattr(s, "finished_at", None),
                    )
                    for s in stages
                ),
            )

        return self._read(work)


class _StartedRunView:
    __slots__ = ("run_id", "replayed")

    def __init__(self, run_id: str, replayed: bool) -> None:
        self.run_id, self.replayed = run_id, replayed


def _finding_view(row: Any, evidence: Sequence[Any], verdict: Any) -> FindingView:
    return FindingView(
        finding_uid=row.finding_uid,
        project_uid=row.project_uid,
        version_uid=row.version_uid,
        run_id=row.run_id,
        category=row.category,
        current_verdict=getattr(verdict, "current_verdict", "pending"),
        latest_decision_id=getattr(verdict, "latest_decision_id", None),
        decision_recorded_at=getattr(verdict, "decision_recorded_at", None),
        observation=ObservationView(
            finding_observation_id=row.finding_observation_id,
            run_id=row.run_id,
            category=row.category,
            finding_text=row.finding_text,
            recommendation_text=row.recommendation_text,
            evidence=tuple(
                EvidenceView(
                    evidence_ordinal=e.evidence_ordinal,
                    page_number=e.page_number,
                    quote=e.quote,
                    char_start=e.char_start,
                    char_end=e.char_end,
                    block_id=getattr(e, "block_id", None),
                )
                for e in evidence
                if e.finding_observation_id == row.finding_observation_id
            ),
            provenance=ProvenanceView(
                stage_id=row.stage_id,
                analysis_profile_id=row.analysis_profile_id,
                prompt_bundle_id=row.prompt_bundle_id,
                provider_mode=row.provider_mode,
                model_call_id=row.model_call_id,
            ),
        ),
    )


class FindingAdapter(_SessionHolder):
    def list_run_findings(
        self,
        *,
        run_id: str,
        category: str | None = None,
        verdict: str | None = None,
    ) -> Sequence[FindingView]:
        """The published findings of one run, filtered as the contract declares.

        The first version of this method took ``**_`` and swallowed both filters. The
        router read them, validated them against their enums and passed them; the adapter
        dropped them silently, so `?category=explicit_placeholder` returned everything and
        looked like it had worked. A filter that is accepted and ignored is worse than one
        that is refused.

        Filtering here rather than in SQL is deliberate for PC-01: a run publishes a handful
        of findings, the router already paginates the ordered sequence in memory, and pushing
        a predicate into the query would add a second place for the ordering contract to
        drift. If a run ever publishes enough findings for that to matter, this is the line
        to move, and the port signature does not change when it does.
        """
        from auditmanager.decisions import current_verdict
        from auditmanager.findings import published_finding_evidence, published_findings

        def work(session: Session) -> Sequence[FindingView]:
            rows = published_findings(session, run_id)
            evidence = published_finding_evidence(session, run_id)
            views = [
                _finding_view(r, evidence, current_verdict(session, r.finding_uid))
                for r in rows
            ]
            if category is not None:
                views = [v for v in views if v.category == category]
            if verdict is not None:
                views = [v for v in views if v.current_verdict == verdict]
            return tuple(views)

        return self._read(work)

    def get_finding(self, *, finding_uid: str) -> FindingDetailView:
        from auditmanager.decisions import current_verdict, decision_history
        from auditmanager.findings import finding_by_uid, published_finding_evidence

        def work(session: Session) -> FindingDetailView:
            row = finding_by_uid(session, finding_uid)
            if row is None:
                raise _not_found("Finding")
            evidence = published_finding_evidence(session, row.run_id)
            verdict = current_verdict(session, finding_uid)
            history = decision_history(session, finding_uid)
            comments = [e.comment for e in history if e.comment]
            return FindingDetailView(
                finding=_finding_view(row, evidence, verdict),
                latest_comment=comments[-1] if comments else None,
                decision_event_count=len(history),
            )

        return self._read(work)


class DecisionAdapter(_SessionHolder):
    def append_decision(
        self,
        *,
        finding_uid: str,
        finding_observation_id: str,
        event_type: str,
        idempotency_key: str,
        comment: str | None = None,
        **_: Any,
    ) -> Any:
        from auditmanager.decisions import append_decision_under_key, current_verdict

        def work(session: Session) -> Any:
            event, _replayed = append_decision_under_key(
                session,
                finding_uid=finding_uid,
                finding_observation_id=finding_observation_id,
                event_type=event_type,
                idempotency_key=idempotency_key,
                comment=comment,
            )
            verdict = current_verdict(session, finding_uid)
            return _AppendedDecision(_event_view(event), getattr(verdict, "current_verdict", "pending"))

        return self._write(work)

    def decision_history(self, *, finding_uid: str) -> Sequence[DecisionEventView]:
        from auditmanager.decisions import decision_history as history

        return self._read(lambda s: tuple(_event_view(e) for e in history(s, finding_uid)))


def _event_view(event: Any) -> DecisionEventView:
    return DecisionEventView(
        decision_id=event.decision_id,
        finding_uid=event.finding_uid,
        finding_observation_id=event.finding_observation_id,
        event_type=event.event_type,
        author_label=event.author_label,
        recorded_at=event.recorded_at,
        verdict=event.verdict,
        comment=event.comment,
    )


class _AppendedDecision:
    __slots__ = ("_event", "_verdict")

    def __init__(self, event: DecisionEventView, verdict: str) -> None:
        self._event, self._verdict = event, verdict

    @property
    def event(self) -> DecisionEventView:
        return self._event

    @property
    def current_verdict(self) -> str:
        return self._verdict


class CsvExportAdapter(_SessionHolder):
    def export_run_csv(self, *, run_id: str) -> bytes:
        from auditmanager.exports import export_run_csv

        return self._read(lambda s: export_run_csv(s, run_id).content)
