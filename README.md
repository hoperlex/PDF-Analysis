# AuditManager Greenfield — bootstrap package

This repository is a **starter kit for developing a new application from scratch**. It is not a copy of the legacy code and assumes no runtime dependency on the old application.

The legacy `PDF-proverka-main` is used only as:

1. a behavioral oracle — the source of actual user-facing behaviour;
2. a source of characterization/golden fixtures;
3. a catalog of edge cases and business invariants;
4. the reference for semantic parity where the business meaning must be preserved.

The architecture of the new application is defined by `docs/architecture/ARCHITECTURE_BIBLE.md`, the accepted ADRs and the frozen contracts in `contracts/`.

## Where to start

The new repository must be created **from the contents of this package**; work then proceeds in the following order:

```text
README
  → docs/PRODUCT_SYNOPSIS.md
  → docs/architecture/ARCHITECTURE_BIBLE.md
  → docs/architecture/ADR_INDEX.md
  → docs/program/ROADMAP.md
  → docs/program/WAVE_EXECUTION_GUIDE.md
  → docs/stages/S00_...
```

`FF-01 ACCEPTED` was recorded on 2026-09-09. On the current planning line only the
foundation provider code from P01 (`infra/local/**`, `db/migrations/**`,
`src/auditmanager/shared/db/**`, `src/auditmanager/storage/**`) is permitted, within the
task-specific `allowed_paths`. Production domain code remains forbidden until a separate
acceptance of the detailed P02–P05 plan and the fulfilment of its dependencies.

## Foundation commands (P01)

The root task runner is `make`. These nine commands are frozen by FF-01 and are the
only command surface of the foundation; their owner is `P1-INT-00`.
Provider lanes fill only their own reserved paths and call these targets
without editing the `Makefile` and without creating private aliases.

| Command | What it does | Implemented by |
|---|---|---|
| `make bootstrap` | reproduces both locked environments: `.venv/bootstrap` (validators) and `.venv` (runtime/tests) | `P1-INT-00` |
| `make up` | starts PostgreSQL and the S3-compatible service | `P1-INF-01` |
| `make down` | stops them without deleting data | `P1-INF-01` |
| `make check-services` | service health and idempotent initialisation of the private bucket | `P1-INF-01` |
| `make migrate` | applies the migration head | `P1-DB-01` |
| `make check-db` | DB connectivity and the current migration state | `P1-DB-01` |
| `make check-storage` | BlobStore access to the private bucket | `P1-STO-01` |
| `make test-foundation` | only the accepted foundation test suite | `P1-QA-00` |
| `make foundation` | the whole sequence, one after another | composition |

A target whose implementation has not arrived yet is a stable forwarder: it **fails explicitly**,
naming the reserved path and the owning task. No target has an implementation substitute,
a silent skip or a fallback.

An exit code alone is not proof. `check-services`, `check-db` and
`check-storage` must print `FOUNDATION-CHECK OK <target>` as **the last actual
line of output** — after their checks have passed. `make` rejects: a zero exit
code without this line, any visible output after it, and a zero-size reserved
file. ANSI colour, CR and surrounding whitespace are normalised; blank lines
after the sentinel are allowed. The checker runs with `PYTHONUNBUFFERED=1`; otherwise the order
in the captured output would reflect stdout buffering rather than the order of writes. The limit
of the guarantee: what is checked is that the checker **printed** nothing more after its
success claim; work that produces no output (a background process, output sent to `/dev/null`)
cannot be checked through output.

Images cannot be overridden from the call site. The actual reference is read at
run time from the `override FOUNDATION_*_IMAGE :=` lines of the `Makefile` itself, so it is
changed neither by `make up FOUNDATION_POSTGRES_IMAGE=...`, nor by `make -e`, nor by a
target-scoped assignment via `--eval` (including one passed through `MAKEFLAGS`/`GNUMAKEFLAGS`),
nor by a second `-f` makefile: a make variable can be overridden, the bytes of the file
cannot. A value without `@sha256:` is rejected. A different image is a request to
`P1-INT-00` for a new pin, not a lane's decision.

