# Task W58-INT-OFFLINE-RESTORE-PREFLIGHT-PREP-01 — check one offline recovery input set

task_id: W58-INT-OFFLINE-RESTORE-PREFLIGHT-PREP-01

## Outcome

A read-only preflight refuses a local W54 copy and W58 object mirror unless the
record, dump, inventory, object seal and every mirrored payload agree before an
isolated restore. It does not restore a database or qualify a backup.

## Depends on

- `W54-STAND-COPY-01` — completed copy record, dump and inventory formats.
- `W58-INT-OBJECT-COPY-PREP-01` — completed offline mirror seal and rehash.
- `W58-INT-COPY-RECORD-BINDING-PREP-01` — completed record/inventory/seal binding.

## Frozen inputs

- base commit: `62a9e23dd44cdd7d9373e69413ce6ad27e508d3d`
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- W54 copy-serve SHA-256: `998442c31a583831d3dd941e81cb7ef039045a2212a25bfb47c8ce14bbfa4f86`;
- W54 pull-copy SHA-256: `7e44d3f6f3126d8b758f85e031cc9a8bacb69023b5ac02f9616b60b397e341da`;
- W58 object-copy SHA-256: `2e66ca7b30672d7118c037a35ab2ac71251082d6a8ed0602327e9e1f44195884`;
- W58 record-binding SHA-256: `080a82775b469d09321cbc79d2d65d284f2aebb5e577e997572531e905e21bb6`;
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- domain identifiers SHA-256: `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- error catalog SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head: `0022_findings_v2`; R-135 defers the complete gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: existing W58 checks take the inventory and mirror, or the record,
  inventory and seal, but neither checks local dump bytes alongside both.

### P-01 — existing entry points omit the dump

- captured_at: 2026-10-15
- command: `rg -n '^def (verify_copy_record_binding|verify_manifest)\(' scripts/recovery/copy_record_binding.py scripts/recovery/object_copy.py`
- captured_output:
  ```text
  scripts/recovery/object_copy.py:150:def verify_manifest(inventory_data: bytes, objects_root: Path, sealed_bytes: bytes) -> None:
  scripts/recovery/copy_record_binding.py:151:def verify_copy_record_binding(record_data: bytes, inventory_data: bytes, sealed_data: bytes) -> None:
  ```
- interpretation: both are reusable; an additional offline caller must hash
  the local dump and bind all five inputs before restore.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/offline_restore_preflight.py`
- `tests/integration/recovery/test_offline_restore_preflight.py`
- `docs/program/tasks/W58-INT-OFFLINE-RESTORE-PREFLIGHT-PREP-01.md`
- `docs/program/W58-INT-OFFLINE-RESTORE-PREFLIGHT-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependency and lock files;
- existing `scripts/recovery/**`, `src/**`, `infra/deploy/**`;
- composition root, global styles, corpus data, Docker/S3/DB and Git refs.

## Non-goals

- No actual restore, S3 fetch or readback, DB-to-Blob reference check, writer
  quiescence proof, scheduling, RPO, production qualification or runtime switch.
- A changed mirror after this check needs a fresh preflight; the tool creates
  no durable acceptance marker.

## Deliverables

- One read-only offline preflight module/CLI, focused refusal tests and report.

## Required tests

- `.venv/bin/python -m pytest tests/integration/recovery/test_offline_restore_preflight.py -q -p no:cacheprovider` — focused cases pass.
- `.venv/bin/python -m py_compile scripts/recovery/offline_restore_preflight.py tests/integration/recovery/test_offline_restore_preflight.py` — syntax passes.
- `git diff --check` — no whitespace errors.
- Full gate and DB/S3 drill deferred under R-135 and the future W58 recovery freeze.

## Integration contract

Call `verify_offline_restore_inputs(copy_dir, objects_root)` immediately before
an isolated restore while both private directories remain frozen. `copy_dir`
holds canonical `record.json`, `db.dump`, `inventory.tsv`, `objects.json`.
The function opens each as a regular, nonsymlink file, invokes the existing
record/seal and mirror checks, streams and hashes the dump, then checks local
file identity/metadata again. It returns only on exact agreement and writes
nothing. A later W58 owner must separately restore and test DB and Blob
references on isolated data and prove writer quiescence.

## Failure/idempotency/security cases

- Missing or symlinked files/roots, public or foreign-owned directories,
  changed copy files, dump size/hash mismatch, inventory/seal mismatch and
  missing/extra/changed mirrored payloads refuse.
- Repeated checks are read-only. The W54 object key is a transport locator;
  ETag is never treated as a payload checksum.

## Rollback / feature flag

No application behavior change or feature flag. Delete the four added files
to roll back this unconnected preparation.

## Handoff

- changed files: the four allowed paths;
- commands/results: `docs/program/W58-INT-OFFLINE-RESTORE-PREFLIGHT-PREP-01.md`;
- known limits: no actual restore or live source proof;
- integration notes: keep unconnected until an owned W58 recovery integration.
