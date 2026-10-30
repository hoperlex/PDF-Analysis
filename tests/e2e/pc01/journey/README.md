# The PC-01 browser journey

```
E2E_PC01_LOGIN=<login> E2E_PC01_PASSWORD=<password> \
  npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:PORT
```

A sign-in, two phases, one instrument, one envelope, one exit code.

`BETA-COST-JOURNEY-1030` keeps the existing ordinary starts compatible with required cost approval.
Each declared start first presses its cost-estimate control, reads the actual successful source-bound response,
checks that the prefilled finite USD cap equals the server's recommendation and covers its estimate, then presses
the unchecked approval checkbox. The later start must carry identical version/executor-or-preset/raised-limit
options, the exact estimate digest/cap and a real command key. Failed/missing/stale endpoints or changed payloads
fail the step. Recorded mode is required unless `--allow-spend` explicitly permits live approval, including the
first core Run. No provider mode is selected or replaced by the harness.

The closed `approve_run_cost` action supports `run` and `ar_v3_group`; the latter uses «Оценить стоимость шести
проверок». The current manifest has six ordinary starts, including two historical pending AR v1 steps. Their
pending status is preserved; this compatibility update does not invent an executed six-check AR v3 journey or
activate those older steps. Browser execution of these new approval actions remains **UNVERIFIED**.

`CMP-JOURNEY-CODE-01` adds six concrete version-module steps over `fixtures/comparison/vs1`: upload five PDFs,
confirm grouping/order, prepare the matrix, compare all four adjacent transitions, open real viewer tiles,
consent to the recorded AI route, and download the resulting Markdown. The steps are part of the existing write half,
retain every older route/step, and require recorded mode even when `--allow-spend` is present. Missing recordings,
module wiring, browser controls or terminal results fail the step; they are not skipped.

`CMP-JOURNEY-C4-01` adds eight `cmp-stage-*` steps: four SP-1 PDF documents, assembly and pair confirmation,
an intentionally swapped map, a full recorded-AI/image chain, HIGH repair undo plus text recomputation and a fresh
full run, expert verdict, all three real journal groupings/exports, and a REVIEW card over a masked fragment.
The old SP-1 corpus is unchanged. R2 uses an explicitly declared synthetic derivative with one added circle so an
actual graphic crop is required, rather than assuming a text edit creates one. Manifest SHA/size fields pin both
the derivative and original source. The derivative generator is `fixtures/make-sp1-graphic.py`.

**Browser/worker execution is UNVERIFIED.** Syntax/census/conformance checks are code evidence only.

```sh
node tests/e2e/pc01/journey/comparison-conformance.mjs
```

This short command checks declarations and exact synthetic corpus bytes only. It starts no browser and gives no
journey acceptance. Run the full recorded journey tomorrow against the exact integrated candidate, keeping its
normal response/download envelope. The new `last_response` expectation checks the last recorded poll after the
bounded UI wait; `requires_idempotency_key` checks the browser's actual command header.

For the C4 recorded window, use an isolated local stand with the exact candidate's migration head and
`versions,stages` enabled on the API. The normal worker may continue ordinary Run work with comparison modules
disabled; it must not compete for these recorded comparison items, because production composition deliberately
refuses recorded C4 routes. In the same local database/S3 environment, explicitly launch the test-owned worker:

```sh
AUDITMANAGER_PROVIDER_MODE=recorded PYTHONPATH=src .venv/bin/python \
  tests/e2e/pc01/journey/c4_recorded_worker.py --local-synthetic-only --seed-route \
  --receipts /tmp/c4-synthetic-receipts.jsonl
```

This helper requires loopback DB/S3 endpoints, uses real profile/engine/queue/spend code and an explicit
source-bound **synthetic** reply fixture. It does not replay a real model's answer and does not claim an engineering
conclusion. It never imports a live model adapter. Unknown request schemas fail. Actual PNG byte digests and the
request/source/run identity are written to the receipt file; GRAPHIC replies without source images fail.
It claims stage AI and shared deterministic intake/profile work only. The six preceding version-module steps
retain their existing recorded-provider prerequisite; this helper does not supply version-AI recordings.

