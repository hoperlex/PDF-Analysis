# W32-CONTRAST — the token set's legibility becomes a measured figure with a guard

**Task:** `W32-CONTRAST`. **Base:** `cd475cc`. **Branch:** `agent/w32-contrast`, worktree `/root/w32contrast`.
**Contracts touched:** none. **Consumers touched:** none. **Rules changed:** none — three token *values*.

`W31-STYLE` closed its report with a named risk in its own words: *"the `-light` tints were
chosen by eye, no WCAG figure is claimed."* For an interface whose whole purpose is that a
domain expert reads findings carefully, "chosen by eye" is the wrong standard for text
legibility, and unlike most of `R-18` this one has an objective measure. This is that
measure, the repairs it forced, the guard that keeps them, and the four premises of the
brief that turned out to be false.

---

## 0. In one paragraph

The brief handed this wave twelve ratios over eleven pairs and called them "the integrator's
guess at which pairs matter". **All eleven reproduce to the digit** — and they are not the
census. Rendering thirty real screens and resolving the cascade over them finds **120 pairs**,
of which **78 answer to a WCAG threshold**, and **the worst text failure in the tree is not
among the twelve**: `--am-ink-soft` at **2.68:1** on `--am-failed-light`, carrying the
correlation id under a failed query. Three token values moved; every text pair on every
rendered screen now clears AA 4.5 except one, which needs a rule change this task may not
make and is registered. **The third ink level did not survive the repair as a level**: AA on
the darkest text surface caps any foreground just above `--am-ink-muted`, so the whole window
for a compliant third ink is 1.14:1 wide. It now passes everywhere and is 1.10:1 from muted.
Saying so was the brief's own instruction and it is the honest form of this result.

---

## 1. The co-occurrence census

### 1.1 How it was established

Two ways, because neither alone is a census.

**Rendered.** `web/tests/unit/styles/screens.ts` renders **30 screens** — every page and every
widget in `web/src`, each in the states that put a different ink on a different tint: a
selected finding row, a failed query, a quotation whose anchor disagrees with its text, a
disabled control, five badge tones, six run outcomes. `web/tests/unit/styles/contrast.ts`
then parses the rendered markup into an element tree, parses `globals.css` and
`run-progress.module.css` into rules, matches selectors against the tree, resolves the
cascade by specificity and source order, and for every element computes **the colour it
inherits** and **the nearest self-or-ancestor background**. A pair is recorded when an
element that carries text has both.

This is the half that matters, and the reason is visible in the output: **the four worst
pairs in the tree are ones no rule declares.** Nothing in `globals.css` says
`--am-ink-soft` on `--am-failed-light`; `.am-state__correlation` declares the ink and
`.am-state--error`, two levels up, declares the tint. A reading of the stylesheet cannot see
it. A rendered screen can.

**Declared.** One server render pass cannot fire an event or run an effect, so
`.am-form__created`, `.am-form__problem` and `.am-form__chosen` — which appear only after a
click — are unreachable by it. Each declares its ink and its tint in the *same rule*, so
`declaredPairs()` reads them off the stylesheet with no markup at all. The two censuses are
unioned. The declared pass contributed **2** pairs the render did not reach; that it
contributed so few is itself the evidence that the render is wide.

No dependency was added. `web/FRONTEND_LOCK.json` is untouched and `package.json` is
unchanged. The WCAG formula is ten lines; the cascade is about two hundred.

### 1.2 What it found

| | count |
|---|---|
| screens rendered | 30 |
| distinct (foreground, background, state, pseudo-element) pairs | 120 |
| pairs answering to a WCAG threshold | 78 |
| text pairs below 4.5 **before** the repair | 9 |
| text pairs below 4.5 **after** the repair | 1 (registered, §3.4) |
| 1.4.11 boundary/graphic pairs below 3.0 **before** | 11 |
| 1.4.11 pairs below 3.0 **after** | 4 (one token, registered, §3.3) |
| selectors the matcher declined | 1 (`:has()`, §6.5) |

**Reproduce:**

```
cd /root/w32contrast/web && npx vitest run tests/unit/styles/
```

### 1.3 The pairs the brief's list did not have

