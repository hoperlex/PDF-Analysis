# Short road to a deployable alpha

Written 2026-09-17. Base `c96ccf3` on `planning/prototype-roadmap`, with PC-01 re-certified
at `e6eae1e` the same day. **Candidate**: four owner rulings in §9 are dispatch
prerequisites, and nothing below is dispatchable until they exist.

> **Revision 2, 2026-09-17 — the owner ruled FastAPI, and two open questions are now closed.**
> Revision 1's `T-1` argued for a hand-written ASGI adapter over the existing `Router` and
> against FastAPI. The owner overruled it: FastAPI is a core decision of the main plan
> (`ARCHITECTURE_BIBLE.md` P-05, `ADR-0002`, `PROTOTYPE_PROFILE.md` §2), and the contracts are
> to be built under it. §3 `T-1` is rewritten and **the old objection is kept inside it**,
> because a decision whose objection has been deleted cannot be re-examined later — it can
> only be re-argued from scratch.
>
> Two questions the owner answered with it: the frozen document stays the contract authority
> and FastAPI conforms to it (**contract-first**), and the twelve operations are converted
> **natively before the deploy**, not behind a shell that would have to be certified twice.
> Wave 13 is rewritten accordingly and is now the largest wave in this road; §8 says so.

The programme has certified the same prototype four times through an in-process router. It
has never served one HTTP request. This plan ends that in three waves, and it is deliberately
the shortest route that still leaves a commit somebody can certify.

## 1. What "alpha" means here, and what it does not

**Done means:** one internal server runs the stack from a script; an operator opens a browser,
uploads a real Russian-language AR PDF, watches the run, reads findings beside their pages,
records verdicts, downloads the CSV; PostgreSQL and the S3 bucket live on that same server in
containers with persistent volumes; one command wipes both, safely and reversibly, so the
pilot's throwaway data does not become the production data by accident.

**Not in this road:** multiple tenants, in-app authorization, retention, legal hold, HA, DR,
backup rotation, job/attempt framework, remote workers, OCR. Every one stays where
`PROTOTYPE_PROFILE.md` §7 put it.

The purpose is stated plainly, because it decides every trade-off below: **we stop judging
this application through its own test harness.** A manual test on a live deployment is the
cheapest instrument that can still tell us the product is unsound, and it is the only one we
have not used.

## 2. The gap, measured at `c96ccf3`

| Missing | Evidence it is missing |
|---|---|
| any process that listens on a socket, and any web framework | `grep -rn "serve_forever\|uvicorn\|asgi\|fastapi" src tools tests Makefile` — empty. `ADR-0002` and `ARCHITECTURE_BIBLE.md` P-05 have named FastAPI since the bootstrap; the lock has never carried it, and `GATE_B2_CLOSURE.md` §3 records `B6` finding that and writing ~100 stdlib lines instead |
| an application image or any packaging | `find . -iname "*Dockerfile*"` finds only `infra/local/docker-compose.yml`, which runs PostgreSQL and MinIO and nothing of ours |
| one run of the UI against the backend | `web/src/shared/api/transport.ts` calls `NEXT_PUBLIC_API_BASE_URL`; nothing has ever served it. `e2e:pc01` is a reserved name that fails on purpose (`web/scripts/reserved-forwarder.mjs`) |
| any authentication | `src/auditmanager/access/` holds a README and no code |
| a wipe, a dump or a restore | no script under `infra/`; `make down` keeps the volumes |
| UI rendering under test | `DEBT_REGISTER.md` D-1.5: 34 of 110 `web/src` modules reached by no test; criterion 4's UI clause is the certification's one named exception |

What is **not** missing, and is why this road is still short: the twelve operations, the
typed error envelope over a frozen 20-code catalog, the append-only ledger, migrations, the
checksum-verified blob store, the six `Port` protocols the handlers talk to, the frozen
OpenAPI and a generated client against it. `envelope_response()` in
`src/auditmanager/api/routers/errors.py` already renders every failure the contract declares.
Under `T-1` the work is not to invent that — it is to make sure FastAPI never answers around
it.

## 2.5 The principle these decisions are taken under

**Owner, 2026-09-17.** The point of this stage is to stand the system up on the **stack it will
keep**, even while the things running on it are still specimens. Sample corpora, sample
documents, a sample operator, placeholder content — all fine at this stage. **The structure is
not a specimen.** By the release version the code must be free of high coupling and open to
fast modification, and that is not a property that gets added later: it is decided by what we
choose now and by what we refuse to write.

