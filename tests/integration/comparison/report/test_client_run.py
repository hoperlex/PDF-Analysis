"""`CMP-VC-REPORT-01`: a client report from the start to its PDF, in recorded mode (database, bucket and the PDF child).

One model call per transition that has something to write about, made through the spend wrapper; the program's check drops the point the facts do not
confirm; the PDF carries the unconfirmed label and the recall line on its page; every answer is by the digest of its request, so a request nobody
recorded is never a call."""

from __future__ import annotations

import json
from typing import Any

import pytest

from auditmanager.comparison.report.model import UNCONFIRMED_LABEL
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.comparison.report.conftest import EXPERT, support
from tests.integration.comparison.report.run_support import pdf_text, record_client, reread, run_client_report, source_of, start


def test_a_started_report_runs_to_a_pdf_with_one_recorded_call_per_transition_that_has_a_description(db: Any, world: Any, make: Any, route: Any) -> None:
    report, started = run_client_report(db, world, make, route)
    assert (started["state"], started["stage"]) == ("queued", "client_writing")
    assert started["job"]["state"] == "queued" and started["job"]["counts"]["total"] == 2 and started["job"]["method"] == "report"
    assert "estimate" not in started and started["job"]["estimate"]["estimate_digest"] == report["estimate"]["estimate_digest"]
    final = reread(db, report)
    assert (final["state"], final["stage"], final["job"]["state"]) == ("completed", "pdf_writing", "completed")
    assert db.answers.calls == 1  # the second and the third transition have no description: the program finishes them, no call
    assert [p["selection"] for p in final["parts"]] == ["done", "done", "done"]
    assert [p.get("points") for p in final["parts"]] == [1, 0, 0] and final["parts"][0]["questions"] == 0
    assert sorted(a["kind"] for a in final["artifacts"]) == ["report_pdf", "source_md"]
    pdf = db.service().read_report_pdf(report_id=report["report_id"])
    assert pdf.startswith(b"%PDF-")
    text = pdf_text(pdf)
    assert all(UNCONFIRMED_LABEL.replace(" ", "") in page.replace(" ", "").replace("\n", "") for page in text)
    assert "изменённых листов 3, описано 1, отброшено проверкой 0" in " ".join(text).replace("\n", " ")
    assert "V1→V2" in text[0] and "3×4" in text[0] and "Описание изменений для этого перехода не подготовлено." in text[0]


def test_every_call_is_journalled_through_the_wrapper_as_a_recorded_unmetered_call_of_the_jobs_own_item(db: Any, world: Any, make: Any, route: Any) -> None:
    report, started = run_client_report(db, world, make, route)
    calls = db.rows("SELECT c.provider_mode, c.state, c.cost_basis, c.cost_micros, c.work_kind, w.comparison_ai_job_id AS job FROM comparison_model_call c "
                    "JOIN comparison_work w ON w.comparison_work_id = c.comparison_work_id")
    assert len(calls) == 1
    assert (calls[0]["provider_mode"], calls[0]["state"], calls[0]["cost_basis"], calls[0]["cost_micros"]) == ("recorded", "completed", "unmetered", 0)
    assert calls[0]["work_kind"] == "comparison_report" and calls[0]["job"] == started["job"]["job_id"]
    final = reread(db, report)
    assert final["job"]["spend"]["calls"] == 1 and final["job"]["spend"]["spent_micros"] == 0


def test_a_point_the_facts_do_not_confirm_is_dropped_and_counted_in_the_recall_line_of_every_page(db: Any, world: Any, make: Any, route: Any, h: Any) -> None:
    report = make(world)
    doc = source_of(db, report["report_id"])
    answer = h.good_client_answer(doc)
    answer["points"].append(h.bad_point(doc))  # «16 А → 63 А»: the number 63 is in no fact
    record_client(db, world, report, route, answer=answer)
    start(db, report)
    db.drain(db.handler())
    final = reread(db, report)
    assert final["state"] == "completed" and final["parts"][0]["points"] == 1
    stored = db.state("SELECT facts FROM comparison_report_part WHERE comparison_report_id = :r ORDER BY created_at LIMIT 1", r=report["report_id"])
    assert [d["point"]["object"] for d in stored["result"]["dropped"]] == ["Автомат QF1"]
    assert "the number 63 is not found in the cited facts" in stored["result"]["dropped"][0]["problems"]
    text = pdf_text(db.service().read_report_pdf(report_id=report["report_id"]))
    flat = " ".join(text).replace("\n", " ")
    assert "отброшено проверкой 1" in flat and "63" not in flat and "QF1" not in flat
    assert all("отброшено проверкой 1" in page.replace("\n", " ") for page in text)


