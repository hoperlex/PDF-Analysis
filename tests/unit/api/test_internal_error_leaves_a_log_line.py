"""`HARDEN-01` / `F-13` (`EXPOSURE-REVIEW-02`, `D-240`): a failure that the API answers as
``internal_error`` leaves one log line -- the exception's type, where it was raised and the
correlation id -- and never its message.

The finding: ``FailureEnvelopeMiddleware`` answers ``internal_error`` and "declines to re-raise",
``to_domain_error`` keeps "nothing from the original", and no logger was called anywhere in the
API's request path, so the correlation id in the envelope addressed no record at all: a 500
storm, or an exploit attempt, was invisible to the operator.

**What the line may carry.** The type (a class name is code), the module and line of the frame that
raised (code), and the correlation id (opaque, caller-chosen only within a frozen pattern). **What
it may not carry**, and what these tests plant a sentinel in to prove it: the exception's message
(a driver's message can hold a row value; a ``DomainError`` message can hold ``reason`` text), its
arguments, its cause, the traceback text (which ends with the message), headers and bodies. So
the record is built with no ``exc_info``, and the tests read every attribute of the record.

**Which failures.** Those the envelope reports as ``internal_error`` -- an exception nobody mapped
(the middleware's path) and a ``DomainError`` that already carries that code (the registered
handler's path; several call sites raise it with a ``reason``). A typed refusal that is the
caller's doing -- ``not_found`` and the rest -- is not an incident and leaves no line.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from auditmanager.api.routers import (
    CorrelationMiddleware,
    FailureEnvelopeMiddleware,
    install_exception_handlers,
)
from auditmanager.shared.errors import DomainError, ErrorCode

LOGGER = "auditmanager.api.routers.handlers"

#: Planted in every message, argument and cause below; it must reach neither a record nor a client.
SENTINEL = "row-value-3c81e0aa-must-not-be-logged"


class _Unmapped(Exception):
    """A class of the application's own: the line names it by module and qualified name."""


def _boom() -> None:
    raise _Unmapped(f"{SENTINEL} in the message", SENTINEL)


def _chained() -> None:
    try:
        raise ValueError(SENTINEL)
    except ValueError as cause:
        raise RuntimeError(f"wrapped {SENTINEL}") from cause


def _app() -> FastAPI:
    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        _boom()

    @app.get("/chained")
    def chained() -> None:
        _chained()

    @app.get("/typed")
    def typed() -> None:
        raise DomainError(ErrorCode.NOT_FOUND, message=f"nothing here {SENTINEL}")

    @app.get("/internal")
    def internal() -> None:
        raise DomainError(ErrorCode.INTERNAL_ERROR, message=f"inconsistent: {SENTINEL}")

    # Outermost first, as `build_application` does: correlation, then the failure envelope.
    app.add_middleware(FailureEnvelopeMiddleware)
    app.add_middleware(CorrelationMiddleware)
    return app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(_app(), raise_server_exceptions=False)


def _records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name == LOGGER]


def _every_text_of(record: logging.LogRecord) -> str:
    """All the text a handler could write for this record, whichever formatter it has."""
    return " | ".join(
        [
            record.getMessage(),
            repr(record.args),
            repr(record.msg),
            str(record.exc_text),
            str(record.stack_info),
            repr(record.exc_info),
            repr(sorted(vars(record).items(), key=lambda item: item[0])),
        ]
    )


def test_an_unmapped_exception_is_answered_as_internal_error_and_logged_once(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        answer = client.get("/boom", headers={"X-Correlation-Id": "cid-harden-01-a"})

    assert answer.status_code == 500
    assert answer.json()["error_code"] == "internal_error"
    assert answer.headers["X-Correlation-Id"] == "cid-harden-01-a"
    (record,) = _records(caplog)
    assert record.levelno == logging.ERROR
    line = record.getMessage()
    assert f"{_Unmapped.__module__}.{_Unmapped.__qualname__}" in line, line
    assert "cid-harden-01-a" in line, line
    # where it was raised: module, line and function of the innermost frame (code, never data)
    assert re.search(r"raised at \S+:\d+ in _boom\b", line), line


def test_the_line_carries_the_generated_id_the_client_is_given(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """No id supplied: the edge makes one, and the envelope, the header and the log all say the same."""
    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        answer = client.get("/boom")

    generated = answer.headers["X-Correlation-Id"]
    assert answer.json()["correlation_id"] == generated
    (record,) = _records(caplog)
    assert generated in record.getMessage()


@pytest.mark.parametrize("path", ["/boom", "/chained", "/internal"])
def test_nothing_of_the_message_the_cause_or_the_traceback_reaches_the_record(
    path: str, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        answer = client.get(path)

    assert answer.status_code == 500
    records = _records(caplog)
    assert len(records) == 1, [record.getMessage() for record in records]
    (record,) = records
    assert record.exc_info is None and record.exc_text is None and record.stack_info is None
    assert SENTINEL not in _every_text_of(record)
    assert "Traceback" not in _every_text_of(record)


def test_the_chained_failure_is_named_by_the_exception_that_escaped_not_by_its_cause(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        client.get("/chained")
    (record,) = _records(caplog)
    assert "RuntimeError" in record.getMessage()
    assert "ValueError" not in record.getMessage()


def test_a_domain_error_that_is_itself_internal_error_is_logged_by_type(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        answer = client.get("/internal", headers={"X-Correlation-Id": "cid-harden-01-b"})

    assert answer.status_code == 500
    (record,) = _records(caplog)
    assert "DomainError" in record.getMessage()
    assert "cid-harden-01-b" in record.getMessage()


def test_a_typed_refusal_that_is_the_callers_doing_leaves_no_line(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        answer = client.get("/typed")

    assert answer.status_code == 404
    assert _records(caplog) == []


def test_the_client_still_gets_the_envelope_and_none_of_the_original(client: TestClient) -> None:
    """Logging added nothing to the answer: the frozen envelope is what it was."""
    answer = client.get("/boom")
    body: dict[str, Any] = answer.json()
    assert SENTINEL not in answer.text
    assert body["error_code"] == "internal_error"
    assert set(body) >= {"contract_version", "error_code", "message", "correlation_id", "retryable"}


def test_a_direct_call_of_the_unhandled_handler_logs_too(caplog: pytest.LogCaptureFixture) -> None:
    """`on_unhandled` is exported; a registration of it must not be a way back to a silent 500."""
    from auditmanager.api.routers.handlers import on_unhandled

    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        try:
            _boom()
        except _Unmapped as exc:
            answer = on_unhandled(None, exc)  # type: ignore[arg-type]

    assert answer.status_code == 500
    (record,) = _records(caplog)
    assert "_Unmapped" in record.getMessage()
    assert SENTINEL not in _every_text_of(record)
