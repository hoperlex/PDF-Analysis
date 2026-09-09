# Task P1-INT-00 — pin the early foundation toolchain and command surface

> **Status: implemented on branch `agent/p1-int-00`; READY_FOR_PRIMARY_REVIEW.**
> Executed from the `FF-01 ACCEPTED` commit `0b01a3eefe0e6724f6570ccebb9154daf1fdbaec`.
> This task is **not accepted**: `P1-INF-01`, `P1-DB-01` and `P1-STO-01` stay blocked
> until an independent review accepts the pins and the command surface, and until the
> integrator records the resulting `P1_INT_SHA`.

## Outcome

One reproducible Python toolchain, environment contract and root command surface that
the three PostgreSQL/S3 provider lanes consume without modifying.

## Depends on

- `P0-FND-00` — completed with `FF-01 ACCEPTED`

## Frozen inputs

- `docs/program/PROTOTYPE_FOUNDATION_FREEZE.md` at the accepted commit
- CP-00 domain/analysis/event contracts: read only
- migration head: `none`
- base commit: exact `P0-FND-00` integration commit, pinned by the integrator at dispatch

## Allowed paths

- `.python-version`, `pyproject.toml`, `uv.lock`
- `Makefile`, `.env.example`
- `docs/program/FOUNDATION_LOCK.json`
- foundation command sections in `README.md`
- `docs/program/tasks/P1-INT-00.md` status/handoff

## Forbidden hotspots

- runtime provider code, `infra/local/**`, `db/migrations/**`, `tests/**`, `web/**`
- every contract, CP-00 artifact and Git tag

## Non-goals

- No PostgreSQL/MinIO service, migration, storage adapter or product code.
- No frontend toolchain and no dependency needed only by a later stage.

## Deliverables

- exact supported Python, `uv`, runtime/test dependency and container-image pins
- reproducible lock; no floating dependency or image reference
- `.env.example` with all service, application and lane-isolation names frozen by FF-01
  and disposable local values
- the nine literal `make` targets frozen by FF-01
- stable forwarders for the later INF, DB, storage and QA implementations at the exact
  paths reserved by FF-01; missing implementations fail explicitly rather than falling
  back to a substitute
- machine-readable `FOUNDATION_LOCK.json` containing pins, paths and commands

## Required tests

- Command: `make bootstrap`
  Expected: exit `0`; `.venv/bootstrap/bin/python` and `.venv/bin/python` both execute
  their locked smoke probes, and a second run changes no lock or tracked file.
- Command: `make -n up down check-services migrate check-db check-storage test-foundation foundation`
  Expected: exit `0`; all required targets exist.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, `PASS`.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Provider lanes may rely on exact locked dependencies, environment names and commands.
They may not add or upgrade a root dependency or change the command surface.
Each lane must override the disposable defaults with a unique `FOUNDATION_INSTANCE`,
ports, database and bucket before it starts live services.

## Failure/idempotency/security cases

- Bootstrap fails when a required lock is missing; it never regenerates silently.
- No real credential or secret is stored in tracked files.
- Repeated bootstrap is idempotent.

## Rollback / feature flag

Revert before provider integration. A later pin change is a new single-owner task.

## Handoff

Delivered on `agent/p1-int-00` from base `0b01a3eefe0e6724f6570ccebb9154daf1fdbaec`.

**Changed files.** `.python-version`, `pyproject.toml`, `uv.lock`, `Makefile`,
`.env.example`, `docs/program/FOUNDATION_LOCK.json`, the foundation command section of
`README.md`, and this status/handoff. Nothing else is touched.

**Pins.** Python `3.12.3`; `uv 0.12.11` installed from a sha256-verified artifact set;
`psycopg[binary]==3.3.5`, `SQLAlchemy==2.0.52`, `alembic==1.19.2`, `boto3==1.43.90`,
`pytest==9.1.1` (group `test`). `uv.lock` holds 23 `[[package]]` entries: 22 third-party
packages plus the virtual root, of which 20 install on linux/x86_64 (`colorama` and
`tzdata` are `sys_platform == 'win32'`). Images are pinned by
tag **and** multi-arch index digest: `postgres:17.11-trixie`,
`minio/minio:RELEASE.2025-09-07T16-13-09Z`, `minio/mc:RELEASE.2025-08-13T08-35-41Z`.
No floating tag and no `latest` reference exists. Exact digests, lock hashes and the
literal invocation of every target are in `docs/program/FOUNDATION_LOCK.json`.

**Bootstrap.** `make bootstrap` builds `.venv/bootstrap` from
`requirements/validation.lock` with `--require-hashes` and `.venv` from `uv.lock` with
`uv sync --frozen`, then probes both against their own locks. It never writes a lock: a
missing `uv.lock` is a hard, explicit failure. A second run installs nothing and leaves
every tracked file and both locks byte-identical.

**Host prerequisites.** CPython exactly `3.12.3` as a base interpreter (an active
virtualenv is refused, not silently used); Docker with the `compose` plugin for the
service targets; network to PyPI and the container registry on first use. Where
`python3.12` is not on `PATH`, pass `FOUNDATION_PYTHON=<path>`.

**Commit for the provider lanes.** Lanes must not branch from `agent/p1-int-00`. They
branch from the integrator's P1-INT-00 integration commit (`P1_INT_SHA`), recorded by
the integrator after this task is accepted, and each lane must first give itself a
unique `FOUNDATION_INSTANCE`, `POSTGRES_PORT`, `S3_API_PORT`, `S3_CONSOLE_PORT`,
`POSTGRES_DB` and `S3_BUCKET` in its own `.env`.

**Evidence contract for the provider lanes.** `check-services`, `check-db` and
`check-storage` must each print `FOUNDATION-CHECK OK <target>` as their last line, after
their assertions pass. `make` refuses a zero exit status without that line, and refuses a
reserved path that exists but is zero bytes. This is a P1-INT-00 addition to the command
contract, not an FF-01 requirement: an exit code alone is not evidence, and without it a
stub checker would make `make foundation` report success having proved nothing. Reject it
in review if the program does not want it — it is a deliberate constraint on three lanes.

**Known limitations.** No target beyond `bootstrap` has been executed end-to-end, because
every one of them forwards to a provider implementation that does not exist yet; each was
exercised only to the point of its explicit refusal. The full list, including the
`.venv/bootstrap` nesting that FF-01's literal paths require, is in
`docs/program/FOUNDATION_LOCK.json` under `known_limitations`.
