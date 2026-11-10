"""`LIMITS-01` (contract 1.49.0, `R-153n`, `R-153o`): a layout write that still names an answer limit or a timeout is refused, not ignored.

The cells of the layout (the six rows and the four kinds of comparison work) are a model and an effort. The objects of the contract are closed,
so a request that carries `max_output_tokens` or `timeout_seconds` on a cell is `422 validation_failed` before the service sees it: nothing is
silently dropped (`AGENTS.md` section 4: no silent fallback). The route is mounted alone with a port that fails the test if it is reached.
No database and no network.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from auditmanager.api.routers.handlers import install_exception_handlers
from auditmanager.api.routers.stage_models import build_stage_model_routes
from auditmanager.api.security import Subject, current_subject
from auditmanager.runs import stage_layout as layout

USER = "usr_01M2545JSD15ETSNNV904X991K"


class _Port:
    """The layout port: a request that is valid reaches it, a refused one must not."""

    reached = 0

    def revise_layout(self, *, body: Any, user_uid: str, idempotency_key: str) -> Any:
        type(self).reached += 1
        raise AssertionError("a refused write must not reach the service")


def _client() -> TestClient:
    app = FastAPI()
    install_exception_handlers(app)
    router = APIRouter()
    build_stage_model_routes(router, _Port())  # type: ignore[arg-type]
    app.include_router(router)
    app.dependency_overrides[current_subject] = lambda: Subject(user_uid=USER, login="a@suite.invalid", token_epoch=1, display_label="A")
    return TestClient(app, raise_server_exceptions=False)


def _body(*, cell_extra: dict[str, Any] | None = None, comparison_extra: dict[str, Any] | None = None) -> dict[str, Any]:
    cells = layout.cells_to_wire(layout.preset_cells("codex_only"))
    comparison = layout.comparison_cells_to_wire(layout.comparison_preset_cells("codex_only"))
    cells[0] = {**cells[0], **(cell_extra or {})}
    comparison[0] = {**comparison[0], **(comparison_extra or {})}
    return {"kit": "codex_only", "cells": cells, "comparison_cells": comparison}


@pytest.mark.parametrize("member,value", [("max_output_tokens", 16000), ("timeout_seconds", 1800)])
@pytest.mark.parametrize("where", ["cell", "comparison_cell"])
def test_a_cell_that_names_a_limit_or_a_timeout_is_refused_422_and_never_reaches_the_service(where: str, member: str, value: int) -> None:
    body = _body(**({"cell_extra": {member: value}} if where == "cell" else {"comparison_extra": {member: value}}))
    before = _Port.reached
    answer = _client().post("/model-layout/revisions", json=body, headers={"Idempotency-Key": "k-limits-0001"})
    assert answer.status_code == 422, answer.text
    envelope = json.loads(answer.content)
    assert envelope["error_code"] == "validation_failed"
    assert _Port.reached == before


def test_the_same_request_without_the_two_members_is_valid_for_the_route() -> None:
    """The control of the two cases above: with the members gone the request passes validation and reaches the service."""
    before = _Port.reached
    answer = _client().post("/model-layout/revisions", json=_body(), headers={"Idempotency-Key": "k-limits-0002"})
    assert _Port.reached == before + 1, "a valid layout reaches the service (which this port then fails, as a 500)"
    assert answer.status_code == 500
