"""The executor connections (`EXEC-SEAL-01`, `R-143`): where a process sends model work.

The executor operations share one port. Reads are open to any role; writes are an administrator's act
(`api/security.py`). **No operation returns a secret and none has a GET counterpart for one**:
``setExecutorSecret`` takes a write-only value and answers metadata only, and
``generateExecutorSshKey`` returns the public half of a key whose private half is sealed. A
refusal reuses an existing catalogue code with its existing detail keys.

Optional properties are absent, never null: every body is dumped with ``exclude_unset``, so the
adapter builds a body from the fields that have a value and nothing else.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ExecutorPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_executor_routes"]

_TAGS = ["execution"]
#: `ANALYSIS-PRESETS-01`. The presets sit beside the analysis profiles on the settings screen.
_PRESET_TAGS = ["analysis"]

_PRESETS_DESCRIPTION = (
    "The named presets of how a run starts (`R-146av`, `ANALYSIS-PRESETS-01`). A run start selects "
    "exactly one setting per run, the executor connection, so a preset is a name plus that "
    "connection; the cost ceiling is a process-wide setting and no threshold is an input of a "
    "start, so a preset holds neither. Each item is the preset's current revision; every earlier "
    "revision is kept and a run records the revision it started with. Archived presets are listed "
    "after the active ones. Any one role, `role:admin|expert`."
)
_CREATE_PRESET_DESCRIPTION = (
    "Save a preset: a name and an executor connection. An administrator's act, like every executor "
    "write (`role:admin`; the command re-reads the role set in its own transaction). The name is "
    "trimmed, 1 to 120 characters without control characters, and unique among active presets "
    "without regard to case. The connection must exist and must not be archived. At most 100 "
    "presets exist. The change and its audit event commit together. Refusals: `403`, "
    "`422 validation_failed` (`name`: `required`, `max_length`, `printable`; "
    "`executor_connection_id`: `unknown_connection`), `409 conflict` (`preset_name_in_use`, "
    "`preset_limit_reached`, `connection_archived`)."
)
_REVISE_PRESET_DESCRIPTION = (
    "Append a revision with the full settings, never a patch; the earlier revision is kept as it "
    "was and runs that used it keep pointing at it. An administrator's act (`role:admin`). Refusals: "
    "`403`, `404` for an unknown preset, `422 validation_failed` as for creation and "
    "`differs_from_current` on `name` when nothing would change, `409 conflict` "
    "(`preset_archived`, `preset_name_in_use`, `connection_archived`)."
)
_ARCHIVE_PRESET_DESCRIPTION = (
    "Append the archived revision, which repeats the previous name and connection. One-way: nothing "
    "follows an archive, and the name is free again. An administrator's act (`role:admin`). "
    "Refusals: `403`, `404` for an unknown preset, `409 conflict` (`preset_archived`) for one "
    "already archived."
)


def build_executor_routes(router: APIRouter, executors: ExecutorPort) -> None:
    @router.get(
        "/executor-connections", operation_id="listExecutorConnections", tags=_TAGS,
        response_model=models.ExecutorConnectionList,
        responses={**success(200, "Every connection with its secrets as metadata, and the "
                                  "models a revision may name with their pinned rates."),
                   **envelope_responses(401, 403, 500, 503)},
    )
    def list_executor_connections(subject: CurrentSubject) -> WireResponse:
        answer = executors.list_connections(user_uid=subject.user_uid)
        return json_response(200, encode_json(answer.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/executor-connections", operation_id="createExecutorConnection", tags=_TAGS,
        status_code=201, response_model=models.ExecutorConnection,
        responses={**success(201, "The connection, or the recorded outcome of an identical "
                                  "earlier request."),
                   **envelope_responses(401, 403, 409, 422, 500, 503)},
    )
    def create_executor_connection(
        subject: CurrentSubject, body: models.CreateExecutorConnectionRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = executors.create_connection(
            kind=body.kind.value, display_name=body.display_name,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.get(
        "/executor-connections/{connection_id}", operation_id="getExecutorConnection",
        tags=_TAGS, response_model=models.ExecutorConnectionDetail,
        responses={**success(200, "The connection, every revision with its latest probe, "
                                  "and the last ten probes."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def get_executor_connection(
        subject: CurrentSubject, connection_id: Annotated[models.ExecutorConnectionId, Path()],
    ) -> WireResponse:
        view = executors.get_connection(
            connection_id=connection_id, user_uid=subject.user_uid
        )
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/executor-connections/{connection_id}/revisions",
        operation_id="reviseExecutorConnection", tags=_TAGS, status_code=201,
        response_model=models.ExecutorRevision,
        responses={**success(201, "The new immutable revision, or the recorded outcome of "
                                  "an identical earlier request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def revise_executor_connection(
        subject: CurrentSubject, connection_id: Annotated[models.ExecutorConnectionId, Path()],
        body: models.ReviseExecutorConnectionRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = executors.revise_connection(
            connection_id=connection_id, settings=body,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/executor-connections/{connection_id}/archive",
        operation_id="archiveExecutorConnection", tags=_TAGS,
        response_model=models.ExecutorConnection,
        responses={**success(200, "The archived connection. A connection a route still "
                                  "names is a conflict."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def archive_executor_connection(
        subject: CurrentSubject, connection_id: Annotated[models.ExecutorConnectionId, Path()],
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = executors.archive_connection(
            connection_id=connection_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/executor-connections/{connection_id}/secrets",
        operation_id="setExecutorSecret", tags=_TAGS, status_code=201,
        response_model=models.ExecutorSecretMetadata,
        responses={**success(201, "The secret's metadata. The value is sealed on arrival "
                                  "and is never returned by any operation."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def set_executor_secret(
        subject: CurrentSubject, connection_id: Annotated[models.ExecutorConnectionId, Path()],
        body: models.SetExecutorSecretRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = executors.set_secret(
            connection_id=connection_id, purpose=body.purpose.value, value=body.value,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/executor-connections/{connection_id}/ssh-key",
        operation_id="generateExecutorSshKey", tags=_TAGS, status_code=201,
        response_model=models.ExecutorSshKey,
        responses={**success(201, "The public half of a new ed25519 key and its "
                                  "authorized_keys line. The private half is sealed to the "
                                  "connection's SSH endpoint and never returned."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def generate_executor_ssh_key(
        subject: CurrentSubject, connection_id: Annotated[models.ExecutorConnectionId, Path()],
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = executors.generate_ssh_key(
            connection_id=connection_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(201, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/executor-connections/{connection_id}/probes",
        operation_id="requestExecutorProbe", tags=_TAGS, status_code=202,
        response_model=models.ExecutorProbe,
        responses={**success(202, "The probe, recorded as requested. A worker executes it; "
                                  "one nobody takes within 120 seconds ends as no_worker."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def request_executor_probe(
        subject: CurrentSubject, connection_id: Annotated[models.ExecutorConnectionId, Path()],
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = executors.request_probe(
            connection_id=connection_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(202, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.get(
        "/executor-routes", operation_id="listExecutorRoutes", tags=_TAGS,
        response_model=models.ExecutorRouteList,
        responses={**success(200, "The current route of each kind of model work that has "
                                  "one."),
                   **envelope_responses(401, 403, 500, 503)},
    )
    def list_executor_routes(subject: CurrentSubject) -> WireResponse:
        answer = executors.list_routes(user_uid=subject.user_uid)
        return json_response(200, encode_json(answer.model_dump(mode="json", exclude_unset=True)))

    @router.get(
        "/analysis/presets", operation_id="listAnalysisPresets", tags=_PRESET_TAGS,
        response_model=models.AnalysisPresetList,
        responses={**success(200, "Every preset by its current revision: active ones first by name, "
                                  "then archived ones."),
                   **envelope_responses(401, 403, 500, 503)},
        description=_PRESETS_DESCRIPTION,
    )
    def list_analysis_presets(subject: CurrentSubject) -> WireResponse:
        answer = executors.list_presets(user_uid=subject.user_uid)
        return json_response(200, encode_json(answer.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/analysis/presets", operation_id="createAnalysisPreset", tags=_PRESET_TAGS,
        status_code=201, response_model=models.AnalysisPreset,
        responses={**success(201, "The preset (revision 1), or the recorded outcome of an identical "
                                  "earlier request."),
                   **envelope_responses(401, 403, 409, 422, 500, 503)},
        description=_CREATE_PRESET_DESCRIPTION,
    )
    def create_analysis_preset(
        subject: CurrentSubject, body: models.SaveAnalysisPresetRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = executors.create_preset(
            name=body.name, executor_connection_id=body.executor_connection_id,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/analysis/presets/{preset_id}/revisions", operation_id="reviseAnalysisPreset",
        tags=_PRESET_TAGS, status_code=201, response_model=models.AnalysisPreset,
        responses={**success(201, "The new revision, or the recorded outcome of an identical earlier "
                                  "request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
        description=_REVISE_PRESET_DESCRIPTION,
    )
    def revise_analysis_preset(
        subject: CurrentSubject, preset_id: Annotated[models.PresetId, Path()],
        body: models.SaveAnalysisPresetRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = executors.revise_preset(
            preset_id=preset_id, name=body.name, executor_connection_id=body.executor_connection_id,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/analysis/presets/{preset_id}/archive", operation_id="archiveAnalysisPreset",
        tags=_PRESET_TAGS, response_model=models.AnalysisPreset,
        responses={**success(200, "The archived revision. Archiving is one-way and the name is "
                                  "freed."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
        description=_ARCHIVE_PRESET_DESCRIPTION,
    )
    def archive_analysis_preset(
        subject: CurrentSubject, preset_id: Annotated[models.PresetId, Path()],
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = executors.archive_preset(
            preset_id=preset_id, user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.put(
        "/executor-routes", operation_id="setExecutorRoute", tags=_TAGS,
        response_model=models.ExecutorRoute,
        responses={**success(200, "The route as it now stands. Every change is journaled."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def set_executor_route(
        subject: CurrentSubject, body: models.SetExecutorRouteRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = executors.set_route(
            work_kind=body.work_kind.value,
            primary_connection_id=body.primary_connection_id,
            standby_connection_id=body.standby_connection_id,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))
