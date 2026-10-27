"""The comparison loop's brain, hosted by the worker (`CMP-WORK-01`, ADR-0025 decisions 4, 6, 23).

The worker's dispatch loop asks :meth:`ComparisonWorkRunner.claim` only when it found no Run to
hand a slot; the runner then decides, from the database, whether it may claim at all:

1. the module set (``AUDITMANAGER_COMPARISON_MODULES``) names no module -> nothing is claimed;
2. ``execution_control.paused`` -> nothing is claimed;
3. a Run is claimable -> nothing is claimed (strict priority; an item in flight is never
   preempted, so a Run waits at most one item: one page or one pair);
4. otherwise the strongest queued item of an enabled module and of a kind this build has a handler
   for is leased to the worker.

A module that is off therefore *pauses* its queued work: the items stay ``queued`` and nothing
else changes, so turning the module back on resumes them with no un-pause to forget. Reclaim of
expired leases runs whatever the module set says, so a worker that died holding an item never
blocks a project erase because a module happens to be off.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.work.errors import HandlerRegistryError, UnhandledKindError
from auditmanager.comparison.work.gates import ClaimGates, default_gates
from auditmanager.comparison.work.heartbeat import ItemHeartbeat
from auditmanager.comparison.work.model import (
    ATTEMPT_WATCHDOG_SECONDS,
    HEARTBEAT_SECONDS,
    REASON_HANDLER_ERROR,
    REASON_NO_HANDLER,
    REASON_OUTCOME_INVALID,
    REASON_WATCHDOG,
    Completed,
    Failed,
    Outcome,
    SpendSettler,
    WorkItem,
    Yielded,
)
from auditmanager.comparison.work.registry import HandlerRegistry
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["ComparisonWorkRunner"]

_log = logging.getLogger(__name__)
_FENCED = frozenset({ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID})


class ComparisonWorkRunner:
    """Claim, run, end and reclaim comparison work for one worker process."""

    def __init__(
        self, sessions: "sessionmaker[Session]", *, registry: HandlerRegistry,
        modules: frozenset[str], repository: ComparisonWorkRepository | None = None,
        gates: ClaimGates | None = None, spend_settlers: Sequence[SpendSettler] = (),
        heartbeat_seconds: float = HEARTBEAT_SECONDS,
        watchdog_seconds: float = ATTEMPT_WATCHDOG_SECONDS,
    ) -> None:
        self._sessions = sessions
        self._registry = registry
        self._modules = frozenset(modules)
        self._repository = repository or ComparisonWorkRepository()
        self._gates = gates or default_gates()
        self._settlers = tuple(spend_settlers)
        self._heartbeat_seconds = heartbeat_seconds
        self._watchdog_seconds = watchdog_seconds

    @property
    def modules(self) -> frozenset[str]:
        return self._modules

    @property
    def kinds(self) -> frozenset[str]:
        return self._registry.kinds

    @property
    def repository(self) -> ComparisonWorkRepository:
        return self._repository

    def verify(self) -> None:
        """Refuse (``UnhandledKindError``) while an enabled module has live items of a kind this
        build has no handler for. Called before the worker registers."""
        if not self._modules:
            return
        with self._sessions() as session:
            live = self._repository.live_kinds(session, modules=self._modules)
        unhandled = live - self._registry.kinds
        if unhandled:
            raise UnhandledKindError(unhandled)

    def claim(self, worker_id: str) -> WorkItem | None:
        """Lease one item to ``worker_id`` if the gates allow it; ``None`` otherwise."""
        if not self._modules or not self._registry.kinds:
            return None
        with self._sessions() as session:
            if self._gates.paused(session):
                session.rollback()
                return None
            yields_to_a_run = self._gates.run_claimable(session)
            # `next_queued_run` locks the hinted Run's row for the transaction: release it now.
            session.rollback()
            if yields_to_a_run:
                return None
            item = self._repository.claim(
                session, worker_id=worker_id, modules=self._modules, kinds=self._registry.kinds,
            )
            session.commit()
        return item

    def execute(self, item: WorkItem) -> str | None:
        """Run the item's handler under a heartbeat and end the attempt with its outcome.

        Answers the item's new state, or ``None`` when the attempt had lost its lease (the handler's
        result is dropped and nothing is written: the reclaim already decided what happens to the
        item). A handler that raises ends the attempt ``failed`` with a retryable
        ``handler_error``; a handler that returns something else than an outcome, ``failed``
        with ``handler_outcome_invalid``. Neither is silent: both are logged.
        """
        heartbeat = ItemHeartbeat(
            self._sessions, self._repository, item,
            interval_seconds=self._heartbeat_seconds, watchdog_seconds=self._watchdog_seconds,
            fence=self._fence,
        )
        heartbeat.start()
        outcome: Outcome
        try:
            outcome = self._registry.handler(item.kind).run(item)
        except HandlerRegistryError:
            _log.error("comparison work %s: no handler for kind %s", item.work_id, item.kind)
            outcome = Failed(REASON_NO_HANDLER)
        except Exception:
            _log.exception(
                "comparison work %s (kind %s, attempt %d): the handler raised",
                item.work_id, item.kind, item.attempt_no,
            )
            outcome = Failed(REASON_HANDLER_ERROR, retry=True)
        finally:
            heartbeat.stop()
        if not isinstance(outcome, (Completed, Failed, Yielded)):
            _log.error(
                "comparison work %s (kind %s): the handler returned %s, not an outcome",
                item.work_id, item.kind, type(outcome).__name__,
            )
            outcome = Failed(REASON_OUTCOME_INVALID)
        try:
            with self._sessions() as session:
                state = self._repository.finish(session, item.authority, outcome)
                session.commit()
        except DomainError as refusal:
            if refusal.code in _FENCED:
                _log.warning(
                    "comparison work %s (kind %s, attempt %d) no longer holds its lease; "
                    "its outcome is dropped and nothing was written",
                    item.work_id, item.kind, item.attempt_no,
                )
                return None
            raise
        return state

    def reclaim(self) -> int:
        """Fence expired leases, whatever the module set says. Answers how many attempts it ended."""
        with self._sessions() as session:
            recovered = self._repository.reclaim_expired(session, spend_settlers=self._settlers)
            session.commit()
        return recovered

    def _fence(self, session: Session, attempt_id: str) -> int:
        """The watchdog's forced reclaim of one attempt (see :class:`ItemHeartbeat`)."""
        return self._repository.reclaim_expired(
            session, spend_settlers=self._settlers, force_attempt_id=attempt_id,
            reason=REASON_WATCHDOG,
        )
