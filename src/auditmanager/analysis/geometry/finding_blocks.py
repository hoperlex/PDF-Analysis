"""Which portal blocks a finding's evidence sits in: pure, deterministic, no I/O (`UI-PARITY-C6`).

An evidence item of a finding is a span of the document-global text layer (``page_number``,
``char_start``, ``char_end``). The text-layer block index says where each extracted line of that
layer lies on its page, in points (``geometry.block_index``: the box of every line and the span
of characters it carries), and ``prepared.page_inventory`` says how large the page is. The
portal's block list (``geometry.portal_blocks``) says where each portal block lies on the same
page, normalised to the page. Putting the three together answers *where on the page the
evidence is* and *which portal blocks that place is inside*, with arithmetic and nothing else:
no model, no search of the quotation in the portal's recognised text (that text is the portal's
reading, not the text layer the evidence quotes), and nothing is stored.

The rule
--------
1. The lines of the evidence's page whose span of characters meets the evidence's span.
2. For each of them, the **evidence's box**: the line's height, and of the line's width the part
   its characters occupy -- the line's box cut at the same fraction of the line's characters as
   the evidence's span cuts the line's text. The cut matters because the extractor joins words
   that stand side by side at one height into one line, so a line of a two-column page crosses
   the columns, and the whole line would be in neither.
3. A portal block **holds** the evidence when it covers at least :data:`COVERAGE` of that box's
   area. A block inside another block (a table in a drawing area) holds it too: the relation is
   to every block that holds the evidence, never to one chosen among them.
4. A finding's blocks are the blocks that hold any of its evidence, in the portal's own order.

Known misses, each of them a **missing** link and never a wrong one:

* a page whose portal raster does not describe the PDF page (``geometry_mismatch``, or an
  aspect or rotation the text layer's page does not share -- what a page with a CropBox smaller
  than its MediaBox looks like to this check) has no link at all, and is named in
  ``unlinked_pages`` so that its blocks are not read as "no findings";
* the cut of rule 2 is proportional to characters, an estimate where the glyph widths differ
  much (a proportional font next to a wide numeral): an evidence in the gap between two
  blocks that neither covers by half has no block;
* an evidence in a text-layer line that no portal block covers by half (a stamp's text the
  portal did not box, a block the portal did not detect) has no block.

Evidence is never moved to a block it is not in, and the stored evidence is never touched.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from auditmanager.analysis.geometry.maths import GEOMETRY_OK, check_page

__all__ = [
    "COVERAGE",
    "EvidenceSpan",
    "PortalBox",
    "TextLine",
    "link_evidence",
    "linkable_pages",
]

#: The share of the evidence's box a block must cover to hold it: at least half.
COVERAGE: Final[float] = 0.5


@dataclass(frozen=True, slots=True)
class TextLine:
    """One block of ``geometry.block_index`` (an extracted line), box in points, top-left origin."""

    page_number: int
    char_start: int
    char_end: int
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True, slots=True)
class PortalBox:
    """One block of ``geometry.portal_blocks`` with its box normalised to its page, top-left origin."""

    portal_block_id: str
    page_number: int
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True, slots=True)
class EvidenceSpan:
    page_number: int
    char_start: int
    char_end: int


def linkable_pages(
    portal_pages: Iterable[Mapping[str, object]],
    inventory_pages: Mapping[int, Mapping[str, object]],
) -> dict[int, tuple[float, float]]:
    """The pages on which a link can be derived, with the page's size in points.

    A page qualifies when the portal's own check of its raster against the PDF passed
    (``geometry: ok``) **and** the raster describes the text layer's page just as well: the
    same rotation and an aspect within the tolerance the crops use (``check_page``). The
    second condition is the one that keeps the text layer's coordinates and the portal's
    normalised ones on one page: the extractor measures the MediaBox, the portal's raster
    shows what a viewer shows.
    """
    usable: dict[int, tuple[float, float]] = {}
    for page in portal_pages:
        number = int(page["page_number"])  # type: ignore[call-overload]
        if page.get("geometry") != GEOMETRY_OK:
            continue
        inventory = inventory_pages.get(number)
        if inventory is None:
            continue
        width, height = float(inventory["width_pt"]), float(inventory["height_pt"])  # type: ignore[arg-type]
        verdict = check_page(
            portal_width_px=int(page["width_px"]),  # type: ignore[call-overload]
            portal_height_px=int(page["height_px"]),  # type: ignore[call-overload]
            portal_rotation=int(page["rotation_deg"]),  # type: ignore[call-overload]
            page_width_pt=width,
            page_height_pt=height,
            page_rotation=int(inventory["rotation_deg"]),  # type: ignore[call-overload]
        )
        if verdict == GEOMETRY_OK:
            usable[number] = (width, height)
    return usable


def _evidence_box(
    line: TextLine, span: EvidenceSpan, width: float, height: float
) -> tuple[float, float, float, float] | None:
    """The part of ``line`` the evidence occupies, normalised to the page; ``None`` when it is empty."""
    length = line.char_end - line.char_start
    start, end = max(span.char_start, line.char_start), min(span.char_end, line.char_end)
    if length <= 0 or end <= start:
        return None
    left = line.x0 + (start - line.char_start) / length * (line.x1 - line.x0)
    right = line.x0 + (end - line.char_start) / length * (line.x1 - line.x0)
    box = (left / width, line.y0 / height, right / width, line.y1 / height)
    return box if box[2] > box[0] and box[3] > box[1] else None


def _covered(box: tuple[float, float, float, float], block: PortalBox) -> float:
    """The share of ``box``'s area that ``block`` covers."""
    across = min(box[2], block.x1) - max(box[0], block.x0)
    down = min(box[3], block.y1) - max(box[1], block.y0)
    if across <= 0 or down <= 0:
        return 0.0
    return across * down / ((box[2] - box[0]) * (box[3] - box[1]))


def link_evidence(
    evidence: Sequence[EvidenceSpan],
    *,
    lines: Mapping[int, Sequence[TextLine]],
    pages: Mapping[int, tuple[float, float]],
    blocks: Sequence[PortalBox],
) -> tuple[str, ...]:
    """The ids of the portal blocks that hold any of ``evidence``, in the order of ``blocks``.

    ``lines`` are the text-layer lines by page, ``pages`` the :func:`linkable_pages` (an evidence
    on another page links to nothing) and ``blocks`` the portal's blocks in the port's order.
    """
    by_page: dict[int, list[PortalBox]] = {}
    for block in blocks:
        by_page.setdefault(block.page_number, []).append(block)
    held: set[str] = set()
    for span in evidence:
        size = pages.get(span.page_number)
        if size is None:
            continue
        for line in lines.get(span.page_number, ()):
            if line.char_end <= span.char_start or line.char_start >= span.char_end:
                continue
            box = _evidence_box(line, span, size[0], size[1])
            if box is None:
                continue
            held.update(
                block.portal_block_id
                for block in by_page.get(span.page_number, ())
                if _covered(box, block) >= COVERAGE
            )
    return tuple(block.portal_block_id for block in blocks if block.portal_block_id in held)
