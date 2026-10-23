"""The ``pull`` connection kind as a model adapter, and its «Проверить» (`EXEC-PULL-01`, `R-143`).

A ``pull`` connection has no address the stand can call: a runner (a Claude Code session behind
the stdio bridge, or an unattended agent) calls the stand and takes the work. So the adapter does
not send a request. It **writes a task and waits for the answer inside the Attempt** (plan
section 3, long waits); the ``api`` serves the runner (``runner.py``) and the worker reads the
result from the same table (`R-143c`: the remote party only ever calls HTTP).

The wait
--------
``deadline = min(revision answer deadline, watchdog remaining - 60 s)``, from the
:class:`~auditmanager.jobs.public.AttemptContext` the factory passes in. The worker waits on a
``LISTEN`` connection and polls as well, so a lost notification costs one poll interval. When
the deadline passes the task is expired and the call fails as ``dependency_unavailable``,
``retry_safe=False`` (a plain ``DomainError`` would be marked ``provider_effect_uncertain`` and
retried; this must not be):

* a task **never claimed** is ``not_sent`` with ``dependency: no_executor_online`` -- no runner
  ever took it, so no model ran, and the stage records a not-processed effect;
* a task **claimed and not answered**, or reported failed after a claim, is ``outcome_unknown``
  -- the model may have run.

What the answer is
------------------
The runner declares the model it ran as; the server already held it equal to the revision's
gateway model and held the document to the task's output schema when it accepted the answer. The
:class:`~auditmanager.analysis.public.ModelResponse` carries the declared model as its reported
model, so `R-133` applies unchanged (the stage compares it again), and the call row records
``identity_basis: declared`` (``IDENTITY_BASIS_BY_KIND``): a declared model is an assertion, not
evidence. The cost is ``None``: the runner's own token counts are carried, no price is invented,
and a ``not_metered`` revision is recorded as unmetered by the meter.
"""

from __future__ import annotations

import dataclasses
import logging
import re
import time
from collections.abc import Callable, Mapping
from typing import Any, Final

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ModelRequest,
    ModelResponse,
    ProviderMode,
    ProxyDispatchError,
)
from auditmanager.executors.answers import SchemaNotSupported, check_supported
from auditmanager.executors.model import RevisionRecord
from auditmanager.executors.probes import ProbeResult
from auditmanager.executors.runner_repository import (
    TASK_DONE_CHANNEL,
    RunnerRepository,
    TaskRecord,
)
from auditmanager.shared.errors import ErrorCode
from auditmanager.storage.public import derive_blob_id

__all__ = [
    "DEADLINE_MARGIN_SECONDS",
    "PROBE_ANSWER_SECONDS",
    "PROBE_CLAIM_SECONDS",
    "PullAdapter",
    "TaskWaiter",
    "answer_window",
    "build_pull_adapter",
    "probe_pull",
]

_log = logging.getLogger(__name__)

#: What the watchdog must keep in hand beyond the wait: the evidence gate and the terminal.
DEADLINE_MARGIN_SECONDS: Final[int] = 60
#: «Проверить»: a runner must take the synthetic task within this long ...
PROBE_CLAIM_SECONDS: Final[int] = 120
#: ... and answer it within this long after taking it.
PROBE_ANSWER_SECONDS: Final[int] = 120
_POLL_SECONDS: Final[float] = 2.0
_DEPENDENCY_NONE_ONLINE: Final[str] = "no_executor_online"
_DEPENDENCY_DEADLINE: Final[str] = "executor_deadline"
_DEPENDENCY_FAILED: Final[str] = "executor_task_failed"
_ECHO_SYSTEM: Final[str] = (
    "You are answering a connection check for an audit application. Reply with one JSON "
    "document that has the single field \"echo\" set to the exact text you were given."
)
MAX_RUNNER_IMAGE_BYTES: Final[int] = 16 * 1024 * 1024
_SHA256: Final = re.compile(r"[0-9a-f]{64}\Z")
_BLOCK_ID: Final = re.compile(r"blk_[0-9a-f]{32}\Z")


