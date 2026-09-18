"""The persisted ``AuditRun``, the sequential local executor, and restart reconciliation.

This is the composition point of PC-01: it drives modules that already exist and
reimplements none of them. The public surface is deliberately small — a command, an
executor, a read model and a reconciler — because ``B6``'s API is written against
``P02_SEAMS.md`` and ``contracts/api/v1/openapi.json``, not against this code.

    from auditmanager.runs import start_audit_run, execute_run, reconcile

What PC-01 has no such thing as
-------------------------------
``Job``, ``Attempt``, lease, heartbeat, execution token, fencing, resume and outbox. None
of those tables exists (P02 §3.1) and a test asserts their absence. The model stage does
retry an unreachable provider, in process and within a pinned budget
(:mod:`auditmanager.runs.retry`); that is a loop inside one execution, and it creates no
``Attempt`` row, takes no lease and redelivers nothing.

There is also **no ``succeeded`` run state**: the success terminal is ``published``, and
``succeeded`` is a *stage* status. :mod:`auditmanager.runs.scope` records, as data, every
clause of the ``audit_run`` contract PC-01 leaves unevaluated.
"""

from auditmanager.runs.commands import (
    COMMAND_TYPE_START_RUN,
    StartedRun,
    frozen_input_digest,
    run_of_command,
    start_audit_run,
    start_run_fingerprint,
)
from auditmanager.runs.executor import ExecutionResult, execute_run
from auditmanager.runs.retry import (
    ATTEMPT_BUDGET,
    BACKOFF_SECONDS,
    RETRYABLE_STAGE_ERRORS,
    AttemptRecord,
    AttemptSummary,
    RetryPolicy,
)
from auditmanager.runs.reconciliation import (
    INTERRUPTED_REASON,
    INTERRUPTED_TERMINAL_REASON,
    ReconciledRun,
    ReconciliationReport,
    abandon_stale_commands,
    reconcile,
    reconcile_interrupted_runs,
)
from auditmanager.runs.repository import (
    INITIAL_STATE,
    PC01_STAGES,
    RUN_MACHINE,
    RunCost,
    RunRepository,
    RunRow,
    StageResultRow,
)
from auditmanager.runs.scope import (
    ABSENT_CAPABILITIES,
    AGGREGATES_NOT_INSTANTIATED,
    RECONCILIATION_TERMINAL,
    SCHEMAS_NOT_CLAIMED,
    UNEVALUATED_GUARDS,
    UnevaluatedGuard,
)

__all__ = [
    "ABSENT_CAPABILITIES",
    "AGGREGATES_NOT_INSTANTIATED",
    "ATTEMPT_BUDGET",
    "BACKOFF_SECONDS",
    "COMMAND_TYPE_START_RUN",
    "INITIAL_STATE",
    "INTERRUPTED_REASON",
    "INTERRUPTED_TERMINAL_REASON",
    "PC01_STAGES",
    "RECONCILIATION_TERMINAL",
    "RETRYABLE_STAGE_ERRORS",
    "RUN_MACHINE",
    "SCHEMAS_NOT_CLAIMED",
    "UNEVALUATED_GUARDS",
    "AttemptRecord",
    "AttemptSummary",
    "ExecutionResult",
    "ReconciledRun",
    "ReconciliationReport",
    "RetryPolicy",
    "RunCost",
    "RunRepository",
    "RunRow",
    "StageResultRow",
    "StartedRun",
    "UnevaluatedGuard",
    "abandon_stale_commands",
    "execute_run",
    "frozen_input_digest",
    "reconcile",
    "reconcile_interrupted_runs",
    "run_of_command",
    "start_audit_run",
    "start_run_fingerprint",
]
