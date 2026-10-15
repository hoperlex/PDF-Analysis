"""Pure projection of complete finding reads into the W57b XLSX writer input.

The caller owns one consistent database read, page-label resolution and the
sealed export authorization. This module neither queries nor repairs data.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditmanager.exports.xlsx.writer import (
    Citation,
    FindingMember,
    FindingRow,
    SEVERITIES,
    WorkbookInput,
)


_VERDICTS = frozenset({"pending", "accepted", "rejected", "needs_manual_review"})


@dataclass(frozen=True, slots=True)
class RunRead:
    project_uid: str
    version_uid: str
    run_id: str
    profile_id: str
    snapshot_key: str
    attribution: str


@dataclass(frozen=True, slots=True)
class EvidenceLocationRead:
    evidence_ordinal: int
    page_number: int
    page_label: str


@dataclass(frozen=True, slots=True)
class ObservationRead:
    finding_observation_id: str
    finding_uid: str
    category: str
    finding_text: str
    recommendation: str
    proposed_severity: str | None
    evidence: tuple[EvidenceLocationRead, ...]


@dataclass(frozen=True, slots=True)
class VerdictRead:
    finding_uid: str
    current_verdict: str
    decided_severity: str | None
    latest_comment: str | None


@dataclass(frozen=True, slots=True)
class CitationRead:
    document: str
    clause: str
    quote: str


@dataclass(frozen=True, slots=True)
class FindingRead:
    finding_uid: str
    run_id: str
    category: str
    canonical_observation_id: str
    member_observation_ids: tuple[str, ...]
    observations: tuple[ObservationRead, ...]
    verdict: VerdictRead
    citations: tuple[CitationRead, ...]


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _locations(observation: ObservationRead) -> str:
    if not isinstance(observation.evidence, tuple) or not observation.evidence:
        raise ValueError("xlsx_projection_evidence_missing")
    labels: list[str] = []
    for expected, item in enumerate(observation.evidence):
        if (
            not isinstance(item, EvidenceLocationRead)
            or type(item.evidence_ordinal) is not int
            or item.evidence_ordinal != expected
            or type(item.page_number) is not int
            or item.page_number < 1
            or not _text(item.page_label)
        ):
            raise ValueError("xlsx_projection_evidence_invalid")
        labels.append(item.page_label)
    return "\n".join(labels)


def _finding_row(finding: FindingRead, run_id: str) -> FindingRow:
    if (
        not isinstance(finding, FindingRead)
        or not _text(finding.finding_uid)
        or finding.run_id != run_id
        or not _text(finding.category)
        or not _text(finding.canonical_observation_id)
        or not isinstance(finding.observations, tuple)
        or not isinstance(finding.member_observation_ids, tuple)
        or not isinstance(finding.citations, tuple)
    ):
        raise ValueError("xlsx_projection_finding_invalid")

    by_id: dict[str, ObservationRead] = {}
    for observation in finding.observations:
        if (
            not isinstance(observation, ObservationRead)
            or not _text(observation.finding_observation_id)
            or observation.finding_observation_id in by_id
            or observation.finding_uid != finding.finding_uid
            or observation.category != finding.category
            or not _text(observation.finding_text)
            or not isinstance(observation.recommendation, str)
            or (
                observation.proposed_severity is not None
                and observation.proposed_severity not in SEVERITIES
            )
        ):
            raise ValueError("xlsx_projection_observation_invalid")
        by_id[observation.finding_observation_id] = observation

    canonical = by_id.get(finding.canonical_observation_id)
    if canonical is None:
        raise ValueError("xlsx_projection_canonical_missing")
    members = finding.member_observation_ids
    if (
        any(not _text(member_id) for member_id in members)
        or len(set(members)) != len(members)
        or set(members) != by_id.keys() - {finding.canonical_observation_id}
    ):
        raise ValueError("xlsx_projection_member_partition_invalid")

    verdict = finding.verdict
    if (
        not isinstance(verdict, VerdictRead)
        or verdict.finding_uid != finding.finding_uid
        or not isinstance(verdict.current_verdict, str)
        or verdict.current_verdict not in _VERDICTS
        or (
            verdict.decided_severity is not None
            and verdict.decided_severity not in SEVERITIES
        )
        or (verdict.current_verdict != "accepted" and verdict.decided_severity is not None)
        or (verdict.latest_comment is not None and not isinstance(verdict.latest_comment, str))
    ):
        raise ValueError("xlsx_projection_verdict_invalid")

    citations: list[Citation] = []
    for item in finding.citations:
        if (
            not isinstance(item, CitationRead)
            or not _text(item.document)
            or not isinstance(item.clause, str)
            or not _text(item.quote)
        ):
            raise ValueError("xlsx_projection_citation_invalid")
        citations.append(Citation(item.document, item.clause, item.quote))

    return FindingRow(
        finding_uid=finding.finding_uid,
        sheet_page=_locations(canonical),
        category=finding.category,
        finding_text=canonical.finding_text,
        recommendation=canonical.recommendation,
        decided_severity=verdict.decided_severity,
        proposed_severity=canonical.proposed_severity,
        citations=tuple(citations),
        expert_decision=verdict.current_verdict,
        comment=verdict.latest_comment if verdict.latest_comment is not None else "",
        members=tuple(
            FindingMember(
                sheet_page=_locations(by_id[member_id]),
                note=by_id[member_id].finding_text,
            )
            for member_id in members
        ),
    )


def project_workbook(run: RunRead, findings: tuple[FindingRead, ...]) -> WorkbookInput:
    """Project one row per finding, retaining supplied finding and member order.

    ``findings`` must be a complete, ordered read for ``run``. Missing canonical
    identity, member or page label is an error; there is no v1 fallback.
    """
    if (
        not isinstance(run, RunRead)
        or not all(_text(value) for value in (
            run.project_uid, run.version_uid, run.run_id, run.profile_id,
        ))
        or not isinstance(run.snapshot_key, str)
        or not isinstance(run.attribution, str)
        or not isinstance(findings, tuple)
    ):
        raise ValueError("xlsx_projection_run_invalid")
    seen: set[str] = set()
    rows: list[FindingRow] = []
    for finding in findings:
        row = _finding_row(finding, run.run_id)
        if row.finding_uid in seen:
            raise ValueError("xlsx_projection_finding_duplicate")
        seen.add(row.finding_uid)
        rows.append(row)
    return WorkbookInput(
        project_uid=run.project_uid,
        version_uid=run.version_uid,
        run_id=run.run_id,
        profile_id=run.profile_id,
        snapshot_key=run.snapshot_key,
        attribution=run.attribution,
        findings=tuple(rows),
    )


__all__ = [
    "CitationRead",
    "EvidenceLocationRead",
    "FindingRead",
    "ObservationRead",
    "RunRead",
    "VerdictRead",
    "project_workbook",
]
