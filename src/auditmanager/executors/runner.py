"""The pull channel, runner side: tokens and the tasks a runner takes (`EXEC-PULL-01`, `R-143`).

A runner is a Claude Code session behind the stdio bridge, or an unattended agent. It reaches the
stand over HTTPS with a **runner token** and never reaches PostgreSQL or S3 (`R-143c`): the ``api``
runs these functions on its behalf. The wire is ``tools/executor-runner/RUNNER_API.md``.

Tokens
------
A token is ``amr_`` + eight characters + ``_`` + 43 characters of url-safe base64 (256 bits).
Only its SHA-256 is stored; the value is returned **once**, by :func:`issue_runner_token`, and an
identical repeat of the request cannot return it again (it answers the conflict
``token_shown_once``). The first twelve characters (``token_prefix``) are the non-secret part an
administrator reads on the screen and the row is looked up by; the hash is then compared with
:func:`hmac.compare_digest`. A token belongs to one connection and opens that connection's tasks
and nobody else's; a revoked, expired or archived-connection token is the same ``None`` as a
wrong one, so a caller learns nothing about which it was.

Tasks
-----
``open -> claimed -> answered | failed``, and ``expired`` or ``cancelled`` from ``open`` or
``claimed``. A claim is a lease (:data:`CLAIM_LEASE_SECONDS`) that the runner extends while it
works, never beyond the task's ``deadline_at``; a lapsed lease returns the task to ``open`` the
next time anyone claims. A claim joins the Attempt that waits for the task: a task whose Attempt
is no longer the current live one is never served.

Long poll
---------
:func:`claim_task` waits by sleeping in the thread that serves the request, and the API serves
synchronous handlers from a pool of 40 threads (anyio's default). So the wait is a shared
resource: :class:`LongPollSlots` lets one token park **one** claim and all tokens together
:data:`MAX_WAITING_CLAIMS_TOTAL`, leaving :data:`RESERVED_SYNC_THREADS` threads to every other
request (`SEC-RUNNER-CAP-01`, `F-06`). A claim over either bound is not refused: it looks once at
the rows, as ``wait_seconds: 0`` does, and answers a task if one is open or the contract's
empty ``204``. The state is the process's, as is the pool it protects; with several API
processes each bounds its own pool and a token can park one claim per process, never more
threads than one process has.

The functions here run in the caller's transaction and never commit. A refusal raises before any
write, so a refused answer (``422``) leaves the claim exactly as it was.

Nothing here puts a token, a payload or an answer in an event, a log line or an error detail.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import string
import threading
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy.orm import Session

from auditmanager.executors.answers import read_answer
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.runner_repository import (
    DEFAULT_CLAIM_IMAGES,
    ClaimedRow,
    RunnerRepository,
    RunnerTokenRecord,
    TaskRecord,
)
from auditmanager.ingest.public import (
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from auditmanager.jobs.public import append_execution_event
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.errors.envelope import UnsafeMessage, screen_message
from auditmanager.shared.identity import IdempotencyKey

__all__ = [
    "CLAIM_LEASE_SECONDS",
    "DEFAULT_TOKEN_DAYS",
    "MAX_WAITING_CLAIMS_PER_TOKEN",
    "MAX_WAITING_CLAIMS_TOTAL",
    "MAX_WAIT_SECONDS",
    "PAYLOAD_RETENTION_DAYS",
    "RESERVED_SYNC_THREADS",
    "SYNC_POOL_THREADS",
    "TOKEN_PREFIX_LENGTH",
    "ClaimedTask",
    "IssuedToken",
    "LongPollSlots",
    "RunnerPrincipal",
    "TaskAck",
    "authenticate_runner",
    "claim_task",
    "extend_claim",
    "fail_task",
    "generate_token",
    "hash_token",
    "issue_runner_token",
    "claimed_image",
    "long_polls_waiting",
    "open_task_count",
    "revoke_runner_token",
    "runner_tokens_of",
    "submit_answer",
]

_AGGREGATE = "ExecutorConnection"
#: The lease a claim holds before a runner must extend it. A runner extends at about a third of
#: it, so a runner that dies strands a task for at most this long.
CLAIM_LEASE_SECONDS: Final[int] = 120
#: ``wait_seconds`` is 0..25: the long poll stays under every proxy's read timeout.
MAX_WAIT_SECONDS: Final[int] = 25
#: The API's synchronous handlers run in anyio's default pool: 40 threads (measured in
#: `EXPOSURE-REVIEW-02`; nothing in ``src`` resizes it). A test pins the figure beside the share.
SYNC_POOL_THREADS: Final[int] = 40
#: How many of those threads long polls may hold, all tokens together.
MAX_WAITING_CLAIMS_TOTAL: Final[int] = 16
#: What is left to every other request while long polls wait: sign-in, reads, uploads.
RESERVED_SYNC_THREADS: Final[int] = SYNC_POOL_THREADS - MAX_WAITING_CLAIMS_TOTAL
#: How many claims one token may have waiting at once. A runner polls one claim at a time.
MAX_WAITING_CLAIMS_PER_TOKEN: Final[int] = 1
DEFAULT_TOKEN_DAYS: Final[int] = 30
MAX_TOKEN_DAYS: Final[int] = 365
#: The payload (the stand's documents) and the answer are cleared this long after a task ends.
PAYLOAD_RETENTION_DAYS: Final[int] = 7
#: ``amr_`` and eight lower-case characters: what an administrator reads and the row is found by.
TOKEN_PREFIX_LENGTH: Final[int] = 12
_TOKEN_SHAPE: Final[re.Pattern[str]] = re.compile(r"amr_[0-9a-z]{8}_[A-Za-z0-9_-]{43}")
_PREFIX_ALPHABET: Final[str] = string.ascii_lowercase + string.digits
_POLL_SECONDS: Final[float] = 1.0
#: The most of a failure reason that is kept.
_REASON_LIMIT: Final[int] = 512
_CONTROL: Final[re.Pattern[str]] = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class LongPollSlots:
    """Who may sleep in a thread of the API's pool: at most ``per_token`` waiting claims for one
    token and ``total`` for all of them. A counter under a lock, held by the process.

    :meth:`try_acquire` never blocks and never waits for a slot: a claim that cannot have one
    does not sleep. Every acquire is paired with a :meth:`release` in a ``finally``."""

    __slots__ = ("_per_token", "_total", "_held", "_count", "_lock")

    def __init__(self, *, per_token: int, total: int) -> None:
        if per_token < 1 or total < per_token:
            raise ValueError("a token needs one slot at least and the total cannot be smaller")
        self._per_token = per_token
        self._total = total
        self._held: dict[str, int] = {}
        self._count = 0
        self._lock = threading.Lock()

    @property
    def waiting(self) -> int:
        with self._lock:
            return self._count

    def try_acquire(self, token_id: str) -> bool:
        with self._lock:
            held = self._held.get(token_id, 0)
            if self._count >= self._total or held >= self._per_token:
                return False
            self._held[token_id] = held + 1
            self._count += 1
            return True

    def release(self, token_id: str) -> None:
        with self._lock:
            held = self._held.get(token_id, 0)
            if held < 1:
                raise RuntimeError("a long-poll slot was released that was not held")
            if held == 1:
                del self._held[token_id]
            else:
                self._held[token_id] = held - 1
            self._count -= 1


#: The process's slots. Production uses this one; a test passes its own to ``claim_task``.
_LONG_POLLS: Final[LongPollSlots] = LongPollSlots(
    per_token=MAX_WAITING_CLAIMS_PER_TOKEN, total=MAX_WAITING_CLAIMS_TOTAL)


def long_polls_waiting() -> int:
    """Claims of this process that hold a thread asleep right now (a test and a probe read it)."""
    return _LONG_POLLS.waiting


@dataclass(frozen=True, slots=True)
class IssuedToken:
    """The only moment a token's value exists outside the runner: this object."""

    record: RunnerTokenRecord
    value: str

    def __repr__(self) -> str:  # a value must not reach a log through a stray repr
        return f"IssuedToken(record={self.record!r}, value=<shown once>)"


