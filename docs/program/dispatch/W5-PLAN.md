# Wave 5 plan — two independent sessions, in parallel

Written 2026-09-15 by the integrator. Base `463a53a` on `planning/prototype-roadmap`,
published as `origin/dev`.

**Not to be started until the owner rules on whether to re-certify PC-01.** `W5-ADV` is
useful either way; `W5-CERT` exists only because re-certification is on the table.

## Why this wave is dispatched rather than led

Waves 2, 3 and 4 were led personally. Wave 5 cannot be, and the reason is not workload.

Both jobs here require a session that **authored none of the code**. The integrator led
waves 2 through 4, so the integrator is disqualified from both by the same rule that has
made every finding in this programme hold up: a session that repairs or authors the tree it
is measuring cannot be cited for the measurement.

That is the stop trigger the owner named, reached in its stated form.

## The two sessions

| Session | Asks | Instance | Live provider |
|---|---|---|---|
| `W5-CERT` | do the ten `PROTOTYPE_PROFILE.md` §8 criteria still hold, at the journey level, after 915 lines changed under them | `gate-w5` — 55560 / 59160 / 59161, `audit_w5` | **yes**, criterion 4 requires one |
| `W5-ADV` | is the new code correct, and are the guards the integrator wrote for it real | `gate-w5a` — 55570 / 59170 / 59171, `audit_w5a` | no |

Owned paths are disjoint. `W5-CERT` writes `artifacts/checkpoints/PC-01/**`, the PC-01
registry rows and the runbook; `W5-ADV` writes `tests/integration/{runs,findings,exports}/**`.
Neither writes `src/`, `db/`, `contracts/` or `web/`. Neither repairs anything.

## Why parallel, and the cost of being wrong about it

Sequential would be safer in one narrow way: if `W5-ADV` holes the new code, `W5-CERT` will
have spent a live run and a full manual runbook certifying something that must be certified
again.

Parallel is still right, because the two failure modes barely overlap. `W5-ADV`'s sharpest
target is an *internal* seam — the run row's `terminal_reason` after the retry budget is
exhausted. If a defect there is visible through the twelve journey operations, `W5-CERT`
reaches it independently and the certification is not wasted; if it is not journey-visible,
criterion 10 is unaffected and the certification stands.

So the realistic loss from parallelism is one re-run in the case where both sessions find
the same journey-visible defect — and in that case their agreement is itself worth having.
The gain is the whole of `W5-CERT`'s wall-clock, which is the expensive half.

**Both briefs tell the session to reach that seam from its own side, and say plainly that a
disagreement between the two answers is the most valuable thing the wave can produce.**

## The one seam that motivated a second session

Wave 2 built the retry loop. Wave 3 rewrote terminal selection. Neither session read the
other's code, and they meet on one path:

- `test_retry_policy.py:303` asserts that an exhausted attempt budget leaves the **stage**
  row carrying `dependency_unavailable` — "an operator reading `analysis_failed` has no
  reason to retry".
- Wave 3 made the **run** row carry the cause too.
- **Nothing asserts `audit_run.terminal_reason` on that path.** The wave-3 guard reaches the
  unreachable-provider case by a different route.

Found by reading the tests, not the closures. It may well be correct today — but correct and
unasserted is a coverage hole, and this programme's rule is that a hole is worth a test
rather than a shrug.

## What the integrator does with the results

Reconciles two reports that are **not subordinate to each other**. Neither session waits for
the other, and neither's verdict overrides the other's.

Defects go back to the tree that owns them. Whether `origin/main` advances to carry a new
PC-01 acceptance is the owner's decision, informed by `W5-CERT`'s verdict — not the
integrator's and not the session's.

## Still owner-blocked, and untouched by this wave

- **`OD-18`** — three to five named experts with committed slots. `P4-BHV-01` waits on this
  alone now that `P4-QA-01`'s second-reader pass is cleared (`W4_CLOSURE.md` §2).
- **`OD-17`** — the next corpus shape. PC-02's precision evidence is saturated.
- **The 21st error code.**
