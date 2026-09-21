# `W31-STYLE` — the styling layer `R-18` asks for

Worktree `/root/w31style`, branch `agent/w31-style`, based on `ae2adf5`.
Four commits: `df80763`, `c37b9b9`, `aeded7d`, `7791f4b`.

`R-18` (`OWNER_RULINGS_2026-09-17.md` §3.9, amending `ALPHA_ROADMAP.md` §1) rules that the
alpha is shown in a finished interface, because `P4` measures whether the **findings** are
professionally useful and an expert handed a skeleton reports on interface friction
instead. Its rule is **breadth of finish beats depth of function**, and that is what
decided every trade-off below: the element layer — `h2`, `dl`, `table`, the form controls —
got the largest share of the work, because most of PC-01's markup names no class at all and
styling an element finishes every screen that ever uses it.

**How everything here was seen.** This is a visual change and the suite cannot see it, so
the evidence is rendered. `/root/w31-logs/style-shots/` holds `before-*.png` and
`after-*.png` for all six screens at 1440px, full page, plus `legacy-default.png`. They
were taken with a harness kept **outside** the tree
(`/root/w31-logs/style-shots/harness/`, `shoot.mjs`), which renders each real screen
component through the repository's own `tests/unit/screens/harness.ts` — a `QueryClient`
seeded under the frozen `queryKeys`, `renderToStaticMarkup`, the real `globals.css` inlined
— and photographs it in a cold headless Chromium over CDP. **Say which stack a reading came
from:** these came from that static render, **not** from a deployed instance, and never from
`127.0.0.1:31500`. The one thing the harness stubs is `useEvidenceDocument`, because it
mints its `blob:` URL inside an effect and a server render runs none; it is given a
`file://` URL to `fixtures/synthetic/ar/ar_baseline.pdf` instead, so the review screen's PDF
island is a real PDF in a real browser.

---

## 1. What the token set gained, token by token

`W31-UI` left **14** custom properties. There are now **57**, and the set is **extended, not
replaced**: every name it defined is still defined and still carries a value of the same
kind. `grep -oE '\.am-[a-z0-9_-]*' globals.css | sort -u` before and after shows **no class
lost** — 83 declared before, 99 after.

| Added | Measured gap it closes |
|---|---|
| `--am-ink-soft` | Two ink levels existed. A quotation anchor, a timestamp, an author label and an identifier chip all want a level quieter than `--am-ink-muted`, and each was reaching for `muted` and arriving at the same weight as the body copy beside it. |
| `--am-ink-inverse` | Text on a filled surface was `var(--am-paper)`, i.e. "the same colour as paper" — true today and not a statement about contrast. Under a second palette it is the token that has to move. |
| `--am-surface-sunken` | One surface below paper existed. A code chip, a count pill, an inset PDF well and a provider tag all need a level below `--am-surface`, and without one they were outlined instead. |
| `--am-line-soft`, `--am-line-strong`, `--am-grid-line` | **One** `--am-line` was doing the work of a hairline inside a card, a divider between cards, the edge of a control and a table rule. Nothing on a screen had a near and a far, which is most of why everything read as one flat plane. |
| `--am-accent-strong` | There was no hover/active value: the primary button hovered with `filter: brightness(1.1)`, which lightens rather than deepens and is not a token anything else can read. |
| `--am-accent-light`, `--am-ok-light`, `--am-degraded-light`, `--am-failed-light`, `--am-inert-light` | The five semantic hues were outline-on-`currentColor`, so a status plaque was a thin ring around 12px type. A filled badge needs a tint per hue and there was none. All five state blocks and all five badges now read at a glance across a list. |
| `--am-shadow-0/1/2/3`, `--am-shadow-inset` | One shadow value existed. Everything that lifted, lifted by the same amount, so a card, a hovered row, a sticky bar and an inset well were indistinguishable in depth. |
| `--am-ring` | The focus affordance was `outline` alone. A ring is what lets a focused input keep its border colour and still say it is focused. |
| `--am-motion-fast/base/slow`, `--am-ease` | **Zero** transitions existed. Every state change was instantaneous, which is the single cheapest thing that makes an interface read as unfinished. Every transition below reads its duration from a token, and `@media (prefers-reduced-motion: reduce)` collapses all three to `1ms` — a motion scale that cannot be turned off is an accessibility defect. |
| `--am-radius-sm/lg/pill`, `--am-radius` 6px → 10px | One radius served a card, a control and a 999px pill alike. |
| `--am-text-xs/sm/md/base/lg/xl/2xl`, `--am-leading-*`, `--am-tracking-caps` | One font size and the browser's own heading ladder. An `<h2>` inside a card rendered **larger** than the page title above it — visible in `before-5-run.png` and `before-1-projects.png`. |
| `--am-gap-xs/sm/lg/xl` | One spacing value, so every gap was 16px or a literal. |