@dataclass(frozen=True, slots=True)
class RunnerPrincipal:
    """Who a runner request is: one token of one connection. Not a user, and carrying no role."""

    token_id: str
    connection_id: str


@dataclass(frozen=True, slots=True)
class ClaimedTask:
    """A claimed task as the runner receives it."""

    task_id: str
    claim_expires_at: datetime
    deadline_at: datetime
    model: str
    system: str
    user_text: str
    output_schema: Mapping[str, Any]
    images: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class TaskAck:
    task_id: str
    state: str


# -- tokens ---------------------------------------------------------------------------------


def generate_token() -> tuple[str, str]:
    """``(value, prefix)`` of a new token: 256 bits of entropy behind a recognisable prefix."""
    prefix = "amr_" + "".join(secrets.choice(_PREFIX_ALPHABET) for _ in range(8))
    value = f"{prefix}_{secrets.token_urlsafe(32)}"
    assert _TOKEN_SHAPE.fullmatch(value) is not None
    return value, prefix


def hash_token(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def _admin(roles: Iterable[str]) -> None:
    if "admin" not in set(roles):
        raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin")


def _conflict(reason: str, message: str = "the request conflicts with the task's state"
              ) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, message=message, conflict_reason=reason)


def _begin(
    session: Session, ledger: CommandRepository, command_type: str, idempotency_key: str,
    payload: dict[str, object],
) -> CommandStarted | CommandReplay:
    return ledger.begin(
        session, command_type=command_type, idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint(payload),
    )


