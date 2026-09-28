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

### X-4 — the historical boundary — **repaired for both judges' mutations; the positional hole survives a heading of the right shape**

On the **real** `docs/program/CURRENT_STATE.md` in a second disposable clone
(`/root/w46z-clone2`, `.git` and tags present), every insertion placed directly after the live
section's line ending *"…stays at 22.\*\*"* — where both judges put theirs.
`test_doc_prose_facts.py` baseline **26 passed**.

| inserted after the first claim | `d5c9be5` (X, Y) | `d56ae05` |
|---|---|---|
| control: *"The migration head is \`0010_run_terminal_detail\`."* alone | 1 failed | **1 failed** — `…migration_head_this_tree_has` |
| **X's**: a fenced `bash` block whose comment reads `# the historical record below is kept verbatim; do not edit it`, then the stale sentence | 21 passed | **1 failed** — the same test: the fence is masked, the boundary falls on the real heading, the stale head is read |
| **Y's**: `### What the historical record below keeps`, then the stale sentence | 21 passed | **7 failed** — *"the first historical-record marker outside a code fence does not look like this file's genuine heading … '### What the historical record below keeps'"* |
| **mine**: `## Previous release state — wave 46 (historical record)`, then the stale sentence | — | **26 passed** |

Both judges' mutations are **repaired**. The stream proved its repair on synthetic prose
(`_SYNTHETIC_LIVE_PREFIX`); on the real file it holds too.

