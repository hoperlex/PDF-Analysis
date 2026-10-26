# `jobs` boundary

AuditRun remains owned by ``auditmanager.runs``. This package owns the durable local
``Job``/``Attempt``/``Lease`` authority and the provider/artifact effect journals introduced by
``W48-DURABLE-01``. The current Attempt's opaque ``execution_token`` is checked under a database
lock inside every publishing transaction. Progress remains a projection, never a status source.

This is not a distributed scheduler. Since `W54-WORKER-01` (`R-105`) the claimant is the local
worker service (`auditmanager.workers`) or, under `EXECUTION_ROLE=all`, the serving process; a
claim made for a worker records its `wrk` identity on the Lease and refuses while that worker's
intake is off. `enqueue`, an unpause and a lease reclaim that requeues `NOTIFY`
`auditmanager_job_wakeup` in the same transaction. There is no remote worker protocol. A lost
Attempt is resumed only when no provider effect of it can have spent: a recorded call never
does (D-150), a live one that may have been sent fails the run with that uncertainty recorded.

One executor connection has at most one active Run (`EXEC-PAR-QUEUE-01`). A Run's connection is the
one its frozen revision belongs to (`audit_run.connection_revision_id`); a Run without one is never
limited. A Run is *active* while its Job is `leased`, `running` or `retry_wait` -- an unreleased
Lease, live or expired, so a killed worker's connection stays busy until the reclaim releases it.
`next_queued_run` skips a Job whose connection is busy and returns the next one in the unchanged
priority-then-age order; the claim takes a transaction-scoped advisory lock on the connection
(before the dispatch-control row), re-checks under it, and a claim that loses raises
`ExecutionNotClaimed` having written nothing.

Create subfolders/classes only when a real use case requires them. Keep internal APIs private by default.
