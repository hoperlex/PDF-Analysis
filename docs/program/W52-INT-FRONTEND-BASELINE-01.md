# W52-INT-FRONTEND-BASELINE-01 — current frontend diagnostic

Measured on 2026-10-08 from clean `integration/w51` and matching local
`origin/dev` at `defade8177ed808049425e15f741a8424997d0c3`.

| Command | Result |
| --- | --- |
| `npm --prefix web run typecheck` | exit 0 |
| `npm --prefix web run lint -- --quiet` | exit 0 |
| `npm --prefix web test -- --run`, with child processes permitted | exit 0; 109 test files, 1,712 tests passed |

An initial Vitest run in the restricted sandbox reported six failures:
four `eslint-boundary` fixtures could not spawn `eslint` (`EPERM`), and two
`query-key-shape` fixtures could not get their expected `tsc` diagnostics.
The same command rerun with child-process execution permitted passed all six
and the complete suite. The restricted run is not a product failure. The
seven failures reported by `W52-INT-VALIDATE-01` belonged to the earlier
`e2cfea92` tree; the current run is a new measurement, not a correction
claim about that historical result.

The focused programme governance and prose/surface suite passed 93 tests on
the documentation candidate; `git diff --check` passed. These checks do not
substitute for light acceptance or the complete gate.

This diagnostic does not run the Python battery, service-backed PC-01
journey, independent QA, manual acceptance or complete `make gate`. D-137
through D-140 remain open. W52 still needs `W52-RULE-01` and
`W52-FREEZE-01` before new lanes are dispatched.

Changed tracked files for this task: its task and report, and bounded
`CURRENT_STATE.md` and D-140 addenda. No contract, migration, dependency,
lock, composition-root, global-style, product code or test path changes.
The integrator checks the docs candidate and remote ancestry before any
development-line publication. No `origin/main`, tag or deployment action is
authorized here.
