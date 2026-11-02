"""`EXEC2-CAP-01` (ADR-0026 decision 1) -- a connection serves as many Runs at once as its capacity, in the hint and in the claim.

Real PostgreSQL, no object store (see ``connection_limit_support`` and ``connection_capacity_support``). Everything
here is made by the shipped ``JobRepository``; the rows around it are written directly. These tests are written and
**not run** in EXEC-2 (`R-149d`, D-292); each would pass against PostgreSQL.

What the tests below pin, and the reading of B1 section 6 they take (the section is not in the repository; the task
file's outcome and cases are, and the numbers are the integrator's to re-map):

1. with capacity 3 and enough worker slots, three independent Runs of one connection hold it at once (``test_three_runs...``,
   ``test_the_hint_and_the_claim_agree...``);
2. the fourth waits and is claimed when one ends (same tests);
3. with the default of one -- absent or explicit -- behaviour is as before (``test_the_default_capacity...``);
4. a full connection never blocks another connection or a Run with none (``test_a_full_connection...``);
5. a lowered capacity governs new claims only; a raised one admits more, and the capacity is the connection's
   **current** revision, not the one a Run froze (``test_a_lowered...``, ``test_the_capacity_is_read...``);
6. a killed worker's Run keeps its unit until the reclaim ends its Attempt (``test_a_killed_workers...``);
15. two claims for the last unit: exactly one succeeds -- in threads and between two processes
   (``test_claims_racing...``, ``test_the_last_unit...``).
"""

from __future__ import annotations

import importlib.util
import sys
import threading
import time
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.jobs.public import ExecutionNotClaimed, JobRepository
from auditmanager.shared.errors import ErrorCode

pytestmark = pytest.mark.usefixtures("quiet_queue")

_SUPPORT_NAME = "exec2_cap_connection_capacity_support"
if _SUPPORT_NAME in sys.modules:
    support: ModuleType = sys.modules[_SUPPORT_NAME]
else:
    _spec = importlib.util.spec_from_file_location(
        _SUPPORT_NAME, Path(__file__).resolve().parent / "connection_capacity_support.py"
    )
    assert _spec is not None and _spec.loader is not None
    support = importlib.util.module_from_spec(_spec)
    sys.modules[_SUPPORT_NAME] = support
    _spec.loader.exec_module(support)

WAIT_SECONDS = 30.0


def _hint(sessions: sessionmaker[Session], **kwargs: Any) -> str | None:
    with sessions() as session:
        return JobRepository().next_queued_run(session, **kwargs)


def _wait_until(predicate: Any, *, what: str) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(f"timed out after {WAIT_SECONDS:.0f} s waiting for {what}")


def _a_backend_waits_on_a_lock(engine: Engine) -> bool:
    with engine.connect() as connection:
        return bool(connection.execute(text(
            "SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE datname = current_database() "
            "AND pid <> pg_backend_pid() AND state = 'active' AND wait_event_type = 'Lock')"
        )).scalar_one())


def _refused(sessions: sessionmaker[Session], run_id: str) -> bool:
    """Try the shipped claim. ``True`` when it was refused, and then the Run and its Job are as they were: queued,
    with no Attempt. ``False`` when it claimed (the Run is then active and the caller owns ending it)."""
    try:
        support.claim(sessions, run_id)
    except ExecutionNotClaimed as refusal:
        assert refusal.code is ErrorCode.CONFLICT
        assert support.job_state(sessions, run_id) == "queued" and support.attempts(sessions, run_id) == 0
        return True
    return False


def _cancel_all(sessions: sessionmaker[Session], *run_ids: str) -> None:
    for run_id in run_ids:
        support.cancel(sessions, run_id)


# --- three at once and a fourth waits ---------------------------------------------------------------------------