`.env` is data, not code. The file is parsed line by line as `NAME=VALUE` and is never
executed: sourcing it would let `.env` replace the `compose()` function, replace
`PATH`, or run `exit 0` and report success without having executed anything.

Names are a strict allowlist of exactly the 15 names frozen by FF-01, not a denylist.
Any other name is rejected: `PYTEST_ADDOPTS`, `PYTHONPATH`, `DOCKER_HOST`, `AWS_*`,
`PATH`, `MAKEFLAGS`, an image name — all alike. A denylist would close only the
names someone remembered. Each of the 15 names must occur exactly once:
an omission and a repetition are explicit errors; a repetition is never silently resolved in
favour of one of the two values.

There is no variable substitution inside values. Quotes are allowed only as a single matched
pair wrapping the whole value, with no quote of the same kind inside it; there is no escaping.
An unclosed quote (`X="abc`), a quote that does not wrap the value (`X=abc"`) and a quote
inside a quoted value (`X="a"b"`) are rejected, not kept as an
ambiguous literal.

The providers' reserved paths (`infra/local/docker-compose.yml`,
`infra/local/check_services.py`, `db/migrations/alembic.ini`,
`src/auditmanager/shared/db/check.py`, `src/auditmanager/storage/check.py`,
`tests/integration/foundation`) and the interpreters are read at run time from the bytes
of the makefile that make actually parsed (`$(abspath $(lastword
$(MAKEFILE_LIST)))`), as are the image pins. The anchor is exactly this because `awk` over a
bare `Makefile` reads `./Makefile`: running `make -f /real/Makefile` from a directory
holding a forged copy would take the forged one. Therefore neither `make up INF_COMPOSE=...`,
nor `make -e`, nor a target-scoped `--eval` (including via `MAKEFLAGS`/`GNUMAKEFLAGS`), nor
a second `-f` makefile replaces the path the forwarder accesses. The same closes
`make test-foundation RUNTIME_PY=/bin/true`, which would otherwise exit with
code 0 without running a single test.

`make test-foundation` runs hermetically: all `PYTEST_*` variables, the `PYTHON*` variables
that change interpretation and the loader variables (`LD_AUDIT`, `LD_PRELOAD`, `OPENSSL_CONF`,
`GLIBC_TUNABLES`) are scrubbed, `PYTHONNOUSERSITE=1` is set, the pytest config
is pinned with `-c pyproject.toml --rootdir=.`, and pytest exit code `5` (“no
tests were collected”) is treated as an error. The scrubbing is done with `unset` in a subshell,
not through `env`: an exported bash function `env` would shadow the binary. In addition,
`make` no longer passes `BASH_ENV`, `ENV`, `SHELLOPTS` and `BASHOPTS` into the recipe shell, and
`make -t` is rejected at parse time.

What this does **not** close, stated plainly: `MAKEFLAGS=-n` is a dry run and the recipe is not
executed at all, so no guard inside the recipe can fire (`make -n`
remains a mandatory check, and a dry run prints neither `bootstrap OK` nor a
pytest report, so it cannot be mistaken for proof); a `conftest.py` inside the
suite itself and a plugin from the runtime lock are deliverables of `P1-QA-00` and are reviewed there; a
`.pth` file in `.venv/lib/python3.12/site-packages` is executed at interpreter start-up,
after the scrubbing has already happened.

`make bootstrap` brings the governance environment `.venv/bootstrap` into exact agreement with
`requirements/validation.lock`: extra distributions are removed, after which it verifies
that exactly what is locked is installed (plus the seeded `pip`).

Importing foundation code from `src/` is provided by two root-owned mechanisms:
`PYTHONPATH=src` in module invocations and `pythonpath = ["src"]` in
`[tool.pytest.ini_options]`. Thanks to the second, the lanes' literal commands work
without editing the environment:

```bash
.venv/bin/pytest tests/integration/db
.venv/bin/pytest tests/integration/storage
```

A lane does not need to add `sys.path` manipulation to a conftest, and is not allowed to.

### Host requirements