**The typeface line is NOT closed, and is not silently half-done.** The scale, the weights
and the tracking are here; the face is still the system stack. A self-hosted Onest or
JetBrains Mono needs a font **file**, and no path that could hold one is in this task's
`allowed_paths` — `web/src/app/**` is not mine except `globals.css`, and a webfont package
would be the first UI dependency in thirteen, which the brief forbids. Naming the face in
the stack ahead of the fallback would have been worse: it would read as closed and resolve
to nothing on a host that does not have it. §5 names whose it is.

---

## 2. The six screens, before and after

Before is `before-N-*.png`; after is `after-N-*.png`. `.local/handoff/` also holds the
2026-09-21 stand capture at `ca16a18` — eight PDF pages and **six** PNGs — which is the state
before `W31-UI` as well as before this wave.

| # | Route and page module | What changed | `R-18` defect |
|---|---|---|---|
| 1 | `/projects` — `web/src/_pages/projects/ui/projects-page.tsx` | Rows stopped being dashed placeholder panels (see below); `prj_…` became a quiet chip instead of a line of body text under the name; the create form got a real field, a real row and a real button rank; `Все проекты` stopped out-sizing the page title. | **identifiers in body text — closed** |
| 2 | `/projects/{project_uid}` — `_pages/project-detail/` | The `<code>{projectUid}</code>` subtitle became a chip; the upload envelope panel reads as a note rather than as an error; `input[type=file]` became a bordered drop target and the title field a real control — the whole of the form styling before this was three inline `padding` declarations. | **identifiers — closed** |
| 3 | `…/documents/{document_uid}` — `_pages/document-detail/` | Version row as a card; the transport caveat set as `am-note` rather than as loose italic body text. | **identifiers — closed** |
| 4 | `…/versions/{version_uid}` — `_pages/version-detail/` | The immutable manifest reads as a labelled panel; the two run rows carry filled state badges; `Start run` is the one primary control on the screen and the pager is quiet. | **identifiers — closed** |
| 5 | `…/runs/{run_id}` — `_pages/run/` + `widgets/run-progress/` | The largest change on any screen, and all but three lines of it came from the element layer: `<dl>` became a key/value grid with rules instead of an indented ladder, the stage `<table>` got a header rank and row separation, the heading ladder inverted back. The run's **outcome** — the reading the user came for — is now a tinted result block keyed off `data-run-outcome`, not the seventh of twelve identical paragraphs. | — |
| 6 | `…/runs/{run_id}/review` — `_pages/review/` | `prj_…` and `run_…` are `am-uid` chips on their own row and the diagnostic sentence is a block beneath them, not a clause running into them. The **open page tab is now marked** (see §5). The quotation — the load-bearing half of this screen — is a card with a rule, not a line of text. The decision panel is a panel. The history is a timeline with per-verdict markers. The export panel spans the grid instead of being squeezed under the finding list, and the seventeen CSV columns are behind the sentence that describes them. | **identifiers — closed; CSV column list — closed; unreadable page — closed** |

Three things worth naming because they are not visible from a diff:

- **Every list row in this application is an `<li class="am-state">`**, written in
  `src/entities/**` — another session's tree this wave. So a project row arrived carrying
  the *dashed placeholder* look of an empty state, and a project list read as three "nothing
  here" panels stacked (`before-1-projects.png`). The repair needed no edit to that tree: a
  state is a `<div>`, a row is an `<li>`, and `li.am-state` is the whole of it.
