"""Durable Job/Attempt authority and the two external-effect journals.

This is the only writer of ``job``, ``attempt``, ``lease``,
``provider_call_effect`` and ``analysis_artifact_publication``.  The execution token is
never formatted into a message or returned by a public API; it is carried only by the
in-process :class:`AttemptAuthority` and compared for equality while the Job row is
locked by the publishing transaction.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AttemptId, JobId, LeaseId, ModelCallId
from auditmanager.storage.public import BlobDeclaration, BlobId, parse_blob_id
from auditmanager.jobs.events import append_execution_event

_INSERT_JOB = text(
    "INSERT INTO job (job_id, run_id, state) VALUES (:job_id, :run_id, 'queued')"
)
_LOCK_RUN = text("SELECT state FROM audit_run WHERE run_id = :run_id FOR UPDATE")
_LOCK_JOB = text(
    "SELECT job_id, state, current_attempt_id FROM job WHERE run_id = :run_id "
    "FOR UPDATE SKIP LOCKED"
)
_LOCK_JOB_WAIT = text(
    "SELECT job_id, state, current_attempt_id FROM job WHERE run_id = :run_id "
    "FOR UPDATE"
)
#: `EXEC-PAR-QUEUE-01`. The Job states in which a Run is **active**, i.e. executing or owed a
#: release: ``leased`` and ``running`` (an unreleased Lease, live or expired -- an expired one
#: stays active until the reclaim releases it, so a killed worker's connection is not handed to a
#: second Run while the first might still be sending) and ``retry_wait`` (written only inside the
#: reclaim's own transaction, listed so that no committed state of an unfinished Job escapes the
#: definition). ``queued`` is waiting and the other four are terminal. The state machine writes
#: the Lease and the Job state together, so this set and "has an unreleased Lease" agree.
_ACTIVE_JOB_STATES = "('leased', 'running', 'retry_wait')"
#: One connection serves at most as many active units as its capacity -- one unless its current revision
#: says more (`EXEC-PAR-DECISION-01`, ruling 3; `EXEC2-CAP-01`). The
#: connection of a Run is the one its frozen revision belongs to: ``audit_run.connection_revision_id``
#: is written once at INSERT, and a Run with none (the ``environment`` source) is never limited.
#:
#: **A NULL revision means ``environment`` only when ``binding_state`` is ``frozen_at_start``** (`EXEC2-GROUP-RUN-01`,
#: ADR-0026 decision 12). A ``pending`` Run -- admitted on a group, no member chosen yet -- has a NULL revision too, and
#: reading that as "never limited" would run it on no connection at all. The claim therefore decides the binding state
#: first (:meth:`JobRepository._pending_group_revision`): a ``pending`` Run takes the dispatch path, which locks the
#: group and its members and writes the revision once; only a ``frozen_at_start`` or ``bound`` Run reaches this
#: statement, and a ``bound`` one has a revision, so its retry stays on the member it was bound to (decision 16).
_CONNECTION_OF_RUN = text(
    "SELECT rev.connection_id FROM audit_run r "
    "JOIN executor_connection_revision rev ON rev.revision_id = r.connection_revision_id "
    "WHERE r.run_id = :run_id"
)
#: A transaction-scoped advisory lock keyed on the **capacity key** of a connection: the claim's guard, taken before
#: the check and held to the claim's commit. The capacity key is the connection's ``capacity_pool`` when it has one -- a system
#: connection of a host: ``<host_id>:<provider>`` (`HOSTS-BACKEND-01`, ADR-0028 decision 4) -- and its own id otherwise, so every connection
#: of one pool takes the one lock and a connection nobody pooled is locked as it always was. A hash collision only serialises two keys
#: that did not need it; the check below compares the real identity. The comparison mirror
#: (``comparison.spend.repository._LOCK_CONNECTION``) spells the statement the same, and :data:`_LOCK_POOL` takes the same key from a pool.
_LOCK_CONNECTION = text(
    "SELECT pg_advisory_xact_lock(hashtextextended('auditmanager.executor_connection|' || "
    "COALESCE((SELECT capacity_pool FROM executor_connection WHERE connection_id = :connection_id), :connection_id), 0))"
)
#: The same lock taken from a pool (``<host_id>:<provider>``) when no connection is at hand: the claim of a planned run and the cell binding
#: lock every pool a cell might be bound in, **in ascending pool key order** (ADR-0028 decision 15).
_LOCK_POOL = text(
    "SELECT pg_advisory_xact_lock(hashtextextended('auditmanager.executor_connection|' || :pool, 0))"
)
#: The one write that binds a planned Run: ``pending`` -> ``bound`` after every cell has its ``audit_run_cell_binding`` row (the database
#: refuses the move otherwise, ``am_guard_audit_run_frozen``). The Run keeps no group, connection or preset of its own. The wait is over, so it is
#: cleared with it.
_BIND_PLANNED_RUN = text(
    "UPDATE audit_run SET binding_state = 'bound', wait_reason = NULL, waiting_since = NULL, "
    "updated_at = statement_timestamp() "
    "WHERE run_id = :run_id AND binding_state = 'pending' AND stage_plan IS NOT NULL"
)
#: `EXEC2-GROUP-RUN-01` (ADR-0026 decisions 12 to 16). What the claim needs to know of a Run's binding before it takes
#: any lock: the state, and the group revision a ``pending`` Run was admitted on. An unlocked read -- the Run lock comes
#: later, in the claim's order -- so it is read again under that lock (:data:`_RUN_BINDING`) and compared.
_CLAIM_BINDING = text(
    "SELECT binding_state, executor_group_revision_id, stage_plan FROM audit_run WHERE run_id = :run_id"
)
_RUN_BINDING = text(
    "SELECT binding_state, executor_group_revision_id, connection_revision_id FROM audit_run WHERE run_id = :run_id"
)
#: The group's row, locked ``FOR UPDATE`` and read for its rotation: the first lock after the worker's intake (ADR-0026
#: decision 14's order: worker intake, group, member connections ascending, control, Run, Job). It serialises the
#: dispatches of one group and the persisted tie-break rotation they read and advance. Nothing is written by it.
_LOCK_GROUP = text(
    "SELECT rotation_cursor FROM executor_group WHERE group_id = :group_id FOR UPDATE"
)
#: The one write that binds a Run: the connection revision goes NULL -> a member of its group revision in the same
#: statement that moves ``binding_state`` ``pending`` -> ``bound`` (``am_guard_audit_run_frozen`` allows exactly that, once,
#: and ``ck_audit_run_binding_shape`` refuses any other shape). The wait is over, so it is cleared with it.
_BIND_RUN = text(
    "UPDATE audit_run SET connection_revision_id = :revision_id, binding_state = 'bound', "
    "wait_reason = NULL, waiting_since = NULL, updated_at = statement_timestamp() "
    "WHERE run_id = :run_id AND binding_state = 'pending' AND connection_revision_id IS NULL"
)
#: Durable waiting (decision 15). ``wait_reason`` is written only when it changes -- ``waiting_since`` is when the Run began
#: waiting for *this* reason, so an unchanged reason keeps its clock -- and is cleared (NULL, NULL) when nothing holds the
#: Run back. Only a Run still ``pending`` and ``queued``; the pair CHECK holds the two columns together.
_WRITE_WAIT = text(
    "UPDATE audit_run SET wait_reason = CAST(:reason AS text), "
    "waiting_since = CASE WHEN CAST(:reason AS text) IS NULL THEN NULL ELSE statement_timestamp() END "
    "WHERE run_id = :run_id AND binding_state = 'pending' AND state = 'queued' "
    "AND wait_reason IS DISTINCT FROM CAST(:reason AS text)"
)
#: The pending Runs the sweep looks at, oldest first, one page at a time. The page is a **keyset** over ``(created_at, run_id)``
#: -- the order and the columns of ``ix_audit_run_pending`` -- so the sweep can walk every pending Run in one pass, however many
#: there are, and no Run stays hidden behind the first ``batch_size``. ``wait_reason`` here is the reading that picks the
#: candidates; what a write or an end decides on is read again under the Run's lock (:data:`_LOCK_PENDING_RUN`).
_PENDING_RUNS = text(
    "SELECT r.run_id, r.executor_group_revision_id AS group_revision_id, r.created_at, r.wait_reason "
    "FROM audit_run r JOIN job j ON j.run_id = r.run_id "
    "WHERE r.binding_state = 'pending' AND r.state = 'queued' AND j.state = 'queued' AND r.stage_plan IS NULL "
    "AND (CAST(:after_run_id AS text) IS NULL "
    "OR (r.created_at, r.run_id) > (CAST(:after_created_at AS timestamptz), CAST(:after_run_id AS text))) "
    "ORDER BY r.created_at, r.run_id LIMIT :batch_size"
)
#: The same page for the **planned** pending Runs (`HOSTS-BACKEND-01`): they have no group revision, and what they wait for is read from the cells
#: of their frozen plan. The keyset is the same ``(created_at, run_id)``.
_PENDING_PLANNED_RUNS = text(
    "SELECT r.run_id, r.stage_plan, r.created_at, r.wait_reason "
    "FROM audit_run r JOIN job j ON j.run_id = r.run_id "
    "WHERE r.binding_state = 'pending' AND r.state = 'queued' AND j.state = 'queued' AND r.stage_plan IS NOT NULL "
    "AND (CAST(:after_run_id AS text) IS NULL "
    "OR (r.created_at, r.run_id) > (CAST(:after_created_at AS timestamptz), CAST(:after_run_id AS text))) "
    "ORDER BY r.created_at, r.run_id LIMIT :batch_size"
)
#: The Run's lock, taken ``SKIP LOCKED`` so a claim in flight is not waited for, answers what the Run holds **now**:
#: its reason, since when, and -- computed on database time from those two locked values -- whether it has waited for
#: that reason longer than ``:offline_seconds``. The offline expiry is decided from this row and from nothing read before
#: the lock: a claim or an earlier sweep may have changed the wait in between.
_LOCK_PENDING_RUN = text(
    "SELECT run_id, wait_reason, waiting_since, "
    "(waiting_since IS NOT NULL "
    "AND waiting_since <= statement_timestamp() - make_interval(secs => :offline_seconds)) AS wait_expired "
    "FROM audit_run WHERE run_id = :run_id AND binding_state = 'pending' AND state = 'queued' "
    "FOR UPDATE SKIP LOCKED"
)
#: `EXEC2-CAP-01` (ADR-0026 decision 1). How many **units** of the connection are in use, and how many it
#: has. A unit is an active Run other than the one being claimed (the Job states of
#: :data:`_ACTIVE_JOB_STATES`) or -- `CMP-SPEND-01` (ADR-0025 decision 4; the grant of the PROD-20 owner) --
#: an active **comparison model call**: a ``prepared`` or ``sent`` row of ``comparison_model_call`` whose
#: attempt still holds its work item (a killed worker's call stays active until the queue's reclaim ends the
#: attempt, the same rule as a Run's expired Lease). Each counts one. The capacity is ``max_active_runs`` of
#: the connection's **current** revision (the highest ``revision_no``), and one when that is NULL (a revision
#: written before the setting) or the connection has no revision, so a connection nobody configured is
#: decided exactly as it was: busy with one unit. The comparison wrapper takes the same advisory lock
#: (:data:`_LOCK_CONNECTION`) before it prepares a call and asks the mirror of this question, so a Run's claim
#: and a comparison call never both pass their check on the last unit. The comparison table is empty while no
#: comparison module is on, so a plain Run is decided by the first count alone.
_CONNECTION_UNITS = text(
    "SELECT ((SELECT count(*) FROM job other_job "
    "JOIN audit_run other ON other.run_id = other_job.run_id "
    "JOIN executor_connection_revision peer ON peer.revision_id = other.connection_revision_id "
    "WHERE peer.connection_id = :connection_id AND other.run_id <> :run_id "
    f"AND other_job.state IN {_ACTIVE_JOB_STATES}) "
    "+ (SELECT count(*) FROM comparison_model_call active_call "
    "JOIN comparison_work_attempt active_attempt "
    "ON active_attempt.comparison_work_attempt_id = active_call.comparison_work_attempt_id "
    "JOIN executor_connection_revision call_peer "
    "ON call_peer.revision_id = active_call.connection_revision_id "
    "WHERE call_peer.connection_id = :connection_id "
    "AND active_call.state IN ('prepared', 'sent') "
    "AND active_attempt.state IN ('created', 'leased', 'running'))) AS units_in_use, "
    "COALESCE((SELECT current_revision.max_active_runs FROM executor_connection_revision current_revision "
    "WHERE current_revision.connection_id = :connection_id "
    "ORDER BY current_revision.revision_no DESC LIMIT 1), 1) AS capacity"
)
#: The dispatcher's hint. ``:submitted`` is the Runs this process has already handed to a slot:
#: they are not offered again, and they count as held units of their connections, because a slot that has
#: not claimed yet has not written its Job state. The hint is advisory -- the claim re-checks under the
#: lock -- but it is what keeps a slot from being spent on a Run whose connection is full: the next Job for
#: a connection with a free unit is the one returned.
#:
#: `EXEC2-CAP-01`: the test is "units held < capacity" (``max_active_runs`` of the connection's current
#: revision, one when absent), where it was "nothing held". ``held`` names each held *Run* (an active Job, or
#: a submitted Run), once -- ``UNION`` removes a submitted Run whose Job is already active -- and ``loaded``
#: counts them per connection. The hint counts Runs only, as it always did; the claim also counts the
#: connection's active comparison calls, so at worst the hint offers a Run the claim then refuses.
#:
#: `EXEC2-GROUP-RUN-01` (ADR-0026 decisions 14 and 15). A **pending** Run (admitted on a group, no connection yet: its revision is
#: NULL, which for the old test below would read "never limited") is offered only when **nothing holds it back** -- its
#: ``wait_reason`` is NULL -- and its group revision has a member with a free unit, the same "units held < capacity" test, per
#: member, over the same ``loaded`` count. That second clause is coarse on purpose: it looks at units only, not at whether the
#: member is online, current, served or probed, which is the claim's business under the locks.
#:
#: The first clause is what keeps a Run the claim will refuse from being offered again and again. A group whose only member
#: with a free unit is offline passes the unit test every poll; offering such a Run on every poll, with the claim refusing it
#: every time, would hold the head of the queue and starve every other Run and every comparison item behind it. So a Run is
#: offered **once**: a freshly admitted Run has no reason yet, the claim that refuses it stores one (``executor_at_capacity``,
#: ``runner_offline`` or ``needs_reconsent``; the carrier writes it in a transaction of its own after the refusal), and from
#: then on the Run is not offered until the sweep (:meth:`JobRepository.refresh_group_waits`) has seen a member that can take
#: it -- eligible in every respect *and* with a free unit -- and cleared the reason. The cost is at most one sweep interval
#: of delay between a unit freeing and the Run being offered. The test is advisory like the rest: the claim decides under
#: the group and member locks, and Runs this process has submitted but not yet claimed do not count against a group (they
#: have no connection until they bind), so a hint may offer two Runs for one free unit and the second claim loses cleanly.
#:
#: ``:dispatch_groups`` is false for a process whose provider source is not ``database`` (`ADR-0026` decision 12: the
#: ``environment`` source never runs a ``pending`` Run, because it has no connection to bind one to). It is then offered
#: no pending Run at all. Every other Run keeps the old shape, to the clause.
#:
#: ``held`` is built from the few active Jobs (the ``ix_job_dispatch`` prefix on ``state``) and the
#: few submitted Runs, never from the history of a connection's Runs: written as a correlated
#: ``NOT EXISTS`` over ``audit_run`` the planner enumerated every Run ever frozen to the connection
#: (5703 buffers against 10, 13.9 ms against 0.1 ms on 20 000 Runs), and that grows with the history.
def _pool_slots_sql(pool: str) -> str:
    """The SQL for the units a pool has (``<host_id>:<provider>``, given as a SQL expression): the latest slot event of the provider on
    the host, else the default of the access the host's current report gives the provider (2 for ``api``, 1 otherwise). The copy
    ``executors.host_repository.pool_slots_sql`` keeps for the executors' reads; a test holds the two equal."""
    host, provider = f"split_part({pool}, ':', 1)", f"split_part({pool}, ':', 2)"
    return (
        f"COALESCE((SELECT slot_event.slots FROM executor_host_slot_event slot_event WHERE slot_event.host_id = {host} "
        f"AND slot_event.provider = {provider} ORDER BY slot_event.event_no DESC LIMIT 1), "
        "(SELECT CASE reported.provider_item ->> 'access' WHEN 'api' THEN 2 ELSE 1 END "
        "FROM (SELECT jsonb_array_elements(host_report.providers) AS provider_item "
        f"FROM executor_host_report host_report WHERE host_report.host_id = {host}) reported "
        f"WHERE reported.provider_item ->> 'provider' = {provider} LIMIT 1), 1)"
    )


