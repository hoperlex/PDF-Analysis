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

A Run admitted on an executor group (`EXEC2-GROUP-RUN-01`, ADR-0026 decisions 12 to 16) is written `binding_state =
'pending'` with **no** connection revision -- which is also what the `environment` source has, so a NULL revision means
"never limited" only for a `frozen_at_start` Run. The claim decides the binding state first. A `pending` Run takes the
dispatch path: it locks, in this order, the worker's intake, the group's row, the member connections' advisory locks in
ascending `connection_id`, then the control row, the Run and the Job; reads each member's facts (current revision equals the
group's snapshot, not archived, served, `ok` probe on the current key, a `pull` runner online, a free unit); re-checks that
the consent still holds; picks the member with the lowest `used / capacity` (ties by the group's persisted rotation); and
writes the connection revision **once**, with `binding_state` `pending` to `bound`, advancing the rotation and journalling
one `executor.run_dispatched` event, all before the commit -- model I/O starts only after it. A claim that finds no member
raises `GroupDispatchWaiting` (an `ExecutionNotClaimed`) having written nothing; the carrier stores why in a transaction of
its own. A `bound` Run is claimed like a `frozen_at_start` one on its bound member, so an Attempt retry never moves and
an `outcome_unknown` is never redispatched.

`next_queued_run` offers a `pending` Run **once**: only while it has no stored wait reason and its group revision has a member
with a free unit (units only; whether that member is online, current, served and probed is the claim's business). The claim that
refuses a Run stores why (`executor_at_capacity`, `runner_offline` or `needs_reconsent`; the carrier writes it in a transaction of
its own), and from then on the hint does not offer the Run, so a Run no member can take never holds the head of the queue or starves
another connection's Run or a comparison item. `refresh_group_waits` (the worker's dispatch loop and the in-process carrier call it
every five seconds, each as a step of its own whose failure never stops the dispatch) walks **every** pending Run in pages (a keyset
on `(created_at, run_id)`) and keeps the reason true: it clears it only when some member has no issue at all, that is, is eligible
in every respect and has a free unit, and otherwise sets or keeps one. It takes a Run's lock (`SKIP LOCKED`) only to write or to end
it, and decides the offline expiry on the locked row. A Run that has waited for `runner_offline` longer than
`AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS` (default 1800) ends with `dependency_unavailable`, `dependency: no_executor_online`.
Waiting for capacity never expires. A Run has no way to renew its cost consent, so a Run whose consent no longer holds ends too:
`analysis_input_invalid`, `stage_id: text_analysis`, `reason: cost_estimate_binding_changed` (the Run path's own refusal for an
approved estimate that no longer binds), with an `executor.group_consent_lapsed` event; the user starts again with a fresh consent.

Only a process that serves the `database` provider source dispatches a group Run (`dispatch_groups`, set by the composition root
from `AUDITMANAGER_PROVIDER_SOURCE`). With it false the hint offers no `pending` Run and the claim refuses one before it takes any
lock or writes anything: an ordinary `ExecutionNotClaimed` without a wait reason, the Run left queued for a worker that can bind it.

Create subfolders/classes only when a real use case requires them. Keep internal APIs private by default.
