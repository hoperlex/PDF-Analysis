"""Pure integrity seal for one ordered version pair's approved raw text diffs.

The caller supplies the authoritative version pair and approved link revision.
Recomputing the deterministic diffs from their embedded text prevents a derived
AI artifact from becoming an alternative source of raw comparison evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Sequence

from auditmanager.comparison.raw_text import (
    MAX_LINES_PER_PAGE,
    MAX_PAGE_CHARACTERS,
    ApprovedSheetPair,
    LineChange,
    RawTextDiff,
    RawTextDiffRefused,
    diff_approved_pairs,
)
from auditmanager.comparison.version_reader import MAX_VERSION_PAGES, OrderedVersionPair
from auditmanager.shared.identity import ComparisonId, IdentityError

ALGORITHM = "approved-sheet-raw-evidence-seal-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class RawEvidenceSealRefused(ValueError):
    """The supplied pair and raw differences cannot form one exact artifact."""


@dataclass(frozen=True, slots=True)
class RawEvidenceSeal:
    algorithm: str
    comparison_id: str
    project_uid: str
    document_uid: str
    source_version_uid: str
    target_version_uid: str
    source_version_sha256: str
    target_version_sha256: str
    link_revision: int
    sheet_evidence_sha256s: tuple[str, ...]
    seal_sha256: str


def _text(changes: tuple[LineChange, ...], *, source: bool) -> str:
    if not isinstance(changes, tuple):
        raise RawEvidenceSealRefused("changes_invalid")
    lines: list[str] = []
    characters = 0
    for change in changes:
        if not isinstance(change, LineChange):
            raise RawEvidenceSealRefused("changes_invalid")
        part = change.source_lines if source else change.target_lines
        if not isinstance(part, tuple) or any(not isinstance(line, str) for line in part):
            raise RawEvidenceSealRefused("changes_invalid")
        characters += sum(len(line) for line in part)
        if characters > MAX_PAGE_CHARACTERS or len(lines) + len(part) > MAX_LINES_PER_PAGE:
            raise RawEvidenceSealRefused("changes_too_large")
        lines.extend(part)
    joined = "".join(lines)
    if tuple(joined.splitlines(keepends=True)) != tuple(lines):
        raise RawEvidenceSealRefused("changes_invalid")
    return joined


def seal_raw_version_evidence(
    *,
    version_pair: OrderedVersionPair,
    comparison_id: str,
    link_revision: int,
    raw_diffs: Sequence[RawTextDiff],
) -> RawEvidenceSeal:
    """Verify and bind every page diff to immutable version bytes and approval.

    The caller must read the pair and approved links in one consistent
    transaction, persist the raw diffs write-once, then let a separate AI
    artifact reference ``seal_sha256``. This function grants no approval.
    """
    if not isinstance(version_pair, OrderedVersionPair):
        raise RawEvidenceSealRefused("version_pair_invalid")
    try:
        ComparisonId.parse(comparison_id)
    except (IdentityError, TypeError):
        raise RawEvidenceSealRefused("comparison_id_invalid") from None
    if type(link_revision) is not int or link_revision < 1:
        raise RawEvidenceSealRefused("link_revision_invalid")
    if not isinstance(raw_diffs, (tuple, list)) or not raw_diffs:
        raise RawEvidenceSealRefused("raw_diffs_invalid")

    source, target = version_pair.source, version_pair.target
    if (
        source.document_uid != version_pair.document_uid
        or target.document_uid != version_pair.document_uid
        or source.project_uid != version_pair.project_uid
        or target.project_uid != version_pair.project_uid
        or type(source.version_ordinal) is not int
        or type(target.version_ordinal) is not int
        or source.version_ordinal >= target.version_ordinal
        or type(source.page_count) is not int
        or type(target.page_count) is not int
        or not 1 <= source.page_count <= MAX_VERSION_PAGES
        or not 1 <= target.page_count <= MAX_VERSION_PAGES
        or source.version_uid == target.version_uid
        or not isinstance(source.sha256, str)
        or _SHA256.fullmatch(source.sha256) is None
        or not isinstance(target.sha256, str)
        or _SHA256.fullmatch(target.sha256) is None
    ):
        raise RawEvidenceSealRefused("version_pair_invalid")
    pairs: list[ApprovedSheetPair] = []
    source_pages: dict[int, str] = {}
    target_pages: dict[int, str] = {}
    for diff in raw_diffs:
        if not isinstance(diff, RawTextDiff):
            raise RawEvidenceSealRefused("raw_diff_invalid")
        if (
            diff.comparison_id != comparison_id
            or diff.link_revision != link_revision
            or diff.source_version_uid != source.version_uid
            or diff.target_version_uid != target.version_uid
        ):
            raise RawEvidenceSealRefused("raw_diff_binding_mismatch")
        if (
            type(diff.source_page_number) is not int
            or type(diff.target_page_number) is not int
            or not 1 <= diff.source_page_number <= source.page_count
            or not 1 <= diff.target_page_number <= target.page_count
        ):
            raise RawEvidenceSealRefused("raw_diff_page_out_of_range")
        pairs.append(ApprovedSheetPair(
            comparison_id, diff.sheet_link_id, link_revision,
            source.version_uid, target.version_uid,
            diff.source_page_number, diff.target_page_number,
        ))
        source_pages[diff.source_page_number] = _text(diff.changes, source=True)
        target_pages[diff.target_page_number] = _text(diff.changes, source=False)
    try:
        recomputed = diff_approved_pairs(
            comparison_id=comparison_id,
            source_version_uid=source.version_uid,
            target_version_uid=target.version_uid,
            link_revision=link_revision,
            approved_pairs=pairs,
            source_pages=source_pages,
            target_pages=target_pages,
        )
    except RawTextDiffRefused as error:
        raise RawEvidenceSealRefused(str(error)) from None
    if tuple(sorted(raw_diffs, key=lambda item: (item.source_page_number, item.sheet_link_id))) != recomputed:
        raise RawEvidenceSealRefused("raw_diff_not_canonical")

    body = {
        "algorithm": ALGORITHM,
        "comparison_id": comparison_id,
        "project_uid": version_pair.project_uid,
        "document_uid": version_pair.document_uid,
        "source_version_uid": source.version_uid,
        "target_version_uid": target.version_uid,
        "source_version_sha256": source.sha256,
        "target_version_sha256": target.sha256,
        "link_revision": link_revision,
        "sheet_evidence_sha256s": tuple(diff.evidence_sha256 for diff in recomputed),
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return RawEvidenceSeal(**body, seal_sha256=digest)


__all__ = ["RawEvidenceSeal", "RawEvidenceSealRefused", "seal_raw_version_evidence"]
