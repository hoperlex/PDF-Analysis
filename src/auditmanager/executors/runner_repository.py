"""The only writer and reader of ``executor_runner_token`` and ``executor_task`` (migration ``0031``).

Statements only: the rules live in ``runner.py`` and ``pull.py``. Every comparison with time uses
the database clock (``clock_timestamp()``), so the ``api`` that serves a runner, the worker that
waits for it and a test that moves a lease all agree on one clock.

A token's hash is returned to exactly one caller, :meth:`RunnerRepository.token_by_prefix`, which
hands it to the comparison in ``runner.authenticate``. No method here returns a payload or an
answer except :meth:`task_for_claim` (to the runner that holds the claim) and
:meth:`answer_of` (to the worker that waits for it).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import ExecutorRunnerTokenId, ExecutorTaskId

__all__ = [
    "ClaimedRow",
    "RunnerRepository",
    "RunnerTokenRecord",
    "StoredToken",
    "TaskRecord",
]

#: The channel a worker is woken on when a runner answers or fails a task.
TASK_DONE_CHANNEL: Final[str] = "auditmanager_executor_task_done"
#: The channel a runner-facing process may be woken on when a task is written. The ``api``'s
#: long poll also polls, so a lost notification costs at most one second.
TASK_OPEN_CHANNEL: Final[str] = "auditmanager_executor_task_open"

_TOKEN_COLUMNS: Final = (
    "token_id, connection_id, token_prefix, created_at, created_by, expires_at, revoked_at, "
    "revoked_by, last_seen_at, last_seen_address"
)
_TASK_COLUMNS: Final = (
    "task_id, connection_id, revision_id, origin, run_id, attempt_id, model_call_id, probe_id, "
    "state, expected_model, created_at, deadline_at, claimed_by_token_id, claim_expires_at, "
    "first_claimed_at, claim_count, declared_model, declared_input_tokens, "
    "declared_output_tokens, fail_reason, terminal_at, payload_cleared_at, "
    "(deadline_at <= clock_timestamp()) AS past_deadline"
)
#: A task whose Attempt is not the live, current one of its Job is never served.
_ATTEMPT_LIVE: Final = (
    "EXISTS (SELECT 1 FROM attempt a JOIN job j ON j.job_id = a.job_id "
    "AND j.current_attempt_id = a.attempt_id WHERE a.attempt_id = t.attempt_id "
    "AND a.state IN ('leased', 'running'))"
)


#: The most images a claim may declare it serves, and the count that applies to a claim that
#: declares none: every runner deployed before `CMP-EXEC-IMAGES-01` sends no ``max_images``.
MAX_CLAIM_IMAGES: Final[int] = 8
DEFAULT_CLAIM_IMAGES: Final[int] = 1


def _image_count(alias: str | None = None) -> str:
    """The SQL for how many images a task's payload carries, for the claim gate.

    Absent ``images`` is none. A present member that is not a JSON array is a malformed payload,
    and counts as more than any claim can declare, so that it is never handed out (the gate fails
    closed; it never reads a malformed list as an empty one)."""
    images = f"{alias + '.' if alias else ''}payload -> 'images'"
    return (f"CASE WHEN {images} IS NULL THEN 0 WHEN jsonb_typeof({images}) = 'array' "
            f"THEN jsonb_array_length({images}) ELSE {MAX_CLAIM_IMAGES + 1} END")


def _declared(max_images: int) -> int:
    if type(max_images) is not int or not 1 <= max_images <= MAX_CLAIM_IMAGES:
        raise ValueError("max_images is an integer from 1 to 8")
    return max_images


@dataclass(frozen=True, slots=True)
class RunnerTokenRecord:
    """A token's metadata. The hash is not a field."""

    token_id: str
    connection_id: str
    token_prefix: str
    created_at: datetime
    created_by: str
    expires_at: datetime
    revoked_at: datetime | None
    revoked_by: str | None
    last_seen_at: datetime | None
    last_seen_address: str | None


@dataclass(frozen=True, slots=True)
class StoredToken:
    """What authentication reads: the hash and whether the token is usable *now* (by the
    database clock): not revoked, not expired, on a connection that is not archived."""

    token_id: str
    connection_id: str
    token_hash: bytes
    usable: bool


