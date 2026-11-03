"""`EXEC2-FOLLOWUP-01` item 3 (ADR-0026 decision 15, `R-149c`): the offline sweep of comparison AI jobs admitted by a group.

Before the sweep a job's offline expiry was decided only inside a retried call. The sweep walks the live ``pending`` jobs that have
waited for ``runner_offline`` longer than the limit and gives each the in-call expiry's outcome. Container-free: the job repository, the
job service and the group's members are stand-ins that record what they were asked and in what order, so each guard is an assertion that
would fail without it:

* the outcome is the in-call expiry's, by the same call: ``pause_for_spend(job, "no_executor_online")``, committed once, in a
  transaction of the job's own;
* **items first, then the job row** -- the order every handler takes them -- and a job a handler is in the middle of (an item that is
  locked elsewhere) is left alone, as is a job another transaction holds;
* the expiry is **decided under the lock**: a job whose locked row no longer waits for ``runner_offline``, or not for long enough, or is
  no longer pending, is not ended, whatever the page that named it said;
* a group that **has an eligible member again** is not ended, and neither is a group that only waits for capacity (which never expires);
* one pass walks **every** candidate, page after page (a keyset), and a job whose transaction fails does not stop the pass;
* a job is never given a wait by the sweep, and the sweep is the worker's step only for a worker that dispatches groups.

The same flows over real rows are ``tests/integration/comparison/test_group_waits.py``.

Written and **not run** in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.ai_jobs import group_waits, service
from auditmanager.comparison.ai_jobs.group_waits import ComparisonGroupWaitSweep, ComparisonGroupWaits
from auditmanager.comparison.ai_jobs.repository import OfflineWait
from auditmanager.comparison.spend import dispatch
from auditmanager.comparison.spend.errors import REASON_NO_EXECUTOR_ONLINE
from auditmanager.executors.public import MemberFacts

BASE = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)
GROUP_REVISION = "exgr_01"


def facts(name: str, *, used: int = 0, capacity: int = 1, **over: Any) -> MemberFacts:
    values: dict[str, Any] = {
        "connection_id": f"exc_{name}", "tie_break_order": None, "revision_is_snapshot": True, "archived": False,
        "served": True, "probed_ok": True, "runner_online": True, "capacity": capacity, "used": used,
    }
    values.update(over)
    return MemberFacts(**values)


OFFLINE = {"runner_online": False}


class Log(list):  # type: ignore[type-arg]
    def at(self, name: str) -> list[int]:
        return [i for i, entry in enumerate(self) if (entry[0] if isinstance(entry, tuple) else entry) == name]

    def first(self, name: str) -> int:
        return self.at(name)[0]


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


class FakeJobs:
    """The job repository's sweep statements over a list of candidates; ``locked`` is how each job stands under its lock."""

    def __init__(self, log: Log, candidates: list[str], *, locked: dict[str, OfflineWait | None] | None = None) -> None:
        self.log = log
        self.candidates = {job_id: BASE + timedelta(seconds=index) for index, job_id in enumerate(candidates)}
        self.locked = locked or {}
        self.items_held_elsewhere: set[str] = set()
        self.pages: list[dict[str, Any]] = []

    def offline_waiting(self, session: Any, *, offline_seconds: float, batch_size: int, after: Any = None) -> list[tuple[datetime, str]]:
        self.pages.append({"offline_seconds": offline_seconds, "batch_size": batch_size, "after": after})
        ordered = sorted((created, job_id) for job_id, created in self.candidates.items())
        if after is not None:
            ordered = [row for row in ordered if row > after]
        return ordered[:batch_size]

    def lock_live_items(self, session: Any, job_id: str) -> bool:
        self.log.append(("lock_items", job_id))
        return job_id not in self.items_held_elsewhere

    def lock_offline_wait(self, session: Any, job_id: str, *, offline_seconds: float) -> OfflineWait | None:
        self.log.append(("lock_job", job_id, offline_seconds))
        return self.locked[job_id] if job_id in self.locked else waiting(job_id)


def waiting(job_id: str, *, reason: str | None = "runner_offline", expired: bool = True, revision: str = GROUP_REVISION) -> OfflineWait:
    return OfflineWait(job_id=job_id, group_revision_id=revision, wait_reason=reason, expired=expired)


class FakeService:
    """The job layer's answer to a refusal: what the handlers call. ``ends`` says which jobs it ends; ``raises`` which fail."""

    def __init__(self, log: Log) -> None:
        self.log = log
        self.ends: dict[str, bool] = {}
        self.raises: dict[str, BaseException] = {}

    def pause_for_spend(self, session: Any, job_id: str, spend_reason: str) -> bool:
        self.log.append(("pause_for_spend", job_id, spend_reason))
        if job_id in self.raises:
            raise self.raises[job_id]
        return self.ends.get(job_id, True)


