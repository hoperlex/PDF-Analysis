# W15-AUTH — the credential the browser never sent

**Session** `W15-AUTH` · **branch** `agent/w15-auth` · **worktree** `/root/w15auth`
**HEAD on arrival** `700022f` (`merge(W14-PKG): the image, the single origin and the wipe`),
the tip of `origin/dev` at provisioning.
**Elapsed** 03:20 → 03:54 +05:00, 2026-09-18. **34 minutes wall-clock.** Roughly: 12
minutes to the green frontend suite, 4 to the mutation sweep, 4 to the live drive, and
14 to two `make gate` runs and the fresh-database diagnosis in section 9.1.

---

## Summary

- **Shape chosen: a server-side route in Next.** `/bff/v1/[...path]` holds the bearer
  credential; the browser calls it on the same origin and never sees the token. §2 argues
  against the two rejected shapes.
- **Measured, not asserted:** a build with the token as a sentinel puts **0 occurrences**
  anywhere in `.next/`, while the same build puts a `NEXT_PUBLIC_*` sentinel in
  `.next/static/chunks/904-*.js`. The instrument is proven on the same build (§3).
- **401 is now a state, on all five classifiers.** It was `server_error` — "the request
  failed on the server" — on every one of them (§4).
- **19 mutations, 19 killed, 0 survived**, every run carrying both provenance assertions
  (§5). Suite **440 → 498**.
- **Driven live against wave 14's stack on 31480**, not a rebuild: 200 with the credential,
  401 with a wrong one, 401 fail-closed with none (§6).
- **Two lines stop at wave 14's boundary** and are not reached for (§7).
- **One premise of the dispatch is false**, and one thing it implies is not quite right (§8).

---

## 1. The blocker, as measured on arrival

- `grep -rn "Authorization\|Bearer\|credentials" web/src` → no match. Confirmed.
- `transport.ts` sets `Accept`, `Idempotency-Key`, `X-Correlation-Id` and, for a JSON body,
  `Content-Type`. Confirmed — the brief omits the fourth, which is set in `buildBody`.
- Against the running stack: `curl http://127.0.0.1:31480/api/v1/projects` → **401**,
  `error_code: authentication_required`.
- Baseline before the first edit: `npx vitest run` in `web/` → **35 files, 440 passed**.

And one thing the brief does not say, which turned out to be the sharper half of the
problem: **`web/src` had no branch for `authentication_required` anywhere.** Every one of
the five failure classifiers ended in

```ts
default:
  return { ...base, kind: 'server_error', title: 'The request failed on the server.' };
```

so even once a credential was sent, a refused one would have rendered as a server fault.
`PC01_ERROR_CODES` — the list of "the ones a PC-01 screen has to be able to render" — had
ten entries and neither authorization code among them. That list was written when nothing
could produce them; `R-3` made both reachable from every screen and nobody widened it.

---

## 2. The shape, and the argument against the two rejected

### Chosen: a server-side route in Next

`web/src/app/bff/v1/[...path]/route.ts`, a catch-all Route Handler. The browser calls
`/bff/v1/<operation path>` on the origin it was served from; the handler reads
`AUDITMANAGER_API_TOKEN` out of the Node process's environment, attaches
`Authorization: Bearer <token>`, and returns the API's status and body bytes verbatim.

Three properties made it the answer rather than merely a workable one:

1. **It is where OIDC lands without touching the twelve operations again**, which is the
   thing `T-6` actually asks for. A sign-in flow terminates at a bearer header in the
   browser; replacing a static token with an issued one then means changing what the
   browser holds, how it refreshes, and what every screen does when it expires. Here the
   whole of that change is inside one route handler: today it reads an environment
   variable, tomorrow it exchanges a code and holds a session. `transport.ts`, the
   generated client, the twelve operations and the frozen contract do not move either way.