- CPython of exactly the version in `.python-version` (currently `3.12.3`). If `python3.12` is not on
  `PATH` or is the interpreter of an active virtualenv, bootstrap refuses to run —
  pass the base interpreter: `make bootstrap FOUNDATION_PYTHON=/path/to/python3.12`.
- Docker with the `compose` plugin — for `up`/`down` and the service checks.
- Network access to PyPI and the container registry on the first `make bootstrap` / `make up`.

Caches are pinned inside the repository (in `.gitignore`): uv in `.local/uv-cache`, pip
in `.local/pip-cache`. Therefore `make bootstrap` without any variables does not write to the
home directory — neither to `~/.cache/uv` nor to `~/.cache/pip` — and does not require setting
`UV_CACHE_DIR`.

`make bootstrap` is idempotent and never generates a lock: a missing `uv.lock`
or `requirements/validation.lock` is an explicit error, not a reason to rebuild the pins.
All dependency versions, the exact images (tag + digest) and the exact invocation lines are
recorded in `docs/program/FOUNDATION_LOCK.json`.

### Local environment

```bash
cp .env.example .env
```

`.env` is ignored by git and is never committed; `.env.example` holds only
throwaway local examples. Before `make up`, give your lane unique
`FOUNDATION_INSTANCE`, `POSTGRES_PORT`, `S3_API_PORT`, `S3_CONSOLE_PORT`,
`POSTGRES_DB` and `S3_BUCKET` values: FF-01 forbids two lanes from sharing one live
service state. Before any service command, `make` checks that all
frozen names are set and that the service side (`POSTGRES_*`, `MINIO_ROOT_*`)
agrees with the application side (`DATABASE_URL`, `S3_*`).

### If something is wrong

- `.env is missing` — run `cp .env.example .env` and set your lane's values.
- `is an active virtualenv interpreter` — you are in an activated venv; open a clean
  shell or pass `FOUNDATION_PYTHON`.
- `Python version mismatch` — the pin is exact; install the required version or give its path.
- `uv.lock is missing` — only the owner of the pins creates the lock, in a separate task.
- `a foundation provider implementation is not present yet` — the corresponding lane
  has not delivered its file yet; the owning task is named in the error text.

## Target stack

- backend/control plane: Python + FastAPI/ASGI, modular monolith;
- metadata/durable workflow state: PostgreSQL;
- files/artifacts: private S3-compatible object storage;
- frontend: Next.js + React + TypeScript strict, App Router, FSD/vertical slices;
- contracts: OpenAPI + JSON Schema + SQL migrations;
- heavy analysis: a separate execution process/worker that communicates with the control plane only through versioned packages/ports;
- local development: containers for PostgreSQL and S3-compatible storage; exact tool versions are fixed in `CP-01`.

## Checkpoint versions

| Checkpoint | Tag | Main result |
|---|---|---|
| CP-00 | `v0.0.0-architecture` | business/architecture/contracts frozen enough to code |
| CP-01 | `v0.1.0-foundation` | reproducible repo/toolchain/local stack |
| CP-02 | `v0.2.0-walking-skeleton` | upload → fake run → finding end-to-end |
| CP-03 | `v0.3.0-audit-alpha` | first real audit stage + evidence |
| CP-04 | `v0.4.0-audit-beta` | main audit pipeline |
| CP-05 | `v0.5.0-expert` | expert decisions + KB/review workflow |
| CP-06 | `v0.6.0-comparison-core` | deterministic comparison core |
| CP-07 | `v0.7.0-comparison-advanced` | AI/graphic comparison layers |
| CP-08 | `v0.8.0-distributed` | remote workers with fencing/recovery |
| CP-09 | `v0.9.0-hardening` | security/retention/restore/load/cost gates |
| CP-10 | `v1.0.0` | release acceptance |

Each checkpoint is created only after the automated gates, the manual local runbook and a completed checkpoint report.

## What the package deliberately omits

- production business implementation;
- secrets and real production payloads;
- exact TTL/retention for user data — this is an owner/legal decision;
- exact cloud/vendor choices and provider credentials;
- importing legacy modules “to speed things up” without a separate contract/characterization task.

These are not gaps: they are listed as explicit decisions/gates in the roadmap and the ADRs.
