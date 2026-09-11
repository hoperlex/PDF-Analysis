"""The value types ingest returns. Opaque identity plus recorded facts, nothing else.

``docs/program/P02_SEAMS.md`` section 2.2 lists what is never an identity, and the
``P2-META-01`` integration contract fixes what a consumer receives: "the version
identity plus a manifest of role, blob identity, checksum, size and media type. Bucket
and object key never appear in a return value, log or error."

That is enforced here by omission rather than by redaction. These dataclasses have no
field for a bucket, an object key, a URL, a filesystem path, an uploaded file name or a
display ordinal, so there is nothing for a caller to read and nothing for a formatter to
leak. The columns that hold those values -- ``document_version.source_filename`` and
``document_version.version_ordinal`` -- are written by the repository and are simply not
projected onto any of these types.

``sha256`` *is* present, and deliberately: the contract names a checksum among the facts
a consumer receives. A checksum is a verification value, never an identity, and nothing
in the schema references one with a foreign key.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid
from auditmanager.storage import BlobId

__all__ = [
    "ROLE_SOURCE_DOCUMENT",
    "DocumentVersionRecord",
    "ManifestEntry",
    "ProjectRecord",
    "UploadOutcome",
]

#: The one manifest role PC-01 publishes. Matches ``auditmanager.storage``'s blob role
#: of the same name and the schema's ``ck_input_manifest_entry_role`` pattern.
ROLE_SOURCE_DOCUMENT: Final[str] = "source_document"


@dataclass(frozen=True, slots=True)
class ProjectRecord:
    """A project as a consumer sees it.

    ``name`` is a display label the expert chose. The schema's own comment calls it
    "not unique, not an identity and never a foreign key", so returning it reveals no
    address and creates no coupling.
    """

    project_uid: ProjectUid
    name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    """One row of a published version's immutable input manifest.

    ``blob_id`` is the only handle to the bytes. It is derived by
    ``auditmanager.storage`` from ``(sha256, size)``, so it addresses content rather
    than a location, and there is no accessor anywhere that turns it into a key.
    """

    role: str
    blob_id: BlobId
    sha256: str
    size_bytes: int
    media_type: str


@dataclass(frozen=True, slots=True)
class DocumentVersionRecord:
    """One published, immutable version and its complete input manifest.

    Immutable in the database as well as here: ``trg_document_version_immutable`` and
    ``trg_input_manifest_entry_immutable`` refuse UPDATE and DELETE with SQLSTATE
    ``AM003``. A corrected source file is a new ``version_uid``, never an edit.
    """

    version_uid: VersionUid
    document_uid: DocumentUid
    project_uid: ProjectUid
    #: The display ordinal of this version within its document, 1-based. Foundation
    #: invariant 3 says a display ordinal is **not an identifier** - it is never a key,
    #: never resolved against, and never used to address a version. It is carried
    #: because ``DocumentVersion`` in the frozen API contract requires it, so a reviewer
    #: can be told they are looking at version 2 rather than version 1.
    version_ordinal: int
    media_type: str
    byte_size: int
    sha256: str
    page_count: int
    published_at: datetime
    manifest: tuple[ManifestEntry, ...]

    def entry(self, role: str) -> ManifestEntry:
        """The manifest entry for one role.

        Raises :class:`KeyError` rather than returning ``None``: a missing required
        role is a broken manifest, and the caller that asked for it cannot continue.
        """
        for item in self.manifest:
            if item.role == role:
                return item
        raise KeyError(role)

    @property
    def source(self) -> ManifestEntry:
        """The ``source_document`` entry every PC-01 version carries."""
        return self.entry(ROLE_SOURCE_DOCUMENT)


@dataclass(frozen=True, slots=True)
class UploadOutcome:
    """What one upload command produced.

    ``replayed`` is ``True`` when the command key had already succeeded with this exact
    payload and the stored result was returned without creating anything. A caller can
    therefore distinguish "created" from "already done" without comparing timestamps.
    """

    version: DocumentVersionRecord
    replayed: bool = False
