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

from auditmanager.api.schemas.decisions import DecisionEventView, DecisionRecordView
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
from auditmanager.api.security import IssuedCredential, Subject, TokenSigner
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
        # `document_count` is carried, not recomputed: `IngestService.list_projects`
        # returns `ProjectListingRecord`s whose count came out of the same statement that
        # produced the row (`R-10`). Passing it here rather than counting here is what
        # keeps this a single query -- a `len(list_documents(...))` in this comprehension
        # would be one round trip per project and would also be a *second* definition of
        # what a document is.
        #
        # It is never `None` on this path, so `project_body` always emits the field: a
        # project with no documents answers `0`. The `None` default on `ProjectView`
        # remains for `create_project`, which reads no documents and claims no count.
        return tuple(
            ProjectView(
                project_uid=str(r.project_uid),
                name=r.name,
                created_at=r.created_at,
                document_count=r.document_count,
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
        # Required by the frozen schema and simply omitted here, so every call raised a
        # TypeError inside the adapter and answered 500. The record carried it all along.
        sha256=record.sha256,
        page_count=record.page_count,
        published_at=record.published_at,
        media_type=record.media_type,
        display_title=record.display_title,
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

    def list_documents(self, *, project_uid: str) -> Sequence[DocumentVersionView]:
        from auditmanager.shared.identity import ProjectUid

        return tuple(
            _version_view(record)
            for record in self._service.list_documents(ProjectUid.parse(project_uid))
        )

    def list_versions(self, *, document_uid: str) -> Sequence[DocumentVersionView]:
        from auditmanager.shared.identity import DocumentUid

        return tuple(
            _version_view(record)
            for record in self._service.list_versions(DocumentUid.parse(document_uid))
        )


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
    """Starts and reports runs. Starting one does not execute it.

    `D-20`. This adapter used to import ``execute_run`` and call it inside the same
    ``_write(...)`` that created the run, so ``startRun`` answered ``202`` with a
    ``published`` body and every state between was written and overwritten inside one
    uncommitted transaction. A poller made exactly one request; ``PA-01`` criterion 4's UI
    clause had nothing to poll for. See :mod:`auditmanager.runs.carrier` for what replaced
    it and why that is concurrency rather than the distribution the profile defers.

    The ``carrier`` is a constructor argument with no default. A default would make "which
    side of `D-20` is this application on?" a question you answer by reading a signature
    instead of by reading the composition root, and :class:`InlineCarrier` -- the
    pre-`D-20` behaviour -- is a thing a caller must ask for by name.
    """

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
        carrier: Any,
    ) -> None:
        super().__init__(session_factory)
        self._blob_store = blob_store
        self._model_adapter = adapter
        self._provider_config = provider_config
        self._provider_mode = provider_mode
        self._profile = analysis_profile_id
        self._bundle = prompt_bundle_id
        self._carrier = carrier

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
        from auditmanager.runs import start_audit_run

        if provider_mode is not None and provider_mode != self._provider_mode:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=(
                    "the requested provider mode is not the one this deployment is "
                    "configured to provide; a run is never silently given a different one"
                ),
            )

        from auditmanager.runs import RunRepository

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
                # `D-20`. `created -> queued` happens here, in the transaction that
                # *accepts* the run, and not in the worker. Two reasons, and neither is
                # convenience.
                #
                # The contract's guard on this edge is "the input manifest and the
                # AnalysisProfile, PromptBundle and NormsSnapshot references resolve to
                # immutable versioned records" (`state-machines.json`, audit_run guards;
                # PC-01 leaves the NormsSnapshot clause unevaluated, `runs/scope.py`).
                # `start_audit_run` has just resolved exactly those references, three
                # statements ago and in this transaction. Queueing anywhere else would
                # evaluate the guard in one place and take the edge in another.
                #
                # And it is what makes the answer true. A run this method has handed to a
                # carrier is scheduled; saying `created` -- "exists, nothing has scheduled
                # it" -- about a run already sitting in a work queue would be a state that
                # was accurate for the few microseconds before the submit.
                RunRepository().advance(
                    session,
                    run_id=started.run_id,
                    from_state="created",
                    to_state="queued",
                )
            return started

        started = self._write(work)
        # The frozen document renders `startRun` and `getRunStatus` with the same
        # `RunStatus` body, so this must be the whole view and not a receipt. Returning two
        # fields answered 500 *after* the analysis had run and every row was written, which
        # left the caller unable to address what it had just created - the worst shape a
        # failure can take on a write.
        #
        # **Read before submit, and that ordering is the answer, not an implementation
        # detail.** Once the carrier has the job, the run's state is a race between this
        # process's worker and this process's reader: a fast recorded run can be `running`
        # or already `published` by the time the view is built. Reading first makes the
        # `202` say what was *accepted* -- `queued`, every time, for every document and
        # every provider -- instead of reporting how quick the machine happened to be. A
        # body that varies with scheduling is a body no characterization record can pin
        # and no client can reason about.
        view = self._read(lambda session: _run_status_view(session, str(started.run_id)))
        if not started.replayed:
            # A replay submits nothing. The key's original request submitted the work and
            # the run has whatever state it has since reached; re-submitting would hand a
            # second worker a run that is not `queued`, which the compare-and-set in
            # `run_to_terminal` refuses - correctly, and after needlessly occupying a
            # worker. `started.replayed` is the command ledger's own answer to "did this
            # request create anything", so nothing here re-derives it from the state.
            self._carrier.submit(self._job(str(started.run_id)))
        return view

    def _job(self, run_id: str) -> Any:
        """The unit of work a carrier carries: one queued run, to a terminal.

        Built here because this adapter is what holds the store, the model adapter and the
        provider configuration, and closed over rather than passed as arguments so the
        carrier stays a scheduler that knows nothing about runs.
        """
        from auditmanager.runs import run_to_terminal

        def job() -> None:
            run_to_terminal(
                self._sessions,
                run_id,
                blob_store=self._blob_store,
                adapter=self._model_adapter,
                provider_config=self._provider_config,
            )

        return job

    def get_run_status(self, *, run_id: str) -> RunStatusView:
        return self._read(lambda session: _run_status_view(session, run_id))

    def list_runs(self, *, version_uid: str) -> Sequence[RunStatusView]:
        """Every run of one version, each built through ``_run_status_view``.

        The version is proved to exist before the runs are read, so an unknown version is
        ``not_found`` rather than an empty page. ``RunRepository`` owns ``audit_run`` and
        knows nothing about ``document_version``, so the check belongs here, in the one
        place that holds both modules.
        """
        from auditmanager.documents.repository import DocumentRepository
        from auditmanager.runs import RunRepository
        from auditmanager.shared.identity import VersionUid

        def work(session: Session) -> Sequence[RunStatusView]:
            DocumentRepository().get_version(session, VersionUid.parse(version_uid))
            rows = RunRepository().list_for_version(session, version_uid)
            return tuple(
                _run_status_view(session, str(row.run_id)) for row in rows
            )

        return self._read(work)


