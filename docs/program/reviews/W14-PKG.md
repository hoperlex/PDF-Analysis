# W14-PKG — the build and the wipe

**Session:** `W14-PKG`, wave 14 of the alpha road.
**Worktree:** `/root/w14pkg`, branch `agent/w14-pkg`, from `origin/dev`.
**HEAD on arrival:** `4a8cf23` — *docs: close wave 13 — the twelve operations serve HTTP under FastAPI*.
**Instance:** `gate-w14a` — PostgreSQL 55740, S3 59340/59341, database `audit_w14a`, bucket `auditmanager-gate-w14a`.
**Alpha stack instance (separate, and mine too):** `auditmanager-w14a`, one published port, 31480.

Everything below was built **and driven** on this host. Nothing was deployed; §6 names where
that boundary bit.

> ## Erratum — 2026-09-21, by the integrator
>
> **A review record is history and is not rewritten; it is annotated.** This file states one
> thing that was measured to be false, twelve waves after it was written, and the sentence is
> left standing below with an `[ERRATUM E-1]` marker so that anyone who has already quoted it
> finds the correction at the same address.
>
> **`E-1` (§2, the provider-credential channel).** The claim that a credential kept out of
> `--env-file` *"therefore never appears in `docker compose config` output"* is wrong in its
> second half. **It appears.** Compose v5.3.1 resolves `env_file:` into `environment:` and
> prints the value in clear; measured with a sentinel, `config | grep -c PROXY_LLM_TOKEN`
> returns `1`. What the channel genuinely buys is that those names never enter compose
> **substitution** — real, and not what the sentence said. `config` output must be treated as a
> secret: it also prints the API token and both the database and object-store passwords. The
> full measurement, and the contrasting result for the TLS private key (a bind mount is a path;
> **zero** hits for the key material), are `DEBT_REGISTER.md` D-42, found by `W26-HOST`.

## 1. What was built

| Path | What it is |
|---|---|
| `infra/deploy/Dockerfile.api` | the twelve operations under uvicorn, plus `T-3`'s health plane |
| `infra/deploy/Dockerfile.web` | `npm ci`, `npm run build`, `next start` |
| `infra/deploy/serve.py` | the entry point: **one built application, two ports** |
| `infra/deploy/compose.server.yml` | PostgreSQL, MinIO, bucket-init, migrate, api, web, proxy |
| `infra/deploy/proxy/nginx.conf` | `T-2` — the web app at `/`, the API at `/api/v1`, one origin |
| `infra/deploy/reset.sh` | `T-5` — the guarded wipe, and the restore of its own dump |
| `infra/deploy/object_attrs.py` | the third part of a dump (§4) |
| `infra/deploy/env/alpha.env.example` | the deployment environment — **not `.env`** (§3) |
| `infra/deploy/env/provider.env.example` | the model credential, alone, owner-written on the host |
| `infra/deploy/README.md` | the runbook |
| `src/auditmanager/bootstrap/settings.py` | one field: `api_token`, required at construction |
| `tests/integration/composition/test_api_token_channel.py` | 10 cases |
| `tests/integration/composition/test_reset_script_refusals.py` | 21 cases, one per guard plus its mutant |

**Nothing packaged the application before this.** `find . -iname "*Dockerfile*"` found none; the
brief's premise held.

**Three decisions worth naming.**

*The API image is not just `src/`.* Four things under the runtime resolve a repository path
from `auditmanager.__file__`, and the first container built without them died on **import**,
not at first use: `contracts/domain/v1/error-codes.json` is read at module scope in
`shared/errors/catalog.py`. Measured with `grep -rn "parents\[" src/`, the image carries
`contracts/` (876K), `fixtures/recorded/` (72K) and the single file `docs/program/P02_LOCK.json`.
The other 55M of `fixtures/` is corpus and is deliberately absent.

*uv is pinned from the Makefile's own bytes.* The build stage copies `Makefile`, extracts
`UV_VERSION` and the eighteen `UV_HASHES` wheel hashes, and installs `--require-hashes`. A
second copy of a version string and eighteen hashes in a Dockerfile is a second thing that can
drift; the Makefile already argues for reading a pin out of bytes rather than a variable.
`uv sync --frozen --no-dev` then builds the same closure the gate ran against, minus the `test`
group — `httpx` is a client library and has no business in a deployed application's closure,
which is what `pyproject.toml` says where the pin was made.

