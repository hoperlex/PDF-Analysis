# W42-LOOK — every border to 3:1, and two defects a widened census can now see

**task_id:** `W42-LOOK` · **wave:** 42 · **lane:** `gate-w42b` · **branch:** `agent/w42-look`
**base:** `b0a329b` · **opened:** 2026-09-23, **before the first measurement**

This file is opened first and written as the work happens, so the ordering it claims is the
ordering it was written in. Three pieces:

- **L1** — `R-33` / `D-81`: every border rises to 3:1 in both palettes, with the census
  assertion **written and shown red against today's tokens before the tokens move**.
- **L2** — `D-84`: the decision panel's typed refusal, widened to `string` at the widget
  boundary and matched against a magic literal.
- **L3** — `D-85` and the census residue: the eleven colour-bearing rules no rendered screen
  reaches, named individually and each one classified as dead or unseeded.

## 0. Premises in the brief, checked before anything was built on them

`OPERATING_CONSTRAINTS.md` §12 and the previous wave's two false brief premises are why this
section exists. Every premise below was read in the tree at `b0a329b`.

| premise | verdict |
|---|---|
| `decision-panel.tsx:41` declares `readonly refusal?: string \| null \| undefined` | **true**, line 41 exactly |
| the widget renders on `refusal === 'empty'` | **true**, line 118 |
| `CommentRefusal` is exported from `features/append-comment` | **true**, `index.ts:3`, declared `comment-text.ts:15` as `'empty'`, one member |
| `useAppendComment` returns `CommentRefusal \| null` | **true**, `use-append-comment.ts:47` |
| `sign-in-form.tsx:23` declares `SignInRefusal` and renders on presence | **true**, line 23; the presence test is line 71 and the message is `signInRefusalMessage` |
| `--am-line` `#d9dde3` on `--am-paper` `#ffffff` light; `#27323f` on `#151d28` dark | **true**, `globals.css` token blocks |
| the census reports 11 colour-bearing rules reaching no screen | **true**, `UNREACHED_BY_ANY_SCREEN` in `contrast.test.ts` carries exactly 11 entries |
| `--am-surface` carries four related rows in the register | **true**, `-`, `hover`, `focus-visible`, `active`; `--am-paper` carries four more |

No premise in the brief was found false. Anything discovered beyond them is recorded in the
section it belongs to.

---

## 1. L1 — `R-33` / `D-81`: every border to 3:1

### 1.1 The ordering, which is the deliverable

The assertion was written and **committed red** at `c7cd08f`, against tokens nobody had
touched. The fix is `e1abddd`. A guard written after a fix is a guard nobody has seen fail.

What went red, from the log of `c7cd08f` (`/root/w42look-l1-red2.log`):

```
Tests  2 failed | 17 passed (19)

R-33 ... names the theme, the ratio and the site of every border under the floor
  expected [ { theme: 'dark', …(4) }, …(79) ] to deeply equal []     -- 80 border pairs
every pair that meets on a screen clears the threshold its role asks of it
  expected [ { theme: 'light', …(4) }, …(63) ] to deeply equal []    -- 64 of them
                                                                       unexcused
```

The printed diff carries 72 of the 80 before it truncates. Those 72, by token family, with
the worst ratio in either palette:

| token | occurrences | worst |
|---|---|---|
| `--am-line` | 42 | 1.20 |
| `--am-line-soft` | 10 | 1.08 |
| `--am-inert` @22% | 6 | 1.32 |
| `--am-grid-line` | 4 | 1.13 |
| `--am-ok` @22% | 4 | 1.39 |
| `--am-accent` @22% | 2 | 1.43 |
| `--am-degraded` @26–32% | 2 | 1.44 |
| `--am-failed` @24–30% | 2 | 1.52 |

37 light, 35 dark in the printed part.

### 1.2 Two things the brief did not say, found by the guard

**The ruling reaches five tinted rings nobody had counted.** `R-33` and `D-81` are written
about `--am-line`. The census, once it asked 3:1 of *every* border, also named
`.am-state--error`, `.am-state--warning` and the four badge variants, which drew
`color-mix(in srgb, var(--am-hue) 22–32%, transparent)` and composite to **1.32–2.00:1**
against the page. They are borders, so the ruling reaches them. Reported here rather than
treated as a surprise: the wave's scope is the ruling's, and the ruling says *every*.

**`--am-line-soft` and `--am-grid-line` are worse than `--am-line`.** `D-81` names the
1.30/1.36 pair because it is the load-bearing one. The quiet separator is at **1.08**.

