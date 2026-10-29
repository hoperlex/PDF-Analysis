"""The candidate objects of a sheet from the engine's pointers and the two pages (`CMP-VC-AISHEET-01`; no model, zero tokens).

A port of the original's ``sheet_changes/collect.py`` (`23f379fd`, lines 1-471) onto this tree's raw evidence.

A **pointer** is one entry of the engine's stored result -- ``text_changes``, ``differences``, ``service_notes`` of
``comparison_sheet_pair_result.result`` -- "there is a difference here". A **candidate** is a preliminary grouping for the model:

* ``table`` -- a table of the drawing: rows of A and B whole (by the ruling lines), the header, a preliminary pairing of rows by designation
  (it may be wrong);
* ``place`` -- a place on the drawing: the pointers near each other, the words of the areas of A and B, the nearest room and opening
  designations;
* ``shift`` -- a shift of a graphic element outside any other place (a possible move of an object).

The model may join, split or redefine candidates -- the grouping is preliminary. Every pointer gets exactly one fate (candidate, attached
to a candidate, excluded with a reason, counted through a link, not sorted): the ledger is for diagnostics. Only what is confidently
recognised as service is excluded; the content under a mark stays.

Where the engine's evidence is thinner than the original's records, and what was done (each is a reason in the report):

* the engine keeps one box for a text change and for a region, on the canvas of page A; the box on page B is the inverse of the engine's
  registration matrix applied to it (the original had a second box from its records);
* a region of the class ``text`` that overlaps a text change is **linked** to it (the original's ``group == "linked"``), not a candidate of
  its own; the layers ``within_tolerance`` and ``noise`` and the service zones are excluded as the engine's own side-products.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Final

from auditmanager.comparison.ai_sheets import geometry as geo
from auditmanager.comparison.ai_sheets import tables as tb

__all__ = [
    "ANCHOR",
    "Collected",
    "PageText",
    "REASONS",
    "UNIT_NUMBER",
    "collect",
    "norm_mark",
    "pointers_of",
]

PLACE_GAP_PT: Final[float] = 45.0  # pointers closer than this are one place (collect.py:30)
PLACE_MAX_PT: Final[float] = 650.0  # a place does not grow beyond this on a side (collect.py:31)
CONTEXT_PAD_PT: Final[float] = 55.0  # collect.py:32
CONTEXT_MIN_PT: Final[float] = 190.0  # collect.py:33
FULL_TABLE_ROWS: Final[int] = 15  # collect.py:34
FULL_TABLE_CHARS: Final[int] = 6000  # over this only the touched rows and the rows with the same designations (collect.py:35)
SPECK_PT: Final[float] = 3.0  # collect.py:36
TAG: Final = re.compile(r"^(\d{1,2})\.(\d{1,2})$")  # collect.py:37
ANCHOR: Final = re.compile(r"^([А-ЯЁA-Z]{1,3}\.\d{1,3}[а-я]?|[А-ЯЁ]{1,4}\d{1,3}[А-ЯЁ]{0,2}-\d{1,2}|ЛФ-\d+)$")  # collect.py:38
UNIT_NUMBER: Final = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:-|–)\s*\d+|\d+(?:[.,]\d+)?\s*(?:мм|см|м2|м²|м|%|кВт|А|шт)\b"
)  # collect.py:40
_MARKS: Final = re.compile(r"[A-Za-zА-Яа-яЁё]{1,4}-[0-9][0-9A-Za-zА-Яа-яЁё*/.]*")  # pack.py:218
_HOMO: Final = str.maketrans("ABCEHKMOPTXaceopxy", "АВСЕНКМОРТХасеорху")  # context.py:25

#: ``collect.py:42-50``, with the two reasons this tree's evidence adds (``engine_noise``, ``normalisation``).
REASONS: Final[Mapping[str, str]] = {
    "service": "служебное поле или зона штампа (дата выпуска, QR, изменения штампа)",
    "revision_tag": "отметка изменения с номером текущего изменения B",
    "whitespace": "только пробелы",
    "label_move": "перемещение надписи без изменения текста, вне мест с другими изменениями",
    "line_style": "только толщина или тон линии: линия есть в обеих версиях (класс движка), вне мест с изменениями",
    "shift_speck": "сдвиг без изменённых пикселей размером меньше 3 pt (артефакт совмещения)",
    "engine_noise": "в пределах допуска совмещения или шум (слой движка)",
}

#: ``collect.py:177-190`` ``_what``.
_TEXT_WHAT: Final[Mapping[str, str]] = {
    "changed": "текст изменён", "added": "текст добавлен (B)", "removed": "текст удалён (A)", "moved": "надпись перемещена",
}
_REGION_WHAT: Final[Mapping[str, str]] = {
    "added": "графика добавлена (B)", "removed": "графика удалена (A)", "changed": "графика изменена",
    "text": "текст и графика", "color": "изменён цвет", "light": "светлая заливка/штриховка", "shifted": "элемент сдвинут",
    "block_moved": "блок перемещён", "style": "толщина/тон линии", "text_moved": "надпись перемещена",
}
#: The engine's ``region_class`` (``engine/child/result.py`` ``REGION_CLASSES``) as the original's region ``kind``.
_REGION_KIND: Final[Mapping[str, str]] = {
    "text": "text", "text_moved": "text_moved", "graphic_added": "added", "graphic_removed": "removed",
    "graphic_changed": "changed", "color_change": "color", "light_fill": "light", "line_style": "style",
    "block_moved": "block_moved", "shifted": "shifted",
}
_NOISE_LAYERS: Final[frozenset[str]] = frozenset({"within_tolerance", "noise"})


def norm_mark(text: str) -> str:
    """``context.py:157-158``."""
    return text.strip(" -.,;:()").translate(_HOMO).replace(",", ".").casefold()


class PageText:
    """The words and the ruling lines of one page, as the candidates read them (the words as ``(x0, top, x1, bottom, text)``)."""

    def __init__(self, words: Sequence[Sequence[Any]], lines: Sequence[Sequence[Any]], *, revision_number: str | None = None) -> None:
        self.words: list[tuple[float, float, float, float, str]] = [
            (float(w[0]), float(w[1]), float(w[2]), float(w[3]), str(w[4])) for w in words
        ]
        self.rulings = tb.Rulings(lines)
        self.revision_number = revision_number

    def words_in(self, box: Sequence[float], limit: int = 1500) -> str:
        """``collect.py:123-126``."""
        found = [w for w in self.words if geo.intersects(box, w[:4])]
        text = tb.lines_text(found)
        return text if len(text) <= limit else text[:limit] + " …"


# -- the pointers -----------------------------------------------------------------------------------------------------------


def _what_text(kind: str) -> str:
    base = kind.split("_", 1)[0]
    return _TEXT_WHAT.get(base, f"текст: {kind}")


def pointers_of(result: Mapping[str, Any], transform: Sequence[float]) -> list[dict[str, Any]]:
    """The pointers of a stored result, in a fixed order: ``T`` text changes, ``D`` differences, ``S`` service notes.

    A pointer is ``{id, type, kind, what, before, after, bbox_a, bbox_b, box, pixels, ...}``; ``type`` is ``text``, ``region`` or
    ``service`` (the original's records, ``collect.py:193-199``). Raw evidence is copied, never rewritten: ``before`` and ``after`` are
    the engine's texts, clipped to 300 characters as the original's pointer did.
    """
    out: list[dict[str, Any]] = []

    def b_box(box: list[float] | None) -> list[float] | None:
        return None if box is None else geo.rounded(geo.a_to_b_page(transform, box))

    for index, change in enumerate(result.get("text_changes") or [], 1):
        kind = str(change["kind"])
        base, _, norm = kind.partition("_")
        box = geo.box_of(change.get("box"))
        before, after = str(change.get("before") or ""), str(change.get("after") or "")
        out.append({
            "id": f"T{index}", "type": "text", "kind": base, "norm": norm or None, "what": _what_text(kind),
            "before": before[:300], "after": after[:300],
            "bbox_a": box if (before or base == "moved") and base != "added" else None,
            "bbox_b": b_box(box) if (after or base == "moved") and base != "removed" else None,
            "box": box, "pixels": 0, "numbers": list(change.get("numbers") or []),
        })
    for index, difference in enumerate(result.get("differences") or [], 1):
        region_class = str(difference["region_class"])
        kind = _REGION_KIND.get(region_class, region_class)
        box = geo.box_of(difference.get("box"))
        before, after = str(difference.get("before_text") or ""), str(difference.get("after_text") or "")
        out.append({
            "id": f"D{index}", "type": "region", "kind": kind, "layer": str(difference.get("layer") or "main"), "norm": None,
            "what": _REGION_WHAT.get(kind, f"графика: {kind}"), "before": before[:300], "after": after[:300],
            "bbox_a": None if kind == "added" else box, "bbox_b": None if kind == "removed" else b_box(box), "box": box, "pixels": 0,
            "numbers": [],
        })
    for index, note in enumerate(result.get("service_notes") or [], 1):
        out.append({
            "id": f"S{index}", "type": "service", "kind": str(note["kind"]), "norm": None,
            "what": f"служебное ({note['kind']}, {note['change']})", "before": str(note.get("before") or "")[:300],
            "after": str(note.get("after") or "")[:300], "bbox_a": None, "bbox_b": None, "box": None, "pixels": 0, "numbers": [],
        })
    return out


def _overlap(a: Sequence[float], b: Sequence[float]) -> float:
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    return ix * iy if ix > 0 and iy > 0 else 0.0


def _link_regions(pointers: list[dict[str, Any]]) -> None:
    """A region of the class ``text`` that overlaps a text change is that change seen as a region: it is linked to it
    (``group == "linked"``, ``collect.py:82-83``)."""
    texts = [p for p in pointers if p["type"] == "text" and p["box"]]
    for p in pointers:
        if p["type"] != "region" or p["kind"] != "text" or not p["box"]:
            continue
        hits = [t["id"] for t in texts if _overlap(p["box"], t["box"]) > 0]
        if hits:
            p["group"] = "linked"
            p["links"] = hits


def _role(pointer: Mapping[str, Any], izm_b: int | None) -> tuple[str, str | None]:
    """``(strength, reason)`` -- strong / weak / excluded / linked (``collect.py:63-91``)."""
    kind, type_ = pointer["kind"], pointer["type"]
    if type_ == "service":
        return "excluded", "service"
    if type_ == "text":
        if kind == "moved":
            return "weak", "label_move"
        if pointer.get("norm") == "spaces":
            return "excluded", "whitespace"
        match = TAG.match((pointer.get("after") or "").strip())
        if kind == "added" and match and izm_b is not None and int(match.group(1)) == izm_b:
            return "excluded", "revision_tag"
        return "strong", None
    if type_ == "region":
        if pointer.get("layer") == "service_zones":
            return "excluded", "service"
        if pointer.get("layer") in _NOISE_LAYERS:
            return "excluded", "engine_noise"
        if pointer.get("group") == "linked":
            return "linked", None
        if kind == "text_moved":
            return "weak", "label_move"
        if kind in ("shifted", "block_moved"):
            return "weak", "object_shift"
        if kind == "style":
            return "weak", "line_style"
        return "strong", None
    return "strong", None


# -- geometry helpers of the candidates ---------------------------------------------------------------------------------------


def _box_center(box: Sequence[float]) -> tuple[float, float]:
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def _dist(a: Sequence[float], b: Sequence[float]) -> float:
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return (dx * dx + dy * dy) ** 0.5


def _anchors(words: Sequence[Sequence[Any]], box: Sequence[float], n: int = 4) -> list[str]:
    """The nearest designations of rooms and openings (``collect.py:146-162``)."""
    centre = _box_center(box)
    found = []
    for w in words:
        token = str(w[4]).strip(" ,;")
        if ANCHOR.match(token):
            wc = _box_center([float(v) for v in w[:4]])
            distance = ((wc[0] - centre[0]) ** 2 + (wc[1] - centre[1]) ** 2) ** 0.5
            if distance <= 260:
                found.append((distance, token))
    out: list[str] = []
    for distance, token in sorted(found):
        if token not in [x.split(" ")[0] for x in out]:
            out.append(f"{token} ({int(distance)} pt)")
        if len(out) >= n:
            break
    return out


def _context_box(area: Sequence[float]) -> list[float]:
    box = geo.expand(area, CONTEXT_PAD_PT)
    width, height = box[2] - box[0], box[3] - box[1]
    if width < CONTEXT_MIN_PT:
        box[0] -= (CONTEXT_MIN_PT - width) / 2
        box[2] += (CONTEXT_MIN_PT - width) / 2
    if height < CONTEXT_MIN_PT:
        box[1] -= (CONTEXT_MIN_PT - height) / 2
        box[3] += (CONTEXT_MIN_PT - height) / 2
    return [round(v, 1) for v in box]


# -- tables ---------------------------------------------------------------------------------------------------------------------


def _marks_of(candidate: Mapping[str, Any]) -> set[str]:
    texts = list(candidate.get("labels_a") or []) + list(candidate.get("labels_b") or [])
    texts += [r["key"] for r in (candidate.get("rows_a") or []) + (candidate.get("rows_b") or []) if r.get("key")]
    out: set[str] = set()
    for text in texts:
        for mark in _MARKS.findall(text or ""):
            out.add(norm_mark(mark))
    return out


class _Sheet:
    def __init__(self, page_a: PageText, page_b: PageText, transform: Sequence[float]) -> None:
        self.text = {"A": page_a, "B": page_b}
        self.transform = tuple(transform)
        self._headers: dict[tuple[str, tuple[float, ...]], dict[str, Any] | None] = {}

    def b_box(self, box_a: Sequence[float]) -> list[float]:
        return geo.a_to_b_page(self.transform, box_a)

    def b_to_a(self, box_b: Sequence[float]) -> list[float]:
        return geo.b_page_to_a(self.transform, box_b)

    def header(self, side: str, row: dict[str, Any]) -> dict[str, Any] | None:
        key = (side, tuple(row["box"]))
        if key not in self._headers:
            page = self.text[side]
            self._headers[key] = tb.header_for(page.rulings, page.words, row)
        return self._headers[key]


def _tables(sheet: _Sheet, strong: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], set[str]]:
    """The text pointers inside table rows as table candidates; returns the tables and the ids that are in them (``collect.py:212-242``)."""
    groups: list[dict[str, Any]] = []
    used: set[str] = set()
    for pointer in strong:
        if pointer["type"] != "text":
            continue
        rows: dict[str, dict[str, Any]] = {}
        for side, key in (("A", "bbox_a"), ("B", "bbox_b")):
            if pointer.get(key):
                page = sheet.text[side]
                row = tb.row_at(page.rulings, page.words, pointer[key])
                # A band with no header of a table is not a row (the walls of a plan also give bands).
                if row and len(row["cells"]) >= 2 and sheet.header(side, row):
                    rows[side] = row
        if not rows:
            continue
        extent = next(iter(rows.values()))["box"]
        group = next(
            (g for g in groups if min(g["x"][1], extent[2]) - max(g["x"][0], extent[0])
             > 0.8 * min(g["x"][1] - g["x"][0], extent[2] - extent[0])),
            None,
        )
        if group is None:
            group = {"x": [extent[0], extent[2]], "pointers": [], "rows": {"A": {}, "B": {}}}
            groups.append(group)
        group["pointers"].append(pointer["id"])
        for side, row in rows.items():
            group["rows"][side][tuple(row["box"])] = row
        used.add(pointer["id"])
    out = []
    for group in groups:
        sample = next(iter(group["rows"]["A"].values()), None) or next(iter(group["rows"]["B"].values()))
        out.append(_table_candidate(sheet, group, sample))
    return out, used


def _table_candidate(sheet: _Sheet, group: dict[str, Any], sample: dict[str, Any]) -> dict[str, Any]:
    headers = {s: tb.header_for(sheet.text[s].rulings, sheet.text[s].words, sample) for s in ("A", "B")}
    header = headers["A"] or headers["B"]
    rows: dict[str, list[dict[str, Any]]] = {}
    full = False
    if header and header["cells"]:
        key_x = (header["cells"][0]["x"][0] + header["cells"][0]["x"][1]) / 2
        x0, _, x1, _ = header["box"]
        all_rows = {
            s: tb.rows_below(sheet.text[s].rulings, sheet.text[s].words, headers[s] or header, key_x, x0, x1) for s in ("A", "B")
        }
        size = sum(len(r["text"]) for v in all_rows.values() for r in v)
        if all(0 < len(v) <= FULL_TABLE_ROWS for v in all_rows.values()) and size <= FULL_TABLE_CHARS:
            rows, full = all_rows, True
    if not full:
        touched = {s: sorted(group["rows"][s].values(), key=lambda row: row["box"][1]) for s in ("A", "B")}
        keys = {tb.row_key(row) for s in ("A", "B") for row in touched[s]} - {""}
        # to the touched rows, the rows with the same designations on the other side
        if header and header["cells"]:
            key_x = (header["cells"][0]["x"][0] + header["cells"][0]["x"][1]) / 2
            x0, _, x1, _ = header["box"]
            for s in ("A", "B"):
                have = {tuple(row["box"]) for row in touched[s]}
                for row in tb.rows_below(sheet.text[s].rulings, sheet.text[s].words, headers[s] or header, key_x, x0, x1):
                    if tb.row_key(row) in keys and tuple(row["box"]) not in have:
                        touched[s].append(row)
                touched[s].sort(key=lambda row: row["box"][1])
        rows = touched
    for s in rows:
        # a band inside another row of the same side (a line inside a cell) is not a row of its own
        rows[s] = [
            row for row in rows[s]
            if not any(o is not row and geo.contains(geo.expand(o["box"], 0.5), row["box"]) and o["box"] != row["box"] for o in rows[s])
        ]
        for row in rows[s]:
            row["key"] = tb.row_key(row)
    title = ""
    if header:
        above = [
            w for w in sheet.text["A"].words
            if header["box"][0] <= w[0] <= header["box"][2] and header["box"][1] - 28 <= w[1] <= header["box"][1] - 1
        ]
        title = tb.lines_text(above)[:200]
    keys_a = {norm_mark(r["key"]): r["key"] for r in rows.get("A", []) if r["key"]}
    keys_b = {norm_mark(r["key"]): r["key"] for r in rows.get("B", []) if r["key"]}
    region = {
        s: geo.union([r["box"] for r in rows.get(s, [])] + ([headers[s]["box"]] if headers[s] else [])) for s in ("A", "B")
    }
    return {
        "kind": "table", "title": title, "header": header["text"] if header else "", "full": full,
        "header_box": header["box"] if header else None,
        "rows_a": [{"key": r["key"], "text": r["text"], "box": r["box"]} for r in rows.get("A", [])],
        "rows_b": [{"key": r["key"], "text": r["text"], "box": r["box"]} for r in rows.get("B", [])],
        "pairs": [{"key": keys_a[k], "a": keys_a[k], "b": keys_b[k]} for k in keys_a if k in keys_b],
        "unpaired_a": [keys_a[k] for k in keys_a if k not in keys_b],
        "unpaired_b": [keys_b[k] for k in keys_b if k not in keys_a],
        "region_a": region["A"], "region_b": region["B"], "pointers": list(group["pointers"]),
        "area": geo.union([region["A"], sheet.b_to_a(region["B"]) if region["B"] else None]),
    }


def _row_boxes_a(sheet: _Sheet, table: dict[str, Any]) -> list[list[float]]:
    out = [r["box"] for r in table["rows_a"]] + [sheet.b_to_a(r["box"]) for r in table["rows_b"]]
    if table.get("header_box"):
        out.append(geo.union([table["header_box"]] + [r["box"] for r in table["rows_a"][:1]]))
    if table.get("full"):
        out += [
            b for b in (table.get("region_a"), sheet.b_to_a(table["region_b"]) if table.get("region_b") else None) if b
        ]
    return out


def _table_host(sheet: _Sheet, tables: list[dict[str, Any]], box: Sequence[float] | None) -> dict[str, Any] | None:
    if not box or not tables:
        return None
    cx, cy = _box_center(box)
    point = [cx, cy, cx, cy]
    for table in tables:
        if any(geo.contains(geo.expand(rb, 1.0), point) for rb in _row_boxes_a(sheet, table)):
            return table
    best, best_area = None, 0.0
    for table in tables:
        for rb in _row_boxes_a(sheet, table):
            area = _overlap(rb, box)
            if area > best_area:
                best, best_area = table, area
    return best


# -- places -----------------------------------------------------------------------------------------------------------------------


def _clusters(items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    parent = list(range(len(items)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if _dist(items[i]["box"], items[j]["box"]) <= PLACE_GAP_PT:
                a, b = find(i), find(j)
                if a != b:
                    u = geo.union([items[k]["box"] for k in range(len(items)) if find(k) in (a, b)])
                    if u is not None and max(u[2] - u[0], u[3] - u[1]) <= PLACE_MAX_PT:
                        parent[a] = b
    grouped: dict[int, list[dict[str, Any]]] = {}
    for i, item in enumerate(items):
        grouped.setdefault(find(i), []).append(item)

    def order(cluster: list[dict[str, Any]]) -> tuple[int, float]:
        u = geo.union([x["box"] for x in cluster]) or [0.0, 0.0, 0.0, 0.0]
        return round(u[1] / 50), u[0]

    return sorted(grouped.values(), key=order)


def _place_candidate(sheet: _Sheet, members: list[dict[str, Any]], kind: str = "place") -> dict[str, Any]:
    area = geo.union([m["box"] for m in members]) or [0.0, 0.0, 0.0, 0.0]
    context_a = _context_box(area)
    context_b = sheet.b_box(context_a)
    labels_a = [m["before"] for m in members if m["type"] == "text" and m["before"]]
    labels_b = [m["after"] for m in members if m["type"] == "text" and m["after"]]
    return {
        "kind": kind, "area": [round(v, 1) for v in area], "context_a": context_a, "context_b": [round(v, 1) for v in context_b],
        # The title of a view by the words of the sheet is unreliable (it picks up a neighbouring fragment): it is not passed
        # (collect.py:354-355); the place is given by the nearest designations and the overview image.
        "view": "",
        "anchors": _anchors(sheet.text["B"].words, sheet.b_box(area)) or _anchors(sheet.text["A"].words, area),
        "labels_a": labels_a, "labels_b": labels_b,
        "words_a": sheet.text["A"].words_in(context_a), "words_b": sheet.text["B"].words_in(context_b),
        "pointers": [m["id"] for m in members],
    }


def _link(candidates: list[dict[str, Any]]) -> None:
    marks = {c["id"]: _marks_of(c) for c in candidates}
    for c in candidates:
        c["links"] = sorted(o["id"] for o in candidates if o is not c and marks[c["id"]] & marks[o["id"]])
        c["marks"] = sorted(marks[c["id"]])


# -- the whole -------------------------------------------------------------------------------------------------------------------


class Collected:
    """What :func:`collect` made: the candidates, the pointers by id, the fate of each pointer and its counts."""

    __slots__ = ("candidates", "pointers", "ledger", "counts", "izm_b")

    def __init__(
        self, candidates: list[dict[str, Any]], pointers: dict[str, dict[str, Any]], ledger: dict[str, dict[str, Any]],
        counts: dict[str, int], izm_b: int | None,
    ) -> None:
        self.candidates, self.pointers, self.ledger, self.counts, self.izm_b = candidates, pointers, ledger, counts, izm_b


def _int_or_none(value: str | None) -> int | None:
    try:
        return int(value) if value is not None and str(value).strip() else None
    except (TypeError, ValueError):
        return None


def collect(
    result: Mapping[str, Any], page_a: PageText, page_b: PageText, transform: Sequence[float] | None = None,
) -> Collected:
    """The candidates of a sheet pair from the stored result and the two pages (``collect.py:365-454``)."""
    matrix = tuple(transform) if transform else geo.IDENTITY
    sheet = _Sheet(page_a, page_b, matrix)
    izm_b = _int_or_none(page_b.revision_number)
    pointer_list = pointers_of(result, matrix)
    _link_regions(pointer_list)
    pointers = {p["id"]: p for p in pointer_list}
    ledger: dict[str, dict[str, Any]] = {}
    strong: list[dict[str, Any]] = []
    weak: list[tuple[dict[str, Any], str]] = []
    for p in pointer_list:
        role, reason = _role(p, izm_b)
        if role == "excluded":
            ledger[p["id"]] = {"status": "excluded", "reason": reason}
        elif role == "linked":
            ledger[p["id"]] = {"status": "linked", "links": p.get("links") or []}
        elif role == "weak":
            weak.append((p, reason or ""))
        else:
            if p["box"] is None:
                ledger[p["id"]] = {"status": "unassigned", "reason": "нет рамки"}
                continue
            strong.append(p)
    # The frames of change marks: graphics wholly inside a mark are a mark too (collect.py:385-393).
    tags = [pointers[i]["box"] for i, e in ledger.items() if e.get("reason") == "revision_tag" and pointers[i]["box"]]
    kept = []
    for p in strong:
        if p["type"] == "region" and any(geo.contains(geo.expand(t, 10.0), p["box"]) for t in tags):
            ledger[p["id"]] = {"status": "excluded", "reason": "revision_tag"}
        else:
            kept.append(p)
    strong = kept

    candidates: list[dict[str, Any]] = []
    tables, in_tables = _tables(sheet, strong)
    candidates.extend(tables)
    rest = [p for p in strong if p["id"] not in in_tables]
    # graphics inside the rows of a table go to the table: by the centre first, then by the largest overlap of rows
    free = []
    for p in rest:
        host = _table_host(sheet, tables, p.get("box"))
        if host is not None:
            host["pointers"].append(p["id"])
        else:
            free.append(p)
    for cluster in _clusters([p for p in free if p.get("box")]):
        candidates.append(_place_candidate(sheet, cluster))
    # weak pointers: inside a place -- to the place; otherwise by the rules
    for p, reason in weak:
        box = p.get("box")
        host = None
        if box:
            cx, cy = _box_center(box)
            host = next(
                (k for k in candidates if k.get("area") and geo.contains(geo.expand(k["area"], 15.0), [cx, cy, cx, cy])), None,
            )
        if host is not None:
            host.setdefault("attached", []).append(p["id"])
            continue
        if reason == "object_shift":
            small = box and max(box[2] - box[0], box[3] - box[1]) < SPECK_PT and p["pixels"] == 0
            if small:
                ledger[p["id"]] = {"status": "excluded", "reason": "shift_speck"}
            else:
                candidates.append(_place_candidate(sheet, [p], kind="shift"))
            continue
        ledger[p["id"]] = {"status": "excluded", "reason": reason}
    for number, candidate in enumerate(candidates, 1):
        candidate["id"] = f"O{number}"
        for pid in candidate["pointers"]:
            ledger[pid] = {"status": "candidate", "candidate": candidate["id"]}
        for pid in candidate.get("attached") or []:
            ledger[pid] = {"status": "attached", "candidate": candidate["id"]}
    for pid, entry in ledger.items():
        if entry["status"] == "linked":
            hosts = {ledger.get(t, {}).get("candidate") for t in entry["links"]} - {None}
            entry["candidate"] = sorted(hosts)[0] if hosts else None
            if not hosts:
                entry.update(status="unassigned", reason="связанный текст не попал в кандидата")
        if entry.get("reason") in REASONS:
            entry["reason_text"] = REASONS[entry["reason"]]
    for p in pointer_list:
        ledger.setdefault(p["id"], {"status": "unassigned", "reason": "не отнесён"})
    _link(candidates)
    counts: dict[str, int] = {}
    for entry in ledger.values():
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    return Collected(candidates, pointers, ledger, counts, izm_b)
