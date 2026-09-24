# W44-JOURNEY — make the browser journey run again, then make it see width

**task_id:** `W44-JOURNEY` · **wave:** 44, sub-stage A · **lane:** `gate-w44a`
**worktree:** `/root/w44jrn` · **branch:** `agent/w44-journey` · **base:** `843082f`

Opened **before the first measurement**, as the brief requires, and filled as each command
ran. Nothing here is written in advance of the command that produced it.

## Subject

| row | claim |
|---|---|
| `D-92` | the browser journey stops at route 2 of 15 and has since wave 34 |
| `D-83` | eleven of fifteen `expects_rendered` sentences are verified by nothing inside the gate |
| `D-93` | 1085 frontend tests and not one can express a width |

---

## §0 Premises in the brief, verified before being built on

Wave 42's brief asserted something false about FastAPI; wave 43's asserted three things
the stream had to correct. So each of this brief's premises was checked rather than used.

### The three `D-92` facts: all three hold

| premise | verdict | how |
|---|---|---|
| the BFF answers `401` without a session cookie | **true** | driven: `POST /bff/v1/projects` → `401 authentication_required`, body quoted in §1 |
| `cdp.mjs` gives every route a fresh browser with an empty profile | **true** | read: `withColdBrowser` spawns a new process with a `mkdtemp` profile and there is no exported way to reuse one |
| the manifest has no sign-in step, and `write.mjs` knows three verbs | **true** | `grep -oE "'(fill\|click\|attach_file)'" tests/e2e/pc01/journey/write.mjs \| sort -u` → exactly those three; no `sign_in` anywhere under `tests/e2e/pc01/journey/` |

### One premise of the brief is wrong, and one of `D-83`'s is wrong

**`D-83` says the eleven sentences are "verified only against a live stand" by
`refusals.mjs`. They were verified by nothing, anywhere.** Measured before touching it:

```
$ node tests/e2e/pc01/journey/refusals.mjs --origin http://127.0.0.1:31500
Error: click form button[type="submit"] [text="Create"]: no element matches it
    at Page.click (cdp.mjs:643:31)
    at async seedProject (refusals.mjs:214:10)
    at async main (refusals.mjs:445:18)
rc=1
```

It died **before driving a single fixture**. `refusals.mjs` addressed four controls by
English word — `Create`, `Upload`, `Retry`, `Chosen: ` — and the screens say `Создать`,
`Загрузить`, `Повторить…` and render the chosen-file line in `.am-form__chosen`. It would
also have had no session. So the row's "a real check that is not in `make gate`" was a
statement about a script that had not run since the application was translated.

**This is `W28-GUARD`'s own lesson, on the half it did not move.** That session moved the
six refusal *expectations* into `manifest.json` because a script's own source is
unreadable to the gate, and left the *controls* behind. The controls are what rotted.

**And two of the four checks in `refusals.mjs` could not have failed even so.** The retry
check tested `innerText.startsWith('Retry')` on a screen whose retry says
`Повторить с тем же ключом`, so it was vacuous; and `submitDisabled` was `null` rather
than `true`/`false` whenever the label did not match, which reads as "still pressable".

**The rot is wider than one script: it is every English control literal in `tests/e2e`
that `make gate` does not read.** Found by running the documented proofs rather than by
grepping for it:

| where | pressed | screen says | consequence |
|---|---|---|---|
| `refusals.mjs` | `Create`, `Upload`, `Retry`, `Chosen: ` | `Создать`, `Загрузить`, `Повторить…`, `.am-form__chosen` | died before driving anything |
| `fixtures/redden-write.manifest.json` | `Create`, `Upload`, `Start run` | `Создать`, `Загрузить`, `Запустить прогон` | **5** findings where the README documents **6**, and one of the five is the dead click rather than a declared wrong |
| `fixtures/redden-write-bound.manifest.json` | same three, **plus** `expects_rendered` `Created`, `This version`, `Run` | `Создан…`, the version panel, the run screen | stopped at step 1 and **never reached the 1 ms bound the fixture exists to demonstrate**. `Run` is `D-61`'s own defect, still in this file after `W41-BLIND` removed it from the real manifest |
| `fixtures/w28-live/*.manifest.json` (×4) | same three | same three | nothing drives them; reported in §6 |

**`manifest.json` did not rot, and the reason is the whole lesson**:
`test_every_control_the_write_half_presses_still_exists_in_the_application` reads it at
gate time. The fixtures are exempt from that guard **by design** — their deliberate wrongs
must not redden `make gate` — and the exemption is exactly what let them go stale. The two
the README names as proofs are corrected and re-measured in §7; the four nobody drives are
left alone and reported.

### A third premise, mine, that I had to correct mid-flight

`Network.getCookies` with no `urls` answers **for the frames of the current page**, so on
`about:blank` — where a profile sits before its first navigation, which is exactly where
`D-16`'s check has to be taken — it answers `[]` however many cookies the profile holds.
The first repaired run reddened all three routes it reached with *"its browser started
with cookies [(none)] and the journey handed it [am_session]"* while the cookie was in
fact present and working. `Storage.getCookies` answers for the browser, which is the thing
the question is about. Recorded in `cdp.mjs` beside the call.

