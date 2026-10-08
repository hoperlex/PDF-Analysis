# W50-SHELL-UI — completion report

## Result

**DONE.** Branch `agent/w50-shell-ui` from base `96a1653` (= `origin/dev` = `integration/w50`,
the commit carrying the "Integrator rulings at the `W50-REGISTRY-01` merge" section).
`web/src/shared/ui/` exports `Disclosure` (the APG disclosure pattern), `Menu` (the APG menu
button pattern) and `Avatar` (initials on a circle coloured by a hash of the e-mail);
`globals.css` declares fourteen pairs `--am-avatar-NN` / `--am-avatar-NN-ink` in `:root` and in
both dark blocks, plus one rule per primitive class; a new test reads every avatar declaration
and holds the initials to 4.5:1 and the circle to 3:1 against the page and the bar in every
block. No new dependency, no contract change, nothing renders the primitives yet.

Code commit: `cfa4966`. This report is a docs-only commit on top of it; **the gate measured
`cfa4966`** (§2.6).

## 1. Changed files

`git diff --name-only 96a1653..cfa4966` (13 paths; this report adds the 14th):

```
web/src/app/globals.css
web/src/shared/ui/avatar-colour.ts
web/src/shared/ui/avatar.tsx
web/src/shared/ui/disclosure-state.ts
web/src/shared/ui/disclosure.tsx
web/src/shared/ui/index.ts
web/src/shared/ui/menu-state.ts
web/src/shared/ui/menu.tsx
web/tests/unit/styles/avatar-palette.test.ts
web/tests/unit/styles/screens.ts
web/tests/unit/ui/avatar.test.ts
web/tests/unit/ui/disclosure.test.ts
web/tests/unit/ui/menu.test.ts
```

Every path matches one of the grant's `allowed_paths` (`web/src/shared/ui/**`,
`web/src/app/globals.css`, `web/tests/unit/styles/**`, `web/tests/unit/ui/**`,
`docs/program/W50-SHELL-UI.md`), checked by a script over the list with `fnmatch`: 0 outside.

What each is:

| path | what |
|---|---|
| `shared/ui/disclosure-state.ts` | `disclosureTransition(open, event)` — the pure open/close logic |
| `shared/ui/disclosure.tsx` | `'use client'`: `DisclosureView` (pure markup) and the `Disclosure` island |
| `shared/ui/menu-state.ts` | `menuTransition(state, event, count)` — the pure keyboard/open/close logic, `MENU_CLOSED` |
| `shared/ui/menu.tsx` | `'use client'`: `MenuView` (pure markup) and the `Menu` island |
| `shared/ui/avatar-colour.ts` | `avatarColourIndex` (32-bit FNV-1a of the normalised e-mail, mod 14), `AVATAR_PALETTE_SIZE`, `normaliseColourKey` |
| `shared/ui/avatar.tsx` | `Avatar` (server component), `AvatarInitialsError` |
| `shared/ui/index.ts` | exports the three primitives, their prop types and the pure functions |
| `app/globals.css` | 28 avatar tokens × 3 blocks; the disclosure, menu and avatar rules |
| `tests/unit/ui/*.test.ts` | keyboard/state tests for both primitives; the avatar hash and markup |
| `tests/unit/styles/avatar-palette.test.ts` | the dedicated 14 × 2 palette test (Enumerator section of the grant) |
| `tests/unit/styles/screens.ts` | census seeds: disclosure closed / open / stacked, menu closed / open, one avatar per pair |

## 2. Checks and their results

### 2.1 Premises, re-measured at the base

```
$ git ls-tree -r --name-only 96a1653 web/src/shared/ui
web/src/shared/ui/icon.tsx
web/src/shared/ui/index.ts
web/src/shared/ui/page-shell.tsx
web/src/shared/ui/route-placeholder.tsx
web/src/shared/ui/run-state-badge.tsx
web/src/shared/ui/stage-label.ts
web/src/shared/ui/stage-status-badge.tsx
web/src/shared/ui/states.tsx
$ git ls-tree -d --name-only 96a1653 web/tests/unit/
web/tests/unit/api  …/decisions  …/entities  …/export  …/lib  …/projects  …/qa_w49
…/review  …/run  …/screens  …/session  …/styles  …/widgets
```

P-01 holds (the same eight files the grant captured at `ead639f`); P-02 holds (no
`web/tests/unit/ui`; `entities` is new since `ead639f`, added by `W50-REGISTRY-01`).

