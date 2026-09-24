# W43-JUDGE-B — the stage-B judge, on the merged and gated tree

**task_id:** `W43-JUDGE-B` · **wave:** 43, stage B · **lane:** `gate-w43j`
**worktree:** `/root/w43judge` · **branch:** `agent/w43-judge-b` · **base:** `c455848` (`alpha-w43`)

**This branch repairs nothing.** Its diff against `c455848` is this file and nothing else;
`git diff --name-only c455848 agent/w43-judge-b` is quoted in §8. Every probe below was applied
to `web/src`, measured, reverted with `git checkout -- web/src`, and `git status --porcelain`
was confirmed empty after each.

**Where the measurements come from.** `make gate` was **not** re-run: the integrator ran it on
this tree and §12 says a second run of the same command is not an independent check. What is
independent here is the product — the deployed stand was driven in a real browser, through the
application's own controls, and every figure below that concerns behaviour was read off that
stand rather than off a harness. Containers: `gate-w43j*` only; `auditmanager-w19a` was driven
over HTTP and never restarted, reconfigured or inspected with `docker exec` beyond what
`verify-deployed.sh` does itself.

## 1. Findings, most severe first

| # | finding | question | reproduction |
|---|---|---|---|
| **F1** | **Wave 43 put a horizontal scrollbar on every screen in the product below 839 CSS px.** The four new navigation links widen the frame past the viewport; the overflow threshold moves from **482 px to 839 px**, which puts a small laptop and every tablet inside the broken band. `W43-PREP` disclosed the risk and nobody measured it. | K2 | §3.1 |
| **F2** | **The browser journey cannot run at all, and has not been able to since wave 34.** It stops at route **2 of 15** on the deployed stand. Every route gets a cold browser with no cookies, the BFF answers `401` without a session, and neither the manifest nor `write.mjs` can sign in. **The five rows wave 43 added to `manifest.json` have never been walked and cannot be.** | K2 | §3.2 |
| **F3** | **`routes.comparison()` is asserted by nothing.** Pointing it at an address that does not exist leaves the whole suite green — 75 files, 1085 tests, 0 failed. Integrator's own unreviewed change. | K1, K4 | §5.1 |
| **F4** | **The only navigation link to this wave's flagship screen is asserted by nothing.** Deleting it outright leaves the suite green. `W43-PREP`'s four links *are* guarded (`P4`); the comparison link is not. Integrator's own unreviewed change. | K2, K4 | §5.2 |
| **F5** | **Broken Russian on a reviewer's screen, reachable only through the new address**: *«Такого версии не существует.»* / *«На сервере нет этого версии…»*. A feminine genitive noun is interpolated into a masculine template. The language guard cannot see it — it looks for Latin words, and this is Russian, only wrong. | K3 | §4.3 |
| **F6** | **`W43-JUDGE-A`'s `F4` survived the merge unrecorded and unrepaired.** `docs/program/W43-PREP.md:174` still says *"Two modules call `logging.getLogger`"*; **three** do. It is the one false statement in the notes the next wave is meant to budget against, and it is the only stage-A finding that got no `DEBT_REGISTER.md` row. | K4 | §6 |
| **F7** | *(observation)* The comparison link is offered on a version with fewer than two runs, and in the version's own error state. On the stand it leads to a screen whose only content is *«Для сравнения нужны два прогона этой версии.»* | K3 | §4.2 |

**F1 and F2 are one story told twice.** The wave's visible defect is a layout regression that no
test in this repository can see, and the one instrument that could have seen it is an instrument
that no longer runs. `D-88` says the frontend guards take their subject from a literal; F2 says
the guard that takes its subject from the tree — and that was the hero of stage A — is a
*gate-time* reader of a manifest whose *run-time* half has been dead for nine waves. **The wave
closed on a green gate, a green frontend battery and a conformance guard that all agree, and
none of the three has ever rendered a box.**

## 2. K1 — did the merge lose anything? **No. Nothing, and I can name what is present.**

