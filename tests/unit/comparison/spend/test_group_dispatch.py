"""`EXEC2-GROUP-CMP-01` (ADR-0026 decisions 12 to 16): the first-call binding of a comparison job admitted by a rule or a group,
against a recording stand-in for the database. Container-free.

Written and **not run** in EXEC-2 (`R-149d`, D-292). Every statement the real database would take is a line in one log, so the order
the ADR demands is an assertion on a list:

* the lock order -- the group's row, the members' connections in ascending ``connection_id``, then the day -- and the commit
  before any model I/O;
* the choice (the lowest ``used / capacity`` among the eligible members that have a free unit, the persisted rotation breaking a tie),
  the rotation advancing only with a dispatch that is kept;
* the wait (``executor_at_capacity`` is unbounded, ``runner_offline`` ends the job after the offline wait, and exactly at the wait is
  still a wait) and the consent that does not hold (nothing is called, ``needs_reconsent`` is recorded);
* the ceilings applied against the selected member, ``not_metered`` shown as such, the binding written once, with its event;
* no re-routing: a bound job stays on its member, whatever the group looks like, and a member that is busy is waited for;
* `EXEC2-FOLLOWUP-01` item 1 -- **one price**: the rates the consent was given on (the group revision's snapshot) must be the rates the
  bound member's pin is priced at now (the provider lock's), the rule a Run's dispatch holds; a lock that has moved since the group
  revision was made refuses the call ``consent_stale`` and re-prices nothing, and the ceilings, the journal's estimate and the cost the
  call settles at are one price.

What the real database adds -- the trigger that writes the connection revision once, the locks that really exclude, the two threads that
really race -- is ``tests/integration/comparison/test_group_binding.py``.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import ModelPin, ModelRequest, ModelResponse, ProviderMode
from auditmanager.comparison.ai_jobs.model import METHODS, AiJobRecord, work_kind_of
from auditmanager.comparison.spend import dispatch, errors
from auditmanager.comparison.spend.caller import ComparisonModelCaller
from auditmanager.comparison.spend.model import CallEstimate, CallRoute, Consent, Spend
from auditmanager.comparison.spend.repository import ComparisonSpendRepository
from auditmanager.executors.public import MemberFacts
from auditmanager.shared.errors import DomainError, ErrorCode

NOW = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)
DIGEST = "ab" * 32
MODEL = "claude-opus-5"
GATEWAY = "anthropic/claude-opus-5"
GROUP, GROUP_REVISION, RULE_REVISION = "exg_01", "exgr_01", "exrr_01"
JOB = "cmj_01"
#: USD 1 per million input tokens, USD 5 per million output tokens: the call below is USD 2.00.
PIN = ModelPin(model_id=MODEL, input_per_mtok_usd=1.0, output_per_mtok_usd=5.0)
ESTIMATE = CallEstimate(input_tokens=1_000_000, output_tokens=200_000)
USD = 1_000_000


@pytest.fixture(autouse=True)
def provider_lock(monkeypatch: pytest.MonkeyPatch) -> list[ModelPin]:
    """The provider lock as this file reads it: one pin, ``PIN``. A test moves the lock by replacing the list's content. (The real
    lock prices ``claude-opus-5`` at other rates than the group revisions below hold, which the rates rule would refuse.)"""
    from auditmanager.executors import public

    pins = [PIN]
    monkeypatch.setattr(public, "pinned_models", lambda: tuple(pins))
    return pins


class Log(list):  # type: ignore[type-arg]
    def at(self, name: str) -> list[int]:
        return [i for i, entry in enumerate(self) if (entry[0] if isinstance(entry, tuple) else entry) == name]

    def first(self, name: str) -> int:
        return self.at(name)[0]

    def entry(self, name: str) -> tuple[Any, ...]:
        return next(entry for entry in self if isinstance(entry, tuple) and entry[0] == name)


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

    @contextmanager
    def begin_nested(self):  # type: ignore[no-untyped-def]
        self.log.append("savepoint")
        try:
            yield
        except BaseException:
            self.log.append("savepoint_rollback")
            raise
        else:
            self.log.append("savepoint_release")


class FakeItem:
    def __init__(self, log: Log) -> None:
        self.log = log
        self.work_id, self.attempt_id, self.project_uid = "cq_01", "cqa_01", "prj_01"
        self.kind, self.payload = "comparison_pair_check", {"ai_job_id": JOB}

    def require_current(self, session: Any) -> None:
        self.log.append("require_current")


class FakeRepository(ComparisonSpendRepository):
    """The statements of the journal and of the locks, each a line of the log."""

    def __init__(
        self, log: Log, *, rotation: int = 0, free: dict[str, bool] | None = None, job: Spend = Spend(0, 0),
        day: Spend = Spend(0, 0),
    ) -> None:
        self.log, self.rotation, self.free, self.job, self.day = log, rotation, free or {}, job, day
        self.connections = {"excr_A": "exc_A", "excr_B": "exc_B"}

    def open_calls_of_other_attempts(self, session: Any, **kw: Any) -> int:
        self.log.append("other_attempts")
        return 0

    def lock_group(self, session: Any, group_id: str) -> int | None:
        self.log.append(("lock_group", group_id))
        return self.rotation

    def lock_connection(self, session: Any, connection_id: str) -> None:
        self.log.append(("lock_connection", connection_id))

    def connection_of(self, session: Any, revision_id: str) -> str | None:
        return self.connections.get(revision_id)

    def connection_has_free_unit(self, session: Any, connection_id: str) -> bool:
        self.log.append(("free_unit?", connection_id))
        return self.free.get(connection_id, True)

    def lock_day(self, session: Any) -> None:
        self.log.append("lock_day")

    def job_spend(self, session: Any, **kw: Any) -> Spend:
        self.log.append("job_spend")
        return self.job

    def day_spend(self, session: Any) -> Spend:
        self.log.append("day_spend")
        return self.day

    def settle_abandoned(self, session: Any, **kw: Any) -> int:
        self.log.append("settle_abandoned")
        return 0

    def prepare(self, session: Any, **kw: Any) -> str:
        self.log.append(("prepare", kw))
        return "cmc_01"

    def mark_sent(self, session: Any, call_id: str) -> bool:
        self.log.append("mark_sent")
        return True

    def complete(self, session: Any, call_id: str, **kw: Any) -> bool:
        self.log.append(("complete", kw))
        return True

    def fail(self, session: Any, call_id: str, **kw: Any) -> bool:
        self.log.append(("fail", kw))
        return True

    def mark_unknown(self, session: Any, call_id: str, **kw: Any) -> bool:
        self.log.append(("unknown", kw))
        return True


class Adapter:
    def __init__(self, log: Log, *, error: BaseException | None = None) -> None:
        self.log, self.error, self.calls = log, error, 0

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.LIVE

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        self.log.append("adapter")
        if self.error is not None:
            raise self.error
        return ModelResponse(
            output_text="{}", stop_reason="end_turn", input_tokens=500_000, output_tokens=100_000, latency_ms=10,
            reported_cost_usd=None, model=GATEWAY,
        )


class FakeJobs:
    """The job's side: the row as it stands, the binding once, the wait with the seconds it has lasted."""

    def __init__(self, log: Log, record: AiJobRecord, *, waited: float = 0.0) -> None:
        self.log, self.record, self.waited = log, record, waited

    def get(self, session: Any, job_id: str, *, lock: bool = False) -> AiJobRecord | None:
        self.log.append("job_get")
        return self.record

    def bind(self, session: Any, job_id: str, *, connection_revision_id: str) -> bool:
        self.log.append(("bind", connection_revision_id))
        if self.record.binding_state != "pending":
            return False
        self.record = replace(self.record, binding_state="bound", connection_revision_id=connection_revision_id)
        return True

    def set_wait(self, session: Any, job_id: str, reason: str) -> float | None:
        self.log.append(("set_wait", reason))
        return self.waited


