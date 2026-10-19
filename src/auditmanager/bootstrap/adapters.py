"""The port adapters: frozen API shapes on one side, real modules on the other.

`B6` wrote `build_router` to take six protocols and construct none of them. Five more
were added later with a default rather than a required argument -- `credentials` at wave
39, `blocks` at `W45-BLOCKS`, `dashboard` at `W46-SEAL`, `accounts` and `registrations` at
`W49-SEAL-01`, and a release placeholder at `W52-SEAL-01` -- so this file now carries
twelve adapter classes. Each implemented adapter is thin on purpose - it
opens a session, calls one module, maps the result into the view the frozen schema
declares, and does nothing else. A rule that lives here rather than in a module is a rule
the module's own tests cannot reach.

Every adapter takes its session factory rather than building one, so the whole application
shares one engine and the composition root remains the only thing that reads configuration.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, BinaryIO

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.schemas.accounts import AccountView, PersonNamesView
from auditmanager.api.schemas.blocks import (
    PortalBlockIndexView,
    PortalCropContent,
    VersionBlockIndexView,
)
from auditmanager.api.schemas.content import (
    CONTENT_CHUNK_BYTES,
    PDF_MEDIA_TYPE,
    ByteRange,
    StreamedContent,
)
from auditmanager.api.schemas.dashboard import (
    DashboardSummaryView,
    ProjectDocumentCountView,
    RunActivitySpendView,
    RunStateCountView,
    SectionDocumentCountView,
    VerdictCountView,
)
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
from auditmanager.api.schemas.registrations import RegistrationListingView, RegistrationView
from auditmanager.api.schemas.models import (
    ProductVersion, ReleaseEntry, ReleaseList, ReleaseNoteItem,
)
from auditmanager.api.schemas import models
from auditmanager.api.schemas.common import paginate, decode_cursor, encode_cursor
from auditmanager.api.schemas.runs import RunStatusView, StageStateView
from auditmanager.api.security import (
    ROLE_ADMIN,
    ROLE_EXPERT,
    AccountStanding,
    IssuedCredential,
    Subject,
    TokenSigner,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.errors import CONTRACT_VERSION
from auditmanager.shared.identity import JobId
from auditmanager.releases.public import ReleaseRepository


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


def _execution_cursor(raw: str | None) -> str | None:
    if raw is None:
        return None
    parts = decode_cursor(raw)
    if len(parts) != 1:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="cursor", constraint="format")
    return parts[0]


def _queue_cursor(raw: str | None) -> "QueuePosition | None":
    """Decode only coordinates issued by the queue's versioned page format."""
    from auditmanager.execution.public import QueuePosition

    if raw is None:
        return None
    parts = decode_cursor(raw)
    if len(parts) != 5 or parts[0] != "q1":
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="cursor", constraint="format")
    _, rank_text, priority_text, created_text, job_id = parts
    try:
        rank = int(rank_text)
        priority = int(priority_text)
        created_at = datetime.fromisoformat(created_text)
        JobId.parse(job_id)
    except ValueError:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="cursor", constraint="format",
        ) from None
    if (
        rank not in range(5) or str(rank) != rank_text
        or priority not in range(-100, 101) or str(priority) != priority_text
        or created_at.tzinfo is None
        or created_at.astimezone(timezone.utc).isoformat() != created_text
    ):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="cursor", constraint="format")
    return QueuePosition(rank, priority, created_at, job_id)


class ExecutionAdapter(_SessionHolder):
    """Map the sealed execution port to the owning run/job commands and read projection."""

    def __init__(self, session_factory: sessionmaker[Session], *, runs: "RunAdapter") -> None:
        super().__init__(session_factory)
        self._runs = runs

    @staticmethod
    def _roles(session: Session, user_uid: str) -> frozenset[str]:
        from auditmanager.access.public import AccountRepository

        return AccountRepository().roles_of(session, user_uid)

    def list_queue(self, *, cursor: str | None, limit: int) -> models.ExecutionQueuePage:
        from auditmanager.execution.public import ExecutionRepository

        def read(session: Session) -> models.ExecutionQueuePage:
            repo = ExecutionRepository()
            after = _queue_cursor(cursor)
            rows = repo.list_queue(session, cursor=after, limit=limit + 1)
            items = rows[:limit]
            if len(rows) > limit:
                position = items[-1].position
                next_cursor = encode_cursor((
                    "q1", str(position.rank), str(position.priority),
                    position.created_at.astimezone(timezone.utc).isoformat(),
                    position.job_id,
                ))
            else:
                next_cursor = None
            return models.ExecutionQueuePage(
                items=[models.ExecutionQueueItem(**{
                    "job_id": row.job_id, "run_id": row.run_id, "state": row.state,
                    "priority": row.priority, "created_at": row.created_at,
                    "available_at": row.available_at,
                }) for row in items],
                page=models.PageInfo(next_cursor=next_cursor),
                paused=repo.dispatch_status(session).paused,
            )
        return self._read(read)

    def list_journal(
        self, *, run_id: str | None, cursor: str | None, limit: int
    ) -> models.ExecutionJournalPage:
        from auditmanager.execution.public import ExecutionRepository

        def read(session: Session) -> models.ExecutionJournalPage:
            after = _execution_cursor(cursor)
            rows = ExecutionRepository().list_journal(
                session, run_id=run_id, cursor=after, limit=limit + 1,
            )
            items = rows[:limit]
            next_cursor = encode_cursor((items[-1].event_id,)) if len(rows) > limit else None
            return models.ExecutionJournalPage(
                items=[models.ExecutionJournalEntry(**{
                    "event_id": row.event_id, "run_id": row.run_id,
                    "aggregate_type": row.aggregate_type,
                    "aggregate_id": row.aggregate_id,
                    "event_type": row.event_type,
                    "occurred_at": row.occurred_at,
                    "payload": dict(row.payload),
                }) for row in items],
                page=models.PageInfo(next_cursor=next_cursor),
            )
        return self._read(read)

    def cancel_run(self, *, run_id: str, user_uid: str, idempotency_key: str) -> RunStatusView:
        from auditmanager.runs.commands import cancel_audit_run

        def write(session: Session) -> RunStatusView:
            cancel_audit_run(session, run_id=run_id, roles=self._roles(session, user_uid),
                             idempotency_key=idempotency_key)
            return _run_status_view(session, run_id)
        return self._write(write)

    def reaudit_run(self, *, run_id: str, user_uid: str, idempotency_key: str) -> RunStatusView:
        from auditmanager.runs.commands import reaudit_run

        profile, bundle, mode = self._runs.current_configuration()
        budget = self._runs.input_budget_characters
        # `W59-SECTION-SEAL-01`: a routed deployment routes the re-audit from the version's
        # persisted classification now; the configured AR pair is then not passed at all.
        routes = self._runs.section_profiles
        explicit: dict[str, Any] = (
            {"analysis_profile_id": profile, "prompt_bundle_id": bundle}
            if routes is None
            else {"section_profiles": routes}
        )

        def write(session: Session) -> tuple[str, bool, RunStatusView]:
            # `R-82`: the new run records the configuration this deployment executes,
            # exactly as `startRun` does, never the source run's. The command reads the
            # current norms snapshot in this same transaction (`W55A-PIN-01`). The analysis
            # input budget is part of that configuration (`W55B-BUDGET-01`, R-118): the
            # version is checked against the budget in force now, and the budget is always
            # passed -- the one served path that reaches `reaudit_run` never omits it.
            result = reaudit_run(session, source_run_id=run_id,
                                 roles=self._roles(session, user_uid),
                                 idempotency_key=idempotency_key,
                                 provider_mode=mode, input_budget_characters=budget,
                                 **explicit)
            return result.run_id, result.replayed, _run_status_view(session, result.run_id)
        new_id, replayed, view = self._write(write)
        if not replayed:
            self._runs.submit_existing(new_id)
        return view

    def set_job_priority(
        self, *, job_id: str, priority: int, user_uid: str, idempotency_key: str
    ) -> models.ExecutionQueueItem:
        from auditmanager.jobs.public import set_job_priority
        from auditmanager.execution.public import ExecutionRepository

        def write(session: Session) -> models.ExecutionQueueItem:
            set_job_priority(session, job_id=job_id, priority=priority,
                             roles=self._roles(session, user_uid),
                             idempotency_key=idempotency_key)
            row = ExecutionRepository().get_queue_item(session, job_id)
            if row is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Job")
            return models.ExecutionQueueItem(**{
                "job_id": row.job_id, "run_id": row.run_id, "state": row.state,
                "priority": row.priority, "created_at": row.created_at,
                "available_at": row.available_at,
            })
        return self._write(write)

    def set_paused(self, *, paused: bool, user_uid: str, idempotency_key: str) -> models.ExecutionDispatchStatus:
        from auditmanager.jobs.public import set_execution_paused
        from auditmanager.execution.public import ExecutionRepository

        def write(session: Session) -> models.ExecutionDispatchStatus:
            set_execution_paused(session, paused=paused, roles=self._roles(session, user_uid),
                                 idempotency_key=idempotency_key, actor_uid=user_uid)
            state = ExecutionRepository().dispatch_status(session)
            return models.ExecutionDispatchStatus(paused=state.paused,
                                                  changed_at=state.changed_at)
        return self._write(write)

    # `W54-WORKER-01` (R-105, R-80). The worker registry behind `listWorkers` and
    # `setWorkerIntake`, which `W54-SEAL-01` sealed as stubs. Reads are any role; the
    # intake switch is an administrator's, checked again by the command itself.
    def list_workers(self, *, cursor: str | None, limit: int) -> models.ExecutionWorkerPage:
        from auditmanager.jobs.public import JobRepository
        from auditmanager.workers.public import WorkerRegistry

        def read(session: Session) -> models.ExecutionWorkerPage:
            rows = WorkerRegistry().page(
                session, cursor=_worker_cursor(cursor), limit=limit + 1,
            )
            items = rows[:limit]
            held = JobRepository().runs_held_by(session, [row.worker_id for row in items])
            next_cursor = None
            if len(rows) > limit:
                last = items[-1]
                next_cursor = encode_cursor((
                    "w1", last.started_at.astimezone(timezone.utc).isoformat(),
                    last.worker_id,
                ))
            return models.ExecutionWorkerPage(
                items=[_worker_view(row, held.get(row.worker_id, ())) for row in items],
                page=models.PageInfo(next_cursor=next_cursor),
            )
        return self._read(read)

    def set_worker_intake(
        self, *, worker_id: str, enabled: bool, user_uid: str, idempotency_key: str
    ) -> models.ExecutionWorker:
        from auditmanager.jobs.public import JobRepository
        from auditmanager.workers.public import set_worker_intake

        def write(session: Session) -> models.ExecutionWorker:
            record = set_worker_intake(
                session, worker_id=worker_id, enabled=enabled,
                roles=self._roles(session, user_uid),
                idempotency_key=idempotency_key, actor_uid=user_uid,
            )
            held = JobRepository().runs_held_by(session, [record.worker_id])
            return _worker_view(record, held.get(record.worker_id, ()))
        return self._write(write)


