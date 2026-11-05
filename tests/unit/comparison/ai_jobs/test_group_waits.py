"""`EXEC2-FOLLOWUP-01` (ADR-0026 decision 15, `R-149c`): the wait sweep of comparison AI jobs admitted by a group.

Before the sweep a job's wait was written, and its offline expiry decided, only inside a retried call. The sweep walks the live ``pending`` jobs
(queued or running), keeps the stored wait true and ends the ones whose group has had no eligible member for longer than the limit,
**without a break**. Container-free: the job repository, the job layer and the group's members are stand-ins on one clock, so each guard is an
assertion that would fail without it:

* the wait follows the members, as the Run side's sweep does (``None`` when some member can take the job, ``executor_at_capacity`` when none
  can but some is only full, ``runner_offline`` otherwise) and is written only when it differs from the one stored, which restarts the clock;
* a job ends only when ``runner_offline`` has held continuously for longer than the limit: **a runner back at minute 29 and gone again does not
  end the job**, and a job stored ``executor_at_capacity`` whose group goes fully offline starts the offline clock at the sweep's observation and
  **does end**, once, after the limit;
* a paused job, an ended job and a job in ``needs_reconsent`` are never read or written;
* the outcome is the in-call expiry's, by the same call, in a transaction of the job's own: items locked first, then the job row, hooks around the
  ending in the order their handlers take (`test_group_wait_hooks.py` holds the hooks of the three methods that have one);
* one pass walks every candidate page after page, and a job whose transaction fails does not stop the pass.

The same flows over real rows and the sweep's own SQL are in ``tests/integration/comparison/test_group_binding.py`` (section «3b»).

Written and **not run** in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.ai_jobs import group_waits, service
from auditmanager.comparison.ai_jobs.group_waits import (
    ENDED_BY_PAUSE_ONLY,
    ComparisonGroupWaitSweep,
    ComparisonGroupWaits,
    EndedWithoutExecutor,
)
from auditmanager.comparison.ai_jobs.model import METHODS
from auditmanager.comparison.ai_jobs.repository import PendingWait
from auditmanager.comparison.spend import dispatch
from auditmanager.comparison.spend.errors import REASON_NO_EXECUTOR_ONLINE
from auditmanager.executors.public import MemberFacts

BASE = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)
GROUP_REVISION = "exgr_01"
LIMIT = 1800.0
OFFLINE = {"runner_online": False}


def facts(name: str, *, used: int = 0, capacity: int = 1, **over: Any) -> MemberFacts:
    values: dict[str, Any] = {
        "connection_id": f"exc_{name}", "tie_break_order": None, "revision_is_snapshot": True, "archived": False,
        "served": True, "probed_ok": True, "runner_online": True, "capacity": capacity, "used": used,
    }
    values.update(over)
    return MemberFacts(**values)


DARK = [facts("A", **OFFLINE), facts("B", **OFFLINE)]
ONLINE = [facts("A"), facts("B", **OFFLINE)]
FULL = [facts("A", used=1), facts("B", **OFFLINE)]


class Log(list):  # type: ignore[type-arg]
    def at(self, name: str) -> list[int]:
        return [i for i, entry in enumerate(self) if (entry[0] if isinstance(entry, tuple) else entry) == name]

    def first(self, name: str) -> int:
        return self.at(name)[0]


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeSession:
    def __init__(self, log: Log) -> None:
        self.log = log

    def __enter__(self) -> "FakeSession":
        self.log.append("open")
        return self

    def __exit__(self, *exc: object) -> bool:
        self.log.append("close")
        return False

    def commit(self) -> None:
        self.log.append("commit")

    def rollback(self) -> None:
        self.log.append("rollback")


class Job:
    def __init__(self, job_id: str, index: int, *, method: str, reason: str | None, since: float | None, state: str) -> None:
        self.job_id, self.created_at, self.method = job_id, BASE + timedelta(seconds=index), method
        self.reason, self.since, self.state = reason, since, state


class FakeJobs:
    """The job repository's sweep statements over a table of jobs on the clock: what a statement would answer, and what it would write."""

    def __init__(self, log: Log, clock: Clock) -> None:
        self.log, self.clock, self.jobs = log, clock, {}
        self.items_held_elsewhere: set[str] = set()
        self.rows_held_elsewhere: set[str] = set()
        self.pages: list[dict[str, Any]] = []

    def add(
        self, job_id: str, *, method: str = "pair_check", reason: str | None = "runner_offline", waited: float | None = 0.0,
        state: str = "running",
    ) -> Job:
        """A job whose wait for ``reason`` began ``waited`` seconds ago."""
        job = Job(job_id, len(self.jobs), method=method, reason=reason, since=None if waited is None else self.clock.now - waited, state=state)
        self.jobs[job_id] = job
        return job

    # -- the statements -----------------------------------------------------------------------------------------------------------
    def _live(self, job: Job) -> bool:
        return job.state in ("queued", "running") and job.reason != "needs_reconsent"

    def _row(self, job: Job, limit: float) -> PendingWait:
        expired = job.since is not None and self.clock.now - job.since > limit
        return PendingWait(job.job_id, job.created_at, job.method, GROUP_REVISION, job.reason, expired)

    def pending_waits(
        self, session: Any, *, methods: Any, offline_seconds: float, batch_size: int, after: Any = None,
    ) -> list[PendingWait]:
        self.pages.append({"methods": tuple(methods), "offline_seconds": offline_seconds, "batch_size": batch_size, "after": after})
        rows = sorted((job.created_at, job.job_id) for job in self.jobs.values() if self._live(job) and job.method in methods)
        if after is not None:
            rows = [row for row in rows if row > after]
        return [self._row(self.jobs[job_id], offline_seconds) for _, job_id in rows[:batch_size]]

    def lock_live_items(self, session: Any, job_id: str) -> bool:
        self.log.append(("lock_items", job_id))
        return job_id not in self.items_held_elsewhere

    def lock_pending_wait(self, session: Any, job_id: str, *, offline_seconds: float) -> PendingWait | None:
        self.log.append(("lock_job", job_id))
        job = self.jobs.get(job_id)
        if job is None or not self._live(job) or job_id in self.rows_held_elsewhere:
            return None
        return self._row(job, offline_seconds)

    def set_wait(self, session: Any, job_id: str, reason: str) -> float | None:
        self.log.append(("set_wait", job_id, reason))
        job = self.jobs[job_id]
        assert job.state in ("queued", "running"), "a paused or ended job is never given a wait"
        if job.reason != reason:
            job.reason, job.since = reason, self.clock.now
        return self.clock.now - (job.since or self.clock.now)

    def clear_wait(self, session: Any, job_id: str) -> bool:
        self.log.append(("clear_wait", job_id))
        job = self.jobs[job_id]
        assert job.state in ("queued", "running"), "a paused or ended job is never written"
        job.reason, job.since = None, None
        return True

    def get(self, session: Any, job_id: str) -> Any:
        job = self.jobs[job_id]
        return SimpleNamespace(job_id=job_id, method=job.method, stage_chain_run_id=None)


