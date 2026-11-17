"""`restartRun` (contract 1.59.0, `RUN-RESTART-01`): the route, its body, its refusals and the bodies of the two new views, end to end over a minimal application.

No database and no network. The execution routes are mounted alone on a bare ``FastAPI`` application with the subject the seam would publish and a
stand-in :class:`~auditmanager.api.routers.ports.ExecutionPort`; what is under test is the chain *body model -> port call -> typed refusal -> envelope*
and *view -> wire body -> frozen model*. Lane L1 replaces the port's refusing stub with the command; nothing here depends on it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from auditmanager.api.routers.execution import build_execution_routes
from auditmanager.api.routers.handlers import install_exception_handlers
from auditmanager.api.routers.runs import build_run_routes
from auditmanager.api.routers.stage_models import build_stage_model_routes
from auditmanager.api.schemas import models
from auditmanager.api.schemas.decisions import DecisionCarriedFromView, decision_carried_from_body
from auditmanager.api.schemas.runs import RunStatusView, run_status_body
from auditmanager.api.security import OPERATION_ROLES, Subject, current_subject
from auditmanager.bootstrap.adapters import ExecutionAdapter
from auditmanager.shared.errors import DomainError, ErrorCode

ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
SOURCE = f"run_{ULID}"
NEW = "run_01ARZ3NDEKTSV4RRFFQ69G5FAW"
USER = "usr_01M2545JSD15ETSNNV904X991K"
POINTS = ["preparation", "text", "blocks", "cross_check", "merge", "norms", "review", "correction"]
KEY = {"Idempotency-Key": "restart-key-0001"}
_AT = datetime(2026, 11, 17, 9, 30, tzinfo=timezone.utc)
CONSENT = {"estimate_digest": "a" * 64, "ceiling_micros": 1_500_000, "confirmed": True}


def _view(**overrides: Any) -> RunStatusView:
    fields: dict[str, Any] = dict(
        run_id=NEW, project_uid="prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", version_uid="ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", state="queued",
        provider_mode="live", created_at=_AT, started_from_run_id=SOURCE, restart_point="review",
    )
    fields.update(overrides)
    return RunStatusView(**fields)


class Port:
    """A stand-in execution port: records the call, then answers the view or raises the refusal it was given."""

    def __init__(self, answer: RunStatusView | DomainError) -> None:
        self.answer = answer
        self.calls: list[dict[str, Any]] = []

    def restart_run(self, **call: Any) -> RunStatusView:
        self.calls.append(call)
        if isinstance(self.answer, DomainError):
            raise self.answer
        return self.answer


def _client(port: Any) -> TestClient:
    app = FastAPI()
    install_exception_handlers(app)
    router = APIRouter()
    build_execution_routes(router, port)
    app.include_router(router)
    app.dependency_overrides[current_subject] = lambda: Subject(user_uid=USER, login="u@suite.invalid", token_epoch=1, display_label="U")
    return TestClient(app, raise_server_exceptions=False)


def _post(client: TestClient, body: Any, *, headers: dict[str, str] | None = None, run: str = SOURCE) -> Any:
    return client.post(f"/runs/{run}/restart", content=json.dumps(body), headers={"Content-Type": "application/json", **(KEY if headers is None else headers)})


# -- the route ----------------------------------------------------------------------------------


def test_the_register_lets_an_expert_and_an_administrator_restart_and_nobody_else() -> None:
    assert OPERATION_ROLES["restartRun"] == frozenset({"expert", "admin"})
    assert OPERATION_ROLES["restartRun"] == OPERATION_ROLES["reauditRun"] == OPERATION_ROLES["startRunFromStage"]


@pytest.mark.parametrize("point", POINTS)
def test_each_of_the_eight_chips_is_accepted_and_reaches_the_port_as_a_word(point: str) -> None:
    port = Port(_view(restart_point=point))
    answer = _post(_client(port), {"restart_point": point})
    assert answer.status_code == 202, answer.text
    assert port.calls == [{"run_id": SOURCE, "restart_point": point, "user_uid": USER, "idempotency_key": "restart-key-0001"}]
    body = json.loads(answer.content)
    models.RunStatus.model_validate(body)
    assert (body["run_id"], body["started_from_run_id"], body["restart_point"]) == (NEW, SOURCE, point)
    assert "start_stage_id" not in body and "replaced_by_run_id" not in body


def test_the_consent_reaches_the_port_only_when_it_is_sent() -> None:
    port = Port(_view())
    assert _post(_client(port), {"restart_point": "norms", "cost_consent": CONSENT}).status_code == 202
    assert port.calls[0]["cost_consent"] == CONSENT
    port = Port(_view())
    assert _post(_client(port), {"restart_point": "norms"}).status_code == 202
    assert "cost_consent" not in port.calls[0]


@pytest.mark.parametrize("body", [
    {}, {"restart_point": "Review"}, {"restart_point": "comprehensive_analysis"}, {"restart_point": "text_analysis"}, {"restart_point": ""},
    {"restart_point": None}, {"restart_point": "review", "stage_id": "text_analysis"}, {"restart_point": "review", "cost_consent": {"confirmed": True}},
    {"restart_point": ["review"]},
], ids=["empty", "capital", "procedure-word", "stage-id", "blank", "null", "extra-field", "bad-consent", "list"])
def test_a_body_that_is_not_the_contracts_is_refused_and_nothing_reaches_the_port(body: dict[str, Any]) -> None:
    port = Port(_view())
    answer = _post(_client(port), body)
    assert answer.status_code == 422, answer.text
    assert json.loads(answer.content)["error_code"] == "validation_failed"
    assert port.calls == []


def test_a_restart_needs_its_idempotency_key() -> None:
    port = Port(_view())
    answer = _post(_client(port), {"restart_point": "review"}, headers={})
    assert answer.status_code == 422 and json.loads(answer.content)["error_code"] == "validation_failed"
    assert port.calls == []


def test_a_run_identity_that_is_not_one_is_not_found_before_the_port() -> None:
    """The identity rule of the surface: a malformed identity in a path addresses nothing (`404 not_found`), as for every run operation."""
    port = Port(_view())
    answer = _post(_client(port), {"restart_point": "review"}, run="run_not-an-identity")
    assert answer.status_code == 404 and json.loads(answer.content)["error_code"] == "not_found", answer.text
    assert port.calls == []


# -- the refusals ---------------------------------------------------------------------------------


@pytest.mark.parametrize(("refusal", "status", "code", "details"), [
    (DomainError(ErrorCode.STATE_TRANSITION_NOT_ALLOWED, machine="audit_run", current_state="published", requested_state="restart"),
     409, "state_transition_not_allowed", {"machine": "audit_run", "current_state": "published", "requested_state": "restart"}),
    (DomainError(ErrorCode.CONFLICT, aggregate_type="AuditRun", conflict_reason="restart_in_progress"),
     409, "conflict", {"aggregate_type": "AuditRun", "conflict_reason": "restart_in_progress"}),
    (DomainError(ErrorCode.CONFLICT, aggregate_type="AuditRun", conflict_reason="restart_source_deleted"),
     409, "conflict", {"aggregate_type": "AuditRun", "conflict_reason": "restart_source_deleted"}),
    (DomainError(ErrorCode.CONFLICT, aggregate_type="AuditRun", conflict_reason="restart_source_leased"),
     409, "conflict", {"aggregate_type": "AuditRun", "conflict_reason": "restart_source_leased"}),
    (DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="norm_verification", restart_point="norms", reason="restart_request_changed"),
     422, "analysis_input_invalid", {"stage_id": "norm_verification", "restart_point": "norms", "reason": "restart_request_changed"}),
    (DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, reason="restart_settings_differ"),
     422, "analysis_input_invalid", {"reason": "restart_settings_differ"}),
    (DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun"), 404, "not_found", {"aggregate_type": "AuditRun"}),
])
def test_a_typed_refusal_reaches_the_caller_with_its_details_and_the_restart_point_is_a_safe_key(
    refusal: DomainError, status: int, code: str, details: dict[str, str],
) -> None:
    answer = _post(_client(Port(refusal)), {"restart_point": "review"})
    assert answer.status_code == status, answer.text
    body = json.loads(answer.content)
    assert body["error_code"] == code
    assert body["details"] == details, "a detail the catalog does not declare safe would be screened out"


def test_restart_point_is_a_declared_safe_key_of_analysis_input_invalid_and_of_no_other_code_by_this_change() -> None:
    assert ErrorCode.ANALYSIS_INPUT_INVALID.safe_detail_keys == frozenset({"stage_id", "reason", "restart_point"})
    assert "restart_point" not in ErrorCode.CONFLICT.safe_detail_keys | ErrorCode.STATE_TRANSITION_NOT_ALLOWED.safe_detail_keys


def test_the_shipped_adapter_no_longer_answers_the_sealed_stub() -> None:
    """`RUN-RESTART-01` L1: the L0 stub (`503 dependency_unavailable`, the class `run_restart`) is gone from the adapter; ``restart_run`` is the command, and a
    deployment that has no cost preflight refuses it as the other starts do (``analysis_cost_preflight``), never with the stub's class."""
    import inspect

    source = inspect.getsource(ExecutionAdapter.restart_run)
    assert "run_restart" not in source and "restart_run(" in source


