"""CITE only consumes a saved request, one completed call and exact reply."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import ModelResponse, V3GenerationSettings
from auditmanager.jobs.public import AttemptAuthority, V3CompletedCall
from auditmanager.runs import v3_cite_preflight as preflight
from auditmanager.runs.v3_provider_call import REPLY_FORMAT
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import derive_blob_id


AUTHORITY = AttemptAuthority("run_test", "job_test", "att_cite", "lease_test", "secret")
RESPONSE = ModelResponse("{\"observations\":[]}", "end_turn", 11, 13, 17, 0.012,
                         "reported-gateway-model")
SETTINGS = V3GenerationSettings(4096, "high", {"type": "adaptive"})


class FakeJobs:
    def __init__(self, call, order):
        self.call = call
        self.order = order
        self.reads = 0
        self.change_after_reply = False

    def completed_v3_call(self, session, authority, *, lock_authority=True):
        assert authority is AUTHORITY
        self.order.append("call_lock" if lock_authority else "call_peek")
        self.reads += 1
        if self.change_after_reply and self.reads == 2:
            return replace(self.call, reply_blob_sha256="f" * 64)
        return self.call


class FakeStore:
    def __init__(self, payload, order):
        self.payload = payload
        self.order = order
        self.reads = 0

    def read(self, blob_id, *, verify):
        assert verify is True
        self.order.append("reply_blob")
        self.reads += 1
        return self.payload


def _payload(response=RESPONSE, **changes):
    data = {
        "format": REPLY_FORMAT, "run_id": AUTHORITY.run_id,
        "model_call_id": "call_test", "provider": "http_api",
        "candidate_sha256": "a" * 64, "request_sha256": "b" * 64,
        "response_sha256": response.response_sha256,
        "output_text": response.output_text, "stop_reason": response.stop_reason,
        "input_tokens": response.input_tokens, "output_tokens": response.output_tokens,
        "latency_ms": response.latency_ms,
        "reported_cost_usd": response.reported_cost_usd,
        "reported_model": response.model,
    }
    data.update(changes)
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def _call(payload):
    digest = hashlib.sha256(payload).hexdigest()
    return V3CompletedCall(
        run_id=AUTHORITY.run_id, job_id=AUTHORITY.job_id,
        attempt_id="att_prior", model_call_id="call_test", provider="http_api",
        model_id="model-pin", provider_mode="live", request_sha256="b" * 64,
        response_sha256=RESPONSE.response_sha256, candidate_sha256="a" * 64,
        scope_id="F1", set_sha256="c" * 64,
        max_output_tokens=4096, effort="high",
        reply_blob_id=str(derive_blob_id(sha256=digest, size=len(payload))),
        reply_blob_sha256=digest, reply_blob_size=len(payload),
        input_tokens=11, output_tokens=13, latency_ms=17,
        cost_micros=12000, cost_basis="measured", status="succeeded",
        connection_revision_id="rev_test", identity_basis="pinned",
    )


def _arrange(monkeypatch, *, call=None, payload=None, binding_changes=None,
             prepared_changes=None):
    payload = payload or _payload()
    call = call or _call(payload)
    binding = SimpleNamespace(run_id=AUTHORITY.run_id, scope_id="F1",
                              set_sha256="c" * 64, provider_mode="live")
    if binding_changes:
        binding = SimpleNamespace(**{**vars(binding), **binding_changes})
    prepared = SimpleNamespace(
        binding=binding, candidate_sha256="a" * 64,
        provider_body_sha256="b" * 64,
        pinned_corpus=object(),
        saved_text=SimpleNamespace(text_layer=object()),
    )
    if prepared_changes:
        prepared = SimpleNamespace(**{**vars(prepared), **prepared_changes})
    observed = {"order": []}
    jobs = FakeJobs(call, observed["order"])
    store = FakeStore(payload, observed["order"])

    def prepare(session, **kwargs):
        observed["order"].append("request_blobs")
        assert kwargs["defer_final_fence"] is True
        assert kwargs["authority"] is AUTHORITY
        assert kwargs["expected_provider_mode"] == call.provider_mode
        assert kwargs["model_identity"] == call.model_id
        assert kwargs["idempotency_scope"] == AUTHORITY.run_id
        assert kwargs["settings"] == SETTINGS
        return prepared

    def review(corpus, reply, text_layer):
        observed["order"].append("review")
        assert corpus is prepared.pinned_corpus
        assert text_layer is prepared.saved_text.text_layer
        observed["reply"] = reply
        return "review-only"

    monkeypatch.setattr(preflight, "prepare_v3_execution_request", prepare)
    monkeypatch.setattr(preflight, "plan_v3_beta_citation_review", review)
    def fence(session, **kwargs):
        observed["order"].append("request_lock")
        assert kwargs["prepared"] is prepared
        assert kwargs["authority"] is AUTHORITY

    monkeypatch.setattr(preflight, "fence_v3_execution_request", fence)
    return jobs, store, prepared, observed


def _execute(jobs, store):
    return preflight.prepare_v3_cite_preflight(
        object(), authority=AUTHORITY, registry=object(), blob_store=store,
        max_text_bytes=100_000, jobs=jobs,
    )


def test_prior_attempt_call_and_reply_feed_only_review(monkeypatch):
    jobs, store, prepared, observed = _arrange(monkeypatch)
    result = _execute(jobs, store)
    assert result.prepared is prepared
    assert result.completed_call.attempt_id == "att_prior"
    assert result.recovered_reply.model_response == RESPONSE
    assert observed["reply"].request_sha256 == "a" * 64
    assert result.review == "review-only"
    assert jobs.reads == 2 and store.reads == 1
    assert observed["order"] == [
        "call_peek", "request_blobs", "reply_blob", "review",
        "request_lock", "call_lock",
    ]
    assert not hasattr(result, "normative_candidates")


@pytest.mark.parametrize(("field", "value"), [
    ("run_id", "run_foreign"), ("job_id", "job_foreign"),
    ("candidate_sha256", "d" * 64), ("request_sha256", "d" * 64),
    ("scope_id", "F2"), ("set_sha256", "d" * 64),
])
def test_foreign_call_or_saved_request_refuses_before_reply(monkeypatch, field, value):
    payload = _payload()
    jobs, store, _, _ = _arrange(monkeypatch, call=replace(_call(payload), **{field: value}),
                                  payload=payload)
    with pytest.raises(DomainError) as caught:
        _execute(jobs, store)
    assert caught.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert caught.value.detail_fields["stage_id"] == "text_analysis"
    assert store.reads == 0


@pytest.mark.parametrize("changes", [
    {"input_tokens": 12}, {"latency_ms": 18},
    {"reported_model": None}, {"reported_cost_usd": 0.02},
    {"stop_reason": "max_tokens"},
])
def test_reply_facts_refuse_even_with_self_consistent_blob(monkeypatch, changes):
    payload = _payload(**changes)
    jobs, store, _, _ = _arrange(monkeypatch, payload=payload)
    with pytest.raises(DomainError) as caught:
        _execute(jobs, store)
    assert caught.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert store.reads == 1


def test_changed_call_after_review_refuses(monkeypatch):
    jobs, store, _, observed = _arrange(monkeypatch)
    jobs.change_after_reply = True
    with pytest.raises(DomainError) as caught:
        _execute(jobs, store)
    assert caught.value.detail_fields["reason"] == "saved_evidence_changed_during_review"
    assert "reply" in observed


def test_changed_saved_settings_at_final_call_fence_refuse(monkeypatch):
    jobs, store, _, observed = _arrange(monkeypatch)
    original = jobs.completed_v3_call

    def changed(session, authority, *, lock_authority=True):
        call = original(session, authority, lock_authority=lock_authority)
        return replace(call, effort="medium") if lock_authority else call

    jobs.completed_v3_call = changed
    with pytest.raises(DomainError) as caught:
        _execute(jobs, store)
    assert caught.value.detail_fields["reason"] == "saved_evidence_changed_during_review"
    assert store.reads == 1
    assert "reply" in observed


def test_truncated_completed_call_cannot_yield_provisional_review(monkeypatch):
    truncated = replace(RESPONSE, stop_reason="max_tokens")
    payload = _payload(response=truncated)
    call = replace(_call(payload), response_sha256=truncated.response_sha256,
                   status="truncated")
    jobs, store, _, observed = _arrange(monkeypatch, call=call, payload=payload)
    with pytest.raises(DomainError) as caught:
        _execute(jobs, store)
    assert caught.value.detail_fields["reason"] == "saved_reply_incomplete"
    assert "reply" not in observed


def test_changed_binding_after_review_refuses(monkeypatch):
    jobs, store, prepared, _ = _arrange(monkeypatch)
    def changed_binding(*args, **kwargs):
        raise DomainError(ErrorCode.REQUIRED_NORM_UNAVAILABLE,
                          reason="group_binding_changed_during_read")
    monkeypatch.setattr(preflight, "fence_v3_execution_request", changed_binding)
    with pytest.raises(DomainError) as caught:
        _execute(jobs, store)
    assert caught.value.detail_fields["reason"] == "group_binding_changed_during_read"


def test_stale_current_attempt_from_completed_call_propagates(monkeypatch):
    jobs, store, _, _ = _arrange(monkeypatch)

    def stale(session, authority, *, lock_authority=True):
        raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")

    jobs.completed_v3_call = stale
    with pytest.raises(DomainError) as caught:
        _execute(jobs, store)
    assert caught.value.code is ErrorCode.STALE_ATTEMPT
    assert store.reads == 0


def test_stale_attempt_at_final_call_fence_refuses_after_reply(monkeypatch):
    jobs, store, _, observed = _arrange(monkeypatch)
    original = jobs.completed_v3_call

    def stale_at_final(session, authority, *, lock_authority=True):
        if lock_authority:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")
        return original(session, authority, lock_authority=False)

    jobs.completed_v3_call = stale_at_final
    with pytest.raises(DomainError) as caught:
        _execute(jobs, store)
    assert caught.value.code is ErrorCode.STALE_ATTEMPT
    assert store.reads == 1
    assert observed["order"][-2:] == ["review", "request_lock"]