def issue_runner_token(
    session: Session, *, connection_id: str, expires_in_days: int | None, roles: Iterable[str],
    idempotency_key: str, actor_uid: str, executors: ExecutorRepository | None = None,
    repository: RunnerRepository | None = None, commands: CommandRepository | None = None,
) -> IssuedToken:
    """Issue a token for a ``pull`` connection and return its value, once.

    A repeat of the same request (same key) answers ``conflict``/``token_shown_once``: the value
    is not stored, so it cannot be shown again, and the administrator revokes the token whose
    response was lost and issues another."""
    _admin(roles)
    days = DEFAULT_TOKEN_DAYS if expires_in_days is None else expires_in_days
    if not 1 <= days <= MAX_TOKEN_DAYS:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="the token's lifetime is not acceptable",
            field="expires_in_days", constraint="range",
        )
    store, runner, ledger = (
        executors or ExecutorRepository(), repository or RunnerRepository(),
        commands or CommandRepository(),
    )
    claimed = _begin(session, ledger, "issue_runner_token", idempotency_key,
                     {"connection_id": connection_id, "expires_in_days": days})
    if isinstance(claimed, CommandReplay):
        raise _conflict("token_shown_once", "the token was shown once and cannot be shown again")
    connection = store.get_connection(session, connection_id, lock=True)
    if connection is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=_AGGREGATE)
    if connection.archived_at is not None:
        raise _conflict("connection_archived", "the connection is archived")
    if connection.kind != "pull":
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="only a pull connection takes runner tokens",
            field="kind", constraint="kind_not_pull",
        )
    value, prefix = generate_token()
    record = runner.insert_token(
        session, connection_id=connection_id, token_prefix=prefix, token_hash=hash_token(value),
        expires_in_days=days, actor_uid=actor_uid,
    )
    append_execution_event(
        session, event_type="executor.runner_token_issued", aggregate_type=_AGGREGATE,
        aggregate_id=connection_id,
        payload={"connection_id": connection_id, "token_id": record.token_id,
                 "actor_uid": actor_uid},
    )
    ledger.succeed(session, claimed.command_id, {"token_id": record.token_id})
    return IssuedToken(record=record, value=value)