def answer_window(revision_deadline_seconds: int, context: Any | None) -> float | None:
    """Seconds a task may wait: the revision's answer deadline cut to what the watchdog leaves,
    minus the margin. ``None`` when less than one second is left, which the caller refuses."""
    window = float(revision_deadline_seconds)
    if context is not None:
        window = min(window, float(context.remaining_seconds()) - DEADLINE_MARGIN_SECONDS)
    return None if window < 1.0 else window


class TaskWaiter:
    """``LISTEN`` on a connection of its own for the runner's answer, surviving its loss.

    The connection is taken from the engine and detached from the pool, like the worker's job
    wakeup: a pooled connection held for minutes would starve the pool. Without an engine, or
    when ``LISTEN`` cannot be made, :meth:`wait` simply sleeps, and the caller's poll decides."""

    def __init__(self, engine: Engine | None, *, channel: str = TASK_DONE_CHANNEL) -> None:
        self._engine = engine
        self._channel = channel
        self._connection: Any = None
        self._failed = engine is None

    def wait(self, seconds: float) -> None:
        if seconds <= 0:
            return
        if self._connection is None and not self._failed:
            self._connect()
        if self._connection is None:
            time.sleep(seconds)
            return
        try:
            list(self._connection.notifies(timeout=seconds, stop_after=1))
        except Exception as failure:  # noqa: BLE001 - the poll still decides
            _log.warning("executor task LISTEN lost (%s); polling", type(failure).__name__)
            self.close()
            self._failed = True
            time.sleep(min(seconds, _POLL_SECONDS))

    def _connect(self) -> None:
        assert self._engine is not None
        try:
            pooled = self._engine.raw_connection()
            connection = pooled.driver_connection
            pooled.detach()
            connection.rollback()
            connection.autocommit = True
            connection.execute(f"LISTEN {self._channel}")
        except Exception as failure:  # noqa: BLE001
            _log.warning("executor task LISTEN not established (%s); polling",
                         type(failure).__name__)
            self._failed = True
            return
        self._connection = connection

    def close(self) -> None:
        connection, self._connection = self._connection, None
        if connection is not None:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a dead socket
                pass


def _with_reported_model(response: ModelResponse, name: str | None) -> ModelResponse:
    """Attach the declared model once ``ModelResponse`` carries a reported model
    (`MODEL-IDENTITY-CHECK-01`); until the two lanes meet it is a no-op."""
    if "model" in {field.name for field in dataclasses.fields(response)}:
        return dataclasses.replace(response, model=name)  # type: ignore[call-arg]
    return response


def _error(
    dispatch_class: str, dependency: str, message: str, *, code: ErrorCode =
    ErrorCode.DEPENDENCY_UNAVAILABLE,
) -> ProxyDispatchError:
    return ProxyDispatchError(
        code, dispatch_class=dispatch_class, retry_safe=False, message=message,
        details={"dependency": dependency} if code is ErrorCode.DEPENDENCY_UNAVAILABLE else None,
    )


