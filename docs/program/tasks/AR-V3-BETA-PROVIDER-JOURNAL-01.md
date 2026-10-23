# Task AR-V3-BETA-PROVIDER-JOURNAL-01 — v3 provider call journal

## Outcome
One current AR v3 group member can send its sealed request through a bound model adapter; the committed effect and canonical call record bind the candidate SHA, exact provider-body SHA, response SHA, model, transport revision, usage and reported cost. Refusals preserve an honest effect state.

## Depends on
- `AR-V3-BETA-EXECUTE-GUARD-01`
- `AR-V3-BETA-EXECUTE-PREFLIGHT-01`
- `AR-V3-BETA-REQUEST-CUSTODY-01`
- `AR-V3-BETA-SAVED-SOURCE-01`
- `AR-V3-BETA-REQUEST-DELIVERY-01`

## Frozen inputs
- domain contract: `contracts/domain/v1`, unchanged
- API contract: `contracts/api/v1`, unchanged
- analysis/comparison/event contract: `contracts/analysis/v1`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `4c47dbbdcf3c02e13b7e637ed4d486b0dd914410`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the active v3 executor guard remains in place
### P-01 — the active v3 guard precedes any Job or provider effect
- captured_at: 2026-10-23
- command: `rg -n 'the pinned AR v3 beta executor is not installed' src/auditmanager/runs/executor.py`
- captured_output:
  ```text
873:            message="the pinned AR v3 beta executor is not installed",
  ```
- interpretation: served v3 remains disabled while this task builds its provider-call seam.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/v3_provider_call.py`
- `tests/integration/runs/test_v3_provider_call.py`
- `docs/program/tasks/AR-V3-BETA-PROVIDER-JOURNAL-01.md`
- `docs/program/AR-V3-BETA-PROVIDER-JOURNAL-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies and lock files
- composition root, active executor and provider transport implementations
- `src/auditmanager/analysis/profiles/ar_v3/norm_map/**` and normative corpus data
- global styles and API schemas

## Non-goals
- Installing or signing six normative maps/sets.
- Enabling the served v3 executor, CITE publication or numerical findings.
- Persisting raw provider answer text before the CITE artifact owner defines its role and binding.

## Deliverables
- A provider-call operation with durable prepare/response/complete boundaries, current Attempt and set rechecks, and transport identity checks.
- Focused recorded/live transport and failure-order tests; result note.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_provider_call.py tests/integration/runs/test_v3_execution_request.py -x --tb=short`
- expected: all passed, plus `git diff --check` and exact allowlist.

## Integration contract
Call this operation only after the Run, Job and Attempt are committed and a reviewed `TrustedPackRegistry` is installed. It builds the request from saved source and verified set bytes. It commits intent before dispatch, records the answer before any downstream interpretation, checks current Attempt and unchanged group/set pins after the answer, and returns untrusted response text to the CITE owner. A completed call cannot be issued again for the same Run.

## Failure/idempotency/security cases
- No pack, wrong mode, missing model pin or changed group/set refuses before dispatch.
- Proven pre-send refusal is `not_processed`; an uncertain live failure is `outcome_unknown`; a received unusable reply is `response_received` or completed as failed.
- The journal stores hashes and usage, never prompt text, answer text or credentials.
- No automatic retry after an answer or uncertain live dispatch.

## Rollback / feature flag
The active executor guard is the feature gate. Reverting this unserved operation is sufficient while no CITE stage or reviewed pack exists.

## Handoff
- changed files: to be recorded in the result note
- commands/results: to be recorded in the result note
- known limits: no served v3 stage or raw-answer artifact
- integration notes: CITE owns response artifact and stage publication