#: `HOSTS-BACKEND-01` (ADR-0028 decisions 4 and 5): the stage-plan source. ``held`` also names, **per capacity pool**, each Run whose Job is
#: active (or that this process has submitted) and whose cells are bound in it -- a Run is one unit of a pool however many cells share it, which
#: ``UNION`` gives by naming the pair (pool, run) once. The first column of ``held`` and ``loaded`` is the *capacity key*: a connection id for a
#: Run frozen to a connection, a pool for a planned Run. A **bound planned Run** is offered unless one of its pools has all its slots held; a
#: **pending planned Run** is offered once, while nothing holds it back (no stored wait reason), and the claim decides everything else under the
#: pool locks (the hint is advisory, as it is for a group). Planned Runs are offered only by a process that dispatches them (``dispatch_groups``).
_NEXT_JOB = text(
    "WITH held AS ("
    "SELECT rev.connection_id AS capacity_key, active_job.run_id FROM job active_job "
    "JOIN audit_run active_run ON active_run.run_id = active_job.run_id "
    "JOIN executor_connection_revision rev ON rev.revision_id = active_run.connection_revision_id "
    f"WHERE active_job.state IN {_ACTIVE_JOB_STATES} "
    "UNION "
    "SELECT rev.connection_id, submitted_run.run_id FROM audit_run submitted_run "
    "JOIN executor_connection_revision rev ON rev.revision_id = submitted_run.connection_revision_id "
    "WHERE submitted_run.run_id = ANY (CAST(:submitted AS text[])) "
    "UNION "
    "SELECT pool_connection.capacity_pool, bound_cell.run_id FROM job pool_job "
    "JOIN audit_run_cell_binding bound_cell ON bound_cell.run_id = pool_job.run_id "
    "JOIN executor_connection_revision pool_rev ON pool_rev.revision_id = bound_cell.connection_revision_id "
    "JOIN executor_connection pool_connection ON pool_connection.connection_id = pool_rev.connection_id "
    f"WHERE pool_job.state IN {_ACTIVE_JOB_STATES} "
    "UNION "
    "SELECT pool_connection.capacity_pool, bound_cell.run_id FROM audit_run_cell_binding bound_cell "
    "JOIN executor_connection_revision pool_rev ON pool_rev.revision_id = bound_cell.connection_revision_id "
    "JOIN executor_connection pool_connection ON pool_connection.connection_id = pool_rev.connection_id "
    "WHERE bound_cell.run_id = ANY (CAST(:submitted AS text[]))), "
    "loaded AS (SELECT capacity_key, count(*) AS units FROM held GROUP BY capacity_key) "
    "SELECT j.run_id FROM job j JOIN audit_run r ON r.run_id = j.run_id "
    "WHERE j.state = 'queued' AND r.state IN ('queued', 'running') "
    "AND j.available_at <= statement_timestamp() "
    "AND NOT EXISTS (SELECT 1 FROM execution_control WHERE singleton AND paused) "
    # `EMBED-01` (ADR-0029 decision 8): the night window of the vectors takes no new run, the way the analysis pause takes none. In the
    # same statement, so a claim cannot pass one check and miss the other; `draining` and `encoding` are the two open states
    # (`precedents/vectors/window.py`), and a run that is waiting then is told so by `precedents.public.window_wait`.
    "AND NOT EXISTS (SELECT 1 FROM vector_control WHERE control_key = 'default' AND window_state IN ('draining', 'encoding')) "
    "AND j.run_id <> ALL (CAST(:submitted AS text[])) "
    "AND ("
    # frozen_at_start and bound: the connection test, exactly as it was (a NULL revision is the environment source).
    "(r.stage_plan IS NULL AND r.binding_state <> 'pending' AND NOT EXISTS (SELECT 1 FROM executor_connection_revision mine "
    "JOIN loaded ON loaded.capacity_key = mine.connection_id "
    "WHERE mine.revision_id = r.connection_revision_id "
    "AND loaded.units >= COALESCE((SELECT current_revision.max_active_runs "
    "FROM executor_connection_revision current_revision "
    "WHERE current_revision.connection_id = mine.connection_id "
    "ORDER BY current_revision.revision_no DESC LIMIT 1), 1))) "
    # pending: only when this process dispatches groups, nothing holds the Run back (no stored reason: a Run the claim
    # refused has one, and the sweep clears it when a member could take the Run) and some member of its group revision has
    # a free unit; the claim decides everything else under its locks.
    "OR (r.binding_state = 'pending' "
    "AND CAST(:dispatch_groups AS boolean) "
    "AND r.wait_reason IS NULL "
    "AND EXISTS (SELECT 1 FROM executor_group_member group_member "
    "WHERE group_member.group_revision_id = r.executor_group_revision_id "
    "AND COALESCE((SELECT loaded.units FROM loaded WHERE loaded.capacity_key = group_member.connection_id), 0) "
    "< COALESCE((SELECT current_revision.max_active_runs FROM executor_connection_revision current_revision "
    "WHERE current_revision.connection_id = group_member.connection_id "
    "ORDER BY current_revision.revision_no DESC LIMIT 1), 1))) "
    # a bound planned Run: offered unless one of the pools its cells are bound in has all its slots held (its own unit is not held while
    # its Job is queued, so a retry competes for a free one, as a connection's Run does).
    "OR (r.binding_state = 'bound' AND r.stage_plan IS NOT NULL AND NOT EXISTS ("
    "SELECT 1 FROM audit_run_cell_binding bound_cell "
    "JOIN executor_connection_revision pool_rev ON pool_rev.revision_id = bound_cell.connection_revision_id "
    "JOIN executor_connection pool_connection ON pool_connection.connection_id = pool_rev.connection_id "
    "JOIN loaded ON loaded.capacity_key = pool_connection.capacity_pool "
    f"WHERE bound_cell.run_id = r.run_id AND loaded.units >= {_pool_slots_sql('pool_connection.capacity_pool')})) "
    # a pending planned Run: offered once; the claim binds every cell or stores why not.
    "OR (r.binding_state = 'pending' AND r.stage_plan IS NOT NULL AND CAST(:dispatch_groups AS boolean) "
    "AND r.wait_reason IS NULL)) "
    "ORDER BY j.priority DESC, j.created_at, j.job_id LIMIT 1 "
    "FOR UPDATE OF r SKIP LOCKED"
)
_HEARTBEAT = text(
    "UPDATE lease SET heartbeat_at = statement_timestamp(), "
    "expires_at = statement_timestamp() + make_interval(secs => :lease_seconds) "
    "WHERE lease_id = :lease_id AND attempt_id = :attempt_id "
    "AND released_at IS NULL AND expires_at > statement_timestamp()"
)
#: `W54-WORKER-01` (R-105). One channel wakes every listening worker; the payload is
#: empty because the queue in PostgreSQL is the authority and a notification is a hint.
#: ``NOTIFY`` is transactional, so a worker is woken only after the accepting commit.
JOB_WAKEUP_CHANNEL = "auditmanager_job_wakeup"
_NOTIFY = text("SELECT pg_notify(:channel, '')")
_LOCK_WORKER_INTAKE = text(
    "SELECT intake_enabled FROM worker WHERE worker_id = :worker_id FOR SHARE"
)
_RUNS_HELD = text(
    "SELECT l.worker_id, j.run_id FROM lease l JOIN job j ON j.job_id = l.job_id "
    "WHERE l.worker_id = ANY(:worker_ids) AND l.released_at IS NULL "
    "ORDER BY l.worker_id, l.acquired_at, j.run_id"
)
_EXPIRED_LEASES = text(
    "SELECT j.run_id, j.job_id, a.attempt_id, l.lease_id FROM lease l "
    "JOIN attempt a ON a.attempt_id = l.attempt_id "
    "JOIN job j ON j.job_id = l.job_id WHERE l.released_at IS NULL "
    "AND ((CAST(:force_attempt_id AS text) IS NULL "
    "AND l.expires_at <= statement_timestamp()) "
    "OR (CAST(:force_attempt_id AS text) IS NOT NULL "
    "AND l.attempt_id = :force_attempt_id)) "
    "ORDER BY j.run_id, l.lease_id LIMIT 100"
)
#: `RUN-ROBUSTNESS-01` (D-169). For each Attempt of a Job that was lost, the stage the Run had
#: started last while that Attempt held authority: ``stage.started`` is journalled and committed
#: before a deterministic stage runs (`runs.executor`), so a worker killed inside a stage leaves
#: that stage as the newest start of its Attempt's window. ``NULL`` when the Attempt started no
#: stage (killed before the first one).
_LOST_ATTEMPT_STAGES = text(
    "SELECT a.attempt_id, ("
    "SELECT e.payload ->> 'stage_id' FROM audit_event e "
    "WHERE e.event_type = 'stage.started' AND e.aggregate_id = :run_id "
    "AND e.occurred_at >= a.created_at "
    "AND (a.terminal_at IS NULL OR e.occurred_at <= a.terminal_at) "
    "ORDER BY e.sequence_no DESC LIMIT 1) AS stage_id "
    "FROM attempt a WHERE a.job_id = :job_id AND a.state = 'lost' "
    "ORDER BY a.created_at, a.attempt_id"
)
_ENSURE_CONTROL = text(
    "INSERT INTO execution_control (singleton, paused) VALUES (true, false) "
    "ON CONFLICT (singleton) DO NOTHING"
)
_LOCK_CONTROL = text(
    "SELECT paused FROM execution_control WHERE singleton = true FOR UPDATE"
)
_INSERT_ATTEMPT = text(
    "INSERT INTO attempt (attempt_id, job_id, state, execution_token) "
    "VALUES (:attempt_id, :job_id, 'created', gen_random_uuid()::text) "
    "RETURNING execution_token"
)
_SET_CURRENT = text(
    "UPDATE job SET current_attempt_id = :attempt_id, updated_at = statement_timestamp() "
    "WHERE job_id = :job_id AND state = 'queued'"
)
_INSERT_LEASE = text(
    "INSERT INTO lease (lease_id, job_id, attempt_id, worker_id, expires_at) "
    "VALUES (:lease_id, :job_id, :attempt_id, :worker_id, "
    "statement_timestamp() + make_interval(secs => :lease_seconds))"
)
_ADVANCE_JOB = text(
    "UPDATE job SET state = :to_state, updated_at = statement_timestamp(), "
    "terminal_at = CASE WHEN :terminal THEN statement_timestamp() ELSE NULL END "
    "WHERE job_id = :job_id AND state = :from_state"
)
_ADVANCE_ATTEMPT = text(
    "UPDATE attempt SET state = :to_state, updated_at = statement_timestamp(), "
    "terminal_at = CASE WHEN :terminal THEN statement_timestamp() ELSE NULL END "
    "WHERE attempt_id = :attempt_id AND state = :from_state"
)
_RELEASE_LEASE = text(
    "UPDATE lease SET released_at = statement_timestamp() "
    "WHERE attempt_id = :attempt_id AND released_at IS NULL"
)
_LOCK_AUTHORITY_JOB = text(
    "SELECT run_id, job_id, state AS job_state, current_attempt_id "
    "FROM job WHERE job_id = :job_id FOR UPDATE"
)
_LOCK_AUTHORITY_ATTEMPT = text(
    "SELECT state AS attempt_state, execution_token FROM attempt "
    "WHERE attempt_id = :attempt_id FOR UPDATE"
)
_LOCK_AUTHORITY_LEASE = text(
    "SELECT lease_id, released_at, expires_at, "
    "expires_at > statement_timestamp() AS current FROM lease "
    "WHERE attempt_id = :attempt_id FOR UPDATE"
)
_CHECK_AUTHORITY_UNLOCKED = text(
    "SELECT j.run_id, j.state AS job_state, j.current_attempt_id, "
    "a.state AS attempt_state, a.execution_token, "
    "l.lease_id, l.released_at, "
    "l.expires_at > statement_timestamp() AS lease_current "
    "FROM job j "
    "LEFT JOIN attempt a ON a.job_id = j.job_id AND a.attempt_id = :attempt_id "
    "LEFT JOIN lease l ON l.job_id = j.job_id AND l.attempt_id = a.attempt_id "
    "AND l.lease_id = :lease_id "
    "WHERE j.job_id = :job_id"
)

