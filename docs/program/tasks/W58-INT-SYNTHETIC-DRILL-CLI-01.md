# Task W58-INT-SYNTHETIC-DRILL-CLI-01 — prepare and invoke one isolated synthetic restore

task_id: W58-INT-SYNTHETIC-DRILL-CLI-01

## Outcome

An offline builder prepares a private, canonical W54-shaped/W58-sealed small
synthetic copy from an operator-supplied real PostgreSQL 17 custom dump,
frozen stand-fingerprint-v1 output and one positive Blob payload. A separate
operator CLI wires that copy to the completed W58 PostgreSQL restore callback,
target object copy and Blob readback. It refuses non-isolated configuration,
nonempty target bucket, wrong PostgreSQL tools and incomplete positive-Blob
evidence, including a missing `input_manifest_entry` reference. Container-free
tests verify preparation and refusal sequencing; no
actual service drill is claimed until a later owned lane runs the CLI.

## Depends on

- `W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01` — completed W58 coordinator.
- `W58-INT-ISOLATED-POSTGRES-ADAPTER-CODE-01` — completed guarded PG callback.
- `W58-INT-TARGET-DIGEST-METADATA-01` — completed positive Blob read path, integrated in dev32.
- `W54-STAND-COPY-01` — completed stand-fingerprint-v1 source and record layout.

## Frozen inputs

- base commit: `5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15`
- published development commit at dispatch: `5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15`;
- W58 scope/plan SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`, `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- coordinator/PG adapter/target copy/preflight SHA-256: `4fbb33f0992b7c3ea68bba00e7e26c7c256c410b52a3abb0c8af822caa6dc436`, `0d6ccc96ca38aecbe39dc9e5a9c8da059c9ea9d18395a86e76bba3d73b9175b0`, `bd0ab6f3ae14c69121d18b98f9c8ef1033d25bd61b2f68294e95207b3c0aaa2f`, `91d40a5dbb4d9108ff3ed5aa81d86e861dc57f0fca3d37fc3250270f975a7b76`;
- storage public/stand SQL SHA-256: `b8f1c8163827e9e86ae7e3a96a286e15e7fb41afc35813cadb7f705f9c54247c`, `998442c31a583831d3dd941e81cb7ef039045a2212a25bfb47c8ce14bbfa4f86`;
- migration head: `0023_norm_citations`; API/domain/error/stage contracts unchanged.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W58 coordinator and PG callback exist, but no operator command
  builds a small positive-Blob copy or wires a live isolated target.

### P-01 — available helpers and missing operator CLI

- captured_at: 2026-10-16
- command: `rg -n '^def run_isolated_restore_drill|^def restore_isolated_postgres|^def main\(' scripts/recovery/isolated_restore_drill.py scripts/recovery/isolated_postgres_restore.py scripts/recovery/offline_restore_preflight.py scripts/recovery/object_copy.py`
- captured_output:
  ```text
  scripts/recovery/object_copy.py:186:def main(argv: list[str] | None = None) -> int:
  scripts/recovery/isolated_restore_drill.py:53:def run_isolated_restore_drill(
  scripts/recovery/offline_restore_preflight.py:127:def main(argv: list[str] | None = None) -> int:
  scripts/recovery/isolated_postgres_restore.py:158:def restore_isolated_postgres(
  ```
- interpretation: existing CLIs seal/verify local input only; the DB+Blob
  coordinator and adapter are importable. This does not prove a runnable
  source copy, safe target identity or real DB/S3 recovery.

### P-02 — host PostgreSQL tool mismatch

- captured_at: 2026-10-16
- command: `pg_dump --version; pg_restore --version; /usr/lib/postgresql/17/bin/pg_dump --version; /usr/lib/postgresql/17/bin/pg_restore --version`
- captured_output:
  ```text
  pg_dump (PostgreSQL) 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)
  pg_restore (PostgreSQL) 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)
  pg_dump (PostgreSQL) 17.11 (Ubuntu 17.11-1.pgdg24.04+2)
  pg_restore (PostgreSQL) 17.11 (Ubuntu 17.11-1.pgdg24.04+2)
  ```
- interpretation: the operator must pin PostgreSQL 17 tools explicitly;
  ambient PATH cannot safely select the restore tool for a PG17 dump.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/synthetic_drill_fixture.py`
- `scripts/recovery/synthetic_drill_runner.py`
- `tests/integration/recovery/test_synthetic_drill_fixture.py`
- `tests/integration/recovery/test_synthetic_drill_runner.py`
- `docs/program/tasks/W58-INT-SYNTHETIC-DRILL-CLI-01.md`
- `docs/program/W58-INT-SYNTHETIC-DRILL-CLI-01.md`

## Forbidden hotspots

- other `scripts/recovery/**`, `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`;
- root dependency/lock files, composition root, global styles,
  `docs/program/CURRENT_STATE.md`, W56b/W57a/W59 lanes, Git refs and tags.

## Non-goals

- No source S3 mirror provenance: this small synthetic fixture uses an
  operator-owned local payload and a labelled synthetic inventory ETag.
- No real PostgreSQL/S3/Docker use in this source task while W55b gate owns
  resources. No production/stand copy, source metadata preservation,
  deployment, RPO or W58/B6 acceptance.
- No database or bucket creation/cleanup by the runner; the operator supplies
  fresh isolated services and verifies Docker project/volume identity.

## Deliverables

- Offline private fixture builder, opt-in isolated target CLI, focused tests
  and an exact operator runbook with capacity, target isolation and evidence.

## Required tests

- Focused container-free tests for both new modules with no network, Docker,
  PostgreSQL or S3 service startup.
- Python compile, task governance/parser, `git diff --check` and exact six-path containment.
- The actual service drill and full gate remain separately owned under R-135.

## Integration contract

`prepare` builds a private copy directory, one canonical Blob mirror object,
inventory and canonical record from supplied bytes; it does not authenticate
the dump or source SQL session. The target CLI consumes only that frozen copy
and an owner-private 15-name `.env` as data, demands a numeric loopback PG17
target with a disposable name and a distinct empty S3 bucket, pins CLI tools
to PostgreSQL 17, then invokes the existing coordinator and adapter. Only
positive one-Blob readback evidence with one source manifest reference returns
success. Source DB/S3 and target
isolation remain operator proofs, not inferred from loopback syntax alone.

## Failure/idempotency/security cases

- Existing output, unsafe/private-file violations, malformed fingerprint
  lines or mismatched seal refuse before any target call.
- Environment duplicates/unknown fields, target URL/port/bucket mismatch,
  wrong PG tools or nonempty bucket refuse before database restore.
- Failed restore leaves the disposable target for inspection; retry requires
  a fresh empty target DB and bucket. No credential appears in process argv
  or returned evidence.

## Rollback / feature flag

No served behavior or feature flag. Revert the six task paths to remove this
unactivated operator-only preparation.

## Handoff

- changed files: report on completion;
- commands/results: report on completion;
- known limits: synthetic fixture and offline tests are not a service drill;
- integration notes: operator lane runs the documented command only after
  W55b gate releases the host and capacity/identity checks pass.
