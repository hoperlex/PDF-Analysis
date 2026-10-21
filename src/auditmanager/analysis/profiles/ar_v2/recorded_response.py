"""Replay one verified AR v2 request and finish its PDF evidence offline.

This boundary has no provider selector or persistence. The caller supplies the
exact request/model identities from its durable execution context; a recording
is read only through the concrete offline adapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditmanager.analysis.engine.serialization import canonical_bytes, sha256_hex
from auditmanager.analysis.profiles.ar_v2.recorded_input import RecordedV2Input
from auditmanager.analysis.profiles.ar_v2.response_pipeline import (
    FinishedV2Response,
    finish_response,
)
from auditmanager.analysis.text.adapter import ModelResponse
from auditmanager.analysis.text.config import ProviderMode
from auditmanager.analysis.text.recorded import RecordedAdapter


class RecordedResponseError(ValueError):
    """The replay context is not the exact verified recorded request."""


@dataclass(frozen=True, slots=True)
class RecordedReplayResult:
    model_id: str
    provider_mode: ProviderMode
    request_sha256: str
    source_binding_sha256: str
    response_sha256: str
    finished: FinishedV2Response
    response: ModelResponse


def replay_recorded_response(
    *,
    prepared: RecordedV2Input,
    adapter: RecordedAdapter,
    expected_request_sha256: str,
    expected_model_id: str,
    expected_source_binding_sha256: str,
) -> RecordedReplayResult:
    """Make exactly one offline replay, then parse, ground and prepare merge.

    ``prepared`` must have come from verified source artifacts. The three
    expected identities come from the caller's saved execution context, not
    from a recording. This check precedes the adapter's only read.
    """
    if not isinstance(prepared, RecordedV2Input):
        raise RecordedResponseError("invalid_recorded_input")
    # A general ModelAdapter can claim recorded mode while making live calls.
    # The concrete adapter has no network client or fallback path.
    if type(adapter) is not RecordedAdapter or adapter.provider_mode is not ProviderMode.RECORDED:
        raise RecordedResponseError("recorded_adapter_required")

    request = prepared.request
    if (
        not isinstance(expected_model_id, str)
        or not expected_model_id.startswith("fixture/")
        or request.model_id != expected_model_id
        or request.body.get("model") != expected_model_id
    ):
        raise RecordedResponseError("recorded_model_mismatch")
    if request.request_sha256 != expected_request_sha256:
        raise RecordedResponseError("recorded_request_mismatch")
    source_binding_sha256 = sha256_hex(canonical_bytes({
        "version_uid": prepared.version_uid,
        "text_layer_ref": prepared.text_layer_ref.to_document(),
        "recognised_ref": (
            None if prepared.recognised_ref is None
            else prepared.recognised_ref.to_document()
        ),
        "textless_pages": prepared.textless_pages,
        "request_sha256": request.request_sha256,
    }))
    if (
        source_binding_sha256 != prepared.source_binding_sha256
        or source_binding_sha256 != expected_source_binding_sha256
    ):
        raise RecordedResponseError("recorded_source_binding_mismatch")

    response = adapter.complete(request)
    finished = finish_response(
        response, prepared.text_layer,
        recognised_context=prepared.recognised_context,
    )
    return RecordedReplayResult(
        model_id=expected_model_id,
        provider_mode=ProviderMode.RECORDED,
        request_sha256=request.request_sha256,
        source_binding_sha256=source_binding_sha256,
        response_sha256=response.response_sha256,
        finished=finished,
        response=response,
    )


__all__ = ["RecordedReplayResult", "RecordedResponseError", "replay_recorded_response"]