Set `E2E_C4_RECORDED_RECEIPTS=/tmp/c4-synthetic-receipts.jsonl` in the journey process. The eight C4 phases use
the existing signed-in browser and project captured by the core steps. A focused `--steps` run must include the
project/core Run prerequisites (or their explicit seed) and remains PARTIAL, exactly as the maintained harness
already reports. `--allow-spend` never bypasses recorded-only C4 mode. Missing mount, SP-1 proof, HIGH repair,
route/recording, consent, PNG receipt, terminal result or download is a failed step, never a skip or synthetic PASS.

Static exposure can be regenerated without launching the application:

```sh
node tests/e2e/pc01/journey/comparison-exposure.mjs
# For a new dated source snapshot, add --write --source-sha=<exact-reviewed-40-hex-SHA>.
```

The current table is 32 C3 +24 C4 operations; its prior 55-row snapshot is retained verbatim in
`fixtures/exposure-cmp-prior.md`. Auth/role/scope/cost/stream declarations remain execution UNVERIFIED until the
deferred request matrix and browser/download window run.

**The write half** creates a project, uploads the synthetic portal bundle (a ZIP), confirms the uploaded
version's stage and section (П, ПБ) and starts a run — through the app's own controls, on the public
origin — then waits for the run's terminal by reading what the run screen's own poller renders. The
section is ПБ, not АР, since `PROD-10B-JOURNEY-REBASE-01`: see "The journey's section, and the steps
that stay on АР" below.

**The read walk** then visits every route declared in `manifest.json`, each in a cold browser, discovering every
identifier by following links the pages render.

Exit `0` means both halves did what `manifest.json` says they do. Non-zero prints every
finding and names the envelope file. `--phase read|write|all` selects; the default is
`all`, and a phase that does not run says so on stdout and in the envelope.

**The origin must be one you may write to.** There is no default origin, and the write half
creates real state.

## W51 identity continuation

`identity.mjs` consumes the completed PC-01 write envelope so the newly approved expert can
record a verdict on that run. It needs an administrator in `E2E_PC01_LOGIN` and
`E2E_PC01_PASSWORD`, plus a read-only host path to the web tier's version-2 session register:

```sh
E2E_PC01_LOGIN=<admin-login> E2E_PC01_PASSWORD=<admin-password> \
E2E_PC01_SESSION_STORE_PATH=<read-only-host-path-to-web-session-register> \
  node tests/e2e/pc01/journey/identity.mjs \
    --origin <allowed-origin> --journey <out>/journey.json --out <out>/identity
```

The path is a runtime input, not a repository fixture. The script checks that the expert's
opaque cookie still names a register row after the administrator changes roles, and that the row
has disappeared after the next BFF request returns 401. It records neither the cookie nor
the generated passwords. An inaccessible register is a failure, because HTTP 401 alone
cannot prove row deletion. The output is `<out>/identity/identity.json`.

The continuation covers registration, pending status, approval with `expert`, profile,
verdict author label, role removal, revoked session, a new sign-in with a denied mutation,
archive, purge conflict, rejected/unknown generic refusal and self-archive refusal. The
last-admin conflict needs a separately prepared isolation fixture; an ordinary administrator
cannot both be the last admin and remove their own role. The human A13–A20 checklist names
the observations. `D-137` records that the continuation has not run on a built stand.

The existing `--phase all` runner and `manual-alpha-check.sh --automated` still cover the
PC-01 product journey and the six upload refusals. Run this identity continuation separately and keep
both envelopes for W51 validation; its result is not folded into the earlier release
verifier until the separate validation wave.

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

Four steps, declared in `manifest.json` under `write`:

