"""The two request headers the edge reads, and the rules on them no test could redden.

`W10-API` swept `routers/idempotency.py` and `routers/correlation.py` by mutation. Most of
both was guarded: a missing key, a key outside the character class, the header's own name,
the `not_found`-not-`validation_failed` answer for a bad path identity, the correlation
pattern and the echo of a supplied id all reddened something. Two rules did not:

* the **length bound** on `Idempotency-Key`. Widening `{0,127}` to `{0,100000}` left all
  816 tests green. The character class was guarded; the bound on how many of those
  characters may be sent was not.
* the **uniqueness** of an assigned correlation id. Replacing `secrets.token_hex(16)` with
  a constant left all 816 tests green. Every existing test asserted that *an* id is
  present, that a supplied one is echoed, and that an unusable one is replaced -- none that
  two requests get different ones, which is the only property that makes the value worth
  assigning.

**Rewritten by `W13-API`, not re-pointed.** Both helpers changed shape under `T-1`:
``require_idempotency_key`` is a FastAPI dependency whose signature *is* the contract's
``#/components/parameters/IdempotencyKey``, and ``resolve_correlation_id`` takes the header
value instead of a request object. Calling either with a ``Request`` would now be a
``TypeError``, so the two rules above are asserted where they are actually enforced: the
key's bound through the real surface, and the correlation rules through the middleware and
its generator.

**One deliberate change to a refusal, recorded rather than smuggled.** A key of 129
characters used to answer ``details.constraint: "pattern"``, because the hand-written
parser had one refusing branch for every malformed key. The contract declares
``maxLength: 128`` *and* the pattern, Pydantic reports the specific one, and the edge now
reports ``"length"`` for a key that is too long or empty and ``"pattern"`` for one outside
the character class. The message is unchanged and the request is refused either way; what
moved is that the envelope now names the bound that broke. No record in
``tests/characterization/w13_baseline`` covers this path -- case ``27`` covers the *absent*
header, whose ``"required"`` is unchanged -- so this is outside the response baseline and
is reported in ``docs/program/reviews/W13-API.md``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from auditmanager.api.routers.correlation import (
    CORRELATION_HEADER,
    new_correlation_id,
    resolve_correlation_id,
)
from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from w13_api_driver import Request, Surface, dispatch

#: The frozen API contract, resolved from *this file's* location rather than from any
#: module's, so it is an authority independent of the code under test.
OPENAPI = Path(__file__).resolve().parents[3] / "contracts/api/v1/openapi.json"

#: One well-formed body, so a refusal in these tests is the header's and not the body's.
_BODY = json.dumps({"name": "header rules"}).encode("utf-8")


def _schema(name: str) -> dict[str, object]:
    return json.loads(OPENAPI.read_text(encoding="utf-8"))["components"]["schemas"][name]


def _create(router: Surface, key: str | None) -> dict[str, object]:
    headers = {"Content-Type": "application/json"}
    if key is not None:
        headers[IDEMPOTENCY_HEADER] = key
    answer = dispatch(
        router, Request.build("POST", "/projects", headers=headers, body=_BODY)
    )
    return {"status": answer.status, "body": json.loads(answer.body)}


class TestTheIdempotencyKeyLengthIsTheOneTheContractDeclares:
    """``routers/idempotency.py`` declares its parameter as
    ``#/components/schemas/IdempotencyKey``. This asserts that claim against the frozen
    document instead of taking it on trust, and then exercises the bound at both sides,
    through the surface a client reaches."""

    def test_the_frozen_document_declares_a_maximum_of_128(self) -> None:
        schema = _schema("IdempotencyKey")
        assert schema["maxLength"] == 128
        assert schema["minLength"] == 1
        assert schema["pattern"] == "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"

    def test_a_key_of_exactly_128_characters_is_accepted(self, router: Surface) -> None:
        answer = _create(router, "k" * 128)
        assert answer["status"] == 201, answer["body"]

    def test_a_key_of_129_characters_is_refused_for_its_length(
        self, router: Surface
    ) -> None:
        """129, not 1000: one character over is what a bound means.

        The constraint is asserted, not only the refusal. There are three ways this header
        can be refused and they all answer the same ``field`` -- ``required`` when it is
        absent, ``length`` when it is too long or empty, ``pattern`` when it carries a
        character the class forbids -- so a test asserting the field alone would pass
        whichever one fired.
        """
        answer = _create(router, "k" * 129)
        assert answer["status"] == 422
        body = answer["body"]
        assert body["error_code"] == "validation_failed"
        assert body["message"] == "The Idempotency-Key header is not of the declared form."
        assert body["details"] == {"field": "Idempotency-Key", "constraint": "length"}

    def test_a_key_outside_the_character_class_is_refused_by_the_pattern_rule(
        self, router: Surface
    ) -> None:
        """The other malformed branch, pinned so the two cannot be confused.

        ``/`` is inside no part of the declared class, and the key is exactly one
        character over nothing -- its length is fine. So only the pattern can refuse it.
        """
        answer = _create(router, "key/with/slashes")
        assert answer["status"] == 422
        assert answer["body"]["details"] == {
            "field": "Idempotency-Key",
            "constraint": "pattern",
        }

    def test_an_absent_header_is_refused_as_required_not_as_length(
        self, router: Surface
    ) -> None:
        """The third branch. ``records/27`` pins these exact bytes."""
        answer = _create(router, None)
        assert answer["status"] == 422
        assert answer["body"]["message"] == (
            "This operation requires an Idempotency-Key header."
        )
        assert answer["body"]["details"] == {
            "field": "Idempotency-Key",
            "constraint": "required",
        }

    def test_the_offending_key_is_never_echoed_back(self, router: Surface) -> None:
        """The contract calls it a forbidden detail key: "never returned in a response body
        and never placed in an error envelope"."""
        key = "K" * 129
        answer = _create(router, key)
        assert answer["status"] == 422
        assert key not in json.dumps(answer["body"])


