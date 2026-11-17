# Task RUN-RESTART-01 — restart an ended run from any stage, and lift the analysis time limits

task_id: RUN-RESTART-01

## Outcome

1. **Time.** A live Attempt has no age ceiling. A model call's window is its stage row's window (`ROW_TIMEOUT_SECONDS`), not the
   ~540 s the stall window cuts it to today. Local work between calls is bounded by a silence watchdog that ends the run as `failed`
   (`interrupted_reason = attempt_stalled`) without re-queueing it, and a worker thread that does not return its slot after the fence
   does not block the worker forever.
2. **Restart.** On a `partial`, `failed` or `cancelled` run an expert or administrator restarts the analysis from any of the eight
   stage chips (Подготовка, Текст, Блоки, Сверка, Свод, Нормы, Критик, Уточнение). A new run is created with all the settings of the
   source; everything before the chosen chip is taken from the source chain without a new paid call (stage artifacts by reference,
   model replies replayed); the chosen chip and every later one are computed. When the new run publishes, the source is tombstoned
   (`deleteRun`, migration 0066) and the expert's decisions on the source chain's findings are carried to verbatim-matching findings.
   A replay that cannot be made fails the new run with a named reason before any paid call and publishes nothing; the source stays.

Owner rulings: `R-155a`…`R-155i` (`docs/program/OWNER_RULINGS_2026-09-17.md` §3.56). They change `R-151i` for a restart and, for a
restart only, the confirm-only carryover of `W59-DECISION-CARRYOVER-01`.

## Frozen inputs

- base: `origin/dev` `3214032ba` (0.30.8); contract `1.58.0` (surface 302 paths / 331 operations / 823 schemas); migration head
  `0070_document_group`. Known reds on this base, not this task's: `live_state`, `wave_governance` (ANALYSIS-REPAIR-* task files),
  `polling.test.ts`, `cmp_seal_c4`, `seal52`.
- the default production analysis path is extended review **v2** (`runs/preflight.py:76-83`, `infra/deploy/compose.server.yml:269`);
  a v3 source is refused by a restart.

## Ownership (this task holds the contract slot and the migration head until it merges to dev)

Integrator: session pdf-analysis-28, branch `integration/run-restart`. Lanes branch from it; nobody else edits these paths meanwhile
(agreed with pdf-analysis-01 and pdf-analysis-c7 on 2026-11-17).

| Lane | Owns | Starts |
| --- | --- | --- |
| L2 time | `src/auditmanager/jobs/{lease.py,repository.py,temporaries.py}`, `src/auditmanager/workers/**`, `src/auditmanager/executors/{pull.py,http_adapter.py,ssh_adapter.py,ssh_transport.py}`, their unit tests, the docs and comments that state 7200 | at once |
| L0 contract | `contracts/**`, `db/migrations/versions/*0071*`, `web/openapi/openapi.json`, `web/src/shared/api/generated/**`, `tests/support/expected_facts.json`, contract/schema pin tests, `src/auditmanager/api/schemas/models.py`, the new router and its port signature, prose counts | at once |
| L1 executor | `src/auditmanager/runs/{executor.py,extended_review.py,stage_reuse.py,preflight.py,commands.py}`, `src/auditmanager/jobs/extended_review.py`, `src/auditmanager/bootstrap/adapters.py`, the attempt progress signals in `runs/executor.py` | after L0 merges |
| L1b decisions | `src/auditmanager/decisions/**` and the post-terminal carry step's call site (agreed with L1) | after L0 merges |
| L3 web | `web/src/features/start-run-from-stage/**` (replaced by a restart feature), `web/src/widgets/{run-stages-dialog,run-progress,run-list}/**`, the deleted-run page note, the `attempt_stalled` label, `web/tests/unit/**` for them | after L0 merges |

## Design (verified against the base; file:line on `3214032ba`)

### Time (L2)

- `ATTEMPT_HARD_CAP_SECONDS` (`jobs/lease.py:26,78,156`) becomes `math.inf` for a live Attempt (never `None`; `remaining_seconds`
  then yields `min(inf, stall - silence)`, finite).
- Call window: `answer_window` (`executors/pull.py:128-140`, and `executors/http_adapter.py:94-97`) takes `min(row window,
  remaining)`, where after `call_started()` (`lease.py:102`) `remaining` is at most the 600 s stall window → every call is cut to
  ~540 s. A call's window must be its row window (`analysis/text/cell_settings.py:45`); silence inside a call stays bounded by the
  agent's activity window (600 s) and the runner claim lease.
