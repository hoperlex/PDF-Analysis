"""The order-independent comparison of two streams of positions (pure Python).

`CMP-VC-SPEC-01`. A port of ``spec.compare`` of the original (PDF-proverka at commit ``23f379fd``, ``version_comparison/spec.py``;
``spec.py:N`` below is that file's line N). A position of A is matched to a position of B by the key «name of the parent + name +
mark» (``:405-407``), **never by its place**: a position that moves to another page or another place in the list is not a change
(``:19-20``), and one that moves to another section is reported as ``moved`` (a statement, not a change). Three passes, in the
original's order:

1. the same key; inside a key the same section and note first, then the same section, then the order (``:443-458``);
2. what is left: the same unit and the same kind (a position or a sub-row), the same mark with a name that is at least 0.8 alike,
   or the same name with a mark that is at least 0.8 alike (``:459-482``) -- a renamed position is *changed*, not *removed + added*;
3. what is left: the same name, unit and section, by order -- a replaced mark (``:483-491``).

A pair is ``changed`` when a compared field differs (quantities are compared as numbers within ``1e-9``, ``:417-422``; every other
field by :func:`~.table.norm`), ``renumbered`` when only the position number differs (``:504-508``), ``unclear`` when a side was
flagged ambiguous and nothing differs (``:513-516``), ``moved`` when nothing differs and the section does, and otherwise the same.
What is left unmatched is ``removed`` (A) or ``added`` (B). The order of the list is the original's (``:529``), with ``moved``
last. A side that is not read completely is not compared here: the caller decides (part B refuses to publish an addition or a
removal from an incomplete side).

Unlike the original the passes are indexed (by mark and by name), so a specification of thousands of rows is not quadratic; the
matches are those of the original's loops (the same candidates in the same order).

This module imports the standard library and its sibling :mod:`.table` only: the engine's child program loads the package by path
as ``_amc_spec`` and both modules with it.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from difflib import SequenceMatcher
from typing import Any, Final

from . import table

__all__ = ["KIND_ORDER", "MIN_SIMILARITY", "compare", "page_changes", "render_text", "totals"]

#: ``spec.py:479``.
MIN_SIMILARITY: Final[float] = 0.8
#: ``spec.py:529`` and ``moved`` after the original's last.
KIND_ORDER: Final[dict[str, int]] = {"changed": 0, "removed": 1, "added": 2, "unclear": 3, "renumbered": 4, "moved": 5}
_TEXT_MAX: Final[int] = 600


def _last_section(item: dict[str, Any]) -> str:
    return table.norm((item.get("section") or "").split(" / ")[-1])


def _key(item: dict[str, Any]) -> tuple[str, str, str]:
    mark = item.get("mark") or item.get("parent_mark") or ""
    return (table.norm(item.get("parent_name", "")), table.norm(item["name"]), table.norm(mark))


def _effective(item: dict[str, Any], field: str) -> str:
    """The value of a field; a sub-row that has no mark, code or supplier takes its parent's (``spec.py:410-414``)."""
    value = item.get(field, "")
    if not value and field in ("mark", "code", "supplier") and item.get("parent"):
        value = item.get("parent_" + field, "")
    return " ".join(str(value).split())


def _same_value(field: str, a: str, b: str) -> bool:
    if field=="unit":
        from .units import unit_identity
        return table.norm(unit_identity(a))==table.norm(unit_identity(b))
    if field == "quantity":
        qa, qb = table.quantity(a), table.quantity(b)
        if qa is not None and qb is not None:
            return abs(qa - qb) < 1e-9
    return table.norm(a) == table.norm(b)


def _label(item: dict[str, Any]) -> str:
    """What names a position in a sentence (``spec.py:425-432``)."""
    name = " ".join(item["name"].split())
    mark = _effective(item, "mark")
    if item.get("parent"):
        base = " ".join(item.get("parent_name", "").split())
        return f"{mark} {name}".strip() if mark else f"{base[:60]} {name}".strip()
    return f"{name[:90]}{' — ' + mark if mark else ''}"


def _pages(item: dict[str, Any]) -> list[int]:
    return sorted({int(r[0]) for r in item["rows"]})


class _Keys:
    """The normalised values of an item, computed once (``table.norm`` is a regular expression and a translation; the passes ask
    for the same values of the same items again and again)."""

    __slots__ = ("_cache",)

    def __init__(self) -> None:
        self._cache: dict[int, tuple[str, str, str, str, str, bool, str, str]] = {}

    def of(self, item: dict[str, Any]) -> tuple[str, str, str, str, str, bool, str, str]:
        """``(name, effective mark, unit, parent name, last section, is a sub-row, own mark, note)``, all normalised."""
        found = self._cache.get(id(item))
        if found is None:
            found = (
                table.norm(item["name"]), table.norm(_effective(item, "mark")), table.norm(item["unit"]),
                table.norm(item.get("parent_name", "")), _last_section(item), bool(item.get("parent")),
                table.norm(item.get("mark") or item.get("parent_mark") or ""), table.norm(_effective(item, "note")),
            )
            self._cache[id(item)] = found
        return found


