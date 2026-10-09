# W53-SEAL-01 handoff

- Branch: `agent/w53-seal-01`.
- Dispatch base: `2e458ca9b1867d7dd360a2314b4bf55d848e4aed`.
- Custody repair grant: `be7374c2bb132a295eacac82764f3818ea0291c5` (`W53-SEAL-GRANT-01`); the completed `tasks/NORM-CUSTODY-01.md` record remains unchanged.
- HEAD: record from the handoff commit; this report is part of that commit.

## 1. Changed files

The exact path list follows at the end of this report. Every path is in the SEAL task's allowed paths, including the one addendum path supplied by the repair grant.

## 2. Checks and results

- `python3 tools/plan/pin_sweep.py reseal-surface migration route --check docs/program/tasks/W53-SEAL-01.md`: passed. Hits were reviewed as current pins, historical prose, or unrelated patterns; the affected current assertions were resealed.
- Python API conformance, role register, and operation surface: 114 passed.
- P02 seam register and live prose mutation guards: 53 passed after adding the six operations and four keyed writes to the register.
- Migration 0017 upgrade/downgrade, fresh schema invariant inventory and shape: 12 passed on the disposable `gate-w53seal` PostgreSQL service. A populated 0016 database with a queued run lacking a Job and an unreleased lease upgrades; retained execution data refuses downgrade. Existing Job writers receive a 60-second lease expiry default.
- Existing durable effect boundary tests: 18 passed on fresh 0017 database; new migration tests: 3 passed; operation surface plus durable analysis effect tests: 15 passed.
- `npm --prefix web run api:verify`: passed; web typecheck and lint passed; web contract: 127 passed; web guards: 263 passed.
- `git diff --check`: passed.
- A broad `tests/contract` diagnostic run was red (77 failed, 684 passed, 126 errors). The CP00 candidate harness assumes `.git` is a directory and raises `NotADirectoryError` in a linked worktree; the other failures included four W53 register/prose assertions, now fixed and retested, plus pre-existing CP00 publication evidence and missing `jsonschema` in this lane's bootstrap subprocess. The narrowed rerun log is `/tmp/w53seal-contract-no-cp00.log` (36 failed, 541 passed, 64 subtests), retained for the integrator. This broad run is not an acceptance gate for this task.

## 3. Contracts and migration

- OpenAPI: 36 paths, 43 operations, 91 schemas; SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`. Six execution operations are declared, role-gated and wired to explicit `dependency_unavailable` stubs. `RunStatus.reaudit_of_run_id` is optional and absent for an ordinary run.
- Domain state-machine revision remains 9: the additions are explanatory notes about existing execution states, with no new transition or guard in the catalog.
- Alembic head is `0017_execution_queue`. It adds queue scheduling and lease timing columns, execution control, re-audit linkage and provider effect states; backfills queued runs without Jobs; enforces id shapes and safe downgrade refusal.
- R-76 custody design has a new addendum and ADR note. No custody runtime behavior was changed.

## 4. Risks and limitations

- The six operations are port stubs until Stage B supplies execution behavior. They fail explicitly with `dependency_unavailable`.
- Migration 0017 is intentionally not reversible once execution data is retained.
- The historical CP00 contract tests require a regular checkout and published checkpoint evidence; they are unsuitable as this lane's linked-worktree acceptance signal.
- No live stand, backup, MinIO image, release note or version changes were made.

## 5. Integrator instructions

Merge this branch first, then integrate the independent MINIO lane according to the freeze. Backup implementation remains deferred to a separate beta wave under the owner decision. On the integrated exact SHA, rerun the API/DB tests and full gate after the other lanes and independent QA. The 0017 database head and 36/43/91 surface are the Stage B input. The Stage B owner should replace the port stubs without changing this wire contract and preserve the migration's 60-second default compatibility until the Job writer passes explicit lease timing.

## 6. Allowed path and forbidden hotspot proof

The path audit is against the exact dispatch base and the single custody addendum grant. Existing migration files, root dependencies/locks, error catalog, identifier catalog, MINIO/backup paths, Job/Run/analysis implementations, `VERSION`, release notes, global styles, refs and tags were untouched. `docs/program/tasks/NORM-CUSTODY-01.md` is bytewise unchanged. The worktree's temporary `.venv` and `web/node_modules` symlinks are removed before commit and excluded from this list.

### Exact changed paths
- `contracts/api/v1/openapi.json`
- `contracts/domain/v1/state-machines.json`
- `db/migrations/versions/20261009_0017_execution_queue.py`
- `docs/architecture/adr/ADR-0020-normative-corpus-alpha-runtime.md`
- `docs/manual-tests/PC-01_prototype.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/NORM-CUSTODY-W53-ADDENDUM.md`
- `docs/program/NORM_CORPUS_CUSTODY.md`
- `docs/program/NORM_CORPUS_DECISION_BACKLOG.md`
- `docs/program/P02_SEAMS.md`
- `docs/program/W53-SEAL-01.md`
- `infra/deploy/README.md`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/serve.py`
- `src/auditmanager/api/README.md`
- `src/auditmanager/api/app.py`
- `src/auditmanager/api/health.py`
- `src/auditmanager/api/routers/__init__.py`
- `src/auditmanager/api/routers/declarations.py`
- `src/auditmanager/api/routers/errors.py`
- `src/auditmanager/api/routers/execution.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/api/schemas/models.py`
- `src/auditmanager/api/schemas/runs.py`
- `src/auditmanager/api/security.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `tests/contract/api_v1/test_openapi_conformance.py`
- `tests/contract/api_v1/test_surface_counts_in_prose.py`
- `tests/contract/domain_p02/test_openapi_document.py`
- `tests/integration/api/test_operation_surface.py`
- `tests/integration/api/test_role_register.py`
- `tests/integration/db/test_accounts_migration.py`
- `tests/integration/db/test_downgrade_never_loses_a_measurement.py`
- `tests/integration/db/test_durable_analysis_effects.py`
- `tests/integration/db/test_execution_queue_migration.py`
- `tests/integration/db/test_fixture_template.py`
- `tests/integration/db/test_migration_lifecycle.py`
- `tests/integration/db/test_release_notes_migration.py`
- `tests/integration/db/test_schema_invariant_inventory.py`
- `tests/integration/db/test_schema_shape.py`
- `tests/support/expected_facts.json`
- `web/FRONTEND_LOCK.json`
- `web/openapi/openapi.json`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/src/shared/api/authorization.ts`
- `web/src/shared/api/generated/client.gen.ts`
- `web/src/shared/api/generated/index.ts`
- `web/src/shared/api/generated/operations.gen.ts`
- `web/src/shared/api/generated/types.gen.ts`
- `web/tests/contract/seam-operations.contract.test.ts`
