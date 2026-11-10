"""`CRIT-SEAL-50` (contract 1.51.0): the seven sleeping routes of the «Прецеденты» surface, the role register and the schemas, with no database.

The routes are mounted alone on a bare ``FastAPI`` application with the principal the authorization seam would publish. What is shown:

* **every body is asleep, loudly**: ``503 dependency_unavailable`` with the stable class name of the lane that owns it, never an empty answer
  (the error catalogue is closed and has no ``501``; every earlier seal's stubs answer ``503``);
* a malformed identity is ``404``, a missing ``Idempotency-Key`` or a body that is not the declared one is ``422``, so a sleeping route is
  still a closed route -- the lane that fills it inherits the validation;
* **who may call what** is the register's: written here as literals, not read from the contract. The viewer is in none of the sets, and the
  context operation is a runner operation with no role;
* the schemas: the closed vocabularies, the at-most-two hints (and no hint of AR v3), `Evidence` and `RunStageChip` untouched.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from auditmanager.api.app import create_documentation_app
from auditmanager.api.routers.handlers import install_exception_handlers
from auditmanager.api.routers.precedents import (
    APPEND_PRECEDENT_SETTING_COMMAND_TYPE,
    DEPENDENCIES,
    SET_VECTOR_PAUSED_COMMAND_TYPE,
    build_precedent_routes,
)
from auditmanager.api.schemas import models
from auditmanager.api.security import (
    OPERATION_ROLES,
    ROLE_ADMIN,
    ROLE_EXPERT,
    ROLE_VIEWER,
    RUNNER_OPERATIONS,
    RunnerIdentity,
    Subject,
    current_runner,
    current_subject,
)

TASK = "ext_01M2545JSD15ETSNNV904X991K"
RUN = "run_01M2545JSD15ETSNNV904X991K"
FINDING = "fnd_01M2545JSD15ETSNNV904X991K"
USER = "usr_01M2545JSD15ETSNNV904X991K"
KEY = {"Idempotency-Key": "precedents-seal-key"}

#: operationId -> (method, path, json body, headers, the class name the sleeping body refuses with). Written here, not read from the contract.
ROUTES: dict[str, tuple[str, str, Any, dict[str, str], str]] = {
    "getExecutorTaskContext": ("POST", f"/runner/tasks/{TASK}/context", {"kind": "similar_cases"}, {}, "executor_task_context"),
    "getRunPrecedents": ("GET", f"/runs/{RUN}/precedents", None, {}, "precedents"),
    "getFindingPrecedents": ("GET", f"/findings/{FINDING}/precedents", None, {}, "precedents"),
    "getVectorControl": ("GET", "/vector-control", None, {}, "vector_control"),
    "setVectorPaused": ("PUT", "/vector-control/paused", {"paused": True}, KEY, "vector_control"),
    "listPrecedentSettings": ("GET", "/precedent-settings", None, {}, "precedent_settings"),
    "appendPrecedentSetting": ("POST", "/precedent-settings", {"setting_name": "one_list", "value": {"enabled": True}}, KEY,
                               "precedent_settings"),
}

#: The register's answer for the six user routes, as literals: an expert and an administrator read, the administrator alone writes. The viewer
#: («Наблюдатель», `R-150w`) is in none of them: the labels and the cases quote the experts' words and other clients' documents.
EXPECTED_ROLES = {
    "getRunPrecedents": frozenset({ROLE_EXPERT, ROLE_ADMIN}),
    "getFindingPrecedents": frozenset({ROLE_EXPERT, ROLE_ADMIN}),
    "getVectorControl": frozenset({ROLE_EXPERT, ROLE_ADMIN}),
    "setVectorPaused": frozenset({ROLE_ADMIN}),
    "listPrecedentSettings": frozenset({ROLE_ADMIN}),
    "appendPrecedentSetting": frozenset({ROLE_ADMIN}),
}


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    install_exception_handlers(app)
    router = APIRouter()
    build_precedent_routes(router)
    app.include_router(router)
    app.dependency_overrides[current_subject] = lambda: Subject(user_uid=USER, login="a@suite.invalid", token_epoch=1, display_label="A")
    app.dependency_overrides[current_runner] = lambda: RunnerIdentity(token_id="ert_01M2545JSD15ETSNNV904X991K", connection_id=None,
                                                                      host_id="exh_01M2545JSD15ETSNNV904X991K")
    return TestClient(app, raise_server_exceptions=False)


def _call(client: TestClient, operation: str, *, path: str | None = None, body: Any = ..., headers: dict[str, str] | None = None) -> Any:
    method, route, payload, default_headers, _ = ROUTES[operation]
    return client.request(method, path or route, json=payload if body is ... else body, headers=default_headers if headers is None else headers)


# -- asleep, loudly ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("operation", sorted(ROUTES))
def test_every_sleeping_body_refuses_with_dependency_unavailable_and_names_its_lane(client: TestClient, operation: str) -> None:
    answer = _call(client, operation)
    assert answer.status_code == 503, answer.text
    body = answer.json()
    assert body["error_code"] == "dependency_unavailable" and body["retryable"] is True, body
    assert body["details"] == {"dependency": ROUTES[operation][4]}, body
    assert ROUTES[operation][4] in DEPENDENCIES


def test_the_four_lane_names_are_the_ones_the_routes_use() -> None:
    assert {route[4] for route in ROUTES.values()} == set(DEPENDENCIES)
    assert DEPENDENCIES == {"executor_task_context": "executor_task_context", "precedents": "precedents",
                            "vector_control": "vector_control", "precedent_settings": "precedent_settings"}


def test_a_sleeping_route_is_still_a_closed_one(client: TestClient) -> None:
    # a malformed identity in the path is not a resource (404, by design: the API is no oracle for which identities exist)
    for operation, path in (("getExecutorTaskContext", "/runner/tasks/task-1/context"), ("getRunPrecedents", "/runs/run-1/precedents"),
                            ("getFindingPrecedents", "/findings/F-014/precedents")):
        assert _call(client, operation, path=path).status_code == 404, operation
    # a keyed write without its key is refused before anything else
    for operation in ("setVectorPaused", "appendPrecedentSetting"):
        answer = _call(client, operation, headers={})
        assert answer.status_code == 422 and answer.json()["error_code"] == "validation_failed", (operation, answer.text)
    # a body that is not the declared one: an unknown kind, an unknown setting, a member nobody declared, a pause that is not a boolean (pydantic reads «yes» as true, as it does everywhere)
    for operation, body in (("getExecutorTaskContext", {"kind": "norm_excerpts"}), ("getExecutorTaskContext", {"kind": "patterns", "x": 1}),
                            ("getExecutorTaskContext", {}),
                            ("appendPrecedentSetting", {"setting_name": "ar_v3", "value": {}}),
                            ("appendPrecedentSetting", {"setting_name": "one_list", "value": [1]}),
                            ("setVectorPaused", {"paused": "maybe"}), ("setVectorPaused", {})):
        answer = _call(client, operation, body=body)
        assert answer.status_code == 422, (operation, body, answer.text)


# -- who may call what ------------------------------------------------------------------------------------------------


def test_the_register_holds_exactly_the_six_user_routes_with_these_roles() -> None:
    assert {name: OPERATION_ROLES[name] for name in EXPECTED_ROLES} == EXPECTED_ROLES
    assert all(ROLE_VIEWER not in roles for roles in EXPECTED_ROLES.values())
    assert not (set(OPERATION_ROLES) & {"getExecutorTaskContext"})


def test_the_context_is_a_runner_operation_and_has_no_role() -> None:
    assert "getExecutorTaskContext" in RUNNER_OPERATIONS
    assert "getExecutorTaskContext" not in OPERATION_ROLES
    assert not (set(EXPECTED_ROLES) & RUNNER_OPERATIONS)


def test_the_two_command_types_are_the_ones_the_keyed_writes_will_record() -> None:
    assert APPEND_PRECEDENT_SETTING_COMMAND_TYPE == "append_precedent_setting"
    assert SET_VECTOR_PAUSED_COMMAND_TYPE == "set_vector_paused"


# -- the served document ------------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    return create_documentation_app().openapi()


def _operations(document: dict[str, Any]) -> dict[str, tuple[str, str, dict[str, Any]]]:
    return {op["operationId"]: (method.upper(), path, op) for path, item in document["paths"].items() for method, op in item.items()
            if isinstance(op, dict) and "operationId" in op}


def test_the_document_declares_the_seven_operations_where_the_plan_says(document: dict[str, Any]) -> None:
    operations = _operations(document)
    for name, (method, path, _body, _headers, _lane) in ROUTES.items():
        declared = operations[name]
        # the declared path is the template of the one called
        assert declared[0] == method, name
    assert operations["getExecutorTaskContext"][1] == "/runner/tasks/{task_id}/context"
    assert operations["getRunPrecedents"][1] == "/runs/{run_id}/precedents"
    assert operations["getFindingPrecedents"][1] == "/findings/{finding_uid}/precedents"
    assert operations["getVectorControl"][1] == "/vector-control"
    assert operations["setVectorPaused"][1] == "/vector-control/paused"
    assert {operations["listPrecedentSettings"][1], operations["appendPrecedentSetting"][1]} == {"/precedent-settings"}


def test_the_user_routes_declare_the_refusal_of_a_role_and_the_runner_route_does_not(document: dict[str, Any]) -> None:
    operations = _operations(document)
    for name in EXPECTED_ROLES:
        assert "403" in operations[name][2]["responses"], name
    runner = operations["getExecutorTaskContext"][2]["responses"]
    assert "403" not in runner and {"200", "401", "404", "409", "422", "500", "503"} <= set(runner)
    for name in ("setVectorPaused", "appendPrecedentSetting"):
        keyed = [p for p in operations[name][2]["parameters"] if p["name"] == "Idempotency-Key"]
        assert keyed and keyed[0]["required"] is True, name


def test_the_surface_is_additive_evidence_and_the_rail_are_untouched(document: dict[str, Any]) -> None:
    schemas = document["components"]["schemas"]
    # `Evidence` keeps the members it had; a block is proved in a list of its own
    assert set(schemas["Evidence"]["properties"]) == {"evidence_ordinal", "page_number", "quote", "char_start", "char_end", "block_id"}
    assert set(schemas["Evidence"]["required"]) == {"evidence_ordinal", "page_number", "quote", "char_start", "char_end"}
    # the rail is not widened (plan-v5 section 3.2): the eight chips of the text and extended analysis are first and in this order, and the
    # Precedents programme adds no chip of its own (the AR v3 chip, the ninth until the removal wave takes it, is that wave's)
    chips = schemas["RunStageChip"]["enum"]
    assert chips[:8] == ["preparation", "text", "blocks", "cross_check", "merge", "norms", "review", "correction"], chips
    assert not [chip for chip in chips if "precedent" in chip or "vector" in chip], chips
    # the members this seal adds are optional everywhere they are added
    for name, member in (("Finding", "block_evidence"), ("Finding", "origin"), ("FindingDetail", "block_evidence"),
                         ("FindingDetail", "origin"), ("FindingObservation", "grounding_kind"), ("ClaimedExecutorTask", "context_request"),
                         ("SubmitExecutorTaskAnswerRequest", "context_sha256")):
        assert member in schemas[name]["properties"], (name, member)
        assert member not in schemas[name].get("required", []), (name, member)


# -- the schemas --------------------------------------------------------------------------------------------------------


def test_the_vocabularies_are_the_plans() -> None:
    assert [item.value for item in models.PrecedentLabelCode] == ["none", "few", "often_rejected", "cancel_suggested", "likely_accepted", "mixed"]
    # AR v3 is being removed (R-154): its hints P2 and P3 are not built
    assert [item.value for item in models.PrecedentHintCode] == ["p1", "p4", "p5"]
    assert [item.value for item in models.ExecutorTaskContextKind] == ["similar_cases", "patterns"]
    assert [item.value for item in models.PrecedentSettingName] == [
        "one_list", "critic_context", "section_labels", "stop_words", "vector_window", "thresholds"]
    assert [item.value for item in models.VectorWindowState] == ["closed", "draining", "encoding", "skipped"]
    assert [item.value for item in models.FindingGroundingKind] == ["text_span", "portal_block"]
    assert [item.value for item in models.FindingOrigin] == ["text", "drawing", "cross_check"]
    assert "vector_window" in {item.value for item in models.RunWaitCause}
    assert {"drawing_discrepancy", "cross_source"} <= {item.value for item in models.FindingCategory}


def _label(**over: Any) -> dict[str, Any]:
    return {"finding_uid": FINDING, "label": "often_rejected", "critic_reviewed": True,
            "votes": {"total": 8, "rejected": 7, "accepted": 1, "independent": 6, "projects": 3}, "hint_codes": ["p1"], "revision": 1, **over}


def test_a_label_carries_at_most_two_hints_and_none_of_ar_v3() -> None:
    assert models.PrecedentFindingLabel.model_validate(_label()).hint_codes == [models.PrecedentHintCode.P1]
    assert models.PrecedentFindingLabel.model_validate(_label(hint_codes=["p1", "p5"]))
    for bad in (["p1", "p4", "p5"], ["p2"], ["p3"], ["P1"]):
        with pytest.raises(ValueError):
            models.PrecedentFindingLabel.model_validate(_label(hint_codes=bad))
    with pytest.raises(ValueError):
        models.PrecedentFindingLabel.model_validate(_label(label="unknown"))
    with pytest.raises(ValueError):
        models.PrecedentFindingLabel.model_validate({**_label(), "text": "a model's words"})   # closed: no text in a label


def test_the_context_answer_is_laid_out_by_input_and_says_why_it_has_nothing() -> None:
    case = {"case_id": "dmc_01M2545JSD15ETSNNV904X991K", "verdict": "rejected", "category": "dimensions", "similarity": 0.91,
            "finding_text": "text", "recommendation_text": "advice"}
    available = {"kind": "similar_cases", "status": "available", "items": [{"input_id": "c1", "cases": [case]}], "not_fitted": 0,
                 "context_sha256": "a" * 64}
    assert models.ExecutorTaskContext.model_validate(available).items[0].cases[0].similarity == 0.91
    asleep = {"kind": "similar_cases", "status": "unavailable", "reason": "until_move", "items": [], "not_fitted": 0}
    assert models.ExecutorTaskContext.model_validate(asleep).reason == "until_move"
    for bad in ({**available, "items": [{"input_id": "c1", "cases": [case] * 4}]},            # at most three cases per input
                {**available, "context_sha256": "A" * 64}, {**asleep, "reason": "Until Move"},
                {**available, "items": [{"input_id": "", "cases": []}]}, {**available, "not_fitted": -1}):
        with pytest.raises(ValueError):
            models.ExecutorTaskContext.model_validate(bad)


def test_a_claimed_task_may_carry_a_context_request_and_the_answer_may_echo_the_digest() -> None:
    request = {"input_id": "c1", "text_sha256": "b" * 64, "section": "AR"}
    assert models.ExecutorContextInput.model_validate(request).section == "AR"
    with pytest.raises(ValueError):
        models.ExecutorContextInput.model_validate({**request, "text_sha256": "short"})
    answer = models.SubmitExecutorTaskAnswerRequest.model_validate({"output_text": "{}", "model": "m", "context_sha256": "c" * 64})
    assert answer.context_sha256 == "c" * 64
    assert models.SubmitExecutorTaskAnswerRequest.model_validate({"output_text": "{}", "model": "m"}).context_sha256 is None


def test_block_evidence_is_a_place_in_a_normalised_box() -> None:
    evidence = {"ordinal": 0, "page_number": 1, "portal_block_id": "blk_" + "d" * 32,
                "bbox_norm": {"x0": 0.1, "y0": 0.1, "x1": 0.5, "y1": 0.5}, "crop_sha256": "e" * 64}
    assert models.FindingBlockEvidence.model_validate(evidence).recognised_quote is None
    for bad in ({**evidence, "portal_block_id": "b_000001"}, {**evidence, "bbox_norm": {"x0": 0, "y0": 0, "x1": 2, "y1": 1}},
                {**evidence, "page_number": 0}):
        with pytest.raises(ValueError):
            models.FindingBlockEvidence.model_validate(bad)


def test_the_precedent_models_stay_out_of_the_document_dump_when_unset() -> None:
    # an optional member left out is absent on the wire, never null (`exclude_unset` is how every route renders its model)
    run = models.RunPrecedents(run_id=RUN, available=False, items=[])
    assert json.loads(run.model_dump_json(exclude_unset=True)) == {"run_id": RUN, "available": False, "items": []}
