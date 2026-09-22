"""`T-6` -- the authorization seam, and the three ways past it that must not exist.

`W13-SEAL` added the contract half at `a5f4001`: one ``http``/``bearer`` scheme at the
document's root, ``security: [{"bearerAuth": []}]`` over all twelve operations, and ``401``
and ``403`` on every one of them. This is the implementation half, and the trap
`W13-SEAL` section 8.1 names by name is what most of this file is about:

    ``auto_error`` is the thing to watch: FastAPI's default raises its own
    ``HTTPException``, and a bare 403 or a ``{"detail": ...}`` body would violate the
    one-failure-shape rule this document has held since CP-00. **401 is
    ``authentication_required`` in an ``ErrorEnvelope`` with ``X-Correlation-Id``, and
    nothing else is acceptable.**

Three more properties are asserted here because each is a way the seam could be *present*
and useless:

* **it is in front of all twelve**, not eleven. A dependency declared per operation is
  eleven chances to forget one, which is why it is declared once on the router -- and why
  this sweeps the twelve rather than naming one.
* **an unconfigured application refuses**, rather than opening. "No token configured, so
  let everyone in" is a switch that turns the seam off by omission, which is the failure a
  deployment discovers rather than a test.
* **the refusal does not depend on the request being otherwise valid.** A request that is
  *both* unauthenticated and malformed answers ``401``, not ``422``: telling an anonymous
  caller which of their fields is wrong is a small oracle, and one they have not earned.
"""

from __future__ import annotations

import base64
import json
import time

import pytest

from auditmanager.api.app import create_asgi_app
from auditmanager.api.security import (
    API_TOKEN_VARIABLE,
    SCHEME_NAME,
    UNAUTHENTICATED_OPERATIONS,
    Subject,
    build_signer,
)
from w13_api_driver import (
    DEPLOYMENT_SECRET,
    SUITE_LOGIN,
    SUITE_PASSWORD,
    TEST_SUBJECT,
    TEST_TOKEN,
    Request,
    Surface,
    dispatch,
)

#: The guarded operations, written out: one request each, shaped so that *authorization*
#: is the only thing that can refuse it before anything else does. Every operation of the
#: surface except the credential exchange, which is the register's one entry and is swept
#: separately below.
GUARDED = (
    ("createProject", "POST", "/projects"),
    ("listProjects", "GET", "/projects"),
    ("uploadDocument", "POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents"),
    ("getDocumentVersion", "GET", "/versions/ver_01M2545JSD15ETSNNV904X991J"),
    (
        "streamDocumentVersionContent",
        "GET",
        "/versions/ver_01M2545JSD15ETSNNV904X991J/content",
    ),
    ("startRun", "POST", "/runs"),
    ("getRunStatus", "GET", "/runs/run_01M2545JSD15ETSNNV904X991K"),
    ("listRunFindings", "GET", "/runs/run_01M2545JSD15ETSNNV904X991K/findings"),
    ("getFinding", "GET", "/findings/fnd_01M2545JSD15ETSNNV904X991M"),
    ("appendDecision", "POST", "/findings/fnd_01M2545JSD15ETSNNV904X991M/decisions"),
    ("listDecisionHistory", "GET", "/findings/fnd_01M2545JSD15ETSNNV904X991M/decisions"),
    ("exportRunCsv", "GET", "/runs/run_01M2545JSD15ETSNNV904X991K/export.csv"),
    # `R-5`. The three list operations are behind the same seam as the twelve. The
    # top-level `security` declaration is not what enforces it -- the `T-6` dependency is
    # -- so a new operation is not covered by having been added to the document, and this
    # tuple is what says so about each one individually.
    (
        "listDocuments",
        "GET",
        "/projects/prj_01M2545JSD15ETSNNV904X991F/documents",
    ),
    (
        "listVersions",
        "GET",
        "/documents/doc_01M2545JSD15ETSNNV904X991H/versions",
    ),
    ("listRuns", "GET", "/versions/ver_01M2545JSD15ETSNNV904X991J/runs"),
    # `R-24`, `W38-KB`. The decision journal is the first listing with no parent in its
    # path, so it is the first one whose 401 cannot be mistaken for the 404 an unknown
    # parent would produce. That makes the row below the only thing asserting it.
    ("listDecisions", "GET", "/decisions"),
)

#: The catalog's own summary for the code, as a literal. `W13-SEAL` section 8.1 requires
#: this exact answer and not merely a 401.
AUTHENTICATION_REQUIRED = "authentication_required"

