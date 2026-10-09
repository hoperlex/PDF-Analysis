# W53-EXEC-REPAIR-02 — orphan running Run must not mint new authority

Integrator review on 2026-10-09, after EXEC merge
`e210c674b4c6db8904572f939619e20d95625be4`.

The present `_execute_run_body` in `src/auditmanager/runs/executor.py`
allows a Run already in `running` because lease recovery can resume it.
`JobRepository.start_execution` in `src/auditmanager/jobs/repository.py`
then locks that Run and, if no Job exists, creates a new Job and Attempt for
it. The no-Job fallback is needed for legacy **queued** direct callers, but
for an orphan **running** Run it bypasses the required check of the lost
Attempt's provider effects. A caller of `execute_run` could repeat a model
call after an earlier process had spent it. Startup reconciliation takes the
opposite safe path and fails a running Run without a Job.

**Exact repair boundary, with a formal task grant to be dispatched after WEB's
sequential host lane:** in
`src/auditmanager/jobs/repository.py`, allow the absent-Job fallback only
when the locked Run is `queued`. Refuse a running Run with no Job before
creating Job/Attempt/Lease or writing a stage event. Add a DB regression in
`tests/integration/runs/test_w53_execution.py`: seed a running Run with no
Job, call `execute_run` with a counting adapter, assert zero provider calls,
no Job or Attempt creation, and a typed refusal; preserve the existing direct
created/queued caller tests and valid resumed running Job test. No contract,
migration, other runtime path or release file may change. The repair agent
must return a clean branch, exact SHA, six `AGENTS.md` §5 items and final
base-to-HEAD changed-path proof. Integrator reruns focused tests after merge.

This is a narrow safety stop for `execute_run` on an orphan running Run; other
EXEC work and the sealed WEB UI can proceed. No release or full W53 verdict
may claim this case safe until the regression passes.
