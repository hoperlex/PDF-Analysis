"""The worker's pass that drives the night window (`ADR-0029` decision 8, plan-v5 section 5).

One call is one look at the clock, the control row and the exchange directory, and at most one step of the machine below; the whole state is in
the database (``vector_control``) and in the files of the exchange, so a worker that restarts in the middle of a night picks the round up where
it was, and a second worker's pass is serialized by the control row's lock.

::

    closed / skipped --(window open, not paused, intents pending, host timer alive)--> draining
    draining         --(nothing running)--> encoding           the batch is written for the host
    draining         --(paused)--> closed
    draining         --(window over, work still running)--> skipped  runs_did_not_finish
    encoding         --(host reports the container done, answer accepted)--> closed   vectors stored, intents done
    encoding         --(host reports a failure)--> skipped     encoder_failed / encoder_out_of_memory / encoder_timed_out / ...
    encoding         --(window over, no report)--> skipped     window_ended_while_encoding   the host is told to stop
    encoding         --(paused)--> closed, once the host reports (the container is stopped, nothing is imported)

**The window is used once.** After it closed, or was skipped, the machine stays idle until the next occurrence opens: a stand that has encoded
what was queued does not stop its runs again at four o'clock for what was queued since. **A skip is loud** (AGENTS section 4): a journalled
event with its reason, a state the administrator reads in the pause menu until the next window, and a line at ERROR in the log. Nothing is
silently repeated; the intents stay and the next night tries again.

**The queue fills all day**, paused or not (the backfill and every case captured since): an intent is a row, the encoder is the night's.
"""

from __future__ import annotations

import logging
import time as _time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.precedents.vectors import repository as store
from auditmanager.precedents.vectors.exchange import HEARTBEAT_FRESH_SECONDS, Exchange
from auditmanager.precedents.vectors.intents import (
    POISON_DIGEST_MISMATCH,
    POISON_TOKEN_LIMIT,
    ImportRefused,
    build_request,
    parse_answer,
)
from auditmanager.precedents.vectors.window import (
    STATE_CLOSED,
    STATE_DRAINING,
    STATE_ENCODING,
    STATE_SKIPPED,
    WindowSetting,
    WindowSpan,
    current_span,
)

__all__ = ["BACKFILL_ROUNDS", "MAX_LOOKS", "PassReport", "Step", "VectorWindowPass"]

_log = logging.getLogger(__name__)

#: At most this many batches of the backfill in one look: a large memory is queued over a few ticks, never in one long transaction.
BACKFILL_ROUNDS: Final[int] = 4
#: Looks that follow one another in one call: opened, drained, exported, and one more for the first wait.
MAX_LOOKS: Final[int] = 4
#: The container's exit statuses the host reports (`infra/deploy/embed-window.sh`): 0 done; 124 stopped at the deadline (the ``timeout`` convention);
#: 137 killed (the kernel's memory limit gives SIGKILL); 127 the image is not there.
_EXIT_DONE: Final[int] = 0
_EXIT_TIMEOUT: Final[int] = 124
_EXIT_KILLED: Final[int] = 137
_EXIT_IMAGE_MISSING: Final[int] = 127


@dataclass(frozen=True, slots=True)
class Step:
    """What one look did: the state it ended in, whether it changed, and a word for the log and the tests."""

    state: str
    changed: bool
    what: str


@dataclass(frozen=True, slots=True)
class PassReport:
    """What one call did: how many times the state changed, and the last look."""

    changes: int
    last: Step