### 2.2 Frontend suite

`npm --prefix web test -- --run`:

- base `96a1653` (this worktree, before any edit): **91 files / 1399 tests**, all passed;
- head `cfa4966`: **95 files / 1459 tests**, all passed.

The +4 files / +60 tests are exactly the new files: `tests/unit/ui/disclosure.test.ts` 15,
`tests/unit/ui/menu.test.ts` 23, `tests/unit/ui/avatar.test.ts` 12,
`tests/unit/styles/avatar-palette.test.ts` 10. Every other file's count is unchanged; the
census (`contrast.test.ts`, 20 tests) gains six seeded screens and stays green in both palettes,
with its `unsupported()` list unchanged (no `:not()`, `:has()` or `:focus-within` was added).

### 2.3 Lint, typecheck, whitespace

`npm --prefix web run lint -- --quiet` — no output, exit 0. `npm --prefix web run typecheck`
— no output, exit 0. `git diff --check 96a1653..cfa4966` — clean.

### 2.4 The measured palette — 14 × 2, produced by the test

Command (on `cfa4966`):

```
AM_AVATAR_TABLE=1 npm --prefix web test -- --run tests/unit/styles/avatar-palette.test.ts
```

`initials : circle` is the text ratio (floor 4.5); `circle : page` is against `body`'s
background (`--am-surface`), `circle : bar` against `.am-app__bar`'s (`--am-paper`), both read
off the stylesheet (floor 3). The two dark blocks are asserted equal, so the table shows the
explicit-choice one; the test measures all three blocks.

| theme | pair | circle | ink | initials : circle | circle : page | circle : bar |
|---|---|---|---|---|---|---|
| light | 01 | #a34145 | #ffffff | 6.18 | 5.71 | 6.18 |
| light | 02 | #9f4716 | #ffffff | 6.20 | 5.73 | 6.20 |
| light | 03 | #885703 | #ffffff | 6.16 | 5.69 | 6.16 |
| light | 04 | #716004 | #ffffff | 6.22 | 5.75 | 6.22 |
| light | 05 | #536a03 | #ffffff | 6.12 | 5.66 | 6.12 |
| light | 06 | #107030 | #ffffff | 6.21 | 5.74 | 6.21 |
| light | 07 | #066f5b | #ffffff | 6.12 | 5.66 | 6.12 |
| light | 08 | #026c71 | #ffffff | 6.20 | 5.74 | 6.20 |
| light | 09 | #036a87 | #ffffff | 6.15 | 5.69 | 6.15 |
| light | 10 | #1a64a8 | #ffffff | 6.12 | 5.66 | 6.12 |
| light | 11 | #535aac | #ffffff | 6.13 | 5.67 | 6.13 |
| light | 12 | #744fa2 | #ffffff | 6.21 | 5.74 | 6.21 |
| light | 13 | #8c478a | #ffffff | 6.21 | 5.74 | 6.21 |
| light | 14 | #9d416b | #ffffff | 6.17 | 5.71 | 6.17 |
| dark | 01 | #dd8c8b | #0d1219 | 7.34 | 7.34 | 6.62 |
| dark | 02 | #d9916f | #0d1219 | 7.36 | 7.36 | 6.65 |
| dark | 03 | #ca995a | #0d1219 | 7.35 | 7.35 | 6.63 |
| dark | 04 | #b3a154 | #0d1219 | 7.29 | 7.29 | 6.58 |
| dark | 05 | #95aa63 | #0d1219 | 7.34 | 7.34 | 6.63 |
| dark | 06 | #71b07c | #0d1219 | 7.34 | 7.34 | 6.62 |
| dark | 07 | #50b29a | #0d1219 | 7.32 | 7.32 | 6.60 |
| dark | 08 | #41b2b7 | #0d1219 | 7.41 | 7.41 | 6.68 |
| dark | 09 | #51accf | #0d1219 | 7.29 | 7.29 | 6.58 |
| dark | 10 | #72a6de | #0d1219 | 7.36 | 7.36 | 6.64 |
| dark | 11 | #939de2 | #0d1219 | 7.30 | 7.30 | 6.59 |
| dark | 12 | #b195d9 | #0d1219 | 7.31 | 7.31 | 6.60 |
| dark | 13 | #c88fc5 | #0d1219 | 7.33 | 7.33 | 6.61 |
| dark | 14 | #d88caa | #0d1219 | 7.38 | 7.38 | 6.66 |

