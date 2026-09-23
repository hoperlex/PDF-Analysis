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

## 3. B1, the other half — the contrast census

### 3.1 First, the premise the brief told me to check: is `D-64` still real?

**No. It was repaired in wave 35, the repair holds, and the register is not stale.**

`D-64` is that the census matched **authored** class names while the rendered markup carries
the bundler's, so no rule in any `*.module.css` ever matched. `DEBT_REGISTER.md` records it
as *"Opened and closed the same day"*, and the tree agrees: `contrast.test.ts` reads the
modules through `import.meta.glob` and rewrites each class name through that module's own
export.

I did not take the register's word for it. Measured in `/root/w41blind-mut`, a `git archive`
of `3544fa3`, **baselined green first** (41 passed):

```
web/src/widgets/run-progress/ui/run-progress.module.css
+ .mode { color: var(--am-line); }          <- ink only; the tint comes from an ancestor
```

A colour-only rule is the exact `D-64` shape: `declaredPairs` cannot see it, so only the
cascade can, and only if the module's names resolve.

```
× every pair that meets on a screen clears the threshold its role asks of it
+   "pair": "text|--am-line|--am-surface|-|-", "ratio": 1.26, "theme": "light",
+   "where": "RunProgress published div > p._mode_5f66a5 > span"
+   "pair": "text|--am-line|--am-surface|-|-", "ratio": 1.44, "theme": "dark"
Tests  1 failed | 40 passed (41)
```

**`p._mode_5f66a5` is the proof**: the site is named with the *bundler's* class, which is
what the wave-35 repair produces. Then the counter-measurement — the same mutation against
the pre-wave-35 instrument, `scopedCss` returning the authored text:

```
✓ … holds in BOTH palettes, and names the theme and the ratio of anything that does not
Tests  1 passed | 15 skipped (16)
```

**Green.** The blindness was real, the repair is load-bearing, and `D-69`'s wave-35 row is
history rather than an open item.

### 3.2 The blindness that IS live, and it is one layer out

`D-64` was *"the names the census reads do not match the markup"*. What is live at `295ff04`
is *"the screens that carry those names are never rendered"*.

**Measured before writing anything**: of the **137** colour-bearing rules in this
application's stylesheets, **31 were reached by no screen the census renders** — 23% of the
surface a file called a census is named after.

The cause is the same as B1's, and `contrast.test.ts` stated it in its own words:

```ts
for (const screen of ['AppFrame', 'ProjectsPage', …18 names…]) {
  expect({ screen, present: names.includes(screen) }).toEqual({ screen, present: true });
}
```

**A literal checked against a literal.** `screens.ts` names a component and this case asserts
that `screens.ts` names it. Nothing anywhere asked the tree — so the knowledge base (`R-23`),
the sign-in screen and the change-password screen (`R-26`) were outside the census entirely,
two of them the first thing a reviewer ever sees, and this case was green.

### 3.3 The repair

`3544fa3`. The eighteen-name list is **deleted** and replaced by a question derived from the
stylesheet: **every rule that declares a colour must be reached by some rendered screen**, or
carry a written reason in `UNREACHED_BY_ANY_SCREEN`, held in **both directions** so the list
may only shrink. A widget the census does not render fails that by the rules it takes with
it, and a screen list nobody maintains cannot make it pass.

Screens added, each because the assertion demanded it and named it:

| added | rules it recovered |
|---|---|
| the knowledge base widget and page | the eight `.am-kb__*` rules |
| the three sign-in and four change-password shapes | `.am-note` and the session chrome |
| a screen carrying `UnsupportedState` | `.am-state--warning` — the **third state tone, measured in neither palette** |
| the four lists **with rows in them** | `li.am-state`, every project and run row |
| the review screen **with data in its four caches** | `.am-review__*`, `.am-uid` |
| a genuinely partial run | `.am-badge--degraded`, `[data-run-outcome='partial']` |

**31 unreached → 11.** Census: 25 → **49 screens**, 90 → **143 pairs per palette**, 1573
elements. The floors in `reaches enough of the application to be worth calling a census` were
raised with it, because a floor left at the old figure lets twenty screens be deleted in
silence.

Two fixtures were repaired that **named a state they did not reach** — the same defect as the
guards, inside the census's own seeds:

- `add('RunProgress partial', runScreen('published', …))` — named partial, seeded published;
- `add('DecisionPanel refused', { refusal: 'Пустой комментарий не отправляется.' })` —
  `decision-panel.tsx` compares `refusal === 'empty'`, so this screen rendered no refusal at
  all. The prop is typed `string | null | undefined` and compared against one magic value;
  that is a `web/src` smell, reported and not repaired.

### 3.4 What the widening found: four real WCAG 1.4.11 failures

Reaching those screens produced a red immediately, and it is not an instrument fault.

| pair | light | dark | needs | where |
|---|---|---|---|---|
| `edge\|--am-line\|--am-paper\|-\|border` | 1.36:1 | 1.30:1 | 3:1 | the theme control in the application bar |
| `…\|hover\|border` | 1.36:1 | 1.30:1 | 3:1 | `li.am-state` — every project row and run row |
| `…\|focus-visible\|border` | 1.36:1 | 1.30:1 | 3:1 | the review screen's finding row |
| `…\|active\|border` | 1.36:1 | 1.30:1 | 3:1 | the same row, pointer down |

`--am-line` is the **only** boundary those interactive controls have, and their own fill does
not separate them from the page, which is exactly the case 1.4.11 covers. **A pair on the row
a reviewer clicks first has been unmeasured since wave 32**, because no census had ever
rendered a populated list or a review screen with data in it.

**Registered with their ratios, not repaired.** The register four rows above already carries
the identical decision for `--am-line` on `--am-surface`: the repair is `--am-line-strong`'s
own territory in both palettes, a three-level border scale cannot carry two levels at the
1.4.11 ceiling, and `W32-CONTRAST` §3 and `W33-THEME` each declined it. It is a scale
decision with an owner and this task's grant is the instruments. What changed is that the
pair is now **measured, named and held in both directions** instead of invisible.

### 3.5 The eleven rules that remain unreached, and why

Each carries its reason in `UNREACHED_BY_ANY_SCREEN`; two of them are findings rather than
limits and are **reported, not repaired**, because nothing this task changed requires them:

- **`.am-evidence__none` is unreachable by any input.** `evidence-viewer.tsx` chooses `page`
  out of `pages`, which it derives from the observation's own evidence — so a page carrying
  no quotation cannot be the active page and this branch cannot render. Dead code.
- **`hr` and `.am-app__context` are dead CSS.** No module in `web/src` renders either;
  `grep -rn "<hr" web/src` and the `am-app__context` grep are both empty.

The other nine are honest limits: `::selection` is composed by the browser;
`.am-app__instance` needs a configured deployment label; `.am-theme__option[aria-pressed]`
is decided by the browser's stored preference; `.am-quotation:has(…)` is the `:has()` the
matcher declines and already names; `[open] > summary` needs a click; and the three
`.am-form__*` rules render only after a mutation settles — all three declare ink and tint in
one block, so `declaredPairs` measures them with no markup at all.