2. **It preserves `T-2` and wave 14's measured bundle property.** The browser still calls
   one origin with a relative base path. The built bundle still carries `let e="/bff/v1"`
   and no baked origin (§3) — the same shape wave 14 measured, with a different four
   characters in it.
3. **It needed no nginx change**, which I did not expect and checked rather than assumed.
   `infra/deploy/proxy/nginx.conf` special-cases only `/api/v1`; everything else falls to
   `location /` → `web:3000`. A handler at `/api/v1` would never have been called. A
   handler at `/bff/v1` is reached through the proxy exactly as deployed.

### Rejected: a sign-in flow

> The operator supplies the token, it is held for the session and sent as a bearer.

**A shared secret typed by a human is an identity model, and this one would be a false
one.** The alpha has exactly one token. Every operator who "signs in" signs in as the same
subject, so the sign-in screen states a fact that is not true — that this person
authenticated — and the audit trail it implies does not exist. `R-3`'s own scheme
description says `403 permission_denied` is "for a subject not permitted this operation";
a design with one subject for everyone cannot ever produce that code, and the screen I
would have built for it would be decoration.

The practical cost is worse. The token would live in the browser — `sessionStorage`, a
React context, or a non-`HttpOnly` cookie — which is precisely what
`web/src/shared/config/env.ts` warns against, just reached by a different route than the
build inliner. And when the public version arrives, the sign-in screen is the thing that
has to be deleted and replaced, having taught operators a gesture that stops existing.

It is genuinely simpler. That is its whole case, and it buys simplicity by making the
next change larger than the one it avoids.

### Rejected: the proxy injects the header

> Simplest, and it makes the API unauthenticated from the proxy's point of view.

**It deletes the property `T-6` exists to create, and does it silently.** After this
change every request arriving at nginx is authenticated, so the authorization seam has
moved from "a credential the caller holds" to "network reachability of port 8080" — which
is what the seam replaced. The API would still answer 401 to an uncredentialed request and
the deployment would still pass wave 14's three checks, so nothing would show that the
seam had stopped meaning anything. A control that silently becomes a no-op is worse than
one that was never added, because the next reviewer reads `security: [bearerAuth]` in the
contract and believes it.

It also makes `403 permission_denied` unreachable forever and puts the credential in
`infra/**` — wave 14's tree — rather than in the tier that will eventually hold a session.

There is a narrower version of this — nginx injecting the header only as a stopgap — and
it is still rejected, because "stopgap" is not a property the deployed artifact has.

### What the BFF costs, stated rather than omitted

- **One more hop.** Browser → nginx → Next → nginx's sibling → API, instead of browser →
  nginx → API. Same host, compose network, no TLS between them.
- **Request bodies are buffered in the Next process,** not streamed: a Node stream body
  needs `duplex: 'half'`. The largest thing on this surface is a 25 MiB PDF that nginx
  already caps at 32m. Responses *are* streamed through, so a PDF export is not buffered.
- **An open forwarder is a new class of defect.** Answered by building the path from
  checked segments rather than concatenating a string — §5 mutates that check away and
  watches two tests go red.
- **No new runtime dependency.** `package.json` is unchanged; the handler uses the
  platform `Request`, `Response` and HTTP client.

---

## 3. Where the token lives, and the evidence it is not in the browser bundle

**It lives in the Node process of the `web` container**, read by exactly one module:

```
web/src/shared/config/server-env.ts     AUDITMANAGER_API_UPSTREAM, AUDITMANAGER_API_TOKEN
```

Neither name carries the `NEXT_PUBLIC_` prefix, which is the whole mechanism: Next
substitutes `process.env.X` in client code only for `X` beginning `NEXT_PUBLIC_`, so in a
module that reaches the client any other lookup compiles to a lookup on an empty object.
The module is deliberately **not** re-exported from `shared/config/index.ts` — a barrel a
client component imports would pull it into the client graph even where the binding is
never called — and its only importer is the route handler.

### The measurement

Built at `5860f19`, with the token set to a sentinel:

```
$ cd web && NEXT_PUBLIC_API_BASE_URL=/SENTINEL-W15AUTH-PUBLIC-b7d41e \
    NEXT_PUBLIC_INSTANCE_LABEL=alpha \
    AUDITMANAGER_API_UPSTREAM=http://api:8000 \
    AUDITMANAGER_API_TOKEN=SENTINEL-W15AUTH-TOKEN-b7d41e \
    npm run build

$ grep -rl 'SENTINEL-W15AUTH-TOKEN-b7d41e'  .next/static/ | wc -l   → 0
$ grep -rl 'SENTINEL-W15AUTH-TOKEN-b7d41e'  .next/        | wc -l   → 0
$ grep -rl 'AUDITMANAGER_API_TOKEN'         .next/static/ | wc -l   → 0
```

**The same build is the negative control.** A `NEXT_PUBLIC_*` value from that identical
invocation *is* there:

```
$ grep -rl 'SENTINEL-W15AUTH-PUBLIC-b7d41e' .next/static/            → .next/static/chunks/904-ec8cd4d1cf3e80c9.js
$ grep -rho 'let e="/SENTINEL-W15AUTH-PUBLIC-b7d41e"' .next/static/  → let e="/SENTINEL-W15AUTH-PUBLIC-b7d41e"
```

so the grep is shown to find an inlined value on the tree it is being asked about. Without
that line the first three zeros would be worth nothing, and the point is not hypothetical:
**my first control was a false negative.** I put the sentinel in
`NEXT_PUBLIC_INSTANCE_LABEL` and got zero hits, which looked like the same reassuring
answer. It is zero because `getInstanceLabel()` is called only from `_app/app-frame.tsx`,
a server component, so that value legitimately never reaches the client bundle. A control
has to use a variable known to be inlined, and `NEXT_PUBLIC_API_BASE_URL` is one.

With the real relative base, the bundle keeps wave 14's property:

```
$ grep -rho 'let e="/bff/v1"' .next/static/   → let e="/bff/v1"
$ grep -rho 'http://api:8000' .next/static/   → (nothing)
```

Next's own route table agrees the handler is server-rendered and not static:

```
├ ƒ /bff/v1/[...path]     127 B    103 kB        ƒ (Dynamic) server-rendered on demand
```

### The standing guard

The build measurement needs a build, so the suite carries the static half:
`web/tests/guards/server-credential.guard.test.ts` with a pure scanner in
`tests/guards/lib/credential-scan.ts`, following `source-scan.ts`'s shape. Four rules —
no `NEXT_PUBLIC_` name may read as a secret; the server-only names are read in one module;
no barrel re-exports it; only `src/app/bff/` imports it — run over the real tree **and**
over six in-memory fixtures that break each one, so the scanner is shown to fire. It also
scans `web/.env.example`, which is where a later session would write
`NEXT_PUBLIC_API_TOKEN=`; it caught this commit's own first draft naming the variable in
that file's prose.

---

## 4. The 401 state the UI now shows

All five classifiers gained explicit `not_authenticated` / `not_permitted` branches,
sharing one wording from `web/src/shared/api/authorization.ts`:

| screen | 401 title | before |
|---|---|---|
| start / watch a run | *This run is not authorized.* | *The request failed on the server.* |
| create a project | *Creating a project is not authorized.* | *Creating the project failed on the server.* |
| project list | *Reading the project list is not authorized.* | *The project list could not be read.* |
| upload a document | *Uploading is not authorized.* | *Uploading failed on the server.* |
| review screen | caller's title + the authorization sentence | `authentication_required: <envelope message>` |

The detail is the same sentence everywhere, because five copies of a sentence about a
credential drift into five diagnoses of one fact:

> The API did not accept a credential for this request. Either this deployment has none
> configured, or the one it presents is not one the API accepts. Nothing was applied, and
> retrying sends the same credential to the same refusal.

