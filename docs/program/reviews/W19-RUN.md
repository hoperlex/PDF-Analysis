# W19-RUN — the run screen says what the run did

**Session:** `W19-RUN`  **Branch:** `agent/w19-run`  **Worktree:** `/root/w19run`

## HEAD on arrival

```
d3520b0af02861c56896cf504bb94f435674e966
d3520b0 merge(W19-API): the count the contract promised, and the mutation that passed first
```

Provisioned from `origin/dev` after the integrator pushed. On my first attempt `origin/dev`
was `653152f`, eighteen commits behind, and I stopped at STEP 0 rather than branch from an
unpushed local ref. Recorded here because the stop is part of this session's history.

## The brief's framing, corrected against the tree

The brief lists six fields that "no screen renders". That is true of three of them and
false of three. Before writing anything I read what the run screen already does.

| field | brief says | the tree says |
|---|---|---|
| stage `started_at` / `finished_at` | never read back | **already rendered.** `stage-table.tsx:44-45,58-63` has Started and Finished columns, fed by `stageRows` (`run-presentation.ts:198-199`) |
| `published_finding_count` | not rendered | **already rendered.** `run-presentation.ts:137` reads it, `run-progress.tsx:70-71` prints it |
| `diagnostic_observation_count` | not rendered | correct — no reference anywhere in `web/src/` |
| `cost_micros` | not rendered | correct |
| `cost_basis` | not rendered | correct |
| `model_call_count` | not rendered | correct |

**Why the user saw what they saw.** `formatInstant` (`format-instant.ts:9-14`) returns
`'—'` for `null`, `undefined` and `''`. "Started — Finished —" is therefore not a screen
that ignores the columns; it is a screen faithfully reporting that the reading carried no
stage timings. Likewise "Published findings: not reported" is the `findingCount === null`
branch at `run-progress.tsx:71` firing because the field was absent from that response.

This matters for what the work is. The defect is not uniformly "the screen drops fields".
For three fields it is "the screen has no place for them at all", and for the other three
it is a data question that belongs to whoever owns the response. I verified the data
question before assuming either: `bootstrap/adapters.py:352-358` populates all five run
fields and `:379-380` populates the stage timings, so a fresh run does carry them. The
brief's "everything you need is already in the response body" holds.

## Base gate figures

Integrator's figures, measured on the merged tip `d3520b0`: battery 1785 / 5 skipped /
168 subtests, foundation 35, frontend 633 (46 files), exit 0. My own measurement is
recorded in the gate section below.

## Files I edited, and why each one is the run screen

The coordinator's corrected ownership named `_pages/run/**`, `widgets/run-progress/**`,
`widgets/run-list/**`, `features/start-run/**`, `features/export-run/**` and this review,
"plus whatever else you prove the run screen lives in". I edited none of the features and
neither page: **the run screen is not in `_pages/run/`**. `run-page.tsx` is nineteen lines
of `PageShell` that delegate everything to `RunProgress`, and `RunProgress` delegates every
judgement to `entities/audit-run`. So the four files below are the run screen.

| file | why it is the run screen |
|---|---|
| `web/src/widgets/run-progress/ui/run-progress.tsx` | the whole screen; `_pages/run/ui/run-page.tsx:38` renders this and nothing else |
| `web/src/entities/audit-run/model/run-presentation.ts` | every judgement the screen makes, as pure functions — the module's own header says the rules live here "so a test can hold them without a browser" |
| `web/src/entities/audit-run/ui/stage-table.tsx` | the per-stage timings, which is where three of the six fields surface |
| `web/src/entities/audit-run/index.ts` | the slice's public API; FSD boundary rules refuse a deep import past it, so a new selector is unreachable until it is exported here |

**`entities/audit-run/**` was in nobody's ownership line.** I edited it because the
alternative was to reimplement its selectors inside the widget, which the repository's own
FSD guard test forbids. Flagging it rather than assuming it: `web/src/entities/**` is the
fourth ownership line this week that was narrower than the code.

`widgets/run-list/**`, `features/start-run/**` and `features/export-run/**` were mine to
edit and needed nothing. `web/FRONTEND_LOCK.json`, `web/package.json`,
`web/package-lock.json` and `Makefile` are byte-identical to `d3520b0`, and nothing under
`src/`, `contracts/` or `infra/` was touched.

