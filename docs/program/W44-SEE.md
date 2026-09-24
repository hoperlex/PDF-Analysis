# W44-SEE — derive the subject from the tree, and repair what that makes visible

**task_id:** `W44-SEE` · **wave:** 44, sub-stage A · **lane:** `gate-w44b`
**worktree:** `/root/w44see` · **branch:** `agent/w44-see` · **base:** `843082f`

Opened before the first measurement. Every figure carries the command that produced it and
the commit the tree was at.

## 0. The measurement wave 43 took, reproduced at this wave's base

Provisioned first: `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` → `bootstrap OK`;
`.venv/bin/python -c "import boto3"` → `boto3 1.43.90`; `npm --prefix web ci` → 184 packages.

**Baseline, at `386130e`** (the base tree plus this file): `npm --prefix web test` →
**75 files, 1085 tests, 0 failed**; `npm --prefix web run typecheck` clean. That is wave
43's figure to the test.

**Wave 43's probe, verbatim, applied to the base tree.** English prose on a screen — four
screens, four different sentences, so no single guard's mask could hide the result — and a
border under `R-33`'s 3:1 floor on a really-rendered element: a `blocks-page.module.css`
declaring `border: 1px solid var(--am-paper)` on a `div` `BlocksPage` really renders, which
the census measures at **1.08:1** in the light palette and 1.11:1 in the dark.

Result at `386130e`: **1 failed | 1084 passed (1085)**. The language guard was green over
four entirely English screens. `R-33`'s floor was green over a border at 1.08:1. The one
red was the census's *unreached rule* case, and **what it said was false**:

```
FAIL tests/unit/styles/contrast.test.ts > names every colour-bearing rule that NO rendered screen reaches
  these rules declare a colour and NO screen in `screens.ts` renders an element they match,
  so their contrast is not measured by anything.
  expected [ '._frame_d22d03' ] to deeply equal []
```

`BlocksPage` renders that element. `screens.ts` did not render `BlocksPage`. The message
named a bundler hash and not the screen. That is `D-88`'s first defect, at the tip of wave
43's work.

## 1. `S1` — `D-88`: the screen set, derived from the route tree

`web/tests/unit/screens/route-screens.ts` walks `web/src/app` for `page.tsx` the way
`tests/e2e/test_pc01_journey_conformance.py` already does with `rglob`, and both frontend
instruments consume it. `web/tests/guards/screen-set.guard.test.ts` holds the join.

**The hard part was not the glob.** Three things stood between an address and a render:

1. **A route file is not a component this harness can render.** Every `page.tsx` under a
   dynamic segment is an `async` server component whose `params` arrive as a promise, and
   `renderToStaticMarkup` cannot render one. A seed therefore names the `_pages` slice the
   route delegates to — which is also what a reviewer reads — and `routes.test.ts` holds
   the delegation itself.
2. **Identifiers.** `make` receives the segment values **by segment name** (`project_uid`,
   `run_id`) — the names the directory layout already carries — so a seed cannot pass a run
   id where a version uid belongs.
3. **Cache state.** Every seed is state-free and returns the element; the caller decides
   the client. The sixteen-state matrix stays in the language guard and the populated
   clients stay in the census, so the derivation does not duplicate either.

**How a screen opts out.** By an entry in `SEEDS` carrying `optOut` instead of `make`, with
(a) a reason of at least 80 characters, (b) a **`proof`** — a predicate over the route
file's own source — which the guard **runs**, so a claim that stops holding is red rather
than silent, and (c) it is still counted: the derived count is asserted as *every address
minus the excused*, so nothing leaves the census by being excused.

**A `try`/`catch` around a render is not an opt-out and must never become one.** It states
no reason, nothing checks it, and it turns a screen that throws — a defect — into a screen
that is merely absent, which is `D-88` itself. That sentence is in the file so the next
reader has to argue against it rather than merely notice an absence.

Wave 41's rule, unchanged: **coverage is derived from the contract; the seeds are not. The
question is derived; a human answers it.**

### The plain count

`web/src/app` carries **15 `page.tsx` files**. **14 render; 1 opts out.**

