# Task GATE-COST-STAND-01 — remove an artificial stand-copy test wait

task_id: GATE-COST-STAND-01

## Outcome

The `database-ready` guard case in the container-free stand-copy suite still
executes the readiness probe, refuses when it fails, and goes past that exact
refusal when the guard is removed, while its test-only wait takes fewer seconds.
The complete file retains all 147 collected cases and its previous outcome.

## Depends on

- `GATE-SUITE-AUDIT-01` — completed local suite inventory and cost review.
- `GATE-OPT-INT-01` — completed local integration of the timed gate.

## Frozen inputs

- base commit: `19658de9e1dacbaa8a944489249a1153518af377`
- API: 47 paths / 54 operations / 124 schemas; error catalog: 25
- domain candidate: revision 13 / 32 identities
- migration head: `0022_findings_v2`; product version: `0.6.0`
- analysis/comparison/event contracts: unchanged
- `R-135`: complete gate deferred to the exact final beta candidate

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the isolated readiness-failure case spends time in the test's wait

### P-01 — bounded baseline

- captured_at: 2026-10-15
- command: `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q --durations=20 tests/integration/composition/test_stand_copy_refusals.py`
- captured_output:
  ```text
  7.92s call tests/integration/composition/test_stand_copy_refusals.py::test_each_guard_refuses_and_its_deletion_stops_the_refusal[restore-test.sh:database-ready]
  146 passed, 1 skipped, 5 warnings in 75.44s (0:01:15)
  ```
- interpretation: one full file passed on the base; this is not a complete
  project gate or a stable whole-file speed baseline under changing host load.

### P-02 — the wait is controlled only by the test environment

- captured_at: 2026-10-15
- command: `rg -n 'STAND_COPY_RESTORE_READY_SECONDS|database-ready' tests/integration/composition/test_stand_copy_refusals.py scripts/stand-copy/restore-test.sh`
- captured_output:
  ```text
  tests/integration/composition/test_stand_copy_refusals.py:470:        STAND_COPY_RESTORE_READY_SECONDS="2",
  tests/integration/composition/test_stand_copy_refusals.py:809:    ("restore-test.sh", "database-ready"): Case(_restore_case(state={"ready": False})),
  scripts/stand-copy/restore-test.sh:44:READY_SECONDS="${STAND_COPY_RESTORE_READY_SECONDS:-180}"
  scripts/stand-copy/restore-test.sh:154:# >>> guard: database-ready
  ```
- interpretation: a case-specific zero-second wait still enters the readiness
  loop once; the test must assert that the probe actually ran on both variants.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tests/integration/composition/test_stand_copy_refusals.py`
- `docs/program/tasks/GATE-COST-STAND-01.md`
- `docs/program/GATE-COST-STAND-01.md`
- `.local/handoff/gate-optimization-2026-10-15.md`

## Forbidden hotspots

- `scripts/stand-copy/**`, `infra/deploy/**`, `Makefile`, `contracts/**`
- migrations, root dependency/lock files, composition roots, global styles
- runtime code, other tests/fixtures, release refs, tags and deployment host

## Non-goals

- Shortening production readiness policy or changing a deploy script.
- Deleting guard, mutation or live PostgreSQL assertions.
- Complete `make gate`, frontend installation or publication under `R-135`.

## Deliverables

- One case-specific test timeout and an assertion that each staged variant
  attempted the readiness probe.
- Before/after targeted timing and complete-file result in a dated report.

## Required tests

- Repeat the exact `database-ready` case before and after the change with
  `--durations=20`; record individual times and outcomes.
- Run the complete `test_stand_copy_refusals.py` file after the change and
  confirm 146 passed / 1 intentionally skipped, with 147 collected.
- `governance_findings()` for this task is empty; `git diff --check` passes;
  all changed paths are in this task's allowlist.

## Integration contract

Only the test's fake readiness wait changes. The real script, stub's response,
guard refusal, deletion mutation and live-window test retain their meaning.
The final beta candidate still requires the complete gate and new timings.

## Failure, idempotency and security

If the probe is not called or the guard fails to distinguish original and
mutant, the test fails. The test uses temporary files and fake Docker; no
container, network, data migration or external publication is started.

## Rollback / feature flag

Revert this test-only task; no flag, runtime behavior or data rollback exists.

## Handoff

- changed files: Allowed paths
- commands/results: `docs/program/GATE-COST-STAND-01.md`
- known limits: no full gate and no live PostgreSQL window
- integration notes: do not present a test-file speedup as beta gate evidence
