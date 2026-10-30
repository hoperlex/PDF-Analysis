"""The reads of a described sheet and the steering of a job (`CMP-VC-AISHEET-01`)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest

from auditmanager.api.schemas import models
from auditmanager.comparison.ai_sheets.handler import SheetChangesHandler, UnavailableRoutes
from auditmanager.comparison.work.model import Completed, Failed, Yielded
from auditmanager.shared.errors import DomainError, ErrorCode

from .conftest import core, fx, support


def conflict(error: Any) -> str:
    return core.conflict_reason(error)


def record_all(lab: Any) -> None:
    for name in ("p1", "p6"):
        lab.record(name)
    lab.record_single("p4")
    lab.record_single("p5")


# -- the Markdown ---------------------------------------------------------------------------------------------------------------------


def test_the_markdown_of_a_sheet_is_the_same_bytes_every_time_and_says_it_is_unconfirmed(lab: Any) -> None:
    record_all(lab)
    lab.start_series()
    lab.drain()
    pair = lab.world["p1"].pair
    first = lab.service.read_md(sheet_pair_id=pair)
    assert isinstance(first, bytes) and first == lab.service.read_md(sheet_pair_id=pair)
    text = first.decode("utf-8")
    assert text.startswith("### План этажа · A стр. PDF 1 → B стр. PDF 1\n\nA: версия №1. B: версия №2.\nСостояние: Готово.\n")
    assert "1. **Люк Лк-1** — Лк-1 — количество 2 → 3." in text
    assert "Заявлено проектировщиком в разрешении: Изм. 3: замена люка Лк-1" in text
    assert "_Описание составлено ИИ по исходным листам двух версий и инженером не подтверждено._" in text
    assert "Записанный (тестовый) ответ" in text and text.endswith("\n")
    # the stored description is immutable, so a later read of the same description gives the same bytes after a rerun of the job
    assert lab.service.read_md(sheet_pair_id=pair) == first


def test_a_sheet_with_no_description_has_no_markdown_and_an_unknown_sheet_is_not_found(lab: Any) -> None:
    with pytest.raises(DomainError) as missing:
        lab.service.read_md(sheet_pair_id=lab.world["p1"].pair)
    assert conflict(missing) == "comparison_description_missing"
    for call in (lambda: lab.service.read_md(sheet_pair_id=core.new_id("ctp")),
                 lambda: lab.service.get_description(sheet_pair_id=core.new_id("ctp")),
                 lambda: lab.service.estimate_description(sheet_pair_id=core.new_id("ctp")),
                 lambda: lab.service.list_history(sheet_pair_id=core.new_id("ctp"), after=None, limit=10),
                 lambda: lab.service.list_review_sheets(transition_id=core.new_id("ctn"), after=0, limit=10),
                 lambda: lab.service.estimate_series(series_id=core.new_id("cser"), only_failed=False),
                 lambda: lab.service.get_series(series_id=core.new_id("cser"))):
        with pytest.raises(DomainError) as absent:
            call()
        assert absent.value.code is ErrorCode.NOT_FOUND


# -- the history ----------------------------------------------------------------------------------------------------------------------


def test_the_history_lists_the_descriptions_of_a_sheet_newest_first_and_pages(lab: Any) -> None:
    pair = lab.world["p1"]
    with lab.db.sessions() as session:
        facts = lab.repo.pair(session, pair.pair)
        for n, prompt in enumerate(("sheet-changes/0+aaaaaaaaaaaa", "sheet-changes/0+bbbbbbbbbbbb")):
            lab.repo.insert_description(
                session, project_uid=lab.world.project, key=support.digest("h", str(n)), result_id=facts.result_id, page_profile_id=None,
                state="done", prompt_version=prompt, model_identity="recorded", recorded=True,
                description={"schema": "x", "state": "done", "changes": [{"id": "CH1"}] * n, "unresolved": [], "excluded": []}, calls=1,
                input_tokens=1, output_tokens=1, model_call_id=None)
        session.commit()
    lab.record("p1")
    lab.start_pair("p1")
    lab.drain()
    page = lab.service.list_history(sheet_pair_id=pair.pair, after=None, limit=2)
    models.ComparisonSheetDescriptionHistory.model_validate({"items": page.items, "page": {"next_cursor": None}})
    assert [i["prompt_version"].split("+")[0] for i in page.items] == ["sheet-changes/2", "sheet-changes/0"]
    assert page.next_after is not None
    rest = lab.service.list_history(sheet_pair_id=pair.pair, after=page.next_after, limit=2)
    assert len(rest.items) == 1 and rest.next_after is None
    assert rest.items[0]["prompt_version"].startswith("sheet-changes/0+aaaa") and rest.items[0]["changes_count"] == 0
    assert lab.service.get_description(sheet_pair_id=pair.pair)["history_count"] == 3
    assert lab.service.get_description(sheet_pair_id=pair.pair)["state"] == "done"


# -- the list to check -----------------------------------------------------------------------------------------------------------------


def test_the_list_to_check_holds_the_sheets_left_partial_and_the_one_sided_ones_in_matrix_order(lab: Any) -> None:
    packet, _request = lab.packet_of("p6")
    unsorted = lab.good_answer(packet, excluded=[])  # two candidates left in no list: the sheet is "частично"
    lab.record("p1")
    lab.record("p6", unsorted)
    lab.record_single("p4")
    lab.record_single("p5")
    # the quiet sheet has engine notes in this variant: no, p2 stays "no_construction_changes": it is not to be checked
    lab.start_series()
    lab.drain()
    page = lab.service.list_review_sheets(transition_id=lab.world.transition, after=0, limit=10)
    models.ComparisonReviewSheetPage.model_validate({"items": page.items, "page": {"next_cursor": None}})
    assert [(i["sheet_pair_id"], i["kind"]) for i in page.items] == [
        (lab.world["p4"].pair, "added"), (lab.world["p5"].pair, "removed"), (lab.world["p6"].pair, "to_check")]
    assert [i["state"] for i in page.items] == ["done", "done", "partial"]
    assert "page_a" not in page.items[0] and "page_b" not in page.items[1] and "page_a" in page.items[2]
    first = lab.service.list_review_sheets(transition_id=lab.world.transition, after=0, limit=2)
    assert len(first.items) == 2 and first.next_after == 5
    second = lab.service.list_review_sheets(transition_id=lab.world.transition, after=first.next_after, limit=2)
    assert [i["kind"] for i in second.items] == ["to_check"] and second.next_after is None
    partial = lab.service.get_description(sheet_pair_id=lab.world["p6"].pair)
    assert partial["state"] == "partial" and partial["coverage"]["not_reviewed"] == 2


# -- a single sheet by itself ---------------------------------------------------------------------------------------------------------------


def test_one_sided_sheet_is_described_by_its_own_job_and_cancelled_with_the_same_operation(lab: Any) -> None:
    lab.record_single("p4")
    estimate = lab.service.estimate_description(sheet_pair_id=lab.world["p4"].pair)
    assert (estimate["units"], estimate["calls"], estimate["images"]) == (1, 1, 1)
    job = lab.start_pair("p4")
    models.ComparisonAiJob.model_validate(job)
    assert job["sheet_pair_id"] == lab.world["p4"].pair and "series_id" not in job
    cancelled = lab.service.cancel(job_id=job["job_id"], command=lab.command("cancel_comparison_ai_sheet_changes"))
    assert cancelled["state"] == "cancelled"
    assert lab.service.get_description(sheet_pair_id=lab.world["p4"].pair)["state"] == "cancelled"
    assert lab.answers.calls == 0
    again = lab.start_pair("p4")
    lab.drain()
    assert lab.service.get_description(sheet_pair_id=lab.world["p4"].pair)["state"] == "done"
    assert lab.job(again["job_id"])["state"] == "completed"


def test_a_sheet_that_did_not_change_needs_no_description(lab: Any) -> None:
    with pytest.raises(DomainError) as same:
        lab.service.estimate_description(sheet_pair_id=lab.world["p3"].pair)
    assert conflict(same) == "comparison_ai_nothing_to_do"
    with pytest.raises(DomainError) as same:
        lab.service.start_description(sheet_pair_id=lab.world["p3"].pair, consent=lab.consent("a" * 64),
                                      command=lab.command("start_comparison_sheet_description"))
    assert conflict(same) == "comparison_ai_nothing_to_do"


def test_a_series_without_a_finished_transition_has_nothing_to_estimate(lab: Any) -> None:
    unfinished = support.sheet_world(lab.db.connection, fx, transition_state="running")
    with pytest.raises(DomainError) as nothing:
        lab.service.estimate_series(series_id=unfinished.series, only_failed=False)
    assert conflict(nothing) == "comparison_ai_nothing_to_do"


# -- steering ----------------------------------------------------------------------------------------------------------------------------


def test_pause_and_resume_in_the_middle_of_a_run_finish_the_series_without_asking_twice(lab: Any) -> None:
    record_all(lab)
    job = lab.start_series()
    lab.run_next()
    lab.run_next()
    paused = lab.service.pause(job_id=job["job_id"], command=lab.command("pause_comparison_ai_sheet_changes"))
    assert (paused["state"], paused["pause_reason"]) == ("paused", "user")
    asked = lab.answers.calls
    step = lab.run_next()
    assert step is None or "drain_job_id" in step[0].payload, "a paused job's waiting sheets are not claimable"
    assert lab.service.get_description(sheet_pair_id=lab.world["p6"].pair)["state"] in {"queued", "done"}
    resumed = lab.service.resume(job_id=job["job_id"], consent=None, command=lab.command("resume_comparison_ai_sheet_changes"))
    assert resumed["state"] == "queued" and "pause_reason" not in resumed
    lab.drain()
    assert lab.job(job["job_id"])["state"] == "completed" and lab.answers.calls == 4 and asked <= 4
    assert lab.items(job["job_id"]) == {n: "done" for n in ("p1", "p2", "p4", "p5", "p6")}


def test_an_item_in_hand_when_the_job_pauses_sends_nothing_and_continues_after_the_resume(lab: Any) -> None:
    record_all(lab)
    job = lab.start_series()
    item = lab.db.claim(lab.worker_id, "comparison_sheet_changes")
    lab.service.pause(job_id=job["job_id"], command=lab.command("pause_comparison_ai_sheet_changes"))
    outcome = lab.handler.run(item)
    assert isinstance(outcome, Yielded) and lab.answers.calls == 0
    with lab.db.sessions() as session:
        lab.db.work.finish(session, item.authority, outcome)
        session.commit()
    lab.service.resume(job_id=job["job_id"], consent=None, command=lab.command("resume_comparison_ai_sheet_changes"))
    lab.drain()
    assert lab.job(job["job_id"])["state"] == "completed" and lab.answers.calls == 4


def test_cancel_ends_the_job_marks_the_sheets_cancelled_and_a_finish_describes_the_rest(lab: Any) -> None:
    record_all(lab)
    job = lab.start_series()
    lab.run_next()
    lab.run_next()
    cancelled = lab.service.cancel(job_id=job["job_id"], command=lab.command("cancel_comparison_ai_sheet_changes"))
    assert cancelled["state"] == "cancelled"
    states = {n: lab.service.get_description(sheet_pair_id=lab.world[n].pair)["state"] for n in ("p1", "p2", "p4", "p5", "p6")}
    assert set(states.values()) <= {"done", "no_construction_changes", "cancelled", "partial", "needs_clarification"} and "cancelled" in states.values()
    done = [n for n, s in states.items() if s != "cancelled"]
    asked = lab.answers.calls
    finished = lab.service.finish(job_id=job["job_id"], command=lab.command("finish_comparison_ai_sheet_changes"))
    assert finished["state"] == "queued"
    lab.drain()
    assert lab.job(job["job_id"])["state"] == "completed"
    assert lab.answers.calls == 4, "the sheets done before the cancel are not asked again"
    assert asked <= 4 and len(done) >= 1
    assert lab.items(job["job_id"]) == {n: "done" for n in ("p1", "p2", "p4", "p5", "p6")}


def test_a_job_that_has_not_started_leaves_the_queue_and_one_that_has_cannot(lab: Any) -> None:
    record_all(lab)
    job = lab.start_series()
    dequeued = lab.service.dequeue(job_id=job["job_id"], command=lab.command("dequeue_comparison_ai_sheet_changes"))
    assert dequeued["state"] == "cancelled" and lab.run_next() is None
    second = lab.start_series()
    lab.run_next()
    with pytest.raises(DomainError) as started:
        lab.service.dequeue(job_id=second["job_id"], command=lab.command("dequeue_comparison_ai_sheet_changes"))
    assert conflict(started) == "comparison_ai_job_state"


def test_a_job_of_another_method_or_none_at_all_is_not_found_for_every_control(lab: Any) -> None:
    ghost = core.new_id("cai")
    for control in (lab.service.pause, lab.service.cancel, lab.service.finish, lab.service.dequeue):
        with pytest.raises(DomainError) as absent:
            control(job_id=ghost, command=lab.command("pause_comparison_ai_sheet_changes"))
        assert absent.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(DomainError) as absent:
        lab.service.resume(job_id=ghost, consent=None, command=lab.command("resume_comparison_ai_sheet_changes"))
    assert absent.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(DomainError) as absent:
        lab.service.retry(job_id=ghost, consent=lab.consent("a" * 64), command=lab.command("retry_comparison_ai_sheet_changes"))
    assert absent.value.code is ErrorCode.NOT_FOUND
    # a job of the pair check is not this method's: the same operations answer 404 for it
    from auditmanager.comparison.public import AiScope, ComparisonAiJobService

    core.recorded_route(lab.db.connection, "comparison_pair_check", billing="not_metered")
    other = ComparisonAiJobService(lab.db.sessions, methods=[core.FakeMethod("pair_check")], work=lab.db.work,
                                   comparison_modules="versions", provider_mode="recorded")
    scope = AiScope("pair_check", lab.world.project, lab.world.document, matrix_id=lab.world.build)
    foreign = other.start(scope=scope, consent=lab.consent(other.estimate(scope).estimate_digest),
                          command=lab.command("start_comparison_ai_pair_check"))
    for control in (lab.service.pause, lab.service.cancel, lab.service.finish, lab.service.dequeue):
        with pytest.raises(DomainError) as foreign_job:
            control(job_id=foreign.record.job_id, command=lab.command("pause_comparison_ai_sheet_changes"))
        assert foreign_job.value.code is ErrorCode.NOT_FOUND
    assert lab.job(foreign.record.job_id)["state"] == "queued"


# -- the worker's side ---------------------------------------------------------------------------------------------------------------------


def test_a_process_with_no_route_source_ends_the_job_failed_and_says_why(lab: Any) -> None:
    record_all(lab)
    job = lab.start_series()
    bare = SheetChangesHandler(lab.handler._deps, routes=UnavailableRoutes(), material=lab.material, jobs=lab.jobs)  # noqa: SLF001
    item = lab.db.claim(lab.worker_id, "comparison_sheet_changes")
    outcome = bare.run(item)
    assert isinstance(outcome, Failed) and outcome.reason == "executor_adapter_unavailable"
    after = lab.job(job["job_id"])
    assert (after["state"], after["failure_reason"]) == ("failed", "executor_adapter_unavailable")
    assert lab.answers.calls == 0


def test_a_requested_cancel_stops_the_item_before_any_call(lab: Any) -> None:
    record_all(lab)
    lab.start_series()
    item = lab.db.claim(lab.worker_id, "comparison_sheet_changes")
    item.cancelled.set()
    outcome = lab.handler.run(item)
    assert isinstance(outcome, Yielded) and lab.answers.calls == 0


def test_the_job_completes_only_when_the_last_sheet_is_over_and_exactly_once(lab: Any) -> None:
    record_all(lab)
    job = lab.start_series()
    states = []
    for _ in range(5):
        lab.run_next()
        states.append(lab.job(job["job_id"])["state"])
    assert states == ["running"] * 5, "five sheets are over but the job is not completed by a sheet"
    lab.drain()
    assert lab.job(job["job_id"])["state"] == "completed"
    drains = lab.db.rows(
        "SELECT state FROM comparison_work WHERE kind = 'comparison_sheet_changes' AND comparison_ai_job_id IS NULL "
        "AND project_uid = :p", p=lab.world.project)
    assert [d["state"] for d in drains] == ["succeeded"] and lab.db.rows(
        "SELECT 1 FROM comparison_work WHERE kind = 'comparison_sheet_changes' AND comparison_ai_job_id = :j AND state <> 'succeeded'",
        j=job["job_id"]) == []


def test_the_sheet_with_no_candidate_is_described_without_a_call(lab: Any) -> None:
    record_all(lab)
    lab.start_series()
    lab.drain()
    quiet = lab.db.rows("SELECT calls, recorded, state FROM comparison_sheet_description WHERE result_id = :r", r=lab.world["p2"].result)[0]
    assert quiet == {"calls": 0, "recorded": False, "state": "no_construction_changes"}
    shown = lab.service.get_description(sheet_pair_id=lab.world["p2"].pair)
    assert shown["recorded"] is False and shown["changes"] == [] and shown["state"] == "no_construction_changes"