def _worker_cursor(raw: str | None) -> Any:
    """Decode only coordinates issued by the worker page's versioned format.

    Returns a ``workers`` ``WorkerCursor`` or ``None``; imported here, at the one use,
    like every other boundary this module adapts.
    """
    from auditmanager.shared.identity import WorkerId
    from auditmanager.workers.public import WorkerCursor

    if raw is None:
        return None
    parts = decode_cursor(raw)
    if len(parts) != 3 or parts[0] != "w1":
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="cursor", constraint="format")
    _, started_text, worker_id = parts
    try:
        started_at = datetime.fromisoformat(started_text)
        WorkerId.parse(worker_id)
    except ValueError:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="cursor", constraint="format",
        ) from None
    if (started_at.tzinfo is None
            or started_at.astimezone(timezone.utc).isoformat() != started_text):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="cursor", constraint="format")
    return WorkerCursor(started_at=started_at, worker_id=worker_id)


def _worker_view(record: Any, run_ids: Sequence[str]) -> models.ExecutionWorker:
    return models.ExecutionWorker(**{
        "worker_id": record.worker_id,
        "state": record.state,
        "intake_enabled": record.intake_enabled,
        "slots": record.slots,
        "version": record.version,
        "started_at": record.started_at,
        "heartbeat_at": record.heartbeat_at,
        "current_run_ids": list(run_ids),
    })


class ReleasesAdapter:
    """Transport views over the release context's immutable history and account mark."""

    def __init__(
        self, repository: ReleaseRepository, *, product_version: str, build_id: str
    ) -> None:
        self._repository = repository
        self._product_version = product_version
        self._build_id = build_id

    def get_product_version(self) -> ProductVersion:
        return ProductVersion(
            product_version=self._product_version,
            build_id=self._build_id,
            contract_version=CONTRACT_VERSION,
        )

    def list_releases(self, *, user_uid: str) -> ReleaseList:
        listing = self._repository.list_for_account(user_uid)
        return ReleaseList(
            items=[
                ReleaseEntry(
                    version=item.version,
                    revision=item.revision,
                    date=item.released_on.isoformat(),
                    title=item.title,
                    is_archive=item.is_archive,
                    range_label=item.range_label,
                    items=[ReleaseNoteItem(**note_item) for note_item in item.items],
                )
                for item in listing.items
            ],
            whats_new=list(listing.whats_new),
        )

    def mark_read(self, *, user_uid: str, read_through: str) -> None:
        self._repository.mark_read(user_uid=user_uid, read_through=read_through)


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
        section=record.section,
        classification=_classification_view(record.classification),
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


def _classification_view(record: Any) -> models.VersionClassification | None:
    """`W59-SECTION-SEAL-01`. The persisted classification in the frozen shape, or ``None``."""
    if record is None:
        return None
    return models.VersionClassification(
        version_uid=str(record.version_uid),
        project_stage=models.ProjectStage(record.project_stage),
        section_code=models.ProjectSection(record.section_code),
        confirmed_by_user_uid=record.confirmed_by_user_uid,
        confirmed_at=record.confirmed_at,
    )


