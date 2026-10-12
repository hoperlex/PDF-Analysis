"""MinIO / S3-compatible BlobStore adapter.

Implements :class:`~auditmanager.storage.port.BlobStore` against the S3 API.
MinIO is what runs locally; nothing here depends on MinIO specifically.

The sequence
------------
``stage_temporary`` puts bytes under a temporary key. ``verify_temporary``
reads them *back out of the store* and recomputes size and SHA-256 -- reading
back is the point, because it is the only thing that catches a truncated or
corrupted upload rather than trusting what the caller believed it sent. Only
then does ``publish`` copy the object under its canonical key.

If verification fails, the temporary object is deleted and a typed
:class:`BlobIntegrityError` is raised. No canonical object was ever created:
publication is a separate later step, so there is nothing to roll back and no
window in which a half-published blob is visible.

Streamed reads
--------------
``open_stream`` (`W55A-CONTENT-01`, ``R-115``) issues one ``GetObject`` -- with
``Range`` for a window -- and checks its headers before it returns, then hands
back a generator that reads the body a chunk at a time. A whole read hashes as it
goes and holds its last chunk back until the digest is the caller's declared one;
a windowed read transfers the window and nothing else.

Error translation
-----------------
Every ``botocore`` failure is translated into one of this package's typed
errors. Botocore messages are never re-raised as text, and no translated
message carries a bucket or a key -- the error classes make that structurally
impossible, see :mod:`auditmanager.storage.errors`.
"""

from __future__ import annotations

import hashlib
import logging
import re
import secrets
from datetime import datetime, timezone
from typing import Any, Final

import boto3
from botocore.client import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionError as BotoConnectionError,
    EndpointConnectionError,
    NoCredentialsError,
)

from . import _object_layout as layout
from .errors import (
    BlobAttributeConflictError,
    BlobIntegrityError,
    BlobMetadataInvalidError,
    BlobNotFoundError,
    ChecksumMismatchError,
    SizeMismatchError,
    StorageBucketMissingError,
    StorageError,
    StorageCredentialRefusedError,
    StorageUnavailableError,
    TemporaryBlobLostError,
)
from .models import (
    BlobId,
    BlobRole,
    PublishedBlob,
    TemporaryBlob,
    VerifiedBlob,
    derive_blob_id,
    parse_blob_role,
)
from .port import STREAM_CHUNK_BYTES, BlobChunks, BlobSource
from .settings import BUCKET_VAR, S3StorageSettings

_log = logging.getLogger(__name__)

_CHUNK: Final[int] = 1024 * 1024
_UPLOAD_TOKEN_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9._~-]{1,128}$")

# User metadata names. S3 lower-cases and prefixes these with `x-amz-meta-`.
_META_BLOB_ID: Final[str] = "blob-id"
_META_ROLE: Final[str] = "blob-role"
_META_SHA256: Final[str] = "content-sha256"
_META_SIZE: Final[str] = "content-size"

_NOT_FOUND_CODES: Final[frozenset[str]] = frozenset({"404", "NoSuchKey", "NotFound"})
#: A window past the end of the stored object. The caller resolved the window against
#: its own declared size, so the object is shorter than declared.
_INVALID_RANGE_CODES: Final[frozenset[str]] = frozenset({"416", "InvalidRange"})
_CONTENT_RANGE: Final[re.Pattern[str]] = re.compile(r"^bytes (\d+)-(\d+)/(\d+)$")
_NO_BUCKET_CODES: Final[frozenset[str]] = frozenset({"NoSuchBucket"})
_DENIED_CODES: Final[frozenset[str]] = frozenset(
    {
        "403",
        "AccessDenied",
        "AllAccessDisabled",
        "InvalidAccessKeyId",
        "SignatureDoesNotMatch",
        "InvalidToken",
        "ExpiredToken",
        "AccountProblem",
    }
)


def sha256_of(data: bytes) -> str:
    """Hex SHA-256 of an in-memory buffer. Convenience for callers and checks."""
    return hashlib.sha256(data).hexdigest()


