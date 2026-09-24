# W43-COMPARE — the stage-comparison skeleton

**task_id:** `W43-COMPARE` · **wave:** 43, stage A · **lane:** `gate-w43a` ·
**worktree:** `/root/w43comp` · **branch:** `agent/w43-compare` · **base:** `b7d9bc4`

This file was opened **before the first measurement** (`c4683ec`), per the brief's second
deliverable. Every figure below carries the commit it was taken at, because a figure without
its tree is not a measurement (`OPERATING_CONSTRAINTS.md` §4.62).

## 1. What this screen is

`R-23`: *«Сравнение стадий — очень важно; хотя бы скелет с заглушками сейчас, реализация по ходу
альфы.»* The screen puts **two runs of one published version** side by side on the facts the
contract already carries, and says plainly which comparison is not here yet.

Address: `/projects/{project_uid}/versions/{version_uid}/comparison`.

It hangs off the **version** and not off a run. A version is immutable, so a difference between
two of its runs is a difference in the analysis rather than in the document. Mounting it under
one run would make the other run a parameter of the first, which is a relationship nothing in
the contract supports.

**One request.** `listRuns` over the version, through the existing `useRunList`. Each item is
the whole `RunStatus`, byte-identical to what `getRunStatus` answers for that run, so a
comparison needs no per-run fetch — and adds no second polling cadence beside `useRunStatus`.

**Twelve compared facts, four verdicts.** `state`, `provider_mode`, `created_at`, `terminal_at`,
duration, `published_finding_count`, `diagnostic_observation_count`, `model_call_count`,
`cost_micros`, `cost_basis`, `terminal_reason`, `terminal_detail` — plus one row per stage either
run knows about, with status and elapsed compared separately.

The verdict is `same`, `differs`, `one_sided` or `absent`, and the fourth is the one that would
otherwise be silently wrong: **a fact neither run carries was not compared.** Two `published`
runs carry no `terminal_reason` between them, and a row reading «совпадает» there would claim
they agree about a failure neither of them had.

## 2. Premises in the brief, checked before use

All of the brief's contract premises hold. Checked against `contracts/api/v1/openapi.json` at
`b7d9bc4`, before any of them was used:

| premise | verdict |
|---|---|
| `listRuns` over a version | holds — `GET /versions/{version_uid}/runs` |
| `getRunStatus` with its stages | holds, and **is not needed**: `listRuns` items are the whole `RunStatus`, stages included, which the operation's own summary states |
| `published_finding_count`, `diagnostic_observation_count`, `cost_micros`, `model_call_count` | hold, all four optional |
| `state`, `terminal_reason` | hold; `state` required, `terminal_reason` optional |
| `terminal_detail`, since wave 42 | holds in the contract **and** in `web/src/shared/api/generated/types.gen.ts:457` |
| `PC01_STAGE_IDS` schedules four of the contract's nine | holds |
| `alpha-w42` frontend baseline `1032 in 72 files` | holds — measured `1032 in 72` at `4a2c493` |

**One correction, and it is an addition rather than a contradiction.** The brief says
`terminal_detail` is available "since wave 42". It is — in the contract and in the generated
client — but **`grep -rn 'terminal_detail' web/src` at `b7d9bc4` matched the generated types and
nothing else.** Wave 42 carried `D-46` to the wire and to the database and not to a screen. This
widget is the first consumer in `web/src`.

## 3. What the screen may say, and what it may not

`C2`. The screen tells a reviewer that deeper comparison arrives later — *«Разбор того, что
именно изменилось внутри этапа … появится позже»* — and never explains this programme's
transport (`R-18`; `D-58` was closed by deleting exactly that). Which operation carries which
field is in the module comments and in this file.
`tests/unit/screens/stage-comparison.test.ts` asserts that no reviewer-facing string contains
`listRuns`, `getRunStatus`, `RunStatus`, `API` or `endpoint`.

`C1`'s addendum — **no invented numbers.** Where the contract carries a figure the screen prints
it; where it does not, the screen prints `—` and names the verdict. Three cases are kept apart
on purpose and each has a test:

- **an absent count is not zero** — `published_finding_count: 0` is "published nothing", its
  absence is "never reached publication" (`D-3`);
