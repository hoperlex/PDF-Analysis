# Task CMP-STAGE-TEXT-RECOMPUTE-01 — durable deterministic Stage Text recomputation

## Outcome
An expert's keyed recompute request creates a durable two-step Stage Text run and one comparison work item; a worker reads pinned immutable profiles, stores a complete evidence batch under its lease fence and completes the run, including an explicitly empty result.

## Depends on
- CMP-STAGE-TEXT-READ-01

## Frozen inputs
- domain contract: ADR-0025 A-9; `COMPARE-MODULES-PLAN.md` §1.2/§4
- API contract: `1.12.0`, 204 paths / 230 operations / 570 schemas; sealed recompute POST and `StageChainRun` schema
- migration head: `0041_comparison_stage_core`; `stage_chain_run`, `stage_chain_step`, `comparison_work` and text evidence tables are frozen
- evidence producer/reader: `CMP-STAGE-TEXT-CORE-01`, `-DIFF-01`, `-STORE-01`, `-READ-01`
- base commit: `9fa035029a3422b1c3e63d108fbe8c5fdde5dd8e`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/comparison/public.py`
- enumerator_owner: CMP-STAGE-TEXT-RECOMPUTE-01
- totality_query: `rg -n 'stage_text_recompute_handler|HANDLER_FACTORIES' src/auditmanager/comparison/public.py`

## Captured premise evidence
- premise: recompute remains sealed and the worker handler tuple has no Stage Text kind.

### P-01 — frozen recompute gap
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; rg -n '^class ComparisonStageTextAdapter|^HANDLER_FACTORIES' src/auditmanager/bootstrap/adapters.py src/auditmanager/comparison/public.py`
- captured_output:
  ```text
  9fa035029a3422b1c3e63d108fbe8c5fdde5dd8e
  src/auditmanager/bootstrap/adapters.py:7085:class ComparisonStageTextAdapter(_StagesModuleGate):
  src/auditmanager/comparison/public.py:315:HANDLER_FACTORIES: tuple[HandlerFactory, ...] = (
  ```
- interpretation: this task owns the one worker registry change and a single sealed POST implementation.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/CMP-STAGE-TEXT-RECOMPUTE-01.md`
- `docs/program/CMP-STAGE-TEXT-RECOMPUTE-01.md`
- `docs/program/CURRENT_STATE.md`
- `src/auditmanager/comparison/stage_text/**`
- `src/auditmanager/comparison/public.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `tests/unit/comparison/stage_text/**`
- `tests/unit/comparison/engine/test_handler_unit.py`
- `tests/integration/comparison/stage_text/**`
- `tests/integration/api/test_stage_text_read.py`
- `tests/integration/composition/test_comparison_stage_stub_operations.py`

## Forbidden hotspots
- `contracts/**`, migrations/head, root dependency/lock files, global styles, C2 runtime, C3 pair/link service internals, generated client, deployment and remote refs

## Non-goals
- no full seven-step chain start/cancel, AI, mask UI, reverse-direction hint contract or contract reseal
- no live model call; recompute covers deterministic steps 2 and 3 only

## Deliverables
1. Expert-only keyed command and durable work enqueue in one DB transaction; exact replay and single live run per revision.
2. Worker lease fencing before evidence publication; immutable profile/version/map pins, bounded work and explicit failure state.
3. Completed two-step run seals an empty result; GET reads return a real empty page only after that seal.
4. Unit, DB, API and composition tests for enqueue/replay, worker completion/recovery, module-off and stale revision.

## Required tests
- isolated `0041` PostgreSQL and real HTTP; scoped unit and composition registry; `git diff --check`
- full integrated gate/heavy windows deferred to 2026-10-31 by the owner's 2026-10-30 direct instruction

## Integration contract
`recomputeStageTextEvidence` is served only under `versions,stages`. It creates a `stage_chain_run` with steps 2 and 3, whose `command_record.command_type` is `recompute_stage_text_evidence`; the full seven-step chain remains owned by `CMP-STAGE-RUN-01`. The worker's `stage_text_recompute` kind is registered once in `HANDLER_FACTORIES` and claimed only when the stages module is on. Evidence remains raw and immutable; hints remain recommendations.

## Failure/idempotency/security cases
- one key/payload replays the same run; a reused key with changed payload refuses; another live request for the same revision receives the existing run
- lease loss or map/version change prevents publication; a crash after an evidence commit is safe to retry
- no profile archive, over-budget page count, invalid evidence or failed storage leaves the run explicitly failed without claiming absence

## Rollback / feature flag
`AUDITMANAGER_COMPARISON_MODULES=none`/`versions` leaves POST and worker kind inactive. Existing append-only rows and run records are retained; no schema downgrade.

## Handoff
- changed files: task/report/state, Stage Text recompute/handler/read/store/grouped differences, public registry/adapter wiring and focused unit/DB/HTTP/composition tests
- commands/results: **33 unit passed**, **78 PostgreSQL/HTTP/composition passed**, whitespace clean; no full gate
- contracts: none
- known limits: two deterministic steps only; 512-page/20,000-fragment admission and per-connected-group compute budgets; full chain and UI masks open
- integration notes: merge after read; no remote publication authority
