# Local stack

Disposable local PostgreSQL and private S3-compatible (MinIO) services for the P01
foundation. Owned by `P1-INF-01`. Local credentials are disposable and are never reused
as production credentials.

Files here:

| file | what it is |
| --- | --- |
| `docker-compose.yml` | the three services, at pinned image digests |
| `bucket-init.sh` | idempotent private-bucket initialization, run inside the `mc` container |
| `check_services.py` | what `make check-services` forwards to |

## Prerequisites

- Docker with the Compose v2 plugin (`docker compose version`).
- The runtime environment: `make bootstrap`. If your shell already has a virtualenv
  active, `make bootstrap` refuses the ambient interpreter; pass the base one, e.g.
  `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`.
- A `.env`. Copy it and give this lane its own values:

  ```
  cp .env.example .env
  ```

  `.env` is git-ignored and must never be committed. Six values are **per lane** and must
  be unique across every lane running at once (FF-01 §5): `FOUNDATION_INSTANCE`,
  `POSTGRES_PORT`, `S3_API_PORT`, `S3_CONSOLE_PORT`, `POSTGRES_DB`, `S3_BUCKET`.
  Two lanes sharing one instance is forbidden.

## Start and stop

```
make up             # start; returns only when everything is healthy
make check-services # prove health, bucket presence, privacy and authenticated access
make down           # stop, keeping all data
```

`make up` passes `--detach --wait`, so it returns only once PostgreSQL, MinIO **and**
bucket initialization have all reported healthy. There is no manual follow-up step.

`make down` stops and removes the containers and the network. It never removes the
volumes, so database contents and stored objects survive `down` and are still there after
the next `up`.

Do not invoke `docker compose` directly for `up`/`down`. The Makefile is the only thing
that exports the pinned image digests, and the compose file refuses to interpolate
without them:

```
error while interpolating services.s3-init.image: required variable
FOUNDATION_S3_MC_IMAGE is missing a value
```

That refusal is deliberate — see "Images are pinned" below.

## What the three services are

| compose service | image | published on |
| --- | --- | --- |
| `postgres` | `FOUNDATION_POSTGRES_IMAGE` | `127.0.0.1:$POSTGRES_PORT` -> 5432 |
| `s3` | `FOUNDATION_S3_IMAGE` (MinIO) | `127.0.0.1:$S3_API_PORT` -> 9000, `127.0.0.1:$S3_CONSOLE_PORT` -> 9001 |
| `s3-init` | `FOUNDATION_S3_MC_IMAGE` (`mc`) | nothing published |

Ports bind to `127.0.0.1` only. These services hold disposable credentials and must not
be reachable from the network.

### Health checks — "up" means ready, not started

- **`postgres`** probes `127.0.0.1:5432` over TCP with `pg_isready` and then runs an
  authenticated `SELECT 1` as the configured role against the configured database.
  A unix-socket `pg_isready` is not enough: during `initdb` the image runs a temporary
  server on the socket only, so a socket probe reports ready while the database and role
  are still being created.
- **`s3`** uses `mc ready local`, MinIO's own readiness probe.
- **`s3-init`** becomes healthy only after `bucket-init.sh` has succeeded, so `--wait`
  gates on the bucket existing and being private, not just on containers starting.

### Lane isolation

Everything durable is named from `FOUNDATION_INSTANCE`:

| object | name |
| --- | --- |
| compose project | `$FOUNDATION_INSTANCE` |
| network | `$FOUNDATION_INSTANCE-net` |
| PostgreSQL volume | `$FOUNDATION_INSTANCE-postgres-data` |
| MinIO volume | `$FOUNDATION_INSTANCE-s3-data` |

Two lanes with different `FOUNDATION_INSTANCE` values share no container, no network and
no volume. Check what your instance owns with:

```
docker volume ls  --filter name=$FOUNDATION_INSTANCE
docker network ls --filter name=$FOUNDATION_INSTANCE
```

### Images are pinned

FF-01 forbids a floating tag anywhere in the foundation. The three digests live in the
`Makefile`'s `override FOUNDATION_*_IMAGE :=` lines and in
`docs/program/FOUNDATION_LOCK.json`; `make` reads them out of its own bytes and exports
them. This compose file consumes them with `${...:?}`, so an unset pin is a loud failure
and never silently falls back to a tag. A lane configures instance, ports, database and
bucket — never which image runs. **Changing an image is a pin request back to
`P1-INT-00`, not a local edit.**

## The bucket is private

