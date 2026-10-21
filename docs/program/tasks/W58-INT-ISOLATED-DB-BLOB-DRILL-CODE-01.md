# Task W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01 — coordinate isolated DB and Blob restore checks

task_id: W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01

## Outcome

An offline W58 coordinator runs the already sealed copy preflight, caller-owned
isolated PostgreSQL restore, restored-DB reference audit, isolated target-object
copy and complete target Blob readback in that order. The DB audit understands
both Blob columns added by migration 0023 and refuses incomplete verified
retrieval-set references. Container-free tests prove ordering, exact target
coverage and refusal paths. This is code preparation, not a completed drill.

## Depends on

- `W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01` — completed, integrated in dev19.
- `W58-INT-OFFLINE-RESTORE-AUDIT-01` — completed local/DB binding.
- `W58-INT-TARGET-BLOB-READBACK-PREP-01` — completed full target Blob readback.
- `W57A-SEAL-01A` — completed migration 0023 storage seal, integrated in dev23.

## Frozen inputs

- base commit: `e70c91ef7064c8e36f377bd3995960a0e93acf35`
- dispatch `origin/dev`: `e70c91ef7064c8e36f377bd3995960a0e93acf35`;
- W58 scope and code-first plan SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`, `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- migration 0023 SHA-256: `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- object restore, preflight, offline audit and target readback SHA-256: `c1e1a5f54f557bc6ea7e291d94467709fedbf52f1e99f86cdf97775c4d2bca8b`, `91d40a5dbb4d9108ff3ed5aa81d86e861dc57f0fca3d37fc3250270f975a7b76`, `91595bcde9460ef019179fe1e8cf72318d3eeef8c1b5eee8bae4ebfdc63bf8b1`, `b85e85818fce4e0dcbe701c33b30fef7366b008a102b79c2c85a83d5611ee53b`;
- frozen API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`; analysis stage SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3`; domain candidate revision 14;
- migration head: `0023_norm_citations`; R-135 defers complete beta gate.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: scripts/recovery/blob_reference_audit.py
- enumerator_owner: W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01
- totality_query: `_CATALOG` SQL in the owned file enumerates every schema-declared Blob column/FK and the audit compares its complete result with `_CATALOG_EXPECTED`; focused catalog missing/extra-column tests refuse.

## Captured premise evidence

- premise: the W58 helpers exist, while the DB audit still pins 0022 and
  migration 0023 adds two Blob references to a verified retrieval set.

### P-01 — existing W58 entry points and new references

- captured_at: 2026-10-16
- command: `git grep -n -E '^def (verify_offline_restore_inputs|collect_offline_restore_evidence|restore_sealed_objects|audit_target_blob_readback|audit_blob_references)|^_HEAD =|set_blob_id text|catalogue_blob_id text' e70c91ef7064c8e36f377bd3995960a0e93acf35 -- scripts/recovery db/migrations/versions/20261016_0023_norm_citations.py`
- captured_output:
  ```text
  e70c91ef7064c8e36f377bd3995960a0e93acf35:db/migrations/versions/20261016_0023_norm_citations.py:147:            set_blob_id text NULL REFERENCES blob (blob_id),
  e70c91ef7064c8e36f377bd3995960a0e93acf35:db/migrations/versions/20261016_0023_norm_citations.py:149:            catalogue_blob_id text NULL REFERENCES blob (blob_id),
  e70c91ef7064c8e36f377bd3995960a0e93acf35:scripts/recovery/blob_reference_audit.py:19:_HEAD = "0022_findings_v2"
  e70c91ef7064c8e36f377bd3995960a0e93acf35:scripts/recovery/blob_reference_audit.py:138:def audit_blob_references(session: Session) -> BlobReferenceAudit:
  e70c91ef7064c8e36f377bd3995960a0e93acf35:scripts/recovery/offline_restore_audit.py:88:def collect_offline_restore_evidence(
  e70c91ef7064c8e36f377bd3995960a0e93acf35:scripts/recovery/offline_restore_preflight.py:81:def verify_offline_restore_inputs(copy_dir: Path, objects_root: Path) -> None:
  e70c91ef7064c8e36f377bd3995960a0e93acf35:scripts/recovery/target_blob_readback.py:66:def audit_target_blob_readback(
  e70c91ef7064c8e36f377bd3995960a0e93acf35:scripts/recovery/target_object_restore.py:166:def restore_sealed_objects(
  ```
- interpretation: the current-head DB audit cannot pass its own version and
  closed catalog checks. Existing helpers are independent and need an owned
  offline coordinator; this evidence does not prove a real restore.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/blob_reference_audit.py`
- `scripts/recovery/isolated_restore_drill.py`
- `tests/integration/recovery/test_blob_reference_audit.py`
- `tests/integration/recovery/test_isolated_restore_drill.py`
- `docs/program/tasks/W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01.md`
- `docs/program/W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, `src/**`, `infra/**`;
- other existing `scripts/recovery/**`, root dependencies/lockfiles,
  composition root, global styles, `docs/program/CURRENT_STATE.md`;
- live stand, actual PostgreSQL/S3 services, origin refs and tags.

## Non-goals

- No production restore runner, source-writer quiescence proof, endpoint
  authentication, DB fingerprint implementation, RPO claim or B6 acceptance.
- The caller owns an isolated empty PostgreSQL target, matching isolated S3
  client/BlobStore bucket, a frozen private copy and a verified DB restore.
- Do not change policy for nonavailable Blobs or undeclared references.

## Deliverables

- 0023-compatible SELECT-only Blob reference audit, offline orchestration,
  focused tests and result report.

## Required tests

- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.venv/bin/python -m pytest tests/integration/recovery/test_blob_reference_audit.py tests/integration/recovery/test_isolated_restore_drill.py -q -p no:cacheprovider` — pass.
- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.venv/bin/python -m pytest tests/integration/recovery -q -p no:cacheprovider` — pass.
- Python compile, task governance, `git diff --check`, exact-path containment.
- Real PostgreSQL/S3 drill and full gate deferred by active resource lane and R-135.

## Integration contract

`run_isolated_restore_drill` receives a frozen private copy, an operator-owned
restore callback that restores `db.dump` into a fresh isolated PostgreSQL and
yields a stable read-only Session, and two views of the same isolated S3 bucket
(low-level object client and public BlobStore). It refuses bad local inputs
before calling restore; collects restored DB and mirror evidence before any
target writes; copies the entire sealed mirror with conditional writes and
complete readback; reads every available DB Blob from target; rechecks local
inputs before returning counts and digests. Lower-level refusal types propagate.
The callback/target isolation and stand fingerprint remain independently
owned operator prerequisites; a fake callback is not a recovery verdict.

## Failure/idempotency/security cases

- Invalid copy or DB reference prevents target write. A partial target upload
  may be retried only after existing exact bytes and key set are verified.
- Missing or changed target Blob, extra target key, wrong verified retrieval-set
  set/catalogue Blob, or local drift prevents return. A retry never overwrites.
- There is no DB/S3 dual write from the application or source stand.

## Rollback / feature flag

The helper is unactivated and changes no serving behavior. Revert this task's
six paths; no feature flag is needed.

## Handoff

- changed files: six allowed paths;
- commands/results: result report;
- known limits: no real PostgreSQL/S3 drill or isolation proof;
- integration notes: leave unactivated until a separately owned real lane.
