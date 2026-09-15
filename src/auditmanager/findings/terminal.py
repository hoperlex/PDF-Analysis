"""Terminal selection — which terminal state the run reached, and why.

``P2-RUN-01`` calls this during ``validating`` and **records** what it returns; the
executor never selects a terminal itself. That ordering is why this function is pure:
selection is a decision about stage outcomes and gate results, not about how the runner
happens to be structured, and a runner authored against a stub that faked ``published``
would have proved nothing.

The rules, from the task deliverables and P02 §3.4:

* every required stage ``succeeded`` and the gate ran → ``published``, with an **empty**
  degradation set;
* a required stage reported ``partial`` → ``partial``, with the degraded stages recorded
  in a **non-empty** degradation set;
* any required stage ``failed`` (or was ``skipped``) → ``failed``, with a terminal
  reason, and nothing published.

``published`` with a non-empty degradation set and ``partial`` with an empty one are
both refused by CHECK constraints in the migration, so a silent degradation cannot reach
the success terminal even if this function were wrong. This function is the *reason*
recorded alongside it, not the only thing standing in the way.

Note what is **not** a terminal input: the number of findings published. A run over a
clean document publishes nothing and is still ``published``. Zero findings is a result,
not a failure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Mapping, Sequence

from auditmanager.shared.errors import DomainError, ErrorCode

#: Status values ``stage_result`` may carry (P02 §3.4).
STAGE_STATUSES: Final[frozenset[str]] = frozenset(
    {"succeeded", "partial", "failed", "skipped"}
)

#: The terminals ``audit_run`` declares reachable from ``validating``.
TERMINALS_FROM_VALIDATING: Final[frozenset[str]] = frozenset(
    {"published", "partial", "failed"}
)


@dataclass(frozen=True, slots=True)
class TerminalSelection:
    """The terminal a run reached, with everything the runner must record with it."""

    state: str
    degradation_set: tuple[str, ...] = ()
    terminal_reason: str | None = None

    def __post_init__(self) -> None:
        # The same coupling the database enforces, asserted at the point of decision so
        # an incoherent selection never reaches the runner.
        if self.state == "published" and self.degradation_set:
            raise ValueError("a published run records an empty degradation set")
        if self.state == "partial" and not self.degradation_set:
            raise ValueError("a partial run must record a non-empty degradation set")
        if self.state == "failed" and self.terminal_reason is None:
            raise ValueError("a failed run must record a terminal reason")

    @property
    def is_publishable(self) -> bool:
        """``published`` and ``partial`` both publish findings; ``failed`` publishes
        nothing. ``partial`` is a terminal state and stays exportable under ``OD-11``,
        so no PC-01 operation refuses because a run is partial."""
        return self.state in {"published", "partial"}


def select_terminal(
    stage_statuses: Mapping[str, str],
    *,
    required_stages: Sequence[str],
    gate_ran: bool = True,
    stage_errors: Mapping[str, str | None] | None = None,
) -> TerminalSelection:
    """Choose the terminal from the required stages' statuses.

    ``failed`` dominates ``partial``, which dominates ``published``: a run with one
    failed and one partial stage failed. Reporting it as partial would put a run that
    lost a whole stage on the exportable side of the line.
    """
    missing = [stage for stage in required_stages if stage not in stage_statuses]
    if missing:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=(
                "terminal selection needs a status for every required stage; "
                f"{len(missing)} were not reported"
            ),
        )
    unknown = {
        stage: status
        for stage, status in stage_statuses.items()
        if status not in STAGE_STATUSES
    }
    if unknown:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"{len(unknown)} stage statuses are not in the declared status set",
        )

    failed = [stage for stage in required_stages if stage_statuses[stage] == "failed"]
    skipped = [stage for stage in required_stages if stage_statuses[stage] == "skipped"]
    if failed or skipped:
        return TerminalSelection(
            state="failed",
            degradation_set=tuple(failed + skipped),
            terminal_reason=_reason_for(failed + skipped, stage_errors),
        )

    if not gate_ran:
        # The gate is unconditional: a run that reached validating without it did not
        # establish that anything is grounded, and no flag lets it publish.
        return TerminalSelection(
            state="failed",
            degradation_set=(),
            terminal_reason="analysis_failed",
        )

    degraded = [stage for stage in required_stages if stage_statuses[stage] == "partial"]
    if degraded:
        return TerminalSelection(state="partial", degradation_set=tuple(degraded))

    return TerminalSelection(state="published")


def _reason_for(
    stages: Sequence[str], stage_errors: Mapping[str, str | None] | None
) -> str:
    """The run's terminal reason: the stages' own code when they agree on one.

    ``audit_run.terminal_reason`` is CHECK-constrained to the frozen error catalog, so the
    only values this may return are catalog members; an unrecognised code from a stage is
    ignored rather than passed through to be refused by the database.

    One reason cannot represent two different causes, so a run whose stages failed for
    different reasons keeps the generic ``analysis_failed``. That is a deliberate loss:
    naming one of several causes would be a guess, and the stage rows carry all of them.

    Without this the run row said ``analysis_failed`` whatever killed it, which matters
    because the catalog marks ``analysis_failed`` not retryable and ``dependency_unavailable``
    retryable -- so an operator reading the run could not tell a model that answered badly
    from a provider that never answered.
    """
    if not stage_errors:
        return ErrorCode.ANALYSIS_FAILED.value
    codes = {stage_errors.get(stage) for stage in stages}
    codes.discard(None)
    if len(codes) != 1:
        return ErrorCode.ANALYSIS_FAILED.value
    code = codes.pop()
    try:
        return ErrorCode(code).value
    except ValueError:
        return ErrorCode.ANALYSIS_FAILED.value