_INSERT_PROVIDER_EFFECT = text(
    """
    INSERT INTO provider_call_effect (
        model_call_id, run_id, job_id, attempt_id, stage_id, provider,
        model_identity, provider_mode, parameters, request_sha256,
        connection_revision_id, identity_basis, stage_key, host_id, access
    ) VALUES (
        :model_call_id, :run_id, :job_id, :attempt_id, 'text_analysis', :provider,
        :model_identity, :provider_mode, CAST(:parameters AS jsonb), :request_sha256,
        :connection_revision_id, :identity_basis, :stage_key, :host_id, :access
    )
    """
)
_PROVIDER_RESPONSE = text(
    """
    UPDATE provider_call_effect
       SET state = 'response_received', response_sha256 = :response_sha256,
           input_tokens = :input_tokens, output_tokens = :output_tokens,
           latency_ms = :latency_ms, updated_at = statement_timestamp()
     WHERE model_call_id = :model_call_id AND run_id = :run_id
       AND job_id = :job_id AND attempt_id = :attempt_id AND state = 'prepared'
    """
)
_PROVIDER_UNKNOWN = text(
    """
    UPDATE provider_call_effect
       SET state = 'outcome_unknown', error_code = :error_code,
           dispatch_class = 'outcome_unknown',
           updated_at = statement_timestamp()
     WHERE model_call_id = :model_call_id AND run_id = :run_id
       AND job_id = :job_id AND attempt_id = :attempt_id AND state = 'prepared'
    """
)
_PROVIDER_NOT_PROCESSED = text(
    "UPDATE provider_call_effect SET state = 'not_processed', "
    "error_code = :error_code, dispatch_class = :dispatch_class, "
    "updated_at = statement_timestamp() WHERE model_call_id = :model_call_id "
    "AND run_id = :run_id AND job_id = :job_id AND attempt_id = :attempt_id "
    "AND state = 'prepared'"
)
_COMPLETE_PROVIDER = text(
    """
    UPDATE provider_call_effect
       SET state = 'completed', final_model_call_id = model_call_id,
           updated_at = statement_timestamp()
     WHERE model_call_id = :model_call_id AND run_id = :run_id
       AND job_id = :job_id AND attempt_id = :attempt_id
       AND state = 'response_received'
    """
)
_PROVIDER_FOR_COMPLETION = text(
    """
    SELECT connection_revision_id, identity_basis, stage_key, host_id, access FROM provider_call_effect
     WHERE model_call_id = :model_call_id AND run_id = :run_id
       AND job_id = :job_id AND attempt_id = :attempt_id
       AND state = 'response_received'
     FOR UPDATE
    """
)
_EXISTING_RECORDED_STAGE_CALL = text(
    "SELECT EXISTS ("
    "SELECT 1 FROM provider_call_effect WHERE run_id = :run_id "
    "AND stage_id = 'text_analysis' AND state NOT IN ('not_processed', 'abandoned') "
    "UNION ALL SELECT 1 FROM model_call WHERE run_id = :run_id "
    "AND stage_id = 'text_analysis'"
    ")"
)
_RECORDED_COMPLETED_CALLS = text(
    "SELECT m.model_call_id, m.model_identity, m.request_sha256, m.response_sha256, "
    "m.provider, m.provider_mode, m.status, "
    "e.job_id, e.stage_id AS effect_stage, e.state AS effect_state, "
    "e.final_model_call_id, "
    "e.provider AS effect_provider, e.provider_mode AS effect_mode, "
    "e.model_identity AS effect_model, e.request_sha256 AS effect_request, "
    "e.response_sha256 AS effect_response "
    "FROM model_call m LEFT JOIN provider_call_effect e "
    "ON e.run_id = m.run_id AND e.model_call_id = m.model_call_id "
    "WHERE m.run_id = :run_id AND m.stage_id = 'text_analysis'"
)
_V3_COMPLETED_CALLS = text(
    "SELECT m.model_call_id, m.provider, m.model_identity, m.provider_mode, "
    "m.parameters AS call_parameters, m.request_sha256, m.response_sha256, "
    "m.input_tokens, m.output_tokens, m.latency_ms, m.cost_micros, m.cost_basis, "
    "m.status, m.error_code AS call_error, "
    "m.connection_revision_id AS call_revision, m.identity_basis AS call_basis, "
    "e.job_id, e.attempt_id, e.stage_id AS effect_stage, "
    "e.provider AS effect_provider, e.model_identity AS effect_model, "
    "e.provider_mode AS effect_mode, e.parameters AS effect_parameters, "
    "e.request_sha256 AS effect_request, e.response_sha256 AS effect_response, "
    "e.input_tokens AS effect_input_tokens, e.output_tokens AS effect_output_tokens, "
    "e.latency_ms AS effect_latency_ms, e.state AS effect_state, "
    "e.error_code AS effect_error, e.final_model_call_id, "
    "e.connection_revision_id AS effect_revision, e.identity_basis AS effect_basis, "
    "r.state AS run_state, r.provider_mode AS run_mode, "
    "r.connection_revision_id AS run_revision "
    "FROM model_call m LEFT JOIN provider_call_effect e "
    "ON e.run_id = m.run_id AND e.model_call_id = m.model_call_id "
    "JOIN audit_run r ON r.run_id = m.run_id "
    "WHERE m.run_id = :run_id AND m.stage_id = 'text_analysis'"
)
_V3_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_V3_BLOB_ID = re.compile(r"blob_[0-9A-HJKMNP-TV-Z]{26}\Z")
#: `SECTION-CHUNKED-ANALYSIS-01`. The ``model_call.parameters`` keys a finished text window carries
#: (``analysis.text.windows`` writes them; this context may not import that one, and
#: ``tests/unit/analysis/test_text_windows.py`` pins the two spellings together).
_WINDOW_KEY = "text_window_key"
_WINDOW_INDEX = "text_window_index"
_WINDOW_COUNT = "text_window_count"
_WINDOW_FIRST = "text_window_first_page"
_WINDOW_LAST = "text_window_last_page"
_WINDOW_BLOB_ID = "text_window_reply_blob_id"
_WINDOW_BLOB_SHA = "text_window_reply_blob_sha256"
_WINDOW_BLOB_SIZE = "text_window_reply_blob_size"
_WINDOW_CALLS = text(
    "SELECT m.model_call_id, m.provider, m.model_identity, m.provider_mode, "
    "m.parameters AS call_parameters, m.request_sha256, m.response_sha256, "
    "m.input_tokens, m.output_tokens, m.latency_ms, m.cost_micros, m.cost_basis, "
    "m.status, m.error_code AS call_error, "
    "e.job_id, e.attempt_id, e.stage_id AS effect_stage, "
    "e.provider AS effect_provider, e.model_identity AS effect_model, "
    "e.provider_mode AS effect_mode, e.request_sha256 AS effect_request, "
    "e.response_sha256 AS effect_response, e.state AS effect_state, "
    "e.error_code AS effect_error, e.final_model_call_id, "
    "r.provider_mode AS run_mode "
    "FROM model_call m "
    "JOIN provider_call_effect e ON e.run_id = m.run_id AND e.model_call_id = m.model_call_id "
    "JOIN audit_run r ON r.run_id = m.run_id "
    "WHERE m.run_id = :run_id AND m.stage_id = 'text_analysis' "
    f"AND m.parameters ->> '{_WINDOW_KEY}' IS NOT NULL "
    "ORDER BY m.created_at, m.model_call_id"
)
_INSERT_MODEL_CALL = text(
    """
    INSERT INTO model_call (
        model_call_id, run_id, stage_id, provider, model_identity, provider_mode,
        parameters, request_sha256, response_sha256, input_tokens, output_tokens,
        latency_ms, cost_micros, cost_basis, status, error_code,
        connection_revision_id, identity_basis, stage_key, host_id, access
    ) VALUES (
        :model_call_id, :run_id, 'text_analysis', :provider, :model_identity,
        :provider_mode, CAST(:parameters AS jsonb), :request_sha256, :response_sha256,
        :input_tokens, :output_tokens, :latency_ms, :cost_micros, :cost_basis,
        :status, :error_code, :connection_revision_id, :identity_basis,
        :stage_key, :host_id, :access
    )
    """
)

_INSERT_ARTIFACT_INTENT = text(
    """
    INSERT INTO analysis_artifact_publication (
        run_id, job_id, attempt_id, stage_id, blob_id, blob_role
    ) VALUES (
        :run_id, :job_id, :attempt_id, :stage_id, :blob_id, :blob_role
    )
    ON CONFLICT (attempt_id, stage_id, blob_id, blob_role) DO UPDATE
       SET upload_token = analysis_artifact_publication.upload_token
    RETURNING upload_token
    """
)
_BIND_ARTIFACT = text(
    """
    UPDATE analysis_artifact_publication
       SET state = 'bound', artifact_role = :artifact_role,
           bound_at = statement_timestamp()
     WHERE run_id = :run_id AND job_id = :job_id AND attempt_id = :attempt_id
       AND stage_id = :stage_id AND blob_id = :blob_id AND state = 'prepared'
    """
)
_UNRESOLVED_PROVIDER_EFFECTS = text(
    """
    SELECT model_call_id, run_id, job_id, attempt_id, state, request_sha256,
           response_sha256, error_code
      FROM provider_call_effect
     WHERE state IN ('prepared', 'response_received')
     ORDER BY prepared_at, model_call_id
    """
)
_SETTLE_TERMINAL_PROVIDER_EFFECTS = text(
    """
    WITH candidates AS (
        SELECT effect.model_call_id, effect.state AS previous_state
          FROM provider_call_effect effect
          JOIN attempt execution_attempt
            ON execution_attempt.attempt_id = effect.attempt_id
           AND execution_attempt.job_id = effect.job_id
          JOIN job execution_job
            ON execution_job.job_id = effect.job_id
           AND execution_job.run_id = effect.run_id
          JOIN audit_run run ON run.run_id = effect.run_id
         WHERE effect.state IN ('prepared', 'response_received')
           AND execution_attempt.state IN (
               'succeeded', 'failed', 'superseded', 'lost', 'cancelled'
           )
           AND execution_job.state IN ('succeeded', 'failed', 'cancelled', 'dead_letter')
           AND run.state IN ('published', 'partial', 'failed', 'cancelled')
           AND effect.prepared_at <= statement_timestamp() - CAST(:older_than AS interval)
         ORDER BY effect.prepared_at, effect.model_call_id
         LIMIT :batch_size
         FOR UPDATE OF effect SKIP LOCKED
    )
    UPDATE provider_call_effect effect
       SET state = 'abandoned', error_code = :error_code,
           updated_at = statement_timestamp()
      FROM candidates
     WHERE effect.model_call_id = candidates.model_call_id
    RETURNING effect.model_call_id, effect.run_id, effect.job_id, effect.attempt_id,
              candidates.previous_state, effect.state
    """
)
#: `D-142`: an Attempt-scoped artifact intent whose Attempt is terminal can never be
#: bound (``bind_artifacts`` requires the current authority), so it is settled
#: ``prepared -> abandoned``. The blob row is never touched: its identity is
#: content-derived, and a rerun of the same version re-records and publishes it.
_SETTLE_TERMINAL_ARTIFACT_PUBLICATIONS = text(
    """
    WITH candidates AS (
        SELECT publication.attempt_id, publication.stage_id, publication.blob_id,
               publication.blob_role
          FROM analysis_artifact_publication publication
          JOIN attempt execution_attempt
            ON execution_attempt.attempt_id = publication.attempt_id
           AND execution_attempt.job_id = publication.job_id
         WHERE publication.state = 'prepared'
           AND execution_attempt.state IN (
               'succeeded', 'failed', 'superseded', 'lost', 'cancelled'
           )
           AND publication.created_at <= statement_timestamp() - CAST(:older_than AS interval)
         ORDER BY publication.created_at, publication.attempt_id, publication.stage_id,
                  publication.blob_id, publication.blob_role
         LIMIT :batch_size
         FOR UPDATE OF publication SKIP LOCKED
    )
    UPDATE analysis_artifact_publication publication
       SET state = 'abandoned', abandoned_at = statement_timestamp()
      FROM candidates
     WHERE publication.attempt_id = candidates.attempt_id
       AND publication.stage_id = candidates.stage_id
       AND publication.blob_id = candidates.blob_id
       AND publication.blob_role = candidates.blob_role
    RETURNING publication.run_id, publication.attempt_id, publication.stage_id
    """
)

_JOB_TERMINALS = frozenset({"succeeded", "failed", "cancelled", "dead_letter"})
_ATTEMPT_TERMINALS = frozenset({"succeeded", "failed", "superseded", "lost", "cancelled"})


class ExecutionNotClaimed(DomainError):
    """``start_execution`` refused before the caller held any execution authority.

    Raised only by the claim itself: the dispatch pause, a Run or Job that is not
    claimable, or the duplicate-executor guard. No Attempt, Lease or token exists for
    the caller when it is raised, and the caller's transaction still holds every row
    the claim touched. A carrier must therefore leave the Run and its Job as it found
    them; turning this refusal into a crash terminal would destroy a run that this
    process never owned (`W53C-EXEC-01` C-01). The code and details are the original
    refusal's, so an API caller sees the same envelope as before.
    """

    __slots__ = ()


class GroupDispatchWaiting(ExecutionNotClaimed):
    """The claim of a Run admitted on a group found no member to bind it to, and says why (`EXEC2-GROUP-RUN-01`).

    It is an :class:`ExecutionNotClaimed`: nothing was written, no Attempt, Lease or binding exists, and the Run and its
    Job stay as the claim found them. ``wait_reason`` is the controlled word (``executor_at_capacity``,
    ``runner_offline`` or ``needs_reconsent``) a carrier hands to :meth:`JobRepository.record_group_wait` **in a
    transaction of its own**, so the wait is durable although this claim's transaction is rolled back (ADR-0026
    decision 15). Its code and details are those of any other lost claim.
    """

    __slots__ = ("wait_reason",)

    def __init__(self, wait_reason: str) -> None:
        super().__init__(
            ErrorCode.CONFLICT,
            message="the run's executor group has no member that can take it now",
            aggregate_type="ExecutorGroup",
        )
        self.wait_reason = wait_reason


@dataclass(frozen=True, slots=True)
class _Dispatch:
    """The member a pending Run is bound to: decided under the group and connection locks, written once."""

    group_id: str
    connection_id: str
    connection_revision_id: str


@dataclass(frozen=True, slots=True)
class GroupWaits:
    """What one pass of :meth:`JobRepository.refresh_group_waits` did: waits written or cleared, Runs ended.

    ``expired`` is the Runs ended ``no_executor_online`` (every member offline for too long); ``consent_lapsed`` is the Runs ended
    because the cost consent they were accepted under no longer holds (``cost_estimate_binding_changed``)."""

    updated: int = 0
    expired: int = 0
    consent_lapsed: int = 0


#: The words of ``RunQueueReason`` the dispatcher stores. ``executor_at_capacity`` and ``runner_offline`` are the two
#: ``RUN_QUEUE_REASONS`` of ``EXEC2-CAP-01``; ``needs_reconsent`` is the third.
WAIT_AT_CAPACITY = "executor_at_capacity"
WAIT_RUNNER_OFFLINE = "runner_offline"
WAIT_NEEDS_RECONSENT = "needs_reconsent"
#: `HOSTS-BACKEND-01` (ADR-0028 decision 5): a planned Run waits because a cell of its plan has no available server. A run-only word: no comparison
#: job carries it, so ``executors.model.WAIT_REASONS`` (the words both share) does not name it.
WAIT_MODEL_UNAVAILABLE = "model_unavailable"
#: The first reason ``member_issue`` gives for a member that passed every test but has no free unit (the words of
#: ``ExecutorGroupMemberIssue``; ``executors.group_selection`` holds them).
_ISSUE_AT_CAPACITY = "at_capacity"