- Silence watchdog: a live Attempt with no sign of life for `ATTEMPT_LOCAL_SILENCE_SECONDS` (30 min, a named constant) outside a model
  call is fenced. The fence must not go through the re-queueing `reclaim_expired` (`jobs/repository.py:962-1100`, re-queues unless an
  effect is ambiguous or `count >= 3`); it fails the run with `fail_reclaimed_run(..., interrupted_reason="attempt_stalled")`
  (`interrupted_reason` is a free string, `api/schemas/models.py:1874`; no contract change).
- Slot recovery: the fence revokes authority but the thread keeps the slot (`repository.py:965`; `AUDITMANAGER_WORKER_SLOTS` = 1,
  `workers/service.py:41`). If the fenced thread has not returned within a bounded grace, the worker process exits so the container
  restart policy brings a fresh one (state is durable; leases are reclaimed). The same covers `cancelRun`, which today only marks the
  database (`cancel_for_run`, `repository.py:1765`).
- The SSH adapter passes `hard_remaining - 60` as its per-call ceiling (`executors/ssh_adapter.py:165` → `ssh_transport.py:549-566`);
  with no cap it needs a finite per-call constant (7200 s; the agent stops itself at 7140 s).
- Temporaries: `STALE_AFTER_SECONDS = cap + 60` (`jobs/temporaries.py:76`, `workers/service.py:138,173`) gets its own constant; the
  in-process sweep skips while a slot is busy; the startup sweep keeps the age rule.
- Pins: `tests/unit/jobs/test_attempt_liveness.py`, `tests/unit/jobs/test_stale_temporaries.py`,
  `tests/unit/workers/test_running_sweep_threshold.py`, `tests/unit/shared/test_tempsweep.py`,
  `tests/unit/executors/test_ssh_adapter.py:240,267`. Not changed: the contract clamp of a host call 1..7200 s
  (`api/schemas/models.py:6058`, `tests/unit/executors/test_pull_host_call.py:96`). Prose: ADR-0028:77, `DEBT_REGISTER.md` D-285,
  `docs/program/tasks/HOSTS-AGENT-01.md:78`, `cell_settings.py:43`, `runs/extended_review.py:412`, `analysis/text/budget.py:187`,
  `api/app.py:324` (stale: a lost lease re-queues and resumes, `runs/executor.py:1449,1501`, `workers/service.py:61-65`).
- Progress signals (in `runs/executor.py`, owned by L1 to avoid two writers): today `executor.py:1275,1308` (preparation pages) and
  `:1489` (extended counters). Add: at Attempt claim, after reused stages are materialised, on every replayed reply, and in each
  deterministic step (`document_context_build`, evidence gate, publication, carry step).

### Contract and migration (L0)

- A new operation `restartRun` (`POST /runs/{run_id}/restart`, roles expert/admin, keyed) with a new enum `RestartPoint`:
  `preparation, text, blocks, cross_check, merge, norms, review, correction`. `startRunFromStage` stays as it is (tests pin it and it
  admits published sources). `StageId` is bound to the registry (`web/tests/guards/stage-dictionary.guard.test.ts`) and has no
  `comprehensive_analysis`, so `RestartPoint` is its own enum.
- `RunStatus`: the restart point and the source; a tombstoned source answers the run that replaced it (link through the restart's
  command record, `audit_run.command_id = audit_run_deletion.command_id`, no new column on the frozen `audit_run`).
- Cost estimate: the request carries the restart point (`runs/preflight.py:693` today prices the whole run).
- `DecisionCarriedFrom`: an origin «from run» beside `version_ordinal`; a carry mode `restart`.
- Migration `0071`: the restart point stored for the new run (widen `ck_audit_run_start_stage_id` or a column of its own); the
  downgrade refuses while rows hold new values (pattern of 0060); `ck_expert_decision_event_carried_from_verdict` (0058) and the
  carryover constraints admit a same-version restart carry.
- `contracts/domain/v1/state-machines.json`: `run_creation.cases` says a restart makes no new run_id — add the restart case. The three
  domain files move together; the API README seal and `openapi.json`; `error-codes.json` prose for the new refusals.
