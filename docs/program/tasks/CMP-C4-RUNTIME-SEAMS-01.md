# Task CMP-C4-RUNTIME-SEAMS-01 — caller-owned AI cancellation

## Outcome
A chain cancellation atomically cancels its shared AI job; safe provider refusal metadata reaches the Stage AI runtime for bounded rate-limit waits and typed auth/quota pauses.

## Depends on
- CMP-SEAL-C4
- CMP-STAGE-AI-01

## Frozen inputs
- API1.13 / migration0042, unchanged
- provider base: `13b17880` Stage AI runtime integrated under CMP-INT-CODE-1030
- existing `ComparisonAiJobService.cancel` opens a separate session, unlike C4 start/resume seams

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: caller-owned start/resume exist and cancel currently uses `_steer` only

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/ai_jobs/service.py`
- `src/auditmanager/comparison/spend/errors.py`
- `src/auditmanager/comparison/spend/caller.py`
- `src/auditmanager/analysis/text/proxy.py`
- `src/auditmanager/executors/http_adapter.py`
- `scripts/recovery/product_purge.py`
- `tests/unit/comparison/spend/**`
- `docs/program/tasks/CMP-C4-RUNTIME-SEAMS-01.md`
- `docs/program/CMP-C4-RUNTIME-SEAMS-01.md`

## Forbidden hotspots
- contracts/migrations/root locks, unrelated shared runtime and remote refs

## Non-goals
- no provider dispatch or heavy gate

## Deliverables
- `cancel_in_session` shared seam, registered internal receipt and safe typed refusal metadata

## Required tests
- focused existing AI command checks; Stage AI recorded cancellation test in its implementation lane
- heavy checks tomorrow per owner

## Integration contract
StageAiRuntime.cancel uses this public seam with caller session; root chain lifecycle remains the transaction owner. Existing cancel() wraps the same operation with its own session.

## Failure/idempotency/security cases
- existing command/role/idempotency validation is reused; no direct job update by the stage runtime

## Rollback / feature flag
Existing module and consent gates remain; additive public seam only.

## Handoff
- changed files: task/report and shared cancellation seam/receipt
- checks/results: shared state edges54 passed; caller64 passed, HTTP adapter29 passed, refusal metadata5 passed
- contracts: none
- known limits: full acceptance deferred
- integration notes: root dev only
