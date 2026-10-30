# Task CMP-STAGE-RUN-01 — durable stage chain and batch lifecycle

## Outcome
Single and batch stage comparisons have durable seven-step progress, keyed expert commands, explicit AI consent, cancellation/resume and version/map staleness; workers cooperate with the deterministic, AI, repair and review services.

## Depends on
- CMP-STAGE-TEXT-RECOMPUTE-01
- CMP-SEAL-C4
- CMP-STAGE-REPAIR-CORE-01

## Frozen inputs
- domain: ADR-0025, `COMPARE-MODULES-PLAN.md` C4 and §1.2
- base commit: `d16a5627a43e659c1702b32879fe5662b1d770e4` (C4 provider and shared cancellation seam)
- current API/migration: `1.13.0` / `0042_comparison_stage_review`
- provider seam: serial `CMP-SEAL-C4` owner has assigned `stage_chain_run.kind/with_ai/comparison_ai_job_id/effective_link_revision_id/stage_chain_batch_id/pause_reason/repair_cycle_count` plus durable batch/item tables; runtime is integrated only after its committed 1.13/0042 seal
- shared AI runtime owns provider/spend calls; this lane orchestrates public service interfaces

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: C3 has deterministic recomputation but the existing full-chain adapter is still sealed.

### P-01 — full chain gap
- captured_at: 2026-10-30
- command: `git rev-parse HEAD; rg -n '^class ComparisonStageRunAdapter' src/auditmanager/bootstrap/adapters.py`
- captured_output:
  ```text
  74aa1928446a9fe5eb222adfb7ff69c014422690
  7193:class ComparisonStageRunAdapter(_StagesModuleGate):
  ```
- interpretation: new runtime is isolated until root integrates its wiring after C4 seal.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/stage_run/**`
- `tests/unit/comparison/stage_run/**`
- `tests/integration/comparison/stage_run/**`
- `docs/program/tasks/CMP-STAGE-RUN-01.md`
- `docs/program/CMP-STAGE-RUN-01.md`
- `.venv`
- `.env`

## Lane resources
- foundation_instance: `auditmanager-cmp-stage-run-01`
- postgres_port: `58060`
- s3_api_port: `62060`
- s3_console_port: `62061`
- postgres_db: `auditmanager_cmp_stage_run_01`
- s3_bucket: `auditmanager-cmp-stage-run-01`

## Forbidden hotspots
- contract/migration/shared wiring, root dependencies/locks, global styles, unrelated services and remote refs

## Non-goals
- no provider call outside the shared AI runtime; no AI decision becomes an expert verdict
- no heavy gate/window or production deployment

## Deliverables
- chain lifecycle, batch commands and durable worker handlers with lease fences
- explicit stage pipeline interfaces for AI/repair/review; recorded step receipts and audit acts
- short focused implementation checks and integration report

## Required tests
- focused lifecycle/orchestration tests and compile/whitespace checks
- full gate/heavy windows deferred by the owner's 2026-10-30 instruction

## Integration contract
Root wires this lane after the serial C4 seal. Two-step recomputes remain distinct from full chains; full chains launch deterministic child recomputes by a stable key and yield while those execute. AI requires the shared consent/spend service. Only root publishes dev under CMP-INT-CODE-1030.

## Failure/idempotency/security cases
- replay and one live run; stale input refuses publication; lease loss yields without writing
- cancellation prevents future steps and asks active child work to stop; resume reuses immutable completed receipts
- batch pause stops new launches; failed entries do not erase other entries' progress

## Rollback / feature flag
Comparison stages module gates commands and worker claims. Immutable evidence remains when disabled.

## Handoff
- changed files: see `docs/program/CMP-STAGE-RUN-01.md`
- checks/results: focused PostgreSQL tests PASS (RUN 4; REPAIR 2); compile and whitespace PASS
- contracts: none owned
- known limits: shared adapters/factories and real graphic provider are integrated by root
- integration notes: root owns shared wiring and dev