| address | in the derived set |
|---|---|
| `/` | **opt-out** — `redirect('/projects')` throws before any element exists |
| `/account/password`, `/blocks`, `/knowledge-base`, `/login`, `/logs`, `/optimisation`, `/projects`, `/workers` | yes |
| `/projects/[project_uid]` | yes |
| `/projects/[project_uid]/documents/[document_uid]` | yes |
| `/projects/[project_uid]/runs/[run_id]` | yes |
| `/projects/[project_uid]/runs/[run_id]/review` | yes |
| `/projects/[project_uid]/versions/[version_uid]` | yes |
| `/projects/[project_uid]/versions/[version_uid]/comparison` | yes |

**Nothing is missing.** Four addresses — `/blocks`, `/logs`, `/optimisation`, `/workers` —
were rendered by **neither** instrument before this wave. `/` is the one opt-out and it is
checked, not assumed. Eleven **(screen, dynamic segment)** refusal shapes are now derived
where three were hand-written.

`app/not-found.tsx` and `AppFrame` are not addresses and stay hand-written entries, each
saying so.

### The probe, driven and red, at `46f8f92`

The same probe, unchanged:

```
Test Files  2 failed | 74 passed (76)
     Tests  4 failed | 1092 passed (1096)
```

```
FAIL tests/guards/rendered-language.guard.test.ts > R-18: no Latin word reaches a reviewer …
  expected [
    "\"Here you will be able to read the execution journal of a run, …\"  … [logs]",
    "\"The executors of this system will be listed here, …\"           … [workers]",
    "\"This is where the tuning of the analysis will live, …\"         … [optimisation]",
    "\"This section will show the block markup of the page, …\"        … [blocks]",
  ] to deeply equal []
```

```
FAIL tests/unit/styles/contrast.test.ts > R-33: every border that meets on a screen clears 3:1 …
  expected [
    { "needs": 3, "pair": "edge|--am-paper|--am-surface|-|border", "ratio": 1.08,
      "theme": "light", "where": "blocks cold html > body > div._frame_d22d03" },
    { … "theme": "dark", "where": "blocks cold html > body > div._frame_d22d03" },
  ] to deeply equal []
```

Both redden, and both name the screen: `[blocks]`, `[logs]`, `[optimisation]`, `[workers]`
by name, and `blocks cold …` as the site of the border. The probe was reverted; the tree
carries none of it.

## 2. `S2` — `D-82`: the three English `LoadingState` arguments

`S1` did **not** make those branches reachable, and the reason is worth recording because
the row's own wording invited the opposite guess. They are selected by a settled
`useMutation`, and `useMutation` — unlike `useQuery` — **builds its own observer and reads
no cache**, so there is nothing a harness can seed. No screen set, however derived, reaches
them in one static pass.

So the row got what it asked for: **an instrument, not an edit.**

`UNREACHABLE_IN_ONE_PASS` excused these branches from the **coverage** assertion, and that
was read as excusing them from `R-18` as well. It never did. Two new cases in
`rendered-language.guard.test.ts`:

- **`D-82: no branch label carries English, reachable or not`** — judges every label
  `branchLabelsInSource()` derives from `web/src`, excused or not, with the same
  `unexplainedLatin` the rendered half uses.
- **`proves its composition against the screens that DO render a loading label`** — the
  scan composes `Загрузка: ${what}…` the way `LoadingState` does, and that composition is a
  claim about the subject, which is `OPERATING_CONSTRAINTS.md` §12 waiting to happen. It is
  proved, not assumed: at least four composed labels must appear **verbatim** in rendered
  text, and a deliberately broken formula must not.

Committed **red** at `b67e672`, naming all three and their modules, then repaired at
`73f3578`:

| was | is |
|---|---|
| `the new project` | `новый проект` |
| `the upload` | `загружаемый файл` |
| `the run request` | `запрос на прогон` |

**Regression shown.** A fourth English argument — `what="the fourth one"`, in a branch
nothing renders — reddens three cases and names the module:

```
"\"Загрузка: the fourth one…\"  the fourth one  (web/src/features/create-project/ui/create-project-form.tsx)"
```

**What the instrument cannot do**, stated rather than left to look like coverage: it judges
the words in an argument that reaches a mandatory state. It does not render the branch, so
a sentence composed some other way is outside it. It is the half of the matrix's subject
that one static pass cannot select, judged by the only means available.

## 3. `S3` — `D-95`: gender agreement

`web/tests/guards/gender-agreement.guard.test.ts`, committed **red** at `866d4af`,
repaired at `7c5ce9b`. Two halves, because the class has two.

