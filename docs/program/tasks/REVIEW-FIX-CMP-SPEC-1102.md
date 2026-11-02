# Task REVIEW-FIX-CMP-SPEC-1102 — specification extraction durable and resumable; versions beyond 500 pages under relaxed intake

## Outcome
A failed or truncated specification batch no longer seals a side forever; the zero-call consent
gate is per command, not process-wide state; progress writes counters, not every position; list
reads do not re-plan; the comparison cost estimate does not parse a whole PDF inside the HTTP
request and again in the start transaction; with `AUDITMANAGER_INTAKE_RELAXED=1` a comparison
version above 500 pages is accepted by every comparison table (migration 0045).

## Depends on
- REVIEW-FIX-BOUNDS-1102
- REVIEW-FIX-SEAMS-1102

## Frozen inputs
- domain contract: unchanged
- API contract: 1.14.0, unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0044_section_stats_uncapped`; this task owns the next slot `0045`
- base commit: the integration tip after REVIEW-FIX-BOUNDS-1102 and REVIEW-FIX-SEAMS-1102
- findings: S2-blocks-4-9-02, -04, -05, -06, -08, -11 and S6-04 in `.local/reports/code-review-2026-11-02/*.findings.md`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `db/migrations/versions/**`
- enumerator_owner: REVIEW-FIX-CMP-SPEC-1102
- totality_query: `ls db/migrations/versions/*_004*.py`

## Captured premise evidence
- premise: the comparison tables still check 500 pages

### P-01 — page constants in the comparison migrations
- captured_at: 2026-11-02
- command: `grep -n '^MAX_PAGE_NUMBER' db/migrations/versions/20261027_0035_comparison_records.py db/migrations/versions/20261028_0038_comparison_foundation.py db/migrations/versions/20261028_0039_comparison_core.py db/migrations/versions/20261029_0040_comparison_ai_reports.py`
- captured_output:
  ```text
  db/migrations/versions/20261027_0035_comparison_records.py:97:MAX_PAGE_NUMBER = 500
  db/migrations/versions/20261028_0038_comparison_foundation.py:90:MAX_PAGE_NUMBER = 500
  db/migrations/versions/20261028_0039_comparison_core.py:88:MAX_PAGE_NUMBER = 500
  db/migrations/versions/20261029_0040_comparison_ai_reports.py:78:MAX_PAGE_NUMBER = 500
  ```
- interpretation: page checks of the comparison tables stop at 500 regardless of the code constant.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/specification/**`
- `src/auditmanager/comparison/ai_jobs/service.py`
- `src/auditmanager/comparison/version_reader.py`
- `src/auditmanager/runs/preflight.py`
- `src/auditmanager/runs/commands.py`
- `db/migrations/versions/20261102_0045_comparison_page_bounds.py`
- `scripts/recovery/schema_coverage.py`
- `tests/unit/comparison/specification/**`
- `tests/unit/runs/**`

## Forbidden hotspots
- contracts, composition root, `infra/**`, root dependency/lock files, global styles
- paths owned by REVIEW-FIX-CMP-RUNTIME-1102 and REVIEW-FIX-ANALYSIS-1102

## Non-goals
- Export labels and chunking (S2-09, S2-10), estimate output sizing (S2-07).

## Deliverables
- Migration `0045_comparison_page_bounds`: relax the page-number CHECKs of the comparison tables created in 0035/0038/0039/0040 to `>= 1` (and their documented companions), with a downgrade guard that refuses when rows above 500 exist; `schema_coverage.py` moved to the new head with the new constraint shapes.
- `version_reader.MAX_VERSION_PAGES` stays 500 by default; with `AUDITMANAGER_INTAKE_RELAXED=1` it rises to the database integer maximum (read through the settings function REVIEW-FIX-BOUNDS-1102 added).
- S2-04: an aggregate incomplete because of a failed batch is not persisted as final; the side can be re-asked under fresh consent, never when a paid reply is unconfirmed.
- S2-05: the zero-call flag travels with the counts of the command, not on the shared `SpecMethod`.
- S2-06: per-batch progress writes counters only to the comparison row.
- S2-08: list reads do not re-plan transitions without a row; a missing page count becomes a per-transition `incomplete` diagnostic.
- S2-11: a "complete" extraction needs positions or an explicit empty table header.
- S6-04: the comparison-PDF character count is computed once when the version completes (or cached by blob sha256) and never inside the start transaction.
- Unit tests for each.

## Verification
- Optional per owner instruction. Proof check if run: `.venv/bin/pytest -q tests/unit/comparison/specification tests/unit/runs`.

## Integration contract
- The lane does not run git. The integrator commits exactly the allowed paths it changed.
- REVIEW-FIX-TESTS-1102 moves `tests/support/expected_facts.json` to the new head.

## Rollback / feature flag
- `AUDITMANAGER_INTAKE_RELAXED=0` (default) keeps comparison versions at 500 pages; the migration downgrade is guarded.
