"""Bounded, write-once input for version text comparison.

This pure module consumes *already approved* SheetLink rows. It neither
suggests pairs nor proves that the caller authorized the approval. Page numbers
are coordinates in immutable DocumentVersions, not identities inferred from a
filename, sheet label or display number. The later persistence layer owns the
approved state and must store these raw results separately from AI synthesis.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Mapping, Sequence

from auditmanager.shared.identity import (
    ComparisonId,
    IdentityError,
    SheetLinkId,
    VersionUid,
)

ALGORITHM = "approved-sheet-lines-v1"
MAX_PAIRS = 32
MAX_PAGE_CHARACTERS = 200_000
MAX_TOTAL_CHARACTERS = 2_000_000
MAX_LINES_PER_PAGE = 1_000
MAX_TOTAL_LINES = 4_000


class RawTextDiffRefused(ValueError):
    """An input cannot produce a bounded and attributable raw artifact."""


@dataclass(frozen=True, slots=True)
class ApprovedSheetPair:
    """One caller-supplied, authoritative link at a recorded approval revision."""

    comparison_id: str
    sheet_link_id: str
    link_revision: int
    source_version_uid: str
    target_version_uid: str
    source_page_number: int
    target_page_number: int


@dataclass(frozen=True, slots=True)
class LineChange:
    tag: str
    source_start: int
    source_end: int
    target_start: int
    target_end: int
    source_lines: tuple[str, ...]
    target_lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RawTextDiff:
    algorithm: str
    comparison_id: str
    sheet_link_id: str
    link_revision: int
    source_version_uid: str
    target_version_uid: str
    source_page_number: int
    target_page_number: int
    source_sha256: str
    target_sha256: str
    changes: tuple[LineChange, ...]
    evidence_sha256: str


def _check_identity(value: str, identity_type: type, field: str) -> None:
    try:
        identity_type.parse(value)
    except (IdentityError, TypeError):
        raise RawTextDiffRefused(f"{field}_invalid") from None


def _check_positive(value: int, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise RawTextDiffRefused(f"{field}_invalid")


def _lines(text: str, field: str) -> tuple[str, ...]:
    if not isinstance(text, str):
        raise RawTextDiffRefused(f"{field}_invalid")
    if len(text) > MAX_PAGE_CHARACTERS:
        raise RawTextDiffRefused(f"{field}_too_large")
    lines = tuple(text.splitlines(keepends=True))
    if len(lines) > MAX_LINES_PER_PAGE:
        raise RawTextDiffRefused(f"{field}_too_many_lines")
    return lines


def _raw_diff(pair: ApprovedSheetPair, source: str, target: str) -> RawTextDiff:
    source_lines = _lines(source, "source_text")
    target_lines = _lines(target, "target_text")
    try:
        source_digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        target_digest = hashlib.sha256(target.encode("utf-8")).hexdigest()
    except UnicodeEncodeError:
        raise RawTextDiffRefused("text_not_utf8_encodable") from None

    matcher = SequenceMatcher(None, source_lines, target_lines, autojunk=False)
    changes = tuple(
        LineChange(
            tag=tag,
            source_start=source_start,
            source_end=source_end,
            target_start=target_start,
            target_end=target_end,
            source_lines=source_lines[source_start:source_end],
            target_lines=target_lines[target_start:target_end],
        )
        for tag, source_start, source_end, target_start, target_end in matcher.get_opcodes()
    )
    body = {
        "algorithm": ALGORITHM,
        "comparison_id": pair.comparison_id,
        "sheet_link_id": pair.sheet_link_id,
        "link_revision": pair.link_revision,
        "source_version_uid": pair.source_version_uid,
        "target_version_uid": pair.target_version_uid,
        "source_page_number": pair.source_page_number,
        "target_page_number": pair.target_page_number,
        "source_sha256": source_digest,
        "target_sha256": target_digest,
        "changes": [
            {
                "tag": change.tag,
                "source_start": change.source_start,
                "source_end": change.source_end,
                "target_start": change.target_start,
                "target_end": change.target_end,
                "source_lines": change.source_lines,
                "target_lines": change.target_lines,
            }
            for change in changes
        ],
    }
    evidence_digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return RawTextDiff(**body | {"changes": changes, "evidence_sha256": evidence_digest})


def diff_approved_pairs(
    *,
    comparison_id: str,
    source_version_uid: str,
    target_version_uid: str,
    link_revision: int,
    approved_pairs: Sequence[ApprovedSheetPair],
    source_pages: Mapping[int, str],
    target_pages: Mapping[int, str],
) -> tuple[RawTextDiff, ...]:
    """Compare explicitly linked page text, with no automatic pairing or fallback.

    The caller must load links from authoritative approved state, establish
    same-set membership and version ordering, and persist the returned evidence
    as immutable revision artifacts. This function refuses even one ambiguous
    pair before yielding any result.
    """
    _check_identity(comparison_id, ComparisonId, "comparison_id")
    _check_identity(source_version_uid, VersionUid, "source_version_uid")
    _check_identity(target_version_uid, VersionUid, "target_version_uid")
    if source_version_uid == target_version_uid:
        raise RawTextDiffRefused("same_version")
    _check_positive(link_revision, "link_revision")
    if not isinstance(approved_pairs, (tuple, list)) or not 1 <= len(approved_pairs) <= MAX_PAIRS:
        raise RawTextDiffRefused("pair_count_invalid")
    if not isinstance(source_pages, Mapping) or not isinstance(target_pages, Mapping):
        raise RawTextDiffRefused("page_text_mapping_invalid")

    seen_links: set[str] = set()
    seen_source_pages: set[int] = set()
    seen_target_pages: set[int] = set()
    total_characters = 0
    total_lines = 0
    ordered: list[tuple[ApprovedSheetPair, str, str]] = []
    for pair in approved_pairs:
        if not isinstance(pair, ApprovedSheetPair):
            raise RawTextDiffRefused("pair_invalid")
        _check_identity(pair.comparison_id, ComparisonId, "pair_comparison_id")
        _check_identity(pair.sheet_link_id, SheetLinkId, "sheet_link_id")
        _check_identity(pair.source_version_uid, VersionUid, "pair_source_version_uid")
        _check_identity(pair.target_version_uid, VersionUid, "pair_target_version_uid")
        _check_positive(pair.link_revision, "pair_link_revision")
        _check_positive(pair.source_page_number, "source_page_number")
        _check_positive(pair.target_page_number, "target_page_number")
        if pair.comparison_id != comparison_id or pair.link_revision != link_revision:
            raise RawTextDiffRefused("pair_revision_mismatch")
        if (
            pair.source_version_uid != source_version_uid
            or pair.target_version_uid != target_version_uid
        ):
            raise RawTextDiffRefused("pair_version_mismatch")
        if (
            pair.sheet_link_id in seen_links
            or pair.source_page_number in seen_source_pages
            or pair.target_page_number in seen_target_pages
        ):
            raise RawTextDiffRefused("pair_not_one_to_one")
        seen_links.add(pair.sheet_link_id)
        seen_source_pages.add(pair.source_page_number)
        seen_target_pages.add(pair.target_page_number)
        if (
            pair.source_page_number not in source_pages
            or pair.target_page_number not in target_pages
        ):
            raise RawTextDiffRefused("page_text_missing")
        source = source_pages[pair.source_page_number]
        target = target_pages[pair.target_page_number]
        source_lines = _lines(source, "source_text")
        target_lines = _lines(target, "target_text")
        total_characters += len(source) + len(target)
        total_lines += len(source_lines) + len(target_lines)
        if total_characters > MAX_TOTAL_CHARACTERS or total_lines > MAX_TOTAL_LINES:
            raise RawTextDiffRefused("comparison_input_too_large")
        ordered.append((pair, source, target))

    ordered.sort(key=lambda entry: (entry[0].source_page_number, entry[0].sheet_link_id))
    return tuple(_raw_diff(pair, source, target) for pair, source, target in ordered)