**The mechanism.** A gendered word written next to a substitution is a bet that every value
the substitution can take has that gender. `web/src` is scanned for one, and a hit is red.
The repair makes the determiner travel with the noun:

```ts
const PARENT_GENITIVE: Readonly<Record<ListingParent, ParentNoun>> = {
  project:  { genitive: 'проекта',  noSuch: 'Такого', thisOne: 'этого' },
  document: { genitive: 'документа', noSuch: 'Такого', thisOne: 'этого' },
  version:  { genitive: 'версии',   noSuch: 'Такой',  thisOne: 'этой'  },
};
```

so agreement is data, the compiler refuses a fourth parent that leaves a form out, and the
scanned pattern is simply absent.

**The output.** Every sentence `classifyListingFailure` can produce — `ListingParent` read
out of the module's own source, `ErrorCode` out of `contracts/api/v1/openapi.json`, 66
sentences — plus the prose of every derived screen and every refusal shape.

**What the morphological rule decides, and what it does not.** One axis, and it is the axis
this mechanism gets wrong: after a genitive determiner, `-и/-ы` is feminine and `-а/-я` is
masculine or neuter. Anything else is **unjudged**, counted, and the judged ratio is
asserted — so a rule that quietly starts declining everything is red rather than green. The
`-мя` heteroclitics (`времени`, `имени`, …) are the known exception; their absence **from
the position the rule reads** is asserted.

Two findings from building it, both recorded in the file:

- **The scan's first run reddened on the doc comment of the module it had just repaired**,
  because that comment quotes the defect. It now strips comments, with an assertion in both
  directions. `D-83` recorded the same shape from the other side.
- **The heteroclitic check was first written over the whole corpus and went red on
  `пара имени и пароля`** — an ordinary genitive in the sign-in screen's prose that no
  determiner precedes and that the rule never looks at. A check that fails on text it does
  not judge teaches the next reader to weaken it.

**Mutations driven.** Restoring the masculine forms in the table reddens the classifier
case naming both sentences verbatim; writing a determiner beside a `${…}` again reddens the
mechanism case naming the line.

## 4. `S4` — `D-90` and `D-94`: live conditions nothing asserts

**`D-90`.** `screen-set.guard.test.ts` derives one `(screen, dynamic segment)` pair per
`[segment]` in the directory layout — eleven — and each seed **answers** what its screen
does with a malformed value: `refuses` or `defers-to-route`. Both directions are asserted
by rendering.

The split is the whole point and it is `OPERATING_CONSTRAINTS.md` §12: **a guard that
recovered the expectation by scanning the component for `looksLike…(` would go green on the
mutation it exists to catch**, because deleting the call deletes the scan's evidence with
it. The answer is a human's, in `SEEDS`, so it survives.

The register's own mutation — delete the `looksLikeProjectUid` call, keep the import used —
now gives a clean `tsc` and:

```
FAIL tests/guards/screen-set.guard.test.ts > D-90: every dynamic segment says what its screen does …
  expected [ "stage-comparison (project_uid malformed): seed says refuses" ] to deeply equal []
```

The red is about the condition and names the screen and the segment. The premise was
verified at the base commit: `stage-comparison.test.ts` renders the page only ever with a
well-formed `PROJECT_UID`, so nothing asserted that check.

**The run and the review screens legitimately check nothing of their own** — their route
files call `notFound()` first — and that is now *declared* rather than accidental, so a
check added to either of them without a decision is red too.

**`D-94`.** The hand-written list of six `{url, file}` pairs in `routes.test.ts` is gone.
Every builder `routes` exports is **called**, with a sentinel per parameter position, and:

- the address it produces must be one `web/src/app` serves;
- every address with a dynamic segment must be produced by some builder;
- every address a builder builds must be drawn as an `href` by some screen the contrast
  census renders.

The third reads `tests/unit/styles/screens.ts`, which is a module and not a suite, so it
runs nothing twice — and it is the **loaded** states that make it work: the document link
and the review link are drawn only once a query has answered, so a check over cold renders
alone would have been green with both deleted.

Both of the register's mutations driven:

| mutation | result |
|---|---|
| `routes.comparison` → `/compare` | 2 cases red, naming `routes.comparison() -> /compare` **and** the address left unbuilt |
| delete the comparison `<p>` from `version-detail-page.tsx` | 1 case red, naming the full address |

