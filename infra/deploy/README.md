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
| `Dockerfile.api` | the fifteen operations under uvicorn, plus `T-3`'s health plane |
| `Dockerfile.web` | `npm run build`, then `next start` |
| `serve.py` | the entry point: **one built application, two ports** |
| `compose.server.yml` | the stack: PostgreSQL, MinIO, migrate, api, web, one proxy |
| `proxy/nginx.conf` | `T-2` — the web app at `/`, the API at `/api/v1`, one origin |
| `proxy/tls-server.conf` | the TLS server block. **nginx never loads it unless a certificate is there** |
| `proxy/enable-tls.sh` | the switch: the image runs it before nginx starts, and it asks one question |
| `proxy/compose.tls.yml` | the overlay that mounts those two and publishes the TLS port |
| `proxy/tls/` | where the certificate and its private key go **on the host**. Contents ignored whole |
| `deploy.sh` | `PA-01` criterion 1 — bring this clone up, and refuse to call it deployed until the stack has answered |
| `reset.sh` | `T-5` — the guarded wipe, and the restore of its own dump |
| `verify-deployed.sh` | `D-27` — is the stack in front of you this tree? |
| `reload-proxy.sh` | `D-27` — the step after a rebuild that everyone forgets |
| `object_attrs.py` | the third part of a dump: each object's S3 attributes |
| `env/alpha.env.example` | the deployment's environment. **Not `.env`** — see below |
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

`migrate` runs once and exits; `api` waits for it. Migrations are never run by a serving
process — two replicas starting together would race the same upgrade.

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

One port is published, and it is the proxy's. PostgreSQL, MinIO, the API and the web app
are reachable only on the compose network.

## `AUDITMANAGER_API_TOKEN` — read this before the first deployment

The authorization seam of `T-6` is **fail-closed**. An application with no token
configured answers `authentication_required` to every one of the fifteen operations, while
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

Clients present it as `Authorization: Bearer <token>`. **The frontend has no branch for
401** (`W13_CLOSURE.md` §7) — see `docs/program/reviews/W14-PKG.md` §7.

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
:8000   the fifteen operations, mounted by the proxy at /api/v1
:8001   /healthz and /readyz — no credential, no product meaning, no contract
```

The compose health check polls `:8001/healthz`. It is deliberately not proxied: nothing
outside needs it, and publishing it would add a surface nobody authorized.

`/readyz` answers `{"status":"ok","wired":true}`. The `wired` flag is only worth something
because `serve.py` builds the application once and hands the *same object* to both apps —
a health plane in its own process would report on its own wiring and tell the proxy nothing
about the process actually serving `/api/v1`.

## Deploying it — `PA-01` criterion 1

```
infra/deploy/deploy.sh [--env-file <path>]
```

Exit **0** the stack is up and has answered for itself, **3** it refused and said why,
**2** the arguments were wrong. Thirteen guards, delimited by `# >>> guard:` markers, and
`tests/integration/composition/test_deploy_script_refusals.py` shows every one of them able
to fail by deleting it from a copy — the same form as `reset.sh` and for the same reason.
The thirteenth, `identity-policy-known`, is `W24-IDEM`'s and its case lives beside that file
in `test_deploy_image_identity.py`.

Seven refuse **before docker is touched at all**, so an empty `docker` call log is the
evidence the refusal came first: an unknown option, a missing environment, a
half-configured instance, an `ALPHA_PRESERVE_IMAGE_IDENTITY` that is neither `yes` nor `no`,
**secrets still set to the example file's own published values**, a missing compose file,
and a clone that does not contain the paths the two Dockerfiles copy. That last one is the clean-clone guard: the paths are read out of the Dockerfiles'
own `COPY` lines, so it cannot drift from what the build needs.

Then `port-not-foreign` — the published port must be free, or held by *this* instance's own
proxy. Then the build, and **only then** the `up`: two steps on purpose, because nothing
that is serving should be replaced until the images that would replace it exist.

Then it asks the running stack four questions it can fail: every service healthy;
**the database at the head this code expects**, asked by running the application's own
`auditmanager.shared.db.check` inside the api image, with the `FOUNDATION-CHECK OK check-db`
sentinel as the evidence rather than an exit code; the published port answering 200; and
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

## TLS — `R-15`, and it is off until a certificate exists

**`compose.server.yml` is not changed and `nginx.conf` names no certificate.** TLS is one
overlay and one file that nginx loads conditionally:

```
docker compose --env-file infra/deploy/env/alpha.env \
  -f infra/deploy/compose.server.yml \
  -f infra/deploy/proxy/compose.tls.yml up -d
infra/deploy/reload-proxy.sh
```

The operator's steps are in `docs/program/DEPLOYMENT_RUNBOOK.md` section 6. What belongs
here is **why the switch cannot be in the configuration**, which is nginx's behaviour and
not a preference:

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

**The key.** It is placed by the owner, by hand, in `infra/deploy/proxy/tls/`, mode 600,
read-only in the container, and never committed. It is also the one secret around this
stack that **`docker compose config` cannot print** — the overlay reaches it through a bind
mount, so the output carries the path and not a byte of the file, measured with a sentinel.
That is the opposite of what the same command does with `env_file:`; see
`env/provider.env.example`.

**Turning it off** is dropping the second `-f`, and what is lost is the TLS listener and
nothing else. There is deliberately **no redirect** from the plain port: `deploy.sh`'s
`proxy-answers` guard requires 200 there and a `301` would turn a successful deploy into a
refusal.

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

The twelve refusals are delimited by `# >>> guard:` markers, and
`tests/integration/composition/test_reset_script_refusals.py` shows every one of them able
to fail by deleting it from a copy.

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