- **a cost with no call count is not a cost** — `D-15`: the run total sums across retry
  attempts, so `runCost` calls it `unreadable` and the row reads `one_sided`, never `same`
  against a real figure;
- **a backwards instant pair is not a duration** — it contributes `null` rather than a negative
  span.

`C3`. `STAGE_LABELS` names every stage; the contract value keeps its home in `data-stage-id`.
**No new state was added to the language guard's matrix on account of vocabulary** — the screen
introduces no contract member the matrix did not already seed. What it did need is a cache
state, and that is §4.

## 4. Instrument reach — the measurement this wave is

**Stated plainly, because the brief asks for it and a stream that reports its own weakness and
one that does not are distinguishable.**

### 4.1 Neither frontend instrument evaluated this screen until it was told to

Measured at `4a2c493` — the screen committed, both instruments untouched. The probe is the
judge's: **an English sentence on the screen and a border at 1.06:1 on it.**

| assertion | probe result at `4a2c493` |
|---|---|
| `rendered-language.guard.test.ts` › *R-18: no Latin word reaches a reviewer* › **finds none at all** | **GREEN** — 1 passed, 18 skipped |
| `contrast.test.ts` › *R-33: every border that meets on a screen clears 3:1* › **names the theme, the ratio and the site of every border under the floor** | **GREEN** — 1 passed, 18 skipped |

An English sentence sat on a reachable address and the language guard did not see it. A border
at 1.06:1 sat on the same screen and the contrast census did not see it. **Both instruments were
sound and blind, for the eighth and ninth time in this programme.**

### 4.2 What each one *did* notice, and it was only that something new exists

The same tree, whole suite, `4a2c493`: **2 failed | 1030 passed (1032 in 72 files)**. Both
failures are coverage assertions, not defect assertions:

- **the contrast census** named six selectors — `._absent`, `._choice`, `._instant`,
  `._ordinal`, `._summary`, `._verdict` — under *names every colour-bearing rule that NO
  rendered screen reaches*. It could only do that because the screen ships a collocated
  `.module.css` and `import.meta.glob('../../../src/**/*.module.css')` picks one up
  automatically. **A screen that had reused the global `am-*` classes would have been wholly
  invisible to this census.**
- **the language guard** named exactly one string — `"Для сравнения нужны два прогона этой
  версии."` — under *renders every one of them, and NAMES the branch it does not reach*. That
  comes from `branchLabelsInSource()`, which scans `web/src/**/*.tsx` for `title=`/`what=` on
  the five mandatory states and for the pager's two controls. It named one of my four state
  labels and not the others, because the other three are strings the matrix already renders
  from `run-list`. **Nothing in that mechanism looks at prose, headings, table cells or
  attributes.**

So wave 41's repair is **half-reaching**, measured: the *branch* census is derived from the tree
and does reach a new screen; the *screen* census is still a hand-written literal and does not.
Wave 42's contrast repair is in the same shape one level out — the stylesheet scan is derived,
the screen list is not.

### 4.3 What I then did, and why it is not a tidy-up

I **pointed both instruments at the screen** (`ed1b3e6`), and I am saying so rather than
reporting a clean green.

There was no green-preserving alternative for the census: its other branch is
`UNREACHED_BY_ANY_SCREEN`, and that file's own text calls an entry whose reason is only "it is
not rendered" *"the defect being laundered"*. The language guard's branch scan demanded a state
that renders the not-applicable title, which likewise had to be seeded or excused.

**The before-measurement is preserved and reproducible.** `git checkout 4a2c493`, re-apply the
two-line probe, and run the two assertions in the table above.

After wiring, the identical probe:

| assertion | probe result after `ed1b3e6` |
|---|---|
| **finds none at all** | **RED** — `"PROBE: this sentence is deliberately English and must not survive the probe."` |
| **names … every border under the floor** | **RED** — `--am-surface` on `--am-paper`, 1.08:1 light and 1.11:1 dark, at `StageComparisonPage with two runs div.am-page__body > div._comparison > p._summary` |

The probe was reverted in the same commit range; the tree carries neither half.