Two rules follow, and they decide the trade-offs in §3 and the table in §12:

1. **Where the relevant stack has a mechanism, use it rather than write a parallel one.** This
   is what settles `T-1`. The programme has already paid for the alternative: `B6` found no
   HTTP framework in the lock and wrote about a hundred stdlib lines of `Request`/`Response`/
   `Router` (`GATE_B2_CLOSURE.md` §3). It was the right call for that session, under that
   lock, and it is a hundred lines plus a multipart parser plus a wire-shape package that a
   new contributor has to learn instead of reading FastAPI's documentation. That is precisely
   the coupling this stage is meant to end.
2. **Keep the seams that make replacement cheap, and replace what sits on them.** The six
   `Port` protocols are why `T-1` is a transport change and not a rewrite of the application:
   the handlers change, the services do not. Every future swap named in §12 is affordable for
   the same reason. A decision that widens a seam to save an afternoon is refused here.

What this principle does **not** license: replacing something bespoke that is already
contract-shaped, certified and stable, merely because a library exists. §12 gives each such
piece a disposition and an argument, not a preference.

## 3. Six decisions this plan makes, with the argument for each

**T-1 — FastAPI, natively, with the frozen contract built under it.** Owner decision,
2026-09-17. The twelve operations become typed FastAPI path operations; the 43 schemas of
`contracts/api/v1/openapi.json` become Pydantic models; the hand-rolled
`Router`/`dispatch`/`http.py`/`multipart.py` layer is retired. The `Port` protocols in
`routers/ports.py` are the seam that makes this a transport change rather than a rewrite of
the application: the handlers keep calling exactly the same six ports.

**Contract-first, not code-first.** `contracts/api/v1/openapi.json` stays frozen and stays the
authority. FastAPI's generated document must conform to it, a test says so, and the frontend's
generated client and its drift test are untouched. The direction matters: code-first would hand
the contract's authority to whichever Pydantic field someone renamed last.

**The objection revision 1 raised, and what answers it.** A framework that generates its own
OpenAPI over a frozen one creates a second routing and schema authority, and that is a real
drift risk — it is why revision 1 argued against it. What answers it is not an assurance but a
gate: the conformance test of `W13-CONF`, which fails on any semantic difference between the
generated document and the frozen one, and which must itself be shown able to fail against a
planted difference. **Without that gate this decision is worse than revision 1's; with it, it
is better** — FastAPI gives typed request validation, a served schema, and the framework the
architecture has named since `ADR-0002`, and the drift it could introduce is the one thing in
this road with a machine checking it on every run.

**T-2 — one origin, and therefore no CORS at all.** A reverse proxy serves the web app at `/`
and the API at `/api/v1`. `getApiBaseUrl()` accepts a base *path*, so
`NEXT_PUBLIC_API_BASE_URL=/api/v1` is relative: the web image works on any host, the value is
not baked to one origin, and there is no cross-origin surface to configure, mis-configure or
test. Adding CORS headers would also mean touching a frozen contract.

**T-3 — the operational plane is off-contract.** Liveness and readiness answer on a **second
port**, never under `/api/v1`. The contract has twelve operations and `openapi-drift.contract.test.ts`
will say so. An alpha still needs a health check the proxy and the deploy script can poll;
this is where it goes, and it is documented as an operational surface with no product meaning.

**T-4 — deployment commands live in `infra/deploy/*.sh`, not in the `Makefile`.** `OD-16`
makes a new `make` target an FF-01 freeze-break requiring an explicit break record. Nothing
here needs one: the deploy scripts are invoked directly on the server, and the Makefile stays
what it is — the developer's gate. If the owner later wants `make deploy`, that is a freeze
decision taken on its own, not smuggled in with the transport.

**T-5 — the wipe dumps before it drops.** `reset.sh` takes a `pg_dump` and a bucket copy to a
timestamped directory, *then* drops and recreates the schema and purges and re-initialises the
bucket. It refuses unless an explicit destructive flag is set **and** the target database and
bucket names match the configured alpha instance, so it cannot be pointed at something else by
a stale environment. `--dry-run` prints what it would delete. Each refusal gets a test that is
shown able to fail — the rule this programme has paid for four times.

