"""`W49-SEAL-01b` -- the seam's registers, swept against the served application.

`W49-PLAN.md` section 3.2: three registers and one map in ``auditmanager.api.security`` say
what an account may reach, and a request meets them in a fixed order -- signature and expiry,
the standing (archived or stale is ``authentication_required``), the default credential, the
incomplete profile, the role set. This module is the sweep the plan requires: **for every
guarded operation x every role set in {none, expert, admin, expert+admin} x {complete,
incomplete} x {default, changed}, the served application's answer equals what the registers
say.**

Three properties keep the sweep from being a tautology:

* **the registers themselves are pinned as literals** (:data:`EXPECTED_ROLES` and the three
  sets in :func:`test_the_registers_are_the_ruled_ones`), written from `R-60`'s groups and
  never read back out of the module under test, so a register that drifted fails here even
  though the seam and the sweep would still agree with each other;
* **the expected answer is computed by this module, from the plan's order**, not by calling
  the seam: :func:`_expected` is a second, independent statement of section 3.2;
* **the observed answer is classified by the envelope the seam writes** -- ``403``,
  ``permission_denied``, ``required_capability`` -- and every port behind the operations
  answers a refusal of another kind (``driver.SuiteAccountAdapter``), so a ``403`` here is
  the seam's and nothing else's.
"""

from __future__ import annotations

import itertools
import json

import pytest

from auditmanager.api.security import (
    ENROLLMENT_OPERATIONS,
    OPERATION_ROLES,
    OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES,
    OPERATIONS_AN_INCOMPLETE_PROFILE_REACHES,
    ROLES_OF_A_ROUTE_WITHOUT_AN_OPERATION,
    RUNNER_OPERATIONS,
    UNAUTHENTICATED_OPERATIONS,
)
from w13_api_driver import Request, Surface, dispatch

