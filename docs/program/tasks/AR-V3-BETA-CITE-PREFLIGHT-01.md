# Task AR-V3-BETA-CITE-PREFLIGHT-01 — bind saved v3 reply to grounded review

## Outcome
A current CITE Attempt can rebuild its saved AR v3 request, match the sole completed call and verified reply, and obtain a grounded, review-only beta classification without redispatch.

## Depends on
- `AR-V3-BETA-REQUEST-CUSTODY-01`
- `AR-V3-BETA-SAVED-SOURCE-01`
- `AR-V3-BETA-REPLY-REPLAY-01`
- `AR-V3-BETA-CALL-READ-01`

## Frozen inputs
- domain contract: `contracts/domain/v1`, unchanged
- API contract: `contracts/api/v1`, unchanged
- analysis/comparison/event contract: `contracts/analysis/v1`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `717e904c20cf05ed438218af28260041930efb95`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: completed-call facts and a verified reply reader exist but have no CITE join
### P-01 — available seam
- captured_at: 2026-10-23
- command: `rg -n 'def completed_v3_call|def read_v3_reply|def plan_v3_beta_citation_review' src/auditmanager/jobs/repository.py src/auditmanager/runs`
- captured_output:
  ```text
  src/auditmanager/jobs/repository.py:970:    def completed_v3_call(
  src/auditmanager/runs/v3_citations.py:193:def plan_v3_beta_citation_review(
  src/auditmanager/runs/v3_reply_custody.py:69:def read_v3_reply(
  ```
- interpretation: the missing join must compare saved request hashes and call/answer facts before grounding.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/v3_cite_preflight.py`
- `tests/integration/runs/test_v3_cite_preflight.py`
- `docs/program/tasks/AR-V3-BETA-CITE-PREFLIGHT-01.md`
- `docs/program/AR-V3-BETA-CITE-PREFLIGHT-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lock files
- composition root, active executor, provider transports, global styles
- normative maps, source corpus and set data

## Non-goals
- Writing a CITE StageResult or publishing findings.
- Serving v3, approving six maps/sets, or making a legal/numeric conclusion.
- Changing the existing Blob reader transaction behavior.

## Deliverables
- One read-only CITE preflight result with completed call, saved request, verified answer and grounded beta review.
- Focused refusal tests, result note and queue update.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_cite_preflight.py tests/integration/runs/test_v3_reply_custody.py tests/integration/runs/test_v3_execution_request.py tests/integration/runs/test_v3_corpus_citation_bridge.py -x --tb=short`
- expected: all passed; governance findings empty and changed-path check clear.

## Integration contract
Use the returned review only as an input to a later current-Attempt CITE writer. The writer must bind the exact call and reply artifact to its StageResult, recheck the same group/set pins, and keep provisional/context-only distinctions. Generation settings are explicit inputs and the rebuilt provider-body SHA must equal the saved call. This function neither commits nor writes; caller owns the transaction.

## Failure/idempotency/security cases
- Missing/duplicate call, changed candidate/scope/set/body digest, wrong Run/Job/mode, mismatched reply usage/status/cost, absent live model report or stale Attempt refuses. The provider boundary has already checked the reported name against its connection pin; that name need not equal the request's model pin ID.
- Recovered prior-Attempt call is accepted only through the jobs reader for the same Job; no model invocation.
- Context-only and mixed citations remain withheld by the beta policy.

## Rollback / feature flag
Unserved and read-only behind the current v3 executor guard. Revert this bridge without migration before CITE activation.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: caller-held lease locks across Blob reads; CITE writer and served wiring remain open
- integration notes: use a short, dedicated CITE read transaction and check lease behavior before serving