**T-6 — authentication for the alpha is the proxy's job.** TLS plus one shared credential at
the reverse proxy, no in-app AuthZ, no user model, no session. The assumption on record is a
trusted internal network (`PROTOTYPE_PROFILE.md` §2), and an application-level identity model
built before we know who the users are is the kind of guess this programme exists to avoid.
This is written into the debt register the day it ships, not left implicit.

## 4. Three waves and one certification

The parallelism rule is `W12-PLAN.md` §1 as corrected: **only a stream that changes `src/`
serializes before a certification.** Tests-only and infrastructure-only streams run beside it.

### Wave 13 — FastAPI, and the contract built under it

The largest wave in this road, and the only one that rewrites a certified surface. Measured at
`c96ccf3` with `wc -l src/auditmanager/api/routers/*.py src/auditmanager/api/schemas/*.py`:
**2 525 lines in the API layer, of which roughly 1 950 are replaced** — everything but
`ports.py`, the envelope renderer in `errors.py` and the package `__init__`. Plus **21 test
files that drive the router directly** (`grep -rln "api.routers\|Request.build" tests/`). It
runs in four stages, and stage 1 exists so that the rewrite has something to be wrong
against.

**Stage 0 — `W13-PIN`, owner-ruled, one writer.** `pyproject.toml` pins: FastAPI, an ASGI
server, and the multipart parser FastAPI needs for `uploadDocument`. Also whatever the ASGI
test client requires — note that this lock already carries an httpx-family package, so the
stream reports what is actually resolvable rather than assuming a name. Every pin's licence
is named in the diff; `OD-01` blocks copyleft, and nothing in this set should come close.
FF-01 §2.8 makes this a single-owner task; §9 R-2 is the ruling it needs.

**Stage 1 — `W13-GOLD`, tests only, starts now, needs no pin.** Capture a **golden corpus**
of request/response pairs through the *current, certified* implementation at `e6eae1e`: all
twelve operations, the five refusals with their distinct `details.constraint` values, the
`additionalProperties` refusal, the idempotency replay and conflict, the 26 MiB boundary on
both sides, a Range read, the CSV with its BOM and CRLF, and an `X-Correlation-Id` supplied
and absent. Commit the bytes.

This is the wave's safety net and it is cheap: after the rewrite, **the FastAPI
implementation must reproduce those bytes exactly.** A rewrite of a certified surface with no
before-picture is how a programme discovers in wave 15, in a browser, that a status code
moved.

**Stage 2 — `W13-API`, one writer, `src/auditmanager/api/**` and the tests that follow it.**

- Pydantic models for the 43 schemas, named exactly as the contract's `components.schemas`
  keys, with `extra="forbid"` where the contract refuses unknown fields;
- twelve typed path operations over the same six `Port` protocols, mounted at `/api/v1`,
  carrying the contract's `operationId`, tags, parameters, status codes and response headers;
- **every failure rendered by `envelope_response` and nothing else.** FastAPI's own
  `RequestValidationError` and `HTTPException` bodies must never reach a client: handlers map
  them onto the frozen 20-code catalog, preserving the constraint names the certifications
  pin. This is the single highest-risk item in the wave;
- the `X-Correlation-Id` middleware, the body cap, the two-guard size distinction
  (`max_bytes` at the transport, `byte_size <= 26214400` in the envelope — `P4_CLOSURE.md` §5
  explains why both exist and `tests/integration/ingest/test_size_guard_boundary.py` pins it),
  the Range response and the CSV's exact bytes and headers;
- the health plane of `T-3` on its own port;
- the 21 coupled test files migrated. `tests/e2e/pc01/driver.py` is cheap — it funnels every
  call through one `request()` method, so the driver becomes an ASGI test client in one place
  — but `tests/integration/api/*` tests helpers like `require_idempotency_key` and
  `resolve_correlation_id` directly, and those helpers change shape. **Those tests are
  rewritten, not re-pointed**, and each must still assert *which rule refused*, not merely
  that something did.

**Stage 3 — `W13-CONF`, tests only, runs beside stage 2.** The conformance gate:
`app.openapi()` against the frozen document. Byte-equality is not the goal and claiming it
would be dishonest — FastAPI adds titles, orders keys its own way, and may split input and
output schemas unless told not to. So: a **declared normalization**, enumerated in the test
file, and then equality of everything that remains — paths, methods, operationIds,
parameters and their required-ness, request and response media types, status codes, response
headers, and schema shapes.

