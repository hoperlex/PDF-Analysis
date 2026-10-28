"""Cross-context surface of the storage boundary."""

from __future__ import annotations

from auditmanager.storage.blob_repository import BlobMetadataRecord, BlobMetadataRepository
from auditmanager.storage.durable_publication import DurablePublicationStore
from auditmanager.storage.errors import (
    BlobAttributeConflictError,
    BlobIntegrityError,
    BlobMetadataInvalidError,
    BlobNotFoundError,
    MultipartPartError,
    MultipartPartsError,
    StorageError,
    TemporaryBlobLostError,
)
from auditmanager.storage.models import (
    BlobDeclaration,
    BlobId,
    BlobState,
    PublishedBlob,
    TemporaryBlob,
    VerifiedBlob,
    declare_blob,
    derive_blob_id,
    parse_blob_id,
    parse_blob_role,
)
from auditmanager.storage.multipart import (
    MULTIPART_PART_BYTES_MAX,
    MULTIPART_PART_NUMBER_MAX,
    MultipartSweepReport,
    UploadedPart,
    abort_multipart_sweep,
    new_multipart_token,
)
from auditmanager.storage.port import (
    STREAM_CHUNK_BYTES,
    BlobChunks,
    BlobSource,
    BlobStore,
    MultipartStaging,
)
from auditmanager.storage.s3 import S3BlobStore, sha256_of
from auditmanager.storage.settings import S3StorageSettings

from . import _object_layout as layout


def canonical_object_key_for_recovery(blob_id: BlobId) -> str:
    """Resolve a validated Blob ID using the S3 adapter's canonical layout.

    This transport locator is for isolated recovery verification only. Product
    consumers continue to retain and pass the opaque Blob ID.
    """
    return layout.canonical_key(parse_blob_id(blob_id))


__all__ = [
    "MULTIPART_PART_BYTES_MAX",
    "MULTIPART_PART_NUMBER_MAX",
    "STREAM_CHUNK_BYTES",
    "BlobAttributeConflictError",
    "BlobChunks",
    "BlobDeclaration",
    "BlobId",
    "BlobIntegrityError",
    "BlobMetadataInvalidError",
    "BlobMetadataRecord",
    "BlobMetadataRepository",
    "BlobNotFoundError",
    "BlobSource",
    "BlobState",
    "S3BlobStore",
    "S3StorageSettings",
    "BlobStore",
    "DurablePublicationStore",
    "MultipartStaging",
    "MultipartPartError",
    "MultipartPartsError",
    "MultipartSweepReport",
    "PublishedBlob",
    "StorageError",
    "TemporaryBlob",
    "TemporaryBlobLostError",
    "UploadedPart",
    "VerifiedBlob",
    "abort_multipart_sweep",
    "canonical_object_key_for_recovery",
    "declare_blob",
    "derive_blob_id",
    "new_multipart_token",
    "parse_blob_id",
    "parse_blob_role",
    "sha256_of",
]
