# Task W58-INT-ISOLATED-POSTGRES-ADAPTER-CODE-01 — prepare guarded PostgreSQL restore callback

task_id: W58-INT-ISOLATED-POSTGRES-ADAPTER-CODE-01

## Outcome

An unactivated W58 operator callback adapter for `run_isolated_restore_drill`
refuses an unsafe PostgreSQL target or nonempty database, feeds a private dump
to atomic `pg_restore`, computes the one-source `stand-fingerprint-v1` through
`psql`, and yields a read-only repeatable-read Session. Container-free tests
prove arguments, ordering and refusals. No real DB or S3 drill is claimed.

## Depends on

- `W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01` — completed coordinator and callback contract, integrated in dev25.
- `W54-STAND-COPY-01` — completed `pg_restore` and stand fingerprint source.

## Frozen inputs

- base commit: `3d131d2966e0efeea7b53d9662785f253165a9a4`
- dispatch `origin/dev`: `3d131d2966e0efeea7b53d9662785f253165a9a4`;
- W58 scope and code-first plan SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`, `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- W58 coordinator/preflight SHA-256: `4fbb33f0992b7c3ea68bba00e7e26c7c256c410b52a3abb0c8af822caa6dc436`, `91d40a5dbb4d9108ff3ed5aa81d86e861dc57f0fca3d37fc3250270f975a7b76`;
- stand fingerprint source `infra/deploy/copy-serve.sh` SHA-256: `998442c31a583831d3dd941e81cb7ef039045a2212a25bfb47c8ce14bbfa4f86`; extracted marker block SHA-256: `dc1a7923faca4462c3e55b6c3976bc30179c69684c74ae41d3804192efbc6a72`;
- API/domain/error/stage SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`, `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`, `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`, `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head: `0023_norm_citations`; R-135 defers complete beta gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W58 expects a restore callback, while W54 has the sole stand
  fingerprint SQL and atomic `pg_restore` options; there is no W58 adapter.

### P-01 — callback contract and one-source fingerprint

- captured_at: 2026-10-16
- command: `rg -n 'class RestoredDatabase|def run_isolated_restore_drill|fingerprint_sql\(\)|^-- >>> stand-fingerprint-v1|^-- <<< stand-fingerprint-v1|pg_restore --no-owner' scripts/recovery/isolated_restore_drill.py infra/deploy/copy-serve.sh scripts/stand-copy/restore-test.sh`
- captured_output:
  ```text
  scripts/stand-copy/restore-test.sh:161:if ! docker exec -i "$NAME" pg_restore --no-owner --no-privileges --exit-on-error --single-transaction \
  scripts/recovery/isolated_restore_drill.py:39:class RestoredDatabase:
  scripts/recovery/isolated_restore_drill.py:53:def run_isolated_restore_drill(
  infra/deploy/copy-serve.sh:410:fingerprint_sql() {
  infra/deploy/copy-serve.sh:412:-- >>> stand-fingerprint-v1
  infra/deploy/copy-serve.sh:439:-- <<< stand-fingerprint-v1
  infra/deploy/copy-serve.sh:932:    compose exec -T postgres pg_restore --no-owner --no-privileges --exit-on-error --single-transaction \
  ```
- interpretation: the callback port and one fingerprint source exist. This
  output does not prove a target's isolation or that a restore has run.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/isolated_postgres_restore.py`
- `tests/integration/recovery/test_isolated_postgres_restore.py`
- `docs/program/tasks/W58-INT-ISOLATED-POSTGRES-ADAPTER-CODE-01.md`
- `docs/program/W58-INT-ISOLATED-POSTGRES-ADAPTER-CODE-01.md`

## Forbidden hotspots

- existing `scripts/recovery/**`, `infra/**`, `src/**`, `contracts/**`, `db/migrations/**`;
- root dependency/lock files, composition root, global styles,
  `docs/program/CURRENT_STATE.md`, W56b/W57a lanes, origin refs and tags.

## Non-goals

- No actual PostgreSQL/S3/Docker start during this task. The adapter is not
  activated by a CLI, serving route, worker or production deployment.
- No proof that a loopback endpoint is not a tunnel to a production database;
  the operator must own target isolation, PostgreSQL credentials and bucket
  match. No source-writer quiescence, RPO, timing or B6 acceptance.
- No database creation or cleanup by this adapter; only an already empty
  disposable target may be used.

## Deliverables

- One guarded adapter, injected-runner/engine tests and result report.

## Required tests

- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.venv/bin/python -m pytest tests/integration/recovery/test_isolated_postgres_restore.py -q -p no:cacheprovider` — pass.
- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.venv/bin/python -m pytest tests/integration/recovery tests/contract/program/test_wave_governance.py -q -p no:cacheprovider` — pass.
- Python compile, task governance, `git diff --check` and four-path containment.
- Real PostgreSQL/S3 drill and full gate deferred under lane ownership and R-135.

## Integration contract

The caller constructs the application's owned SQLAlchemy Engine for an
operator-owned disposable loopback target and supplies a matching explicit
PostgreSQL host/port/database/user plus an optional private libpq passfile.
The adapter verifies that Engine URL and SQL database/user match, refuses
public/nonempty targets, runs `pg_restore` with `--exit-on-error` and
`--single-transaction` with a no-follow private dump as stdin, executes the
frozen stand SQL through `psql`, validates complete table lines and returns
its SHA-256 with a read-only repeatable-read Session in `RestoredDatabase`.
It cleans up the transaction on context exit. The W58 coordinator rechecks
the returned digest against the copy record and audits Blob references.

## Failure/idempotency/security cases

- Target URL mismatch, non-loopback/default-port/non-disposable name, bad
  passfile, nonempty database or unsafe dump refuses before `pg_restore`.
- Failed/timeout restore, malformed/mismatched fingerprint SQL/output or
  non-read-only transaction refuses before yielding a Session. CLI errors
  are reported without echoing credentials or dump contents.
- A failed restore leaves its disposable target for owner inspection; retry
  requires a fresh empty target. A successful target is read-only during the
  coordinator's DB/S3 audit, but external writers remain an operator concern.

## Rollback / feature flag

The adapter is unactivated. Delete the four task paths; no feature flag.

## Handoff

- changed files: four allowed paths;
- commands/results: result report;
- known limits: no real service acceptance or isolation proof;
- integration notes: instantiate only for an owner-designated isolated lane.
