"""The table of a specification page and the stream of positions across the pages of one version (pure Python).

`CMP-VC-SPEC-01`, part A. A port of ``version_comparison/spec.py`` of the original (PDF-proverka at commit ``23f379fd``; the
``spec.py:N`` below is that file's line N): a specification sheet is a table by GOST 21.110, **the columns are the vertical rules
of the header and the rows are the horizontal rules** (``spec.py:1-4``); the type of a row is decided by which cells are filled,
never by the number in the «Поз.» cell (``:4``); an ambiguous row is flagged ``ambiguous`` and never guessed (``:16-17``).

What differs from the original, and why:

* the original read a PDF with ``fitz``; this reads the **page profile** (``CMP-PROFILE-01``): the words with boxes and the vector
  lines (since ``CMP-C1-FIX-A`` item 8 the edges of stroked rectangles and the thin filled rules are among them), all in points
  in the frame of the page as displayed. Nothing here opens a PDF or calls PDFium;
* the profile has no font, so a **bold** title cannot be told from a plain one: ``bold`` is always false and a section title is
  recognised by its being centred, or (when it is not centred) by the rule at ``spec.py:314-317``;
* the original took the bottom of the header from the lowest word of a band around the labels, which drops the first row of a
  compact form (the band reaches into it). The header here ends at **the first row rule below the label line**;
* the original separated the release mark and the QR (``separation.separate``, ``:351-356``) before reading; the profile has no
  such separation, so words of a mark that lies over the table would be read as cells. The title block is cut out by the
  profile's stamp zone, as the original cut it by the stamp zone of the profile (``:184-186``);
* the values are the contract's names (``quantity`` where the original says ``qty``; ``завод`` is the supplier column).

Every value is the text of the sheet: the words of a cell are joined by one space; nothing is summed, rounded or normalised.

This module imports the standard library only: the engine's child program loads it by path (``_amc_spec.table``).
"""

from __future__ import annotations

import re
from bisect import bisect_right
from collections import defaultdict
from collections.abc import Sequence
from typing import Any, Final

__all__ = [
    "COMPARE_FIELDS",
    "FIELDS",
    "FIELD_LABELS",
    "SPEC_VERSION",
    "assemble",
    "find_columns",
    "find_header",
    "is_spec_stamp",
    "norm",
    "parse_page",
    "quantity",
    "segments",
]

#: Names the parser; it is in the content key of anything derived from it (the engine's ``ALGO_VERSION`` carries it by its own bump).
#: The original's is ``so3`` (``spec.py:38``); this one is its own and starts at 1.
SPEC_VERSION: Final[str] = "cmp-spec/1"
#: ``spec.py:39``: the nine fields of a position (``qty`` is called ``quantity`` here, as the contract does).
FIELDS: Final[tuple[str, ...]] = ("pos", "name", "mark", "code", "supplier", "unit", "quantity", "mass", "note")
#: ``spec.py:40``: the fields compared besides the name.
COMPARE_FIELDS: Final[tuple[str, ...]] = ("quantity", "unit", "mark", "code", "supplier", "note", "pos")
#: ``spec.py:41-42``.
FIELD_LABELS: Final[dict[str, str]] = {
    "pos": "Поз.", "name": "Наименование", "mark": "Тип, марка", "code": "Код", "supplier": "Завод",
    "unit": "Ед. изм.", "quantity": "Кол.", "mass": "Масса", "note": "Примечание",
}
#: ``spec.py:43-45`` (a header cell is keyed by what its text starts with); ``прим`` is added because the corpus (and many forms)
#: print «Прим.», which ``примечан`` does not match.
HEADER_KEYS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("pos", ("поз",)),
    ("name", ("наименование",)),
    ("mark", ("тип", "марка", "обозначение")),
    ("code", ("код",)),
    ("supplier", ("поставщик", "завод", "изготовит")),
    ("unit", ("ед", "единиц")),
    ("quantity", ("кол",)),
    ("mass", ("масса",)),
    ("note", ("примечан", "прим")),
)
#: ``spec.py:46``: a size or an execution, «3х1.5» or «100×40×2».
SIZE_RE: Final[re.Pattern[str]] = re.compile(r"^[\d.,]+\s*[хx×]\s*[\d.,]+([хx×][\d.,]+)*(\s*\S{0,6})?$", re.I)
#: ``spec.py:47``.
NUM_RE: Final[re.Pattern[str]] = re.compile(r"^-?\d+(?:[.,]\d+)?$")
#: ``textdiff._HOMOGLYPHS``: Latin look-alikes of Cyrillic letters.
_HOMOGLYPHS: Final[dict[int, int]] = str.maketrans("ABCEHKMOPTXaceopxyі", "АВСЕНКМОРТХасеорхуі")

