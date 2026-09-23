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

## 4. B1, third part — the widgets' branches

The coverage assertion in §2 answers *"is every contract member seeded"*. It says nothing
about the branches no schema declares — **pending, error, empty, non-empty, and a listing
with a next page** — and four of `D-69`'s seven instances are exactly those.

**The required set is read out of `web/src`**: every literal `title=` or `what=` passed to
one of the five mandatory state components `shared/ui/states.tsx` declares, plus the two
pager controls. The filesystem decides it, so a widget added next wave brings its own
branches with it, and a literal no rendered screen carries makes the guard red naming the
branch **and the module that has it**.

### 4.1 It reddened for seven branches, and every one of them was reachable

Nobody had reached them:

| branch | module | what it is |
|---|---|---|
| `Такого адреса в приложении нет.` | `app/not-found.tsx` | the 404 screen — **in `SCREENS` at all for the first time** |
| `Это не адрес проекта. / документа. / версии.` | the three detail pages | a pasted address that is not an identifier |
| `Нарушение целостности данных` | `evidence-viewer.tsx` | a finding with no evidence |
| `Страницу не удалось показать` | `evidence-viewer.tsx` | the document bytes unavailable |
| `Загрузка: the decision history…` | `decision-history.tsx` | the history still in flight |

Four of those seven are `UnsupportedState` — **the tone that says no retry will help, which
was rendered by no screen in this guard and by none in the contrast census either.**

### 4.2 Two real `R-18` defects fell out of rendering them, and both are repaired

Both are repaired here because the **repaired guard is what caught them**, which is the one
condition the grant puts on touching `web/src`:

- **`web/src/app/not-found.tsx` carried a whole English sentence** to a reviewer who had
  mistyped an address: *"A project, a document, a version and a run are each addressed by an
  opaque identifier…"* — 33 words, on a screen no instrument had ever rendered, **three
  waves after `D-53` was closed**;
- **`decision-history.tsx` rendered `Загрузка: the decision history…`** — a fourth English
  `LoadingState` argument.

### 4.3 One masking repair, and it narrows rather than widens

The evidence viewer names the programme phase to the reviewer — *"Шлюз свидетельств **P02**
делает такое невозможным"* — and `MACHINE_SHAPES` knew only `PC-\d{2}`. So the guard
reported the residue **`P`**: a letter no reviewer can see, in a report meant to name what
they can, which is `D-61`'s own complaint about `accepted` → `ed`. The pattern now covers
`PC-01` and `P02` and nothing else; a bare `P` and a bare `PC` are still offences.

### 4.4 Five branches one static pass cannot select, and three of them are English

Each carries its reason in `UNREACHABLE_IN_ONE_PASS`, and the list is held in both
directions. **Three are English on a screen a reviewer reaches in a browser:**

| string | module |
|---|---|
| `Загрузка: the new project…` | `create-project-form.tsx`, while the mutation is in flight |
| `Загрузка: the upload…` | `upload-document-form.tsx` |
| `Загрузка: the run request…` | `start-run-control.tsx` |

**Reported, not repaired, and the reason is a rule rather than a shortage of time.** No
instrument in this tree can render those branches — they are selected by a `useMutation`
that has settled, and `contrast.ts` records the same boundary for `.am-form__created` — so
**no instrument could verify the repair**. A three-word change that no guard can check is
precisely what this programme keeps paying for. They are named here for the wave that owns
`web/src` and can add a test that reaches them.

The other two are `Файл выходит за допустимые ограничения.` (the upload pre-check panel,
selected by a `useState` the harness cannot write) and `В начало` (the pager's first-page
control, which needs a widget's own cursor state — `W38-KB` stated this limit and it is
unchanged: the **next**-page control is reached, the return to the first page is not).

## 5. B2 — `D-61`'s third instance

### 5.1 What was there

`tests/e2e/test_pc01_journey_conformance.py` asserted every `expects_rendered` sentence by
**substring containment against a concatenation of every `.ts`/`.tsx` byte under
`web/src`**. The manifest declared the sentence `"Run"` and passed, because `Run` occurs
inside `RunPage`, and no screen renders it.

### 5.2 A premise in the brief that is false, and it changed the repair

