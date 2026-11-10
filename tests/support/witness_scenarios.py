"""Scenarios on which the second witness of the finding to block relation CAN link wrongly, and the ablations that show it (D-649).

`tests/support/measure_finding_blocks.py` reported "0 wrong" for the second witness on sets where a wrong link is impossible by
construction (quotations unique on their page, readings exact) and on one set where it abstained by an accident of its row template.
A figure of 0 means nothing about a rule that the measurement could not have made link wrongly. Here every scenario is a real PDF
(reportlab, a real text layer) with portal blocks and readings authored the way a portal fails, and each comes with the proof that it
can fail: the rule is called once per **subset of its guards removed**, and the scenario is worth something only if some subset links
wrongly (a link to a block that does not even touch the glyphs of the quotation, `finding_block_proof.analyse`).

The guards (step 5 of ``analysis/geometry/finding_blocks.py``), by the name used here:

* ``unique`` -- 5a, the quotation occurs once in the page's text layer;
* ``reading`` -- 5c, every block that touches the line has a reading to trust (an image, a stamp, an unread or a flagged text block
  makes the witness abstain);
* ``flags`` -- the part of ``reading`` that is a quality flag on a text block's reading (removed alone: only the flagged blocks are
  trusted, a block with no reading still is not);
* ``gap`` -- 5d, no stretch of the line wider than two of its heights is unboxed;
* ``near_copy`` -- 5f, no other touching block holds a near copy of the quotation.

(5e, exactly one touching block contains the quotation, is the witness itself and is never removed.)

The five scenarios of the debt row (each builder returns a :class:`Sheet`; ``SCENARIOS`` names them):

1. ``image_over_line`` -- a drawing sheet: callouts in a drawing area the portal made one IMAGE block, notes beside them at the same
   heights that repeat the callout, wrap it over two lines, or only have it read into them by a crop that bled;
2. ``two_word_schedule`` -- a schedule whose rows differ in two words of four and repeat their phrase in two cells, one reading damaged
   as ``degrade`` damages it (a letter short: no flag names it);
3. ``reading_damage`` -- the same repeat, the damage a portal makes of a building document's text (Latin look-alikes in a word and in a
   designation, a letter O for a zero, a lost space, a dropped sign, two short words), flagged and unflagged;
4. ``a1_residual`` -- the judge's A1: the quotation is unique on its page, the true block's reading is wrong in a way no flag names, and
   the neighbour's reading holds the quotation (a crop that bled, or a copy the text layer's order hides). Per damage class, combinations
   of the two faults show that it takes BOTH, and how often the rule then still links wrongly;
5. ``wide_gutter`` -- after `D-626`: gutters of 1 to 6 line heights between the blocks (the price), a cell the portal did not box with the
   neighbour's crop reading it, and the judge's A2b (a label in a stretch that four mean characters of a line with a wide gap let through).

Not product code. The readings are authored (``SheetBlock.reading``): a portal's, never a model's, and never a real portal's.
"""

from __future__ import annotations

import contextlib
import io
import unicodedata
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from typing import Any
from unittest import mock

import pdfplumber
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics

from auditmanager.analysis.geometry import finding_blocks as rule_module
from auditmanager.analysis.geometry.finding_blocks import (
    WITNESS_MAX_GAP_LINE_HEIGHTS,
    WITNESS_MIN_CHARACTERS,
    Readings,
    TextLine,
)
from auditmanager.analysis.stages.extraction import TEXT_OPTIONS
from tests.support import stress_layout_pdf as stress
from tests.support.finding_block_proof import (
    BlockFact,
    EvidenceFact,
    MemoOracle,
    PdfOracle,
    analyse,
    degrade,
    doubtful_blocks,
    figures,
    rule_links,
)

PAGE_W, PAGE_H = A4
ASCENT = 0.8 * stress.SIZE
#: The guards that can be removed, in the order a removed set is named.
GUARDS = ("unique", "reading", "flags", "gap", "near_copy")
SHIPPED = "shipped"
#: The pre-`D-626` unit of the unboxed-stretch limit, restated: four mean characters of the line (its width over its number of characters).
OLD_GAP_CHARACTERS = 4.0
OLD_UNIT = "gap_old_unit"


# -- the sheets ----------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Quote:
    """One authored finding: ``text`` quoted on ``page``; ``kind`` names the case it belongs to (the label of its figures)."""

    kind: str
    page: int
    text: str


@dataclass(frozen=True, slots=True)
class SheetBlock:
    """A portal block: ``box`` in points of its page (top-left origin), ``reading`` its recognised text (``None``: an image)."""

    page: int
    kind: str
    box: tuple[float, float, float, float]
    reading: str | None = None


@dataclass(frozen=True, slots=True)
class Sheet:
    name: str
    note: str
    pdf: bytes
    blocks: tuple[SheetBlock, ...]
    quotes: tuple[Quote, ...]


