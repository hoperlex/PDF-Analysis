"""`EXEC-PAR-QUEUE-01` -- one active run per executor connection, in the hint and in the claim.

Real PostgreSQL, no object store (see ``connection_limit_support``). Everything here is made by
the shipped ``JobRepository``; the rows around it are written directly.

What is "active": a run whose Job is ``leased``, ``running`` or ``retry_wait`` -- an unreleased
Lease, live or expired. A queued Job is waiting and the other states are terminal. Every test
that needs the definition says so by reading the table itself (``active_runs``), not by asking
the code it checks.

Each guard has a mutation recorded in ``docs/program/EXEC-PAR-QUEUE-01.md``: the hint's skip, the
connection lock, the re-check under the lock, the definition of "active" (an expired Lease keeps
the connection busy), and the in-flight exclusion.
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

_SUPPORT_NAME = "exec_par_queue_connection_limit_support"
if _SUPPORT_NAME in sys.modules:
    support: ModuleType = sys.modules[_SUPPORT_NAME]
else:
    _spec = importlib.util.spec_from_file_location(
        _SUPPORT_NAME, Path(__file__).resolve().parent / "connection_limit_support.py"
    )
    assert _spec is not None and _spec.loader is not None
    support = importlib.util.module_from_spec(_spec)
    sys.modules[_SUPPORT_NAME] = support
    _spec.loader.exec_module(support)

#: ``next_queued_run`` as it was before this task (`a3e83f39`), verbatim. The order of the hint is
#: pinned against it: with no connection involved the two must agree on every queue.
_TODAYS_NEXT_JOB = text(
    "SELECT j.run_id FROM job j JOIN audit_run r ON r.run_id = j.run_id "
    "WHERE j.state = 'queued' AND r.state IN ('queued', 'running') "
    "AND j.available_at <= statement_timestamp() "
    "AND NOT EXISTS (SELECT 1 FROM execution_control WHERE singleton AND paused) "
    "ORDER BY j.priority DESC, j.created_at, j.job_id LIMIT 1 "
    "FOR UPDATE OF r SKIP LOCKED"
)

WAIT_SECONDS = 20.0


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


# --- the hint ----------------------------------------------------------------------------------


def test_the_hint_skips_a_run_whose_connection_is_busy_and_offers_the_next_free_one(
    sessions: sessionmaker[Session],
) -> None:
    busy, busy_revision = support.new_connection(sessions)
    _free, free_revision = support.new_connection(sessions)
    running = support.queue_run(sessions, busy_revision)
    waiting = support.queue_run(sessions, busy_revision)   # older than the free one below
    elsewhere = support.queue_run(sessions, free_revision)
    unlimited = support.queue_run(sessions, None)
    authority = support.claim(sessions, running)
    try:
        assert support.active_runs(sessions, busy) == [running]
        # The unchanged order is waiting, elsewhere, unlimited; the first is not allowed to run.
        assert _hint(sessions) == elsewhere
        support.claim(sessions, elsewhere)
        assert _hint(sessions) == unlimited
        support.claim(sessions, unlimited)
        assert _hint(sessions) is None, "the busy connection's run was offered"
        support.finish(sessions, authority)
        assert support.active_runs(sessions, busy) == []
        assert _hint(sessions) == waiting, "the run was not offered once the connection was free"
    finally:
        for run_id in (running, waiting, elsewhere, unlimited):
            support.cancel(sessions, run_id)


def test_the_hint_keeps_todays_order_when_no_run_has_a_connection(
    sessions: sessionmaker[Session],
) -> None:
    older = support.queue_run(sessions, None)
    newer = support.queue_run(sessions, None)
    higher = support.queue_run(sessions, None, priority=support.PRIORITY + 1)
    try:
        with sessions() as session:
            expected = session.execute(_TODAYS_NEXT_JOB).scalar_one_or_none()
        assert _hint(sessions) == expected == higher
        support.claim(sessions, higher)
        with sessions() as session:
            expected = session.execute(_TODAYS_NEXT_JOB).scalar_one_or_none()
        assert _hint(sessions) == expected == older
        support.claim(sessions, older)
        with sessions() as session:
            expected = session.execute(_TODAYS_NEXT_JOB).scalar_one_or_none()
        assert _hint(sessions) == expected == newer
    finally:
        for run_id in (older, newer, higher):
            support.cancel(sessions, run_id)


def test_runs_without_a_connection_are_never_limited(sessions: sessionmaker[Session]) -> None:
    first = support.queue_run(sessions, None)
    second = support.queue_run(sessions, None)
    try:
        support.claim(sessions, first)
        assert _hint(sessions) == second
        support.claim(sessions, second)
        assert support.job_state(sessions, first) == support.job_state(sessions, second) == "running"
    finally:
        for run_id in (first, second):
            support.cancel(sessions, run_id)


def test_two_revisions_of_one_connection_share_its_limit(sessions: sessionmaker[Session]) -> None:
    connection, first_revision = support.new_connection(sessions)
    second_revision = support.new_revision(sessions, connection, 2)
    running = support.queue_run(sessions, first_revision)
    waiting = support.queue_run(sessions, second_revision)
    try:
        support.claim(sessions, running)
        assert _hint(sessions) is None
        with pytest.raises(ExecutionNotClaimed):
            support.claim(sessions, waiting)
    finally:
        for run_id in (running, waiting):
            support.cancel(sessions, run_id)


def test_a_submitted_run_is_not_offered_again_and_holds_its_connection(
    sessions: sessionmaker[Session],
) -> None:
    _connection, revision = support.new_connection(sessions)
    _other, other_revision = support.new_connection(sessions)
    handed_to_a_slot = support.queue_run(sessions, revision)
    behind_it = support.queue_run(sessions, revision)
    elsewhere = support.queue_run(sessions, other_revision)
    try:
        # Nothing is claimed yet, so the database alone would offer the first run again.
        assert _hint(sessions) == handed_to_a_slot
        # Handed to a slot: not offered again, and the run behind it waits for the connection.
        assert _hint(sessions, submitted=[handed_to_a_slot]) == elsewhere
        assert _hint(sessions, submitted=[handed_to_a_slot, elsewhere]) is None
    finally:
        for run_id in (handed_to_a_slot, behind_it, elsewhere):
            support.cancel(sessions, run_id)


# --- the claim ---------------------------------------------------------------------------------


def test_a_claim_that_loses_the_check_leaves_the_run_and_its_job_as_they_were(
    sessions: sessionmaker[Session],
) -> None:
    connection, revision = support.new_connection(sessions)
    running = support.queue_run(sessions, revision)
    refused = support.queue_run(sessions, revision)
    support.claim(sessions, running)
    snapshot = """
        SELECT (SELECT to_jsonb(j) - 'updated_at' FROM job j WHERE j.run_id = :r),
               (SELECT to_jsonb(r) - 'updated_at' FROM audit_run r WHERE r.run_id = :r),
               (SELECT count(*) FROM attempt a JOIN job j ON j.job_id = a.job_id WHERE j.run_id = :r),
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
        assert support.job_state(sessions, refused) == "queued"
        assert support.attempts(sessions, refused) == 0
        assert support.active_runs(sessions, connection) == [running]
    finally:
        for run_id in (running, refused):
            support.cancel(sessions, run_id)


