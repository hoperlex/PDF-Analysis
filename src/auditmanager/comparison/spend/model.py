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
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:  # the types only: this module never imports another context at run time
    from auditmanager.analysis.public import ModelAdapter, ModelPin, ModelResponse

__all__ = [
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
    "JOB_CEILING_MICROS",
    "JOB_CEILING_USD",
    "JOB_KEY",
    "MICROS_PER_USD",
    "OPEN_STATES",
    "OVERRUN_DENOMINATOR",
    "OVERRUN_NUMERATOR",
    "Spend",
    "SpendPause",
    "TERMINAL_STATES",
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
    """

    estimate_digest: str
    estimate_usd: float
    ceiling_usd: float
    connection_revision_id: str
    pinned_model: str

    def __post_init__(self) -> None:
        if len(self.estimate_digest) != 64 or any(c not in "0123456789abcdef" for c in self.estimate_digest):
            raise ValueError("the estimate digest is a lower-case SHA-256 hex digest")
        if not (math.isfinite(self.estimate_usd) and self.estimate_usd >= 0):
            raise ValueError("the estimate is a finite, non-negative USD amount")
        if not (math.isfinite(self.ceiling_usd) and 0 < self.ceiling_usd <= JOB_CEILING_USD):
            raise ValueError(f"the consent ceiling is above zero and at most USD {JOB_CEILING_USD}")
        if not self.connection_revision_id or not self.pinned_model:
            raise ValueError("a consent names a connection revision and a pinned model")

    @property
    def binding_digest(self) -> str:
        """One digest over the four things the consent binds, for a job layer that stores it."""
        document = {
            "estimate_digest": self.estimate_digest,
            "ceiling_usd": self.ceiling_usd,
            "connection_revision_id": self.connection_revision_id,
            "pinned_model": self.pinned_model,
        }
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
    """

    adapter: "ModelAdapter"
    model_identity: str
    connection_revision_id: str | None = None
    expected_model: str | None = None
    check_identity: bool = True
    unmetered: bool = False
    pin: "ModelPin | None" = None

    def __post_init__(self) -> None:
        if not self.model_identity:
            raise ValueError("a route names its pinned model")

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
