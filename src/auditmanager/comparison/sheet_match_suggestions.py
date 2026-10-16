"""Rebuildable exact-text sheet suggestions for two ordered versions.

The caller supplies complete page-text snapshots from published versions.
Page numbers are coordinates, never identities. A suggestion has no approval
authority and cannot become an ``ApprovedSheetPair`` without expert action.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Mapping

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
        try:
            encoded = value.encode("utf-8")
        except UnicodeEncodeError:
            raise SheetMatchSuggestionRefused(f"{label}_page_text_invalid") from None
        if len(value) > MAX_SNAPSHOT_PAGE_CHARACTERS:
            raise SheetMatchSuggestionRefused(f"{label}_page_too_large")
        total_characters += len(value)
        if total_characters > MAX_SNAPSHOT_CHARACTERS:
            raise SheetMatchSuggestionRefused(f"{label}_pages_too_large")
        if value.strip():
            by_digest.setdefault(hashlib.sha256(encoded).hexdigest(), []).append(number)
    return by_digest


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
    _identity(version_pair.project_uid, ProjectUid, "project_uid")
    _identity(version_pair.document_uid, DocumentUid, "document_uid")
    source, target = version_pair.source, version_pair.target
    _version(source, version_pair, "source")
    _version(target, version_pair, "target")
    if source.version_uid == target.version_uid or source.version_ordinal >= target.version_ordinal:
        raise SheetMatchSuggestionRefused("version_order_invalid")

    older = _page_digests(source_pages, source.page_count, "source")
    newer = _page_digests(target_pages, target.page_count, "target")
    suggestions: list[SheetMatchSuggestion] = []
    for digest in older.keys() & newer.keys():
        if len(older[digest]) != 1 or len(newer[digest]) != 1:
            continue
        source_page, target_page = older[digest][0], newer[digest][0]
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
        suggestion_sha256 = hashlib.sha256(json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")).hexdigest()
        suggestions.append(SheetMatchSuggestion(
            ALGORITHM, comparison_id, source.version_uid, target.version_uid,
            source_page, target_page, digest, suggestion_sha256,
        ))
    return tuple(sorted(suggestions, key=lambda item: item.source_page_number))


__all__ = [
    "SheetMatchSuggestion", "SheetMatchSuggestionRefused", "suggest_exact_sheet_matches",
]
