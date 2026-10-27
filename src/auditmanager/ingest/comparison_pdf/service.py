"""The use cases of a comparison upload: declare, send in parts, complete, read, propose, confirm.

The functions of :class:`ComparisonUploadService` serve the contract's ``createComparisonUpload``,
``getComparisonUpload``, ``getComparisonUploadProposal``, ``uploadComparisonUploadPart``,
``completeComparisonUploadFile`` and ``confirmComparisonUploadSet``; the order of the versions of a document is
:mod:`.orders`. The rules are ADR-0025 decisions 9, 10, 11 and 16.

The sequence of one file, and why it is that sequence
-----------------------------------------------------
============================ ============================================= =====================================
step                         what happens                                  committed when it ends
============================ ============================================= =====================================
declare (once per batch)     the batch, its files (name, size, SHA-256)    **committed**; the limits of decision 9
                                                                           were refused before any row existed
first part of a file         the declared Blob row, the multipart token     **committed before any byte moves**
                             (write-once) and the part row, ``declared``
each part                    the store's ``UploadPart``; the part row       ``staged`` with size, SHA-256 and ETag
                             moves to ``staged`` and the key's receipt
completion                   the store assembles the parts under a          ``verifying`` for the declared Blob
                             temporary key, reads the whole object back
                             and compares SHA-256 and size (a mismatch
                             removes it and the file is ``failed``)
                             publish; the Blob is ``available`` and the     **committed**
                             file names it
reading                      the comparison envelope and the stamp reader,  nothing (a refusal marks the file
                             each in a ceilinged child                      ``failed`` with its reason)
placement                    the file is ``verified`` and joins the set of  **committed** with the command
                             its designation (or its name); when every
                             file of the batch is settled the batch is
                             ``proposed`` and its sets ``needs_confirmation``
confirmation                 one transaction: the document, one            **committed** with the command
                             ``comparison_pdf`` version per file, the
                             classification, the order revision, the set
                             ``done``
============================ ============================================= =====================================

**The database is canonical.** The bytes mean nothing until a committed ``blob`` row says ``available`` and a
committed ``comparison_upload_file`` names it; a process killed between two steps leaves state the next call
resumes from (a file with its blob and no reading resumes at the reading; a completion whose temporary upload is
gone but whose Blob was published is recognised by the Blob's identity, which is the content's). Nothing here
retries by itself.

**Idempotency.** Every keyed write is answered from its recorded outcome under the same key and refused under a
different payload (``idempotency_key_reuse``). The three single-transaction writes (declare, confirm, append an
order) claim the key first, inside their one transaction. The two writes that move bytes (a part, a completion)
claim it **last**, in the transaction that records their result, so a request that dies half-way leaves no
``in_progress`` record that would block the client's retry under the same key; both are idempotent by state in any
case (a staged part with the same bytes replays its receipt, a verified file is answered as verified).

**What it never does.** It never decides an expert's question: the designation, the order, the labels, the stage
and the section are proposals until a set is confirmed (decision 11); it never uses a name as an identity
(decision 10); it never makes a comparison-only version the current version of a document that has a portal
version (``documents.public.DocumentRepository.publish_version``, decision 11); and it never writes a state the
batch operations own (`CMP-INGEST-02`): ``excluded``, ``paused``, ``processing``, ``cancelled`` or a retry.
"""

from __future__ import annotations