Worst figures: light text 6.12, light circle 5.66; dark text 7.29, dark circle 6.58. How the
values were derived is in the `globals.css` comment above them: OKLCH hue 20° + k·360°/14,
chroma 0.13 light / 0.10 dark (lowered only where sRGB cannot hold it), lightness solved so the
WCAG relative luminance of every circle is 0.12 (light) / 0.36 (dark); the ink is whichever of
white and near-black contrasts more with that circle.

### 2.5 Mutations, each red

Run one at a time in a disposable `git clone --shared` of `cfa4966` at `/root/w50ui-mut`
(`web/node_modules` symlinked from the worktree), by a script that applies one edit, runs the
named test files, records the output and restores the copy with `git checkout -- web/src
web/tests` before the next. Baseline first: the unmutated copy ran `tests/unit/ui
tests/unit/styles` → `Test Files 7 passed (7)`, `Tests 107 passed (107)`. Every run prints
`RUN v3.2.7 /root/w50ui-mut/web`, so the copy is the tree under test. Exit status 1 in every
case. Output trimmed to the failing tests and the assertion; `…` marks the cut.

**M01 — a `div` trigger in `Disclosure`** (`<button type="button" …>` → `<div …>` in the view)
```
$ npm --prefix web test -- --run tests/unit/ui/disclosure.test.ts        (exit 1)
   × … > its trigger is a real <button type="button">, in the island and in the view
   × … > marks the current page on its link and the current group on its button
   × … > holds arbitrary content instead of links, which is how the stacked menu nests groups
      Tests  3 failed | 12 passed (15)
AssertionError: expected 'div' to be 'button' // Object.is equality
```

**M02 — a `div` trigger in `Menu`**
```
$ npm --prefix web test -- --run tests/unit/ui/menu.test.ts              (exit 1)
   × the menu button and its menu > its trigger is a real <button type="button"> with aria-haspopup="menu"
      Tests  1 failed | 22 passed (23)
AssertionError: expected 'div' to be 'button' // Object.is equality
```

**M03 — a light pair below the text floor, one value** (`:root` `--am-avatar-05: #536a03` →
`#8a8a8a`; the circle still clears 3:1, so only the text floor can fire)
```
$ npm --prefix web test -- --run tests/unit/styles/avatar-palette.test.ts tests/unit/styles/contrast.test.ts   (exit 1)
   × every pair is legible in both palettes > the initials clear 4.5:1 and the circle clears 3:1 against the page and the bar
   × every pair that meets on a screen clears the threshold its role asks of it > holds in BOTH palettes, …
      Tests  2 failed | 28 passed (30)
+   ":root pair 05 (#ffffff on #8a8a8a): initials 3.45:1 < 4.5",
+   ":root pair 05 (#ffffff on #8a8a8a): the ink is white, and near-black reads better here",
…
+     "pair": "text|--am-avatar-05-ink|--am-avatar-05|-|-",
+     "ratio": 3.45,
+     "theme": "light",
+       "Avatar, one per colour pair body > header.am-app__bar > span.am-avatar.am-avatar--05",
```
The census reddens too, through the seed that renders one avatar per pair.

**M04 — a dark pair below the text floor, one value** (explicit dark block
`--am-avatar-03: #ca995a` → `#707070`)
```
$ npm --prefix web test -- --run tests/unit/styles/avatar-palette.test.ts tests/unit/styles/contrast.test.ts tests/unit/styles/theme.test.ts   (exit 1)
      Tests  6 failed | 40 passed (46)
+   ":root[data-theme='dark'] pair 03 (#0d1219 on #707070): initials 3.79:1 < 4.5",
+   ":root[data-theme='dark'] pair 03 (#0d1219 on #707070): the ink is near-black, and white reads better here",
+   "pair 03 differs between the two dark blocks",
…   (census: "text|--am-avatar-03-ink|--am-avatar-03|-|-", ratio 3.79, theme "dark";
     theme.test.ts: the two dark blocks "have drifted apart")
```
One value in one dark block is also a drift, so the completeness and parity checks fire beside
the floor; the "can fail" case of the palette test reddens as well, because its fixtures are
built from the (now mutated) real stylesheet.

