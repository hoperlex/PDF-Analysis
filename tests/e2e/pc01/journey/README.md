# The PC-01 browser journey

```
npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:PORT
```

Two phases, one instrument, one envelope, one exit code.

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
throwaway profile directory** — no cache, no `localStorage`, no cookies, no prior client
state. `D-16` ("no screen can reach anything after a page reload") survived four
certifications because every one of them navigated inside a single warm page.

`cdp.mjs` exposes `withColdBrowser(fn)` and nothing else: there is no API for reusing a
browser across routes, so the property cannot be lost by forgetting it.

## One origin, no credential, following the app's own links

The journey is given an origin and nothing else. It is handed no project, document, version
or run identifier: it starts at `/`, and each route's `follow` rule extracts the next
identifier from a link the page actually rendered. A screen that renders no link to its
children fails the route that needed it, and the walk stops rather than reporting on routes
it did not reach.

`T-6` puts the API credential in the BFF route handler, server-side. The journey asserts
that **no** browser request carried an `Authorization` header.

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
npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:PORT \
  --manifest ../tests/e2e/pc01/journey/fixtures/redden.manifest.json
```

**Expected: non-zero.** That fixture declares a call the screen does not make, a route that
does not exist, and a link the screen never renders. Measured on 2026-09-19 against
`http://127.0.0.1:31500`: exit `1`, five findings, `routes checked: 3/4` — the walk stops
at the broken link and says so rather than reporting the route after it as passing.

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
