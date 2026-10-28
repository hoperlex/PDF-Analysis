# CMP-PQ-ISOLATION-01 — report

Lane: `agent/cmp-pq-isolation-01`, base `eca5f9fa` on `integration/compare-modules`. Tests only: nothing under `src/`,
`contracts/`, `db/migrations/` or any root file changed. Task: `docs/program/tasks/CMP-PQ-ISOLATION-01.md`.

## What was wrong

The eighteen tests of `tests/integration/comparison/profile_queue/` passed only on a database no other integration
directory had used. The comparison queue is written for a worker, so it reads the whole database: it yields to **any**
claimable Run (`ClaimGates` / `default_gates`, strict priority, `CMP-WORK-01`), leases the strongest queued item of
**any** project (`_PICK`, `FOR UPDATE SKIP LOCKED`) and reclaims **every** expired lease (`_EXPIRED`). Once a queued Job
existed anywhere (`tests/integration/composition/test_the_run_leaves_the_request_thread.py` leaves four; `runs/`
leaves about twenty more), `Lane.claim` failed with `the runner claimed nothing: a gate is shut or no item is due` in the eleven
tests that claim. The other three global reads (the stronger foreign item, the foreign expired lease, the count of
`reclaim()`) did not fail yet on the databases at hand, because every comparison directory deletes its own queue rows;
they are the same defect and were closed with it.

## What changed

`tests/integration/comparison/profile_queue/conftest.py` (`Lane`):

* `gates()`: the real pause gate and a Run-priority gate that asks the question of `next_queued_run` (a queued Job, due, of
  a Run that is queued or running) of the Runs of **the lane's own projects**. The lane seeds no Run, so it stays open; it
  is a read of the real `job` / `audit_run` tables, not a constant. `runner()` passes it as `gates=`.
* `worker_runner()`: the runner the worker builds (`build_comparison_work`, the shipped handler tuples), built while
  `auditmanager.comparison.work.runner.default_gates` is the lane's `gates()`. `build_comparison_work` takes no gates and
  `src/` is not ours; the patch ends with the build. The two tests of `test_version_built_through_the_queue.py` use it, so
  the registration of the kind through `HANDLER_FACTORIES` is still proved on the worker's own runner.
* `claim()`: a foreign queued item (a project that is not the lane's) is locked by a connection of its own for the length of
  the claim, so the pick passes over it (`SKIP LOCKED`) and nothing in it changes; the lock ends by a rollback before the
  item runs. The claimed item must belong to the lane's projects. A refusal names the gate states instead of guessing.
* `reclaim(runner)`: runs the runner's reclaim (which, like a worker's, fences every expired lease of the database) and
  answers how many of **the lane's own** attempts it ended. `test_a_lease_that_runs_out_mid_build...` asserts
  `lane.reclaim(runner) == 1` in place of `runner.reclaim() == 1`.
* `queue_run`, `foreign_project`, `foreign_run`, `foreign_item`, `foreign_expired_lease`: plant the rows another directory
  would leave. `clean()` removes them (the Job and Run, the work and attempt rows of the foreign projects).

`tests/integration/comparison/profile_queue/test_foreign_rows_do_not_change_the_verdict.py` (new, two tests): the isolation
is shown on any database, fresh or not, because the foreign rows are planted by the test itself.

* the lane's gate is a read of the lane's own Runs: the real gate yields to a foreign Run (premise), the lane's does not; a
  Run of the lane's project (written and rolled back) shuts it; a Job that is not due does not;
* with a foreign claimable Run, a **stronger** foreign queued item and a foreign expired lease in the database, the lane's
  claim leases its own item and not the foreign one, its reclaim counts its own attempt (the foreign lease is fenced too,
  asserted as the premise), and the next claim, with two stronger foreign items queued, is again the lane's own item,
  which is built.

The other three test files changed only where they read the queue globally (`reclaim`, the worker-built runner and the
docstrings that said "the real gates").