---

## §1 J1 — `D-92`: the walk, before

Lane `gate-w44a`, provisioned first: `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`
→ `bootstrap OK`; `npm --prefix web ci` → `added 184 packages`.

At `2b3ac89` (the tree as dispatched), against the owner's stand:

```
$ npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:31500 --phase all
write half: 3 step(s), fixture fixtures/synthetic/ar/ar_baseline.pdf

RED create-project   api=2

e2e:pc01: stopping the write half at 'create-project'. The steps after it were NOT checked.

ok  root       200  api=1 auth=0 console=0
RED projects   200  api=1 auth=0 console=0

e2e:pc01: stopping at 'projects' -- the walk cannot continue without project_uid.
The routes after it were NOT checked.

write steps checked: 1/3
routes checked: 2/15

e2e:pc01 FAILED -- 9 finding(s):
  - create-project: createProject answered 401 Unauthorized and this step declares 201.
    body: "{...\"error_code\":\"authentication_required\",\"message\":\"Этот запрос требует
    входа. Откройте экран входа и войдите под своей учётной записью.\"...}"
  - projects: rendered no link matching ^/projects/(prj_%ID%)$ so the journey cannot reach
    project_uid. Links offered: /projects | /knowledge-base | /account/password | /blocks |
    /optimisation | /logs | /workers | /login
  - only 2 of 15 routes were reached; an unfinished walk is not a pass
rc=1
```

**`D-92` reproduced exactly: write 1/3, routes 2/15.**

**An instrument note, and it is `OPERATING_CONSTRAINTS.md` §4.62 live.** The harness
reported this run as *"completed (exit code 0)"*. The run's own `$?`, redirected to the
log, was **1**. Every verdict in this report is read from the log, never from a
notification.

---

## §2 J1 — the design decision and its argument

**Decision: one sign-in, driven through the application's own screen, carried as one
cookie value into every cold browser.** `tests/e2e/pc01/journey/session.mjs`, plus a
`session` section in `manifest.json`.

### Why not the other two shapes

**`--session <cookie>`**, `D-92`'s second named candidate: it puts a live credential on a
command line, where it reaches the process table, the shell history and every transcript
of the run — and it moves the sign-in *out* of the instrument, so the journey would stop
checking the screen a reviewer actually signs in on, which is one of the fifteen.

**A fresh sign-in inside every route's browser**: it would put the sign-in navigation and
its `POST /bff/v1/session` inside **every** route's recorded exchanges, and `journey.mjs`
reddens on undeclared traffic at the seam on purpose — so every route would then have to
declare or filter traffic that has nothing to do with it. And it makes each route's
verdict depend on `/login` working, so a broken sign-in screen would redden fifteen routes
and name none of them. One sign-in fails in one place and says which place.

### Which property I built, and how a reader can tell

The brief is right that a session carried deliberately and state leaking between routes
look identical in a passing run. Four things distinguish them here, and three of them are
checks rather than prose:

1. **The cookie is obtained once, before the walk, and the same value goes to every
   route.** Route 15's browser receives exactly what route 1's received. **The test a
   reader can run:** any route in isolation behaves the same as in the walk, because no
   route's input depends on any earlier route having run. Leaking state fails that test by
   definition.
2. **Nothing is ever read out of a route's browser.** `session.mjs` is the only caller of
   `page.cookieFor`, and it is called once, in the sign-in browser. `grep -n 'cookieFor'
   tests/e2e/pc01/journey/*.mjs` returns the definition and that one call.
3. **Every profile reports the jar it held before its first navigation, and the walk
   asserts it per route.** It is printed on every line — `jar=[am_session]` — and a
   mismatch is a finding naming `D-16`. If a browser were ever reused, a route would start
   with whatever the previous route's screen had set, and that line would show it.
4. **`cdp.mjs` still exports `withColdBrowser` and nothing else.** There is no `Page`
   handed out, no jar shared between calls, and the two new options are *values the caller
   states*. `test_the_instrument_still_reads_back_the_jar_every_route_started_with` in the
   conformance guard reddens if either half of this is deleted.

Put the other way: the identifiers `project_uid`, `document_uid`, `version_uid`, `run_id`
have always been carried deliberately between routes, and nobody calls that leaking —
because they are extracted from a *rendered link* and passed as explicit values rather
than inherited by a shared browser. The session is one more explicit value of the same
kind, and it is the one the walk can prove it did not accumulate.

### The credential

`E2E_PC01_LOGIN` and `E2E_PC01_PASSWORD`, read at run time, **no default and no file**.
The manifest names the *field* each action fills — `from: "login"`, `from: "password"` —
and never a value.