#: `AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS` (ADR-0026 decision 15, `R-149c`): how long a pending Run whose members are
#: all offline waits before it ends ``no_executor_online``. Thirty minutes unless set. A whole number of seconds, written
#: plainly; anything else is refused, never clamped.
GROUP_OFFLINE_WAIT_ENV = "AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS"
DEFAULT_GROUP_OFFLINE_WAIT_SECONDS = 1800
MAX_GROUP_OFFLINE_WAIT_SECONDS = 7 * 24 * 3600
#: How many pending Runs the sweep reads per page. A pass walks every pending Run, page after page (keyset on
#: ``(created_at, run_id)``), so this bounds one read and never the number of Runs a pass looks at.
GROUP_WAIT_BATCH = 200
#: Why a Run whose cost consent no longer holds ends, in the words of the catalogue that already carries it: the Run path's own
#: refusal for an approved estimate whose binding has changed (``analysis.text.cost.require_approved_model``,
#: ``runs.cost_policy``) -- ``analysis_input_invalid`` with ``stage_id: text_analysis`` and this ``reason``. No code is added.
CONSENT_LAPSED_REASON = "cost_estimate_binding_changed"


def _group_wait_reason(issues: Sequence[str | None]) -> str | None:
    """Why a pending Run cannot be dispatched now, from the first issue of each member of its group revision.

    ``None`` when some member has no issue at all: it can take the Run. ``at_capacity`` is the last test of
    ``member_issue``, so a member with no issue is eligible in every respect (current, not archived, served, probed, a
    runner online) **and** has a free unit; a member that is only free (offline, say) or only eligible (full) does not
    clear a Run's wait. Otherwise a member whose only issue is
    ``at_capacity`` has passed every other test -- it is current, served, probed and online -- so the Run waits for
    **capacity**, which is unbounded (decision 15). When no member got that far, no member is online and serving: the Run
    waits for a **runner** (``runner_offline``), the reason the offline expiry applies to. That includes a group whose
    members were all revised, archived or un-probed since admission -- none of them can take the Run, which for the
    waiting Run is the same as having no executor online."""
    if any(issue is None for issue in issues):
        return None
    if any(issue == _ISSUE_AT_CAPACITY for issue in issues):
        return WAIT_AT_CAPACITY
    return WAIT_RUNNER_OFFLINE


@dataclass(frozen=True, slots=True)
class AttemptAuthority:
    run_id: str
    job_id: str
    attempt_id: str
    lease_id: str
    execution_token: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class RecordedCompletedCall:
    model_call_id: str
    model_id: str
    request_sha256: str
    response_sha256: str


@dataclass(frozen=True, slots=True)
class CompletedWindowCall:
    """One finished text-analysis window of a Run: its call, its effect, and where its reply is kept."""

    key: str
    run_id: str
    job_id: str
    attempt_id: str
    model_call_id: str
    provider: str
    model_id: str
    provider_mode: str
    request_sha256: str
    response_sha256: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_micros: int | None
    cost_basis: str
    status: str
    window_index: int
    window_count: int
    first_page: int
    last_page: int
    reply_blob_id: str
    reply_blob_sha256: str
    reply_blob_size: int


@dataclass(frozen=True, slots=True)
class UnresolvedProviderEffect:
    model_call_id: str
    run_id: str
    job_id: str
    attempt_id: str
    state: str
    request_sha256: str
    response_sha256: str | None
    error_code: str | None


@dataclass(frozen=True, slots=True)
class SettledProviderEffect:
    """One non-repeatable call whose owning execution ended without completion."""

    model_call_id: str
    run_id: str
    job_id: str
    attempt_id: str
    previous_state: str
    state: str