ESTIMATE_DOCUMENT = {
    "method": "pair_check", "estimate_digest": DIGEST, "input_tokens": 1_000_000, "output_tokens": 200_000,
    "route": {
        "pinned_model": MODEL, "billing": "metered", "provider_mode": "live", "executor_group_id": GROUP,
        "executor_group_revision_id": GROUP_REVISION, "routing_rule_revision_id": RULE_REVISION,
    },
}


def job_record(**over: Any) -> AiJobRecord:
    values: dict[str, Any] = {
        "job_id": JOB, "project_uid": "prj_01", "document_uid": "doc_01", "method": "pair_check", "state": "running",
        "pause_reason": None, "failure_reason": None, "matrix_id": "cmx_01", "series_id": None, "transition_id": None,
        "sheet_pair_id": None, "restart": False, "connection_revision_id": None, "pinned_model": MODEL,
        "provider_mode": "live", "estimate": ESTIMATE_DOCUMENT, "estimate_digest": DIGEST, "estimate_micros": 2 * USD,
        "ceiling_micros": 10 * USD, "consent_no": 1, "consented_by_user_uid": "usr_01", "consented_at": NOW,
        "command_id": "cmd_01", "created_at": NOW, "updated_at": NOW, "finished_at": None,
        "binding_state": "pending", "executor_group_revision_id": GROUP_REVISION,
        "routing_rule_revision_id": RULE_REVISION,
    }
    values.update(over)
    return AiJobRecord(**values)


def group_revision(*, billing: str = "metered", members: tuple[str, ...] = ("B", "A")) -> SimpleNamespace:
    """The members are listed B first: the locks must still be taken A first."""
    return SimpleNamespace(
        group_revision_id=GROUP_REVISION, group_id=GROUP, revision_no=1, pin_id=MODEL, gateway_model=GATEWAY,
        billing=billing, input_per_mtok_usd=Decimal("1.0"), output_per_mtok_usd=Decimal("5.0"), strategy="least_loaded",
        members=tuple(
            SimpleNamespace(connection_id=f"exc_{name}", connection_revision_id=f"excr_{name}", tie_break_order=None)
            for name in members
        ),
    )


def facts(name: str, *, used: int = 0, capacity: int = 1, **over: Any) -> MemberFacts:
    values: dict[str, Any] = {
        "connection_id": f"exc_{name}", "tie_break_order": None, "revision_is_snapshot": True, "archived": False,
        "served": True, "probed_ok": True, "runner_online": True, "capacity": capacity, "used": used,
    }
    values.update(over)
    return MemberFacts(**values)


def member_revision(name: str, **over: Any) -> SimpleNamespace:
    settings = {"pin_id": MODEL, "gateway_model": GATEWAY, "billing": "metered"}
    settings.update(over)
    return SimpleNamespace(revision_id=f"excr_{name}", connection_id=f"exc_{name}", settings=SimpleNamespace(**settings))


class World:
    """One scenario: the group, its members' facts, the job row, the log, and the caller over them."""

    def __init__(
        self, monkeypatch: pytest.MonkeyPatch, *, revision: SimpleNamespace | None = None,
        member_facts: list[MemberFacts] | None = None, job: AiJobRecord | None = None, rotation: int = 0,
        free: dict[str, bool] | None = None, waited: float = 0.0, day: Spend = Spend(0, 0), jobspend: Spend = Spend(0, 0),
        member_route_error: BaseException | None = None, adapter_error: BaseException | None = None,
        wait_seconds: int = 1800, member_pin: ModelPin = PIN, member_unmetered: bool | None = None,
    ) -> None:
        from auditmanager.executors import public
        from auditmanager.jobs import public as jobs_public

        self.log = Log()
        self.revision = revision or group_revision()
        self.facts = member_facts if member_facts is not None else [facts("A"), facts("B")]
        self.currents = {"exc_A": member_revision("A"), "exc_B": member_revision("B")}
        self.jobs = FakeJobs(self.log, job or job_record(), waited=waited)
        self.repository = FakeRepository(self.log, rotation=rotation, free=free, job=jobspend, day=day)
        self.adapters: list[Adapter] = []
        self.adapter_error, self.member_route_error, self.member_pin = adapter_error, member_route_error, member_pin
        self.member_unmetered = member_unmetered
        self.events: list[dict[str, Any]] = []
        monkeypatch.setattr(public, "group_revision_of", lambda session, revision_id, groups=None: self.revision)
        monkeypatch.setattr(public, "member_facts", lambda session, revision, repository=None: self.facts)
        monkeypatch.setattr(public, "current_revision", lambda session, connection_id, repository=None: self.currents.get(connection_id))
        monkeypatch.setattr(public, "advance_group_rotation", self._advance)
        monkeypatch.setattr(jobs_public, "append_execution_event", self._event)
        self.caller = ComparisonModelCaller(
            lambda: FakeSession(self.log), repository=self.repository, offline_wait_seconds=wait_seconds,  # type: ignore[arg-type]
        )

    def _advance(self, session: Any, group_id: str, groups: Any = None) -> int:
        self.log.append(("advance", group_id))
        return self.repository.rotation + 1

    def _event(self, session: Any, **kw: Any) -> None:
        self.log.append(("event", kw["event_type"]))
        self.events.append(kw)

    def member_route(self, session: Any, bound: AiJobRecord) -> CallRoute:
        self.log.append(("member_route", bound.connection_revision_id, bound.binding_state))
        if self.member_route_error is not None:
            raise self.member_route_error
        adapter = Adapter(self.log, error=self.adapter_error)
        self.adapters.append(adapter)
        return CallRoute(
            adapter=adapter, model_identity=MODEL, connection_revision_id=bound.connection_revision_id,
            expected_model=GATEWAY, pin=self.member_pin,
            unmetered=self.revision.billing == "not_metered" if self.member_unmetered is None else self.member_unmetered,
        )

    def route(self, record: AiJobRecord | None = None) -> CallRoute:
        return dispatch.pending_route(
            FakeSession(self.log), record or job_record(), member_route=self.member_route, jobs=self.jobs,  # type: ignore[arg-type]
        )

    def consent(self, **over: Any) -> Consent:
        values: dict[str, Any] = {
            "estimate_digest": DIGEST, "estimate_usd": 5.0, "ceiling_usd": 10.0, "connection_revision_id": None,
            "pinned_model": MODEL, "executor_group_revision_id": GROUP_REVISION,
        }
        values.update(over)
        return Consent(**values)

    def call(self, route: CallRoute | None = None, consent: Consent | None = None) -> Any:
        request = ModelRequest(model_id=MODEL, body={"model": MODEL, "messages": [{"role": "user", "content": "x"}]})
        return self.caller.call(
            FakeItem(self.log), route or self.route(), request, estimate=ESTIMATE, consent=consent or self.consent(),  # type: ignore[arg-type]
        )

    def prepared(self) -> dict[str, Any]:
        return self.log.entry("prepare")[1]



