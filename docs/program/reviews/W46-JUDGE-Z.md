# W46-JUDGE-Z — sub-stage C closed, on the merged tree, before the final gate

**Judge:** `W46-JUDGE-Z` · **lane:** `gate-w46j` (PostgreSQL `127.0.0.1:56390`, S3
`59990`/`59991`, API `56391`, Next `56393`) · **worktree:** `/root/w46j` · **branch:**
`agent/w46-judge-z` · **tree judged:** `d56ae05`, which merges `W46-GUARD` (`08f0e7f`, stream tip
`2c2be2b`) and `W46-CLIENT` (`d56ae05`, stream tip `c4e5575`) over the cross-judged tree.

Brief: `docs/program/dispatch/W46-JUDGE-Z.md`. Inputs read before the first measurement:
`AGENTS.md`, `docs/program/dispatch/W46-STAGE-C.md`, `docs/program/reviews/W46-JUDGE-X.md` and
`W46-JUDGE-Y.md` (both cross-examination sections), `docs/program/W46-GUARD.md`,
`docs/program/W46-CLIENT.md`.

This judge repairs nothing and owns this file only. Opened before the first measurement and
committed after each section. *A heading without a verdict has not been judged yet.*

## Z1 — the gate, literally — **`GATE OK`**

```
cd /root/w46j && make gate > /root/w46z-gate.log 2>&1      # literally
grep -n 'GATE' /root/w46z-gate.log
230:GATE OK: battery, foundation, frontend and whitespace all pass
```

Run on `8f7aae5` (= `d56ae05` plus this file, which sits in `docs/program/reviews/`, outside
every prose guard's scope), tree clean before and after, 22:40:16Z–22:49:41Z. Before starting:
`free -g` showed 4 GB available, load 2.6, and no `make` process had a cwd under `/root/w46*`.
Nothing else ran on this lane during the gate; I did read-only work only (`git show`/`git diff`
of the tip, scripts written to my scratch directory). The verdict is the log line above; the exit
status was `0`.

| layer | `W46-JUDGE-X` on `d5c9be5` | this run on `d56ae05` |
|---|---|---|
| foundation | 35 passed | **35 passed** (log line 60) |
| battery | 2504 passed, 5 skipped, 4 warnings, 169 subtests | **2516 passed, 5 skipped, 4 warnings, 169 subtests** (line 121) |
| frontend | 79 files, 1118 passed | **80 files, 1134 passed** (lines 225–226) |
| whitespace | passed | passed (the recipe reached `GATE OK`) |

### Every difference, by test id

**The instrument.** Two `git archive` trees, `/root/w46z-tree-d5c9be5` and
`/root/w46z-tree-d56ae05`, each with the worktree's `.venv` and `web/node_modules` linked and the
lane's `.env` copied in; `pytest --collect-only -p no:cacheprovider` with `run_battery`'s three
ignores plus `--ignore=tests/integration/foundation` (that suite refuses `--collect-only` by
design, and `git diff --stat d5c9be5 d56ae05 -- tests/integration/foundation` is empty, so its
35 cannot differ), and `npx vitest list --json`, set-differenced in Python. Removed at the end.

**Battery: 2474 → 2486 collected nodes (+ 35 foundation = 2509 → 2521 = passed + 5 skipped).
Removed: none. Added: twelve, every one `W46-GUARD`'s; `W46-CLIENT` added no Python node.**

```text
test_doc_prose_facts.py            (+5)  test_a_historical_heading_inside_a_code_fence_is_not_a_boundary
                                         test_a_too_early_heading_after_the_first_claim_is_still_caught
                                         test_a_too_early_heading_outside_a_fence_is_still_caught
                                         test_judge_ys_own_heading_after_the_first_claim_is_still_caught
                                         test_the_genuine_heading_is_still_found_as_the_boundary
test_openapi_conformance_live.py   (+1)  test_the_served_document_conforms_to_the_frozen_contract
test_openapi_document.py           (+5)  test_a_cookie_parameter_declared_on_the_path_item_also_counts
                                         test_a_required_cookie_parameter_makes_getdashboardsummary_take_input
                                         test_a_required_cookie_parameter_with_its_client_fault_response_is_accepted
                                         test_no_operation_declares_a_cookie_parameter_today
                                         test_the_correlation_header_exemption_is_case_insensitive
test_dashboard_summary_over_a_fresh_deployment.py (+1)
                                         test_a_deployment_with_known_data_reports_the_exact_counts
```

This matches the `W46-GUARD` stream gate recorded in the merge message `08f0e7f` (*"battery
2516"*) and the stream's own sums (G1 +1, G2 +1, G3 +4 +1, G4 +4 +1).

**Frontend: 1118 ids in 79 files → 1134 ids in 80 files. 31 ids removed, 47 added; net +16.**

- **27 are one rename, not this stage's streams**: every id under `the nineteen seam operations`
  became `the twenty seam operations` (same 27 leaves, checked one by one). That is the
  integrator's `ce25e14`, the X-8 repair, which landed on this line between `d5c9be5` and the
  streams' base.
- **+9 in `tests/unit/widgets/dashboard.test.ts`** (7 → 16): six under *"an omitted or
  unrecognised row is a fault, never a zero"* (a missing and an unknown row for each of the
  sections, verdicts and run-state panels) and three under *"every row is keyed to its own data
  attribute"* (sections, verdicts, rendered run states). `W46-CLIENT` C1/C2.
- **+7 in a new file**, `tests/guards/dashboard-invalidation.guard.test.ts` (the 80th): one
  set-equality case and one case per mapped mutation hook (six). `W46-CLIENT` C3.
- **4 renamed in `tests/unit/screens/project-sections.test.ts`**: the describe block
  *"…a rule of intake…"* became *"…a rule about the analysis and never a rule of intake"*, and
  three leaves were renamed with it. Read in the diff, each renamed case asserts the new sentence
  (*«Анализ построен для текста раздела АР»*, *«применяется к любому загруженному документу»*,
  *«Отдельного анализа для этого раздела нет»*) and the membership case gained two forbidden
  phrases (*«правило приёма»*, *«принимаются документы раздела»*); no assertion was dropped.

This matches the `W46-CLIENT` stream gate in `d56ae05`'s message (*"frontend 1134 in 80
files"*). Both stream gate logs exist and end in `GATE OK` (`/root/w46g-gate.log:229`, battery
2516, frontend 1118; `/root/w46c-gate.log:230`, battery 2504, frontend 1134); read with `grep`
only.

## Z2 — both judges' reproductions, re-taken against the repair

*(pending)*

## Z3 — did the stage break what the wave had?

*(pending)*

## Z4 — off the trail

*(pending)*

## Findings, most severe first

*(pending)*

## What I could not answer, and why

*(pending)*

## Evidence discipline

*(pending)*
