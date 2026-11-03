"""`EXEC2-GROUP-STORE-01`: until `EXEC2-GROUP-RUN-01`, a start or an estimate that names an executor group is refused.

Contract 1.16.0 gave ``startRun`` and ``estimateRunCost`` an optional ``executor_group_id``. Nothing serves it yet, and
the one wrong thing to do with a field nobody serves is to read it as absent: the run would start on the default route
(or the estimate would be of it) with the caller believing a group had been used. So the router refuses the request,
before any work, with ``503 dependency_unavailable`` and ``details.dependency`` ``executor_group_dispatch``:

* the port is never reached -- no estimate, no command record, no run, no event;
* the refusal does not depend on the other fields (a connection, a preset, a consent, a raised limit);
* a request that does not name a group still reaches the port, so the refusal is the field's and not the route's.

The handlers are taken from the router and called as functions: no application, no database. The same refusal through the
served application is in ``tests/integration/executors/test_groups.py``. Written and **not run** in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable

import pytest
from fastapi import APIRouter

from auditmanager.api.routers.runs import build_run_routes
from auditmanager.api.schemas import models
from auditmanager.shared.errors import DomainError, ErrorCode

VERSION = "ver_01M2545JSD15ETSNNV904X991J"
GROUP = "exg_01M2545JSD15ETSNNV904X991K"
CONNECTION = "exc_01M2545JSD15ETSNNV904X991K"
PRESET = "evt_01M2545JSD15ETSNNV904X991K"
SUBJECT = SimpleNamespace(user_uid="usr_01M2545JSD15ETSNNV904X991K")


class Reached(Exception):
    """Raised by the stand-in port: the router got as far as the port."""


class RecordingRuns:
    """A ``RunPort`` that records the call and stops there."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def estimate_run_cost(self, **kwargs: Any) -> Any:
        self.calls.append("estimate_run_cost")
        raise Reached

    def start_run(self, **kwargs: Any) -> Any:
        self.calls.append("start_run")
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


def refused(call: Callable[[], Any]) -> DomainError:
    with pytest.raises(DomainError) as error:
        call()
    return error.value


def test_both_operations_are_declared_and_take_the_field() -> None:
    _, endpoints = handlers()
    assert {"startRun", "estimateRunCost"} <= set(endpoints)
    for model in (models.StartRunRequest, models.RunCostEstimateRequest):
        assert "executor_group_id" in model.model_fields, "the field this refusal is about"


def test_a_start_that_names_a_group_is_refused_before_the_port_is_reached() -> None:
    runs, endpoints = handlers()
    error = refused(lambda: start(endpoints["startRun"], executor_group_id=GROUP))
    assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert dict(error.detail_fields) == {"dependency": "executor_group_dispatch"}
    assert runs.calls == [], "no estimate, no command record, no run, no event"


def test_an_estimate_that_names_a_group_is_refused_before_the_port_is_reached() -> None:
    runs, endpoints = handlers()
    error = refused(lambda: estimate(endpoints["estimateRunCost"], executor_group_id=GROUP))
    assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert dict(error.detail_fields) == {"dependency": "executor_group_dispatch"}
    assert runs.calls == []


def test_the_refusal_does_not_depend_on_what_else_the_request_carries() -> None:
    runs, endpoints = handlers()
    consent = {"estimate_digest": "a" * 64, "ceiling_micros": 1_000_000, "confirmed": True}
    for extra in (
        {"relaxed_limits": True},
        {"cost_consent": consent},
        {"executor_connection_id": CONNECTION},   # exclusive with a group: the field is still not read as absent
        {"preset_id": PRESET},
    ):
        error = refused(lambda: start(endpoints["startRun"], executor_group_id=GROUP, **extra))
        assert dict(error.detail_fields) == {"dependency": "executor_group_dispatch"}, extra
    assert runs.calls == []


def test_the_refusal_carries_no_value_of_the_request() -> None:
    _, endpoints = handlers()
    error = refused(lambda: start(endpoints["startRun"], executor_group_id=GROUP))
    assert GROUP not in repr(error.detail_fields) and GROUP not in str(error)


def test_a_request_that_names_no_group_still_reaches_the_port() -> None:
    """The control: the refusal is the field's, and the port is what the other requests meet."""
    runs, endpoints = handlers()
    with pytest.raises(Reached):
        start(endpoints["startRun"])
    with pytest.raises(Reached):
        start(endpoints["startRun"], executor_connection_id=CONNECTION)
    with pytest.raises(Reached):
        estimate(endpoints["estimateRunCost"])
    assert runs.calls == ["start_run", "start_run", "estimate_run_cost"]