def test_three_runs_of_one_connection_hold_it_at_once_and_a_fourth_waits_until_one_ends(
    sessions: sessionmaker[Session],
) -> None:
    connection, revision = support.new_connection(sessions, capacity=3)
    runs = [support.queue_run(sessions, revision) for _ in range(4)]
    first_three, fourth = runs[:3], runs[3]
    authorities = []
    try:
        for run_id in first_three:
            authorities.append(support.claim(sessions, run_id))
        assert support.active_runs(sessions, connection) == sorted(first_three)
        assert _refused(sessions, fourth) is True
        assert _hint(sessions) is None, "the fourth Run was offered while the connection held three"
        support.finish(sessions, authorities.pop(0))
        assert _hint(sessions) == fourth, "the fourth Run was not offered once a unit was free"
        authorities.append(support.claim(sessions, fourth))
        assert len(support.active_runs(sessions, connection)) == 3
        assert fourth in support.active_runs(sessions, connection)
    finally:
        _cancel_all(sessions, *runs)


@pytest.mark.parametrize("capacity", [1, 2, 3, 5, 16])
def test_the_hint_and_the_claim_agree_at_every_step_up_to_the_capacity(
    sessions: sessionmaker[Session], capacity: int,
) -> None:
    """The n-th Run is offered and claimed for n up to the capacity; Run capacity + 1 is neither."""
    connection, revision = support.new_connection(sessions, capacity=capacity)
    runs = [support.queue_run(sessions, revision) for _ in range(capacity + 1)]
    try:
        for index, run_id in enumerate(runs[:capacity]):
            assert _hint(sessions) == run_id, f"Run {index + 1} of {capacity} was not offered"
            support.claim(sessions, run_id)
        assert len(support.active_runs(sessions, connection)) == capacity
        assert _hint(sessions) is None
        assert _refused(sessions, runs[capacity]) is True
    finally:
        _cancel_all(sessions, *runs)


def test_the_hint_skips_a_full_connection_for_the_next_one_with_a_free_unit(
    sessions: sessionmaker[Session],
) -> None:
    _connection, revision = support.new_connection(sessions, capacity=2)
    _other, other_revision = support.new_connection(sessions)
    older = [support.queue_run(sessions, revision) for _ in range(3)]
    elsewhere = support.queue_run(sessions, other_revision)
    try:
        assert _hint(sessions) == older[0]
        support.claim(sessions, older[0])
        assert _hint(sessions) == older[1], "one unit of two was still free"
        support.claim(sessions, older[1])
        assert _hint(sessions) == elsewhere, "the full connection's third Run was offered"
        support.claim(sessions, elsewhere)
        assert _hint(sessions) is None
    finally:
        _cancel_all(sessions, *older, elsewhere)


def test_the_runs_this_process_has_handed_to_a_slot_count_as_held_units_once_each(
    sessions: sessionmaker[Session],
) -> None:
    _connection, revision = support.new_connection(sessions, capacity=2)
    _other, other_revision = support.new_connection(sessions)
    r1, r2, r3 = (support.queue_run(sessions, revision) for _ in range(3))
    elsewhere = support.queue_run(sessions, other_revision)
    try:
        assert _hint(sessions, submitted=[r1]) == r2, "one submitted Run of two units filled the connection"
        assert _hint(sessions, submitted=[r1, r2]) == elsewhere, "two submitted Runs did not fill it"
        assert _hint(sessions, submitted=[r1, r2, elsewhere]) is None
        # A submitted Run that has already claimed is one held unit, not two: its Job is active and it is submitted.
        support.claim(sessions, r1)
        assert _hint(sessions, submitted=[r1]) == r2, "a Run both claimed and submitted was counted twice"
        assert _hint(sessions, submitted=[r1, r2]) == elsewhere
    finally:
        _cancel_all(sessions, r1, r2, r3, elsewhere)


# --- the default is one -----------------------------------------------------------------------------------------


@pytest.mark.parametrize("capacity", [None, 1])
def test_the_default_capacity_is_one_whether_the_setting_is_absent_or_explicit(
    sessions: sessionmaker[Session], capacity: int | None,
) -> None:
    connection, revision = support.new_connection(sessions, capacity=capacity)
    running, waiting = support.queue_run(sessions, revision), support.queue_run(sessions, revision)
    try:
        support.claim(sessions, running)
        assert support.active_runs(sessions, connection) == [running]
        assert _hint(sessions) is None
        assert _refused(sessions, waiting) is True
    finally:
        _cancel_all(sessions, running, waiting)


