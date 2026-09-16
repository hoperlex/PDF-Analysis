"""Two rules in `routers/http.py` and `routers/errors.py` that no test could redden.

`W10-API`'s sweep found most of both modules guarded: header case-folding, the
placeholder that must not swallow a `/`, the last-wins rule for a repeated query
parameter, the `405` code, the driver-prose refusal, the unmapped-fault mapping and the
correlation header on every response all redden something. Two did not.

* **`Router` refuses a duplicate `operationId`.** Removing the check left all 816 tests
  green. It is not a defensive nicety: `_by_operation` is a dict, so a duplicate
  silently **overwrites** the first route. `routes` still reports twelve, and the
  existing `len(app.router.routes) == 12` assertion still passes, while `operation_ids`
  quietly holds eleven and one frozen operation is no longer addressable by its id.

* **A request body must be one JSON object.** Removing the `isinstance(parsed, dict)`
  check left all 816 tests green. A bare array, a string or `null` then reaches the
  schema parsers, which call `set(payload)` and `payload.get(...)` on it.

`decode_json_object`'s two refusals carry **no details at all** -- they are told apart
only by their message -- so the messages are pinned here as literals. That is the only
thing that distinguishes "not valid JSON" from "not a JSON object", and they are
different faults with different fixes.
"""

from __future__ import annotations

import json

import pytest

from auditmanager.api.routers.errors import decode_json_object
from auditmanager.api.routers.http import Request, Response, Route, Router
from auditmanager.shared.errors import DomainError, ErrorCode


def _handler(_: Request) -> Response:
    return Response(200, b"{}")


class TestTheRouterRefusesADuplicateOperationId:
    def test_two_routes_sharing_an_operation_id_are_refused_at_construction(self) -> None:
        with pytest.raises(ValueError, match="duplicate operationId"):
            Router(
                [
                    Route("listProjects", "GET", "/projects", _handler),
                    Route("listProjects", "GET", "/other", _handler),
                ]
            )

    def test_the_refusal_names_the_offending_operation_id(self) -> None:
        with pytest.raises(ValueError) as caught:
            Router(
                [
                    Route("getRun", "GET", "/runs/{run_id}", _handler),
                    Route("getRun", "POST", "/runs", _handler),
                ]
            )
        assert "getRun" in str(caught.value)

    def test_without_the_check_one_operation_would_become_unaddressable(self) -> None:
        """The consequence, asserted so the rule is not merely a raise.

        Distinct ids give a router whose ``operation_ids`` has one entry per route. A
        duplicate would leave ``routes`` at two and ``operation_ids`` at one, which is
        exactly what ``len(router.routes) == 12`` cannot see.
        """
        router = Router(
            [
                Route("listProjects", "GET", "/projects", _handler),
                Route("createProject", "POST", "/projects", _handler),
            ]
        )
        assert len(router.routes) == 2
        assert router.operation_ids == frozenset({"listProjects", "createProject"})
        assert len(router.operation_ids) == len(router.routes)


class TestARequestBodyMustBeOneJsonObject:
    def test_an_object_is_returned_as_a_mapping(self) -> None:
        assert decode_json_object(b'{"name":"a"}') == {"name": "a"}

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
    def test_valid_json_that_is_not_an_object_is_refused(self, label: str, body: bytes) -> None:
        """Each of these parses cleanly, so the JSON branch does not fire. Only the
        object rule can refuse them, and the message is what says so."""
        assert json.loads(body.decode("utf-8")) is not None or label == "null"
        with pytest.raises(DomainError) as caught:
            decode_json_object(body)
        assert caught.value.code is ErrorCode.VALIDATION_FAILED
        assert str(caught.value) == "The request body must be a JSON object."

    def test_bytes_that_are_not_json_are_refused_by_the_other_rule(self) -> None:
        """The two refusals carry no details, so the message is the only way to tell
        a body that did not parse from one that parsed to the wrong thing."""
        with pytest.raises(DomainError) as caught:
            decode_json_object(b"{not json")
        assert str(caught.value) == "The request body is not valid JSON."

    def test_the_decoder_s_own_message_never_reaches_the_caller(self) -> None:
        """A JSON decoder quotes the offending input, which is caller-controlled text."""
        with pytest.raises(DomainError) as caught:
            decode_json_object(b'{"k": /etc/passwd}')
        rendered = str(caught.value.envelope("cid-fixed-0001").as_dict())
        assert "/etc/passwd" not in rendered
        assert "line 1" not in rendered
