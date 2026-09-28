# Wave 47 — dispatch, 2026-09-29: what changed since the briefs were written

`W47-GATE.md` and `W47-PASS.md` were written on 2026-09-28 (`0803e27`), before wave 46's
sub-stages B and C. They stand. This page gives what is true at dispatch, and **where it
disagrees with a brief, this page wins.**

**The integrator:** `pdf-analysis-0c [548707]`, the same conversation as `pdf-analysis-4f [73faf8]`,
resumed. On 2026-09-28 the owner split the lock by wave: 47 was to go to `pdf-analysis-4f
[826d91]` from the wave-46 tag. That session has since exited, and on 2026-09-29 the owner told
this one *"продолжи разработку"*.

## Base and baseline

- **Base:** `alpha-w46` (`e47d657`), local. `origin` still ends at `alpha-w45`, and nothing is
  pushed without the owner.
- **Baseline, measured on `1196ca7`** (the gated candidate; `e47d657` changes only docs):
  `GATE OK`, battery **2516 passed / 5 skipped**, foundation **35**, frontend **1135 in 80 files**.
  `/root/w46-final-gate.log`. **Do not re-take a full baseline.** Account for your final counts
  against these, by test id.
- **Surface:** 17 paths / 20 operations / 61 schemas, 22 error codes, head `0011_document_section`.

## Corrections to the briefs

- `W47-PASS` P2 says *"wave 46 has just closed a reseal"*. It closed **three**, which makes the
  stop-and-report rule stronger, not weaker. **If P2's only honest mechanism needs a contract
  field or an error code, stop and report the options and their cost.**
- `W47-PASS` owns `web/src/**`. Wave 46 changed `web/src/widgets/dashboard/**`,
  `shared/api/query-keys.ts`, `features/create-project` and `widgets/project-sections`, and added
  `web/tests/guards/dashboard-invalidation.guard.test.ts`. **That guard maps every mutation hook
  under `features/**` to the dashboard key.** A new mutation hook (a password change, for example)
  must be added to its map, or the guard reddens. That is the guard working, not an obstacle.
- `W47-GATE` owns `tests/integration/composition/**`. Wave 46 added
  `test_dashboard_summary_over_a_fresh_deployment.py` there. Leave it alone unless a readiness check
  needs it.

## Discipline both briefs now carry (wave 46's lessons, each paid for)

- **Kill only by PID, and only processes confirmed to be your own descendants** (`pstree -p`,
  `readlink /proc/<pid>/cwd`). Never `pkill -f` and never `killall`: on 2026-09-28 a stream's
  `pkill -9 -f vitest` reached ten other sessions' test runs.
- **One full gate on the host at a time.** Before `make gate`, check `free -g` and confirm no other
  `make gate` whose cwd is under `/root/w4*` is running. If one is, wait. The host has 11 GB and is
  shared: on 2026-09-28 two gates side by side were both killed by the OOM killer. **Exit status
  137 is the OOM killer, not a result.**
- **Commit after each step.** A restart kills you, and only committed work survives it.
- **Record your final gate in your report**: the `GATE` line and the counts. Three wave-46
  reports did not (`D-117`).
- **When you hand back, stop.** No re-runs and no commits. The integrator merges at the sha you
  report. On 2026-09-28 a stream kept working after its branch was merged.
- **Any screen change drives the live journey**, `npm --prefix web run e2e:pc01 -- --phase all`,
  and quotes its summary. `make gate` does not run it (`D-108`).

## Lanes

| stream | worktree / branch | lane | ports |
|---|---|---|---|
| `W47-GATE` | `/root/w47gate` · `agent/w47-gate` | `gate-w47a` | PostgreSQL `56410`, S3 `60010/60011`, API `56411` |
| `W47-PASS` | `/root/w47pass` · `agent/w47-pass` | `gate-w47b` | PostgreSQL `56420`, S3 `60020/60021`, API `56421`, Next `56423` |

Both worktrees were moved from wave 46's provisioned ones. Their `.env` files and venv paths were
rewritten, and both lanes start empty (`make up` creates them).

## Judging

- **A judge at sub-stage A's close:** `W47-JUDGE-A`, on `gate-w47j`.
- **Two cross-judges on the merged tree before the final gate,** X on `gate-w47j` and Y on
  `gate-w47k`. **They get different entry points on purpose** (`W47-PLAN.md`): two judges agreeing
  is evidence only when their starting points were independent.
