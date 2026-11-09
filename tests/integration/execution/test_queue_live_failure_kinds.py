"""`D-462`: `live_failure_count` (`D-395`) tells the two analyses apart, on real PostgreSQL rows.

A failed job stays «live» unless a LATER job of the same document version AND the same kind of analysis exists, the kind being the
shared ``STANDARD_RUN_SQL`` (the sealed AR v3 beta pair against any other). `test_queue_readable.py` proves the rest of the rule on
standard runs only; this module puts a v3 group and a standard run on ONE version and reads the count back through the same
adapter call the side menu's red mark reads (`ExecutionAdapter.list_queue`):

* a later v3 group does not answer a failed standard run, and a later standard run does not answer a failed v3 member;
* the same kind does answer: a later standard run answers a failed standard run, a later group answers a failed member;
* the kind condition is what the world tells apart: with every run read as «standard» the same rows give another count.

The v3 runs are the six members of a real group (`start_ar_v3_group` on a sealed pack, on a private migrated database, committed so that
the group's deferred constraint trigger checks its six members), advanced
`created -> queued` with their jobs enqueued as the served start does (`RunAdapter.start_ar_v3_group`). The database is private, so
every count here is absolute and not «more than before».

`test_a_failed_member_is_answered_by_its_own_later_siblings_as_the_contract_reads_it` PINS A QUESTIONABLE READING, on purpose and by
name (`D-600`): the rule reads a group's own later members as «the version having been run again», which they are not. Changing it
is a contract and owner matter; whoever does must flip that test, not delete it.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import nullcontext

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

import auditmanager.runs.public as runs_public
from auditmanager.analysis.public import AR_V3_BETA_BUNDLE_ID, AR_V3_BETA_PROFILE_ID
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.bootstrap.adapters import ExecutionAdapter
from auditmanager.jobs.public import JobRepository
from auditmanager.runs.analysis_kind import analysis_kind
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.v3_group import start_ar_v3_group
from auditmanager.shared.identity import RunId
from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
)
from tests.integration.db.test_ar_v3_run_group import _seed  # type: ignore[import-not-found]

V3 = (str(AR_V3_BETA_PROFILE_ID), str(AR_V3_BETA_BUNDLE_ID))
#: The pair the registry routes an АР version to: a run of it is of the standard analysis.
STANDARD = load_text_profile_registry().section_profiles()["AR"]


class World:
    """One document version on a private database, and the means to start runs on it and to fail their jobs."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.version, self.pack = _seed(session)
        session.commit()
        self.project = session.execute(text("SELECT project_uid FROM project")).scalar_one()
        self.groups = 0

    def standard_run(self) -> str:
        """A run of the standard analysis, queued with its job as `start_run` leaves it."""
        run_id = str(RunId.new())
        runs = RunRepository()
        runs.create(
            self.session, run_id=run_id, project_uid=self.project, version_uid=self.version,
            analysis_profile_id=STANDARD[0], prompt_bundle_id=STANDARD[1], provider_mode="recorded",
            frozen_input_digest="a" * 64, command_id=None,
        )
        runs.advance(self.session, run_id=run_id, from_state="created", to_state="queued")
        JobRepository().enqueue(self.session, run_id=run_id)
        assert analysis_kind(STANDARD[0], STANDARD[1]) == "standard"
        return run_id

    def group(self) -> list[str]:
        """A v3 group of six runs, queued with their jobs in scope order as the served start leaves them."""
        self.groups += 1
        started = start_ar_v3_group(
            self.session, version_uid=self.version, idempotency_key=f"live-failure-{self.groups}", provider_mode="recorded",
            pack=self.pack, input_budget_characters=1000, start_allowed=True,
        )
        self.session.commit()  # the group's deferred constraint trigger (six members, one pin) checks at commit
        members = [member.run_id for member in started.group.members]
        assert len(members) == 6
        for run_id in members:
            RunRepository().advance(self.session, run_id=run_id, from_state="created", to_state="queued")
            JobRepository().enqueue(self.session, run_id=run_id)
        kinds = {
            analysis_kind(*row) for row in self.session.execute(
                text("SELECT analysis_profile_id, prompt_bundle_id FROM audit_run WHERE run_id = ANY(:ids)"), {"ids": members})
        }
        assert kinds == {"ar_v3_beta"}, kinds
        return members

    def fail(self, run_id: str) -> None:
        """The run's job ends `failed` by the real commands (claim, then finish without a result)."""
        jobs = JobRepository()
        authority = jobs.start_execution(self.session, run_id=run_id)
        jobs.finish_execution(self.session, authority, publishes_result=False)
        assert self.session.execute(text("SELECT state FROM job WHERE run_id = :r"), {"r": run_id}).scalar_one() == "failed"

    def live(self) -> int:
        """The side menu's red mark: the count the queue page carries."""
        adapter = ExecutionAdapter(lambda: nullcontext(self.session), runs=None)  # type: ignore[arg-type]
        count = adapter.list_queue(cursor=None, limit=1).live_failure_count
        assert count is not None, "the page carries the count whatever its filters"
        return count


