"""Prove that the findings of an AR v3 beta Run are exactly the review's provisional proposals.

The sealed review artifact (``ar-v3-beta-citation-review/1``) keeps, for every proposal that
passed both pure gates and cites only provisional topics, its PDF anchors and its norm
citations. The terminal publishes one finding per such proposal (``R-146as``). A reader that
shows either side must be able to say they are the same set, so the comparison lives here once:
the group-review reader, the norm-verification report and the terminal's own post-write check
all call it.

Two states are legitimate and nothing else: a Run with no finding rows (it was closed before
the terminal published findings, or it had nothing to publish) and a Run whose finding rows are
exactly its provisional proposals, one to one, by content. A withheld (context-only or mixed)
proposal and a rejected proposal have no finding; a finding that matches no proposal is a
refusal, never a partial answer.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.orm import Session

from auditmanager.findings.public import (
    CitationReadRefused,
    VerifiedFindingPartitions,
    publication_rows_exist,
    published_finding_evidence,
    read_verified_citations,
)
from auditmanager.shared.errors import DomainError, ErrorCode

CITE_STAGE_ID = "ar_v3_citation_review"


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="the published AR v3 findings differ from the saved review",
        stage_id=CITE_STAGE_ID, reason=reason,
    )


def _proposal_key(entry: Mapping[str, Any]) -> tuple[Any, ...]:
    try:
        evidence = tuple(
            (row["page_number"], row["quote"], row["char_start"], row["char_end"], row["block_id"])
            for row in entry["evidence"]
        )
        citations = tuple(
            (row["document_id"], row["paragraph_id"], row["raw_quote"], row["state"])
            for row in entry["citations"]
        )
    except (KeyError, TypeError) as exc:
        raise _refuse("review_proposal_unreadable") from exc
    return evidence, citations


def _finding_key(
    finding: VerifiedFindingPartitions, evidence_by_observation: Mapping[str, tuple[Any, ...]],
) -> tuple[Any, ...]:
    canonical = finding.canonical
    evidence = evidence_by_observation.get(canonical.finding_observation_id, ())
    return (
        tuple(evidence),
        tuple(
            (item.norm_document_id, item.norm_paragraph_id, item.quote, item.state)
            for item in canonical.citations
        ),
    )


def match_published_findings(
    findings: Sequence[VerifiedFindingPartitions],
    evidence_rows: Sequence[Any],
    document: Mapping[str, Any],
) -> None:
    """Raise unless the findings are none, or exactly the provisional proposals of the review."""
    proposals = document["provisional_citations"]
    if not findings:
        return
    if len(findings) != len(proposals):
        raise _refuse("published_finding_count_differs_from_review")
    if any(finding.merged_observations for finding in findings):
        raise _refuse("published_finding_merged_unexpected")
    by_observation: dict[str, list[Any]] = {}
    for row in sorted(evidence_rows, key=lambda r: (r.finding_observation_id, r.evidence_ordinal)):
        by_observation.setdefault(row.finding_observation_id, []).append(
            (row.page_number, row.quote, row.char_start, row.char_end, row.block_id)
        )
    expected = Counter(_proposal_key(entry) for entry in proposals)
    actual = Counter(
        _finding_key(finding, {k: tuple(v) for k, v in by_observation.items()})
        for finding in findings
    )
    if expected != actual:
        raise _refuse("published_finding_not_in_review")


def check_run_published_findings(
    session: Session, *, run_id: str, version_uid: str, profile_id: str,
    document: Mapping[str, Any],
) -> tuple[VerifiedFindingPartitions, ...]:
    """The reader-side check: no finding rows, or rows that the review explains exactly."""
    if not publication_rows_exist(session, run_id):
        return ()
    try:
        read = read_verified_citations(
            session, run_id=run_id, version_uid=version_uid, profile_id=profile_id,
            cite_stage_id=CITE_STAGE_ID,
        )
    except CitationReadRefused as exc:
        raise _refuse(f"published_findings_unverifiable:{exc}") from exc
    match_published_findings(
        read.findings, published_finding_evidence(session, run_id), document,
    )
    return read.findings


__all__ = ["CITE_STAGE_ID", "check_run_published_findings", "match_published_findings"]
