# Task CMP-STORAGE-PARTS-01 — multipart staging in the storage port (ADR-0025 decision 10)

## Outcome
The `storage` boundary stages one file as an S3 multipart upload that a database row owns before its first byte
moves, and publishes it only after the whole object has been read back and matched to the declared SHA-256 and size.
A second function aborts uploads that will never be completed, in a form a comparison work handler can call later, and
`scripts/recovery/blob_reference_audit.py` reports the published blobs that no table names. The existing `BlobStore`
port, its adapter behaviour and its callers are unchanged byte for byte.

## Depends on
- CMP-SEAL-C0 (merged on `integration/compare-modules` at `0990de4b`): `comparison_upload_file.multipart_token`,
  `comparison_upload_part`, the four audited blob columns
- CMP-ADR-01 (ADR-0025 decision 10 and decision 9's 16 MiB chunk)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` unchanged (error codes: `validation_failed`, `storage_integrity_error`,
  `staged_upload_lost`, `dependency_unavailable`; no new code)
- API contract: `contracts/api/v1/openapi.json` `1.9.0`, 115 paths / 130 operations / 351 schemas, 27 error codes
- analysis/comparison/event contract: ADR-0025 decisions 9, 10 and the 2026-10-27 addendum
- migration head: `0038_comparison_foundation` (not touched)
- base commit: `cc3dd36b` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the base is the seal's tree: contract `1.9.0`, 115 / 130 / 351, head `0038_comparison_foundation`; the lane
  re-reads it before any edit and STOPs if it differs

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-28
- command: `git show HEAD:contracts/api/v1/openapi.json | python3 -c "import json,sys;d=json.load(sys.stdin);print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; git grep -n "^revision: str" HEAD -- db/migrations/versions/20261028_0038_comparison_foundation.py | cut -d: -f3-; git grep -n "MAX_PART_NUMBER\s*[:=]\|PART_SIZE_BYTES\s*[:=]" HEAD -- db/migrations/versions/20261028_0038_comparison_foundation.py | cut -d: -f3-`
- captured_output:
  ```text
  contract 1.9.0 115 paths 130 operations 351 schemas 27 error codes
  revision: str = "0038_comparison_foundation"
  MAX_PART_NUMBER = 10_000
  PART_SIZE_BYTES = 16 * 1024 * 1024
  ```
- interpretation: equal to the premise, so the lane did not STOP. The part number bound (10 000) and the part size
  bound (16 MiB) are the table's own CHECK values, which the port repeats as refusals before any store call

### P-02 — the port is pinned by a test, so it cannot grow a method
- captured_at: 2026-10-28
- command: `grep -n "dir(BlobStore)" tests/integration/storage/test_publication.py; grep -rn "def stage_temporary" --include=*.py tests | wc -l`
- captured_output:
  ```text
  169:    members = {name for name in dir(BlobStore) if not name.startswith("_")}
  8
  ```
