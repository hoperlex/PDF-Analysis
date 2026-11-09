"""The vocabulary of the comparison spend journal and of its call wrapper (`CMP-SPEND-01`).

ADR-0025 decisions 5 and 19 (`Q-CMP-7`), in one place:

* the life of a row of ``comparison_model_call``: ``prepared -> sent -> completed | failed | unknown``;
* the ceilings, in USD: **10 per job and 50 per day per installation**, and the **1.2 x** overrun
  that pauses the job. Money is kept in micro-USD (an integer) so a ceiling is never decided on a
  float that has drifted: an estimate rounds up, a measured cost rounds to the nearest micro;
* a **consent** binds {estimate digest, USD ceiling, connection revision, pinned model}; the wrapper
  takes it as a value and compares the route it is about to use with it.

Nothing here reads a database or calls a provider.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Final, Protocol

if TYPE_CHECKING:  # the types only: this module never imports another context at run time
    from sqlalchemy.orm import Session

    from auditmanager.analysis.public import ModelAdapter, ModelPin, ModelResponse

__all__ = [
    "BINDING_BOUND",
    "BINDING_FROZEN",
    "BINDING_PENDING",
    "CALL_STATES",
    "COST_ESTIMATED",
    "COST_MEASURED",
    "COST_UNMETERED",
    "CallEstimate",
    "CallRecord",
    "CallResult",
    "CallRoute",
    "Consent",
    "DAY_CEILING_MICROS",
    "DAY_CEILING_USD",
    "GroupDispatch",
    "JOB_CEILING_MICROS",
    "JOB_CEILING_USD",
    "JOB_KEY",
    "JobBindings",
    "MICROS_PER_USD",
    "OPEN_STATES",
    "OVERRUN_DENOMINATOR",
    "OVERRUN_NUMERATOR",
    "Spend",
    "SpendPause",
    "TERMINAL_STATES",
    "WAIT_AT_CAPACITY",
    "WAIT_NEEDS_RECONSENT",
    "WAIT_RUNNER_OFFLINE",
    "estimate_micros_of",
    "measured_micros_of",
    "overruns",
]

#: The states of ``comparison_model_call`` (the CHECK of migration ``0038``; a test pins the two).
CALL_STATES: Final[tuple[str, ...]] = ("prepared", "sent", "completed", "failed", "unknown")
#: A call in one of these has been prepared or sent and not ended: money may be in flight.
OPEN_STATES: Final[tuple[str, ...]] = ("prepared", "sent")
TERMINAL_STATES: Final[tuple[str, ...]] = ("completed", "failed", "unknown")

COST_MEASURED: Final[str] = "measured"
COST_ESTIMATED: Final[str] = "estimated"
COST_UNMETERED: Final[str] = "unmetered"

MICROS_PER_USD: Final[int] = 1_000_000
#: ADR-0025 decision 19 (`Q-CMP-7`): hard ceilings, enforced before each call.
JOB_CEILING_USD: Final[int] = 10
DAY_CEILING_USD: Final[int] = 50
JOB_CEILING_MICROS: Final[int] = JOB_CEILING_USD * MICROS_PER_USD
DAY_CEILING_MICROS: Final[int] = DAY_CEILING_USD * MICROS_PER_USD
#: An actual spend above 6/5 of the estimate pauses the job (an integer ratio: no float on the edge).
OVERRUN_NUMERATOR: Final[int] = 6
OVERRUN_DENOMINATOR: Final[int] = 5

#: `EXEC2-GROUP-CMP-01` (ADR-0026 decision 12; migration ``0048``): whether the executor of a comparison AI job was fixed when it started.
#: ``frozen_at_start`` -- every job made before the cut-over and every job made while the routing mode is ``legacy``: the
#: connection revision is written with the consent and nothing changes. ``pending`` -- admitted by a rule or a group, no connection
#: yet. ``bound`` -- the job's first dispatched call chose a member and wrote its connection revision, once.
BINDING_FROZEN: Final[str] = "frozen_at_start"
BINDING_PENDING: Final[str] = "pending"
BINDING_BOUND: Final[str] = "bound"
#: Why a ``pending`` job is not dispatched (decision 15): the contract's ``RunQueueReason`` and the CHECK of migration ``0048`` spell them
#: so, and ``auditmanager.executors.model.WAIT_REASONS`` holds the same three (a test pins the two equal).
WAIT_AT_CAPACITY: Final[str] = "executor_at_capacity"
WAIT_RUNNER_OFFLINE: Final[str] = "runner_offline"
WAIT_NEEDS_RECONSENT: Final[str] = "needs_reconsent"

#: The key of a work item's payload that names the AI job (the unit the user consented to and that the
#: job ceiling applies to). An item whose payload has none is a job of its own. ``CMP-SEAL-C2`` owns the
#: job object; until it exists this key is the one thing that groups the items of a job in the journal.
JOB_KEY: Final[str] = "ai_job_id"


def estimate_micros_of(usd: float) -> int:
    """An estimate in micro-USD, rounded **up**: a ceiling is never passed by a rounding."""
    if not math.isfinite(usd) or usd < 0:
        raise ValueError("an estimate is a finite, non-negative amount")
    return int(math.ceil(usd * MICROS_PER_USD - 1e-6))


def measured_micros_of(usd: float) -> int:
    """A measured cost in micro-USD, to the nearest micro."""
    if not math.isfinite(usd) or usd < 0:
        raise ValueError("a cost is a finite, non-negative amount")
    return int(round(usd * MICROS_PER_USD))


def overruns(actual_micros: int, estimate_micros: int) -> bool:
    """``True`` when ``actual`` is above 1.2 x ``estimate`` (ADR-0025 decision 19)."""
    return actual_micros * OVERRUN_DENOMINATOR > estimate_micros * OVERRUN_NUMERATOR


@dataclass(frozen=True, slots=True)
class Consent:
    """What the user consented to for one AI job (decision 19): the estimate they saw (its digest and
    its USD total), the ceiling they accepted, the connection revision that will serve the calls and
    the pinned model. The wrapper compares a call's route with it; it does not store or issue one.

    The ceiling may not exceed the hard ceiling of the job: a consent for more than USD 10 is
    refused when it is built, never quietly lowered.

    `EXEC2-GROUP-CMP-01` (ADR-0026 decisions 12 and 13): a job admitted by a rule or a group is consented to
    **before** it has a connection. Its consent names the group revision (``executor_group_revision_id``) and, while
    the job is ``pending``, no connection revision; once the job is bound it names both. A consent names a connection
    revision or a group revision, and always a pinned model.

    `HOSTS-CMP-01` (ADR-0028 decision 19): a job the stage layout admitted also consented to its ``cell`` -- the effort, the answer limit and the
    timeout of its kind of work, frozen with the estimate (the digest binds it). The wrapper applies it to every call of the job
    (:mod:`auditmanager.comparison.spend.cell`); a consent with no cell leaves a call as its method built it.
    """

    estimate_digest: str
    estimate_usd: float
    ceiling_usd: float
    connection_revision_id: str | None
    pinned_model: str
    executor_group_revision_id: str | None = None
    cell: Any | None = None

    def __post_init__(self) -> None:
        if len(self.estimate_digest) != 64 or any(c not in "0123456789abcdef" for c in self.estimate_digest):
            raise ValueError("the estimate digest is a lower-case SHA-256 hex digest")
        if not (math.isfinite(self.estimate_usd) and self.estimate_usd >= 0):
            raise ValueError("the estimate is a finite, non-negative USD amount")
        if not (math.isfinite(self.ceiling_usd) and 0 < self.ceiling_usd <= JOB_CEILING_USD):
            raise ValueError(f"the consent ceiling is above zero and at most USD {JOB_CEILING_USD}")
        if not self.pinned_model or not (self.connection_revision_id or self.executor_group_revision_id):
            raise ValueError("a consent names a connection revision or a group revision, and a pinned model")

    @property
    def binding_digest(self) -> str:
        """One digest over the four things the consent binds, for a job layer that stores it. A job admitted by a group
        binds the group revision as a fifth; a job with none keeps the digest it always had."""
        document = {
            "estimate_digest": self.estimate_digest,
            "ceiling_usd": self.ceiling_usd,
            "connection_revision_id": self.connection_revision_id,
            "pinned_model": self.pinned_model,
        }
        if self.executor_group_revision_id is not None:
            document["executor_group_revision_id"] = self.executor_group_revision_id
        encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @property
    def estimate_micros(self) -> int:
        return estimate_micros_of(self.estimate_usd)

    @property
    def ceiling_micros(self) -> int:
        return estimate_micros_of(self.ceiling_usd)


@dataclass(frozen=True, slots=True)
class CallEstimate:
    """The size the caller expects of one call, in tokens: the wrapper prices it from the pinned rates.

    ``input_tokens`` counts the prompt **and the images** (ADR-0025 decision 18: the estimate counts
    images and image bytes). ``output_tokens`` is the ceiling the request allows (its ``max_tokens``).
    """

    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        for value in (self.input_tokens, self.output_tokens):
            if type(value) is not int or value < 0:
                raise ValueError("a token estimate is a non-negative integer")


class JobBindings(Protocol):
    """The job's side of a first-call binding (`EXEC2-GROUP-CMP-01`): read the job, bind it once, record why it waits.

    :class:`~auditmanager.comparison.ai_jobs.repository.AiJobRepository` is the implementation -- the only writer of
    ``comparison_ai_job`` -- and is handed in by the registry, so this package never imports ``ai_jobs``. Every method
    takes the caller's session and never commits.
    """

    def get(self, session: "Session", job_id: str, *, lock: bool = False) -> Any:
        """The job row (an ``AiJobRecord``), or ``None``."""

    def bind(self, session: "Session", job_id: str, *, connection_revision_id: str) -> bool:
        """``pending -> bound`` with the connection revision, once; ``False`` when the job is not ``pending``."""

    def set_wait(self, session: "Session", job_id: str, reason: str) -> float | None:
        """Record that the pending job waits for ``reason`` and answer how many seconds it has waited for that reason."""


@dataclass(frozen=True, slots=True)
class GroupDispatch:
    """What a call of a job admitted by a rule or a group carries instead of a connection (ADR-0026 decisions 12 to 16).

    The route of such a job has **no adapter of its own** until its first call binds it: the first call, in the
    transaction that prepares it, takes the group's lock and its members', chooses an eligible member that has a free
    unit, re-checks the consent, applies the ceilings and writes the binding (``comparison_ai_job.binding_state``
    ``pending -> bound``, ``connection_revision_id`` NULL -> the member's revision) together with the ``prepared`` row of
    the journal. ``member_route`` then opens the chosen member's route -- the composition root's own binder, called with
    the job as it will be once bound. Every later call of the job stays on that member.

    ``group_revision_id`` is what admission froze (the consent names it); ``rule_revision_id`` is the rule that routed the
    job, ``None`` when a group was named explicitly.
    """

    job_id: str
    group_id: str
    group_revision_id: str
    work_kind: str
    member_route: Callable[["Session", str], "CallRoute"]
    jobs: JobBindings
    rule_revision_id: str | None = None

    def __post_init__(self) -> None:
        if not (self.job_id and self.group_id and self.group_revision_id and self.work_kind):
            raise ValueError("a group dispatch names its job, group, group revision and work kind")


@dataclass(frozen=True, slots=True)
class CallRoute:
    """The connection that serves a call, as the wrapper needs to know it.

    ``adapter`` is the object that produces the reply; the **mode is read from it** (``recorded`` or
    ``live``), never from a field here, so a recorded reply cannot be journalled as a live one.
    ``connection_revision_id`` is the executor connection revision (``None`` for the environment
    source, which has no connection and so no per-connection limit). ``model_identity`` is the pinned
    model; ``expected_model`` is the gateway name the reply must report (``R-133``). ``unmetered`` is
    the connection's ``not_metered`` billing: such a call is recorded as unmetered and is never
    limited by money. ``pin`` carries the rates and is required for a live metered call.

    `EXEC2-GROUP-CMP-01`: ``dispatch`` marks the route of a job that is still ``pending`` -- admitted by a group and not
    yet bound to a member. Such a route has no connection revision (the wrapper chooses one in the transaction that
    prepares the call and answers the member's own route), its ``pin`` and ``unmetered`` follow the group revision and its
    ``adapter`` is a placeholder that refuses to be called. ``executor_group_revision_id`` is the group revision the route
    was opened for; the consent names the same one.
    """

    adapter: "ModelAdapter"
    model_identity: str
    connection_revision_id: str | None = None
    expected_model: str | None = None
    check_identity: bool = True
    unmetered: bool = False
    pin: "ModelPin | None" = None
    #: Worker-only mutable attempt context, filled after the journal's prepared row exists.
    call_context: Any | None = None
    executor_group_revision_id: str | None = None
    dispatch: GroupDispatch | None = None

    def __post_init__(self) -> None:
        if not self.model_identity:
            raise ValueError("a route names its pinned model")
        if self.dispatch is not None:
            if self.connection_revision_id is not None:
                raise ValueError("a route that is bound at its first call names no connection revision yet")
            if self.executor_group_revision_id is None:
                object.__setattr__(self, "executor_group_revision_id", self.dispatch.group_revision_id)
            elif self.executor_group_revision_id != self.dispatch.group_revision_id:
                raise ValueError("the route and its dispatch name the same group revision")

    @classmethod
    def from_binding(cls, adapter: "ModelAdapter", call: Any, pin: "ModelPin | None") -> "CallRoute":
        """The route of a ``CallBinding`` (what the executors' resolver hands the Run path), for a
        comparison lane that binds a connection the same way."""
        model = pin.model_id if pin is not None else (call.expected_model or "")
        return cls(
            adapter=adapter, model_identity=model,
            connection_revision_id=call.connection_revision_id,
            expected_model=call.expected_model, check_identity=call.check_identity,
            unmetered=call.unmetered, pin=pin,
        )


@dataclass(frozen=True, slots=True)
class Spend:
    """What a scope (one job, one day) has cost so far, in micro-USD.

    ``actual`` is the known cost of completed calls and of failed calls that were charged;
    ``reserved`` is the estimate of calls that are still open or ended ``unknown`` (money that may be
    spent). A ceiling is decided on ``committed`` (both); an overrun on ``actual`` alone.
    """

    actual_micros: int
    reserved_micros: int

    @property
    def committed_micros(self) -> int:
        return self.actual_micros + self.reserved_micros


@dataclass(frozen=True, slots=True)
class SpendPause:
    """The job must pause and ask for a new consent. Carried by a :class:`CallResult` whose call was
    made and paid for; the next call of the job is refused (the same reason) until a consent is made."""

    reason: str


@dataclass(frozen=True, slots=True)
class CallRecord:
    """One row of ``comparison_model_call``, as a reader sees it."""

    call_id: str
    work_id: str
    attempt_id: str
    work_kind: str
    state: str
    provider_mode: str
    model_identity: str
    connection_revision_id: str | None
    request_sha256: str
    estimate_micros: int
    executor_task_id: str | None
    response_sha256: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    cost_basis: str | None
    cost_micros: int | None
    error_code: str | None
    prepared_at: datetime
    sent_at: datetime | None
    terminal_at: datetime | None


@dataclass(frozen=True, slots=True)
class CallResult:
    """What a completed call gives back: the reply, its journal row and what it cost.

    ``pause`` is set when this call took the job over a ceiling or past 1.2 x its estimate: the reply
    is valid and was paid for, so it is handed back, but the job makes no further call.
    """

    response: "ModelResponse"
    call_id: str
    cost_basis: str
    cost_micros: int
    pause: SpendPause | None = field(default=None)
