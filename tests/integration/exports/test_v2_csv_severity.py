"""W56a CSV reads the independent decision view and the canonical observation."""

from __future__ import annotations

import csv
import io
from dataclasses import replace

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.decisions import record_decision
from auditmanager.exports import BOM, export_run_csv
from auditmanager.exports.query import ExportRow
from auditmanager.exports.serializer import COLUMNS, render_csv
from auditmanager.findings import published_findings
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.identity import FindingObservationId


def _rows(content: bytes) -> list[dict[str, str]]:
    parsed = list(csv.reader(io.StringIO(content[len(BOM) :].decode("utf-8"), newline="")))
    return [dict(zip(parsed[0], row, strict=True)) for row in parsed[1:]]


def test_appended_severity_cells_keep_the_od11_prefix_and_empty_legacy_values() -> None:
    base = ExportRow(
        project_uid="prj_1",
        document_uid="doc_1",
        version_uid="ver_1",
        run_id="run_1",
        run_state="succeeded",
        provider_mode="recorded",
        finding_uid="fnd_1",
        finding_observation_id="fobs_1",
        category="fire_safety",
        finding_text="текст",
        recommendation_text=None,
        evidence_page=1,
        evidence_quote="цитата",
        current_verdict="pending",
        latest_comment=None,
        latest_decision_id=None,
        decision_recorded_at=None,
        evidence_ordinal=0,
    )
    assert COLUMNS[-2:] == ("severity", "severity_proposed")
    assert _rows(render_csv((base,)))[0]["severity"] == ""
    assert _rows(render_csv((base,)))[0]["severity_proposed"] == ""
    decided = replace(base, severity="critical", severity_proposed="economic")
    row = _rows(render_csv((decided,)))[0]
    assert row["severity"] == "critical"
    assert row["severity_proposed"] == "economic"


def test_csv_uses_canonical_proposal_and_current_expert_decision(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
) -> None:
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("w56a-csv-severity"),
    )
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )
    finding = published_findings(session, started.run_id)[0]
    original = str(finding.finding_observation_id)
    canonical = str(FindingObservationId.new())
    member = str(FindingObservationId.new())
    before = next(
        row
        for row in _rows(export_run_csv(session, started.run_id).content)
        if row["finding_uid"] == str(finding.finding_uid)
    )
    assert before["severity"] == before["severity_proposed"] == ""

    # `finding_observation` refuses UPDATE ("correcting data creates a new entity with a new
    # identifier"), so the proposing canonical observation and the member are new rows
    # copied from the published one, and the finding names the canonical one
    # (`W57B-NORMS-CATALOGUE-XLSX-01`: the earlier UPDATE of the published row could never
    # pass the 0002 immutability trigger).
    for observation, text_value, severity in (
        (canonical, None, "economic"),
        (member, "member text", "critical"),
    ):
        session.execute(
            text(
                "INSERT INTO finding_observation (finding_observation_id, run_id, "
                "finding_uid, stage_id, category, finding_text, recommendation_text, "
                "grounded, analysis_profile_id, prompt_bundle_id, provider_mode, "
                "proposed_severity) "
                "SELECT :observation, run_id, finding_uid, stage_id, category, "
                "COALESCE(:text_value, finding_text), recommendation_text, TRUE, "
                "analysis_profile_id, prompt_bundle_id, provider_mode, :severity "
                "FROM finding_observation WHERE finding_observation_id = :original"
            ),
            {"observation": observation, "text_value": text_value, "severity": severity,
             "original": original},
        )
        session.execute(
            text(
                "INSERT INTO finding_evidence (finding_observation_id, evidence_ordinal, "
                "page_number, quote, char_start, char_end) "
                "SELECT :observation, 0, page_number, quote, char_start, char_end "
                "FROM finding_evidence WHERE finding_observation_id = :original "
                "ORDER BY evidence_ordinal LIMIT 1"
            ),
            {"observation": observation, "original": original},
        )
    session.execute(
        text(
            "UPDATE finding SET canonical_observation_id = :canonical "
            "WHERE finding_uid = :finding"
        ),
        {"canonical": canonical, "finding": finding.finding_uid},
    )
    record_decision(
        session,
        finding_uid=finding.finding_uid,
        finding_observation_id=canonical,
        event_type="accept",
        severity="operational",
        author_label="expert",
        author_user_uid=None,
    )

    rows = [
        row
        for row in _rows(export_run_csv(session, started.run_id).content)
        if row["finding_uid"] == str(finding.finding_uid)
    ]
    assert rows
    assert {row["finding_observation_id"] for row in rows} == {canonical}
    assert {row["severity_proposed"] for row in rows} == {"economic"}
    assert {row["severity"] for row in rows} == {"operational"}

    record_decision(
        session,
        finding_uid=finding.finding_uid,
        finding_observation_id=canonical,
        event_type="reject",
        author_label="expert",
        author_user_uid=None,
    )
    rejected = [
        row
        for row in _rows(export_run_csv(session, started.run_id).content)
        if row["finding_uid"] == str(finding.finding_uid)
    ]
    assert {row["severity"] for row in rejected} == {""}
    assert {row["severity_proposed"] for row in rejected} == {"economic"}
