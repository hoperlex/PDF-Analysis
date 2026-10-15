# Task W56A-INT-RECORDED-RESPONSE-BRIDGE-01 — bind offline replay to AR v2 response finish

task_id: W56A-INT-RECORDED-RESPONSE-BRIDGE-01

## Outcome

One verified recorded AR v2 input and one explicit offline adapter yield a
typed result carrying exact request, source-binding and response checksums,
plus the existing PDF-grounding diagnostics and dense merge preparation.
Wrong request, model, source binding or adapter mode is refused before replay.

## Depends on

- `W56A-INT-AR-V2-RECORDED-INPUT-01` — completed verified source binder;
- `W56A-INT-RESPONSE-PIPELINE-PREP-01` — completed pure finish step;
- `W56A-INT-RECORDING-MODEL-BIND-01` — completed recorded model check.

## Frozen inputs

- captured base commit: `0cbbb72560ee02d45b4f0fc2fa1f7902b365f09f`;
- source branch: `integration/code-first-entry`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`; `P02_SEAMS.md` §§4.3, 4.8 and R-133/R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the verified input binder, concrete recorded adapter and pure
  response finisher exist separately; no exact-identity bridge joins them.

### P-01 — four new task paths absent on the captured base

- captured_at: 2026-10-15
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2/recorded_response.py tests/integration/analysis/test_ar_v2_recorded_response.py docs/program/tasks/W56A-INT-RECORDED-RESPONSE-BRIDGE-01.md docs/program/W56A-INT-RECORDED-RESPONSE-BRIDGE-01.md`
- captured_output:
  ```text
  0cbbb72560ee02d45b4f0fc2fa1f7902b365f09f
  ```
- interpretation: these four additive paths were absent; existing lower-level
  seams do not themselves check the caller's saved request/source identities.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/recorded_response.py`
- `tests/integration/analysis/test_ar_v2_recorded_response.py`
- `docs/program/tasks/W56A-INT-RECORDED-RESPONSE-BRIDGE-01.md`
- `docs/program/W56A-INT-RECORDED-RESPONSE-BRIDGE-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, existing adapter/binder/finish
modules, public boundary, run executor and repository, call journal, StageResult,
finding publisher, recordings, corpus, root dependency/lock files, composition
root, global styles, `CURRENT_STATE.md`, refs, tags and deployment state.

## Non-goals

No DB/Blob read, recording creation, provider call, live adapter, run state,
call journal, stage artifact, finding write, block-index binding, model/price
pin, full gate or beta claim. The caller must supply independently saved
request/model/source-binding identities; this seam cannot authenticate them.

## Deliverables

Additive recorded response bridge, focused tests and task result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/test_ar_v2_recorded_response.py` — pass;
- Python compilation, direct task governance, frozen-hash check,
  `git diff --check` and exact owned-path proof — pass;
- complete `make gate` deferred under R-135.

## Integration contract

The later recorded executor obtains a `RecordedV2Input` from the saved-run
reader and separately saved expected request/model/source-binding values.
`replay_recorded_response` requires the concrete `RecordedAdapter` in recorded
mode, compares all identities before its single `complete` call, then invokes
`finish_response` with the bound PDF layer and marked OCR. It returns immutable
typed checksums and the full grounding/merge result. The adapter independently
checks the recording's declared request and model. No publication follows.

## Failure/idempotency/security cases

Wrong adapter or mode, model, request or source binding fails before reading a
recording. Missing or mismatched recording propagates the existing typed
`analysis_input_invalid` refusal. Invalid response propagates parser refusal;
no partial result is emitted. Equal fixture and sources return equal digests.
No live fallback exists here. OCR stays non-citable.

## Rollback / feature flag

Remove the additive module before executor wiring. No runtime behavior or data
migration is active, so no feature flag is needed.

## Handoff

- changed files/checks/limits: accompanying report;
- contracts: none;
- next: an owned executor task must persist one call attempt with all three
  digests, diagnostic/stage artifacts and durable idempotency before activation.
