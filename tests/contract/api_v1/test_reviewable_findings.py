"""The authored contract and transport both admit honest uncertain observations."""
from copy import deepcopy
import pytest
from pydantic import ValidationError

from auditmanager.api.schemas import models
from auditmanager.shared.identity import FindingObservationId, RunId, AnalysisProfileId, PromptBundleId


def observation():
    return {"finding_observation_id": str(FindingObservationId.new()), "run_id": str(RunId.new()),
        "category": "drawing_discrepancy", "finding_text": "Уточнить исполнение узла.",
        "recommendation_text": "Передать проектировщику.", "grounding_kind": "unverified",
        "unverified_reason": "source_binding_unverified", "evidence": [],
        "provenance": {"stage_id": "finding_merge", "analysis_profile_id": str(AnalysisProfileId.new()),
            "prompt_bundle_id": str(PromptBundleId.new()), "provider_mode": "recorded", "model_call_id": None}}


def test_authored_and_served_shapes_admit_unverified_with_limitation(validate, openapi_document):
    row = observation()
    result = validate(openapi_document, [{"name": "uncertain", "schema": "FindingObservation", "payload": row}])
    assert result["uncertain"]["valid"], result["uncertain"]["messages"]
    parsed = models.FindingObservation.model_validate(row)
    assert parsed.grounding_kind.value == "unverified" and parsed.evidence == []


@pytest.mark.parametrize("change", ["missing_reason", "empty_reason", "ordinary_text_empty"])
def test_uncertain_admission_does_not_erase_evidence_guards(change, validate, openapi_document):
    row = deepcopy(observation())
    if change == "missing_reason":
        row.pop("unverified_reason")
    elif change == "empty_reason":
        row["unverified_reason"] = ""
    else:
        row.pop("grounding_kind")
        row.pop("unverified_reason")
    result = validate(openapi_document, [{"name": "invalid", "schema": "FindingObservation", "payload": row}])
    assert not result["invalid"]["valid"]
    with pytest.raises(ValidationError):
        models.FindingObservation.model_validate(row)


@pytest.mark.parametrize("value,valid", [(None, True), ("source_binding_unverified", True),
    ("", False), ("x" * 201, False), (1, False)])
def test_memory_limitation_has_the_same_nullable_bounds_in_contract_and_transport(
        value, valid, validate, openapi_document):
    row = {"finding_text": "Проверить исполнение узла.", "recommendation_text": "Сверить по схеме.",
        "proposed_severity": None, "required_value": None, "stated_value": None,
        "stage_id": "finding_merge", "analysis_profile_id": str(AnalysisProfileId.new()),
        "provider_mode": "recorded", "unverified_reason": value}
    result = validate(openapi_document, [{"name": "memory", "schema": "DecisionMemoryContent", "payload": row}])
    assert result["memory"]["valid"] is valid
    if valid:
        models.DecisionMemoryContent.model_validate(row)
    else:
        with pytest.raises(ValidationError):
            models.DecisionMemoryContent.model_validate(row)
