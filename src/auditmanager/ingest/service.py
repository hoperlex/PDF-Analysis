"""The direct single-PDF upload use case.

One public sequence, written out in one place, because the order is the design.

The publication order, and why it is that order
-----------------------------------------------
``P2-META-01`` fixes it: "temporary upload, checksum verification, publish, blob
metadata row, then document version and input manifest rows, in one transaction with
the command record." This module implements that with the metadata row split across the
publication boundary, which is what makes the interrupted case recoverable:

===== ============================================ =========================
step   what happens                                 committed when it ends
===== ============================================ =========================
0      admission probe                              nothing; no service touched
1      claim the idempotency key                    ``command_record`` in_progress
2      stage temporary bytes                        nothing canonical
3      verify checksum and size                     nothing canonical
4      record the blob as ``verifying``             **committed**
5      publish to the canonical location            the object exists
6      blob ``available`` + version + manifest      **committed**, with the
       + command ``succeeded``, one transaction     command record
===== ============================================ =========================

**The database is canonical.** Bytes in the object store mean nothing until a committed
``blob`` row says ``available`` and a committed ``input_manifest_entry`` references it.
That is a decision, and everything else follows from it: a crash between step 5 and
step 6 leaves an orphan object rather than a half-version, and step 4's committed
``verifying`` row is the breadcrumb that lets
:mod:`auditmanager.ingest.reconciliation` find that object without the BlobStore port
having a ``list`` operation -- which it deliberately does not have.

Step 6 is a single transaction on purpose. A version that became visible without its
manifest would be a version nobody could reproduce, and the whole point of freezing the
manifest with the version is that a later run knows its exact input set.

Nothing here retries. ``docs/program/P02_SEAMS.md`` section 3.5: a retry that does not
consult the command record writes duplicates. The command record is how a caller
retries, and step 1 is where it is consulted.
"""

from __future__ import annotations

from typing import Any, Final, Mapping

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.documents import (
    ROLE_SOURCE_DOCUMENT,
    DocumentRepository,
    DocumentVersionRecord,
    ManifestEntry,
    ProjectRecord,
    UploadOutcome,
)
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    DocumentUid,
    IdempotencyKey,
    ProjectUid,
    VersionUid,
)
from auditmanager.storage import (
    BlobStore,
    StorageError,
    TemporaryBlob,
    VerifiedBlob,
    parse_blob_role,
)
from auditmanager.storage.blob_repository import BlobMetadataRepository

