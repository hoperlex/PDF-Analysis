"""Read W55b's saved IMAGE crops for one current Run/Attempt.

This is an unserved read seam. A caller must journal and fence any later model
effect separately; returning these bytes does not reserve future authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ARTIFACT_MEDIA_TYPE,
    ROLE_BLOCK_INDEX,
    ROLE_CROP_IMAGE,
    ROLE_PAGE_CROPS,
    ROLE_PORTAL_BLOCKS,
    ArtifactRef,
    CheckedCropBytes,
    RunScopedGeometryStage,
    SavedCropCustodyRefused,
    check_saved_crop_bytes,
    default_registry,
)
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.repository import RunRepository, StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobStore, StorageError, parse_blob_id


_STAGE: Final[str] = "page_geometry_extraction"
_REQUIRED: Final[frozenset[str]] = frozenset({
    ROLE_BLOCK_INDEX, ROLE_PORTAL_BLOCKS, ROLE_PAGE_CROPS,
})
_READ: Final[frozenset[str]] = frozenset({
    ROLE_PORTAL_BLOCKS, ROLE_PAGE_CROPS, ROLE_CROP_IMAGE,
})


@dataclass(frozen=True, slots=True)
class SavedImageCropInput:
    """Verified crop bytes and their saved cohort, scoped to one current read."""

    checked: CheckedCropBytes
    crop_bytes: tuple[tuple[str, bytes], ...]


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="saved geometry crops cannot be bound to the current run",
        stage_id=_STAGE,
        reason=reason,
    )


def _one_stage(rows: tuple[StageResultRow, ...]) -> StageResultRow:
    matches = tuple(row for row in rows if row.stage_id == _STAGE)
    if len(matches) != 1:
        raise _refuse("geometry_stage_missing_or_duplicate")
    row = matches[0]
    try:
        version = default_registry().stage(_STAGE).stage_version
    except Exception as exc:  # a broken registry is a refusal, not a guessed version
        raise _refuse("geometry_stage_registry_unavailable") from exc
    if row.status != "succeeded" or row.stage_version != version:
        raise _refuse("geometry_stage_not_succeeded")
    return row


def _read_refs(row: StageResultRow, *, max_input_bytes: int) -> tuple[ArtifactRef, ...]:
    if type(max_input_bytes) is not int or max_input_bytes < 1:
        raise _refuse("invalid_input_byte_ceiling")
    roles: set[str] = set()
    ids: set[str] = set()
    refs: list[ArtifactRef] = []
    total = 0
    for raw in row.artifacts:
        if not isinstance(raw, Mapping):
            raise _refuse("invalid_saved_artifact_reference")
        try:
            ref = ArtifactRef(**dict(raw))
        except (TypeError, ValueError):
            raise _refuse("invalid_saved_artifact_reference") from None
        if (
            ref.role not in _REQUIRED | {ROLE_CROP_IMAGE}
            or (ref.role in _REQUIRED and ref.role in roles)
            or ref.blob_id in ids
            or ref.size_bytes < 1
            or ref.media_type != (
                "image/png" if ref.role == ROLE_CROP_IMAGE else ARTIFACT_MEDIA_TYPE
            )
        ):
            raise _refuse("invalid_saved_artifact_reference")
        roles.add(ref.role)
        ids.add(ref.blob_id)
        if ref.role in _READ:
            total += ref.size_bytes
            if total > max_input_bytes:
                raise _refuse("saved_crop_input_too_large")
            refs.append(ref)
    if not _REQUIRED <= roles:
        raise _refuse("saved_geometry_artifact_missing")
    return tuple(refs)


def _read_exact(store: BlobStore, ref: ArtifactRef) -> bytes:
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
                    raise _refuse("saved_blob_size_mismatch")
                content.extend(chunk)
        finally:
            chunks.close()
    except StorageError as exc:
        raise _refuse("saved_blob_unreadable") from exc
    if len(content) != ref.size_bytes:
        raise _refuse("saved_blob_size_mismatch")
    return bytes(content)


def load_saved_image_crops(
    session: Session,
    *,
    authority: AttemptAuthority,
    blob_store: BlobStore,
    max_input_bytes: int,
    runs: RunRepository | None = None,
    jobs: JobRepository | None = None,
) -> SavedImageCropInput:
    """Bind saved StageResult/Blob reads to the current Attempt in one transaction.

    ``require_current`` locks Run → Job → Attempt → Lease. The caller owns this
    transaction and should finish it promptly: these locks are held during the
    object reads. A later provider effect needs its own authority check/journal.
    """
    run_repo = runs or RunRepository()
    job_repo = jobs or JobRepository()
    job_repo.require_current(session, authority)
    run = run_repo.get(session, authority.run_id)
    if run.state != "running" or run.run_id != authority.run_id:
        raise _refuse("running_run_required")
    stage = _one_stage(run_repo.stage_results(session, authority.run_id))
    refs = _read_refs(stage, max_input_bytes=max_input_bytes)
    payloads = {ref.blob_id: _read_exact(blob_store, ref) for ref in refs}
    try:
        checked = check_saved_crop_bytes(
            run_id=authority.run_id,
            version_uid=run.version_uid,
            stage=RunScopedGeometryStage(
                run_id=authority.run_id,
                stage_id=stage.stage_id,
                stage_version=stage.stage_version,
                status=stage.status,
                artifacts=stage.artifacts,
            ),
            supplied_blob_bytes=payloads,
        )
    except SavedCropCustodyRefused as exc:
        raise _refuse("saved_crop_integrity_invalid") from exc
    job_repo.require_current(session, authority)
    if run_repo.get(session, authority.run_id) != run:
        raise _refuse("run_changed_during_crop_read")
    if _one_stage(run_repo.stage_results(session, authority.run_id)) != stage:
        raise _refuse("geometry_stage_changed_during_crop_read")
    return SavedImageCropInput(
        checked=checked,
        crop_bytes=tuple(
            (crop.blob.blob_id, payloads[crop.blob.blob_id])
            for crop in checked.cohort.crops
        ),
    )


__all__ = ["SavedImageCropInput", "load_saved_image_crops"]
