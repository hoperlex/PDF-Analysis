"""Left-to-right cross-sheet text hints; recommendations never become exclusions."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Mapping, Sequence

from .exact import SheetLink
from .fragments import TextFragment

__all__ = ["CrossSheetHint", "find_cross_sheet_hints"]


@dataclass(frozen=True, slots=True)
class CrossSheetHint:
    source_content_key: str  # left, as the sealed stage_text_hint table requires
    target_content_key: str  # right


def find_cross_sheet_hints(
    links: Sequence[SheetLink],
    all_fragments: Sequence[TextFragment],
    expected_keys: Mapping[str, frozenset[str]],
    excluded_keys: frozenset[str],
) -> tuple[CrossSheetHint, ...]:
    """Recommend a unique exact match on an unexpected Р sheet.

    ``all_fragments`` includes the confirmed pair's unlinked sheets. This is a
    second lookup pass only; a hint never changes the map or raw-difference rows.
    The frozen table stores left source/right target, so the reverse direction
    deliberately waits for a contract decision.
    """
    if len(links) > 1_000 or len(all_fragments) > 20_000:
        raise ValueError("stage_text_hint_budget_exceeded")
    if len({f.content_key for f in all_fragments}) != len(all_fragments):
        raise ValueError("duplicate_fragment_key")
    by_profile: dict[str, list[TextFragment]] = defaultdict(list)
    for fragment in all_fragments:
        if fragment.side not in {"left", "right"} or fragment.profile_id not in expected_keys:
            raise ValueError("fragment_scope_invalid")
        by_profile[fragment.profile_id].append(fragment)
    if any(frozenset(f.content_key for f in by_profile[profile]) != expected_keys[profile]
           for profile in expected_keys):
        raise ValueError("fragment_manifest_mismatch")
    known_keys = {f.content_key for f in all_fragments}
    if not excluded_keys <= known_keys:
        raise ValueError("excluded_fragment_unknown")
    expected_right: dict[str, set[str]] = defaultdict(set)
    for link in links:
        if link.left_profile_id not in expected_keys or link.right_profile_id not in expected_keys:
            raise ValueError("linked_profile_missing")
        expected_right[link.left_profile_id].add(link.right_profile_id)
    left_counts = Counter(f.normalised_text for f in all_fragments if f.side == "left")
    right_counts = Counter(f.normalised_text for f in all_fragments if f.side == "right")
    right_by_text: dict[str, list[TextFragment]] = defaultdict(list)
    for fragment in all_fragments:
        if fragment.side == "right" and fragment.content_key not in excluded_keys:
            right_by_text[fragment.normalised_text].append(fragment)
    out: list[CrossSheetHint] = []
    for source in all_fragments:
        if (source.side != "left" or source.profile_id not in expected_right
                or source.content_key in excluded_keys or len(source.normalised_text) < 15
                or left_counts[source.normalised_text] != 1
                or right_counts[source.normalised_text] != 1):
            continue
        targets = right_by_text[source.normalised_text]
        if len(targets) != 1 or targets[0].profile_id in expected_right[source.profile_id]:
            continue
        out.append(CrossSheetHint(source.content_key, targets[0].content_key))
    return tuple(sorted(out, key=lambda hint: (hint.source_content_key, hint.target_content_key)))
