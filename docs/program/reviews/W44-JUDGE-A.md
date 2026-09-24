# W44-JUDGE-A — sub-stage A, judged on both branches before the merge

**task_id:** `W44-JUDGE-A` · **wave:** 44, close of sub-stage A · **lane:** `gate-w44j`
**worktree:** `/root/w44judge` · **branch:** `agent/w44-judge` · **base:** `843082f`

**Subjects, unmerged:** `agent/w44-see` at **`18e7873`** and `agent/w44-journey` at
**`d4cb060`**.

**This branch repairs nothing.** Its whole diff against `843082f` is this file; §8 is the
proof. Everything mutated to measure was reverted from a saved copy of the original bytes, and
the worktree was `git status --short`-clean between measurements.

**Lane provisioned first:** `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` →
`bootstrap OK`; `.venv/bin/python -c "import boto3"` → `boto3 1.43.90`; `npm --prefix web ci` →
184 packages. PostgreSQL `127.0.0.1:56310`, S3 `59910`/`59911`. No container outside
`gate-w44j*` was touched; the owner's stand at `127.0.0.1:31500` was driven over HTTP and with
a browser and never restarted or reconfigured.

---

## 0. The verdict in one paragraph

**Both repairs are repairs and not descriptions, and I could falsify neither headline claim.**
The fixed probe — English prose on a screen, a 1.08:1 border on a really-rendered element —
leaves **four of the fourteen screens unseen at `843082f`** and **reddens naming all fourteen at
`18e7873`**. A whole English page that no list mentions is **invisible to 1085 tests at the
base** and **named by its address at the tip**. The journey reaches **15/15** routes where the
base reaches 2/15, and the width assertion reproduces **839 > 780** to the pixel on the two
routes I re-took. Of eighteen mutations of my own, chosen before reading either stream's
table, **fourteen reddened the case they were aimed at, one is caught by the walk but not by
the gate, two were weak mutations of mine that correctly changed nothing, and one found a
hole** — F1 below. **Five findings follow; none of
them blocks the merge, and the first is a gap in a guard whose docstring says it has none.**

---

## 1. Findings, most severe first

### F1 — the guard that keeps a password out of this repository can be walked around by spelling the fallback differently, and its own docstring says it cannot

**Where.** `tests/e2e/test_pc01_journey_conformance.py`,
`test_the_journey_reads_its_credential_only_from_the_environment`:

```python
for smell in ("?? 'admin'", '?? "admin"', "?? 'password'", '?? "password"'):
    assert smell not in source, (
        f"session.mjs carries the fallback {smell}, which is a credential in this "
        "repository wearing a default's clothes"
    )
```

and its docstring: *"a `?? 'admin'` here would be a password in this repository **however it was
spelled**."*

**What is false.** It is four literals, not a property. `||` is not `??`.

**Reproduction.** On `agent/w44-journey` at `d4cb060`, one character changed in
`tests/e2e/pc01/journey/session.mjs:71`:

```diff
-  const password = env[PASSWORD_ENV];
+  const password = env[PASSWORD_ENV] || 'password';
```

```
$ .venv/bin/pytest tests/e2e/test_pc01_journey_conformance.py -q
78 passed in 0.14s

$ E2E_PC01_LOGIN=admin node -e "import('…/session.mjs').then(m =>
    console.log(m.credentialsFromEnvironment({ E2E_PC01_LOGIN: 'admin' })))"
login= admin  password length= 8  password= "password"
```

**The stand's seeded password is now a literal in the repository, the journey runs with no
`E2E_PC01_PASSWORD` at all, the `rc=2` hard failure never fires, and the whole conformance
suite is green.** A ternary, a destructuring default (`const { E2E_PC01_PASSWORD: password =
'password' } = env`), or `?? DEFAULT` with the literal on a `const` two lines up all pass the
same way.

**What it costs.** This is the one guard standing between this repository and a credential, and
its docstring teaches the next session that the check is exhaustive — which is
`OPERATING_CONSTRAINTS.md` §4.7's direction of damage in miniature: the prose does not merely
mislead, it authorises. Nothing here is wrong on the branch today; what is wrong is the promise.

**The cheap repair, for whoever owns it** (not taken here): assert the two reads are bare —
e.g. require each of the two assignment lines to end at `env[…_ENV];` with nothing between the
subscript and the semicolon — or assert the behaviour, that `credentialsFromEnvironment({})`
reports both names missing. Either catches every spelling; the enumeration catches four.

### F2 — the `/` opt-out's `proof` does not test the claim the opt-out stands for, and what holds the line is a case the opt-out does not know about

**Where.** `web/tests/unit/screens/route-screens.ts`, the `/` seed:

```ts
proof: (source) => /\bredirect\(/.test(source) && !/\breturn\s*\(/.test(source),
```

**What is false.** The module's header and `W44-SEE.md` §1 present the `proof` as what makes an
excused screen *"red rather than silent"* when its claim stops holding. The claim is *"it
renders nothing"*. The predicate tests two spellings: that `redirect(` occurs somewhere in the
file, and that no `return` is followed by an open parenthesis. **A screen that renders a full
page of English prose satisfies both.**

**Reproduction.** On `agent/w44-see` at `18e7873`, replace `web/src/app/page.tsx` with:

```tsx
import { redirect } from 'next/navigation';

const NEVER = false;

export default function RootPage() {
  if (NEVER) redirect('/projects');
  return <section className="am-page"><h1 className="am-page__title">This root screen is written in English and the opt-out still excuses it</h1></section>;
}
```

Both predicates hold. Then `npm --prefix web test`:

```
 Test Files  1 failed | 76 passed (77)
      Tests  1 failed | 1106 passed (1107)
 FAIL  tests/unit/screens/routes.test.ts > / starts the journey at the project list > redirects rather than rendering a screen of its own
```

