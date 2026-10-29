"""The safety rules of the sheet descriptions, each with the test that fails the day it is broken (`CMP-VC-AISHEET-01`).

* a claim the raw evidence does not contain is never a confirmed change;
* a stored description is never requested again, whatever the job;
* a retry touches only the sheets that failed;
* a request carries at most eight pictures;
* the spend is written before the call, a cost over the consent pauses the job, an outcome nobody knows is never sent again;
* the descriptions are an expert's act and the writes are keyed.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from auditmanager.analysis.public import ModelResponse, ProviderMode
from auditmanager.comparison.spend.model import SpendPause  # noqa: F401  (documents the pause the wrapper reports)
from auditmanager.shared.errors import DomainError, ErrorCode

from .conftest import ADMIN, EXPERT, FixedRoutes, core, fx, support


def conflict(error: Any) -> str:
    return core.conflict_reason(error)


# -- a claim the raw evidence does not contain ----------------------------------------------------------------------------------------


def test_a_value_the_sheet_does_not_contain_is_stored_as_unverified_never_as_a_confirmed_change(lab: Any) -> None:
    packet, _request = lab.packet_of("p1")
    claim = lab.good_answer(packet)
    claim["changes"][0]["fields"][0]["after"] = "97"
    claim["changes"][0]["summary"] = "Лк-1 — количество 2 → 97."
    lab.record("p1", claim)
    lab.record("p6")
    lab.record_single("p4")
    lab.record_single("p5")
    lab.start_series()
    lab.drain()
    description = lab.service.get_description(sheet_pair_id=lab.world["p1"].pair)
    change = description["changes"][0]
    assert (change["now"], change["now_tier"], change["certainty"]) == ("97", "unverified", "unclear")
    assert "VALUE_UNVERIFIED" in description["diagnostics"]["issues"]
    stored = lab.db.rows("SELECT description FROM comparison_sheet_description WHERE result_id = :r", r=lab.world["p1"].result)[0]["description"]
    assert stored["changes"][0]["confirmation"] == "unverified" and stored["engineer_confirmed"] is False
    assert b"(\xd0\xbd\xd0\xb5 \xd0\xbf\xd0\xbe\xd0\xb4\xd1\x82\xd0\xb2\xd0\xb5\xd1\x80\xd0\xb6\xd0\xb4\xd0\xb5\xd0\xbd\xd0\xbe)" in lab.service.read_md(sheet_pair_id=lab.world["p1"].pair)


def test_a_number_and_a_place_that_no_text_of_the_sheet_holds_make_the_change_unclear(lab: Any) -> None:
    packet, _request = lab.packet_of("p1")
    claim = lab.good_answer(packet)
    claim["changes"][0]["summary"] = "Лк-1 — количество 2 → 3, смета 7777 руб."
    claim["changes"][0]["place"] = "оси 17-18, помещение 304"
    lab.record("p1", claim)
    lab.record("p6")
    lab.record_single("p4")
    lab.record_single("p5")
    lab.start_series()
    lab.drain()
    change = lab.service.get_description(sheet_pair_id=lab.world["p1"].pair)["changes"][0]
    assert change["certainty"] == "unclear" and "7777" in change["limitation"] and "17-18" in change["limitation"]


def test_the_raw_evidence_is_the_same_before_and_after_a_description(lab: Any) -> None:
    before = lab.db.rows("SELECT comparison_sheet_pair_result_id, result, status, reasons, channels FROM comparison_sheet_pair_result "
                         "WHERE project_uid = :p ORDER BY 1", p=lab.world.project)
    pairs_before = lab.db.rows("SELECT * FROM comparison_sheet_pair WHERE comparison_transition_id = :t ORDER BY pair_no", t=lab.world.transition)
    for name in ("p1", "p6"):
        lab.record(name)
    lab.record_single("p4")
    lab.record_single("p5")
    lab.start_series()
    lab.drain()
    assert lab.db.rows("SELECT comparison_sheet_pair_result_id, result, status, reasons, channels FROM comparison_sheet_pair_result "
                       "WHERE project_uid = :p ORDER BY 1", p=lab.world.project) == before
    assert lab.db.rows("SELECT * FROM comparison_sheet_pair WHERE comparison_transition_id = :t ORDER BY pair_no", t=lab.world.transition) == pairs_before


# -- never asked twice ------------------------------------------------------------------------------------------------------------------


def test_a_stored_description_is_never_requested_again_by_another_job(lab: Any) -> None:
    for name in ("p1", "p6"):
        lab.record(name)
    lab.record_single("p4")
    lab.record_single("p5")
    series = lab.start_series()
    single = lab.start_pair("p1")  # a second job over the same sheet, started before either ran
    assert single["sheet_pair_id"] == lab.world["p1"].pair
    lab.drain()
    assert lab.answers.calls == 4, "p1 is asked once although two jobs listed it"
    descriptions = lab.db.rows("SELECT result_id FROM comparison_sheet_description WHERE result_id = :r", r=lab.world["p1"].result)
    assert len(descriptions) == 1
    assert lab.items(series["job_id"])["p1"] == "done" and lab.items(single["job_id"]) == {"p1": "done"}
    assert {lab.job(series["job_id"])["state"], lab.job(single["job_id"])["state"]} == {"completed"}


def test_a_series_whose_sheets_are_all_described_has_nothing_to_send(lab: Any) -> None:
    for name in ("p1", "p6"):
        lab.record(name)
    lab.record_single("p4")
    lab.record_single("p5")
    lab.start_series()
    lab.drain()
    again = lab.service.estimate_series(series_id=lab.world.series, only_failed=False)
    assert again["calls"] == 0 and again["reused"] == 5 and again["units"] == 5
    with pytest.raises(DomainError) as refused:
        lab.service.start_series(series_id=lab.world.series, consent=lab.consent(again["estimate_digest"]), restart=False,
                                 command=lab.command())
    assert conflict(refused) == "comparison_ai_nothing_to_do"
    asked = lab.answers.calls
    with pytest.raises(DomainError) as refused:
        lab.service.start_series(series_id=lab.world.series, consent=lab.consent(again["estimate_digest"]), restart=True,
                                 command=lab.command())
    assert conflict(refused) == "comparison_ai_nothing_to_do" and lab.answers.calls == asked


def test_a_new_prompt_version_is_a_new_question_and_the_old_description_stays_as_history(lab: Any) -> None:
    with lab.db.sessions() as session:
        pair = lab.repo.pair(session, lab.world["p1"].pair)
        lab.repo.insert_description(
            session, project_uid=lab.world.project, key=support.digest("old"), result_id=pair.result_id, page_profile_id=None, state="done",
            prompt_version="sheet-changes/0+deadbeef0000", model_identity="recorded", recorded=True,
            description={"schema": "x", "state": "done", "changes": [], "unresolved": [], "excluded": [], "diagnostics": {}}, calls=1,
            input_tokens=1, output_tokens=1, model_call_id=None)
        session.commit()
    stale = lab.service.get_description(sheet_pair_id=lab.world["p1"].pair)
    assert stale["state"] == "stale" and stale["history_count"] == 1
    estimate = lab.service.estimate_series(series_id=lab.world.series, only_failed=False)
    assert estimate["reused"] == 0 and estimate["calls"] == 4, "an old prompt's answer is not this prompt's answer"


def test_a_digest_the_user_saw_is_stale_once_a_sheet_has_been_described_since(lab: Any) -> None:
    seen = lab.service.estimate_series(series_id=lab.world.series, only_failed=False)
    for name in ("p1",):
        lab.record(name)
    lab.start_pair("p1")
    lab.drain()
    with pytest.raises(DomainError) as refused:
        lab.service.start_series(series_id=lab.world.series, consent=lab.consent(seen["estimate_digest"]), restart=False, command=lab.command())
    assert conflict(refused) == "comparison_estimate_stale"
    assert lab.db.rows("SELECT 1 FROM comparison_ai_job WHERE comparison_series_id IS NOT NULL") == []


def test_a_restart_is_consented_to_the_digest_of_the_estimate_without_it_and_a_stale_one_is_refused(lab: Any) -> None:
    seen = lab.service.estimate_series(series_id=lab.world.series, only_failed=False)
    for name in ("p6",):
        lab.record(name)
    lab.record("p1")
    lab.record_single("p4")
    lab.record_single("p5")
    with pytest.raises(DomainError) as refused:
        lab.service.start_series(series_id=lab.world.series, consent=lab.consent("f" * 64), restart=True, command=lab.command())
    assert conflict(refused) == "comparison_estimate_stale"
    job = lab.service.start_series(series_id=lab.world.series, consent=lab.consent(seen["estimate_digest"]), restart=True, command=lab.command())
    assert lab.job(job["job_id"])["restart"] is True and job["counts"]["total"] == 5
    with pytest.raises(DomainError) as refused:  # a restart that asks for a consent that was not given
        lab.service.start_series(series_id=lab.world.series, consent=lab.consent(seen["estimate_digest"], confirmed=False), restart=True,
                                 command=lab.command())
    assert refused.value.code is ErrorCode.VALIDATION_FAILED


# -- a retry touches only the failed sheets ---------------------------------------------------------------------------------------------


def test_a_retry_describes_again_only_the_sheets_that_failed(lab: Any) -> None:
    lab.record("p1")
    lab.record_single("p4")
    lab.record_single("p5")  # p6 has no recorded answer: its call fails, whatever the model might have said
    job = lab.start_series()
    lab.drain()
    assert lab.items(job["job_id"]) == {"p1": "done", "p2": "done", "p4": "done", "p5": "done", "p6": "failed"}
    failed = lab.db.rows("SELECT failure_reason FROM comparison_ai_sheet_item WHERE comparison_sheet_pair_id = :p", p=lab.world["p6"].pair)
    assert failed[0]["failure_reason"] == "analysis_input_invalid"
    assert lab.job(job["job_id"])["state"] == "completed"
    done_before = {r["pair"]: r["updated_at"] for r in lab.db.rows(
        "SELECT comparison_sheet_pair_id AS pair, updated_at FROM comparison_ai_sheet_item WHERE state = 'done'")}
    asked = lab.answers.calls

    estimate = lab.service.estimate_series(series_id=lab.world.series, only_failed=True)
    assert (estimate["units"], estimate["calls"]) == (1, 1)
    lab.record("p6")
    retried = lab.service.retry(job_id=job["job_id"], consent=lab.consent(estimate["estimate_digest"]),
                                command=lab.command("retry_comparison_ai_sheet_changes"))
    assert retried["state"] == "queued" and retried["counts"]["total"] == 5
    lab.drain()
    assert lab.answers.calls == asked + 1, "exactly the failed sheet was sent again"
    assert lab.items(job["job_id"]) == {n: "done" for n in ("p1", "p2", "p4", "p5", "p6")}
    done_after = {r["pair"]: r["updated_at"] for r in lab.db.rows(
        "SELECT comparison_sheet_pair_id AS pair, updated_at FROM comparison_ai_sheet_item WHERE state = 'done'")}
    assert all(done_after[p] == t for p, t in done_before.items()), "the sheets that were done are not touched"
    assert lab.job(job["job_id"])["state"] == "completed"


def test_a_retry_with_no_failed_sheet_has_nothing_to_do(lab: Any) -> None:
    for name in ("p1", "p6"):
        lab.record(name)
    lab.record_single("p4")
    lab.record_single("p5")
    job = lab.start_series()
    lab.drain()
    estimate = lab.service.estimate_series(series_id=lab.world.series, only_failed=True)
    assert estimate["calls"] == 0
    with pytest.raises(DomainError) as refused:
        lab.service.retry(job_id=job["job_id"], consent=lab.consent(estimate["estimate_digest"]),
                          command=lab.command("retry_comparison_ai_sheet_changes"))
    assert conflict(refused) == "comparison_ai_nothing_to_do"


# -- eight pictures at most ----------------------------------------------------------------------------------------------------------


def test_a_request_carries_at_most_eight_pictures_even_for_a_sheet_with_a_dozen_places(lab: Any) -> None:
    result = fx.table_result()
    for n in range(12):
        x, y = 700 + (n % 4) * 600, 300 + (n // 4) * 600
        result["text_changes"].append({"kind": "changed", "before": f"Щ-{n}", "after": f"Щ-{n + 1}", "box": fx.box(x, y, x + 30, y + 10)})
    support.add_table_pair(lab.db.connection, lab.world, fx, "p7", result, pair_no=7, pages=lab.material.pages)
    packet, request = lab.packet_of("p7")
    assert len(packet.images) == 8 and len(packet.candidates) > 8
    lab.answers.record(request, json.dumps(lab.good_answer(packet)))
    lab.start_pair("p7")
    lab.drain()
    sent = lab.answers.requests[-1]
    assert len(sent.images_bytes) == 8 and len(sent.body["images"]) == 8
    estimate_images = lab.jobs.view(lab.db.rows("SELECT comparison_ai_job_id AS j FROM comparison_ai_job")[0]["j"]).record.estimate["images"]
    assert estimate_images == 8, "the estimate counts the same eight"


# -- the spend is written before the call; a cost over the consent pauses the job ---------------------------------------------------------


class Watching:
    """A live-mode adapter that looks at the journal when it is called and answers what the test chose."""

    def __init__(self, lab: Any, reply: ModelResponse | None = None, raises: Exception | None = None) -> None:
        self.lab, self.reply, self.raises = lab, reply, raises
        self.seen: list[list[str]] = []
        self.requests: list[Any] = []

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.LIVE

    def complete(self, request: Any) -> ModelResponse:
        self.requests.append(request)
        self.seen.append([r["state"] for r in self.lab.calls()])
        if self.raises is not None:
            raise self.raises
        assert self.reply is not None
        return self.reply


def metered(lab: Any, adapter: Any) -> None:
    core.recorded_route(lab.db.connection, "comparison_sheet_changes", billing="metered")
    lab.handler._routes = FixedRoutes(adapter, unmetered=False, pin=core.PIN)  # noqa: SLF001


def live_reply(lab: Any, packet: Any, *, cost: float) -> ModelResponse:
    return ModelResponse(output_text=json.dumps(lab.good_answer(packet)), stop_reason="end_turn", input_tokens=1000, output_tokens=200,
                         latency_ms=5, reported_cost_usd=cost, model=core.GATEWAY)


def test_the_row_of_the_journal_is_written_before_the_adapter_is_called(lab: Any) -> None:
    packet, _request = lab.packet_of("p1")
    adapter = Watching(lab, live_reply(lab, packet, cost=0.001))
    metered(lab, adapter)
    estimate = lab.service.estimate_description(sheet_pair_id=lab.world["p1"].pair)
    assert estimate["estimate_micros"] > 0, "a metered route is priced"
    lab.service.start_description(sheet_pair_id=lab.world["p1"].pair, consent=lab.consent(estimate["estimate_digest"]),
                                  command=lab.command("start_comparison_sheet_description"))
    lab.drain()
    assert adapter.seen == [["sent"]], "when the adapter ran, the journal already held the row, committed, as sent"
    assert [c["state"] for c in lab.calls()] == ["completed"] and lab.calls()[0]["provider_mode"] == "live"


def test_a_cost_over_the_consent_keeps_the_answer_and_pauses_the_job_which_sends_nothing_more(lab: Any) -> None:
    packet, _request = lab.packet_of("p1")
    adapter = Watching(lab, live_reply(lab, packet, cost=5.0))  # far over 1.2 x the estimate
    metered(lab, adapter)
    job = lab.start_series()
    assert lab.job(job["job_id"])["estimate_micros"] > 0
    lab.drain()
    assert len(adapter.requests) == 1, "the first reply took the job over its consent: no second call"
    after = lab.job(job["job_id"])
    assert (after["state"], after["pause_reason"]) == ("paused", "overrun")
    assert [d["state"] for d in lab.descriptions()] == ["done"], "the reply that was paid for is kept"
    states = lab.items(job["job_id"])
    assert list(states.values()).count("done") == 1 and "failed" not in states.values()
    assert lab.db.rows("SELECT count(*) AS n FROM comparison_work WHERE comparison_ai_job_id = :j AND state = 'paused'",
                       j=job["job_id"])[0]["n"] >= 3
    # a resume after an overrun asks for a new consent and is refused without one
    with pytest.raises(DomainError) as refused:
        lab.service.resume(job_id=job["job_id"], consent=None, command=lab.command("resume_comparison_ai_sheet_changes"))
    assert refused.value.code is ErrorCode.VALIDATION_FAILED


def test_an_outcome_nobody_knows_fails_the_sheet_and_is_not_sent_again_until_a_retry(lab: Any) -> None:
    adapter = Watching(lab, raises=RuntimeError("the connection broke after the request went out"))
    metered(lab, adapter)
    estimate = lab.service.estimate_description(sheet_pair_id=lab.world["p1"].pair)
    job = lab.service.start_description(sheet_pair_id=lab.world["p1"].pair, consent=lab.consent(estimate["estimate_digest"]),
                                        command=lab.command("start_comparison_sheet_description"))
    lab.drain()
    assert len(adapter.requests) == 1
    assert lab.items(job["job_id"]) == {"p1": "failed"}
    assert lab.db.rows("SELECT failure_reason FROM comparison_ai_sheet_item")[0]["failure_reason"] == "spend_unknown"
    assert [c["state"] for c in lab.calls()] == ["unknown"]
    assert len(adapter.requests) == 1, "nothing sends it again by itself"
    assert lab.job(job["job_id"])["state"] == "completed"


# -- the descriptions are an expert's act, the writes are keyed ----------------------------------------------------------------------


def test_an_administrator_without_the_expert_role_is_refused_every_write_and_may_read(lab: Any) -> None:
    estimate = lab.service.estimate_series(series_id=lab.world.series, only_failed=False)
    admin = lambda kind: lab.command(kind, roles=ADMIN)  # noqa: E731
    job = lab.start_series()
    writes = [
        lambda: lab.service.start_series(series_id=lab.world.series, consent=lab.consent(estimate["estimate_digest"]), restart=False,
                                         command=admin("start_comparison_ai_sheet_changes")),
        lambda: lab.service.start_description(sheet_pair_id=lab.world["p1"].pair, consent=lab.consent(estimate["estimate_digest"]),
                                              command=admin("start_comparison_sheet_description")),
        lambda: lab.service.pause(job_id=job["job_id"], command=admin("pause_comparison_ai_sheet_changes")),
        lambda: lab.service.resume(job_id=job["job_id"], consent=None, command=admin("resume_comparison_ai_sheet_changes")),
        lambda: lab.service.cancel(job_id=job["job_id"], command=admin("cancel_comparison_ai_sheet_changes")),
        lambda: lab.service.finish(job_id=job["job_id"], command=admin("finish_comparison_ai_sheet_changes")),
        lambda: lab.service.dequeue(job_id=job["job_id"], command=admin("dequeue_comparison_ai_sheet_changes")),
        lambda: lab.service.retry(job_id=job["job_id"], consent=lab.consent(estimate["estimate_digest"]),
                                  command=admin("retry_comparison_ai_sheet_changes")),
    ]
    for write in writes:
        with pytest.raises(DomainError) as refused:
            write()
        assert refused.value.code is ErrorCode.PERMISSION_DENIED
        assert refused.value.detail_fields["required_capability"] == "role:expert"
    assert lab.job(job["job_id"])["state"] == "queued"
    lab.service.get_series(series_id=lab.world.series)
    lab.service.get_description(sheet_pair_id=lab.world["p1"].pair)
    lab.service.estimate_description(sheet_pair_id=lab.world["p1"].pair)


def test_the_same_key_and_payload_replays_the_job_and_another_payload_under_the_key_is_refused(lab: Any) -> None:
    estimate = lab.service.estimate_series(series_id=lab.world.series, only_failed=False)
    command = lab.command(key="same-key-1")
    first = lab.service.start_series(series_id=lab.world.series, consent=lab.consent(estimate["estimate_digest"]), restart=False, command=command)
    again = lab.service.start_series(series_id=lab.world.series, consent=lab.consent(estimate["estimate_digest"]), restart=False,
                                     command=lab.command(key="same-key-1"))
    assert again["job_id"] == first["job_id"]
    assert lab.db.state("SELECT count(*) FROM comparison_ai_job WHERE method = 'sheet_changes'") == 1
    with pytest.raises(DomainError) as reused:
        lab.service.start_series(series_id=lab.world.series, consent=lab.consent("e" * 64), restart=False, command=lab.command(key="same-key-1"))
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
