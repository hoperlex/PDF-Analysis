# Task W56A-INT-RECORDING-MODEL-BIND-01 — bind replay model identity

task_id: W56A-INT-RECORDING-MODEL-BIND-01

## Outcome

`RecordedAdapter` refuses a file whose declared `model_id` differs from the
request model before yielding a response. The refusal uses the existing
nonretryable recorded-input error class and exposes no path or payload.

## Depends on

- `W56A-INT-AR-V2-RECORDED-REQUEST-01` — completed keyed offline request;
- `CFB-INT-AR-V2-PROFILE-06` — completed recorded profile registration.

## Frozen inputs

- base commit and `origin/dev`: `aa1ac421d3abfc029d29e2fcc1c031bdcc9d542f`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `tests/integration/analysis_text/test_provider_modes.py`
- enumerator_owner: `W56A-INT-RECORDING-MODEL-BIND-01`
- totality_query: `sed -n '245,305p' tests/integration/analysis_text/test_provider_modes.py`

## Captured premise evidence

- premise: the replay checksum is checked but a forged recording can declare
  a different model while retaining the request checksum.

### P-01 — missing model comparison

- captured_at: 2026-10-15
- command: `rg -n 'request_sha256|model_id|_response_from' src/auditmanager/analysis/text/recorded.py`
- captured_output:
  ```text
  76:        "request_sha256": request.request_sha256,
  77:        "model_id": request.model_id,
  125:        return self._response_from(json.loads(raw), expected_key=key)
  127:    def _response_from(
  132:        if document.get("request_sha256") != expected_key:
  ```
- interpretation: file creation records the model, but replay does not verify
  it against the request; this is an input-integrity defect.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/recorded.py`
- `tests/integration/analysis_text/test_provider_modes.py`
- `docs/program/tasks/W56A-INT-RECORDING-MODEL-BIND-01.md`
- `docs/program/W56A-INT-RECORDING-MODEL-BIND-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, root dependency/lock files,
composition root, global styles, live adapter, run executor, historical
recordings, corpus, `CURRENT_STATE.md`, refs and tags.

## Non-goals

No live model pin/price, recording rewrite, provider call, v2 executor switch,
DB acceptance, full gate or beta verdict.

## Deliverables

Model-bound replay refusal, focused characterization, task and result report.

## Required tests

- focused recorded adapter and request tests;
- Python compilation, direct governance, frozen hashes, whitespace and exact
  owned-path proof;
- full `make gate` deferred under R-135.

## Integration contract

The adapter compares `recording.model_id` with `request.model_id` after the
request checksum check and before creating `ModelResponse`. Mismatch uses
`analysis_input_invalid` with a `recording_*` reason; no retry or live
fallback. Existing v1 recordings remain byte-identical and accepted.

## Failure/idempotency/security cases

Missing, nonstring or different model identity fails closed. Replays remain
deterministic and read-only; the error envelope carries neither file path
nor prompt body.

## Rollback / feature flag

Revert the adapter guard before activation. No flag, migration or data
rollback is needed.
