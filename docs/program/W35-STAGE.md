# W35-STAGE — the stage table gets tokens, names and an order, and the contrast census turns out to have been measuring nothing about collocated modules

**Task:** `W35-STAGE`, closing `D-62`. **Base:** `91b9c0d`. **Branch:** `agent/w35-stage`,
worktree `/root/w35stage`. **Contracts touched:** none. **Consumers touched:** one —
`widgets/run-progress`'s degradation list, which is in this task's `allowed_paths`.
**Rules changed:** one — `StageId` leaves the rendered-language guard's permitted set.

---

## 0. In one paragraph

All three halves of `D-62` are closed: the table is on the styling layer, the nine stages
have Russian names, and the order the data always held is now rendered. Two of the brief's
premises did not survive measurement and both changed the work. **The nine stages are a
graph, not a line** — `stage-registry.json` forks twice and joins once — so the ordinal
covers only the four stages PC-01 schedules, whose being a chain is asserted against the
registry rather than assumed. And **the twelve inline styles were not an absence of
styling but a duplicate of it**: `globals.css` styles `table`, `thead th`, `tbody td`,
`code` and `em` by element selector, so the table always reached both palettes, and eleven
of the twelve attributes overrode a tokenised rule with a literal. The repair was to
delete, not to re-declare. The largest find is not in `D-62` at all: **the contrast census
could not see a collocated CSS module's rules through the cascade**, because it parsed the
authored class names and the markup carries the bundler's scoped ones — so for two waves
the sentence "the census crosses MODULES with the rendered markup" was false, and
`project-sections.module.css` declined to carry colour for exactly that reason. Gate:
`GATE OK`, battery **2047 / 5 / 169** unchanged, foundation **35**, frontend **908 → 916 in
63 → 64 files**, every test accounted for below.

---

## 1. Before and after

### 1.1 What the table was

| | before (`91b9c0d`) | after |
|---|---|---|
| styling | 12 `style={{…}}`, 0 tokens — **and** every `globals.css` element rule for `table`/`th`/`td`/`code`/`em` underneath them | 1 collocated module, 7 class rules, 0 colour literals, 0 duplicated element rules |
| first column | `<code>source_preparation</code>` ×4 | `Подготовка источника` … , contract value in `data-stage-id` |
| order | implied by row order, asserted nowhere | `№` column, 1–4, plus each stage's declared dependency under its name |
| degradation list (`run-progress`) | `<code>text_analysis</code>` | `Анализ текста`, value in `data-degraded-stage` |
| language guard | `StageId` **permitted** as visible text | `StageId` in `TRANSLATED_SCHEMAS` |

### 1.2 The contrast figures, per theme

Every pair the table puts on a screen, measured by
`web/tests/unit/styles/contrast.test.ts` over the rendered `RunProgress` screens in six run
states. Threshold is WCAG 2.1 AA: 4.5 for text, and `null` for these borders because a
`td` is not an operable component (1.4.11 reaches a boundary only when it is the sole thing
identifying a control).

| pair | role | light | dark | needs |
|---|---|---|---|---|
| `--am-ink` / `--am-surface` | stage name, elapsed | **16.31:1** | **15.24:1** | 4.5 |
| `--am-ink-muted` / `--am-surface` | header, ordinal, dependency, stamps, "не начинался" | **5.55:1** | **9.15:1** | 4.5 |
| `--am-line-strong` / `--am-surface` | the rule under the header | 3.29:1 | 4.29:1 | — |
| `--am-grid-line` / `--am-surface` | the rule between rows | 1.13:1 | 1.31:1 | — |
| *(before)* `--am-ink-muted` / `--am-surface-sunken` | the old `<code>` chip | 5.26:1 | 9.36:1 | 4.5 |

Nothing regressed and nothing new is registered: the whole census is **123 pairs per
palette, 0 unexcused failures**, and the four `REGISTERED` rows are the same four
`W32-CONTRAST` left.

`--am-ink-soft` is used nowhere here, per the brief. Its separation from `--am-ink-muted`
is **1.10:1 in the light palette** — and **1.64:1 in the dark one**, where three ink levels
survive. The brief gives the light figure as if it were the palette-independent one; the
guard is already per-palette and says both (`the light palette has two visible levels and
three tokens` / `the dark palette has three`).

### 1.3 The commands