That is guarded rather than promised:
`test_no_session_action_carries_a_credential` fails `make gate` if a session action ever
carries a literal `value`, and
`test_the_journey_reads_its_credential_only_from_the_environment` fails if `session.mjs`
grows a `?? 'password'`-shaped fallback. The seeded account that
`db/migrations/versions/20260922_0006_app_user.py` publishes in its own docstring is
deliberately **not** a default here: a default would be correct for one deployment and
would teach the next reader that the journey knows a password.

The password is never recorded either. `cdp.mjs` records request bodies — `D-5` is a
`POST` nobody kept — so `session.mjs` redacts the one body that carries it, **by address**
(`/bff/v1/session`) rather than by searching for the password's text, because
`/account/password` is a real route of this application and a journey that blanked every
string containing the word would corrupt its own evidence. Verified on the envelope:
`/password=/` does not match, and the cookie's **value** is nowhere in it — only its name
and its attributes, the same rule `cdp.mjs` applies to `Authorization`.

### Failing loudly

**No credential** — exit `2`, before any browser starts:

```
$ npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:31500 --phase all
e2e:pc01: no credential. E2E_PC01_LOGIN and E2E_PC01_PASSWORD are not set.
  E2E_PC01_LOGIN=<login> E2E_PC01_PASSWORD=<password> \
    npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:PORT
The BFF answers 401 without a session (wave 34, by design), so a run without a
credential walks two routes of fifteen and reports on thirteen it never opened.
That is D-92 and it survived nine waves, so this is a hard failure and not a skip.
rc=2
```

**A credential the stand refuses** — exit `1`, nothing walked:

```
$ E2E_PC01_LOGIN=no-such-account-w44-journey E2E_PC01_PASSWORD=irrelevant \
    npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:31500 --phase all
sign-in: FAILED

e2e:pc01 FAILED -- the journey could not sign in, so NOTHING was walked.
0 of 15 routes and 0 of 3 write steps were checked. This is D-92's own failure mode
and it is reported rather than survived:

  - session: after 1 ms (bound 30000 ms) the browser was at "/login?refusal=credentials"
    and not at /projects. The screen refused with 'credentials': "Вход не выполнен…"
  - session: the exchange set no 'am_session' cookie, so there is nothing to carry into
    the walk. Cookies the profile holds: (none)
rc=1
```

The wait watches for the landing **or** the refusal, so a refusal is reported in 1 ms
rather than after the 30 s bound: a refusal is an answer, not a timeout. (A login that does
not exist was used on purpose for the second and third runs of this proof —
`W40-LIMIT` locks an account out after five consecutive failures, and locking the stand's
only account out of a read-only stand would be a poor way to end a wave.)

---

## §3 J1 — the walk, after

Same command, same stand, `E2E_PC01_LOGIN` / `E2E_PC01_PASSWORD` supplied:

```
sign-in: ok at /login -- carrying 'am_session' (HttpOnly=true, SameSite=Strict) into every cold browser

write half: 3 step(s), fixture fixtures/synthetic/ar/ar_baseline.pdf

ok  create-project   api=3 {"project_uid":"prj_01M39D9NSQWSRJVK8A85XVQJFG"}
ok  upload-document  api=4 {"project_uid":"prj_...","version_uid":"ver_01M39DAK3X8ZWDJJFZ7Y9RKV17"}
ok  start-run        api=5 {"project_uid":"prj_...","run_id":"run_01M39DBF3NNTZEMTE13N1M28RW"} terminal=published in 1512ms/150000ms

ok  root           200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  projects       200  api=1 auth=0 console=0 jar=[am_session] w=765/780 {"project_uid":"prj_..."}
ok  project        200  api=1 auth=0 console=0 jar=[am_session] w=765/780 {"document_uid":"doc_..."}
ok  document       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"version_uid":"ver_..."}
ok  version        200  api=2 auth=0 console=0 jar=[am_session] w=765/780 {"run_id":"run_..."}
ok  comparison     200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  run            200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  review         200  api=5 auth=0 console=0 jar=[am_session] w=765/780
ok  sign-in        200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  knowledge-base 200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  change-password 200 api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  blocks         200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  optimisation   200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  logs           200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  workers        200  api=0 auth=0 console=0 jar=[am_session] w=780/780

envelope: /root/w44jrn/tests/e2e/pc01/journey/.out/journey.json
write steps checked: 3/3
routes checked: 15/15
e2e:pc01 OK
rc=0
```

| | before | after |
|---|---|---|
| write steps checked | **1/3** | **3/3** |
| routes checked | **2/15** | **15/15** |
| findings | 9 | 0 |
| exit code (from `$?` after a redirect) | 1 | **0** |

**`e2e:pc01 OK` for the first time since wave 34.** The run took **20 min 55 s** wall
clock against the 248 s `W22-E2E` measured for 3 write steps and 7 read routes: the walk
is now more than twice as long (15 routes), each route does an extra layout measurement,
and the host had another lane's work on it (`OPERATING_CONSTRAINTS.md` §4.6 — a wall clock
on a shared host is evidence about the machine). The envelope is **12.4 MB** and **655
exchanges**, against 5.3 MB and 206.

