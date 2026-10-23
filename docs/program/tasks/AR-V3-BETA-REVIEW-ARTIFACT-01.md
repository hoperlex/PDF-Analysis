# Task AR-V3-BETA-REVIEW-ARTIFACT-01 — seal review-only CITE bytes

## Outcome
The completed AR v3 CITE preflight can produce deterministic, bounded review-only artifact bytes with every scoped topic, provisional grounded citations and withheld/rejected diagnostics, while excluding model-supplied numeric conclusions.

## Depends on
- `AR-V3-BETA-CITE-PREFLIGHT-01`
- `AR-BETA-CITATION-REVIEW-GATE-01`

## Frozen inputs
- domain contract: `contracts/domain/v1`, unchanged
- API contract: `contracts/api/v1`, unchanged
- analysis/comparison/event contract: `contracts/analysis/v1` 1.2.0, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `4a03d25f22d04f962f8b00a549abd024a11f2639`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: current registry's normative stage depends on finding_merge, while v3 CITE needs a separate contract slot
### P-01 — existing stage and premature preflight label
- captured_at: 2026-10-23
- command: `rg -n '"stage_id": "norm_verification"|"depends_on": \["finding_merge"\]|stage_id="citation_validation"' contracts/analysis/v1/stage-registry.json src/auditmanager/runs/v3_cite_preflight.py`
- captured_output:
  ```text
  contracts/analysis/v1/stage-registry.json:701:      "stage_id": "norm_verification",
  src/auditmanager/runs/v3_cite_preflight.py:47:        stage_id="citation_validation", reason=reason,
  ```
- interpretation: no `citation_validation` canonical stage exists; use the registered text-analysis error label until a contract-owned CITE stage is defined. Do not reuse the existing normative stage for this distinct sequence.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/v3_cite_preflight.py`
- `src/auditmanager/runs/v3_review_artifact.py`
- `tests/integration/runs/test_v3_cite_preflight.py`
- `tests/integration/runs/test_v3_review_artifact.py`
- `docs/program/tasks/AR-V3-BETA-REVIEW-ARTIFACT-01.md`
- `docs/program/AR-V3-BETA-REVIEW-ARTIFACT-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lockfiles
- composition root, active executor, provider transports, global styles
- normative maps, source corpus and set data

## Non-goals
- Writing or publishing the artifact, binding a StageResult or serving v3.
- Publishing normative findings or an expert decision.
- Adding a new canonical stage without the later contract/integration slot.

## Deliverables
- Canonical review artifact bytes and digest with exact call/set/response provenance.
- Focused totality, numerical suppression and tamper tests; result note.
- Correction of the preflight's premature noncanonical error-stage label.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_review_artifact.py tests/integration/runs/test_v3_cite_preflight.py -x --tb=short`
- expected: all passed; governance and exact changed-path checks clear.

## Integration contract
The returned artifact is an internal, unpublished `analysis.v3_beta_review` payload. A later contract-owned CITE writer must validate the registry stage/output role, publish through the existing outbox, read back exact bytes, bind the same completed call and reply, and commit StageResult under current Attempt. Topic statuses are advisory; model numeric claims never enter this artifact.

## Failure/idempotency/security cases
- Mismatched request/review/call/response pins, missing or duplicate topics, overlapping or missing normative proposal classifications, salvaged or malformed response, and artifact >2 MiB refuse.
- Withheld/rejected proposals never carry numeric claims or recommendation text. Provisional entries carry only grounded quotes/anchors and suggestion text, no model-required or project-stated numeric value field.
- Canonical bytes and SHA are stable under repeated build; no external effect.

## Rollback / feature flag
Pure, unserved code behind the existing v3 executor guard; revert without migration.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: artifact is not durable or served until contract-owned writer
- integration notes: do not map this draft to existing `norm_verification` contract
