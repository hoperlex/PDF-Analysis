# Task CFB-INT-DEV-PUBLISH-65 — offline custody and boundedness guards

task_id: CFB-INT-DEV-PUBLISH-65

## Outcome

Integrate four reviewed unserved W56a/W56b/W58/W59 source slices on the exact
published dev64 predecessor. Publish the combined, focused-checked candidate
as a fast-forward to `origin/dev` with an exact remote readback.

## Depends on

- `CFB-INT-DEV-PUBLISH-64` — completed at `a09721a5895a0aff93d08f203fe1bedbbffffb8a`.
- `W56A-INT-EVALUATION-RUN-SOURCE-01` — completed source `ed485d1c30f1c1618709d99d1db93cf120fca2cb`.
- `W56B-INT-SELECTIVE-CROP-READ-01` — completed source `d7c9e8d02801102f5b0271ecc554a2d168210fef`.
- `W58-INT-NONBLOCK-MIRROR-01` — completed source `9d01a939cc3d3563d5514300d2f5f962508e732a`.
- `W59-INT-CARRYOVER-BOUNDS-01` — completed source `4a21a675bed82723275aaf1d0600da711eee113d`.

## Frozen inputs

- base commit: `a09721a5895a0aff93d08f203fe1bedbbffffb8a`
- API v1 SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- `VERSION=0.6.0`; `origin/main` and `v0.6.0` remain W55b `37393a979a430e490843d7f410e9eca9491a4ea1`;
- R-135: focused checks for intermediate development candidates, complete beta gate deferred.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: four source commits are based on dev64, have disjoint implementation
  paths and do not change frozen contracts, migration, dependencies or served routes.

### P-01 — exact combined source paths

- captured_at: 2026-10-16
- command: `git diff --name-only a09721a5895a0aff93d08f203fe1bedbbffffb8a..92019212`
- captured_output:
  ```text
  docs/program/W56A-INT-EVALUATION-RUN-SOURCE-01.md
  docs/program/W56B-INT-SELECTIVE-CROP-READ-01.md
  docs/program/W58-INT-NONBLOCK-MIRROR-01.md
  docs/program/W59-INT-CARRYOVER-BOUNDS-01.md
  docs/program/tasks/W56A-INT-EVALUATION-RUN-SOURCE-01.md
  docs/program/tasks/W56B-INT-SELECTIVE-CROP-READ-01.md
  docs/program/tasks/W58-INT-NONBLOCK-MIRROR-01.md
  docs/program/tasks/W59-INT-CARRYOVER-BOUNDS-01.md
  scripts/recovery/object_copy.py
  scripts/recovery/source_object_mirror.py
  src/auditmanager/analysis/geometry/saved_crop_custody.py
  src/auditmanager/analysis/public.py
  src/auditmanager/comparison/decision_carryover.py
  src/auditmanager/runs/geometry_crop_item_input.py
  src/auditmanager/runs/public.py
  tests/integration/analysis/geometry/test_saved_crop_item_custody.py
  tests/integration/comparison/test_decision_carryover.py
  tests/integration/evaluation/test_run_sources.py
  tests/integration/recovery/test_object_copy.py
  tests/integration/recovery/test_source_object_mirror.py
  tests/integration/runs/test_geometry_crop_item_input.py
  tools/evaluation/run_sources.py
  ```
- interpretation: these 22 paths are the complete source diff before this
  integration task's three documentation paths; no live acceptance follows.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W56A-INT-EVALUATION-RUN-SOURCE-01.md`
- `docs/program/W56B-INT-SELECTIVE-CROP-READ-01.md`
- `docs/program/W58-INT-NONBLOCK-MIRROR-01.md`
- `docs/program/W59-INT-CARRYOVER-BOUNDS-01.md`
- `docs/program/tasks/W56A-INT-EVALUATION-RUN-SOURCE-01.md`
- `docs/program/tasks/W56B-INT-SELECTIVE-CROP-READ-01.md`
- `docs/program/tasks/W58-INT-NONBLOCK-MIRROR-01.md`
- `docs/program/tasks/W59-INT-CARRYOVER-BOUNDS-01.md`
- `scripts/recovery/object_copy.py`
- `scripts/recovery/source_object_mirror.py`
- `src/auditmanager/analysis/geometry/saved_crop_custody.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/comparison/decision_carryover.py`
- `src/auditmanager/runs/geometry_crop_item_input.py`
- `src/auditmanager/runs/public.py`
- `tests/integration/analysis/geometry/test_saved_crop_item_custody.py`
- `tests/integration/comparison/test_decision_carryover.py`
- `tests/integration/evaluation/test_run_sources.py`
- `tests/integration/recovery/test_object_copy.py`
- `tests/integration/recovery/test_source_object_mirror.py`
- `tests/integration/runs/test_geometry_crop_item_input.py`
- `tools/evaluation/run_sources.py`
- `docs/program/CURRENT_STATE.md`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-65.md`
- `docs/program/CFB-INT-DEV-PUBLISH-65.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root,
global styles, served API/UI, provider, corpus data/DB/S3, deployment workflow,
`origin/main` and tags.

## Non-goals

No qualified W54 corpus, original seeded ZIP saved custody, measured AR v2
baseline, W56b model/citation/effect policy, W59 authoritative carryover
snapshot, W58 live recovery drill, complete beta gate or deployment.

## Deliverables

Four source cherry-picks, first-read state update, this task/report, combined
focused checks, clean-tree handoff, dev fast-forward and exact remote readback.

## Required tests

- Combined recovery, evaluation, crop, comparison, ALR-05, programme
  governance and API documentation facts suites: pass.
- Frozen SHA-256s, owned Python compilation, exact 25-path diff, whitespace,
  clean tree and direct task handoff: pass.
- Fresh remote refs, fast-forward proof, exact-SHA dev push and readback:
  pass. No intermediate full `make gate` under R-135.

## Integration contract

W58 local object readers refuse FIFO paths promptly. W56a's read-only
attestation joins persisted Run/Version to one bounded saved PDF Blob and an
explicit seeded manifest bundle. W56b's current-Attempt reader checks whole
saved crop metadata and source digest but opens one selected PNG. W59's pure
carryover planner bounds offered matches and selected digests to 200. These
functions add no served route or external effect.

## Failure/idempotency/security cases

Stop on dirty tree, changed frozen input, expanded path set, moved dev or
failed check. Never force push. Correct by a separately reviewed forward
commit. Source-task refusal cases are recorded in their paired reports.

## Rollback / feature flag

Unserved, read-only or pure changes. Revert before activation; no data
rollback or runtime flag applies.

## Handoff

- changed files: 25 exact allowed paths;
- contracts: none;
- checks, risks and publication readback: paired report and local evidence;
- forbidden hotspots untouched.