def revoke_runner_token(
    session: Session, *, connection_id: str, token_id: str, roles: Iterable[str],
    idempotency_key: str, actor_uid: str, executors: ExecutorRepository | None = None,
    repository: RunnerRepository | None = None, commands: CommandRepository | None = None,
) -> RunnerTokenRecord:
    """Revoke a token. Idempotent: a token already revoked is answered as it stands."""
    _admin(roles)
    store, runner, ledger = (
        executors or ExecutorRepository(), repository or RunnerRepository(),
        commands or CommandRepository(),
    )
    claimed = _begin(session, ledger, "revoke_runner_token", idempotency_key,
                     {"connection_id": connection_id, "token_id": token_id})
    found = runner.get_token(session, token_id, lock=True)
    if found is None or found.connection_id != connection_id:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=_AGGREGATE)
    if isinstance(claimed, CommandReplay):
        return found
    if found.revoked_at is not None:
        ledger.succeed(session, claimed.command_id, {"token_id": token_id})
        return found
    record = runner.revoke_token(session, token_id, actor_uid=actor_uid)
    append_execution_event(
        session, event_type="executor.runner_token_revoked", aggregate_type=_AGGREGATE,
        aggregate_id=connection_id,
        payload={"connection_id": connection_id, "token_id": token_id, "actor_uid": actor_uid},
    )
    ledger.succeed(session, claimed.command_id, {"token_id": token_id})
    return record


def runner_tokens_of(
    session: Session, connection_id: str, repository: RunnerRepository | None = None
) -> list[RunnerTokenRecord]:
    return (repository or RunnerRepository()).list_tokens(session, connection_id)


def open_task_count(
    session: Session, connection_id: str, repository: RunnerRepository | None = None
) -> int:
    """Tasks waiting for, or held by, a runner right now."""
    return (repository or RunnerRepository()).count_open(session, [connection_id]).get(
        connection_id, 0)


def authenticate_runner(
    session: Session, presented: str, *, address: str | None,
    repository: RunnerRepository | None = None,
) -> RunnerPrincipal | None:
    """The principal of a presented runner token, or ``None`` for every way it can fail.

    The shape is checked before any read, so a user's credential or garbage costs no query. The
    stored hash is compared with :func:`hmac.compare_digest`; a missing, revoked, expired or
    archived-connection token is the same ``None``, so the answer is not an oracle for which."""
    if _TOKEN_SHAPE.fullmatch(presented) is None:
        return None
    store = repository or RunnerRepository()
    stored = store.token_by_prefix(session, presented[:TOKEN_PREFIX_LENGTH])
    candidate = hash_token(presented)
    if stored is None:
        # Compare against a fixed digest so a miss and a mismatch take the same path.
        hmac.compare_digest(candidate, hash_token(""))
        return None
    if not hmac.compare_digest(candidate, stored.token_hash) or not stored.usable:
        return None
    store.touch_token(session, stored.token_id, None if address is None else address[:64])
    return RunnerPrincipal(token_id=stored.token_id, connection_id=stored.connection_id)


# -- tasks ----------------------------------------------------------------------------------


def _not_found() -> DomainError:
    """Unknown task, or one of another connection: the answer never says which."""
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type="ExecutorTask")


def _own_task(
    session: Session, principal: RunnerPrincipal, task_id: str, store: RunnerRepository
) -> TaskRecord:
    task = store.get_task(session, task_id, lock=True)
    if task is None or task.connection_id != principal.connection_id:
        raise _not_found()
    return task


def _claimed(row: ClaimedRow) -> ClaimedTask:
    payload = row.payload
    return ClaimedTask(
        task_id=row.task_id, claim_expires_at=row.claim_expires_at, deadline_at=row.deadline_at,
        model=row.expected_model, system=str(payload["system"]),
        user_text=str(payload["user_text"]), output_schema=payload["output_schema"],
        images=tuple(payload.get("images", ())),
    )


def claimed_image(
    session: Session, principal: RunnerPrincipal, task_id: str, blob_id: str,
    repository: RunnerRepository | None = None,
) -> Mapping[str, Any]:
    """One image reference of a live claim, bound to this token and Attempt.

    The caller reads bytes outside this short transaction and repeats this check
    afterwards, so a cancelled task cannot be served after a slow Blob read.
    """
    store = repository or RunnerRepository()
    task = _own_task(session, principal, task_id, store)
    _must_hold(task, principal)
    if not store.live_claim_and_attempt(session, task_id, principal.token_id):
        raise _conflict("claim_lost", "the claim on the task is lost")
    payload = store.payload_of(session, task_id)
    for image in () if payload is None else payload.get("images", ()):
        if isinstance(image, Mapping) and image.get("blob_id") == blob_id:
            return image
    raise _not_found()


