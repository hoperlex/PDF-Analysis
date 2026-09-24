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

PLACEHOLDER_J2

---

## §5 J3 — `D-93`: the width assertion, and it seen red

PLACEHOLDER_J3

---

## §6 Outside the grant: reported, not repaired

PLACEHOLDER_J6
