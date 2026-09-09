# Task P1-INT-00 — pin the early foundation toolchain and command surface

> **Status: specified; dispatch only after `FF-01 ACCEPTED`.**

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

- changed files and hashes of locks/images
- bootstrap transcript and clean second-run proof
- known host prerequisites
- exact commit used by all three provider lanes
