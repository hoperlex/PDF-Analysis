"""The composed journey: figures, decisions, idempotency and restart.

Every module passed its own suite. This file is the first to run them in one sequence
and assert on what came out. The version is seeded through ``DocumentRepository`` with
the contract's manifest role, because ``IngestService`` cannot currently produce a
runnable version -- see ``test_manifest_role_seam.py``, which owns that defect and is
red. Nothing here masks it: these tests assert other properties.
"""

from __future__ import annotations

import csv
import io

import pytest
from sqlalchemy import text


@pytest.fixture(scope="module")
def composed_run(journey_harness, session_factory, blob_store, recorded_adapter, provider_config):
    """One journey, shared by the module: project, version, run, four stages, gate."""
    h = journey_harness
    with session_factory() as session:
        seed = h.seed_version_with_contract_manifest(session, blob_store, h.new_key("figures"))
        run_id = h.run_from_seed(
            session,
            seed,
            blob_store=blob_store,
            adapter=recorded_adapter,
            provider_config=provider_config,
            declared_provider_mode="recorded",
            run_key=h.new_key("run"),
        )
        yield {**seed, "run_id": run_id}


def test_run_reaches_published_with_no_degradation(composed_run, session):
    row = session.execute(
        text("SELECT state, degradation_set, terminal_reason FROM audit_run WHERE run_id = :r"),
        {"r": composed_run["run_id"]},
    ).mappings().one()
    assert row["state"] == "published"
    assert not row["degradation_set"], f"degradation set is {row['degradation_set']!r}"
    assert row["terminal_reason"] is None


def test_all_four_pc01_stages_succeeded(composed_run, session):
    from auditmanager.runs import PC01_STAGES

    observed = dict(
        session.execute(
            text("SELECT stage_id, status FROM stage_result WHERE run_id = :r"),
            {"r": composed_run["run_id"]},
        ).all()
    )
    assert set(observed) == set(PC01_STAGES)
    assert set(observed.values()) == {"succeeded"}, observed


def test_three_findings_published_through_the_gate(composed_run, session):
    from auditmanager.findings import published_findings

    findings = published_findings(session, composed_run["run_id"])
    assert len(findings) == 3, f"expected 3 published findings, got {len(findings)}"
    for row in findings:
        assert row.project_uid == composed_run["project_uid"]
        assert row.version_uid == composed_run["version_uid"]
        assert row.run_id == composed_run["run_id"]


def test_every_published_finding_carries_grounded_evidence(composed_run, session):
    """Publication is only through the gate: no published finding may lack evidence."""
    orphans = session.execute(
        text(
            "SELECT o.finding_observation_id FROM finding_observation o "
            "LEFT JOIN finding_evidence e "
            "       ON e.finding_observation_id = o.finding_observation_id "
            "WHERE o.run_id = :r AND o.grounded IS TRUE AND e.finding_observation_id IS NULL"
        ),
        {"r": composed_run["run_id"]},
    ).scalars().all()
    assert not orphans, f"grounded observations with no evidence row: {orphans}"

    ungrounded_but_published = session.execute(
        text(
            "SELECT o.finding_observation_id FROM finding_observation o "
            "JOIN finding f ON f.finding_uid = o.finding_uid "
            "WHERE o.run_id = :r AND o.grounded IS NOT TRUE"
        ),
        {"r": composed_run["run_id"]},
    ).scalars().all()
    assert not ungrounded_but_published, (
        f"an ungrounded observation reached a finding: {ungrounded_but_published}"
    )