**Each normalization is a place a real difference can hide, so each one gets a planted
difference proving the comparison still fails.** A conformance test that has never been shown
to fail is the most expensive kind of green in this programme's history.

**Acceptance for the wave:** the golden corpus reproduced byte-for-byte; the conformance gate
green and shown able to fail; `make gate` at or above 1505/5/167 with the migrated and new
suites; and the app serving its own schema at a documented path. **If the golden corpus does
not hold, the wave does not end** — that, and not a certification, is what lets wave 15 treat
the transport as solved. The full certification comes at `PA-01`, on the server, where it is
worth paying for once.

### Wave 14 — the build, the deploy and the wipe

Starts as soon as wave 13's entrypoint name is merged. Two streams, neither touching `src/`.

| Stream | Writes | Delivers |
|---|---|---|
| `W14-PKG` | `infra/deploy/Dockerfile.api`, `Dockerfile.web`, `compose.server.yml`, the proxy config, `env/*.example` | two images built from the locked toolchain, the server compose with named volumes for PostgreSQL and the bucket, the reverse proxy terminating TLS and serving one origin, and a documented environment that never places a provider credential in the `.env` the Makefile allow-lists |
| `W14-OPS` | `infra/deploy/deploy.sh`, `reset.sh`, `dump.sh`, `status.sh`, `tests/integration/deploy/**` | an idempotent deploy — fetch, build, migrate, health-check, switch, and **roll back on a failed health check** — plus the guarded wipe of T-5 and guards that are shown to fail |

Acceptance: the whole stack comes up on the target server from a clean clone with one command;
`deploy.sh` run twice changes nothing the second time; a deliberately broken build rolls back
and leaves the previous version serving; `reset.sh` refuses without its flag, refuses against a
foreign database name, and its dump restores.

### Wave 15 — the first live journey, then the certification

**Stage A — `W15-RUN`.** An operator drives the ten `PROTOTYPE_PROFILE.md` §8 criteria through
a **browser** against the deployed stack, on the synthetic AR corpus, and writes down
everything that breaks. This has never been done and it is the point of the whole road; expect
it to find things (§10). Repairs land in the same stage, in `src/` and `web/src`, by whoever
owns the tree.

Beside it, tests-only: `W15-E2E` fills the reserved `e2e:pc01` — the journey as an automated
browser suite against the deployed origin — which is also the natural repair for `D-1.5`, the
18% of `web/src` that no test reaches and the certification's one named exception.

**Stage B — `PA-01`, by a session that authored none of it.** §5.

## 5. PA-01 — what the checkpoint asserts

Executed **on the server**, from a clean clone, by an independent session, and recorded in
`artifacts/checkpoints/PA-01/report.json` with the commit, the image digests and the migration
head:

1. `deploy.sh` brings the stack up from a clean clone on a machine that has never run it, and the schema the
   running app serves conforms to the frozen `contracts/api/v1/openapi.json` — the same check the gate runs,
   re-run against the deployed process rather than against a build artifact;
2. the browser reaches the app over TLS, and an unauthenticated request does not;
3. a project is created and a real AR PDF is uploaded through the browser, producing an
   immutable version and a verified private object;
4. a live `text_analysis` run completes, with its provider mode and cost visible, and the UI
   distinguishes running, published, partial and failed — criterion 4's UI clause, which the
   `e6eae1e` certification explicitly did not establish;
5. a finding opens at its exact quotation beside the page it came from;
6. an accept, a reject and a later comment are recorded, and the history shows all three;
7. the CSV downloads through the browser with its seventeen columns, its BOM and its CRLF
   intact, and resolves back to the same version and run;
8. the server is rebooted and every canonical row, object and decision survives;
9. each of the five refusals answers with its own typed code **through HTTP**, and a provider
   outage fails the run rather than publishing it;
10. `reset.sh` dumps, wipes and re-initialises; the app comes back empty and working; the dump
    restores the wiped state.

Criterion 10 is the one that makes the switch to real work safe, and it is why the wipe is in
the alpha rather than after it.

## 6. The switch to real use