def _run_status_view(session: Session, run_id: str) -> RunStatusView:
    """The whole frozen `RunStatus`, from the two places that hold it.

    `RunRow` carries the run; the stage rows are behind `RunRepository.stage_results`. The
    first version read `getattr(run, "stages", ())`, which `RunRow` does not have, so
    `RunStatus.stages` was permanently empty and nothing said so - a `getattr` default is a
    silent answer to a question the object cannot answer.
    """
    from auditmanager.findings import diagnostics, published_finding_count
    from auditmanager.runs import RunRepository

    repository = RunRepository()
    run = repository.get(session, run_id)
    stages = repository.stage_results(session, run_id)
    # `D-21`. Read from the `model_call` rows, which are exact, and not from
    # `stage_result.metrics` -- `D-15` measures that pair as a sum over attempts wearing
    # one attempt's provenance, and that ambiguity is not being inherited into a contract.
    cost = repository.cost(session, run_id)
    return RunStatusView(
        run_id=str(run.run_id),
        project_uid=str(run.project_uid),
        version_uid=str(run.version_uid),
        state=run.state,
        provider_mode=run.provider_mode,
        created_at=run.created_at,
        analysis_profile_id=run.analysis_profile_id,
        prompt_bundle_id=run.prompt_bundle_id,
        degradation_set=tuple(run.degradation_set or ()),
        terminal_reason=run.terminal_reason,
        interrupted_reason=run.interrupted_reason,
        # W17VIEW-1: both counts are declared by the frozen `RunStatus`, carried by
        # `RunStatusView` and emitted by `run_status_body` whenever they are not None -
        # and nothing ever set them, so a user read "Published findings: not reported"
        # about a run that had published three. The two reads are deliberately separate
        # functions with separate names (`findings/queries.py` says why): a diagnostic is
        # not a finding and the two counts must not be obtainable from one call.
        published_finding_count=published_finding_count(session, run_id),
        diagnostic_observation_count=len(diagnostics(session, run_id)),
        # All three or none: a run that made no provider call has no cost to report, and
        # a zero would be an answer to a question nothing asked.
        cost_micros=None if cost is None else cost.cost_micros,
        cost_basis=None if cost is None else cost.basis,
        model_call_count=None if cost is None else cost.model_call_count,
        terminal_at=run.terminal_at,
        stages=tuple(
            StageStateView(
                stage_id=stage.stage_id,
                status=stage.status,
                stage_version=stage.stage_version,
                # D4: a stage that failed because the provider was unreachable carried a
                # null error_code, so a *retryable* dependency failure was reported as a
                # non-retryable analysis failure and an operator would not retry a run that
                # failed only because the proxy was down. The code is in the stage's own
                # error object; it was simply not read.
                # The stored key is `code`, not `error_code`. The first version of this
                # line read the latter, so every failed stage still published null - the
                # defect the comment above claims to fix, surviving inside its own repair.
                # Nothing caught it because no test drove a failed stage through the API,
                # which is the same gap that hid the four defects this method was written
                # to close. `test_a_failed_stage_reports_its_code` is that test.
                error_code=(stage.error or {}).get("code"),
                # W17VIEW-1: the stage rows have carried these since the first migration
                # and the reader did not select them. `_SELECT_STAGE_RESULTS` does now.
                started_at=stage.started_at,
                finished_at=stage.finished_at,
            )
            for stage in stages
        ),
    )


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

    def decision_journal(
        self, *, category: str | None = None, verdict: str | None = None
    ) -> Sequence[DecisionRecordView]:
        """The journal, filtered in the query rather than here.

        Unlike ``list_run_findings``, which filters in Python over one run's handful of
        findings, this listing is not scoped by a parent and grows with every decision the
        deployment has ever taken. The predicate goes to PostgreSQL, against the same
        columns the record reports.

        Both arguments are named in the signature rather than swallowed by ``**_``. The
        finding adapter's first version took ``**_`` and dropped its two filters, so a
        filtered request returned everything and looked like it had worked, and
        ``test_every_adapter_accepts_every_parameter_its_port_declares`` exists because of
        it.
        """
        from auditmanager.decisions import decision_journal

        def work(session: Session) -> Sequence[DecisionRecordView]:
            return tuple(
                _record_view(entry)
                for entry in decision_journal(session, category=category, verdict=verdict)
            )

        return self._read(work)


