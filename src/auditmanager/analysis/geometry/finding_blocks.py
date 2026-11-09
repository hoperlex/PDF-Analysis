"""Which portal blocks a finding's evidence sits in: pure, deterministic, no I/O (`UI-PARITY-C6`).

An evidence item of a finding is a span of the document-global text layer (``page_number``,
``char_start``, ``char_end``). The text-layer block index says where each extracted line of that
layer lies on its page, in points (``geometry.block_index``: the box of every line and the span
of characters it carries), and ``prepared.page_inventory`` says how large the page is. The
portal's block list (``geometry.portal_blocks``) says where each portal block lies on the same
page, normalised to the page. Putting the three together answers *where on the page the
evidence is* and *which portal blocks that place is inside*, with arithmetic: no model, and
nothing is stored. Where the arithmetic cannot decide, an optional second witness (the rule's step 5) chooses among
the blocks a line crosses by the quotation's presence in their recognised text, and only then.

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
5. **The second witness** (`D-450`). For a line of the evidence that **no** block holds (step 3), and only when the caller hands
   over the recognised text of the portal's text blocks (``block_texts``) and the evidence's quotation (``EvidenceSpan.quote``):
   the **candidates** are the blocks of the page the line crosses (more than :data:`EDGE_TOLERANCE` of the page's width across
   the line's box and at least :data:`COVERAGE` of its height) that have recognised text; the line's block is the candidate whose
   text **contains the whole quotation**, and the link is made only when **exactly one** candidate does. Ambiguity (two
   candidates contain it), no match, a quotation of fewer than :data:`WITNESS_MIN_CHARACTERS` characters once folded, and a
   missing quotation or text give no link. The comparison is over words: case, ``ё``/``е``, soft and end-of-line hyphens, runs of
   whitespace and punctuation are folded away (:func:`fold_text`), and the quotation's words must be a contiguous run of the
   block's words. A line some block holds is never given to the witness: geometry that proves containment is not second-guessed
   by a reading.
What the rule does not claim
----------------------------
It claims containment, which the geometry proves, and nothing more. Known misses, each of them a **missing** link:

* a line that crosses a block's edge (a table row whose cells are blocks of their own, two columns joined at one height)
  holds its evidence in no block **by geometry**: where along the line the evidence stands is not in the data, and a guess is
  how a finding came to be linked to a block that does not contain its quotation. The second witness (step 5) recovers the
  link where the recognised text names exactly one of the crossed blocks; where it does not (a quotation that is short, that
  the reading garbled, that two crossed blocks both contain, a multi-block quotation) the link stays missing. The text layer's
  per-character positions would settle it for good (`D-353`, `D-450`);
* an evidence in the gap between blocks, or in a line that no block covers over its whole width (a stamp's text the portal
  did not box, a block the portal did not detect), has no block;
* a page whose portal raster does not describe the PDF page (``geometry_mismatch``, or an aspect or rotation the text
  layer's page does not share -- what a page with a CropBox of another aspect than its MediaBox looks like to this check) has
  no link at all, and is named in ``unlinked_pages`` so that its blocks are not read as "no findings".

What it can still get wrong, because the data to see it is not published: a page whose text-layer coordinates are not the
portal's (a MediaBox whose origin is not 0, or a CropBox of the MediaBox's aspect; the extractor measures the MediaBox and the
portal rasterises what a viewer shows). :func:`linkable_pages` refuses such a page when a line of it lies outside the page,
which proves the shift, but a page whose shifted lines still fall inside it passes (`D-353`).

What the second witness can get wrong, and the geometry cannot: it trusts the portal's reading. A quotation that stands in a crossed
block whose recognised text garbled it, and that a **different** crossed block's text repeats, is linked to the latter: the one
way a link of this rule can be wrong. It is bounded (the candidates are only the blocks the line crosses, the text must contain
all of a quotation of at least :data:`WITNESS_MIN_CHARACTERS` characters, two matches give nothing), not excluded. The recognised
text must be the reading of **text** blocks: the portal's description of an image is not what the page says and is never passed.

A link by geometry is a containment the arithmetic proves; a link by the witness is a choice among the blocks a line crosses and is
as good as the recognised text. The stored evidence is never touched, and no evidence is linked to a block its line does not
cross.
"""

from __future__ import annotations

import re
import unicodedata
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
    "WITNESS_MIN_CHARACTERS",
    "fold_text",
    "link_evidence",
    "linkable_pages",
]

#: The share of a line's height a block must cover to hold the line: at least half.
COVERAGE: Final[float] = 0.5

#: How far a block may fall short of a line's left or right end and still extend over the whole line, as a share of the page's
#: width (0.5 %, about 3 pt on A4): the stored boxes are rounded to four digits and a drawn rectangle is not exact.
EDGE_TOLERANCE: Final[float] = 0.005

