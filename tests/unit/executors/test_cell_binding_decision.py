"""`HOSTS-BACKEND-01` (ADR-0028 decisions 4, 5 and 15): which member a cell is bound to, and when none is.

The decision is a pure function over what was read (:func:`~auditmanager.executors.cell_binding._decide`): every cell is bound or none is; a run
holds one unit per pool however many cells share it; a pool whose slots are all in use takes no other run; the cause of a wait is named per cell; the
run's wait reason is ``model_unavailable`` when a cell has no *available* member and ``executor_at_capacity`` when the only trouble is full pools;
and the tie-break is stateless, so no group row is locked. The lock itself (two binds on one subscription cannot both pass) is proved on PostgreSQL
(``tests/integration/executors/test_hosts_backend.py``); here the unit-level half is shown: with the first run's unit counted, the second is refused.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from auditmanager.executors.cell_binding import (
    AT_CAPACITY,
    CAPACITY_WAIT_REASON,
    WAIT_MODEL_UNAVAILABLE,
    CellRequest,
    _Candidate,
    _decide,
    cell_requests,
)
from auditmanager.executors.host_commands import HostFacts, SlotUse
from auditmanager.executors.host_repository import HostRecord
from auditmanager.shared.errors import DomainError

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
ACTOR = "usr_01M2545JSD15ETSNNV904X991K"
HOST_A = "exh_01M2545JSD15ETSNNV904X991M"
HOST_B = "exh_01M2545JSD15ETSNNV904X991N"
OPUS, SONNET = "claude-opus-5-5", "claude-sonnet-5-5"
GROUP_REVISION = "exgr_01M2545JSD15ETSNNV904X991K"


def _facts(host_id: str, *, slots: int = 1, in_use: int = 0, provider: str = "claude_code") -> HostFacts:
    return HostFacts(
        record=HostRecord(host_id, "h", NOW, ACTOR), enabled=True, pulse_age_seconds=1.0, report=None,
        slots=(SlotUse(provider, "subscription", slots, in_use),), cooldowns={}, connections=(), now=NOW)


def _member(connection: str, host: str, *, reasons: tuple[str, ...] = (), in_service: bool = True,
            provider: str = "claude_code") -> _Candidate:
    return _Candidate(
        connection_id=connection, connection_revision_id="excr_" + connection[4:], host_id=host, provider=provider,
        pool=f"{host}:{provider}", reasons=reasons, in_service=in_service)


def _groups(**per_pair: list[_Candidate]) -> dict[tuple[str, str], tuple[str, list[_Candidate]]]:
    return {(model, "subscription"): (GROUP_REVISION, members)
            for model, members in ((OPUS, per_pair.get("opus", [])), (SONNET, per_pair.get("sonnet", [])))}


def _cells(*pairs: tuple[str, str]) -> list[CellRequest]:
    return [CellRequest(key, model, "subscription") for key, model in pairs]


def test_every_cell_is_bound_to_a_member_of_its_pair() -> None:
    a, b = _member("exc_AAAA", HOST_A), _member("exc_BBBB", HOST_B)
    outcome = _decide("run_1", _cells(("text:main", OPUS)), _groups(opus=[a, b]), {HOST_A: _facts(HOST_A), HOST_B: _facts(HOST_B)})
    assert outcome.reason is None and outcome.bound is not None
    (cell,) = outcome.bound
    assert cell.cell_key == "text:main" and cell.model_id == OPUS and cell.group_revision_id == GROUP_REVISION
    assert cell.connection_id in ("exc_AAAA", "exc_BBBB") and cell.host_id in (HOST_A, HOST_B)
    assert cell.pool == f"{cell.host_id}:claude_code"


def test_two_cells_in_one_pool_take_one_unit_because_a_run_holds_a_pool_once() -> None:
    """One subscription, one slot, two cells (Opus and Sonnet on the same host and provider): the run takes the pool's one unit for both."""
    opus, sonnet = _member("exc_OPUS", HOST_A), _member("exc_SONN", HOST_A)
    outcome = _decide("run_1", _cells(("text:main", OPUS), ("norms:main", SONNET)), _groups(opus=[opus], sonnet=[sonnet]),
                      {HOST_A: _facts(HOST_A, slots=1, in_use=0)})
    assert outcome.bound is not None and {cell.pool for cell in outcome.bound} == {f"{HOST_A}:claude_code"}