def _pair_same_key(
    a_items: Sequence[dict[str, Any]], b_items: Sequence[dict[str, Any]], keys: _Keys
) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], list[dict[str, Any]], list[dict[str, Any]]]:
    """The first pass (``spec.py:443-458``)."""
    by_a: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    by_b: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in a_items:
        by_a[_key(item)].append(item)
    for item in b_items:
        by_b[_key(item)].append(item)
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    left_a: list[dict[str, Any]] = []
    left_b: list[dict[str, Any]] = []
    for key in list(by_a) + [k for k in by_b if k not in by_a]:
        rest_b = list(by_b.get(key, []))
        for ia in by_a.get(key, []):
            ka = keys.of(ia)
            same_section = [ib for ib in rest_b if keys.of(ib)[4] == ka[4]]
            candidates = [ib for ib in same_section if keys.of(ib)[7] == ka[7]] or same_section or rest_b
            if candidates:
                pairs.append((ia, candidates[0]))
                rest_b = [ib for ib in rest_b if ib is not candidates[0]]
            else:
                left_a.append(ia)
        left_b.extend(rest_b)
    return pairs, left_a, left_b


def _second_pass(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]], left_a: list[dict[str, Any]], left_b: list[dict[str, Any]], keys: _Keys
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """A renamed position, or the same position with another mark (``spec.py:459-482``); what is left of A and of B."""
    by_mark: dict[str, list[int]] = defaultdict(list)
    by_name: dict[str, list[int]] = defaultdict(list)
    for index, ib in enumerate(left_b):
        kb = keys.of(ib)
        by_mark[kb[1]].append(index)
        by_name[kb[0]].append(index)
    taken: set[int] = set()
    paired_a: set[int] = set()
    for ia in left_a:
        na, ma, unit_a, parent_a, _, is_sub_a, _, _ = keys.of(ia)
        candidates = set(by_name.get(na, ()))
        if ma:
            candidates |= set(by_mark.get(ma, ()))
        best, best_index, score = None, -1, 0.0
        for index in sorted(candidates):
            if index in taken:
                continue
            ib = left_b[index]
            nb, mb, unit_b, parent_b, _, is_sub_b, _, _ = keys.of(ib)
            if unit_a != unit_b or is_sub_a != is_sub_b:
                continue
            if is_sub_a and parent_a != parent_b and ma != mb:
                continue
            if ma and ma == mb:
                sc = SequenceMatcher(None, na, nb).ratio()
            elif na == nb:
                sc = SequenceMatcher(None, ma, mb).ratio() if (ma or mb) else 1.0
            else:
                continue
            if sc > score:
                best, best_index, score = ib, index, sc
        if best is not None and score >= MIN_SIMILARITY:
            pairs.append((ia, best))
            paired_a.add(id(ia))
            taken.add(best_index)
    return [ia for ia in left_a if id(ia) not in paired_a], [ib for index, ib in enumerate(left_b) if index not in taken]


