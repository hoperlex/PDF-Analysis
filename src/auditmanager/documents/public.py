"""Cross-context surface of the documents boundary."""

from __future__ import annotations

from auditmanager.documents.models import (
    MANIFEST_ROLE_COMPARISON_PDF,
    MANIFEST_ROLE_MARKDOWN,
    MANIFEST_ROLE_SOURCE_DOCUMENT,
    MANIFEST_ROLE_STAMP_AUDIT,
    MANIFEST_ROLE_STRUCTURED_COMPANION,
    ROLE_COMPARISON_PDF,
    ROLE_SOURCE_DOCUMENT,
    ROLE_SOURCE_MARKDOWN,
    ROLE_SOURCE_STAMP_AUDIT,
    ROLE_SOURCE_STRUCTURED_COMPANION,
    UPLOAD_KIND_COMPARISON_PDF,
    UPLOAD_KIND_PORTAL_BUNDLE,
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
    "MANIFEST_ROLE_COMPARISON_PDF",
    "MANIFEST_ROLE_MARKDOWN",
    "MANIFEST_ROLE_SOURCE_DOCUMENT",
    "MANIFEST_ROLE_STAMP_AUDIT",
    "MANIFEST_ROLE_STRUCTURED_COMPANION",
    "MAX_PLACEMENT_PAGE",
    "ROLE_COMPARISON_PDF",
    "ROLE_SOURCE_DOCUMENT",
    "ROLE_SOURCE_MARKDOWN",
    "ROLE_SOURCE_STAMP_AUDIT",
    "ROLE_SOURCE_STRUCTURED_COMPANION",
    "UNIQUE_VIOLATION",
    "UPLOAD_KIND_COMPARISON_PDF",
    "UPLOAD_KIND_PORTAL_BUNDLE",
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
