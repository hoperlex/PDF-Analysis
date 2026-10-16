# Task CFB-INT-DEV-PUBLISH-29 — integrate W56b complete crop cohort

task_id: CFB-INT-DEV-PUBLISH-29

## Outcome

A clean fast-forward `origin/dev` candidate carries the pure unserved W56b
preflight that requires a complete, unique crop set for every checked IMAGE
block and explicitly reports geometry-mismatch skips. No Blob read or
provider call is activated.

## Depends on

- `CFB-INT-DEV-PUBLISH-28` — complete at
  `f468d20eaf46dba82908615b04f20090541b21df`;
- `W56B-INT-CROP-COHORT-PREP-01` — complete at
  `81ca174112dc1d8d97e9b8e3c0a1da0c9d2c6518`.

## Frozen inputs

- integration base and directly read `origin/dev`:
  `f468d20eaf46dba82908615b04f20090541b21df`;
- directly read `origin/main`: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- source parent equals integration base; source commit
  `81ca174112dc1d8d97e9b8e3c0a1da0c9d2c6518`, exact four-path
  additive diff, 19 focused offline tests;
- API 48 paths / 55 operations / 131 schemas, SHA-256
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
  stage SHA-256
  `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
  domain IDs SHA-256
  `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`,
  error catalogue SHA-256
  `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`,
  migration head `0023_norm_citations`;
- R-135 defers complete beta gate; W55b release gate is separate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W55b saved geometry documents contain IMAGE blocks and crop
  records, but no analysis-side complete-cohort preflight exists.

### P-01 — source path scope

- captured_at: 2026-10-16
- command: `git show --format= --name-only 81ca174112dc1d8d97e9b8e3c0a1da0c9d2c6518`
- captured_output:
  ```text
  docs/program/W56B-INT-CROP-COHORT-PREP-01.md
  docs/program/tasks/W56B-INT-CROP-COHORT-PREP-01.md
  src/auditmanager/analysis/geometry/crop_cohort.py
  tests/integration/analysis/geometry/test_crop_cohort.py
  ```
- interpretation: accept exact source bytes without changing geometry
  producers, storage or stage contracts.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W56B-INT-CROP-COHORT-PREP-01.md`;
- `docs/program/tasks/W56B-INT-CROP-COHORT-PREP-01.md`;
- `src/auditmanager/analysis/geometry/crop_cohort.py`;
- `tests/integration/analysis/geometry/test_crop_cohort.py`;
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-29.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-29.md`;
- `docs/program/CURRENT_STATE.md`;
- ignored `.venv` link to the existing Python environment for focused tests.

## Forbidden hotspots

All other paths, especially `contracts/**`, migrations, root dependencies
and locks, composition root, existing geometry/recognised producers,
global styles, production DB/S3, `origin/main`, tags and deployment
workflow.

## Non-goals

No same-run saved-artifact proof, crop Blob readback, provider choice or
budget, executable W56b stage, finding/citation, corpus publication,
W55b deployment or beta acceptance.

## Deliverables

Exact four-path source payload, bounded current-state update, this
task/report and direct published-dev SHA readback.

## Required tests

- source 19 focused tests; integrated geometry-focused and programme
  checks, direct task governance;
- exact patch/path and frozen contract checks, whitespace, clean-tree,
  fresh remote fast-forward and post-push readback;
- complete W56–W63 beta gate deferred by R-135; W55b gate separate.

## Integration contract

Cherry-pick exact source commit. A future W56b stage can consume the cohort
only after same-run checksum-verified saved artifact reads and each named
crop Blob's byte verification. Missing or phantom crop refuses the whole
cohort. A moved ref or changed source stops publication; never force-push.

## Failure/idempotency/security cases

Wrong version, duplicate/phantom/missing crop, wrong page/region/Blob/profile
or page/block geometry disagreement refuses; geometry-mismatch blocks are
explicit skips. Repeated valid input yields the same immutable projection
with no I/O.

## Rollback / feature flag

No served behavior is wired. Revert the four source paths and these three
integration documents through a reviewed forward commit if abandoned.

## Handoff

- source files: exact four W56b task paths;
- integration files: this task, report and bounded state update;
- contracts: none; W56b provider and artifact custody remain open;
- forbidden hotspots and `origin/main` remain untouched.