Eight text pairs co-occur that the brief's eleven do not name. Five of them were failing.

| pair | ratio before | where it meets | how |
|---|---|---|---|
| `ink-soft` on `failed-light` | **2.68** | `.am-state__correlation` inside `.am-state--error` | ancestor |
| `ink-soft` on `accent-light` | **2.70** | `.am-finding-row__pages` inside the **selected** row | ancestor |
| `ink-soft` on `inert-light` | **2.75** | `.am-button:disabled` label | one rule |
| `ink-soft` on `surface-sunken` | **2.76** | `.am-export__disclosure` marker, page-range spans | ancestor |
| `inert` on `accent-light` | **4.15** | a `pending` badge inside a selected finding row | ancestor |
| `ink-muted` on `surface-sunken` | 5.26 | the most common pair in the tree, 41 sites | ancestor |
| `ink-muted` on `failed-light` | 5.11 | `.am-state__detail` inside a failure | ancestor |
| `accent` on `accent-light` | 7.07 | `.am-badge--active` — the running-state badge | one rule |

Eleven of the twelve figures in the brief are about pairs a rule declares. **The failures
live where two rules meet**, which is exactly what a stylesheet reading cannot show and a
render can.

---

## 2. Every pair's ratio, before and after

Produced by the command in §1.1, against `cd475cc` (before) and `HEAD` (after). Bold is
below threshold.

| pair | kind | before | after | needs |
|---|---|---|---|---|
| `--am-ink-soft` on `--am-failed-light` | text | **2.68** | 4.65 | 4.5 |
| `--am-ink-soft` on `--am-accent-light` | text | **2.70** | 4.68 | 4.5 |
| `--am-ink-soft` on `--am-inert-light` | text | **2.75** | 4.78 | 4.5 |
| `--am-ink-soft` on `--am-surface-sunken` | text | **2.76** | 4.78 | 4.5 |
| `--am-ink-soft` on `--am-surface` | text | **2.91** | 5.04 | 4.5 |
| `--am-ink-soft` on `--am-paper` | text | **3.14** | 5.45 | 4.5 |
| `--am-inert` on `--am-inert-light` | text | **4.23** | 4.61 | 4.5 |
| `--am-inert` on `--am-accent-light` | text | **4.15** | 4.51 | 4.5 |
| `--am-line-strong` on `--am-surface-sunken` | 1.4.11 | **1.68** | 3.12 | 3.0 |
| `--am-line-strong` on `--am-accent-light` | 1.4.11 | **1.64** | 3.06 | 3.0 |
| `--am-line-strong` on `--am-surface` | 1.4.11 | **1.77** | 3.29 | 3.0 |
| `--am-line-strong` on `--am-paper` | 1.4.11 | **1.92** | 3.56 | 3.0 |
| `--am-ink-soft` on `--am-surface` (hover border) | 1.4.11 | **2.91** | 5.04 | 3.0 |
| `--am-ink-soft` on `--am-paper` (hover border) | 1.4.11 | 3.14 | 5.45 | 3.0 |
| `--am-ink` on `--am-paper` | text | 17.63 | 17.63 | 4.5 |
| `--am-ink-muted` on `--am-paper` | text | 6.00 | 6.00 | 4.5 |
| `--am-ink-muted` on `--am-failed-light` | text | 5.11 | 5.11 | 4.5 |
| `--am-accent` on `--am-paper` | text | 8.24 | 8.24 | 4.5 |
| `--am-ok` on `--am-ok-light` | text | 5.58 | 5.58 | 4.5 |
| `--am-degraded` on `--am-degraded-light` | text | 5.20 | 5.20 | 4.5 |
| `--am-failed` on `--am-failed-light` | text | 6.57 | 6.57 | 4.5 |
| `--am-accent` on `--am-accent-light` | text | 7.07 | 7.07 | 4.5 |
| `--am-ink-inverse` on `--am-accent` | text | 8.24 | 8.24 | 4.5 |
| `--am-line` on `--am-surface` | 1.4.11 | **1.26** | **1.26** | 3.0 |

The three values that moved:

```
--am-ink-soft     #8a929d -> #646a73
--am-inert        #6b7280 -> #666c7a
--am-line-strong  #b4bcc7 -> #838891
```

