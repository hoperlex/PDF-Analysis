# Task EXEC2-CAP-01 — count capacity units per connection in the Run claim, the dispatcher hint and the comparison call

## Outcome
With `max_active_runs = 3` and enough worker slots, three independent Runs execute on one connection at once and a fourth waits. A comparison call takes a unit from the same budget. A connection at capacity never blocks Runs of another connection. With the default of one, behaviour is exactly as before.

## Depends on
- EXEC2-SEAL-1

## Frozen inputs
- domain contract: unchanged
- API contract: 1.15.0, frozen by `EXEC2-SEAL-1`
- analysis/comparison/event contract: unchanged
- migration head: `0046`, created by `EXEC2-SEAL-1`; this task adds no migration
- base commit: `integration/exec2` after the `EXEC2-SEAL-1` merge
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 1, 2, 18; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: exclusivity is an EXISTS check in three places

### P-01 — the Run claim, its lock and the dispatcher hint
- captured_at: 2026-11-02
- command: `git grep -nE '^_LOCK_CONNECTION = |^_CONNECTION_HAS_OTHER_ACTIVE_RUN = |^_NEXT_JOB = |def _hold_connection_limit' origin/dev -- src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
  origin/dev:src/auditmanager/jobs/repository.py:58:_LOCK_CONNECTION = text(
  origin/dev:src/auditmanager/jobs/repository.py:69:_CONNECTION_HAS_OTHER_ACTIVE_RUN = text(
  origin/dev:src/auditmanager/jobs/repository.py:94:_NEXT_JOB = text(
  origin/dev:src/auditmanager/jobs/repository.py:955:    def _hold_connection_limit(session: Session, *, run_id: str) -> None:
  exit=0
  ```
- interpretation: the claim's busy check, its lock and `_NEXT_JOB` are the three statements to turn into counts.

### P-02 — the comparison mirror
- captured_at: 2026-11-02
- command: `git grep -nE 'def (connection_has_active_run|connection_has_active_call|lock_connection)' origin/dev -- src/auditmanager/comparison/spend/repository.py`
- captured_output:
  ```text
  origin/dev:src/auditmanager/comparison/spend/repository.py:255:    def lock_connection(self, session: Session, connection_id: str) -> None:
  origin/dev:src/auditmanager/comparison/spend/repository.py:263:    def connection_has_active_run(self, session: Session, connection_id: str) -> bool:
  origin/dev:src/auditmanager/comparison/spend/repository.py:266:    def connection_has_active_call(self, session: Session, connection_id: str) -> bool:
  exit=0
  ```
- interpretation: the comparison call preparation asks the same question with its own two checks under the same lock.

### P-03 — `max_parallel_calls` is enforced nowhere
- captured_at: 2026-11-02
- command: `git grep -n 'max_parallel_calls' origin/dev -- src/auditmanager ':!src/auditmanager/executors/model.py' ':!src/auditmanager/executors/repository.py'`
- captured_output:
  ```text
  origin/dev:src/auditmanager/api/schemas/models.py:4022:    max_parallel_calls: Annotated[int, Field(ge=1, le=16)] = Field(  # type: ignore[assignment]
  exit=0
  ```
- interpretation: outside the executor model and repository the field exists only in the generated schema; decision 2 couples it by validation.

The integrator re-runs every premise command on the actual base before dispatch (`EXEC2-PLAN.md` section 6) and corrects line numbers; a premise that no longer holds stops the dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/jobs/README.md`
- `src/auditmanager/comparison/spend/repository.py`
- `src/auditmanager/comparison/spend/caller.py`
- `src/auditmanager/executors/repository.py`
- `src/auditmanager/executors/commands.py`
- `src/auditmanager/executors/queries.py`
- `src/auditmanager/executors/README.md`
- `src/auditmanager/runs/repository.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/api/routers/runs.py`
- `src/auditmanager/api/routers/executors.py`
- `src/auditmanager/api/schemas/runs.py`
- `src/auditmanager/executors/public.py`
- `src/auditmanager/workers/service.py`
- `docs/program/DEBT_REGISTER.md`
- `tests/integration/comparison/spend/test_connection_single_user.py`
- `tests/unit/runs/test_run_status_executor.py`
- `tools/executor-runner/claude_answer.py`
- `tools/executor-runner/codex_answer.py`
- `tests/unit/jobs/**`
- `tests/unit/executors/**`
- `tests/unit/comparison/spend/**`
- `tests/integration/jobs/**`
- `tests/integration/executors/test_connection_capacity.py`
- `tests/integration/comparison/spend/test_connection_capacity.py`

## Forbidden hotspots
- `contracts/**`, generated models and client, the migration head, root dependency/lock files and global styles (owned by the stage's SEAL task)
- `src/auditmanager/shared/errors/**`: EXEC-2 adds no error code (ADR-0026 decision 18)
- paths another EXEC-2 task owns in the same stage (`EXEC2-PLAN.md` section 5)
- in `src/auditmanager/bootstrap/adapters.py` and `src/auditmanager/api/routers/ports.py`, which three stage-1 lanes share: any function or class outside this task's own port; new code goes in a section headed with this task id, and the integrator merges the lanes one by one
- `src/auditmanager/executors/runner*.py` and `tools/executor-runner/agent.py` (`EXEC2-PULL-01`)

## Non-goals
- no reservation table (ADR-0026, alternatives)
- no group routing
- no parallel calls inside a Run

## Deliverables
- Used units = active Runs plus live `prepared`/`sent` comparison calls of the connection, compared with `max_active_runs` of its current revision under the existing `connection_id` lock and lock order, in `_hold_connection_limit`, `_NEXT_JOB` and the comparison call preparation.
- Coupled revision validation (decision 2) in the revision commands, as `validation_failed` with the SEAL-1 constraint values.
- `ssh_command`: read `claude_answer.py` and `codex_answer.py` for per-invocation isolation (working directory, temporary files, output). Make them isolated if they are not. Accept a value above one only when they are, and record the finding.
- Read model `occupancy` and the Run `queue_reason` `executor_at_capacity`, derived from the database at read time.
- Tests for B1 §6 items 1–6 and 15. That includes a two-process PostgreSQL race on the last unit and a comparison call contending with Runs.

## Required tests
- command: not run in EXEC-2 (`R-149d`); write the tests below and mark those that need PostgreSQL with the suite's existing database marker
- expected: B1 §6 tests 1–6 and 15 exist and would pass against PostgreSQL

## Integration contract
- `executors.public` (or the module the lane names) exposes `used_units(session, connection_id)` and `capacity_of(session, connection_id)`; `EXEC2-GROUP-RUN-01` and `EXEC2-GROUP-CMP-01` reuse them
- a lowered capacity affects new claims only

## Failure/idempotency/security cases
- two claims for the last unit: exactly one succeeds
- a killed worker's Run keeps its unit until the queue's reclaim ends its Attempt, as today
- `retry_wait` keeps its unit (unchanged semantics)
- a Run without a revision (`environment`) takes no lock and no unit, as today

## Rollback / feature flag
Operational: a new revision with `max_active_runs = 1` restores exclusivity. Code: revert the merge; the column is ignored.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