## What the screen renders now

Timings as a **duration**, not only as two stamps; both counts, apart; and the cost with
its basis and the count it sums.

### Cost is formatted without ever becoming a float

`formatCostMicros` (`run-presentation.ts`) does decimal-point insertion on the integer's
own digit string. It never divides and never parses:

```ts
const digits = String(Math.abs(micros)).padStart(MICRO_FRACTION_DIGITS + 1, '0');
const whole = digits.slice(0, -MICRO_FRACTION_DIGITS);
const fraction = digits.slice(-MICRO_FRACTION_DIGITS);
```

The test that matters is the sub-cent one. `(1 / 1_000_000).toFixed(2)` is `'0.00'`, which
reads as free; `formatCostMicros(1)` is `'0.000001'`. Migration `20260910_0002` says
floating-point money is not stored, and this is the contract not turning it into one on
the way out.

**No currency symbol.** The contract says "millionths of the provider currency unit" and
never names the currency — I grepped `contracts/` and the word appears exactly once, in
that phrase. Printing `$` would invent a fact the response does not carry, so the screen
prints `0.034400 provider currency units` and the raw integer beside it.

### Absent is not zero, and the test that proves it

The backend keeps these apart and I verified it before building on it:
`runs/repository.py:cost()` returns `None` when `count(*)` over `model_call` is zero, and
its docstring calls reporting that as `0` "the same class of invention as `D-3`'s
defaulted provenance". `bootstrap/adapters.py:356-358` maps `None` to all three fields
absent together.

`runCost` returns a discriminated union, so the two states cannot be merged by a caller
even by accident: `{kind:'absent'}` versus `{kind:'reported', micros:0, …}`. They reach
the user as different sentences, not different numbers:

* absent — *"This run made no provider call, so it has no cost to report. That is not a
  cost of zero — nothing was spent here because nothing was called, and the two are
  different claims."*
* a genuine zero — *"This run called the provider twice and was charged nothing. This is a
  reported zero, not an absent cost."*

Proving it: `an absent cost is not a zero cost (M-2) > gives the two states different
kinds, so no caller can merge them by accident`, and at the screen level `a run that spent
nothing and a run that called nothing read differently (M-3) > gives the two states
markers that cannot both appear`.

### `model_call_count` is shown beside the cost — and the cost is withheld without it

Yes, always. `D-15` is open: the total sums across retry attempts while `cost_basis`
describes the last response only, so a figure with no count beside it cannot be told apart
from a first-try one. I went further than displaying it: **`runCost` returns `unreadable`
when `cost_micros` arrives without `model_call_count`**, and the screen prints no figure
at all. Showing the sum without its span would be `D-15` re-created on the screen, which
the brief names as the thing to avoid; the contract's own words are "present exactly when
`cost_micros` is", so a response missing one is malformed and is reported as such.

### `estimated` is not rendered as a warning

It is the ordinary case — a `recorded` run replays calls carrying no cost, and the
aggregate rule downgrades the whole run when any one call is unmeasured. The caption ends
"which is the ordinary case for this prototype and not a fault", there is no error state
and no warning styling, and a test asserts the cost region contains none of
`am-state--error`, `Warning`, `Invalid`, `went wrong`. A separate test asserts an unstated
basis renders as `unstated` and never as `measured` — defaulting it would be `D-3` again,
in the flattering direction.

## The cold load, in a fresh tab

**How.** `next build` + `next start` on `127.0.0.1:3920`, `NEXT_PUBLIC_API_BASE_URL=/bff/v1`
forwarding through the real `/bff/v1` route handler to this repository's own
`infra/deploy/serve.py` on `127.0.0.1:58840`, against this lane's PostgreSQL (55840) and
MinIO (59440), instance `gate-w19c`, `AUDITMANAGER_PROVIDER_MODE=recorded`. **No image was
rebuilt and no alpha stack was touched** — 31480, 31490 and 31500 were left alone.

Seeded through the public origin as a user: a project, an upload of
`fixtures/synthetic/ar/ar_baseline.pdf` (8 pages, 58 978 bytes, `sha256 6d53674f…`), and a
run — `published`, `recorded`, 4 stages, **3 findings, `cost_micros` 34 400, basis
`estimated`, 1 model call**.