def claim_task(
    session_factory: Callable[[], Session], principal: RunnerPrincipal, *, wait_seconds: int,
    executors: ExecutorRepository | None = None, repository: RunnerRepository | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    slots: LongPollSlots | None = None, max_images: int | None = None,
) -> ClaimedTask | None:
    """Long poll: the connection's oldest open task, now claimed by this token, or ``None``
    after ``wait_seconds``. Each attempt is its own short transaction, so a waiting runner
    holds no row and no connection while it sleeps.

    A token holds at most the connection's current ``max_claimed_tasks`` claims at once, and a
    token whose limit is one and that already holds its claim is **given that same task again**,
    lease refreshed, so a lost response or a restarted runner does not strand it.

    The sleep holds a thread of the API's pool, so it needs a slot of ``slots`` (the process's
    by default): one waiting claim per token and :data:`MAX_WAITING_CLAIMS_TOTAL` in all. A
    claim that cannot have one looks once, as ``wait_seconds: 0`` does -- it still receives a
    task that is open and still redelivers its own -- and answers ``None`` (the ``204``)
    without sleeping. The runner's protocol is unchanged.

    ``max_images`` is the most images one task may carry that this runner serves, as it declared
    it in the claim (ADR-0025 decision 18); ``None`` is a claim that declared nothing, which every
    runner deployed before `CMP-EXEC-IMAGES-01` is, and means 1. The task handed back never has
    more images than that, on a fresh claim and on a redelivery."""
    declared = DEFAULT_CLAIM_IMAGES if max_images is None else max_images
    pool = _LONG_POLLS if slots is None else slots
    wait = max(0, min(int(wait_seconds), MAX_WAIT_SECONDS))
    holds_slot = wait > 0 and pool.try_acquire(principal.token_id)
    try:
        return _poll(
            session_factory, principal, wait=wait if holds_slot else 0, executors=executors,
            repository=repository, sleep=sleep, monotonic=monotonic, max_images=declared)
    finally:
        if holds_slot:
            pool.release(principal.token_id)


def _poll(
    session_factory: Callable[[], Session], principal: RunnerPrincipal, *, wait: int,
    executors: ExecutorRepository | None, repository: RunnerRepository | None,
    sleep: Callable[[float], None], monotonic: Callable[[], float], max_images: int,
) -> ClaimedTask | None:
    store = repository or RunnerRepository()
    revisions = executors or ExecutorRepository()
    stop = monotonic() + wait
    first = True
    while True:
        with session_factory() as session:
            current = revisions.current_revisions(session, [principal.connection_id]).get(
                principal.connection_id)
            limit = 1 if current is None else (current.settings.max_claimed_tasks or 1)
            store.sweep(session, principal.connection_id)
            if first:  # retention is housekeeping, once per call and not once per poll
                store.clear_terminal_payloads(
                    session, older_than_days=PAYLOAD_RETENTION_DAYS, limit=20)
                first = False
            row: ClaimedRow | None = None
            if limit == 1:
                row = store.redeliver(
                    session, token_id=principal.token_id, lease_seconds=CLAIM_LEASE_SECONDS,
                    max_images=max_images)
            if row is None and store.held_claims(session, principal.token_id) < limit:
                row = store.claim_next(
                    session, connection_id=principal.connection_id,
                    token_id=principal.token_id, lease_seconds=CLAIM_LEASE_SECONDS,
                    max_images=max_images)
            session.commit()
        if row is not None:
            return _claimed(row)
        remaining = stop - monotonic()
        if remaining <= 0:
            return None
        sleep(min(_POLL_SECONDS, remaining))