def test_two_claims_of_one_connection_cannot_both_win(
    engine: Engine, sessions: sessionmaker[Session],
) -> None:
    """The second claim starts while the first is in its transaction and cannot see its write.

    The first claim is held open (uncommitted), the second starts in another thread and queues
    behind it, and only then does the first commit. The second must then read the committed Job
    and refuse. Without the connection lock it would read the connection as free, win the control
    row's lock after the first commits, and claim.
    """
    connection, revision = support.new_connection(sessions)
    first = support.queue_run(sessions, revision)
    second = support.queue_run(sessions, revision)
    outcome: dict[str, Any] = {}

    def claim_second() -> None:
        with sessions() as other:
            try:
                JobRepository().start_execution(other, run_id=second)
                other.commit()
                outcome["result"] = "claimed"
            except ExecutionNotClaimed as refusal:
                other.rollback()
                outcome["result"] = refusal.code
            except BaseException as failure:  # surfaced by the assertion below
                outcome["result"] = failure

    holder = sessions()
    try:
        JobRepository().start_execution(holder, run_id=first)
        thread = threading.Thread(target=claim_second, name="second-claim")
        thread.start()
        _wait_until(lambda: _a_backend_waits_on_a_lock(engine), what="the second claim to queue")
        assert thread.is_alive() and "result" not in outcome, "the second claim did not wait"
        holder.commit()
        thread.join(WAIT_SECONDS)
        assert not thread.is_alive()
        assert outcome["result"] is ErrorCode.CONFLICT, outcome
        assert support.active_runs(sessions, connection) == [first]
        assert support.job_state(sessions, second) == "queued"
        assert support.attempts(sessions, second) == 0
    finally:
        holder.close()
        for run_id in (first, second):
            support.cancel(sessions, run_id)


