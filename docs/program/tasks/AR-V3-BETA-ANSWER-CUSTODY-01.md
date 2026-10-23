# Task AR-V3-BETA-ANSWER-CUSTODY-01 — durable v3 answer bytes

## Outcome
A received AR v3 model reply is kept in a verified, private Blob with an Attempt-scoped publication intent, and its Blob identity and SHA are carried by the completed model call for later CITE readback.

## Depends on
- `AR-V3-BETA-PROVIDER-JOURNAL-01`
- `AR-V3-BETA-REQUEST-CUSTODY-01`

## Frozen inputs
- domain contract: `contracts/domain/v1`, unchanged
- API contract: `contracts/api/v1`, unchanged
- analysis/comparison/event contract: `contracts/analysis/v1`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `a86e7cf16e77e33b9c7a7e10004b0b2d6830d69e`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: a completed v3 call currently returns the answer without a response Blob
### P-01 — response receipt boundary
- captured_at: 2026-10-23
- command: `rg -n 'answer evidence survives a later identity/CITE refusal' src/auditmanager/runs/v3_provider_call.py`
- captured_output:
  ```text
192:    session.commit()  # answer evidence survives a later identity/CITE refusal
  ```
- interpretation: the response hash and usage survive, while output text still needs Blob custody.

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
- `docs/program/tasks/AR-V3-BETA-ANSWER-CUSTODY-01.md`
- `docs/program/AR-V3-BETA-ANSWER-CUSTODY-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migrations, root dependencies and lock files
- composition root, active executor, provider transports, global styles
- normative maps, corpus, set data and API schemas

## Non-goals
- Raw HTTP wire-body capture; model adapters expose a parsed `ModelResponse`.
- CITE StageResult, response interpretation, finding publication or v3 activation.

## Deliverables
- Attempt-scoped response artifact publication via existing outbox, verified readback and completed-call link.
- Focused boundary/failure tests and result note.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_provider_call.py tests/integration/runs/test_v3_execution_request.py -x --tb=short`
- expected: all passed; exact allowed paths; `git diff --check`.

## Integration contract
The receipt includes an `ArtifactRef` for the exact canonical parsed response envelope. CITE must verify/read that Blob, compare its recorded hashes and model_call_id with the completed effect, then bind the artifact in its StageResult transaction. Until binding, an interrupted Attempt leaves an enumerable publication intent and must not redispatch.

## Failure/idempotency/security cases
- Response receipt is committed before Blob upload; its declaration/intent is committed before external upload.
- Digest or readback mismatch refuses success. The completed call is never written without answer custody.
- A process loss after response leaves durable effect and publication breadcrumbs; no automatic replay.
- The private Blob holds response text and model metadata, never a credential.

## Rollback / feature flag
Active v3 executor guard remains. Revert this unserved slice before CITE integration if needed; reconcile any test-only publication intents.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: no served v3 stage or CITE binding
- integration notes: bind reply ref with CITE StageResult