#: ``spec.py:98``, ``:100``: the header is looked for in the upper 30 % of the page.
HEADER_REGION: Final[float] = 0.3
#: ``spec.py:103``, ``:104-105``: the labels of one header lie within this many points of one another; the band around them.
LABEL_ROW_PT: Final[float] = 25.0
BAND_PT: Final[float] = 30.0
#: ``spec.py:110``: a specification header names at least this many of the nine columns.
MIN_HEADER_GROUPS: Final[int] = 5
#: ``spec.py:69-72``: a vertical (horizontal) rule is at most 0.8 pt off the axis and longer than 8 pt.
RULE_SLOPE_PT: Final[float] = 0.8
RULE_MIN_PT: Final[float] = 8.0
#: ``spec.py:120``: two vertical rules closer than this are one.
COLUMN_MERGE_PT: Final[float] = 3.0
#: ``spec.py:122``: fewer column boundaries than this is no table.
MIN_COLUMN_RULES: Final[int] = 4
#: ``spec.py:157``: the table spans at least this share of the page width (it is not an inset of a drawing).
MIN_TABLE_WIDTH: Final[float] = 0.6
#: ``spec.py:173``: a row rule covers at least half the width of the table.
ROW_RULE_COVER: Final[float] = 0.5
#: ``spec.py:192``: text below the last rule is split into rows of this height.
OVERFLOW_ROW_PT: Final[float] = 12.0


def norm(text: Any) -> str:
    """The key of a comparison: no spaces, no case, ``,`` is ``.``, ``×`` is ``х``, Latin look-alikes are Cyrillic (``spec.py:50-52``).
    The look-alikes are mapped **before** the case is dropped: the original lowers first (``:52``), after which the capital letters of
    its table (``B``, ``H``, ``K``, ``M``, ``T``) can no longer match."""
    return re.sub(r"\s+", "", str(text or "")).translate(_HOMOGLYPHS).lower().replace("×", "х").replace(",", ".")


def quantity(text: Any) -> float | None:
    """A number with a comma or a dot, else ``None`` (``spec.py:55-57``)."""
    value = str(text or "").replace(" ", "").replace(",", ".")
    return float(value) if NUM_RE.match(value) else None


def _field_of(text: str) -> str | None:
    t = norm(text)
    for field, keys in HEADER_KEYS:
        if any(t.startswith(key) for key in keys):
            return field
    return None


def _mid_y(word: Sequence[Any]) -> float:
    return (float(word[1]) + float(word[3])) / 2


def _mid_x(word: Sequence[Any]) -> float:
    return (float(word[0]) + float(word[2])) / 2


def is_spec_stamp(designation: str | None, title: str | None) -> bool:
    """The cheap test of a specification sheet from its title block: the designation ends in «СО» or the title says
    «Спецификация» (``stamp.classify_kind``, ``stamp.py:190-204``, and ``spec.drawing_stamp``, ``spec.py:380-396``, which is the converse).
    The page itself is confirmed by :func:`find_header`."""
    if designation and re.search(r"(?:^|[.\-\s])СО\s*$", designation.strip(), re.I):
        return True
    return bool(title and re.search(r"спецификац", title, re.I))