**What this buys, stated as the thing that is now checked rather than as a number.** The
five screens wave 43 added were checked only statically — that a page module exists, that
the segments match, that the operation is real. All fifteen are now driven: each answers
`200` from a cold profile, renders a non-empty body, throws no uncaught exception, makes
exactly the calls the manifest declares and no others, presents no `Authorization` header
of its own, and — new in this wave — **has no call on the `/bff/v1` seam that answered
`>= 400`**. That last check is what makes a session that dies mid-walk loud instead of
invisible; the read walk had never had it, which is half of why `D-92` presented as a
missing link rather than as thirteen unopened screens.


---

## §4 J2 — `D-83`: the eleven sentences, in three honest categories

`D-83` asks the right question and states one premise that is false. **The false premise
is measured in §0: `refusals.mjs` could not drive at all**, so "verified only against a
live stand" described a script that had not run since the screens were translated. Both
halves of `D-83` were therefore "verified by nothing".

The repair is in two parts. `refusals.mjs` now signs in (`D-92` reaches it too) and reads
its four controls from `manifest.json` rather than from its own source — which is
`W28-GUARD`'s move applied to the half it left behind. Driven today:

```
$ E2E_PC01_LOGIN=… E2E_PC01_PASSWORD=… \
    node tests/e2e/pc01/journey/refusals.mjs --origin http://127.0.0.1:31500
signed in at /login, carrying 'am_session' into every cold browser
seeded project prj_01M39DVRD71ZMFPF0JFTMF8Y53

-- not_a_pdf.txt        (ENV-PDF)       as declared in 22511 ms  refused by: client
-- companion_archive.zip (ENV-PDF)      as declared in 29738 ms  refused by: client
-- oversize.pdf         (ENV-SIZE)      as declared in 27594 ms  refused by: client
-- encrypted.pdf        (ENV-ENCRYPTED) as declared in 28278 ms  refused by: server
                                        POST …/documents -> 422
-- image_only.pdf       (ENV-TEXT)      as declared in 28640 ms  refused by: server
                                        POST …/documents -> 422
-- too_many_pages.pdf   (ENV-PAGES)     as declared in  7853 ms  refused by: server
                                        POST …/documents -> 422

6 fixture(s) driven, 0 finding(s), 204965 ms
rc=0
```

### The sentences, one line each, in three categories

**"Verified in the gate" means: a browser inside `make gate` asserted that a screen
rendered it. By that meaning the answer for all twelve is no, and it cannot be yes** —
the gate has no browser, no built web image and no bound port, which is the stated cost of
keeping it stack-free. What the gate *does* check is in the third column, and it is not
the same claim.

| # | case | sentence | what the gate checks | live | was |
|---|---|---|---|---|---|
| 1 | `not_a_pdf.txt` | `не является PDF` | authored by the pressed control's closure | ✅ driven | nothing |
| 2 | `not_a_pdf.txt` | `Ничего не отправлено` | authored by the closure | ✅ driven | nothing |
| 3 | `companion_archive.zip` | `не является PDF` | authored by the closure | ✅ driven | nothing |
| 4 | `companion_archive.zip` | `Ничего не отправлено` | authored by the closure | ✅ driven | nothing |
| 5 | `oversize.pdf` | `Ничего не отправлено` | authored by the closure | ✅ driven | nothing |
| **5a** | `oversize.pdf` | **`Этот файл больше, чем`** | authored by the closure | ✅ driven | **not declared at all** |
| 6 | `encrypted.pdf` | `выходит за допустимые ограничения` | authored by the closure | ✅ driven | nothing |
| 7 | `encrypted.pdf` | `not_encrypted` (envelope) | is a substring of the declared `constraint` — **data against data** | ✅ driven | nothing |
| 8 | `image_only.pdf` | `выходит за допустимые ограничения` | authored by the closure | ✅ driven | nothing |
| 9 | `image_only.pdf` | `every_page_has_extractable_text` (envelope) | substring of the declared `constraint` | ✅ driven | nothing |
| 10 | `too_many_pages.pdf` | `выходит за допустимые ограничения` | authored by the closure | ✅ driven | nothing |
| 11 | `too_many_pages.pdf` | `page_count` (envelope) | substring of the declared `constraint` | ✅ driven | nothing |

**Category 1 — verified in the gate: zero of twelve, and the number cannot move without a
browser in the gate.** Saying "eight are checked in the gate" would be the optimistic
count `D-83` warns about: *authored by the control's import closure* is a real check (it
reddens on a reworded panel and `prove_the_guard_can_fail.py` shows it doing so twice),
but it answers "are these the application's own words" and not "does a screen render
them". The three envelope sentences are weaker still — they are checked against a
`constraint` string declared three lines above them in the same file.

**Category 2 — verified only against a live stand: all twelve, as of today.** `refusals.mjs`,
`0 findings`. This is a real check and it is **not in `make gate`**, so it cannot redden a
merge. That has not changed and this wave does not claim it has.

