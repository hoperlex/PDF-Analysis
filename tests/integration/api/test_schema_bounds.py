"""Two length bounds in `api/schemas/**` that no test could redden.

`W10-API`'s sweep of the query and project schemas found most of the surface guarded:
the minimum limit, the default limit, the cursor's decoded shape, a non-integer limit and
the closed `CreateProjectRequest` object all redden something. `test_query_surface.py`
already pins `(MIN_LIMIT, MAX_LIMIT, DEFAULT_LIMIT)` against the frozen document, which
is the right pattern and is why this file does not repeat it.

Two bounds were not reachable by any test:

* `MAX_CURSOR = 512`. Raising it to 100000 left all 816 tests green. Every cursor the
  suite builds is short, and a forged one is rejected for not decoding rather than for
  its length.
* `MAX_PROJECT_NAME = 200`. Raising it to 100000 left all 816 tests green.

Both constants carry a comment naming the frozen schema they come from, and both of
those schemas declare the number. The bounds are asserted against the document, read
from this file's own location, so the module drifting away from the contract is a red
test rather than a private agreement between a module and itself.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditmanager.api.schemas.common import decode_cursor, encode_cursor
from auditmanager.api.schemas.projects import parse_create_project_request
from auditmanager.shared.errors import DomainError

OPENAPI = Path(__file__).resolve().parents[3] / "contracts/api/v1/openapi.json"


def _schemas() -> dict[str, dict]:
    return json.loads(OPENAPI.read_text(encoding="utf-8"))["components"]["schemas"]


class TestTheCursorLengthBound:
    """512 is the frozen `Cursor.maxLength`. The bound needs a cursor that is valid in
    every other respect, or the refusal proves only that base64 did not decode."""

    def test_the_frozen_document_declares_a_maximum_of_512(self) -> None:
        cursor = _schemas()["Cursor"]
        assert cursor["maxLength"] == 512
        assert cursor["minLength"] == 1

    def test_a_well_formed_cursor_of_exactly_512_characters_decodes(self) -> None:
        """A sort key of 380 `x` encodes to exactly 512 characters."""
        token = encode_cursor(["x" * 380])
        assert len(token) == 512
        assert decode_cursor(token) == ("x" * 380,)

    def test_a_well_formed_cursor_over_the_bound_is_refused_for_its_length(self) -> None:
        """514, not 513: base64url with its padding stripped never has a length
        congruent to 1 modulo 4, so no token of 513 characters exists. 514 is the first
        attainable length over the bound.

        The token is a real one produced by ``encode_cursor``, so it decodes perfectly
        well and the **only** reason to refuse it is that it is too long. A forged token
        would be refused by the base64 branch instead and would prove nothing about the
        bound -- both branches answer ``constraint: "format"``, so the constraint cannot
        tell them apart and the input has to.
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


class TestTheProjectNameLengthBound:
    """200 is the frozen `CreateProjectRequest.properties.name.maxLength`."""

    def test_the_frozen_document_declares_one_to_two_hundred(self) -> None:
        name = _schemas()["CreateProjectRequest"]["properties"]["name"]
        assert name["maxLength"] == 200
        assert name["minLength"] == 1

    def test_a_name_of_exactly_200_characters_is_accepted(self) -> None:
        name = "n" * 200
        assert parse_create_project_request({"name": name}) == name

    def test_a_name_of_201_characters_is_refused_for_its_length(self) -> None:
        with pytest.raises(DomainError) as caught:
            parse_create_project_request({"name": "n" * 201})
        assert caught.value.detail_fields["field"] == "name"
        assert caught.value.detail_fields["constraint"] == "length"

    def test_an_empty_name_is_refused_for_its_length_not_its_type(self) -> None:
        """The other side of the same bound, and a different rule from ``type``.

        ``parse_create_project_request`` has three refusing branches and two of them
        answer ``field: "name"``. Only the constraint distinguishes a name that is the
        wrong length from one that is the wrong type.
        """
        with pytest.raises(DomainError) as caught:
            parse_create_project_request({"name": ""})
        assert caught.value.detail_fields["constraint"] == "length"

    def test_a_non_string_name_is_refused_as_type(self) -> None:
        with pytest.raises(DomainError) as caught:
            parse_create_project_request({"name": 7})
        assert caught.value.detail_fields["constraint"] == "type"

    def test_an_undeclared_property_is_refused_as_additional_properties(self) -> None:
        with pytest.raises(DomainError) as caught:
            parse_create_project_request({"name": "ok", "owner": "someone"})
        assert caught.value.detail_fields["constraint"] == "additionalProperties"
