# Task W58-INT-COPY-RECORD-BINDING-PREP-01 — bind an offline object seal to its stand copy

task_id: W58-INT-COPY-RECORD-BINDING-PREP-01

## Outcome

A pure verifier refuses a W54 `record.json`, `inventory.tsv` and W58
`offline-object-copy-v1` seal unless they describe the same complete object
inventory. It performs no transfer or restore and does not qualify a backup.

## Depends on

- `W54-STAND-COPY-01` — completed copy record and inventory formats.
- `W58-INT-OBJECT-COPY-PREP-01` — completed offline object seal format.

## Frozen inputs

- base commit: `f88c3bef90f8180ac7ade683bff2b2359d1e9b20`
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- W54 copy-serve SHA-256: `998442c31a583831d3dd941e81cb7ef039045a2212a25bfb47c8ce14bbfa4f86`;
- W54 pull-copy SHA-256: `7e44d3f6f3126d8b758f85e031cc9a8bacb69023b5ac02f9616b60b397e341da`;
- W58 object-copy seal SHA-256: `2e66ca7b30672d7118c037a35ab2ac71251082d6a8ed0602327e9e1f44195884`;
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- domain identifiers SHA-256: `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- error catalog SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head: `0022_findings_v2`; R-135 defers the full gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W54 exports a record, dump and inventory; the W58 seal currently checks
  inventory plus mirrored object bytes, without binding its metadata to the record.

### P-01 — the prior seal takes only inventory and objects

- captured_at: 2026-10-15
- command: `rg -n '^def (build_manifest|verify_manifest)\(' scripts/recovery/object_copy.py`
- captured_output:
  ```text
  113:def build_manifest(inventory_data: bytes, objects_root: Path) -> dict[str, object]:
  150:def verify_manifest(inventory_data: bytes, objects_root: Path, sealed_bytes: bytes) -> None:
  ```
- interpretation: neither function receives the W54 record; the missing binding
  can be checked without changing the existing object scanner.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/copy_record_binding.py`
- `tests/integration/recovery/test_copy_record_binding.py`
- `docs/program/tasks/W58-INT-COPY-RECORD-BINDING-PREP-01.md`
- `docs/program/W58-INT-COPY-RECORD-BINDING-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies and lock files;
- `src/**`, `infra/deploy/**`, existing `scripts/recovery/object_copy.py`;
- composition root, global styles, Docker/S3, `.local/norms/**`, refs and tags.

## Non-goals

- No S3 fetch/readback, DB restore, DB-to-Blob reference query, scheduling,
  RPO, production recovery claim, new format version or runtime activation.
- This verifier does not rehash mirrored payloads or validate that writers
  remained stopped. The existing `object_copy.verify_manifest` does the former;
  an operator-controlled quiescence window must prove the latter.

## Deliverables

- Pure verifier of W54 record, inventory and W58 seal bytes.
- Focused positive/refusal tests and a report naming the integration order.

## Required tests

- `.venv/bin/python -m pytest tests/integration/recovery/test_copy_record_binding.py -q -p no:cacheprovider` — focused cases pass when host resources permit.
- `.venv/bin/python -m py_compile scripts/recovery/copy_record_binding.py tests/integration/recovery/test_copy_record_binding.py` — syntax passes.
- `git diff --check` — no whitespace errors.
- Full gate and DB/S3 drill deferred under R-135 and the absent W58 production freeze.

## Integration contract

After W54 `pull-copy` and W58 object mirror `seal`/`verify`, pass the raw
`record.json`, `inventory.tsv` and `objects.json` bytes to the new pure verifier.
It accepts only `record_version=1`, `kind=copy`, the recorded inventory file,
count, bytes and SHA-256 matching the canonical object seal and exact inventory
rows. A later W58 owner must call it before an isolated restore and separately
prove DB-to-Blob references, S3 readback, repeated restore and the quiescence
boundary. No existing consumer is switched by this task.

## Failure/idempotency/security cases

- Duplicate JSON keys, unknown or incomplete shapes, wrong record kind,
  mismatched inventory digest/count/bytes, missing/reordered seal entries and
  malformed object hashes refuse.
- Same three byte strings always produce the same result; no file is written.
- Object key remains a transport locator, never a Blob identity. ETag is
  inventory provenance, never a content checksum.

## Rollback / feature flag

No application behavior changes or feature flag. Remove the new pure module
and its tests/report to roll back this preparation.

## Handoff

- changed files: the four allowed paths above;
- checks and limitations: `docs/program/W58-INT-COPY-RECORD-BINDING-PREP-01.md`;
- integration notes: keep this verifier inactive until a separately frozen W58
  transport/restore owner wires the complete recovery sequence.
