"""`EXEC2-GROUP-RUN-01` (ADR-0026 decisions 14 to 16): the dispatch of a pending Run, without a database.

The claim of a Run admitted on a group chooses its member under the locks of decision 14. What is decided is separable from
the rows: the order the locks are asked in, which members are eligible, which one ``choose`` picks, what the Run is told when
none can take it, what is written when one can. Here the group, its members and their facts are values, the consent is a
function, and the session is a recorder of the statements it was handed, so the **order of the locks is read off the
statements themselves**. B3 section 11 numbers are the task file's reading (the integrator re-maps them):

* **4 -- the binding is written once, by the claim,** with one ``executor.``-prefixed event whose payload keys are the
  journal's allowlist (``test_the_dispatch_...``), and the rotation moves on only with it;
* **5 -- least loaded, ties by the persisted rotation** (``test_the_member_with_the_lowest_ratio...``);
* **6, 7 -- a Run that no member can take waits and says why:** capacity (unbounded), runner offline, and nothing is
  written by the refusal;
* **9, 10 -- a member whose current revision is no longer the group's snapshot, or that is archived, unserved or not probed
  is never chosen** and never adopted;
* **12 -- a consent that no longer holds binds nothing and reads no member** (``needs_reconsent``);
* the hint's SQL keeps the old shape for every other Run and offers a pending one only while nothing holds it back (no stored
  wait reason: a Run the claim refused is offered **once**) and only for a free member, and never to a process that does not
  dispatch groups; the sweep walks every pending Run, clears a reason only for a member that is eligible *and* free, decides the
  offline expiry on the locked row and ends a Run whose consent no longer holds.

``tests/integration/jobs/test_group_dispatch.py`` runs the same rules on PostgreSQL, including the two-process race. Written
and **not run** in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

import auditmanager.executors.public as executors_public
import auditmanager.runs.public as runs_public
from auditmanager.executors.group_selection import MemberFacts
from auditmanager.executors.groups import GroupMemberRecord, GroupRevisionRecord
from auditmanager.jobs import repository as jobs
from auditmanager.jobs.events import _SAFE_KEYS
from auditmanager.jobs.repository import (
    DEFAULT_GROUP_OFFLINE_WAIT_SECONDS,
    GROUP_OFFLINE_WAIT_ENV,
    ExecutionNotClaimed,
    GroupDispatchWaiting,
    JobRepository,
)
from auditmanager.shared.errors import DomainError, ErrorCode

RUN = "run_01M2545JSD15ETSNNV904X991K"
GROUP = "exg_01M2545JSD15ETSNNV904X991G"
GROUP_REVISION = "exgr_01M2545JSD15ETSNNV904X991R"
A, B, C = (f"exc_01M2545JSD15ETSNNV904X99{letter}N" for letter in "123")
REVISION = {A: "excr_01M2545JSD15ETSNNV904X991A", B: "excr_01M2545JSD15ETSNNV904X992A",
            C: "excr_01M2545JSD15ETSNNV904X993A"}


def _revision(*connections: str, billing: str = "not_metered") -> GroupRevisionRecord:
    return GroupRevisionRecord(
        group_revision_id=GROUP_REVISION, group_id=GROUP, revision_no=1, pin_id="claude-sonnet-5",
        gateway_model="claude-sonnet-5", billing=billing, input_per_mtok_usd=Decimal("3"),
        output_per_mtok_usd=Decimal("15"), strategy="least_loaded",
        created_at=datetime(2026, 11, 3, tzinfo=timezone.utc), created_by="usr_" + "0" * 26,
        members=tuple(GroupMemberRecord(connection_id=c, connection_revision_id=REVISION[c]) for c in connections),
    )


def _facts(connection: str, *, used: int = 0, capacity: int = 1, snapshot: bool = True, archived: bool = False,
           served: bool = True, probed: bool = True, online: bool = True) -> MemberFacts:
    return MemberFacts(
        connection_id=connection, tie_break_order=None, revision_is_snapshot=snapshot, archived=archived,
        served=served, probed_ok=probed, runner_online=online, capacity=capacity, used=used,
    )


class _Result:
    def __init__(self, value: Any = None, rowcount: int = 1) -> None:
        self._value, self.rowcount = value, rowcount

    def scalar_one_or_none(self) -> Any:
        return self._value

    def first(self) -> Any:
        return self._value


class Recorder:
    """A session that records each statement's text and parameters, in order, and answers the group lock's rotation."""

    def __init__(self, rotation: int = 0, bound_rows: int = 1) -> None:
        self.statements: list[tuple[str, dict[str, Any]]] = []
        self._rotation, self._bound_rows = rotation, bound_rows

    def execute(self, statement: Any, parameters: Any = None) -> Any:
        sql = str(statement)
        self.statements.append((sql, dict(parameters or {})))
        if "FROM executor_group WHERE group_id" in sql:
            return _Result(self._rotation)
        if sql.lstrip().startswith("UPDATE audit_run SET connection_revision_id"):
            return _Result(rowcount=self._bound_rows)
        return _Result()

    def kinds(self) -> list[str]:
        found = []
        for sql, _ in self.statements:
            if "FROM executor_group WHERE group_id" in sql:
                found.append("group")
            elif "pg_advisory_xact_lock" in sql:
                found.append("connection")
            elif sql.lstrip().startswith("UPDATE audit_run SET connection_revision_id"):
                found.append("bind")
            elif sql.lstrip().startswith("INSERT INTO audit_event"):
                found.append("event")
        return found


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """The executors and runs surfaces the dispatcher reaches, replaced by values; ``choose`` and ``member_issue`` stay real."""
    state = SimpleNamespace(revision=_revision(A, B), facts=[_facts(A), _facts(B)], consent=True, reads=[], rotations=[])

    def group_revision_of(session: Any, group_revision_id: str) -> Any:
        state.reads.append(("revision", group_revision_id))
        return state.revision if group_revision_id == GROUP_REVISION else None

    def member_facts(session: Any, revision: Any) -> list[MemberFacts]:
        state.reads.append(("facts", revision.group_revision_id))
        return list(state.facts)

    def advance(session: Any, group_id: str) -> int:
        state.rotations.append(group_id)
        return len(state.rotations)

    def consent(session: Any, **keywords: Any) -> bool:
        state.reads.append(("consent", keywords["group_revision_id"], keywords["billing"]))
        return state.consent

    monkeypatch.setattr(executors_public, "group_revision_of", group_revision_of)
    monkeypatch.setattr(executors_public, "member_facts", member_facts)
    monkeypatch.setattr(executors_public, "advance_group_rotation", advance)
    monkeypatch.setattr(runs_public, "group_consent_holds", consent)
    return state


def _select(session: Recorder) -> Any:
    return JobRepository()._select_member(session, run_id=RUN, group_revision_id=GROUP_REVISION)  # type: ignore[arg-type]


# --- the lock order -------------------------------------------------------------------------------------------------


def test_the_group_is_locked_first_then_every_member_connection_in_ascending_order(world: SimpleNamespace) -> None:
    world.revision = _revision(C, A, B)               # listed out of order on purpose
    world.facts = [_facts(C), _facts(A), _facts(B)]
    session = Recorder()
    _select(session)
    assert session.kinds()[:4] == ["group", "connection", "connection", "connection"]
    connections = [params["connection_id"] for sql, params in session.statements if "pg_advisory_xact_lock" in sql]
    assert connections == sorted([A, B, C]), "ascending connection_id, the order of ADR-0026 decision 14"
    assert "FOR UPDATE" in session.statements[0][0], "the group's row is locked, not merely read"
    assert [r[0] for r in world.reads[:1]] == ["revision"]


def test_the_connection_locks_are_the_ones_the_connection_path_and_the_comparison_call_take(world: SimpleNamespace) -> None:
    session = Recorder()
    _select(session)
    lock = next(sql for sql, _ in session.statements if "pg_advisory_xact_lock" in sql)
    assert lock == str(jobs._LOCK_CONNECTION), "one lock key per connection, shared with the other two claimants"


def test_a_claim_that_chooses_writes_nothing_until_it_binds(world: SimpleNamespace) -> None:
    session = Recorder()
    _select(session)
    assert "bind" not in session.kinds() and "event" not in session.kinds()
    assert world.rotations == [], "the rotation moves on with the binding, not with the choice"


# --- 5: least loaded, ties by the persisted rotation -----------------------------------------------------------------


def test_the_member_with_the_lowest_ratio_is_chosen_and_its_snapshot_revision_is_the_one_bound(
    world: SimpleNamespace,
) -> None:
    world.revision = _revision(A, B)
    world.facts = [_facts(A, used=2, capacity=4), _facts(B, used=1, capacity=4)]
    chosen = _select(Recorder())
    assert (chosen.connection_id, chosen.connection_revision_id, chosen.group_id) == (B, REVISION[B], GROUP)


def test_equal_members_take_turns_by_the_persisted_rotation(world: SimpleNamespace) -> None:
    picked = [_select(Recorder(rotation=n)).connection_id for n in range(4)]
    assert picked == [A, B, A, B], "the same loads and the cursor n give the n-th of the tied members, by connection id"


# --- 6, 7: a Run no member can take waits, and says why --------------------------------------------------------------


@pytest.mark.parametrize(("facts", "reason"), [
    ([_facts(A, used=1), _facts(B, used=1)], "executor_at_capacity"),
    ([_facts(A, used=1), _facts(B, online=False)], "executor_at_capacity"),
    ([_facts(A, online=False), _facts(B, online=False)], "runner_offline"),
    ([_facts(A, online=False, used=1), _facts(B, online=False)], "runner_offline"),
])
def test_a_run_that_no_member_can_take_is_refused_with_the_reason_it_waits_and_nothing_is_written(
    world: SimpleNamespace, facts: list[MemberFacts], reason: str,
) -> None:
    world.facts = facts
    session = Recorder()
    with pytest.raises(GroupDispatchWaiting) as caught:
        _select(session)
    assert caught.value.wait_reason == reason
    assert isinstance(caught.value, ExecutionNotClaimed) and caught.value.code is ErrorCode.CONFLICT
    assert not {"bind", "event"} & set(session.kinds()), "a refused claim writes nothing"
    assert world.rotations == []


# --- 9, 10: a member that is not what the group snapshotted is never chosen ------------------------------------------------


@pytest.mark.parametrize("ineligible", [
    {"snapshot": False}, {"archived": True}, {"served": False}, {"probed": False},
])
def test_an_ineligible_member_is_skipped_even_when_it_is_the_emptier_one(
    world: SimpleNamespace, ineligible: dict[str, bool],
) -> None:
    world.facts = [_facts(A, **ineligible), _facts(B, used=7, capacity=8)]
    assert _select(Recorder()).connection_id == B, "A would be the least loaded, but it is not what the group snapshotted"


def test_a_group_whose_every_member_is_stale_waits_as_runner_offline_and_adopts_none(world: SimpleNamespace) -> None:
    world.facts = [_facts(A, snapshot=False), _facts(B, archived=True)]
    with pytest.raises(GroupDispatchWaiting) as caught:
        _select(Recorder())
    assert caught.value.wait_reason == "runner_offline", "no member can serve: the wait the offline expiry ends"


# --- 12: the consent --------------------------------------------------------------------------------------------------------


def test_a_consent_that_no_longer_holds_binds_nothing_and_reads_no_member(world: SimpleNamespace) -> None:
    world.consent = False
    session = Recorder()
    with pytest.raises(GroupDispatchWaiting) as caught:
        _select(session)
    assert caught.value.wait_reason == "needs_reconsent"
    assert [read[0] for read in world.reads] == ["revision", "consent"], "no member fact was read"
    assert world.reads[1] == ("consent", GROUP_REVISION, "unmetered"), "billing in the estimate's spelling"


def test_metered_billing_reaches_the_consent_check_as_metered(world: SimpleNamespace) -> None:
    world.revision = _revision(A, B, billing="metered")
    _select(Recorder())
    assert ("consent", GROUP_REVISION, "metered") in world.reads


# --- 4: the binding --------------------------------------------------------------------------------------------------------


def test_the_dispatch_binds_once_advances_the_rotation_and_journals_one_allowlisted_event(world: SimpleNamespace) -> None:
    session = Recorder()
    chosen = _select(session)
    JobRepository()._bind(session, run_id=RUN, dispatch=chosen)  # type: ignore[arg-type]
    assert session.kinds()[-2:] == ["bind", "event"]
    sql, params = next(item for item in session.statements if item[0].lstrip().startswith("UPDATE audit_run"))
    assert "binding_state = 'bound'" in sql and "binding_state = 'pending'" in sql
    assert params == {"run_id": RUN, "revision_id": chosen.connection_revision_id}
    assert world.rotations == [GROUP], "advanced once, for this group"
    (event,) = [params for sql, params in session.statements if sql.lstrip().startswith("INSERT INTO audit_event")]
    assert event["event_type"] == "executor.run_dispatched" and event["event_type"].startswith("executor.")
    payload = json.loads(event["payload"])
    assert payload == {
        "run_id": RUN, "connection_id": chosen.connection_id, "revision_id": chosen.connection_revision_id,
        "work_kind": "text_analysis", "from_state": "pending", "to_state": "bound", "reason": "least_loaded"}
    assert set(payload) - {"run_id"} <= _SAFE_KEYS


def test_a_binding_that_changes_no_row_is_a_state_conflict_and_does_not_move_the_rotation(world: SimpleNamespace) -> None:
    session = Recorder(bound_rows=0)
    chosen = _select(Recorder())
    with pytest.raises(DomainError) as caught:
        JobRepository()._bind(session, run_id=RUN, dispatch=chosen)  # type: ignore[arg-type]
    assert caught.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert world.rotations == [] and "event" not in session.kinds()


# --- the binding state decides the lock path ---------------------------------------------------------------------------


class _Rows:
    def __init__(self, row: Any) -> None:
        self._row = row

    def execute(self, statement: Any, parameters: Any = None) -> Any:
        return _Result(self._row)


@pytest.mark.parametrize(("row", "expected"), [
    (("pending", GROUP_REVISION), GROUP_REVISION),
    (("bound", GROUP_REVISION), None),            # a retry stays on the bound member: the connection path
    (("frozen_at_start", None), None),            # the environment source is not pending
    (None, None),                                 # no such Run: the old path raises its own transition error
])
def test_only_a_pending_run_takes_the_dispatch_path(row: Any, expected: str | None) -> None:
    assert JobRepository._pending_group_revision(_Rows(row), run_id=RUN) == expected  # type: ignore[arg-type]


def test_a_pending_run_without_a_group_revision_is_an_internal_fault_not_an_unlimited_run() -> None:
    with pytest.raises(DomainError) as caught:
        JobRepository._pending_group_revision(_Rows(("pending", None)), run_id=RUN)  # type: ignore[arg-type]
    assert caught.value.code is ErrorCode.INTERNAL_ERROR


@pytest.mark.parametrize("row", [("bound", GROUP_REVISION, "excr_X"), ("pending", "exgr_OTHER", None),
                                 ("pending", GROUP_REVISION, "excr_X"), None])
def test_a_run_bound_by_another_claim_since_is_not_bound_again(row: Any) -> None:
    with pytest.raises(DomainError) as caught:
        JobRepository._require_still_pending(_Rows(row), run_id=RUN, group_revision_id=GROUP_REVISION)  # type: ignore[arg-type]
    assert caught.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED


def test_a_run_still_pending_under_the_run_lock_passes() -> None:
    JobRepository._require_still_pending(  # type: ignore[arg-type]
        _Rows(("pending", GROUP_REVISION, None)), run_id=RUN, group_revision_id=GROUP_REVISION)


# --- waiting is durable: the reasons, the setting, the carrier's handle --------------------------------------------------


@pytest.mark.parametrize(("issues", "reason"), [
    ([None, "at_capacity"], None),
    (["at_capacity", "at_capacity"], "executor_at_capacity"),
    (["at_capacity", "runner_offline"], "executor_at_capacity"),
    (["runner_offline", "runner_offline"], "runner_offline"),
    (["revision_changed", "connection_archived"], "runner_offline"),
    (["not_served", "probe_not_ok"], "runner_offline"),
])
def test_the_wait_reason_follows_the_first_issue_of_each_member(issues: list[str | None], reason: str | None) -> None:
    assert jobs._group_wait_reason(issues) == reason


def test_the_wait_reasons_are_the_words_of_run_queue_reason() -> None:
    from auditmanager.executors.model import WAIT_REASONS

    assert {jobs.WAIT_AT_CAPACITY, jobs.WAIT_RUNNER_OFFLINE, jobs.WAIT_NEEDS_RECONSENT} == set(WAIT_REASONS)


def test_an_ordinary_refusal_carries_no_wait_reason_and_a_group_refusal_does() -> None:
    assert getattr(ExecutionNotClaimed(ErrorCode.CONFLICT), "wait_reason", None) is None
    assert GroupDispatchWaiting("runner_offline").wait_reason == "runner_offline"


def test_an_unknown_wait_reason_is_refused_before_the_database_is_touched() -> None:
    with pytest.raises(ValueError):
        JobRepository().record_group_wait(None, run_id=RUN, reason="somewhere_else")  # type: ignore[arg-type]


def test_the_offline_wait_is_thirty_minutes_unless_set_and_a_bad_value_is_never_clamped() -> None:
    assert DEFAULT_GROUP_OFFLINE_WAIT_SECONDS == 1800
    assert JobRepository.group_offline_wait_seconds({}) == 1800
    assert JobRepository.group_offline_wait_seconds({GROUP_OFFLINE_WAIT_ENV: "60"}) == 60
    assert JobRepository.group_offline_wait_seconds({GROUP_OFFLINE_WAIT_ENV: " 900 "}) == 900
    for bad in ("", " ", "0", "-5", "+5", "1.5", "1e3", "thirty", "٣٠", str(7 * 24 * 3600 + 1)):
        with pytest.raises(ValueError, match=GROUP_OFFLINE_WAIT_ENV):
            JobRepository.group_offline_wait_seconds({GROUP_OFFLINE_WAIT_ENV: bad})


def test_the_worker_and_the_in_process_carrier_poll_the_waits_at_the_same_interval() -> None:
    from auditmanager.runs.carrier import GROUP_WAIT_SECONDS as carrier_seconds
    from auditmanager.workers.service import GROUP_WAIT_SECONDS as worker_seconds

    assert carrier_seconds == worker_seconds == 5.0


# --- the hint ---------------------------------------------------------------------------------------------------------------


def test_the_hint_keeps_the_old_test_for_every_run_that_is_not_pending_and_adds_one_for_a_pending_run() -> None:
    sql = str(jobs._NEXT_JOB)
    assert "r.binding_state <> 'pending' AND NOT EXISTS" in sql, "the old connection test, to the clause, for the rest"
    assert "mine.revision_id = r.connection_revision_id" in sql
    pending = sql[sql.index("r.binding_state = 'pending'"):]
    assert "executor_group_member" in pending and "group_member.group_revision_id = r.executor_group_revision_id" in pending
    assert "loaded.units" in pending and "max_active_runs" in pending, "units held < capacity, per member"
    assert sql.rstrip().endswith("FOR UPDATE OF r SKIP LOCKED")
    assert "ORDER BY j.priority DESC, j.created_at, j.job_id LIMIT 1" in sql, "the order is unchanged"


def test_the_hint_offers_a_pending_run_only_while_nothing_holds_it_back() -> None:
    """A Run the claim will refuse is offered once: with any stored reason it is not offered at all (`EXEC2-GROUP-RUN-01`)."""
    sql = str(jobs._NEXT_JOB)
    pending = sql[sql.index("r.binding_state = 'pending'"):]
    assert "AND r.wait_reason IS NULL" in pending, "a stored reason of any kind keeps the Run out of the hint"
    assert "DISTINCT FROM" not in pending, "no list of reasons that are excluded: every reason is"
    for reason in ("executor_at_capacity", "runner_offline", "needs_reconsent"):
        assert reason not in pending
    assert pending.index("r.wait_reason IS NULL") < pending.index("executor_group_member"), "the reason comes before the unit test"
    old = sql[:sql.index("r.binding_state = 'pending'")]
    assert "wait_reason" not in old, "the old branch for every other Run does not read it"


def test_the_hint_offers_no_pending_run_to_a_process_that_does_not_dispatch_groups() -> None:
    sql = str(jobs._NEXT_JOB)
    pending = sql[sql.index("r.binding_state = 'pending'"):]
    assert "CAST(:dispatch_groups AS boolean)" in pending
    assert "dispatch_groups" not in sql[:sql.index("r.binding_state = 'pending'")], "it gates the pending branch only"


@pytest.mark.parametrize("flag", [True, False])
def test_the_hint_is_asked_with_the_repositorys_dispatch_flag_and_the_submitted_runs(flag: bool) -> None:
    session = Recorder()
    JobRepository(dispatch_groups=flag).next_queued_run(session, submitted=("run_a",))  # type: ignore[arg-type]
    ((sql, parameters),) = session.statements
    assert sql == str(jobs._NEXT_JOB)
    assert parameters == {"submitted": ["run_a"], "dispatch_groups": flag}


def test_a_repository_dispatches_groups_unless_told_otherwise() -> None:
    assert JobRepository().dispatch_groups is True and JobRepository(worker_id="wrk_x").dispatch_groups is True
    assert JobRepository(dispatch_groups=False).dispatch_groups is False


class _ClaimView:
    """A session that answers the claim's first read (the Run's binding) and records every statement it is handed."""

    def __init__(self, row: Any) -> None:
        self.row, self.statements = row, []

    def execute(self, statement: Any, parameters: Any = None) -> Any:
        self.statements.append((str(statement), dict(parameters or {})))
        return _Result(self.row)


def test_a_process_that_does_not_dispatch_groups_refuses_a_pending_run_before_any_lock_or_write() -> None:
    session = _ClaimView(("pending", GROUP_REVISION))
    with pytest.raises(ExecutionNotClaimed) as caught:
        JobRepository(worker_id="wrk_x", dispatch_groups=False).start_execution(session, run_id=RUN)  # type: ignore[arg-type]
    assert caught.value.code is ErrorCode.CONFLICT and not isinstance(caught.value, GroupDispatchWaiting)
    assert getattr(caught.value, "wait_reason", None) is None, "an ordinary refusal: no reason is stored for it"
    assert len(session.statements) == 1, "only the binding was read"
    sql = session.statements[0][0]
    assert sql == str(jobs._CLAIM_BINDING) and "FOR " not in sql
    assert "ExecutorGroup" in str(caught.value.detail_fields.get("aggregate_type", ""))


def test_a_process_that_does_not_dispatch_groups_still_reads_every_other_run_as_it_did() -> None:
    """A frozen Run reaches the connection path (and its first statement), exactly as with the flag on."""
    for row in (("frozen_at_start", None), ("bound", GROUP_REVISION)):
        session = _ClaimView(row)
        with pytest.raises(Exception) as caught:
            JobRepository(dispatch_groups=False).start_execution(session, run_id=RUN)  # type: ignore[arg-type]
        assert not (isinstance(caught.value, ExecutionNotClaimed) and caught.value.detail_fields.get("aggregate_type") == "ExecutorGroup")
        assert len(session.statements) > 1, "the claim went on past the binding read"


def test_the_binding_write_names_the_pending_state_so_a_second_write_changes_no_row() -> None:
    sql = str(jobs._BIND_RUN)
    assert "binding_state = 'pending' AND connection_revision_id IS NULL" in sql
    assert "wait_reason = NULL, waiting_since = NULL" in sql, "binding ends the wait"


def test_a_wait_is_rewritten_only_when_its_reason_changes() -> None:
    sql = str(jobs._WRITE_WAIT)
    assert "wait_reason IS DISTINCT FROM CAST(:reason AS text)" in sql, "an unchanged reason keeps its clock"
    assert "binding_state = 'pending' AND state = 'queued'" in sql


# --- 6, 7, 8: the sweep keeps the waits true and ends the Runs nobody can serve ----------------------------------------------


class _Page:
    """What ``.mappings()`` of the sweep's reads answers: the rows of a page, or the one locked row."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> "_Page":
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None


