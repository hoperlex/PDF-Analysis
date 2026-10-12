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

Create subfolders/classes only when a real use case requires them. Keep internal APIs private by default.
