"""Envelope invariants: one failure shape, a pinned ``retryable``, a correlation id.

The property that matters most here is that ``retryable`` is **read from the catalog**
and cannot be set by a call site. It is not a parameter of
:func:`auditmanager.shared.errors.build` at all, so this suite checks the consequence:
for every code the surface can emit, the envelope's flag equals the catalog's, and it is
not a function of the HTTP status.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from auditmanager.api.routers import Router, dispatch
from auditmanager.api.routers.correlation import CORRELATION_HEADER
from auditmanager.api.routers.errors import envelope_response
from auditmanager.api.routers.http import Request, Response, Route
from auditmanager.api.routers.http import Router as RawRouter
from auditmanager.shared.errors import CONTRACT_VERSION, DomainError, ErrorCode

from .conftest import PublishedRun


def test_every_catalog_code_renders_a_valid_envelope(
    openapi_document: dict[str, Any], validate_against_schema
) -> None:
    """All twenty codes, each rendered and validated against the frozen envelope.

    Includes the codes PC-01 has no producer for. They are in the closed enum, and a
    surface that could not render one correctly would be a surface that breaks the day
    a producer appears.
    """
    cases = []
    for code in ErrorCode:
        response = envelope_response(DomainError(code), "cid-fixed-0001")
        body = json.loads(response.body)
        assert body["error_code"] == code.value
        assert body["retryable"] is code.retryable, (
            f"{code.value}: envelope says {body['retryable']}, catalog says {code.retryable}"
        )
        assert response.status == code.http_status
        assert body["contract_version"] == CONTRACT_VERSION
        cases.append({"name": code.value, "schema": "ErrorEnvelope", "payload": body})

    results = validate_against_schema(openapi_document, cases)
    for code in ErrorCode:
        result = results[code.value]
        assert result["valid"], f"{code.value} envelope invalid: {result['messages']}"


def test_retryable_is_not_a_function_of_the_http_status() -> None:
    """Two codes share a status and disagree on retryability.

    This is the assertion that would fail if anything ever inferred the flag from the
    status line. ``idempotency_key_in_progress`` and ``idempotency_key_stale`` are both
    409; the first is retryable and the second is not.
    """
    in_progress = ErrorCode.IDEMPOTENCY_KEY_IN_PROGRESS
    stale = ErrorCode.IDEMPOTENCY_KEY_STALE
    assert in_progress.http_status == stale.http_status == 409
    assert in_progress.retryable is True
    assert stale.retryable is False

    assert json.loads(envelope_response(DomainError(in_progress), "c").body)["retryable"]
    assert not json.loads(envelope_response(DomainError(stale), "c").body)["retryable"]


def test_the_contract_version_matches_the_frozen_document(
    openapi_document: dict[str, Any]
) -> None:
    """``ErrorEnvelope.contract_version`` is a ``const`` in the document."""
    declared = openapi_document["components"]["schemas"]["ErrorEnvelope"]["properties"][
        "contract_version"
    ]["const"]
    assert declared == CONTRACT_VERSION
    assert declared == openapi_document["info"]["version"]


def test_every_response_carries_a_correlation_id(
    router: Router, published_run: PublishedRun
) -> None:
    """Success and failure alike. Section 7 says *every* response."""
    requests = (
        Request.build("GET", "/projects"),
        Request.build("GET", f"/runs/{published_run.run_id}"),
        Request.build("GET", "/versions/ver_01M2545JSD15ETSNNV904X991J"),
        Request.build("GET", "/nothing-here"),
        Request.build("POST", "/projects", body=b"{}"),
    )
    for request in requests:
        response = dispatch(router, request)
        assert response.header(CORRELATION_HEADER), (
            f"{request.method} {request.path} carried no {CORRELATION_HEADER}"
        )


def test_a_supplied_correlation_id_is_echoed(router: Router) -> None:
    supplied = "trace-0123456789"
    response = dispatch(
        router,
        Request.build("GET", "/projects", headers={CORRELATION_HEADER: supplied}),
    )
    assert response.header(CORRELATION_HEADER) == supplied


def test_an_unusable_correlation_id_is_replaced_not_reflected(router: Router) -> None:
    """A value outside the frozen pattern is replaced rather than echoed.

    Echoing it would put caller-controlled text into a response header, and into the
    ``correlation_id`` field of every error envelope, where it is not screened.
    """
    hostile = "../../etc/passwd\r\nX-Injected: 1"
    response = dispatch(
        router,
        Request.build("GET", "/projects", headers={CORRELATION_HEADER: hostile}),
    )
    assigned = response.header(CORRELATION_HEADER)
    assert assigned != hostile
    assert "\r" not in assigned and "\n" not in assigned
    assert "/" not in assigned


def test_the_correlation_id_in_the_body_matches_the_header(router: Router) -> None:
    response = dispatch(router, Request.build("GET", "/nothing-here"))
    assert response.status == 404
    assert json.loads(response.body)["correlation_id"] == response.header(
        CORRELATION_HEADER
    )


def test_an_unknown_identity_is_not_found_and_reveals_nothing(
    router: Router, published_run: PublishedRun
) -> None:
    """A malformed identity and a well-formed absent one are indistinguishable.

    If they differed, the surface would be an oracle for which identifier shapes are
    real. Both bodies must be byte-identical once the correlation id is removed.
    """
    absent = dispatch(
        router, Request.build("GET", "/findings/fnd_01M2545JSD15ETSNNV904X991M")
    )
    malformed = dispatch(router, Request.build("GET", "/findings/not-an-identity"))
    wrong_prefix = dispatch(
        router, Request.build("GET", "/findings/run_01M2545JSD15ETSNNV904X991K")
    )

    bodies = []
    for response in (absent, malformed, wrong_prefix):
        assert response.status == 404, response.body
        body = json.loads(response.body)
        body.pop("correlation_id")
        bodies.append(body)
    assert bodies[0] == bodies[1] == bodies[2]


def test_a_domain_error_detail_outside_the_catalog_is_refused_not_dropped() -> None:
    """The envelope's own guard, exercised from this edge.

    A detail key the catalog does not declare safe raises rather than being silently
    dropped -- so a call site here learns at once instead of shipping a redaction that
    did nothing. This is the guard working, not a bug.
    """
    from auditmanager.shared.errors import UnsafeDetailKey

    with pytest.raises(UnsafeDetailKey):
        DomainError(ErrorCode.NOT_FOUND, bucket="audit-b6").envelope("cid-1")

    # And a declared key is accepted.
    envelope = DomainError(ErrorCode.NOT_FOUND, aggregate_type="Finding").envelope("cid-1")
    assert envelope.details == {"aggregate_type": "Finding"}


def test_a_message_carrying_an_address_is_refused_by_the_screen() -> None:
    """The envelope's message screen, exercised from this edge."""
    from auditmanager.shared.errors import UnsafeMessage

    for unsafe in (
        "could not read /var/lib/audit/objects/ab/cd.pdf",
        "GET https://minio.internal/audit-b6 failed",
        "SELECT blob_id FROM blob WHERE state = 'available'",
    ):
        with pytest.raises(UnsafeMessage):
            DomainError(ErrorCode.INTERNAL_ERROR, message=unsafe).envelope("cid-1")


def test_an_unclassified_fault_becomes_internal_error_carrying_nothing(
    router: Router,
) -> None:
    """A handler that raises anything at all answers 500 with no trace of the original."""

    def handler(_: Request) -> Response:
        raise RuntimeError("/var/lib/audit/secret.key could not be read")

    raw = RawRouter([Route("probe", "GET", "/probe", handler)])
    response = dispatch(raw, Request.build("GET", "/probe"))

    assert response.status == 500
    body = json.loads(response.body)
    assert body["error_code"] == "internal_error"
    assert body["retryable"] is False
    assert "secret.key" not in response.body.decode("utf-8")
    assert "RuntimeError" not in response.body.decode("utf-8")


def test_the_error_response_is_json_whatever_the_operation_produced(
    router: Router, published_run: PublishedRun
) -> None:
    """A failure on a ``text/csv`` operation is still the JSON envelope."""
    response = dispatch(
        router, Request.build("GET", f"/runs/{published_run.run_id}/export.csv")
    )
    assert response.status == 409, response.body
    assert response.header("Content-Type") == "application/json"
    assert json.loads(response.body)["error_code"] == "state_transition_not_allowed"
