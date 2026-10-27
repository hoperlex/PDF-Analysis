"""Reading a sheet's title block: designation, «Изм.», release date and stage. Pure text, no PDF.

The stamp reader of a comparison upload (`ORIGINAL-VERSION-COMPARISON-INVENTORY.md` section 3.2) has two halves.
The half that touches the PDF is the child program :mod:`auditmanager.ingest.comparison_pdf.stamp_reader`: it
hands back, for every page, the text that lies in the lower-right corner of the *displayed* sheet (the title
block of a drawing is there: 185 x 55 mm by GOST, read in a 205 x 70 mm zone as the original reads it). This
module is the other half: it turns that text into facts, and from the facts of the pages into the facts of the
file. It imports nothing of the product and nothing that can fault, so each rule is a plain function with a
test that shows it failing.

**What is read, and what is never invented.** A value is returned only when the text says it: a designation
under «Обозначение» / «Шифр» or shaped like one, ``Изм.N`` or ``Изм. N``, a date ``дд.мм.гггг``, a stage under
«Стадия» spelled with the Cyrillic **П** or **Р**. A Latin ``P`` or ``R`` is never read as a stage: a title block
typeset with a Latin letter that looks like the Cyrillic one is a reason to ask the expert, not to guess. A
page with no text in the zone (a scan, a drawing whose letters are outlines) has no stamp; it says so and
nothing is read from elsewhere. **Everything here is a proposal an expert confirms** (ADR-0025 decisions 11
and 16); no value is an identity, and the designation is metadata, never the document's identity.

**The file's facts** (:func:`read_file_stamp`):

* the designation is the one most pages carry; a sub-document («ИТП.ТМ») joins its parent («ИТП») when the
  parent is on at least a fifth of the sheets (the original's ``_PARENT_SHARE``); a second designation on a
  fifth of the stamped sheets or more is reported as *differing*;
* the revision is the highest «Изм.» of any sheet, because a sheet keeps the «Изм.» of its **last change**:
  the version's own number is the highest on its sheets (``fixtures/comparison/README.md``, VS-1);
* the release date is the latest date of a sheet that carries that highest revision; with no revision, the
  latest date of any sheet;
* the stage is the one most stamped pages state (ties state none); the section is read from the mark that ends
  the designation (``-ЭМ``, ``-АР``, ``-КЖ``), only when the mark is one the section catalogue knows by that name.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Any, Final

__all__ = [
    "FileStamp",
    "PageStamp",
    "SECTION_MARKS",
    "parse_page_stamp",
    "read_file_stamp",
    "section_from_designation",
]

#: A sub-document's parent must be on at least this share of the sheets for the two to be one designation.
PARENT_SHARE: Final[float] = 0.2
#: A second designation on at least this share of the stamped sheets makes the file's designations differ.
DIFFER_SHARE: Final[float] = 0.2
MAX_DESIGNATION: Final[int] = 200

_SEPARATORS: Final[re.Pattern[str]] = re.compile(r"[\r\n]+")
#: ``Изм.2``, ``Изм. 2``, ``Изм 2``, ``Изм.№2`` (NFKC turns ``№`` into ``No``, so that is the spelling matched).
_REVISION: Final[re.Pattern[str]] = re.compile(
    r"(?<![^\W\d_])Изм\.?[ \t]*(?:№|No\.?)?[ \t]*(\d{1,3})(?!\d)", re.IGNORECASE
)
_DATE: Final[re.Pattern[str]] = re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4}|\d{2})(?!\d)")
_DESIGNATION: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w.\-])([A-Za-zА-Яа-яЁё0-9]{1,12}(?:[.\-–][A-Za-zА-Яа-яЁё0-9]{1,12}){2,})(?![\w\-])"
)
_LABEL: Final[re.Pattern[str]] = re.compile(r"^\s*([A-Za-zА-Яа-яЁё. ]{2,40}?)\s*[:：]?\s*(.*)$")
#: The words a title block prints as labels; a line that is one of them is never a value.
_KNOWN_LABELS: Final[frozenset[str]] = frozenset(
    (
        "обозначение", "шифр", "наименование", "наименование листа", "наименование объекта", "стадия", "лист",
        "листов", "изм", "изм.", "дата", "организация", "подпись", "разработал", "проверил", "н. контр.",
        "н.контр.", "гип", "гап", "масштаб", "формат", "кол.уч", "кол.уч.", "№док", "№ док", "зам", "нов",
    )
)
_DESIGNATION_LABELS: Final[tuple[str, ...]] = ("обозначение", "шифр")
_STAGE_LABELS: Final[tuple[str, ...]] = ("стадия",)
_DATE_LABELS: Final[tuple[str, ...]] = ("дата",)
_YEAR_RANGE: Final[range] = range(1990, 2101)

#: Stage words, Cyrillic only (see the module docstring). ``П`` / ``ПД`` is the project, ``Р`` / ``РД`` the
#: working documentation; the contract's ``ProjectStage`` spells them with Latin ``P`` and ``R``.
_STAGES: Final[dict[str, str]] = {
    "П": "P", "ПД": "P", "ПРОЕКТ": "P", "ПРОЕКТНАЯ": "P",
    "Р": "R", "РД": "R", "РАБОЧАЯ": "R", "РАБОЧИЙ": "R",
}

#: The mark that ends a designation, to the section code of the reviewed catalogue
#: (``sections/suggestion_patterns.json``, the legacy registry's folder patterns written ``-ЭМ`` / ``-АР``).
#: Only marks that catalogue lists as a designation suffix (or its plain two-letter name) are here, and the
#: unit tests hold every value to ``sections.public.SECTION_CODES``.
SECTION_MARKS: Final[dict[str, str]] = {
    "АИ": "AI", "АР": "AR", "AR": "AR",
    "ЭОМ": "EOM", "ЭМ": "EOM", "ЭС": "EOM", "EM": "EOM", "EOM": "EOM",
    "ГП": "GP", "ИТП": "ITP",
    "КЖ": "KJ", "KJ": "KJ", "КМ": "KM",
    "ОВ": "OV", "ОВК": "OV", "ОВИК": "OV", "OV": "OV",
    "ПБ": "PB", "PB": "PB", "ПОС": "POS", "ПС": "PS", "ПТ": "PT",
    "СС": "SS", "АК": "SS", "АПЗ": "SS", "АПС": "SS", "КК": "SS", "СОВ": "SS", "СОТ": "SS", "СОУЭ": "SS",
    "ТХ": "TX", "ВК": "VK",
}


def _normal(text: str) -> str:
    return unicodedata.normalize("NFKC", text).replace(" ", " ")


def _lines(text: str) -> list[str]:
    return [line.strip() for line in _SEPARATORS.split(_normal(text)) if line.strip()]


def _is_label(line: str) -> bool:
    return line.strip().strip(":：").strip().casefold() in _KNOWN_LABELS


def _after_label(lines: list[str], labels: tuple[str, ...]) -> str | None:
    """The value a label introduces: the rest of its line, else the next line that is not a label itself."""
    for index, line in enumerate(lines):
        folded = line.casefold().strip()
        for label in labels:
            if folded == label or folded.rstrip(":：") == label:
                # The value is the very next line: a label followed by another label states nothing.
                follower = lines[index + 1] if index + 1 < len(lines) else None
                return None if follower is None or _is_label(follower) else follower
            if folded.startswith(label + ":") or folded.startswith(label + "："):
                rest = line[len(label) + 1 :].strip()
                if rest and not _is_label(rest):
                    return rest
    return None


def _date_of(day: str, month: str, year: str) -> date | None:
    number = int(year)
    if len(year) == 2:
        number += 2000
    if number not in _YEAR_RANGE:
        return None
    try:
        return date(number, int(month), int(day))
    except ValueError:
        return None


def _dates(text: str) -> list[date]:
    found = (_date_of(*match.groups()) for match in _DATE.finditer(text))
    return [item for item in found if item is not None]


def _looks_like_designation(value: str) -> bool:
    return (
        bool(_DESIGNATION.fullmatch(value))
        and any(char.isdigit() for char in value)
        and any(char.isalpha() for char in value)
        and not _REVISION.search(value)
        and _DATE.fullmatch(value) is None
    )


def _designation(lines: list[str], text: str) -> str | None:
    """The labelled designation when there is one, else the first thing shaped like one."""
    labelled = _after_label(lines, _DESIGNATION_LABELS)
    if labelled:
        value = " ".join(labelled.split())
        if 0 < len(value) <= MAX_DESIGNATION and not _is_label(value):
            return value
    for line in lines:
        if _is_label(line):
            continue
        for match in _DESIGNATION.finditer(line):
            if _looks_like_designation(match.group(1)):
                return match.group(1)
    return None


def _stage(lines: list[str]) -> str | None:
    value = _after_label(lines, _STAGE_LABELS)
    if value is None:
        return None
    word = value.strip().strip(".:").upper()
    return _STAGES.get(word)


def _release_date(lines: list[str], text: str) -> date | None:
    labelled = _after_label(lines, _DATE_LABELS)
    if labelled:
        dates = _dates(labelled)
        if dates:
            return max(dates)
    dates = _dates(text)
    return max(dates) if dates else None


@dataclass(frozen=True, slots=True)
class PageStamp:
    """What one page's title block says. Every member is ``None`` when the text does not say it."""

    designation: str | None
    revision_number: int | None
    release_date: date | None
    project_stage: str | None
    #: Whether the zone held any text at all (a scan or outlined letters hold none).
    has_text: bool

    @property
    def is_empty(self) -> bool:
        return not any((self.designation, self.revision_number is not None, self.release_date, self.project_stage))


