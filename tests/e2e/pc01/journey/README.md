# The PC-01 browser journey

```
E2E_PC01_LOGIN=<login> E2E_PC01_PASSWORD=<password> \
  npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:PORT
```

A sign-in, two phases, one instrument, one envelope, one exit code.

**The write half** creates a project, uploads the AR PDF and starts a run — through the
app's own controls, on the public origin — then waits for the run's terminal by reading
what the run screen's own poller renders.

**The read walk** then visits all seven routes, each in a cold browser, discovering every
identifier by following links the pages render.

Exit `0` means both halves did what `manifest.json` says they do. Non-zero prints every
finding and names the envelope file. `--phase read|write|all` selects; the default is
`all`, and a phase that does not run says so on stdout and in the envelope.

**The origin must be one you may write to.** There is no default origin, and the write half
creates real state.

## Why it is here and not in someone's `/root`

`D-5` — `POST /api/v1/runs` answered 500, twice, on 2026-09-16 — is closed **not
reproducible**, permanently. The harness that saw it logged status lines only, kept no
envelope, and died with its worktree. Three browser harnesses have been built since and all
three lived outside the repository:

| harness | closed | where it is now |
|---|---|---|
| `/root/w15run-browser/journey.mjs` | `D-5` | outside the tree |
| `/root/w19shell-logs/browser/drive.mjs` | `D-16` | outside the tree |
| `/root/w19-journey/drive.mjs` | the `W19` journey | outside the tree |

This is the same instrument, committed, under the name `web/package.json` reserved for it
before it existed.

## What it records

For **every** request the browser makes, not only the ones that look interesting:

* method, URL, resource type;
* the request headers that matter, the request body, and **whether the request carried an
  `Authorization` header** — presence only, never the value;
* status, status text, the response headers that matter (`content-type`,
  `x-correlation-id`, `location`, `cache-control`, …);
* **the response body**, fetched from the browser before its process ends. That fetch is
  the step the 2026-09-16 harness skipped, and skipping it is the whole of `D-5`.

Plus, per route: what the page rendered as text, every link it offered, its console errors,
and any uncaught exception. All of it lands in `journey.json` under `--out` (default
`.out/`, git-ignored).

## The write half, and why it is the point

`D-5` was `POST /api/v1/runs` → 500, twice, through a browser, on 2026-09-16. The read walk
makes no `POST` at all, so **the journey as `W21-E2E` committed it would not have caught
it.** `D-30` is that gap; this is it filled.

Three steps, declared in `manifest.json` under `write`:

| step | at | what a user does | what is asserted |
|---|---|---|---|
| `create-project` | `/projects` | types a name, presses **Create** | `POST /projects` → `201`, `project_uid` matches the identifier pattern, the screen states what it created, no alert |
| `upload-document` | `/projects/{project_uid}` | chooses `fixtures/synthetic/ar/ar_baseline.pdf`, presses **Upload** | `POST /projects/{uid}/documents` → `201`, sent as `multipart/form-data` with `name="file"`, `ar_baseline.pdf` and `application/pdf` on the wire, the screen navigates to the published version |
| `start-run` | `/projects/{project_uid}/versions/{version_uid}` | presses **Start run** | `POST /runs` → **`202`** with `state: "queued"`, the screen navigates to run progress, and the run reaches a terminal |

Nothing is typed into a URL and no identifier is handed in: each step's address is built
from what the previous step's *screen* produced.

### The `202`, and waiting for the terminal without sleeping

`startRun` has answered `202 queued` since `W20-EXEC`: the run reaches its terminal after
the response. The journey therefore checks the **body**, not only the status — a `202` that
had already finished the work would be a different system — and then waits on the
attribute the run screen's own poller writes, `data-run-outcome`, until it leaves
`in_flight`.

That poller is the application's single `pollRunStatus` loop at its frozen 2 s/×1.5/15 s
schedule, and `polling.ts` says in its header that it deliberately has **no deadline**. So
the bound lives here, in the manifest, as `await_terminal.bound_ms` — currently **150 000
ms**. Hitting it is a **finding with every reading attached and exit 1**: never a skip,
never a pass. The bound is a floor, not a stopwatch — the wait ends at the first reading at
or after it, so a 1 ms bound reports at the first poll, around 500 ms.

