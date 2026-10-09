"""W53 execution declarations; every operation delegates to a port."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query
from pydantic import WithJsonSchema

from auditmanager.api.routers.declarations import CursorParam, LimitParam, envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ExecutionPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.models import optional_property
from auditmanager.api.schemas.runs import run_status_body
from auditmanager.api.security import CurrentSubject


RunIdFilterParam = Annotated[
    models.RunId | None,
    WithJsonSchema({"$ref": "#/components/schemas/RunId"}),
    Query(json_schema_extra=optional_property),
]


def build_execution_routes(router: APIRouter, execution: ExecutionPort) -> None:
    @router.get(
        "/execution/queue", operation_id="listExecutionQueue", tags=["execution"],
        response_model=models.ExecutionQueuePage,
        responses={**success(200, "The durable queue and dispatch pause state."),
                   **envelope_responses(401, 403, 422, 500, 503)},
    )
    def list_queue(
        subject: CurrentSubject, cursor: CursorParam = None, limit: LimitParam = 50,
    ) -> WireResponse:
        page = execution.list_queue(cursor=cursor, limit=limit)
        return json_response(200, encode_json(page.model_dump(mode="json")))

    @router.get(
        "/execution/journal", operation_id="listExecutionJournal", tags=["execution"],
        response_model=models.ExecutionJournalPage,
        responses={**success(200, "The execution journal, newest first."),
                   **envelope_responses(401, 403, 422, 500, 503)},
    )
    def list_journal(
        subject: CurrentSubject,
        run_id: RunIdFilterParam = None,
        cursor: CursorParam = None,
        limit: LimitParam = 50,
    ) -> WireResponse:
        page = execution.list_journal(run_id=run_id, cursor=cursor, limit=limit)
        return json_response(200, encode_json(page.model_dump(mode="json")))

    @router.post(
        "/runs/{run_id}/cancel", operation_id="cancelRun", tags=["execution"],
        response_model=models.RunStatus,
        responses={**success(200, "The cancelled run or a replayed result."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def cancel_run(
        subject: CurrentSubject, run_id: Annotated[models.RunId, Path()],
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = execution.cancel_run(
            run_id=run_id, user_uid=subject.user_uid, idempotency_key=idempotency_key
        )
        return json_response(200, encode_json(run_status_body(view)))

    @router.post(
        "/runs/{run_id}/reaudit", operation_id="reauditRun", tags=["execution"],
        status_code=202, response_model=models.RunStatus,
        responses={**success(202, "The newly accepted re-audit run or a replayed result."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def reaudit_run(
        subject: CurrentSubject, run_id: Annotated[models.RunId, Path()],
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = execution.reaudit_run(
            run_id=run_id, user_uid=subject.user_uid, idempotency_key=idempotency_key
        )
        return json_response(202, encode_json(run_status_body(view)))

    @router.put(
        "/execution/queue/{job_id}/priority", operation_id="setJobPriority",
        tags=["execution"], response_model=models.ExecutionQueueItem,
        responses={**success(200, "The queued job with its new priority."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def set_priority(
        subject: CurrentSubject, job_id: Annotated[models.JobId, Path()],
        body: models.SetJobPriorityRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        item = execution.set_job_priority(
            job_id=job_id, priority=body.priority, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, encode_json(item.model_dump(mode="json")))

    @router.put(
        "/execution/dispatch", operation_id="setExecutionPaused",
        tags=["execution"], response_model=models.ExecutionDispatchStatus,
        responses={**success(200, "The durable dispatch pause state."),
                   **envelope_responses(401, 403, 409, 422, 500, 503)},
    )
    def set_paused(
        subject: CurrentSubject, body: models.SetExecutionPausedRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        status = execution.set_paused(
            paused=body.paused, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, encode_json(status.model_dump(mode="json")))