def test_a_second_run_finds_the_pool_full_once_the_first_runs_unit_is_counted() -> None:
    """The unit-level half of «two binds on one subscription must not both pass»: the facts the second decision reads include the first's unit."""
    member = _member("exc_AAAA", HOST_A)
    first = _decide("run_1", _cells(("text:main", OPUS)), _groups(opus=[member]), {HOST_A: _facts(HOST_A, slots=1, in_use=0)})
    second = _decide("run_2", _cells(("text:main", OPUS)), _groups(opus=[member]), {HOST_A: _facts(HOST_A, slots=1, in_use=1)})
    assert first.bound is not None
    assert second.bound is None and second.reason == CAPACITY_WAIT_REASON == "executor_at_capacity"
    assert [(wait.cell_key, wait.cause) for wait in second.waits] == [("text:main", AT_CAPACITY)]


def test_a_cell_prefers_a_pool_its_run_already_holds_over_a_free_unit_elsewhere() -> None:
    held, other = _member("exc_HELD", HOST_A), _member("exc_OTHR", HOST_B)
    groups = _groups(opus=[held], sonnet=[_member("exc_SONA", HOST_A), _member("exc_SONB", HOST_B)])
    facts = {HOST_A: _facts(HOST_A, slots=1, in_use=0), HOST_B: _facts(HOST_B, slots=1, in_use=0)}
    del other
    for run in (f"run_{n}" for n in range(1, 41)):
        outcome = _decide(run, _cells(("text:main", OPUS), ("norms:main", SONNET)), groups, facts)
        assert outcome.bound is not None
        assert {cell.host_id for cell in outcome.bound} == {HOST_A}, "the second cell follows the first into the pool the run holds"


def test_the_least_loaded_pool_wins_and_ties_spread_by_a_stateless_hash() -> None:
    a, b = _member("exc_AAAA", HOST_A), _member("exc_BBBB", HOST_B)
    facts = {HOST_A: _facts(HOST_A, slots=4, in_use=3), HOST_B: _facts(HOST_B, slots=4, in_use=1)}
    for run in ("run_1", "run_2", "run_3"):
        outcome = _decide(run, _cells(("text:main", OPUS)), _groups(opus=[a, b]), facts)
        assert outcome.bound is not None and outcome.bound[0].host_id == HOST_B, "3/4 versus 1/4: the emptier pool"
    equal = {HOST_A: _facts(HOST_A, slots=2, in_use=1), HOST_B: _facts(HOST_B, slots=2, in_use=1)}
    chosen = {_decide(f"run_{n}", _cells(("text:main", OPUS)), _groups(opus=[a, b]), equal).bound[0].host_id for n in range(40)}  # type: ignore[index]
    assert chosen == {HOST_A, HOST_B}, "a tie is broken by a hash of the run and the cell, so it spreads"
    again = [_decide("run_7", _cells(("text:main", OPUS)), _groups(opus=[a, b]), equal).bound[0].host_id for _ in range(5)]  # type: ignore[index]
    assert len(set(again)) == 1, "and the same run always gets the same answer"


def test_one_cell_without_an_available_member_binds_nothing() -> None:
    ok = _member("exc_OPUS", HOST_A)
    down = _member("exc_SONN", HOST_A, reasons=("host_offline",))
    outcome = _decide("run_1", _cells(("text:main", OPUS), ("norms:main", SONNET)), _groups(opus=[ok], sonnet=[down]),
                      {HOST_A: _facts(HOST_A)})
    assert outcome.bound is None, "no cell is bound when any cell cannot be"
    assert outcome.reason == WAIT_MODEL_UNAVAILABLE == "model_unavailable"
    assert [(wait.cell_key, wait.model_id, wait.cause) for wait in outcome.waits] == [("norms:main", SONNET, "host_offline")]


