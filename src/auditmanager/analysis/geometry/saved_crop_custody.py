"""Check supplied saved geometry refs and bytes before future IMAGE analysis.

This pure seam verifies the values it receives. The caller must obtain the
stage row from a run-scoped repository read and the bytes from BlobStore; this
module cannot attest that those external reads happened or fence an Attempt.
"""

from __future__ import annotations

import hashlib
import io
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from PIL import Image, UnidentifiedImageError

from auditmanager.analysis.engine.registry import default_registry
from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.engine.serialization import ARTIFACT_MEDIA_TYPE, canonical_bytes
from auditmanager.analysis.geometry.crop_cohort import (
    CropCohortRefused,
    ImageCropCandidate,
    ImageCropCohort,
    prepare_image_crop_cohort,
)
from auditmanager.analysis.ports.artifacts import (
    ROLE_BLOCK_INDEX,
    ROLE_CROP_IMAGE,
    ROLE_PAGE_CROPS,
    ROLE_PORTAL_BLOCKS,
)
from auditmanager.shared.identity import IdentityError, RunId, VersionUid


_STAGE: Final[str] = "page_geometry_extraction"
_SINGLE_ROLES: Final[frozenset[str]] = frozenset({
    ROLE_BLOCK_INDEX, ROLE_PORTAL_BLOCKS, ROLE_PAGE_CROPS,
})
_ALLOWED_ROLES: Final[frozenset[str]] = _SINGLE_ROLES | {ROLE_CROP_IMAGE}


class SavedCropCustodyRefused(ValueError):
    """The supplied stage row and bytes do not agree as one crop input."""


@dataclass(frozen=True, slots=True)
class RunScopedGeometryStage:
    """One supplied row from an authoritative run-scoped stage-result read.

    `StageResultRow` itself has no `run_id`; the future runs adapter attaches
    the query's exact run ID here. Constructing this value alone proves no DB
    provenance.
    """

    run_id: str
    stage_id: str
    stage_version: str
    status: str
    artifacts: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True, slots=True)
class CheckedCropBytes:
    """A pure check of supplied bytes, with no persisted-readback claim."""

    run_id: str
    cohort: ImageCropCohort
    checked_blob_sha256: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class PreparedCropItem:
    """Complete checked metadata and one eligible IMAGE crop, without PNG bytes."""

    run_id: str
    cohort: ImageCropCohort
    crop: ImageCropCandidate


@dataclass(frozen=True, slots=True)
class CheckedCropItem:
    """One decoded PNG whose bytes agree with its saved cohort reference."""

    prepared: PreparedCropItem
    checked_blob_sha256: tuple[str, str]


def _stage_refs(stage: RunScopedGeometryStage, run_id: str) -> dict[str, ArtifactRef]:
    try:
        expected_version = default_registry().stage(_STAGE).stage_version
    except Exception as exc:  # a missing registry is a refusal, never a version guess
        raise SavedCropCustodyRefused("stage_registry_unavailable") from exc
    if (
        not isinstance(stage, RunScopedGeometryStage)
        or stage.run_id != run_id
        or stage.stage_id != _STAGE
        or stage.stage_version != expected_version
        or stage.status != "succeeded"
        or not isinstance(stage.artifacts, tuple)
    ):
        raise SavedCropCustodyRefused("saved_stage_identity_or_status_invalid")
    refs: dict[str, ArtifactRef] = {}
    ids: set[str] = set()
    for raw in stage.artifacts:
        if not isinstance(raw, Mapping):
            raise SavedCropCustodyRefused("saved_artifact_reference_invalid")
        try:
            ref = ArtifactRef(**dict(raw))
        except (TypeError, ValueError):
            raise SavedCropCustodyRefused("saved_artifact_reference_invalid") from None
        if (
            ref.role not in _ALLOWED_ROLES
            or ref.size_bytes < 1
            or ref.blob_id in ids
            or ref.media_type != (
                "image/png" if ref.role == ROLE_CROP_IMAGE else ARTIFACT_MEDIA_TYPE
            )
            or (ref.role in _SINGLE_ROLES and ref.role in refs)
        ):
            raise SavedCropCustodyRefused("saved_artifact_reference_invalid")
        ids.add(ref.blob_id)
        if ref.role in _SINGLE_ROLES:
            refs[ref.role] = ref
        else:
            refs[ref.blob_id] = ref
    if not _SINGLE_ROLES <= {ref.role for ref in refs.values()}:
        raise SavedCropCustodyRefused("saved_geometry_artifact_missing")
    return refs


def _bytes(ref: ArtifactRef, payloads: Mapping[str, bytes]) -> bytes:
    payload = payloads.get(ref.blob_id)
    if (
        type(payload) is not bytes
        or len(payload) != ref.size_bytes
        or hashlib.sha256(payload).hexdigest() != ref.sha256
    ):
        raise SavedCropCustodyRefused("supplied_blob_bytes_mismatch")
    return payload


def _document(ref: ArtifactRef, payloads: Mapping[str, bytes]) -> Mapping[str, Any]:
    payload = _bytes(ref, payloads)
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise SavedCropCustodyRefused("supplied_artifact_json_invalid") from None
    if not isinstance(decoded, dict):
        raise SavedCropCustodyRefused("supplied_artifact_json_invalid")
    try:
        canonical = canonical_bytes(decoded)
    except (TypeError, ValueError):
        raise SavedCropCustodyRefused("supplied_artifact_json_invalid") from None
    if canonical != payload:
        raise SavedCropCustodyRefused("supplied_artifact_not_canonical")
    return decoded