After PA-01: run `reset.sh` once more to clear every byte the pilot produced, confirm the app
is empty, and begin with real documents. From that moment the measurements P04 wanted —
useful/incorrect/unclear findings, evidence-location correctness, review time, provider
latency, cost and failure rate — come from real use instead of from a corpus, and `OD-17`
(the next corpus shape) can be answered with evidence rather than by decision.

This line does **not** wait for `OD-18`. Named experts with committed slots block
`P4-BHV-01` and nothing else; an operated internal alpha is not a moderated validation session
and does not need one.

## 7. After deployment: the external bucket and the managed cluster

Held deliberately for the wave after PA-01, because they are a configuration change and not a
code change, and doing them before we have a running system would mean debugging two unknowns
at once.

The switch is already possible: `S3StorageSettings` reads `S3_ENDPOINT_URL`, `S3_REGION`,
`S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` and `S3_BUCKET` with no default and no fallback, and
`_build_client` pins `signature_version="s3v4"` with `addressing_style="path"` — which is what
Yandex Object Storage accepts. PostgreSQL is one `DATABASE_URL`.

What that wave must **measure** rather than assume: TLS to the external endpoint under a 25 MiB
upload and a Range read; round-trip latency against the run's timing; egress cost on the CSV and
the PDF stream; the managed cluster's connection limits against the session factory; and one
restore drill from a dump taken against the managed instance. Until those exist, the local
volumes stay the canonical store.

## 8. Estimate, in the unit this programme actually executes in

Measured from this repository's own record, not from the task-row model in `ROADMAP.md` §
Estimates, which prices person-days for a different shape of work:

```
git log --date=format:'%m-%d %H:%M' --pretty='%ad %h %s' --all --since=2026-09-16 \
  | grep -iE "dispatch|close wave|merge\("
```

Wave 10 ran 13:12→18:23 with five parallel streams; wave 12 ran 11:02→12:21 for stage A and
12:30→13:12 for its certification. **A wave here is hours, not days.**

**Wave 13 is not a wave of that shape, and pricing it like one would be the mistake
`estimate in the executor's unit` exists to prevent.** The sweep waves measured above wrote
tests against a stable tree. Wave 13 rewrites ~1 800 lines of a certified surface, migrates 21
test files and authors 43 models: **one orchestration day, plausibly two**, with the golden
corpus of stage 1 the thing most likely to extend it — and the thing most likely to save wave
15 from a false start. Waves 14 and 15 remain of the measured shape, hours each.

On that basis, and stating the assumption plainly: this road is **two to three working days of
orchestration** if nothing surprises us. The waves will not run back to back, because two
things in it are not agent-paced:

- **the server** — access, a hostname, a certificate and a place to put it (§9, R-1);
- **stage A of wave 15**, which is a human at a browser, and whose duration is decided by what
  it finds, not by how fast it is driven.

So: **the engineering is small and the schedule risk is entirely in the server and in the first
live run.** No row here is a commitment, and the first one to be revised will be wave 15's.

## 9. What the owner must rule before dispatch

- **R-1 — the server.** Host, who has root, a DNS name, a TLS certificate (internal CA or Let's
  Encrypt), open ports, and whether the provider proxy is reachable from it. Blocks wave 14.
- **R-2 — the FastAPI pin set.** FastAPI, an ASGI server, the multipart parser and whatever the
  ASGI test client needs, with each licence named in the diff. A `pyproject.toml` change is a
  single-owner task under FF-01 §2.8. Blocks stage 2 of wave 13 — not stage 1, which captures
  the golden corpus against the tree as it stands today and can start immediately.
- **R-3 — the alpha credential.** One shared secret at the proxy, and who holds it. Blocks
  PA-01 criterion 2.
- **R-4 — the documents.** Whether real client PDFs may be uploaded to this server, by whom, and
  what happens to them at the end of the pilot. Nothing in this repository may hold them, and
  `reset.sh` is the answer to the last part — but the first two are not the integrator's call.

## 10. Risks, ranked by what they would cost

1. **The first HTTP run finds what four in-process certifications could not.** Upload
   buffering and timeouts at 25 MiB, the polling loop under real latency, the PDF page render in
   a browser, the CSV's BOM and CRLF through a download. This is not a risk to be mitigated —
   it is the reason for the road. It is ranked first because it is where the schedule moves.