def test_a_request_nobody_recorded_is_never_a_call_and_the_report_is_partial_with_no_pdf(db: Any, world: Any, make: Any, route: Any) -> None:
    report = make(world)
    start(db, report)  # nothing recorded
    outcomes = db.drain(db.handler())
    assert outcomes[0].startswith("Failed:") and db.state("SELECT count(*) FROM comparison_model_call WHERE state = 'completed'") == 0
    final = reread(db, report)
    assert final["state"] == "partial" and final["job"]["state"] == "completed"
    assert [p["selection"] for p in final["parts"]] == ["failed", "done", "done"]
    assert [a["kind"] for a in final["artifacts"]] == ["source_md"]
    error = pytest.raises(DomainError, db.service().read_report_pdf, report_id=report["report_id"]).value
    assert error.code is ErrorCode.CONFLICT and error.detail_fields["conflict_reason"] == "comparison_report_state"


def test_the_final_item_waits_for_every_other_item_and_a_report_is_never_finished_twice(db: Any, world: Any, make: Any, route: Any) -> None:
    report = make(world)
    record_client(db, world, report, route)
    start(db, report)
    worker = db.worker()
    handler = db.handler()
    first = db.claim(worker)  # the transition's item comes before the final one (priority)
    assert first.payload["unit"] == "transition"
    final = db.claim(worker)
    assert final.payload["unit"] == "final"
    assert type(handler.run(final)).__name__ == "Yielded"  # the transition's item has not ended: nothing is written
    assert db.state("SELECT count(*) FROM comparison_report_artifact WHERE comparison_report_id = :r", r=report["report_id"]) == 1
    outcome = handler.run(first)
    assert type(outcome).__name__ == "Completed"


def test_a_second_start_of_the_same_report_is_refused_and_one_report_has_one_job(db: Any, world: Any, make: Any, route: Any) -> None:
    report = make(world)
    start(db, report)
    error = pytest.raises(DomainError, start, db, report, key="start-2").value
    assert error.code is ErrorCode.CONFLICT and error.detail_fields["conflict_reason"] == "comparison_report_state"
    assert db.state("SELECT count(*) FROM comparison_ai_job WHERE method = 'report'") == 1
    assert db.state("SELECT count(comparison_ai_job_id) FROM comparison_report WHERE comparison_report_id = :r", r=report["report_id"]) == 1


def test_a_repeat_of_the_start_key_replays_the_job_and_does_not_queue_it_twice(db: Any, world: Any, make: Any, route: Any) -> None:
    report = make(world)
    first = start(db, report, key="the-key")
    again = start(db, report, key="the-key")
    assert again["job"]["job_id"] == first["job"]["job_id"]
    assert db.state("SELECT count(*) FROM comparison_work WHERE comparison_ai_job_id = :j", j=first["job"]["job_id"]) == 2


def test_a_stale_digest_is_refused_and_the_draft_shows_the_digest_a_start_will_accept(db: Any, world: Any, make: Any, route: Any, h: Any) -> None:
    report = make(world)
    error = pytest.raises(DomainError, start, db, report, digest="0" * 64).value
    assert error.code is ErrorCode.CONFLICT and error.detail_fields["conflict_reason"] == "comparison_estimate_stale"
    assert db.state("SELECT count(*) FROM comparison_ai_job WHERE method = 'report'") == 0
    assert reread(db, report)["estimate"]["estimate_digest"] == report["estimate"]["estimate_digest"]  # nothing moved: the same digest
    revision = h.base.new_revision(db.connection, route)  # the connection has a new revision, which the route's current one is
    stale = pytest.raises(DomainError, start, db, report, key="start-2").value
    assert stale.code is ErrorCode.CONFLICT and stale.detail_fields["conflict_reason"] == "comparison_estimate_stale"
    fresh = reread(db, report)
    assert fresh["state"] == "draft" and fresh["estimate"]["estimate_digest"] != report["estimate"]["estimate_digest"]
    assert fresh["estimate"]["route"]["revision_id"] == revision
    assert start(db, fresh, key="start-3")["state"] == "queued"  # the digest the draft shows now is the one a start accepts


def test_an_unconfirmed_consent_starts_nothing(db: Any, world: Any, make: Any, route: Any) -> None:
    report = make(world)
    error = pytest.raises(
        DomainError, db.service().start_report, report_id=report["report_id"], consent=db.consent(report["estimate"]["estimate_digest"], False),
        user_uid=support.ACTOR, actor_roles=EXPERT, idempotency_key="k",
    ).value
    assert error.code is ErrorCode.VALIDATION_FAILED and error.detail_fields["constraint"] == "comparison_consent_required"
    assert reread(db, report)["state"] == "draft" and db.state("SELECT count(*) FROM comparison_ai_job WHERE method = 'report'") == 0