It names both halves deliberately. From the browser they are the same event and the API is
required not to distinguish them — the 401 "carries no hint about the addressed resource" —
so naming both is what makes the sentence actionable rather than merely accurate.

**No screen offers a retry for either code.** `contracts/domain/v1/error-codes.json` pins
`retryable: false` on both, and `presentFailure` drops `onRetry` even when the caller
passes one. 403 additionally renders the two safe classifiers the catalog declares for it
(`aggregate_type`, `required_capability`) and nothing else.

`PC01_ERROR_CODES` goes from ten to twelve, with the two pins asserting ten updated. A new
contract test reads `401` and `403` off all twelve operations in the frozen document rather
than restating them, so if a later reseal dropped the security scheme the list and the
document would stop agreeing.

### The tests that redden without it

| behaviour | test that goes red |
|---|---|
| 401 on a run is `not_authenticated` | `authorization-state` → *reports a 401 as not authenticated, not as a server error* |
| …on create / list / upload | `authorization-state` → three more, one per screen |
| review screen shows the sentence | `authorization-state` → *shows the authorization sentence and never the envelope message with the code* |
| no retry button for a refusal | `authorization-state` → *offers no retry button even when the caller passed one* |
| the wording stays specific | `authorization-state` → *says what the operator can act on, and says retrying will not help* |
| the whole path | `authorization-state` → *decodes to an ApiError the classifiers name, on a read and on a write* — a real 401 `Response`, the real `transport.request`, the real classifiers |

Titles and details are pinned as **literals**. Asserting
`failure.detail === AUTHENTICATION_REQUIRED_DETAIL` would share the constant with its
subject and would pass over an empty string — `OPERATING_CONSTRAINTS.md` §12.

---

## 5. The mutation harness, and how I know the mutated tree was the one under test

Built on `W12-WEB` §1 rather than reinvented, for the reason recorded there: the web suite
reaches `web/src` by **two** routes — the `@` alias, and a **text read** whose root comes
from `tests/guards/lib/repo.ts` resolving `import.meta.url` — and a harness that redirects
only the alias leaves every source-scanning guard reading the pristine tree. My new guard
is a source-scanning guard, so a path-alias-only harness would have reported it green
against a leak that was still there.

```
/root/w15auth-mut/rebuild.sh               full copy of web/ + contracts + P02_SEAMS, node_modules symlinked
/root/w15auth-mut/provenance.probe.test.ts the `auditmanager.__file__` equivalent, NOT committed
/root/w15auth-mut/mut.py                   one substitution, refused if absent or ambiguous, read back, run
/root/w15auth-mut/batch.py                 the 19 mutations, as data
/root/w15auth-logs/mutations.log           every run
```

vitest runs with `cwd` inside the copy and the copy's own committed `vitest.config.ts`, so
both routes move together. Nothing in `/root/w15auth` is edited.

**Evidence of provenance.** The probe proves both routes at runtime and both assertions
compare against `MUT_WEB_ROOT`, supplied by the driver, so it *fails* if either leaks back:

```
PROVENANCE module frame:    at assertNever (/root/w15auth-mut/repo/web/src/shared/lib/assert-never.ts:10:9)
PROVENANCE WEB_ROOT: /root/w15auth-mut/repo/web REPO_ROOT: /root/w15auth-mut/repo
```

The stack frame is emitted by the loader, not by anything the test declares. **Both lines
appear in all 19 runs**, and the probe is never in a `FAIL` line.

**Baseline of the unmutated copy: 500 passed** — the repository's 498 plus the 2 probe
assertions. The copy mechanism reddens nothing by itself.

### The sweep — 19 applied, 19 killed, 0 survived

