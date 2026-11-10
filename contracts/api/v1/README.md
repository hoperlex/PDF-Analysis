# API v1 contract area

OpenAPI is introduced in S01/S02. Do not invent hundreds of endpoints from legacy. Add endpoints per vertical slice and freeze them before frontend implementation.

Minimum conventions:

- commands accept idempotency key where replay can duplicate effects;
- errors use domain error envelope;
- opaque IDs only;
- cursor pagination for growing lists;
- object-level authorization server-side;
- file reads return safe/scoped representations, not internal S3 key.

## Current contract `1.52.0` (`CRIT-SEAL-52`)

The second seal of the «Прецеденты» programme (plan-v5, ADR-0029). It closes three debts of the first seal ahead of the wave-5 tables, which move to 1.53.0 / `0066`:
`D-681` (the table of norm page renders), `D-682` (a memory case's comments) and `D-683` (a block finding has no text evidence). **No operation, one schema and two member changes;
nothing is removed**; migration `0065_norm_crop_render` (head `0065`); no identity prefix, no error code, no state machine.

- **`DecisionMemoryCase.comments` (`D-682`).** Optional, not in `required`: the experts' comments on the case, oldest first. Each is the new schema `DecisionMemoryComment`:
  `comment_id` (`dmk_...`), `decided_at` and `comment` (1 to 4000 characters), **no author**, as a decision names none. Absent when the server does not report them; present and empty when the case has none and for a forgotten case.
- **`FindingObservation.evidence` may be empty for a block observation (`D-683`).** It had `minItems: 1`. It now has none on the property, and the schema carries a JSON Schema
  `if`/`else`: `if` the observation has `grounding_kind: portal_block`, nothing more is required; `else` (every other observation, an absent `grounding_kind` included) `evidence` has `minItems: 1`.
  A block observation stands on the blocks the finding lists in `block_evidence`, not on a text span. `Evidence` is not touched. The rule is an `if`/`else`, not a `oneOf` of two restated
  objects, because the observation is a closed object (`additionalProperties: false`) and a branch of a `oneOf` would restate every member; the `else` adds no member. The generated web
  types are unchanged (an array already admits no items); the web admission is the web lane's.
- **Storage (migration `0065`).** `norm_crop_render`: the PNG of one norm page, made once from the page's one-page PDF and published as a Blob, one row per (custody binding, render profile),
  immutable. It is the norm side and KEEP, not memory content: it is registered in `scripts/recovery/blob_reference_audit.py` (the closed registry of Blob references), classified with the norm
  tables in the purge and the schema coverage, and the forget of a case does not touch it. Nothing writes it yet (`M7-NORM-PNG`).
- **Compatibility.** Additive for a reader: a client of 1.51.0 reads every answer of 1.52.0 unchanged (`comments` is optional and appears only where a later lane maps it; an empty
  `evidence` appears only on a block observation, which `one_list` runs publish and which stay off until the web admits them).

The API has 296 paths, 325 operations and 809 schemas; migration head `0065`. The domain catalogs are at candidate revision 69.

## Contract `1.51.0` (`CRIT-SEAL-50`, historical)

Slice for the «Прецеденты» programme (plan-v5, ADR-0029, ruling `R-154h` of 2026-11-10, which gave this seal the slot after the removal of the АР beta). It is a seal of
storage and surface only: **nothing behaves**, every operation answers `503 dependency_unavailable` (`details.dependency` the lane that owns it) until that lane fills its body.
The error catalogue is closed and has no 501, so this is the answer every earlier seal's stubs give. **Seven operations (listed below), twenty-nine schemas and a handful of optional members are
added; nothing is removed**; migration `0064_precedents_seal` (head `0064`); four identity prefixes; no error code and no state machine.

- **Operations (7).** `getExecutorTaskContext` (`POST /runner/tasks/{task_id}/context`): a runner token with the claim of the task asks, once per kind, for the decisions of experts on
  findings like the task's own; idempotent by (task, kind); `status: unavailable, reason: until_move` while the night encoder is the only one. `getRunPrecedents`
  (`GET /runs/{run_id}/precedents`) and `getFindingPrecedents` (`GET /findings/{finding_uid}/precedents`): the labels, the queue «Рекомендовано снять» and the card. `getVectorControl`
  (`GET /vector-control`) and `setVectorPaused` (`PUT /vector-control/paused`): the pause of the vectors and the state of the night window. `listPrecedentSettings` and
  `appendPrecedentSetting` (`GET` and `POST /precedent-settings`): the switches (`one_list`, `critic_context`, `section_labels`), the stop words, the window and the thresholds, journalled
  with the administrator. An expert and an administrator read; the viewer is denied (`permission_denied`); the writes and the settings are the administrator's, the two writes keyed.
- **Schemas added (29).** `ExecutorContextInput`, `ExecutorTaskContext`, `ExecutorTaskContextCase`, `ExecutorTaskContextItem`, `ExecutorTaskContextKind`, `ExecutorTaskContextRequest`,
  `ExecutorTaskContextStatus`; `FindingBlockBox`, `FindingBlockEvidence`, `FindingGroundingKind`, `FindingOrigin`; `PossibleNorm`, `PrecedentCase`, `PrecedentFindingLabel`, `PrecedentHint`,
  `PrecedentHintCode`, `PrecedentLabelCode`, `PrecedentPassState`, `PrecedentVotes`, `FindingPrecedents`, `RunPrecedents`; `PrecedentSetting`, `PrecedentSettingList`,
  `PrecedentSettingName`, `AppendPrecedentSettingRequest`; `SetVectorPausedRequest`, `VectorControl`, `VectorWindow`, `VectorWindowState`.
- **Optional members added.** `ClaimedExecutorTask.context_request` (a `review:main` task of a run on the stage layout only), `SubmitExecutorTaskAnswerRequest.context_sha256`, `block_evidence`
  and `origin` on `Finding` and `FindingDetail`, `FindingObservation.grounding_kind`. `FindingCategory` gains `drawing_discrepancy` and `cross_source`; `RunWaitCause` gains `vector_window`.
- **Not changed.** `Evidence` (a block is proved in `block_evidence`, a list of its own) and `RunStageChip` (the rail keeps its chips). No error code, no state machine.
- **Hints.** `PrecedentHintCode` is `p1`, `p4` and `p5`: the hints that were to serve the АР beta (`p2`, `p3`) are not built (`R-154`).
- **Storage (migration `0064`).** The memory's comments, block evidence, encoder queue and vectors (the forget guard, and a guard on INSERT into a forgotten case), the label in force and the
  history verdict shown on a decision, the probe, the pass and its advice, a finding's block evidence, the settings journal, the vectors' control and its journal, the journal of
  reference data handed to an agent (no foreign key, no text), `audit_run.publication_mode` (frozen at the start) and the grounding columns of an observation. `norm_crop_render` followed
  in 1.52.0 (migration `0065`), once `scripts/recovery/blob_reference_audit.py`, the closed registry of Blob references, was granted to the seal.
- **Compatibility.** Additive: a client of 1.50.0 reads every answer of 1.51.0 unchanged (the added members are optional, the added enum values appear only where a later lane writes them).

At that version the API had 296 paths, 325 operations and 808 schemas; migration head `0064`; the domain catalogs were at candidate revision 68.

## Contract `1.50.0` (`AR-V3-BE-RM-01`, historical)

Slice for the removal of the six-scope АР beta (owner rulings `R-154a`, `R-154c` and `R-154h` of 2026-11-10), with one additive member of the run-start readiness.
**Six operations, nineteen schemas, three `RunStatus` properties and four enum members are removed; one optional property is added**; migration `0063_drop_ar_v3_beta` drops the
beta's two tables and restores two earlier database objects (head `0063`). No error code and no state machine changes.

- **Version.** A strict reading of `VERSIONING_AND_FREEZE_POLICY` makes this a major; the owner chose 1.50.0 (`R-154h`) because the removed operations were a beta that never went
  live, and their only consumer, our web client, is regenerated here; 2.0.0 stays reserved for `D-233`.
- **Operations removed (6).** `startArV3BetaGroup`, `estimateArV3GroupCost`, `getArV3BetaGroup`, `getArV3BetaGroupReview`, `getArV3BetaPackStatus` and `getRunNormVerification`. The
  last one served the beta only: it answered `404 not_found` for a run of any other profile. The standard analysis of every section, the extended review and the stage comparison are
  not changed.
- **Schemas removed (19).** `ArV3BetaGroup`, `ArV3BetaGroupMember`, `ArV3BetaGroupReview`, `ArV3BetaGroupReviewMember`, `ArV3BetaPackReview`, `ArV3BetaPackStatus`, `ArV3BetaStageId`,
  `ArV3BetaVisibleCitation`, `ArV3BetaVisibleEvidence`, `ArV3BetaVisibleProposal`, `ArV3BetaVisibleReview`, `ArV3BetaVisibleTopic`, `ArV3GroupCostEstimateRequest`, `ArV3RunGroupId`,
  `StartArV3BetaGroupRequest`, `NormVerificationReport`, `NormFindingVerification`, `NormObservationCitationPartition` and `UngroundedReason` (referenced by nothing else).
- **Narrowed.** `RunStatus` loses `analysis_kind`, `ar_v3_group_id` and `ar_v3_scope_id` and its `degradation_set` holds `StageId`; `StageState.stage_id` is `StageId`;
  `RunCostEstimate.scope` is `run`; `RunStageChip` loses `ar_v3`; `ComparisonRefusal.reason` loses `analysis_not_comparable`. The prose that named the beta is corrected
  (`ExecutionQueuePage.live_failure_count`, `DocumentActiveRun`, `DocumentAuditCounts`, `RunStageChip`, `uploadDocument`, `estimateRunCost`, `reauditRun`, `getRunStages`,
  `startRunFromStage`); the history of the earlier seals in `info.description` is kept.
- **Added (optional).** `RunStartReadiness.extended_plan`: `v2`, `v3`, or `null` when the extended analysis is off. It is read through the same call the estimate prices with, so it cannot
  disagree with it; under `v2` the critic and refinement rows are not called, and the client labels them from this field.
- **Domain and analysis contracts.** The identity prefix `arg` (`ar_v3_run_group_id`, entity `ArV3RunGroup`) leaves the identifier catalogue and its schema; the conflict reasons
  `ar_v3_start_not_enabled` and `ar_v3_member_not_repeatable` leave the `conflict` notes of the error catalogue (the catalogue keeps its 27 codes); the candidate revision is 67.
  `contracts/analysis/ar_v3_beta/**` is deleted, and the optional `norms.snapshot` input of `text_analysis` no longer says it serves the beta.
- **Compatibility.** A client that read a removed operation or property must stop reading it; no consumer outside this repository is known. A server of this version answers the
  removed paths with `404`. The database refuses the upgrade while any row of the beta exists (see migration `0063`).

At that version the API had 290 paths, 318 operations and 779 schemas; migration head `0063`; the domain catalogs were at candidate revision 67.

## Contract `1.49.0` (`LIMITS-01`, historical)

Slice for `LIMITS-01` (owner rulings `R-153n`, `R-153o` and `R-153p` of 2026-11-10): **no answer cap reaches a model, and the window of a call is a constant of its
row**. **No operation, no schema added or removed, no migration, no new error code, no state machine and no identity prefix**; migration head stays `0062`. The paths
and operations are those of `1.48.0`.

- **`StageLayoutCell`, `StageComparisonCell` and `RunStageCell` lose `max_output_tokens` and `timeout_seconds`.** A layout cell (the six rows, with the roles of the blocks
  ensemble, and the four kinds of comparison work) is a model and an effort, and a stage line of a run is the cell the run froze with its access and server.
  `reviseStageModelLayout` refuses a cell that still names either member, `422 validation_failed` (the objects stay closed: an unknown member is refused, not ignored).
  The layout of a revision stored before still reads: the two numbers it holds per cell are not read and not shown.
- **`ClaimedExecutorTask` loses `max_output_tokens`.** The host members of a task are now `provider`, `access`, `model_id`, `effort`, `timeout_seconds` and `cell_key`, all
  six or none. No answer cap reaches a model: the agent runs the Claude Code command without `CLAUDE_CODE_MAX_OUTPUT_TOKENS`, Codex has none, OpenAI Responses and
  OpenRouter get no output-token parameter, and Anthropic Messages, which requires `max_tokens`, gets the model's maximum. `timeout_seconds` stays: it is the constant of the
  cell's row (text 1800, blocks 1800, cross-check 3600, norms 600, critic 600, refinement 600; the comparison kinds 900, 1800, 900 and 2400, the original's), cut to what the
  attempt watchdog leaves.
