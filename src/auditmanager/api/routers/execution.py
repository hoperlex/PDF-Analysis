"""W53 execution declarations; every operation delegates to a port.

`W54-SEAL-01` added the worker registry's ``listWorkers`` and ``setWorkerIntake``
(plan section 3.7) as sealed stubs; `W54-WORKER-01` gave their port methods the registry
behaviour (``bootstrap/adapters.py``, ``auditmanager.workers``).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Path, Query
from pydantic import WithJsonSchema

from auditmanager.api.routers.declarations import (
    CursorParam, LimitParam, QueueCreatedFromParam, QueueCreatedToParam, QueueStateFilterParam,
    QueueStateGroupFilterParam, envelope_responses, success,
)
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
        state: QueueStateFilterParam = None,  # type: ignore[assignment]
        created_from: QueueCreatedFromParam = None,  # type: ignore[assignment]
        created_to: QueueCreatedToParam = None,  # type: ignore[assignment]
        state_group: QueueStateGroupFilterParam = None,  # type: ignore[assignment]
    ) -> WireResponse:
        page = execution.list_queue(
            cursor=cursor, limit=limit, state=state,
            created_from=created_from, created_to=created_to, state_group=state_group,
        )
        # `UI-PARITY-QUEUE-A`: a property an item does not have is omitted, not sent as `null` -- the
        # contract declares none of them nullable, and `binding_state` / `wait_reason` were sent as
        # `null` for an ordinary job until now.
        return json_response(200, encode_json(page.model_dump(mode="json", exclude_unset=True)))

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
        body: models.ReauditRunRequest = Body(default=None),
    ) -> WireResponse:
        view = execution.reaudit_run(
            run_id=run_id, user_uid=subject.user_uid, idempotency_key=idempotency_key,
            **({"cost_consent": body.cost_consent.model_dump(mode="json")}
                if body is not None and body.cost_consent is not None else {}),
        )
        return json_response(202, encode_json(run_status_body(view)))

    @router.post(
        "/runs/{run_id}/start-from-stage", operation_id="startRunFromStage", tags=["execution"],
        status_code=202, response_model=models.RunStatus,
        responses={**success(202, "The newly accepted run that reuses the earlier run's stage outputs, or a replayed result."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
        description=(
            "`R-151i` (`UI-A-60`): a NEW run of the earlier run's document version that reuses the earlier run's completed "
            "outputs of every PC-01 stage before `stage_id` and computes `stage_id` and the stages after it. The earlier "
            "run is immutable history and is not changed; the new run is linked to it by `started_from_run_id` and "
            "`start_stage_id` on its `RunStatus` (not by `reaudit_of_run_id`) and records today's configuration, exactly as "
            "a re-audit does (R-82). `stage_id` is one of `page_geometry_extraction`, `document_context_build` or "
            "`text_analysis`: the first stage reuses nothing (`422 validation_failed`, `field` `stage_id`, `constraint` "
            "`nothing_to_reuse`; use `reauditRun`) and any other stage is not startable (`constraint` `stage_not_startable`). "
            "The earlier run must have ended (`409 state_transition_not_allowed`) and be a run of the standard analysis "
            "(a member of an AR v3 group is `409 conflict`, `conflict_reason` `ar_v3_member_not_repeatable`). A stage output "
            "that cannot be taken is `422 analysis_input_invalid` with `details.stage_id` (the first stage that cannot) and "
            "`details.reason`: `source_stage_not_completed`, `source_stage_version_changed`, `source_stage_output_incomplete`, "
            "`source_artifact_unavailable`, `source_artifact_changed` or `source_stage_inputs_changed`. Nothing is "
            "recomputed in place of a refused output and nothing is written. Served starts require fresh confirmed cost "
            "consent from estimateRunCost with `start_from_run_id` and `start_stage_id`: the price is for the stages the "
            "new run computes, and the digest is bound to this earlier run and stage. While a run from this earlier run and "
            "stage has not ended, a second is `409 conflict`. Accepted keys replay their recorded outcome."),
    )
    def start_run_from_stage(
        subject: CurrentSubject, run_id: Annotated[models.RunId, Path()],
        idempotency_key: RequiredIdempotencyKey,
        body: models.StartRunFromStageRequest,
    ) -> WireResponse:
        view = execution.start_run_from_stage(
            run_id=run_id, stage_id=body.stage_id.value, user_uid=subject.user_uid, idempotency_key=idempotency_key,
            **({"cost_consent": body.cost_consent.model_dump(mode="json")} if body.cost_consent is not None else {}),
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
        return json_response(200, encode_json(item.model_dump(mode="json", exclude_unset=True)))

    @router.get(
        "/execution/dispatch", operation_id="getExecutionDispatch",
        tags=["execution"], response_model=models.ExecutionDispatchStatus,
        responses={**success(200, "The durable dispatch pause state."),
                   **envelope_responses(401, 403, 500, 503)},
    )
    def get_dispatch(subject: CurrentSubject) -> WireResponse:
        # `UI-PARITY-P0E` (ruling `R-151f`): the pause state without reading the queue.
        status = execution.get_dispatch_status()
        return json_response(200, encode_json(status.model_dump(mode="json")))

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

    @router.get(
        "/execution/workers", operation_id="listWorkers", tags=["execution"],
        response_model=models.ExecutionWorkerPage,
        responses={**success(200, "The worker registry: state, intake, slots, version and current runs."),
                   **envelope_responses(401, 403, 422, 500, 503)},
    )
    def list_workers(
        subject: CurrentSubject, cursor: CursorParam = None, limit: LimitParam = 50,
    ) -> WireResponse:
        page = execution.list_workers(cursor=cursor, limit=limit)
        return json_response(200, encode_json(page.model_dump(mode="json")))

    @router.put(
        "/execution/workers/{worker_id}/intake", operation_id="setWorkerIntake",
        tags=["execution"], response_model=models.ExecutionWorker,
        responses={**success(200, "The worker with its new intake setting."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def set_worker_intake(
        subject: CurrentSubject, worker_id: Annotated[models.WorkerId, Path()],
        body: models.SetWorkerIntakeRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        worker = execution.set_worker_intake(
            worker_id=worker_id, enabled=body.enabled, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, encode_json(worker.model_dump(mode="json")))
