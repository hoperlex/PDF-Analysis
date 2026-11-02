"""`EXEC2-CAP-01` (ADR-0026 decision 1): the capacity reads of ``executors.queries``, against a stand-in for the
repository. The counts themselves are SQL and are proved on PostgreSQL in
``tests/integration/executors/test_connection_capacity.py``; what is decided *from* them is proved here.

* ``used_units`` / ``capacity_of`` / ``occupancies`` -- what ``EXEC2-GROUP-RUN-01`` and ``EXEC2-GROUP-CMP-01`` import;
* ``run_queue_reason`` -- ``runner_offline`` first, for a ``pull`` connection with no runner seen recently (the
  cause an administrator can act on), then ``executor_at_capacity``, otherwise nothing;
* the connection summaries carry the occupancy of the moment they were read.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from auditmanager.executors import queries
from auditmanager.executors.model import ConnectionRecord, ConnectionSummary, RevisionRecord, RevisionSettings
from auditmanager.executors.queries import (
    QUEUE_AT_CAPACITY,
    QUEUE_RUNNER_OFFLINE,
    Occupancy,
    capacity_of,
    list_connection_summaries,
    occupancies,
    occupancy_of,
    run_queue_reason,
    used_units,
)
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.shared.errors import DomainError, ErrorCode

NOW = datetime(2026, 11, 2, tzinfo=timezone.utc)


class Fake(ExecutorRepository):
    """Answers the four reads the capacity queries make and records which were asked, in order."""

    def __init__(
        self, *, counts: dict[str, tuple[int, int, int]] | None = None,
        queued: tuple[str, str] | None = None, online: bool = False,
        connections: tuple[ConnectionRecord, ...] = (),
    ) -> None:
        self.counts, self.queued, self.online, self.connections = counts or {}, queued, online, connections
        self.log: list[str] = []

    def unit_counts(self, session: Any, connection_ids: Any) -> dict[str, tuple[int, int, int]]:
        self.log.append("unit_counts")
        return {name: self.counts[name] for name in connection_ids if name in self.counts}

    def queued_run_connection(self, session: Any, run_id: str) -> tuple[str, str] | None:
        self.log.append("queued_run_connection")
        return self.queued

    def runner_online(self, session: Any, connection_id: str) -> bool:
        self.log.append("runner_online")
        return self.online

    def list_connections(self, session: Any, *, limit: int = 500) -> list[ConnectionRecord]:
        return list(self.connections)

    def current_revisions(self, session: Any, connection_ids: Any) -> dict[str, RevisionRecord]:
        return {}

    def current_secrets(self, session: Any, connection_ids: Any) -> dict[str, list[Any]]:
        return {}

    def current_routes(self, session: Any) -> list[Any]:
        return []


def _record(connection_id: str, kind: str = "http_api") -> ConnectionRecord:
    return ConnectionRecord(connection_id=connection_id, kind=kind, display_name=connection_id,
                            created_at=NOW, created_by="usr_A")


# --- Occupancy ----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("capacity", "runs", "calls", "used", "free"), [
    (1, 0, 0, 0, True), (1, 1, 0, 1, False), (1, 0, 1, 1, False),
    (3, 2, 0, 2, True), (3, 1, 1, 2, True), (3, 2, 1, 3, False), (3, 0, 3, 3, False),
    (1, 2, 1, 3, False),            # a lowered capacity: more in flight than allowed, none free
])
def test_a_unit_is_a_run_or_a_call_and_the_connection_is_full_when_they_reach_the_capacity(
    capacity: int, runs: int, calls: int, used: int, free: bool,
) -> None:
    occupancy = Occupancy(capacity, runs, calls)
    assert (occupancy.used, occupancy.has_free_unit) == (used, free)


# --- used_units, capacity_of, occupancies -------------------------------------------------------------------------


def test_used_units_and_capacity_of_read_the_same_counts() -> None:
    fake = Fake(counts={"exc_A": (3, 2, 1)})
    assert used_units(None, "exc_A", fake) == 3  # type: ignore[arg-type]
    assert capacity_of(None, "exc_A", fake) == 3  # type: ignore[arg-type]
    assert occupancy_of(None, "exc_A", fake) == Occupancy(3, 2, 1)  # type: ignore[arg-type]


def test_a_connection_that_does_not_exist_is_not_found_rather_than_a_default() -> None:
    for read in (used_units, capacity_of, occupancy_of):
        with pytest.raises(DomainError) as refused:
            read(None, "exc_NONE", Fake())  # type: ignore[arg-type]
        assert refused.value.code is ErrorCode.NOT_FOUND


def test_occupancies_answers_each_named_connection_in_one_read_and_omits_a_missing_one() -> None:
    fake = Fake(counts={"exc_A": (1, 0, 0), "exc_B": (4, 1, 2)})
    found = occupancies(None, ["exc_A", "exc_B", "exc_NONE"], fake)  # type: ignore[arg-type]
    assert found == {"exc_A": Occupancy(1, 0, 0), "exc_B": Occupancy(4, 1, 2)}
    assert fake.log == ["unit_counts"]


# --- run_queue_reason ---------------------------------------------------------------------------------------------


def test_a_run_that_is_not_waiting_has_no_reason_and_nothing_else_is_read() -> None:
    """Running, ended, or of the `environment` source (which froze no connection)."""
    fake = Fake(queued=None, counts={"exc_A": (1, 1, 0)})
    assert run_queue_reason(None, "run_X", fake) is None  # type: ignore[arg-type]
    assert fake.log == ["queued_run_connection"]


@pytest.mark.parametrize("counts", [(1, 1, 0), (1, 0, 1), (3, 2, 1), (3, 3, 0), (1, 2, 0)])
def test_a_waiting_run_on_a_full_connection_is_at_capacity(counts: tuple[int, int, int]) -> None:
    fake = Fake(queued=("exc_A", "http_api"), counts={"exc_A": counts})
    assert run_queue_reason(None, "run_X", fake) == QUEUE_AT_CAPACITY == "executor_at_capacity"  # type: ignore[arg-type]


@pytest.mark.parametrize("counts", [(1, 0, 0), (3, 2, 0), (3, 1, 1)])
def test_a_waiting_run_on_a_connection_with_a_free_unit_has_no_reason_unless_its_runner_is_offline(
    counts: tuple[int, int, int],
) -> None:
    for kind in ("http_api", "ssh_command"):
        assert run_queue_reason(None, "run_X", Fake(queued=("exc_A", kind), counts={"exc_A": counts})) is None  # type: ignore[arg-type]


def test_a_waiting_pull_run_with_a_free_unit_is_runner_offline_only_while_no_runner_was_seen_recently() -> None:
    offline = Fake(queued=("exc_A", "pull"), counts={"exc_A": (2, 1, 0)}, online=False)
    assert run_queue_reason(None, "run_X", offline) == QUEUE_RUNNER_OFFLINE == "runner_offline"  # type: ignore[arg-type]
    online = Fake(queued=("exc_A", "pull"), counts={"exc_A": (2, 1, 0)}, online=True)
    assert run_queue_reason(None, "run_X", online) is None  # type: ignore[arg-type]


def test_an_offline_runner_is_named_before_a_full_connection() -> None:
    """The integrator's ruling: the offline runner is the actionable cause, so it wins over a full connection."""
    fake = Fake(queued=("exc_A", "pull"), counts={"exc_A": (1, 1, 0)}, online=False)
    assert run_queue_reason(None, "run_X", fake) == QUEUE_RUNNER_OFFLINE  # type: ignore[arg-type]
    assert "unit_counts" not in fake.log, "the occupancy is not read once the runner is known to be offline"


