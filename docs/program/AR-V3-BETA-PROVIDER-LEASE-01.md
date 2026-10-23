# AR-V3-BETA-PROVIDER-LEASE-01 — provider call does not hold the lease lock

The unserved AR v3 dispatch still commits the exact request and effect intent before sending. Its immediate post-intent group/Attempt check now uses the nonlocking reader. The existing locked checks before intent and after response remain; a changed pin before dispatch still records `not_sent`, while an uncertain external call is never silently repeated.

## Verification and handoff

- Task: [AR-V3-BETA-PROVIDER-LEASE-01](tasks/AR-V3-BETA-PROVIDER-LEASE-01.md), frozen from `64cb9f32024d4e206105482cc2daf9a4c30937bb`.
- Changed paths: `src/auditmanager/runs/v3_provider_call.py`, `tests/integration/runs/test_v3_provider_call.py`, this note, task file and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Checks: provider/request focused suite **28 passed**. The fake transaction marks a locked lease and asserts it has been released at `adapter.complete`; intent ordering, changed-pin refusal and response journaling still pass. Python compilation and `git diff --check` passed; handoff follows commit.
- New or changed contracts: none. `resolve_v3_execution_binding(lock_authority=False)` is used only for the post-intent check.
- Risks: PostgreSQL/S3 plus delayed-provider heartbeat acceptance has not run locally. A change after the nonlocking check can race with dispatch; the committed intent and response/effect journal record that possibility for reconciliation. No approved six-set pack or served v3 path exists.
- Integration: pass a separately maintained Attempt heartbeat and do not acquire another lock between the post-intent check and `adapter.complete`. Preserve the response and final call's locked authority checks.
- Rollback: unserved behind the v3 executor guard; no migration.
- Forbidden hotspots: contracts, migration head, root dependencies/lockfiles, composition root, active executor, provider transports, global styles and normative map/source/set data were untouched.