# -- the estimate and the readiness -------------------------------------------------------------


class Runs:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def estimate_run_cost(self, **call: Any) -> Any:
        self.calls.append(call)
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="run_restart")


def _runs_client(runs: Any, stage_models: Any = None) -> TestClient:
    app = FastAPI()
    install_exception_handlers(app)
    router = APIRouter()
    build_run_routes(router, runs)
    if stage_models is not None:
        build_stage_model_routes(router, stage_models)
    app.include_router(router)
    app.dependency_overrides[current_subject] = lambda: Subject(user_uid=USER, login="u@suite.invalid", token_epoch=1, display_label="U")
    return TestClient(app, raise_server_exceptions=False)


def test_the_estimate_passes_the_restart_point_only_when_it_is_named_and_a_word_not_an_enum_member() -> None:
    runs = Runs()
    version = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    _runs_client(runs).post("/runs/cost-estimate", json={"version_uid": version, "start_from_run_id": SOURCE, "restart_point": "blocks"})
    _runs_client(runs).post("/runs/cost-estimate", json={"version_uid": version, "start_from_run_id": SOURCE, "start_stage_id": "text_analysis"})
    assert runs.calls[0]["restart_point"] == "blocks" and runs.calls[0]["start_from_run_id"] == SOURCE
    assert "restart_point" not in runs.calls[1], "a start from a stage is called exactly as before"
    bad = _runs_client(runs).post("/runs/cost-estimate", json={"version_uid": version, "start_from_run_id": SOURCE, "restart_point": "critic"})
    assert bad.status_code == 422 and len(runs.calls) == 2