- interpretation: `test_the_port_offers_no_way_to_name_or_delete_an_object` pins the member set of `BlobStore`, and
  eight test doubles implement it. Multipart staging is therefore a second Protocol (`MultipartStaging`) that the S3
  adapter also satisfies; `BlobStore` and `DurablePublicationStore` do not change

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/storage/**`
- `scripts/recovery/blob_reference_audit.py`
- `tests/unit/storage/**`
- `tests/integration/storage/**`
- `docs/program/tasks/CMP-STORAGE-PARTS-01.md`
- `docs/program/CMP-STORAGE-PARTS-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-storage-parts-01`
- postgres_port: `57730`
- s3_api_port: `61730`
- s3_console_port: `61731`
- postgres_db: `auditmanager_cmp_storage_parts_01`
- s3_bucket: `auditmanager-cmp-storage-parts-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependency and lock files
- `src/auditmanager/bootstrap/**`, `src/auditmanager/api/**`, `src/auditmanager/comparison/**` (the wiring and the
  work kind belong to the lanes that use the functions)
- every other lane's paths of `docs/program/dispatch/CMP-WAVE-C0.md` section 2
- `tests/integration/recovery/test_blob_reference_audit.py` and every other test outside the two allowed directories

## Non-goals
- no router, no adapter in `bootstrap`, no operation of the seal is implemented (CMP-INGEST-01 wires
  `uploadComparisonUploadPart` and `completeComparisonUploadFile` over the functions this lane adds)
- no SQL against a comparison table is written or read by the storage package; the database owner of a file and its
  parts is CMP-INGEST-01
- the work kind that calls the abort sweep is registered by the lanes that use it, not here
- no change to `BlobStore`, `stage_temporary`, `verify_temporary`, `publish`, `put_blob` or `DurablePublicationStore`

## Deliverables
1. `MultipartStaging` (a second Protocol in `storage/port.py`), implemented by `S3BlobStore`:
   `begin_multipart`, `upload_part`, `complete_multipart`, `abort_multipart`, with value types
   (`UploadedPart`, `MultipartSweepReport`), `new_multipart_token` and typed refusals under existing error codes
2. `abort_multipart_sweep(store, tokens)` — the function a comparison work handler calls
3. `report_unreferenced_comparison_blobs(session)` in `scripts/recovery/blob_reference_audit.py`; `audit_blob_references`
   keeps its statements and their order
4. tests in `tests/unit/storage/**` and `tests/integration/storage/**`, each new guard shown failing under a quoted
   mutation
5. the report `docs/program/CMP-STORAGE-PARTS-01.md` with the exact public names for CMP-INGEST-01

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/storage tests/integration/storage` on the lane's own MinIO and PostgreSQL
- expected: all green; the pre-existing storage tests are unchanged and green
- command: `git diff --check`; `pytest -q tests/contract` minus the three `D-220` files
- expected: clean / green

## Integration contract
CMP-INGEST-01 persists `new_multipart_token()` in `comparison_upload_file.multipart_token` and commits it, then calls
`begin_multipart`, then `upload_part` for each part, recording the returned `UploadedPart` in
`comparison_upload_part`; completion passes the recorded parts to `complete_multipart` with the file's declared
SHA-256 and size and gets a `PublishedBlob` back (its `blob_id` goes into `comparison_upload_file.blob_id`). A work
handler of the abort sweep marks the file and its parts in the database first, then calls
`abort_multipart_sweep(store, tokens)`.

## Failure/idempotency/security cases
- a completed object whose bytes do not match the declared SHA-256 or size is refused and leaves no object (temporary
  or canonical) in the bucket
- an aborted upload leaves no object and no in-progress upload; a part sent after the abort is refused
- parts out of order, with a gap, duplicated, or not matching what the store holds are refused at completion before the
  object is assembled
- `begin_multipart` and `abort_multipart` and the sweep are idempotent; `complete_multipart` after a crash between the
  assembly and the verification resumes at the verification
- the abort never deletes a published blob
- a token that is not minted by `new_multipart_token` is refused (no arbitrary key stems)

## Rollback / feature flag
Not applicable: nothing calls the new functions yet; the module flag (`comparison/modules.py`) gates the callers.

## Handoff
- changed files: `src/auditmanager/storage/{__init__,errors,multipart,port,public,s3}.py` (`multipart.py` new),
  `scripts/recovery/blob_reference_audit.py`, `tests/unit/storage/test_multipart_offline.py` (new),
  `tests/integration/storage/{test_multipart_staging,test_unreferenced_comparison_blobs}.py` (new), this file and
  `docs/program/CMP-STORAGE-PARTS-01.md`
- commands/results: `pytest -q tests/unit/storage tests/integration/storage` 259 passed (106 pre-existing + 153 new);
  `tests/contract` minus the three `D-220` files 1307 passed; `git diff --check` clean; 28 mutations shown red and
  restored (report section 5)
- known limits: report section 6 (5 MiB minimum of every part but the last; the whole object is re-read through the API
  process at completion; no CLI or restore-drill wiring of the report)
- integration notes: report sections 3 and 7. The protocol is named `MultipartStaging`, not `MultipartBlobStore`,
  because `test_the_package_ships_no_filesystem_adapter` pins every exported name ending `BlobStore`. The one addition
  beyond the brief is `before_publish` on `complete_multipart` (the seam `DurablePublicationStore` has)
