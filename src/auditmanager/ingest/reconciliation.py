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
from auditmanager.storage import parse_blob_id
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
        """Prove one published version is still readable, or fail it.

        Raises ``storage_integrity_error`` when a manifest entry's bytes are absent, and
        also when the store's recorded checksum disagrees with the manifest's. The
        version is never repaired: it is immutable, and a corrected source file is a new
        ``version_uid``.
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
            if published.sha256 != entry.sha256 or published.size != entry.size_bytes:
                raise DomainError(
                    ErrorCode.STORAGE_INTEGRITY_ERROR,
                    blob_id=str(entry.blob_id),
                    role=entry.role,
                    expected_sha256=entry.sha256,
                    actual_sha256=published.sha256,
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
