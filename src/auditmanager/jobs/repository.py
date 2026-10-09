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
    "expires_at = statement_timestamp() + interval '60 seconds' "
    "WHERE lease_id = :lease_id AND attempt_id = :attempt_id "
    "AND released_at IS NULL AND expires_at > statement_timestamp()"
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
    "INSERT INTO lease (lease_id, job_id, attempt_id) "
    "VALUES (:lease_id, :job_id, :attempt_id)"
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

_JOB_TERMINALS = frozenset({"succeeded", "failed", "cancelled", "dead_letter"})
_ATTEMPT_TERMINALS = frozenset({"succeeded", "failed", "superseded", "lost", "cancelled"})


@dataclass(frozen=True, slots=True)
class AttemptAuthority:
    run_id: str
    job_id: str
    attempt_id: str
    lease_id: str
    execution_token: str = field(repr=False)


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
    """Create and fence local execution plus journal its external effects."""

    def enqueue(self, session: Session, *, run_id: str) -> str:
        """Create the durable Job in the accepting transaction."""
        job_id = str(JobId.new())
        session.execute(_INSERT_JOB, {"job_id": job_id, "run_id": run_id})
        append_execution_event(
            session, event_type="job.created", aggregate_type="Job",
            aggregate_id=job_id, run_id=run_id, payload={"state": "queued"},
        )
        return job_id

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
            {"lease_id": authority.lease_id, "attempt_id": authority.attempt_id},
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
            ambiguous = bool(session.execute(text(
                "SELECT EXISTS (SELECT 1 FROM provider_call_effect "
                "WHERE attempt_id = :attempt_id AND state <> 'not_processed')"
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
            recovered += 1
        return recovered

    def start_execution(self, session: Session, *, run_id: str) -> AttemptAuthority:
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
                {"lease_id": lease_id, "job_id": job_id, "attempt_id": attempt_id},
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
    ) -> str:
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
                "cost_micros": int(round(float(call["cost_usd"]) * 1_000_000)),
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
        return tuple(SettledProviderEffect(**dict(row)) for row in rows)

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
    "AttemptAuthority",
    "JobRepository",
    "SettledProviderEffect",
    "UnresolvedProviderEffect",
]
