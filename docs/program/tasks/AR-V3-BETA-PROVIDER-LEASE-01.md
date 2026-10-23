# Task AR-V3-BETA-PROVIDER-LEASE-01 — release lease lock for provider call

## Outcome
An AR v3 provider call dispatches only after a committed intent and a fresh nonlocking group/Attempt check, allowing the independent lease heartbeat to progress during the external model call.

## Depends on
- `AR-V3-BETA-PROVIDER-JOURNAL-01`
- `AR-V3-BETA-LEASE-PEEK-01`
- `AR-V3-BETA-REQUEST-LEASE-01`

## Frozen inputs
- domain/API/analysis/events contract: `1.2.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `64cb9f32024d4e206105482cc2daf9a4c30937bb`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the post-intent group resolver locks the Attempt immediately before the external adapter call
### P-01 — dispatch boundary
- captured_at: 2026-10-23
- command: `rg -n 'session.commit\(\)|resolve_v3_execution_binding\(|adapter.complete\(' src/auditmanager/runs/v3_provider_call.py`
- captured_output: `session.commit()` at 221 records intent; `resolve_v3_execution_binding` at 224 checks the group; `adapter.complete(request)` at 239 performs the external call. The resolver defaults to locked authority.
- interpretation: without an explicit nonlocking read, the adapter inherits the post-intent transaction's Lease row lock.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/v3_provider_call.py`
- `tests/integration/runs/test_v3_provider_call.py`
- `docs/program/tasks/AR-V3-BETA-PROVIDER-LEASE-01.md`
- `docs/program/AR-V3-BETA-PROVIDER-LEASE-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lockfiles
- composition root, active executor, provider transports, global styles
- normative maps, source corpus and set data

## Non-goals
- Changing the final locked response/call journal, provider adapter, or retry policy.
- Activating served v3 or claiming live provider/heartbeat acceptance.

## Deliverables
- Explicit nonlocking post-intent group/Attempt check and focused lock-order evidence.
- Result note and queue update.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_provider_call.py tests/integration/runs/test_v3_execution_request.py -x --tb=short`
- expected: all passed; handoff exact-path and clean-tree checks pass.

## Integration contract
The provider intent and request/body hashes are committed before the nonlocking pre-dispatch check. A changed group or stale Attempt is recorded as definitely not sent. The adapter runs without a Lease row lock held by this dispatch operation; after its answer, the canonical response/effect and call are written under the existing locked authority fences.

## Failure/idempotency/security cases
- A race after the nonlocking check cannot justify replay: the committed intent is durable, so a lost or uncertain call remains unresolved until reconciliation.
- The no-dispatch refusal remains a durable `not_sent` effect.
- A stale Attempt after dispatch refuses any canonical success during the final locked journal.

## Rollback / feature flag
Unserved behind the v3 executor guard. Revert before activation; no migration.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: live delayed-call heartbeat acceptance remains
- integration notes: no prior authority lock may be held across adapter.complete