`bucket-init.sh` creates `$S3_BUCKET` if it is absent and sets its anonymous policy to
`none` unconditionally. It is idempotent: a second, third and hundredth run creates
nothing, changes nothing and exits 0.

```
bucket-init: created private bucket audit-a2 at http://s3:9000     <- first run
bucket-init: bucket audit-a2 already present at ... - no-op        <- every later run
```

It runs when the `s3-init` container **starts** — the first `make up`, and every `make up`
that follows a `make down`. Compose does not restart a container that is already running,
so `make up` against an already-running stack does not re-run it. The initializer
*establishes* privacy; `check_services.py` is what *detects* a bucket that was opened
afterwards, and it fails loudly when it finds one.

To re-run initialization by hand without a restart:

```
docker compose --project-name "$FOUNDATION_INSTANCE" \
  --file infra/local/docker-compose.yml \
  exec s3-init /bin/sh /usr/local/lib/foundation/bucket-init.sh
```

## `make check-services`

Runs `infra/local/check_services.py`. It proves:

1. PostgreSQL accepts an authenticated TCP connection as the configured role against the
   configured database, and serves a read and a write (via a temporary table, so it
   creates nothing persistent);
2. MinIO answers `/minio/health/live`;
3. the frozen `S3_BUCKET` exists;
4. an object round-trips byte-for-byte with the service credentials;
5. re-running initialization is a benign no-op that destroys nothing;
6. anonymous **list**, **read** and **write** are each denied — attempted for real with an
   unsigned client and again over plain HTTP, with the read aimed at a key that provably
   exists and the refused write confirmed to have created nothing.

It deliberately makes **no claim about the application migration head** (that is
`make check-db`) and **none about the BlobStore adapter** (that is `make check-storage`).
It never imports `auditmanager` and never reads `alembic_version`.

On success the last line is exactly `FOUNDATION-CHECK OK check-services`. Every failure
is explicit and non-zero; there is no partial pass.

## Troubleshooting

**`make up` fails with `required variable FOUNDATION_S3_MC_IMAGE is missing a value`.**
You ran `docker compose` directly. Use `make up` / `make down`.

**`.env is missing and no default is assumed`.** `cp .env.example .env`, then set this
lane's six unique values.

**`bind: address already in use`.** Another lane, or a stray stack, holds your port.
`docker ps --format '{{.Names}} {{.Ports}}'` shows who. Change your `POSTGRES_PORT` /
`S3_API_PORT` / `S3_CONSOLE_PORT` (and `S3_ENDPOINT_URL`, which must carry `S3_API_PORT`)
rather than stopping someone else's instance.

**`connected to the wrong database`.** Your port is bound to another lane's PostgreSQL.
Same fix as above.

**`make up` hangs on `Waiting` and then fails with an unhealthy service.** Read the logs:

```
docker compose --project-name "$FOUNDATION_INSTANCE" \
  --file infra/local/docker-compose.yml logs postgres s3 s3-init
```

- `postgres` never healthy right after a `POSTGRES_USER`/`POSTGRES_PASSWORD` change: the
  volume was initialized with the old credentials, and `initdb` does not re-run on a
  populated volume. Either restore the old values or destroy this lane's data — see the
  destructive command below.
- `s3-init` unhealthy: it could not authenticate to MinIO. Check `MINIO_ROOT_USER` and
  `MINIO_ROOT_PASSWORD`; MinIO refuses a root password shorter than 8 characters.

**`THE BUCKET IS PUBLIC` from `check-services`.** Somebody granted an anonymous policy.
Close it and re-check:

```
docker compose --project-name "$FOUNDATION_INSTANCE" \
  --file infra/local/docker-compose.yml \
  exec s3-init /bin/sh /usr/local/lib/foundation/bucket-init.sh
```

**Starting over.** `make down` is non-destructive and is the rollback. Deleting data is
never a default; it is this explicit, deliberate command, and it destroys **this lane's**
database and objects:

```
docker compose --project-name "$FOUNDATION_INSTANCE" \
  --file infra/local/docker-compose.yml down --volumes
```

## Known limitations

- The application authenticates to MinIO with the same disposable root credentials as the
  container. That is a local convenience, not an IAM design; scoped service credentials
  are out of scope for FF-01 §4.
- Single-node MinIO with no erasure coding, versioning, lifecycle or backup, and no
  PostgreSQL tuning. These are development services.
- Linux/amd64 with the Docker Compose v2 plugin is what this was exercised on. The pins
  are multi-arch index digests, so other architectures resolve, but were not run here.