**The wiring needed one seed the existing matrix could not supply.** Every cache state in that
file seeds **one** run, because every other screen reads one. A comparison screen with one run
renders its not-applicable block, so all nine states would have rendered that block and **every
assertion about its tables would have been vacuous.** `twoRunClient` seeds a pair chosen so all
four verdicts render in one pass. Its first version called `loadedClient` directly and crashed
`review-page.tsx` reading `.data.items` off a bare model — `D-57` seen from inside a test, which
is why it now takes the loaded builder the way `pagedClient` does.

### 4.4 The one instrument that reached the screen on its own is not a frontend instrument

`tests/e2e/test_pc01_journey_conformance.py::test_the_journey_walks_every_screen_the_application_offers`
reddened naming the new address, with no prompting and no list to maintain, because it derives
its subject with `rglob("page.tsx")` over `web/src/app` instead of reading a literal. That is
the difference between the instruments that reached this screen and the ones that did not, and
it is a property of the **query**, not of the language it is written in.

## 5. Guards added, each shown to fail

`tests/unit/run/run-comparison.test.ts` (19 cases), `tests/unit/screens/stage-comparison.test.ts`
(16 cases), and four cases added to `tests/unit/screens/routes.test.ts`. Mutation sweep at
`6b24bd8`; every mutation reverted with `git checkout --`, tree clean afterwards.

| # | mutation | target | result |
|---|---|---|---|
| M1 | `if (!hasLeft && !hasRight) return 'absent';` → `return 'same';` | `run-comparison.test.ts` | RED — *is `absent`, and is never `same`* |
| M2 | `comparableCostMicros` reads `run.cost_micros` directly instead of through `runCost` | `run-comparison.test.ts` | RED — *treats a cost with no call count as absent rather than as a figure* |
| M3 | `defaultPair` re-sorts by `created_at` instead of trusting the server order | `run-comparison.test.ts` | RED — *takes the first two items, because `listRuns` answers newest first* |
| M4 | `durationComparison: compareReadings(leftSide.status, rightSide.status)` | `run-comparison.test.ts` | RED — *compares the status and the elapsed span separately* |
| M5 | `{STAGE_LABELS[row.stageId]}` → `{row.stageId}` | `stage-comparison.test.ts` | RED — *renders a stage id as a Russian label…* |
| M6 | the absent cost-basis cell prints `'0'` instead of `'—'` | `stage-comparison.test.ts` | RED — *marks it `absent` and puts a dash on both sides* |
| M7 | the terminal-detail cell prints the digest instead of a count | `stage-comparison.test.ts` | RED — *carries `terminal_detail` as an attribute and a count, never as prose* |
| M8 | the route checks only `version_uid`, not `project_uid` | `routes.test.ts` | RED — *a malformed version address 404s on the comparison route too* |

## 6. Measurements

| what | figure | commit | command |
|---|---|---|---|
| frontend suite, baseline with the screen and no instrument wiring | **1032 in 72 files** — 2 failed, 1030 passed | `4a2c493` | `npm --prefix web run test -- --run` |
| frontend suite, final | **1070 passed in 74 files** | `6b24bd8` | `npm --prefix web run test -- --run` |
| typecheck | clean | `6b24bd8` | `npm --prefix web run typecheck` |
| lint | clean | `6b24bd8` | `npm --prefix web run lint` |
| foundation | **35 passed** in 30.65s | `6b24bd8` | `make gate` |
| canonical battery | **2441 passed, 1 failed, 5 skipped, 4 warnings, 169 subtests** in 646.76s | `6b24bd8` | `make gate` |
| `make gate` verdict | **no `GATE OK`** — `grep -c 'GATE OK' /root/w43a-gate.log` = **0**; the gate's own line reads *"GATE: the canonical battery failed with pytest exit status 1."* | `6b24bd8` | `make gate > /root/w43a-gate.log 2>&1` |

The battery population is unchanged: 2441 + 1 = 2442, exactly `alpha-w42`'s figure. This branch
adds no Python test.

**The one failure is `tests/e2e/test_pc01_journey_conformance.py::test_the_journey_walks_every_screen_the_application_offers`**,
and it is the shared-hotspot collision the integrator owns this wave —
`tests/e2e/pc01/journey/manifest.json` is in neither stage-A stream's `allowed_paths` and both
streams add screens. Run alone it is **1 failed, 53 passed in 0.15s**, naming exactly one
screen: `/projects/{project_uid}/versions/{version_uid}/comparison`. Not worked around, not
skipped, not weakened.