| step | at | what a user does | what is asserted |
|---|---|---|---|
| `create-project` | `/projects` | types a name, presses **Create** | `POST /projects` → `201`, `project_uid` matches the identifier pattern, the screen states what it created, no alert |
| `upload-document` | `/projects/{project_uid}` | chooses `fixtures/synthetic/ar/bundles/ar_baseline.zip`, presses **Upload** | `POST /projects/{uid}/documents` → `201`, sent as `multipart/form-data` with `name="file"`, `ar_baseline.zip` and `application/zip` on the wire, the screen navigates to the published version |
| `classify-version` | `/projects/{project_uid}/versions/{version_uid}` | in «Стадия и раздел», chooses **П — проектная** and **ПБ**, presses **Подтвердить раздел** | `PUT /projects/{uid}/documents/{uid}/versions/{uid}/classification` → `200` echoing `project_stage: "P"` and `section_code: "PB"`, the panel switches to the confirmed classification and names the version's document (captured for the `PUT`'s path), no refusal and no conflict note |
| `start-run` | `/projects/{project_uid}/versions/{version_uid}` | presses **Start run** | `POST /runs` → **`202`** with `state: "queued"`, the screen navigates to run progress, and the run reaches a terminal |

Nothing is typed into a URL and no identifier is handed in: each step's address is built
from what the previous step's *screen* produced.

`classify-version` exists because `W59-SECTION-SEAL-01` routes a run from the version's
expert-confirmed stage and section: an unclassified version is refused with
`422 version_classification_required` before any run
exists, so a journey that went straight from the upload to **Start run** would stop at
`start-run` with a refusal (`W59-SECTION-UI-01`). The read walk's `version` route declares the
panel's `getVersionSectionReview` read for the same reason.

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

An initial `Page.navigate` GET retries only `net::ERR_NETWORK_CHANGED`, with delays of
1, 3 and 6 seconds (four attempts total). The journey records `navigationAttempts`
for successful route and write-step loads and logs each retry. Other navigation
errors fail immediately. Form actions, uploads and API writes are never replayed.

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

**The account must not be on the deployment's seeded password — `R-50`.** Since wave 47 a
credential minted for an account that has never changed its password reaches `issueToken`
and `changePassword` and nothing else: every other operation answers `403 permission_denied`
with `required_capability: password_changed`, and the sign-in screen sends that reviewer to
`/account/password` rather than to the home screen. So a journey run with the seeded
`admin`/`password` pair stops at the sign-in with *"the browser was at `/account/password`
and not at `/`"* — and that is the feature working, not the instrument breaking.

Give it an account whose password has been changed, which is what every deployment is
required to do anyway. On a stand that is the one command:

```
# through the application, as a reviewer would, on the stand's own origin
curl -s -X POST "$ORIGIN/api/v1/auth/password" \
  -H "Authorization: Bearer $(…/auth/token …)" -H 'content-type: application/json' \
  -d '{"current_password":"password","new_password":"<the new one>"}'
```