`runs every opt-out claim against the route file it is about` — **green**. `has a seed for every
address, and names the ones it does not` — **green**. The screen is excused from the language
guard and from the contrast census while rendering English prose, and the only red in 1107
tests comes from a case written in an earlier wave that the opt-out neither references nor
depends on.

**What it costs.** Today, nothing: `/` is the only opt-out and `routes.test.ts` covers it. The
cost is structural, and it is this wave's own defect one level in — *an excuse whose proof can
be satisfied without the claim being true*. A second opt-out, for any address that is not `/`,
would carry no such backstop; the only friction against writing one is
`expect(excused.length).toBe(1)` in `screen-set.guard.test.ts:130`, a literal that the session
adding the opt-out edits in the same commit.

**The cheap repair** (not taken): make the proof **execute** the route module and require the
redirect — the move `routes.test.ts` already makes — so "renders nothing" is tested as
behaviour rather than as two spellings.

### F3 — a border below the floor is reported at one screen even when every screen reaches it

**Where.** `web/tests/unit/styles/contrast.test.ts:634` and `:695`, both
`where: m.occurrence.sites[0]`.

**What is missing.** `census()` (`contrast.ts:669`) accumulates **every** site a pair is reached
at; both threshold assertions print `sites[0]`. A pair key is
`edge|--am-paper|--am-surface|-|border` — tokens and property, **nothing about the screen** — so
fourteen screens carrying the same offending rule collapse into one failing row naming one of
them.

**Reproduction.** Put the same 1.08:1 module rule on **two** screens at once — `blocks` and
`workers` — and run `npm --prefix web test -- tests/unit/styles/contrast.test.ts`:

```
      Tests  2 failed | 18 passed (20)
$ grep -oE '"where": "[^"]*"' … | sort | uniq -c
      4 "where": "blocks cold html > body > div._judgeProbeEdge_388bf2"
```

Four rows — two assertions times two palettes — and **`workers` is never named**, although its
screen carries the identical rule. §2.2's fourteen runs each named their own screen precisely
because they were one screen at a time, which is the case where `sites[0]` is the whole truth.

**What it costs.** `D-93` is exactly the defect where a product-wide regression read as a
single-screen one, and `W44-JOURNEY`'s width finding ends *"AppFrame is global, so this is every
screen in the product and not this one"* for that reason. The contrast census cannot say that
while it prints `sites[0]`, so a reviewer handed `where: "blocks cold …"` for a token pair the
whole product uses is being sent to repair one screen. It never produces a wrong verdict — only
a narrow message.

### F4 — the journey's README understates what the instrument covers and what it costs, in a file this wave rewrote

**Where.** `tests/e2e/pc01/journey/README.md` on `agent/w44-journey`:

* line 14 — *"**The read walk** then visits all seven routes"*. The manifest declares
  **fifteen** and the walk visits fifteen.
* `## What it costs to run` — *"Measured on 2026-09-19 … **248 s** … **206 exchanges** … a
  **5.3 MB** envelope — 3 write steps in 83 s and 7 read routes in 165 s"*. My own run:
  **12.8 MB** and about twenty minutes; the stream measured 655 exchanges.

**Reproduction.**
```
git show agent/w44-journey:tests/e2e/pc01/journey/README.md | sed -n '14p;296,300p'
python3 -c "import json;print(len(json.load(open('tests/e2e/pc01/journey/manifest.json'))['routes']))"
```

**Not the stream's fault that it went stale, and its fault that it still is.** *"seven routes"*
has been wrong since wave 43 added five screens; the cost figure became wrong in this wave's own
commits. `W44-JOURNEY` rewrote 132 lines of this README in those commits and touched neither
number. `D-23`'s class, in the document an operator reads to learn what the instrument covers
and how long to budget — and nothing in `make gate` reads this file's prose, which is §12's
*"the absence of a reader is the absence of a check"*.

### F5 — the screen that asserts something false about the system is a recurrence, and nothing was added either time to stop the next one

The integrator already holds `/projects`' subtitle — *"Один локальный проверяющий. Без
аутентификации, ролей и разделения на организации."* under `SIGN_IN_LANDING_PATH = '/projects'`.
I did not re-find it. **I did look for others of its class, and the interesting result is not a
second instance but the history.**

```
grep -rniE "аутентифик|без учётных|no authentication|tenancy|ролей|разделени[ея] доступа|локальн" \
  web/src --include=*.tsx --include=*.ts
```

returns three hits: the `/projects` subtitle, `layout.tsx`'s metadata description (true), and
`app-frame.tsx`'s footer — and the footer carries this comment, written in wave 37:

> *AMENDED 2026-09-22 after wave 34: it said "без учётных записей" — WITHOUT ACCOUNTS — and
> accounts now exist. `W37-CERT4` found it as `W37CERT4-2`: a claim about the system's security
> posture, rendered to a reviewer on every screen INCLUDING the sign-in screen they had just
> used, and by then the opposite of true.*

So the class was found, understood and written up seven waves ago; **the repair was applied to
one of the two sites that carried the claim, and no instrument was added.** The `/projects` copy
then survived seven waves and was found again — by a browser, not by a guard. The reportable
part is not that one sentence is wrong; it is that a screen's claim *about the system* is
checked by nothing in this repository, and the one previous repair was site-by-site.

I checked the other places such a claim lives and **all of them hold**: the four prepared
sections' promises against the contract (`/optimisation`'s *"запуск прогона принимает только
версию документа и режим работы с провайдером"* against `StartRunRequest`, which requires
`version_uid`, allows `provider_mode` and sets `additionalProperties: false`; `/logs`' *"такой
операции в договоре нет"* against the eighteen operation ids; `/blocks`; `/workers`), and the
knowledge base's *"проекция над журналом решений: ничего не хранится отдельно и всё
пересчитывается из событий"* against `src/auditmanager/decisions/projection.py`, which is a view
folded from `expert_decision_event` with no stored current verdict.

