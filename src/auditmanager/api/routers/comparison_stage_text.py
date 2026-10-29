"""C3 immutable raw text evidence and deterministic recomputation boundary."""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Path
from pydantic import BaseModel

from auditmanager.api.routers.declarations import CursorParam, LimitParam, envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ComparisonStageTextPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_comparison_stage_text_routes"]

_TAGS: Final[list[str]] = ["comparison"]
_PAIR: Final[str] = "/stage-pairs/{stage_pair_id}"
_REVISION: Final[str] = "/stage-link-revisions/{stage_link_revision_id}"
_PairId = Annotated[models.StagePairId, Path()]
_RevisionId = Annotated[models.StageLinkRevisionId, Path()]


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def build_comparison_stage_text_routes(router: APIRouter, text: ComparisonStageTextPort) -> None:
    @router.get(
        f"{_PAIR}/text-fragments", operation_id="listStageTextFragments", tags=_TAGS,
        status_code=200, response_model=models.StageTextFragmentPage,
        responses={**success(200, "One page of extracted raw text fragments."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_stage_text_fragments(
        stage_pair_id: _PairId, cursor: CursorParam = None, limit: LimitParam = 50,
    ) -> WireResponse:
        return json_response(200, _body(text.list_fragments(
            pair_id=stage_pair_id, cursor=cursor, limit=limit,
        )))

    @router.get(
        f"{_REVISION}/text-exclusions", operation_id="listStageTextExclusions", tags=_TAGS,
        status_code=200, response_model=models.StageTextExclusionPage,
        responses={**success(200, "Proven identical or moved fragment exclusions."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_stage_text_exclusions(
        stage_link_revision_id: _RevisionId, cursor: CursorParam = None, limit: LimitParam = 50,
    ) -> WireResponse:
        return json_response(200, _body(text.list_exclusions(
            revision_id=stage_link_revision_id, cursor=cursor, limit=limit,
        )))

    @router.get(
        f"{_REVISION}/raw-differences", operation_id="listStageRawDifferences", tags=_TAGS,
        status_code=200, response_model=models.StageTextDifferencePage,
        responses={**success(200, "Immutable deterministic text differences."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_stage_raw_differences(
        stage_link_revision_id: _RevisionId, cursor: CursorParam = None, limit: LimitParam = 50,
    ) -> WireResponse:
        return json_response(200, _body(text.list_differences(
            revision_id=stage_link_revision_id, cursor=cursor, limit=limit,
        )))

    @router.get(
        f"{_REVISION}/text-hints", operation_id="listStageTextHints", tags=_TAGS,
        status_code=200, response_model=models.StageTextHintPage,
        responses={**success(200, "Cross-sheet hints kept separate from raw differences."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_stage_text_hints(
        stage_link_revision_id: _RevisionId, cursor: CursorParam = None, limit: LimitParam = 50,
    ) -> WireResponse:
        return json_response(200, _body(text.list_hints(
            revision_id=stage_link_revision_id, cursor=cursor, limit=limit,
        )))

    @router.post(
        f"{_REVISION}/text-evidence/recomputation", operation_id="recomputeStageTextEvidence",
        tags=_TAGS, status_code=202, response_model=models.StageChainRun,
        responses={**success(202, "A durable deterministic recomputation request or keyed replay."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def recompute_stage_text_evidence(
        subject: CurrentSubject, stage_link_revision_id: _RevisionId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(202, _body(text.recompute(
            revision_id=stage_link_revision_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )))
