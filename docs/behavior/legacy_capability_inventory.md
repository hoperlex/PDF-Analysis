# Legacy capability inventory — W0-BHV-01

## 1. Scope and evidence policy

This document inventories observable behavior in the immutable legacy snapshot. It
is a traceability index, not a greenfield specification and not a claim of runtime
parity.

| Item | Frozen value |
|---|---|
| Inspection date | 2026-08-31 |
| Legacy repository discovery path | `/root/projects/PDF-proverka/PDF-proverka` |
| Immutable legacy commit | `32b9d903792b30506048a1d42b0e6b2d07aee403` |
| Greenfield base commit | `cf11eddbadd134bc09e1c65e01662939134eb01b` |
| Method | Read-only Git-object inspection (`git cat-file`, `git show`, `git grep`, `git ls-tree`) |
| Runtime execution | None: no legacy service, job, provider, migration or user flow was run |

Evidence notation:

- **[D]** means direct source evidence at the pinned commit. It supports only the
  behavior stated in the same cell.
- **[I]** means an inference from one or more direct references. It is not a frozen
  fact and must be characterized before implementation.
- A reference has the form
  `legacy_commit:path:symbol-or-line`. Line numbers are anchors in the immutable
  object, not references to the moving checkout.
- `symbol@line` names the literal source symbol at its definition line;
  `lines@start-end` and `module@start-end` explicitly identify evidence regions.
- `observed` means source-observed, not runtime-observed. `not observed` means the
  bounded static search found no implementation or found an explicit negative
  declaration; it does not prove universal absence.

The current legacy checkout, branch position and worktree were not used as evidence.
All contract trees listed in `W0-BHV-01` remained read-only advisory inputs.

## 2. Discovery coverage

### 2.1 Public router modules

Discovery rule: every committed `backend/app/api/routers/*.py` containing
`APIRouter(` at the pinned SHA. Inclusion was reconciled against
`backend/app/main.py`. A module is counted once even when it exports more than one
router.

| # | Router module | Disposition | Capability mapping / exclusion | Evidence |
|---:|---|---|---|---|
| 1 | `action_log.py` | mapped | LO-01 operational action log | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@245` |
| 2 | `audit.py` | mapped | AN-01 through AN-04 audit control, progress and recovery | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@225` |
| 3 | `audit_worker_agent.py` | mapped | DW-01 through DW-05; feature-gated | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@248-267` |
| 4 | `audit_workers_admin.py` | mapped | DW-01 through DW-05; status route is unconditional, administrative routes are gated | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@252-278` |
| 5 | `auth.py` | mapped | WS-01 portal authentication/session | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@239` |
| 6 | `blocks.py` | mapped | AN-02 block, region and image evidence | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@224` |
| 7 | `critic_v2_assisted_round1.py` | mapped | EX-07 quality/assisted-review diagnostics | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@236` |
| 8 | `critic_v2_ui.py` | mapped | EX-07 critic triage and feedback UI | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@235` |
| 9 | `discussions.py` | mapped | EX-03 discussion and revision workflow | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@230` |
| 10 | `document.py` | mapped | WS-04 document/PDF pages and render access | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@229` |
| 11 | `export.py` | mapped | OUT-01 and OUT-02 Excel/ZIP export | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@226` |
| 12 | `external_register.py` | mapped | EX-06 external review-register reconciliation | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@237` |
| 13 | `findings.py` | mapped | FD-01 and FD-02 findings/evidence access | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@223` |
| 14 | `knowledge_base.py` | mapped | EX-01, EX-02, EX-04 and EX-05 expert/KB behavior | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@231` |
| 15 | `migrated_findings.py` | mapped | EX-08 manual cross-version debt recheck | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@220` |
| 16 | `objects.py` | mapped | WS-01 workspace objects | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@232` |
| 17 | `optimization.py` | mapped | AN-08 optimization and replication | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@228` |
| 18 | `projects.py` | mapped | WS-02 and WS-03 project/version/file ingest; also exports a groups router | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@221-222` |
| 19 | `projects_v2_shadow.py` | excluded | Feature-gated, read-only migration-shadow diagnostic; not counted as user product behavior | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@243` |
| 20 | `schedule.py` | mapped | LO-02 work schedule/plan | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@234` |
| 21 | `stage_comparison.py` | mapped | CP-01 through CP-06 stage comparison | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@238` |
| 22 | `usage.py` | mapped | AN-09 token/cost/budget accounting | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@227` |
| 23 | `users.py` | mapped | WS-01 user/current-user/activity administration | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@233` |
| 24 | `worker_bootstrap.py` | mapped | DW-06 resumable worker bootstrap; gated with distributed admin | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@269-280` |

Router coverage: **24 / 24 = 100%**: 23 mapped, 1 explicitly excluded.
The direct routes and WebSockets declared in `main.py` are supplementary public
surface rather than router modules. They expose login/root/info views and audit/global
progress sockets; their behavior is represented in WS-01 and AN-01.

### 2.2 Pipeline stage/order declarations

Discovery combined semantic searches for stage enums, stage/model maps, ordered
stage lists, retry/resume/skip maps, routing compiler/validator declarations,
sub-pipeline stage lists and UI progress orders. The ledger records declaration
sites, not a claim that all lists are equivalent or canonical.

