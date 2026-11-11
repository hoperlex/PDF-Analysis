"""The worker's pass that drives the night window (`ADR-0029` decision 8, plan-v5 section 5).

One call is one look at the clock, the control row and the exchange directory, and at most one step of the machine below; the whole state is in
the database (``vector_control``) and in the files of the exchange, so a worker that restarts in the middle of a night picks the round up where
it was, and a second worker's pass is serialized by the control row's lock.

::

    closed / skipped --(window open, not paused, intents pending, host timer alive)--> draining
    draining         --(nothing running)--> encoding           the batch is written for the host
    draining         --(paused)--> closed
    draining         --(window over, work still running)--> skipped  runs_did_not_finish
    encoding         --(host reports the container done, answer accepted, clean)--> encoding   the next round, while time and intents remain
    encoding         --(the last round imported, or too little of the window is left)--> closed   vectors stored, intents done
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

__all__ = ["BACKFILL_ROUNDS", "MAX_FAILED_LOOKS", "MAX_LOOKS", "MIN_ROUND_SECONDS", "PassReport", "Step", "VectorWindowPass"]

_log = logging.getLogger(__name__)

#: At most this many batches of the backfill in one look: a large memory is queued over a few ticks, never in one long transaction.
BACKFILL_ROUNDS: Final[int] = 4
#: Looks that follow one another in one call: opened, drained, exported, and one more for the first wait.
MAX_LOOKS: Final[int] = 4
#: Consecutive looks that raise before the pass gives the stand back (a skip with ``pass_failed``): while the window is open the stand takes no run, so a pass
#: that cannot do its work must not hold it. One failure is a bad moment (a lock, a timeout); three in a row (about a minute) is a fault.
MAX_FAILED_LOOKS: Final[int] = 3
#: A new round starts after an import only if at least this much of the window is left: an encoder that is cut off loses its round.
MIN_ROUND_SECONDS: Final[int] = 1200
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
        after_import: Callable[[], None] | None = None, round_limit: int = store.EXPORT_LIMIT,
    ) -> None:
        if interval_seconds < 0:
            raise ValueError("a pass needs a non-negative interval")
        self._sessions = session_factory
        self._exchange = exchange
        self._interval = interval_seconds
        self._clock = clock or (lambda: datetime.now(UTC))
        self._monotonic = monotonic or _time.monotonic
        self._after_import = after_import
        self._round_limit = round_limit
        self._next_at: float | None = None
        self._moment: datetime = self._clock()
        self._failed_looks = 0

    def __call__(self) -> int:
        now = self._monotonic()
        if self._next_at is not None and now < self._next_at:
            return 0
        self._next_at = now + self._interval
        return self.run().changes

    # -- one look ----------------------------------------------------------------------------------------------

    def run(self, now: datetime | None = None) -> PassReport:
        """Fill the queue, then look at the machine; while a step changed the state, look again (the drain, the export and the first wait of
        the encoder are looks of one call, not of three intervals). At most :data:`MAX_LOOKS` looks follow one another.

        A look that raises is logged and tried again at the next call; :data:`MAX_FAILED_LOOKS` in a row give the stand back (:meth:`_give_back`)."""
        moment = now or self._clock()
        try:
            self._fill_queue()
        except Exception:  # noqa: BLE001 - the queue is the day's work; a window that is open must not wait for it
            _log.exception("the queue of intents could not be filled; the window's own work goes on")
        changes = 0
        try:
            step = self._look(moment)
            while step.changed:
                changes += 1
                if changes >= MAX_LOOKS:
                    break
                step = self._look(moment)
        except Exception:  # noqa: BLE001 - see _give_back
            self._failed_looks += 1
            _log.exception("a look of the vector window failed (%d in a row)", self._failed_looks)
            if self._failed_looks >= MAX_FAILED_LOOKS:
                self._give_back(moment)
            return PassReport(changes, Step("unknown", False, "failed"))
        self._failed_looks = 0
        return PassReport(changes, step)

    def _give_back(self, now: datetime) -> None:
        """The pass cannot do its work: if the window is holding the stand, skip it (loudly, with ``pass_failed``) and tell the host to stop. Best effort:
        if the database itself is what failed, nothing is running that this could free."""
        self._moment = now
        try:
            with self._sessions() as session:
                control = store.lock_control(session)
                if control.window_state in (STATE_DRAINING, STATE_ENCODING):
                    self._skip(session, "pass_failed", f"{self._failed_looks} looks in a row raised")
                    try:
                        self._exchange.request_abort()
                    except OSError:
                        _log.exception("the host could not be told to stop")
                session.commit()
            self._failed_looks = 0
        except Exception:  # noqa: BLE001 - nothing more can be done from here
            _log.exception("the stand could not be given back by the failing pass")

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
        if store.count_pending_work(session) == 0:
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
        try:
            result = self._exchange.result()
        except ValueError as exc:   # the host writes it whole; a file that is not one is a fault, and the round is not waited for
            self._exchange.clear()
            return self._skip(session, "encoder_failed", f"the host's account of the container could not be read: {exc}"), False
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
            return self._import(session, span)
        tail = self._exchange.stderr_tail()
        self._exchange.clear()
        reason = {
            _EXIT_KILLED: "encoder_out_of_memory", _EXIT_TIMEOUT: "encoder_timed_out", _EXIT_IMAGE_MISSING: "encoder_image_missing",
        }.get(result.exit_code, "encoder_failed")
        return self._skip(session, reason, f"the container ended with status {result.exit_code}: {tail.strip()[-500:]}"), False

    def _export(self, session: Session, span: WindowSpan) -> Step:
        """Write the batch for the host: the pending probes of findings first (a few, and what an expert waits for), then the pending intents of cases, one
        entry per distinct text. Whatever an earlier round left is cleared first."""
        probes = store.pending_probe_texts(session, limit=self._round_limit)
        lost = [item for item in probes if item.text is None]
        if lost:
            store.mark_probes_poisoned(session, probes=lost, reason=store.POISON_FINDING_MISSING)
        changed_probes = [item for item in probes if item.text is not None and not item.matches]
        if changed_probes:
            store.mark_probes_poisoned(session, probes=changed_probes, reason=POISON_DIGEST_MISMATCH)
        usable_probes = [item for item in probes if item.matches]
        pending = store.pending_intent_texts(session, limit=max(self._round_limit - len(probes), 0)) if len(probes) < self._round_limit else []
        changed = [item for item in pending if not item.matches]
        if changed:
            store.mark_poisoned(session, intent_ids=[item.intent_id for item in changed], reason=POISON_DIGEST_MISMATCH)
        usable = [item for item in pending if item.matches]
        texts = [*(item.text for item in usable_probes if item.text is not None), *(item.text for item in usable)]
        if not texts:
            self._set(session, STATE_CLOSED)
            return Step(STATE_CLOSED, True, "nothing left to encode")
        try:
            self._exchange.clear()
            self._exchange.write_request(build_request(texts), deadline_epoch=int(span.closes_at.timestamp()))
        except OSError as exc:
            return self._skip(session, "export_failed", f"the exchange directory refused the batch: {exc}")
        return Step(STATE_ENCODING, False, f"{len(usable)} intents and {len(usable_probes)} probes exported")

    def _import(self, session: Session, span: WindowSpan | None) -> tuple[Step, bool]:
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
        _log.info(
            "a round of vectors was imported: %d stored, %d over the token limit (poisoned), %d refused (retried), %d unanswered, %d for forgotten cases; "
            "probes of findings: %d stored, %d poisoned",
            outcome.done, outcome.poisoned, outcome.retried, outcome.missing, outcome.skipped_forgotten, outcome.probes_done, outcome.probes_poisoned)
        stored = outcome.done + outcome.probes_done + outcome.probes_poisoned > 0    # what the «Прецеденты» pass waits for moved
        # Another round only after a clean one that made progress: a round that stored nothing, or had a vector refused or a text unanswered, ends the
        # window, so an encoder that is wrong is tried once a night (the attempts of an intent count nights) and not until it is poisoned by morning.
        clean = outcome.retried == 0 and outcome.missing == 0 and (outcome.done + outcome.poisoned + outcome.probes_done + outcome.probes_poisoned) > 0
        if clean and span is not None and (span.closes_at - self._moment).total_seconds() >= MIN_ROUND_SECONDS:
            following = self._export(session, span)
            if following.state == STATE_ENCODING:
                return Step(STATE_ENCODING, False, "imported; the next round is out"), stored
            return following, stored
        self._set(session, STATE_CLOSED)
        _log.info("the vector window closed")
        return Step(STATE_CLOSED, True, "imported"), stored

    # -- the loud skip -----------------------------------------------------------------------------------------

    def _skip(self, session: Session, reason: str, detail: str) -> Step:
        """The window did not take place. Journalled with its reason, shown to the administrator and logged at ERROR: the intents stay."""
        self._set(session, STATE_SKIPPED, reason)
        _log.error("the vector window was skipped (%s): %s; the queued intents wait for the next night", reason, detail)
        return Step(STATE_SKIPPED, True, reason)