- **Compatibility.** An agent of this version reads a task of an older stand and ignores its `max_output_tokens`, so it can be installed first. An older agent refuses a
  task without it (`host_task_incomplete`), so the agent is reinstalled before or with the stand. The `ComparisonAiRoute.cell` of an estimate stored before is shown without the
  two numbers.
- **Not changed.** Every operation, every other schema, the stage plan's key and model, and every error code. The agent's silence window (`R-153p`, 120 to 600 s) is not a
  contract member.

The API has 296 paths, 324 operations and 798 schemas; migration head `0062`. The domain catalogs are at candidate revision 66.

## Contract `1.48.0` (`HOSTS-L1`, historical)

Slice for `HOSTS-L1` (lane of the HOSTS wave, 2026-11-10; `D-660`): **a waiting planned run names the cells it waits for**. **No operation, two new
schemas, one widened one, no migration, no new error code, no state machine and no identity prefix**; migration head stays `0062`. The paths and
operations are those of `1.47.0`.

- **`RunStatus.wait_cells`** (optional, 1 to 32 items) lists the cells of a run started on the stage layout that cannot be bound now, in the order of
  the run's frozen plan, as the new `RunWaitCell`: `cell_key`, `model_id` and `access` (the plan's own, `ExecutorModelAccess`) and `cause`, the new
  closed enum `RunWaitCause`. It is present **only** while the run is `queued` with `binding_state` `pending` and a `wait_reason`, and at least one
  cell has no server to take it; it is omitted otherwise and never an empty list.
- **`RunWaitCause`** is the six words of `ModelUnavailableReason` (`host_disabled`, `host_offline`, `login_required`, `model_not_verified`,
  `model_cooling_down`, `not_on_any_server`: no available server for the cell's model and access) and `at_capacity` (a server serves the model and
  every place for it is taken). `wait_reason` keeps its meaning: `model_unavailable` when any cell has a cause other than `at_capacity`,
  `executor_at_capacity` when every cell has only that. The status carries no server: a cell names a model and a cause, never a host.
- **How it is read.** One read, no table: the status asks `executors.public.evaluate_wait` (the evaluation the sweep keeps `wait_reason` true with)
  over the cells of the plan at the time of the request, so it can differ from the stored `wait_reason` by one sweep. A run that could be bound now
  names no cell.
- **A planned run has no `planned` and no `binding`.** It holds a plan and no group, rule, connection or preset of its own, so the status of a
  `pending` or `bound` planned run reports `binding_state` (and, while it waits, `wait_reason`, `waiting_since` and `wait_cells`) and nothing of
  `planned` and `binding`. Before this seal the status reading looked for a group revision that a planned run does not have
  and would have refused with `internal_error`.
- **The model catalogue gains `gpt-6-luna`** (`contracts/analysis/v1/model-catalogue.json`; `D-667`, owner ruling `R-153m`): the Codex client
  (subscription and API), the OpenAI API and OpenRouter serve it at `low`, `medium` and `high`, and `docs/program/P02_LOCK.json` pins it with the
  Standard rates read on 2026-11-10 ($0.10 input, $0.50 output per 1M tokens). The table of « Только Codex » now gives `comparison_pair_check` and
  `comparison_spec` `gpt-6-luna` high (the original's `sheet_match` and whole-specification model), with the limits and windows of `1.47.0`
  unchanged; `comparison_sheet_changes` and `comparison_report` stay `gpt-6.1-sol` high. A revision that stored its comparison cells keeps them; one
  that follows the table of its set serves the new one. No schema changes for it: the model is a value of `model_id`.
- **Not changed.** Every operation, every other schema, the stage plan a run freezes and every error code.

The API has 296 paths, 324 operations and 798 schemas; migration head `0062`. The domain catalogs are at candidate revision 65.

## Contract `1.47.0` (`HOSTS-SEAL-3`, historical)

Slice for `HOSTS-SEAL-3` with `HOSTS-CMP-01` (ADR-0028 decision 19; decisions of the HOSTS integrator, 2026-11-10): **the comparison of versions on the stage
layout**. **No operation, two new schemas, three widened ones, no migration, no new error code, no state machine and no identity prefix**; migration head
stays `0062`. The paths and operations are those of `1.46.0`.

- **The cells.** The four kinds of comparison work that call a model -- `comparison_pair_check`, `comparison_sheet_changes`, `comparison_spec` and
  `comparison_report` (the new enum `ComparisonLayoutKind`; `comparison_stage_review` has no handler and is not offered) -- each get one cell of the
  layout, `StageComparisonCell`: `work_kind`, `model_id`, `effort`, `max_output_tokens` (1 to 65536) and `timeout_seconds` (1 to 7200). The model and the
  effort are a pair of `listModelCatalogue`, as for a row. The analysis rows (`StageRowKey`, `StageLayoutCell`) are unchanged: no existing reader changes.
- **The layout.** `ReviseStageModelLayoutRequest.comparison_cells` is **optional**: the four cells, each kind once. A named kit
  (`claude_only`, `codex_only`) must have the models and efforts of its table (a limit or a timeout may be longer or shorter, as for the rows); `custom`
  may name any pair of the catalogue. `StageLayoutRevision.comparison_cells` returns the cells **in force**: what the revision stored, else the table
  of its kit -- so a revision made before this seal serves with the kit's defaults. It is absent only for a `custom` revision that stored none: its
  comparison kinds have no cell, and a comparison is refused (`503 dependency_unavailable`, `executor_route_missing`), never served by a model nobody
  chose. `StageModelLayout.unavailable_cell_keys` also names a comparison cell (`comparison_pair_check:main`) whose model no server serves.
- **The tables** (the original's `version_comparison_ai` settings mapped onto the catalogue; the original's `gpt-6-luna` is not a pin, so it is
  `gpt-6-astra`): « Только Codex » -- pair check `gpt-6-astra` high, 1200 tokens, 900 s; sheet changes `gpt-6.1-sol` high, 8192, 1800 s; specification
  `gpt-6-astra` high, 32000, 900 s; report `gpt-6.1-sol` high, 8000, 2400 s. « Только Claude » -- `claude-sonnet-5-5` high for all four, with the same
  limits and windows.
- **The route.** `ComparisonAiRoute.cell` (optional) is the cell a comparison job froze. While the layout is switched on, an estimate or a start of one
  of the four kinds is served by the system group of the cell's model (a subscription before an API key; the group revision, not a connection, is the
  route), so it is a route of the group shape (`executor_group_id`, `executor_group_revision_id`, no `routing_rule_revision_id`) with the `cell`. **The
  estimate digest binds the cell**: the consent names what will run. A kind whose model no server serves is refused at the estimate and at the start with
  `503 dependency_unavailable`, `executor_route_missing`; it is not routed to a legacy connection or a rule. With the layout switched off the route is
  what it was.
- **The call.** The cell's effort replaces the module's, its limit is a ceiling over the module's own (`min(module limit, cell limit)`, also in the
  estimate's `output_tokens`) and its timeout is the window of the call to the server. A job admitted by the legacy route or by a rule keeps today's
  values.
- **Prose corrected.** The description of `startRun` said that a start that finds another rate or another access since the estimate was read answers
  `409` with `conflict_reason` `cost_estimate_binding_changed`. The code, its tests and ADR-0028 decision 8 answer `422 analysis_input_invalid` with
  `details.reason` `cost_estimate_binding_changed`, before the key is claimed; the description now says so (prose only, no schema change).
- **Not changed.** Every operation, every other schema, the stage plan a run freezes (it holds the six rows only) and every error code.

The API has 296 paths, 324 operations and 796 schemas; migration head `0062`. The domain catalogs are at candidate revision 64.

## Contract `1.46.0` (`HOSTS-SEAL-2`, historical)

Slice for `HOSTS-SEAL-2` with `RUN-STAGES-01` (ADR-0028; plan section 9.4 of the owner-approved plan of 2026-11-09): **the stages of a run, plan and
fact**. **One operation, seven schemas, no migration, no new error code, no state machine and no identity prefix**; migration head stays `0062`.

- `getRunStages` -- `GET /runs/{run_id}/stages` (`runs`; `role:admin|expert|viewer`, a product read like `getRunStatus`): the data of the window
  «Этапы анализа раздела». For each chip the run has, **in the order the rail draws them** (`preparation`, `text`, `blocks`, `cross_check`,
  `merge`, `norms`, `review`, `correction` and, for the AR v3 profile, `ar_v3`; a chip that no stage result, procedure, plan cell or call mentions
  is not listed) it answers `stage_ids` (the code stage and procedure ids the chip covers), `plan` and `facts`.
- **`plan`** is the run's frozen `stage_plan` cells for the chip's row -- `role`, `model_id`, `effort`, `max_output_tokens`, `timeout_seconds`,
  `access` and, once the cell is bound (`audit_run_cell_binding`), `server`, the display name of the host. A run that froze no `stage_plan`
  (`plan_source` `run_binding`) has one line per chip that calls a model, `role` `main` and the model its binding pins (the server and access of its
  binding too; with no binding, the model the journal names). A chip that calls no model (`preparation`, `merge`) has an empty plan.
