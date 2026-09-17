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
    The store holds an object the database never finished claiming. This is the crash
    between publish and commit. The bytes are inert -- no manifest references them, so
    no run can read them -- and they are *adoptable*: because ``blob_id`` is derived
    from ``(sha256, size)``, re-uploading the identical content resolves to the same
    identifier, finds the ``verifying`` row already there and completes it, re-using the
    object rather than writing a second copy. Reconciliation therefore **reports** and
    does not delete. It could not delete in any case: the BlobStore port has no delete
    or erase operation, by design.

``unpublished_records``
    The database is mid-publication and the store has nothing. Nothing was ever
    canonical, so there is nothing to clean up. This also self-heals on a re-upload.

``missing_objects``
    A published version's manifest names bytes the store does not hold. This is the
    serious one: it means a reproducible run is no longer reproducible.
    :meth:`Reconciler.verify_version` raises ``storage_integrity_error`` for it, because
    the version is not repairable -- the version row is immutable, and correcting a
    source file creates a new ``version_uid``.

``stale_commands``
    A ``command_record`` still ``in_progress`` long after its executor should have
    finished. Left alone it makes the key unusable forever, so an operator can abandon
    it explicitly.

Why the scan can work without listing the bucket
------------------------------------------------
It never enumerates the store. It starts from database rows -- the unsettled blobs, the
available blobs no manifest references, the blobs every manifest does reference -- and
asks the store about each specific ``blob_id``. That is exactly why
:mod:`auditmanager.storage.blob_repository` commits the ``verifying`` row *before* the
object is published: without that breadcrumb an orphan would be unfindable through a
port that offers no ``list``.

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

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.documents import DocumentRepository
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import CommandId, VersionUid
from auditmanager.storage import BlobId, BlobNotFoundError, BlobStore, StorageError
from auditmanager.storage import parse_blob_id, sha256_of
from auditmanager.storage.blob_repository import BlobMetadataRepository

from .commands import CommandRepository
from .failures import domain_error_from_storage

__all__ = [
    "MissingObject",
    "OrphanObject",
    "ReconciliationReport",
    "Reconciler",
]

_AVAILABLE_WITHOUT_MANIFEST = text(
    "SELECT b.blob_id, b.state, b.sha256, b.size_bytes FROM blob b "
    "WHERE b.state = 'available' AND NOT EXISTS ("
    "  SELECT 1 FROM input_manifest_entry m WHERE m.blob_id = b.blob_id"
    ") ORDER BY b.created_at"
)


@dataclass(frozen=True, slots=True)
class OrphanObject:
    """Bytes the database does not fully own. Identity and content facts only."""

    blob_id: BlobId
    recorded_state: str
    sha256: str | None
    size_bytes: int | None


@dataclass(frozen=True, slots=True)
class MissingObject:
    """A published manifest entry whose bytes the store no longer holds."""

    blob_id: BlobId
    version_uid: VersionUid
    role: str


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    """What one reconciliation pass found. Empty on a healthy instance."""

    orphan_objects: tuple[OrphanObject, ...] = ()
    unpublished_records: tuple[OrphanObject, ...] = ()
    missing_objects: tuple[MissingObject, ...] = ()
    stale_commands: tuple[CommandId, ...] = ()

    @property
    def is_clean(self) -> bool:
        return not (
            self.orphan_objects
            or self.unpublished_records
            or self.missing_objects
            or self.stale_commands
        )

    def describe(self) -> str:
        """A short operator-facing summary. Counts and opaque identities only."""
        return (
            f"orphan_objects={len(self.orphan_objects)} "
            f"unpublished_records={len(self.unpublished_records)} "
            f"missing_objects={len(self.missing_objects)} "
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

    def report(self, *, stale_command_age: str = "1 hour") -> ReconciliationReport:
        """One full pass. Reads only; changes nothing anywhere."""
        with session_scope(self._factory) as session:
            unsettled = self._blobs.unsettled(session)
            detached = tuple(
                OrphanObject(
                    blob_id=parse_blob_id(blob_id),
                    recorded_state=state,
                    sha256=sha256,
                    size_bytes=None if size is None else int(size),
                )
                for blob_id, state, sha256, size in (
                    tuple(row)
                    for row in session.execute(_AVAILABLE_WITHOUT_MANIFEST).all()
                )
            )
            manifest_blobs = self._documents.manifest_blob_ids(session)
            stale = tuple(
                record.command_id
                for record in self._commands.stale_in_progress(
                    session, older_than=stale_command_age
                )
            )

        orphans: list[OrphanObject] = list(detached)
        unpublished: list[OrphanObject] = []
        for record in unsettled:
            candidate = OrphanObject(
                blob_id=record.blob_id,
                recorded_state=record.state.value,
                sha256=record.sha256,
                size_bytes=record.size_bytes,
            )
            if self._object_exists(record.blob_id):
                orphans.append(candidate)
            else:
                unpublished.append(candidate)

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

        return ReconciliationReport(
            orphan_objects=tuple(orphans),
            unpublished_records=tuple(unpublished),
            missing_objects=tuple(missing),
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

    def reject_unpublished(self, blob_id: BlobId) -> None:
        """Settle one never-published blob record as ``rejected``.

        Explicit and opt-in, and it has a consequence worth stating: ``blob_id`` is
        derived from ``(sha256, size)``, so a rejected record permanently occupies the
        identity of that exact content and a later upload of identical bytes will be
        refused with ``state_transition_not_allowed``. Rejection is for content an
        operator has decided must never be stored. For an ordinary interrupted upload,
        do nothing: a re-upload adopts the record and completes it.
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
