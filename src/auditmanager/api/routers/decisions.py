"""``appendDecision`` and ``listDecisionHistory``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from auditmanager.api.routers.declarations import (
    CursorParam,
    LimitParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import DecisionPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.common import page_body, paginate, timestamp
from auditmanager.api.schemas.decisions import (
    append_decision_body,
    decision_event_body,
    check_comment_is_present_for_a_comment_event,
)

__all__ = ["build_decision_routes"]


def build_decision_routes(router: APIRouter, decisions: DecisionPort) -> None:

    @router.post(
        "/findings/{finding_uid}/decisions",
        operation_id="appendDecision",
        tags=["decisions"],
        status_code=201,
        response_model=models.AppendDecisionResponse,
        responses={
            **success(201, "The appended event and the verdict that now follows."),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503),
        },
    )
    def append_decision(
        finding_uid: Annotated[models.FindingUid, Path()],
        body: models.AppendDecisionRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        # One rule the contract states in prose and no JSON Schema keyword can express:
        # a `comment` event must carry a comment. It is checked here, against the
        # validated model, rather than left to the command layer, because the refusal is
        # a request-shape refusal and the caller needs to know which property it is.
        check_comment_is_present_for_a_comment_event(
            event_type=body.event_type.value, comment=body.comment
        )
        appended = decisions.append_decision(
            finding_uid=finding_uid,
            finding_observation_id=body.finding_observation_id,
            event_type=body.event_type.value,
            comment=body.comment,
            idempotency_key=idempotency_key,
        )
        payload = append_decision_body(appended.event, appended.current_verdict)
        return json_response(201, encode_json(payload))

    @router.get(
        "/findings/{finding_uid}/decisions",
        operation_id="listDecisionHistory",
        tags=["decisions"],
        status_code=200,
        response_model=models.DecisionEventPage,
        responses={
            **success(200, "The whole ledger for one finding, oldest first."),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
    )
    def list_decision_history(
        finding_uid: Annotated[models.FindingUid, Path()],
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        rows = decisions.decision_history(finding_uid=finding_uid)
        page = paginate(rows, limit=limit, cursor=cursor, sort_key=_decision_sort_key)
        body = page_body([decision_event_body(view) for view in page.items], page.next_cursor)
        return json_response(200, encode_json(body))



def _decision_sort_key(view: object) -> tuple[str, ...]:
    """``(recorded_at, decision_id)`` -- the declared client-visible total order.

    ``P02_SEAMS.md`` section 5.3 names exactly this pair and adds that the server's
    ``sequence_no`` "is never returned and never embedded in a cursor". Using the sequence
    here would be the easy implementation and the declared defect.
    """
    return (timestamp(getattr(view, "recorded_at")), getattr(view, "decision_id"))