```
cd /root/w35stage
npm --prefix web test                                   # 916 passed in 64 files
npm --prefix web run typecheck                          # tsc --noEmit, clean
npm --prefix web run lint                               # eslint, clean
make gate > /root/w35-logs/stage-gate.log 2>&1          # GATE OK
npx --prefix web vitest run --root web tests/unit/styles/contrast.test.ts
```

---

## 2. Where the stage-label map lives, and why

**`web/src/shared/ui/stage-label.ts`, exported from `shared/ui`'s public API on the day it
was written.**

The brief names the trap precisely: `VERDICT_LABELS` and `STATE_LABELS` were each written
private and each had to be exported once a second consumer rendered the raw value around
them. The way not to do that a third time is not "remember to export it" — it is to put it
where every consumer that will want it can reach it.

This map had **two** consumers on the day it was written, which is the fact that decides it:

| consumer | layer | reaches `shared` | reaches `entities/audit-run` |
|---|---|---|---|
| `entities/audit-run/ui/stage-table.tsx` | entity | yes | yes (its own) |
| `widgets/run-progress/ui/run-progress.tsx` degradation list | widget | yes | yes |
| *(plausible next)* a stage badge in `shared/ui` | shared | yes | **no** |
| *(plausible next)* `run-failure.ts`'s `details.stage_id` classifier | entity | yes | yes (its own) |

`shared` is reachable from every layer; `entities/audit-run` is reachable from widgets,
features and pages but not from `shared/ui`'s own badges nor from another entity. The
narrower placement is exactly what made the other two maps move later.

The argument from ownership points the same way. `entities/audit-run` owns a **run
reading** — `stageRows`, `elapsedMs`, the outcome classification. A stage id is not the run
aggregate's private vocabulary: it is a contract enum that also arrives in an error
envelope's `details.stage_id` and in `RunStatus.degradation_set`, and it sits beside
`STATE_LABELS` (`RunState`) and `STAGE_STATUS_LABELS` (`StageStatus`), which are already
there for the same reason. A label is not an identity, and translating a contract value for
the screen is presentation.

**What did NOT go into `shared/ui`:** `STAGE_DEPENDS_ON`, the pipeline topology, which is in
`entities/audit-run/model/run-presentation.ts` beside `PC01_STAGE_IDS`. How a stage is
*named* to a person is presentation; what the run's stages *wait for* is the run model.

**And the third instance is already sitting there, unfixed and reported rather than
touched.** `STAGE_STATUS_LABELS` in `shared/ui/stage-status-badge.tsx` is private today.
It has one consumer — its own badge — so exporting it now would be a declared constant with
no consumer, which this programme has ruled against separately. It is named here so the
next session that needs a stage status as a bare word finds this sentence instead of
writing a local copy.

---

## 3. A line or a graph — established from our own contract

**A graph.** From `contracts/analysis/v1/stage-registry.json`, `depends_on`, all nine
stages:

```
source_preparation → page_geometry_extraction → document_context_build
                                                     ├→ text_analysis  ─┐
                                                     └→ block_analysis ─┴→ finding_merge
                                                                              ├→ finding_review → finding_correction
                                                                              └→ norm_verification
```

- **Two fan-outs:** `document_context_build` is waited on by `text_analysis` **and**
  `block_analysis`; `finding_merge` is waited on by `finding_review` **and**
  `norm_verification`.
- **One join:** `finding_merge` waits on both `text_analysis` and `block_analysis`.
- **Four of the nine may not run at all:** `block_analysis`, `finding_review`,
  `finding_correction`, `norm_verification` all carry `status_policy.skip_allowed: true`,
  and the last three carry `execution.mandatory: false`.

This was established from **our** registry, not from legacy's `stage-algorithm-branch` /
`stage-algorithm-split` vocabulary. Legacy forking is not evidence that ours does; it
happens that both do.

### What was rendered as a result

**An ordinal over the four stages PC-01 schedules, and a declared dependency under every
stage name.**

The brief's instruction was "if any stage is conditional or parallel, an ordinal is a lie,
and you report that instead of drawing something false". Both halves are true of the nine
and **neither is true of the four PC-01 schedules**: `source_preparation` →
`page_geometry_extraction` → `document_context_build` → `text_analysis` is a strict chain,
every one of them `mandatory: true` and `skip_allowed: false`. So the ordinal is honest over
exactly the set the table numbers, and a stage the run reported outside that schedule shows
`—` rather than a position.

