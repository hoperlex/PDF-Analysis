"""The journey figures, pinned as absolute numbers, through the real upload path.

``test_journey.py`` beside this file drives the same journey and checks that every row
resolves back to it, but almost every figure it asserts is relative: the finding count is
compared against the count the same execution returned, and the CSV is compared against
itself. That is a real cross-check of two surfaces and it is not what this file does.

This file asserts the **absolute** figures the programme has been quoting, so that a
wave-2 change which moved one of them fails here rather than being re-derived and quietly
re-quoted. The numbers come from ``GATE_B2_CLOSURE.md`` §1, ``artifacts/checkpoints/PC-01/
report.json`` item 7 and ``docs/manual-tests/PC-01_prototype.md``, which agree with each
other:

    published, empty degradation set, four stages succeeded, 3 findings,
    0 diagnostics, 5 CSV data rows, 17 columns, 4251 bytes, two exports identical.

One figure in the tree disagrees with those three and is wrong: the evidence comment at
the foot of ``tests/integration/p02_journey/journey.py`` records ``CSV 4497 bytes`` at
base ``92bece8``. It is a stale note from the previous convergence pass, not a wave-2
regression -- the three sources above all predate wave 2 and all say 4251, and the figure
is unchanged at this session's base. The comment is annotated rather than rewritten.

The byte count is the sharpest of these. Rows and columns are structural and survive a
change to what a column *contains*; the byte count does not. A recommendation text that
grew, an evidence quote that was re-anchored, a verdict column that started emitting a
default -- each keeps five rows of seventeen columns and moves this number.
"""

from __future__ import annotations

import csv
import io

import pytest
from sqlalchemy import text

#: The figures three independent records in this repository agree on. Named here, once,
#: rather than spelled into each assertion, so that a deliberate future change to the
#: corpus has exactly one place to move and one reason to be argued for.
PINNED = {
    "state": "published",
    "findings": 3,
    "diagnostics": 0,
    "csv_rows": 5,
    "csv_columns": 17,
    "csv_bytes": 4251,
    "stages": 4,
}


@pytest.fixture(scope="module")
def corpus_journey(journey_harness, session_factory, blob_store, recorded_adapter, provider_config):
    """One journey through ``IngestService``, the way a product begins one.

    This module drives its own rather than borrowing ``test_journey.py``'s, because a
    module-scoped fixture does not cross modules and the alternative -- promoting it into
    the conftest -- would silently couple the two files' figures to one execution.
    """
    from auditmanager.ingest import IngestService

    h = journey_harness
    with session_factory() as session:
        yield h.drive_journey(
            session,
            ingest=IngestService(blob_store, session_factory=session_factory),
            blob_store=blob_store,
            adapter=recorded_adapter,
            provider_config=provider_config,
            project_name=f"W2-QA figures {h.new_key('proj')}",
            upload_key=h.new_key("upload"),
            run_key=h.new_key("run"),
        )


def test_the_journey_figures_have_not_moved(corpus_journey, session):
    """Every pinned figure at once, and the export measured rather than compared.

    Asserted in one test because they are one measurement of one run: splitting them
    would drive the journey once per figure and say nothing extra. The failure message
    reports the whole set, so a reader sees which of them moved and which held.
    """
    from auditmanager.exports import COLUMNS, export_run_csv
    from auditmanager.findings import published_findings
    from auditmanager.runs import PC01_STAGES

    run_id = corpus_journey.run_id
    row = (
        session.execute(
            text("SELECT state, degradation_set FROM audit_run WHERE run_id = :r"),
            {"r": run_id},
        )
        .mappings()
        .one()
    )
    stages = dict(
        session.execute(
            text("SELECT stage_id, status FROM stage_result WHERE run_id = :r"),
            {"r": run_id},
        ).all()
    )
    first = export_run_csv(session, run_id)
    second = export_run_csv(session, run_id)
    body = [r for r in csv.reader(io.StringIO(first.content[3:].decode("utf-8"))) if r]
    ungrounded = session.execute(
        text(
            "SELECT count(*) FROM finding_observation "
            "WHERE run_id = :r AND grounded IS NOT TRUE"
        ),
        {"r": run_id},
    ).scalar_one()

    measured = {
        "state": row["state"],
        "findings": len(published_findings(session, run_id)),
        "diagnostics": int(ungrounded),
        "csv_rows": len(body) - 1,
        "csv_columns": len(body[0]),
        "csv_bytes": first.byte_size,
        "stages": len(stages),
    }
    assert measured == PINNED, (
        f"a journey figure moved.\n  measured {measured}\n  pinned   {PINNED}\n"
        "These are recorded in GATE_B2_CLOSURE.md, artifacts/checkpoints/PC-01/report.json "
        "and docs/manual-tests/PC-01_prototype.md. If a change moved one deliberately, "
        "all four records move together."
    )
    assert not row["degradation_set"], row["degradation_set"]
    assert set(stages) == set(PC01_STAGES)
    assert set(stages.values()) == {"succeeded"}, stages
    assert tuple(body[0]) == tuple(COLUMNS)
    assert first.content == second.content, "two exports of an unchanged run differed"
    assert first.byte_size == len(first.content), (
        "the reported byte size is not the length of the bytes returned"
    )


def test_the_model_stage_recorded_one_first_try_call(corpus_journey, session):
    """The baseline against which a retried run is read.

    Beside the figures above rather than in the retry suite: this is the journey as a
    product actually performs it, through ``IngestService``, and its attempt count is the
    number every quoted journey figure was measured under. A first-try run reading
    anything but ``1`` would mean the retry loop is entered on the happy path, which the
    figures above would not reveal.
    """
    import json

    metrics = session.execute(
        text(
            "SELECT metrics FROM stage_result "
            "WHERE run_id = :r AND stage_id = 'text_analysis'"
        ),
        {"r": corpus_journey.run_id},
    ).scalar_one()
    if not isinstance(metrics, dict):
        metrics = json.loads(metrics)

    assert metrics["attempts"] == 1, (
        f"the happy-path journey took {metrics['attempts']} attempts; every figure the "
        "programme quotes was measured on a first-try run"
    )
    assert metrics["call_status"] == "succeeded"
    assert metrics["retried_on_error_code"] is None

    calls = session.execute(
        text("SELECT count(*) FROM model_call WHERE run_id = :r"),
        {"r": corpus_journey.run_id},
    ).scalar_one()
    assert calls == 1, f"one first-try call wrote {calls} model_call rows"