**M05 — a light pair below the circle floor, one value** (`:root` `--am-avatar-10: #1a64a8` →
`#a8c4e0`)
```
$ npm --prefix web test -- --run tests/unit/styles/avatar-palette.test.ts   (exit 1)
      Tests  1 failed | 9 passed (10)
+   ":root pair 10 (#ffffff on #a8c4e0): initials 1.80:1 < 4.5",
+   ":root pair 10 (#ffffff on #a8c4e0): circle on the page 1.67:1 < 3",
+   ":root pair 10 (#ffffff on #a8c4e0): circle on the bar 1.80:1 < 3",
+   ":root pair 10 (#ffffff on #a8c4e0): the ink is white, and near-black reads better here",
```
With white ink no single light value can fail the circle floor alone (a circle too pale for 3:1
on the page is too pale for white text), so M06 isolates it.

**M06 — the circle floor alone** (pair 11 in both dark blocks: circle `#3a4f8a`, ink `#ffffff`;
four values, so text and parity still pass and only the circle check can fire)
```
$ npm --prefix web test -- --run tests/unit/styles/avatar-palette.test.ts   (exit 1)
      Tests  1 failed | 9 passed (10)
+   ":root:not([data-theme='light']) pair 11 (#ffffff on #3a4f8a): circle on the page 2.38:1 < 3",
+   ":root:not([data-theme='light']) pair 11 (#ffffff on #3a4f8a): circle on the bar 2.15:1 < 3",
+   ":root[data-theme='dark'] pair 11 (#ffffff on #3a4f8a): circle on the page 2.38:1 < 3",
+   ":root[data-theme='dark'] pair 11 (#ffffff on #3a4f8a): circle on the bar 2.15:1 < 3",
```

**M07 — Escape does not close the `Disclosure`** (`event.key === 'Escape'` → `'Esc'`)
```
$ npm --prefix web test -- --run tests/unit/ui/disclosure.test.ts        (exit 1)
   × disclosureTransition: what each event does > Escape closes an open disclosure and returns focus to its button
   × disclosureTransition: what each event does > nested: one Escape closes one level, from the inside out
      Tests  2 failed | 13 passed (15)
AssertionError: expected { open: true, focus: null, …(1) } to deeply equal { open: false, focus: 'button', …(1) }
```

**M08 — Escape on an item does not close the `Menu`**
```
$ npm --prefix web test -- --run tests/unit/ui/menu.test.ts              (exit 1)
   × menuTransition: closing, and where focus goes > Escape on an item closes and returns focus to the trigger
   × menuTransition: closing, and where focus goes > a whole keyboard journey: open, walk, Escape, and back on the trigger
      Tests  2 failed | 21 passed (23)
```

**M09 — Escape on the trigger of an open `Menu` does not close it**
```
$ npm --prefix web test -- --run tests/unit/ui/menu.test.ts              (exit 1)
   × menuTransition: closing, and where focus goes > Escape on the trigger of an open menu closes it too
      Tests  1 failed | 22 passed (23)
```

**M10 — focus does not return to the `Menu` trigger after an item is chosen**
(`closed(TRIGGER, false)` → `closed(null, false)` for `chosen`)
```
$ npm --prefix web test -- --run tests/unit/ui/menu.test.ts              (exit 1)
   × menuTransition: closing, and where focus goes > choosing an item closes the menu and returns focus to the trigger
      Tests  1 failed | 22 passed (23)
```

**M11 — focus does not return to the `Disclosure` button on Escape** (`focus: 'button'` → `null`)
```
$ npm --prefix web test -- --run tests/unit/ui/disclosure.test.ts        (exit 1)
   × disclosureTransition: what each event does > Escape closes an open disclosure and returns focus to its button
      Tests  1 failed | 14 passed (15)
AssertionError: expected { open: false, focus: null, …(1) } to deeply equal { open: false, focus: 'button', …(1) }
```

**M12 — `role="menu"` on the disclosure's list**
```
$ npm --prefix web test -- --run tests/unit/ui/disclosure.test.ts        (exit 1)
   × … > holds links, and no menu role anywhere: the items are links, not commands
      Tests  1 failed | 14 passed (15)
AssertionError: a disclosure carries no role="menu" / "menuitem": expected [ 'menu' ] to deeply equal []
```

