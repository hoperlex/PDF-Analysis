# Task GATE-REPAIR-03 — the notification test waits for the run to finish, not for the claim

task_id: GATE-REPAIR-03

## Outcome

`tests/integration/workers/test_worker_service.py::test_a_notification_wakes_the_worker_before_its_poll`, the one red of
the complete gate of `c58d62f6` (artefacts `.local/gates/night-c58d62f6/gate.log`), proves what its docstring says, that the
`NOTIFY` of the accepting commit woke the worker long before its 120 s poll, without depending on how long a whole run takes in
the battery's process.

## Depends on

- `GATE-REPAIR-02` — completed, merged (`0234047c`).

## Frozen inputs

- base: `origin/dev` at the freeze commit of this file (parent `c58d62f6`);
- measured cause (the gate stand's database after the failed battery, read with `psql`): the worker did claim the run promptly
  and the run took about 55 s to finish (`job` created 01:50:04.903, `terminal_at` 01:50:59.819 for the test's own run; the
  following worker tests' runs took 55 to 58 s each), while the test waits 45 s for a terminal state. A run that is 10 s in a
  small process takes 55 s behind the eight large directories, because of the per-page full `gc.collect()` in
  `analysis/stages/extraction.py::_release` (`D-200`); the three other worker tests wait 60 to 90 s and passed;
- the test file and `tests/integration/workers/conftest.py` as they are on `c58d62f6`; migration head `0029`; no src change.

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

- `tests/integration/workers/**`
- `docs/program/GATE-REPAIR-03.md`
- `docs/program/tasks/GATE-REPAIR-03.md`

## Lane resources

- foundation_instance: `auditmanager-gate-repair`
- postgres_port: `57600`
- s3_api_port: `61400`
- s3_console_port: `61401`
- postgres_db: `auditmanager_gate_repair`
- s3_bucket: `auditmanager-gate-repair`

## Forbidden hotspots

Every `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, dependency and lock files, `tests/support/**`,
`tests/conftest.py`, `web/**`, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, refs, tags and the stand. The worktree
`.local/worktrees/gate-night` and the instance `auditmanager-gate-night` belong to the integrator (a second phase of the
battery may be running there): do not run anything there.

## Non-goals

No product change, in particular not the `gc.collect()` of `D-200`. No lengthening of a timeout as the whole repair: the test
is about the claim, so it observes the claim.

## Work

1. In the notification test, replace the wait for a terminal state by a wait for the **claim**: the job leaves `queued`
   (an Attempt exists, `attempts >= 1`, or the job is `running`), within the 45 s window. The poll is 120 s, so only the
   notification can explain a claim inside it. Then let the run finish with the generous timeout the sibling tests use (60 to
   90 s), so the worker stops clean and no run is left running for the next test.
2. Check the sibling tests of the same file for the same shape (a short wait for a terminal state that depends on the run's
   duration) and list them in the report; change one only if it shows the same weakness at the battery's heap size, and say why.
3. A mutation: with the notification wake-up disabled (the worker does not `LISTEN`, or the `NOTIFY` is not sent) the new
   test fails inside 45 s with the poll at 120 s; quote the exact mutation and the result.
4. Before and after: the file alone (11 passed), and the file behind a heap that models the battery (a collector that holds the
   GIL for about 3 s per page, as in `GATE-REPAIR-02`, or the real prefix if time allows): the old test fails, the new passes.

## Deliverables

The changed test (and conftest only if needed), and `docs/program/GATE-REPAIR-03.md`.

## Required tests

`tests/integration/workers/` as a whole on the lane's own stand, once, and the mutation; `git diff --check`.

## Integration contract

Merged as a real merge into `integration/night-1020` by the integrator; the dev tip after it is the candidate of the next complete
gate. Hand-back as soon as it is repaired (within about 1.5 h).

## Failure/idempotency/security cases

A test that passes without the notification (the poll alone would satisfy it) is not a repair. The lane stops its own containers
and kills no process it did not start, by confirmed PID.

## Rollback / feature flag

Revert the merge. Tests only; no flag.
