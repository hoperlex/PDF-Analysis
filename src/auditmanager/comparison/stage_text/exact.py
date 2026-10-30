"""Conservative exact exclusions inside caller-confirmed sheet links."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import hypot
from typing import Mapping, Sequence

from .fragments import TextFragment

__all__ = ["ExactExclusion", "SheetLink", "prove_exact_exclusions"]


@dataclass(frozen=True, slots=True)
class SheetLink:
    left_profile_id: str
    right_profile_id: str


@dataclass(frozen=True, slots=True)
class ExactExclusion:
    left_content_key: str
    right_content_key: str
    proof_kind: str  # same or moved


def _relative_center(fragment: TextFragment, dimensions: tuple[float, float]) -> tuple[float, float]:
    box = fragment.box_anchor
    return ((box["x0"] + box["x1"]) / (2 * dimensions[0]),
            (box["top"] + box["bottom"]) / (2 * dimensions[1]))


def prove_exact_exclusions(
    links: Sequence[SheetLink],
    fragments: Sequence[TextFragment],
    dimensions: dict[str, tuple[float, float]],
    expected_keys: Mapping[str, frozenset[str]],
) -> tuple[ExactExclusion, ...]:
    """Prove unique exact text on a confirmed linked sheet pair.

    A phrase repeated on either side anywhere in the supplied relation set stays
    unmatched. The caller derives ``expected_keys`` from complete, immutable
    page-profile extraction. A missing fragment refuses before any proof.
    """
    if len(links) > 1_000 or len(fragments) > 20_000:
        raise ValueError("text_evidence_too_large")
    if len({(l.left_profile_id, l.right_profile_id) for l in links}) != len(links):
        raise ValueError("duplicate_sheet_link")
    if any(link.left_profile_id not in dimensions or link.right_profile_id not in dimensions
           for link in links):
        raise ValueError("linked_profile_dimensions_missing")
    linked_left = {link.left_profile_id for link in links}
    linked_right = {link.right_profile_id for link in links}
    linked_profiles = linked_left | linked_right
    if (set(dimensions) != linked_profiles or set(expected_keys) != linked_profiles
            or linked_left & linked_right):
        raise ValueError("linked_profile_manifest_invalid")
    keyed = {f.content_key: f for f in fragments}
    if len(keyed) != len(fragments):
        raise ValueError("duplicate_fragment_key")
    by_profile: dict[str, list[TextFragment]] = defaultdict(list)
    for fragment in fragments:
        if fragment.side not in {"left", "right"} or fragment.profile_id not in dimensions:
            raise ValueError("fragment_scope_invalid")
        if (fragment.side == "left" and fragment.profile_id not in linked_left) or (
            fragment.side == "right" and fragment.profile_id not in linked_right
        ):
            raise ValueError("fragment_not_in_links")
        width, height = dimensions[fragment.profile_id]
        if width <= 0 or height <= 0:
            raise ValueError("page_dimensions_invalid")
        by_profile[fragment.profile_id].append(fragment)
    if any(frozenset(f.content_key for f in by_profile[profile]) != expected_keys[profile]
           for profile in linked_profiles):
        raise ValueError("fragment_manifest_mismatch")
    for link in links:
        if (any(f.side != "left" for f in by_profile[link.left_profile_id])
                or any(f.side != "right" for f in by_profile[link.right_profile_id])):
            raise ValueError("sheet_link_side_invalid")
    counts = {
        "left": Counter(f.normalised_text for f in fragments if f.profile_id in linked_left and f.side == "left"),
        "right": Counter(f.normalised_text for f in fragments if f.profile_id in linked_right and f.side == "right"),
    }
    out: list[ExactExclusion] = []
    for link in sorted(links, key=lambda l: (l.left_profile_id, l.right_profile_id)):
        right = {f.normalised_text: f for f in by_profile[link.right_profile_id]
                 if counts["right"][f.normalised_text] == 1}
        for left in by_profile[link.left_profile_id]:
            value = left.normalised_text
            if len(value) < 8 or counts["left"][value] != 1:
                continue
            match = right.get(value)
            if match is None:
                continue
            a = _relative_center(left, dimensions[left.profile_id])
            b = _relative_center(match, dimensions[match.profile_id])
            distance = hypot(a[0] - b[0], a[1] - b[1])
            if distance > (0.24 if len(value) >= 30 else 0.12):
                continue
            out.append(ExactExclusion(left.content_key, match.content_key,
                                      "same" if distance <= 0.03 else "moved"))
    return tuple(sorted(out, key=lambda item: (item.left_content_key, item.right_content_key)))
