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

**The instruments.** A disposable `git clone` of this worktree at `d56ae05`
(`/root/w46z-clone`, tags fetched so `test_doc_prose_facts.py` can read `alpha-w45`, the
worktree's `.venv` and `web/node_modules` linked and excluded, the lane's `.env` copied), and
the two `git archive` trees from Z1 for the checks that need no `.git`. Every mutation is a
scratch script that replaces an exact string and refuses to run if its anchor does not occur
exactly once, so a mutation that missed its target cannot pass as a green. Each was reverted
(`git checkout --` in the clone; `git show d56ae05:<path> >` in the archive tree) and checked
with `git status --porcelain` or `cmp` against `git show d56ae05:<path>`. Every scope was
baselined unmutated first.

### X-7 — a cookie is input, and the correlation exemption ignores case — **repaired**

**Y's reproduction** (`_takes_caller_input` itself, in-process, `getDashboardSummary` given one
required parameter at a time, on a copy of each tree's frozen document):

| extra parameter | `d5c9be5` | `d56ae05` |
|---|---|---|
| none | False | False |
| path `x` / query `x` / header `X-Scope` | True / True / True | True / True / True |
| **cookie `am_scope`** | **False** | **True** |
| **header `x-correlation-id`** | **True** | **False** |
| **header `X-CORRELATION-ID`** | **True** | **False** |
| header `X-Correlation-Id` | False | False |
| **a `$ref` to a component cookie parameter** | **False** | **True** |

The `d5c9be5` column is Y's table exactly; every wrong cell flipped.

**X's reproduction** (the required cookie added to `getDashboardSummary` in
`contracts/api/v1/openapi.json`, no client-fault response), `test_openapi_document.py`,
baseline **51 passed**: now **4 failed**, among them
`test_every_operation_that_takes_input_can_report_a_client_fault` with X's expected sentence,
*"getDashboardSummary takes caller input and declares no client-fault response"*. It passed
46/46 on `d5c9be5`. **Repaired.**

**X's "honest repair" direction** (the same cookie plus a `422`): the rule itself now accepts
it (the client-fault test passes, where X measured it refused). The file is still **4 failed**,
for three different reasons: the pinned input-less set (expected: a pin must move),
`test_no_operation_declares_a_cookie_parameter_today` (*"a cookie parameter now exists and
needs a decision"* — a deliberate tripwire), and two of the stream's own mutation tests
(`…makes_getdashboardsummary_take_input`, `…declared_on_the_path_item_also_counts`), which add
a cookie to the **live** document and expect the rule to refuse it, and so fail as soon as the
live document already declares a `422` there. Not a defect of the rule; recorded because the
day this contract legitimately gains a cookie, two proof-tests go red for a reason that is not
theirs.

### Y5 M5/M6 — the render guard asserts each number in its own row — **repaired for both mutations; a swap between equal rows still passes**

`dashboard.test.ts` in the archive tree, baseline **16 passed**. Y's mutations, applied
verbatim:

| mutation | `d5c9be5` (Y) | `d56ae05` |
|---|---|---|
| **M5** every section shows its neighbour's count (`sections-panel.tsx`) | 7/7 and 79/1118 passed | **1 failed**: *"every section row carries its own section's count"* — `AI: expected 4 to be +0` |
| **M6** `принято`/`отклонено` swapped (`verdicts-panel.tsx`) | 7/7 and 79/1118 passed | **1 failed**: *"every verdict row carries its own verdict's count"* — `accepted: expected 1 to be 2` |

`tsc --noEmit` exits `0` under both, as in Y's run: only the keyed assertions catch them.
**Repaired.**

**X stated the one limit of a keyed check in the cross-examination** — *"a swap between two rows
that hold the same number is invisible to any keyed check, so the fixture must give the rows
distinct counts."* The committed fixture does not: twelve of fourteen sections are `0`, and six
of eight run states are `0`. Two swaps of the same class as M5/M6, between rows the fixture
holds equal:

| mutation | `dashboard.test.ts` | whole frontend suite | `tsc` |
|---|---|---|---|
| `sections-panel.tsx`: АР shows ГП's count and ГП shows АР's | **16 passed** | **80 files, 1134 passed** | exit 0 |
| `run-activity-panel.tsx`: `queued` and `running` swapped (cell and filter) | **16 passed** | — | exit 0 |

Both would show wrong numbers on any deployment where the two rows differ. The verdict fixture
(4 / 2 / 1 / 0) is distinct and is not affected. See the findings table (Z-3).

**One quoted output does not reproduce.** `docs/program/W46-CLIENT.md` (C2) quotes Y's M5 as
failing with `AR: expected 0 to be 3`. No section in the committed fixture has the count 3
(`KM` 4, `PB` 2, the rest 0, at `c1081ed`, `2fccac8` and `c4e5575` alike), and `AR` reads
`AI`'s 0 under M5, which is correct. The mutation as described produces
`AI: expected 4 to be +0`, above. The repair is real; the quoted evidence for it is not the
output of the mutation it names.

### X-11 — what an absent `spend` means, and the generated types' shape — **repaired**

- **The description is present.** `contracts/api/v1/openapi.json`,
  `components.schemas.RunActivity.properties.spend`: `"description": "Absent when the deployment
  has made no provider call."`, beside the `$ref`. `RunActivity.required` is still
  `["by_state"]`. The mirror is byte-identical (Z3). `types.gen.ts` carries it as a doc comment
  above `spend?: RunActivitySpend;`, so the reader X-11 and Y wrote for now has something to read.
- **The generated types kept their shape, by the compiler rather than by a diff.** A probe
  declaring, for every one of the **61** `export type`s in `types.gen.ts`, a mutual-identity
  check `Eq<Old.T, New.T> = true` between `d5c9be5`'s and `d56ae05`'s generated file, compiled
  with `tsc --strict --exactOptionalPropertyTypes`: **exit 0**. Control: the same probe with
  `RunActivity` compared against `New.RunActivity & { extra?: 1 }` → **exit 2**, `TS2322: Type
  'true' is not assignable to type 'false'` at that line, so the probe can fail. (A first
  control built with `sed` failed on a syntax error, which proves nothing, and was redone.) The
  textual diff agrees: one JSDoc line and the digest lines.
- One sentence in the lock's new `commit_note` is not exact: *"`069f656` … W46-SPEND's own
  reseal, which made spend optional and absent-when-no-calls **in behaviour**"*. `069f656` is
  the reseal of the documents; the behaviour is `f50e656` (*"fix(F-1): run_activity.spend is
  absent, not a zero labelled measured"*), the commit the previous note named as
  `content_commit`. Very low; the digests, which the note calls the authority, recompute (Z3).

*(X-1, X-2, X-3/Y5-a, X-4, X-6/Y6-a and Y2-a follow.)*

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