| # | Declaration site | Disposition | Role / reason | Evidence |
|---:|---|---|---|---|
| 1 | `models/audit.py` `AuditStage` | mapped | Persisted audit-stage vocabulary | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/models/audit.py:AuditStage@8` |
| 2 | `core/config.py` stage model keys/defaults | mapped | Model-configurable stage vocabulary | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/core/config.py:_stage_models@262`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/core/config.py:_STAGE_MODEL_DEFAULTS@276` |
| 3 | `core/config.py` critical model stages | mapped | Provider/model validation subset | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/core/config.py:CRITICAL_STAGE_MODEL_STAGES@585` |
| 4 | `routers/audit.py` global-template whitelist | mapped | User-editable global prompt/model stage subset | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/audit.py:valid_stages@618` |
| 5 | `routers/audit.py` project-prompt whitelist | mapped | User-editable project prompt stage subset | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/audit.py:valid_stages@841` |
| 6 | `routers/audit.py` retry aliases | mapped | Public retry name to manager-stage mapping | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/audit.py:stage_to_pipeline_stage@1107` |
| 7 | `routers/audit.py` skip whitelist | mapped | Publicly skippable stages | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/audit.py:valid_stages@1157` |
| 8 | `pipeline/manager.py` normalized resume aliases | mapped | Accepted resume-entry vocabulary | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/manager.py:_normalize_ocr_stage@3243` |
| 9 | `pipeline/manager.py` OCR resume order | mapped | Actual ordered continuation path | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/manager.py:ocr_stages@3688` |
| 10 | `pipeline/manager.py` full pipeline body | mapped | Runtime orchestration: preparation, analysis, merge, review/norm/optimization, debt/carryover and Excel | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/manager.py:_run_ocr_pipeline@5346` |
| 11 | `pipeline/resume_detector.py` failure-recovery order | mapped | Log-state to resumable-stage order | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/resume_detector.py:stage_order@253` |
| 12 | `services/common/audit_logger.py` order keys | mapped | Audit-log display/status order, feature-dependent text/block reorder | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/common/audit_logger.py:_PIPELINE_STAGE_ORDER_KEYS@79` |
| 13 | `services/common/project_service.py` stage order | mapped | Project status/display order, feature-dependent reorder | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/common/project_service.py:_PIPELINE_STAGE_ORDER@1864` |
| 14 | `audit_routing/compiler.py` stage/scope maps | mapped | Routing stage keys and execution scopes | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/audit_routing/compiler.py:PIPELINE_STAGE_OF@46`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/audit_routing/compiler.py:SCOPE_OF_PIPELINE_STAGE@62` |
| 15 | `audit_routing/compiler.py` plan order | mapped | Compiled routing-plan order | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/audit_routing/compiler.py:RoutingCompiler.compile.stages@690` |
| 16 | `audit_routing/presets.py` model-stage order | mapped | Preset completeness/order vocabulary | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/audit_routing/presets.py:STAGE_MODEL_KEYS@47` |
| 17 | `audit_routing/validator.py` mandatory/central sets | mapped | Routing validation and center-only execution constraints | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/audit_routing/validator.py:MANDATORY_STAGES@38`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/audit_routing/validator.py:CENTER_ONLY_PIPELINE_STAGES@55` |
| 18 | `models/distributed_workers.py` remote/central sets | mapped | Remote-pilot and central-only stage eligibility | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/models/distributed_workers.py:REMOTE_AUDIT_PILOT_STAGES@39`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/models/distributed_workers.py:CENTRAL_ONLY_STAGES@52` |
| 19 | `pipeline/remote_audit_runner.py` forbidden stages | mapped | Remote runner exclusion set | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/remote_audit_runner.py:FORBIDDEN_STAGES@30` |
| 20 | `distributed_workers/provider_requirement.py` allowed model stages | mapped | Provider requirement stage subset | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/distributed_workers/provider_requirement.py:AUDIT_MODEL_STAGES@72` |
| 21 | Section-optimization pipeline stages | mapped | Collect/normalize/synthesize/agent/graphics/review sub-pipeline | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/section_optimization_pipeline_service.py:_STAGES@34` |
| 22 | Section-optimization replication stages | mapped | Validate/package/agent/graphics/expert sub-pipeline | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/section_optimization_replication_service.py:_STAGES@45` |
| 23 | Stage-comparison upload stages | mapped | `stage_1`/`stage_2` comparison input slots, not audit stages | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/stage_upload.py:VALID_STAGES@27` |
| 24 | Frontend base stage-model configuration | mapped | UI stage/model configuration vocabulary | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:frontend/static/js/app.js:BASE_STAGE_MODEL_CONFIG@3049` |
| 25 | Frontend legacy artifact aliases | mapped | UI mapping from old audit artifact names to stage status | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:frontend/static/js/app.js:STAGES@2837` |
| 26 | Distributed-task UI progress order | excluded | Transfer/worker task UI lifecycle, not the analysis pipeline; retained for DW behavior | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:frontend/static/js/distributed-feature.js:TASK_STAGE_ORDER@20` |
| 27 | `text_analysis/stage_gates.py` document classes | excluded | Experimental document classification explicitly not wired into the production pipeline | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/text_analysis/stage_gates.py:module@1-16` |
| 28 | `project_service.py` pipeline stage aliases | mapped | Legacy artifact/status names accepted when computing pipeline state | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/common/project_service.py:_PIPELINE_STAGE_ALIASES@2175` |
| 29 | `project_service.py` stage artifacts | mapped | Artifact-presence map used to infer completed stages | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/common/project_service.py:_PIPELINE_STAGE_ARTIFACTS@2185` |
| 30 | `storage/stage_artifacts.py` value aliases | mapped | Persisted stage-value canonicalization aliases | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/storage/stage_artifacts.py:STAGE_VALUE_ALIASES@61` |
| 31 | `norms/runner.py` active norm stages | mapped | Norm-verification/fix set used by concurrency and model-unload gating | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/stages/norms/runner.py:norm_stages@313` |

Declaration coverage: **31 / 31 = 100%**: 29 mapped, 2 explicitly
excluded. The declaration sites conflict in membership and order; section 7 records
that contradiction rather than naming one list as the greenfield registry.

## 3. Stable capability matrix

### 3.1 Workspace, ingest and versioning

| ID | Actor / intent | Trigger / input | Observable output or artifact | Failure, retry and recovery | Status | Confidence | Evidence |
|---|---|---|---|---|---|---|---|
| WS-01 | Portal user administers workspace objects, users and session | Login/session and object/user actions | Authenticated portal state, object/user/activity records | Auth and role gates produce visible denials; exact runtime policy was not exercised | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/auth.py:router`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/objects.py:router`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/users.py:router` |
| WS-02 | Auditor creates and manages discipline/project/version hierarchy | Project metadata, folder upload, version creation or merge-source-as-version | Project/version directories and metadata; a new version does not copy prior output | Missing/invalid input is 4xx; active audit/conflict is 409; merge can retain or delete the source project by request | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/projects.py:create_project_version@533`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/projects.py:create_version_from_project@746` |
| WS-03 | Auditor prechecks and ingests source documents | Folder/multipart upload of PDF, Markdown and recognized JSON companions | Precheck status/fingerprint/suggested target; stored input files and updated metadata | Dry-run reports ready/warning/duplicate/error; path traversal, extension and version-1 misuse are rejected; ZIP is only observed in comparison ingest | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/projects.py:upload_folder_precheck@279`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/projects.py:upload_version_files_endpoint@616`; **[I]** workspace-level mixed PDF/ZIP ingest is only partial because the ZIP route belongs to CP-01 |
| WS-04 | Reviewer opens source document and page evidence | Project/version, page, block or region request | PDF/page render, text layer, block image/region and block context | Missing project/page/block is a visible HTTP error; render parity was not executed | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/document.py:router`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/blocks.py:router` |

