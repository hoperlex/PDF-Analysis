# W46-JUDGE-X — the contract, the instruments and the integrator's own changes

**Judge:** `W46-JUDGE-X` · **lane:** `gate-w46j` (PostgreSQL `127.0.0.1:56390`, S3
`59990`/`59991`, API `56391`, Next `56393`) · **worktree:** `/root/w46j` · **branch:**
`agent/w46-judge-x` · **tree judged:** `d5c9be5`, the merged tip of wave 46 (sub-stage A judged
at `2ffca8c`, then `W46-SPEND` merged at `9a295aa`, `W46-WIRE` at `1c38c52`, and the
integrator's join repair `d5c9be5`).

Brief: `docs/program/dispatch/W46-JUDGES-XY.md`, section `W46-JUDGE-X`. Opened before the first
measurement and committed section by section; a section marked *pending* has not been measured
yet.

## X1 — the whole gate on the merged tip — **`GATE OK`**

```
cd /root/w46j && make gate > /root/w46x-gate.log 2>&1      # literally
grep -n 'GATE' /root/w46x-gate.log
229:GATE OK: battery, foundation, frontend and whitespace all pass
```

Run on `f35e7cd` (= `d5c9be5` plus this file only, which sits in `docs/program/reviews/`,
outside every prose guard's named scope: `test_wave_reports_are_never_scanned`), tree clean,
11:57:13Z–12:09:09Z. Before starting: `free -g` showed 4 GB available, and no other
`make gate` had a cwd under `/root/w46*`. Another project's node test suite ran on the host
during the battery (load 20 at its peak); nothing was OOM-killed and the log is complete.
The verdict is the log line above, not the exit status (which was `0`).

| layer | `W46-JUDGE-A` on `130200d` | this run on `d5c9be5` |
|---|---|---|
| foundation | 35 passed | **35 passed** (log line 60) |
| battery | 7 failed, 2493 passed, 5 skipped, 4 warnings, 169 subtests | **2504 passed, 5 skipped, 4 warnings, 169 subtests** (line 121) |
| frontend | 1 file failed; 2 failed, 1118 passed (1120) in 79 files — run by hand, because the battery stopped the gate first | **79 files, 1118 passed (1118)** (lines 224–225), run by the gate itself |
| whitespace | `git diff --check` exit 0 | passed (the recipe reached `GATE OK`) |

**Every difference, by count.** Accounted by name in X6 below (node-id set algebra), and
predicted before the run from the commits alone:

- **battery 2500 nodes → 2504.** `8ad692f` repaired six battery reds by editing inside
  existing tests (no node added or removed), so `2ffca8c` still had 2500 nodes (`W46-SPEND`'s
  own baseline: 1 failed + 2499 passed). `W46-SPEND` removed one node
  (`test_every_operation_can_report_not_found_or_validation`), added two in the same file
  (`test_every_operation_that_takes_input_can_report_a_client_fault`,
  `test_the_input_less_operation_set_is_exactly_the_pinned_one`) and three in a new file
  (`test_dashboard_summary_over_a_fresh_deployment.py`): 2500 − 1 + 2 + 3 = **2504**.
  `W46-WIRE` and `d5c9be5` touch no Python test. The seven reds of `130200d` are all gone:
  six by `8ad692f`, the seventh (#5) by `W46-SPEND`'s restated rule.
- **frontend 1120 → 1118.** `8ad692f` added `getDashboardSummary` to `SEAM_OPERATIONS`,
  which is iterated into one `it()` per row (`seam-operations.contract.test.ts:95-96`):
  **+1 → 1121 at `2ffca8c`**. That is the one test `W46-WIRE.md`'s *"Frontend baseline"*
  section could not place: the integrator's derived `1120` missed that the row is a test
  of its own; `W46-WIRE`'s reconstructed `1121` was right. `W46-WIRE` then replaced the three
  deleted aggregators' cases in `dashboard.test.ts` (10 → 7): **−3 → 1118**. No test file was
  added or deleted: 79 → 79.
- **the two frontend reds of `130200d`** (`seam-operations`, #8–#9) were repaired by
  `8ad692f`'s row; the second one cleared because its 19 was derived from the list.

## X2 — `F-1` re-driven

*pending*

## X3 — the reseal: five documents or four?

*pending*

## X4 — the three guards `W46-SPEND` claims, mutated by me

*pending*

## X5 — the integrator's own changes

*pending*

## X6 — did the merge lose a test?

*pending*

## Off the trail

*pending*

## Findings, most severe first

*pending*

## What I could not answer, and why

*pending*