> *"`W32-SEE` already built a renderer for exactly this. Reuse it… When the repaired
> assertion reddens, the manifest is what is wrong, not the screen."*

**The renderer cannot decide these sentences positively, for 11 of the 15.** Measured at
`abe1c15` over `renderedScreens()`: eleven live in the upload pre-check panel, the
created-project panel and the version panel — branches driven by `useState` and by a
settled `useMutation`, which one static pass cannot select. `contrast.ts` says the same
thing in its own words about `.am-form__created`, `.am-form__problem` and `.am-form__chosen`,
and §4.4 above measures the same boundary from the other side. A check that claimed to
confirm them would be the same false affordance one layer along.

### 5.3 What the renderer CAN decide, and it is the half that was actually wrong

**The other 4 of 15 passed by matching text the screen renders whatever happened:**

| step | declared | what it actually matched |
|---|---|---|
| `create-project` | `Создан` | `Создан 2026-09-10 08:00:00 UTC · документов 2` — every project row's created date |
| `upload-document` | `Эта версия` | `Эта версия и её манифест неизменяемы.` — the version panel's standing prose |
| `start-run` | `Прогон` | `Прогон использует тот режим провайдера…` — the start-run control's own note |
| `oversize.pdf` | `25 MiB` | `Не более 25 MiB.` — the upload envelope, printed before any file is chosen |

**Every one of those passes in the live browser too.** `write.mjs` and `refusals.mjs` test
`bodyText.includes(needle)` against the page the journey is already on, and all four strings
are on that page regardless. So the deception was never confined to the gate: **four of the
journey's own assertions could not fail.**

**So: none of the manifest's fifteen sentences was verified by anything.** Eleven asserted
something no instrument in the gate could see, and four asserted something that was true
before the step ran.

### 5.4 The repair — two checks, and neither is the old one

**Rendered**, in `web/tests/guards/rendered-language.guard.test.ts`, over `W32-SEE`'s
renderer — reused, not rebuilt, because two renderers is two truths:

> a sentence offered as evidence that a step happened **must not be on the screen before it
> happens.**

The corpus performs no write at all, so it *is* the application before any of these steps
has run. The rule is derived from the manifest, and `STILL_EVIDENCE_THOUGH_RENDERED` is
empty with the one shape that would justify an entry written down.

**Source**, in the Python file, with its subject corrected rather than its matcher: the
sentence must be authored by the **import closure of the `control_module` the manifest
itself names**, in a **quoted literal or JSX text**, **comments stripped**, on a **word
boundary**. Each of those four is load-bearing and the negative controls say so — with
comments left in, declaring `"Run"` on the create-project step *still passed*, because this
repository writes markdown in doc comments and a backtick run reads as a template literal.
Scoping and literal-filtering remove `Run` inside the identifier `RunPage`; they do not
remove `Run` inside the string literal `'RunStateBadge'`, which `run-state-badge.tsx` really
carries, and that is what the boundary is for.

`test_the_rendered_half_of_d61_has_not_left_the_frontend_guard` keeps the rendered half from
leaving the gate in silence — `OPERATING_CONSTRAINTS.md` §4.65's precedent, and sharper here,
because deleting it would leave the Python file green and looking complete.

### 5.5 The manifest, repaired

The four vacuous sentences are removed, each with the reason in its own step and **the
evidence that step really has** named: `create-project` has `[data-created-project]` matched
against `^(prj_%ID%)$` under a 30-second bound; `upload-document` has the location match on
the published version's own address; `start-run` has the captured run id, `await_terminal`
and `expects_api_after_terminal`; `oversize.pdf` keeps `Ничего не отправлено`, which only
the pre-check refusal panel renders.

### 5.6 Falsification

```
manifest.json: write.steps[2].expects_rendered = ["Прогон завершился как"]
× D-61: every sentence the journey calls evidence is evidence > finds none of them already
  on a screen before the step that is supposed to produce it
+   "start-run: \"Прогон завершился как\" is already on [run]"
Tests  1 failed | 16 passed (17)
```

reverted → `Tests 17 passed (17)`.

