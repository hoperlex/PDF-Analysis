"""Durable Job/Attempt authority and the two external-effect journals.

This is the only writer of ``job``, ``attempt``, ``lease``,
``provider_call_effect`` and ``analysis_artifact_publication``.  The execution token is
never formatted into a message or returned by a public API; it is carried only by the
in-process :class:`AttemptAuthority` and compared for equality while the Job row is
locked by the publishing transaction.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AttemptId, JobId, LeaseId, ModelCallId
from auditmanager.storage.public import BlobDeclaration, BlobId, parse_blob_id
from auditmanager.jobs.events import append_execution_event

_INSERT_JOB = text(
    "INSERT INTO job (job_id, run_id, state) VALUES (:job_id, :run_id, 'queued')"
)
_LOCK_RUN = text("SELECT state FROM audit_run WHERE run_id = :run_id FOR UPDATE")
_LOCK_JOB = text(
    "SELECT job_id, state, current_attempt_id FROM job WHERE run_id = :run_id "
    "FOR UPDATE SKIP LOCKED"
)
_LOCK_JOB_WAIT = text(
    "SELECT job_id, state, current_attempt_id FROM job WHERE run_id = :run_id "
    "FOR UPDATE"
)
_NEXT_JOB = text(
    "SELECT j.run_id FROM job j JOIN audit_run r ON r.run_id = j.run_id "
    "WHERE j.state = 'queued' AND r.state IN ('queued', 'running') "
    "AND j.available_at <= statement_timestamp() "
    "AND NOT EXISTS (SELECT 1 FROM execution_control WHERE singleton AND paused) "
    "ORDER BY j.priority DESC, j.created_at, j.job_id LIMIT 1 "
    "FOR UPDATE OF r SKIP LOCKED"
)
_HEARTBEAT = text(
    "UPDATE lease SET heartbeat_at = statement_timestamp(), "
    "expires_at = statement_timestamp() + make_interval(secs => :lease_seconds) "
    "WHERE lease_id = :lease_id AND attempt_id = :attempt_id "
    "AND released_at IS NULL AND expires_at > statement_timestamp()"
)
#: `W54-WORKER-01` (R-105). One channel wakes every listening worker; the payload is
#: empty because the queue in PostgreSQL is the authority and a notification is a hint.
#: ``NOTIFY`` is transactional, so a worker is woken only after the accepting commit.
JOB_WAKEUP_CHANNEL = "auditmanager_job_wakeup"
_NOTIFY = text("SELECT pg_notify(:channel, '')")
_LOCK_WORKER_INTAKE = text(
    "SELECT intake_enabled FROM worker WHERE worker_id = :worker_id FOR SHARE"
)
_RUNS_HELD = text(
    "SELECT l.worker_id, j.run_id FROM lease l JOIN job j ON j.job_id = l.job_id "
    "WHERE l.worker_id = ANY(:worker_ids) AND l.released_at IS NULL "
    "ORDER BY l.worker_id, l.acquired_at, j.run_id"
)
_EXPIRED_LEASES = text(
    "SELECT j.run_id, j.job_id, a.attempt_id, l.lease_id FROM lease l "
    "JOIN attempt a ON a.attempt_id = l.attempt_id "
    "JOIN job j ON j.job_id = l.job_id WHERE l.released_at IS NULL "
    "AND ((CAST(:force_attempt_id AS text) IS NULL "
    "AND l.expires_at <= statement_timestamp()) "
    "OR (CAST(:force_attempt_id AS text) IS NOT NULL "
    "AND l.attempt_id = :force_attempt_id)) "
    "ORDER BY j.run_id, l.lease_id LIMIT 100"
)
#: `RUN-ROBUSTNESS-01` (D-169). For each Attempt of a Job that was lost, the stage the Run had
#: started last while that Attempt held authority: ``stage.started`` is journalled and committed
#: before a deterministic stage runs (`runs.executor`), so a worker killed inside a stage leaves
#: that stage as the newest start of its Attempt's window. ``NULL`` when the Attempt started no
#: stage (killed before the first one).
_LOST_ATTEMPT_STAGES = text(
    "SELECT a.attempt_id, ("
    "SELECT e.payload ->> 'stage_id' FROM audit_event e "
    "WHERE e.event_type = 'stage.started' AND e.aggregate_id = :run_id "
    "AND e.occurred_at >= a.created_at "
    "AND (a.terminal_at IS NULL OR e.occurred_at <= a.terminal_at) "
    "ORDER BY e.sequence_no DESC LIMIT 1) AS stage_id "
    "FROM attempt a WHERE a.job_id = :job_id AND a.state = 'lost' "
    "ORDER BY a.created_at, a.attempt_id"
)
_ENSURE_CONTROL = text(
    "INSERT INTO execution_control (singleton, paused) VALUES (true, false) "
    "ON CONFLICT (singleton) DO NOTHING"
)
_LOCK_CONTROL = text(
    "SELECT paused FROM execution_control WHERE singleton = true FOR UPDATE"
)
_INSERT_ATTEMPT = text(
    "INSERT INTO attempt (attempt_id, job_id, state, execution_token) "
    "VALUES (:attempt_id, :job_id, 'created', gen_random_uuid()::text) "
    "RETURNING execution_token"
)
_SET_CURRENT = text(
    "UPDATE job SET current_attempt_id = :attempt_id, updated_at = statement_timestamp() "
    "WHERE job_id = :job_id AND state = 'queued'"
)
_INSERT_LEASE = text(
    "INSERT INTO lease (lease_id, job_id, attempt_id, worker_id, expires_at) "
    "VALUES (:lease_id, :job_id, :attempt_id, :worker_id, "
    "statement_timestamp() + make_interval(secs => :lease_seconds))"
)
_ADVANCE_JOB = text(
    "UPDATE job SET state = :to_state, updated_at = statement_timestamp(), "
    "terminal_at = CASE WHEN :terminal THEN statement_timestamp() ELSE NULL END "
    "WHERE job_id = :job_id AND state = :from_state"
)
_ADVANCE_ATTEMPT = text(
    "UPDATE attempt SET state = :to_state, updated_at = statement_timestamp(), "
    "terminal_at = CASE WHEN :terminal THEN statement_timestamp() ELSE NULL END "
    "WHERE attempt_id = :attempt_id AND state = :from_state"
)
_RELEASE_LEASE = text(
    "UPDATE lease SET released_at = statement_timestamp() "
    "WHERE attempt_id = :attempt_id AND released_at IS NULL"
)
_LOCK_AUTHORITY_JOB = text(
    "SELECT run_id, job_id, state AS job_state, current_attempt_id "
    "FROM job WHERE job_id = :job_id FOR UPDATE"
)
_LOCK_AUTHORITY_ATTEMPT = text(
    "SELECT state AS attempt_state, execution_token FROM attempt "
    "WHERE attempt_id = :attempt_id FOR UPDATE"
)
_LOCK_AUTHORITY_LEASE = text(
    "SELECT lease_id, released_at, expires_at, "
    "expires_at > statement_timestamp() AS current FROM lease "
    "WHERE attempt_id = :attempt_id FOR UPDATE"
)

_INSERT_PROVIDER_EFFECT = text(
    """
    INSERT INTO provider_call_effect (
        model_call_id, run_id, job_id, attempt_id, stage_id, provider,
        model_identity, provider_mode, parameters, request_sha256
    ) VALUES (
        :model_call_id, :run_id, :job_id, :attempt_id, 'text_analysis', :provider,
        :model_identity, :provider_mode, CAST(:parameters AS jsonb), :request_sha256
    )
    """
)
_PROVIDER_RESPONSE = text(
    """
    UPDATE provider_call_effect
       SET state = 'response_received', response_sha256 = :response_sha256,
           input_tokens = :input_tokens, output_tokens = :output_tokens,
           latency_ms = :latency_ms, updated_at = statement_timestamp()
     WHERE model_call_id = :model_call_id AND run_id = :run_id
       AND job_id = :job_id AND attempt_id = :attempt_id AND state = 'prepared'
    """
)
_PROVIDER_UNKNOWN = text(
    """
    UPDATE provider_call_effect
       SET state = 'outcome_unknown', error_code = :error_code,
           dispatch_class = 'outcome_unknown',
           updated_at = statement_timestamp()
     WHERE model_call_id = :model_call_id AND run_id = :run_id
       AND job_id = :job_id AND attempt_id = :attempt_id AND state = 'prepared'
    """
)
_PROVIDER_NOT_PROCESSED = text(
    "UPDATE provider_call_effect SET state = 'not_processed', "
    "error_code = :error_code, dispatch_class = :dispatch_class, "
    "updated_at = statement_timestamp() WHERE model_call_id = :model_call_id "
    "AND run_id = :run_id AND job_id = :job_id AND attempt_id = :attempt_id "
    "AND state = 'prepared'"
)
_COMPLETE_PROVIDER = text(
    """
    UPDATE provider_call_effect
       SET state = 'completed', final_model_call_id = model_call_id,
           updated_at = statement_timestamp()
     WHERE model_call_id = :model_call_id AND run_id = :run_id
       AND job_id = :job_id AND attempt_id = :attempt_id
       AND state = 'response_received'
    """
)
_PROVIDER_FOR_COMPLETION = text(
    """
    SELECT 1 FROM provider_call_effect
     WHERE model_call_id = :model_call_id AND run_id = :run_id
       AND job_id = :job_id AND attempt_id = :attempt_id
       AND state = 'response_received'
     FOR UPDATE
    """
)
_EXISTING_RECORDED_STAGE_CALL = text(
    "SELECT EXISTS ("
    "SELECT 1 FROM provider_call_effect WHERE run_id = :run_id "
    "AND stage_id = 'text_analysis' AND state NOT IN ('not_processed', 'abandoned') "
    "UNION ALL SELECT 1 FROM model_call WHERE run_id = :run_id "
    "AND stage_id = 'text_analysis'"
    ")"
)
_RECORDED_COMPLETED_CALLS = text(
    "SELECT m.model_call_id, m.model_identity, m.request_sha256, m.response_sha256, "
    "m.provider, m.provider_mode, m.status, "
    "e.job_id, e.stage_id AS effect_stage, e.state AS effect_state, "
    "e.final_model_call_id, "
    "e.provider AS effect_provider, e.provider_mode AS effect_mode, "
    "e.model_identity AS effect_model, e.request_sha256 AS effect_request, "
    "e.response_sha256 AS effect_response "
    "FROM model_call m LEFT JOIN provider_call_effect e "
    "ON e.run_id = m.run_id AND e.model_call_id = m.model_call_id "
    "WHERE m.run_id = :run_id AND m.stage_id = 'text_analysis'"
)
_INSERT_MODEL_CALL = text(
    """
    INSERT INTO model_call (
        model_call_id, run_id, stage_id, provider, model_identity, provider_mode,
        parameters, request_sha256, response_sha256, input_tokens, output_tokens,
        latency_ms, cost_micros, cost_basis, status, error_code
    ) VALUES (
        :model_call_id, :run_id, 'text_analysis', :provider, :model_identity,
        :provider_mode, CAST(:parameters AS jsonb), :request_sha256, :response_sha256,
        :input_tokens, :output_tokens, :latency_ms, :cost_micros, :cost_basis,
        :status, :error_code
    )
    """
)

_INSERT_ARTIFACT_INTENT = text(
    """
    INSERT INTO analysis_artifact_publication (
        run_id, job_id, attempt_id, stage_id, blob_id, blob_role
    ) VALUES (
        :run_id, :job_id, :attempt_id, :stage_id, :blob_id, :blob_role
    )
    ON CONFLICT (attempt_id, stage_id, blob_id, blob_role) DO UPDATE
       SET upload_token = analysis_artifact_publication.upload_token
    RETURNING upload_token
    """
)
_BIND_ARTIFACT = text(
    """
    UPDATE analysis_artifact_publication
       SET state = 'bound', artifact_role = :artifact_role,
           bound_at = statement_timestamp()
     WHERE run_id = :run_id AND job_id = :job_id AND attempt_id = :attempt_id
       AND stage_id = :stage_id AND blob_id = :blob_id AND state = 'prepared'
    """
)
_UNRESOLVED_PROVIDER_EFFECTS = text(
    """
    SELECT model_call_id, run_id, job_id, attempt_id, state, request_sha256,
           response_sha256, error_code
      FROM provider_call_effect
     WHERE state IN ('prepared', 'response_received')
     ORDER BY prepared_at, model_call_id
    """
)
_SETTLE_TERMINAL_PROVIDER_EFFECTS = text(
    """
    WITH candidates AS (
        SELECT effect.model_call_id, effect.state AS previous_state
          FROM provider_call_effect effect
          JOIN attempt execution_attempt
            ON execution_attempt.attempt_id = effect.attempt_id
           AND execution_attempt.job_id = effect.job_id
          JOIN job execution_job
            ON execution_job.job_id = effect.job_id
           AND execution_job.run_id = effect.run_id
          JOIN audit_run run ON run.run_id = effect.run_id
         WHERE effect.state IN ('prepared', 'response_received')
           AND execution_attempt.state IN (
               'succeeded', 'failed', 'superseded', 'lost', 'cancelled'
           )
           AND execution_job.state IN ('succeeded', 'failed', 'cancelled', 'dead_letter')
           AND run.state IN ('published', 'partial', 'failed', 'cancelled')
           AND effect.prepared_at <= statement_timestamp() - CAST(:older_than AS interval)
         ORDER BY effect.prepared_at, effect.model_call_id
         LIMIT :batch_size
         FOR UPDATE OF effect SKIP LOCKED
    )
    UPDATE provider_call_effect effect
       SET state = 'abandoned', error_code = :error_code,
           updated_at = statement_timestamp()
      FROM candidates
     WHERE effect.model_call_id = candidates.model_call_id
    RETURNING effect.model_call_id, effect.run_id, effect.job_id, effect.attempt_id,
              candidates.previous_state, effect.state
    """
)
#: `D-142`: an Attempt-scoped artifact intent whose Attempt is terminal can never be
#: bound (``bind_artifacts`` requires the current authority), so it is settled
#: ``prepared -> abandoned``. The blob row is never touched: its identity is
#: content-derived, and a rerun of the same version re-records and publishes it.
_SETTLE_TERMINAL_ARTIFACT_PUBLICATIONS = text(
    """
    WITH candidates AS (
        SELECT publication.attempt_id, publication.stage_id, publication.blob_id,
               publication.blob_role
          FROM analysis_artifact_publication publication
          JOIN attempt execution_attempt
            ON execution_attempt.attempt_id = publication.attempt_id
           AND execution_attempt.job_id = publication.job_id
         WHERE publication.state = 'prepared'
           AND execution_attempt.state IN (
               'succeeded', 'failed', 'superseded', 'lost', 'cancelled'
           )
           AND publication.created_at <= statement_timestamp() - CAST(:older_than AS interval)
         ORDER BY publication.created_at, publication.attempt_id, publication.stage_id,
                  publication.blob_id, publication.blob_role
         LIMIT :batch_size
         FOR UPDATE OF publication SKIP LOCKED
    )
    UPDATE analysis_artifact_publication publication
       SET state = 'abandoned', abandoned_at = statement_timestamp()
      FROM candidates
     WHERE publication.attempt_id = candidates.attempt_id
       AND publication.stage_id = candidates.stage_id
       AND publication.blob_id = candidates.blob_id
       AND publication.blob_role = candidates.blob_role
    RETURNING publication.run_id, publication.attempt_id, publication.stage_id
    """
)

_JOB_TERMINALS = frozenset({"succeeded", "failed", "cancelled", "dead_letter"})
_ATTEMPT_TERMINALS = frozenset({"succeeded", "failed", "superseded", "lost", "cancelled"})


class ExecutionNotClaimed(DomainError):
    """``start_execution`` refused before the caller held any execution authority.

    Raised only by the claim itself: the dispatch pause, a Run or Job that is not
    claimable, or the duplicate-executor guard. No Attempt, Lease or token exists for
    the caller when it is raised, and the caller's transaction still holds every row
    the claim touched. A carrier must therefore leave the Run and its Job as it found
    them; turning this refusal into a crash terminal would destroy a run that this
    process never owned (`W53C-EXEC-01` C-01). The code and details are the original
    refusal's, so an API caller sees the same envelope as before.
    """

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class AttemptAuthority:
    run_id: str
    job_id: str
    attempt_id: str
    lease_id: str
    execution_token: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class RecordedCompletedCall:
    model_call_id: str
    model_id: str
    request_sha256: str
    response_sha256: str


@dataclass(frozen=True, slots=True)
class UnresolvedProviderEffect:
    model_call_id: str
    run_id: str
    job_id: str
    attempt_id: str
    state: str
    request_sha256: str
    response_sha256: str | None
    error_code: str | None


@dataclass(frozen=True, slots=True)
class SettledProviderEffect:
    """One non-repeatable call whose owning execution ended without completion."""

    model_call_id: str
    run_id: str
    job_id: str
    attempt_id: str
    previous_state: str
    state: str


class JobRepository:
    """Create and fence local execution plus journal its external effects.

    ``worker_id`` (`W54-WORKER-01`, R-105) names the registered worker process a claim is
    made for. It is recorded on the Lease, frozen with it, and the claim refuses while
    that worker's intake is switched off. ``None`` is the in-process claimant of
    ``EXECUTION_ROLE=all``, whose Lease names no worker, exactly as before migration 0019.
    """

    #: The lease length, stamped on database time. Sixty seconds is the W53 value (the
    #: 0017 column default); three heartbeats of :data:`jobs.lease.HEARTBEAT_SECONDS` fit
    #: inside it. A class attribute so a test can shorten both the claim and the
    #: extension together without a second code path.
    lease_seconds: float = 60.0

    def __init__(self, *, worker_id: str | None = None) -> None:
        self._worker_id = worker_id

    @property
    def worker_id(self) -> str | None:
        return self._worker_id

    def enqueue(self, session: Session, *, run_id: str) -> str:
        """Create the durable Job in the accepting transaction and wake the workers."""
        job_id = str(JobId.new())
        session.execute(_INSERT_JOB, {"job_id": job_id, "run_id": run_id})
        append_execution_event(
            session, event_type="job.created", aggregate_type="Job",
            aggregate_id=job_id, run_id=run_id, payload={"state": "queued"},
        )
        self.wake_workers(session)
        return job_id

    @staticmethod
    def wake_workers(session: Session) -> None:
        """Hint every listening worker, delivered only if the caller's transaction commits."""
        session.execute(_NOTIFY, {"channel": JOB_WAKEUP_CHANNEL})

    def runs_held_by(
        self, session: Session, worker_ids: Sequence[str]
    ) -> dict[str, tuple[str, ...]]:
        """The Runs whose unreleased Lease names each worker, oldest claim first."""
        held: dict[str, list[str]] = {worker_id: [] for worker_id in worker_ids}
        if not worker_ids:
            return {}
        for row in session.execute(_RUNS_HELD, {"worker_ids": list(worker_ids)}).all():
            held.setdefault(str(row[0]), []).append(str(row[1]))
        return {worker_id: tuple(runs) for worker_id, runs in held.items()}

    def next_queued_run(self, session: Session) -> str | None:
        """Hint the highest runnable Job whose Run is not held by another claimant.

        Only the Run is briefly locked here. Every writer follows Run then Job;
        the worker later makes the authoritative claim under that same order.
        """
        return session.execute(_NEXT_JOB).scalar_one_or_none()

    def heartbeat(self, session: Session, authority: AttemptAuthority) -> bool:
        """Extend only a live lease, with database time and a bounded lock wait."""
        session.execute(text("SET LOCAL lock_timeout = '2s'"))
        return session.execute(
            _HEARTBEAT,
            {"lease_id": authority.lease_id, "attempt_id": authority.attempt_id,
             "lease_seconds": float(self.lease_seconds)},
        ).rowcount == 1

    def set_priority(self, session: Session, *, job_id: str, priority: int) -> None:
        """Change only a queued Job, under the run-first lock order."""
        if not -100 <= priority <= 100:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="priority", constraint="range")
        run_id = session.execute(text(
            "SELECT run_id FROM job WHERE job_id = :job_id"
        ), {"job_id": job_id}).scalar_one_or_none()
        if run_id is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Job")
        session.execute(_LOCK_RUN, {"run_id": run_id}).scalar_one()
        row = session.execute(text(
            "SELECT state FROM job WHERE job_id = :job_id FOR UPDATE"
        ), {"job_id": job_id}).mappings().one()
        if row["state"] != "queued":
            raise self._transition_error("job", str(row["state"]), "queued")
        session.execute(text(
            "UPDATE job SET priority = :priority, updated_at = statement_timestamp() "
            "WHERE job_id = :job_id"
        ), {"job_id": job_id, "priority": priority})
        append_execution_event(
            session, event_type="job.priority_changed", aggregate_type="Job",
            aggregate_id=job_id, run_id=run_id, payload={"priority": priority},
        )

    def set_paused(self, session: Session, *, paused: bool) -> None:
        session.execute(text(
            "INSERT INTO execution_control (singleton, paused) VALUES (true, :paused) "
            "ON CONFLICT (singleton) DO UPDATE SET paused = EXCLUDED.paused, "
            "changed_at = statement_timestamp()"
        ), {"paused": paused})
        if not paused:
            self.wake_workers(session)

    def reclaim_expired(self, session: Session, *, force_attempt_id: str | None = None) -> int:
        """Fence lost Attempts and resume only when no ambiguous provider effect exists.

        A watchdog passes ``force_attempt_id`` after the fixed execution deadline. It
        fences authority but does not free the caller's in-process worker slot.
        The forced pass considers only its Attempt. Periodic passes take all Run
        locks in one stable order, including when two sweeps overlap.
        """
        from auditmanager.runs.public import fail_reclaimed_run

        session.execute(text("SET LOCAL lock_timeout = '2s'"))
        recovered = 0
        candidates = session.execute(
            _EXPIRED_LEASES, {"force_attempt_id": force_attempt_id}
        ).mappings().all()
        for candidate in candidates:
            run_id = str(candidate["run_id"])
            run_state = session.execute(
                _LOCK_RUN, {"run_id": run_id}
            ).scalar_one_or_none()
            job = session.execute(
                _LOCK_JOB_WAIT, {"run_id": run_id}
            ).mappings().first()
            if job is None or job["current_attempt_id"] != candidate["attempt_id"]:
                continue
            attempt = session.execute(
                _LOCK_AUTHORITY_ATTEMPT, {"attempt_id": candidate["attempt_id"]}
            ).mappings().first()
            lease = session.execute(
                _LOCK_AUTHORITY_LEASE, {"attempt_id": candidate["attempt_id"]}
            ).mappings().first()
            if (attempt is None or lease is None or lease["released_at"] is not None
                    or (lease["current"] and candidate["attempt_id"] != force_attempt_id)):
                continue
            if attempt["attempt_state"] in {"leased", "running"}:
                self._advance_attempt(
                    session, str(candidate["attempt_id"]),
                    str(attempt["attempt_state"]), "lost",
                )
            session.execute(_RELEASE_LEASE, {"attempt_id": candidate["attempt_id"]})
            state = str(job["state"])
            if state not in {"leased", "running"} or run_state not in {"queued", "running"}:
                recovered += 1
                continue
            # D-150 (decided at `W54-FREEZE-01`): a recorded call spends nothing, so a
            # recorded effect the lost Attempt left ``prepared`` is settled
            # ``not_processed`` and no recorded effect makes the Attempt ambiguous.
            # Only a live call that might have been sent fences the run.
            settled_recorded = session.execute(text(
                "UPDATE provider_call_effect SET state = 'not_processed', "
                "error_code = :code, dispatch_class = 'not_sent', "
                "updated_at = statement_timestamp() "
                "WHERE attempt_id = :attempt_id AND state = 'prepared' "
                "AND provider_mode = 'recorded' "
                "RETURNING run_id, attempt_id"
            ), {"attempt_id": candidate["attempt_id"],
                "code": ErrorCode.ANALYSIS_FAILED.value}).mappings().all()
            for effect in settled_recorded:
                append_execution_event(
                    session, event_type="provider.not_processed",
                    aggregate_type="Attempt", aggregate_id=str(effect["attempt_id"]),
                    run_id=str(effect["run_id"]),
                    payload={"attempt_id": str(effect["attempt_id"]),
                             "error_code": ErrorCode.ANALYSIS_FAILED.value,
                             "dispatch_class": "not_sent"},
                )
            ambiguous = bool(session.execute(text(
                "SELECT EXISTS (SELECT 1 FROM provider_call_effect "
                "WHERE attempt_id = :attempt_id AND state <> 'not_processed' "
                "AND provider_mode <> 'recorded')"
            ), {"attempt_id": candidate["attempt_id"]}).scalar_one())
            count = int(session.execute(text(
                "SELECT count(*) FROM attempt WHERE job_id = :job_id"
            ), {"job_id": candidate["job_id"]}).scalar_one())
            if ambiguous:
                changed_effects = session.execute(text(
                    "UPDATE provider_call_effect SET state = 'outcome_unknown', "
                    "error_code = :code, dispatch_class = 'outcome_unknown', "
                    "updated_at = statement_timestamp() "
                    "WHERE attempt_id = :attempt_id AND state = 'prepared' "
                    "RETURNING run_id, attempt_id"
                ), {"attempt_id": candidate["attempt_id"],
                    "code": ErrorCode.ANALYSIS_FAILED.value}).mappings().all()
                for effect in changed_effects:
                    append_execution_event(
                        session, event_type="provider.outcome_unknown",
                        aggregate_type="Attempt", aggregate_id=str(effect["attempt_id"]),
                        run_id=str(effect["run_id"]),
                        payload={"attempt_id": str(effect["attempt_id"]),
                                 "error_code": ErrorCode.ANALYSIS_FAILED.value,
                                 "dispatch_class": "outcome_unknown"},
                    )
            if ambiguous or count >= 3:
                if state == "running" and not ambiguous:
                    self._advance_job(session, str(candidate["job_id"]), "running", "retry_wait")
                    self._advance_job(session, str(candidate["job_id"]), "retry_wait", "dead_letter")
                else:
                    self._advance_job(session, str(candidate["job_id"]), state, "failed")
                fail_reclaimed_run(
                    session, run_id=run_id, from_state=str(run_state),
                    interrupted_reason=(
                        "provider_outcome_unknown" if ambiguous else "attempt_budget_exhausted"
                    ),
                    # D-169: an exhausted budget names the stage that killed the worker again
                    # and again; an uncertain provider effect keeps the cause it always had.
                    terminal_detail=(
                        None if ambiguous else self._repeated_kill_detail(
                            session, run_id=run_id, job_id=str(candidate["job_id"]),
                        )
                    ),
                )
            else:
                if state == "running":
                    self._advance_job(session, str(candidate["job_id"]), "running", "retry_wait")
                    self._advance_job(session, str(candidate["job_id"]), "retry_wait", "queued")
                else:
                    self._advance_job(session, str(candidate["job_id"]), "leased", "queued")
                session.execute(text(
                    "UPDATE job SET available_at = statement_timestamp() WHERE job_id = :job_id"
                ), {"job_id": candidate["job_id"]})
                self.wake_workers(session)
            recovered += 1
        return recovered

    @staticmethod
    def _repeated_kill_detail(
        session: Session, *, run_id: str, job_id: str
    ) -> dict[str, str] | None:
        """``{"stage_id": ...}`` when the last two lost Attempts died in the same stage.

        `RUN-ROBUSTNESS-01`, D-169. A worker killed for memory is resumed (nothing it did can
        have spent a provider call) and the same pages kill the next one, so the third loss
        dead-letters a Job whose Run then said ``analysis_failed`` and nothing more. Two lost
        Attempts in a row inside the same stage is the signature of an input that kills its
        worker; it is named with the ``stage_id`` detail the code ``analysis_failed`` already
        declares safe. Attempts lost in different stages, or before any stage, are restarts and
        not an input: no stage is named, as before -- a stage the worker merely happened to be
        in is not a cause.
        """
        stages = [
            row["stage_id"] for row in session.execute(
                _LOST_ATTEMPT_STAGES, {"run_id": run_id, "job_id": job_id}
            ).mappings().all()
        ]
        if len(stages) >= 2 and stages[-1] is not None and stages[-1] == stages[-2]:
            return {"stage_id": str(stages[-1])}
        return None

    def start_execution(self, session: Session, *, run_id: str) -> AttemptAuthority:
        """Claim the Run's Job with a new current Attempt, Lease and token.

        Every catalog refusal raised here precedes the returned authority, so it is
        re-raised as :class:`ExecutionNotClaimed` with its code and details intact.
        """
        try:
            return self._claim(session, run_id=run_id)
        except ExecutionNotClaimed:
            raise
        except DomainError as refusal:
            raise ExecutionNotClaimed(
                refusal.code, message=refusal.custom_message,
                **dict(refusal.detail_fields),
            ) from refusal

    def _claim(self, session: Session, *, run_id: str) -> AttemptAuthority:
        if self._worker_id is not None:
            # R-105. A registered worker claims only while its intake is on. FOR SHARE
            # serialises the claim with `setWorkerIntake`'s row lock, so a switch that
            # commits first is observed here before any Attempt exists.
            intake = session.execute(
                _LOCK_WORKER_INTAKE, {"worker_id": self._worker_id}
            ).scalar_one_or_none()
            if intake is None:
                raise DomainError(
                    ErrorCode.CONFLICT, message="the claiming worker is not registered",
                    aggregate_type="Worker",
                )
            if not intake:
                raise DomainError(
                    ErrorCode.CONFLICT, message="the worker's intake is switched off",
                    aggregate_type="Worker",
                )
        # The singleton must exist before it can be locked. Its insert races with
        # an administrator's upsert safely: whichever transaction commits first
        # is observed by the other before a new Attempt can be created.
        session.execute(_ENSURE_CONTROL)
        if session.execute(_LOCK_CONTROL).scalar_one():
            raise DomainError(
                ErrorCode.CONFLICT, message="execution dispatch is paused",
            )
        # The run is always locked before its Job. This serialises a claim with
        # cancellation, final publication and the recovery sweep.
        run_state = session.execute(_LOCK_RUN, {"run_id": run_id}).scalar_one_or_none()
        if run_state not in ("queued", "running"):
            raise self._transition_error("audit_run", str(run_state), "running")
        job = session.execute(_LOCK_JOB, {"run_id": run_id}).mappings().first()
        if job is None:
            # Direct execute_run callers can enqueue a queued Run without the
            # API's accepting transaction. A running Run requires prior Job authority.
            existing = session.execute(
                text("SELECT 1 FROM job WHERE run_id = :run_id"), {"run_id": run_id}
            ).scalar_one_or_none()
            if existing is not None:
                raise self._transition_error("job", "locked", "leased")
            if run_state != "queued":
                raise self._transition_error("audit_run", str(run_state), "queued")
            job_id = self.enqueue(session, run_id=run_id)
        else:
            job_id = str(job["job_id"])
            if job["state"] != "queued":
                raise self._transition_error("job", str(job["state"]), "leased")
        attempt_id = str(AttemptId.new())
        lease_id = str(LeaseId.new())
        try:
            token = str(session.execute(
                _INSERT_ATTEMPT,
                {"attempt_id": attempt_id, "job_id": job_id},
            ).scalar_one())
            append_execution_event(
                session, event_type="attempt.created", aggregate_type="Attempt",
                aggregate_id=attempt_id, run_id=run_id,
                payload={"job_id": job_id, "state": "created"},
            )
            changed = session.execute(
                _SET_CURRENT,
                {"job_id": job_id, "attempt_id": attempt_id},
            ).rowcount
            if changed != 1:
                raise self._transition_error("job", "queued", "leased")
            session.execute(
                _INSERT_LEASE,
                {"lease_id": lease_id, "job_id": job_id, "attempt_id": attempt_id,
                 "worker_id": self._worker_id,
                 "lease_seconds": float(self.lease_seconds)},
            )
            self._advance_job(session, job_id, "queued", "leased")
            self._advance_attempt(session, attempt_id, "created", "leased")
            self._advance_job(session, job_id, "leased", "running")
            self._advance_attempt(session, attempt_id, "leased", "running")
        except DomainError:
            raise
        except DBAPIError as exc:
            # The uniqueness constraint on job.run_id is the final duplicate-executor
            # guard. Only that exact database category is a conflict: mapping arbitrary
            # driver/schema faults to "already running" would be a silent fallback.
            sqlstate = getattr(exc.orig, "sqlstate", None)
            diagnostic = getattr(exc.orig, "diag", None)
            constraint = getattr(diagnostic, "constraint_name", None)
            if sqlstate == "23505" and constraint == "uq_job_run_id":
                raise DomainError(
                    ErrorCode.CONFLICT,
                    message="the run already has durable execution authority",
                    aggregate_type="Job",
                ) from exc
            raise
        return AttemptAuthority(run_id, job_id, attempt_id, lease_id, token)

    def require_current(self, session: Session, authority: AttemptAuthority) -> None:
        session.execute(_LOCK_RUN, {"run_id": authority.run_id}).scalar_one_or_none()
        row = session.execute(
            _LOCK_AUTHORITY_JOB, {"job_id": authority.job_id}
        ).mappings().first()
        if row is None or row["run_id"] != authority.run_id:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")
        if row["current_attempt_id"] != authority.attempt_id:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")
        attempt = session.execute(
            _LOCK_AUTHORITY_ATTEMPT, {"attempt_id": authority.attempt_id}
        ).mappings().first()
        lease = session.execute(
            _LOCK_AUTHORITY_LEASE, {"attempt_id": authority.attempt_id}
        ).mappings().first()
        if attempt is None or not secrets.compare_digest(
            str(attempt["execution_token"]), authority.execution_token
        ):
            raise DomainError(ErrorCode.EXECUTION_TOKEN_INVALID, aggregate_type="Attempt")
        if (row["job_state"] != "running" or attempt["attempt_state"] != "running"
                or lease is None or lease["lease_id"] != authority.lease_id
                or lease["released_at"] is not None or not lease["current"]):
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")

    def finish_execution(
        self, session: Session, authority: AttemptAuthority, *, publishes_result: bool
    ) -> None:
        self.require_current(session, authority)
        target = "succeeded" if publishes_result else "failed"
        self._advance_attempt(session, authority.attempt_id, "running", target)
        self._advance_job(session, authority.job_id, "running", target)
        session.execute(_RELEASE_LEASE, {"attempt_id": authority.attempt_id})

    def fail_for_run(self, session: Session, *, run_id: str) -> None:
        self._close_for_run(session, run_id=run_id, target="failed")

    def cancel_for_run(self, session: Session, *, run_id: str) -> None:
        """Fence an accepted run under the run → job → attempt → lease lock order."""
        self._close_for_run(session, run_id=run_id, target="cancelled")

    def _close_for_run(self, session: Session, *, run_id: str, target: str) -> None:
        session.execute(_LOCK_RUN, {"run_id": run_id}).scalar_one_or_none()
        row = session.execute(_LOCK_JOB_WAIT, {"run_id": run_id}).mappings().first()
        if row is None:
            return
        attempt_id = row["current_attempt_id"]
        if attempt_id is not None:
            attempt = session.execute(
                _LOCK_AUTHORITY_ATTEMPT, {"attempt_id": attempt_id}
            ).mappings().one()
            attempt_state = str(attempt["attempt_state"])
            if attempt_state in {"created", "leased", "running"}:
                attempt_target = (
                    "cancelled" if target == "cancelled" or attempt_state == "created"
                    else "lost"
                )
                self._advance_attempt(session, str(attempt_id), attempt_state, attempt_target)
            session.execute(
                _LOCK_AUTHORITY_LEASE, {"attempt_id": attempt_id}
            ).mappings().first()
            session.execute(_RELEASE_LEASE, {"attempt_id": attempt_id})
        job_state = str(row["state"])
        if target == "cancelled" and job_state in {"queued", "leased", "running", "retry_wait"}:
            self._advance_job(session, str(row["job_id"]), job_state, "cancelled")
        elif target == "failed" and job_state in {"leased", "running"}:
            self._advance_job(session, str(row["job_id"]), job_state, "failed")
        elif target == "failed" and job_state == "queued":
            # A queued Job cannot move directly to failed in the sealed graph. The
            # run can be failed by reconciliation while the Job is cancelled.
            self._advance_job(session, str(row["job_id"]), "queued", "cancelled")

    def prepare_provider_call(
        self,
        session: Session,
        authority: AttemptAuthority,
        *,
        provider: str,
        model_identity: str,
        provider_mode: str,
        parameters: Mapping[str, Any],
        request_sha256: str,
    ) -> ModelCallId:
        self.require_current(session, authority)
        model_call_id = ModelCallId.new()
        session.execute(
            _INSERT_PROVIDER_EFFECT,
            {
                "model_call_id": str(model_call_id),
                "run_id": authority.run_id,
                "job_id": authority.job_id,
                "attempt_id": authority.attempt_id,
                "provider": provider,
                "model_identity": model_identity,
                "provider_mode": provider_mode,
                "parameters": json.dumps(dict(parameters), sort_keys=True),
                "request_sha256": request_sha256,
            },
        )
        append_execution_event(
            session, event_type="provider.prepared", aggregate_type="Attempt",
            aggregate_id=authority.attempt_id, run_id=authority.run_id,
            payload={"attempt_id": authority.attempt_id, "state": "prepared"},
        )
        return model_call_id

    def require_recorded_stage_call_available(
        self, session: Session, authority: AttemptAuthority
    ) -> None:
        """Fence a second recorded text call before its intent can be committed.

        A completed call, a response awaiting completion, or an uncertain effect
        blocks another replay for the same run. A proven ``not_processed`` or
        reconciled ``abandoned`` effect does not fabricate a canonical call.
        The current Attempt lock serialises this read with another claimant.
        """
        self.require_current(session, authority)
        if session.execute(
            _EXISTING_RECORDED_STAGE_CALL, {"run_id": authority.run_id}
        ).scalar_one():
            raise DomainError(
                ErrorCode.CONFLICT,
                message="a text analysis call already has durable evidence for this run",
                aggregate_type="AuditRun",
            )

    def completed_recorded_call(
        self, session: Session, *, run_id: str, job_id: str
    ) -> RecordedCompletedCall:
        """Read the sole completed recorded call for a saved text stage.

        The call can belong to an earlier Attempt after lease recovery. It must
        still belong to this Run and Job, with a completed effect and identical
        immutable request/response facts. This read takes no Lease lock.
        """
        rows = session.execute(_RECORDED_COMPLETED_CALLS, {"run_id": run_id}).mappings().all()
        if len(rows) != 1:
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message="recorded text stage requires exactly one completed model call",
            )
        row = rows[0]
        if (
            row["job_id"] != job_id
            or row["effect_stage"] != "text_analysis"
            or row["effect_state"] != "completed"
            or row["final_model_call_id"] != row["model_call_id"]
            or row["provider"] != "anthropic"
            or row["provider_mode"] != "recorded"
            or row["status"] != "succeeded"
            or row["effect_provider"] != row["provider"]
            or row["effect_mode"] != row["provider_mode"]
            or row["effect_model"] != row["model_identity"]
            or row["effect_request"] != row["request_sha256"]
            or row["effect_response"] != row["response_sha256"]
            or row["response_sha256"] is None
        ):
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message="recorded call and completed effect do not agree",
            )
        return RecordedCompletedCall(
            str(row["model_call_id"]), str(row["model_identity"]),
            str(row["request_sha256"]), str(row["response_sha256"]),
        )

    def record_provider_response(
        self,
        session: Session,
        authority: AttemptAuthority,
        *,
        model_call_id: ModelCallId,
        response_sha256: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
    ) -> None:
        self.require_current(session, authority)
        changed = session.execute(
            _PROVIDER_RESPONSE,
            {
                "model_call_id": str(model_call_id),
                "run_id": authority.run_id,
                "job_id": authority.job_id,
                "attempt_id": authority.attempt_id,
                "response_sha256": response_sha256,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency_ms,
            },
        ).rowcount
        if changed != 1:
            raise self._transition_error(
                "provider_call_effect", "prepared", "response_received"
            )
        append_execution_event(
            session, event_type="provider.response_received",
            aggregate_type="Attempt", aggregate_id=authority.attempt_id,
            run_id=authority.run_id,
            payload={"attempt_id": authority.attempt_id, "state": "response_received"},
        )

    def record_provider_not_processed(
        self, session: Session, authority: AttemptAuthority, *,
        model_call_id: ModelCallId, error_code: str, dispatch_class: str,
    ) -> None:
        if dispatch_class not in {"not_sent", "rate_limited", "proxy_unavailable", "definite_refusal"}:
            raise ValueError("not_processed requires a proven dispatch class")
        self.require_current(session, authority)
        changed = session.execute(_PROVIDER_NOT_PROCESSED, {
            "model_call_id": str(model_call_id), "run_id": authority.run_id,
            "job_id": authority.job_id, "attempt_id": authority.attempt_id,
            "error_code": error_code, "dispatch_class": dispatch_class,
        }).rowcount
        if changed != 1:
            raise self._transition_error("provider_call_effect", "prepared", "not_processed")
        append_execution_event(
            session, event_type="provider.not_processed",
            aggregate_type="Attempt", aggregate_id=authority.attempt_id,
            run_id=authority.run_id,
            payload={"attempt_id": authority.attempt_id, "error_code": error_code,
                     "dispatch_class": dispatch_class},
        )

    def record_provider_unknown(
        self,
        session: Session,
        authority: AttemptAuthority,
        *,
        model_call_id: ModelCallId,
        error_code: str,
    ) -> None:
        self.require_current(session, authority)
        changed = session.execute(
            _PROVIDER_UNKNOWN,
            {
                "model_call_id": str(model_call_id),
                "run_id": authority.run_id,
                "job_id": authority.job_id,
                "attempt_id": authority.attempt_id,
                "error_code": error_code,
            },
        ).rowcount
        if changed != 1:
            raise self._transition_error(
                "provider_call_effect", "prepared", "outcome_unknown"
            )
        append_execution_event(
            session, event_type="provider.outcome_unknown",
            aggregate_type="Attempt", aggregate_id=authority.attempt_id,
            run_id=authority.run_id,
            payload={"attempt_id": authority.attempt_id, "error_code": error_code,
                     "dispatch_class": "outcome_unknown"},
        )

    def complete_provider_call(
        self,
        session: Session,
        authority: AttemptAuthority,
        *,
        call: Mapping[str, Any],
    ) -> None:
        self.require_current(session, authority)
        ownership = {
            "model_call_id": call["model_call_id"],
            "run_id": authority.run_id,
            "job_id": authority.job_id,
            "attempt_id": authority.attempt_id,
        }
        owned_effect = session.execute(
            _PROVIDER_FOR_COMPLETION, ownership
        ).scalar_one_or_none()
        if owned_effect is None:
            raise self._transition_error(
                "provider_call_effect", "response_received", "completed"
            )
        session.execute(
            _INSERT_MODEL_CALL,
            {
                "model_call_id": call["model_call_id"],
                "run_id": authority.run_id,
                "provider": call["provider"],
                "model_identity": call["model_id"],
                "provider_mode": call["provider_mode"],
                "parameters": json.dumps(
                    {**dict(call["parameters"]), "call_status": call["status"]},
                    sort_keys=True,
                ),
                "request_sha256": call["request_sha256"],
                "response_sha256": call["response_sha256"],
                "input_tokens": call["input_tokens"],
                "output_tokens": call["output_tokens"],
                "latency_ms": call["latency_ms"],
                "cost_micros": (
                    None if call["cost_usd"] is None
                    else int(round(float(call["cost_usd"]) * 1_000_000))
                ),
                "cost_basis": call.get("cost_basis", "estimated"),
                "status": call["status"],
                "error_code": (
                    ErrorCode.ANALYSIS_FAILED.value
                    if call["status"] == "failed"
                    else None
                ),
            },
        )
        changed = session.execute(
            _COMPLETE_PROVIDER,
            ownership,
        ).rowcount
        if changed != 1:
            raise self._transition_error(
                "provider_call_effect", "response_received", "completed"
            )
        append_execution_event(
            session, event_type="provider.completed", aggregate_type="Attempt",
            aggregate_id=authority.attempt_id, run_id=authority.run_id,
            payload={"attempt_id": authority.attempt_id, "state": "completed"},
        )

    def prepare_artifact(
        self,
        session: Session,
        authority: AttemptAuthority,
        *,
        stage_id: str,
        declaration: BlobDeclaration,
    ) -> str:
        self.require_current(session, authority)
        return str(
            session.execute(
                _INSERT_ARTIFACT_INTENT,
                {
                    "run_id": authority.run_id,
                    "job_id": authority.job_id,
                    "attempt_id": authority.attempt_id,
                    "stage_id": stage_id,
                    "blob_id": str(declaration.blob_id),
                    "blob_role": str(declaration.role),
                },
            ).scalar_one()
        )

    def bind_artifacts(
        self,
        session: Session,
        authority: AttemptAuthority,
        *,
        stage_id: str,
        artifacts: Sequence[Any],
    ) -> tuple[BlobId, ...]:
        self.require_current(session, authority)
        bound: list[BlobId] = []
        for artifact in artifacts:
            blob_id = parse_blob_id(str(artifact.blob_id))
            changed = session.execute(
                _BIND_ARTIFACT,
                {
                    "run_id": authority.run_id,
                    "job_id": authority.job_id,
                    "attempt_id": authority.attempt_id,
                    "stage_id": stage_id,
                    "blob_id": str(blob_id),
                    "artifact_role": str(artifact.role),
                },
            ).rowcount
            if changed != 1:
                raise DomainError(
                    ErrorCode.STORAGE_INTEGRITY_ERROR,
                    message="a stage result names an artifact with no current publication intent",
                    blob_id=str(blob_id),
                    role=str(artifact.role),
                )
            bound.append(blob_id)
        return tuple(bound)

    def unresolved_provider_effects(
        self, session: Session
    ) -> tuple[UnresolvedProviderEffect, ...]:
        return tuple(
            UnresolvedProviderEffect(**dict(row))
            for row in session.execute(_UNRESOLVED_PROVIDER_EFFECTS).mappings().all()
        )

    def settle_terminal_provider_effects(
        self,
        session: Session,
        *,
        older_than: str = "1 hour",
        batch_size: int = 100,
    ) -> tuple[SettledProviderEffect, ...]:
        """Bound one reconciliation pass and preserve ambiguous calls as abandoned.

        Only effects owned by a terminal Run, Job and Attempt are eligible.  Both a
        pre-dispatch ``prepared`` row and a durable ``response_received`` row may be
        abandoned: neither is safe to repeat, and neither contains enough evidence to
        invent the immutable canonical ``model_call``.  The previous state remains in
        the returned report while the row retains any response checksum/token counts it
        had already recorded.
        """
        if batch_size < 1:
            raise ValueError("provider effect reconciliation batch_size must be positive")
        rows = session.execute(
            _SETTLE_TERMINAL_PROVIDER_EFFECTS,
            {
                "older_than": older_than,
                "batch_size": batch_size,
                "error_code": ErrorCode.ANALYSIS_FAILED.value,
            },
        ).mappings().all()
        for effect in rows:
            append_execution_event(
                session, event_type="provider.abandoned",
                aggregate_type="Attempt", aggregate_id=str(effect["attempt_id"]),
                run_id=str(effect["run_id"]),
                payload={"attempt_id": str(effect["attempt_id"]),
                         "state": "abandoned"},
            )
        self.settle_terminal_artifact_publications(
            session, older_than=older_than, batch_size=batch_size
        )
        return tuple(SettledProviderEffect(**dict(row)) for row in rows)

    def settle_terminal_artifact_publications(
        self,
        session: Session,
        *,
        older_than: str = "1 hour",
        batch_size: int = 100,
    ) -> int:
        """`D-142`: settle unbound artifact intents of terminal Attempts as ``abandoned``.

        Called by :meth:`settle_terminal_provider_effects`, so every reconciliation
        pass that settles provider effects settles these too, under the same age
        threshold and batch bound. Each settled intent is journalled
        (``artifact.abandoned``) in the caller's transaction. Returns how many were
        settled; the blob rows they name are left exactly as they were.
        """
        if batch_size < 1:
            raise ValueError("artifact publication settlement batch_size must be positive")
        rows = session.execute(
            _SETTLE_TERMINAL_ARTIFACT_PUBLICATIONS,
            {"older_than": older_than, "batch_size": batch_size},
        ).mappings().all()
        for publication in rows:
            append_execution_event(
                session, event_type="artifact.abandoned",
                aggregate_type="Attempt", aggregate_id=str(publication["attempt_id"]),
                run_id=str(publication["run_id"]),
                payload={"attempt_id": str(publication["attempt_id"]),
                         "stage_id": str(publication["stage_id"]),
                         "state": "abandoned"},
            )
        return len(rows)

    def _advance_job(
        self, session: Session, job_id: str, from_state: str, to_state: str
    ) -> None:
        changed = session.execute(
            _ADVANCE_JOB,
            {
                "job_id": job_id,
                "from_state": from_state,
                "to_state": to_state,
                "terminal": to_state in _JOB_TERMINALS,
            },
        ).rowcount
        if changed != 1:
            raise self._transition_error("job", from_state, to_state)
        run_id = session.execute(
            text("SELECT run_id FROM job WHERE job_id = :job_id"), {"job_id": job_id}
        ).scalar_one()
        append_execution_event(
            session, event_type="job.transition", aggregate_type="Job",
            aggregate_id=job_id, run_id=run_id,
            payload={"from_state": from_state, "to_state": to_state},
        )

    def _advance_attempt(
        self, session: Session, attempt_id: str, from_state: str, to_state: str
    ) -> None:
        changed = session.execute(
            _ADVANCE_ATTEMPT,
            {
                "attempt_id": attempt_id,
                "from_state": from_state,
                "to_state": to_state,
                "terminal": to_state in _ATTEMPT_TERMINALS,
            },
        ).rowcount
        if changed != 1:
            raise self._transition_error("attempt", from_state, to_state)
        run_id = session.execute(text(
            "SELECT j.run_id FROM attempt a JOIN job j ON j.job_id = a.job_id "
            "WHERE a.attempt_id = :attempt_id"
        ), {"attempt_id": attempt_id}).scalar_one()
        append_execution_event(
            session, event_type="attempt.transition", aggregate_type="Attempt",
            aggregate_id=attempt_id, run_id=run_id,
            payload={"from_state": from_state, "to_state": to_state},
        )

    @staticmethod
    def _transition_error(machine: str, current: str, requested: str) -> DomainError:
        return DomainError(
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
            machine=machine,
            current_state=current,
            requested_state=requested,
        )


__all__ = [
    "JOB_WAKEUP_CHANNEL",
    "AttemptAuthority",
    "ExecutionNotClaimed",
    "JobRepository",
    "SettledProviderEffect",
    "UnresolvedProviderEffect",
]