#: The least a quotation may be, folded (:func:`fold_text`: its words joined by single spaces), for the second witness to be asked.
#: A short quotation (a unit, a mark, a number) repeats across the cells of a row, and a reading's one wrong character in the
#: block that really holds it would hand the link to the block that happens to repeat it.
WITNESS_MIN_CHARACTERS: Final[int] = 8

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
    """An evidence's span of the text layer; ``quote`` (the quoted text, optional) is the second witness's input."""

    page_number: int
    char_start: int
    char_end: int
    quote: str | None = None


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


def _crosses(box: tuple[float, float, float, float], block: PortalBox) -> bool:
    """Whether the line's box passes through ``block``: more than :data:`EDGE_TOLERANCE` of the page's width of the line lies
    inside it, and it covers at least :data:`COVERAGE` of the line's height. A block that only grazes the line's end is not
    one the evidence can be said to be in."""
    across = min(box[2], block.x1) - max(box[0], block.x0)
    down = min(box[3], block.y1) - max(box[1], block.y0)
    return across > EDGE_TOLERANCE and down > 0 and down / (box[3] - box[1]) >= COVERAGE


_HYPHEN_AT_LINE_END = re.compile(r"[-\u2010\u2011]\s*\n\s*")
_WORD = re.compile(r"\w+")


def fold_text(text: str) -> str:
    """``text`` as the second witness compares it: the words only, joined by single spaces.

    Folded away: case, ``ё`` (to ``е``), compatibility forms (NFKC), soft hyphens, a hyphen at the end of a line together with
    the break (``строи-\\nтельство`` is ``строительство``), whitespace of any kind and punctuation. Pure and deterministic.
    """
    text = unicodedata.normalize("NFKC", text).casefold().replace("ё", "е").replace("\u00ad", "")
    return " ".join(_WORD.findall(_HYPHEN_AT_LINE_END.sub("", text)))


def link_evidence(
    evidence: Sequence[EvidenceSpan],
    *,
    lines: Mapping[int, Sequence[TextLine]],
    pages: Mapping[int, tuple[float, float]],
    blocks: Sequence[PortalBox],
    block_texts: Mapping[str, str] | None = None,
    witness_min_characters: int = WITNESS_MIN_CHARACTERS,
) -> tuple[str, ...]:
    """The ids of the portal blocks that hold any of ``evidence``, in the order of ``blocks``.

    ``lines`` are the text-layer lines by page, ``pages`` the :func:`linkable_pages` (an evidence
    on another page links to nothing) and ``blocks`` the portal's blocks in the port's order. A page one of whose lines
    lies outside it links to nothing here either, whether or not the caller refused it in ``pages``.

    ``block_texts`` (the recognised text of the portal's **text** blocks by block id) switches the second witness on (step 5 of
    the module's rule): for a line of an evidence whose ``quote`` is given and that no block holds, the one crossed block whose
    text contains the quotation is linked. ``None`` (the default) is the geometry alone, as before. ``witness_min_characters``
    is the shortest folded quotation the witness is asked about.
    """
    by_page: dict[int, list[PortalBox]] = {}
    for block in blocks:
        by_page.setdefault(block.page_number, []).append(block)
    folded: dict[str, str] = {}

    def text_of(block: PortalBox) -> str | None:
        """The block's folded recognised text padded with a space at both ends (a word-aligned containment test), if any."""
        if block.portal_block_id not in folded:
            text = None if block_texts is None else block_texts.get(block.portal_block_id)
            folded[block.portal_block_id] = f" {fold_text(text)} " if text else ""
        return folded[block.portal_block_id] or None

    held: set[str] = set()
    for span in evidence:
        size = pages.get(span.page_number)
        if size is None or _shifted(lines.get(span.page_number, ()), size[0], size[1]):
            continue
        quotation = fold_text(span.quote) if block_texts and span.quote else ""
        asked = len(quotation) >= witness_min_characters
        for line in lines.get(span.page_number, ()):
            if line.char_end <= span.char_start or line.char_start >= span.char_end:
                continue
            box = _line_box(line, size[0], size[1])
            if box is None:
                continue
            on_page = by_page.get(span.page_number, ())
            holding = [block.portal_block_id for block in on_page if _holds(box, block)]
            if holding:
                held.update(holding)
                continue
            if not asked:
                continue
            needle = f" {quotation} "
            matching = [
                block.portal_block_id for block in on_page
                if _crosses(box, block) and (text := text_of(block)) is not None and needle in text
            ]
            if len(matching) == 1:
                held.update(matching)
    return tuple(block.portal_block_id for block in blocks if block.portal_block_id in held)
