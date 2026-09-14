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

import json
from pathlib import Path

from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid
from auditmanager.storage import BlobId

__all__ = [
    "MANIFEST_ROLE_SOURCE_DOCUMENT",
    "ROLE_SOURCE_DOCUMENT",
    "DocumentVersionRecord",
    "ManifestEntry",
    "ProjectRecord",
    "UploadOutcome",
]

#: The blob role, in ``auditmanager.storage``'s namespace. Validated by
#: ``parse_blob_role`` and written on the object, not on the manifest entry.
ROLE_SOURCE_DOCUMENT: Final[str] = "source_document"


def _required_source_role() -> str:
    """The manifest-entry role ``source_preparation`` requires, read from the contract.

    **These are two different namespaces and they were conflated.** The blob role above is
    ``source_document``; the manifest-entry role the analysis stage registry requires is
    ``source.document``. Writing the blob spelling into the manifest made every version
    produced by the real upload path unable to start a run - ``start_audit_run`` refused
    with ``analysis_input_invalid`` before any stage - while
    ``ck_input_manifest_entry_role`` accepted both, because it is a shape pattern rather
    than a vocabulary.

    It survived eight test suites because the run harness defined its own manifest role
    constant with the contract's spelling and seeded fixtures with that, so the executor
    was only ever shown the role its own code expected.

    Reading it from the frozen registry rather than restating it means a rename in the
    contract cannot silently diverge again: this raises at import instead.
    """
    registry = json.loads(_STAGE_REGISTRY.read_text(encoding="utf-8"))
    stages = registry.get("stages") or registry.get("registry") or []
    for stage in stages:
        if stage.get("stage_id") != "source_preparation":
            continue
        for declared in stage.get("required_inputs") or stage.get("inputs") or []:
            if declared.get("required") and declared.get("media_type") == "application/pdf":
                return str(declared["role"])
    raise RuntimeError(
        "contracts/analysis/v1/stage-registry.json declares no required PDF input for "
        "source_preparation; the manifest role cannot be derived"
    )


_STAGE_REGISTRY = (
    Path(__file__).resolve().parents[3] / "contracts" / "analysis" / "v1" / "stage-registry.json"
)

#: The manifest-entry role PC-01 publishes, derived from the stage registry.
MANIFEST_ROLE_SOURCE_DOCUMENT: Final[str] = _required_source_role()


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
    #: The display label the uploader supplied, carried because the frozen
    #: ``DocumentVersion`` schema declares it and `B7`'s upload panel has no other way to
    #: show a reviewer the title they typed. It is a label, never an identity: nothing
    #: resolves a version by it, and `source_filename` stays withheld because a filename is
    #: named in foundation invariant 3 and a display title is not.
    display_title: str
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
        return self.entry(MANIFEST_ROLE_SOURCE_DOCUMENT)


@dataclass(frozen=True, slots=True)
class UploadOutcome:
    """What one upload command produced.

    ``replayed`` is ``True`` when the command key had already succeeded with this exact
    payload and the stored result was returned without creating anything. A caller can
    therefore distinguish "created" from "already done" without comparing timestamps.
    """

    version: DocumentVersionRecord
    replayed: bool = False