---

## 3. What was changed, what was refused, and why

### 3.1 The third ink level is not viable at these surfaces, and this is the arithmetic

**The brief anticipated this case and asked for it to be said plainly. It is the case.**

AA 4.5 against the darkest surface `--am-ink-soft` carries text over — `--am-failed-light`,
L = 0.8449 — caps any foreground at **L ≤ 0.1489**. `--am-ink-muted` already sits at
**L = 0.1251**. The entire window in which a third ink level can be both compliant and
quieter than muted is therefore **1.14:1 wide**, and `--am-ink-soft` at `#646a73` spends it:

| | before | after |
|---|---|---|
| `ink` → `ink-muted` | 2.94:1 | 2.94:1 |
| `ink-muted` → `ink-soft` | **1.91:1** | **1.10:1** |

1.10:1 is not a step anyone can see at 13px. **Two tokens, two values, one visible level.**
The guard asserts both halves of that sentence — `soft !== muted`, *and*
`contrastRatio(soft, muted) < 1.3` — so a later wave that believes it has three ink levels
reddens rather than inheriting the belief.

**What would restore a real ladder, priced and not taken.** From `--am-ink` (L = 0.0095) to
the AA ceiling is 3.34:1 in total. Two even steps are 1.83:1 each, which puts
`--am-ink-muted` at **`#3f464e`** and leaves `--am-ink-soft` where it now is. That is a
legible three-level ladder and every level clears AA. It was **not done**, for one reason
stated rather than implied: it moves a token that *passes* (6.00 on paper) and redistributes
a scale `W31-STYLE` built two days ago. The brief's non-goals say "you are closing measured
failures, not redesigning", and this is a redesign. **It is one line and it is the
integrator's or the owner's call, not mine.** The arithmetic is here so the call can be made
without re-deriving it.

### 3.2 `--am-line-strong` is a component boundary, not decoration — the argument

The brief asked this to be argued before being changed. The argument is that the token has
two jobs and one of them is load-bearing:

- it is the **resting border of every `input`, `textarea` and `select`**, of
  `.am-button--quiet`, and of `input[type='file']::file-selector-button`. Every one of those
  controls is filled `--am-paper` on a `--am-paper` or `--am-surface` page — 1.00:1 and
  1.09:1 respectively. **The border is the only thing that says a control is there.** WCAG
  1.4.11 asks 3:1 of exactly that: "visual information required to identify user interface
  components". It was 1.92 on paper and 1.77 on surface;
- it is also a table rule, two left rails and a hover border, where it is decoration.

One token, both jobs, so the value must answer to the stricter one. Splitting it would mean
a new token *and* edits to the rules that read it, and this task may change neither. The cost
is that the decorative uses got heavier; that cost is named here rather than discovered.

The change is in the right direction for the scale as well: `line` → `line-strong` was
1.41:1 and is now **2.61:1**, so the three border levels are more distinguishable than
before, not less.

### 3.3 `--am-line` fails 1.4.11 at three interactive sites, and was left alone

Not in the brief. Found by the census, and it is the finding I am least comfortable leaving.

`--am-line` bounds three things that are genuinely interactive and whose fill does not
distinguish them from the page: **the finding row**, **the evidence page tabs**, and **the
page-action links**. At 1.26:1 on `--am-surface`, the extent of a finding row is invisible;
only its text says where it is.

Raising it to 3:1 needs L ≤ 0.2568 — `--am-line-strong`'s own territory. **A three-level
border scale cannot carry two levels at the 1.4.11 ceiling**, and raising `--am-line` would
darken every card, every table and every divider in the tree, which is precisely the visual
hierarchy the brief protects. So it is registered in the guard, with its reason, rather than
repaired or ignored. **Four register rows, one token, one decision.**

### 3.4 `::selection` makes a primary button's label vanish, and it is a rule, not a value

`::selection { background: var(--am-accent-light) }` sets no `color`, so selected text keeps
whatever colour it had. Over a `.am-button` that means `--am-ink-inverse` — white — on a pale
tint at **1.17:1**. Drag-select across a primary button and its label disappears.