That is a claim about the contract, so it is asserted against the contract rather than
trusted:

- `says the four stages PC-01 schedules ARE a chain, which is what licenses the ordinal` —
  the first waits for nothing, each later one waits for exactly its predecessor, and no two
  scheduled stages share a dependency set;
- `says the nine stages are a GRAPH, which is why nothing numbers them` — the fan-outs and
  the join are asserted by name, so this file states the finding rather than describing it.

Adding `block_analysis` to `PC01_STAGE_IDS` reddens the first (see M4 below). **The column
cannot quietly become an invention.**

The dependency is the half that survives a fork, which is why it is rendered beside the
ordinal rather than instead of it: `finding_merge` waits on two stages and can say so in a
cell, where a table would otherwise have to draw an arrow. It is a `Record<StageId,
readonly StageId[]>` mirroring the registry, held to it in both directions by the guard, so
it cannot drift.

---

## 4. The guard changes, and the red each one produces

### 4.1 `StageId` leaves the permitted set

`web/tests/guards/rendered-language.guard.test.ts`:

- `TRANSLATED_SCHEMAS` gains `StageId` — five schemas, not four.
- Its **self-tests move with it, in both directions**, because the file asserts the split
  rather than describing it: `text_analysis` leaves the "still permitted" list and the nine
  stage ids join the "no longer permitted" list; `unexplainedLatin('text_analysis')` leaves
  the *does not redden* case and joins the *now reddens* case as `['text', 'analysis']`,
  with `source_preparation` beside it. Nothing was deleted — a control that quietly loses a
  case is how a guard stops proving what its name says.

### 4.2 A new guard: `web/tests/guards/stage-vocabulary.guard.test.ts`

Five cases. It reads `openapi.json` and `stage-registry.json` and judges `STAGE_LABELS` and
`STAGE_DEPENDS_ON` against them. It exists because the type checker holds only the map's
**keys**: it cannot see a label that is still an English word, a label that is a copy of the
machine value, or a dependency list that has stopped matching the registry. It also reaches
the five stages no seeded screen renders, which the rendered-language guard structurally
cannot.

### 4.3 The mutations, and the red verbatim

Nine, each applied to a committed tree, run alone, and reverted (`git checkout -- web/`,
tree clean after each). Logs: `/root/w35-logs/stage-mutations/`.

| | mutation | guard | result |
|---|---|---|---|
| **M1** | the stage table renders `<code>{row.stageId}</code>` again | rendered-language | **red**, 2 cases |
| **M2** | `text_analysis: 'Text analysis'` | stage-vocabulary **and** rendered-language | **red**, 3 cases |
| **M3** | `norm_verification: ['finding_review']` | stage-vocabulary | **red**, 2 cases |
| **M4** | `block_analysis` added to `PC01_STAGE_IDS` | stage-vocabulary | **red** |
| **M5** | `.name { color: #16191d }` | styling-layer | **red** |
| **M6** | `.table th { color: var(--am-line) }` (1.26:1) | contrast | **red**, both palettes |
| **M6b** | the same, on `.ordinal`, after the module was slimmed | contrast | **red**, both palettes |
| **M7** | M6 **plus** the census reading authored module names | contrast | **the AA failure passes** — §5 |
| **M8** | `ordinal: null` in `stageRows` | stage-rows | **red** |
| **M9** | the degradation list renders `<code>{stageId}</code>` again | rendered-language | **red**, 2 cases |

**M1** — the proof that the `TRANSLATED_SCHEMAS` move is the whole of the repair. This is
the markup that was green at `91b9c0d`:

```
 FAIL  tests/guards/rendered-language.guard.test.ts > R-18: no Latin word reaches a reviewer
       that a contract did not put there > finds no English on a rendered screen…
AssertionError: … expected [ …(4) ] to deeply equal []
+ [
+   "\"document_context_build\"  build context document  [run]",
+   "\"page_geometry_extraction\"  extraction geometry page  [run]",
+   "\"source_preparation\"  preparation source  [run]",
+   "\"text_analysis\"  analysis text  [run]",
+ ]
```

**M2**:

```
 FAIL  tests/guards/stage-vocabulary.guard.test.ts > every stage the contract publishes has
       a Russian name > names each stage in the reader’s language and never in the machine’s
AssertionError: expected { stageId: 'text_analysis', …(1) } to deeply equal { stageId: 'text_analysis', …(1) }
 FAIL  tests/guards/rendered-language.guard.test.ts > … > finds none at all
AssertionError: expected [ 'Text analysis' ] to deeply equal []
```

**M3**:

```
 × matches every stage’s declared depends_on, in both directions
   → expected { source_preparation: [], …(8) } to deeply equal { source_preparation: [], …(8) }
 × says the nine stages are a GRAPH, which is why nothing numbers them
   → expected [ 'document_context_build', …(1) ] to deeply equal [ 'document_context_build', …(1) ]
```

**M4** — the ordinal's licence:

```
 × says the four stages PC-01 schedules ARE a chain, which is what licenses the ordinal
   → expected { stageId: 'block_analysis', …(1) } to deeply equal { stageId: 'block_analysis', …(1) }
```

**M5**:

```
 FAIL  tests/unit/styles/styling-layer.test.ts > every colour is a token read, so the second
       theme stayed additive > holds over globals.css and every collocated module
AssertionError: expected { …(2) } to deeply equal { …(2) }
```

**M6 / M6b** — the census naming the site and the theme:

```
 FAIL  tests/unit/styles/contrast.test.ts > every pair that meets on a screen clears the
       threshold its role asks of it > holds in BOTH palettes…
+   { "needs": 4.5, "pair": "text|--am-line|--am-surface|-|-", "ratio": 1.26,
+     "theme": "light", "where": "RunProgress published thead > tr > th" },
+   { "needs": 4.5, "pair": "text|--am-line|--am-surface|-|-", "ratio": 1.44,
+     "theme": "dark",  "where": "RunProgress published thead > tr > th" },
```

**M8**:

```
 × numbers the scheduled stages from one, in the order they run
   → expected [ null, null, null, null ] to deeply equal [ 1, 2, 3, 4 ]
```

**M9**:

```
AssertionError: expected [ 'text_analysis' ] to deeply equal []
```

**Nothing here was a coverage report.** Every mutation reddened a case that names the
defect, and M7 is the one that establishes the opposite for the *previous* instrument.

---

## 5. The contrast census could not see a collocated CSS module, and it is a §12 shape

**The largest finding of this task, and it is not in `D-62`.**

`web/tests/unit/styles/contrast.test.ts` carried `MODULES`, a literal array of one file, and
crossed it with the rendered screens. Two things were wrong with it, and the second is the
one that mattered.

**The list.** A second module landed one wave after the census was written
(`project-sections.module.css`, `W33-SECT`) and the array never grew — the
hand-maintained-subset shape `W30-LISTS` closed eighteen instances of.

**The names.** A CSS module's class names are **scoped at build time**. The module declares
`.ordinal`; the rendered markup carries `class="_ordinal_b1553c"`, with a different suffix
per file (`_outcome_5f66a5`, `_tabs_1ca4fe`). `parseRules` reads the authored file, so
**every module selector this census ever parsed matched no element**. The cascade half of
the measurement was empty for modules, and the only module pair that ever reached the
register did so through `declaredPairs`, which needs `color` and `background` in one rule —
true of exactly one rule in the tree, `run-progress`'s `.activity`.

**It had already cost something, in writing.** `project-sections.module.css`'s own header
says colour is *"deliberately absent"* because *"a colour declared in a collocated module
is a colour that census cannot see"*. That sentence was **right**, for a deeper reason than
the array, and a session declined the architecture `globals.css` promises because of it.

This is `OPERATING_CONSTRAINTS.md` §12's shape and not carelessness: **the query and its
subject shared no vocabulary, and nothing in the query could reveal that.** The census was
sound — the formula, the thresholds, the cascade, the two palettes are all correct — and
**blind**, on one input class, for two waves. M7 is the demonstration: with a genuine AA
failure of 1.26:1 declared in a module and the census reading authored names, the assertion
`every pair that meets on a screen clears the threshold its role asks of it` **passes**.

**The repair**, in `web/tests/unit/**`, which this task owns:

1. `MODULES` comes from `import.meta.glob('../../../src/**/*.module.css', { eager: true })`
   — the filesystem decides the set, and the same call hands back each module's **own class
   mapping**, so the scoped name is the bundler's rather than a format this guard guessed.