- **The PDF island is bounded at both ends** — `clamp(460px, 62vh, 820px)`. `W31-UI` set
  `62vh`, which on a tall window returns a 1500px-high island with one paragraph beside it;
  that is visible in the intermediate shots and is why the bound is there.
- **The CSV columns are still all seventeen**, still from `CSV_COLUMNS`, still carrying
  `data-csv-column`, and the `<summary>` is the sentence the panel already had. **No string
  was invented and none was translated.**

---

## 3. `R-18` defects NOT closed, and whose they are

| Defect | Status | Whose |
|---|---|---|
| The footer *"Local prototype. One reviewer, no authentication, no tenancy."* on every page | **Not closed.** It is English copy in `web/src/_app/app-frame.tsx`, which is **outside this task's `allowed_paths`** — the brief lists `widgets`, `_pages`, `features`, `shared/ui` and `_app` is none of them. I styled `.am-app__footer` from `globals.css`; I could not touch the sentence or remove it. | The shell owner, plus `W31-RUS` for the language. Needs a task that owns `web/src/_app/**`. |
| Mixed language elsewhere | **Not closed, and not mine.** The brief says `W31-UI` "made the interface Russian, including the failure-presentation layer" and tells me not to revisit it. **That is not what is in the tree** — see §5.1. | `W31-RUS`. |
| The typeface (Onest / JetBrains Mono) | **Not closed.** Needs a font file; no `allowed_path` can hold one; no dependency may be added. | A task owning a font path, under the `R-18` line. |
| Icons — 43 inline `<svg>` in the reference, **0** in `web/src` | **Not built, deliberately.** `.local/handoff/ICONS-PROVENANCE.md` records that this is already `D-52` in the debt register with an open provenance question (part of the 24×24 set is Feather, one match byte-identical). Building an icon set here would have pre-empted that row. Priced in §6. | `D-52`. |
| A dark default | **Not built, deliberately.** Owner question. Priced in §6. | The owner. |

---

## 4. The gate delta, case by case

**Frontend: 772 in 53 files → 779 in 54.** Seven cases in one new file,
`web/tests/unit/styles/styling-layer.test.ts`. The suite renders markup; a stylesheet is not
markup, so every defect this wave repaired was structurally invisible to it. Each check is a
pure function over text, exercised against a deliberately broken fixture **and** against the
real files.

| # | Case | What it asserts |
|---|---|---|
| 1 | *can fail: the shape `R-18` measured 55 of* | `undeclared()` returns `am-finding-row` for markup that names it over a stylesheet that does not declare it; returns the prefix report for a computed modifier with no declared modifier; returns nothing once one exists. The fixtures are the **actual historical strings**. |
| 2 | *holds over every `.tsx` in `web/src`* | Every `am-…` class named anywhere in the 42 `.tsx` modules is declared in `globals.css` or in a collocated module. A name ending `--` is a computed modifier (`` `am-badge--${tone}` ``) and is satisfied by any declared modifier carrying that prefix — the most the source can honestly claim without evaluating the component. |
| 3 | *can fail: the exact disagreement `W31-UI` left* | Over the two real strings, the emitted value is `page`, the selected value is `true`, and the agreement check is `false`. |
| 4 | *holds between `evidence-viewer.tsx` and `globals.css`* | Every `aria-current` value the widget can emit is a value the stylesheet's `.am-evidence__pages` rules select. |
| 5 | *can fail: a colour spelled inside a rule* | A hex inside a rule and an `rgba()` inside a `box-shadow` are both reported; a hex inside `:root` is not. |
| 6 | *holds over `globals.css` and every collocated module* | **Zero** colour literals outside `:root`, in every stylesheet in the tree. This is what makes a second theme a block of values rather than a rewrite (§6). |
| 7 | *a collocated module defines no token of its own* | A module **consumes** the global tokens and declares none. A module that redefined one is the defect this architecture exists to prevent. |

**Anti-vacuity against the real tree, not only against fixtures.** Four mutations, four
reds, each naming the right thing — run on a committed tree and reverted with `git checkout`:

| Mutation | Result |
|---|---|
| rename every `.am-finding-row` declaration in `globals.css` (5 occurrences) | red: `expected [ 'am-finding-row' ] to deeply equal []` |
| restore `W31-UI`'s `[aria-current='true']`-only selector | red: `expected [ 'true' ] to include 'page'` |
| write `color: #16191d` into `.am-badge__label` | red: literal `#16191d` reported |
| declare `--am-gap-sm` inside `run-progress.module.css` | red: module declares a token |