### 3.2 Audit execution and analysis

| ID | Actor / intent | Trigger / input | Observable output or artifact | Failure, retry and recovery | Status | Confidence | Evidence |
|---|---|---|---|---|---|---|---|
| AN-01 | Auditor starts one or many audits and watches progress | Prepare/full/standard/pro/start-from/resume requests, including batches | Audit status, queue/batch status, live logs and WebSocket progress | Pause/resume/cancel/reorder/retry are public; rate-limit can pause; errors/cancellation are persisted and surfaced | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/audit.py:router`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:ws_audit@301` |
| AN-02 | Pipeline prepares geometry and evidence context | Source PDF/Markdown and project configuration | Crops, page/block geometry, document graph/context and image references | Stage errors are logged; interrupted startup state is converted to resumable state | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/manager.py:_run_ocr_pipeline@5346`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/manager.py:_recover_stale_pipelines@1304` |
| AN-03 | Pipeline analyzes extracted text | Prepared text, block/context artifacts and configured model route | Text-analysis JSON/artifacts used by later merge | Text/block order is feature-dependent; provider failure and stage error are visible through pipeline status | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/manager.py:_run_ocr_pipeline@5346`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/common/project_service.py:_get_stage_order@1882` |
| AN-04 | Pipeline analyzes blocks/visual context | Crops, geometry, document context and routed model | Block-analysis findings/artifacts | Can precede or follow text analysis by pipeline version; stage failure is resumable from a declared entry point | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/manager.py:_run_ocr_pipeline@5346`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/manager.py:ocr_stages@3688` |
| AN-05 | Pipeline merges and deduplicates analysis findings | Text/block result sets and evidence maps | Canonical `03_findings.json` with merged finding identities and links | Merge is a retryable named stage; exact equivalence under provider variation was not executed | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/manager.py:_run_ocr_pipeline@5346`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/audit.py:stage_to_pipeline_stage@1107` |
| AN-06 | Pipeline reviews/grounds findings and checks norms | Merged findings, project context and configured reviewer/corrector/norm stages | Review, correction and normative-verification artifacts | Review failure can fail the path; norm/optimization branches may record degradation and continue; no removed legacy evidence-verifier may be inferred from this | observed | medium | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/manager.py:_run_post_findings_parallel@4711`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/findings.py:get_kb_validation@110`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/findings.py:run_kb_validation@123` |
| AN-07 | Operator resumes, retries, skips or cancels a failed/interrupted run | Stage name and audit control request | Updated pipeline log/status and continued or stopped execution | Unknown retry/skip name is 4xx; unsafe state conflicts are 409; startup changes stale `running` to `interrupted` | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/audit.py:retry_stage@1099`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/resume_detector.py:stage_order@253` |
| AN-08 | Auditor requests section/project optimization and replication | Project/section plus generated findings/context | Optimization artifacts and section replication pipeline artifacts | Substage progress is persisted; graphics/agent/expert substages can surface sub-pipeline failure | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/optimization.py:router`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/section_optimization_pipeline_service.py:_STAGES@34` |
| AN-09 | Administrator observes and constrains model usage | Stage/model calls, project/accounting and budget inputs | Token/cost/usage and budget records/views | Budget/config validation and provider errors are visible, but deterministic replay of live model output was not observed | observed | medium | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/usage.py:router`; **[I]** cost observability does not establish replayability |

### 3.3 Findings and expert intelligence

