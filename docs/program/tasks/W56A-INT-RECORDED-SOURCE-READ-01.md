# Task W56A-INT-RECORDED-SOURCE-READ-01 — read durable AR v2 request sources

task_id: W56A-INT-RECORDED-SOURCE-READ-01

## Outcome

A recorded-only run service reads the persisted run, immutable version and
`source_preparation` stage result, verifies its published text-layer and OCR Blob
bytes, and returns one bound AR v2 request. A fake repository/Blob test proves
the read order and refusal paths without changing the active v1 executor.

## Depends on

- `W56A-INT-AR-V2-RECORDED-INPUT-01` — completed binder at `b236b6bc`;
- `W56A-INT-RECORDED-PREFLIGHT-BIND-01` — completed pinned run preflight;
- `W56A-INT-AR-V2-RECORDED-PROFILE-01` — completed registration.

## Frozen inputs

- base commit: `0c9f2d644a5a89c930ee61ff6e14ae3d8e9733e4`
- source branch: `integration/code-first-entry`
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`
- stage registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only)
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/analysis/public.py`
- enumerator_owner: `W56A-INT-RECORDED-SOURCE-READ-01`
- totality_query: `sed -n '1,200p' src/auditmanager/analysis/public.py`

## Captured premise evidence

- premise: the recorded input binder is pure, while the executor has no
  recorded v2 reader for persisted stage references and Blob bytes.

### P-01 — exact base and new paths

- captured_at: 2026-10-15
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/runs/recorded_v2_sources.py tests/integration/runs/test_recorded_v2_sources.py docs/program/tasks/W56A-INT-RECORDED-SOURCE-READ-01.md docs/program/W56A-INT-RECORDED-SOURCE-READ-01.md`
- captured_output:
  ```text
  0c9f2d644a5a89c930ee61ff6e14ae3d8e9733e4
  ```
- interpretation: the four additive paths are absent; the existing public
  analysis boundary alone needs narrowly scoped exports.

### P-02 — runtime is still v1

- captured_at: 2026-10-15
- command: `rg -n 'profile=AR_TEXT_PROFILE|required_stages=PC01_STAGES|publish_gate_result\(' src/auditmanager/runs/executor.py`
- captured_output:
  ```text
  592:            profile=AR_TEXT_PROFILE,
  702:    publication = publish_gate_result(
  1014:            required_stages=PC01_STAGES,
  ```
- interpretation: a read-only source seam can be added; no recorded v2
  execution or publication is active.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/runs/recorded_v2_sources.py`
- `src/auditmanager/analysis/public.py`
- `tests/integration/runs/test_recorded_v2_sources.py`
- `docs/program/tasks/W56A-INT-RECORDED-SOURCE-READ-01.md`
- `docs/program/W56A-INT-RECORDED-SOURCE-READ-01.md`

## Forbidden hotspots

`contracts/**`, migration head, provider lock, active executor/repository,
findings publisher, recordings, corpus, root dependency/lock files,
composition root, global styles, `CURRENT_STATE.md`, Git refs and deployment
state. The public-boundary grant is limited to imports and `__all__` exports for
the existing recorded input binder; no other symbol or behaviour changes.

## Non-goals

No provider replay or call journal, StageResult, finding write, run transition,
runtime route switch, model/price pin, recorded baseline, full gate or beta
claim. The caller still owns execution authority and terminal selection.

## Deliverables

Read-only run service, focused fake repository/Blob tests, narrow public
exports, task and result report.

## Required tests

- `.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_recorded_v2_sources.py` when resources allow;
- Python compilation, frozen hashes, direct task governance,
  `git diff --check` and exact changed-path proof;
- PostgreSQL/S3 acceptance and complete `make gate` deferred under R-135.

## Integration contract

`load_recorded_v2_input` takes a caller-owned session, run ID, Blob store,
recorded adapter/config and explicit fixture settings. It resolves the pinned
AR v2 profile independently of the run, checks the saved run, reads its saved
version and the successful `source_preparation` result, requires exactly one
text-layer and the portal-bundle OCR reference when applicable, then calls
`read_artifact` and the existing binder. The output retains request and
source-binding checksums. The function performs DB SELECTs and Blob reads only.

## Failure/idempotency/security cases

Wrong profile/mode/state, version/project mismatch, absent or duplicate stage
references, missing portal OCR, unexpected artifact roles, bad Blob bytes or
changed version identity fail before a request is returned. Repeated reads of
unchanged durable inputs yield identical keys. Nothing calls a provider or
mutates canonical data, so a failed read leaves no partial write.

## Rollback / feature flag

Remove the new reader and three public exports before activation. No behaviour
is active and no migration or feature flag is needed.

## Handoff

- changed files/checks/limits: accompanying report;
- contracts: none;
- next: a separately owned executor task needs recording provenance, stage
  artifact semantics, run-level idempotency and DB-backed acceptance before
  recorded v2 activation.