class World:
    def __init__(
        self, monkeypatch: pytest.MonkeyPatch, candidates: list[str], *, members: list[MemberFacts] | None = None,
        locked: dict[str, OfflineWait | None] | None = None, batch_size: int = 200,
    ) -> None:
        from auditmanager.executors import public

        self.log = Log()
        self.jobs = FakeJobs(self.log, candidates, locked=locked)
        self.service = FakeService(self.log)
        self.members = members if members is not None else [facts("A", **OFFLINE), facts("B", **OFFLINE)]
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
            lambda: FakeSession(self.log), repository=self.jobs, service=self.service, batch_size=batch_size,  # type: ignore[arg-type]
        )

    def run(self, limit: float = 1800.0) -> ComparisonGroupWaits:
        return self.sweep.expire_offline(limit)

    def decided(self) -> list[str]:
        return [entry[1] for entry in self.log if isinstance(entry, tuple) and entry[0] == "lock_job"]

    def ended(self) -> list[str]:
        return [entry[1] for entry in self.log if isinstance(entry, tuple) and entry[0] == "pause_for_spend"]


# --- the outcome -------------------------------------------------------------------------------------------------------------


def test_a_job_over_the_limit_with_no_eligible_member_ends_as_the_in_call_expiry_ends_it(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, ["cmj_a"])
    report = world.run()
    assert report == ComparisonGroupWaits(expired=1, skipped=0, failed=0)
    entry = next(e for e in world.log if isinstance(e, tuple) and e[0] == "pause_for_spend")
    assert entry == ("pause_for_spend", "cmj_a", REASON_NO_EXECUTOR_ONLINE) and REASON_NO_EXECUTOR_ONLINE == "no_executor_online"
    assert len(world.log.at("commit")) == 1, "one transaction, committed once"
    assert world.log.first("pause_for_spend") < world.log.first("commit")


def test_the_reason_the_sweep_hands_the_job_layer_ends_the_job_failed_and_is_no_pause() -> None:
    """The one call both the handlers and the sweep make: this reason is a failure of the job, not a pause."""
    assert service.FAILURE_OF_SPEND_REASON[REASON_NO_EXECUTOR_ONLINE] == "no_executor_online"
    assert service.pause_reason_of(REASON_NO_EXECUTOR_ONLINE) is None


def test_the_default_job_layer_is_the_comparison_ai_job_service() -> None:
    sweep = ComparisonGroupWaitSweep(lambda: None)  # type: ignore[arg-type]
    assert isinstance(sweep._service, service.ComparisonAiJobService)


def test_the_sweep_is_handed_the_limit_it_decides_on_and_reads_the_candidates_with_it(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, ["cmj_a"])
    world.run(90.0)
    assert world.jobs.pages[0]["offline_seconds"] == 90.0
    assert [entry for entry in world.log if isinstance(entry, tuple) and entry[0] == "lock_job"][0][2] == 90.0


@pytest.mark.parametrize("bad", [0, -1, 0.0, float("nan")])
def test_a_limit_that_is_not_positive_is_refused_not_defaulted(monkeypatch: pytest.MonkeyPatch, bad: float) -> None:
    world = World(monkeypatch, ["cmj_a"])
    with pytest.raises(ValueError):
        world.run(bad)
    assert world.log == [] and world.jobs.pages == []


def test_a_page_holds_at_least_one() -> None:
    with pytest.raises(ValueError):
        ComparisonGroupWaitSweep(lambda: None, batch_size=0)  # type: ignore[arg-type]


# --- locks: items first, then the job; a job in the middle of a handler is left alone ------------------------------------------


def test_the_items_are_locked_before_the_job_row_and_both_before_the_job_is_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, ["cmj_a"])
    world.run()
    log = world.log
    assert log.first("lock_items") < log.first("lock_job") < log.first("pause_for_spend") < log.first("commit")


def test_a_job_whose_item_a_handler_holds_is_left_for_a_later_pass_and_its_row_is_never_locked(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, ["cmj_busy", "cmj_free"])
    world.jobs.items_held_elsewhere.add("cmj_busy")
    report = world.run()
    assert (report.expired, report.skipped) == (1, 1)
    assert world.decided() == ["cmj_free"] and world.ended() == ["cmj_free"]


def test_a_job_another_transaction_holds_or_that_is_no_longer_pending_is_not_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, ["cmj_held", "cmj_over"], locked={"cmj_held": None, "cmj_over": None})
    report = world.run()
    assert (report.expired, report.skipped) == (0, 2)
    assert world.ended() == [] and not world.log.at("commit")


# --- decided under the lock, from the locked row -----------------------------------------------------------------------------------


@pytest.mark.parametrize("locked", [
    waiting("cmj_a", reason="executor_at_capacity"),     # the reason moved to a wait for capacity, which never expires
    waiting("cmj_a", reason="needs_reconsent"),
    waiting("cmj_a", reason=None),                        # the wait was cleared (the job bound, or was renewed)
    waiting("cmj_a", expired=False),                      # the clock restarted since the page was read
])
def test_the_expiry_is_decided_on_the_locked_row_not_on_the_page_that_named_the_job(
    monkeypatch: pytest.MonkeyPatch, locked: OfflineWait,
) -> None:
    world = World(monkeypatch, ["cmj_a"], locked={"cmj_a": locked})
    report = world.run()
    assert (report.expired, report.skipped) == (0, 1)
    assert world.ended() == [] and not world.log.at("commit")
    assert not world.log.at("member_facts"), "a job that does not qualify under its lock does not even read its group"


