"""The ``http_api`` adapters against a local gateway (`EXEC-HTTP-01`). No paid call.

The fake gateway listens on 127.0.0.1, but a connection names ``gateway.example.test``, which a
test policy resolves to a *public* address and dials as the fake. A test that wants the
destination rules to bite uses the default policy instead, and the gateway then sees nothing.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from auditmanager.analysis.public import ModelRequest, ProxyDispatchError
from auditmanager.analysis.text.proxy import _completions_url as proxy_completions_url
from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.http_adapter import (
    build_http_adapter,
    completions_url,
    effective_timeout,
)
from auditmanager.jobs.lease import AttemptContext
from auditmanager.shared.errors import DomainError, ErrorCode

KEY = "sk-sentinel-0123456789abcdef"
GATEWAY_MODEL = "anthropic/claude-opus-5"
REQUEST = ModelRequest(
    model_id="claude-opus-5",
    body={"model": "claude-opus-5", "max_tokens": 16, "system": "s",
          "messages": [{"role": "user", "content": "hello"}]},
)


def _adapter(gateway: Any, flavour: str = "openai_chat", *, base_path: str = "/agent/v1",
             policy: DestinationPolicy | None = None, context: Any = None,
             transport: str = "direct", base_url: str | None = None) -> Any:
    return build_http_adapter(
        api_flavour=flavour, base_url=base_url or gateway.base_url(base_path), api_key=KEY,
        gateway_model=GATEWAY_MODEL, timeout_seconds=5, transport=transport,
        policy=policy or gateway.policy(), context=context,
    )


@pytest.mark.parametrize("base", [
    "https://proxy.example", "https://proxy.example/", "https://proxy.example/agent/v1",
    "https://proxy.example/agent/v1/", "http://h:8000/v1",
])
def test_the_completions_url_is_the_proxys_own_rule(base: str) -> None:
    assert completions_url(base) == proxy_completions_url(base)


def test_openai_chat_sends_the_gateway_name_and_the_key_to_the_chat_path(gateway_factory: Any) -> None:
    gateway = gateway_factory()
    response = _adapter(gateway).complete(REQUEST)
    (seen,) = gateway.requests
    assert seen["path"] == "/agent/v1/chat/completions"
    assert seen["authorization"] == f"Bearer {KEY}"
    assert seen["body"]["model"] == GATEWAY_MODEL, "the gateway name is sent, never the pin id"
    assert response.input_tokens == 1200 and response.output_tokens == 340
    assert response.reported_cost_usd == 0.0402
    assert seen["host"] == f"gateway.example.test:{gateway.port}"


def test_an_origin_only_base_url_uses_the_portal_path(gateway_factory: Any) -> None:
    gateway = gateway_factory()
    _adapter(gateway, base_path="").complete(REQUEST)
    assert gateway.requests[0]["path"] == "/api/v1/chat/completions"


def test_the_default_policy_refuses_loopback_in_the_call_and_nothing_is_sent(gateway_factory: Any) -> None:
    gateway = gateway_factory()
    adapter = _adapter(gateway, policy=DestinationPolicy(),
                       base_url=f"http://127.0.0.1:{gateway.port}/v1")
    with pytest.raises(ProxyDispatchError) as refused:
        adapter.complete(REQUEST)
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert refused.value.dispatch_class == "not_sent" and refused.value.retry_safe is False
    assert gateway.requests == []
    assert "127.0.0.1" not in str(refused.value) and KEY not in str(refused.value)


def test_a_service_name_is_refused_in_the_call(gateway_factory: Any) -> None:
    gateway = gateway_factory()
    adapter = _adapter(gateway, policy=gateway.policy(), base_url=f"http://postgres:{gateway.port}/v1")
    with pytest.raises(ProxyDispatchError) as refused:
        adapter.complete(REQUEST)
    assert refused.value.dispatch_class == "not_sent" and gateway.requests == []


def test_a_redirect_is_not_followed(gateway_factory: Any) -> None:
    gateway = gateway_factory(behaviour="redirect")
    with pytest.raises(DomainError):
        _adapter(gateway).complete(REQUEST)
    assert len(gateway.requests) == 1, "the redirect target was never contacted"


def test_a_call_with_no_watchdog_time_left_is_refused_before_it_is_sent(gateway_factory: Any) -> None:
    gateway = gateway_factory()
    spent = AttemptContext(run_id="run", attempt_id="att", started_monotonic=0.0,
                           watchdog_seconds=30.0)
    assert effective_timeout(120, spent) is None
    with pytest.raises(ProxyDispatchError) as refused:
        _adapter(gateway, context=spent).complete(REQUEST)
    assert refused.value.dispatch_class == "not_sent" and gateway.requests == []


def test_the_timeout_is_the_revisions_cut_to_the_watchdog() -> None:
    fresh = AttemptContext(run_id="r", attempt_id="a", started_monotonic=time.monotonic(),
                           watchdog_seconds=900.0)
    assert effective_timeout(120, fresh, margin=60) is not None
    nearly = AttemptContext(run_id="r", attempt_id="a", started_monotonic=time.monotonic(),
                            watchdog_seconds=100.0)
    # Not asserted to the second: remaining time shrinks as the test runs.
    assert 1.0 <= (effective_timeout(120, nearly, margin=60) or 0) <= 100.0
    assert effective_timeout(30, None) == 30.0


def test_anthropic_messages_goes_through_the_sdk_to_the_revisions_base_url(gateway_factory: Any) -> None:
    gateway = gateway_factory(content="{}")
    response = _adapter(gateway, "anthropic_messages", base_path="").complete(REQUEST)
    (seen,) = gateway.requests
    assert seen["path"] == "/v1/messages"
    assert seen["x_api_key"] == KEY
    assert seen["body"]["model"] == GATEWAY_MODEL
    assert response.output_text == "{}" and response.input_tokens == 1200
    assert getattr(response, "model", GATEWAY_MODEL) == GATEWAY_MODEL


def test_anthropic_messages_is_pinned_too(gateway_factory: Any) -> None:
    gateway = gateway_factory()
    adapter = _adapter(gateway, "anthropic_messages", policy=DestinationPolicy(),
                       base_url=f"http://127.0.0.1:{gateway.port}")
    with pytest.raises(ProxyDispatchError) as refused:
        adapter.complete(REQUEST)
    assert refused.value.dispatch_class == "not_sent" and gateway.requests == []


def test_anthropic_refusal_of_the_key_is_a_definite_refusal(gateway_factory: Any) -> None:
    gateway = gateway_factory(behaviour="json401")
    with pytest.raises(ProxyDispatchError) as refused:
        _adapter(gateway, "anthropic_messages", base_path="").complete(REQUEST)
    assert refused.value.code is ErrorCode.DEPENDENCY_CREDENTIAL_REFUSED
    assert refused.value.dispatch_class == "definite_refusal"
    assert len(gateway.requests) == 1, "the SDK does not retry on its own"
    assert KEY not in str(refused.value)


def test_a_tunnelled_connection_is_not_served(gateway_factory: Any) -> None:
    gateway = gateway_factory()
    with pytest.raises(DomainError) as refused:
        _adapter(gateway, transport="ssh_tunnel")
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