#: The exchange, which the register opens. Written out here as its own row rather than
#: added to :data:`GUARDED`, because what is asserted about it is the opposite thing.
EXCHANGE = ("issueToken", "POST", "/auth/token")


def _another_deployments_credential() -> str:
    """A well-formed credential, minted with a key this deployment does not hold."""
    signer = build_signer({API_TOKEN_VARIABLE: "some-other-deployments-secret"})
    assert signer is not None
    return signer.issue(TEST_SUBJECT).token


def _an_expired_credential() -> str:
    """One this deployment really minted, an hour and a second ago."""
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    issued = signer.issue(TEST_SUBJECT, now=time.time() - 3601)
    assert signer.verify(issued.token) is None, (
        "this case is only a case if the credential really has expired"
    )
    return issued.token


def _a_tampered_credential() -> str:
    """This deployment's own credential, with another subject written into the payload.

    The tag is left exactly as it was, which is what a caller who can read their own
    credential and wants to be somebody else would produce. Built by re-encoding the
    payload rather than by flipping bytes, so the result is a *valid-looking* credential
    and the only thing wrong with it is that this deployment did not sign it.
    """
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    version, body, tag = signer.issue(TEST_SUBJECT).token.split(".")
    payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    assert payload["sub"] == TEST_SUBJECT.user_uid, payload
    payload["sub"] = "usr_01M2545JSD15ETSNNV904X991Z"
    edited = (
        base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        .decode("ascii")
        .rstrip("=")
    )
    assert edited != body
    return f"{version}.{edited}.{tag}"


def _envelope(answer) -> dict:
    assert answer.header("Content-Type") == "application/json", answer.headers
    assert answer.header("X-Correlation-Id"), answer.headers
    body = json.loads(answer.body)
    assert "detail" not in body, (
        f"FastAPI's own body reached the client: {body!r}. This is the `auto_error` trap."
    )
    return body


def test_every_operation_but_the_register_is_behind_the_seam(router: Surface) -> None:
    """One request per guarded operation, with no credential. Sixteen, not fifteen.

    The set comparison is what makes this a sweep rather than a list: a seventeenth
    operation is either written into ``GUARDED`` and swept, or named in
    :data:`~auditmanager.api.security.UNAUTHENTICATED_OPERATIONS` and reported by
    ``test_the_open_surface_is_exactly_the_register`` -- there is no third place for it to
    be, and an operation that is in neither fails here.
    """
    assert len(GUARDED) == 16
    assert UNAUTHENTICATED_OPERATIONS == {"issueToken"}
    assert {operation for operation, _, _ in GUARDED} | UNAUTHENTICATED_OPERATIONS == (
        router.operation_ids
    )
    open_surface = []
    for operation, method, path in GUARDED:
        answer = dispatch(router, Request.build(method, path), credential=None)
        if answer.status != 401:
            open_surface.append((operation, answer.status))
            continue
        body = _envelope(answer)
        assert body["error_code"] == AUTHENTICATION_REQUIRED, (operation, body)
        assert body["retryable"] is False, (operation, body)
    assert open_surface == [], (
        f"these operations answered something other than 401 with no credential: "
        f"{open_surface}"
    )


@pytest.mark.parametrize(
    ("label", "credential"),
    [
        ("no credential at all", None),
        ("a credential the deployment does not accept", "not-a-credential-at-all"),
        ("an empty bearer", ""),
        ("this deployment's credential with one character removed", TEST_TOKEN[:-1]),
        ("this deployment's credential with one character added", TEST_TOKEN + "x"),
        # `W34-API`. The alpha accepted the configured string itself. It is now the secret
        # the signing key is derived from and **not** a credential, and an upgraded
        # deployment that kept its value has therefore stopped honouring the token every
        # operator and every runbook already knows.
        ("the deployment secret itself", DEPLOYMENT_SECRET),
        # A credential this deployment did not sign. Same format, same shape, another key:
        # what a second deployment's token, or a forgery, looks like from here.
        (
            "a credential minted with another deployment's key",
            _another_deployments_credential(),
        ),
        # A credential this deployment signed, and would sign again, an hour and a second
        # ago. The tag verifies; the expiry does not.
        ("an expired credential this deployment minted", _an_expired_credential()),
        # The payload rewritten to name another subject, with the tag left as it was.
        ("a credential whose payload was edited", _a_tampered_credential()),
    ],
    ids=[
        "absent",
        "wrong",
        "empty",
        "one-short",
        "one-long",
        "the-deployment-secret",
        "another-key",
        "expired",
        "tampered",
    ],
)
def test_a_credential_the_deployment_does_not_accept_is_refused(
    router: Surface, label: str, credential: str | None
) -> None:
    """Including the two neighbours of the real credential, and the four `W34-API` added.

    A comparison that passed for a prefix or for a longer string would be a comparison
    that is not a comparison. ``hmac.compare_digest`` is what makes the timing of these
    indistinguishable as well, which no test can assert and which is why the
    implementation says so out loud.

    Every one of the nine answers the *same* refusal: one status, one code, one envelope.
    A caller cannot tell "expired" from "forged" from "never issued", which is the point --
    each of those is a different sentence about the deployment's internals.
    """
    answer = dispatch(router, Request.build("GET", "/projects"), credential=credential)
    assert answer.status == 401, (label, answer.status, answer.body)
    assert _envelope(answer)["error_code"] == AUTHENTICATION_REQUIRED


