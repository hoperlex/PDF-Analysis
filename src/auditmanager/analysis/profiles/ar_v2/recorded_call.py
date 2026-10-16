"""Pure model-call facts from the exact offline AR v2 replay.

This is a pre-persistence value. The durable stage still owns its call journal,
provider identity, cost policy and transaction. No fixture replay is a live call.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from auditmanager.analysis.engine.serialization import canonical_bytes, sha256_hex
from auditmanager.analysis.profiles.ar_v2.recorded_input import RecordedV2Input
from auditmanager.analysis.profiles.ar_v2.recorded_response import RecordedReplayResult
from auditmanager.analysis.text.config import ProviderMode
from auditmanager.analysis.text.provenance import CALL_SUCCEEDED, CALL_TRUNCATED
from auditmanager.shared.identity import ModelCallId


class RecordedCallFactsError(ValueError):
    """The replay cannot support an auditable recorded call."""


@dataclass(frozen=True, slots=True)
class RecordedCallFacts:
    model_call_id: str
    model_id: str
    provider_mode: ProviderMode
    request_sha256: str
    response_sha256: str
    source_binding_sha256: str
    parameters_json: bytes
    input_tokens: int
    output_tokens: int
    latency_ms: int
    status: str

    @property
    def parameters(self) -> Mapping[str, Any]:
        """A fresh value copy; mutation cannot change the retained facts."""
        return json.loads(self.parameters_json)


def build_recorded_call_facts(
    *, prepared: RecordedV2Input, replay: RecordedReplayResult, model_call_id: str,
) -> RecordedCallFacts:
    """Retain response usage from the one response already read by the adapter.

    The caller allocates the ID before replay and must persist it under the same
    run. This function never reads a recording again or infers a monetary cost.
    """
    if not isinstance(prepared, RecordedV2Input) or not isinstance(replay, RecordedReplayResult):
        raise RecordedCallFactsError("recorded_inputs_required")
    try:
        call_id = str(ModelCallId.parse(model_call_id))
    except (TypeError, ValueError):
        raise RecordedCallFactsError("invalid_model_call_id") from None
    response = replay.response
    request = prepared.request
    if (
        replay.provider_mode is not ProviderMode.RECORDED
        or not isinstance(replay.model_id, str)
        or not replay.model_id.startswith("fixture/")
        or request.model_id != replay.model_id
        or request.body.get("model") != replay.model_id
        or request.request_sha256 != replay.request_sha256
    ):
        raise RecordedCallFactsError("recorded_request_mismatch")
    expected_binding = sha256_hex(canonical_bytes({
        "version_uid": prepared.version_uid,
        "text_layer_ref": prepared.text_layer_ref.to_document(),
        "recognised_ref": (
            None if prepared.recognised_ref is None
            else prepared.recognised_ref.to_document()
        ),
        "textless_pages": prepared.textless_pages,
        "request_sha256": request.request_sha256,
    }))
    if expected_binding != prepared.source_binding_sha256 or expected_binding != replay.source_binding_sha256:
        raise RecordedCallFactsError("recorded_source_binding_mismatch")
    if (
        response.response_sha256 != replay.response_sha256
        or response.response_sha256 != replay.finished.response_sha256
        or replay.finished.truncated != response.truncated
        or response.reported_cost_usd is not None
    ):
        raise RecordedCallFactsError("recorded_response_mismatch")
    if response.stop_reason not in {"end_turn", "max_tokens"}:
        raise RecordedCallFactsError("recorded_stop_reason_invalid")
    if any(type(value) is not int or value < 0 for value in (
        response.input_tokens, response.output_tokens, response.latency_ms,
    )):
        raise RecordedCallFactsError("recorded_usage_invalid")
    parameters_json = canonical_bytes(request.parameters)
    return RecordedCallFacts(
        model_call_id=call_id,
        model_id=replay.model_id,
        provider_mode=ProviderMode.RECORDED,
        request_sha256=request.request_sha256,
        response_sha256=response.response_sha256,
        source_binding_sha256=expected_binding,
        parameters_json=parameters_json,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        latency_ms=response.latency_ms,
        status=CALL_TRUNCATED if response.truncated else CALL_SUCCEEDED,
    )


__all__ = ["RecordedCallFacts", "RecordedCallFactsError", "build_recorded_call_facts"]