**And one mutation that did NOT redden, reported because it is the more useful result.** The
first attempt renamed only the *first* `.am-finding-row` declaration. The class is declared
in five places, so it stayed declared and the guard was correctly silent. **The mutation was
insufficient, not the guard weak** — which is exactly the `§12` shape, and it is the reason
the four above are stated with their replacement counts.

### What could not be run, and why

**`make gate` did not complete in this lane, and the reason is environmental, not the
tree.** `make up` fails before any service starts:

```
Network gate-w31b-net Error ... all predefined address pools have been fully subnetted
make: *** [Makefile:868: up] Error 1        EXIT=2      (/root/w31-logs/style-gate.log)
```

Docker's default address pools are exhausted. Measured: **33** networks exist; **24** of them
have zero containers attached and belong to dead sessions from waves 3–24
(`gate-w3-net`, `gate-w13a-e`, `gate-w14a`, `gate-w16a/b`, `gate-w17a`, `gate-w18a`,
`gate-w19a/b`, `gate-w20a/b`, `gate-w21a`, `gate-w22b`, `gate-w23b`, `gate-w24a`,
`auditmanager-gate-w21b`, `auditmanager-gate-w22c`, `auditmanager-w14a`,
`auditmanager-w15b`, `auditmanager-w30cert3`). Four lanes are live and were not touched:
`gate-b0`, `gate-w30a`, `gate-w30b`, `gate-w31c`, plus the `auditmanager-w19a` stack.

**Removing the 24 stale networks is the remedy and this session was denied permission to
do it** (`docker network rm` and even `docker network inspect` on another lane's network
are refused as workload interference). It is one command for whoever has the permission,
and it only removes networks no container is attached to:

```
for n in $(docker network ls --format '{{.Name}}' | grep -E '^(gate-|auditmanager-)'); do
  [ "$(docker network inspect "$n" --format '{{len .Containers}}')" = 0 ] && docker network rm "$n"
done
```

**What was run instead, with exit codes read from `$?` after a redirect and never through a
pipe:**

| Check | Result |
|---|---|
| `npm --prefix web test` — the gate's whole `run_frontend` step | **779 passed in 54 files**, exit 0 |
| `git diff --check` and `git diff --check ae2adf5..HEAD` — the gate's `check_whitespace` step | exit 0, exit 0 |
| `tests/e2e/test_pc01_journey_conformance.py` — **the trap the brief names** | **47 passed** in 0.44s, exit 0 |
| the canonical battery, minus every suite that needs PostgreSQL or S3 | **402 passed, 49 subtests**, exit 0 |
| `npm run typecheck` (`tsc --noEmit`) | exit 0 |
| `npm run lint` (`eslint .`) | exit 0 |
| `npm run build` (`next build`) | exit 0, six routes — this is what proves the collocated module compiles |

The battery run that **did** include the service-backed suites is recorded for honesty:
1187 passed, 48 failed, 778 errors — every failure a connection refusal from the absent
services, grouped by directory in the log. **None of it can be affected by this branch:**
`git diff --name-only ae2adf5..HEAD` touches `web/src/**` and `web/tests/unit/**` and
nothing else, so the Python tree at `HEAD` is byte-identical to the gated tip.

**Note for the integrator:** neither `tsc --noEmit` nor `eslint` is in `make gate` —
`run_frontend` is `npm --prefix web test` alone. Both are clean here, and that they are not
gated is worth a debt row somebody else owns.

---

## 5. Premises of the brief I measured and found false

### 5.1 "`W31-UI` made the interface Russian … do not revisit the translation"

**False as a statement about the tree**, though right as a statement about ownership.
Measured at `ae2adf5`, at least **20 distinct user-visible English strings survive across 17
modules**. A sample, by path:

- `shared/ui/states.tsx:42`, `features/start-run/ui/start-run-control.tsx:63`,
  `features/upload-document/ui/upload-document-form.tsx:144` — *"Correlation id"*, on the
  face of the failure layer the brief says is done;