**Category 3 — verified by nothing: all twelve, before today**, and that includes the
eight `D-83` credited to the live drive.

### Two things worth having found, beside the count

**`ENV-SIZE` had no rule-specific sentence at all, and now does.** `W41-BLIND` correctly
removed `25 MiB` from that case — the upload panel prints `Не более 25 MiB.` before any
file is chosen, so it could not fail — and left the case asserting only
`Ничего не отправлено`, which says *a* refusal happened and not *which rule* was broken.
`Этот файл больше, чем` is authored in
`web/src/entities/document-version/model/upload-envelope.ts` and rendered by the
`too_large` pre-check and nothing else. The size itself is interpolated, so the declared
sentence stops where the template does: declaring the number back would be declaring a
value the source does not author.

**Three of the twelve carry no rule-specific information and that is correct.**
`выходит за допустимые ограничения` is `UnsupportedState`'s generic title and is identical
for all three server refusals — and is also what a *client* refusal renders. It is
evidence that a refusal panel appeared; the rule is carried by the envelope sentence
beside it. The manifest already splits them for exactly this reason, and the split is
worth stating rather than leaving as an apparent redundancy.

**And two of `refusals.mjs`'s own checks were vacuous.** The retry check tested
`innerText.startsWith('Retry')` on a screen whose retry says
`Повторить с тем же ключом` — it could not fire. It now reads
`.am-state__action button`, which is structure the application owns rather than a word.
And `submitDisabled` came back `null` rather than `true`/`false` whenever the label did
not match, which the check read as "still pressable"; the finding now distinguishes
"still pressable" from "not on the screen at all".

---

## §5 J3 — `D-93`: the width assertion, and it seen red

**The assertion.** `document.documentElement.scrollWidth <= window.innerWidth`, on every
route, at the manifest's declared `viewport` — **780 × 900**, deliberately the same width
`W43-JUDGE-B` measured the regression at, so the two measurements are comparable. It lives
in `width.mjs`, which `journey.mjs` and the proof both import: a proof that exercises a
second copy of the assertion proves nothing about the first
(`OPERATING_CONSTRAINTS.md` §12).

`innerWidth` and not `clientWidth`, stated once rather than discovered later: a vertical
scrollbar makes `clientWidth` smaller than the viewport, so a page exactly filling the
viewport would redden for a scrollbar rather than for a layout. The looser comparison is
the one that cannot produce a false red — and the numbers below show the difference is
real, 765 against 780 on every scrolling screen.

**The fifteen routes, green** (from the run in §3): `scrollWidth` is 765 on the nine
screens with a vertical scrollbar and 780 on the six without; `innerWidth` is 780 on all
fifteen. No route overflows.

### Seen red

```
$ node tests/e2e/pc01/journey/prove_the_width_assertion_can_fail.mjs \
    --origin http://127.0.0.1:31500

scratch copy: /tmp/w44-journey-width-DcYxyT/globals.reverted.css
  .am-app__bar in the repository declares 'flex-wrap: wrap;'; the copy declares no flex-wrap at all
  `nowrap` is flex-wrap's initial value, so that block computes to `nowrap`. The injection
  below is required to read back exactly that.

ok  root             before  765/780 (wrap)  ->  after  839/780 (nowrap)
      root: the screen scrolls sideways at the declared width. scrollWidth 839 > innerWidth 780
      (clientWidth 765), overflowing by 59 px. 11 element(s) cross the right edge; widest:
      <div.am-theme> right=839 width=71; <button.am-theme__option> right=836 width=32;
      <svg> right=826 width=12; <path> right=824 width=9;
      <button.am-theme__option> right=802 width=32.
      D-93: AppFrame is global, so this is every screen in the product and not this one.
ok  projects         before  765/780 (wrap)  ->  after  839/780 (nowrap)
ok  sign-in          before  780/780 (wrap)  ->  after  839/780 (nowrap)
ok  knowledge-base   before  765/780 (wrap)  ->  after  839/780 (nowrap)
ok  change-password  before  780/780 (wrap)  ->  after  839/780 (nowrap)
ok  blocks           before  780/780 (wrap)  ->  after  839/780 (nowrap)
ok  optimisation     before  780/780 (wrap)  ->  after  839/780 (nowrap)
ok  logs             before  780/780 (wrap)  ->  after  839/780 (nowrap)
ok  workers          before  780/780 (wrap)  ->  after  839/780 (nowrap)

routes measured: 9/9 placeholder-free route(s) at 780x900

prove_the_width_assertion_can_fail OK -- every route was green at 780 px with the repair
and red with it reverted. D-93's assertion has been seen failing.
rc=0
```

**The route it names: all nine it can open on its own**, which is the point rather than a
flourish — `AppFrame` is global, so the class is product-wide and an assertion that
reddened on one screen would be under-reporting. The six routes behind a captured
identifier are not in this probe because it is not the walk; the assertion itself runs on
all fifteen.

