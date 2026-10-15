# Task CFB-INT-RECORDED-AND-NORM-04 — integrate recorded and normative adapters

task_id: CFB-INT-RECORDED-AND-NORM-04

## Outcome

`origin/dev` contains a recorded-only AR v2 response-to-publication chain,
an offline seeded evaluation bridge, a byte-pinned W57b catalogue adapter
and an XLSX read adapter over the current findings schema. Current state
records remaining migration, custody and runtime limits.

## Depends on

- `CFB-INT-PUBLICATION-AND-XLSX-03` — completed at `9e3ec73e`;
- `W56A-INT-RECORDED-V2-CHAIN-PREP-01` — completed focused chain;
- `W56A-INT-EVALUATION-BRIDGE-PREP-01` — completed offline bridge;
- `W57B-INT-CATALOGUE-QUERY-PREP-01` — completed byte adapter;
- `W57B-INT-XLSX-READ-PREP-01` — completed read adapter.

## Frozen inputs

- base commit and `origin/dev`: `9e3ec73e3be2ba3326380ca2c8e77bda6ad1bb7d`;
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
- enumerator_path: `src/auditmanager/analysis/public.py`
- enumerator_owner: `W56A-INT-RECORDED-V2-CHAIN-PREP-01`
- totality_query: `sed -n '80,170p' src/auditmanager/analysis/public.py`

## Captured premise evidence

- premise: four scoped slices are present and pass together on the same dev base.

### P-01 — exact base and focused suite

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && ../../../.venv/bin/python -m pytest -q -p no:cacheprovider <eleven focused modules>`
- captured_output:
  ```text
  9e3ec73e3be2ba3326380ca2c8e77bda6ad1bb7d
  9e3ec73e3be2ba3326380ca2c8e77bda6ad1bb7d
  116 passed in 0.34s
  ```
- interpretation: the four slices can be integrated without runtime activation.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/public.py`
- `docs/program/W56A-INT-EVALUATION-BRIDGE-PREP-01.md`
- `docs/program/W56A-INT-RECORDED-V2-CHAIN-PREP-01.md`
- `docs/program/W57B-INT-CATALOGUE-QUERY-PREP-01.md`
- `docs/program/W57B-INT-XLSX-READ-PREP-01.md`
- `docs/program/tasks/W56A-INT-EVALUATION-BRIDGE-PREP-01.md`
- `docs/program/tasks/W56A-INT-RECORDED-V2-CHAIN-PREP-01.md`
- `docs/program/tasks/W57B-INT-CATALOGUE-QUERY-PREP-01.md`
- `docs/program/tasks/W57B-INT-XLSX-READ-PREP-01.md`
- `src/auditmanager/exports/xlsx/query.py`
- `src/auditmanager/findings/v2_recorded.py`
- `src/auditmanager/norms/references/catalogue_query.py`
- `tests/contract/evaluation/test_bridge.py`
- `tests/integration/exports/test_xlsx_read_query.py`
- `tests/integration/findings/test_v2_recorded_chain.py`
- `tests/integration/norms/references/test_catalogue_query.py`
- `tools/evaluation/bridge.py`
- `docs/program/tasks/CFB-INT-RECORDED-AND-NORM-04.md`
- `docs/program/CFB-INT-RECORDED-AND-NORM-04.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, root dependency/lock files,
composition root, global styles, existing v1 publisher, run executor,
historical fixtures, corpus source/promotion, stand, `VERSION`, tags and
`origin/main`.

## Non-goals

No 0023 seal, verified set/custody, provider activation, run-executor wiring,
XLSX API, spreadsheet opening, complete gate, deployment or beta verdict.

## Deliverables

Four scoped slices and reports, this task/report, current state and exact
development-ref readback.

## Required tests

- focused no-DB recorded chain, offline matcher, catalogue and XLSX tests;
- Python compilation, direct governance, frozen hashes, whitespace and exact
  changed-path checks;
- record DB and corpus resource limits; full `make gate` deferred under R-135.

## Integration contract

Stage only listed paths. Recheck remote `origin/dev`, commit the checked
candidate, prove fast-forward of the exact remote SHA, push only that commit
to `origin/dev`, then read back both refs. Neither integration status nor
focused checks authorize `origin/main`. Later tasks must authenticate the
W57a verified set/custody, build the real AR v2 recorded baseline, connect
the run executor and XLSX API under their own grants.

## Failure/idempotency/security cases

Unexpected paths, changed frozen hashes, moved remote ref, non-fast-forward
or focused failure stop publication. Recorded chain refuses live context;
catalogue adapter cannot authenticate caller-supplied expected facts;
XLSX read requires explicit source labels/citations and caller authorization.

## Rollback / feature flag

Revert this development commit before activation. No migration or flag is
introduced by these preparations.