It is real and it is **not a token value**: the repair is a `color` declaration on the
`::selection` rule, and this task may change values, not rules. Lightening or darkening
`--am-accent-light` is forbidden (it is a surface, and eight other rules use it). Registered,
and handed to the integrator.

### 3.5 What was deliberately not touched

- **No surface moved.** Not `--am-paper`, `--am-surface`, `--am-surface-sunken`, nor any
  `-light` tint. The brief's "darken the ink, do not lighten the surface" and its
  "do not touch `--am-evidence__object`'s white frame" are the **same constraint**:
  `.am-evidence__object` reads `var(--am-paper)` because it frames a genuine white PDF page,
  and `--am-paper` is untouched, so the rule is untouched by construction.
- **No rule, no selector, no consumer.** `git diff --stat cd475cc..HEAD` (§7) shows one
  source file changed and three test files added.
- **No new token.** §3.2 explains where one would have helped and why it is not this task's.

---

## 4. The guard, and its mutation red

`web/tests/unit/styles/contrast.test.ts`, 10 cases, beside `W31-STYLE`'s existing
`styling-layer.test.ts` (7 cases, untouched and still green).

### 4.1 What is derived and what is hand-maintained

`docs/program/W30-LISTS.md` closed eighteen instances of *a hand-maintained subset standing
in for a set something else decides, with nothing that fails when the authority grows*. A
list of "the pairs that matter" is that class exactly, so almost nothing here is a list:

| | where it comes from |
|---|---|
| the pairs | computed by `census()` from 30 rendered screens × the stylesheet, plus `declaredPairs()` |
| the threshold | a **function** of what the pair is: text → 4.5, meaningful graphic → 3.0, boundary → 3.0 **only if load-bearing** |
| "load-bearing" | derived from the **markup**: the element is operable (an interactive tag, a widget `role`, a `tabindex`) *and* its own fill does not already reach 3:1 against what is behind it |
| the exemption for disabled controls | WCAG 1.4.3 and 1.4.11 both except inactive components, so it is a clause in `thresholdFor`, not a row |
| **`REGISTERED`** | **the only hand-maintained set: 5 rows, each measured, below threshold, knowingly unrepaired, with its reason** |

And `REGISTERED` is held to the census **in both directions**: a registered pair the screens
no longer produce, *or* that now passes, is a failure — exactly as an unregistered failure
is. A stale exemption cannot sit here unnoticed and a new failure cannot hide behind one.
Mutation M4 proves that direction.

**Nothing asserts a ratio.** Every assertion is a relationship — this pair is at or above
its threshold; this token is below this derived ceiling; this separation is under 1.3. A test
saying `expect(ratio).toBe(4.62)` reddens on every correct change and teaches people to
update the number.

### 4.2 The mutations

Run in `/root/w32contrast-webmut`, a copy of `web/` outside the worktree with `node_modules`
symlinked, **baselined green (17/17) before any mutation** and confirmed green again after
every revert. No tracked file was edited to mutate anything.

#### M1 — `--am-ink-soft` `#646a73` → `#686e78`

Chosen so it still **passes** on `--am-paper` (5.13) and `--am-surface` (4.75) and fails only
where the tint comes from an **ancestor**. This is the mutation that proves the cascade
resolution is load-bearing rather than decoration.

```
 FAIL  tests/unit/styles/contrast.test.ts > every pair that meets on a screen clears the threshold its role asks of it > holds, and names the ratio of anything that does not
AssertionError: expected [ { …(4) }, { …(4) }, { …(4) }, …(2) ] to deeply equal []

- Expected
+ Received

- []
+ [
+   {
+     "needs": 4.5,
+     "pair": "text|--am-ink-soft|--am-failed-light|-|-",
+     "ratio": 4.38,
+     "where": "FindingList failed body > div.am-state.am-state--error > p.am-state__correlation",
+   },
+   {
+     "needs": 4.5,
+     "pair": "text|--am-ink-soft|--am-accent-light|-|selection",
+     "ratio": 4.4,
+     "where": "AppFrame body > div.am-app > footer.am-app__footer {::selection}",
+   },
+   {
+     "needs": 4.5,
+     "pair": "text|--am-ink-soft|--am-accent-light|-|-",
+     "ratio": 4.4,
+     "where": "FindingList selected li > button.am-finding-row.am-button > span.am-finding-row__pages",
+   },
...
      Tests  2 failed | 8 passed (10)
```

