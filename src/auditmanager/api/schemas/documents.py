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

__all__ = [
    "DocumentActiveRunView",
    "DocumentAuditView",
    "DocumentVersionView",
    "ManifestEntryView",
    "document_audit_body",
    "document_version_body",
]


@dataclass(frozen=True, slots=True)
class ManifestEntryView:
    """Exactly the frozen ``InputManifestEntry``. No ``blob_id`` field: see below."""

    role: str
    sha256: str
    size_bytes: int
    media_type: str


@dataclass(frozen=True, slots=True)
class DocumentActiveRunView:
    """Exactly the frozen ``DocumentActiveRun`` (`UI-A-47`, contract 1.40.0): the run in flight and its state."""

    run_id: str
    state: str


@dataclass(frozen=True, slots=True)
class DocumentAuditView:
    """Exactly the frozen ``DocumentAudit`` (`UI-PARITY-DOC-AUDIT`, `UI-A-46`).

    Nothing is decided here: the read model (``auditmanager.dashboard.audit_state``) classifies and the adapter
    copies its record field for field. ``result_run_id`` is ``None`` exactly when ``state`` is ``not_run`` and is
    then omitted on the wire. ``active_run`` (`UI-A-47`) is ``None`` when no run of the version is in flight and is
    then omitted too.
    """

    state: str
    partial: bool
    result_run_id: str | None
    finding_count: int
    undecided_finding_count: int
    active_run: DocumentActiveRunView | None = None


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
    #: `R-40`. One of the fifteen project sections, or ``None`` when the document
    #: has not been classified -- see ``documents.models.DocumentVersionRecord.section``.
    section: str | None = None
    media_type: str = "application/pdf"
    #: `W59-SECTION-SEAL-01`. The version's persisted classification (the frozen
    #: ``VersionClassification``), or ``None`` while unclassified -- then omitted on the wire.
    classification: Any = None
    #: `CMP-SEAL-C0`. How the version reached the product (``portal_bundle`` or
    #: ``comparison_pdf``); always emitted.
    upload_kind: str = "portal_bundle"
    #: `R-151a` (contract 1.22.0, migration 0052): when the document was archived; ``None`` while in use. Rendered only
    #: when present; an archived document is listed only on request (``include_archived``).
    archived_at: datetime | None = None
    #: `R-151e` (contract 1.23.0, migration 0053): the document's free tags; ``None`` where the read does not carry
    #: them, rendered as a list (possibly empty) otherwise.
    tags: tuple[str, ...] | None = None
    #: `UI-PARITY-DOC-AUDIT` (contract 1.34.0): the audit of this version, attached by ``listDocuments`` only;
    #: ``None`` on every other operation, and then omitted on the wire.
    audit: DocumentAuditView | None = None


def document_audit_body(view: DocumentAuditView) -> dict[str, Any]:
    body: dict[str, Any] = {
        "state": view.state,
        "partial": view.partial,
        "finding_count": view.finding_count,
        "undecided_finding_count": view.undecided_finding_count,
    }
    if view.result_run_id is not None:
        body["result_run_id"] = view.result_run_id
    if view.active_run is not None:
        body["active_run"] = {"run_id": view.active_run.run_id, "state": view.active_run.state}
    return body


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
        "upload_kind": view.upload_kind,
    }
    if view.display_title is not None:
        body["display_title"] = view.display_title
    if view.section is not None:
        body["section"] = view.section
    if view.classification is not None:
        body["classification"] = view.classification.model_dump(mode="json")
    if view.archived_at is not None:
        body["archived_at"] = timestamp(view.archived_at)
    if view.tags is not None:
        body["tags"] = list(view.tags)
    if view.audit is not None:
        body["audit"] = document_audit_body(view.audit)
    return body
