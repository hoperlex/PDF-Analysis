# Task W57B-INT-CATALOGUE-DB-S3-ACCEPT-01 — real catalogue custody read

task_id: W57B-INT-CATALOGUE-DB-S3-ACCEPT-01

## Outcome

A focused integration test proves that the unserved W57b catalogue reader
obtains exact canonical bytes from a real S3 object through a verified set,
confirmed dual custody and current Attempt in real migration-0023 PostgreSQL.
A forged execution token and a noncurrent Attempt are refused before any object read.

## Depends on

- `W57A-SEAL-01A` — completed 0023 verified-set and custody schema.
- `W57B-INT-CATALOGUE-CUSTODY-READ-01` — completed unserved reader.
- `CFB-INT-DEV-PUBLISH-58` — completed base integrating that reader.

## Frozen inputs

- base commit: `85d9936a8faacc00df3687b32ba51797439f2736`
- API v1 SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- errors SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head: `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- catalogue query SHA-256: `1684cbc9cf3eb24ab51f4edbcc3bc16f51cce9dee2abb1fade2a18206fd69780`;
- W57 plan §§A3.2, B3.1–B3.6; R-76, R-80, R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: test asserts the snapshot's one declared document equals the one persisted document before the read.

## Captured premise evidence

- premise: the W57b reader's original acceptance uses fake Session and BlobStore ports and explicitly leaves real SQL/S3 unverified.

### P-01 — offline limitation on the exact base

- captured_at: 2026-10-16
- command: `rg -n 'fake-port|real DB/S3|does not prove|Real DB/S3' docs/program/W57B-INT-CATALOGUE-CUSTODY-READ-01.md`
- captured_output:
  ```text
41:These fake-port tests do **not** prove that the SQL runs against real 0023
43:published corpus. Real DB/S3 acceptance remains for an isolated integration
  ```
- interpretation: a narrow real-service acceptance can close this evidence gap without activating a caller.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none
- integration grant: integrator message dated 2026-10-16, local source commit and handoff only.

## Allowed paths

- `tests/integration/norms/references/test_catalogue_input_db_s3_accept.py`
- `docs/program/tasks/W57B-INT-CATALOGUE-DB-S3-ACCEPT-01.md`
- `docs/program/W57B-INT-CATALOGUE-DB-S3-ACCEPT-01.md`

## Lane resources

- foundation_instance: `auditmanager-w57b-cat-accept-01`
- postgres_port: `55462`
- s3_api_port: `59064`
- s3_console_port: `59065`
- postgres_db: `auditmanager_w57b_cat_accept_01`
- s3_bucket: `auditmanager-w57b-cat-accept-01`

## Forbidden hotspots

All runtime modules, `contracts/**`, `db/migrations/**`, root dependencies
and lockfiles, composition root, global styles, API/routes, source corpus,
W54/W56/W58 paths, `CURRENT_STATE.md`, production DB/S3, remote refs, tags.

## Non-goals

No served W57b route, reference-resolution result, 0024 migration, review of
unparsed slugs, qualified W54 corpus, provider call, export or B3.5 verdict.
No complete gate or beta acceptance under R-135.

## Deliverables

One targeted real PostgreSQL/S3 integration test, this formal task and one
paired result report. The test is not an application data seeder.

## Required tests

- `PYTHONPATH=src:. .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/references/test_catalogue_input_db_s3_accept.py` against this isolated 0023 instance; hard fail on absent service.
- Python compilation, frozen hashes, task governance, exact three-path and `git diff --check` proof.
- No broad suite, full gate, deployment or paid call.

## Integration contract

The test creates a one-document synthetic snapshot and complete one-window
vector build, publishes set and canonical catalogue bytes through the S3
adapter, records available Blob metadata, confirms two admissions/bindings,
and forces the deferred verified-set constraint. It pins the set on one Run,
claims a real Job/Attempt/Lease, reads the catalogue through
`load_verified_catalogue`, validates those bytes with `load_pinned_catalogue`,
then proves a forged token is rejected. Database changes roll back; the
temporary S3 bucket is emptied and deleted.

## Failure/idempotency/security cases

An absent/mismatched PostgreSQL revision fails explicitly. Missing S3 fails
explicitly. No credential or token value enters the report or Git. The
test leaves no database rows or bucket, and does not contact a provider.

## Rollback / feature flag

Test-only addition. Revert these three files; no runtime flag or data rollback.
