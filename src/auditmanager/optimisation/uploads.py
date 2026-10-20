"""Uploading a price list: one immutable revision, bound to its file's Blob, or a refusal.

The order is the design, as in ``auditmanager.ingest.service`` (``P2-META-01``), with the
Blob's declared intent made durable **before** the first object-store write
(:class:`~auditmanager.storage.public.DurablePublicationStore`):

===== ================================================ ==========================
step   what happens                                     committed when it ends
===== ================================================ ==========================
0      the actor holds ``expert``; the project exists   nothing
1      the file is parsed (bounded, deterministic)      nothing; a refusal stops here
2      claim the idempotency key                        ``command_record`` in_progress
3      record the Blob ``temporary``                    **committed** (the breadcrumb)
4      stage the bytes under the command's identity     nothing canonical
5      verify; record the Blob ``verifying``            **committed**
6      publish to the canonical location                the object exists
7      Blob ``available`` + revision + every position   **committed**, one
       + command ``succeeded``                          transaction
===== ================================================ ==========================

**The database is canonical.** The bytes mean nothing until step 7 commits a revision that
names them; a crash between steps 3 and 7 leaves a ``temporary`` or ``verifying`` Blob row
(enumerable without listing the bucket) and an ``in_progress`` command record, and no
revision. Step 7 is one transaction and the schema refuses a revision whose positions are not
all there (``am_require_price_list_positions``) or whose Blob is not ``available`` with the
recorded digest and size (``am_check_price_list_blob``).

**Idempotency.** The fingerprint covers the project, the actor, the file's digest and size,
the file name and the declared default currency. The same key with the same payload answers
the stored revision and creates nothing; the same key with another payload is
``idempotency_key_reuse``. Uploading the same bytes again under a **new** key is a new
revision: the Blob is content-addressed and shared, the revision is not.

Nothing here retries; a failure after step 2 terminates the command record ``failed`` with
its catalog code, so a repeat of the key is answered rather than re-run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, BinaryIO, Final, Mapping

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import AccountRepository
from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest.public import (
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from auditmanager.sections.public import section_names
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode, from_internal
from auditmanager.shared.identity import IdempotencyKey, IdentityError, ProjectUid
from auditmanager.storage.public import (
    BlobDeclaration,
    BlobMetadataRepository,
    BlobStore,
    DurablePublicationStore,
    StorageError,
    VerifiedBlob,
    parse_blob_id,
    parse_blob_role,
    sha256_of,
)

from .identity import PriceListId
from .parsing import ParseOutcome, parse_price_list
from .parsing.limits import MAX_BYTES
from .policy import AGGREGATE_PRICE_LIST, parse_currency_code, require_expert
from .repository import OptimisationRepository, PriceListRevisionRecord

__all__ = [
    "COMMAND_TYPE_UPLOAD_PRICE_LIST",
    "MAX_SOURCE_FILENAME",
    "ROLE_PRICE_LIST_SOURCE",
    "PriceListUploadOutcome",
    "PriceListUploads",
]

#: Matches ``ck_command_record_command_type`` (lowercase snake_case, 3-64 characters).
COMMAND_TYPE_UPLOAD_PRICE_LIST: Final[str] = "upload_price_list"
#: The role recorded with the uploaded file's Blob (historical metadata, ``R-76``).
ROLE_PRICE_LIST_SOURCE: Final[str] = "price_list_source"
MAX_SOURCE_FILENAME: Final[int] = 255

_PLAIN_BASENAME: Final[re.Pattern[str]] = re.compile(r"^[^\x00-\x1f/\\]+$")


@dataclass(frozen=True, slots=True)
class PriceListUploadOutcome:
    """The stored revision, and whether it was answered from an earlier identical request."""

    revision: PriceListRevisionRecord
    replayed: bool


def _validate_filename(value: Any) -> str:
    """A plain base name kept for display only -- never an identity, a key or a path."""
    if not isinstance(value, str) or not value.strip():
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="source_filename", constraint="non_empty"
        )
    candidate = value.strip()
    if len(candidate) > MAX_SOURCE_FILENAME:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            field="source_filename",
            constraint=f"char_length <= {MAX_SOURCE_FILENAME}",
        )
    if candidate in (".", "..") or not _PLAIN_BASENAME.match(candidate):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="source_filename", constraint="plain_base_name"
        )
    return candidate


def _read_bounded(content: bytes | BinaryIO) -> bytes:
    """The upload's bytes, reading at most one byte past the bound so oversize is seen."""
    if isinstance(content, (bytes, bytearray)):
        data = bytes(content)
    else:
        data = content.read(MAX_BYTES + 1)
    return data


