"""``getRunNormVerification`` for an AR v3 beta Run, from the saved CITE stage (``R-146at``).

Source, and nothing else: the sealed review artifact of the Run (read through
``read_v3_saved_review``, which rechecks the Blob, its digests and the group binding) and the
certified citation partitions of the Run's findings (``read_verified_citation_report`` with the
AR v3 CITE stage as the certifying stage). The two are compared by ``match_published_findings``:
the findings are none or exactly the review's provisional proposals. The report never turns a
withheld or rejected proposal into a finding, and it is a pure function of saved facts, so a
replay of the same Run answers the same report.

``withheld_by_reason`` counts the review's rejected proposals by their grounding reason. The
beta policy's context-only withholding is not a grounding reason and ``UngroundedReason`` is a
closed enum, so those proposals stay counted by the group review only.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.analysis.public import AR_V3_BETA_PROFILE_ID
from auditmanager.findings.public import (
    CitationReadRefused,
    CitationReportRefused,
    UngroundedReason,
    VerifiedFindingPartitions,
    published_finding_evidence,
    read_verified_citation_report,
)
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.v3_published_findings import CITE_STAGE_ID, match_published_findings
from auditmanager.runs.v3_review_reader import read_v3_saved_review
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobMetadataRepository, BlobStore


@dataclass(frozen=True, slots=True)
class V3NormVerification:
    run_id: str
    norms_snapshot_id: str
    norm_retrieval_set_id: str
    status: str
    findings: tuple[VerifiedFindingPartitions, ...]
    withheld_by_reason: tuple[tuple[str, int], ...]
    textless_pages: tuple[int, ...]
    error_code: str | None


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="the AR v3 norm-verification report cannot be verified",
        stage_id=CITE_STAGE_ID, reason=reason,
    )


def _withheld_by_reason(rejected: object) -> tuple[tuple[str, int], ...]:
    known = {reason.value for reason in UngroundedReason}
    if not isinstance(rejected, list):
        raise _refuse("review_rejected_unreadable")
    counts: Counter[str] = Counter()
    for item in rejected:
        reason = item.get("reason") if isinstance(item, dict) else None
        if reason not in known:
            raise _refuse("review_rejected_reason_unknown")
        counts[reason] += 1
    return tuple(sorted(counts.items()))


def read_v3_norm_verification(
    session: Session, run_id: str, *, blob_store: BlobStore,
    runs: RunRepository | None = None,
    blobs: BlobMetadataRepository | None = None,
) -> V3NormVerification:
    """The canonical report of one terminal AR v3 beta Run, or a typed refusal.

    The caller holds one consistent read snapshot. ``not_found`` for a Run that is not an
    AR v3 beta Run is raised by the review reader; every other refusal is
    ``analysis_input_invalid`` with a ``reason``.
    """
    run_repo = runs or RunRepository()
    saved = read_v3_saved_review(
        session, run_id, blob_store=blob_store, runs=run_repo, blobs=blobs,
    )
    run = run_repo.get(session, run_id)
    try:
        report = read_verified_citation_report(
            session, run_id=run_id, version_uid=run.version_uid,
            profile_id=str(AR_V3_BETA_PROFILE_ID), cite_stage_id=CITE_STAGE_ID,
        )
    except (CitationReadRefused, CitationReportRefused) as exc:
        raise _refuse(f"certified_partitions_unverifiable:{exc}") from exc
    match_published_findings(
        report.findings, published_finding_evidence(session, run_id), saved.document,
    )
    return V3NormVerification(
        run_id=report.run_id, norms_snapshot_id=report.norms_snapshot_id,
        norm_retrieval_set_id=report.norm_retrieval_set_id, status=report.status,
        findings=report.findings,
        withheld_by_reason=_withheld_by_reason(saved.document["rejected_proposals"]),
        textless_pages=report.textless_pages, error_code=report.error_code,
    )


__all__ = ["V3NormVerification", "read_v3_norm_verification"]
