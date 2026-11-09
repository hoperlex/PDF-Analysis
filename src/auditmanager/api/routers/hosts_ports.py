"""The ports of the host and stage-layout operations of contract 1.45.0 (`HOSTS-SEAL-1`, ADR-0028).

They live beside ``ports.py`` and not in it: ``ports.py`` is the integrator's hotspot for the wave, and a Protocol needs no place in a shared
file to be a seam. The wave-1 lanes implement them -- ``HOSTS-BACKEND-01`` the servers, ``HOSTS-LAYOUT-01`` the layout, the catalogue and
the readiness of a start -- and the integrator wires an implementation into ``build_router(executor_hosts=..., stage_models=...)`` in the
composition root. Until then the shipped stubs (``bootstrap/hosts_adapter.py``, ``bootstrap/stage_plan_adapter.py``) answer every call with a
typed ``503 dependency_unavailable``; nothing is read, written or sent to a model.

Every method takes what the route parsed and returns the contract's model; a rule -- a role beyond the register, a transition, a lock, an
availability -- is the implementation's, never the route's.
"""

from __future__ import annotations

from typing import Protocol

from auditmanager.api.schemas import models

__all__ = ["ExecutorHostPort", "StageModelPort"]


class ExecutorHostPort(Protocol):
    """The servers: reads for ``expert`` and ``admin`` (the viewer sees none), writes and the details for ``admin``. The two keyed
    creations (``issue_enrollment`` and ``create_agent_install``) make the host and its grant or install session together."""

    def list_hosts(self) -> models.ExecutorHostList: ...

    def get_host(self, *, host_id: str) -> models.ExecutorHost: ...

    def get_host_details(self, *, host_id: str) -> models.ExecutorHostDetails: ...

    def set_enabled(
        self, *, host_id: str, body: models.SetExecutorHostEnabledRequest, user_uid: str, idempotency_key: str
    ) -> models.ExecutorHost: ...

    def set_slots(
        self, *, host_id: str, body: models.SetExecutorHostSlotsRequest, user_uid: str, idempotency_key: str
    ) -> models.ExecutorHost: ...

    def archive_host(self, *, host_id: str, user_uid: str, idempotency_key: str) -> models.ExecutorHost: ...

    def issue_enrollment(
        self, *, body: models.IssueExecutorHostEnrollmentRequest, user_uid: str, idempotency_key: str
    ) -> models.IssuedExecutorEnrollment: ...

    def create_agent_install(
        self, *, body: models.CreateExecutorHostAgentInstallRequest, user_uid: str, idempotency_key: str
    ) -> models.ExecutorAgentInstall: ...

    def get_agent_install(self, *, host_id: str, install_id: str) -> models.ExecutorAgentInstall: ...

    def confirm_agent_install_host_key(
        self, *, host_id: str, install_id: str, body: models.ConfirmExecutorAgentInstallHostKeyRequest,
        user_uid: str, idempotency_key: str,
    ) -> models.ExecutorAgentInstall: ...


class StageModelPort(Protocol):
    """The layout of models over the analysis stages, the catalogue it chooses from and the readiness of a start: reads for
    ``expert`` and ``admin`` (the viewer sees none), the two writes for ``admin``."""

    def get_layout(self) -> models.StageModelLayout: ...

    def revise_layout(
        self, *, body: models.ReviseStageModelLayoutRequest, user_uid: str, idempotency_key: str
    ) -> models.StageModelLayout: ...

    def set_layout_enabled(
        self, *, body: models.SetStageModelLayoutEnabledRequest, user_uid: str, idempotency_key: str
    ) -> models.StageModelLayout: ...

    def list_catalogue(self) -> models.ModelCatalogue: ...

    def get_start_readiness(self, *, body: models.RunCostEstimateRequest) -> models.RunStartReadiness: ...
