# Task CMP-STAGE-AI-01 — durable consented Stage AI runtime

## Outcome
The full stage-chain caller can estimate and prepare a consented shared AI job in its own transaction, then advance reviewer/classifier/synthesis phases through the shared spend caller with persisted content-key replay and atomic source-bound answers.

## Depends on
- CMP-STAGE-AI-CORE-01

## Frozen inputs
- domain contract: ADR-0025 raw-then-AI stack, durable work/spend and A-9/A-10; `COMPARE-MODULES-PLAN.md` C4
- API contract: C4 `1.13.0`, migration `0042_comparison_stage_review`, with root-owned mutable `stage_ai_unit.progress` fix; immutable source `payload` pins stay frozen
- negotiated C4 storage: `stage_ai_unit`, immutable `stage_ai_review`/`stage_ai_classification`/`stage_ai_synthesis`, `stage_graphic_evidence`; effective revision fallback to the original run revision
- negotiated shared runtime: `stage_review` AiScope with `stage_chain_run_id` and revision preflight metadata, `ComparisonAiJobService.start_in_session`; shared caller owns every provider/spend operation
- base commit: `682d38b6e5de925efd2dab74bca1d604a9190929`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: core is integrated and the sole seal owner is authoring C4 shared seams separately.

### P-01 — isolated runtime base
- captured_at: 2026-10-30
- command: `git rev-parse HEAD; git status --short; test -f src/auditmanager/comparison/stage_ai/reviewer.py; test ! -f src/auditmanager/comparison/stage_ai/runtime.py`
- captured_output:
  ```text
  063c8282feef3cea4e201b08b0db8f13cfd4086a
  ```
- interpretation: this lane adds only its owned runtime; root/seal own shared wiring, scope and migration changes.

### P-02 — serial providers consumed before runtime commit
- captured_at: 2026-10-30
- command: `git rev-parse HEAD; git log -3 --oneline`
- captured_output:
  ```text
  682d38b6e5de925efd2dab74bca1d604a9190929
  682d38b6 merge: consume durable AI progress integration fix
  39f65c8d cmp: persist AI chunk progress separately from frozen source
  6e9cf6d1 merge: classify C4 command receipts for recovery
  ```
- interpretation: root consumed the shared seal and progress fix while preserving this lane's uncommitted owned files; path proof starts after these provider merges.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/stage_ai/**`
- `tests/unit/comparison/stage_ai/**`
- `tests/integration/comparison/stage_ai/**`
- `docs/program/tasks/CMP-STAGE-AI-01.md`
- `docs/program/CMP-STAGE-AI-01.md`
- `.venv`
- `.env`

## Lane resources
- foundation_instance: `auditmanager-cmp-stage-ai-01`
- postgres_port: `58050`
- s3_api_port: `62050`
- s3_console_port: `62051`
- postgres_db: `auditmanager_cmp_stage_ai_01`
- s3_bucket: `auditmanager-cmp-stage-ai-01`

## Forbidden hotspots
- shared `ai_jobs/**`, comparison public/worker registry, adapters/composition, contracts, migrations/head, root dependency/lock files, global styles, raw Stage Text, remote refs

## Non-goals
- no direct provider implementation, separate spend journal or hardcoded model
- no deterministic repair or expert card/verdict persistence; root orchestrates step5 repair and step7 card materialization
- no unverified GRAPHIC proof; absent engine/crop bridge is explicit not_checked

## Deliverables
1. `StageAiRuntime.estimate(revision_id,user_uid)`, caller-owned `prepare(session,run_id,user_uid,consent)` and `resume(session,...)` using shared AI job service.
2. `advance(item,run_id,phase)` for review/classify/synthesize; persisted units and answers, exact source pins and no resend of a saved content key.
3. Whole-group reviewer accept after every bounded chunk is saved; raw differences are retained and classifier/synthesis use immutable evidence IDs.
4. Routed executor from `WorkDependencies.routes`, shared `ComparisonModelCaller`, recorded short tests and report.

## Required tests
- short `pytest tests/unit/comparison/stage_ai`; package compile/whitespace
- assigned short C4 PostgreSQL replay tests if a stack is available after seal
- full gates/heavy windows deferred by the owner's direct 2026-10-30 instruction

## Integration contract
Root creates the run first in the caller transaction, then calls `prepare`; no second connection must read that uncommitted run. Root owns steps1–7 orchestration and invokes review at4, classification at5 before/with repair, synthesis at6 and card materialization at7. The runtime returns counts or typed `Yielded`/`Failed`; pauses stay durable in the shared job and run rows. All source reads use effective link revision when present. Root wires the public adapter/worker only after C4 seal integration.

## Failure/idempotency/security cases
- content-key answer replay sends no provider request; unknown call outcome never retries itself
- lease/run/version/revision mismatch prevents answer publication; a group accepts all chunks or none
- changed route/estimate/ceiling pauses through shared core; resumed consent is checked in caller transaction
- GRAPHIC without a reliable 1↔1 result and crop receipt stays not_checked

## Rollback / feature flag
Module stages off prevents root from scheduling/advancing this runtime. Existing raw/answer rows stay immutable; no migration downgrade.

## Handoff
- changed files: stage_ai runtime/planning/repository/source and package export; scoped unit/SQL tests; this task and runtime report
- commands/results: 36 unit tests PASS; 2 recorded SQL tests PASS on assigned PostgreSQL58050; compile/whitespace PASS
- contracts: none in this lane
- known limits: first runtime candidate leaves D-3 context/unparsed follow-up and real GRAPHIC bridge to explicit subsequent work; no live provider/acceptance claim
- integration notes: root/seal own all shared edits and publication