- `widgets/{project,document,version,run}-list` ×4 — *"First page"*, *"Next page"*;
- `widgets/run-progress/ui/run-progress.tsx` — *"Published findings:"*, *"The run terminated
  `failed`. Nothing was published."*, *"The run terminated `cancelled`…"*, *"provider
  mode:"*, *"— this run's provider mode is …"*;
- `widgets/export-panel` — *"Downloaded …"*; `features/create-project` — *"Created …"*;
  `features/upload-document` — *"Display title"*, *"Chosen:"*;
- `_pages/version-detail/ui/version-detail-page.tsx:82` — *"All versions of this document"*;
- `entities/document-version/ui/version-panel.tsx` — *"Ordinal"*, *"Media type"*, *"Pages"*,
  *"Size"*, *"Published"*, *"Uploaded as"*, *"(58978 bytes)"*;
- `entities/{project,audit-run,document-version}/ui/*-row.tsx` — *"Created …"*,
  *"documents"*, *"Findings … · stages …"*, *"Version 1 · 8 pages · … published …"*;
- `app/not-found.tsx` — the entire `detail` sentence;
- `_app/app-frame.tsx` — the footer `R-18` names.

Query: `grep -rnE '(Created |Downloaded |Chosen: |First page|Next page|Display title|Correlation id|All versions|Published findings|provider mode:)' --include=*.tsx web/src`.
**I changed none of them** — they are `W31-RUS`'s, and three of the files are outside my
paths anyway. They are listed because a brief that says the translation is finished will
otherwise be believed, and `R-18`'s first named defect is mixed language.

### 5.2 "`web/src/app/**` … is nine six-line delegations that never hold behaviour"

**False in all three of count, size and behaviour**, and it matters because it was offered
as a reason the path is unimportant. Measured (`find web/src/app -type f | xargs wc -l`):
**seven** `page.tsx` files of **9 to 36 lines**, plus `layout.tsx` (28 lines — it carries
`<html lang="ru">` and the document metadata), `not-found.tsx` (43 lines, carrying real
user-facing copy), and `bff/v1/[...path]/route.ts` (**109 lines** — the credentialed
transport seam, which is behaviour by any definition). This is not academic: `layout.tsx` is
where a theme attribute and its anti-flash script would have to go (§6), so the path being
"empty" is exactly the assumption that would mis-price that work.

### 5.3 The legacy prefix counts

The brief states *"76 `stage*`, 47 `queue*`, 25 `modal*`, 13 `batch*`, 5 `compar*` is
already 166 classes"* for screens we do not have. **Neither query I can construct
reproduces those numbers**, and the brief does not say which one produced them — which is
`§12`'s own rule applied to `§12`'s own kind of claim.

| Query | `stage*` | `queue*` | `modal*` | `batch*` | `compar*` | total |
|---|---|---|---|---|---|---|
| distinct class **selectors** in all three legacy stylesheets | 26 | 42 | 13 | 10 | **0** | **91** |
| distinct **identifiers** in `index.html` + `static/js/*.js` (includes variable names) | 84 | 62 | 27 | 43 | 8 | **224** |
| the brief | 76 | 47 | 25 | 13 | 5 | 166 |

**The conclusion the brief draws from them still stands** — a large share of legacy's rules
serve screens PC-01 does not have, so the raw ratio overstates the per-screen gap. The
margin is smaller than stated on the CSS-selector query. Related figure, also different: the
brief says legacy has **1538** classes; `grep -oE '\.[a-zA-Z][a-zA-Z0-9_-]*' static/css/*.css | sort -u | wc -l`
gives **1880** across the three stylesheets and **1656** in `styles.css` alone.

### 5.4 The light/dark premise — the integrator's own correction, verified

The correction that arrived mid-task is **confirmed, by rendering and not only by reading**,
with one detail of it wrong:

- `static/js/app.js:10` reads `localStorage.getItem('audit-theme') || 'dark'`. The
  correction gives the key as `theme`; it is **`audit-theme`**. The claim it supports —
  **dark is the default** — is right.
