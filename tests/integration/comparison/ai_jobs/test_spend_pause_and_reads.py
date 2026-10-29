"""`CMP-AI-JOBS-01`: the spend of a job -- the consent the spend wrapper checks, the x1.2 overrun pause, the pause for a route
that changed, a lost lease settled through the registered settlers -- and the reads (the job view, the installation's waiting
jobs). The wrapper is the real `ComparisonModelCaller` over a scripted live-mode adapter that calls nothing."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.comparison.public import (
    SPEND_SETTLERS,
    AiMode,
    CallEstimate,
    CallRefused,
    CallRoute,
    Completed,
    ComparisonModelCaller,
)

KIND = "comparison_pair_check"
ESTIMATE = CallEstimate(input_tokens=4_800, output_tokens=1_000)  # USD 0.049 at the claude-opus-5 pin


@pytest.fixture
def w(db: Any, h: Any, world: dict[str, Any], scope_of: Any) -> Any:
    route = h.recorded_route(db.connection, KIND)
    method = h.FakeMethod(method="pair_check")
    service = db.service(method, provider_mode="live")
    scope = scope_of("pair_check")
    job = db.start(service, scope).record.job_id
    worker = db.worker()
    return SimpleNamespace(route=route, method=method, service=service, scope=scope, job=job, world=world, worker=worker,
                           caller=ComparisonModelCaller(db.sessions))


def live_route(h: Any, adapter: Any, revision_id: str) -> CallRoute:
    return CallRoute(adapter=adapter, model_identity=h.MODEL, connection_revision_id=revision_id, expected_model=h.GATEWAY,
                     check_identity=True, unmetered=False, pin=h.PIN)


def consent_of(db: Any, w: Any) -> Any:
    with db.sessions() as session:
        return w.service.consent_for_calls(session, w.job)


def spend_call(db: Any, h: Any, w: Any, item: Any, cost: float, *, revision_id: str | None = None, consent: Any = None) -> Any:
    adapter = h.ScriptedLiveAdapter(h.live_reply(cost=cost))
    return w.caller.call(
        item, live_route(h, adapter, revision_id or w.route.revision_id), h.request_for(f"q-{cost}"), estimate=ESTIMATE,
        consent=consent or consent_of(db, w),
    )


def job_row(db: Any, w: Any) -> dict[str, Any]:
    return db.rows("SELECT state, pause_reason, consent_no FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=w.job)[0]


def items(db: Any, w: Any) -> list[str]:
    return sorted(r["state"] for r in db.rows("SELECT state FROM comparison_work WHERE comparison_ai_job_id = :j", j=w.job))


# -- the consent the wrapper checks ----------------------------------------------------------------------------------


def test_the_consent_given_to_the_wrapper_is_the_jobs_stored_consent(db: Any, h: Any, w: Any) -> None:
    consent = consent_of(db, w)
    record = w.service.view(w.job).record
    assert consent.estimate_digest == record.estimate_digest
    assert consent.estimate_micros == record.estimate_micros == 490_000
    assert (consent.connection_revision_id, consent.pinned_model, consent.ceiling_usd) == (w.route.revision_id, h.MODEL, 10.0)


# -- the x1.2 overrun pause ------------------------------------------------------------------------------------------


def test_a_call_that_takes_the_job_past_1_2_times_its_estimate_pauses_the_job_and_its_waiting_items(db: Any, h: Any, w: Any) -> None:
    item = db.claim(w.worker, KIND)
    with db.sessions() as session:
        assert w.service.mark_running(session, w.job) == "running"
        session.commit()
    result = spend_call(db, h, w, item, 0.60)  # the estimate is USD 0.49; 1.2 x is USD 0.588
    assert result.pause is not None and result.pause.reason == "overrun"
    with db.sessions() as session:
        assert w.service.pause_for_spend(session, w.job, result.pause.reason)
        session.commit()
    row = job_row(db, w)
    assert (row["state"], row["pause_reason"]) == ("paused", "overrun")
    assert items(db, w) == ["paused", "paused", "running"]  # the call in hand finishes
    view = w.service.view(w.job)
    assert (view.spend.spent_micros, view.spend.calls, view.spend.unknown_calls) == (600_000, 1, 0)
    with db.sessions() as session:  # idempotent: already paused
        assert w.service.pause_for_spend(session, w.job, "overrun") is False


def test_a_call_inside_1_2_times_its_estimate_pauses_nothing(db: Any, h: Any, w: Any) -> None:
    item = db.claim(w.worker, KIND)
    result = spend_call(db, h, w, item, 0.58)
    assert result.pause is None
    assert job_row(db, w)["state"] == "queued"


def test_the_wrapper_refuses_the_next_call_of_an_overrun_job_and_the_refusal_pauses_it(db: Any, h: Any, w: Any) -> None:
    first = db.claim(w.worker, KIND)
    spend_call(db, h, w, first, 0.60)
    second = db.claim(w.worker, KIND)
    with pytest.raises(CallRefused) as refused:
        spend_call(db, h, w, second, 0.01)
    assert refused.value.reason == "overrun" and refused.value.pauses_job
    with db.sessions() as session:
        assert w.service.pause_for_spend(session, w.job, refused.value.reason)
        session.commit()
    assert job_row(db, w)["pause_reason"] == "overrun"


def test_a_resumed_job_judges_the_overrun_on_what_it_had_spent_before_its_new_consent(db: Any, h: Any, w: Any) -> None:
    item = db.claim(w.worker, KIND)
    result = spend_call(db, h, w, item, 0.60)
    with db.sessions() as session:
        db.work.finish(session, item.authority, Completed())
        assert w.service.pause_for_spend(session, w.job, result.pause.reason)
        session.commit()
    w.method.counts_by_mode[AiMode.LEFT] = h.counts_for(5)  # USD 0.245 for what is left
    with db.sessions() as session:
        left = w.service.estimate_in(session, w.scope, AiMode.LEFT, job=w.service.job(session, w.job))
    w.service.resume(job_id=w.job, method="pair_check", command=db.command("resume_comparison_ai_pair_check"),
                     consent=db.consent(left.estimate_digest))
    assert job_row(db, w)["consent_no"] == 2
    consent = consent_of(db, w)
    assert consent.estimate_micros == 600_000 + 245_000  # the baseline is what the job had spent before this consent
    second = db.claim(w.worker, KIND)
    assert spend_call(db, h, w, second, 0.10).pause is None  # 0.70 is inside 1.2 x 0.845
    third = db.claim(w.worker, KIND)
    assert spend_call(db, h, w, third, 0.40, consent=consent).pause is not None  # 1.10 is not... 1.2 x 0.845 = 1.014


def test_a_new_revision_of_the_connection_makes_the_wrappers_consent_stale_and_the_job_pauses_for_the_route(db: Any, h: Any, w: Any) -> None:
    revision = h.new_revision(db.connection, w.route)
    item = db.claim(w.worker, KIND)
    with pytest.raises(CallRefused) as refused:
        spend_call(db, h, w, item, 0.01, revision_id=revision)
    assert refused.value.reason == "consent_stale" and refused.value.pauses_job
    with db.sessions() as session:
        assert w.service.pause_for_spend(session, w.job, refused.value.reason)
        session.commit()
    assert job_row(db, w)["pause_reason"] == "route_changed"


@pytest.mark.parametrize(("reason", "expected"), [
    ("overrun", "overrun"), ("job_ceiling", "overrun"), ("day_ceiling", "quota"),
    ("consent_stale", "route_changed"), ("consent_required", "route_changed"),
])
def test_each_reason_of_the_spend_wrapper_pauses_the_job_with_its_own_reason(db: Any, h: Any, w: Any, reason: str, expected: str) -> None:
    with db.sessions() as session:
        assert w.service.pause_for_spend(session, w.job, reason)
        session.commit()
    row = job_row(db, w)
    assert (row["state"], row["pause_reason"]) == ("paused", expected)
    assert items(db, w) == ["paused"] * 3


@pytest.mark.parametrize("reason", ["connection_busy", "model_not_selected", "unsettled_call", "spend_unknown", "no_such_reason"])
def test_a_reason_that_is_not_a_pause_changes_nothing(db: Any, h: Any, w: Any, reason: str) -> None:
    with db.sessions() as session:
        assert w.service.pause_for_spend(session, w.job, reason) is False
        session.commit()
    assert job_row(db, w)["state"] == "queued" and items(db, w) == ["queued"] * 3


def test_a_call_lost_with_its_lease_is_settled_unknown_through_the_registered_settlers_and_is_not_sent_again(db: Any, h: Any, w: Any) -> None:
    item = db.claim(w.worker, KIND)
    call_id = h.insert_call(db.connection, item, state="sent", estimate_micros=49_000, revision_id=w.route.revision_id)
    db.connection.execute(text("UPDATE comparison_work_attempt SET lease_expires_at = statement_timestamp() - interval '1 second' "
                               "WHERE comparison_work_attempt_id = :a"), {"a": item.attempt_id})
    with db.sessions() as session:
        db.work.reclaim_expired(session, spend_settlers=SPEND_SETTLERS)
        session.commit()
    assert db.state("SELECT state FROM comparison_model_call WHERE comparison_model_call_id = :c", c=call_id) == "unknown"
    view = w.service.view(w.job)
    assert view.progress.unknown == 1 and view.progress.by_state["spend_unknown"] == 1
    assert (view.spend.unknown_calls, view.spend.reserved_micros, view.spend.spent_micros) == (1, 49_000, 0)
    # the unit is not queued again by itself: only the explicit retry of the item clears it
    assert db.claim(w.worker, KIND).work_id != item.work_id


# -- the reads -------------------------------------------------------------------------------------------------------


def test_the_job_view_reads_progress_and_spend_through_the_jobs_items(db: Any, h: Any, w: Any) -> None:
    a, b = db.claim(w.worker, KIND), db.claim(w.worker, KIND)
    h.insert_call(db.connection, a, cost_micros=120_000, estimate_micros=49_000, input_tokens=5_000, output_tokens=900,
                  revision_id=w.route.revision_id)
    h.insert_call(db.connection, b, state="sent", estimate_micros=49_000, revision_id=w.route.revision_id)
    h.insert_call(db.connection, b, state="unknown", estimate_micros=30_000, revision_id=w.route.revision_id)
    with db.sessions() as session:
        db.work.finish(session, a.authority, Completed())
        session.commit()
    view = w.service.view(w.job)
    assert (view.progress.total, view.progress.done, view.progress.failed, view.progress.unknown) == (3, 1, 0, 0)
    assert view.spend.spent_micros == 120_000 and view.spend.reserved_micros == 79_000
    assert (view.spend.calls, view.spend.unknown_calls) == (3, 1)
    assert (view.spend.input_tokens, view.spend.output_tokens) == (5_000, 900)


def test_the_view_has_the_shape_of_the_contracts_job_and_its_queue_item(db: Any, h: Any, w: Any) -> None:
    from auditmanager.api.schemas import models

    view = w.service.view(w.job)
    job = models.ComparisonAiJob.model_validate(view.as_dict())
    assert job.state.value == "queued" and job.queue_position is not None and job.estimate.estimate_digest == view.record.estimate_digest
    assert job.counts.total == 3 and job.spend.spent_micros == 0
    models.ComparisonAiQueueItem.model_validate(view.as_queue_item())
    models.ComparisonAiQueue.model_validate(w.service.waiting().as_dict())
    paused = db.service(w.method, provider_mode="live")
    paused.pause(job_id=w.job, method="pair_check", command=db.command("pause_comparison_ai_pair_check"))
    again = models.ComparisonAiJob.model_validate(w.service.view(w.job).as_dict())
    assert again.pause_reason.value == "user" and again.queue_position is None


def test_the_installations_waiting_jobs_run_first_then_start_in_order_and_paused_last(db: Any, h: Any, w: Any, scope_of: Any) -> None:
    for kind in ("comparison_spec", "comparison_sheet_changes", "comparison_report"):
        h.recorded_route(db.connection, kind)
    both = db.service(w.method, h.FakeMethod(method="spec"), h.FakeMethod(method="sheet_changes"), h.FakeMethod(method="report"))
    spec = db.start(both, scope_of("spec"), command=db.command("start_comparison_specification")).record.job_id
    sheets = db.start(both, scope_of("sheet_changes"), command=db.command("start_comparison_ai_sheet_changes")).record.job_id
    report = db.start(both, scope_of("report"), command=db.command("start_comparison_report")).record.job_id
    with db.sessions() as session:
        both.mark_running(session, report)  # started: it runs
        session.commit()
    both.pause(job_id=sheets, method="sheet_changes", command=db.command("pause_comparison_ai_sheet_changes"))
    mine = {w.job, spec, sheets, report}
    waiting = both.waiting()
    order = [item.record.job_id for item in waiting.items if item.record.job_id in mine]
    assert order == [report, w.job, spec, sheets]  # running, queued in start order, paused
    positions = {item.record.job_id: item.queue_position for item in waiting.items if item.record.job_id in mine}
    assert positions[report] is None and positions[sheets] is None and positions[w.job] < positions[spec]
    assert waiting.running >= 1 and waiting.queued >= 2 and waiting.paused >= 1
    assert waiting.queued + waiting.running + waiting.paused >= len(waiting.items)


def test_the_latest_job_of_a_scope_is_the_newest_in_any_state(db: Any, h: Any, w: Any) -> None:
    assert w.service.latest(w.scope).record.job_id == w.job
    w.service.cancel(job_id=w.job, method="pair_check", command=db.command("cancel_comparison_ai_pair_check"))
    newer = db.start(w.service, w.scope)
    assert w.service.latest(w.scope).record.job_id == newer.record.job_id


# -- recorded mode ---------------------------------------------------------------------------------------------------


def test_a_recorded_answer_goes_through_the_wrapper_unmetered_with_no_consent_and_a_missing_one_is_never_a_call(db: Any, h: Any, w: Any) -> None:
    from auditmanager.comparison.public import CallFailed, RecordedAnswers

    answers = RecordedAnswers()
    route = CallRoute(adapter=answers, model_identity=h.MODEL, connection_revision_id=w.route.revision_id, expected_model=h.GATEWAY,
                      check_identity=True, unmetered=False, pin=h.PIN)
    question = h.request_for("is page 3 the pair of page 5?")
    answers.record(question, '{"pair": true}')
    item = db.claim(w.worker, KIND)
    result = w.caller.call(item, route, question, estimate=ESTIMATE, consent=None)  # a replay needs no consent
    assert result.response.output_text == '{"pair": true}' and result.cost_basis == "unmetered" and result.cost_micros == 0 and result.pause is None
    (row,) = db.rows("SELECT provider_mode, model_identity, cost_basis, cost_micros, estimate_micros, state FROM comparison_model_call "
                     "WHERE comparison_work_id = :w", w=item.work_id)
    assert row == {"provider_mode": "recorded", "model_identity": "recorded", "cost_basis": "unmetered", "cost_micros": 0,
                   "estimate_micros": 0, "state": "completed"}
    view = w.service.view(w.job)
    assert (view.spend.spent_micros, view.spend.reserved_micros, view.spend.calls) == (0, 0, 1)
    with pytest.raises(CallFailed):
        w.caller.call(item, route, h.request_for("a question nobody recorded"), estimate=ESTIMATE, consent=None)
    assert answers.calls == 2 and answers.digests[1] != answers.digests[0]
    assert db.rows("SELECT state FROM comparison_model_call WHERE comparison_work_id = :w ORDER BY prepared_at", w=item.work_id) == [
        {"state": "completed"}, {"state": "failed"}]
