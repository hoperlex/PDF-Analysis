"""The persisted ``AuditRun``, the sequential local executor, and restart reconciliation.

This is the composition point of PC-01: it drives modules that already exist and
reimplements none of them. The public surface is deliberately small — a command, an
executor, a read model and a reconciler — because ``B6``'s API is written against
``P02_SEAMS.md`` and ``contracts/api/v1/openapi.json``, not against this code.

    from auditmanager.runs import start_audit_run, execute_run, reconcile

What PC-01 has no such thing as
-------------------------------
``Job``, ``Attempt``, lease, heartbeat, execution token, fencing, resume, automatic
retry and outbox. None of those tables exists (P02 §3.1) and a test asserts their
absence. There is also **no ``succeeded`` run state**: the success terminal is
``published``, and ``succeeded`` is a *stage* status. :mod:`auditmanager.runs.scope`
records, as data, every clause of the ``audit_run`` contract PC-01 leaves unevaluated.
"""

from auditmanager.runs.commands import (
    COMMAND_TYPE_START_RUN,
    StartedRun,
    frozen_input_digest,
    run_of_command,
    start_audit_run,
)
from auditmanager.runs.executor import ExecutionResult, execute_run
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
    "COMMAND_TYPE_START_RUN",
    "INITIAL_STATE",
    "INTERRUPTED_REASON",
    "INTERRUPTED_TERMINAL_REASON",
    "PC01_STAGES",
    "RECONCILIATION_TERMINAL",
    "RUN_MACHINE",
    "SCHEMAS_NOT_CLAIMED",
    "UNEVALUATED_GUARDS",
    "ExecutionResult",
    "ReconciledRun",
    "ReconciliationReport",
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
]