@dataclass(frozen=True, slots=True)
class TaskRecord:
    """A task without its payload or its answer."""

    task_id: str
    connection_id: str
    revision_id: str
    origin: str
    run_id: str | None
    attempt_id: str | None
    model_call_id: str | None
    probe_id: str | None
    state: str
    expected_model: str
    created_at: datetime
    deadline_at: datetime
    claimed_by_token_id: str | None
    claim_expires_at: datetime | None
    first_claimed_at: datetime | None
    claim_count: int
    declared_model: str | None
    declared_input_tokens: int | None
    declared_output_tokens: int | None
    fail_reason: str | None
    terminal_at: datetime | None
    payload_cleared_at: datetime | None
    #: By the database clock at the moment of the read.
    past_deadline: bool


@dataclass(frozen=True, slots=True)
class ClaimedRow:
    """A task as a runner receives it: the lease, the deadline and the payload."""

    task_id: str
    claim_expires_at: datetime
    deadline_at: datetime
    expected_model: str
    payload: Mapping[str, Any]


def _token(row: Mapping[str, Any]) -> RunnerTokenRecord:
    return RunnerTokenRecord(**{name: row[name] for name in (
        "token_id", "connection_id", "token_prefix", "created_at", "created_by", "expires_at",
        "revoked_at", "revoked_by", "last_seen_at", "last_seen_address")})


def _task(row: Mapping[str, Any]) -> TaskRecord:
    return TaskRecord(**{name: row[name] for name in (
        "task_id", "connection_id", "revision_id", "origin", "run_id", "attempt_id",
        "model_call_id", "probe_id", "state", "expected_model", "created_at", "deadline_at",
        "claimed_by_token_id", "claim_expires_at", "first_claimed_at", "claim_count",
        "declared_model", "declared_input_tokens", "declared_output_tokens", "fail_reason",
        "terminal_at", "payload_cleared_at", "past_deadline")})


def _payload(raw: Any) -> Mapping[str, Any]:
    return raw if isinstance(raw, Mapping) else json.loads(raw)


