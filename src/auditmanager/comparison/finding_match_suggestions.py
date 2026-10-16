"""Conservative, rebuildable finding-match suggestions for ordered versions.

Only identical issue text and quoted evidence on explicitly linked sheets can
form a suggestion. A suggestion is never an approved match or a carryover
command; the comparison owner must persist expert approval separately.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import asdict, dataclass
from typing import Sequence

from auditmanager.comparison.raw_text import ApprovedSheetPair, MAX_PAIRS
from auditmanager.comparison.version_reader import OrderedVersionPair
from auditmanager.shared.identity import (
    ComparisonId,
    FindingObservationId,
    FindingUid,
    IdentityError,
    RunId,
    SheetLinkId,
    VersionUid,
)

ALGORITHM = "exact-linked-finding-suggestion-v1"
MAX_FINDINGS_PER_RUN = 200
MAX_EVIDENCE_PER_FINDING = 8


class FindingMatchSuggestionRefused(ValueError):
    """The inputs cannot form attributable, bounded suggestions."""


@dataclass(frozen=True, slots=True)
class FindingQuote:
    page_number: int
    quote: str


@dataclass(frozen=True, slots=True)
class FindingForMatch:
    finding_uid: str
    finding_observation_id: str
    run_id: str
    version_uid: str
    category: str
    finding_text: str
    evidence: tuple[FindingQuote, ...]


@dataclass(frozen=True, slots=True)
class FindingMatchSuggestion:
    algorithm: str
    comparison_id: str
    link_revision: int
    source_version_uid: str
    target_version_uid: str
    source_finding_uid: str
    target_finding_uid: str
    source_observation_id: str
    target_observation_id: str
    matched_sheet_link_ids: tuple[str, ...]
    suggestion_sha256: str


def _id(value: str, kind: type, label: str) -> None:
    try:
        kind.parse(value)
    except (IdentityError, TypeError):
        raise FindingMatchSuggestionRefused(f"{label}_invalid") from None


def _normalized(value: str, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise FindingMatchSuggestionRefused(f"{label}_invalid")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise FindingMatchSuggestionRefused(f"{label}_invalid") from None
    normalized = " ".join(unicodedata.normalize("NFC", value).split())
    if not normalized:
        raise FindingMatchSuggestionRefused(f"{label}_invalid")
    return normalized


def _links(
    pairs: Sequence[ApprovedSheetPair], *, comparison_id: str,
    link_revision: int, source_uid: str, target_uid: str,
    source_pages: int, target_pages: int,
) -> dict[int, tuple[int, str]]:
    if not isinstance(pairs, (tuple, list)) or not 1 <= len(pairs) <= MAX_PAIRS:
        raise FindingMatchSuggestionRefused("approved_pairs_invalid")
    mapped: dict[int, tuple[int, str]] = {}
    target_seen: set[int] = set()
    link_seen: set[str] = set()
    for pair in pairs:
        if not isinstance(pair, ApprovedSheetPair):
            raise FindingMatchSuggestionRefused("approved_pair_invalid")
        _id(pair.sheet_link_id, SheetLinkId, "sheet_link_id")
        if type(pair.link_revision) is not int or pair.link_revision < 1:
            raise FindingMatchSuggestionRefused("approved_pair_revision_invalid")
        if (
            pair.comparison_id != comparison_id
            or pair.link_revision != link_revision
            or pair.source_version_uid != source_uid
            or pair.target_version_uid != target_uid
        ):
            raise FindingMatchSuggestionRefused("approved_pair_binding_mismatch")
        if (
            type(pair.source_page_number) is not int
            or type(pair.target_page_number) is not int
            or not 1 <= pair.source_page_number <= source_pages
            or not 1 <= pair.target_page_number <= target_pages
        ):
            raise FindingMatchSuggestionRefused("approved_pair_page_invalid")
        if (
            pair.sheet_link_id in link_seen
            or pair.source_page_number in mapped
            or pair.target_page_number in target_seen
        ):
            raise FindingMatchSuggestionRefused("approved_pairs_not_one_to_one")
        link_seen.add(pair.sheet_link_id)
        target_seen.add(pair.target_page_number)
        mapped[pair.source_page_number] = (pair.target_page_number, pair.sheet_link_id)
    return mapped


def _findings(
    findings: Sequence[FindingForMatch], *, version_uid: str,
    run_id: str, page_count: int,
) -> tuple[FindingForMatch, ...]:
    if not isinstance(findings, (tuple, list)) or len(findings) > MAX_FINDINGS_PER_RUN:
        raise FindingMatchSuggestionRefused("findings_invalid")
    seen_findings: set[str] = set()
    seen_observations: set[str] = set()
    for finding in findings:
        if not isinstance(finding, FindingForMatch):
            raise FindingMatchSuggestionRefused("finding_invalid")
        _id(finding.finding_uid, FindingUid, "finding_uid")
        _id(finding.finding_observation_id, FindingObservationId, "finding_observation_id")
        _id(finding.run_id, RunId, "finding_run_id")
        _id(finding.version_uid, VersionUid, "finding_version_uid")
        if finding.version_uid != version_uid or finding.run_id != run_id:
            raise FindingMatchSuggestionRefused("finding_source_mismatch")
        if finding.finding_uid in seen_findings or finding.finding_observation_id in seen_observations:
            raise FindingMatchSuggestionRefused("finding_duplicate")
        seen_findings.add(finding.finding_uid)
        seen_observations.add(finding.finding_observation_id)
        _normalized(finding.category, "category", 64)
        _normalized(finding.finding_text, "finding_text", 4000)
        if (
            not isinstance(finding.evidence, tuple)
            or not 1 <= len(finding.evidence) <= MAX_EVIDENCE_PER_FINDING
        ):
            raise FindingMatchSuggestionRefused("finding_evidence_invalid")
        seen_quotes: set[tuple[int, str]] = set()
        for evidence in finding.evidence:
            if not isinstance(evidence, FindingQuote):
                raise FindingMatchSuggestionRefused("finding_evidence_invalid")
            if type(evidence.page_number) is not int or not 1 <= evidence.page_number <= page_count:
                raise FindingMatchSuggestionRefused("finding_evidence_page_invalid")
            key = (evidence.page_number, _normalized(evidence.quote, "quote", 2000))
            if key in seen_quotes:
                raise FindingMatchSuggestionRefused("finding_evidence_duplicate")
            seen_quotes.add(key)
    return tuple(findings)


def _key(
    finding: FindingForMatch, *, page_links: dict[int, tuple[int, str]] | None,
) -> tuple[str, str, tuple[tuple[int, str], ...]] | None:
    coordinates: list[tuple[int, str]] = []
    for evidence in finding.evidence:
        page = evidence.page_number
        if page_links is not None:
            link = page_links.get(page)
            if link is None:
                return None
            page = link[0]
        coordinates.append((page, _normalized(evidence.quote, "quote", 2000)))
    return (
        finding.category,
        _normalized(finding.finding_text, "finding_text", 4000),
        tuple(sorted(coordinates)),
    )


def suggest_exact_finding_matches(
    *,
    version_pair: OrderedVersionPair,
    comparison_id: str,
    link_revision: int,
    approved_pairs: Sequence[ApprovedSheetPair],
    source_run_id: str,
    target_run_id: str,
    source_findings: Sequence[FindingForMatch],
    target_findings: Sequence[FindingForMatch],
) -> tuple[FindingMatchSuggestion, ...]:
    """Suggest unique exact issue+quote matches across approved page links.

    Ambiguous or unlinked findings produce no suggestion. No absent finding is
    marked fixed, no decision is carried, and no link is approved here.
    """
    if not isinstance(version_pair, OrderedVersionPair):
        raise FindingMatchSuggestionRefused("version_pair_invalid")
    source, target = version_pair.source, version_pair.target
    if (
        source.version_uid == target.version_uid
        or source.document_uid != version_pair.document_uid
        or target.document_uid != version_pair.document_uid
        or source.project_uid != version_pair.project_uid
        or target.project_uid != version_pair.project_uid
        or type(source.version_ordinal) is not int
        or type(target.version_ordinal) is not int
        or source.version_ordinal >= target.version_ordinal
        or type(source.page_count) is not int
        or type(target.page_count) is not int
        or not 1 <= source.page_count <= 30
        or not 1 <= target.page_count <= 30
    ):
        raise FindingMatchSuggestionRefused("version_pair_invalid")
    _id(comparison_id, ComparisonId, "comparison_id")
    _id(source_run_id, RunId, "source_run_id")
    _id(target_run_id, RunId, "target_run_id")
    if source_run_id == target_run_id:
        raise FindingMatchSuggestionRefused("same_run")
    if type(link_revision) is not int or link_revision < 1:
        raise FindingMatchSuggestionRefused("link_revision_invalid")
    links = _links(
        approved_pairs, comparison_id=comparison_id, link_revision=link_revision,
        source_uid=source.version_uid, target_uid=target.version_uid,
        source_pages=source.page_count, target_pages=target.page_count,
    )
    older = _findings(
        source_findings, version_uid=source.version_uid,
        run_id=source_run_id, page_count=source.page_count,
    )
    newer = _findings(
        target_findings, version_uid=target.version_uid,
        run_id=target_run_id, page_count=target.page_count,
    )
    if {item.finding_uid for item in older} & {item.finding_uid for item in newer}:
        raise FindingMatchSuggestionRefused("finding_identity_crosses_versions")

    source_by_key: dict[tuple, list[FindingForMatch]] = {}
    target_by_key: dict[tuple, list[FindingForMatch]] = {}
    for finding in older:
        key = _key(finding, page_links=links)
        if key is not None:
            source_by_key.setdefault(key, []).append(finding)
    for finding in newer:
        key = _key(finding, page_links=None)
        if key is not None:
            target_by_key.setdefault(key, []).append(finding)
    suggestions: list[FindingMatchSuggestion] = []
    for key in source_by_key.keys() & target_by_key.keys():
        if len(source_by_key[key]) != 1 or len(target_by_key[key]) != 1:
            continue
        old, new = source_by_key[key][0], target_by_key[key][0]
        link_ids = tuple(sorted({links[item.page_number][1] for item in old.evidence}))
        body = {
            "algorithm": ALGORITHM,
            "comparison_id": comparison_id,
            "link_revision": link_revision,
            "source_version_uid": source.version_uid,
            "target_version_uid": target.version_uid,
            "source_run_id": source_run_id,
            "target_run_id": target_run_id,
            "source": asdict(old),
            "target": asdict(new),
            "matched_sheet_link_ids": link_ids,
        }
        digest = hashlib.sha256(json.dumps(
            body, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        suggestions.append(FindingMatchSuggestion(
            ALGORITHM, comparison_id, link_revision, source.version_uid,
            target.version_uid, old.finding_uid, new.finding_uid,
            old.finding_observation_id, new.finding_observation_id,
            link_ids, digest,
        ))
    return tuple(sorted(suggestions, key=lambda item: item.target_finding_uid))


__all__ = [
    "FindingForMatch", "FindingMatchSuggestion", "FindingMatchSuggestionRefused",
    "FindingQuote", "suggest_exact_finding_matches",
]
