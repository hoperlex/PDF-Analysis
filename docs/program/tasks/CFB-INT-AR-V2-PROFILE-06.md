# Task CFB-INT-AR-V2-PROFILE-06 — integrate recorded profile registration

task_id: CFB-INT-AR-V2-PROFILE-06

## Outcome

`origin/dev` contains a content-bound recorded AR v2 profile descriptor and
an executor preflight that resolves it before checking persisted run identity.

## Depends on

- `CFB-INT-PIPELINES-AND-PREFLIGHT-05` — completed at `697279fa`;
- `W56A-INT-AR-V2-RECORDED-PROFILE-01` — completed descriptor;
- `W56A-INT-RECORDED-PREFLIGHT-BIND-01` — completed bound preflight.

## Frozen inputs

- base commit and `origin/dev`: `697279facee30216871389cc783e68b3bc58243b`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- stage registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`; `origin/main=23fd729dbb06c642be0588017f6b195305e2e53e` is outside this task.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/analysis/public.py`
- enumerator_owner: `W56A-INT-RECORDED-PREFLIGHT-BIND-01`
- totality_query: `sed -n '85,175p' src/auditmanager/analysis/public.py`

## Captured premise evidence

- premise: the additive descriptor and public preflight binding pass together
  on the exact dev base without changing the active executor path.

### P-01 — exact base and focused tests

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && ../../../.venv/bin/python -m pytest -q -p no:cacheprovider <three focused modules>`
- captured_output:
  ```text
  697279facee30216871389cc783e68b3bc58243b
  697279facee30216871389cc783e68b3bc58243b
  25 passed, 5 warnings in 0.33s
  ```
- interpretation: content pin and refusal tests pass; warnings concern stale
  `/tmp/pytest-of-root` cleanup, not a product failure.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/executor.py`
- `tests/integration/runs/test_v2_recorded_executor.py`
- `docs/program/tasks/W56A-INT-RECORDED-PREFLIGHT-BIND-01.md`
- `docs/program/W56A-INT-RECORDED-PREFLIGHT-BIND-01.md`
- `src/auditmanager/analysis/profiles/ar_v2/registered.py`
- `tests/integration/analysis/test_ar_v2_registered_profile.py`
- `docs/program/tasks/W56A-INT-AR-V2-RECORDED-PROFILE-01.md`
- `docs/program/W56A-INT-AR-V2-RECORDED-PROFILE-01.md`
- `docs/program/tasks/CFB-INT-AR-V2-PROFILE-06.md`
- `docs/program/CFB-INT-AR-V2-PROFILE-06.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, root dependency/lock files,
composition root, global styles, v1 publication, provider adapter,
historical recordings, corpus source/promotion, stand, `VERSION`, tags and
`origin/main`.

## Non-goals

No live model identity/price, v2 request checksum/recording, executor switch,
DB acceptance, complete gate, deployment or beta verdict.

## Deliverables

Two scoped slices and reports, this task/report, current state and exact
development-ref readback.

## Required tests

- focused descriptor/preflight/recorded-chain tests;
- Python compilation, direct governance, frozen hashes, whitespace and exact
  changed-path proof;
- full `make gate` deferred under R-135.

## Integration contract

Stage only listed paths. Recheck remote `origin/dev`, commit the checked
candidate, prove fast-forward of the exact remote SHA, push only that commit
to `origin/dev`, then read back both refs. Neither integration status nor
focused checks authorize `origin/main`. Future owner must build the recorded
v2 request/artifact/stage path and connect it transactionally.

## Failure/idempotency/security cases

Unexpected paths, changed frozen hashes, moved remote ref, non-fast-forward
or focused failure stop publication. Unknown IDs or content drift fail closed;
the preflight remains uncalled by active `execute_run`.

## Rollback / feature flag

Revert this development commit before activation. No migration or flag is
introduced by these preparations.
