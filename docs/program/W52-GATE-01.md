# W52-GATE-01 — serial gate fixture preparation

**Base:** `7c68e84186fa13023961dd6119ec05176de29485` (the read-back Stage-A freeze).
**Lane:** `agent/w52-gate-01`. **Date:** 2026-10-08.

## 1. Changed files and result

- `tests/integration/db/conftest.py`: one session-local migrated template, named with a digest of every regular `db/migrations/` file and a run nonce. Each consumer gets a new PostgreSQL clone; migration-application tests retain their truly empty database.
- `tests/integration/db/test_fixture_template.py`: verifies two clones have the migration head, cannot see each other's row/table, and the empty fixture has no schema. After the template migrates, a subprocess spy refuses a second Alembic invocation.
- `tests/integration/storage/conftest.py` and `tests/integration/ingest/conftest.py`: a new bucket per test, full unfiltered key census, exact-key teardown and bucket deletion. Session clients retain the same endpoint and credentials; direct boto3 fixture users receive the test bucket.
- `tests/integration/auth/test_sign_in_throttle.py` and `tests/integration/auth/test_revocation.py`: replace fixed absent-account targets with random names and a new User UID; real account fixtures were already random and cleaned per test.
- This report.

## 2. Checks and results

- `make up`, `make check-services migrate check-db check-storage` on the reserved `gate-w52g` instance and ports `56780`, `60380`, `60381`: passed; migration head `0015_accounts_roles_registration`.
- Real PostgreSQL `tests/integration/db`: **257 passed**. Real S3 `tests/integration/storage`: **63 passed** after the final teardown change. Real PostgreSQL/S3 `tests/integration/ingest`: **91 passed**, one existing Starlette deprecation warning. Real PostgreSQL `test_sign_in_throttle.py` and `test_revocation.py`: **54 passed**, one existing Starlette warning.
- The first ingest run found two accepted-upload tests that do not register their Blob for teardown; it ended **91 passed, 2 teardown errors**. Teardown now enumerates and removes exact keys in the test-owned bucket. The repeat passed. The two buckets left by the failed run were removed by exact name.
- Adversarial two-bucket probe against both fixture census helpers: `blobs/unexpected` in this test's bucket was visible; `blobs/adversarial` in the other bucket was excluded. Both probe buckets were deleted.
- After all suites: **0** temporary `a1_*` / `b1_ingest_*` PostgreSQL databases and only the base `audit-w52g` bucket remained. Python `compileall`, `npm --prefix web run lint`, and `git diff --check`: passed.
- `make down` removed only the `gate-w52g` containers/network; the exact `gate-w52g-postgres-data` and `gate-w52g-s3-data` disposable volumes were then removed. The owner's `auditmanager-w19a` stand was untouched.

## 3. Contracts

No API, domain, event, migration, dependency or runtime contract changed. The frozen surface remains 27 paths / 34 operations / 77 schemas, domain candidate revision 9 / 29 identities, 23 error codes and migration head `0015_accounts_roles_registration`.

## 4. Risks and limits

This is code-only development evidence. Full `make gate`, JUnit outcome parity and timing remain D-140; QA, built-stand and release acceptance remain D-137–D-139. The PostgreSQL template is unique to a pytest process and is removed at session end; interruption can leave its named database for operator cleanup. Temporary S3 buckets are removed at test teardown, including unexpected keys, after assertions have had the full bucket census.

## 5. Integrator instruction

Review this branch's exact diff against the task grant, fast-forward `integration/w51`, run R-70's development checks, and publish only the checked candidate to `origin/dev` with remote readback. Run a fresh `pin_sweep` and issue concrete Stage-B grants from that merged SHA. Do not infer a release verdict or `origin/main` authority from this hand-back.

## 6. Forbidden-hotspot proof

`git diff --name-only 7c68e841..HEAD` after the lane commit must list exactly the six fixture/test paths in §1 and this report. None is in `contracts/**`, `db/migrations/**`, `Makefile`, root dependencies/locks, application code, composition roots, global styles, deployment, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `origin/dev`, `origin/main` or tags. The ignored `.env` has only the lane's disposable values and is not committed.