Measured 2026-09-19: terminal `published` after **1 506 ms** of a 150 000 ms bound, with the
poller's own readings `running` → `published` recovered from the response bodies, and the
screen reporting `data-run-activity="stopped"` afterwards.

### Read the body, not the status

`D-28`: `/projects/<anything>` answers **200** and renders an error state, so a status code
does not tell a working screen from a failing one. Every write step therefore asserts a
response field *and* a rendered marker, and forbids the failure markers `web/src` defines
(`[data-upload-failure]`, `[data-run-failure]`, `[data-precheck-problem]`, `[role="alert"]`).
Separately, **any** call on the `/bff/v1` seam that answers `>= 400` during a step is a
finding with its correlation id and body — which is `D-5`, stated as a check.

## Cold loads

Every route is visited by a **separate operating-system browser process with its own
throwaway profile directory** — no cache, no `localStorage`, no prior client state, and
no cookies except the one the walk explicitly hands it. `D-16` ("no screen can reach
anything after a page reload") survived four certifications because every one of them
navigated inside a single warm page.

`cdp.mjs` exposes `withColdBrowser(fn, { cookies, viewport })` and nothing else: there is
still no API for reusing a browser across routes, so the property cannot be lost by
forgetting it. Both options are **values the caller states**, never values carried over
from a previous call, and `page.startedWith()` reports the jar as it stood before the
first navigation — so the property is measured per route rather than asserted here.

## One origin, one session, following the app's own links

The journey is given an origin and a login, and nothing else. It is handed no project,
document, version or run identifier: it starts at `/`, and each route's `follow` rule
extracts the next identifier from a link the page actually rendered. A screen that renders
no link to its children fails the route that needed it, and the walk stops rather than
reporting on routes it did not reach.

`T-6` puts the API credential in the BFF route handler, server-side. The journey asserts
that **no** browser request carried an `Authorization` header. That is still true and is
not what the session below is.

### The sign-in, and why the journey has one now — `D-92`

**The BFF answers `401` without a session cookie.** That has been true since wave 34, by
design. This journey was written for the application as it stood before that, so it
reached **route 2 of 15** and stopped — for nine waves, while reporting a red nobody read
as "the instrument is blind to thirteen screens".

`session.mjs` opens **one** cold browser at `/login`, types the two fields through the
browser's own editing pipeline, presses the control by its own label, and carries the
single `HttpOnly` cookie the exchange sets into every later cold browser. The manifest's
`session` section declares the screen, the controls, the exchange and the landing; the
same two checkers read it as they read everything else here.

**The credential is not in this repository and may never be.** Each `fill` names the
*field* it fills — `login` or `password` — and the value comes from `E2E_PC01_LOGIN` and
`E2E_PC01_PASSWORD` at run time. There is no default. A session action carrying a literal
`value` fails `make gate`, so the obvious shortcut is caught by a guard rather than by a
reviewer.

**A run that cannot sign in stops.** It names the sign-in as the reason, walks nothing,
and exits 1. A journey that quietly covers fewer routes is exactly how `D-92` survived
nine waves.

### A session carried deliberately is not state leaking between routes

They look identical in a passing run and they are opposite properties, so the difference
is built rather than described:

* the cookie is obtained **once, before the walk**, and the same value is handed to every
  route. Route 15's browser receives exactly what route 1's received, so no route depends
  on any route before it having run;
* nothing is ever read **out of** a route's browser. `cdp.mjs` has no jar shared between
  calls and still has no way to reuse a browser;
* every profile reports the cookies it held **before its first navigation**, and the walk
  asserts per route that this is exactly what it handed over — printed as
  `jar=[am_session]` on each line. State leaking forward would show up there as a jar that
  grows.

## The declared width — `D-93`

Wave 43's four navigation links widened `.am-app__bar` past the viewport and moved the
overflow threshold from **482 px to 839 px**, so every screen in the product scrolled
sideways on a small laptop and on every tablet. **1085 frontend tests could not see it**:
the battery renders through `renderToStaticMarkup`, which has no layout, no box and no
viewport.

Every route is now laid out at the manifest's declared `viewport` — **780 × 900**, the
width `W43-JUDGE-B` measured the regression at — and asserted:
`document.documentElement.scrollWidth <= window.innerWidth`. A finding names the route,
both numbers, the overflow in pixels and the widest boxes crossing the right edge.

`innerWidth` and not `clientWidth`, stated once: a vertical scrollbar makes `clientWidth`
smaller than the viewport, so a page exactly filling the viewport would redden for a
scrollbar rather than for a layout. The looser comparison is the one that cannot produce a
false red.

**Shown failing**, because a width assertion nobody has watched fail is one nobody can
trust:

```
node tests/e2e/pc01/journey/prove_the_width_assertion_can_fail.mjs \
  --origin http://127.0.0.1:PORT
```

It writes a scratch copy of `web/src/app/globals.css` with wave 43's `flex-wrap: wrap`
removed and checks the copy's `.am-app__bar` block then declares no `flex-wrap` at all;
`nowrap` is that property's initial value, so the block computes to `nowrap`. It then
injects exactly that on the live screens and **reads the computed style back on both
sides** — `wrap`, then `nowrap` — which is what makes the scratch copy and the injection
the same mutation rather than a claim that they are. It imports `width.mjs`, the
journey's own assertion, rather than a second copy written to agree with it.

## No dependency

`cdp.mjs` speaks the Chrome DevTools Protocol over Node's built-in global `WebSocket`
(Node 22, pinned in `web/package.json` `engines`). Nothing was added to `web/package.json`
or to `package-lock.json`.

The Chromium *binary* is an environment prerequisite, like `docker` or `npm` — not a
repository dependency. It is searched for in the usual places and `E2E_PC01_CHROME`
overrides. An absent browser is a hard failure with instructions, never a skip.

## What stops it rotting

It cannot run inside `make gate`: it needs a built web image, a bound port and a live
stack, and a gate that needs those is a gate that gets skipped.

So `tests/e2e/test_pc01_journey_conformance.py` runs **inside** the canonical battery,
with no browser and no stack, and checks `manifest.json` against the route tree under
`web/src/app` and against `contracts/api/v1/openapi.json`. Add a screen, delete one, rename
a dynamic segment, rename an operation, change a method, move the BFF mount — the gate goes
red until the journey is updated.

Since `W22-E2E` it also checks what the *write* half needs and the read half never did:
that every `#id`, every `[data-*]` marker and every control label the write section names
still appears in `web/src`; that the uploaded fixture is on disk; that each declared status
is one the contract publishes for that operation (so `startRun`'s `202` is checked against
the contract, not against taste); that every wait carries a positive bound; and that every
run state named is one `RunState` publishes.

`prove_the_guard_can_fail.py` beside this file mutates the **real** `manifest.json` ten
ways and asserts ten reds — because the controls inside the guard are pure functions over
synthetic data, and that leaves "is the check actually wired to the real tree" unproven.
Measured 2026-09-19: ten mutations, ten reds.

**The cost, stated, and narrowed rather than closed:** that guard checks *addressing* and
*existence*, not *behaviour*. A screen whose route, calls and handles are all unchanged but
which renders nothing is invisible to the gate and visible only to this journey — and an
`id` existing in `web/src` is not the same as pressing it doing anything. Keeping the gate
stack-free buys that blind spot; running the journey is what closes it.

## Proving it can fail

A journey that cannot fail is a screenshot, so the proof is a command and not a claim:

```
npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:PORT --phase read \
  --manifest ../tests/e2e/pc01/journey/fixtures/redden.manifest.json
```

**Expected: non-zero.** That fixture declares a call the screen does not make, a route that
does not exist, and a link the screen never renders. Measured on 2026-09-19 against
`http://127.0.0.1:31500`: exit `1`, five findings, `routes checked: 3/4` — the walk stops
at the broken link and says so rather than reporting the route after it as passing.
Re-measured unchanged on 2026-09-19 by `W22-E2E`.

`--phase read` is needed there and is not decoration: this fixture has no `write` section,
and a manifest with no write section is itself a **sixth finding** under the default phase
— *"the journey makes no POST at all, which is exactly what D-30 says the read half cannot
catch"*. That is the correct verdict on a manifest, and it is not what this fixture is
being used to demonstrate.

And for the write half, two more — one per property:

```
npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:PORT --phase write \
  --manifest ../tests/e2e/pc01/journey/fixtures/redden-write.manifest.json
```

**Expected: non-zero.** Measured 2026-09-19: exit `1`, **six findings**, `write steps
checked: 1/3` — a wrong status, a wrong response field, an operation the screen never
calls, text no screen renders, a forbidden element that is present, and the stop itself.
The write half stops at the first red step rather than reporting on state it never created.

```
npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:PORT --phase write \
  --manifest ../tests/e2e/pc01/journey/fixtures/redden-write-bound.manifest.json
```

**Expected: non-zero.** That fixture gives the wait for the run's terminal a bound of 1 ms.
Measured: exit `1`, **four findings**, the first being *"the run did not reach a terminal
within the stated bound of 1 ms … This is a finding, not a skip"*, with every reading it
took attached. The other three catch the `202` declared as `200` and `state` declared as
`published` when the server said `queued` — on `POST /runs`, which is the call `D-5` was.

The fixtures are not read by the conformance guard, so their deliberate wrongs never redden
`make gate`.

## What it costs to run

Measured on 2026-09-19, both halves against `http://127.0.0.1:31500`: **248 s**, exit `0`,
**206 exchanges** recorded, a **5.3 MB** envelope — 3 write steps in 83 s and 7 read routes
in 165 s.

Almost all of that is **browser startup**: in a warm browser the same navigation takes
16 ms, against 3.8–25 s for the first navigation in a fresh process. One process per route
is what makes these cold loads, so the cost *is* the property. Reusing one browser would
make the suite roughly ten times faster and would stop it being able to find `D-16`.

`E2E_PC01_SETTLE_TIMEOUT_MS` (default 10000) bounds the wait for a screen to go quiet. The
run screen polls and never goes quiet; the bound is what ends that wait, and whatever the
page had done by then is still recorded and checked.

## What this is not

This is **not** the whole of `P3-QA-01`. That lane's task specifies an idempotency spec, a
negative spec set, a leakage spec, a restart spec, a byte-identity export spec and an
anti-vacuity spec, and none of those are here. A green from a partial suite that does not
say it is partial is `D-23` in a different costume; this paragraph is the weaker mitigation
and it is stated rather than claimed solved.

### What the refusal drive's own controls cost, and it is the same shape

`W28-GUARD` moved the six refusal *expectations* into `manifest.json`, stating the cost it
was paying off: expectations in a script's own source are expectations `make gate` cannot
read. It left the *controls* — `Create`, `Upload`, `Retry`, `Chosen: ` — in
`refusals.mjs`. The application was then translated and **all four stopped matching**.

Measured 2026-09-24: `node tests/e2e/pc01/journey/refusals.mjs --origin ...` threw
`click form button[type="submit"] [text="Create"]: no element matches it` **before driving
a single fixture**. `D-83` says the eleven refusal sentences are "verified only against a
live stand" by this script. They were not: they were verified by nothing, anywhere. The
controls are declared in `manifest.json` now, the drive replays the manifest's own
`create-project` step instead of a second copy of it, and `make gate` reddens the next
time one is relabelled.

**One negative set is now partly here, and only partly.** The write half proves the happy
path of create, upload and start. It does not drive the refusals the upload screen renders
— the four negative fixtures under `fixtures/synthetic/ar/negative/` are not uploaded by
anything here, and `precheckUploadFile`'s browser-side refusal is untouched. That is the
obvious next `write` section, and it is an extension of `manifest.json` in the way this one
was not entirely (see below).

## Was the write half "an extension of `manifest.json` plus the walk"?

`W21-E2E` predicted it would be, and `D-30` repeats the prediction. **Measured: half right.**

* **The manifest part is right.** The write half is a `write` section of the same
  `manifest.json`, read by the same two checkers, and it added no new file format, no
  second source of truth and no second npm script. `web/package.json` is untouched by this
  session, and so is `web/package-lock.json` and `web/FRONTEND_LOCK.json`.
* **The "plus the walk" part is wrong.** The walk navigates and reads. Writing means
  pressing the application's own controls, and `cdp.mjs` said in its own header that it
  deliberately had no way to do that. It grew `click`, `fill`, `attachFile`, `waitFor` and
  a public `settle`, over two more protocol domains (`Input`, `DOM`) — about 200 lines. The
  walk in `journey.mjs` did not grow at all; the write half is `write.mjs` beside it.

So: one instrument, one manifest, one envelope, one exit code — but not "plus the walk".
Anyone planning the next write section should price the primitives, which now exist, and
not the walk, which was never going to do it.
