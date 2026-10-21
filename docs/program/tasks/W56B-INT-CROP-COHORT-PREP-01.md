# Task W56B-INT-CROP-COHORT-PREP-01 — complete image-crop cohort preflight

task_id: W56B-INT-CROP-COHORT-PREP-01

## Outcome

A pure W56b input selector accepts W55b's two saved geometry documents only
when every geometry-checked IMAGE block has exactly one matching PNG crop and
no other crop is present. It returns an immutable, deterministic cohort of
crop references plus an explicit list of IMAGE blocks skipped for page geometry
mismatch. A missing or phantom crop refuses the whole cohort before any model
call could start.

## Depends on

- `W55B-GEOMETRY-01` — completed portal block and crop producers.

## Frozen inputs

- base commit: `f468d20eaf46dba82908615b04f20090541b21df`;
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

- premise: W55b already emits `geometry.portal_blocks` and
  `geometry.page_crops`, but W56b has no analysis-side complete-crop preflight;
  code-first scope permits neutral evidence primitives before vision and
  budget decisions.

### P-01 — existing geometry files at exact base

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only f468d20eaf46dba82908615b04f20090541b21df src/auditmanager/analysis/geometry`
- captured_output:
  ```text
  src/auditmanager/analysis/geometry/__init__.py
  src/auditmanager/analysis/geometry/crops.py
  src/auditmanager/analysis/geometry/maths.py
  src/auditmanager/analysis/geometry/portal.py
  src/auditmanager/analysis/geometry/render.py
  src/auditmanager/analysis/geometry/source_file.py
  ```
- interpretation: this task adds one selector without changing any producer
  or image renderer. The listing alone does not prove runtime readiness.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/geometry/crop_cohort.py`
- `tests/integration/analysis/geometry/test_crop_cohort.py`
- `docs/program/tasks/W56B-INT-CROP-COHORT-PREP-01.md`
- `docs/program/W56B-INT-CROP-COHORT-PREP-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, existing geometry/recognised producers,
W57a API adapter/stage/composition, W54/W58 files, root dependencies/locks,
global styles, API routes, UI, run executor, `CURRENT_STATE.md`, remote refs
and tags.

## Non-goals

No provider/vision call or model budget, crop bytes read, stage activation,
finding or citation, status of skipped blocks as a reviewer decision,
storage write, contract, migration, full gate or beta acceptance.

## Deliverables

One additive pure selector, focused offline tests and this paired report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/geometry/test_crop_cohort.py` — pass;
- Python compilation, direct task governance, frozen-input readback,
  `git diff --check` and exact changed-path proof — pass;
- no Docker/PG/S3/full suite while W55b gate owns the host.

## Integration contract

The future W56b stage can use the complete cohort only after reading both
documents through checksum-verified saved artifact references from the same
Run and verifying each named `geometry.crop_image` Blob against the manifest
before sending image bytes. This selector does not prove Blob custody or
authorize partial analysis when any expected crop is missing.

## Failure/idempotency/security cases

Wrong version/role/schema, duplicate block/crop, a crop for TEXT or a
geometry-mismatch IMAGE, missing checked crop, wrong page or box, malformed
Blob/digest/size/render profile and page/block verdict disagreement refuse.
Repeated input produces an equal immutable result without I/O.

## Rollback / feature flag

Remove the additive module/test before wiring; no data rollback or feature
flag is needed.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: W56b seal owner binds saved artifact/Blob custody and the approved
  provider/budget policy after W57b and the vision probe.
