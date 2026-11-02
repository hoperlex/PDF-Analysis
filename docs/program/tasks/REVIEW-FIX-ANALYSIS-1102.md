# Task REVIEW-FIX-ANALYSIS-1102 — section analysis does what its reports promise on ordinary runs

## Outcome
One refused critic reply no longer aborts a whole paid window; norm verification is not marked
partial merely because a search excerpt has two fragments; request-size guards see the final
request after context decorators; zero-call assembly opens only when there is something to edit.

## Depends on
- REVIEW-FIX-BOUNDS-1102
- REVIEW-FIX-SEAMS-1102

## Frozen inputs
- domain contract: unchanged
- API contract: 1.14.0, unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0044_section_stats_uncapped`
- base commit: the integration tip after REVIEW-FIX-BOUNDS-1102 and REVIEW-FIX-SEAMS-1102
- findings: S1-sprints-03, S1-sprints-05, S3-03, S3-05 in `.local/reports/code-review-2026-11-02/*.findings.md`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/analysis/extended/**`
- `src/auditmanager/runs/extended_review.py`
- `src/auditmanager/norms/paragraph_context.py`
- `tests/unit/analysis/**`
- `tests/unit/norms/**`

## Forbidden hotspots
- contracts, migrations, composition root, `infra/**`, root dependency/lock files, global styles
- `src/auditmanager/norms/search/**` (read the fragment delimiter through the norms public seam)

## Non-goals
- New model steps, prompt rewrites, cost-policy changes.

## Deliverables
- S1-sprints-03: in `parse_critic_reply` a rejection-type reason with `enough_source` below the reject thresholds becomes `needs_human` with the model text kept as a note; per-batch parse errors in `_review_batched_v3` / `_norm_batched_v3` record a failed receipt for that batch and the window continues.
- S3-03: the literal-quote check splits a stored excerpt on the search fragment delimiter and requires every non-empty segment to be found; the stored quote is unchanged.
- S3-05: each context decorator re-runs the request byte check after attaching and fails the window cleanly when over the limit.
- S1-sprints-05: `can_run_without_model` also requires at least one editable unit with a chunk.
- Unit tests for each of the four.

## Verification
- Optional per owner instruction. Proof check if run: `.venv/bin/pytest -q tests/unit/analysis tests/unit/norms`.

## Integration contract
- The lane does not run git. The integrator commits exactly the allowed paths it changed.

## Rollback / feature flag
- Existing flags unchanged; behaviour changes are corrections of documented behaviour.
