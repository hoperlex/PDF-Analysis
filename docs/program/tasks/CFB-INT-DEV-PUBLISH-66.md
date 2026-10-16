# Task CFB-INT-DEV-PUBLISH-66 — bounded offline source and section checks

task_id: CFB-INT-DEV-PUBLISH-66

## Outcome

Integrate four reviewed, unserved W56a/W57b/W58/W59 source slices on the
exact published dev65 predecessor and publish the focused-checked result as
a fast-forward to `origin/dev`, with exact remote readback.

## Depends on

- `CFB-INT-DEV-PUBLISH-65` — completed at `8c39b9e0dfd63da7d32d1a848e609ae2dd437a01`.
- `W56A-INT-EVALUATION-LOCAL-BUNDLE-BIND-01` — completed source `c6d1d07713d58cff0f1933a4a2c4b90941d1e72c`.
- `W57B-INT-REFERENCE-LIST-BOUNDS-01` — completed source `576bdefb78210e8cc252c4809885ba9a74c82fa6`.
- `W58-INT-TARGET-LIST-BOUNDS-01` — completed local source `b8efe199` on this integration branch.
- `W59-INT-SAME-SECTION-PAIR-PREP-01` — completed source `ff33185a0b9366405cfa695379dbfe9ba149129a`.

## Frozen inputs

- base commit: `8c39b9e0dfd63da7d32d1a848e609ae2dd437a01`
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

- premise: the four source slices change disjoint paths, are based on
  published dev65 and leave frozen contracts, migration and served routes
  unchanged.

### P-01 — exact combined source paths

- captured_at: 2026-10-16
- command: `git diff --name-only 8c39b9e0dfd63da7d32d1a848e609ae2dd437a01..29b4ed30`
- captured_output:
  ```text
  docs/program/W56A-INT-EVALUATION-LOCAL-BUNDLE-BIND-01.md
  docs/program/W57B-INT-REFERENCE-LIST-BOUNDS-01.md
  docs/program/W58-INT-TARGET-LIST-BOUNDS-01.md
  docs/program/W59-INT-SAME-SECTION-PAIR-PREP-01.md
  docs/program/tasks/W56A-INT-EVALUATION-LOCAL-BUNDLE-BIND-01.md
  docs/program/tasks/W57B-INT-REFERENCE-LIST-BOUNDS-01.md
  docs/program/tasks/W58-INT-TARGET-LIST-BOUNDS-01.md
  docs/program/tasks/W59-INT-SAME-SECTION-PAIR-PREP-01.md
  scripts/recovery/target_object_restore.py
  src/auditmanager/comparison/version_section_pair.py
  src/auditmanager/runs/reference_pipeline.py
  tests/integration/comparison/test_version_section_pair.py
  tests/integration/evaluation/test_local_bundle.py
  tests/integration/recovery/test_target_object_restore.py
  tests/integration/runs/test_reference_pipeline.py
  tools/evaluation/local_bundle.py
  ```
- interpretation: these 16 paths are the full source diff before this
  integration task's three documentation paths; no live acceptance follows.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W56A-INT-EVALUATION-LOCAL-BUNDLE-BIND-01.md`
- `docs/program/W57B-INT-REFERENCE-LIST-BOUNDS-01.md`
- `docs/program/W58-INT-TARGET-LIST-BOUNDS-01.md`
- `docs/program/W59-INT-SAME-SECTION-PAIR-PREP-01.md`
- `docs/program/tasks/W56A-INT-EVALUATION-LOCAL-BUNDLE-BIND-01.md`
- `docs/program/tasks/W57B-INT-REFERENCE-LIST-BOUNDS-01.md`
- `docs/program/tasks/W58-INT-TARGET-LIST-BOUNDS-01.md`
- `docs/program/tasks/W59-INT-SAME-SECTION-PAIR-PREP-01.md`
- `scripts/recovery/target_object_restore.py`
- `src/auditmanager/comparison/version_section_pair.py`
- `src/auditmanager/runs/reference_pipeline.py`
- `tests/integration/comparison/test_version_section_pair.py`
- `tests/integration/evaluation/test_local_bundle.py`
- `tests/integration/recovery/test_target_object_restore.py`
- `tests/integration/runs/test_reference_pipeline.py`
- `tools/evaluation/local_bundle.py`
- `docs/program/CURRENT_STATE.md`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-66.md`
- `docs/program/CFB-INT-DEV-PUBLISH-66.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root,
global styles, served API/UI, provider, production corpus/DB/S3, deployment
workflow, `origin/main` and tags.

## Non-goals

No qualified W54 corpus, persisted portal ZIP custody, measured AR v2
baseline, reviewed W57b slug source or 0024 seal, W59 persisted section
confirmation or served comparison, W58 live drill, complete beta gate or
deployment.

## Deliverables

Four source commits, first-read state update, this task/report, combined
focused checks, clean-tree handoff, dev fast-forward and exact remote readback.

## Required tests

- Combined recovery, evaluation, references, comparison, sections, ALR-05,
  programme governance and API documentation facts suites: pass. Exclude
  `test_catalogue_input_db_s3_accept.py`, whose required isolated
  `DATABASE_URL`/S3 lane is unavailable; report this limitation explicitly.
- Frozen SHA-256s, owned Python compilation, exact 19-path diff, whitespace,
  clean tree and direct task handoff: pass.
- Fresh remote refs, fast-forward proof, exact-SHA dev push and readback:
  pass. No intermediate full `make gate` under R-135.

## Integration contract

W56a's offline tool binds one saved Run/PDF attestation to all frozen local
seeded PDF/ZIP bytes without claiming persisted ZIP custody. W57b rejects an
oversized or malformed explicit slug list before Blob reads and retains the
verified catalogue as the membership authority. W58 bounds target S3 listing
work by the sealed object count. W59's pure guard checks the same explicit
P/R stage and confirmed section code for a supplied ordered version pair;
future caller still proves saved expert provenance and catalogue membership.
These functions add no served route or external effect.

## Failure/idempotency/security cases

Stop on dirty tree, changed frozen input, expanded paths, moved dev or failed
check. Never force push. Correct by a separately reviewed forward commit.
Source-task refusal cases are recorded in their paired reports.

## Rollback / feature flag

Unserved, read-only or pure changes. Revert before activation; no data
rollback or runtime flag applies.

## Handoff

- changed files: 19 exact allowed paths;
- contracts: none;
- checks, risks and publication readback: paired report and local evidence;
- forbidden hotspots untouched.
