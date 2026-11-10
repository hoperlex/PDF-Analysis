"""The adapter of ``ExecutorHostPort`` (`HOSTS-SEAL-1`, ADR-0028): the router's seam to ``HostsService``.

It delegates every call to :class:`~auditmanager.bootstrap.hosts_service.HostsService`, which `HOSTS-BACKEND-01` filled. The integrator wires it with
``build_router(executor_hosts=ExecutorHostAdapter(sessions, ring=<public ring>, public_origin=<configured origin>))`` in the composition root; the
adapter is complete (every method of the port). A service that returns a different shape than the contract's model gets a ``ValidationError``
from ``model_validate`` -- loudly, not a silent coercion.

Beyond the port it carries the two calls the **host token** makes (``redeem_host_enrollment`` and ``report_host_health``), which the integrator's
``ExecutorEnrollmentAdapter`` calls when the identity it is handed names a host, not a connection.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.schemas import models
from auditmanager.bootstrap.hosts_service import HostsService

__all__ = ["ExecutorHostAdapter"]


class ExecutorHostAdapter:
    def __init__(
        self, session_factory: sessionmaker[Session], *, service: HostsService | None = None, ring: Any = None,
        public_origin: str | None = None,
    ) -> None:
        self._service = service or HostsService(session_factory=session_factory, ring=ring, public_origin=public_origin)

    # -- the host token's calls (not on the port: the router reaches them through the enrollment and runner ports) ------------

    def redeem_host_enrollment(self, *, enrollment: Any, runner_instance_id: str) -> models.IssuedRunnerToken:
        """The exchange of a host grant for the host token (``redeemExecutorEnrollment``): the token, the host and the catalogue."""
        return models.IssuedRunnerToken.model_validate(
            self._service.redeem_host_enrollment(enrollment=enrollment, runner_instance_id=runner_instance_id))

    def report_host_health(self, *, runner: Any, body: models.ReportRunnerHealthRequest) -> models.RunnerHealthAck:
        """``reportRunnerHealth`` of a host token. ``body`` is converted to plain JSON values (enumerations as their words, instants as text)."""
        return models.RunnerHealthAck.model_validate(
            self._service.report_health(runner=runner, body=body.model_dump(mode="json", exclude_unset=True)))

    def list_hosts(self) -> models.ExecutorHostList:
        return models.ExecutorHostList.model_validate(self._service.list_hosts())

    def get_host(self, *, host_id: str) -> models.ExecutorHost:
        return models.ExecutorHost.model_validate(self._service.get_host(host_id=host_id))

    def get_host_details(self, *, host_id: str) -> models.ExecutorHostDetails:
        return models.ExecutorHostDetails.model_validate(self._service.get_host_details(host_id=host_id))

    def set_enabled(
        self, *, host_id: str, body: models.SetExecutorHostEnabledRequest, user_uid: str, idempotency_key: str
    ) -> models.ExecutorHost:
        return models.ExecutorHost.model_validate(self._service.set_enabled(
            host_id=host_id, enabled=body.enabled, user_uid=user_uid, idempotency_key=idempotency_key))

    def set_slots(
        self, *, host_id: str, body: models.SetExecutorHostSlotsRequest, user_uid: str, idempotency_key: str
    ) -> models.ExecutorHost:
        return models.ExecutorHost.model_validate(self._service.set_slots(
            host_id=host_id, slots=body.slots.model_dump(exclude_unset=True), user_uid=user_uid, idempotency_key=idempotency_key))

    def archive_host(self, *, host_id: str, user_uid: str, idempotency_key: str) -> models.ExecutorHost:
        return models.ExecutorHost.model_validate(self._service.archive_host(
            host_id=host_id, user_uid=user_uid, idempotency_key=idempotency_key))

    def issue_enrollment(
        self, *, body: models.IssueExecutorHostEnrollmentRequest, user_uid: str, idempotency_key: str
    ) -> models.IssuedExecutorEnrollment:
        return models.IssuedExecutorEnrollment.model_validate(self._service.issue_enrollment(
            display_name=body.display_name, user_uid=user_uid, idempotency_key=idempotency_key))

    def create_agent_install(
        self, *, body: models.CreateExecutorHostAgentInstallRequest, user_uid: str, idempotency_key: str
    ) -> models.ExecutorAgentInstall:
        return models.ExecutorAgentInstall.model_validate(self._service.create_agent_install(
            body=body, user_uid=user_uid, idempotency_key=idempotency_key))

    def get_agent_install(self, *, host_id: str, install_id: str) -> models.ExecutorAgentInstall:
        return models.ExecutorAgentInstall.model_validate(self._service.get_agent_install(host_id=host_id, install_id=install_id))

    def confirm_agent_install_host_key(
        self, *, host_id: str, install_id: str, body: models.ConfirmExecutorAgentInstallHostKeyRequest,
        user_uid: str, idempotency_key: str,
    ) -> models.ExecutorAgentInstall:
        return models.ExecutorAgentInstall.model_validate(self._service.confirm_agent_install_host_key(
            host_id=host_id, install_id=install_id, host_key_fingerprint=body.host_key_fingerprint,
            user_uid=user_uid, idempotency_key=idempotency_key))