def segments(lines: Sequence[Sequence[float]]) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]]]:
    """Vertical ``(x, y0, y1)`` and horizontal ``(y, x0, x1)`` rules of the page (``spec.py:62-83``). A line is ``[x0, top, x1, bottom]``."""
    vertical: list[tuple[float, float, float]] = []
    horizontal: list[tuple[float, float, float]] = []
    for line in lines:
        x0, y0, x1, y1 = float(line[0]), float(line[1]), float(line[2]), float(line[3])
        dx, dy = abs(x0 - x1), abs(y0 - y1)
        if dx < RULE_SLOPE_PT and dy > RULE_MIN_PT:
            vertical.append(((x0 + x1) / 2, min(y0, y1), max(y0, y1)))
        elif dy < RULE_SLOPE_PT and dx > RULE_MIN_PT:
            horizontal.append(((y0 + y1) / 2, min(x0, x1), max(x0, x1)))
    return vertical, horizontal


def find_header(words: Sequence[Sequence[Any]], page_height: float) -> tuple[list[Sequence[Any]], float] | None:
    """The words of the table header and the bottom of its label line, or ``None`` when the page has no specification header
    (``spec.py:96-112``): a «Поз.» and an «Наименование» on one line in the upper part of the page, and a label line that names
    at least five of the nine columns (so that «Поз.» and «Наименование» of a table on a single-line diagram do not count)."""
    top = [w for w in words if float(w[1]) < page_height * HEADER_REGION]
    positions = [w for w in top if norm(w[4]).startswith("поз")]
    names = [w for w in top if norm(w[4]).startswith("наименование")]
    for pos in positions:
        for name in names:
            if abs(_mid_y(pos) - _mid_y(name)) >= LABEL_ROW_PT or float(name[0]) <= float(pos[0]):
                continue
            anchor = (_mid_y(pos) + _mid_y(name)) / 2
            band_lo = min(float(pos[1]), float(name[1])) - BAND_PT
            band_hi = max(float(pos[3]), float(name[3])) + BAND_PT
            band = [w for w in top if band_lo <= _mid_y(w) <= band_hi]
            labels = [w for w in band if abs(_mid_y(w) - anchor) < LABEL_ROW_PT and _field_of(str(w[4])) is not None]
            if len({_field_of(str(w[4])) for w in labels}) < MIN_HEADER_GROUPS:
                continue
            labels_bottom = max(float(w[3]) for w in labels)
            return [w for w in band if _mid_y(w) <= labels_bottom + 1], labels_bottom
    return None


def find_columns(header: Sequence[Sequence[Any]], vertical: Sequence[tuple[float, float, float]]) -> list[dict[str, Any]] | None:
    """The columns of the table: the spans between the vertical rules that cross the header, each keyed by what its header text
    starts with (``spec.py:115-143``). ``None`` when there are too few rules, or no name and no quantity or unit column."""
    if not header:
        return None
    header_y = sum(_mid_y(w) for w in header) / len(header)
    xs = sorted(x for x, y0, y1 in vertical if y0 - 2 <= header_y <= y1 + 2)
    merged: list[float] = []
    for x in xs:
        if not merged or x - merged[-1] > COLUMN_MERGE_PT:
            merged.append(x)
    if len(merged) < MIN_COLUMN_RULES:
        return None
    columns: list[dict[str, Any]] = []
    for x0, x1 in zip(merged, merged[1:], strict=False):
        text = " ".join(
            str(w[4]) for w in sorted(header, key=lambda w: (round(float(w[1]) / 6), float(w[0]))) if x0 <= _mid_x(w) <= x1
        )
        t = norm(text)
        # What the header starts with first («Масса 1 ед.» is the mass, not the unit), then what its first 24 letters contain.
        field = next((f for f, keys in HEADER_KEYS if any(t.startswith(k) for k in keys)), None)
        if field is None:
            field = next((f for f, keys in HEADER_KEYS if any(k in t[:24] for k in keys)), None)
        columns.append({"x0": x0, "x1": x1, "field": field, "header": text})
    # The margins of the sheet to the left and the right of the table are not columns.
    while columns and not columns[0]["field"]:
        columns.pop(0)
    while columns and not columns[-1]["field"]:
        columns.pop()
    fields = {c["field"] for c in columns}
    if "name" not in fields or not ({"quantity", "unit"} & fields):
        return None
    return columns