@pytest.mark.parametrize(("reasons", "cause"), [
    (("host_disabled",), "host_disabled"), (("host_offline",), "host_offline"),
    (("login_required", "model_not_verified"), "login_required"), (("model_not_verified",), "model_not_verified"),
    (("model_cooling_down",), "model_cooling_down"),
])
def test_the_cause_of_a_wait_is_the_most_actionable_reason(reasons: tuple[str, ...], cause: str) -> None:
    outcome = _decide("run_1", _cells(("text:main", OPUS)), _groups(opus=[_member("exc_AAAA", HOST_A, reasons=reasons)]),
                      {HOST_A: _facts(HOST_A)})
    assert outcome.reason == "model_unavailable" and outcome.waits[0].cause == cause


def test_the_member_with_the_fewest_reasons_names_the_cause() -> None:
    worse = _member("exc_AAAA", HOST_A, reasons=("host_disabled", "host_offline"))
    closer = _member("exc_BBBB", HOST_B, reasons=("model_cooling_down",))
    outcome = _decide("run_1", _cells(("text:main", OPUS)), _groups(opus=[worse, closer]), {HOST_A: _facts(HOST_A), HOST_B: _facts(HOST_B)})
    assert outcome.waits[0].cause == "model_cooling_down"


def test_a_model_on_no_server_waits_as_not_on_any_server() -> None:
    for members in ([], [_member("exc_GONE", HOST_A, in_service=False)]):
        outcome = _decide("run_1", _cells(("text:main", OPUS)), _groups(opus=members), {HOST_A: _facts(HOST_A)})
        assert outcome.reason == "model_unavailable" and outcome.waits[0].cause == "not_on_any_server"


def test_an_unavailable_cell_makes_the_run_wait_for_the_model_even_when_another_cell_is_only_busy() -> None:
    busy = _member("exc_OPUS", HOST_A)
    down = _member("exc_SONN", HOST_B, reasons=("host_offline",))
    outcome = _decide("run_1", _cells(("text:main", OPUS), ("norms:main", SONNET)), _groups(opus=[busy], sonnet=[down]),
                      {HOST_A: _facts(HOST_A, slots=1, in_use=1), HOST_B: _facts(HOST_B)})
    assert outcome.reason == "model_unavailable", "the 30-minute expiry belongs to the unavailable cell, not to the busy one"
    assert {wait.cause for wait in outcome.waits} == {AT_CAPACITY, "host_offline"}


def test_a_member_whose_snapshot_is_not_the_current_revision_is_never_adopted() -> None:
    stale = _member("exc_AAAA", HOST_A, in_service=False)
    fresh = _member("exc_BBBB", HOST_B)
    outcome = _decide("run_1", _cells(("text:main", OPUS)), _groups(opus=[stale, fresh]), {HOST_A: _facts(HOST_A), HOST_B: _facts(HOST_B)})
    assert outcome.bound is not None and outcome.bound[0].connection_id == "exc_BBBB"


def test_the_capacity_wait_word_is_one_switch() -> None:
    assert CAPACITY_WAIT_REASON in ("executor_at_capacity", WAIT_MODEL_UNAVAILABLE)


# --- the plan the cells are read from ---------------------------------------------------------------------------


def test_the_cells_of_a_plan_are_read_in_order_with_model_and_access() -> None:
    plan = {"cells": [
        {"cell_key": "text:main", "model_id": OPUS, "access": "subscription", "effort": "medium"},
        {"cell_key": "blocks:leg1", "model_id": SONNET, "access": "api", "effort": "low"}]}
    assert cell_requests(plan) == [CellRequest("text:main", OPUS, "subscription"), CellRequest("blocks:leg1", SONNET, "api")]


@pytest.mark.parametrize("cell", [
    {"cell_key": "text:main", "model_id": OPUS}, {"cell_key": "text:main", "access": "subscription"},
    {"model_id": OPUS, "access": "subscription"}, {"cell_key": "text:main", "model_id": OPUS, "access": "free"},
])
def test_a_cell_without_its_key_model_or_access_is_the_plans_defect_and_is_refused(cell: dict[str, str]) -> None:
    with pytest.raises(DomainError):
        cell_requests({"cells": [cell]})