There is deliberately **no way for the journey to do this for itself**, and no flag that
skips the check. A harness that could put itself past the refusal is a harness that no
longer proves the refusal is there; `tests/integration/api/test_authorization.py` proves
the refusal, and this instrument's job is to walk the application a reviewer can actually
use.

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
Measured 2026-09-19: ten mutations, ten reds. Re-measured 2026-10-21
(`BETA-LIVE-JOURNEY-01`): 76 mutations (the night window's added), 76 reds; the ten originals now address steps by name.

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

**`PROD-10B-JOURNEY-REBASE-01` put a `classify-version` step (stage П, section ПБ) into both write
fixtures and into the four `fixtures/w28-live/` manifests**, because a run starts only for a classified
version (`W59-SECTION-SEAL-01`) and none of them could reach its run since then. The figures above
(*checked 1/3*, *six findings*, *four findings*) were measured before the step existed and are **not
re-measured**: `redden-write` still stops at its first red step, so the step is never reached there and
the tally should read `1/4` (derived, not measured); in `redden-write-bound` the three real steps now pass before the bounded one.
Re-measure both with the two commands above on a stand before quoting a figure.

**And that is also why three of them stopped proving anything.** `W44-JOURNEY` found the
two write fixtures pressing controls labelled `Create`, `Upload` and `Start run` — the
application says `Создать`, `Загрузить` and `Запустить прогон` — so each died at its first
click and reported findings about a control it could not press **instead of** the
deliberate wrongs it declares. The real manifest did not rot, because `make gate` reads
it; the fixtures are exempt from that guard by design, and the exemption is what let them
go stale. Labels corrected and all three re-measured; the figures above are this wave's.
The four `fixtures/w28-live/*.manifest.json` carry the same stale labels and no `session`
section, and are deliberately left alone — nothing drives them, and a run of one now fails
loudly naming `D-92`.

## What it costs to run

> **These figures were 2026-09-19's and this file was rewritten around them in wave 44
> without any of them being re-taken.** `W44-JUDGE-A` caught that: the paragraph said
> *248 s, 206 exchanges, a 5.3 MB envelope, 7 read routes* while the manifest carried
> fifteen. **`D-23`'s class, in a file the same wave edited 132 lines of** — prose next to
> code outlives the code, and `make gate` does not read this file.

Re-measured 2026-09-24 against `http://127.0.0.1:31500`, both halves, with the sign-in
`D-92` added: **~20 minutes**, exit `0`, a **12.8 MB** envelope — **3 write steps and 15
read routes**, each route in its own cold browser.

**The route count is the number to distrust first.** It was seven when this paragraph was
written and is 22 now, and it changes whenever `web/src/app` gains a screen — which
is exactly what `test_the_journey_walks_every_screen_the_application_offers` reddens on.
The seconds are a property of this host under whatever else it was running.

Almost all of that was **browser startup**: in a warm browser the same navigation takes
16 ms, against 3.8–25 s for the first navigation in a fresh process. One process per route
is what makes these cold loads, so the cost *is* the property. Reusing one browser would
make the suite roughly ten times faster and would stop it being able to find `D-16`.

**Superseded 2026-10-21 (`BETA-LIVE-JOURNEY-01`): the 25 s was a keyring, not a cold load.**
On Chrome 154 the first cookie-store access of a fresh profile (`Storage.getCookies`, which
`recordStartingJar` makes before the first navigation) took 25 s, because the browser asked the
desktop keyring for the key it encrypts cookies with and waited for a keyring that is not there.
`--password-store=basic` (in `cdp.mjs`) makes it 3 ms and a browser launch 0.3 s. Every browser
is still a new process with its own throwaway profile, so the property is untouched; the walk of
29 routes and the 95 write steps below now take **about five minutes** on this host.

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

## The upload refusals take a bundle, and two of their files are made on the spot

`W55B-INGEST-01`. The upload takes a portal bundle, a ZIP, and refuses a bare PDF, so the six
drives of `refusals.mjs` are now: a bare PDF (`ar_baseline.pdf`), a text file (`not_a_pdf.txt`)
and a sparse file past 250 MiB, each refused by the **browser** before a byte is sent; and
`encrypted.zip`, `image_only.zip` and a 501-page bundle, each refused by the **server** with a
constraint the screen states in Russian. The bare PDF is refused by the browser here, so the
server's own refusal of one (`portal_bundle_required`) is covered by
`tests/integration/api/test_multipart_rules.py` through the HTTP route, not by this screen.

Two of the six files are never committed: 250 MiB is too large and 501 pages exist only to sit
one past the limit. The drive builds them into a temporary directory with
`tools/fixtures/build_journey_inputs.py` (Python, standard library; `E2E_PC01_PYTHON` names the
interpreter, default `python3`) and deletes the directory afterwards. The oversize file is
sparse (it costs a few kilobytes of disk) and the tool refuses to build it on a file system that
would allocate it. `manifest.json` declares the set twice (`generated: true` on the case and
`refusals.generated.files`) and the conformance guard holds both equal to `--list`.

```
node tests/e2e/pc01/journey/refusals.mjs --origin http://127.0.0.1:PORT
```

## The night window's screens, and what a refusal is here (`BETA-LIVE-JOURNEY-01`)

The first four write steps (project, upload, classify, run) were the whole write half until the
night window of 2026-10-20 added the screens `docs/program/BETA-MATRIX-01.md` §B12 lists as never
walked live. The steps after them walk every one of those screens on a stack the journey is
allowed to write to, and **each screen has a case it must refuse**: a role the screen refuses a
control, an input it refuses, or a second identical submit that must change nothing. A step carries
`screen` (the screen it belongs to) and `case` (`action` or `refused`); the gate checks that every
night screen has both, or says why it has no refusal (`no_negative_case`).

| screen | action | refused |
|---|---|---|
| stage and section | confirm ПБ/П, pressed twice: one `PUT` | admin-only sees a sentence and no form; a stage without a section is a disabled button |
| next version | upload a bundle as version 2 and 3 | a bare PDF is refused by the browser, nothing sent |
| comparison, П→Р, carried decision | compare, carry a verdict (confirmation pressed twice: one `POST`) | admin-only gets the read-only sentence; П against Р is refused without the switch; a carried row offers nothing again |
| «Настройки анализа» | the fifteen sections and their profiles | no form, no field, no select |
| «Диспетчер», «Мои задачи» | assign (twice), take, complete | admin-only cannot take the work; an expert sees no creation form; a return needs a reason |
| price lists | upload the committed CSV (twice, ten positions); a second revision with formula-named vendors, a priceless row and an analog | admin-only sees no upload; an empty file; a table with no columns (422) |
| vendor lists | the global list (administrator), the project list | an expert is offered no global button; a row with no vendor |
| «Спецификация и цены» | the committed set's seven rows read, five matched, four counted (RUB 464278), three left out with their reasons | `price_list_missing` before any list |
| «Предложения» | a pass (twice) with the oracle's four proposals; accept; accept then reject; revise with a `=`-comment; history; the decision filter; two CSVs (BOM, 42 columns, 4 and 5 data rows, no formula cell) | a pass with no price list is refused `409 conflict`; admin-only starts nothing and decides nothing; «На доработку» needs a comment; a pass over the set with no table holds no proposal and its CSV is the header alone |
| «Оптимизация разделов», dashboard | the АР section across projects (an `ar_bound` step); the section panel counts the journey's own section, ПБ | a section with no members |
| «Нормы» | designate a snapshot, search, catalogue + filter | an unqualified snapshot has no button; an expert has no designation; an empty query |
| exports | a run's CSV and Excel (the saved file is read) | admin-only is refused `permission_denied` |
| «Очередь», «Исполнители» | pause, a waiting run, priority, cancel, re-audit, resume; worker intake off and on | an expert has no priority or pause; 500 is out of range |
| account | profile, password change, sign-out, version history | a surname is required; mismatch and wrong current password; the old pass is refused after a change |
| «Пользователи» | archive, restore, reset password | a repeat that differs |

### The journey's section, and the steps that stay on АР (`PROD-10B-JOURNEY-REBASE-01`)

`PROD-11` removes the АР v1 run, so the journey stopped confirming its sets as АР. The main flow (the three
runs, the decision, the comparisons and the carried decision, the exports, the blocks, the queue, the
dashboard, the correction of a classification) confirms **ПБ**. ПБ was chosen because its synthetic recording
over the same text layer (`fixtures/recorded/sections/pb/`) carries the АР baseline recording's findings —
the same three categories, the same five quotations on pages 2, 6, 3, 7 and 8 — so every figure measured on
the АР run holds for it. `tests/e2e/test_pc01_journey_section.py` compares the two recordings, reads the
section from `tests/e2e/pc01/driver.py` (`JOURNEY_SECTION`, which `test_acceptance.py` uses too) and refuses a
classification step that names another. **That proves the recorded answer, not that a ПБ run publishes on a
stand and not what a live model finds under the ПБ profile: both are measured by the first live run.**

What cannot move is listed in `manifest.json` under `write.ar_bound`: the project's «Оптимизация» tab (price
lists, vendor lists, «Спецификация и цены», the passes and their proposals) and the АР Form-7 exist for АР only,
and they read the saved text of a **published АР run**. Three steps (`upload-ar-set-without-a-table`,
`classify-ar-set-without-a-table`, `start-ar-run-without-a-table`) give the honest-empty-pass steps an АР set of
their own, since a pass over the journey's own ПБ set is refused `section_not_ar`. Since
`PROD-11-AR-V1-V2-REMOVAL-01` an АР version can start only the v3 group (`startRun` refuses it with
`section_profile_unavailable`), which needs an installed reviewed pack (`D-204`) and, in recorded mode, a provider
binding with a verifiable cost (`D-225` piece 2). So **every step of `write.ar_bound.steps` carries
`pending_v3_activation: true`**: the driver does not run it, prints `PENDING <step> pending_v3_activation -- NOT RUN:
<reason>` for each, reports the count (`write steps checked: 79/112 (33 PENDING ...)`), writes `stepsPending` and the
names into the envelope, and ends `e2e:pc01 OK WITH PENDING`, never plain `OK`; `verify-acceptance.mjs` refuses such an
envelope, so the manual acceptance cannot be signed while a step is pending. Nothing is deleted: removing the mark
is how a step comes back once a published АР run can exist. The conformance test refuses a listed step without the
mark, a marked step that is not listed, a missing reason, any АР pin, АР classification or run start outside that
list, and a pass or a specification read asked of a document that no earlier step confirmed as АР. `--steps` can
walk the rest alone, as a PARTIAL run (exit 3).

