"""``restartRun`` (contract 1.59.0, `RUN-RESTART-01`) over the served seam, through the adapter the application ships.

The command is lane L1's and is wired (``runs.commands.restart_run``; its behaviour is ``tests/integration/runs/test_restart_command.py``). What is
asserted here is the seam: the operation is behind the seam's registers (an expert reaches it, an account that is neither expert nor administrator does not),
a body that is not the contract's is refused before the port, and the shipped adapter reaches the command -- an unknown run is ``404 not_found`` for each of
the eight chips and writes nothing, not even the idempotency key. (The L0 stub answered ``503 dependency_unavailable`` here until L1 replaced it.)
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from w13_api_driver import Answer, Request, Surface, dispatch

from auditmanager.api.routers import Router
from auditmanager.api.routers.execution import build_execution_routes
from auditmanager.bootstrap.adapters import ExecutionAdapter

RUN = "run_01M2545JSD15ETSNNV904X991K"
POINTS = ("preparation", "text", "blocks", "cross_check", "merge", "norms", "review", "correction")


class _Runs:
    """The run adapter's configuration seam the command reads (nothing of it is reached for an unknown run)."""

    section_profiles = None
    cost_preflight = None
    require_cost_consent = False
    stage_plans = None

    def current_configuration(self) -> tuple[str, str, str]:
        return "analysis-profile", "prompt-bundle", "recorded"

    def submit_existing(self, run_id: str) -> None:  # pragma: no cover - an unknown run is refused before a run exists
        raise AssertionError(run_id)


@pytest.fixture
def restart_surface(shipped_router: Surface, session_factory: sessionmaker[Session]) -> Surface:
    router = Router(credentials=shipped_router.router.credentials)
    build_execution_routes(router, ExecutionAdapter(session_factory, runs=_Runs()))  # type: ignore[arg-type]
    return Surface(router)


def _restart(surface: Surface, body: Any, *, key: str | None = "restart-wire-0001", run: str = RUN) -> Answer:
    headers = {"Content-Type": "application/json", **({"Idempotency-Key": key} if key is not None else {})}
    return dispatch(surface, Request.build("POST", f"/runs/{run}/restart", headers=headers, body=json.dumps(body).encode()))


def _error(answer: Answer) -> dict[str, Any]:
    return json.loads(answer.body)


@pytest.mark.parametrize("point", POINTS)
def test_an_expert_reaches_the_command_for_each_chip_and_an_unknown_run_writes_nothing(
    restart_surface: Surface, session: Session, point: str,
) -> None:
    before = session.execute(text("SELECT count(*) FROM command_record")).scalar_one()
    answer = _restart(restart_surface, {"restart_point": point})
    assert answer.status == 404, answer.body
    assert _error(answer)["error_code"] == "not_found"
    assert session.execute(text("SELECT count(*) FROM command_record")).scalar_one() == before, "a refused restart leaves no command record"
    assert session.execute(text("SELECT count(*) FROM audit_run WHERE restart_point IS NOT NULL")).scalar_one() == 0


@pytest.mark.parametrize("body", [{}, {"restart_point": "critic"}, {"restart_point": "text_analysis"}, {"restart_point": "review", "extra": 1}])
def test_a_body_that_is_not_the_contracts_is_refused_before_the_port(restart_surface: Surface, body: dict[str, Any]) -> None:
    answer = _restart(restart_surface, body)
    assert answer.status == 422, answer.body
    assert _error(answer)["error_code"] == "validation_failed"


def test_a_restart_without_its_idempotency_key_is_refused(restart_surface: Surface) -> None:
    answer = _restart(restart_surface, {"restart_point": "review"}, key=None)
    assert answer.status == 422 and _error(answer)["error_code"] == "validation_failed"


def test_a_malformed_run_identity_addresses_nothing(restart_surface: Surface) -> None:
    answer = _restart(restart_surface, {"restart_point": "review"}, run="run_not-an-identity")
    assert answer.status == 404 and _error(answer)["error_code"] == "not_found"


def test_the_operation_is_in_the_served_document_with_its_202_and_its_refusals(restart_surface: Surface) -> None:
    from auditmanager.api.app import create_documentation_app

    operation = create_documentation_app().openapi()["paths"]["/runs/{run_id}/restart"]["post"]
    assert operation["operationId"] == "restartRun"
    assert set(operation["responses"]) == {"202", "401", "403", "404", "409", "422", "500", "503"}
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/RestartRunRequest"}
