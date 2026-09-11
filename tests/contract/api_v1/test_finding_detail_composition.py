"""`FindingDetail` validates the payload it exists to carry, and stays closed.

The defect this pins, reported by Gate A session `A5` in
`docs/program/tasks/P3-API-01.md` and repaired by `A7-FIX`:

    FindingDetail: allOf: [ {$ref: Finding}, {properties: {latest_comment,
                                                           decision_event_count}} ]
    Finding:       additionalProperties: false

Under JSON Schema 2020-12 - which OpenAPI 3.1 adopts wholesale - `additionalProperties`
is evaluated against the property annotations of **its own** schema object. Sibling
`allOf` branches contribute nothing to it. So the closed `Finding` branch rejected
`latest_comment` and `decision_event_count` as unexpected, and the composed schema
failed for exactly the payloads it was written for. `GET /findings/{finding_uid}`
declares `FindingDetail` as its 200 body.

Two things are asserted here, and the second is what keeps the repair honest:

1. a realistic detail body, carrying both added fields, validates against
   `FindingDetail`; and
2. an unknown property is still rejected on `Finding` **and** on `FindingDetail`.

A repair that bought (1) by loosening closure would pass (1) and fail (2). That is the
whole point: this repository refuses silent extra fields, and a schema that accepts
anything is worse than one that rejects too much.

`test_the_pre_fix_shape_still_reproduces_the_defect` evaluates the original composition,
rebuilt in memory, through the same validator - so this guard is shown to fail on every
run rather than trusted to have failed once.
"""

from __future__ import annotations

from typing import Any

import pytest

DETAIL_SCHEMA = "FindingDetail"
BASE_SCHEMA = "Finding"


# --------------------------------------------------------------------------------
# The defect itself: the payload the detail endpoint returns must validate.
# --------------------------------------------------------------------------------


def test_a_detail_body_carrying_both_added_fields_validates(
    openapi_document: dict[str, Any],
    finding_detail_payload: dict[str, Any],
    detail_only_properties: frozenset[str],
    validate,
) -> None:
    """The regression. Red before the repair, green after."""
    assert detail_only_properties <= finding_detail_payload.keys(), (
        "the fixture is meant to carry both added fields; without them it cannot "
        "witness the defect"
    )

    results = validate(
        openapi_document,
        [
            {
                "name": "detail",
                "schema": DETAIL_SCHEMA,
                "payload": finding_detail_payload,
            }
        ],
    )
    result = results["detail"]
    assert result["valid"], (
        f"a realistic {DETAIL_SCHEMA} body carrying "
        f"{sorted(detail_only_properties)} does not validate against the document: "
        + "; ".join(result["messages"])
    )


def test_the_same_body_without_the_added_fields_validates_as_a_finding(
    openapi_document: dict[str, Any],
    finding_payload: dict[str, Any],
    validate,
) -> None:
    """The fixture is a real `Finding` too, so failure above cannot be a bad fixture."""
    results = validate(
        openapi_document,
        [{"name": "base", "schema": BASE_SCHEMA, "payload": finding_payload}],
    )
    result = results["base"]
    assert result["valid"], "; ".join(result["messages"])


# --------------------------------------------------------------------------------
# Closure: the reason `additionalProperties: false` is there in the first place.
# --------------------------------------------------------------------------------


@pytest.mark.parametrize("schema_name", [BASE_SCHEMA, DETAIL_SCHEMA])
def test_an_unknown_property_is_still_rejected(
    openapi_document: dict[str, Any],
    finding_detail_payload: dict[str, Any],
    finding_payload: dict[str, Any],
    unknown_property: str,
    validate,
    schema_name: str,
) -> None:
    """A fix that bought validity by accepting anything would fail here."""
    base = finding_payload if schema_name == BASE_SCHEMA else finding_detail_payload
    payload = dict(base, **{unknown_property: "x"})

    results = validate(
        openapi_document,
        [{"name": "unknown", "schema": schema_name, "payload": payload}],
    )
    result = results["unknown"]
    assert not result["valid"], (
        f"{schema_name} accepted the undeclared property {unknown_property!r}; "
        "the closed response shape has been lost"
    )
    assert any(unknown_property in message for message in result["messages"]), (
        f"{schema_name} rejected the payload, but not for the undeclared property: "
        + "; ".join(result["messages"])
    )


@pytest.mark.parametrize("schema_name", [BASE_SCHEMA, DETAIL_SCHEMA])
def test_the_added_fields_are_rejected_where_they_do_not_belong(
    openapi_document: dict[str, Any],
    finding_payload: dict[str, Any],
    validate,
    schema_name: str,
) -> None:
    """`Finding` is the list item type; the detail fields must not leak into it.

    This is the assertion that rules out "just put the two properties on `Finding`".
    `FindingPage.items` is a `$ref` to `Finding`, so widening `Finding` would let a
    list response carry the detail projection and still validate - erasing exactly the
    distinction `FindingDetail` exists to draw.
    """
    payload = dict(finding_payload, latest_comment="x", decision_event_count=1)
    results = validate(
        openapi_document,
        [{"name": "detail_fields", "schema": schema_name, "payload": payload}],
    )
    result = results["detail_fields"]
    if schema_name == DETAIL_SCHEMA:
        assert result["valid"], "; ".join(result["messages"])
    else:
        assert not result["valid"], (
            "Finding accepted the detail-only projection fields; a list response "
            "could now carry them and still validate"
        )


# --------------------------------------------------------------------------------
# The guard is shown to fail: the original composition, evaluated in memory.
# --------------------------------------------------------------------------------