**M13 — no `aria-controls` on the disclosure's button**
```
$ npm --prefix web test -- --run tests/unit/ui/disclosure.test.ts        (exit 1)
   × … > aria-controls names the panel, which is always in the markup
   × … > is closed by default: the island renders aria-expanded="false" and a hidden panel
   × … > the island renders exactly the closed view, so the census measures what ships
   × … > holds arbitrary content instead of links, which is how the stacked menu nests groups
      Tests  4 failed | 11 passed (15)
AssertionError: the trigger has no aria-controls: expected undefined to be truthy
```

**M14 — no `aria-controls` on the menu's trigger**
```
$ npm --prefix web test -- --run tests/unit/ui/menu.test.ts              (exit 1)
   × the menu button and its menu > aria-controls names the role="menu" element, which the trigger labels
   × the menu button and its menu > is closed by default, and the island renders exactly the closed view
      Tests  2 failed | 21 passed (23)
AssertionError: the trigger has no aria-controls: expected undefined to be truthy
```

**M15 — `--am-avatar-07` removed from one dark block** (the explicit-choice block)
```
$ npm --prefix web test -- --run tests/unit/styles/avatar-palette.test.ts tests/unit/styles/theme.test.ts   (exit 1)
      Tests  6 failed | 20 passed (26)
+   ":root[data-theme='dark']: pair 07 has no circle, --am-avatar-07",
+   "pair 07 differs between the two dark blocks",
+   ":root[data-theme='dark'] pair 07 (#0d1219 on #066f5b): initials 3.07:1 < 4.5",
+   ":root[data-theme='dark'] pair 07 (#0d1219 on #066f5b): circle on the bar 2.77:1 < 3",
…   (theme.test.ts: "These tokens carry a colour in `:root` and have no value in the dark block" → [ "--am-avatar-07" ])
```
The light circle falling through into the dark theme is exactly what the measurement then sees.

**M16 — the avatar hash keyed on the label (or initials) instead of the e-mail**
(`avatarColourIndex(colourKey)` → `avatarColourIndex(label ?? letters)`)
```
$ npm --prefix web test -- --run tests/unit/ui/avatar.test.ts            (exit 1)
   × the colour is keyed on the e-mail, never on the name > a corrected name keeps its colour: same e-mail, different initials and label
   × the colour is keyed on the e-mail, never on the name > two accounts with the same initials are told apart by their addresses
   × the colour is keyed on the e-mail, never on the name > the rendered pair is the hash of the colour key, numbered from 01
      Tests  3 failed | 9 passed (12)
AssertionError: expected '14' to be '12' // Object.is equality
```

Two more, beyond the grant, for the two claims the census half rests on:

**M17 — the hash modulus no longer equals the pairs declared** (`AVATAR_PALETTE_SIZE` 14 → 13)
```
$ npm --prefix web test -- --run tests/unit/styles/avatar-palette.test.ts tests/unit/ui/avatar.test.ts   (exit 1)
   × … > the hash's modulus is the number of pairs the stylesheet declares
      Tests  1 failed | 21 passed (22)
AssertionError: expected 13 to be 14 // Object.is equality
```

