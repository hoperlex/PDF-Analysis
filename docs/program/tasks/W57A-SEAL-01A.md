# Task W57A-SEAL-01A — storage, custody and certified citation partition

task_id: W57A-SEAL-01A

## Outcome

Migration `0023_norm_citations` adds a retrieval-set identity, two checked custody
roles, a frozen Run pin, and an append-only citation partition whose recorded
count is checked at commit. Existing v1/v2 rows upgrade without invented
citations. This is the storage portion of the sole-owner W57A seal; API and
runtime activation follow only after this step is integrated and reviewed.

## Depends on

- `CFB-INT-DEV-PUBLISH-18` — complete at `c157ee0d4601f2bf81c68708ebf556b95b87acd5`.
- `W57A-INT-RULE-FREEZE-01` — complete at `33a4d45647adea7e4f94f2fa0b94f75737eb89b5`.
- `W57A-INT-CITATION-PREP-01` — complete pure grounding preparation.

## Frozen inputs

- base: `c157ee0d4601f2bf81c68708ebf556b95b87acd5`;
- migration head: `0022_findings_v2`; 0023–0024 absent;
- API 47 paths / 54 operations / 124 schemas, SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- identifiers SHA-256 `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- stage registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- error catalogue SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- P02 model lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- governing rules: W57 plan Part A, R-76, R-80, R-135, W57A-INT-RULE-FREEZE-01.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `contracts/domain/v1/identifiers.json`
- enumerator_owner: `W57A-SEAL-01A`
- totality_query: `python3 tools/plan/pin_sweep.py reseal-surface migration table error-code route`

This owner alone writes the 0023 migration, `nrs_` identity and custody roles.
No other lane writes these shared hotspots before integration. The API/stage
reseal remains the subsequent W57A-SEAL-01B owner, not a concurrent writer.

## Captured premise evidence

- premise: the exact base has 0022 as the only successor slot and the frozen
  files match the source report.

### P-01 — base, migration and frozen bytes

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; git ls-tree -r --name-only HEAD db/migrations/versions | tail -5; sha256sum contracts/api/v1/openapi.json contracts/domain/v1/identifiers.json contracts/analysis/v1/stage-registry.json contracts/domain/v1/error-codes.json docs/program/P02_LOCK.json`
- captured_output:
  ```text
  c157ee0d4601f2bf81c68708ebf556b95b87acd5
  db/migrations/versions/20261012_0018_norm_custody.py
  db/migrations/versions/20261012_0019_execution_workers.py
  db/migrations/versions/20261012_0020_norms_search.py
  db/migrations/versions/20261013_0021_portal_bundles.py
  db/migrations/versions/20261015_0022_findings_v2.py
  fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227  contracts/api/v1/openapi.json
  c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50  contracts/domain/v1/identifiers.json
  bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a  contracts/analysis/v1/stage-registry.json
  89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace  contracts/domain/v1/error-codes.json
  2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd  docs/program/P02_LOCK.json
  ```
- interpretation: 0023 is available on this exact base; no runtime corpus qualification follows from it.

### P-02 — direct consumer inventory

- captured_at: 2026-10-16
- command: `python3 tools/plan/pin_sweep.py reseal-surface migration table error-code route | sha256sum`
- captured_output:
  ```text
  5412fa5a43a348c22cdaa9b99395d9ad2555d3c22210ffe680f37d1647f3ae47  -
  ```
