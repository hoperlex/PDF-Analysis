"""Reconciling the object store against the database after an interrupted publication.

``P2-META-01``: "a reconciliation entrypoint reporting a published object with no
committed version row, and failing a version whose blob is missing with
``storage_integrity_error``." Those are the two directions a two-phase publication can
break, and this module is where each is named and answered.

What is canonical
-----------------
**The database.** Bytes in the store are meaningless until a committed ``blob`` row says
``available`` and a committed ``input_manifest_entry`` references them. Everything below
follows from that single decision:

``orphan_objects``
    Bytes that a current publication protocol can prove lost their owner.  W48's
    Attempt-scoped analysis intents are not placed here while they are live.

``legacy_unattributed_blobs``
    Blob rows with no manifest and no W48 publication intent.  They may pre-date
    migration ``0014`` and therefore have no Attempt authority from which an operator
    could infer that rejection is safe.  They remain visible and adoptable, but are
    never presented as action-ready orphans.

``unpublished_records``
    The database is mid-publication and the store has nothing. Nothing was ever
    canonical, so there is nothing to clean up. This also self-heals on a re-upload.

``missing_objects``
    A published version's manifest names bytes the store does not hold. This is the
    serious one: it means a reproducible run is no longer reproducible.
    :meth:`Reconciler.verify_version` raises ``storage_integrity_error`` for it, because
    the version is not repairable -- the version row is immutable, and correcting a
    source file creates a new ``version_uid``.

``missing_analysis_artifacts``
    A bound analysis publication names bytes the store no longer holds. Unlike an
    unbound intent this is consumer-visible evidence, so the report names its exact
    run, stage and artifact role. Bound analysis blobs are excluded from
    ``orphan_objects`` for the same reason manifest blobs are.

``unbound_analysis_artifacts``
    An Attempt committed publication intent but never committed the stage-result binding.
    The entry retains run/Attempt/stage attribution, Attempt state, creation time and
    staleness classification, and says whether point inspection found either its exact
    opaque temporary handle or the canonical object; neither handle nor storage location
    is exposed, and nothing is adopted or deleted.

``stale_commands``
    A ``command_record`` still ``in_progress`` long after its executor should have
    finished. Left alone it makes the key unusable forever, so an operator can abandon
    it explicitly.

Why the scan can work without listing the bucket
------------------------------------------------
It never enumerates the store. It starts from database rows -- the unsettled blobs, the
available blobs no manifest or bound analysis publication references, and the blobs those
two reference sets name -- and asks the store about each specific ``blob_id``. Unbound
analysis intents additionally carry an internal opaque upload handle, so the same sweep
can point-inspect the exact temporary object without returning that handle. That is why
:mod:`auditmanager.storage.blob_repository` commits ``temporary`` before upload and
``verifying`` before canonical publication: without those breadcrumbs an orphan would be
unfindable through a port that offers no ``list``.

What is cheap here and what is not
----------------------------------
The two entrypoints are deliberately priced differently, and the difference is the
answer to "should reconciliation read bytes".

:meth:`Reconciler.report` is the **sweep**. It touches every unsettled blob, every
available blob and every blob any manifest references, and it asks each question with
:meth:`Reconciler._object_exists` -- one ``head_object``, never a list and never a body.
Its cost must stay proportional to the number of rows and independent of how large the
objects are, so it establishes *presence* and nothing more. That is unchanged.

:meth:`Reconciler.verify_version` is the **verdict**, on one version an operator named.
It is not part of the sweep, it does not call ``_object_exists``, and nothing in this
repository calls it on a loop. It is the method whose whole reason to exist is to settle
whether a published version is still the version that was published, and a verdict that
never looks at the bytes cannot settle that. It therefore reads and hashes each manifest
entry's body, and pays one full transfer per entry to do it. Wave 12 made that change;
before it, both entrypoints were ``head``-only and the verdict was worth no more than
the sweep.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.documents.public import DocumentRepository
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import CommandId, VersionUid
from auditmanager.storage.public import (
    BlobId,
    BlobNotFoundError,
    BlobStore,
    StorageError,
    TemporaryBlob,
    parse_blob_id,
    parse_blob_role,
    sha256_of,
)
from auditmanager.storage.public import BlobMetadataRepository

from .commands import CommandRepository
from .failures import domain_error_from_storage

__all__ = [
    "MissingAnalysisArtifact",
    "MissingObject",
    "LegacyUnattributedBlob",
    "OrphanObject",
    "ReconciliationReport",
    "Reconciler",
    "UnboundAnalysisArtifact",
]

_AVAILABLE_WITHOUT_MANIFEST = text(
    "SELECT b.blob_id, b.state, b.sha256, b.size_bytes FROM blob b "
    "WHERE b.state = 'available' AND NOT EXISTS ("
    "  SELECT 1 FROM input_manifest_entry m WHERE m.blob_id = b.blob_id"
    ") AND NOT EXISTS ("
    "  SELECT 1 FROM analysis_artifact_publication a "
    "  WHERE a.blob_id = b.blob_id"
    ") ORDER BY b.created_at"
)

_BOUND_ANALYSIS_ARTIFACTS = text(
    "SELECT DISTINCT blob_id, run_id, stage_id, artifact_role "
    "FROM analysis_artifact_publication WHERE state = 'bound' "
    "ORDER BY blob_id, run_id, stage_id, artifact_role"
)

_UNBOUND_ANALYSIS_ARTIFACTS = text(
    "SELECT a.blob_id, a.run_id, a.job_id, a.attempt_id, a.stage_id, a.blob_role, "
    "a.upload_token, b.sha256, b.size_bytes, b.media_type, execution_attempt.state, "
    "a.created_at, "
    "a.created_at <= statement_timestamp() - CAST(:older_than AS interval) AS is_stale "
    "FROM analysis_artifact_publication a "
    "JOIN blob b ON b.blob_id = a.blob_id "
    "JOIN attempt execution_attempt ON execution_attempt.attempt_id = a.attempt_id "
    "WHERE a.state = 'prepared' "
    "ORDER BY a.created_at, a.attempt_id, a.stage_id, a.blob_id, a.blob_role"
)

_REJECTION_AUTHORITY = text(
    "SELECT a.upload_token, a.blob_role, a.created_at, b.sha256, b.size_bytes, "
    "b.media_type, execution_attempt.state AS attempt_state, "
    "a.created_at <= statement_timestamp() - CAST(:older_than AS interval) AS is_stale "
    "FROM analysis_artifact_publication a "
    "JOIN blob b ON b.blob_id = a.blob_id "
    "JOIN attempt execution_attempt ON execution_attempt.attempt_id = a.attempt_id "
    "WHERE a.blob_id = :blob_id AND a.state = 'prepared' "
    "ORDER BY a.created_at, a.attempt_id, a.stage_id, a.blob_role "
    "FOR UPDATE OF a, execution_attempt"
)

_ATTEMPT_TERMINALS = frozenset({"succeeded", "failed", "superseded", "lost", "cancelled"})


@dataclass(frozen=True, slots=True)
class OrphanObject:
    """Bytes the database does not fully own. Identity and content facts only."""

    blob_id: BlobId
    recorded_state: str
    sha256: str | None
    size_bytes: int | None


@dataclass(frozen=True, slots=True)
class LegacyUnattributedBlob:
    """A pre-0014-style blob with no Attempt-scoped publication authority."""

    blob_id: BlobId
    recorded_state: str
    sha256: str | None
    size_bytes: int | None
    object_present: bool


@dataclass(frozen=True, slots=True)
class MissingObject:
    """A published manifest entry whose bytes the store no longer holds."""

    blob_id: BlobId
    version_uid: VersionUid
    role: str


@dataclass(frozen=True, slots=True)
class MissingAnalysisArtifact:
    """A committed stage result binding whose content-addressed bytes are absent."""

    blob_id: BlobId
    run_id: str
    stage_id: str
    role: str


@dataclass(frozen=True, slots=True)
class UnboundAnalysisArtifact:
    """A pre-effect publication intent that never became a stage-result binding.

    Presence booleans expose the two point inspections, never the opaque upload handle.
    """

    blob_id: BlobId
    run_id: str
    job_id: str
    attempt_id: str
    stage_id: str
    role: str
    attempt_state: str
    created_at: datetime
    is_stale: bool
    object_present: bool
    temporary_present: bool

    @property
    def rejection_eligible(self) -> bool:
        """Whether the ordinary rejection action may safely settle this evidence."""
        return (
            self.attempt_state in _ATTEMPT_TERMINALS
            and self.is_stale
            and not self.object_present
            and not self.temporary_present
        )


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    """What one reconciliation pass found. Empty on a healthy instance."""

    orphan_objects: tuple[OrphanObject, ...] = ()
    unpublished_records: tuple[OrphanObject, ...] = ()
    legacy_unattributed_blobs: tuple[LegacyUnattributedBlob, ...] = ()
    missing_objects: tuple[MissingObject, ...] = ()
    missing_analysis_artifacts: tuple[MissingAnalysisArtifact, ...] = ()
    unbound_analysis_artifacts: tuple[UnboundAnalysisArtifact, ...] = ()
    stale_commands: tuple[CommandId, ...] = ()

    @property
    def is_clean(self) -> bool:
        return not (
            self.orphan_objects
            or self.unpublished_records
            or self.legacy_unattributed_blobs
            or self.missing_objects
            or self.missing_analysis_artifacts
            or self.unbound_analysis_artifacts
            or self.stale_commands
        )

    def describe(self) -> str:
        """A short operator-facing summary. Counts and opaque identities only."""
        return (
            f"orphan_objects={len(self.orphan_objects)} "
            f"unpublished_records={len(self.unpublished_records)} "
            f"legacy_unattributed_blobs={len(self.legacy_unattributed_blobs)} "
            f"missing_objects={len(self.missing_objects)} "
            f"missing_analysis_artifacts={len(self.missing_analysis_artifacts)} "
            f"unbound_analysis_artifacts={len(self.unbound_analysis_artifacts)} "
            f"stale_commands={len(self.stale_commands)}"
        )


class Reconciler:
    """The reconciliation entrypoint. Reports; repairs only when told to explicitly."""

    __slots__ = ("_store", "_factory", "_documents", "_blobs", "_commands")

    def __init__(
        self,
        store: BlobStore,
        *,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        self._store = store
        self._factory = session_factory
        self._documents = DocumentRepository()
        self._blobs = BlobMetadataRepository()
        self._commands = CommandRepository()

    def report(
        self,
        *,
        stale_command_age: str = "1 hour",
        unbound_artifact_age: str = "1 hour",
    ) -> ReconciliationReport:
        """One full pass. Reads only; changes nothing anywhere."""
        with session_scope(self._factory) as session:
            unsettled = self._blobs.unsettled(session)
            detached = tuple(
                LegacyUnattributedBlob(
                    blob_id=parse_blob_id(blob_id),
                    recorded_state=state,
                    sha256=sha256,
                    size_bytes=None if size is None else int(size),
                    object_present=True,
                )
                for blob_id, state, sha256, size in (
                    tuple(row)
                    for row in session.execute(_AVAILABLE_WITHOUT_MANIFEST).all()
                )
            )
            manifest_blobs = self._documents.manifest_blob_ids(session)
            analysis_artifacts = tuple(
                (
                    parse_blob_id(blob_id),
                    str(run_id),
                    str(stage_id),
                    str(role),
                )
                for blob_id, run_id, stage_id, role in session.execute(
                    _BOUND_ANALYSIS_ARTIFACTS
                ).all()
            )
            unbound_artifacts = tuple(
                (
                    parse_blob_id(blob_id),
                    str(run_id),
                    str(job_id),
                    str(attempt_id),
                    str(stage_id),
                    str(role),
                    TemporaryBlob(
                        upload_token=str(upload_token),
                        declared_sha256=str(sha256),
                        declared_size=int(size_bytes),
                        role=parse_blob_role(str(role)),
                        media_type=str(media_type),
                    ),
                    str(attempt_state),
                    created_at,
                    bool(is_stale),
                )
                for (
                    blob_id,
                    run_id,
                    job_id,
                    attempt_id,
                    stage_id,
                    role,
                    upload_token,
                    sha256,
                    size_bytes,
                    media_type,
                    attempt_state,
                    created_at,
                    is_stale,
                ) in session.execute(
                    _UNBOUND_ANALYSIS_ARTIFACTS,
                    {"older_than": unbound_artifact_age},
                ).all()
            )
            stale = tuple(
                record.command_id
                for record in self._commands.stale_in_progress(
                    session, older_than=stale_command_age
                )
            )

        unbound_blob_ids = {blob_id for blob_id, *_rest in unbound_artifacts}
        legacy: list[LegacyUnattributedBlob] = list(detached)
        for record in unsettled:
            if record.blob_id in unbound_blob_ids:
                continue
            object_present = self._object_exists(record.blob_id)
            legacy.append(
                LegacyUnattributedBlob(
                    blob_id=record.blob_id,
                    recorded_state=record.state.value,
                    sha256=record.sha256,
                    size_bytes=record.size_bytes,
                    object_present=object_present,
                )
            )

        missing: list[MissingObject] = []
        for blob_id in manifest_blobs:
            if self._object_exists(blob_id):
                continue
            with session_scope(self._factory) as session:
                references = self._documents.versions_referencing(session, blob_id)
            missing.extend(
                MissingObject(blob_id=blob_id, version_uid=version_uid, role=role)
                for version_uid, role in references
            )

        missing_analysis: list[MissingAnalysisArtifact] = []
        for blob_id, run_id, stage_id, role in analysis_artifacts:
            if self._object_exists(blob_id):
                continue
            missing_analysis.append(
                MissingAnalysisArtifact(
                    blob_id=blob_id,
                    run_id=run_id,
                    stage_id=stage_id,
                    role=role,
                )
            )

        unbound_analysis = tuple(
            UnboundAnalysisArtifact(
                blob_id=blob_id,
                run_id=run_id,
                job_id=job_id,
                attempt_id=attempt_id,
                stage_id=stage_id,
                role=role,
                attempt_state=attempt_state,
                created_at=created_at,
                is_stale=bool(is_stale),
                object_present=self._object_exists(blob_id),
                temporary_present=self._store.temporary_exists(temporary),
            )
            for (
                blob_id,
                run_id,
                job_id,
                attempt_id,
                stage_id,
                role,
                temporary,
                attempt_state,
                created_at,
                is_stale,
            ) in unbound_artifacts
        )

        return ReconciliationReport(
            legacy_unattributed_blobs=tuple(legacy),
            missing_objects=tuple(missing),
            missing_analysis_artifacts=tuple(missing_analysis),
            unbound_analysis_artifacts=unbound_analysis,
            stale_commands=stale,
        )

    def verify_version(self, version_uid: VersionUid) -> None:
        """Prove one published version is still the bytes it was published as, or fail it.

        Three questions per manifest entry, asked in this order because each is cheaper
        than the next and each can settle the verdict on its own.

        **1. Does the store hold anything at all?** An absent object is
        ``storage_integrity_error`` carrying ``expected_sha256`` and no
        ``actual_sha256`` -- there is nothing to have hashed. This is the module
        docstring's ``missing_objects``, and it is unchanged.

        **2. Can the store vouch for the object, and does its record agree with the
        manifest?** ``inspect`` is a ``head_object``: it returns what the object
        *records*, never what it holds. An object recording **no** digest is
        ``validation_failed`` -- the store has compared nothing to anything and has no
        evidence about these bytes, which is the same answer and the same code
        ``BlobStore.read`` gives over the same row, and is not the integrity verdict that
        would send an operator to restore a backup they may not need. A record that
        *disagrees* with the manifest's digest or length is ``storage_integrity_error``
        with the record as ``actual_sha256``, and is refused here without pulling a body:
        the verdict is already settled and the transfer would buy nothing.

        **3. Are the bytes the document the manifest names?** Reached only when the two
        declarations agree, which is precisely the state in which nothing has yet looked
        at the object. The body is read and hashed and compared against ``entry.sha256``.

        Question 3 is what wave 12 added, and the reason is that questions 1 and 2 are
        both comparisons between *declarations*. A replacement that preserved the
        object's recorded metadata and its length satisfied both and was reported sound
        here, while :meth:`auditmanager.ingest.service.IngestService.read_source_bytes`
        refused the same row -- reconciliation, the tool an operator uses to decide a
        version is fine, being the permissive one. The manifest entry is the only digest
        that is independent of the object, so it is the one compared, and the read is
        ``verify=False`` deliberately: the adapter's own check is the object against its
        *own* record, which question 2 has already tied to the manifest, and leaving it
        on would make the comparison below a branch no test could redden.

        Both integrity refusals are ``storage_integrity_error``. That is not the two
        causes flattened into one answer: they are two comparisons, each separately
        guarded, and ``actual_sha256`` names the strongest fact the method established --
        the store's record when nothing was read, the bytes' own digest when they were.
        The catalog declares ``blob_id``, ``expected_sha256``, ``actual_sha256`` and
        ``role`` for this code and no discriminator, so the only way to give the two
        causes two codes would be to move one to ``validation_failed``, which would put
        this method and the read path back to two answers over one row -- the condition
        wave 11 removed.

        The version is never repaired: it is immutable, and a corrected source file is a
        new ``version_uid``.
        """
        with session_scope(self._factory) as session:
            version = self._documents.get_version(session, version_uid)
        for entry in version.manifest:
            try:
                published = self._store.inspect(entry.blob_id)
            except BlobNotFoundError:
                raise DomainError(
                    ErrorCode.STORAGE_INTEGRITY_ERROR,
                    blob_id=str(entry.blob_id),
                    role=entry.role,
                    expected_sha256=entry.sha256,
                ) from None
            except StorageError as exc:
                raise domain_error_from_storage(exc, role=entry.role) from None
            if not published.sha256:
                # An object with no recorded digest. Reporting this as an integrity
                # failure would put ``actual_sha256=""`` into an operator's envelope --
                # an empty string where a digest is expected, and a claim about bytes
                # nothing has looked at. ``field`` is the port's own spelling: this
                # method holds a ``BlobStore`` and reads ``PublishedBlob.sha256``, and it
                # has no business naming an S3 metadata key.
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED,
                    aggregate_type="Blob",
                    field="sha256",
                    constraint="recorded on every published object",
                )
            if published.sha256 != entry.sha256 or published.size != entry.size_bytes:
                raise DomainError(
                    ErrorCode.STORAGE_INTEGRITY_ERROR,
                    blob_id=str(entry.blob_id),
                    role=entry.role,
                    expected_sha256=entry.sha256,
                    actual_sha256=published.sha256,
                )
            try:
                # ``verify=False`` is not a weaker check, it is a different and stronger
                # one: the adapter would compare the body against the object's own
                # record, and the comparison that follows is against the manifest.
                data = self._store.read(entry.blob_id, verify=False)
            except BlobNotFoundError:
                # The object was there for the ``head`` and gone for the ``get``.
                raise DomainError(
                    ErrorCode.STORAGE_INTEGRITY_ERROR,
                    blob_id=str(entry.blob_id),
                    role=entry.role,
                    expected_sha256=entry.sha256,
                ) from None
            except StorageError as exc:
                raise domain_error_from_storage(exc, role=entry.role) from None
            actual_sha256 = sha256_of(data)
            if actual_sha256 != entry.sha256:
                raise DomainError(
                    ErrorCode.STORAGE_INTEGRITY_ERROR,
                    blob_id=str(entry.blob_id),
                    role=entry.role,
                    expected_sha256=entry.sha256,
                    actual_sha256=actual_sha256,
                )

    def abandon_stale_commands(
        self, *, older_than: str = "1 hour"
    ) -> tuple[CommandId, ...]:
        """Move stale ``in_progress`` records to ``abandoned``.

        Abandoned is terminal, so the key is never reusable afterwards. That is the
        contract's answer and not a choice made here: a caller whose command outcome
        cannot be established retries with a new key rather than replaying a result
        nobody can vouch for.
        """
        with session_scope(self._factory) as session:
            stale = self._commands.stale_in_progress(session, older_than=older_than)
            for record in stale:
                self._commands.abandon(session, record.command_id)
            return tuple(record.command_id for record in stale)

    def reject_unpublished(
        self, blob_id: BlobId, *, older_than: str = "1 hour"
    ) -> None:
        """Settle one never-published blob record as ``rejected``.

        Eligibility requires Attempt-scoped W48 authority, a terminal producing Attempt,
        and an explicit age threshold. Legacy rows cannot prove that authority. A
        canonical or temporary object also requires a separate recovery decision and is
        refused here rather than burned under a content-derived identity.
        """
        with session_scope(self._factory) as session:
            record = self._blobs.require(session, blob_id)
            if record.is_available:
                raise DomainError(
                    ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
                    machine="blob",
                    current_state=record.state.value,
                    requested_state="rejected",
                )
            authorities = session.execute(
                _REJECTION_AUTHORITY,
                {"blob_id": str(blob_id), "older_than": older_than},
            ).mappings().all()
            if not authorities:
                self._refuse_rejection("legacy_unattributed")
            if any(row["attempt_state"] not in _ATTEMPT_TERMINALS for row in authorities):
                self._refuse_rejection("attempt_not_terminal")
            if any(not bool(row["is_stale"]) for row in authorities):
                self._refuse_rejection("publication_not_stale")
            if self._object_exists(blob_id):
                self._refuse_rejection("canonical_object_present")
            for row in authorities:
                temporary = TemporaryBlob(
                    upload_token=str(row["upload_token"]),
                    declared_sha256=str(row["sha256"]),
                    declared_size=int(row["size_bytes"]),
                    role=parse_blob_role(str(row["blob_role"])),
                    media_type=str(row["media_type"]),
                )
                if self._store.temporary_exists(temporary):
                    self._refuse_rejection("temporary_object_present")
            self._blobs.mark_rejected(session, blob_id)

    # -- internals -----------------------------------------------------------

    def _object_exists(self, blob_id: BlobId) -> bool:
        """Ask the store about one specific blob. Never lists, never reads bytes."""
        try:
            self._store.inspect(blob_id)
        except BlobNotFoundError:
            return False
        except StorageError as exc:
            # An unreachable store must not be reported as "the object is gone": that
            # would turn a transient outage into a permanent integrity verdict.
            raise domain_error_from_storage(exc) from None
        return True

    @staticmethod
    def _refuse_rejection(current_state: str) -> None:
        raise DomainError(
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
            machine="analysis_artifact_publication",
            current_state=current_state,
            requested_state="reject_blob",
        )