def _row_rules(
    horizontal: Sequence[tuple[float, float, float]], tx0: float, tx1: float
) -> list[float]:
    """The ordinates of the row rules: segments on one height (a rule is often drawn cell by cell) that together cover at least
    half the width of the table (``spec.py:160-175``)."""
    by_y: dict[float, list[tuple[float, float]]] = defaultdict(list)
    for y, x0, x1 in horizontal:
        by_y[round(y * 2) / 2].append((max(x0, tx0), min(x1, tx1)))
    rules: list[float] = []
    for y, spans in by_y.items():
        covered, end = 0.0, -1e9
        for x0, x1 in sorted(spans):
            if x1 <= x0:
                continue
            covered += max(0.0, x1 - max(x0, end))
            end = max(end, x1)
        if covered >= ROW_RULE_COVER * (tx1 - tx0):
            rules.append(y)
    rules.sort()
    return rules


def parse_page(
    words: Sequence[Sequence[Any]],
    lines: Sequence[Sequence[float]],
    width: float,
    height: float,
    stamp_zone: Sequence[float] | None = None,
) -> dict[str, Any] | None:
    """The rows of the specification table of a page.

    ``None``: this is not a specification page (no header, or a table that does not span the sheet). ``{"parsed": False,
    "reason": ...}``: a header was found but the table could not be read (the columns, or the row rules). Otherwise
    ``{"parsed": True, "rows": [...], "columns": [...]}`` where a row is ``{"cells": {field: text}, "bbox", "centered",
    "bold", "span"?}`` in the order of the page (``spec.py:146-232``). ``words`` are ``[x0, top, x1, bottom, text]``, ``lines``
    ``[x0, top, x1, bottom]``, ``stamp_zone`` ``[x0, top, x1, bottom]``; all in points, origin at the top left.
    """
    found = find_header(words, height)
    if found is None:
        return None
    header, labels_bottom = found
    vertical, horizontal = segments(lines)
    columns = find_columns(header, vertical)
    if not columns:
        return {"parsed": False, "reason": "колонки таблицы не найдены"}
    tx0, tx1 = float(columns[0]["x0"]), float(columns[-1]["x1"])
    if tx1 - tx0 < MIN_TABLE_WIDTH * width:
        return None
    rules = _row_rules(horizontal, tx0, tx1)
    below = [y for y in rules if y >= labels_bottom - 1]
    if not below:
        return {"parsed": False, "reason": "нет линий строк таблицы"}
    y_start = below[0]
    y_end = float(stamp_zone[1]) if stamp_zone and float(stamp_zone[1]) > y_start else height
    bounds = [y for y in below if y <= y_end + 1]
    if not bounds:
        return {"parsed": False, "reason": "нет линий строк таблицы"}
    stamp = [float(v) for v in stamp_zone] if stamp_zone else None
    body = [w for w in words if y_start < _mid_y(w) < y_end and tx0 <= _mid_x(w) <= tx1]
    if stamp:
        body = [w for w in body if not (stamp[0] <= _mid_x(w) <= stamp[2] and stamp[1] <= _mid_y(w) <= stamp[3])]
    rows: dict[int, list[Sequence[Any]]] = defaultdict(list)
    for w in body:
        cy = _mid_y(w)
        index = bisect_right(bounds, cy) - 1
        if index >= len(bounds) - 1:
            index = len(bounds) - 1 + int((cy - bounds[-1]) // OVERFLOW_ROW_PT)
        rows[index].append(w)

    def column_of(w: Sequence[Any]) -> int:
        return next((k for k, c in enumerate(columns) if c["x0"] <= _mid_x(w) < c["x1"]), -1)

    out: list[dict[str, Any]] = []
    name_column = next((c for c in columns if c["field"] == "name"), None)
    for index in sorted(rows):
        ws = rows[index]
        # A merged cell (a section title across the table): its words lie close together and cross a column border (``:197-209``).
        seq = sorted(ws, key=lambda w: float(w[0]))
        col_of = [column_of(w) for w in seq]
        spans = any(
            col_of[k] != col_of[k + 1] and float(seq[k + 1][0]) - float(seq[k][2]) < 0.6 * (float(seq[k][3]) - float(seq[k][1]))
            for k in range(len(seq) - 1)
        )
        bbox = [min(float(w[0]) for w in ws), min(float(w[1]) for w in ws), max(float(w[2]) for w in ws), max(float(w[3]) for w in ws)]
        if spans:
            text = " ".join(str(w[4]) for w in seq)
            if not any(columns[col_of[k]]["field"] in ("unit", "quantity") for k in range(len(seq)) if col_of[k] >= 0):
                out.append({"cells": {"name": text}, "bbox": [round(v, 1) for v in bbox], "centered": True, "bold": False, "span": True})
                continue
        cells: dict[str, str] = {}
        boxes: dict[str, list[float]] = {}
        for c in columns:
            if not c["field"]:
                continue
            cw = sorted((w for w in ws if c["x0"] <= _mid_x(w) < c["x1"]), key=lambda w: (round(float(w[1]) / 4), float(w[0])))
            if cw:
                cells[c["field"]] = " ".join(str(w[4]) for w in cw)
                boxes[c["field"]] = [
                    min(float(w[0]) for w in cw), min(float(w[1]) for w in cw), max(float(w[2]) for w in cw), max(float(w[3]) for w in cw)
                ]
        if not cells:
            continue
        # The row of column numbers «1 2 3 ... 9» under the header is not a position (``:221-223``).
        if all(NUM_RE.match(v.strip()) for v in cells.values()) and len(cells) >= 4:
            continue
        nb = boxes.get("name")
        centered = bool(
            nb and name_column
            and abs((nb[0] + nb[2]) / 2 - (name_column["x0"] + name_column["x1"]) / 2) < 0.12 * (name_column["x1"] - name_column["x0"])
            and nb[0] > name_column["x0"] + 0.15 * (name_column["x1"] - name_column["x0"])
        )
        out.append({"cells": cells, "bbox": [round(v, 1) for v in bbox], "centered": centered, "bold": False})
    return {"parsed": True, "rows": out, "columns": [c["field"] for c in columns]}


def _row_type(cells: dict[str, str]) -> str:
    """``spec.py:237-246``: by the filled cells, not by the number."""
    if cells.get("unit") or cells.get("quantity"):
        return "quantity"
    has_mark = bool(cells.get("mark") or cells.get("code"))
    if has_mark and cells.get("name"):
        return "parent"
    if has_mark:
        return "mark_only"
    return "text"


def assemble(pages: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """The stream of positions over the specification pages of one version, in the order of the version (``spec.py:249-325``).

    ``pages`` is ``[{"page": number, "rows": [...]}, ...]`` (the rows of :func:`parse_page`). A position has a quantity or a unit;
    a parent has a name and a mark and no quantity, the sub-rows below it belong to it; a text-only row is a continuation of the
    previous position or parent, or a section title. The top rows of a new page are classified by the same rules (a sub-row at the
    top of a page belongs to the last parent of the previous page). A boundary that is not obvious at a page break flags the item
    ``ambiguous`` (``:312-313``). Returns ``{"items": [...], "parents": [...]}``; an item carries ``id``, ``kind`` (``position`` or
    ``child``), ``section``, ``page``, ``rows`` (``[[page, x0, top, x1, bottom], ...]``), ``parent`` and the nine fields.
    """
    items: list[dict[str, Any]] = []
    parents: dict[str, dict[str, Any]] = {}
    section: list[str] = []
    parent: dict[str, Any] | None = None
    parent_has_children = False
    last: dict[str, Any] | None = None

    def new_item(kind: str, cells: dict[str, str], page: int, bbox: list[float], par: dict[str, Any] | None) -> dict[str, Any]:
        item: dict[str, Any] = {
            "id": f"i{len(items) + 1}", "kind": kind, "section": " / ".join(section), "page": page,
            "rows": [[page, *bbox]], "parent": par["id"] if par else None, "ambiguous": False,
        }
        for field in FIELDS:
            item[field] = cells.get(field, "")
        items.append(item)
        return item

    for pg in pages:
        first_row = True
        page = int(pg["page"])
        for row in pg["rows"]:
            cells, bbox = row["cells"], row["bbox"]
            kind = _row_type(cells)
            name = cells.get("name", "")
            if kind == "quantity":
                # A sub-row of the parent: a size or an execution, or the first row with a quantity right under the parent (``:272-281``).
                if (
                    parent
                    and not cells.get("mark") and not cells.get("code") and not cells.get("pos")
                    and (SIZE_RE.match(name.strip() or "-") or not parent_has_children)
                ):
                    last = new_item("child", cells, page, bbox, parent)
                    parent_has_children = True
                else:
                    last = new_item("position", cells, page, bbox, None)
                    parent, parent_has_children = None, False
            elif kind in ("parent", "mark_only"):
                pid = f"g{len(parents) + 1}"
                parent = {"id": pid, "section": " / ".join(section), "page": page, "rows": [[page, *bbox]]}
                for field in FIELDS:
                    parent[field] = cells.get(field, "")
                parents[pid] = parent
                parent_has_children = False
                last = parent
            else:  # text only (``:290-317``)
                text = (name or " ".join(cells.values())).strip()
                first = text[:1]
                if row.get("centered") or row.get("bold"):
                    if row.get("centered") or not section:
                        section = [text]
                    else:
                        section = section[:1] + [text]
                    parent, parent_has_children, last = None, False, None
                elif parent is not None and not parent_has_children:
                    # The name of the parent goes on (a supplier «или аналог» goes to the same parent).
                    for field in ("name", "supplier", "note"):
                        if cells.get(field):
                            parent[field] = (parent[field] + " " + cells[field]).strip()
                    parent["rows"].append([page, *bbox])
                elif last is not None and (first.islower() or first in '(-–,.;:"«' or SIZE_RE.match(text)):
                    # A continuation of a phrase (lower case, a bracket, a size «3х1.5») goes to the previous position. A line that starts
                    # with a digit and is not a size («2 этаж кв.9») is a sub-title.
                    for field in ("name", "supplier", "note"):
                        if cells.get(field):
                            last[field] = (last[field] + " " + cells[field]).strip()
                    last["rows"].append([page, *bbox])
                    if first_row and last.get("page") != page and not first.islower():
                        last["ambiguous"] = True  # the boundary of a position at a page break is not obvious
                else:
                    # A capital after a finished position is a sub-title of the section.
                    section = (section[:1] + [text]) if section else [text]
                    parent, parent_has_children, last = None, False, None
            first_row = False
    # A sub-row gets the name and the mark of its parent (``:319-324``).
    for item in items:
        if item["parent"]:
            par = parents[item["parent"]]
            item["parent_name"], item["parent_mark"] = par["name"], par["mark"]
            item["parent_code"], item["parent_supplier"] = par["code"], par["supplier"]
    return {"items": items, "parents": list(parents.values())}
