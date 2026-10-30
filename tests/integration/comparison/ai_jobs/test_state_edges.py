"""`CMP-AI-JOBS-01`: the state edges -- pause, resume, cancel, dequeue, finish, retry -- on the job and its work items, the
refusal of an edge that is not allowed, the consents that a resume and a retry carry, and the replay of a keyed command."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.public import AiMode, AiScope, Completed, Failed
from auditmanager.comparison.ai_jobs.service import COMMAND_EDGES
from auditmanager.comparison.spend.pull_images import ComparisonCallContext
from auditmanager.shared.errors import DomainError, ErrorCode

KIND = "comparison_pair_check"
STATES = ("queued", "running", "paused", "completed", "failed", "cancelled")
#: The states each command may be taken from, written out from the contract's operation descriptions -- an oracle of its own,
#: not the table under test («A job that is not queued or running is 409 comparison_ai_job_state», «only a job that has not
#: started», «a paused job», ...).
ALLOWED = {
    "pause": {"queued", "running"},
    "resume": {"paused"},
    "cancel": {"queued", "running", "paused"},
    "dequeue": {"queued"},
    "finish": {"paused", "cancelled", "failed", "completed"},
    "retry": {"completed", "failed", "cancelled"},
}


@pytest.fixture
def w(db: Any, h: Any, world: dict[str, Any], scope_of: Any) -> Any:
    route = h.recorded_route(db.connection, KIND)
    method = h.FakeMethod(method="pair_check")
    service = db.service(method)
    scope = scope_of("pair_check")
    view = db.start(service, scope)
    return SimpleNamespace(route=route, method=method, service=service, scope=scope, job=view.record.job_id, world=world)


def cmd(db: Any, name: str, key: str | None = None) -> Any:
    return db.command(f"{name}_comparison_ai_pair_check", key=key)


def call(db: Any, w: Any, name: str, **over: Any) -> Any:
    return getattr(w.service, name)(job_id=w.job, method="pair_check", command=cmd(db, name), **over)


def job_state(db: Any, w: Any) -> tuple[str, str | None]:
    row = db.rows("SELECT state, pause_reason FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=w.job)[0]
    return row["state"], row["pause_reason"]


def item_states(db: Any, w: Any) -> list[str]:
    return [r["state"] for r in db.rows(
        "SELECT state FROM comparison_work WHERE comparison_ai_job_id = :j ORDER BY dedupe_key", j=w.job)]


def run_items(db: Any, h: Any, w: Any, outcomes: list[Any]) -> None:
    """Claim the job's items one by one and end each with the next outcome."""
    worker = db.worker()
    for outcome in outcomes:
        item = db.claim(worker, KIND)
        assert item is not None
        with db.sessions() as session:
            db.work.finish(session, item.authority, outcome)
            session.commit()


def into(db: Any, h: Any, w: Any, state: str) -> None:
    """Drive the job to ``state`` the way production does: the commands and the worker's side."""
    if state == "queued":
        return
    if state == "cancelled":
        call(db, w, "cancel")
    elif state == "paused":
        call(db, w, "pause")
    elif state == "failed":
        with db.sessions() as session:
            assert w.service.fail(session, w.job, "executor_gone")
            session.commit()
    else:
        with db.sessions() as session:
            assert w.service.mark_running(session, w.job) == "running"
            session.commit()
        if state == "completed":
            run_items(db, h, w, [Completed()] * 3)
            with db.sessions() as session:
                assert w.service.complete_if_drained(session, w.job)
                session.commit()
    assert job_state(db, w)[0] == state


