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

Taken at this branch's tip `fbea618`, which is `2ffca8c` plus docs-only commits
(`git diff --name-only 2ffca8c..fbea618` touches only `docs/program/DEBT_REGISTER.md`
and `docs/program/dispatch/**`), so this baseline stands for `2ffca8c` as the brief asks.

**First attempt, lost — not a result.** `make gate > /root/w46a-gate.log 2>&1`, tree
clean at `63dbd60`. The battery reached 64% (past foundation, past the known red at
~14%, past a second failing node at ~61%) when the host ran out of memory system-wide:
`dmesg` — `Out of memory: Killed process 1125603 (python)`, `total-vm:1196752kB`. Swap
was 15/15 GB across roughly 54 concurrent sessions on the shared host, `W46-WIRE`'s own
baseline in `/root/w46dash` died the identical way at the identical time. The log's own
tail: `GATE: the canonical battery failed with pytest exit status 137.` **137 is
`SIGKILL`, not a test failure, and no `GATE OK` line exists in this log** — a killed
process is not a measurement and this attempt is discarded rather than read for a
verdict. Confirmed via the integrator (session restarted after the same event) before
re-running: kill only by confirmed-own PID, never by pattern, on a host every project
shares.

Second attempt, after confirming no other `make gate` under `/root/w46*` was running
(`readlink -f /proc/<pid>/cwd` on every `make gate`/`pytest` PID) and the host had
calmed (load ~3, ~3.5 Gi available, swap 5.4/15 Gi). Ran to completion, no OOM:

```
1 failed, 2499 passed, 5 skipped, 4 warnings, 169 subtests passed in 755.26s (0:12:35)
FAILED tests/contract/domain_p02/test_openapi_document.py::test_every_operation_can_report_not_found_or_validation
GATE: the canonical battery failed with pytest exit status 1.
```

**No `GATE OK` line** (`grep -n "GATE OK" /root/w46a-gate.log` → nothing). `run_battery`
failing aborts the recipe before `run_frontend`/`check_whitespace` run — this log says
nothing about the frontend battery or whitespace, only about the backend one, which is
this stream's to fix.

**One red, by node id**, exactly the brief's premise (`F-2`, gate red #5) and nothing
else:

- `tests/contract/domain_p02/test_openapi_document.py::test_every_operation_can_report_not_found_or_validation`
  — `AssertionError: getDashboardSummary declares no client-fault response`.

Reported to the integrator (`SendMessage`, `to: "main"`) with this exact line and list
before starting `S1`.
