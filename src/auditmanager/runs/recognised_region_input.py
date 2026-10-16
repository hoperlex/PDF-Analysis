"""Read one saved W56b OCR region candidate under current Run/Attempt custody.

The caller owns the SQL transaction and keeps its authority locks through the
two Blob reads. This unserved service neither chooses a citation policy nor
reserves authority for a later provider effect or publication.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ARTIFACT_MEDIA_TYPE,
    ARTIFACT_VERSION,
    ROLE_BLOCK_INDEX,
    ROLE_CROP_IMAGE,
    ROLE_PAGE_CROPS,
    ROLE_PAGE_INVENTORY,
    ROLE_PORTAL_BLOCKS,
    ROLE_RECOGNISED_TEXT,
    ROLE_TEXT_LAYER,
    ArtifactRef,
    RecognisedRegionCandidate,
    RecognisedRegionRefused,
    bind_recognised_region_candidate,
    canonical_bytes,
    default_registry,
    sha256_hex,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.repository import RunRepository, StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdentityError, VersionUid
from auditmanager.storage.public import BlobStore, StorageError, parse_blob_id


_SOURCE: Final[str] = "source_preparation"
_GEOMETRY: Final[str] = "page_geometry_extraction"
_SOURCE_REQUIRED: Final[frozenset[str]] = frozenset({
    ROLE_PAGE_INVENTORY, ROLE_TEXT_LAYER, ROLE_RECOGNISED_TEXT,
})
_GEOMETRY_REQUIRED: Final[frozenset[str]] = frozenset({
    ROLE_BLOCK_INDEX, ROLE_PAGE_CROPS, ROLE_PORTAL_BLOCKS,
})


@dataclass(frozen=True, slots=True)
class SavedRecognisedRegionInput:
    """Checked OCR region and the two exact saved artifact references."""

    candidate: RecognisedRegionCandidate
    recognised_ref: ArtifactRef
    portal_blocks_ref: ArtifactRef


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="saved recognised region cannot be bound to the current run",
        stage_id=_GEOMETRY,
        reason=reason,
    )


def _one_stage(rows: tuple[StageResultRow, ...], stage_id: str) -> StageResultRow:
    matches = tuple(row for row in rows if row.stage_id == stage_id)
    if len(matches) != 1:
        raise _refuse("stage_missing_or_duplicate")
    row = matches[0]
    try:
        expected_version = default_registry().stage(stage_id).stage_version
    except Exception as exc:
        raise _refuse("stage_registry_unavailable") from exc
    if row.status != "succeeded" or row.stage_version != expected_version:
        raise _refuse("stage_not_succeeded")
    return row


def _stage_refs(
    row: StageResultRow, *, required: frozenset[str], allowed: frozenset[str]
) -> dict[str, ArtifactRef]:
    refs: dict[str, ArtifactRef] = {}
    blob_ids: set[str] = set()
    for raw in row.artifacts:
        if not isinstance(raw, Mapping):
            raise _refuse("saved_artifact_reference_invalid")
        try:
            ref = ArtifactRef(**dict(raw))
        except (TypeError, ValueError):
            raise _refuse("saved_artifact_reference_invalid") from None
        if (
            ref.role not in allowed
            or type(ref.size_bytes) is not int or ref.size_bytes < 1
            or ref.media_type != (
                "image/png" if ref.role == ROLE_CROP_IMAGE else ARTIFACT_MEDIA_TYPE
            )
            or ref.blob_id in blob_ids
            or (ref.role != ROLE_CROP_IMAGE and ref.role in refs)
        ):
            raise _refuse("saved_artifact_reference_invalid")
        blob_ids.add(ref.blob_id)
        if ref.role != ROLE_CROP_IMAGE:
            refs[ref.role] = ref
    if not required <= refs.keys():
        raise _refuse("saved_artifact_reference_missing")
    return refs


def _read_document(store: BlobStore, ref: ArtifactRef, *, version_uid: str) -> dict[str, Any]:
    try:
        chunks = store.open_stream(
            parse_blob_id(ref.blob_id),
            expected_sha256=ref.sha256,
            expected_size=ref.size_bytes,
        )
        try:
            content = bytearray()
            for chunk in chunks:
                if type(chunk) is not bytes or len(content) + len(chunk) > ref.size_bytes:
                    raise _refuse("saved_artifact_size_mismatch")
                content.extend(chunk)
        finally:
            chunks.close()
    except (StorageError, IdentityError) as exc:
        raise _refuse("saved_artifact_unreadable") from exc
    payload = bytes(content)
    if len(payload) != ref.size_bytes or sha256_hex(payload) != ref.sha256:
        raise _refuse("saved_artifact_integrity_mismatch")
    try:
        document = json.loads(payload.decode("utf-8"))
        if (
            not isinstance(document, dict)
            or canonical_bytes(document) != payload
            or document.get("artifact_role") != ref.role
            or document.get("artifact_version") != ARTIFACT_VERSION
            or document.get("version_uid") != version_uid
        ):
            raise _refuse("saved_artifact_document_invalid")
    except (UnicodeError, ValueError, TypeError, OverflowError) as exc:
        raise _refuse("saved_artifact_document_invalid") from exc
    return document


def load_saved_recognised_region(
    session: Session,
    *,
    authority: AttemptAuthority,
    blob_store: BlobStore,
    max_input_bytes: int,
    portal_block_id: str,
    page_number: int,
    quote: str,
    runs: RunRepository | None = None,
    jobs: JobRepository | None = None,
    documents: DocumentRepository | None = None,
) -> SavedRecognisedRegionInput:
    """Bind one supplied OCR quote to saved source and geometry under two fences."""
    run_repo = runs or RunRepository()
    job_repo = jobs or JobRepository()
    document_repo = documents or DocumentRepository()

    job_repo.require_current(session, authority)
    if type(max_input_bytes) is not int or max_input_bytes < 1:
        raise _refuse("invalid_input_byte_ceiling")
    run = run_repo.get(session, authority.run_id)
    if run.run_id != authority.run_id or run.state != "running":
        raise _refuse("running_run_required")
    try:
        version = document_repo.get_version(session, VersionUid.parse(run.version_uid))
    except IdentityError:
        raise _refuse("run_version_identity_invalid") from None
    if (
        str(version.version_uid) != run.version_uid
        or str(version.project_uid) != run.project_uid
        or type(version.page_count) is not int or version.page_count < 1
        or not isinstance(version.textless_pages, tuple)
        or any(
            type(page) is not int or page < 1 or page > version.page_count
            for page in version.textless_pages
        )
        or tuple(sorted(set(version.textless_pages))) != version.textless_pages
    ):
        raise _refuse("portal_version_required")

    rows = run_repo.stage_results(session, authority.run_id)
    source_row = _one_stage(rows, _SOURCE)
    geometry_row = _one_stage(rows, _GEOMETRY)
    recognised_ref = _stage_refs(
        source_row, required=_SOURCE_REQUIRED, allowed=_SOURCE_REQUIRED,
    )[ROLE_RECOGNISED_TEXT]
    portal_ref = _stage_refs(
        geometry_row, required=_GEOMETRY_REQUIRED,
        allowed=_GEOMETRY_REQUIRED | {ROLE_CROP_IMAGE},
    )[ROLE_PORTAL_BLOCKS]
    if recognised_ref.blob_id == portal_ref.blob_id:
        raise _refuse("saved_artifact_reference_duplicate")
    if recognised_ref.size_bytes + portal_ref.size_bytes > max_input_bytes:
        raise _refuse("saved_region_input_too_large")

    recognised = _read_document(blob_store, recognised_ref, version_uid=run.version_uid)
    portal = _read_document(blob_store, portal_ref, version_uid=run.version_uid)
    if not isinstance(portal.get("pages"), list) or len(portal["pages"]) != version.page_count:
        raise _refuse("portal_page_count_mismatch")
    try:
        candidate = bind_recognised_region_candidate(
            version_uid=run.version_uid,
            textless_pages=version.textless_pages,
            recognised_document=recognised,
            portal_blocks_document=portal,
            portal_block_id=portal_block_id,
            page_number=page_number,
            quote=quote,
        )
    except RecognisedRegionRefused as exc:
        raise _refuse(str(exc)) from exc

    job_repo.require_current(session, authority)
    if run_repo.get(session, authority.run_id) != run:
        raise _refuse("run_changed_during_region_read")
    if document_repo.get_version(session, VersionUid.parse(run.version_uid)) != version:
        raise _refuse("version_changed_during_region_read")
    later_rows = run_repo.stage_results(session, authority.run_id)
    if (
        _one_stage(later_rows, _SOURCE) != source_row
        or _one_stage(later_rows, _GEOMETRY) != geometry_row
    ):
        raise _refuse("stage_changed_during_region_read")
    return SavedRecognisedRegionInput(candidate, recognised_ref, portal_ref)


__all__ = ["SavedRecognisedRegionInput", "load_saved_recognised_region"]
