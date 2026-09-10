"""Columns 14-17: the current-verdict projection, as the CSV carries it.

The four decision columns are the only ones sourced from a **view** rather than a table,
and the only ones that can change without a run being re-executed. So they get their own
module: the rest of the contract is about a run's output, and this is about what an
expert did to it afterwards.

``finding_current_verdict`` is the single definition of the projection (P02 §5.4). This
suite reads the CSV and the view and requires them to agree; neither is recomputed here,
because a test that recomputed the rule would be asserting its own arithmetic.
"""

from __future__ import annotations

import csv
import io

from sqlalchemy.orm import Session

from auditmanager.decisions import current_verdict, record_decision
from auditmanager.exports import BOM, export_run_csv
from auditmanager.findings import published_findings
from auditmanager.runs import execute_run, start_audit_run


def _rows(content: bytes) -> list[dict[str, str]]:
    body = content[len(BOM) :].decode("utf-8")
    reader = csv.reader(io.StringIO(body, newline=""), delimiter=",", quotechar='"')
    parsed = list(reader)
    return [dict(zip(parsed[0], row)) for row in parsed[1:]]


def _published_run(session, seeded, blob_store, recorded_adapter, provider_config, key):
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=key,
    )
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )
    return started.run_id


def test_an_accepted_finding_carries_its_verdict_into_the_csv(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    run_id = _published_run(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("accepted")
    )
    findings = published_findings(session, run_id)
    assert findings
    judged = findings[0]

    event = record_decision(
        session,
        finding_uid=judged.finding_uid,
        finding_observation_id=judged.finding_observation_id,
        event_type="accept",
        comment="Подтверждено при проверке.",
    )

    rows = _rows(export_run_csv(session, run_id).content)
    judged_rows = [row for row in rows if row["finding_uid"] == judged.finding_uid]
    other_rows = [row for row in rows if row["finding_uid"] != judged.finding_uid]
    assert judged_rows

    projection = current_verdict(session, judged.finding_uid)
    assert projection is not None
    for row in judged_rows:
        assert row["current_verdict"] == projection.current_verdict == "accepted"
        assert row["latest_comment"] == "Подтверждено при проверке."
        assert row["latest_decision_id"] == str(event.decision_id)
        assert row["decision_recorded_at"] != ""
        # RFC 3339 with a Z offset, so a spreadsheet reads one instant.
        assert row["decision_recorded_at"].endswith("Z")

    # A decision on one finding must not colour any other finding's rows.
    for row in other_rows:
        assert row["current_verdict"] == "pending"
        assert row["latest_decision_id"] == ""


def test_a_later_comment_moves_the_timestamp_without_moving_the_verdict(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """§5.4: ``latest_decision_id`` tracks any event; the verdict tracks only verdicts."""
    run_id = _published_run(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("comment-after")
    )
    judged = published_findings(session, run_id)[0]

    record_decision(
        session,
        finding_uid=judged.finding_uid,
        finding_observation_id=judged.finding_observation_id,
        event_type="reject",
    )
    after_verdict = _rows(export_run_csv(session, run_id).content)
    verdict_row = next(
        row for row in after_verdict if row["finding_uid"] == judged.finding_uid
    )
    assert verdict_row["current_verdict"] == "rejected"

    commented = record_decision(
        session,
        finding_uid=judged.finding_uid,
        finding_observation_id=judged.finding_observation_id,
        event_type="comment",
        comment="Требует повторного рассмотрения.",
    )
    after_comment = _rows(export_run_csv(session, run_id).content)
    comment_row = next(
        row for row in after_comment if row["finding_uid"] == judged.finding_uid
    )

    assert comment_row["current_verdict"] == "rejected", "a comment changed the verdict"
    assert comment_row["latest_comment"] == "Требует повторного рассмотрения."
    assert comment_row["latest_decision_id"] == str(commented.decision_id)
    assert comment_row["decision_recorded_at"] != verdict_row["decision_recorded_at"]


def test_the_export_changes_when_a_decision_is_appended_and_is_stable_otherwise(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """Byte-identity is about an *unchanged* run, not about a frozen file.

    Without this, "two exports are byte-identical" could be satisfied by an export that
    ignored the projection entirely.
    """
    run_id = _published_run(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("stability")
    )
    before = export_run_csv(session, run_id).content
    assert export_run_csv(session, run_id).content == before

    judged = published_findings(session, run_id)[0]
    record_decision(
        session,
        finding_uid=judged.finding_uid,
        finding_observation_id=judged.finding_observation_id,
        event_type="accept",
    )

    after = export_run_csv(session, run_id).content
    assert after != before, "appending a decision did not reach the export"
    assert export_run_csv(session, run_id).content == after


def test_a_quote_containing_a_comma_or_quote_survives_the_round_trip(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """RFC 4180 quoting, exercised through a comment the expert actually typed.

    The corpus quotations happen not to contain a delimiter, so the case is reached
    through the one free-text column a person fills in. A field carrying a comma, a
    double quote and a newline must come back through a conforming reader unchanged.
    """
    run_id = _published_run(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("quoting")
    )
    judged = published_findings(session, run_id)[0]
    hostile = 'Сравнить: "II" и "III", затем\nуточнить у ГИПа.'

    record_decision(
        session,
        finding_uid=judged.finding_uid,
        finding_observation_id=judged.finding_observation_id,
        event_type="comment",
        comment=hostile,
    )

    rows = _rows(export_run_csv(session, run_id).content)
    row = next(row for row in rows if row["finding_uid"] == judged.finding_uid)
    assert row["latest_comment"] == hostile

    # And the record count is unchanged: the embedded newline did not split a row.
    assert len(rows) == len(
        _rows(export_run_csv(session, run_id).content)
    )
    assert len({r["finding_observation_id"] for r in rows}) >= 1