def test_the_configured_credential_is_accepted(router: Surface) -> None:
    """The anti-vacuity of every case above: the seam is not refusing everything."""
    answer = dispatch(router, Request.build("GET", "/projects"))
    assert answer.status == 200, answer.body


def test_an_unauthenticated_and_malformed_request_answers_401_and_not_422(
    router: Surface,
) -> None:
    """Authorization first. A caller who has not authenticated learns nothing else.

    The same request *with* the credential is a 422 that names the rule, which is what
    makes this an ordering assertion rather than a claim that the body is fine.
    """
    malformed = Request.build(
        "POST",
        "/projects",
        headers={"Content-Type": "application/json"},
        body=b'{"name":"ok","surprise":1}',
    )
    anonymous = dispatch(router, malformed, credential=None)
    assert anonymous.status == 401, anonymous.body
    assert _envelope(anonymous)["error_code"] == AUTHENTICATION_REQUIRED

    authenticated = dispatch(
        router,
        Request.build(
            "POST",
            "/projects",
            headers={"Content-Type": "application/json", "Idempotency-Key": "auth-422"},
            body=b'{"name":"ok","surprise":1}',
        ),
    )
    assert authenticated.status == 422, authenticated.body
    assert json.loads(authenticated.body)["details"]["constraint"] == "additionalProperties"


def test_an_application_with_no_configured_token_refuses_everything(
    router: Surface,
) -> None:
    """Unconfigured means refused, not open.

    Built through ``create_asgi_app`` with an environment that names no token, over the
    same router this suite already wired -- so the only difference between this
    application and the one every other test drives is the absence of the credential.
    """
    from starlette.testclient import TestClient

    class _Built:
        # `D-20`: `create_asgi_app` publishes the built application's carrier as
        # `app.state.run_carrier`. This application exists to be refused at the
        # credential and starts nothing, so an inline carrier is the honest stand-in
        # rather than a `None` that would fail three frames from the cause.
        def __init__(self, table: object) -> None:
            from auditmanager.runs import InlineCarrier

            self.router = table
            self.carrier = InlineCarrier()

    unconfigured = create_asgi_app(environ={}, application=_Built(router.router))
    client = TestClient(unconfigured, raise_server_exceptions=False)

    for presented in (None, "", TEST_TOKEN, "anything at all"):
        headers = {} if presented is None else {"Authorization": f"Bearer {presented}"}
        response = client.get("/projects", headers=headers)
        assert response.status_code == 401, (presented, response.status_code)
        assert json.loads(response.content)["error_code"] == AUTHENTICATION_REQUIRED


def test_the_served_document_declares_the_scheme_the_contract_declares(
    router: Surface,
) -> None:
    """The document half, asserted against the frozen contract's own spelling.

    `W13-SEAL` chose ``http``/``bearer`` with **no** ``bearerFormat`` deliberately: an
    opaque deployment token and an OIDC-issued JWT are both bearer credentials, and naming
    the format would pin the document to whichever one is current. ``HTTPBearer`` will not
    emit it unless asked, and this is the assertion that keeps it unasked.
    """
    document = router.app.openapi()
    schemes = document["components"]["securitySchemes"]
    assert set(schemes) == {SCHEME_NAME}
    scheme = schemes[SCHEME_NAME]
    assert scheme["type"] == "http"
    assert scheme["scheme"] == "bearer"
    assert "bearerFormat" not in scheme, scheme
    opened = []
    for path_item in document["paths"].values():
        for method, operation in path_item.items():
            if method not in ("get", "post"):
                continue
            if operation["security"] == [{SCHEME_NAME: []}]:
                continue
            opened.append(operation["operationId"])
            # The empty requirement, and only that. An operation that merely *omitted*
            # `security` would inherit the document root -- which this document does not
            # declare -- and would be a third state neither the contract nor the seam has
            # a meaning for.
            assert operation["security"] == [], (
                method,
                operation["operationId"],
                operation.get("security"),
            )
    assert set(opened) == UNAUTHENTICATED_OPERATIONS, (
        "the document opens a different set of operations from the one the seam opens: "
        f"document {sorted(opened)}, seam {sorted(UNAUTHENTICATED_OPERATIONS)}"
    )


