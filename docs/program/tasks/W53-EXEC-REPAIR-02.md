# Task W53-EXEC-REPAIR-02 — refuse orphan running Run authority

task_id: W53-EXEC-REPAIR-02

## Outcome

Calling `execute_run` on a `running` Run with no Job cannot create a fresh
Job/Attempt/Lease or repeat a provider call. A queued direct caller remains
compatible, and an authorized resumed running Job still works.

## Depends on

- `W53-FREEZE-01`, completed at `3c527d363ee5a196fbd44bf2f5b187d544615dd6`.
- `W53-SEAL-01`, accepted at `3132fcb861edbc86bb8bc9130034e7125f4e5bb3`.
- `W53-EXEC-WEB`, integrated at `f5e0e26e410e44f0c305c01d64b00594d9b3b4a3`;
  the sequential host lane is now free. This dependency is for scheduling;
  the repair changes backend paths only.

The original EXEC implementation is integrated as code but has separate
STOP-01/STOP-02 limitations. This repair closes only the orphan-running flaw.

## Frozen inputs

- Code input after Stage B: `f5e0e26e410e44f0c305c01d64b00594d9b3b4a3`.
  The integrator supplies the exact task-file dispatch SHA after committing
  this grant.
- API SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`;
  domain state-machine SHA-256
  `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`;
  migration head `0017_execution_queue`, contract version `1.0.0-draft.1`.
- Evidence: `docs/program/W53-EXEC-REPAIR-02.md` and the existing
  `W53-EXEC-STOP-01`/`STOP-02` boundaries.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

### P-01 — orphan running fallback

- captured_at: 2026-10-09
- command: `git grep -n -E 'elif run.state != "running"|if job is None:|job_id = self.enqueue' -- src/auditmanager/runs/executor.py src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
  src/auditmanager/jobs/repository.py:419:        if job is None:
  src/auditmanager/jobs/repository.py:427:            job_id = self.enqueue(session, run_id=run_id)
  src/auditmanager/runs/executor.py:705:    elif run.state != "running":
  ```
- interpretation: a direct caller could mint new authority for a running
  orphan without checking any prior provider effects.

### P-02 — required sequencing repair discovered in focused regression

- captured_at: 2026-10-09
- command: `git grep -n -E 'run_repo.advance\(|job_repo.start_execution\(' -- src/auditmanager/runs/executor.py | tail -12`
- captured_output:
  ```text
  src/auditmanager/runs/executor.py:700:        run_repo.advance(
  src/auditmanager/runs/executor.py:704:        run_repo.advance(session, run_id=run_id, from_state="queued", to_state="running")
  src/auditmanager/runs/executor.py:720:    authority = job_repo.start_execution(session, run_id=run_id)
  src/auditmanager/runs/executor.py:825:    run_repo.advance(session, run_id=run_id, from_state="running", to_state="validating")
  ```
- interpretation: a repository-only state check cannot distinguish that
  valid direct caller from an orphan that was already `running`. The first
  repair attempt passed its new orphan test but failed 25 existing direct
  execution tests. Scope extends only to the executor call site below.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/jobs/repository.py`: the absent-Job branch of
  `start_execution` only.
- `src/auditmanager/runs/executor.py`: only `_execute_run_body` near the
  Run `queued→running` transition and Job claim. Call `start_execution`
  while a direct caller's Run is still `queued`, then advance it to
  `running` in the same transaction before the existing commit. A Run
  already `running` must prove existing Job authority. No other stage,
  retry, carrier behavior or public signature may change.
- `tests/integration/runs/test_w53_execution.py`: focused regression only.
- `docs/program/W53-EXEC-REPAIR-02-HANDBACK.md`: six-item report.

## Forbidden hotspots

Every other file, in particular `contracts/**`, migrations, routers,
composition, executor, proxy, frontend, root locks, global styles, MinIO,
backup, release files, refs/tags and the working stand. Do not change the
sealed graph or retry classification.

## Non-goals

No own-proxy 503 retry, validating cancellation reseal, frontend change,
worker service, MinIO build, backup, deployment or release verdict.

## Deliverables

The narrow refusal in `JobRepository.start_execution`, a DB regression that
proves zero provider calls and no new authority, and the handback report.

## Required tests

- Seed a running Run with no Job; call `execute_run` with a counting adapter;
  assert typed refusal, zero provider calls, no Job/Attempt/Lease or stage
  event created. Repeat under a second connection if fixture permits.
- Existing direct created/queued execution, valid resumed running Job,
  concurrency and lease tests still pass; specifically rerun the 25 direct
  tests that the repository-only attempt broke. `git diff --check` and
  frozen hashes.
- Check disk before expensive testing under `AGENTS.md` §8. Full `make gate`
  belongs to the integrator on a later clean SHA.

## Integration contract

Isolated worktree, branch `agent/w53-exec-repair-02` from the exact dispatch
SHA supplied by the integrator. `running` with no Job is a typed refusal
before any new authority or external effect; a Run initially `created` or
`queued` retains the direct-caller fallback because the Job claim occurs
while it is `queued`. The following Run advancement and existing commit
form the same transaction. Public `execute_run`, `RunCarrier` and
`RunAdapter` signatures remain unchanged. Existing Job recovery remains
unchanged. Use only
disposable `gate-w53exec` ports 56860 and 60460/60461 after checking them;
stop only own resources. No working-stand operation.

## Failure/idempotency/security cases

No second spend from a missing Job, even if a stale Run says `running`.
The lock order remains Run then Job then Attempt then Lease. A refusal must
not turn a live Run into the generic crash path.

## Rollback / feature flag

Revert the repair commit before development publication if it breaks direct
callers; no new feature flag or stand change.

## Handoff

Return clean branch and exact SHA, all six `AGENTS.md` §5 items, test logs,
frozen hashes and exact base-to-HEAD allowed-path audit. Do not publish refs
or create tags.
