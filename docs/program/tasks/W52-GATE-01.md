# Task W52-GATE-01 — finish serial gate fixture preparation

task_id: W52-GATE-01

## Outcome

The remaining W52 §3.7 fixture changes remove repeated migrations in the
database integration suite and isolate storage and authentication tests
without changing product behavior. The lane returns a checked branch and
report for integrator acceptance; timing and JUnit outcome parity remain
release-validation obligations under D-140.

## Depends on

- `W52-FREEZE-01`, complete when its exact docs-only SHA is read back on
  `origin/dev`. Start from that SHA, not from the pre-freeze `3ab4097` base.

## Frozen inputs

- W52 Stage-A freeze report and read-back SHA; domain candidate revision 9 /
  29 identities, API 27 paths / 34 operations / 77 schemas, error catalog
  23, migration head `0015_accounts_roles_registration`.
- R-70, R-74 and the W52 code-first full-gate exception. D-137–D-140 remain
  open. `W52-INT-GATE-PARTITION-01` already removed duplicate foundation
  collection from the battery; `W52-INT-GATE-PC01-ENV-01` already restored
  provider mode after each PC-01 test. Neither slice is reimplemented.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the remaining `migrated_database` fixture invokes the literal
  migration command for every test, and both `bucket_keys` fixtures enumerate
  the whole shared bucket.

### P-01 — current fixture sites on the ruled base

- captured_at: 2026-10-08
- command: `git grep -n -E 'def migrated_database|def bucket_keys' 3ab4097c8014ff70f5187882a188d0ef3f955f33 -- tests/integration/db/conftest.py tests/integration/storage/conftest.py tests/integration/ingest/conftest.py`
- captured_output:
  ```text
  3ab4097c8014ff70f5187882a188d0ef3f955f33:tests/integration/db/conftest.py:217:def migrated_database(empty_database: DatabaseSettings) -> DatabaseSettings:
  3ab4097c8014ff70f5187882a188d0ef3f955f33:tests/integration/ingest/conftest.py:263:def bucket_keys(raw_s3: Any, s3_settings: S3StorageSettings):
  3ab4097c8014ff70f5187882a188d0ef3f955f33:tests/integration/storage/conftest.py:130:def bucket_keys(raw_s3: Any, settings: S3StorageSettings):
  ```
- interpretation: the existing fixture boundaries are the task's code
  surface. The object layout is content-derived, so filtering canonical
  keys by an invented test prefix would be unsound; isolate the bucket or
  otherwise prove every observed key belongs to this test.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tests/integration/db/conftest.py` — migrated template, per-test clone and cleanup only
- `tests/integration/db/test_fixture_template.py` — new focused fixture regression
- `tests/integration/storage/conftest.py` — test-owned bucket/key observation only
- `tests/integration/ingest/conftest.py` — test-owned bucket/key observation only
- `tests/integration/auth/conftest.py`
- `tests/integration/auth/test_sign_in_throttle.py`
- `tests/integration/auth/test_revocation.py` — isolate only shared throttle/revocation rows
- `docs/program/W52-GATE-01.md` — six-item hand-back report
- local `agent/w52-gate-01` branch/worktree and its own ignored environment

## Forbidden hotspots

Everything else, including `Makefile`, `tests/e2e/pc01/conftest.py`,
`contracts/**`, migrations, root locks/dependencies, application code,
composition roots, global styles, other test suites, current state, debt
register, `origin/dev`, `origin/main`, tags and deployment.

## Non-goals

No `pytest-xdist`, changed battery selection, new test dependency, product
S3/DB layout change, full gate, JUnit parity or speed claim. A test whose
subject is migration application still starts from `empty_database` and runs
the literal command itself. No QA/stand/release verdict here.

## Deliverables

- One migration-head template per suite session, named with a digest of
  `db/migrations/` content and not reused across runs; each consumer test
  gets a fresh clone that is dropped after use.
- Storage/ingest object assertions scoped to a test-owned bucket or an
  equivalent proven ownership boundary, preserving detection of unexpected
  writes and exact-key cleanup. Do not infer test ownership from a canonical
  Blob key's content-derived prefix.
- Isolated throttle and revocation test rows; focused checks and report.

## Required checks

- Focused real PostgreSQL/S3 tests in the changed suites, plus a regression
  proving one migration for multiple clones, no cross-test rows and
  `empty_database` remaining truly empty.
- An adversarial object in another test's bucket does not affect this
  test's key census; an unexpected object in this test's bucket is seen.
- Throttle/revocation cases rerun against distinct rows; Python compilation,
  frontend lint and `git diff --check`.
- Full-gate JUnit outcome parity and timing are measured later under D-140,
  not claimed by this code-only hand-back.

## Integration contract

The executor starts from the exact read-back freeze SHA, uses only
`gate-w52g`'s reserved PostgreSQL `56780` and S3 `60380/60381`, unique DB and
bucket, and hands back `agent/w52-gate-01` with a report and exact diff. The
integrator checks the grant, accepts the branch and publishes to `origin/dev`
only after the W52 development checks. Stage-B grants are issued after that
merge and a fresh pin sweep.

## Failure/idempotency/security cases

If the content-derived object layout prevents a sound scoped observation
inside this grant, stop and report the exact missing path/semantic choice;
never make `bucket_keys` silently ignore writes. A template with stale head,
an active connection blocking drop, or an unavailable service fails loudly.
Use only lane containers and credentials; report no secret values.

## Rollback / feature flag

Revert the fixture-only lane commit. No runtime feature flag or persisted
product data changes.

## Handoff

List changed files, checks/results, contract changes (expected none), risks,
integrator steps and proof that forbidden hotspots were untouched.
