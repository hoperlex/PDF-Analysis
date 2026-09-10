"""``appendDecision`` and ``listDecisionHistory``."""

from __future__ import annotations

import json
from typing import Sequence

from auditmanager.api.routers.errors import decode_json_object
from auditmanager.api.routers.http import Request, Response, Route, json_response
from auditmanager.api.routers.idempotency import (
    require_idempotency_key,
    require_path_identity,
)
from auditmanager.api.routers.ports import DecisionPort
from auditmanager.api.schemas.common import page_body, paginate, parse_limit
from auditmanager.api.schemas.decisions import (
    append_decision_body,
    decision_event_body,
    parse_append_decision_request,
)
from auditmanager.api.schemas.common import timestamp
from auditmanager.shared.identity import FindingUid

__all__ = ["build_decision_routes"]


def build_decision_routes(decisions: DecisionPort) -> Sequence[Route]:
    def append_decision(request: Request) -> Response:
        key = require_idempotency_key(request)
        finding_uid = require_path_identity(
            request.path_params["finding_uid"],
            parse=FindingUid,
            aggregate_type="Finding",
        )
        command = parse_append_decision_request(decode_json_object(request.body))
        appended = decisions.append_decision(
            finding_uid=str(finding_uid),
            finding_observation_id=command.finding_observation_id,
            event_type=command.event_type,
            comment=command.comment,
            idempotency_key=key,
        )
        body = append_decision_body(appended.event, appended.current_verdict)
        return json_response(201, _encode(body))

    def list_decision_history(request: Request) -> Response:
        finding_uid = require_path_identity(
            request.path_params["finding_uid"],
            parse=FindingUid,
            aggregate_type="Finding",
        )
        limit = parse_limit(request.query_one("limit"))
        cursor = request.query_one("cursor")
        rows = decisions.decision_history(finding_uid=str(finding_uid))
        page = paginate(rows, limit=limit, cursor=cursor, sort_key=_decision_sort_key)
        body = page_body([decision_event_body(view) for view in page.items], page.next_cursor)
        return json_response(200, _encode(body))

    return (
        Route(
            "appendDecision",
            "POST",
            "/findings/{finding_uid}/decisions",
            append_decision,
        ),
        Route(
            "listDecisionHistory",
            "GET",
            "/findings/{finding_uid}/decisions",
            list_decision_history,
        ),
    )


def _decision_sort_key(view: object) -> tuple[str, ...]:
    """``(recorded_at, decision_id)`` -- the declared client-visible total order.

    ``P02_SEAMS.md`` section 5.3 names exactly this pair and adds that the server's
    ``sequence_no`` "is never returned and never embedded in a cursor". Using the
    sequence here would be the easy implementation and the declared defect.
    """
    return (timestamp(getattr(view, "recorded_at")), getattr(view, "decision_id"))


def _encode(body: object) -> bytes:
    return json.dumps(body, ensure_ascii=False).encode("utf-8")
