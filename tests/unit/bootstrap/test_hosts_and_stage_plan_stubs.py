"""`HOSTS-SEAL-1` shipped the two adapters as stubs that refused with a typed ``503 dependency_unavailable``; `HOSTS-BACKEND-01` and `HOSTS-LAYOUT-01` filled
the services behind them and `HOSTS-INT-WIRE-01` wired them. What this module now holds: **the adapters are the seam and decide nothing** -- every call of
each reaches its service with the request's values, and each adapter carries the whole of its port. (The cases of the services are
`test_stage_plan_service.py`, `test_stage_plan_binding.py` and `tests/unit/executors/test_hosts_*`; the served answers are
`tests/integration/api/test_hosts_stage_models_surface.py`.)

No database, no network: nothing is read, written or sent to a model. An adapter that answered by itself would hide a service nobody wrote.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from auditmanager.api.routers.hosts_ports import ExecutorHostPort, StageModelPort
from auditmanager.api.schemas import models
from auditmanager.bootstrap.hosts_adapter import ExecutorHostAdapter
from auditmanager.bootstrap.stage_plan_adapter import StageModelAdapter

HOST = "exh_01ARZ3NDEKTSV4RRFFQ69G5FAV"
INSTALL = "exai_01ARZ3NDEKTSV4RRFFQ69G5FAV"
USER = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
CELL = {"cell_key": "text:main", "row": "text", "role": "main", "model_id": "claude-sonnet-5-5", "effort": "medium",
        "max_output_tokens": 16000, "timeout_seconds": 600}

HOST_CALLS: list[tuple[str, dict[str, Any]]] = [
    ("list_hosts", {}),
    ("get_host", {"host_id": HOST}),
    ("get_host_details", {"host_id": HOST}),
    ("set_enabled", {"host_id": HOST, "body": models.SetExecutorHostEnabledRequest(enabled=True), "user_uid": USER, "idempotency_key": "k1"}),
    ("set_slots", {"host_id": HOST, "body": models.SetExecutorHostSlotsRequest(slots=models.ExecutorHostSlots(codex=2)),
                   "user_uid": USER, "idempotency_key": "k2"}),
    ("archive_host", {"host_id": HOST, "user_uid": USER, "idempotency_key": "k3"}),
    ("issue_enrollment", {"body": models.IssueExecutorHostEnrollmentRequest(display_name="adm1.hlab.kz"), "user_uid": USER, "idempotency_key": "k4"}),
    ("create_agent_install", {"body": models.CreateExecutorHostAgentInstallRequest(
        display_name="adm1.hlab.kz", access="generated_key", ssh_host="adm1.hlab.kz", ssh_port=22, ssh_user="root"),
        "user_uid": USER, "idempotency_key": "k5"}),
    ("get_agent_install", {"host_id": HOST, "install_id": INSTALL}),
    ("confirm_agent_install_host_key", {"host_id": HOST, "install_id": INSTALL, "body": models.ConfirmExecutorAgentInstallHostKeyRequest(
        host_key_fingerprint="SHA256:" + "A" * 43), "user_uid": USER, "idempotency_key": "k6"}),
]
STAGE_CALLS: list[tuple[str, dict[str, Any]]] = [
    ("get_layout", {}),
    ("revise_layout", {"body": models.ReviseStageModelLayoutRequest(kit="custom", cells=[models.StageLayoutCell(**CELL)]),
                       "user_uid": USER, "idempotency_key": "k7"}),
    ("set_layout_enabled", {"body": models.SetStageModelLayoutEnabledRequest(enabled=True), "user_uid": USER, "idempotency_key": "k8"}),
    ("list_catalogue", {}),
    ("get_start_readiness", {"body": models.RunCostEstimateRequest(version_uid="ver_01ARZ3NDEKTSV4RRFFQ69G5FAV")}),
]


class _Reached(Exception):
    """Raised by the stand-in service: the adapter got as far as the service."""


class _Service:
    """``StagePlanService`` and ``HostsService``: the adapter is their seam and decides nothing, so each call must arrive at them."""

    def __getattr__(self, name: str) -> Any:
        def reached(**kwargs: Any) -> Any:
            raise _Reached(name)

        return reached


@pytest.mark.parametrize(("method", "kwargs"), HOST_CALLS, ids=[name for name, _ in HOST_CALLS])
def test_every_server_call_of_the_adapter_is_the_services(method: str, kwargs: dict[str, Any]) -> None:
    adapter = ExecutorHostAdapter(None, service=_Service())  # type: ignore[arg-type]
    with pytest.raises(_Reached):
        getattr(adapter, method)(**kwargs)


def test_the_host_tokens_two_calls_are_the_services_too() -> None:
    """``redeem_host_enrollment`` and ``report_host_health`` are not on the port: the enrollment adapter calls them for a host token."""
    adapter = ExecutorHostAdapter(None, service=_Service())  # type: ignore[arg-type]
    with pytest.raises(_Reached):
        adapter.redeem_host_enrollment(enrollment=object(), runner_instance_id="agent-instance-0001")
    with pytest.raises(_Reached):
        adapter.report_host_health(runner=object(), body=models.ReportRunnerHealthRequest.model_validate({
            "agent_version": "0.21.0", "clis": [], "concurrency": 1, "execution_profile": "command", "features": []}))


@pytest.mark.parametrize(("method", "kwargs"), STAGE_CALLS, ids=[name for name, _ in STAGE_CALLS])
def test_every_layout_call_of_the_adapter_is_the_services(method: str, kwargs: dict[str, Any]) -> None:
    adapter = StageModelAdapter(None, service=_Service())  # type: ignore[arg-type]
    with pytest.raises(_Reached):
        getattr(adapter, method)(**kwargs)


def test_the_two_adapters_carry_the_whole_of_their_ports() -> None:
    for port, adapter in ((ExecutorHostPort, ExecutorHostAdapter), (StageModelPort, StageModelAdapter)):
        declared = {name for name, member in inspect.getmembers(port, inspect.isfunction) if not name.startswith("_")}
        for name in declared:
            assert callable(getattr(adapter, name, None)), f"{adapter.__name__} lacks {name}"
            ours = set(inspect.signature(getattr(adapter, name)).parameters)
            theirs = set(inspect.signature(getattr(port, name)).parameters)
            assert ours == theirs, (adapter.__name__, name, ours ^ theirs)
    assert {name for name, _ in HOST_CALLS} == {n for n, m in inspect.getmembers(ExecutorHostPort, inspect.isfunction) if not n.startswith("_")}
    assert {name for name, _ in STAGE_CALLS} == {n for n, m in inspect.getmembers(StageModelPort, inspect.isfunction) if not n.startswith("_")}

