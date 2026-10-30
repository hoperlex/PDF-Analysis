"""Composition factories: construct without I/O, bind models only in the worker."""

from auditmanager.comparison.stage_ai.runtime import StageAiRuntime
from auditmanager.comparison.stage_repair.service import StageRepairService
from auditmanager.comparison.stage_review.service import StageReviewService
from auditmanager.comparison.work.model import WorkDependencies

from .batch import StageBatchHandler
from .handler import StageChainHandler


def stage_chain_handler(dependencies: WorkDependencies) -> StageChainHandler:
    from auditmanager.comparison.stage_graphic.service import StageGraphicService

    sessions = getattr(dependencies, "session_factory", None)
    return StageChainHandler(
        dependencies,
        ai=StageAiRuntime(sessions, blob_store=getattr(dependencies, "blob_store", None), routes=getattr(dependencies, "routes", None),
            graphic_source=StageGraphicService(sessions, blob_store=getattr(dependencies, "blob_store", None))),
        repair=StageRepairService(sessions), review=StageReviewService(sessions),
        graphics=StageGraphicService(sessions, blob_store=getattr(dependencies, "blob_store", None)),
    )


def stage_chain_batch_handler(dependencies: WorkDependencies) -> StageBatchHandler:
    from auditmanager.comparison.stage_graphic.service import StageGraphicService

    return StageBatchHandler(dependencies, ai=StageAiRuntime(
        getattr(dependencies, "session_factory", None), blob_store=getattr(dependencies, "blob_store", None), routes=getattr(dependencies, "routes", None),
        graphic_source=StageGraphicService(getattr(dependencies, "session_factory", None), blob_store=getattr(dependencies, "blob_store", None)),
    ))
