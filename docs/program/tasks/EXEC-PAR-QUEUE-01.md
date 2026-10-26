# Task EXEC-PAR-QUEUE-01 — worker slots and a per-executor limit in the claim

task_id: EXEC-PAR-QUEUE-01

## Outcome

The worker can run several runs at once. `AUDITMANAGER_WORKER_SLOTS` (an integer from 1 to 16,
default `1`, invalid value = the process refuses to start; no silent default) sets the slot count.
A connection has a limit of **one** simultaneously active run: the claim skips a queued job whose
run is frozen to a connection that already has an active run, so a slot is never spent waiting
for a busy executor, and the next queued job for a free executor runs instead. Runs without a
connection (the `environment` source) are not limited. With the default `1` behaviour is today's.

## Depends on

- `EXEC-HTTP-01` — completed (`audit_run.connection_revision_id`).
- `EXEC-PAR-DECISION-01` — the decision record (4 slots chosen; default stays 1; limit 1).
- It does **not** depend on `EXEC-PAR-START-01`: a run is frozen to a revision either way.

## Frozen inputs

- base commit: `f6ee66ee73d0bfb7e87cc6a057d010be8d1df4e5` (`origin/main`); the lane starts from
  branch `plan/exec-parallel-runs`, which adds documents only;
- shared contract `1.5.0`, migration head `0032_ar_v3_run_group`: **neither changes**;
- facts read on this base: `bootstrap/composition.py:225` fixes `slots=1`; `workers/service.py:200,236`
  already sizes a `ThreadPoolExecutor(max_workers=slots)`; `jobs/repository.py` `_NEXT_JOB` claims by
  priority and age with `FOR UPDATE OF r SKIP LOCKED` and knows nothing about connections.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the composition root fixes one slot
- captured_at: 2026-10-26
- command: `git grep -n "slots=1" f6ee66ee73d0bfb7e87cc6a057d010be8d1df4e5 -- src/auditmanager/bootstrap/composition.py`
- captured_output:
  ```text
  f6ee66ee73d0bfb7e87cc6a057d010be8d1df4e5:src/auditmanager/bootstrap/composition.py:225:        slots=1,
  ```
- interpretation: the slot count is a literal in the composition root; this lane owns that slot.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

The lane commits to its own branch only. It does not merge, push or tag.

## Allowed paths

Derive the exact set from the tree (list the directories first) and record every path beyond this
list, with its reason, in the report.

- `src/auditmanager/jobs/**`
- `src/auditmanager/workers/**`
- `src/auditmanager/bootstrap/composition.py` and the settings module that reads worker environment variables
- `infra/deploy/compose.server.yml`, `infra/deploy/env/alpha.env.example` (pass the variable by name; default `1`)
- `tests/unit/jobs/**`, `tests/unit/workers/**`, `tests/integration/jobs/**`, `tests/integration/workers/**`,
  `tests/integration/composition/**`
- `docs/program/PROTOTYPE_PROFILE.md`, `docs/program/DEPLOYMENT_RUNBOOK.md` (the concurrency statement and the setting only)
- `docs/program/tasks/EXEC-PAR-QUEUE-01.md`, `docs/program/EXEC-PAR-QUEUE-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**` (if the claim needs an index, stop and report with the query
  plan instead of adding a migration), root dependency and lock files;
- `src/auditmanager/executors/**`, `src/auditmanager/runs/**`, `src/auditmanager/api/**`
  (owned by `EXEC-PAR-START-01`); `web/**`; global styles; `docs/program/CURRENT_STATE.md`; refs, tags, the stand.

## Non-goals

No executor field on runs, no UI, no change to how a connection is chosen. No parking of Attempts.
No change to the Attempt watchdog, the lease, or the drain time. No fairness policy beyond today's
priority-then-age order among the jobs that are allowed to run.

## Work

1. **Setting.** Read `AUDITMANAGER_WORKER_SLOTS` once at startup with strict parsing (integer
   1–16); pass it to `WorkerService(slots=…)`. Anything else stops the process with a clear message.
2. **Claim with a per-connection limit.** A queued job is claimable only if its run's connection (via
   `audit_run.connection_revision_id` → the revision's `connection_id`) has no other active run. Define
   "active" from the job/lease states in `jobs/repository.py`, not from a guess, and say which states
   in the report. The check and the claim must be **atomic**: two workers (or two slots) claiming at
   once cannot both take runs of one connection. Use a per-connection lock taken inside the claim
   transaction (an advisory transaction lock keyed on the connection id, or a row lock on
   `executor_connection`) and re-check after taking it; a candidate that loses the check is skipped and
   the next candidate is tried, with a bounded number of tries.
3. **Drain and reclaim.** Show by test that a drain waits for every run in flight and that a reclaimed
   (expired-lease) run of a limited connection does not let a second one start before it is released.
4. **Docs.** Replace the «one run at a time» statement where it is written with the setting and the
   default; do not touch `CURRENT_STATE.md`.

## Deliverables

The setting, the claim, the tests, the compose/env pass-through, the doc lines, and the report
`docs/program/EXEC-PAR-QUEUE-01.md`.

## Required tests

- command: `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/jobs tests/unit/workers tests/contract`
  with the gate's contract ignores (`--ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py`); expected: pass.
- The claim is SQL and needs a database. Start **one** PostgreSQL container from the image already
  present on the host (do not pull, build or start MinIO), on a free loopback port, named
  `exec-par-queue-pg-<your task id>`; run `tests/integration/jobs` and `tests/integration/workers`
  against it; remove **that container by its exact name** at the end. If these tests cannot run
  without more than Postgres, list them as not run. Never touch another container or database.
- a **concurrent-claim test** (two threads, one connection, two queued runs, two slots): exactly one
  runs at a time; and a different-connection pair runs together. It must fail when the lock is removed.
- command: `git diff --check`; expected: exit 0.

## Integration contract

With the setting unset or `1`, the claim returns the same job as today (the order is unchanged). With
`N > 1`, up to `N` runs are active, and at most one per connection. A run frozen to no connection is
never limited. Nothing is added to the API or to the database schema.

## Failure/idempotency/security cases

- an invalid or out-of-range setting stops the process; it never becomes `1` silently;
- a claim that loses the per-connection check leaves the job queued and unchanged;
- a worker killed mid-run: the lease expires and the reclaim obeys the same limit;
- a connection archived while its run is active: the run finishes; no new run for it is claimed
  because none could be started (that is `EXEC-PAR-START-01`'s refusal).

## Rollback / feature flag

Set `AUDITMANAGER_WORKER_SLOTS=1` (or unset it): today's behaviour. The per-connection check with
one slot is inert.

## Handoff

changed files with reasons; commands and results; the states that count as «active»; the mutation
table; known limits (host load, PDFium lock serialisation measured or not); the instruction to the
integrator; proof the forbidden hotspots are untouched.