**On contention** (§4.6): the battery took 646.76s against a normal ~277s, with `gate-w43b`'s
containers up alongside it for the whole run. That is evidence about the machine. It is **not**
what produced this red: the failing assertion is a deterministic read of a JSON file and runs in
0.15s alone.

## 7. Outside the grant — reported, not repaired

1. **`web/src/shared/lib/routes.ts` has no `comparison()` builder.** Outside
   `allowed_paths`. Consequence: the address is served and **nothing in the application links to
   it** — it is reachable only by being typed. The repair is two lines:

   ```ts
   /** Two runs of one published version, side by side. */
   comparison: (projectUid: string, versionUid: string): string =>
     `/projects/${projectUid}/versions/${versionUid}/comparison`,
   ```

   plus one row in `ADDRESSES` in `tests/unit/screens/routes.test.ts` pointing at
   `src/app/projects/[project_uid]/versions/[version_uid]/comparison/page.tsx`.

2. **No link from the version screen.** `web/src/_pages/version-detail/**` is outside
   `allowed_paths`. The natural caller is `version-detail-page.tsx`'s `actions`, beside «К
   проекту», or a link under the «Прогоны» heading. `web/src/_app/app-frame.tsx` is
   `W43-PREP`'s this wave and is untouched — this screen wants no frame entry anyway, since it
   is a child of a version rather than a top-level section.

3. **`tests/e2e/pc01/journey/manifest.json`** — the integrator's. The entry this screen needs,
   and it calls **exactly one operation**:

   ```json
   {
     "name": "comparison",
     "path": "/projects/{project_uid}/versions/{version_uid}/comparison",
     "page_module": "web/src/app/projects/[project_uid]/versions/[version_uid]/comparison/page.tsx",
     "expects_api": [
       { "method": "GET", "path": "/versions/{version_uid}/runs", "operationId": "listRuns" }
     ],
     "follow": null
   }
   ```

   `expects_api` is a real claim and not an omission: the screen issues `listRuns` on mount in
   every state, including the one-run and no-run states, so the claim holds whatever the stand
   happens to hold.

4. **`D-69` should not be closed on the strength of wave 41's and wave 42's repairs.** §4.1
   measured both instruments green over a fully English sentence and a 1.06:1 border on a
   reachable screen. The cause named in `D-69` — *a guard's seed matrix is a hand-written
   literal and nothing checks that the literal covers the space* — is still true of
   `SCREENS`/`CACHE_STATES` in `rendered-language.guard.test.ts` and of `screens()` in
   `tests/unit/styles/screens.ts`. The shape of a repair is in §4.4: derive the screen list from
   `web/src/app`'s route tree the way the journey conformance check does, rather than from an
   import list.

5. **`terminal_detail` reaches a reviewer nowhere else.** `D-46`'s classifiers now render on this
   one screen, as a count and a `data-` attribute. They are *not* rendered on the run screen,
   where `W29-SAY`'s sentence — *your document is fine, the provider is fine, this deployment has
   no recording for it* — is the one a failed run actually needs. Worth a wave; not this
   stream's grant.

## 8. Known limitations

- **The chooser's `useState` branch is not reached by any static render pass.** Selecting a
  different pair, and the `data-same-run` block that appears when both sides are the same run,
  need an event the harness cannot fire. Stated rather than left looking like coverage; the
  underlying selection is a `Map` lookup and the four verdicts it feeds are covered by
  `run-comparison.test.ts`.
- **The comparison is over the first page of runs.** `useRunList` is called with no cursor, so a
  version with more than `RUN_PAGE_LIMIT` runs offers only the newest 50 in the two choosers.
  The default pair is unaffected — `listRuns` answers newest first, so the two newest are on the
  first page whatever its size.
- **No stage-content comparison, by design.** `listRuns` carries `published_finding_count` and
  not the findings, so which finding appeared or disappeared between two runs is not in this
  data at any cost. The screen says so to the reviewer and this file says why.
- **Nothing links to the screen** until §7.1 and §7.2 land.
