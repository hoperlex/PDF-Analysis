"""Read one saved W56b IMAGE crop under current Run/Attempt custody.

This unserved input boundary checks the entire cohort's metadata, then opens
only the selected PNG. It grants no later provider or publication authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ARTIFACT_MEDIA_TYPE,
    ROLE_PAGE_CROPS,
    ROLE_PORTAL_BLOCKS,
    ArtifactRef,
    CheckedCropItem,
    RunScopedGeometryStage,
    SavedCropCustodyRefused,
    check_saved_crop_item_bytes,
    prepare_saved_crop_item,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.geometry_crop_input import _one_stage, _read_exact, _source_digest
from auditmanager.runs.repository import RunRepository, StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdentityError, VersionUid
from auditmanager.storage.public import BlobStore


_METADATA_ROLES = frozenset({ROLE_PORTAL_BLOCKS, ROLE_PAGE_CROPS})


@dataclass(frozen=True, slots=True)
class SavedImageCropItemInput:
    """Checked metadata and bytes of one selected saved crop."""

    checked: CheckedCropItem
    png_bytes: bytes
    portal_blocks_ref: ArtifactRef
    crop_manifest_ref: ArtifactRef


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="saved image crop cannot be bound to the current run",
        stage_id="page_geometry_extraction",
        reason=reason,
    )


def _metadata_refs(
    row: StageResultRow, *, max_metadata_bytes: int
) -> tuple[ArtifactRef, ArtifactRef]:
    if not isinstance(row.artifacts, tuple):
        raise _refuse("invalid_saved_artifact_reference")
    refs: dict[str, ArtifactRef] = {}
    total = 0
    for raw in row.artifacts:
        if not isinstance(raw, Mapping):
            raise _refuse("invalid_saved_artifact_reference")
        if raw.get("role") not in _METADATA_ROLES:
            continue
        try:
            ref = ArtifactRef(**dict(raw))
        except (TypeError, ValueError):
            raise _refuse("invalid_saved_artifact_reference") from None
        if ref.role in refs or ref.media_type != ARTIFACT_MEDIA_TYPE or ref.size_bytes < 1:
            raise _refuse("invalid_saved_artifact_reference")
        refs[ref.role] = ref
        total += ref.size_bytes
        if total > max_metadata_bytes:
            raise _refuse("saved_crop_metadata_too_large")
    if refs.keys() != _METADATA_ROLES or refs[ROLE_PORTAL_BLOCKS].blob_id == refs[ROLE_PAGE_CROPS].blob_id:
        raise _refuse("saved_geometry_artifact_missing_or_duplicate")
    return refs[ROLE_PORTAL_BLOCKS], refs[ROLE_PAGE_CROPS]


def load_saved_image_crop_item(
    session: Session,
    *,
    authority: AttemptAuthority,
    blob_store: BlobStore,
    portal_block_id: str,
    max_metadata_bytes: int,
    max_crop_bytes: int,
    runs: RunRepository | None = None,
    jobs: JobRepository | None = None,
    documents: DocumentRepository | None = None,
) -> SavedImageCropItemInput:
    """Return one checked PNG while preserving the complete saved crop plan.

    Both byte caps are caller supplied. The caller owns the short transaction
    and must reacquire authority and journal any later external effect.
    """
    run_repo = runs or RunRepository()
    job_repo = jobs or JobRepository()
    document_repo = documents or DocumentRepository()
    job_repo.require_current(session, authority)
    if (
        type(max_metadata_bytes) is not int or max_metadata_bytes < 1
        or type(max_crop_bytes) is not int or max_crop_bytes < 1
    ):
        raise _refuse("invalid_input_byte_ceiling")

    run = run_repo.get(session, authority.run_id)
    if run.state != "running" or run.run_id != authority.run_id:
        raise _refuse("running_run_required")
    try:
        parsed_version = VersionUid.parse(run.version_uid)
    except IdentityError:
        raise _refuse("run_version_identity_invalid") from None
    version = document_repo.get_version(session, parsed_version)
    if str(version.version_uid) != run.version_uid or str(version.project_uid) != run.project_uid:
        raise _refuse("run_version_mismatch")
    source_digest = _source_digest(version)
    stage = _one_stage(run_repo.stage_results(session, authority.run_id))
    portal_ref, manifest_ref = _metadata_refs(
        stage, max_metadata_bytes=max_metadata_bytes,
    )
    metadata_bytes = {
        portal_ref.blob_id: _read_exact(blob_store, portal_ref),
        manifest_ref.blob_id: _read_exact(blob_store, manifest_ref),
    }
    try:
        prepared = prepare_saved_crop_item(
            run_id=authority.run_id,
            version_uid=run.version_uid,
            stage=RunScopedGeometryStage(
                run_id=authority.run_id,
                stage_id=stage.stage_id,
                stage_version=stage.stage_version,
                status=stage.status,
                artifacts=stage.artifacts,
            ),
            supplied_metadata_bytes=metadata_bytes,
            portal_block_id=portal_block_id,
        )
    except SavedCropCustodyRefused as exc:
        raise _refuse("saved_crop_metadata_invalid") from exc
    if prepared.cohort.blocks_sha256 != source_digest:
        raise _refuse("portal_source_digest_mismatch")
    if prepared.crop.blob.size_bytes > max_crop_bytes:
        raise _refuse("saved_crop_image_too_large")
    png_bytes = _read_exact(blob_store, prepared.crop.blob)
    try:
        checked = check_saved_crop_item_bytes(
            prepared=prepared, supplied_png_bytes=png_bytes,
        )
    except SavedCropCustodyRefused as exc:
        raise _refuse("saved_crop_image_invalid") from exc

    job_repo.require_current(session, authority)
    if run_repo.get(session, authority.run_id) != run:
        raise _refuse("run_changed_during_crop_read")
    if document_repo.get_version(session, parsed_version) != version:
        raise _refuse("version_changed_during_crop_read")
    if _one_stage(run_repo.stage_results(session, authority.run_id)) != stage:
        raise _refuse("geometry_stage_changed_during_crop_read")
    return SavedImageCropItemInput(checked, png_bytes, portal_ref, manifest_ref)


__all__ = ["SavedImageCropItemInput", "load_saved_image_crop_item"]