def test_a_later_revision_without_a_capacity_puts_the_connection_back_to_one(
    sessions: sessionmaker[Session],
) -> None:
    """The current revision decides, whatever the older ones said: a revision written without the setting after one
    that said three puts the connection back to exclusive use."""
    connection, revision = support.new_connection(sessions, capacity=3)
    reset = support.new_revision_with_capacity(sessions, connection, 3, None)
    running, waiting = support.queue_run(sessions, reset), support.queue_run(sessions, revision)
    try:
        support.claim(sessions, running)
        assert _refused(sessions, waiting) is True and _hint(sessions) is None
    finally:
        _cancel_all(sessions, running, waiting)


# --- another connection, or none ----------------------------------------------------------------------------------


def test_a_full_connection_never_blocks_another_connection_or_a_run_with_none(
    sessions: sessionmaker[Session],
) -> None:
    connection, revision = support.new_connection(sessions, capacity=2)
    other, other_revision = support.new_connection(sessions, capacity=2)
    full = [support.queue_run(sessions, revision) for _ in range(3)]
    elsewhere = [support.queue_run(sessions, other_revision) for _ in range(2)]
    unlimited = [support.queue_run(sessions, None) for _ in range(3)]
    try:
        support.claim(sessions, full[0])
        support.claim(sessions, full[1])
        assert _refused(sessions, full[2]) is True
        for run_id in (*elsewhere, *unlimited):
            support.claim(sessions, run_id)
        assert len(support.active_runs(sessions, connection)) == 2
        assert sorted(support.active_runs(sessions, other)) == sorted(elsewhere)
    finally:
        _cancel_all(sessions, *full, *elsewhere, *unlimited)


def test_a_run_with_no_connection_takes_no_unit_from_any_connection(sessions: sessionmaker[Session]) -> None:
    connection, revision = support.new_connection(sessions, capacity=1)
    unlimited = [support.queue_run(sessions, None) for _ in range(3)]
    mine = support.queue_run(sessions, revision)
    try:
        for run_id in unlimited:
            support.claim(sessions, run_id)
        support.claim(sessions, mine)
        assert support.active_runs(sessions, connection) == [mine]
    finally:
        _cancel_all(sessions, *unlimited, mine)


# --- the capacity is the connection's current revision's ------------------------------------------------------------


def test_the_capacity_is_read_from_the_current_revision_not_from_the_one_a_run_froze(
    sessions: sessionmaker[Session],
) -> None:
    """Three Runs frozen to revision 1 (capacity absent, so one). Raising the capacity by a revision 2 admits the
    others, though they froze revision 1."""
    connection, first_revision = support.new_connection(sessions)
    runs = [support.queue_run(sessions, first_revision) for _ in range(3)]
    try:
        support.claim(sessions, runs[0])
        assert _refused(sessions, runs[1]) is True
        support.new_revision_with_capacity(sessions, connection, 2, 3)
        assert _hint(sessions) == runs[1]
        support.claim(sessions, runs[1])
        support.claim(sessions, runs[2])
        assert len(support.active_runs(sessions, connection)) == 3
    finally:
        _cancel_all(sessions, *runs)


def test_a_lowered_capacity_governs_new_claims_only_and_stops_nothing_in_flight(
    sessions: sessionmaker[Session],
) -> None:
    connection, revision = support.new_connection(sessions, capacity=3)
    runs = [support.queue_run(sessions, revision) for _ in range(5)]
    authorities = [support.claim(sessions, run_id) for run_id in runs[:3]]
    waiting_one, waiting_two = runs[3], runs[4]
    try:
        support.new_revision_with_capacity(sessions, connection, 3, 2)           # lowered under three running
        assert [support.job_state(sessions, run_id) for run_id in runs[:3]] == ["running"] * 3
        assert len(support.active_runs(sessions, connection)) == 3, "a lowered capacity stopped a Run"
        assert _hint(sessions) is None and _refused(sessions, waiting_one) is True
        support.finish(sessions, authorities.pop())                              # 2 active, capacity 2
        assert _hint(sessions) is None and _refused(sessions, waiting_one) is True
        support.finish(sessions, authorities.pop())                              # 1 active, capacity 2
        assert _hint(sessions) == waiting_one
        support.claim(sessions, waiting_one)
        assert len(support.active_runs(sessions, connection)) == 2
        assert _refused(sessions, waiting_two) is True
    finally:
        _cancel_all(sessions, *runs)