*Measured image sizes:* api **401 MB**, web **1.21 GB**. The web image is large because
`next start` needs `node_modules`, `.next`, `package.json` and `next.config.mjs`, so the whole
build tree ships. `output: "standalone"` would roughly halve it and is **not** done: that
switch lives in `web/next.config.mjs`, which this session does not own. Recorded as a cost, not
hidden.

## 2. What was brought up and driven

```
docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml up -d --build
```

Five services healthy: `postgres`, `s3`, `web`, `api`, `proxy`, with `s3-init` and `migrate`
having run to completion. All of the following is through the **one published port**, 31480,
which is the proxy's — nothing else is reachable from the host.

| What | Evidence |
|---|---|
| the web app at `/` | `GET /` → the PC-01 shell, `am-app__instance` = `alpha` |
| **no credential** | `GET /api/v1/projects` → `401` `{"error_code":"authentication_required",...}` |
| **wrong credential** | `Authorization: Bearer nope` → `401` |
| **the configured token** | → `200 {"items": [], "page": {"next_cursor": null}}`, `X-Correlation-Id` present |
| `createProject` | → `201`, `prj_01M2RP57JJFQZ77VMFP3H6MRAS` |
| idempotent replay | same `Idempotency-Key` → the same project, same `created_at` |
| the contract's strictness is live | `-F title=...` → `422 validation_failed`, `details.constraint = additionalProperties` (the part is `display_title`) |
| `uploadDocument` | a real 58 978-byte PDF → `201`, `page_count: 8`, sha `6d53674f…` |
| `getDocumentVersion` | → the same manifest |
| **a Range read** | `Range: bytes=0-31` → `206`, `Content-Range: bytes 0-31/58978` |
| the object is really in the bucket | `blobs/7K/DZ/7KDZE8SQTZ9K23JYB742HG7K8J`, 58 KiB |
| the bucket is private | `mc anonymous get` → `private` |

**`T-2` proved rather than asserted.** The client bundle carries `let e="/api/v1"` — a relative
path — and `grep` over `.next/static` finds no baked origin at all. The image names no host.

**The proxy has to strip the base path, and the first version of mine did not.** Measured
against the running container: `GET /projects` → 401, `GET /api/v1/projects` → 404. The frozen
document declares `servers: [{"url": "/api/v1"}]` and `api/app.py` says the twelve paths "are
declared relative to it rather than carrying it", so the application serves `/projects` at its
own root and **mounting the base path is the deployment's job**. The out-of-repo harness settled
this the same way and wrote it down — `bridge.py` does `target = self.path[len(PREFIX):]`. A
proxy that forwarded the prefix intact answered `404 not_found` to all twelve operations with a
perfectly valid `ErrorEnvelope`, which is the most confusing way this could have failed. Fixed
with `location = /api/v1` and `location /api/v1/` plus `proxy_pass http://api:8000/`, and the
reasoning is in the file.

## 3. The token channel, and the construction-time test

`W13_CLOSURE.md` §7 called this the load-bearing one and it was.

**The brief's instruction to put the key in `.env.example` is wrong against the tree**, and the
tree says so in three places. The Makefile parses `.env` against `FROZEN_ENV_NAMES`, a strict
allowlist of exactly the fifteen names FF-01 §3 freezes, and refuses every other name with an
explicit error whose own text is *".env configures this lane's services. It does not carry tool
options, credentials for other systems, or anything that selects what code runs."*
`bootstrap/settings.py` opens with the same reasoning for `AUDITMANAGER_PROVIDER_MODE`, citing
`P02_LOCK.json`. And `api/security.py:33` — the module that reads the token — already records
that it is deliberately *"not in `.env.example` and not on `AppSettings`"*. Putting the token in
`.env` would **break `make gate`** rather than configure anything, and would be an FF-01 §3
change besides.

So the channel is `infra/deploy/env/alpha.env.example`, which is what the roadmap's own wave-14
row asked for: *"a documented environment that never places a provider credential in the `.env`
the Makefile allow-lists"*. The provider credential goes one step further out, into
`env/provider.env`, which is written on the host by the owner, is never passed to `--env-file`,
and therefore never appears in `docker compose config` output **[ERRATUM E-1: the second
clause is false — see the erratum at the head of this file]** — `OWNER_RULINGS` §3 and
`LIVE_RUN_INSTRUCTIONS.md` §2.

**What changed in `src/`, and it is one field.** `AppSettings` gains `api_token: str`, resolved
by the same `_require` every other mandatory value uses. `API_TOKEN_ENV` is spelled in
`settings.py` rather than imported from `api/security.py`, because `bootstrap` sits below `api`
and must not depend upward; a test pins the two spellings equal so the duplication cannot drift.