def test_decision_ledger_is_append_only_and_projects_the_latest(composed_run, session, journey_harness):
    """Accept one, reject another, then append a later comment to the accepted one."""
    from auditmanager.decisions import current_verdict, decision_history, record_decision
    from auditmanager.findings import published_findings

    findings = published_findings(session, composed_run["run_id"])
    accepted, rejected = findings[0], findings[1]

    record_decision(session, finding_uid=str(accepted.finding_uid),
                    finding_observation_id=str(accepted.finding_observation_id),
                    event_type="accept", comment="verified against the page",
                    author_label="reviewer-1")
    record_decision(session, finding_uid=str(rejected.finding_uid),
                    finding_observation_id=str(rejected.finding_observation_id),
                    event_type="reject", comment="different objects",
                    author_label="reviewer-1")
    record_decision(session, finding_uid=str(accepted.finding_uid),
                    finding_observation_id=str(accepted.finding_observation_id),
                    event_type="comment", comment="checked again after restart",
                    author_label="reviewer-1")
    session.commit()

    verdict = current_verdict(session, str(accepted.finding_uid))
    assert verdict.current_verdict == "accepted", (
        "a later comment must not change the verdict it was appended to"
    )
    assert verdict.latest_comment == "checked again after restart"
    assert verdict.decision_event_count == 2

    history = decision_history(session, str(accepted.finding_uid))
    assert [event.event_type for event in history] == ["accept", "comment"], (
        "the ledger must keep the earlier decision visible, not overwrite it"
    )
    assert current_verdict(session, str(rejected.finding_uid)).current_verdict == "rejected"


def test_csv_is_five_rows_of_seventeen_columns_and_stable(composed_run, session):
    from auditmanager.exports import COLUMNS, export_run_csv

    first = export_run_csv(session, composed_run["run_id"])
    second = export_run_csv(session, composed_run["run_id"])
    assert first.content == second.content, "two exports of an unchanged run must be identical"
    # The literal bytes, never the module's BOM constant: importing it makes this
    # assertion vacuously true the day the constant becomes empty.
    assert first.content.startswith(b"\xef\xbb\xbf")
    assert first.content_type == "text/csv; charset=utf-8"

    rows = list(csv.reader(io.StringIO(first.content[3:].decode("utf-8"))))
    rows = [row for row in rows if row]
    header, data = rows[0], rows[1:]
    assert tuple(header) == tuple(COLUMNS)
    assert len(header) == 17
    assert len(data) == 5, f"expected 5 data rows, got {len(data)}"

    position = {name: index for index, name in enumerate(header)}
    for row in data:
        assert row[position["run_id"]] == composed_run["run_id"]
        assert row[position["version_uid"]] == composed_run["version_uid"]
        assert row[position["project_uid"]] == composed_run["project_uid"]
        assert row[position["run_state"]] == "published"


def test_no_internal_address_reaches_the_export(composed_run, session):
    import os

    from auditmanager.exports import export_run_csv

    content = export_run_csv(session, composed_run["run_id"]).content.decode("utf-8")
    for forbidden in ("s3://", os.environ["S3_BUCKET"], "blob_"):
        assert forbidden not in content, f"{forbidden!r} leaked into the CSV"


def test_state_survives_a_new_engine_and_session(composed_run, journey_harness, session_factory):
    """Step 6, at the level this suite can reach: canonical state is in PostgreSQL and
    MinIO, not in a process, so a fresh engine must resolve the same journey.

    The process-level restart -- stopping and starting the application and the execution
    process -- is exercised by ``make down && make up`` in the gate, not from inside a
    test that would have to kill its own interpreter.
    """
    import os

    from sqlalchemy.orm import sessionmaker

    from auditmanager.exports import export_run_csv
    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.shared.db.engine import create_database_engine

    with session_factory() as before_session:
        before = export_run_csv(before_session, composed_run["run_id"]).content

    fresh = create_database_engine(
        DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"]))
    )
    try:
        with sessionmaker(bind=fresh.engine, future=True)() as after_session:
            state = after_session.execute(
                text("SELECT state FROM audit_run WHERE run_id = :r"),
                {"r": composed_run["run_id"]},
            ).scalar_one()
            findings = after_session.execute(
                text("SELECT count(*) FROM finding_observation WHERE run_id = :r"),
                {"r": composed_run["run_id"]},
            ).scalar_one()
            after = export_run_csv(after_session, composed_run["run_id"]).content
    finally:
        fresh.engine.dispose()

    assert state == "published"
    assert findings == 3
    assert after == before, "the CSV did not survive a new engine byte-identically"
