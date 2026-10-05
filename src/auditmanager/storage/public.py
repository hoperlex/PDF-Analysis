"""Cross-context surface of the storage boundary."""

from __future__ import annotations

from auditmanager.storage.blob_repository import BlobMetadataRepository
from auditmanager.storage.durable_publication import DurablePublicationStore
from auditmanager.storage.errors import BlobNotFoundError, StorageError
from auditmanager.storage.models import (
    BlobDeclaration,
    BlobId,
    TemporaryBlob,
    VerifiedBlob,
    parse_blob_id,
    parse_blob_role,
)
from auditmanager.storage.port import BlobStore
from auditmanager.storage.s3 import sha256_of

__all__ = [
    "BlobDeclaration",
    "BlobId",
    "BlobMetadataRepository",
    "BlobNotFoundError",
    "BlobStore",
    "DurablePublicationStore",
    "StorageError",
    "TemporaryBlob",
    "VerifiedBlob",
    "parse_blob_id",
    "parse_blob_role",
    "sha256_of",
]