class VectorWindowPass:
    """``pass_() -> int`` as the worker's housekeeping loop calls its passes: the number of state changes made (0 when idle).

    ``exchange`` is the directory shared with the host's timer; ``after_import`` (optional) runs after the vectors are committed, in no
    transaction of this pass, so the «Прецеденты» pass over fresh runs (`PREC-PASS`) can follow an import without this module knowing it."""

    def __init__(
        self, session_factory: sessionmaker[Session], exchange: Exchange, *, interval_seconds: float = 15.0,
        clock: Callable[[], datetime] | None = None, monotonic: Callable[[], float] | None = None,
        after_import: Callable[[], None] | None = None,
    ) -> None:
        if interval_seconds < 0:
            raise ValueError("a pass needs a non-negative interval")
        self._sessions = session_factory
        self._exchange = exchange
        self._interval = interval_seconds
        self._clock = clock or (lambda: datetime.now(UTC))
        self._monotonic = monotonic or _time.monotonic
        self._after_import = after_import
        self._next_at: float | None = None
        self._moment: datetime = self._clock()

    def __call__(self) -> int:
        now = self._monotonic()
        if self._next_at is not None and now < self._next_at:
            return 0
        self._next_at = now + self._interval
        return self.run().changes

    # -- one look ----------------------------------------------------------------------------------------------

    def run(self, now: datetime | None = None) -> PassReport:
        """Fill the queue, then look at the machine; while a step changed the state, look again (the drain, the export and the first wait of
        the encoder are looks of one call, not of three intervals). At most :data:`MAX_LOOKS` looks follow one another."""
        moment = now or self._clock()
        self._fill_queue()
        changes = 0
        step = self._look(moment)
        while step.changed:
            changes += 1
            if changes >= MAX_LOOKS:
                break
            step = self._look(moment)
        return PassReport(changes, step)

    def _fill_queue(self) -> None:
        """Queue the cases that have no intent, in transactions of their own, so it runs paused and outside the window (`R-153w`)."""
        for _ in range(BACKFILL_ROUNDS):
            with self._sessions() as session:
                added = store.add_intents_for_new_cases(session)
                session.commit()
            if added < store.BACKFILL_BATCH:
                return

    def _set(self, session: Session, state: str, reason: str | None = None) -> None:
        """Move the window and stamp the move with the moment of this look (the pass's clock, which the window's own span is read in)."""
        store.set_window_state(session, state=state, reason=reason, at=self._moment)

    def _look(self, now: datetime) -> Step:
        self._moment = now
        imported = False
        with self._sessions() as session:
            control = store.lock_control(session)
            setting = store.read_window_setting(session)
            span = current_span(now, setting)
            if control.window_state in (STATE_CLOSED, STATE_SKIPPED):
                step = self._idle(session, control, setting, span, now)
            elif control.window_state == STATE_DRAINING:
                step = self._draining(session, control, span)
            else:
                step, imported = self._encoding(session, control, span)
            session.commit()
        if imported and self._after_import is not None:
            try:
                self._after_import()
            except Exception:  # noqa: BLE001 - the vectors are stored; what follows them is the next look's to repeat
                _log.exception("the pass that follows an import of vectors failed")
        return step

    # -- closed and skipped -------------------------------------------------------------------------------------

    def _idle(self, session: Session, control: store.ControlRow, setting: WindowSetting, span: WindowSpan | None, now: datetime) -> Step:
        if control.paused:
            return Step(control.window_state, False, "paused")
        if span is None:
            return Step(control.window_state, False, "outside the window")
        if control.window_changed_at >= span.opens_at:
            return Step(control.window_state, False, "the window of this night was used")
        pending, _poisoned = store.count_intents(session)
        if pending == 0:
            return Step(control.window_state, False, "nothing queued")
        age = self._exchange.heartbeat_age_seconds(now)
        if age is None or age > HEARTBEAT_FRESH_SECONDS:
            return self._skip(session, "host_timer_silent", f"the host's timer has not reported for {'ever' if age is None else f'{int(age)} s'}")
        self._set(session, STATE_DRAINING)
        _log.info("the vector window opened until %s; no new run is issued", span.closing_clock(setting))
        return Step(STATE_DRAINING, True, "opened")

    # -- draining ------------------------------------------------------------------------------------------------

    def _draining(self, session: Session, control: store.ControlRow, span: WindowSpan | None) -> Step:
        if control.paused:
            self._set(session, STATE_CLOSED)
            return Step(STATE_CLOSED, True, "paused while draining")
        running = store.running_work(session)
        if span is None:
            reason = "runs_did_not_finish" if running else "window_ended_before_start"
            return self._skip(session, reason, f"the window ended while draining; {running} still running")
        if running:
            return Step(STATE_DRAINING, False, f"waiting for {running} running")
        self._set(session, STATE_ENCODING)
        return Step(STATE_ENCODING, True, "drained")

    # -- encoding ------------------------------------------------------------------------------------------------

    def _encoding(self, session: Session, control: store.ControlRow, span: WindowSpan | None) -> tuple[Step, bool]:
        result = self._exchange.result()
        if result is None:
            if span is None:
                self._exchange.request_abort()
                return self._skip(session, "window_ended_while_encoding", "the window ended before the host reported"), False
            if control.paused:
                self._exchange.request_abort()
                return Step(STATE_ENCODING, False, "paused; the host is told to stop"), False
            if not self._exchange.has_request():
                return self._export(session, span), False
            return Step(STATE_ENCODING, False, "waiting for the host"), False
        if control.paused:
            self._exchange.clear()
            self._set(session, STATE_CLOSED)
            return Step(STATE_CLOSED, True, "paused; the encoder was stopped and nothing is imported"), False
        if result.exit_code == _EXIT_DONE:
            return self._import(session)
        tail = self._exchange.stderr_tail()
        self._exchange.clear()
        reason = {
            _EXIT_KILLED: "encoder_out_of_memory", _EXIT_TIMEOUT: "encoder_timed_out", _EXIT_IMAGE_MISSING: "encoder_image_missing",
        }.get(result.exit_code, "encoder_failed")
        return self._skip(session, reason, f"the container ended with status {result.exit_code}: {tail.strip()[-500:]}"), False

    def _export(self, session: Session, span: WindowSpan) -> Step:
        """Write the batch for the host: the pending intents, one entry per distinct text. Whatever an earlier round left is cleared first."""
        pending = store.pending_intent_texts(session)
        changed = [item for item in pending if not item.matches]
        if changed:
            store.mark_poisoned(session, intent_ids=[item.intent_id for item in changed], reason=POISON_DIGEST_MISMATCH)
        usable = [item for item in pending if item.matches]
        if not usable:
            self._set(session, STATE_CLOSED)
            return Step(STATE_CLOSED, True, "nothing left to encode")
        try:
            self._exchange.clear()
            self._exchange.write_request(build_request(item.text for item in usable), deadline_epoch=int(span.closes_at.timestamp()))
        except OSError as exc:
            return self._skip(session, "export_failed", f"the exchange directory refused the batch: {exc}")
        return Step(STATE_ENCODING, False, f"{len(usable)} intents exported")

    def _import(self, session: Session) -> tuple[Step, bool]:
        request = self._exchange.read_request()
        try:
            if not isinstance(request, dict):
                raise ImportRefused("the request of the round is gone, so the answer cannot be matched to it")
            asked = [item["id"] for item in request["texts"]]
            parsed = parse_answer(self._exchange.read_response(), self._exchange.read_over_limit(), requested=asked)
        except (ImportRefused, ValueError, KeyError, TypeError) as exc:
            self._exchange.clear()
            return self._skip(session, "import_refused", str(exc)), False
        outcome = store.import_vectors(
            session, vectors=list(parsed.vectors.values()), over_limit=parsed.over_limit, rejected=parsed.rejected, missing=parsed.missing)
        self._exchange.clear()
        self._set(session, STATE_CLOSED)
        _log.info(
            "the vector window closed: %d stored, %d over the token limit (poisoned), %d refused (retried), %d unanswered, %d for forgotten cases",
            outcome.done, outcome.poisoned, outcome.retried, outcome.missing, outcome.skipped_forgotten)
        return Step(STATE_CLOSED, True, "imported"), outcome.done > 0

    # -- the loud skip -----------------------------------------------------------------------------------------

    def _skip(self, session: Session, reason: str, detail: str) -> Step:
        """The window did not take place. Journalled with its reason, shown to the administrator and logged at ERROR: the intents stay."""
        self._set(session, STATE_SKIPPED, reason)
        _log.error("the vector window was skipped (%s): %s; the queued intents wait for the next night", reason, detail)
        return Step(STATE_SKIPPED, True, reason)