import re
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, Protocol

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.documents.public import (
    MANIFEST_ROLE_COMPARISON_PDF,
    ROLE_COMPARISON_PDF,
    UPLOAD_KIND_COMPARISON_PDF,
    DocumentRepository,
    ManifestEntry,
)
from auditmanager.ingest.commands import (
    CommandRecord,
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from auditmanager.ingest.failures import domain_error_from_storage
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, IdempotencyKey, ProjectUid
from auditmanager.storage.public import (
    BlobIntegrityError,
    BlobMetadataRepository,
    BlobNotFoundError,
    BlobStore,
    MultipartStaging,
    StorageError,
    TemporaryBlobLostError,
    UploadedPart,
    declare_blob,
    new_multipart_token,
    parse_blob_id,
    parse_blob_role,
    sha256_of,
)

from .limits import (
    ACTIVE_UPLOADS_PER_ACCOUNT,
    ACTIVE_UPLOADS_PER_INSTALLATION,
    MAX_SETS,
    PART_BYTES,
    DeclaredFile,
    check_declaration,
    parts_needed,
)
from .names import clean_display_name, name_hint, source_filename_of
from .proposal import FileEntry, SetProposal, fold_designation, grouping_key, propose_set
from .reading import PdfReading, read_pdf
from .repository import (
    ComparisonUploadRepository,
    FileRow,
    SetRow,
    UploadRow,
    new_file_id,
    new_order_id,
    new_set_id,
    new_upload_id,
)
from .stamp import FileStamp
from .views import FileView, PartReceiptView, ProposalView, ProposedFileView, SetView, UploadView

__all__ = [
    "COMMAND_COMPLETE_FILE",
    "COMMAND_CONFIRM_SET",
    "COMMAND_CREATE_UPLOAD",
    "COMMAND_PUT_PART",
    "RETRYABLE_FILE_REASONS",
    "ComparisonStore",
    "ComparisonUploadService",
    "ConfirmedFile",
    "DeclaredFileRequest",
    "ReadPdf",
    "require_expert",
]

#: The command types are the snake case of the operationId (``scripts/recovery/product_purge.py`` registers them).
COMMAND_CREATE_UPLOAD: Final[str] = "create_comparison_upload"
COMMAND_PUT_PART: Final[str] = "upload_comparison_upload_part"
COMMAND_COMPLETE_FILE: Final[str] = "complete_comparison_upload_file"
COMMAND_CONFIRM_SET: Final[str] = "confirm_comparison_upload_set"

#: Why a file may be sent again: the bytes (or the store) were wrong, not the document. Every other reason a
#: file is ``failed`` is the document's (the envelope refused it) and the same bytes will be refused again.
RETRYABLE_FILE_REASONS: Final[frozenset[str]] = frozenset(
    ("comparison_file_sha256", "comparison_file_size", "staged_upload_lost")
)
_SCHEMA: Final[str] = "cmp-set-proposal/1"
_PDF: Final[str] = "application/pdf"
_BLOB_ROLE: Final = parse_blob_role(ROLE_COMPARISON_PDF)


class ComparisonStore(BlobStore, MultipartStaging, Protocol):
    """The store a comparison upload needs: the verified-blob port and the multipart staging beside it."""


#: ``read_pdf``'s signature: a seekable handle in, the envelope's facts and the stamp facts out.
ReadPdf = Callable[..., PdfReading]


@dataclass(frozen=True, slots=True)
class DeclaredFileRequest:
    display_name: str
    size_bytes: int
    sha256: str
    page_count: int | None = None


@dataclass(frozen=True, slots=True)
class ConfirmedFile:
    file_id: str
    version_label: str | None = None


def require_expert(roles: frozenset[str] | set[str]) -> None:
    """A comparison act is an expert's (ADR-0025 decision 16, ``R-60``): an administrator alone is refused.

    The edge refuses it too (``OPERATION_ROLES``); this is the command's own check, in the transaction that
    would act, so a caller that does not come through the edge is held to the same rule.
    """
    if "expert" not in roles:
        raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:expert")


def _conflict(reason: str, aggregate_type: str | None = None) -> DomainError:
    if aggregate_type is None:
        return DomainError(ErrorCode.CONFLICT, conflict_reason=reason)
    return DomainError(ErrorCode.CONFLICT, conflict_reason=reason, aggregate_type=aggregate_type)


def _not_found(aggregate_type: str) -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=aggregate_type)


def _slug(constraint: str) -> str:
    return "content_" + re.sub(r"[^a-z0-9]+", "_", constraint.lower()).strip("_")[:100]