---

## 2. A1 — the fixed probe, on each of the fourteen addresses

Wave 43's measurement, unchanged: **English prose on a screen** and **a border at 1.08:1 on a
really-rendered element**. Run on all fourteen rendering addresses rather than on a sample, and
run at **`843082f` as well** — a probe that reddens at the tip says nothing until the same
probe is shown green at the base (`OPERATING_CONSTRAINTS.md` §12: my instrument must not share
an assumption with its subject).

### 2.1 English prose: 10 of 14 at the base, 14 of 14 at the tip

The probe replaces the one rendered title of each of the fourteen `_pages` slices with a
distinct English sentence — *"Judge probe: this whole sentence reaches a reviewer in English on
the `<name>` screen"*. **Deliberately digit-free**: a first pass numbered the sentences and
tripped `prepared-sections.guard.test.ts`'s *"shows no number at all"* on four screens, which is
a red about a digit and says nothing about English. That pass is discarded; the figures below
are the digit-free ones.

| tree | whole frontend suite | screens the language guard names |
|---|---|---|
| `843082f` | `Test Files 5 failed \| 70 passed (75)` · `Tests 7 failed \| 1078 passed (1085)` | **10** — all but `blocks`, `logs`, `optimisation`, `workers` |
| `18e7873` | `Test Files 5 failed \| 73 passed (78)` · `Tests 11 failed \| 1097 passed (1108)` | **14 of 14, each by name** |

At the tip, `R-18 … finds none at all` lists all fourteen sentences, and `finds no English on a
rendered screen that D-53 has not already recorded` lists all fourteen again **with the screen
in brackets** — including the four that were invisible:

```
"\"Judge probe: … on the blocks screen\"        …  [blocks]",
"\"Judge probe: … on the logs screen\"          …  [logs]",
"\"Judge probe: … on the optimisation screen\"  …  [optimisation]",
"\"Judge probe: … on the workers screen\"       …  [workers]",
```

The four invisible at the base are **the same four wave 43 measured**, so the two waves are
comparable and the difference is the repair.

