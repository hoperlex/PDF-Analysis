"""Two length bounds that no test could redden.

`W10-API`'s sweep of the query and project schemas found most of the surface guarded: the
minimum limit, the default limit, the cursor's decoded shape, a non-integer limit and the
closed ``CreateProjectRequest`` object all redden something. ``test_query_surface.py``
already pins ``(MIN_LIMIT, MAX_LIMIT, DEFAULT_LIMIT)`` against the frozen document, which is
the right pattern and is why this file does not repeat it.

Two bounds were not reachable by any test:

* ``MAX_CURSOR = 512``. Raising it to 100000 left all 816 tests green. Every cursor the
  suite builds is short, and a forged one is rejected for not decoding rather than for its
  length.
* the project name's ``maxLength = 200``. Raising it to 100000 left all 816 tests green.

Both bounds are asserted against the frozen document, read from **this file's** own
location, so a module drifting away from the contract is a red test rather than a private
agreement between a module and itself.

**Rewritten by `W13-API`, not re-pointed.** ``parse_create_project_request`` is gone: the
project name's bound is now ``models.CreateProjectRequest``'s, which is also what puts
``minLength``/``maxLength`` in the served document, so the bound is asserted where a caller
meets it -- through the operation. ``decode_cursor`` survives unchanged and is still
exercised directly **and** through the surface, because the cursor's length bound is the
one thing about a cursor the declared ``Cursor`` schema cannot enforce for the edge: a
cursor is opaque, and the edge is what decides a forged one is not a continuation token.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditmanager.api.schemas.common import decode_cursor, encode_cursor
from auditmanager.shared.errors import DomainError
from w13_api_driver import Request, Surface, dispatch

OPENAPI = Path(__file__).resolve().parents[3] / "contracts/api/v1/openapi.json"


def _schemas() -> dict[str, dict]:
    return json.loads(OPENAPI.read_text(encoding="utf-8"))["components"]["schemas"]


def _create(router: Surface, name: object, key: str) -> dict[str, object]:
    answer = dispatch(
        router,
        Request.build(
            "POST",
            "/projects",
            headers={"Content-Type": "application/json", "Idempotency-Key": key},
            body=json.dumps({"name": name}).encode("utf-8"),
        ),
    )
    return {"status": answer.status, "body": json.loads(answer.body)}


class TestTheCursorLengthBound:
    """512 is the frozen ``Cursor.maxLength``. The bound needs a cursor that is valid in
    every other respect, or the refusal proves only that base64 did not decode."""

    def test_the_frozen_document_declares_a_maximum_of_512(self) -> None:
        cursor = _schemas()["Cursor"]
        assert cursor["maxLength"] == 512
        assert cursor["minLength"] == 1

    def test_a_well_formed_cursor_of_exactly_512_characters_decodes(self) -> None:
        """A sort key of 380 ``x`` encodes to exactly 512 characters."""
        token = encode_cursor(["x" * 380])
        assert len(token) == 512
        assert decode_cursor(token) == ("x" * 380,)

    def test_a_well_formed_cursor_over_the_bound_is_refused_for_its_length(self) -> None:
        """514, not 513: base64url with its padding stripped never has a length congruent
        to 1 modulo 4, so no token of 513 characters exists. 514 is the first attainable
        length over the bound.

        The token is a real one produced by ``encode_cursor``, so it decodes perfectly well
        and the **only** reason to refuse it is that it is too long. A forged token would be
        refused by the base64 branch instead and would prove nothing about the bound -- both
        branches answer ``constraint: "format"``, so the constraint cannot tell them apart
        and the input has to.
        """
        token = encode_cursor(["x" * 381])
        assert len(token) == 514
        with pytest.raises(DomainError) as caught:
            decode_cursor(token)
        assert caught.value.detail_fields["field"] == "cursor"
        assert caught.value.detail_fields["constraint"] == "format"

    def test_an_empty_cursor_is_refused(self) -> None:
        with pytest.raises(DomainError):
            decode_cursor("")

    def test_the_bound_is_reachable_through_the_operation_that_declares_it(
        self, router: Surface
    ) -> None:
        """The same over-long token, presented as a caller would present it.

        A bound enforced only where a unit test can reach it is a bound a caller never
        meets. This is the half the sweep could not redden.
        """
        token = encode_cursor(["x" * 381])
        answer = dispatch(router, Request.build("GET", f"/projects?cursor={token}"))
        assert answer.status == 422, answer.body
        body = json.loads(answer.body)
        assert body["error_code"] == "validation_failed"
        assert body["details"] == {"field": "cursor", "constraint": "format"}


class TestTheProjectNameLengthBound:
    """200 is the frozen ``CreateProjectRequest.properties.name.maxLength``."""

    def test_the_frozen_document_declares_one_to_two_hundred(self) -> None:
        name = _schemas()["CreateProjectRequest"]["properties"]["name"]
        assert name["maxLength"] == 200
        assert name["minLength"] == 1

    def test_a_name_of_exactly_200_characters_is_accepted(self, router: Surface) -> None:
        answer = _create(router, "n" * 200, "sb-200")
        assert answer["status"] == 201, answer

    def test_a_name_of_201_characters_is_refused_for_its_length(
        self, router: Surface
    ) -> None:
        answer = _create(router, "n" * 201, "sb-201")
        assert answer["status"] == 422, answer
        assert answer["body"]["details"] == {"field": "name", "constraint": "length"}

    def test_an_empty_name_is_refused_for_its_length_not_its_type(
        self, router: Surface
    ) -> None:
        """The other side of the same bound, and a different rule from ``type``.

        Three refusals of this body answer ``field: "name"``. Only the constraint
        distinguishes a name that is the wrong length from one that is the wrong type or
        absent.
        """
        answer = _create(router, "", "sb-empty")
        assert answer["status"] == 422, answer
        assert answer["body"]["details"] == {"field": "name", "constraint": "length"}

    def test_a_non_string_name_is_refused_as_type(self, router: Surface) -> None:
        answer = _create(router, 7, "sb-type")
        assert answer["status"] == 422, answer
        assert answer["body"]["details"] == {"field": "name", "constraint": "type"}

    def test_an_absent_name_is_refused_as_required(self, router: Surface) -> None:
        answer = dispatch(
            router,
            Request.build(
                "POST",
                "/projects",
                headers={
                    "Content-Type": "application/json",
                    "Idempotency-Key": "sb-absent",
                },
                body=b"{}",
            ),
        )
        assert answer.status == 422, answer.body
        assert json.loads(answer.body)["details"] == {
            "field": "name",
            "constraint": "required",
        }

    def test_an_undeclared_property_is_refused_as_additional_properties(
        self, router: Surface
    ) -> None:
        """``records/23-createProject.refusal.additionalProperties.json`` pins these bytes."""
        answer = dispatch(
            router,
            Request.build(
                "POST",
                "/projects",
                headers={
                    "Content-Type": "application/json",
                    "Idempotency-Key": "sb-extra",
                },
                body=json.dumps({"name": "ok", "owner": "someone"}).encode("utf-8"),
            ),
        )
        assert answer.status == 422, answer.body
        body = json.loads(answer.body)
        assert body["details"] == {"field": "body", "constraint": "additionalProperties"}
        assert "owner" not in json.dumps(body), (
            "the refusal reflected the caller's own property name back to them"
        )