**A separate `chromium.launch()` process, fresh context, no storage, no cache, no prior
client state.** Browser is the existing `chromium-1234` on this host driven by the
`playwright-core` at `/root/w15run-browser`; no repository dependency was added. Journal:
`/root/w19run-logs/browser/cold-loads.json`.

```
GET http://127.0.0.1:3920/projects/prj_01M2T9RX3Q8VD7YVWNNNP8P5C7/runs/run_01M2T9S412Y6B8JNZGC3CWAV7Z  ->  200
  200 /bff/v1/runs/run_01M2T9S412Y6B8JNZGC3CWAV7Z
```

What the browser rendered:

```
published
recorded
provider mode: recorded

Replayed from recordings. This run is not evidence of a live provider call.

Run          run_01M2T9S412Y6B8JNZGC3CWAV7Z
Version      ver_01M2T9RXYXBCTD2Q0T0FFWB5PB
Created      2026-09-18 13:02:34 UTC
Terminal at  2026-09-18 13:02:34 UTC
Took         374 ms

The run reached its success terminal, published.

Published findings: 3

Diagnostic observations

Recorded: 0

A diagnostic observation is something the run noticed and did not admit as evidence.
It is not a finding, it is not counted as one, and the two totals are never added together.

Cost
Spent                          0.034400 provider currency units (34400 millionths, the integer the run stored)
Provider calls this total sums 1
Basis                          estimated

At least one call this figure sums did not report a cost of its own, so the figure is
estimated. A recorded run replays calls that carry no cost, which is the ordinary case
for this prototype and not a fault.

The total sums every provider call this run made, retries included. The call count is
printed beside it so a run that answered first time can be told from one that was retried.

Stages
Stage                      Status      Started                 Finished                Took
source_preparation         succeeded   2026-09-18 13:02:34 UTC 2026-09-18 13:02:34 UTC 115 ms
page_geometry_extraction   succeeded   2026-09-18 13:02:34 UTC 2026-09-18 13:02:34 UTC 157 ms
document_context_build     succeeded   2026-09-18 13:02:34 UTC 2026-09-18 13:02:34 UTC 30 ms
text_analysis              succeeded   2026-09-18 13:02:34 UTC 2026-09-18 13:02:34 UTC 34 ms

Is this reading final?

Not polling. This reading is final.
```

Data attributes the same load carried: `data-run-outcome="published"`,
`data-diagnostic-observation-count="0"`, `data-run-cost="reported"`,
`data-cost-micros="34400"`, `data-model-call-count="1"`,
`data-cost-basis="estimated"`, `data-run-activity="stopped"`.

### What the first cold load changed about the work

The first cold load, before the `Took` columns existed, rendered **every stage with the
same Started and Finished string** — `2026-09-18 13:02:34 UTC` four times over. The run
took 374 ms and `formatInstant` prints to the second, so the two columns that already
existed carried no information whatever. Rendering a field is not rendering a fact. The
`Took` column is the result, and it is the one change in this session that the browser
found and no unit test would have.

## `D-20` — the polling copy, judged by loading it cold

**Judged harmless, and kept — but moved.** The three branches are guarded by
`isRunAnimating`, which is false for any terminal or reconciled reading. Because
`execute_run` is inline, every real reading is terminal, so what a user actually sees is
`Not polling. This reading is final.` — which the cold load above confirms, and which is
true. The backoff sentence at the former line 164 is unreachable in practice but is not
false: it is correctly conditioned, and it would be accurate if a non-terminal reading
ever arrived. Deleting it would remove the screen's only statement about whether what you
are looking at is final, which is genuinely useful and not otherwise checkable.

There was no user-visible misrepresentation to remove. The words "progress" and "running"
never reach the user: `PageShell` is titled `Run`, and `run-progress` is an internal module
name. What was wrong was **emphasis** — the paragraph sat immediately under the badge, so
the most prominent thing on a terminal run was a statement about the poller. It now sits
below the result under the heading *"Is this reading final?"*, and the screen leads with
what the run did. I built nothing that implies live progress.