**M18 / M19 — the census seeds are load-bearing.** Removing the one-avatar-per-pair seed:
```
$ npm --prefix web test -- --run tests/unit/styles/contrast.test.ts   (exit 1)
   × the census is taken over rendered screens, not over a list > names every colour-bearing rule that NO rendered screen reaches
      Tests  1 failed | 19 passed (20)
+   ".am-avatar--01", … ".am-avatar--06", ".am-avatar--08", … ".am-avatar--14",
```
(13 rules: pair 07 stays reached through the menu seeds' trigger avatar). Removing the three
open-state seeds (menu open, disclosure open, stacked menu):
```
$ npm --prefix web test -- --run tests/unit/styles/contrast.test.ts   (exit 1)
      Tests  1 failed | 19 passed (20)
+   ".am-disclosure--inline > .am-disclosure__panel",
+   ".am-disclosure__button[aria-expanded='true']",
```
Only these two: the panels are in the markup while closed (`hidden`), so the closed seeds already
reach the other rules — which is the reason the open seeds are there at all.

(A first form of M18/M19 replaced `add(` with `void (`, which left a trailing comma inside a
parenthesised expression; the file failed to load — `Tests no tests` — which is not a red for
the right reason. It was replaced by the call form above and rerun; the outputs quoted are the
rerun's.)

### 2.6 `make gate`

Run once, from the worktree on a clean tree at `cfa4966` (`git status --porcelain -uall`
empty before and after), through the integrator's lock wrapper
(`/root/projects/PDF-Analysis/.local/w50-stage-b-gate.lock`, memory ≥ 3 GB and no other
`make gate` running) into `.local/gate.log`; started 2026-10-06T16:02:19Z, finished
≈16:19:41Z. Verdict read from the log, not from the wrapper's status:

```
============================= 35 passed in 25.86s ==============================   (foundation)
foundation sequence complete
3183 passed, 6 skipped, 5 warnings, 298 subtests passed in 952.71s (0:15:52)        (battery)
 Test Files  95 passed (95)                                                          (frontend)
      Tests  1459 passed (1459)
GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass
exit=0
```

**The gate measured the code commit `cfa4966`.** This report is the only commit after it and
touches only `docs/program/W50-SHELL-UI.md`.

## 3. Contracts

No change to `contracts/**`, the API surface (27 / 34 / 77), the error catalog, the migration
head or the dependency set (`web/package.json`, `web/package-lock.json`,
`web/FRONTEND_LOCK.json` untouched).

New in-tree interfaces, for `W50-SHELL-FRAME`, all from `@/shared/ui`:

- `Disclosure(props: DisclosureProps)` — `label`, `current?` (the group holds the current page →
  `aria-current="true"` on the button), `layout?: 'popover' | 'inline'`, `align?: 'start' |
  'end'`, and either `links: DisclosureLink[]` (`{ href, label, current? }` → `aria-current="page"`)
  or `children` (the stacked «Меню» nests inline groups this way). Closed by default.
- `Menu(props: MenuProps)` — `label` (the trigger's accessible name), `trigger` (its content,
  the avatar), `header?` (outside `role="menu"`), `items: [MenuItem, ...MenuItem[]]` where a
  `MenuItem` is `{ kind: 'link', label, href }` or `{ kind: 'submit', label, action }` (a
  `<button type="submit" role="menuitem">` in its own `<form method="post" action>`).
- `Avatar(props: AvatarProps)` — `initials`, `colourKey` (the subject's `login`, i.e. the
  e-mail), `label?` (omitted: `aria-hidden`; given: `role="img"` with that name). Blank
  initials throw `AvatarInitialsError`.
- The pure logic: `disclosureTransition`, `menuTransition`, `MENU_CLOSED`, their event/state
  types; `avatarColourIndex`, `normaliseColourKey`, `AVATAR_PALETTE_SIZE`.
- Tokens: `--am-avatar-01` … `--am-avatar-14` and `--am-avatar-01-ink` … `--am-avatar-14-ink`,
  each declared in `:root`, `@media (prefers-color-scheme: dark) :root:not([data-theme='light'])`
  and `:root[data-theme='dark']`.
- Classes, each with a rule: `am-disclosure` (`--inline`, `--end`), `am-disclosure__button`,
  `__panel`, `__list`, `__item`, `__link`; `am-menu`, `am-menu__trigger`, `__popup`, `__header`,
  `__list`, `__entry`, `__form`, `__item`; `am-avatar`, `am-avatar--01` … `--14`.

`DisclosureView` and `MenuView` are exported from their modules (`@/shared/ui/disclosure`,
`@/shared/ui/menu`) for tests and the census, not from the index: they are what the islands
render, and the frame should use the islands.

## 4. Risks and known limitations

- **No browser has run these islands.** The node test environment has no DOM, so the tests
  drive the pure transitions and read server-rendered markup. That focus actually lands where a
  transition says, that the document `pointerdown`/`focusin` listener closes an open panel, that
  Tab out of an open menu (closed in the keydown, default not prevented) lands on the next
  tabbable, and that a submit item still posts after its menu hides in the same click — all are
  exercised first by `W50-SHELL-FRAME` and `W50-QA-01`. The islands are thin (`apply` = set
  state + focus a ref), but they are not covered by a test that executes them.
- **Popover placement is CSS only.** The disclosure panel opens under its button (`left: 0`, or
  `right: 0` with `align: 'end'`), the menu popup under the trigger's right edge, both capped at
  `calc(100vw - 32px)`. No script measures the viewport, so a group near the right edge at the
  780 px floor must be given `align: 'end'` by the frame; `W50-SHELL-FRAME`'s overflow mutations
  are where that is proven.
- **Optional parts of the APG menu pattern are not implemented**, and `menu-state.ts` says so:
  type-ahead, and Space as an activation key on a link item (Space on the submit item activates
  it natively). Neither is needed for a three-item account menu.
- **The disclosure does not take over the arrow keys** — deliberately: its items are links, and
  the APG disclosure-navigation pattern leaves arrow-key movement optional. Tab walks the links.
- **"White or near-black chosen per pair"**: the rule is per pair and asserted per pair (the ink
  must be whichever of the two contrasts more with that circle — M03/M04 show it firing). At the
  two equalised luminances it selects white for every light pair and near-black for every dark
  pair, so the palette carries no mixed theme. If the owner prefers more natural-looking yellows
  (lighter circles with dark ink in the light theme), the luminance per hue can vary; the test
  needs no change for that.
- **The page background** the circle is held against is read from the `body` rule
  (`--am-surface`) and, because the frame puts the account menu in the bar, from `.am-app__bar`
  (`--am-paper`). If `W50-SHELL-FRAME` places an avatar on another surface, that surface is not
  in this test.
- `AvatarInitialsError` makes a blank-initials avatar a render error rather than a blank
  circle. The subject's `initials` is never empty by construction upstream (`initialsOf`
  returns at least the label's first character, and the label itself is never empty), so this
  is unreachable through the session; it is loud on purpose.
- The `useId`-derived ids (`_R_…_panel`, `_R_…_trigger`, `_R_…_menu`) are React's; nothing
  outside the component should select on them.

## 5. Integrator notes

- Hand-back: branch `agent/w50-shell-ui`, code commit `cfa4966`, report commit on top. Base
  `96a1653`. Stage-B merge order is `W50-SHELL-UI` first (`W50-PLAN.md` §5), and this lane
  touches no path of HOME or LAZY.
- `globals.css` overlap: this lane is its only W50 writer; the additions are three token runs
  (one per palette block, placed after `--am-inert-light`) and one new section after
  `.am-theme__option:focus-visible`. No existing rule or token changed.
- `tests/unit/styles/screens.ts` gains six screens at the end of `screens()`, before the final
  comment. If `W50-LAZY-01` edits `screens.ts`, the hunks are disjoint.
- For `W50-SHELL-FRAME`: compose from `@/shared/ui` only. Use `align: 'end'` for a group at the
  right of the bar; `layout: 'inline'` for groups inside the stacked «Меню» (pass them as the
  outer disclosure's `children`); `Avatar` with `colourKey={session.login}` and no `label`
  inside the menu trigger (the trigger's `label` names the account); `Выйти` as
  `{ kind: 'submit', label: 'Выйти', action: SESSION_CLOSE_PATH }`.
- Lane resources: `FOUNDATION_INSTANCE=gate-w50ui`, `POSTGRES_PORT=56650`, `S3_API_PORT=60250`,
  `S3_CONSOLE_PORT=60251`, `POSTGRES_DB=auditmanager_w50ui`, `S3_BUCKET=auditmanager-w50ui`;
  the three ports were checked free with `ss -ltn` at setup and again just before the gate.
  After the gate: `make down` (exit 0: the three `gate-w50ui-*` containers and
  `gate-w50ui-net` removed), then `docker volume rm gate-w50ui-postgres-data
  gate-w50ui-s3-data` by exact name; afterwards no `w50ui` container, volume or network remains
  and the three ports are free. The mutation clone `/root/w50ui-mut` was removed (its
  `node_modules` was a symlink, unlinked first). No process was killed.

## 6. Forbidden hotspots

`git diff --name-only 96a1653..HEAD` is the list in §1 plus this report. None of it is under
`contracts/**`, `web/src/shared/api/**`, `db/**` migrations, `src/**`, a root lock,
`web/package.json`, `web/package-lock.json`, `web/FRONTEND_LOCK.json`, `web/src/_app/**`
(including `providers.tsx`), `web/src/app/**` other than `globals.css`, `web/src/_pages/**`,
`web/src/widgets/**`, `web/src/entities/**`, `web/src/features/**`, `web/src/shared/config/**`,
`tests/e2e/**`, or `CURRENT_STATE.md` / `DEBT_REGISTER.md` / `OWNER_RULINGS_*.md` /
`PORT_REGISTRY.md`. `shared/ui` imports nothing above `shared` (`@/shared/lib`, `next/link`,
`react`); `eslint-boundary.guard.test.ts` and lint are green. No ref was pushed, no tag created,
no merge made, no worktree removed.
