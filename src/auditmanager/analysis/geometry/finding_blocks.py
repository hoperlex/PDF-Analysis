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
2. For each of them, the **line's box** as a whole -- never a part of it. The extractor joins words that stand side by side
   at one height into one line with one space for any gap (a label, a 300 pt gap and a value are one line of 40 characters),
   and the block index keeps the line's box and its span of characters but not where each character stands. A cut of the box
   at the evidence's fraction of the line's characters (what this rule did until `D-353`'s measurement) places the evidence
   by a guess that is wrong where the gap is: the value of a label/value row landed in the label's block. So the only
   statement the data supports is "the evidence is somewhere on this line".
3. A portal block **holds** the evidence of a line when the evidence is certainly inside it: the block extends over the
   **whole width** of the line (give or take :data:`EDGE_TOLERANCE` of the page's width: the stored boxes are rounded and a
   hand-drawn rectangle is not exact) **and** covers at least :data:`COVERAGE` of the line's height. A block inside another
   block (a table in a drawing area) holds it too: the relation is to every block that holds the evidence, never to one
   chosen among them.
4. A finding's blocks are the blocks that hold any of its evidence, in the portal's own order.

What the rule does not claim
----------------------------
It claims containment, which the geometry proves, and nothing more. Known misses, each of them a **missing** link:

* a line that crosses a block's edge (a table row whose cells are blocks of their own, two columns joined at one height)
  holds its evidence in no block: where along the line the evidence stands is not in the data, and a guess is how a finding
  came to be linked to a block that does not contain its quotation. The text layer's per-character positions would settle
  it (`D-353`);
* an evidence in the gap between blocks, or in a line that no block covers over its whole width (a stamp's text the portal
  did not box, a block the portal did not detect), has no block;
* a page whose portal raster does not describe the PDF page (``geometry_mismatch``, or an aspect or rotation the text
  layer's page does not share -- what a page with a CropBox of another aspect than its MediaBox looks like to this check) has
  no link at all, and is named in ``unlinked_pages`` so that its blocks are not read as "no findings".

What it can still get wrong, because the data to see it is not published: a page whose text-layer coordinates are not the
portal's (a MediaBox whose origin is not 0, or a CropBox of the MediaBox's aspect; the extractor measures the MediaBox and the
portal rasterises what a viewer shows). :func:`linkable_pages` refuses such a page when a line of it lies outside the page,
which proves the shift, but a page whose shifted lines still fall inside it passes (`D-353`).

Evidence is never moved to a block it is not in, and the stored evidence is never touched.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from auditmanager.analysis.geometry.maths import GEOMETRY_OK, check_page

__all__ = [
    "COVERAGE",
    "EDGE_TOLERANCE",
    "EvidenceSpan",
    "PortalBox",
    "TextLine",
    "link_evidence",
    "linkable_pages",
]

#: The share of a line's height a block must cover to hold the line: at least half.
COVERAGE: Final[float] = 0.5

#: How far a block may fall short of a line's left or right end and still extend over the whole line, as a share of the page's
#: width (0.5 %, about 3 pt on A4): the stored boxes are rounded to four digits and a drawn rectangle is not exact.
EDGE_TOLERANCE: Final[float] = 0.005

#: How far a line may lie outside its page before the page is taken to be shifted, in points: the glyph boxes of a font may
#: reach a hair past the edge of the page they are set on.
OUTSIDE_TOLERANCE_PT: Final[float] = 2.0


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
    lines: Mapping[int, Sequence[TextLine]] | None = None,
) -> dict[int, tuple[float, float]]:
    """The pages on which a link can be derived, with the page's size in points.

    A page qualifies when the portal's own check of its raster against the PDF passed
    (``geometry: ok``) **and** the raster describes the text layer's page just as well: the
    same rotation and an aspect within the tolerance the crops use (``check_page``). The
    second condition is the one that keeps the text layer's coordinates and the portal's
    normalised ones on one page: the extractor measures the MediaBox, the portal's raster
    shows what a viewer shows.

    ``lines`` (the text-layer lines by page) adds a third: a page with a line **outside** the page
    (:data:`OUTSIDE_TOLERANCE_PT`) is refused, because a text on the page cannot lie outside it, so the
    coordinates are not the page's -- the extractor reports positions from the MediaBox's origin, and a
    MediaBox whose origin is not 0 shifts every box. This is evidence of a shift, not a test for one: a page
    shifted by less than the margin of its text passes, as does a CropBox of the MediaBox's aspect (neither
    is in the data the guard reads; `D-353`).
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
        if verdict != GEOMETRY_OK:
            continue
        if lines is not None and _shifted(lines.get(number, ()), width, height):
            continue
        usable[number] = (width, height)
    return usable


def _shifted(lines: Sequence[TextLine], width: float, height: float) -> bool:
    """Whether a line lies outside the page it is set on: the proof that the text layer's coordinates are not the page's."""
    return any(
        line.x0 < -OUTSIDE_TOLERANCE_PT
        or line.y0 < -OUTSIDE_TOLERANCE_PT
        or line.x1 > width + OUTSIDE_TOLERANCE_PT
        or line.y1 > height + OUTSIDE_TOLERANCE_PT
        for line in lines
    )


def _line_box(line: TextLine, width: float, height: float) -> tuple[float, float, float, float] | None:
    """The line's box normalised to the page; ``None`` when it is empty."""
    box = (line.x0 / width, line.y0 / height, line.x1 / width, line.y1 / height)
    return box if box[2] > box[0] and box[3] > box[1] else None


def _holds(box: tuple[float, float, float, float], block: PortalBox) -> bool:
    """Whether the evidence, wherever on the line ``box`` it stands, is inside ``block``.

    The block extends over the whole width of the line (within :data:`EDGE_TOLERANCE`) and covers at least
    :data:`COVERAGE` of its height.
    """
    if block.x0 > box[0] + EDGE_TOLERANCE or block.x1 < box[2] - EDGE_TOLERANCE:
        return False
    down = min(box[3], block.y1) - max(box[1], block.y0)
    return down > 0 and down / (box[3] - box[1]) >= COVERAGE


def link_evidence(
    evidence: Sequence[EvidenceSpan],
    *,
    lines: Mapping[int, Sequence[TextLine]],
    pages: Mapping[int, tuple[float, float]],
    blocks: Sequence[PortalBox],
) -> tuple[str, ...]:
    """The ids of the portal blocks that hold any of ``evidence``, in the order of ``blocks``.

    ``lines`` are the text-layer lines by page, ``pages`` the :func:`linkable_pages` (an evidence
    on another page links to nothing) and ``blocks`` the portal's blocks in the port's order. A page one of whose lines
    lies outside it links to nothing here either, whether or not the caller refused it in ``pages``.
    """
    by_page: dict[int, list[PortalBox]] = {}
    for block in blocks:
        by_page.setdefault(block.page_number, []).append(block)
    held: set[str] = set()
    for span in evidence:
        size = pages.get(span.page_number)
        if size is None or _shifted(lines.get(span.page_number, ()), size[0], size[1]):
            continue
        for line in lines.get(span.page_number, ()):
            if line.char_end <= span.char_start or line.char_start >= span.char_end:
                continue
            box = _line_box(line, size[0], size[1])
            if box is None:
                continue
            held.update(
                block.portal_block_id
                for block in by_page.get(span.page_number, ())
                if _holds(box, block)
            )
    return tuple(block.portal_block_id for block in blocks if block.portal_block_id in held)