## Mutations

Thirteen, each applied to the tree and reverted, the two suites re-run each time.
**Thirteen killed, none surviving.**

| # | mutation | file | result | test that goes red |
|---|---|---|---|---|
| M-1 | `formatCostMicros` divides by a million and `toFixed(2)` | `run-presentation.ts` | KILLED | `…without ever becoming a float (M-1) > keeps a cost far below a cent instead of rounding it to zero` |
| M-2 | `runCost` reports `0` instead of `absent` for a run that made no call | `run-presentation.ts` | KILLED | `an absent cost is not a zero cost (M-2) > reports absent when the run made no provider call` |
| M-3 | the absent branch renders the zero branch's sentence and marker | `run-progress.tsx` | KILLED | `…read differently (M-3) > gives the two states markers that cannot both appear` |
| M-4 | the call count is dropped from the cost block | `run-progress.tsx` | KILLED | `a cost is never shown without the call count it sums (M-4) > prints the call count beside the figure` |
| M-5 | the missing-count guard is deleted | `run-presentation.ts` | KILLED *(after strengthening — see below)* | `…without the count it sums (M-5) > refuses a cost that arrived with no model_call_count` |
| M-6 | the diagnostic count is rendered from `published_finding_count` | `run-progress.tsx` | KILLED | `findings and diagnostic observations are two counts, never one (M-6) > renders both, with different values, under different labels` |
| M-7 | `estimated` is captioned as a warning | `run-presentation.ts` | KILLED | `an estimated basis is the normal case, not a warning (M-7) > does not dress an estimated basis as an error or a warning` |
| M-8 | `diagnosticObservationCount` answers `0` for an unreported count | `run-presentation.ts` | KILLED | `a diagnostic count that was not reported is not zero (M-8) > answers null when the field is absent` |
| M-9 | the whole cost and diagnostics section is dropped | `run-progress.tsx` | KILLED | `the cost section is on the screen (M-9) > renders a cost statement for a published run` |
| M-10 | a missing `cost_basis` defaults to `measured` | `run-presentation.ts` | KILLED | `an unstated cost basis is not a measured one (M-10) > reports a missing basis as null rather than as measured` |
| M-11 | `formatElapsed` drops the millisecond branch | `run-presentation.ts` | KILLED | `a span is rendered at a resolution that still says something (M-11) > reports a sub-second stage in milliseconds rather than as zero` |
| M-12 | `elapsedMs` returns a negative span instead of refusing it | `run-presentation.ts` | KILLED | `a span that runs backwards is not a duration (M-12) > refuses a pair that finishes before it starts` |
| M-13 | the `Took` cell renders a constant `0` | `stage-table.tsx` | KILLED | `the stage timings carry a measurement… (M-13) > reports how long a sub-second stage took` |

### The one survivor, and what it cost to kill

