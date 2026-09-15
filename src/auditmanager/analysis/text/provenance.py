"""Model call records, and the guard that keeps a replay from looking like a call.

A recorded run must never be presentable as a live one. That is a named ``PC-01``
acceptance criterion, and it is held by four separate mechanics rather than by a
convention:

1. ``ProviderMode`` is a closed two-member enum (:mod:`.config`), so there is no third
   value and no free-text mode anywhere.
2. The mode is a read-only class constant on the adapter (:mod:`.adapter`), stamped by
   the object that actually produced the response. A caller cannot pass one in.
3. A recording file on disk carries **no mode field at all** (:mod:`.recorded`), so
   editing a recording cannot make it claim to be live. There is nothing to edit.
4. :func:`assert_consistent_mode` refuses to publish an artifact whose declared mode
   disagrees with any of the call records behind it, so the artifact and its evidence
   cannot say different things.

``model_call`` rows are immutable after insert (``P02_SEAMS.md`` section 3.1), so a
record is built complete or not at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from auditmanager.analysis.text.config import ProviderMode
from auditmanager.analysis.text.lock import STAGE_ID
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId

#: Terminal states of one provider call. Distinct from a stage status.
CALL_SUCCEEDED = "succeeded"
CALL_TRUNCATED = "truncated"
CALL_FAILED = "failed"

#: The closed vocabulary, named once so that no reader has to infer it from three
#: constants that merely happen to sit together. ``model_call.status`` holds exactly
#: these three (migration ``0005``), and :class:`ModelCallRecord` refuses anything else
#: at the layer that builds the row rather than leaving it to the CHECK: a record that
#: cannot be persisted should not be constructible.
CALL_STATUSES: frozenset[str] = frozenset({CALL_SUCCEEDED, CALL_TRUNCATED, CALL_FAILED})

#: What ``truncated`` asserts, stated as a rule rather than as prose. A truncated call
#: *answered*: the provider produced output and stopped at the ceiling part-way through,
#: so there is a response and it has a checksum. A call with no response is a failure,
#: whatever its stop reason said.
_STATUSES_THAT_ANSWERED: frozenset[str] = frozenset({CALL_SUCCEEDED, CALL_TRUNCATED})


@dataclass(frozen=True, slots=True)
class ModelCallRecord:
    """One provider call, recorded whether it was live or replayed.

    ``provider_mode`` is set from the adapter's constant at construction and is never
    a caller's opinion. The request and response checksums are what make a recorded
    run auditable: the same pair identifies the same question and the same answer.
    """

    model_call_id: ModelCallId
    provider: str
    model_id: str
    provider_mode: ProviderMode
    parameters: Mapping[str, Any]
    request_sha256: str
    response_sha256: str
    input_tokens: int
    #: The provider's own figure for how much the model said, lifted verbatim out of its
    #: usage block by the adapter. It is never recomputed from ``output_text``: the two
    #: answer different questions, and they diverge precisely where this figure is worth
    #: recording. A reply cut short at the ceiling reports the whole ceiling here while
    #: only its complete prefix survives parsing, and a reply that reasons at length and
    #: publishes nothing reports that reasoning here and no observation anywhere.
    output_tokens: int
    latency_ms: int
    status: str
    cost_usd: float
    #: Whether ``cost_usd`` was reported by the transport or derived from the pinned rate
    #: table. Carried on the record rather than inferred downstream: this is the only layer
    #: that saw the response and therefore the only one that knows.
    cost_basis: str = "estimated"

    def __post_init__(self) -> None:
        """Refuse a record the database would refuse, at the layer that knows why.

        The three checks below mirror ``ck_model_call_status``,
        ``ck_model_call_truncated_has_response`` and ``ck_model_call_tokens``. Duplicating
        them here is not belt-and-braces: this is the only layer that saw the response, so
        it is the only one that can say *which* provider call was malformed, and a
        constraint violation surfacing from an INSERT several frames later names a row id
        and nothing about the call.
        """
        if self.status not in CALL_STATUSES:
            raise DomainError(
                ErrorCode.ANALYSIS_FAILED,
                message=(
                    "a model call record declared a status outside the closed vocabulary "
                    "succeeded|truncated|failed; the run provenance is not publishable"
                ),
                stage_id=STAGE_ID,
            )
        if self.status in _STATUSES_THAT_ANSWERED and not self.response_sha256:
            raise DomainError(
                ErrorCode.ANALYSIS_FAILED,
                message=(
                    "a model call record claims the provider answered but carries no "
                    "response checksum; the run provenance is not publishable"
                ),
                stage_id=STAGE_ID,
            )
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise DomainError(
                ErrorCode.ANALYSIS_FAILED,
                message=(
                    "a model call record carries a negative token count; the provider "
                    "reports usage and this layer never computes it, so a negative figure "
                    "means the usage block was not read"
                ),
                stage_id=STAGE_ID,
            )

    def as_dict(self) -> dict[str, Any]:
        """The record as it is written out. Every value is ASCII or a number."""
        return {
            "model_call_id": str(self.model_call_id),
            "provider": self.provider,
            "model_id": self.model_id,
            "provider_mode": self.provider_mode.value,
            "parameters": dict(self.parameters),
            "request_sha256": self.request_sha256,
            "response_sha256": self.response_sha256,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "cost_usd": round(self.cost_usd, 8),
            "cost_basis": self.cost_basis,
        }


def assert_consistent_mode(
    declared: ProviderMode, calls: Iterable[ModelCallRecord]
) -> ProviderMode:
    """Refuse to publish provenance that disagrees with itself.

    Reached only when the code above it has already gone wrong, which is exactly when
    a check earns its keep: the failure mode it prevents is a recorded run published
    with ``provider_mode: live``, and nothing downstream could detect that afterwards.
    """
    for call in calls:
        if call.provider_mode is not declared:
            raise DomainError(
                ErrorCode.ANALYSIS_FAILED,
                message=(
                    "the declared provider mode disagrees with a model call record; "
                    "the run provenance is not publishable"
                ),
                stage_id=STAGE_ID,
            )
    return declared
