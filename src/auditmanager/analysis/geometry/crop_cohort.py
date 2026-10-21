"""Complete, unserved W56b input cohort for W55b portal IMAGE crops.

The selector joins saved geometry documents only. It does not read PNG bytes,
choose a model or make a partial cohort look complete. The caller must prove
the two documents came from checksum-verified references of the same saved Run.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.geometry.maths import (
    GEOMETRY_MISMATCH,
    GEOMETRY_OK,
    MAX_PIXELS,
    MIN_LONG_SIDE_PX,
)
from auditmanager.analysis.recognised.portal import IMAGE, PORTAL_BLOCK_ID
from auditmanager.shared.identity import IdentityError, VersionUid


_DIGEST: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}\Z")
_STATUS: Final[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9_]{0,39}\Z")
_PORTAL_KEYS: Final[frozenset[str]] = frozenset({
    "artifact_role", "artifact_version", "version_uid", "blocks_sha256", "pages", "blocks",
})
_PAGE_KEYS: Final[frozenset[str]] = frozenset({
    "page_number", "width_px", "height_px", "rotation_deg", "geometry",
})
_BLOCK_KEYS: Final[frozenset[str]] = frozenset({
    "portal_block_id", "page_number", "page_label", "ordinal", "block_type",
    "status", "bbox_norm", "geometry",
})
_MANIFEST_KEYS: Final[frozenset[str]] = frozenset({
    "artifact_role", "artifact_version", "version_uid", "crop_policy", "crops",
})
_CROP_KEYS: Final[frozenset[str]] = frozenset({
    "portal_block_id", "page_number", "bbox_norm", "render_profile", "blob_id",
    "sha256", "size_bytes", "width_px", "height_px",
})
_RENDER_KEYS: Final[frozenset[str]] = frozenset({
    "renderer", "scale", "min_long_side_px", "max_pixels", "format",
})


class CropCohortRefused(ValueError):
    """The saved geometry cannot form a complete trusted crop input cohort."""


@dataclass(frozen=True, slots=True)
class ImageCropCandidate:
    portal_block_id: str
    page_number: int
    bbox_norm: tuple[float, float, float, float]
    blob: ArtifactRef
    width_px: int
    height_px: int


@dataclass(frozen=True, slots=True)
class SkippedImageBlock:
    portal_block_id: str
    page_number: int
    reason: str


@dataclass(frozen=True, slots=True)
class ImageCropCohort:
    version_uid: str
    blocks_sha256: str
    crops: tuple[ImageCropCandidate, ...]
    skipped: tuple[SkippedImageBlock, ...]


def _positive_int(value: object) -> bool:
    return type(value) is int and value > 0


def _unit(value: object) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and 0 <= value <= 1
    except OverflowError:
        return False


def _positive_finite(value: object) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and value > 0
    except OverflowError:
        return False


def _box(value: object) -> tuple[float, float, float, float]:
    if not isinstance(value, list) or len(value) != 4 or not all(_unit(n) for n in value):
        raise CropCohortRefused("region_invalid")
    x0, y0, x1, y1 = (float(n) for n in value)
    if x0 >= x1 or y0 >= y1:
        raise CropCohortRefused("region_invalid")
    return x0, y0, x1, y1


def _require_envelope(
    document: object, *, role: str, version_uid: str, keys: frozenset[str]
) -> Mapping[str, Any]:
    if (
        not isinstance(document, Mapping) or set(document) != keys
        or document.get("artifact_role") != role
        or document.get("artifact_version") != "1.0.0"
        or document.get("version_uid") != version_uid
    ):
        raise CropCohortRefused("artifact_role_version_or_shape_mismatch")
    return document


def _pages(document: Mapping[str, Any]) -> tuple[str, ...]:
    raw = document["pages"]
    if not isinstance(raw, list) or not raw:
        raise CropCohortRefused("portal_pages_invalid")
    verdicts: list[str] = []
    for index, page in enumerate(raw, start=1):
        if (
            not isinstance(page, Mapping) or set(page) != _PAGE_KEYS
            or type(page["page_number"]) is not int or page["page_number"] != index
            or not _positive_int(page["width_px"])
            or not _positive_int(page["height_px"])
            or type(page["rotation_deg"]) is not int
            or page["rotation_deg"] not in (0, 90, 180, 270)
            or page["geometry"] not in (GEOMETRY_OK, GEOMETRY_MISMATCH)
        ):
            raise CropCohortRefused("portal_pages_invalid")
        verdicts.append(page["geometry"])
    return tuple(verdicts)


def _image_blocks(
    document: Mapping[str, Any], verdicts: tuple[str, ...]
) -> tuple[tuple[Mapping[str, Any], ...], tuple[SkippedImageBlock, ...]]:
    raw = document["blocks"]
    if not isinstance(raw, list):
        raise CropCohortRefused("portal_blocks_invalid")
    seen: set[str] = set()
    order: list[tuple[int, bool, int, str]] = []
    eligible: list[Mapping[str, Any]] = []
    skipped: list[SkippedImageBlock] = []
    for block in raw:
        if not isinstance(block, Mapping) or set(block) not in (
            _BLOCK_KEYS, _BLOCK_KEYS | {"polygon_points"}
        ):
            raise CropCohortRefused("portal_blocks_invalid")
        identifier, page = block["portal_block_id"], block["page_number"]
        ordinal = block["ordinal"]
        if (
            not isinstance(identifier, str) or PORTAL_BLOCK_ID.fullmatch(identifier) is None
            or identifier in seen
            or not _positive_int(page) or page > len(verdicts)
            or not _positive_int(block["page_label"])
            or (ordinal is not None and (type(ordinal) is not int or ordinal < 0))
            or block["block_type"] not in ("text", IMAGE, "stamp")
            or not isinstance(block["status"], str)
            or _STATUS.fullmatch(block["status"]) is None
            or block["geometry"] != verdicts[page - 1]
        ):
            raise CropCohortRefused("portal_blocks_invalid")
        _box(block["bbox_norm"])
        polygon = block.get("polygon_points")
        if "polygon_points" in block and (
            not isinstance(polygon, list) or not 3 <= len(polygon) <= 64
            or any(
                not isinstance(point, list) or len(point) != 2
                or not all(_unit(n) for n in point)
                for point in polygon
            )
        ):
            raise CropCohortRefused("portal_blocks_invalid")
        seen.add(identifier)
        order.append((page, ordinal is None, ordinal or 0, identifier))
        if block["block_type"] == IMAGE:
            if block["geometry"] == GEOMETRY_OK:
                eligible.append(block)
            else:
                skipped.append(SkippedImageBlock(identifier, page, GEOMETRY_MISMATCH))
    if order != sorted(order):
        raise CropCohortRefused("portal_blocks_unordered")
    return tuple(eligible), tuple(skipped)


def _crop(record: object) -> ImageCropCandidate:
    if not isinstance(record, Mapping) or set(record) != _CROP_KEYS:
        raise CropCohortRefused("crop_record_invalid")
    identifier = record["portal_block_id"]
    profile = record["render_profile"]
    if (
        not isinstance(identifier, str) or PORTAL_BLOCK_ID.fullmatch(identifier) is None
        or not _positive_int(record["page_number"])
        or not _positive_int(record["size_bytes"])
        or not _positive_int(record["width_px"])
        or not _positive_int(record["height_px"])
        or record["width_px"] * record["height_px"] > MAX_PIXELS
        or max(record["width_px"], record["height_px"]) < MIN_LONG_SIDE_PX
        or not isinstance(profile, Mapping) or set(profile) != _RENDER_KEYS
        or not isinstance(profile["renderer"], str) or not profile["renderer"].strip()
        or not _positive_finite(profile["scale"])
        or type(profile["min_long_side_px"]) is not int
        or profile["min_long_side_px"] != MIN_LONG_SIDE_PX
        or type(profile["max_pixels"]) is not int
        or profile["max_pixels"] != MAX_PIXELS
        or profile["format"] != "png"
        or not isinstance(record["sha256"], str)
        or _DIGEST.fullmatch(record["sha256"]) is None
    ):
        raise CropCohortRefused("crop_record_invalid")
    bbox = _box(record["bbox_norm"])
    try:
        blob = ArtifactRef(
            role="geometry.crop_image", blob_id=record["blob_id"],
            sha256=record["sha256"], size_bytes=record["size_bytes"],
            media_type="image/png",
        )
    except (TypeError, ValueError):
        raise CropCohortRefused("crop_reference_invalid") from None
    return ImageCropCandidate(
        portal_block_id=identifier, page_number=record["page_number"],
        bbox_norm=bbox, blob=blob, width_px=record["width_px"],
        height_px=record["height_px"],
    )


def prepare_image_crop_cohort(
    *, version_uid: str, portal_blocks_document: Mapping[str, Any],
    crop_manifest_document: Mapping[str, Any],
) -> ImageCropCohort:
    """Demand a complete image-crop projection before any block analysis call."""
    try:
        VersionUid.parse(version_uid)
    except IdentityError:
        raise CropCohortRefused("version_identity_invalid") from None
    portal = _require_envelope(
        portal_blocks_document, role="geometry.portal_blocks", version_uid=version_uid,
        keys=_PORTAL_KEYS,
    )
    manifest = _require_envelope(
        crop_manifest_document, role="geometry.page_crops", version_uid=version_uid,
        keys=_MANIFEST_KEYS,
    )
    digest = portal["blocks_sha256"]
    if not isinstance(digest, str) or _DIGEST.fullmatch(digest) is None:
        raise CropCohortRefused("portal_source_digest_invalid")
    if manifest["crop_policy"] != "portal_image_blocks":
        raise CropCohortRefused("crop_policy_invalid")
    eligible, skipped = _image_blocks(portal, _pages(portal))
    records = manifest["crops"]
    if not isinstance(records, list):
        raise CropCohortRefused("crop_manifest_invalid")
    crops = tuple(_crop(record) for record in records)
    if len({crop.portal_block_id for crop in crops}) != len(crops):
        raise CropCohortRefused("crop_duplicate")
    if [crop.portal_block_id for crop in crops] != [
        block["portal_block_id"] for block in eligible
    ]:
        raise CropCohortRefused("crop_cohort_incomplete_or_extra")
    for crop, block in zip(crops, eligible):
        if (
            crop.page_number != block["page_number"]
            or crop.bbox_norm != _box(block["bbox_norm"])
        ):
            raise CropCohortRefused("crop_block_region_mismatch")
    return ImageCropCohort(version_uid, digest, crops, skipped)