**M-5 survived the first run.** Deleting the missing-count guard changed nothing
observable, because the type guard below it (`typeof callCount !== 'number'`) catches
`undefined` too. It was an **equivalent mutant** in behaviour — but not in output: the two
paths return different `why` strings, and `why` is rendered (*"This reading's cost cannot
be read: {why}"*). A rendered fact with no test on it is exactly what this standard is
about, so I constrained the reason rather than argue equivalence and leave it. Two new
assertions, and M-5 now goes red. That is the only thing in this session that a weaker
reading of "survivor" would have let through.

### A process defect this session hit, worth recording

The first mutation harness reverted with `git checkout -- <path>` against files whose new
code I had **not yet committed**, and silently destroyed the `elapsedMs`/`formatElapsed`
work and the `Took` column. It cost a re-application. `MEMORY` already carries this as
*"snapshot before dispatch"*; the narrower rule a mutation harness needs is **commit
before you mutate**, because the revert mechanism cannot tell your work from the mutation.

## Boundaries stopped at

* **`origin/dev` eighteen commits behind at STEP 0.** Stopped and reported rather than
  branch from the unpushed local `planning/prototype-roadmap`. The integrator pushed and
  the base became `d3520b0`.
* **The absent-cost state cannot be reached through the product, and could not be forged
  either.** No accepted upload avoids a provider call: an image-only PDF is refused at
  upload (`validation_failed`, `every_page_has_extractable_text`), so every run that
  starts reaches `text_analysis`. I then tried to construct it in the database, and
  **PostgreSQL itself refused**:

  ```
  ERROR:  state_transition_not_allowed: model_call is immutable once written; DELETE is refused
  HINT:  Correcting data creates a new entity with a new identifier; it never rewrites an existing one.
  ```

  So the absent branch is proved by test and by reading `repository.py:cost()`, **not by a
  browser**, and I am not claiming otherwise. It is still correct to implement — the
  contract declares the three fields optional and the repository returns `None` — but no
  cold load can show it today. Whether a state no run can produce should be reachable at
  all is an owner's question, not mine.
* **No `src/`, `contracts/`, `infra/` or `Makefile`.** Nothing needed them; the response
  body already carried all six fields, which I verified at `adapters.py:352-358` and
  `:379-380` before designing around it.
* **`web/FRONTEND_LOCK.json` untouched**, along with `package.json` and `package-lock.json`.

## What was false in the brief

1. **"`published_finding_count` … no screen renders."** It was rendered before I arrived,
   at `run-progress.tsx:70-71`, fed by `run-presentation.ts:137`.
2. **"stage `started_at`/`finished_at` … the columns were written since the first
   migration and never read back."** `stage-table.tsx` had Started and Finished columns
   and `stageRows` fed them. They were read back; they just said nothing, for the
   different reason in §*What the first cold load changed*.
3. **"a user saw *Published findings: not reported* and *Started — Finished —*."** Both
   are real strings in the code, but neither is a screen dropping a field:
   `formatInstant` returns `'—'` for a null and `run-progress.tsx:71` prints
   *not reported* when the count is absent. Both were faithful reports of an empty
   reading. A run seeded today through the public origin renders `3` and four real stage
   timings, so whatever that user loaded predates `W17-VIEW` landing.
4. **`web/src/features/run/**` and `web/src/_pages/run-*/**` do not exist** — corrected by
   the coordinator before I started, recorded here because it is three sessions running.
5. **`W19-LIST` is not live** — cancelled and never dispatched; `run-list` was mine.

Everything else in the brief held. `D-3`, `D-15` and `D-20` are all open or closed as
described, the six fields carry the semantics the contract states, and the response body
did contain everything I needed.

## The gate

Run on a clean tree at **`1d4cb390208ec239226334c59d9cf0197224068f`**, which is every
commit of this session except the two that add this section and record elapsed. Instance
`gate-w19c`, PostgreSQL 55840, MinIO 59440/59441, database `audit_w19c`, bucket
`auditmanager-gate-w19c`. No image rebuilt; the alpha stacks on 31480, 31490 and 31500
were untouched.

Exit code taken from `$?` after a redirect, never through a pipe:

```
make gate > /root/w19run-logs/gate.log 2>&1
GATE_EXIT=$?          ->  0
```

```
GATE OK: battery, foundation, frontend and whitespace all pass
```

| suite | at base `d3520b0` (mine) | at `1d4cb39` | integrator's figure |
|---|---|---|---|
| battery | *not separately measured* | **1785 passed, 5 skipped, 168 subtests** | 1785 / 5 / 168 — agrees |
| foundation | **35 passed** | **35 passed** | 35 — agrees |
| frontend | **633 passed (46 files)** | **681 passed (47 files)** | 633 (46) — agrees |

I measured foundation and frontend at base myself before editing anything and both matched
the integrator's figures exactly. I did not run the battery separately at base — it is a
four-minute suite, it is untouched by a frontend-only change, and its figure at exit is
identical to the base figure, which is the evidence that matters. **No base figure
differed from what was briefed.**

Frontend is +48 tests in +1 file: 27 in the new `web/tests/unit/run/cost.test.ts` and 21
added to `web/tests/unit/screens/run-progress.test.ts`.

## Elapsed

**24 m 24 s**, measured, not estimated: `date +%s` recorded at STEP 0 on arrival and again
after the gate returned.

```
start  2026-09-18T17:50:02+05:00
end    2026-09-18T18:14:26+05:00
       1464 s
```

This excludes the earlier STEP 0 stop, which was a separate span before the integrator
pushed.
