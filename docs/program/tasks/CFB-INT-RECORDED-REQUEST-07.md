# Task CFB-INT-RECORDED-REQUEST-07 — integrate v2 replay request and model guard

task_id: CFB-INT-RECORDED-REQUEST-07

## Outcome

`origin/dev` contains a deterministic offline AR v2 request builder and a
recorded adapter that refuses a recording whose model field differs from the
request. The active executor remains v1.

## Depends on

- `CFB-INT-AR-V2-PROFILE-06` — completed at `aa1ac421`;
- `W56A-INT-AR-V2-RECORDED-REQUEST-01` — completed request builder;
- `W56A-INT-RECORDING-MODEL-BIND-01` — completed model guard.

## Frozen inputs

- base commit and `origin/dev`: `aa1ac421d3abfc029d29e2fcc1c031bdcc9d542f`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- stage registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`; `origin/main=23fd729dbb06c642be0588017f6b195305e2e53e` is outside this task.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `tests/integration/analysis_text/test_provider_modes.py`
- enumerator_owner: `W56A-INT-RECORDING-MODEL-BIND-01`
- totality_query: `sed -n '245,305p' tests/integration/analysis_text/test_provider_modes.py`

## Captured premise evidence

- premise: request/recorded-adapter compatibility passes, and the discovered
  missing model-field comparison has a narrow refusal fix on the same base.

### P-01 — exact base and focused suite

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && ../../../.venv/bin/python -m pytest -q -p no:cacheprovider <three focused modules>`
- captured_output:
  ```text
  aa1ac421d3abfc029d29e2fcc1c031bdcc9d542f
  aa1ac421d3abfc029d29e2fcc1c031bdcc9d542f
  39 passed, 5 warnings in 0.36s
  ```
- interpretation: offline request/replay works and existing v1 recordings
  remain accepted; warnings are stale `/tmp` cleanup.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/recorded_request.py`
- `tests/integration/analysis/test_ar_v2_recorded_request.py`
- `docs/program/tasks/W56A-INT-AR-V2-RECORDED-REQUEST-01.md`
- `docs/program/W56A-INT-AR-V2-RECORDED-REQUEST-01.md`
- `src/auditmanager/analysis/text/recorded.py`
- `tests/integration/analysis_text/test_provider_modes.py`
- `docs/program/tasks/W56A-INT-RECORDING-MODEL-BIND-01.md`
- `docs/program/W56A-INT-RECORDING-MODEL-BIND-01.md`
- `docs/program/tasks/CFB-INT-RECORDED-REQUEST-07.md`
- `docs/program/CFB-INT-RECORDED-REQUEST-07.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, root dependency/lock files,
composition root, global styles, live adapter, run executor, historical
recordings, corpus source/promotion, stand, `VERSION`, tags and `origin/main`.

## Non-goals

No live model identity/price, v2 executor switch, measured baseline,
DB acceptance, complete gate, deployment or beta verdict.

## Deliverables

Two scoped slices and reports, this task/report, current state and exact
development-ref readback.

## Required tests

- focused offline request, adapter and v1 replay tests;
- Python compilation, direct governance, frozen hashes, whitespace and exact
  changed-path proof;
- full `make gate` deferred under R-135.

## Integration contract

Stage only listed paths. Recheck remote `origin/dev`, commit the checked
candidate, prove fast-forward of the exact remote SHA, push only that commit
to `origin/dev`, then read back both refs. Neither integration status nor
focused checks authorize `origin/main`. Future owner must bind this request
and its response to durable v2 stage execution, artifact and run transaction.

## Failure/idempotency/security cases

Unexpected paths, changed frozen hashes, moved remote ref, non-fast-forward
or focused failure stop publication. Request inputs change the checksum;
recording model mismatch fails before response creation with no live fallback.

## Rollback / feature flag

Revert this development commit before activation. No migration or feature
flag is introduced.