def row_top(index: int) -> float:
    """The top of the line box of row ``index`` (from 1), top-left origin, in points: its height is the font size."""
    return PAGE_H - (stress.TOP - index * stress.LEADING) - ASCENT


def row_bottom(index: int) -> float:
    return row_top(index) + stress.SIZE


def text_width(text: str, size: float = stress.SIZE) -> float:
    stress.ensure_font()
    return pdfmetrics.stringWidth(text, "StressSans", size)


class SheetBuilder:
    def __init__(self, name: str, note: str) -> None:
        self.name, self.note = name, note
        self._pages: list[list[tuple[Any, ...]]] = []
        self._blocks: list[SheetBlock] = []
        self._quotes: list[Quote] = []

    def page(self, rows: Sequence[Sequence[tuple[Any, ...]]]) -> int:
        self._pages.append([tuple(row) for row in rows])
        return len(self._pages)

    def block(
        self, page: int, x0: float, x1: float, readings: Sequence[str | None] | None = None, *, kind: str = "text",
        rows: tuple[int, int] | None = None,
    ) -> None:
        """A block over the rows ``rows`` (default: all of the page's) between ``x0`` and ``x1``; its reading is the lines of
        ``readings`` (a ``None`` is a line the portal skipped)."""
        first, last = rows or (1, len(self._pages[page - 1]))
        box = (x0, row_top(first) - 3.0, x1, row_bottom(last) + 3.0)
        reading = None if readings is None else "\n".join(line for line in readings if line is not None)
        self._blocks.append(SheetBlock(page, kind, box, reading))

    def quote(self, kind: str, page: int, text: str) -> None:
        self._quotes.append(Quote(kind, page, text))

    def build(self) -> Sheet:
        return Sheet(self.name, self.note, stress.build_grid(self._pages), tuple(self._blocks), tuple(self._quotes))


# -- the words (every pool has at least 40 distinct words, so that rows differ in every position) ----------

NOUNS = (
    "плита", "балка", "колонна", "перемычка", "ригель", "панель", "стойка", "связь", "опора", "анкер", "фундамент", "перегородка",
    "кровля", "стяжка", "фасад", "лестница", "шахта", "проём", "лоток", "колодец", "труба", "кабель", "стена", "дверь", "окно",
    "пандус", "карниз", "парапет", "цоколь", "отмостка", "арматура", "каркас", "настил", "прогон", "раскос", "подкос", "консоль",
    "диафрагма", "ростверк", "свая",
)
ADJECTIVES = (
    "стальная", "сборная", "бетонная", "несущая", "навесная", "входная", "нижняя", "верхняя", "боковая", "угловая", "торцевая",
    "сварная", "болтовая", "наружная", "кирпичная", "стеклянная", "ребристая", "листовая", "трубчатая", "профильная", "кровельная",
    "фасадная", "цокольная", "клееная", "лёгкая", "тяжёлая", "гладкая", "глухая", "рабочая", "общая", "полная", "малая", "узкая",
    "прямая", "косая", "двойная", "тройная", "составная", "свободная", "жёсткая",
)
LETTERS = "АБВГДЕЖИКЛ"


def pick(pool: Sequence[str], index: int, stride: int) -> str:
    """The ``index``-th word of ``pool`` at ``stride``: distinct for 40 consecutive indices when the stride is coprime to 40."""
    return pool[(index * stride) % len(pool)]


def noun(index: int, stride: int = 3) -> str:
    return pick(NOUNS, index, stride)


def adjective(index: int, stride: int = 7) -> str:
    return pick(ADJECTIVES, index, stride)


# -- damage classes: what a portal's reading does to a phrase (D-643) ------------------------------------

TO_LATIN = str.maketrans("аеорсх", "aeopcx")


@dataclass(frozen=True, slots=True)
class DamageClass:
    """A way a reading goes wrong: ``phrase(i)`` the row's text as the PDF prints it, ``damage(i, phrase)`` what the portal reads
    instead (``None``: the line is skipped). ``flagged`` is whether a quality flag (`analysis/recognised/flags`) names the damage;
    ``caught`` whether the rule's near-copy veto is expected to see the damaged text for a copy of the phrase."""

    name: str
    phrase: Callable[[int], str]
    damage: Callable[[int, str], str | None]
    flagged: bool
    caught: bool
    sparse: int = 1                # one row in `sparse` is damaged by `damage_class_rows`; the others are read exactly


def _swap(words: list[str], at: int, value: str) -> str:
    words = list(words)
    words[at] = value
    return " ".join(words)


