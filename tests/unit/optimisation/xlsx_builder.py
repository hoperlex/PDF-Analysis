"""A minimal XLSX writer for the price-list tests, standard library only.

It writes exactly the parts the reader under test consults -- package relationships, the
workbook, its relationships, the sheets and (optionally) the shared-string table -- so each
test controls the cell encodings it exercises: shared strings, inline strings, rich runs,
phonetic runs, stored numbers written as raw text, sparse cell references and the order of
the workbook's sheets.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from xml.sax.saxutils import escape

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_DOCUMENT = f"{REL}/officeDocument"
WORKSHEET = f"{REL}/worksheet"
SHARED_STRINGS = f"{REL}/sharedStrings"


@dataclass(frozen=True)
class Num:
    """A stored number, written to ``<v>`` exactly as given."""

    raw: str


@dataclass(frozen=True)
class Inline:
    """An inline string cell (``t="inlineStr"``)."""

    text: str


@dataclass(frozen=True)
class Rich:
    """A shared string made of rich runs, with an optional phonetic run that is not text."""

    runs: tuple[str, ...]
    phonetic: str | None = None


@dataclass(frozen=True)
class Raw:
    """A cell written verbatim (for booleans, errors, formulas with cached values)."""

    xml: str


Value = str | int | float | Num | Inline | Rich | Raw | None


def _column(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def _sheet_xml(
    rows: Sequence[tuple[int, Sequence[Value]]], strings: list[str | Rich], *, prolog: str = ""
) -> str:
    out = [f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>{prolog}<worksheet xmlns="{MAIN}"><sheetData>']
    for number, values in rows:
        out.append(f'<row r="{number}">')
        for index, value in enumerate(values):
            if value is None:
                continue
            ref = f"{_column(index)}{number}"
            if isinstance(value, Num):
                out.append(f'<c r="{ref}"><v>{escape(value.raw)}</v></c>')
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                out.append(f'<c r="{ref}"><v>{value!r}</v></c>')
            elif isinstance(value, Inline):
                out.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(value.text)}</t></is></c>')
            elif isinstance(value, Raw):
                out.append(value.xml.replace("{ref}", ref))
            else:
                strings.append(value)
                out.append(f'<c r="{ref}" t="s"><v>{len(strings) - 1}</v></c>')
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def _shared_xml(strings: list[str | Rich]) -> str:
    items = []
    for value in strings:
        if isinstance(value, Rich):
            runs = "".join(f"<r><rPr><b/></rPr><t>{escape(run)}</t></r>" for run in value.runs)
            phonetic = (
                ""
                if value.phonetic is None
                else f'<rPh sb="0" eb="1"><t>{escape(value.phonetic)}</t></rPh>'
            )
            items.append(f"<si>{runs}{phonetic}</si>")
        else:
            items.append(f'<si><t xml:space="preserve">{escape(value)}</t></si>')
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><sst xmlns="{MAIN}" '
        f'count="{len(strings)}" uniqueCount="{len(strings)}">{"".join(items)}</sst>'
    )


def build_xlsx(
    sheets: Sequence[tuple[str, Sequence[tuple[int, Sequence[Value]]]]],
    *,
    sheet_prolog: str = "",
    with_package_rels: bool = True,
) -> bytes:
    """A workbook whose sheets are listed in the given order; the first one is read.

    ``sheets`` is ``[(name, [(row_number, [cell values...]), ...]), ...]``. The first listed
    sheet is deliberately stored as the **last** part (``sheetN.xml``), so a reader that picks
    ``sheet1.xml`` by name reads the wrong sheet.
    """
    strings: list[str | Rich] = []
    parts: dict[str, str] = {}
    sheet_entries = []
    rel_entries = []
    count = len(sheets)
    for position, (name, rows) in enumerate(sheets):
        part_number = count - position
        target = f"worksheets/sheet{part_number}.xml"
        parts[f"xl/{target}"] = _sheet_xml(rows, strings, prolog=sheet_prolog)
        rel_id = f"rId{position + 1}"
        sheet_entries.append(
            f'<sheet name="{escape(name)}" sheetId="{position + 1}" r:id="{rel_id}"/>'
        )
        rel_entries.append(f'<Relationship Id="{rel_id}" Type="{WORKSHEET}" Target="{target}"/>')
    rel_entries.append(
        f'<Relationship Id="rId{count + 1}" Type="{SHARED_STRINGS}" Target="sharedStrings.xml"/>'
    )
    parts["xl/sharedStrings.xml"] = _shared_xml(strings)
    parts["xl/workbook.xml"] = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="{MAIN}" '
        f'xmlns:r="{REL}"><sheets>{"".join(sheet_entries)}</sheets></workbook>'
    )
    parts["xl/_rels/workbook.xml.rels"] = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships '
        f'xmlns="{PKG_REL}">{"".join(rel_entries)}</Relationships>'
    )
    if with_package_rels:
        parts["_rels/.rels"] = (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships '
            f'xmlns="{PKG_REL}"><Relationship Id="rId1" Type="{OFFICE_DOCUMENT}" '
            'Target="xl/workbook.xml"/></Relationships>'
        )
    parts["[Content_Types].xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types '
        'xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(parts):
            archive.writestr(name, parts[name])
    return buffer.getvalue()


def simple_xlsx(rows: Sequence[Sequence[Value]], *, name: str = "Прайс") -> bytes:
    """One sheet, rows numbered from 1."""
    return build_xlsx([(name, [(index + 1, row) for index, row in enumerate(rows)])])
