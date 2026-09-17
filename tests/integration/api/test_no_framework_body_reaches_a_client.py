"""The single highest-risk item of wave 13, asserted as a sweep.

``ALPHA_ROADMAP.md`` section 4: *every failure rendered by ``envelope_response`` and
nothing else. FastAPI's own ``RequestValidationError`` and ``HTTPException`` bodies must
never reach a client.* The reason it is the highest-risk item and not a cosmetic one:
**four certifications and the response baseline assert which rule refused**, not merely
that something did. FastAPI's own answer to a bad request is

    422 {"detail": [{"type": "string_too_short", "loc": ["body", "name"], ...}]}

which carries a status a reader would accept and no ``error_code``, no
``contract_version``, no ``correlation_id`` and no ``details.constraint``. A regression
here is a criterion-10 regression wearing a 422.

**Why a sweep rather than a case per refusal.** The suites beside this one assert the
*content* of each refusal -- ``test_multipart_rules``, ``test_header_rules``,
``test_schema_bounds``, ``test_error_envelope``. What none of them can say is that there is
no **other** way out. This file drives one request of every failing kind the framework has
an opinion about, including the ones no operation declares, and requires each answer to be
an ``ErrorEnvelope`` and nothing else. A thirteenth way of failing added later is covered
without anyone remembering to extend a list, because the property asserted is a property of
the *answer* and not of the case.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from auditmanager.shared.errors import ErrorCode
from w13_api_driver import Answer, Request, Surface, dispatch, probe_surface

#: Exactly the required properties of ``#/components/schemas/ErrorEnvelope``, written out.
ENVELOPE_REQUIRED = ("contract_version", "error_code", "message", "correlation_id", "retryable")

#: ``info.version`` of the frozen document, and the ``contract_version`` const.
CONTRACT_VERSION = "1.0.0-draft.1"

#: The keys FastAPI's own error bodies carry, and Starlette's. If any of these is the
#: *top level* of a response body, a framework body reached a client.
FRAMEWORK_KEYS = ("detail",)

_JSON = {"Content-Type": "application/json"}


def _identity(name: str) -> str:
    return {
        "project_uid": "prj_01M2545JSD15ETSNNV904X991F",
        "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
        "run_id": "run_01M2545JSD15ETSNNV904X991K",
        "finding_uid": "fnd_01M2545JSD15ETSNNV904X991M",
    }[name]


#: One request per kind of failure the framework would otherwise answer for itself. The
#: label says which framework behaviour is being displaced.
CASES: tuple[tuple[str, Request], ...] = (
    (
        "starlette's 404 for an undeclared path",
        Request.build("GET", "/there-is-no-such-operation"),
    ),
    (
        "starlette's 405 for an undeclared method on a declared path",
        Request.build("DELETE", "/projects"),
    ),
    (
        "fastapi's 422 for a missing required header",
        Request.build("POST", "/projects", headers=_JSON, body=b'{"name":"x"}'),
    ),
    (
        "fastapi's 422 for a header outside its pattern",
        Request.build(
            "POST",
            "/projects",
            headers={**_JSON, "Idempotency-Key": "not a key"},
            body=b'{"name":"x"}',
        ),
    ),
    (
        "fastapi's 422 for a malformed path identity",
        Request.build("GET", "/runs/run_NOT_A_REAL_IDENTITY"),
    ),
    (
        "fastapi's 422 for a body that is not JSON",
        Request.build(
            "POST",
            "/projects",
            headers={**_JSON, "Idempotency-Key": "nfb-notjson"},
            body=b"{not json",
        ),
    ),
    (
        "fastapi's 422 for a body that is not an object",
        Request.build(
            "POST",
            "/projects",
            headers={**_JSON, "Idempotency-Key": "nfb-array"},
            body=b"[1,2,3]",
        ),
    ),
    (
        "fastapi's 422 for a property outside a closed model",
        Request.build(
            "POST",
            "/projects",
            headers={**_JSON, "Idempotency-Key": "nfb-extra"},
            body=b'{"name":"x","surprise":1}',
        ),
    ),
    (
        "fastapi's 422 for a property that breaks a declared bound",
        Request.build(
            "POST",
            "/projects",
            headers={**_JSON, "Idempotency-Key": "nfb-length"},
            body=json.dumps({"name": "n" * 201}).encode("utf-8"),
        ),
    ),
    (
        "fastapi's 422 for a query parameter outside its enum",
        Request.build("GET", f"/runs/{_identity('run_id')}/findings?category=nonsense"),
    ),
    (
        "fastapi's 422 for a query parameter outside its bounds",
        Request.build("GET", "/projects?limit=0"),
    ),
    (
        "fastapi's 400 for a body its parser cannot read",
        Request.build(
            "POST",
            f"/projects/{_identity('project_uid')}/documents",
            headers={
                "Content-Type": "multipart/form-data; boundary=b",
                "Idempotency-Key": "nfb-unreadable",
            },
            body=b'--b\r\nContent-Disposition: form-data; filename="x.pdf"\r\n\r\nz\r\n--b--\r\n',
        ),
    ),
    (
        "fastapi's own 401 from HTTPBearer",
        Request.build("GET", "/projects"),
    ),
)


def _envelope(answer: Answer, label: str) -> dict[str, Any]:
    assert answer.header("Content-Type") == "application/json", (
        f"{label}: answered {answer.header('Content-Type')!r}, so it is not an envelope"
    )
    assert answer.header("X-Correlation-Id"), f"{label}: no correlation id"
    body = json.loads(answer.body)
    assert isinstance(body, dict), f"{label}: the body is not an object: {body!r}"
    for key in FRAMEWORK_KEYS:
        assert key not in body, (
            f"{label}: the answer carries {key!r} at its top level, which is the "
            f"framework's own body shape and not this contract's: {body!r}"
        )
    for key in ENVELOPE_REQUIRED:
        assert key in body, f"{label}: the envelope is missing {key!r}: {body!r}"
    assert body["contract_version"] == CONTRACT_VERSION, body
    assert body["error_code"] in {code.value for code in ErrorCode}, body
    assert body["correlation_id"] == answer.header("X-Correlation-Id"), body
    assert isinstance(body["retryable"], bool), body
    assert body["retryable"] is ErrorCode(body["error_code"]).retryable, (
        f"{label}: retryable disagrees with the catalog"
    )
    return body


@pytest.mark.parametrize(("label", "request_"), CASES, ids=[case[0] for case in CASES])
def test_the_framework_never_answers_for_itself(
    router: Surface, label: str, request_: Request
) -> None:
    """Every failing kind, answered as one ``ErrorEnvelope``."""
    credential = None if "401" in label else "w13-api-suite-token"
    answer = dispatch(router, request_, credential=credential)
    assert answer.status >= 400, f"{label}: answered {answer.status}"
    _envelope(answer, label)


def test_the_sweep_covers_every_status_the_framework_would_have_chosen(
    router: Surface,
) -> None:
    """Anti-vacuity: the cases above really do reach 400, 401, 404 and 422.

    Without this the sweep could shrink to one case and still be green, and the two
    statuses FastAPI is most likely to answer for itself -- its 422 and Starlette's 405 --
    are exactly the ones a reader would not notice missing.
    """
    # Three statuses, not four: FastAPI answers **400** for a body its parser cannot read
    # and this contract has no 400 -- the status is read from the catalog code, so that
    # case leaves as 422 `validation_failed`. Asserted as an equality rather than a subset
    # so a case that stopped being reached is a red test.
    statuses = set()
    for label, request_ in CASES:
        credential = None if "401" in label else "w13-api-suite-token"
        statuses.add(dispatch(router, request_, credential=credential).status)
    assert statuses == {401, 404, 422}, statuses
    assert 405 not in statuses, (
        "an undeclared method answered 405; this surface answers 404 so it is not an "
        "oracle for which paths exist"
    )
    assert 400 not in statuses, (
        "a body the parser could not read answered 400; FastAPI's own status for that is "
        "400 and this contract's is 422, because the status is read from the catalog code "
        "and never the other way round"
    )


def test_an_exception_no_handler_is_registered_for_still_leaves_as_an_envelope() -> None:
    """The last resort, which is the one a registration list cannot cover.

    Starlette's ``ExceptionMiddleware`` answers only the classes registered with it;
    anything else reaches ``ServerErrorMiddleware``, which sends *its own* body -- HTML in
    debug mode, ``"Internal Server Error"`` otherwise -- and re-raises.
    ``FailureEnvelopeMiddleware`` sits between them.
    """

    def handler() -> Answer:
        raise ZeroDivisionError("/var/lib/audit/secret.key")

    answer = dispatch(probe_surface(handler), Request.build("GET", "/probe"))
    assert answer.status == 500
    body = _envelope(answer, "an unregistered exception class")
    assert body["error_code"] == "internal_error"
    assert "secret.key" not in answer.body.decode("utf-8")
    assert "ZeroDivisionError" not in answer.body.decode("utf-8")


def test_the_sweep_can_fail(router: Surface) -> None:
    """The guard, run against a framework body, so it is not a test nobody has seen reject.

    The body below is verbatim what FastAPI answers for a validation error. If
    ``_envelope`` accepted it, every case above would pass against an application that had
    stopped mapping anything.
    """
    framework = Answer(
        status=422,
        headers=(
            ("Content-Type", "application/json"),
            ("X-Correlation-Id", "cid-00000000000000000000000000000000"),
        ),
        body=json.dumps(
            {"detail": [{"type": "string_too_short", "loc": ["body", "name"], "msg": "x"}]}
        ).encode("utf-8"),
    )
    with pytest.raises(AssertionError, match="framework's own body shape"):
        _envelope(framework, "a planted framework body")