def test_the_environment_variable_is_the_one_the_deployment_will_set() -> None:
    """A literal, because a deployment sets a string and not a symbol."""
    assert API_TOKEN_VARIABLE == "AUDITMANAGER_API_TOKEN"


# =======================================================================================
# `W34-API` -- the body behind the seam: a credential is issued, and only that is accepted
# =======================================================================================


def test_the_open_surface_is_exactly_the_register(router: Surface) -> None:
    """Sweep every operation with no credential; the ones that answer are the register.

    The sweep is the assertion, not the list: this is what reports a second operation
    that opened itself, whoever opened it and whichever module it lives in. It is the
    runtime twin of the document sweep above, and the two are deliberately written
    against different sources -- one reads the served document, one sends requests.
    """
    samples = {
        operation: (method, path) for operation, method, path in (*GUARDED, EXCHANGE)
    }
    assert set(samples) == router.operation_ids

    answered = set()
    for operation, (method, path) in samples.items():
        body = b'{"login":"nobody","password":"nothing"}' if operation == "issueToken" else b""
        headers = {"Content-Type": "application/json"} if body else {}
        answer = dispatch(
            router,
            Request.build(method, path, headers=headers, body=body),
            credential=None,
        )
        if answer.status != 401 or _envelope(answer)["error_code"] != AUTHENTICATION_REQUIRED:
            answered.add(operation)
    # ``issueToken`` above is deliberately sent a pair the suite's port refuses, so that a
    # 401 from *the exchange's own rule* would put it in this set and be reported. It is
    # not here because the exchange refused it with the same code -- see the next test,
    # which is where "the exchange answers at all" is asserted.
    assert answered == set(), (
        f"these operations did not answer authentication_required without a credential: "
        f"{sorted(answered)}"
    )


def test_the_exchange_answers_without_a_credential(router: Surface) -> None:
    """The register's one entry, doing the thing the register exists for.

    The anti-vacuity of the sweep above: if the exchange were behind the seam too, this
    would be a 401 and there would be no way to obtain a credential at all.
    """
    answer = dispatch(
        router,
        Request.build(
            "POST",
            "/auth/token",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"login": SUITE_LOGIN, "password": SUITE_PASSWORD}).encode(),
        ),
        credential=None,
    )
    assert answer.status == 200, answer.body
    body = json.loads(answer.body)
    assert sorted(body) == ["expires_in", "token"], body
    assert isinstance(body["token"], str) and body["token"]
    assert body["expires_in"] == 3600, body
    assert answer.header("X-Correlation-Id"), answer.headers


def test_a_credential_from_the_exchange_opens_the_guarded_surface(router: Surface) -> None:
    """End to end through the seam: exchange a pair, present what comes back.

    This is the whole point of the wave in four lines. The credential is not written down
    anywhere in this test: it is the one the application just minted, and the operation it
    opens is one the same application guards.
    """
    exchanged = dispatch(
        router,
        Request.build(
            "POST",
            "/auth/token",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"login": SUITE_LOGIN, "password": SUITE_PASSWORD}).encode(),
        ),
        credential=None,
    )
    assert exchanged.status == 200, exchanged.body
    minted = json.loads(exchanged.body)["token"]

    answer = dispatch(router, Request.build("GET", "/projects"), credential=minted)
    assert answer.status == 200, answer.body


