"""Cross-context surface of the documents boundary."""

from __future__ import annotations

from auditmanager.documents.models import (
    MANIFEST_ROLE_MARKDOWN,
    MANIFEST_ROLE_SOURCE_DOCUMENT,
    MANIFEST_ROLE_STAMP_AUDIT,
    MANIFEST_ROLE_STRUCTURED_COMPANION,
    ROLE_SOURCE_DOCUMENT,
    ROLE_SOURCE_MARKDOWN,
    ROLE_SOURCE_STAMP_AUDIT,
    ROLE_SOURCE_STRUCTURED_COMPANION,
    ClassificationRevisionRecord,
    CurrentVersionPlacementRecord,
    DocumentVersionRecord,
    ManifestEntry,
    ProjectListingRecord,
    ProjectRecord,
    UploadOutcome,
    VersionClassificationRecord,
)
from auditmanager.documents.refusals import UNIQUE_VIOLATION, sqlstate_of
from auditmanager.documents.repository import MAX_PLACEMENT_PAGE, DocumentRepository

__all__ = [
    "MANIFEST_ROLE_MARKDOWN",
    "MANIFEST_ROLE_SOURCE_DOCUMENT",
    "MANIFEST_ROLE_STAMP_AUDIT",
    "MANIFEST_ROLE_STRUCTURED_COMPANION",
    "MAX_PLACEMENT_PAGE",
    "ROLE_SOURCE_DOCUMENT",
    "ROLE_SOURCE_MARKDOWN",
    "ROLE_SOURCE_STAMP_AUDIT",
    "ROLE_SOURCE_STRUCTURED_COMPANION",
    "UNIQUE_VIOLATION",
    "ClassificationRevisionRecord",
    "CurrentVersionPlacementRecord",
    "DocumentRepository",
    "DocumentVersionRecord",
    "ManifestEntry",
    "ProjectListingRecord",
    "ProjectRecord",
    "UploadOutcome",
    "VersionClassificationRecord",
    "sqlstate_of",
]