### 1.3 The four `--am-surface` rows in the register, and the four beside them

The brief asked whether one scale decision resolves them. **It does, and it resolves eight
rather than four.** The register carried `edge|--am-line|--am-surface|…` in four states and
`edge|--am-line|--am-paper|…` in four more, every row ending in the same sentence: this is
`--am-line-strong`'s own territory and a three-level scale cannot carry two levels at the
1.4.11 ceiling. That sentence was true while the floor applied to one level. `R-33` applies
it to all of them, so there is no ceiling to compete for, and all eight rows close on the
same token move. **The register is now empty.**

It was not emptied by hand. Moving the tokens made `every registered row is still produced
and still below its threshold` fail, naming all sixteen rows (eight pairs × two palettes) as
excuses for pairs that now pass — wave 32's both-directions check, firing for the second
time in its life.

### 1.4 The values, and why they are these values

Every border token clears 3:1 against **every** surface in its palette — the four page
surfaces and the four semantic tints — not only against the surfaces today's screens happen
to draw it on. That is deliberate: a floor that holds only for the pairs a census currently
produces reddens the day someone puts a card on a tint.

| token | light | dark | worst ratio, light / dark |
|---|---|---|---|
| `--am-line-soft` | `#ebedf1` → `#818790` | `#1b2431` → `#616f80` | 3.08 / 3.13 |
| `--am-grid-line` | `#e6e9ed` → `#7a8089` | `#212b38` → `#667587` | 3.39 / 3.41 |
| `--am-line` | `#d9dde3` → `#6e737b` | `#27323f` → `#748295` | 4.07 / 4.10 |
| `--am-line-strong` | `#838891` → `#60656d` | `#6b7a8d` → `#8491a1` | 5.00 / 5.00 |

The ladder keeps its order and its meaning — soft is the separator inside a card, `line` is a
card edge or a row boundary, strong is a control's own boundary — and `the three border
levels are three levels` still passes in both palettes. Each value carries the hue and
saturation of that palette's existing grey (`#838891` light, `#6b7a8d` dark) at the
luminance the target ratio requires, so the scale is one family rather than four choices.

**The tinted rings are the hue itself**, not a fraction of it. Reaching 3:1 through the mix
needs 59–78% depending on hue and palette; a percentage tuned to land just over a threshold
is a number the next reader cannot check against anything. At full strength the worst ring
in either palette is **4.48:1**, and the rule says what it means: the ring around a failed
state is the failed colour.

### 1.5 Rendered, because arithmetic is half the verification

Both palettes, before and after, in `/root/w42look-evidence/`:

| file | what it shows |
|---|---|
| `{before,after}-{light,dark}-zoom.png` | the project card, the selected finding row, a failed state block, a badge, the upload panel |
| `{before,after}-{light,dark}-controls.png` | the application bar's **theme control** — `D-81`'s own site — plus the decision panel, export panel, knowledge base and sign-in refusal |
| `after-{light,dark}.png` | a ten-screen contact sheet |

Rendered from `screens.ts`'s own markup with `globals.css` linked, screenshotted in the
chromium headless shell at device scale 2, light and dark by `data-theme`. The renderer is
kept beside them as `render-screens.mjs.txt`; it was a temporary test file and is **not** in
the tree.

**What they show.** Before: cards whose edges are a suggestion, a table whose rules are
nearly absent, a badge with no ring. After: an interface with visible boundaries everywhere,
which is the change the owner ruled for, and it reads as a decision rather than as damage —
the four levels are still distinguishable, the dark palette is still a dark palette, and
nothing is boxed twice. The theme control, which had a 1.30:1 outline in the dark palette,
is now a legible pill.

## 2. L2 — `D-84`: a typed refusal widened to `string`

### 2.1 The proof is a compile failure

Before the repair, a second member added to `CommentRefusal` in the tree:

```
npm --prefix web run typecheck          exit 0
```

**Green.** `string` accepts every member anyone will ever add, so `tsc` had nothing to say,
and the reviewer's comment would have been refused while the screen said nothing at all —
the silent fallback `AGENTS.md` §4 forbids by name.

After the repair, the same mutation:

```
npm --prefix web run typecheck          exit 2
src/features/append-comment/model/comment-text.ts(38,65): error TS2366: Function lacks
ending return statement and return type does not include 'undefined'.
```