def _verify_png(payload: bytes, *, width: int, height: int) -> None:
    try:
        with Image.open(io.BytesIO(payload)) as image:
            if image.format != "PNG" or image.size != (width, height):
                raise SavedCropCustodyRefused("crop_png_shape_mismatch")
            image.load()
    except SavedCropCustodyRefused:
        raise
    except (OSError, ValueError, UnidentifiedImageError):
        raise SavedCropCustodyRefused("crop_png_unreadable") from None


def check_saved_crop_bytes(
    *,
    run_id: str,
    version_uid: str,
    stage: RunScopedGeometryStage,
    supplied_blob_bytes: Mapping[str, bytes],
) -> CheckedCropBytes:
    """Verify one supplied stage row and all image Blob bytes as a whole."""
    try:
        RunId.parse(run_id)
        VersionUid.parse(version_uid)
    except IdentityError:
        raise SavedCropCustodyRefused("run_or_version_identity_invalid") from None
    if not isinstance(supplied_blob_bytes, Mapping):
        raise SavedCropCustodyRefused("supplied_blob_set_invalid")
    refs = _stage_refs(stage, run_id)
    portal_ref = refs[ROLE_PORTAL_BLOCKS]
    manifest_ref = refs[ROLE_PAGE_CROPS]
    crop_refs = {key: ref for key, ref in refs.items() if ref.role == ROLE_CROP_IMAGE}
    expected_payload_ids = {portal_ref.blob_id, manifest_ref.blob_id} | set(crop_refs)
    if set(supplied_blob_bytes) != expected_payload_ids:
        raise SavedCropCustodyRefused("supplied_blob_set_invalid")
    portal = _document(portal_ref, supplied_blob_bytes)
    manifest = _document(manifest_ref, supplied_blob_bytes)
    try:
        cohort = prepare_image_crop_cohort(
            version_uid=version_uid,
            portal_blocks_document=portal,
            crop_manifest_document=manifest,
        )
    except CropCohortRefused as exc:
        raise SavedCropCustodyRefused(f"crop_cohort_invalid:{exc}") from None
    expected_crop_ids = {candidate.blob.blob_id for candidate in cohort.crops}
    if set(crop_refs) != expected_crop_ids or any(
        crop_refs[candidate.blob.blob_id] != candidate.blob
        for candidate in cohort.crops
    ):
        raise SavedCropCustodyRefused("saved_crop_reference_mismatch")
    for candidate in cohort.crops:
        payload = _bytes(candidate.blob, supplied_blob_bytes)
        _verify_png(payload, width=candidate.width_px, height=candidate.height_px)
    return CheckedCropBytes(
        run_id=run_id,
        cohort=cohort,
        checked_blob_sha256=tuple(
            (ref.blob_id, ref.sha256) for ref in crop_refs.values()
        ),
    )


def prepare_saved_crop_item(
    *,
    run_id: str,
    version_uid: str,
    stage: RunScopedGeometryStage,
    supplied_metadata_bytes: Mapping[str, bytes],
    portal_block_id: str,
) -> PreparedCropItem:
    """Check the *whole* saved IMAGE cohort using only its two JSON Blobs.

    All distinct saved crop references must match the complete manifest. This
    phase does not claim that any sibling PNG has been read or validated.
    """
    try:
        RunId.parse(run_id)
        VersionUid.parse(version_uid)
    except IdentityError:
        raise SavedCropCustodyRefused("run_or_version_identity_invalid") from None
    if not isinstance(supplied_metadata_bytes, Mapping):
        raise SavedCropCustodyRefused("supplied_blob_set_invalid")
    refs = _stage_refs(stage, run_id)
    portal_ref = refs[ROLE_PORTAL_BLOCKS]
    manifest_ref = refs[ROLE_PAGE_CROPS]
    if set(supplied_metadata_bytes) != {portal_ref.blob_id, manifest_ref.blob_id}:
        raise SavedCropCustodyRefused("supplied_blob_set_invalid")
    portal = _document(portal_ref, supplied_metadata_bytes)
    manifest = _document(manifest_ref, supplied_metadata_bytes)
    try:
        cohort = prepare_image_crop_cohort(
            version_uid=version_uid,
            portal_blocks_document=portal,
            crop_manifest_document=manifest,
        )
    except CropCohortRefused as exc:
        raise SavedCropCustodyRefused(f"crop_cohort_invalid:{exc}") from None
    crop_refs = {key: ref for key, ref in refs.items() if ref.role == ROLE_CROP_IMAGE}
    expected_crop_ids = {candidate.blob.blob_id for candidate in cohort.crops}
    if set(crop_refs) != expected_crop_ids or any(
        crop_refs[candidate.blob.blob_id] != candidate.blob
        for candidate in cohort.crops
    ):
        raise SavedCropCustodyRefused("saved_crop_reference_mismatch")
    if type(portal_block_id) is not str:
        raise SavedCropCustodyRefused("selected_crop_unavailable")
    selected = tuple(
        crop for crop in cohort.crops if crop.portal_block_id == portal_block_id
    )
    if len(selected) != 1:
        raise SavedCropCustodyRefused("selected_crop_unavailable")
    return PreparedCropItem(run_id, cohort, selected[0])


def check_saved_crop_item_bytes(
    *, prepared: PreparedCropItem, supplied_png_bytes: bytes
) -> CheckedCropItem:
    """Check SHA-256, size and decoded shape for one selected PNG only."""
    if (
        not isinstance(prepared, PreparedCropItem)
        or prepared.crop not in prepared.cohort.crops
    ):
        raise SavedCropCustodyRefused("selected_crop_unavailable")
    crop = prepared.crop
    payload = _bytes(crop.blob, {crop.blob.blob_id: supplied_png_bytes})
    _verify_png(payload, width=crop.width_px, height=crop.height_px)
    return CheckedCropItem(prepared, (crop.blob.blob_id, crop.blob.sha256))
