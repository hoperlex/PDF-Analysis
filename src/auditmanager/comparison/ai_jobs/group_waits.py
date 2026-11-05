"""The wait sweep of comparison AI jobs admitted by a group (`EXEC2-FOLLOWUP-01`, ADR-0026 decision 15, ruling `R-149c`).

A comparison job admitted by a rule or a group binds to a member at its **first call**. While no member is eligible the call records why the
job waits (``wait_reason``, since when) and is refused ``connection_busy``, so its item is asked again after
:data:`~auditmanager.comparison.spend.errors.BUSY_RETRY_SECONDS`. Before this sweep the wait was kept true, and its offline expiry -- the job ends
``failed`` / ``no_executor_online`` once it has waited for a runner longer than ``AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS`` -- was decided **only
inside that call**: a job none of whose items was being retried stayed ``runner_offline`` for ever, and a runner that had come back left the
stored reason as it was.

:meth:`ComparisonGroupWaitSweep.sweep` is the Run side's group-wait sweep (``jobs.repository.JobRepository.refresh_group_waits``) for this other
kind of work, with the same shape:

* **one pass walks every candidate**, oldest first, ``batch_size`` per read (a keyset on ``(created_at, job_id)``), so no job stays hidden
  behind the first page. A candidate is a ``pending`` job that is **queued or running**, whatever reason it stores; a paused job waits for a
  person and an ended one for nobody, so neither is read nor written, and ``needs_reconsent`` (a pause's wait) is never touched;
* **the wait is kept true**: from the first issue of each member of the job's group revision
  (:func:`~auditmanager.comparison.spend.dispatch.group_wait_reason`, the Run side's reading) the sweep derives ``None`` when some member can take
  the job, ``executor_at_capacity`` when none can but some is only full, and ``runner_offline`` otherwise, and writes it when it is not the one
  stored. A changed reason restarts the clock (``set_wait``), so **the offline clock starts at the sweep's own observation**: a runner that came
  back for one pass, even at minute 29, clears the wait, and the next time the group goes dark the wait begins again;
* **a job ends only when ``runner_offline`` has held without a break for longer than the limit**: the derived reason equals the stored one, both
  are ``runner_offline``, and the stored wait is older than the limit. Waiting for capacity never ends a job;
* **each job is its own transaction**: its items are locked first and then its row (the order every handler and command takes them, so the sweep
  cannot deadlock with a handler that holds an item and wants the job), both ``SKIP LOCKED`` -- a job a handler is in the middle of is left for a
  later pass, never waited for. Everything is decided under that lock, on the locked row and a fresh reading of the group;
* **the outcome is the in-call expiry's, method by method**. Every handler answers a ``CallRefused(no_executor_online)`` with
  ``ComparisonAiJobService.pause_for_spend`` -- which ends the job ``failed`` with that reason, cancels its live items and clears its wait --
  and three methods do something more in the same transaction. :class:`EndedWithoutExecutor` is that something, a hook per method that the
  sweep calls around the ending:

  ===============  ==============================================================================================================
  ``pair_check``   nothing more (``ai_pairs/handler.py``); ``spec`` likewise (``specification/method.py``)
  ``sheet_changes``  the pair the call was at moves ``running -> queued`` (``ai_sheets/handler.py``)
  ``report``       ``sync_report`` moves the report row to the state the job implies (``report/handler.py``)
  ``stage_review``  the unit at work fails, the run and its step fail, the pending units are cancelled, **then** the job ends
                   (``stage_ai/runtime.py`` ``_failed``)
  ===============  ==============================================================================================================

  The hooks are built where the methods are known (``comparison/group_wait_hooks.py``). A method with neither a hook nor a place in
  :data:`ENDED_BY_PAUSE_ONLY` is **not swept** -- its jobs are never candidates -- rather than ended differently from its own handler;
* **it is isolated from every other sweep**: a job whose transaction fails is rolled back, counted and logged by the category of the failure
  (never its text, which may quote a row), and the pass goes on with the next job.

It reads and writes nothing about a connection: no group or connection lock is taken, because nothing is bound here. The caller's transaction is
not used; the sweep opens its own sessions from the factory it is given.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.ai_jobs.model import AiJobRecord, WAIT_RUNNER_OFFLINE
from auditmanager.comparison.ai_jobs.repository import AiJobRepository, PendingWait
from auditmanager.comparison.ai_jobs.service import ComparisonAiJobService
from auditmanager.comparison.spend.dispatch import group_wait_reason, member_issues
from auditmanager.comparison.spend.errors import REASON_NO_EXECUTOR_ONLINE

__all__ = [
    "ENDED_BY_PAUSE_ONLY",
    "GROUP_WAIT_BATCH",
    "ComparisonGroupWaitSweep",
    "ComparisonGroupWaits",
    "EndedWithoutExecutor",
]

_log = logging.getLogger(__name__)

#: How many candidate jobs the sweep reads per page. A pass walks every candidate, page after page, so this bounds one read and never the
#: number of jobs a pass looks at (the Run sweep's ``GROUP_WAIT_BATCH``).
GROUP_WAIT_BATCH: Final[int] = 200
#: The methods whose in-call answer to ``no_executor_online`` is ``pause_for_spend`` and nothing else (the table in the module doc). A test
#: holds the set to the methods that have no hook.
ENDED_BY_PAUSE_ONLY: Final[frozenset[str]] = frozenset({"pair_check", "spec"})

#: ``(session, job)``: runs in the transaction that ends the job, with the job as it was read under its lock.
JobHook = Callable[[Session, AiJobRecord], None]


@dataclass(frozen=True, slots=True)
class EndedWithoutExecutor:
    """What a method does besides ending the job when its call is refused ``no_executor_online``. ``before`` runs ahead of the job's ending and
    ``after`` once the job has ended -- each in the order its own handler takes -- both in the one transaction that ends the job."""

    before: JobHook | None = None
    after: JobHook | None = None


@dataclass(frozen=True, slots=True)
class ComparisonGroupWaits:
    """What one pass did: jobs ended ``no_executor_online`` (``expired``), jobs whose wait was written or cleared because it had stopped being
    true (``updated``), jobs left alone because a handler holds them or they no longer qualified (``skipped``), and jobs whose transaction
    failed (``failed``). A candidate whose stored wait is already true and has not run out is none of these."""

    expired: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0


_ENDED, _UPDATED, _UNCHANGED, _SKIPPED = "ended", "updated", "unchanged", "skipped"


class ComparisonGroupWaitSweep:
    """Keeps the wait of the comparison jobs admitted by a group true, and ends the ones nobody can serve. Holds no state between passes."""

    __slots__ = ("_sessions", "_jobs", "_service", "_hooks", "_methods", "_batch_size")

    def __init__(
        self, session_factory: "sessionmaker[Session]", *, hooks: Mapping[str, EndedWithoutExecutor] | None = None,
        repository: AiJobRepository | None = None, service: ComparisonAiJobService | None = None,
        batch_size: int = GROUP_WAIT_BATCH,
    ) -> None:
        if batch_size < 1:
            raise ValueError("a page of waiting jobs holds at least one")
        self._sessions = session_factory
        self._jobs = repository or AiJobRepository()
        #: The job layer's own answer to ``no_executor_online``: the one place a refusal reaches a job (the handlers call the same method).
        self._service = service or ComparisonAiJobService(
            session_factory, methods=[], comparison_modules="versions", provider_mode="live", repository=self._jobs,
        )
        self._hooks = dict(hooks or {})
        #: Only these are swept: a method this sweep cannot end the way its own handler does is excluded, not ended differently.
        self._methods = tuple(sorted(ENDED_BY_PAUSE_ONLY | self._hooks.keys()))
        self._batch_size = batch_size

    @property
    def methods(self) -> tuple[str, ...]:
        """The methods whose jobs this sweep reads and may end."""
        return self._methods

    def sweep(self, offline_wait_seconds: float) -> ComparisonGroupWaits:
        """One pass. ``offline_wait_seconds`` is ``AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS`` as the worker read it (positive)."""
        limit = float(offline_wait_seconds)
        if not limit > 0:
            raise ValueError("the offline wait of a group is positive")
        counts = {_ENDED: 0, _UPDATED: 0, _SKIPPED: 0, "failed": 0}
        readings: dict[str, list[str | None] | None] = {}
        after: tuple[datetime, str] | None = None
        while True:
            with self._sessions() as session:
                page = self._jobs.pending_waits(
                    session, methods=self._methods, offline_seconds=limit, batch_size=self._batch_size, after=after,
                )
                session.rollback()  # a read: nothing to keep, and no snapshot held while the jobs are decided one by one
            for row in page:
                after = (row.created_at, row.job_id)
                try:
                    if not self._needs_a_decision(row, readings):
                        continue
                    outcome = self._decide(row.job_id, limit)
                except Exception as failure:  # noqa: BLE001 - one job's failure must not stop the pass or any other sweep
                    counts["failed"] += 1
                    _log.error(
                        "comparison group wait: a job could not be decided (%s); it is tried again at the next pass",
                        type(failure).__name__,
                    )
                    continue
                if outcome != _UNCHANGED:
                    counts[outcome] += 1
            if len(page) < self._batch_size:
                return ComparisonGroupWaits(
                    expired=counts[_ENDED], updated=counts[_UPDATED], skipped=counts[_SKIPPED], failed=counts["failed"],
                )

    # -- one candidate ------------------------------------------------------------------------------------------------------------

    def _reading(self, group_revision_id: str, readings: dict[str, list[str | None] | None]) -> list[str | None] | None:
        """The first issue of each member of a group revision, read once per pass (the jobs of one group share it). ``None`` for a revision that
        cannot be read."""
        if group_revision_id not in readings:
            from auditmanager.executors.public import group_revision_of

            with self._sessions() as session:
                revision = group_revision_of(session, group_revision_id)
                readings[group_revision_id] = None if revision is None else member_issues(session, revision)
                session.rollback()
        return readings[group_revision_id]

    def _needs_a_decision(self, row: PendingWait, readings: dict[str, list[str | None] | None]) -> bool:
        """The cheap look, with no lock: is the stored wait true, and has it not run out? The decision itself is made again under the lock."""
        issues = self._reading(row.group_revision_id, readings)
        if issues is None:
            return False
        derived = group_wait_reason(issues)
        return derived != row.wait_reason or (derived == WAIT_RUNNER_OFFLINE and row.expired)

    def _decide(self, job_id: str, limit: float) -> str:
        """Decide one job in a transaction of its own, under the locks, on the locked row and a fresh reading of its group."""
        from auditmanager.executors.public import group_revision_of

        with self._sessions() as session:
            # Items first, then the job row: the order every handler and command takes them. A session that is closed without a commit
            # releases its locks and writes nothing, so every early answer below simply returns.
            if not self._jobs.lock_live_items(session, job_id):
                return _SKIPPED
            locked = self._jobs.lock_pending_wait(session, job_id, offline_seconds=limit)
            if locked is None or locked.method not in self._methods:
                return _SKIPPED
            revision = group_revision_of(session, locked.group_revision_id)
            if revision is None:
                return _SKIPPED
            derived = group_wait_reason(member_issues(session, revision))
            if derived != locked.wait_reason:
                # The stored wait is not true any more (a runner is back, a place is full, the group went dark): write what is, which
                # restarts the clock when the reason changed.
                if derived is None:
                    self._jobs.clear_wait(session, job_id)
                else:
                    self._jobs.set_wait(session, job_id, derived)
                session.commit()
                return _UPDATED
            if not (derived == WAIT_RUNNER_OFFLINE and locked.expired):
                return _UNCHANGED
            job = self._jobs.get(session, job_id)
            if job is None:
                return _SKIPPED
            hook = self._hooks.get(locked.method)
            if hook is not None and hook.before is not None:
                hook.before(session, job)
            if not self._service.pause_for_spend(session, job_id, REASON_NO_EXECUTOR_ONLINE):
                return _SKIPPED
            if hook is not None and hook.after is not None:
                hook.after(session, job)
            session.commit()
            return _ENDED
