# Task AR-V3-BETA-CITE-WRITER-01 — persist the grounded beta review

## Outcome
A current AR v3 beta Attempt can publish its grounded review artifact through the durable outbox and commit one validated CITE StageResult with the artifact binding; a grounded refusal is recorded as an explicit failed stage.

## Depends on
- `AR-V3-BETA-CITE-PREFLIGHT-01`
- `AR-V3-BETA-REVIEW-ARTIFACT-01`
- `AR-V3-BETA-CITE-STAGE-CONTRACT-01`

## Frozen inputs
- domain/API/analysis/events contract: `1.2.0`, unchanged
- AR v3 CITE extension: `contracts/analysis/ar_v3_beta/v1/stage.json` 1.0.0
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `cc94c8e3a7e27096148ed45847d5b7a630faca7e`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the existing outbox and StageResult binder can publish review bytes without a dual write
### P-01 — durable publication and binder
- captured_at: 2026-10-23
- command: `rg -n '^def _publication_store|^def _persist_and_bind' src/auditmanager/runs/executor.py`
- captured_output:
  ```text
  422:def _publication_store(
  463:def _persist_and_bind(
  ```
- interpretation: reuse the existing commit-before-Blob outbox and transaction-bound StageResult/Blob binding, with an independent current-Attempt and call/set recheck.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/v3_cite_stage.py`
- `tests/integration/runs/test_v3_cite_stage.py`
- `docs/program/tasks/AR-V3-BETA-CITE-WRITER-01.md`
- `docs/program/AR-V3-BETA-CITE-WRITER-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lockfiles
- composition root, active executor, provider transports, global styles
- normative maps, source corpus and set data

## Non-goals
- Serving v3, approving six maps/sets, terminating a Run or publishing a finding.
- Changing the existing outbox or global stage registry.
- Resolving the slow Blob-read/lease lock span (required before served activation).

## Deliverables
- One unserved current-Attempt CITE writer and focused success, replay and failure tests.
- Result note and queue update.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_cite_stage.py tests/integration/runs/test_v3_cite_preflight.py tests/integration/runs/test_v3_review_artifact.py -x --tb=short`
- expected: all passed; governance, changed-path and diff checks clear.

## Integration contract
Caller begins with a committed running Run/current Job Attempt and a live lease heartbeat. The writer validates the profile stage declaration, checks group and prior stage rows, records stage.started, commits it, rebuilds the saved request/call/reply, publishes the review via the Attempt outbox and verifies exact bytes. It rechecks current Attempt, group, completed call and prior rows, then validates and commits StageResult and Blob binding together. No provider retry occurs. Caller owns later Run terminal selection; six-Run aggregation remains separate.

## Failure/idempotency/security cases
- Existing CITE StageResult refuses replay. A new Attempt may consume a prior completed call of the same Job but has its own artifact intent.
- Verified input/grounding refusal records a failed StageResult under current authority. Unexpected storage or infrastructure failure propagates; prepared intent remains reconcilable.
- Stale Attempt or changed call/group/source rows after Blob publication refuses final bind; no success StageResult is committed.

## Rollback / feature flag
Unserved behind the active v3 executor guard. Revert before activation without migration; keep any already recorded outbox/call evidence immutable.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: no real DB/S3 acceptance, slow Blob lease hazard and served wiring open
- integration notes: do not call this from the legacy executor until pack and lease tests pass
