"""The universal agent (`EXEC2-ENROLL-01`, ADR-0026 decisions 4 to 9, owner ruling `R-149b`): the enrollment
grant, the exchange for a runner token, the agent's health, the package route, the API side of an install
over SSH and the integration-authorisation mark. Eight operations of contract 1.15.0.

====================================  =========================================================================
``issueExecutorEnrollment``           an administrator; the grant's secret and install command, shown once
``redeemExecutorEnrollment``          an **enrollment secret** (its own principal); a runner token, shown once
``reportRunnerHealth``                a **runner token**; the agent's version, clients and their auth states
``downloadAgentPackage``              **no credential**; the package of exactly one version, by its digest
``createExecutorAgentInstall``        an administrator; path A, the API side
``getExecutorAgentInstall``           an administrator; one install session
``confirmExecutorAgentInstallHostKey``  an administrator; the fingerprint the worker observed, by value
``setExecutorIntegrationAuthorisation`` an administrator; the "authorised for this integration" mark
====================================  =========================================================================

Who may call what is decided by the authorization seam (``api/security.py``): the administrator's five by the
role register, ``redeemExecutorEnrollment`` by :data:`~auditmanager.api.security.ENROLLMENT_OPERATIONS`,
``reportRunnerHealth`` by :data:`~auditmanager.api.security.RUNNER_OPERATIONS` and ``downloadAgentPackage`` by
:data:`~auditmanager.api.security.UNAUTHENTICATED_OPERATIONS`. An enrollment secret reaches the exchange and no
other operation; a runner token does not reach it.

**Where these routes are registered.** ``build_router`` declares them, as it declares every operation, and its
``enrollment`` argument is the port. The port also travels on the ``Router`` (``router.enrollment``), which is
where the authorization seam finds it to authenticate an enrollment secret. A router built with no port still
declares them -- the served document is a function of the declarations -- and answers none.

No route returns a secret except the two that exist to show one once, and none reads a file or a row: the
package route asks the port for the bytes, as the image route asks for a Blob.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Request
from pydantic import WithJsonSchema

from auditmanager.api.routers.auth import OPEN_REQUIREMENT
from auditmanager.api.routers.declarations import (
    STATE_CONFLICT_DESCRIPTION,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import EnrollmentPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentEnrollment, CurrentRunner, CurrentSubject

__all__ = [
    "build_enrollment_routes",
    "requested_origin",
]

_TAGS = ["execution"]

#: ``version`` is declared with the contract's ``AgentPackageVersion`` schema and **not enforced by the
#: framework**, for the reason ``CorrelationIdParam`` is not: a constrained path parameter is a refusable one,
#: and a malformed path identity is ``404`` on this surface. This route's contract is different -- a version
#: the image does not hold, malformed or merely absent, is ``422 package_version_unknown`` and never a
#: listing -- so the shape is checked by the module that owns the directory (``agent_package.load_package``).
AgentPackageVersionParam = Annotated[
    str,
    WithJsonSchema({"$ref": "#/components/schemas/AgentPackageVersion"}),
    Path(),
]

_GZIP = {"application/gzip": {"schema": {"type": "string", "format": "binary"}}}


def requested_origin(request: Request) -> str | None:
    """The origin the administrator's own request arrived on: the forwarded scheme and the ``Host``.

    Unvalidated here; ``agent_package.resolve_origin`` validates it (or prefers the configured one), because it
    ends up inside the command the administrator copies to another host."""
    host = request.headers.get("host", "").strip()
    if not host:
        return None
    scheme = (request.headers.get("x-forwarded-proto") or request.url.scheme).split(",")[0].strip()
    return f"{scheme}://{host}"


def build_enrollment_routes(router: APIRouter, enrollment: EnrollmentPort) -> None:
    # -- the administrator's ------------------------------------------------------------------

    @router.post(
        "/executor-connections/{connection_id}/enrollments",
        operation_id="issueExecutorEnrollment", tags=_TAGS, status_code=201,
        response_model=models.IssuedExecutorEnrollment,
        responses={**success(201, "The grant, shown once. Only a one-way hash of its secret is "
                                  "stored; no operation returns the secret or the command again."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503,
                                        descriptions={409: STATE_CONFLICT_DESCRIPTION})},
    )
    def issue_executor_enrollment(
        request: Request, subject: CurrentSubject,
        connection_id: Annotated[models.ExecutorConnectionId, Path()],
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = enrollment.issue_enrollment(
            connection_id=connection_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key, requested_origin=requested_origin(request),
        )
        return json_response(201, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/executor-connections/{connection_id}/integration-authorisation",
        operation_id="setExecutorIntegrationAuthorisation", tags=_TAGS,
        response_model=models.ExecutorConnection,
        responses={**success(200, "The connection, with the mark as it now stands."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503,
                                        descriptions={409: STATE_CONFLICT_DESCRIPTION})},
    )
    def set_executor_integration_authorisation(
        subject: CurrentSubject, connection_id: Annotated[models.ExecutorConnectionId, Path()],
        body: models.SetExecutorIntegrationAuthorisationRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = enrollment.set_integration_authorisation(
            connection_id=connection_id, authorised=body.authorised, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/executor-connections/{connection_id}/agent-installs",
        operation_id="createExecutorAgentInstall", tags=_TAGS, status_code=201,
        response_model=models.ExecutorAgentInstall,
        responses={**success(201, "The install session, or the recorded outcome of an identical "
                                  "earlier request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503,
                                        descriptions={409: STATE_CONFLICT_DESCRIPTION})},
    )
    def create_executor_agent_install(
        subject: CurrentSubject, connection_id: Annotated[models.ExecutorConnectionId, Path()],
        body: models.CreateExecutorAgentInstallRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = enrollment.create_agent_install(
            connection_id=connection_id, body=body, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(201, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.get(
        "/executor-connections/{connection_id}/agent-installs/{install_id}",
        operation_id="getExecutorAgentInstall", tags=_TAGS,
        response_model=models.ExecutorAgentInstall,
        responses={**success(200, "The install session as it stands."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def get_executor_agent_install(
        connection_id: Annotated[models.ExecutorConnectionId, Path()],
        install_id: Annotated[models.ExecutorAgentInstallId, Path()],
    ) -> WireResponse:
        # The role register (an administrator) has already decided; the read names no actor.
        view = enrollment.get_agent_install(connection_id=connection_id, install_id=install_id)
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/executor-connections/{connection_id}/agent-installs/{install_id}/confirm-host-key",
        operation_id="confirmExecutorAgentInstallHostKey", tags=_TAGS,
        response_model=models.ExecutorAgentInstall,
        responses={**success(200, "The install session after the confirmation, or as it stands "
                                  "for an identical repeat."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503,
                                        descriptions={409: STATE_CONFLICT_DESCRIPTION})},
    )
    def confirm_executor_agent_install_host_key(
        subject: CurrentSubject, connection_id: Annotated[models.ExecutorConnectionId, Path()],
        install_id: Annotated[models.ExecutorAgentInstallId, Path()],
        body: models.ConfirmExecutorAgentInstallHostKeyRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = enrollment.confirm_agent_install_host_key(
            connection_id=connection_id, install_id=install_id,
            host_key_fingerprint=body.host_key_fingerprint, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    # -- the agent's ----------------------------------------------------------------------------

    @router.post(
        "/runner/enroll", operation_id="redeemExecutorEnrollment", tags=_TAGS, status_code=201,
        response_model=models.IssuedRunnerToken,
        responses={**success(201, "A runner token, shown once, bound to the enrollment's "
                                  "connection."),
                   **envelope_responses(401, 409, 422, 500, 503,
                                        descriptions={409: STATE_CONFLICT_DESCRIPTION})},
    )
    def redeem_executor_enrollment(
        identity: CurrentEnrollment, body: models.RedeemExecutorEnrollmentRequest,
    ) -> WireResponse:
        view = enrollment.redeem_enrollment(
            enrollment=identity, runner_instance_id=body.runner_instance_id)
        return json_response(201, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/runner/health", operation_id="reportRunnerHealth", tags=_TAGS,
        response_model=models.RunnerHealthAck,
        responses={**success(200, "The report was stored."),
                   **envelope_responses(401, 422, 500, 503)},
    )
    def report_runner_health(
        identity: CurrentRunner, body: models.ReportRunnerHealthRequest,
    ) -> WireResponse:
        view = enrollment.report_health(runner=identity, body=body)
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.get(
        "/runner/agent-package/{version}", operation_id="downloadAgentPackage", tags=_TAGS,
        status_code=200, response_class=WireResponse,
        openapi_extra=dict(OPEN_REQUIREMENT),
        responses={**success(200, "The package, deterministic for its version.", content=_GZIP),
                   **envelope_responses(422, 500, 503)},
    )
    def download_agent_package(version: AgentPackageVersionParam) -> WireResponse:
        file_name, content = enrollment.read_package(version=version)
        return WireResponse(200, (
            ("Content-Type", "application/gzip"),
            ("Content-Length", str(len(content))),
            ("Content-Disposition", f'attachment; filename="{file_name}"'),
            ("Cache-Control", "no-store"),
        ), content)