def parse_page_stamp(zone_text: str) -> PageStamp:
    """The facts a page's lower-right zone text states."""
    text = _normal(zone_text)
    if not text.strip():
        return PageStamp(None, None, None, None, has_text=False)
    lines = _lines(text)
    revisions = [int(match.group(1)) for match in _REVISION.finditer(text)]
    return PageStamp(
        designation=_designation(lines, text),
        revision_number=max(revisions) if revisions else None,
        release_date=_release_date(lines, text),
        project_stage=_stage(lines),
        has_text=True,
    )


def section_from_designation(designation: str | None) -> str | None:
    """The section code the mark that ends a designation names, or ``None``.

    The mark is the last group after a ``-``, else the last after a ``.`` (``СИНТ-01-ЭМ`` -> ``ЭМ``,
    ``ИТП.ТМ`` -> ``ТМ``, which is no section, so the whole is tried again as ``ИТП``). Only a mark of
    :data:`SECTION_MARKS` answers; a value the catalogue does not know by that name is ``None``, never a
    nearest match.
    """
    if not designation:
        return None
    folded = _normal(designation).upper().strip()
    groups = [group for group in re.split(r"[-–]", folded) if group]
    candidates: list[str] = []
    if groups:
        candidates.append(groups[-1])
        candidates.extend(piece for piece in reversed(re.split(r"[.]", groups[-1])) if piece)
        candidates.extend(piece for piece in re.split(r"[.]", groups[0]) if piece)
    for candidate in candidates:
        code = SECTION_MARKS.get(candidate.strip())
        if code is not None:
            return code
    return None


