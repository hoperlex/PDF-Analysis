# Task AR-V3-BETA-COST-REFUSAL-01 — fence v3 spend and preserve refusal reason

## Outcome
A reviewed-pack v3 worker refuses before a new provider effect when the Run's recorded spend has exhausted its configured ceiling, and refuses CITE/terminal publication when its sole completed call exceeded that ceiling or has unknown metered cost. A provider DomainError that escapes before CITE is retained as the v3 Run's terminal reason and screened detail.

## Depends on
- `AR-V3-BETA-EXECUTOR-WIRE-01`

## Frozen inputs
- shared domain/API/analysis/events contract: `1.3.0`, unchanged
- AR v3 beta stage extension: `1.0.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `e4c3ae357e19205d62d7652660aefaa9d0ceecd2`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the v3 worker currently passes directly from a completed call to CITE without consulting the per-Run ceiling, while the generic carrier replaces a provider DomainError with `analysis_failed`
### P-01 — worker and carrier
- captured_at: 2026-10-23
- command: `rg -n 'completed_v3_call|run_v3_cite_stage|terminal_reason=ErrorCode.ANALYSIS_FAILED' src/auditmanager/runs/v3_worker.py src/auditmanager/runs/carrier.py`
- captured_output: worker reads a call before CITE but does not inspect `cost_micros`; carrier `_record_crash` always writes `analysis_failed`.
- interpretation: the completed-call record is the durable cost witness after any recovery, and the exact v3 pair identifies the terminal that should preserve a typed refusal.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/v3_worker.py`
- `src/auditmanager/runs/executor.py`
- `src/auditmanager/runs/carrier.py`
- `tests/integration/runs/test_v3_worker_pipeline.py`
- `tests/integration/runs/test_v3_cost_refusal.py`
- `docs/program/tasks/AR-V3-BETA-COST-REFUSAL-01.md`
- `docs/program/AR-V3-BETA-COST-REFUSAL-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lockfiles, composition root and global styles
- provider transports, normative map/source/set data, product VERSION
- `origin/main`, tag and deployment host

## Non-goals
- Speculative price estimates for models without a measured call cost.
- Installing an unapproved pack, publishing findings or changing the six-Run group API.
- Real PostgreSQL/S3/provider acceptance on this host.

## Deliverables
- One cost check before a new provider effect and again on the canonical completed call before CITE, including recovered and already-saved CITE paths.
- Exact v3 DomainError code/detail in the carrier's failed terminal, preserving the legacy crash rule for other profiles.
- Focused success/refusal tests and result note.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_worker_pipeline.py tests/integration/runs/test_v3_cost_refusal.py tests/integration/runs/test_v3_execution_guard.py -x --tb=short`
- expected: all pass, handoff path check passes; full make gate deferred by R-135.

## Integration contract
The ceiling is the executor's single resolved `ProviderConfig.run_cost_ceiling_usd` for this Run. The worker reads persisted prior spend before dispatch and the sole completed canonical call after dispatch or recovery. Any metered call without a cost amount is unavailable for publication; explicitly unmetered calls remain zero and counted. The carrier records a typed provider/cost refusal only for the exact sealed v3 identity, retaining legacy terminal behavior elsewhere. No second model effect is issued on recovery.

## Failure/idempotency/security cases
- Invalid/nonfinite ceiling, exhausted opening balance, over-ceiling answer or unknown metered amount cannot reach CITE.
- After a process loss following call completion, the same saved amount is checked before any CITE or terminal action.
- A missing/inconsistent completed call cannot turn into a zero-cost success; provider refusal details are screened by the existing terminal repository.

## Rollback / feature flag
Production remains closed by empty trusted-pack registries. Revert this task before pack activation; no migration.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: no approved six-set pack or live provider acceptance
- integration notes: keep the exact v3 guard until pack activation validates the same worker and API pack bytes
