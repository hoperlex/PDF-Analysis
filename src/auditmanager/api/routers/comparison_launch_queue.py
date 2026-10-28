"""The launch queue of a project and the installation's AI queue, sealed as stubs (`CMP-SEAL-C2`,
ADR-0025 decisions 4, 6 and 19).

``enqueueComparisonLaunch`` queues the selected document sets × steps (profiles, matrix, AI check of pairs,
series, AI description, summary and report); ``getComparisonLaunchQueue`` reads «готово N из M · пропущено K ·
ошибок E»; ``pauseComparisonLaunchQueue``, ``resumeComparisonLaunchQueue``, ``clearComparisonLaunchQueue``
and ``removeComparisonLaunchEntry`` steer it; ``getComparisonAiQueue`` reads «Очередь «ИИ-описание
изменений»» of the installation. The queue runs one step at a time across sets and asks for AI consent per
set only when its estimate exists. Reads are any one role; every write is an expert's act (`R-60`) and
keyed. All seven answer ``503 dependency_unavailable`` until `CMP-VC-QUEUE-01` wires the port, and
``comparison_modules`` first while the versions module is off.
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Path
from pydantic import BaseModel

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ComparisonLaunchQueuePort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_comparison_launch_queue_routes"]

_TAGS: Final[list[str]] = ["comparison"]
_QUEUE: Final[str] = "/projects/{project_uid}/comparison-launch-queue"

_ProjectUid = Annotated[models.ProjectUid, Path()]
_EntryId = Annotated[models.ComparisonLaunchEntryId, Path()]


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def build_comparison_launch_queue_routes(
    router: APIRouter, queue: ComparisonLaunchQueuePort
) -> None:
    @router.get(
        _QUEUE, operation_id="getComparisonLaunchQueue", tags=_TAGS, status_code=200,
        response_model=models.ComparisonLaunchQueue,
        responses={**success(200, "The launch queue of the project."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_comparison_launch_queue(project_uid: _ProjectUid) -> WireResponse:
        return json_response(200, _body(queue.get_queue(project_uid=project_uid)))

    @router.post(
        f"{_QUEUE}/entries", operation_id="enqueueComparisonLaunch", tags=_TAGS, status_code=201,
        response_model=models.ComparisonLaunchQueue,
        responses={**success(201, "The launch queue with the new entries, or the recorded outcome of "
                                  "an identical earlier request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def enqueue_comparison_launch(
        subject: CurrentSubject, project_uid: _ProjectUid,
        body: models.EnqueueComparisonLaunchRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = queue.enqueue(
            project_uid=project_uid, items=body.items, restart=bool(body.restart),
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, _body(view))

    @router.post(
        f"{_QUEUE}/pause", operation_id="pauseComparisonLaunchQueue", tags=_TAGS, status_code=200,
        response_model=models.ComparisonLaunchQueue,
        responses={**success(200, "The launch queue, paused after the step in hand."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def pause_comparison_launch_queue(
        subject: CurrentSubject, project_uid: _ProjectUid, idempotency_key: RequiredIdempotencyKey
    ) -> WireResponse:
        view = queue.pause_queue(
            project_uid=project_uid, user_uid=subject.user_uid, idempotency_key=idempotency_key
        )
        return json_response(200, _body(view))

    @router.post(
        f"{_QUEUE}/resume", operation_id="resumeComparisonLaunchQueue", tags=_TAGS,
        status_code=200, response_model=models.ComparisonLaunchQueue,
        responses={**success(200, "The launch queue, running again."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def resume_comparison_launch_queue(
        subject: CurrentSubject, project_uid: _ProjectUid, idempotency_key: RequiredIdempotencyKey
    ) -> WireResponse:
        view = queue.resume_queue(
            project_uid=project_uid, user_uid=subject.user_uid, idempotency_key=idempotency_key
        )
        return json_response(200, _body(view))

    @router.post(
        f"{_QUEUE}/clear", operation_id="clearComparisonLaunchQueue", tags=_TAGS, status_code=200,
        response_model=models.ComparisonLaunchQueue,
        responses={**success(200, "The launch queue without the waiting entries and the history."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def clear_comparison_launch_queue(
        subject: CurrentSubject, project_uid: _ProjectUid, idempotency_key: RequiredIdempotencyKey
    ) -> WireResponse:
        view = queue.clear_queue(
            project_uid=project_uid, user_uid=subject.user_uid, idempotency_key=idempotency_key
        )
        return json_response(200, _body(view))

    @router.post(
        "/comparison-launch-entries/{comparison_launch_entry_id}/removal",
        operation_id="removeComparisonLaunchEntry", tags=_TAGS, status_code=200,
        response_model=models.ComparisonLaunchQueue,
        responses={**success(200, "The launch queue without the entry."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def remove_comparison_launch_entry(
        subject: CurrentSubject, comparison_launch_entry_id: _EntryId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = queue.remove_entry(
            entry_id=comparison_launch_entry_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.get(
        "/execution/comparison-ai-queue", operation_id="getComparisonAiQueue",
        tags=["execution"], status_code=200, response_model=models.ComparisonAiQueue,
        responses={**success(200, "The AI jobs of the installation that are queued, running or "
                                  "paused."),
                   **envelope_responses(401, 403, 500, 503)},
    )
    def get_comparison_ai_queue() -> WireResponse:
        return json_response(200, _body(queue.get_ai_queue()))