class FakeService:
    """The job layer's answer to a refusal -- the call the handlers make. ``ends`` says which jobs it ends; ``raises`` which fail."""

    def __init__(self, log: Log, jobs: FakeJobs) -> None:
        self.log, self.jobs = log, jobs
        self.ends: dict[str, bool] = {}
        self.raises: dict[str, BaseException] = {}

    def pause_for_spend(self, session: Any, job_id: str, spend_reason: str) -> bool:
        self.log.append(("pause_for_spend", job_id, spend_reason))
        if job_id in self.raises:
            raise self.raises[job_id]
        ended = self.ends.get(job_id, True)
        if ended:
            self.jobs.jobs[job_id].state = "failed"
        return ended


class World:
    def __init__(
        self, monkeypatch: pytest.MonkeyPatch, *, members: list[MemberFacts] | None = None, batch_size: int = 200,
        hooks: dict[str, EndedWithoutExecutor] | None = None,
    ) -> None:
        from auditmanager.executors import public

        self.log, self.clock = Log(), Clock()
        self.jobs = FakeJobs(self.log, self.clock)
        self.service = FakeService(self.log, self.jobs)
        self.members = members if members is not None else list(DARK)
        self.revision = SimpleNamespace(group_revision_id=GROUP_REVISION, group_id="exg_01", members=())

        def group_revision_of(session: Any, revision_id: str, groups: Any = None) -> Any:
            self.log.append(("group_revision_of", revision_id))
            return self.revision if revision_id == GROUP_REVISION else None

        def member_facts(session: Any, revision: Any, repository: Any = None) -> list[MemberFacts]:
            self.log.append("member_facts")
            return self.members

        monkeypatch.setattr(public, "group_revision_of", group_revision_of)
        monkeypatch.setattr(public, "member_facts", member_facts)
        self.sweep = ComparisonGroupWaitSweep(
            lambda: FakeSession(self.log), hooks=hooks, repository=self.jobs, service=self.service,  # type: ignore[arg-type]
            batch_size=batch_size,
        )

    def run(self, limit: float = LIMIT) -> ComparisonGroupWaits:
        return self.sweep.sweep(limit)

    def after(self, seconds: float, limit: float = LIMIT) -> ComparisonGroupWaits:
        """Time passes, then one pass."""
        self.clock.advance(seconds)
        return self.run(limit)

    def written(self) -> list[tuple[Any, ...]]:
        return [entry for entry in self.log if isinstance(entry, tuple) and entry[0] in ("set_wait", "clear_wait", "pause_for_spend")]

    def ended(self) -> list[str]:
        return [entry[1] for entry in self.log if isinstance(entry, tuple) and entry[0] == "pause_for_spend"]