class SectionAdapter(_SessionHolder):
    """`W59-SECTION-SEAL-01`. A version's classification and its fifteen-choice review.

    Thin like every adapter here: the command and the review live in
    ``auditmanager.sections``; this opens the session, reads the actor's role set inside it,
    reads the recognised-text evidence from the store **outside** it, and maps the result
    into the frozen shapes. ``executable_sections`` is the registry's sealed set, the same
    one run start routes through, so ``executable`` cannot disagree with what a run does.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        blob_store: Any,
        executable_sections: frozenset[str],
    ) -> None:
        super().__init__(session_factory)
        self._blob_store = blob_store
        self._executable = frozenset(executable_sections)

    def classify_version(
        self,
        *,
        project_uid: str,
        document_uid: str,
        version_uid: str,
        project_stage: str,
        section_code: str,
        user_uid: str,
    ) -> models.VersionClassification:
        from auditmanager.access.public import AccountRepository
        from auditmanager.sections.public import classify_document_version

        def work(session: Session) -> models.VersionClassification:
            stored = classify_document_version(
                session,
                project_uid=project_uid,
                document_uid=document_uid,
                version_uid=version_uid,
                project_stage=project_stage,
                section_code=section_code,
                actor_uid=user_uid,
                # Read in this transaction (the decision's authorization rule): the request
                # register checked the role before the route; this is the command's own check.
                actor_roles=AccountRepository().roles_of(session, user_uid),
            )
            view = _classification_view(stored)
            assert view is not None
            return view

        return self._write(work)

    def get_section_review(
        self, *, project_uid: str, document_uid: str, version_uid: str
    ) -> models.SectionReview:
        from auditmanager.sections.public import build_section_review, read_section_review

        facts = self._read(
            lambda session: read_section_review(
                session,
                project_uid=project_uid,
                document_uid=document_uid,
                version_uid=version_uid,
            )
        )
        text = None if facts.markdown is None else self._recognised_text(facts.markdown)
        packet = build_section_review(facts, recognised_text=text)
        return models.SectionReview(
            version_uid=packet.version_uid,
            classification=_classification_view(facts.classification),
            recognised_text_consulted=text is not None,
            options=[
                models.SectionReviewOption(
                    section_code=models.ProjectSection(option.code),
                    name=option.name,
                    executable=option.code in self._executable,
                    suggestion=(
                        None
                        if option.suggestion is None
                        else models.SectionSuggestion(
                            score=option.suggestion.score,
                            filename_patterns=list(option.suggestion.filename_patterns),
                            text_keywords=list(option.suggestion.text_keywords),
                            name_in_text=option.suggestion.name_in_text,
                        )
                    ),
                )
                for option in packet.options
            ],
        )

    def _recognised_text(self, entry: Any) -> str:
        """The markdown member's text, held to the manifest's SHA-256 and size."""
        from auditmanager.ingest import domain_error_from_storage
        from auditmanager.storage.public import BlobNotFoundError, StorageError

        try:
            chunks = self._blob_store.open_stream(
                entry.blob_id, expected_sha256=entry.sha256, expected_size=entry.size_bytes
            )
            try:
                payload = b"".join(chunks)
            finally:
                close = getattr(chunks, "close", None)
                if close is not None:
                    close()
        except BlobNotFoundError:
            raise DomainError(
                ErrorCode.STORAGE_INTEGRITY_ERROR,
                blob_id=str(entry.blob_id),
                role=entry.role,
                expected_sha256=entry.sha256,
            ) from None
        except StorageError as exc:
            raise domain_error_from_storage(exc, blob_id=str(entry.blob_id), role=entry.role) from None
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            raise DomainError(
                ErrorCode.STORAGE_INTEGRITY_ERROR, blob_id=str(entry.blob_id), role=entry.role
            ) from None


class DocumentAdapter:
    """Documents. Like :class:`ProjectAdapter`, the service owns its sessions."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def upload_document(
        self,
        *,
        project_uid: str,
        content: BinaryIO,
        source_filename: str | None = None,
        display_title: str | None = None,
        idempotency_key: str = "",
        section: str | None = None,
    ) -> Any:
        """The port declares ``source_filename``; this method called it ``filename``.

        The router passed the declared name, no parameter matched, and it fell into a
        ``**kwargs`` that discarded it - so every upload was stored under a default name and
        nothing said so. A parameter renamed in an adapter is not a rename, it is a deletion
        with a plausible signature.
        """
        from auditmanager.shared.identity import IdempotencyKey, ProjectUid

        name = source_filename or "upload.zip"
        # `W55B-STREAM-01`: the part's file handle goes through to the service. The envelope
        # measures and hashes it chunk by chunk and the store streams it to the temporary
        # object, so nothing on this path holds the upload whole.
        #
        # `W55B-INGEST-01` (R-116): an upload is a portal bundle -- a ZIP, recognised by its
        # magic bytes whatever label the browser sent. Every upload goes to the bundle entry,
        # which refuses anything that is not a ZIP (a bare PDF included) with
        # `portal_bundle_required`; this adapter reads no byte of it. A missing title is left
        # to the service, which takes the PDF member's name.
        outcome = self._service.upload_bundle(
            project_uid=ProjectUid.parse(project_uid),
            content=content,
            source_filename=name,
            display_title=display_title,
            idempotency_key=IdempotencyKey(idempotency_key),
            section=section,
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

    def stream_content(
        self, *, version_uid: str, byte_range: ByteRange | None
    ) -> StreamedContent:
        """`W55A-CONTENT-01` (plan section A3.5, ``R-115``): the chunked, ranged read.

        The order -- version, range against the manifest's size, object opened -- and
        the integrity rule are :meth:`IngestService.open_source_stream`'s. The media
        type is the one the operation has always answered with (records 14 and 15).
        """
        from auditmanager.shared.identity import VersionUid

        opened = self._service.open_source_stream(
            VersionUid.parse(version_uid),
            resolve_window=None if byte_range is None else byte_range.resolve,
            chunk_size=CONTENT_CHUNK_BYTES,
        )
        return StreamedContent(
            media_type=PDF_MEDIA_TYPE,
            total_size=opened.total_size,
            window=opened.window,
            chunks=opened.chunks,
        )

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
        input_budget_characters: int | None = None,
        section_profiles: Mapping[str, tuple[str, str]] | None = None,
        text_profiles: Any = None,
    ) -> None:
        super().__init__(session_factory)
        # `W59-SECTION-SEAL-01`. The sealed section -> (profile, bundle) table run start and
        # re-audit route through, and the registry resolver the executor runs a run's pinned
        # profile with. The composition root always passes both
        # (``test_the_served_application_routes_by_section``); ``None`` keeps the many tests
        # that build a bare adapter on the explicit configured pair.
        self._section_profiles = section_profiles
        self._text_profiles = text_profiles
        self._blob_store = blob_store
        self._model_adapter = adapter
        self._provider_config = provider_config
        self._provider_mode = provider_mode
        self._profile = analysis_profile_id
        self._bundle = prompt_bundle_id
        self._carrier = carrier
        # `W55B-BUDGET-01`. The analysis input budget, derived once at start-up
        # (``AppSettings.input_budget_characters``) and handed to ``start_audit_run`` and,
        # through ``ExecutionAdapter``, to ``reaudit_run``. ``None`` means "no configuration"
        # and exists so the many tests that build a bare adapter stay as they are; the
        # composition root always passes a positive integer, and
        # ``test_the_served_application_always_passes_a_budget`` is red for any path that
        # does not.
        self._input_budget_characters = input_budget_characters

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

        # `W59-SECTION-SEAL-01`: routed from the version's persisted classification when the
        # deployment has a section table; the configured pair is then not passed at all.
        profile_source: dict[str, Any] = (
            {"analysis_profile_id": self._profile, "prompt_bundle_id": self._bundle}
            if self._section_profiles is None
            else {"section_profiles": self._section_profiles}
        )

        def work(session: Session) -> Any:
            started = start_audit_run(
                session,
                version_uid=version_uid,
                **profile_source,
                # The configured mode, never a caller-supplied one. execute_run refuses a
                # run whose declared mode disagrees with the adapter it is given, and the
                # composition root is the one place that knows both - so passing the
                # configured value here means the refusal can only fire on a wiring fault,
                # not on a request.
                provider_mode=self._provider_mode,
                idempotency_key=idempotency_key,
                input_budget_characters=self._input_budget_characters,
            )
            if not started.replayed:
                # `D-20`. `created -> queued` happens here, in the transaction that
                # *accepts* the run, and not in the worker. Two reasons, and neither is
                # convenience.
                #
                # The contract's guard on this edge is "the input manifest and the
                # AnalysisProfile, PromptBundle and NormsSnapshot references resolve to
                # immutable versioned records" (`state-machines.json`, audit_run guards;
                # a NULL NormsSnapshot pin is admitted until W57, `runs/scope.py`).
                # `start_audit_run` has just resolved exactly those references and read
                # the current norms snapshot (`W55A-PIN-01`), in this transaction.
                # Queueing anywhere else would evaluate the guard in one place and take
                # the edge in another.
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
                # Job creation shares the command transaction. A process dying after
                # the 202 leaves a claimable row, not an in-memory-only submission.
                from auditmanager.jobs.public import JobRepository

                JobRepository().enqueue(session, run_id=started.run_id)
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
                text_profiles=self._text_profiles,
            )

        return job

    @property
    def input_budget_characters(self) -> int | None:
        """The analysis input budget a new run is checked against (`W55B-BUDGET-01`).

        The same value ``start_run`` passes, read by ``ExecutionAdapter.reaudit_run`` so a
        re-audit faces exactly the budget a start does -- today's, not the source run's.
        """
        return self._input_budget_characters

    @property
    def section_profiles(self) -> Mapping[str, tuple[str, str]] | None:
        """The sealed section route table, or ``None`` for an unrouted test wiring."""
        return self._section_profiles

    @property
    def text_profiles(self) -> Any:
        """The registry resolver the executor runs a pinned profile with, or ``None``."""
        return self._text_profiles

    def current_configuration(self) -> tuple[str, str, str]:
        """The analysis profile, prompt bundle and provider mode a new run receives.

        `R-82`. The same three values ``start_run`` stamps, read from the same fields, so
        a re-audit can only ever record the configuration this deployment executes.
        """
        return self._profile, self._bundle, self._provider_mode

    def submit_existing(self, run_id: str) -> None:
        """Wake execution for a durable re-audit accepted in another command."""
        self._carrier.submit(self._job(run_id))

    def get_run_status(self, *, run_id: str) -> RunStatusView:
        return self._read(lambda session: _run_status_view(session, run_id))

    def get_norm_verification(self, *, run_id: str) -> models.NormVerificationReport:
        """Refuse until a reader proves the 0023 partition and the pinned set.

        An empty citation SELECT is not a certificate of zero. CITE will replace this
        seam after it checks stage success and every canonical/member partition.
        """
        raise DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            dependency="norm_verification_reader",
        )

    def run_exists(self, *, run_id: str) -> bool:
        """`D-74`. One row of ``audit_run``, and nothing else.

        ``RunRepository.find`` is the repository's own narrow read -- the same
        ``_SELECT_RUN`` its ``get`` uses, without the refusal -- so this adds no query to
        the tree and reads no stage result and no model call. ``get_run_status`` reads all
        three, which is what made proving a parent exists cost a full parent.
        """
        from auditmanager.runs import RunRepository

        return self._read(
            lambda session: RunRepository().find(session, run_id) is not None
        )

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
        reaudit_of_run_id=run.reaudit_of_run_id,
        # `W55A-PIN-01` (R-113). The snapshot the run pinned at creation, from the row;
        # `run_status_body` renders it only when one was pinned.
        norms_snapshot_id=run.norms_snapshot_id,
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
        # `D-46`. Carried straight through: it was screened when the terminal was chosen
        # and again when the row was written, and `run_status_body` screens it once more
        # before it reaches a client. An adapter that filtered it here would be a fourth
        # place the catalog's rule lives.
        terminal_detail=run.terminal_detail,
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
        decided_severity=getattr(verdict, "decided_severity", None),
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


