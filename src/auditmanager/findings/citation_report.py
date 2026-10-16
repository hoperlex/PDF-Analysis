"""Unserved, read-only W57a report facts from one consistent transaction.

The caller owns authorization, a registered v3 profile identity and a
repeatable-read transaction. This module does not expose an API route.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.findings.citation_reader import (
    VerifiedFindingPartitions,
    read_verified_citations,
)
from auditmanager.findings.grounding import UngroundedReason
from auditmanager.shared.errors import ErrorCode


class CitationReportRefused(ValueError):
    """Persisted context cannot support a verified v3 report."""


@dataclass(frozen=True, slots=True)
class VerifiedCitationReport:
    run_id: str
    norms_snapshot_id: str
    norm_retrieval_set_id: str
    status: str
    findings: tuple[VerifiedFindingPartitions, ...]
    withheld_by_reason: tuple[tuple[str, int], ...]
    textless_pages: tuple[int, ...]
    error_code: str | None


_CONTEXT = text("""
    SELECT r.run_id, r.version_uid, r.analysis_profile_id,
           r.prompt_bundle_id, r.provider_mode, r.state AS run_state,
           r.norms_snapshot_id, r.norm_retrieval_set_id,
           v.page_count, v.textless_pages
      FROM audit_run r
      JOIN document_version v ON v.version_uid = r.version_uid
     WHERE r.run_id = :run_id AND r.version_uid = :version_uid
       AND r.analysis_profile_id = :profile_id
""")

_DIAGNOSTICS = text("""
    SELECT finding_observation_id, run_id, stage_id, finding_uid, grounded,
           ungrounded_reason, analysis_profile_id, prompt_bundle_id, provider_mode
      FROM finding_observation
     WHERE run_id = :run_id AND grounded = false
     ORDER BY finding_observation_id COLLATE "C"
""")

_STAGES = text("""
    SELECT stage_id, status, error
      FROM stage_result
     WHERE run_id = :run_id
     ORDER BY stage_id COLLATE "C"
""")


def read_verified_citation_report(
    session: Session, *, run_id: str, version_uid: str, profile_id: str,
) -> VerifiedCitationReport:
    """Combine certified citations and report context from the same DB snapshot."""
    citations = read_verified_citations(
        session, run_id=run_id, version_uid=version_uid, profile_id=profile_id,
    )
    context_rows = session.execute(_CONTEXT, {
        "run_id": run_id, "version_uid": version_uid, "profile_id": profile_id,
    }).mappings().all()
    if len(context_rows) != 1:
        raise CitationReportRefused("report_context_missing_or_duplicate")
    context = dict(context_rows[0])
    if (context["run_id"] != citations.run_id
            or context["version_uid"] != citations.version_uid
            or context["analysis_profile_id"] != profile_id
            or context["norms_snapshot_id"] != citations.norms_snapshot_id
            or context["norm_retrieval_set_id"] != citations.norm_retrieval_set_id
            or context["run_state"] != citations.run_state
            or not isinstance(context["prompt_bundle_id"], str)
            or not context["prompt_bundle_id"]
            or context["provider_mode"] not in {"live", "recorded"}):
        raise CitationReportRefused("report_authority_mismatch")
    pages = context["textless_pages"]
    page_count = context["page_count"]
    if (type(page_count) is not int or page_count < 1
            or not isinstance(pages, (list, tuple))
            or any(type(page) is not int or page < 1 or page > page_count
                   for page in pages)
            or tuple(pages) != tuple(sorted(set(pages)))):
        raise CitationReportRefused("textless_page_context_unavailable")

    counts: Counter[str] = Counter()
    seen_diagnostics: set[str] = set()
    for row_ in session.execute(_DIAGNOSTICS, {"run_id": run_id}).mappings().all():
        row = dict(row_)
        observation_id = row["finding_observation_id"]
        reason = row["ungrounded_reason"]
        if (not isinstance(observation_id, str) or not observation_id
                or observation_id in seen_diagnostics
                or row["run_id"] != run_id or row["stage_id"] != "text_analysis"
                or row["finding_uid"] is not None or row["grounded"] is not False
                or row["analysis_profile_id"] != profile_id
                or row["prompt_bundle_id"] != context["prompt_bundle_id"]
                or row["provider_mode"] != context["provider_mode"]
                or reason not in {item.value for item in UngroundedReason}):
            raise CitationReportRefused("diagnostic_provenance_invalid")
        seen_diagnostics.add(observation_id)
        counts[reason] += 1

    stages = [dict(row) for row in session.execute(
        _STAGES, {"run_id": run_id}
    ).mappings().all()]
    if (not stages or len({row["stage_id"] for row in stages}) != len(stages)
            or any(row["status"] not in {"succeeded", "partial", "failed", "skipped"}
                   for row in stages)
            or any(row["status"] in {"failed", "skipped"} for row in stages)
            or sum(row["stage_id"] == "norm_verification"
                   and row["status"] == "succeeded" for row in stages) != 1):
        raise CitationReportRefused("report_stage_status_invalid")
    partial = [row for row in stages if row["status"] == "partial"]
    if (context["run_state"] == "published" and partial) or (
        context["run_state"] == "partial" and not partial
    ):
        raise CitationReportRefused("report_terminal_status_invalid")
    error_code = None
    if partial:
        if any(not isinstance(row["error"], dict) for row in partial):
            raise CitationReportRefused("partial_stage_error_missing")
        codes = {row["error"].get("code") for row in partial}
        if len(codes) != 1:
            raise CitationReportRefused("partial_stage_error_ambiguous")
        candidate = next(iter(codes))
        if not isinstance(candidate, str) or candidate not in {item.value for item in ErrorCode}:
            raise CitationReportRefused("partial_stage_error_invalid")
        error_code = candidate
    return VerifiedCitationReport(
        run_id=run_id, norms_snapshot_id=citations.norms_snapshot_id,
        norm_retrieval_set_id=citations.norm_retrieval_set_id,
        status="complete" if context["run_state"] == "published" else "partial",
        findings=citations.findings,
        withheld_by_reason=tuple(sorted(counts.items())),
        textless_pages=tuple(pages), error_code=error_code,
    )


__all__ = [
    "CitationReportRefused", "VerifiedCitationReport", "read_verified_citation_report",
]
