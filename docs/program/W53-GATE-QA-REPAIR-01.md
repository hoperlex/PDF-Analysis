# W53-GATE-QA-REPAIR-01 — handback

- Branch: `agent/w53-gate-qa`; immutable dispatch base: `8d94517e30c91564557d1f30ba98cd76cd559c62`.
- Frozen inputs checked: `contracts/api/v1/openapi.json` SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`; `contracts/domain/v1/state-machines.json` SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`; private DB migrated to `0017_execution_queue`.

## 1. Changed files

- `tests/integration/qa_w53/test_queue_and_effect_journal.py`: the pause race test creates a priority-100 competing Job ahead of its own priority-99 Job. It first checks that an ordinary hint selects another Run. A separate transaction then locks every other runnable Run, allowing the real dispatcher `next_queued_run` to hint its own Run through `SKIP LOCKED`. That lock-only transaction rolls back before the administrator commits pause. The existing claim assertion still requires no authority, a queued Job and zero Attempts; teardown unpauses and cancels only the two Runs this test created.
- This handback.

## 2. Checks and results

- Disk/ports preflight at `2026-10-09T14:46:14.768166+00:00`: worktree and Docker root each had `8,309,198,848` available bytes; estimated incremental peak `2,147,483,648` plus `3,221,225,472` safety bytes. Ports `56922/60524/60525` were free. `/tmp/w53-gate-qa-repair/preflight.log` SHA-256 `5df51f66bc902abbb89323d5c86e15741457f3bfe37d4d139ac368772fdaf391`.
- `make up`, then `make check-services migrate check-db check-storage`: exit 0 on only `gate-w53qa-repair`; private DB head `0017_execution_queue`. Logs `/tmp/w53-gate-qa-repair/up.log` SHA-256 `e1a4533d5a557f2ffbe001fc8b30c77ea5b59556cb549153882da77a2598663a` and `foundation.log` SHA-256 `5c5da5cefaa4d0de7841efef8fe9dbf64206eeed9ffa52d3a9ee7d02559f4e66`.
- `PYTHONPATH=src .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q tests/integration/qa_w53/test_queue_and_effect_journal.py`: **4 passed**. `/tmp/w53-gate-qa-repair/owned.log` SHA-256 `88da021324d6d242d588113c1a55da88adaf9d53beca1d0f36a813392ea4bc30`.
- Same pytest command with `tests/integration/runs/test_w53_execution.py` first and the owned file second: **17 passed**. `/tmp/w53-gate-qa-repair/combined.log` SHA-256 `7ec585bed8c21d230180931683f362223d179544f0a1fc052010836261b1f205`.
- Process-only plugin `/tmp/w53-gate-qa-repair/pause_mutation.py` replaced `start_execution`'s `_LOCK_CONTROL` with a locked read that reports `false`. The single repaired test exited **1** on its intended assertion: a returned `AttemptAuthority`, Job `running`, one Attempt. The unmutated source tree remained untouched. `/tmp/w53-gate-qa-repair/mutation.log` SHA-256 `b4eb2b0b6c3908f0a4125d9780e3970327515fca12ee5326ece8e89e6e57d1f1`.
- `git diff --check`: exit 0.

## 3. Contracts

No contract, migration, product behavior or API changes.

## 4. Risks and limitations

The test intentionally obtains its hint while other runnable Run rows are locked by a separate test transaction. It proves pause-after-hint claim refusal, not fairness or selection among unlocked Jobs. That transaction makes no writes and rolls back before pause; the claim is performed on a new connection.

## 5. Integrator instruction

Verify the base-to-HEAD path audit and adopt this test-only commit. Run the affected focused tests on the integration candidate, then the complete gate on its clean exact SHA under the disk preflight rule. Do not publish a ref from this lane.

## 6. Allowed paths and forbidden hotspots

Only the two paths granted by `docs/program/tasks/W53-GATE-QA-REPAIR-01.md` are changed. `contracts/**`, `db/migrations/**`, `src/**`, `infra/**`, root dependencies/locks, composition roots, global styles, refs and tags are untouched. The disposable lane uses only `gate-w53qa-repair` and ports `56922/60524/60525`; no working stand was accessed.