| # | mutation | killed by |
|---|---|---|
| M-01 | the credential is not attached | 3 |
| M-02 | request headers become a passthrough, not an allowlist | 1 |
| M-03 | response headers become a passthrough | 1 |
| M-04 | `..` and `.` segments reach the upstream | 2 |
| M-05 | an unreachable API is reported non-retryable | 1 |
| M-06 | an unconfigured deployment answers `500 internal_error` | 2 |
| M-07 | the token defaults to empty — fail-open | 2 |
| M-08 | a relative upstream is accepted | 1 |
| M-09 | the token is read through a `NEXT_PUBLIC_` name | 5 |
| M-10 | the config barrel re-exports the credential reader | 2 |
| M-11 | a run 401 falls through to `server_error` | 1 |
| M-12 | a create 401 falls through | 2 |
| M-13 | a list 401 falls through | 2 |
| M-14 | an upload 401 falls through | 1 |
| M-15 | the review screen loses its authorization branch | 1 |
| M-16 | the review screen offers a retry for a refused credential | 1 |
| M-17 | `PC01_ERROR_CODES` loses the two authorization codes | 3 |
| M-18 | the 401 sentence goes generic | 3 |
| M-19 | the correlation id stops coming back | 2 |

M-11…M-14 substitute the case label for `cost_budget_exceeded` — a real catalog code with
no PC-01 producer — rather than deleting the arm, so the mutant still type-checks and the
mutation is the realistic one: an arm that exists and guards the wrong code.

---

## 6. Driven live against wave 14's stack — reused, not rebuilt

Wave 14's stack was **left running on 31480 and used as-is**; nothing was rebuilt and it
was not torn down. `next start` from this worktree ran on 31490–31492 with
`AUDITMANAGER_API_UPSTREAM=http://127.0.0.1:31480/api/v1`, reaching the deployed API
through the deployed proxy.

| | request | result |
|---|---|---|
| A | `GET /bff/v1/projects`, correct token | **200**, `{"items":[{"project_uid":"prj_01M2RP57JJFQZ77VMFP3H6MRAS","name":"W14-PKG drive",…}]}` — wave 14's restored document |
| B | same, headers and body scanned for the token | **0 occurrences** in either |
| C | `X-Correlation-Id: cid-w15auth-probe` | echoed back on the response |
| D | `GET /bff/v1/projects/..%2f..%2fhealthz` | **404** `not_found`, a real `ErrorEnvelope`, the API never called |
| E | `GET /api/v1/projects` direct — what the frontend did before | **401** `authentication_required` |
| F | **wrong** token configured | **401** `authentication_required`, the API's own envelope |
| G | **no** token configured | **401** `authentication_required`, this app's envelope: *"This deployment presented no credential to the API, because none is configured for its web tier. No request was sent."* |

E is the blocker, reproduced. A is it removed. F and G are the two ways it comes back, both
landing on the state §4 built.

G is the design decision worth naming: **an unconfigured web tier answers 401, not 500.**
The request genuinely was not authenticated — this process had no credential to present —
and the operator lands on a screen that says the deployment has none configured. A 500
would blame the API, which is working. The refusal deliberately does not name the
environment variable: a variable name on a public response is a hint about the deployment
that nothing outside needs, and a test asserts it is absent.

---

## 7. What I stopped at

I own `web/**` and this file. **Two lines in `infra/**` are wave 14's and are reported
rather than reached for.** Until they land, the deployed stack still has the blocker: the
code is here, the deployment is not pointed at it.

**7.1 — `infra/deploy/compose.server.yml`, the `web` service needs a runtime environment.**
It currently has only build args and no `environment:` block at all. It needs:

```yaml
    environment:
      AUDITMANAGER_API_UPSTREAM: http://api:8000
      AUDITMANAGER_API_TOKEN: ${AUDITMANAGER_API_TOKEN:?AUDITMANAGER_API_TOKEN is unset.}
```

This is irreducible, and not a consequence of the shape I chose. The token has to be in
some process, that process cannot be the browser, so it is the web server — under any
design where the browser does not hold the secret. `AUDITMANAGER_API_TOKEN` is already in
`alpha.env` and already reaches the `api` service; this hands the same value to a second
container, which is why the name is deliberately identical rather than a second name for
one secret.

