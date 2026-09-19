# The PC-01 browser journey

```
npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:PORT
```

Exit `0` means every route in `manifest.json` loaded cold, made exactly the API calls the
manifest declares, carried no credential, and offered the link the next route needed.
Non-zero prints every finding and names the envelope file.

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

**The cost, stated:** that guard checks *addressing*, not *behaviour*. A screen whose route
and API calls are unchanged but which renders nothing is invisible to the gate and visible
only to this journey. Keeping the gate stack-free buys that blind spot; running the journey
is what closes it.

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

The fixture is not read by the conformance guard, so its three deliberate wrongs never
redden `make gate`.

## What it costs to run

Measured on 2026-09-19, seven routes against `http://127.0.0.1:31500`: **178 s**, exit `0`,
134 exchanges recorded, a 3.6 MB envelope.

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
anti-vacuity spec, and none of those are here. Neither is the **write** half of the journey
— create a project, upload a document, start a run — which is what `D-5` itself was. Driving
a write needs a deployed stack the session may write to; the step is named here rather than
written unexecuted, because an untested code path in a test instrument is the same defect as
an unrun suite.

Filling those in is an extension of `manifest.json` and of the walk in `journey.mjs`; it is
not a second instrument.
