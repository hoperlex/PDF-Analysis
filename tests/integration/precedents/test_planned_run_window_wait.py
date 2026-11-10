"""`EMBED-01`, `CRIT-CAPTURE-01` part C: a queued planned run is told it waits for the night window while the window is open (contract 1.51.0).

Real PostgreSQL, the shipped status adapter (``_planned_run_status_fields``) and the shipped ``window_wait`` over the control row and the window setting
the administrator journalled. The window is made around **now** in the zone UTC (an hour either side, so it holds whatever time the suite runs at,
midnight included); the state is the control row's. What is shown: inside an open window a queued run with no stored reason reports ``model_unavailable``
and **every cell of its plan** with the cause ``vector_window`` (and no ``waiting_since``: the wait is derived, never stored), and the same run reports
nothing when the window is closed, when its state is open but the clock is outside the window, when the run is not queued, and when it already has a stored
reason (that reading is the executors' own, and it never says ``vector_window``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.schemas import models
from auditmanager.bootstrap.adapters import _planned_run_status_fields
from auditmanager.precedents.public import PrecedentSettingService
from auditmanager.precedents.vectors import repository as vectors

PLAN = {
    "format": "stage-plan/1", "layout_revision_id": "slr_01M2545JSD15ETSNNV904X991A", "kit": "codex_only",
    "cells": [
        {"cell_key": "text:main", "model_id": "gpt-6-sol", "effort": "medium", "access": "subscription"},
        {"cell_key": "blocks:leg1", "model_id": "gpt-6-astra", "effort": "medium", "access": "subscription"},
        {"cell_key": "review:main", "model_id": "gpt-6-sol", "effort": "medium", "access": "api"},
    ],
}


def _run(**over: Any) -> Any:
    fields: dict[str, Any] = dict(run_id="run_01M2545JSD15ETSNNV904X993K", state="queued", wait_reason=None, waiting_since=None)
    fields.update(over)
    return SimpleNamespace(**fields)


def _around_now(sessions: sessionmaker[Session], uid: str, *, from_hours: int, to_hours: int) -> None:
    """Journal a window in UTC from ``now + from_hours`` to ``now + to_hours`` (whole minutes; the wall clock may cross midnight)."""
    now = datetime.now(UTC)
    PrecedentSettingService(sessions, roles_of=lambda _s, _u: frozenset({"admin"})).append_precedent_setting(
        setting_name="vector_window", user_uid=uid, idempotency_key=f"window-{now.timestamp()}-{from_hours}",
        value={"start": (now + timedelta(hours=from_hours)).strftime("%H:%M"), "end": (now + timedelta(hours=to_hours)).strftime("%H:%M"), "tz": "UTC"})


def _state(sessions: sessionmaker[Session], state: str) -> None:
    with sessions() as session:
        vectors.lock_control(session)
        vectors.set_window_state(session, state=state)
        session.commit()


def _fields(sessions: sessionmaker[Session], run: Any, state: str = "pending") -> dict[str, Any]:
    with sessions() as session:
        return _planned_run_status_fields(session, run, state, PLAN)


@pytest.mark.parametrize("open_state", ["draining", "encoding"])
def test_a_queued_run_inside_an_open_window_waits_for_the_window_in_every_cell(
    journalled_sessions: sessionmaker[Session], admin_uid: str, open_state: str,
) -> None:
    _around_now(journalled_sessions, admin_uid, from_hours=-1, to_hours=1)
    _state(journalled_sessions, open_state)
    fields = _fields(journalled_sessions, _run())
    assert fields["binding_state"] == "pending" and fields["wait_reason"] == "model_unavailable"
    assert "waiting_since" not in fields, "derived, never stored: there is no moment the wait began"
    assert [(c.cell_key, c.model_id, c.access, c.cause) for c in fields["wait_cells"]] == [
        ("text:main", "gpt-6-sol", "subscription", "vector_window"),
        ("blocks:leg1", "gpt-6-astra", "subscription", "vector_window"),
        ("review:main", "gpt-6-sol", "api", "vector_window")], "one per cell of the plan, in the plan's order"
    for cell in fields["wait_cells"]:   # each is a member of the contract's RunWaitCell, and the cause a word of its RunWaitCause
        models.RunWaitCell.model_validate({"cell_key": cell.cell_key, "model_id": cell.model_id, "access": cell.access, "cause": cell.cause})


def test_the_same_run_waits_for_nothing_when_the_window_is_closed_or_skipped_or_the_clock_is_outside_it(
    journalled_sessions: sessionmaker[Session], admin_uid: str,
) -> None:
    sessions = journalled_sessions
    _around_now(sessions, admin_uid, from_hours=-1, to_hours=1)
    for closed in ("closed",):
        _state(sessions, closed)
        assert _fields(sessions, _run()) == {"binding_state": "pending"}, closed
    with sessions() as session:
        vectors.lock_control(session)
        vectors.set_window_state(session, state="skipped", reason="encoder_failed")
        session.commit()
    assert _fields(sessions, _run()) == {"binding_state": "pending"}, "a skipped window holds nothing back"
    # a state that is open while the clock is already past the window: the pass has not looked yet, and there is no closing time to tell
    _around_now(sessions, admin_uid, from_hours=2, to_hours=3)
    _state(sessions, "encoding")
    assert _fields(sessions, _run()) == {"binding_state": "pending"}


def test_a_run_that_is_not_queued_or_not_pending_is_never_told_it_waits_for_the_window(
    journalled_sessions: sessionmaker[Session], admin_uid: str,
) -> None:
    sessions = journalled_sessions
    _around_now(sessions, admin_uid, from_hours=-1, to_hours=1)
    _state(sessions, "encoding")
    assert _fields(sessions, _run(state="running")) == {"binding_state": "pending"}
    assert _fields(sessions, _run(), state="bound") == {"binding_state": "bound"}


def test_a_run_with_a_stored_reason_keeps_the_executors_reading_and_never_says_vector_window(
    journalled_sessions: sessionmaker[Session], admin_uid: str,
) -> None:
    sessions = journalled_sessions
    _around_now(sessions, admin_uid, from_hours=-1, to_hours=1)
    _state(sessions, "encoding")
    since = datetime(2026, 11, 10, 9, 30, tzinfo=UTC)
    fields = _fields(sessions, _run(wait_reason="model_unavailable", waiting_since=since))
    assert fields["wait_reason"] == "model_unavailable" and fields["waiting_since"] == since, "the stored reason and its clock are the sweep's, untouched"
    assert all(cell.cause != "vector_window" for cell in fields.get("wait_cells", ()))
