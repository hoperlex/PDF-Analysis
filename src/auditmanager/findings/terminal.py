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
from typing import Any, Final, Mapping, Sequence

from auditmanager.shared.errors import DomainError, ErrorCode, screen_details

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
    #: `D-46`. The classifiers that say **which** dependency, restricted to the
    #: ``safe_detail_keys`` the frozen catalog declares for :attr:`terminal_reason`.
    #:
    #: ``None`` when the run carries no reason, or when the failing stages recorded no
    #: detail. Never an empty object: "no detail" and "an empty detail" are the same fact
    #: and the schema spells it one way.
    #:
    #: **Why a run reading needs this at all.** ``dependency_unavailable`` is a true answer
    #: that an operator cannot act on: `W29-SAY` made the screen explain what the code
    #: *means* and registered `D-46` because it still could not say *which* dependency. The
    #: catalog's ``safe_detail_keys`` live on the **error envelope**, and a ``200`` run
    #: reading is not an error envelope, so the information was not in the data and
    #: inventing it was the one thing that task forbade.
    #:
    #: The sentence this makes sayable, from `W29-SAY`: *your document is fine, the
    #: provider is fine, this deployment has no recording for it.* `R-30` put the stand in
    #: ``recorded`` mode, so a document with no recording is now the ordinary case.
    terminal_detail: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        # The same coupling the database enforces, asserted at the point of decision so
        # an incoherent selection never reaches the runner.
        if self.state == "published" and self.degradation_set:
            raise ValueError("a published run records an empty degradation set")
        if self.state == "partial" and not self.degradation_set:
            raise ValueError("a partial run must record a non-empty degradation set")
        if self.state == "failed" and self.terminal_reason is None:
            raise ValueError("a failed run must record a terminal reason")
        # `D-46`, and this is the point of the field rather than decoration.
        #
        # A detail with no reason beside it is **unscreenable** -- by anything, now or
        # later -- because the allowlist that bounds it is a property of the reported code.
        # And a detail whose keys the reported code does not declare safe is how internals
        # leak into a client, which is the failure the catalog's `safe_detail_keys` exist
        # to prevent. Both are refused here, at the point of decision, by the *same*
        # screen the error envelope uses: one implementation, two call sites.
        if self.terminal_detail is not None:
            if self.terminal_reason is None:
                raise ValueError(
                    "a terminal detail with no terminal reason cannot be screened: the "
                    "allowlist that bounds it belongs to the reported code"
                )
            screen_details(ErrorCode(self.terminal_reason), self.terminal_detail)

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
    stage_details: Mapping[str, Mapping[str, Any] | None] | None = None,
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
        reason = _reason_for(failed + skipped, stage_errors)
        return TerminalSelection(
            state="failed",
            degradation_set=tuple(failed + skipped),
            terminal_reason=reason,
            terminal_detail=_detail_for(
                failed + skipped, reason, stage_errors, stage_details
            ),
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


def _detail_for(
    stages: Sequence[str],
    reason: str,
    stage_errors: Mapping[str, str | None] | None,
    stage_details: Mapping[str, Mapping[str, Any] | None] | None,
) -> Mapping[str, Any] | None:
    """`D-46`. The classifiers the failing stages agreed on, or ``None``.

    **It follows the reason and never leads it.** A detail is carried only from a stage
    whose own error code *is* the reason the run reports, for the reason :func:`_reason_for`
    keeps ``analysis_failed`` when stages disagree: one answer cannot represent two causes,
    and a detail taken from the wrong cause is worse than no detail, because it reads as an
    explanation.

    **Disagreement is a refusal, not a merge.** Two stages that reported the same code with
    different classifiers describe two situations, and a union of their keys would be a
    sentence neither of them said. ``None`` is the honest answer; the stage rows carry both.

    The values were already screened once, by ``StageError.from_domain_error``, against the
    same catalog. They are screened again on the way out, and again at the edge, because
    three screens fail in three different eras -- when the run terminates, when the row is
    written, and when a reader asks -- and only the last covers a row this code did not
    write.
    """
    if not stage_details or not stage_errors:
        return None
    try:
        code = ErrorCode(reason)
    except ValueError:  # pragma: no cover - `_reason_for` returns a catalog member
        return None
    candidates = [
        stage_details.get(stage)
        for stage in stages
        if stage_errors.get(stage) == reason and stage_details.get(stage)
    ]
    if not candidates:
        return None
    first = dict(candidates[0])
    if any(dict(other) != first for other in candidates[1:]):
        return None
    screened = screen_details(code, first)
    return screened or None
