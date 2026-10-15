# Task CFB-INT-PINS-AND-PLANS-02 — integrate CSV pins and pure publication plans

task_id: CFB-INT-PINS-AND-PLANS-02

## Outcome

`origin/dev` contains the synchronized 19-column CSV seam and executable
structural pins, the pure AR v2 merge-publication planner and pure W57b
newer-edition observation planner. Current state records their limits.

## Depends on

- `W56A-INT-CSV-SEVERITY-01` — completed 19-column implementation at `12916869`;
- `W56A-INT-MERGE-INPUT-PREP-01` — completed merge preparation;
- `W57B-INT-REFERENCE-RESOLUTION-PREP-01` — completed reference resolver;
- `W57B-INT-CATALOGUE-SLUG-AUDIT-01` — completed at `eca8597b`.

## Frozen inputs

- base commit and `origin/dev`: `eca8597b4b59a06371cfaf709df7bee8509a604f`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`; `origin/main=23fd729dbb06c642be0588017f6b195305e2e53e` is outside this task.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: docs/program/P02_SEAMS.md
- enumerator_owner: W56A-INT-CSV-PINS-SYNC-01
- totality_query: `sed -n '760,786p' docs/program/P02_SEAMS.md`

## Captured premise evidence

- premise: the three code-first slices share an exact development base and need one integration owner for current state and development publication.

### P-01 — exact base

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev`
- captured_output:
  ```text
  eca8597b4b59a06371cfaf709df7bee8509a604f
  eca8597b4b59a06371cfaf709df7bee8509a604f
  ```
- interpretation: integration can review one candidate from this base if the remote ref remains unchanged.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`
- `docs/manual-tests/PC-01_prototype.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/program/P02_SEAMS.md`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/exports/query.py`
- `tests/contract/domain_p02/test_seam_register.py`
- `tests/e2e/p02/test_journey.py`
- `tests/e2e/p02/test_journey_figures_pinned.py`
- `tests/e2e/pc01/test_acceptance.py`
- `tests/integration/exports/test_csv_contract.py`
- `tests/integration/exports/test_frozen_column_list.py`
- `tests/integration/p02_journey/test_journey_figures.py`
- `web/src/widgets/export-panel/ui/export-panel.tsx`
- `web/tests/contract/csv-columns.contract.test.ts`
- `web/tests/guards/rendered-language.guard.test.ts`
- `web/tests/unit/export/export-panel.test.ts`
- `docs/program/W56A-INT-CSV-PINS-SYNC-01.md`
- `docs/program/W56A-INT-MERGE-PUBLICATION-PLAN-PREP-01.md`
- `docs/program/W57B-INT-REFERENCE-OBSERVATION-PREP-01.md`
- `docs/program/tasks/W56A-INT-CSV-PINS-SYNC-01.md`
- `docs/program/tasks/W56A-INT-MERGE-PUBLICATION-PLAN-PREP-01.md`
- `docs/program/tasks/W57B-INT-REFERENCE-OBSERVATION-PREP-01.md`
- `src/auditmanager/findings/merge_publication_plan.py`
- `src/auditmanager/norms/references/observation_plan.py`
- `tests/integration/findings/test_merge_publication_plan.py`
- `tests/integration/norms/references/test_observation_plan.py`
- `docs/program/tasks/CFB-INT-PINS-AND-PLANS-02.md`
- `docs/program/CFB-INT-PINS-AND-PLANS-02.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root,
global styles, provider lock, corpus source/promotion, historical
characterization record 12, stand, `VERSION`, tags and `origin/main`.

## Non-goals

No DB activation of AR v2 or W57b, verified corpus set, provider call,
complete gate, deployment or beta acceptance.

## Deliverables

Three task-owned slices and reports, this integration report, current state,
and one exact development commit/ref readback.

## Required tests

- focused no-DB Python tests, compilation and direct governance;
- static 19-column parity, frozen hashes, whitespace and exact-path proof;
- record DB, web and characterization limitations honestly;
- no complete `make gate` under R-135.

## Integration contract

Stage only the listed paths. Recheck remote `origin/dev`, commit the reviewed
candidate, prove it fast-forwards that exact remote SHA, push only the commit
to `origin/dev`, then read back the ref. No `origin/main` update. Later owners
must complete DB and web checks, characterization compatibility, W57b seal and
verified corpus admission before activating or advertising the functionality.

## Failure/idempotency/security cases

Unexpected paths, frozen digest change, moved remote ref, non-fast-forward or
focused test failure stop publication. No source norm text or credential enters
Git. Repeated pure inputs produce identical plans.

## Rollback / feature flag

Revert this development commit before runtime activation; no schema downgrade
or feature flag is needed for the pure plans and CSV pin synchronization.