**7.2 — the browser base URL becomes `/bff/v1`.** In
`infra/deploy/env/alpha.env.example` and correspondingly in any `alpha.env`:

```
NEXT_PUBLIC_API_BASE_URL=/bff/v1      # was /api/v1
```

Still relative, so wave 14's "the image names no origin" property is unchanged. I did
**not** hardcode the path to avoid this line: that would have made
`NEXT_PUBLIC_API_BASE_URL` dead configuration, and would have deleted the
`MissingConfigurationError` discipline `env.ts` exists for.

`web/.env.example` — which is mine — is updated for both, and documents what each name is
for and what happens if the base is left at `/api/v1`.

**Explicitly not needed:** no nginx change (`location /` already reaches Next), no
`AppSettings` field, no change under `src/auditmanager/api/**`, no contract change, no
regeneration of the client, and no new dependency.

**Not attempted, and named so it is not mistaken for done:** rebuilding the alpha image
with this code in it. That is a `--build` of a compose file I do not own, after 7.1 and
7.2 land.

---

## 8. What is false in the dispatch

**8.1 — false. "`transport.ts` sets exactly `Accept`, `Idempotency-Key` and
`X-Correlation-Id`."** It sets a fourth: `buildBody` sets `Content-Type:
application/json` for a JSON request, and deliberately leaves it unset for multipart
because only the runtime can supply the boundary. It matters here because the forward's
inbound allowlist has to carry `content-type` or every write breaks, and a list built from
the brief's three would have dropped it.

**8.2 — incomplete, and it was the more useful half.** The brief says the UI "does not
*fail to branch* on a 401" and that 401 "must be a state the UI can show". Both true, but
the reason is sharper than a missing branch: `PC01_ERROR_CODES`, the list of codes a PC-01
screen must render, **did not contain either authorization code**, and its own comment
asserted that the other codes have "no PC-01 producer". That was correct before `R-3` and
false after it. Widening that list, and adding a contract test that reads 401 and 403 off
all twelve operations in the frozen document, is what keeps §4 from silently reverting.

**8.3 — a premise that held, and was worth checking.** The brief warns that the Makefile
parses `.env` against a strict fifteen-name allowlist. It does, and it is why the two
server-only names go in `web/.env.local` and `infra/deploy/env/alpha.env` and never in
`.env`. `web/.env.example` is outside that allowlist entirely — it is read by Next, never
by `make` — so adding two names there breaks nothing, and `make gate` is green (§9).

**8.4 — the `run-progress.tsx` pointer did not apply.** `W12-WEB` measured 34 of 110
modules reached by no test and named `run-progress.tsx`. It renders `RunFailure` values it
receives as props and has no error-code branch of its own, so the 401 state lands in
`run-failure.ts` — which *is* test-reached — and nothing this wave adds falls inside the
unswept region. That region is still unswept and this wave did not sweep it.

---

## 9. The gate

`make gate` on instance `gate-w15a` (POSTGRES_PORT 55750, S3 59350/59351, database
`audit_w15a`, bucket `auditmanager-gate-w15a`), at `19ca6f5`:

```
1726 passed, 5 skipped, 1 warning, 168 subtests passed in 204.92s
 Test Files  39 passed (39)
      Tests  498 passed (498)
foundation: 35 passed
GATE OK: battery, foundation, frontend and whitespace all pass
```

Battery, foundation and subtests are exactly the figures the dispatch names. The frontend
is 39 files / 498 tests against the expected 440, which is this wave's 58 new tests.
`/root/w15auth-logs/gate2.log`.

### 9.1 The first `make gate` failed, and the cause is not mine — it is a live defect

The **first** run on this lane came back `1679 passed, 5 skipped, 47 errors` — 1679 + 47 =
1726, so the deficit is exactly these 47, all of them setup errors in one session-scoped
fixture in `tests/characterization/w13_baseline/test_response_baseline.py`:

```
E   AssertionError: next_cursor is null although a second project exists; a bounded page
    with more rows behind it must carry a continuation token