class ComparisonUploadService:
    """Constructed with its dependencies; it builds no engine and reads no ``DATABASE_URL``.

    ``read`` is the PDF reader (:func:`.reading.read_pdf`); tests pass another to reach a path the real one reaches
    only with a hostile document, and the served application never does.
    """

    __slots__ = ("_store", "_factory", "_documents", "_blobs", "_commands", "_repo", "_read")

    def __init__(
        self,
        store: ComparisonStore,
        *,
        session_factory: sessionmaker[Session] | None = None,
        read: ReadPdf = read_pdf,
    ) -> None:
        self._store = store
        self._factory = session_factory
        self._documents = DocumentRepository()
        self._blobs = BlobMetadataRepository()
        self._commands = CommandRepository()
        self._repo = ComparisonUploadRepository()
        self._read = read

    # -- declare ---------------------------------------------------------------------------------------

    def create_upload(
        self,
        *,
        project_uid: str,
        files: Sequence[DeclaredFileRequest],
        user_uid: str,
        actor_label: str,
        idempotency_key: str,
    ) -> UploadView:
        """Declare a batch of plain PDFs under a project. Nothing is stored yet.

        The limits of decision 9 are refused here, before the first part and before any row exists; an account
        that already has an active batch, or an installation that already has two, is ``conflict``
        (``comparison_upload_active``). A repeat under the same key answers the first batch.
        """
        key = IdempotencyKey(idempotency_key)
        label = _label(actor_label)
        files = [
            DeclaredFileRequest(clean_display_name(f.display_name), f.size_bytes, f.sha256, f.page_count) for f in files
        ]
        if any(not f.display_name for f in files):
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="files", constraint="display_name")
        fingerprint = payload_fingerprint(
            {
                "command": "create_comparison_upload.v1",
                "project_uid": project_uid,
                "files": [[f.display_name, f.size_bytes, f.sha256, f.page_count] for f in files],
            }
        )
        with session_scope(self._factory) as session:
            self._documents.get_project(session, ProjectUid.parse(project_uid))
            claim = self._commands.begin(
                session, command_type=COMMAND_CREATE_UPLOAD, idempotency_key=key, fingerprint=fingerprint
            )
            if isinstance(claim, CommandReplay):
                return self._upload_view(session, str(claim.outcome["upload_id"]), with_files=True)
            assert isinstance(claim, CommandStarted)

            self._repo.lock_creation(session)
            mine, installation = self._repo.count_active(session, user_uid)
            if mine >= ACTIVE_UPLOADS_PER_ACCOUNT or installation >= ACTIVE_UPLOADS_PER_INSTALLATION:
                raise _conflict("comparison_upload_active")
            declared = [DeclaredFile(f.display_name, f.size_bytes, f.page_count) for f in files]
            check_declaration(declared, project_stored_bytes=self._repo.project_stored_bytes(session, project_uid))

            upload_id = new_upload_id()
            self._repo.insert_upload(
                session,
                upload_id=upload_id,
                project_uid=project_uid,
                declared_files=len(files),
                declared_bytes=sum(f.size_bytes for f in files),
                declared_pages=sum(f.page_count or 0 for f in files),
                part_size_bytes=PART_BYTES,
                actor_user_uid=user_uid,
                actor_label=label,
                command_id=str(claim.command_id),
            )
            for item in files:
                self._repo.insert_file(
                    session,
                    file_id=new_file_id(),
                    upload_id=upload_id,
                    display_name=item.display_name,
                    size_bytes=item.size_bytes,
                    sha256=item.sha256,
                    page_count=item.page_count,
                )
            self._commands.succeed(session, claim.command_id, {"upload_id": upload_id})
            return self._upload_view(session, upload_id, with_files=True)

    # -- reads -----------------------------------------------------------------------------------------

    def get_upload(self, *, upload_id: str) -> UploadView:
        with session_scope(self._factory) as session:
            return self._upload_view(session, upload_id, with_files=True)

    def get_proposal(self, *, upload_id: str) -> ProposalView:
        with session_scope(self._factory) as session:
            upload = self._require_upload(session, upload_id)
            sets = self._repo.list_sets(session, upload_id)
            return ProposalView(
                upload_id=upload.upload_id,
                state=upload.state,
                sets=tuple(self._set_view(session_set) for session_set in sets),
            )

    # -- one part --------------------------------------------------------------------------------------

    def put_part(
        self,
        *,
        upload_id: str,
        file_id: str,
        part_number: int,
        content: bytes,
        user_uid: str,
        idempotency_key: str,
    ) -> PartReceiptView:
        """Stage one part of one file.

        The part has a database owner before its bytes are staged, and the file's multipart token is persisted
        before the first part. Sending a part again with the same bytes replays its recorded receipt without
        asking the store; with other bytes it replaces the part (the whole file is verified at completion).
        Refused before the store is asked: a batch that is not uploading or a file that cannot take a part
        (``conflict``/``comparison_upload_state``), a part number the declared size does not need
        (``comparison_part_number``) and a body that is empty, over 16 MiB or, in the middle of a file, not
        exactly one part long (``comparison_part_size``).
        """
        key = IdempotencyKey(idempotency_key)
        size = len(content)
        digest = sha256_of(content)
        fingerprint = payload_fingerprint(
            {
                "command": "upload_comparison_upload_part.v1",
                "upload_id": upload_id,
                "file_id": file_id,
                "part_number": part_number,
                "size_bytes": size,
                "sha256": digest,
            }
        )
        receipt = PartReceiptView(file_id=file_id, part_number=part_number, size_bytes=size, sha256=digest)

        # Transaction 1: decide, and give the bytes an owner before they move.
        with session_scope(self._factory) as session:
            recorded = self._known(session, COMMAND_PUT_PART, key, fingerprint)
            if recorded is not None:
                return receipt
            upload, file = self._load_file(session, upload_id, file_id, lock=True)
            self._require_accepting(upload, file)
            total = parts_needed(file.declared_size_bytes, upload.part_size_bytes)
            if not 1 <= part_number <= total:
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED, field="content", constraint="comparison_part_number"
                )
            if size < 1 or size > PART_BYTES or (part_number < total and size != upload.part_size_bytes) or (
                size > upload.part_size_bytes
            ):
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED, field="content", constraint="comparison_part_size"
                )
            existing = self._repo.get_part(session, file_id, part_number)
            if existing is not None and existing.state == "staged" and existing.sha256 == digest and (
                existing.size_bytes == size
            ):
                self._record(session, COMMAND_PUT_PART, key, fingerprint, {"sha256": digest})
                return receipt
            token = self._own_the_bytes(session, file)
            self._repo.insert_part(session, file_id, part_number)

        # The store. No transaction is open: a part is up to 16 MiB.
        try:
            self._store.begin_multipart(token)
            staged = self._store.upload_part(token, part_number, content)
        except StorageError as exc:
            raise domain_error_from_storage(exc) from None

        # Transaction 2: the receipt, and the key's outcome with it.
        with session_scope(self._factory) as session:
            self._repo.mark_part_staged(
                session, file_id, part_number, size_bytes=staged.size_bytes, sha256=staged.sha256, etag=staged.etag
            )
            self._repo.touch_upload(session, upload_id)
            self._record(session, COMMAND_PUT_PART, key, fingerprint, {"sha256": staged.sha256})
        return PartReceiptView(
            file_id=file_id, part_number=part_number, size_bytes=staged.size_bytes, sha256=staged.sha256
        )

    def _own_the_bytes(self, session: Session, file: FileRow) -> str:
        """The file's token, persisted now if this is its first part (and a failed file moved to ``uploading``).

        The declared Blob row is recorded first: the database owner of the bytes, enumerable by reconciliation
        however the process dies (``storage.public`` documents the sequence).
        """
        if file.multipart_token is not None:
            if file.state == "failed":
                self._repo.restart_file(session, file.file_id)
            return file.multipart_token
        token = new_multipart_token()
        self._blobs.record_declared(
            session,
            declare_blob(
                sha256=file.declared_sha256, size=file.declared_size_bytes, role=_BLOB_ROLE, media_type=_PDF
            ),
        )
        self._repo.persist_token_and_start(session, file.file_id, token=token)
        return token

    # -- one file --------------------------------------------------------------------------------------

    def complete_file(
        self, *, upload_id: str, file_id: str, user_uid: str, idempotency_key: str
    ) -> FileView:
        """Complete one file: verify the whole object, read it, and place it in a set.

        The store assembles the staged parts and compares the object with the declared SHA-256 and size; a
        mismatch removes it, marks the file ``failed`` (``comparison_file_sha256`` / ``comparison_file_size``) and
        answers ``storage_integrity_error``: nothing was published and the client sends the file again. A PDF
        outside the comparison envelope marks it ``failed`` with the envelope's own reason and answers its
        ``validation_failed``; the same bytes would be refused again, so the file is not retried. An already
        verified file is answered as it is.
        """
        key = IdempotencyKey(idempotency_key)
        fingerprint = payload_fingerprint(
            {"command": "complete_comparison_upload_file.v1", "upload_id": upload_id, "file_id": file_id}
        )

        with session_scope(self._factory) as session:
            if self._known(session, COMMAND_COMPLETE_FILE, key, fingerprint) is not None:
                return self._file_view(session, self._load_file(session, upload_id, file_id)[1])
            upload, file = self._load_file(session, upload_id, file_id)
            if file.state == "verified":
                self._record(session, COMMAND_COMPLETE_FILE, key, fingerprint, {"file_id": file_id})
                return self._file_view(session, file)
            self._require_accepting(upload, file)
            if file.blob_id is None:
                parts = self._repo.list_parts(session, file_id)
                needed = parts_needed(file.declared_size_bytes, upload.part_size_bytes)
                if file.multipart_token is None or [p.part_number for p in parts] != list(range(1, needed + 1)) or any(
                    p.state != "staged" for p in parts
                ):
                    raise DomainError(
                        ErrorCode.VALIDATION_FAILED,
                        field="parts",
                        constraint="ascending part numbers from 1 with no gap and no repeat",
                    )
            else:
                parts = ()
        # From here the file is read by value: the session is closed, no lock is held across the store.
        if file.blob_id is None:
            blob_id = self._publish(file, parts, key, fingerprint)
        else:
            blob_id = file.blob_id
        published = self._record_published(file_id, blob_id)

        try:
            reading = self._read_blob(published)
        except DomainError as refusal:
            if refusal.code is not ErrorCode.VALIDATION_FAILED:
                raise
            self._refuse_content(published, refusal, key, fingerprint)
            raise
        except StorageError as exc:
            raise domain_error_from_storage(exc, role=ROLE_COMPARISON_PDF) from None
        mismatch = published.declared_page_count is not None and published.declared_page_count != reading.facts.page_count
        if mismatch:
            refusal = DomainError(
                ErrorCode.VALIDATION_FAILED, field="page_count", constraint="declared_page_count"
            )
            self._refuse_content(published, refusal, key, fingerprint, reason="content_declared_page_count")
            raise refusal

        with session_scope(self._factory) as session:
            upload = self._require_upload(session, upload_id, lock=True)
            file = self._repo.get_file(session, file_id, for_update=True)
            assert file is not None
            if file.state != "verified":
                self._place(session, upload, file, reading)
                file = self._repo.get_file(session, file_id)
                assert file is not None
            self._record(session, COMMAND_COMPLETE_FILE, key, fingerprint, {"file_id": file_id})
            return self._file_view(session, file)

    def _publish(self, file: FileRow, parts: Sequence[Any], key: IdempotencyKey, fingerprint: Any) -> str:
        """Assemble, verify and publish the object; return its Blob identity.

        ``before_publish`` commits ``verifying`` for the declared Blob before the canonical copy exists, so a
        process killed after the publication leaves a Blob the reconciliation names. A store that no longer holds
        the temporary upload but does hold the Blob (the publication finished, the process did not) is
        recognised by the Blob's identity, which is the content's.
        """
        assert file.multipart_token is not None

        def checkpoint(verified: Any) -> None:
            with session_scope(self._factory) as session:
                self._blobs.record_verified(session, verified)

        offered = [
            UploadedPart(part_number=p.part_number, size_bytes=int(p.size_bytes or 0), sha256=p.sha256 or "", etag=p.etag or "")
            for p in parts
        ]
        try:
            published = self._store.complete_multipart(
                file.multipart_token,
                offered,
                declared_sha256=file.declared_sha256,
                declared_size=file.declared_size_bytes,
                role=_BLOB_ROLE,
                media_type=_PDF,
                before_publish=checkpoint,
            )
            return str(published.blob_id)
        except BlobIntegrityError as exc:
            self._fail_integrity(file, exc)
            raise
        except TemporaryBlobLostError as exc:
            declared = declare_blob(
                sha256=file.declared_sha256, size=file.declared_size_bytes, role=_BLOB_ROLE, media_type=_PDF
            )
            try:
                self._store.inspect(declared.blob_id)
            except BlobNotFoundError:
                self._fail_file(file, "staged_upload_lost")
                raise domain_error_from_storage(exc) from None
            except StorageError as inner:
                raise domain_error_from_storage(inner) from None
            return str(declared.blob_id)
        except StorageError as exc:
            raise domain_error_from_storage(exc) from None

    def _fail_integrity(self, file: FileRow, exc: BlobIntegrityError) -> None:
        """The assembled object did not match its declaration: the store removed it, so the parts no longer
        exist and the file is ``failed`` until the client sends it again. The refusal is the contract's."""
        by_size = "expected_size" in exc.details
        self._fail_file(file, "comparison_file_size" if by_size else "comparison_file_sha256")
        if by_size:
            raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="comparison_file_size") from None
        details = {k: v for k, v in exc.details.items() if k in ("expected_sha256", "actual_sha256")}
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, **details) from None

    def _fail_file(self, file: FileRow, reason: str) -> None:
        with session_scope(self._factory) as session:
            current = self._repo.get_file(session, file.file_id, for_update=True)
            if current is not None and current.state != "failed":
                self._repo.mark_file_failed(session, file.file_id, reason=reason)
            self._repo.delete_parts(session, file.file_id)
            self._repo.touch_upload(session, file.upload_id)

    def _record_published(self, file_id: str, blob_id: str) -> FileRow:
        """``available`` for the Blob and its identity on the file, in one transaction."""
        with session_scope(self._factory) as session:
            file = self._repo.get_file(session, file_id, for_update=True)
            assert file is not None
            self._blobs.mark_available(session, parse_blob_id(blob_id))
            if file.blob_id is None:
                self._repo.record_blob(session, file_id, blob_id=blob_id)
                file = self._repo.get_file(session, file_id)
                assert file is not None
            return file

    def _read_blob(self, file: FileRow) -> PdfReading:
        """Spool the verified object and read it in the ceilinged children."""
        assert file.blob_id is not None
        chunks = self._store.open_stream(
            parse_blob_id(file.blob_id),
            expected_sha256=file.declared_sha256,
            expected_size=file.declared_size_bytes,
        )
        with tempfile.TemporaryFile() as spool:
            try:
                for chunk in chunks:
                    spool.write(chunk)
            finally:
                chunks.close()
            spool.flush()
            spool.seek(0)
            return self._read(spool)

    def _refuse_content(
        self,
        file: FileRow,
        refusal: DomainError,
        key: IdempotencyKey,
        fingerprint: Any,
        *,
        reason: str | None = None,
    ) -> None:
        """The document is outside the envelope: mark the file ``failed`` for good and record the refusal.

        The same bytes would be refused again, so the key's outcome is the refusal (a repeat answers it), and
        the batch counts the file as settled so the rest of it can be proposed.
        """
        slug = reason or _slug(str(refusal.detail_fields.get("constraint", "refused")))
        with session_scope(self._factory) as session:
            upload = self._require_upload(session, file.upload_id, lock=True)
            current = self._repo.get_file(session, file.file_id, for_update=True)
            assert current is not None
            if current.state != "failed":
                self._repo.mark_file_failed(session, file.file_id, reason=slug)
                self._repo.complete_parts(session, file.file_id)
            self._finalize_if_settled(session, upload)
            claim = self._commands.begin(
                session, command_type=COMMAND_COMPLETE_FILE, idempotency_key=key, fingerprint=fingerprint
            )
            if isinstance(claim, CommandStarted):
                self._commands.fail(session, claim.command_id, refusal.code)

    # -- placement and the proposal --------------------------------------------------------------------

    def _place(self, session: Session, upload: UploadRow, file: FileRow, reading: PdfReading) -> None:
        """A verified file joins the set of its designation, and the batch is proposed when all are settled."""
        stamp = reading.stamp
        hint = name_hint(file.display_name)
        key = grouping_key(stamp, hint)
        entry = {"display_name": file.display_name, "stamp": stamp.to_json()}
        target = self._repo.find_set_by_key(session, upload.upload_id, key)
        if target is None:
            created = self._repo.insert_set(
                session,
                set_id=new_set_id(),
                upload_id=upload.upload_id,
                proposal={"schema": _SCHEMA, "grouping_key": key, "files": {file.file_id: entry}},
            )
            if self._repo.count_sets(session, upload.upload_id) > MAX_SETS:
                # The stamps group the batch into more sets than the limit of decision 9 allows: the surplus set
                # is refused, with its files, rather than silently merged into another.
                self._repo.set_state(session, created.set_id, to_state="failed", failure_reason="comparison_sets_limit")
            target = created
        else:
            proposal = dict(target.proposal)
            files = dict(proposal.get("files", {}))
            files[file.file_id] = entry
            proposal["files"] = files
            self._repo.write_set_proposal(
                session,
                target.set_id,
                proposal=proposal,
                designation=target.designation,
                project_stage=target.project_stage,
                section_code=target.section_code,
                existing_document_uid=target.existing_document_uid,
            )
        self._refresh_set_columns(session, target.set_id)
        self._repo.mark_file_verified(session, file.file_id, set_id=target.set_id)
        self._repo.complete_parts(session, file.file_id)
        self._repo.touch_upload(session, upload.upload_id)
        self._finalize_if_settled(session, upload)

    def _refresh_set_columns(self, session: Session, set_id: str) -> None:
        """The set's designation, stage and section follow the files it holds (they are proposals until confirmed)."""
        current = self._repo.get_set(session, set_id)
        assert current is not None
        proposed = propose_set(_entries_of(current))
        self._repo.write_set_proposal(
            session,
            set_id,
            proposal=current.proposal,
            designation=proposed.designation,
            project_stage=proposed.project_stage,
            section_code=proposed.section_code,
            existing_document_uid=current.existing_document_uid,
        )

    def _finalize_if_settled(self, session: Session, upload: UploadRow) -> None:
        """When every file of the batch is settled the batch is ``proposed`` and its sets await the user.

        Settled: verified, or failed for a reason the same bytes will not escape (a refused document). A file that
        failed by its integrity, or has not arrived, keeps the batch ``uploading``: it can be sent again, and a
        batch that is already proposed cannot go back. A batch in which nothing was admitted to any set is
        ``completed`` at once: there is nothing for the user to confirm.
        """
        current = self._repo.get_upload(session, upload.upload_id, for_update=True)
        assert current is not None
        if current.state != "uploading":
            return
        states = self._repo.file_states_of(session, upload.upload_id)
        if not all(
            state == "verified" or (state == "failed" and reason not in RETRYABLE_FILE_REASONS)
            for state, reason in states
        ):
            return
        sets = self._repo.list_sets(session, upload.upload_id)
        for item in sets:
            if item.state != "uploading":
                continue
            proposed = propose_set(_entries_of(item))
            self._repo.write_set_proposal(
                session,
                item.set_id,
                proposal=item.proposal,
                designation=proposed.designation,
                project_stage=proposed.project_stage,
                section_code=proposed.section_code,
                existing_document_uid=self._existing_document(session, upload.project_uid, proposed.designation),
            )
            self._repo.set_state(session, item.set_id, to_state="reading")
            self._repo.set_state(session, item.set_id, to_state="needs_confirmation")
        self._repo.set_upload_state(session, upload.upload_id, to_state="proposed")
        if not [item for item in sets if item.state != "failed"]:
            self._repo.set_upload_state(session, upload.upload_id, to_state="completed")

    def _existing_document(self, session: Session, project_uid: str, designation: str | None) -> str | None:
        """The document of the project this designation may belong to, as an offer the user confirms.

        A set an earlier batch confirmed under the same designation, else a document whose title is it.
        Never a document of another project.
        """
        if not designation:
            return None
        folded = fold_designation(designation)
        for stored, document_uid in self._repo.done_set_documents(session, project_uid):
            if fold_designation(stored) == folded:
                return document_uid
        for document_uid, title in self._documents.list_document_titles(session, ProjectUid.parse(project_uid)):
            if fold_designation(title) == folded:
                return str(document_uid)
        return None

    # -- confirmation ----------------------------------------------------------------------------------

    def confirm_set(
        self,
        *,
        upload_id: str,
        set_id: str,
        files: Sequence[ConfirmedFile],
        designation: str | None,
        existing_document_uid: str | None,
        project_stage: str | None,
        section_code: str | None,
        user_uid: str,
        actor_roles: frozenset[str],
        idempotency_key: str,
    ) -> SetView:
        """The user's final word on one set; the document and one version per file are made in this transaction.

        ``files`` is the membership **in order** (the array order is the version order), each with the label the
        user chose. A file listed twice, a file of another set or a file of the set that is not listed is
        ``validation_failed`` (``comparison_set_members``); a set that is not awaiting confirmation is
        ``conflict`` (``comparison_set_state``). The stage and the section, given together, classify every new
        version (the first classification of a version stands); they are never inferred. The versions are
        ``comparison_pdf`` versions, and none of them becomes the current version of a document that has a
        portal version (decision 11).
        """
        require_expert(actor_roles)
        key = IdempotencyKey(idempotency_key)
        fingerprint = payload_fingerprint(
            {
                "command": "confirm_comparison_upload_set.v1",
                "upload_id": upload_id,
                "set_id": set_id,
                "files": [[f.file_id, f.version_label] for f in files],
                "designation": designation,
                "existing_document_uid": existing_document_uid,
                "project_stage": project_stage,
                "section_code": section_code,
            }
        )
        with session_scope(self._factory) as session:
            upload = self._require_upload(session, upload_id, lock=True)
            row = self._repo.get_set(session, set_id, for_update=True)
            if row is None or row.upload_id != upload_id:
                raise _not_found("ComparisonUploadSet")
            claim = self._commands.begin(
                session, command_type=COMMAND_CONFIRM_SET, idempotency_key=key, fingerprint=fingerprint
            )
            if isinstance(claim, CommandReplay):
                again = self._repo.get_set(session, set_id)
                assert again is not None
                return self._set_view(again)
            assert isinstance(claim, CommandStarted)
            if row.state != "needs_confirmation":
                raise _conflict("comparison_set_state")

            members = {item.file_id: item for item in self._repo.files_of_set(session, set_id)}
            listed = [item.file_id for item in files]
            if len(set(listed)) != len(listed) or set(listed) != set(members):
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED, field="files", constraint="comparison_set_members"
                )
            if (project_stage is None) != (section_code is None):
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED,
                    field="project_stage" if project_stage is None else "section_code",
                    constraint="required_together",
                )
            if existing_document_uid is not None and self._documents.require_document(
                session, _document_uid(existing_document_uid)
            ) != ProjectUid.parse(upload.project_uid):
                raise _not_found("Document")

            proposed = propose_set(_entries_of(row))
            confirmed_designation = designation if designation is not None else proposed.designation
            self._repo.confirm_set(
                session,
                set_id,
                designation=confirmed_designation,
                existing_document_uid=existing_document_uid,
                project_stage=project_stage,
                section_code=section_code,
                confirmed_by_user_uid=user_uid,
            )
            self._repo.set_state(session, set_id, to_state="ready")
            self._repo.set_state(session, set_id, to_state="admitting")

            proposed_labels = {item.file_id: item.version_label for item in proposed.files}
            proposed_order = [item.file_id for item in proposed.files]
            order_source = "proposal" if listed == proposed_order else "expert"
            ordered = [
                ConfirmedFile(item.file_id, item.version_label or proposed_labels.get(item.file_id))
                for item in files
            ]
            document_uid, version_uids = self._admit(
                session,
                upload=upload,
                row=row,
                members=members,
                ordered=ordered,
                designation=confirmed_designation,
                existing_document_uid=existing_document_uid,
                project_stage=project_stage,
                section_code=section_code,
                user_uid=user_uid,
                command_id=str(claim.command_id),
                order_source=order_source,
            )
            confirmed = {
                "files": [
                    {
                        "file_id": item.file_id,
                        "position": position,
                        "version_label": item.version_label,
                        "version_uid": version_uids[position - 1],
                    }
                    for position, item in enumerate(ordered, start=1)
                ],
                "order_source": order_source,
            }
            proposal = dict(row.proposal)
            proposal["confirmed"] = confirmed
            self._repo.finish_set(session, set_id, document_uid=document_uid, proposal=proposal)
            self._repo.set_state(session, set_id, to_state="done")
            self._complete_if_all_terminal(session, upload_id)
            self._commands.succeed(session, claim.command_id, {"set_id": set_id, "document_uid": document_uid})
            done = self._repo.get_set(session, set_id)
            assert done is not None
            return self._set_view(done)

    def _admit(
        self,
        session: Session,
        *,
        upload: UploadRow,
        row: SetRow,
        members: Mapping[str, FileRow],
        ordered: Sequence[ConfirmedFile],
        designation: str | None,
        existing_document_uid: str | None,
        project_stage: str | None,
        section_code: str | None,
        user_uid: str,
        command_id: str,
        order_source: str,
    ) -> tuple[str, list[str]]:
        """The document, a ``comparison_pdf`` version per file in the confirmed order, and the order revision."""
        project = ProjectUid.parse(upload.project_uid)
        if existing_document_uid is not None:
            document_uid = _document_uid(existing_document_uid)
        else:
            first = members[ordered[0].file_id]
            title = designation or source_filename_of(first.display_name).rsplit(".", 1)[0] or "Документ"
            document_uid = self._documents.create_document(session, project, title[:400], section_code)
        earlier = [str(item.version_uid) for item in reversed(self._documents.list_versions(session, document_uid))]

        version_uids: list[str] = []
        for item in ordered:
            file = members[item.file_id]
            assert file.blob_id is not None
            facts = FileStamp.from_json(row.proposal["files"][file.file_id]["stamp"])
            version_uid = self._documents.publish_version(
                session,
                document_uid=document_uid,
                media_type=_PDF,
                byte_size=file.declared_size_bytes,
                sha256=file.declared_sha256,
                page_count=facts.page_count,
                source_filename=source_filename_of(file.display_name),
                entries=(
                    ManifestEntry(
                        role=MANIFEST_ROLE_COMPARISON_PDF,
                        blob_id=parse_blob_id(file.blob_id),
                        sha256=file.declared_sha256,
                        size_bytes=file.declared_size_bytes,
                        media_type=_PDF,
                    ),
                ),
                upload_kind=UPLOAD_KIND_COMPARISON_PDF,
            )
            version_uids.append(str(version_uid))
            if project_stage is not None and section_code is not None:
                self._documents.insert_classification(
                    session,
                    version_uid=version_uid,
                    project_stage=project_stage,
                    section_code=section_code,
                    confirmed_by_user_uid=user_uid,
                )

        # The order revision: what the document's order already was, then these versions in the confirmed order.
        self._repo.lock_document_order(session, str(document_uid))
        latest = self._repo.latest_order(session, str(document_uid))
        before = list(latest.version_uids) if latest else []
        before += [uid for uid in earlier if uid not in before]
        self._repo.insert_order(
            session,
            order_id=new_order_id(),
            project_uid=upload.project_uid,
            document_uid=str(document_uid),
            revision_no=(latest.revision_no if latest else 0) + 1,
            version_uids=before + version_uids,
            source=order_source,
            actor_user_uid=user_uid,
            actor_label=_label(upload.actor_label),
            command_id=command_id,
        )
        return str(document_uid), version_uids

    def _complete_if_all_terminal(self, session: Session, upload_id: str) -> None:
        """The batch is ``completed`` once no set is left that the user (or a retry) can still act on."""
        states = self._repo.set_states_of(session, upload_id)
        if states and all(state in ("done", "excluded") for state in states):
            current = self._repo.get_upload(session, upload_id, for_update=True)
            if current is not None and current.state == "proposed":
                self._repo.set_upload_state(session, upload_id, to_state="completed")

    # -- helpers ---------------------------------------------------------------------------------------

    def _require_upload(self, session: Session, upload_id: str, *, lock: bool = False) -> UploadRow:
        row = self._repo.get_upload(session, upload_id, for_update=lock)
        if row is None:
            raise _not_found("ComparisonUpload")
        return row

    def _load_file(
        self, session: Session, upload_id: str, file_id: str, *, lock: bool = False
    ) -> tuple[UploadRow, FileRow]:
        upload = self._require_upload(session, upload_id, lock=lock)
        file = self._repo.get_file(session, file_id, for_update=lock)
        if file is None or file.upload_id != upload_id:
            raise _not_found("ComparisonUploadFile")
        return upload, file

    @staticmethod
    def _require_accepting(upload: UploadRow, file: FileRow) -> None:
        """A part or a completion is accepted while the batch is uploading and the file can still take bytes."""
        if upload.state != "uploading":
            raise _conflict("comparison_upload_state")
        if file.state == "verified" or file.blob_id is not None and file.state == "failed":
            raise _conflict("comparison_upload_state")
        if file.state == "failed" and file.failure_reason not in RETRYABLE_FILE_REASONS:
            raise _conflict("comparison_upload_state")

    def _known(
        self, session: Session, command_type: str, key: IdempotencyKey, fingerprint: Any
    ) -> Mapping[str, Any] | None:
        """The recorded outcome of this key, ``None`` when it is new; a different payload or a running one refuses."""
        existing: CommandRecord | None = self._commands.find(
            session, command_type=command_type, idempotency_key=key
        )
        if existing is None:
            return None
        if existing.payload_fingerprint != fingerprint:
            raise DomainError(ErrorCode.IDEMPOTENCY_KEY_REUSE, command_type=command_type)
        if existing.state == "succeeded" and existing.outcome is not None:
            return dict(existing.outcome)
        if existing.state == "in_progress":
            raise DomainError(ErrorCode.IDEMPOTENCY_KEY_IN_PROGRESS, command_type=command_type)
        if existing.state == "failed" and existing.error_code:
            raise DomainError(ErrorCode(existing.error_code))
        raise DomainError(ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=command_type)

    def _record(
        self, session: Session, command_type: str, key: IdempotencyKey, fingerprint: Any, outcome: Mapping[str, Any]
    ) -> None:
        """Claim the key and record the outcome in the caller's transaction (a concurrent winner is a replay)."""
        claim = self._commands.begin(
            session, command_type=command_type, idempotency_key=key, fingerprint=fingerprint
        )
        if isinstance(claim, CommandStarted):
            self._commands.succeed(session, claim.command_id, outcome)

    def _upload_view(self, session: Session, upload_id: str, *, with_files: bool) -> UploadView:
        upload = self._require_upload(session, upload_id)
        files: tuple[FileView, ...] | None = None
        if with_files:
            staged = self._repo.staged_part_counts(session, upload_id)
            files = tuple(
                _file_view(row, staged.get(row.file_id, 0)) for row in self._repo.list_files(session, upload_id)
            )
        return UploadView(
            upload_id=upload.upload_id,
            project_uid=upload.project_uid,
            state=upload.state,
            part_size_bytes=upload.part_size_bytes,
            declared_files=upload.declared_files,
            declared_bytes=upload.declared_bytes,
            created_at=upload.created_at,
            updated_at=upload.updated_at,
            files=files,
        )

    def _file_view(self, session: Session, file: FileRow) -> FileView:
        return _file_view(file, self._repo.staged_part_counts(session, file.upload_id).get(file.file_id, 0))

    def _set_view(self, row: SetRow) -> SetView:
        entries = _entries_of(row)
        confirmed = row.proposal.get("confirmed")
        if entries:
            proposed = propose_set(entries)
        else:  # pragma: no cover - a set exists because a file was placed in it
            proposed = SetProposal(None, None, None, (), ())
        if isinstance(confirmed, dict) and row.state in ("ready", "admitting", "done"):
            files = tuple(
                ProposedFileView(str(item["file_id"]), int(item["position"]), str(item["version_label"]))
                for item in confirmed["files"]
            )
        else:
            files = tuple(ProposedFileView(item.file_id, item.position, item.version_label) for item in proposed.files)
        return SetView(
            set_id=row.set_id,
            state=row.state,
            files=files,
            designation=row.designation if row.designation is not None else proposed.designation,
            existing_document_uid=row.existing_document_uid,
            project_stage=row.project_stage if row.project_stage is not None else proposed.project_stage,
            section_code=row.section_code if row.section_code is not None else proposed.section_code,
            warnings=proposed.warnings,
            failure_reason=row.failure_reason,
            document_uid=row.document_uid,
        )


def _file_view(row: FileRow, staged: int) -> FileView:
    return FileView(
        file_id=row.file_id,
        display_name=row.display_name,
        size_bytes=row.declared_size_bytes,
        sha256=row.declared_sha256,
        state=row.state,
        parts_staged=staged,
        set_id=row.set_id,
        failure_reason=row.failure_reason,
    )


def _entries_of(row: SetRow) -> list[FileEntry]:
    """The proposal's input: the stamp facts of every file the set holds, from the set's own record."""
    files = row.proposal.get("files", {})
    return [
        FileEntry(
            file_id=file_id,
            display_name=str(item["display_name"]),
            stamp=FileStamp.from_json(item["stamp"]),
            hint=name_hint(str(item["display_name"])),
        )
        for file_id, item in files.items()
    ]


def _document_uid(value: str) -> DocumentUid:
    return DocumentUid.parse(value)


def _label(value: str) -> str:
    """The actor's label as the table stores it: 1 to 128 characters, no surrounding whitespace."""
    cleaned = " ".join(value.split())[:128].strip()
    if not cleaned:
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="the actor has no display label")
    return cleaned