**The number is 839.** That is `W43-JUDGE-B`'s measured figure, reproduced exactly, per
route, from a scratch copy of the stylesheet with wave 43's one-line repair removed — and
it is **59 px over** the declared viewport. The widest offender is `.am-theme`, the
right-hand theme cluster, which is where the bar runs out of room.

### Why an injected rule is the same mutation as the scratch copy, and not merely near it

The deployed stand is read-only to this session; its image was built from the repaired
tree and cannot be rebuilt to carry the defect. So the probe joins the two halves rather
than asserting they are equivalent:

1. it writes the scratch copy, and **checks that the copy's `.am-app__bar` block then
   declares no `flex-wrap` at all** — if removing the line had left a second declaration,
   it exits 2 and says so;
2. `nowrap` is `flex-wrap`'s initial value, so that block computes to `nowrap`; and the
   probe **reads the computed style back off the live bar on both sides** — `wrap` before,
   `nowrap` after — and reddens if either reading is not what it declares. The two halves
   meet at the computed value, which is what the browser lays out from.

It also fails if a route was **already** overflowing before the mutation, because a route
that was red to begin with proves nothing about the assertion.

### One observation the measurement produced and the verdict does not use

The `run` route reports **13 elements crossing the right edge while `scrollWidth` is 765**
— no overflow. Those boxes are clipped by an ancestor's `overflow`, so they extend past
the viewport without making the page scroll. The offender list is **diagnostic only**: the
verdict is `scrollWidth` against `innerWidth` and nothing else. Worth writing down because
a reader meeting `offenderCount: 13` in a green envelope would reasonably ask.

---

## §6 Outside the grant: reported, not repaired

### 1. `/projects` tells a reviewer, just after they sign in, that there is no authentication

**The most serious thing this wave found, and it was found by driving rather than by
reading.** The landing screen's own subtitle, quoted from the envelope of a run that had
signed in thirty seconds earlier:

```
web/src/_pages/projects/ui/projects-page.tsx:18
  subtitle="Один локальный проверяющий. Без аутентификации, ролей и разделения на организации."

rendered, on /projects, in a browser holding a live session:
  "Проекты
   Один локальный проверяющий. Без аутентификации, ролей и разделения на организации."
```

A reviewer types a password at `/login`, is issued an `HttpOnly` session, is redirected to
`/projects` by the application itself — and the first sentence under the heading says the
product has **no authentication**. It has had authentication for nine waves.

It is `D-23`'s shape with the direction `OPERATING_CONSTRAINTS.md` §4.7 warns about: not a
stale count that a reader discards, but a **false statement about a security property**,
on the screen every signed-in reviewer lands on. It stops short of §4.7's worst case only
because it instructs nobody to do anything. `W43-JUDGE-B` had to raise a session by hand
to see any of these screens; the journey now lands here on every run, which is why it
turned up today.

**Not repaired: `web/src` is `W44-SEE`'s.** The sentence and the two clauses after it
(`roles`, `separation by organisation`) need re-checking together against what wave 34 and
`W40-LIMIT` actually shipped — roles and multi-tenancy may still be absent, and the
correct repair is not simply deleting the first clause.

### 2. A **fourth** English string on a reviewer's screen — `D-82`'s own missing one

`D-82` names three, all `LoadingState what="the …"` props, and says in its last line that
nothing in the gate could *"catch the fourth one"*. **Here it is, measured in a browser on
the deployed stand today** rather than grepped:

```
web/src/features/upload-document/ui/upload-document-form.tsx:105
  <p className="am-form__chosen">Chosen: {file.name} · {formatBytes(file.size)}</p>

rendered, from the refusal drive's envelope, on a Russian screen:
  "Chosen: not_a_pdf.txt · 489 B"
  "Chosen: oversize.pdf · 26.0 MiB"
  "Chosen: too_many_pages.pdf · 64.9 KiB"
```

It is in a branch selected by `useState` (`file !== null`), which is the same class
`D-82` says no static pass reaches — and it is on the upload screen, beside a refusal, in
front of the reviewer `R-18` is about. **Not repaired: `web/src` is `W44-SEE`'s.**

`D-82`'s three are confirmed unchanged and all three are in `mutation.isPending`
branches: `create-project-form.tsx:99` (`the new project`), `upload-document-form.tsx:135`
(`the upload`), `start-run-control.tsx:53` (`the run request`). Each renders as a
**mixed-language sentence** — `LoadingState` builds `Загрузка: ${what}…`, so a reviewer
sees `Загрузка: the upload…`, not an English panel.

**And `D-82`'s row is a request for an instrument rather than for an edit. This wave is
half of that instrument.** The journey reaches `useState` branches — the `Chosen:` line
above came out of its envelope — and the refusals drive presses the control that enters
the `isPending` branch. What is still missing is an *assertion*: neither instrument runs
inside `make gate`, so reaching the branch is not yet reddening on it. `W44-SEE` should
know that the reach now exists before deciding what `D-88`'s census can be widened to.

### 3. `CURRENT_STATE.md` describes a defect this branch repairs

