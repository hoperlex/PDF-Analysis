"""`ADR-0027`: the decision memory's sweep, with the database and the assembler replaced.

What is shown: a pass captures what the anti-join returns and reports it; one event's failure is logged and does not stop the others
or roll them back; the pass is throttled; and the cursor lets a pass move past events that keep failing instead of starving the
ones behind them, while a short batch sends the next pass back to the beginning so the failures are retried.

`CRIT-CAPTURE-01`: the same pass repairs the experts' comments of cases that exist -- it hands the memory the ``comment`` events it does
not keep yet (the memory's own answer, ``captured_comment_sources``), one transaction each, after the decisions, with a cursor of its own;
a failure is reported and retried, and a comment the memory declines (a forgotten case) is not counted as written.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.bootstrap.adapters import MemoryCaptureSweep

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)


def _row(number: int, *, carried: str | None = None) -> dict[str, Any]:
    return {
        "sequence_no": number, "decision_id": f"dec_{number:026d}", "finding_uid": "fnd_x", "finding_observation_id": "fobs_x",
        "event_type": "accept", "verdict": "accepted", "severity": None, "comment": None, "author_label": "А",
        "author_user_uid": None, "command_id": None, "recorded_at": NOW, "carried_from_decision_id": carried,
    }


class _Result:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> "_Result":
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rows


def _comment_row(number: int) -> dict[str, Any]:
    return {**_row(number), "decision_id": f"dec_{number + 5000:026d}", "event_type": "comment", "verdict": None, "comment": "заметка"}


class _Session:
    def __init__(self, world: "_World") -> None:
        self._world = world
        self.committed = False

    def __enter__(self) -> "_Session":
        return self

    def __exit__(self, *exc: object) -> None:
        self._world.closed += 1

    def execute(self, statement: object, parameters: dict[str, Any]) -> _Result:
        after, batch = parameters["after"], parameters["batch"]
        if "'comment'" in str(statement):         # the comment repair's candidates: the ledger's comment events of existing cases
            self._world.comment_queries.append(dict(parameters))
            return _Result([r for r in self._world.comment_rows if r["sequence_no"] > after][:batch])
        self._world.queries.append(dict(parameters))
        pending = [r for r in self._world.rows if r["sequence_no"] > after and r["decision_id"] not in self._world.captured]
        return _Result(pending[:batch])

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:  # the sweep never needs it (closing a session rolls back its own transaction)
        raise AssertionError("the sweep must not roll back a session it only read from")


class _World:
    def __init__(
        self, rows: list[dict[str, Any]], failing: set[str] = frozenset(),  # type: ignore[assignment]
        comment_rows: list[dict[str, Any]] | None = None, kept: set[str] | None = None,
    ) -> None:
        self.rows, self.failing, self.captured = rows, set(failing), set()
        self.comment_rows = comment_rows or []
        self.kept = set(kept or ())                # the comment events the memory already keeps
        self.forgotten: set[str] = set()           # comment events of a forgotten case: declined, nothing written
        self.comment_queries: list[dict[str, Any]] = []
        self.order: list[str] = []                 # "decision" / "comment", in the order the assembler was called
        self.queries: list[dict[str, Any]] = []
        self.closed = 0
        self.seen: list[tuple[str, str]] = []

    def factory(self) -> _Session:
        return _Session(self)


class _Assembler:
    def __init__(self, world: _World) -> None:
        self._world = world

    def capture(self, session: _Session, event: Any, origin_kind: str) -> Any:
        self._world.order.append("decision")
        self._world.seen.append((event.decision_id, origin_kind))
        if event.decision_id in self._world.failing:
            raise RuntimeError("the crop manifest cannot be read")
        self._world.captured.add(event.decision_id)
        return SimpleNamespace(decision_created=True)

    def captured_comment_sources(self, session: _Session, decision_ids: list[str]) -> frozenset[str]:
        return frozenset(self._world.kept & set(decision_ids))

    def capture_comment(self, session: _Session, event: Any) -> Any:
        self._world.order.append("comment")
        self._world.seen.append((event.decision_id, event.event_type))
        if event.decision_id in self._world.failing:
            raise RuntimeError("the memory could not be written")
        if event.decision_id in self._world.forgotten:
            return SimpleNamespace(comment_created=False)
        self._world.kept.add(event.decision_id)
        return SimpleNamespace(comment_created=True)


def _sweep(world: _World, **options: Any) -> MemoryCaptureSweep:
    return MemoryCaptureSweep(world.factory, _Assembler(world), **options)  # type: ignore[arg-type]


def test_a_pass_captures_what_has_no_memory_decision_and_reports_it() -> None:
    world = _World([_row(1), _row(2, carried="dec_" + "9" * 26)])
    report = _sweep(world).run_once()
    assert (report.captured, report.failed) == (2, 0)
    assert world.seen == [(f"dec_{1:026d}", "direct"), (f"dec_{2:026d}", "carried")]
    assert _sweep(world).run_once().captured == 0  # nothing is left: the anti-join is the whole state


def test_one_failure_is_logged_and_does_not_stop_or_undo_the_others(caplog: pytest.LogCaptureFixture) -> None:
    world = _World([_row(1), _row(2), _row(3)], failing={f"dec_{2:026d}"})
    with caplog.at_level(logging.ERROR):
        report = _sweep(world).run_once()
    assert (report.captured, report.failed) == (2, 1)
    assert world.captured == {f"dec_{1:026d}", f"dec_{3:026d}"}
    assert any(f"dec_{2:026d}" in record.getMessage() and "RuntimeError" in record.getMessage() for record in caplog.records)
    assert "crop manifest" not in caplog.text  # the error's type is logged, never its text


def test_the_next_pass_retries_what_failed() -> None:
    world = _World([_row(1), _row(2)], failing={f"dec_{1:026d}"})
    sweep = _sweep(world)
    assert sweep.run_once().failed == 1
    world.failing.clear()
    assert sweep.run_once().captured == 1


def test_a_full_batch_moves_the_cursor_and_a_short_one_sends_it_back() -> None:
    world = _World([_row(n) for n in range(1, 6)], failing={f"dec_{1:026d}", f"dec_{2:026d}"})
    sweep = _sweep(world, batch=2)
    assert sweep.run_once().failed == 2          # events 1 and 2 fail; a full batch moves the cursor past them
    assert sweep.run_once().captured == 2        # events 3 and 4 are not starved by the two that keep failing
    assert sweep.run_once().captured == 1        # event 5: a short batch, so the cursor goes back to the start
    assert sweep.run_once().failed == 2          # and the two failures are tried again
    assert [q["after"] for q in world.queries] == [0, 2, 4, 0]


def test_the_pass_is_throttled_by_its_interval() -> None:
    now = [100.0]
    world = _World([_row(1)])
    sweep = _sweep(world, interval_seconds=30.0, clock=lambda: now[0])
    assert sweep() == 1
    world.rows.append(_row(2))
    now[0] = 110.0
    assert sweep() == 0 and len(world.queries) == 1      # too soon: nothing was even read
    now[0] = 131.0
    assert sweep() == 1


def test_a_sweep_needs_a_batch() -> None:
    with pytest.raises(ValueError):
        _sweep(_World([]), batch=0)


def test_a_pass_hands_the_memory_the_comments_of_existing_cases_it_does_not_keep_yet() -> None:
    world = _World([], comment_rows=[_comment_row(1), _comment_row(2), _comment_row(3)], kept={_comment_row(2)["decision_id"]})
    report = _sweep(world).run_once()
    assert (report.captured, report.failed, report.comments_captured, report.comments_failed) == (0, 0, 2, 0)
    assert world.seen == [(_comment_row(1)["decision_id"], "comment"), (_comment_row(3)["decision_id"], "comment")]  # the kept one is not handed over
    assert _sweep(world).run_once().comments_captured == 0       # nothing is left: the memory's answer is the whole state


def test_the_comments_are_repaired_after_the_decisions_in_the_same_pass() -> None:
    world = _World([_row(1)], comment_rows=[_comment_row(2)])
    sweep = _sweep(world)
    assert sweep.run_once().comments_captured == 1
    assert world.order == ["decision", "comment"]                # a case made by this pass has its comments repaired by this pass
    world.rows.append(_row(3))
    world.comment_rows.append(_comment_row(4))
    assert sweep() == 2                                          # the throttled call reports decisions and comments together


def test_a_comment_that_fails_is_logged_retried_and_does_not_stop_the_others(caplog: pytest.LogCaptureFixture) -> None:
    bad = _comment_row(2)["decision_id"]
    world = _World([], failing={bad}, comment_rows=[_comment_row(1), _comment_row(2), _comment_row(3)])
    with caplog.at_level(logging.ERROR):
        report = _sweep(world).run_once()
    assert (report.comments_captured, report.comments_failed) == (2, 1)
    assert world.kept == {_comment_row(1)["decision_id"], _comment_row(3)["decision_id"]}
    assert any(bad in record.getMessage() and "RuntimeError" in record.getMessage() for record in caplog.records)
    assert "could not be written" not in caplog.text             # the error's type is logged, never its text
    world.failing.clear()
    assert _sweep(world).run_once().comments_captured == 1       # the next pass tries it again


def test_a_comment_the_memory_declines_is_not_counted_as_written() -> None:
    declined = _comment_row(1)["decision_id"]
    world = _World([], comment_rows=[_comment_row(1)])
    world.forgotten.add(declined)
    report = _sweep(world).run_once()
    assert (report.comments_captured, report.comments_failed) == (0, 0)
    assert world.seen == [(declined, "comment")]                 # it was handed over (and answered "forgotten"), so it is not an error


def test_the_comment_cursor_is_its_own_and_follows_the_same_batch_rule() -> None:
    world = _World([_row(1)], comment_rows=[_comment_row(n) for n in range(1, 4)])
    sweep = _sweep(world, batch=2)
    sweep.run_once()
    sweep.run_once()
    assert [q["after"] for q in world.comment_queries] == [0, 2]      # a full batch moved it; the decisions' cursor did not
    sweep.run_once()
    assert [q["after"] for q in world.comment_queries][-1] == 0       # the short batch of the second pass sent it back to the start
