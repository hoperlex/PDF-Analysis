# Task CFB-INT-DEV-PUBLISH-23 — integrate W57A storage seal

task_id: CFB-INT-DEV-PUBLISH-23

## Outcome

A clean fast-forward `origin/dev` candidate carries the reviewed W57A
`0023_norm_citations` storage/custody seal, its domain mirrors and focused
real-PostgreSQL evidence. No W57A served route, CITE stage or qualified
normative corpus is claimed.

## Depends on

- `CFB-INT-DEV-PUBLISH-22` — completed at `c3527fd969c4512441971d9a1f6e2c68a52b9a13`;
- `W57A-SEAL-01A` — completed at `c71048f788e5d0bee39a312217dfd4c0912e5bc1`.

## Frozen inputs

- integration base and directly read `origin/dev`:
  `c3527fd969c4512441971d9a1f6e2c68a52b9a13`;
- source base `c157ee0d4601f2bf81c68708ebf556b95b87acd5` is an
  ancestor of dev22; source commit is `c71048f788e5d0bee39a312217dfd4c0912e5bc1`;
- directly read `origin/main`: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- frozen API/identifier/error/stage SHA-256 before source:
  `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`,
  `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`,
  `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`,
  `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315b2c1239453ba3a`;
- P02 model lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- source lane passed 49 focused real-PostgreSQL tests and 176
  contract/offline tests, then stopped its isolated containers;
- R-135 defers the complete beta gate; separate W55b main candidate has no
  successful complete gate yet.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `contracts/domain/v1/identifiers.json`
- enumerator_owner: `W57A-SEAL-01A`
- totality_query: `python3 tools/plan/pin_sweep.py reseal-surface migration table error-code route`

The completed source owner alone changed the six domain contract artifacts,
identity/custody mirrors and migration 0023. This integration cherry-picks
that exact payload without editing it. W57A 01B owns the subsequent API and
stage reseal serially.

## Captured premise evidence

- premise: the source is one complete 31-path commit on an ancestor of the
  published development tree, and post-base dev changes have no source-path
  overlap.

### P-01 — source lineage and frozen base

- captured_at: 2026-10-16
- command: `git log -1 --format='%H %s' c71048f7; sha256sum contracts/api/v1/openapi.json contracts/domain/v1/identifiers.json contracts/analysis/v1/stage-registry.json contracts/domain/v1/error-codes.json docs/program/P02_LOCK.json`
- captured_output:
  ```text
  c71048f788e5d0bee39a312217dfd4c0912e5bc1 W57A seal verified retrieval set and citation partition storage
  fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227  contracts/api/v1/openapi.json
  c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50  contracts/domain/v1/identifiers.json
  bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315b2c1239453ba3a  contracts/analysis/v1/stage-registry.json
  89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace  contracts/domain/v1/error-codes.json
  2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd  docs/program/P02_LOCK.json
  ```
- interpretation: integrate the source as-is; review the contract reseal
  and exact changed paths before publishing. The real DB result belongs to
  the unchanged source payload.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/CFB-INT-DEV-PUBLISH-23.md`
- `docs/program/CFB-INT-DEV-PUBLISH-23.md`
- `docs/program/CURRENT_STATE.md`
- `contracts/domain/v1/error-codes.json`
- `contracts/domain/v1/error-codes.schema.json`
- `contracts/domain/v1/identifiers.json`
- `contracts/domain/v1/identifiers.schema.json`
- `contracts/domain/v1/state-machines.json`
- `contracts/domain/v1/state-machines.schema.json`
- `db/migrations/versions/20261016_0023_norm_citations.py`
- `docs/program/NORM_CORPUS_CUSTODY.md`
- `docs/program/P02_SEAMS.md`
- `docs/program/W57A-SEAL-01A.md`
- `docs/program/tasks/W57A-SEAL-01A.md`
- `src/auditmanager/norms/custody/__init__.py`
- `src/auditmanager/norms/custody/roles.py`
- `src/auditmanager/norms/public.py`
- `src/auditmanager/shared/identity/__init__.py`
- `src/auditmanager/shared/identity/ids.py`
- `tests/integration/db/test_accounts_migration.py`
- `tests/integration/db/test_execution_workers_migration.py`
- `tests/integration/db/test_findings_v2_migration.py`
- `tests/integration/db/test_fixture_template.py`
- `tests/integration/db/test_migration_lifecycle.py`
- `tests/integration/db/test_norm_citations_migration.py`
- `tests/integration/db/test_norm_custody_migration.py`
- `tests/integration/db/test_norms_search_migration.py`
- `tests/integration/db/test_portal_bundles_migration.py`
- `tests/integration/db/test_release_notes_migration.py`
- `tests/integration/db/test_schema_invariant_inventory.py`
- `tests/integration/db/test_schema_shape.py`
- `tests/integration/jobs/test_recorded_v2_publication_gate.py`
- `tests/integration/norms/custody/test_custody_offline.py`
- `tests/support/expected_facts.json`

## Forbidden hotspots

Old migrations, migration 0024, API contracts and generated client, stage
registry, W56 executor/composition root, root dependencies/locks, global
styles, production DB/S3, `origin/main`, tags and deployment workflow.

## Non-goals

No W57A 01B API/stage/runtime reseal, served CITE or reader, corpus
qualification, external provider, W57b export, W55b deployment or beta
acceptance. No historical 0022 migration edit.

## Deliverables

Exact source payload, bounded current-state update, this task/report and
direct read-back of the published dev SHA.

## Required tests

- integrated container-free W57 domain/custody tests and programme
  governance; source 49/49 real-service result covers unchanged 0023 payload;
- contract-reseal and migration-head readback, exact path, whitespace,
  clean-tree, fresh remote fast-forward and post-push read-back;
- complete beta `make gate` deferred by R-135; W55b's gate is separate.

## Integration contract

Only this task may publish its exact checked SHA to `origin/dev`. Cherry-pick
the completed source commit without payload edits. A verified `nrs_` set
requires matching expected/observed digests, nonempty complete chunk/vector
build and both confirmed custody bindings. A Run pin is frozen. A non-NULL
citation count denotes a certified 0..5 partition checked at commit; NULL
remains legacy/unsealed. Later 01B readers must refuse absent or mismatched
state and must not infer zero from an empty SELECT. A moved remote ref or
changed source stops publication; never force-push.

## Failure/idempotency/security cases

The source DB checks covered missing binding, incomplete build, rejected
pin, mismatched partition and populated-downgrade refusal. No corpus object,
credential or DB volume enters Git. Retry reads remote and no-ops if equal.

## Rollback / feature flag

No served behavior is activated. `0023` refuses downgrade with retained
data. Corrections use reviewed forward commits and an appropriate backup,
not an unsafe populated downgrade.

## Handoff

- integration files: this task, its report and bounded state update;
- source files: the exact 31-path 01A commit;
- new contracts: domain revision 14 and migration head 0023; API/stage unchanged;
- next: serial W57A 01B API/stage/reader seal; `origin/main` untouched.
