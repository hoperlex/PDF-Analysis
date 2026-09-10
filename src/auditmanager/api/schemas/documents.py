"""``DocumentVersion`` and ``InputManifestEntry``.

One rule dominates this module: **the manifest carries a ``blob_id`` and a checksum and
never an object key, bucket or URL**, which is the frozen ``InputManifestEntry``
description verbatim. ``blob_id`` is content-derived -- ``auditmanager.storage`` builds
it from ``(sha256, size)`` -- so it addresses content rather than a location, and there
is no accessor anywhere that turns one back into a key.

``source_filename`` is deliberately **not** emitted. See the module note below.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence

from auditmanager.api.schemas.common import timestamp

__all__ = ["DocumentVersionView", "ManifestEntryView", "document_version_body"]


@dataclass(frozen=True, slots=True)
class ManifestEntryView:
    """Exactly the frozen ``InputManifestEntry``. No ``blob_id`` field: see below."""

    role: str
    sha256: str
    size_bytes: int
    media_type: str


@dataclass(frozen=True, slots=True)
class DocumentVersionView:
    """Exactly the frozen ``DocumentVersion``.

    ``version_ordinal`` is **required** by the frozen schema. It is a display and
    ordering value only -- the document says so, and ``P02_SEAMS.md`` section 2.2 lists
    a display ordinal among the things that are never an identity -- but a response
    without it does not validate.
    """

    version_uid: str
    document_uid: str
    project_uid: str
    version_ordinal: int
    byte_size: int
    sha256: str
    page_count: int
    published_at: datetime
    input_manifest: tuple[ManifestEntryView, ...] = ()
    display_title: str | None = None
    media_type: str = "application/pdf"


def manifest_entry_body(view: ManifestEntryView) -> dict[str, Any]:
    return {
        "role": view.role,
        "sha256": view.sha256,
        "size_bytes": view.size_bytes,
        "media_type": view.media_type,
    }


def document_version_body(view: DocumentVersionView) -> dict[str, Any]:
    """Render one published version.

    ``source_filename`` is declared optional by the frozen document and is **never
    emitted here**. The dispatch brief for this session is explicit that no filename may
    cross the boundary, and the uploaded name is the one value on this schema that is a
    caller-supplied filename. Omitting an optional property is schema-valid; the
    tension between the two documents is reported rather than resolved locally.
    """
    body: dict[str, Any] = {
        "version_uid": view.version_uid,
        "document_uid": view.document_uid,
        "project_uid": view.project_uid,
        "version_ordinal": view.version_ordinal,
        "media_type": view.media_type,
        "byte_size": view.byte_size,
        "sha256": view.sha256,
        "page_count": view.page_count,
        "published_at": timestamp(view.published_at),
        "input_manifest": [manifest_entry_body(entry) for entry in view.input_manifest],
    }
    if view.display_title is not None:
        body["display_title"] = view.display_title
    return body
