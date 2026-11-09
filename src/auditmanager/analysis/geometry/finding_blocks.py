"""Which portal blocks a finding's evidence sits in: pure, deterministic, no I/O (`UI-PARITY-C6`).

An evidence item of a finding is a span of the document-global text layer (``page_number``,
``char_start``, ``char_end``). The text-layer block index says where each extracted line of that
layer lies on its page, in points (``geometry.block_index``: the box of every line and the span
of characters it carries), and ``prepared.page_inventory`` says how large the page is. The
portal's block list (``geometry.portal_blocks``) says where each portal block lies on the same
page, normalised to the page. Putting the three together answers *where on the page the
evidence is* and *which portal blocks that place is inside*, with arithmetic: no model, and
nothing is stored. Where the arithmetic cannot decide, an optional second witness (the rule's step 5) chooses among
the blocks a line touches by the quotation's presence in their recognised text, and only then, and only under conditions
that leave a missing link rather than a wrong one.

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
5. **The second witness** (`D-450`, `D-590`). For a line of the evidence that **no** block holds (step 3), and only when the caller hands
   over the portal's reading (``block_texts``: the recognised text of the portal's text blocks; ``doubtful_blocks``; ``page_texts``: the
   text layer's own text of each page) and the evidence's quotation (``EvidenceSpan.quote``), the line's block is the one **touching**
   block whose recognised text contains the whole quotation. Every one of these must hold, or there is **no link** (the direction of a
   doubt is a missing link):

   a. *The quotation is unique on its page.* Its folded words (:func:`fold_text`) occur exactly once, as a run of whole words, in the folded
      text of the evidence's page. The evidence is the **first** occurrence on the page (``resolve_anchor`` takes ``page.text.find``), so a
      text block that repeats the quotation elsewhere on the page is a match for the text and not for the place; with one occurrence the
      only place the quotation is printed is the line under test, and a block whose reading contains it is a block that reads that place.
      This is the root condition: it leaves no way for a repeated phrase to win. Nothing is asked of a quotation the page repeats, or one
      the page's text does not hold, or when ``page_texts`` is not handed over.
   b. *The quotation is long enough.* At least :data:`WITNESS_MIN_CHARACTERS` characters once folded.
   c. *Every block that touches the line has a reading to trust.* A block **touches** the line when more than :data:`EDGE_TOLERANCE` of the
      page's width of the line lies inside it and it covers at least :data:`TOUCH_COVERAGE` of the line's height (a block of less than the
      half that :data:`COVERAGE` asks of a *crossing* block still touches). A touching block with no recognised text (an image or a drawing
      area, a stamp, a text block nobody read, an empty body) or with a reading the caller names doubtful (a quality flag on it) cannot match
      and cannot veto, so it is **not** passed over: the witness abstains. Without this the quotation could stand in exactly the block that
      cannot speak and a neighbour's copy would win.
   d. *No stretch of the line is unboxed.* The touching blocks cover the line's width but for gaps of at most
      :data:`WITNESS_MAX_GAP_CHARACTERS` characters of the line (its width divided by its number of characters), the line's two ends
      included: a stamp's text the portal did not box, or a block it did not detect, may be exactly where the evidence stands.
   e. *Exactly one touching block contains the quotation*, as a run of whole words of its text (case, ``ё``/``е``, soft and end-of-line
      hyphens, whitespace and punctuation folded; a number keeps its sign and its decimal or range separator), and that block **crosses**
      the line (:data:`COVERAGE` of its height). Two matches give nothing.
   f. *No other touching block holds a near copy of it.* A near copy is an alignment of the quotation's words with a run of the block's words
      at a cost of at most a quarter of its words (:func:`_near_copy`): a word costs nothing when it is the same word or the same word with
      one letter wrong, extra or missing or with Latin look-alikes or a digit for a letter (:func:`skeleton`); a missing, an extra word and a
      word merged or split cost one. A damaged reading no quality flag names looks exactly so.

   A line some block holds is never given to the witness. The shipped caller (``BlockAdapter.list_run_finding_blocks``, `D-590`) hands the
   readings over whenever the version has a recognised-text document, and none when it has not: the relation is then steps 1 to 4.

What the rule does not claim
----------------------------
It claims containment, which the geometry proves, and nothing more. Known misses, each of them a **missing** link:

* a line that crosses a block's edge (a table row whose cells are blocks of their own, two columns joined at one height)
  holds its evidence in no block **by geometry**: where along the line the evidence stands is not in the data, and a guess is
  how a finding came to be linked to a block that does not contain its quotation. The second witness (step 5) recovers the
  link where the recognised text names exactly one of the touching blocks and every condition of step 5 holds; where it does not (a
  quotation that is short, that the page repeats, that the reading garbled, that a touching block cannot read, a multi-block quotation)
  the link stays missing. The text layer's per-character positions would settle it for good (`D-353`, `D-450`);
* an evidence in the gap between blocks, or in a line that no block covers over its whole width (a stamp's text the portal
  did not box, a block the portal did not detect), has no block;
* a page whose portal raster does not describe the PDF page (``geometry_mismatch``, or an aspect or rotation the text
  layer's page does not share -- what a page with a CropBox of another aspect than its MediaBox looks like to this check) has
  no link at all, and is named in ``unlinked_pages`` so that its blocks are not read as "no findings".

What it can still get wrong, because the data to see it is not published: a page whose text-layer coordinates are not the
portal's (a MediaBox whose origin is not 0, or a CropBox of the MediaBox's aspect; the extractor measures the MediaBox and the
portal rasterises what a viewer shows). :func:`linkable_pages` refuses such a page when a line of it lies outside the page,
which proves the shift, but a page whose shifted lines still fall inside it passes (`D-353`).

What the second witness can get wrong, and the geometry cannot: it trusts the portal's reading. With the quotation unique on its page, the
reading of the touching blocks all present and unflagged, and no stretch of the line unboxed, a link needs a portal that **reads a phrase
into a block that does not print it** (the same words from the raster at a place the text layer does not have), or a text layer whose
page text is not the page's. It is not excluded. The recognised text must be the reading of **text** blocks: the portal's description of
an image is not what the page says and is never passed (an image block is a block without a reading, step 5c).

A link by geometry is a containment the arithmetic proves; a link by the witness is a choice among the blocks a line touches and is
as good as the recognised text. The stored evidence is never touched, and no evidence is linked to a block its line does not
cross.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Final

from auditmanager.analysis.geometry.maths import GEOMETRY_OK, check_page

__all__ = [
    "COVERAGE",
    "EDGE_TOLERANCE",
    "EvidenceSpan",
    "PortalBox",
    "Readings",
    "TOUCH_COVERAGE",
    "TextLine",
    "WITNESS_MAX_GAP_CHARACTERS",
    "WITNESS_MIN_CHARACTERS",
    "fold_text",
    "link_evidence",
    "linkable_pages",
    "skeleton",
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

#: How many of a quotation's words (a quarter of them, rounded down) another touching block may differ in and still be a near copy of it.
NEAR_COPY_MISSES_PER_WORDS: Final[int] = 4

#: The share of a line's height a block must cover for the second witness to count the block as touching the line (and so to need its
#: reading): a block that covers less than the :data:`COVERAGE` of a *crossing* block still may be where the evidence stands.
TOUCH_COVERAGE: Final[float] = 0.1

#: The widest stretch of a line that no touching block covers, for the second witness to be asked, in characters of that line (its
#: width divided by its number of characters, so a line with a wide gap in it has wide "characters"): the gutter between two cells is
#: a few characters wide, a stamp's text the portal did not box is not.
WITNESS_MAX_GAP_CHARACTERS: Final[float] = 4.0

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


def _touches(box: tuple[float, float, float, float], block: PortalBox) -> bool:
    """Whether the block touches the line for the second witness: more than :data:`EDGE_TOLERANCE` of the page's width of the line lies
    inside it and it covers at least :data:`TOUCH_COVERAGE` of the line's height. Looser than :func:`_crosses` on purpose: a block that
    is not one the evidence can be said to be in may still be the one it stands in, and is then a block whose reading must be had."""
    across = min(box[2], block.x1) - max(box[0], block.x0)
    down = min(box[3], block.y1) - max(box[1], block.y0)
    return across > EDGE_TOLERANCE and down > 0 and down / (box[3] - box[1]) >= TOUCH_COVERAGE


def _uncovered(box: tuple[float, float, float, float], touching: Sequence[PortalBox]) -> float:
    """The widest stretch of the line's width (a share of the page's) that none of the blocks covers, the two ends of the line included."""
    cursor, widest = box[0], 0.0
    for left, right in sorted((max(block.x0, box[0]), min(block.x1, box[2])) for block in touching):
        widest = max(widest, left - cursor)
        cursor = max(cursor, right)
    return max(widest, box[2] - cursor)


_HYPHEN_AT_LINE_END = re.compile(r"[-\u2010\u2011]\s*\n\s*")
#: A word is a run of letters and digits. A number keeps what makes it that number: its sign (a minus or a plus that is not a hyphen
#: inside a word, standing before a digit) and the decimal, range or time separator between digits (``1,5``, ``1.5``, ``1-5`` and
#: ``1 5`` are four different tokens; ``табл. 2`` is not the start of ``табл. 2.5``).
_WORD = re.compile(r"(?:(?<![\w.,])[+\-\u2212\u2013](?=\d))?\w+(?:(?<=\d)[-\u2013./,:](?=\w)\w+)*")
_SIGNS = str.maketrans({"\u2212": "-", "\u2013": "-"})
_SIGN = re.compile(r"^[+\-]")

#: Letters and digits a reading takes for one another (Latin for Cyrillic look-alikes, a digit for a letter, a bar for a one): the
#: alphabet a damaged reading is compared in.
_LOOKALIKES = str.maketrans({
    "a": "а", "b": "в", "c": "с", "e": "е", "h": "н", "k": "к", "m": "м", "o": "о", "p": "р", "t": "т", "x": "х", "y": "у",
    "0": "о", "3": "з", "6": "б",
    "l": "1", "i": "1", "\u0456": "1", "\u0131": "1", "|": "1",
})


def fold_text(text: str) -> str:
    """``text`` as the second witness compares it: the words only, joined by single spaces.

    Folded away: case, ``ё`` (to ``е``), compatibility forms (NFKC; ``№`` is a separator, not ``No``), soft hyphens, a hyphen at the end
    of a line together with the break (``строи-\\nтельство`` is ``строительство``), whitespace of any kind and punctuation. Kept: a number's
    sign and its decimal or range separator (a minus and an en dash are one sign). Pure and deterministic.
    """
    text = unicodedata.normalize("NFKC", text.replace("\u2116", " ")).casefold().replace("ё", "е").replace("\u00ad", "")
    return " ".join(word.translate(_SIGNS) for word in _WORD.findall(_HYPHEN_AT_LINE_END.sub("", text)))


def skeleton(word: str) -> str:
    """A folded word in the alphabet a damaged reading is compared in: without its sign, Latin look-alikes of Cyrillic letters and
    a digit for a letter (``0``/``о``/``o``, ``3``/``з``, ``1``/``l``/``i``) written as one. Two words with one skeleton may be one word
    read two ways; used to find a near copy, never to match a quotation."""
    return _SIGN.sub("", word).translate(_LOOKALIKES)


@lru_cache(maxsize=1 << 16)
def _close(first: str, second: str) -> bool:
    """Two folded words that are one word read with at most one letter wrong, extra or missing (words of four letters and more)."""
    if first == second:
        return True
    if len(first) < 4 or len(second) < 4 or abs(len(first) - len(second)) > 1:
        return False
    if len(first) == len(second):
        return sum(a != b for a, b in zip(first, second)) == 1
    shorter, longer = sorted((first, second), key=len)
    return any(longer[:at] + longer[at + 1:] == shorter for at in range(len(longer)))


def _near_copy(quotation: Sequence[str], words: Sequence[str]) -> bool:
    """Whether ``words`` (skeleton words, :func:`skeleton`) hold a stretch the quotation's words (skeleton words) align with at a cost of
    at most a quarter of them, rounded down: a word costs nothing when it is the same or :func:`_close` to the one it is set against,
    one when it is set against another word, missing or extra, or when two of one side are one of the other (a space lost or added).
    What the same quotation looks like in a reading that damaged some of it. An approximate substring match over words (Sellers)."""
    length = len(quotation)
    allowed = length // NEAR_COPY_MISSES_PER_WORDS
    if length == 0 or not words:
        return False
    size = len(words)
    before: list[int] | None = None
    row = [0] * (size + 1)
    for i in range(1, length + 1):
        word = quotation[i - 1]
        joined = quotation[i - 2] + word if i >= 2 else None
        now = [0] * (size + 1)
        now[0] = i
        for j in range(1, size + 1):
            other = words[j - 1]
            best = row[j - 1] + (0 if _close(word, other) else 1)
            if row[j] + 1 < best:
                best = row[j] + 1
            if now[j - 1] + 1 < best:
                best = now[j - 1] + 1
            if before is not None and joined is not None and before[j - 1] + 1 < best and _close(joined, other):
                best = before[j - 1] + 1
            if j >= 2 and row[j - 2] + 1 < best and _close(word, words[j - 2] + other):
                best = row[j - 2] + 1
            now[j] = best
        if min(now) > allowed:
            return False
        before, row = row, now
    return min(row) <= allowed


class Readings:
    """The portal's reading of a page, folded once: what the second witness compares the evidence's quotation with.

    ``block_texts`` (the recognised text of the portal's **text** blocks by block id), ``doubtful_blocks`` (the blocks whose reading is
    not to be trusted: flagged, empty, unread) and ``page_texts`` (the text layer's own text of each page, the text the evidence's
    offsets index). A block is **trusted** when it has a text that folds to something and is not doubtful; a block of any other kind
    (an image, a stamp) has no text here, so it is not trusted. The folds are made on first use and kept; the memo only ever holds what
    a recomputation would give, so one object can be shared by concurrent readers. :meth:`active` says whether the witness can be asked
    at all: with no text of any block or no text of the pages it cannot.
    """

    __slots__ = ("_texts", "_doubtful", "_pages", "_folded", "_words", "_page_folds", "_copies")

    def __init__(
        self, block_texts: Mapping[str, str] | None, doubtful_blocks: Collection[str] = (),
        page_texts: Mapping[int, str] | None = None,
    ) -> None:
        self._texts = block_texts or {}
        self._doubtful = frozenset(doubtful_blocks)
        self._pages = page_texts
        self._folded: dict[str, str] = {}
        self._words: dict[str, tuple[str, ...]] = {}
        self._page_folds: dict[int, str] = {}
        self._copies: dict[tuple[tuple[str, ...], str], bool] = {}

    @property
    def active(self) -> bool:
        return bool(self._texts) and self._pages is not None

    def text(self, block_id: str) -> str | None:
        """The block's folded text padded with a space at both ends (a word-aligned containment test), or ``None`` when it has none."""
        if block_id not in self._folded:
            folded = fold_text(self._texts.get(block_id) or "")
            self._folded[block_id] = f" {folded} " if folded else ""
        return self._folded[block_id] or None

    def trusted(self, block_id: str) -> bool:
        return block_id not in self._doubtful and self.text(block_id) is not None

    def occurrences(self, page_number: int, quotation: str) -> int | None:
        """How many times the folded ``quotation`` occurs in the folded text of the page, as a run of whole words (overlaps counted);
        ``None`` when the page's text is not known."""
        if self._pages is None or page_number not in self._pages:
            return None
        if page_number not in self._page_folds:
            self._page_folds[page_number] = f" {fold_text(self._pages[page_number])} "
        page, needle, count, at = self._page_folds[page_number], f" {quotation} ", 0, 0
        while (found := page.find(needle, at)) >= 0:
            count, at = count + 1, found + 1
        return count

    def near_copy(self, quotation: tuple[str, ...], block_id: str) -> bool:
        """Whether the block's text holds a near copy of the quotation (``quotation``: its skeleton words)."""
        key = (quotation, block_id)
        if key not in self._copies:
            if block_id not in self._words:
                self._words[block_id] = tuple(skeleton(word) for word in (self.text(block_id) or "").split())
            self._copies[key] = _near_copy(quotation, self._words[block_id])
        return self._copies[key]


