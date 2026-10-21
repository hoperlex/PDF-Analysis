"""The unserved v3 proposal shape stays closed against the 0023 API vocabulary."""

from __future__ import annotations

from auditmanager.analysis.profiles.ar_v2.response_schema import (
    CATEGORIES as V2_CATEGORIES,
)
from auditmanager.analysis.profiles.ar_v3.response_schema import (
    CATEGORIES,
    NONNORMATIVE_CATEGORIES,
    NORMATIVE_CATEGORIES,
    SEVERITIES,
    response_schema,
)
from auditmanager.api.schemas.models import FindingCategory, Severity


def test_category_and_severity_sets_are_total_against_the_sealed_api() -> None:
    assert NONNORMATIVE_CATEGORIES == V2_CATEGORIES
    assert NORMATIVE_CATEGORIES == (
        "evacuation", "fire_safety", "accessibility", "insulation", "sound",
    )
    assert len(CATEGORIES) == len(set(CATEGORIES)) == 12
    assert set(CATEGORIES) == {item.value for item in FindingCategory}
    assert set(SEVERITIES) == {item.value for item in Severity}


def test_schema_separates_normative_and_nonnormative_fields() -> None:
    schema = response_schema()
    assert schema["required"] == ["observations"]
    assert schema["additionalProperties"] is False
    branches = schema["properties"]["observations"]["items"]["oneOf"]
    assert len(branches) == 2
    ordinary, normative = branches
    for branch in branches:
        assert branch["additionalProperties"] is False
        assert set(branch["required"]) == set(branch["properties"])
        assert branch["properties"]["evidence"]["minItems"] == 1
        assert branch["properties"]["evidence"]["items"]["additionalProperties"] is False
    assert set(ordinary["properties"]["category"]["enum"]) == set(NONNORMATIVE_CATEGORIES)
    assert set(normative["properties"]["category"]["enum"]) == set(NORMATIVE_CATEGORIES)
    assert not {"norm_citations", "required_value", "stated_value"} & set(ordinary["properties"])
    citations = normative["properties"]["norm_citations"]
    assert (citations["minItems"], citations["maxItems"]) == (1, 5)
    assert citations["items"]["properties"]["quote"] == {
        "type": "string", "minLength": 20, "maxLength": 1000,
    }
    assert citations["items"]["additionalProperties"] is False
    assert normative["properties"]["required_value"]["maxLength"] == 200
    assert normative["properties"]["stated_value"]["maxLength"] == 200


def test_schema_returns_a_fresh_tree() -> None:
    first = response_schema()
    first["properties"]["observations"]["items"]["oneOf"][1]["properties"]["category"]["enum"].clear()
    assert response_schema()["properties"]["observations"]["items"]["oneOf"][1]["properties"]["category"]["enum"]
