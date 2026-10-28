# Task CMP-PQ-ISOLATION-01 — the `page_profile` queue suite does not depend on the rows other integration directories leave in a shared database

## Outcome
`tests/integration/comparison/profile_queue/` passes (its 18 tests, and the 2 that prove the isolation) on a database that also holds rows left by other
integration directories. Today it passes only on a fresh database: eleven of the eighteen end in
`the runner claimed nothing: a gate is shut or no item is due` (`conftest.py`, `Lane.claim`) as soon as a Run is
claimable anywhere in the database, because the comparison queue yields to any claimable Run by design (strict
priority, `ClaimGates` / `default_gates`, `docs/program/CMP-WORK-01.md`). The lane's runner is built with gates whose
Run-priority read is scoped to the lane's own projects, and every read the suite makes of the queue (a claim, a reclaim, a
count) is scoped to the items the test enqueued, so a foreign Run, a foreign queued item or a foreign expired lease
cannot change a verdict. What the suite proves about the `page_profile` handler (the build stops between pages, a lost
lease is reclaimed and resumed, a child that never started retries, the budget is spent, a payload of another shape
fails at once, the version is built through the worker's own `build_comparison_work`) is unchanged; the strict priority
of Runs over comparison work stays proved by `tests/integration/comparison/work/test_claim_gates.py`.

## Depends on
- CMP-PROFILE-QUEUE-01 (merged on `integration/compare-modules`): the suite and its `Lane` helper
- CMP-WORK-01 (merged): `ClaimGates`, `ComparisonWorkRunner(gates=...)`, `ComparisonWorkRepository`

## Frozen inputs
- domain contract: `contracts/domain/v1/**` unchanged
- API contract: `contracts/api/v1/openapi.json` `1.9.0`, 115 paths / 130 operations / 351 schemas, 27 error codes (unchanged)
- analysis/comparison/event contract: ADR-0025 decisions 4, 6, 7 (the queue yields to a claimable Run; an item is leased by
  the strongest-first pick; a reclaim fences every expired lease), unchanged
- migration head: `0038_comparison_foundation` (not touched)
- base commit: `eca5f9fa` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the base is `eca5f9fa` on `integration/compare-modules`: contract `1.9.0`, 115 / 130 / 351, 27 error codes, `VERSION` `0.9.0`, head `0038_comparison_foundation`; the lane printed them before any edit and would have STOPPED if they differed

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-28
- command: `.venv/bin/python -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; cat VERSION; grep -n '^revision: str' db/migrations/versions/20261028_0038_comparison_foundation.py; git rev-parse HEAD`
- captured_output:
  ```text
  contract 1.9.0 115 paths 130 operations 351 schemas 27 error codes
  0.9.0
  81:revision: str = "0038_comparison_foundation"
  eca5f9fa4e0bc8bfd7a06104f4fba132db8c6044
  ```
- interpretation: equal to the premise of the wave brief, so the lane did not STOP

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `tests/integration/comparison/profile_queue/**`
- `tests/unit/comparison/work/test_composition_unit.py`
- `tests/unit/runs/test_serving_start_sweeps_temporaries.py`
- `docs/program/CMP-PQ-ISOLATION-01.md`
- `docs/program/tasks/CMP-PQ-ISOLATION-01.md`

The two unit files were added to the lane by message of the PW5 integrator on 2026-10-28 (tests only, still no change
under `src/`): both were red on the integration tree for reasons outside this lane's first brief.

## Lane resources
- foundation_instance: `auditmanager-cmp-pq-isolation-01`
- postgres_port: `57830`
- s3_api_port: `61830`
- s3_console_port: `61831`
- postgres_db: `auditmanager_cmp_pq_isolation_01`
- s3_bucket: `auditmanager-cmp-pq-isolation-01`

## Forbidden hotspots
- everything under `src/**` (no production change: the defect is in the suite, not in the queue)
- `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`
- `tests/integration/comparison/work/**` (the owner of the priority proof), `tests/support/**`, any other `conftest.py`
- `web/**`, global styles

## Non-goals
- changing the strict priority of Runs, the gates, the pick or the reclaim (all of CMP-WORK-01)
- parking, pausing or otherwise changing rows other directories left (the `quiet_runs` fixture of `comparison/work`
  does that; this suite must not touch what is not its own)
- a shared fixture for the other comparison directories (they decide for themselves)

## Deliverables
- `tests/integration/comparison/profile_queue/conftest.py`: the lane's runner built with a Run-priority gate scoped to the
  lane's projects (`Lane.gates`, `Lane.worker_runner`); a claim that cannot lease a foreign item (`Lane.claim`); a reclaim
  count scoped to the lane's attempts (`Lane.reclaim`); the helpers that plant foreign rows
- the three existing test files changed only where they read the queue globally
- `tests/integration/comparison/profile_queue/test_foreign_rows_do_not_change_the_verdict.py`: two tests that plant a foreign
  Run, a stronger foreign item and a foreign expired lease, so the isolation is shown on any database
- `tests/unit/comparison/work/test_composition_unit.py`: the bundle test asserts what it means (every factory, patched or
  appended by the root, receives the one bundle; the kinds it patched are registered) and not a closed set of kinds
- `tests/unit/runs/test_serving_start_sweeps_temporaries.py`: the stand-in `Runtime` carries `comparison_work = None`
- the report `docs/program/CMP-PQ-ISOLATION-01.md`

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/integration/comparison/profile_queue`
- expected: 20 passed (the 18 of the base and the two new) on a fresh database; 20 passed again, without a reset, after an integration file that leaves queued Runs (`tests/integration/composition/test_the_run_leaves_the_request_thread.py`) has run against the same database; the base tree's four files fail 11 of 18 on that database (the reproduction)
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit` and the same for `tests/contract` minus `test_cp00_candidate.py`, `test_cp00_final_state.py`, `test_validate_bootstrap.py`
- expected: no failure in `tests/unit`; in `tests/contract` only what the base already fails (`test_wave_governance.py` on `docs/program/tasks/CMP-SEAL-C1.md`)

## Integration contract
The integrator can rely on: nothing outside `tests/integration/comparison/profile_queue/` changed; the suite no longer needs
a quiet database, so it can run in any order with the other integration directories on one lane database; the guards it
adds each have a quoted mutation under which they fail.

## Failure/idempotency/security cases
- a Run of the lane's own projects that is claimable still shuts the lane's gate (the scoped gate is a read of the real
  `job` / `audit_run` tables, not a constant); a Job that is not due does not
- a foreign `page_profile` item that is queued, even a stronger one, is neither leased nor changed by the suite
- a foreign expired lease is fenced by the worker's reclaim (as it would be in production) but is not counted as the lane's
- the suite deletes only the rows of the projects it seeded or planted (the Jobs and Runs it plants are deleted too)

## Rollback / feature flag
Not applicable: tests only. Rollback is not merging the lane.

## Handoff
- changed files: the four files of `tests/integration/comparison/profile_queue/` (`conftest.py`, two existing tests, one new test), the two unit files named above, this file and `docs/program/CMP-PQ-ISOLATION-01.md`; nothing under `src/`
- commands/results: profile_queue 18 passed (base, fresh) / 20 passed (lane, fresh) / 20 passed (lane, 4 foreign queued Jobs, no reset) / 11 failed + 7 passed (base files, same database); `tests/unit` 4313 passed, 76 skipped, 0 failed; `tests/contract` minus the three `D-220` files 1309 passed, 1 failed (`CMP-SEAL-C1.md`, red on the base); the table and the mutations are in the report
- known limits: the claim fence holds a row lock for one claim; the pause gate is the real one; see the report
- integration notes: no wiring or `src/` file touched, so no merge-order constraint; the stack (3 containers, network, 2 volumes) was removed
