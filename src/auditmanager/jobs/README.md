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

One executor connection serves at most as many **units** at once as its capacity, which is one unless
its current revision says more (`EXEC-PAR-QUEUE-01`, widened by `EXEC2-CAP-01`, ADR-0026 decision 1). A
Run's connection is the one its frozen revision belongs to (`audit_run.connection_revision_id`); a Run
without one takes no lock and no unit and is never limited. A unit is a Run that is *active* -- its Job is
`leased`, `running` or `retry_wait`, an unreleased Lease, live or expired, so a killed worker's connection
keeps its unit until the reclaim releases it -- or a comparison model call in `prepared` or `sent` whose
attempt is still live (`CMP-SPEND-01`). The capacity is `max_active_runs` of the connection's **current**
(highest-numbered) revision; NULL, or no revision, reads as one, and with one the behaviour is exactly the
old single-active-Run rule. A lowered capacity governs new claims only and never stops a Run in flight.

`next_queued_run` skips a Job whose connection already holds as many Runs as its capacity (the Runs this
process has handed to a slot count) and returns the next one in the unchanged priority-then-age order. The
claim takes a transaction-scoped advisory lock on the connection (before the dispatch-control row), counts
the units in use under it, and compares them with the capacity; a claim that loses raises
`ExecutionNotClaimed` having written nothing. The comparison call preparation takes the same lock and asks
the same question (`comparison/spend/repository.py`), so a Run and a call never both take the last unit.

Create subfolders/classes only when a real use case requires them. Keep internal APIs private by default.