#### M2 — `--am-line-strong` back to `W31-STYLE`'s `#b4bcc7`

The exact defect this wave repaired, replayed.

```
   × every pair that meets on a screen clears the threshold its role asks of it > holds, and names the ratio of anything that does not
   × the repaired tokens say what they are for > the strong line clears 1.4.11 on every surface a control sits on

+     "needs": 3,
+     "pair": "edge|--am-line-strong|--am-surface|-|border",
+     "ratio": 1.77,
+     "where": "UploadPanel form > div.am-form > input",
+     "needs": 3,
+     "pair": "edge|--am-line-strong|--am-surface|-|file-selector-button",
+     "ratio": 1.77,
+     "where": "UploadPanel form > div.am-form > input {input[type='file']::file-selector-button}",
+     "needs": 3,
+     "pair": "graphic|--am-line-strong|--am-surface|-|before",
+     "ratio": 1.77,
      Tests  2 failed | 8 passed (10)
```

#### M3 — `--am-ink-soft` set equal to `--am-ink-muted`

The repair the brief forbids: two tokens with one value, called a fix.

```
 FAIL  tests/unit/styles/contrast.test.ts > the repaired tokens say what they are for > the third ink level is AA everywhere, and is no longer a level
AssertionError: expected '#5b6470' to not deeply equal '#5b6470'
 ❯ tests/unit/styles/contrast.test.ts:287:22
    285|     const muted = tokens.get('--am-ink-muted') as string;
    286|     // It is not `ink-muted` under another name: two tokens, two value…
    287|     expect(soft).not.toEqual(muted);
       |                      ^
      Tests  1 failed | 9 passed (10)
```

#### M4 — `--am-line` **repaired** to `#87898d` (3.24 on surface)

The direction that catches a stale exemption. Four register rows are no longer failures, so
the register is wrong and says so.

```
 FAIL  tests/unit/styles/contrast.test.ts > the register is held to the census in both directions > every registered pair is still produced and still below its threshold
AssertionError: expected [ …(4) ] to deeply equal []

- []
+ [
+   "edge|--am-line|--am-surface|-|border",
+   "edge|--am-line|--am-surface|hover|border",
+   "edge|--am-line|--am-surface|focus-visible|border",
+   "edge|--am-line|--am-surface|active|border",
+ ]
      Tests  1 failed | 9 passed (10)
```

#### M5 — `--am-ok` lightened to `#33ad73`

A **brand new** failure, on a token this wave never touched, in no register row.

```
+     "needs": 4.5,
+     "pair": "text|--am-ok|--am-ok-light|-|-",
+     "ratio": 2.45,
+     "where": "RunProgress published p._mode_5f66a5 > span.am-badge.am-badge--ok > span.am-badge__label",
+     "needs": 3,
+     "pair": "graphic|--am-ok|--am-surface|-|before",
+     "ratio": 2.64,
+     "where": "DecisionHistory section.am-history > ol.am-history__events > li.am-history__event {.am-history__event[data-verdict='accepted']::before}",
+     "needs": 4.5,
+     "pair": "text|--am-ok|--am-surface|-|-",
+     "ratio": 2.64,
+     "where": "ExportPanel exported body > section.am-export > p.am-export__last",
      Tests  1 failed | 9 passed (10)
```

**Every mutation reddened**, each on the test that should have caught it and not on the
others, and the copy returned to 17/17 after each revert. `W31-STYLE` reported a mutation
that reddened nothing and said so honestly; this wave has no such case to report.

---

## 5. The dark palette's price, and whether the guard extends

**This settles nothing.** Whether the alpha is dark by default is an open owner question
(`DEBT_REGISTER.md` §2) and nothing here touches it.

### 5.1 What the guard would need

