"""The order-independent comparison of two whole specifications that passed the program's check (pure Python; `CMP-VC-SPEC-01`, part B).

A port of ``version_comparison/specification_compare.py`` of the original (PDF-proverka at ``23f379fd``; ``:N`` below are that file's
lines) over the rows :func:`~.check.check_extraction` confirmed. Its principle (``docs/whole_specification_comparison.md`` lines
36-40): **nothing about the order of the rows, the page a row is on, or how close two quantities are decides which row is which.**

1. identical records cancel one against one, keeping the multiplicity, first with the position number and then without it
   (``:340-352``);
2. what is left is matched by an **unambiguous identity** inside the same section and parent -- the code, the mark with the name, the
   mark, the leading model of the mark, the name with the family and ratings of the model, the name -- the strongest tier that finds
   a pair that is the only candidate on both sides first; a name match with two different codes is a substitution and is not paired
   (``:75-107``, ``:192-226``), first with the parent and then without it (``:356-365``);
3. a position all of whose fields agree and that is the only one such among the rest of each side is *moved* to another section
   (``:367-385``);
4. what still shares an identity with something on the other side forms a **group the program does not decide** (``:397-426``): it is
   reported ``unclear`` and neither added nor removed;
5. what has no counterpart is ``added`` or ``removed``, **published only when both sides are complete** (``:619-641``).

A renamed section title is found by the order, the likeness of the title and the content of the sections that exist on one side
only (``:233-285``) and its positions are compared as the same section.

Not ported: the groups an unresolved structural markup leaves out of the comparison (``:292-313``): the markup mode of the original is
not built here (the packet's structure is the table's own), so every row is either compared or the whole side is incomplete.

Imports the standard library only.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict, deque
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Any, Final

__all__ = ["FIELDS", "FIELD_LABELS", "KIND_ORDER", "SUBSTANTIVE_FIELDS", "changes_of", "compare", "row_item"]

FIELDS: Final[tuple[str, ...]] = ("pos", "name", "mark", "code", "supplier", "unit", "quantity", "mass", "note")
SUBSTANTIVE_FIELDS: Final[tuple[str, ...]] = tuple(f for f in FIELDS if f != "pos")
NUMERIC_FIELDS: Final[frozenset[str]] = frozenset({"quantity", "mass"})
FIELD_LABELS: Final[dict[str, str]] = {
    "pos": "Позиция", "name": "Наименование", "mark": "Марка", "code": "Код", "supplier": "Поставщик", "unit": "Ед. изм.",
    "quantity": "Количество", "mass": "Масса", "note": "Примечание",
}
KIND_ORDER: Final[dict[str, int]] = {"changed": 0, "removed": 1, "added": 2, "unclear": 3, "renumbered": 4, "moved": 5}
_UNCLEAR_TEXT: Final[str] = "Несколько строк имеют общие признаки; автоматическое соответствие неоднозначно."
_TEXT_MAX: Final[int] = 600


def _text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(unicodedata.normalize("NFKC", str(value)).split()).casefold()


def _number(value: Any) -> str:
    """A canonical decimal spelling; empty stays distinct from numeric zero (``:36-52``)."""
    raw = _text(value)
    if not raw:
        return ""
    candidate = raw.replace(" ", "").replace(",", ".")
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", candidate):
        return raw
    try:
        number = Decimal(candidate)
    except InvalidOperation:
        return raw
    if number == 0:
        return "0"
    rendered = format(number, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _value(row: dict[str, Any], field: str) -> str:
    raw = (row.get("fields") or {}).get(field, "")
    if field=="unit":
        from .units import unit_identity
        return _text(unit_identity(raw))
    return _number(raw) if field in NUMERIC_FIELDS else _text(raw)


def _context_value(value: str) -> str:
    if value.strip().startswith("|") and value.strip().endswith("|"):
        return " ".join(cell.strip() for cell in value.strip().strip("|").split("|") if cell.strip())
    return value


def _context(row: dict[str, Any]) -> tuple[str, str]:
    return _text(_context_value(row.get("section", ""))), _text(_context_value(row.get("parent", "")))


def _substantive(row: dict[str, Any]) -> tuple[Any, ...]:
    return (*_context(row), *(_value(row, f) for f in SUBSTANTIVE_FIELDS))


def _identities(row: dict[str, Any], with_parent: bool = True) -> tuple[tuple[Any, ...], ...]:
    """The keys by which a row may be the same position as another (``:75-107``). Without the parent: the same position in the same
    section where the parent group is marked differently in the two versions."""
    section, parent = _context(row)
    if not with_parent:
        parent = ""
    code, mark, name = _value(row, "code"), _value(row, "mark"), _value(row, "name")
    keys: list[tuple[Any, ...]] = []
    if code:
        keys.append(("code", section, parent, code))
    if mark and name:
        keys.append(("mark_name", section, parent, mark, name))
    if mark:
        # A complete leading model designation may survive an expanded description (AB-1 differs from AB-10).
        model = mark.split()[0]
        if re.search(r"[a-zа-я]", model) and re.search(r"\d", model) and re.search(r"[-/]", model):
            keys.append(("mark", section, parent, mark))
            keys.append(("mark_model", section, parent, model))
            family = re.match(r"^[^\d]+", model)
            numbers = tuple(re.findall(r"\d+(?:[.,]\d+)?", model))
            if name and family and numbers:
                keys.append(("name_model_ratings", section, parent, name, family.group().rstrip("-/"), numbers))
    if name:
        keys.append(("name", section, parent, name))
    return tuple(keys)


def _source_order(row: dict[str, Any]) -> tuple[Any, ...]:
    refs = row.get("sources") or []
    return tuple(sorted(
        (_text(r.get("document", "")), r.get("page", 0) or 0, _text(r.get("sheet", "")), _text(r.get("block_id", "")),
         r.get("line_start", 0), r.get("line_end", 0), _text(r.get("quote", "")))
        for r in refs
    ))


def _stable(row: dict[str, Any]) -> tuple[Any, ...]:
    return (*_substantive(row), _text(_value(row, "pos")), _source_order(row))


def _row_copy(row: dict[str, Any]) -> dict[str, Any]:
    fields = row.get("fields") or {}
    return {
        "id": str(row.get("id", "")), "section": str(row.get("section", "")), "section_shown": "", "parent": str(row.get("parent", "")),
        "fields": {f: str(fields.get(f, "") or "") for f in FIELDS}, "sources": [dict(s) for s in (row.get("sources") or [])],
    }


def _pages(row: dict[str, Any]) -> tuple[str, ...]:
    return tuple(sorted({str(s.get("page", "")) for s in row.get("sources", [])}))


def _pair(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    changes = [
        {"field": f, "old": old["fields"][f], "new": new["fields"][f]} for f in SUBSTANTIVE_FIELDS if _value(old, f) != _value(new, f)
    ]
    return {
        "old": old, "new": new, "field_changes": changes, "section_changed": _context(old)[0] != _context(new)[0],
        "renumbered": _value(old, "pos") != _value(new, "pos"), "relocated": _pages(old) != _pages(new), "unchanged": not changes,
    }


def _candidate_graph(old_rows: list[dict[str, Any]], new_rows: list[dict[str, Any]]) -> dict[int, set[int]]:
    new_by_key: dict[tuple[Any, ...], set[int]] = defaultdict(set)
    for j, row in enumerate(new_rows):
        for key in _identities(row):
            new_by_key[key].add(j)
    graph: dict[int, set[int]] = {}
    for i, row in enumerate(old_rows):
        candidates: set[int] = set()
        for key in _identities(row):
            candidates.update(new_by_key.get(key, ()))
        if not _identities(row):
            context = _context(row)
            candidates.update(j for j, other in enumerate(new_rows) if not _identities(other) and _context(other) == context)
        if candidates:
            graph[i] = candidates
    return graph


def _unique_identity_pairs(
    old_rows: list[dict[str, Any]], new_rows: list[dict[str, Any]], old_left: set[int], new_left: set[int], with_parent: bool = True
) -> list[tuple[int, int]]:
    for priority in ("code", "mark_name", "mark", "mark_model", "name_model_ratings", "name"):
        old_groups: dict[tuple[Any, ...], list[int]] = defaultdict(list)
        new_groups: dict[tuple[Any, ...], list[int]] = defaultdict(list)
        for i in old_left:
            for key in _identities(old_rows[i], with_parent):
                if key[0] == priority:
                    old_groups[key].append(i)
        for j in new_left:
            for key in _identities(new_rows[j], with_parent):
                if key[0] == priority:
                    new_groups[key].append(j)
        proposals: list[tuple[int, int]] = []
        for key, old_ids in old_groups.items():
            new_ids = new_groups.get(key, [])
            if len(old_ids) == len(new_ids) == 1:
                i, j = old_ids[0], new_ids[0]
                old_code, new_code = _value(old_rows[i], "code"), _value(new_rows[j], "code")
                if old_code and new_code and old_code != new_code:
                    continue  # a name match with two different codes may be a model substitution
                proposals.append((i, j))
        by_old: dict[int, set[int]] = defaultdict(set)
        by_new: dict[int, set[int]] = defaultdict(set)
        for i, j in proposals:
            by_old[i].add(j)
            by_new[j].add(i)
        accepted = [(i, j) for i, js in by_old.items() if len(js) == 1 for j in js if len(by_new[j]) == 1]
        if accepted:
            return accepted
    return []


def _section_key(row: dict[str, Any]) -> str:
    return _text(_context_value(row.get("section", "")))


def _align_sections(old_rows: list[dict[str, Any]], new_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Renamed section titles (``:233-285``): the sections that exist on one side only are aligned by order, title likeness and
    content."""
    def order(rows: list[dict[str, Any]]) -> tuple[list[str], dict[str, Counter], dict[str, str]]:
        seen: set[str] = set()
        out: list[str] = []
        content: dict[str, Counter] = defaultdict(Counter)
        title: dict[str, str] = {}
        for r in rows:
            k = _section_key(r)
            if k not in seen:
                seen.add(k)
                out.append(k)
                title[k] = r.get("section", "")
            content[k][(_value(r, "name"), _value(r, "mark"))] += 1
        return out, content, title

    o_order, o_content, o_title = order(old_rows)
    n_order, n_content, n_title = order(new_rows)
    o_only = [k for k in o_order if k and k not in set(n_order)]
    n_only = [k for k in n_order if k and k not in set(o_order)]
    if not o_only or not n_only:
        return []

    def score(a: str, b: str) -> float:
        ca, cb = o_content[a], n_content[b]
        inter, union = sum((ca & cb).values()), sum((ca | cb).values())
        jac = inter / union if union else 0.0
        title = SequenceMatcher(None, a, b).ratio()
        size = min(sum(ca.values()), sum(cb.values()))
        ok = (jac >= 0.6 and title >= 0.5 and size >= 2) or (jac >= 0.85 and size >= 3)
        return 0.4 * title + 0.6 * jac if ok else 0.0

    n, m = len(o_only), len(n_only)
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    move = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            s = score(o_only[i - 1], n_only[j - 1])
            options = [(best[i - 1][j], 1), (best[i][j - 1], 2)]
            if s:
                options.append((best[i - 1][j - 1] + s, 3))
            best[i][j], move[i][j] = max(options)
    renames: list[dict[str, Any]] = []
    i, j = n, m
    while i and j:
        if move[i][j] == 3:
            renames.append({"old": o_title[o_only[i - 1]], "new": n_title[n_only[j - 1]], "old_key": o_only[i - 1], "new_key": n_only[j - 1]})
            i, j = i - 1, j - 1
        elif move[i][j] == 1:
            i -= 1
        else:
            j -= 1
    return list(reversed(renames))


