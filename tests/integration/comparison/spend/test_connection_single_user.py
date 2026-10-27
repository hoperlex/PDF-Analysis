"""One user per executor connection, in both directions (`CMP-SPEND-01`, ADR-0025 decision 4).

* A Run's claim is refused while a comparison model call is active on the Run's connection -- **the one query
  of ``jobs/repository.py`` this lane was granted** (`_CONNECTION_HAS_OTHER_ACTIVE_RUN`). A mutation that puts
  the old query back turns the tests of this file that name it red.
* A comparison call is refused while a Run is active on its connection, and while another comparison call is.
* Both are decided under the Run claim's own advisory lock, so they cannot both pass.
* A plain Run serialises per connection exactly as before (the ``EXEC-PAR-QUEUE-01`` suites are not touched and
  stay green; the last tests here restate the behaviour with the comparison tables non-empty).
"""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.comparison.public import CallRefused, SPEND_SETTLERS
from auditmanager.jobs.public import ExecutionNotClaimed, JobRepository
from auditmanager.shared.errors import ErrorCode


def _run_claim_is_refused(sessions: Any, helpers: Any, revision: str | None) -> bool:
    """Queue a Run on ``revision`` and try the shipped claim: ``True`` if the claim was refused, in which case
    the Run and its Job are exactly as they were (queued, no Attempt)."""
    run_id = helpers.queue_run(sessions, revision)
    try:
        try:
            authority = helpers.claim(sessions, run_id)
        except ExecutionNotClaimed as refusal:
            assert refusal.code is ErrorCode.CONFLICT
            assert helpers.job_state(sessions, run_id) == "queued" and helpers.attempts(sessions, run_id) == 0
            return True
        helpers.finish(sessions, authority)
        return False
    finally:
        helpers.cancel(sessions, run_id)


# --- a Run's claim counts an active comparison call (the granted query) ------------------------------------------


@pytest.mark.parametrize(("state", "blocks"), [
    ("prepared", True), ("sent", True), ("completed", False), ("failed", False), ("unknown", False),
])
def test_a_runs_claim_is_refused_exactly_while_a_comparison_call_is_open_on_its_connection(
    state: str, blocks: bool, queue: Any, journal: Any, sessions: Any, helpers: Any, connection: tuple[str, str],
) -> None:
    item = queue.claimed()
    journal.insert(item.work_id, item.attempt_id, state=state, estimate_micros=1, cost_micros=1,
                   connection_revision_id=connection[1])
    assert _run_claim_is_refused(sessions, helpers, connection[1]) is blocks


def test_a_runs_claim_is_not_refused_by_a_call_on_another_connection_or_by_a_run_with_none(
    queue: Any, journal: Any, sessions: Any, helpers: Any, connection: tuple[str, str],
) -> None:
    item = queue.claimed()
    journal.insert(item.work_id, item.attempt_id, state="sent", estimate_micros=1,
                   connection_revision_id=connection[1])
    _other_connection, other_revision = helpers.new_connection(sessions)
    assert _run_claim_is_refused(sessions, helpers, other_revision) is False
    assert _run_claim_is_refused(sessions, helpers, None) is False
    assert _run_claim_is_refused(sessions, helpers, connection[1]) is True


def test_a_call_that_has_no_connection_blocks_nothing(
    queue: Any, journal: Any, sessions: Any, helpers: Any, connection: tuple[str, str],
) -> None:
    item = queue.claimed()
    journal.insert(item.work_id, item.attempt_id, state="sent", estimate_micros=1, connection_revision_id=None)
    assert _run_claim_is_refused(sessions, helpers, connection[1]) is False


def test_the_connection_stays_busy_while_the_calls_worker_may_still_be_sending_and_is_free_once_its_attempt_ends(
    queue: Any, journal: Any, sessions: Any, helpers: Any, connection: tuple[str, str],
) -> None:
    """The Run rule applied to a call: an expired lease keeps the connection busy until the reclaim ends the attempt;
    a row an attempt that is over left open blocks nothing."""
    item = queue.claimed()
    journal.insert(item.work_id, item.attempt_id, state="sent", estimate_micros=1, connection_revision_id=connection[1])
    with sessions() as session:      # the lease ran out, nobody has reclaimed yet
        session.execute(text(
            "UPDATE comparison_work_attempt SET lease_expires_at = statement_timestamp() - interval '1 second' "
            "WHERE comparison_work_attempt_id = :a"), {"a": item.attempt_id})
        session.commit()
    assert _run_claim_is_refused(sessions, helpers, connection[1]) is True
    queue.expire_and_reclaim(item, settlers=())                    # the reclaim ends the attempt; no settler ran
    assert _run_claim_is_refused(sessions, helpers, connection[1]) is False