Give the new member a sentence and both go green again, with the panel rendering it:
typecheck `exit 0`, `viewer-and-panels` 18 passed. That is the full chain — the compiler
refuses until the refusal has words, and the screen shows them by construction.

### 2.2 The repair

The pattern eight files away, as the brief said: `SIGN_IN_REFUSALS` declares the set as an
array, `signInRefusalMessage` switches over it with no `default`, the form renders on
presence and carries the machine value on a `data-` attribute. So:

- `COMMENT_REFUSALS = ['empty'] as const`, with `CommentRefusal` derived from it, which makes
  the set enumerable at run time as well as at compile time;
- `commentRefusalMessage`, a switch with **no `default`** — a `default` would make the
  function total over a union it has not been told about, which is the same silence one layer
  down;
- the widget's prop is `CommentRefusal | null | undefined` and it renders on **presence**,
  with `data-comment-refusal` beside the Russian sentence.

The new test iterates `COMMENT_REFUSALS` rather than naming `'empty'`, because a test that
names the literal is a second copy of the assumption that broke.

## 3. L3 — `D-85` and the census residue

**All eleven, named, with the verdict each one got after being read in `web/src`.** The
count is the least interesting part: a rule no screen reaches is either a missing seed or a
rule nobody needs, and the census cannot tell those apart — only the tree can.

### Dead, deleted (3)

| rule | how it was established |
|---|---|
| `hr` | `grep -rn "<hr" web/src` is empty. Dead CSS. |
| `.am-app__context` | Declared in `globals.css`, rendered by no module. Dead CSS. |
| `.am-evidence__none` | **Unreachable on every input.** `pages` is the distinct set of `page_number` over the observation's *own* evidence; `page` is either an `activePage` in that set or `pages[0]`. So the active page always cites at least one quotation. The branch is deleted with the rule. |

`D-85`'s premise was checked rather than inherited, and it holds.

### A missing seed, seeded (1)

`.am-app__instance`. `W41-BLIND` excused it because *"a static render pass has no environment
to read one from"*. **That premise is false**, in the `OPERATING_CONSTRAINTS.md` §12 shape:
`getInstanceLabel()` reads `process.env.NEXT_PUBLIC_INSTANCE_LABEL` in the component's own
body at render time, and this harness is a node process that can set one. `screens.ts` now
renders the shell with a label and restores the variable afterwards.

### Out of reach of a server render pass (7)

Each entry now says how its colours **are** measured, not only why the rule is unreachable.

| rule | why | how its colours are measured |
|---|---|---|
| `::selection` | the browser composes the highlight | both halves in one block → `declaredPairs` |
| `.am-theme__option[aria-pressed='true']` | `useState('system')` and the stored choice arrives in an **effect**, which SSR does not run, so both options render `aria-pressed="false"` whatever the harness does — checked this wave, not assumed | declares `background` and `color` in one block → `declaredPairs` |
| `.am-quotation:has(…)` | `:has()` is one of the two constructs the matcher declines; named by `unsupported()` | sets `border-left-color` to the same `--am-degraded` its own child declares |
| `.am-export__disclosure[open] > summary` | `<details>` is closed until a click; the component takes no prop that would open it | its one colour is `--am-line-soft` on `--am-surface`, measured at other sites in both palettes |
| `.am-form__chosen` | needs a change event | both halves in one block → `declaredPairs` |
| `.am-form__problem` | needs a click | both halves in one block → `declaredPairs` |
| `.am-form__created` | needs a mutation to settle | both halves in one block → `declaredPairs` |

### 3.1 Deleting a branch on the strength of an argument leaves the argument unchecked

The invariant that made `.am-evidence__none` dead is now a test: the viewer is rendered at
`activePage` 7, 0, −1, 2, 9 and 1000 against evidence on pages 2 and 9 **declared out of
order**, and a quotation must be present on whatever page comes back. Shown to fail —
replacing the fallback with `const page = activePage` reddens 4 of the 6 cases.

### 3.2 A third fixture whose name claimed a state it never reached

`EvidenceViewer no quotation on this page` renders a quotation: `activePage: 7` is not a page
the observation cites, so the viewer falls back to page 2 and shows page 2's. It has been in
the census under that name since wave 41. Renamed to what it exercises — the fallback. The
first two instances were `DecisionPanel refused`, which rendered no refusal, and the finding
list, censused cold while named as though populated. **A fixture's name is not evidence that
a state was reached.**

---

## 4. Checks, each with the commit it was taken at