def snapshot(db: Any, w: Any) -> Any:
    return (
        job_state(db, w), item_states(db, w), db.state("SELECT count(*) FROM command_record"),
        db.state("SELECT consent_no FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=w.job),
    )


# -- pause, resume ---------------------------------------------------------------------------------------------------


def test_a_pause_stops_the_job_and_its_waiting_items_and_a_resume_gives_them_back(db: Any, h: Any, w: Any) -> None:
    view = call(db, w, "pause")
    assert (view.record.state, view.record.pause_reason) == ("paused", "user")
    assert item_states(db, w) == ["paused"] * 3
    resumed = call(db, w, "resume")
    assert (resumed.record.state, resumed.record.pause_reason, resumed.record.consent_no) == ("queued", None, 1)
    assert item_states(db, w) == ["queued"] * 3


def test_a_pull_call_context_reads_the_claimed_attempt_watchdog(db: Any, h: Any, w: Any) -> None:
    item = db.claim(db.worker(), KIND)
    assert item is not None
    context = ComparisonCallContext(db.sessions)
    context.bind(item, "cmc_prepared")
    assert context.comparison_attempt_id == item.attempt_id and context.call_id == "cmc_prepared"
    assert 0.0 < context.remaining_seconds() <= 900.0


def test_a_pause_leaves_the_item_in_flight_to_finish(db: Any, h: Any, w: Any) -> None:
    worker = db.worker()
    held = db.claim(worker, KIND)
    assert held is not None
    call(db, w, "pause")
    assert sorted(item_states(db, w)) == ["paused", "paused", "running"]
    with db.sessions() as session:
        db.work.finish(session, held.authority, Completed())
        session.commit()
    assert sorted(item_states(db, w)) == ["paused", "paused", "succeeded"]


def test_a_resume_after_a_pause_for_the_user_ignores_a_consent(db: Any, h: Any, w: Any) -> None:
    call(db, w, "pause")
    view = call(db, w, "resume", consent=db.consent("f" * 64))
    assert view.record.state == "queued" and view.record.consent_no == 1


@pytest.mark.parametrize("reason", ["overrun", "route_changed"])
def test_a_resume_after_overrun_or_route_change_needs_a_new_consent_for_what_is_left(db: Any, h: Any, w: Any, reason: str) -> None:
    with db.sessions() as session:
        assert w.service.pause_system(session, w.job, reason)
        session.commit()
    assert job_state(db, w) == ("paused", reason)
    w.method.counts_by_mode[AiMode.LEFT] = h.counts_for(4)
    before = snapshot(db, w)
    with pytest.raises(DomainError) as missing:
        call(db, w, "resume")
    assert missing.value.code is ErrorCode.VALIDATION_FAILED
    assert dict(missing.value.detail_fields) == {"field": "consent", "constraint": "comparison_consent_required"}
    with pytest.raises(DomainError) as unconfirmed:
        call(db, w, "resume", consent=db.consent("a" * 64, confirmed=False))
    assert unconfirmed.value.code is ErrorCode.VALIDATION_FAILED
    with pytest.raises(DomainError) as stale:
        call(db, w, "resume", consent=db.consent("a" * 64))
    assert h.conflict_reason(stale) == "comparison_estimate_stale"
    assert snapshot(db, w) == before
    # The public estimate GET uses this read; its digest must be the one resume accepts.
    left = w.service.estimate(w.scope)
    assert left.totals.calls == 4
    view = call(db, w, "resume", consent=db.consent(left.estimate_digest))
    assert (view.record.state, view.record.consent_no, view.record.estimate_digest) == ("queued", 2, left.estimate_digest)
    assert view.record.estimate["calls"] == 4 and view.record.estimate_micros == left.estimate_micros
    assert item_states(db, w) == ["queued"] * 3


def test_a_resume_with_a_new_consent_counts_what_the_job_has_spent_against_the_job_ceiling(db: Any, h: Any, w: Any) -> None:
    item = db.claim(db.worker(), KIND)
    h.insert_call(db.connection, item, cost_micros=9_800_000, revision_id=w.route.revision_id)
    with db.sessions() as session:
        assert w.service.pause_system(session, w.job, "overrun")
        session.commit()
    w.method.counts_by_mode[AiMode.LEFT] = h.counts_for(10)  # USD 0.49 more would pass USD 10 after USD 9.80
    left = w.service.estimate_in(db.sessions(), w.scope, AiMode.LEFT, job=w.service.job(db.sessions(), w.job))
    assert left.blocked_by == "job"
    before = snapshot(db, w)
    with pytest.raises(DomainError) as refused:
        call(db, w, "resume", consent=db.consent(left.estimate_digest))
    assert h.conflict_reason(refused) == "comparison_ceiling_job"
    assert snapshot(db, w) == before


# -- cancel, dequeue -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("state", ["queued", "running", "paused"])
def test_a_live_job_is_cancelled_with_its_items(db: Any, h: Any, w: Any, state: str) -> None:
    into(db, h, w, state)
    view = call(db, w, "cancel")
    assert view.record.state == "cancelled" and view.record.finished_at is not None and view.record.pause_reason is None
    assert item_states(db, w) == ["cancelled"] * 3


def test_a_cancel_asks_the_item_in_flight_to_stop(db: Any, h: Any, w: Any) -> None:
    worker = db.worker()
    held = db.claim(worker, KIND)
    call(db, w, "cancel")
    assert sorted(item_states(db, w)) == ["cancelled", "cancelled", "running"]
    assert db.state("SELECT cancel_requested_at IS NOT NULL FROM comparison_work WHERE comparison_work_id = :w", w=held.work_id)


def test_a_job_that_has_not_started_leaves_the_queue_and_one_that_has_started_does_not(db: Any, h: Any, w: Any) -> None:
    view = call(db, w, "dequeue")
    assert view.record.state == "cancelled" and item_states(db, w) == ["cancelled"] * 3


def test_a_job_with_a_claimed_item_has_started_and_cannot_be_dequeued(db: Any, h: Any, w: Any) -> None:
    db.claim(db.worker(), KIND)
    before = snapshot(db, w)
    with pytest.raises(DomainError) as refused:
        call(db, w, "dequeue")
    assert h.conflict_reason(refused) == "comparison_ai_job_state"
    assert snapshot(db, w) == before


def test_a_resumed_job_that_had_started_cannot_be_dequeued(db: Any, h: Any, w: Any) -> None:
    held = db.claim(db.worker(), KIND)
    call(db, w, "pause")
    with db.sessions() as session:
        db.work.finish(session, held.authority, Completed())
        session.commit()
    call(db, w, "resume")
    assert job_state(db, w)[0] == "queued"
    with pytest.raises(DomainError) as refused:
        call(db, w, "dequeue")
    assert h.conflict_reason(refused) == "comparison_ai_job_state"


# -- finish, retry ---------------------------------------------------------------------------------------------------


def test_finish_queues_the_units_with_no_result_under_the_consent_the_job_holds(db: Any, h: Any, w: Any) -> None:
    run_items(db, h, w, [Completed()])
    call(db, w, "cancel")
    w.method.units[AiMode.LEFT] = ["u1", "u2"]
    view = call(db, w, "finish")
    assert (view.record.state, view.record.consent_no) == ("queued", 1)
    # the two units are counted once, by their newest item; the cancelled ones are replaced
    assert view.progress.total == 3 and view.progress.by_state == {"succeeded": 1, "queued": 2}
    assert db.state("SELECT count(*) FROM comparison_work WHERE comparison_ai_job_id = :j", j=w.job) == 5


def test_finish_with_nothing_left_is_nothing_to_do(db: Any, h: Any, w: Any) -> None:
    call(db, w, "cancel")
    w.method.units[AiMode.LEFT] = []
    before = snapshot(db, w)
    with pytest.raises(DomainError) as refused:
        call(db, w, "finish")
    assert h.conflict_reason(refused) == "comparison_ai_nothing_to_do"
    assert snapshot(db, w) == before


def test_finish_of_a_paused_job_takes_its_paused_items_up(db: Any, h: Any, w: Any) -> None:
    call(db, w, "pause")
    w.method.units[AiMode.LEFT] = []
    view = call(db, w, "finish")
    assert view.record.state == "queued" and item_states(db, w) == ["queued"] * 3


def test_finish_of_a_job_paused_for_overrun_needs_the_consent_of_a_resume(db: Any, h: Any, w: Any) -> None:
    with db.sessions() as session:
        w.service.pause_system(session, w.job, "overrun")
        session.commit()
    w.method.units[AiMode.LEFT] = ["u0"]
    before = snapshot(db, w)
    with pytest.raises(DomainError) as refused:
        call(db, w, "finish")
    assert h.conflict_reason(refused) == "comparison_ai_job_state"
    assert snapshot(db, w) == before


def test_retry_queues_only_the_failed_units_under_a_new_consent(db: Any, h: Any, w: Any) -> None:
    into(db, h, w, "running")
    run_items(db, h, w, [Completed(), Failed("provider_refused"), Completed()])
    with db.sessions() as session:
        assert w.service.complete_if_drained(session, w.job)
        session.commit()
    done = w.service.view(w.job)
    assert (done.record.state, done.progress.done, done.progress.failed) == ("completed", 2, 1)
    w.method.units[AiMode.FAILED] = ["u1"]
    w.method.counts_by_mode[AiMode.FAILED] = h.counts_for(1)
    failed = w.service.estimate_in(db.sessions(), w.scope, AiMode.FAILED, job=w.service.job(db.sessions(), w.job))
    before = snapshot(db, w)
    with pytest.raises(DomainError) as stale:
        call(db, w, "retry", consent=db.consent("a" * 64))
    assert h.conflict_reason(stale) == "comparison_estimate_stale"
    with pytest.raises(DomainError) as required:
        call(db, w, "retry", consent=db.consent(failed.estimate_digest, confirmed=False))
    assert required.value.code is ErrorCode.VALIDATION_FAILED
    assert snapshot(db, w) == before
    view = call(db, w, "retry", consent=db.consent(failed.estimate_digest))
    assert (view.record.state, view.record.consent_no, view.record.estimate_digest) == ("queued", 2, failed.estimate_digest)
    assert view.record.estimate_micros == failed.estimate_micros == 49_000
    assert view.record.finished_at is None
    assert view.progress.total == 3 and view.progress.done == 2 and view.progress.failed == 0
    assert view.progress.by_state == {"succeeded": 2, "queued": 1}


def test_retry_with_no_failed_unit_is_nothing_to_do(db: Any, h: Any, w: Any) -> None:
    call(db, w, "cancel")
    w.method.counts_by_mode[AiMode.FAILED] = h.counts_for(0, units=0)
    digest = w.service.estimate_in(db.sessions(), w.scope, AiMode.FAILED, job=w.service.job(db.sessions(), w.job)).estimate_digest
    before = snapshot(db, w)
    with pytest.raises(DomainError) as refused:
        call(db, w, "retry", consent=db.consent(digest))
    assert h.conflict_reason(refused) == "comparison_ai_nothing_to_do"
    assert snapshot(db, w) == before


def test_a_job_cannot_go_back_to_queued_while_another_live_job_holds_its_scope(db: Any, h: Any, w: Any) -> None:
    call(db, w, "cancel")
    other = db.start(w.service, w.scope)
    w.method.units[AiMode.LEFT] = ["u0"]
    before = snapshot(db, w)
    with pytest.raises(DomainError) as refused:
        call(db, w, "finish")
    assert h.conflict_reason(refused) == "comparison_ai_job_active"
    assert snapshot(db, w) == before
    assert other.record.state == "queued"


def test_the_database_index_holds_the_scope_when_a_finish_races_past_the_look(db: Any, h: Any, w: Any) -> None:
    call(db, w, "cancel")
    db.start(w.service, w.scope)
    w.method.units[AiMode.LEFT] = ["u0"]
    repo = type(w.service._repo)
    kept = repo.live_on_scope
    repo.live_on_scope = lambda self, session, scope: None  # type: ignore[method-assign]
    try:
        with pytest.raises(DomainError) as refused:
            call(db, w, "finish")
    finally:
        repo.live_on_scope = kept  # type: ignore[method-assign]
    assert h.conflict_reason(refused) == "comparison_ai_job_active"


# -- the edges that are not allowed ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("command", "state"),
    [(command, state) for command in sorted(ALLOWED) for state in STATES if state not in ALLOWED[command]],
)
def test_a_command_from_a_state_it_may_not_be_taken_from_is_refused_and_changes_nothing(
    db: Any, h: Any, w: Any, command: str, state: str
) -> None:
    into(db, h, w, state)
    before = snapshot(db, w)
    extra: dict[str, Any] = {"consent": db.consent("a" * 64)} if command == "retry" else {}
    with pytest.raises(DomainError) as refused:
        call(db, w, command, **extra)
    assert h.conflict_reason(refused) == "comparison_ai_job_state"
    assert snapshot(db, w) == before