| part | extends for free? | why |
|---|---|---|
| the census — rendering, the cascade, ancestor backgrounds | **yes, entirely** | it resolves backgrounds to token **names**, never to values. The pairs are the same pairs in any theme; only what they resolve to changes. This is the expensive half and it is theme-independent by construction. |
| `contrastRatio`, `relativeLuminance` | yes | arithmetic |
| `thresholdFor`, the load-bearing derivation | yes | reads the markup and the ratio between two token values, whatever those values are |
| `colourTokens()` | **no, ~10 lines** | it reads the **first `:root` block only**. A `[data-theme="dark"]` block is invisible to it. It must take a theme selector. |
| the assertions | **no, ~5 lines** | must loop over themes rather than read one token map |
| **`REGISTERED`** | **no, and this is the real cost** | it is **per-theme**, and the both-directions check makes that a hard failure rather than a quiet pass |

The last row is the one to plan for. `text\|--am-ink-inverse\|--am-accent-light\|-\|selection`
fails at 1.17:1 in light because white sits on a pale tint. In a dark theme
`--am-accent-light` is a *dark* tint and white on it very likely passes — so that row goes
**stale in dark and holds in light**, and the register must become
`Record<Theme, Registered[]>`. That is a design change, not a line count, and it is better
made when the second palette exists than guessed at now.

**Estimate: half a day for the machinery, and the register redesign is an hour.** The
expensive work is not the guard.

### 5.2 What the palette itself would cost, measured

`W31-STYLE` priced a second theme at **27 colour tokens to override and zero rule edits**.
That number is about *structure*. This is the number about *legibility*: every one of the 27
would have to be chosen against the measure rather than by eye, and **the ink ladder problem
recurs in mirror image**, because a dark theme has *less* room, not more.

How much room an ink ladder has above the AA floor, by surface (best achievable ink against
the surface, divided by the 4.5 floor):

| surface | L | best possible ink | room above AA |
|---|---|---|---|
| light: `--am-paper` `#ffffff` | 1.0000 | 21.00:1 | 4.67:1 |
| light: `--am-surface` `#f5f6f8` | 0.9210 | 19.42:1 | 4.32:1 |
| light: `--am-failed-light` `#fae9e9` | 0.8449 | 17.90:1 | **3.98:1** ← what this wave worked inside |
| dark: a near-black `#0b0d10` | 0.0040 | 19.46:1 | 4.32:1 |
| dark: `#16191d` (our `--am-ink`) | 0.0095 | 17.63:1 | 3.92:1 |
| dark: `#23282e` | 0.0207 | 14.85:1 | 3.30:1 |
| dark: `#2b3138` | 0.0300 | 13.13:1 | 2.92:1 |
| dark: `#343b43` | 0.0426 | 11.34:1 | **2.52:1** |

The counter-intuitive part, and the thing worth handing the owner: **a dark theme raises a
surface by lightening it**, so its *worst* text surface is its most elevated one — the mirror
of light theme, where the worst is the most tinted. A dark palette whose elevated cards sit
around `#2b3138`–`#343b43` has **2.5–2.9:1 of room** for its whole ink ladder, against light
theme's 3.98:1. **A three-level ink ladder is harder in dark, not easier**, and the same
collapse §3.1 documents would happen sooner. A dark palette that wants three ink levels must
keep its elevated surfaces near-black.

That is computed from first principles and needs no palette to exist. It is the one thing I
would want in the room when the owner takes the decision.

---

## 6. Every premise of this brief I measured and found false

### 6.1 The twelve ratios are right, and the twelfth is not a measurement

All eleven distinct figures reproduce to two decimals. But `ink-inverse on accent 8.24` and
`accent on paper 8.24` are the **same arithmetic**: `--am-ink-inverse` and `--am-paper` are
both `#ffffff`. Twelve figures, eleven pairs, ten independent numbers. Nothing turns on it;
it is recorded because a list that looks like twelve measurements and is ten is the shape
`OPERATING_CONSTRAINTS.md` §12 exists for.

### 6.2 **FALSE: the four failures are the failures.** They are four of nine

The brief named `ink-soft` on paper and surface, `inert` on `inert-light`, and `line-strong`
on paper. The census found **nine** text pairs below 4.5 and **eleven** 1.4.11 pairs below
3.0. The worst in the tree — `ink-soft` on `failed-light` at **2.68** — is not among the four,
and it is the one that matters most: it is the correlation id a reviewer reads off the
screen to report a failure.

