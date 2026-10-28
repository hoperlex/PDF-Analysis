"""«Разрешение на внесение изменений»: what the designer declared against what the comparison found (`CMP-SERIES-01`).

Pure: no database, no clock, no PDF library. A port of the original's ``permit.py`` and ``_permit_phase``
(``jobs.py:951-968``), read at ``23f379fd`` from the public repository (the local clone does not exist):

* the table «Изм. | Лист | Содержание изменения | Код» is read from the page's words and vertical lines
  (``permit.py:63-127``); the text is taken literally and shown as «заявлено проектировщиком»;
* the declared sheets are those of rows whose «Изм.» is above the older version's last «Изм.» (``permit.py:174``);
* the reconciliation is by the set of sheets, the number from the stamp, no reading of meaning (``permit.py:167-219``):
  *declared and a difference found* -> ``declared_and_found``; *declared, no difference* -> ``declared_no_diff``;
  *a difference found, not declared* -> ``diff_not_declared``; a sheet number that repeats in the version, a number
  with no sheet in the version, or a sheet that itself needs a review -> ``needs_review``.

Where this port differs from the original, and why:

* the original reads the PDF with PyMuPDF (``OD-01`` excludes it) and takes the words and the vertical segments of the
  page from it; here they are the page profile's words and vector lines, the same facts without a second reader;
* the original looks for the table header only in the top 35 % of a page of kind ``permit`` or ``title``
  (``permit.py:64``, ``:136``); the profile has no page kind, and the synthetic corpus draws the table lower on the first
  sheet (header at 37 % of the height), so the whole page is searched and the caller offers the first pages of the version;
* the permit's own number (``permit.py:91-95``) is not read: the contract has no place for it;
* a permit row that numbers a sheet in the main set where only the specification set has that number (once) means that
  sheet (the original would report «лист с таким номером не найден»): the synthetic corpus numbers its specification
  "7" in the main series, and the key expects that declaration to be found;
* the sheet that **carries** the permit table is not reported as «отличия найдены, но не заявлены»: its table grows with every
  revision and the new row is its declaration (the synthetic corpus' key names that sheet the ``carrier_sheet`` and leaves it
  out of ``found_not_declared``; the original has no such rule and would list it every time).
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Final

__all__ = [
    "MAX_ITEMS",
    "PermitWord",
    "izm_of",
    "pair_permits",
    "parse_page",
    "parse_sheet_refs",
    "reconcile",
    "ref_label",
    "sheet_ref",
]

#: ``ComparisonPermit.items`` holds at most 200 entries, each text at most 2000 characters.
MAX_ITEMS: Final[int] = 200
MAX_TEXT: Final[int] = 2000

#: ``(x0, top, x1, bottom, text)``: a word as the profile gives it.
PermitWord = tuple[float, float, float, float, str]

_IZM = re.compile(r"^\d{1,2}$")
_HEAD: Final[dict[str, tuple[str, ...]]] = {
    "izm": ("изм",), "sheet": ("лист",), "text": ("содержание",), "code": ("код",), "note": ("примечан",),
}
_REF = re.compile(
    r"(?P<so>СО|С\.О\.)?\s*(?:л\.?|лист)?\s*(?P<a>\d+)(?P<sfx>[а-я])?"
    r"(?:\s*[-–…]+\s*(?:СО|С\.О\.)?\s*(?:л\.?)?\s*(?P<b>\d+))?",
    re.I,
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "")).lower()


def parse_sheet_refs(text: str) -> list[dict[str, str]]:
    """«4,5» -> [4, 5]; «СО л. 2» -> [СО 2]; «2-27 14-16» -> 2..27, 14..16; «все» -> [all] (``permit.py:37-60``)."""
    t = " ".join(str(text or "").split())
    if not t:
        return []
    if re.search(r"\bвсе\b", t, re.I):
        return [{"set": "all", "sheet": "*"}]
    out: list[dict[str, str]] = []
    pos = 0
    for m in _REF.finditer(t):
        gap = t[pos:m.start()].strip(" ,;")
        if gap:
            out.append({"set": "unparsed", "sheet": gap})
        pos = m.end()
        kind = "СО" if m.group("so") else "main"
        a, b = int(m.group("a")), m.group("b")
        if b and 0 <= int(b) - a <= 200:
            out += [{"set": kind, "sheet": str(k)} for k in range(a, int(b) + 1)]
        else:
            out.append({"set": kind, "sheet": str(a) + (m.group("sfx") or "")})
    rest = t[pos:].strip(" ,;")
    if rest:
        out.append({"set": "unparsed", "sheet": rest})
    return out


def _columns(
    words: Sequence[PermitWord], vertical: Sequence[tuple[float, float, float]], page_height: float
) -> tuple[list[dict[str, Any]], float, float] | None:
    """The columns of the permit table, the bottom of its header band and the bottom of the table (``permit.py:63-82``)."""
    izm = [w for w in words if _norm(w[4]).startswith("изм")]
    for iw in izm:
        cy = (iw[1] + iw[3]) / 2
        band = [w for w in words if abs((w[1] + w[3]) / 2 - cy) < 12]
        names = {f for f, keys in _HEAD.items() for w in band if any(_norm(w[4]).startswith(k) for k in keys)}
        if {"izm", "sheet", "text"} <= names:
            xs = sorted({round(x) for x, y0, y1 in vertical if y0 - 2 <= cy <= y1 + 2})
            cols: list[dict[str, Any]] = []
            for x0, x1 in zip(xs, xs[1:]):
                head = " ".join(w[4] for w in band if x0 <= (w[0] + w[2]) / 2 < x1)
                field = next((f for f, keys in _HEAD.items() if any(_norm(head).startswith(k) for k in keys)), None)
                if field:
                    cols.append({"x0": x0, "x1": x1, "field": field})
            if {"izm", "sheet", "text"} <= {c["field"] for c in cols}:
                bottoms = [
                    y1 for x, y0, y1 in vertical
                    if y0 - 2 <= cy <= y1 + 2 and cols[0]["x0"] - 1 <= x <= cols[-1]["x1"] + 1
                ]
                return cols, max(w[3] for w in band), (max(bottoms) if bottoms else page_height)
    return None


def parse_page(
    words: Sequence[PermitWord], vertical: Sequence[tuple[float, float, float]], page_height: float
) -> list[dict[str, Any]] | None:
    """The rows of the permit table of one page, or ``None`` when the page has none (``permit.py:85-127``).

    ``vertical`` are the page's vertical segments ``(x, top, bottom)``. A row is ``{"izm", "sheet", "text", "code",
    "note", "y", "refs"}``."""
    found = _columns(words, vertical, page_height)
    if not found:
        return None
    cols, head_bottom, table_bottom = found
    sign = [w[1] for w in words if w[1] > head_bottom and _norm(w[4]).startswith(("составил", "утв", "внес"))]
    stop = min([table_bottom + 1] + [y - 2 for y in sign])
    body = [
        w for w in words
        if head_bottom + 2 < w[1] and w[3] < stop and cols[0]["x0"] <= (w[0] + w[2]) / 2 <= cols[-1]["x1"]
    ]
    lines: dict[int, list[PermitWord]] = defaultdict(list)
    for w in sorted(body, key=lambda w: (w[1], w[0])):
        key = next((k for k in lines if abs(k - (w[1] + w[3]) / 2) < 4), None)
        lines[key if key is not None else round((w[1] + w[3]) / 2)].append(w)
    rows: list[dict[str, Any]] = []
    for y in sorted(lines):
        cells = {
            c["field"]: " ".join(
                w[4] for w in sorted(lines[y], key=lambda w: w[0]) if c["x0"] <= (w[0] + w[2]) / 2 < c["x1"]
            )
            for c in cols
        }
        izm = cells.get("izm", "").strip()
        if _IZM.match(izm) and rows and rows[-1]["izm"] == int(izm) and rows[-1]["sheet"].rstrip().endswith(("-", "–", ",")):
            for f in ("sheet", "text", "note"):  # the same «Изм.», the list of sheets goes on (``permit.py:110-114``)
                if cells.get(f):
                    rows[-1][f] = (rows[-1][f] + " " + cells[f]).strip()
        elif _IZM.match(izm):
            rows.append({
                "izm": int(izm), "sheet": cells.get("sheet", "").strip(), "text": cells.get("text", "").strip(),
                "code": cells.get("code", "").strip(), "note": cells.get("note", "").strip(), "y": round(y, 1),
            })
        elif rows and any(cells.values()):
            for f in ("sheet", "text", "note"):  # a wrapped line belongs to the last row (``permit.py:118-122``)
                if cells.get(f):
                    rows[-1][f] = (rows[-1][f] + " " + cells[f]).strip()
    if not rows:
        return None
    for row in rows:
        row["refs"] = parse_sheet_refs(row["sheet"])
    return rows


def sheet_ref(stamp: Mapping[str, Any] | None) -> dict[str, str] | None:
    """The sheet's number and set from its stamp (``permit.py:147-158``): ``СО`` by the designation or the title."""
    stamp = stamp or {}
    number = str(stamp.get("sheet_number") or "").strip()
    if not number:
        return None
    designation = str(stamp.get("designation") or "")
    title = str(stamp.get("sheet_name") or "").strip().lower()
    is_so = designation.upper().replace(" ", "").endswith(".СО") or title.startswith("спецификация")
    return {"set": "СО" if is_so else "main", "sheet": number}


