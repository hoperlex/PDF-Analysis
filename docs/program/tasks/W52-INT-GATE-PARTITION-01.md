# Task W52-INT-GATE-PARTITION-01 — stop running foundation twice in gate

task_id: W52-INT-GATE-PARTITION-01

## Outcome

`make gate` keeps its separate cross-provider foundation suite and does not run
that same suite again in the canonical Python battery. All other battery test IDs
remain in the selected set.

## Depends on

- `W52-INT-HOTFIX-BACKPORT-01` — completed on `origin/dev` at
  `2c2e7d8a75d360bb9dc6cc0fc9916c55892886c5`.

## Frozen inputs

- Exact development base `2c2e7d8a75d360bb9dc6cc0fc9916c55892886c5`.
- Domain candidate revision 9 / 29 opaque identities; API 27 paths / 34 operations /
  77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`.
- `docs/program/dispatch/W52-PLAN.md` §3.7 item 1, read from the planning-owned
  `plan/roadmap-to-beta` worktree. This is one independent code preparation, not
  `W52-GATE-01` completion or a W52 freeze.
- Owner's code-first direction: focused/basic checks and lint; complete gates and QA
  remain D-139/D-140.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the current gate names foundation as a prerequisite and its battery
  selects `tests` without excluding the foundation directory.

### P-01 — duplicate selection

- captured_at: 2026-10-08
- command: `rg -n '^(foundation:|gate:)|tests --ignore=tests/checkpoint|run_suite "\$\$QA_SUITE"' Makefile && git rev-parse HEAD && git status --short`
- captured_output:
  ```text
  485:    tests --ignore=tests/checkpoint \
  969:    run_suite "$$QA_SUITE"
  973:foundation: up check-services migrate check-db check-storage test-foundation
  1040:gate: foundation
  2c2e7d8a75d360bb9dc6cc0fc9916c55892886c5
  ```
- interpretation: the battery selects the foundation directory after the
  prerequisite has already executed it. No status line followed the SHA.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `Makefile` — `run_battery` selection and adjacent comment only
- `docs/program/tasks/W52-INT-GATE-PARTITION-01.md`
- `docs/program/W52-INT-GATE-PARTITION-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEBT_REGISTER.md`

## Forbidden hotspots

Everything else, especially the `foundation` and `gate` target bodies, contracts,
migrations, root dependency/lock files, composition root, global styles, test or
fixture code, and `origin/main`.

## Non-goals

No database-template optimization, xdist, impacted-test selection, fixture repair,
contract reseal, temporary stand, full gate, QA, release or tag. Those remain with
the frozen W52 gate lane or the deferred validation wave.

## Deliverables

- One explicit battery ignore for `tests/integration/foundation` while
  `test-foundation` remains in the foundation prerequisite.
- A collection comparison of all non-foundation IDs before and after the change,
  noting that the foundation suite deliberately refuses `--collect-only`.
- A report with focused checks and a clear D-140 status.

## Required tests

- Collect the battery outside foundation before and after, compare exact IDs.
  Do not bypass the foundation suite's `--collect-only` refusal.
- `tests/contract/test_alpha_acceptance_command.py`,
  `tests/contract/test_light_acceptance_command.py`, governance/prose tests,
  frontend lint and `git diff --check`.
- The complete JUnit parity/full gate remains deferred; no `GATE OK` claim.

## Integration contract

The gate's `foundation` dependency remains, and its `test-foundation` target
continues to execute the cross-provider suite. Only `run_battery`'s selection
changes. The integrator publishes a fast-forward `origin/dev` commit after
checks and exact remote-ref review. Later W52 freeze must remeasure this base.

## Failure/idempotency/security cases

- The ignore must be exact, never a broad `tests/integration` exclusion.
- A missing foundation suite must still fail in `test-foundation`; the battery
  never substitutes a collection-only pass for execution evidence.
- No credentials or service state are changed by this task.

## Rollback / feature flag

Revert this integration commit to restore the previous duplicate run. No
feature flag applies to test selection.

## Handoff

- Changed files, checks/results, contracts, risks, integration instruction
  and forbidden-hotspot proof are in `docs/program/W52-INT-GATE-PARTITION-01.md`.
