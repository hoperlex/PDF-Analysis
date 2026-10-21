# Task W58-INT-STORAGE-KEY-RESOLVER-01 — expose the storage-owned recovery key resolver

task_id: W58-INT-STORAGE-KEY-RESOLVER-01

## Outcome

The W58 offline Blob-object binding can use the storage adapter's actual
canonical key rule through an explicitly recovery-scoped public function.
One focused test proves the bridge binds two available Blob rows with that
function and rejects an invalid Blob ID.

## Depends on

- `W58-INT-BLOB-OBJECT-BINDING-PREP-01` — completed pure bridge requiring a
  storage-owned resolver.
- `W58-INT-BLOB-REFERENCE-AUDIT-PREP-01` — completed available Blob fact audit.

## Frozen inputs

- base commit: `8dac96f7c36fad3e3855ab6abeb180a2a503fd9a`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- storage public SHA-256: `a044e35616de2f392bac20e83901dcdcadb95a04ce1213d50bd0326a16e1dff8`;
- private storage layout SHA-256: `33cc2c9693d319088a14bcd913af26eec7ef89dd024352212ca0c7f359e907df`;
- W58 bridge SHA-256: `37e705e36877ede907a7e362c601f4cfa3286830b6f9ff86c8cf8ff3c5e4c169`;
- API/domain/error/analysis registry SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`, `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`, `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`, `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head: `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the canonical key rule is implemented in storage's private layout,
  and `storage.public` currently exports no key resolver.

### P-01 — private rule and public boundary

- captured_at: 2026-10-15
- command: `rg -n '^def canonical_key\(|^__all__' src/auditmanager/storage/public.py src/auditmanager/storage/_object_layout.py`
- captured_output:
  ```text
  src/auditmanager/storage/public.py:31:__all__ = [
  src/auditmanager/storage/_object_layout.py:39:def canonical_key(blob_id: BlobId) -> str:
  src/auditmanager/storage/_object_layout.py:58:__all__ = [
  ```
- interpretation: the private rule exists and the public module has no
  resolver declaration. The output does not establish a storage readback.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/storage/public.py`
- `tests/integration/recovery/test_blob_object_binding.py`
- `docs/program/tasks/W58-INT-STORAGE-KEY-RESOLVER-01.md`
- `docs/program/W58-INT-STORAGE-KEY-RESOLVER-01.md`

## Forbidden hotspots

- `src/auditmanager/storage/_object_layout.py`, `src/auditmanager/storage/s3.py`;
- other `src/**`, existing `scripts/recovery/**`, other tests and reports;
- `contracts/**`, `db/migrations/**`, root dependencies/lockfiles;
- composition root, global styles, Docker/S3/DB, Git refs.

## Non-goals

- No change to the canonical layout, BlobStore port or S3 adapter behavior.
- No actual restore, S3 read, mirror rehash or recovery acceptance. Product
  business code must continue to use opaque Blob IDs, not object keys.

## Deliverables

- A validated recovery-only storage public resolver, one integration test and
  a limitation report.

## Required tests

- `.venv/bin/python -m pytest tests/integration/recovery/test_blob_object_binding.py -q -p no:cacheprovider`
- `.venv/bin/python -m pytest tests/integration/recovery -q -p no:cacheprovider`
- `.venv/bin/python -m py_compile src/auditmanager/storage/public.py tests/integration/recovery/test_blob_object_binding.py`
- task governance, `git diff --check` and exact-path containment.
- Full gate deferred under R-135.

## Integration contract

This task alone owns the `storage.public` hotspot for this integration slice.
`canonical_object_key_for_recovery(blob_id)` validates the opaque ID and
delegates to the same private `canonical_key` function used by `S3BlobStore`.
The recovery caller may pass it as `canonical_key_for` to
`bind_available_blob_objects` after the offline preflight and restored-DB
audit. The function exposes no bucket, credentials or object bytes; its string
return is a transport locator solely for isolated recovery verification.

## Failure/idempotency/security cases

- Invalid IDs refuse before key calculation. A valid ID deterministically
  produces the adapter's canonical key. The function writes nothing and makes
  no network call. W58 bridge still refuses missing/mismatched/ambiguous sealed
  objects. Do not log keys or put them in product error responses.

## Rollback / feature flag

No runtime behavior or feature flag changes. Remove the new function/export,
test and task/report to roll back this unactivated recovery seam.

## Handoff

- changed files: the four allowed paths;
- checks/results: `docs/program/W58-INT-STORAGE-KEY-RESOLVER-01.md`;
- known limits: no real DB/S3 recovery drill;
- integration notes: keep resolver use inside W58 recovery tooling only.