**What survives is X-4's own subject, the position.** The shape check reads a heading's
*shape* and not its *place*, and the non-vacuity check (*"at least one claim survives"*) still
cannot see a boundary placed after the first claim. So a heading of the genuine shape, placed
where both judges placed theirs, blinds the scan to the stale head below it, exactly as the
unrepaired guard was blinded. The stream's own comment claims the opposite
(`tests/contract/api_v1/test_doc_prose_facts.py:486-492`): *"Non-vacuity is what would still
catch the one case that has the right shape and the wrong position: the genuine heading text
itself, copied verbatim and placed early by hand."* It catches it only when it is placed before
**every** claim — the same sentence X-4 found false in the previous version of this comment
(*"a too-early heading truncates all of them together"*). Reachable in the way X-4 described:
the close of wave 46 moves this file's live section into a `## Previous release state — wave
46 (historical record)` block, and a sentence left above a prematurely written heading is
exactly how a stale claim would be hidden. **Low–medium**, finding Z-2.

### X-1 — the served document against the frozen one — **repaired under both judges' mutations**

Each judge's own mutation, each judge's own scope, in `/root/w46z-clone` with the lane's `.env`
loaded; nothing else ran on the lane.

| mutation (`src/auditmanager/api/schemas/models.py` only) | scope | `d5c9be5` (the judge) | `d56ae05` |
|---|---|---|---|
| **X's**: `RunActivity.spend` required again (`spend: RunActivitySpend`, no default) | `run_battery`'s exact command, whole canonical battery | 2504 passed, 5 skipped | **1 failed, 2515 passed, 5 skipped** (22:51:45Z–23:00:13Z) |
| **Y's**: `AppendDecisionRequest.comment` `max_length=4000` → `400` | `tests/integration/api tests/integration/composition tests/contract tests/e2e`, `run_battery`'s ignores | 1119 passed, 6 skipped, 0 failed | **1 failed, 1131 passed, 5 skipped** (23:00:31Z–23:03:55Z) |

The one failure is the same node both times,
`test_openapi_conformance_live.py::test_the_served_document_conforms_to_the_frozen_contract`,
naming the exact location: *"schemas.RunActivity.required: the contract has 1 entries and the
generated document has 2 entries - contract ["by_state"] - generated ["by_state", "spend"]"*,
and *"schemas.AppendDecisionRequest.properties.comment.anyOf[0].maxLength: the contract has
4000, the generated document has 400"*. The file passes unmutated (1 passed). The scope's
node count moved 1125 → 1137, the twelve `W46-GUARD` nodes of Z1; the one fewer skip than Y
saw is environmental and not a node this stage touched. **Repaired.**

What it still assumes, stated so it is not mine to forget: the test compares
`create_documentation_app().openapi()`, and that this is what `serve.py`'s process serves rests
on `test_the_documented_and_the_wired_app_agree`, which Y showed compares against the router
fixture rather than the process. Y measured the two equal over HTTP at `d5c9be5`; nothing in the
gate does that at `d56ae05`. And the engine drops `description` (`N4`), so the served document
may disagree with the frozen one in any sentence — including X-11's new one, which the Pydantic
model does not carry (no file under `src/` changed in this stage) — without a red.

### X-2 — the fresh-deployment guard asserts counts — **repaired under every judge's mutation; a swap between equal counts passes**

`tests/integration/composition/test_dashboard_summary_over_a_fresh_deployment.py`, baseline
**4 passed** (the three old tests plus `test_a_deployment_with_known_data_reports_the_exact_counts`).
Mutations of `src/auditmanager/dashboard/repository.py`:

| mutation | whose | `d5c9be5` | `d56ae05` |
|---|---|---|---|
| `_filled` returns `(member, 0)`; the unclassified row `0` — no count ever read | X | 3 passed | **1 failed**: `{'AR': 0, …} assert 0 == 1` |
| `basis="measured"` unconditionally | X | 3 passed | **1 failed**: `'measured'` ≠ `'estimated'` |
| `_RUNS_BY_STATE` counts every run as `published` | Y | 3 passed | **1 failed**: `{'created': 0, …} == {'created': 1, …}` |
| `_DOCUMENTS_BY_SECTION` counts every published document as `KM` | Y | 3 passed | **1 failed**: `{'AR': 0, …, 'KM': 3, …}` |
| `model_call_count=calls + 1` | Y | 1 failed | **2 failed** |
| X's two together, over X's 612-test scope (`tests/integration/api tests/integration/composition tests/contract/domain_p02/test_project_section_catalog.py`) | X | 612 passed | **1 failed, 612 passed** (baseline 613 passed) |

**Repaired.** The stream's fixture seeds two projects, three published documents, a run in
each of the eight states, four findings and two calls with different bases, and asserts every
number; the seeded rows are the ones the assertions read, which answers Y's narrowing too.

**The same limit as the render guard, on the server side.** The known-data fixture gives equal
counts to rows the query could confuse: `AR` 1, `KM` 1 and unclassified 1; `pending` 1 and
`rejected` 1; seven of the eight run states 1. Three swaps, each a `CASE` in the query's
`SELECT` with `GROUP BY 1`:

| mutation | the guard |
|---|---|
| `_DOCUMENTS_BY_SECTION` reports `AR` documents under `KM` and `KM` under `AR` | **4 passed** |
| `_FINDINGS_BY_VERDICT` reports `pending` as `rejected` and back | **4 passed** |
| `_RUNS_BY_STATE` reports `queued` as `running` and back | **4 passed** |

Each is a wrong number on any deployment where the two rows differ (the section swap is driven
live in Z3 below, where it does). This is X's own stated condition for a keyed check —
distinct counts — unmet on the server side as on the client side. Finding Z-3.

### The product, as Y drove it

`audit_w46j` untouched; two judge databases created in `gate-w46j-postgres-1`:
`audit_w46z_judge` and `audit_w46z_empty`, each migrated to `0011_document_section` with the
seeded `admin` account and nothing else. The API is `infra/deploy/serve.py` on
`127.0.0.1:56391` (health `56392`), `AUDITMANAGER_PROVIDER_MODE=recorded`, a freshly generated
token, the lane's `.env` with `DATABASE_URL` pointed at the database being served (*"wired,
provider_mode=recorded, operations=20"*). Next is `npm --prefix web run build` (exit 0, 6 GB
available) with `NEXT_PUBLIC_API_BASE_URL=/bff/v1`, then `next start -p 56393 -H 127.0.0.1`
with `AUDITMANAGER_API_UPSTREAM=http://127.0.0.1:56391` and the same token. Sign-in is the
repository's own `session.mjs` through the real `/login`; every reading is a cold browser from
`cdp.mjs` (`withColdBrowser`) with `width.mjs`'s `MEASUREMENT`. A scratch `httpx` driver prints
raw status and body; a scratch `.mjs` probe imports only those three modules by path. Neither is
committed; every load-bearing reading is quoted here.

**The data state**, built through the API with an expectation of my own before any read: two
projects; four documents in one of them (`section=KM`, unclassified, `AR`, `AR`); two runs,
on the `KM` document and the unclassified one, both published with three findings each; three
decisions (`accept`, `accept`, `reject`). Expected: sections `AR 2 · KM 1 · unclassified 1`,
verdicts `pending 3 · accepted 2 · rejected 1 · needs_manual_review 0`, runs `published 2`, spend
two calls. `GET /dashboard` answered exactly that, and so did the screen. These rows were chosen
distinct so that a swap between any two of them would show.

### X-3 / Y5-a — an omitted or unknown row, through the full stack — **repaired**

Y's reproduction: A's `F-5a` server mutation (`_filled` drops every member with no rows; the
unclassified bucket appended only when non-zero), **plus** one unknown verdict row
`escalated: 9`, applied to `dashboard/repository.py` in the clone and **served from the clone**
on `56391` (cwd `/root/w46z-clone`); my unchanged Next in front of it; a cold `/dashboard` at
780 px.