| ID | Actor / intent | Trigger / input | Observable output or artifact | Failure, retry and recovery | Status | Confidence | Evidence |
|---|---|---|---|---|---|---|---|
| FD-01 | Reviewer browses and filters findings | Project/version, filters, grouping and pagination | Finding summary/list/detail, grouped pages and version-aware results | Missing finding/project returns a visible error; filters are read-only | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/findings.py:get_findings@145` |
| FD-02 | Reviewer traces a finding to deterministic source context | Finding ID, block IDs and page/region inputs | Block map, text-layer shadow/detail, strict text/image evidence links | Missing/invalid evidence link remains explicit; evidence is not silently invented by the AI summary layer | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/findings/findings_service.py:get_finding_block_map@492`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/findings/findings_service.py:compute_finding_block_map@543`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/findings.py:get_finding_block_map@45` |
| EX-01 | Expert accepts/rejects or annotates findings | Review payload; reviewer identity comes from portal session when authentication is enabled | Per-project `expert_review.json`, enriched decision and global decision-log projection | Save is atomic; unmapped authenticated login is not replaced with another identity; shadow-v2 mirror failure is fail-soft | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/knowledge_base.py:_resolve_reviewer@26`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/knowledge_base/knowledge_base_service.py:save_expert_review@220` |
| EX-02 | Product expects immutable append-only expert-decision events | Repeated decision, correction or revocation | No append-only event stream was found: a matching decision is updated, and revoke deletes from both global log and active review | Historical value can be replaced/removed; this contradicts the synopsis target and requires a greenfield semantic decision | not observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/knowledge_base/knowledge_base_service.py:_append_to_decisions_log@683`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/knowledge_base/knowledge_base_service.py:revoke_decision@861` |
| EX-03 | Expert discusses, revises and resolves a finding | Discussion/revision/resolution request | Discussion and revision artifacts linked to finding/project | Missing/invalid item is visible; persistence/runtime collaboration was not exercised | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/discussions.py:router` |
| EX-04 | Expert searches and curates the global KB | Filters/search/status, customer confirm/unconfirm, pattern and missing-norm actions | Filtered entries/stats, confirmations, approved/dismissed patterns and missing-norm queue | Confirmation is accepted-only; ambiguous revoke is refused; import/action failures are visible | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/knowledge_base.py:lines@102-272`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/knowledge_base/knowledge_base_service.py:revoke_decision@861` |
| EX-05 | Expert imports prior decisions from a spreadsheet | Decision Excel upload | Imported decision/KB projection with per-row outcome | Validation/import errors are user-visible; exact spreadsheet compatibility requires characterization | observed | medium | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/knowledge_base.py:upload_decisions_excel@194` |
| EX-06 | Reviewer reconciles an external review register | External register upload plus match/confirm/reject/export actions | Matched register entries, explicit confirmations/rejections and exported register | Ambiguous/unmatched items remain reviewable; exact matching boundaries require characterization | observed | medium | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/external_register.py:router` |
| EX-07 | Quality reviewer inspects critic output and gives feedback | Critic artifacts and assisted-review feedback | Diagnostic/triage views and feedback/quality artifacts | Diagnostic routes may be absent from production policy despite being included; runtime UI was not exercised | observed | medium | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/critic_v2_ui.py:router`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/critic_v2_assisted_round1.py:router` |
| EX-08 | Expert carries prior-version judgment forward without overriding current human work | V2+ audit with previous checked version and current findings | Deterministic shortlist, optional LLM match, carryover report and review merge; provider/threshold failure yields `needs_manual_review` with no verdict | Existing non-empty human/auto verdict is preserved; wrapper is fail-soft; rerun/provider behavior needs a golden journey | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/findings/decision_carryover_service.py:run_decision_carryover@436`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/stages/decision_carryover/runner.py:run_decision_carryover_stage@40` |
| EX-09 | Expert manually checks migrated accepted findings separately from decision carryover | Manual recheck request using prior accepted findings | Stable `MIG` items, report and current `03_findings.json` mutation | Stable origin pairs make append idempotent; auto-run is not the default; statuses include manual-review states | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/migrated_findings.py:check_migrated_findings@33`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/findings/migrated_findings_service.py:_stable_migrated_id@1436`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/findings/migrated_findings_service.py:append_migrated_findings_to_current_findings@1442`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/findings/migrated_findings_service.py:run_migrated_findings_check@1599` |

### 3.4 Stage comparison

| ID | Actor / intent | Trigger / input | Observable output or artifact | Failure, retry and recovery | Status | Confidence | Evidence |
|---|---|---|---|---|---|---|---|
| CP-01 | Reviewer loads two design stages | Object plus `stage_1`/`stage_2` ZIP or folder upload | Versioned comparison-stage filesystem roots and PDF counts | Rejects wrong stage, traversal, symlink, encrypted/oversized ZIP/member; replacement uses temp, atomic switch and recoverable previous backup | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/stage_upload.py:VALID_STAGES@27`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/stage_upload.py:_commit_extracted_stage@347`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/stage_upload.py:replace_stage_from_zip@444`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/stage_upload.py:replace_stage_from_folder@478` |
| CP-02 | Reviewer creates session/document pairs and chooses sheet links | Stage source signature, selected PDFs and many-to-many sheet decisions | Idempotent session/pair, disposable suggestions and authoritative saved link file | All-document/uniqueness/range validation is explicit; saving replaces the prior explicit decision and supersedes repair suggestions | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/store.py:create_session@184`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/store.py:save_sheet_links@564` |
| CP-03 | Reviewer computes deterministic text changes | Accepted links, exclusions and extracted sheet text | Raw comparison and factual-difference artifacts | Missing accepted links/current exclusions are hard gates; same signature can reuse output; GET returns `not_started` when absent | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/store.py:run_text_comparison@1281`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/store.py:require_text_exclusions_for_downstream@690`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/store.py:run_text_differences@720` |
| CP-04 | Reviewer requests AI classification/summary downstream of raw evidence | Current deterministic comparison/difference artifacts | Additive AI review/final/change-summary JSON; failed groups/chunks remain failed/partial | Same-signature completed groups can be reused; provider/validation failure has deterministic summary fallback; source-changing race rejects before atomic write | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/store.py:run_text_ai_review@1068`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/store.py:run_project_change_summary@939` |
| CP-05 | Reviewer applies or reverses high-confidence sheet-link repair | Current suggestions/link state and repair action | Durable repair history, recomputed downstream stages, undo restoring snapshot | Repair validates confidence/current source; undo restores snapshot and recomputes; race/stale artifacts are explicit | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/store.py:_apply_sheet_link_repair@838`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/store.py:undo_sheet_link_repair@908` |
| CP-06 | Reviewer compares graphic/vector changes | Paired drawing sheets | No graphic/vector comparison artifact was found; the text-difference artifact explicitly reports graphics not analyzed | No recovery behavior exists for this absent capability | not observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/store.py:vector_graphics_comparison@1427`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/text_differences.py:graphics_analyzed@479` |