The paragraph at `docs/program/CURRENT_STATE.md:129-134` says the journey *"stops at route
2 of 15"* and that it is *"written for an application that has no authorization"*. Both
become false when this branch merges. It is outside `allowed_paths` and is **reported, not
edited** — and it is the file `AGENTS.md` §1 makes every agent read first, which is
`D-79`'s exact shape, so it should not wait for a documentation pass. The measured
replacement is §3 of this file: write 3/3, routes 15/15, `e2e:pc01 OK`.

The same paragraph says *"the fourteen addresses answer"*; the manifest declares **fifteen
routes** and all fifteen answered.

### 4. The wave-28 live fixtures have no `session` section

`tests/e2e/pc01/journey/fixtures/w28-live/*.manifest.json` — four of them — predate the
sign-in. They are inputs for a provider-mode drive nobody has run this wave, they are not
named by any documented proof command, and a run of one now fails loudly with *"this
manifest declares no `session` section … That is D-92"*. Left alone deliberately: adding a
session to a manifest nobody drives is speculative maintenance, and the failure names its
own fix. The three `redden*` fixtures, which the README's proof commands **do** name, were
given one and re-measured (§7).

### 5. The stand has accumulated the journey's projects

Every full run creates one project, uploads a PDF and publishes a run; every refusal drive
creates one more. The walk's own `projects` screen listed **20** by the end of today.
Nothing here deletes anything — the journey has never had a teardown and this wave did not
give it one — but the integrator and the cross-judges should know the stand's project
count is now a function of how many times the journey has been driven, not of the
product.

### 6. A blind spot in the `D-61` sentence guard, found by walking into it

`authored_strings`'s JSX arm is `>([^<>{}\n]+)<`: it requires the text to sit between the
two angle brackets **on one line**. This repository formats a labelled button over four
lines, so `Загрузить` is authored by `upload-document-form.tsx` and **invisible to that
helper**. The failure mode is conservative — a false *red*, not a false green — so nothing
is unsafe today; the consequence is that a sentence rendered as multi-line JSX text cannot
be declared in `expects_rendered`.

**Not repaired**: widening `_LITERAL` would loosen the `D-61` sentence guard that shares
it, which is the wrong direction for a guard three waves of work went into. The new label
check works around it by scoping to the control module's closure and matching on a word
boundary, and its control records the blind spot as a test.

---

## §7 What was run, at which commit

Every verdict below was read from a **file** — the command redirected, `$?` read after the
redirect, and the instrument's own last line asserted. Never from a harness status:
`OPERATING_CONSTRAINTS.md` §4.62, and the harness handed this session *"exit code 0"* over
a run whose `$?` was `1` at least twice today.

| check | commit | result | log |
|---|---|---|---|
| `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` | `2b3ac89` | `bootstrap OK` | `/root/w44a-bootstrap.log` |
| `.venv/bin/python -c "import boto3"` | `2b3ac89` | boto3 1.43.90, printed by the bootstrap probe | same |
| `npm --prefix web ci` | `2b3ac89` | `added 184 packages` | `/root/w44a-npmci.log` |
| journey, **before** | `2b3ac89` | `rc=1`, write **1/3**, routes **2/15**, 9 findings | `/root/w44a-journey-before.log` |
| `refusals.mjs`, **before** | `2b3ac89` | `rc=1`, threw on `[text="Create"]`, **0 fixtures driven** | `/root/w44a-refusals-before.log` |
| journey, no credential | `48eee0c` | `rc=2`, nothing started | `/root/w44a-nocred.log` |
| journey, credential refused | `48eee0c` | `rc=1`, **0/15 routes**, 0/3 write steps | `/root/w44a-badcred2.log` |
| journey, **after** | `48eee0c` | `rc=0`, **`e2e:pc01 OK`**, write **3/3**, routes **15/15**, 0 findings | `/root/w44a-journey-after2.log` |
| `prove_the_width_assertion_can_fail.mjs` | `71c27ed` | `rc=0`, 9/9 routes green→red, **839 vs 780** on every one | `/root/w44a-width-proof.log` |
| `refusals.mjs`, **after** | `71c27ed` | `rc=0`, **6 driven, 0 findings**, 204 965 ms | `/root/w44a-refusals-after.log` |
| `pytest tests/e2e/test_pc01_journey_conformance.py` | `a3b8ee6` | **78 passed** | `/root/w44a-conformance.log` |
| `prove_the_guard_can_fail.py` | `12b8b14` | **36 mutations, 36 reds, 0 vacuous**; restored → 78 passed | `/root/w44a-prove-guard.log` |
| `redden.manifest.json --phase read` | `12b8b14` | `rc=1`, **5 findings, routes 3/4** — the documented figures | `/root/w44a-redden-read.log` |
| `redden-write.manifest.json --phase write` | `049a672` | `rc=1`, **6 findings, write 1/3** — the documented figures, restored | `/root/w44a-redden-write2.log` |
| `redden-write-bound.manifest.json --phase write` | `049a672`+ | `rc=1`, **4 findings**, the first *"the run did not reach a terminal within the stated bound of 1 ms … still rendering 'in_flight' after 503 ms"*, plus the `202` declared as `200` and `state` declared as `published`. Steps now **3/3** rather than 1/3 | `/root/w44a-redden-bound2.log` |
| `redden-refusals.json` via `refusals.mjs --cases` | `12b8b14` | `rc=1`, 2 driven, **7 findings** | `/root/w44a-redden-rest.log` |
| **`make gate`** | **`3e224c0`** | **`GATE OK: battery, foundation, frontend and whitespace all pass`**, and `GATE_EXIT=0` from `$?` after the redirect. Battery **2466 passed**, 5 skipped, 169 subtests, 778.64 s; foundation **35 passed**; frontend **1085 passed in 75 files**; `tsc --noEmit` clean | `/root/w44a-gate.log` |
| `pytest tests/e2e --ignore=tests/e2e/pc01` | `049a672` | 89 passed, 8 errors — all eight `p02`, all `connection refused` on `127.0.0.1:56290`, i.e. the lane's PostgreSQL was not up. Unrelated to this branch; `make gate` brings it up | `/root/w44a-e2e-py.log` |