DAMAGE_CLASSES: dict[str, DamageClass] = {c.name: c for c in (
    DamageClass(
        "latin_in_word", lambda i: f"{noun(i)} {adjective(i)} {i}",
        lambda i, p: _swap(p.split(), 1, p.split()[1].translate(TO_LATIN)), flagged=True, caught=True),
    DamageClass(
        "latin_designation", lambda i: f"{noun(i)} из бетона класса B{20 + i}",
        lambda i, p: p.replace(f"B{20 + i}", f"В{20 + i}"), flagged=False, caught=True),
    DamageClass(
        "letter_o_for_zero", lambda i: f"{noun(i)} {adjective(i)} шаг {i}00 мм",
        lambda i, p: p.replace(f"{i}00", f"{i}OO"), flagged=False, caught=True),
    DamageClass(
        "lost_space", lambda i: f"{noun(i)} из керамического кирпича марки {i}",
        lambda i, p: p.replace("из керамического", "изкерамического"), flagged=False, caught=True),
    DamageClass(
        "sign_dropped", lambda i: f"отм. -{i}.{(i * 37) % 1000:03d} низ {noun(i)}",
        lambda i, p: p.replace(f"-{i}.", f"{i}.", 1), flagged=False, caught=True),
    DamageClass(
        "two_short_words", lambda i: f"отм. +{i}.000 пол 1 этажа {noun(i)} {adjective(i)}",
        lambda i, p: p.replace(f"+{i}.000", f"+{i}.ООО").replace(" 1 ", " I "), flagged=False, caught=True),
    DamageClass(
        "digit_for_letter", lambda i: f"{noun(i)} Зона {i} {adjective(i)}",
        lambda i, p: p.replace("Зона", "3она"), flagged=False, caught=True),
    # What the near-copy veto does not see, a quality flag does: a word garbled into a mixed script.
    DamageClass(
        "garbled_mixed_script", lambda i: f"{noun(i)} {adjective(i)} {i}",
        lambda i, p: _swap(p.split(), 1, p.split()[1][:4] + "shtu"), flagged=True, caught=False),
    # What the near-copy veto does not see: the judge's A1 classes.
    DamageClass("skipped_line", lambda i: f"{noun(i)} {adjective(i)} {i}", lambda i, p: None, flagged=False, caught=False),
    DamageClass(
        "word_swapped_of_3", lambda i: f"{adjective(i)} {noun(i)} {i}",
        lambda i, p: _swap(p.split(), 0, adjective(i + 13)), flagged=False, caught=False),
    DamageClass(
        "two_words_of_5", lambda i: f"{noun(i)} {adjective(i)} {noun(i, 11)} {adjective(i, 13)} {i}",
        lambda i, p: _swap(p.split()[:1] + [adjective(i + 17)] + p.split()[2:], 3, adjective(i + 19)), flagged=False, caught=False),
)}
#: Flagged damage on one row in ten: the whole block's reading carries the flag, whichever row is damaged.
SPARSE_FLAGGED = DamageClass(
    "flagged_one_row_in_ten", DAMAGE_CLASSES["latin_in_word"].phrase, DAMAGE_CLASSES["latin_in_word"].damage, flagged=True,
    caught=True, sparse=10,
)


# -- scenario 1: an image block over the line ------------------------------------------------------------


#: The damage classes of scenario 3 (a portal's reading of a building document), in the order they are drawn.
PORTAL_DAMAGE = (
    "latin_in_word", "latin_designation", "letter_o_for_zero", "digit_for_letter", "lost_space", "sign_dropped", "two_short_words",
    "garbled_mixed_script",
)


def image_over_line(rows: int = 30) -> Sheet:
    """A drawing sheet. The callouts are drawn in an area the portal made one IMAGE block (no reading); the notes stand at the same
    heights, so the extractor joins each callout and its note into one line that crosses the image and the notes block and which
    neither holds. The finding quotes the callout (the FIRST occurrence on the page). Kinds:

    * ``repeat`` -- the note prints the callout again: the quotation occurs twice in the text layer;
    * ``wrapped`` -- the note prints it wrapped over two rows, so the extractor interleaves it with the next row's callout and the text
      layer holds the quotation ONCE although the notes' reading holds it whole (the unique-quotation gate is blind to it);
    * ``bleed`` -- the note prints something else, but the notes' reading holds the callout (the crop of the notes bled into the drawing);
    * ``clean`` -- the note prints something else and is read exactly: the control, the quotation is in no reading.
    """
    sheet = SheetBuilder("witness_image", "a drawing sheet: callouts in an IMAGE block, notes beside them at the same heights")
    for kind in ("repeat", "wrapped", "bleed", "clean"):
        callouts = [f"{noun(i)} {adjective(i)} {i}" for i in range(1, rows + 1)]
        plain = [f"{i}) см. лист {i + 1}, узел {i}" for i in range(1, rows + 1)]
        if kind == "repeat":
            notes = [f"{i}) {callouts[i - 1]}" for i in range(1, rows + 1)]
            reads: list[str | None] = list(notes)
        elif kind == "wrapped":
            first = [c.split(" ", 1)[0] for c in callouts]
            second = [c.split(" ", 1)[1] for c in callouts]
            notes = [(f"{second[i - 2]}; " if i > 1 else "") + first[i - 1] for i in range(1, rows + 1)]
            notes.append(f"{second[-1]}.")
            reads = list(notes)
        elif kind == "bleed":
            notes, reads = plain, [f"{note} {callout}" for note, callout in zip(plain, callouts)]
        else:
            notes, reads = plain, list(plain)
        body = [[(60.0, callouts[i - 1]), (350.0, notes[i - 1])] for i in range(1, rows + 1)]
        if kind == "wrapped":
            body.append([(60.0, "Конец листа"), (350.0, notes[rows])])    # a callout of its own keeps the last wrap interleaved
        page = sheet.page(body)
        sheet.block(page, 44.0, 338.0, None, kind="image")
        sheet.block(page, 344.0, 560.0, reads)
        for callout in callouts:
            sheet.quote(kind, page, callout)
    return sheet.build()