## 5. Premises in the brief that are false

1. **«The same substitution mechanism is in `upload-failure.ts`, `run-failure.ts` and
   `catalog-message.ts`.»** **False.** None of the three substitutes a noun into a gendered
   template. Their sentences are fixed literals with the determiner already agreeing —
   `'Такого прогона или версии не существует.'`, `'Такого проекта не существует.'` — and
   `catalog-message.ts` has no parameterised noun at all.
   `grep -rnE "(такого|такой|этого|этой|…)\s+\$\{" web/src` returns **two** hits at the
   base commit, both in `listing-failure.ts`. The three modules are also not where the
   brief puts them: they are `web/src/entities/audit-run/model/run-failure.ts`,
   `web/src/entities/document-version/model/upload-failure.ts` and
   `web/src/shared/api/catalog-message.ts`. **The class is real and the class is one module
   wide today** — which is why the repair is a scan over all of `web/src` rather than three
   edits.
2. **«`rendered-language.guard.test.ts:795`, `const SCREENS = [...]`.»** It is line **892**
   at `843082f`. The row's line number predates wave 43's additions to the file.
3. **«the fourteen addresses `web/src/app` offers».** `web/src/app` carries **fifteen**
   `page.tsx`. Fourteen render; the fifteenth, `/`, is a redirect that renders nothing. The
   brief's fourteen is the right number for *screens* and the wrong number for *addresses*,
   and the difference is exactly the opt-out this task had to design — so it is reported
   rather than quietly reconciled.

Premises checked and **true**: the lane's ports in `.env` (`gate-w44b`, PostgreSQL 56300,
S3 59900/59901); wave 43's frontend figure (75 files, 1085 tests, measured); the `SCREENS`
literal and the hand-written import list; `listing-failure.ts:108` as the substitution site;
`D-90`'s condition unasserted at the base commit.

## 6. Outside the grant: reported, not repaired

1. **`web/tests/unit/screens/stage-comparison.test.ts` renders the page with a malformed
   *version* uid and never a malformed *project* uid.** It is inside my grant and is now
   covered by the derived pairs, so nothing is owed — recorded because it is the file a
   reader would expect `D-90` to have been caught in.
2. **`docs/program/DEBT_REGISTER.md` is a forbidden hotspot**, so `D-82`, `D-88`, `D-90`,
   `D-94` and `D-95` are **not** marked closed. The integrator owns those rows.
3. **`tests/e2e/pc01/journey/manifest.json` needs no amendment from this stream.** This
   wave adds no screen to `web/src/app`, so `D-89`'s hotspot is untouched by `W44-SEE`.
4. **The contrast census still excuses seven selectors as unreachable by a server render
   pass.** Unchanged by this wave, and each still carries its reason.

## 7. Risks and known limitations

1. **The derived set renders one cold pass per screen inside `screen-set.guard.test.ts` and
   sixteen cache states per screen inside the language guard.** Four screens joined the
   matrix, so the language guard's render count rose from 385 to 411. The three
   `*-bad-address` entries that used to be multiplied by all sixteen states are now appended
   once each, which is why the increase is smaller than the screen count suggests.
2. **A route group (`(name)`) or a parallel route (`@slot`) would come through the
   derivation with its bracket in the address.** It would then match no seed and be **named**
   by the guard, which is the intended outcome for anything the derivation has not been
   taught — but it is a red somebody will have to read rather than a silent pass.
3. **The gender rule decides one axis.** It cannot see an adjective that disagrees, a plural
   that disagrees, or a case error. It sees the determiner-next-to-noun disagreement that
   this substitution mechanism produces, and the mechanism half prevents the mechanism.
4. **`MALFORMED_SEGMENT` is Cyrillic (`это-не-идентификатор`) and that is load-bearing.**
   The hand-written entries it replaces used the Latin `not-an-identifier`, which was
   invisible only because the three screens that used it all refuse and never echo the
   value. The run and review screens do echo it, and the first run of the derived variants
   reported it as English on a rendered screen. The guard was right and the seed was wrong.
5. **The machine was under heavy contention while this was measured** — `load average
   24.8` with three sibling lanes live. Two runs of the identical tree took 69.5s and
   36.5s. `OPERATING_CONSTRAINTS.md` §4.6: a slow run is evidence about the machine.
