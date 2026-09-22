"""Two rules no test could redden, restated where `T-1` put them.

`W10-API`'s sweep found most of the retired ``routers/http.py`` and ``routers/errors.py``
guarded: header case-folding, the placeholder that must not swallow a ``/``, the last-wins
rule for a repeated query parameter, the ``405`` code, the driver-prose refusal, the
unmapped-fault mapping and the correlation header on every response all reddened something.
Two did not.

* **a duplicate ``operationId`` is refused at construction.** Removing the check left all
  816 tests green. An ``operationId`` is an operation's identity: the frozen document keys
  on it, the generated client names a function after it, and the conformance gate compares
  the set. A duplicate leaves ``len(routes) == 15`` passing while one frozen operation is
  no longer addressable.
* **a request body must be one JSON object.** Removing the ``isinstance(parsed, dict)``
  check left all 816 tests green. A bare array, a string or ``null`` then reached the
  schema parsers, which called ``set(payload)`` and ``payload.get(...)`` on it.

**Rewritten by `W13-API`, not re-pointed.** ``Router``, ``Route`` and
``decode_json_object`` are gone. Both rules survive and both moved:

* the duplicate check is now in :func:`auditmanager.api.routers.build_router`, because
  FastAPI does **not** refuse a duplicate ``operationId`` -- it logs a warning and serves a
  document declaring the id twice. So the rule had to be rewritten as product code and not
  only as a test;
* the JSON-object rule is Pydantic's, and the refusals are rendered by
  ``handlers.on_request_validation_error``. They carry no ``details`` -- neither does the
  contract's ``ErrorEnvelope`` require any -- so the **message** is the only thing that
  tells a body that did not parse from one that parsed to the wrong thing, and both are
  pinned here as literals.
"""

from __future__ import annotations

import json

import pytest
from fastapi import APIRouter

from auditmanager.api.routers import build_router
from w13_api_driver import Request, Surface, dispatch


class TestTheRouterRefusesADuplicateOperationId:
    """Asserted on the real assembly, not on a stand-in.

    The check lives in ``build_router``, so this drives ``build_router`` -- with a
    seventh group of routes that collides with one of the twelve. Building a two-route
    toy router would prove only that the helper can raise.
    """

    @staticmethod
    def _twelve_plus(extra: APIRouter) -> APIRouter:
        import auditmanager.api.routers as package

        original = package.build_export_routes

        def with_the_collision(router: APIRouter, exports: object) -> None:
            original(router, exports)
            router.include_router(extra)
            router.routes.extend(extra.routes)

        package.build_export_routes = with_the_collision  # type: ignore[assignment]
        try:
            return build_router(
                projects=None,  # type: ignore[arg-type]
                documents=None,  # type: ignore[arg-type]
                runs=None,  # type: ignore[arg-type]
                findings=None,  # type: ignore[arg-type]
                decisions=None,  # type: ignore[arg-type]
                exports=None,  # type: ignore[arg-type]
            )
        finally:
            package.build_export_routes = original  # type: ignore[assignment]

    def test_a_second_route_sharing_an_operation_id_is_refused_at_construction(
        self,
    ) -> None:
        colliding = APIRouter()

        @colliding.get("/other", operation_id="listProjects")
        def other() -> dict[str, str]:  # pragma: no cover - never served
            return {}

        with pytest.raises(ValueError, match="duplicate operationId"):
            self._twelve_plus(colliding)

    def test_the_refusal_names_the_offending_operation_id(self) -> None:
        colliding = APIRouter()

        @colliding.post("/runs/anything", operation_id="getRunStatus")
        def other() -> dict[str, str]:  # pragma: no cover - never served
            return {}

        with pytest.raises(ValueError) as caught:
            self._twelve_plus(colliding)
        assert "getRunStatus" in str(caught.value)

    def test_without_the_check_one_operation_would_become_unaddressable(
        self, router: Surface
    ) -> None:
        """The consequence, asserted so the rule is not merely a raise.

        Distinct ids give a surface whose ``operation_ids`` has one entry per route. A
        duplicate would leave ``routes`` at seventeen and ``operation_ids`` at sixteen,
        which is exactly what ``len(router.routes) == 17`` cannot see.
        """
        assert len(router.routes) == 17
        assert len(router.operation_ids) == 17
        assert len(router.operation_ids) == len(router.routes)


class TestARequestBodyMustBeOneJsonObject:
    """Driven through ``createProject``, which is where a body is now read at all."""

    @staticmethod
    def _post(router: Surface, body: bytes, key: str) -> dict[str, object]:
        answer = dispatch(
            router,
            Request.build(
                "POST",
                "/projects",
                headers={"Content-Type": "application/json", "Idempotency-Key": key},
                body=body,
            ),
        )
        return {"status": answer.status, "body": json.loads(answer.body)}

    def test_an_object_is_accepted(self, router: Surface) -> None:
        answer = self._post(router, b'{"name":"a"}', "rbr-object")
        assert answer["status"] == 201, answer

    @pytest.mark.parametrize(
        ("label", "body"),
        [
            ("array", b"[1, 2, 3]"),
            ("string", b'"just a string"'),
            ("null", b"null"),
            ("number", b"7"),
            ("boolean", b"true"),
        ],
        ids=["array", "string", "null", "number", "boolean"],
    )
    def test_valid_json_that_is_not_an_object_is_refused(
        self, router: Surface, label: str, body: bytes
    ) -> None:
        """Each of these parses cleanly, so the not-JSON branch does not fire. Only the
        object rule can refuse them, and the message is what says so."""
        json.loads(body.decode("utf-8"))  # it really is valid JSON
        answer = self._post(router, body, f"rbr-{label}")
        assert answer["status"] == 422, answer
        assert answer["body"]["error_code"] == "validation_failed"
        assert answer["body"]["message"] == "The request body must be a JSON object."

    def test_bytes_that_are_not_json_are_refused_by_the_other_rule(
        self, router: Surface
    ) -> None:
        """The two refusals carry no details, so the message is the only way to tell a
        body that did not parse from one that parsed to the wrong thing."""
        answer = self._post(router, b"{not json", "rbr-notjson")
        assert answer["status"] == 422, answer
        assert answer["body"]["message"] == "The request body is not valid JSON."

    def test_the_decoders_own_message_never_reaches_the_caller(
        self, router: Surface
    ) -> None:
        """A JSON decoder quotes the offending input, which is caller-controlled text."""
        answer = self._post(router, b'{"k": /etc/passwd}', "rbr-secret")
        rendered = json.dumps(answer["body"])
        assert "/etc/passwd" not in rendered
        assert "line 1" not in rendered
        assert "Expecting" not in rendered