def _task_payload(request: ModelRequest) -> dict[str, Any]:
    """``system``, ``user_text`` and ``output_schema`` out of the Anthropic-shaped body the
    prompt module builds (the same reading the proxy's translation does)."""
    body: Mapping[str, Any] = request.body
    system = body.get("system")
    parts = [
        str(message.get("content", "")) for message in body.get("messages", ())
        if isinstance(message, Mapping) and message.get("role", "user") == "user"
    ]
    output = body.get("output_config")
    schema = None
    if isinstance(output, Mapping) and isinstance(output.get("format"), Mapping):
        schema = output["format"].get("schema")
    if not isinstance(system, str) or not parts:
        raise _error("not_sent", "executor_request", "the request has no prompt to hand over",
                     code=ErrorCode.ANALYSIS_INPUT_INVALID)
    images = body.get("images", ())
    if not isinstance(images, (list, tuple)) or len(images) > 1:
        raise _error("not_sent", "executor_request", "one image is allowed per runner task",
                     code=ErrorCode.ANALYSIS_INPUT_INVALID)
    checked_images: list[dict[str, Any]] = []
    for raw in images:
        if not isinstance(raw, Mapping) or set(raw) != {
            "blob_id", "portal_block_id", "sha256", "size_bytes", "media_type",
        }:
            raise _error("not_sent", "executor_request", "invalid runner image reference",
                         code=ErrorCode.ANALYSIS_INPUT_INVALID)
        blob_id, block_id, digest, size = (
            raw["blob_id"], raw["portal_block_id"], raw["sha256"], raw["size_bytes"],
        )
        if (not isinstance(blob_id, str) or not isinstance(block_id, str)
                or _BLOCK_ID.fullmatch(block_id) is None
                or not isinstance(digest, str) or _SHA256.fullmatch(digest) is None
                or type(size) is not int or not 1 <= size <= MAX_RUNNER_IMAGE_BYTES
                or raw["media_type"] != "image/png"
                or blob_id != str(derive_blob_id(sha256=digest, size=size))):
            raise _error("not_sent", "executor_request", "invalid runner image reference",
                         code=ErrorCode.ANALYSIS_INPUT_INVALID)
        checked_images.append(dict(raw))
    payload = {
        "system": system, "user_text": "\n\n".join(parts),
        "output_schema": schema if isinstance(schema, Mapping) else {"type": "object"},
    }
    if checked_images:
        payload["images"] = checked_images
    return payload


