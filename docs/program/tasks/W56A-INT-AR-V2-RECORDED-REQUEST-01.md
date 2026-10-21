# Task W56A-INT-AR-V2-RECORDED-REQUEST-01 — build an offline AR v2 request

task_id: W56A-INT-AR-V2-RECORDED-REQUEST-01

## Outcome

An exact registered AR v2 profile and bundle, explicit fixture model and
generation settings, PDF text layer and selected marked OCR produce one stable
`ModelRequest` body and SHA-256 key. Changed request inputs change the key;
unknown IDs or modified reviewed material are refused before rendering.

## Depends on

- `W56A-INT-AR-V2-RECORDED-PROFILE-01` — completed registration;
- `W56A-INT-RECORDED-PREFLIGHT-BIND-01` — completed inert preflight;
- `CFB-INT-AR-V2-PROFILE-06` — completed integration at `aa1ac421`.

## Frozen inputs

- base commit and `origin/dev`: `aa1ac421d3abfc029d29e2fcc1c031bdcc9d542f`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- stage registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: registered AR v2 prompt material exists, but no AR v2 request builder exists on the exact base.

### P-01 — request builder path absent

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2/recorded_request.py`
- captured_output:
  ```text
  aa1ac421d3abfc029d29e2fcc1c031bdcc9d542f
  aa1ac421d3abfc029d29e2fcc1c031bdcc9d542f
  ```
- interpretation: the additive request path is absent; the descriptor has no
  model identity or generation settings, so this task must require explicit
  offline inputs and must not infer a live model pin.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/recorded_request.py`
- `tests/integration/analysis/test_ar_v2_recorded_request.py`
- `docs/program/tasks/W56A-INT-AR-V2-RECORDED-REQUEST-01.md`
- `docs/program/W56A-INT-AR-V2-RECORDED-REQUEST-01.md`

## Forbidden hotspots

`contracts/**`, migrations, `P02_LOCK.json`, existing runtime/adapter/profile
modules, recordings, corpus, root dependencies/locks, composition root,
global styles, `CURRENT_STATE.md`, refs and tags.

## Non-goals

No live model identity/price, provider call, runtime stage or executor switch,
recorded baseline, DB, finding publication, full gate or beta verdict.
The `fixture/` model namespace is valid only for offline keyed recordings.

## Deliverables

Pure request builder, strict explicit settings and input validation, focused
checksum/refusal tests, offline adapter-to-response-pipeline check and report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/test_ar_v2_recorded_request.py`;
- Python compilation, direct governance, frozen-hash check, `git diff --check`
  and exact owned-path proof;
- full `make gate` deferred under R-135.

## Integration contract

`build_recorded_request` resolves registered profile/bundle IDs before
rendering; its body matches the existing `ModelRequest`/`RecordedAdapter`
shape. The checksum covers model, explicit generation settings, reviewed
system prompt, response schema, PDF pages and selected OCR. Runtime code must
select OCR from the stored `textless_pages`, verify recorded mode and bind
the request SHA to durable call provenance before invoking the adapter.

## Failure/idempotency/security cases

Wrong IDs, changed reviewed bytes, malformed fixture model/settings/text/OCR
fail closed. Repeated inputs produce equal bodies and keys. No provider, DB,
credential or external side effect is available in this module. A missing
recording remains a typed `recording_missing` refusal, never a live fallback.

## Rollback / feature flag

Remove the additive module before runtime wiring; no feature flag or data
rollback is required. A future live model and parameter pin needs its own
contract and task.

## Handoff

- changed files/checks/limits: task report;
- contracts: none changed;
- next: integrator verifies exact paths and tests, then grants separate
  recording/provenance and executor wiring only after their inputs are pinned.