2. **FastAPI answering in its own voice instead of the contract's.** `RequestValidationError`
   and `HTTPException` have their own JSON bodies, and a single unhandled path lets one escape
   with a shape no client of this API has ever been written against — while every suite that
   only checks a status code stays green. The five pinned `details.constraint` values and the
   `additionalProperties` refusal are the specific things to watch. The golden corpus is the
   instrument: it compares bytes, not codes.
3. **The UI is the least-tested surface we have.** `D-1.5`: 34 of 110 modules reached by no
   test, and the one line that renders `terminal_reason` is among them. The browser journey is
   both the exposure and the repair.
4. **Provider instability at run time.** PC-02 measured three failures in seventeen attempts at
   ~133 s each — an 18% attempt-failure rate with **no retry in the executor**. On a desk that
   is an annoyance; in front of an operator it reads as a broken product. The retry policy
   recommended in `P4_CLOSURE.md` §6 becomes a candidate the moment a real user sees it.
5. **A wipe that runs against the wrong thing.** Addressed by T-5, and the guards get tests
   that fail.
6. **Scope creep into the security gate.** An internal alpha on a trusted network is an
   assumption on record. The first request for external access is a different checkpoint, and it
   should be refused here rather than half-built.

## 11. What this plan will not do, and why that is deliberate

No multi-tenancy, no in-app authorization, no retention or legal hold, no HA or DR, no backup
rotation beyond the dump the wipe takes, no job/attempt framework, no remote workers, no OCR,
no second discipline. Each is either waiting on evidence this deployment is meant to produce,
or belongs to the security gate that external use requires. Building any of them now would
delay the only thing on this road that can still tell us the product is wrong.

## 12. What is bespoke today, and where each piece lands

Measured against §2.5. **Now** means inside this road; **release** means the line that ends in
a clean v1 and is scheduled by evidence, not by taste; **keep** means the bespoke thing is the
right thing and a library would be the regression.

| Piece | Today | Disposition | Argument |
|---|---|---|---|
| `api/routers/http.py` — `Request`/`Response`/`Route`/`Router` | ~260 hand-written lines | **now** — retired by `T-1` | a parallel framework nobody else knows, over a contract a real one can serve |
| `api/routers/multipart.py` | `email.parser` over a buffered body | **now** — FastAPI + its multipart parser, with the two-guard size rule preserved | the same code exists, tested, in the stack |
| `api/schemas/**` | 922 lines building wire dicts by hand | **now** — Pydantic models named after the contract's schemas | this is the single largest bespoke surface, and it is exactly what Pydantic is |
| `tests/e2e/pc01/driver.py` | a bespoke in-process client | **now** — ASGI test client; the driver funnels every call through one method, so it is a small change | a test harness that models the transport is a second implementation of it |
| `bootstrap/composition.py` | manual wiring, one place | **now, partially** — the composition root stays the single place adapters are built; FastAPI dependencies expose them, and dependency overrides replace the bespoke test wiring | keeps the seam, drops the parallel mechanism |
| `bootstrap/settings.py` | hand-read environment with typed refusals | **release** | it is certified, its refusals are pinned by tests, and `pydantic-settings` would buy uniformity rather than capability. Worth doing when something else opens the file |
| `runs/executor.py` | one sequential in-process executor | **release, evidence-driven** | PC-02 measured an 18% attempt-failure rate with no retry; a task runner is a P05 candidate the moment a live user meets it, and picking one before that is guessing |
| no authentication | proxy-level for the alpha (`T-6`) | **release** — OIDC/JWT through FastAPI dependencies | the alpha's assumption is a trusted network; an identity model built before we know the users is the guess this programme exists to avoid |
| `shared/db/**`, `storage/s3.py` | SQLAlchemy, Alembic, boto3 | **keep** | already the relevant stack |
| `web/**` | Next.js, TanStack Query, a generated client | **keep** | already the relevant stack, and the client is generated from the contract rather than hand-written |
| the error catalog and `ErrorEnvelope` | 20 frozen codes, one renderer | **keep** | a domain contract, not a framework substitute. FastAPI is made to answer around it; §10 risk 2 is about exactly that |

The row that matters most for §2.5's second rule is the last one in the **now** group: the
composition root. It is the only place in this tree that knows how the application is
assembled, and every swap above is cheap because that knowledge is in one file. Whatever wave
13 does to it, it does not scatter it.