class PullAdapter:
    """One ``pull`` revision for one Attempt. ``complete`` writes a task and waits.

    ``session_factory`` opens the short transactions that write and read the task; ``engine``
    (optional) is the source of the ``LISTEN`` connection. ``sleep`` and ``monotonic`` are
    injectable so a test states the clock instead of waiting for it."""

    #: Recorded on the call row: the model is the runner's assertion, not the response's word.
    identity_basis: Final[str] = "declared"

    __slots__ = ("_context", "_engine", "_monotonic", "_poll", "_repository", "_revision",
                 "_sessions")

    def __init__(
        self, *, session_factory: Callable[[], Session], revision: RevisionRecord,
        context: Any | None, engine: Engine | None = None,
        repository: RunnerRepository | None = None, poll_seconds: float = _POLL_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if revision.settings.answer_deadline_seconds is None:
            raise ValueError("a pull revision carries an answer deadline")
        self._sessions = session_factory
        self._revision = revision
        self._context = context
        self._engine = engine
        self._repository = repository or RunnerRepository()
        self._poll = poll_seconds
        self._monotonic = monotonic

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.LIVE

    def complete(self, request: ModelRequest) -> ModelResponse:
        settings = self._revision.settings
        assert settings.answer_deadline_seconds is not None
        window = answer_window(settings.answer_deadline_seconds, self._context)
        if window is None:
            raise _error("not_sent", _DEPENDENCY_DEADLINE,
                         "the attempt has too little time left to wait for a runner")
        payload = _task_payload(request)
        try:
            check_supported(payload["output_schema"])
        except SchemaNotSupported:
            raise _error("not_sent", "executor_request",
                         "the output schema uses a keyword runners cannot be held to",
                         code=ErrorCode.ANALYSIS_INPUT_INVALID) from None
        started = self._monotonic()
        task = self._write_task(payload, window)
        return self._await(task, started, window)

    # -- internals -------------------------------------------------------------------------

    def _write_task(self, payload: Mapping[str, Any], window: float) -> TaskRecord:
        context = self._context
        with self._sessions() as session:
            task = self._repository.insert_task(
                session, connection_id=self._revision.connection_id,
                revision_id=self._revision.revision_id, origin="run_call",
                run_id=getattr(context, "run_id", None),
                attempt_id=getattr(context, "attempt_id", None),
                model_call_id=getattr(context, "call_id", None), probe_id=None,
                expected_model=self._revision.settings.gateway_model, payload=payload,
                deadline_seconds=window,
            )
            session.commit()
        return task

    def _await(self, task: TaskRecord, started: float, window: float) -> ModelResponse:
        waiter = TaskWaiter(self._engine)
        stop = started + window
        try:
            while True:
                current = self._read(task.task_id)
                if current is not None and current.state == "answered":
                    return self._response(current, started)
                if current is not None and current.state == "failed":
                    raise _error("outcome_unknown", _DEPENDENCY_FAILED,
                                 "the runner reported that it could not answer; the outcome "
                                 "is unknown")
                if current is not None and current.state in ("expired", "cancelled"):
                    raise self._unanswered(current)
                remaining = stop - self._monotonic()
                if remaining <= 0:
                    return self._expire(task.task_id, started)
                waiter.wait(min(self._poll, remaining))
        except BaseException:
            self._withdraw(task.task_id)
            raise
        finally:
            waiter.close()

    def _read(self, task_id: str) -> TaskRecord | None:
        try:
            with self._sessions() as session:
                return self._repository.get_task(session, task_id)
        except SQLAlchemyError as failure:
            _log.warning("executor task %s unreadable (%s); retrying", task_id,
                         type(failure).__name__)
            return None

    def _expire(self, task_id: str, started: float) -> ModelResponse:
        """The deadline: end the task, then say what that means. A runner that answered in the
        last instant wins -- its answer is delivered."""
        with self._sessions() as session:
            expired = self._repository.expire_task(session, task_id)
            session.commit()
        if expired is not None:
            raise self._unanswered(expired)
        with self._sessions() as session:
            final = self._repository.get_task(session, task_id)
        assert final is not None
        if final.state == "answered":
            return self._response(final, started)
        raise self._unanswered(final)

    def _withdraw(self, task_id: str) -> None:
        """Nobody should take a task whose waiter has gone."""
        try:
            with self._sessions() as session:
                self._repository.cancel_task(session, task_id)
                session.commit()
        except Exception:  # noqa: BLE001 - the api's sweep cancels it with its Attempt
            _log.warning("executor task %s could not be withdrawn", task_id)

    @staticmethod
    def _unanswered(task: TaskRecord) -> ProxyDispatchError:
        if task.claim_count == 0:
            return _error("not_sent", _DEPENDENCY_NONE_ONLINE,
                          "no runner took the task before its deadline")
        return _error("outcome_unknown", _DEPENDENCY_DEADLINE,
                      "a runner took the task and did not answer it; the outcome is unknown")

    def _response(self, task: TaskRecord, started: float) -> ModelResponse:
        with self._sessions() as session:
            answer, declared = self._repository.answer_of(session, task.task_id)
        if answer is None or declared is None:
            raise _error("outcome_unknown", _DEPENDENCY_FAILED,
                         "the answer is no longer readable; the outcome is unknown")
        response = ModelResponse(
            output_text=answer, stop_reason="end_turn",
            input_tokens=task.declared_input_tokens or 0,
            output_tokens=task.declared_output_tokens or 0,
            latency_ms=int((self._monotonic() - started) * 1000),
            reported_cost_usd=None,
        )
        return _with_reported_model(response, declared)


def build_pull_adapter(
    *, session_factory: Callable[[], Session], revision: RevisionRecord, context: Any | None,
    engine: Engine | None = None,
) -> PullAdapter:
    """The adapter of one ``pull`` revision for one Attempt: what the resolver's kind table
    calls, as ``build_http_adapter`` is for ``http_api``. ``engine`` is the source of the
    ``LISTEN`` connection; without it the wait is a poll."""
    return PullAdapter(
        session_factory=session_factory, revision=revision, context=context, engine=engine)


def probe_pull(
    session_factory: Callable[[], Session], revision: RevisionRecord, probe_id: str, *,
    engine: Engine | None = None, repository: RunnerRepository | None = None,
    claim_seconds: float = PROBE_CLAIM_SECONDS, answer_seconds: float = PROBE_ANSWER_SECONDS,
    poll_seconds: float = _POLL_SECONDS, monotonic: Callable[[], float] = time.monotonic,
    nonce: str | None = None,
) -> ProbeResult:
    """«Проверить» for a ``pull`` revision: post a synthetic task a runner must take within
    ``claim_seconds`` and answer, declaring the revision's model, within ``answer_seconds``.

    ``no_runner_online`` when nobody took it; ``ok`` with the declared model when a runner
    answered; ``timeout`` when one took it and did not answer; ``protocol_error`` when one
    reported that it could not. Never raises for a wait: the outcome is the result. A wrong
    declared model is refused at the runner's submit (it keeps its claim and may correct it), so
    it surfaces here as the ``timeout`` of a probe nobody answered correctly."""
    import secrets

    store = repository or RunnerRepository()
    echo = nonce or secrets.token_hex(8)
    payload = {
        "system": _ECHO_SYSTEM, "user_text": echo,
        "output_schema": {
            "type": "object", "properties": {"echo": {"type": "string", "const": echo}},
            "required": ["echo"], "additionalProperties": False,
        },
    }
    started = monotonic()
    with session_factory() as session:
        task = store.insert_task(
            session, connection_id=revision.connection_id, revision_id=revision.revision_id,
            origin="probe", run_id=None, attempt_id=None, model_call_id=None, probe_id=probe_id,
            expected_model=revision.settings.gateway_model, payload=payload,
            deadline_seconds=claim_seconds + answer_seconds,
        )
        session.commit()
    waiter = TaskWaiter(engine)
    claim_stop = started + claim_seconds
    answer_stop = started + claim_seconds + answer_seconds
    try:
        while True:
            with session_factory() as session:
                current = store.get_task(session, task.task_id)
            assert current is not None
            now = monotonic()
            if current.state == "answered":
                return _probe_answered(revision, current, int((now - started) * 1000))
            if current.state == "failed":
                return ProbeResult(
                    "protocol_error", "the runner reported that it could not answer the probe",
                    latency_ms=int((now - started) * 1000))
            if current.state in ("expired", "cancelled"):
                return _probe_unanswered(current, int((now - started) * 1000))
            if current.claim_count == 0 and now >= claim_stop:
                break
            if now >= answer_stop:
                break
            stop = answer_stop if current.claim_count else claim_stop
            waiter.wait(min(poll_seconds, max(0.0, stop - now)))
        with session_factory() as session:
            expired = store.expire_task(session, task.task_id)
            session.commit()
        if expired is None:  # answered in the last instant
            with session_factory() as session:
                expired = store.get_task(session, task.task_id)
            assert expired is not None
            if expired.state == "answered":
                return _probe_answered(revision, expired, int((monotonic() - started) * 1000))
        return _probe_unanswered(expired, int((monotonic() - started) * 1000))
    except BaseException:
        try:
            with session_factory() as session:
                store.cancel_task(session, task.task_id)
                session.commit()
        except Exception:  # noqa: BLE001
            _log.warning("probe task %s could not be withdrawn", task.task_id)
        raise
    finally:
        waiter.close()


def _probe_unanswered(task: TaskRecord, latency_ms: int) -> ProbeResult:
    if task.claim_count == 0:
        return ProbeResult(
            "no_runner_online", "no runner took the probe task within 120 seconds",
            latency_ms=latency_ms)
    return ProbeResult(
        "timeout", "a runner took the probe task and did not answer it", latency_ms=latency_ms)


def _probe_answered(revision: RevisionRecord, task: TaskRecord, latency_ms: int) -> ProbeResult:
    declared = task.declared_model
    metered = revision.settings.billing == "metered"
    if declared != revision.settings.gateway_model:  # held at submit; a second, local check
        return ProbeResult(
            "model_mismatch", "the runner declared another model than the revision's",
            reported_model=declared, identity_basis="declared", latency_ms=latency_ms)
    return ProbeResult(
        "ok", None, reported_model=declared, identity_basis="declared", latency_ms=latency_ms,
        rate_check="not_reported" if metered else "not_metered")
