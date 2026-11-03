"""`EXEC2-GROUP-RUN-01`: a start or an estimate that names an executor group is handed to the port, not refused.

Until this task, `EXEC2-GROUP-STORE-01` refused ``executor_group_id`` at the router (``503 dependency_unavailable``,
``executor_group_dispatch``) because nothing served the field and reading it as absent would have started the run on the
default route. The Run port now admits the run on the group (``tests/unit/runs/test_group_admission_unit.py`` holds the
rules), so the router's only job is to pass the field on:

* a request that names a group reaches the port, with ``executor_group_id`` and nothing else changed;
* a request that names none reaches it **without** the keyword, so a port that predates the field is called exactly as
  before (the same rule ``reaudit_of_run_id`` follows);
* the router makes no decision of its own about exclusivity, the routing mode or the provider source: those refusals are
  the port's, before the idempotency key is claimed.

The handlers are taken from the router and called as functions: no application, no database. Written and **not run** in
EXEC-2 (`R-149d`).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable

import pytest
from fastapi import APIRouter

from auditmanager.api.routers.runs import build_run_routes
from auditmanager.api.schemas import models

VERSION = "ver_01M2545JSD15ETSNNV904X991J"
GROUP = "exg_01M2545JSD15ETSNNV904X991K"
CONNECTION = "exc_01M2545JSD15ETSNNV904X991K"
PRESET = "evt_01M2545JSD15ETSNNV904X991K"
SUBJECT = SimpleNamespace(user_uid="usr_01M2545JSD15ETSNNV904X991K")


class Reached(Exception):
    """Raised by the stand-in port: the router got as far as the port."""


class RecordingRuns:
    """A ``RunPort`` that records the keywords of the call and stops there."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def estimate_run_cost(self, **kwargs: Any) -> Any:
        self.calls.append(("estimate_run_cost", kwargs))
        raise Reached

    def start_run(self, **kwargs: Any) -> Any:
        self.calls.append(("start_run", kwargs))
        raise Reached


def handlers() -> tuple[RecordingRuns, dict[str, Callable[..., Any]]]:
    runs = RecordingRuns()
    router = APIRouter()
    build_run_routes(router, runs)  # type: ignore[arg-type]
    return runs, {route.operation_id: route.endpoint for route in router.routes}  # type: ignore[attr-defined]


def start(endpoint: Callable[..., Any], **body: Any) -> Any:
    request = models.StartRunRequest.model_validate({"version_uid": VERSION, **body})
    return endpoint(body=request, idempotency_key="key-1", subject=SUBJECT)


def estimate(endpoint: Callable[..., Any], **body: Any) -> Any:
    request = models.RunCostEstimateRequest.model_validate({"version_uid": VERSION, **body})
    return endpoint(body=request)


def test_both_operations_are_declared_and_take_the_field() -> None:
    _, endpoints = handlers()
    assert {"startRun", "estimateRunCost"} <= set(endpoints)
    for model in (models.StartRunRequest, models.RunCostEstimateRequest):
        assert "executor_group_id" in model.model_fields


def test_a_start_that_names_a_group_reaches_the_port_with_the_group() -> None:
    runs, endpoints = handlers()
    with pytest.raises(Reached):
        start(endpoints["startRun"], executor_group_id=GROUP)
    ((name, kwargs),) = runs.calls
    assert name == "start_run" and kwargs["executor_group_id"] == GROUP
    assert kwargs["executor_connection_id"] is None and kwargs["preset_id"] is None


def test_an_estimate_that_names_a_group_reaches_the_port_with_the_group() -> None:
    runs, endpoints = handlers()
    with pytest.raises(Reached):
        estimate(endpoints["estimateRunCost"], executor_group_id=GROUP)
    ((name, kwargs),) = runs.calls
    assert name == "estimate_run_cost" and kwargs["executor_group_id"] == GROUP


def test_the_router_does_not_judge_exclusivity_that_is_the_ports_refusal() -> None:
    """A group together with a connection or a preset is handed to the port as it came: the refusal
    (``conflicts_with_executor_connection_id`` / ``conflicts_with_preset_id``) is raised there, before the key is claimed."""
    runs, endpoints = handlers()
    for extra in ({"executor_connection_id": CONNECTION}, {"preset_id": PRESET}):
        with pytest.raises(Reached):
            start(endpoints["startRun"], executor_group_id=GROUP, **extra)
    assert [kwargs["executor_group_id"] for _, kwargs in runs.calls] == [GROUP, GROUP]


def test_a_request_that_names_no_group_calls_the_port_without_the_keyword() -> None:
    """The control: a port written before the field is called exactly as it always was."""
    runs, endpoints = handlers()
    with pytest.raises(Reached):
        start(endpoints["startRun"])
    with pytest.raises(Reached):
        start(endpoints["startRun"], executor_connection_id=CONNECTION)
    with pytest.raises(Reached):
        estimate(endpoints["estimateRunCost"])
    assert [name for name, _ in runs.calls] == ["start_run", "start_run", "estimate_run_cost"]
    assert all("executor_group_id" not in kwargs for _, kwargs in runs.calls)