# -- scenario 2: a schedule whose rows differ in two words of four --------------------------------------


DEGRADE_LEVELS: dict[str, tuple[float, bool]] = {
    "d00": (0.0, False), "d10": (0.1, False), "d30": (0.3, False), "d50": (0.5, False), "f30": (0.3, True),
}


def two_word_schedule(rows: int = 30) -> Sheet:
    """``Поз. n | Не <word>, п. n | the same phrase again | n шт.``: four columns, each its own block; the rows differ in two of the
    phrase's four words (the word and the number). The finding quotes the left phrase (the FIRST occurrence); the right cell repeats
    it, so the quotation occurs twice in the text layer. The left column's reading is damaged by ``degrade`` at the rate of the page's
    kind (``d10`` = a word in ten, a letter short, the damage no flag names; ``f30`` = a word in three written with a Latin look-alike,
    which a flag names). This is the judge's P5b with the damage of the measurement's own model."""
    sheet = SheetBuilder("witness_schedule", "a schedule, rows differing in two words of four, the phrase repeated in two cells")
    for level, (rate, flaggable) in DEGRADE_LEVELS.items():
        words = [noun(i, 7) for i in range(1, rows + 1)]
        phrases = [f"Не {words[i - 1]}, п. {i}" for i in range(1, rows + 1)]
        page = sheet.page([
            [(56.0, f"Поз. {i}"), (150.0, phrases[i - 1]), (330.0, phrases[i - 1]), (500.0, f"{i} шт.")] for i in range(1, rows + 1)
        ])
        left = degrade(f"{level}-left", "\n".join(phrases), rate, flaggable=flaggable)
        sheet.block(page, 50.0, 142.0, [f"Поз. {i}" for i in range(1, rows + 1)])
        sheet.block(page, 146.0, 324.0, left.split("\n"))
        sheet.block(page, 328.0, 494.0, phrases)
        sheet.block(page, 498.0, 560.0, [f"{i} шт." for i in range(1, rows + 1)])
        for phrase in phrases:
            sheet.quote(level, page, phrase)
    return sheet.build()


# -- scenarios 3 and 4: damage classes --------------------------------------------------------------------


def damage_class_rows(damage: DamageClass, rows: int) -> tuple[list[str], list[str | None]]:
    """The phrases of ``rows`` rows and the left block's reading of them (``None``: a skipped line)."""
    phrases = [damage.phrase(i) for i in range(1, rows + 1)]
    readings = [damage.damage(i, p) if i % damage.sparse == 0 else p for i, p in enumerate(phrases, start=1)]
    return phrases, readings


def reading_damage(rows: int = 24) -> Sheet:
    """``phrase | the same phrase again``: two columns, two blocks; the finding quotes the left phrase, the right cell repeats it (the
    quotation occurs twice in the text layer) and is read exactly. The left block's reading is damaged in the way of the page's kind,
    on every row (or on one row in ten for ``flagged_one_row_in_ten``, where the flag on the block's reading is the point)."""
    sheet = SheetBuilder("witness_damage", "two columns repeating a phrase, the left reading damaged as a portal damages it")
    for damage in (*(DAMAGE_CLASSES[name] for name in PORTAL_DAMAGE), SPARSE_FLAGGED):
        phrases, readings = damage_class_rows(damage, rows)
        page = sheet.page([[(56.0, p), (330.0, p)] for p in phrases])
        sheet.block(page, 50.0, 322.0, readings)
        sheet.block(page, 326.0, 584.0, phrases)
        for phrase in phrases:
            sheet.quote(damage.name, page, phrase)
    return sheet.build()


