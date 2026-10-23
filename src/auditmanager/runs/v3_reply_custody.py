"""Read the private AR v3 reply Blob for deterministic CITE replay.

The caller must obtain the expectation from a completed, owned model call and
its effect; a Blob alone is never proof of a provider call or expert decision.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass

from auditmanager.analysis.public import ArtifactRef, ModelResponse, SuppliedV3Response
from auditmanager.runs.v3_provider_call import (
    MAX_REPLY_BYTES, REPLY_ARTIFACT_ROLE, REPLY_FORMAT,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobStore, parse_blob_id


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_FIELDS = frozenset({
    "format", "run_id", "model_call_id", "provider", "candidate_sha256",
    "request_sha256", "response_sha256", "output_text", "stop_reason",
    "input_tokens", "output_tokens", "latency_ms", "reported_cost_usd",
    "reported_model",
})


@dataclass(frozen=True, slots=True)
class V3ReplyExpectation:
    run_id: str
    model_call_id: str
    provider: str
    candidate_sha256: str
    request_sha256: str
    response_sha256: str


@dataclass(frozen=True, slots=True)
class V3RecoveredReply:
    model_response: ModelResponse
    supplied_response: SuppliedV3Response


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="the saved AR v3 provider reply does not match its completed call",
        stage_id="text_analysis", reason=reason,
    )


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate reply key")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON constant {value}")


def read_v3_reply(
    blob_store: BlobStore, *, reference: ArtifactRef,
    expected: V3ReplyExpectation,
) -> V3RecoveredReply:
    """Verify exact Blob bytes and call pins; return only an untrusted answer."""
    if (not isinstance(reference, ArtifactRef)
            or reference.role != REPLY_ARTIFACT_ROLE
            or reference.media_type != "application/json"
            or reference.size_bytes < 1
            or reference.size_bytes > MAX_REPLY_BYTES
            or not isinstance(expected, V3ReplyExpectation)
            or not all(isinstance(value, str) and value for value in (
                expected.run_id, expected.model_call_id, expected.provider,
            ))
            or any(not isinstance(value, str) or _SHA256.fullmatch(value) is None for value in (
                expected.candidate_sha256, expected.request_sha256,
                expected.response_sha256,
            ))):
        raise _refuse("reply_reference_or_expectation_invalid")
    payload = blob_store.read(parse_blob_id(reference.blob_id), verify=True)
    if (len(payload) != reference.size_bytes
            or hashlib.sha256(payload).hexdigest() != reference.sha256):
        raise _refuse("reply_blob_digest_mismatch")
    try:
        document = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, ValueError, TypeError) as exc:
        raise _refuse("reply_json_invalid") from exc
    if not isinstance(document, dict) or frozenset(document) != _FIELDS:
        raise _refuse("reply_envelope_invalid")
    for key, value in {
        "format": REPLY_FORMAT,
        "run_id": expected.run_id,
        "model_call_id": expected.model_call_id,
        "provider": expected.provider,
        "candidate_sha256": expected.candidate_sha256,
        "request_sha256": expected.request_sha256,
        "response_sha256": expected.response_sha256,
    }.items():
        if document[key] != value:
            raise _refuse("reply_call_binding_mismatch")
    if (not isinstance(document["output_text"], str)
            or not isinstance(document["stop_reason"], str)
            or any(type(document[key]) is not int or document[key] < 0 for key in (
                "input_tokens", "output_tokens", "latency_ms",
            ))
            or (document["reported_model"] is not None
                and not isinstance(document["reported_model"], str))):
        raise _refuse("reply_fields_invalid")
    cost = document["reported_cost_usd"]
    if cost is not None and (
        isinstance(cost, bool) or not isinstance(cost, (int, float))
        or not math.isfinite(cost) or cost < 0
    ):
        raise _refuse("reply_cost_invalid")
    response = ModelResponse(
        output_text=document["output_text"],
        stop_reason=document["stop_reason"],
        input_tokens=document["input_tokens"],
        output_tokens=document["output_tokens"],
        latency_ms=document["latency_ms"],
        reported_cost_usd=cost,
        model=document["reported_model"],
    )
    if response.response_sha256 != expected.response_sha256:
        raise _refuse("reply_response_digest_mismatch")
    return V3RecoveredReply(
        model_response=response,
        supplied_response=SuppliedV3Response(
            request_sha256=expected.candidate_sha256,
            output_text=response.output_text,
            truncated=response.truncated,
        ),
    )


__all__ = ["V3RecoveredReply", "V3ReplyExpectation", "read_v3_reply"]
