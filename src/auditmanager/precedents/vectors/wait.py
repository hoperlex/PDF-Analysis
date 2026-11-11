"""What a run that waits for the night window is told (`ADR-0029` decision 8, contract 1.51.0 ``RunWaitCause.vector_window``).

While ``vector_control.window_state`` is ``draining`` or ``encoding`` the stand issues no new run (the one query of ``jobs/repository.py``). A run
that is queued then waits, and the contract gives the wait one place to be told: **every cell of the run has the cause** ``vector_window`` and the
run's ``wait_reason`` is ``model_unavailable`` (``ck_audit_run_wait_reason`` was not widened; the seal chose the cell cause so that the closed
vocabulary of the run's reason stayed as it was).

**It is derived when the status is read, never stored.** ``audit_run.wait_reason`` is kept by the sweep, and a run that waits for
``model_unavailable`` longer than 30 minutes **ends** ``no_executor_online`` (`R-149c`): a window lasts up to five hours, so a stored wait would end
every run that was queued at night. The status adapter asks :func:`window_wait` and, when it answers, reports ``model_unavailable`` and one cell
per cell of the plan with this cause, and the sentence below; the stored reason and its clock are not touched.

Wiring (the composition root's, ``bootstrap/adapters.py`` ``_planned_run_status_fields``): after the stored-reason branch, for a ``pending``
planned run that is ``queued`` and has no stored reason, ``window = window_wait(session)``; when it is not ``None`` set ``wait_reason`` to
``model_unavailable`` and ``wait_cells`` to ``RunWaitCellView(cell_key, model_id, access, cause=window.cause)`` for each cell of the plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from sqlalchemy.orm import Session

from auditmanager.precedents.vectors import repository as store
from auditmanager.precedents.vectors.window import OPEN_STATES, current_span, wait_text

__all__ = ["CAUSE", "WindowWait", "window_open", "window_wait"]

#: The ``RunWaitCause`` word of the window.
CAUSE: Final[str] = "vector_window"


@dataclass(frozen=True, slots=True)
class WindowWait:
    """The window is open: the cause for every cell, the sentence for the run and the moment the window closes."""

    cause: str
    text: str
    closes_at: datetime


def window_wait(session: Session, *, now: datetime | None = None) -> WindowWait | None:
    """The wait the night window puts on every queued run now, or ``None`` when no run is held back by it.

    Read-only: one read of the control row and of the window setting. A state that is open while the clock is already past the window (the
    worker's pass has not looked yet) answers ``None``: there is no closing time to give, and the pass ends the state within seconds."""
    control = store.read_control(session)
    if control.window_state not in OPEN_STATES:
        return None
    setting = store.read_window_setting(session)
    span = current_span(now or datetime.now(UTC), setting)
    if span is None:
        return None
    return WindowWait(CAUSE, wait_text(span, setting), span.closes_at)


def window_open(session: Session) -> bool:
    """``True`` while ``vector_control.window_state`` is ``draining`` or ``encoding``: the stand starts no new work of its own.

    The state alone, with no look at the clock: the very condition the dispatcher's hint holds new runs on (``jobs/repository.py``, the same
    ``OPEN_STATES``), so work that reads this and the hint cannot disagree about whether the window holds. :func:`window_wait` is the other
    read and answers ``None`` past the window's closing hour although the state is still open (it tells a waiting run how long); it is
    the wrong read for a gate, which must hold until the pass has ended the state. Read-only: one read of the control row."""
    return store.read_control(session).window_state in OPEN_STATES
