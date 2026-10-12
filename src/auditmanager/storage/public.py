"""Cross-context surface of the storage boundary."""

from __future__ import annotations

from auditmanager.storage.blob_repository import BlobMetadataRecord, BlobMetadataRepository
from auditmanager.storage.durable_publication import DurablePublicationStore
from auditmanager.storage.errors import (
    BlobAttributeConflictError,
    BlobIntegrityError,
    BlobMetadataInvalidError,
    BlobNotFoundError,
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
from auditmanager.storage.port import BlobSource, BlobStore
from auditmanager.storage.s3 import sha256_of

__all__ = [
    "BlobAttributeConflictError",
    "BlobDeclaration",
    "BlobId",
    "BlobIntegrityError",
    "BlobMetadataInvalidError",
    "BlobMetadataRecord",
    "BlobMetadataRepository",
    "BlobNotFoundError",
    "BlobSource",
    "BlobState",
    "BlobStore",
    "DurablePublicationStore",
    "PublishedBlob",
    "StorageError",
    "TemporaryBlob",
    "TemporaryBlobLostError",
    "VerifiedBlob",
    "declare_blob",
    "derive_blob_id",
    "parse_blob_id",
    "parse_blob_role",
    "sha256_of",
]