from .commands import (
    COMMAND_TYPE_UPLOAD,
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from .envelope import ACCEPTED_MEDIA_TYPE, AdmissionReport, probe
from .failures import domain_error_from_storage

__all__ = ["IngestService"]

_SOURCE_ROLE: Final = parse_blob_role(ROLE_SOURCE_DOCUMENT)


class IngestService:
    """Create projects, upload one PDF, and read back what was published.

    Constructed with its dependencies. It builds no engine, reads no ``DATABASE_URL``
    and writes no rollback of its own: the unit of work is
    :func:`auditmanager.shared.db.session_scope`, exactly as seam ``S12`` requires.
    """

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

    # -- projects ------------------------------------------------------------

    def create_project(self, name: str) -> ProjectRecord:
        with session_scope(self._factory) as session:
            return self._documents.create_project(session, name)

    def list_projects(self) -> tuple[ProjectRecord, ...]:
        with session_scope(self._factory) as session:
            return self._documents.list_projects(session)

    def get_project(self, project_uid: ProjectUid) -> ProjectRecord:
        with session_scope(self._factory) as session:
            return self._documents.get_project(session, project_uid)

    # -- reads ---------------------------------------------------------------

    def get_version(self, version_uid: VersionUid) -> DocumentVersionRecord:
        with session_scope(self._factory) as session:
            return self._documents.get_version(session, version_uid)

    def manifest_for(self, version_uid: VersionUid) -> tuple[ManifestEntry, ...]:
        """Seam ``S2``, as ``B5`` consumes it."""
        with session_scope(self._factory) as session:
            return self._documents.manifest_for(session, version_uid)

    def read_source_bytes(self, version_uid: VersionUid) -> bytes:
        """The source bytes of one published version.

        Deliberately the *only* route to them, and it goes through the manifest: the
        version names a ``blob_id``, the BlobStore resolves it, and nothing in between
        knows a bucket or a key. A missing object is
        ``storage_integrity_error`` -- the same answer reconciliation gives -- rather
        than an empty result that a caller might mistake for an empty document.
        """
        entry = self.require_source_entry(version_uid)
        try:
            return self._store.read(entry.blob_id)
        except StorageError as exc:
            raise domain_error_from_storage(exc, role=entry.role) from None

    def require_source_entry(self, version_uid: VersionUid) -> ManifestEntry:
        with session_scope(self._factory) as session:
            version = self._documents.get_version(session, version_uid)
        try:
            return version.source
        except KeyError:
            raise DomainError(
                ErrorCode.STORAGE_INTEGRITY_ERROR, role=ROLE_SOURCE_DOCUMENT
            ) from None

    # -- the upload command --------------------------------------------------

    def upload_single_pdf(
        self,
        *,
        project_uid: ProjectUid,
        content: bytes,
        source_filename: str,
        display_title: str,
        idempotency_key: IdempotencyKey,
        document_uid: DocumentUid | None = None,
    ) -> UploadOutcome:
        """Publish one PDF as one immutable version, or explain why not.

        ``display_title`` is the caller's own display label and is what a reviewer
        sees. It is a separate argument from ``source_filename`` on purpose: the file
        name is retained for the record but never travels back out, so a title the
        caller chose is the only presentation value a consumer receives.
        """
        # Step 0. The envelope, before any service is touched. A refusal here has
        # created nothing anywhere, including no command record, because nothing has
        # been attempted yet.
        report = probe(content, source_filename=source_filename)

        fingerprint = payload_fingerprint(
            {
                "project_uid": str(project_uid),
                "document_uid": None if document_uid is None else str(document_uid),
                "content_sha256": report.sha256,
                "byte_size": report.byte_size,
                "media_type": report.media_type,
                "source_filename": source_filename,
            }
        )

        # Step 1. Claim the key, having first proved the target exists so a bad target
        # does not burn a key.
        with session_scope(self._factory) as session:
            self._documents.get_project(session, project_uid)
            if document_uid is not None:
                owner = self._documents.require_document(session, document_uid)
                if owner != project_uid:
                    raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")
            claim = self._commands.begin(
                session,
                command_type=COMMAND_TYPE_UPLOAD,
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
            )

        if isinstance(claim, CommandReplay):
            return UploadOutcome(
                version=self.get_version(_replayed_version_uid(claim.outcome)),
                replayed=True,
            )
        assert isinstance(claim, CommandStarted)

        temporary: TemporaryBlob | None = None
        try:
            # Steps 2 and 3. Nothing is canonical until verification has passed; the
            # adapter removes the staged bytes itself on a mismatch.
            temporary = self._store.stage_temporary(
                content,
                declared_sha256=report.sha256,
                declared_size=report.byte_size,
                role=_SOURCE_ROLE,
                media_type=report.media_type,
            )
            verified = self._store.verify_temporary(temporary)

            # Step 4. Committed before publication: this row is what makes step 5's
            # object findable if step 6 never happens.
            with session_scope(self._factory) as session:
                self._blobs.record_verified(session, verified)

            # Step 5. The object becomes canonical. Idempotent by (sha256, size), so a
            # resumed publication of the same content re-uses the existing object.
            published = self._store.publish(verified)
            temporary = None

            # Step 6. One transaction: the blob becomes available, the version and its
            # manifest appear, and the command records its outcome, or none of it does.
            with session_scope(self._factory) as session:
                version_uid = self._commit_publication(
                    session,
                    report=report,
                    verified=verified,
                    project_uid=project_uid,
                    document_uid=document_uid,
                    display_title=display_title,
                    source_filename=source_filename,
                )
                self._commands.succeed(
                    session,
                    claim.command_id,
                    {
                        "version_uid": str(version_uid),
                        "blob_id": str(published.blob_id),
                    },
                )
                version = self._documents.get_version(session, version_uid)
            return UploadOutcome(version=version, replayed=False)

        except Exception as exc:
            # Deliberately ``Exception`` and not ``BaseException``: a KeyboardInterrupt
            # or SystemExit must stay an interrupt rather than be reported to a caller
            # as a domain failure. It leaves the command ``in_progress``, which is
            # exactly the case ``Reconciler.report`` names as a stale command.
            failure = self._as_domain_error(exc)
            if temporary is not None:
                # Staged bytes that will never be published. Deleting an absent object
                # is a no-op, so this is safe on every failure path.
                self._discard_quietly(temporary)
            self._record_failure(claim, failure)
            raise failure from None

    # -- internals -----------------------------------------------------------

    def _commit_publication(
        self,
        session: Session,
        *,
        report: AdmissionReport,
        verified: VerifiedBlob,
        project_uid: ProjectUid,
        document_uid: DocumentUid | None,
        display_title: str,
        source_filename: str,
    ) -> VersionUid:
        self._blobs.mark_available(session, verified.blob_id)
        target = document_uid
        if target is None:
            target = self._documents.create_document(
                session, project_uid, display_title
            )
        entry = ManifestEntry(
            role=ROLE_SOURCE_DOCUMENT,
            blob_id=verified.blob_id,
            sha256=verified.sha256,
            size_bytes=verified.size,
            media_type=ACCEPTED_MEDIA_TYPE,
        )
        return self._documents.publish_version(
            session,
            document_uid=target,
            media_type=report.media_type,
            byte_size=report.byte_size,
            sha256=report.sha256,
            page_count=report.page_count,
            source_filename=source_filename,
            entries=(entry,),
        )

    @staticmethod
    def _as_domain_error(exc: BaseException) -> DomainError:
        if isinstance(exc, DomainError):
            return exc
        if isinstance(exc, StorageError):
            return domain_error_from_storage(exc, role=ROLE_SOURCE_DOCUMENT)
        # An unclassified fault. The original never reaches a caller: the catalog's own
        # rule is that the internal code stays in protected diagnostics only.
        return DomainError(ErrorCode.INTERNAL_ERROR)

    def _discard_quietly(self, temporary: TemporaryBlob) -> None:
        try:
            self._store.discard_temporary(temporary)
        except StorageError:
            # The store is already failing; the original failure is the one that must
            # reach the caller. A staged object with no metadata row is inert -- it is
            # not addressable by any blob_id and no manifest can reference it.
            pass

    def _record_failure(self, claim: CommandStarted, failure: DomainError) -> None:
        """Terminate the command record, so a repeat of this key is answered.

        Its own unit of work: the failing one has already been rolled back, and this
        write must survive whatever went wrong with it. If even this fails the record
        stays ``in_progress`` and reconciliation reports it, which is the reason
        ``stale_in_progress`` exists.
        """
        try:
            with session_scope(self._factory) as session:
                self._commands.fail(session, claim.command_id, failure.code)
        except Exception:  # noqa: BLE001
            pass


def _replayed_version_uid(outcome: Mapping[str, Any]) -> VersionUid:
    raw = outcome.get("version_uid")
    if not isinstance(raw, str):
        raise DomainError(
            ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=COMMAND_TYPE_UPLOAD
        )
    return VersionUid(raw)
