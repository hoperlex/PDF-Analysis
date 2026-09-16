"""The two request headers the edge reads, and the rules on them no test could redden.

`W10-API` swept `routers/idempotency.py` and `routers/correlation.py` by mutation. Most
of both is guarded: a missing key, a key outside the character class, the header's own
name, the `not_found`-not-`validation_failed` answer for a bad path identity, the
correlation pattern and the echo of a supplied id all redden something. Two rules did not:

* the **length bound** on `Idempotency-Key`. Widening `{0,127}` to `{0,100000}` left all
  816 tests green. The character class is guarded; the bound on how many of those
  characters may be sent is not.
* the **uniqueness** of an assigned correlation id. Replacing `secrets.token_hex(16)`
  with a constant left all 816 tests green. Every existing test asserts that *an* id is
  present, that a supplied one is echoed, and that an unusable one is replaced -- none
  that two requests get different ones, which is the only property that makes the value
  worth assigning.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditmanager.api.routers.correlation import (
    CORRELATION_HEADER,
    new_correlation_id,
    resolve_correlation_id,
)
from auditmanager.api.routers.http import Request
from auditmanager.api.routers.idempotency import (
    IDEMPOTENCY_HEADER,
    require_idempotency_key,
)
from auditmanager.shared.errors import DomainError

#: The frozen API contract, resolved from *this file's* location rather than from any
#: module's, so it is an authority independent of the code under test.
OPENAPI = Path(__file__).resolve().parents[3] / "contracts/api/v1/openapi.json"


def _schema(name: str) -> dict[str, object]:
    return json.loads(OPENAPI.read_text(encoding="utf-8"))["components"]["schemas"][name]


class TestTheIdempotencyKeyLengthIsTheOneTheContractDeclares:
    """`routers/idempotency.py` says its pattern is "exactly
    ``#/components/schemas/IdempotencyKey``". This asserts that claim against the frozen
    document instead of taking it on trust, and then exercises the bound at both sides."""

    def test_the_frozen_document_declares_a_maximum_of_128(self) -> None:
        schema = _schema("IdempotencyKey")
        assert schema["maxLength"] == 128
        assert schema["minLength"] == 1
        assert schema["pattern"] == "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"

    def test_a_key_of_exactly_128_characters_is_accepted(self) -> None:
        key = "k" * 128
        request = Request.build("POST", "/projects", headers={IDEMPOTENCY_HEADER: key})
        assert require_idempotency_key(request) == key

    def test_a_key_of_129_characters_is_refused_by_the_pattern_rule(self) -> None:
        """129, not 1000: one character over is what a bound means.

        The constraint is asserted, not only the refusal. ``require_idempotency_key``
        has two refusing branches and they answer the same ``field`` -- ``required``
        when the header is absent and ``pattern`` when it is malformed -- so a test
        asserting the field alone would pass whichever one fired.
        """
        request = Request.build(
            "POST", "/projects", headers={IDEMPOTENCY_HEADER: "k" * 129}
        )
        with pytest.raises(DomainError) as caught:
            require_idempotency_key(request)
        assert caught.value.detail_fields["field"] == "Idempotency-Key"
        assert caught.value.detail_fields["constraint"] == "pattern"

    def test_an_absent_header_is_refused_as_required_not_as_pattern(self) -> None:
        """The other branch, pinned so the two cannot be confused."""
        with pytest.raises(DomainError) as caught:
            require_idempotency_key(Request.build("POST", "/projects"))
        assert caught.value.detail_fields["constraint"] == "required"

    def test_the_offending_key_is_never_echoed_back(self) -> None:
        """The contract calls it a forbidden detail key: "never returned in a response
        body and never placed in an error envelope"."""
        key = "K" * 129
        request = Request.build("POST", "/projects", headers={IDEMPOTENCY_HEADER: key})
        with pytest.raises(DomainError) as caught:
            require_idempotency_key(request)
        assert key not in str(caught.value.envelope("cid-fixed-0001").as_dict())


class TestAnAssignedCorrelationIdIsDifferentEveryTime:
    """Replacing the generator with a constant left the battery green.

    A correlation id addresses one diagnostic record. If two requests share one, the
    record it addresses is not this request's, and every existing assertion -- that the
    header is present, that the body matches the header, that a supplied id is echoed --
    holds just as well when every response carries the same value.
    """

    def test_two_hundred_generated_ids_are_all_distinct(self) -> None:
        ids = {new_correlation_id() for _ in range(200)}
        assert len(ids) == 200

    def test_two_requests_without_a_supplied_id_are_assigned_different_ones(self) -> None:
        first = resolve_correlation_id(Request.build("GET", "/projects"))
        second = resolve_correlation_id(Request.build("GET", "/projects"))
        assert first != second, (
            "both requests were assigned the same correlation id, so it does not "
            "identify a request"
        )

    def test_an_assigned_id_satisfies_the_pattern_the_contract_declares(self) -> None:
        """Otherwise a generator could be made unique by producing something the frozen
        ``CorrelationId`` schema does not admit."""
        import re

        declared = _schema("CorrelationId")
        pattern = re.compile("^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
        assert declared["pattern"] == pattern.pattern
        for _ in range(20):
            assigned = new_correlation_id()
            assert pattern.match(assigned), assigned
            assert len(assigned) <= 128

    def test_a_supplied_id_is_still_preferred_over_an_assigned_one(self) -> None:
        """The uniqueness rule must not be satisfied by ignoring the caller."""
        supplied = "trace-0123456789"
        request = Request.build(
            "GET", "/projects", headers={CORRELATION_HEADER: supplied}
        )
        assert resolve_correlation_id(request) == supplied
