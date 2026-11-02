# Task REVIEW-FIX-CMP-RUNTIME-1102 — comparison queue, stage repair undo and batch failures as documented

## Outcome
The comparison launch queue counts a step it launched and that later finished as `done`, never
`skipped`; an entry queued while the project's launch item finishes is not stranded; undoing an
applied repair on a completed stage run ends in a finished recompute, not a failed run; a batch
item that cannot start records why.

## Depends on
- REVIEW-FIX-BOUNDS-1102
- REVIEW-FIX-SEAMS-1102

## Frozen inputs
- domain contract: unchanged
- API contract: 1.14.0, unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0044_section_stats_uncapped` (this task adds no migration)
- base commit: the integration tip after REVIEW-FIX-BOUNDS-1102 and REVIEW-FIX-SEAMS-1102
- findings: S4-01, S4-03, S5-01, S5-05 in `.local/reports/code-review-2026-11-02/*.findings.md`

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
- `src/auditmanager/comparison/queue/**`
- `src/auditmanager/comparison/stage_repair/**`
- `src/auditmanager/comparison/stage_review/**`
- `src/auditmanager/comparison/stage_run/**`
- `tests/unit/comparison/queue/**`
- `tests/unit/comparison/stage_repair/**`
- `tests/unit/comparison/stage_review/**`
- `tests/integration/comparison/stage_run/**`

## Forbidden hotspots
- contracts, migrations, `scripts/recovery/**`, composition root, `infra/**`, root dependency/lock files, global styles
- `src/auditmanager/comparison/specification/**` and `comparison/version_reader.py` (REVIEW-FIX-CMP-SPEC-1102)

## Non-goals
- S4-04 provider mode wiring (needs the composition root), S5-03 graphic window count (needs a contract change).

## Deliverables
- S4-01: the skip decision is taken only at the start phase; at poll the handler reads progress and records `done` when the launched step finishes.
- S4-03: an entry added while the launch item finishes is picked up (a generation in the dedupe key, or a re-check of waiting entries before `Completed()`).
- S5-01: undo on a completed run either refuses with a typed reason or recomputes without re-materialising cards; it never leaves the run failed.
- S5-05: the reason a batch item could not start is recorded (an audit event or an existing column; no new migration).
- Unit tests for each.

## Verification
- Optional per owner instruction. Proof check if run: `.venv/bin/pytest -q tests/unit/comparison/queue tests/unit/comparison/stage_repair tests/unit/comparison/stage_run`.

## Integration contract
- The lane does not run git. The integrator commits exactly the allowed paths it changed.

## Rollback / feature flag
- Corrections of documented behaviour; no flag.