- Must move with the contract: `web/openapi/openapi.json` (byte copy, `tests/contract/api_v1/test_contract_seal.py:87`), the generated
  client (`npm run api:generate`, `api:verify`), `tests/support/expected_facts.json` (incl. `schema_names`), `tests/contract/api_v1/
  {test_contract_seal,test_openapi_conformance,test_doc_prose_facts,test_surface_counts_in_prose}.py`,
  `tests/contract/domain_p02/test_openapi_document.py:152,480`, `docs/program/CONTRACT_PIN_REGISTRY.md`, `P02_SEAMS.md`, the README
  heads, `CURRENT_STATE.md:100-101`, `ALPHA_ROADMAP` and `api/app.py` / `routers/declarations.py` schema counts,
  `docs/manual-tests/PC-01_prototype.md:39`, `scripts/recovery/schema_coverage.py:41`, `tests/integration/db/
  test_schema_invariant_inventory.py` and `test_application_role_grants` (measured on a throwaway PostgreSQL),
  `test_schema_shape.py:339`, `tests/integration/api/test_role_register.py:69,784`, `test_authorization.py:163`,
  `web/tests/contract/seam-operations.contract.test.ts:279`, contract_version literals in web test fixtures,
  `tests/e2e/test_pc01_journey_conformance.py` and `tests/e2e/pc01/journey/{README.md,manifest.json,write.mjs}`.

### Executor (L1)

- Acceptance (`runs/commands.py`): source `partial|failed|cancelled`, not tombstoned (today's start-from-stage does not check,
  `commands.py:1423`), no live lease, a stage-layout run (otherwise reply keys hold the connection revision,
  `runs/extended_review.py:297-299`), v2; one active restart per source; `started_by_user_uid` required (the tombstone's
  `deleted_by_user_uid` is NOT NULL). The new run copies the source's frozen settings (norms snapshot — today
  `start_run_from_stage` pins today's, `commands.py:1511` — profile/bundle, policies, stage plan and cell bindings). Pre-check before
  enqueue: settings equal, and a saved reply exists for every call identity the kept procedures made in the source chain.
- Preparation by reference as today (`plan_stage_reuse`); «Подготовка» as a point = a full rerun with the same settings.
- Text by reference **byte-identical**: the source's `analysis.text_observations` blob is reused as is (same sha256). Its digest
  enters `source_sha256` of every reply key (`analysis/extended/core.py:181`, called at `extended_review.py:2096`) and it carries
  `run_id` and per-observation `model_call_id` (`analysis/text/artifact.py:105-121`) — never rewrite it. A rule of its own:
  `plan_stage_reuse` demands `succeeded` (`stage_reuse.py:160`) but a partial source's text row is `PARTIAL`
  (`executor.py:1644-1650`): check sha/size, `stage_version`, profile/bundle/provider mode, complete `pages_analysed`, the
  visual-pages flag. Seam: `executor.py:1523-1553` (bypass `_run_text_analysis_stage`).
- Replies by chain: `extended_unit` (`jobs/extended_review.py:42-66`) and `extended_context_unit` (`:21`) read one run; add chain
  reads — own run first, then the nearest ancestor, rows with a reply blob and status succeeded/truncated only. A replay writes no
  `model_call` row, so the chain is walked to the original run.
- The boundary is the call identity (`call()` `extended_review.py:1895` → row via `runs/stage_layout.py:102` `row_of_phase`), not
  `phase()` (it only writes status). v2 identities: `blocks:N[:leg1|leg2|judge]`, `comprehensive:N`, `norm_verification:queries:N`,
  `norm_verification:N`, `finding_review:substantive:N`, `…:repair:1`. «Свод» makes no model call.
- Strict refusal: `_run_workflow_v2` catches every DomainError and saves `partial` (`extended_review.py:2410-2432`), and the evidence
  gate would still publish. A restart refusal must escape that catch: text stage `FAILED` with `terminal_detail {stage_id, reason}`,
  no publication, no tombstone, no carry. Reasons: reply missing (also a leg silenced by the breaker, `extended_review.py:413,452`),
  request changed, settings differ.
- Norm lookups are not provably deterministic (search timeout 1.2 s → `lookup_unavailable`, `extended_review.py:803,814,846`; the
  external embedder `:706,905`; latest embedding build `norms/search/semantic.py:94`): a restart from «Критик» may refuse at «Нормы»
  — say so in the refusal. For runs made after this task, persist norm lookup results and replay them.
- Cost: price only the computed procedures, bounded by the source's actual per-row call counts (`preflight.py:618-660`;
  `bootstrap/adapters.py:1375-1384`).
- Tombstone when the new run publishes (`R-155g`), in the terminal transaction.