class S3BlobStore:
    """The S3/MinIO implementation of the BlobStore port."""

    def __init__(
        self, settings: S3StorageSettings, *, client: Any | None = None
    ) -> None:
        self._settings = settings
        self._bucket = settings.bucket
        self._client = client if client is not None else _build_client(settings)

    # --- access probe --------------------------------------------------------

    def check_access(self) -> None:
        """Prove the configured application credentials reach the bucket."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as exc:
            raise self._translate(exc, bucket_scope=True) from None
        except (BotoCoreError, OSError) as exc:
            raise self._translate_transport(exc) from None

    # --- temporary -----------------------------------------------------------

    def stage_temporary(
        self,
        source: BlobSource,
        *,
        declared_sha256: str,
        declared_size: int,
        role: BlobRole,
        media_type: str,
        upload_token: str | None = None,
    ) -> TemporaryBlob:
        role = parse_blob_role(role)
        declared_sha256 = _normalize_sha256(declared_sha256)
        _require_non_negative_size(declared_size)

        token = (
            secrets.token_hex(16)
            if upload_token is None
            else _normalize_upload_token(upload_token)
        )
        key = layout.temporary_key(token)
        try:
            if isinstance(source, (bytes, bytearray)):
                self._client.put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=bytes(source),
                    ContentType=media_type,
                )
            else:
                self._client.upload_fileobj(
                    source,
                    self._bucket,
                    key,
                    ExtraArgs={"ContentType": media_type},
                )
        except ClientError as exc:
            raise self._translate(exc, bucket_scope=True) from None
        except (BotoCoreError, OSError) as exc:
            raise self._translate_transport(exc) from None

        return TemporaryBlob(
            upload_token=token,
            declared_sha256=declared_sha256,
            declared_size=declared_size,
            role=role,
            media_type=media_type,
        )

    def temporary_exists(self, temporary: TemporaryBlob) -> bool:
        """Point-inspect one opaque temporary handle without listing the bucket."""
        return (
            self._head(layout.temporary_key(temporary.upload_token), missing=None)
            is not None
        )

    def verify_temporary(self, temporary: TemporaryBlob) -> VerifiedBlob:
        """Read the staged bytes back and prove they are what was declared.

        On any mismatch the temporary object is deleted before the typed error
        is raised, so a refused upload leaves no residue anywhere -- neither
        canonical nor temporary.
        """
        key = layout.temporary_key(temporary.upload_token)

        head = self._head(key, missing=TemporaryBlobLostError)
        stored_size = int(head["ContentLength"])
        if stored_size != temporary.declared_size:
            self.discard_temporary(temporary)
            raise SizeMismatchError(
                expected_size=temporary.declared_size,
                actual_size=stored_size,
                role=str(temporary.role),
            )

        digest = hashlib.sha256()
        try:
            body = self._client.get_object(Bucket=self._bucket, Key=key)["Body"]
            try:
                while True:
                    chunk = body.read(_CHUNK)
                    if not chunk:
                        break
                    digest.update(chunk)
            finally:
                body.close()
        except ClientError as exc:
            if _error_code(exc) in _NOT_FOUND_CODES:
                raise TemporaryBlobLostError() from None
            raise self._translate(exc) from None
        except (BotoCoreError, OSError) as exc:
            raise self._translate_transport(exc) from None

        stored_sha256 = digest.hexdigest()
        if stored_sha256 != temporary.declared_sha256:
            self.discard_temporary(temporary)
            raise ChecksumMismatchError(
                expected_sha256=temporary.declared_sha256,
                actual_sha256=stored_sha256,
                role=str(temporary.role),
            )

        return VerifiedBlob(
            blob_id=derive_blob_id(sha256=stored_sha256, size=stored_size),
            upload_token=temporary.upload_token,
            sha256=stored_sha256,
            size=stored_size,
            role=temporary.role,
            media_type=temporary.media_type,
        )

    def discard_temporary(self, temporary: TemporaryBlob) -> None:
        """Delete a staged upload. Idempotent; deleting nothing is success."""
        self._delete(layout.temporary_key(temporary.upload_token))

    # --- publication ---------------------------------------------------------

    def publish(self, verified: VerifiedBlob) -> PublishedBlob:
        """Copy verified bytes to their canonical key, then drop the temporary.

        Idempotent by ``(sha256, size)``. If the canonical object already exists it is
        reused only after its recorded size, SHA-256 and media type are checked
        against this publication -- available bytes are immutable, so a disagreement
        is refused rather than overwritten:

        * no recorded SHA-256 -- this adapter cannot vouch for the object, so it is
          refused (:class:`BlobMetadataInvalidError`), never reused;
        * a recorded SHA-256 or size that differs -- :class:`BlobIntegrityError`;
        * a different media type -- :class:`BlobAttributeConflictError`.

        **The role is not compared** (owner ruling `R-76`). A role belongs to the
        binding that uses the bytes, not to the bytes: a project document and a
        normative-corpus source may be the same file. The first publisher's
        ``blob-role`` stays on the object as historical metadata and is returned
        unchanged; a consumer reads its own role from its own binding.
        """
        canonical = layout.canonical_key(verified.blob_id)
        existing = self._head(canonical, missing=None)
        if existing is not None:
            temporary = _as_temporary(verified)
            try:
                record = self._record_from_head(verified.blob_id, existing)
            except StorageError:
                self.discard_temporary(temporary)
                raise
            if not record.sha256:
                self.discard_temporary(temporary)
                raise BlobMetadataInvalidError(
                    field=_META_SHA256,
                    constraint="recorded on every object this adapter publishes",
                )
            if record.sha256 != verified.sha256:
                self.discard_temporary(temporary)
                raise ChecksumMismatchError(
                    expected_sha256=verified.sha256,
                    actual_sha256=record.sha256,
                    role=str(verified.role),
                )
            if record.size != verified.size:
                self.discard_temporary(temporary)
                raise SizeMismatchError(
                    expected_size=verified.size,
                    actual_size=record.size,
                    role=str(verified.role),
                )
            if record.media_type != verified.media_type:
                self.discard_temporary(temporary)
                raise BlobAttributeConflictError(
                    blob_id=str(verified.blob_id),
                    media_type=record.media_type,
                )
            self.discard_temporary(temporary)
            return record

        source_key = layout.temporary_key(verified.upload_token)
        try:
            self._client.copy_object(
                Bucket=self._bucket,
                Key=canonical,
                CopySource={"Bucket": self._bucket, "Key": source_key},
                MetadataDirective="REPLACE",
                ContentType=verified.media_type,
                Metadata=_metadata_for(verified),
            )
        except ClientError as exc:
            if _error_code(exc) in _NOT_FOUND_CODES:
                raise TemporaryBlobLostError() from None
            raise self._translate(exc) from None
        except (BotoCoreError, OSError) as exc:
            raise self._translate_transport(exc) from None

        self._delete(source_key)
        return self.inspect(verified.blob_id)

    def put_blob(
        self,
        source: BlobSource,
        *,
        declared_sha256: str,
        declared_size: int,
        role: BlobRole,
        media_type: str,
    ) -> PublishedBlob:
        """``temporary -> verify -> publish`` as one call.

        Any failure leaves nothing canonical. The ``except`` here only cleans
        up the staged bytes for failures raised *after* staging succeeded;
        ``verify_temporary`` already removes them on a mismatch, and deleting
        an absent object is a no-op.
        """
        temporary = self.stage_temporary(
            source,
            declared_sha256=declared_sha256,
            declared_size=declared_size,
            role=role,
            media_type=media_type,
        )
        try:
            verified = self.verify_temporary(temporary)
            return self.publish(verified)
        except StorageError:
            self.discard_temporary(temporary)
            raise

    # --- inspection and read -------------------------------------------------

    def inspect(self, blob_id: BlobId) -> PublishedBlob:
        head = self._head(layout.canonical_key(blob_id), missing=None)
        if head is None:
            raise BlobNotFoundError(blob_id=str(blob_id))
        return self._record_from_head(blob_id, head)

    def read(self, blob_id: BlobId, *, verify: bool = True) -> bytes:
        """Return published bytes, re-verifying the recorded SHA-256 by default.

        Available bytes are immutable, so a read that does not hash what it
        returns is trusting that nothing ever bypassed this adapter. Re-hashing
        is cheap at prototype sizes and turns that assumption into a check.

        An object carrying **no** recorded digest is refused rather than
        returned. ``publish`` writes ``content-sha256`` onto every canonical
        object, so an object without it was not published through this adapter,
        and returning it from a call named ``verify`` would be a claim this
        adapter cannot support. That refusal is
        :class:`BlobMetadataInvalidError` -- ``validation_failed``, the
        declaration itself is absent -- and is deliberately **not** the
        ``storage_integrity_error`` a disagreeing digest raises: "this store
        cannot vouch for this object" and "these bytes are not the declared
        bytes" are two different faults with two different answers, and an
        operator reading an envelope must be able to tell which one happened.
        ``verify=False`` remains the explicit opt-out and is unchanged.
        """
        key = layout.canonical_key(blob_id)
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            body = response["Body"]
            try:
                data = body.read()
            finally:
                body.close()
        except ClientError as exc:
            if _error_code(exc) in _NOT_FOUND_CODES:
                raise BlobNotFoundError(blob_id=str(blob_id)) from None
            raise self._translate(exc) from None
        except (BotoCoreError, OSError) as exc:
            raise self._translate_transport(exc) from None

        if verify:
            recorded = _metadata_value(response, _META_SHA256)
            if recorded is None:
                raise BlobMetadataInvalidError(
                    field=_META_SHA256,
                    constraint="recorded on every object this adapter publishes",
                )
            actual = hashlib.sha256(data).hexdigest()
            if recorded != actual:
                raise ChecksumMismatchError(
                    expected_sha256=recorded, actual_sha256=actual
                )
        return data

    def open_stream(
        self,
        blob_id: BlobId,
        *,
        expected_sha256: str,
        expected_size: int,
        window: tuple[int, int] | None = None,
        chunk_size: int = STREAM_CHUNK_BYTES,
    ) -> BlobChunks:
        """Open published bytes for a chunked read. See :meth:`BlobStore.open_stream`.

        One ``GetObject``, carrying ``Range`` for a window, is issued **here**, and its
        status line and headers are checked here, so every refusal this adapter can make
        before a byte is consumed is raised by this call rather than by the iterator.
        The body is not read until the iterator is advanced, and then at most
        ``chunk_size`` bytes at a time: a windowed read never transfers more than the
        window, and no read ever holds the object whole.
        """
        expected_sha256 = _normalize_sha256(expected_sha256)
        _require_non_negative_size(expected_size)
        if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")
        if window is not None:
            first, last = window
            if not 0 <= first <= last < expected_size:
                raise ValueError("window must be resolved inside the declared size")

        request: dict[str, Any] = {
            "Bucket": self._bucket,
            "Key": layout.canonical_key(blob_id),
        }
        if window is not None:
            request["Range"] = f"bytes={window[0]}-{window[1]}"
        try:
            response = self._client.get_object(**request)
        except ClientError as exc:
            code = _error_code(exc)
            if code in _NOT_FOUND_CODES:
                raise BlobNotFoundError(blob_id=str(blob_id)) from None
            if window is not None and code in _INVALID_RANGE_CODES:
                raise SizeMismatchError(expected_size=expected_size) from None
            raise self._translate(exc) from None
        except (BotoCoreError, OSError) as exc:
            raise self._translate_transport(exc) from None

        body = response["Body"]
        try:
            length = _admitted_length(
                response,
                expected_sha256=expected_sha256,
                expected_size=expected_size,
                window=window,
            )
        except StorageError:
            body.close()
            raise
        return self._chunks(
            blob_id,
            body,
            length=length,
            expected_sha256=expected_sha256 if window is None else None,
            chunk_size=chunk_size,
        )

    def _chunks(
        self,
        blob_id: BlobId,
        body: Any,
        *,
        length: int,
        expected_sha256: str | None,
        chunk_size: int,
    ) -> BlobChunks:
        """The body, ``chunk_size`` at a time; a whole read holds its last chunk back.

        ``expected_sha256`` is ``None`` for a windowed read, which is counted but not
        hashed. For a whole read every chunk is hashed as it arrives and yielded only
        once the *next* one has arrived, so the final chunk is still here when the
        digest is complete -- and is yielded only if the digest is the declared one.
        """
        digest = hashlib.sha256() if expected_sha256 is not None else None
        received = sent = 0
        held: bytes | None = None
        try:
            while True:
                try:
                    chunk = body.read(chunk_size)
                except (BotoCoreError, OSError) as exc:
                    raise self._translate_transport(exc) from None
                if not chunk:
                    break
                received += len(chunk)
                if received > length:
                    raise SizeMismatchError(expected_size=length, actual_size=received)
                if digest is None:
                    sent += len(chunk)
                    yield chunk
                    continue
                digest.update(chunk)
                if held is not None:
                    sent += len(held)
                    yield held
                held = chunk
            if received != length:
                raise SizeMismatchError(expected_size=length, actual_size=received)
            if digest is not None:
                actual = digest.hexdigest()
                if actual != expected_sha256:
                    raise ChecksumMismatchError(
                        expected_sha256=expected_sha256, actual_sha256=actual
                    )
                if held is not None:
                    sent += len(held)
                    yield held
        except BlobIntegrityError as failure:
            # The one place this fault is seen: the status line is already sent, so the
            # stream can only stop short. The record is what an operator follows.
            _log.error(
                "storage_integrity_error: the streamed read of %s stopped after %d of "
                "%d declared bytes (%s)",
                blob_id,
                sent,
                length,
                failure,
            )
            raise
        finally:
            body.close()

    # --- maintenance ---------------------------------------------------------

    def _purge_published(self, blob_id: BlobId) -> None:
        """Delete exactly one canonical object.

        **Not part of the port and never called by business code.** It exists
        for the lane's own scoped cleanup: ``check.py`` and the integration
        tests remove the objects they created, one key at a time, so that no
        cleanup path in this repository is ever a broad bucket deletion.
        Erasure of real content is an ``erasure_pending -> erased`` transition
        under an approved ``erasure_request_id``, which P01 does not implement.
        """
        self._delete(layout.canonical_key(blob_id))

    # --- internals -----------------------------------------------------------

    def _head(self, key: str, *, missing: type[StorageError] | None) -> Any:
        try:
            return self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            code = _error_code(exc)
            if code in _NOT_FOUND_CODES:
                if missing is None:
                    return None
                raise missing() from None
            raise self._translate(exc, bucket_scope=True) from None
        except (BotoCoreError, OSError) as exc:
            raise self._translate_transport(exc) from None

    def _delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if _error_code(exc) in _NOT_FOUND_CODES:
                return
            raise self._translate(exc) from None
        except (BotoCoreError, OSError) as exc:
            raise self._translate_transport(exc) from None

    def _record_from_head(self, blob_id: BlobId, head: Any) -> PublishedBlob:
        metadata = {k.lower(): v for k, v in (head.get("Metadata") or {}).items()}
        recorded_sha = metadata.get(_META_SHA256)
        recorded_size = metadata.get(_META_SIZE)
        size = int(head["ContentLength"])
        if recorded_size is not None and int(recorded_size) != size:
            raise SizeMismatchError(
                expected_size=int(recorded_size), actual_size=size
            )
        last_modified = head.get("LastModified") or datetime.now(timezone.utc)
        return PublishedBlob(
            blob_id=blob_id,
            role=BlobRole(metadata.get(_META_ROLE, "")),
            media_type=head.get("ContentType", "application/octet-stream"),
            size=size,
            sha256=recorded_sha or "",
            published_at=last_modified,
        )

    def _translate(self, exc: ClientError, *, bucket_scope: bool = False) -> StorageError:
        """Map a botocore ``ClientError`` onto a typed, key-free failure.

        The botocore message is deliberately dropped rather than wrapped: it is
        the one string in this path that can name a bucket or a key. Only the
        error code -- a fixed vocabulary token -- influences the result.
        """
        code = _error_code(exc)
        if code in _NO_BUCKET_CODES:
            return StorageBucketMissingError(field=BUCKET_VAR, constraint="must_exist")
        if code in _DENIED_CODES:
            return StorageCredentialRefusedError()
        status = (
            exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if isinstance(getattr(exc, "response", None), dict)
            else None
        )
        if status is not None and int(status) >= 500:
            return StorageUnavailableError()
        if bucket_scope and code in _NOT_FOUND_CODES:
            # A HEAD against a bucket that is absent answers 404, not
            # NoSuchBucket, so the bucket-scoped call sites map it explicitly.
            return StorageBucketMissingError(field=BUCKET_VAR, constraint="must_exist")
        return StorageUnavailableError()

    def _translate_transport(self, exc: Exception) -> StorageError:
        if isinstance(exc, NoCredentialsError):
            return StorageCredentialRefusedError()
        if isinstance(exc, (EndpointConnectionError, BotoConnectionError, OSError)):
            return StorageUnavailableError()
        return StorageUnavailableError()


# --- module helpers ----------------------------------------------------------


def _build_client(settings: S3StorageSettings) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.endpoint_url,
        region_name=settings.region,
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=settings.connect_timeout_seconds,
            read_timeout=settings.read_timeout_seconds,
            retries={"max_attempts": settings.max_attempts, "mode": "standard"},
        ),
    )


def _error_code(exc: ClientError) -> str:
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return ""
    return str(response.get("Error", {}).get("Code", ""))


def _metadata_for(verified: VerifiedBlob) -> dict[str, str]:
    return {
        _META_BLOB_ID: str(verified.blob_id),
        _META_ROLE: str(verified.role),
        _META_SHA256: verified.sha256,
        _META_SIZE: str(verified.size),
    }


def _metadata_value(response: Any, name: str) -> str | None:
    metadata = {k.lower(): v for k, v in (response.get("Metadata") or {}).items()}
    return metadata.get(name)


def _admitted_length(
    response: Any,
    *,
    expected_sha256: str,
    expected_size: int,
    window: tuple[int, int] | None,
) -> int:
    """How many body bytes an opened ``GetObject`` must deliver, or a typed refusal.

    Checked from the response's headers alone, before any body byte is read: the
    recorded digest must be present and the declared one (the read's own
    verification), and the stored size -- ``ContentLength`` for a whole read, the
    total after the slash of ``ContentRange`` for a window -- must be the declared
    size. A store that ignored ``Range`` and sent the whole object is refused rather
    than sliced, since slicing is exactly the whole-object read a window avoids.
    """
    recorded = _metadata_value(response, _META_SHA256)
    if recorded is None:
        raise BlobMetadataInvalidError(
            field=_META_SHA256,
            constraint="recorded on every object this adapter publishes",
        )
    if recorded != expected_sha256:
        raise ChecksumMismatchError(expected_sha256=expected_sha256, actual_sha256=recorded)
    content_length = int(response.get("ContentLength", -1))
    if window is None:
        if content_length != expected_size:
            raise SizeMismatchError(expected_size=expected_size, actual_size=content_length)
        return expected_size
    match = _CONTENT_RANGE.match(str(response.get("ContentRange") or ""))
    if match is None:
        raise StorageUnavailableError()
    first, last, total = (int(value) for value in match.groups())
    if total != expected_size:
        raise SizeMismatchError(expected_size=expected_size, actual_size=total)
    length = window[1] - window[0] + 1
    if (first, last) != window or content_length != length:
        raise StorageUnavailableError()
    return length


def _as_temporary(verified: VerifiedBlob) -> TemporaryBlob:
    return TemporaryBlob(
        upload_token=verified.upload_token,
        declared_sha256=verified.sha256,
        declared_size=verified.size,
        role=verified.role,
        media_type=verified.media_type,
    )


def _normalize_sha256(value: str) -> str:
    candidate = (value or "").strip().lower()
    if len(candidate) != 64 or any(c not in "0123456789abcdef" for c in candidate):
        raise BlobMetadataInvalidError(
            field="declared_sha256", constraint="64 lowercase hex characters"
        )
    return candidate


def _normalize_upload_token(value: str) -> str:
    if not isinstance(value, str) or not _UPLOAD_TOKEN_PATTERN.fullmatch(value):
        raise BlobMetadataInvalidError(
            field="upload_token", constraint="1-128 URL-safe opaque characters"
        )
    return value


def _require_non_negative_size(size: int) -> None:
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise BlobMetadataInvalidError(
            field="declared_size", constraint="non-negative integer"
        )


__all__ = ["S3BlobStore", "sha256_of"]