### 3.5 Export and operational support

| ID | Actor / intent | Trigger / input | Observable output or artifact | Failure, retry and recovery | Status | Confidence | Evidence |
|---|---|---|---|---|---|---|---|
| OUT-01 | Reviewer exports findings/optimization | Project/version, export kind and optional section | XLSX file/path and guarded download | Invalid kind/project is 400; generator error is 500; safe-path validation protects download | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/export.py:generate_excel@42`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/export.py:download_file@78` |
| OUT-02 | Reviewer exports a portable audit package | Project/version with `03_findings.json` | ZIP with available metadata/source/pipeline/evidence/review/discussion/optimization artifacts and generated Excel when successful | Missing findings is 404; embedded Excel failure is swallowed and ZIP can succeed without it, an explicit completeness risk | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/export.py:_download_audit_package_v2@137`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/export.py:download_audit_package@253`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/export.py:lines@207-229`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/export.py:lines@332-355` |
| LO-01 | Administrator examines operator/system actions | Action-log query | Operational action records | Read behavior is present; retention/immutability guarantees were not established | observed | medium | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/action_log.py:router` |
| LO-02 | Planner manages project work schedule | Schedule CRUD/actions | Project schedule/work-plan artifact | Optional expert completion stamp is coupled to review save; exact concurrent behavior was not exercised | observed | medium | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/schedule.py:router`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/knowledge_base/knowledge_base_service.py:save_expert_review@220` |

### 3.6 Distributed execution and recovery

| ID | Actor / intent | Trigger / input | Observable output or artifact | Failure, retry and recovery | Status | Confidence | Evidence |
|---|---|---|---|---|---|---|---|
| DW-01 | Administrator enrolls workers and inspects capabilities/status | Registration/reenrollment, heartbeat/resources, capability and admin requests | Worker identity/capabilities/connectivity plus administrative dashboard/audit records | Agent API is feature-gated; admin routes additionally require portal auth or explicit insecure-admin mode | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/audit_worker_agent.py:register@263`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:lines@248-280` |
| DW-02 | Center assigns logical work and tracks attempts | Job poll/claim, accept/reject, heartbeat, events and operator attempt actions | Persistent logical-job/attempt state with at most one active job per project/version and one active attempt per job | Attempt-scoped execution token, idempotency keys and stale/superseded checks reject conflicts; state/disposition are separate | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/distributed_workers/schema.py:_MIGRATION_3@243`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/audit_worker_agent.py:jobs_next@625` |
| DW-03 | Product expects distinct Run, Job and Attempt identities | Distributed execution creation/claim | Job and Attempt are explicit; a distinct canonical Run entity/identity was not found in the bounded schema and protocol | Greenfield must not manufacture Run semantics from project/version or attempt | not observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/distributed_workers/schema.py:lines@223-318`; **[I]** absence is bounded to the inspected schema/protocol |
| DW-04 | Worker uploads result safely and center imports only validated output | Resumable upload session/chunks/complete plus result package | Checksum-verified assembled package, rejected/validated storage, staging/backup/journal and atomic project replacement | Chunk/session/complete are idempotent; superseded results are stored without publication; same applied hash replays, different hash conflicts; rollback/restart recovery is explicit | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/distributed_workers/upload_service.py:module@1-16`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/audit_worker_agent.py:lines@1231-1260`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/distributed_workers/result_import.py:module@1-18` |
| DW-05 | Worker continues across disconnect/restart without accepting stale authority | Disk-first event outbox, event sequence/ACK, reconciliation request and connection epoch | Ack/deduped events, closed reconciliation action and fenced gateway connection | Old connection epoch and stale/superseded attempt are rejected; reconciliation returns continue/upload/await/stop; no explicit domain-level `fencing_token` field was established | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:audit_worker/event_outbox.py:module@1-18`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/distributed_workers/gateway_repository.py:accept_connection@22`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/audit_worker_agent.py:reconcile@1502` |
| DW-06 | Administrator bootstraps or resumes worker installation | Bootstrap create/list/get/update/resume session | Resumable bootstrap session and repeat-safe remote steps | Repeated run avoids duplicate release/service/worker; worker update delivery itself is explicitly a no-op `204` manifest | observed | high | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/worker_bootstrap/manager.py:run@144`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/audit_worker_agent.py:update_manifest@1488` |

## 4. Inputs, outputs and side effects

