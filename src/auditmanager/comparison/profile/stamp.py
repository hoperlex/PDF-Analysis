"""Read the title block of a sheet from the words of its stamp zone: designation, sheet number,
sheet title, «Изм.» and release date.

`CMP-PROFILE-01` (plan G-04; the original reads the lower-right corner of every page, 205 x 70 mm,
`ORIGINAL-VERSION-COMPARISON-INVENTORY.md` section 3.2). Pure: words in, a small record out.

The rule
--------
1. **The zone** is the rectangle 205 x 70 mm anchored at the lower-right corner of the page **as
   displayed** (the frame ``pdfplumber`` reports, rotation applied), clipped to the page. A word belongs
   to the zone when its centre is inside it.
2. **Labels.** A title block of the GOST 21.101 family prints the name of a cell above its value:
   «Обозначение», «Наименование листа», «Стадия», «Лист», «Изм.», «Дата». A word whose normalised text
   (lower case, trailing ``.:,;`` removed) is exactly one of those names is a label.
3. **A cell** is read below its label: it starts at the label's left edge, runs right up to the next
   label of the same row (or the edge of the zone), and down to the next label below it in that
   column (or the edge of the zone). The value is the text of the words whose top is under the label's
   own bottom, in reading order, at most three lines, stopping at a vertical gap wider than 1.5 line
   heights.
4. **Nothing is guessed.** A field whose label is absent, whose cell is empty or whose text does not
   have the field's shape (a sheet number is a short number, optionally ``5.1`` or ``5-1``; a date is
   ``dd.mm.yyyy``; «Изм.» holds a number) is absent from the record. A page with no text layer, such
   as a scan, has no stamp here; its fields are what the image shows, and no OCR substitutes for them.

It is tuned to the label-above-value layout and says so in the report's known limits; a stamp that
prints its labels beside the values, or in another language, yields an empty record, never a wrong one.
A word «Лист» or «Дата» inside a title can shorten the cell to its left: a known, rare limit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Final, Sequence

__all__ = ["StampRead", "read_stamp", "stamp_zone"]

ZONE_WIDTH_MM: Final[float] = 205.0
ZONE_HEIGHT_MM: Final[float] = 70.0
_MM_TO_PT: Final[float] = 72.0 / 25.4
#: Two words are on one row when their tops differ by no more than this many points.
ROW_TOLERANCE: Final[float] = 3.0
_LEFT_SLACK: Final[float] = 3.0
_MAX_VALUE_LINES: Final[int] = 3
_GAP_FACTOR: Final[float] = 1.5
_MAX_DESIGNATION: Final[int] = 200
_MAX_TITLE: Final[int] = 400

_LABELS: Final[dict[str, str]] = {
    "обозначение": "designation",
    "наименование": "title",
    "стадия": "stage",
    "лист": "sheet",
    "изм": "revision",
    "дата": "date",
    "организация": "organisation",
}
_SHEET_NUMBER = re.compile(r"^[A-Za-zА-Яа-я]{0,2}\d{1,4}(?:[.\-/]\d{1,3})?$")
_DATE = re.compile(r"(\d{1,2})[./](\d{1,2})[./](\d{4})")
_DIGITS = re.compile(r"\d{1,4}")

Word = Sequence  # (x0, top, x1, bottom, text)


@dataclass(frozen=True, slots=True)
class StampRead:
    """What the stamp zone says. Every field is ``None`` when the page does not say it."""

    zone: tuple[float, float, float, float]
    designation: str | None = None
    sheet_number: str | None = None
    sheet_title: str | None = None
    revision_number: str | None = None
    release_date: str | None = None
    #: The fields that were read, in a fixed order (a record of how much of the stamp was understood).
    labels: tuple[str, ...] = ()

    @property
    def found(self) -> bool:
        return any((self.designation, self.sheet_number, self.sheet_title, self.revision_number, self.release_date))


@dataclass(frozen=True, slots=True)
class _Word:
    x0: float
    top: float
    x1: float
    bottom: float
    text: str

    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2


def stamp_zone(width_pt: float, height_pt: float) -> tuple[float, float, float, float]:
    """``(x0, top, x1, bottom)`` of the stamp zone on a displayed page of this size."""
    return (
        max(0.0, width_pt - ZONE_WIDTH_MM * _MM_TO_PT),
        max(0.0, height_pt - ZONE_HEIGHT_MM * _MM_TO_PT),
        width_pt,
        height_pt,
    )


def _kind(text: str) -> str | None:
    return _LABELS.get(text.strip().lower().rstrip(".:,;"))


def _lines(words: list[_Word]) -> list[list[_Word]]:
    ordered = sorted(words, key=lambda w: (w.top, w.x0))
    lines: list[list[_Word]] = []
    for word in ordered:
        if lines and abs(word.top - lines[-1][0].top) <= ROW_TOLERANCE:
            lines[-1].append(word)
        else:
            lines.append([word])
    return [sorted(line, key=lambda w: w.x0) for line in lines]


def _cell(label: _Word, labels: list[_Word], zone_words: list[_Word], zone: tuple[float, ...]) -> str | None:
    """The text under ``label``, or ``None`` when the cell is empty."""
    left = label.x0 - _LEFT_SLACK
    same_row_right = [
        other.x0 - 1.0
        for other in labels
        if other is not label and abs(other.top - label.top) <= ROW_TOLERANCE and other.x0 > label.x1 - 0.5
    ]
    right = min(same_row_right, default=zone[2] + 1.0)
    below = [
        other.top
        for other in labels
        if other.top > label.top + ROW_TOLERANCE and other.x1 > left and other.x0 < right
    ]
    limit = min(below, default=zone[3] + 1.0)
    inside = [
        word
        for word in zone_words
        if word.top >= label.bottom - 1.0
        and left <= word.center_x < right
        and word.bottom <= limit + 1.0
        and _kind(word.text) is None
    ]
    if not inside:
        return None
    kept: list[list[_Word]] = []
    for line in _lines(inside):
        if kept:
            previous = kept[-1]
            height = max(word.bottom - word.top for word in previous)
            if line[0].top - max(word.bottom for word in previous) > _GAP_FACTOR * height:
                break
            if len(kept) >= _MAX_VALUE_LINES:
                break
        kept.append(line)
    return " ".join(" ".join(word.text for word in line) for line in kept).strip() or None


def _sheet_number(text: str | None) -> str | None:
    if not text:
        return None
    for token in text.split():
        if _SHEET_NUMBER.fullmatch(token):
            return token
    return None


def _release_date(text: str | None) -> str | None:
    if not text:
        return None
    found = _DATE.search(text)
    if found is None:
        return None
    day, month, year = (int(part) for part in found.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _revision(text: str | None) -> str | None:
    if not text:
        return None
    found = _DIGITS.search(text)
    return found.group(0) if found else None


def read_stamp(words: Sequence[Word], width_pt: float, height_pt: float) -> StampRead:
    """Read the stamp zone of a displayed ``width_pt`` x ``height_pt`` page from its words."""
    zone = stamp_zone(width_pt, height_pt)
    in_zone = [
        _Word(float(w[0]), float(w[1]), float(w[2]), float(w[3]), str(w[4]))
        for w in words
        if str(w[4]).strip()
    ]
    in_zone = [w for w in in_zone if zone[0] <= w.center_x <= zone[2] and zone[1] <= w.center_y <= zone[3]]
    labels = [word for word in in_zone if _kind(word.text) is not None]
    if not labels:
        return StampRead(zone=tuple(round(v, 2) for v in zone))  # type: ignore[arg-type]

    def read(kind: str, accept) -> str | None:
        for label in sorted((w for w in labels if _kind(w.text) == kind), key=lambda w: (w.top, w.x0)):
            value = accept(_cell(label, labels, in_zone, zone))
            if value is not None:
                return value
        return None

    designation = read("designation", lambda t: t[:_MAX_DESIGNATION] if t else None)
    title = read("title", lambda t: t[:_MAX_TITLE] if t else None)
    sheet = read("sheet", _sheet_number)
    revision = read("revision", _revision)
    released = read("date", _release_date)
    kinds = tuple(
        name
        for name, value in (
            ("designation", designation),
            ("title", title),
            ("sheet", sheet),
            ("revision", revision),
            ("date", released),
        )
        if value is not None
    )
    return StampRead(
        zone=tuple(round(v, 2) for v in zone),  # type: ignore[arg-type]
        designation=designation,
        sheet_number=sheet,
        sheet_title=title,
        revision_number=revision,
        release_date=released,
        labels=kinds,
    )