### What the stack needs

* **A worker beside the API.** The queue and worker steps need a registered worker: run the API
  with `EXECUTION_ROLE=api` and `python -m auditmanager.workers serve` (`EXECUTION_ROLE=worker`, no
  deployment secret). With `EXECUTION_ROLE=all` the Исполнители list is honestly empty and the step
  that reads it fails.
* **A norms snapshot to designate.** `PYTHONPATH=src .venv/bin/python
  tests/e2e/pc01/journey/seed_norms.py` writes, by SQL, one qualified and one unqualified synthetic
  snapshot into the lane's database (it refuses a database whose name lacks `journey` or `lane`).
  Run it before each journey: each run designates one. Since `PC01-JOURNEY-GAPS-01` it also puts the
  bytes each document's PDF binding names into the lane's own object store, BEFORE it writes the rows
  that claim them, so it needs the `S3_*` names of the lane's `.env` (or of its environment) as well as
  `DATABASE_URL`; with no usable store it exits 2 and writes nothing.
* **Nothing to install for the specification set.** The journey uploads the committed synthetic set of
  `SPEC-TABLE-RECORDING-01` itself: `fixtures/synthetic/ar_specification/ar_specification.zip` and
  `ar_specification_prices.csv`, and the recorded provider replays the committed answer
  `fixtures/recorded/sections/ar_specification/<request key>.json`. No file is written into the checkout
  (an untracked recording used to make `tests/contract/test_alpha_acceptance_command.py` refuse the tree).
  The figures the steps declare are the oracle's (`expected_specification.json`);
  `test_the_journey_declares_the_figures_the_committed_oracle_computes` keeps the two together, and
  `test_the_journey_uploads_the_committed_specification_set_and_installs_nothing` keeps the uploads on the
  committed digests. The second price-list revision, `fixtures/optimisation/prices_hostile.csv`, is the
  committed CSV byte for byte plus five rows (a formula-named vendor selling a cheaper membrane, a row with
  no price, vendors that begin with `+`, `@`, `-`).
