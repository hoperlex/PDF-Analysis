# Task CFB-INT-PIPELINES-AND-PREFLIGHT-05 — integrate bounded pipelines

task_id: CFB-INT-PIPELINES-AND-PREFLIGHT-05

## Outcome

`origin/dev` contains a recorded AR v2 executor preflight, one-source W57b
reference pipeline, and caller-authorized XLSX read-to-byte package service.
No runtime activation is implied.

## Depends on

- `CFB-INT-RECORDED-AND-NORM-04` — completed at `e4cf264b`;
- `W56A-INT-RECORDED-EXECUTOR-01` — completed preflight;
- `W57B-INT-REFERENCE-PIPELINE-PREP-01` — completed reference pipeline;
- `W57B-INT-XLSX-PACKAGE-PREP-01` — completed XLSX package service.

## Frozen inputs

- base commit and `origin/dev`: `e4cf264bc71375f85625d9ab3ad110316815d046`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- stage registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`; `origin/main=23fd729dbb06c642be0588017f6b195305e2e53e` is outside this task.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/runs/executor.py`
- enumerator_owner: `W56A-INT-RECORDED-EXECUTOR-01`
- totality_query: `tail -25 src/auditmanager/runs/executor.py`

## Captured premise evidence

- premise: three bounded slices pass on the same dev base and touch disjoint
  code paths, with only the integrator owning current state and ref publication.

### P-01 — exact base and focused suite

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && ../../../.venv/bin/python -m pytest -q -p no:cacheprovider <nine focused modules>`
- captured_output:
  ```text
  e4cf264bc71375f85625d9ab3ad110316815d046
  e4cf264bc71375f85625d9ab3ad110316815d046
  104 passed in 0.26s
  ```
- interpretation: the candidate can be integrated as preparation, without
  provider or W57b contract activation.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/runs/executor.py`
- `docs/program/W56A-INT-RECORDED-EXECUTOR-01.md`
- `docs/program/W57B-INT-REFERENCE-PIPELINE-PREP-01.md`
- `docs/program/W57B-INT-XLSX-PACKAGE-PREP-01.md`
- `docs/program/tasks/W56A-INT-RECORDED-EXECUTOR-01.md`
- `docs/program/tasks/W57B-INT-REFERENCE-PIPELINE-PREP-01.md`
- `docs/program/tasks/W57B-INT-XLSX-PACKAGE-PREP-01.md`
- `src/auditmanager/exports/xlsx/package.py`
- `src/auditmanager/norms/references/pipeline.py`
- `tests/integration/exports/test_xlsx_package.py`
- `tests/integration/norms/references/test_reference_pipeline.py`
- `tests/integration/runs/test_v2_recorded_executor.py`
- `docs/program/tasks/CFB-INT-PIPELINES-AND-PREFLIGHT-05.md`
- `docs/program/CFB-INT-PIPELINES-AND-PREFLIGHT-05.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, root dependency/lock files,
composition root, global styles, existing v1 publication, provider adapter,
historical fixtures, corpus source/promotion, stand, `VERSION`, tags and
`origin/main`.

## Non-goals

No AR v2 runtime switch, W57a `0023` or W57b `0024` seal, verified custody,
XLSX API/role grant, real recorded baseline, complete gate, deployment or
beta verdict.

## Deliverables

Three bounded slices and reports, this task/report, current state and exact
development-ref readback.

## Required tests

- focused no-DB executor, reference and XLSX tests;
- Python compilation, direct governance, frozen hashes, whitespace and exact
  changed-path checks;
- DB, spreadsheet application and full `make gate` deferred under R-135.

## Integration contract

Stage only listed paths. Recheck remote `origin/dev`, commit the checked
candidate, prove fast-forward of the exact remote SHA, push only that commit
to `origin/dev`, then read back both refs. Neither integration status nor
focused checks authorize `origin/main`. Future owners must register the AR v2
profile and recorded request/artifact flow; W57a/W57b owners must seal the
verified set, custody, API, role and citation sources before activating these
pure pipelines.

## Failure/idempotency/security cases

Unexpected paths, changed frozen hashes, moved remote ref, non-fast-forward
or focused failure stop publication. The preflight refuses identity/mode/state
mismatch before effects, but is not yet invoked by `execute_run`. Source refs
and allow decisions are caller claims until authenticated by sealed readers.

## Rollback / feature flag

Revert this development commit before activation. No migration or feature
flag is introduced by these preparations.