@pytest.mark.parametrize("members", [
    [facts("A"), facts("B", **OFFLINE)],                  # one member can take it now
    [facts("A", used=1), facts("B", used=1)],             # every member is only full: the job waits for capacity, and that never ends
    [facts("A", used=1), facts("B", **OFFLINE)],
])
def test_a_group_with_an_eligible_member_is_never_ended(monkeypatch: pytest.MonkeyPatch, members: list[MemberFacts]) -> None:
    world = World(monkeypatch, ["cmj_a"], members=members)
    report = world.run()
    assert (report.expired, report.skipped) == (0, 1)
    assert world.ended() == [] and not world.log.at("commit")


@pytest.mark.parametrize("issue", [
    {"revision_is_snapshot": False}, {"archived": True}, {"served": False}, {"probed_ok": False}, {"runner_online": False},
])
def test_every_issue_that_makes_a_member_ineligible_counts_as_nobody_online(monkeypatch: pytest.MonkeyPatch, issue: dict[str, bool]) -> None:
    """The in-call reading: a revised, archived, unserved or unprobed member is, for the waiting job, no executor online."""
    world = World(monkeypatch, ["cmj_a"], members=[facts("A", **issue), facts("B", **issue)])
    assert world.run().expired == 1


def test_the_sweep_and_the_first_call_read_eligibility_through_one_function() -> None:
    assert dispatch.is_eligible(facts("A")) and dispatch.is_eligible(facts("A", used=1))
    assert not dispatch.is_eligible(facts("A", **OFFLINE)) and not dispatch.is_eligible(facts("A", probed_ok=False))


def test_a_group_revision_that_is_gone_is_left_alone_not_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, ["cmj_a"], locked={"cmj_a": waiting("cmj_a", revision="exgr_gone")})
    assert world.run().skipped == 1 and world.ended() == []


def test_a_job_the_job_layer_does_not_end_is_not_committed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The job moved between the lock and the edge (``pause_for_spend`` answers ``False``): nothing is counted as expired."""
    world = World(monkeypatch, ["cmj_a"])
    world.service.ends["cmj_a"] = False
    report = world.run()
    assert (report.expired, report.skipped) == (0, 1) and not world.log.at("commit")


# --- one pass walks every candidate; a failure stops nothing --------------------------------------------------------------------


def test_a_pass_walks_every_candidate_page_after_page(monkeypatch: pytest.MonkeyPatch) -> None:
    names = [f"cmj_{index}" for index in range(5)]
    world = World(monkeypatch, names, batch_size=2)
    report = world.run()
    assert report.expired == 5 and world.ended() == names
    assert [page["after"] is None for page in world.jobs.pages] == [True, False, False], "2 + 2 + 1, a keyset after the last job seen"
    assert world.jobs.pages[1]["after"][1] == "cmj_1" and world.jobs.pages[2]["after"][1] == "cmj_3"
    assert {page["batch_size"] for page in world.jobs.pages} == {2}


def test_a_full_last_page_is_followed_by_one_more_read(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, ["cmj_0", "cmj_1"], batch_size=2)
    world.run()
    assert len(world.jobs.pages) == 2 and world.jobs.pages[1]["after"][1] == "cmj_1"


def test_a_job_whose_transaction_fails_is_counted_and_logged_by_category_and_the_pass_goes_on(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    world = World(monkeypatch, ["cmj_0", "cmj_bad", "cmj_2"])
    world.service.raises["cmj_bad"] = RuntimeError("row cmj_bad quoted a secret value")
    with caplog.at_level(logging.ERROR, logger=group_waits.__name__):
        report = world.run()
    assert report == ComparisonGroupWaits(expired=2, skipped=0, failed=1)
    assert world.ended() == ["cmj_0", "cmj_bad", "cmj_2"]
    assert len(world.log.at("commit")) == 2, "the failed job committed nothing"
    text = " ".join(record.getMessage() for record in caplog.records)
    assert "RuntimeError" in text and "secret value" not in text and "cmj_bad" not in text


def test_the_sweep_writes_no_wait_and_takes_no_group_or_connection_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, ["cmj_a"])
    world.run()
    names = {entry[0] if isinstance(entry, tuple) else entry for entry in world.log}
    assert names <= {
        "open", "close", "commit", "rollback", "lock_items", "lock_job", "group_revision_of", "member_facts", "pause_for_spend",
    }, names


def test_nothing_to_do_reads_one_page_and_writes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, [])
    assert world.run() == ComparisonGroupWaits()
    assert len(world.jobs.pages) == 1 and not world.log.at("commit") and not world.log.at("lock_items")
