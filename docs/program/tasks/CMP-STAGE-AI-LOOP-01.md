# Task CMP-STAGE-AI-LOOP-01 — durable bounded context and coverage follow-up

## Outcome
Stage AI can execute one source-bound model context request and one unparsed-record pass per plan, preserving all paid responses and the existing shared consent/spend fences. A paused run can obtain the LEFT estimate needed to renew consent.

## Depends on
- CMP-STAGE-AI-CORE-01

## Frozen inputs
- domain contract: ADR-0025 and COMPARE-MODULES-PLAN D-3; parent explicitly dispatches this immediate follow-up after first runtime candidate
- API contract: C4 `1.13.0`; no transport changes in this lane
- migration head: `0042`, mutable progress added by root `CMP-C4-INT-FIX-01`
- runtime input: `13b17880`, shared caller/start/resume seams already consumed
- base commit: `a9be86595be81003abd60528c6494399aba91c7e`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: parent requires D-3 and paused LEFT estimate after first runtime candidate; root owns graphical bridge and transport wiring separately.

### P-01 — root-owned shared seam consumed before owned follow-up commit
- captured_at: 2026-10-30
- command: `git rev-parse HEAD; git log -3 --oneline`
- captured_output:
  ```text
  a9be86595be81003abd60528c6494399aba91c7e
  a9be8659 merge: consume cancellation and safe provider metadata seams
  e045736f cmp: preserve safe provider refusals and caller-owned cancellation
  d50e2fa9 merge: consume connected stage read and estimate provider
  ```
- interpretation: parent consumed its shared cancel/dispatch provider while preserving the owned dirty loop files; path proof excludes root's changes.

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
- `docs/program/tasks/CMP-STAGE-AI-LOOP-01.md`
- `docs/program/CMP-STAGE-AI-LOOP-01.md`

## Forbidden hotspots
- shared ai_jobs/spend, contracts, migration head, registry/composition, root dependencies/locks, raw deterministic rows, other task/report history and remote refs

## Non-goals
- no arbitrary model-selected filesystem/network/database access
- no extra provider or private spend path; no implicit replay of paid requests
- no expert decisions or raw changes; root owns real graphical bridge

## Deliverables
- bounded context request schema/resolver and durable per-plan main/context/coverage state
- one safe technical retry per plan and retained response history
- durable 429 waits 20/60/120/300/600 seconds, typed quota/auth pauses and caller-owned shared cancellation
- `estimate_resume(run_id,user_uid)` using shared LEFT estimate and current job spend
- focused recorded tests, report and exact SHA handoff

## Required tests
- short Stage AI unit tests and two targeted recorded SQL cases; compile/whitespace
- no full gate, heavy suite or live provider window today under owner's instruction

## Integration contract
Existing constructor/prepare/advance signatures remain compatible. `estimate_resume(*,run_id,user_uid)` returns shared AiEstimate. Parent owns the existing estimate endpoint's optional run query. All follow-up calls use the same shared caller, pinned route/consent and immutable original source IDs/digest. Entire group publishes only after every final chunk validates.

## Failure/idempotency/security cases
- context is read only from current pinned profile fragments, never arbitrary paths or URLs
- unknown/duplicate IDs, oversized requests, repeated context/coverage or invalid final answers fail explicitly
- pause/crash preserves request identity and every returned response; saved content keys never re-send

## Rollback / feature flag
Stages module scheduling flag remains the rollback boundary; persisted paid responses and immutable source/answers remain stored.

## Handoff
- changed files: owned Stage AI loop/runtime/planning/repository, scoped unit/SQL tests, this task and report
- commands/results: 48 unit tests PASS; 5 real recorded SQL tests PASS on PostgreSQL58050; compile/whitespace PASS
- known limits: source-only TEXT context; graphical crops/graphic-only estimate remain explicitly assigned to the subsequent bridge integration; no live provider claim
- integration notes: parent remains sole integrator and publisher
