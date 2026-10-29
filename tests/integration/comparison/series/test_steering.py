"""Pause, resume, cancel, finish and restart (`CMP-SERIES-01`, ADR-0025 decisions 4, 16, 19): the series' work follows its
state, a command the state does not allow is `comparison_series_state`, every command is an expert's act and keyed."""

from __future__ import annotations

import pytest

from auditmanager.shared.errors import DomainError, ErrorCode

from .support import (
    ADMIN, ScriptedEngine, build, drain, fenced, items, key, make_due, pair_rows, runner_with, start, steer,
)

VERBS = ("pause", "resume", "cancel", "finish")


@pytest.fixture
def prepared(lab, matrix_service, service, expert_uid):
    doc = lab.clone()
    build(matrix_service, doc)
    return doc, start(service, doc, expert_uid)


def refused(failure: pytest.ExceptionInfo[DomainError]) -> tuple[ErrorCode, str | None]:
    return failure.value.code, failure.value.detail_fields.get("conflict_reason")


def test_a_paused_series_runs_nothing_until_it_is_resumed(lab, sessions, engine, blob_store, worker_id, service, expert_uid, prepared) -> None:
    doc, series = prepared
    sid = series["series_id"]
    fake = ScriptedEngine(sessions)
    runner = runner_with(sessions, engine, blob_store, compare=fake)
    paused = steer(service, "pause", sid, expert_uid)
    assert paused["state"] == "paused"
    assert {w["state"] for w in items(lab, sid)} == {"paused"}
    assert drain(runner, worker_id, engine, sessions, doc.project_uid) == [] and fake.calls == []

    resumed = steer(service, "resume", sid, expert_uid)
    assert resumed["state"] == "running" and {w["state"] for w in items(lab, sid)} == {"queued"}
    drain(runner, worker_id, engine, sessions, doc.project_uid)
    assert service.get_series(series_id=sid)["state"] == "completed" and len(fake.calls) == 24


def test_the_pair_in_flight_finishes_when_the_series_is_paused(lab, sessions, engine, blob_store, worker_id, service, expert_uid, prepared) -> None:
    doc, series = prepared
    sid = series["series_id"]
    runner = runner_with(sessions, engine, blob_store, compare=ScriptedEngine(sessions))
    make_due(sessions, doc.project_uid)
    with fenced(engine, doc.project_uid, ("series_drive",)):
        item = runner.claim(worker_id)
    assert item is not None and item.kind == "series_pair"
    steer(service, "pause", sid, expert_uid)  # the claimed item is not paused: an item is one pair
    assert runner.execute(item) == "succeeded"
    states = [w["state"] for w in items(lab, sid)]
    assert states.count("succeeded") == 1 and states.count("paused") == 24
    assert [p["state"] for p in pair_rows(lab, sid)].count("done") == 3  # the two immediate pairs and the one finished


@pytest.mark.parametrize("verb", VERBS)
def test_a_command_the_state_does_not_allow_is_comparison_series_state(lab, service, expert_uid, prepared, verb: str) -> None:
    doc, series = prepared
    sid = series["series_id"]
    if verb in ("resume", "finish"):  # a series that is queued is neither paused nor finished
        with pytest.raises(DomainError) as queued:
            steer(service, verb, sid, expert_uid)
        assert refused(queued) == (ErrorCode.CONFLICT, "comparison_series_state")
    steer(service, "cancel", sid, expert_uid)
    if verb in ("pause", "resume", "cancel"):
        with pytest.raises(DomainError) as ended:
            steer(service, verb, sid, expert_uid)
        assert refused(ended) == (ErrorCode.CONFLICT, "comparison_series_state")
    assert service.get_series(series_id=sid)["state"] == "cancelled"


def test_finish_with_nothing_left_is_refused(lab, sessions, engine, blob_store, worker_id, service, expert_uid, prepared) -> None:
    doc, series = prepared
    drain(runner_with(sessions, engine, blob_store, compare=ScriptedEngine(sessions)), worker_id, engine, sessions, doc.project_uid)
    assert service.get_series(series_id=series["series_id"])["state"] == "completed"
    with pytest.raises(DomainError) as nothing:
        steer(service, "finish", series["series_id"], expert_uid)
    assert refused(nothing) == (ErrorCode.CONFLICT, "comparison_series_state")


