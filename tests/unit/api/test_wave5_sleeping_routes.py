"""`CRIT-SEAL-53` (contract 1.54.0): the three operations of the wave-5 seal -- the failure patterns and the quality table -- asleep, with no database.

Mounted alone on a bare ``FastAPI`` application with the principal the authorization seam would publish. What is shown:

* **asleep, loudly**: with no port each answers ``503 dependency_unavailable`` naming its lane (``decision_patterns``, ``stage_quality``);
* **answering through a port**: with a fake port the route parses, calls one method, validates the answer against the contract's own model and renders it
  (an answer that is not the contract's shape is refused, never passed on); a keyed write without its key is ``422``;
* **who may call what** is the register's, written here as literals: an expert and an administrator read and review the patterns, the administrator alone
  reads the quality table, the viewer none;
* the schemas: the closed vocabularies, the closed bodies, the optional members.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from auditmanager.api.app import create_documentation_app
from auditmanager.api.routers.handlers import install_exception_handlers
from auditmanager.api.routers.precedents import REVIEW_DECISION_PATTERN_COMMAND_TYPE, build_precedent_routes
from auditmanager.api.schemas import models
from auditmanager.api.security import OPERATION_ROLES, ROLE_ADMIN, ROLE_EXPERT, ROLE_VIEWER, Subject, current_subject

USER = "usr_01M2545JSD15ETSNNV904X991K"
PATTERN = "dmp_01M2545JSD15ETSNNV904X991K"
KEY = {"Idempotency-Key": "wave5-seal-key"}
CELL = "review:main"

ROUTES: dict[str, tuple[str, str, Any, dict[str, str], str]] = {
    "listDecisionPatterns": ("GET", "/decision-memory/patterns", None, {}, "decision_patterns"),
    "reviewDecisionPattern": ("POST", f"/decision-memory/patterns/{PATTERN}/review", {"decision": "approve"}, KEY, "decision_patterns"),
    "getQualityTable": ("GET", "/quality-table", None, {}, "stage_quality"),
}
EXPECTED_ROLES = {
    "listDecisionPatterns": frozenset({ROLE_EXPERT, ROLE_ADMIN}),
    "reviewDecisionPattern": frozenset({ROLE_EXPERT, ROLE_ADMIN}),
    "getQualityTable": frozenset({ROLE_ADMIN}),
}


def _pattern(**over: Any) -> dict[str, Any]:
    return {"pattern_id": PATTERN, "section_code": "AR", "pattern_text": "Размер указан в другом разделе.", "member_count": 8, "refusal_count": 7,
            "status": "proposed", "status_cause": "proposed", "status_changed_at": "2026-11-11T09:00:00Z", "proposed_at": "2026-11-11T09:00:00Z", **over}


class _Patterns:
    def __init__(self, answer: Mapping[str, Any] | None = None) -> None:
        self.answer = answer
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def list_decision_patterns(self, **kwargs: Any) -> Mapping[str, Any]:
        self.calls.append(("list", kwargs))
        return self.answer if self.answer is not None else {"items": [_pattern()], "total": 1}

    def review_decision_pattern(self, **kwargs: Any) -> Mapping[str, Any]:
        self.calls.append(("review", kwargs))
        return self.answer if self.answer is not None else _pattern(status="approved", status_cause="expert_review")


class _Quality:
    def __init__(self, answer: Mapping[str, Any]) -> None:
        self.answer = answer

    def get_stage_quality(self, **kwargs: Any) -> Mapping[str, Any]:
        return self.answer


def _client(**ports: Any) -> TestClient:
    app = FastAPI()
    install_exception_handlers(app)
    router = APIRouter()
    build_precedent_routes(router, **ports)
    app.include_router(router)
    app.dependency_overrides[current_subject] = lambda: Subject(user_uid=USER, login="a@suite.invalid", token_epoch=1, display_label="A")
    return TestClient(app, raise_server_exceptions=False)


def _call(client: TestClient, operation: str, *, path: str | None = None, body: Any = ..., headers: dict[str, str] | None = None) -> Any:
    method, route, payload, default_headers, _ = ROUTES[operation]
    return client.request(method, path or route, json=payload if body is ... else body, headers=default_headers if headers is None else headers)


@pytest.mark.parametrize("operation", sorted(ROUTES))
def test_every_wave_5_body_is_asleep_without_a_port_and_names_its_lane(operation: str) -> None:
    answer = _call(_client(), operation)
    assert answer.status_code == 503, answer.text
    body = answer.json()
    assert body["error_code"] == "dependency_unavailable" and body["details"] == {"dependency": ROUTES[operation][4]}, body


def test_a_port_answers_and_the_route_passes_what_it_parsed() -> None:
    patterns = _Patterns()
    client = _client(decision_patterns=patterns)
    listed = client.get("/decision-memory/patterns", params={"status": "approved", "section_code": "AR", "limit": 20})
    assert listed.status_code == 200 and listed.json() == {"items": [_pattern()], "total": 1}, listed.text
    assert patterns.calls[0] == ("list", {"status": "approved", "section_code": "AR", "limit": 20, "user_uid": USER})
    client.get("/decision-memory/patterns")
    assert patterns.calls[1][1] == {"status": None, "section_code": None, "limit": 50, "user_uid": USER}
    reviewed = _call(client, "reviewDecisionPattern", body={"decision": "suspend"})
    assert reviewed.status_code == 200 and reviewed.json()["status"] == "approved"
    assert patterns.calls[2] == ("review", {"pattern_id": PATTERN, "decision": "suspend", "user_uid": USER, "idempotency_key": "wave5-seal-key"})


def test_a_route_is_a_closed_one() -> None:
    client = _client(decision_patterns=_Patterns())
    # a malformed identity is not a resource; a missing key, an unknown decision, an unknown member and an out-of-range filter are refused before the port
    assert _call(client, "reviewDecisionPattern", path="/decision-memory/patterns/dmp-1/review").status_code == 404
    assert _call(client, "reviewDecisionPattern", headers={}).status_code == 422
    for body in ({"decision": "delete"}, {"decision": "approve", "surprise": 1}, {}):
        assert _call(client, "reviewDecisionPattern", body=body).status_code == 422, body
    for query in ({"status": "approved-ish"}, {"limit": 0}, {"limit": 201}, {"section_code": "x" * 65}):
        assert client.get("/decision-memory/patterns", params=query).status_code == 422, query
    # an empty filter is the absent one
    assert client.get("/decision-memory/patterns", params={"status": ""}).status_code == 200


def test_an_answer_that_is_not_the_contracts_shape_is_refused_not_passed_on() -> None:
    for bad in ({"items": [_pattern(status="deleted")], "total": 1}, {"items": [_pattern(pattern_text="")], "total": 1},
                {"items": [_pattern(refusal_count=0)], "total": 1}, {"items": [], "total": -1}, {"items": [_pattern()]}):
        answer = _client(decision_patterns=_Patterns(bad)).get("/decision-memory/patterns")
        assert answer.status_code >= 500, (bad, answer.text)


def test_the_quality_table_is_counts_and_leaves_an_unset_member_out() -> None:
    rows = {"rows": [
        {"section_code": "AR", "ensemble": False, "cell_key": CELL, "model_id": "claude-opus-5-5", "decided_count": 9,
         "accepted_count": 7, "rejected_count": 2},
        {"section_code": "AR", "ensemble": True, "decided_count": 4, "accepted_count": 1, "rejected_count": 3},
    ]}
    answer = _client(stage_quality=_Quality(rows)).get("/quality-table")
    assert answer.status_code == 200 and answer.json() == rows, answer.text
    assert "cell_key" not in answer.json()["rows"][1] and "model_id" not in answer.json()["rows"][1]
    assert _client(stage_quality=_Quality({"rows": []})).get("/quality-table").json() == {"rows": []}       # nothing decided: an empty table
    for bad in ({"section_code": "AR", "ensemble": False, "decided_count": 0, "accepted_count": 0, "rejected_count": 0},   # no row without a decision
                {"section_code": "AR", "ensemble": False, "cell_key": "blocks:leg9", "decided_count": 1, "accepted_count": 1, "rejected_count": 0},
                {"section_code": "AR", "ensemble": False, "decided_count": 1, "accepted_count": 1, "rejected_count": 0, "share": 1.0}):
        assert _client(stage_quality=_Quality({"rows": [bad]})).get("/quality-table").status_code >= 500, bad


def test_the_register_holds_exactly_these_roles_and_never_the_viewer() -> None:
    assert {name: OPERATION_ROLES[name] for name in EXPECTED_ROLES} == EXPECTED_ROLES
    assert all(ROLE_VIEWER not in roles for roles in EXPECTED_ROLES.values())


def test_the_command_type_is_the_one_the_review_will_record() -> None:
    assert REVIEW_DECISION_PATTERN_COMMAND_TYPE == "review_decision_pattern"


# -- the schemas and the document -----------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    return create_documentation_app().openapi()


def test_the_document_declares_the_three_operations_and_the_new_members(document: dict[str, Any]) -> None:
    operations = {op["operationId"]: (method.upper(), path, op) for path, item in document["paths"].items() for method, op in item.items()
                  if isinstance(op, dict) and "operationId" in op}
    assert operations["listDecisionPatterns"][:2] == ("GET", "/decision-memory/patterns")
    assert operations["reviewDecisionPattern"][:2] == ("POST", "/decision-memory/patterns/{pattern_id}/review")
    assert operations["getQualityTable"][:2] == ("GET", "/quality-table")
    for name in EXPECTED_ROLES:
        assert "403" in operations[name][2]["responses"], name
    keyed = [p for p in operations["reviewDecisionPattern"][2]["parameters"] if p["name"] == "Idempotency-Key"]
    assert keyed and keyed[0]["required"] is True
    schemas = document["components"]["schemas"]
    for name, member in (("Finding", "cross_evidence"), ("FindingDetail", "cross_evidence"), ("FindingObservation", "extended_observation_ref"),
                         ("RunStatus", "publication_mode")):
        assert member in schemas[name]["properties"] and member not in schemas[name].get("required", []), (name, member)
    # the answer text keeps no bound (the owner removed the answer caps on 2026-11-06; `D-688` was withdrawn from this seal)
    assert "maxLength" not in schemas["SubmitExecutorTaskAnswerRequest"]["properties"]["output_text"]


def test_the_vocabularies_are_the_plans() -> None:
    assert [i.value for i in models.DecisionPatternStatus] == ["proposed", "approved", "rejected", "suspended"]
    assert [i.value for i in models.DecisionPatternStatusCause] == ["proposed", "expert_review", "group_dissolved"]
    assert [i.value for i in models.DecisionPatternReview] == ["approve", "reject", "suspend"]
    assert [i.value for i in models.RunPublicationMode] == ["text_only", "one_list"]
    assert "parameter_mismatch" in {i.value for i in models.FindingCategory}


def test_cross_evidence_names_the_other_version_and_is_a_span_of_its_quote() -> None:
    item = {"evidence_ordinal": 0, "version_uid": "ver_01M2545JSD15ETSNNV904X991K", "page_number": 3, "quote": "Площадь 1200 м2", "char_start": 10, "char_end": 25}
    assert models.FindingCrossEvidence.model_validate(item).version_uid.startswith("ver_")
    for bad in ({**item, "version_uid": "run_01M2545JSD15ETSNNV904X991K"}, {**item, "page_number": 0}, {**item, "quote": ""}, {**item, "surprise": 1}):
        with pytest.raises(ValueError):
            models.FindingCrossEvidence.model_validate(bad)
