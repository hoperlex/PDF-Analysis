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
- captured_at: 2026-10-26
- command: `git grep -n -A 3 -E 'session.commit\(\)|resolve_v3_execution_binding\(|adapter.complete\(' 64cb9f32024d4e206105482cc2daf9a4c30937bb -- src/auditmanager/runs/v3_provider_call.py; git grep -n -E 'def resolve_v3_execution_binding|lock_authority' 64cb9f32024d4e206105482cc2daf9a4c30937bb -- src/auditmanager/runs/v3_execution_binding.py`
- captured_output:
  ```text
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py:102:    session.commit()
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-103-
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-104-
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-105-def _publish_reply(
  --
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py:202:    if resolve_v3_execution_binding(
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-203-        session, authority=authority, registry=registry, jobs=job_repo,
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-204-    ) != prepared.binding:
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-205-        raise _refuse("group_binding_changed_before_intent")
  --
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py:221:    session.commit()  # intent is durable before the first provider effect
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-222-
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-223-    try:
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py:224:        if resolve_v3_execution_binding(
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-225-            session, authority=authority, registry=registry, jobs=job_repo,
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-226-        ) != prepared.binding:
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-227-            raise _refuse("group_binding_changed_before_dispatch")
  --
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py:235:        session.commit()
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-236-        raise
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-237-
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-238-    try:
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py:239:        response = adapter.complete(request)
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-240-    except Exception as error:
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-241-        _record_failure(session, job_repo, authority, model_call_id, error, mode)
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-242-        raise
  --
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py:254:    session.commit()  # answer evidence survives a later identity/CITE refusal
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-255-
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-256-    if (type(response.input_tokens) is not int or response.input_tokens < 0
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-257-            or type(response.output_tokens) is not int or response.output_tokens < 0
  --
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py:274:    if resolve_v3_execution_binding(
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-275-        session, authority=authority, registry=registry, jobs=job_repo,
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-276-    ) != prepared.binding:
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-277-        raise _refuse("group_binding_changed_after_response")
  --
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py:307:    session.commit()
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-308-    return V3ProviderCallReceipt(
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-309-        prepared=prepared, response=response, model_call_id=str(model_call_id),
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_provider_call.py-310-        provider=provider_label, cost_usd=cost_usd, cost_basis=basis,
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_execution_binding.py:74:def resolve_v3_execution_binding(
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_execution_binding.py:80:    lock_authority: bool = True,
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_execution_binding.py:90:    if type(lock_authority) is not bool:
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_execution_binding.py:93:    if lock_authority:
  64cb9f32024d4e206105482cc2daf9a4c30937bb:src/auditmanager/runs/v3_execution_binding.py:137:    if lock_authority:
  ```
- interpretation: Re-captured on 2026-10-26 from base commit 64cb9f32024d4e206105482cc2daf9a4c30937bb with git grep against that tree (not at dispatch time). At the base, v3_provider_call.py records the intent with session.commit() at line 221, then calls resolve_v3_execution_binding at 224-225 with session, authority, registry and jobs but no lock_authority argument, then calls adapter.complete(request) at 239. The only session.commit() between 221 and 239 is at 235, inside the except branch that re-raises (236). resolve_v3_execution_binding (v3_execution_binding.py:74) declares lock_authority: bool = True (80) and takes the locking path when it is true (93), so the call at 224 uses the locked default and no commit separates it from the adapter call on the success path. Not shown: what require_current locks (taken from the task's premise). Dispatch-time record (2026-10-23, quoted from the original section, not re-run): command `rg -n 'session.commit\(\)|resolve_v3_execution_binding\(|adapter.complete\(' src/auditmanager/runs/v3_provider_call.py`; captured_output was a prose summary: `session.commit()` at 221 records intent; `resolve_v3_execution_binding` at 224 checks the group; `adapter.complete(request)` at 239 performs the external call. The resolver defaults to locked authority. Original interpretation: without an explicit nonlocking read, the adapter inherits the post-intent transaction's Lease row lock.

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