And the source half, through `prove_the_guard_can_fail.py` against the **real** manifest:
**23 → 24 mutations, every one RED, none vacuous.** The three that drive this check are
*require a sentence no screen renders*, *reword the write half's own panel*, and the new
*declare a sentence that is only an identifier in the source* — which is `D-61` itself, and
which **came back GREEN** against the first version of the repair. That green is the reason
comments are stripped and the boundary is there.

## 6. B3 — the tally, and how far a structural check actually reaches

The brief asks for the seven-row table extended with **what now reaches each state** and
**which of the seven a structural check would have caught**. The honest answer is **three of
seven**, and the other four need something this wave did not build.

The four checks this wave added, named so the table can refer to them:

| | what it asserts | where |
|---|---|---|
| **C1** | every member of every `TRANSLATED_SCHEMAS` schema is rendered, read from the contract | `rendered-language.guard.test.ts` |
| **C2** | every mandatory-state branch and pager control literal in `web/src` is rendered | `rendered-language.guard.test.ts` |
| **C3** | every colour-bearing rule in the stylesheets is reached by a rendered screen | `contrast.test.ts` |
| **C4** | no `expects_rendered` sentence is on the screen before its step runs | `rendered-language.guard.test.ts` |

### The seven

| wave | guard | why it was blind | what reaches it now | structural? |
|---|---|---|---|---|
| 35 | contrast census | matched **authored** class names; the markup carries the bundler's | **C3.** Measured, not argued: with `scopedCss` returning the authored text — the pre-wave-35 instrument — C3 goes red naming `.activity`, `.aside`, `.ordinal`, `.outcome[data-run-outcome='…']` and every other module rule | **YES** |
| 35 | `rendered-language` | rendered four of eight run states | **C1.** Demonstrated on the same mechanism in §2.3 Case C: the pre-repair seed leaves the language half green over an English label and C1 red, naming the members | **YES** |
| 37 | `rendered-language` | the empty branch is also Russian, so the `D-57` mutation stayed green | the branch *was* rendered; the mutation could not distinguish it | **NO** |
| 37 | seam sweep | two of six mutations reddened nothing | nothing here reaches `src/auditmanager` | **NO** |
| 38 | `rendered-language` | every seeded page had `next_cursor: null`, so pagination never rendered | **C2.** The pager scan puts `Дальше` in the required set; with every page `next_cursor: null` it is rendered nowhere and C2 names it and its module | **YES** |
| 39 | three guards (`W39-REVOKE`) | two mutations never reached the code — a subprocess `PYTHONPATH` resolved to the pristine checkout; one assertion read a fixture flag that was already `False` | neither is a coverage gap | **NO** |
| 40 | `W40-LIMIT`'s `L5` | the test aged the row by an hour, so the served-block branch was never reached and the assertion passed for the wrong reason | the shape is a coverage gap, but in Python, and nothing here measures it | **NO** |

**Three of seven.** And `D-61`'s third instance — the manifest asserting a sentence no screen
renders — is a fourth case of the same family that C4 now reaches, but it is not in the
seven-row table, so it is not counted here.

### What the other four need, stated so the next wave can cost it

The four split cleanly into two kinds, and neither is *"more coverage"*.

**1. Two are mutation-adequacy, not coverage** — wave 37's empty branch and wave 39's `G7`.
The state *was* reached; the mutation could not tell the difference, or the assertion was
built out of the thing under test. **Nothing structural can tell you the mutation you chose
was too weak.** What would help is not a guard: it is the rule `W32-SEE` already wrote down
— *when a mutation reddens nothing, the first hypothesis is missing coverage, not a weak
assertion* — plus a mutation harness that reports **which branch the mutation sits in**, so
"the branch was never executed" and "the branch was executed and nothing noticed" stop
looking identical.

**2. Two need branch coverage over `src/auditmanager`, which this programme does not have**
— wave 37's seam sweep and wave 40's `L5`. `L5` is the sharpest statement of it in the whole
register: *a test that reaches the right outcome through the wrong branch*, indefinitely and
with no symptom. C1–C4 are all frontend, and all four answer *"did the rendered output ever
contain this"*. The backend analogue is a per-branch coverage instrument, or — cheaper and
in the same spirit as C1 — **an assertion that the mutated line was executed at all**, which
would also have caught wave 39's `G10`/`G11` from the other side.

