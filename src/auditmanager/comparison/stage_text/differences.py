"""Bounded raw TEXT deltas after proven exact exclusions, without a model call."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Mapping, Sequence

from .exact import ExactExclusion, SheetLink, prove_exact_exclusions
from .fragments import TextFragment

__all__ = ["RawDifference", "RawTextPass", "build_raw_differences"]

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_ROOM = re.compile(r"(?:^|\b)(?:помещение|комната|room)\s*(?:№\s*)?(\d+[а-яa-z]?)\b")
_MAX_LINKS = 32
_MAX_FRAGMENTS = 4_000
_MAX_CANDIDATES = 10_000
_MAX_FUZZY_CHARACTERS = 512
_SIMILARITY_THRESHOLD = 0.82
_AMBIGUITY_GAP = 0.02


@dataclass(frozen=True, slots=True)
class RawDifference:
    status: str  # changed, removed, added; matches sealed storage
    left_content_key: str | None
    right_content_key: str | None


@dataclass(frozen=True, slots=True)
class RawTextPass:
    exact_exclusions: tuple[ExactExclusion, ...]
    differences: tuple[RawDifference, ...]


def _token_overlap(left: str, right: str) -> float:
    a, b = set(left.split()), set(right.split())
    return len(a & b) / min(len(a), len(b)) if a and b else 0.0


def _score(left: TextFragment, right: TextFragment) -> float:
    a, b = left.normalised_text, right.normalised_text
    room_a, room_b = _ROOM.search(a), _ROOM.search(b)
    if room_a and room_b and room_a.group(1) != room_b.group(1):
        return 0.0
    if a == b:
        # An equal string withheld by exact proof may be duplicated or too far
        # away. A fuzzy pass must not promote it through a different door.
        return 0.0
    skeleton_a, skeleton_b = _NUMBER.sub("#", a), _NUMBER.sub("#", b)
    if skeleton_a == skeleton_b and "#" in skeleton_a and len(a) >= 8 and len(b) >= 8:
        return 0.97
    if (max(len(a), len(b)) < 24 or max(len(a), len(b)) > _MAX_FUZZY_CHARACTERS
            or _token_overlap(a, b) < 0.5):
        return 0.0
    ratio = SequenceMatcher(None, a, b, autojunk=False).ratio()
    return ratio if ratio >= _SIMILARITY_THRESHOLD else 0.0


def _unique_best(options: list[tuple[float, str]]) -> str | None:
    if not options:
        return None
    options.sort(key=lambda option: (-option[0], option[1]))
    if len(options) > 1 and options[0][0] - options[1][0] < _AMBIGUITY_GAP:
        return None
    return options[0][1]


def build_raw_differences(
    links: Sequence[SheetLink],
    fragments: Sequence[TextFragment],
    dimensions: dict[str, tuple[float, float]],
    expected_keys: Mapping[str, frozenset[str]],
) -> RawTextPass:
    """Return exactly proven exclusions and the remaining raw difference rows.

    A changed row requires a mutually unique candidate on a confirmed link.
    Everything else remains a separate removed or added row with its original
    fragment box. No fuzzy score proves sameness or edits an expert link.
    """
    if len(links) > _MAX_LINKS or len(fragments) > _MAX_FRAGMENTS:
        raise ValueError("stage_text_difference_budget_exceeded")
    exact = prove_exact_exclusions(links, fragments, dimensions, expected_keys)
    excluded_left = {item.left_content_key for item in exact}
    excluded_right = {item.right_content_key for item in exact}
    by_profile: dict[str, list[TextFragment]] = {profile: [] for profile in dimensions}
    for fragment in fragments:
        if fragment.content_key not in (excluded_left if fragment.side == "left" else excluded_right):
            by_profile[fragment.profile_id].append(fragment)
    comparisons = sum(len(by_profile[link.left_profile_id]) * len(by_profile[link.right_profile_id])
                      for link in links)
    if comparisons > _MAX_CANDIDATES:
        raise ValueError("stage_text_candidate_budget_exceeded")
    left_options: dict[str, list[tuple[float, str]]] = {}
    right_options: dict[str, list[tuple[float, str]]] = {}
    for link in links:
        for left in by_profile[link.left_profile_id]:
            for right in by_profile[link.right_profile_id]:
                score = _score(left, right)
                if score:
                    left_options.setdefault(left.content_key, []).append((score, right.content_key))
                    right_options.setdefault(right.content_key, []).append((score, left.content_key))
    left_best = {key: _unique_best(options) for key, options in left_options.items()}
    right_best = {key: _unique_best(options) for key, options in right_options.items()}
    paired = sorted(
        (left, right) for left, right in left_best.items()
        if right is not None and right_best.get(right) == left
    )
    used_left = {left for left, _ in paired}
    used_right = {right for _, right in paired}
    differences = [RawDifference("changed", left, right) for left, right in paired]
    for key in sorted(f.content_key for f in fragments
                      if f.side == "left" and f.content_key not in excluded_left | used_left):
        differences.append(RawDifference("removed", key, None))
    for key in sorted(f.content_key for f in fragments
                      if f.side == "right" and f.content_key not in excluded_right | used_right):
        differences.append(RawDifference("added", None, key))
    return RawTextPass(exact, tuple(differences))
