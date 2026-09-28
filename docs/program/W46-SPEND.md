# W46-SPEND — the reseal for `F-1`, `F-2` restated as a test, and two backend guards

**task_id:** `W46-SPEND` · **wave:** 46, sub-stage B · **lane:** `gate-w46a`
**worktree:** `/root/w46seal` · **branch:** `agent/w46-spend`, dispatched at `fbea618`
(docs-only on top of `2ffca8c`, which is the base this stream measures against)

Opened before the first measurement, per discipline. Written as the work is found, one
step at a time, and committed after each step so a session restart loses nothing.

## 0. Premises, from `docs/program/reviews/W46-JUDGE-A.md`

- **F-1** (section 3): `getDashboardSummary` answers
  `"cost_basis":"measured","cost_micros":0` on a deployment with **zero** `model_call`
  rows — an invented measurement. `RunRepository.cost()` returns `None` for the same
  state and says why in its docstring; the aggregate's own docstring claims to lift that
  rule and drops the `calls == 0 -> None` branch. Repair, per the integrator's shape:
  `RunActivity.spend` becomes optional, absent when there is nothing to report, present
  with all three fields otherwise. A reseal.
- **F-2** (section 3, `F-2b`): gate red #5,
  `test_every_operation_can_report_not_found_or_validation`, is a rule that shared an
  assumption with its subject. Integrator's ruling: the rule is wrong, the operation is
  right, repair the test, no reseal for this finding.
- **F-5a** (section 3, "What is not guarded"): `_filled`'s absent-is-not-empty mutation
  survives 609/609 — no test observes a response row.
- **F-5c** (section 6, `F-5`): `ff686b1`'s structural historical-section control lost the
  assertion that the live section still yields a claim the guard can read; a premature
  heading blinds the scan and the control stays green.

## 1. Baseline

Pending — first `make gate` run, taken at this branch's tip `fbea618`, which is `2ffca8c`
plus docs-only commits (`git diff --name-only 2ffca8c..fbea618` touches only
`docs/program/DEBT_REGISTER.md` and `docs/program/dispatch/**`), so this baseline stands
for `2ffca8c` as the brief asks.
