"""`getRunStages` (contract 1.46.0): the route, its adapter and the viewer's reading, end to end over a minimal application.

No database and no network. The route is mounted alone on a bare ``FastAPI`` application with the subject the seam would publish; the
adapter is the shipped :class:`~auditmanager.bootstrap.run_stage_adapter.RunStageAdapter` with the role set and the read patched in, so
what is under test is the chain *role set -> include_server -> assemble -> contract model -> wire bytes*: for the viewer the bytes carry neither
``server`` nor ``access``, for an expert and an administrator both, and an account with no role fails closed to the viewer's answer.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from auditmanager.api.routers.handlers import install_exception_handlers
from auditmanager.api.routers.hosts_ports import RunStagePort
from auditmanager.api.routers.run_stages import build_run_stage_routes
from auditmanager.api.schemas import models
from auditmanager.api.security import OPERATION_ROLES, Subject, current_subject
from auditmanager.bootstrap import run_stage_adapter as adapter_module
from auditmanager.bootstrap.run_stage_adapter import RunStageAdapter
from auditmanager.runs import stage_facts as sf
from auditmanager.shared.errors import DomainError, ErrorCode

RUN = "run_01M2545JSD15ETSNNV904X991K"
USER = "usr_01M2545JSD15ETSNNV904X991K"
PLAN = {"cells": [{"cell_key": "text:main", "model_id": "claude-sonnet-5-5", "effort": "medium",
                   "access": "subscription"}]}


class _Sessions:
    def __call__(self) -> "_Sessions":
        return self

    def __enter__(self) -> "_Sessions":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None


def _wire(monkeypatch: pytest.MonkeyPatch, roles: frozenset[str], seen: list[bool]) -> TestClient:
    class Accounts:
        def roles_of(self, session: Any, user_uid: str) -> frozenset[str]:
            assert user_uid == USER
            return roles

    def read(sessions: Any, blob_store: Any, *, run_id: str, include_server: bool) -> dict[str, Any]:
        seen.append(include_server)
        if run_id != RUN:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
        return sf.assemble_run_stage_facts(
            run=sf.RunRow(RUN, "running", PLAN, None),
            stage_rows=[sf.StageRow("text_analysis", "succeeded")],
            calls=[], review=None, cell_bindings={"text:main": sf.CellBinding("adm1.hlab.kz", "subscription")} if include_server else {},
            include_server=include_server,
        )

    monkeypatch.setattr(adapter_module, "AccountRepository", Accounts)
    monkeypatch.setattr(adapter_module, "read_run_stage_facts", read)
    port: RunStagePort = RunStageAdapter(_Sessions(), blob_store=None)  # type: ignore[arg-type]
    app = FastAPI()
    install_exception_handlers(app)
    router = APIRouter()
    build_run_stage_routes(router, port)
    app.include_router(router)
    app.dependency_overrides[current_subject] = lambda: Subject(user_uid=USER, login="u@suite.invalid", token_epoch=1, display_label="U")
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(("roles", "sees_server"), [
    (frozenset({"expert"}), True), (frozenset({"admin"}), True), (frozenset({"expert", "admin"}), True),
    (frozenset({"viewer"}), False), (frozenset(), False),
], ids=["expert", "admin", "both", "viewer", "no-role"])
def test_only_an_expert_or_an_administrator_is_told_the_server_and_the_access(
    monkeypatch: pytest.MonkeyPatch, roles: frozenset[str], sees_server: bool
) -> None:
    seen: list[bool] = []
    answer = _wire(monkeypatch, roles, seen).get(f"/runs/{RUN}/stages")
    assert answer.status_code == 200, answer.text
    assert seen == [sees_server]
    body = json.loads(answer.content)
    models.RunStages.model_validate(body)
    cell = body["items"][0]["plan"][0]
    assert cell["model_id"] == "claude-sonnet-5-5" and cell["effort"] == "medium"  # the viewer still reads the model and the settings
    assert ("server" in cell, "access" in cell) == (sees_server, sees_server), cell
    assert ("server" in answer.text) == sees_server and ("access" in answer.text) == sees_server  # not a null, not anywhere in the bytes


def test_an_unknown_run_is_not_found_and_the_answer_names_no_run(monkeypatch: pytest.MonkeyPatch) -> None:
    answer = _wire(monkeypatch, frozenset({"expert"}), []).get("/runs/run_01M2545JSD15ETSNNV904X991M/stages")
    assert answer.status_code == 404
    assert json.loads(answer.content)["error_code"] == "not_found"


def test_the_examples_of_the_contract_are_valid_answers_and_the_viewers_has_no_server_or_access() -> None:
    schema = models.RunStages.model_json_schema()
    examples = schema["examples"]
    assert len(examples) == 3
    for example in examples:
        models.RunStages.model_validate(example)
    viewer = examples[1]
    assert "server" not in json.dumps(viewer) and "access" not in json.dumps(viewer)
    assert any('"server"' in json.dumps(example) for example in (examples[0], examples[2]))
    assert examples[2]["plan_source"] == "run_binding"


def test_the_port_is_one_method_and_the_adapter_has_it() -> None:
    assert {n for n in dir(RunStagePort) if not n.startswith("_")} == {"get_run_stages"}
    assert callable(RunStageAdapter.get_run_stages)


def test_every_role_that_reads_a_run_reads_its_stages_and_the_viewer_is_among_them() -> None:
    """The register lets the viewer ask; what the viewer is not told is the implementation's (above). The two together are `R-150w`:
    a register that closed the read to the viewer would hide the model and the stages, which the owner ruled the viewer may see."""
    assert OPERATION_ROLES["getRunStages"] == OPERATION_ROLES["getRunStatus"] == frozenset({"expert", "admin", "viewer"})