def _record_view(entry: Any) -> DecisionRecordView:
    return DecisionRecordView(
        decision_id=entry.decision_id,
        finding_uid=entry.finding_uid,
        finding_observation_id=entry.finding_observation_id,
        event_type=entry.event_type,
        author_label=entry.author_label,
        recorded_at=entry.recorded_at,
        project_uid=entry.project_uid,
        run_id=entry.run_id,
        category=entry.category,
        finding_text=entry.finding_text,
        current_verdict=entry.current_verdict,
        decision_event_count=entry.decision_event_count,
        verdict=entry.verdict,
        comment=entry.comment,
    )


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


class CredentialAdapter(_SessionHolder):
    """``issueToken``: `W34-DOM`'s user repository on one side, the seam's signer on the other.

    The two halves of the exchange meet here and nowhere else. The repository proves a
    password and never returns credential material; the signer mints a credential for the
    subject it proved and never sees a password. Neither imports the other, and this adapter
    is the only object in the tree that holds both -- which is what keeps "a digest never
    leaves the repository" and "the signing key never leaves the seam" two separate
    sentences that are each true.

    **Why the adapter and not the router mints.** Minting needs the deployment's signing
    key. A router that held one would be a router that reads configuration, and the
    composition root exists so that nothing else does.

    **Authenticating writes, and until `W40-LIMIT` it did not.** This paragraph said *"No
    session row, no last-login column, no attempt counter"*, and the third of those is
    exactly what `R-26`'s second half adds: a refused exchange raises the account's
    consecutive-failure count and, when that count is spent, shuts the account for a
    cooling-off period; a successful one clears both. So :meth:`issue` opens a **write**
    session rather than a read one, and a sentence that described the old behaviour is
    replaced rather than left standing beside the new -- ``OPERATING_CONSTRAINTS.md`` §4.7,
    in the module that holds the credential.

    The first two are still true and are the load-bearing half: **no session row and no
    last-login column.** A credential is a signed statement about a subject, not a row --
    which is why nothing here has to be cleaned up when it expires, and why this surface
    has no logout. What is written is a count of failures, which is not a record of who is
    signed in.

    **Changing a password writes exactly once**, and revoking is the same write. `W39-REVOKE`
    added the two halves that make a credential retractable: ``change_password`` opens a
    write session for one UPDATE that replaces the digest and raises the account's
    ``token_epoch``, and ``epoch_of`` is the read the seam performs on every guarded request
    to find out whether the credential it has just verified is still the generation this
    account accepts. Neither puts a token in the ``access`` boundary or a password in the
    seam: one integer crosses, in each direction, and this adapter is still the only object
    that holds both halves.
    """

    __slots__ = ("_users", "_signer")

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        users: Any,
        signer: TokenSigner,
    ) -> None:
        super().__init__(session_factory)
        #: ``auditmanager.access.ports.UserRepository``. Annotated ``Any`` and imported by
        #: the composition root rather than here, so this module -- which every adapter in
        #: the application is in -- does not import the ``access`` boundary's internals to
        #: name a type it only passes through.
        self._users = users
        self._signer = signer

    def issue(self, *, login: str, password: str) -> IssuedCredential | None:
        """Prove a password and mint, and commit whatever the attempt recorded either way.

        ``_write`` and not ``_read``, and the difference is the whole of `W40-LIMIT`'s
        durability. ``authenticate`` records a refused attempt and clears the record on a
        successful one, and the caller owns the transaction: a read session would discard
        both on the way out, so an attacker would get an unlimited allowance and the log
        would say the brake was applied.

        It commits on a refusal as readily as on a success. That is not an oddity of the
        session helper -- a refusal is precisely the outcome whose evidence has to survive.
        """
        record = self._write(lambda session: self._users.authenticate(session, login, password))
        if record is None:
            # One answer for an unknown login, a wrong password and a login that could not
            # have been stored. The repository already spends a key derivation on all
            # three, so this returns in comparable time as well as with one answer.
            return None
        return self._signer.issue(
            Subject(
                user_uid=str(record.user_uid),
                login=record.login,
                # The epoch as the row has it at this instant, never a constant and never
                # an assumption. A credential minted under a stale epoch is refused by the
                # very next request, which looks exactly like a broken sign-in.
                token_epoch=record.token_epoch,
            )
        )

    def change_password(
        self, *, user_uid: str, current_password: str, new_password: str
    ) -> IssuedCredential | None:
        """Change the password, then mint under the epoch the change produced.

        The order is the property. ``change_password`` returns the record **after** the
        UPDATE, so ``record.token_epoch`` is the new generation and the credential minted
        from it is the only one this account now accepts. Minting before the write, or from
        a record read before it, would hand back a credential that the next request refuses
        -- a password change that appears to sign the caller out, which is indistinguishable
        from a broken one.
        """
        record = self._write(
            lambda session: self._users.change_password(
                session,
                user_uid=user_uid,
                current_password=current_password,
                new_password=new_password,
            )
        )
        if record is None:
            return None
        return self._signer.issue(
            Subject(
                user_uid=str(record.user_uid),
                login=record.login,
                token_epoch=record.token_epoch,
            )
        )

    def epoch_of(self, user_uid: str) -> int | None:
        """The account's current credential generation, for the seam to compare against.

        A read, so no transaction is committed. ``None`` reaches the seam as a refusal: see
        :class:`auditmanager.api.security.CredentialEpochs`.
        """
        return self._read(lambda session: self._users.token_epoch(session, user_uid))