*(The 78 files / 1108 tests at the tip include one throwaway dump file of mine; without it the
tree is **77 files, 1107 tests**, which is `W44-SEE`'s figure, independently reproduced.)*

### 2.2 The 1.08:1 border: green at the base, red naming the screen on all fourteen

Wave 43's border unchanged — a collocated `*.module.css` declaring `border: 1px solid
var(--am-paper)` on a `div` the screen really renders — driven **fourteen times, one screen per
run**, each `npm --prefix web test -- tests/unit/styles/contrast.test.ts`:

```
[0]  blocks                     rc=1  Tests 2 failed | 18 passed (20)  1.08 / 1.11  where: "blocks cold html > body > div._judgeProbeEdge_388bf2"
[1]  change-password-signed-out rc=1  …  where: "change-password-signed-out cold …"
[2]  document-detail            rc=1  …  where: "document-detail cold …"
[3]  knowledge-base             rc=1  …  where: "knowledge-base cold …"
[4]  logs                       rc=1  …  where: "logs cold …"
[5]  optimisation               rc=1  …  where: "optimisation cold …"
[6]  project-detail             rc=1  …  where: "project-detail cold …"
[7]  projects                   rc=1  …  where: "projects cold …"
[8]  review                     rc=1  …  where: "review cold …"
[9]  run                        rc=1  …  where: "run cold …"
[10] sign-in                    rc=1  …  where: "sign-in cold …"
[11] stage-comparison           rc=1  …  where: "stage-comparison cold …"
[12] version-detail             rc=1  …  where: "version-detail cold …"
[13] workers                    rc=1  …  where: "workers cold …"
```

**Fourteen for fourteen**, 1.08:1 light and 1.11:1 dark, each naming its own screen.

**The control at `843082f`, identical probe, on `/blocks`:**

```
 ✓ R-33: every border that meets on a screen clears 3:1, in both palettes > names the theme, the ratio and the site of every border under the floor
 × the census … > names every colour-bearing rule that NO rendered screen reaches
   → these rules declare a colour and NO screen in `screens.ts` renders an element they match …
     expected [ '._judgeProbeEdge_388bf2' ] to deeply equal []
```

`R-33`'s floor is **green over a 1.08:1 border on an element the product renders**, and the one
red says something **false** about a rule `BlocksPage` does render, naming a bundler hash rather
than a screen. `D-88`'s second defect, reproduced verbatim at the base and gone at the tip.

**A1's answer: the suite does not stay green. `D-88`'s repair is a repair.**

---

## 3. A2 — does the derived set actually derive?

### 3.1 A screen no list mentions

`web/src/app/judge-probe/page.tsx`: a whole page of English prose, mentioned nowhere else.

| tree | result |
|---|---|
| `843082f` | `Test Files 75 passed (75)` · `Tests 1085 passed (1085)` · **rc=0** |
| `18e7873` | `Test Files 1 failed \| 76 passed (77)` · `Tests 2 failed \| 1105 passed (1107)` · **rc=1** |

and the message is the address, not a hash:

```
FAIL tests/guards/screen-set.guard.test.ts > … has a seed for every address, and names the ones it does not
  web/src/app serves these addresses and `SEEDS` … answers for none of them, so NO frontend
  instrument renders them: not the language guard, not the contrast census. …
  expected [ '/judge-probe' ] to deeply equal []
FAIL … > every derived screen renders real markup, and none of them throws
  expected 14 to be 15
```

**A whole English page is invisible to 1085 tests at the base and reddens two cases naming its
address at the tip.** That is a glob and not a longer literal.

**Stated precisely, because a reader could take it too far:** the new screen is **named, not
rendered**. Neither census reaches its prose until a human writes a seed — which is the design
(*"coverage is derived from the contract; the seeds are not"*), and which the guard's own
message says out loud. The derivation closes *"nobody noticed the screen"*; it does not close
*"nobody answered for it"*, and it is not claimed to.

### 3.2 Defeating the opt-out

See **F2**: the proof can be satisfied by a screen that renders, and what catches it is
`routes.test.ts`, which the opt-out neither names nor depends on.
---

## 4. A3 and A4 — the journey, driven

### 4.1 Getting it to run, which is part of the question

`E2E_PC01_LOGIN=admin E2E_PC01_PASSWORD=password`. The account is the one
`db/migrations/versions/20260922_0006_app_user.py` seeds, and that migration's **own docstring**
is the only place in the tree that names it — deliberately, and
`test_the_journey_reads_its_credential_only_from_the_environment` is what keeps it that way.
Finding it cost one read of one file. **The design is usable**, and the failure when it is not
supplied is the right failure:

```
$ npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:31500 --phase all
e2e:pc01: no credential. E2E_PC01_LOGIN and E2E_PC01_PASSWORD are not set.
…
The BFF answers 401 without a session (wave 34, by design), so a run without a
credential walks two routes of fifteen and reports on thirteen it never opened.
That is D-92 and it survived nine waves, so this is a hard failure and not a skip.
rc=2
```

`rc=2`, before any browser starts, naming the row and saying why a skip would be a lie.

### 4.2 The walk, re-driven

```
$ E2E_PC01_LOGIN=admin E2E_PC01_PASSWORD=password \
    npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:31500 --phase all
sign-in: ok at /login -- carrying 'am_session' (HttpOnly=true, SameSite=Strict) into every cold browser
ok  create-project   api=3 …
ok  upload-document  api=4 …
ok  start-run        api=5 … terminal=published in 1507ms/150000ms
ok  root           200  api=1 auth=0 console=0 jar=[am_session] w=765/780
…
ok  workers        200  api=0 auth=0 console=0 jar=[am_session] w=780/780
write steps checked: 3/3
routes checked: 15/15
e2e:pc01 OK
rc=0
```

**15 of 15, 3 of 3, zero findings, `rc=0` read from `$?` after a redirect.** The envelope is
12.8 MB. Read out of it rather than off the console:

```
routesChecked 15  declared 15  failures 0   viewport {'width': 780, 'height': 900}
```

and per route, `innerWidth` is **780 on all fifteen**, `scrollWidth` is **765 on the nine
screens with a vertical scrollbar and 780 on the six without**, `startedWith` is
`['am_session']` on all fifteen. Those are `W44-JOURNEY`'s numbers, reproduced on a different
lane by a different session.

### 4.3 `D-16`: carried deliberately, or leaking?

**Carried deliberately, and three of the four things that say so are checks rather than prose.**
What I verified myself:

* `cdp.mjs` exports `withColdBrowser` and nothing else; every route gets `spawn(chrome,
  --user-data-dir=<mkdtempSync>)` and the process is `SIGKILL`ed in the `finally`. There is no
  API that hands a `Page` out, so the property cannot be lost by forgetting it.
* The jar is read **before the first navigation** (`recordStartingJar()` is called between
  `setCookies` and `fn(page)`), and it is read with **`Storage.getCookies`**, which answers for
  the browser rather than for the frames of `about:blank`. That distinction is the one the
  stream got wrong once, caught with a false red, and wrote down beside the call.
* The walk then asserts, per route, that what the profile held equals what it was handed, and
  prints it on every line. All fifteen printed `jar=[am_session]`.
* No route's input depends on an earlier route having run: the cookie is one value computed
  once, and the four identifiers are extracted from rendered links and passed explicitly.

**The one place it could still become a tautology, stated because A3 asks for the difference.**
The walk's comparison is necessarily *reading vs. the value handed in*; what makes it a
measurement is that the left-hand side comes out of the browser. Nothing outside `cdp.mjs`
checks that. `test_the_instrument_still_reads_back_the_jar_every_route_started_with` asserts
`"recordStartingJar" in cdp and "startedWith" in cdp` — substrings. A one-line change inside
`recordStartingJar` that set `#startedWith` from the cookies the caller passed instead of from
`#jar()` would leave the walk green, the gate green and `D-16` unmeasured. **I did not drive
that mutation** — it costs a twenty-minute walk to demonstrate a green — so it is reasoned from
the source and labelled as such, not measured. It is the natural next assertion for whoever
owns this file: require `recordStartingJar` to route through `Storage.getCookies`.

### 4.4 A4 — is the width assertion real?

**It runs on every route**, which the walk's own output and the envelope both say: fifteen
routes, `innerWidth` 780 on all fifteen, `scrollWidth` 765 or 780, and one shared `width.mjs`
that `journey.mjs` and the proof both import. What that does not establish is that it can go
red, so:

**The measurement, re-taken on two routes.** `prove_the_width_assertion_can_fail.mjs` restores
what `.am-app__bar` had before wave 43 — it writes a scratch copy of `globals.css` with the one
`flex-wrap: wrap` removed, checks the copy then declares no `flex-wrap` at all, injects the
equivalent rule into the live stand and **reads the computed value back on both sides**, `wrap`
then `nowrap`, so the two halves meet at the value the browser lays out from.

```
$ node tests/e2e/pc01/journey/prove_the_width_assertion_can_fail.mjs \
    --origin http://127.0.0.1:31500 --route root
ok  root             before  765/780 (wrap)  ->  after  839/780 (nowrap)
      root: the screen scrolls sideways at the declared width. scrollWidth 839 > innerWidth 780
      (clientWidth 765), overflowing by 59 px. 11 element(s) cross the right edge; widest:
      <div.am-theme> right=839 width=71; …
      D-93: AppFrame is global, so this is every screen in the product and not this one.
rc=0

$ … --route workers
ok  workers          before  780/780 (wrap)  ->  after  839/780 (nowrap)
      workers: … scrollWidth 839 > innerWidth 780 … overflowing by 59 px …
rc=0
```

**839, on both, to the pixel — which is `W43-JUDGE-B`'s number and `W44-JOURNEY`'s.** The
assertion is real, it names the route, it names the numbers, and it names the widest offenders
with enough identity to grep. The other seven routes are the stream's measurement and not mine
(§11).

**Two things about this proof that are right and worth saying**, because the obvious version of
it would have been wrong in both:

* it **imports `width.mjs`'s own `measureWidth` and `widthFindings`** rather than restating the
  comparison, so the proof exercises the assertion the walk uses and not a second copy written
  to agree — `OPERATING_CONSTRAINTS.md` §12, applied by the stream to itself;
* it **fails if a route was already overflowing before the mutation**, because a route that
  starts red proves nothing about an assertion.

**Its one unavoidable limit, stated by the stream and confirmed by me:** the deployed stand's
image was built from the repaired tree and this session may not rebuild it, so the mutation
reaches the screen as an injected rule rather than as a rebuilt stylesheet. The join is the
computed value — and the probe's `before !== 'wrap'` check is what would catch a stand built
from some other tree.

### 4.5 A route the walk cannot reach — named by the walk, or by a reader?

**By the walk, up to a point, and the point is worth stating.** Driven rather than read: one
`follow.href_pattern` in `manifest.json` pointed at a link the application does not render, and
the read walk run again.

```
$ python3 …/jmutate.py apply JA-unreachable-route     # "^/projects/prj_%ID%/documents/(doc_%ID%)$"
                                                      #   -> "^/no-such-link/(doc_%ID%)$"
$ E2E_PC01_LOGIN=admin E2E_PC01_PASSWORD=password \
    npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:31500 --phase read

ok  root           200  … jar=[am_session] w=765/780
ok  projects       200  … jar=[am_session] w=765/780 {"project_uid":"prj_…"}
RED project        200  … jar=[am_session] w=765/780

e2e:pc01: stopping at 'project' -- the walk cannot continue without document_uid.
The routes after it were NOT checked.

routes checked: 3/15

e2e:pc01 FAILED -- 2 finding(s):
  - project: rendered no link matching ^/no-such-link/(doc_%ID%)$ so the journey cannot reach
    document_uid. Links offered: /projects | /knowledge-base | /account/password | /blocks |
    /optimisation | /logs | /workers | /login | /projects | /projects/prj_…/versions/ver_… |
    /projects/prj_…/documents/doc_…
  - only 3 of 15 routes were reached; an unfinished walk is not a pass
rc=1
```

**What the walk names by itself:** the route it stopped at, by name and with `RED` on its own
line; the identifier it could not capture; **every link the screen did offer**, which is what
turns "it broke" into "here is what it rendered instead"; and the sentence that the routes after
it were not checked. **What it does not name:** the twelve unreached routes, individually. They
are a count — *"only 3 of 15"* — and a reader has to open `manifest.json` to learn which twelve.

That is much better than the base, where the same shape produced *"routes checked: 2/15"* and
nothing else, and it is one line short of complete: the walk knows `manifest.routes` and could
list the names it never opened. Not a finding, a suggestion.

### 4.6 The thirteen offenders on the `run` screen, checked rather than accepted

`W44-JOURNEY` §5 records an observation its verdict does not use: the `run` route reports
**13 elements crossing the right edge while `scrollWidth` is 765** — no overflow — and explains
it as boxes clipped by an ancestor's `overflow`. **That explanation is right, and I verified it
with computed styles rather than by agreeing.** Driving the same URL from a cold browser at
780 × 900 and walking the table's ancestor chain:

```
table                              overflow-x: visible  clientW 764  scrollW 764  right 813
div.stage-table_scroller__kpQWd    overflow-x: auto     clientW 667  scrollW 764  right 716
div.am-page__body                  overflow-x: visible  clientW 715  scrollW 715  right 741
```

The stage table sits in a **deliberate horizontal scroller**, so the `ДЛИТЕЛЬНОСТЬ` column is
reachable rather than lost, and the page does not scroll sideways. It is also the case that
**makes the choice of verdict right**: an assertion that counted offenders, or that compared
element right-edges to the viewport, would have reddened here for a designed scroll container.
`scrollWidth <= innerWidth` is the comparison that does not.

### 4.7 `D-83`'s row, re-taken independently

`W44-JOURNEY` reports that `D-83`'s register row was false — that the eleven sentences were not
*"verified only against a live stand"* but verified **by nothing**, because `refusals.mjs` died
on an English control selector before driving a single fixture. **Confirmed, from the base tree
rather than from their branch:**

```
$ git archive 843082f tests fixtures web/package.json | tar -x -C /root/w44j-basejourney
$ node /root/w44j-basejourney/tests/e2e/pc01/journey/refusals.mjs --origin http://127.0.0.1:31500
Error: click form button[type="submit"] [text="Create"]: no element matches it
    at Page.click (…/cdp.mjs:600:31)
    at async seedProject (…/refusals.mjs:214:10)
    at async main (…/refusals.mjs:445:18)
rc=1
```

**Zero fixtures driven, in `seedProject`, before any refusal.** The row's "live stand" column
described a script that had not run since the screens were translated. `W44-JOURNEY` found this
by running the documented proof rather than by grepping, and reported it in the direction that
made its own result smaller.

---

## 5. A5 — does every new guard bite?

Eighteen mutations, **chosen before reading either stream's table**, applied one at a time,
each reverted before the next, each confirmed reverted with `git status --short`. Seventeen are
below; the eighteenth is §4.5's, which made a route unreachable and is reported there.

### 5.1 The frontend, on `18e7873`

`npm --prefix web run typecheck` then `npm --prefix web test -- tests/guards tests/unit/screens
tests/unit/styles` — 27 files, 423 tests, green unmutated.

| mutation | `tsc` | what reddened |
|---|---|---|
| **M1** `stage-comparison-page.tsx`: drop the `looksLikeProjectUid` branch, keep the import used | **clean** | 1: `screen-set.guard … refuses exactly the segments the seeds say it refuses` — **`D-90`'s own check, with a clean typechecker** |
| **M2** `routes.comparison()` → `` `/compare` `` | fails | 4: the three `D-94` route cases, naming the builder and the orphaned address |
| **M3** delete the comparison `<Link>` from `version-detail-page.tsx` | clean | 1: `D-94: every address a builder builds is linked from some rendered screen` |
| **M4** restore `D-95`: `version: { genitive: 'версии', noSuch: 'Такого', thisOne: 'этого' }` | clean | 1: `gender-agreement … finds no disagreement in anything the listing classifier produces` |
| **M5** a fourth English `LoadingState what="the fourth one"` | clean | 2: `D-82: no branch label carries English, reachable or not` + the coverage case |
| **M6** `routeAddresses()` returns `[]` | clean | **11 tests across 5 files** — all four instruments |
| **M7** the census stops consuming the derived set | clean | 2: `opens every screen web/src/app offers, derived rather than listed` + the unreached-rule case |
| **M8** the language guard stops spreading `DERIVED_SCREENS` | fails | the **suite** fails to load: `Error: no screen named 'review' is in the derived set …`, plus `TS6133` |

**M1 is the one that matters most**: the register's own mutation, which in its naive form dies
at `tsc` for an unused import, gives a **clean typecheck** here and a red that names the screen
and the segment. The split `W44-SEE` argues for — derive the question, let a human answer it —
is what makes that possible, and it is the right call.

### 5.2 The journey, on `d4cb060`

`.venv/bin/pytest tests/e2e/test_pc01_journey_conformance.py -q` — **78 passed** unmutated,
which is the stream's figure (54 → 78).

| mutation | result |
|---|---|
| **J1** `journey.mjs` stops calling `widthFindings` | **red**: `test_the_instrument_still_asserts_a_width_on_every_route` + its control |
| **J4** a session action in `manifest.json` carries a literal `value` | **red**: `test_no_session_action_carries_a_credential` |
| **J5** the manifest's viewport widened to 1400 | **red**: `test_the_viewport_declares_a_width_every_route_is_held_to` + its control |
| **J7** a route's `path` changed to one `web/src/app` does not serve | **red**: `test_the_journey_walks_every_screen_the_application_offers`, `test_each_route_agrees_with_its_own_page_module` |
| **J8** the declared session cookie renamed | **red**: `test_the_session_cookie_and_mount_are_the_ones_the_application_uses` |
| **J2** `session.mjs`: `env[PASSWORD_ENV] \|\| 'password'` | **GREEN — this is F1** |
| **J3** `recordStartingJar` set to `[]` | green in the gate; **the walk catches it**, per route, by comparing the reading to what it handed in. The conformance case is a substring check and its docstring says it checks wiring rather than firing. Not a finding; the sharper version is §4.3. |
| **J6** a route's `name` changed but not its `path` | green, and **correctly so** — the guard joins on paths, and my mutation changed nothing it is about. A weak mutation of mine, recorded so the table is not read as five-for-five. |
| **J9** `refusals.mjs`'s `openSession(` call renamed | green: `test_the_refusal_drive_signs_in_before_it_drives_anything` is `"openSession" in source`, which the surviving import satisfies. The script would throw at run time, so nothing is silent — but the check cannot tell an import from a call. |

### 5.3 Two honest caveats about my own table

1. **M6 was wrong the first time and I nearly reported a false green.** My first version inserted
   `if (process.env.W44_JUDGE_MUTATION === 'empty') return [];` and I never set the variable, so
   the mutation was a no-op and the suite was green — which reads exactly like a derivation
   nothing checks. Corrected to an unconditional `return []`, it reddens eleven tests. Both runs
   are in this report, because a judge who publishes only the runs that worked is running the
   same instrument as the sessions being judged.
2. **M8's red is a failed *suite*, not a failed *test*.** vitest's `Tests 1 failed | 400 passed
   (401)` line counts only the typecheck guard; the real red is on `Test Files 2 failed | 25
   passed (27)` and in the `Failed Suites` block. `make gate` reads `GATE OK`, which requires
   both, so nothing is at risk — but a session reading the `Tests` line alone would conclude
   that only `tsc` caught it.

---

## 6. What the streams did right, including against their own interest

Both did, repeatedly, and this is not padding — it is the part an audit that only names faults
destroys.

* **`W44-SEE` proved its own brief wrong three times and said so**: the substitution mechanism
  is **one** module wide and not four (and the three named modules are not where the brief puts
  them); `SCREENS` is at line **892**, not 795; and `web/src/app` carries **fifteen** `page.tsx`
  and not fourteen — *"the brief's fourteen is the right number for screens and the wrong
  number for addresses, and the difference is exactly the opt-out this task had to design"*. I
  confirmed all three. The last one is the kind of correction that could have been quietly
  reconciled and was not.
* **`W44-SEE` declined to claim a repair `S2` could not support.** `D-82`'s row invited the
  guess that the derived set would make the `useMutation` branches reachable. It does not —
  `useMutation` builds its own observer and reads no cache — and the report says so and
  delivers an instrument instead of an edit. That is the row's actual request.
* **`W44-SEE` volunteered that its own seed was wrong before its guard was.** `MALFORMED_SEGMENT`
  had to become Cyrillic because the derived variants immediately reported the old Latin
  `not-an-identifier` as English on a rendered screen: *"The guard was right and the seed was
  wrong."*
* **`W44-SEE` volunteered two false reds it created and fixed** — the scan reddening on the
  doc comment of the module it had just repaired, and the heteroclitic check reddening on
  `пара имени и пароля`, an ordinary genitive the rule never judges. *"A check that fails on
  text it does not judge teaches the next reader to weaken it."*
* **`W44-JOURNEY` reported that `D-83`'s register row was false in the direction that made its
  own result smaller**, not larger: the eleven sentences were verified **by nothing**, not
  "only against a live stand", because `refusals.mjs` died on an English control selector
  before driving a single fixture. And then it refused the optimistic count: *"Category 1 —
  verified in the gate: zero of twelve, and the number cannot move without a browser in the
  gate."* A stream that wanted a good number had eight of twelve available and did not take
  them.
* **`W44-JOURNEY` corrected a premise of its own mid-flight and left the correction in the
  code**: `Network.getCookies` answers for the current page's frames, so on `about:blank` — the
  only place `D-16`'s check can be taken — it answers `[]` while the cookie is present and
  working. The first repaired run reddened all three routes with a false finding. It is
  `Storage.getCookies` now, with the reason written beside the call.
* **`W44-JOURNEY` reported that two of `refusals.mjs`'s four checks were vacuous** — a
  `startsWith('Retry')` on a screen whose retry says `Повторить с тем же ключом`, and a
  `submitDisabled` that came back `null` and read as "still pressable" — which is a statement
  that its predecessor's instrument had been proving nothing.
* **Both read their verdicts from logs and both recorded a harness telling them `exit code 0`
  over a run whose `$?` was `1`.** `OPERATING_CONSTRAINTS.md` §4.62, followed rather than cited.
* **`W44-JOURNEY` left the four `w28-live` fixtures alone** and said why, rather than doing
  speculative maintenance on manifests nobody drives — and noted that a run of one now fails
  loudly naming `D-92`, so the failure carries its own fix.
* **`W44-JOURNEY`'s explanation of the `run` screen's thirteen offenders is right, and I checked
  it rather than agreeing** — see §4.6. It is also the case that justifies its choice of
  comparison: an offender-count rule would have reddened on a designed scroll container.
* **`W44-SEE` chose the comparison that cannot go green on its own mutation.** `D-90`'s
  expectation is a human's answer in `SEEDS` rather than a scan of the component for
  `looksLike…(`, and the difference is the whole of M1: a scan would have deleted its own
  evidence along with the behaviour.

---

## 7. Claims of theirs I re-measured rather than re-read

| claim | source | my measurement |
|---|---|---|
| wave 43's probe gives **1 failed at the base** | `W44-SEE.md` §0 | **Confirmed in kind**, not to the number. The contrast half alone gives exactly 1 failed and it is the false unreached-rule case. With the English half applied to all fourteen screens the base gives **7 failed** — because ten of the fourteen screens *were* in the old literal. The stream's "1 failed" is its four-screen probe; mine is a fourteen-screen one. Neither number is wrong; they are different probes and the report should not be read as "the base catches one thing". |
| **4 failed at the tip** | `W44-SEE.md` §0 | **Confirmed in kind.** My fourteen-screen English probe plus a one-screen border gives 11 failed at the tip, and both halves name every screen. |
| frontend is **1107 tests in 77 files** at `18e7873` | `W44-SEE.md` §4c | **Confirmed exactly**, from my own clean run: `Test Files 1 failed \| 76 passed (77)` · `Tests 2 failed \| 1105 passed (1107)`. |
| wave 43's frontend was **1085 in 75 files** | both briefs | **Confirmed exactly** at `843082f`: `Test Files 75 passed (75)` · `Tests 1085 passed (1085)`. |
| `web/src/app` carries **15 `page.tsx`**, **14 render** | `W44-SEE.md` §1 | **Confirmed.** `find web/src/app -name page.tsx \| wc -l` → 15; rendering all fourteen derived screens through the harness produces fourteen non-empty documents (602–6816 bytes). |
| the walk goes from **2/15 to 15/15** | `W44-JOURNEY.md` §1, §3 | **Confirmed by driving it**: `routes checked: 15/15`, `write steps checked: 3/3`, 0 findings, `e2e:pc01 OK`, `rc=0`. §4.2. |
| the width assertion names **839 > 780** | `W44-JOURNEY.md` §5 | **Confirmed to the pixel on two of the nine routes** (`root`, `workers`), each `before 765/780 (wrap) -> after 839/780 (nowrap)`, 59 px over. §4.4. |
| **`D-83`'s row is false**: `refusals.mjs` had not run at all | `W44-JOURNEY.md` §0 | **Confirmed from the base tree, not from their branch**: 0 fixtures driven, dies in `seedProject`. §4.7. |
| the conformance guard went **54 → 78** tests | `W44-JOURNEY.md` §7 | **Confirmed**: `.venv/bin/pytest tests/e2e/test_pc01_journey_conformance.py -q` → `78 passed in 0.32s`. |
| every case this wave adds is reddened by at least one of twenty-four mutations | `W44-SEE.md` §4b | **Not re-measured in full** — I drove eight frontend mutations of my own instead (§5.1), which cover every row the register names plus the four wiring seams, and none of the rest. Twenty-four checked one at a time is a claim I did not take. |


---

## 8. This branch carries one file

```
$ git diff --name-only 843082f..agent/w44-judge
docs/program/reviews/W44-JUDGE-A.md
```

Nothing in `web/**`, `tests/**`, `contracts/**`, `src/auditmanager/**`, `db/**`, `infra/**`,
`Makefile`, `package.json`, `docs/program/DEBT_REGISTER.md` or `docs/program/dispatch/**` was
committed by this session. The mutations above were applied to a detached checkout of each
subject branch, reverted from a saved copy of the original bytes, and confirmed reverted with
`git status --short` before the next one.

---

## 9. Conditions, and what I did not do

* **The host was contended throughout.** `load average 5.6–10.3`, and an unrelated workload
  under `/tmp/codex-vor-wave2` was running `npm run build` across three workspaces during the
  mutation battery. `OPERATING_CONSTRAINTS.md` §4.6: every duration in this report is evidence
  about the machine and none of them is used as a verdict. Every verdict here is a case name
  and a `Tests`/`Test Files` line, or the journey's own last line.
* **I did not run `make gate` on either branch.** The streams each did and quoted their
  `GATE OK` lines; re-running two full gates would have cost the sub-stage more than it bought,
  and the wave's one gate belongs to the integrator after the cross-judges. **So both gate
  verdicts in this sub-stage are read rather than re-measured, and I say so rather than
  implying otherwise.** `W44-JUDGE-X` runs on the merged tree and is the right place for it.
* **I did not re-drive `W44-SEE`'s twenty-four mutations or `W44-JOURNEY`'s thirty-six.** I
  drove eight and nine of my own instead, plus one more for §4.5.
* **I did not run `prove_the_guard_can_fail.py`'s thirty-six mutations** either; the
  conformance suite's own `test_control_*` cases are its proof that each check can fail, and
  §5.2 mutates the real subject rather than a synthetic declaration, which is the half those
  controls cannot cover.
* **Every measurement was taken with the worktree clean.** `git status --short` between runs,
  and the probe scripts restore from a saved copy of the original bytes rather than from `git
  checkout`, so a restore that failed would show as a dirty tree rather than as a silent
  revert. One did, once — a language-probe and a contrast-probe restore interleaved and left
  `blocks-page.tsx` patched; `git status` caught it, the file was restored from the index, and
  that run was re-taken.
* **The stand accumulated my projects too.** One full walk and any drive creates a project on
  `auditmanager-w19a`; `W44-JOURNEY` already recorded that the project count is now a function
  of how often the journey was driven. Nothing was restarted, reconfigured or deleted.

---

## 10. For the integrator

1. **Nothing here blocks the merge of sub-stage A.** Both branches do what they say.
2. **F1 is the one to route somewhere, and it is small.** A guard that is meant to keep a
   credential out of this repository enumerates four spellings and its docstring claims it
   covers every one. Tightening it is a few lines and it is cheapest now, while the file is one
   wave old and its author's reasoning is on the branch. **F2** is the same shape in the other
   stream — an excuse whose proof does not test its claim — and deserves a register row beside
   it. **F3** is a message, not a verdict, and can wait. **F4** is a two-line edit in a file
   `W44-JOURNEY` owns. **F5** is context for a repair already in hand, and the useful part of
   it is that nothing checks this class at all.
3. **The journey's two environment variables are a change to how the instrument is invoked**
   and `W44-JOURNEY` said so. I add one operational note: `E2E_PC01_LOGIN=admin
   E2E_PC01_PASSWORD=password` against this stand is discoverable only from the docstring of
   `db/migrations/versions/20260922_0006_app_user.py`. Getting the walk to run took one read of
   that file and nothing else, so the design is usable — but whatever the integrator hands the
   cross-judges should carry that pointer, because a judge who cannot find it reads `rc=2` as a
   broken instrument.
4. **Do not read `W44-SEE`'s "1 failed / 4 failed" as the size of the base's blindness.** See
   §7 row 1: those are a four-screen probe's numbers. The fourteen-screen figures are 7 and 11,
   and the load-bearing statement is *which screens are named*, not how many cases fail.

---

## 11. What I could not answer, and why

1. **Whether either branch's `make gate` line is still true.** I did not run a gate. Both
   streams quote a `GATE OK` line; I read them, I did not re-measure them, and two full gates
   on a contended host would have cost this sub-stage more than the answer is worth before the
   merge. `W44-JUDGE-X` runs on the merged tree and that is the right place for it. **Read, not
   measured — treat it as such.**
2. **Whether the `D-16` reading could be turned into a tautology without a red.** §4.3. The
   mutation is a one-liner inside `recordStartingJar`, and demonstrating that it stays green
   costs a full twenty-minute walk plus a full conformance run, which I judged not worth a
   sub-stage's time against a hole nobody has opened. **Reasoned from the source, not driven**,
   and labelled that way in §4.3 rather than stated as a finding.
3. **Whether `W44-SEE`'s twenty-four mutations each redden the case its table names.** I drove
   eight of my own instead. A table of twenty-four re-driven one at a time is a `W44-JUDGE-X`
   job on the merged tree if anyone wants it; the eight I chose cover every row the register
   names (`D-82`, `D-90`, `D-94`, `D-95`) plus the four wiring seams, and all eight bite.
4. **Whether the width assertion reddens on all nine placeholder-free routes.** I re-took two
   — `root` and `workers` — and both give exactly `839 > 780`. The other seven are `W44-JOURNEY`'s
   measurement, and since the offender is `.am-theme` inside the global `AppFrame`, a
   per-route difference would be surprising rather than informative. **Two of nine measured,
   seven read.**
5. **Whether any *other* screen asserts something false about the system.** I swept the three
   places such a claim can live — `web/src` prose, the four prepared-section promises against
   the contract, and the knowledge base's claim about the decision journal against
   `src/auditmanager/decisions/` — and found none beyond the one the integrator already holds.
   **That is a negative result from three queries, not a proof.** Nothing in this repository
   checks a screen's claim about the system against the system, so the honest statement is that
   I looked where I could think to look.
