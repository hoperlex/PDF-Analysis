"""Two things `T-1` and `T-3` leave that no other suite is the home of.

* **the served document is the one the gate compares.** ``W13-CONF``'s conformance gate
  reads ``create_documentation_app().openapi()``, which builds the eighteen operations with
  nothing behind the ports so that a document can be read on any checkout, without a
  database, an object store or a credential. That is only worth anything if it is the
  *same* document the wired application serves. Asserted here, because the gate cannot
  assert it -- ``tests/contract/api_v1/**`` is tests-only and has no wired application.
* **the health plane of `T-3` is a different application.** Liveness and readiness answer
  on a second port, never under ``/api/v1``, and **outside the authorized surface** so a
  health check needs no credential. `W13-SEAL` section 8.3: *if it inherits an app-wide
  dependency it stops answering and wave 14 discovers that in a deployment.*
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from starlette.testclient import TestClient

from auditmanager.api.app import create_documentation_app
from auditmanager.api.health import LIVENESS_PATH, READINESS_PATH, build_health_app
from w13_api_driver import Surface

OPENAPI = Path(__file__).resolve().parents[3] / "contracts/api/v1/openapi.json"

#: The three figures, as literals. ``OPERATING_CONSTRAINTS.md`` section 12: a count read
#: from the document it is counting cannot tell you the document shrank.
OPENAPI_VERSION = "3.1.0"
BASE_PATH = "/api/v1"
PATH_COUNT = 16
OPERATION_COUNT = 19
SCHEMA_COUNT = 53


class TestTheDocumentedAndTheWiredApplicationAgree:
    def test_the_documented_and_the_wired_app_agree(self, router: Surface) -> None:
        """The same bytes, from an application with ports and one without.

        If these ever diverged, the conformance gate would be comparing the frozen
        contract against a document nothing serves -- which is the most expensive kind of
        green this programme has a name for.
        """
        wired = router.app.openapi()
        documented = create_documentation_app().openapi()
        assert json.dumps(wired, sort_keys=True) == json.dumps(documented, sort_keys=True)

    def test_the_served_document_is_the_shape_the_contract_is(self) -> None:
        document = create_documentation_app().openapi()
        assert document["openapi"] == OPENAPI_VERSION
        assert [server["url"] for server in document["servers"]] == [BASE_PATH]
        assert len(document["paths"]) == PATH_COUNT
        operations = [
            operation["operationId"]
            for path_item in document["paths"].values()
            for method, operation in path_item.items()
            if method in ("get", "post", "put", "patch", "delete")
        ]
        assert len(operations) == OPERATION_COUNT
        assert len(set(operations)) == OPERATION_COUNT, "an operationId is declared twice"
        assert len(document["components"]["schemas"]) == SCHEMA_COUNT

    def test_the_two_schemas_fastapi_would_have_added_are_not_in_it(self) -> None:
        """``HTTPValidationError`` and ``ValidationError``, and the 422 that referenced them.

        FastAPI injects a ``422`` for any operation with parameters that declares none of
        its own. Fourteen of the eighteen displace it by declaring the contract's; the other
        four -- ``getRunStatus``, ``getDocumentVersion``, ``getFinding``, ``exportRunCsv``
        -- declare no 422 at all, because they cannot answer one. A malformed path identity
        is 404 by design and the correlation header is declared but not enforced.

        The three `R-5` listings are in the first group: each declares ``cursor`` and
        ``limit``, and a cursor that is not a continuation token from this API is
        ``validation_failed``. `W39-REVOKE`'s ``changePassword`` is too: it takes a body,
        and a body that is not the declared object is ``validation_failed``.

        **This docstring was the only correct statement of that figure in the tree.**
        ``api/app.py`` said *"Twelve of the seventeen"* for two reseals -- a number whose own
        arithmetic never summed to the surface, since twelve plus four is sixteen. It was
        repaired alongside this line rather than left to be found a third time.
        """
        document = create_documentation_app().openapi()
        schemas = document["components"]["schemas"]
        assert "HTTPValidationError" not in schemas
        assert "ValidationError" not in schemas
        rendered = json.dumps(document)
        assert "HTTPValidationError" not in rendered, "a dangling $ref was left behind"

        declared_422 = {
            operation["operationId"]
            for path_item in document["paths"].values()
            for method, operation in path_item.items()
            if method in ("get", "post") and "422" in operation["responses"]
        }
        assert declared_422 == {
            "appendDecision",
            "createProject",
            "changePassword",
            "issueToken",
            "listDecisionHistory",
            "listDecisions",
            "listDocuments",
            "listProjects",
            "listRunFindings",
            "listRuns",
            "listVersions",
            "startRun",
            "streamDocumentVersionContent",
            "uploadDocument",
        }, declared_422

    def test_no_schema_property_declares_a_default(self) -> None:
        """The contract declares no ``default`` on any property of any of the 51 schemas.

        ``default: null`` on an optional property says the server substitutes ``null``,
        which is not what an absent property means here -- and the conformance gate
        compares ``default``. ``models.optional_property`` is the declaration of that
        intent; this is the property itself, pinned where a change in how FastAPI chooses
        to generate a schema would be caught whether or not that helper is still there.
        """
        contract = json.loads(OPENAPI.read_text(encoding="utf-8"))
        for name, schema in contract["components"]["schemas"].items():
            for prop, sub in (schema.get("properties") or {}).items():
                assert "default" not in sub, f"the contract declares one: {name}.{prop}"

        served = create_documentation_app().openapi()["components"]["schemas"]
        offenders = [
            f"{name}.{prop}"
            for name, schema in served.items()
            for prop, sub in (schema.get("properties") or {}).items()
            if "default" in sub
        ]
        assert offenders == [], offenders

    def test_a_declared_422_is_the_contracts_and_is_never_removed(self) -> None:
        """The removal is narrow, and this is what says so.

        It fires only when the response object is byte-for-byte FastAPI's injected one.
        The eight below declare ``ErrorEnvelope``, which is a different object, and every
        one of them survives.
        """
        contract = json.loads(OPENAPI.read_text(encoding="utf-8"))
        document = create_documentation_app().openapi()
        for path, path_item in contract["paths"].items():
            for method, operation in path_item.items():
                if method not in ("get", "post") or "422" not in operation["responses"]:
                    continue
                served = document["paths"][path][method]["responses"]["422"]
                schema = served["content"]["application/json"]["schema"]
                assert schema == {"$ref": "#/components/schemas/ErrorEnvelope"}, (
                    operation["operationId"],
                    schema,
                )


class TestTheHealthPlaneIsOffTheContract:
    def test_it_answers_without_a_credential(self) -> None:
        """No ``Authorization`` header anywhere in this test. That is the whole point."""
        client = TestClient(build_health_app(object()))
        for path in (LIVENESS_PATH, READINESS_PATH):
            response = client.get(path)
            assert response.status_code == 200, (path, response.content)
            assert json.loads(response.content)["status"] == "ok"

    def test_it_is_not_a_route_on_the_api_application(self) -> None:
        """The contract declares twelve operations and these are not two of them."""
        document = create_documentation_app().openapi()
        assert LIVENESS_PATH not in document["paths"]
        assert READINESS_PATH not in document["paths"]
        assert not any(path.startswith("/health") for path in document["paths"])

    def test_it_publishes_no_document_of_its_own(self) -> None:
        """There is nothing here a client generates code from.

        A second OpenAPI document served by this deployment is a second thing a reader can
        mistake for the contract.
        """
        client = TestClient(build_health_app(None), raise_server_exceptions=False)
        for path in ("/openapi.json", "/docs", "/redoc"):
            assert client.get(path).status_code == 404, path

    def test_readiness_reports_whether_an_application_was_wired(self) -> None:
        """Not a constant. A readiness probe that returns ``ok`` unconditionally is a
        readiness probe that says nothing."""
        wired = TestClient(build_health_app(object())).get(READINESS_PATH)
        bare = TestClient(build_health_app(None)).get(READINESS_PATH)
        assert json.loads(wired.content)["wired"] is True
        assert json.loads(bare.content)["wired"] is False

    def test_the_two_paths_are_the_ones_the_deploy_script_will_poll(self) -> None:
        """Literals: wave 14's proxy configuration will carry these strings."""
        assert LIVENESS_PATH == "/healthz"
        assert READINESS_PATH == "/readyz"