- Rendered in a cold browser with no stored preference, over a plain static file server and
  empty JSON on `/api`: `data-theme="dark"`, `body` background `rgb(13, 18, 25)`.
  `legacy-default.png`. The server was mine, on port **38317**, over a **copy** of the legacy
  tree, and was stopped by pid afterwards; no legacy backend was started.
- `styles.css` carries **11** `[data-theme]` blocks. Line 45 is a full second token set —
  **30** declarations against `:root`'s **32**. The other ten are component-level dark tweaks.
- `--teal` is `#008f7e` under `:root` and `#00c2b8` under dark, so the teal in the original
  brief was the light value, as the correction says.
- `frontend/index.html` carries **43** inline `<svg>`; `web/src` has **0**.

### 5.5 The instrument the brief pointed me at cannot take a screenshot

The brief names `tests/e2e/pc01/journey/` as what to read before building anything, and it
was the right thing to read — `look.mjs` is a deliberate assertion-free window and `cdp.mjs`
is the CDP client. But `cdp.mjs`'s `Page` exposes `goto`, `evaluate`, `click`, `fill`,
`attachFile`, `waitFor`, `settle`, `location` and the exchange log, and **no screenshot**;
`#send` is private, so there is no way to reach `Page.captureScreenshot` through it. A
deliverable stated as "a screenshot of each of the six screens" therefore needs a tool that
does not exist in the tree. Mine is outside the tree and adds no dependency (Node 22's
`WebSocket`, same as `cdp.mjs`). **If screenshots are going to be asked for again, a
`screenshot()` on that `Page` is about eight lines and belongs to whoever owns
`tests/e2e/**`.**

### 5.6 Smaller ones

- The `.local/handoff/` set is **8 PDF pages and 6 PNGs** for **6** screens; the brief says
  "eight pages … one page per screen".
- `R-18`'s own scope figures still hold at `ae2adf5` and were re-measured, not assumed:
  `find web/src -name '*.module.css' | wc -l` → **0**; `grep -n 'lang=' web/src/app/layout.tsx`
  → `lang="ru"` (so that one is already closed by `W31-UI`).
- The brief's frontend baseline, **772 in 53**, is correct for `ae2adf5`. The integrator
  notes `W31-RUS` has since taken `dev` to **785 in 55**; my `+7 in +1` is against my own
  base and must not be added to that.

---

## 6. What a dark default would cost, and what was done to keep it cheap

Written because the integrator asked for a price rather than a build. **Nothing here builds
a theme, changes a default or adds a toggle.** `globals.css`'s header sentence — *"There is
no theming system and no dark mode … a theme toggle is a decision nobody has taken"* —
**is still true**, and it is now followed by a paragraph saying why every colour is a token
anyway, which is a statement about cost and not about a theme.

### What it costs in this stylesheet: 27 declarations and no rule edit

| Measure | Value | Command |
|---|---|---|
| tokens in `:root` | **57** | `grep -cE '^\s+--am-' globals.css` |
| of those, colour-valued (need a dark override) | **27** | `grep -E '^\s+--am-' globals.css \| grep -cE '#[0-9a-fA-F]{3,8}\|rgba\('` |
| rules in `globals.css` | **199** | `grep -c '{' globals.css` |
| **colour literals outside `:root`** | **0** | `sed '/^:root {/,/^}/d' globals.css \| grep -nE '#[0-9a-fA-F]{3,8}\b\|rgba\(\|hsl\('` → no match, exit 1 |