def ref_label(ref: Mapping[str, str]) -> str:
    if ref["set"] == "all":
        return "все листы"
    return ("СО л." if ref["set"] == "СО" else "л.") + ref["sheet"]


def izm_of(permit_rows: Iterable[Mapping[str, Any]], revision_numbers: Iterable[Any]) -> int:
    """The last «Изм.» of a version: the largest in its permits and on its stamps (``jobs.py:944-948``)."""
    stamps: list[int] = []
    for value in revision_numbers:
        digits = re.sub(r"\D", "", str(value or ""))
        if digits:
            stamps.append(int(digits))
    return max([int(r["izm"]) for r in permit_rows] + stamps + [0])


def reconcile(
    permits_b: Sequence[Mapping[str, Any]],
    izm_a: int,
    stamps_b: Mapping[int, Mapping[str, Any]],
    found: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """The reconciliation «заявлено ↔ найдено» for a transition (``permit.py:167-219``).

    ``permits_b`` is ``[{"page", "rows"}]`` of the newer version; ``stamps_b`` maps its page number to the stamp;
    ``found`` is one entry for each pair with a newer page: ``{"key", "b_page", "status", "title"}``. Each entry of the
    four lists names the ``keys`` of the pairs it concerns."""
    rows = [r | {"page": p["page"]} for p in permits_b for r in p["rows"] if r["izm"] > izm_a]
    carriers = {p["page"] for p in permits_b}
    declared: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    all_sheets = False
    unparsed: list[dict[str, Any]] = []
    for r in rows:
        for ref in r["refs"]:
            if ref["set"] == "all":
                all_sheets = True
            elif ref["set"] == "unparsed":
                unparsed.append({"izm": r["izm"], "sheet": ref["sheet"], "text": r["text"]})
            else:
                declared[(ref["set"], ref["sheet"])].append(r)
    by_ref: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for f in found:
        page = f.get("b_page")
        ref = sheet_ref(stamps_b.get(page)) if page else None
        if ref:
            by_ref[(ref["set"], ref["sheet"])].append(f)
    out: dict[str, Any] = {
        "izm_a": izm_a, "izm_new": sorted({r["izm"] for r in rows}), "rows": rows, "unparsed_refs": unparsed,
        "declared_no_diff": [], "diff_not_declared": [], "declared_and_found": [], "needs_review": [],
        "all_sheets_declared": all_sheets,
    }
    for key, rws in sorted(declared.items(), key=lambda kv: (kv[0][0], int(re.sub(r"\D", "", kv[0][1]) or 0))):
        items = by_ref.get(key, [])
        if not items and key[0] == "main":
            # The original takes any sheet titled «Спецификация…» for the specification set (``permit.py:157``); a
            # permit that numbers it in the main set ("7") would then name a sheet the version does not have. If the
            # specification set has that number exactly once, it is the sheet the permit means.
            alternative = by_ref.get(("СО", key[1]), [])
            items = alternative if len(alternative) == 1 else []
        entry = {
            "ref": ref_label({"set": key[0], "sheet": key[1]}), "izm": sorted({r["izm"] for r in rws}),
            "declared": [r["text"] for r in rws], "statuses": [f["status"] for f in items],
            "titles": [f.get("title") for f in items], "keys": [f["key"] for f in items],
        }
        if len(items) > 1:
            out["needs_review"].append(entry | {"reason": "duplicate_sheet_number"})
        elif not items:
            out["needs_review"].append(entry | {"reason": "sheet_not_in_version"})
        elif items[0]["status"] in ("different", "added", "removed"):
            out["declared_and_found"].append(entry)
        elif items[0]["status"] == "needs_review":
            out["needs_review"].append(entry | {"reason": "sheet_needs_review"})
        else:
            out["declared_no_diff"].append(entry)
    if not all_sheets:
        for key, items in sorted(by_ref.items()):
            if key in declared:
                continue
            for f in items:
                if f["b_page"] in carriers:
                    continue  # the sheet that carries the permit changes with every revision: the new row is its declaration
                if f["status"] in ("different", "added", "removed"):
                    out["diff_not_declared"].append({
                        "ref": ref_label({"set": key[0], "sheet": key[1]}), "status": f["status"],
                        "title": f.get("title"), "keys": [f["key"]],
                    })
    return out


def pair_permits(reconciled: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """The ``ComparisonPermit`` of each pair the reconciliation concerns, keyed by the pair's ``key``.

    A pair named by several entries (it cannot be: a sheet number is one entry) keeps the first. A declared entry for a
    sheet that is not in the version names no pair and so is not attached (its text stays in the reconciliation)."""
    out: dict[str, dict[str, Any]] = {}
    for state in ("declared_and_found", "declared_no_diff", "needs_review", "diff_not_declared"):
        for entry in reconciled[state]:
            texts = [
                {"text": " ".join(str(t).split())[:MAX_TEXT], "state": state}
                for t in entry.get("declared", ())
                if " ".join(str(t).split())
            ][:MAX_ITEMS]
            for key in entry["keys"]:
                out.setdefault(key, {"state": state, "items": texts})
    return out