def _domain_error_from_storage(exc: StorageError) -> DomainError:
    """A storage failure as the catalog code it carries, details narrowed to the code's own."""
    code = from_internal(getattr(exc, "code", "") or "")
    allowed = code.safe_detail_keys
    details = {
        key: value
        for key, value in dict(exc.details).items()
        if key in allowed and isinstance(value, (str, int, float, bool))
    }
    if "role" in allowed:
        details["role"] = ROLE_PRICE_LIST_SOURCE
    return DomainError(code, **details)


class PriceListUploads:
    """The upload command. Owns its units of work, like ``IngestService``; builds no engine."""

    __slots__ = ("_store", "_factory", "_repository", "_documents", "_accounts", "_blobs", "_commands")

    def __init__(
        self, store: BlobStore, *, session_factory: sessionmaker[Session] | None = None
    ) -> None:
        self._store = store
        self._factory = session_factory
        self._repository = OptimisationRepository()
        self._documents = DocumentRepository()
        self._accounts = AccountRepository()
        self._blobs = BlobMetadataRepository()
        self._commands = CommandRepository()

    def upload(
        self,
        *,
        project_uid: str,
        content: bytes | BinaryIO,
        source_filename: str,
        idempotency_key: str,
        actor_uid: str,
        default_currency: str | None = None,
    ) -> PriceListUploadOutcome:
        """Store one price list as the project's newest revision, or explain why not.

        Order of refusals: ``permission_denied`` (no ``expert`` role), ``validation_failed``
        (identifiers, file name, key, currency), ``not_found`` (``Project``), the file's own
        refusals (``validation_failed``, ``field: content``), then the idempotency answers.
        """
        with session_scope(self._factory) as session:
            require_expert(
                self._accounts.roles_of(session, actor_uid),
                aggregate_type=AGGREGATE_PRICE_LIST,
                act="upload a price list",
            )
        try:
            project = ProjectUid.parse(project_uid)
        except IdentityError:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="project_uid", constraint="pattern"
            ) from None
        filename = _validate_filename(source_filename)
        try:
            key = IdempotencyKey(idempotency_key)
        except IdentityError:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="idempotency_key", constraint="pattern"
            ) from None
        currency = parse_currency_code(default_currency)
        with session_scope(self._factory) as session:
            self._documents.get_project(session, project)

        data = _read_bounded(content)
        sha256 = sha256_of(data)
        fingerprint = payload_fingerprint(
            {
                "command": "upload_price_list.v1",
                "project_uid": str(project),
                "actor_uid": actor_uid,
                "sha256": sha256,
                "size_bytes": len(data),
                "source_filename": filename,
                "default_currency": currency,
            }
        )
        # A key already claimed is answered before the file is parsed again: a repeat of a
        # stored upload replays it even if the parser has since changed what it accepts.
        with session_scope(self._factory) as session:
            if self._commands.find(
                session, command_type=COMMAND_TYPE_UPLOAD_PRICE_LIST, idempotency_key=key
            ) is not None:
                answered = self._claim(session, key, fingerprint)
                if not isinstance(answered, CommandReplay):  # pragma: no cover - begin() raises
                    raise DomainError(
                        ErrorCode.IDEMPOTENCY_KEY_STALE,
                        command_type=COMMAND_TYPE_UPLOAD_PRICE_LIST,
                    )
                return PriceListUploadOutcome(
                    revision=self._replayed(answered.outcome), replayed=True
                )

        parsed = parse_price_list(data, default_currency=currency, section_names=section_names())
        with session_scope(self._factory) as session:
            claim = self._claim(session, key, fingerprint)
        if isinstance(claim, CommandReplay):
            return PriceListUploadOutcome(revision=self._replayed(claim.outcome), replayed=True)
        assert isinstance(claim, CommandStarted)

        try:
            published = self._publication_store(upload_token=str(claim.command_id)).put_blob(
                data,
                declared_sha256=sha256,
                declared_size=len(data),
                role=parse_blob_role(ROLE_PRICE_LIST_SOURCE),
                media_type=parsed.media_type,
            )
            with session_scope(self._factory) as session:
                record = self._commit(
                    session,
                    claim=claim,
                    project_uid=str(project),
                    actor_uid=actor_uid,
                    blob_id=str(published.blob_id),
                    sha256=sha256,
                    size_bytes=len(data),
                    filename=filename,
                    currency=currency,
                    parsed=parsed,
                )
            return PriceListUploadOutcome(revision=record, replayed=False)
        except Exception as exc:
            failure = self._as_domain_error(exc)
            self._record_failure(claim, failure)
            raise failure from None

    # -- internals -----------------------------------------------------------

    def _claim(
        self, session: Session, key: IdempotencyKey, fingerprint: Any
    ) -> CommandStarted | CommandReplay:
        return self._commands.begin(
            session,
            command_type=COMMAND_TYPE_UPLOAD_PRICE_LIST,
            idempotency_key=key,
            fingerprint=fingerprint,
        )

    def _publication_store(self, *, upload_token: str) -> DurablePublicationStore:
        def before_stage(declaration: BlobDeclaration) -> str:
            # Committed before the first external write: a process lost while staging leaves
            # a ``temporary`` row naming exactly this content.
            with session_scope(self._factory) as session:
                self._blobs.record_declared(session, declaration)
            return upload_token

        def before_publish(verified: VerifiedBlob) -> None:
            with session_scope(self._factory) as session:
                self._blobs.record_verified(session, verified)

        return DurablePublicationStore(
            self._store, before_stage=before_stage, before_publish=before_publish
        )

    def _commit(
        self,
        session: Session,
        *,
        claim: CommandStarted,
        project_uid: str,
        actor_uid: str,
        blob_id: str,
        sha256: str,
        size_bytes: int,
        filename: str,
        currency: str | None,
        parsed: ParseOutcome,
    ) -> PriceListRevisionRecord:
        """Step 7: the Blob available, the revision with all its positions, the outcome."""
        # The role is read again in the writing transaction: an expert stripped of the role
        # while the file was being stored does not get a revision written in their name.
        require_expert(
            self._accounts.roles_of(session, actor_uid),
            aggregate_type=AGGREGATE_PRICE_LIST,
            act="upload a price list",
        )
        self._blobs.mark_available(session, parse_blob_id(blob_id))
        self._repository.lock_project_price_lists(session, project_uid)
        price_list_id = PriceListId.new()
        self._repository.insert_price_list(
            session,
            price_list_id=price_list_id,
            project_uid=project_uid,
            revision_number=self._repository.next_price_list_number(session, project_uid),
            uploaded_by_user_uid=actor_uid,
            blob_id=blob_id,
            sha256=sha256,
            size_bytes=size_bytes,
            media_type=parsed.media_type,
            source_format=parsed.source_format,
            source_filename=filename,
            default_currency=currency,
            parse_report=parsed.report,
            data_row_count=parsed.data_row_count,
            accepted_row_count=parsed.accepted_row_count,
            skipped_row_count=parsed.skipped_row_count,
        )
        self._repository.insert_positions(session, price_list_id, parsed.positions)
        self._commands.succeed(
            session,
            claim.command_id,
            {"price_list_id": str(price_list_id), "blob_id": blob_id},
        )
        record = self._repository.get_price_list(session, str(price_list_id))
        if record is None:  # pragma: no cover - inserted above in this transaction
            raise DomainError(ErrorCode.INTERNAL_ERROR, message="the new price list is not readable")
        return record

    def _replayed(self, outcome: Mapping[str, Any]) -> PriceListRevisionRecord:
        raw = outcome.get("price_list_id")
        if not isinstance(raw, str):
            raise DomainError(
                ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=COMMAND_TYPE_UPLOAD_PRICE_LIST
            )
        with session_scope(self._factory) as session:
            record = self._repository.get_price_list(session, raw)
        if record is None:  # pragma: no cover - a succeeded command names a committed row
            raise DomainError(
                ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=COMMAND_TYPE_UPLOAD_PRICE_LIST
            )
        return record

    @staticmethod
    def _as_domain_error(exc: BaseException) -> DomainError:
        if isinstance(exc, DomainError):
            return exc
        if isinstance(exc, StorageError):
            return _domain_error_from_storage(exc)
        # An unclassified fault; the original stays in protected diagnostics only.
        return DomainError(ErrorCode.INTERNAL_ERROR)

    def _record_failure(self, claim: CommandStarted, failure: DomainError) -> None:
        """Terminate the command record in its own unit of work, so a repeat is answered."""
        try:
            with session_scope(self._factory) as session:
                self._commands.fail(session, claim.command_id, failure.code)
        except Exception:  # noqa: BLE001 - the original failure is the one that must surface
            pass