**3. And one is instrument plumbing** — wave 39's `G10`/`G11`, where the mutation never
reached the code. `OPERATING_CONSTRAINTS.md` §2 and §10 already carry the rule; what is
missing is that it must hold for **every process the test spawns**, not only for pytest's
own import. That is a line in the mutation target, not a guard.

### The claim this wave can make, and the one it cannot

**Can:** for the first time on this programme, a blindness of the `D-69` kind was found by a
**structural check** rather than by a mutation dying quietly — five times over, in one wave:
thirteen unseeded contract members, seven unrendered widget branches, thirty-one unreached
colour rules, four vacuous journey sentences, and `D-64`'s repair re-verified by mutation
rather than by reading the register.

**Cannot:** *"a guard can no longer be sound and blind."* Four of the seven are outside what
was built, three of them because they are backend, and one of them because no structure can
audit a mutation's strength. A row that claimed otherwise is how `D-4` and `D-2` closed early.

## 7. The gate

Taken at **`c32a4e5`**, in lane `gate-w41b` (PostgreSQL `127.0.0.1:56230`, S3 `59830`/`59831`),
`make gate > /root/w41b-gate.log 2>&1`. **Read from the `GATE OK` line in the log**, never
from a status a harness handed back — `OPERATING_CONSTRAINTS.md` §4.6 and §4.62.

```
grep -c 'GATE OK' /root/w41b-gate.log   ->  1
```

| component | figure |
|---|---|
| foundation | **35 passed** in 31.20s |
| battery | **2319 passed, 5 skipped, 1 warning, 169 subtests passed** in 502.70s |
| frontend | **72 files, 1022 tests passed**, after `tsc --noEmit` clean |
| whitespace | pass |
| | `GATE OK: battery, foundation, frontend and whitespace all pass` |

### The deltas, each measured rather than recalled

**The first version of this section gave two figures from memory and both were wrong** — it
said 1010 frontend tests at the base and 51 conformance tests, against 1014 and 50. They are
re-measured here at `295ff04` in `/root/w41blind-mut`, and the method is the point: a count
quoted without the command that produced it is not a measurement (`OPERATING_CONSTRAINTS.md`
§7, §12).

```
git archive 295ff04 contracts docs web/src web/tests tests | tar -x -C /root/w41blind-mut
cd /root/w41blind-mut/web && npm exec -- vitest run
cd /root/w41blind-mut && /root/w41blind/.venv/bin/python -m pytest tests/e2e/test_pc01_journey_conformance.py -q
```

| suite | `295ff04` | `f4add83` | delta |
|---|---|---|---|
| frontend, whole | 72 files, **1014** | 72 files, **1022** | **+8**, no new file |
| `rendered-language.guard.test.ts` | 12 | **19** | **+7** — 3 contract coverage, 2 branch coverage, 2 journey evidence |
| `contrast.test.ts` | 15 | **16** | **+1** — the rule-coverage assertion, which also replaced the eighteen-name literal |
| `test_pc01_journey_conformance.py` | **50** | **54** | **+4** — the rendered-half marker check and three negative controls |

## 8. What this wave did not do

- **Three English `LoadingState` arguments remain on screens a reviewer reaches** —
  §4.4. Reported, not repaired, because no instrument in this tree can render those
  branches and so none could verify the repair.
- **`.am-evidence__none` is dead code** and **`hr` / `.am-app__context` are dead CSS** —
  §3.5. Reported, not repaired; nothing this task changed requires them.
- **`decision-panel.tsx` takes `refusal?: string` and compares it against the literal
  `'empty'`.** A sentence passed there renders nothing, silently, which is how the contrast
  census had a screen called `DecisionPanel refused` that showed no refusal. The fixture is
  repaired; the prop's type is not.
- **Four WCAG 1.4.11 failures are registered rather than repaired** — §3.4. The repair is a
  border-scale decision with an owner.
- **Eleven of the journey's fifteen `expects_rendered` sentences are still verified by no
  instrument in the gate** — §5.2. Only `refusals.mjs` against a running stack reaches them.
