# The alpha deployment — the runbook

Everything here was built and **driven** by `W14-PKG` on the development host. Nothing in
it has run on a server, and it deliberately stops short of doing so: `R-1` is ruled (the
owner's own VPS) but the host name, who holds root, which ports may be opened and when
access appears do not exist yet. Where that boundary bit, it is named below rather than
guessed past.

`T-4`: **none of this is a `make` target.** `OD-16` makes a tenth root target an FF-01
freeze-break needing an explicit break record, and nothing here needs one. The Makefile
stays the developer's gate; these are scripts and one compose file, invoked directly.

**The ordered procedure for a machine that has never run this is**
**`docs/program/DEPLOYMENT_RUNBOOK.md`.** This file is the reference behind it: one
section per file, the mechanism, and the measurement behind each decision. Neither
restates the other.

`infra/local/docker-compose.yml` is a different thing and neither replaces the other. That
is the developer's disposable service pair, driven only by the frozen `make up`/`make
down`. This is the deployed stack.

## What is here

| Path | What it is |
|---|---|
| `Dockerfile.api` | the 148 operations under uvicorn, plus `T-3`'s health plane |
| `Dockerfile.web` | `npm run build`, then `next start` |
| `serve.py` | the entry point: **one built application, two ports** |
| `compose.server.yml` | the stack: PostgreSQL, MinIO, migrate, release-notes, api, worker, web, one proxy. Two database urls (`PROD-04`): `DATABASE_URL`, the application role's, reaches `api` and `worker`; `MIGRATOR_DATABASE_URL`, the owner's, reaches `migrate` and `release-notes` only |
| `apply-grants.sh` | `PROD-04-DB-ROLES-01` — the one idempotent step that gives the application role (`ALPHA_APP_DB_USER`) exactly the rights `scripts/recovery/grant_classification.py` says, and nothing that changes the schema; `--check` verifies, `--config-only` judges the settings. Run by `deploy.sh` between `migrate` and `up`, and by `reset.sh` and `copy-serve.sh restore-db` after a restore (a `--no-privileges` dump carries none). Runbook §16 |
| `proxy/nginx.conf` | `T-2` — the web app at `/`, the API at `/api/v1`, one origin |
| `proxy/tls-server.conf` | the TLS server block. **nginx never loads it unless a certificate is there** |
| `proxy/enable-tls.sh` | the switch: the image runs it before nginx starts, and it asks one question |
| `proxy/trusted-proxies.sh` | `REAL-IP-EDGE-01` — the other start-up hook: turns `ALPHA_TRUSTED_PROXY_CIDRS` into the proxy's `set_real_ip_from` lines, or into none |
| `proxy/compose.tls.yml` | `PROD-01-TLS-ACME-01` — the 443 overlay: it publishes container port 8443 as public 443 and does nothing else; `deploy.sh` passes it only for a deploy that has `ALPHA_PUBLISH_HTTPS=yes`, a certificate **and a clean credential gate** (`PROD-02`) |
| `proxy/acme-challenge.conf` | `PROD-01-TLS-ACME-01` — the challenge listener (public port 80): the ACME webroot and a redirect to HTTPS, **no route to any other tier** |
| `proxy/watch-certificate.sh` | `PROD-01-TLS-ACME-01` — the proxy's timer: when the pair on the volume changes it re-runs the switch, tests the configuration and reloads nginx |
| `proxy/tls/` | no longer mounted by anything; kept, with its ignore rule, so a key dropped there out of habit still cannot be committed |
| `../acme/` | `PROD-01-TLS-ACME-01` — the ACME client as a service of the same project: `Dockerfile`, `client.pin` (the exact client version), `entrypoint.sh`, `export-pair.sh`, `check-served.sh`, and `compose.acme.yml`, the overlay passed whenever `ALPHA_CERT_NAME` is set (it also declares the client's own network, `acme-edge`, shared only with the proxy) |
| `lib/proxy-listeners.sh` | `PROD-01-TLS-ACME-01`, `PROD-02` — the one place that decides which of the proxy's three listeners a deploy has, and the one place that asks the default-credential gate (`deploy.sh`, `verify-deployed.sh`, `reset.sh --restore` and `copy-serve.sh restore-db` all call it) |
| `deploy.sh` | `PA-01` criterion 1 — bring this clone up, and refuse to call it deployed until the stack has answered |
| `reset.sh` | `T-5` — the guarded wipe, and the restore of its own dump |
| `purge-product-data.sh` | `STAND-PURGE-TOOL-01` — delete the stand's product data (projects, documents, runs, findings, decisions, price lists, their objects) and **keep the accounts and the norm corpus**; dumps and verifies first. Since `PROD-04` it runs the python half as the owner (`MIGRATOR_DATABASE_URL`). `docs/program/STAND-PURGE-TOOL-01.md` |
| `verify-deployed.sh` | `D-27` — is the stack in front of you this tree? |
| `reload-proxy.sh` | `D-27` — the step after a rebuild that everyone forgets |
| `object_attrs.py` | the third part of a dump: each object's S3 attributes |
| `receive-bundle.sh` | `W54-TRANSPORT-01` — the inbound key's forced command on the stand: `receive`, `status`, `import`, `report`, `requeue`; the boundary for an account that can run `docker` |
| `push-bundle.sh` | `W54-TRANSPORT-01` — this host's side: re-hash a bundle, send it as `receive <KEY> <size>` |
| `lib/forced-command.sh` | the one verb dispatcher every forced-command key uses, the bundle-name grammar and the bundle-tree rule both ends apply; since `W54-STAND-COPY-01` also the copy record's canonical layout and its reader/rewriter |
| `copy-serve.sh` | `W54-STAND-COPY-01` — the copy key's forced command on the stand, installed apart from the checkout and acting on `ALPHA_CHECKOUT`: `capacity`, `dump-db`, `inventory-s3`, `fetch`, `attest` (and `attest --test-data`, `R-110`), `verify-objects`, `restore-db`, `resume`, `status`. Runbook §13 |
| `capacity-probe.sh` | `W54-STAND-COPY-01` — free disk per filesystem, available RAM, swap and load; refuses below a stated need. The stand's `capacity` and this host's heavy-step stop rule (`W54-PLAN.md` §3.9) |
| `pull-copy.sh` | `W54-STAND-COPY-01` — this host's side: fetch one copy's record, dump and inventory through the copy key and check them against the record |
| `env/alpha.env.example` | the deployment's environment. **Not `.env`** — see below |
| the `<instance>-web-sessions` volume | `R-51` — the session register, mounted by `web` and by nothing else. See below |
| `env/provider.env.example` | the model credential, alone, written on the host by the owner |

## Bring it up

Run from the **repository root** — both builds need `src/`, `db/`, `contracts/`,
`uv.lock` and `web/` in their context.

```
cp infra/deploy/env/alpha.env.example infra/deploy/env/alpha.env
chmod 600 infra/deploy/env/alpha.env          # then edit EVERY value in it
cp infra/deploy/env/provider.env.example infra/deploy/env/provider.env
chmod 600 infra/deploy/env/provider.env

infra/deploy/deploy.sh
```

**`deploy.sh` is the command**, and the raw `docker compose` line below is what it runs in
the middle. Use the script: it refuses a stale environment, an unedited example, an
incomplete clone and another instance's port *before* it builds anything, and afterwards it
refuses to report success until the stack itself has answered four questions — see
**Deploying it** below. The compose invocation is kept here because an operator debugging a
deployment needs to know what the script is doing, not because it is the way to deploy.

```
docker compose --env-file infra/deploy/env/alpha.env \
  -f infra/deploy/compose.server.yml up -d --build
```

`migrate` runs once and exits; `release-notes` then loads authored revisions
and exits; `api` waits for both. Migrations and release loading are never run
by a serving process — two replicas starting together would race the same work.

### Normative corpus in this alpha candidate

The API image contains migrations through `0013_norm_embeddings` and the deterministic,
transaction-scoped corpus loader. A normal `deploy.sh` run first builds the repository-owned
PostgreSQL 17.11 derivative with pgvector 0.8.6, then advances the database to that head before
the API starts. It does
**not** import a corpus: source paths and repair-ledger paths are operator inputs, not deployment
configuration, and corpus bytes are not baked into the image.

This boundary is intentional and observable:

- the durable DB model separates opaque snapshot/document/paragraph identities from the
  content-derived equality key;
- canonical paragraphs are immutable evidence, while retrieval chunks are a rebuildable
  versioned projection;
- the DB loader performs no MinIO write, and PDF/crop custody remains a separate reconciliation
  implementation slot;
- migration 0013 installs the exact pgvector extension and durable `vector(1024)` projection;
- no production BGE runtime, embedding worker or search API/UI exists yet.

Consequently `env/alpha.env.example` has no corpus path, pgvector or embedding setting: the image,
migration and frozen profile own those constants. Runtime model credentials and search settings
would still be ignored and would falsely suggest search is live.

### A trailing slash, and the two things that made it leave this origin — `Y-G`

`/api/v1/<anything>/` answers **307**, and the application builds that `Location` as an
**absolute** URL out of the request. Until this wave the proxy gave it the wrong request to
build it from, twice over, so the header named a different port *and* a different tier:

```
# before -- driven on the deployed stack on port 56441
curl -s -i --path-as-is 'http://127.0.0.1:56441/api/v1/dashboard/' | grep -i '^location'
#  location: http://127.0.0.1/dashboard          <- port 80, and the WEB screen
```

* **`proxy_set_header Host $host`** strips the port, so every absolute redirect named port
  **80** of whatever the caller typed. Over the owner's tunnel that is port 80 of *his own
  machine*. It is now `$http_host`, which is the Host header as sent, port and all;
* **`proxy_pass http://api:8000/`** strips `/api/v1` on the way in — correctly, that is how
  the base path is mounted — and nothing put it back on the way out, so an **API** path
  redirected to the **web screen** of the same name. A `proxy_redirect` inside each of the
  two `/api/v1` blocks puts it back. It is inside them and not at `server` level on purpose:
  at `server` level it would rewrite the web tier's own redirects the other way.

It never leaked anything — the screen renders empty and its data calls answer `401` — and a
redirect that leaves the origin's port is not one origin, which is what `T-2` promises.
`tests/integration/composition/test_proxy_tls_path.py::TestTheRedirectStaysOnThisOrigin`
holds all of it, in **both** server bodies.

### A rebuild is not finished when the images are

`up -d --build` replaces the api and web containers, and each replacement gets a new address
on the compose network. **nginx resolves an upstream once, at worker start-up, and holds
it.** So after a rebuild the proxy is still pointing at containers that no longer exist and
**every path through it answers 502** — while both new containers are healthy, and while
`docker compose` says nothing is wrong. That was measured here, and it cost a session an
afternoon of looking at the application for a fault that was in the proxy.

**It is intermittent, which is why it kept coming back.** Driven on this host: a replaced
container usually gets its old address back, and then the proxy carries on answering 200 and
nothing looks wrong. Only when the replacement lands elsewhere does it break — forced by
moving the name to a different address, the proxy kept connecting to the old one and
answered 502 while DNS already said otherwise, and `nginx -s reload` put it back to 200 on
the next request. *The last rebuild was fine* is therefore not evidence about the next one.

The rebuild is therefore three commands, not one:

```
docker compose --env-file infra/deploy/env/alpha.env \
  -f infra/deploy/compose.server.yml up -d --build
infra/deploy/reload-proxy.sh          # the proxy re-resolves its upstreams
infra/deploy/verify-deployed.sh       # and then: is this stack that tree?
```

**A reload does not pick up a changed `proxy/nginx.conf`, and `reload-proxy.sh` no longer
pretends it does** (`W49-FIX`, `B-1`). The proxy bind-mounts that file as a single file, and a
single-file bind mount keeps the inode the file had when the container started. `git
checkout` replaces a changed file with a new inode, so after a deploy the running proxy read
— and `nginx -t` and `nginx -s reload` inside it re-read — the old configuration, measured by
`W49-JUDGE-X` (`docs/program/reviews/W49-JUDGE-X.md` §7.4). So `reload-proxy.sh` first asks
the running proxy what it reads: for every single-file mount it compares the SHA-256 of the
host file with the SHA-256 inside the container. When they differ it tests the checkout's
configuration in a throwaway container (same image, network and mounts, read-only), and
only if that passes it **restarts** the proxy — a restart re-resolves every mount and keeps
the container, its ports and any overlay mounts such as `infra/acme/compose.acme.yml`'s — and asks
again. A broken configuration is refused (exit 5) with the running proxy untouched; a proxy
that still reads other bytes, or was created from another checkout, is refused (exit 6) and
named. When nothing differs it only reloads, so a second `deploy.sh` of the same tree
restarts nothing. A restart drops the proxy's open connections for the moment it takes; it
happens only on a deploy that changed a mounted file.

One port is published, and it is the proxy's. PostgreSQL, MinIO, the API and the web app
are reachable only on the compose network.

## `AUDITMANAGER_API_TOKEN` — read this before the first deployment

The authorization seam of `T-6` is **fail-closed**. An application with no token
configured answers `authentication_required` to every operation but the three a caller
reaches without a credential (`issueToken`, `submitRegistration`, `readRegistrationStatus`)
-- the protected operations -- while
`/healthz` and `/readyz` stay green because `T-3` puts them outside the authorized
surface. From a browser that looks like a broken product rather than an unconfigured one.

Two things now stop that, one in front of the other:

* `docker compose` refuses to render `compose.server.yml` at all if the variable is unset
  (`${AUDITMANAGER_API_TOKEN:?...}`), so the stack cannot be started without it;
* `bootstrap/settings.py` requires it **at construction**, so a container started with it
  empty exits non-zero instead of serving refusals. That is the same Gate C contract
  `ANTHROPIC_API_KEY` is already held to.

Generate one per deployment and never reuse the example:

```
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

> **Its meaning changed in wave 34, and the old sentence was dangerous.** This used to be
> the shared bearer every client presented, and this paragraph used to say so. It is now
> **the key the API signs reviewer credentials with**. An operator following the old
> instruction would hand the signing key to every reviewer, and anyone holding it can mint
> a credential for any subject. Nobody presents it. Nothing outside the API process needs
> it. `JUDGE-SEC` raised this as blocking on wave 34's merge: the code changed and the
> runbook did not, which is the shape where a document becomes an attack.

Reviewers obtain a credential by logging in — `POST /auth/token` — and the web tier holds
what the API mints, in the Node process, never in the browser. A refused request now has a
sign-in screen behind it rather than nothing (`W13_CLOSURE.md` §7 described the state
before wave 34).


### Why the token is not in `.env`

It cannot be. The Makefile parses `.env` against a strict allowlist of exactly the fifteen
names FF-01 §3 freezes and refuses every other name with an explicit error — its own
comment says `.env` "does not carry tool options, credentials for other systems, or
anything that selects what code runs". Adding the token there would break `make gate`
rather than configure anything. `bootstrap/settings.py` records the same reasoning for
`AUDITMANAGER_PROVIDER_MODE`. `env/alpha.env.example` is its channel, and
`tests/integration/composition/test_api_token_channel.py` pins all of it.

## The health plane

Two ports on the API container, from **one built application**:

```
:8000   the 148 operations, mounted by the proxy at /api/v1
:8001   /healthz and /readyz — no credential, no product meaning, no contract
```

The compose health check polls `:8001/healthz`. It is deliberately not proxied: nothing
outside needs it, and publishing it would add a surface nobody authorized.

`/readyz` answers `{"status":"ok","wired":true}`. The `wired` flag is only worth something
because `serve.py` builds the application once and hands the *same object* to both apps —
a health plane in its own process would report on its own wiring and tell the proxy nothing
about the process actually serving `/api/v1`.

## The worker service — `R-105`

Since `W54-WORKER-01` the API does not execute runs. The `worker` service does: the API's
image started as `python -m auditmanager.workers serve`. Each service sets its role
**literally** in `compose.server.yml` — `EXECUTION_ROLE: api` on the API,
`EXECUTION_ROLE: worker` on the worker — and never in `alpha.env`. `deploy.sh`'s
`execution-role-declared` guard refuses a compose file in which either line is missing, is
not a literal, or names the wrong role, and refuses `api` with no worker service, because
then nothing would ever claim a run.

| | `api` | `worker` |
|---|---|---|
| claims queued runs | no | yes, one at a time (`slots` 1) |
| fences expired leases | yes, every 30 s | yes, every 30 s |
| `AUDITMANAGER_API_TOKEN` | required | **absent** — the worker refuses to start if it is set |
| `provider.env` | **not read** (`EXEC-HTTP-01`: the api makes no model call and holds neither the credential nor the private key ring) | read |
| `AUDITMANAGER_SECRETS_PUBLIC_KEYS` / `_ACTIVE_KID` (alpha.env) | seals a connection's key to them | receives them, opens with the private ring |
| ports, session volume | `8000`/`8001` behind the proxy; no session volume | none; none |

What the worker does: it registers a new `wrk_…` identity in the `worker` table on every
start (kept on a tmpfs at `/run/auditmanager`, so a restarted container is a new worker),
heartbeats every 20 s (stale after 90 s, offline after 600 s, derived on read), wakes on
`LISTEN auditmanager_job_wakeup` and polls every 5 s regardless. A lost `LISTEN` connection
is logged as a warning and the poll carries on until it is re-established. The container's
health check is `python -m auditmanager.workers health`, which reads only the identity and
heartbeat files on that tmpfs.

**Stopping it drains it.** `SIGTERM` stops new claims and waits up to 270 s for the run in
flight; `stop_grace_period` is 300 s, so a `deploy.sh` that recreates the worker can wait
that long. A run still in flight when the process ends keeps its lease until it expires
(60 s) and is then fenced by either process: resumed when no provider effect can have spent
(every recorded call, D-150), failed as `provider_outcome_unknown` otherwise.

**«Не брать новые»** (`setWorkerIntake`, administrators) is the same drain for one worker
without stopping it: the claim refuses while intake is off and the run it holds finishes.

**Rollback without the worker** (`W54-PLAN.md` §3.10): a forward fix that sets
`EXECUTION_ROLE: all` on the API and removes the `worker` service is W53's in-process
execution again; `deploy.sh` accepts exactly that shape.

## Deploying it — `PA-01` criterion 1

```
infra/deploy/deploy.sh [--env-file <path>]
```

Exit **0** the stack is up and has answered for itself, **3** it refused and said why,
**2** the arguments were wrong. Fourteen guards, delimited by `# >>> guard:` markers, and
`tests/integration/composition/test_deploy_script_refusals.py` shows every one of them able
to fail by deleting it from a copy — the same form as `reset.sh` and for the same reason.
One of them, `identity-policy-known`, is `W24-IDEM`'s and its case lives beside that file
in `test_deploy_image_identity.py`.

**Count them with the marker anchored to the start of the line** — `grep -cE '^# >>> guard: '`
→ **14**. A bare `grep -c '# >>> guard:'` answers **15**, because `deploy.sh:89` documents
the marker syntax using the marker string itself (`Y5`).

Eight refuse **before docker is touched at all**, so an empty `docker` call log is the
evidence the refusal came first: an unknown option, a missing environment, a
half-configured instance, an `ALPHA_PRESERVE_IMAGE_IDENTITY` that is neither `yes` nor `no`,
**secrets still set to the example file's own published values**, **`derived-secrets-coherent`**
(`W47-GATE`'s `D-103` repair, which is what moved both of these numbers), a missing compose
file, and a clone that does not contain the paths the two Dockerfiles copy. That last one is the clean-clone guard: the paths are read out of the Dockerfiles'
own `COPY` lines, so it cannot drift from what the build needs.

Then `port-not-foreign` — the published port must be free, or held by *this* instance's own
proxy. Then the build, and **only then** the `up`: two steps on purpose, because nothing
that is serving should be replaced until the images that would replace it exist.

Then it asks the running stack four questions it can fail: every service healthy;
**the database at the head this code expects**, asked by running the application's own
`auditmanager.shared.db.check` inside the api image, with the `FOUNDATION-CHECK OK check-db`
sentinel as the evidence rather than an exit code; **the published port answering 401** on
`/api/v1/openapi.json` — `R-31` closed those four documentation routes behind a credential, so
401 is the answer that proves the application's own authorization seam is reached, and a
**200 there is a refusal** (`Y3`); and
**the document the process serves conforming to the frozen `contracts/api/v1/openapi.json`**,
compared by mounting `tests/contract/api_v1/openapi_conformance.py` — the gate's own engine,
not a second one — into a one-off container and piping the served bytes to it.

### Running it twice — measured, and it does change nothing

Driven three times in succession on an unchanged tree (`W24-IDEM.md` §6): **no layer is
rebuilt** (23 `CACHED` steps), **no data is touched**, both named volumes keep their creation
time, both image IDs are identical, and **all seven container IDs are identical** —
`postgres`, `s3`, `s3-init`, `migrate`, `api`, `web`, `proxy`. `compose up -d` reports
`Recreated` for nothing. The one residue: `migrate` and `s3-init` are *started again* in
place, keeping their container IDs; `alembic upgrade head` against a database already at head
applies nothing, and `migrations-at-head` proves it afterwards.

Since W52, `release-notes` is a third one-shot service after `migrate`.
An unchanged entry is checked by its canonical content hash and left as one
stored revision on repeat deployment; a changed entry needs an authored
revision bump. The historical seven-container measurement above predates it.

`W23-DEPLOY` measured `api`, `web` and `migrate` being recreated and `D-36` recorded it. **The
cause that row names is wrong**, and `W24-IDEM` measured it: two consecutive fully cached
builds produce images whose `.Created` is identical *to the nanosecond*, whose
`.RootFS.Layers` are identical and whose entire `.Config` is identical — and whose ids differ
anyway, because the id is the digest of the **manifest** and BuildKit attaches a **provenance
attestation** carrying the build time. `SOURCE_DATE_EPOCH` addresses timestamps inside the
image and was never going to touch that.

Two things close it, answering two different causes:

1. the build runs with `BUILDX_NO_DEFAULT_ATTESTATIONS=1`, which makes the id a digest of the
   content. Measured: two consecutive builds, same id, both images. What is given up is the
   attestation itself, which nothing in this repository reads;
2. after the build, each image is compared with what its name pointed at **before** it — by
   the layer diffIDs and the runtime configuration, never by the id — and the name is pointed
   back at the old image when they are the same. That catches the cause (1) does not: `api`
   and `migrate` share one image and compose's own `com.docker.compose.service` label was
   measured coming out `migrate` on one build and `api` on the next.

The previous image has to be **pinned with a second tag** before the build, because this
host's docker deletes the image a tag moved off at once, even while containers run on it. The
pin comes off after `up`, because while the old container runs docker refuses to untag the
image it runs. Both facts are measured in `W24-IDEM.md` §3.

**Turning it off:** `ALPHA_PRESERVE_IMAGE_IDENTITY=no` in `env/alpha.env`. Every run then
mints a new image and `api`, `web` and `migrate` are recreated, as before. Any value that is
neither `yes` nor `no` is refused before anything is built. It does not turn off the
attestation setting, which is about how the image is built rather than about identity.

**The failure mode, and whether the probe catches it.** An image that kept an old identity
after its content genuinely changed would leave a stale container running.
`verify-deployed.sh` was driven against exactly that stack — a changed `serve.py`, a rebuild,
and the old tag forced back by hand — and it exited **6**, naming `/app/serve.py  DIFFERENT
BYTES` with both digests. `W24-IDEM.md` §4.

### The served document is piped in, never bind-mounted

`$SERVED` comes from `mktemp`. On a host whose docker is the **snap** build, the daemon's
mount namespace has `/tmp/snap-private-tmp/snap.docker/tmp` over `/tmp`, so a `-v` source
under `/tmp` does not resolve — and docker's answer to an unresolvable bind source is to
create an **empty directory** at the destination and start the container anyway. Measured:
the first drive of this guard died on `IsADirectoryError: Is a directory: '/served.json'`
while the identical bind from `/root` delivered the file. This is `reset.sh`'s relative-path
finding in a second costume — **a `-v` source is resolved by the daemon, not by the shell
that typed it** — and both fail by producing something plausible.

## TLS — `R-15`, then `PROD-01-TLS-ACME-01`: the stack obtains its own certificate

**Since `PROD-01-TLS-ACME-01` (`ADR-0021` section 2, `R-146a`) the stack terminates TLS itself and
obtains and renews its own certificate.** `compose.server.yml` is still not changed and `nginx.conf` still
names no certificate. `ALPHA_CERT_NAME` in `alpha.env` is the one switch: empty, nothing below exists and
the stack is what it was; set, `deploy.sh` adds the ACME overlay (`infra/acme/compose.acme.yml`: an ACME
client, the challenge listener on public port 80, the volumes, a network of its own) and, for a deploy that
may publish 443, `proxy/compose.tls.yml` (public port 443). Three listeners, and `lib/proxy-listeners.sh`
decides which exist:

| listener | where | serves | exists when |
|---|---|---|---|
| application, plain | `127.0.0.1:${ALPHA_HTTP_PORT}` | the whole application | always, on loopback; with a name set `deploy.sh` refuses any other `ALPHA_BIND_ADDRESS` |
| challenge | public port 80 (`ALPHA_PUBLIC_ADDRESS`, `ALPHA_ACME_HTTP_PORT`) | the ACME webroot and a redirect to HTTPS; **no application route** | whenever `ALPHA_CERT_NAME` is set, so issuance works while the seeded password is still the seeded one |
| application, TLS | public port 443 (`ALPHA_PUBLIC_ADDRESS`, `ALPHA_HTTPS_PORT`) | the application over TLS with HSTS | only when **all three** hold: `ALPHA_PUBLISH_HTTPS=yes` (the operator's half), a certificate pair exists on the `certs` volume, **and the default-credential gate is clean** (`PROD-02`, `R-146s`) |

**Who decides 443, and when.** The gate is `python -m auditmanager.access.check --gate` run in the `api` image: it
asks whether the published seeded pair (`admin` / `password`) is still valid. It needs the database, so a deploy decides
443 in two steps: the full `up` never *opens* 443 (it keeps an already published one only while the setting still says
`yes` and a pair exists), and the gate step after `migrations-at-head` then opens it, or withdraws it by recreating
**only the proxy** without the 443 overlay. The restore paths (`reset.sh --restore`, `copy-serve.sh restore-db`) end by
asking the same gate and withdraw 443 on a finding, or on an answer they could not get; they never open it.
`verify-deployed.sh` exits 8 on the pair and says loudly if 443 is published meanwhile. The decision functions
(`listeners_https_wanted`, `listeners_apply_https`, `listeners_withhold_https`) are in `lib/proxy-listeners.sh`.

**Networks.** Every service of `compose.server.yml` is on the data network `<instance>-net`. The ACME client is on
`<instance>-acme-net`, shared with the `proxy` and with nothing else (`D-229` item 3): it needs only the proxy (its probe
on 8081, `check-served.sh` on 8443) and the way out to the authority, and it holds no route to postgres, s3 or the api.
The `proxy` is on both networks. `reload-proxy.sh` therefore takes the network of its throwaway `nginx -t` container from
the `api` container and not from "the proxy's first", which would sort to the client's network.

**What `deploy.sh` refuses before it builds, for a stack with a name** (each guard is a marked block with a test that
deletes it): the clone lacks a terminator file (`acme-files-present`); a setting is unusable, or one of the TLS settings
is set with no name (`acme-settings-well-formed`); the client is not pinned (`acme-client-pinned`); a socket of this host
listens on port 80, or on 443 when this deploy would publish it, **on any address** — the kernel's table of listeners is
read, because a host nginx bound to the host's own address is invisible to a connect to `127.0.0.1` and collides with
Docker's `0.0.0.0` publish (`public-ports-free`, `D-229` item 1); a non-empty `ALPHA_TRUSTED_PROXY_CIDRS` is left over
from the host nginx this stack replaces (`trusted-proxies-empty-with-name`, `D-229` item 4); the certificate volume
cannot be asked (`acme-pair-answerable`).

The operator's procedure — the staging rehearsal that comes before the first real issuance, the cutover
from the host's nginx, the expected output of every step — is `docs/program/DEPLOYMENT_RUNBOOK.md` section 6.
The rest of this section is the part that did not change: **why the switch cannot be in the
configuration**, which is nginx's behaviour and not a preference (the original `R-15` text follows, with the
paths updated where the layout moved).


* **`ssl_certificate` is read when the configuration is parsed**, not when a connection
  arrives. Driven, with this very block placed straight into `conf.d/` and no certificate
  present: nginx exits **1** with `[emerg] cannot load certificate ... BIO_new_file()
  failed`. The proxy is the only published port, so that is not a degraded TLS — **the
  whole site is dark because of a file nobody had yet**;
* nginx has **no conditional inclusion**. An `include` whose wildcard matches nothing is a
  legal no-op, but `compose.server.yml` bind-mounts exactly **one** file into `conf.d/`, so
  a wildcard there would have nothing to find and no way to be given anything without
  editing that file — which `W26-OPS` owns this wave;
* the official image runs every executable `/docker-entrypoint.d/*.sh` **before the master
  starts**. That hook is therefore the only place in this stack where *"is there a
  certificate?"* can be asked and acted on **before** the parse that would refuse.

So `tls-server.conf` is mounted at `/etc/nginx/tls-server.conf` — outside the directory
nginx reads — and `enable-tls.sh` copies it into `conf.d/` only when both
`/etc/nginx/tls/fullchain.pem` and `privkey.pem` are present and non-empty. **The disabled
branch un-installs**, because a restarted container keeps its writable layer and a stale
`tls.conf` would make nginx refuse to start over a certificate that was deliberately
removed.

**Both halves were driven**, against real containers, with a **self-signed** certificate
generated by the test — not a real one, which does not exist: no certificate gives plain
port 200, `conf.d` holding `default.conf` alone and 8443 refusing; a certificate gives
`TLS IS ON`, HTTP/2 over TLS 1.3, 200 on both `/` and `/api/v1`, **and the plain port still
200**. `docs/program/reviews/W26-HOST.md` section 2 has the commands and the output.
`tests/integration/composition/test_proxy_tls_path.py` holds the parts of that which can
stop being true without a daemon: no TLS directive in the always-loaded config, the block
staying out of `conf.d`, the switch staying executable in git, the un-install, the two
server bodies not drifting, and `git check-ignore` refusing to let a private key be
committed.

**The key.** It is written by the ACME client into the `certs` named volume — the account key stays in a
volume of its own that the proxy never mounts — and the proxy mounts the pair **read-only**. No file in this
repository or on the host's checkout holds it, and no variable carries it, so **`docker compose config` cannot
print it**: the output names a volume and not a byte of the key. That is the opposite of what the same command
does with `env_file:`; see `env/provider.env.example`. `proxy/tls/` is not mounted by anything now; it stays,
with its ignore rule, as a net.

**Turning it off** is emptying `ALPHA_CERT_NAME` and deploying: the overlays are no longer passed and the proxy
is recreated without them. What is lost is the challenge listener, the TLS listener and the renewal; the volumes
stay (`down` never removes them), so the account and the certificate are still there if the name comes back.
`deploy.sh` does not remove the `acme` container the earlier deploy left (it is no longer in the file list, so
compose treats it as an orphan and leaves it); the runbook, section 6, gives the one command that does.
Between those two states the plain port keeps serving, and there is deliberately **no redirect** from it:
`deploy.sh`'s `proxy-answers` guard requires **401** on `/api/v1/openapi.json` there, and a `301` is not 401, so
it would turn a successful deploy into a refusal. The redirect lives on the challenge listener (port 80), which
is a different listener (`Y3`: the number in that guard was once 200 here and was wrong).

## The client address — `REAL-IP-EDGE-01`, and what a host nginx in front must send

**The problem, measured.** On the deployed stand the traffic is browser → a **host** nginx (TLS,
outside this repository, `proxy_pass http://127.0.0.1:<ALPHA_HTTP_PORT>`) → this stack's proxy
container. The container accepts every connection from one peer: the compose network's **bridge
gateway**. Driven on the development host with the pinned `nginx:1.27-alpine` on a user-defined
bridge, a request to the loopback-published port was logged by nginx as `peer=172.29.0.1` — the
network's gateway — whatever `X-Forwarded-For` it carried (`W49-EDGE-01` measured `172.17.0.1` on
the default bridge the same way). So `limit_req`'s `$binary_remote_addr` — the registration zone
and, since `HARDEN-AUTH-EDGE-01`, the `POST /api/v1/auth/token` zone — was **one bucket for every
visitor**, and so was the web tier's guest bucket, which keys the `X-Real-IP` this proxy sets
from `$remote_addr` (`D-144`, `D-191` `E-3`): one script could spend everyone's sign-ups and token
exchanges.

**The repair is a trust list, and it is empty until the operator fills it.**
`proxy/nginx.conf` declares, once and at http level, `real_ip_header X-Forwarded-For;
real_ip_recursive on;` and **no** `set_real_ip_from`. The trusted peers come from one value in
`alpha.env`:

```
ALPHA_TRUSTED_PROXY_CIDRS=<the gateway of this instance's network>/32
```

`compose.server.yml` hands it to the `proxy` container, `proxy/trusted-proxies.sh` (mounted at
`/docker-entrypoint.d/26-trusted-proxies.sh`, beside `enable-tls.sh`'s hook) validates it and
writes `conf.d/trusted-proxies.conf`, which the image's own `include /etc/nginx/conf.d/*.conf;`
loads beside `default.conf` and `tls.conf`. **Empty or absent — the default — writes nothing and
removes anything an earlier start left: nobody is trusted, `X-Forwarded-For` is never read, and
the proxy behaves exactly as before.** A value the script does not accept (`0.0.0.0/0`, a host
name, anything but IPv4/IPv6 addresses or CIDRs) **stops the container** with the entry named
rather than being read as empty, and `deploy.sh`'s `trusted-proxies-well-formed` guard runs the
same script with `--check` first, so a typo is a refusal before anything is built.

**The rule once a peer is trusted** (driven, `test_real_client_address_at_the_edge.py`): the client
is the **rightmost** address in `X-Forwarded-For` that is not itself trusted; everything to its
left is never read. A request from any peer **not** in the list has its header ignored. Because
nginx then replaces `$remote_addr` for the whole request, the registration and token zones, the
`X-Real-IP` the web tier keys, and the access log all see the client. `tls-server.conf` inherits
the rule (it is http-level) and repeats nothing.

### The value for this stand

* **Which address the host terminator appears from.** A nginx on the host connecting to the
  loopback-published port reaches the container through Docker, and the container sees the
  **gateway of the compose network** `<ALPHA_INSTANCE>-net` (`172.29.0.1` in the measurement
  above — it is allocated from Docker's address pool, **so it differs between hosts and can change
  if the network is deleted and created again**). Read it from the stack that is running:

  ```
  docker network inspect <ALPHA_INSTANCE>-net --format '{{(index .IPAM.Config 0).Gateway}}'
  docker logs <ALPHA_INSTANCE>-proxy-1 --tail 5      # the first field of an access line is the same address
  ```

  The value is that address with `/32`. Check the log line **before** setting the value: once a
  peer is trusted the log shows the client instead.
* **Whom `/32` trusts.** Every process on this host that can open `127.0.0.1:<ALPHA_HTTP_PORT>` —
  the host nginx, and also an SSH-tunnelled operator. They may name a client address for the
  per-address throttles and for nothing else; no authorization decision reads it.
* **If the gateway moves** (network recreated with another subnet) the value no longer matches:
  the proxy falls back to counting the TCP peer, which is the old shared bucket — never to
  believing a client. Re-read the gateway after a `down`/`up` that recreates the network.
* **UNVERIFIED, because the stand is not reachable from the development lane:** the stand's actual
  network name and gateway; the exact lines of its host nginx site file (nginx 1.24.0, Ubuntu —
  the development host has the same package and no site configured); whether its Docker runs with
  the userland proxy off (then the container still sees an address of that bridge, not `127.0.0.1`,
  but this was not measured); and that nothing else (a CDN, a load balancer) sits in front of the
  host nginx. If something does, the host nginx's `$remote_addr` is that device's address, and the
  host needs its own real-IP handling before any of this is true.

### What the host nginx must send

The inner proxy believes only what the trusted peer puts at the **right** of `X-Forwarded-For`,
so the host nginx must **write that header itself**:

```
proxy_set_header X-Forwarded-For $remote_addr;
```

This is the strictest form and the one to use: no byte a client wrote ever reaches this tier.
`proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` is **also safe** with
`real_ip_recursive on`: it appends the real peer on the right, the client's own text stays to its
left and is never read (driven: a forged head in front of a real client buys no bucket).
**Unsafe, and not detected by anything here:** a host nginx with **no** `X-Forwarded-For`
`proxy_set_header` at all (nginx then passes the client's header as sent, so the client chooses the
rightmost address and therefore its bucket — or charges a victim's: "attacker, victim" is the
victim's bucket), or one that forwards `$http_x_forwarded_for`. Keep `Host`, `X-Real-IP` and
`X-Forwarded-Proto` as they are; the inner proxy ignores the first and rewrites the second.

### Checking it took

```
docker logs <ALPHA_INSTANCE>-proxy-1 2>&1 | grep trusted-proxies   # "1 peer(s) trusted ..." or "is empty"
# from the host (its loopback is the trusted peer): twelve exchanges, twelve different clients
for i in $(seq 1 12); do curl -s -o /dev/null -w '%{http_code} ' -X POST \
  -H "X-Forwarded-For: 198.51.100.$i" -H 'Content-Type: application/json' -d '{}' \
  http://127.0.0.1:<ALPHA_HTTP_PORT>/api/v1/auth/token; done; echo
```

With the list set, no `429` appears; with it empty the twelfth is `429` — one bucket. The check
spends those documentation addresses' budgets and nobody else's. `compose.server.yml` carries the
value as an `environment:` entry, so changing it recreates the `proxy` container on the next
`up`; `reload-proxy.sh` alone does not re-run the hook.

## The session register — `R-51`, and what it costs

**A named volume, `<instance>-web-sessions`, mounted by the `web` container and by nothing
else.** The web tier holds each signed-in reviewer's API credential in its own process and
hands the browser only an opaque session number (`W15-AUTH`; the credential is never in the
browser bundle and never in a cookie). Until wave 47 that register was memory and nothing
else — and `deploy.sh` recreates the `web` container on every run, so **every deploy signed
every reviewer out.** Not a rare crash: a support incident per deployment.

| | |
|---|---|
| volume | `${ALPHA_INSTANCE}-web-sessions`, declared in `compose.server.yml` |
| mounted at | `/var/lib/auditmanager/sessions`, by `web` only |
| the file | `register.json`, mode `0600`, in a directory the image creates owned by `node` |
| configured by | `AUDITMANAGER_SESSION_STORE`, set in `compose.server.yml` — not in `alpha.env`, because it is a path inside the image and not a deployment choice |

**What is on that volume, stated here because it is the cost the owner accepted and not a
detail:** until each credential expires — one hour, `TOKEN_LIFETIME_SECONDS` — the API
credentials the web tier holds are in that file, on this host's disk. Two things are
unchanged by it and both matter:

* **they still never reach the browser.** What the browser holds is still a 32-byte opaque
  number in an `HttpOnly` cookie, which is a key to a map only this process can read;
* **a revoked credential still stops working at once.** The API compares `token_epoch` on
  every request, wherever the token was kept, so `python -m auditmanager.access.revoke` and
  a password change both take effect on the next request rather than when a file is
  rewritten.

Two operational consequences to know before you meet them:

* `docker compose down` does **not** remove it, exactly as it does not remove the database
  or the object store; `down --volumes` does, and doing that signs everybody out. That is
  the one command that undoes what this volume is for.
* **`reset.sh --yes-destroy-everything` clears it**, in the same movement as the database
  and the bucket, and it does so *before* it drops anything, so a deployment that cannot
  clear it refuses with the documents still whole. Until wave 47 it could not reach the
  volume and did not try: `W47-JUDGE-Y` drove the wipe to the end and found `register.json`
  **byte-identical**, `md5sum` unchanged, with three complete reviewer credentials in it
  (`Y8`). The `web` container is stopped for the moment of the clearing and started again
  afterwards, because the register is a file *and* a map in that process, and a live
  container writes the map back out after every change.
* a `web` container that cannot write the file **still serves**: the sessions are live in
  its memory either way, and refusing to sign anybody in because of a full disk would take
  the stand down for a reason no reviewer can act on. It says so in its own log, on every
  attempt, starting `[session-register] could not write` — if you see that line, the next
  deploy will sign everyone out and the volume is the thing to look at.

A stand that sets no `AUDITMANAGER_SESSION_STORE` at all keeps the pre-wave-47 behaviour
and says so once, at the first sign-in: `[session-register] AUDITMANAGER_SESSION_STORE is
not set`. That is `next dev`, never this compose file.

## The wipe — `R-4`

The owner ruled that **real client documents may be uploaded and must be wiped at the end
of the pilot.** `reset.sh` is that wipe, and it dumps and *verifies the dump* before it
drops anything.

```
# rehearse — touches nothing
infra/deploy/reset.sh --database <db> --bucket <bucket> --dry-run

# do it
infra/deploy/reset.sh --database <db> --bucket <bucket> --yes-destroy-everything

# put one of its dumps back, both halves
infra/deploy/reset.sh --database <db> --bucket <bucket> --restore infra/deploy/dumps/<stamp>
```

It refuses unless an explicit flag is given **and** the database and bucket you typed are
the ones the environment configures, so a stale environment cannot point it at another
instance. Every destructive step runs through `compose.server.yml`, so it cannot reach a
database that file does not define.

**A dump is three things** and a restore needs all three: `database.dump`, the object
mirror under `objects/`, and `objects.attrs`. `mc mirror` drops S3 user metadata — measured,
not assumed: an object mirrored out and back arrives with no `content-sha256` and the
storage adapter refuses it with `validation_failed`, leaving an instance that lists a
document and 422s on its bytes. `object_attrs.py` records what `mirror` loses and
`--restore` puts it back.

**The bytes go back before the rows**, and the order is deliberate: either half can fail, and
rows without bytes is an instance that lists a document and cannot serve it — it *looks
recovered* — while bytes without rows looks exactly as empty as it is. `W22-OPS` found that
by running the relative-path invocation this script prints, which until then restored the
database and then died on the object half, leaving the misleading one.

The thirteen refusals are delimited by `# >>> guard:` markers, and
`tests/integration/composition/test_reset_script_refusals.py` shows every one of them able
to fail by deleting it from a copy.

**A wipe takes three things and not two** — the database, the bucket and the **session
register** (`Y8`, above). The register goes first, before anything is dropped.

**A restore takes the credentials back that it puts back** — `R-52`, ruled 2026-09-29. The
dump is the whole database with no `--exclude-table` and the restore is `pg_restore --clean
--if-exists`, so `app_user` comes back entire: `password_hash`, `token_epoch` **and**
`is_default_credential`. So restoring any dump taken before a forced password change would
otherwise put the deployment back on the shipped `admin`/`password`, silently, by a
documented command — and unlike a revoked token, a password is bounded by nothing.
`--restore` therefore, after the rows are back:

* runs `auditmanager.access.revoke --everyone`, so **every restored credential is dead**;
* runs `auditmanager.access.check`, which **names by login** any account that came back on
  its default password, and prints what to do about it.

Both run inside the `api` image (`docker compose run --rm --no-deps -T --entrypoint python
api -m …`), which is the only idiom that works on the host §1 of the runbook describes.
**It reports; it does not refuse** — the owner's own line from `R-46`, taken with `D-72` in
hand: a restore that refuses blocks the legitimate one at the moment it is needed most,
which is after a failure. Neither command's status can turn a completed restore into a
non-zero exit; what a failure of either buys is a named block on the screen and the exact
command to type.

**The wipe that keeps the accounts and the corpus — `STAND-PURGE-TOOL-01`.** `reset.sh` drops the schema, so it also drops the
imported normative corpus and the accounts. To remove only the generated test data, `purge-product-data.sh --database <db> --bucket
<bucket> --dry-run` prints, with exact counts, which tables are truncated (the 29 product tables), which are never written (accounts,
registration requests, release notes, lookup data, every `norm*` table), which rows of `audit_event`, `command_record` and `blob` go, and
which objects would be deleted by exact key; `--yes-purge-product-data` then stops the worker, writes and verifies a dump in
`reset.sh`'s layout (so `reset.sh --restore` applies), purges in one transaction that rolls back if any kept row's count or digest
differs, deletes the product objects only after the commit, and starts the worker again. It refuses, naming it, a table nobody classified
(`product_purge.py` classifies from `schema_coverage.py`), and a run or job that is executing (`--allow-running`); exit `3` is a refusal
and `4` a failure, and after a commit `--finish-objects <dump directory>` completes a half-done object deletion. Read the document before the first run.

## Is the deployed stack this repository? — `D-27`

```
infra/deploy/verify-deployed.sh
```

Exit **0** the stack is this working tree, **6** it is not, **4** the question could not be
answered. All three are printed; only one of them is a success. The row this closes is not
that a stack drifted — it is that for three waves running nobody noticed, because there was
nothing that could be red. So there is no path through the script that reports a healthy
stack without having compared bytes, including the paths where it is confused: a Dockerfile
it cannot parse, a container that is not there, a proxy that does not answer.

**It compares what is inside the running containers to what is in the tree**, file by file,
for exactly the paths the two Dockerfiles copy — read out of the Dockerfiles' own `COPY`
lines, so a newly copied path is covered without anyone remembering. It also asks the proxy
first, which is how the 502 above is told apart from a stale image.

**It also asks the running proxy what configuration it reads** (`B-1`). The mounts are read
from the container, so an overlay is seen too; each source must be this checkout's
`infra/deploy/proxy/`, and every tracked file under it is compared by SHA-256 inside the
container. A difference exits **6** with *the running proxy is NOT serving this tree's
configuration* and the file named, as does a proxy that does not mount
`proxy/nginx.conf` at all or mounts it from another checkout. It sends no request burst:
whether the throttle answers 429 is a property of the configuration this compares, and a
burst against the live stand on every deploy would be a side effect. The burst is driven
on a disposable stand instead, by the opt-in class in
`tests/integration/composition/test_proxy_config_follows_checkout.py`.

**It deliberately does not compare the served `/openapi.json`,** and that was measured
rather than assumed:

* the served document is generated by `api/app.py` and the frozen one is written by hand.
  They differ — in `paths`, `components`, `info` and `security` — even after annotations are
  dropped. That is why `tests/contract/api_v1/openapi_conformance.py` is a conformance
  engine and not a digest comparison. There is no digest to compare;
* and even a correct comparison of the two documents is **blind to the drift this row was
  created by**. `W20-EXEC`'s `src/auditmanager/runs/carrier.py` was missing from the
  deployed image; the document this tree generates is byte-identical with a line appended
  to that file. A probe watching the API surface would have been green on the exact defect
  that made the row.

`tests/integration/composition/test_deployed_stack_probe.py` drives every one of its
answers against stubs, including the ones where it is confused.

## What is NOT here, and why

* **A host name, a certificate and a DNS record.** Still nobody's to invent. `W14-PKG`
  refused to write a `listen 443 ssl` block naming a certificate that has never existed, on
  the grounds that that is a document and not a deliverable, and **that judgment stands**.
  What `W26-HOST` added under `R-15` is not that block in `nginx.conf`: it is a block
  **nginx does not load** until a certificate pair is on the host — see *TLS* above. The
  deployment as certified is unchanged, and is what you get without the overlay.
* **Fetch, switch and rollback.** `deploy.sh` exists now (below), but it does not fetch a
  revision, switch between versions or roll one back. All three are claims about a server
  that has a previous version on it, and `R-1`'s host does not exist. What it does instead
  is put the build *before* the switch, so a failed build leaves whatever was serving still
  serving — which is the part of that behaviour a machine with no previous version can show.
* **A leaner web image.** `output: "standalone"` would roughly halve it. That switch lives
  in `web/next.config.mjs`, which `W14-PKG` does not own.
