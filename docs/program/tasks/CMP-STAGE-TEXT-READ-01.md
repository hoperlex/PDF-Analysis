# Task CMP-STAGE-TEXT-READ-01 — served immutable Stage Text evidence reads

## Outcome
An expert can page through stored Stage Text fragments, exact exclusions, raw differences and nonbinding hints for a confirmed pair/revision through the four frozen GET operations. Missing materialization refuses explicitly.

## Depends on
- CMP-STAGE-TEXT-STORE-01

## Frozen inputs
- domain contract: ADR-0025 A-9 and `COMPARE-MODULES-PLAN.md` §1.2/§4
- API contract: `1.12.0`, 204 paths / 230 operations / 570 schemas; four sealed GET operations, recompute POST remains sealed
- migration head: `0041_comparison_stage_core`; `stage_text_*` tables unchanged
- evidence producer: `CMP-STAGE-TEXT-STORE-01` and its content-key rows
- base commit: `ff0ba71bc86a1e17cff045d2b5304b22c8026e60`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: frozen GET methods still refuse while evidence rows can now be stored by a worker-side repository.

### P-01 — sealed adapter
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; rg -n '^class ComparisonStageTextAdapter|^class StageTextEvidenceStore' src/auditmanager/bootstrap/adapters.py src/auditmanager/comparison/stage_text/store.py`
- captured_output:
  ```text
  ff0ba71bc86a1e17cff045d2b5304b22c8026e60
  src/auditmanager/bootstrap/adapters.py:7085:class ComparisonStageTextAdapter(_StagesModuleGate):
  src/auditmanager/comparison/stage_text/store.py:49:class StageTextEvidenceStore:
  ```
- interpretation: the read service can expose stored rows without claiming a durable recompute command.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/CMP-STAGE-TEXT-READ-01.md`
- `docs/program/CMP-STAGE-TEXT-READ-01.md`
- `docs/program/CURRENT_STATE.md`
- `src/auditmanager/comparison/stage_text/**`
- `src/auditmanager/comparison/public.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `tests/integration/comparison/stage_text/**`
- `tests/integration/api/test_stage_text_read.py`
- `tests/integration/composition/test_comparison_stage_stub_operations.py`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependencies/locks, global styles, C2 and other C3 service internals, generated client, deployment/remote refs

## Non-goals
- no recompute POST, durable scheduling, masks, browser screen or contract reseal
- no claim of full `CMP-STAGE-TEXT-01` or a completed empty-evidence run

## Deliverables
1. Pair/revision-scoped keyset reads with explicit parent absence, cursor validation and module gating.
2. No empty-success for unmaterialized evidence; immutable historical revision reads stay available after a newer map revision.
3. DB, real HTTP and composition tests including module-off, pagination, unknown IDs and unmaterialized refusal.

## Required tests
- isolated `0041` PostgreSQL and HTTP tests, composition stubs; `git diff --check`
- later integrated `make gate` on exact C3 candidate

## Integration contract
The four GETs serve only rows already persisted by the Stage Text writer. They never compute or mutate evidence. The POST still returns its sealed typed 503. A future durable-run slice must seal empty results and decide when a pair/revision is materialized before these reads can return an empty successful page for that case.

## Failure/idempotency/security cases
- missing pair or revision returns 404; a valid but unmaterialized revision refuses with `comparison_stage_text_evidence` dependency
- invalid or foreign cursor refuses; no cross-pair rows are returned
- module `none`/`versions` still returns `comparison_modules` 503 before any read

## Rollback / feature flag
`AUDITMANAGER_COMPARISON_MODULES=none` or `versions` restores the typed module refusal; stored rows are immutable. No schema rollback.

## Handoff
- changed files: task/report/state, Stage Text read service, comparison public export, adapter/composition wiring, DB/HTTP/composition tests; exact SHA/path proof follows after commit
- commands/results: isolated PostgreSQL store/read and HTTP **6 passed**; C3 composition registry **67 passed**; pure Stage Text unit **17 passed**, package compile and `git diff --check` passed
- contracts: none
- known limits: recompute POST, durable worker, empty-result seal and UI remain open
- integration notes: merge after store; no remote publication authority
