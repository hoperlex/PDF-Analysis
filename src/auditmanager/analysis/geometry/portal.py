"""The portal's block list, normalised into ``geometry.portal_blocks``: pure, no I/O.

`W55B-GEOMETRY-01` (``P02_SEAMS`` section 4.9). The stored ``_blocks.json`` is read twice
over, for two different questions:

* :func:`auditmanager.analysis.recognised.portal.read_block_list` -- `W55B-RECOGNISED-01`'s
  strict reader -- proves what both stages rely on: strict UTF-8 JSON, a ``pages`` list as
  long as the PDF has pages, and blocks with a well-formed unique ``blk_`` identifier, a type
  of the three and a page index on a page of the PDF. It is called first and not restated.
* :func:`read_layout` then reads what only this stage uses -- the page rasters, the page
  labels, ordinals, statuses, boxes and polygons -- and refuses anything it cannot use with
  ``analysis_input_invalid`` and ``reason: portal_blocks_invalid``, never skipping a block or
  repairing a value. Ingest held the bytes to the pinned schema at upload; bytes that fail
  here are a defect of storage or of a version published some other way.

What is never copied: ``crop_url`` (a capability URL the portal minted: never fetched, stored
or served), ``document_id``, ``document_name``, ``document_path``, ``generated_at``,
``shape_type`` and ``export_status``. The artifact is built from named fields only, so a
member the portal adds later cannot ride along.

``polygon_points`` reaches the artifact only when the portal gave a polygon: a ``null`` or an
empty list (the portal's spelling of a rectangle) is **left out**, never written as ``null``
or ``[]``, because the wire omits an absent optional member and its ``polygon_points`` holds
3 to 64 vertices when present.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from auditmanager.analysis.geometry.maths import GEOMETRY_OK, ROTATIONS
from auditmanager.analysis.recognised.portal import REASON_BLOCKS_INVALID, read_block_list
from auditmanager.shared.errors import DomainError, ErrorCode

#: The pinned schema's literals (``contracts/analysis/v1/portal-blocks.schema.json``).
SCHEMA_VERSION: Final[int] = 1
COORDINATE_SPACE: Final[str] = "normalized_page_top_left"
#: The portal's status token, as the pinned schema spells it.
_STATUS: Final[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9_]{0,39}")
#: A non-empty polygon holds this many vertices (the pinned schema's ``if``/``then``).
MIN_POLYGON_POINTS: Final[int] = 3
MAX_POLYGON_POINTS: Final[int] = 64

TEXT: Final[str] = "text"
IMAGE: Final[str] = "image"
STAMP: Final[str] = "stamp"


@dataclass(frozen=True, slots=True)
class PortalPage:
    """One page of the portal's raster, renumbered to the product's 1-based page number."""

    page_number: int
    width_px: int
    height_px: int
    rotation_deg: int


@dataclass(frozen=True, slots=True)
class PortalBlockGeometry:
    """One block of the list, with what the artifact keeps of it."""

    portal_block_id: str
    page_number: int
    page_label: int
    ordinal: int | None
    block_type: str
    status: str
    bbox_norm: tuple[float, float, float, float]
    polygon_points: tuple[tuple[float, float], ...] | None


@dataclass(frozen=True, slots=True)
class PortalLayout:
    """The block list, read and ordered. Built only by :func:`read_layout`."""

    blocks_sha256: str
    pages: tuple[PortalPage, ...]
    blocks: tuple[PortalBlockGeometry, ...]

    def page(self, page_number: int) -> PortalPage:
        return self.pages[page_number - 1]


def block_order(block: PortalBlockGeometry) -> tuple[int, bool, int, str]:
    """Page, ordinal (a null one last), then the identifier: ``P02_SEAMS`` section 4.9."""
    return (
        block.page_number,
        block.ordinal is None,
        0 if block.ordinal is None else block.ordinal,
        block.portal_block_id,
    )


def _invalid(message: str, stage_id: str | None) -> DomainError:
    details: dict[str, Any] = {"reason": REASON_BLOCKS_INVALID}
    if stage_id is not None:
        details["stage_id"] = stage_id
    return DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, message=message, **details)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_unit(value: object) -> bool:
    """A JSON number in [0, 1]."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0 <= value <= 1
    )


def _pages(document: Mapping[str, Any], page_count: int, stage_id: str | None) -> tuple[PortalPage, ...]:
    pages: dict[int, PortalPage] = {}
    for item in document["pages"]:
        if not isinstance(item, dict):
            raise _invalid("a page of the portal block list is not an object", stage_id)
        index = item.get("page_index")
        width = item.get("width_px")
        height = item.get("height_px")
        rotation = item.get("rotation")
        if not (
            _is_int(index)
            and 0 <= index < page_count
            and _is_int(width)
            and width >= 1
            and _is_int(height)
            and height >= 1
            and _is_int(rotation)
            and rotation in ROTATIONS
        ):
            raise _invalid(
                "a page of the portal block list lacks a well-formed index, raster size or "
                "rotation",
                stage_id,
            )
        if index in pages:
            raise _invalid("a page of the portal block list is repeated", stage_id)
        pages[index] = PortalPage(index + 1, width, height, rotation)
    if len(pages) != page_count:
        raise _invalid("the portal block list does not describe every page", stage_id)
    return tuple(pages[index] for index in range(page_count))


