# Short road to a deployable alpha

Written 2026-09-17. Base `c96ccf3` on `planning/prototype-roadmap`, with PC-01 re-certified
at `e6eae1e` the same day. **Candidate**: four owner rulings in §9 are dispatch
prerequisites, and nothing below is dispatchable until they exist.

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
| any process that listens on a socket | `grep -rn "serve_forever\|uvicorn\|asgi\|wsgi" src tools tests Makefile` — empty; `pyproject.toml` pins no HTTP framework |
| an application image or any packaging | `find . -iname "*Dockerfile*"` finds only `infra/local/docker-compose.yml`, which runs PostgreSQL and MinIO and nothing of ours |
| one run of the UI against the backend | `web/src/shared/api/transport.ts` calls `NEXT_PUBLIC_API_BASE_URL`; nothing has ever served it. `e2e:pc01` is a reserved name that fails on purpose (`web/scripts/reserved-forwarder.mjs`) |
| any authentication | `src/auditmanager/access/` holds a README and no code |
| a wipe, a dump or a restore | no script under `infra/`; `make down` keeps the volumes |
| UI rendering under test | `DEBT_REGISTER.md` D-1.5: 34 of 110 `web/src` modules reached by no test; criterion 4's UI clause is the certification's one named exception |

What is **not** missing, and is why this road is short: the twelve operations, the typed error
envelope, the append-only ledger, migrations, the checksum-verified blob store, the frozen
OpenAPI and a generated client against it. `dispatch()` in
`src/auditmanager/api/routers/errors.py` already guarantees a typed answer on every path out,
including a miss and an unclassified fault. A transport does not have to invent one.

## 3. Six decisions this plan makes, with the argument for each

**T-1 — an ASGI adapter over the existing `Router`, and uvicorn. Not FastAPI.**
`Request`/`Response`/`Router`/`dispatch` already are the edge, and `routers/__init__.py`
already declares `BASE_PATH = "/api/v1"`, which the frozen contract's `servers[0].url` also
declares. The adapter reads a scope and a body, calls `dispatch`, writes the response — on the
order of a hundred lines. FastAPI would introduce a **second routing authority** over a frozen
contract: two places that decide what `/api/v1/runs/{run_id}` means, and a new way for the
implementation to drift from `contracts/api/v1/openapi.json`. `PROTOTYPE_PROFILE.md` §2 names
FastAPI as the *direction*; it also says framework architecture is implemented only where the
journey needs it. This journey does not need it.

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

### Wave 13 — a service, not a library

| Stream | Writes | Delivers |
|---|---|---|
| `W13-HTTP` | `src/auditmanager/api/asgi.py`, `serve.py`, health module, `pyproject.toml` pin, `tests/integration/transport/**` | an ASGI app over `dispatch`, a `python -m` entrypoint, graceful shutdown, a body cap above `multipart.MAX_BODY` that refuses larger bodies without buffering them, `/api/v1` prefix stripping with anything outside it a typed 404, the health plane on its own port |
| `W13-EQV` | `tests/e2e/transport/**` only | **the transport-equivalence suite**: each of the twelve operations driven twice — in-process through `tests/e2e/pc01/driver.py` and over a real socket — asserting identical status, body bytes and contract headers; plus the refusals (404, 405, 422), the 26 MiB boundary through the socket, a Range request on `streamDocumentVersionContent`, and `X-Correlation-Id` surviving the wire |

The pin is the one owner ruling this wave needs (§9, R-2): `pyproject.toml` is `P1-INT-00`'s
file and FF-01 §2.8 makes a pin change a new single-owner task.

Acceptance: `make gate` at or above 1505/5/167 with the new suites added, and the equivalence
suite green — which is what lets the next wave treat HTTP as a solved problem rather than as a
variable.

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

1. `deploy.sh` brings the stack up from a clean clone on a machine that has never run it;
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

On that basis, and stating the assumption plainly: waves 13, 14 and 15 are **one to two working
days of orchestration** if nothing surprises us. They will not run back to back, because two
things in this road are not agent-paced:

- **the server** — access, a hostname, a certificate and a place to put it (§9, R-1);
- **stage A of wave 15**, which is a human at a browser, and whose duration is decided by what
  it finds, not by how fast it is driven.

So: **the engineering is small and the schedule risk is entirely in the server and in the first
live run.** No row here is a commitment, and the first one to be revised will be wave 15's.

## 9. What the owner must rule before dispatch

- **R-1 — the server.** Host, who has root, a DNS name, a TLS certificate (internal CA or Let's
  Encrypt), open ports, and whether the provider proxy is reachable from it. Blocks wave 14.
- **R-2 — the uvicorn pin.** A `pyproject.toml` change is a single-owner task under FF-01 §2.8.
  Blocks wave 13.
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
2. **The UI is the least-tested surface we have.** `D-1.5`: 34 of 110 modules reached by no
   test, and the one line that renders `terminal_reason` is among them. The browser journey is
   both the exposure and the repair.
3. **Provider instability at run time.** PC-02 measured three failures in seventeen attempts at
   ~133 s each — an 18% attempt-failure rate with **no retry in the executor**. On a desk that
   is an annoyance; in front of an operator it reads as a broken product. The retry policy
   recommended in `P4_CLOSURE.md` §6 becomes a candidate the moment a real user sees it.
4. **A wipe that runs against the wrong thing.** Addressed by T-5, and the guards get tests
   that fail.
5. **Scope creep into the security gate.** An internal alpha on a trusted network is an
   assumption on record. The first request for external access is a different checkpoint, and it
   should be refused here rather than half-built.

## 11. What this plan will not do, and why that is deliberate

No multi-tenancy, no in-app authorization, no retention or legal hold, no HA or DR, no backup
rotation beyond the dump the wipe takes, no job/attempt framework, no remote workers, no OCR,
no second discipline. Each is either waiting on evidence this deployment is meant to produce,
or belongs to the security gate that external use requires. Building any of them now would
delay the only thing on this road that can still tell us the product is wrong.