def link_evidence(
    evidence: Sequence[EvidenceSpan],
    *,
    lines: Mapping[int, Sequence[TextLine]],
    pages: Mapping[int, tuple[float, float]],
    blocks: Sequence[PortalBox],
    block_texts: Mapping[str, str] | None = None,
    doubtful_blocks: Collection[str] = (),
    page_texts: Mapping[int, str] | None = None,
    readings: Readings | None = None,
    witness_min_characters: int = WITNESS_MIN_CHARACTERS,
    witness_max_gap_characters: float | None = WITNESS_MAX_GAP_CHARACTERS,
) -> tuple[str, ...]:
    """The ids of the portal blocks that hold any of ``evidence``, in the order of ``blocks``.

    ``lines`` are the text-layer lines by page, ``pages`` the :func:`linkable_pages` (an evidence
    on another page links to nothing) and ``blocks`` the portal's blocks in the port's order. A page one of whose lines
    lies outside it links to nothing here either, whether or not the caller refused it in ``pages``.

    The second witness (step 5 of the module's rule) is switched on by the portal's reading: ``block_texts`` (the recognised text of
    the portal's **text** blocks by block id), ``doubtful_blocks`` (blocks whose reading may be wrong: a quality flag on it; a block with
    no text in ``block_texts`` is not trusted either) and ``page_texts`` (the text layer's text of each page, which says whether the
    quotation is unique on its page), or ``readings`` (a :class:`Readings` the caller built once for them and keeps; not together with
    the three). Without ``block_texts`` or without ``page_texts`` it is the geometry alone, as before the witness.
    ``witness_min_characters`` is the shortest folded quotation the witness is asked about, ``witness_max_gap_characters`` the widest
    stretch of a line, in characters of that line, the touching blocks may leave uncovered (``None``: no limit; an ablation, not a
    policy).
    """
    if readings is not None and (block_texts or doubtful_blocks or page_texts is not None):
        raise ValueError("readings replaces block_texts, doubtful_blocks and page_texts; give one or the other")
    if readings is None and block_texts:
        readings = Readings(block_texts, doubtful_blocks, page_texts)
    if readings is not None and not readings.active:
        readings = None
    by_page: dict[int, list[PortalBox]] = {}
    for block in blocks:
        by_page.setdefault(block.page_number, []).append(block)

    held: set[str] = set()
    for span in evidence:
        size = pages.get(span.page_number)
        if size is None or _shifted(lines.get(span.page_number, ()), size[0], size[1]):
            continue
        quotation = fold_text(span.quote) if readings is not None and span.quote else ""
        asked = (
            bool(quotation) and len(quotation) >= witness_min_characters
            and readings is not None and readings.occurrences(span.page_number, quotation) == 1
        )
        needle, words = f" {quotation} ", tuple(skeleton(word) for word in quotation.split())
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
            if not asked or readings is None:
                continue
            touching = [block for block in on_page if _touches(box, block)]
            if any(not readings.trusted(block.portal_block_id) for block in touching):
                continue
            if witness_max_gap_characters is not None and _uncovered(box, touching) > max(
                EDGE_TOLERANCE, witness_max_gap_characters * (box[2] - box[0]) / max(1, line.char_end - line.char_start),
            ):
                continue
            matching = [block for block in touching if needle in (readings.text(block.portal_block_id) or "")]
            if len(matching) != 1 or not _crosses(box, matching[0]):
                continue
            if any(readings.near_copy(words, block.portal_block_id) for block in touching if block is not matching[0]):
                continue
            held.add(matching[0].portal_block_id)
    return tuple(block.portal_block_id for block in blocks if block.portal_block_id in held)