- interpretation: the 124-path output is a review inventory; the explicit grants below control writes.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W57A-SEAL-01A.md`
- `docs/program/W57A-SEAL-01A.md`
- `.env` (ignored, private instance configuration only)
- `db/migrations/versions/20261016_0023_norm_citations.py`
- `contracts/domain/v1/identifiers.json`
- `contracts/domain/v1/identifiers.schema.json`
- `contracts/domain/v1/state-machines.json`
- `contracts/domain/v1/state-machines.schema.json`
- `contracts/domain/v1/error-codes.json`
- `contracts/domain/v1/error-codes.schema.json`
- `src/auditmanager/shared/identity/ids.py`
- `src/auditmanager/shared/identity/__init__.py`
- `src/auditmanager/norms/custody/roles.py`
- `src/auditmanager/norms/custody/__init__.py`
- `src/auditmanager/norms/public.py`
- `tests/integration/db/test_norm_citations_migration.py`
- `tests/integration/db/test_migration_lifecycle.py`
- `tests/integration/db/test_schema_shape.py`
- `tests/integration/db/test_schema_invariant_inventory.py`
- `tests/integration/db/test_open_items_migration.py`
- `tests/integration/db/test_accounts_migration.py`
- `tests/integration/db/test_release_notes_migration.py`
- `tests/integration/db/test_execution_workers_migration.py`
- `tests/integration/db/test_norms_search_migration.py`
- `tests/integration/db/test_fixture_template.py`
- `tests/integration/db/test_portal_bundles_migration.py`
- `tests/integration/db/test_findings_v2_migration.py`
- `tests/integration/db/test_norm_custody_migration.py`
- `tests/integration/jobs/test_recorded_v2_publication_gate.py`
- `tests/integration/norms/custody/test_custody_offline.py`
- `tests/integration/norms/custody/test_two_phase_custody.py`
- `tests/support/expected_facts.json`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `docs/program/NORM_CORPUS_CUSTODY.md`
- `docs/program/P02_SEAMS.md`

## Lane resources

- foundation_instance: `auditmanager-w57a-seal-01a`
- postgres_port: `57471`
- s3_api_port: `61072`
- s3_console_port: `61073`
- postgres_db: `auditmanager_w57a_seal_01a`
- s3_bucket: `auditmanager-w57a-seal-01a`

The DB/S3 lane starts only after the integrator releases the W55b gate lane.

## Forbidden hotspots

- old migrations, migration 0024 and all W56 executor paths;
- API contracts, generated client, API composition root and global styles;
- root dependency and lock files, `P02_LOCK.json`, error-code semantics;
- `CURRENT_STATE.md`, remote refs, release tags and live stand.

## Non-goals

No qualified set, approved map, runtime CITE stage, served API route, real
provider call, model pin, corpus publication, W57b export or beta acceptance.

## Deliverables

Forward-only 0023 schema, direct identity/role mirrors, populated 0022 upgrade
and constraint tests, focused result report. The subsequent 01B task owns the
API/stage reseal and any application publishing path.

## Required tests

- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/contract/domain_p02 tests/integration/norms/custody/test_custody_offline.py`;
- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/db/test_norm_citations_migration.py tests/integration/db/test_migration_lifecycle.py tests/integration/db/test_schema_shape.py` on the isolated DB lane;
- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/db/test_schema_invariant_inventory.py` after reviewing the fresh 0023 catalogue delta;
- `python3 tools/plan/pin_sweep.py reseal-surface migration table error-code route`
  as an advisory whole-wave inventory, then compare `git diff --name-only`
  with this task's exact grants. The whole-wave `--check` applies only after
  the serial 01B API/stage reseal grants its remaining consumers;
- `git diff --check` and governance findings `[]`.

## Integration contract

The new `nrs_` row cannot become verified without exact expected/observed
digests, a nonempty chunk/vector build whose declared counts match stored
rows, and both confirmed Blob custody bindings. The Run pin is immutable.
Published v3 observations require an explicit 0–5 citation count, and a
deferred count check validates the immutable relation on commit. Legacy rows
keep NULL and no invented citation. 01B must consume only those certified
partitions and refuse absent or mismatched state; it must not infer zero from
an empty SELECT result.

## Failure/idempotency/security cases

Rejected sets cannot pin; duplicate verified identity refuses. Missing one
binding, wrong Blob, wrong snapshot/paragraph/observation or citation count
refuses transactionally. Upgrade leaves existing rows untouched. Populated
downgrade refuses. No SQL/S3 operation is added to a router.

## Rollback / feature flag

No runtime feature is activated. Empty 0023 may downgrade; retained set,
citation or run pin data refuses downgrade. Restore from backup instead.

## Handoff

- changed files: recorded in `W57A-SEAL-01A.md`;
- commands/results: recorded there;
- known limits: API/runtime and qualified corpus remain separate;
- integration notes: cherry-pick exact commit only after focused checks.
