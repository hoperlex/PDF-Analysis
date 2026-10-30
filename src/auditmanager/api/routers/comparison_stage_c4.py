"""C4 typed boundaries: AI evidence, durable chain, repairs and expert review."""
from __future__ import annotations

from typing import Annotated, Literal
from fastapi import APIRouter, Path, Query, Response
from auditmanager.api.routers.declarations import CursorParam, LimitParam, envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ComparisonStageC4Port
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_comparison_stage_c4_routes"]


def build_comparison_stage_c4_routes(router: APIRouter, stage: ComparisonStageC4Port) -> None:
    @router.get("/stage-link-revisions/{stage_link_revision_id}/chain-estimate", operation_id="estimateStageChainRun", tags=["comparison"], status_code=200, response_model=models.ComparisonAiEstimate,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def estimate_run(
        stage_link_revision_id: Annotated[models.StageLinkRevisionId, Path()],
        subject: CurrentSubject,
        stage_chain_run_id: Annotated[str, Query(pattern=r"^(?:crn_[0-9A-HJKMNP-TV-Z]{26})?$")] = "",
    ) -> WireResponse:
        result = stage.estimate_run(revision_id=stage_link_revision_id,
                                    user_uid=subject.user_uid, run_id=stage_chain_run_id or None)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.post("/stage-chain-runs/{stage_chain_run_id}/resume", operation_id="resumeStageChainRun", tags=["comparison"], status_code=200, response_model=models.StageChainRun,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def resume_run(stage_chain_run_id: Annotated[models.StageChainRunId, Path()], body: models.ResumeStageChainRunRequest, subject: CurrentSubject, idempotency_key: RequiredIdempotencyKey) -> WireResponse:
        result = stage.resume_run(run_id=stage_chain_run_id, body=body, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.post("/projects/{project_uid}/stage-chain-batches", operation_id="startStageChainBatch", tags=["comparison"], status_code=201, response_model=models.StageChainBatch,
        responses={**success(201, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def start_batch(project_uid: Annotated[models.ProjectUid, Path()], body: models.StartStageChainBatchRequest, subject: CurrentSubject, idempotency_key: RequiredIdempotencyKey) -> WireResponse:
        result = stage.start_batch(project_uid=project_uid, body=body, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(201, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.get("/stage-chain-batches/{stage_chain_batch_id}", operation_id="getStageChainBatch", tags=["comparison"], status_code=200, response_model=models.StageChainBatch,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def get_batch(stage_chain_batch_id: Annotated[models.StageChainBatchId, Path()]) -> WireResponse:
        result = stage.get_batch(batch_id=stage_chain_batch_id)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.post("/stage-chain-batches/{stage_chain_batch_id}/pause", operation_id="pauseStageChainBatch", tags=["comparison"], status_code=200, response_model=models.StageChainBatch,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def pause_batch(stage_chain_batch_id: Annotated[models.StageChainBatchId, Path()], subject: CurrentSubject, idempotency_key: RequiredIdempotencyKey) -> WireResponse:
        result = stage.pause_batch(batch_id=stage_chain_batch_id, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.post("/stage-chain-batches/{stage_chain_batch_id}/resume", operation_id="resumeStageChainBatch", tags=["comparison"], status_code=200, response_model=models.StageChainBatch,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def resume_batch(stage_chain_batch_id: Annotated[models.StageChainBatchId, Path()], subject: CurrentSubject, idempotency_key: RequiredIdempotencyKey) -> WireResponse:
        result = stage.resume_batch(batch_id=stage_chain_batch_id, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.post("/stage-chain-batches/{stage_chain_batch_id}/cancellation", operation_id="cancelStageChainBatch", tags=["comparison"], status_code=200, response_model=models.StageChainBatch,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def cancel_batch(stage_chain_batch_id: Annotated[models.StageChainBatchId, Path()], subject: CurrentSubject, idempotency_key: RequiredIdempotencyKey) -> WireResponse:
        result = stage.cancel_batch(batch_id=stage_chain_batch_id, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.get("/stage-chain-runs/{stage_chain_run_id}/ai-reviews", operation_id="listStageAiReviews", tags=["comparison"], status_code=200, response_model=models.StageAiReviewPage,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def list_ai_reviews(stage_chain_run_id: Annotated[models.StageChainRunId, Path()], cursor: CursorParam = None, limit: LimitParam = 50) -> WireResponse:
        result = stage.list_ai_reviews(run_id=stage_chain_run_id, cursor=cursor, limit=limit)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.get("/stage-chain-runs/{stage_chain_run_id}/classifications", operation_id="listStageClassifications", tags=["comparison"], status_code=200, response_model=models.StageAiClassificationPage,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def list_classifications(stage_chain_run_id: Annotated[models.StageChainRunId, Path()], cursor: CursorParam = None, limit: LimitParam = 50) -> WireResponse:
        result = stage.list_classifications(run_id=stage_chain_run_id, cursor=cursor, limit=limit)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.get("/stage-chain-runs/{stage_chain_run_id}/synthesis", operation_id="getStageSynthesis", tags=["comparison"], status_code=200, response_model=models.StageAiSynthesisPage,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def get_synthesis(stage_chain_run_id: Annotated[models.StageChainRunId, Path()], cursor: CursorParam = None, limit: LimitParam = 50) -> WireResponse:
        result = stage.get_synthesis(run_id=stage_chain_run_id, cursor=cursor, limit=limit)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.get("/stage-chain-runs/{stage_chain_run_id}/graphic-evidence", operation_id="listStageGraphicEvidence", tags=["comparison"], status_code=200, response_model=models.StageGraphicEvidencePage,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def list_graphics(stage_chain_run_id: Annotated[models.StageChainRunId, Path()], cursor: CursorParam = None, limit: LimitParam = 50) -> WireResponse:
        result = stage.list_graphics(run_id=stage_chain_run_id, cursor=cursor, limit=limit)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.get("/stage-chain-runs/{stage_chain_run_id}/sheet-link-repairs", operation_id="listStageLinkRepairs", tags=["comparison"], status_code=200, response_model=models.StageLinkRepairPage,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def list_repairs(stage_chain_run_id: Annotated[models.StageChainRunId, Path()], cursor: CursorParam = None, limit: LimitParam = 50) -> WireResponse:
        result = stage.list_repairs(run_id=stage_chain_run_id, cursor=cursor, limit=limit)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.post("/stage-link-repairs/{stage_link_repair_id}/undo", operation_id="undoStageLinkRepair", tags=["comparison"], status_code=200, response_model=models.StageLinkRepair,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def undo_repair(stage_link_repair_id: Annotated[models.StageLinkRepairId, Path()], body: models.UndoStageLinkRepairRequest, subject: CurrentSubject, idempotency_key: RequiredIdempotencyKey) -> WireResponse:
        result = stage.undo_repair(repair_id=stage_link_repair_id, body=body, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.get("/stage-chain-runs/{stage_chain_run_id}/cards", operation_id="listStageChangeCards", tags=["comparison"], status_code=200, response_model=models.StageChangeCardPage,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def list_cards(stage_chain_run_id: Annotated[models.StageChainRunId, Path()], cursor: CursorParam = None, limit: LimitParam = 50) -> WireResponse:
        result = stage.list_cards(run_id=stage_chain_run_id, cursor=cursor, limit=limit)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.get("/stage-change-cards/{stage_change_card_id}", operation_id="getStageChangeCard", tags=["comparison"], status_code=200, response_model=models.StageChangeCard,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def get_card(stage_change_card_id: Annotated[models.StageChangeCardId, Path()]) -> WireResponse:
        result = stage.get_card(card_id=stage_change_card_id)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.post("/stage-chain-runs/{stage_chain_run_id}/card-verdicts", operation_id="applyStageCardVerdicts", tags=["comparison"], status_code=200, response_model=models.StageCardVerdictPage,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def apply_verdicts(stage_chain_run_id: Annotated[models.StageChainRunId, Path()], body: models.ApplyStageCardVerdictsRequest, subject: CurrentSubject, idempotency_key: RequiredIdempotencyKey) -> WireResponse:
        result = stage.apply_verdicts(run_id=stage_chain_run_id, body=body, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.get("/stage-change-cards/{stage_change_card_id}/verdicts", operation_id="listStageCardVerdicts", tags=["comparison"], status_code=200, response_model=models.StageCardVerdictPage,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def list_verdicts(stage_change_card_id: Annotated[models.StageChangeCardId, Path()], cursor: CursorParam = None, limit: LimitParam = 50) -> WireResponse:
        result = stage.list_verdicts(card_id=stage_change_card_id, cursor=cursor, limit=limit)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.get("/stage-chain-runs/{stage_chain_run_id}/journal", operation_id="getStageChangeJournal", tags=["comparison"], status_code=200, response_model=models.StageChangeJournal,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def get_journal(stage_chain_run_id: Annotated[models.StageChainRunId, Path()], grouping: Literal["designation", "section", "system"] = "designation") -> WireResponse:
        result = stage.get_journal(run_id=stage_chain_run_id, grouping=grouping)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))

    @router.get("/stage-chain-runs/{stage_chain_run_id}/journal.xlsx", operation_id="streamStageChangeJournalXlsx", tags=["comparison"], status_code=200, response_class=Response,
        responses={**success(200, "Deterministic journal export.", content={"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {"schema": {"type": "string", "format": "binary"}}}), **envelope_responses(401,403,404,409,422,500,503)})
    def journal_xlsx(stage_chain_run_id: Annotated[models.StageChainRunId, Path()]) -> WireResponse:
        content = stage.journal_xlsx(run_id=stage_chain_run_id)
        return WireResponse(200, (("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("Content-Length", str(len(content))), ("Content-Disposition", f'attachment; filename="stage-journal-{stage_chain_run_id}.xlsx"')), content)

    @router.get("/stage-chain-runs/{stage_chain_run_id}/journal.pdf", operation_id="streamStageChangeJournalPdf", tags=["comparison"], status_code=200, response_class=Response,
        responses={**success(200, "Deterministic journal export.", content={"application/pdf": {"schema": {"type": "string", "format": "binary"}}}), **envelope_responses(401,403,404,409,422,500,503)})
    def journal_pdf(stage_chain_run_id: Annotated[models.StageChainRunId, Path()]) -> WireResponse:
        content = stage.journal_pdf(run_id=stage_chain_run_id)
        return WireResponse(200, (("Content-Type", "application/pdf"), ("Content-Length", str(len(content))), ("Content-Disposition", f'attachment; filename="stage-journal-{stage_chain_run_id}.pdf"')), content)

    @router.get("/stage-chain-runs/{stage_chain_run_id}/journal.html", operation_id="streamStageChangeJournalHtml", tags=["comparison"], status_code=200, response_class=Response,
        responses={**success(200, "Deterministic journal export.", content={"text/html": {"schema": {"type": "string", "format": "binary"}}}), **envelope_responses(401,403,404,409,422,500,503)})
    def journal_html(stage_chain_run_id: Annotated[models.StageChainRunId, Path()]) -> WireResponse:
        content = stage.journal_html(run_id=stage_chain_run_id)
        return WireResponse(200, (("Content-Type", "text/html"), ("Content-Length", str(len(content))), ("Content-Disposition", f'attachment; filename="stage-journal-{stage_chain_run_id}.html"')), content)

    @router.get("/comparison-page-profiles/{comparison_page_profile_id}/stage-text", operation_id="getStageProfileText", tags=["comparison"], status_code=200, response_model=models.StageProfileText,
        responses={**success(200, "The frozen stage result or keyed replay."), **envelope_responses(401,403,404,409,422,500,503)})
    def get_profile_text(comparison_page_profile_id: Annotated[models.ComparisonPageProfileId, Path()], query: Annotated[str, Query(max_length=200)] = "") -> WireResponse:
        result = stage.get_profile_text(profile_id=comparison_page_profile_id, query=query)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))


    @router.get("/stage-assemblies/{stage_assembly_id}", operation_id="getStageAssembly", tags=["comparison"], response_model=models.StageAssembly,
        responses={**success(200, "The persisted assembly membership and revision base."), **envelope_responses(401,403,404,422,500,503)})
    def get_assembly(stage_assembly_id: Annotated[models.StageAssemblyId, Path()]) -> WireResponse:
        result = stage.get_assembly(assembly_id=stage_assembly_id)
        return json_response(200, encode_json(result.model_dump(mode="json", exclude_unset=True)))