The arithmetic `W43-JUDGE-A` handed me is **1032 + 15 + 38 = 1085 in 75 files**, with the warning
that a renamed or substituted test satisfies it too. So the count was not the check.

### 2.1 The check that a count cannot fail: every stream file survived byte-for-byte

```bash
cd /root/w43judge
for f in $(git diff --name-only b7d9bc4 1579738); do git diff --quiet 1579738 c455848 -- "$f" || echo "DIFFERS: $f"; done   # (no output)
for f in $(git diff --name-only b7d9bc4 37a6bc2); do git diff --quiet 37a6bc2 c455848 -- "$f" || echo "DIFFERS: $f"; done   # (no output)
```

**Every one of the 14 files `W43-COMPARE` touched and the 16 files `W43-PREP` touched is
identical in the merged tree to the branch that wrote it.** No pre-existing test file was
deleted. Three existing test files were modified, all by `W43-COMPARE`, and the diffs are
`+122/-1`, `+41/-0` and `+67/-0` — the single removed line is `: loaded(overrides ?? {});`
inside a helper, not a case.

### 2.2 And the check that names what is present: the test *name sets*, not the totals

Four runs of the frontend suite with `--reporter=json`, in this lane, one tree at a time:

| tree | tests | failed | files | unique `(file, fullName)` |
|---|---|---|---|---|
| `b7d9bc4` (base, `alpha-w42`) | **1032** | 0 | 72 | 1028 |
| `37a6bc2` (`w43-prep`) | **1047** | 0 | 73 | 1043 |
| `1579738` (`w43-compare`) | **1070** | 0 | 74 | 1066 |
| **`c455848` (merged)** | **1085** | 0 | **75** | **1081** |

```
base names missing from merged        : 0
prep-added names missing from merged  : 0
compare-added names missing from merged: 0
in merged but in NO source set        : []
in union but not merged               : []
base files missing from merged        : []
```

**The merged set is exactly `base ∪ prep-added ∪ compare-added`, with nothing extra and nothing
absent.** Not a coincidence of totals: 1081 named pairs on both sides. The 4-test gap between
1085 and 1081 is one parametrised case in `routes.test.ts` whose reported name is truncated
identically five times; it is present at the base too.

`+1` file is `prepared-sections.guard.test.ts`; `+2` are `run-comparison.test.ts` and
`stage-comparison.test.ts`. **No test was lost, renamed or substituted by the merge.**

## 3. K2 — does the browser journey still pass? **It cannot run. I drove the product instead.**

### 3.1 F1 — the frame now overflows the viewport, and the four new links are why

Driven on the stand, in Chromium, through the repository's own `withColdBrowser`. The viewport
is set with the harness's own `Emulation` override; the four wave-43 links are then removed from
the live DOM and the document re-measured in the same page. **Nothing on disk is touched.**

```
viewport  with wave 43's links      without the four
1440      scroll=1440  no overflow  scroll=1440  no overflow
1200      scroll=1200  no overflow  scroll=1200  no overflow
1024      scroll=1024  no overflow  scroll=1024  no overflow
 900      scroll= 900  no overflow  scroll= 900  no overflow
 820      scroll= 839  OVERFLOW     scroll= 820  no overflow
 780      scroll= 839  OVERFLOW     scroll= 780  no overflow
 600      scroll= 839  OVERFLOW     scroll= 600  no overflow
 375      scroll= 839  OVERFLOW     scroll= 482  OVERFLOW
```

**The frame's intrinsic width went from 482 px to 839 px.** Below 839 the whole application —
every screen, not only the five new ones, because `AppFrame` is global — scrolls sideways. The
default viewport of the journey's own browser on this host is **780**, which is inside the band.

```bash
node - <<'JS'
import { withColdBrowser } from '/root/w43judge/tests/e2e/pc01/journey/cdp.mjs';
await withColdBrowser(async (page) => {
  await page.goto('http://127.0.0.1:31500/projects');
  const M = `({ inner: window.innerWidth, scroll: document.documentElement.scrollWidth })`;
  console.log('with   :', await page.evaluate(`(${M})`));
  await page.evaluate(`(() => { for (const a of [...document.querySelectorAll('header a')])
    if (['/blocks','/optimisation','/logs','/workers'].includes(a.getAttribute('href'))) a.remove(); return null; })()`);
  console.log('without:', await page.evaluate(`(${M})`));
});
JS
# with   : { inner: 780, scroll: 839 }
# without: { inner: 780, scroll: 765 }
```