def test_a_full_pull_connection_with_a_runner_online_is_at_capacity() -> None:
    fake = Fake(queued=("exc_A", "pull"), counts={"exc_A": (1, 1, 0)}, online=True)
    assert run_queue_reason(None, "run_X", fake) == QUEUE_AT_CAPACITY  # type: ignore[arg-type]
    assert fake.log == ["queued_run_connection", "runner_online", "unit_counts"]


def test_an_http_or_ssh_connection_is_never_runner_offline() -> None:
    for kind in ("http_api", "ssh_command"):
        fake = Fake(queued=("exc_A", kind), counts={"exc_A": (1, 0, 0)}, online=False)
        assert run_queue_reason(None, "run_X", fake) is None  # type: ignore[arg-type]
        assert "runner_online" not in fake.log


# --- the summaries ----------------------------------------------------------------------------------------------------


def test_each_connection_summary_carries_the_occupancy_read_with_it() -> None:
    fake = Fake(connections=(_record("exc_A"), _record("exc_B", "pull")),
                counts={"exc_A": (3, 2, 1), "exc_B": (1, 0, 0)})
    summaries = list_connection_summaries(None, fake)  # type: ignore[arg-type]
    assert [summary.connection.connection_id for summary in summaries] == ["exc_A", "exc_B"]
    assert [summary.occupancy for summary in summaries] == [Occupancy(3, 2, 1), Occupancy(1, 0, 0)]
    assert all(isinstance(summary, ConnectionSummary) for summary in summaries)
    assert fake.log == ["unit_counts"], "one statement for the whole list, not one per connection"


def test_a_summary_is_still_the_summary_the_other_readers_know() -> None:
    summary = list_connection_summaries(None, Fake(connections=(_record("exc_A"),), counts={"exc_A": (1, 0, 0)}))[0]  # type: ignore[arg-type]
    assert summary.current_revision is None and summary.secrets == () and summary.routed_work_kinds == ()


def test_the_occupancy_is_a_read_not_a_stored_field() -> None:
    assert "occupancy" not in RevisionSettings.__slots__
    assert not hasattr(queries, "store_occupancy")