### 6.3 **FALSE: `ink-soft` on `surface-sunken` is the pair to look for.** It is one of eight

The brief suggested `ink-soft` on `surface-sunken` as the shape of what might be missing. It
does occur, at 2.76. But the pattern is broader than one pair: **`--am-ink-soft` meets six
different backgrounds**, and every ink in the set meets between two and six. The ladder
metaphor in `globals.css` — ink on paper — is true of almost nothing on a real screen.

### 6.4 **FALSE: `--am-line-strong` is the border to argue about.** `--am-line` is worse

The brief asked me to argue whether `line-strong` is text or decoration. The answer is
neither — it is a component boundary, and §3.2 makes the case. But the census found that
**`--am-line`, which the brief does not mention, bounds three interactive controls at
1.26:1**, which is worse than anything `line-strong` was doing and is unrepairable without
collapsing the border scale. §3.3.

### 6.5 `:has()` is the only construct the matcher declines, and it costs nothing

`.am-quotation:has(.am-quotation__inconsistent)` sets `border-left-color: var(--am-degraded)`
on a card whose own child already declares the same colour, so the pair it would contribute
is in the census from the child. The guard asserts the declined list **equals** that one
selector, so a rule using a construct the matcher cannot read reddens rather than being
silently skipped. A skipped rule must never read as a passing one.

### 6.6 `.am-state--warning` is declared and nothing emits it

`globals.css` carries `.am-state--warning` and `.am-state--warning .am-state__title`. No
`.tsx` in `web/src` emits that class — `StateBlock` renders `am-state--${tone}` and the only
tones reached are `error` and `neutral`. This is the exact shape `W31-STYLE`'s own
`styling-layer.test.ts` case 2 exists for, one level up: not a selector that matches nothing,
but a **modifier class no component produces**. Reported, not changed — it is a rule, and
this task may not edit rules.

### 6.7 Two defects in my own machinery, found by reading its output rather than trusting it

Both are the brief's own method rules, and both cost real time:

- **"any `role` means a user interface component" is wrong.** The only roles in this tree are
  `alert`, `note` and `status` — a live region and two document roles, not a control among
  them. Accepting them made the guard demand 1.4.11 of a failure card's border, which WCAG
  does not. Fixed to widget roles.
- **Deduplicating a pair by key kept the FIRST site's classification.** `--am-line` on
  `--am-surface` occurs at forty decorative card edges and at *one* interactive page-action
  link. Keeping the first made the verdict depend on the order screens happen to render in,
  and it silently exempted the only site that mattered. It now merges to the **strictest**
  site. *Measure across every site that can produce the behaviour, not the first one that
  explains it* — the rule was in the brief and I broke it anyway; the output is what caught
  it.

Two more, smaller, in the same class: a fragment render has no `<body>`, so every element
whose ancestors declared no background resolved to its **own** and a primary button reported
its border against its own fill at 1.00:1; and applying one stateful rule on top of the
resting cascade invented `ink-muted on accent-strong` at 1.91, a pair no browser paints,
because `.am-evidence__pages .am-button:hover` beats `.am-button:hover` on specificity. Both
fixed before any token moved, which is why the census in §1 is a measurement of what
`W31-STYLE` left rather than of what this wave did.

---

## 7. Files changed, and the forbidden hotspots

```
 docs/program/W32-CONTRAST.md            | new
 web/src/app/globals.css                 | 3 token values + the comments that justify them
 web/tests/unit/styles/contrast.ts       | new — formula, parsers, cascade, threshold rule
 web/tests/unit/styles/contrast.test.ts  | new — the guard, 10 cases
 web/tests/unit/styles/screens.ts        | new — 30 rendered screens
```

Nothing under `web/src` but `app/globals.css`. No `.module.css`. No `contracts/**`, `src/**`,
`db/**`, `infra/**`. `web/FRONTEND_LOCK.json`, `package.json` and both lockfiles untouched —
no dependency was added, and none could have been.

## 8. Rollback

`git revert` the token commit. The three values return to `W31-STYLE`'s and the guard
reddens with the four pairs §2 lists, which is the correct behaviour: the guard is not
coupled to the repair, it is coupled to the measure.