**`W43-PREP` disclosed exactly this and could not repair it** — *"six links plus the right-hand
cluster will overflow the bar on a narrow viewport, and the repair is one `flex-wrap: wrap` in a
file it does not own"* — and `W43-JUDGE-A` recorded the disclosure as a credit. **Nobody
measured it, and the number is the part that decides whether it ships.** `globals.css` already
carries `@media (max-width: 900px)` blocks, so the breakpoint the repair belongs at exists.

**Why no instrument saw it.** The frontend battery renders through `renderToStaticMarkup`: there
is no layout, no box and no viewport, so a width is not a thing it can have an opinion about.
The contrast census reads colours. The journey would have seen it and does not run (F2).

### 3.2 F2 — the journey stops at route 2 of 15, and cannot be made to finish

```bash
npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:31500 --phase all
```

```
write half: 3 step(s), fixture fixtures/synthetic/ar/ar_baseline.pdf
RED create-project   api=2
ok  root       200  api=1 auth=0 console=0
RED projects   200  api=1 auth=0 console=0
write steps checked: 1/3
routes checked: 2/15
e2e:pc01 FAILED -- 9 finding(s):
  - create-project: createProject answered 401 Unauthorized and this step declares 201
  - create-project: POST /bff/v1/projects answered 401 ... "error_code":"authentication_required"
  - projects: rendered no link matching ^/projects/(prj_%ID%)$ so the journey cannot reach project_uid
  - only 2 of 15 routes were reached; an unfinished walk is not a pass
```

**This is not a wave-43 defect and it is not a defect of the stand.** It is structural, and the
three facts that make it so are all in the tree:

1. `web/src/app/bff/v1/[...path]/route.ts` — *"**no session cookie** — NOTHING. This route
   answers `401` locally and forwards no credential at all."* Correct, deliberate, and wave 34's.
2. `cdp.mjs` exposes `withColdBrowser` **and nothing else**, by design (`D-16`): every route is a
   new browser process with a throwaway profile — no cookies, ever.
3. The manifest has no sign-in step and `write.mjs` knows three verbs — `fill`, `click`,
   `attach_file`. There is nothing that could sign in even if a warm browser existed.

So the journey was written for an application without authorization, and the application grew
authorization nine waves ago. `grep -rn "cookie" tests/e2e/pc01/journey/*.mjs` returns two
comments and no code.

**The stand is not empty and that is the point.** With a session established by hand, the same
origin lists **sixteen projects**, with documents, versions and runs under them:

```bash
curl -s -c c.txt -X POST http://127.0.0.1:31500/bff/v1/session -d 'login=admin&password=password'  # 303, sets am_session
curl -s -b c.txt http://127.0.0.1:31500/bff/v1/projects                                            # 200, items: [...]
```

The walk does not fail for lack of data. It fails because it cannot hold a session.

**What this costs wave 43 specifically.** `tests/e2e/test_pc01_journey_conformance.py` — the one
instrument stage A found that derives its subject from the tree — is a **gate-time reader of the
manifest**. It asserts that each `page_module` exists, that the dynamic segments match, and that
each `(method, path, operationId)` is a real contract operation. It cannot assert that the screen
answers, renders, or makes the call. The comparison row's `expects_api` claim — *"the screen
calls `listRuns` on mount in EVERY state it has"* — is therefore verified by nothing that runs.
**I verified it by hand instead, and it is true** (§4.2). `D-83` already says eleven journey
sentences are verified only by `refusals.mjs` *against a live stand*; F2 is that the live-stand
half cannot run either, which is wider than the row as written.

### 3.3 So I drove the five addresses myself, and said how

