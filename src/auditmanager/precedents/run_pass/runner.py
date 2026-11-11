"""The «Прецеденты» pass over a run's findings (`ADR-0029` decisions 4 to 6, plan-v5 sections 2 and 5).

For each run that finished with findings the pass does four things, in one transaction and under the lock of the run's own pass row, so two workers never
compute one run twice:

1. **Probes.** The text of each finding, as the view ``finding_v1``, is queued for the night encoder under the key ``(run_id, finding_uid, text_sha256)``
   (``decision_memory_probe``): the window of the vectors (`EMBED-01`) encodes pending probes with the intents of the cases, in the same rounds.
2. **Waiting.** A finding whose probe has no vector yet has **no answer**: «Недоступно», never a search by words. While any probe is pending the pass
   row says ``pending``; a probe the encoder refused for its length is ``poisoned`` and the finding stays without an answer for good.
3. **The rules.** For each finding with a vector, an exact scan of the active cases of its section (`reads.neighbours`) and the core's ``evaluate``, with
   the critic's part read from the saved extended review of the run (``critic_input``: the AI critic of plan v3, the deterministic critic of plan v2),
   the owner's stop words and the thresholds in force (a section switched on is computed at the analogous threshold its replay report chose).
4. **The result.** One row per finding at a revision (``decision_memory_precedent_advice``), the run's pass row moved to ``done`` (or ``pending`` while
   probes wait). **Idempotent:** a result equal to the latest revision's is not written again; a different one is a whole new set at ``revision + 1``.

The pass is called two ways. ``__call__`` is the worker's housekeeping tick (throttled): it takes runs that finished and have no pass row, and the runs that
wait for vectors. :meth:`PrecedentPass.after_import` is the hook of the vector window (``VectorWindowPass(after_import=...)``), run after a round of vectors
is stored: it does the same and also computes **again** the fresh runs it has finished (their neighbours may have grown since), the nightly recomputation.

Nothing here decides for an expert, writes a verdict, calls a model or opens a network connection (`ADR-0029` decision 2).
"""

from __future__ import annotations

import logging
import time as _time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.precedents import settings as journal
from auditmanager.precedents.run_pass import evaluation, reads, store
from auditmanager.precedents.run_pass.critic_input import CriticPlan, critic_projection, link, read_critic_plan

__all__ = ["FRESH_DAYS", "PassOutcome", "PrecedentPass"]

_log = logging.getLogger(__name__)

#: A run is fresh for this many days after it finished: the nightly pass computes it again, an older one keeps its last revision (it is read as stored,
#: or evaluated at read time once the memory has moved).
FRESH_DAYS: Final[int] = 14
#: Runs one call takes: a backlog is taken over a few ticks, never in one long transaction.
BATCH: Final[int] = 10
REFRESH_BATCH: Final[int] = 50

OUTCOME_COMPUTED: Final[str] = "computed"
OUTCOME_UNCHANGED: Final[str] = "unchanged"
OUTCOME_WAITING: Final[str] = "waiting_for_vectors"
OUTCOME_NOT_READY: Final[str] = "not_ready"
OUTCOME_NO_FINDINGS: Final[str] = "no_findings"
OUTCOME_FAILED: Final[str] = "failed"


class _CriticUnreadable(Exception):
    """The saved extended review of the run could not be read. The pass fails loudly: a review it could not read is not «no review»."""


@dataclass(frozen=True, slots=True)
class PassOutcome:
    """What one run's computation did. ``changed`` is true when the pass row or the advice moved (a new revision, a new state)."""

    run_id: str
    status: str
    changed: bool
    revision: int | None = None


def _same(stored: Mapping[str, store.StoredAdvice], rows: list[dict[str, Any]]) -> bool:
    if set(stored) != {row["finding_uid"] for row in rows}:
        return False
    for row in rows:
        old = stored[row["finding_uid"]]
        if (old.label, old.critic_reviewed, list(old.hint_codes), dict(old.votes)) != (
                row["label"], row["critic_reviewed"], list(row["hint_codes"]), row["votes"]):
            return False
    return True