**The construction-time test** is `test_api_token_channel.py`, ten cases:

* building with the token absent raises `ConfigurationError` **naming the variable** — not a 401
  on a first request, and no application object at all;
* an empty or whitespace token is the same as an absent one, so the two halves cannot disagree
  about what "configured" means;
* the same environment **with** the token builds twelve operations — the discriminator, without
  which both refusals would pass just as happily against a composition root broken for some
  other reason;
* `load()` alone refuses, so anything that resolves settings inherits it;
* `create_asgi_app` cannot produce an ASGI application at all, which is the whole distinction:
  there is nothing to send a first request to;
* the Makefile's allowlist is read from its bytes and compared against the fifteen names written
  out as a literal tuple, and the token is asserted absent from it;
* `.env.example` does not assign it and `alpha.env.example` does, with a non-empty value;
* `compose.server.yml` carries `${AUDITMANAGER_API_TOKEN:?…}`, a **second, independent** refusal
  one layer out: compose will not render the stack at all without it.

Blast radius of making it required: two files, both owned by this session
(`test_composition_root.py`, `test_settings_defaults.py`), whose `_base_env()` now names a literal
token. Every other construction site in the tree — the `W13-BASE` baseline journey, the e2e
driver, the api driver, the size-guard suite — already injected one. `create_documentation_app()`
never calls `load`, so the conformance gate still reads a document on any checkout, and
`test_an_application_with_no_configured_token_refuses_everything` still passes because it builds
through `create_asgi_app(application=…)`, which bypasses the composition root.

## 4. The wipe, and every refusal shown able to fail

`infra/deploy/reset.sh`. `R-4` — real client documents, wiped at the end of the pilot — is why
this is load-bearing rather than tidy.

**Order:** every guard before any connection is opened → `pg_dump` and a full bucket mirror into
`dumps/<instance>-<UTC stamp>/` → **the dump is verified** → and only then drop, re-migrate,
purge and re-initialise.

**The target is always this stack.** Every destructive step runs through
`compose.server.yml`, so a `DATABASE_URL` exported in a stale shell cannot be reached from here
at all. That is the second half of "a stale environment cannot point it at something else"; the
typed `--database` and `--bucket`, which must equal the configured ones, are the first.

**Eleven guards, each delimited by `# >>> guard: <name>` markers, each with two tests.**

| Guard | Refuses |
|---|---|
| `known-options` | an unrecognised option — `--dryrun` silently ignored would run the destructive path |
| `destructive-flag` | neither `--dry-run` nor `--yes-destroy-everything` nor `--restore` |
| `one-mode` | more than one of the three |
| `names-required` | a missing `--database` or `--bucket`, **even for `--dry-run`** |
| `env-file-present` | an unreadable environment — an unverifiable target is not a target |
| `instance-configured` | an environment naming no `ALPHA_INSTANCE`/`POSTGRES_DB`/`S3_BUCKET` |
| `database-matches` | a typed database that is not the configured one |
| `bucket-matches` | a typed bucket that is not the configured one |
| `compose-file-present` | a missing compose file — then it has no target it is allowed to reach |
| `dump-verified` | an empty dump, an unreadable one, a short mirror, or a short attribute sidecar |
| `restore-complete` | a `--restore` directory that is not one of this script's own dumps |

**Each one is shown able to fail**, and by deletion rather than by assertion:
`test_reset_script_refusals.py` reads the markers, produces a copy of the script with **exactly
one guard block removed**, runs the same invocation, and asserts the refusal is gone. A message
can be produced by a guard that happens to be unreachable; a deletion cannot. A meta-test pins
the marker count at 11 and asserts every marker has a case, so a twelfth guard added without a
test fails here rather than in a wipe.

**Nothing in that suite can destroy anything, and not by hoping.** `docker` is replaced on
`PATH` with a stub that records its arguments and exits 0, so even a mutant that runs to the end
reaches no database and no bucket. The stub is also the instrument: for the guards that run
before any connection, *an empty call log is the evidence that the refusal came first*. For
`dump-verified` the log is the evidence the other way — `pg_dump` appears in it and `DROP SCHEMA`
does not, and in the mutant `DROP SCHEMA` does.

**Driven for real, against the live stack.**

*Refusals, on a host that really has two databases:*

```
$ reset.sh --database audit_w14a --bucket auditmanager-alpha --dry-run
reset.sh: REFUSED: the typed database is not the configured alpha database.
    typed     : audit_w14a
    configured: auditmanager_alpha   (POSTGRES_DB in …/env/alpha.env)
```