So `[data-theme="dark"] { … }` is **27 declarations and zero rule edits** — the same shape
legacy's is (30 against 32). This is the property guard 6 in §4 pins, and it was not free
by accident: the sweep found exactly **one** colour written into a rule
(`.am-evidence__page`'s inset shadow) and it became `--am-shadow-inset`. The 27 are:
`--am-ink`, `-muted`, `-soft`, `-inverse`; `--am-paper`, `--am-surface`, `-sunken`;
`--am-line-soft`, `--am-line`, `-strong`, `--am-grid-line`; `--am-accent`, `-strong`,
`-light`; `--am-ok`/`-light`, `--am-degraded`/`-light`, `--am-failed`/`-light`,
`--am-inert`/`-light`; `--am-shadow-1/2/3/-inset`; `--am-ring`.

### What it costs beyond the token block — stated, because "purely additive" is an ideal legacy itself did not reach

Legacy needed **ten** component-level `[data-theme="dark"]` blocks on top of its token block.
Expect a handful here too. **One is certain and is a real design decision, not a tweak:**

> `.am-evidence__object` sits on `var(--am-paper)`. It is the browser's own PDF viewer
> showing a white page of a real document. Under a dark palette that token goes dark and the
> PDF island would be a dark frame around white paper — or worse, a dark well the viewer
> paints white anyway. **The evidence pane has to stay light whatever the theme**, which
> means one rule that does not follow the token. Whoever builds the theme should start there.

Also: the `-light` companions are pale solids here, and in legacy's dark block they are
**alpha tints of the hue** (`rgba(0,194,184,0.12)`). Same token names, different kind of
value — which is fine, and is the reason they are tokens.

### What the toggle and its persistence cost: three files, none of them in this lane

| Needed | Where | Note |
|---|---|---|
| `data-theme` on `<html>` | `web/src/app/layout.tsx` | It is a server component; the attribute cannot be read from `localStorage` during SSR. |
| a blocking inline script before first paint | `web/src/app/layout.tsx` | Without it every load flashes the server's default before the stored preference applies. This is the part people forget and it is the reason this is not a one-line change. |
| the control | `web/src/_app/app-frame.tsx` | The frame is a **server** component today and says so in its header, so the toggle is a new client component beside it, not a hook in it. |
| the persisted value | a new `shared/` or `features/` module | One `localStorage` key. Legacy's is `audit-theme`. |

**All four are outside this task's `allowed_paths`.** The work is small and it is not mine.

### Icons: priced, not built

`frontend/index.html` has **43** inline `<svg>` in two conventions (28 at 24×24 stroke-2, 10
at 16×16 stroke-1.5); `web/src` has **0**. Most of legacy's are sidebar items, and **we have
no sidebar** — the icon surface on PC-01's six screens is roughly the brand mark, the three
header links, the two verdict buttons, the download and the disclosure: **8 to 12 glyphs**.
The cost is not the drawing. It is (a) a convention — inline component vs sprite — and (b)
**provenance**, which is already `D-52` in the debt register: part of legacy's 24×24 set is
Feather, one path byte-identical. Building a set here would have pre-empted that row.

---

## 7. Files changed

```
web/src/_pages/review/ui/review-page.tsx                   |  15 +-
web/src/app/globals.css                                    | 1198 ++++++++++++++---
web/src/features/create-project/ui/create-project-form.tsx |   8 +-
web/src/features/start-run/ui/start-run-control.tsx        |   2 +-
web/src/features/upload-document/ui/upload-document-form.tsx |  7 +-
web/src/widgets/document-list/ui/document-list.tsx         |   8 +-
web/src/widgets/export-panel/ui/export-panel.tsx           |  35 +-
web/src/widgets/project-list/ui/project-list.tsx           |   8 +-
web/src/widgets/run-list/ui/run-list.tsx                   |   8 +-
web/src/widgets/run-progress/ui/run-progress.module.css    |  70 ++
web/src/widgets/run-progress/ui/run-progress.tsx           |  16 +-
web/src/widgets/upload-panel/ui/upload-panel.tsx           |   2 +-
web/src/widgets/version-list/ui/version-list.tsx           |  10 +-
web/tests/unit/styles/styling-layer.test.ts                | (new)
docs/program/W31-STYLE.md                                  | (this file)
```

`git diff --name-only ae2adf5..HEAD | grep -vE '^web/src/(app/globals\.css|widgets/|_pages/|features/|shared/ui/)|^web/tests/unit/|^docs/program/W31-STYLE\.md'`
is **empty**: no `contracts/**`, no `src/**`, no `db/**`, no `infra/**`, no `tests/**`
(Python), no `web/FRONTEND_LOCK.json`, no `web/package.json`, no `web/package-lock.json`, no
root lockfile, no `Makefile`, no `DEBT_REGISTER.md`, no `CURRENT_STATE.md`, no
`ALPHA_ROADMAP.md`, no `OWNER_RULINGS_2026-09-17.md`. `web/src/entities/**` and
`web/src/shared/api/**` — `W31-RUS`'s this wave — are untouched.

**The collocated module.** `run-progress.module.css` is the first in this application and
the thing `globals.css`'s header has promised since the bootstrap; `R-18` measured **zero**
against that promise. That slice was chosen because being first there costs nothing: every
class in it was introduced by this wave, so nothing asserts the names. **That is not true of
the rest**, and the cost is measured rather than assumed — **eight** `am-` class names are
asserted by the frontend suite (`am-decision__refusal`, `am-history__comment`,
`am-history__verdict`, `am-quotation__anchor`, `am-quotation__inconsistent`,
`am-state--error`, `am-state--neutral`, `am-state__title`), and **`.am-state` is read out of
the live DOM** by `tests/e2e/pc01/journey/refusals.mjs` to capture a refusal panel's text and
tone. Under `css: false` vitest answers a module import with a proxy returning the **mangled**
name, so migrating any of those turns the assertion that names it red. Migrating the rest is
a change to two trees this wave does not own; it is a decision, not a chore.

---

## 8. Risks and known limitations

1. **No rendering in a browser against a live stack.** Everything in §2 was seen through a
   static SSR render plus the real stylesheet in a real browser. That is exactly what decides
   layout, but it is **not** the deployed application: no hydration, no client state, no
   handler ever fired. A screen whose *interaction* is wrong would look right in these shots.
   The instrument that closes that gap is `npm --prefix web run e2e:pc01` against a served
   origin, and it needs the stack that `make up` could not start.
2. **`make gate` is unrun in this lane.** §4 says why and what to do. The four halves I could
   run are green, and the Python tree is byte-identical to the gated tip.
3. **`li.am-state` carries one `!important`.** It overrides an inline
   `style={{ marginBottom: '0.5rem' }}` written in `src/entities/**`, which this wave may not
   edit. When that tree is next owned, the inline style should go and the `!important` with
   it.
4. **`:has()` is used once** (`.am-quotation:has(.am-quotation__inconsistent)`), to colour a
   quotation card whose anchor disagrees with its own string. It is supported everywhere the
   pinned Chromium runs; a browser without it loses the tint and nothing else — the alert
   paragraph inside the card is unaffected.
5. **The `-light` tints were chosen by eye against the existing hues**, not computed to a
   contrast ratio. Text on them is the hue's dark value, which is comfortably above 4.5:1 by
   inspection, but no WCAG figure is claimed and none was measured.
6. **`p { max-width: 78ch }` is a global.** It makes prose readable on a 1440px screen and it
   will surprise whoever first writes a wide paragraph that wants to fill a card.

---

## 9. For the integrator

1. **Merge order.** This branch is `web/src/**` plus one new `web/tests/unit/**` file plus
   this document. `W31-RUS` owns `web/src/entities/**` and `web/src/shared/api/**` and this
   branch touches neither, so the trees do not intersect. It does touch four files in
   `widgets/`, three in `features/`, one in `_pages/` and `shared/ui/` not at all — check
   those eight against whatever `W31-RUS` merged.
2. **Re-gate on a host with address pools.** §4 has the one-line remedy and the exact
   `make gate` command from a committed-clean tree. My `.env` lane is
   `FOUNDATION_INSTANCE=gate-w31b`, ports 56090 / 59690 / 59691.
3. **Expect the frontend figure to be additive, not absolute.** `+7 cases in +1 file` against
   `ae2adf5`'s 772 in 53. If `dev` is at 785 in 55, the merged figure should be **792 in 56**.
4. **Two things want an owner decision and are priced, not built:** the dark default (§6) and
   the icon set (`D-52`).
5. **One thing wants a task that does not exist:** `web/src/_app/**` has no owner this wave,
   and the footer `R-18` names by name lives there.

## 10. Rollback

Additive and revertible commit by commit, newest first:

| Commit | Drop it if |
|---|---|
| `7791f4b` | the three style guards are judged out of scope for this lane. Dropping it loses no styling. |
| `aeded7d` | never usefully — it is one token and a header paragraph, and dropping it reintroduces the only colour literal. |
| `c37b9b9` | the collocated module is judged premature. Dropping it takes the run screen's three classes with it; they would have to go back into `globals.css`. |
| `df80763` | the whole styling layer is being reconsidered. Everything else sits on it. |
