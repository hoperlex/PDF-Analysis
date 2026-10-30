"""Focused C4 seal proof; full acceptance is owned by the integrator."""
from __future__ import annotations
import inspect
import json
from pathlib import Path
import pytest
from auditmanager.api.app import create_documentation_app
from auditmanager.api.schemas import models
from auditmanager.bootstrap.adapters import ComparisonStageC4Adapter
from auditmanager.comparison.ai_jobs.model import AiScope
from auditmanager.shared.errors import DomainError

OPS = {
"createStageReviewCard","estimateStageChainRun","resumeStageChainRun","startStageChainBatch","getStageChainBatch",
"pauseStageChainBatch","resumeStageChainBatch","cancelStageChainBatch","listStageAiReviews",
"listStageClassifications","getStageSynthesis","listStageGraphicEvidence","listStageLinkRepairs",
"undoStageLinkRepair","listStageChangeCards","getStageChangeCard","applyStageCardVerdicts",
"listStageCardVerdicts","getStageChangeJournal","streamStageChangeJournalXlsx",
"streamStageChangeJournalPdf","streamStageChangeJournalHtml","getStageProfileText","getStageAssembly",
}


def test_c4_surface_is_additive_and_authorized() -> None:
    doc = create_documentation_app().openapi()
    frozen = json.loads(Path("contracts/api/v1/openapi.json").read_text())
    assert doc["info"]["version"] == frozen["info"]["version"] == "1.14.0"
    actual = {op["operationId"] for item in doc["paths"].values() for key,op in item.items()
              if key in {"get","post","put","delete","patch"}}
    assert OPS <= actual and len(actual) == 259
    assert len(doc["paths"]) == 233
    assert set(doc["components"]["schemas"]) == set(frozen["components"]["schemas"])
    for item in doc["paths"].values():
        for method,op in item.items():
            if method not in {"get","post","put","delete","patch"} or op["operationId"] not in OPS:
                continue
            assert op.get("security") == [{"bearerAuth": []}]
            assert "503" in op["responses"]


@pytest.mark.parametrize("modules", ["none", "versions"])
def test_disabled_c4_module_refuses_before_touching_its_arguments(modules: str) -> None:
    adapter = ComparisonStageC4Adapter(None, comparison_modules=modules)
    for name,method in inspect.getmembers(adapter, predicate=inspect.ismethod):
        if name.startswith("_"):
            continue
        params = inspect.signature(method).parameters
        with pytest.raises(DomainError) as error:
            method(**{key:None for key in params})
        assert error.value.detail_fields["dependency"] == "comparison_modules"


def test_stage_estimate_binds_source_before_the_run_identity_exists() -> None:
    preview = AiScope(method="stage_review",project_uid="p",document_uid="d",stage_link_revision_id="revision")
    prepared = AiScope(method="stage_review",project_uid="p",document_uid="d",
                       stage_link_revision_id="revision",stage_chain_run_id="run")
    assert preview.as_document() == prepared.as_document()
    assert prepared.work_kind == "comparison_stage_review"
    assert {system.value for system in models.StageSystem} == {
        "unknown","architecture","structural","electrical","heating_ventilation","water_sewage",
        "fire_protection","low_current","technology","site","other",
    }