def a1_residual(rows: int = 40, wrapped_rows: int = 20) -> Sheet:
    """The judge's A1 and the damage classes of scenario 3, in layouts where the quotation occurs ONCE in the text layer although the
    neighbouring column's reading holds it. Two ways for that:

    * ``<class>/<combination>`` -- the right cell prints something else and the right block's reading holds the quotation because its
      crop bled into the left cell: a SECOND portal fault. Four combinations of the two faults per page (``--`` none, ``D-`` the left
      reading damaged in the page's class, ``-B`` bled only, ``DB`` both), ten rows of each;
    * ``wrapped:<class>/<combination>`` -- the right column prints the phrase itself, wrapped over two rows, so that the extractor
      interleaves its halves with the left cells of the next row and the text layer holds the quotation once while the right block's
      reading holds it whole. No second fault: a real copy that the text layer's order hides. Two combinations (``--`` and ``D-``).
    """
    sheet = SheetBuilder("witness_a1", "the quotation unique on its page; the left reading damaged and/or the right reading holding it")
    combinations_ = ("--", "D-", "-B", "DB")
    for damage in DAMAGE_CLASSES.values():
        phrases = [damage.phrase(i) for i in range(1, rows + 1)]
        own = [f"см. лист {i}, узел {i + 1}" for i in range(1, rows + 1)]
        kind = [combinations_[i % 4] for i in range(1, rows + 1)]
        left = [damage.damage(i, p) if kind[i - 1][0] == "D" else p for i, p in enumerate(phrases, start=1)]
        right = [f"{phrases[i - 1]} {own[i - 1]}" if kind[i - 1][1] == "B" else own[i - 1] for i in range(1, rows + 1)]
        page = sheet.page([[(56.0, phrases[i - 1]), (330.0, own[i - 1])] for i in range(1, rows + 1)])
        sheet.block(page, 50.0, 322.0, left)
        sheet.block(page, 326.0, 584.0, right)
        for i, phrase in enumerate(phrases, start=1):
            sheet.quote(f"{damage.name}/{kind[i - 1]}", page, phrase)
    for damage in DAMAGE_CLASSES.values():
        phrases = [damage.phrase(i) for i in range(1, wrapped_rows + 1)]
        halves = [(" ".join(p.split()[: len(p.split()) // 2]), " ".join(p.split()[len(p.split()) // 2:])) for p in phrases]
        notes = [(f"{halves[i - 2][1]}; " if i > 1 else "") + halves[i - 1][0] for i in range(1, wrapped_rows + 1)] + [f"{halves[-1][1]}."]
        kind = ["--" if i % 2 else "D-" for i in range(1, wrapped_rows + 1)]
        left = [damage.damage(i, p) if kind[i - 1][0] == "D" else p for i, p in enumerate(phrases, start=1)]
        page = sheet.page(
            [[(56.0, phrases[i - 1]), (330.0, notes[i - 1])] for i in range(1, wrapped_rows + 1)]
            + [[(56.0, "Конец листа"), (330.0, notes[-1])]]
        )
        sheet.block(page, 50.0, 322.0, [*left, "Конец листа"])
        sheet.block(page, 326.0, 584.0, notes)
        for i, phrase in enumerate(phrases, start=1):
            sheet.quote(f"wrapped:{damage.name}/{kind[i - 1]}", page, phrase)
    return sheet.build()


# -- scenario 5: wide gutters (after D-626) ------------------------------------------------------------


GUTTER_HEIGHTS = (1.0, 1.9, 2.1, 3.0, 6.0)


def wide_gutter(rows: int = 24) -> Sheet:
    """Three kinds of page, all with a stretch of the line that no block covers:

    * ``inside-g<w>`` -- ``label | gutter | value``: the label's block and the value's block stand ``w`` line heights apart (10 pt a
      height), the quotation is the label and its block's reading is exact. The price of the unboxed-stretch condition: the rule links
      the label up to two heights and abstains from there;
    * ``unboxed-<size>`` -- ``Поз. n | label | value``, the label's cell has NO block and the value's block (a crop that reaches over to
      the label) reads it: the quotation is in no block and the only block that contains it is a neighbour;
    * ``a2b`` -- the judge's A2b: a short label at the line's start in a stretch no block covers, the value far to the right, and one block
      from the end of the label to the right edge whose crop reads the label. The line has few characters over a long width, so four of
      its MEAN characters (the unit before `D-626`) are wider than the stretch; two line heights are not.
    """
    sheet = SheetBuilder("witness_gutter", "gutters between blocks, a cell the portal did not box, and the judge's A2b")
    for width in GUTTER_HEIGHTS:
        labels = [f"{noun(i)} {adjective(i)} {i}" for i in range(1, rows + 1)]
        values = [f"{i * 13 + 7},{i % 10} кг" for i in range(1, rows + 1)]
        label_end = 56.0 + max(text_width(label) for label in labels) + 4.0
        value_at = label_end + width * stress.SIZE + 4.0
        value_end = value_at + max(text_width(value) for value in values) + 4.0
        page = sheet.page([[(56.0, labels[i - 1]), (value_at, values[i - 1])] for i in range(1, rows + 1)])
        sheet.block(page, 50.0, label_end, labels)
        sheet.block(page, value_at - 4.0, value_end, values)
        for label in labels:
            sheet.quote(f"inside-g{width:g}", page, label)
    shapes: dict[str, Callable[[int], str]] = {
        "short": lambda i: f"Ось {i}-{LETTERS[i % len(LETTERS)]}",
        "medium": lambda i: f"{noun(i)} типа {i}",
        "long": lambda i: f"{noun(i)} {adjective(i)} {noun(i, 11)} {i}",
    }
    for shape, label_of in shapes.items():
        labels = [label_of(i) for i in range(1, rows + 1)]
        values = [f"{i * 13 + 7},{i % 10} кг" for i in range(1, rows + 1)]
        first_end = 56.0 + text_width("Поз. 99") + 4.0
        label_at = 140.0
        value_at = label_at + max(text_width(label) for label in labels) + 8.0
        value_end = value_at + max(text_width(value) for value in values) + 4.0
        page = sheet.page([[(56.0, f"Поз. {i}"), (label_at, labels[i - 1]), (value_at, values[i - 1])] for i in range(1, rows + 1)])
        sheet.block(page, 50.0, first_end, [f"Поз. {i}" for i in range(1, rows + 1)])
        sheet.block(page, value_at - 4.0, value_end, [f"{labels[i - 1]} {values[i - 1]}" for i in range(1, rows + 1)])
        for label in labels:
            sheet.quote(f"unboxed-{shape}", page, label)
    labels = [f"Ось Б-{i:02d} (п{1 + i % 9})" for i in range(1, rows + 1)]
    values = [f"серия {1 + i % 9}" for i in range(1, rows + 1)]
    label_end = 50.0 + max(text_width(label) for label in labels) + 3.0
    value_at = 470.0
    page = sheet.page([[(50.0, labels[i - 1]), (value_at, values[i - 1])] for i in range(1, rows + 1)])
    sheet.block(page, label_end, value_at + max(text_width(value) for value in values) + 4.0,
                [f"{labels[i - 1]} {values[i - 1]}" for i in range(1, rows + 1)])
    for label in labels:
        sheet.quote("a2b", page, label)
    return sheet.build()


SCENARIOS: dict[str, Callable[[], Sheet]] = {
    "witness_image": image_over_line,
    "witness_schedule": two_word_schedule,
    "witness_damage": reading_damage,
    "witness_a1": a1_residual,
    "witness_gutter": wide_gutter,
}


# -- what a sheet gives the measurement --------------------------------------------------------------------


@dataclass
class Inputs:
    """What ``matrix`` needs, as the stored documents give it on the stand and as the PDF gives it here."""

    evidence: dict[str, list[EvidenceFact]]
    labels: dict[str, str]
    lines: list[TextLine]
    sizes: dict[int, tuple[float, float]]
    layer: dict[int, str]
    blocks: list[BlockFact]
    oracle: Any
    unlinked: frozenset[int] = frozenset()
    pdf_oracle: PdfOracle | None = None            # the open PDF behind ``oracle`` (closed by :func:`evaluate`)


def label_of(label: str) -> str:
    """The kind of a finding from its label (``AUTHORED <kind> p<page> #<n>``)."""
    return label.split()[1] if label.startswith("AUTHORED") else "recorded"


def inputs_of(sheet: Sheet) -> Inputs:
    """The sheet's text layer, line boxes, blocks and evidence read straight from its PDF, without a database. The evidence of a quotation
    is its first occurrence on its page, as the chain's anchor resolution takes it; line boxes are rounded as the geometry stage rounds."""
    oracle = PdfOracle(sheet.pdf)
    lines: list[TextLine] = []
    with pdfplumber.open(io.BytesIO(sheet.pdf)) as pdf:
        for number, (page, entry) in enumerate(zip(pdf.pages, oracle.layer, strict=True), start=1):
            cursor = entry.char_start
            for line in page.extract_text_lines(**TEXT_OPTIONS):
                text = unicodedata.normalize("NFC", line["text"])
                lines.append(TextLine(
                    number, cursor, cursor + len(text), round(float(line["x0"]), 2), round(float(line["top"]), 2),
                    round(float(line["x1"]), 2), round(float(line["bottom"]), 2),
                ))
                cursor += len(text) + 1
            if entry.text:
                assert cursor - 1 == entry.char_end, "the lines do not rebuild the page's text"
    blocks = [
        BlockFact(
            f"blk_{number:03d}", block.page, block.kind,
            (block.box[0] / oracle.layer[block.page - 1].width_pt, block.box[1] / oracle.layer[block.page - 1].height_pt,
             block.box[2] / oracle.layer[block.page - 1].width_pt, block.box[3] / oracle.layer[block.page - 1].height_pt),
            block.reading,
        )
        for number, block in enumerate(sheet.blocks, start=1)
    ]
    evidence: dict[str, list[EvidenceFact]] = {}
    labels: dict[str, str] = {}
    for number, quote in enumerate(sheet.quotes, start=1):
        entry = oracle.layer[quote.page - 1]
        local = entry.text.find(quote.text)
        if local < 0:
            raise ValueError(f"the quotation {quote.text!r} is not on page {quote.page}")
        uid = f"fnd_{number:04d}"
        evidence[uid] = [EvidenceFact(quote.page, entry.char_start + local, entry.char_start + local + len(quote.text), quote.text)]
        labels[uid] = f"AUTHORED {quote.kind} p{quote.page} #{number}"
    return Inputs(
        evidence, labels, lines, {p.page_number: (p.width_pt, p.height_pt) for p in oracle.layer},
        {p.page_number: p.text for p in oracle.layer}, blocks, MemoOracle(oracle), pdf_oracle=oracle,
    )


def portal_files(sheet: Sheet, stem: str, layer: Sequence[Any]) -> tuple[bytes, bytes]:
    """``(the recognised-text markdown, the block list)`` of a portal export of the sheet: its blocks as authored (TEXT blocks with their
    readings, IMAGE blocks with a description) over the pages ``layer`` (``PdfOracle.layer``) describes."""
    import sys  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fixtures"))
    from portal_bundle import blocklist, portal_format  # noqa: PLC0415
    from portal_bundle import bundle as portal_bundle  # noqa: PLC0415
    from portal_bundle.pdffacts import PageFacts  # noqa: PLC0415

    facts = [PageFacts(p.width_pt, p.height_pt, 0, p.text) for p in layer]
    note = blocklist.ImageNote("План", ("1",), "Область чертежа с выносками.", "Область чертежа с выносками.", ("выноска",))
    blocks = []
    for block in sheet.blocks:
        page = layer[block.page - 1]
        box = (block.box[0] / page.width_pt, block.box[1] / page.height_pt, block.box[2] / page.width_pt, block.box[3] / page.height_pt)
        if block.kind == "image":
            blocks.append(blocklist.Block(portal_format.KIND_IMAGE, block.page - 1, box, image=note))
        else:
            blocks.append(blocklist.Block(portal_format.KIND_TEXT, block.page - 1, box, text=block.reading or ""))
    files = portal_bundle.make_files(sheet.pdf, stem, pages=facts, blocks=blocks)
    return files.results_md, files.blocks_json


# -- the ablations -------------------------------------------------------------------------------------


@contextlib.contextmanager
def without(removed: Iterable[str]):
    """The rule with the guards named in ``removed`` patched out for the duration of the block: an ablation, never the shipped rule.
    ``gap`` is not patched here (it is the call's ``max_gap_line_heights``), nor ``flags`` (it is the doubtful set)."""
    removed = set(removed)
    unknown = removed - set(GUARDS)
    if unknown:
        raise ValueError(f"no such guard: {sorted(unknown)}")
    with contextlib.ExitStack() as patched:
        if "near_copy" in removed:
            patched.enter_context(mock.patch.object(rule_module, "_near_copy", lambda *_a, **_k: False))
        if "unique" in removed:
            patched.enter_context(mock.patch.object(Readings, "occurrences", lambda *_a, **_k: 1))
        if "reading" in removed:
            patched.enter_context(mock.patch.object(Readings, "trusted", lambda *_a, **_k: True))
        yield


def variant_name(removed: Iterable[str]) -> str:
    removed = [guard for guard in GUARDS if guard in set(removed)]
    return "+".join(removed) if removed else SHIPPED


def _old_unit_heights(facts: Sequence[EvidenceFact], lines: Sequence[TextLine]) -> float:
    """The limit of the pre-`D-626` rule for a finding, in line heights: four mean characters of the line the evidence is on."""
    for fact in facts:
        for line in lines:
            if line.page_number == fact.page_number and line.char_start < fact.char_end and line.char_end > fact.char_start:
                return OLD_GAP_CHARACTERS * (line.x1 - line.x0) / max(1, line.char_end - line.char_start) / (line.y1 - line.y0)
    return WITNESS_MAX_GAP_LINE_HEIGHTS


def run_variant(inputs: Inputs, removed: Iterable[str] = (), *, old_unit: bool = False) -> dict[str, Any]:
    """The rule over the inputs with the guards ``removed`` patched out, held against the glyphs: ``figures`` with ``by_kind``."""
    removed = set(removed)
    texts = {block.portal_block_id: block.text for block in inputs.blocks if block.text}
    doubtful = set() if "flags" in removed else doubtful_blocks(inputs.blocks, texts)
    readings = Readings(texts, doubtful, inputs.layer)
    items = []
    with without(removed):
        for uid, facts in inputs.evidence.items():
            gap = None if "gap" in removed else (_old_unit_heights(facts, inputs.lines) if old_unit else WITNESS_MAX_GAP_LINE_HEIGHTS)
            linked = rule_links(
                facts, inputs.lines, inputs.sizes, inputs.blocks, set(inputs.unlinked), texts, WITNESS_MIN_CHARACTERS,
                max_gap_line_heights=gap, readings=readings,
            )
            items.append((uid, linked, inputs.labels[uid]))
    report = analyse(
        items=items, evidence=inputs.evidence, blocks=inputs.blocks, unlinked_pages=sorted(inputs.unlinked), oracle=inputs.oracle,
    )
    return figures(report, label_of=label_of)


def compact(result: Mapping[str, Any]) -> dict[str, Any]:
    """The counts of one ``figures`` result that the table needs: overall and by kind."""

    def counts(source: Mapping[str, Any]) -> dict[str, int]:
        return {key: source[key] for key in ("findings", "with_a_block", "links", "wrong", "marginal", "missed")}

    overall = {
        "findings": result["findings"], "with_a_block": result["findings_with_a_block"], "links": result["links"],
        "wrong": result["wrong"], "marginal": result["links_by_geometry"].get("marginal", 0), "missed": result["missed_links"],
        "unplaced": result["links_by_geometry"].get("unplaced", 0), "ceiling": result["findings_whose_glyphs_a_block_holds"],
    }
    return {"all": overall, "by_kind": {kind: counts(c) for kind, c in result["by_kind"].items()}}


def matrix(inputs: Inputs, *, guards: Sequence[str] = GUARDS) -> dict[str, dict[str, Any]]:
    """The rule once for every subset of ``guards`` removed (``shipped`` is the empty one) and once with the pre-`D-626` unit of the
    unboxed-stretch limit: ``{variant name: compact figures}``."""
    result: dict[str, dict[str, Any]] = {}
    for size in range(len(guards) + 1):
        for removed in combinations(guards, size):
            result[variant_name(removed)] = compact(run_variant(inputs, removed))
    result[OLD_UNIT] = compact(run_variant(inputs, (), old_unit=True))
    return result


def minimal_failing_sets(table: Mapping[str, Mapping[str, Any]], kind: str | None = None) -> list[tuple[str, ...]]:
    """The smallest sets of guards whose removal makes ``kind`` (all findings when ``None``) link wrongly: a set that links wrongly and
    has no subset that does. ``[()]`` is the shipped rule itself linking wrongly."""

    def wrong(name: str) -> int:
        row = table[name]
        return row["all"]["wrong"] if kind is None else row["by_kind"].get(kind, {}).get("wrong", 0)

    failing = [
        frozenset() if name == SHIPPED else frozenset(name.split("+")) for name in table if name != OLD_UNIT and wrong(name) > 0
    ]
    minimal = [s for s in failing if not any(other < s for other in failing)]
    return sorted((tuple(g for g in GUARDS if g in s) for s in minimal), key=lambda s: (len(s), s))


def table_differences(first: Mapping[str, Mapping[str, Any]], second: Mapping[str, Mapping[str, Any]]) -> list[tuple[str, str, Any, Any]]:
    """Where two tables disagree: ``(variant, kind, first's links / wrong / missed, second's)``; empty when they are the same."""
    found: list[tuple[str, str, Any, Any]] = []
    for variant in sorted(set(first) | set(second)):
        a, b = first.get(variant), second.get(variant)
        if a is None or b is None:
            found.append((variant, "*", a is not None, b is not None))
            continue
        for kind in sorted(set(a["by_kind"]) | set(b["by_kind"])):
            x, y = a["by_kind"].get(kind), b["by_kind"].get(kind)
            pick_ = lambda row: None if row is None else (row["links"], row["wrong"], row["missed"])  # noqa: E731
            if pick_(x) != pick_(y):
                found.append((variant, kind, pick_(x), pick_(y)))
    return found


def kinds_of(table: Mapping[str, Mapping[str, Any]]) -> list[str]:
    return list(table[SHIPPED]["by_kind"])


def evaluate(sheet: Sheet) -> dict[str, dict[str, Any]]:
    """The matrix of a sheet read straight from its PDF: no database, the same numbers the stand gives for the stored documents."""
    inputs = inputs_of(sheet)
    try:
        return matrix(inputs)
    finally:
        if inputs.pdf_oracle is not None:
            inputs.pdf_oracle.close()


def render_table(name: str, table: Mapping[str, Mapping[str, Any]]) -> str:
    """A markdown table of one scenario: per kind, the shipped rule's links / wrong / missed and the guard sets whose removal links wrongly."""
    lines = [
        f"### {name}", "",
        "| kind | findings | shipped: links | wrong | missed | single guards that give wrong (count) | minimal guard sets whose removal gives wrong |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for kind in kinds_of(table):
        shipped = table[SHIPPED]["by_kind"][kind]
        if shipped["wrong"]:
            singles, old = "(the shipped rule already links wrongly)", 0
        else:
            singles = ", ".join(
                f"{guard} ({table[guard]['by_kind'][kind]['wrong']})" for guard in GUARDS if table[guard]["by_kind"][kind]["wrong"]
            ) or "none"
            old = table[OLD_UNIT]["by_kind"][kind]["wrong"]
        sets = "; ".join("{" + ", ".join(s) + "}" if s else "SHIPPED" for s in minimal_failing_sets(table, kind)) or "none"
        lines.append(
            f"| {kind} | {shipped['findings']} | {shipped['links']} | {shipped['wrong']} | {shipped['missed']} | {singles}"
            f"{'; old unit (' + str(old) + ')' if old else ''} | {sets} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    for scenario_name, build in SCENARIOS.items():
        print(render_table(scenario_name, evaluate(build())))