2. Each module's text is rewritten `.local` → `.scoped` before `parseRules`.
3. A new case, `reads a collocated module through the CASCADE, not only through
   declaredPairs`, measures both ways and asserts the scoped census gains pairs — so a
   change that silently reverts to authored names is red rather than merely quieter. M7 is
   that case firing.

Census: **118 → 123 pairs per palette**, **no new failure in either**, `unsupported()`
unchanged.

---

## 6. The gate delta, case by case

```
make gate > /root/w35-logs/stage-gate.log 2>&1   →  GATE OK: battery, foundation, frontend
                                                     and whitespace all pass
```

| half | baseline (`91b9c0d`) | this branch | delta |
|---|---|---|---|
| battery | 2047 passed / 5 skipped / 169 subtests | **2047 / 5 / 169** | **0** — no file under `src/`, `db/`, `tests/` was touched |
| foundation | 35 | **35** | 0 |
| frontend | 908 in 63 files | **916 in 64 files** | **+8 in +1** |
| whitespace | clean | clean | 0 |

The +8, named:

| tests | file | what |
|---|---|---|
| +5 | `web/tests/guards/stage-vocabulary.guard.test.ts` *(new)* | the labels against `openapi.json`; the dependencies against `stage-registry.json`; the nine are a graph; the four are a chain |
| +2 | `web/tests/unit/run/stage-rows.test.ts` | the ordinal is 1–4 and `null` off-schedule; each row carries the contract's dependency |
| +1 | `web/tests/unit/styles/contrast.test.ts` | the collocated-module cascade case (§5) |

**One gate re-run, and it was not the tree.** The first `make gate` died in `make up`:
`Bind for 127.0.0.1:56140 failed: port is already allocated`. `POSTGRES_PORT=56140` is the
value this task's brief assigned, and it is **held by a peer session's container**,
`gate-w34dom-postgres` — wave 34, the live JWT stream. Per `OPERATING_CONSTRAINTS.md` §4.5
a host-wide resource is not scoped to a session, so nothing was done to the peer's
container: this lane moved to **56148** (verified free, `DATABASE_URL` moved with it) and
`make down`/`make gate` ran clean. The S3 ports 59740/59741 were free and are unchanged.
The second run was the only run of the battery, so no figure here is a re-measurement of a
contended one.

---

## 7. Every premise of this brief that measurement found false

**Seven.**

1. **"nine rows of `source_preparation`, `page_geometry_extraction`, `text_analysis`"** —
   the table renders **four** rows, not nine. `PC01_STAGE_IDS` has four members and
   `stageRows` walks it; the other five appear only if a run reports a stage PC-01 does not
   schedule. `D-62` carries the same "nine" and it is wrong in the register too. The map
   *is* keyed on all nine, which is right and is a different statement.

2. **"this table reaches neither [the token layer nor the second palette] — on the dark
   theme it renders in the browser's defaults on a dark surface."** False, and it changed
   the work. `globals.css` styles `table`, `thead th`, `tbody td`, `tbody tr:hover`, `code`
   and `em` by **element selector**, and every one is a token read, so the table reached
   both palettes on both themes. What the twelve inline attributes were is a **token-free
   duplicate** winning on inline specificity — a literal `0.35rem 0.75rem 0.35rem 0` where
   the spacing tokens were, `borderCollapse`/`width` restating `table`, `textAlign: left`
   restating `thead th`. **Eleven of the twelve** overrode a tokenised rule with a literal;
   only `overflowX: auto` had nothing behind it. So the repair is to **delete**, and the
   module carries only the scroller and the cells this wave added — a third copy of
   `thead th`'s padding would be the same defect one layer further out.

3. **"read `run-progress.module.css` first, it is the first such module and the pattern"** —
   true that it is first, and following it as *the* pattern is what the finding in §5 makes
   unsafe: its rules were, and until this task's repair would have remained, invisible to
   the contrast census. The pattern to copy is the colocation, not the assumption that a
   guard is watching it.

4. **"`W32-CONTRAST`'s guard will hold you to it"** — on colour literals, that is
   `styling-layer.test.ts` and it does (M5). On the **contrast of a module's own rules**,
   the guard would not have held anybody to anything (M7, §5). Both halves of the brief's
   sentence pointed at a guard; one of them pointed at a blind one.

