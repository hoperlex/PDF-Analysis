"""`EMBED-01` (ADR-0029 decision 8): while the night window is open the stand takes no new run -- in the same query as the analysis pause.

Real PostgreSQL. The dispatcher's hint (``JobRepository.next_queued_run``, the one statement that also holds the analysis pause) is asked with a
run that is queued and runnable, in each state of ``vector_control``: ``draining`` and ``encoding`` offer nothing, ``closed`` and ``skipped`` offer
the run, and the analysis pause still holds on its own. The check is shown able to fail by the run being offered in the states that do not hold it:
a hint that offered nothing in every state would pass "draining offers nothing" too.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.jobs.public import JobRepository
from auditmanager.precedents.public import VECTOR_WINDOW_CAUSE, window_wait

pytestmark = pytest.mark.usefixtures("quiet_queue")


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


support = _load("embed01_connection_limit_support", "connection_limit_support.py")
window = _load("embed01_vector_window_support", "vector_window_support.py")


@pytest.fixture(autouse=True)
def _control_back(sessions: sessionmaker[Session]) -> object:
    window.reset_control(sessions)
    yield
    window.reset_control(sessions)


def _hint(sessions: sessionmaker[Session]) -> str | None:
    with sessions() as session:
        return JobRepository().next_queued_run(session)


def _state(sessions: sessionmaker[Session], state: str, reason: str | None = None) -> None:
    with sessions() as session:
        session.execute(text("UPDATE vector_control SET window_state = :s, window_reason = :r WHERE control_key = 'default'"), {"s": state, "r": reason})
        session.commit()


@pytest.fixture
def queued_run(sessions: sessionmaker[Session]) -> object:
    run_id = support.queue_run(sessions, None)
    yield run_id
    support.cancel(sessions, run_id)


def test_a_queued_run_is_offered_while_the_window_is_closed_or_was_skipped(sessions: sessionmaker[Session], queued_run: str) -> None:
    assert _hint(sessions) == queued_run
    _state(sessions, "skipped", "encoder_failed")
    assert _hint(sessions) == queued_run, "a skipped window holds nothing: the night that did not happen costs no run"


@pytest.mark.parametrize("state", ["draining", "encoding"])
def test_a_queued_run_is_not_offered_in_the_two_open_states(sessions: sessionmaker[Session], queued_run: str, state: str) -> None:
    _state(sessions, state)
    assert _hint(sessions) is None
    _state(sessions, "closed")
    assert _hint(sessions) == queued_run, "and it is offered again the moment the window closes"


def test_the_analysis_pause_still_holds_on_its_own_and_the_two_are_one_statement(sessions: sessionmaker[Session], queued_run: str) -> None:
    with sessions() as session:
        JobRepository().set_paused(session, paused=True)
        session.commit()
    try:
        assert _hint(sessions) is None
    finally:
        with sessions() as session:
            JobRepository().set_paused(session, paused=False)
            session.commit()
    assert _hint(sessions) == queued_run
    from auditmanager.jobs import repository

    statement = str(repository._NEXT_JOB)
    assert "FROM execution_control WHERE singleton AND paused" in statement and "FROM vector_control WHERE control_key = 'default'" in statement, (
        "one query holds both, so a claim cannot pass one check and miss the other")


def test_a_run_waiting_for_the_window_is_told_so_with_the_closing_hour_and_only_while_it_is_open(sessions: sessionmaker[Session]) -> None:
    inside = datetime(2026, 11, 10, 21, 0, tzinfo=UTC)   # 02:00 at +05 on the 11th is 21:00 UTC the evening before
    with sessions() as session:
        assert window_wait(session, now=inside) is None, "closed: nobody waits"
    for state in ("draining", "encoding"):
        _state(sessions, state)
        with sessions() as session:
            found = window_wait(session, now=inside)
        assert found is not None and found.cause == VECTOR_WINDOW_CAUSE == "vector_window"
        assert found.text == "ночное окно векторов, до 06:00"
    _state(sessions, "skipped", "encoder_failed")
    with sessions() as session:
        assert window_wait(session, now=inside) is None
    _state(sessions, "draining")
    with sessions() as session:
        assert window_wait(session, now=datetime(2026, 11, 11, 9, 0, tzinfo=UTC)) is None, "the clock is past the window and the pass has not looked yet"
