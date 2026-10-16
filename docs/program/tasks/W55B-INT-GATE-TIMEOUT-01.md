# Task W55B-INT-GATE-TIMEOUT-01 — bound the serving-carrier gate wait to the real W55b preparation path

## Outcome

The serving-lifespan composition test allows the recorded provider to be reached after the two deterministic W55b preparation stages, while a timeout reports the Run's public state and completed stages.

## Depends on

- `W54-WORKER-01` (the durable carrier and the original D-152 queue isolation).
- `W55B-SEAL-01` (the frozen W55b contract and `0021_portal_bundles`).
- `W55B-INT-CLOSE` (the completed development candidate under `R-125`).

## Frozen inputs

- Base commit: `6d63802ab465a0317839c9b57abd5e90f3d91769`.
- Domain candidate revision 12; API 47 paths / 54 operations / 123 schemas; error catalog 24.
- Analysis, comparison and event contracts as sealed by `W55B-SEAL-01`.
- Migration head: `0021_portal_bundles`.
- In the clean candidate's third full gate, the Run for project `prj_01M51W079RX6CMMF72DEP86Q5C` was claimed about one second after creation, then published. Read-only PostgreSQL evidence records `source_preparation` at 18,761 ms and `page_geometry_extraction` at 19,160 ms before `text_analysis` began. Their 37,921 ms total exceeds the test's 30-second wait. Across eight recorded runs in that gate database, these stages ranged 17,484–21,983 ms and 17,807–21,774 ms respectively.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the failed Run reached the provider after the 30-second test deadline
- captured_at: 2026-10-16
- command: `SELECT stage_id, metrics->>'duration_ms', started_at, finished_at FROM stage_result WHERE run_id = 'run_01M51W07FWNFJVXDA1HGG6N21C' ORDER BY started_at`
- captured_output:
  ```text
  source_preparation       18761  08:07:07.526  08:07:26.288 UTC
  page_geometry_extraction 19160  08:07:26.296  08:07:45.457 UTC
  text_analysis            11940  08:07:45.520  08:07:45.602 UTC
  ```
- interpretation: the first two stages consumed 37,921 ms before the gated provider call; the Run was ultimately published when the failing test released its gate.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tests/integration/composition/test_the_run_leaves_the_request_thread.py`
- `docs/program/tasks/W55B-INT-GATE-TIMEOUT-01.md`
- `docs/program/W55B-INT-GATE-TIMEOUT-01.md`

## Forbidden hotspots

- `contracts/**`, migrations, root dependencies and lockfiles, composition root, global styles, other tests and fixtures, `CURRENT_STATE.md`, provider recordings, release refs and tags.

## Non-goals

- No production scheduler, extraction, geometry or provider change.
- No broader timeout changes, test-data reset, contract reseal or deployment.

## Deliverables

- One test assertion with a 120-second event deadline and useful timeout state.
- A short evidence and verification report.

## Required tests

- Container-free `pytest --collect-only` for the changed test.
- The changed test against the integrator's dedicated PostgreSQL/S3 lane when released for use.
- Contract/governance checks and `git diff --check`.
- The integrator runs a complete `make gate` on the resulting exact candidate before `origin/main` publication.

## Integration contract

The event still proves the worker reached the recorded adapter before the test reads `running`. The 120-second bound only accommodates deterministic preparation before that event. A missed bound reports the Run's public status for triage. No runtime or API behavior changes.

## Failure/idempotency/security cases

- The wait remains bounded; a genuinely stuck or failed Run fails the test.
- The test's existing `finally` releases its gate and restores the parked queue rows after a failure.
- The diagnostic uses the authenticated public status seam already exercised by this test.

## Rollback / feature flag

- Revert this test-only commit; no feature flag, data migration or recovery action is needed.

## Handoff

- No push, tag or service start by this task. The integrator cherry-picks the clean commit, starts the dedicated service lane, and verifies the exact resulting candidate.
