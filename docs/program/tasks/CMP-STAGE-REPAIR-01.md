# Task CMP-STAGE-REPAIR-01 — recorded automatic repair and undo

## Outcome
A full chain may apply one HIGH deterministic map-repair plan atomically, preserve before/after revisions and recompute steps 2–7; an expert can undo a current repair, while a later manual map supersedes it.

## Depends on
- CMP-STAGE-REPAIR-CORE-01
- CMP-STAGE-TEXT-RECOMPUTE-01
- CMP-SEAL-C4

## Frozen inputs
- domain: ADR-0025 Q-CMP-10, `COMPARE-MODULES-PLAN.md` C4 thresholds
- current contract/migration: `1.13.0` / `0042_comparison_stage_review`; runtime consumes the committed C4 repair/event and effective-revision seam
- base commit: `d16a5627a43e659c1702b32879fe5662b1d770e4`
- deterministic core: `plan_repairs`, `revert_eligibility`; raw text remains immutable

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: pure repair core exists; no repair persistence caller is served yet

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/stage_repair/**`
- `src/auditmanager/comparison/stage_text/recompute.py`
- `tests/unit/comparison/stage_repair/**`
- `tests/integration/comparison/stage_repair/**`
- `docs/program/tasks/CMP-STAGE-REPAIR-01.md`
- `docs/program/CMP-STAGE-REPAIR-01.md`

## Forbidden hotspots
- contracts/migrations/shared wiring, root locks, styles, unrelated services and remote refs

## Non-goals
- no model-owned link, raw-evidence rewrite or second repair cycle
- no gate or heavy acceptance window today

## Deliverables
- transactional automatic revision/repair/event writer, deterministic score source and keyed expert undo
- persisted supersession and a recomputation request on undo
- focused checks and integration instruction

## Required tests
- focused transaction/replay/undo checks and whitespace/compile
- full gates deferred by owner's 2026-10-30 instruction

## Integration contract
The full chain calls `advance(item, run_id)` at step5; `recompute:1` means effective revision changed and steps2–7 were reset durably. Undo creates a new expert revision and queues deterministic recomputation; it never edits old evidence. Root owns API wiring and dev publication.

## Failure/idempotency/security cases
- same base/source plan replays; stale base or later manual edit prevents automatic overwrite/undo
- lease fence, map lock and run cycle count protect atomic swaps/chains
- HIGH proof is required by the pure planner; missing evidence cannot become a repair

## Rollback / feature flag
Stages flag disables caller/work claims; repair remains recorded and can be explicitly undone while current.

## Handoff
- changed files: see `docs/program/CMP-STAGE-REPAIR-01.md`
- checks/results: focused PostgreSQL tests PASS (RUN 4; REPAIR 2); compile and whitespace PASS
- contracts: none owned
- known limits: manual supersession is derived from latest revision; old repair events remain immutable
- integration notes: root shared wiring
