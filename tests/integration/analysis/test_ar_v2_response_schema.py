"""The offline v2 reply schema follows the already sealed public enum."""

from __future__ import annotations

import json
from pathlib import Path

from auditmanager.analysis.profiles.ar_v2.response_schema import (
    CATEGORIES,
    SEVERITIES,
    response_schema,
)


def test_v2_response_enums_match_the_sealed_api() -> None:
    api = json.loads(Path("contracts/api/v1/openapi.json").read_text())
    schemas = api["components"]["schemas"]
    assert list(CATEGORIES) == schemas["FindingCategory"]["enum"]
    assert list(SEVERITIES) == schemas["Severity"]["enum"]


def test_reply_shape_requires_evidence_and_model_proposed_severity() -> None:
    schema = response_schema()
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["observations"]
    observation = schema["properties"]["observations"]["items"]
    assert observation["additionalProperties"] is False
    assert set(observation["required"]) == {
        "category", "finding_text", "recommendation_text", "proposed_severity", "evidence"
    }
    assert observation["properties"]["category"]["enum"] == list(CATEGORIES)
    assert observation["properties"]["proposed_severity"]["enum"] == list(SEVERITIES)
    evidence = observation["properties"]["evidence"]
    assert evidence["minItems"] == 1
    assert evidence["items"]["required"] == ["page_number", "quote"]
    assert evidence["items"]["additionalProperties"] is False
    assert "decided_severity" not in json.dumps(schema)
    assert "char_start" not in json.dumps(schema)


def test_each_caller_receives_an_independent_schema_tree() -> None:
    first = response_schema()
    second = response_schema()
    first["properties"]["observations"]["items"]["properties"]["category"]["enum"].clear()
    category = second["properties"]["observations"]["items"]["properties"]["category"]
    assert category["enum"] == list(CATEGORIES)