Not weakened: the pause gate is still the real one; every assertion about the handler (stop between pages, a lost lease
reclaimed and resumed, a child that never started retried, the budget spent, a payload of another shape failed at once,
the version built through the worker's runner) is unchanged. The strict priority of Runs over comparison work is not this
suite's to prove and stays proved by `tests/integration/comparison/work/test_claim_gates.py` on the real gates.

### The two further items the integrator granted

* `tests/unit/comparison/work/test_composition_unit.py::test_one_dependency_bundle_is_built_once_and_every_factory_receives_it`
  was red because `build_comparison_work` appends the two `CMP-INGEST-02` batch factories to the tuple the test patched.
  **Chosen: assert what the test means, not patch the extra kinds away.** The comparison tuple is still replaced by two
  recording factories; each factory of `BATCH_HANDLER_FACTORIES` is wrapped so that it records the bundle it is given and
  still builds its real handler; the test asserts that the kinds it patched are registered (`<=`, not `==`), that every
  factory (patched and batch) received the **same** bundle, and that the count of recorded bundles is the count of
  factories of the two tuples it knows. A later lane that appends a factory registers one kind more and does not turn
  it red; patching only the extra kinds would have named the two batch kinds in the test and broken it for the next lane
  in the same way.
* `tests/unit/runs/test_serving_start_sweeps_temporaries.py::test_the_worker_sweeps_after_its_configuration_is_accepted_and_before_it_registers`:
  the stand-in `Runtime` now carries `comparison_work = None`, which `workers/__main__.py serve()` reads.

## Checks (commands on the lane's own stack: ports 57830 / 61830 / 61831, head `0038_comparison_foundation`)

All with `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider`.

| # | State of the database | Tree | Result |
| --- | --- | --- | --- |
| 1 | fresh (0 Job rows) | base `eca5f9fa` | `tests/integration/comparison/profile_queue`: **18 passed** |
| 1 | fresh (0 Job rows) | this lane | same directory: **20 passed** (18 + the two new) |
| 2 | after `tests/integration/composition/test_the_run_leaves_the_request_thread.py` (16 passed): `select count(*) from job where state='queued'` = **4**, all 4 due and joined to a Run in state `queued`/`running`; `comparison_work` 0 rows | this lane, no reset | **20 passed** |
| 3 | the same database as 2, no reset | base tree's four files (`git show eca5f9fa:...`) | **11 failed, 7 passed**, every failure `the runner claimed nothing: a gate is shut or no item is due` (`conftest.py:227`) |

Earlier, on a database that `runs/`, `jobs/`, `ingest/comparison_batch`, `comparison/work` and `comparison/spend` had used
(35 to 36 queued Jobs): base tree 11 failed / 7 passed; this lane 20 passed.

Mutations of the new guards, each red at once and restored by `git checkout` (profile_queue, 20 tests):

| Mutation | Result |
| --- | --- |
| `gates()` returns `default_gates()` (the unscoped read) | 13 failed (the 11 + both new tests) |
| `claim()` without the fence on foreign queued items | 1 failed: the stronger-foreign-item test |
| `reclaim()` answers `runner.reclaim()` (the unscoped count) | 1 failed: the same test (the 18 old tests stay green on a database with no foreign lease, which is why the new test plants one) |
| the lane's Run gate is a constant `False` | 1 failed: the gate test |
| the lane's Run gate not scoped to the lane's projects | 13 failed |

Unit-test items (container-free):

| Mutation / state | Result |
| --- | --- |
| base: the two tests as found | both red (kinds set; `Runtime` without `comparison_work`) |
| `src/auditmanager/bootstrap/composition.py` stops applying the comparison tuple (mutated, restored) | 2 failed in `test_composition_unit.py` (this test and the duplicate-kind test) |
| `src/auditmanager/comparison/work/registry.py` hands each factory a copy of the bundle (mutated, restored) | 1 failed: this test (`4 == 2 + 2 and False`) |
| stand-in without `comparison_work` (the base file) | `test_the_worker_sweeps...` red |

Whole suites on the final tree:

* `tests/unit`: 4389 collected, **4313 passed, 76 skipped, 0 failed**, exit 0, 4 min 2 s (no database variable in the
  environment).
* `tests/contract` minus the three `D-220` files (`test_cp00_candidate.py`, `test_cp00_final_state.py`,
  `test_validate_bootstrap.py`): **1309 passed, 1 failed, 19283 subtests passed**, 2 min 15 s. The one red,
  `tests/contract/program/test_wave_governance.py::test_every_task_added_after_governance_activation_satisfies_the_rules`,
  is `docs/program/tasks/CMP-SEAL-C1.md` (`PREMISE_COMMAND_REQUIRED`, `PREMISE_DATE_REQUIRED`, `PREMISE_OUTPUT_REQUIRED`),
  a file this lane did not touch and which is red on `eca5f9fa`; this lane's task file is not flagged.
* `git diff --check`: clean.

## Forbidden hotspots

`git diff --stat eca5f9fa -- src contracts db pyproject.toml uv.lock docs/program/P02_LOCK.json web` is empty. The two `src/`
mutations above were restored with `git checkout -- src` before any commit. Changed files are under
`tests/integration/comparison/profile_queue/`, the two unit files granted by the integrator, and the two documents of
this lane. `conftest.py` of `profile_queue/` is a shared test fixture of **this directory only** (`AGENTS.md` §8, case 3);
no complete gate was run, as the code-first override `R-135` and the lane brief provide; the integrator's gate covers it.

## Known limits

* `Lane.claim` fences foreign queued items with a row lock held for the length of one claim (milliseconds). A foreign
  writer that needs one of those rows in that instant waits for the lock; the shared lane database is not meant to be
  used by two suites at once, and the old behaviour (a foreign item leased by the test) was worse.
* `reclaim` still fences foreign expired leases (the worker's job) and puts those items back in the queue; the lane
  neither counts nor claims them. It does not protect against more than 100 foreign expired leases (`_EXPIRED` has a
  `LIMIT 100` ordered by work id), which no directory produces.
* The pause gate is the real one: a suite that leaves `execution_control.paused` set would still shut this suite. None does
  (`comparison/work` restores it).
* The Jobs and Runs of `composition/test_the_run_leaves_the_request_thread.py` stay queued in the database; they are the
  reproduction, and this suite no longer minds them.

## Instructions for the integrator

Merge the lane with its two commits of tests and the two documents. No ordering constraint against the other C0/C1 lanes:
no `src/` or wiring file is touched. If another comparison directory builds a runner with the real gates on a shared
database it has the same exposure; `tests/integration/comparison/work` already parks foreign Jobs with `quiet_runs`.