| Category | Source-observed inventory | Main evidence / qualification |
|---|---|---|
| Ingest inputs | PDF, Markdown, recognized JSON companion/result metadata and folder/multipart project input; comparison ZIP/folder; expert decision spreadsheet; operator configuration/actions; distributed worker packages, event batches and chunk uploads | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/projects.py:FlatVersionFromCandidateRequest@413`; **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/projects.py:flat_create_version_from_candidate@426`; **[D]** CP-01, EX-05 and DW-04 references above |
| Core audit artifacts | Project/version metadata; source PDF/Markdown; crops/block index; document graph/context; text and block analyses; merged findings; review/norm/optimization; debt and carryover reports; pipeline log; Excel | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/manager.py:_run_ocr_pipeline@5346`; **[D]** OUT-02 |
| Expert artifacts | Per-project expert review, mutable global decision-log projection, discussions, KB entries/patterns/confirmations, external register and imported-decision results | **[D]** EX-01 through EX-06. The decision log must not be described as append-only |
| Comparison artifacts | Session, document pair, suggestions, authoritative sheet links, exclusions, deterministic comparison/differences, AI review/final/summary and repair history | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/paths.py:module@17-89` |
| Stores | Filesystem JSON/directories in legacy and projects-v2 layouts; SQLite tables for distributed workers/jobs/attempts/events/uploads; process-local active task handles alongside persisted logs/queue/recovery state | **[D]** `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/distributed_workers/schema.py:module@1-22`; **[I]** process-memory use does not imply jobs are memory-only |
| Provider boundaries | Configured CLI and paid/model-provider runners are reachable from routed stages; model/provider selection and cost are persisted or displayed | **[D]** stage-model declarations in section 2.2 and AN-09. No provider was called and no credential/config value was read |
| External side effects | Filesystem writes/replacements, SQLite state transitions, generated downloads, WebSocket progress, optional worker/remote bootstrap actions and provider invocations | **[D]** WS-02, AN-01, CP-01, DW-02 and DW-06. Static evidence cannot establish production delivery/timing |
| User-visible failures | HTTP 4xx/5xx including validation, authorization, not-found, conflict and disabled-service cases; WebSocket/pipeline logs; stage `error`, `partial`, `skipped` or `interrupted`; comparison `not_started`/stale/required gates; distributed stale/superseded conflict, rejected result and retention state | **[D]** AN-07, CP-03/04 and DW-02/04/05. Exact response wording was not characterized |

Security-relevant behavior observed in source includes safe-path checks, archive limits,
attempt-scoped tokens, checksum validation, redaction before outbox persistence and
staging before project replacement. This inventory does not certify those controls.

## 5. Product synopsis reconciliation

`docs/PRODUCT_SYNOPSIS.md` is a target taxonomy, not legacy evidence. The status
below compares every listed capability, without rewriting that target document.

| Group | Synopsis capability | Result | Legacy evidence and boundary |
|---|---|---|---|
| Audit workspace | Objects, disciplines, projects, documents, versions | supported | WS-01, WS-02 |
| Audit workspace | PDF/ZIP/structured companion ingest | partial | WS-03 supports PDF/Markdown/recognized JSON; ZIP is observed only for CP-01 comparison ingest |
| Audit workspace | Ingest status and audit status | supported | WS-03, AN-01 |
| Audit workspace | PDF/evidence viewer | supported | WS-04, FD-02 |
| Audit workspace | Findings list and filters | supported | FD-01 |
| Audit workspace | Retry and resume failed stages | supported | AN-07 |
| Audit workspace | Excel and portable audit package | supported | OUT-01/02; package can omit failed embedded Excel |
| Analysis platform | Versioned stage registry | partial | Section 2.2 finds many stage declarations and pipeline-version ordering, but no single consistent versioned registry |
| Analysis platform | Text extraction, geometry and block context | supported | AN-02 |
| Analysis platform | Text analysis | supported | AN-03 |
| Analysis platform | Visual/block analysis | supported | AN-04 |
| Analysis platform | Merge and deduplication | supported | AN-05 |
| Analysis platform | Grounding/evidence validation | partial | FD-02 has strict evidence linkage and KB validation exists; this does not establish the synopsis verifier semantics |
| Analysis platform | Normative verification | supported | AN-06 |
| Analysis platform | Critic/corrector passes | supported | AN-06, EX-07 |
| Analysis platform | Replay and cost accounting | partial | Same-signature/idempotent paths exist in comparison/distributed flows and AN-09 provides cost/usage accounting; no general deterministic replay of live provider output was found |
| Expert intelligence | Append-only expert decision events | contradicted | EX-02: matched entries can be overwritten and revocation removes them |
| Expert intelligence | Reason/comments/discussions | supported | EX-01, EX-03; decision reason typing remains permissive |
| Expert intelligence | Knowledge-base projection | supported | EX-04 |
| Expert intelligence | Evidence-verifier results | partial | KB-validation endpoints exist, but they cannot be equated to the target evidence verifier without characterization |
| Expert intelligence | Suggested re-review of rejected findings | partial | Carryover/migration/validation review queues exist; exact synopsis lifecycle is not established |
| Expert intelligence | Quality analytics | supported | EX-07 |
| Comparison | Project-stage pairs | supported | CP-01, CP-02 |
| Comparison | Suggested and user-confirmed links | supported | CP-02 |
| Comparison | Deterministic exclusions and text diff | supported | CP-03 |
| Comparison | Immutable/raw evidence artifacts | partial | CP-03/04 preserve deterministic inputs from AI mutation; filesystem replacement/immutability guarantees are not universal |
| Comparison | AI additive classification/summary | supported | CP-04 |
| Comparison | Graphic/vector comparison | not observed | CP-06 explicitly reports graphics not analyzed |
| Comparison | Audit/undo trail for link repair | supported | CP-05 |
| Distributed execution | Worker enrollment and capability registration | supported | DW-01 |
| Distributed execution | Run / Job / Attempt separation | partial | DW-02 has Job/Attempt; DW-03 finds no distinct Run entity |
| Distributed execution | Lease, heartbeat and fencing | partial | Heartbeat, token checks and connection-epoch fencing exist; a canonical lease/fencing-token contract was not established |
| Distributed execution | Immutable package and checksum verification | supported | DW-04; input/result packages are hash-checked and staged |
| Distributed execution | Offline outbox and recovery | supported | DW-05 |
| Distributed execution | Stale/superseded attempt rejection | supported | DW-02, DW-05 |
| Distributed execution | Publish only after validation | supported | DW-04 stores rejected/superseded output without project publication and imports validated output |