5. **"the third ink level is spent … its separation from `--am-ink-muted` is 1.10:1 and the
   guard asserts it stays there."** True of the **light** palette and false of the dark one,
   where the separation is **1.64:1** and three levels survive. The guard is already
   per-palette and says both; the brief states a light-palette figure without the theme,
   which is the shape `W33-THEME` was created to stop.

6. **"`StageId` … nine members"** — correct, and worth recording as the one contract claim
   in the brief that reproduced exactly: nine in `openapi.json`, the same nine in
   `stage-registry.json`, in the same order, asserted both ways.

7. **"if a string you move is named in `tests/e2e/pc01/journey/manifest.json`, stop and
   report it."** Checked and clear: the manifest names **no** stage id, no stage label and
   none of this table's column headings; `refusals.mjs` reads `.am-state`, which this table
   does not use. Nothing in `tests/e2e/**` was read by more than `grep` and nothing was
   changed there.

**And one that is not a premise of the brief but of the tree**, found by an existing guard
firing on this task's prose: `styling-layer.test.ts`'s `referencedClasses` greps `.tsx`
sources for `am-[\w-]*` and cannot tell a **class** from a **design token**, nor code from a
comment. A doc comment quoting `var(--am-gap-sm)` made it demand a declared class
`am-gap-sm`. Harmless here — the comment was reworded — but the next session that documents
a token in a `.tsx` comment will meet it, and the message will name a class that does not
exist rather than the sentence that does.

---

## 8. Risks and known limitations

1. **The dependency map is a mirror, not a fetch.** `stage-registry.json` is a build-time
   contract with no wire representation, so `STAGE_DEPENDS_ON` restates it in `web/src`.
   The guard holds the two together in both directions and runs in the gate, so drift is a
   red rather than a silence — but it is a red at gate time, not a compile error.
2. **The ordinal is scoped to PC-01's schedule by construction.** If a later wave wants the
   nine numbered, the honest instrument is a topological rendering, not a wider ordinal, and
   the guard will say so before the column can lie.
3. **The census reads a module's classes through the bundler's mapping**, which is a
   property of the vitest/Vite CSS-modules transform. If that transform's scoping is ever
   disabled, `scopedCss` becomes an identity function and the new anti-vacuity case reddens,
   which is the intended direction of failure.
4. **`STAGE_STATUS_LABELS` is still private** in `shared/ui/stage-status-badge.tsx` (§2).
   Not touched, because exporting a constant with no second consumer is its own defect.
5. **`D-62`'s own text is wrong in two places** (§7.1, §7.2) and `DEBT_REGISTER.md` is a
   forbidden hotspot for this task, so it is unedited. The register row should be corrected
   when it is closed.
6. **No browser was driven.** `R-18`'s question is what an expert sees, and everything above
   is a server render plus a resolved cascade. The `make gate` frontend half does not open a
   browser and neither did this task.

---

## 9. For the integrator

1. **Merge `agent/w35-stage` (2 commits) onto whatever base wave 34 leaves.** Nothing here
   touches `contracts/**`, `src/**`, `web/src/_pages/**`, `web/src/features/**`,
   `web/src/_app/**` or `tests/e2e/**`, so a conflict with the JWT stream is unlikely; if
   one appears it will be in `web/src/shared/ui/index.ts` (one added export line).
2. **`DEBT_REGISTER.md` needs one edit this task could not make:** close `D-62`, and correct
   its "nine rows" and its "renders in the browser's defaults" — §7.1 and §7.2 give the
   measurement and the commands. Per this register's own rule, the row closes in the same
   commit as the fix; that commit is the merge.
3. **§5 is a finding about an instrument, not about this table**, and it is worth its own
   register row if `D-62`'s closure would bury it: *the contrast census read authored CSS
   module class names and the markup carries scoped ones, so no module rule was ever
   measured through the cascade.* Repaired here; the check is
   `vitest run tests/unit/styles/contrast.test.ts -t 'through the CASCADE'`.
4. **Tell the other live lanes that `56140` is taken** (§6). The brief assigned it to this
   task and `gate-w34dom-postgres` holds it. §4.5 exists because this class of collision is
   invisible until someone's gate dies in `make up`.
5. **Nothing was tagged, pushed, merged or rebased**, and `main`/`dev` were not touched.
   This lane's containers are `gate-w35a-*` on ports 56148 / 59740 / 59741 and are still up;
   `make down` in `/root/w35stage` removes them.