class BlockAdapter(_SessionHolder):
    """``getVersionBlocks`` (`W45-BLOCKS`), ``listVersionPortalBlocks`` and
    ``streamVersionPortalBlockCrop`` (`W55B-GEOMETRY-01`).

    Reads through ``RunRepository`` rather than through ``auditmanager.analysis`` --
    there is no analysis-side reader for a published artifact, only a writer
    (``publish_artifact`` in ``analysis/ports/artifacts.py``), and this needed the other
    direction. ``stage_result.artifacts`` already carries every ``ArtifactRef`` a stage
    published, so the blob is resolved from that JSON rather than from a second index.

    The portal reads join three artifacts of one run on ``portal_block_id``:
    ``geometry.portal_blocks`` and ``geometry.page_crops`` of its ``page_geometry_extraction``
    and ``prepared.recognised_text`` of its ``source_preparation``. Each is read with the
    SHA-256 and size its ``stage_result`` recorded as the declaration (not the object's own
    metadata), and so is a crop's PNG with the digest its manifest recorded: a blob that is
    missing or differs is ``storage_integrity_error``, never an empty or shorter answer.
    """

    def __init__(self, session_factory: sessionmaker[Session], *, blob_store: Any) -> None:
        super().__init__(session_factory)
        self._blob_store = blob_store

    def get_block_index(self, *, version_uid: str) -> VersionBlockIndexView:
        from auditmanager.analysis.ports.artifacts import ROLE_BLOCK_INDEX
        from auditmanager.api.schemas.blocks import (
            STATUS_NOT_PRODUCED,
            STATUS_PRODUCED,
            BlockGeometryView,
        )
        from auditmanager.documents.repository import DocumentRepository
        from auditmanager.runs import RunRepository
        from auditmanager.shared.identity import VersionUid

        def work(session: Session) -> VersionBlockIndexView:
            # Proves the parent exists before anything else is read, the same rule
            # `RunAdapter.list_runs` follows for the same reason `D-67` states: an
            # unknown version must answer `404`, never the empty-but-present shape below.
            DocumentRepository().get_version(session, VersionUid.parse(version_uid))

            repository = RunRepository()
            for run in repository.list_for_version(session, version_uid):
                stage = next(
                    (
                        s
                        for s in repository.stage_results(session, str(run.run_id))
                        if s.stage_id == "page_geometry_extraction"
                    ),
                    None,
                )
                if stage is None or stage.status != "succeeded":
                    continue
                artifact = next(
                    (a for a in stage.artifacts if a.get("role") == ROLE_BLOCK_INDEX),
                    None,
                )
                if artifact is None:
                    continue
                document = self._read_artifact(artifact)
                return VersionBlockIndexView(
                    version_uid=version_uid,
                    status=STATUS_PRODUCED,
                    produced_by_run_id=str(run.run_id),
                    text_layer_sha256=document.get("text_layer_sha256"),
                    block_count=len(document.get("blocks", ())),
                    blocks=tuple(
                        BlockGeometryView(
                            block_id=b["block_id"],
                            page_number=b["page_number"],
                            block_ordinal=b["block_ordinal"],
                            bbox=b["bbox"],
                            bbox_unit=b["bbox_unit"],
                            bbox_origin=b["bbox_origin"],
                            char_start=b["char_start"],
                            char_end=b["char_end"],
                        )
                        for b in document.get("blocks", ())
                    ),
                )
            # No run of this version ever reached page_geometry_extraction
            # successfully -- absent, never rendered as the same bytes a version with
            # genuinely zero blocks would answer.
            return VersionBlockIndexView(
                version_uid=version_uid,
                status=STATUS_NOT_PRODUCED,
                produced_by_run_id=None,
                text_layer_sha256=None,
                block_count=0,
                blocks=(),
            )

        return self._read(work)

    # `W55B-GEOMETRY-01`. The two portal-block reads, which `W55B-SEAL-01` sealed as
    # stubs answering `503 dependency_unavailable`.

    #: The crop's media type: the wire's ``PortalCrop.media_type`` const and the blob's.
    _PNG_MEDIA_TYPE = "image/png"

    class _PortalSource:
        """The run a version's portal geometry is read from, and the references to join."""

        __slots__ = ("run_id", "portal_blocks", "page_crops", "recognised_text")

        def __init__(
            self,
            *,
            run_id: str,
            portal_blocks: Mapping[str, Any],
            page_crops: Mapping[str, Any] | None,
            recognised_text: Mapping[str, Any] | None,
        ) -> None:
            self.run_id = run_id
            self.portal_blocks = portal_blocks
            self.page_crops = page_crops
            self.recognised_text = recognised_text

    @staticmethod
    def _artifact_reference(
        artifacts: Sequence[Mapping[str, Any]], role: str
    ) -> Mapping[str, Any] | None:
        return next((artifact for artifact in artifacts if artifact.get("role") == role), None)

    @staticmethod
    def _portal_integrity(role: str) -> DomainError:
        """The artifacts one run published disagree with each other or with the record."""
        return DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role=role)

    def _portal_source(self, version_uid: str) -> "BlockAdapter._PortalSource | None":
        """The latest run of the version that produced portal geometry, or ``None``.

        Proves the version exists first (an unknown one is ``not_found``, never the empty
        shape), then walks the version's runs newest first for one whose
        ``page_geometry_extraction`` succeeded **and** published ``geometry.portal_blocks``:
        a run over a version without a bundle succeeds without it and is not portal geometry.
        """
        from auditmanager.analysis.public import (
            ROLE_PAGE_CROPS,
            ROLE_PORTAL_BLOCKS,
            ROLE_RECOGNISED_TEXT,
        )
        from auditmanager.documents.repository import DocumentRepository
        from auditmanager.runs import RunRepository
        from auditmanager.shared.identity import VersionUid

        def work(session: Session) -> BlockAdapter._PortalSource | None:
            DocumentRepository().get_version(session, VersionUid.parse(version_uid))
            repository = RunRepository()
            for run in repository.list_for_version(session, version_uid):
                stages = {
                    stage.stage_id: stage
                    for stage in repository.stage_results(session, str(run.run_id))
                }
                geometry = stages.get("page_geometry_extraction")
                if geometry is None or geometry.status != "succeeded":
                    continue
                portal_blocks = self._artifact_reference(geometry.artifacts, ROLE_PORTAL_BLOCKS)
                if portal_blocks is None:
                    continue
                preparation = stages.get("source_preparation")
                return BlockAdapter._PortalSource(
                    run_id=str(run.run_id),
                    portal_blocks=portal_blocks,
                    page_crops=self._artifact_reference(geometry.artifacts, ROLE_PAGE_CROPS),
                    recognised_text=(
                        None
                        if preparation is None
                        else self._artifact_reference(preparation.artifacts, ROLE_RECOGNISED_TEXT)
                    ),
                )
            return None

        return self._read(work)

    def list_portal_blocks(self, *, version_uid: str) -> PortalBlockIndexView:
        from auditmanager.analysis.public import (
            KIND_PORTAL_DESCRIPTION,
            KIND_RECOGNISED_TEXT,
            ROLE_PAGE_CROPS,
            ROLE_PORTAL_BLOCKS,
            ROLE_RECOGNISED_TEXT,
        )
        from auditmanager.api.schemas.blocks import (
            STATUS_NOT_PRODUCED,
            STATUS_PRODUCED,
            PortalBlockView,
            PortalCropView,
            PortalRecognisedTextView,
        )

        source = self._portal_source(version_uid)
        if source is None:
            # No run of this version produced portal geometry: absent, never rendered as
            # the same answer a produced geometry with no blocks gives.
            return PortalBlockIndexView(version_uid, STATUS_NOT_PRODUCED, None, ())

        blocks = self._portal_document(source.portal_blocks, ROLE_PORTAL_BLOCKS, version_uid)
        crops = self._portal_document(source.page_crops, ROLE_PAGE_CROPS, version_uid)
        recognised = self._portal_document(
            source.recognised_text, ROLE_RECOGNISED_TEXT, version_uid
        )
        identifiers = {block["portal_block_id"] for block in blocks["blocks"]}
        entries = {entry["portal_block_id"]: entry for entry in recognised["entries"]}
        records = {record["portal_block_id"]: record for record in crops["crops"]}
        if not set(entries) <= identifiers:
            raise self._portal_integrity(ROLE_RECOGNISED_TEXT)
        if not set(records) <= identifiers:
            raise self._portal_integrity(ROLE_PAGE_CROPS)

        views: list[PortalBlockView] = []
        for block in blocks["blocks"]:
            identifier = block["portal_block_id"]
            text: PortalRecognisedTextView | None = None
            description: str | None = None
            entry = entries.get(identifier)
            if entry is not None:
                if entry["kind"] == KIND_RECOGNISED_TEXT and block["block_type"] == "text":
                    # The wire's `text` is `minLength: 1`: an empty body is left out.
                    if entry["text"]:
                        text = PortalRecognisedTextView(entry["text"], tuple(entry["flags"]))
                elif entry["kind"] == KIND_PORTAL_DESCRIPTION and block["block_type"] == "image":
                    if entry["text"]:
                        description = entry["text"]
                else:
                    raise self._portal_integrity(ROLE_RECOGNISED_TEXT)
            crop: PortalCropView | None = None
            record = records.get(identifier)
            if record is not None:
                if block["block_type"] != "image" or block["geometry"] != "ok":
                    raise self._portal_integrity(ROLE_PAGE_CROPS)
                crop = PortalCropView(
                    self._PNG_MEDIA_TYPE, record["width_px"], record["height_px"], record["sha256"]
                )
            polygon = block.get("polygon_points")
            views.append(
                PortalBlockView(
                    portal_block_id=identifier,
                    page_number=block["page_number"],
                    page_label=block["page_label"],
                    ordinal=block["ordinal"],
                    block_type=block["block_type"],
                    status=block["status"],
                    bbox_norm=tuple(block["bbox_norm"]),
                    geometry=block["geometry"],
                    polygon_points=(
                        tuple((point[0], point[1]) for point in polygon) if polygon else None
                    ),
                    crop=crop,
                    recognised_text=text,
                    portal_description=description,
                )
            )
        # The artifact is written in the port's order (page, ordinal with a null one last,
        # id) by the stage; it is passed on as written and never re-sorted here.
        return PortalBlockIndexView(version_uid, STATUS_PRODUCED, source.run_id, tuple(views))

    def read_portal_block_crop(
        self, *, version_uid: str, portal_block_id: str
    ) -> PortalCropContent:
        from auditmanager.analysis.public import ROLE_CROP_IMAGE, ROLE_PAGE_CROPS

        source = self._portal_source(version_uid)
        if source is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="PortalBlock")
        crops = self._portal_document(source.page_crops, ROLE_PAGE_CROPS, version_uid)
        record = next(
            (item for item in crops["crops"] if item["portal_block_id"] == portal_block_id),
            None,
        )
        if record is None:
            # Not a block of this version, not an IMAGE block, or on a page marked
            # `geometry_mismatch`: the same fact for the caller, there is no such image.
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="PortalBlock")
        content = self._verified_bytes(
            {
                "role": ROLE_CROP_IMAGE,
                "blob_id": record["blob_id"],
                "sha256": record["sha256"],
                "size_bytes": record["size_bytes"],
            }
        )
        return PortalCropContent(self._PNG_MEDIA_TYPE, record["sha256"], content)

    def _portal_document(
        self, reference: Mapping[str, Any] | None, role: str, version_uid: str
    ) -> dict[str, Any]:
        """One JSON artifact of the join, verified against its recorded digest.

        A reference the run did not record, bytes that are not that artifact of this
        version, or an artifact version this reader does not implement all fail closed.
        """
        import json

        from auditmanager.analysis.public import ARTIFACT_VERSION

        if reference is None:
            raise self._portal_integrity(role)
        try:
            document = json.loads(self._verified_bytes(reference).decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise self._portal_integrity(role) from None
        if not isinstance(document, dict):
            raise self._portal_integrity(role)
        if document.get("artifact_version") != ARTIFACT_VERSION:
            raise DomainError(ErrorCode.UNSUPPORTED_CONTRACT_VERSION)
        if document.get("artifact_role") != role or document.get("version_uid") != version_uid:
            raise self._portal_integrity(role)
        return document

    def _verified_bytes(self, reference: Mapping[str, Any]) -> bytes:
        """The blob's bytes, held to the SHA-256 and size the reference recorded."""
        from auditmanager.ingest import domain_error_from_storage
        from auditmanager.storage.public import BlobNotFoundError, StorageError, parse_blob_id

        blob_id = str(reference["blob_id"])
        role = str(reference["role"])
        # The declaration is the reference's record, never the object's own metadata.
        declared_sha256, declared_size = str(reference["sha256"]), int(reference["size_bytes"])
        try:
            chunks = self._blob_store.open_stream(
                parse_blob_id(blob_id),
                expected_sha256=declared_sha256,
                expected_size=declared_size,
            )
            try:
                return b"".join(chunks)
            finally:
                close = getattr(chunks, "close", None)
                if close is not None:
                    close()
        except BlobNotFoundError:
            raise DomainError(
                ErrorCode.STORAGE_INTEGRITY_ERROR,
                blob_id=blob_id,
                role=role,
                expected_sha256=declared_sha256,
            ) from None
        except StorageError as exc:
            raise domain_error_from_storage(exc, blob_id=blob_id, role=role) from None

    def _read_artifact(self, artifact: Mapping[str, Any]) -> dict[str, Any]:
        import json

        from auditmanager.storage.models import parse_blob_id

        blob_id = parse_blob_id(artifact["blob_id"])
        payload = self._blob_store.read(blob_id, verify=True)
        return json.loads(payload.decode("utf-8"))


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

    def finding_exists(self, *, finding_uid: str) -> bool:
        """`D-74`. The question the decision ledger has always asked, offered to the router.

        ``auditmanager.findings.queries.finding_exists`` is not new: ``record_decision``
        calls it before appending, for the same reason and with the same meaning -- an
        ungrounded observation carries no ``finding_uid`` and is ``False`` here. Using it
        rather than a second query is what keeps "is this a published finding" one
        sentence in one place.
        """
        from auditmanager.findings import finding_exists

        return self._read(lambda session: finding_exists(session, finding_uid))


class DecisionAdapter(_SessionHolder):
    def append_decision(
        self,
        *,
        finding_uid: str,
        finding_observation_id: str,
        event_type: str,
        severity: str | None = None,
        idempotency_key: str,
        author_label: str,
        author_user_uid: str,
        comment: str | None = None,
    ) -> Any:
        """`D-78`. ``author_label`` is named, not swallowed, and has no default.

        The ``**_`` this signature used to end with is the shape
        ``test_every_adapter_accepts_every_parameter_its_port_declares`` exists because of:
        the finding adapter once took one and dropped both its filters, so a filtered
        request returned everything and looked like it had worked. A swallowed author would
        have been worse -- the row would still be written, attributed to whatever the ledger
        defaulted to -- so the argument is named and nothing here supplies a fallback.
        """
        from auditmanager.decisions import append_decision_under_key, current_verdict

        def work(session: Session) -> Any:
            event, _replayed = append_decision_under_key(
                session,
                finding_uid=finding_uid,
                finding_observation_id=finding_observation_id,
                event_type=event_type,
                severity=severity,
                idempotency_key=idempotency_key,
                comment=comment,
                author_label=author_label,
                author_user_uid=author_user_uid,
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
        severity=entry.severity,
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
        severity=event.severity,
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


class DashboardAdapter(_SessionHolder):
    """``getDashboardSummary``. `R-44`. Reads the same session factory as everything
    else here; nothing new is opened for it."""

    def get_summary(self) -> DashboardSummaryView:
        from auditmanager.dashboard import DashboardRepository

        record = self._read(lambda s: DashboardRepository().summary(s))
        return DashboardSummaryView(
            documents_by_project=tuple(
                ProjectDocumentCountView(
                    project_uid=row.project_uid,
                    name=row.name,
                    document_count=row.document_count,
                )
                for row in record.documents_by_project
            ),
            findings_by_verdict=tuple(
                VerdictCountView(verdict=row.verdict, count=row.count)
                for row in record.findings_by_verdict
            ),
            run_activity=tuple(
                RunStateCountView(state=row.state, count=row.count)
                for row in record.run_activity
            ),
            # `F-1`. `record.run_spend` is `None` on a deployment with no `model_call`
            # row at all, and that absence is carried through rather than defaulted --
            # see `DashboardSummaryRecord.run_spend` and `RunActivitySpendView`.
            run_spend=(
                None
                if record.run_spend is None
                else RunActivitySpendView(
                    model_call_count=record.run_spend.model_call_count,
                    cost_micros=record.run_spend.cost_micros,
                    cost_basis=record.run_spend.basis,
                )
            ),
            section_breakdown=tuple(
                SectionDocumentCountView(
                    section=row.section, document_count=row.document_count
                )
                for row in record.section_breakdown
            ),
        )


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
    ``token_epoch``, and ``standing_of`` is the read the seam performs on every guarded
    request to find out whether the credential it has just verified is still the generation
    this account accepts -- and, since `R-50`, whether the account is still on the password
    it was seeded with. Neither puts a token in the ``access`` boundary or a password in the
    seam: two scalars cross one way and an integer the other, and this adapter is still the
    only object that holds both halves.
    """

    __slots__ = ("_users", "_accounts", "_signer")

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        users: Any,
        accounts: Any,
        signer: TokenSigner,
    ) -> None:
        super().__init__(session_factory)
        #: ``auditmanager.access.ports.UserRepository``. Annotated ``Any`` and imported by
        #: the composition root rather than here, so this module -- which every adapter in
        #: the application is in -- does not import the ``access`` boundary's internals to
        #: name a type it only passes through.
        self._users = users
        #: `W49-SEAL-01`. ``auditmanager.access.ports.AccountRepository``: the standing the
        #: seam reads on every guarded request -- epoch, default credential, archive state,
        #: profile completeness, roles, and the row's login and label -- comes from one
        #: statement of the management half, not from the sign-in half's two-column read.
        #: Required, not defaulted: an adapter wired without it could not refuse an archived
        #: or roleless account, and would serve them.
        self._accounts = accounts
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
                # `R-37`. The name other reviewers read, taken from the record and never
                # resolved here: `display_label` is the account's own answer -- the chosen
                # display name, or the login when there is none -- and one fallback in one
                # place is the whole of why it is not a silent one.
                display_label=record.display_label,
            ),
            # `R-50`. The row's own answer, read in the same statement that proved the
            # password, and never a guess about which login the deployment seeded. It goes
            # to the client, which is what lets a screen send this reviewer to the change
            # screen at the moment of signing in instead of after a refusal.
            is_default_credential=record.is_default_credential,
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
                display_label=record.display_label,
            ),
            # `R-50`. Read from the record the UPDATE returned, which is the record *after*
            # the change -- and the change clears the column in the same statement, so this
            # is `false` here by the write's own doing and not by this line assuming it.
            is_default_credential=record.is_default_credential,
        )

    def standing_of(self, user_uid: str) -> AccountStanding | None:
        """The account's standing, for the seam to decide this request against.

        A read, so no transaction is committed. ``None`` reaches the seam as a refusal: see
        :class:`auditmanager.api.security.AccountStandings`.

        **This is where the two vocabularies meet**, and the translation is the point of the
        method rather than an overhead. The ``access`` boundary answers its own
        :class:`~auditmanager.access.models.Account`; the seam is handed its own
        :class:`~auditmanager.api.security.AccountStanding`. Neither module imports the
        other, exactly as for :class:`~auditmanager.api.security.Subject`, and this adapter
        stays the only object in the tree that holds both halves.

        `W49-SEAL-01`. One statement (``get_account``: the account's public columns and its
        role set, joined) answers every field: the epoch and the default credential as
        before, and the archive state, the profile completeness, the roles and the row's
        login and display label. The roles cross by :data:`_SEAM_ROLE_OF`, which refuses a
        value it does not know rather than dropping it -- a role set that silently lost a
        member would be a privilege decision made by a dictionary.
        """
        account = self._read(lambda session: self._accounts.get_account(session, user_uid))
        if account is None:
            return None
        record = account.record
        return AccountStanding(
            token_epoch=record.token_epoch,
            is_default_credential=record.is_default_credential,
            archived=record.archived,
            profile_complete=record.profile_complete,
            roles=frozenset(_seam_role(role) for role in account.roles),
            login=record.login,
            display_label=record.display_label,
        )


#: `W49-SEAL-01`. The ``access`` boundary's role vocabulary to the seam's, written out: the
#: two spell the same words today, and a table rather than an identity is what keeps a new
#: role on one side from reaching the other without a decision.
_SEAM_ROLE_OF: dict[str, str] = {"expert": ROLE_EXPERT, "admin": ROLE_ADMIN}


def _seam_role(role: str) -> str:
    try:
        return _SEAM_ROLE_OF[role]
    except KeyError:
        raise DomainError(
            ErrorCode.INTERNAL_ERROR, message="an account holds a role the seam does not know"
        ) from None


# --------------------------------------------------------------------------------------
# `W49-SEAL-01`: the account and registration ports, over `auditmanager.access`.
# --------------------------------------------------------------------------------------


def _account_view(account: Any) -> AccountView:
    """``auditmanager.access.models.Account`` as the frozen ``Account`` shape."""
    record = account.record
    return AccountView(
        user_uid=str(record.user_uid),
        login=record.login,
        display_label=record.display_label,
        last_name=record.last_name,
        first_name=record.first_name,
        middle_name=record.middle_name,
        roles=tuple(sorted(account.roles)),
        profile_complete=record.profile_complete,
        is_default_credential=record.is_default_credential,
        archived_at=record.archived_at,
    )


def _registration_view(record: Any) -> RegistrationView:
    """``auditmanager.access.registrations.RegistrationRecord`` as ``RegistrationRequest``."""
    return RegistrationView(
        request_id=record.request_id,
        login=record.login,
        display_label=record.display_label,
        last_name=record.last_name,
        first_name=record.first_name,
        middle_name=record.middle_name,
        status=record.status,
        submitted_at=record.submitted_at,
        decided_at=record.decided_at,
        decided_by=record.decided_by,
        rejection_reason=record.rejection_reason,
        created_user_uid=record.created_user_uid,
    )


class AccountAdapter(_SessionHolder):
    """``AccountPort`` over the access boundary's management half.

    Thin in the way every adapter here is: one session, the access method that owns the
    rule, the account read back in the **same** session so the answer is the state the
    change produced, and the view. Every invariant -- no act on oneself, the last
    administrator, a fixed login, a referenced purge -- is raised by
    ``auditmanager.access``; nothing here decides one.
    """

    __slots__ = ("_accounts",)

    def __init__(self, session_factory: sessionmaker[Session], *, accounts: Any) -> None:
        super().__init__(session_factory)
        #: ``auditmanager.access.ports.AccountRepository``; ``Any`` for the reason
        #: ``CredentialAdapter._users`` gives.
        self._accounts = accounts

    def _view_of(self, session: Session, user_uid: str) -> AccountView:
        account = self._accounts.get_account(session, user_uid)
        if account is None:
            raise _not_found("User")
        return _account_view(account)

    def get_account(self, *, user_uid: str) -> AccountView:
        return self._read(lambda session: self._view_of(session, user_uid))

    def list_accounts(self, *, include_archived: bool) -> Sequence[AccountView]:
        return self._read(
            lambda session: tuple(
                _account_view(account)
                for account in self._accounts.list_accounts(
                    session, include_archived=include_archived
                )
            )
        )

    def update_my_profile(
        self,
        *,
        user_uid: str,
        last_name: str,
        first_name: str,
        middle_name: str | None,
        email: str | None,
    ) -> AccountView:
        def work(session: Session) -> AccountView:
            self._accounts.update_my_profile(
                session,
                user_uid=user_uid,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                email=email,
            )
            return self._view_of(session, user_uid)

        return self._write(work)

    def update_account(
        self,
        *,
        actor_uid: str,
        user_uid: str,
        names: PersonNamesView | None,
        roles: frozenset[str] | None,
    ) -> AccountView:
        """Update names and roles in one transaction; a refused role change rolls both back.

        **Roles first**, because ``set_roles`` takes the lock order ``auditmanager.access``
        documents for every change that can remove an administrator -- the active
        administrators, then the target. Writing the names first locked the target before
        the administrator set, the reverse order, so a combined change and a concurrent
        archive of the same account could deadlock (C-08). The names then lock a row this
        transaction already holds. An empty change still answers ``not_found`` for an
        archived or missing account, as either half alone does (`R-62`, C-09).
        """

        def work(session: Session) -> AccountView:
            if roles is not None:
                self._accounts.set_roles(
                    session, actor_uid=actor_uid, user_uid=user_uid, roles=roles
                )
            if names is not None:
                self._accounts.update_names(
                    session,
                    user_uid=user_uid,
                    last_name=names.last_name,
                    first_name=names.first_name,
                    middle_name=names.middle_name,
                )
            account = self._accounts.get_account(session, user_uid)
            if account is None or account.record.archived:
                raise _not_found("User")
            return _account_view(account)

        return self._write(work)

    def archive_account(self, *, actor_uid: str, user_uid: str) -> AccountView:
        def work(session: Session) -> AccountView:
            self._accounts.archive_account(session, actor_uid=actor_uid, user_uid=user_uid)
            return self._view_of(session, user_uid)

        return self._write(work)

    def restore_account(self, *, actor_uid: str, user_uid: str) -> AccountView:
        def work(session: Session) -> AccountView:
            self._accounts.restore_account(session, actor_uid=actor_uid, user_uid=user_uid)
            return self._view_of(session, user_uid)

        return self._write(work)

    def purge_account(self, *, actor_uid: str, user_uid: str) -> None:
        self._write(
            lambda session: self._accounts.purge_account(
                session, actor_uid=actor_uid, user_uid=user_uid
            )
        )

    def reset_password(
        self, *, actor_uid: str, user_uid: str, temporary_password: str
    ) -> AccountView:
        def work(session: Session) -> AccountView:
            self._accounts.reset_password(
                session,
                actor_uid=actor_uid,
                user_uid=user_uid,
                temporary_password=temporary_password,
            )
            return self._view_of(session, user_uid)

        return self._write(work)


#: `W49-SEAL-01`. The command type an approval claims its idempotency key under, beside
#: `append_decision` and the run and upload commands that share `command_record`.
APPROVE_REGISTRATION_COMMAND = "approve_registration"


class RegistrationAdapter(_SessionHolder):
    """``RegistrationPort`` over ``auditmanager.access.registrations``.

    **The status read commits.** ``read_status`` counts a refused read on the request's
    own brake, and the caller owns the transaction: a read session would discard the count
    on the way out, and the brake would be applied in the log and nowhere else -- the
    reason ``CredentialAdapter.issue`` writes.

    **The approval claims its key in the same transaction as the approval**, through
    ``auditmanager.ingest``'s ``CommandRepository`` -- the primitive every keyed create on
    this surface claims with -- so an identical repeat replays the decided request and a
    reused key with another payload is ``idempotency_key_reuse``. The approval itself, and
    every rule of it, is ``auditmanager.access``'s.
    """

    __slots__ = ("_registrations",)

    def __init__(
        self, session_factory: sessionmaker[Session], *, registrations: Any
    ) -> None:
        super().__init__(session_factory)
        #: ``auditmanager.access.ports.RegistrationRepository``.
        self._registrations = registrations

    def submit(
        self,
        *,
        login: str,
        password: str,
        last_name: str,
        first_name: str,
        middle_name: str | None,
    ) -> str:
        record = self._write(
            lambda session: self._registrations.submit(
                session,
                login=login,
                password=password,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
            )
        )
        return record.status

    def read_status(self, *, login: str, password: str) -> str | None:
        answer = self._write(
            lambda session: self._registrations.read_status(
                session, login=login, password=password
            )
        )
        if answer is None:
            return None
        if answer.status != "pending":
            # `R-56` addendum: only `pending` is ever shown. The access boundary can prove
            # a pair only for a pending request; anything else reaching here is a defect,
            # reported as one rather than shown to the applicant.
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                message="the status read proved a request that is not pending",
            )
        return answer.status

    def list_requests(self, *, status: str | None) -> RegistrationListingView:
        def work(session: Session) -> RegistrationListingView:
            items = self._registrations.list_requests(session, status=status)
            return RegistrationListingView(
                items=tuple(_registration_view(record) for record in items),
                pending_total=self._registrations.pending_total(session),
            )

        return self._read(work)

    def approve(
        self,
        *,
        actor_uid: str,
        request_id: str,
        roles: frozenset[str],
        idempotency_key: str,
    ) -> RegistrationView:
        from auditmanager.ingest.public import (
            CommandReplay,
            CommandRepository,
            payload_fingerprint,
        )

        def work(session: Session) -> RegistrationView:
            commands = CommandRepository()
            claim = commands.begin(
                session,
                command_type=APPROVE_REGISTRATION_COMMAND,
                idempotency_key=idempotency_key,
                fingerprint=payload_fingerprint(
                    {
                        "command": "approve_registration.v1",
                        "request_id": request_id,
                        "roles": sorted(roles),
                        "actor_uid": actor_uid,
                    }
                ),
            )
            if isinstance(claim, CommandReplay):
                recorded = claim.outcome.get("request_id")
                record = (
                    self._registrations.get(session, recorded)
                    if isinstance(recorded, str)
                    else None
                )
                if record is None:
                    raise DomainError(
                        ErrorCode.IDEMPOTENCY_KEY_STALE,
                        command_type=APPROVE_REGISTRATION_COMMAND,
                    )
                return _registration_view(record)
            decided, _account = self._registrations.approve(
                session, actor_uid=actor_uid, request_id=request_id, roles=roles
            )
            commands.succeed(session, claim.command_id, {"request_id": decided.request_id})
            return _registration_view(decided)

        return self._write(work)

    def reject(self, *, actor_uid: str, request_id: str, reason: str) -> RegistrationView:
        return self._write(
            lambda session: _registration_view(
                self._registrations.reject(
                    session, actor_uid=actor_uid, request_id=request_id, reason=reason
                )
            )
        )


class NormsSearchAdapter(_SessionHolder):
    """`W55A-SEARCH-01`. The six norms reads and the designation.

    Thin, as every adapter here: one session per call, one call into
    ``auditmanager.norms`` (``norms.public``: the search module and the current-snapshot
    module), and the answer mapped into the frozen shape. ``timeout_ms`` is the operator's
    ``AUDITMANAGER_NORMS_SEARCH_TIMEOUT_MS`` (``bootstrap/settings.py``), handed to every
    search; the refusals -- no current snapshot, a never-current scope, a stale
    ``expected_current``, a target that does not qualify, a search the timeout cancelled --
    are the module's, raised as typed failures and never an empty page.
    """

    def __init__(self, sessions: sessionmaker[Session], *, timeout_ms: int) -> None:
        super().__init__(sessions)
        if timeout_ms <= 0:
            raise ValueError("the norms search timeout must be positive")
        self._timeout_ms = timeout_ms

    def search(
        self, *, q: str, norms_snapshot_id: str | None, cursor: str | None, limit: int
    ) -> models.NormSearchPage:
        from auditmanager.norms.public import search_norms

        page = self._read(
            lambda session: search_norms(
                session, q=q, norms_snapshot_id=norms_snapshot_id, cursor=cursor,
                limit=limit, timeout_ms=self._timeout_ms,
            )
        )
        return models.NormSearchPage(
            items=[_norm_hit(hit) for hit in page.items],
            page=models.PageInfo(next_cursor=page.next_cursor),
        )

    def get_document(self, *, norm_document_id: str) -> models.NormDocument:
        from auditmanager.norms.public import get_norm_document

        return _norm_document(
            self._read(lambda session: get_norm_document(session, norm_document_id))
        )

    def list_paragraphs(
        self, *, norm_document_id: str, cursor: str | None, limit: int
    ) -> models.NormParagraphPage:
        from auditmanager.norms.public import list_norm_paragraphs

        document, page = self._read(
            lambda session: list_norm_paragraphs(
                session, norm_document_id, cursor=cursor, limit=limit
            )
        )
        return models.NormParagraphPage(
            items=[
                models.NormParagraph(
                    norm_paragraph_id=item.norm_paragraph_id,
                    ordinal=item.ordinal,
                    page_label=item.page_label,
                    block_ref=item.block_ref,
                    kind=models.NormParagraphKind(item.kind),
                    clause_number=item.clause_number,
                    text=item.text,
                    text_reliability=models.NormTextReliability(item.text_reliability),
                )
                for item in page.items
            ],
            page=models.PageInfo(next_cursor=page.next_cursor),
            source_attribution=models.NormSourceAttribution(document.source_attribution),
        )

    def list_snapshots(self, *, cursor: str | None, limit: int) -> models.NormSnapshotPage:
        from auditmanager.norms.public import list_norm_snapshots

        page = self._read(
            lambda session: list_norm_snapshots(session, cursor=cursor, limit=limit)
        )
        return models.NormSnapshotPage(
            items=[
                models.NormSnapshot(
                    norms_snapshot_id=item.norms_snapshot_id,
                    content_key=item.content_key,
                    document_count=item.document_count,
                    paragraph_count=item.paragraph_count,
                    unreliable_count=item.unreliable_count,
                    build_state=models.NormBuildState(item.build_state),
                    qualified=item.qualified,
                    current=item.current,
                    created_at=item.created_at,
                )
                for item in page.items
            ],
            page=models.PageInfo(next_cursor=page.next_cursor),
        )

    def list_snapshot_events(
        self, *, cursor: str | None, limit: int
    ) -> models.NormSnapshotEventPage:
        from auditmanager.norms.public import (
            EventPosition,
            decode_event_cursor,
            encode_event_cursor,
            list_snapshot_events,
        )

        position = None if cursor is None else decode_event_cursor(cursor)
        after = None if position is None else (position.changed_at, position.event_id)
        rows = self._read(
            lambda session: list_snapshot_events(session, after=after, limit=limit + 1)
        )
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = (
            encode_event_cursor(EventPosition(rows[-1].changed_at, rows[-1].event_id))
            if has_more and rows
            else None
        )
        return models.NormSnapshotEventPage(
            items=[
                models.NormSnapshotEvent(
                    event_id=row.event_id,
                    from_norms_snapshot_id=row.from_snapshot_id,
                    to_norms_snapshot_id=row.to_snapshot_id,
                    actor_user_uid=row.actor_user_uid,
                    changed_at=row.changed_at,
                )
                for row in rows
            ],
            page=models.PageInfo(next_cursor=next_cursor),
        )

    def set_current_snapshot(
        self, *, norms_snapshot_id: str, expected_current: str | None, user_uid: str
    ) -> models.NormCurrentSnapshot:
        from auditmanager.norms.public import set_current_snapshot

        designation = self._write(
            lambda session: set_current_snapshot(
                session,
                norms_snapshot_id=norms_snapshot_id,
                expected_current=expected_current,
                actor_user_uid=user_uid,
            )
        )
        return models.NormCurrentSnapshot(
            norms_snapshot_id=designation.current.norms_snapshot_id,
            designated_at=designation.current.designated_at,
            designated_by=designation.current.designated_by,
        )


def _norm_hit(hit: Any) -> models.NormSearchHit:
    return models.NormSearchHit(
        norms_snapshot_id=hit.norms_snapshot_id,
        norm_document_id=hit.norm_document_id,
        norm_paragraph_id=hit.norm_paragraph_id,
        designation=hit.designation,
        title=hit.title,
        doc_type=hit.doc_type,
        clause_number=hit.clause_number,
        page_label=hit.page_label,
        block_ref=hit.block_ref,
        fragment=models.NormFragment(
            text=hit.fragment.text,
            highlights=[
                models.NormHighlight(char_start=first, char_end=last)
                for first, last in hit.fragment.highlights
            ],
        ),
        source_attribution=models.NormSourceAttribution(hit.source_attribution),
    )


def _norm_document(document: Any) -> models.NormDocument:
    return models.NormDocument(
        norm_document_id=document.norm_document_id,
        norms_snapshot_id=document.norms_snapshot_id,
        designation=document.designation,
        title=document.title,
        doc_type=document.doc_type,
        drawn_on=document.drawn_on,
        pdf_page_count=document.pdf_page_count,
        paragraph_count=document.paragraph_count,
        unreliable_paragraph_count=document.unreliable_paragraph_count,
        content_available=document.content_available,
        source_attribution=models.NormSourceAttribution(document.source_attribution),
    )


class NormContentAdapter(_SessionHolder):
    """`W55A-SEARCH-01`. ``streamNormDocumentContent``: the PDF through its confirmed binding.

    `W55A-CONTENT-01`'s recipe (``docs/program/W55A-CONTENT-01.md`` section 5), in its order,
    because the caller sends a status line as soon as this returns:

    1. the document and its confirmed ``norm_source`` PDF binding -- an unknown document is
       ``not_found``, one without the binding ``required_norm_unavailable``
       (``reference_kind: norm_source``);
    2. the ``Range`` resolved against the **binding's** declared size -- ``422`` before the
       store is touched;
    3. the object opened with the binding's SHA-256 and size as the declaration, every
       storage failure typed as ``IngestService.open_source_stream`` types it (``role``
       ``norm_source``).

    The held-back last chunk of a whole read, the size checks and the
    ``storage_integrity_error`` log come with :meth:`BlobStore.open_stream`.
    """

    def __init__(self, sessions: sessionmaker[Session], *, blob_store: Any) -> None:
        super().__init__(sessions)
        self._blob_store = blob_store

    def stream_content(
        self, *, norm_document_id: str, byte_range: ByteRange | None
    ) -> StreamedContent:
        from auditmanager.ingest import domain_error_from_storage
        from auditmanager.norms.public import NORM_SOURCE, norm_pdf_binding
        from auditmanager.storage.public import (
            BlobId,
            BlobNotFoundError,
            StorageError,
        )

        binding = self._read(lambda session: norm_pdf_binding(session, norm_document_id))
        window = None if byte_range is None else byte_range.resolve(binding.size_bytes)
        try:
            chunks = self._blob_store.open_stream(
                BlobId(binding.blob_id),
                expected_sha256=binding.sha256,
                expected_size=binding.size_bytes,
                window=window,
                chunk_size=CONTENT_CHUNK_BYTES,
            )
        except BlobNotFoundError:
            raise DomainError(
                ErrorCode.STORAGE_INTEGRITY_ERROR,
                blob_id=binding.blob_id,
                role=NORM_SOURCE,
                expected_sha256=binding.sha256,
            ) from None
        except StorageError as exc:
            raise domain_error_from_storage(
                exc, blob_id=binding.blob_id, role=NORM_SOURCE
            ) from None
        return StreamedContent(
            media_type=PDF_MEDIA_TYPE,
            total_size=binding.size_bytes,
            window=window,
            chunks=_typed_norm_chunks(chunks, binding.blob_id),
        )


def _typed_norm_chunks(chunks: Any, blob_id: str) -> Any:
    """The opened body, a failure half-way raised as the system's typed failure."""
    from auditmanager.ingest import domain_error_from_storage
    from auditmanager.norms.public import NORM_SOURCE
    from auditmanager.storage.public import StorageError

    try:
        yield from chunks
    except StorageError as exc:
        raise domain_error_from_storage(exc, blob_id=blob_id, role=NORM_SOURCE) from None
    finally:
        chunks.close()


class ComparisonAdapter(_SessionHolder):
    """``compareDocumentVersions`` (`W59-VERSION-COMPARE-01`).

    The comparison context owns the rule (``comparison.public.VersionComparisonService``);
    this adapter owns only the two port implementations it needs and the mapping into the
    frozen ``VersionComparison``. **The path is proved first** (``get_version_in``): an
    unknown project, a document of another project or a source version of another document
    is ``404 not_found`` exactly as for every other addressed read (`D-67`); only then is the
    target judged, and a target the rule does not admit is an answer with a closed reason.
    One session holds every read -- the path chain, the version pair, both
    classifications, the runs, the stage rows -- and each text layer is read from the store
    with the SHA-256 and size its ``stage_result`` recorded, then checked as canonical
    ``prepared.text_layer`` for exactly that version and page count. A missing or differing
    blob is ``storage_integrity_error``, never an empty page; a run whose
    ``source_preparation`` did not succeed has no text and the service refuses
    ``text_unavailable``.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        blob_store: Any,
        section_codes: frozenset[str],
    ) -> None:
        from auditmanager.comparison.public import VersionComparisonService

        super().__init__(session_factory)
        self._blob_store = blob_store
        self._service = VersionComparisonService(
            classifications=_ClassificationReader(),
            analyses=_AnalysisReader(blob_store),
            section_codes=section_codes,
        )

    def compare_versions(
        self,
        *,
        project_uid: str,
        document_uid: str,
        source_version_uid: str,
        target_version_uid: str,
        source_run_id: str | None,
        target_run_id: str | None,
        mode: str,
        diff_offset: int,
        diff_limit: int,
    ) -> models.VersionComparison:
        from auditmanager.comparison.public import (
            ComparisonIntegrityError,
            ComparisonRequest,
            ComparisonRequestInvalid,
        )

        request = ComparisonRequest(
            project_uid=project_uid,
            document_uid=document_uid,
            source_version_uid=source_version_uid,
            target_version_uid=target_version_uid,
            source_run_id=source_run_id,
            target_run_id=target_run_id,
            diff_offset=diff_offset,
            diff_limit=diff_limit,
            mode=mode,
        )
        from auditmanager.documents.public import DocumentRepository
        from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid

        def work(session: Session) -> Any:
            DocumentRepository().get_version_in(
                session,
                project_uid=ProjectUid.parse(project_uid),
                document_uid=DocumentUid.parse(document_uid),
                version_uid=VersionUid.parse(source_version_uid),
            )
            return self._service.compare(session, request)

        try:
            result = self._read(work)
        except ComparisonRequestInvalid as exc:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field=str(exc).removesuffix("_invalid"),
                constraint="format",
            ) from None
        except ComparisonIntegrityError as exc:
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                message="the stored comparison inputs contradict their own constraints",
            ) from exc
        return models.VersionComparison.model_validate(_comparison_view(result))


class _ClassificationReader:
    """The seal's persisted classification (``documents``), never an inferred one."""

    def read_classification(self, session: Session, *, version_uid: str) -> Any:
        from auditmanager.comparison.public import SuppliedVersionClassification
        from auditmanager.documents.public import DocumentRepository
        from auditmanager.shared.identity import VersionUid

        stored = DocumentRepository().get_classification(session, VersionUid.parse(version_uid))
        if stored is None:
            return None
        return SuppliedVersionClassification(
            str(stored.version_uid), stored.project_stage, stored.section_code,
        )


class _AnalysisReader:
    """Runs, saved text layers and published findings, for the comparison service."""

    _SOURCE_STAGE = "source_preparation"

    def __init__(self, blob_store: Any) -> None:
        self._blob_store = blob_store

    def runs_newest_first(self, session: Session, *, version_uid: str) -> Any:
        from auditmanager.comparison.public import RunCandidate
        from auditmanager.runs import RunRepository

        return tuple(
            RunCandidate(str(run.run_id), run.state)
            for run in RunRepository().list_for_version(session, version_uid)
        )

    def saved_page_text(self, session: Session, *, run_id: str, version: Any) -> Any:
        from auditmanager.analysis.public import (
            ROLE_TEXT_LAYER,
            ArtifactRef,
            SuppliedTextSourceRefused,
            check_supplied_text_layer_bytes,
        )
        from auditmanager.comparison.public import SavedPageText
        from auditmanager.runs import RunRepository

        stages = [
            row for row in RunRepository().stage_results(session, run_id)
            if row.stage_id == self._SOURCE_STAGE
        ]
        if len(stages) != 1 or stages[0].status != "succeeded":
            return None
        references = [a for a in stages[0].artifacts if a.get("role") == ROLE_TEXT_LAYER]
        if len(references) != 1:
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                message="a succeeded source preparation does not record exactly one text layer",
            )
        reference = references[0]
        payload = _verified_artifact_bytes(self._blob_store, reference)
        try:
            layer = check_supplied_text_layer_bytes(
                version_uid=version.version_uid,
                expected_page_count=version.page_count,
                text_layer_ref=ArtifactRef(**dict(reference)),
                supplied_bytes=payload,
            )
        except (SuppliedTextSourceRefused, TypeError, ValueError):
            raise DomainError(
                ErrorCode.STORAGE_INTEGRITY_ERROR,
                blob_id=str(reference.get("blob_id")),
                role=ROLE_TEXT_LAYER,
                expected_sha256=str(reference.get("sha256")),
            ) from None
        return SavedPageText(
            run_id, str(reference["sha256"]),
            {page.page_number: page.text for page in layer.pages},
        )

    def published_findings(self, session: Session, *, run_id: str) -> Any:
        from auditmanager.comparison.public import FindingEvidenceSnapshot, FindingSnapshot
        from auditmanager.findings import published_finding_evidence, published_findings

        evidence: dict[str, list[Any]] = {}
        for item in published_finding_evidence(session, run_id):
            evidence.setdefault(item.finding_observation_id, []).append(item)
        return tuple(
            FindingSnapshot(
                row.finding_uid, row.finding_observation_id, row.category, row.finding_text,
                tuple(
                    FindingEvidenceSnapshot(item.page_number, item.quote)
                    for item in sorted(
                        evidence.get(row.finding_observation_id, ()),
                        key=lambda item: item.evidence_ordinal,
                    )
                ),
            )
            for row in published_findings(session, run_id)
        )


def _verified_artifact_bytes(blob_store: Any, reference: Mapping[str, Any]) -> bytes:
    """One artifact's bytes, held to the SHA-256 and size its stage row recorded."""
    from auditmanager.ingest import domain_error_from_storage
    from auditmanager.storage.public import BlobNotFoundError, StorageError, parse_blob_id

    blob_id, role = str(reference["blob_id"]), str(reference["role"])
    declared_sha256, declared_size = str(reference["sha256"]), int(reference["size_bytes"])
    try:
        chunks = blob_store.open_stream(
            parse_blob_id(blob_id), expected_sha256=declared_sha256, expected_size=declared_size,
        )
        try:
            return b"".join(chunks)
        finally:
            close = getattr(chunks, "close", None)
            if close is not None:
                close()
    except BlobNotFoundError:
        raise DomainError(
            ErrorCode.STORAGE_INTEGRITY_ERROR,
            blob_id=blob_id, role=role, expected_sha256=declared_sha256,
        ) from None
    except StorageError as exc:
        raise domain_error_from_storage(exc, blob_id=blob_id, role=role) from None


def _comparison_view(result: Any) -> dict[str, Any]:
    """The read model as the frozen ``VersionComparison`` shape (field names are equal)."""
    from dataclasses import asdict

    return asdict(result)