Reconciliation totals: **36 / 36 synopsis bullets classified**: 25 supported,
9 partial, 1 not observed, 1 contradicted.

No edit was made to `docs/PRODUCT_SYNOPSIS.md`: its statements describe intended
greenfield scope rather than asserting legacy facts. The append-only contradiction
is therefore recorded here for product/domain decision instead of silently changing
the target.

## 6. Pipeline topology observed

The executable manager path prepares source artifacts, builds crops/graph/context,
runs text and block analysis in feature-dependent order, merges findings, coordinates
review/norm/optimization, then runs debt control, decision carryover and Excel
generation. Some post-merge branches are fail-soft and can leave an audit complete
with degraded/warning artifacts; Excel generation can also warn without reversing
all prior results.

The declaration ledger shows at least five overlapping notions of stage order:
runtime orchestration, resume order, status/display order, routed model-stage order
and remote eligibility. They do not have identical membership or ordering. For
example, some display declarations omit debt/carryover or use a legacy enrichment
alias, while text/block order changes with pipeline version. This is direct evidence
of legacy drift, not permission to choose a canonical greenfield order in W0-BHV-01.

## 7. Gaps, contradictions and risks

1. **Expert decisions are not append-only.** Matching decision-log entries can be
   replaced and revocation deletes records. Product/domain authority must choose the
   greenfield event/history semantics.
2. **There is no single legacy stage registry.** Stage enums, UI order, resume order,
   routing presets and remote eligibility overlap but diverge. W0-ANA-01 must trace
   each legacy alias before freezing a new registry.
3. **Graphic/vector comparison is absent in the bounded source evidence.** The
   comparison artifacts explicitly describe text-only behavior.
4. **Distributed Run identity is absent.** Job and Attempt are durable, but a
   distinct Run was not found. Connection epoch and attempt token checks must not be
   relabeled as a greenfield fencing-token contract without a domain decision.
5. **Some failures are fail-soft.** Decision carryover, optimization/norm branches,
   shadow mirroring, queue-handle persistence and embedded Excel generation may log
   or degrade while a broader operation continues. Silent/weakly visible omissions
   require explicit golden journeys.
6. **Legacy decision typing is permissive.** The decision field is not constrained to
   an enum and carryover can intentionally produce an empty pending verdict. A new
   contract must preserve the user-visible state without copying weak typing.
7. **Dual filesystem layouts and shadow mirroring exist.** They are migration
   implementation details, not stable identities or authorization to dual-write.
8. **Runtime/UI/provider parity is unknown.** Static inspection cannot establish
   provider wording, visual layout, latency, concurrency timing, deployment flags or
   actual production data compatibility.

## 8. W0-BHV-02 characterization candidates

All fixtures must be synthetic, minimal and free of credentials, customer data,
production PDFs, generated production payloads and provider recordings containing
sensitive content.

| Candidate | User-verifiable journey | Required assertions |
|---|---|---|
| GJ-01 | Precheck then ingest a synthetic PDF/Markdown/JSON companion as V1 and V2 | Duplicate/conflict statuses, immutable source identity, version output isolation and explicit invalid-extension/path failures |
| GJ-02 | Interrupt after each major audit stage and resume/retry/skip where allowed | Exact stage alias, artifact reuse/invalidation, persisted status and visible error; cover text-before-block and block-before-text variants |
| GJ-03 | Review a finding, rerun on V+1 with provider failure, then manually resolve | Existing decision is not overwritten, carryover stays pending/manual-review, provenance remains visible |
| GJ-04 | Revoke/correct an expert decision | Capture legacy replacement/deletion behavior separately from the desired append-only target; require explicit product approval for new semantics |
| GJ-05 | Re-run comparison with identical signature, then change a source/exclusion/link | Idempotent reuse, downstream stale invalidation, partial AI-group reuse, raw deterministic evidence unchanged |
| GJ-06 | Apply high-confidence sheet-link repair and undo | Snapshot restoration, repair audit record and deterministic downstream recomputation |
| GJ-07 | Export package once with Excel success and once with generator failure | Successful member inventory and explicit characterization of legacy ZIP-without-Excel behavior |
| GJ-08 | Worker disconnects, reconnects and resumes a chunk upload | Outbox sequence/ACK dedup, reconciliation action, checksum and no duplicate publication |
| GJ-09 | Mark attempt lost, create a new attempt, then deliver the old result late | New attempt authority, old result stored-only, visible history and stale rejection |
| GJ-10 | Crash the center during result apply and restart | Journal recovery/rollback, same-hash replay, different-hash conflict and publish-after-validation |
| GJ-11 | Exercise disabled/enabled distributed route configurations | Status/admin/agent/bootstrap route visibility and authorization boundaries |

Live LLM text equality is explicitly out of scope. Provider-dependent journeys need
a deterministic fake/recording whose data is repository-approved and synthetic.

