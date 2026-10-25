"""`AR-V3-BETA-PACK-STATUS-API-01`: the sealed 200 body of `getArV3BetaPackStatus`.

The frozen document is the authority. Cases are evaluated by a real JSON Schema 2020-12
validator (the `validate` fixture drives the governance interpreter), so closure, the enum, the
six-item bound and the date pattern are proven by the validator and not by a hand-written copy of
those rules. The model the server answers with is held to the same document: what the adapter
produces must pass, and what the contract forbids must be refused.
"""

from __future__ import annotations

import copy
from typing import Any, Callable

import pytest

from auditmanager.api.schemas import models

SCHEMA = "ArV3BetaPackStatus"
SCOPES = ["F1", "F2", "A1", "A2", "S1", "S2"]
INSTALLED: dict[str, Any] = {
    "state": "installed",
    "analysis_profile_id": "ap_01M5M28ZCDD8VPSP1BTAEW92YE",
    "prompt_bundle_id": "pb_01M5M28ZCDVCR37BX1884JGSPM",
    "pack_sha256": "ab" * 32,
    "scope_ids": SCOPES,
    "review": {
        "reviewer": "Test Reviewer", "capacity": "expert", "reviewed_at": "2026-10-26",
        "decision_ref": "TEST-RULING-1", "scope_statement": "six synthetic scopes, test only",
    },
}
Validate = Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]]


def _with(**changes: Any) -> dict[str, Any]:
    payload = copy.deepcopy(INSTALLED)
    payload.update(changes)
    return payload


def _without(*keys: str) -> dict[str, Any]:
    payload = copy.deepcopy(INSTALLED)
    for key in keys:
        del payload[key]
    return payload


ACCEPTED = {
    "not_installed": {"state": "not_installed"},
    "installed": INSTALLED,
}
REFUSED = {
    "no_state": _without("state"),
    "unknown_state": _with(state="pending"),
    "unknown_property": _with(map_sha256="a" * 64),
    "set_identity_is_not_a_property": _with(set_id="nrs_01M5M28ZCDD8VPSP1BTAEW92YE"),
    "five_scopes": _with(scope_ids=SCOPES[:5]),
    "seven_scopes": _with(scope_ids=[*SCOPES, "S2"]),
    "unknown_scope": _with(scope_ids=[*SCOPES[:5], "S3"]),
    "short_digest": _with(pack_sha256="ab" * 31),
    "upper_case_digest": _with(pack_sha256="AB" * 32),
    "profile_id_of_another_kind": _with(analysis_profile_id="pb_01M5M28ZCDVCR37BX1884JGSPM"),
    "review_without_a_reviewer": _with(review={
        key: value for key, value in INSTALLED["review"].items() if key != "reviewer"
    }),
    "review_with_an_extra_key": _with(review={**INSTALLED["review"], "approved": True}),
    "review_date_is_not_a_date_shape": _with(review={**INSTALLED["review"], "reviewed_at": "26.10.2026"}),
    "review_value_is_not_a_string": _with(review={**INSTALLED["review"], "capacity": 7}),
    "null_instead_of_absent": _with(review=None),
}


def _verdicts(validate: Validate, document: dict[str, Any], cases: dict[str, Any]) -> dict[str, bool]:
    results = validate(
        document,
        [{"name": name, "schema": SCHEMA, "payload": payload} for name, payload in cases.items()],
    )
    return {name: results[name]["valid"] for name in cases}


def test_the_contract_accepts_both_states(validate: Validate, openapi_document: dict[str, Any]) -> None:
    assert _verdicts(validate, openapi_document, ACCEPTED) == {name: True for name in ACCEPTED}


def test_the_contract_refuses_everything_it_closes_off(
    validate: Validate, openapi_document: dict[str, Any],
) -> None:
    assert _verdicts(validate, openapi_document, REFUSED) == {name: False for name in REFUSED}


def test_what_the_server_models_answer_with_passes_the_contract(
    validate: Validate, openapi_document: dict[str, Any],
) -> None:
    served = {
        "not_installed": models.ArV3BetaPackStatus(state="not_installed").model_dump(
            mode="json", exclude_unset=True,
        ),
        "installed": models.ArV3BetaPackStatus.model_validate(INSTALLED).model_dump(
            mode="json", exclude_unset=True,
        ),
    }
    assert served == ACCEPTED
    assert _verdicts(validate, openapi_document, served) == {name: True for name in served}


def test_the_operation_is_declared_the_way_the_group_reads_are(openapi_document: dict[str, Any]) -> None:
    paths = openapi_document["paths"]
    operation = paths["/ar-v3-beta/pack"]["get"]
    sibling = paths["/ar-v3-beta/groups/{group_id}"]["get"]
    assert operation["operationId"] == "getArV3BetaPackStatus"
    assert operation["tags"] == sibling["tags"] == ["runs"]
    assert operation["security"] == sibling["security"] == [{"bearerAuth": []}]
    assert operation["parameters"] == [{"$ref": "#/components/parameters/CorrelationId"}]
    assert list(operation["responses"]) == ["200", "401", "403", "500", "503"]
    for code in ("401", "403", "500", "503"):
        assert operation["responses"][code] == sibling["responses"][code], code
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ArV3BetaPackStatus"
    }
    assert "requestBody" not in operation


def test_the_pack_schemas_carry_no_identity_digest_or_path_property(openapi_document: dict[str, Any]) -> None:
    schemas = openapi_document["components"]["schemas"]
    assert set(schemas[SCHEMA]["properties"]) == {
        "state", "analysis_profile_id", "prompt_bundle_id", "pack_sha256", "scope_ids", "review",
    }
    assert schemas[SCHEMA]["required"] == ["state"]
    assert set(schemas["ArV3BetaPackReview"]["properties"]) == {
        "reviewer", "capacity", "reviewed_at", "decision_ref", "scope_statement",
    }
    assert set(schemas["ArV3BetaPackReview"]["required"]) == set(schemas["ArV3BetaPackReview"]["properties"])
    assert schemas[SCHEMA]["additionalProperties"] is False
    assert schemas["ArV3BetaPackReview"]["additionalProperties"] is False
    assert schemas[SCHEMA]["properties"]["scope_ids"]["items"]["enum"] == SCOPES
    assert (schemas[SCHEMA]["properties"]["scope_ids"]["minItems"],
            schemas[SCHEMA]["properties"]["scope_ids"]["maxItems"]) == (6, 6)


@pytest.mark.parametrize("forbidden", ["map_sha256", "set_id", "set_sha256", "snapshot_id", "blob_id", "path"])
def test_no_forbidden_property_is_declared_anywhere_in_the_pack_schemas(
    openapi_document: dict[str, Any], forbidden: str,
) -> None:
    schemas = openapi_document["components"]["schemas"]
    for name in (SCHEMA, "ArV3BetaPackReview"):
        assert forbidden not in schemas[name]["properties"], (name, forbidden)
