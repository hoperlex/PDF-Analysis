"""Pure AR v2 grouping after the independent grounding gate.

This module assigns neither finding IDs nor verdicts. Its caller passes only
grounded observations, after the gate has retained diagnostics elsewhere.
Ordinals are positions in the run artifact, never database identities.
"""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

ARTIFACT_ROLE = "findings.merged"
ARTIFACT_VERSION = "1.0.0"
MERGE_RULE_VERSION = "1.0.0"
MIN_EQUAL_QUOTE_CHARS = 20


@dataclass(frozen=True, slots=True)
class MergeEvidence:
    page_number: int
    char_start: int
    char_end: int
    quote: str


@dataclass(frozen=True, slots=True)
class MergeObservation:
    observation_ordinal: int
    category: str
    evidence: tuple[MergeEvidence, ...]


def _normalised_quote(quote: str) -> str:
    return " ".join(unicodedata.normalize("NFC", quote).casefold().split())


def _validate(observations: Sequence[MergeObservation]) -> None:
    seen: set[int] = set()
    for observation in observations:
        ordinal = observation.observation_ordinal
        if type(ordinal) is not int or ordinal < 0 or ordinal in seen:
            raise ValueError("observation ordinals must be distinct nonnegative integers")
        seen.add(ordinal)
        if not isinstance(observation.category, str) or not observation.category:
            raise ValueError(f"observation {ordinal} has no category")
        if not observation.evidence:
            raise ValueError(f"observation {ordinal} has no grounded evidence")
        for item in observation.evidence:
            if type(item.page_number) is not int or item.page_number < 1:
                raise ValueError(f"observation {ordinal} has an invalid page")
            if (type(item.char_start) is not int or type(item.char_end) is not int
                    or item.char_start < 0 or item.char_end <= item.char_start):
                raise ValueError(f"observation {ordinal} has an invalid evidence span")
            if not isinstance(item.quote, str) or not item.quote:
                raise ValueError(f"observation {ordinal} has an empty evidence quote")


def merge_grounded(observations: Sequence[MergeObservation]) -> dict[str, object]:
    """Return connected components with a canonical member for each component.

    Overlap uses half-open spans, so adjacent citations do not overlap. An
    equal quote links only on the same page and category, and only when its
    normalised text has at least twenty Unicode code points. Input order has
    no bearing on the result.
    """
    _validate(observations)
    ordered = sorted(observations, key=lambda item: item.observation_ordinal)
    parent = list(range(len(ordered)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first: int, second: int) -> None:
        a, b = find(first), find(second)
        if a != b:
            parent[max(a, b)] = min(a, b)

    spans: dict[tuple[str, int], list[tuple[int, int, int]]] = defaultdict(list)
    first_for_quote: dict[tuple[str, int, str], int] = {}
    for index, observation in enumerate(ordered):
        for evidence in observation.evidence:
            spans[(observation.category, evidence.page_number)].append(
                (evidence.char_start, evidence.char_end, index)
            )
            quote = _normalised_quote(evidence.quote)
            if len(quote) >= MIN_EQUAL_QUOTE_CHARS:
                key = (observation.category, evidence.page_number, quote)
                previous = first_for_quote.setdefault(key, index)
                union(previous, index)

    # The interval sweep joins every overlap chain using one representative
    # and the maximum end reached so far. Equal endpoints are disjoint.
    for page_spans in spans.values():
        page_spans.sort()
        representative: int | None = None
        furthest_end = -1
        for start, end, index in page_spans:
            if representative is not None and start < furthest_end:
                union(representative, index)
                furthest_end = max(furthest_end, end)
            else:
                representative = index
                furthest_end = end

    components: dict[int, list[MergeObservation]] = defaultdict(list)
    for index, observation in enumerate(ordered):
        components[find(index)].append(observation)

    def canonical_key(observation: MergeObservation) -> tuple[int, int, int]:
        earliest = min((e.page_number, e.char_start) for e in observation.evidence)
        return (*earliest, observation.observation_ordinal)

    sorted_components = sorted(
        components.values(), key=lambda members: min(canonical_key(item) for item in members)
    )
    groups = []
    for members in sorted_components:
        canonical = min(members, key=canonical_key)
        groups.append({
            "observation_ordinals": sorted(item.observation_ordinal for item in members),
            "canonical_ordinal": canonical.observation_ordinal,
            "merge_rule_version": MERGE_RULE_VERSION,
        })
    return {
        "artifact_role": ARTIFACT_ROLE,
        "artifact_version": ARTIFACT_VERSION,
        "groups": groups,
    }