class TestAnAssignedCorrelationIdIsDifferentEveryTime:
    """Replacing the generator with a constant left the battery green.

    A correlation id addresses one diagnostic record. If two requests share one, the record
    it addresses is not this request's, and every existing assertion -- that the header is
    present, that the body matches the header, that a supplied id is echoed -- holds just
    as well when every response carries the same value.
    """

    def test_two_hundred_generated_ids_are_all_distinct(self) -> None:
        ids = {new_correlation_id() for _ in range(200)}
        assert len(ids) == 200

    def test_two_requests_without_a_supplied_id_are_assigned_different_ones(
        self, router: Surface
    ) -> None:
        """Driven through the middleware, which is where the assignment now happens."""
        first = dispatch(router, Request.build("GET", "/projects"))
        second = dispatch(router, Request.build("GET", "/projects"))
        assert first.header(CORRELATION_HEADER) is not None
        assert first.header(CORRELATION_HEADER) != second.header(CORRELATION_HEADER), (
            "both requests were assigned the same correlation id, so it does not identify "
            "a request"
        )

    def test_an_assigned_id_satisfies_the_pattern_the_contract_declares(self) -> None:
        """Otherwise a generator could be made unique by producing something the frozen
        ``CorrelationId`` schema does not admit."""
        declared = _schema("CorrelationId")
        pattern = re.compile("^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
        assert declared["pattern"] == pattern.pattern
        for _ in range(20):
            assigned = new_correlation_id()
            assert pattern.match(assigned), assigned
            assert len(assigned) <= 128

    def test_a_supplied_id_is_still_preferred_over_an_assigned_one(
        self, router: Surface
    ) -> None:
        """The uniqueness rule must not be satisfied by ignoring the caller."""
        supplied = "trace-0123456789"
        assert resolve_correlation_id(supplied) == supplied
        answer = dispatch(
            router,
            Request.build("GET", "/projects", headers={CORRELATION_HEADER: supplied}),
        )
        assert answer.header(CORRELATION_HEADER) == supplied

    def test_an_unusable_supplied_id_is_replaced_and_not_refused(
        self, router: Surface
    ) -> None:
        """A correlation id authorises nothing, so a malformed one costs the caller nothing.

        This is why the declared ``X-Correlation-Id`` parameter is *not* a constrained
        FastAPI parameter: a constrained one would answer 422, and four of the twelve
        operations declare no 422 at all.
        """
        unusable = "-not a correlation id-"
        assert resolve_correlation_id(unusable) != unusable
        answer = dispatch(
            router,
            Request.build("GET", "/projects", headers={CORRELATION_HEADER: unusable}),
        )
        assert answer.status == 200, answer.body
        assigned = answer.header(CORRELATION_HEADER)
        assert assigned is not None and assigned != unusable
        assert re.match(r"^cid-[0-9a-f]{32}$", assigned), assigned
