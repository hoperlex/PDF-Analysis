"""The paid repair journal's vocabulary: calls, their states, the transport port, refusals.

`R-106` binds the shape (`W54-PLAN.md` §3.3): one ``norm_repair_call`` row per provider
try, its idempotency scope its own ``nrc`` id, the response checkpointed before it is
parsed, and three terminal states — ``completed``, ``not_processed`` and
``outcome_unknown``. This module names those states and the facts each call carries; it
knows no provider and no database.
"""

from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from ..rerecognition import PageToRecognise, RecognisedPage

#: `R-79`: at most three provider tries for one call, the second after 2 s and the third
#: after 8 s, and a `Retry-After` honoured up to 60 s. Only a try the transport proves was
#: not processed (no connection, 429) is retried.
MAX_PROVIDER_TRIES: int = 3
RETRY_DELAYS_SECONDS: tuple[float, ...] = (2.0, 8.0)
RETRY_AFTER_CAP_SECONDS: float = 60.0

#: W-4 / `R-106`: the cumulative ceiling of the repair run, across every restart and every
#: row the promotion database holds.
CEILING_USD: Decimal = Decimal(10)

#: `R-95` (K-8): the sample is the three largest crops by area, and the full run proceeds
#: only if ``mean sample cost x pages x 1.25 <= ceiling``.
SAMPLE_SIZE: int = 3
SAMPLE_MARGIN: Decimal = Decimal("1.25")

#: A run that sees this many ``outcome_unknown`` calls in a row stops: each is counted at
#: its bound, and an unreachable proxy would otherwise turn the ceiling into a bill for
#: nothing.
MAX_CONSECUTIVE_UNKNOWN: int = 3

#: Money is kept to the database's scale, ``numeric(12, 6)``.
MONEY_QUANTUM: Decimal = Decimal("0.000001")


def money(value: Decimal | float | str) -> Decimal:
    """A dollar amount at the journal's scale. Floats pass through ``str`` first."""
    if isinstance(value, float):
        value = repr(value)
    return Decimal(value).quantize(MONEY_QUANTUM)


class CallState(enum.Enum):
    """``norm_repair_call.state`` (`0018`). The last three are terminal."""

    PREPARED = "prepared"
    RESPONSE_RECEIVED = "response_received"
    COMPLETED = "completed"
    NOT_PROCESSED = "not_processed"
    OUTCOME_UNKNOWN = "outcome_unknown"

    @property
    def terminal(self) -> bool:
        return self in (CallState.COMPLETED, CallState.NOT_PROCESSED, CallState.OUTCOME_UNKNOWN)


class Failure:
    """The ``failure`` classifiers this lane writes (``^[a-z][a-z0-9_]{2,63}$``)."""

    #: Retry-safe: the request never left (DNS, refused connect, certificate).
    NOT_SENT = "not_sent"
    #: Retry-safe: an explicit 429.
    RATE_LIMITED = "rate_limited"
    #: Not processed, not retried, and the run stops: 401/403.
    CREDENTIAL_REFUSED = "credential_refused"
    #: Not processed, not retried, and the run stops: 400/413.
    REQUEST_REFUSED = "request_refused"
    #: Ambiguous (`R-85`/D-153: every 503, a reset, a timeout, a foreign 5xx).
    OUTCOME_UNKNOWN = "proxy_outcome_unknown"
    #: The transport returned without handing over an answer body.
    NO_ANSWER_BODY = "no_answer_body"
    #: A start found a call with no recorded outcome and no checkpointed body.
    RECONCILED_UNKNOWN = "journal_reconciled"
    #: A completed answer the runner refuses (counted, never applied).
    MODEL_MISMATCH = "model_mismatch"
    UNPRICED = "unpriced_response"
    UNREADABLE = "unreadable_answer"


#: Failures after which the same call may be tried again.
RETRY_SAFE_FAILURES: frozenset[str] = frozenset({Failure.NOT_SENT, Failure.RATE_LIMITED})
#: Completed answers that are recorded and charged but never judged.
REFUSED_ANSWERS: frozenset[str] = frozenset(
    {Failure.MODEL_MISMATCH, Failure.UNPRICED, Failure.UNREADABLE}
)


@dataclass(frozen=True, slots=True)
class CallIntent:
    """Everything known about one provider try before it is dispatched.

    ``block_anchor`` is the pipeline's ``blk_<hex>`` block id (`AGENTS.md` §4: never a path
    or a page label). ``ordinal`` is the recognition of the page (`R-19`'s two reads) and
    ``try_number`` the provider try within it (`R-79`'s three); ``attempt_number`` is the
    database's per-block sequence over both. ``bound_usd`` is what the call is charged if
    its outcome is never learned.
    """

    call_id: str
    document_slug: str
    block_anchor: str
    page_label: int
    crop_sha256: str
    request_sha256: str
    model: str
    attempt_number: int
    ordinal: int
    try_number: int
    bound_usd: Decimal
    prepared_at: str

    def identity(self) -> tuple[str, str, str, str, int]:
        """The columns the database row must agree on with the journal file."""
        return (
            self.block_anchor,
            self.crop_sha256,
            self.request_sha256,
            self.model,
            self.attempt_number,
        )

    def as_document(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "document_slug": self.document_slug,
            "block_anchor": self.block_anchor,
            "page_label": self.page_label,
            "crop_sha256": self.crop_sha256,
            "request_sha256": self.request_sha256,
            "model": self.model,
            "attempt_number": self.attempt_number,
            "ordinal": self.ordinal,
            "try_number": self.try_number,
            "bound_usd": str(self.bound_usd),
            "prepared_at": self.prepared_at,
        }

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> CallIntent:
        return cls(
            call_id=str(document["call_id"]),
            document_slug=str(document["document_slug"]),
            block_anchor=str(document["block_anchor"]),
            page_label=int(document["page_label"]),
            crop_sha256=str(document["crop_sha256"]),
            request_sha256=str(document["request_sha256"]),
            model=str(document["model"]),
            attempt_number=int(document["attempt_number"]),
            ordinal=int(document["ordinal"]),
            try_number=int(document["try_number"]),
            bound_usd=money(document["bound_usd"]),
            prepared_at=str(document["prepared_at"]),
        )


