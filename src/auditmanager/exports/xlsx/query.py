"""Read one run's published findings for the pure XLSX projection.

This is a read adapter, not an export policy or citation resolver. The current
schema stores evidence page numbers but no display labels or finding citations.
Both must be supplied explicitly by the future sealed caller; even an empty
citation set is an explicit value. All reads use the caller's transaction.

**A v1 finding** (`W57B-NORMS-CATALOGUE-XLSX-01`) has no ``canonical_observation_id``: only
the v2 publication writes one, and a v1 publication writes exactly one observation per
finding. Such a finding's single observation is its canonical one, exactly the row the CSV
exports for it (``canonical_observation_id IS NULL OR ...``); a finding with no canonical
identity and more than one observation is still refused. A v1 observation may have no
recommendation; its cell is empty, as the CSV's is.
"""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.exports.xlsx.projection import (
    CitationRead,
    EvidenceLocationRead,
    FindingRead,
    ObservationRead,
    RunRead,
    VerdictRead,
    project_workbook,
)


_RUN = text("""
    SELECT r.run_id, r.project_uid, r.version_uid,
           r.analysis_profile_id, r.norms_snapshot_id,
           s.content_key AS snapshot_key
      FROM audit_run r
      LEFT JOIN norms_snapshot s ON s.norms_snapshot_id = r.norms_snapshot_id
     WHERE r.run_id = :run_id
""")

_FINDINGS = text("""
    SELECT f.finding_uid, f.project_uid, f.version_uid,
           f.allocated_by_run_id, f.category, f.canonical_observation_id,
           o.finding_observation_id, o.run_id AS observation_run_id,
           o.finding_uid AS observation_finding_uid, o.category AS observation_category,
           o.finding_text, o.recommendation_text, o.proposed_severity,
           e.evidence_ordinal, e.page_number,
           cv.current_verdict, cv.decided_severity, cv.latest_comment,
           cv.finding_uid AS verdict_finding_uid
      FROM finding f
      LEFT JOIN finding_observation o ON o.finding_uid = f.finding_uid
      LEFT JOIN finding_evidence e ON e.finding_observation_id = o.finding_observation_id
      LEFT JOIN finding_current_verdict cv ON cv.finding_uid = f.finding_uid
     WHERE f.allocated_by_run_id = :run_id
     ORDER BY f.finding_uid COLLATE "C", o.finding_observation_id COLLATE "C",
              e.evidence_ordinal
""")