def test_the_command_edges_are_the_ones_the_contract_describes() -> None:
    assert {command: set(states) for command, states in COMMAND_EDGES.items()} == ALLOWED


def test_the_command_edges_are_edges_the_database_declares() -> None:
    """Every state a command may be taken from can reach the state the command takes it to, by the migration's own table."""
    import importlib.util
    from pathlib import Path

    path = next(Path("db/migrations/versions").glob("*_0040_comparison_ai_reports.py"))
    spec = importlib.util.spec_from_file_location("migration_0040_for_edges", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    declared = {(a, b) for table, a, b in module.EDGES if table == "comparison_ai_job"}
    targets = {"pause": "paused", "resume": "queued", "cancel": "cancelled", "dequeue": "cancelled", "finish": "queued", "retry": "queued"}
    for command, states in COMMAND_EDGES.items():
        for state in states:
            assert (state, targets[command]) in declared, (command, state)
    assert {"queued", "running", "paused", "completed", "failed", "cancelled"} == set(STATES) == set(module.JOB_STATES)


# -- who may, which job, the module flag, the key ---------------------------------------------------------------------


@pytest.mark.parametrize("command", sorted(COMMAND_EDGES))
def test_every_command_is_an_experts_and_behind_the_module_flag(db: Any, h: Any, w: Any, command: str) -> None:
    extra: dict[str, Any] = {"consent": db.consent("a" * 64)} if command == "retry" else {}
    off = db.service(w.method, modules="none")
    before = snapshot(db, w)
    with pytest.raises(DomainError) as module:
        getattr(off, command)(job_id=w.job, method="pair_check", command=cmd(db, command), **extra)
    assert module.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE and module.value.detail_fields["dependency"] == "comparison_modules"
    with pytest.raises(DomainError) as role:
        getattr(w.service, command)(job_id=w.job, method="pair_check", command=db.command(f"{command}_x", roles=frozenset({"admin"})), **extra)
    assert role.value.code is ErrorCode.PERMISSION_DENIED
    assert snapshot(db, w) == before


def test_an_unknown_job_and_a_job_of_another_method_are_not_found(db: Any, h: Any, w: Any) -> None:
    with pytest.raises(DomainError) as unknown:
        w.service.pause(job_id=h.new_id("cai"), method="pair_check", command=cmd(db, "pause"))
    assert unknown.value.code is ErrorCode.NOT_FOUND
    other = db.service(w.method, h.FakeMethod(method="spec"))
    with pytest.raises(DomainError) as wrong:
        other.pause(job_id=w.job, method="spec", command=cmd(db, "pause"))
    assert wrong.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(DomainError) as read:
        w.service.view(w.job, method="spec")
    assert read.value.code is ErrorCode.NOT_FOUND


def test_a_repeat_of_a_keyed_steering_command_replays_it_and_a_changed_payload_is_refused(db: Any, h: Any, w: Any) -> None:
    command = cmd(db, "pause", key="pause-key-0001")
    first = w.service.pause(job_id=w.job, method="pair_check", command=command)
    again = w.service.pause(job_id=w.job, method="pair_check", command=command)
    assert again.record.state == first.record.state == "paused" and again.record.updated_at == first.record.updated_at
    # the same key for another job is a different payload
    h.recorded_route(db.connection, "comparison_spec")
    both = db.service(w.method, h.FakeMethod(method="spec"))
    spec_scope = AiScope(method="spec", project_uid=w.world["project"], document_uid=w.world["document"], transition_id=w.world["transition"])
    spec = db.start(both, spec_scope, command=db.command("start_comparison_specification"))
    with pytest.raises(DomainError) as reused:
        both.pause(job_id=spec.record.job_id, method="spec", command=command)
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