tests/characterization/w13_baseline/journey.py:1101
```

**It is not this wave's.** `git diff --stat origin/dev..HEAD -- src/ tests/ contracts/ db/
pyproject.toml Makefile infra/` is empty: this branch changes no Python, no contract, no
migration and no infrastructure, and the battery never reads `web/`.

**It is a real, reproducible defect in wave 13's tree**, not flakiness. Measured on a
database created and migrated for the purpose:

```
DROP DATABASE / CREATE DATABASE audit_w15a_probe; alembic upgrade head
project rows: 0
RUN 1   →  8 passed, 47 errors   ← the assertion above
project rows after run 1: 1
RUN 2   →  55 passed
```

**The cause, read off the source.** `journey.py:654` creates a "cursor setup" project so
that case 16's `GET /projects?limit=1` has a second row behind it — the comment says
`next_cursor` is then non-null "**by construction**". That call is `api.send(...)` and does
**not** go through `record()`. `record()` is the only thing that attaches the credential,
and the `Caller` docstring states the rule outright: *"it sends exactly the headers it is
given, and adds none. The `T-6` credential is added by `record()`, not here."*

So since `T-6` the setup call is answered `401 authentication_required` and **creates
nothing**. Its response is discarded, so nothing notices. The count confirms it: after the
failing run the table holds **one** project — case 01's — not two.

The assertion at line 1101 therefore holds only on a lane whose `project` table already
contains a row from an earlier run. That is precisely the "function of residue" `W13-CONF`
added the setup call to eliminate: the conditional was removed, but the setup it was
replaced by had already been broken by the authorization dependency landing in the same
wave. `OPERATING_CONSTRAINTS.md` §9 is about exactly this shape.

**Consequence for the programme, which is the part worth acting on: `make gate` is red on
any lane whose database is fresh.** It has been green for wave 13 and wave 14 only because
those lanes had been run before. A clean-clone reviewer, or any new session that
provisions a new instance, sees 47 errors on the first run and a pass on the second.

**Stopped at the boundary.** `tests/characterization/**` and `src/auditmanager/api/**` are
wave 13's. The repair is one line — give that `api.send` the header `record()` gives
everything else:

```python
headers={AUTHORIZATION_HEADER: f"Bearer {STATIC_TOKEN}",
         "Idempotency-Key": f"w13base-{tag}-cursor-setup", **json_headers},
```

and it wants a check that the setup call's status was 201, because a silently discarded
response is what let this sit. I did not make the change.

---

## 10. Reproducing this

```
git worktree add /root/w15auth -b agent/w15-auth origin/dev
cd /root/w15auth && cp .env.example .env     # instance gate-w15a, ports 55750/59350/59351
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12
npm --prefix web ci
make gate

# the bundle measurement
cd web && NEXT_PUBLIC_API_BASE_URL=/SENTINEL-W15AUTH-PUBLIC-b7d41e \
  AUDITMANAGER_API_TOKEN=SENTINEL-W15AUTH-TOKEN-b7d41e npm run build
grep -rl 'SENTINEL-W15AUTH-TOKEN-b7d41e'  .next/          # expect 0
grep -rl 'SENTINEL-W15AUTH-PUBLIC-b7d41e' .next/static/   # expect 1 — the control

# the mutation sweep
/root/w15auth-mut/batch.py

# the live drive, against a running alpha stack on 31480
AUDITMANAGER_API_UPSTREAM=http://127.0.0.1:31480/api/v1 \
  AUDITMANAGER_API_TOKEN=<the stack's token> npx next start -p 31490
curl -s http://127.0.0.1:31490/bff/v1/projects
```

The harness lives outside the worktree on purpose, for `W12-WEB`'s reason: committing it
would put a second copy of `web/src` where a later session could mistake it for the tree.
