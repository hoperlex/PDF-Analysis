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

_INSERT_JOB = text(
    "INSERT INTO job (job_id, run_id, state) VALUES (:job_id, :run_id, 'queued')"
)
_INSERT_ATTEMPT = text(
    "INSERT INTO attempt (attempt_id, job_id, state, execution_token) "
    "VALUES (:attempt_id, :job_id, 'created', gen_random_uuid()::text) "
    "RETURNING execution_token"
)
_SET_CURRENT = text(
    "UPDATE job SET current_attempt_id = :attempt_id, updated_at = statement_timestamp() "
    "WHERE job_id = :job_id AND state = 'queued' AND current_attempt_id IS NULL"
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
_CURRENT_AUTHORITY = text(
    "SELECT j.run_id, j.job_id, j.state AS job_state, j.current_attempt_id, "
    "a.state AS attempt_state, a.execution_token "
    "FROM job j JOIN attempt a ON a.attempt_id = j.current_attempt_id "
    "WHERE j.job_id = :job_id FOR UPDATE OF j, a"
)
_BY_RUN_FOR_UPDATE = text(
    "SELECT j.job_id, j.state AS job_state, j.current_attempt_id, "
    "a.state AS attempt_state, a.execution_token "
    "FROM job j JOIN attempt a ON a.attempt_id = j.current_attempt_id "
    "WHERE j.run_id = :run_id FOR UPDATE OF j, a"
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
           updated_at = statement_timestamp()
     WHERE model_call_id = :model_call_id AND run_id = :run_id
       AND job_id = :job_id AND attempt_id = :attempt_id AND state = 'prepared'
    """
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

    def start_execution(self, session: Session, *, run_id: str) -> AttemptAuthority:
        job_id = str(JobId.new())
        attempt_id = str(AttemptId.new())
        lease_id = str(LeaseId.new())
        try:
            session.execute(_INSERT_JOB, {"job_id": job_id, "run_id": run_id})
            token = str(session.execute(
                _INSERT_ATTEMPT,
                {"attempt_id": attempt_id, "job_id": job_id},
            ).scalar_one())
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
        row = session.execute(
            _CURRENT_AUTHORITY, {"job_id": authority.job_id}
        ).mappings().first()
        if row is None or row["run_id"] != authority.run_id:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")
        if row["current_attempt_id"] != authority.attempt_id:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")
        if not secrets.compare_digest(str(row["execution_token"]), authority.execution_token):
            raise DomainError(ErrorCode.EXECUTION_TOKEN_INVALID, aggregate_type="Attempt")
        if row["job_state"] != "running" or row["attempt_state"] != "running":
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
        row = session.execute(_BY_RUN_FOR_UPDATE, {"run_id": run_id}).mappings().first()
        if row is None:
            return
        attempt_state = str(row["attempt_state"])
        job_state = str(row["job_state"])
        if attempt_state in {"created", "leased", "running"}:
            target = "lost" if attempt_state in {"leased", "running"} else "cancelled"
            self._advance_attempt(
                session, str(row["current_attempt_id"]), attempt_state, target
            )
            session.execute(_RELEASE_LEASE, {"attempt_id": row["current_attempt_id"]})
        if job_state == "running":
            self._advance_job(session, str(row["job_id"]), "running", "failed")
        elif job_state == "leased":
            self._advance_job(session, str(row["job_id"]), "leased", "failed")

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