```text
empty deployment, mutated API:
  {"documents_by_project": [], "findings_by_verdict": [{"verdict": "escalated", "count": 9}],
   "run_activity": {"by_state": []}, "section_breakdown": []}
  documents  no fault  digits []  «Проектов пока нет. …»
  verdicts   data-panel-fault="incomplete"  digits []  «Разбивка по вердиктам пришла неполной. …»
  runs       no fault  digits []  «Проектов пока нет. Прогонов показывать нечего, …»
  sections   data-panel-fault="incomplete"  digits []  «Разбивка по разделам пришла неполной. …»

data state, mutated API:
  findings_by_verdict pending 3, accepted 2, rejected 1, escalated 9 (needs_manual_review omitted)
  by_state [published 2] only;  section_breakdown AR 2, KM 1, unclassified 1 only
  documents  no fault  digits [4, 2, 4, 0]   (not a closed vocabulary; the server's own answer)
  verdicts   data-panel-fault="incomplete"  digits []
  runs       data-panel-fault="incomplete"  digits []   (spend is inside this panel and is not shown)
  sections   data-panel-fault="incomplete"  digits []
  one request: GET /bff/v1/dashboard 200; no overflow (765/780)
```

On `d5c9be5` Y's first reading rendered nineteen zeros and panel text identical to the honest
server's, and X's rendered no 9 and no `ZZ` anywhere. Now every panel whose rows are a closed
vocabulary refuses the body and shows no number; the run panel's empty-deployment branch shows
no number either, because it is decided by `documents_by_project` before `by_state` is read.
**Repaired**, on the screen and not only in the render test.

### X-6 / Y6-a — the dashboard after creating a project — **repaired**

Y's five steps, one browser page, all navigation client-side, on the empty deployment:

```text
1  0.9s  cold /dashboard           Проектов пока нет. | Проектов пока нет. Прогонов показывать нечего…
2  1.7s  brand link -> /projects   (client-side)
3  2.5s  fill #new-project-name, «Создать» -> data-created-project = prj_01M3N4QSN6PM6MVMNR57YKFBFC
4  4.1s  a[href="/dashboard"]      Документов: 0 на 1 проекте. Judge Z staleness probe документов 0 |
                                   Прогонов пока нет. Среди проектов системы ни один прогон ещё не запускался.
   /bff calls in the page session: GET /dashboard 200, GET /projects?limit=50 200,
                                   POST /projects 201, GET /projects?limit=50 200, GET /dashboard 200
5  5.0s  reload /dashboard         (the same)
```

At `d5c9be5` Y read *«Проектов пока нет.»* at step 4 with no second `GET /dashboard`; now, 1.6 s
after the project exists and well inside the 30-second window, the dashboard refetches and shows
it. **Repaired.** The guard that is meant to keep it repaired is weaker than it looks
(Z4, finding Z-5).

### Y2-a — every sentence about the analysed section, against a stored `KM` document with a published run — **repaired except one new sentence, which is false**

State: the `KM` document (`GET /versions/ver_01M3N4RK6XGVRZ9MPH27BXMW5V` → `"section": "KM"`) was
analysed and published three findings with `analysis_profile_id ap_01M25P3TH08VVTTGJRXYBZZ7RP`,
the same profile as the unclassified document's run. And `POST /projects/{uid}/documents` with
`section=ZZ` → **`422 validation_failed`**, *"The section property of the request body is not of
the declared form."*, `details: {"field": "section", "constraint": "enum"}`.

| screen | sentence, as rendered | true? |
|---|---|---|
| `/dashboard`, sections panel | *«Раздел документа сохраняется и проверяется на сервере, когда его называют при загрузке. Форма загрузки в этом продукте раздел не предлагает…»* | **true**; *«единственный анализируемый раздел»* is gone |
| `/projects/{uid}`, both tabs | *«Разделы — это навигация. Раздел документа хранится и проверяется на сервере, когда его называют при загрузке; … ни один список здесь не отобран по разделу.»* | **true** (the АР tab lists all four documents, the `KM` one among them) |
| АР tab | *«Анализ построен для текста раздела АР — это единственный профиль анализа, который есть у продукта, и он применяется к любому загруженному документу вне зависимости от того, под каким разделом сервер его хранит.»* | **true**: one profile id for both runs |
| АР tab | ***«При загрузке проверяется конверт файла, а не раздел.»*** | **false**: the upload above was refused **on the section**, and the very next sentence says *«Раздел документа сервер тоже хранит и проверяет, когда его называют»* |
| АР tab, the note's title | *«Что сейчас принимается»* over a body that no longer describes intake | stale framing, not a false number; the body under it now says nothing is refused by section |
| КМ tab | *«Отдельного анализа для этого раздела нет: анализ построен только для текста раздела АР и применяется к любому загруженному документу вне зависимости от того, под каким разделом он сохранён.»* | **true**: the `KM` document was analysed by the АР profile |
| КМ tab | *«Раздел появится в одной из следующих версий как самостоятельный экран…»* | a promise; not measurable |

