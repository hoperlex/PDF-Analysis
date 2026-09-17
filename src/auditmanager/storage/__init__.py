"""Storage boundary: the BlobStore port and its S3/MinIO adapter.

Public surface. Everything a consumer needs is re-exported here; everything
else in this package is an implementation detail. In particular
``_object_layout`` -- the module that knows what an object key looks like -- is
not exported and is imported by the adapter alone.

    from auditmanager.storage import S3BlobStore, S3StorageSettings

    store = S3BlobStore(S3StorageSettings.from_env())
    blob = store.put_blob(
        pdf_bytes,
        declared_sha256=sha256_of(pdf_bytes),
        declared_size=len(pdf_bytes),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    assert store.read(blob.blob_id) == pdf_bytes

``blob.blob_id`` is the only thing a consumer keeps. There is no accessor for a
bucket, a key, a URL or a path anywhere on this surface.
"""

from __future__ import annotations

from .errors import (
    BLOB_STORAGE_DEPENDENCY,
    SAFE_DETAIL_KEYS,
    BlobAttributeConflictError,
    BlobIntegrityError,
    BlobMetadataInvalidError,
    BlobNotFoundError,
    ChecksumMismatchError,
    InvalidBlobIdError,
    SizeMismatchError,
    StorageBucketMissingError,
    StorageConfigurationError,
    StorageError,
    StorageCredentialRefusedError,
    StorageUnavailableError,
    TemporaryBlobLostError,
)
from .models import (
    BLOB_ID_PATTERN,
    BLOB_ID_PREFIX,
    ROLE_FOUNDATION_CHECK,
    ROLE_SOURCE_DOCUMENT,
    BlobId,
    BlobRole,
    BlobState,
    PublishedBlob,
    TemporaryBlob,
    VerifiedBlob,
    derive_blob_id,
    parse_blob_id,
    parse_blob_role,
)
from .port import BlobSource, BlobStore
from .s3 import S3BlobStore, sha256_of
from .settings import S3StorageSettings

__all__ = [
    "BLOB_ID_PATTERN",
    "BLOB_ID_PREFIX",
    "BLOB_STORAGE_DEPENDENCY",
    "ROLE_FOUNDATION_CHECK",
    "ROLE_SOURCE_DOCUMENT",
    "SAFE_DETAIL_KEYS",
    "BlobAttributeConflictError",
    "BlobId",
    "BlobIntegrityError",
    "BlobMetadataInvalidError",
    "BlobNotFoundError",
    "BlobRole",
    "BlobSource",
    "BlobState",
    "BlobStore",
    "ChecksumMismatchError",
    "InvalidBlobIdError",
    "PublishedBlob",
    "S3BlobStore",
    "S3StorageSettings",
    "SizeMismatchError",
    "StorageBucketMissingError",
    "StorageConfigurationError",
    "StorageError",
    "StorageCredentialRefusedError",
    "StorageUnavailableError",
    "TemporaryBlob",
    "TemporaryBlobLostError",
    "VerifiedBlob",
    "derive_blob_id",
    "parse_blob_id",
    "parse_blob_role",
    "sha256_of",
]
