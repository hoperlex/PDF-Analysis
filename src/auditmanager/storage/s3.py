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

Error translation
-----------------
Every ``botocore`` failure is translated into one of this package's typed
errors. Botocore messages are never re-raised as text, and no translated
message carries a bucket or a key -- the error classes make that structurally
impossible, see :mod:`auditmanager.storage.errors`.
"""

from __future__ import annotations

import hashlib
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
    BlobMetadataInvalidError,
    BlobNotFoundError,
    ChecksumMismatchError,
    SizeMismatchError,
    StorageBucketMissingError,
    StorageError,
    StoragePermissionDeniedError,
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
from .port import BlobSource
from .settings import BUCKET_VAR, S3StorageSettings

_CHUNK: Final[int] = 1024 * 1024

# User metadata names. S3 lower-cases and prefixes these with `x-amz-meta-`.
_META_BLOB_ID: Final[str] = "blob-id"
_META_ROLE: Final[str] = "blob-role"
_META_SHA256: Final[str] = "content-sha256"
_META_SIZE: Final[str] = "content-size"

_NOT_FOUND_CODES: Final[frozenset[str]] = frozenset({"404", "NoSuchKey", "NotFound"})
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
    ) -> TemporaryBlob:
        role = parse_blob_role(role)
        declared_sha256 = _normalize_sha256(declared_sha256)
        _require_non_negative_size(declared_size)

        token = secrets.token_hex(16)
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

        Idempotent by ``(sha256, size)``. If the canonical object already
        exists, its recorded role and media type must agree with this
        publication -- available bytes are immutable, so a disagreement is a
        typed conflict rather than an overwrite.
        """
        canonical = layout.canonical_key(verified.blob_id)
        existing = self._head(canonical, missing=None)
        if existing is not None:
            record = self._record_from_head(verified.blob_id, existing)
            if record.role != verified.role or record.media_type != verified.media_type:
                self.discard_temporary(_as_temporary(verified))
                raise BlobAttributeConflictError(
                    blob_id=str(verified.blob_id),
                    role=str(record.role),
                    media_type=record.media_type,
                )
            self.discard_temporary(_as_temporary(verified))
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
            actual = hashlib.sha256(data).hexdigest()
            if recorded is not None and recorded != actual:
                raise ChecksumMismatchError(
                    expected_sha256=recorded, actual_sha256=actual
                )
        return data

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
            return StoragePermissionDeniedError(required_capability="blob_storage_rw")
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
            return StoragePermissionDeniedError(required_capability="blob_storage_rw")
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


def _require_non_negative_size(size: int) -> None:
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise BlobMetadataInvalidError(
            field="declared_size", constraint="non-negative integer"
        )


__all__ = ["S3BlobStore", "sha256_of"]
