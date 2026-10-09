"""The persisted ``AuditRun``, the sequential local executor, and restart reconciliation.

This is the composition point of PC-01: it drives modules that already exist and
reimplements none of them. The public surface is deliberately small — a command, an
executor, a read model and a reconciler — because ``B6``'s API is written against
``P02_SEAMS.md`` and ``contracts/api/v1/openapi.json``, not against this code.

    from auditmanager.runs import start_audit_run, execute_run, reconcile

Durable local authority
-----------------------
W48 gives each accepted run one local ``Job``, current ``Attempt``, lease and opaque
execution token before its first external effect. Provider-call retries remain a bounded
loop *inside* that execution Attempt. Remote dispatch, heartbeat/failover, run-level
resume and outbox delivery are still absent.

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
from auditmanager.runs.executor import EffectCheckpoint, ExecutionResult, execute_run
from auditmanager.runs.carrier import (
    CRASHED_REASON,
    RUN_CONCURRENCY,
    InlineCarrier,
    RunCarrier,
    ThreadCarrier,
    DurableCarrier,
    run_to_terminal,
)
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
    STARTUP_THRESHOLD,
    STRANDED_STATES,
    ReconciledRun,
    ReconciliationReport,
    abandon_stale_commands,
    reconcile,
    reconcile_at_startup,
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
    "AttemptRecord",
    "AttemptSummary",
    "BACKOFF_SECONDS",
    "COMMAND_TYPE_START_RUN",
    "CRASHED_REASON",
    "DurableCarrier",
    "EffectCheckpoint",
    "ExecutionResult",
    "INITIAL_STATE",
    "INTERRUPTED_REASON",
    "INTERRUPTED_TERMINAL_REASON",
    "InlineCarrier",
    "PC01_STAGES",
    "RECONCILIATION_TERMINAL",
    "RETRYABLE_STAGE_ERRORS",
    "RUN_CONCURRENCY",
    "RUN_MACHINE",
    "ReconciledRun",
    "ReconciliationReport",
    "RetryPolicy",
    "RunCarrier",
    "RunCost",
    "RunRepository",
    "RunRow",
    "SCHEMAS_NOT_CLAIMED",
    "STARTUP_THRESHOLD",
    "STRANDED_STATES",
    "StageResultRow",
    "StartedRun",
    "ThreadCarrier",
    "UNEVALUATED_GUARDS",
    "UnevaluatedGuard",
    "abandon_stale_commands",
    "execute_run",
    "frozen_input_digest",
    "reconcile",
    "reconcile_at_startup",
    "reconcile_interrupted_runs",
    "run_of_command",
    "run_to_terminal",
    "start_audit_run",
    "start_run_fingerprint",
]