def compare(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Compare two checked sides: ``{"complete", "pairs", "added", "removed", "unresolved", "section_renames", "counts"}``.

    A side is ``{"complete": bool, "rows": [...]}`` (:func:`~.check.check_extraction`'s answer). A side that is not complete has no rows,
    so ``complete`` is false and nothing is added, removed or claimed unchanged."""
    old_rows = [_row_copy(r) for r in old.get("rows", [])]
    new_rows = [_row_copy(r) for r in new.get("rows", [])]
    renames = _align_sections(old_rows, new_rows)
    to_old = {r["new_key"]: r["old"] for r in renames}
    for row in new_rows:
        key = _section_key(row)
        if key in to_old:
            row["section_shown"], row["section"] = row["section"], to_old[key]
    old_sorted, new_sorted = sorted(old_rows, key=_stable), sorted(new_rows, key=_stable)
    old_left, new_left = set(range(len(old_sorted))), set(range(len(new_sorted)))
    pairs: list[dict[str, Any]] = []

    for include_position in (True, False):  # identical records cancel, keeping the multiplicity (``:340-352``)
        def exact_key(row: dict[str, Any]) -> tuple[Any, ...]:
            return (*_substantive(row), _value(row, "pos")) if include_position else _substantive(row)

        buckets: dict[tuple[Any, ...], deque[int]] = defaultdict(deque)
        for j in sorted(new_left):
            buckets[exact_key(new_sorted[j])].append(j)
        for i in sorted(old_left):
            bucket = buckets.get(exact_key(old_sorted[i]))
            if bucket:
                j = bucket.popleft()
                old_left.remove(i)
                new_left.remove(j)
                pairs.append(_pair(old_sorted[i], new_sorted[j]))

    for with_parent in (True, False):  # a stable identity, independent of the row order (``:354-365``)
        while old_left and new_left:
            matches = _unique_identity_pairs(old_sorted, new_sorted, old_left, new_left, with_parent)
            if not matches:
                break
            for i, j in matches:
                if i in old_left and j in new_left:
                    old_left.remove(i)
                    new_left.remove(j)
                    pairs.append(_pair(old_sorted[i], new_sorted[j]))

    def fields_key(row: dict[str, Any]) -> tuple[Any, ...]:
        return tuple(_value(row, f) for f in SUBSTANTIVE_FIELDS)

    old_by: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    new_by: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    for i in old_left:
        if any(fields_key(old_sorted[i])):
            old_by[fields_key(old_sorted[i])].append(i)
    for j in new_left:
        if any(fields_key(new_sorted[j])):
            new_by[fields_key(new_sorted[j])].append(j)
    for key, ids in sorted(old_by.items(), key=lambda kv: kv[1]):  # moved between sections: the only one of its kind on each side
        if len(ids) == 1 and len(new_by.get(key, [])) == 1:
            i, j = ids[0], new_by[key][0]
            old_left.remove(i)
            new_left.remove(j)
            pairs.append(_pair(old_sorted[i], new_sorted[j]))

    remaining_old, remaining_new = sorted(old_left), sorted(new_left)
    rem_old = [old_sorted[i] for i in remaining_old]
    rem_new = [new_sorted[j] for j in remaining_new]
    graph = _candidate_graph(rem_old, rem_new)
    reverse: dict[int, set[int]] = defaultdict(set)
    for i, js in graph.items():
        for j in js:
            reverse[j].add(i)
    unresolved: list[dict[str, Any]] = []
    visited_old: set[int] = set()
    visited_new: set[int] = set()
    for start in sorted(graph):  # connected candidates are unresolved as a whole; never pick the nearest quantity (``:397-426``)
        if start in visited_old:
            continue
        queue: deque[tuple[str, int]] = deque([("old", start)])
        comp_old: set[int] = set()
        comp_new: set[int] = set()
        while queue:
            side, idx = queue.popleft()
            if side == "old":
                if idx in comp_old:
                    continue
                comp_old.add(idx)
                queue.extend(("new", j) for j in graph.get(idx, ()))
            else:
                if idx in comp_new:
                    continue
                comp_new.add(idx)
                queue.extend(("old", i) for i in reverse.get(idx, ()))
        visited_old.update(comp_old)
        visited_new.update(comp_new)
        unresolved.append({"old_rows": [rem_old[i] for i in sorted(comp_old)], "new_rows": [rem_new[j] for j in sorted(comp_new)], "reason": _UNCLEAR_TEXT})
    added = [rem_new[j] for j in range(len(rem_new)) if j not in visited_new]
    removed = [rem_old[i] for i in range(len(rem_old)) if i not in visited_old]
    complete = bool(old.get("complete")) and bool(new.get("complete"))
    pairs.sort(key=lambda p: (_stable(p["old"]), _stable(p["new"])))
    unresolved.sort(key=lambda g: (tuple(_stable(r) for r in g["old_rows"]), tuple(_stable(r) for r in g["new_rows"])))
    added.sort(key=_stable)
    removed.sort(key=_stable)
    counts = {
        "old_rows": len(old_sorted), "new_rows": len(new_sorted), "paired": len(pairs),
        "unchanged": sum(p["unchanged"] for p in pairs), "changed": sum(bool(p["field_changes"]) for p in pairs),
        "renumbered": sum(p["renumbered"] for p in pairs), "relocated": sum(p["relocated"] for p in pairs),
        "added": len(added), "removed": len(removed),
        "unresolved_old": sum(len(g["old_rows"]) for g in unresolved), "unresolved_new": sum(len(g["new_rows"]) for g in unresolved),
    }
    return {
        "complete": complete, "pairs": pairs, "added": added, "removed": removed, "unresolved": unresolved,
        "section_renames": [{"old": r["old"], "new": r["new"]} for r in renames], "counts": counts,
    }


def _md(value: Any) -> str:
    return str(value if value is not None else "").replace("\r", " ").replace("\n", " ")


def row_item(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """A row as an item of :mod:`.views` (the nine fields flat, the section, the parent, the first page)."""
    if row is None:
        return None
    fields = row["fields"]
    pages = sorted({int(s["page"]) for s in row.get("sources", []) if s.get("page") not in (None, "")})
    item: dict[str, Any] = {f: fields.get(f, "") for f in FIELDS}
    item.update({
        "section": row.get("section_shown") or row.get("section", ""), "parent": row.get("parent", ""),
        "parent_name": row.get("parent", ""), "page": pages[0] if pages else 0, "pages": pages, "ambiguous": False,
    })
    return item


def _label(row: dict[str, Any], *, full: bool = False, include_position: bool = True) -> str:
    fields = row.get("fields") or {}
    parts = []
    for key, label in (("pos", "Поз."), ("name", "Наименование"), ("mark", "Марка")):
        if key == "pos" and not include_position:
            continue
        if fields.get(key):
            parts.append(f"{label} {_md(fields[key])}")
    for key, label in (("section", "раздел"), ("parent", "группа")):
        value = _context_value(row.get("section_shown") or row.get("section", "") if key == "section" else row.get(key, ""))
        if value:
            parts.append(f"{label} {_md(value)}")
    if full:
        for key in ("code", "supplier", "unit", "quantity", "mass", "note"):
            value = fields.get(key, "")
            if key == "unit" and fields.get("quantity"):
                continue
            if value:
                if key == "quantity" and fields.get("unit"):
                    parts.append(f"{FIELD_LABELS[key]} {_md(value)} {_md(fields['unit'])}")
                else:
                    parts.append(f"{FIELD_LABELS[key]} {_md(value)}")
    return "; ".join(parts) or "Строка спецификации"


def _clip(text: str) -> str:
    return text if len(text) <= _TEXT_MAX else text[: _TEXT_MAX - 1] + "…"


def changes_of(result: dict[str, Any]) -> list[dict[str, Any]]:
    """The changes of a comparison as the contract lists them: ``{"id", "kind", "label", "fields", "a", "b", "text"}`` with ``a`` and
    ``b`` the positions before and after (``None`` for an addition or a removal), in the order changed, removed, added, unclear,
    renumbered, moved. Additions and removals are published **only from a complete comparison** (``:619-641``); a pair of unchanged
    content that only changed page is no change (``docs/whole_specification_comparison.md`` lines 46-48)."""
    entries: list[dict[str, Any]] = []
    for pair in result["pairs"]:
        old, new = pair["old"], pair["new"]
        fields = pair["field_changes"]
        if fields:
            diff = {c["field"]: [c["old"], c["new"]] for c in fields}
            if pair["renumbered"]:
                diff = {"pos": [old["fields"].get("pos", ""), new["fields"].get("pos", "")], **diff}
            parts = [f"{FIELD_LABELS[f]}: {_md(was) or 'не указано'} → {_md(now) or 'не указано'}" for f, (was, now) in diff.items()]
            entries.append({"kind": "changed", "fields": diff, "a": old, "b": new,
                            "text": f"{_label(new, include_position='pos' not in diff)}; " + "; ".join(parts)})
        elif pair["section_changed"]:
            entries.append({"kind": "moved", "fields": {}, "a": old, "b": new, "text": (
                f"Перенесено без изменения: раздел «{_md(old.get('section')) or '—'}» → «{_md(new.get('section_shown') or new.get('section')) or '—'}»; "
                + _label(new, full=True))})
        elif pair["renumbered"]:
            was, now = old["fields"].get("pos", ""), new["fields"].get("pos", "")
            entries.append({"kind": "renumbered", "fields": {"pos": [was, now]}, "a": old, "b": new,
                            "text": f"Поз. {_md(was) or '—'} → {_md(now) or '—'}; {_label(new, include_position=False)}"})
    for rename in result["section_renames"]:
        entries.append({"kind": "changed", "fields": {"section": [rename["old"], rename["new"]]}, "a": None, "b": None, "section_title": True,
                        "text": f"Заголовок группы изменён: «{_md(_context_value(rename['old']))}» → «{_md(_context_value(rename['new']))}»"})
    if result["complete"]:
        for row in result["added"]:
            entries.append({"kind": "added", "fields": {}, "a": None, "b": row, "text": f"Добавлено: не было → {_label(row, full=True)}"})
        for row in result["removed"]:
            entries.append({"kind": "removed", "fields": {}, "a": row, "b": None, "text": f"Удалено: {_label(row, full=True)} → отсутствует"})
    for group in result["unresolved"]:
        a = group["old_rows"][0] if group["old_rows"] else None
        b = group["new_rows"][0] if group["new_rows"] else None
        entries.append({"kind": "unclear", "fields": {}, "a": a, "b": b, "text": group["reason"]})
    entries.sort(key=lambda e: (KIND_ORDER[e["kind"]], _stable(e["b"] or e["a"]) if (e["b"] or e["a"]) else ()))
    out: list[dict[str, Any]] = []
    for number, entry in enumerate(entries, 1):
        label_row = entry["b"] or entry["a"]
        out.append({
            "id": f"s{number}", "kind": entry["kind"], "label": _label(label_row) if label_row else entry["text"],
            "fields": entry["fields"], "a": row_item(entry["a"]), "b": row_item(entry["b"]), "text": _clip(entry["text"]),
        })
    return out