@dataclass(frozen=True, slots=True)
class FileStamp:
    """The stamp facts of one file, from its pages. Everything but ``page_count`` may be ``None``."""

    page_count: int
    designation: str | None
    #: The designations found, most common first, with the sheets that carry each (after the sub-document merge).
    designation_votes: tuple[tuple[str, int], ...]
    designations_differ: bool
    revision_number: int | None
    release_date: date | None
    project_stage: str | None
    section_code: str | None
    #: Pages whose zone held any text, and pages whose zone said nothing a stamp says.
    stamped_pages: int
    #: ``1``-based pages with no text in the stamp zone (scans, outlined letters).
    textless_pages: tuple[int, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "page_count": self.page_count,
            "designation": self.designation,
            "designation_votes": [[name, count] for name, count in self.designation_votes],
            "designations_differ": self.designations_differ,
            "revision_number": self.revision_number,
            "release_date": None if self.release_date is None else self.release_date.isoformat(),
            "project_stage": self.project_stage,
            "section_code": self.section_code,
            "stamped_pages": self.stamped_pages,
            "textless_pages": list(self.textless_pages),
        }

    @classmethod
    def from_json(cls, value: dict[str, Any]) -> FileStamp:
        released = value.get("release_date")
        return cls(
            page_count=int(value["page_count"]),
            designation=value.get("designation"),
            designation_votes=tuple((str(name), int(count)) for name, count in value.get("designation_votes", [])),
            designations_differ=bool(value.get("designations_differ", False)),
            revision_number=value.get("revision_number"),
            release_date=None if released is None else date.fromisoformat(released),
            project_stage=value.get("project_stage"),
            section_code=value.get("section_code"),
            stamped_pages=int(value.get("stamped_pages", 0)),
            textless_pages=tuple(int(page) for page in value.get("textless_pages", [])),
        )