@pytest.fixture
def world(migrated_engine: Engine) -> Iterator[World]:
    with Session(migrated_engine) as session:
        built = World(session)
        assert built.live() == 0, "a private database starts with no failure"
        yield built
        session.rollback()


def test_a_later_v3_group_does_not_answer_a_failed_standard_run(world: World) -> None:
    failed = world.standard_run()
    world.fail(failed)
    assert world.live() == 1
    world.group()
    assert world.live() == 1, "six queued v3 jobs of the same version are another analysis: the standard failure stays live"


def test_a_later_standard_run_does_not_answer_a_failed_v3_member(world: World) -> None:
    members = world.group()
    world.fail(members[-1])  # the last of the six, so that no sibling is later: the siblings are `D-600`'s question
    assert world.live() == 1
    world.standard_run()
    assert world.live() == 1, "a later standard run is another analysis: the v3 failure stays live"


def test_the_same_kind_does_answer_a_later_standard_run_a_standard_failure_and_a_later_group_a_member(world: World) -> None:
    standard = world.standard_run()
    world.fail(standard)
    members = world.group()
    world.fail(members[-1])
    assert world.live() == 2, "one live failure of each analysis on one version"
    world.standard_run()
    assert world.live() == 1, "the later standard run answered the standard failure and only it"
    world.group()
    assert world.live() == 0, "the later group answered the v3 failure"


def test_a_failure_of_each_kind_is_counted_once_each_whichever_was_first(world: World) -> None:
    members = world.group()
    world.fail(members[-1])
    standard = world.standard_run()  # later than the v3 failure, of another kind
    world.fail(standard)
    assert world.live() == 2
    again = world.standard_run()
    world.fail(again)
    assert world.live() == 2, "two failures in a row of one kind are one live failure: the last; the other kind's stays"


def test_a_failed_member_is_answered_by_its_own_later_siblings_as_the_contract_reads_it(world: World) -> None:
    """`D-600`: PINS THE CURRENT READING, which is questionable. The contract (`D-395`, 1.43.0) says a failure is answered by «a later
    job for a run of the same document version and the same analysis»; the five later members of a group started in one transaction are
    that, though nobody ran the version again. A failed member of a group whose siblings are fine therefore does not count. Changing it
    means another sentence in `contracts/api/v1` and an owner's ruling (a group-aware rule: a later job answers a v3 member only when it
    belongs to another group); this test then flips to `== 1`."""
    members = world.group()
    world.fail(members[0])  # F1; F2..S2 are queued after it
    assert world.live() == 0
    world.fail(members[-1])  # the last member failing is not answered by anyone
    assert world.live() == 1


def test_the_kind_condition_is_what_the_counts_above_come_from(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """The mutation check of this module: with every run read as «standard» the mixed world counts differently, so the tests above
    can fail on a predicate that ignores the kind (`STANDARD_RUN_SQL` is read inside the count, at each call)."""
    failed = world.standard_run()
    world.fail(failed)
    world.group()
    assert world.live() == 1
    monkeypatch.setattr(runs_public, "STANDARD_RUN_SQL", "TRUE")
    assert world.live() == 0, "with the kinds merged, the later group answers the standard failure: the world can tell the difference"