`tests/e2e/pc01/journey/cdp.mjs`, imported from the scratchpad, one cold browser per address,
signed in through the application's own `/login` form before navigating. Recorded per address:
the document chain and status, `document.title`, `document.body.innerText`, every `<a href>`,
every `/bff/v1` exchange with its status, console errors, uncaught exceptions, every Latin word
in the visible text, and every rendered border's contrast against the surface behind it in both
palettes. Results in §4.

## 4. K3 — are the five new addresses real on the deployed stand?

### 4.1 The stand is this tree, checked here and not taken

```bash
cd /root/w43judge
bash infra/deploy/verify-deployed.sh --repo /root/w43judge \
  --env-file /root/projects/PDF-Analysis/infra/deploy/env/alpha.env      # exit 0
```

```
instance auditmanager-w19a · repository /root/w43judge at c455848 · proxy http://127.0.0.1:31500
  401 on /api/v1/openapi.json -- the API answered and D-73 is closed here
  src/ 164 identical · db/ 14 · contracts/ 34 · fixtures/recorded/ 7 · web/ 305 identical
verify-deployed.sh: the deployed stack IS this tree (c455848).
```

The env file is git-ignored and lives in the original clone; `--repo` points the comparison at
this worktree, which is `c455848` and clean. **The integrator's `differences: 0` reproduces.**

### 4.2 Every address answers, and the identifier guard is real

| address | document | API calls the browser made | console / page errors |
|---|---|---|---|
| `/blocks` | **200** | none | 0 / 0 |
| `/optimisation` | **200** | none | 0 / 0 |
| `/logs` | **200** | none | 0 / 0 |
| `/workers` | **200** | none | 0 / 0 |
| `…/{prj}/versions/{ver}/comparison` (real pair) | **200** | `GET /bff/v1/versions/{ver}/runs → 200` | 0 / 0 |
| same, well-formed but absent version | **200** | `GET /bff/v1/versions/{ver}/runs → 404` | 0 / 0 |
| `/projects/notaprj/versions/notaver/comparison` | **404** | **none — no request was sent** | 0 / 0 |

**The integrator's probes reproduce**, and the malformed case is stronger than a status code
says: the browser made *no* API call at all, and the 404 screen says so — *«запрос не
отправлялся — это не сообщение о том, что сервер чего-то не нашёл»*.

**The manifest's `expects_api` claim for the comparison row is true, driven.** `listRuns` is
called on mount; the four prepared screens call nothing, which is what their `expects_api: []`
claims. This is the assertion F2 says no runnable instrument makes.

**The four prepared screens' `expects_api: []` is the strongest row in the manifest and the
weakest claim**: a screen that calls nothing cannot fail that assertion, and the rows say so
themselves. That is honest and it is also why the manifest addition costs nothing to be right.

**F7.** No version on the stand has two runs, so the populated comparison table could not be
reached. The real pair renders the one-run state: *«Для сравнения нужны два прогона этой
версии.»* — correct, and reached from a link on the version screen that is offered unconditionally,
including when the version itself failed to load.

### 4.3 Do they render in Russian? Four yes, one with a defect the guard cannot see

Every Latin word in the visible text of each new screen, taken from the rendered DOM:

```
/blocks /optimisation /logs /workers : AuditManager · alpha · w19
…/comparison (real pair)             : AuditManager · alpha · w19 · ver_01M34RWZ29KMC4F60RSS5YH0N3
```

The brand, the instance label `ALPHA-W19`, and a contract identifier. Nothing else. **`R-18`
holds on all five as rendered on the stand.**

**F5 is the exception, and it is Russian rather than English, which is why nothing caught it.**
On the well-formed-but-absent version the comparison screen renders:

```
Такого версии не существует.
На сервере нет этого версии, поэтому перечислять здесь нечего.
```

`web/src/shared/lib/listing-failure.ts:108-110` builds these from `PARENT_GENITIVE`, which maps
`version → 'версии'` — a feminine genitive — into templates written for `проекта` and
`документа`: `` `Такого ${parent} не существует.` `` and `` `На сервере нет этого ${parent}…` ``.
It should read *«Такой версии не существует»* / *«нет этой версии»*.

