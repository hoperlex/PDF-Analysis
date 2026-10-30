"""Nonbinding sheet hints from two sets of stored page passports."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from .passports import SheetPassport

__all__ = ["SheetSuggestion", "suggest_sheets"]

_WEIGHTS = (
    ("building", 4), ("floor", 4), ("level", 3),
    ("sheet_type", 2), ("sheet_number", 1),
)
_MAX_RIGHTS_PER_LEFT = 5


@dataclass(frozen=True, slots=True)
class SheetSuggestion:
    left_profile_id: str
    right_profile_id: str
    score: int
    confidence: str
    reasons: tuple[str, ...]


def _semantic_key(page: SheetPassport) -> tuple[str, ...] | None:
    if page.sheet_type is None:
        return None
    if page.building is not None and page.floor is not None:
        return (page.sheet_type, page.building, page.floor)
    if page.level is not None and page.level.startswith("-"):
        return (page.sheet_type, "underground", page.level)
    return None


def _score(left: SheetPassport, right: SheetPassport) -> tuple[int, tuple[str, ...]] | None:
    # Strong contradictory evidence excludes a suggestion even when all weak
    # fields, including sheet number or order, happen to agree.
    for field in ("building", "floor", "sheet_type"):
        a, b = getattr(left, field), getattr(right, field)
        if a is not None and b is not None and a != b:
            return None
    matched = tuple(
        field for field, _weight in _WEIGHTS
        if (a := getattr(left, field)) is not None and a == getattr(right, field)
    )
    score = sum(weight for field, weight in _WEIGHTS if field in matched)
    if left.page_number == right.page_number:
        score += 1
        matched += ("page_order",)
    return (score, matched) if score > 0 else None


def suggest_sheets(
    left: tuple[SheetPassport, ...], right: tuple[SheetPassport, ...],
) -> tuple[SheetSuggestion, ...]:
    """Return stable hints; exact semantic matches are high only when unique both ways."""
    left_keys = [_semantic_key(page) for page in left]
    right_keys = [_semantic_key(page) for page in right]
    left_counts = Counter(left_keys)
    right_counts = Counter(right_keys)
    indexes: dict[str, dict[object, list[int]]] = {
        field: defaultdict(list) for field, _weight in _WEIGHTS
    }
    indexes["page_number"] = defaultdict(list)
    for other_index, target in enumerate(right):
        if target.side != "right":
            raise ValueError("right input contains a left-side passport")
        for field in indexes:
            value = getattr(target, field)
            if value is not None:
                indexes[field][value].append(other_index)
    output: list[SheetSuggestion] = []
    for index, source in enumerate(left):
        if source.side != "left":
            raise ValueError("left input contains a right-side passport")
        candidates: list[SheetSuggestion] = []
        possible = set(indexes["page_number"].get(source.page_number, ()))
        for field, _weight in _WEIGHTS:
            value = getattr(source, field)
            if value is not None:
                possible.update(indexes[field].get(value, ()))
        for other_index in sorted(possible):
            target = right[other_index]
            scored = _score(source, target)
            if scored is None:
                continue
            score, reasons = scored
            key = left_keys[index]
            unique = (
                key is not None and key == right_keys[other_index]
                and left_counts[key] == 1 and right_counts[key] == 1
            )
            candidates.append(SheetSuggestion(
                source.profile_id, target.profile_id, score,
                "high" if unique else "review", reasons,
            ))
        candidates.sort(key=lambda item: (-item.score, item.right_profile_id))
        output.extend(candidates[:_MAX_RIGHTS_PER_LEFT])
    return tuple(sorted(
        output,
        key=lambda item: (-item.score, item.left_profile_id, item.right_profile_id),
    ))