@pytest.mark.parametrize("verb", VERBS)
def test_every_command_is_an_experts_act(lab, service, expert_uid, prepared, verb: str) -> None:
    doc, series = prepared
    sid = series["series_id"]
    if verb in ("resume",):
        steer(service, "pause", sid, expert_uid)
    if verb == "finish":
        steer(service, "cancel", sid, expert_uid)
    before = service.get_series(series_id=sid)["state"]
    with pytest.raises(DomainError) as denied:
        steer(service, verb, sid, expert_uid, roles=ADMIN)
    assert denied.value.code is ErrorCode.PERMISSION_DENIED
    assert service.get_series(series_id=sid)["state"] == before


@pytest.mark.parametrize("verb", VERBS)
def test_a_repeat_of_a_key_answers_the_first_outcome_and_another_series_under_it_is_refused(
    lab, matrix_service, service, expert_uid, prepared, verb: str,
) -> None:
    doc, series = prepared
    sid = series["series_id"]
    if verb == "resume":
        steer(service, "pause", sid, expert_uid)
    if verb == "finish":
        steer(service, "cancel", sid, expert_uid)
    token = key()
    first = steer(service, verb, sid, expert_uid, idempotency_key=token)
    again = steer(service, verb, sid, expert_uid, idempotency_key=token)  # without a replay this repeat would be a state conflict
    assert again["series_id"] == sid and again["state"] == first["state"]
    other = lab.clone()
    build(matrix_service, other)
    elsewhere = start(service, other, expert_uid)
    with pytest.raises(DomainError) as reuse:
        steer(service, verb, elsewhere["series_id"], expert_uid, idempotency_key=token)
    assert reuse.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


@pytest.mark.parametrize("verb", VERBS)
def test_an_unknown_series_is_not_found(service, expert_uid, verb: str) -> None:
    with pytest.raises(DomainError) as missing:
        steer(service, verb, "cser_01ARZ3NDEKTSV4RRFFQ69G5FAV", expert_uid)
    assert missing.value.code is ErrorCode.NOT_FOUND


def test_a_cancel_that_reaches_an_item_in_flight_puts_its_pair_back_and_writes_no_result(
    lab, sessions, engine, blob_store, worker_id, service, expert_uid, prepared,
) -> None:
    doc, series = prepared
    sid = series["series_id"]
    fake = ScriptedEngine(sessions)
    cancelled_in_flight: list[str] = []

    def cancel_while_computing(*_args, **_kwargs) -> None:
        cancelled_in_flight.append(steer(service, "cancel", sid, expert_uid)["state"])

    fake.on_call = cancel_while_computing
    runner = runner_with(sessions, engine, blob_store, compare=fake)
    make_due(sessions, doc.project_uid)
    with fenced(engine, doc.project_uid, ("series_drive",)):
        item = runner.claim(worker_id)
    assert item is not None and item.kind == "series_pair"
    assert runner.execute(item) == "cancelled"
    assert cancelled_in_flight == ["cancelled"]
    rows = pair_rows(lab, sid)
    assert [p["state"] for p in rows].count("computing") == 0 and [p["state"] for p in rows].count("done") == 2  # the immediate pairs only
    assert all(p["result_id"] is None for p in rows)
    assert lab.rows("SELECT count(*) AS n FROM comparison_sheet_pair_result WHERE project_uid = :p", p=doc.project_uid)[0]["n"] == 0


def test_cancel_marks_the_unfinished_transitions_and_leaves_the_finished_ones(
    lab, sessions, engine, blob_store, worker_id, service, expert_uid, prepared,
) -> None:
    doc, series = prepared
    sid = series["series_id"]
    runner = runner_with(sessions, engine, blob_store, compare=ScriptedEngine(sessions))
    for _ in range(6):  # the six pairs of the first transition (the strongest priority)
        make_due(sessions, doc.project_uid)
        with fenced(engine, doc.project_uid, ("series_drive",)):
            item = runner.claim(worker_id)
        assert item is not None and runner.execute(item) == "succeeded"
    make_due(sessions, doc.project_uid)
    with fenced(engine, doc.project_uid):
        drive = runner.claim(worker_id)
    assert drive is not None and drive.kind == "series_drive" and runner.execute(drive) == "queued"
    assert service.get_series(series_id=sid)["transitions"][0]["state"] == "completed"
    cancelled = steer(service, "cancel", sid, expert_uid)
    assert [t["state"] for t in cancelled["transitions"]] == ["completed", "cancelled", "cancelled", "cancelled"]
    assert (cancelled["transitions_total"], cancelled["transitions_done"]) == (4, 1)