@pytest.mark.parametrize(
    ("label", "payload"),
    [
        ("a login this deployment has never heard of", {"login": "nobody", "password": "x"}),
        ("the right login and the wrong password", {"login": SUITE_LOGIN, "password": "x"}),
    ],
    ids=["unknown-login", "wrong-password"],
)
def test_a_refused_pair_is_the_same_refusal_a_missing_credential_gets(
    router: Surface, label: str, payload: dict
) -> None:
    """401 ``authentication_required``, in an ``ErrorEnvelope``, for both.

    Two facts in one assertion. **It is a 401 and not a 403**: ``permission_denied`` is an
    authenticated subject being refused, and this is the operation that produces one.
    **The two cases are indistinguishable**: an answer that told them apart would let
    anyone with this form enumerate which accounts exist.
    """
    answer = dispatch(
        router,
        Request.build(
            "POST",
            "/auth/token",
            headers={"Content-Type": "application/json"},
            body=json.dumps(payload).encode(),
        ),
        credential=None,
    )
    assert answer.status == 401, (label, answer.status, answer.body)
    envelope = _envelope(answer)
    assert envelope["error_code"] == AUTHENTICATION_REQUIRED, envelope
    assert envelope["retryable"] is False, envelope
    assert "login" not in json.dumps(envelope.get("details")), envelope


def test_the_exchange_never_answers_with_what_it_was_given(router: Surface) -> None:
    """No password reaches a response body, on either outcome.

    The refusal carries the catalog summary and nothing of the request; the success
    carries a credential the deployment minted. Asserted on a password distinctive enough
    that a substring search means something.
    """
    secret = "correct-horse-battery-staple-9182"
    for payload in (
        {"login": SUITE_LOGIN, "password": secret},
        {"login": SUITE_LOGIN, "password": SUITE_PASSWORD},
    ):
        answer = dispatch(
            router,
            Request.build(
                "POST",
                "/auth/token",
                headers={"Content-Type": "application/json"},
                body=json.dumps(payload).encode(),
            ),
            credential=None,
        )
        assert secret.encode() not in answer.body, answer.body
        assert SUITE_PASSWORD.encode() not in answer.body, answer.body


def test_a_malformed_exchange_body_is_refused_as_a_rule_and_not_as_a_credential(
    router: Surface,
) -> None:
    """422 ``validation_failed``, because the request never reached a credential check.

    The distinction matters: 401 here would say "the deployment does not accept this
    pair" about a request that carried no pair at all.
    """
    answer = dispatch(
        router,
        Request.build(
            "POST",
            "/auth/token",
            headers={"Content-Type": "application/json"},
            body=b'{"login":"api-suite"}',
        ),
        credential=None,
    )
    assert answer.status == 422, answer.body
    assert _envelope(answer)["error_code"] == "validation_failed", answer.body


def test_the_exchange_declares_the_empty_requirement(router: Surface) -> None:
    """``security: []`` in the served document, in memory and in the bytes.

    Both halves, because they are produced by different machinery: ``app.openapi()``
    builds the object, and the ``/openapi.json`` route serialises it. The frozen contract
    declares ``[]``, an *absent* key would mean "inherit the root", and this surface's
    document declares no root requirement -- so absent and empty are not the same answer
    and only one of them is the contract's.
    """
    from starlette.testclient import TestClient

    document = router.app.openapi()
    assert document["paths"]["/auth/token"]["post"]["security"] == []

    served = TestClient(router.app, raise_server_exceptions=False).get("/openapi.json")
    assert served.status_code == 200
    assert b'"security":[]' in served.content.replace(b", ", b",").replace(b": ", b":")


def test_a_subject_is_published_for_the_next_session_and_read_by_nobody_now(
    router: Surface,
) -> None:
    """The seam decides *who*; it does not decide *what they may do*.

    ``request.state.subject`` carries the verified subject, so the day roles exist there
    is something to attach them to. That it is currently read by nothing is the `T-6`
    boundary this session was told not to cross, and this asserts the boundary from both
    sides: the value is there, and no router module reads it.
    """
    import pathlib

    routers = pathlib.Path("src/auditmanager/api/routers")
    readers = [
        path.name
        for path in routers.rglob("*.py")
        if "state.subject" in path.read_text(encoding="utf-8")
    ]
    assert readers == [], (
        f"{readers} read the subject off the request. Deciding what a subject may do is "
        "the next session's work (roles), and doing it here would make this seam an "
        "authorization model nobody specified."
    )

    seen: list = []
    from starlette.testclient import TestClient

    app = router.app

    @app.middleware("http")
    async def _capture(request, call_next):  # pragma: no cover - exercised below
        response = await call_next(request)
        seen.append(getattr(request.state, "subject", None))
        return response

    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/projects", headers={"Authorization": f"Bearer {TEST_TOKEN}"}).status_code == 200
    assert seen and seen[0] is not None, seen
    assert seen[0] == Subject(
        user_uid=TEST_SUBJECT.user_uid, login=TEST_SUBJECT.login
    ), seen
