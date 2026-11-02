# Task EXEC2-SEAL-2 — contract 1.16.0 and migrations 0047–0048 for groups, rules, routing mode and write-once binding

## Outcome
OpenAPI 1.16.0 declares the stage-2 and stage-3 additions of ADR-0026 decisions 10–17. Migration `0047` creates the group, rule and routing-mode tables. Migration `0048` adds `binding_state`, `wait_reason` and `waiting_since`, and re-creates the frozen-column triggers of `audit_run` and `comparison_ai_job` with the single NULL → value exception. Models, client, pins and inventories follow.

## Depends on
- EXEC2-INT-1

## Frozen inputs
- domain contract: version literal 1.15.0 → 1.16.0; new identifier prefixes for groups, group revisions and rule revisions; state machines gain `binding_state`
- API contract: 1.15.0 → 1.16.0, owned by this task
- analysis/comparison/event contract: version literal 1.15.0 → 1.16.0 only
- migration head: `0046`; this task owns slots `0047` and `0048`
- base commit: `integration/exec2` after `EXEC2-INT-1` is on `origin/dev`
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 10–18; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json` (paths); `db/migrations/versions/**` (migrations)
- enumerator_owner: EXEC2-SEAL-2
- totality_query: `python3 -c "import json; print(len(json.load(open('contracts/api/v1/openapi.json'))['paths']))"` and `ls db/migrations/versions/*_004*.py`

## Captured premise evidence
- premise: the frozen-column guards forbid any change of a frozen revision, and comparison consent pins the revision at consent

### P-01 — the guards to re-create
- captured_at: 2026-11-02
- command: `git grep -nE 'CREATE TRIGGER trg_audit_run_frozen_guard|CREATE FUNCTION am_guard_comparison_ai_job_consent|connection_revision_id +text NOT NULL' origin/dev -- db/migrations/versions`
- captured_output:
  ```text
  origin/dev:db/migrations/versions/20260910_0002_pc01_schema.py:1289:        CREATE TRIGGER trg_audit_run_frozen_guard
  origin/dev:db/migrations/versions/20261009_0017_execution_queue.py:35:        "CREATE TRIGGER trg_audit_run_frozen_guard BEFORE UPDATE ON audit_run "
  origin/dev:db/migrations/versions/20261016_0023_norm_citations.py:126:        "CREATE TRIGGER trg_audit_run_frozen_guard BEFORE UPDATE ON audit_run "
  origin/dev:db/migrations/versions/20261022_0030_executor_connections.py:92:        "CREATE TRIGGER trg_audit_run_frozen_guard BEFORE UPDATE ON audit_run "
  origin/dev:db/migrations/versions/20261027_0037_analysis_presets.py:98:        "CREATE TRIGGER trg_audit_run_frozen_guard BEFORE UPDATE ON audit_run "
  origin/dev:db/migrations/versions/20261029_0040_comparison_ai_reports.py:295:        CREATE FUNCTION am_guard_comparison_ai_job_consent() RETURNS trigger
  origin/dev:db/migrations/versions/20261029_0040_comparison_ai_reports.py:602:            connection_revision_id    text NOT NULL,
  exit=0
  ```
- interpretation: `trg_audit_run_frozen_guard` is re-created by five migrations, and `am_guard_comparison_ai_job_consent` with `connection_revision_id NOT NULL` lives in 0040; 0048 re-creates both with the write-once exception.

### P-02 — the name «group» is taken
- captured_at: 2026-11-02
- command: `git grep -n 'CREATE TABLE ar_v3_run_group' origin/dev -- db/migrations/versions`
- captured_output:
  ```text
  origin/dev:db/migrations/versions/20261023_0032_ar_v3_run_group.py:24:        CREATE TABLE ar_v3_run_group (
  origin/dev:db/migrations/versions/20261023_0032_ar_v3_run_group.py:44:        CREATE TABLE ar_v3_run_group_member (
  exit=0
  ```
- interpretation: the new tables are `executor_group*`, never `*_run_group`.

The integrator re-runs every premise command on the actual base before dispatch (`EXEC2-PLAN.md` section 6) and corrects line numbers; a premise that no longer holds stops the dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `contracts/**`
- `src/auditmanager/api/schemas/models.py`
- `src/auditmanager/api/routers/__init__.py`
- `src/auditmanager/analysis/engine/result.py`
- `src/auditmanager/api/security.py`
- `src/auditmanager/api/app.py`
- `src/auditmanager/shared/identity/**`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `web/src/shared/api/generated/**`
- `web/openapi/openapi.json`
- `web/src/shared/api/credentialed-forward.ts`
- `web/src/app/bff/v1/[...path]/route.ts`
- `tests/support/expected_facts.json`
- `tests/contract/api_v1/test_cmp_seal_c4.py`
- `tests/contract/api_v1/test_contract_seal.py`
- `src/auditmanager/executors/model.py`
- `db/migrations/versions/20261104_0047_executor_groups_rules.py`
- `db/migrations/versions/20261104_0048_dispatch_time_binding.py`
- `infra/deploy/apply-grants.sh`
- `scripts/recovery/grant_classification.py`
- `scripts/recovery/product_purge.py`
- `scripts/recovery/schema_coverage.py`
- `tests/integration/db/test_migration_lifecycle.py`
- `tests/integration/db/test_schema_invariant_inventory.py`
- `tests/integration/p02_journey/journey.py`
- `tests/integration/recovery/test_product_purge.py`
- `tests/integration/recovery/test_project_erase_shapes.py`

## Forbidden hotspots
- implementation code of the stage-2 and stage-3 lanes
- `src/auditmanager/shared/errors/**`
- root dependency/lock files, global styles

## Non-goals
- no behaviour
- no group-targeting presets

## Deliverables
- The date prefixes are the dispatch date, as in SEAL-1.
- OpenAPI 1.16.0 adds:
  - `GET/POST /executor-groups`
  - `GET /executor-groups/{group_id}`
  - `POST /executor-groups/{group_id}/revisions`
  - `POST /executor-groups/{group_id}/archive`
  - `GET /executor-groups/{group_id}/capacity`
  - `GET /executor-routing-rules`
  - `PUT /executor-routing-rules/{work_kind}` (administrator, idempotency key)
  - `GET /executor-routing/preview`
  - `POST /executor-routing/mode` (cut-over and rollback with a confirmed mapping)
  - `executor_group_id` on `startRun` and `estimateRunCost`, mutually exclusive with `executor_connection_id` and `preset_id`;
  - group, rule and planned-model fields on the comparison estimates and consents;
  - `binding_state`, the planned and the bound model and connection, `wait_reason` and `waiting_since` on the Run and comparison-job read models.
- Migration `0047`: the tables of decisions 10 and 11 plus the routing mode, with ID checks, uniqueness, immutability triggers and no hard delete of a referenced revision.
- Migration `0048`:
  - `binding_state` on `audit_run` and `comparison_ai_job`; every existing row becomes `frozen_at_start`;
  - `comparison_ai_job.connection_revision_id` becomes nullable, with a CHECK tying NULL to `pending`;
  - rule and group revision references;
  - `wait_reason` and `waiting_since`;
  - both guards re-created with the exception of decision 12.
- Pins and the `D-213` inventories as in SEAL-1. Models and client regenerated.

## Required tests
- command: not run in EXEC-2 (`R-149d`); write the tests below and mark those that need PostgreSQL with the suite's existing database marker
- expected: `tests/contract` pins move with the facts

## Integration contract
- stage-2 `EXEC2-GROUP-STORE-01` and all stage-3 lanes treat 1.16.0, 0047 and 0048 as frozen

## Failure/idempotency/security cases
- a second NULL → value write, or a value → value write, is refused by the database
- an existing Run or comparison job is never `pending` after the upgrade

## Rollback / feature flag
Downgrade refuses while any `pending` or `bound` row or any group exists. Before cut-over nothing reads the new tables.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