# --- reclaim ---------------------------------------------------------------------------------------------------------


def test_a_killed_workers_run_keeps_its_unit_until_the_reclaim_ends_its_attempt(
    sessions: sessionmaker[Session],
) -> None:
    connection, revision = support.new_connection(sessions, capacity=2)
    killed = support.queue_run(sessions, revision)
    alive = support.queue_run(sessions, revision)
    behind = support.queue_run(sessions, revision)
    killed_authority = support.claim(sessions, killed)
    alive_authority = support.claim(sessions, alive)
    try:
        with sessions() as session:
            session.execute(text(
                "UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' WHERE lease_id = :lease"
            ), {"lease": killed_authority.lease_id})
            session.commit()
        # Expired but unreleased: the killed Run is still active, so both units are held.
        assert sorted(support.active_runs(sessions, connection)) == sorted([killed, alive])
        assert _hint(sessions) is None and _refused(sessions, behind) is True

        with sessions() as session:
            assert JobRepository().reclaim_expired(session) >= 1
            session.commit()
        assert support.active_runs(sessions, connection) == [alive]
        assert support.job_state(sessions, killed) == "queued"
        assert _hint(sessions) == killed, "the older Run did not come first once its unit was released"
        support.claim(sessions, killed)
        assert support.attempts(sessions, killed) == 2
        assert _refused(sessions, behind) is True
        support.finish(sessions, alive_authority)
        assert _hint(sessions) == behind
    finally:
        _cancel_all(sessions, killed, alive, behind)


# --- the claim that loses leaves nothing behind -------------------------------------------------------------------------


def test_a_claim_that_finds_the_connection_full_writes_nothing(sessions: sessionmaker[Session]) -> None:
    connection, revision = support.new_connection(sessions, capacity=2)
    a, b, refused = (support.queue_run(sessions, revision) for _ in range(3))
    support.claim(sessions, a)
    support.claim(sessions, b)
    snapshot = """
        SELECT (SELECT to_jsonb(j) - 'updated_at' FROM job j WHERE j.run_id = :r),
               (SELECT to_jsonb(r) - 'updated_at' FROM audit_run r WHERE r.run_id = :r),
               (SELECT count(*) FROM attempt t JOIN job j ON j.job_id = t.job_id WHERE j.run_id = :r),
               (SELECT count(*) FROM audit_event WHERE payload ->> 'run_id' = :r)
    """
    try:
        with sessions() as session:
            before = session.execute(text(snapshot), {"r": refused}).one()
        with sessions() as session:
            with pytest.raises(ExecutionNotClaimed) as caught:
                JobRepository().start_execution(session, run_id=refused)
            session.commit()
        assert caught.value.code is ErrorCode.CONFLICT
        with sessions() as session:
            after = session.execute(text(snapshot), {"r": refused}).one()
        assert tuple(after) == tuple(before)
        assert sorted(support.active_runs(sessions, connection)) == sorted([a, b])
    finally:
        _cancel_all(sessions, a, b, refused)


# --- the last unit: exactly one wins -------------------------------------------------------------------------------------