The module is **pre-existing** and `run-list.tsx` already passes `parent: 'version'`, so this is
not wave 43's doing — but the comparison screen is a second site for it, and the wave is when it
was first read by anybody. **The language guard is structurally unable to find it**: it asserts
that no Latin word reaches a reviewer, and every word here is Cyrillic.

### 4.4 Do their borders meet `R-33`'s 3:1 floor? **Yes, all five, both palettes.**

Measured in the browser on the deployed stand: for every rendered element with a visible border,
the border colour against the first opaque background behind it, with the palette switched
**through the product's own theme control**.

| screen | light | dark |
|---|---|---|
| `/blocks`, `/optimisation`, `/logs`, `/workers` | 14 borders, **0 under 3:1** | 14 borders, **0 under 3:1** |
| `…/comparison` | 18 borders, **0 under 3:1** | 18 borders, **0 under 3:1** |
| `/projects/{prj}/versions/{ver}` (for the new link) | 32 borders, **0 under 3:1** | 32 borders, **0 under 3:1** |

**A near-miss of my own, recorded because §12 is about exactly this.** My first pass switched the
palette with `document.documentElement.setAttribute('data-theme','dark')` and reported
`button.am-button` at **2.06:1** in dark on four sides — a clean-looking `R-33` violation on a
closed row. It was my instrument. Under a scripted attribute flip Chrome had re-resolved
`--am-accent` on `:root` (`#7aa9e0`) while the button's `border` shorthand still held the light
value `rgb(31, 79, 139)`; driven through the product's own `[data-theme-choice="dark"]` control
the border is `rgb(122, 169, 224)` and the pair is 6.93:1, which is what the token arithmetic in
`globals.css` says it should be. **The tell was that my browser figure disagreed with a
calculation I could do from the stylesheet**, and the rule that saved it is the same one `W43-JUDGE-A`
used on the four prepared screens: measure the thing the product does, not the thing you can
make it do.

## 5. The integrator's own changes, which no stream and no judge had reviewed

Three executable files, none in either stream's grant: `tests/e2e/pc01/journey/manifest.json`,
`web/src/shared/lib/routes.ts`, `web/src/_pages/version-detail/ui/version-detail-page.tsx`.

**The manifest rows are right, including the placement argument.** `comparison` sits after
`version`, which is where `W43-PREP` argued a route naming `{project_uid}`/`{version_uid}` must
go, and the four prepared rows sit at the end with `sign-in`'s neighbours. `follow: null` on the
comparison row is correct — it captures nothing the later routes need, and inserting it between
the route that captures `run_id` and the `run` route that consumes it changes no capture order.
The conformance guard is green on all five.

### 5.1 F3 — `routes.comparison()` is asserted by nothing

```bash
cd /root/w43judge
sed -i 's|`/projects/${projectUid}/versions/${versionUid}/comparison`|`/projects/${projectUid}/versions/${versionUid}/compare`|' web/src/shared/lib/routes.ts
npm --prefix web run test      # -> Test Files 75 passed (75) | Tests 1085 passed (1085)
git checkout -- web/src
```

The builder can name an address that does not exist and every test in the repository agrees.
`routes.test.ts` gained a comparison case, but it imports the **route file** directly
(`import ComparisonRoute from '@/app/.../comparison/page'`) and never calls `routes.comparison`.
`grep -rn "routes.comparison" web/` finds exactly one caller and no test. Cost is low — the link
is one line and it is right today — but the builder exists precisely so the address is written
once, and the one place it is written is the one place nothing checks.

### 5.2 F4 — the link is asserted by nothing either

```bash
cd /root/w43judge
sed -i '89,92d' web/src/_pages/version-detail/ui/version-detail-page.tsx   # deletes the whole <p> with the link
npm --prefix web run test      # -> Test Files 75 passed (75) | Tests 1085 passed (1085)
git checkout -- web/src
```