def test_the_readiness_takes_the_estimate_body_and_refuses_a_restart_point_instead_of_dropping_it() -> None:
    class StageModels:
        def get_start_readiness(self, *, body: Any) -> Any:  # pragma: no cover - must not be reached
            raise AssertionError("the readiness priced a whole run for a restart request")

    answer = _runs_client(Runs(), StageModels()).post(
        "/runs/start-readiness", json={"version_uid": "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", "start_from_run_id": SOURCE, "restart_point": "norms"})
    assert answer.status_code == 422, answer.text
    body = json.loads(answer.content)
    assert body["error_code"] == "validation_failed"
    assert body["details"].get("field") == "restart_point" and body["details"].get("constraint") == "not_for_readiness"


# -- the bodies of the new views ----------------------------------------------------------------


def test_a_restart_run_names_its_source_and_its_chip_and_no_start_stage() -> None:
    body = run_status_body(_view(restart_point="cross_check"))
    assert (body["started_from_run_id"], body["restart_point"]) == (SOURCE, "cross_check")
    assert "start_stage_id" not in body and "replaced_by_run_id" not in body
    models.RunStatus.model_validate(body)


def test_a_start_from_a_stage_is_rendered_as_it_was_and_a_run_that_reuses_nothing_has_none_of_the_three() -> None:
    body = run_status_body(_view(restart_point=None, start_stage_id="text_analysis"))
    assert (body["started_from_run_id"], body["start_stage_id"]) == (SOURCE, "text_analysis") and "restart_point" not in body
    plain = run_status_body(_view(started_from_run_id=None, restart_point=None))
    assert not {"started_from_run_id", "start_stage_id", "restart_point", "replaced_by_run_id"} & set(plain)
    # A source with no mode is not a link: only a source with a start stage or a restart point is rendered (the database holds the pair).
    assert "started_from_run_id" not in run_status_body(_view(restart_point=None))


def test_a_replaced_source_names_the_run_that_replaced_it_and_nothing_else_about_the_restart() -> None:
    body = run_status_body(_view(run_id=SOURCE, started_from_run_id=None, restart_point=None, state="partial", replaced_by_run_id=NEW))
    assert body["replaced_by_run_id"] == NEW
    assert not {"started_from_run_id", "start_stage_id", "restart_point"} & set(body)
    models.RunStatus.model_validate(body)


def test_the_carried_origin_renders_the_run_and_the_mode_only_when_it_has_them() -> None:
    origin = dict(decision_id=f"dec_{ULID}", finding_uid=f"fnd_{ULID}", version_uid=f"ver_{ULID}", version_ordinal=1)
    plain = decision_carried_from_body(DecisionCarriedFromView(**origin))
    assert plain == origin, "a decision carried before 1.59.0 reads as it did"
    restart = decision_carried_from_body(DecisionCarriedFromView(**origin, run_id=SOURCE, mode="restart"))
    assert restart == {**origin, "run_id": SOURCE, "mode": "restart"}
    models.DecisionCarriedFrom.model_validate(restart)
    for mode in ("version", "stage", "restart"):
        models.DecisionCarriedFrom.model_validate({**origin, "mode": mode})
    with pytest.raises(ValueError):
        models.DecisionCarriedFrom.model_validate({**origin, "mode": "automatic"})
    with pytest.raises(ValueError):
        models.DecisionCarriedFrom.model_validate({**origin, "run_id": "run_x"})


def test_the_estimate_models_carry_the_restart_fields_and_a_restart_may_make_no_call() -> None:
    request = models.RunCostEstimateRequest.model_validate(
        {"version_uid": "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", "start_from_run_id": SOURCE, "restart_point": "correction"})
    assert request.restart_point is models.RestartPoint.CORRECTION
    schema = models.RunCostEstimate.model_json_schema()["properties"]
    assert schema["calls"]["minimum"] == 0
    assert {"restart_point", "reused_restart_points", "computed_restart_points"} <= set(schema)