@dataclass(frozen=True, slots=True)
class Settlement:
    """A call's terminal outcome, as the database and the file both record it."""

    state: CallState
    charged_usd: Decimal
    cost_usd: Decimal | None = None
    response_model: str | None = None
    failure: str | None = None
    retry_after_seconds: float = 0.0

    def as_document(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "charged_usd": str(self.charged_usd),
            "cost_usd": None if self.cost_usd is None else str(self.cost_usd),
            "response_model": self.response_model,
            "failure": self.failure,
            "retry_after_seconds": self.retry_after_seconds,
        }

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> Settlement:
        return cls(
            state=CallState(document["state"]),
            charged_usd=money(document["charged_usd"]),
            cost_usd=None if document.get("cost_usd") is None else money(document["cost_usd"]),
            response_model=document.get("response_model"),
            failure=document.get("failure"),
            retry_after_seconds=float(document.get("retry_after_seconds") or 0.0),
        )

    def same_outcome(self, other: Settlement) -> bool:
        """Equal on what the database stores (``retry_after`` lives in the file only)."""
        return (
            self.state is other.state
            and self.charged_usd == other.charged_usd
            and self.cost_usd == other.cost_usd
            and self.response_model == other.response_model
            and self.failure == other.failure
        )


@dataclass(frozen=True, slots=True)
class CallRow:
    """One ``norm_repair_call`` row as the store returns it."""

    call_id: str
    block_anchor: str
    crop_sha256: str
    request_sha256: str
    model: str
    attempt_number: int
    state: CallState
    response_sha256: str | None
    settlement: Settlement | None

    def identity(self) -> tuple[str, str, str, str, int]:
        return (
            self.block_anchor,
            self.crop_sha256,
            self.request_sha256,
            self.model,
            self.attempt_number,
        )


@dataclass(slots=True)
class JournalCall:
    """One call as the local journal file knows it: the intent, then appended effects."""

    intent: CallIntent
    response_sha256: str | None = None
    settlement: Settlement | None = None
    settled_at: str | None = None


@dataclass(frozen=True, slots=True)
class PreparedRequest:
    """A request ready to send: its checksum, its pixel count and the transport's payload."""

    request_sha256: str
    pixels: int
    max_output_tokens: int
    payload: Any = field(compare=False, repr=False)


class CallFailure(Exception):
    """A provider try that ended without an answer body, classified by the transport."""

    def __init__(self, failure: str, *, retry_safe: bool, retry_after_seconds: float = 0.0) -> None:
        super().__init__(failure)
        self.failure = failure
        self.retry_safe = retry_safe
        self.retry_after_seconds = retry_after_seconds


class UnreadableAnswer(Exception):
    """A checkpointed body that is not a usable answer. ``cost_usd`` when usage priced it."""

    def __init__(self, message: str, *, cost_usd: Decimal | None = None) -> None:
        super().__init__(message)
        self.cost_usd = cost_usd


class AnswerReader(Protocol):
    """Reads a checkpointed response body. Used live and on every replay, so one parse path."""

    def read_answer(self, raw: bytes) -> RecognisedPage: ...


class RepairTransport(AnswerReader, Protocol):
    """The provider seam. :mod:`auditmanager.norms.__main__` composes the proxy behind it.

    ``dispatch`` sends one try with ``call_id`` as its idempotency scope. It must hand the
    complete 200 body to ``checkpoint`` *before* parsing it, and raise :class:`CallFailure`
    for a try that produced no body. ``model`` is the configured model, named explicitly.
    """

    model: str

    def prepare(self, page: PageToRecognise) -> PreparedRequest: ...

    def dispatch(
        self, prepared: PreparedRequest, *, call_id: str, checkpoint: Callable[[bytes], None]
    ) -> None: ...


class JournalRefused(RuntimeError):
    """The journal and the database disagree in a way no rule resolves; nothing was spent."""


class RunStopped(RuntimeError):
    """The run stopped on a rule and says which. ``reason`` is a stable token."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(f"{reason}: {message}")
        self.reason = reason


class StopReason:
    CEILING = "ceiling_reached"
    SAMPLE_ABOVE_CEILING = "sample_projects_above_ceiling"
    NO_SAMPLE_VERDICT = "sample_verdict_missing"
    CREDENTIAL_REFUSED = Failure.CREDENTIAL_REFUSED
    REQUEST_REFUSED = Failure.REQUEST_REFUSED
    MODEL_MISMATCH = Failure.MODEL_MISMATCH
    UNPRICED = Failure.UNPRICED
    PROXY_UNAVAILABLE = "proxy_unavailable"
