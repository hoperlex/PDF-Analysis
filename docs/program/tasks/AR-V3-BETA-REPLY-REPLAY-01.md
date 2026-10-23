# Task AR-V3-BETA-REPLY-REPLAY-01 — verify saved v3 reply for CITE

## Outcome
A later CITE worker can read the private AR v3 reply Blob, verify its exact bytes and provider-call bindings, and obtain untrusted `SuppliedV3Response` without redispatching the model.

## Depends on
- `AR-V3-BETA-ANSWER-CUSTODY-01`

## Frozen inputs
- domain contract: `contracts/domain/v1`, unchanged
- API contract: `contracts/api/v1`, unchanged
- analysis/comparison/event contract: `contracts/analysis/v1`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `985e3a1cd0a6543c35ffcbf7dd2a872cb21f5832`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the provider receipt now carries a verified private reply ref
### P-01 — reply reference
- captured_at: 2026-10-23
- command: `rg -n 'reply_ref: ArtifactRef' src/auditmanager/runs/v3_provider_call.py`
- captured_output:
  ```text
57:    reply_ref: ArtifactRef
  ```
- interpretation: the new reader can use this ref, but must check its Blob bytes and call evidence independently.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/v3_reply_custody.py`
- `tests/integration/runs/test_v3_reply_custody.py`
- `tests/integration/runs/test_v3_provider_call.py`
- `docs/program/tasks/AR-V3-BETA-REPLY-REPLAY-01.md`
- `docs/program/AR-V3-BETA-REPLY-REPLAY-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- contracts, migrations, root dependencies and lock files
- composition root, active executor, provider transports, global styles
- normative maps, corpus and set data

## Non-goals
- Proving a completed DB model call/effect: the CITE owner supplies those independently read facts.
- Grounding and publishing CITE StageResult or findings.

## Deliverables
- Strict verified reply reader returning a local-evaluation input.
- Positive cross-producer and tamper tests; result note.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_reply_custody.py tests/integration/runs/test_v3_provider_call.py -x --tb=short`
- expected: all passed, task governance and exact allowlist clear.

## Integration contract
CITE rebuilds the sealed request from saved Run/set inputs, reads a completed model call and effect for the same Run/Attempt, constructs `V3ReplyExpectation` from those rows, and calls `read_v3_reply` with the call's recorded Blob reference. Only the returned `SuppliedV3Response` may enter the beta citation reviewer. The reader never treats model output as an expert decision.

## Failure/idempotency/security cases
- Wrong role, media type, bytes, size, envelope keys, run/call IDs, candidate/body/response digests or malformed usage refuses.
- No fallback to local paths or a second provider call.
- Read is read-only and uses verified Blob access.

## Rollback / feature flag
The active v3 executor guard remains. Revert this unserved reader without data migration if necessary.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: completed-call DB reader and CITE stage still open
- integration notes: use only canonical call/effect facts as expectation
