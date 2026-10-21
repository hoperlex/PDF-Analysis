"""Rebuildable exact-text sheet suggestions for two ordered versions.

The caller supplies complete page-text snapshots from published versions.
Page numbers are coordinates, never identities. A suggestion has no approval
authority and cannot become an ``ApprovedSheetPair`` without expert action.

:func:`suggest_exact_sheet_matches` binds its candidates to a future persisted
Comparison. :func:`suggest_sheet_pairs` serves the read-only comparison, which
has no Comparison identity: it applies the same exact rule, then proposes pairs
for the pages that rule left unpaired by the distinctive lines two pages share,
so a sheet whose text changed still has a candidate counterpart. Both results
are suggestions only; neither carries a ComparisonId or a SheetLinkId.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence

from auditmanager.comparison.version_reader import (
    MAX_VERSION_PAGES,
    OrderedVersionPair,
    VersionFacts,
)
from auditmanager.shared.identity import (
    ComparisonId,
    DocumentUid,
    IdentityError,
    ProjectUid,
    VersionUid,
)

ALGORITHM = "exact-complete-page-text-suggestion-v1"
# A complete text snapshot follows W55b's PDF envelope: 200k characters per
# page and 20M per version. Only one page is UTF-8 encoded at a time, so the
# hashing scratch buffer is at most 800k bytes. The caller retains the maps.
MAX_SNAPSHOT_PAGE_CHARACTERS = 200_000
MAX_SNAPSHOT_CHARACTERS = 20_000_000
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")

#: The read-only rules of :func:`suggest_sheet_pairs`.
EXACT_PAIR_ALGORITHM = "exact-page-text-pair-suggestion-v1"
SIMILAR_PAIR_ALGORITHM = "distinctive-line-pair-suggestion-v1"
#: A whitespace-collapsed, nonblank line is *distinctive* while it occurs on at
#: most this many pages of the two versions together. Stamp and frame text that
#: repeats on many sheets carries no pairing signal and is ignored; the cap also
#: bounds the pair-count work to 16 increments per distinct line.
MAX_DISTINCTIVE_LINE_PAGES = 8
#: A candidate needs at least this many shared distinctive lines ...
MIN_SHARED_DISTINCTIVE_LINES = 2
#: ... and a Dice similarity 2*shared/(source+target) of at least this, in permille.
MIN_SIMILARITY_PERMILLE = 500


class SheetMatchSuggestionRefused(ValueError):
    """The supplied version or page snapshot is incomplete or invalid."""


@dataclass(frozen=True, slots=True)
class SheetMatchSuggestion:
    algorithm: str
    comparison_id: str
    source_version_uid: str
    target_version_uid: str
    source_page_number: int
    target_page_number: int
    page_text_sha256: str
    suggestion_sha256: str


@dataclass(frozen=True, slots=True)
class SheetPairSuggestion:
    """One read-only sheet pair candidate and the evidence it rests on.

    For ``EXACT_PAIR_ALGORITHM`` both page digests are equal and the line counts
    are ``None``; for ``SIMILAR_PAIR_ALGORITHM`` the counts are distinctive
    lines and ``similarity_permille`` is the Dice similarity of those sets.
    """

    algorithm: str
    source_version_uid: str
    target_version_uid: str
    source_page_number: int
    target_page_number: int
    source_page_text_sha256: str
    target_page_text_sha256: str
    shared_line_count: int | None
    source_line_count: int | None
    target_line_count: int | None
    similarity_permille: int
    suggestion_sha256: str


def _identity(value: str, kind: type, label: str) -> None:
    try:
        kind.parse(value)
    except (IdentityError, TypeError):
        raise SheetMatchSuggestionRefused(f"{label}_invalid") from None


def _version(facts: VersionFacts, pair: OrderedVersionPair, label: str) -> None:
    if not isinstance(facts, VersionFacts):
        raise SheetMatchSuggestionRefused("version_pair_invalid")
    _identity(facts.version_uid, VersionUid, f"{label}_version_uid")
    if facts.project_uid != pair.project_uid or facts.document_uid != pair.document_uid:
        raise SheetMatchSuggestionRefused("version_pair_mismatch")
    if (
        type(facts.version_ordinal) is not int or facts.version_ordinal < 1
        or type(facts.page_count) is not int or not 1 <= facts.page_count <= MAX_VERSION_PAGES
        or type(facts.byte_size) is not int or facts.byte_size < 0
        or not isinstance(facts.sha256, str) or _SHA256.fullmatch(facts.sha256) is None
        or facts.media_type != "application/pdf"
    ):
        raise SheetMatchSuggestionRefused("version_facts_invalid")


def _page_digests(pages: Mapping[int, str], page_count: int, label: str) -> dict[str, list[int]]:
    if (
        not isinstance(pages, Mapping)
        or len(pages) != page_count
        or any(type(number) is not int for number in pages)
        or set(pages) != set(range(1, page_count + 1))
    ):
        raise SheetMatchSuggestionRefused(f"{label}_pages_incomplete")
    by_digest: dict[str, list[int]] = {}
    total_characters = 0
    for number in range(1, page_count + 1):
        value = pages[number]
        if not isinstance(value, str):
            raise SheetMatchSuggestionRefused(f"{label}_page_text_invalid")
        if len(value) > MAX_SNAPSHOT_PAGE_CHARACTERS:
            raise SheetMatchSuggestionRefused(f"{label}_page_too_large")
        total_characters += len(value)
        if total_characters > MAX_SNAPSHOT_CHARACTERS:
            raise SheetMatchSuggestionRefused(f"{label}_pages_too_large")
        try:
            encoded = value.encode("utf-8")
        except UnicodeEncodeError:
            raise SheetMatchSuggestionRefused(f"{label}_page_text_invalid") from None
        if value.strip():
            by_digest.setdefault(hashlib.sha256(encoded).hexdigest(), []).append(number)
    return by_digest


def _exact_pairs(
    older: dict[str, list[int]], newer: dict[str, list[int]],
) -> list[tuple[str, int, int]]:
    """Unique identical nonblank pages: ``(page_text_sha256, source, target)``."""
    return [
        (digest, older[digest][0], newer[digest][0])
        for digest in older.keys() & newer.keys()
        if len(older[digest]) == 1 and len(newer[digest]) == 1
    ]


def _digest(body: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


def suggest_exact_sheet_matches(
    *,
    version_pair: OrderedVersionPair,
    comparison_id: str,
    source_pages: Mapping[int, str],
    target_pages: Mapping[int, str],
) -> tuple[SheetMatchSuggestion, ...]:
    """Suggest unique identical nonblank pages from complete page snapshots.

    Any repeated text on either version is ambiguous and yields no suggestion.
    Changed and textless sheets require an independent expert-approved link.
    The caller must prove source custody and persisted approval separately.
    """
    if not isinstance(version_pair, OrderedVersionPair):
        raise SheetMatchSuggestionRefused("version_pair_invalid")
    _identity(comparison_id, ComparisonId, "comparison_id")
    source, target = _check_pair(version_pair)

    older = _page_digests(source_pages, source.page_count, "source")
    newer = _page_digests(target_pages, target.page_count, "target")
    suggestions: list[SheetMatchSuggestion] = []
    for digest, source_page, target_page in _exact_pairs(older, newer):
        body = {
            "algorithm": ALGORITHM,
            "comparison_id": comparison_id,
            "project_uid": version_pair.project_uid,
            "document_uid": version_pair.document_uid,
            "source_version_uid": source.version_uid,
            "target_version_uid": target.version_uid,
            "source_version_sha256": source.sha256,
            "target_version_sha256": target.sha256,
            "source_page_number": source_page,
            "target_page_number": target_page,
            "page_text_sha256": digest,
        }
        suggestions.append(SheetMatchSuggestion(
            ALGORITHM, comparison_id, source.version_uid, target.version_uid,
            source_page, target_page, digest, _digest(body),
        ))
    return tuple(sorted(suggestions, key=lambda item: item.source_page_number))


def _check_pair(version_pair: OrderedVersionPair) -> tuple[VersionFacts, VersionFacts]:
    if not isinstance(version_pair, OrderedVersionPair):
        raise SheetMatchSuggestionRefused("version_pair_invalid")
    _identity(version_pair.project_uid, ProjectUid, "project_uid")
    _identity(version_pair.document_uid, DocumentUid, "document_uid")
    source, target = version_pair.source, version_pair.target
    _version(source, version_pair, "source")
    _version(target, version_pair, "target")
    if source.version_uid == target.version_uid or source.version_ordinal >= target.version_ordinal:
        raise SheetMatchSuggestionRefused("version_order_invalid")
    return source, target


def _distinctive_line_sets(
    source_pages: Mapping[int, str], source_count: int,
    target_pages: Mapping[int, str], target_count: int,
) -> tuple[list[frozenset[str]], list[frozenset[str]]]:
    """Per page, the whitespace-collapsed nonblank lines that are distinctive."""
    def lines(pages: Mapping[int, str], count: int) -> list[frozenset[str]]:
        return [
            frozenset(
                collapsed
                for collapsed in (" ".join(line.split()) for line in pages[number].splitlines())
                if collapsed
            )
            for number in range(1, count + 1)
        ]

    older, newer = lines(source_pages, source_count), lines(target_pages, target_count)
    frequency: Counter[str] = Counter()
    for page in (*older, *newer):
        frequency.update(page)

    def keep(page: frozenset[str]) -> frozenset[str]:
        return frozenset(line for line in page if frequency[line] <= MAX_DISTINCTIVE_LINE_PAGES)

    return [keep(page) for page in older], [keep(page) for page in newer]


def _similar_pairs(
    older: list[frozenset[str]], newer: list[frozenset[str]],
    anchored_source: set[int], anchored_target: set[int],
) -> list[tuple[int, int, int, int]]:
    """Greedy one-to-one ``(source, target, shared, permille)`` over unanchored pages."""
    postings: dict[str, tuple[list[int], list[int]]] = {}
    for number, page in enumerate(older, start=1):
        if number not in anchored_source:
            for line in page:
                postings.setdefault(line, ([], []))[0].append(number)
    for number, page in enumerate(newer, start=1):
        if number not in anchored_target:
            for line in page:
                postings.setdefault(line, ([], []))[1].append(number)
    shared: Counter[tuple[int, int]] = Counter()
    for source_numbers, target_numbers in postings.values():
        for source_number in source_numbers:
            for target_number in target_numbers:
                shared[(source_number, target_number)] += 1

    candidates: list[tuple[int, int, int, int]] = []
    for (source_number, target_number), count in shared.items():
        total = len(older[source_number - 1]) + len(newer[target_number - 1])
        permille = (2000 * count) // total
        if count >= MIN_SHARED_DISTINCTIVE_LINES and permille >= MIN_SIMILARITY_PERMILLE:
            candidates.append((-permille, -count, source_number, target_number))
    candidates.sort()
    taken_source: set[int] = set()
    taken_target: set[int] = set()
    chosen: list[tuple[int, int, int, int]] = []
    for negative_permille, negative_count, source_number, target_number in candidates:
        if source_number in taken_source or target_number in taken_target:
            continue
        taken_source.add(source_number)
        taken_target.add(target_number)
        chosen.append((source_number, target_number, -negative_count, -negative_permille))
    return chosen


def suggest_sheet_pairs(
    *,
    version_pair: OrderedVersionPair,
    source_pages: Mapping[int, str],
    target_pages: Mapping[int, str],
) -> tuple[SheetPairSuggestion, ...]:
    """Read-only one-to-one sheet candidates: exact pages first, then similar ones.

    The exact rule is :func:`suggest_exact_sheet_matches`' rule. Pages it leaves
    unpaired get a similarity candidate when they share at least
    ``MIN_SHARED_DISTINCTIVE_LINES`` distinctive lines with a Dice similarity of
    at least ``MIN_SIMILARITY_PERMILLE``; candidates are taken greedily by
    similarity, then shared count, then page coordinates, so the result does
    not depend on mapping order. A page with no distinctive text (blank, or only
    repeated frame text) gets no candidate and stays explicitly unpaired.
    Nothing here approves, persists or links a pair.
    """
    source, target = _check_pair(version_pair)
    older_digests = _page_digests(source_pages, source.page_count, "source")
    newer_digests = _page_digests(target_pages, target.page_count, "target")
    binding = {
        "project_uid": version_pair.project_uid,
        "document_uid": version_pair.document_uid,
        "source_version_uid": source.version_uid,
        "target_version_uid": target.version_uid,
        "source_version_sha256": source.sha256,
        "target_version_sha256": target.sha256,
    }
    suggestions: list[SheetPairSuggestion] = []
    for digest, source_page, target_page in _exact_pairs(older_digests, newer_digests):
        body = binding | {
            "algorithm": EXACT_PAIR_ALGORITHM,
            "source_page_number": source_page,
            "target_page_number": target_page,
            "page_text_sha256": digest,
        }
        suggestions.append(SheetPairSuggestion(
            EXACT_PAIR_ALGORITHM, source.version_uid, target.version_uid,
            source_page, target_page, digest, digest, None, None, None, 1000, _digest(body),
        ))

    older, newer = _distinctive_line_sets(
        source_pages, source.page_count, target_pages, target.page_count,
    )
    anchored_source = {item.source_page_number for item in suggestions}
    anchored_target = {item.target_page_number for item in suggestions}
    for source_page, target_page, shared, permille in _similar_pairs(
        older, newer, anchored_source, anchored_target,
    ):
        source_text_sha256 = hashlib.sha256(source_pages[source_page].encode("utf-8")).hexdigest()
        target_text_sha256 = hashlib.sha256(target_pages[target_page].encode("utf-8")).hexdigest()
        source_count, target_count = len(older[source_page - 1]), len(newer[target_page - 1])
        body = binding | {
            "algorithm": SIMILAR_PAIR_ALGORITHM,
            "source_page_number": source_page,
            "target_page_number": target_page,
            "source_page_text_sha256": source_text_sha256,
            "target_page_text_sha256": target_text_sha256,
            "shared_line_count": shared,
            "source_line_count": source_count,
            "target_line_count": target_count,
            "similarity_permille": permille,
        }
        suggestions.append(SheetPairSuggestion(
            SIMILAR_PAIR_ALGORITHM, source.version_uid, target.version_uid,
            source_page, target_page, source_text_sha256, target_text_sha256,
            shared, source_count, target_count, permille, _digest(body),
        ))
    return tuple(sorted(suggestions, key=lambda item: item.source_page_number))


__all__ = [
    "SheetMatchSuggestion", "SheetMatchSuggestionRefused", "SheetPairSuggestion",
    "suggest_exact_sheet_matches", "suggest_sheet_pairs",
]