def extend_claim(
    session: Session, principal: RunnerPrincipal, task_id: str,
    repository: RunnerRepository | None = None,
) -> datetime:
    """Push the claim's lease forward by :data:`CLAIM_LEASE_SECONDS`, never beyond the
    deadline. ``conflict`` when the claim is not this token's any more."""
    store = repository or RunnerRepository()
    task = _own_task(session, principal, task_id, store)
    _must_hold(task, principal)
    lease = store.extend_claim(
        session, task_id=task_id, token_id=principal.token_id,
        lease_seconds=CLAIM_LEASE_SECONDS)
    if lease is None:  # the deadline passed between the read and the write
        raise _conflict("task_expired", "the task's deadline has passed")
    return lease


def _must_hold(task: TaskRecord, principal: RunnerPrincipal) -> None:
    """The refusals that say the task is not this runner's to work on. A lapsed lease alone is
    not one: the claim is lost when the task was returned to ``open`` or taken by another
    claim, which the next claim's sweep does. A passed deadline always is."""
    if task.state in ("answered", "failed", "expired", "cancelled"):
        raise _conflict("task_expired" if task.state == "expired" else "task_terminal",
                        f"the task is {task.state}")
    if task.past_deadline:
        raise _conflict("task_expired", "the task's deadline has passed")
    if task.state != "claimed" or task.claimed_by_token_id != principal.token_id:
        raise _conflict("claim_lost", "the claim on the task is lost")


def submit_answer(
    session: Session, principal: RunnerPrincipal, task_id: str, *, output_text: str,
    model: str, input_tokens: int | None, output_tokens: int | None,
    on_mismatch: Callable[[], Exception], repository: RunnerRepository | None = None,
) -> TaskAck:
    """Accept the runner's answer.

    Idempotent on the task: the same answer again is accepted, a different one is a conflict.
    ``on_mismatch`` builds the refusal for a declared model that is not the task's (the caller
    owns its status); both the model and the schema refusals leave the claim as it was."""
    store = repository or RunnerRepository()
    task = _own_task(session, principal, task_id, store)
    if task.state == "answered":
        stored_text, stored_model = store.answer_of(session, task_id)
        if (task.claimed_by_token_id == principal.token_id and stored_text == output_text
                and stored_model == model):
            return TaskAck(task_id, "answered")
        raise _conflict("answer_differs", "a different answer was already accepted")
    _must_hold(task, principal)
    if model != task.expected_model:
        raise on_mismatch()
    payload = store.payload_of(session, task_id)
    if payload is None:  # cleared payloads belong to terminal tasks; unreachable for a claim
        raise _conflict("task_terminal", "the task has no payload")
    violation = read_answer(payload["output_schema"], output_text)
    if violation is not None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message=_violation_message(violation),
            field="output_text", constraint="output_schema",
        )
    store.record_answer(
        session, task_id=task_id, answer_text=output_text, declared_model=model,
        input_tokens=input_tokens, output_tokens=output_tokens)
    return TaskAck(task_id, "answered")


def _violation_message(violation: object) -> str:
    """Name the first violated location and keyword. The envelope's own screen has the last
    word: a location it would refuse falls back to the sentence without one."""
    message = f"the answer violates the output schema ({violation})"
    try:
        return screen_message(message)
    except UnsafeMessage:
        return "the answer violates the output schema"


def _scrub(reason: str) -> str:
    cleaned = _CONTROL.sub(" ", reason).strip()
    return (cleaned or "no reason given")[:_REASON_LIMIT]


def fail_task(
    session: Session, principal: RunnerPrincipal, task_id: str, *, reason: str,
    repository: RunnerRepository | None = None,
) -> TaskAck:
    """The runner reports that it cannot answer. The task ends ``failed``; the worker that
    waits treats a failure after a claim as outcome-unknown (the model may have run)."""
    store = repository or RunnerRepository()
    task = _own_task(session, principal, task_id, store)
    if task.state == "failed":
        if task.claimed_by_token_id != principal.token_id:
            raise _conflict("claim_lost", "the claim on the task is lost")
        return TaskAck(task_id, "failed")
    _must_hold(task, principal)
    store.record_failure(session, task_id=task_id, reason=_scrub(reason))
    return TaskAck(task_id, "failed")