# --- the lock order, the binding and the commit before any model I/O (decision 14) -------------------------------------------


def test_the_first_call_takes_the_group_then_the_members_in_ascending_order_then_the_day(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    world.call()
    log = world.log
    group = log.first("lock_group")
    members = [i for i, entry in enumerate(log) if isinstance(entry, tuple) and entry[0] == "lock_connection"]
    assert [log[i][1] for i in members] == ["exc_A", "exc_B"], "ascending connection_id, whatever the revision lists first"
    assert group < members[0] < members[1] < log.first("lock_day") < log.first("prepare")


def test_the_binding_is_written_once_with_its_event_and_committed_before_the_model_is_called(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    world.call()
    log = world.log
    assert len(log.at("bind")) == 1 and log.entry("bind")[1] == "excr_A"
    assert world.events[0]["event_type"] == "executor.comparison_job_bound"
    assert world.events[0]["aggregate_id"] == JOB
    assert world.events[0]["payload"] == {
        "job_id": JOB, "connection_id": "exc_A", "revision_id": "excr_A", "work_kind": "comparison_pair_check",
        "from_state": "pending", "to_state": "bound",
    }
    assert world.prepared()["connection_revision_id"] == "excr_A", "the journal row names the member, not NULL"
    # the binding, its event and the journal row stand together in one savepoint, and the commit follows it
    assert (log.first("savepoint") < log.first("advance") < log.first("lock_day") < log.first("bind")
            < log.first("event") < log.first("prepare") < log.first("savepoint_release"))
    commit = next(i for i in log.at("commit") if i > log.first("savepoint_release"))
    assert commit < log.first("mark_sent") < log.first("adapter"), "model I/O starts only after the commit"
    assert world.adapters[0].calls == 1 and len(world.adapters) == 1


def test_the_member_route_is_opened_for_the_job_as_it_will_be_once_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    world.call()
    assert world.log.entry("member_route")[1:] == ("excr_A", "bound")
    # and it is opened before anything is written, so a route that cannot be opened leaves nothing behind
    assert world.log.first("member_route") < world.log.first("advance")


# --- the choice (decision 14): least loaded, the persisted rotation breaking a tie ---------------------------------------


def test_the_least_loaded_eligible_member_is_chosen(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, member_facts=[facts("A", used=1, capacity=2), facts("B", used=0, capacity=2)])
    world.call()
    assert world.prepared()["connection_revision_id"] == "excr_B"


@pytest.mark.parametrize(("rotation", "chosen"), [(0, "excr_A"), (1, "excr_B"), (2, "excr_A")])
def test_equal_members_take_turns_by_the_persisted_rotation(monkeypatch: pytest.MonkeyPatch, rotation: int, chosen: str) -> None:
    world = World(monkeypatch, rotation=rotation)
    world.call()
    assert world.prepared()["connection_revision_id"] == chosen
    assert world.log.entry("advance") == ("advance", GROUP), "the dispatch advances the rotation once"


@pytest.mark.parametrize("issue", [
    {"revision_is_snapshot": False}, {"archived": True}, {"served": False}, {"probed_ok": False}, {"runner_online": False},
])
def test_a_member_with_an_issue_is_never_chosen_even_when_it_is_the_lightest(monkeypatch: pytest.MonkeyPatch, issue: dict[str, bool]) -> None:
    world = World(monkeypatch, member_facts=[facts("A", used=0, capacity=4, **issue), facts("B", used=3, capacity=4)])
    world.call()
    assert world.prepared()["connection_revision_id"] == "excr_B"


def test_the_rotation_moves_only_with_a_dispatch_that_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    """The ceiling refuses after the member is chosen: the rotation's advance is in the savepoint that is rolled back."""
    world = World(monkeypatch, day=Spend(49 * USD + 500_000, 0))
    with pytest.raises(errors.CallRefused) as refused:
        world.call()
    assert refused.value.reason == errors.REASON_DAY_CEILING and refused.value.pauses_job is True
    log = world.log
    assert log.first("savepoint") < log.first("advance") < log.first("savepoint_rollback")
    assert not log.at("bind") and not log.at("event") and not log.at("prepare") and not log.at("adapter")


# --- the wait (decision 15) ------------------------------------------------------------------------------------------------


def test_no_member_with_a_free_unit_is_a_wait_for_capacity_and_calls_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, member_facts=[facts("A", used=1), facts("B", used=1)])
    with pytest.raises(errors.CallRefused) as refused:
        world.call()
    assert (refused.value.reason, refused.value.pauses_job) == (errors.REASON_CONNECTION_BUSY, False)
    assert world.log.entry("set_wait")[1] == "executor_at_capacity"
    assert world.log.first("set_wait") < world.log.first("commit"), "the wait is kept: it is committed on the way out"
    for written in ("advance", "bind", "event", "prepare", "adapter", "lock_day"):
        assert not world.log.at(written), written
    assert isinstance(refused.value.as_outcome(), errors.Yielded), "every handler answers a busy connection with a retry that spends no attempt"


def test_a_wait_for_capacity_has_no_end(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, member_facts=[facts("A", used=1), facts("B", used=1)], waited=10.0**9)
    with pytest.raises(errors.CallRefused) as refused:
        world.call()
    assert refused.value.reason == errors.REASON_CONNECTION_BUSY


def test_a_group_with_no_eligible_member_waits_as_runner_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    offline = {"runner_online": False}
    world = World(monkeypatch, member_facts=[facts("A", **offline), facts("B", **offline)], waited=5.0)
    with pytest.raises(errors.CallRefused) as refused:
        world.call()
    assert (refused.value.reason, refused.value.pauses_job) == (errors.REASON_CONNECTION_BUSY, False)
    assert world.log.entry("set_wait")[1] == "runner_offline"
    assert not world.log.at("prepare") and not world.log.at("adapter")


@pytest.mark.parametrize(("waited", "ends"), [(1799.9, False), (1800.0, False), (1800.1, True), (10.0**6, True)])
def test_the_offline_wait_ends_the_job_only_after_it_has_lasted_longer_than_the_wait(
    monkeypatch: pytest.MonkeyPatch, waited: float, ends: bool,
) -> None:
    offline = {"probed_ok": False}
    world = World(monkeypatch, member_facts=[facts("A", **offline), facts("B", **offline)], waited=waited)
    with pytest.raises(errors.CallRefused) as refused:
        world.call()
    if ends:
        assert (refused.value.reason, refused.value.pauses_job) == (errors.REASON_NO_EXECUTOR_ONLINE, True)
        assert refused.value.reason == "no_executor_online"
    else:
        assert (refused.value.reason, refused.value.pauses_job) == (errors.REASON_CONNECTION_BUSY, False)
    assert not world.log.at("adapter") and not world.log.at("bind")


def test_the_offline_wait_is_the_callers_to_set(monkeypatch: pytest.MonkeyPatch) -> None:
    offline = {"runner_online": False}
    world = World(monkeypatch, member_facts=[facts("A", **offline)], waited=61.0, wait_seconds=60)
    with pytest.raises(errors.CallRefused) as refused:
        world.call()
    assert refused.value.reason == errors.REASON_NO_EXECUTOR_ONLINE


# --- the consent, re-checked against the member (decisions 13 and 14) --------------------------------------------------------


@pytest.mark.parametrize("tamper", [
    {"estimate_micros": 3 * USD},                       # the figure the group's rates price the stored estimate at is 2.00
    {"ceiling_micros": 11 * USD},                       # above the hard USD 10
    {"ceiling_micros": 0},                              # a metered job with no ceiling
    {"pinned_model": "claude-sonnet-5"},                # the model consented to is not the group's
    {"executor_group_revision_id": "exgr_other"},       # not the group revision this route was opened for
])
def test_a_consent_that_does_not_hold_calls_nothing_and_records_that_a_new_one_is_needed(
    monkeypatch: pytest.MonkeyPatch, tamper: dict[str, Any],
) -> None:
    world = World(monkeypatch, job=job_record(**tamper))
    with pytest.raises(errors.CallRefused) as refused:
        world.call(route=world.route(job_record()))
    assert (refused.value.reason, refused.value.pauses_job) == (errors.REASON_CONSENT_STALE, True)
    for written in ("advance", "bind", "event", "prepare", "mark_sent", "adapter", "lock_day"):
        assert not world.log.at(written), written
    if "executor_group_revision_id" not in tamper:
        assert world.log.entry("set_wait")[1] == "needs_reconsent"


def test_the_member_must_still_be_the_snapshot_and_serve_the_consented_model_and_billing(monkeypatch: pytest.MonkeyPatch) -> None:
    for wrong in ({"pin_id": "claude-sonnet-5"}, {"gateway_model": "other"}, {"billing": "not_metered"}):
        world = World(monkeypatch, member_facts=[facts("A")])
        world.currents["exc_A"] = member_revision("A", **wrong)
        with pytest.raises(errors.CallRefused) as refused:
            world.call()
        assert refused.value.reason == errors.REASON_CONSENT_STALE, wrong
        assert not world.log.at("bind") and not world.log.at("adapter")
    gone = World(monkeypatch, member_facts=[facts("A")])
    gone.currents["exc_A"] = member_revision("A_changed")  # a revision other than the one the group snapshotted
    with pytest.raises(errors.CallRefused):
        gone.call()


def test_a_consent_of_another_group_revision_is_refused_before_the_database(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    with pytest.raises(errors.CallRefused) as refused:
        world.call(consent=world.consent(executor_group_revision_id="exgr_other"))
    assert refused.value.reason == errors.REASON_CONSENT_STALE
    assert list(world.log) == [], "refused before the database: not even a session was opened"


def test_a_consent_with_no_connection_is_not_a_consent_for_a_route_with_no_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    bare = CallRoute(adapter=Adapter(world.log), model_identity=MODEL, expected_model=GATEWAY, pin=PIN)
    with pytest.raises(errors.CallRefused) as refused:
        world.call(route=bare)
    assert refused.value.reason == errors.REASON_CONSENT_STALE and not world.log.at("prepare")


# --- one price: the rates the consent was given on are the rates the member is priced at (`EXEC2-FOLLOWUP-01` item 1) ---------


def refuse_stale(world: "World", **call: Any) -> errors.CallRefused:
    with pytest.raises(errors.CallRefused) as refused:
        world.call(**call)
    assert (refused.value.reason, refused.value.pauses_job) == (errors.REASON_CONSENT_STALE, True)
    for written in ("advance", "bind", "event", "prepare", "mark_sent", "adapter", "lock_day"):
        assert not world.log.at(written), written
    return refused.value


@pytest.mark.parametrize("moved", [
    ModelPin(model_id=MODEL, input_per_mtok_usd=2.0, output_per_mtok_usd=5.0),    # only the input rate moved
    ModelPin(model_id=MODEL, input_per_mtok_usd=1.0, output_per_mtok_usd=10.0),   # only the output rate moved
    ModelPin(model_id=MODEL, input_per_mtok_usd=0.5, output_per_mtok_usd=2.5),    # the lock got cheaper: still not what was consented to
])
def test_a_provider_lock_that_moved_since_the_group_revision_was_made_refuses_the_first_call_and_reprices_nothing(
    monkeypatch: pytest.MonkeyPatch, provider_lock: list[ModelPin], moved: ModelPin,
) -> None:
    """The group revision holds the rates the consent was given on; the member's route is priced at the lock. Without the rule the call
    went on over the lock's rates while the ceilings and the journal's estimate were the snapshot's: two prices for one call."""
    provider_lock[:] = [moved]
    world = World(monkeypatch)
    route = world.route()
    assert (route.pin.input_per_mtok_usd, route.pin.output_per_mtok_usd) == (1.0, 5.0), "the estimate is still the consented one"
    refuse_stale(world, route=route)
    assert world.log.entry("set_wait")[1] == "needs_reconsent", "the job asks for a new consent, visibly"
    assert world.log.first("set_wait") < world.log.first("commit"), "and the wait is kept"


def test_the_rates_rule_is_read_at_the_member_the_call_is_bound_to_not_at_the_route_in_hand(
    monkeypatch: pytest.MonkeyPatch, provider_lock: list[ModelPin],
) -> None:
    """The route (opened while the lock was as consented) still carries the snapshot; the lock moves before the call is dispatched."""
    world = World(monkeypatch)
    route = world.route()
    provider_lock[:] = [ModelPin(model_id=MODEL, input_per_mtok_usd=1.0, output_per_mtok_usd=5.5)]
    refuse_stale(world, route=route)


def test_a_group_revision_whose_snapshot_is_not_the_lock_cannot_be_dispatched_even_though_its_route_can_be_opened(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = group_revision()
    revision.input_per_mtok_usd, revision.output_per_mtok_usd = Decimal("7.5"), Decimal("30.0")
    # a job consented on that snapshot: 100 000 + 20 000 tokens are USD 1.35 at 7.5 / 30, so the stored figure is consistent with it and
    # the estimate check alone would let the call through -- only the comparison with the lock refuses it
    record = job_record(estimate={**ESTIMATE_DOCUMENT, "input_tokens": 100_000, "output_tokens": 20_000}, estimate_micros=1_350_000)
    world = World(monkeypatch, revision=revision, job=record)
    assert world.route(record).pin.input_per_mtok_usd == 7.5, "the pending route follows the snapshot"
    assert _problem(record, revision) == "rates"
    refuse_stale(world, route=world.route(record))


def test_the_rates_rule_holds_for_a_not_metered_group_as_it_does_for_a_run(
    monkeypatch: pytest.MonkeyPatch, provider_lock: list[ModelPin],
) -> None:
    """A Run's dispatch compares the rate digest whatever the billing; this side does the same, so the two cannot disagree."""
    provider_lock[:] = [ModelPin(model_id=MODEL, input_per_mtok_usd=2.0, output_per_mtok_usd=5.0)]
    world = World(monkeypatch, revision=group_revision(billing="not_metered"))
    for name in ("A", "B"):
        world.currents[f"exc_{name}"] = member_revision(name, billing="not_metered")
    world.jobs.record = job_record(
        estimate_micros=0, ceiling_micros=0,
        estimate={**ESTIMATE_DOCUMENT, "route": {**ESTIMATE_DOCUMENT["route"], "billing": "not_metered"}},
    )
    refuse_stale(world, consent=world.consent(estimate_usd=0.0))


def test_a_lock_that_does_not_pin_the_model_any_more_is_a_consent_that_does_not_hold(
    monkeypatch: pytest.MonkeyPatch, provider_lock: list[ModelPin],
) -> None:
    world = World(monkeypatch)
    route = world.route()
    provider_lock[:] = [ModelPin(model_id="claude-sonnet-5", input_per_mtok_usd=1.0, output_per_mtok_usd=5.0)]
    assert _problem() == "rates"
    refuse_stale(world, route=route)


def assert_needs_reconsent_recorded(world: "World") -> None:
    """The consent that does not hold is recorded where the first call's own re-check records it, and kept (committed) on the way out."""
    assert world.log.entry("set_wait")[1] == "needs_reconsent"
    assert world.log.first("set_wait") < world.log.first("commit")


def test_the_member_route_must_carry_the_rates_of_the_route_the_estimate_was_priced_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """The second guard, at the one place the two prices could part: the lock is as consented, but the binder opens the member's route
    over another pin. The call settles at the member's pin, so it is refused before anything is written -- and the job is told it needs
    a new consent, as the first call's own re-check tells it (L5: this path used to refuse without recording the wait)."""
    other = ModelPin(model_id=MODEL, input_per_mtok_usd=1.0, output_per_mtok_usd=7.0)
    world = World(monkeypatch, member_pin=other)
    refuse_stale(world)
    assert world.log.at("member_route") and not world.log.at("savepoint"), "refused after the member's route was opened, before anything is written"
    assert_needs_reconsent_recorded(world)


def test_a_member_route_that_is_not_metered_when_the_consent_was_refuses_the_same_way_and_records_the_same_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = World(monkeypatch, member_unmetered=True)
    refuse_stale(world)
    assert_needs_reconsent_recorded(world)


# --- the calls AFTER binding: the same rates rule at every call, as a Run's call-time guard (`EXEC2-FOLLOWUP-01`, M2) ---------------


def bound_call(world: "World", *, consent: Consent | None = None, route: CallRoute | None = None) -> Any:
    """A later call of a job that is already bound to member A: a route with no dispatch, opened from the lock as it is now."""
    over = route or CallRoute(
        adapter=Adapter(world.log), model_identity=MODEL, connection_revision_id="excr_A", expected_model=GATEWAY, pin=PIN,
    )
    return world.call(route=over, consent=consent or world.consent(connection_revision_id="excr_A"))


def test_a_later_call_of_a_bound_job_is_priced_at_the_rates_its_consent_was_given_on(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, job=job_record(binding_state="bound", connection_revision_id="excr_A"))
    result = bound_call(world)
    assert result.cost_basis == "estimated" and world.log.at("prepare") and world.log.at("adapter")


@pytest.mark.parametrize("moved", [
    ModelPin(model_id=MODEL, input_per_mtok_usd=2.0, output_per_mtok_usd=5.0),
    ModelPin(model_id=MODEL, input_per_mtok_usd=0.5, output_per_mtok_usd=5.0),
])
def test_a_later_call_of_a_bound_job_over_a_route_priced_at_other_rates_is_refused_consent_stale(
    monkeypatch: pytest.MonkeyPatch, moved: ModelPin,
) -> None:
    """The route of a bound job is opened from the lock of the moment, so the lock moving after binding changes the price the call settles at
    while the consent stands on the snapshot. Without this check every later call went on at the new price."""
    world = World(monkeypatch, job=job_record(binding_state="bound", connection_revision_id="excr_A"))
    route = CallRoute(adapter=Adapter(world.log), model_identity=MODEL, connection_revision_id="excr_A", expected_model=GATEWAY, pin=moved)
    with pytest.raises(errors.CallRefused) as refused:
        bound_call(world, route=route)
    assert (refused.value.reason, refused.value.pauses_job) == (errors.REASON_CONSENT_STALE, True)
    for written in ("prepare", "mark_sent", "adapter", "lock_day", "lock_connection"):
        assert not world.log.at(written), written
    assert not world.log.at("set_wait"), "a bound job holds no wait: the database allows one only while the job is pending"


def test_a_group_revision_that_cannot_be_read_is_not_a_consent_that_holds_for_a_bound_job(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.executors import public

    world = World(monkeypatch, job=job_record(binding_state="bound", connection_revision_id="excr_A"))
    monkeypatch.setattr(public, "group_revision_of", lambda session, revision_id, groups=None: None)
    with pytest.raises(errors.CallRefused) as refused:
        bound_call(world)
    assert refused.value.reason == errors.REASON_CONSENT_STALE and not world.log.at("adapter")


def test_the_check_is_skipped_for_a_job_of_a_connection_a_recorded_replay_and_a_route_that_costs_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A consent with no group (every job made before the cut-over) has no snapshot to hold; its call is not asked about one."""
    world = World(monkeypatch)
    from auditmanager.executors import public

    monkeypatch.setattr(public, "group_revision_of", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no group is read")))
    legacy = Consent(estimate_digest=DIGEST, estimate_usd=5.0, ceiling_usd=10.0, connection_revision_id="excr_A", pinned_model=MODEL)
    assert bound_call(world, consent=legacy).cost_basis == "estimated"


def test_the_estimate_the_ceilings_see_and_the_cost_the_call_settles_at_are_one_price(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    result = world.call()
    estimated = int(round(PIN.cost_usd(input_tokens=ESTIMATE.input_tokens, output_tokens=ESTIMATE.output_tokens) * USD))
    settled = int(round(PIN.cost_usd(input_tokens=500_000, output_tokens=100_000) * USD))
    assert world.prepared()["estimate_micros"] == estimated == 2 * USD
    assert (result.cost_basis, result.cost_micros) == ("estimated", settled) and settled == 1 * USD
    # the day and job ceilings were decided on that same estimate
    assert world.log.first("lock_day") < world.log.first("prepare")


# --- the ceilings, against the selected member (decision 14) and `not_metered` shown as such ---------------------------------


def test_the_job_ceiling_is_applied_before_the_binding_is_written(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, jobspend=Spend(8 * USD + 500_000, 0))
    with pytest.raises(errors.CallRefused) as refused:
        world.call(consent=world.consent(estimate_usd=9.0))
    assert refused.value.reason == errors.REASON_JOB_CEILING and refused.value.pauses_job is True
    assert not world.log.at("bind") and not world.log.at("prepare") and not world.log.at("adapter")


def test_a_not_metered_group_binds_without_a_money_check_and_the_call_is_journalled_unmetered(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, revision=group_revision(billing="not_metered"), day=Spend(50 * USD, 0))
    for name in ("A", "B"):
        world.currents[f"exc_{name}"] = member_revision(name, billing="not_metered")
    world.jobs.record = job_record(
        estimate_micros=0, ceiling_micros=0,
        estimate={**ESTIMATE_DOCUMENT, "route": {**ESTIMATE_DOCUMENT["route"], "billing": "not_metered"}},
    )
    result = world.call(consent=world.consent(estimate_usd=0.0))
    assert not world.log.at("lock_day") and not world.log.at("job_spend"), "nothing is limited by money"
    assert world.prepared()["estimate_micros"] == 0, "an estimate of zero, journalled as such, never a per-call price"
    assert len(world.log.at("bind")) == 1
    assert result.cost_basis == "unmetered" and result.cost_micros == 0
    assert result.pause is None


# --- no re-routing (decision 16) -----------------------------------------------------------------------------------------------


def test_a_job_that_is_already_bound_stays_on_its_member_and_chooses_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Another item bound the job after this route was opened: the route still says ``pending``, the row says ``bound``."""
    bound = job_record(binding_state="bound", connection_revision_id="excr_B")
    world = World(monkeypatch, job=bound, member_facts=[facts("A", used=0, capacity=4), facts("B", used=3, capacity=4)])
    world.call(route=world.route(job_record()), consent=world.consent(connection_revision_id="excr_B"))
    assert world.prepared()["connection_revision_id"] == "excr_B", "the lighter member A is not asked"
    for written in ("advance", "bind", "event"):
        assert not world.log.at(written), written
    assert world.log.entry("member_route")[1:] == ("excr_B", "bound")


def test_a_bound_job_whose_member_is_busy_waits_for_it_and_is_never_sent_to_another(monkeypatch: pytest.MonkeyPatch) -> None:
    bound = job_record(binding_state="bound", connection_revision_id="excr_B")
    world = World(monkeypatch, job=bound, free={"exc_B": False, "exc_A": True})
    with pytest.raises(errors.CallRefused) as refused:
        world.call(route=world.route(job_record()))
    assert (refused.value.reason, refused.value.pauses_job) == (errors.REASON_CONNECTION_BUSY, False)
    assert not world.log.at("prepare") and not world.log.at("adapter") and not world.log.at("bind")
    assert ("free_unit?", "exc_A") not in world.log, "the other member is not even looked at"


def test_an_unknown_outcome_is_not_repeated_and_the_next_call_of_the_job_goes_to_the_same_member(monkeypatch: pytest.MonkeyPatch) -> None:
    """``spend_unknown`` is never sent to another member: the first call binds A and ends unknown; the job's next call is A's again,
    although B is lighter and free."""
    world = World(monkeypatch, adapter_error=RuntimeError("the connection dropped"))
    with pytest.raises(errors.OutcomeUnknown):
        world.call()
    assert world.adapters[0].calls == 1 and world.log.entry("bind")[1] == "excr_A"
    assert world.jobs.record.binding_state == "bound" and world.jobs.record.connection_revision_id == "excr_A"
    world.facts = [facts("A", used=1, capacity=2), facts("B", used=0, capacity=2)]
    world.adapter_error = None
    world.call(route=world.route(job_record()))
    assert [e[1]["connection_revision_id"] for e in world.log if isinstance(e, tuple) and e[0] == "prepare"] == ["excr_A", "excr_A"]
    assert len(world.log.at("bind")) == 1 and len(world.log.at("advance")) == 1


def test_two_items_of_one_job_bind_it_once(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    first_route, second_route = world.route(), world.route()  # both opened while the job was pending
    world.call(route=first_route)
    world.call(route=second_route, consent=world.consent(connection_revision_id="excr_A"))
    assert len(world.log.at("bind")) == 1 and len(world.log.at("event")) == 1
    assert [e[1]["connection_revision_id"] for e in world.log if isinstance(e, tuple) and e[0] == "prepare"] == ["excr_A", "excr_A"]


# --- a member that cannot be opened ----------------------------------------------------------------------------------------------


def test_a_member_whose_route_cannot_be_opened_refuses_and_writes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, member_route_error=DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="secret_unreadable"))
    with pytest.raises(errors.CallRefused) as refused:
        world.call()
    assert (refused.value.reason, refused.value.pauses_job) == (errors.REASON_EXECUTOR_ROUTE_MISSING, False)
    for written in ("advance", "bind", "event", "prepare", "adapter"):
        assert not world.log.at(written), written


def test_a_job_that_the_database_does_not_hold_as_admitted_by_this_group_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    for record in (job_record(binding_state="frozen_at_start", executor_group_revision_id=None, connection_revision_id="excr_A"),
                   job_record(executor_group_revision_id="exgr_other")):
        world = World(monkeypatch, job=record)
        with pytest.raises(errors.CallRefused) as refused:
            world.call()
        assert refused.value.reason == errors.REASON_CONSENT_STALE
        assert not world.log.at("bind") and not world.log.at("prepare")


# --- the route of a pending job ---------------------------------------------------------------------------------------------------


def test_the_pending_route_follows_the_group_revision_not_a_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    route = world.route()
    assert route.connection_revision_id is None and route.dispatch is not None
    assert (route.model_identity, route.expected_model, route.unmetered) == (MODEL, GATEWAY, False)
    assert route.executor_group_revision_id == GROUP_REVISION
    assert (route.pin.input_per_mtok_usd, route.pin.output_per_mtok_usd) == (1.0, 5.0), "the rate snapshot of the group revision"
    assert (route.dispatch.job_id, route.dispatch.group_id, route.dispatch.work_kind) == (JOB, GROUP, "comparison_pair_check")
    assert route.dispatch.rule_revision_id == RULE_REVISION
    assert route.adapter.provider_mode == "live"
    with pytest.raises(RuntimeError):
        route.adapter.complete(object())  # the placeholder refuses: only a member's adapter is called
    assert not_metered_route(monkeypatch).unmetered is True


def not_metered_route(monkeypatch: pytest.MonkeyPatch) -> CallRoute:
    return World(monkeypatch, revision=group_revision(billing="not_metered")).route()


def test_the_rates_of_the_pending_route_are_the_revisions_snapshot_and_not_the_lock_of_today(monkeypatch: pytest.MonkeyPatch) -> None:
    revision = group_revision()
    revision.input_per_mtok_usd, revision.output_per_mtok_usd = Decimal("7.5"), Decimal("30.0")
    route = World(monkeypatch, revision=revision).route()
    assert (route.pin.model_id, route.pin.input_per_mtok_usd, route.pin.output_per_mtok_usd) == (MODEL, 7.5, 30.0)


def test_a_pending_route_for_a_job_with_no_group_revision_or_an_unpinned_model_is_executor_route_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(DomainError) as no_group:
        World(monkeypatch).route(job_record(executor_group_revision_id=None))
    assert no_group.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE and no_group.value.detail_fields["dependency"] == "executor_route_missing"
    revision = group_revision()
    revision.pin_id = "not-a-pinned-model"
    with pytest.raises(DomainError) as unpinned:
        World(monkeypatch, revision=revision).route()
    assert unpinned.value.detail_fields["dependency"] == "executor_route_missing"


class Inner:
    """The composition root's route source, as the handlers know it."""

    def __init__(self) -> None:
        self.seen: list[AiJobRecord] = []

    def route(self, session: Any, job: AiJobRecord) -> str:
        self.seen.append(job)
        return f"route-of-{job.binding_state}"

    route_for = route


def test_group_routes_open_a_pending_live_job_with_its_dispatch_and_every_other_job_with_the_inner_source(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch)
    inner = Inner()
    routes = dispatch.GroupRoutes(inner, jobs=world.jobs)
    session = FakeSession(world.log)
    assert routes.route(session, job_record(binding_state="frozen_at_start", executor_group_revision_id=None, routing_rule_revision_id=None,
                                            connection_revision_id="excr_A")) == "route-of-frozen_at_start"
    assert routes.route_for(session, job_record(binding_state="bound", connection_revision_id="excr_A")) == "route-of-bound"
    assert routes.route(session, job_record(provider_mode="recorded")) == "route-of-pending", "a replay binds nothing and spends nothing"
    assert len(inner.seen) == 3
    opened = routes.route(session, job_record())
    assert isinstance(opened, CallRoute) and opened.dispatch is not None and len(inner.seen) == 3
    assert opened.dispatch.member_route(session, "excr_B") == "route-of-bound"
    assert (inner.seen[-1].binding_state, inner.seen[-1].connection_revision_id) == ("bound", "excr_B")


def test_group_aware_leaves_no_route_source_without_one_and_wraps_once() -> None:
    jobs = object()
    assert dispatch.group_aware(None, jobs=jobs) is None  # type: ignore[arg-type]
    wrapped = dispatch.group_aware(Inner(), jobs=jobs)  # type: ignore[arg-type]
    assert isinstance(wrapped, dispatch.GroupRoutes) and dispatch.group_aware(wrapped, jobs=jobs) is wrapped  # type: ignore[arg-type]


def test_the_registry_hands_every_factory_the_wrapped_route_source() -> None:
    from auditmanager.comparison.work.model import WorkDependencies
    from auditmanager.comparison.work.registry import HandlerRegistry

    seen: list[Any] = []

    class Handler:
        kind = "page_profile"

        def run(self, item: Any) -> Any: ...

    def factory(dependencies: Any) -> Handler:
        seen.append(dependencies.routes)
        return Handler()

    inner = Inner()
    HandlerRegistry.build([factory], WorkDependencies(None, None, None, None, routes=inner))  # type: ignore[arg-type]
    assert isinstance(seen[0], dispatch.GroupRoutes) and seen[0]._inner is inner
    seen.clear()
    HandlerRegistry.build([factory], WorkDependencies(None, None, None, None))  # type: ignore[arg-type]
    assert seen == [None], "a bundle with no route source stays without one"


# --- the consent envelope, as a pure check -----------------------------------------------------------------------------------------


_ABSENT: Any = object()


def _problem(job: AiJobRecord | None = None, revision: SimpleNamespace | None = None, member: Any = _ABSENT,
             snapshot: str = "excr_A") -> str | None:
    return dispatch.consent_problem(
        job or job_record(), revision or group_revision(), member_revision("A") if member is _ABSENT else member, snapshot,
    )


def test_a_consent_that_holds_has_no_problem() -> None:
    assert _problem() is None


def test_the_rates_the_consent_was_given_on_are_read_against_the_lock_of_the_members_pin(provider_lock: list[ModelPin]) -> None:
    assert _problem() is None
    provider_lock[:] = [ModelPin(model_id=MODEL, input_per_mtok_usd=1.0, output_per_mtok_usd=5.000001)]
    assert _problem() == "rates", "a rate that differs in the sixth decimal is another rate: the digest is over the exact figures"
    provider_lock[:] = [PIN]
    revision = group_revision()
    revision.output_per_mtok_usd = Decimal("5.5")
    assert _problem(revision=revision) == "rates"


def test_the_wait_a_sweep_derives_is_the_run_sides_and_the_first_calls() -> None:
    """``None`` when some member has no issue; at capacity when none has but some is only full; offline otherwise -- the same function of
    the same issues as ``jobs.repository._group_wait_reason``, over every combination of three issues."""
    import itertools

    from auditmanager.jobs.repository import _group_wait_reason

    issues = (None, "at_capacity", "runner_offline", "probe_not_ok")
    for size in (1, 2, 3):
        for combination in itertools.product(issues, repeat=size):
            assert dispatch.group_wait_reason(combination) == _group_wait_reason(combination), combination
    assert dispatch.group_wait_reason(["runner_offline", "revision_changed"]) == "runner_offline"
    assert dispatch.group_wait_reason(["at_capacity", "archived"]) == "executor_at_capacity"
    assert dispatch.group_wait_reason([None, "runner_offline"]) is None


def test_the_rates_a_group_holds_are_the_locks_or_they_are_not(provider_lock: list[ModelPin]) -> None:
    assert dispatch.group_rates_hold(group_revision()) is True
    provider_lock[:] = [ModelPin(model_id=MODEL, input_per_mtok_usd=1.0, output_per_mtok_usd=5.5)]
    assert dispatch.group_rates_hold(group_revision()) is False
    provider_lock[:] = []
    assert dispatch.group_rates_hold(group_revision()) is False, "a model the lock no longer pins holds no rates"
    assert dispatch.snapshot_pin(group_revision()) is None


def test_an_unrelated_lock_entry_does_not_decide_the_rates(provider_lock: list[ModelPin]) -> None:
    provider_lock[:] = [ModelPin(model_id="claude-sonnet-5", input_per_mtok_usd=9.0, output_per_mtok_usd=9.0), PIN]
    assert _problem() is None


@pytest.mark.parametrize(("what", "problem"), [
    ({"executor_group_revision_id": "exgr_other"}, "group_revision"),
    ({"estimate": {**ESTIMATE_DOCUMENT, "route": {**ESTIMATE_DOCUMENT["route"], "executor_group_revision_id": "exgr_other"}}},
     "estimate_group_revision"),
    ({"pinned_model": "claude-sonnet-5"}, "pinned_model"),
    ({"estimate": {**ESTIMATE_DOCUMENT, "route": {**ESTIMATE_DOCUMENT["route"], "billing": "not_metered"}}}, "billing"),
    ({"estimate_micros": 2 * USD + 1}, "estimate"),
    ({"estimate": {k: v for k, v in ESTIMATE_DOCUMENT.items() if k != "input_tokens"}}, "estimate"),
    ({"ceiling_micros": 10 * USD + 1}, "ceiling"),
])
def test_each_part_of_the_envelope_is_read_again(what: dict[str, Any], problem: str) -> None:
    assert _problem(job_record(**what)) == problem


def test_the_member_is_read_again_too() -> None:
    assert _problem(member=None) == "member_revision"
    assert _problem(member=member_revision("A"), snapshot="excr_other") == "member_revision"
    assert _problem(member=member_revision("A", billing="not_metered")) == "member_settings"
    assert _problem(member=member_revision("A", gateway_model="x")) == "member_settings"


def test_a_not_metered_group_has_no_price_to_hold() -> None:
    revision = group_revision(billing="not_metered")
    document = {**ESTIMATE_DOCUMENT, "route": {**ESTIMATE_DOCUMENT["route"], "billing": "not_metered"}}
    member = member_revision("A", billing="not_metered")
    assert _problem(job_record(estimate=document, estimate_micros=0, ceiling_micros=0), revision, member) is None
    assert _problem(job_record(estimate=document, estimate_micros=1, ceiling_micros=0), revision, member) == "estimate"


# --- the setting and the words that must equal other contexts' ---------------------------------------------------------------------


def test_the_offline_wait_is_thirty_minutes_unless_the_environment_says_otherwise() -> None:
    assert dispatch.group_offline_wait_seconds({}) == 1800 == dispatch.DEFAULT_GROUP_OFFLINE_WAIT_SECONDS
    assert dispatch.group_offline_wait_seconds({dispatch.GROUP_OFFLINE_WAIT_ENV: " 90 "}) == 90
    assert dispatch.group_offline_wait_seconds({dispatch.GROUP_OFFLINE_WAIT_ENV: str(dispatch.MAX_GROUP_OFFLINE_WAIT_SECONDS)}) == 7 * 24 * 3600
    assert dispatch.GROUP_OFFLINE_WAIT_ENV == "AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS"


@pytest.mark.parametrize("bad", ["", "  ", "0", "-1", "+5", "30m", "1.5", "1e3", "abc", "604801", "٣٠"])
def test_a_wait_that_is_not_a_whole_number_of_seconds_is_refused_not_defaulted(bad: str) -> None:
    with pytest.raises(ValueError):
        dispatch.group_offline_wait_seconds({dispatch.GROUP_OFFLINE_WAIT_ENV: bad})


def test_the_words_this_context_restates_are_the_executors() -> None:
    from auditmanager.comparison.ai_jobs import estimate, model
    from auditmanager.executors import group_selection
    from auditmanager.executors import model as executors

    assert model.WAIT_REASONS == executors.WAIT_REASONS
    assert dispatch._AT_CAPACITY == group_selection.ISSUE_AT_CAPACITY == executors.GROUP_MEMBER_ISSUES[-1]
    assert estimate.DEPENDENCY_NO_RULE_FOR_WORK_KIND == executors.DEPENDENCY_NO_RULE_FOR_WORK_KIND
    assert estimate.ROUTING_MODE_RULES == executors.ROUTING_MODE_RULES
    assert (model.BINDING_FROZEN, model.BINDING_PENDING, model.BINDING_BOUND) == ("frozen_at_start", "pending", "bound")


def test_a_comparison_work_kind_is_comparison_and_the_method() -> None:
    for method in METHODS:
        assert f"comparison_{method}" == work_kind_of(method)


def test_the_binding_event_is_executor_prefixed_and_its_payload_keys_are_allowlisted() -> None:
    from auditmanager.jobs import events

    assert dispatch.EVENT_JOB_BOUND.startswith("executor.")
    assert {"job_id", "connection_id", "revision_id", "work_kind", "from_state", "to_state"} <= events._SAFE_KEYS  # type: ignore[attr-defined]


def test_the_group_lock_is_the_row_lock_and_the_cursor_the_executors_take_and_advance() -> None:
    """Restated from a context this one may not import: the statement names the table, the column and the lock the executors' own
    group commands, a Run's claim and the rotation use, so the two cannot drift apart unseen."""
    import inspect

    from auditmanager.comparison.spend import repository
    from auditmanager.executors.group_repository import GroupRepository

    ours = str(repository._LOCK_GROUP)  # type: ignore[attr-defined]
    assert "FROM executor_group WHERE group_id = :group_id FOR UPDATE" in ours and "rotation_cursor" in ours
    theirs = inspect.getsource(GroupRepository.get_group) + inspect.getsource(GroupRepository.advance_rotation)
    assert "FROM executor_group WHERE group_id = :id" in theirs and "FOR UPDATE" in theirs
    assert "UPDATE executor_group SET rotation_cursor = rotation_cursor + 1" in theirs