`audit_w14a` is this session's **gate lane** database, which exists, on this host, with data in
it. The wipe refused to touch it. That is the `T-5` case, demonstrated rather than described.

*`--dry-run`* listed all 17 tables with their row counts and the one object in the bucket, and
deleted nothing.

*The real run* dumped (91 799 bytes plus the object mirror plus the sidecar), verified, dropped,
re-ran all five migrations to head, purged and re-initialised the bucket private. After it:
`listProjects` → `{"items": []}`, the version → `404`, the bucket → 0 objects, policy `private`.

*The restore* — `reset.sh --restore <dump dir>` — brought both halves back and the API served the
document's bytes again at `200`, **sha256 identical to the original fixture**
(`6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f`).

**Two bugs that only running it could find.**

1. `pg_restore --list /dev/stdin` cannot read a dump that `file(1)` calls a valid "PostgreSQL
   custom database dump - v1.16-0" — it answers *"did not find magic string in file header"*. The
   readback guard therefore **refused a wipe that should have proceeded**. Safe direction, still a
   bug: a guard that refuses a good backup is a guard that gets disabled at two in the morning.
   `pg_restore --list` reading stdin with no filename works, and the reason is in the file.
2. **`mc mirror` is not a backup of an object.** The bytes came home with
   `Content-Type: application/octet-stream` and no `X-Amz-Meta-Content-Sha256`, and the storage
   adapter then refused them — `422 validation_failed`, `details.field = content-sha256`,
   `constraint = "recorded on every object this adapter publishes"`. The restored instance
   **listed the document and 422'd on its bytes**, which is worse than an empty one because it
   looks recovered. So a dump is now three things — `database.dump`, `objects/`, and
   `objects.attrs` written by `object_attrs.py` from `mc --json stat --recursive` — `--restore`
   reattaches the attributes with `mc cp --attr`, and `dump-verified` refuses a run whose sidecar
   is short or carries an empty sha. `object_attrs.py` runs inside the **API image**, because that
   is the one container this stack is guaranteed to have an interpreter in; the deploy host is
   assumed to have docker and nothing else.

## 5. The health plane — verified, not rebuilt

`W13-API` built it and built it right. `api/health.py` is a **separate FastAPI application**, not
a route with the dependency excluded, with `openapi_url=None`, `/healthz` and `/readyz`, and a
readiness that reports whether an application was wired rather than a constant. Its 21 tests pass
here. It is off the contract: the served document has 10 paths and 12 operations and neither
health path is among them.

**What I found, and it is the gap wave 14 had to close: nothing serves it.** `build_health_app`
had no caller outside tests, and `api/app.py:main` constructs and prints without binding a
socket — deliberately, so an operator can ask "would this process start?" for free. There was no
process anywhere in the tree that put either application on a port.

`infra/deploy/serve.py` is that binding, and it is one process on purpose. `health.py`'s
readiness reports *whether this process is wired*; a health plane in a second container would
report on its own wiring and tell the proxy nothing about the process actually serving
`/api/v1`. So the application is built once and the same object is handed to both apps. The
health server runs in a daemon thread — `uvicorn.Server.serve` installs signal handlers only on
the main thread, so the API server keeps the main thread and the SIGTERM that stops the
container, and a daemon thread cannot outlive a crashed API server and leave a container that
still answers `/healthz` while serving nothing.

Measured inside the running container:

```
:8000 /projects        -> 401      (the authorized surface)
:8000 /openapi.json    -> 200      (the served document)
:8001 /healthz         -> 200 {"status": "ok"}
:8001 /readyz          -> 200 {"status": "ok", "wired": true}
```

`wired: true` is the part that is only true because of the single-process design. Through the
public origin, `/healthz`, `/readyz` and `/api/v1/healthz` are all `404`: it is not proxied, and
that is deliberate — nothing outside needs it and publishing it would add a surface nobody
authorized. The compose health check polls `:8001/healthz` over the compose network, which also
means an **unconfigured** deployment is still pollable, exactly as `security.py` claims.

## 6. The boundary with `R-1`

Three things stopped at it, and each is a claim about a server rather than about code.

* **TLS.** `R-1` is ruled and the roadmap's wave-14 row asks for a proxy terminating it. There is
  no host name, no certificate and no DNS, and a `listen 443 ssl` block naming a certificate path
  that has never existed is a document, not a deliverable. The proxy terminates HTTP on one port;
  the TLS layer is added when the host is. Everything else about `T-2` — one origin, a relative
  base URL, no CORS surface — is independent of TLS and is done and proved.
