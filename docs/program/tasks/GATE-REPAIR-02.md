# Task GATE-REPAIR-02 — the lease test that fails only inside the complete battery

task_id: GATE-REPAIR-02

## Outcome

The two complete-gate runs of `7cb317b0` (artefacts `.local/gates/night-7cb317b0/gate.log` and
`gate.killed-1.log`) both fail test 2 of 2 of
`tests/integration/jobs/test_d141_final_transaction_keeps_the_lease.py` at the same position of
the battery, while the file passes alone and under CPU load. The cause of that battery-only
failure is found by bisection, shown by a failing-first reproduction, and removed (or, when it
is a product defect, reported with its evidence), so the next complete gate does not stop on it.
The one other red seen once, `tests/integration/qa_w55b/test_p1_upload_to_version.py` (test 11 of
20, run 1 only, not in run 2), is classified: flaky with a rate, or a harness race that is
repaired.

## Depends on

- `GATE-REPAIR-01` — completed, merged (`ba6af907`).

## Frozen inputs

- base: `origin/dev` at the freeze commit of this file (parent `7cb317b0`);
- the battery order of the complete gate (the `pytest` arguments of `make gate`): `tests/integration/`
  `analysis analysis_engine analysis_text api auth composition db ingest jobs optimisation p02_journey`
  `qa_w52 qa_w55b recovery runs shared_kernel workers`; the failing test sits at index 4206 of 5294,
  after `ingest` and inside `jobs`;
- migration head `0029_routing_refusal_codes`; API 73/83/242; 27 error codes; contract `1.0.0`;
- rulings: `R-135`, `R-126`, and the owner's direct instruction of 2026-10-22 «гони до беты без
  вопросов».

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tests/integration/jobs/**`
- `tests/integration/qa_w55b/**`
- `tests/integration/ingest/**`
- `docs/program/GATE-REPAIR-02.md`
- `docs/program/tasks/GATE-REPAIR-02.md`

## Lane resources

- foundation_instance: `auditmanager-gate-repair`
- postgres_port: `57600`
- s3_api_port: `61400`
- s3_console_port: `61401`
- postgres_db: `auditmanager_gate_repair`
- s3_bucket: `auditmanager-gate-repair`
- qa_api_port: `28520` (`W55B_QA_API_PORT=28520 W55B_QA_HEALTH_PORT=28521`; the complete gate on this
  host uses 28500/28501, never those)

## Forbidden hotspots

Every `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, dependency and lock
files, `tests/support/**`, `tests/conftest.py`, `tests/e2e/**`, `web/**`, `CURRENT_STATE.md`,
`DEBT_REGISTER.md`, refs, tags and the stand. The worktree `.local/worktrees/gate-night` and the
instance `auditmanager-gate-night` belong to a running gate: do not read them with a tool that
could write, do not run anything there.

## Non-goals

No product change (a product defect is reported, not repaired); no complete `make gate`; no weakening
of an assertion; no widening of the lease margin as a substitute for the cause (the margin was
widened by `GATE-REPAIR-01` and did not help).

## Work

1. Read the traceback: when the first phase of the running gate ends its summary names the failing
   test and its assertion. Until then, work from the position. Do not wait for it to start.
2. Reproduce on the lane's own stack, **one pytest process at a time**, from the test outwards:
   the file alone (known green); `ingest` then the file; then bisect the directories that precede
   `jobs` in the battery order, in that order, in one process, to find the smallest preceding set
   that makes test 2 fail. Each run under 40 minutes; quote command, exit status and the failing
   assertion. Candidates to look at first: module or class state left by an earlier test
   (`JobRepository.lease_seconds`, `lease_module.HEARTBEAT_SECONDS`, monkeypatches that outlive a test,
   threads that outlive a test), database state left behind (runs left `running`, leases, advisory
   locks, roles' timeouts), and fixtures in `tests/integration/jobs/conftest.py`.
3. Repair inside the allowed paths with a failing-first test or a quoted mutation; when the cause is
   in `src/**` stop that item and report it with the evidence.
4. Classify `qa_w55b/test_p1_upload_to_version.py` test 11 by repetition in its own directory.
5. Commit after each repaired group on the lane branch; the last commit is the report
   `docs/program/GATE-REPAIR-02.md`.

## Deliverables

Repaired tests, the bisection log, the report with before/after and the proof of containment.

## Required tests

The bisected set green after the repair, the file in the battery-like context, `git diff --check`.

## Integration contract

Merged as a real merge into `integration/night-1020`; the dev tip after it is the candidate of
the next complete gate. Hand back by 04:30 +05 on 2026-10-22 with whatever is established.

## Failure/idempotency/security cases

A red that passes on rerun without a change is recorded as flaky with its rate. A cause that needs a
hotspot is reported at once by message. The lane stops its own containers when it hands back and
kills no process it did not start, by confirmed PID, never by pattern.

## Rollback / feature flag

Revert the merge. Tests only; no flag.
