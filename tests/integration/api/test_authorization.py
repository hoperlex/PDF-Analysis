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

import json

import pytest

from auditmanager.api.app import create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE, SCHEME_NAME
from w13_api_driver import TEST_TOKEN, Request, Surface, dispatch

#: The twelve, written out: one request each, shaped so that *authorization* is the only
#: thing that can refuse it before anything else does.
FIFTEEN = (
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
)

#: The catalog's own summary for the code, as a literal. `W13-SEAL` section 8.1 requires
#: this exact answer and not merely a 401.
AUTHENTICATION_REQUIRED = "authentication_required"


def _envelope(answer) -> dict:
    assert answer.header("Content-Type") == "application/json", answer.headers
    assert answer.header("X-Correlation-Id"), answer.headers
    body = json.loads(answer.body)
    assert "detail" not in body, (
        f"FastAPI's own body reached the client: {body!r}. This is the `auto_error` trap."
    )
    return body


def test_the_fifteen_are_all_behind_the_seam(router: Surface) -> None:
    """One request per operation, with no credential. Fifteen, not fourteen."""
    assert len(FIFTEEN) == 15
    assert {operation for operation, _, _ in FIFTEEN} == router.operation_ids
    open_surface = []
    for operation, method, path in FIFTEEN:
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
        ("a credential the deployment does not accept", "not-the-configured-token"),
        ("an empty bearer", ""),
        ("the configured token with one character removed", TEST_TOKEN[:-1]),
        ("the configured token with one character added", TEST_TOKEN + "x"),
    ],
    ids=["absent", "wrong", "empty", "one-short", "one-long"],
)
def test_a_credential_the_deployment_does_not_accept_is_refused(
    router: Surface, label: str, credential: str | None
) -> None:
    """Including the two neighbours of the real token.

    A comparison that passed for a prefix or for a longer string would be a comparison
    that is not a comparison. ``hmac.compare_digest`` is what makes the timing of these
    five indistinguishable as well, which no test can assert and which is why the
    implementation says so out loud.
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
    for path_item in document["paths"].values():
        for method, operation in path_item.items():
            if method in ("get", "post"):
                assert operation["security"] == [{SCHEME_NAME: []}], (
                    method,
                    operation["operationId"],
                    operation.get("security"),
                )


def test_the_environment_variable_is_the_one_the_deployment_will_set() -> None:
    """A literal, because a deployment sets a string and not a symbol."""
    assert API_TOKEN_VARIABLE == "AUDITMANAGER_API_TOKEN"
