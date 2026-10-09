# W53-EXEC-REPAIR-02 handback

Base: `b4ae2afd17e9da50c41537e13b2e554bbd40cdde`; branch:
`agent/w53-exec-repair-02`. The integrator's exact scope amendments are
`48a8e3eebd391a0b9ceb6ab947588eece204d235` (executor ordering) and
`d62d8ec2bd0c6c470b75c8f1427a7ff860060580` (two obsolete test setups).

## 1. Changed files

- `src/auditmanager/jobs/repository.py`: the absent-Job branch now refuses a
  running Run before enqueue or any Attempt/Lease authority is created.
- `src/auditmanager/runs/executor.py`: obtains Job authority while a direct
  caller's Run is still queued, then advances it to running within the same
  transaction before the existing commit. Existing running Job resume uses
  the same authority path.
- `tests/integration/runs/test_w53_execution.py`: orphan-running regression
  with a historical model call, counting adapter, typed refusal, and zero
  new Job/Attempt/Lease or stage events.
- `tests/integration/runs/test_durable_effect_boundaries.py`: two test setups
  claim authority while queued, then advance to running; their fault and
  fencing assertions are unchanged.
- `docs/program/W53-EXEC-REPAIR-02-HANDBACK.md`: this report.

## 2. Checks and results

- Disk preflight: 12,154,232,832 bytes free before recreating the disposable
  PostgreSQL service; both the worktree and Docker root are on the checked
  filesystem. Reserved ports 56860/60460/60461 were verified and used only
  by this lane. Disposable PostgreSQL migration head: `0017_execution_queue`.
- On a fresh isolated database with the existing disposable old MinIO image:
  `PYTHONPATH=src python -m pytest -c pyproject.toml --rootdir=. -q
  tests/integration/runs/test_w53_execution.py
  tests/integration/runs/test_full_chain.py
  tests/integration/runs/test_durable_effect_boundaries.py`:
  **35 passed in 10.67s**.
- Four existing two-connection composition tests for live lease recovery,
  locked priority selection, claim/cancel lock order, and watchdog fencing:
  **4 passed in 2.13s**.
- `git diff --check`: passed. No full `make gate` was run; that belongs to
  integration on its clean candidate SHA.

## 3. Contracts

No contract or migration changed. Frozen hashes were rechecked:

- `contracts/api/v1/openapi.json` SHA-256:
  `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`.
- `contracts/domain/v1/state-machines.json` SHA-256:
  `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
- Migration head: `0017_execution_queue`; contract version:
  `1.0.0-draft.1`.

## 4. Risks and known limits

An already orphaned running Run remains running after a direct refusal;
startup reconciliation owns its terminal transition. The existing W53
own-proxy 503 and validating-cancel STOP records remain separate. The
integration gate and cross-lane QA have not been run on this branch.

## 5. Integrator instructions

Cherry-pick this branch's exact HEAD after the task amendments. Verify the
base-to-HEAD path audit, rerun focused tests on a fresh disposable database,
then perform independent QA and the full gate on the final clean SHA after
the required disk preflight. Do not publish this agent branch or tags.

## 6. Forbidden-hotspot and allowed-path proof

The complete base-to-HEAD changed-path set is exactly the five files in
section 1. The two added paths beyond the original task grant are covered
by the exact integrator amendments named above. No `contracts/**`, migration,
router, composition root, proxy, frontend, root lock, global style, MinIO,
backup, release or deployment path changed. No working stand was touched.
