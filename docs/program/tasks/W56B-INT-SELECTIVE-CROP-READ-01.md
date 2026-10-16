# Task W56B-INT-SELECTIVE-CROP-READ-01 — one saved IMAGE crop read

task_id: W56B-INT-SELECTIVE-CROP-READ-01

## Outcome

An unserved read checks the complete saved IMAGE crop cohort by metadata, but
opens and decodes only the selected portal block's PNG. The selected bytes are
bound to the Run Version's source manifest and current Attempt in one
caller-owned transaction. A sibling crop is not read merely to select one item.

## Depends on

- `W56B-INT-CROP-COHORT-PREP-01` — completed complete IMAGE metadata plan.
- `W56B-INT-SAVED-CROP-CUSTODY-PREP-01` — completed full supplied-byte check.
- `W56B-INT-RUN-CROP-READ-01` — completed Run/Attempt and Blob read pattern.
- `W56B-INT-CROP-SOURCE-DIGEST-01` — completed Version source-digest guard.
- `CFB-INT-DEV-PUBLISH-64` — completed exact development base.

## Frozen inputs

- base commit: `a09721a5895a0aff93d08f203fe1bedbbffffb8a`
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- crop manifest schema SHA-256: `0a745c5477bf83a4ba1b14de9b42023525b29b862a3b7104e70fed91a63c4968`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- migration head: `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- saved crop verifier SHA-256: `ae463d1df15195e25e7d3c87bca34638399b36924ab46a64ca2dd171260389dc`;
- current crop reader SHA-256: `2c5689c369b572eba2dc28e494d8eb01e1d6f947cd8ba2052662976462f1e261`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: the new metadata check requires the set of distinct saved
  IMAGE Blob references to equal the set of all cohort crop references.

## Captured premise evidence

- premise: the current complete reader must open every crop PNG to return any
  one crop; the code-first boundary permits neutral evidence primitives.

### P-01 — exact source behavior

- captured_at: 2026-10-16
- command: `rg -n 'def check_saved_crop_bytes|expected_payload_ids|for candidate in cohort.crops|def load_saved_image_crops|payloads =|def _source_digest' src/auditmanager/analysis/geometry/saved_crop_custody.py src/auditmanager/runs/geometry_crop_input.py`
- captured_output:
  ```text
  src/auditmanager/runs/geometry_crop_input.py:83:def _source_digest(version: DocumentVersionRecord) -> str:
  src/auditmanager/runs/geometry_crop_input.py:167:def load_saved_image_crops(
  src/auditmanager/runs/geometry_crop_input.py:202:    payloads = {ref.blob_id: _read_exact(blob_store, ref) for ref in refs}
  src/auditmanager/analysis/geometry/saved_crop_custody.py:155:def check_saved_crop_bytes(
  src/auditmanager/analysis/geometry/saved_crop_custody.py:174:    expected_payload_ids = {portal_ref.blob_id, manifest_ref.blob_id} | set(crop_refs)
  src/auditmanager/analysis/geometry/saved_crop_custody.py:175:    if set(supplied_blob_bytes) != expected_payload_ids:
  src/auditmanager/analysis/geometry/saved_crop_custody.py:187:    expected_crop_ids = {candidate.blob.blob_id for candidate in cohort.crops}
  src/auditmanager/analysis/geometry/saved_crop_custody.py:190:        for candidate in cohort.crops
  src/auditmanager/analysis/geometry/saved_crop_custody.py:193:    for candidate in cohort.crops:
  ```
- interpretation: existing complete-crop verification reads all PNGs. It does
  not offer a bounded one-image read and this premise alone proves no DB/S3
  acceptance.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none
- integration grant: direct integrator assignment on 2026-10-16; local source
  commit and handoff only.

## Allowed paths

- `src/auditmanager/analysis/geometry/saved_crop_custody.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/geometry_crop_item_input.py`
- `src/auditmanager/runs/public.py`
- `tests/integration/analysis/geometry/test_saved_crop_item_custody.py`
- `tests/integration/runs/test_geometry_crop_item_input.py`
- `docs/program/tasks/W56B-INT-SELECTIVE-CROP-READ-01.md`
- `docs/program/W56B-INT-SELECTIVE-CROP-READ-01.md`

## Forbidden hotspots

`contracts/**`, migrations, stage registry, existing complete crop reader,
geometry producers, jobs/storage/documents adapters, provider/rate adapters,
API/router/UI, composition root, root dependencies/locks, global styles,
`CURRENT_STATE.md`, remote refs and tags.

## Non-goals

No guarantee that an unread sibling PNG is available or correct, model choice,
request/price budget, provider or effect journal, W56b citation or region
policy, finding publication, served route, contract/migration, qualified
corpus, DB/S3 acceptance, deployment or beta acceptance.

## Deliverables

One two-phase pure metadata/selected-PNG verifier, one unserved Run read
adapter, narrow public exports, focused offline tests and paired report.

## Required tests

- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/geometry/test_saved_crop_item_custody.py tests/integration/runs/test_geometry_crop_item_input.py tests/integration/analysis/geometry/test_saved_crop_custody.py tests/integration/runs/test_geometry_crop_input.py` — pass;
- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/architecture/test_alr05_boundaries.py tests/contract/program/test_wave_governance.py` — pass;
- compile owned Python; frozen SHA-256 readback, `git diff --check`, exact
  eight-path inspection and `scripts/task_handoff.py` — pass;
- no Docker, provider or complete gate under R-135.

## Integration contract

The caller supplies an existing short transaction, current Attempt authority,
portal block ID, BlobStore and explicit positive aggregate metadata and
selected-PNG byte caps. The pure first phase checks exact canonical JSON,
complete IMAGE cohort, every distinct saved crop reference and the selected
block's eligibility. The Run adapter binds the portal digest to the Version
manifest, opens only the chosen PNG, checks exact SHA-256, size, PNG decoding
and dimensions, and repeats Run, Version, StageResult and Attempt fences.
The returned image is read-only input; any later effect needs a fresh gate.

## Failure/idempotency/security cases

Missing/extra/changed saved IMAGE refs, incomplete cohort, unknown or skipped
block, invalid source digest, corrupt selected PNG, stale Attempt or changed
saved rows refuse. Duplicate crop *uses* of one content-addressed PNG share
one saved Blob reference and are valid. Equal inputs return equal values;
unselected PNG bytes are never opened or certified by this read.

## Rollback / feature flag

Revert the eight owned paths before activation. No persisted product data or
served behavior changes; no runtime flag or data rollback applies.

## Handoff

- changed files/checks/limits: paired report;
- contracts: none;
- next: integrate as an unserved evidence primitive, then separately freeze
  the W56b provider, budget, effect and publication policy.