class PrecedentPass:
    """``__call__() -> int`` as the worker's housekeeping loop calls its passes: the number of runs whose pass moved (0 when idle).

    ``read_extended_review`` is the saved extended review of a run (``runs.public.read_extended_review(sessions, blob_store, run_id)``, which the composition
    root closes over its stores): ``{"status": ..., "result": ...}``. It is a callable so that this context reads no artifact store of its own."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        read_extended_review: Callable[[str], Mapping[str, Any] | None],
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
        interval_seconds: float = 60.0,
        fresh_days: int = FRESH_DAYS,
        batch: int = BATCH,
    ) -> None:
        if interval_seconds < 0 or fresh_days < 1 or batch < 1:
            raise ValueError("a pass needs a non-negative interval, at least one fresh day and a batch of at least one run")
        self._sessions = session_factory
        self._read_extended = read_extended_review
        self._clock = clock or (lambda: datetime.now(UTC))
        self._monotonic = monotonic or _time.monotonic
        self._interval = interval_seconds
        self._fresh_days = fresh_days
        self._batch = batch
        self._next_at: float | None = None

    # -- the two ways the pass is called ---------------------------------------------------------------------------------

    def __call__(self) -> int:
        now = self._monotonic()
        if self._next_at is not None and now < self._next_at:
            return 0
        self._next_at = now + self._interval
        return self.run_once(refresh=False)

    def after_import(self) -> None:
        """The hook of the vector window: runs after a round of vectors is committed, in no transaction of the window. Computes what waits for vectors and
        the fresh runs again. A failure is the caller's to log (the window logs it and the next look repeats)."""
        self.run_once(refresh=True)

    def run_once(self, *, refresh: bool = False) -> int:
        since = self._clock() - timedelta(days=self._fresh_days)
        with self._sessions() as session:
            wanted = [
                *reads.runs_to_schedule(session, since=since, limit=self._batch),
                *reads.unfinished_runs(session, limit=self._batch),
                *(reads.refreshable_runs(session, since=since, limit=REFRESH_BATCH) if refresh else ()),
            ]
        moved = 0
        for run_id in dict.fromkeys(wanted):
            if self.compute_run(run_id).changed:
                moved += 1
        return moved

    # -- one run -----------------------------------------------------------------------------------------------------------

    def compute_run(self, run_id: str) -> PassOutcome:
        """Compute one run now. A defect is recorded on the run's pass row (``failed`` with a code) and logged at ERROR; it is never swallowed into an
        empty answer."""
        try:
            return self._compute(run_id)
        except _CriticUnreadable:
            _log.exception("the saved extended review of run %s could not be read; its precedents pass failed", run_id)
            return self._fail(run_id, store.FAILURE_CRITIC_UNREADABLE)
        except Exception:  # noqa: BLE001 - a run's pass that cannot finish is recorded and the next run goes on
            _log.exception("the precedents pass of run %s failed", run_id)
            return self._fail(run_id, store.FAILURE_PASS_ERROR)

    def _fail(self, run_id: str, code: str) -> PassOutcome:
        try:
            with self._sessions() as session:
                if reads.run_facts(session, run_id) is None:
                    return PassOutcome(run_id, OUTCOME_FAILED, False)
                store.mark_failed(session, run_id, code=code)
                session.commit()
        except Exception:  # noqa: BLE001 - nothing more can be done from here
            _log.exception("the failure of the precedents pass of run %s could not be recorded", run_id)
            return PassOutcome(run_id, OUTCOME_FAILED, False)
        return PassOutcome(run_id, OUTCOME_FAILED, True)

    def _projections(self, session: Session, run_id: str, findings: list[reads.PassFinding], kept: Mapping[str, Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
        """The critic's part for each finding: what the stored advice already holds (the saved review of a finished run does not change), and for the
        findings it holds nothing for, read from the artifact."""
        projections: dict[str, Mapping[str, Any]] = {uid: part for uid, part in kept.items() if isinstance(part, Mapping)}
        missing = [finding for finding in findings if finding.finding_uid not in projections]
        if missing:
            try:
                plan: CriticPlan = read_critic_plan(self._read_extended(run_id))
            except Exception as exc:
                raise _CriticUnreadable(run_id) from exc
            for finding in missing:
                linked = link(plan, extended_observation_refs=finding.extended_observation_refs, category=finding.category, finding_text=finding.finding_text)
                projections[finding.finding_uid] = critic_projection(plan, linked)
        return projections

    def _compute(self, run_id: str) -> PassOutcome:
        now = self._clock()
        with self._sessions() as session:
            run = reads.run_facts(session, run_id)
            if run is None or not run.finished:
                return PassOutcome(run_id, OUTCOME_NOT_READY, False)
            findings = list(reads.findings_of_run(session, run_id))
            if not findings:
                return PassOutcome(run_id, OUTCOME_NO_FINDINGS, False)
            row = store.ensure_run_row(session, run_id)
            started = store.database_now(session)
            store.ensure_probes(session, run_id, findings)
            probes = reads.probe_rows(session, run_id)
            done = {uid for uid, probe in probes.items() if probe.state == "done"}
            waiting = any(probe.state == "pending" for probe in probes.values())
            state = store.STATE_PENDING if waiting else store.STATE_DONE
            latest = store.latest_revision(session, run_id)
            if not done:
                changed = row.state != state or row.failure_code is not None
                if changed:
                    store.set_run_state(session, run_id, state=state, revision=row.revision)
                session.commit()
                return PassOutcome(run_id, OUTCOME_WAITING if waiting else OUTCOME_UNCHANGED, changed, latest)

            stored = {} if latest is None else store.advice_at(session, run_id, latest)
            kept = {uid: item.votes.get("critic") for uid, item in stored.items()}
            projections = self._projections(session, run_id, findings, kept)
            place = reads.version_place(session, run.version_uid)
            base = journal.read_thresholds(session)
            thresholds, _on = evaluation.effective_thresholds(base, place.section, journal.read_section_labels(session))
            results = evaluation.evaluate_run(
                session, run=run, place=place, findings=findings, projections=projections, now=now, thresholds=thresholds,
                stop_words=journal.read_stop_words(session), only=sorted(done))
            rows = [evaluation.row_of(results[uid]) for uid in sorted(results)]
            if latest is not None and _same(stored, rows):
                revision, wrote = latest, False
            else:
                revision, wrote = (1 if latest is None else latest + 1), True
                store.write_advice(session, run_id, revision, rows, computed_at=started)
            changed = wrote or row.state != state or row.revision != revision or row.failure_code is not None
            if changed:
                store.set_run_state(session, run_id, state=state, revision=revision)
            session.commit()
            return PassOutcome(run_id, OUTCOME_COMPUTED if wrote else OUTCOME_UNCHANGED, changed, revision)