def test_claims_racing_for_the_units_of_one_connection_leave_exactly_the_capacity_as_winners(
    sessions: sessionmaker[Session],
) -> None:
    connection, revision = support.new_connection(sessions, capacity=3)
    other, other_revision = support.new_connection(sessions)
    contenders = [support.queue_run(sessions, revision) for _ in range(6)]
    elsewhere = support.queue_run(sessions, other_revision)
    start = threading.Barrier(len(contenders) + 1)
    results: dict[str, Any] = {}

    def claim(run_id: str) -> None:
        start.wait(timeout=WAIT_SECONDS)
        try:
            support.claim(sessions, run_id)
            results[run_id] = "claimed"
        except ExecutionNotClaimed:
            results[run_id] = "refused"
        except BaseException as failure:
            results[run_id] = failure

    threads = [threading.Thread(target=claim, args=(run_id,)) for run_id in (*contenders, elsewhere)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(WAIT_SECONDS)
        outcomes = sorted(str(results[run_id]) for run_id in contenders)
        assert outcomes == ["claimed"] * 3 + ["refused"] * 3, results
        assert results[elsewhere] == "claimed"
        assert len(support.active_runs(sessions, connection)) == 3
        assert support.active_runs(sessions, other) == [elsewhere]
    finally:
        _cancel_all(sessions, *contenders, elsewhere)


def test_two_claims_for_the_last_unit_have_exactly_one_winner(sessions: sessionmaker[Session]) -> None:
    connection, revision = support.new_connection(sessions, capacity=2)
    held, first, second = (support.queue_run(sessions, revision) for _ in range(3))
    support.claim(sessions, held)
    start = threading.Barrier(2)
    results: dict[str, Any] = {}

    def claim(run_id: str) -> None:
        start.wait(timeout=WAIT_SECONDS)
        try:
            support.claim(sessions, run_id)
            results[run_id] = "claimed"
        except ExecutionNotClaimed as refusal:
            results[run_id] = refusal.code
        except BaseException as failure:
            results[run_id] = failure

    threads = [threading.Thread(target=claim, args=(run_id,)) for run_id in (first, second)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(WAIT_SECONDS)
        assert sorted(map(str, results.values())) == sorted(["claimed", str(ErrorCode.CONFLICT)]), results
        assert len(support.active_runs(sessions, connection)) == 2
    finally:
        _cancel_all(sessions, held, first, second)


def test_the_last_unit_goes_to_exactly_one_of_two_processes_and_the_loser_sees_the_winners_commit(
    engine: Engine, sessions: sessionmaker[Session],
) -> None:
    """The first claim takes the connection's advisory lock and does not commit. A second **process** claims the
    other Run and must queue on that lock, not read around it: when the first commits, the connection holds its
    two units and the second is refused. Without the lock the child would count one unit and win too."""
    connection, revision = support.new_connection(sessions, capacity=2)
    held, mine, theirs = (support.queue_run(sessions, revision) for _ in range(3))
    support.claim(sessions, held)
    holder = sessions()
    child = None
    try:
        JobRepository().start_execution(holder, run_id=mine)          # lock taken, nothing committed
        child = support.claim_in_a_second_process(theirs)
        _wait_until(lambda: _a_backend_waits_on_a_lock(engine), what="the other process to queue on the connection's lock")
        assert child.poll() is None, "the other process did not wait for the first claim"
        holder.commit()
        answer = support.child_result(child)
        assert answer == {"result": "refused", "code": ErrorCode.CONFLICT.value}, answer
        assert sorted(support.active_runs(sessions, connection)) == sorted([held, mine])
        assert support.job_state(sessions, theirs) == "queued" and support.attempts(sessions, theirs) == 0
    finally:
        holder.close()
        if child is not None and child.poll() is None:
            child.kill()
            child.communicate()
        _cancel_all(sessions, held, mine, theirs)


def test_a_claim_that_rolls_back_gives_the_last_unit_to_the_waiting_process(
    engine: Engine, sessions: sessionmaker[Session],
) -> None:
    """The mirror: the first claim does not commit but rolls back, so it never took the unit, and the process that
    queued behind it gets it. A unit is held by committed state, not by the lock."""
    connection, revision = support.new_connection(sessions, capacity=2)
    held, mine, theirs = (support.queue_run(sessions, revision) for _ in range(3))
    support.claim(sessions, held)
    holder = sessions()
    child = None
    try:
        JobRepository().start_execution(holder, run_id=mine)
        child = support.claim_in_a_second_process(theirs)
        _wait_until(lambda: _a_backend_waits_on_a_lock(engine), what="the other process to queue on the connection's lock")
        holder.rollback()
        answer = support.child_result(child)
        assert answer == {"result": "claimed"}, answer
        assert sorted(support.active_runs(sessions, connection)) == sorted([held, theirs])
        assert support.job_state(sessions, mine) == "queued"
    finally:
        holder.close()
        if child is not None and child.poll() is None:
            child.kill()
            child.communicate()
        _cancel_all(sessions, held, mine, theirs)
