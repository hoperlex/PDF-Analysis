"""Saved v3 reply is accepted only with exact Blob and call bindings."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from auditmanager.analysis.public import ArtifactRef, ModelResponse
from auditmanager.runs.v3_provider_call import REPLY_ARTIFACT_ROLE, REPLY_FORMAT
from auditmanager.runs.v3_reply_custody import V3ReplyExpectation, read_v3_reply
from auditmanager.shared.errors import DomainError
from auditmanager.storage.public import derive_blob_id


RESPONSE = ModelResponse("ответ", "max_tokens", 12, 34, 56, 0.02, "model-1")
EXPECTED = V3ReplyExpectation(
    "run_test", "call_test", "http_api", "a" * 64, "b" * 64,
    RESPONSE.response_sha256,
)


class Store:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.reads = 0

    def read(self, blob_id, *, verify):
        assert verify is True
        self.reads += 1
        return self.payload


def _reply(**changes):
    value = {
        "format": REPLY_FORMAT, "run_id": EXPECTED.run_id,
        "model_call_id": EXPECTED.model_call_id, "provider": EXPECTED.provider,
        "candidate_sha256": EXPECTED.candidate_sha256,
        "request_sha256": EXPECTED.request_sha256,
        "response_sha256": EXPECTED.response_sha256,
        "output_text": RESPONSE.output_text, "stop_reason": RESPONSE.stop_reason,
        "input_tokens": RESPONSE.input_tokens,
        "output_tokens": RESPONSE.output_tokens,
        "latency_ms": RESPONSE.latency_ms,
        "reported_cost_usd": RESPONSE.reported_cost_usd,
        "reported_model": RESPONSE.model,
    }
    value.update(changes)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _ref(payload):
    digest = hashlib.sha256(payload).hexdigest()
    return ArtifactRef(
        REPLY_ARTIFACT_ROLE,
        str(derive_blob_id(sha256=digest, size=len(payload))),
        digest, len(payload), "application/json",
    )


def test_complete_reply_replays_as_untrusted_citation_input():
    payload = _reply()
    store = Store(payload)
    result = read_v3_reply(store, reference=_ref(payload), expected=EXPECTED)
    assert store.reads == 1
    assert result.model_response == RESPONSE
    assert result.supplied_response.request_sha256 == EXPECTED.candidate_sha256
    assert result.supplied_response.output_text == "ответ"
    assert result.supplied_response.truncated is True


@pytest.mark.parametrize("change,reason", [
    ({"run_id": "other"}, "reply_call_binding_mismatch"),
    ({"model_call_id": "other"}, "reply_call_binding_mismatch"),
    ({"candidate_sha256": "c" * 64}, "reply_call_binding_mismatch"),
    ({"request_sha256": "c" * 64}, "reply_call_binding_mismatch"),
    ({"response_sha256": "c" * 64}, "reply_call_binding_mismatch"),
    ({"output_text": "другой ответ"}, "reply_response_digest_mismatch"),
    ({"output_tokens": -1}, "reply_fields_invalid"),
    ({"input_tokens": True}, "reply_fields_invalid"),
    ({"reported_cost_usd": -1.0}, "reply_cost_invalid"),
    ({"unexpected": "field"}, "reply_envelope_invalid"),
])
def test_resealed_but_wrong_envelope_is_refused(change, reason):
    payload = _reply(**change)
    with pytest.raises(DomainError) as invalid:
        read_v3_reply(Store(payload), reference=_ref(payload), expected=EXPECTED)
    assert invalid.value.detail_fields["reason"] == reason


def test_wrong_ref_or_changed_bytes_refuses_before_or_after_blob_read():
    payload = _reply()
    store = Store(payload)
    with pytest.raises(DomainError):
        read_v3_reply(
            store, reference=replace(_ref(payload), role="analysis.text_observations"),
            expected=EXPECTED,
        )
    assert store.reads == 0
    with pytest.raises(DomainError) as changed:
        read_v3_reply(
            Store(payload + b" "), reference=_ref(payload), expected=EXPECTED,
        )
    assert changed.value.detail_fields["reason"] == "reply_blob_digest_mismatch"


def test_duplicate_keys_and_nonfinite_numbers_are_refused():
    payload = _reply().replace(b'"format":', b'"format":"wrong","format":', 1)
    with pytest.raises(DomainError) as duplicate:
        read_v3_reply(Store(payload), reference=_ref(payload), expected=EXPECTED)
    assert duplicate.value.detail_fields["reason"] == "reply_json_invalid"
    payload = _reply().replace(b'"reported_cost_usd":0.02', b'"reported_cost_usd":NaN')
    with pytest.raises(DomainError) as nonfinite:
        read_v3_reply(Store(payload), reference=_ref(payload), expected=EXPECTED)
    assert nonfinite.value.detail_fields["reason"] == "reply_json_invalid"