## 9. Commands and inspection limitations

The principal read-only commands were:

```bash
git -C /root/projects/PDF-proverka/PDF-proverka cat-file -e '32b9d903792b30506048a1d42b0e6b2d07aee403^{commit}'
git -C /root/projects/PDF-proverka/PDF-proverka show -s --format='%H%n%ci%n%s' 32b9d903792b30506048a1d42b0e6b2d07aee403
git -C /root/projects/PDF-proverka/PDF-proverka ls-tree -r --name-only 32b9d903792b30506048a1d42b0e6b2d07aee403 -- backend frontend
git -C /root/projects/PDF-proverka/PDF-proverka grep -l 'APIRouter(' 32b9d903792b30506048a1d42b0e6b2d07aee403 -- 'backend/app/api/routers/*.py'
git -C /root/projects/PDF-proverka/PDF-proverka grep -n 'include_router' 32b9d903792b30506048a1d42b0e6b2d07aee403 -- backend/app/main.py
git -C /root/projects/PDF-proverka/PDF-proverka grep -n -E 'class AuditStage|_stage_models|_STAGE_MODEL_DEFAULTS|CRITICAL_STAGE_MODEL_STAGES|valid_stages =|stage_to_pipeline_stage|_normalize_ocr_stage|ocr_stages =|stage_order =|_PIPELINE_STAGE_ORDER_KEYS|_PIPELINE_STAGE_ORDER =|_PIPELINE_STAGE_ALIASES|_PIPELINE_STAGE_ARTIFACTS|PIPELINE_STAGE_OF|SCOPE_OF_PIPELINE_STAGE|STAGE_MODEL_KEYS|MANDATORY_STAGES|CENTER_ONLY_PIPELINE_STAGES|REMOTE_AUDIT_PILOT_STAGES|CENTRAL_ONLY_STAGES|FORBIDDEN_STAGES|AUDIT_MODEL_STAGES|_STAGES =|VALID_STAGES|STAGE_VALUE_ALIASES|TASK_STAGE_ORDER' 32b9d903792b30506048a1d42b0e6b2d07aee403 -- backend/app/models/audit.py backend/app/core/config.py backend/app/api/routers/audit.py backend/app/pipeline/manager.py backend/app/pipeline/resume_detector.py backend/app/services/common/audit_logger.py backend/app/services/common/project_service.py backend/app/services/audit_routing/compiler.py backend/app/services/audit_routing/presets.py backend/app/services/audit_routing/validator.py backend/app/models/distributed_workers.py backend/app/pipeline/remote_audit_runner.py backend/app/services/distributed_workers/provider_requirement.py backend/app/services/section_optimization_pipeline_service.py backend/app/services/section_optimization_replication_service.py backend/app/services/stage_comparison/stage_upload.py backend/app/services/storage/stage_artifacts.py frontend/static/js/distributed-feature.js
git -C /root/projects/PDF-proverka/PDF-proverka grep -n -E 'async def _run_ocr_pipeline|^[[:space:]]+stages = \[|const STAGES =|BASE_STAGE_MODEL_CONFIG|This module is NOT wired|class DocumentStage|norm_stages =' 32b9d903792b30506048a1d42b0e6b2d07aee403 -- backend/app/pipeline/manager.py backend/app/services/audit_routing/compiler.py backend/app/services/text_analysis/stage_gates.py backend/app/pipeline/stages/norms/runner.py frontend/static/js/app.js
git -C /root/projects/PDF-proverka/PDF-proverka show 32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py | nl -ba | sed -n '232,243p'
git -C /root/projects/PDF-proverka/PDF-proverka show 32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/stages/norms/runner.py | nl -ba | sed -n '300,330p'
git -C /root/projects/PDF-proverka/PDF-proverka show 32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/audit_worker_agent.py | nl -ba | sed -n '1228,1265p'
```

Targeted `git show`/`git grep` reads were limited to the committed source paths
cited by the ledgers and capability rows. No current-checkout file was read as
evidence. No database, upload, untracked path, generated result, provider process,
network endpoint or production payload was opened.

Sensitive-path handling:

- `.env.example` was discovered by tree metadata only and excluded without opening
  or reading its contents.
- `audit_worker/providers/openrouter_secret.py` was discovered by tree metadata and
  designated metadata-only/excluded. During an early broad outbox/reconciliation
  search, that path produced one match consisting only of a non-value docstring
  line. No secret, credential or value was accessed, copied or retained. The matched
  line is intentionally not quoted. The corrective action was to exclude that path
  explicitly and continue only with named non-sensitive committed source paths.

The exact early command whose scope required that correction was:

```bash
git -C /root/projects/PDF-proverka/PDF-proverka grep -n -i -E 'outbox|offline queue|replay.*event|event.*replay|reconcile' 32b9d903792b30506048a1d42b0e6b2d07aee403 -- audit_worker
```

Inspection limitations:

- Source-observed behavior was not executed, so success, timing, UI rendering,
  provider availability and concurrency outcomes remain unverified.
- Negative findings are bounded to the pinned committed tree and the recorded search
  scope.
- Binary/oversized artifacts were not copied or decoded. Only committed path
  metadata was used where needed for discovery.
- The mutable legacy checkout was dirty and changed further during concurrent work;
  a final metadata-only status check included architecture/operations documentation,
  scripts and tests. This task did not edit or read those checkout paths, and none is
  evidence here. `refs/heads/main` and the pinned Git object still resolved to the
  exact immutable SHA above at handoff time.
- Independent sampling is required before acceptance; this author has not counted
  self-review as the task's manual evidence check.