# --- the outcome ------------------------------------------------------------------------------------------------------------


def test_a_job_that_waited_for_a_runner_longer_than_the_limit_ends_as_the_in_call_expiry_ends_it(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    world.jobs.add("cmj_a", waited=LIMIT + 1)
    report = world.run()
    assert report == ComparisonGroupWaits(expired=1)
    assert ("pause_for_spend", "cmj_a", REASON_NO_EXECUTOR_ONLINE) in world.log and REASON_NO_EXECUTOR_ONLINE == "no_executor_online"
    assert len(world.log.at("commit")) == 1, "one transaction, committed once"
    assert world.log.first("pause_for_spend") < world.log.first("commit")


def test_exactly_at_the_limit_is_still_a_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    world.jobs.add("cmj_a", waited=LIMIT)
    assert world.run() == ComparisonGroupWaits() and world.written() == []
    assert world.after(0.5).expired == 1, "longer than the limit, as the in-call expiry reads it"


def test_the_reason_the_sweep_hands_the_job_layer_ends_the_job_failed_and_is_no_pause() -> None:
    """The one call both the handlers and the sweep make: this reason is a failure of the job, not a pause."""
    assert service.FAILURE_OF_SPEND_REASON[REASON_NO_EXECUTOR_ONLINE] == "no_executor_online"
    assert service.pause_reason_of(REASON_NO_EXECUTOR_ONLINE) is None


def test_the_default_job_layer_is_the_comparison_ai_job_service() -> None:
    sweep = ComparisonGroupWaitSweep(lambda: None)  # type: ignore[arg-type]
    assert isinstance(sweep._service, service.ComparisonAiJobService)


@pytest.mark.parametrize("bad", [0, -1, 0.0, float("nan")])
def test_a_limit_that_is_not_positive_is_refused_not_defaulted(monkeypatch: pytest.MonkeyPatch, bad: float) -> None:
    world = World(monkeypatch)
    with pytest.raises(ValueError):
        world.run(bad)
    assert world.log == [] and world.jobs.pages == []


def test_a_page_holds_at_least_one() -> None:
    with pytest.raises(ValueError):
        ComparisonGroupWaitSweep(lambda: None, batch_size=0)  # type: ignore[arg-type]


# --- the wait follows the members, and the clock is the sweep's own observation (M1) --------------------------------------------


def test_a_runner_back_at_minute_29_and_gone_again_does_not_end_the_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """The old sweep read the age of the stored wait: a job offline since minute 0 was ended at minute 31 although a runner had served it at
    minute 29. The wait is cleared when a member can take the job, and starts again, from that observation, when the group goes dark."""
    world = World(monkeypatch)
    world.jobs.add("cmj_a", waited=0.0)
    assert world.run() == ComparisonGroupWaits(), "dark from the start: the stored wait is true and young"

    world.members[:] = list(ONLINE)
    assert world.after(29 * 60) == ComparisonGroupWaits(updated=1), "a runner at minute 29: the wait is cleared, not left to age"
    assert world.jobs.jobs["cmj_a"].reason is None and world.jobs.jobs["cmj_a"].since is None

    world.members[:] = list(DARK)
    assert world.after(5) == ComparisonGroupWaits(updated=1), "gone again: a new wait, begun now"
    assert world.jobs.jobs["cmj_a"].since == world.clock.now
    assert world.after(2 * 60) == ComparisonGroupWaits(), "minute 31 of the first wait is minute 2 of this one"
    assert world.ended() == [] and world.jobs.jobs["cmj_a"].state == "running"

    assert world.after(LIMIT - 2 * 60 - 1) == ComparisonGroupWaits(), "a second short of the limit since the new wait began"
    assert world.after(2).expired == 1, "and past it, continuously offline, the job ends"


def test_a_flapping_runner_never_lets_a_wait_reach_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    world.jobs.add("cmj_a", waited=0.0)
    for _ in range(8):
        world.members[:] = list(ONLINE)
        world.after(20 * 60)
        world.members[:] = list(DARK)
        world.after(5)
    assert world.ended() == [], "four hours of waiting in all, and no 30 minutes in a row"


def test_a_job_stored_at_capacity_whose_group_goes_dark_ends_after_the_limit_from_the_sweeps_own_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Waiting for a place has no end, and the stored clock of that wait (ten days old) says nothing of the offline wait: the sweep sees
    the group dark, writes ``runner_offline`` (restarting the clock), and only then does the limit run."""
    world = World(monkeypatch, members=list(FULL))
    world.jobs.add("cmj_a", reason="executor_at_capacity", waited=10 * 24 * 3600.0)
    assert world.run() == ComparisonGroupWaits(), "a wait for a place is true and never ends"

    world.members[:] = list(DARK)
    assert world.after(5) == ComparisonGroupWaits(updated=1), "the group went dark: the wait is runner_offline now, begun now"
    assert ("set_wait", "cmj_a", "runner_offline") in world.log and world.ended() == []
    assert world.after(LIMIT - 1) == ComparisonGroupWaits()
    assert world.after(2) == ComparisonGroupWaits(expired=1), "eventually, and exactly once"
    assert world.after(10) == ComparisonGroupWaits(), "an ended job is no candidate"


def test_a_wait_for_a_place_never_ends_a_job_however_old(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, members=list(FULL))
    world.jobs.add("cmj_a", reason="executor_at_capacity", waited=10 * 24 * 3600.0)
    assert world.run() == ComparisonGroupWaits() and world.written() == [] and not world.log.at("lock_items")


def test_a_wait_for_a_runner_becomes_a_wait_for_a_place_when_a_member_is_only_full(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, members=list(FULL))
    world.jobs.add("cmj_a", reason="runner_offline", waited=LIMIT * 5)
    assert world.run() == ComparisonGroupWaits(updated=1), "a member that can take it once it has a place: not an offline wait"
    assert world.jobs.jobs["cmj_a"].reason == "executor_at_capacity" and world.ended() == []


def test_a_job_that_waits_for_nothing_yet_is_given_the_wait_that_is_true(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    world.jobs.add("cmj_a", reason=None, waited=None, state="queued")
    assert world.run() == ComparisonGroupWaits(updated=1)
    assert world.jobs.jobs["cmj_a"].reason == "runner_offline" and world.jobs.jobs["cmj_a"].since == world.clock.now


def test_a_job_whose_group_can_take_it_and_that_waits_for_nothing_is_left_alone_with_no_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, members=list(ONLINE))
    world.jobs.add("cmj_a", reason=None, waited=None, state="queued")
    assert world.run() == ComparisonGroupWaits() and world.written() == [] and not world.log.at("lock_items")


def test_the_wait_a_flap_cleared_is_cleared_under_the_lock_on_a_fresh_reading_not_the_pass_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """The cheap look reads each group once per pass. A group that changed between that look and the lock is read again under the lock, and
    what is written is what that reading says."""
    world = World(monkeypatch)
    world.jobs.add("cmj_a", reason="executor_at_capacity", waited=5.0)
    original = world.jobs.lock_live_items

    def flip(session: Any, job_id: str) -> bool:
        world.members[:] = list(ONLINE)  # the group recovers after the cheap look, before the lock
        return original(session, job_id)

    world.jobs.lock_live_items = flip  # type: ignore[method-assign]
    assert world.run() == ComparisonGroupWaits(updated=1)
    assert world.jobs.jobs["cmj_a"].reason is None, "cleared, not set to the offline the cheap look saw"


# --- paused, ended and reconsent jobs are never touched ---------------------------------------------------------------------


@pytest.mark.parametrize("state", ["paused", "completed", "failed", "cancelled"])
def test_a_job_that_is_paused_or_ended_is_never_read_or_written(monkeypatch: pytest.MonkeyPatch, state: str) -> None:
    world = World(monkeypatch)
    world.jobs.add("cmj_a", waited=LIMIT * 10, state=state)
    assert world.run() == ComparisonGroupWaits()
    assert world.written() == [] and not world.log.at("lock_items") and not world.log.at("lock_job")


def test_a_job_in_needs_reconsent_is_left_to_the_person_who_renews_it(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    world.jobs.add("cmj_a", reason="needs_reconsent", waited=LIMIT * 10)
    assert world.run() == ComparisonGroupWaits() and world.written() == []


def test_a_job_paused_between_the_page_and_the_lock_is_not_written(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    job = world.jobs.add("cmj_a", reason="executor_at_capacity", waited=5.0)
    original = world.jobs.lock_live_items

    def pause(session: Any, job_id: str) -> bool:
        job.state = "paused"  # the user paused it after the page was read
        return original(session, job_id)

    world.jobs.lock_live_items = pause  # type: ignore[method-assign]
    assert world.run() == ComparisonGroupWaits(skipped=1) and world.written() == []


# --- locks: items first, then the job; a job in the middle of a handler is left alone ------------------------------------------


def test_the_items_are_locked_before_the_job_row_and_both_before_the_job_is_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    world.jobs.add("cmj_a", waited=LIMIT + 1)
    world.run()
    log = world.log
    assert log.first("lock_items") < log.first("lock_job") < log.first("pause_for_spend") < log.first("commit")


def test_a_job_whose_item_a_handler_holds_is_left_for_a_later_pass_and_its_row_is_never_locked(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    world.jobs.add("cmj_busy", waited=LIMIT + 1)
    world.jobs.add("cmj_free", waited=LIMIT + 1)
    world.jobs.items_held_elsewhere.add("cmj_busy")
    report = world.run()
    assert (report.expired, report.skipped) == (1, 1)
    assert ("lock_job", "cmj_busy") not in world.log and world.ended() == ["cmj_free"]


def test_a_job_another_transaction_holds_is_not_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    world.jobs.add("cmj_held", waited=LIMIT + 1)
    world.jobs.rows_held_elsewhere.add("cmj_held")
    assert world.run() == ComparisonGroupWaits(skipped=1) and world.written() == [] and not world.log.at("commit")


def test_a_group_revision_that_is_gone_is_left_alone_not_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    world.jobs.add("cmj_a", waited=LIMIT + 1)
    monkeypatch.setattr(
        "auditmanager.executors.public.group_revision_of", lambda session, revision_id, groups=None: None,
    )
    assert world.run() == ComparisonGroupWaits() and world.written() == []


def test_a_job_the_job_layer_does_not_end_is_not_committed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The job moved between the lock and the edge (``pause_for_spend`` answers ``False``): nothing is counted as ended."""
    world = World(monkeypatch)
    world.jobs.add("cmj_a", waited=LIMIT + 1)
    world.service.ends["cmj_a"] = False
    report = world.run()
    assert (report.expired, report.skipped) == (0, 1) and not world.log.at("commit")


# --- methods and hooks --------------------------------------------------------------------------------------------------------


def test_only_the_methods_that_can_be_ended_the_way_their_handler_ends_them_are_swept(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no hooks only the two methods whose handler does nothing but ``pause_for_spend`` are candidates; a method with a hook is added by
    giving it one, and a job of any other method is never read -- not ended differently from its own handler."""
    assert ENDED_BY_PAUSE_ONLY == {"pair_check", "spec"} and ENDED_BY_PAUSE_ONLY <= set(METHODS)
    bare = World(monkeypatch)
    assert bare.sweep.methods == ("pair_check", "spec")
    for method in ("report", "stage_review", "sheet_changes"):
        bare.jobs.add(f"cmj_{method}", method=method, waited=LIMIT + 1)
    bare.jobs.add("cmj_pair", method="pair_check", waited=LIMIT + 1)
    assert bare.run().expired == 1 and bare.ended() == ["cmj_pair"]
    assert bare.jobs.pages[0]["methods"] == ("pair_check", "spec")

    hooked = World(monkeypatch, hooks={"report": EndedWithoutExecutor(after=lambda session, job: None)})
    assert hooked.sweep.methods == ("pair_check", "report", "spec")


def test_a_hook_runs_around_the_ending_in_the_order_its_handler_takes_and_inside_the_one_transaction(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    hooks = {"stage_review": EndedWithoutExecutor(
        before=lambda session, job: calls.append(f"before:{job.job_id}"), after=lambda session, job: calls.append(f"after:{job.job_id}"),
    ), "report": EndedWithoutExecutor(after=lambda session, job: calls.append(f"report_after:{job.job_id}"))}
    world = World(monkeypatch, hooks=hooks)
    world.jobs.add("cmj_stage", method="stage_review", waited=LIMIT + 1)
    world.jobs.add("cmj_report", method="report", waited=LIMIT + 1)
    world.jobs.add("cmj_pair", method="pair_check", waited=LIMIT + 1)
    assert world.run().expired == 3
    assert calls == ["before:cmj_stage", "after:cmj_stage", "report_after:cmj_report"], "no hook for a pair check; each method its own"
    stage = world.log.index(("pause_for_spend", "cmj_stage", REASON_NO_EXECUTOR_ONLINE))
    assert len(world.log.at("commit")) == 3, "each job in a transaction of its own"
    assert stage < world.log.first("commit")


def test_a_hook_that_fails_rolls_the_job_back_and_the_pass_goes_on(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    def broken(session: Any, job: Any) -> None:
        raise RuntimeError("row cmj_stage quoted a secret value")

    world = World(monkeypatch, hooks={"stage_review": EndedWithoutExecutor(before=broken)})
    world.jobs.add("cmj_stage", method="stage_review", waited=LIMIT + 1)
    world.jobs.add("cmj_pair", method="pair_check", waited=LIMIT + 1)
    with caplog.at_level(logging.ERROR, logger=group_waits.__name__):
        report = world.run()
    assert report == ComparisonGroupWaits(expired=1, failed=1)
    assert world.ended() == ["cmj_pair"], "the job layer was not asked to end a job whose hook failed"
    text = " ".join(record.getMessage() for record in caplog.records)
    assert "RuntimeError" in text and "secret value" not in text and "cmj_stage" not in text


# --- one pass walks every candidate; a failure stops nothing --------------------------------------------------------------------


def test_a_pass_walks_every_candidate_page_after_page(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, batch_size=2)
    names = [f"cmj_{index}" for index in range(5)]
    for name in names:
        world.jobs.add(name, waited=LIMIT + 1)
    report = world.run()
    assert report.expired == 5 and world.ended() == names
    # the first page is 2, then 2 after the last seen, then the rest: ended jobs leave the candidates, but the keyset moves on regardless
    assert world.jobs.pages[0]["after"] is None and all(page["after"] is not None for page in world.jobs.pages[1:])
    assert {page["batch_size"] for page in world.jobs.pages} == {2}


def test_every_candidate_is_decided_once_per_pass_whatever_its_state(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, batch_size=1)
    world.jobs.add("cmj_0", reason=None, waited=None, state="queued")      # -> a wait is written
    world.jobs.add("cmj_1", reason="runner_offline", waited=1.0)           # true and young: nothing
    world.jobs.add("cmj_2", reason="runner_offline", waited=LIMIT + 1)     # ends
    world.jobs.add("cmj_3", reason="executor_at_capacity", waited=3.0)     # -> offline
    report = world.run()
    assert report == ComparisonGroupWaits(expired=1, updated=2)
    assert len(world.jobs.pages) >= 4


def test_a_job_whose_transaction_fails_is_counted_and_logged_by_category_and_the_pass_goes_on(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    world = World(monkeypatch)
    for name in ("cmj_0", "cmj_bad", "cmj_2"):
        world.jobs.add(name, waited=LIMIT + 1)
    world.service.raises["cmj_bad"] = RuntimeError("row cmj_bad quoted a secret value")
    with caplog.at_level(logging.ERROR, logger=group_waits.__name__):
        report = world.run()
    assert report == ComparisonGroupWaits(expired=2, failed=1)
    assert world.ended() == ["cmj_0", "cmj_bad", "cmj_2"]
    assert len(world.log.at("commit")) == 2, "the failed job committed nothing"
    text = " ".join(record.getMessage() for record in caplog.records)
    assert "RuntimeError" in text and "secret value" not in text and "cmj_bad" not in text


def test_the_sweep_takes_no_group_or_connection_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    world.jobs.add("cmj_a", waited=LIMIT + 1)
    world.run()
    names = {entry[0] if isinstance(entry, tuple) else entry for entry in world.log}
    assert names <= {
        "open", "close", "commit", "rollback", "lock_items", "lock_job", "group_revision_of", "member_facts", "pause_for_spend",
        "set_wait", "clear_wait",
    }, names


def test_nothing_to_do_reads_one_page_and_writes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    assert world.run() == ComparisonGroupWaits()
    assert len(world.jobs.pages) == 1 and not world.log.at("commit") and not world.log.at("lock_items")


def test_the_sweep_and_the_first_call_read_eligibility_through_one_function() -> None:
    assert dispatch.is_eligible(facts("A")) and dispatch.is_eligible(facts("A", used=1))
    assert not dispatch.is_eligible(facts("A", **OFFLINE)) and not dispatch.is_eligible(facts("A", probed_ok=False))
