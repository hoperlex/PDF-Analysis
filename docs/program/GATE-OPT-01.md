# GATE-OPT-01 — separate development tiers and instrument the complete gate

Task: `docs/program/tasks/GATE-OPT-01.md`. Frozen base: `origin/dev`
`8069220909e40c39e2329d5f5cb9585a5a5714ec`, confirmed by
`git ls-remote --heads origin dev` on 2026-10-15. Worktree:
`task/gate-opt-01`. This report does not claim a complete gate or beta acceptance.

## Result

`make gate-fast` performs whitespace, frontend lint and typecheck, all current
`tests/unit` tests and the two basic API prose/surface guards. It requires this checkout's
`.venv` and `web/node_modules`, and prints `GATE FAST OK` only after every check passes.
It is local feedback, not a release result.

`make gate-affected BASE=<full SHA>` delegates to the existing R-70
`light-acceptance` target. Its selector checks a clean tree and ancestor SHA, refuses
unknown/full-gate-risk paths, selects backend integration suites, and requires a live
PC-01 journey for changed screens. The new marker `GATE AFFECTED OK` follows the existing
`LIGHT ACCEPTANCE OK` only on success. This is the existing acceptance policy under a
more descriptive command name; the selector's semantics are unchanged.

The complete `make gate` keeps `gate-preflight → gate-slot → gate-static → foundation →
battery` and its literal final `GATE OK` line. Timers now cover those stages, each
foundation command, frontend lint/typecheck/tests, contract tests and the two battery
parts. Failure timing preserves the command's status. Python suites print pytest's
`--durations=20` report without changing collected tests or the three CP-00 exclusions.
The final success line still comes after timing output.

## Measurements and checks

| Check | Result |
| --- | --- |
| `git ls-remote --heads origin dev` | exact frozen SHA above |
| `make -n gate-fast gate-affected gate` | exit 0; graph parses |
| focused pytest: `test_gate_tiers.py`, `test_light_acceptance_command.py`, `test_gate_host.py` | 46 passed in 6.00 s; test harness used the parent checkout's Python 3.12.3 / pytest 9.1.1 |
| `pytest -q --durations=20 tests/unit` plus the two API prose/surface guard files | 78 passed in 11.57 s; slowest calls 4.88 s and 3.20 s; five pre-existing pytest temporary-cleanup warnings |
| `make gate-preflight` in this unprovisioned worktree | refused, make exit 2; `GATE TIMING preflight 0s exit=1`; no `GATE OK` |
| `make gate-fast` in this unprovisioned worktree | refused, make exit 2: `.venv/bin/python` missing; no fast success marker |
| `git diff --check` | exit 0 |

`scripts/gate_host.py preflight`, invoked with the parent Python only to diagnose the
worktree, reported missing `.venv`, `web/node_modules`, corpus link and `.env`; the
working tree was also uncommitted. Its Docker probe failed because this execution
environment's snap-confined Docker lacks `cap_dac_override`. The worktree filesystem
had 6,475 MiB available at 2026-10-15 12:32:46 UTC, just above its 6,144 MiB floor;
earlier in the session it showed about 4.1 GiB. This is not a valid environment for
an uncontended complete-gate timing baseline.

No measured 1–3 or 3–10 minute budget is claimed for the new targets. The affected tier
can run a full frontend suite, backend integration directories and a live journey; the
budget depends on the diff and host. The next complete gate on a provisioned exact
candidate will provide comparable stage and top-20 Python durations. Capture its full
log and take the verdict only from its literal `GATE OK` line.

## Deferred performance decisions

- Docker contention is already handled within this repository by `GATE-PKG-01`'s shared
  slot. Its memory floor cannot reserve resources used by unrelated host processes.
- The local composition uses `docker compose up --detach --wait`; cold image acquisition
  and warm starts require separate measurements before cache changes.
- Database integration tests intentionally migrate isolated empty databases. Reusing a
  schema needs a separate proof that it preserves fresh-migration and isolation claims.
- Parallel test execution needs resource-isolation evidence before changing the complete
  gate. No suite, real-service check or external acceptance step was removed here.

## Integration and limits

The task changes only `Makefile`, its own task/report and `test_gate_tiers.py`.
`contracts/**`, migrations, dependencies/locks, composition roots, global styles,
runtime product code and deployment files are untouched. The branch has no ref-push,
tag or deployment authority. Under `R-135`, the complete gate for the development-only
code series runs after the planned beta code on a separately prepared clean candidate;
that integration must include this Makefile change and must not infer `GATE OK` from the
focused checks above. Rollback is a revert of this task's four files; no data migration.