def _folded(designation: str) -> str:
    return " ".join(_normal(designation).upper().split())


def _merge_subdocuments(counts: Counter[str], pages: int) -> Counter[str]:
    """A sub-document joins its parent when the parent is on at least a fifth of the sheets."""
    merged: Counter[str] = Counter(counts)
    for name in sorted(counts, key=len, reverse=True):
        for other in counts:
            if other != name and name.startswith(other) and name[len(other)] in ".-" and (
                counts[other] >= PARENT_SHARE * pages
            ):
                merged[other] += merged.pop(name, 0)
                break
    return merged


def read_file_stamp(
    pages: list[PageStamp], *, has_layer: list[bool] | None = None
) -> FileStamp:
    """The facts of a file from the stamps of its pages, in page order.

    ``has_layer[i]`` says whether page ``i + 1`` has an embedded text layer at all (the envelope's count); a
    page with no layer is a scan, and is listed in ``textless_pages`` whatever its zone says. Without it a
    page counts as textless when its zone held no text.
    """
    count = len(pages)
    # Designations are counted by their folded form; the first spelling seen is the one shown.
    shown: dict[str, str] = {}
    counts: Counter[str] = Counter()
    for page in pages:
        if page.designation:
            key = _folded(page.designation)
            shown.setdefault(key, " ".join(_normal(page.designation).split()))
            counts[key] += 1
    merged = _merge_subdocuments(counts, count)
    ranked = sorted(merged.items(), key=lambda item: (-item[1], item[0]))
    designation = shown[ranked[0][0]] if ranked else None
    stamped = sum(counts.values())
    differs = len(ranked) > 1 and ranked[1][1] >= DIFFER_SHARE * max(stamped, 1)

    revision = max((page.revision_number for page in pages if page.revision_number is not None), default=None)
    carrying = [
        page.release_date for page in pages
        if page.release_date is not None and (revision is None or page.revision_number == revision)
    ]
    released = max(carrying) if carrying else max(
        (page.release_date for page in pages if page.release_date is not None), default=None
    )
    stages = Counter(page.project_stage for page in pages if page.project_stage)
    stage: str | None = None
    if stages:
        (top, top_count), *rest = stages.most_common()
        stage = top if not rest or rest[0][1] < top_count else None

    textless = tuple(
        index + 1
        for index, page in enumerate(pages)
        if (has_layer is not None and not has_layer[index]) or (has_layer is None and not page.has_text)
    )
    return FileStamp(
        page_count=count,
        designation=designation,
        designation_votes=tuple((shown[key], votes) for key, votes in ranked),
        designations_differ=differs,
        revision_number=revision,
        release_date=released,
        project_stage=stage,
        section_code=section_from_designation(designation),
        stamped_pages=sum(1 for page in pages if page.has_text),
        textless_pages=textless,
    )