### The gate's figures against wave 43's

| | wave 43 close | this branch | why |
|---|---|---|---|
| battery | 2442 | **2466** | `+24`, and they are accounted for exactly: `tests/e2e/test_pc01_journey_conformance.py` went from **54 to 78** tests — the session section, the viewport, the refusal controls and their controls |
| foundation | 35 | **35** | unchanged |
| frontend | 1085 in 75 files | **1085 in 75 files** | unchanged, and it must be: `web/tests/**` is `W44-SEE`'s and this branch does not touch it |

**And the figure this wave did not move is the one `D-93` is about.** 1085 frontend tests
still cannot express a width, and nothing here makes them able to — the assertion is in
the journey, which `make gate` cannot run. What changed is that the class now has *an*
instrument, with a proof that it reddens. `D-93`'s repair and its residue are different
things and this report does not merge them.

**One condition on that gate reading, stated rather than left to a judge to find.**
`gate-w44b` — `W44-SEE`'s lane — was up and running its own work during this run
(`docker ps`, measured). `OPERATING_CONSTRAINTS.md` §4.6 says a wall clock on a shared
host is evidence about the machine; the battery's 778 s is therefore not comparable with
wave 43's numbers, and nothing in this report reads a duration as a verdict. The verdict
is the `GATE OK` line, which contention cannot produce.

## §8 For the integrator

**Nothing in `contracts/**`, `src/auditmanager/**`, `db/**`, `infra/**`, `web/src/**`,
`web/tests/**`, `web/FRONTEND_LOCK.json`, `Makefile`, `docs/program/DEBT_REGISTER.md` or
`docs/program/dispatch/**` was touched. This wave changes no contract.** Every changed file
is under `tests/e2e/**` or is `docs/program/W44-JOURNEY.md`. `package.json` and
`web/package.json` were **not** changed: the sign-in needed no new script and no new
dependency — `cdp.mjs` already spoke `Input` and `DOM`, and `Storage` and `Emulation` are
in the same stable half of the protocol.

**The journey now needs two environment variables to run at all.** Any runbook, brief or
CI step that invokes `e2e:pc01` must pass `E2E_PC01_LOGIN` and `E2E_PC01_PASSWORD`, or it
exits 2 with instructions. That is deliberate and it is the `D-92` repair's whole point,
but it is a change to how the instrument is invoked and it belongs in whatever the
integrator hands the cross-judges. The stand seeds `admin` with the password
`db/migrations/versions/20260922_0006_app_user.py` publishes in its own docstring.

**Three things for the register, none of them mine to write:**

1. **`D-83`'s standing claim is false and the row should say so** — the eleven sentences
   were not "verified only against a live stand"; `refusals.mjs` had not driven since the
   screens were translated. §0 and §4.
2. **A new row, or `D-82` widened**: `/projects` tells a signed-in reviewer there is no
   authentication (§6.1). It is the only finding here with a security-adjacent edge.
3. **`D-82` has a fourth string** and its row predicted one (§6.2). The journey now
   *reaches* `useState` and `isPending` branches; what it still lacks is an assertion
   inside `make gate`.

**For `W44-SEE`**, whose subject is `D-88`, `D-82`, `D-95`, `D-90` and `D-94`: §6.1 and
§6.2 are both in `web/src` and both are yours. The second changes what `D-88`'s widened
census can be held to, because the reach now exists even though the assertion does not.

**Run order for a judge on this branch:** `npm --prefix web ci`, then the journey with
credentials, then `prove_the_width_assertion_can_fail.mjs`, then `refusals.mjs`, then
`pytest tests/e2e/test_pc01_journey_conformance.py` and
`prove_the_guard_can_fail.py`. The first four need the stand at `127.0.0.1:31500`; the
last two need nothing.
