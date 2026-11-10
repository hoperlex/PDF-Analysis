"""The servers of the executor surface (`HOSTS-SEAL-1`, ADR-0028, contract 1.45.0): ten routes.

====================================================  =====================================================================
``listExecutorHosts``                                 ``expert`` or ``admin``; the servers and the summary line
``getExecutorHost``                                   ``expert`` or ``admin``; one server
``getExecutorHostDetails``                            ``admin``; slots, the reasons a model is unavailable, running tasks
``setExecutorHostEnabled``                            ``admin``, keyed; the «Использовать» switch, journalled
``setExecutorHostSlots``                              ``admin``, keyed; the slots of providers, journalled
``archiveExecutorHost``                               ``admin``, keyed; one-way, not deletion
``issueExecutorHostEnrollment``                       ``admin``, keyed; a new server and its one-time grant (no model)
``createExecutorHostAgentInstall``                    ``admin``, keyed; a new server and an install session over SSH
``getExecutorHostAgentInstall``                       ``admin``; one install session
``confirmExecutorHostAgentInstallHostKey``            ``admin``, keyed; the fingerprint the worker observed, by value
====================================================  =====================================================================

The last four are the host-targeted forms of ``issueExecutorEnrollment``, ``createExecutorAgentInstall``, ``getExecutorAgentInstall`` and
``confirmExecutorAgentInstallHostKey``, which stay as they are for the connection-bound agents (ADR-0026) until the comparison routes move
to the hosts. Who may call what is decided by the authorization seam (``api/security.py``): the viewer («Наблюдатель», `R-150w`) is denied
every one of them, and a router decides nothing about roles.

**Declared, and answerable only with a port.** ``build_router`` declares these routes whatever the port, as it does for every operation: the
served document is a function of the declarations. A router built with no port answers none (``503 dependency_unavailable``).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path
from pydantic import BaseModel

from auditmanager.api.routers.declarations import STATE_CONFLICT_DESCRIPTION, envelope_responses, success
from auditmanager.api.routers.hosts_ports import ExecutorHostPort
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_host_routes"]

_TAGS = ["execution"]

HostIdPath = Annotated[models.ExecutorHostId, Path()]
InstallIdPath = Annotated[models.ExecutorAgentInstallId, Path()]


def _body(view: BaseModel) -> bytes:
    return encode_json(view.model_dump(mode="json", exclude_unset=True))


def build_host_routes(router: APIRouter, hosts: ExecutorHostPort) -> None:
    @router.get(
        "/executor-hosts", operation_id="listExecutorHosts", tags=_TAGS,
        response_model=models.ExecutorHostList,
        responses={**success(200, "The servers, newest first, with the summary line: on line of all, free slots of all. A "
                                  "model that cannot be used is not listed on a server."),
                   **envelope_responses(401, 403, 500, 503)},
        description=(
            "`HOSTS-SEAL-1` (ADR-0028): every server -- one agent process with its host token -- with the «Использовать» switch, whether it is on "
            "line (a report within the last 120 seconds), the models it can serve **now** and its slots, and the summary line of the screen. "
            "A server is a host, not a connection: the connections and groups the stand keeps for it are its own and are never listed. "
            "`role:admin|expert`; the viewer («Наблюдатель») is denied."
        ),
    )
    def list_executor_hosts() -> WireResponse:
        return json_response(200, _body(hosts.list_hosts()))

    @router.get(
        "/executor-hosts/{host_id}", operation_id="getExecutorHost", tags=_TAGS,
        response_model=models.ExecutorHost,
        responses={**success(200, "The server as it stands."), **envelope_responses(401, 403, 404, 422, 500, 503)},
        description="`HOSTS-SEAL-1`: one server, as `listExecutorHosts` lists it. `404 not_found` for an unknown host. `role:admin|expert`.",
    )
    def get_executor_host(host_id: HostIdPath) -> WireResponse:
        return json_response(200, _body(hosts.get_host(host_id=host_id)))

    @router.get(
        "/executor-hosts/{host_id}/details", operation_id="getExecutorHostDetails", tags=_TAGS,
        response_model=models.ExecutorHostDetails,
        responses={**success(200, "The slots, each provider with the reasons its models cannot be used, and the tasks running."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
        description=(
            "`HOSTS-SEAL-1`: «Подробнее» of a server -- its slots and their use, each provider found on it with its login and, for every "
            "model, why it cannot be used (`host_disabled`, `host_offline`, `login_required`, `model_not_verified`, `model_cooling_down`), "
            "and the tasks running on it now (run, stage, since when). Derived at read time. `role:admin`."
        ),
    )
    def get_executor_host_details(host_id: HostIdPath) -> WireResponse:
        return json_response(200, _body(hosts.get_host_details(host_id=host_id)))

    @router.put(
        "/executor-hosts/{host_id}/enabled", operation_id="setExecutorHostEnabled", tags=_TAGS,
        response_model=models.ExecutorHost,
        responses={**success(200, "The server with the switch as it now stands."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503, descriptions={409: STATE_CONFLICT_DESCRIPTION})},
        description=(
            "`HOSTS-SEAL-1`: the «Использовать» switch of a server (`R-149b`: the administrator who connected a server switched it on). "
            "Off, the server takes no new run; runs already bound to it finish. Each change is an append-only event with its author and time; "
            "setting the value already in force answers the server as it stands. `409 conflict` with `conflict_reason` `host_archived`. "
            "`role:admin`, `Idempotency-Key` required."
        ),
    )
    def set_executor_host_enabled(
        subject: CurrentSubject, host_id: HostIdPath, body: models.SetExecutorHostEnabledRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = hosts.set_enabled(host_id=host_id, body=body, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, _body(view))

    @router.put(
        "/executor-hosts/{host_id}/slots", operation_id="setExecutorHostSlots", tags=_TAGS,
        response_model=models.ExecutorHost,
        responses={**success(200, "The server with its slots as they now stand."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503, descriptions={409: STATE_CONFLICT_DESCRIPTION})},
        description=(
            "`HOSTS-SEAL-1`: how many calls of a provider the server may run at once (1 to 16; default 1 for a subscription, 2 for an API "
            "key). A provider the host does not have is `422 validation_failed`. The stand keeps the slots on the host, not on a revision; "
            "each change is an append-only event with its author. `409 conflict` with `conflict_reason` `host_archived`. `role:admin`, "
            "`Idempotency-Key` required."
        ),
    )
    def set_executor_host_slots(
        subject: CurrentSubject, host_id: HostIdPath, body: models.SetExecutorHostSlotsRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = hosts.set_slots(host_id=host_id, body=body, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, _body(view))

    @router.post(
        "/executor-hosts/{host_id}/archive", operation_id="archiveExecutorHost", tags=_TAGS,
        response_model=models.ExecutorHost,
        responses={**success(200, "The archived server; an archived server answers as it stands."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503, descriptions={409: STATE_CONFLICT_DESCRIPTION})},
        description=(
            "`HOSTS-SEAL-1`: «Удалить» a server -- one-way, not deletion (a call names its host by identity for good). The host token is "
            "revoked, the system connections of the host are archived, and runs already bound to it finish as they can. Archiving an "
            "archived server answers it as it stands. `role:admin`, `Idempotency-Key` required."
        ),
    )
    def archive_executor_host(
        subject: CurrentSubject, host_id: HostIdPath, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = hosts.archive_host(host_id=host_id, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, _body(view))

    @router.post(
        "/executor-hosts/enrollments", operation_id="issueExecutorHostEnrollment", tags=_TAGS, status_code=201,
        response_model=models.IssuedExecutorEnrollment,
        responses={**success(201, "The grant, shown once, and the new server it belongs to."),
                   **envelope_responses(401, 403, 409, 422, 500, 503, descriptions={409: STATE_CONFLICT_DESCRIPTION})},
        description=(
            "`HOSTS-SEAL-1` (ADR-0028): connect a server -- create the host and issue the one-time grant of its agent, with no model. "
            "Same document as `issueExecutorEnrollment`: the secret, the package version and digest and the copyable install command are "
            "**shown once**, only a one-way hash is stored; the grant is single-use, expires after 15 minutes and is bound to the new host "
            "(`enrollment.host_id`). Redeeming it (`redeemExecutorEnrollment`) yields a host token. `409 conflict` with `conflict_reason` "
            "`enrollment_shown_once` for a repeat of the same key (the secret was not stored). `422 validation_failed` for a name another "
            "live server has. `503 dependency_unavailable` with dependency `agent_package` or `public_origin`, as `issueExecutorEnrollment`. "
            "`role:admin`, `Idempotency-Key` required."
        ),
    )
    def issue_executor_host_enrollment(
        subject: CurrentSubject, body: models.IssueExecutorHostEnrollmentRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = hosts.issue_enrollment(body=body, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(201, _body(view))

    @router.post(
        "/executor-hosts/agent-installs", operation_id="createExecutorHostAgentInstall", tags=_TAGS, status_code=201,
        response_model=models.ExecutorAgentInstall,
        responses={**success(201, "The install session and the new server it belongs to, or the recorded outcome of an identical "
                                  "earlier request."),
                   **envelope_responses(401, 403, 409, 422, 500, 503, descriptions={409: STATE_CONFLICT_DESCRIPTION})},
        description=(
            "`HOSTS-SEAL-1`: connect a server over SSH (path A) -- create the host and an install session, with no model. As "
            "`createExecutorAgentInstall`: `private_key` is required for `pasted_key` and refused for `generated_key`, sealed to the stand's "
            "public key and never returned; the session carries `host_id`. `role:admin`, `Idempotency-Key` required."
        ),
    )
    def create_executor_host_agent_install(
        subject: CurrentSubject, body: models.CreateExecutorHostAgentInstallRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = hosts.create_agent_install(body=body, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(201, _body(view))

    @router.get(
        "/executor-hosts/{host_id}/agent-installs/{install_id}", operation_id="getExecutorHostAgentInstall", tags=_TAGS,
        response_model=models.ExecutorAgentInstall,
        responses={**success(200, "The install session as it stands."), **envelope_responses(401, 403, 404, 422, 500, 503)},
        description="`HOSTS-SEAL-1`: one install session of a host, as `getExecutorAgentInstall` reads one of a connection. `role:admin`.",
    )
    def get_executor_host_agent_install(host_id: HostIdPath, install_id: InstallIdPath) -> WireResponse:
        return json_response(200, _body(hosts.get_agent_install(host_id=host_id, install_id=install_id)))

    @router.post(
        "/executor-hosts/{host_id}/agent-installs/{install_id}/confirm-host-key",
        operation_id="confirmExecutorHostAgentInstallHostKey", tags=_TAGS,
        response_model=models.ExecutorAgentInstall,
        responses={**success(200, "The install session after the confirmation, or as it stands for an identical repeat."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503, descriptions={409: STATE_CONFLICT_DESCRIPTION})},
        description=(
            "`HOSTS-SEAL-1`: confirm the host key of the install session of a host, as `confirmExecutorAgentInstallHostKey`: the fingerprint "
            "must equal the one the worker observed; there is no trust on first use. `role:admin`, `Idempotency-Key` required."
        ),
    )
    def confirm_executor_host_agent_install_host_key(
        subject: CurrentSubject, host_id: HostIdPath, install_id: InstallIdPath,
        body: models.ConfirmExecutorAgentInstallHostKeyRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = hosts.confirm_agent_install_host_key(
            host_id=host_id, install_id=install_id, body=body, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, _body(view))
