"""Which settlers a reclaim asks, and when (`CMP-C0-FIX-01` item 2; `CMP-SPEND-01` report section 8 item 2). Container-free.

A lost attempt may have left a model call ``sent``. The settlers (`SPEND_SETTLERS`) are what turns such a row ``unknown``;
before this lane the queue asked them only for an item it was not going to end ``cancelled``, so a cancel that arrived
with a lost lease left the call open. The tests drive ``reclaim_expired`` through a session that answers the four reads
of the pass from a script and a repository whose two writes are recorded, so the order of the settlers and the writes is
what is asserted. The same behaviour is shown against PostgreSQL in ``tests/integration/comparison/work/test_lease_reclaim.py``
and, through the real settler, in ``tests/integration/comparison/spend/test_reclaim_spend_unknown.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.comparison.work import repository as module
from auditmanager.comparison.work.repository import ComparisonWorkRepository


class Rows:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> "Rows":
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None


class ScriptedSession:
    """The reads of ``reclaim_expired``, answered for one lost attempt of one item."""

    def __init__(self, *, work: dict[str, Any], lease_current: bool = False, attempt_state: str = "running") -> None:
        self._work, self._lease, self._attempt_state = work, lease_current, attempt_state

    def execute(self, statement: object, params: dict[str, Any] | None = None) -> Rows:
        if statement is module._LOCK_TIMEOUT:
            return Rows([])
        if statement is module._EXPIRED:
            return Rows([{"attempt_id": "cqa_A", "work_id": "cqw_W"}])
        if statement is module._LOCK_WORK:
            return Rows([self._work])
        if statement is module._LOCK_ATTEMPT:
            return Rows([{"state": self._attempt_state, "lease_current": self._lease}])
        raise AssertionError(f"a read the script does not know: {statement}")


def _work(**changes: Any) -> dict[str, Any]:
    return {"current_work_attempt_id": "cqa_A", "state": "running", "cancel_requested": False,
            "attempt_count": 1, "max_attempts": 3, **changes}


@pytest.fixture
def log(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    events: list[tuple[str, ...]] = []

    def advance_attempt(session: object, attempt_id: str, from_state: str, to_state: str, **_: object) -> None:
        events.append(("attempt", attempt_id, to_state))

    def advance_work(session: object, work_id: str, from_state: str, to_state: str, **_: object) -> None:
        events.append(("work", work_id, to_state))

    monkeypatch.setattr(ComparisonWorkRepository, "_advance_attempt", staticmethod(advance_attempt))
    monkeypatch.setattr(ComparisonWorkRepository, "_advance_work", staticmethod(advance_work))
    monkeypatch.setattr(module, "_wake_workers", lambda session: events.append(("wake",)))
    return events


def _settler(name: str, answer: bool, events: list[tuple[str, ...]]) -> Any:
    def settle(session: object, attempt_id: str) -> bool:
        events.append(("settle", name, attempt_id))
        return answer

    return settle


def _reclaim(session: ScriptedSession, settlers: tuple[Any, ...]) -> int:
    return ComparisonWorkRepository().reclaim_expired(session, spend_settlers=settlers)  # type: ignore[arg-type]


def test_a_cancelled_item_asks_the_settler_about_the_lost_attempt_before_it_ends(log: list[tuple[str, ...]]) -> None:
    assert _reclaim(ScriptedSession(work=_work(cancel_requested=True)), (_settler("a", True, log),)) == 1
    assert log == [("attempt", "cqa_A", "lost"), ("settle", "a", "cqa_A"), ("work", "cqw_W", "cancelled")]


def test_the_cancel_wins_whatever_the_settler_answers(log: list[tuple[str, ...]]) -> None:
    for answer in (True, False):
        log.clear()
        _reclaim(ScriptedSession(work=_work(cancel_requested=True)), (_settler("a", answer, log),))
        assert ("work", "cqw_W", "cancelled") in log and ("work", "cqw_W", "spend_unknown") not in log


def test_every_settler_is_asked_for_a_cancelled_item_even_after_one_says_yes(log: list[tuple[str, ...]]) -> None:
    """``any(...)`` stops at the first ``True``; a call left open by the second family of settlers would stay open."""
    settlers = (_settler("first", True, log), _settler("second", False, log), _settler("third", True, log))
    _reclaim(ScriptedSession(work=_work(cancel_requested=True)), settlers)
    assert [event[1] for event in log if event[0] == "settle"] == ["first", "second", "third"]
    assert log[-1] == ("work", "cqw_W", "cancelled")


def test_a_cancelled_item_with_no_settler_ends_cancelled_as_before(log: list[tuple[str, ...]]) -> None:
    assert _reclaim(ScriptedSession(work=_work(cancel_requested=True)), ()) == 1
    assert log == [("attempt", "cqa_A", "lost"), ("work", "cqw_W", "cancelled")]


def test_a_leased_cancelled_item_is_asked_too(log: list[tuple[str, ...]]) -> None:
    """A lease that was never turned into a run (``leased``) is cancelled by the same branch."""
    _reclaim(ScriptedSession(work=_work(cancel_requested=True, state="leased"), attempt_state="leased"),
             (_settler("a", False, log),))
    assert ("settle", "a", "cqa_A") in log and log[-1] == ("work", "cqw_W", "cancelled")


def test_an_item_that_is_not_cancelled_is_unchanged_spend_unknown_or_requeued(log: list[tuple[str, ...]]) -> None:
    _reclaim(ScriptedSession(work=_work()), (_settler("a", True, log),))
    assert log[-1] == ("work", "cqw_W", "spend_unknown")
    log.clear()
    _reclaim(ScriptedSession(work=_work()), (_settler("a", False, log),))
    assert ("work", "cqw_W", "queued") in log and ("work", "cqw_W", "spend_unknown") not in log


def test_a_live_lease_never_reaches_the_settlers_even_with_a_cancel_requested(log: list[tuple[str, ...]]) -> None:
    assert _reclaim(ScriptedSession(work=_work(cancel_requested=True), lease_current=True), (_settler("a", True, log),)) == 0
    assert log == []


def test_an_attempt_that_is_not_the_items_current_one_is_never_settled(log: list[tuple[str, ...]]) -> None:
    other = ScriptedSession(work=_work(cancel_requested=True, current_work_attempt_id="cqa_OTHER"))
    assert _reclaim(other, (_settler("a", True, log),)) == 0
    assert log == []
