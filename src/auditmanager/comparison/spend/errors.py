"""The typed refusals and failures of a comparison model call (`CMP-SPEND-01`).

Not catalogue errors: a worker handler is the only caller, and none of these reaches the HTTP layer,
so no code of the error catalogue is added (the contract stays as sealed). Every one carries a
``reason`` that is a lower-case code, the same shape a work item's ``failure_reason`` takes, so a
handler turns it into the item's outcome with :meth:`SpendError.as_outcome` and no free text ever
reaches the queue, a log line or the journal.

Three families, by how much is known about the money:

* :class:`CallRefused` -- **before** the adapter was called. Nothing was sent and nothing was
  spent; the journal has no row for it (or, for a lost lease, a ``failed`` one).
* :class:`CallFailed` -- the adapter was called and the journal says ``failed``: either nothing was
  sent (a proven pre-dispatch refusal) or what the provider answered is recorded with its cost.
* :class:`OutcomeUnknown` -- the adapter was called and nothing proves whether the provider did
  billable work. The journal says ``unknown``; the wrapper never sends again by itself.
"""

from __future__ import annotations

from typing import Final

from auditmanager.comparison.work.model import Failed, Outcome, Yielded

__all__ = [
    "CallFailed",
    "CallLost",
    "CallRefused",
    "OutcomeUnknown",
    "REASON_CALL_FAILED",
    "REASON_CONNECTION_BUSY",
    "REASON_CONSENT_REQUIRED",
    "REASON_CONSENT_STALE",
    "REASON_DAY_CEILING",
    "REASON_IMAGES_UNSUPPORTED",
    "REASON_JOB_CEILING",
    "REASON_LEASE_LOST",
    "REASON_MODEL_IDENTITY",
    "REASON_MODEL_NOT_SELECTED",
    "REASON_OVERRUN",
    "REASON_SPEND_UNKNOWN",
    "REASON_UNSETTLED_CALL",
    "SpendError",
]

REASON_CONSENT_REQUIRED: Final[str] = "consent_required"
#: The route, the connection's revision or the pinned model is not the one the consent was given for
#: (ADR-0025 decision 19): the job pauses and asks for a new consent.
REASON_CONSENT_STALE: Final[str] = "consent_stale"
#: A live call whose reply must be held to a model, with no model selected (a gateway stub or nothing):
#: the call fails closed before it is made (`R-133`).
REASON_MODEL_NOT_SELECTED: Final[str] = "model_not_selected"
REASON_JOB_CEILING: Final[str] = "job_ceiling"
REASON_DAY_CEILING: Final[str] = "day_ceiling"
#: The actual spend of the job is above 1.2 x the estimate the consent was given for.
REASON_OVERRUN: Final[str] = "overrun"
#: A Run, or another comparison call, is using the connection (one active user per connection).
REASON_CONNECTION_BUSY: Final[str] = "connection_busy"
#: An earlier attempt of the item left a call that is neither settled nor re-queued; the item is
#: never sent again by itself.
REASON_UNSETTLED_CALL: Final[str] = "unsettled_call"
REASON_MODEL_IDENTITY: Final[str] = "model_identity_mismatch"
REASON_SPEND_UNKNOWN: Final[str] = "spend_unknown"
REASON_CALL_FAILED: Final[str] = "model_call_failed"
#: The runner of a pull connection refused the images (`CMP-EXEC-IMAGES-01`).
REASON_IMAGES_UNSUPPORTED: Final[str] = "executor_image_input_unsupported"
REASON_LEASE_LOST: Final[str] = "lease_lost"

#: How long an item whose connection is busy waits before it is offered again.
BUSY_RETRY_SECONDS: Final[float] = 15.0


class SpendError(Exception):
    """Base of the three families; ``reason`` is a code and the only text a caller may store."""

    reason: str

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason

    def as_outcome(self) -> Outcome:
        """What a handler returns for this error: ``Failed(reason)`` unless a subclass knows better."""
        return Failed(self.reason)


class CallRefused(SpendError):
    """The call was not made. ``pauses_job`` says the job layer should pause the job and ask for a new
    consent (a consent that no longer holds, a ceiling, an overrun); ``False`` is a wait."""

    def __init__(self, reason: str, *, pauses_job: bool) -> None:
        super().__init__(reason)
        self.pauses_job = pauses_job

    def as_outcome(self) -> Outcome:
        if self.reason == REASON_CONNECTION_BUSY:
            return Yielded(BUSY_RETRY_SECONDS)
        return Failed(self.reason)


class CallFailed(SpendError):
    """The adapter was called and the journal row is ``failed``. ``retry_safe`` is the transport's
    own word that a new call cannot double-spend (a proven pre-dispatch refusal)."""

    def __init__(self, reason: str, *, call_id: str, retry_safe: bool = False) -> None:
        super().__init__(reason)
        self.call_id = call_id
        self.retry_safe = retry_safe

    def as_outcome(self) -> Outcome:
        return Failed(self.reason, retry=self.retry_safe)


class OutcomeUnknown(SpendError):
    """The adapter was called and the journal row is ``unknown``. The wrapper does not send again;
    only an explicit retry of the item does (decision 5)."""

    def __init__(self, *, call_id: str) -> None:
        super().__init__(REASON_SPEND_UNKNOWN)
        self.call_id = call_id


class CallLost(SpendError):
    """The attempt no longer holds the item: the lease was reclaimed before the call was sent, or
    while it was in flight (the reclaim has already settled the row ``unknown``). Nothing may be
    published from this call."""

    def __init__(self, *, call_id: str | None) -> None:
        super().__init__(REASON_LEASE_LOST)
        self.call_id = call_id