def _polygon(value: object, stage_id: str | None) -> tuple[tuple[float, float], ...] | None:
    if value is None or value == []:
        return None
    if (
        not isinstance(value, list)
        or not MIN_POLYGON_POINTS <= len(value) <= MAX_POLYGON_POINTS
        or not all(
            isinstance(point, list) and len(point) == 2 and all(_is_unit(c) for c in point)
            for point in value
        )
    ):
        raise _invalid(
            "a portal block's polygon is not 3 to 64 normalised vertices", stage_id
        )
    return tuple((float(point[0]), float(point[1])) for point in value)


def _block(item: Mapping[str, Any], stage_id: str | None) -> PortalBlockGeometry:
    label = item.get("page_label")
    ordinal = item.get("ordinal")
    status = item.get("status")
    coords = item.get("coords_norm")
    if not (_is_int(label) and label >= 1):
        raise _invalid("a portal block lacks a page label", stage_id)
    if ordinal is not None and not (_is_int(ordinal) and ordinal >= 0):
        raise _invalid("a portal block's ordinal is neither null nor a count", stage_id)
    if not (isinstance(status, str) and _STATUS.fullmatch(status)):
        raise _invalid("a portal block lacks a well-formed status", stage_id)
    if not (isinstance(coords, list) and len(coords) == 4 and all(_is_unit(c) for c in coords)):
        raise _invalid("a portal block's box is not four normalised coordinates", stage_id)
    x0, y0, x1, y1 = (float(c) for c in coords)
    if not (x0 < x1 and y0 < y1):
        raise _invalid("a portal block's box has no width or no height", stage_id)
    return PortalBlockGeometry(
        portal_block_id=item["block_id"],
        page_number=item["page_index"] + 1,
        page_label=label,
        ordinal=ordinal,
        block_type=item["block_type"],
        status=status,
        bbox_norm=(x0, y0, x1, y1),
        polygon_points=_polygon(item.get("polygon_points"), stage_id),
    )


def read_layout(raw: bytes, *, page_count: int, stage_id: str | None = None) -> PortalLayout:
    """The stored ``_blocks.json`` as this stage uses it, blocks in the section 4.9 order."""
    read_block_list(raw, page_count=page_count, stage_id=stage_id)
    document = json.loads(raw.decode("utf-8"))
    if (
        document.get("schema_version") != SCHEMA_VERSION
        or isinstance(document.get("schema_version"), bool)
        or document.get("coordinate_space") != COORDINATE_SPACE
    ):
        raise _invalid(
            "the portal block list is not schema version 1 in the normalised top-left space",
            stage_id,
        )
    pages = _pages(document, page_count, stage_id)
    blocks = tuple(sorted((_block(item, stage_id) for item in document["blocks"]), key=block_order))
    return PortalLayout(
        blocks_sha256=hashlib.sha256(raw).hexdigest(), pages=pages, blocks=blocks
    )


def page_entry(page: PortalPage, geometry: str) -> dict[str, Any]:
    """One ``pages`` entry of the artifact."""
    return {
        "page_number": page.page_number,
        "width_px": page.width_px,
        "height_px": page.height_px,
        "rotation_deg": page.rotation_deg,
        "geometry": geometry,
    }


def block_entry(block: PortalBlockGeometry, geometry: str) -> dict[str, Any]:
    """One ``blocks`` entry of the artifact; ``polygon_points`` only when there is a polygon."""
    entry: dict[str, Any] = {
        "portal_block_id": block.portal_block_id,
        "page_number": block.page_number,
        "page_label": block.page_label,
        "ordinal": block.ordinal,
        "block_type": block.block_type,
        "status": block.status,
        "bbox_norm": list(block.bbox_norm),
        "geometry": geometry,
    }
    if block.polygon_points:
        entry["polygon_points"] = [list(point) for point in block.polygon_points]
    return entry


def portal_blocks_body(layout: PortalLayout, verdicts: Mapping[int, str]) -> dict[str, Any]:
    """``blocks_sha256``, ``pages`` and ``blocks`` of ``geometry.portal_blocks``.

    ``verdicts`` maps each page number to its page-box check; a block repeats its page's.
    """
    return {
        "blocks_sha256": layout.blocks_sha256,
        "pages": [page_entry(page, verdicts[page.page_number]) for page in layout.pages],
        "blocks": [block_entry(block, verdicts[block.page_number]) for block in layout.blocks],
    }


def image_blocks_to_crop(
    layout: PortalLayout, verdicts: Mapping[int, str]
) -> tuple[PortalBlockGeometry, ...]:
    """The IMAGE blocks whose page passed the page-box check, in the artifact's order."""
    return tuple(
        block
        for block in layout.blocks
        if block.block_type == IMAGE and verdicts[block.page_number] == GEOMETRY_OK
    )


__all__ = [
    "COORDINATE_SPACE",
    "IMAGE",
    "MAX_POLYGON_POINTS",
    "MIN_POLYGON_POINTS",
    "SCHEMA_VERSION",
    "STAMP",
    "TEXT",
    "PortalBlockGeometry",
    "PortalLayout",
    "PortalPage",
    "block_entry",
    "block_order",
    "image_blocks_to_crop",
    "page_entry",
    "portal_blocks_body",
    "read_layout",
]