| check | commit | result |
|---|---|---|
| `npm --prefix web run test -- --run tests/unit/styles/contrast.test.ts` | `c7cd08f` | **2 failed / 17 passed** — the R-33 floor red against untouched tokens, 80 border pairs |
| same | `e1abddd` | 19 passed; the register emptied because the both-directions check demanded it |
| `npm --prefix web run typecheck` (with a second `CommentRefusal` member) | `e1abddd` (pre-repair) | **exit 0** — the defect: `string` hid it |
| `npm --prefix web run typecheck` (same mutation) | `f09c087` | **exit 2, TS2366** — the repair |
| `npm --prefix web run test -- --run tests/unit/review/viewer-and-panels.test.ts` (with `const page = activePage`) | `2a59edb` | **4 of 6 red** — the invariant guard seen to fail |
| `npm --prefix web run typecheck` | `b174a69` | exit 0 |
| `npm --prefix web run lint` | `b174a69` | exit 0 |
| `make gate` (lane `gate-w42b`) | `b174a69`, clean tree | **`GATE OK`** |

Read from the `GATE OK` line of `/root/w42b-gate.log`, not from a status a harness returned
(`OPERATING_CONSTRAINTS.md` §4.62):

```
2361 passed, 5 skipped, 1 warning, 169 subtests passed in 488.11s   (battery)
35 passed in 29.54s                                                 (foundation)
Test Files  72 passed (72)   Tests  1032 passed (1032)              (frontend)
GATE OK: battery, foundation, frontend and whitespace all pass
```

Wave 41 closed at **2361 / 35 / 1022 in 72 files**. The battery and foundation are unchanged
— this wave touches no Python — and the frontend is **1032 in 72 files**, ten tests more: three
for the R-33 floor, one for the refusal union, six for the viewer invariant.

**The run took 488s against a normal ~280s battery, on a host at load average 15 with another
lane and an unrelated node workload live.** Recorded per `OPERATING_CONSTRAINTS.md` §4.6: a
gate that took twice as long as usual is evidence about the machine. It was green, so nothing
turns on it; it is written down because the next session to see 488s should not read it as a
symptom of this change.

## 5. Risks and known limitations

1. **The interface looks different on every screen, and that is the ruling, not a defect.**
   `R-33` was chosen over the targeted option with the arithmetic in front of the owner.
   Anyone meeting the change without the ruling will read it as heavy-handed. The renders are
   in `/root/w42look-evidence/` so the first look does not have to be at a running stand.
2. **The four border levels are closer together than they were.** The compliant band is
   narrow and four levels share it. They are all *visible* levels now, which the light
   palette's soft/line/grid were not, but the step between soft and grid is small.
3. **Scope boundary, named rather than left implicit: the census measures `border-*` and
   `outline` colour properties.** Three colours a reader can see are therefore outside
   `R-33` as implemented — `text-decoration-color: color-mix(… var(--am-accent) 35% …)` on a
   link underline, `--am-ring` (a `box-shadow`, not an outline), and the elevation shadows.
   None is a border; none was raised. If the owner reads `R-33` as reaching a link's
   underline, that is a fourth token move and it is not this wave's.
4. **The census still cannot run a browser.** Seven rules are evaluated only through
   `declaredPairs` or not at all (§3). The pressed theme option, an open disclosure and the
   three form states are reached by the browser journey and by nothing in `make gate`.
5. **`--am-line-strong` in the dark palette (`#8491a1`) now sits close to `--am-ink-soft`
   (`#838d9c`).** A control's boundary is about as light as the quietest text. Both clear
   their own thresholds and no assertion couples them; it is a taste risk, and a palette
   question rather than a compliance one.
6. **The screenshots are a chromium headless shell over `screens.ts`'s static markup**, not
   the deployed stand. Hover, focus and the pressed theme option are not in them; their
   ratios are in the census, which measures states the renders cannot show.

## 6. Reported, not repaired

- **`R-33` reaches five tinted rings the ruling's text does not mention** (§1.2). Repaired
  here, because they are borders and the ruling says every border — but the owner should
  know the change is wider than `D-81`'s row reads.
- **`W41-BLIND`'s reason for excusing `.am-app__instance` was false** (§3). No harm done: it
  excused a rule rather than permitting a defect, and it is closed.
- **A third fixture whose name claimed a state it never reached** (§3.2).
- **Nothing outside the grant was touched.** `web/FRONTEND_LOCK.json`, `web/openapi/**` and
  `web/src/shared/api/generated/**` are `W42-SEAL`'s and do not appear in this branch's diff.
