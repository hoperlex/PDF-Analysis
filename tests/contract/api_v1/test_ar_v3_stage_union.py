"""The AR v3 review stage extends RunStatus without changing legacy StageId."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auditmanager.api.schemas.models import ArV3BetaStageId, RunStatus, StageId


ROOT = Path(__file__).resolve().parents[3]
OPENAPI = ROOT / "contracts/api/v1/openapi.json"
LEGACY = (
    "source_preparation", "page_geometry_extraction", "document_context_build",
    "text_analysis", "block_analysis", "finding_merge", "finding_review",
    "finding_correction", "norm_verification",
)


def test_profile_stage_is_separate_from_the_legacy_enum():
    document = json.loads(OPENAPI.read_text())
    schemas = document["components"]["schemas"]
    assert tuple(schemas["StageId"]["enum"]) == LEGACY
    assert tuple(item.value for item in StageId) == LEGACY
    assert schemas["ArV3BetaStageId"]["enum"] == ["ar_v3_citation_review"]
    assert tuple(item.value for item in ArV3BetaStageId) == ("ar_v3_citation_review",)
    assert schemas["StageState"]["properties"]["stage_id"]["anyOf"] == [
        {"$ref": "#/components/schemas/StageId"},
        {"$ref": "#/components/schemas/ArV3BetaStageId"},
    ]
    assert schemas["RunStatus"]["properties"]["degradation_set"]["items"]["anyOf"] == [
        {"$ref": "#/components/schemas/StageId"},
        {"$ref": "#/components/schemas/ArV3BetaStageId"},
    ]


def _run_status(stage_id: str) -> dict[str, object]:
    return {
        "run_id": "run_01M25P3TH08VVTTGJRXYBZZ7RP",
        "project_uid": "prj_01M25P3TH08VVTTGJRXYBZZ7RP",
        "version_uid": "ver_01M25P3TH08VVTTGJRXYBZZ7RP",
        "state": "failed", "provider_mode": "recorded",
        "created_at": "2026-10-23T00:00:00Z",
        "stages": [{"stage_id": stage_id, "status": "failed",
                    "error_code": "analysis_failed"}],
        "degradation_set": [stage_id],
    }


def test_run_status_accepts_profile_stage_in_state_and_degradation():
    parsed = RunStatus.model_validate(_run_status("ar_v3_citation_review"))
    assert parsed.stages[0].stage_id is ArV3BetaStageId.CITATION_REVIEW
    assert parsed.degradation_set == [ArV3BetaStageId.CITATION_REVIEW]


def test_unknown_stage_still_refuses():
    with pytest.raises(ValidationError):
        RunStatus.model_validate(_run_status("ar_v3_unregistered_stage"))