#: One request per guarded operation, shaped so that whatever the seam lets through is
#: refused by the operation itself (its body model, or a stand-in port) and never by a 403.
SAMPLES: dict[str, tuple[str, str]] = {
    "createProject": ("POST", "/projects"),
    "listProjects": ("GET", "/projects"),
    "uploadDocument": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents"),
    # `W59-VERSION-UPLOAD-01`. The next version of a document, addressed through its project.
    "uploadDocumentVersion": (
        "POST",
        "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H"
        "/versions",
    ),
    "listDocuments": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents"),
    "getDocumentVersion": ("GET", "/versions/ver_01M2545JSD15ETSNNV904X991J"),
    "streamDocumentVersionContent": ("GET", "/versions/ver_01M2545JSD15ETSNNV904X991J/content"),
    "getVersionBlocks": ("GET", "/versions/ver_01M2545JSD15ETSNNV904X991J/blocks"),
    "listRuns": ("GET", "/versions/ver_01M2545JSD15ETSNNV904X991J/runs"),
    "listVersions": ("GET", "/documents/doc_01M2545JSD15ETSNNV904X991H/versions"),
    "startRun": ("POST", "/runs"),
    "getRunStatus": ("GET", "/runs/run_01M2545JSD15ETSNNV904X991K"),
    "startArV3BetaGroup": ("POST", "/ar-v3-beta/groups"),
    "getArV3BetaGroup": ("GET", "/ar-v3-beta/groups/arg_01M2545JSD15ETSNNV904X991K"),
    "getArV3BetaGroupReview": (
        "GET", "/ar-v3-beta/groups/arg_01M2545JSD15ETSNNV904X991K/review",
    ),
    "getArV3BetaPackStatus": ("GET", "/ar-v3-beta/pack"),
    "getRunNormVerification": (
        "GET", "/runs/run_01M2545JSD15ETSNNV904X991K/norm-verification"
    ),
    "listExecutionQueue": ("GET", "/execution/queue"),
    "listExecutionJournal": ("GET", "/execution/journal"),
    "cancelRun": ("POST", "/runs/run_01M2545JSD15ETSNNV904X991K/cancel"),
    "reauditRun": ("POST", "/runs/run_01M2545JSD15ETSNNV904X991K/reaudit"),
    "startRunFromStage": ("POST", "/runs/run_01M2545JSD15ETSNNV904X991K/start-from-stage"),
    "setJobPriority": ("PUT", "/execution/queue/job_01M2545JSD15ETSNNV904X991T/priority"),
    "setExecutionPaused": ("PUT", "/execution/dispatch"),
    "getExecutionDispatch": ("GET", "/execution/dispatch"),
    "setDocumentArchived": ("PUT", "/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/documents/doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/archive"),
    "renameDocument": ("PUT", "/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/documents/doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/title"),
    "setDocumentTags": ("PUT", "/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/documents/doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/tags"),
    "listDocumentTags": ("GET", "/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/document-tags"),
    "setFindingExecutionStatus": ("PUT", "/findings/fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/execution-status"),
    "listProposalDecisionJournal": ("GET", "/proposal-decisions"),
    "listKnowledgeBaseEntries": ("GET", "/knowledge-base/entries"),
    "listAcceptedOptimisationProposals": ("GET", "/optimisation-proposals/accepted"),
    "exportOptimisationProposalsXlsx": ("GET", "/optimisation-passes/opp_01M2545JSD15ETSNNV904X991N/export.xlsx"),
    "importOptimisationProposalDecisions": ("POST", "/optimisation-passes/opp_01M2545JSD15ETSNNV904X991N/decision-imports"),
    "carryOverProposalDecisions": ("POST", "/optimisation-passes/opp_01M2545JSD15ETSNNV904X991N/decision-carryovers"),
    "listDecisionMemoryCases": ("GET", "/decision-memory/cases"),
    "getDecisionMemoryCase": ("GET", "/decision-memory/cases/dmc_01M2545JSD15ETSNNV904X991N"),
    "getDecisionMemoryStatus": ("GET", "/decision-memory/status"),
    "withdrawDecisionMemoryCase": ("POST", "/decision-memory/cases/dmc_01M2545JSD15ETSNNV904X991N/withdraw"),
    "restoreDecisionMemoryCase": ("POST", "/decision-memory/cases/dmc_01M2545JSD15ETSNNV904X991N/restore"),
    # `HOSTS-SEAL-1` (contract 1.45.0).
    "listExecutorHosts": ("GET", "/executor-hosts"),
    "getExecutorHost": ("GET", "/executor-hosts/exh_01M2545JSD15ETSNNV904X991N"),
    "getExecutorHostDetails": ("GET", "/executor-hosts/exh_01M2545JSD15ETSNNV904X991N/details"),
    "setExecutorHostEnabled": ("PUT", "/executor-hosts/exh_01M2545JSD15ETSNNV904X991N/enabled"),
    "setExecutorHostSlots": ("PUT", "/executor-hosts/exh_01M2545JSD15ETSNNV904X991N/slots"),
    "archiveExecutorHost": ("POST", "/executor-hosts/exh_01M2545JSD15ETSNNV904X991N/archive"),
    "issueExecutorHostEnrollment": ("POST", "/executor-hosts/enrollments"),
    "createExecutorHostAgentInstall": ("POST", "/executor-hosts/agent-installs"),
    "getExecutorHostAgentInstall": ("GET", "/executor-hosts/exh_01M2545JSD15ETSNNV904X991N/agent-installs/exai_01M2545JSD15ETSNNV904X991N"),
    "confirmExecutorHostAgentInstallHostKey": ("POST", "/executor-hosts/exh_01M2545JSD15ETSNNV904X991N/agent-installs/exai_01M2545JSD15ETSNNV904X991N/confirm-host-key"),
    "getStageModelLayout": ("GET", "/model-layout"),
    "reviseStageModelLayout": ("POST", "/model-layout/revisions"),
    "setStageModelLayoutEnabled": ("PUT", "/model-layout/enabled"),
    "listModelCatalogue": ("GET", "/model-catalogue"),
    "getRunStartReadiness": ("POST", "/runs/start-readiness"),
    "importRunDecisions": ("POST", "/runs/run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/decision-imports"),
    "getProject": ("GET", "/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B"),
    "listVersionSheetLabels": ("GET", "/versions/ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/sheet-labels"),
    "listRunFindingBlocks": ("GET", "/runs/run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/finding-blocks"),
    "getWorkSchedule": ("GET", "/work-schedule?month=2026-11"),
    "getWorkScheduleReserve": ("GET", "/work-schedule/reserve?start=2026-11-02"),
    "setWorkScheduleSettings": ("PUT", "/work-schedule/settings"),
    "setWorkSchedulePlans": ("PUT", "/work-schedule/plans"),
    "setWorkCalendarDays": ("PUT", "/work-calendar/days"),
    "setEngineerAbsences": ("PUT", "/work-schedule/absences"),
    "scheduleAssignments": ("POST", "/work-schedule/reserve/moves"),
    # `W54-SEAL-01`. The worker registry (R-80 any-role read, administrator intake).
    "listWorkers": ("GET", "/execution/workers"),
    "setWorkerIntake": ("PUT", "/execution/workers/wrk_01M2545JSD15ETSNNV904X991T/intake"),
    # `EXEC-SEAL-01`. The executor connections (R-80 any-role reads; administrator writes).
    "listExecutorConnections": ("GET", "/executor-connections"),
    "createExecutorConnection": ("POST", "/executor-connections"),
    "getExecutorConnection": ("GET", "/executor-connections/exc_01M2545JSD15ETSNNV904X991T"),
    "reviseExecutorConnection": (
        "POST", "/executor-connections/exc_01M2545JSD15ETSNNV904X991T/revisions"
    ),
    "archiveExecutorConnection": (
        "POST", "/executor-connections/exc_01M2545JSD15ETSNNV904X991T/archive"
    ),
    "setExecutorSecret": ("POST", "/executor-connections/exc_01M2545JSD15ETSNNV904X991T/secrets"),
    "generateExecutorSshKey": (
        "POST", "/executor-connections/exc_01M2545JSD15ETSNNV904X991T/ssh-key"
    ),
    "requestExecutorProbe": (
        "POST", "/executor-connections/exc_01M2545JSD15ETSNNV904X991T/probes"
    ),
    "listExecutorRoutes": ("GET", "/executor-routes"),
    "setExecutorRoute": ("PUT", "/executor-routes"),
    # `ANALYSIS-PRESETS-01`. The presets: reads for any role, writes for an administrator.
    "listAnalysisPresets": ("GET", "/analysis/presets"),
    "createAnalysisPreset": ("POST", "/analysis/presets"),
    "reviseAnalysisPreset": ("POST", "/analysis/presets/evt_01M2545JSD15ETSNNV904X991T/revisions"),
    "archiveAnalysisPreset": ("POST", "/analysis/presets/evt_01M2545JSD15ETSNNV904X991T/archive"),
    # `CMP-SEAL-C0` (ADR-0025). The comparison modules: reads for any role, every write an expert's act.
    "createComparisonUpload": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/comparison-uploads"),
    "listComparisonUploads": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/comparison-uploads"),
    "getComparisonUpload": ("GET", "/comparison-uploads/cbt_01M2545JSD15ETSNNV904X991K"),
    "getComparisonUploadProposal": ("GET", "/comparison-uploads/cbt_01M2545JSD15ETSNNV904X991K/proposal"),
    "uploadComparisonUploadPart": ("PUT", "/comparison-uploads/cbt_01M2545JSD15ETSNNV904X991K/files/cuf_01M2545JSD15ETSNNV904X991K/parts"),
    "completeComparisonUploadFile": ("POST", "/comparison-uploads/cbt_01M2545JSD15ETSNNV904X991K/files/cuf_01M2545JSD15ETSNNV904X991K/completion"),
    "confirmComparisonUploadSet": ("POST", "/comparison-uploads/cbt_01M2545JSD15ETSNNV904X991K/sets/cus_01M2545JSD15ETSNNV904X991K/confirmation"),
    "excludeComparisonUploadSet": ("POST", "/comparison-uploads/cbt_01M2545JSD15ETSNNV904X991K/sets/cus_01M2545JSD15ETSNNV904X991K/exclusion"),
    "retryComparisonUploadSet": ("POST", "/comparison-uploads/cbt_01M2545JSD15ETSNNV904X991K/sets/cus_01M2545JSD15ETSNNV904X991K/retry"),
    "pauseComparisonUpload": ("POST", "/comparison-uploads/cbt_01M2545JSD15ETSNNV904X991K/pause"),
    "resumeComparisonUpload": ("POST", "/comparison-uploads/cbt_01M2545JSD15ETSNNV904X991K/resume"),
    "cancelComparisonUpload": ("POST", "/comparison-uploads/cbt_01M2545JSD15ETSNNV904X991K/cancellation"),
    "listComparisonVersionOrders": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H/comparison-version-orders"),
    "appendComparisonVersionOrder": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H/comparison-version-orders"),
    "listVersionPageProfiles": ("GET", "/versions/ver_01M2545JSD15ETSNNV904X991J/page-profiles"),
    "getVersionPageProfile": ("GET", "/page-profiles/cpr_01M2545JSD15ETSNNV904X991K"),
    "streamVersionPagePreview": ("GET", "/page-profiles/cpr_01M2545JSD15ETSNNV904X991K/preview"),
    "streamVersionPageThumbnail": ("GET", "/page-profiles/cpr_01M2545JSD15ETSNNV904X991K/thumbnail"),
    "streamVersionPageTile": ("GET", "/page-profiles/cpr_01M2545JSD15ETSNNV904X991K/tile"),
    # `CMP-SEAL-C1`. The version comparison core.
    "getComparisonMatrix": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H/comparison-matrix"),
    "prepareComparisonMatrix": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H/comparison-matrix/preparation"),
    "listComparisonMatrixEdits": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H/comparison-matrix/edits"),
    "applyComparisonMatrixEdits": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H/comparison-matrix/edits"),
    "undoComparisonMatrixEdit": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H/comparison-matrix/edits/undo"),
    "listComparisonAiLinks": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H/comparison-ai-links"),
    "startComparisonSeries": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H/comparison-series"),
    "listComparisonSeries": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H/comparison-series"),
    "getComparisonSeries": ("GET", "/comparison-series/cser_01M2545JSD15ETSNNV904X991K"),
    "pauseComparisonSeries": ("POST", "/comparison-series/cser_01M2545JSD15ETSNNV904X991K/pause"),
    "resumeComparisonSeries": ("POST", "/comparison-series/cser_01M2545JSD15ETSNNV904X991K/resume"),
    "cancelComparisonSeries": ("POST", "/comparison-series/cser_01M2545JSD15ETSNNV904X991K/cancellation"),
    "finishComparisonSeries": ("POST", "/comparison-series/cser_01M2545JSD15ETSNNV904X991K/finish"),
    "listComparisonSheetPairs": ("GET", "/comparison-transitions/ctn_01M2545JSD15ETSNNV904X991K/sheet-pairs"),
    "getComparisonSheetPair": ("GET", "/comparison-sheet-pairs/ctp_01M2545JSD15ETSNNV904X991K"),
    "streamComparisonPairTile": ("GET", "/comparison-sheet-pairs/ctp_01M2545JSD15ETSNNV904X991K/tile"),
    "getComparisonOverview": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/comparison-overview"),
    "getComparisonQueueSummary": ("GET", "/execution/comparison-queue"),
    # `CMP-SEAL-C2`. The version comparison AI, specifications, launch queue and reports.
    "estimateComparisonAiPairCheck": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H/comparison-ai-pair-check/estimate"),
    "getComparisonAiPairCheck": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H/comparison-ai-pair-check"),
    "startComparisonAiPairCheck": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H/comparison-ai-pair-check"),
    "pauseComparisonAiPairCheck": ("POST", "/comparison-ai-pair-checks/cai_01M2545JSD15ETSNNV904X991K/pause"),
    "resumeComparisonAiPairCheck": ("POST", "/comparison-ai-pair-checks/cai_01M2545JSD15ETSNNV904X991K/resume"),
    "cancelComparisonAiPairCheck": ("POST", "/comparison-ai-pair-checks/cai_01M2545JSD15ETSNNV904X991K/cancellation"),
    "listComparisonAiPairHints": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H/comparison-ai-pair-hints"),
    "estimateComparisonAiSheetChanges": ("GET", "/comparison-series/cser_01M2545JSD15ETSNNV904X991K/ai-sheet-changes/estimate"),
    "getComparisonAiSheetChanges": ("GET", "/comparison-series/cser_01M2545JSD15ETSNNV904X991K/ai-sheet-changes"),
    "startComparisonAiSheetChanges": ("POST", "/comparison-series/cser_01M2545JSD15ETSNNV904X991K/ai-sheet-changes"),
    "pauseComparisonAiSheetChanges": ("POST", "/comparison-ai-sheet-jobs/cai_01M2545JSD15ETSNNV904X991K/pause"),
    "resumeComparisonAiSheetChanges": ("POST", "/comparison-ai-sheet-jobs/cai_01M2545JSD15ETSNNV904X991K/resume"),
    "cancelComparisonAiSheetChanges": ("POST", "/comparison-ai-sheet-jobs/cai_01M2545JSD15ETSNNV904X991K/cancellation"),
    "finishComparisonAiSheetChanges": ("POST", "/comparison-ai-sheet-jobs/cai_01M2545JSD15ETSNNV904X991K/finish"),
    "dequeueComparisonAiSheetChanges": ("POST", "/comparison-ai-sheet-jobs/cai_01M2545JSD15ETSNNV904X991K/dequeue"),
    "retryComparisonAiSheetChanges": ("POST", "/comparison-ai-sheet-jobs/cai_01M2545JSD15ETSNNV904X991K/retry"),
    "getComparisonSheetDescription": ("GET", "/comparison-sheet-pairs/ctp_01M2545JSD15ETSNNV904X991K/description"),
    "startComparisonSheetDescription": ("POST", "/comparison-sheet-pairs/ctp_01M2545JSD15ETSNNV904X991K/description"),
    "listComparisonSheetDescriptionHistory": ("GET", "/comparison-sheet-pairs/ctp_01M2545JSD15ETSNNV904X991K/description-history"),
    "estimateComparisonSheetDescription": ("GET", "/comparison-sheet-pairs/ctp_01M2545JSD15ETSNNV904X991K/description/estimate"),
    "streamComparisonSheetDescriptionMd": ("GET", "/comparison-sheet-pairs/ctp_01M2545JSD15ETSNNV904X991K/description/md"),
    "listComparisonReviewSheets": ("GET", "/comparison-transitions/ctn_01M2545JSD15ETSNNV904X991K/review-sheets"),
    "getVersionPageSpecPositions": ("GET", "/page-profiles/cpr_01M2545JSD15ETSNNV904X991K/spec-positions"),
    "getComparisonSheetPairSpecPositions": ("GET", "/comparison-sheet-pairs/ctp_01M2545JSD15ETSNNV904X991K/spec-positions"),
    "listComparisonSpecifications": ("GET", "/comparison-series/cser_01M2545JSD15ETSNNV904X991K/specifications"),
    "getComparisonSpecification": ("GET", "/comparison-transitions/ctn_01M2545JSD15ETSNNV904X991K/specification"),
    "startComparisonSpecification": ("POST", "/comparison-transitions/ctn_01M2545JSD15ETSNNV904X991K/specification"),
    "listComparisonSpecificationChanges": ("GET", "/comparison-transitions/ctn_01M2545JSD15ETSNNV904X991K/specification/changes"),
    "estimateComparisonSpecification": ("GET", "/comparison-transitions/ctn_01M2545JSD15ETSNNV904X991K/specification/estimate"),
    "cancelComparisonSpecification": ("POST", "/comparison-ai-spec-jobs/cai_01M2545JSD15ETSNNV904X991K/cancellation"),
    "getComparisonLaunchQueue": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/comparison-launch-queue"),
    "enqueueComparisonLaunch": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/comparison-launch-queue/entries"),
    "pauseComparisonLaunchQueue": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/comparison-launch-queue/pause"),
    "resumeComparisonLaunchQueue": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/comparison-launch-queue/resume"),
    "clearComparisonLaunchQueue": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/comparison-launch-queue/clear"),
    "removeComparisonLaunchEntry": ("POST", "/comparison-launch-entries/cle_01M2545JSD15ETSNNV904X991K/removal"),
    "getComparisonAiQueue": ("GET", "/execution/comparison-ai-queue"),
    "streamComparisonSeriesSummary": ("GET", "/comparison-series/cser_01M2545JSD15ETSNNV904X991K/summary-md"),
    "listComparisonReports": ("GET", "/comparison-series/cser_01M2545JSD15ETSNNV904X991K/reports"),
    "createComparisonReport": ("POST", "/comparison-series/cser_01M2545JSD15ETSNNV904X991K/reports"),
    "uploadComparisonReportSource": ("POST", "/comparison-series/cser_01M2545JSD15ETSNNV904X991K/reports/upload"),
    "getComparisonReport": ("GET", "/comparison-reports/crt_01M2545JSD15ETSNNV904X991K"),
    "startComparisonReport": ("POST", "/comparison-reports/crt_01M2545JSD15ETSNNV904X991K/start"),
    "cancelComparisonReport": ("POST", "/comparison-reports/crt_01M2545JSD15ETSNNV904X991K/cancellation"),
    "continueComparisonReport": ("POST", "/comparison-reports/crt_01M2545JSD15ETSNNV904X991K/continuation"),
    "rebuildComparisonReportPdf": ("POST", "/comparison-reports/crt_01M2545JSD15ETSNNV904X991K/pdf-rebuild"),
    "deleteComparisonReport": ("POST", "/comparison-reports/crt_01M2545JSD15ETSNNV904X991K/deletion"),
    "prepareComparisonClientReport": ("POST", "/comparison-reports/crt_01M2545JSD15ETSNNV904X991K/client-report"),
    "streamComparisonReportPdf": ("GET", "/comparison-reports/crt_01M2545JSD15ETSNNV904X991K/pdf"),
    "streamComparisonReportSourceMd": ("GET", "/comparison-reports/crt_01M2545JSD15ETSNNV904X991K/source-md"),
    # `CMP-SEAL-C3`: sixteen reads for any role and sixteen keyed expert writes.
    "createStageAssembly": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991K/stage-assemblies"),
    "listStagePairSuggestions": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991K/stage-pair-suggestions"),
    "listStagePairs": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991K/stage-pairs"),
    "confirmStagePair": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991K/stage-pairs"),
    "listStageUploads": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991K/stage-uploads"),
    "createStageUpload": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991K/stage-uploads"),
    "reviseStageAssembly": ("POST", "/stage-assemblies/sas_01M2545JSD15ETSNNV904X991K/members"),
    "getStageChainRun": ("GET", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K"),
    "cancelStageChainRun": ("POST", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K/cancellation"),
    "getStageSheetMapRevision": ("GET", "/stage-link-revisions/slk_01M2545JSD15ETSNNV904X991K"),
    "listStageRawDifferences": ("GET", "/stage-link-revisions/slk_01M2545JSD15ETSNNV904X991K/raw-differences"),
    "recomputeStageTextEvidence": ("POST", "/stage-link-revisions/slk_01M2545JSD15ETSNNV904X991K/text-evidence/recomputation"),
    "listStageTextExclusions": ("GET", "/stage-link-revisions/slk_01M2545JSD15ETSNNV904X991K/text-exclusions"),
    "listStageTextHints": ("GET", "/stage-link-revisions/slk_01M2545JSD15ETSNNV904X991K/text-hints"),
    "getStagePair": ("GET", "/stage-pairs/stp_01M2545JSD15ETSNNV904X991K"),
    "listStageChainRuns": ("GET", "/stage-pairs/stp_01M2545JSD15ETSNNV904X991K/chain-runs"),
    "startStageChainRun": ("POST", "/stage-pairs/stp_01M2545JSD15ETSNNV904X991K/chain-runs"),
    "setStagePairCompleteness": ("POST", "/stage-pairs/stp_01M2545JSD15ETSNNV904X991K/completeness"),
    "getStageSheetMap": ("GET", "/stage-pairs/stp_01M2545JSD15ETSNNV904X991K/sheet-map"),
    "applyStageSheetMap": ("POST", "/stage-pairs/stp_01M2545JSD15ETSNNV904X991K/sheet-map"),
    "listStageSheetMapHistory": ("GET", "/stage-pairs/stp_01M2545JSD15ETSNNV904X991K/sheet-map/revisions"),
    "listStageSheetPassports": ("GET", "/stage-pairs/stp_01M2545JSD15ETSNNV904X991K/sheet-passports"),
    "listStageSheetSuggestions": ("GET", "/stage-pairs/stp_01M2545JSD15ETSNNV904X991K/sheet-suggestions"),
    "listStageTextFragments": ("GET", "/stage-pairs/stp_01M2545JSD15ETSNNV904X991K/text-fragments"),
    "confirmStageUploadCandidate": ("POST", "/stage-upload-candidates/suc_01M2545JSD15ETSNNV904X991K/confirmation"),
    "rejectStageUploadCandidate": ("POST", "/stage-upload-candidates/suc_01M2545JSD15ETSNNV904X991K/rejection"),
    "getStageUpload": ("GET", "/stage-uploads/stu_01M2545JSD15ETSNNV904X991K"),
    "cancelStageUpload": ("POST", "/stage-uploads/stu_01M2545JSD15ETSNNV904X991K/cancellation"),
    "completeStageUploadFile": ("POST", "/stage-uploads/stu_01M2545JSD15ETSNNV904X991K/files/suf_01M2545JSD15ETSNNV904X991K/completion"),
    "uploadStageUploadPart": ("PUT", "/stage-uploads/stu_01M2545JSD15ETSNNV904X991K/files/suf_01M2545JSD15ETSNNV904X991K/parts"),
    "pauseStageUpload": ("POST", "/stage-uploads/stu_01M2545JSD15ETSNNV904X991K/pause"),
    "resumeStageUpload": ("POST", "/stage-uploads/stu_01M2545JSD15ETSNNV904X991K/resume"),
    # `CMP-SEAL-C4` and `BETA-COST-PREFLIGHT-1030` (1.13.0), `HOTFIX-PRESENTATION-INT-1030` (1.14.0): the operations this
    # sweep had not yet been shown.
    "estimateStageChainRun": ("GET", "/stage-link-revisions/slk_01M2545JSD15ETSNNV904X991K/chain-estimate"),
    "getStageChainBatch": ("GET", "/stage-chain-batches/scb_01M2545JSD15ETSNNV904X991K"),
    "listStageAiReviews": ("GET", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K/ai-reviews"),
    "listStageClassifications": ("GET", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K/classifications"),
    "getStageSynthesis": ("GET", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K/synthesis"),
    "listStageGraphicEvidence": ("GET", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K/graphic-evidence"),
    "listStageLinkRepairs": ("GET", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K/sheet-link-repairs"),
    "listStageChangeCards": ("GET", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K/cards"),
    "getStageChangeCard": ("GET", "/stage-change-cards/ccd_01M2545JSD15ETSNNV904X991K"),
    "listStageCardVerdicts": ("GET", "/stage-change-cards/ccd_01M2545JSD15ETSNNV904X991K/verdicts"),
    "getStageChangeJournal": ("GET", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K/journal"),
    "streamStageChangeJournalXlsx": ("GET", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K/journal.xlsx"),
    "streamStageChangeJournalPdf": ("GET", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K/journal.pdf"),
    "streamStageChangeJournalHtml": ("GET", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K/journal.html"),
    "getStageProfileText": ("GET", "/comparison-page-profiles/cpr_01M2545JSD15ETSNNV904X991K/stage-text"),
    "getStageAssembly": ("GET", "/stage-assemblies/sas_01M2545JSD15ETSNNV904X991K"),
    "resumeStageChainRun": ("POST", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K/resume"),
    "startStageChainBatch": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991K/stage-chain-batches"),
    "pauseStageChainBatch": ("POST", "/stage-chain-batches/scb_01M2545JSD15ETSNNV904X991K/pause"),
    "resumeStageChainBatch": ("POST", "/stage-chain-batches/scb_01M2545JSD15ETSNNV904X991K/resume"),
    "cancelStageChainBatch": ("POST", "/stage-chain-batches/scb_01M2545JSD15ETSNNV904X991K/cancellation"),
    "undoStageLinkRepair": ("POST", "/stage-link-repairs/crp_01M2545JSD15ETSNNV904X991K/undo"),
    "applyStageCardVerdicts": ("POST", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K/card-verdicts"),
    "createStageReviewCard": ("POST", "/stage-chain-runs/crn_01M2545JSD15ETSNNV904X991K/review-cards"),
    "getExtendedRunReview": ("GET", "/runs/run_01M2545JSD15ETSNNV904X991K/extended-review"),
    "streamComparisonTechnicalReport": ("GET", "/comparison-series/cser_01M2545JSD15ETSNNV904X991K/technical-report"),
    "estimateRunCost": ("POST", "/runs/cost-estimate"),
    "estimateArV3GroupCost": ("POST", "/ar-v3-beta/groups/cost-estimate"),
    "importComparisonZip": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991K/comparison-zip-uploads"),
    # `EXEC-PULL-01`. Runner tokens are an administrator's (the runner's own four operations
    # are not role-gated: they are authenticated by the token, see RUNNER_OPERATIONS).
    "issueRunnerToken": (
        "POST", "/executor-connections/exc_01M2545JSD15ETSNNV904X991T/runner-tokens"
    ),
    "revokeRunnerToken": (
        "POST",
        "/executor-connections/exc_01M2545JSD15ETSNNV904X991T/runner-tokens/"
        "ern_01M2545JSD15ETSNNV904X991T/revoke",
    ),
    # `EXEC2-SEAL-1`. The universal agent: the grant, the SSH install session and the
    # integration-authorisation mark are an administrator's. The agent's own operations
    # (`reportRunnerHealth`, `redeemExecutorEnrollment`, `downloadAgentPackage`) are not role-gated.
    "issueExecutorEnrollment": (
        "POST", "/executor-connections/exc_01M2545JSD15ETSNNV904X991T/enrollments"
    ),
    "setExecutorIntegrationAuthorisation": (
        "POST", "/executor-connections/exc_01M2545JSD15ETSNNV904X991T/integration-authorisation"
    ),
    "createExecutorAgentInstall": (
        "POST", "/executor-connections/exc_01M2545JSD15ETSNNV904X991T/agent-installs"
    ),
    "getExecutorAgentInstall": (
        "GET",
        "/executor-connections/exc_01M2545JSD15ETSNNV904X991T/agent-installs/"
        "exai_01M2545JSD15ETSNNV904X991T",
    ),
    "confirmExecutorAgentInstallHostKey": (
        "POST",
        "/executor-connections/exc_01M2545JSD15ETSNNV904X991T/agent-installs/"
        "exai_01M2545JSD15ETSNNV904X991T/confirm-host-key",
    ),
    # `EXEC2-SEAL-2`, `EXEC2-GROUP-STORE-01`. Executor groups, the routing rule of a work kind and the routing mode: the
    # four reads of the group store are any role's, the writes, the cut-over preview and the routing mode an administrator's.
    "listExecutorGroups": ("GET", "/executor-groups"),
    "createExecutorGroup": ("POST", "/executor-groups"),
    "getExecutorGroup": ("GET", "/executor-groups/exg_01M2545JSD15ETSNNV904X991T"),
    "reviseExecutorGroup": ("POST", "/executor-groups/exg_01M2545JSD15ETSNNV904X991T/revisions"),
    "archiveExecutorGroup": ("POST", "/executor-groups/exg_01M2545JSD15ETSNNV904X991T/archive"),
    "getExecutorGroupCapacity": ("GET", "/executor-groups/exg_01M2545JSD15ETSNNV904X991T/capacity"),
    "listExecutorRoutingRules": ("GET", "/executor-routing-rules"),
    "setExecutorRoutingRule": ("PUT", "/executor-routing-rules/text_analysis"),
    "previewExecutorRouting": ("GET", "/executor-routing/preview"),
    "setExecutorRoutingMode": ("POST", "/executor-routing/mode"),
    # `W55A-SEAL-01`. The norms operations (R-80 any-role reads; R-113 administrator history
    # and designation). `q` is supplied so the role refusal is the only one in play.
    "searchNorms": ("GET", "/norms/search?q=gost"),
    "getNormDocument": ("GET", "/norm-documents/ndoc_01M2545JSD15ETSNNV904X991V"),
    "listNormParagraphs": ("GET", "/norm-documents/ndoc_01M2545JSD15ETSNNV904X991V/paragraphs"),
    "streamNormDocumentContent": ("GET", "/norm-documents/ndoc_01M2545JSD15ETSNNV904X991V/content"),
    "listNormSnapshots": ("GET", "/norms/snapshots"),
    "listNormSnapshotEvents": ("GET", "/norms/snapshots/events"),
    "setCurrentNormSnapshot": ("PUT", "/norms/snapshots/current"),
    # `W55B-SEAL-01`. The portal-block reads (R-80 any-role reads).
    "listVersionPortalBlocks": ("GET", "/versions/ver_01M2545JSD15ETSNNV904X991J/portal-blocks"),
    "streamVersionPortalBlockCrop": (
        "GET",
        "/versions/ver_01M2545JSD15ETSNNV904X991J/portal-blocks/blk_00000000000000000000000000000000/crop",
    ),
    # `W59-SECTION-SEAL-01`. The classification (expert) and the section review (any role),
    # addressed through the version's document and project. The empty body is refused by
    # the classification's own body model.
    "classifyDocumentVersion": (
        "PUT",
        "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H"
        "/versions/ver_01M2545JSD15ETSNNV904X991J/classification",
    ),
    # `CLASSIFICATION-CORRECTION-01`. The correction is an expert's write on the same chain.
    "correctVersionClassification": (
        "POST",
        "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H"
        "/versions/ver_01M2545JSD15ETSNNV904X991J/classification/corrections",
    ),
    "getVersionSectionReview": (
        "GET",
        "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H"
        "/versions/ver_01M2545JSD15ETSNNV904X991J/section-review",
    ),
    # `W59-VERSION-COMPARE-01`. Two versions of one set compared (any role), addressed the
    # same way; the required ``target_version_uid`` is given so only the role decides.
    "compareDocumentVersions": (
        "GET",
        "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H"
        "/versions/ver_01M2545JSD15ETSNNV904X991J/comparison"
        "?target_version_uid=ver_01M2545JSD15ETSNNV904X991K",
    ),
    # `W59-DECISION-CARRYOVER-01`. The expert's carryover of a decision, addressed the same
    # way; the missing body is refused by the body model only after the role decided.
    "carryOverDecision": (
        "POST",
        "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H"
        "/versions/ver_01M2545JSD15ETSNNV904X991J/comparison/carryovers",
    ),
    # `COMPARE-PERSISTED-SUMMARY-01`. The expert's approval and withdrawal of a sheet pairing,
    # addressed the same way; a missing body is refused by the body model only after the role decided.
    "approveSheetPairing": (
        "POST",
        "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H"
        "/versions/ver_01M2545JSD15ETSNNV904X991J/comparison/sheet-pairings",
    ),
    "withdrawSheetPairing": (
        "POST",
        "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H"
        "/versions/ver_01M2545JSD15ETSNNV904X991J/comparison/sheet-pairings"
        "/sln_01M2545JSD15ETSNNV904X991M/withdrawals",
    ),
    # `COMPARE-PERSISTED-SUMMARY-01` (B2). The only operation that calls a model about a comparison.
    "generateComparisonSummary": (
        "POST",
        "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H"
        "/versions/ver_01M2545JSD15ETSNNV904X991J/comparison/summaries",
    ),
    # `W59-ANALYSIS-SETTINGS-01`. The text-profile registry (any role); no parameter.
    "listAnalysisProfiles": ("GET", "/analysis/profiles"),
    # `W61-DISPATCHER-01`. «Диспетчер»: creating (admin) and listing, reading and moving
    # (any one role) an assignment. The empty body is refused by the body models.
    "createAssignment": ("POST", "/assignments"),
    "listAssignments": ("GET", "/assignments"),
    "getAssignment": ("GET", "/assignments/asg_01M2545JSD15ETSNNV904X991W"),
    "transitionAssignment": ("POST", "/assignments/asg_01M2545JSD15ETSNNV904X991W/transitions"),
    # `W60-PRICE-LIST-01`. Price lists and vendor lists; the writes' missing bodies are refused
    # by their models only after the role decided.
    "uploadPriceList": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/price-lists"),
    "listPriceListRevisions": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/price-lists"),
    "listPriceListPositions": ("GET", "/price-lists/prl_01M2545JSD15ETSNNV904X991N/positions"),
    "getEffectiveVendorLists": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/vendor-lists"),
    "setGlobalVendorList": ("PUT", "/vendor-lists/EOM"),
    "setProjectVendorList": ("PUT", "/projects/prj_01M2545JSD15ETSNNV904X991F/vendor-lists/EOM"),
    # `W60-OPT-PROPOSALS-01`. Passes, proposals and decisions; the writes' missing bodies are
    # refused by their models only after the role decided.
    "startOptimisationPass": (
        "POST",
        "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991G"
        "/optimisation-passes",
    ),
    "listOptimisationPasses": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/optimisation-passes"),
    "listOptimisationProposals": (
        "GET",
        "/optimisation-passes/opp_01M2545JSD15ETSNNV904X991N/proposals",
    ),
    "decideOptimisationProposal": (
        "POST",
        "/optimisation-proposals/opr_01M2545JSD15ETSNNV904X991N/decisions",
    ),
    "listProposalDecisions": (
        "GET",
        "/optimisation-proposals/opr_01M2545JSD15ETSNNV904X991N/decisions",
    ),
    "exportOptimisationProposalsCsv": (
        "GET",
        "/optimisation-passes/opp_01M2545JSD15ETSNNV904X991N/export.csv",
    ),
    "listRunFindings": ("GET", "/runs/run_01M2545JSD15ETSNNV904X991K/findings"),
    "exportRunCsv": ("GET", "/runs/run_01M2545JSD15ETSNNV904X991K/export.csv"),
    # `W57B-NORMS-CATALOGUE-XLSX-01`. The workbook (expert, as the CSV) and the norms
    # catalogue (any role).
    "exportRunXlsx": ("GET", "/runs/run_01M2545JSD15ETSNNV904X991K/export.xlsx"),
    "listNormDocuments": ("GET", "/norm-documents"),
    # `W60-OPT-MATCH-01`. The priced specification of a document set (any role).
    "getSpecificationPrices": (
        "GET",
        "/projects/prj_01M2545JSD15ETSNNV904X991F/documents/doc_01M2545JSD15ETSNNV904X991H"
        "/specification-prices",
    ),
    # `W63-SECTION-FORM7-01`. A section's combined specification across projects (any role).
    "getSectionSpecification": ("GET", "/sections/AR/specification"),
    # `NORM-REFS-RUN-01`. The norms a run's saved text cites (any role).
    "getRunNormReferences": ("GET", "/runs/run_01M2545JSD15ETSNNV904X991K/norm-references"),
    "getFinding": ("GET", "/findings/fnd_01M2545JSD15ETSNNV904X991M"),
    "appendDecision": ("POST", "/findings/fnd_01M2545JSD15ETSNNV904X991M/decisions"),
    "listDecisionHistory": ("GET", "/findings/fnd_01M2545JSD15ETSNNV904X991M/decisions"),
    "listDecisions": ("GET", "/decisions"),
    "getDashboardSummary": ("GET", "/dashboard"),
    "getProductVersion": ("GET", "/system/version"),
    "listReleases": ("GET", "/releases"),
    "markReleaseNotesRead": ("PUT", "/me/release-notes"),
    "changePassword": ("POST", "/auth/password"),
    "getMe": ("GET", "/me"),
    "updateMyProfile": ("PATCH", "/me"),
    "listRegistrations": ("GET", "/registrations"),
    "approveRegistration": ("POST", "/registrations/reg_01M2545JSD15ETSNNV904X991R/approve"),
    "rejectRegistration": ("POST", "/registrations/reg_01M2545JSD15ETSNNV904X991R/reject"),
    "listUsers": ("GET", "/users"),
    "getUser": ("GET", "/users/usr_01M2545JSD15ETSNNV904X991S"),
    "updateUser": ("PATCH", "/users/usr_01M2545JSD15ETSNNV904X991S"),
    "archiveUser": ("POST", "/users/usr_01M2545JSD15ETSNNV904X991S/archive"),
    "restoreUser": ("POST", "/users/usr_01M2545JSD15ETSNNV904X991S/restore"),
    "purgeUser": ("DELETE", "/users/usr_01M2545JSD15ETSNNV904X991S"),
    "resetUserPassword": ("POST", "/users/usr_01M2545JSD15ETSNNV904X991S/password"),
    "endUserSessions": ("POST", "/users/usr_01M2545JSD15ETSNNV904X991S/sessions/end"),
    "listAuthEvents": ("GET", "/auth-events"),
}

_ANY: frozenset[str] = frozenset()
_EXPERT = frozenset({"expert"})
_ADMIN = frozenset({"admin"})
#: `R-80`: any one role -- an account whose role set is empty reads no product data.
_ANY_ROLE = frozenset({"expert", "admin"})
#: `R-150e`, `R-150x`: a product read «Наблюдатель» makes as well. Written from the owner's
#: rulings and the approved matrix (`UI-PARITY-01`), not read from the seam. `R-150w` keeps
#: the queue, journal, workers, executors and comparison queues on `_ANY_ROLE`.
_READ = frozenset({"expert", "admin", "viewer"})
#: `R-150e`: the run exports, an expert's until now, are a download the viewer may make too.
_EXPERT_OR_VIEWER = frozenset({"expert", "viewer"})

#: `R-60`, written out from the ruling's three sentences and **not** read from the seam, as
#: `R-80` amends it: product reads -- projects, documents, versions, blocks, runs, findings,
#: decisions, the dashboard, the execution queue and journal, the worker registry, the norms
#: search, documents, PDFs and snapshot list -- need any one role; product
#: changes `expert`, account and request management `admin`; the account's own operations
#: and the product version and release notes need any complete account, roles or none.
EXPECTED_ROLES: dict[str, frozenset[str]] = {
    "listProjects": _READ,
    "listDocuments": _READ,
    "getDocumentVersion": _READ,
    "streamDocumentVersionContent": _READ,
    "getVersionBlocks": _READ,
    "listVersions": _READ,
    "listRuns": _READ,
    "getRunStatus": _READ,
    "getArV3BetaGroup": _READ,
    "getArV3BetaGroupReview": _READ,
    "getArV3BetaPackStatus": _READ,
    "getRunNormVerification": _READ,
    "listExecutionQueue": _ANY_ROLE,
    "getExecutionDispatch": _ANY_ROLE,
    "setDocumentArchived": _ANY_ROLE,
    "renameDocument": _ANY_ROLE,
    "setDocumentTags": _ANY_ROLE,
    "listDocumentTags": _READ,
    "setFindingExecutionStatus": _EXPERT,
    "listProposalDecisionJournal": _READ,
    "listKnowledgeBaseEntries": _READ,
    "listAcceptedOptimisationProposals": _READ,
    "exportOptimisationProposalsXlsx": _READ,
    "importOptimisationProposalDecisions": _EXPERT,
    "carryOverProposalDecisions": _EXPERT,
    # `DECISION-MEMORY-M2` (1.44.0): the memory is read by experts and administrators, never by the viewer; its standing is the administrator's.
    "listDecisionMemoryCases": _ANY_ROLE,
    "getDecisionMemoryCase": _ANY_ROLE,
    "getDecisionMemoryStatus": _ADMIN,
    "withdrawDecisionMemoryCase": _ADMIN,
    "restoreDecisionMemoryCase": _ADMIN,
    # `HOSTS-SEAL-1` (contract 1.45.0): an expert and an administrator read the servers, the layout, the catalogue and the readiness of a start; the viewer none (`R-150w`). Every write and a server's details are the administrator's.
    "listExecutorHosts": _ANY_ROLE,
    "getExecutorHost": _ANY_ROLE,
    "getExecutorHostDetails": _ADMIN,
    "setExecutorHostEnabled": _ADMIN,
    "setExecutorHostSlots": _ADMIN,
    "archiveExecutorHost": _ADMIN,
    "issueExecutorHostEnrollment": _ADMIN,
    "createExecutorHostAgentInstall": _ADMIN,
    "getExecutorHostAgentInstall": _ADMIN,
    "confirmExecutorHostAgentInstallHostKey": _ADMIN,
    "getStageModelLayout": _ANY_ROLE,
    "reviseStageModelLayout": _ADMIN,
    "setStageModelLayoutEnabled": _ADMIN,
    "listModelCatalogue": _ANY_ROLE,
    "getRunStartReadiness": _ANY_ROLE,
    "importRunDecisions": _EXPERT,
    "getProject": _READ,
    "listVersionSheetLabels": _READ,
    "listRunFindingBlocks": _READ,
    "getWorkSchedule": _ANY_ROLE,
    "getWorkScheduleReserve": _ANY_ROLE,
    "setWorkScheduleSettings": _ADMIN,
    "setWorkSchedulePlans": _ADMIN,
    "setWorkCalendarDays": _ADMIN,
    "setEngineerAbsences": _ADMIN,
    "scheduleAssignments": _ADMIN,
    "listExecutionJournal": _ANY_ROLE,
    "listWorkers": _ANY_ROLE,
    # `EXEC-SEAL-01`: connections, probes and routes are product reads.
    "listExecutorConnections": _ANY_ROLE,
    "getExecutorConnection": _ANY_ROLE,
    "listExecutorRoutes": _ANY_ROLE,
    "listAnalysisPresets": _READ,
    # `CMP-SEAL-C0` (ADR-0025 decision 16): reads any one role; every write is the expert's act, and an
    # administrator without the expert role is refused.
    "createComparisonUpload": _EXPERT,
    "listComparisonUploads": _READ,
    "getComparisonUpload": _READ,
    "getComparisonUploadProposal": _READ,
    "uploadComparisonUploadPart": _EXPERT,
    "completeComparisonUploadFile": _EXPERT,
    "confirmComparisonUploadSet": _EXPERT,
    "excludeComparisonUploadSet": _EXPERT,
    "retryComparisonUploadSet": _EXPERT,
    "pauseComparisonUpload": _EXPERT,
    "resumeComparisonUpload": _EXPERT,
    "cancelComparisonUpload": _EXPERT,
    "listComparisonVersionOrders": _READ,
    "appendComparisonVersionOrder": _EXPERT,
    "listVersionPageProfiles": _READ,
    "getVersionPageProfile": _READ,
    "streamVersionPagePreview": _READ,
    "streamVersionPageThumbnail": _READ,
    "streamVersionPageTile": _READ,
    # `CMP-SEAL-C1` (ADR-0025 decision 16): reads any one role; every write the expert's act.
    "getComparisonMatrix": _READ,
    "prepareComparisonMatrix": _EXPERT,
    "listComparisonMatrixEdits": _READ,
    "applyComparisonMatrixEdits": _EXPERT,
    "undoComparisonMatrixEdit": _EXPERT,
    "listComparisonAiLinks": _READ,
    "startComparisonSeries": _EXPERT,
    "listComparisonSeries": _READ,
    "getComparisonSeries": _READ,
    "pauseComparisonSeries": _EXPERT,
    "resumeComparisonSeries": _EXPERT,
    "cancelComparisonSeries": _EXPERT,
    "finishComparisonSeries": _EXPERT,
    "listComparisonSheetPairs": _READ,
    "getComparisonSheetPair": _READ,
    "streamComparisonPairTile": _READ,
    "getComparisonOverview": _READ,
    "getComparisonQueueSummary": _ANY_ROLE,
    # `CMP-SEAL-C2`: reads are any one role, every write is the expert's act (ADR-0025 decision 16).
    "estimateComparisonAiPairCheck": _READ,
    "getComparisonAiPairCheck": _READ,
    "startComparisonAiPairCheck": _EXPERT,
    "pauseComparisonAiPairCheck": _EXPERT,
    "resumeComparisonAiPairCheck": _EXPERT,
    "cancelComparisonAiPairCheck": _EXPERT,
    "listComparisonAiPairHints": _READ,
    "estimateComparisonAiSheetChanges": _READ,
    "getComparisonAiSheetChanges": _READ,
    "startComparisonAiSheetChanges": _EXPERT,
    "pauseComparisonAiSheetChanges": _EXPERT,
    "resumeComparisonAiSheetChanges": _EXPERT,
    "cancelComparisonAiSheetChanges": _EXPERT,
    "finishComparisonAiSheetChanges": _EXPERT,
    "dequeueComparisonAiSheetChanges": _EXPERT,
    "retryComparisonAiSheetChanges": _EXPERT,
    "getComparisonSheetDescription": _READ,
    "startComparisonSheetDescription": _EXPERT,
    "listComparisonSheetDescriptionHistory": _READ,
    "estimateComparisonSheetDescription": _READ,
    "streamComparisonSheetDescriptionMd": _READ,
    "listComparisonReviewSheets": _READ,
    "getVersionPageSpecPositions": _READ,
    "getComparisonSheetPairSpecPositions": _READ,
    "listComparisonSpecifications": _READ,
    "getComparisonSpecification": _READ,
    "startComparisonSpecification": _EXPERT,
    "listComparisonSpecificationChanges": _READ,
    "estimateComparisonSpecification": _READ,
    "cancelComparisonSpecification": _EXPERT,
    "getComparisonLaunchQueue": _READ,
    "enqueueComparisonLaunch": _EXPERT,
    "pauseComparisonLaunchQueue": _EXPERT,
    "resumeComparisonLaunchQueue": _EXPERT,
    "clearComparisonLaunchQueue": _EXPERT,
    "removeComparisonLaunchEntry": _EXPERT,
    "getComparisonAiQueue": _ANY_ROLE,
    "streamComparisonSeriesSummary": _READ,
    "listComparisonReports": _READ,
    "createComparisonReport": _EXPERT,
    "uploadComparisonReportSource": _EXPERT,
    "getComparisonReport": _READ,
    "startComparisonReport": _EXPERT,
    "cancelComparisonReport": _EXPERT,
    "continueComparisonReport": _EXPERT,
    "rebuildComparisonReportPdf": _EXPERT,
    "deleteComparisonReport": _EXPERT,
    "prepareComparisonClientReport": _EXPERT,
    "streamComparisonReportPdf": _READ,
    "streamComparisonReportSourceMd": _READ,
    # `CMP-SEAL-C3`: stage reads need any one role; all stage writes need expert.
    "createStageAssembly": _EXPERT,
    "listStagePairSuggestions": _READ,
    "listStagePairs": _READ,
    "confirmStagePair": _EXPERT,
    "listStageUploads": _READ,
    "createStageUpload": _EXPERT,
    "reviseStageAssembly": _EXPERT,
    "getStageChainRun": _READ,
    "cancelStageChainRun": _EXPERT,
    "getStageSheetMapRevision": _READ,
    "listStageRawDifferences": _READ,
    "recomputeStageTextEvidence": _EXPERT,
    "listStageTextExclusions": _READ,
    "listStageTextHints": _READ,
    "getStagePair": _READ,
    "listStageChainRuns": _READ,
    "startStageChainRun": _EXPERT,
    "setStagePairCompleteness": _EXPERT,
    "getStageSheetMap": _READ,
    "applyStageSheetMap": _EXPERT,
    "listStageSheetMapHistory": _READ,
    "listStageSheetPassports": _READ,
    "listStageSheetSuggestions": _READ,
    "listStageTextFragments": _READ,
    "confirmStageUploadCandidate": _EXPERT,
    "rejectStageUploadCandidate": _EXPERT,
    "getStageUpload": _READ,
    "cancelStageUpload": _EXPERT,
    "completeStageUploadFile": _EXPERT,
    "uploadStageUploadPart": _EXPERT,
    "pauseStageUpload": _EXPERT,
    "resumeStageUpload": _EXPERT,
    # `CMP-SEAL-C4` (contract 1.13.0; `docs/program/P02_SEAMS.md`, `docs/program/CMP-SEAL-C4.md`): "Reads are any one of `expert` and
    # `admin`; every write is an expert's act and keyed" -- written here from that sentence, not read back from the module.
    # `BETA-COST-PREFLIGHT-1030` (read-only cost preflights, `expert`) and `HOTFIX-PRESENTATION-INT-1030` (the extended review
    # for `expert` or `admin`, the ZIP import `expert`, keyed; the technical report is a stream read like the other reports).
    "estimateStageChainRun": _ANY_ROLE,
    "getStageChainBatch": _READ,
    "listStageAiReviews": _READ,
    "listStageClassifications": _READ,
    "getStageSynthesis": _READ,
    "listStageGraphicEvidence": _READ,
    "listStageLinkRepairs": _READ,
    "listStageChangeCards": _READ,
    "getStageChangeCard": _READ,
    "listStageCardVerdicts": _READ,
    "getStageChangeJournal": _READ,
    "streamStageChangeJournalXlsx": _READ,
    "streamStageChangeJournalPdf": _READ,
    "streamStageChangeJournalHtml": _READ,
    "getStageProfileText": _READ,
    "getStageAssembly": _READ,
    "getExtendedRunReview": _READ,
    "streamComparisonTechnicalReport": _READ,
    "resumeStageChainRun": _EXPERT,
    "startStageChainBatch": _EXPERT,
    "pauseStageChainBatch": _EXPERT,
    "resumeStageChainBatch": _EXPERT,
    "cancelStageChainBatch": _EXPERT,
    "undoStageLinkRepair": _EXPERT,
    "applyStageCardVerdicts": _EXPERT,
    "createStageReviewCard": _EXPERT,
    "estimateRunCost": _EXPERT,
    "estimateArV3GroupCost": _EXPERT,
    "importComparisonZip": _EXPERT,
    "searchNorms": _READ,
    "getNormDocument": _READ,
    "listNormParagraphs": _READ,
    "streamNormDocumentContent": _READ,
    "listNormSnapshots": _READ,
    "listVersionPortalBlocks": _READ,
    "streamVersionPortalBlockCrop": _READ,
    # `W59-SECTION-SEAL-01`: the section review is a product read.
    "getVersionSectionReview": _READ,
    # `W59-VERSION-COMPARE-01`: the version comparison is a product read.
    "compareDocumentVersions": _READ,
    # `W59-ANALYSIS-SETTINGS-01`: the analysis-profile registry is a product read.
    "listAnalysisProfiles": _READ,
    "listNormDocuments": _READ,
    "exportRunXlsx": _EXPERT_OR_VIEWER,
    # `W61-DISPATCHER-01`: the dispatcher's reads and moves at the seam; the dispatch context
    # decides who reads which assignment and who makes which move.
    "listAssignments": _ANY_ROLE,
    "getAssignment": _ANY_ROLE,
    "transitionAssignment": _ANY_ROLE,
    # `W60-OPT-MATCH-01`: the priced specification is a product read.
    "getSpecificationPrices": _READ,
    # `W63-SECTION-FORM7-01`: a section's combined specification is a product read.
    "getSectionSpecification": _READ,
    # `NORM-REFS-RUN-01`: the run's cited norms are a product read.
    "getRunNormReferences": _READ,
    "listRunFindings": _READ,
    "getFinding": _READ,
    "listDecisionHistory": _READ,
    "listDecisions": _READ,
    "getDashboardSummary": _READ,
    "getProductVersion": _ANY,
    "listReleases": _ANY,
    "markReleaseNotesRead": _ANY,
    "getMe": _ANY,
    "updateMyProfile": _ANY,
    "changePassword": _ANY,
    "createProject": _EXPERT,
    "uploadDocument": _EXPERT,
    # `W59-VERSION-UPLOAD-01`: the next version takes exactly the first upload's roles.
    "uploadDocumentVersion": _EXPERT,
    "startRun": _EXPERT,
    "startArV3BetaGroup": _EXPERT,
    # `W59-SECTION-SEAL-01`: only an expert confirms a section; admin alone does not.
    "classifyDocumentVersion": _EXPERT,
    # `CLASSIFICATION-CORRECTION-01`: only an expert corrects a classification; admin alone does not.
    "correctVersionClassification": _EXPERT,
    "cancelRun": frozenset({"expert", "admin"}),
    "reauditRun": frozenset({"expert", "admin"}),
    "startRunFromStage": frozenset({"expert", "admin"}),
    "appendDecision": _EXPERT,
    # `W59-DECISION-CARRYOVER-01`: a carried decision is a verdict; admin alone does not.
    "carryOverDecision": _EXPERT,
    # `COMPARE-PERSISTED-SUMMARY-01`: approving or withdrawing a sheet pairing is a decision about
    # evidence; only an expert, admin alone does not.
    "approveSheetPairing": _EXPERT,
    "withdrawSheetPairing": _EXPERT,
    # B2: asking a model about a comparison is an expert's act too.
    "generateComparisonSummary": _EXPERT,
    # `W60-PRICE-LIST-01`: an expert uploads a price list and overrides a project's vendor
    # list; the global vendor list is an administrator's; any one role reads.
    "uploadPriceList": _EXPERT,
    "setProjectVendorList": _EXPERT,
    "setGlobalVendorList": _ADMIN,
    "listPriceListRevisions": _READ,
    "listPriceListPositions": _READ,
    "getEffectiveVendorLists": _READ,
    # `W60-OPT-PROPOSALS-01`: an expert starts a pass and decides its proposals (an
    # administrator alone reads and does not decide, R-60); any one role reads and exports.
    "startOptimisationPass": _EXPERT,
    "decideOptimisationProposal": _EXPERT,
    "listOptimisationPasses": _READ,
    "listOptimisationProposals": _READ,
    "listProposalDecisions": _READ,
    "exportOptimisationProposalsCsv": _READ,
    "exportRunCsv": _EXPERT_OR_VIEWER,
    # `W61-DISPATCHER-01`: assigning work is an administrator's act (R-60).
    "createAssignment": _ADMIN,
    "listRegistrations": _ADMIN,
    "approveRegistration": _ADMIN,
    "rejectRegistration": _ADMIN,
    "listUsers": _ADMIN,
    "getUser": _ADMIN,
    "updateUser": _ADMIN,
    "archiveUser": _ADMIN,
    "restoreUser": _ADMIN,
    "purgeUser": _ADMIN,
    "resetUserPassword": _ADMIN,
    "endUserSessions": _ADMIN,
    "listAuthEvents": _ADMIN,
    "setJobPriority": _ADMIN,
    "setExecutionPaused": _ADMIN,
    "setWorkerIntake": _ADMIN,
    # `EXEC-SEAL-01` (R-143): where model work goes is an administrator's act.
    "createExecutorConnection": _ADMIN,
    "reviseExecutorConnection": _ADMIN,
    "archiveExecutorConnection": _ADMIN,
    "setExecutorSecret": _ADMIN,
    "generateExecutorSshKey": _ADMIN,
    "requestExecutorProbe": _ADMIN,
    "setExecutorRoute": _ADMIN,
    # `ANALYSIS-PRESETS-01` (R-146av): a preset is executor configuration; who may change the route
    # may change a preset. The list is open to every role.
    "createAnalysisPreset": _ADMIN,
    "reviseAnalysisPreset": _ADMIN,
    "archiveAnalysisPreset": _ADMIN,
    "issueRunnerToken": _ADMIN,
    "revokeRunnerToken": _ADMIN,
    # `EXEC2-SEAL-1`: the agent's enrollment, its install over SSH (a host and a user are named) and the
    # integration-authorisation mark are administrator acts, reads of an install included.
    "issueExecutorEnrollment": _ADMIN,
    "setExecutorIntegrationAuthorisation": _ADMIN,
    "createExecutorAgentInstall": _ADMIN,
    "getExecutorAgentInstall": _ADMIN,
    "confirmExecutorAgentInstallHostKey": _ADMIN,
    # `EXEC2-SEAL-2`, as `EXEC2-GROUP-STORE-01` settles it: creating, revising and archiving a group and pointing a work
    # kind at a group revision are administrator acts, as are the cut-over preview and the routing mode; the four reads
    # of the group store (the list, one group, a group's capacity, the rules with the routing mode) are for any role.
    "listExecutorGroups": _ANY_ROLE,
    "createExecutorGroup": _ADMIN,
    "getExecutorGroup": _ANY_ROLE,
    "reviseExecutorGroup": _ADMIN,
    "archiveExecutorGroup": _ADMIN,
    "getExecutorGroupCapacity": _ANY_ROLE,
    "listExecutorRoutingRules": _ANY_ROLE,
    "setExecutorRoutingRule": _ADMIN,
    "previewExecutorRouting": _ADMIN,
    "setExecutorRoutingMode": _ADMIN,
    # `W55A-SEAL-01` (R-113): who designated which snapshot, and the designation itself.
    "listNormSnapshotEvents": _ADMIN,
    "setCurrentNormSnapshot": _ADMIN,
}

ROLE_SETS: tuple[frozenset[str], ...] = (
    frozenset(),
    frozenset({"expert"}),
    frozenset({"admin"}),
    frozenset({"expert", "admin"}),
    # `R-150e`: the viewer is always alone; a combined set is refused where roles are written.
    frozenset({"viewer"}),
)


def _expected(
    operation: str, *, roles: frozenset[str], complete: bool, default: bool
) -> str | None:
    """Section 3.2, restated: the capability the seam must name, or ``None`` for served."""
    if default and operation not in {"issueToken", "changePassword", "getMe"}:
        return "password_changed"
    if not complete and operation not in {"getMe", "updateMyProfile", "changePassword"}:
        return "profile_completed"
    required = EXPECTED_ROLES[operation]
    if required and not (required & roles):
        return "role:" + "|".join(sorted(required))
    return None


def _observed(router: Surface, operation: str) -> str | None:
    """The capability the served application refused with, or ``None`` when it served.

    A ``401`` is an assertion failure here, not a classification: every request in the
    sweep carries a credential the standing accepts, so a ``401`` would mean the sweep
    measured something other than the registers.
    """
    method, path = SAMPLES[operation]
    answer = dispatch(
        router,
        Request.build(method, path, headers={"Content-Type": "application/json"}, body=b"{}"),
    )
    assert answer.status != 401, (operation, answer.status, answer.body)
    if answer.status != 403:
        return None
    body = json.loads(answer.body)
    assert body["error_code"] == "permission_denied", (operation, body)
    return body["details"]["required_capability"]


def test_the_registers_are_the_ruled_ones() -> None:
    """The literal pin: each register equals what `R-59`, `R-60` and section 3.2 say."""
    assert UNAUTHENTICATED_OPERATIONS == {
        "issueToken",
        "submitRegistration",
        "readRegistrationStatus",
        "downloadAgentPackage",
    }
    assert ENROLLMENT_OPERATIONS == {"redeemExecutorEnrollment"}
    assert OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES == {"issueToken", "changePassword", "getMe"}
    assert OPERATIONS_AN_INCOMPLETE_PROFILE_REACHES == {
        "getMe",
        "updateMyProfile",
        "changePassword",
    }
    assert dict(OPERATION_ROLES) == EXPECTED_ROLES
    assert ROLES_OF_A_ROUTE_WITHOUT_AN_OPERATION == frozenset()


def test_every_guarded_operation_is_in_the_role_register(router: Surface) -> None:
    """Totality: the served operations minus the open ones are exactly the map's keys.

    An operation with no line is refused to everyone -- closed by default -- and this is
    what reports it rather than letting it sit closed unnoticed.
    """
    assert set(OPERATION_ROLES) == (
        router.operation_ids
        - UNAUTHENTICATED_OPERATIONS
        - RUNNER_OPERATIONS
        - ENROLLMENT_OPERATIONS
    )
    assert set(SAMPLES) == set(OPERATION_ROLES)


@pytest.mark.parametrize(
    ("roles", "complete", "default"),
    list(itertools.product(ROLE_SETS, (True, False), (False, True))),
    ids=lambda value: (
        ("+".join(sorted(value)) or "no-role")
        if isinstance(value, frozenset)
        else str(value)
    ),
)
def test_the_served_application_answers_what_the_registers_say(
    router: Surface, roles: frozenset[str], complete: bool, default: bool
) -> None:
    """Every guarded operation, for one standing; the whole matrix is the parametrisation."""
    credentials = router.router.credentials
    credentials.roles = roles
    credentials.profile_complete = complete
    credentials.is_default_credential = default
    mismatches = []
    for operation in sorted(SAMPLES):
        expected = _expected(operation, roles=roles, complete=complete, default=default)
        observed = _observed(router, operation)
        if expected != observed:
            mismatches.append((operation, expected, observed))
    assert mismatches == [], (
        "the served application and the registers disagree, as (operation, expected, "
        f"observed): {mismatches}"
    )


def test_an_archived_account_is_refused_as_unauthenticated_everywhere(
    router: Surface,
) -> None:
    """`R-61`: an archived account has no standing; one answer for every guarded operation."""
    credentials = router.router.credentials
    credentials.roles = frozenset({"expert", "admin"})
    credentials.archived = True
    for operation, (method, path) in sorted(SAMPLES.items()):
        answer = dispatch(router, Request.build(method, path))
        assert answer.status == 401, (operation, answer.status, answer.body)
        assert json.loads(answer.body)["error_code"] == "authentication_required", operation


def test_the_open_operations_read_no_standing(router: Surface) -> None:
    """The three open operations answer the same whatever the account's state would be.

    An archived, roleless, incomplete account on a default credential: none of it is read
    for an operation that takes no credential, so each answers its own validation refusal.
    """
    credentials = router.router.credentials
    credentials.roles = frozenset()
    credentials.archived = True
    credentials.profile_complete = False
    credentials.is_default_credential = True
    for method, path in (
        ("POST", "/auth/token"),
        ("POST", "/registrations"),
        ("POST", "/registrations/status"),
    ):
        answer = dispatch(
            router,
            Request.build(method, path, headers={"Content-Type": "application/json"}, body=b"{}"),
            credential=None,
        )
        assert answer.status == 422, (path, answer.status, answer.body)


def test_a_role_refusal_names_the_role_and_nothing_else(router: Surface) -> None:
    """The envelope's whole detail: the one safe key the catalog declares, with `role:<x>`."""
    credentials = router.router.credentials
    credentials.roles = frozenset({"expert"})
    method, path = SAMPLES["listUsers"]
    answer = dispatch(router, Request.build(method, path))
    assert answer.status == 403, answer.body
    body = json.loads(answer.body)
    assert body["details"] == {"required_capability": "role:admin"}, body
    assert body["retryable"] is False, body


def test_a_roleless_account_reads_no_product_data(router: Surface) -> None:
    """`R-80`: an empty role set is suspension -- no product read, the way out stays open.

    A complete account on a changed password with no role is refused every product read
    with ``role:admin|expert|viewer`` (``role:admin|expert`` where the viewer may not read either), and still reads its own account and the product's version
    and release notes, so the person can see that no role is assigned.
    """
    credentials = router.router.credentials
    credentials.roles = frozenset()
    for operation in ("listProjects", "getDashboardSummary"):
        assert _observed(router, operation) == "role:admin|expert|viewer", operation
    # `R-150w`: the queue is not a viewer's read, so its refusal names the two older roles.
    assert _observed(router, "listExecutionQueue") == "role:admin|expert"
    for operation in ("getMe", "getProductVersion", "listReleases"):
        assert _observed(router, operation) is None, operation


def test_the_subject_carries_the_label_the_row_holds_now(router: Surface) -> None:
    """A profile completed or renamed after the credential was minted is visible at once.

    The credential still names the label it was minted with; the account's row now holds
    another. The subject a handler receives -- and the decision ledger writes
    ``author_label`` from -- carries the row's, because the seam publishes the standing's
    login and label (`W49-SEAL-01`).
    """
    from starlette.testclient import TestClient

    from w13_api_driver import TEST_DISPLAY_LABEL, TEST_TOKEN

    seen: list = []
    app = router.app

    @app.middleware("http")
    async def _capture(request, call_next):  # pragma: no cover - exercised below
        response = await call_next(request)
        seen.append(getattr(request.state, "subject", None))
        return response

    router.router.credentials.display_label = "Переименованная А. И."
    client = TestClient(app, raise_server_exceptions=False)
    answer = client.get("/projects", headers={"Authorization": f"Bearer {TEST_TOKEN}"})
    assert answer.status_code == 200, answer.content
    assert seen and seen[0] is not None, seen
    assert seen[0].display_label == "Переименованная А. И.", seen[0]
    assert seen[0].display_label != TEST_DISPLAY_LABEL


def test_an_operation_the_register_does_not_name_is_refused_to_everyone() -> None:
    """Closed by default: a guarded ``operationId`` with no line in the map is a 403 for
    every role set, carrying no capability, because nothing would open it."""
    from w13_api_driver import SuiteCredentialAdapter

    from auditmanager.api.routers import Router

    credentials = SuiteCredentialAdapter(roles=frozenset({"expert", "admin"}))
    router = Router(credentials=credentials)

    @router.get("/unregistered", operation_id="anOperationNobodyRegistered", tags=["probe"])
    def unregistered() -> dict[str, str]:  # pragma: no cover - must never run
        raise AssertionError("the seam let an unregistered operation through")

    surface = Surface(router)
    answer = dispatch(surface, Request.build("GET", "/unregistered"))
    assert answer.status == 403, (answer.status, answer.body)
    body = json.loads(answer.body)
    assert body["error_code"] == "permission_denied", body
    assert "details" not in body, body