### Chain, lineage and tombstones (decided by L1)

- **Chain.** The chain of a run is the run, its restart source, that source's own restart source, and so on up to the first run that is no restart
  (`runs.restart.restart_chain`). A restart of a run that is itself a failed or cancelled restart is allowed; its source is that run.
  Replies are looked for along the chain (own run first, then the nearest ancestor); the text observations are taken from the nearest run of the chain
  whose `text_analysis` row holds the artifact (a restart that took the text itself holds it by reference).
- **Lineage.** Every run whose chain ends at the same root. A command refuses a restart while *any* restart of the lineage has not ended
  (`conflict` / `restart_in_progress`; the database's partial unique index `ux_audit_run_active_restart` is the per-source last word).
- **Tombstones.** When restart run R ends `published` **or** `partial` (owner `R-155g` «при публикации нового»: a partial run has published findings too;
  the guard `trg_audit_run_deletion_by_restart` of migration 0071 was changed from `published` only), the executor writes, in the transaction that moved R
  to its terminal state and after the state change: (a) the tombstone of R's direct source with **R's own restart command** (the guarded path), and
  (b) for every other lineage run that is not tombstoned and ended `partial`/`failed`/`cancelled`, a tombstone with a plain `delete_audit_run` command
  record of its own (key `restart-lineage-<R>-<run>`, outcome `{run_id, replaced_by_run_id: R}`). A lineage run that is active or published is left alone.
  So exactly one run of the lineage stays listed. The step is idempotent (`runs.restart.tombstone_lineage`).
- **`replaced_by_run_id`** of a tombstoned run (`runs.restart.replaced_by`): the run whose `command_id` is the tombstone's; else the one run of the lineage
  that is a restart, ended `published`/`partial` and is not tombstoned; and a replacement that was itself replaced later is followed to the run that
  stands. A plain `deleteRun` of a run outside every restart lineage replaces nothing.
- **Settings copy.** The new run copies version, project, input digest, norms snapshot (and a verified retrieval-set pin), analysis profile, prompt bundle,
  provider mode, publication mode and the stage plan's cells. The consent it runs under is the one the restart estimate binds: the estimate refuses
  (`restart_settings_differ`) unless today's source digest, extended-review policy, window and cells equal the source's accepted consent. The layout
  revision named in the new run's plan is today's (the cells are proven equal). The cell **bindings** (`audit_run_cell_binding`) are dispatch's product,
  written for the new run at its claim as for every planned run; a reply key holds neither host nor connection, so the replies replay on any member.
- **`finding_observation.model_call_id`** of the findings a restart publishes from a taken text points at the **source's** model calls (a foreign key to
  `model_call`, satisfied by the source's rows): the findings come from those calls.

### Decisions (L1b)

- `carry_over_decision` refuses same-version pairs (`decisions/carryover.py` `_check_provenance`, 0058); add mode `restart`.
- Verdicts (✓/✕) carry with `carried_from_decision_id`; comments carry as comment events with provenance text; severity carries when
  the target observation has `proposed_severity` (`decisions/ledger.py` `_SEVERITY_TARGET`), otherwise it is skipped and reported.
- Match 1:1 on `finding_text`, `recommendation_text`, `category` and evidence (page, quote, `char_start/end`) (0002:916,987); block
  findings without evidence on text and category; ties by order, else skip.
- Author `run.started_by_user_uid`; one command per carried event with a deterministic key (`uq_expert_decision_event_command_id`);
  carried events do not vote in precedents (`precedents/votes.py:57-64`).
- After `publish_candidate_groups` (`runs/executor.py:~900-925`) as an idempotent post-terminal step with a sweeper; decisions
  gathered from the whole chain.

### Web (L3)

- «Перезапустить с этого этапа» in the dialog of each of the eight chips, for `partial/failed/cancelled` and expert/admin.
- The confirmation: taken vs computed, estimate and consent, «Старый прогон будет удалён после публикации нового; решения эксперта (N)
  перенесутся на совпавшие находки», the norms warning.
- A deleted run's page: «Прогон перезапущен» with a link to the new run; the new run: «Перезапущен с этапа … из прогона …». The label of
  `attempt_stalled`.

## Checks

- Each lane: focused unit tests of its seams; L0 the contract battery and `npm run api:verify`; web `tsc` and component tests.
- Integration on a throwaway stand (tmpfs PostgreSQL + MinIO; `tests/integration/runs/harness.py` needs `DATABASE_URL` and `S3_*`;
  docker is a snap and cannot see `/tmp`): a restart from each point — zero model calls for taken procedures; refusal on a missing
  reply and on a changed request with nothing published; a chain through a tombstoned run; carry (matched, unmatched, severity without a
  target, comments); refusal of a published, a tombstoned and a running source; tombstone and run creation atomic and idempotent;
  roles; migration up and down. A partial/failed source needs failure injection (the existing fixture ends `published`,
  `tests/integration/runs/test_start_from_stage.py:47`).
- Time: an Attempt past 2 h (patched constants); a call past 9 min; the watchdog fails a local loop with no re-queue; the slot returns;
  temporaries of a live Attempt survive; an SSH call stays bounded.
- No `make gate` unless the owner orders it.

## Host rules for every lane

- Kill only by PID confirmed to be your own descendant; never `pkill -f`/`killall` with a pattern.
- One heavy run at a time per project: take `/root/projects/PDF-Analysis/.local/evidence/exec2-d292/host-run.lock` (exclusive) and
  start only when `free -m` available ≥ 2500 MB; cap each locked command at `timeout 1200`, one test group per command, release
  between groups. Disk is at 95 %: no new `.venv` or `node_modules` (they are symlinks to `.local/worktrees/ui-parity-r3`).
- Never touch `/srv/auditmanager`, the production stand, `/opt/pdf-analysis-agent` or another project's paths and containers.

## L1 results (executor lane, branch `agent/run-restart-l1-executor`)

What the lane built, where, and what it measured (commands and counts are in the lane's final report; the pins are the tests named here).

- **Command** `runs.commands.restart_run` (`COMMAND_TYPE_RESTART_RUN`): the refusals in the contract's words, none of them writes the key
  (`tests/integration/runs/test_restart_command.py`, 35 cases on a throwaway PostgreSQL). Wired by `ExecutionAdapter.restart_run`; the L0 stub and its
  503 prose are gone.
- **Estimate** `RunCostPreflight.estimate_restart` + `RestartPricing`: rows before the chip priced at zero, a row the source chain finished bounded by
  its actual calls, the digest bound to this source and chip; `RunAdapter.estimate_run_cost(restart_point=...)`.
- **Executor** (`runs/executor.py`, `runs/restart.py`, `runs/restart_text.py`, `runs/extended_review.py`, `jobs/extended_review.py`): preparation by
  reference, the text blob byte for byte, the replies of the chips before the chip by chain; a replay that cannot be made raises `RestartRefused`
  (not a `DomainError`: the v2 workflow would catch that and save a partial result), the text row fails with `{stage_id, restart_point, reason}`, the
  gate is not asked. Tombstones and the lineage in the terminal transaction; the carry after it (lazy import of `decisions`), swept by the worker.
  Pins: `tests/unit/runs/test_restart_replay.py`, `test_restart_rules.py`, `test_restart_carry_sweeper.py`,
  `tests/integration/runs/test_restart_executor.py` (a restart from each of the eight chips, refusals, chains, signs of life).
- **Norm lookups** of the v2 flow path are saved with the run's extended review (`norm_lookup_results`) and replayed by a restart from a chip after
  «Нормы»; a run made before this task saved none, so a restart from «Критик» may still refuse at «Нормы» (`restart_request_changed`,
  `restart_point: norms`). The non-flow v2 path (no `flow_repair_policy`) still looks the corpus up live.
- **Migration 0071** guard changed to admit `partial` as well as `published` (owner `R-155g`); `test_run_restart_migration.py` proves `partial` and
  `published` are admitted and `failed`, `cancelled` and `running` refused.

Known limits: the integration of the executor runs a source of the v2 workflow **without a stage plan** (a planned run needs a host and a binding per cell
at dispatch); the command's checks run on planned sources whose stage rows and calls are seeded. A planned run restarted end to end is the integrator's
live check. A block leg that failed after its retries has no reply, so a restart from a later chip refuses (`restart_reply_missing`, `restart_point: blocks`).
Two restarts of one lineage racing past the command's read are caught per source by the database index only.

## Integration and rollback

Lanes commit on their branches; the integrator merges L2 and L0, then L1, L1b and L3, runs the checks above on the merged tree,
writes `release-notes/0.31.0.json` with `VERSION` and its pins, and publishes to `origin/dev` after telling pdf-analysis-c7.
`main` only on the owner's word, not during a live run. Rollback: revert the merge on dev; migration 0071 downgrades only while no
row holds a new restart point.
