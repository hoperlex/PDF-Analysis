"""`CTX-STAND`: the route of ``getExecutorTaskContext`` at the edge, with a stand-in port (no database).

What is under test is the edge, the way ``test_runner_seam.py`` tests the runner's four: a runner token is a principal of its own that reaches the
operation and nothing else does; the body is the contract's (``kind`` is one of two words and nothing more); the port sees the runner's identity, the
task and the kind; an answer is written with its optional members absent, never null; and the refusals of the port (404, 409) are the envelope's.

The route is **moved**, not added: the seal declared it asleep in ``api/routers/precedents.py`` and ``build_task_context_route`` declares it again beside
the runner's other operations. ``test_the_declaration_is_the_seals_word_for_word`` is what says the contract's document did not move with it.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from auditmanager.api.app import create_documentation_app
from auditmanager.api.routers import build_router
from auditmanager.api.routers.runner import build_runner_routes, build_task_context_route
from auditmanager.api.schemas import models
from auditmanager.api.security import RUNNER_OPERATIONS, RunnerIdentity
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.executors.conftest import driver
from tests.integration.executors.test_runner_seam import TASK, TOKEN, StubRunner

Request, dispatch = driver.Request, driver.dispatch
PATH = f"/runner/tasks/{TASK}/context"
OPERATION = "getExecutorTaskContext"
SHA = "c" * 64


class StubContext:
    """The port: records what reached it and answers what it was told to (a ``DomainError`` is raised, a mapping is validated)."""

    def __init__(self, answer: Any = None) -> None:
        self.calls: list[tuple[RunnerIdentity, str, str]] = []
        self.answer = answer if answer is not None else {"kind": "similar_cases", "status": "unavailable", "reason": "until_move", "items": [],
                                                         "not_fitted": 0}

    def get_task_context(self, *, runner: RunnerIdentity, task_id: str, kind: str) -> models.ExecutorTaskContext:
        self.calls.append((runner, task_id, kind))
        if isinstance(self.answer, BaseException):
            raise self.answer
        return models.ExecutorTaskContext.model_validate({**self.answer, "kind": kind})


def surface_of(port: StubContext | None, *, moved: bool = True) -> Any:
    """The tree's router; with ``moved`` the seal's sleeping route is taken out and ``build_task_context_route`` declares the operation in its place (what
    the composition root does when it wires the lane), with ``port`` behind it or, for ``None``, nothing."""
    router = build_router(
        projects=None, documents=None, runs=None, findings=None, decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=driver.SuiteCredentialAdapter(roles=frozenset({"admin"})), accounts=driver.SuiteAccountAdapter(),
        registrations=driver.SuiteRegistrationAdapter(), runner=StubRunner())  # type: ignore[arg-type]
    if moved:
        router.routes[:] = [route for route in router.routes if getattr(route, "operation_id", None) != OPERATION]
        build_task_context_route(router, port)
    return driver.Surface(router)


def post(surface: Any, body: Any = None, *, token: str | None = TOKEN, path: str = PATH) -> Any:
    headers = {"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token is not None else {})}
    return dispatch(surface, Request.build("POST", path, headers=headers, body=json.dumps({"kind": "similar_cases"} if body is None else body).encode()),
                    credential=None)


def test_the_operation_is_a_runner_operation_with_no_role() -> None:
    assert OPERATION in RUNNER_OPERATIONS


def test_a_runner_token_reaches_the_port_with_its_identity_the_task_and_the_kind() -> None:
    port = StubContext()
    answer = post(surface_of(port), {"kind": "patterns"})
    assert answer.status == 200 and answer.header("X-Correlation-Id"), answer.body
    assert port.calls == [(RunnerIdentity("ern_T", "exc_C"), TASK, "patterns")]
    assert answer.json() == {"kind": "patterns", "status": "unavailable", "reason": "until_move", "items": [], "not_fitted": 0}


def test_the_optional_members_are_absent_never_null() -> None:
    delivered = {"kind": "similar_cases", "status": "available", "items": [{"input_id": "xri_1", "cases": []}], "not_fitted": 2, "context_sha256": SHA}
    body = post(surface_of(StubContext(delivered))).json()
    assert body == delivered and "reason" not in body
    unavailable = post(surface_of(StubContext())).json()
    assert "context_sha256" not in unavailable and unavailable["reason"] == "until_move"


@pytest.mark.parametrize("token", ["amr_zzzzzzzz_" + "B" * 43, "garbage", None])
def test_a_wrong_token_and_no_token_are_authentication_required_and_reach_no_port(token: str | None) -> None:
    port = StubContext()
    answer = post(surface_of(port), token=token)
    assert answer.status == 401 and answer.json()["error_code"] == "authentication_required" and port.calls == []


def test_a_users_credential_is_not_a_runner_token() -> None:
    port = StubContext()
    answer = dispatch(surface_of(port), Request.build("POST", PATH, headers={"Content-Type": "application/json"}, body=b'{"kind": "similar_cases"}'))
    assert answer.status == 401 and answer.json()["error_code"] == "authentication_required" and port.calls == []


@pytest.mark.parametrize("body", [{}, {"kind": "norm_excerpts"}, {"kind": "norm_crops"}, {"kind": "similar_cases", "x": 1}, {"kind": 1}, {"kind": None}, []])
def test_a_body_that_is_not_the_contracts_is_a_validation_failure_and_reaches_no_port(body: Any) -> None:
    port = StubContext()
    answer = post(surface_of(port), body)
    assert answer.status == 422 and answer.json()["error_code"] == "validation_failed" and port.calls == []


def test_a_malformed_task_identity_is_refused_before_the_port() -> None:
    port = StubContext()
    answer = post(surface_of(port), path="/runner/tasks/not-a-task/context")
    assert answer.status in (404, 422) and port.calls == []


def test_the_ports_refusals_are_the_envelopes() -> None:
    not_found = post(surface_of(StubContext(DomainError(ErrorCode.NOT_FOUND, aggregate_type="ExecutorTask"))))
    assert not_found.status == 404 and not_found.json()["error_code"] == "not_found"
    conflict = post(surface_of(StubContext(DomainError(ErrorCode.CONFLICT, message="the claim on the task is lost", conflict_reason="claim_lost"))))
    assert conflict.status == 409 and conflict.json()["details"]["conflict_reason"] == "claim_lost"


def test_the_moved_route_without_a_port_sleeps_exactly_as_the_seal_did() -> None:
    surface = surface_of(None)
    answer = post(surface)
    assert answer.status == 503 and answer.json()["error_code"] == "dependency_unavailable"
    assert answer.json()["details"]["dependency"] == "executor_task_context"
    assert [route.operation_id for route in surface.routes].count(OPERATION) == 1


def test_this_tree_is_dormant_the_seals_route_is_all_it_declares_and_it_still_sleeps() -> None:
    """Nothing calls ``build_task_context_route`` here: the runner's own builder does not declare the operation, and the router as built is the seal's."""
    from fastapi import APIRouter

    runners = APIRouter()
    build_runner_routes(runners, StubRunner())  # type: ignore[arg-type]
    assert OPERATION not in [route.operation_id for route in runners.routes]
    sealed = surface_of(None, moved=False)
    answer = post(sealed)
    assert answer.status == 503 and answer.json()["details"]["dependency"] == "executor_task_context"
    assert [route.operation_id for route in sealed.routes].count(OPERATION) == 1


def test_the_declaration_is_the_seals_word_for_word() -> None:
    """Moving the route from ``precedents.py`` to ``runner.py`` leaves the served document unchanged: the operation's whole path item is equal."""
    sealed = create_documentation_app().openapi()
    path = next(item for item in sealed["paths"] if item.endswith("/runner/tasks/{task_id}/context"))
    for port in (StubContext(), None):
        moved = surface_of(port).app.openapi()
        assert sealed["paths"][path] == moved["paths"][path], "served or sleeping, the operation's declaration is the same"
        assert sorted(sealed["paths"]) == sorted(moved["paths"]), "no operation was added or lost by the move"
