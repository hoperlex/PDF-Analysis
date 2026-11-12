# Task BLOCK-ANALYSIS-LIMITS-01 — retain norm queries and relationship explanations

## Outcome
An observation with more than two norm queries and a judge relationship with an explanation
longer than 300 characters survive parsing and processing without shortening either field.
Owner instruction: remove both limits identified in run `run_01M75JWVA0NTBXMXAV9FCZQ289`.

## Depends on
- None.

## Frozen inputs
- base commit: `ec1c7931eafe46f44f742a3d1ee561b199ae4152`
- Product 0.25.1 at the local `origin/dev` ref when the task began.
- API, domain and analysis contracts: 1.54.0, unchanged by this task.
- Migration head: `0067_precedents_wave5`, unchanged.
- The attached run is read-only diagnostic evidence; its observations are not committed.

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: local development base
- captured_at: 2026-11-12
- command: `git rev-parse origin/dev`
- captured_output:
  ```text
  ec1c7931eafe46f44f742a3d1ee561b199ae4152
  ```
- interpretation: identifies the local development base, not the deployed version.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/analysis/extended/core.py`
- `src/auditmanager/analysis/extended/block_ensemble.py`
- `src/auditmanager/analysis/extended/cross_window_review.py`
- `src/auditmanager/analysis/extended/workflow.py`
- `src/auditmanager/runs/extended_review.py`
- `src/auditmanager/runs/norm_queries.py`
- `tests/unit/analysis_extended/test_response_limits.py`
- `tests/unit/runs/test_analysis_reply_limits.py`
- `tests/unit/runs/test_block_sources_v2.py`
- `tests/unit/runs/test_norm_reply_per_record.py`
- `tests/contract/release_notes/test_release_notes_form.py`
- `release-notes/0.25.1.json`
- `docs/program/tasks/BLOCK-ANALYSIS-LIMITS-01.md`

## Forbidden hotspots
- `contracts/**`, migrations, root dependencies and lockfiles, composition roots, global styles.
- `origin/main`, deployment configuration and stored run artifacts.

## Non-goals
- Change norm verification completion semantics, search relevance, per-run search budgets,
  individual query length, source binding, citation validation or expert decisions.

## Deliverables
- Remove both limits from response schemas and parsers and the query-count remnants in
  lossless merge and lookup; focused regressions and a 0.25.1 revision note.

## Required tests
- `PYTHONPATH=src /root/projects/PDF-Analysis/.local/worktrees/plan-exec2/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/analysis_extended/test_response_limits.py tests/unit/runs/test_analysis_reply_limits.py`
- Expected: valid longer explanations and all queries retained; invalid sources still refused.
- With `PYTHONPATH=src`, run the new response/runtime tests and the existing core, workflow,
  block-ensemble, block-source, per-record norm and norm-search tests using the shared venv.
- Replay the six refused records from the attachment without changing their contents.
- `git diff --check`; inspect the diff against this allowlist.

## Integration contract
Consumers receive all valid queries and complete relationship explanations. Source identities,
types, reference uniqueness and exact norm citations retain their checks. Existing lookup
budgets remain explicit; additional queries are processed rather than silently sliced to two.
Request digest fixtures change with the deliberately changed internal response schemas.

## Rollback / feature flag
No new flag or storage migration. Revert the implementation commit if necessary. Previously
stored reports remain immutable; they are not recomputed or relabelled by this change.

## Handoff
- Implementation is on `agent/block-analysis-limits-01` and changes only the allowed paths.
- Focused core/workflow/runtime checks: 169 passed; after removing the literal planner's
  remaining slice, its runtime regressions and release-note checks: 28 passed (four repeated).
- The existing global cross-window request/cell-settings check also passed.
- All six original refused records now parse unchanged with their actual batch sources.
- Release 0.25.1 revision 2 records the behavior. No contract, migration, lockfile, composition
  or global-style change; no full gate, model call, publication or deployment.
- Integrator: cherry-pick this commit onto a descendant of the base and include the revision
  note. Run a new analysis to exercise the deployed fix; do not rewrite the earlier report.
- Known limit: the existing per-run norm-search window is separate and still explicit.