**Mostly repaired.** The two sentences Y named are gone or rewritten true. The rewrite
introduced one false sentence, and it contradicts the sentence after it on the same line of the
same screen: `web/src/widgets/project-sections/ui/project-sections.tsx:112` (*«При загрузке
проверяется конверт файла, а не раздел.»*) against `:113` (*«Раздел документа сервер тоже хранит
и проверяет, когда его называют»*). What the author meant — the section does not decide whether
a document is accepted for analysis — is true; what the sentence says is not. It is Y2-a's own
class: a sentence about intake that the server contradicts. `tests/unit/screens/
project-sections.test.ts` pins neither. **Low–medium**, finding Z-4.

## Z3 — did the stage break what the wave had? — **no**

**The live journey**, against my Next and API over the data state:

```text
E2E_PC01_LOGIN=admin E2E_PC01_PASSWORD=password \
  npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:56393 --phase all --out <scratch>
sign-in: ok at /login -- carrying 'am_session' (HttpOnly=true, SameSite=Strict) into every cold browser
ok  create-project   api=3 {"project_uid":"prj_01M3N5D9RZA34FHPRXC0ZAD31M"}
ok  upload-document  api=4 {…"version_uid":"ver_01M3N5E4DFMZB4S5V6S78T6BWB"}
ok  start-run        api=5 {…"run_id":"run_01M3N5EYTTAHEXPK4K7QP0PRQ0"} terminal=published in 1508ms/150000ms
ok  root … ok  dashboard 200 api=1 auth=0 console=0 jar=[am_session] w=765/780   (all sixteen `ok`)
write steps checked: 3/3
routes checked: 16/16
e2e:pc01 OK
```

Exit `0`. Read from the raw exchanges in `journey.json`, not the summary's deduplicated `api=`:
`dashboard` → exactly `GET /bff/v1/dashboard 200`; `blocks` and `projects` → exactly
`GET /bff/v1/projects?limit=50 200`; `undeclaredApi` empty on all sixteen routes; top-level
`failures` empty.

**`/dashboard` at 780 px, both palettes, with data** (the data state above; palette written to
`am-theme` the way the toggle stores it, in its own cold browser):

| palette | `data-theme`, body | `scrollWidth`/`clientWidth`/`innerWidth` | past the edge | faults | `/bff` calls | console / page errors |
|---|---|---|---|---|---|---|
| light | `light`, `rgb(245, 246, 248)` | 765 / 765 / 780 | 0 | none | `GET /dashboard 200` | 0 / 0 |
| dark | `dark`, `rgb(13, 18, 25)` | 765 / 765 / 780 | 0 | none | `GET /dashboard 200` | 0 / 0 |

Identical to Y's readings on `d5c9be5`. The new fault state (X-3 above) also fits: 780/780 and
765/780 with no offender.

**The reseal, recomputed by me.** `hashlib.sha256` over this tree, every 64-hex value in
`web/FRONTEND_LOCK.json`: **8 of 8 match** — `openapi.sha256` = `snapshot_sha256` `78eccd9e…`,
`client.gen.ts` `f5ab53b9…`, `index.ts` `16841483…`, `operations.gen.ts` `6223d863…`,
`types.gen.ts` `ec03026a…`, `lockfile_sha256` `98691bc8…` (= `web/package-lock.json`),
`script_sha256` `787c744d…` (= `web/scripts/generate-api-client.mjs`). `cmp` contract vs mirror:
byte-identical. `npm --prefix web run api:verify` → *"generate-api-client --check: OK - 20
operations, contract sha256 78eccd9e01de927556cc1a1f9ad83db2e318872d3951fe3ab54f732eabf5e0b4"*.
Surface **17 / 20 / 61** from the document, equal to the lock; **22** error codes in `ErrorCode`
and in `contracts/domain/v1/error-codes.json`; `git diff --name-only d5c9be5 d56ae05 --
contracts/domain db/migrations` empty; head `0011_document_section`. The worktree was clean
before and after.

**Nothing the wave had is lost**: the gate is green with 12 + 16 more tests and none removed (Z1),
the journey, the widths and the palettes read as they did on `d5c9be5`, and `F-1` still holds
(the data state's `spend` is `{2, 68800, "estimated"}`; the empty deployment carries no `spend`
key).

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