**The only navigation path to the screen this wave was built for can be deleted and nothing goes
red.** The mutation leaves no unused-import artefact — `Link` and `routes` are both still used on
that page — so this is not `D-90`'s "right answer from a wrong premise" shape; it is simply
unasserted.

The contrast with the other stream is the whole finding. `W43-PREP` shipped
`prepared-sections.guard.test.ts` with a case *"the frame links to all four addresses"*, and
`W43-JUDGE-A`'s `P4` killed it by removing one `<Link>`. **`W43-COMPARE` reported the missing
link as outside its grant, the integrator added it, and nobody added the case that would have
come with it if a stream had owned it.** That is the ownership cost `D-89` names, one level
down: work that lands outside every grant lands outside every guard.

`W43-COMPARE` said its screen was *"reachable only by being typed"* until someone landed two
lines. Those two lines are now landed and are still the only two lines in `web/src` that nothing
in `web/tests` has an opinion about.

## 6. K4 — do `W43-JUDGE-A`'s findings still hold after the merge?

| stage-A finding | after the merge | evidence |
|---|---|---|
| **F1** — no frontend instrument reaches any of the five | **SURVIVES for four of five.** The comparison screen is now reached; the four prepared screens are not. | §6.1 |
| **F2** — `R-33`'s floor evaluated none of the five | **SURVIVES for the four.** `grep -n "blocks\|logs\|optimis\|workers" web/tests/unit/styles/screens.ts` → nothing. `StageComparisonPage` is in the census in three states. **The underlying property nevertheless holds on the stand** (§4.4) — the gap is the instrument, not the colours. | §6.1 |
| **F3** — the census's coverage message is false where it speaks | **SURVIVES, latent.** `contrast.test.ts:455` still reads *"these rules declare a colour and NO screen in `screens.ts` renders an element they match"*. It fires only under a probe; the merged tree is green. | source unchanged |
| **F4** — `W43-PREP` note 3 says two modules, three do | **SURVIVES, and is the one finding nobody recorded.** See below. | §6.2 |
| **F5** — three prepared screens explain the contract to a reviewer | **SURVIVES**, and is now confirmed from the deployed stand rather than a static render: `/blocks` shows *«…но наружу их не отдаёт ни одна операция договора…»*. Recorded for the owner as **`D-91`**. | §4.3 dump |
| **F6** / `C7` — `looksLikeProjectUid` asserted by nothing | **SURVIVES.** Recorded as **`D-90`**. | §6.3 |
| **F7** — `dependency_unavailable` printed bare | **SURVIVES.** `stage-comparison.tsx:173-180` renders `<code>{value}</code>` with no gloss, under a comment asserting the code *"is rendered beside its meaning on the run screen"* — which is true of the run screen and not of this one. Recorded inside `D-90`'s section. | source unchanged |

**Nothing was reintroduced by the other branch.** Every stage-A finding that survives, survives
because it was never repaired, not because the merge undid a repair — which §2.1 proves
independently, since no stream file changed in the merge.

### 6.1 The instruments, re-driven on the merged tree

The four prepared screens, with `W43-JUDGE-A`'s own probe — the one sentence a reviewer reads on
each, replaced with four distinct English sentences so the stream's own distinctness case cannot
mask it:

```bash
cd /root/w43judge
python3 - <<'PY'
import re, pathlib
for name in ['blocks','logs','optimisation','workers']:
    p = pathlib.Path(f'web/src/_pages/{name}/ui/{name}-page.tsx'); s = p.read_text()
    p.write_text(re.sub(r'promise="[^"]*"', f'promise="PROBE {name}: this whole sentence is '
        'deliberately English prose on a reachable screen and must not survive."', s))
PY
npm --prefix web run test      # -> Test Files 75 passed (75) | Tests 1085 passed (1085)
git checkout -- web/src
```

**Green, at the merged tree, with four fully English sentences on four reachable addresses.**

And the comparison screen, which is the control the merge could have broken and did not:

```bash
cd /root/w43judge
sed -i '73s/.*/        PROBE: this whole sentence is deliberately English prose on a reachable screen./' \
  web/src/_pages/stage-comparison/ui/stage-comparison-page.tsx
npm --prefix web run test
# -> FAIL tests/guards/rendered-language.guard.test.ts, 2 failed | 1083 passed (1085)
#    × finds no English on a rendered screen that D-53 has not already recorded
#    × finds none at all
git checkout -- web/src
```

**One of five reached. `D-88` is correctly open and correctly worded.** `SCREENS` at
`rendered-language.guard.test.ts` carries `stage-comparison` and not `blocks`, `optimisation`,
`logs` or `workers`; `screens.ts` is the same shape. Adding the four is four lines in two files
and it is the cheapest thing in this report.

### 6.2 F4 is the only stage-A finding with no home

```bash
cd /root/w43judge && grep -rn "getLogger" src/
# src/auditmanager/runs/carrier.py:106
# src/auditmanager/access/repository.py:118
# src/auditmanager/api/app.py:50
grep -n "Two modules" docs/program/W43-PREP.md            # 174: ... Two modules call `logging.getLogger` ...
grep -n "getLogger" docs/program/DEBT_REGISTER.md         # (no output)
```

`W43-JUDGE-A`'s other findings all landed: `F1–F3` as `D-88`, `F6` as `D-90`, `F7` inside `D-90`,
`F5` as `D-91`, and the manifest ownership gap as `D-89`. **`F4` landed nowhere.** The stream's
report is frozen as delivered, which is right; a register row is the mechanism for saying it is
wrong, and there is none. `W43-PLAN` says *"a false note is worse than no note, because the next
wave budgets against it"*, and `P3` is the wave that would.

Cost is one row. The note's conclusion is unaffected — the server's log lines are nowhere on the
surface either way — so this is about the register's completeness, not about the screen.

### 6.3 F6 reproduces exactly

```bash
cd /root/w43judge
sed -i 's/const wellFormed = looksLikeProjectUid(projectUid) && looksLikeVersionUid(versionUid);/const wellFormed = looksLikeVersionUid(versionUid) \&\& (looksLikeProjectUid(projectUid) || true);/' \
  web/src/_pages/stage-comparison/ui/stage-comparison-page.tsx
npm --prefix web run test      # -> Test Files 75 passed (75) | Tests 1085 passed (1085)
git checkout -- web/src
```

## 7. K5 — what I would look at next, having seen the whole wave

**1. The journey, before anything else is added to its manifest.** `D-83` should be widened and
re-severitied. This programme's own record says `npm test` has been green while the browser
journey was broken and *only the make target catches it* — but the make target catches the
**manifest's shape**, not the journey. Three rows depend on an instrument that has not completed
a walk since wave 34: `D-5` is closed *not reproducible* on the strength of it, `D-30` is closed
by the write half, and `PA-01`'s certification sentence — *"a browser creates a project, uploads
a PDF, starts a run… all through one origin"* — was last true at `ac7c348`, before wave 34.
**That sentence is `OPERATING_CONSTRAINTS.md` §4.7's shape exactly**: a document that outlived the
code it describes, and it is in `CURRENT_STATE.md`, the file `AGENTS.md` §1 makes every session
read first. The repair is small and it is a design decision, not a patch: either a `sign_in` step
type in the write half plus a way to carry one session across the walk, or an explicit
`--session` the journey is handed. The cold-browser-per-route property is load-bearing (`D-16`)
and must not be traded away to get it.

**2. A layout instrument, or an honest statement that there is none.** F1 is the first defect in
this programme that is purely geometric, and nothing in 1085 tests can express it. The cheapest
honest thing is not a visual-regression suite; it is one assertion, in the journey, that
`document.documentElement.scrollWidth <= window.innerWidth` on every route at a declared width.
That is four lines in `journey.mjs` and it makes the frame's growth a red the next time somebody
adds a link — which `R-23` guarantees they will, because the sections it sorted are not finished.

