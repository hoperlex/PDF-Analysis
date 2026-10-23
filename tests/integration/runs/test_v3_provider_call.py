"""AR v3 call boundaries: bytes, ordering, transport identity and durable failures."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import (
    ModelRequest, ModelResponse, ProviderConfig, ProviderMode,
    ProxyDispatchError, V3GenerationSettings,
)
from auditmanager.analysis.text.binding import CallBinding
from auditmanager.analysis.text.proxy import ReceivedResponse
from auditmanager.jobs.public import AttemptAuthority
from auditmanager.runs import v3_provider_call
from auditmanager.runs.provider import ProviderBinding
from auditmanager.shared.errors import DomainError, ErrorCode


AUTHORITY = AttemptAuthority("run_v3", "job_v3", "att_v3", "lease_v3", "secret")
SETTINGS = V3GenerationSettings(4096, "high", {"type": "adaptive"})
REQUEST = ModelRequest(
    "model-pin", {"model": "model-pin", "max_tokens": 4096,
                  "system": "original guide", "messages": [{"role": "user", "content": "N1: quote"}],
                  "thinking": {"type": "adaptive"}, "output_config": {"effort": "high"}},
)
RESPONSE = ModelResponse(
    '{"items":[]}', "end_turn", 123, 45, 67, 0.0042, "gateway-model",
)


class Session:
    def __init__(self, events: list[object]):
        self.events = events

    def commit(self):
        self.events.append("commit")


class Jobs:
    def __init__(self, events: list[object]):
        self.events = events
        self.calls = []
        self.duplicate = False

    def require_current(self, session, authority):
        assert authority == AUTHORITY
        self.events.append("current")

    def require_recorded_stage_call_available(self, session, authority):
        self.events.append("available")
        if self.duplicate:
            raise DomainError(ErrorCode.CONFLICT, aggregate_type="AuditRun")

    def prepare_provider_call(self, session, authority, **fields):
        self.events.append("prepared")
        self.calls.append(fields)
        return "call_v3"

    def record_provider_response(self, session, authority, **fields):
        self.events.append(("response", fields))

    def complete_provider_call(self, session, authority, *, call):
        self.events.append(("completed", call))

    def record_provider_not_processed(self, session, authority, **fields):
        self.events.append(("not_processed", fields))

    def record_provider_unknown(self, session, authority, **fields):
        self.events.append(("outcome_unknown", fields))


class Adapter:
    def __init__(self, mode, events, answer=RESPONSE):
        self.provider_mode = mode
        self.events = events
        self.answer = answer

    def complete(self, request):
        assert self.events[-1] == "current"
        assert "prepared" in self.events
        assert self.events.index("prepared") < self.events.index("commit")
        self.events.append(("dispatch", request))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def _arrange(monkeypatch, *, mode=ProviderMode.LIVE, answer=RESPONSE,
             call=None, binding_changes=(), prepared_error=None):
    events = []
    session, jobs = Session(events), Jobs(events)
    binding = SimpleNamespace(scope_id="F1", set_sha256="a" * 64)
    prepared = SimpleNamespace(
        binding=binding, model_request=REQUEST,
        candidate_sha256="b" * 64, provider_body_sha256=REQUEST.request_sha256,
    )
    def prepare(*args, **kwargs):
        events.append("assemble")
        if prepared_error is not None:
            raise prepared_error
        return prepared
    monkeypatch.setattr(v3_provider_call, "prepare_v3_execution_request", prepare)
    values = iter(binding_changes)
    def resolve(*args, **kwargs):
        events.append("current")
        candidate = next(values, None)
        return binding if candidate is None else candidate
    monkeypatch.setattr(v3_provider_call, "resolve_v3_execution_binding", resolve)
    if call is None and mode is ProviderMode.LIVE:
        call = CallBinding(
            provider_label="http_api", expected_model="gateway-model",
            check_identity=True, identity_basis="reported",
            connection_revision_id="rev_test",
        )
    config = ProviderConfig(mode, "model-pin", 1.0, None, True)
    provider = ProviderBinding(Adapter(mode, events, answer), config, call)
    kwargs = dict(
        authority=AUTHORITY, registry=object(), blob_store=object(),
        max_text_bytes=100_000, provider=provider, settings=SETTINGS,
        jobs=jobs, runs=object(),
    )
    return session, jobs, events, kwargs


@pytest.mark.parametrize("mode", (ProviderMode.LIVE, ProviderMode.RECORDED))
def test_exact_request_and_answer_are_journaled_around_transport(monkeypatch, mode):
    session, jobs, events, kwargs = _arrange(monkeypatch, mode=mode)
    if mode is ProviderMode.RECORDED:
        kwargs["provider"] = replace(kwargs["provider"], call=None)
    receipt = v3_provider_call.dispatch_v3_provider_call(session, **kwargs)
    assert receipt.response is RESPONSE
    assert receipt.model_call_id == "call_v3"
    assert jobs.calls[0]["request_sha256"] == REQUEST.request_sha256
    assert jobs.calls[0]["parameters"]["ar_v3_candidate_sha256"] == "b" * 64
    assert jobs.calls[0]["parameters"]["ar_v3_set_sha256"] == "a" * 64
    assert jobs.calls[0]["connection_revision_id"] == (
        "rev_test" if mode is ProviderMode.LIVE else None
    )
    dispatched = next(row[1] for row in events if isinstance(row, tuple) and row[0] == "dispatch")
    assert dispatched is REQUEST
    request_bytes = json.dumps(
        dispatched.body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    response_bytes = RESPONSE.output_text.encode("utf-8")
    assert hashlib.sha256(request_bytes).hexdigest() == jobs.calls[0]["request_sha256"]
    assert response_bytes == b'{"items":[]}'
    answer = next(row[1] for row in events if isinstance(row, tuple) and row[0] == "response")
    assert answer["response_sha256"] == RESPONSE.response_sha256
    assert answer["input_tokens"] == 123
    completed = next(row[1] for row in events if isinstance(row, tuple) and row[0] == "completed")
    assert completed["request_sha256"] == REQUEST.request_sha256
    assert completed["response_sha256"] == RESPONSE.response_sha256
    assert completed["cost_usd"] == 0.0042
    assert completed["cost_basis"] == "measured"
    names = [event if isinstance(event, str) else event[0] for event in events]
    assert names.index("prepared") < names.index("dispatch") < names.index("response") < names.index("completed")
    assert names[names.index("prepared") + 1] == "commit"
    assert names[names.index("response") + 1] == "commit"
    assert names[names.index("completed") + 1] == "commit"


def test_no_pack_or_existing_call_never_reaches_transport(monkeypatch):
    unavailable = DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="ar_v3_trusted_pack")
    session, jobs, events, kwargs = _arrange(monkeypatch, prepared_error=unavailable)
    with pytest.raises(DomainError) as absent:
        v3_provider_call.dispatch_v3_provider_call(session, **kwargs)
    assert absent.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert not jobs.calls and not any(isinstance(row, tuple) and row[0] == "dispatch" for row in events)
    session, jobs, events, kwargs = _arrange(monkeypatch)
    jobs.duplicate = True
    with pytest.raises(DomainError) as duplicate:
        v3_provider_call.dispatch_v3_provider_call(session, **kwargs)
    assert duplicate.value.code is ErrorCode.CONFLICT
    assert not jobs.calls


def test_changed_pin_after_intent_is_not_sent(monkeypatch):
    changed = SimpleNamespace(scope_id="F2", set_sha256="c" * 64)
    session, jobs, events, kwargs = _arrange(
        monkeypatch, binding_changes=(None, changed),
    )
    with pytest.raises(DomainError):
        v3_provider_call.dispatch_v3_provider_call(session, **kwargs)
    assert not any(isinstance(row, tuple) and row[0] == "dispatch" for row in events)
    state = next(row[1] for row in events if isinstance(row, tuple) and row[0] == "not_processed")
    assert state["dispatch_class"] == "not_sent"


def test_changed_pin_after_answer_keeps_response_and_does_not_complete(monkeypatch):
    changed = SimpleNamespace(scope_id="F2", set_sha256="c" * 64)
    session, jobs, events, kwargs = _arrange(
        monkeypatch, binding_changes=(None, None, changed),
    )
    with pytest.raises(DomainError):
        v3_provider_call.dispatch_v3_provider_call(session, **kwargs)
    assert any(isinstance(row, tuple) and row[0] == "response" for row in events)
    assert not any(isinstance(row, tuple) and row[0] == "completed" for row in events)


@pytest.mark.parametrize("dispatch_class,expected", [
    ("rate_limited", "not_processed"),
    ("outcome_unknown", "outcome_unknown"),
])
def test_transport_failure_has_proven_effect_class(monkeypatch, dispatch_class, expected):
    error = ProxyDispatchError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, dispatch_class=dispatch_class,
        retry_safe=dispatch_class == "rate_limited", details={"dependency": "model_provider"},
    )
    session, jobs, events, kwargs = _arrange(monkeypatch, answer=error)
    with pytest.raises(ProxyDispatchError):
        v3_provider_call.dispatch_v3_provider_call(session, **kwargs)
    assert any(isinstance(row, tuple) and row[0] == expected for row in events)
    assert not any(isinstance(row, tuple) and row[0] == "completed" for row in events)


def test_unusable_received_answer_keeps_exact_raw_digest(monkeypatch):
    received = ReceivedResponse("d" * 64, 88, 12, 30)
    error = ProxyDispatchError(
        ErrorCode.ANALYSIS_FAILED, dispatch_class="outcome_unknown", retry_safe=False,
        received=received,
    )
    session, jobs, events, kwargs = _arrange(monkeypatch, answer=error)
    with pytest.raises(ProxyDispatchError):
        v3_provider_call.dispatch_v3_provider_call(session, **kwargs)
    answer = next(row[1] for row in events if isinstance(row, tuple) and row[0] == "response")
    assert answer["response_sha256"] == "d" * 64
    assert answer["input_tokens"] == 88


def test_wrong_live_model_refuses_after_response_receipt(monkeypatch):
    response = replace(RESPONSE, model="other-model")
    session, jobs, events, kwargs = _arrange(monkeypatch, answer=response)
    with pytest.raises(DomainError) as wrong:
        v3_provider_call.dispatch_v3_provider_call(session, **kwargs)
    assert wrong.value.code is ErrorCode.MODEL_IDENTITY_MISMATCH
    assert any(isinstance(row, tuple) and row[0] == "response" for row in events)
    assert not any(isinstance(row, tuple) and row[0] == "completed" for row in events)


def test_unpinned_live_model_refuses_before_request_assembly(monkeypatch):
    session, jobs, events, kwargs = _arrange(monkeypatch)
    kwargs["provider"] = replace(
        kwargs["provider"],
        call=replace(kwargs["provider"].call, expected_model="proxy"),
    )
    with pytest.raises(DomainError) as unpinned:
        v3_provider_call.dispatch_v3_provider_call(session, **kwargs)
    assert unpinned.value.detail_fields["reason"] == "model_identity_unpinned"
    assert "assemble" not in events and not jobs.calls


def test_unmetered_call_does_not_invent_provider_cost(monkeypatch):
    session, jobs, events, kwargs = _arrange(
        monkeypatch, answer=replace(RESPONSE, reported_cost_usd=None),
    )
    kwargs["provider"] = replace(
        kwargs["provider"],
        call=replace(kwargs["provider"].call, unmetered=True),
    )
    receipt = v3_provider_call.dispatch_v3_provider_call(session, **kwargs)
    assert receipt.cost_usd == 0.0
    assert receipt.cost_basis == "unmetered"
    completed = next(row[1] for row in events if isinstance(row, tuple) and row[0] == "completed")
    assert completed["cost_basis"] == "unmetered"


def test_unpriced_metered_call_records_unknown_cost(monkeypatch):
    session, jobs, events, kwargs = _arrange(
        monkeypatch, answer=replace(RESPONSE, reported_cost_usd=None),
    )
    receipt = v3_provider_call.dispatch_v3_provider_call(session, **kwargs)
    assert receipt.cost_usd is None
    completed = next(row[1] for row in events if isinstance(row, tuple) and row[0] == "completed")
    assert completed["cost_usd"] is None
    assert completed["cost_basis"] == "estimated"