class Sweeper:
    """A session for ``refresh_group_waits``: it answers the pages of pending Runs (keyset, as the statement asks) and the
    per-Run lock, and records the rest. A page carries what the statement selects; ``wait_expired`` is answered only by the lock,
    from the row **as locked** -- ``locked`` overrides it per Run, to show the sweep decides on that and not on the page."""

    def __init__(
        self, rows: list[dict[str, Any]], *, locked: bool = True, as_locked: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.rows, self.locked, self.as_locked, self.statements = rows, locked, as_locked or {}, []

    def execute(self, statement: Any, parameters: Any = None) -> Any:
        sql, params = str(statement), dict(parameters or {})
        self.statements.append((sql, params))
        if sql.startswith("SELECT r.run_id, r.executor_group_revision_id"):
            ordered = sorted(self.rows, key=lambda row: (row["created_at"], row["run_id"]))
            if params["after_run_id"] is not None:
                ordered = [row for row in ordered
                           if (row["created_at"], row["run_id"]) > (params["after_created_at"], params["after_run_id"])]
            return _Page([{key: value for key, value in row.items() if key != "wait_expired"}
                          for row in ordered[:params["batch_size"]]])
        if sql.startswith("SELECT r.run_id, r.stage_plan"):
            return _Page([])  # `HOSTS-BACKEND-01`: the planned Runs' own page (tests/unit/jobs/test_planned_dispatch_unit.py); none here
        if sql.startswith("SELECT run_id, wait_reason, waiting_since"):
            if not self.locked:
                return _Page([])
            row = next(item for item in self.rows if item["run_id"] == params["run_id"])
            return _Page([{"run_id": row["run_id"], "wait_reason": row["wait_reason"], "waiting_since": None,
                           "wait_expired": row["wait_expired"], **self.as_locked.get(row["run_id"], {})}])
        return _Result()

    def locks(self) -> list[str]:
        return [params["run_id"] for sql, params in self.statements if sql.startswith("SELECT run_id, wait_reason, waiting_since")]

    def pages(self) -> list[dict[str, Any]]:
        return [params for sql, params in self.statements if sql.startswith("SELECT r.run_id, r.executor_group_revision_id")]


_CREATED = iter(range(10_000))


def _pending(run_id: str, *, wait: str | None = None, expired: bool = False) -> dict[str, Any]:
    return {"run_id": run_id, "group_revision_id": GROUP_REVISION, "created_at": next(_CREATED), "wait_reason": wait,
            "wait_expired": expired}


@pytest.fixture
def sweep(world: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    seen = SimpleNamespace(written=[], ended=[], lapsed=[], failed=[], events=[])

    def record(self: JobRepository, session: Any, *, run_id: str, reason: str | None) -> bool:
        seen.written.append((run_id, reason))
        return True

    def end(self: JobRepository, session: Any, *, run_id: str) -> None:
        seen.ended.append(run_id)

    def lapse(self: JobRepository, session: Any, *, run_id: str) -> None:
        seen.lapsed.append(run_id)

    monkeypatch.setattr(JobRepository, "record_group_wait", record)
    monkeypatch.setattr(JobRepository, "_end_without_executor", end)
    monkeypatch.setattr(JobRepository, "_end_consent_lapsed", lapse)
    return seen


def _refresh(rows: list[dict[str, Any]], **options: Any) -> jobs.GroupWaits:
    return JobRepository().refresh_group_waits(Sweeper(rows, **options), offline_wait_seconds=1800)  # type: ignore[arg-type]


def test_a_run_a_member_could_take_has_its_wait_cleared(world: SimpleNamespace, sweep: SimpleNamespace) -> None:
    report = _refresh([_pending("run_a", wait="executor_at_capacity")])
    assert sweep.written == [("run_a", None)] and sweep.ended == [] and report.updated == 1


def test_a_run_with_every_member_full_waits_for_capacity_and_that_never_expires(
    world: SimpleNamespace, sweep: SimpleNamespace,
) -> None:
    world.facts = [_facts(A, used=1), _facts(B, used=1)]
    report = _refresh([_pending("old", wait="executor_at_capacity", expired=True), _pending("fresh")])
    assert sweep.written == [("fresh", "executor_at_capacity")], "a reason that is still true is kept, not rewritten"
    assert sweep.ended == [] and report.expired == 0 and report.updated == 1


def test_a_free_member_that_is_offline_does_not_clear_the_wait_of_a_run_the_online_member_is_too_full_for(
    world: SimpleNamespace, sweep: SimpleNamespace,
) -> None:
    """The stall: A has a free unit and is offline, B is online and full. Only a member with **no issue** clears a reason."""
    world.facts = [_facts(A, online=False), _facts(B, used=1)]
    report = _refresh([_pending("kept", wait="executor_at_capacity"), _pending("fresh"), _pending("stale", wait="runner_offline")])
    assert sweep.written == [("fresh", "executor_at_capacity"), ("stale", "executor_at_capacity")], (
        "set where there was none, replaced where it was another, kept where it was true -- and never cleared")
    assert report.updated == 2


def test_a_run_whose_members_are_all_offline_starts_its_clock_and_is_not_ended_by_one_look(
    world: SimpleNamespace, sweep: SimpleNamespace,
) -> None:
    world.facts = [_facts(A, online=False), _facts(B, online=False)]
    _refresh([_pending("fresh"), _pending("other_reason", wait="executor_at_capacity", expired=True),
              _pending("young", wait="runner_offline", expired=False)])
    assert sweep.ended == [], "the clock is the time spent waiting for *this* reason"
    assert sweep.written == [("fresh", "runner_offline"), ("other_reason", "runner_offline"),
                             ("young", "runner_offline")]


def test_a_run_offline_for_longer_than_the_wait_ends_no_executor_online_and_writes_no_wait(
    world: SimpleNamespace, sweep: SimpleNamespace,
) -> None:
    world.facts = [_facts(A, online=False), _facts(B, online=False)]
    report = _refresh([_pending("old", wait="runner_offline", expired=True)])
    assert sweep.ended == ["old"] and sweep.written == [] and (report.expired, report.updated) == (1, 0)


def test_a_member_coming_back_online_resets_the_clock_instead_of_ending_the_run(
    world: SimpleNamespace, sweep: SimpleNamespace,
) -> None:
    world.facts = [_facts(A, used=1), _facts(B, online=False)]       # A is online but full
    _refresh([_pending("old", wait="runner_offline", expired=True)])
    assert sweep.ended == [] and sweep.written == [("old", "executor_at_capacity")]


def test_the_offline_expiry_is_decided_on_the_locked_row_and_not_on_the_page_that_named_the_run(
    world: SimpleNamespace, sweep: SimpleNamespace,
) -> None:
    """Between the page and the lock a claim or an earlier pass changed the wait; what is read under the lock decides."""
    world.facts = [_facts(A, online=False), _facts(B, online=False)]
    rows = [_pending("page_says_old", wait="runner_offline", expired=True), _pending("page_says_young", wait="runner_offline")]
    report = _refresh(rows, as_locked={
        "page_says_old": {"wait_reason": "runner_offline", "wait_expired": False},        # rewritten since: young again
        "page_says_young": {"wait_reason": "runner_offline", "wait_expired": True},       # actually old under the lock
    })
    assert sweep.ended == ["page_says_young"], "the locked values decided, not the page's"
    assert sweep.written == [("page_says_old", "runner_offline")] and (report.expired, report.updated) == (1, 1)
    run = _refresh([_pending("changed", wait="runner_offline", expired=True)], as_locked={"changed": {"wait_reason": "executor_at_capacity"}})
    assert run.expired == 0 and sweep.ended == ["page_says_young"], "an expired clock of another reason is no expiry"


def test_the_lock_returns_what_the_expiry_is_decided_on_and_skips_a_run_a_claim_holds() -> None:
    sql = str(jobs._LOCK_PENDING_RUN)
    assert sql.startswith("SELECT run_id, wait_reason, waiting_since,")
    assert "waiting_since <= statement_timestamp() - make_interval(secs => :offline_seconds)) AS wait_expired" in sql
    assert sql.endswith("FOR UPDATE SKIP LOCKED")
    assert "binding_state = 'pending' AND state = 'queued'" in sql


def test_a_consent_that_no_longer_holds_ends_the_run_whatever_the_members_are(
    world: SimpleNamespace, sweep: SimpleNamespace,
) -> None:
    world.consent = False
    for facts in ([_facts(A), _facts(B)], [_facts(A, used=1), _facts(B, used=1)], [_facts(A, online=False), _facts(B, online=False)]):
        world.facts = facts
        sweep.lapsed.clear()
        report = _refresh([_pending("run_a"), _pending("run_b", wait="needs_reconsent"), _pending("run_c", wait="runner_offline")])
        assert sweep.lapsed == ["run_a", "run_b", "run_c"] and report.consent_lapsed == 3
    assert sweep.written == [] and sweep.ended == [], "needs_reconsent is not stored by the sweep: the Run ends"


def test_a_consent_that_holds_is_not_ended_and_a_run_whose_consent_lapsed_while_a_claim_holds_it_is_left_alone(
    world: SimpleNamespace, sweep: SimpleNamespace,
) -> None:
    assert _refresh([_pending("run_a", wait="executor_at_capacity")]).consent_lapsed == 0
    world.consent = False
    report = _refresh([_pending("claiming")], locked=False)
    assert sweep.lapsed == [] and report == jobs.GroupWaits()


def test_runs_of_one_group_revision_share_one_reading_of_its_members(world: SimpleNamespace, sweep: SimpleNamespace) -> None:
    world.facts = [_facts(A, used=1), _facts(B, used=1)]
    _refresh([_pending("one"), _pending("two"), _pending("three")])
    assert [read[0] for read in world.reads].count("facts") == 1
    assert [run for run, _ in sweep.written] == ["one", "two", "three"]


def test_a_run_a_claim_holds_is_skipped_not_waited_for(world: SimpleNamespace, sweep: SimpleNamespace) -> None:
    session = Sweeper([_pending("claiming", wait="executor_at_capacity")], locked=False)
    report = JobRepository().refresh_group_waits(session, offline_wait_seconds=1800)  # type: ignore[arg-type]
    assert sweep.written == [] and sweep.ended == [] and report == jobs.GroupWaits()
    locking = [sql for sql, _ in session.statements if sql.startswith("SELECT run_id, wait_reason")]
    assert locking and "SKIP LOCKED" in locking[0]


def test_a_run_whose_wait_is_already_true_is_not_locked_at_all(world: SimpleNamespace, sweep: SimpleNamespace) -> None:
    """The lock is held to the caller's commit; a pass over many Runs must not hold one for each of them for nothing."""
    world.facts = [_facts(A), _facts(B)]                                                  # a member is free
    session = Sweeper([_pending("free"), _pending("full", wait="executor_at_capacity")])
    JobRepository().refresh_group_waits(session, offline_wait_seconds=1800)  # type: ignore[arg-type]
    assert session.locks() == ["full"], "a Run with nothing to write is not locked; the one to clear is"
    assert sweep.written == [("full", None)]
    world.facts = [_facts(A, used=1), _facts(B, used=1)]                                  # every member is full
    session = Sweeper([_pending("waiting", wait="executor_at_capacity")])
    JobRepository().refresh_group_waits(session, offline_wait_seconds=1800)  # type: ignore[arg-type]
    assert session.locks() == [] and sweep.written == [("full", None)]


def test_the_pass_walks_every_pending_run_in_pages_by_keyset_and_none_stays_hidden(
    world: SimpleNamespace, sweep: SimpleNamespace,
) -> None:
    rows = [_pending(f"run_{n}", wait="executor_at_capacity") for n in range(5)]          # all stale: a member is free
    session = Sweeper(rows)
    report = JobRepository().refresh_group_waits(session, offline_wait_seconds=60, batch_size=2)  # type: ignore[arg-type]
    assert [run for run, _ in sweep.written] == [f"run_{n}" for n in range(5)] and report.updated == 5
    pages = session.pages()
    assert len(pages) == 3, "2 + 2 + 1: the short page ends the pass"
    assert pages[0] == {"batch_size": 2, "after_created_at": None, "after_run_id": None}
    assert (pages[1]["after_created_at"], pages[1]["after_run_id"]) == (rows[1]["created_at"], "run_1")
    assert (pages[2]["after_created_at"], pages[2]["after_run_id"]) == (rows[3]["created_at"], "run_3")


def test_a_full_last_page_is_followed_by_one_more_read_that_finds_nothing(world: SimpleNamespace, sweep: SimpleNamespace) -> None:
    rows = [_pending(f"run_{n}", wait="executor_at_capacity") for n in range(4)]
    session = Sweeper(rows)
    JobRepository().refresh_group_waits(session, offline_wait_seconds=60, batch_size=2)  # type: ignore[arg-type]
    assert len(session.pages()) == 3 and len(sweep.written) == 4


def test_the_pages_are_a_keyset_in_the_order_of_the_pending_index() -> None:
    sql = str(jobs._PENDING_RUNS)
    assert "binding_state = 'pending' AND r.state = 'queued' AND j.state = 'queued'" in sql
    assert "(r.created_at, r.run_id) > (CAST(:after_created_at AS timestamptz), CAST(:after_run_id AS text))" in sql
    assert "ORDER BY r.created_at, r.run_id LIMIT :batch_size" in sql and "OFFSET" not in sql
    assert "wait_expired" not in sql, "what the expiry is decided on is read under the lock"


def test_a_page_holds_at_least_one_run() -> None:
    with pytest.raises(ValueError):
        JobRepository().refresh_group_waits(Sweeper([]), batch_size=0)  # type: ignore[arg-type]


def test_the_pass_reads_the_oldest_pending_runs_first_in_a_bounded_page(world: SimpleNamespace, sweep: SimpleNamespace) -> None:
    session = Sweeper([])
    JobRepository().refresh_group_waits(session, offline_wait_seconds=60, batch_size=7)  # type: ignore[arg-type]
    sql, parameters = session.statements[0]
    assert parameters == {"batch_size": 7, "after_created_at": None, "after_run_id": None}
    assert "binding_state = 'pending' AND r.state = 'queued' AND j.state = 'queued'" in sql
    assert "ORDER BY r.created_at, r.run_id" in sql


# --- 15: the Run whose consent lapsed ends, visibly, through the terminal path of the offline expiry -----------------------------


def test_the_consent_lapse_closes_the_job_fails_the_run_and_journals_one_allowlisted_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    taken: list[tuple[str, str, str]] = []
    monkeypatch.setattr(JobRepository, "_close_for_run", lambda self, session, *, run_id, target: taken.append(("job", run_id, target)))
    monkeypatch.setattr(runs_public, "fail_run_consent_lapsed",
                        lambda session, *, run_id, from_state: taken.append(("run", run_id, from_state)))
    session = Recorder()
    JobRepository()._end_consent_lapsed(session, run_id=RUN)  # type: ignore[arg-type]
    assert taken == [("job", RUN, "failed"), ("run", RUN, "queued")], "the Job first, then the Run, as the offline expiry does"
    (event,) = [params for sql, params in session.statements if sql.lstrip().startswith("INSERT INTO audit_event")]
    assert event["event_type"] == "executor.group_consent_lapsed" and event["event_type"].startswith("executor.")
    payload = json.loads(event["payload"])
    assert payload == {"run_id": RUN, "work_kind": "text_analysis", "reason": "cost_estimate_binding_changed"}
    assert set(payload) - {"run_id"} <= _SAFE_KEYS


def test_the_reason_a_lapsed_consent_ends_a_run_with_is_the_run_paths_own_refusal() -> None:
    from auditmanager.analysis.text import cost
    from auditmanager.runs import cost_policy

    assert jobs.CONSENT_LAPSED_REASON == "cost_estimate_binding_changed"
    for source in (cost, cost_policy):
        assert f'reason="{jobs.CONSENT_LAPSED_REASON}"' in open(source.__file__, encoding="utf-8").read(), source.__name__
