# Task EXEC2-SEAL-1 — contract 1.15.0 and migration 0046 for capacity, pull claims, enrollment and agent installs

## Outcome
OpenAPI 1.15.0 declares every stage-1 addition of ADR-0026 decisions 1–9. Migration `0046` creates their columns and tables. The server models and the web client are regenerated from the contract. Every literal pin of the contract version, the path and operation counts, the migration head and the table inventories names the new values. Stage-1 lanes implement against this without editing it.

## Depends on
- REVIEW-FIX-INT-1102 (dispatch only once it is on `origin/dev`)

## Frozen inputs
- domain contract: version literal 1.14.0 → 1.15.0; new identifier prefixes for the enrollment and the install session
- API contract: 1.14.0 → 1.15.0, owned by this task
- analysis/comparison/event contract: version literal 1.14.0 → 1.15.0 only
- migration head: `0045_comparison_page_bounds` (on `origin/dev` since `31c66307`); this task owns slot `0046`
- base commit: `integration/exec2` = `origin/dev` `ece9d1ef` plus the assignment commit of this task
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 1–9, 18; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json` (paths); `db/migrations/versions/**` (migrations)
- enumerator_owner: EXEC2-SEAL-1
- totality_query: `python3 -c "import json; print(len(json.load(open('contracts/api/v1/openapi.json'))['paths']))"` and `ls db/migrations/versions/*_004*.py`

## Captured premise evidence
- premise: the contract version, the path count and the migration head are literal pins in the files listed below

### P-01 — files carrying the contract version literal
- captured_at: 2026-11-02
- command: `git grep -l '1\.14\.0' origin/dev -- contracts src infra web/src tests/support tests/contract`
- captured_output:
  ```text
  origin/dev:contracts/analysis/ar_v3_beta/v1/stage.json
  origin/dev:contracts/analysis/v1/crop-manifest.schema.json
  origin/dev:contracts/analysis/v1/examples/job-package.example.json
  origin/dev:contracts/analysis/v1/examples/result-package.example.json
  origin/dev:contracts/analysis/v1/examples/result-package.missing-attempt-authority.invalid.json
  origin/dev:contracts/analysis/v1/examples/stage-result.example.json
  origin/dev:contracts/analysis/v1/examples/stage-result.failed-missing-error.invalid.json
  origin/dev:contracts/analysis/v1/examples/stage-result.succeeded-with-error.invalid.json
  origin/dev:contracts/analysis/v1/job-package.schema.json
  origin/dev:contracts/analysis/v1/legacy-stage-map.json
  origin/dev:contracts/analysis/v1/legacy-stage-map.schema.json
  origin/dev:contracts/analysis/v1/legacy-stage-name-map.json
  origin/dev:contracts/analysis/v1/legacy-stage-name-map.schema.json
  origin/dev:contracts/analysis/v1/portal-blocks.schema.json
  origin/dev:contracts/analysis/v1/result-package.schema.json
  origin/dev:contracts/analysis/v1/stage-registry.json
  origin/dev:contracts/analysis/v1/stage-registry.schema.json
  origin/dev:contracts/analysis/v1/stage-result.schema.json
  origin/dev:contracts/api/v1/openapi.json
  origin/dev:contracts/domain/v1/error-codes.json
  origin/dev:contracts/domain/v1/error-codes.schema.json
  origin/dev:contracts/domain/v1/error-envelope.schema.json
  origin/dev:contracts/domain/v1/examples/error-envelope.example.json
  origin/dev:contracts/domain/v1/examples/error-envelope.unknown-code.invalid.json
  origin/dev:contracts/domain/v1/identifiers.json
  origin/dev:contracts/domain/v1/identifiers.schema.json
  origin/dev:contracts/domain/v1/state-machines.json
  origin/dev:contracts/domain/v1/state-machines.schema.json
  origin/dev:contracts/events/v1/event-envelope.schema.json
  origin/dev:contracts/events/v1/examples/event-envelope.example.json
  origin/dev:contracts/events/v1/examples/event-envelope.legacy-schema-version.invalid.json
  origin/dev:infra/deploy/proxy/nginx.conf
  origin/dev:infra/deploy/proxy/tls-server.conf
  origin/dev:infra/norms-worker/requirements.lock
  origin/dev:src/auditmanager/analysis/engine/result.py
  origin/dev:src/auditmanager/api/routers/__init__.py
  origin/dev:src/auditmanager/api/schemas/models.py
  origin/dev:tests/contract/api_v1/test_cmp_seal_c4.py
  origin/dev:tests/contract/api_v1/test_contract_seal.py
  origin/dev:tests/support/expected_facts.json
  origin/dev:web/src/shared/api/credentialed-forward.ts
  origin/dev:web/src/shared/api/generated/client.gen.ts
  origin/dev:web/src/shared/api/generated/index.ts
  origin/dev:web/src/shared/api/generated/operations.gen.ts
  origin/dev:web/src/shared/api/generated/types.gen.ts
  exit=0
  ```
- interpretation: every file the version bump must touch; `infra/norms-worker/requirements.lock` matches only as `sympy==1.14.0` and is not a pin of this contract.

### P-02 — path-count pins
- captured_at: 2026-11-02
- command: `git grep -nE '== 233|"path_count": 233|233 paths' origin/dev -- tests src infra web/src`
- captured_output:
  ```text
  origin/dev:infra/deploy/proxy/nginx.conf:301:    # contract declares the 233 paths, while its `_SERVERS` comment says those paths
  origin/dev:src/auditmanager/api/app.py:87:#: ``include_in_schema=False`` -- because the contract declares 233 paths and these are
  origin/dev:src/auditmanager/api/app.py:374:    ``include_in_schema=False`` on all four. The contract declares 233 paths and
  origin/dev:tests/contract/api_v1/test_cmp_seal_c4.py:30:    assert len(doc["paths"]) == 233
  origin/dev:tests/support/expected_facts.json:4:    "path_count": 233,
  origin/dev:web/src/app/bff/v1/[...path]/route.ts:22: * Those figures are **259 operations across 233 paths**, which is what the
  exit=0
  ```
- interpretation: the 233-path figure is pinned in a test, the expected facts, two comments of the composition root, the proxy comment and the BFF comment.

### P-03 — the migration head this task builds on
- captured_at: 2026-11-02
- command: `git ls-tree --name-only origin/dev db/migrations/versions/ | grep -E '_004[45]_'`
- captured_output:
  ```text
  db/migrations/versions/20261030_0044_section_stats_uncapped.py
  db/migrations/versions/20261102_0045_comparison_page_bounds.py
  exit=0
  ```
- interpretation: the head is 0045; 0046 is the next free slot.

### P-04 — the operation-to-principal map
- captured_at: 2026-11-02
- command: `git grep -n '"setExecutorRoute": _ADMIN\|"claimExecutorTask", "extendExecutorTaskClaim"' origin/dev -- src/auditmanager/api/security.py`
- captured_output:
  ```text
  origin/dev:src/auditmanager/api/security.py:262:    "claimExecutorTask", "extendExecutorTaskClaim", "submitExecutorTaskAnswer",
  origin/dev:src/auditmanager/api/security.py:643:        "setExecutorRoute": _ADMIN,
  exit=0
  ```
- interpretation: every operation is mapped by name in `api/security.py`: new administrator operations join the administrator map, and new runner operations join the runner set.

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
- `web/FRONTEND_LOCK.json`
- `web/tests/**`
- `web/src/shared/api/authorization.ts`
- `tests/contract/domain_p02/test_openapi_document.py`
- `tests/integration/api/test_authorization.py`
- `tests/integration/api/test_role_register.py`
- `tests/integration/recovery/test_grant_classification.py`
- `tests/integration/recovery/test_synthetic_drill_compare.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `infra/deploy/README.md`
- `infra/deploy/serve.py`
- `src/auditmanager/api/README.md`
- `src/auditmanager/api/health.py`
- `src/auditmanager/api/routers/errors.py`
- `src/auditmanager/api/routers/declarations.py`
- `src/auditmanager/executors/model.py`
- `db/migrations/versions/20261102_0046_executor_capacity_enrollment.py`
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
- implementation code of the stage-1 lanes (`jobs/`, `comparison/`, `executors/` other than `model.py`, `tools/`, `web/src` other than the generated client and the two pinned files)
- `src/auditmanager/shared/errors/**`
- root dependency/lock files, global styles

## Non-goals
- no behaviour: handlers, claim logic, the installer and the UI belong to the stage-1 lanes
- no group or rule schema (stage 2, `EXEC2-SEAL-2`)

## Deliverables
- The migration file name carries the dispatch date `20261102`.
- OpenAPI 1.15.0 adds:
  - `max_active_runs` (integer 1–16, default 1) in the revision settings of every kind;
  - `occupancy` (`capacity`, `active_runs`, `active_calls`) on the connection read models;
  - `queue_reason` (`executor_at_capacity`, `runner_offline` or null) on the Run read models;
  - the optional `runner_instance_id` (`^[A-Za-z0-9_-]{8,64}$`) in the `claimExecutorTask` body;
  - `POST /executor-connections/{connection_id}/enrollments` (administrator, idempotency key). The secret, the package version and sha256, and the copyable command are shown once.
  - `POST /runner/enroll` (enrollment secret as bearer; returns a runner token once)
  - `POST /runner/health` (runner token; sanitised enumerations only)
  - `GET /runner/agent-package/{version}` (no authentication; `application/gzip`)
  - `POST /executor-connections/{connection_id}/agent-installs`, `GET …/agent-installs/{install_id}` and `POST …/agent-installs/{install_id}/confirm-host-key` (administrator)
  - `POST /executor-connections/{connection_id}/integration-authorisation` (administrator; the R-149b mark)
  - the health fields on `RunnerTokenMetadata`;
  - typed refusal details (`constraint`/`conflict_reason`/`dependency` values) on the existing codes only.
- Version literal 1.15.0 in every file of premise P-01. The path and operation counts move in every file of P-02 to the figures the new contract actually has.
- Migration revision id `0046_executor_capacity_enroll` (`alembic_version.version_num` is `varchar(32)`, so the 33-character `0046_executor_capacity_enrollment` cannot be stored); the file keeps the longer name:
  - nullable `executor_connection_revision.max_active_runs` (1–16; NULL reads as 1);
  - `executor_task.claimed_by_instance_id`;
  - the health columns on `executor_runner_token`;
  - tables `executor_enrollment` and `executor_agent_install` with ID checks and immutability where ADR-0026 says so;
  - `agent_install_key` added to the secret purposes;
  - the integration-authorisation columns on `executor_connection`;
  - a downgrade that refuses when it would drop data in use.
- `executors/model.py`: the vocabulary only (purposes, settings fields, new kinds of refusal detail); no behaviour.
- New operations mapped in `api/security.py`: administrator ones to the administrator map, runner ones to the runner set, the enroll exchange and the package to their own principal kinds as stubs the ENROLL lane fills.
- The `D-213` inventories in the allowed paths name the new tables and columns; both new tables start in `SEALED_NOT_YET_WRITTEN`.
- `web/tests/**` and `web/FRONTEND_LOCK.json`: only the contract-version literal, the surface counts and the generated-file hashes move; no test logic changes.
- `ExecutorConnectionDetail.enrollments`: the connection's enrollment metadata (state, expiry, redemption; never a secret) so a reloaded wizard can show «ожидает регистрации».
- Server models and web client regenerated with the repository's generators.

## Required tests
- command: not run in EXEC-2 (`R-149d`); write the tests below and mark those that need PostgreSQL with the suite's existing database marker
- expected: `tests/contract` pins move with the facts; no new behaviour test belongs here

## Integration contract
- stage-1 lanes treat the 1.15.0 contract, the generated client and migration 0046 as frozen
- a missing or wrong contract element is reported to the integrator, who amends this task's output on `integration/exec2`; lanes never edit it

## Failure/idempotency/security cases
- the enrollment secret and the runner token appear in no event, log line, error detail or read model after their single display
- the package route serves only versions built into the image; an unknown version is a typed refusal, not a directory listing

## Rollback / feature flag
Additive. A downgrade of 0046 refuses while enrollments, installs or capacities above one exist. Reverting the merge restores 1.14.0.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
