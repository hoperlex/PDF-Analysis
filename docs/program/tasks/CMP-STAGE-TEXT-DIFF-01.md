# Task CMP-STAGE-TEXT-DIFF-01 — bounded raw Stage Text differences

## Outcome
After exact exclusions, a confirmed sheet relation yields deterministic, box-addressable changed/removed/added fragment references; a unique same-text fragment on another Р sheet yields a recommendation only.

## Depends on
- CMP-STAGE-TEXT-CORE-01

## Frozen inputs
- domain contract: ADR-0025 A-9; `COMPARE-MODULES-PLAN.md` §1.2/§4; `ORIGINAL-UNREAD-SOURCES.md` §1.6/§1.8
- API contract: `1.12.0`, 204 paths / 230 operations / 570 schemas
- evidence: `CMP-STAGE-TEXT-CORE-01` fragment/exclusion types and complete-key manifest
- migration head: `0041_comparison_stage_core`; differences are changed/removed/added; hints are recommendation-only
- base commit: `35782bdf55c1394821ab9e771b94186e8573e666`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: pure exact exclusions exist at the committed base while the served text adapter remains sealed.

### P-01 — base and sealed adapter
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; rg -n '^class ComparisonStageTextAdapter|^def prove_exact_exclusions' src/auditmanager/bootstrap/adapters.py src/auditmanager/comparison/stage_text/exact.py`
- captured_output:
  ```text
  35782bdf55c1394821ab9e771b94186e8573e666
  src/auditmanager/bootstrap/adapters.py:7085:class ComparisonStageTextAdapter(_StagesModuleGate):
  src/auditmanager/comparison/stage_text/exact.py:38:def prove_exact_exclusions(
  ```
- interpretation: this slice may add pure algorithms without changing a served endpoint.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/CMP-STAGE-TEXT-DIFF-01.md`
- `docs/program/CMP-STAGE-TEXT-DIFF-01.md`
- `docs/program/CURRENT_STATE.md`
- `src/auditmanager/comparison/stage_text/**`
- `tests/unit/comparison/stage_text/**`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependencies/locks, composition root, global styles, C2 and other C3 service internals, generated client, remote refs

## Non-goals
- no served API, storage, queue, UI, model call or contract reseal
- no claim of full `CMP-STAGE-TEXT-01` or reverse-direction hint persistence

## Deliverables
1. Deterministic raw difference classes only after exact proof, with one-to-one changed candidates, bounded similarity and explicit removed/added remainder.
2. Left→right cross-sheet lookup that emits a recommendation only under a unique, non-frequent, exact text proof; it never edits a map or an exclusion.
3. Tests for numeric change, ambiguous candidates, input budget, repeated text and recommendation isolation.

## Required tests
- scoped `pytest tests/unit/comparison/stage_text`; `git diff --check`
- later integrated `make gate` on exact C3 merge candidate

## Integration contract
The later persistence slice rechecks current map authority, reads complete pinned profiles and writes raw differences separately from exclusions/hints. A hint cannot modify a link or raw evidence. Fragment keys resolve to sealed `stage_text_fragment` rows only after persistence. The sealed hint table accepts left source/right target; a reverse-direction hint needs a later contract decision.

## Failure/idempotency/security cases
- incomplete manifest, oversized comparison or malformed relation refuses before partial output
- ambiguous changed candidates remain raw removed/added evidence rather than a claimed pair
- exact exclusions are never reclassified as changed; weak similarities do not erase unmatched text

## Rollback / feature flag
Pure code remains unreachable from served adapters; dropping this branch restores the prior pure core and sealed 503.

## Handoff
- changed files: task/report/state, `src/auditmanager/comparison/stage_text/{__init__,differences,hints}.py`, `tests/unit/comparison/stage_text/test_differences.py`; exact SHA/path proof follows after commit
- commands/results: scoped Stage Text **17 passed**; Python package compile and `git diff --check` passed
- contracts: none
- known limits: no persistence, durable recomputation, mask or UI; left→right hints only
- integration notes: consume under confirmed map revision and complete profile manifest
