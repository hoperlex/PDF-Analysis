# CMP-C2-GATE-FE-01 — frontend gate worker cadence

Task: [`tasks/CMP-C2-GATE-FE-01.md`](tasks/CMP-C2-GATE-FE-01.md). Base `ac5ee5cc`; frozen API `1.11.0` (176 paths, 198 operations, 517 schemas), migration head `0040_comparison_ai_reports`.

## Result

The second complete C2 gate reached Vitest and stopped at `Timeout calling "onTaskUpdate"` after 70 green assertions from three guard files. The failure was worker RPC timing, not an assertion failure; its log is `/tmp/cmp-c2-gate-second.log`. The first gate had passed all 3,651 frontend tests but then found a task-record contract error, which `CMP-C2-GOV-01` corrected.

`rendered-language.guard.test.ts` already computes `found = offencesOnScreens()` once for its preceding coverage and stale-exception assertions. Its final `finds none at all` assertion now reads that same complete map instead of rendering the entire matrix a second time. The focused run measured the file at 35 seconds, versus 103 seconds in the failed gate.

`lazy-boundary.guard.test.ts` still checks the screen count and the measured pair counts for both palettes against the same baseline. It runs the light and dark censuses in separate tests and calls the existing `yieldToRunnerAfterEachTest()` helper, so the worker receives an I/O turn between the two CPU-heavy checks. The focused run measured 33 and 38 seconds for them. In the full frontend run, two contrast tests took 53 and 52 seconds, near the same 60-second RPC limit. `contrast.test.ts` now yields to the worker between each test's light and dark measurements. No baseline, screen list, assertion, test timeout, Vitest configuration or product behavior changed.

## Checks

| Check | Result |
| --- | --- |
| `npm --prefix web run lint` | passed |
| `npm --prefix web run typecheck` | passed |
| focused Vitest on the two edited guards | 2 files, 52 tests passed; no RPC error |
| focused Vitest on the final contrast guard | 1 file, 20 tests passed; no RPC error |
| full `npm --prefix web test` in the default sandbox, before the contrast yield | 216 files and 3,646 assertions passed; 7 assertions in three other files failed solely on `spawnSync ... EPERM` or `listen EPERM 127.0.0.1` (sandbox subprocess/socket restrictions) |
| those three subprocess/socket files with elevated local permissions | 3 files, 54 tests passed |
| final full frontend run | assigned to the exact-commit `make gate` with its local-process permissions |
| `tests/contract/program/test_wave_governance.py` | 16 passed |
| `git diff --check` | clean |

## Contracts, limits and handoff

No API, migration, source, styles, dependencies, lockfile, composition root or infrastructure changed. The test guards retain their full coverage but remain CPU-expensive: a future screen census that makes one test exceed 60 seconds needs another measured split. The integration task must run a new complete `make gate` on the exact clean commit that contains this repair; this repair has no remote publication authority.
