"""The portal's block list (`<stem>_blocks.json`), built to the measured format.

A block is a region of a page the portal recognised: TEXT and IMAGE blocks carry an
ordinal (a running document-wide number in reading order) and a crop URL; a STAMP block
carries neither. Identifiers are digests of the stem, the kind and a running number, so
the same inputs always give the same list.

Coordinates are normalised to the page, top-left origin, as the schema says
(`coordinate_space: normalized_page_top_left`).
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from collections.abc import Sequence

from . import portal_format as fmt
from .pdffacts import PageFacts

Box = tuple[float, float, float, float]
Point = tuple[float, float]

_RANK = {fmt.KIND_TEXT: 0, fmt.KIND_IMAGE: 1, fmt.KIND_STAMP: 2}


@dataclass(frozen=True)
class ImageNote:
    """The portal's description of an IMAGE block. Shown to a person, never analysed."""

    drawing_type: str
    axes: tuple[str, ...]
    summary: str
    description: str
    entities: tuple[str, ...]


@dataclass(frozen=True)
class Block:
    kind: str
    page_index: int
    bbox: Box                                   # x0, y0, x1, y1 in [0, 1]
    polygon: tuple[Point, ...] | None = None    # a polygon block's own vertices
    text: str = ""                              # TEXT: the recognised markdown
    image: ImageNote | None = None              # IMAGE: the portal's description
    fields: tuple[tuple[str, str], ...] = ()    # STAMP: the fields it was read as
    status: str = "recognized"
    ordinal: int | None = None                  # set by `assign`
    block_id: str = ""                          # set by `assign`

    def __post_init__(self) -> None:
        if self.kind not in fmt.KINDS:
            raise ValueError(f"unknown block kind {self.kind!r}")
        if self.polygon is not None:
            xs = [x for x, _ in self.polygon]
            ys = [y for _, y in self.polygon]
            object.__setattr__(self, "bbox", (min(xs), min(ys), max(xs), max(ys)))


def assign(stem: str, blocks: Sequence[Block]) -> tuple[Block, ...]:
    """Put blocks in reading order and give each its ordinal and identifier.

    Reading order is page, then top edge, then left edge; the ordinal counts TEXT and
    IMAGE blocks only, because a stamp has none.
    """
    ordered = sorted(
        blocks, key=lambda b: (b.page_index, b.bbox[1], b.bbox[0], _RANK[b.kind])
    )
    ordinal = 0
    counts = {kind: 0 for kind in fmt.KINDS}
    placed: list[Block] = []
    for block in ordered:
        counts[block.kind] += 1
        number: int | None = None
        if block.kind != fmt.KIND_STAMP:
            ordinal += 1
            number = ordinal
        placed.append(dataclasses.replace(
            block, ordinal=number,
            block_id=fmt.block_id(stem, block.kind, counts[block.kind]),
        ))
    return tuple(placed)


def counts_by_kind(blocks: Sequence[Block]) -> dict[str, int]:
    return {kind: sum(1 for b in blocks if b.kind == kind) for kind in fmt.KINDS}


def _block_json(block: Block) -> dict[str, object]:
    polygon = None
    if block.polygon is not None:
        polygon = [[round(x, 6), round(y, 6)] for x, y in block.polygon]
    return {
        "block_id": block.block_id,
        "ordinal": block.ordinal,
        "page_index": block.page_index,
        "page_label": block.page_index + 1,
        "block_type": block.kind,
        "shape_type": "polygon" if block.polygon is not None else "rectangle",
        "status": block.status,
        "export_status": block.status,
        "coords_norm": [round(v, 6) for v in block.bbox],
        "polygon_points": polygon,
        "crop_url": None if block.kind == fmt.KIND_STAMP else fmt.crop_url(block.block_id),
    }


def blocks_document(
    stem: str, pages: Sequence[PageFacts], blocks: Sequence[Block],
    *, display_path: str,
) -> dict[str, object]:
    """The block list as a JSON-ready dictionary, keys in the portal's order."""
    return {
        "schema_version": fmt.SCHEMA_VERSION,
        "document_id": fmt.document_id(stem),
        "document_name": f"{stem}.pdf",
        "document_path": display_path,
        "generated_at": fmt.GENERATED_AT_JSON,
        "coordinate_space": fmt.COORDINATE_SPACE,
        "pages": [
            {
                "page_index": index,
                "width_px": fmt.page_px(page.width_pt),
                "height_px": fmt.page_px(page.height_pt),
                "rotation": page.rotation,
            }
            for index, page in enumerate(pages)
        ],
        "blocks": [_block_json(b) for b in blocks],
    }


def dump(document: dict[str, object]) -> bytes:
    """Serialise like the portal does: two-space indent, UTF-8 as is, no trailing newline."""
    return json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
