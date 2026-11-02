# Task EXEC2-PULL-01 — serialise pull claims per token, deliver each task to one agent instance, and close D-215

## Outcome
One agent with `concurrency = 3`, a matching server limit and three open tasks processes them in parallel, and each task is claimed and answered exactly once. Two processes presenting one token never work on the same task. An old sequential agent works unchanged. A claimed probe task blocks the product purge.

## Depends on
- EXEC2-SEAL-1

## Frozen inputs
- domain contract: unchanged
- API contract: 1.15.0, frozen by `EXEC2-SEAL-1`
- analysis/comparison/event contract: unchanged
- migration head: `0046`, created by `EXEC2-SEAL-1`; this task adds no migration
- base commit: `integration/exec2` after the `EXEC2-SEAL-1` merge
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 3, 18; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the held-claims count and the claim are separate statements, and a limit of one redelivers to any caller of the token

### P-01 — the repository statements
- captured_at: 2026-11-02
- command: `git grep -nE 'def (held_claims|redeliver|claim_next)' origin/dev -- src/auditmanager/executors/runner_repository.py`
- captured_output:
  ```text
  origin/dev:src/auditmanager/executors/runner_repository.py:349:    def held_claims(self, session: Session, token_id: str) -> int:
  origin/dev:src/auditmanager/executors/runner_repository.py:355:    def redeliver(
  origin/dev:src/auditmanager/executors/runner_repository.py:374:    def claim_next(
  exit=0
  ```
- interpretation: `held_claims`, `redeliver` and `claim_next` run in one transaction but without a lock that serialises two claims of one token.

### P-02 — the claim decision
- captured_at: 2026-11-02
- command: `git grep -nE 'limit = 1 if current|if limit == 1|held_claims\(session' origin/dev -- src/auditmanager/executors/runner.py`
- captured_output:
  ```text
  origin/dev:src/auditmanager/executors/runner.py:485:            limit = 1 if current is None else (current.settings.max_claimed_tasks or 1)
  origin/dev:src/auditmanager/executors/runner.py:492:            if limit == 1:
  origin/dev:src/auditmanager/executors/runner.py:496:            if row is None and store.held_claims(session, principal.token_id) < limit:
  exit=0
  ```
- interpretation: the limit is read, the held task is redelivered at limit one, and the count gates a fresh claim.

### P-03 — the agent's local concurrency
- captured_at: 2026-11-02
- command: `git grep -nE 'concurrency: int = 1|1 <= cfg.concurrency <= 8|threading.Semaphore\(self.cfg.concurrency\)' origin/dev -- tools/executor-runner/agent.py`
- captured_output:
  ```text
  origin/dev:tools/executor-runner/agent.py:89:    concurrency: int = 1
  origin/dev:tools/executor-runner/agent.py:199:    if not isinstance(cfg.concurrency, int) or isinstance(cfg.concurrency, bool) or not 1 <= cfg.concurrency <= 8:
  origin/dev:tools/executor-runner/agent.py:405:        slots = threading.Semaphore(self.cfg.concurrency)
  exit=0
  ```
- interpretation: the agent bounds threads with a semaphore and keeps no registry of tasks in work.

### P-04 — the purge's running-state map (`D-215`)
- captured_at: 2026-11-02
- command: `git grep -n 'RUNNING_STATES' origin/dev -- scripts/recovery/product_purge.py`
- captured_output:
  ```text
  origin/dev:scripts/recovery/product_purge.py:224:RUNNING_STATES = {
  origin/dev:scripts/recovery/product_purge.py:653:    for table, states in RUNNING_STATES.items():
  exit=0
  ```
- interpretation: `RUNNING_STATES` is the map `D-215` asks to extend with `executor_task: ("claimed",)`.

The integrator re-runs every premise command on the actual base before dispatch (`EXEC2-PLAN.md` section 6) and corrects line numbers; a premise that no longer holds stops the dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/executors/runner.py`
- `src/auditmanager/executors/runner_repository.py`
- `src/auditmanager/api/routers/runner.py`
- `src/auditmanager/bootstrap/runner.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/api/routers/ports.py`
- `tools/executor-runner/agent.py`
- `tools/executor-runner/runner_client.py`
- `tools/executor-runner/RUNNER_API.md`
- `tools/executor-runner/README.md`
- `scripts/recovery/product_purge.py`
- `tests/unit/executors/**`
- `tests/unit/executor_runner/**`
- `tests/integration/executors/test_runner_channel.py`
- `tests/integration/executors/test_runner_concurrency.py`
- `tests/integration/recovery/test_product_purge.py`
- `docs/program/DEBT_REGISTER.md`

## Forbidden hotspots
- `contracts/**`, generated models and client, the migration head, root dependency/lock files and global styles (owned by the stage's SEAL task)
- `src/auditmanager/shared/errors/**`: EXEC-2 adds no error code (ADR-0026 decision 18)
- paths another EXEC-2 task owns in the same stage (`EXEC2-PLAN.md` section 5)
- in `src/auditmanager/bootstrap/adapters.py` and `src/auditmanager/api/routers/ports.py`, which three stage-1 lanes share: any function or class outside this task's own port; new code goes in a section headed with this task id, and the integrator merges the lanes one by one
- `src/auditmanager/jobs/**` (`EXEC2-CAP-01`)

## Non-goals
- no multi-instance protocol for one token
- no change to answer validation, identity or images

## Deliverables
- The claim locks the runner-token row (`FOR UPDATE`) before `held_claims`, so count and claim are atomic for one token.
- `runner_instance_id`: stored on the claimed task. Redelivery at limit one goes only to the same instance. A claim without the field behaves as today.
- Agent: a random instance id per process, sent on every claim; a synchronised registry of task ids in work; a redelivered id already in work is not started again; claims only with a free local slot; `409` aborts a submission. `RUNNER_API.md` documents the field and the one-process-per-token rule.
- `D-215`: `"executor_task": ("claimed",)` in `RUNNING_STATES` with a scenario test. The row is struck through in the debt register, citing this task.
- Tests for B1 §6 items 7–12 and 14, plus B2 §11 item 11 (pull regression).

## Required tests
- command: not run in EXEC-2 (`R-149d`); write the tests below and mark those that need PostgreSQL with the suite's existing database marker
- expected: B1 §6 tests 7–12 and 14 exist; the purge scenario test exists

## Integration contract
- agents that send `runner_instance_id` get per-instance redelivery; older agents keep today's behaviour
- `EXEC2-AGENT-01` edits `agent.py` only after this task is merged

## Failure/idempotency/security cases
- stale extend or answer after the lease moved: `conflict` (`claim_lost`), unchanged
- a cancelled task's late answer: refused as today
- a restarted agent with a new instance id does not receive its old claim; the lease lapses and the task follows today's re-open rule

## Rollback / feature flag
Optional field; reverting the merge restores today's claim. The purge change only refuses more.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