def _third_pass(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]], left_a: list[dict[str, Any]], left_b: list[dict[str, Any]], keys: _Keys
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The same name, unit and sub-section: a replaced mark, by order (``spec.py:483-491``); what is left of A and of B."""
    pool: dict[tuple[str, str, str, bool], list[int]] = defaultdict(list)
    for index, ib in enumerate(left_b):
        kb = keys.of(ib)
        pool[(kb[0], kb[2], kb[4], kb[5])].append(index)
    cursor: dict[tuple[str, str, str, bool], int] = defaultdict(int)
    taken: set[int] = set()
    rest_a: list[dict[str, Any]] = []
    for ia in left_a:
        ka = keys.of(ia)
        slot = (ka[0], ka[2], ka[4], ka[5])
        indexes = pool.get(slot, [])
        if cursor[slot] < len(indexes):
            index = indexes[cursor[slot]]
            cursor[slot] += 1
            pairs.append((ia, left_b[index]))
            taken.add(index)
        else:
            rest_a.append(ia)
    return rest_a, [ib for index, ib in enumerate(left_b) if index not in taken]


def _entry(kind: str, a: dict[str, Any] | None, b: dict[str, Any] | None, fields: dict[str, list[str]]) -> dict[str, Any]:
    ref = b if b is not None else a
    assert ref is not None
    return {
        "kind": kind, "label": _label(ref), "section": ref["section"], "fields": fields, "a": a, "b": b,
        "a_pages": _pages(a) if a else [], "b_pages": _pages(b) if b else [],
        "ambiguous": bool((a or {}).get("ambiguous") or (b or {}).get("ambiguous")),
    }


def compare(a_items: Sequence[dict[str, Any]], b_items: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """The changes from the items of A to the items of B: ``{"changes": [...], "matched": n, "totals": {kind: count}}``.

    A change is ``{"id", "kind", "label", "section", "fields": {field: [was, now]}, "a", "b", "a_pages", "b_pages", "ambiguous",
    "text"}`` where ``a`` and ``b`` are the items on each side (``None`` for an addition or a removal)."""
    keys = _Keys()
    pairs, left_a, left_b = _pair_same_key(a_items, b_items, keys)
    left_a, left_b = _second_pass(pairs, left_a, left_b, keys)
    left_a, left_b = _third_pass(pairs, left_a, left_b, keys)
    changes: list[dict[str, Any]] = []
    for ia, ib in pairs:
        diff: dict[str, list[str]] = {}
        if table.norm(ia["name"]) != table.norm(ib["name"]):
            diff["name"] = [" ".join(ia["name"].split()), " ".join(ib["name"].split())]
        for field in table.COMPARE_FIELDS:
            va, vb = _effective(ia, field), _effective(ib, field)
            if not _same_value(field, va, vb):
                diff[field] = [va, vb]
        if diff and set(diff) == {"pos"}:
            changes.append(_entry("renumbered", ia, ib, diff))
        elif diff:
            changes.append(_entry("changed", ia, ib, diff))
        elif ia.get("ambiguous") or ib.get("ambiguous"):
            entry = _entry("unclear", ia, ib, {})
            entry["ambiguous"] = True
            changes.append(entry)
        elif _last_section(ia) != _last_section(ib):
            changes.append(_entry("moved", ia, ib, {}))
    for ia in left_a:
        changes.append(_entry("removed", ia, None, {f: [_effective(ia, f), ""] for f in ("quantity", "unit") if _effective(ia, f)}))
    for ib in left_b:
        changes.append(_entry("added", None, ib, {f: ["", _effective(ib, f)] for f in ("quantity", "unit") if _effective(ib, f)}))
    changes.sort(key=lambda c: (KIND_ORDER[c["kind"]], (c["b_pages"] or c["a_pages"] or [0])[0]))
    for number, change in enumerate(changes, 1):
        change["id"] = f"s{number}"
        change["text"] = render_text(change)
    return {"changes": changes, "matched": len(pairs), "totals": totals(changes)}


def totals(changes: Sequence[dict[str, Any]]) -> dict[str, int]:
    """«изменено / +добавлено / −удалено / ?неясно» and the two kinds that are not changes."""
    out = {kind: 0 for kind in KIND_ORDER}
    for change in changes:
        out[change["kind"]] += 1
    return out


def page_changes(changes: Sequence[dict[str, Any]], side: str, page: int) -> list[dict[str, Any]]:
    """The changes that touch a page of A (``side == "a"``) or of B (``spec.py:568-571``)."""
    key = "a_pages" if side == "a" else "b_pages"
    return [c for c in changes if page in c[key]]


def _quantity_text(item: dict[str, Any] | None) -> str:
    if not item:
        return ""
    quantity, unit = _effective(item, "quantity"), _effective(item, "unit")
    return f", {quantity} {unit}".rstrip() if quantity else ""


def render_text(change: dict[str, Any]) -> str:
    """The sentence of a change, in the words of the original's report (``specification_compare.py:588, 604, 630, 640``)."""
    kind, label = change["kind"], change["label"]
    if kind == "added":
        text = f"Добавлено: не было → «{label}»{_quantity_text(change['b'])}"
    elif kind == "removed":
        text = f"Удалено: «{label}»{_quantity_text(change['a'])} → отсутствует"
    elif kind == "unclear":
        text = f"Граница позиции неоднозначна: «{label}»; изменения не подтверждены."
    elif kind == "moved":
        text = (
            "Перенесено без изменения: раздел «"
            f"{(change['a'].get('section') or '').split(' / ')[-1] or '—'}» → «{(change['b'].get('section') or '').split(' / ')[-1] or '—'}»: «{label}»"
        )
    else:
        parts = [f"{table.FIELD_LABELS[f]}: {was or '—'} → {now or '—'}" for f, (was, now) in change["fields"].items()]
        text = f"«{label}»: " + "; ".join(parts)
    return text if len(text) <= _TEXT_MAX else text[: _TEXT_MAX - 1] + "…"
