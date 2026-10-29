# Task CMP-STAGE-TEXT-STORE-01 — append-only stage text evidence storage

## Outcome
A worker-side caller can write one complete deterministic text-evidence batch for a current confirmed sheet-map revision in one transaction, and exact replay returns the stored rows.

## Depends on
- CMP-STAGE-TEXT-DIFF-01

## Frozen inputs
- domain contract: ADR-0025 A-9; `COMPARE-MODULES-PLAN.md` §1.2/§4
- API contract: `1.12.0`, 204 paths / 230 operations / 570 schemas; no route change
- evidence core: `CMP-STAGE-TEXT-CORE-01`, `CMP-STAGE-TEXT-DIFF-01`
- migration head: `0041_comparison_stage_core`, sealed `stage_text_*`, `stage_link_*` tables and scope triggers
- base commit: `318e0c7bb07c2a7c599b638225ef89004e85acc3`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: pure evidence is committed but no storage caller exists; the C3 migration has immutable evidence rows.

### P-01 — base and table set
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; rg -n 'CREATE TABLE stage_text_(fragment|exclusion|difference|hint)' db/migrations/versions/20261029_0041_comparison_stage_core.py`
- captured_output:
  ```text
  318e0c7bb07c2a7c599b638225ef89004e85acc3
  db/migrations/versions/20261029_0041_comparison_stage_core.py:312:        CREATE TABLE stage_text_fragment (
  db/migrations/versions/20261029_0041_comparison_stage_core.py:335:        CREATE TABLE stage_text_exclusion (
  db/migrations/versions/20261029_0041_comparison_stage_core.py:359:        CREATE TABLE stage_text_difference (
  db/migrations/versions/20261029_0041_comparison_stage_core.py:388:        CREATE TABLE stage_text_hint (
  ```
- interpretation: the writer can use the frozen tables without a migration.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/CMP-STAGE-TEXT-STORE-01.md`
- `docs/program/CMP-STAGE-TEXT-STORE-01.md`
- `docs/program/CURRENT_STATE.md`
- `src/auditmanager/comparison/stage_text/**`
- `tests/unit/comparison/stage_text/**`
- `tests/integration/comparison/stage_text/**`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependencies/locks, composition root, global styles, C2 and C3 pair/link internals, generated client, remote refs

## Non-goals
- no served API, durable job scheduling, profile/blob reading, masks or UI
- no claim of full `CMP-STAGE-TEXT-01` or of a sealed empty-result run

## Deliverables
1. Transactional repository writing fragments and exact/difference/hint rows under a current map revision; frozen DB triggers enforce pair/side scope.
2. Stable content-key lookup, exact replay, refusal of a mismatched replay or stale revision, and no partial publish after a failed row.
3. Focused database test for replay, stale map, wrong side and transaction rollback.

## Required tests
- isolated `0041` PostgreSQL test for storage and rollback; scoped Stage Text unit tests
- `git diff --check`; later full integrated `make gate`

## Integration contract
The later worker orchestration provides complete immutable page-profile extraction, manifests and the pure algorithm result. It calls this repository only for the currently confirmed revision; the writer rechecks that authority inside its transaction. A later durable-run slice must tie this batch to a pinned run and seal even an empty result before calling the Stage Text API served.

## Failure/idempotency/security cases
- wrong-side or foreign profile refuses by database scope trigger and rolls back all rows
- a changed map revision refuses before any evidence row
- same content key with changed payload and any changed replay row set refuses

## Rollback / feature flag
The repository is not wired to a served adapter; dropping the branch restores the prior sealed 503. Existing immutable evidence rows are not deleted by this code.

## Handoff
- changed files: task/report/state, `src/auditmanager/comparison/stage_text/store.py`, `tests/integration/comparison/stage_text/test_store.py`; exact SHA/path proof follows after commit
- commands/results: isolated PostgreSQL **3 passed**, Stage Text unit **17 passed**, package compile and `git diff --check` passed
- contracts: none
- known limits: no durable job, served API, complete-profile orchestration or empty-result seal
- integration notes: use only from a pinned worker with complete source profiles
