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
- captured_at: 2026-10-26
- command: `git grep -n -E 'effect_params =|settings: V3GenerationSettings|settings=settings' 3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f -- src/auditmanager/jobs/repository.py src/auditmanager/runs/v3_cite_preflight.py src/auditmanager/runs/v3_cite_stage.py; git grep -n -A 24 'class V3CompletedCall' 3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f -- src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py:1036:        effect_params = row["effect_parameters"]
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/runs/v3_cite_preflight.py:58:    settings: V3GenerationSettings,
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/runs/v3_cite_preflight.py:81:        model_identity=call.model_id, settings=settings,
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/runs/v3_cite_stage.py:86:    settings: V3GenerationSettings,
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/runs/v3_cite_stage.py:119:            settings=settings, jobs=job_repo, runs=run_repo,
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py:402:class V3CompletedCall:
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-403-    run_id: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-404-    job_id: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-405-    attempt_id: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-406-    model_call_id: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-407-    provider: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-408-    model_id: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-409-    provider_mode: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-410-    request_sha256: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-411-    response_sha256: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-412-    candidate_sha256: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-413-    scope_id: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-414-    set_sha256: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-415-    reply_blob_id: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-416-    reply_blob_sha256: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-417-    reply_blob_size: int
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-418-    input_tokens: int
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-419-    output_tokens: int
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-420-    latency_ms: int
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-421-    cost_micros: int | None
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-422-    cost_basis: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-423-    status: str
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-424-    connection_revision_id: str | None
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-425-    identity_basis: str | None
  3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f:src/auditmanager/jobs/repository.py-426-
  ```
- interpretation: Re-captured on 2026-10-26 from base commit 3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f with git grep against that tree (not at dispatch time). At the base, V3CompletedCall (repository.py:402-425) has no generation-parameter or settings field. completed_v3_call reads effect_parameters (line 1036) into a local; v3_cite_preflight.py takes settings: V3GenerationSettings (58) and forwards settings=settings (81); v3_cite_stage.py takes settings (86) and forwards it (119). So CITE preflight and writer require caller-supplied settings. Not shown: that the effect parameters are validated or discarded after line 1036 (the return statement is outside the captured lines). Dispatch-time record (2026-10-23, quoted from the original section, not re-run): command `rg -n 'class V3CompletedCall|effect_params =|settings: V3GenerationSettings|settings=settings' src/auditmanager/jobs/repository.py src/auditmanager/runs/v3_cite_preflight.py src/auditmanager/runs/v3_cite_stage.py`; captured_output was a prose summary: `V3CompletedCall` has no generation parameters; `completed_v3_call` reads `effect_parameters`; CITE preflight and writer require `settings` from their caller. Original interpretation: saved exact body replay can use only the canonical call/effect parameters after validating the v3 settings shape.

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