* **`deploy.sh`.** `W14-OPS` owns it in the roadmap and it is not in this brief's build list. It
  could not be exercised here anyway: *"run it twice and the second changes nothing"* and *"a
  deliberately broken build rolls back and leaves the previous version serving"* are both
  assertions about a server with a previous version on it.
* **The provider proxy.** Whether the model proxy is reachable from the alpha host is one of the
  five things `OWNER_RULINGS` §3 still needs. The stack was driven in `recorded` mode throughout;
  no model call was made and none could have been, since no credential is in the tree.

## 7. What was false in the brief, and one thing wave 13 owed that is worse than described

**1. "the key in `.env.example`" — no.** §3. It would break `make gate`, and `api/security.py`
already said so.

**2. "the frontend has no branch for 401" understates it: the frontend never sends a credential
at all.** `grep -rn "Authorization\|Bearer" web/src web/tests web/scripts` finds nothing outside
the generated `openapi.json`'s prose. `shared/api/transport.ts` builds its headers from the
operation descriptor and the input and attaches no `Authorization`; there is no configuration
channel for a token in the web tier and no place one could go — `NEXT_PUBLIC_*` values are
compiled into the browser bundle, as `env.ts` itself warns. So the deployed web app does not get
a 401 it fails to branch on; **it gets a 401 on every one of the twelve operations and cannot do
otherwise.** This is not cheap and it is not mine — `web/src` is outside this session's ownership
and the fix is a design decision (a server-side route that holds the token, or a sign-in flow),
not a patch. It is a `W15-RUN` blocker: the first live journey through a browser cannot start
until it is answered.

**3. The gate figure in the brief is right, and I checked it rather than assuming.** §8.

Checked and **true**: no Dockerfile in the tree; `checkout_is_unchanged` really is at
`tests/integration/foundation/conftest.py:542`; `T-3`'s health plane exists and is off the
contract; `seam-operations.contract.test.ts` and `openapi-drift.contract.test.ts` both count the
operations; `OD-16` and FF-01 §2.8 say what the brief says they say; the contract's own upload
schema says **25 MiB** (`26214400` bytes), not 26.

## 8. The gate, and elapsed wall-clock

```
GATE OK: battery, foundation, frontend and whitespace all pass
1726 passed, 5 skipped, 168 subtests passed in 200.24s
foundation 35 passed, frontend 440 passed (35 files)
```

**The brief's 1693/5/168 was correct, and this is how I know rather than assuming.** A detached
worktree at the arrival commit `4a8cf23`, collected with the gate's own ignore set and this
worktree's interpreter:

```
4a8cf23  1663 collected  (+ 35 foundation, which needs a lane)  = 1698 = 1693 passed + 5 skipped
HEAD     1696 collected  (+ 35)                                 = 1731 = 1726 passed + 5 skipped
```

The difference is **33**, and all 33 are this session's two new files — the two existing files it
edited collect 31 at both commits. Skips and subtests are unchanged. The worktree was removed
after the measurement.

The gate was run only against a **committed** tree, after `git status --porcelain` was empty, so
`checkout_is_unchanged` (`tests/integration/foundation/conftest.py:542`) had nothing to catch.
The alpha stack was left running during the gate; it is a different compose project on a
different network publishing one port the gate does not use, and it did not interact.

**Elapsed wall-clock: 02:42:54 → 03:16:01 +05:00, 33 minutes.** Of that, roughly 9 minutes was
image building and bringing the stack up, 4 minutes the gate, and one unplanned detour: the host
filesystem was **100% full** on arrival at the first `docker compose up`, which killed
`initdb` with *"No space left on device"*. Reclaimed 3.4 GB of docker build cache and 1.3 GB of
archived systemd journals — both caches, no project state, and no other session's worktree,
venv, volume or container was touched. MinIO also refused a write at under 1 GB free with
*"Storage backend has reached its minimum free drive threshold"*, which is worth knowing before
the same thing happens on the alpha host: **the deploy host needs headroom, and the first symptom
is a `dependency_unavailable` on `blob_storage` that looks like an application fault.**

## 9. Left running

The alpha stack (`auditmanager-w14a`) is up on port 31480 with the restored fixture document in
it, so the next session can drive it without rebuilding. `docker compose --env-file
infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml down` stops it; add `-v` to remove
its volumes. `infra/deploy/env/alpha.env` and `env/provider.env` are git-ignored and hold
disposable local values only.

No tag, no push, no merge to `main`. Branch `agent/w14-pkg`, three commits on top of `4a8cf23`.
