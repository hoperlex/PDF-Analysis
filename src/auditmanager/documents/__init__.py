"""Documents: projects, documents, immutable published versions and input manifests.

Public surface of the ``P2-META-01`` write model and of seam ``S2``. A consumer holds
opaque identities and recorded facts; nothing here exposes a bucket, an object key, a
filesystem path, an uploaded file name or a display ordinal.

    from auditmanager.documents import DocumentRepository, ROLE_SOURCE_DOCUMENT

    with session_scope() as session:
        version = DocumentRepository().get_version(session, version_uid)
        entry = version.source           # role, blob_id, sha256, size, media_type
        data = store.read(entry.blob_id) # the only route to the bytes
"""

from __future__ import annotations

from .models import (
    MANIFEST_ROLE_SOURCE_DOCUMENT,
    ROLE_SOURCE_DOCUMENT,
    DocumentVersionRecord,
    ManifestEntry,
    ProjectRecord,
    UploadOutcome,
)
from .refusals import (
    SQLSTATE_APPEND_ONLY_VIOLATION,
    SQLSTATE_IMMUTABLE_ROW_VIOLATION,
    SQLSTATE_UNDECLARED_TRANSITION,
    UNIQUE_VIOLATION,
    constraint_name_of,
    domain_error_for,
    sqlstate_of,
    translate_database_refusal,
)
from .repository import MAX_DISPLAY_TITLE, MAX_PROJECT_NAME, DocumentRepository

__all__ = [
    "MAX_DISPLAY_TITLE",
    "MAX_PROJECT_NAME",
    "MANIFEST_ROLE_SOURCE_DOCUMENT",
    "ROLE_SOURCE_DOCUMENT",
    "SQLSTATE_APPEND_ONLY_VIOLATION",
    "SQLSTATE_IMMUTABLE_ROW_VIOLATION",
    "SQLSTATE_UNDECLARED_TRANSITION",
    "UNIQUE_VIOLATION",
    "DocumentRepository",
    "DocumentVersionRecord",
    "ManifestEntry",
    "ProjectRecord",
    "UploadOutcome",
    "constraint_name_of",
    "domain_error_for",
    "sqlstate_of",
    "translate_database_refusal",
]