class RunnerRepository:
    """Stateless; every method takes the caller's session and never commits."""

    # -- tokens ----------------------------------------------------------------------------

    def insert_token(
        self, session: Session, *, connection_id: str, token_prefix: str, token_hash: bytes,
        expires_in_days: int, actor_uid: str,
    ) -> RunnerTokenRecord:
        row = session.execute(text(
            "INSERT INTO executor_runner_token (token_id, connection_id, token_prefix, "
            "token_hash, created_by, expires_at) VALUES (:id, :c, :prefix, :hash, :actor, "
            "clock_timestamp() + make_interval(days => :days)) "
            f"RETURNING {_TOKEN_COLUMNS}"
        ), {"id": str(ExecutorRunnerTokenId.new()), "c": connection_id, "prefix": token_prefix,
            "hash": token_hash, "actor": actor_uid, "days": expires_in_days}).mappings().one()
        return _token(row)

    def get_token(
        self, session: Session, token_id: str, *, lock: bool = False
    ) -> RunnerTokenRecord | None:
        row = session.execute(text(
            f"SELECT {_TOKEN_COLUMNS} FROM executor_runner_token WHERE token_id = :id"
            + (" FOR UPDATE" if lock else "")
        ), {"id": token_id}).mappings().first()
        return None if row is None else _token(row)

    def list_tokens(
        self, session: Session, connection_id: str, *, limit: int = 50
    ) -> list[RunnerTokenRecord]:
        rows = session.execute(text(
            f"SELECT {_TOKEN_COLUMNS} FROM executor_runner_token WHERE connection_id = :c "
            "ORDER BY created_at DESC, token_id DESC LIMIT :limit"
        ), {"c": connection_id, "limit": limit}).mappings().all()
        return [_token(row) for row in rows]

    def revoke_token(self, session: Session, token_id: str, *, actor_uid: str) -> RunnerTokenRecord:
        row = session.execute(text(
            "UPDATE executor_runner_token SET revoked_at = clock_timestamp(), "
            "revoked_by = :actor WHERE token_id = :id AND revoked_at IS NULL "
            f"RETURNING {_TOKEN_COLUMNS}"
        ), {"id": token_id, "actor": actor_uid}).mappings().first()
        if row is None:  # already revoked: the metadata as it stands
            found = self.get_token(session, token_id)
            assert found is not None
            return found
        return _token(row)

    def token_by_prefix(self, session: Session, token_prefix: str) -> StoredToken | None:
        row = session.execute(text(
            "SELECT t.token_id, t.connection_id, t.token_hash, "
            "(t.revoked_at IS NULL AND t.expires_at > clock_timestamp() "
            "AND c.archived_at IS NULL) AS usable "
            "FROM executor_runner_token t JOIN executor_connection c "
            "ON c.connection_id = t.connection_id WHERE t.token_prefix = :prefix"
        ), {"prefix": token_prefix}).first()
        if row is None:
            return None
        return StoredToken(row[0], row[1], bytes(row[2]), bool(row[3]))

    def touch_token(
        self, session: Session, token_id: str, address: str | None, *, every_seconds: int = 5
    ) -> None:
        """Record that the token was seen, at most once per ``every_seconds`` unless the
        address changed."""
        session.execute(text(
            "UPDATE executor_runner_token SET last_seen_at = clock_timestamp(), "
            "last_seen_address = :address WHERE token_id = :id AND (last_seen_at IS NULL "
            "OR last_seen_address IS DISTINCT FROM :address "
            "OR last_seen_at < clock_timestamp() - make_interval(secs => :every))"
        ), {"id": token_id, "address": address, "every": every_seconds})

    # -- tasks: the worker's side ----------------------------------------------------------

    def insert_task(
        self, session: Session, *, connection_id: str, revision_id: str, origin: str,
        run_id: str | None, attempt_id: str | None, model_call_id: str | None,
        probe_id: str | None, expected_model: str, payload: Mapping[str, Any],
        deadline_seconds: float,
    ) -> TaskRecord:
        row = session.execute(text(
            "INSERT INTO executor_task (task_id, connection_id, revision_id, origin, run_id, "
            "attempt_id, model_call_id, probe_id, expected_model, payload, deadline_at) "
            "VALUES (:id, :c, :r, :origin, :run, :attempt, :call, :probe, :model, "
            "CAST(:payload AS jsonb), clock_timestamp() + make_interval(secs => :seconds)) "
            f"RETURNING {_TASK_COLUMNS}"
        ), {"id": str(ExecutorTaskId.new()), "c": connection_id, "r": revision_id,
            "origin": origin, "run": run_id, "attempt": attempt_id, "call": model_call_id,
            "probe": probe_id, "model": expected_model,
            "payload": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            "seconds": deadline_seconds}).mappings().one()
        session.execute(text("SELECT pg_notify(:channel, '')"), {"channel": TASK_OPEN_CHANNEL})
        return _task(row)

    def get_task(
        self, session: Session, task_id: str, *, lock: bool = False
    ) -> TaskRecord | None:
        row = session.execute(text(
            f"SELECT {_TASK_COLUMNS} FROM executor_task WHERE task_id = :id"
            + (" FOR UPDATE" if lock else "")
        ), {"id": task_id}).mappings().first()
        return None if row is None else _task(row)

    def answer_of(self, session: Session, task_id: str) -> tuple[str | None, str | None]:
        """``(answer_text, declared_model)`` of a task: for the worker that waited for it."""
        row = session.execute(text(
            "SELECT answer_text, declared_model FROM executor_task WHERE task_id = :id"
        ), {"id": task_id}).first()
        return (None, None) if row is None else (row[0], row[1])

    def expire_task(self, session: Session, task_id: str) -> TaskRecord | None:
        """The worker's deadline: ``open`` or ``claimed`` becomes ``expired``. ``None`` when the
        task was already terminal (a runner answered in the last instant)."""
        row = session.execute(text(
            "UPDATE executor_task SET state = 'expired', terminal_at = clock_timestamp() "
            "WHERE task_id = :id AND state IN ('open', 'claimed') "
            f"RETURNING {_TASK_COLUMNS}"
        ), {"id": task_id}).mappings().first()
        return None if row is None else _task(row)

    def cancel_task(self, session: Session, task_id: str) -> bool:
        """The waiting worker stopped for a reason of its own: nobody should take it."""
        return bool(session.execute(text(
            "UPDATE executor_task SET state = 'cancelled', terminal_at = clock_timestamp() "
            "WHERE task_id = :id AND state IN ('open', 'claimed')"
        ), {"id": task_id}).rowcount)

    def count_open(self, session: Session, connection_ids: Sequence[str]) -> dict[str, int]:
        if not connection_ids:
            return {}
        rows = session.execute(text(
            "SELECT connection_id, count(*) FROM executor_task WHERE connection_id = ANY(:ids) "
            "AND state IN ('open', 'claimed') AND deadline_at > clock_timestamp() "
            "GROUP BY connection_id"
        ), {"ids": list(connection_ids)}).all()
        return {row[0]: int(row[1]) for row in rows}

    # -- tasks: the runner's side ----------------------------------------------------------

    def sweep(self, session: Session, connection_id: str) -> None:
        """Bring the connection's live tasks up to date, in this order: a task whose Attempt is
        gone is cancelled; a task past its deadline expires; a claim whose lease lapsed returns
        the task to ``open``. Idempotent, and run before every claim."""
        session.execute(text(
            "UPDATE executor_task t SET state = 'cancelled', terminal_at = clock_timestamp() "
            "WHERE t.connection_id = :c AND t.state IN ('open', 'claimed') "
            f"AND t.attempt_id IS NOT NULL AND NOT {_ATTEMPT_LIVE}"
        ), {"c": connection_id})
        session.execute(text(
            "UPDATE executor_task SET state = 'expired', terminal_at = clock_timestamp() "
            "WHERE connection_id = :c AND state IN ('open', 'claimed') "
            "AND deadline_at <= clock_timestamp()"
        ), {"c": connection_id})
        session.execute(text(
            "UPDATE executor_task SET state = 'open', claimed_by_token_id = NULL, "
            "claim_expires_at = NULL WHERE connection_id = :c AND state = 'claimed' "
            "AND claim_expires_at <= clock_timestamp()"
        ), {"c": connection_id})

    def held_claims(self, session: Session, token_id: str) -> int:
        return int(session.execute(text(
            "SELECT count(*) FROM executor_task WHERE claimed_by_token_id = :t "
            "AND state = 'claimed' AND claim_expires_at > clock_timestamp()"
        ), {"t": token_id}).scalar_one())

    def redeliver(
        self, session: Session, *, token_id: str, lease_seconds: int,
        max_images: int = DEFAULT_CLAIM_IMAGES,
    ) -> ClaimedRow | None:
        """The claim this token already holds, with its lease refreshed.

        Never a task with more images than ``max_images``: a claim that declares fewer than the
        held task needs is not handed it again (its lease lapses and the task returns to ``open``)."""
        row = session.execute(text(
            "UPDATE executor_task SET claim_expires_at = "
            "LEAST(clock_timestamp() + make_interval(secs => :lease), deadline_at) "
            "WHERE task_id = (SELECT task_id FROM executor_task WHERE claimed_by_token_id = :t "
            "AND state = 'claimed' AND claim_expires_at > clock_timestamp() "
            f"AND {_image_count()} <= :max_images "
            "ORDER BY created_at, task_id LIMIT 1 FOR UPDATE) "
            "RETURNING task_id, claim_expires_at, deadline_at, expected_model, payload"
        ), {"t": token_id, "lease": lease_seconds, "max_images": _declared(max_images)}).first()
        return None if row is None else ClaimedRow(row[0], row[1], row[2], row[3], _payload(row[4]))

    def claim_next(
        self, session: Session, *, connection_id: str, token_id: str, lease_seconds: int,
        max_images: int = DEFAULT_CLAIM_IMAGES,
    ) -> ClaimedRow | None:
        """Claim the oldest open task of the connection whose Attempt is live **and whose images
        the claim can serve**: never a task with more images than ``max_images`` (ADR-0025
        decision 18). A task too large for this claim is skipped, not waited on, so it neither
        blocks the claims behind it nor is handed to a runner that would have to refuse it."""
        row = session.execute(text(
            "UPDATE executor_task t SET state = 'claimed', claimed_by_token_id = :token, "
            "claim_expires_at = LEAST(clock_timestamp() + make_interval(secs => :lease), "
            "t.deadline_at), first_claimed_at = COALESCE(t.first_claimed_at, clock_timestamp()), "
            "claim_count = t.claim_count + 1 "
            "WHERE t.task_id = (SELECT p.task_id FROM executor_task p WHERE p.connection_id = :c "
            "AND p.state = 'open' AND p.deadline_at > clock_timestamp() "
            "AND (p.attempt_id IS NULL OR EXISTS (SELECT 1 FROM attempt a JOIN job j "
            "ON j.job_id = a.job_id AND j.current_attempt_id = a.attempt_id "
            "WHERE a.attempt_id = p.attempt_id AND a.state IN ('leased', 'running'))) "
            f"AND {_image_count('p')} <= :max_images "
            "ORDER BY p.created_at, p.task_id FOR UPDATE OF p SKIP LOCKED LIMIT 1) "
            "RETURNING t.task_id, t.claim_expires_at, t.deadline_at, t.expected_model, t.payload"
        ), {"c": connection_id, "token": token_id, "lease": lease_seconds,
            "max_images": _declared(max_images)}).first()
        return None if row is None else ClaimedRow(row[0], row[1], row[2], row[3], _payload(row[4]))

    def payload_of(self, session: Session, task_id: str) -> Mapping[str, Any] | None:
        row = session.execute(text(
            "SELECT payload FROM executor_task WHERE task_id = :id"
        ), {"id": task_id}).first()
        return None if row is None or row[0] is None else _payload(row[0])

    def live_claim_and_attempt(self, session: Session, task_id: str, token_id: str) -> bool:
        """Check the lease and current Attempt by the database clock before image egress."""
        return bool(session.execute(text(
            "SELECT EXISTS (SELECT 1 FROM executor_task t WHERE t.task_id = :id "
            "AND t.claimed_by_token_id = :token AND t.state = 'claimed' "
            "AND t.claim_expires_at > clock_timestamp() "
            "AND t.deadline_at > clock_timestamp() "
            f"AND (t.attempt_id IS NULL OR {_ATTEMPT_LIVE}))"
        ), {"id": task_id, "token": token_id}).scalar_one())

    def extend_claim(
        self, session: Session, *, task_id: str, token_id: str, lease_seconds: int
    ) -> datetime | None:
        row = session.execute(text(
            "UPDATE executor_task SET claim_expires_at = "
            "LEAST(clock_timestamp() + make_interval(secs => :lease), deadline_at) "
            "WHERE task_id = :id AND state = 'claimed' AND claimed_by_token_id = :t "
            "AND deadline_at > clock_timestamp() RETURNING claim_expires_at"
        ), {"id": task_id, "t": token_id, "lease": lease_seconds}).first()
        return None if row is None else row[0]

    def record_answer(
        self, session: Session, *, task_id: str, answer_text: str, declared_model: str,
        input_tokens: int | None, output_tokens: int | None,
    ) -> None:
        session.execute(text(
            "UPDATE executor_task SET state = 'answered', answer_text = :answer, "
            "declared_model = :model, declared_input_tokens = :input, "
            "declared_output_tokens = :output, terminal_at = clock_timestamp() "
            "WHERE task_id = :id AND state = 'claimed'"
        ), {"id": task_id, "answer": answer_text, "model": declared_model,
            "input": input_tokens, "output": output_tokens})
        session.execute(text("SELECT pg_notify(:channel, :id)"),
                        {"channel": TASK_DONE_CHANNEL, "id": task_id})

    def record_failure(self, session: Session, *, task_id: str, reason: str) -> None:
        session.execute(text(
            "UPDATE executor_task SET state = 'failed', fail_reason = :reason, "
            "terminal_at = clock_timestamp() WHERE task_id = :id AND state = 'claimed'"
        ), {"id": task_id, "reason": reason})
        session.execute(text("SELECT pg_notify(:channel, :id)"),
                        {"channel": TASK_DONE_CHANNEL, "id": task_id})

    def clear_terminal_payloads(
        self, session: Session, *, older_than_days: int, limit: int = 100
    ) -> int:
        """Clear the payload and the answer of tasks terminal for more than ``older_than_days``;
        the row stays as the trail."""
        return int(session.execute(text(
            "UPDATE executor_task SET payload = NULL, answer_text = NULL, "
            "payload_cleared_at = clock_timestamp() WHERE task_id IN ("
            "SELECT task_id FROM executor_task WHERE terminal_at IS NOT NULL "
            "AND payload_cleared_at IS NULL "
            "AND terminal_at < clock_timestamp() - make_interval(days => :days) "
            "ORDER BY terminal_at LIMIT :limit FOR UPDATE SKIP LOCKED)"
        ), {"days": older_than_days, "limit": limit}).rowcount or 0)