def test_the_claim_and_the_comparison_side_agree_on_what_is_active(
    queue: Any, journal: Any, sessions: Any, helpers: Any, repository: Any, connection: tuple[str, str],
) -> None:
    for state in ("prepared", "sent", "completed", "failed", "unknown"):
        item = queue.claimed()
        journal.insert(item.work_id, item.attempt_id, state=state, estimate_micros=1, cost_micros=1,
                       connection_revision_id=connection[1])
        with sessions() as session:
            ours = repository.connection_has_active_call(session, connection[0])
        assert _run_claim_is_refused(sessions, helpers, connection[1]) is ours, state
        with sessions() as session:
            session.execute(text(
                "UPDATE comparison_work_attempt SET state = 'lost', failure_reason = 'x', terminal_at = clock_timestamp() "
                "WHERE comparison_work_attempt_id = :a"), {"a": item.attempt_id})
            session.commit()


def test_the_runs_claim_is_refused_while_the_wrapper_is_calling_and_free_after_it_returns(
    caller: Any, queue: Any, sessions: Any, helpers: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed()
    during: list[bool] = []
    adapter = h.ScriptedAdapter(
        reply=h.reply(cost=0.1),
        on_call=lambda request: during.append(_run_claim_is_refused(sessions, helpers, connection[1])),
    )
    h.make_call(caller, item, adapter, connection[1])
    assert during == [True], "a Run was claimed on a connection with a comparison call in flight"
    assert _run_claim_is_refused(sessions, helpers, connection[1]) is False


# --- a comparison call counts an active Run and another call -------------------------------------------------------


def test_a_comparison_call_is_refused_while_a_run_is_active_on_its_connection(
    caller: Any, queue: Any, journal: Any, sessions: Any, helpers: Any, connection: tuple[str, str], h: Any,
) -> None:
    item = queue.claimed()
    run_id = helpers.queue_run(sessions, connection[1])
    authority = helpers.claim(sessions, run_id)
    try:
        adapter = h.ScriptedAdapter(reply=h.reply())
        with pytest.raises(CallRefused) as refusal:
            h.make_call(caller, item, adapter, connection[1])
        assert refusal.value.reason == "connection_busy" and refusal.value.pauses_job is False
        assert adapter.calls == 0 and journal.rows(item.work_id) == []
    finally:
        helpers.finish(sessions, authority)
        helpers.cancel(sessions, run_id)
    free = h.ScriptedAdapter(reply=h.reply(cost=0.1))
    h.make_call(caller, item, free, connection[1])
    assert free.calls == 1


def test_a_comparison_call_on_another_connection_is_not_refused_by_the_run(
    caller: Any, queue: Any, sessions: Any, helpers: Any, connection: tuple[str, str], h: Any,
) -> None:
    item = queue.claimed()
    run_id = helpers.queue_run(sessions, connection[1])
    authority = helpers.claim(sessions, run_id)
    try:
        _other, other_revision = helpers.new_connection(sessions)
        adapter = h.ScriptedAdapter(reply=h.reply(cost=0.1))
        h.make_call(caller, item, adapter, other_revision)
        assert adapter.calls == 1
    finally:
        helpers.finish(sessions, authority)
        helpers.cancel(sessions, run_id)


def test_two_comparison_calls_do_not_use_one_connection_at_once(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    first, second = queue.claimed(), queue.claimed()
    refused: list[str] = []
    inner = h.ScriptedAdapter(reply=h.reply(cost=0.1))

    def second_call(request: Any) -> None:
        try:
            h.make_call(caller, second, inner, connection[1], label="second")
        except CallRefused as refusal:
            refused.append(refusal.reason)

    outer = h.ScriptedAdapter(reply=h.reply(cost=0.1), on_call=second_call)
    h.make_call(caller, first, outer, connection[1], label="first")
    assert refused == ["connection_busy"] and inner.calls == 0
    assert journal.rows(second.work_id) == []
    h.make_call(caller, second, inner, connection[1], label="second")          # free again
    assert inner.calls == 1


# --- both decided under the Run claim's lock ----------------------------------------------------------------------


def _a_backend_waits_on_a_lock(engine: Any) -> bool:
    with engine.connect() as connection:
        return bool(connection.execute(text(
            "SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE datname = current_database() "
            "AND pid <> pg_backend_pid() AND state = 'active' AND wait_event_type = 'Lock')"
        )).scalar_one())


def test_a_comparison_call_waits_for_a_run_claim_that_holds_the_connection_lock_and_then_sees_the_run(
    caller: Any, queue: Any, journal: Any, sessions: Any, helpers: Any, comparison_engine: Any,
    connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    """The Run's claim has taken the connection's lock and has not committed. The comparison call must queue on
    that lock, not read around it: when the claim commits, the Run is active and the call is refused."""
    item = queue.claimed()
    run_id = helpers.queue_run(sessions, connection[1])
    holder = sessions()
    result: list[object] = []
    adapter = h.ScriptedAdapter(reply=h.reply())
    authority = None
    committed = False

    def call() -> None:
        try:
            h.make_call(caller, item, adapter, connection[1])
            result.append("sent")
        except CallRefused as refusal:
            result.append(refusal.reason)

    try:
        authority = JobRepository().start_execution(holder, run_id=run_id)      # lock taken, nothing committed
        thread = threading.Thread(target=call)
        thread.start()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not _a_backend_waits_on_a_lock(comparison_engine):
            if result:
                break
            time.sleep(0.05)
        assert not result, f"the call did not wait for the Run's claim: {result}"
        assert _a_backend_waits_on_a_lock(comparison_engine)
        holder.commit()
        committed = True
        thread.join(30)
        assert result == ["connection_busy"] and adapter.calls == 0
        assert journal.rows(item.work_id) == []
    finally:
        holder.close()
        if committed:
            helpers.finish(sessions, authority)
        helpers.cancel(sessions, run_id)


# --- a plain Run serialises per connection exactly as before ------------------------------------------------------------


def test_a_plain_run_still_serialises_per_connection_as_before(
    sessions: Any, helpers: Any, connection: tuple[str, str],
) -> None:
    """The statement of the granted query's first half, with comparison rows present on other connections: a second
    Run of a connection with an active Run is refused, a Run of another connection or of none is not, and the
    connection is free once the first Run has ended. (``tests/integration/jobs/test_connection_limit_claim.py`` says
    the same in full and is unmodified.)"""
    _other, other_revision = helpers.new_connection(sessions)
    first = helpers.queue_run(sessions, connection[1])
    second = helpers.queue_run(sessions, connection[1])
    elsewhere = helpers.queue_run(sessions, other_revision)
    unlimited = helpers.queue_run(sessions, None)
    authority = helpers.claim(sessions, first)
    claimed_elsewhere = []
    try:
        assert helpers.active_runs(sessions, connection[0]) == [first]
        with pytest.raises(ExecutionNotClaimed) as refusal:
            helpers.claim(sessions, second)
        assert refusal.value.code is ErrorCode.CONFLICT
        assert helpers.job_state(sessions, second) == "queued" and helpers.attempts(sessions, second) == 0
        claimed_elsewhere = [helpers.claim(sessions, elsewhere), helpers.claim(sessions, unlimited)]
        helpers.finish(sessions, authority)
        retried = helpers.claim(sessions, second)
        helpers.finish(sessions, retried)
    finally:
        for authority_elsewhere in claimed_elsewhere:
            helpers.finish(sessions, authority_elsewhere)
        for run_id in (first, second, elsewhere, unlimited):
            helpers.cancel(sessions, run_id)


def test_a_comparison_row_of_a_finished_attempt_changes_nothing_for_a_run(
    queue: Any, journal: Any, sessions: Any, helpers: Any, connection: tuple[str, str],
) -> None:
    """The comparison half of the query is an OR that only adds a reason to refuse: with no open call of a live attempt it
    answers what it always did."""
    item = queue.claimed()
    journal.insert(item.work_id, item.attempt_id, state="completed", cost_micros=1, connection_revision_id=connection[1])
    run_id = helpers.queue_run(sessions, connection[1])
    try:
        authority = helpers.claim(sessions, run_id)
        assert helpers.active_runs(sessions, connection[0]) == [run_id]
        helpers.finish(sessions, authority)
    finally:
        helpers.cancel(sessions, run_id)
