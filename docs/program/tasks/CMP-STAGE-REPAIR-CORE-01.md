# Task CMP-STAGE-REPAIR-CORE-01 — deterministic, reversible sheet-link repair plans

## Outcome
A caller can obtain a complete, immutable before/after map plan only for deterministic HIGH repair proof, and can check whether that recorded plan is still eligible for revert after later map edits.

## Depends on
- CMP-STAGE-TEXT-DIFF-01

## Frozen inputs
- domain contract: ADR-0025 A-9, Q-CMP-10/D-1, `COMPARE-MODULES-PLAN.md` §4 C4
- API contract: `1.12.0`, 204 paths / 230 operations / 570 schemas; no API change
- migration head: `0041_comparison_stage_core`; no schema or database write
- repair specification: `ORIGINAL-UNREAD-SOURCES.md` §1.2, §1.3 and purpose precheck §1.11
- base commit: `9fa035029a3422b1c3e63d108fbe8c5fdde5dd8e`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the roadmap requires HIGH deterministic repair and undo; this base has no repair implementation.

### P-01 — frozen repair thresholds
- captured_at: 2026-10-30
- command: `git rev-parse HEAD; rg -n '^\| CMP-STAGE-REPAIR-01' docs/program/dispatch/COMPARE-MODULES-PLAN.md`
- captured_output:
  ```text
  9fa035029a3422b1c3e63d108fbe8c5fdde5dd8e
  590:| CMP-STAGE-REPAIR-01 | deterministic purpose precheck, one repair cycle per run (title: unique exact or mutual-best fuzzy ≥ 0.94 with margin 0.02; content: score ≥ 0.44, margin ≥ 0.14, reverse margin ≥ 0.10, improvement ≥ 0.18 — `ORIGINAL-UNREAD-SOURCES.md`; swaps and chains applied atomically); with HIGH proof it may change an expert's link as a recorded, revertible automatic act (`Q-CMP-10`, D-1 withdrawn); repair records, «Откатить» with recompute of steps 02–07, supersession by a later manual edit | M | `src/auditmanager/comparison/stage_repair/**` (new) |
  ```
- interpretation: this task prepares the pure plan and revert predicate; the later C4 service owns persistence and recomputation.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/stage_repair/**`
- `tests/unit/comparison/stage_repair/**`
- `docs/program/tasks/CMP-STAGE-REPAIR-CORE-01.md`
- `docs/program/CMP-STAGE-REPAIR-CORE-01.md`
- `.venv`

## Forbidden hotspots
- contracts, migrations, root dependencies/locks, shared adapter/composition/public wiring, global styles, remote refs, database/blob writes

## Non-goals
- no automatic database act, AI verdict, full chain run, API, UI or contract reseal
- no inferred identity from sheet title or page number; caller supplies canonical profile/link identities

## Deliverables
1. Purpose precheck and title proof (unique exact or mutual fuzzy ≥0.94, margins ≥0.02).
2. Deterministic content-score matrix gate (score ≥0.44, forward margin ≥0.14, reverse margin ≥0.10, improvement ≥0.18 plus content-anchor evidence).
3. Atomic complete swap/chain plans with before/after snapshots, consumed/released unpaired pages and one repair pass per run.
4. Revert eligibility that refuses a superseding manual edit or a map different from the recorded after snapshot.

## Required tests
- focused pure unit suite and `git diff --check`; full gate deferred by the owner's 2026-10-30 instruction

## Integration contract
`plan_repairs` receives the complete current map, complete sheet title inventory, purpose-problem link IDs, and optional complete deterministic content-score matrix. It returns a complete HIGH plan or `None`. The C4 runtime validates its base revision, persists before/after snapshots, assigns canonical IDs for new rows, and applies the entire after snapshot in one transaction. `revert_eligibility` is an explicit predicate; it does not write or launch recomputation.

## Failure/idempotency/security cases
- duplicate IDs, malformed map, incomplete content matrix and a repeated repair run refuse
- a many-to-many or non-problem link is never displaced; a broken displacement chain is omitted completely
- content scores are deterministic evidence supplied by the caller, never model output; no hint becomes a repair on its own

## Rollback / feature flag
Pure code is unreachable until the integrator wires the C4 service; removing the lane has no persisted side effect.

## Handoff
- changed files: task/report, `src/auditmanager/comparison/stage_repair/{__init__,types,purpose,planner}.py`, `tests/unit/comparison/stage_repair/test_planner.py`
- commands/results: focused unit **10 passed**; package compile and `git diff --check` passed
- contracts: none
- known limits: runtime persistence, score extraction, API and recompute are later tasks
- integration notes: apply/revert only as revision-checked atomic acts with recorded snapshots