**3. The four lines that close `D-88` for this wave, and the rule that stops the next one.**
Adding the four screens to `SCREENS` and `screens.ts` is trivial and it is also the wrong shape
— it is the hand-written list again. The derivation exists and is proven: `rglob("page.tsx")`
over `web/src/app`. A frontend census that globbed its screens the way `contrast.test.ts` already
globs its stylesheets would make `D-88` structurally impossible rather than currently repaired,
and it is the same move wave 41 made for contract members.

**4. `listing-failure.ts`'s noun agreement, as a class and not as a typo.** F5 is one bad
sentence, but the mechanism — interpolating a noun into a sentence whose grammar depends on that
noun's gender — is spread across `upload-failure.ts`, `run-failure.ts` and `catalog-message.ts`,
and this programme has a guard that renders every screen and reads every word of the result. It
finds Latin words. **It could find agreement errors with the same render and a list of templates**,
and the next Russian-facing surface will reach for the same interpolation.

**5. The pattern `D-89` is the first instance of, before wave 44 dispatches.** Two grants that
share no file is the right design and it worked — the merge had no conflict at all. What it did
not cover is the work that belongs to neither: the manifest, `routes.ts`, the link. Those three
landed in the integration commit, which is the one commit in a wave that no judge is scheduled
against. **F3 and F4 are both in that commit, and I found them only because this brief put them
inside my subject by name.** A standing rule — *the integrator's own executable changes are stage
B's subject* — costs nothing and would have caught both without anyone remembering to say so.

## 8. Proof that this branch repaired nothing

```bash
cd /root/w43judge && git diff --name-only c455848 agent/w43-judge-b
# docs/program/reviews/W43-JUDGE-B.md
git status --porcelain      # (empty)
```

Six probes were applied to `web/src`, measured and reverted with `git checkout -- web/src`;
`git status --porcelain` was confirmed empty after each, and is quoted above as `REVERTED-CLEAN`
in this session's log. No probe was committed. The four name-set runs of §2.2 were taken by
`git checkout --detach <commit>` in this worktree and the branch was restored afterwards;
neither `/root/w43comp` nor `/root/w43prep` was entered.

**Lane discipline.** `gate-w43j` only — PostgreSQL `127.0.0.1:56280`, S3 `59880`/`59881`.
`docker ps` showed `gate-b0`, `gate-w43a`, `gate-w43b` and `auditmanager-w19a` up throughout;
none was started, stopped or reconfigured. The stand was driven over HTTP and through a browser
only. The write half of the journey was run against it and stopped at its first step with a
`401`, so **no project, document, version or run was created**; the read-only session used for
the browser drives was established through `/login` with the account migration `0006_app_user`
seeds and `access/__init__.py` publishes.

## 9. What I could not answer, and why

1. **Whether the populated comparison table is correct as a reviewer meets it.** No version on
   the stand has two runs, so the twelve fact rows and four stage rows were reached only in the
   test harness, never in a browser. `W43-JUDGE-A` left the run-chooser's `useState` branch to me
   because a static render cannot reach it; I could not reach it either, for a different reason —
   the data is not there. **Creating it would have meant running the write half against the
   owner's stand, and the write half cannot sign in (F2).** This is the one question stage B was
   uniquely placed to answer and did not.
2. **Whether F5's grammar defect appears on the pre-existing screens too.** `run-list.tsx` passes
   the same `parent: 'version'`, so it should, but reproducing it needs a version that 404s inside
   a run list, and I did not construct one rather than write to the stand.
3. **Whether `make gate` is still green.** I did not re-run it and say so plainly: the integrator's
   log at `3e75c91` is the evidence, and §12 makes a second run of the same command a repetition
   rather than a check. Everything in §2 that *could* have been taken from that log was re-measured
   here instead, from four trees, with per-test names rather than totals.
4. **F1's exact breakpoint in CSS terms.** I measured where the overflow starts (839 px intrinsic
   width, so below ~839 px of viewport) but not which flex rule should carry the repair. That is
   the owner of `app-frame.tsx` and `globals.css` deciding between wrapping, a narrower cluster
   and a menu, and it is a decision rather than a measurement.
