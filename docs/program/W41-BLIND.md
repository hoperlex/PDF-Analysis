# W41-BLIND — make the guards reach the state that carries the defect

**task_id:** `W41-BLIND` · **wave:** 41 · **lane:** `gate-w41b`
**worktree:** `/root/w41blind` · **branch:** `agent/w41-blind` · **base:** `295ff04`

> **Opened before the first measurement**, as the brief requires. Every figure below says
> the commit it was taken at.

## 0. A base the brief got wrong

The brief names its base as `6aeda82` (`alpha-w40`). The worktree it dispatched stands at
`295ff04`, which is `6aeda82` plus the dispatch commit carrying the brief itself. Nothing
was rebased; every figure here is taken at `295ff04` or later and says which.

## 1. The principle, stated once because the next reader will be tempted to undo it

> **Coverage is derived from the contract. The seeds are not.**

The assertion asks *"is every member of every translated schema rendered by some state in
this matrix"*, and it reads the members out of `contracts/api/v1/openapi.json` at run time.
The **answer** must be a human's. Deriving the fixtures from the contract as well would make
a tenth stage cover itself, silently, with whatever default a builder chose — the same
silence one level up, and the shape this task exists to stop. **A new member must redden, so
that somebody decides what the screen does with it.**

That is also why the evidence is a `data-` attribute and never the rendered label. The label
is produced by the same map the language half of the guard judges, so a coverage check that
read labels would share an assumption with its subject and could not see the subject being
wrong — `OPERATING_CONSTRAINTS.md` §12.

## 2. B1 — the coverage of `rendered-language.guard.test.ts` is now an assertion

### 2.1 What was blind, measured before anything was written

Measured at `295ff04`, by rendering the matrix and reading the `data-` attributes out of the
markup of all 15 screens × 12 cache states:

| schema | attribute | reached / declared | never rendered |
|---|---|---|---|
| `RunState` | `data-run-state` | **8 / 8** | — |
| `StageStatus` | `data-stage-status` | 1 / 4 | `partial`, `failed`, `skipped` |
| `Verdict` | `data-verdict` | 2 / 4 | `rejected`, `needs_manual_review` |
| `FindingCategory` | `data-category` | 1 / 2 | `explicit_placeholder` |
| `StageId` | `data-stage-id` | 4 / 9 | `block_analysis`, `finding_merge`, `finding_review`, `finding_correction`, `norm_verification` |
| `ProviderMode` | `data-provider-mode` | 1 / 2 | `live` |
| `CostBasis` | `data-cost-basis` | 1 / 2 | `estimated` |
| **total** | | **18 / 31** | **13 members** |

**Thirteen contract members carried a Russian label that no state in this guard's matrix
ever put on a screen.** Every assertion this file makes about them was vacuous. `RunState`
is the only schema at 8/8, and only because a wave-33 judge's mutation died quietly and
somebody chased it — which is the whole of `D-69`'s complaint.

Command, at `295ff04`: a probe over `renderedScreens()` counting
`data-<attr>="<member>"` occurrences per contract enum; it is now the permanent assertion
`renders every member of every translated schema, and NAMES the one it does not`.

### 2.2 The repair

`550ebde`. Two halves, and only the first is new machinery.

- **`SCHEMA_MARKERS`** says, per schema, which `data-` attribute carries the machine value
  on a rendered screen, and why. The members are read from the contract at run time. A
  member no state renders makes the file red **naming the member and the attribute it
  looked for**, because `D-61` records that a guard naming the wrong offence is worse than
  one that misses.
- Three supporting assertions, so the check cannot pass by asking nothing: every schema in
  `TRANSLATED_SCHEMAS` must have a marker and every marker a schema (both directions); every
  attribute must occur at least once in the corpus (a renamed attribute is then red *as a
  rename*, not as 9 phantom unseeded members); and the schemas together must declare more
  than 20 members, so a contract that parsed to nothing is red rather than trivially
  satisfied.
- **The seeds were extended by hand** to cover all 31 today: nine stage ids each carrying a
  different `StageStatus`, one finding per `FindingCategory` and per `Verdict`, one decision
  event per `Verdict`, journal rows for both categories, and one new cache state
  (`live-estimated-run`) carrying the other `ProviderMode` and the other `CostBasis`.

### 2.3 The falsification — mutate, red, revert, green

All three run in `/root/w41blind-mut`, a `git archive` of `550ebde` with `web/node_modules`
copied beside it and `node_modules/.vite` cleared between cases. **Baselined unmutated
first — 15 passed** — per `OPERATING_CONSTRAINTS.md` §10: a red from a copy you never
baselined is not evidence.

**Case A — a contract member added, and nothing seeded for it.** This is the case the brief
asks for by name.

```
contracts/api/v1/openapi.json: components.schemas.StageId.enum += "clause_crossref"
```

```
× the matrix covers the contract … > renders every member of every translated schema, and NAMES the one it does not
AssertionError: the contract publishes these members and NO state in CACHE_STATES renders one …
+   "StageId.clause_crossref (no data-stage-id=\"clause_crossref\")"
Tests  1 failed | 14 passed (15)
```

**And `finds none at all` stayed green.** The guard went red *for not being seeded*, not for
the unrelated reason that the new word is Latin — the new word never reached a screen at
all, which is precisely what was wrong with it. Both halves shown, as the brief asks.

**Case B — an English label on a member the repair newly seeds.**

```
web/src/shared/ui/stage-label.ts
-  block_analysis: 'Блочный и визуальный анализ',
+  block_analysis: 'Block and visual analysis',
```

```
× … finds no English on a rendered screen that D-53 has not already recorded
+   "\"Block and visual analysis\"  Block analysis and visual  [run]"
+   "\"после: Анализ текста, Block and visual analysis\"  Block analysis and visual  [run]"
× … finds none at all
Tests  2 failed | 13 passed (15)
```

**Case C — the same English label, against the seed matrix as it stood at `295ff04`.** The
nine-stage seed is put back to the four it had been since wave 32 and nothing else changes.

```
Tests  1 failed | 14 passed (15)
```

and the one failure is **not** the language check. `finds none at all` is **GREEN over an
English stage label on the run screen** — the guard rendered, saw, and permitted, for the
eighth time in seven waves. What is red is the new coverage assertion, naming all eight
members the old matrix never reached, `StageId.block_analysis` among them:

```
+   "StageId.block_analysis (no data-stage-id=\"block_analysis\")"
+   "StageId.finding_correction (no data-stage-id=\"finding_correction\")"
+   "StageId.finding_merge (no data-stage-id=\"finding_merge\")"
+   "StageId.finding_review (no data-stage-id=\"finding_review\")"
+   "StageId.norm_verification (no data-stage-id=\"norm_verification\")"
+   "StageStatus.failed (no data-stage-status=\"failed\")"
+   "StageStatus.partial (no data-stage-status=\"partial\")"
+   "StageStatus.skipped (no data-stage-status=\"skipped\")"
```

**That is the deliverable.** A structural check caught a blindness that, in all seven
previous instances, only a quietly-dying mutation had ever found — and it caught it without
anybody having to think of the mutation first.

