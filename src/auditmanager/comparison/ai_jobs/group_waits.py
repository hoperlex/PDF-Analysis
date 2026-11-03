"""The offline sweep of comparison AI jobs admitted by a group (`EXEC2-FOLLOWUP-01`, ADR-0026 decision 15, ruling `R-149c`).

A comparison job admitted by a rule or a group binds to a member at its **first call**. While no member is eligible the call records
``wait_reason = runner_offline`` on the job (:mod:`auditmanager.comparison.spend.dispatch`, ``_wait``) and is refused ``connection_busy``,
so its item is asked again after :data:`~auditmanager.comparison.spend.errors.BUSY_RETRY_SECONDS`. Before this sweep the offline expiry --
the job ends ``failed`` / ``no_executor_online`` once it has waited for a runner longer than ``AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS`` --
was decided **only inside that call**: a job none of whose items was being retried (its items claimed behind a Run, waiting in a retry
the worker has not reached, or lost to a drain) stayed ``runner_offline`` for ever.

:meth:`ComparisonGroupWaitSweep.expire_offline` is the Run side's group-wait sweep (``jobs.repository.JobRepository.refresh_group_waits``)
for this other kind of work, with the same shape:

* **one pass walks every candidate**, oldest first, ``batch_size`` per read (a keyset on ``(created_at, job_id)``), so no job stays hidden
  behind the first page; the candidates are the live ``pending`` jobs whose wait is ``runner_offline`` and older than the limit;
* **each job is its own transaction**: its items are locked first and then its row (the order every handler and command takes them, so
  the sweep cannot deadlock with a handler that holds an item and wants the job), both ``SKIP LOCKED`` -- a job a handler is in the
  middle of is left for a later pass, never waited for;
* **the expiry is decided under the lock, from the locked row**: the job must still be ``pending`` and queued or running, still waiting
  for ``runner_offline``, for longer than the limit -- and its group must still have **no eligible member** (the in-call reading,
  :func:`~auditmanager.comparison.spend.dispatch.has_eligible_member`). A runner that came back since the wait was written
  means the job's next call binds, so the job is left alone;
* **the outcome is the in-call expiry's, by the same function**: ``ComparisonAiJobService.pause_for_spend(job, "no_executor_online")``,
  which ends the job ``failed`` with that reason, cancels its live items and clears its wait. It never writes a wait, and a job that has
  ended is never touched (the candidate read and the lock both name the live states, and the job's own edge names them again);
* **it is isolated from every other sweep**: a job whose transaction fails is rolled back, counted and logged by the category of the failure
  (never its text, which may quote a row), and the pass goes on with the next job.

It reads and writes nothing about a connection: no group or connection lock is taken, because nothing is bound here. The caller's
transaction is not used; the sweep opens its own sessions from the factory it is given.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.ai_jobs.model import WAIT_RUNNER_OFFLINE
from auditmanager.comparison.ai_jobs.repository import AiJobRepository
from auditmanager.comparison.ai_jobs.service import ComparisonAiJobService
from auditmanager.comparison.spend.dispatch import has_eligible_member
from auditmanager.comparison.spend.errors import REASON_NO_EXECUTOR_ONLINE

__all__ = ["GROUP_WAIT_BATCH", "ComparisonGroupWaitSweep", "ComparisonGroupWaits"]

_log = logging.getLogger(__name__)

#: How many candidate jobs the sweep reads per page. A pass walks every candidate, page after page, so this bounds one read and never the
#: number of jobs a pass looks at (the Run sweep's ``GROUP_WAIT_BATCH``).
GROUP_WAIT_BATCH: Final[int] = 200


@dataclass(frozen=True, slots=True)
class ComparisonGroupWaits:
    """What one pass did: jobs ended ``no_executor_online`` (``expired``), jobs left alone because they no longer qualify, a handler holds
    them, or a member is eligible again (``skipped``), and jobs whose transaction failed (``failed``)."""

    expired: int = 0
    skipped: int = 0
    failed: int = 0


class ComparisonGroupWaitSweep:
    """Ends the comparison jobs whose group has had no eligible member for longer than the offline wait. Holds no state between passes."""

    __slots__ = ("_sessions", "_jobs", "_service", "_batch_size")

    def __init__(
        self, session_factory: "sessionmaker[Session]", *, repository: AiJobRepository | None = None,
        service: ComparisonAiJobService | None = None, batch_size: int = GROUP_WAIT_BATCH,
    ) -> None:
        if batch_size < 1:
            raise ValueError("a page of waiting jobs holds at least one")
        self._sessions = session_factory
        self._jobs = repository or AiJobRepository()
        #: The job layer's own answer to ``no_executor_online``: the one place a refusal reaches a job (the handlers call the same method).
        self._service = service or ComparisonAiJobService(
            session_factory, methods=[], comparison_modules="versions", provider_mode="live", repository=self._jobs,
        )
        self._batch_size = batch_size

    def expire_offline(self, offline_wait_seconds: float) -> ComparisonGroupWaits:
        """One pass: end every candidate job that is still over the limit under its lock and has no eligible member. ``offline_wait_seconds``
        is ``AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS`` as the worker read it (positive)."""
        limit = float(offline_wait_seconds)
        if not limit > 0:
            raise ValueError("the offline wait of a group is positive")
        expired = skipped = failed = 0
        after: tuple[datetime, str] | None = None
        while True:
            with self._sessions() as session:
                page = self._jobs.offline_waiting(
                    session, offline_seconds=limit, batch_size=self._batch_size, after=after,
                )
                session.rollback()  # a read: nothing to keep, and no snapshot held while the jobs are decided one by one
            for created_at, job_id in page:
                after = (created_at, job_id)
                try:
                    ended = self._expire_one(job_id, limit)
                except Exception as failure:  # noqa: BLE001 - one job's failure must not stop the pass or any other sweep
                    failed += 1
                    _log.error(
                        "comparison group wait: a job could not be decided (%s); it is tried again at the next pass",
                        type(failure).__name__,
                    )
                    continue
                if ended:
                    expired += 1
                else:
                    skipped += 1
            if len(page) < self._batch_size:
                return ComparisonGroupWaits(expired=expired, skipped=skipped, failed=failed)

    def _expire_one(self, job_id: str, limit: float) -> bool:
        """Decide one job in a transaction of its own. ``True`` when it was ended."""
        from auditmanager.executors.public import group_revision_of

        with self._sessions() as session:
            # Items first, then the job row: the order every handler and command takes them. A session that is closed without a commit
            # releases its locks and writes nothing, so every early answer below simply returns.
            if not self._jobs.lock_live_items(session, job_id):
                return False
            locked = self._jobs.lock_offline_wait(session, job_id, offline_seconds=limit)
            if locked is None or locked.wait_reason != WAIT_RUNNER_OFFLINE or not locked.expired:
                return False
            revision = group_revision_of(session, locked.group_revision_id)
            if revision is None or has_eligible_member(session, revision):
                return False
            if not self._service.pause_for_spend(session, job_id, REASON_NO_EXECUTOR_ONLINE):
                return False
            session.commit()
            return True