def test_claims_racing_for_one_connection_leave_exactly_one_winner_and_other_connections_run(
    sessions: sessionmaker[Session],
) -> None:
    """The same race with plain threads: two runs of one connection, one run of another."""
    connection, revision = support.new_connection(sessions)
    other, other_revision = support.new_connection(sessions)
    contenders = [support.queue_run(sessions, revision), support.queue_run(sessions, revision)]
    elsewhere = support.queue_run(sessions, other_revision)
    start = threading.Barrier(3)
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
        assert sorted(results[run_id] for run_id in contenders) == ["claimed", "refused"], results
        assert results[elsewhere] == "claimed"
        assert len(support.active_runs(sessions, connection)) == 1
        assert support.active_runs(sessions, other) == [elsewhere]
    finally:
        for run_id in (*contenders, elsewhere):
            support.cancel(sessions, run_id)


def test_a_cancelled_run_frees_its_connection(sessions: sessionmaker[Session]) -> None:
    connection, revision = support.new_connection(sessions)
    running = support.queue_run(sessions, revision)
    waiting = support.queue_run(sessions, revision)
    support.claim(sessions, running)
    try:
        with pytest.raises(ExecutionNotClaimed):
            support.claim(sessions, waiting)
        support.cancel(sessions, running)
        assert support.active_runs(sessions, connection) == []
        support.claim(sessions, waiting)
        assert support.active_runs(sessions, connection) == [waiting]
    finally:
        for run_id in (running, waiting):
            support.cancel(sessions, run_id)


# --- reclaim -----------------------------------------------------------------------------------


def test_an_expired_lease_keeps_the_connection_busy_until_the_reclaim_releases_it(
    sessions: sessionmaker[Session],
) -> None:
    """A killed worker leaves a Lease nobody heartbeats. Its run is still the connection's run."""
    connection, revision = support.new_connection(sessions)
    killed = support.queue_run(sessions, revision)
    behind = support.queue_run(sessions, revision)
    authority = support.claim(sessions, killed)
    try:
        with sessions() as session:
            session.execute(text(
                "UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' "
                "WHERE lease_id = :lease"
            ), {"lease": authority.lease_id})
            session.commit()
        # Expired but unreleased: still active, so neither the hint nor the claim lets `behind` in.
        assert support.active_runs(sessions, connection) == [killed]
        assert _hint(sessions) is None
        with pytest.raises(ExecutionNotClaimed):
            support.claim(sessions, behind)

        with sessions() as session:
            assert JobRepository().reclaim_expired(session) >= 1
            session.commit()
        # Released: the killed run is queued again, nobody is active, and the order is the queue's:
        # the older run first.
        assert support.active_runs(sessions, connection) == []
        assert support.job_state(sessions, killed) == "queued"
        assert _hint(sessions) == killed
        second_attempt = support.claim(sessions, killed)
        assert support.attempts(sessions, killed) == 2
        # ... and the resumed run holds the connection against the one behind it, as before.
        assert support.active_runs(sessions, connection) == [killed]
        assert _hint(sessions) is None
        with pytest.raises(ExecutionNotClaimed):
            support.claim(sessions, behind)
        support.finish(sessions, second_attempt)
        assert _hint(sessions) == behind
    finally:
        for run_id in (killed, behind):
            support.cancel(sessions, run_id)