def test_the_pre_fix_shape_still_reproduces_the_defect(
    document_with_the_pre_fix_shape: dict[str, Any],
    finding_detail_payload: dict[str, Any],
    detail_only_properties: frozenset[str],
    validate,
) -> None:
    """`allOf` over a closed `$ref` rejects the very fields the branch adds.

    Not a description of a past bug: the shape is rebuilt and re-evaluated here, so if
    a future edit reintroduced it, the assertions above would go red rather than this
    one going quietly stale.
    """
    results = validate(
        document_with_the_pre_fix_shape,
        [
            {
                "name": "pre_fix",
                "schema": DETAIL_SCHEMA,
                "payload": finding_detail_payload,
            }
        ],
    )
    result = results["pre_fix"]
    assert not result["valid"], (
        "the pre-fix composition accepted the payload; the premise of this repair - "
        "that a sibling allOf branch contributes nothing to additionalProperties - "
        "no longer holds, and the repair should be re-derived"
    )
    joined = " ".join(result["messages"])
    for name in sorted(detail_only_properties):
        assert name in joined, (
            f"the pre-fix composition failed, but not on {name!r}: {joined}"
        )


# --------------------------------------------------------------------------------
# Structure: no `allOf` in the document composes a closed `$ref`, anywhere.
# --------------------------------------------------------------------------------


def _walk(node: Any, path: str = "$"):
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, f"{path}[{index}]")


def test_no_allof_composes_a_reference_to_a_closed_schema(
    openapi_document: dict[str, Any],
) -> None:
    """The defect shape, searched for across the whole document rather than one schema.

    Any `allOf` that both references a schema carrying `additionalProperties: false`
    and contributes properties of its own has the identical evaluation-scope defect.
    This is the audit that keeps it from coming back under another name.
    """
    schemas = openapi_document["components"]["schemas"]
    offenders: list[str] = []

    for path, node in _walk(openapi_document):
        if not isinstance(node, dict) or not isinstance(node.get("allOf"), list):
            continue
        branches = node["allOf"]
        closed_refs = [
            branch["$ref"]
            for branch in branches
            if isinstance(branch, dict)
            and isinstance(branch.get("$ref"), str)
            and branch["$ref"].startswith("#/components/schemas/")
            and schemas.get(branch["$ref"].rsplit("/", 1)[-1], {}).get(
                "additionalProperties"
            )
            is False
        ]
        contributes = any(
            isinstance(branch, dict) and branch.get("properties")
            for branch in branches
            if "$ref" not in branch
        )
        if closed_refs and contributes:
            offenders.append(f"{path} composes {closed_refs} and adds properties")

    assert not offenders, (
        "allOf over a closed $ref cannot validate the properties the sibling branch "
        "adds, under JSON Schema 2020-12: " + "; ".join(offenders)
    )


def test_both_shapes_are_closed_in_the_document(
    openapi_document: dict[str, Any],
) -> None:
    """Closure is declared, not merely observed - the structural half of the check."""
    schemas = openapi_document["components"]["schemas"]
    for name in (BASE_SCHEMA, DETAIL_SCHEMA):
        assert schemas[name].get("additionalProperties") is False, (
            f"{name} is no longer a closed object"
        )


def test_the_detail_shape_is_the_base_shape_plus_exactly_two_properties(
    openapi_document: dict[str, Any],
    detail_only_properties: frozenset[str],
) -> None:
    """Anti-drift for the restated shape.

    `FindingDetail` restates `Finding`'s properties rather than composing them, which
    is what keeps both closed. The cost of restating is that the two can drift; this
    is the assertion that makes drift a test failure instead of a silent divergence.
    """
    schemas = openapi_document["components"]["schemas"]
    base = schemas[BASE_SCHEMA]
    detail = schemas[DETAIL_SCHEMA]

    expected = base["properties"].keys() | detail_only_properties
    assert detail["properties"].keys() == expected, (
        "FindingDetail is no longer Finding's property set plus exactly "
        f"{sorted(detail_only_properties)}"
    )
    for name, schema in base["properties"].items():
        assert detail["properties"][name] == schema, (
            f"FindingDetail.{name} has drifted from Finding.{name}"
        )
    assert set(detail["required"]) == set(base["required"]), (
        "FindingDetail's required set has drifted from Finding's"
    )
    assert detail["type"] == base["type"] == "object"


def test_no_response_description_claims_a_unique_retryable_code(openapi_document) -> None:
    """Prose in the document must not contradict the catalog it points at.

    `DependencyUnavailable` called `dependency_unavailable` "the one retryable code in this
    surface". The catalog marks two codes retryable, and the second -
    `idempotency_key_in_progress` - is reachable on every write. B6 found it while
    implementing the routers.

    The harm is specific: `retryable` is pinned per code by the catalog and a caller must
    read it from the envelope. A description asserting there is only one retryable code
    invites exactly the inference the envelope exists to prevent.
    """
    import json
    import pathlib
    import re

    catalog = json.loads(
        (
            pathlib.Path(__file__).resolve().parents[3]
            / "contracts/domain/v1/error-codes.json"
        ).read_text(encoding="utf-8")
    )
    retryable = {code for code, entry in catalog["codes"].items() if entry["retryable"]}
    assert len(retryable) > 1, (
        "this guard assumes more than one retryable code; if the catalog ever has exactly "
        "one, the claim it forbids would become true and this test must be revisited"
    )

    prose = json.dumps(openapi_document, ensure_ascii=False)
    uniqueness_claim = re.compile(
        r"the (?:one|only|single) retryable code", re.IGNORECASE
    )
    assert not uniqueness_claim.search(prose), (
        "a response description claims a unique retryable code, but the catalog marks "
        f"{sorted(retryable)} retryable"
    )
