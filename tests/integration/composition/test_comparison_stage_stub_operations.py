"""Every sealed C3 route reaches its module-gated port through the composition root."""

from __future__ import annotations

import os
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.comparison.public import COMPARISON_MODULES_ENV
from tests.integration.composition.test_router_answers import DEPLOYMENT_SECRET, static_token
from tests.support.expected_facts import FACTS

PRJ = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"
DOC = "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
DOC2 = "doc_01ARZ3NDEKTSV4RRFFQ69G5FAW"
STU = "stu_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SUF = "suf_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SUC = "suc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SAS = "sas_01ARZ3NDEKTSV4RRFFQ69G5FAV"
STP = "stp_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SLK = "slk_01ARZ3NDEKTSV4RRFFQ69G5FAV"
CPR = "cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
CRN = "crn_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SHA = "a" * 64

PATH_VALUES = {
    "project_uid": PRJ,
    "stage_upload_id": STU,
    "stage_upload_file_id": SUF,
    "stage_upload_candidate_id": SUC,
    "stage_assembly_id": SAS,
    "stage_pair_id": STP,
    "stage_link_revision_id": SLK,
    "stage_chain_run_id": CRN,
}
BODIES: dict[str, dict[str, Any]] = {
    "createStageUpload": {"files": [
        {"display_name": "drawing.zip", "media_kind": "zip", "size_bytes": 10, "sha256": SHA},
    ]},
    "confirmStageUploadCandidate": {"stage": "P", "section_code": "AR", "designation": "AR-1"},
    "confirmStagePair": {"left_document_uid": DOC, "right_document_uid": DOC2},
    "createStageAssembly": {"label": "R", "document_uids": [DOC, DOC2]},
    "reviseStageAssembly": {"base_member_no": 0, "add_document_uids": [DOC], "remove_document_uids": []},
    "setStagePairCompleteness": {"completeness": "full"},
    "applyStageSheetMap": {"items": [{"relation": "only_left", "left_profile_id": CPR}]},
    "startStageChainRun": {"link_revision_id": SLK},
}
OPERATIONS = FACTS.operations[-32:]
DEPENDENCIES = {
    "createStageUpload": "comparison_stage_uploads",
    "listStageUploads": "comparison_stage_uploads",
    "getStageUpload": "comparison_stage_uploads",
    "uploadStageUploadPart": "comparison_stage_uploads",
    "completeStageUploadFile": "comparison_stage_uploads",
    "confirmStageUploadCandidate": "comparison_stage_uploads",
    "rejectStageUploadCandidate": "comparison_stage_uploads",
    "pauseStageUpload": "comparison_stage_uploads",
    "resumeStageUpload": "comparison_stage_uploads",
    "cancelStageUpload": "comparison_stage_uploads",
    "listStagePairs": "comparison_stage_pairs",
    "getStagePair": "comparison_stage_pairs",
    "listStagePairSuggestions": "comparison_stage_pairs",
    "confirmStagePair": "comparison_stage_pairs",
    "createStageAssembly": "comparison_stage_pairs",
    "reviseStageAssembly": "comparison_stage_pairs",
    "setStagePairCompleteness": "comparison_stage_pairs",
    "listStageSheetPassports": "comparison_stage_links",
    "listStageSheetSuggestions": "comparison_stage_links",
    "getStageSheetMap": "comparison_stage_links",
    "applyStageSheetMap": "comparison_stage_links",
    "listStageSheetMapHistory": "comparison_stage_links",
    "getStageSheetMapRevision": "comparison_stage_links",
    "listStageTextFragments": "comparison_stage_text",
    "listStageTextExclusions": "comparison_stage_text",
    "listStageRawDifferences": "comparison_stage_text",
    "listStageTextHints": "comparison_stage_text",
    "recomputeStageTextEvidence": "comparison_stage_text",
    "startStageChainRun": "comparison_stage_runs",
    "listStageChainRuns": "comparison_stage_runs",
    "getStageChainRun": "comparison_stage_runs",
    "cancelStageChainRun": "comparison_stage_runs",
}
SERVED_PAIR_OPERATIONS = frozenset({
    "listStagePairs", "getStagePair", "listStagePairSuggestions", "confirmStagePair",
    "createStageAssembly", "reviseStageAssembly", "setStagePairCompleteness",
})
SERVED_UPLOAD_OPERATIONS = frozenset({
    "createStageUpload", "listStageUploads", "getStageUpload", "uploadStageUploadPart",
    "completeStageUploadFile", "confirmStageUploadCandidate", "rejectStageUploadCandidate",
    "pauseStageUpload", "resumeStageUpload", "cancelStageUpload",
})
SERVED_LINK_OPERATIONS = frozenset({
    "listStageSheetPassports", "listStageSheetSuggestions", "getStageSheetMap",
    "applyStageSheetMap", "listStageSheetMapHistory", "getStageSheetMapRevision",
})
SERVED_TEXT_READ_OPERATIONS = frozenset({
    "listStageTextFragments", "listStageTextExclusions",
    "listStageRawDifferences", "listStageTextHints",
})
SERVED_TEXT_WRITE_OPERATIONS = frozenset({"recomputeStageTextEvidence"})


