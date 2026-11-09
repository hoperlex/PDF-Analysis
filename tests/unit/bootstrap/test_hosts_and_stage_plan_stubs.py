"""`HOSTS-SEAL-1`: the stubs the wave-1 lanes replace refuse, every one, with a typed ``503 dependency_unavailable``.

No database, no network: nothing is read, written or sent to a model. A stub that answered with an empty body would be a silent fallback
(AGENTS section 4); a stub that raised ``NotImplementedError`` would be an untyped 500. Each module names the dependency it stands for.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from auditmanager.api.routers.hosts_ports import ExecutorHostPort, StageModelPort
from auditmanager.api.schemas import models
from auditmanager.bootstrap import hosts_dispatch, stage_plan_providers
from auditmanager.bootstrap.hosts_adapter import ExecutorHostAdapter
from auditmanager.bootstrap.stage_plan_adapter import StageModelAdapter
from auditmanager.shared.errors import DomainError, ErrorCode

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


def _refusal(call: Any) -> DomainError:
    with pytest.raises(DomainError) as refused:
        call()
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    return refused.value


@pytest.mark.parametrize(("method", "kwargs"), HOST_CALLS, ids=[name for name, _ in HOST_CALLS])
def test_every_server_call_of_the_shipped_adapter_refuses_naming_executor_hosts(method: str, kwargs: dict[str, Any]) -> None:
    adapter = ExecutorHostAdapter(None)  # type: ignore[arg-type]
    assert _refusal(lambda: getattr(adapter, method)(**kwargs)).detail_fields["dependency"] == "executor_hosts"


@pytest.mark.parametrize(("method", "kwargs"), STAGE_CALLS, ids=[name for name, _ in STAGE_CALLS])
def test_every_layout_call_of_the_shipped_adapter_refuses_naming_stage_models(method: str, kwargs: dict[str, Any]) -> None:
    adapter = StageModelAdapter(None)  # type: ignore[arg-type]
    assert _refusal(lambda: getattr(adapter, method)(**kwargs)).detail_fields["dependency"] == "stage_models"


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


@pytest.mark.parametrize(("call", "dependency"), [
    (lambda: hosts_dispatch.bind_planned_run(None, run_id="run_x"), "executor_host_dispatch"),  # type: ignore[arg-type]
    (lambda: hosts_dispatch.claim_for_host_token(None, token_id="ern_x", runner_instance_id=None, wait_seconds=0), "executor_host_dispatch"),  # type: ignore[arg-type]
    (lambda: stage_plan_providers.StagePlanProviders().binding_for(None, run_id="run_x", cell_key="text:main"), "stage_plan_providers"),  # type: ignore[arg-type]
])
def test_the_seams_of_dispatch_and_providers_refuse_the_same_way(call: Any, dependency: str) -> None:
    assert _refusal(call).detail_fields["dependency"] == dependency