class JobRepository:
    """Create and fence local execution plus journal its external effects.

    ``worker_id`` (`W54-WORKER-01`, R-105) names the registered worker process a claim is
    made for. It is recorded on the Lease, frozen with it, and the claim refuses while
    that worker's intake is switched off. ``None`` is the in-process claimant of
    ``EXECUTION_ROLE=all``, whose Lease names no worker, exactly as before migration 0019.
    """

    #: The lease length, stamped on database time. Sixty seconds is the W53 value (the
    #: 0017 column default); three heartbeats of :data:`jobs.lease.HEARTBEAT_SECONDS` fit
    #: inside it. A class attribute so a test can shorten both the claim and the
    #: extension together without a second code path.
    lease_seconds: float = 60.0

    def __init__(self, *, worker_id: str | None = None, dispatch_groups: bool = True) -> None:
        self._worker_id = worker_id
        #: `EXEC2-GROUP-RUN-01` (ADR-0026 decision 12): ``True`` when this process serves the ``database`` provider source, the
        #: only one that can bind a Run admitted on a group to a connection. The composition root sets it; ``False`` makes the
        #: hint offer no ``pending`` Run and the claim refuse one before it writes anything.
        self._dispatch_groups = dispatch_groups

    @property
    def worker_id(self) -> str | None:
        return self._worker_id

    @property
    def dispatch_groups(self) -> bool:
        return self._dispatch_groups

    def enqueue(self, session: Session, *, run_id: str) -> str:
        """Create the durable Job in the accepting transaction and wake the workers."""
        job_id = str(JobId.new())
        session.execute(_INSERT_JOB, {"job_id": job_id, "run_id": run_id})
        append_execution_event(
            session, event_type="job.created", aggregate_type="Job",
            aggregate_id=job_id, run_id=run_id, payload={"state": "queued"},
        )
        self.wake_workers(session)
        return job_id

    @staticmethod
    def wake_workers(session: Session) -> None:
        """Hint every listening worker, delivered only if the caller's transaction commits."""
        session.execute(_NOTIFY, {"channel": JOB_WAKEUP_CHANNEL})

    def runs_held_by(
        self, session: Session, worker_ids: Sequence[str]
    ) -> dict[str, tuple[str, ...]]:
        """The Runs whose unreleased Lease names each worker, oldest claim first."""
        held: dict[str, list[str]] = {worker_id: [] for worker_id in worker_ids}
        if not worker_ids:
            return {}
        for row in session.execute(_RUNS_HELD, {"worker_ids": list(worker_ids)}).all():
            held.setdefault(str(row[0]), []).append(str(row[1]))
        return {worker_id: tuple(runs) for worker_id, runs in held.items()}

    def next_queued_run(
        self, session: Session, *, submitted: Sequence[str] = (),
    ) -> str | None:
        """Hint the highest runnable Job whose Run is not held by another claimant.

        Only the Run is briefly locked here. Every writer follows Run then Job;
        the worker later makes the authoritative claim under that same order.

        `EXEC-PAR-QUEUE-01`. A Job whose Run is frozen to a connection that already has an
        active Run is skipped, and the next Job in the unchanged priority-then-age order is
        returned instead. ``submitted`` names Runs the caller has handed to a slot and that may
        not have claimed yet: they are neither offered again nor ignored as busy connections.
        Without a connection, or with the default single slot, the order is today's.

        `EXEC2-GROUP-RUN-01`. A Run admitted on a group (``pending``) is offered only while nothing holds it back -- no stored
        wait reason -- and its group has a member with a free unit, and never by a repository built with
        ``dispatch_groups=False`` (:data:`_NEXT_JOB` explains why). A Run the claim refused carries a reason from then on, so
        one Run that no member can take is offered once and does not hold the queue.
        """
        return session.execute(
            _NEXT_JOB, {"submitted": list(submitted), "dispatch_groups": self._dispatch_groups},
        ).scalar_one_or_none()

    def heartbeat(self, session: Session, authority: AttemptAuthority) -> bool:
        """Extend only a live lease, with database time and a bounded lock wait."""
        session.execute(text("SET LOCAL lock_timeout = '2s'"))
        return session.execute(
            _HEARTBEAT,
            {"lease_id": authority.lease_id, "attempt_id": authority.attempt_id,
             "lease_seconds": float(self.lease_seconds)},
        ).rowcount == 1

    def set_priority(self, session: Session, *, job_id: str, priority: int) -> None:
        """Change only a queued Job, under the run-first lock order."""
        if not -100 <= priority <= 100:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="priority", constraint="range")
        run_id = session.execute(text(
            "SELECT run_id FROM job WHERE job_id = :job_id"
        ), {"job_id": job_id}).scalar_one_or_none()
        if run_id is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Job")
        session.execute(_LOCK_RUN, {"run_id": run_id}).scalar_one()
        row = session.execute(text(
            "SELECT state FROM job WHERE job_id = :job_id FOR UPDATE"
        ), {"job_id": job_id}).mappings().one()
        if row["state"] != "queued":
            raise self._transition_error("job", str(row["state"]), "queued")
        session.execute(text(
            "UPDATE job SET priority = :priority, updated_at = statement_timestamp() "
            "WHERE job_id = :job_id"
        ), {"job_id": job_id, "priority": priority})
        append_execution_event(
            session, event_type="job.priority_changed", aggregate_type="Job",
            aggregate_id=job_id, run_id=run_id, payload={"priority": priority},
        )

    def set_paused(self, session: Session, *, paused: bool) -> None:
        session.execute(text(
            "INSERT INTO execution_control (singleton, paused) VALUES (true, :paused) "
            "ON CONFLICT (singleton) DO UPDATE SET paused = EXCLUDED.paused, "
            "changed_at = statement_timestamp()"
        ), {"paused": paused})
        if not paused:
            self.wake_workers(session)

    def reclaim_expired(self, session: Session, *, force_attempt_id: str | None = None) -> int:
        """Fence lost Attempts and resume only when no ambiguous provider effect exists.

        A watchdog passes ``force_attempt_id`` after the fixed execution deadline. It
        fences authority but does not free the caller's in-process worker slot.
        The forced pass considers only its Attempt. Periodic passes take all Run
        locks in one stable order, including when two sweeps overlap.
        """
        from auditmanager.runs.public import fail_reclaimed_run

        session.execute(text("SET LOCAL lock_timeout = '2s'"))
        recovered = 0
        candidates = session.execute(
            _EXPIRED_LEASES, {"force_attempt_id": force_attempt_id}
        ).mappings().all()
        for candidate in candidates:
            run_id = str(candidate["run_id"])
            run_state = session.execute(
                _LOCK_RUN, {"run_id": run_id}
            ).scalar_one_or_none()
            job = session.execute(
                _LOCK_JOB_WAIT, {"run_id": run_id}
            ).mappings().first()
            if job is None or job["current_attempt_id"] != candidate["attempt_id"]:
                continue
            attempt = session.execute(
                _LOCK_AUTHORITY_ATTEMPT, {"attempt_id": candidate["attempt_id"]}
            ).mappings().first()
            lease = session.execute(
                _LOCK_AUTHORITY_LEASE, {"attempt_id": candidate["attempt_id"]}
            ).mappings().first()
            if (attempt is None or lease is None or lease["released_at"] is not None
                    or (lease["current"] and candidate["attempt_id"] != force_attempt_id)):
                continue
            if attempt["attempt_state"] in {"leased", "running"}:
                self._advance_attempt(
                    session, str(candidate["attempt_id"]),
                    str(attempt["attempt_state"]), "lost",
                )
            session.execute(_RELEASE_LEASE, {"attempt_id": candidate["attempt_id"]})
            state = str(job["state"])
            if state not in {"leased", "running"} or run_state not in {"queued", "running"}:
                recovered += 1
                continue
            # D-150 (decided at `W54-FREEZE-01`): a recorded call spends nothing, so a
            # recorded effect the lost Attempt left ``prepared`` is settled
            # ``not_processed`` and no recorded effect makes the Attempt ambiguous.
            # Only a live call that might have been sent fences the run.
            settled_recorded = session.execute(text(
                "UPDATE provider_call_effect SET state = 'not_processed', "
                "error_code = :code, dispatch_class = 'not_sent', "
                "updated_at = statement_timestamp() "
                "WHERE attempt_id = :attempt_id AND state = 'prepared' "
                "AND provider_mode = 'recorded' "
                "RETURNING run_id, attempt_id"
            ), {"attempt_id": candidate["attempt_id"],
                "code": ErrorCode.ANALYSIS_FAILED.value}).mappings().all()
            for effect in settled_recorded:
                append_execution_event(
                    session, event_type="provider.not_processed",
                    aggregate_type="Attempt", aggregate_id=str(effect["attempt_id"]),
                    run_id=str(effect["run_id"]),
                    payload={"attempt_id": str(effect["attempt_id"]),
                             "error_code": ErrorCode.ANALYSIS_FAILED.value,
                             "dispatch_class": "not_sent"},
                )
            # `SECTION-CHUNKED-ANALYSIS-01`: a ``completed`` effect whose ``model_call`` carries a
            # finished text window's saved reply is settled with durable evidence -- the provider
            # answered, the answer is kept, the spend is on the ``model_call`` row -- so it does not
            # make the lost Attempt ambiguous and a run killed *between* windows resumes. A window
            # still ``prepared`` or ``response_received`` stays ambiguous, exactly as a single call.
            ambiguous = bool(session.execute(text(
                "SELECT EXISTS (SELECT 1 FROM provider_call_effect e "
                "WHERE e.attempt_id = :attempt_id AND e.state <> 'not_processed' "
                "AND e.provider_mode <> 'recorded' "
                "AND NOT (e.state = 'completed' AND EXISTS ("
                "SELECT 1 FROM model_call m WHERE m.run_id = e.run_id "
                "AND m.model_call_id = e.final_model_call_id "
                f"AND m.parameters ->> '{_WINDOW_BLOB_ID}' IS NOT NULL)))"
            ), {"attempt_id": candidate["attempt_id"]}).scalar_one())
            count = int(session.execute(text(
                "SELECT count(*) FROM attempt WHERE job_id = :job_id"
            ), {"job_id": candidate["job_id"]}).scalar_one())
            if ambiguous:
                changed_effects = session.execute(text(
                    "UPDATE provider_call_effect SET state = 'outcome_unknown', "
                    "error_code = :code, dispatch_class = 'outcome_unknown', "
                    "updated_at = statement_timestamp() "
                    "WHERE attempt_id = :attempt_id AND state = 'prepared' "
                    "RETURNING run_id, attempt_id"
                ), {"attempt_id": candidate["attempt_id"],
                    "code": ErrorCode.ANALYSIS_FAILED.value}).mappings().all()
                for effect in changed_effects:
                    append_execution_event(
                        session, event_type="provider.outcome_unknown",
                        aggregate_type="Attempt", aggregate_id=str(effect["attempt_id"]),
                        run_id=str(effect["run_id"]),
                        payload={"attempt_id": str(effect["attempt_id"]),
                                 "error_code": ErrorCode.ANALYSIS_FAILED.value,
                                 "dispatch_class": "outcome_unknown"},
                    )
            if ambiguous or count >= 3:
                if state == "running" and not ambiguous:
                    self._advance_job(session, str(candidate["job_id"]), "running", "retry_wait")
                    self._advance_job(session, str(candidate["job_id"]), "retry_wait", "dead_letter")
                else:
                    self._advance_job(session, str(candidate["job_id"]), state, "failed")
                fail_reclaimed_run(
                    session, run_id=run_id, from_state=str(run_state),
                    interrupted_reason=(
                        "provider_outcome_unknown" if ambiguous else "attempt_budget_exhausted"
                    ),
                    # D-169: an exhausted budget names the stage that killed the worker again
                    # and again; an uncertain provider effect keeps the cause it always had.
                    terminal_detail=(
                        None if ambiguous else self._repeated_kill_detail(
                            session, run_id=run_id, job_id=str(candidate["job_id"]),
                        )
                    ),
                )
            else:
                if state == "running":
                    self._advance_job(session, str(candidate["job_id"]), "running", "retry_wait")
                    self._advance_job(session, str(candidate["job_id"]), "retry_wait", "queued")
                else:
                    self._advance_job(session, str(candidate["job_id"]), "leased", "queued")
                session.execute(text(
                    "UPDATE job SET available_at = statement_timestamp() WHERE job_id = :job_id"
                ), {"job_id": candidate["job_id"]})
                self.wake_workers(session)
            recovered += 1
        return recovered

    @staticmethod
    def _repeated_kill_detail(
        session: Session, *, run_id: str, job_id: str
    ) -> dict[str, str] | None:
        """``{"stage_id": ...}`` when the last two lost Attempts died in the same stage.

        `RUN-ROBUSTNESS-01`, D-169. A worker killed for memory is resumed (nothing it did can
        have spent a provider call) and the same pages kill the next one, so the third loss
        dead-letters a Job whose Run then said ``analysis_failed`` and nothing more. Two lost
        Attempts in a row inside the same stage is the signature of an input that kills its
        worker; it is named with the ``stage_id`` detail the code ``analysis_failed`` already
        declares safe. Attempts lost in different stages, or before any stage, are restarts and
        not an input: no stage is named, as before -- a stage the worker merely happened to be
        in is not a cause.
        """
        stages = [
            row["stage_id"] for row in session.execute(
                _LOST_ATTEMPT_STAGES, {"run_id": run_id, "job_id": job_id}
            ).mappings().all()
        ]
        if len(stages) >= 2 and stages[-1] is not None and stages[-1] == stages[-2]:
            return {"stage_id": str(stages[-1])}
        return None

    def start_execution(self, session: Session, *, run_id: str) -> AttemptAuthority:
        """Claim the Run's Job with a new current Attempt, Lease and token.

        Every catalog refusal raised here precedes the returned authority, so it is
        re-raised as :class:`ExecutionNotClaimed` with its code and details intact.
        """
        try:
            return self._claim(session, run_id=run_id)
        except ExecutionNotClaimed:
            raise
        except DomainError as refusal:
            raise ExecutionNotClaimed(
                refusal.code, message=refusal.custom_message,
                **dict(refusal.detail_fields),
            ) from refusal

    def _claim(self, session: Session, *, run_id: str) -> AttemptAuthority:
        # `EXEC2-GROUP-RUN-01` (ADR-0026 decisions 12 and 14). Whether the Run's executor was frozen at start decides which
        # lock path is taken, so it is read first -- a plain read, no lock. A Run admitted on a group and not yet bound
        # (`pending`) takes the dispatch path below; every other Run takes the connection path it always took.
        #
        # `HOSTS-BACKEND-01` (ADR-0028 decision 5). A Run that froze a ``stage_plan`` is bound **by cell**: it has no group revision and no
        # connection of its own, so neither of the two branches below fits it. ``pending``, it takes the planned dispatch path (every pool its
        # cells might be bound in is locked, in ascending order, and every cell is bound or none is); ``bound``, its retry holds the pools it
        # was bound in. The read is unlocked and read again under the Run lock.
        plan_state, pending_revision, stage_plan = self._claim_view(session, run_id=run_id)
        planned_pending = stage_plan is not None and plan_state == "pending"
        if (pending_revision is not None or planned_pending) and not self._dispatch_groups:
            # A process that does not serve the `database` provider source cannot bind a member (decision 12): the
            # `environment` source would run the Run on its own adapter, or fail it `executor_route_missing` after the claim
            # had bound it. Refused before any lock and any write, so the Run and its Job stay exactly as they are for a
            # worker that can dispatch it. An ordinary refusal: it carries no wait reason, because the Run waits for nothing
            # the dispatcher could name and no one's sweep would ever clear.
            raise DomainError(
                ErrorCode.CONFLICT,
                message="this process does not dispatch runs admitted on an executor group",
                aggregate_type="ExecutorGroup",
            )
        if self._worker_id is not None:
            # R-105. A registered worker claims only while its intake is on. FOR SHARE
            # serialises the claim with `setWorkerIntake`'s row lock, so a switch that
            # commits first is observed here before any Attempt exists.
            intake = session.execute(
                _LOCK_WORKER_INTAKE, {"worker_id": self._worker_id}
            ).scalar_one_or_none()
            if intake is None:
                raise DomainError(
                    ErrorCode.CONFLICT, message="the claiming worker is not registered",
                    aggregate_type="Worker",
                )
            if not intake:
                raise DomainError(
                    ErrorCode.CONFLICT, message="the worker's intake is switched off",
                    aggregate_type="Worker",
                )
        # The dispatch path takes the group row, then every member connection, ascending, and chooses a member under those
        # locks; the connection path takes the connection's lock. Both precede the control row.
        dispatch: _Dispatch | None = None
        planned: tuple[Any, ...] | None = None
        if stage_plan is not None:
            if planned_pending:
                planned = self._select_cells(session, run_id=run_id, stage_plan=stage_plan)
            else:
                self._hold_pool_limits(session, run_id=run_id)
        elif pending_revision is None:
            self._hold_connection_limit(session, run_id=run_id)
        else:
            dispatch = self._select_member(
                session, run_id=run_id, group_revision_id=pending_revision,
            )
        # The singleton must exist before it can be locked. Its insert races with
        # an administrator's upsert safely: whichever transaction commits first
        # is observed by the other before a new Attempt can be created.
        session.execute(_ENSURE_CONTROL)
        if session.execute(_LOCK_CONTROL).scalar_one():
            raise DomainError(
                ErrorCode.CONFLICT, message="execution dispatch is paused",
            )
        # The run is always locked before its Job. This serialises a claim with
        # cancellation, final publication and the recovery sweep.
        run_state = session.execute(_LOCK_RUN, {"run_id": run_id}).scalar_one_or_none()
        if run_state not in ("queued", "running"):
            raise self._transition_error("audit_run", str(run_state), "running")
        if pending_revision is not None:
            # Read under the Run lock: a concurrent claim of this very Run that bound it first leaves it `bound`, and
            # this one must lose -- a Run is bound once.
            self._require_still_pending(session, run_id=run_id, group_revision_id=pending_revision)
        elif planned is not None:
            self._require_still_pending(session, run_id=run_id, group_revision_id=None)
        job = session.execute(_LOCK_JOB, {"run_id": run_id}).mappings().first()
        if job is None:
            # Direct execute_run callers can enqueue a queued Run without the
            # API's accepting transaction. A running Run requires prior Job authority.
            existing = session.execute(
                text("SELECT 1 FROM job WHERE run_id = :run_id"), {"run_id": run_id}
            ).scalar_one_or_none()
            if existing is not None:
                raise self._transition_error("job", "locked", "leased")
            if run_state != "queued":
                raise self._transition_error("audit_run", str(run_state), "queued")
            job_id = self.enqueue(session, run_id=run_id)
        else:
            job_id = str(job["job_id"])
            if job["state"] != "queued":
                raise self._transition_error("job", str(job["state"]), "leased")
        if dispatch is not None:
            # Every lock is held and every check has passed: write the binding (once), advance the group's rotation and
            # journal the dispatch. Model I/O starts only after the caller commits this transaction.
            self._bind(session, run_id=run_id, dispatch=dispatch)
        elif planned is not None:
            # The same for a planned Run: one row per cell, then ``pending`` -> ``bound``, before the Attempt exists.
            self._bind_planned(session, run_id=run_id, bound=planned)
        attempt_id = str(AttemptId.new())
        lease_id = str(LeaseId.new())
        try:
            token = str(session.execute(
                _INSERT_ATTEMPT,
                {"attempt_id": attempt_id, "job_id": job_id},
            ).scalar_one())
            append_execution_event(
                session, event_type="attempt.created", aggregate_type="Attempt",
                aggregate_id=attempt_id, run_id=run_id,
                payload={"job_id": job_id, "state": "created"},
            )
            changed = session.execute(
                _SET_CURRENT,
                {"job_id": job_id, "attempt_id": attempt_id},
            ).rowcount
            if changed != 1:
                raise self._transition_error("job", "queued", "leased")
            session.execute(
                _INSERT_LEASE,
                {"lease_id": lease_id, "job_id": job_id, "attempt_id": attempt_id,
                 "worker_id": self._worker_id,
                 "lease_seconds": float(self.lease_seconds)},
            )
            self._advance_job(session, job_id, "queued", "leased")
            self._advance_attempt(session, attempt_id, "created", "leased")
            self._advance_job(session, job_id, "leased", "running")
            self._advance_attempt(session, attempt_id, "leased", "running")
        except DomainError:
            raise
        except DBAPIError as exc:
            # The uniqueness constraint on job.run_id is the final duplicate-executor
            # guard. Only that exact database category is a conflict: mapping arbitrary
            # driver/schema faults to "already running" would be a silent fallback.
            sqlstate = getattr(exc.orig, "sqlstate", None)
            diagnostic = getattr(exc.orig, "diag", None)
            constraint = getattr(diagnostic, "constraint_name", None)
            if sqlstate == "23505" and constraint == "uq_job_run_id":
                raise DomainError(
                    ErrorCode.CONFLICT,
                    message="the run already has durable execution authority",
                    aggregate_type="Job",
                ) from exc
            raise
        return AttemptAuthority(run_id, job_id, attempt_id, lease_id, token)

    @staticmethod
    def _hold_connection_limit(session: Session, *, run_id: str) -> None:
        """No more units in use per connection than its capacity, decided under a lock the claim keeps.

        `EXEC-PAR-QUEUE-01`, widened by `EXEC2-CAP-01` (ADR-0026 decision 1). Take the connection's advisory
        lock, then count the units in use other than this Run (:data:`_CONNECTION_UNITS`) and compare them
        with the capacity of the connection's current revision. Two claims of one connection queue on the
        lock, and the second reads the first's committed Job state, so with one unit left exactly one of them
        wins; a claim that finds the connection full raises before it has written anything, so its Run and
        Job stay as the caller found them (:class:`ExecutionNotClaimed`). With the default capacity of one
        this is the old "another Run or call is active" check, to the row.

        A lowered capacity governs new claims only: a Run already active keeps its unit and is never
        stopped, and the count simply stays at or above the new capacity until enough of them end.

        This is taken and decided **before** the dispatch-control row is locked. That row's lock
        also happens to serialise every claim, but the connection limit must not depend on a
        lock taken for another purpose: ahead of it the limit is decided by its own lock alone,
        and removing that lock lets two claims both pass the check. Every claim takes the locks
        in one order (worker intake, connection, control, Run, Job), so none waits in a cycle.
        A Run without a connection takes no lock and no unit and is never limited. That is the ``environment``
        source -- a Run whose ``binding_state`` is ``frozen_at_start`` and whose connection revision is NULL
        (`EXEC2-GROUP-RUN-01`, premise P-02). A NULL revision is *also* what a ``pending`` Run has, and that Run must
        never be read as unlimited: :meth:`_claim` sends it down the dispatch path (:meth:`_select_member`) before this
        method is reached, so only a ``frozen_at_start`` or a ``bound`` Run (whose revision is set) arrives here.
        """
        connection_id = session.execute(
            _CONNECTION_OF_RUN, {"run_id": run_id}
        ).scalar_one_or_none()
        if connection_id is None:
            return
        session.execute(_LOCK_CONNECTION, {"connection_id": connection_id})
        units_in_use, capacity = session.execute(
            _CONNECTION_UNITS, {"connection_id": connection_id, "run_id": run_id},
        ).one()
        if units_in_use >= capacity:
            raise DomainError(
                ErrorCode.CONFLICT,
                message="the run's executor connection has no free capacity unit",
                aggregate_type="ExecutorConnection",
            )

    # --- dispatch of a Run admitted on a group (`EXEC2-GROUP-RUN-01`, ADR-0026 decisions 12 to 16) ---------------------

    @staticmethod
    def _pending_group_revision(session: Session, *, run_id: str) -> str | None:
        """The group revision a ``pending`` Run was admitted on, or ``None`` for any other Run.

        ``None`` is what a Run whose executor was frozen at start (an explicit connection, a preset, the route, the
        ``environment`` source) answers, and what a ``bound`` Run answers: both go on to the connection path, and a bound
        Run's retry therefore stays on the member it was bound to (decision 16). An unlocked read; the claim reads it
        again under the Run lock."""
        row = session.execute(_CLAIM_BINDING, {"run_id": run_id}).first()
        if row is None or row[0] != "pending":
            return None
        if row[1] is None:  # the database's shape check forbids it; a Run that says otherwise is not dispatched
            raise DomainError(ErrorCode.INTERNAL_ERROR, message="a pending run has no group revision")
        return str(row[1])

    @staticmethod
    def _claim_view(session: Session, *, run_id: str) -> tuple[str | None, str | None, Mapping[str, Any] | None]:
        """What the claim reads of the Run's binding before any lock, in one statement: ``(binding_state, the group revision a pending Run was
        admitted on, the frozen stage plan)``. The group revision is ``None`` for any Run that is not a ``pending`` group Run (what
        :meth:`_pending_group_revision` answers); the plan is ``None`` for every Run that froze none (`HOSTS-BACKEND-01`: a planned Run is bound by
        cell and has no group). An unlocked read, read again under the Run lock."""
        row = session.execute(_CLAIM_BINDING, {"run_id": run_id}).first()
        if row is None:
            return None, None, None
        plan = row[2] if len(row) > 2 else None
        plan = json.loads(plan) if isinstance(plan, str) else plan
        if row[0] != "pending" or plan is not None:
            return str(row[0]), None, plan
        if row[1] is None:  # the database's shape check forbids it; a Run that says otherwise is not dispatched
            raise DomainError(ErrorCode.INTERNAL_ERROR, message="a pending run has no group revision")
        return str(row[0]), str(row[1]), None

    @staticmethod
    def _require_still_pending(session: Session, *, run_id: str, group_revision_id: str | None) -> None:
        row = session.execute(_RUN_BINDING, {"run_id": run_id}).first()
        if row is None or row[0] != "pending" or row[1] != group_revision_id or row[2] is not None:
            raise JobRepository._transition_error(
                "binding_state", "bound" if row is not None and row[0] == "bound" else "unknown", "bound",
            )

    def _select_member(
        self, session: Session, *, run_id: str, group_revision_id: str,
    ) -> _Dispatch:
        """Choose the member a pending Run is bound to, under the locks of decision 14, or say why none can take it.

        **Lock order** (the order of every claim, so none waits in a cycle): worker intake (taken by the caller), the
        group's row, the member connections' advisory locks in ascending ``connection_id`` -- the very lock the connection
        path and the comparison call preparation take, so a Run bound here and a Run or call counted there never both
        take the last unit -- then, back in :meth:`_claim`, the control row, the Run and the Job. Nothing is written
        until the caller binds: a claim that finds no member raises :class:`GroupDispatchWaiting` having written nothing.

        **Eligibility** is what ``executors.public.member_facts`` and ``member_issue`` say, read *after* the locks: the
        member's current revision is the one the group revision snapshots (a member revised since is ineligible and is
        never adopted), it is not archived, this release serves it, its current key has an ``ok`` probe, a ``pull``
        runner is online, and it has a free unit under decision 1. **Selection** is ``choose``: the lowest
        ``used / capacity``, ties broken by the group's persisted rotation, which the bind advances.

        **Consent** is re-checked under those locks, before any member is read
        (:func:`~auditmanager.runs.cost_policy.group_consent_holds`): the rates of a group revision are an immutable
        snapshot, so what can have changed is whether the approved estimate still holds. If it does not, nothing is bound
        and nothing is called -- ``needs_reconsent``.
        """
        from auditmanager.executors.public import choose, group_revision_of, member_facts, member_issue
        from auditmanager.runs.public import group_consent_holds

        revision = group_revision_of(session, group_revision_id)
        if revision is None:
            raise DomainError(ErrorCode.INTERNAL_ERROR, message="the run's group revision is missing")
        rotation = session.execute(_LOCK_GROUP, {"group_id": revision.group_id}).scalar_one_or_none()
        if rotation is None:
            raise DomainError(ErrorCode.INTERNAL_ERROR, message="the run's group is missing")
        for connection_id in sorted({member.connection_id for member in revision.members}):
            session.execute(_LOCK_CONNECTION, {"connection_id": connection_id})
        if not group_consent_holds(
            session, run_id=run_id, group_revision_id=group_revision_id, pin_id=revision.pin_id,
            billing="unmetered" if revision.billing == "not_metered" else "metered",
        ):
            raise GroupDispatchWaiting(WAIT_NEEDS_RECONSENT)
        facts = member_facts(session, revision)
        issues = [member_issue(fact) for fact in facts]
        candidates = [fact for fact, issue in zip(facts, issues, strict=True)
                      if issue is None or issue == _ISSUE_AT_CAPACITY]
        chosen = choose(
            [fact.as_member() for fact in candidates],
            {fact.connection_id: fact.used for fact in candidates},
            {fact.connection_id: fact.capacity for fact in candidates},
            int(rotation),
        )
        if chosen is None:
            reason = _group_wait_reason(issues)
            if reason is None:  # a member with no issue has a free unit, so `choose` cannot have declined it
                raise DomainError(ErrorCode.INTERNAL_ERROR, message="no member chosen though one is eligible")
            raise GroupDispatchWaiting(reason)
        member = next(item for item in revision.members if item.connection_id == chosen)
        return _Dispatch(revision.group_id, chosen, member.connection_revision_id)

    def _bind(self, session: Session, *, run_id: str, dispatch: _Dispatch) -> None:
        """Write the binding, once, and journal it. The caller holds the Run, the Job, the group and the member locks.

        ``connection_revision_id`` goes NULL -> the member's revision together with ``binding_state`` ``pending`` ->
        ``bound`` in one statement; the database allows exactly that and only to a member of the Run's group revision, so
        a second write, a write to another connection and a write that leaves the Run ``pending`` are all refused by it.
        One ``executor.``-prefixed event carries identities and controlled words only (`jobs.events`'s allowlist)."""
        from auditmanager.executors.public import advance_group_rotation

        changed = session.execute(
            _BIND_RUN, {"run_id": run_id, "revision_id": dispatch.connection_revision_id},
        ).rowcount
        if changed != 1:
            raise self._transition_error("binding_state", "pending", "bound")
        advance_group_rotation(session, dispatch.group_id)
        append_execution_event(
            session, event_type="executor.run_dispatched", aggregate_type="AuditRun",
            aggregate_id=run_id, run_id=run_id,
            payload={
                "connection_id": dispatch.connection_id, "revision_id": dispatch.connection_revision_id,
                "work_kind": "text_analysis", "from_state": "pending", "to_state": "bound",
                "reason": "least_loaded",
            },
        )

    # --- dispatch of a planned Run (`HOSTS-BACKEND-01`, ADR-0028 decisions 4, 5 and 15) ---------------------------------------------

    @staticmethod
    def _select_cells(session: Session, *, run_id: str, stage_plan: Mapping[str, Any]) -> tuple[Any, ...]:
        """Decide the binding of **every** cell of a pending planned Run under the pool locks, or say why not. Writes nothing.

        **Lock order** (ADR-0028 decision 15): worker intake (the caller), the pools every cell *might* be bound in, in ascending pool key
        -- the very lock a system connection's ``_LOCK_CONNECTION`` and a comparison call take -- then, back in :meth:`_claim`, the control row,
        the Run and the Job. The pools are read without a lock, locked, read again, and what a group revised in between added is locked too (a
        rare race, resolved by the database's deadlock detection and the next poll; never by an unlocked count).

        Every cell is bound or none is. A cell with no available member, or whose pools are full, raises :class:`GroupDispatchWaiting` with the
        run's wait reason (``model_unavailable`` or ``executor_at_capacity``), having written nothing: the Attempt does not exist yet, so waiting spends
        none of the attempt budget."""
        from auditmanager.executors.public import bind_cells, cell_requests, pools_of

        cells = cell_requests(stage_plan)
        locked: set[str] = set()
        while True:
            missing = [pool for pool in pools_of(session, cells) if pool not in locked]
            if not missing:
                break
            for pool in missing:
                session.execute(_LOCK_POOL, {"pool": pool})
                locked.add(pool)
        outcome = bind_cells(session, run_id=run_id, cells=cells)
        if outcome.bound is None:
            assert outcome.reason is not None
            raise GroupDispatchWaiting(outcome.reason)
        return tuple(outcome.bound)

    def _bind_planned(self, session: Session, *, run_id: str, bound: Sequence[Any]) -> None:
        """Write one row of ``audit_run_cell_binding`` per cell (once; the database refuses a second write and a row for a member that does not pin
        the cell's model), then move the Run ``pending`` -> ``bound`` -- which the database allows only when every cell has its row. The caller holds
        the pools, the Run and the Job. One ``executor.``-prefixed event per cell carries identities and controlled words only."""
        from auditmanager.executors.public import write_bindings

        write_bindings(session, run_id=run_id, bound=bound)
        changed = session.execute(_BIND_PLANNED_RUN, {"run_id": run_id}).rowcount
        if changed != 1:
            raise self._transition_error("binding_state", "pending", "bound")
        for item in bound:
            append_execution_event(
                session, event_type="executor.cell_bound", aggregate_type="AuditRun", aggregate_id=run_id, run_id=run_id,
                payload={"cell_key": item.cell_key, "host_id": item.host_id, "connection_id": item.connection_id,
                         "provider": item.provider, "access": item.access, "model_id": item.model_id,
                         "from_state": "pending", "to_state": "bound", "reason": "stage_plan"})

    @staticmethod
    def _hold_pool_limits(session: Session, *, run_id: str) -> None:
        """A bound planned Run's retry: no more units in use per pool than the pool has, decided under the pools' locks.

        The Run keeps its cells' members (decision 16), so the pools are the ones it was bound in: locked in ascending order, then each is counted
        without this Run (a queued Job holds no unit, as for a connection) and compared with its slots. A pool with no free unit refuses the claim
        before anything is written (:class:`ExecutionNotClaimed`), exactly as a full connection does."""
        from auditmanager.executors.public import bound_pools_of_run, pool_has_room

        pools = bound_pools_of_run(session, run_id)
        for pool in pools:
            session.execute(_LOCK_POOL, {"pool": pool})
        for pool in pools:
            if not pool_has_room(session, pool, exclude_run_id=run_id):
                raise DomainError(
                    ErrorCode.CONFLICT, message="a pool of the run's servers has no free capacity unit",
                    aggregate_type="ExecutorHost",
                )

    # --- waiting is durable and visible (ADR-0026 decision 15) ----------------------------------------------------

    @staticmethod
    def group_offline_wait_seconds(environ: Mapping[str, str] | None = None) -> int:
        """:data:`GROUP_OFFLINE_WAIT_ENV`: unset is :data:`DEFAULT_GROUP_OFFLINE_WAIT_SECONDS`; anything else must be a
        whole number of seconds, written plainly (blank included, no sign, no fraction, no exponent), from one second to
        a week. A bad value raises ``ValueError`` -- it is never clamped to the default, which would make the wait
        something nobody wrote."""
        source = os.environ if environ is None else environ
        if GROUP_OFFLINE_WAIT_ENV not in source:
            return DEFAULT_GROUP_OFFLINE_WAIT_SECONDS
        raw = source[GROUP_OFFLINE_WAIT_ENV].strip()
        if not raw.isascii() or not raw.isdigit():
            raise ValueError(
                f"{GROUP_OFFLINE_WAIT_ENV} is {raw!r}; it is a whole number of seconds, written plainly")
        value = int(raw)
        if not 1 <= value <= MAX_GROUP_OFFLINE_WAIT_SECONDS:
            raise ValueError(
                f"{GROUP_OFFLINE_WAIT_ENV} is {value}; it must be between 1 and {MAX_GROUP_OFFLINE_WAIT_SECONDS}")
        return value

    def record_group_wait(self, session: Session, *, run_id: str, reason: str | None) -> bool:
        """Store why a ``pending`` Run is not dispatched, or clear it (``reason=None``). ``True`` when a row changed.

        Idempotent: the same reason again writes nothing and keeps ``waiting_since``, which is when the Run began waiting
        for *this* reason; another reason restarts that clock. Called by a carrier **after** a
        :class:`GroupDispatchWaiting` refusal, in a transaction of its own, and by the sweep. A Run that is no longer
        ``pending`` and ``queued`` is left alone."""
        if reason is not None and reason not in (
            WAIT_AT_CAPACITY, WAIT_RUNNER_OFFLINE, WAIT_NEEDS_RECONSENT, WAIT_MODEL_UNAVAILABLE,
        ):
            raise ValueError("a wait reason is one of the words of RunQueueReason")
        return session.execute(_WRITE_WAIT, {"run_id": run_id, "reason": reason}).rowcount == 1

    def refresh_group_waits(
        self, session: Session, *, offline_wait_seconds: float | None = None, batch_size: int = GROUP_WAIT_BATCH,
    ) -> GroupWaits:
        """Keep the wait of every ``pending`` Run true, and end the ones nobody can serve any more.

        One pass walks **every** pending, queued Run, oldest first, ``batch_size`` of them per read (a keyset on
        ``(created_at, run_id)``, so no Run stays hidden behind the first page). For each, the group revision's members are
        read now and the reason the Run waits is stored:

        * ``needs_reconsent`` is not stored: a Run has no way to renew its consent, so a Run whose consent no longer holds
          **ends** (:meth:`_end_consent_lapsed`) -- ``analysis_input_invalid``, ``cost_estimate_binding_changed`` -- and the
          user starts again with a fresh consent;
        * otherwise the reason is ``executor_at_capacity`` or ``runner_offline``, or **none**: the reason is cleared only when
          some member has no issue at all, that is, is eligible in every respect *and* has a free unit
          (:func:`_group_wait_reason`). A Run any member could take is then offered by the hint; every other Run keeps or gets
          a reason and is not.

        A Run that has waited for ``runner_offline`` for longer than ``offline_wait_seconds`` (default:
        :meth:`group_offline_wait_seconds`) **ends** too: ``no_executor_online``, through the terminal path of the existing
        recovery (the Job is closed, the Run fails). Waiting for capacity never expires.

        A Run is locked (``SKIP LOCKED``, so a claim in flight is not waited for) only when there is something to write or to
        end, and what is decided is decided on the **locked** row: its reason and the time it has waited for it are read
        again under the lock, never taken from the page that named the Run. Read-only toward connections: no group or
        connection lock is taken, because nothing is bound here. The caller commits. Runs in the same group revision share one
        reading of its members."""
        from auditmanager.executors.public import group_revision_of, member_facts, member_issue
        from auditmanager.runs.public import group_consent_holds

        limit = float(self.group_offline_wait_seconds() if offline_wait_seconds is None else offline_wait_seconds)
        if batch_size < 1:
            raise ValueError("a page of pending runs holds at least one")
        readings: dict[str, tuple[Any, list[str | None]]] = {}
        updated = expired = lapsed = 0
        after_created_at: Any = None
        after_run_id: str | None = None
        while True:
            page = session.execute(_PENDING_RUNS, {
                "batch_size": batch_size, "after_created_at": after_created_at, "after_run_id": after_run_id,
            }).mappings().all()
            for row in page:
                run_id = str(row["run_id"])
                after_created_at, after_run_id = row["created_at"], run_id
                group_revision_id = str(row["group_revision_id"])
                if group_revision_id not in readings:
                    revision = group_revision_of(session, group_revision_id)
                    if revision is None:
                        continue
                    readings[group_revision_id] = (
                        revision, [member_issue(fact) for fact in member_facts(session, revision)])
                revision, issues = readings[group_revision_id]
                consent_holds = group_consent_holds(
                    session, run_id=run_id, group_revision_id=group_revision_id, pin_id=revision.pin_id,
                    billing="unmetered" if revision.billing == "not_metered" else "metered",
                )
                reason = _group_wait_reason(issues) if consent_holds else None
                if consent_holds and reason == row["wait_reason"] and reason != WAIT_RUNNER_OFFLINE:
                    continue  # nothing to write and nothing that can end: no lock is held for it
                locked = session.execute(
                    _LOCK_PENDING_RUN, {"run_id": run_id, "offline_seconds": limit},
                ).mappings().first()
                if locked is None:
                    continue
                if not consent_holds:
                    self._end_consent_lapsed(session, run_id=run_id)
                    lapsed += 1
                    continue
                if reason == WAIT_RUNNER_OFFLINE and locked["wait_reason"] == WAIT_RUNNER_OFFLINE and locked["wait_expired"]:
                    self._end_without_executor(session, run_id=run_id)
                    expired += 1
                    continue
                if self.record_group_wait(session, run_id=run_id, reason=reason):
                    updated += 1
            if len(page) < batch_size:
                break
        planned_updated, planned_expired = self._refresh_planned_waits(
            session, limit=limit, batch_size=batch_size)
        return GroupWaits(
            updated=updated + planned_updated, expired=expired + planned_expired, consent_lapsed=lapsed)

    def _refresh_planned_waits(self, session: Session, *, limit: float, batch_size: int) -> tuple[int, int]:
        """The sweep of the **planned** pending Runs (`HOSTS-BACKEND-01`): keep each one's wait true and end the ones no server can serve.

        For each Run, binding is evaluated **now** from the cells of its frozen plan, read-only and without a lock (:func:`~auditmanager.executors.
        cell_binding.evaluate_wait`; the claim re-decides under the pool locks). The wait stored is that evaluation's reason: ``model_unavailable``
        (some cell has no available server), ``executor_at_capacity`` (every cell has one, the pools are full) or **none** -- cleared, so the hint
        offers the Run. A Run that has waited for ``model_unavailable`` longer than ``limit`` seconds **ends** ``no_executor_online`` (`R-149c`)
        through the terminal path the group Runs use. Waiting for capacity never expires. What is decided is decided on the row locked
        ``SKIP LOCKED``: its reason and the time it has waited are read again under the lock."""
        from auditmanager.executors.public import cell_requests, evaluate_wait

        updated = expired = 0
        after_created_at: Any = None
        after_run_id: str | None = None
        while True:
            page = session.execute(_PENDING_PLANNED_RUNS, {
                "batch_size": batch_size, "after_created_at": after_created_at, "after_run_id": after_run_id,
            }).mappings().all()
            for row in page:
                run_id = str(row["run_id"])
                after_created_at, after_run_id = row["created_at"], run_id
                plan = row["stage_plan"]
                outcome = evaluate_wait(
                    session, run_id=run_id, cells=cell_requests(json.loads(plan) if isinstance(plan, str) else plan))
                reason = None if outcome.bound is not None else outcome.reason
                if reason == row["wait_reason"] and reason != WAIT_MODEL_UNAVAILABLE:
                    continue
                locked = session.execute(
                    _LOCK_PENDING_RUN, {"run_id": run_id, "offline_seconds": limit},
                ).mappings().first()
                if locked is None:
                    continue
                if (reason == WAIT_MODEL_UNAVAILABLE and locked["wait_reason"] == WAIT_MODEL_UNAVAILABLE
                        and locked["wait_expired"]):
                    self._end_without_executor(session, run_id=run_id)
                    expired += 1
                    continue
                if self.record_group_wait(session, run_id=run_id, reason=reason):
                    updated += 1
            if len(page) < batch_size:
                return updated, expired

    def _end_without_executor(self, session: Session, *, run_id: str) -> None:
        """End a ``pending`` Run that waited for a runner longer than allowed: ``no_executor_online``.

        The existing terminal path, in lock order (Run, then Job): the queued Job is closed exactly as a failed Run's
        is, and the Run fails with ``dependency_unavailable`` and ``dependency: no_executor_online`` -- the controlled
        word a pull task nobody claimed already carries. No model was called and nothing was charged."""
        from auditmanager.runs.public import fail_run_without_executor

        self._close_for_run(session, run_id=run_id, target="failed")
        fail_run_without_executor(session, run_id=run_id, from_state="queued")
        append_execution_event(
            session, event_type="executor.group_wait_expired", aggregate_type="AuditRun",
            aggregate_id=run_id, run_id=run_id,
            payload={"work_kind": "text_analysis", "reason": "no_executor_online"},
        )

    def _end_consent_lapsed(self, session: Session, *, run_id: str) -> None:
        """End a ``pending`` Run whose cost consent no longer holds: ``analysis_input_invalid``, ``cost_estimate_binding_changed``.

        A Run has no operation that renews its consent (a comparison job has one), so a Run left in ``needs_reconsent`` would
        stay queued for ever with nothing to tell its owner why. It ends instead, through the same terminal path as the
        offline expiry (the queued Job is closed, the Run fails, the wait is cleared) and with the refusal the Run path already
        raises for an approved estimate whose binding has changed (:data:`CONSENT_LAPSED_REASON`): the consent was given for a
        group revision, model, billing and rate that are no longer the ones the Run would be dispatched with. No model was
        called and nothing was charged; the user starts the work again and consents afresh."""
        from auditmanager.runs.public import fail_run_consent_lapsed

        self._close_for_run(session, run_id=run_id, target="failed")
        fail_run_consent_lapsed(session, run_id=run_id, from_state="queued")
        append_execution_event(
            session, event_type="executor.group_consent_lapsed", aggregate_type="AuditRun",
            aggregate_id=run_id, run_id=run_id,
            payload={"work_kind": "text_analysis", "reason": CONSENT_LAPSED_REASON},
        )

    def check_current_unlocked(
        self, session: Session, authority: AttemptAuthority,
    ) -> None:
        """Early read-only check before Blob I/O; never an effect authority fence.

        No row is locked, so a heartbeat can update the lease while a Blob read
        stalls. The caller must later use ``require_current`` in a short final
        transaction and compare the saved inputs before writing or dispatching.
        """
        row = session.execute(_CHECK_AUTHORITY_UNLOCKED, {
            "job_id": authority.job_id,
            "attempt_id": authority.attempt_id,
            "lease_id": authority.lease_id,
        }).mappings().first()
        if (row is None or row["run_id"] != authority.run_id
                or row["current_attempt_id"] != authority.attempt_id):
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")
        token = row["execution_token"]
        if (not isinstance(token, str)
                or not isinstance(authority.execution_token, str)
                or not secrets.compare_digest(token, authority.execution_token)):
            raise DomainError(ErrorCode.EXECUTION_TOKEN_INVALID, aggregate_type="Attempt")
        if (row["job_state"] != "running"
                or row["attempt_state"] != "running"
                or row["lease_id"] != authority.lease_id
                or row["released_at"] is not None
                or row["lease_current"] is not True):
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")

    def require_current(self, session: Session, authority: AttemptAuthority) -> None:
        session.execute(_LOCK_RUN, {"run_id": authority.run_id}).scalar_one_or_none()
        row = session.execute(
            _LOCK_AUTHORITY_JOB, {"job_id": authority.job_id}
        ).mappings().first()
        if row is None or row["run_id"] != authority.run_id:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")
        if row["current_attempt_id"] != authority.attempt_id:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")
        attempt = session.execute(
            _LOCK_AUTHORITY_ATTEMPT, {"attempt_id": authority.attempt_id}
        ).mappings().first()
        lease = session.execute(
            _LOCK_AUTHORITY_LEASE, {"attempt_id": authority.attempt_id}
        ).mappings().first()
        if attempt is None or not secrets.compare_digest(
            str(attempt["execution_token"]), authority.execution_token
        ):
            raise DomainError(ErrorCode.EXECUTION_TOKEN_INVALID, aggregate_type="Attempt")
        if (row["job_state"] != "running" or attempt["attempt_state"] != "running"
                or lease is None or lease["lease_id"] != authority.lease_id
                or lease["released_at"] is not None or not lease["current"]):
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")

    def finish_execution(
        self, session: Session, authority: AttemptAuthority, *, publishes_result: bool
    ) -> None:
        self.require_current(session, authority)
        target = "succeeded" if publishes_result else "failed"
        self._advance_attempt(session, authority.attempt_id, "running", target)
        self._advance_job(session, authority.job_id, "running", target)
        session.execute(_RELEASE_LEASE, {"attempt_id": authority.attempt_id})

    def fail_for_run(self, session: Session, *, run_id: str) -> None:
        self._close_for_run(session, run_id=run_id, target="failed")

    def cancel_for_run(self, session: Session, *, run_id: str) -> None:
        """Fence an accepted run under the run → job → attempt → lease lock order."""
        self._close_for_run(session, run_id=run_id, target="cancelled")

    def _close_for_run(self, session: Session, *, run_id: str, target: str) -> None:
        session.execute(_LOCK_RUN, {"run_id": run_id}).scalar_one_or_none()
        row = session.execute(_LOCK_JOB_WAIT, {"run_id": run_id}).mappings().first()
        if row is None:
            return
        attempt_id = row["current_attempt_id"]
        if attempt_id is not None:
            attempt = session.execute(
                _LOCK_AUTHORITY_ATTEMPT, {"attempt_id": attempt_id}
            ).mappings().one()
            attempt_state = str(attempt["attempt_state"])
            if attempt_state in {"created", "leased", "running"}:
                attempt_target = (
                    "cancelled" if target == "cancelled" or attempt_state == "created"
                    else "lost"
                )
                self._advance_attempt(session, str(attempt_id), attempt_state, attempt_target)
            session.execute(
                _LOCK_AUTHORITY_LEASE, {"attempt_id": attempt_id}
            ).mappings().first()
            session.execute(_RELEASE_LEASE, {"attempt_id": attempt_id})
        job_state = str(row["state"])
        if target == "cancelled" and job_state in {"queued", "leased", "running", "retry_wait"}:
            self._advance_job(session, str(row["job_id"]), job_state, "cancelled")
        elif target == "failed" and job_state in {"leased", "running"}:
            self._advance_job(session, str(row["job_id"]), job_state, "failed")
        elif target == "failed" and job_state == "queued":
            # A queued Job cannot move directly to failed in the sealed graph. The
            # run can be failed by reconciliation while the Job is cancelled.
            self._advance_job(session, str(row["job_id"]), "queued", "cancelled")

    def prepare_provider_call(
        self,
        session: Session,
        authority: AttemptAuthority,
        *,
        provider: str,
        model_identity: str,
        provider_mode: str,
        parameters: Mapping[str, Any],
        request_sha256: str,
        connection_revision_id: str | None = None,
        identity_basis: str | None = None,
        stage_key: str | None = None,
        host_id: str | None = None,
        access: str | None = None,
        cell_key: str | None = None,
    ) -> ModelCallId:
        """Commit the intent of one provider call. With the provider source ``database`` the
        call names the connection revision that serves it and how its model identity is known
        (`EXEC-HTTP-01`); both or neither, as the schema requires. The ``model_call`` row written
        when the call completes carries the same two values.

        ``stage_key``, ``host_id`` and ``access`` (`HOSTS-SEAL-1`, migration ``0062``) are the row of
        the stage layout the call belongs to, the host that serves it (a bare identity, no foreign key)
        and ``subscription`` or ``api``. Each is ``None`` for every existing caller, which writes
        ``NULL``; the ``model_call`` row carries the values the effect recorded.

        ``cell_key`` (`HOSTS-BACKEND-01`) names the cell of a planned run the call is made for: the host and the access of the member the cell was
        **bound to** are read from ``audit_run_cell_binding`` and written to the effect (and so to the call row), and so is the member's connection
        revision with ``identity_basis`` ``declared`` when the caller named neither. A value the caller also passed must equal the binding's: a
        call is journaled on the member that serves it, never on another. ``stage_key`` still arrives from the caller."""
        self.require_current(session, authority)
        if cell_key is not None:
            from auditmanager.executors.public import cell_binding_of

            bound = cell_binding_of(session, authority.run_id, cell_key)
            if bound is None:
                raise DomainError(
                    ErrorCode.INTERNAL_ERROR, message="the cell of this call is not bound to a member", aggregate_type="AuditRun")
            if (host_id is not None and host_id != bound.host_id) or (access is not None and access != bound.access):
                raise DomainError(
                    ErrorCode.INTERNAL_ERROR, message="the call names another host or access than its cell was bound to",
                    aggregate_type="AuditRun")
            host_id, access = bound.host_id, bound.access
            if connection_revision_id is None and identity_basis is None:
                connection_revision_id, identity_basis = bound.connection_revision_id, "declared"
        model_call_id = ModelCallId.new()
        session.execute(
            _INSERT_PROVIDER_EFFECT,
            {
                "model_call_id": str(model_call_id),
                "run_id": authority.run_id,
                "job_id": authority.job_id,
                "attempt_id": authority.attempt_id,
                "provider": provider,
                "model_identity": model_identity,
                "provider_mode": provider_mode,
                "parameters": json.dumps(dict(parameters), sort_keys=True),
                "request_sha256": request_sha256,
                "connection_revision_id": connection_revision_id,
                "identity_basis": identity_basis,
                "stage_key": stage_key,
                "host_id": host_id,
                "access": access,
            },
        )
        append_execution_event(
            session, event_type="provider.prepared", aggregate_type="Attempt",
            aggregate_id=authority.attempt_id, run_id=authority.run_id,
            payload={"attempt_id": authority.attempt_id, "state": "prepared"},
        )
        return model_call_id

    def require_recorded_stage_call_available(
        self, session: Session, authority: AttemptAuthority
    ) -> None:
        """Fence a second recorded text call before its intent can be committed.

        A completed call, a response awaiting completion, or an uncertain effect
        blocks another replay for the same run. A proven ``not_processed`` or
        reconciled ``abandoned`` effect does not fabricate a canonical call.
        The current Attempt lock serialises this read with another claimant.
        """
        self.require_current(session, authority)
        if session.execute(
            _EXISTING_RECORDED_STAGE_CALL, {"run_id": authority.run_id}
        ).scalar_one():
            raise DomainError(
                ErrorCode.CONFLICT,
                message="a text analysis call already has durable evidence for this run",
                aggregate_type="AuditRun",
            )

    def completed_recorded_call(
        self, session: Session, *, run_id: str, job_id: str
    ) -> RecordedCompletedCall:
        """Read the sole completed recorded call for a saved text stage.

        The call can belong to an earlier Attempt after lease recovery. It must
        still belong to this Run and Job, with a completed effect and identical
        immutable request/response facts. This read takes no Lease lock.
        """
        rows = session.execute(_RECORDED_COMPLETED_CALLS, {"run_id": run_id}).mappings().all()
        if len(rows) != 1:
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message="recorded text stage requires exactly one completed model call",
            )
        row = rows[0]
        if (
            row["job_id"] != job_id
            or row["effect_stage"] != "text_analysis"
            or row["effect_state"] != "completed"
            or row["final_model_call_id"] != row["model_call_id"]
            or row["provider"] != "anthropic"
            or row["provider_mode"] != "recorded"
            or row["status"] != "succeeded"
            or row["effect_provider"] != row["provider"]
            or row["effect_mode"] != row["provider_mode"]
            or row["effect_model"] != row["model_identity"]
            or row["effect_request"] != row["request_sha256"]
            or row["effect_response"] != row["response_sha256"]
            or row["response_sha256"] is None
        ):
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message="recorded call and completed effect do not agree",
            )
        return RecordedCompletedCall(
            str(row["model_call_id"]), str(row["model_identity"]),
            str(row["request_sha256"]), str(row["response_sha256"]),
        )

    def completed_window_calls(
        self, session: Session, authority: AttemptAuthority
    ) -> dict[str, CompletedWindowCall]:
        """Every finished text window of this Run, by window key, each call and effect cross-checked.

        A prior Attempt of the same Job may have finished windows before its worker died; the current
        Attempt may consume that immutable evidence and must never call the provider again for it.
        The read is early and unlocked (:meth:`check_current_unlocked`): it authorises no effect, and
        the caller fences the Attempt again before it writes. A row whose call and effect disagree
        with each other or with the Run, a key shared by two calls, or a malformed reference is a
        refusal (``analysis_input_invalid``), never a window that is quietly called again.
        """
        self.check_current_unlocked(session, authority)
        calls: dict[str, CompletedWindowCall] = {}
        for row in session.execute(_WINDOW_CALLS, {"run_id": authority.run_id}).mappings().all():
            call = self._window_call_of(row, authority)
            if call.key in calls:
                raise self._window_refusal("window_call_duplicate")
            calls[call.key] = call
        return calls

    @staticmethod
    def _window_refusal(reason: str) -> DomainError:
        return DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="a saved text window and its completed effect do not agree",
            stage_id="text_analysis", reason=reason,
        )

    def _window_call_of(
        self, row: Mapping[str, Any], authority: AttemptAuthority
    ) -> CompletedWindowCall:
        params = row["call_parameters"]
        if not (
            isinstance(params, Mapping)
            and row["job_id"] == authority.job_id
            and row["effect_stage"] == "text_analysis"
            and row["effect_state"] == "completed"
            and row["final_model_call_id"] == row["model_call_id"]
            and row["call_error"] is None and row["effect_error"] is None
            and row["status"] in {"succeeded", "truncated"}
            and row["provider_mode"] in {"live", "recorded"}
            and row["provider_mode"] == row["effect_mode"] == row["run_mode"]
            and row["provider"] == row["effect_provider"]
            and row["model_identity"] == row["effect_model"]
            and row["request_sha256"] == row["effect_request"]
            and row["response_sha256"] == row["effect_response"]
            and isinstance(row["response_sha256"], str)
            and _V3_SHA256.fullmatch(row["response_sha256"]) is not None
            and isinstance(row["request_sha256"], str)
            and _V3_SHA256.fullmatch(row["request_sha256"]) is not None
            and all(type(row[name]) is int and row[name] >= 0
                    for name in ("input_tokens", "output_tokens", "latency_ms"))
            and row["cost_basis"] in {"measured", "estimated", "unmetered"}
            and (row["cost_micros"] is None
                 or type(row["cost_micros"]) is int and row["cost_micros"] >= 0)
        ):
            raise self._window_refusal("window_call_pair_invalid")
        key = params.get(_WINDOW_KEY)
        index, count = params.get(_WINDOW_INDEX), params.get(_WINDOW_COUNT)
        first, last = params.get(_WINDOW_FIRST), params.get(_WINDOW_LAST)
        blob_id, blob_sha = params.get(_WINDOW_BLOB_ID), params.get(_WINDOW_BLOB_SHA)
        blob_size = params.get(_WINDOW_BLOB_SIZE)
        if not (
            isinstance(key, str) and _V3_SHA256.fullmatch(key) is not None
            and all(type(value) is int for value in (index, count, first, last))
            and 0 <= index < count and 1 <= first <= last
            and isinstance(blob_id, str) and _V3_BLOB_ID.fullmatch(blob_id) is not None
            and isinstance(blob_sha, str) and _V3_SHA256.fullmatch(blob_sha) is not None
            and type(blob_size) is int and blob_size > 0
        ):
            raise self._window_refusal("window_call_reference_invalid")
        return CompletedWindowCall(
            key=key, run_id=authority.run_id, job_id=row["job_id"],
            attempt_id=row["attempt_id"],
            model_call_id=row["model_call_id"], provider=row["provider"],
            model_id=row["model_identity"], provider_mode=row["provider_mode"],
            request_sha256=row["request_sha256"], response_sha256=row["response_sha256"],
            input_tokens=row["input_tokens"], output_tokens=row["output_tokens"],
            latency_ms=row["latency_ms"], cost_micros=row["cost_micros"],
            cost_basis=row["cost_basis"], status=row["status"],
            window_index=index, window_count=count, first_page=first, last_page=last,
            reply_blob_id=blob_id, reply_blob_sha256=blob_sha, reply_blob_size=blob_size,
        )

    def record_provider_response(
        self,
        session: Session,
        authority: AttemptAuthority,
        *,
        model_call_id: ModelCallId,
        response_sha256: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
    ) -> None:
        self.require_current(session, authority)
        changed = session.execute(
            _PROVIDER_RESPONSE,
            {
                "model_call_id": str(model_call_id),
                "run_id": authority.run_id,
                "job_id": authority.job_id,
                "attempt_id": authority.attempt_id,
                "response_sha256": response_sha256,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency_ms,
            },
        ).rowcount
        if changed != 1:
            raise self._transition_error(
                "provider_call_effect", "prepared", "response_received"
            )
        append_execution_event(
            session, event_type="provider.response_received",
            aggregate_type="Attempt", aggregate_id=authority.attempt_id,
            run_id=authority.run_id,
            payload={"attempt_id": authority.attempt_id, "state": "response_received"},
        )

    def record_provider_not_processed(
        self, session: Session, authority: AttemptAuthority, *,
        model_call_id: ModelCallId, error_code: str, dispatch_class: str,
    ) -> None:
        if dispatch_class not in {"not_sent", "rate_limited", "proxy_unavailable", "definite_refusal"}:
            raise ValueError("not_processed requires a proven dispatch class")
        self.require_current(session, authority)
        changed = session.execute(_PROVIDER_NOT_PROCESSED, {
            "model_call_id": str(model_call_id), "run_id": authority.run_id,
            "job_id": authority.job_id, "attempt_id": authority.attempt_id,
            "error_code": error_code, "dispatch_class": dispatch_class,
        }).rowcount
        if changed != 1:
            raise self._transition_error("provider_call_effect", "prepared", "not_processed")
        append_execution_event(
            session, event_type="provider.not_processed",
            aggregate_type="Attempt", aggregate_id=authority.attempt_id,
            run_id=authority.run_id,
            payload={"attempt_id": authority.attempt_id, "error_code": error_code,
                     "dispatch_class": dispatch_class},
        )

    def record_provider_unknown(
        self,
        session: Session,
        authority: AttemptAuthority,
        *,
        model_call_id: ModelCallId,
        error_code: str,
    ) -> None:
        self.require_current(session, authority)
        changed = session.execute(
            _PROVIDER_UNKNOWN,
            {
                "model_call_id": str(model_call_id),
                "run_id": authority.run_id,
                "job_id": authority.job_id,
                "attempt_id": authority.attempt_id,
                "error_code": error_code,
            },
        ).rowcount
        if changed != 1:
            raise self._transition_error(
                "provider_call_effect", "prepared", "outcome_unknown"
            )
        append_execution_event(
            session, event_type="provider.outcome_unknown",
            aggregate_type="Attempt", aggregate_id=authority.attempt_id,
            run_id=authority.run_id,
            payload={"attempt_id": authority.attempt_id, "error_code": error_code,
                     "dispatch_class": "outcome_unknown"},
        )

    def complete_provider_call(
        self,
        session: Session,
        authority: AttemptAuthority,
        *,
        call: Mapping[str, Any],
    ) -> None:
        self.require_current(session, authority)
        ownership = {
            "model_call_id": call["model_call_id"],
            "run_id": authority.run_id,
            "job_id": authority.job_id,
            "attempt_id": authority.attempt_id,
        }
        owned_effect = session.execute(
            _PROVIDER_FOR_COMPLETION, ownership
        ).mappings().first()
        if owned_effect is None:
            raise self._transition_error(
                "provider_call_effect", "response_received", "completed"
            )
        session.execute(
            _INSERT_MODEL_CALL,
            {
                "model_call_id": call["model_call_id"],
                "run_id": authority.run_id,
                "provider": call["provider"],
                "model_identity": call["model_id"],
                "provider_mode": call["provider_mode"],
                "parameters": json.dumps(
                    {**dict(call["parameters"]), "call_status": call["status"]},
                    sort_keys=True,
                ),
                "request_sha256": call["request_sha256"],
                "response_sha256": call["response_sha256"],
                "input_tokens": call["input_tokens"],
                "output_tokens": call["output_tokens"],
                "latency_ms": call["latency_ms"],
                "cost_micros": (
                    None if call["cost_usd"] is None
                    else int(round(float(call["cost_usd"]) * 1_000_000))
                ),
                "cost_basis": call.get("cost_basis", "estimated"),
                "status": call["status"],
                "error_code": (
                    ErrorCode.ANALYSIS_FAILED.value
                    if call["status"] == "failed"
                    else None
                ),
                "connection_revision_id": owned_effect["connection_revision_id"],
                "identity_basis": owned_effect["identity_basis"],
                "stage_key": owned_effect["stage_key"],
                "host_id": owned_effect["host_id"],
                "access": owned_effect["access"],
            },
        )
        changed = session.execute(
            _COMPLETE_PROVIDER,
            ownership,
        ).rowcount
        if changed != 1:
            raise self._transition_error(
                "provider_call_effect", "response_received", "completed"
            )
        append_execution_event(
            session, event_type="provider.completed", aggregate_type="Attempt",
            aggregate_id=authority.attempt_id, run_id=authority.run_id,
            payload={"attempt_id": authority.attempt_id, "state": "completed"},
        )

    def prepare_artifact(
        self,
        session: Session,
        authority: AttemptAuthority,
        *,
        stage_id: str,
        declaration: BlobDeclaration,
    ) -> str:
        self.require_current(session, authority)
        return str(
            session.execute(
                _INSERT_ARTIFACT_INTENT,
                {
                    "run_id": authority.run_id,
                    "job_id": authority.job_id,
                    "attempt_id": authority.attempt_id,
                    "stage_id": stage_id,
                    "blob_id": str(declaration.blob_id),
                    "blob_role": str(declaration.role),
                },
            ).scalar_one()
        )

    def bind_artifacts(
        self,
        session: Session,
        authority: AttemptAuthority,
        *,
        stage_id: str,
        artifacts: Sequence[Any],
    ) -> tuple[BlobId, ...]:
        self.require_current(session, authority)
        bound: list[BlobId] = []
        for artifact in artifacts:
            blob_id = parse_blob_id(str(artifact.blob_id))
            changed = session.execute(
                _BIND_ARTIFACT,
                {
                    "run_id": authority.run_id,
                    "job_id": authority.job_id,
                    "attempt_id": authority.attempt_id,
                    "stage_id": stage_id,
                    "blob_id": str(blob_id),
                    "artifact_role": str(artifact.role),
                },
            ).rowcount
            if changed != 1:
                raise DomainError(
                    ErrorCode.STORAGE_INTEGRITY_ERROR,
                    message="a stage result names an artifact with no current publication intent",
                    blob_id=str(blob_id),
                    role=str(artifact.role),
                )
            bound.append(blob_id)
        return tuple(bound)

    def unresolved_provider_effects(
        self, session: Session
    ) -> tuple[UnresolvedProviderEffect, ...]:
        return tuple(
            UnresolvedProviderEffect(**dict(row))
            for row in session.execute(_UNRESOLVED_PROVIDER_EFFECTS).mappings().all()
        )

    def settle_terminal_provider_effects(
        self,
        session: Session,
        *,
        older_than: str = "1 hour",
        batch_size: int = 100,
    ) -> tuple[SettledProviderEffect, ...]:
        """Bound one reconciliation pass and preserve ambiguous calls as abandoned.

        Only effects owned by a terminal Run, Job and Attempt are eligible.  Both a
        pre-dispatch ``prepared`` row and a durable ``response_received`` row may be
        abandoned: neither is safe to repeat, and neither contains enough evidence to
        invent the immutable canonical ``model_call``.  The previous state remains in
        the returned report while the row retains any response checksum/token counts it
        had already recorded.
        """
        if batch_size < 1:
            raise ValueError("provider effect reconciliation batch_size must be positive")
        rows = session.execute(
            _SETTLE_TERMINAL_PROVIDER_EFFECTS,
            {
                "older_than": older_than,
                "batch_size": batch_size,
                "error_code": ErrorCode.ANALYSIS_FAILED.value,
            },
        ).mappings().all()
        for effect in rows:
            append_execution_event(
                session, event_type="provider.abandoned",
                aggregate_type="Attempt", aggregate_id=str(effect["attempt_id"]),
                run_id=str(effect["run_id"]),
                payload={"attempt_id": str(effect["attempt_id"]),
                         "state": "abandoned"},
            )
        self.settle_terminal_artifact_publications(
            session, older_than=older_than, batch_size=batch_size
        )
        return tuple(SettledProviderEffect(**dict(row)) for row in rows)

    def settle_terminal_artifact_publications(
        self,
        session: Session,
        *,
        older_than: str = "1 hour",
        batch_size: int = 100,
    ) -> int:
        """`D-142`: settle unbound artifact intents of terminal Attempts as ``abandoned``.

        Called by :meth:`settle_terminal_provider_effects`, so every reconciliation
        pass that settles provider effects settles these too, under the same age
        threshold and batch bound. Each settled intent is journalled
        (``artifact.abandoned``) in the caller's transaction. Returns how many were
        settled; the blob rows they name are left exactly as they were.
        """
        if batch_size < 1:
            raise ValueError("artifact publication settlement batch_size must be positive")
        rows = session.execute(
            _SETTLE_TERMINAL_ARTIFACT_PUBLICATIONS,
            {"older_than": older_than, "batch_size": batch_size},
        ).mappings().all()
        for publication in rows:
            append_execution_event(
                session, event_type="artifact.abandoned",
                aggregate_type="Attempt", aggregate_id=str(publication["attempt_id"]),
                run_id=str(publication["run_id"]),
                payload={"attempt_id": str(publication["attempt_id"]),
                         "stage_id": str(publication["stage_id"]),
                         "state": "abandoned"},
            )
        return len(rows)

    def _advance_job(
        self, session: Session, job_id: str, from_state: str, to_state: str
    ) -> None:
        changed = session.execute(
            _ADVANCE_JOB,
            {
                "job_id": job_id,
                "from_state": from_state,
                "to_state": to_state,
                "terminal": to_state in _JOB_TERMINALS,
            },
        ).rowcount
        if changed != 1:
            raise self._transition_error("job", from_state, to_state)
        run_id = session.execute(
            text("SELECT run_id FROM job WHERE job_id = :job_id"), {"job_id": job_id}
        ).scalar_one()
        append_execution_event(
            session, event_type="job.transition", aggregate_type="Job",
            aggregate_id=job_id, run_id=run_id,
            payload={"from_state": from_state, "to_state": to_state},
        )

    def _advance_attempt(
        self, session: Session, attempt_id: str, from_state: str, to_state: str
    ) -> None:
        changed = session.execute(
            _ADVANCE_ATTEMPT,
            {
                "attempt_id": attempt_id,
                "from_state": from_state,
                "to_state": to_state,
                "terminal": to_state in _ATTEMPT_TERMINALS,
            },
        ).rowcount
        if changed != 1:
            raise self._transition_error("attempt", from_state, to_state)
        run_id = session.execute(text(
            "SELECT j.run_id FROM attempt a JOIN job j ON j.job_id = a.job_id "
            "WHERE a.attempt_id = :attempt_id"
        ), {"attempt_id": attempt_id}).scalar_one()
        append_execution_event(
            session, event_type="attempt.transition", aggregate_type="Attempt",
            aggregate_id=attempt_id, run_id=run_id,
            payload={"from_state": from_state, "to_state": to_state},
        )

    @staticmethod
    def _transition_error(machine: str, current: str, requested: str) -> DomainError:
        return DomainError(
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
            machine=machine,
            current_state=current,
            requested_state=requested,
        )


__all__ = [
    "JOB_WAKEUP_CHANNEL",
    "GROUP_OFFLINE_WAIT_ENV",
    "DEFAULT_GROUP_OFFLINE_WAIT_SECONDS",
    "GroupDispatchWaiting",
    "GroupWaits",
    "AttemptAuthority",
    "CompletedWindowCall",
    "ExecutionNotClaimed",
    "JobRepository",
    "SettledProviderEffect",
    "UnresolvedProviderEffect",
]
