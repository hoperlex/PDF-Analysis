# Task CMP-C2-GATE-FE-01 — keep long frontend guards within Vitest worker RPC cadence

## Outcome
The two frontend guard tests that ran one synchronous assertion for 70–77 seconds retain their full coverage while no one assertion blocks the Vitest worker RPC for 60 seconds. The complete C2 gate can then run on a new exact clean commit.

## Depends on
- CMP-C2-FIX-01
- CMP-C2-GOV-01

## Frozen inputs
- domain contract: ADR-0025 and `CMP-SEAL-C2`
- API contract: `1.11.0`, 176 paths / 198 operations / 517 schemas
- analysis/comparison/event contract: unchanged from `CMP-SEAL-C2`
- migration head: `0040_comparison_ai_reports`
- base commit: `ac5ee5cc6d593bdb1089ad1f566494ec83794da3`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: P-01 and P-02 show a clean sealed candidate and the exact gate failure.

### P-01 — clean C2 candidate
- captured_at: 2026-10-29
- command: `git status --short; git rev-parse HEAD`
- captured_output:
  ```text
  ac5ee5cc6d593bdb1089ad1f566494ec83794da3
  ```
- interpretation: the failed gate was on the clean integration candidate.

### P-02 — frontend RPC refusal after green assertions
- captured_at: 2026-10-29
- command: `rg -n 'rendered-language|lazy-boundary|Timeout calling|Test Files|Tests  |GATE: the frontend' /tmp/cmp-c2-gate-second.log`
- captured_output:
  ```text
  14: ✓ tests/guards/rendered-language.guard.test.ts (26 tests) 102640ms
  21: ✓ tests/guards/lazy-boundary.guard.test.ts (24 tests) 76856ms
  29:Error: [vitest-worker]: Timeout calling "onTaskUpdate"
  38: Test Files  3 passed (219)
  39:      Tests  70 passed (70)
  44:GATE: the frontend suite failed.
  ```
- interpretation: a single guard test ran about 70 seconds and another about 77 seconds; the worker's 60-second RPC timeout stopped the suite without an assertion failure. The first gate on `adcac54f` passed all 3,651 Vitest tests, so the failure is timing-dependent.

### P-03 — the remaining contrast test is close to the same limit
- captured_at: 2026-10-29
- command: `rg -n 'names every selector it declined|produces the same pairs' /tmp/cmp-c2-gate-fe-full-web.log`
- captured_output:
  ```text
  12:   ✓ the census is taken over rendered screens, not over a list > names every selector it declined to evaluate, so a skipped rule is not a passing one  53400ms
  15:   ✓ the census is taken over rendered screens, not over a list > produces the same pairs, and asks the same threshold of each, in both palettes  52029ms
  ```
- interpretation: both assertions combine independent light and dark measurements in one synchronous test, leaving less than eight seconds of margin to the worker RPC limit. This is the same measured risk, within the current repair task.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `web/tests/guards/rendered-language.guard.test.ts`
- `web/tests/guards/lazy-boundary.guard.test.ts`
- `web/tests/unit/styles/contrast.test.ts`
- `docs/program/tasks/CMP-C2-GATE-FE-01.md`
- `docs/program/CMP-C2-GATE-FE-01.md`

## Forbidden hotspots
- product web source, global styles, `web/vitest.config.ts`, all other tests
- `contracts/**`, `db/migrations/**`, root dependency and lock files, composition root, infrastructure, remote refs

## Non-goals
- no raised timeout, skipped guard, lower baseline, narrowed screen census or changed product behavior
- no publication to `origin/dev` or `origin/main` from this repair task

## Deliverables
- reuse the existing complete rendered-language census in its final assertion instead of rendering the same matrix again
- split the lazy-boundary light and dark census assertions into separate tests with a worker yield between them, preserving both baseline values and the screen-count assertion
- yield to the worker between the contrast guard's paired-palette censuses; keep the same rendered screens, unsupported-selector list and pair/threshold comparison
- a repair report with command results, limits and forbidden-hotspot proof

## Required tests
- `npm --prefix web run lint` and `npm --prefix web run typecheck`
- focused Vitest on all touched guard files, then the full `npm --prefix web test` in one invocation (the integration gate may supply the final full run)
- `git diff --check`; the integration task reruns complete `make gate` on the exact clean repaired SHA

## Integration contract
The guard suite still derives its rendered screens and checks every Latin token and both palette pair counts. Only duplicate work and per-test scheduling change. The repair commit belongs to the C2 integration candidate; `CMP-WAVE-C2-INT` alone owns any `origin/dev` push after a new full green gate.

## Failure/idempotency/security cases
- if a guard still has an assertion above the worker's 60-second RPC window, split that computation without removing coverage and rerun the focused and full frontend suites
- a red assertion remains a red assertion; no retry or timeout increase masks it
- the comparison module flag remains `none` by default

## Rollback / feature flag
Tests only. Revert this repair commit if its assertions regress; there is no runtime flag or data migration.

## Handoff
- changed files: `web/tests/guards/rendered-language.guard.test.ts`, `web/tests/guards/lazy-boundary.guard.test.ts`, `web/tests/unit/styles/contrast.test.ts`, this task file and `docs/program/CMP-C2-GATE-FE-01.md`.
- commands/results: web lint and typecheck passed; focused Vitest on the language and lazy guards 52 passed, final contrast guard 20 passed; the three subprocess/socket tests that the default sandbox denied passed 54/54 with local-process permissions; governance 16 passed; `git diff --check` clean. The full frontend and backend suite is assigned to the exact-commit integration gate.
- contracts: unchanged; frozen API `1.11.0`, migration head `0040_comparison_ai_reports`.
- known limits: the guards still do CPU-heavy work; a future single uninterrupted measurement approaching 60 seconds requires another measured yield or split. A default-sandbox full Vitest run is not an acceptance result because `spawnSync` and `127.0.0.1` are denied there.
- integration notes: commit this tests-only repair, then run full `make gate` on a clean SHA with local-process permissions. Only `CMP-WAVE-C2-INT` may publish that SHA to `origin/dev`; no `origin/main` action is authorized.
