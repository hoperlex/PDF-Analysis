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
    output_tokens: int
    latency_ms: int
    status: str
    cost_usd: float

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
