# Task W56B-INT-SAVED-CROP-CUSTODY-PREP-01 — check supplied saved crop bytes

task_id: W56B-INT-SAVED-CROP-CUSTODY-PREP-01

## Outcome

A pure, unserved verifier accepts one run-scoped saved geometry-stage snapshot
and its supplied Blob bytes only if the saved artifact references, portal
blocks, complete crop manifest and every PNG agree by role, identity, SHA-256,
size and image dimensions. A missing/corrupt byte payload refuses the whole
input before a future IMAGE model call. This does not claim a real DB/S3 read.

## Depends on

- `W55B-GEOMETRY-01` — completed saved geometry and crop producers.
- `W56B-INT-CROP-COHORT-PREP-01` — completed complete IMAGE-crop selector.

## Frozen inputs

- base commit: `f6f19220fa5ae019daae07a3771846e2523ce55a`;
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- crop-manifest schema SHA-256: `0a745c5477bf83a4ba1b14de9b42023525b29b862a3b7104e70fed91a63c4968`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- migration head: `0023_norm_citations`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `StageResultRow` stores artifact refs without an embedded `run_id`;
  `RunRepository.stage_results(session, run_id)` supplies one run-scoped set.
  W56b has a complete crop cohort but no analysis-side check over saved refs
  and supplied PNG bytes.

### P-01 — exact geometry package at frozen base

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only f6f19220fa5ae019daae07a3771846e2523ce55a src/auditmanager/analysis/geometry`
- captured_output:
  ```text
  src/auditmanager/analysis/geometry/__init__.py
  src/auditmanager/analysis/geometry/crop_cohort.py
  src/auditmanager/analysis/geometry/crops.py
  src/auditmanager/analysis/geometry/maths.py
  src/auditmanager/analysis/geometry/portal.py
  src/auditmanager/analysis/geometry/render.py
  src/auditmanager/analysis/geometry/source_file.py
  ```
- interpretation: this task adds a separate byte verifier; the file list does
  not prove DB provenance or real object-store availability.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/geometry/saved_crop_custody.py`
- `tests/integration/analysis/geometry/test_saved_crop_custody.py`
- `docs/program/tasks/W56B-INT-SAVED-CROP-CUSTODY-PREP-01.md`
- `docs/program/W56B-INT-SAVED-CROP-CUSTODY-PREP-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, existing geometry producers/cohort,
`runs/**`, storage adapters, W57a CITE, W58 recovery, W54 corpus, root
dependencies/locks, composition, API/UI, global styles, `CURRENT_STATE.md`,
remote refs and tags.

## Non-goals

No DB or S3 access, real Blob readback claim, provider/vision call, budget,
stage activation, durable attempt fencing, publication, finding/citation,
contract, migration or full beta acceptance.

## Deliverables

One additive byte verifier, tiny offline tests and this paired report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/geometry/test_saved_crop_custody.py` — pass;
- Python compilation, direct task governance, frozen SHA-256 readback,
  `git diff --check` and exact changed-path proof — pass;
- no Docker/PG/S3/full suite while W55b gate owns the host.

## Integration contract

A future runs owner obtains a `StageResultRow` through a single
`RunRepository.stage_results(session, run_id)` read and wraps its row with that
run ID. A storage owner supplies bytes read from the pinned Blob references.
This verifier checks those supplied values. The adapter must still prove the
Run's immutable version, current Attempt authority, saved publication
bindings, and BlobStore readback before any model call; it must recheck or
fence mutable state after the pure check.

## Failure/idempotency/security cases

Foreign run, wrong stage identity/version/status, duplicate or unexpected
roles/Blob IDs, missing extra or corrupt bytes, mismatched crop references,
invalid PNG or wrong dimensions refuse without a partial result. The input
mapping is not mutated. Repeated valid input returns an equal immutable value.

## Rollback / feature flag

Remove the additive module and test before wiring. No DB rollback or feature
flag is needed.

## Handoff

- changed files/checks/limits: paired report;
- contracts: none;
- next: W56b runs/storage integration after W57b and vision/budget rulings,
  with real DB/S3 acceptance and Attempt fencing.
