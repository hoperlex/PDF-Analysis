# The alpha deployment — the runbook

Everything here was built and **driven** by `W14-PKG` on the development host. Nothing in
it has run on a server, and it deliberately stops short of doing so: `R-1` is ruled (the
owner's own VPS) but the host name, who holds root, which ports may be opened and when
access appears do not exist yet. Where that boundary bit, it is named below rather than
guessed past.

`T-4`: **none of this is a `make` target.** `OD-16` makes a tenth root target an FF-01
freeze-break needing an explicit break record, and nothing here needs one. The Makefile
stays the developer's gate; these are scripts and one compose file, invoked directly.

`infra/local/docker-compose.yml` is a different thing and neither replaces the other. That
is the developer's disposable service pair, driven only by the frozen `make up`/`make
down`. This is the deployed stack.

## What is here

| Path | What it is |
|---|---|
| `Dockerfile.api` | the twelve operations under uvicorn, plus `T-3`'s health plane |
| `Dockerfile.web` | `npm run build`, then `next start` |
| `serve.py` | the entry point: **one built application, two ports** |
| `compose.server.yml` | the stack: PostgreSQL, MinIO, migrate, api, web, one proxy |
| `proxy/nginx.conf` | `T-2` — the web app at `/`, the API at `/api/v1`, one origin |
| `reset.sh` | `T-5` — the guarded wipe, and the restore of its own dump |
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

docker compose --env-file infra/deploy/env/alpha.env \
  -f infra/deploy/compose.server.yml up -d --build
```

`migrate` runs once and exits; `api` waits for it. Migrations are never run by a serving
process — two replicas starting together would race the same upgrade.

One port is published, and it is the proxy's. PostgreSQL, MinIO, the API and the web app
are reachable only on the compose network.

## `AUDITMANAGER_API_TOKEN` — read this before the first deployment

The authorization seam of `T-6` is **fail-closed**. An application with no token
configured answers `authentication_required` to every one of the twelve operations, while
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
:8000   the twelve operations, mounted by the proxy at /api/v1
:8001   /healthz and /readyz — no credential, no product meaning, no contract
```

The compose health check polls `:8001/healthz`. It is deliberately not proxied: nothing
outside needs it, and publishing it would add a surface nobody authorized.

`/readyz` answers `{"status":"ok","wired":true}`. The `wired` flag is only worth something
because `serve.py` builds the application once and hands the *same object* to both apps —
a health plane in its own process would report on its own wiring and tell the proxy nothing
about the process actually serving `/api/v1`.

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

The eleven refusals are delimited by `# >>> guard:` markers, and
`tests/integration/composition/test_reset_script_refusals.py` shows every one of them able
to fail by deleting it from a copy.

## What is NOT here, and why

* **TLS.** `R-1` is ruled, so TLS and DNS are in scope for the deploy wave — but a
  `listen 443 ssl` block naming a certificate for a host that does not exist is a document,
  not a deliverable. The proxy terminates HTTP on one port; the TLS layer is added when the
  host is.
* **`deploy.sh`.** The roadmap's `W14-OPS` row owns the idempotent fetch/build/migrate/
  health-check/switch with rollback. It cannot be exercised here — "run it twice and the
  second changes nothing" and "a broken build rolls back and leaves the previous version
  serving" are both claims about a server.
* **A leaner web image.** `output: "standalone"` would roughly halve it. That switch lives
  in `web/next.config.mjs`, which `W14-PKG` does not own.
