# Task HOSTS-SEAL-1 — contract 1.45.0 and migration 0062 for hosts, the stage layout, cell binding and consent v2

## Outcome
OpenAPI 1.45.0 declares the host, stage-layout and readiness operations and the changes of the enrollment, install, health, claim and run-start operations of `ADR-0028`. Migration `0062` creates the tables, columns and checks of decisions 1–9 and 14, and re-creates `trg_audit_run_frozen_guard`. Models, client, identifier prefixes, pins, inventories and the catalogue file follow. The stub modules and the call-journal plumbing the wave-1 lanes need exist, so no wave-1 lane touches a shared file. No behaviour.

## Depends on
- HOSTS-ADR-01
- HOSTS-PIN-01

## Frozen inputs
- domain contract: version literal 1.44.0 → 1.45.0; new identifier prefixes `exh` (executor host) and `slr` (stage layout revision); the state-machine and error catalogues gain no code
- API contract: 1.44.0 → 1.45.0, owned by this task
- analysis/comparison/event contract: version literal 1.44.0 → 1.45.0 only, plus the new file `contracts/analysis/v1/model-catalogue.json` with its schema
- migration head: `0061_decision_memory_m2`; this task owns slot `0062`, revision id `0062_hosts_stage_models`, file `db/migrations/versions/<dispatch date>_0062_hosts_stage_models.py`
- base commit: `8f76b4ed6daadad95f9c001e2c2c0dca717aad2d`
- slot: on 2026-11-09 at about 15:00 the session pdf-analysis-f9, the UI-parity window-3 integrator that held the contract and migration slot under `R-151w`, released it to the HOSTS integrator session (pdf-analysis-d6). Contract 1.45.0 and migration 0062 are therefore this work's. This is a handover, not a ruling.
- architecture: `docs/architecture/adr/ADR-0028-hosts-and-stage-models.md` decisions 1–9, 13, 14, 16; rulings `R-153a`…`R-153f`; plan `docs/program/dispatch/HOSTS-PLAN.md`
- pins: seven models in `docs/program/P02_LOCK.json` after `HOSTS-PIN-01`; the catalogue covers exactly those

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json` (paths); `db/migrations/versions/**` (migrations)
- enumerator_owner: HOSTS-SEAL-1
- totality_query: `python3 -c "import json; print(len(json.load(open('contracts/api/v1/openapi.json'))['paths']))"` and `ls db/migrations/versions/*_006*.py`

## Captured premise evidence
- premise: the literal pins of contract 1.44.0, the migration-head pins, the surface-count prose and the exhaustive enum mirrors are the sets below

### P-01 — files that carry the literal 1.44.0, by top-level area
- captured_at: 2026-11-09
- command: `git grep -l "1\.44\.0" -- . | cut -d/ -f1-2 | sort | uniq -c`
- captured_output:
  ```text
       18 contracts/analysis
        2 contracts/api
        9 contracts/domain
        3 contracts/events
        4 docs/program
        2 infra/deploy
        8 src/auditmanager
        3 tests/contract
        5 tests/integration
        1 tests/support
        1 tests/unit
        1 web/FRONTEND_LOCK.json
        1 web/openapi
        5 web/src
       83 web/tests
  ```
- interpretation: `web/tests` holds 83 files, most of them an error-envelope fixture `contract_version: '1.44.0'` that the client parses against the generated literal. Those are pins and are this task's (`web/tests/**`). The two `infra/deploy` files are `proxy/nginx.conf` and `proxy/tls-server.conf`; both carry the literal in a served 401 and 429 body. In `docs/program` the four files are `ALPHA_ROADMAP.md`, `CURRENT_STATE.md`, `DEBT_REGISTER.md` and `DECISION-MEMORY-01.md`: history, or the integrator's (see Integration contract). A phrase «of contract 1.44.0» that names where a thing was introduced is history and stays; an assertion, constant, served value or fixture envelope is a pin and moves.

### P-02 — files that name the migration head
- captured_at: 2026-11-09
- command: `git grep -l 0061_decision_memory_m2 -- tests scripts src docs/manual-tests`
- captured_output:
  ```text
  docs/manual-tests/PC-01_prototype.md
  scripts/recovery/grant_classification.py
  scripts/recovery/product_purge.py
  scripts/recovery/schema_coverage.py
  src/auditmanager/access/references.py
  tests/integration/db/test_application_role_grants.py
  tests/integration/db/test_decision_carryover_migration.py
  tests/integration/db/test_decision_memory_m2_migration.py
  tests/integration/db/test_decision_memory_migration.py
  tests/integration/db/test_finding_decision_origin_migration.py
  tests/integration/db/test_optimisation_decisions_migration.py
  tests/integration/db/test_schema_invariant_inventory.py
  tests/integration/db/test_schema_shape.py
  tests/integration/recovery/test_grant_classification.py
  tests/integration/recovery/test_product_purge.py
  tests/integration/recovery/test_project_erase.py
  tests/integration/recovery/test_synthetic_drill_compare.py
  tests/integration/recovery/test_synthetic_drill_seed.py
  tests/support/expected_facts.json
  tests/unit/decision_memory/test_status_and_settings.py
  ```
- interpretation: every file that is a head pin moves to `0062_hosts_stage_models` (`scripts/recovery/schema_coverage.py` holds the literal that `tests/contract/test_recovery_schema_head.py` compares with the migration tree). A comment that names where a thing was introduced stays. The census includes `docs/manual-tests/PC-01_prototype.md`, which `tests/contract/api_v1/test_doc_prose_facts.py` scans for the head.

### P-03 — prose that states the size of the surface
- captured_at: 2026-11-09
- command: `git grep -lE "\b(280|308|744) (paths|operations|schemas)" -- src infra web/src docs/program/P02_SEAMS.md ':!web/src/shared/api/generated'`
- captured_output:
  ```text
  docs/program/P02_SEAMS.md
  infra/deploy/README.md
  infra/deploy/proxy/nginx.conf
  infra/deploy/serve.py
  src/auditmanager/api/README.md
  src/auditmanager/api/app.py
  src/auditmanager/api/health.py
  src/auditmanager/api/routers/__init__.py
  src/auditmanager/api/routers/errors.py
  web/src/app/bff/v1/[...path]/route.ts
  web/src/shared/api/authorization.ts
  ```
- interpretation: `tests/contract/api_v1/test_surface_counts_in_prose.py` reads these counts from the frozen document and fails on a stale one; the lane reruns it as the totality query. `tests/contract/api_v1/test_cmp_seal_c4.py` and `tests/support/expected_facts.json` hold the counts as assertions.

### P-04 — exhaustive mirrors of the enums this task widens
- captured_at: 2026-11-09
- command: `git grep -n "Record<\(RunQueueReason\|ExecutorGroupMemberIssue\)" -- web/src ':!web/src/shared/api/generated'`
- captured_output:
  ```text
  web/src/entities/audit-run/model/run-queue-reason.ts:20:export const QUEUE_REASON_LABELS: Readonly<Record<RunQueueReason, string>> = {
  web/src/entities/executor-group/model/vocabulary.ts:28:export const MEMBER_ISSUE_SENTENCES: Readonly<Record<ExecutorGroupMemberIssue, string>> = {
  web/src/entities/executor-group/model/wait-detail.ts:36:export const WAIT_CAUSE_SENTENCES: Readonly<Record<ExecutorGroupMemberIssue, string>> = {
  web/src/entities/version-series/model/job-executor.ts:63:export const JOB_WAIT_LABELS: Readonly<Record<RunQueueReason, string>> = {
  ```
- interpretation: `RunQueueReason` gains `model_unavailable` and `ExecutorGroupMemberIssue` gains `host_disabled`, `model_not_verified`, `model_cooling_down`; each `Record` is a type error until it names them. This task adds one neutral entry each; the final words belong to `HOSTS-WEB-01` and `RUN-SCREEN-01`. The Python mirrors are `GROUP_MEMBER_ISSUES` and `WAIT_REASONS` in `src/auditmanager/executors/model.py`, held by `tests/unit/executors/test_capacity_pins.py`.

### P-05 — where the call journal is written
- captured_at: 2026-11-09
- command: `git grep -n "_INSERT_MODEL_CALL\|_INSERT_PROVIDER_EFFECT\|def prepare_provider_call" -- src`
- captured_output:
  ```text
  src/auditmanager/jobs/repository.py:337:_INSERT_PROVIDER_EFFECT = text(
  src/auditmanager/jobs/repository.py:468:_INSERT_MODEL_CALL = text(
  src/auditmanager/jobs/repository.py:1594:    def prepare_provider_call(
  src/auditmanager/jobs/repository.py:1614:            _INSERT_PROVIDER_EFFECT,
  src/auditmanager/jobs/repository.py:2022:            _INSERT_MODEL_CALL,
  ```
- interpretation: the two statements and the signature are the whole of this task's edit to `jobs/repository.py`. The callers are `runs/executor.py:305`, `runs/extended_review.py:91` and `runs/v3_provider_call.py:237`; they pass nothing new, so existing rows keep `NULL`.

The integrator re-runs every premise command on the actual base before dispatch (`HOSTS-PLAN.md` §5) and corrects it; a premise that no longer holds stops the dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `contracts/**`
- `db/migrations/**`
- `docs/architecture/ADR_INDEX.md`
- `docs/program/P02_SEAMS.md`
- `docs/manual-tests/PC-01_prototype.md`
- `src/auditmanager/api/schemas/models.py`
- `src/auditmanager/api/routers/__init__.py`
- `src/auditmanager/api/routers/declarations.py`
- `src/auditmanager/api/routers/errors.py`
- `src/auditmanager/api/routers/executor_hosts.py`
- `src/auditmanager/api/routers/stage_layout.py`
- `src/auditmanager/api/routers/hosts_ports.py`
- `src/auditmanager/api/security.py`
- `src/auditmanager/api/app.py`
- `src/auditmanager/api/health.py`
- `src/auditmanager/api/README.md`
- `src/auditmanager/analysis/engine/result.py`
- `src/auditmanager/shared/identity/**`
- `src/auditmanager/access/references.py`
- `src/auditmanager/executors/model.py`
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/bootstrap/hosts_adapter.py`
- `src/auditmanager/bootstrap/hosts_dispatch.py`
- `src/auditmanager/bootstrap/stage_plan_adapter.py`
- `src/auditmanager/bootstrap/stage_plan_providers.py`
- `src/auditmanager/runs/stage_facts.py`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `infra/deploy/README.md`
- `infra/deploy/serve.py`
- `infra/deploy/apply-grants.sh`
- `scripts/recovery/**`
- `web/openapi/openapi.json`
- `web/src/shared/api/generated/**`
- `web/src/shared/api/credentialed-forward.ts`
- `web/src/shared/api/authorization.ts`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/src/entities/audit-run/model/run-queue-reason.ts`
- `web/src/entities/executor-group/model/vocabulary.ts`
- `web/src/entities/executor-group/model/wait-detail.ts`
- `web/src/entities/version-series/model/job-executor.ts`
- `web/FRONTEND_LOCK.json`
- `web/tests/**`
- `tests/support/expected_facts.json`
- `tests/contract/**`
- `tests/unit/executor_runner/_agent_support.py`
- `tests/unit/executors/test_capacity_pins.py`
- `tests/unit/decision_memory/test_status_and_settings.py`
- `tests/integration/api/test_authorization.py`
- `tests/integration/api/test_role_register.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/integration/db/test_accounts_migration.py`
- `tests/integration/db/test_application_role_grants.py`
- `tests/integration/db/test_decision_carryover_migration.py`
- `tests/integration/db/test_decision_memory_m2_migration.py`
- `tests/integration/db/test_decision_memory_migration.py`
- `tests/integration/db/test_finding_decision_origin_migration.py`
- `tests/integration/db/test_migration_lifecycle.py`
- `tests/integration/db/test_optimisation_decisions_migration.py`
- `tests/integration/db/test_schema_invariant_inventory.py`
- `tests/integration/db/test_schema_shape.py`
- `tests/integration/p02_journey/journey.py`
- `tests/integration/recovery/test_grant_classification.py`
- `tests/integration/recovery/test_product_purge.py`
- `tests/integration/recovery/test_project_erase.py`
- `tests/integration/recovery/test_project_erase_shapes.py`
- `tests/integration/recovery/test_synthetic_drill_compare.py`
- `tests/integration/recovery/test_synthetic_drill_seed.py`

## Created by this task
Not yet in the tree at the base: the migration file; `contracts/analysis/v1/model-catalogue.json` and its schema; `api/routers/executor_hosts.py`, `stage_layout.py` and `hosts_ports.py`; the four `bootstrap/` stubs; `runs/stage_facts.py`. Every stub method refuses with a typed `dependency_unavailable`; none returns an empty success (`AGENTS.md` §4, no silent fallback).

## Forbidden hotspots
- `src/auditmanager/bootstrap/providers.py`, `composition.py`, `adapters.py` and `src/auditmanager/api/routers/ports.py`: the integrator's, wired at the merge. The new port Protocols live in `hosts_ports.py`, not in `ports.py`
- `src/auditmanager/jobs/repository.py` beyond the `prepare_provider_call` signature and the two INSERT statements. After this task is merged the file belongs wholly to `HOSTS-BACKEND-01`; no other lane edits it, and BACKEND starts after the merge
- `src/auditmanager/executors/model.py` beyond the two enum mirrors (`GROUP_MEMBER_ISSUES`, `WAIT_REASONS`)
- `docs/program/CURRENT_STATE.md`, `docs/program/ALPHA_ROADMAP.md`, `VERSION`, `release-notes/**`: the integrator's, at `HOSTS-INT-1`
- `src/auditmanager/shared/errors/**`, root dependency/lock files, global styles
- implementation code of the wave-1 lanes

## Non-goals
- no behaviour: every new operation answers only through its stub or through no port
- no new error code
- no `getRunStages` (`HOSTS-SEAL-2`)
- no composition wiring

## Deliverables
- **Operations added** (11): `listExecutorHosts`, `getExecutorHost`, `setExecutorHostEnabled`, `setExecutorHostSlots`, `archiveExecutorHost`, `getExecutorHostDetails`, `getStageModelLayout`, `reviseStageModelLayout`, `setStageModelLayoutEnabled`, `listModelCatalogue`, `getRunStartReadiness`. Roles: administrator writes; expert reads the layout and the catalogue; **the viewer is closed for every new read** (`R-150w`). Writes carry an idempotency key.
- **Operations changed:** enrollment and install take a host or a connection as target; `reportRunnerHealth` carries the host report; `claimExecutorTask` accepts a host token; `startRun`, `reauditRun` and `startRunFromStage` take no executor selectors under the layout (explicit selectors answer `validation_failed`); `estimateRunCost` is by model; the consent form is v2. A consent body, for illustration: `{"cost_consent": {"estimate_digest": "<digest from getRunStartReadiness>", "ceiling_micros": 0, "confirmed": true}}`; the stage-plan digest and the map model → `rate_sha256` + access are stored by the server, not sent.
- **Enum values:** `RunQueueReason` + `model_unavailable`; `ExecutorGroupMemberIssue` + `host_disabled`, `model_not_verified`, `model_cooling_down`.
- **Migration `0062`:**
  - `executor_host` and its «Использовать» event journal (author, append-only);
  - `host_id` on `executor_runner_token`, `executor_enrollment` and `executor_agent_install`, each with a CHECK «exactly one of `connection_id` / `host_id`»;
  - `system_managed` and `capacity_pool` on the connection records, the report snapshot of a host, and `executor_model_cooldown`;
  - the stage layout, its revisions `slr_<ULID>` with author, and the enable switch with its journal;
  - `audit_run.stage_plan` and `audit_run_cell_binding (run_id, cell_key, group_revision_id, connection_revision_id)` with a write-once trigger;
  - `stage_key`, `host_id` (no foreign key) and `access` on `model_call` and `provider_call_effect`, nullable;
  - the consent v2 storage;
  - `ck_audit_run_binding_shape` with the `stage_plan` shape, `ck_audit_run_wait_pending` admitting such a `pending` run, `ck_audit_run_wait_reason` with `model_unavailable`, and `trg_audit_run_frozen_guard` (function `am_guard_audit_run_frozen`) re-created once more.
- **Catalogue:** `contracts/analysis/v1/model-catalogue.json` with `contract_version`, a schema beside it, and one entry per lock pin (provider, efforts, access kinds, `accepted_reported`); a test fails on an entry without a pin and on a pin without an entry.
- **Pins:** move EVERY literal of 1.44.0, the counts 280 / 308 / 744 and the head `0061`. Before editing, run the commands of P-01 to P-03 and treat each hit that is a pin as yours; a phrase naming where a thing was introduced stays. `docs/program/CURRENT_STATE.md` and `ALPHA_ROADMAP.md` are the integrator's: the lane reports their stale lines.
- **Inventories** (`D-213`): hand-kept table lists, grants, purge and erase registries, the account-reference register for the new author columns (`access/references.py`, `tests/integration/db/test_accounts_migration.py`), the identity-format check and the schema coverage head.
- **ADR index:** `docs/architecture/ADR_INDEX.md` keeps its ADR-0028 row (added by `HOSTS-ADR-01`); this task only corrects it if the contract numbers it names change.
- **Stubs:**
  - `executor_hosts.py` and `stage_layout.py` routers, with their Protocols in `hosts_ports.py` (`ExecutorHostPort`, `StageLayoutPort`); a router built with no port answers none, as every router does;
  - `ExecutorHostAdapter` in `hosts_adapter.py`, and `hosts_dispatch.py`, the cell-binding seam the claim calls;
  - `StageLayoutAdapter` in `stage_plan_adapter.py`, and `stage_plan_providers.py`, the resolution of a `stage_plan` run by cell;
  - `runs/stage_facts.py`, filled by `RUN-STAGES-01`.
- **Host token in the seam:** `RunnerIdentity` in `api/security.py` gains `host_id`; `connection_id` becomes optional; `RUNNER_OPERATIONS` is unchanged.
- **Call journal (minimal plumbing):** `prepare_provider_call` accepts keyword `stage_key`, `host_id` and `access` (default `None`, format-checked); `complete_provider_call` accepts the same keys in its mapping; `_INSERT_PROVIDER_EFFECT` and `_INSERT_MODEL_CALL` write them as nullable pass-through. Existing callers write `NULL`. The meaning of the values belongs to `HOSTS-LAYOUT-01` (callers) and `HOSTS-BACKEND-01` (everything else in the file).
- Models and client regenerated: `npm --prefix web run api:generate`, then `api:verify`.

## Required tests
- command: with the project's Python (`FOUNDATION_PYTHON` in the `Makefile`, the venv), `-m pytest tests/contract -q` and `-m pytest tests/unit/executors/test_capacity_pins.py -q`; then `npm --prefix web run api:verify`, `npm --prefix web run typecheck` and `npm --prefix web test -- tests/guards tests/contract`
- expected: pass, except `tests/contract/api_v1/test_doc_prose_facts.py` on the lines of `CURRENT_STATE.md` and `ALPHA_ROADMAP.md`, which the integrator moves at `HOSTS-INT-1`; the lane lists exactly which lines are red
- not run by the lane: tests that need PostgreSQL or S3. They are written with the suite's database marker and run once by the integrator on a throwaway database (`HOSTS-PLAN.md` §6)

## Integration contract
- `HOSTS-AGENT-01`, `HOSTS-BACKEND-01`, `HOSTS-LAYOUT-01` and `HOSTS-WEB-01` treat contract 1.45.0, migration `0062` and the stub names as frozen.
- **At merge the integrator wires the four hotspot files:**
  - `ports.py`: re-exports of `ExecutorHostPort` and `StageLayoutPort` if a whole-port test needs them;
  - `composition.py`: `executor_hosts=` and `stage_layout=` adapters, and the call site of the single `CallBinding` at `composition.py:932`;
  - `adapters.py`: the thin wrappers of `ExecutorEnrollmentAdapter`, `ExecutorGroupAdapter` and the runner authentication for a host token;
  - `providers.py`: the `stage_plan` branch of `DatabaseProviders` and the typed refusal in `EnvironmentProviders`.
- The integrator moves `CURRENT_STATE.md` and writes the release note at `HOSTS-INT-1`.

## Failure/idempotency/security cases
- a token, grant or install session with both or neither of `connection_id` and `host_id` is refused by the database
- a second write to a run's cell binding, or a change of `stage_plan` after the run has started, is refused by the database
- each trigger and CHECK has a test that fails without it
- no new read is open to the viewer

## Rollback / feature flag
Downgrade refuses while any host, layout revision, `stage_plan` run, cell binding or cooldown exists. Before the layout switch is turned on nothing reads the new tables, and the legacy route serves every run.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: the generation commands and the focused checks above with their result; no database, container or browser run
- known limits: the database-marked tests are unexecuted; the stale lines of `CURRENT_STATE.md`
- integration notes: the new surface triple; the stub names; what each wave-1 lane may rely on
