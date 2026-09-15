"""The bounded in-process retry policy for the one retryable transport failure.

``P4_CLOSURE.md`` §1 accepted a hand-performed retry of three ``dependency_unavailable``
attempts on the grounds that **the failure is transport, not judgement**: the provider was
unreachable, the model never answered, so no model output is discarded and a retry cannot
launder a bad answer into a good one. §6 then recorded what must not happen next — "a
retry policy for ``dependency_unavailable`` belongs in the run executor, not in each
caller… Ruling 1 accepts a retry performed by hand; that is not a licence for every caller
to invent its own."

This module is that policy, and :mod:`auditmanager.runs.executor` is its only caller.

What this is not
----------------
It is **not** durable execution. PC-01 has no ``Job``, no ``Attempt`` row, no lease, no
heartbeat, no execution token and no outbox (``PROTOTYPE_EXECUTION_PLAN.md`` §1), and this
module instantiates none of them: an attempt here is a loop counter in one process, and it
survives only as scalar provenance on the stage result the process writes. Nothing here
retries a *run*; the run's idempotency key never changes and no second command is issued.

The distinction that matters, and why it is structural
------------------------------------------------------
``analysis_failed`` is the model answering badly. Retrying it would re-ask a question that
was already answered, and would eventually launder a bad answer into a good one — exactly
what §1's reasoning forbids. ``dependency_unavailable`` is the provider being unreachable.

That distinction is **not** a comment and not an inline ``!=`` in the executor. It is
carried by the frozen error catalog: ``contracts/domain/v1/error-codes.json`` pins a
``retryable`` flag per code, ``analysis_failed`` is ``retryable: false``, and
:meth:`RetryPolicy.__post_init__` refuses to construct a policy over any code the catalog
does not mark retryable. A policy that retries ``analysis_failed`` is therefore not
expressible, and making it expressible means editing a frozen contract.

The catalog's retryable set is wider than this one: ``idempotency_key_in_progress`` is also
``retryable: true``, and it is a *command* concern that no executing stage can raise. So
:data:`RETRYABLE_STAGE_ERRORS` is declared here as the narrower set, and the catalog is the
ceiling on it rather than the definition of it.

The pins
--------
:data:`ATTEMPT_BUDGET` and :data:`BACKOFF_SECONDS` are pinned facts, not literals in a
branch. They live here for the same reason ``PC01_STAGES`` lives in
:mod:`auditmanager.runs.repository` and ``AGGREGATES_NOT_INSTANTIATED`` lives in
:mod:`auditmanager.runs.scope`: the ``runs`` tree keeps its pinned facts as module-level
data that a test reads, so a change to one cannot quietly fail to reach the other.
``docs/program/P02_LOCK.json`` is the dependency and provider lock, owned by ``B-0``, and
carries no execution-policy facts; this session does not own it and did not widen it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

#: PIN — how many attempts one model stage gets inside one run, first attempt included.
#:
#: Three, because ``P4-RUN-01`` measured the failure it answers: three of seventeen live
#: attempts lost the provider, and **every one of the three succeeded on the next
#: attempt**. One retry therefore covers every observed case and the budget carries one
#: spare. It is small on purpose — an unreachable provider that is still unreachable after
#: two more tries is an outage, and a run that reports that quickly is more useful than one
#: that hides it behind a long ladder. ``OD-03``'s per-run cost ceiling is what bounds the
#: *spend* across these attempts; this bounds the *time*.
ATTEMPT_BUDGET: Final[int] = 3

#: PIN — the wait before each retry, in seconds, indexed by the retry about to be made.
#: Exactly ``ATTEMPT_BUDGET - 1`` entries, checked at construction: a budget and a backoff
#: ladder that disagree would leave one attempt's wait undefined.
#:
#: The observed failure took ~133 s to surface, so these waits are deliberately small
#: beside it: they exist to let a momentary outage clear, not to implement congestion
#: control. Geometric rather than constant, so the second retry concedes more ground.
BACKOFF_SECONDS: Final[tuple[float, ...]] = (2.0, 8.0)

#: PIN — the stage failures this executor retries. Exactly one code: the transport one.
#: Narrower than the catalog's retryable set on purpose (see the module docstring), and it
#: cannot be widened past that set — :class:`RetryPolicy` refuses to construct.
RETRYABLE_STAGE_ERRORS: Final[frozenset[ErrorCode]] = frozenset(
    {ErrorCode.DEPENDENCY_UNAVAILABLE}
)


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """How many attempts a stage gets, how long it waits, and which failures qualify."""

    attempt_budget: int = ATTEMPT_BUDGET
    backoff_seconds: tuple[float, ...] = BACKOFF_SECONDS
    retryable_errors: frozenset[ErrorCode] = RETRYABLE_STAGE_ERRORS

    def __post_init__(self) -> None:
        if self.attempt_budget < 1:
            raise ValueError("a stage gets at least one attempt")
        not_retryable = sorted(
            code.value for code in self.retryable_errors if not code.retryable
        )
        if not_retryable:
            # The frozen catalog is the authority. This is the structural half of "never
            # retry analysis_failed": the policy cannot hold a code the contract says is
            # not retryable, so no call site can opt one in.
            raise ValueError(
                "the frozen error catalog does not mark these codes retryable: "
                + ", ".join(not_retryable)
            )
        if len(self.backoff_seconds) != self.attempt_budget - 1:
            raise ValueError(
                f"a budget of {self.attempt_budget} attempts needs "
                f"{self.attempt_budget - 1} backoff values, got "
                f"{len(self.backoff_seconds)}"
            )
        if any(wait < 0 for wait in self.backoff_seconds):
            raise ValueError("a backoff cannot be negative")

    def retries(self, error: DomainError | None) -> bool:
        """Whether this failure is one a second attempt could answer differently.

        ``None`` — a stage that did not fail — is never retried, which is what keeps a
        ``succeeded`` or ``partial`` outcome out of the loop without a status comparison
        here.
        """
        if error is None:
            return False
        return error.code in self.retryable_errors

    def backoff_before_attempt(self, attempt: int) -> float:
        """The wait before ``attempt`` (1-based). The first attempt never waits."""
        if attempt <= 1:
            return 0.0
        try:
            return self.backoff_seconds[attempt - 2]
        except IndexError:
            raise ValueError(
                f"attempt {attempt} is past a budget of {self.attempt_budget}"
            ) from None

    def has_budget_for(self, attempt: int) -> bool:
        """Whether ``attempt`` (1-based) is within the budget."""
        return attempt <= self.attempt_budget


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    """One attempt at one stage. Not an ``Attempt`` aggregate — PC-01 has none."""

    attempt: int
    status: str
    error_code: str | None
    waited_seconds: float


@dataclass(frozen=True, slots=True)
class AttemptSummary:
    """What a caller and a persisted row can both say about the attempts that ran.

    Every field is a scalar, because ``contracts/analysis/v1/stage-result.schema.json``
    admits only scalars in ``metrics`` — the one place PC-01 can record this without a
    table it is not allowed to have. :meth:`metrics` is the whole of that mapping.
    """

    attempts: int
    attempt_budget: int
    retried_on_error_code: str | None
    waited_seconds_total: float
    records: tuple[AttemptRecord, ...] = ()

    @property
    def retried(self) -> bool:
        return self.attempts > 1

    @property
    def budget_exhausted(self) -> bool:
        """``True`` when the last attempt was the last one the budget allowed."""
        return self.attempts >= self.attempt_budget

    def metrics(self) -> dict[str, str | int | float | bool | None]:
        """The scalar provenance that makes attempts countable after the fact.

        ``attempts`` is the field that keeps ``P4_CLOSURE.md`` §1's alternative headline
        computable: a first-try success reads ``1`` and a third-try success reads ``3``,
        so "how many documents published without a retry" stays a query rather than a
        recollection.
        """
        return {
            "attempts": self.attempts,
            "attempt_budget": self.attempt_budget,
            "attempt_budget_exhausted": self.budget_exhausted,
            "retried_on_error_code": self.retried_on_error_code,
            "retry_waited_seconds": round(self.waited_seconds_total, 6),
        }


@dataclass(slots=True)
class AttemptLedger:
    """The running tally of one stage's attempts, closed into an :class:`AttemptSummary`."""

    attempt_budget: int
    _records: list[AttemptRecord] = field(default_factory=list)

    @property
    def attempts(self) -> int:
        return len(self._records)

    def record(
        self, *, status: str, error: DomainError | None, waited_seconds: float
    ) -> AttemptRecord:
        entry = AttemptRecord(
            attempt=self.attempts + 1,
            status=status,
            error_code=None if error is None else error.code.value,
            waited_seconds=waited_seconds,
        )
        self._records.append(entry)
        return entry

    def close(self) -> AttemptSummary:
        """Freeze the tally.

        ``retried_on_error_code`` is the code of the last attempt that was retried, and is
        ``None`` when nothing was retried: it says *why* a second attempt was made, so a
        reader of the row does not have to take "a retry happened" on trust.
        """
        retried_on: str | None = None
        if len(self._records) > 1:
            retried_on = self._records[-2].error_code
        return AttemptSummary(
            attempts=self.attempts,
            attempt_budget=self.attempt_budget,
            retried_on_error_code=retried_on,
            waited_seconds_total=sum(entry.waited_seconds for entry in self._records),
            records=tuple(self._records),
        )


def not_attempted(policy: RetryPolicy) -> AttemptSummary:
    """The summary for a stage that never reached the provider at all.

    Distinct from one attempt that failed: ``attempts: 0`` says the loop was never entered,
    which is what a missing required input produces. Recording it as a failed attempt would
    overstate what was tried.
    """
    return AttemptSummary(
        attempts=0,
        attempt_budget=policy.attempt_budget,
        retried_on_error_code=None,
        waited_seconds_total=0.0,
    )


__all__ = [
    "ATTEMPT_BUDGET",
    "BACKOFF_SECONDS",
    "RETRYABLE_STAGE_ERRORS",
    "AttemptLedger",
    "AttemptRecord",
    "AttemptSummary",
    "RetryPolicy",
    "not_attempted",
]