- **`facts`**: `state` (`pending`, `running`, `done`, `partial`, `failed`, `skipped`, `unavailable`); `started_at` and `finished_at` (the earliest and
  the latest call of a chip that calls a model, else the times of its stage results; `finished_at` only once the chip has finished, and none from a
  stage taken from an earlier run, which is named by `reused_from_run_id`); `calls_succeeded`, `calls_failed`, `calls_retried`; `input_tokens`,
  `output_tokens`, the part of them served by a subscription (`subscription_input_tokens`, `subscription_output_tokens`) and `cost_micros`;
  `last_error_code`; `reason` (the extended review's reason a procedure did not complete); and `planned` and `completed`, the batches of the
  extended review's `phase_coverage`, absent where the review keeps none.
- **Where the facts come from.** The PC-01 `stage_result` rows; the extended review artifact through its custody-checked reader (`procedures` for the
  state, `phase_coverage` for the batches); the call journal (`model_call` and `provider_call_effect`), each call placed on a chip by its `stage_key`
  (written since `0062`) or, for an older row, **derived at read time** from `parameters ->> 'extended_phase'`. A journal row whose key or phase is
  unknown is `500 storage_integrity_error`, never a guess.
- **The viewer** («Наблюдатель», `R-150w`) reads the stages but not the server nor the access: both are absent from every cell of its answer (not
  null). An expert and an administrator see everything.
- **Not changed.** Every other operation, schema and error code. No page calls the new operation yet (`RUN-SCREEN-01`).
- **Details the stand answers on existing codes** (`HOSTS-INT-WIRE-01`, which wired `HOSTS-BACKEND-01` and `HOSTS-LAYOUT-01`; prose only: no schema,
  no operation and no version change, and `error-codes.json` carries the same notes).
  - `409 conflict`, `details.conflict_reason`: `system_managed` (a connection or group the stand keeps for a server is revised, archived, keyed,
    probed, routed, enrolled or named by a rule by hand), `host_name_in_use` (a live server holds the name), `host_archived` (a write names an
    archived server), `host_in_use` (`archiveExecutorHost` while a bound run still holds a unit of the server's pool) and `upgrade_blocked_by_use`
    (a host enrollment or install under the name of a single-model `pull` connection that a route or a rule still uses, until `HOSTS-CMP-01`).
  - `422 validation_failed`, `details.field` `slots` or `providers` (and `key_file` or `agent_version`) with a `constraint` that names what the
    request got wrong: for `slots` `required`, `range` (1 to 16), `type` and `provider_not_reported`; for `providers` `required`, `length`, `type`,
    `enum`, `access`, `auth_state`, `unique`, `accept_images`, `models`, `checked_at`, `failure_code` and `verified_without_login` (a provider that is
    not logged in has no verified model); `host_token_only` (a connection token sends `providers`, `slots`, `key_file`, or a host answer's
    `provider`/`reported_model`: it speaks the earlier wire); on a host token's answer `provider`, `access` and `reported_model` `required`, and
    `provider` or `access` `not_the_task`. A value is never echoed.
  - `503 dependency_unavailable`, `details.dependency` `model_catalogue`: `contracts/analysis/v1/model-catalogue.json` cannot be read; there is no
    built-in copy to fall back to.
  - The answer of `reportRunnerHealth` and `submitExecutorTaskAnswer` for a model that is not the task's is the runner's existing refusal; for a host
    token the model that *answered* (`reported_model`) is held to the catalogue's `accepted_reported` for the task's model, exactly (`R-133`).
  - **A start on the stage layout that finds another rate or another access since the estimate was read** is refused with the existing
    cost-preflight refusal, `422 analysis_input_invalid` with `details.stage_id` `text_analysis` and `details.reason`
    `cost_estimate_binding_changed`, before the key is claimed, and the client reads `getRunStartReadiness` again. (The description of `startRun` in
    `openapi.json` said `409` with `conflict_reason`, which is not what the stand answers; `1.47.0` (`HOSTS-SEAL-3`) corrects that prose to
    `422 analysis_input_invalid` with `details.reason` -- prose only, no schema change.)

The API has 296 paths, 324 operations and 794 schemas; migration head `0062`. The domain catalogs are at candidate revision 63.

## Contract `1.45.0` (`HOSTS-SEAL-1`, historical)

Slice for `HOSTS-SEAL-1` (ADR-0028; the owner-approved plan of 2026-11-09): **servers** (hosts) and **the models of the analysis stages**.
**Fifteen operations, forty-three schemas, one parameter, no new error code and no new state machine**; migration `0062_hosts_stage_models`; five
identity prefixes (`exh`, `exhu`, `exhs`, `slr`, `sls`). Nothing behaves differently until the wave-1 lanes implement an operation: the shipped
adapters answer `503 dependency_unavailable`.

- **Servers** (`execution`). `listExecutorHosts` (`GET /executor-hosts`) and `getExecutorHost` (`GET /executor-hosts/{host_id}`) --
  `role:admin|expert`, the viewer denied (`R-150w`); `getExecutorHostDetails` (`GET .../details`, `role:admin`): slots, the reasons a model is
  unavailable (`host_disabled`, `host_offline`, `login_required`, `model_not_verified`, `model_cooling_down`) and the tasks running;
  `setExecutorHostEnabled` (`PUT .../enabled`, the «Использовать» switch) and `setExecutorHostSlots` (`PUT .../slots`) -- `role:admin`, keyed,
  each change an append-only event with its author; `archiveExecutorHost` (`POST .../archive`, one-way, not deletion).
- **Connecting a server** (`role:admin`, keyed, no model). `issueExecutorHostEnrollment` (`POST /executor-hosts/enrollments`),
  `createExecutorHostAgentInstall` (`POST /executor-hosts/agent-installs`), `getExecutorHostAgentInstall` and
  `confirmExecutorHostAgentInstallHostKey` (under `/executor-hosts/{host_id}/agent-installs/{install_id}`) are the host-targeted forms of
  `issueExecutorEnrollment`, `createExecutorAgentInstall`, `getExecutorAgentInstall` and `confirmExecutorAgentInstallHostKey`, which are
  **unchanged** and stay the forms for a `pull` connection until the comparison routes move to the hosts. `RunnerTokenMetadata`,
  `ExecutorEnrollmentMetadata` and `ExecutorAgentInstall` name exactly one of `connection_id` and `host_id`.
- **The stage layout.** `getStageModelLayout` (`GET /model-layout`, `role:admin|expert`), `reviseStageModelLayout`
  (`POST .../revisions`, an immutable revision with its author) and `setStageModelLayoutEnabled` (`PUT .../enabled`, the switch and its journal) --
  the writes `role:admin`, keyed; `listModelCatalogue` (`GET /model-catalogue`, `role:admin|expert`), the content of
  `contracts/analysis/v1/model-catalogue.json`; `getRunStartReadiness` (`POST /runs/start-readiness`, a read with the body of `estimateRunCost`,
  `role:admin|expert`): the route, every cell of the plan a start would freeze with its access, whether the start is possible and the digest of
  the estimate to confirm.
- **The runner protocol, host mode** (a token bound to a connection keeps the earlier wire). `redeemExecutorEnrollment` answers `token`, `host_id`
  and `catalogue` (and `runner_token` is optional); `reportRunnerHealth` carries `providers[]`, `slots` and `key_file` and is answered with
  `catalogue` and `enabled`; a claimed task carries `provider`, `access`, `model_id`, `effort`, `max_output_tokens`, `timeout_seconds` and
  `cell_key` (all seven or none) and `model` equals `model_id`; `extendExecutorTaskClaim` is sent only while the call has produced output in the
  last 120 s; `submitExecutorTaskAnswer` carries `provider`, `access`, `reported_model` (the exact string, held against `accepted_reported`) and
  `usage`. `RunnerExecutionProfile` gains no value and `clis` stays required. The text is `tools/executor-runner/RUNNER_API.md` section 10.
- **Runs and the estimate.** `RunQueueReason` gains `model_unavailable`; `ExecutorGroupMemberIssue` gains `host_disabled`, `model_not_verified` and
  `model_cooling_down`. `RunCostEstimate.billing` gains `mixed`, and the estimate carries `stage_plan_digest` and `models` (a line per model:
  the digest of its rates, its access, calls, tokens and cost) -- the consent v2. `RunCostConsent` is unchanged and gains examples. With the layout
  switched on the explicit executor selectors of `startRun` and `estimateRunCost` are `422 validation_failed`; `reauditRun` and `startRunFromStage`
  take today's layout.
- **Not changed.** Every other operation, schema and error code. No page calls the new operations yet.

The API has 295 paths, 323 operations and 787 schemas; migration head `0062`. The domain catalogs are at candidate revision 62.

## Contract `1.44.0` (`DECISION-MEMORY-M2`, historical)

Slice for `DECISION-MEMORY-01` phase M2 (`ADR-0027`): the expert decision memory, the copy of what an expert saw and said when a decision was
taken, which outlives its project and document. **Five operations, fourteen schemas, no new error code and no new identity prefix** (migration
`0061_decision_memory_m2`).

- `listDecisionMemoryCases` -- `GET /decision-memory/cases` (`role:admin|expert`): newest capture first (`cursor`, `limit`), filtered by
  `section_code`, `category`, `verdict` (the latest decision's), `status` (`active`, `withdrawn`, `forgotten`), `data_class` and
  `origin_project_uid`. `DecisionMemoryCasePage`.
- `getDecisionMemoryCase` -- `GET /decision-memory/cases/{case_id}` (`role:admin|expert`): the case with its content, decisions (the expert's
  own comments), evidence, normative references, crop references and the history of its standing. **A forgotten case answers its tombstone
  only** (`content` is `null`, the lists are empty). `DecisionMemoryCase`.
- `getDecisionMemoryStatus` -- `GET /decision-memory/status` (`role:admin`): counts by standing and data class and the installation settings in
  force (`data_class`, `training_use`; nothing journalled means `test` and `off`). `DecisionMemoryStatus`.
- `withdrawDecisionMemoryCase`, `restoreDecisionMemoryCase` -- `POST /decision-memory/cases/{case_id}/withdraw` and `/restore` (`role:admin`,
  `Idempotency-Key` required, body `DecisionMemoryStatusChangeRequest`: a closed `reason_code`): an append-only status event; a case already in
  that state is `409 state_transition_not_allowed`, a forgotten case `409 conflict` with `conflict_reason: memory_case_forgotten`, an unknown one
  `404`. `DecisionMemoryStatusChange`.
- **Not operations.** *Forget* (it deletes content and objects) and the settings stay operator tools (`scripts/recovery/memory_forget.py`,
  `memory_setting.py`); `streamDecisionMemoryCrop`, the similar-cases hint and the training export belong to later phases. The viewer role does
  not read the memory (it holds the experts' own words and quotes of client documents). The memory is not a decision authority: while the
  source finding exists the ledger decides.
- **Not changed.** Every existing operation, schema and error code. No page calls the new operations yet.

The API has 280 paths, 308 operations and 744 schemas; migration head `0061`. The domain catalogs are at candidate revision 61.

## Contract `1.43.0` (`UI-PARITY-C7`, historical)

Slice that closes five open debts end to end (`D-335`, `D-346`, `D-361`, `D-370`, `D-395`). **No operation, no schema, no migration (head stays
`0060`), no error code.** Optional members and one optional query parameter only; every one is additive, so a client that does not know
them reads the same answers as before.

- **`D-335` -- the source of a carried proposal decision.** `ProposalDecisionRecord` (`listProposalDecisionJournal`, and the `proposal` of
  a `listKnowledgeBaseEntries` entry) gains the optional `carried_from` (`ProposalDecisionCarriedFrom`: the source decision, the pass and
  version it was made in, and the version's display ordinal), present only for a decision an expert carried over from an earlier
  version's pass and absent for one made directly -- as `ProposalDecision` and `AcceptedOptimisationProposal` already carry it.
- **`D-346` -- the percent beside the saving.** `AcceptedOptimisationProposal` gains the optional `saving_percent`, the very figure
  `OptimisationProposal.saving_percent` states (computed by the same function over the two stored unit prices; present where `saving` is
  `null`, absent only at a zero current price). The proposals **CSV** (`exportOptimisationProposalsCsv`) gains `saving_percent` among its
  **last** columns (only the carried mark below follows it): the file is read by position by whoever scripts against it, so a column in
  the middle would shift every one after it. The proposals **workbook** (`exportOptimisationProposalsXlsx`) gains «Экономия, %» after «Экономия»: its way back
  (`importOptimisationProposalDecisions`) finds «ID предложения», «Решение эксперта» and «Комментарий» by their headers, so the two
  edited columns move one place right and nothing reads them by position. An empty cell is an absent percent, never `0`.
  **`D-335` -- the carried mark in the same exports.** The CSV's last column is `decision_carried_from_version` (the display ordinal of the
  earlier version the decision **in force** was carried over from; empty for a decision made directly and for a proposal with none in
  force, a withdrawn one included); the workbook's last column is «Перенесено из версии» («V2» or empty), after the two an expert edits, so
  none of them moves.
- **`D-370` -- a group of states.** `listExecutionQueue` takes the optional `state_group`: `active` (`queued`, `leased`, `running`,
  `retry_wait`), `completed` (`succeeded`, `cancelled`) or `errors` (`failed`, `dead_letter`) -- the original's three sub-tabs. It lists
  every job in any state of the group, one paged list with the page's `overview` and cursor as for any other filter; the cursor is bound
  to it (`validation_failed`, `constraint: scope`, under another). `state` and `state_group` are two spellings of one filter and are
  refused together (`422 validation_failed`, `field: state_group`, `constraint: conflicts_with_state`), never merged by a guess.
- **`D-395` -- the failures nobody has answered.** `ExecutionQueuePage` gains the optional `live_failure_count`: the jobs in `failed` or
  `dead_letter` with no **later job for a run of the same document version and the same analysis**. A job belongs to exactly one run, so
  the original's "retried or superseded" is read as the version having been run again since (a re-audit, a start from a stage, a plain
  new run, whatever became of it); a later job that failed too is the one that counts. Over all history, whatever the period or state
  filter of the page, so a one-row page carries it: the side menu's red mark reads it and the 24-hour acceptance window of `D-331` is gone.
- **`D-361` -- the optimisation of a document.** `DocumentAudit` (the `audit` of each `listDocuments` item) gains the optional
  `optimisation_proposal_count` and `optimisation_undecided_count`: the proposals of the version's latest optimisation pass and, of
  those, the ones with no decision in force (none, or a withdrawn one) -- the original's «Оптимизация N» pill. Both are present when a
  pass was started over the version and both are absent when none was (absent is "no optimisation read", never zero). Read in the same
  statement as the audit; a fact beside the four words, which it changes none of (`R-150u`), and the counters do not read it.
- **Not changed.** Every operation, schema, error code and the migration head.

The API still has 275 paths, 303 operations and 730 schemas; migration head `0060`. The domain catalogs are at candidate revision 60.

## Contract `1.42.0` (`UI-PARITY-S2`, historical)

Slice for register row `UI-A-60` (ruling `R-151i`, debt `D-301`): «Запустить с этапа». **One operation, one migration (`0060_run_from_stage`),
no error code.** One new schema, `StartRunFromStageRequest`; optional properties on `RunStatus`, `RunCostEstimateRequest` and
`RunCostEstimate`. The design, with the reuse rule and the idempotency key, is `docs/program/RUN-FROM-STAGE-01.md`.

- **`startRunFromStage`** (`POST /runs/{run_id}/start-from-stage`, `expert` or `admin`, keyed, `202`): a **new** run of the earlier
  run's document version that reuses the earlier run's completed outputs of every PC-01 stage before `stage_id` and computes
  `stage_id` and the stages after it. The earlier run is immutable history and is not changed. `stage_id` is one of
  `page_geometry_extraction`, `document_context_build`, `text_analysis` (the first stage reuses nothing: `422 validation_failed`,
  `constraint` `nothing_to_reuse`, use `reauditRun`; any other is `stage_not_startable`). The new run records today's configuration
  exactly as a re-audit does (`R-82`).
- **A stage output that cannot be taken** is `422 analysis_input_invalid` with `details.stage_id` (the first stage that cannot) and
  `details.reason`: `source_stage_not_completed`, `source_stage_version_changed`, `source_stage_output_incomplete`,
  `source_artifact_unavailable`, `source_artifact_changed`, `source_stage_inputs_changed`. Nothing is recomputed in its place and
  nothing is written. The earlier run must have ended (`409 state_transition_not_allowed`) and be a standard run (an AR v3 member:
  `409 conflict`, `ar_v3_member_not_repeatable`).
- **`RunStatus`** gains the optional `started_from_run_id` and `start_stage_id` (both or neither; absent for a run started from a
  version or as a re-audit, which keeps `reaudit_of_run_id`). **`estimateRunCost`** takes the optional `start_from_run_id` and
  `start_stage_id` (both, and nothing that chooses a route) and **`RunCostEstimate`** answers `start_from_run_id`, `start_stage_id`,
  `reused_stage_ids` and `computed_stage_ids`: the price is for the computed stages, and the digest is bound to the earlier run and
  stage, so a digest of a re-audit or of another stage is `run_cost_estimate_stale`.
- **Idempotency.** The caller's `Idempotency-Key`; the fingerprint is the earlier run, the stage, the earlier run's stored digest and
  the consent. The same key with the same request replays the run; with another stage it is `idempotency_key_reuse`. While a run
  from the same earlier run and stage has not ended, a second is `409 conflict`.
- **Not changed.** `reauditRun`, `startRun`, the stage vocabulary, the error catalogue and every other operation.

The API then had 275 paths, 303 operations and 730 schemas (the new schema was `StartRunFromStageRequest`); migration head `0060`
(chained after `0059_decision_memory`). The domain catalogs were at candidate revision 59.

## Contract `1.41.0` (`UI-PARITY-C6`, historical)

Slice for register rows `UI-A-74`, `UI-A-82` and `UI-A-84` (the portal blocks that hold a finding's evidence: the thumbnails under an
opened finding, the number of findings on a block tile, «Без сущностей»). **One operation, no migration, no error code** (head stays
`0058`). Two new schemas, `FindingBlockLink` and `RunFindingBlockLinks`.

- **`listRunFindingBlocks`** (`GET /runs/{run_id}/finding-blocks`, any one role): one item per published finding of the run, with
  `portal_block_ids`, the portal blocks that hold the evidence of the finding's canonical observation and of every observation merged into it (`D-520`): the canonical observation's blocks first in the portal list's order, then each merged observation's in observation-id order, every block once. A
  **derivation on read**, nothing stored and no evidence changed: the evidence's characters are located on their page by the
  run's own text-layer block index (the line boxes, `geometry.block_index`) and page inventory (`prepared.page_inventory`), the
  evidence's box is the part of the line its characters occupy, and a portal block (the version's `geometry.portal_blocks`, the
  document `listVersionPortalBlocks` serves) holds the evidence when it covers at least half of that box. The rule, with its known
  misses, is `analysis/geometry/finding_blocks.py`; no model and no text search is involved.
- **Absent is not empty.** `status: "not_produced"` (and no items) when the run has no text-layer geometry or the version no portal
  geometry; with `produced`, a finding whose evidence no block holds has an empty `portal_block_ids`. `unlinked_pages` are the
  pages of the portal geometry on which no link can be derived (the portal's raster does not describe the PDF page: a
  `geometry_mismatch`, or an aspect or rotation the text layer's page does not share): a block on such a page is unknown, never
  «no findings». An unknown run is `404`.
- **Not changed.** `Finding`, `Evidence`, `PortalBlock` and `listRunFindings` are as they were; the link is a separate read so that a
  link that cannot be derived never takes the findings list down with it.

The API then had 274 paths, 302 operations and 729 schemas (the new schemas were `FindingBlockLink` and `RunFindingBlockLinks`);
migration head `0058`. The domain catalogs were at candidate revision 58.

## Contract `1.40.0` (`UI-PARITY-AUDIT-STATE`, historical)

Slice for register rows `UI-A-47` (the original's «идёт аудит» strip on a document), `UI-A-65` / `UI-B-45` (the estimated finish
on the run page) and `UI-B-07` (the percent beside a proposal's saving). **No operation, no error code, no migration** (head
stays `0058`). One new schema, `DocumentActiveRun`; three optional properties, each absent when it has nothing to say.

- **A document names the run in flight.** `DocumentAudit.active_run` (`listDocuments` only, read in the same statement as the
  audit, one statement for the page) is `{run_id, state}` of the version's latest run of the standard analysis in state
  `queued`, `running` or `validating`, ordered by `(created_at, run_id)` as the result run is; absent when none is. It is a fact
  beside the four words and changes none of them: a document whose first run is in flight is still `not_run`, and a `checked` one
  with a re-run in flight is still `checked`; the counters (`DocumentAuditCounts`, the dashboard) do not read it. A `created`
  run is not active (not yet admitted); a run of an AR v3 group never is, as it is never a result (`AR-V3-OPT-IN`, `Q3`). **No
  progress figure** («пакет n/m»): the run status reports stages and the server holds no plan of packages to count against
  (`D-345`); the card says «идёт аудит» with the state and links to the run page, where the stages are.
- **The run page has the estimate the queue has.** `RunStatus.estimated_finish_at` is the value of
  `ExecutionQueueItem.estimated_finish_at` (`R-151u`) for the run's job, from **one function**
  (`execution.eta.job_estimated_finish`, which the queue item calls too): the job's first attempt plus the median duration of at
  least three similar recent completed runs. Present only while the run's job is leased or running and has started; absent for a
  queued, waiting or finished run and without enough history; never invented. It can already lie in the past for a run that is
  taking longer than the usual one; the screen says what the time is and not that it will be met.
- **A proposal's percent.** `OptimisationProposal.saving_percent` is how much cheaper the proposed unit price is than the
  current one, in percent of the current unit price: `(current - proposed) / current * 100`, exact rational arithmetic, rounded
  half up to two decimals and written without a trailing zero (`25`, `33.33`; pattern `^(0|100|(0|[1-9][0-9]?)\.[0-9]?[1-9]|[1-9][0-9]?)$`).
  It is the share the `saving` is of the cost at the current price, with the quantity cancelled, so it is present where `saving` is
  `null` for want of a numeric quantity; absent only when the current unit price is zero. The one figure of a proposal that is
  rounded; never computed by a client. The proposals' CSV and workbook and `AcceptedOptimisationProposal` do not carry it (`D-346`).
- **Not changed.** The four audit states, `ExecutionQueueItem`, the counters, every operation's request.

The API then had 273 paths, 301 operations and 727 schemas (the new schema was `DocumentActiveRun`); migration head `0058`. The
domain catalogs were at candidate revision 57.

## Contract `1.39.0` (`UI-PARITY-FINDING-ORIGIN`, historical)

Slice for register row `UI-A-73` (the original's «↩ Перенесено из V1» on a finding whose verdict an expert carried over from an
earlier version) and `D-335`, migration `0058_finding_decision_origin`. **No operation, no error code.** One new schema,
`DecisionCarriedFrom`.

- **A carried finding decision names its source.** `carryOverDecision` (`W59-DECISION-CARRYOVER-01`) already appended the
  confirming expert's verdict to the target finding as an ordinary event, and kept where it came from only in the event's
  rendered `comment`. The new nullable `expert_decision_event.carried_from_decision_id` (migration `0058`: foreign key to the
  table itself, `dec_` shape, not its own source, only an `accept` or a `reject`, a partial index) is written by the same
  statement as the event. `DecisionCarriedFrom` (`decision_id`, `finding_uid`, `version_uid`, `version_ordinal`) is that link as
  the wire shows it: the source decision, its finding and version, and the version's display order («V2», never an identity).
- **The decision history and the journal.** `DecisionEvent.carried_from` (`listDecisionHistory`, `appendDecision`) and
  `DecisionRecord.carried_from` (`listDecisions`, and the finding half of `listKnowledgeBaseEntries`) are **optional**: absent
  for an event an expert made directly, and for every event written before the migration. They are not required-nullable like
  `ProposalDecision.carried_from`, because the finding ledger's shapes predate the field, `appendDecision` answers a direct event
  by construction, and the ledger's attributes (`severity`, `section`, `decided_severity`) are omitted when empty.
- **The origin of a finding's current verdict.** `Finding.current_verdict_carried_from` and
  `FindingDetail.current_verdict_carried_from` (`listRunFindings`, `getFinding`) carry the same object for the decision that
  carries `current_verdict` -- the latest verdict-bearing event, as the projection reads it: a comment appended after a carried
  acceptance leaves it standing, an expert's own verdict after it replaces it, and a withdrawal leaves none. Optional, absent
  unless carried. A small object and not a bare ordinal, so the same shape names the source on all four reads and a screen that
  wants the source finding does not read the whole history.
- **`D-335` (part).** `AcceptedOptimisationProposal.carried_from` (required, nullable `ProposalDecisionCarriedFrom`, as on
  `ProposalDecision`) lets «Принято» show the mark of an acceptance carried over from an earlier version's pass. The proposals'
  CSV and workbook, the proposal-decision journal (`ProposalDecisionRecord`) and the knowledge base's «Предложения» still show
  a carried decision as an ordinary one (`D-335`, narrowed).
- **Not changed.** An event carried before `0058` has the comment and no link (the ledger is append-only); it reads as made
  directly (`D-342`). The downgrade of `0058` refuses while a carried event exists.

The API now has 273 paths, 301 operations and 726 schemas (the new schema is `DecisionCarriedFrom`); migration head `0058`. The
domain catalogs are at candidate revision 56.

## Contract `1.38.0` (`AR-V3-OPT-IN`, historical)

AR v3 as an **opt-in mode** (`docs/program/AR-V3-OPT-IN-01.md`; owner words of 2026-11-07: «реализуй как переключаемую
функцию -- по умолчанию используется импортированный вариант»). **No operation, no schema, no error code, no migration.**

- **The allowance.** `ArV3BetaPackStatus.start_allowed` (optional; present exactly when `state` is `installed`) says whether
  the deployment allows a start of an AR v3 group now (`AR_V3_BETA_START_ALLOWED`, read by the `api` service, off unless `1`,
  anything but absent, blank, `0` or `1` refuses the process start). The pack is the capability to execute, read and review;
  this is the separate permission to start. While a pack is installed and it is false, `startArV3BetaGroup` and
  `estimateArV3GroupCost` answer `409 conflict` with `conflict_reason` `ar_v3_start_not_enabled` and write nothing; a repeat of
  an accepted key still replays its group; runs already accepted finish. With no pack the answers are what they were.
- **Which analysis produced a run.** `RunStatus.analysis_kind` (`standard` | `ar_v3_beta`) is derived from the pinned profile
  and bundle pair and sent on every run; `ar_v3_group_id` and `ar_v3_scope_id` name the group and scope of a member only. Each
  member records the account that started it (`started_by_user_uid`, `R-151v`).
- **The result of a version** is its newest published or partial run **of the standard analysis**: the audit state of a document
  and every counter read off it, the schedule's facts, the default run of a comparison and the text the optimisation reads. A
  published v3 member never displaces it (`Q3`).
- **Refusals.** `reauditRun` (and `estimateRunCost` with `reaudit_of_run_id`) of a member of an AR v3 group is `409 conflict`
  with `conflict_reason` `ar_v3_member_not_repeatable`, before the key is claimed (`Q4`); a v3 run named as `source_run_id` or
  `target_run_id` of a comparison is the refusal `analysis_not_comparable` (new reason of `ComparisonRefusal`, with its side;
  `Q5`), checked after `run_not_of_version` and before `run_not_published`.

The API keeps 273 paths, 301 operations and 725 schemas; migration head `0057`. The domain catalogs are at candidate
revision 55.

## Contract `1.37.0` (`UI-PARITY-OPT-CARRYOVER`, historical)

Slice for register row `UI-B-14` (carry the decisions of an earlier version's optimisation pass over to a later one, the
original's «↩ Перенесено из V2»), migration `0057_decision_carryover`, and two corrections:

- **«Перенести решения из V#»** (`UI-B-14`). `carryOverProposalDecisions`
  (`POST /optimisation-passes/{optimisation_pass_id}/decision-carryovers`, body `source_optimisation_pass_id`, `expert`,
  keyed) carries the decisions in force of the source pass into the pass of the path. The source must be a pass of the same
  document set started over an earlier version; otherwise `409 conflict` with `conflict_reason` `carryover_source_unknown`,
  `carryover_source_is_target`, `carryover_source_other_document` or `carryover_source_not_earlier`, and nothing is written.
  A source decision (`accept`, `reject` or `revise`; a proposal nobody decided, or whose decision was withdrawn, carries
  nothing) is matched to a proposal of the target pass by **content only** -- the type, the specification row's text, the
  unit and the currency, the matched and the proposed position by code, mark, name and supplier, and both exact unit prices;
  never a display number, a name alone, a place in the drawing, a price-list identity or the quantity -- and only when
  exactly one proposal of each pass has that content and the target proposal has no event at all (a decision or a
  withdrawal there is an expert's act and stands). Each match is appended as an ordinary decision event of the target
  proposal: the source's verdict and comment, authored by the caller, with `carried_from` naming the source; a later decision
  on the proposal supersedes it like any other. The answer (`ProposalDecisionCarryoverReport`) counts every decision in force
  of the source (`source_decided`) in exactly one of `carried`, `target_decided`, `ambiguous` (more than one proposal of
  either pass has that content) and `unmatched`, and names the source version's display ordinal. An exact repeat of the key
  answers the stored report and appends nothing; the key for another source or caller is `409 idempotency_key_reuse`; a new
  key repeats the matching and carries nothing more once the targets are decided. The migration adds the nullable
  `optimisation_proposal_decision.carried_from_decision_id` (foreign key to the table itself, the `opd_` shape, not its own
  source, never a `revoke`) and a partial index; its downgrade refuses while a carried decision exists.
- **`ProposalDecision.carried_from`** is a required, nullable `ProposalDecisionCarriedFrom` (`proposal_decision_id`,
  `optimisation_pass_id`, `version_uid`, `version_ordinal`): `null` for a decision made directly and for every decision
  recorded before the migration. It is on every `ProposalDecision` (`decideOptimisationProposal`, `listProposalDecisions`
  and the `current_decision` of each proposal).
- **`OptimisationPass.version_ordinal`** is the required display order of the version the pass was started over («V2»), so a
  screen can name an earlier version's pass; it is never an identity.
- **The tabs of «Оптимизация разделов»** need no new field: `SectionSpecification.row_count` (every row in scope, apart from
  the text search) and `AcceptedOptimisationProposalPage.total` are the server's figures for «Форма 7 · N» and «Принято N»,
  and the screen never counts rows.
- **`AnalysisProfileStatus`** (`D-223`): the description now says what `R-146ag` and `A-7` say -- `reviewed` is a package whose
  open questions a lane answered in writing, with no human review -- and no longer that an expert reviewed it or that the
  original-source АР profile is `draft` until expert review (АР has no profile status at all: its row carries `profile: null`).

The API now has 273 paths, 301 operations and 725 schemas (the three new schemas are `CarryOverProposalDecisionsRequest`,
`ProposalDecisionCarriedFrom` and `ProposalDecisionCarryoverReport`); migration head `0057`. The domain catalogs are at
candidate revision 54. No error code is added.

## Contract `1.36.0` (`UI-PARITY-ADMIN-C2`, historical)

Slice for register rows `UI-A-92`, `UI-A-93` and `UI-A-94` (the administrator's side of the original's «Пользователи»)
and the «Диспетчер» counts, **no migration** (head stays `0056`): the access journal already is the append-only
`audit_event` table, written in the transaction of the change it describes (`PROD-06`, ADR-0023 section 4), so this slice
reads it and adds one event type.

- **«Последний вход»** (`UI-A-92`). `Account` gains the required, nullable `last_sign_in_at`: the instant of the
  account's latest `access.sign_in_succeeded` event, `null` when none is recorded (it never signed in, or signed in before
  the journal began). It is on every `Account` answer (`listUsers`, `getUser`, `getMe` and the account writes). It is read
  from the journal for the accounts an answer names, in one statement for the page; the seam's own per-request standing
  read does not touch the journal.
- **«Завершить сеансы»** (`UI-A-93`). `endUserSessions` (`POST /users/{user_uid}/sessions/end`, `admin`, keyed) raises the
  account's credential epoch, the mechanism archive, reset and a role change already use, so every credential the account
  holds is refused from its next request (`401 authentication_required`) and it signs in again; the password, the roles and
  the sign-in brake are untouched. It answers the `Account`. Not oneself (`403 permission_denied`: an administrator ends
  their own sessions by changing their password); an archived or missing account is `404 not_found`. The key is claimed in
  the transaction of the raise: an exact repeat answers the account unchanged and ends nothing more, the key under another
  account or administrator is `409 idempotency_key_reuse`. A new event type, `access.sessions_ended`, is journalled in
  that transaction (the seventh; the command type `end_user_sessions` is an account-side receipt the purge keeps).
- **«Журнал входов»** (`UI-A-94`). `listAuthEvents` (`GET /auth-events`, `admin`, cursor) is the access journal, newest
  first. Each row is an `AuthEvent`: its identity (`evt_`), `event_type` (`AuthEventType`: `sign_in_succeeded`,
  `sign_in_blocked`, `password_changed`, `password_reset`, `role_granted`, `role_revoked`, `sessions_ended`), `occurred_at`,
  the account it is about (`subject_user_uid` and `subject_label`, the label it has now, `null` once the account has been
  deleted), the administrator who acted (`actor_user_uid`, `actor_label`; `null` for a sign-in, a refusal and a grant by the
  host command), `source` (`api` or `host_cli`), and the three facts a type may carry (`role`, `failures`,
  `default_credential`; `null` otherwise). The order is `(occurred_at, sequence)` and the cursor is the last event's own
  identity; the sequence is never sent. **What the journal holds is what its writer allows**: identities, a role, a source
  word, one boolean and one count -- never a password, a token, an address or a login as typed. **A refused sign-in is
  journalled as `sign_in_blocked`, once per account per cooling-off period (ADR-0023 section 4); a refusal that starts none
  and an attempt on an unknown login are not journalled** (an unknown login has no identity to name, and a row per guess
  would let a guesser grow the table). **Sign-out is not journalled**: the web tier closes its own session and the API is
  not told; an event for it needs an operation of its own.
- **«Диспетчер»: the numbers of the state chips.** `AssignmentPage` gains the required `total` (the assignments the caller
  may read under every filter of the request, the status included) and `overview` (`AssignmentStatusCount`: every one of
  the five statuses with its count, in the order of `AssignmentStatus`, `0` for a status none is in) over the scope
  filters only (`project_uid`, `mine` and what the caller may read), not the `status` filter, the way the execution queue's
  `overview` counts its states: each count is what choosing that status would list. The numbers are the server's, never a
  count of the page held.

The API now has 272 paths, 300 operations and 722 schemas (the four new schemas are `AssignmentStatusCount`, `AuthEvent`,
`AuthEventPage` and `AuthEventType`); migration head `0056`. The domain catalogs are at candidate revision 53. No error
code is added.

## Contract `1.35.0` (`UI-PARITY-OPT-DECISIONS`, historical)

Slice for register rows `UI-B-12`, `UI-B-27` and `UI-B-15` (the optimisation decisions of the original that ours lacked),
migration `0056_optimisation_decisions`:

- **«Снять решение»** (`UI-B-12`). `ProposalVerdict` gains `revoke`: `decideOptimisationProposal` accepts it as a fourth
  verdict. A withdrawal is one more appended event on the append-only decision history, never an update or a deletion, and
  it takes the proposal back to `pending`: `OptimisationProposal.current_verdict` and the pass's `decision_counts` count a
  proposal whose latest event is a `revoke` as `pending`, and `current_decision` still names that latest event, so a screen can
  say who withdrew the decision and when. `listProposalDecisions`, `listProposalDecisionJournal` and `listKnowledgeBaseEntries`
  show the `revoke` event as it was recorded. A `revoke` over a proposal with no decision in force (none yet, or the latest
  event is already a `revoke`) is `409 conflict` with `conflict_reason` `no_decision_to_revoke`; the comment of a `revoke` is
  optional. The operation stays keyed and `expert`-only. Migration `0056` widens `ck_optimisation_proposal_decision_verdict`;
  its downgrade refuses while any `revoke` event exists.
- **«Принято»** (`UI-B-27`). `listAcceptedOptimisationProposals` (`GET /optimisation-proposals/accepted`, a product read,
  optional `project_uid` and `section_code` filters, cursor and `total`) lists the proposals whose decision in force is an
  acceptance, across every pass, newest acceptance first. Each row is an `AcceptedOptimisationProposal`: its proposal and
  pass identities, where it belongs (project, document set, version and the version's section), the row's place and text,
  both position names, the proposed vendor, the exact prices and the saving (`null`, never `0`, when the quantity is not a
  number), and the acceptance (decision id, comment, author, time). Neither filter is a parent: a project or a section with no
  acceptance is an empty page. A rejection, a revision request, a withdrawal or no decision is not listed.

- **«Загрузить решения»** (`UI-B-15`). `exportOptimisationProposalsXlsx` (`GET /optimisation-passes/{optimisation_pass_id}/export.xlsx`,
  any one role) is the pass's proposals as a workbook with one sheet, «Предложения»: the first column, «ID предложения», is
  the proposal's own identity, then the specification row, both positions, the exact prices and the saving (empty, never `0`,
  when absent), and the two columns an expert edits, «Решение эксперта» (`не решено`, `принято`, `отклонено`, `на доработку`)
  and «Комментарий», filled with the decision in force. `importOptimisationProposalDecisions`
  (`POST /optimisation-passes/{optimisation_pass_id}/decision-imports`, multipart `file`, at most 10 MiB, keyed, `expert`)
  reads it back by proposal identity, never by «№», and only into proposals of that pass: a row that differs from the decision
  in force appends one ordinary event authored by the caller (`accept`, `reject`, `revise` with its comment, or `revoke` for
  «не решено» over a decision in force); a blank decision cell keeps the decision in force; the report
  (`ProposalDecisionImportReport`) names every row that carries an ID or a decision as `recorded`, `unchanged` or `refused`
  with one of six reasons. A workbook without the «Предложения» sheet and its three columns is `422 validation_failed`
  (`field: file`, `constraint: not_our_export`; also `unreadable`, `too_large`, `too_many_rows`). An exact repeat of the key
  answers the stored report; another file under it is `409 idempotency_key_reuse`.

The API now has 270 paths, 298 operations and 718 schemas (the six new schemas are `AcceptedOptimisationProposal`,
`AcceptedOptimisationProposalPage`, `ImportProposalDecisionsRequest`, `ProposalDecisionImportRefusal`,
`ProposalDecisionImportReport` and `ProposalDecisionImportRow`); migration head `0056`. The domain catalogs are at candidate
revision 52.

## Contract `1.34.0` (`UI-PARITY-DOC-AUDIT`, historical)

Slice for register rows `UI-A-46`, `UI-A-49` and `UI-A-38`: each document's audit state on `listDocuments`, so a section
orders its documents as the original does and filters «не запускались». No new operation, no migration, no error code.

- `DocumentVersion.audit` (new optional `DocumentAudit`: `state` `not_run`, `clean`, `awaiting_decision` or `checked`;
  `partial`; `result_run_id`, absent exactly when the state is `not_run`; `finding_count`; `undecided_finding_count`) is
  the audit of the version the item shows, by the rules of the counters of `DocumentAuditCounts` (`R-150n`…`R-150u`).
  It is on the items of `listDocuments` only, read for the page in one statement and never one request per document;
  every other answer carrying a `DocumentVersion` omits it.
- `listDocuments` gains the optional `audit_state` filter (the four states; every document when absent) and the `order`
  parameter (`published`, the default and the order the operation always had, newest first; or `audit`). Both are applied
  by the server to the whole listing before it is paged, so the cursor, the end of the listing and the number of
  documents a screen counts by following the cursors are those of the narrowed, ordered listing.
- **Ordering is decided by the server, not by each page.** `order=audit` is the original's `projectOrderRank`: documents
  the expert has checked (`checked`) first, then documents processed and not yet decided on (`clean`,
  `awaiting_decision`), then documents never audited (`not_run`); within each group by `display_title` in natural Russian
  order (runs of digits compare as numbers, case and the marks on a letter such as «ё» are ignored), and by `version_uid`
  among equal names. A client that sorted a page would order a section differently on each page; the cursor is built on
  the identity and resumes after its row in the ordered listing; because the order follows the audit state at the time of each
  request, a document that changes state between two pages can appear on both or on neither, and a screen that needs the whole
  listing reads it again from the first page.

The API then had 267 paths, 295 operations and 712 schemas (the one new schema is `DocumentAudit`); migration head `0055`.
The domain catalogs were at candidate revision 51.

## Contract `1.33.0` (`HOTFIX-RUN-PARTIAL-1106`, historical)

Removed the application character ceiling on runner answer text. Request/response fields,
paths and operations were unchanged. Analysis and event families share the seal.

## Contract `1.32.0` (`UI-PARITY-KB-ALL`, historical)

Slice for ruling `R-151h` and debt `D-317`: the knowledge base's «Все». `listKnowledgeBaseEntries` (`GET /knowledge-base/entries`,
a product read, optional `project_uid` filter, cursor and `total`) lists the decisions on findings and on optimisation
proposals as one journal, newest first. Each row is a `KnowledgeBaseEntry`: its `kind` (`finding` or `proposal`), its
`occurred_at`, and exactly the record its kind names (`DecisionRecord` or `ProposalDecisionRecord`), so each keeps its own
identity; the order and the cursor are the record's time, the kind and that record's id. `listDecisions` and
`listProposalDecisionJournal` stay the «Замечания» and «Предложения» halves. No migration, no error code.
The API then had 267 paths, 295 operations and 711 schemas; migration head `0055`. The domain catalogs were at candidate revision 50.

## Contract `1.31.0` (`UI-PARITY-P0P`, historical)

«График работ» (rulings `R-151x`, `R-152a`…`R-152h`), tag `schedule`, migration `0055_work_schedule`:

- `getWorkSchedule` (`GET /work-schedule?month=YYYY-MM`, `admin` or `expert`): the month's days (Saturday and Sunday off
  unless an administrator decided otherwise) and, per active expert, the plan (`plan_is_default` when the stored default
  applies), the documents that became «Проверено экспертом» in the month credited to the author of their last verdict, and
  the absent days. An expert reads their own row.
- `getWorkScheduleReserve` (`GET /work-schedule/reserve?start=&days=28`, `admin` or `expert`): «Календарь запаса», each
  expert's open assignments of «Диспетчер» with their planned date, or none for «без даты». No daily limit.
- `setWorkScheduleSettings`, `setWorkSchedulePlans`, `setWorkCalendarDays`, `setEngineerAbsences` (`PUT`, keyed, `admin`):
  the default plan (initially 20) and the time zone, each engineer's monthly plan, days off and working days, absences.
- `scheduleAssignments` (`POST /work-schedule/reserve/moves`, keyed, `admin`): moves open assignments to a day and, with
  `assignee_user_uid`, to another expert (a reassignment). Every move is an event with its author.

Sixteen schemas (`WorkSchedule*`, `WorkCalendarDayChange`, `EngineerAbsenceChange`, `AssignmentMove` and four requests).
No error code: a bad zone is `validation_failed` with `constraint: unknown_zone`, a plan for a non-expert
`constraint: active_expert`.
The API then had 266 paths, 294 operations and 709 schemas; migration head `0055`. The domain catalogs were at candidate revision 49.

## Contract `1.30.0` (`UI-PARITY-P0O`, historical)

`listVersionSheetLabels` (`GET /versions/{version_uid}/sheet-labels`, any one role): the version's pages with the drawing
sheet their portal blocks name and their block count, as the original's «Лист» beside a finding's page. Read from the
portal geometry `listVersionPortalBlocks` reads; a page whose blocks name different sheets has no label, a page without a
block is not listed, and a version without geometry answers `not_produced`. Schemas `VersionSheetLabel`,
`VersionSheetLabelList`. No migration, no error code.
The API then had 259 paths, 287 operations and 693 schemas; migration head `0054`. The domain catalogs were at candidate revision 48.

## Contract `1.29.0` (`UI-PARITY-P0N`, historical)

`getProject` (`GET /projects/{project_uid}`, any role that may list projects): one project exactly as `listProjects` lists
it, so a screen that names its project (the project page's title, the «Где вы находитесь» strip) need not find it on a page
of the listing. An unknown project is `404`. No schema, no migration, no error code.
The API then had 258 paths, 286 operations and 691 schemas; migration head `0054`. The domain catalogs were at candidate revision 47.

## Contract `1.28.0` (`UI-PARITY-P0M`, historical)

The rest of `UI-PARITY-01`'s queue group A, as the original's queue line «N / M», «N ✓ M ✗» and its numbered items:
`ExecutionQueuePage` gains `overview`, every job state with its count over the period filter (not the state filter), and
`ExecutionQueueItem` gains `queue_position` (a queued job's place among every queued job in the dispatcher's order --
priority, then the oldest first; the order, not a forecast) and `attempt_count`. One schema, `ExecutionQueueStateCount`.
No operation, no migration, no error code.
The API then had 257 paths, 285 operations and 691 schemas; migration head `0054`. The domain catalogs were at candidate revision 46.

## Contract `1.27.0` (`UI-PARITY-P0L`, historical)

Slice for ruling `R-151d`: decisions edited in our own Excel export are loaded back. `exportRunXlsx`'s «Замечания» sheet
gains a last column, «ID замечания», holding the finding's `finding_uid` (empty on a «также найдено» row).
`importRunDecisions` (`POST /runs/{run_id}/decision-imports`, multipart `file`, keyed, `expert`) reads only that sheet of
our workbook (`422 validation_failed`, `field: file`, `constraint: not_our_export | unreadable | too_large |
too_many_rows`, refuses a foreign file whole) and matches rows by `finding_uid`, never by «№». A changed «Решение
эксперта» appends `accept` or `reject` with the row's comment, a changed «Комментарий» alone a `comment` event, both
authored by the caller; nothing is revoked and the severity columns are not read. `DecisionImportReport` lists every row
naming an ID or a decision as `recorded`, `unchanged` or `refused` with a `DecisionImportRefusal` reason. No migration,
no error code.
The API then had 257 paths, 285 operations and 690 schemas; migration head `0054`. The domain catalogs were at candidate revision 45.

## Contract `1.26.0` (`UI-PARITY-P0K`, historical)

Additive slice for ruling `R-151u`: `ExecutionQueueItem` gains the optional `estimated_finish_at` of a running job -- its
first attempt's start plus the median duration of at least three recent completed runs of the same analysis profile and
a page count within a quarter of its own (`execution/eta.py`); absent without enough history, never invented. No
operation, no schema, no migration, no error code.
The API then had 256 paths, 284 operations and 685 schemas; migration head `0054`. The domain catalogs were at candidate revision 44.

## Contract `1.25.0` (`UI-PARITY-P0J`, historical)

Slice for ruling `R-151h`: the knowledge base's «Предложения» half. `listProposalDecisionJournal` (`GET /proposal-decisions`,
a product read, optional `project_uid` filter, cursor and `total`) lists every expert decision on an optimisation proposal,
newest first, as `ProposalDecisionRecord` (verdict, comment, actor label, project, document, version, section, the
specification row and the proposed vendor). `listDecisions` stays the «Замечания» half; the screen switches between them
with «Тип». No migration, no error code.
The API then had 256 paths, 284 operations and 685 schemas; migration head `0054`. The domain catalogs were at candidate revision 43.

## Contract `1.24.0` (`UI-PARITY-P0I`, historical)

Slice for ruling `R-151g`: the designer's execution status of an accepted finding, our own instead of the original's
SU-10 registry labels. `setFindingExecutionStatus` (`PUT /findings/{finding_uid}/execution-status`, keyed, `expert` only,
body `SetFindingExecutionStatusRequest {status}` with `FindingExecutionStatus` `taken_into_account` | `amended` | `declined` |
`agreed` or `null` to clear) answers `FindingExecutionState`; setting it on a finding not accepted is `422`
(`finding_not_accepted`). `Finding` and `FindingDetail` gain the optional `execution_status` and `execution_status_at`. It is
not an expert decision. Migration `0054_finding_execution_status`. No error code.
The API then had 255 paths, 283 operations and 683 schemas; migration head `0054`. The domain catalogs were at candidate revision 42.

## Contract `1.23.0` (`UI-PARITY-P0H`, historical)

Slice for ruling `R-151e`: free tags on a document, and a filter by tag (the original's folders are not built: no order,
no drag, no group entity). `setDocumentTags` (`PUT /projects/{project_uid}/documents/{document_uid}/tags`, keyed, body
`SetDocumentTagsRequest {tags}`, at most ten tags of 1 to 40 characters) replaces the set; `listDocumentTags`
(`GET /projects/{project_uid}/document-tags`, `DocumentTagList` of `DocumentTagCount {tag, document_count}`) is the project's
catalogue without archived documents; `listDocuments` takes the optional `tag` filter (case-insensitive) and `DocumentVersion`
gains the optional `tags`. Migration `0053_document_tags` adds `document_tag`. No error code.
The API then had 254 paths, 282 operations and 680 schemas; migration head `0053`. The domain catalogs were at candidate revision 41.

## Contract `1.22.0` (`UI-PARITY-P0G`, historical)

Slice for ruling `R-151a`: a document is archived or renamed, never deleted. Two keyed operations, `setDocumentArchived`
(`PUT /projects/{project_uid}/documents/{document_uid}/archive`, body `SetDocumentArchivedRequest {archived}`) and
`renameDocument` (`PUT /projects/{project_uid}/documents/{document_uid}/title`, body `RenameDocumentRequest
{display_title}`), each answering the document's current `DocumentVersion`. `listDocuments` leaves an archived document out
unless `include_archived` is asked, and `DocumentVersion` gains the optional `archived_at`. Every change appends
`document.archived`, `document.restored` or `document.renamed` to the audit trail. `expert` and `admin`; `viewer` refused.
Migration `0052_document_archive` adds `document.archived_at` and `archived_by_user_uid` (a RESTRICT reference). No error code.
The API then had 252 paths, 280 operations and 677 schemas; migration head `0052`. The domain catalogs were at candidate revision 40.

## Contract `1.21.0` (`UI-PARITY-P0F`, historical)

Additive slice for ruling `R-151v`: who started a run. `RunStatus` gains the optional `started_by_user_uid` and
`started_by_label`, `ExecutionQueueItem` the optional `started_by_label` (the account's display label). Both are absent
for a run created before migration `0051_run_started_by`, which adds `audit_run.started_by_user_uid` (a frozen RESTRICT
reference to `app_user`; an account that started a run is archived, never purged). No operation, no error code.
The API then had 250 paths, 278 operations and 675 schemas; migration head `0051`. The domain catalogs were at candidate revision 39.

## Contract `1.20.0` (`UI-PARITY-P0E`, historical)

Additive read slice for the UI parity programme (rulings `R-151f`, `R-151l`). One optional query parameter and one operation;
no migration, no new schema, no new error code.
`listDocuments` takes the optional `section_code` (a `ProjectSection`): only the documents whose current version is confirmed for
that section (its `classification.section_code`); a document whose current version is unclassified never matches. The order is
the unfiltered order with rows removed, and a cursor resumes after its row in the filtered listing.
`getExecutionDispatch` (`GET /execution/dispatch`) returns the `ExecutionDispatchStatus` `setExecutionPaused` writes, so the top
strip can show the pause state without reading the queue; readable by `expert` and `admin`, refused to `viewer` (`R-150w`).
The API then had 250 paths, 278 operations and 675 schemas; migration head `0050`. The domain catalogs were at candidate revision 38.

## Contract `1.19.0` (`UI-PARITY-P0B`, historical)

Additive read slice that gives a document an audit state and its counters (the counters the project selector and the section panel of the
UI parity programme wait for; rulings `R-150n` ... `R-150u`, dictionary `docs/program/UI-PARITY-METRICS.md`). Response fields and one new
schema only; no migration, no new operation, no new error code.
A new schema `DocumentAuditCounts` has `document_count`, `not_run`, `clean`, `awaiting_decision`, `checked`, `partial` and
`no_expert_decision`. `Project` gains the optional `audit_counts` (present on a `listProjects` item, absent from `createProject`, the
reason `document_count` is optional). `SectionDocumentCount` gains the required `audit_counts` and `finding_count` (the published
findings of the result runs of the section's documents); `DashboardSummary` gains the required `awaiting_decision_findings` (findings
whose current verdict is `pending` or `needs_manual_review` in the result runs of current versions; it follows the optional
`project_uid`). `VerdictCount` and `findings_by_verdict` are now described as counting every finding of every run, «за всё время».
A document counts by its current version only; its result run is the latest run in state `published` or `partial` ordered by
`(created_at, run_id)`; a failed, cancelled or still running run is not a result. A document is `not_run`, `clean` (a result with no
finding), `awaiting_decision` or `checked`, and `partial` flags a partial result. `no_expert_decision` is `not_run +
awaiting_decision`.
The API then had 250 paths, 277 operations and 675 schemas; migration head `0050`. The domain catalogs were at candidate revision 37.

## Contract `1.18.0` (`UI-PARITY-QUEUE-A`, historical)

Additive read slice that makes the execution queue readable (items A1 and A2 of the queue group of the UI parity programme).
Optional query parameters and response fields only; no migration, no new operation, no new error code.
`ExecutionQueueItem` gains `project_uid`, `project_name`, `document_uid`, `document_name`, `version_uid` and `version_ordinal`
(required: every job executes exactly one audit run, and a run belongs to one version of one document of one project by
not-null foreign keys; the two names and the ordinal are joined at read time and stored nowhere; the version has no label other
than its display number) and the optional `started_at` (the creation of the job's first attempt), `finished_at` (the job's
terminal time), `error_code` (the run's `terminal_reason`) and `interrupted_reason` (the run's own). A property a job does
not have is omitted, never sent as `null`; `binding_state` and `wait_reason` are omitted for an ordinary job as well (they
were sent as `null` until now). `listExecutionQueue` takes the optional `state` (one of the eight job states) and the optional
period `created_from` (included) / `created_to` (not included) over `created_at`, both RFC 3339 instants with an offset. The
queue's order is unchanged. A cursor belongs to the filters it was issued under: one presented with other filters is
`422 validation_failed` with `constraint: scope`, the refusal the comparison stage listings already give. The overview
(`getExecutionOverview`), an estimate of the end and the attempts of a job are not in this slice.
The API then still had 250 paths, 277 operations and 674 schemas; migration head `0049`. The domain catalogs were at
candidate revision 36.

## Contract `1.17.0` (`UI-PARITY-P0A`, historical)

Additive read slice for "the project chosen in the header" on the dashboard and the knowledge base. Optional query
parameters and response fields only; no migration, no new operation, no new error code.
`getDashboardSummary` takes an optional `project_uid`: with it every one of the four panels (`documents_by_project`,
`findings_by_verdict`, `run_activity` with its `spend`, `section_breakdown`) is restricted to that project by exactly the
definitions it has without it, and no counter is redefined. A `project_uid` naming no project is `404 not_found`, a malformed
one `422 validation_failed`; both responses are declared on the operation from this version. `listDecisions` takes an
optional `project_uid` as well, filtering to decisions on findings of that project (a filter and not a parent: a project
nothing was decided in, or one that does not exist, is an empty page). `DecisionRecord` gains `document_uid`, `version_uid`,
`project_name` and `document_name` (the two names are joined at read time and stored nowhere) and the optional `section`,
the expert-confirmed section of the finding's version (absent while the version is unclassified); `DecisionRecordPage`
gains `total`, the number of entries matching the filters on every page of the listing. A record's type (finding or
proposal) is deliberately not added.
The API then still had 250 paths, 277 operations and 674 schemas; migration head `0048`. The domain catalogs were at
candidate revision 35.

## Contract `1.16.0` (`EXEC2-SEAL-2`, historical)

Additive stage-2 and stage-3 surface of executor groups, routing rules, the routing mode and dispatch-time binding
(ADR-0026 decisions 10 to 17, rulings `R-149a`…`R-149f`). Operations: `listExecutorGroups`, `createExecutorGroup`,
`getExecutorGroup`, `reviseExecutorGroup`, `archiveExecutorGroup`, `getExecutorGroupCapacity`, `listExecutorRoutingRules`,
`setExecutorRoutingRule`, `previewExecutorRouting` and `setExecutorRoutingMode` (all administrator). `startRun` and
`estimateRunCost` take an optional `executor_group_id`, exclusive with `executor_connection_id` and `preset_id`.
`RunCostEstimate` and `ComparisonAiRoute` carry the planned group, rule revision and model; `ComparisonAiRoute.connection_id`
and `revision_id` become optional, since a group's connection is chosen at dispatch. `RunStatus` and `ComparisonAiJob` carry
`binding_state` (`frozen_at_start`, `pending`, `bound`), `planned`, `binding`, `wait_reason` and `waiting_since`; the queue
items carry `binding_state` and `wait_reason`. `RunQueueReason` gains `needs_reconsent`; the persisted `wait_reason` uses the
same words. `issueExecutorEnrollment` names the `public_origin` dependency.
The API then had 250 paths, 277 operations and 674 schemas; migration head `0048`. No error code is added: refusals are
typed details of existing codes (`contracts/domain/v1/error-codes.json` notes). The domain identifiers gain
`executor_group_id` (`exg`), `executor_group_revision_id` (`exgr`), `executor_routing_rule_revision_id` (`exrr`) and
`executor_routing_mode_event_id` (`exrm`), and the state machines gain `binding_state`. Migration
`0047_executor_groups_rules` creates the group, rule and routing-mode tables and `0048_dispatch_time_binding` the binding
columns and the write-once exception of the frozen-column guards. The operations are sealed here and implemented by the
stage-2 and stage-3 lanes; none behaves until its lane lands, the routing mode stays `legacy` and every existing row stays
`frozen_at_start`.

## Contract `1.15.0` (`EXEC2-SEAL-1`, historical)

Additive stage-1 surface of executor capacity and the universal agent (ADR-0026 decisions 1 to 9, rulings
`R-149a`…`R-149f`): `max_active_runs` in the revision settings; `occupancy` and `integration_authorisation` on
`ExecutorConnection`; `enrollments` on `ExecutorConnectionDetail`; `queue_reason` on `RunStatus`; the optional `runner_instance_id` of `claimExecutorTask`; the
health fields of `RunnerTokenMetadata`; and the operations `issueExecutorEnrollment`, `redeemExecutorEnrollment`,
`reportRunnerHealth`, `downloadAgentPackage` (no credential), `createExecutorAgentInstall`,
`getExecutorAgentInstall`, `confirmExecutorAgentInstallHostKey` and `setExecutorIntegrationAuthorisation`.
The API then had 241 paths, 267 operations and 644 schemas; migration head `0046`. No error code is added:
refusals are typed details of existing codes (`contracts/domain/v1/error-codes.json` notes). The domain
identifiers gain `executor_enrollment_id` (`exen`) and `executor_agent_install_id` (`exai`). The operations are
sealed here and implemented by the stage-1 lanes; none behaves until its lane lands.

## Combined contract `1.13.0` (historical)

The serial CMP integrator reconciles C2–C4 with owner hotfixes06b94745/99b337fb.
The current API has230paths/256operations/619schemas; migration head0043.
The additive cost preflight slice supplies source-bound estimates and explicit ceiling consent.
Both StartRunRequest and StartArV3BetaGroupRequest retain optional relaxed_limits.
Comparison evidence, spend consent, expert review and the stage APIs remain present.
The records below describe their own historical seals, rather than the combined counts.

## Comparison C2 seal `1.11.0` (historical branch)

`CMP-SEAL-C2` (wave C2 of the comparison modules, `docs/architecture/adr/ADR-0025-comparison-modules.md`)
adds the version comparison AI, specifications, launch queue and reports as sealed stubs, every operation
answering `503 dependency_unavailable` until its lane wires it, and `comparison_modules` first while the
«Сравнение версий» module is off. The AI check of the doubtful pairs of a document set
(`estimateComparisonAiPairCheck`, `startComparisonAiPairCheck`, `getComparisonAiPairCheck`, the three controls and
`listComparisonAiPairHints`); the AI description of changes, per series (estimate, start, read and six
controls: pause, resume, cancel, «Досчитать», «Убрать из очереди», «Повторить листы с ошибкой») and per sheet pair
(read, history, estimate, start, MD of one sheet) with the «Проверить» list of a transition; the deterministic
positions of a specification page and sheet pair and the AI comparison of whole specifications per transition;
the launch queue of a project and the installation's AI queue; and the deterministic MD summary of a series and
the PDF reports (a draft with its estimate, then a start that consents to it, continue, «Пересобрать PDF»,
delete, «Подготовить отчёт для заказчика», the downloads). Fifty in all. Every AI start carries the
digest of the estimate it consents to, in micro-USD, with the ceilings of USD 10 per job and USD 50 per day for
the installation and a pause when the spend passes 1.2 times the estimate (a connection that is not metered has
no ceiling). Reads are any one role; every write is keyed and an expert's act. `ExecutorWorkKind` gains
`comparison_pair_check`, `comparison_sheet_changes`, `comparison_spec` and `comparison_report`. The contract
items wave C1 left: `ComparisonMatrixStaleReason` gains `algorithm_changed`, `ComparisonMatrixColumn` gains
`label_source`, `ComparisonPairPage` gains `raster`, and `startComparisonSeries` states
`comparison_matrix_stale` and `comparison_versions_few`. The version rule
(`docs/program/VERSIONING_AND_FREEZE_POLICY.md`) reads this as a **minor**. The surface is 176 paths, 198
operations and 517 schemas (131, 148 and 432 under `1.10.0`). No error code is added. Migration
`0040_comparison_ai_reports` adds twelve tables and widens `ck_executor_route_work_kind`.

## Owner hotfix seal `1.12.0` (historical branch)

`HOTFIX-SECTION-LIMITS-BACKEND-20261030` adds optional `relaxed_limits` to
`startRun` for all 14 non-AR sections. True selects a separate immutable
profile/bundle pair with a 64,000-token output request and disables the
application's per-Run cost halt. The 12-window operational size bound remains.
Absent or false keeps the old behavior. This is an additive minor change:
131 paths, 148 operations and 432 schemas remain.

## Owner hotfix seal `1.11.0` (historical branch)

`HOTFIX-AI-LIMITS-20261030` adds the optional `relaxed_limits` boolean to
`startArV3BetaGroup`. Absent or false preserves the current cost ceiling and
16,000-token output request. True selects no application cost halt for the six
created Runs and requests up to 64,000 output tokens; provider limits can still
refuse the request. The flag is part of the command fingerprint and is saved with
the group command so workers retain it after a restart. This is an additive
minor change: 131 paths, 148 operations and 432 schemas remain.

## Version `1.10.0`

`CMP-SEAL-C1` (wave C1 of the comparison modules, `docs/architecture/adr/ADR-0025-comparison-modules.md`)
adds the version comparison core as sealed stubs, every operation answering `503 dependency_unavailable`
until its lane wires it. The effective matrix of a document set: `getComparisonMatrix`,
`prepareComparisonMatrix`, `applyComparisonMatrixEdits` (a keyed batch that carries the base matrix revision;
a stale base is `409 conflict`), `undoComparisonMatrixEdit`, `listComparisonMatrixEdits` and
`listComparisonAiLinks` (read-only until wave C2). The series of adjacent transitions: `startComparisonSeries`,
`listComparisonSeries`, `getComparisonSeries`, `pauseComparisonSeries`, `resumeComparisonSeries`,
`cancelComparisonSeries` and `finishComparisonSeries`; the sheet pairs of a transition:
`listComparisonSheetPairs`, `getComparisonSheetPair` and `streamComparisonPairTile`; and the read models
`getComparisonOverview` and `getComparisonQueueSummary`. Reads are any one role, every write is keyed and an
expert's act. `CreateComparisonUploadRequest` gains the optional `compare_after_preparation`. While the
«Сравнение версий» module is on, `approveSheetPairing`, `withdrawSheetPairing` and `generateComparisonSummary`
answer `503 dependency_unavailable` (`comparison_versions_module`). The version rule
(`docs/program/VERSIONING_AND_FREEZE_POLICY.md`) reads this as a **minor**. The surface is 131 paths, 148
operations and 432 schemas (115, 130 and 351 under `1.9.0`, which sealed the comparison upload, the order of
the versions of a document set and the page reads). No error code is added. Migration `0039_comparison_core` adds
seven tables and migrates the active approvals of `0035` into manual matrix edits.

## Version `1.8.0`

`CONTRACT-1-8-0-01` seals the content that `COMPARE-PERSISTED-SUMMARY-01` added under `1.7.0` (owner
ruling `R-146ar`). Three operations: `approveSheetPairing` and `withdrawSheetPairing` (an expert stores
and ends the approval of one sheet pair that `compareDocumentVersions` proposed, append-only, keyed and
refused to an account without `expert`) and `generateComparisonSummary` (an expert asks once for an AI
summary over the approved pairs; only a recorded implementation exists, any other mode answers
`503 dependency_unavailable`). `compareDocumentVersions` gains the optional and nullable
`approved_pairs`, with the optional `summary`. The version rule
(`docs/program/VERSIONING_AND_FREEZE_POLICY.md`) reads this as a **minor**: operations, schemas and
optional fields are added and nothing disappears. The surface is 98 paths, 111 operations and 321
schemas (92, 104 and 301 under `1.7.0`). No error code or migration is added by the version move; the
content came with migration `0035_comparison_records`.

`ANALYSIS-PRESETS-01` (owner ruling `R-146av`) adds, under the same `1.8.0`, the named presets of how a run
starts: `listAnalysisPresets` (any role), `createAnalysisPreset`, `reviseAnalysisPreset` and
`archiveAnalysisPreset` (an administrator, keyed; a revision and an archive are new rows of an append-only
history), the optional `StartRunRequest.preset_id` (exclusive with `executor_connection_id`) and the
optional, nullable, read-only `RunStatus.preset`. A run start selects one setting per run, the executor
connection, so a preset is a name and that connection; the cost ceiling is a process-wide setting and no
threshold is an input of a start, so a preset holds neither. No error code is added (the refusals reuse
`validation_failed`, `conflict`, `not_found` and `permission_denied` with their existing detail keys) and
migration `0037_analysis_presets` adds one table and one nullable column of `audit_run`. The identity of a
preset and of each revision is `evt_<ULID>`, the id of the audit event written with it; a dedicated prefix
is a change of the domain contract, which this addition does not make. `2.0.0` stays reserved (owner ruling `R-146ar`,
`D-233`: the strict reading of the removal of `AnalysisProfileStatus.builtin`).

## Version `1.7.0` (historical)

`PROD-11-AR-V1-V2-REMOVAL-01` removes АР v1 and v2 from the server (`ADR-0024` section 2, `AD-12`).
`startRun` and `reauditRun` on a version classified АР answer the existing `422
section_profile_unavailable`: АР is analysed only by the six-Run group (`startArV3BetaGroup`) and has no
text profile, and the error catalogue keeps its 27 codes. `listAnalysisProfiles` returns `profile: null`
for АР (the property was already nullable). The enum `AnalysisProfileStatus` loses its member `builtin`,
which only the АР v1 profile carried, and keeps `draft` and `reviewed`; the description of `reviewed` is
corrected to what the status is, a package whose open questions a lane answered in writing with no human
review (`R-146ag`, `D-223`). `FindingCategory` is unchanged. The version rule
(`docs/program/VERSIONING_AND_FREEZE_POLICY.md`) reads this as a **minor**: no field, path or operation
disappears, a response that carried `builtin` never will, and the narrowing for АР is announced by an
existing error code. The strict reading of «remove» is a major; the task file records both and the
integrator confirms the number. The surface is 92 paths, 104 operations and 301 schemas. No error code or
migration was added.

## Version `1.6.0` (historical)

`EXEC-PAR-START-01` lets a run name its executor. `startRun` accepts an optional
`executor_connection_id`; absent, the run follows the global route exactly as before. Present,
the run freezes that connection's current revision when this release serves its kind, the
connection's current key has a passing probe and it is not archived; otherwise the start is
refused before any run exists (`validation_failed` on `executor_connection_id` for an unknown
or malformed id, `dependency_unavailable` with `dependency: executor_connection` for a
connection that cannot serve now). A named connection never falls back to the route's standby
or to another connection, and the same idempotency key with another connection is
`idempotency_key_reuse`. `reauditRun` keeps the original run's named executor. `RunStatus`
gains a read-only, optional and nullable `executor` (`RunExecutor`: `connection_id`,
`display_name`, `pin_id`); a run that froze no connection omits it, and nothing about a
connection's kind, address, key or probe is exposed. The surface is 92 paths, 104 operations
and 301 schemas. No error code or migration was added.

## Version `1.5.0` (historical)

`AR-V3-BETA-PACK-STATUS-API-01` adds the authenticated, read-only
`getArV3BetaPackStatus` operation. It reports whether a reviewed AR v3 beta pack is
installed on the server and, when it is, the pack's profile and prompt-bundle IDs, the
sealed pack digest, the six scope IDs and the reviewer attestation that came with the
manifest. The attestation is a record the server shows, not a statement that it is true;
no map, set or snapshot identity, scope digest, file path or environment value is
exposed. The surface is 92 paths, 104 operations and 300 schemas. No error code or
migration was added.

## Version `1.4.0` (historical)

`AR-V3-BETA-GROUP-API-SEAL-01` adds the authenticated, read-only
`getArV3BetaGroupReview` operation. Its six ordered members expose only verified,
review-only topics and provisional citations, or an explicit pending, failed or
verification-refused state. The surface is 91 paths, 103 operations and 298
schemas. No error code or migration was added.

## Version `1.3.0` (historical)

`AR-V3-BETA-RUN-STAGE-SEAL-01` adds a profile-specific AR v3 beta stage ID to
`RunStatus.stages` and `degradation_set`. The nine legacy `StageId` values and
analysis stage registry remain unchanged. The surface is 90 paths, 102
operations and 291 schemas. Domain, analysis and events version pins move
together.

## Version `1.2.0` (historical)

`AR-V3-BETA-SIX-RUN-02` adds explicit start and read operations for one AR v3
beta group with six durable Run IDs. Start requires an installed reviewed pack;
without one it refuses before writing. The surface is 90 paths, 102 operations
and 290 schemas. Domain, analysis and events version pins moved together.

## Version `1.1.0` (historical)

`EXEC-IMAGE-DELIVERY-01` adds `getExecutorTaskImage` and an optional image descriptor
on a claimed runner task. The binary read is restricted to the token holding the
current claim; the image bytes are checked against the saved Blob reference and
never stored a second time in the task table. The surface is 88 paths, 100 operations
and 286 component schemas; the 27 error codes and migration head are unchanged.
The domain, analysis and events `contract_version` literals move with the API.
The active text stage does not emit images.

## Version `1.0.0` (historical)

`info.version` and the `ErrorEnvelope.contract_version` const read `1.0.0` since
`BETA-CONTRACT-SEAL-01`; they were `1.0.0-draft.1`. The domain, analysis and events families
moved with them, and `getProductVersion` reports the same string. The surface the seal froze is
73 paths, 83 operations and 242 component schemas, with a 27-code error catalog. A change after
the seal follows `docs/program/VERSIONING_AND_FREEZE_POLICY.md`: an optional addition is a minor
version, a removal, a rename or a change of meaning a major one. Every consumer of the literal is
listed by `python3 tools/plan/pin_sweep.py contract-version`.

## The frozen PC-01 surface

`openapi.json` is the frozen document for the PC-01 slice, created by session `A1`
under owner decision `OD-14` and released at Gate A. It is seam `S8` of
`docs/program/P02_SEAMS.md`.

**Twelve operations at Gate A, and no thirteenth without a reseal.** Exactly the eleven
capabilities `docs/program/tasks/P2-API-01.md` enumerated. Adding an endpoint is a contract
change, not an implementation detail, and every one since was added by a recorded reseal:
the document's own `info.description` narrates each, ending with `W52-SEAL-01` (the release
version, history and account read mark), and it states the
current totals once, in its last paragraph. `tests/contract/api_v1/test_doc_prose_facts.py`
pins those totals independently.

**Authorization since `W49-SEAL-01`.** The document still declares one bearer scheme and
no format, issuer or flow. What a subject may do is the account's role set, read by the
server on every request against written registers in `src/auditmanager/api/security.py`;
a refusal is `403 permission_denied` with `required_capability` naming what is missing.
Three operations take no credential: `issueToken`, `submitRegistration` and
`readRegistrationStatus`. The domain catalog code `rate_limited` is answered by the edge in
front of `/api/v1`, before any operation, and is therefore not declared on an operation --
as the edge's own body-size refusal is not.

| Consumer | What it does with this file |
|---|---|
| `A5` | generates `web/src/shared/api/generated/**` from it, deterministically |
| `B6` | implements `src/auditmanager/api/routers/**` against it |
| `B7`, `B8` | use `A5`'s generated client and never call `fetch` directly |

### Why JSON rather than YAML

The runtime lock carries no YAML parser and adding a root dependency is a
single-owner task under FF-01 §2.8, not a lane decision. JSON is parseable by the
standard library, by the governance environment's `jsonschema`, and by every
TypeScript generator. A YAML document would have needed a dependency to validate its
own gate.

### Validating it

```sh
.venv/bin/pytest tests/contract/domain_p02/test_openapi_document.py
.venv/bin/pytest tests/contract/api_v1
.venv/bootstrap/bin/python tests/contract/domain_p02/openapi_metaschema_check.py
```

The first runs in the runtime environment with the standard library alone, and never
skips. It checks the document's structure, that every `$ref` resolves, that no
component is unreachable, that every enum drawn from a frozen contract equals that
contract, that every identity carries its contract pattern, and that nothing in the
surface leaks an address, a credential or a model payload.

The second runs under the governance interpreter, which is the only one carrying
`jsonschema`, and validates every schema object against JSON Schema 2020-12 —
meaningful because OpenAPI 3.1 aligned its Schema Object with that dialect.

### Closed shapes, and why nothing here uses `allOf`

Response shapes are `additionalProperties: false`, because this repository refuses
silent extra fields: a field added without a contract change must fail, not pass.

That closure does not survive composition. Under JSON Schema 2020-12 — the dialect
OpenAPI 3.1 adopts — `additionalProperties` is evaluated against the property
annotations of **its own** schema object, and sibling `allOf` branches contribute
nothing to it. So `allOf: [{$ref: <a closed schema>}, {properties: {...}}]` rejects
the very properties the second branch adds. `FindingDetail` was written that way and
could never validate the body `GET /findings/{finding_uid}` returns; session `A5`
found it, `A7-FIX` repaired it by restating `FindingDetail` as one closed object.

**So: a schema that extends another restates it, and stays closed.** The document
contains no `allOf` at all. The alternative that is idiomatic in plain JSON Schema —
an open base plus `unevaluatedProperties: false` on each composed schema — is
correct, and was rejected here because it requires the base to stop declaring
`additionalProperties: false` itself, which is the property
`tests/contract/domain_p02/test_openapi_document.py` asserts directly.

Restating costs duplication, and `tests/contract/api_v1` pays it down: it asserts
`FindingDetail` is `Finding`'s property set plus exactly `latest_comment` and
`decision_event_count`, compares the shared entries by value, and searches the whole
document for any `allOf` composing a `$ref` to a closed schema. Drift is a test
failure rather than a silent divergence.

### Changing it

A breaking change is a new contract version — `contracts/api/v2/**` — never an edit
here. The frozen document stays as the record of what was promised.

A non-breaking addition is still a change to a file every Gate B and Gate C session
consumes: it goes to the integrator with the failing test that motivates it, per
`docs/program/P02_SEAMS.md` §10.
