"""The expert decision memory (`DECISION-MEMORY-01` phase M2, contract 1.44.0): five routes.

* ``listDecisionMemoryCases`` -- ``GET /decision-memory/cases`` (``expert`` or ``admin``): the cases, newest capture first, filtered by
  section, category, the verdict of the latest decision, standing, data class and the project they came from.
* ``getDecisionMemoryCase`` -- ``GET /decision-memory/cases/{case_id}`` (``expert`` or ``admin``): one case with what it keeps; a forgotten
  case answers its tombstone only.
* ``getDecisionMemoryStatus`` -- ``GET /decision-memory/status`` (``admin``): the counts and the installation settings in force.
* ``withdrawDecisionMemoryCase`` and ``restoreDecisionMemoryCase`` -- ``POST /decision-memory/cases/{case_id}/withdraw`` and ``/restore``
  (``admin``, ``Idempotency-Key`` required): a change of standing, an append-only status event with a closed reason.

The routes parse, call one port method and render; every rule -- the standing, the transitions, the append-only events, the read model --
lives in ``auditmanager.decision_memory``. **Forget is not an operation**: it deletes content and objects, so it stays the operator's tool
(``scripts/recovery/memory_forget.py``). The memory is not a decision authority: while the source finding exists the ledger decides.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Path, Query
from pydantic import BeforeValidator, Field, WithJsonSchema

from auditmanager.api.routers.declarations import CursorParam, LimitParam, envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import DecisionMemoryPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.models import optional_property
from auditmanager.api.security import CurrentSubject
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["build_decision_memory_routes"]

_TAGS = ["decision-memory"]


def _absent(value: Any) -> Any:
    """``?status=`` is the absent parameter, not a value of the empty string."""
    return None if value == "" else value


CaseIdPath = Annotated[models.DecisionMemoryCaseId, Path()]
SectionFilter = Annotated[
    Annotated[str, Field(min_length=1, max_length=64)] | None, BeforeValidator(_absent),
    WithJsonSchema({"type": "string", "minLength": 1, "maxLength": 64}),
    Query(json_schema_extra=optional_property),
]
CategoryFilter = Annotated[
    Annotated[str, Field(min_length=1, max_length=64)] | None, BeforeValidator(_absent),
    WithJsonSchema({"type": "string", "minLength": 1, "maxLength": 64}),
    Query(json_schema_extra=optional_property),
]
VerdictFilter = Annotated[
    Literal["accepted", "rejected"] | None, BeforeValidator(_absent),
    WithJsonSchema({"type": "string", "enum": ["accepted", "rejected"]}),
    Query(json_schema_extra=optional_property),
]
StandingFilter = Annotated[
    Literal["active", "withdrawn", "forgotten"] | None, BeforeValidator(_absent),
    WithJsonSchema({"type": "string", "enum": ["active", "withdrawn", "forgotten"]}),
    Query(json_schema_extra=optional_property),
]
DataClassFilter = Annotated[
    Literal["test", "real"] | None, BeforeValidator(_absent),
    WithJsonSchema({"type": "string", "enum": ["test", "real"]}),
    Query(json_schema_extra=optional_property),
]
ProjectFilter = Annotated[
    models.ProjectUid | None, BeforeValidator(_absent),
    WithJsonSchema({"$ref": "#/components/schemas/ProjectUid"}),
    Query(json_schema_extra=optional_property),
]


def build_decision_memory_routes(router: APIRouter, memory: DecisionMemoryPort) -> None:

    @router.get(
        "/decision-memory/cases", operation_id="listDecisionMemoryCases", tags=_TAGS, status_code=200,
        response_model=models.DecisionMemoryCasePage,
        responses={**success(200, "One page of cases, newest capture first."), **envelope_responses(401, 403, 422, 500, 503)},
        description=(
            "`DECISION-MEMORY-01` phase M2 (contract 1.44.0): the cases of the expert decision memory -- the copy of what an expert saw "
            "and said when a decision was taken, kept after the project and the document are gone. Newest capture first (`cursor`, "
            "`limit`). Filters, all optional: `section_code` (as of capture), `category`, `verdict` (the latest decision's), `status` "
            "(`active`, `withdrawn`, `forgotten`), `data_class` (`test` or `real`, fixed at capture) and `origin_project_uid` (an "
            "identity that may resolve nowhere any more). A case is **history, not a verdict in force**: while the source finding "
            "exists the ledger decides. `role:admin|expert`."
        ),
    )
    def list_decision_memory_cases(
        subject: CurrentSubject,
        section_code: SectionFilter = None,
        category: CategoryFilter = None,
        verdict: VerdictFilter = None,
        status: StandingFilter = None,
        data_class: DataClassFilter = None,
        origin_project_uid: ProjectFilter = None,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        page = memory.list_cases(
            section_code=section_code, category=category, verdict=verdict, status=status, data_class=data_class,
            origin_project_uid=origin_project_uid, cursor=cursor, limit=limit,
        )
        return json_response(200, encode_json(page.model_dump(mode="json")))

    @router.get(
        "/decision-memory/cases/{case_id}", operation_id="getDecisionMemoryCase", tags=_TAGS, status_code=200,
        response_model=models.DecisionMemoryCase,
        responses={**success(200, "The case with what it keeps."), **envelope_responses(401, 403, 404, 422, 500, 503)},
        description=(
            "`DECISION-MEMORY-01` phase M2: one case -- its summary, the model's finding and recommendation as they stood, the evidence "
            "quotes with their page geometry, the certified normative references, the crop images it references (a binding to an "
            "existing Blob), every captured decision with the expert's own comment, and the history of its standing. **A forgotten "
            "case answers its tombstone only**: `content` is `null`, the lists are empty and no decision carries a comment; the "
            "`forget` event carries the digest of what was forgotten. An unknown case is `404`. `role:admin|expert`."
        ),
    )
    def get_decision_memory_case(subject: CurrentSubject, case_id: CaseIdPath) -> WireResponse:
        case = memory.get_case(case_id=case_id)
        if case is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="DecisionMemoryCase")
        return json_response(200, encode_json(case.model_dump(mode="json")))

    @router.get(
        "/decision-memory/status", operation_id="getDecisionMemoryStatus", tags=_TAGS, status_code=200,
        response_model=models.DecisionMemoryStatus,
        responses={**success(200, "The counts and the settings in force."), **envelope_responses(401, 403, 500, 503)},
        description=(
            "`DECISION-MEMORY-01` phase M2: how many cases and decisions the memory holds, by standing and data class, and the "
            "installation settings in force -- `data_class`, what a case captured now is (`test` until an operator journals `real`), and "
            "`training_use`, whether the training export may run (`off` until the owner's permission is recorded). The settings are "
            "changed by an operator tool, not by this surface. `role:admin`."
        ),
    )
    def get_decision_memory_status(subject: CurrentSubject) -> WireResponse:
        return json_response(200, encode_json(memory.status().model_dump(mode="json")))

    @router.post(
        "/decision-memory/cases/{case_id}/withdraw", operation_id="withdrawDecisionMemoryCase", tags=_TAGS, status_code=200,
        response_model=models.DecisionMemoryStatusChange,
        responses={
            **success(200, "The status event written, or the first call's for an exact repeat."),
            **envelope_responses(
                401, 403, 404, 409, 422, 500, 503,
                descriptions={
                    409: "The case was forgotten (`conflict` with `details.conflict_reason`: `memory_case_forgotten`), or an "
                    "idempotency key already used with a different payload. A case that is already withdrawn is "
                    "`409 state_transition_not_allowed`.",
                },
            ),
        },
        description=(
            "`DECISION-MEMORY-01` phase M2: take a case out of hints, prompts and exports. Append-only: a `withdraw` status event with a "
            "closed `reason_code` (no free text) and the caller's account; the case itself is never edited. A case that is already "
            "withdrawn is `409 state_transition_not_allowed`; a forgotten case accepts no status event (`409 conflict`, "
            "`conflict_reason: memory_case_forgotten`); an unknown case is `404`. An exact repeat of the `Idempotency-Key` answers the "
            "first call's event and writes nothing. `role:admin`."
        ),
    )
    def withdraw_decision_memory_case(
        subject: CurrentSubject, case_id: CaseIdPath, body: models.DecisionMemoryStatusChangeRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        change = memory.withdraw_case(
            case_id=case_id, reason_code=body.reason_code, user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(200, encode_json(change.model_dump(mode="json")))

    @router.post(
        "/decision-memory/cases/{case_id}/restore", operation_id="restoreDecisionMemoryCase", tags=_TAGS, status_code=200,
        response_model=models.DecisionMemoryStatusChange,
        responses={
            **success(200, "The status event written, or the first call's for an exact repeat."),
            **envelope_responses(
                401, 403, 404, 409, 422, 500, 503,
                descriptions={
                    409: "The case was forgotten (`conflict` with `details.conflict_reason`: `memory_case_forgotten`), or an "
                    "idempotency key already used with a different payload. A case that is not withdrawn is "
                    "`409 state_transition_not_allowed`.",
                },
            ),
        },
        description=(
            "`DECISION-MEMORY-01` phase M2: undo a withdraw. Append-only: a `restore` status event with a closed `reason_code` and the "
            "caller's account. A case that is not withdrawn is `409 state_transition_not_allowed`; a forgotten case accepts no status "
            "event (`409 conflict`, `conflict_reason: memory_case_forgotten`); an unknown case is `404`. An exact repeat of the "
            "`Idempotency-Key` answers the first call's event and writes nothing. `role:admin`."
        ),
    )
    def restore_decision_memory_case(
        subject: CurrentSubject, case_id: CaseIdPath, body: models.DecisionMemoryStatusChangeRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        change = memory.restore_case(
            case_id=case_id, reason_code=body.reason_code, user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(200, encode_json(change.model_dump(mode="json")))
