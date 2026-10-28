"""Storage boundary: the BlobStore port and its S3/MinIO adapter.

Public surface. Everything a consumer needs is re-exported here; everything
else in this package is an implementation detail. In particular
``_object_layout`` -- the module that knows what an object key looks like -- is
not exported. The S3 adapter uses it, and ``storage.public`` delegates to it
only for the recovery-scoped canonical key resolver.

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

``blob.blob_id`` is the only thing a product consumer keeps. This package root
does not export a bucket, key, URL or path. The recovery-only resolver in
``storage.public`` returns a transport locator for an isolated restore audit;
it does not make an object key a business identity.
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
    MultipartPartError,
    MultipartPartsError,
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
    BlobDeclaration,
    BlobId,
    BlobRole,
    BlobState,
    PublishedBlob,
    TemporaryBlob,
    VerifiedBlob,
    declare_blob,
    derive_blob_id,
    parse_blob_id,
    parse_blob_role,
)
from .multipart import (
    MULTIPART_PART_BYTES_MAX,
    MULTIPART_PART_NUMBER_MAX,
    MultipartSweepReport,
    UploadedPart,
    abort_multipart_sweep,
    new_multipart_token,
)
from .port import STREAM_CHUNK_BYTES, BlobChunks, BlobSource, BlobStore, MultipartStaging
from .durable_publication import (
    AfterPublish,
    BeforePublish,
    BeforeStage,
    DurablePublicationStore,
)
from .s3 import S3BlobStore, sha256_of
from .settings import S3StorageSettings

__all__ = [
    "BLOB_ID_PATTERN",
    "BLOB_ID_PREFIX",
    "BLOB_STORAGE_DEPENDENCY",
    "MULTIPART_PART_BYTES_MAX",
    "MULTIPART_PART_NUMBER_MAX",
    "ROLE_FOUNDATION_CHECK",
    "ROLE_SOURCE_DOCUMENT",
    "SAFE_DETAIL_KEYS",
    "STREAM_CHUNK_BYTES",
    "BlobAttributeConflictError",
    "BlobChunks",
    "BlobDeclaration",
    "BlobId",
    "BlobIntegrityError",
    "BlobMetadataInvalidError",
    "BlobNotFoundError",
    "BlobRole",
    "BlobSource",
    "BlobState",
    "BlobStore",
    "AfterPublish",
    "BeforePublish",
    "BeforeStage",
    "ChecksumMismatchError",
    "InvalidBlobIdError",
    "MultipartStaging",
    "MultipartPartError",
    "MultipartPartsError",
    "MultipartSweepReport",
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
    "UploadedPart",
    "VerifiedBlob",
    "abort_multipart_sweep",
    "declare_blob",
    "derive_blob_id",
    "DurablePublicationStore",
    "new_multipart_token",
    "parse_blob_id",
    "parse_blob_role",
    "sha256_of",
]