def read_xlsx_projection(
    session: Session,
    run_id: str,
    *,
    page_labels: Mapping[int, str],
    citations_by_finding: Mapping[str, tuple[CitationRead, ...]],
    attribution: str,
) -> tuple[RunRead, tuple[FindingRead, ...]] | None:
    """Return complete typed reads, or ``None`` for an absent run.

    The caller must supply verified labels and an explicit citation tuple for
    every finding. The adapter never infers labels from page numbers or treats
    absent citation data as no citations. The caller still owns a consistent
    transaction, role/state enforcement and source verification.
    """
    if (
        not isinstance(run_id, str) or not run_id
        or not isinstance(page_labels, Mapping)
        or not isinstance(citations_by_finding, Mapping)
        or not isinstance(attribution, str) or not attribution.strip()
    ):
        raise ValueError("xlsx_read_inputs_invalid")

    header = session.execute(_RUN, {"run_id": run_id}).mappings().first()
    if header is None:
        return None
    if header["norms_snapshot_id"] is not None and header["snapshot_key"] is None:
        raise ValueError("xlsx_read_snapshot_missing")
    run = RunRead(
        project_uid=header["project_uid"],
        version_uid=header["version_uid"],
        run_id=header["run_id"],
        profile_id=header["analysis_profile_id"],
        snapshot_key=header["snapshot_key"] or "",  # a run may intentionally have no snapshot
        attribution=attribution,
    )
    if run.run_id != run_id:
        raise ValueError("xlsx_read_run_mismatch")

    rows = session.execute(_FINDINGS, {"run_id": run_id}).mappings().all()
    by_finding: dict[str, dict[str, object]] = {}
    for row in rows:
        finding_uid = row["finding_uid"]
        if (
            row["allocated_by_run_id"] != run_id
            or row["project_uid"] != run.project_uid
            or row["version_uid"] != run.version_uid
            or row["finding_observation_id"] is None
            or row["observation_run_id"] != run_id
            or row["observation_finding_uid"] != finding_uid
            or row["observation_category"] != row["category"]
            or row["verdict_finding_uid"] != finding_uid
            or row["evidence_ordinal"] is None
            or row["page_number"] is None
        ):
            raise ValueError("xlsx_read_incomplete_finding")
        page = row["page_number"]
        if type(page) is not int or page not in page_labels:
            raise ValueError("xlsx_read_page_label_missing")
        label = page_labels[page]
        if not isinstance(label, str) or not label.strip():
            raise ValueError("xlsx_read_page_label_invalid")

        entry = by_finding.setdefault(finding_uid, {
            "category": row["category"],
            "canonical": row["canonical_observation_id"],
            "verdict": VerdictRead(
                finding_uid, row["current_verdict"],
                row["decided_severity"], row["latest_comment"],
            ),
            "observations": {},
        })
        if (entry["category"] != row["category"]
                or entry["canonical"] != row["canonical_observation_id"]):
            raise ValueError("xlsx_read_finding_changed")
        verdict = entry["verdict"]
        if verdict != VerdictRead(
            finding_uid, row["current_verdict"],
            row["decided_severity"], row["latest_comment"],
        ):
            raise ValueError("xlsx_read_verdict_changed")
        observations = entry["observations"]
        assert isinstance(observations, dict)
        observation_id = row["finding_observation_id"]
        item = observations.setdefault(observation_id, {
            "text": row["finding_text"],
            "recommendation": row["recommendation_text"],
            "severity": row["proposed_severity"],
            "evidence": [],
        })
        if (item["text"] != row["finding_text"]
                or item["recommendation"] != row["recommendation_text"]
                or item["severity"] != row["proposed_severity"]):
            raise ValueError("xlsx_read_observation_changed")
        evidence = item["evidence"]
        assert isinstance(evidence, list)
        if row["evidence_ordinal"] != len(evidence):
            raise ValueError("xlsx_read_evidence_order_invalid")
        evidence.append(EvidenceLocationRead(row["evidence_ordinal"], page, label))

    if set(citations_by_finding) != set(by_finding):
        raise ValueError("xlsx_read_citation_partition_invalid")
    findings: list[FindingRead] = []
    for finding_uid, entry in by_finding.items():
        citations = citations_by_finding[finding_uid]
        if not isinstance(citations, tuple) or any(
            not isinstance(citation, CitationRead) for citation in citations
        ):
            raise ValueError("xlsx_read_citations_invalid")
        observations = entry["observations"]
        assert isinstance(observations, dict)
        canonical = entry["canonical"]
        if canonical is None and len(observations) == 1:
            canonical = next(iter(observations))  # a v1 finding: see the module docstring
        if canonical is None or canonical not in observations:
            raise ValueError("xlsx_read_canonical_missing")
        reads = tuple(
            ObservationRead(
                finding_observation_id=observation_id,
                finding_uid=finding_uid,
                category=entry["category"],
                finding_text=item["text"],
                recommendation=(
                    "" if item["recommendation"] is None else item["recommendation"]
                ),
                proposed_severity=item["severity"],
                evidence=tuple(item["evidence"]),
            )
            for observation_id, item in observations.items()
        )
        findings.append(FindingRead(
            finding_uid=finding_uid,
            run_id=run_id,
            category=entry["category"],
            canonical_observation_id=canonical,
            member_observation_ids=tuple(
                observation_id for observation_id in observations if observation_id != canonical
            ),
            observations=reads,
            verdict=entry["verdict"],
            citations=citations,
        ))
    result = (run, tuple(findings))
    project_workbook(*result)  # fail closed before handing a partial read to a caller
    return result


__all__ = ["read_xlsx_projection"]
