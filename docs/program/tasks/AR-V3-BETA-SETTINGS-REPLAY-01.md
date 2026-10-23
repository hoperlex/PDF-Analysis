# Task AR-V3-BETA-SETTINGS-REPLAY-01 — recover v3 settings from the completed call

## Outcome
CITE rebuilds the exact saved AR v3 provider body after a worker restart using the completed call's validated generation parameters, without relying on the current process settings.

## Depends on
- `AR-V3-BETA-CALL-READ-01`
- `AR-V3-BETA-CITE-LEASE-01`
- `AR-V3-BETA-PROVIDER-LEASE-01`

## Frozen inputs
- domain/API/analysis/events contract: `1.2.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: completed call stores parameter JSON but CITE accepts independent generation settings
### P-01 — replay seam
- captured_at: 2026-10-23
- command: `rg -n 'class V3CompletedCall|effect_params =|settings: V3GenerationSettings|settings=settings' src/auditmanager/jobs/repository.py src/auditmanager/runs/v3_cite_preflight.py src/auditmanager/runs/v3_cite_stage.py`
- captured_output: `V3CompletedCall` has no generation parameters; `completed_v3_call` reads `effect_parameters`; CITE preflight and writer require `settings` from their caller.
- interpretation: saved exact body replay can use only the canonical call/effect parameters after validating the v3 settings shape.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/runs/v3_cite_preflight.py`
- `src/auditmanager/runs/v3_cite_stage.py`
- `tests/integration/jobs/test_v3_completed_call.py`
- `tests/integration/runs/test_v3_cite_preflight.py`
- `tests/integration/runs/test_v3_cite_stage.py`
- `docs/program/tasks/AR-V3-BETA-SETTINGS-REPLAY-01.md`
- `docs/program/AR-V3-BETA-SETTINGS-REPLAY-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lockfiles
- composition root, active executor, provider transports, global styles
- normative maps, source corpus and set data

## Non-goals
- Changing dispatch settings or editing the stored completed call.
- Activating v3 or widening the frozen API StageId enum.

## Deliverables
- Strict completed-call generation parameter witness and CITE replay from it.
- Malformed-settings and changed-call refusal tests; result note.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/jobs/test_v3_completed_call.py tests/integration/runs/test_v3_cite_preflight.py tests/integration/runs/test_v3_cite_stage.py -x --tb=short`
- expected: all passed; handoff exact-path and clean-tree checks pass.

## Integration contract
The completed-call reader returns the exact validated `max_tokens`, `output_config.effort` and adaptive `thinking` values from the matched effect/call parameter JSON. CITE reconstructs `V3GenerationSettings` from those values and still compares the exact provider-body SHA. A later worker needs the saved call, not a matching local settings object.

## Failure/idempotency/security cases
- Missing, extra or ill-typed generation fields refuse before any reply Blob read or CITE StageResult.
- Changed saved settings at the final locked call check refuse even when the preliminary request was built.
- No provider redispatch or model-supplied decision.

## Rollback / feature flag
Unserved behind the v3 executor guard. Revert before activation; no migration.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: API StageId reseal and served wiring remain
- integration notes: do not reintroduce current-process settings as CITE authority
