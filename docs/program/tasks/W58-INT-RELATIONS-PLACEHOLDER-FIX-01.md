# Task W58-INT-RELATIONS-PLACEHOLDER-FIX-01 — make empty-target query executable

task_id: W58-INT-RELATIONS-PLACEHOLDER-FIX-01

## Outcome

The W58 isolated PostgreSQL callback can check an empty PostgreSQL 17 target
with psycopg before any `pg_restore`. A fresh synthetic DB/Blob target drill
then proves the fixed preflight and full restored readback.

## Depends on

- `W58-INT-ISOLATED-POSTGRES-ADAPTER-CODE-01` — completed guarded PG callback;
- `W58-INT-SYNTHETIC-DRILL-CLI-01` — completed opt-in source and target CLI;
- `CFB-INT-DEV-PUBLISH-38` — published dev base
  `26a9af241bf81f222304a43b9d14c4d50baffe54`.

## Frozen inputs

- base commit: `26a9af241bf81f222304a43b9d14c4d50baffe54`
- W58 scope SHA-256 `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- copy/restore plan SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- one synthetic source copy: dump SHA-256
  `c41002e405ab84e2b9c676321aea8b923f65f85723744cd9fc34fa691b448f91`,
  Blob SHA-256 `6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f`;
- migration head `0023_norm_citations`, API/domain/error/stage contracts unchanged.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `_RELATIONS` is submitted through SQLAlchemy `exec_driver_sql`,
  which sends `%` to psycopg's placeholder parser before target restore.

### P-01 — real empty target refused before restore

- captured_at: 2026-10-16
- command: `PYTHONPATH=src:. .venv/bin/python -m scripts.recovery.synthetic_drill_runner --copy-dir "$DRILL_ROOT/copy/$STAMP" --objects-root "$DRILL_ROOT/copy/objects" --target-env "$DRILL_ROOT/target.env" --pg17-bin /usr/lib/postgresql/17/bin`
- captured_output:
  ```text
  REFUSED: ProgrammingError; preserve target for inspection
  public information_schema table count: 0
  relations ProgrammingError ProgrammingError only '%s', '%b', '%t' are allowed as placeholders, got '%'
  ```
- interpretation: the failure occurs in the empty-target relation query;
  no `pg_restore` or target object write occurred. Keep target-01 for audit;
  use a fresh target-02 for the corrected drill.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/isolated_postgres_restore.py`
- `docs/program/tasks/W58-INT-RELATIONS-PLACEHOLDER-FIX-01.md`
- `docs/program/W58-INT-RELATIONS-PLACEHOLDER-FIX-01.md`

## Forbidden hotspots

`contracts/**`, migration head, root dependency/lock, composition root,
global styles, application/runtime source, shared test fixtures, original
synthetic copy bytes, production DB/S3, `origin/main`, tags and workflow.

## Non-goals

No change to the target-isolation predicate or restore ordering, no old-target
retry, no source S3 attestation, production restore, beta acceptance or W55b
deployment.

## Deliverables

A minimal driver-safe literal-percent fix, exact task/report, read-only probe
of target-01 and positive fresh target-02 DB/Blob restore evidence.

## Required tests

- existing isolated-postgres callback and synthetic-runner focused tests;
- target-01 read-only query probe after fix, showing zero relations;
- fresh distinct target-02 full synthetic drill with positive manifest,
  target object and Blob readbacks;
- governance, whitespace and exact changed-path check.

## Integration contract

The change preserves PostgreSQL `LIKE` matching semantics after psycopg
decodes the escaped literal percent and preserves the empty-before-restore
guard. Integration may publish to `origin/dev` after focused and service
evidence; no `origin/main` authority or full beta verdict follows.

## Failure/idempotency/security cases

The failed target-01 stays untouched. A target-02 failure remains inspectable
and must not be retried in place. Neither generated credentials nor dumps,
copy bytes, local logs or Docker volumes enter Git. The callback still refuses
nonempty or wrong-identity targets before restore.

## Rollback / feature flag

Revert the one script change if rejected. It is opt-in recovery tooling; no
served behavior or runtime flag changes.

## Handoff

- changed files: this task, the one script and its evidence report;
- contracts: none;
- next integration owner: code-first `origin/dev` publication task;
- forbidden hotspots remain untouched.