* **A real browser** (`E2E_PC01_CHROME`) and the administrator's credential, as before.

### What it makes, and what it never records

`accounts.mjs` registers an expert-only and an administrator-only account through the registration
and approval screens and signs them in: a refusal by role needs a session that holds only that
role, and the journey's own account holds both. Each password is random per run. Passwords the steps
type are named by `secret` in the manifest, never by value; the typed value, what the control read
back, request bodies on the tier's own doors and every occurrence of a secret are scrubbed from the
envelope and from findings (`grep -c 'Aq9!\|Zq7!' journey.json` is `0`).

### Reading the files an export saves

An export is a download, and the protocol does not give a download's body to
`Network.getResponseBody` (the first live run read `''` for three exports whose headers said 200,
`text/csv`, 4404 bytes). `expects_download` therefore points the browser's downloads at a
throwaway directory (`Browser.setDownloadBehavior`) and reads the saved file: its first bytes (the
BOM, `PK`), its CSV header width, its number of data rows (`csv_data_rows`), and that no cell begins with `=`, `+`, `-` or `@`.

### Where it will not run

`--phase core` is the journey as it stood before the night window: the four original write steps and the
29 routes, none of the steps that make accounts, pause dispatch, designate a snapshot or start further runs.
`--phase all` is everything, and **refuses the night window's steps on an origin whose provider mode is not
`recorded`** (the mode the first run's own poll reports): it says so once, loudly, before making an account
or starting a run, and exits 1. `--allow-spend` (or `E2E_PC01_ALLOW_SPEND=1`) says the cost and the changes
are accepted. A step that only reads (`reads_only`, checked: no controls, no write) runs first on any origin.
`make alpha-acceptance` calls `--phase all`; for a published stand switch its call to `--phase core`
(`verify-acceptance.mjs` counts what the phase declares).

### Working on one step

`--steps a,b`, `--routes x,y` and `--seed <file of captured identifiers>` run part of the
manifest. Such a run can find a defect and can never be a pass: it prints `PARTIAL` and exits **3**.
`write.on_red: continue_if_captured` lets one red step stop only the steps whose inputs it failed to
produce; a step that was not reached is a finding, never a pass.

### What is not reachable here, stated

* ~~The norms document view with a PDF page~~ is reachable since `PC01-JOURNEY-GAPS-01`: the seed stores
  the bytes its bindings name (see above), and the steps `norms-document-*` open the view. The bytes are a
  stand-in, not a PDF, so what is asserted is the three reads (`getNormDocument`, `listNormParagraphs`,
  `streamNormDocumentContent`) and the viewer's address, not what the browser's viewer draws.
* The recorded model answers the baseline's text under the ПБ profile (`fixtures/recorded/sections/pb/`) and
  the committed specification set's (`fixtures/recorded/sections/ar_specification/`) -- the latter only
  for the АР steps of `write.ar_bound`, which are pending. Other sections' profiles are proven by their own
  recordings elsewhere.
* A norms catalogue «Excel» is the run export above; the catalogue itself has no workbook.
* The vendor-list `vendor_list_missing` refusal of a pass is global state (a list, once set for the
  section, stays), so it cannot be asserted repeatably on a lane; `tests/integration/optimisation`
  holds it.

## The menu destinations the matrix found unwalked (`PC01-JOURNEY-GAPS-01`)

`docs/program/BETA-MATRIX-02.md` section B12 kept the criterion at NEEDS-CODE for five gaps in this
journey. Each now has steps, with a result and a refusal; `GAP_STEPS` in the conformance test pins each
by name, screen, case and the operations it declares.

| gap | steps | what they prove |
|---|---|---|
| «Блоки» | `blocks-portal-blocks-of-a-version-with-a-run`, `blocks-text-lines-of-the-same-version`, `blocks-upload-a-document-no-run-has-read`, `blocks-a-version-no-run-has-read-says-so` | choose a project and a version in the chooser; read the version's portal blocks (`listVersionPortalBlocks`, one crop of an image block, `streamVersionPortalBlockCrop`) and its text lines (`getVersionBlocks`); a version no run has reached is told `not_produced` and shows no list, no count and no picture |
| the norm document view | `norms-document-text-and-pdf`, `norms-document-page-past-the-end` | `getNormDocument`, `listNormParagraphs` and `streamNormDocumentContent` from the catalogue's first document; a page the document does not have is told in words and asks the store for nothing |
| a successful «Вернуть» | `assign-work-to-be-given-back`, `my-tasks-take-the-work-to-give-it-back`, `my-tasks-give-the-work-back`, `dispatcher-shows-the-work-given-back` | a second assignment, taken, then given back with the reason the form requires: one transition `returned` carrying the reason, the row waiting for an administrator with no move left for an expert; the administrator sees the reason and the moves only an administrator has |
| `correctVersionClassification` | `classification-correction-is-an-experts-act`, `classification-correction-needs-a-change`, `classification-correction-needs-a-reason`, `classification-correction` | the first version's stage is corrected from П to Р with a reason, pressing twice: one request based on revision 1, revision 2 stored, the history keeping the confirmation beside the correction; an administrator alone is offered nothing; an unchanged pair and a reason with no word are refused by the form and send nothing |
| the identity continuation | `identity.mjs` (not a step of `--phase all`) | `approveRegistration`, `rejectRegistration`, `updateUser`, `purgeUser` and the other seven operations of `identity.operations`; its handles are now read from the runner and required to exist in `web/src` |

### A click in a row: `click.within`

«Блоки» draws one identical button per project and per document and gives a row no handle of its own, so a
step names the row by the words in it: `"within": {"selector": "li", "text_contains": "…"}` makes the click
the button of the nearest `li` whose text contains the words (the project's name with `%STAMP%`, a version's
identity `{version_uid}`). A row that is not there matches nothing; the first row is never taken instead
(`locatorExpression` in `cdp.mjs`, shown failing in `write.test.mjs`). A click that names a row carries no
`text`: the web tier's language guard requires every click `text` to occur in a rendered screen, and the
chooser's rows are not among the screens it renders.

### Taking the seeded administrator off the shipped password, on a lane (found by `PC01-JOURNEY-GAPS-01`)

Against the API directly (the proxy that strips `/api/v1` is not there): `POST /auth/token` with the seeded
login and password, `POST /auth/password` with that token, then `PATCH /me` with the new token. The seeded login
`admin` is not an e-mail, so the profile **must carry an `email`** (else `422`), and **the account's login then
becomes that e-mail**: `E2E_PC01_LOGIN` is the e-mail from then on. A password lost with the process that
generated it cannot be recovered; the lane's database row can be returned to the shipped state with the
application's own `hash_password` (a lane database only) and the three calls repeated.

### Running the identity continuation on a lane stack

It needs the envelope of a completed `--phase all` run and read access to the web tier's session register.
Measured 2026-10-22 on a lane stack of the full beta tree: `identity: PASS`, 12 operations, 18 checks. Five of
its stages had gone stale since it was written (`D-137`: it had never run on a built stand) and were repaired
against the screens they meet: the profile prints the display label; a role removal closes the session inside
one navigation; a role-less account is turned away at `/403` (its decision is then asked of the API directly and
refused `403`); archiving and rejecting ask for a confirmation first.
Start the web tier with `AUDITMANAGER_SESSION_STORE=<a path in the lane>/register.json` and pass the same
path:

```
E2E_PC01_LOGIN=<admin> E2E_PC01_PASSWORD=<password> E2E_PC01_SESSION_STORE_PATH=<the same register.json> \
  node tests/e2e/pc01/journey/identity.mjs --origin <origin> --journey <out>/journey.json --out <out>/identity
```

### The controls

`prove_the_guard_can_fail.py` rewrites the real manifest once per mutation and reads the conformance test
red (it restores the file even when a run cannot start; `JOURNEY_PROOF_PYTHON` names the interpreter in a
worktree that has no `.venv`). `write.test.mjs` (`node --test`) holds the pure rules, including the row
locator against a minimal DOM.