def _client(modules: str) -> TestClient:
    environ = {k: v for k, v in os.environ.items() if k != COMPARISON_MODULES_ENV} | {
        API_TOKEN_VARIABLE: DEPLOYMENT_SECRET, COMPARISON_MODULES_ENV: modules,
    }
    application = create_app(environ=environ)
    return TestClient(create_asgi_app(environ=environ, application=application),
                      raise_server_exceptions=False)


@pytest.fixture(scope="module", params=["none", "versions,stages"])
def client(request: Any) -> tuple[TestClient, str]:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    modules = str(request.param)
    return _client(modules), modules


def test_the_literal_lane_map_covers_exactly_the_new_thirty_two_operations() -> None:
    assert len(OPERATIONS) == len(DEPENDENCIES) == 32
    assert {name for _method, _path, name in OPERATIONS} == set(DEPENDENCIES)


@pytest.mark.parametrize("method,path,name", OPERATIONS, ids=[row[2] for row in OPERATIONS])
def test_every_stage_route_answers_a_typed_module_or_lane_refusal(
    client: tuple[TestClient, str], method: str, path: str, name: str,
) -> None:
    app, modules = client
    for parameter, value in PATH_VALUES.items():
        path = path.replace("{" + parameter + "}", value)
    assert "{" not in path, (name, path)
    headers = {"Authorization": f"Bearer {static_token()}"}
    kwargs: dict[str, Any] = {}
    if method.lower() != "get":
        headers["Idempotency-Key"] = f"c3-stub-{name}"
    if name == "uploadStageUploadPart":
        path += "?part_number=1"
        headers["content-type"] = "application/octet-stream"
        kwargs["content"] = b"x"
    elif name in BODIES:
        kwargs["json"] = BODIES[name]
    response = app.request(method, path, headers=headers, **kwargs)
    body = response.json()
    if modules == "versions,stages" and name in (
        SERVED_PAIR_OPERATIONS | SERVED_UPLOAD_OPERATIONS
        | SERVED_LINK_OPERATIONS | SERVED_TEXT_READ_OPERATIONS
        | SERVED_TEXT_WRITE_OPERATIONS
    ):
        assert response.status_code == 404, (name, response.status_code, body)
        assert body["error_code"] == "not_found"
        return
    assert response.status_code == 503, (name, modules, response.status_code, body)
    assert body["error_code"] == "dependency_unavailable"
    assert body["contract_version"] == "1.12.0"
    expected = "comparison_modules" if modules == "none" else DEPENDENCIES[name]
    assert body["details"] == {"dependency": expected}, (name, modules, body)


def test_oversized_stage_part_is_refused_before_the_stub(client: tuple[TestClient, str]) -> None:
    app, _modules = client
    response = app.put(
        f"/stage-uploads/{STU}/files/{SUF}/parts?part_number=1",
        headers={"Authorization": f"Bearer {static_token()}",
                 "Idempotency-Key": "c3-part-size", "content-type": "application/octet-stream"},
        content=b"x" * (16 * 1024 * 1024 + 1),
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_failed"
