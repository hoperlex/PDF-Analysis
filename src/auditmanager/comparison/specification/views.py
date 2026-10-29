"""The contract-shaped dictionaries of positions and changes (`CMP-VC-SPEC-01`).

Pure: no database. The adapter in the composition root validates them with the generated models. A value is the text of the sheet;
the only thing done to it is a cut at the contract's bound (with an ellipsis, so a cut value is visible as cut) because the contract
cannot carry a longer one. An empty optional value is omitted, never sent as an empty string or ``null``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from auditmanager.comparison.specification import diff as diff_module
from auditmanager.comparison.specification import table

__all__ = ["MAX_LISTED", "change_dict", "clip", "page_view", "pair_view", "position_dict", "totals_dict"]

#: ``maxItems`` of the lists of positions and changes in ``ComparisonSpecPage`` and ``ComparisonSheetPairSpecPositions``.
MAX_LISTED: Final[int] = 2000

#: ``(contract member, item key, bound)`` of a ``ComparisonSpecPosition`` (``name`` is required, the others are omitted when empty).
_VALUES: Final[tuple[tuple[str, str, int], ...]] = (
    ("name", "name", 400), ("pos", "pos", 32), ("mark", "mark", 200), ("code", "code", 120), ("supplier", "supplier", 200),
    ("unit", "unit", 32), ("quantity", "quantity", 64), ("mass", "mass", 64), ("note", "note", 400),
)
_SECTION_MAX: Final[int] = 200
_PARENT_MAX: Final[int] = 400
_FIELD_VALUE_MAX: Final[int] = 400


def clip(text: str, bound: int) -> str:
    """The text, cut at ``bound`` characters with an ellipsis when it is longer."""
    return text if len(text) <= bound else text[: bound - 1] + "…"


def position_dict(item: Mapping[str, Any], *, page_ref: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """A ``ComparisonSpecPosition`` from an item of :func:`~.table.assemble`; ``page_ref`` is the contract's page reference of the
    page the item (its first row) is on."""
    out: dict[str, Any] = {}
    for member, key, bound in _VALUES:
        value = " ".join(str(item.get(key) or "").split())
        if value or member == "name":
            out[member] = clip(value, bound)
    if item.get("section"):
        out["section"] = clip(str(item["section"]), _SECTION_MAX)
    if item.get("parent") and item.get("parent_name"):
        out["parent"] = clip(" ".join(str(item["parent_name"]).split()), _PARENT_MAX)
    if item.get("ambiguous"):
        out["ambiguous"] = True
    if page_ref is not None:
        out["page"] = dict(page_ref)
    return out


def totals_dict(changes: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return diff_module.totals(list(changes))


def change_dict(change: Mapping[str, Any], *, refs: Mapping[str, Mapping[int, Mapping[str, Any]]] | None = None) -> dict[str, Any]:
    """A ``ComparisonSpecChange``: the position before and after, the fields that differ, and the sentence.

    ``refs`` is ``{"a": {page_number: page_ref}, "b": {...}}``, the page references of each side."""
    refs = refs or {}

    def side(key: str) -> dict[str, Any] | None:
        item = change.get(key)
        if item is None:
            return None
        pages = refs.get(key, {})
        return position_dict(item, page_ref=pages.get(int(item["page"])))

    out: dict[str, Any] = {
        "change_id": change["id"],
        "kind": change["kind"],
        "fields": [
            {"field": field, "was": clip(str(was), _FIELD_VALUE_MAX), "now": clip(str(now), _FIELD_VALUE_MAX)}
            for field, (was, now) in list(change["fields"].items())[:9]
        ],
        "text": change["text"],
    }
    old, new = side("a"), side("b")
    if old is not None:
        out["old"] = old
    if new is not None:
        out["new"] = new
    return out


def page_view(
    page_profile_id: str, *, is_specification: bool, items: Sequence[Mapping[str, Any]], refs: Mapping[int, Mapping[str, Any]]
) -> dict[str, Any]:
    """A ``ComparisonSpecPage``: the positions the parser reads from the page."""
    positions = [position_dict(item, page_ref=refs.get(int(item["page"]))) for item in items[:MAX_LISTED]]
    return {
        "page_profile_id": page_profile_id,
        "is_specification": is_specification,
        "spec_version": table.SPEC_VERSION,
        "positions": positions,
        "ambiguous_rows": sum(1 for item in items if item.get("ambiguous")),
    }


def pair_view(
    sheet_pair_id: str, *, is_specification: bool, changes: Sequence[Mapping[str, Any]],
    refs: Mapping[str, Mapping[int, Mapping[str, Any]]],
) -> dict[str, Any]:
    """A ``ComparisonSheetPairSpecPositions``."""
    return {
        "sheet_pair_id": sheet_pair_id,
        "is_specification": is_specification,
        "totals": totals_dict(changes),
        "changes": [change_dict(c, refs=refs) for c in changes[:MAX_LISTED]],
    }
