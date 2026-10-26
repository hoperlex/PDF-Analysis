"""Bind a marked OCR quote to one geometry-checked portal TEXT region.

This is an unserved evidence candidate. OCR character positions are offsets in
the recognised block body, never offsets in the PDF text layer. The caller must
read both artifact documents with verified Blob references from the same run
and supply the version's stored ``textless_pages`` before calling this module.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Final, Mapping

from auditmanager.analysis.geometry.maths import GEOMETRY_OK
from auditmanager.analysis.recognised.artifact import (
    KIND_RECOGNISED_TEXT,
    QUOTE_SOURCE_RECOGNISED,
)
from auditmanager.analysis.recognised.portal import PORTAL_BLOCK_ID, TEXT
from auditmanager.analysis.profiles.ar_shared.recognised_context import (
    RecognisedContextError,
    select_context,
)
from auditmanager.shared.identity import IdentityError, VersionUid


_DIGEST: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}\Z")
_BLOCK_KEYS: Final[frozenset[str]] = frozenset({
    "portal_block_id", "page_number", "page_label", "ordinal", "block_type",
    "status", "bbox_norm", "geometry",
})
_PAGE_KEYS: Final[frozenset[str]] = frozenset({
    "page_number", "width_px", "height_px", "rotation_deg", "geometry",
})
_STATUS: Final[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9_]{0,39}\Z")


class RecognisedRegionRefused(ValueError):
    """The supplied OCR quote has no unique, trustworthy portal region."""


@dataclass(frozen=True, slots=True)
class RecognisedRegionCandidate:
    version_uid: str
    portal_block_id: str
    page_number: int
    quote: str
    quote_source: str
    ocr_char_start: int
    ocr_char_end: int
    bbox_norm: tuple[float, float, float, float]
    polygon_points: tuple[tuple[float, float], ...] | None
    quality_flags: tuple[str, ...]
    results_sha256: str
    blocks_sha256: str


def _unit(value: object) -> bool:
    return (
        type(value) in (int, float)
        and math.isfinite(value)
        and 0 <= value <= 1
    )


def _region(block: Mapping[str, Any]) -> tuple[
    tuple[float, float, float, float], tuple[tuple[float, float], ...] | None
]:
    keys = set(block)
    if keys not in (_BLOCK_KEYS, _BLOCK_KEYS | {"polygon_points"}):
        raise RecognisedRegionRefused("portal_block_invalid")
    bbox = block["bbox_norm"]
    if not isinstance(bbox, list) or len(bbox) != 4 or not all(_unit(n) for n in bbox):
        raise RecognisedRegionRefused("portal_region_invalid")
    x0, y0, x1, y1 = (float(n) for n in bbox)
    if x0 >= x1 or y0 >= y1:
        raise RecognisedRegionRefused("portal_region_invalid")
    raw_polygon = block.get("polygon_points")
    if raw_polygon is None:
        if "polygon_points" in block:
            raise RecognisedRegionRefused("portal_region_invalid")
        return (x0, y0, x1, y1), None
    if (
        not isinstance(raw_polygon, list)
        or not 3 <= len(raw_polygon) <= 64
        or any(
            not isinstance(point, list)
            or len(point) != 2
            or not all(_unit(n) for n in point)
            for point in raw_polygon
        )
    ):
        raise RecognisedRegionRefused("portal_region_invalid")
    polygon = tuple((float(point[0]), float(point[1])) for point in raw_polygon)
    return (x0, y0, x1, y1), polygon


def bind_recognised_region_candidate(
    *,
    version_uid: str,
    textless_pages: tuple[int, ...] | None,
    recognised_document: Mapping[str, Any],
    portal_blocks_document: Mapping[str, Any],
    portal_block_id: str,
    page_number: int,
    quote: str,
) -> RecognisedRegionCandidate:
    """Return a unique exact OCR quote and its checked region, or refuse.

    No filename, image description, PDF text offset or model result is used.
    This candidate is not a published finding or a sealed W56b citation.
    """
    try:
        VersionUid.parse(version_uid)
    except IdentityError:
        raise RecognisedRegionRefused("version_identity_invalid") from None
    if (
        not isinstance(portal_block_id, str)
        or PORTAL_BLOCK_ID.fullmatch(portal_block_id) is None
        or type(page_number) is not int or page_number < 1
        or not isinstance(quote, str) or not quote.strip()
    ):
        raise RecognisedRegionRefused("quote_claim_invalid")
    try:
        select_context(
            recognised_document,
            version_uid=version_uid,
            textless_pages=textless_pages,
        )
    except RecognisedContextError as exc:
        raise RecognisedRegionRefused(str(exc)) from None
    if textless_pages is None or page_number not in textless_pages:
        raise RecognisedRegionRefused("page_not_textless")

    if not isinstance(portal_blocks_document, Mapping) or any(
        portal_blocks_document.get(key) != expected for key, expected in (
            ("artifact_role", "geometry.portal_blocks"),
            ("artifact_version", "1.0.0"),
            ("version_uid", version_uid),
        )
    ):
        raise RecognisedRegionRefused("portal_artifact_mismatch")
    blocks_digest = portal_blocks_document.get("blocks_sha256")
    results_digest = recognised_document.get("results_sha256")
    if (
        not isinstance(blocks_digest, str) or _DIGEST.fullmatch(blocks_digest) is None
        or not isinstance(results_digest, str) or _DIGEST.fullmatch(results_digest) is None
    ):
        raise RecognisedRegionRefused("source_digest_invalid")
    pages = portal_blocks_document.get("pages")
    blocks = portal_blocks_document.get("blocks")
    if not isinstance(pages, list) or not isinstance(blocks, list):
        raise RecognisedRegionRefused("portal_artifact_invalid")

    page_matches = [
        page for page in pages
        if isinstance(page, Mapping) and page.get("page_number") == page_number
    ]
    block_matches = [
        block for block in blocks
        if isinstance(block, Mapping) and block.get("portal_block_id") == portal_block_id
    ]
    text_matches = [
        entry for entry in recognised_document["entries"]
        if entry["portal_block_id"] == portal_block_id
    ]
    if len(page_matches) != 1 or len(block_matches) != 1 or len(text_matches) != 1:
        raise RecognisedRegionRefused("region_binding_ambiguous_or_absent")
    page, block, entry = page_matches[0], block_matches[0], text_matches[0]
    if (
        set(page) != _PAGE_KEYS
        or type(page["page_number"]) is not int
        or any(type(page[name]) is not int or page[name] < 1
               for name in ("width_px", "height_px"))
        or type(page["rotation_deg"]) is not int
        or page["rotation_deg"] not in (0, 90, 180, 270)
    ):
        raise RecognisedRegionRefused("portal_page_invalid")
    if page.get("geometry") != GEOMETRY_OK or block.get("geometry") != GEOMETRY_OK:
        raise RecognisedRegionRefused("portal_geometry_unverified")
    if (
        block.get("page_number") != page_number
        or type(block.get("page_number")) is not int
        or block.get("block_type") != TEXT
        or entry["page_number"] != page_number
        or entry["kind"] != KIND_RECOGNISED_TEXT
        or entry["quote_source"] != QUOTE_SOURCE_RECOGNISED
    ):
        raise RecognisedRegionRefused("region_source_mismatch")
    bbox, polygon = _region(block)
    if (
        type(block["page_label"]) is not int or block["page_label"] < 1
        or (block["ordinal"] is not None and
            (type(block["ordinal"]) is not int or block["ordinal"] < 0))
        or not isinstance(block["status"], str)
        or _STATUS.fullmatch(block["status"]) is None
    ):
        raise RecognisedRegionRefused("portal_block_invalid")
    body = entry["text"]
    start = body.find(quote)
    if start < 0:
        raise RecognisedRegionRefused("quote_absent_from_recognised_block")
    if body.find(quote, start + 1) >= 0:
        raise RecognisedRegionRefused("quote_ambiguous_in_recognised_block")
    return RecognisedRegionCandidate(
        version_uid=version_uid,
        portal_block_id=portal_block_id,
        page_number=page_number,
        quote=quote,
        quote_source=QUOTE_SOURCE_RECOGNISED,
        ocr_char_start=start,
        ocr_char_end=start + len(quote),
        bbox_norm=bbox,
        polygon_points=polygon,
        quality_flags=tuple(entry["flags"]),
        results_sha256=results_digest,
        blocks_sha256=blocks_digest,
    )
