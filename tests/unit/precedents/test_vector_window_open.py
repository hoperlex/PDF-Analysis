"""`D-684`: ``window_open``, the state of the night window read alone, for a gate that must hold new work (`ADR-0029` decision 8).

A fake session answers the control row's one SELECT. Each state is asked once, so a read that answered ``True`` for every state, or ``False`` for
every state, fails one of the four. The state is read and the clock is not: past the window's closing hour a state that is still open is still
open (the pass has not looked yet), and that is where ``window_wait`` answers ``None`` and ``window_open`` does not.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.precedents.public import window_open, window_wait
from auditmanager.precedents.vectors.window import OPEN_STATES, STATES


class ControlSession:
    """The one thing ``read_control`` asks of a session: ``execute(statement).first()`` is the control row."""

    def __init__(self, state: str) -> None:
        reason = "encoder_failed" if state == "skipped" else None
        self._row = (False, None, state, reason, datetime(2026, 11, 11, 1, 0, tzinfo=UTC))
        self.statements: list[str] = []

    def execute(self, statement: Any, *_args: Any, **_kwargs: Any) -> Any:
        self.statements.append(str(statement))
        return SimpleNamespace(first=lambda: self._row)


@pytest.mark.parametrize("state", STATES)
def test_the_window_is_open_in_exactly_the_two_states_that_hold_new_runs(state: str) -> None:
    assert window_open(ControlSession(state)) is (state in ("draining", "encoding"))  # type: ignore[arg-type]
    assert (state in OPEN_STATES) is (state in ("draining", "encoding")), "the two open states are the ones the dispatcher's hint holds on"


def test_the_read_is_one_select_of_the_control_row_and_writes_nothing() -> None:
    session = ControlSession("encoding")
    assert window_open(session) is True  # type: ignore[arg-type]
    assert len(session.statements) == 1
    statement = session.statements[0].upper()
    assert "FROM VECTOR_CONTROL" in statement and "UPDATE" not in statement, "a read of the control row, not a lock on it"


def test_past_the_closing_hour_an_open_state_still_holds_where_window_wait_answers_none() -> None:
    after_the_window = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)   # 14:00 at +05: the default window (01:00-06:00) is over
    session = ControlSession("draining")
    assert window_wait(session, now=after_the_window) is None  # type: ignore[arg-type]
    assert window_open(session) is True  # type: ignore[arg-type]
