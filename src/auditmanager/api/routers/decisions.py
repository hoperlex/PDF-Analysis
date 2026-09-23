"""``appendDecision``, ``listDecisionHistory`` and ``listDecisions``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from auditmanager.api.routers.declarations import (
    CategoryFilterParam,
    CursorParam,
    LimitParam,
    VerdictFilterParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import DecisionPort, FindingPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.common import page_body, paginate, timestamp
from auditmanager.api.schemas.decisions import (
    append_decision_body,
    decision_event_body,
    decision_record_body,
    check_comment_is_present_for_a_comment_event,
)
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["build_decision_routes"]


def build_decision_routes(
    router: APIRouter, decisions: DecisionPort, findings: FindingPort
) -> None:
    """`D-67`. ``findings`` is here so that ``listDecisionHistory`` can answer its path.

    Not to read a finding for its own sake -- to establish that the finding the path names
    exists, before its ledger is rendered as an empty page. ``listDecisions``, two routes
    below, takes no such argument and must not: its path names no parent.
    """

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
        # `D-67`. The finding is proved to exist before its ledger is read. A finding
        # that has never been decided on has an empty history and that is a true answer;
        # a finding that does not exist has no history to be empty, and until this line
        # the two were the same 200.
        #
        # The reason this sits in the router rather than in the adapter is written out at
        # the same line in `findings.py`, and applies word for word: the `404` is the
        # frozen contract's statement about this operation, and the operation is here.
        #
        # `D-74`. It used to call `get_finding`, which reads the finding's evidence, its
        # current verdict and -- this listing's own rows -- its whole history, to answer a
        # yes/no, and the line below then read that history a second time. `finding_exists`
        # is the narrow question; the refusal stays here, where the operation is.
        if not findings.finding_exists(finding_uid=finding_uid):
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Finding")
        rows = decisions.decision_history(finding_uid=finding_uid)
        page = paginate(rows, limit=limit, cursor=cursor, sort_key=_decision_sort_key)
        body = page_body([decision_event_body(view) for view in page.items], page.next_cursor)
        return json_response(200, encode_json(body))

    @router.get(
        "/decisions",
        operation_id="listDecisions",
        tags=["decisions"],
        status_code=200,
        response_model=models.DecisionRecordPage,
        responses={
            **success(200, "One page of the decision journal, newest first."),
            # No 404. The path addresses no parent identity, so there is no identity that
            # could be missing: a deployment that has decided nothing has an empty journal,
            # and an empty page is the true answer. The listings that DO declare 404 --
            # `listDocuments`, `listVersions`, `listRuns` -- each hang off a parent whose
            # absence is a different fact from its emptiness.
            **envelope_responses(401, 403, 422, 500, 503),
        },
    )
    def list_decisions(
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
        category: CategoryFilterParam = None,  # type: ignore[assignment]
        verdict: VerdictFilterParam = None,  # type: ignore[assignment]
    ) -> WireResponse:
        rows = decisions.decision_journal(
            category=None if category is None else category.value,
            verdict=None if verdict is None else verdict.value,
        )
        page = paginate(rows, limit=limit, cursor=cursor, sort_key=_decision_sort_key)
        body = page_body([decision_record_body(view) for view in page.items], page.next_cursor)
        return json_response(200, encode_json(body))


def _decision_sort_key(view: object) -> tuple[str, ...]:
    """``(recorded_at, decision_id)`` -- the declared client-visible total order.

    ``P02_SEAMS.md`` section 5.3 names exactly this pair and adds that the server's
    ``sequence_no`` "is never returned and never embedded in a cursor". Using the sequence
    here would be the easy implementation and the declared defect.
    """
    return (timestamp(getattr(view, "recorded_at")), getattr(view, "decision_id"))
