"""The two transports of `analysis/text` hand the provider the wire form (`AR-V3-WIRE-SCHEMA-01`).

Each test drives the adapter and asserts on what its fake opener / fake client actually received:
the bytes of the proxy's POST, the keyword arguments of the SDK call. The request's own body, its
checksum and the v1 sections' provider body are asserted unchanged.
"""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.profiles.ar_v3.response_schema import response_schema
from auditmanager.analysis.text.adapter import ModelRequest
from auditmanager.analysis.text.live import LiveAdapter
from auditmanager.analysis.text.prompt import RESPONSE_SCHEMA
from auditmanager.analysis.text.proxy import ProxyAdapter, ProxySettings
from auditmanager.analysis.text.wire_schema import to_wire_schema

REFUSED = (b'"oneOf"', b'"minLength"', b'"maxLength"', b'"minimum"', b'"maxItems"', b'"pattern"')


def _body(schema: Any) -> dict[str, Any]:
    return {
        "model": "claude-opus-5", "max_tokens": 4096, "system": "Система.",
        "messages": [{"role": "user", "content": "страница 1"}],
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": "high", "format": {"type": "json_schema", "schema": schema}},
    }


def _request(schema: Any) -> ModelRequest:
    return ModelRequest(model_id="claude-opus-5", body=_body(schema))


# -- the proxy ---------------------------------------------------------------------------------------


class _Opener:
    def __init__(self) -> None:
        self.sent: Any = None

    def __call__(self, request: Any, timeout: int | None = None) -> Any:
        self.sent = request
        document = {
            "id": "chatcmpl-x", "model": "some/upstream-model",
            "choices": [{"message": {"role": "assistant", "content": "{}"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 3},
        }
        payload = json.dumps(document).encode()

        class _Response:
            status = 200
            headers: dict[str, str] = {}

            def read(self, size: int = -1) -> bytes:
                return payload

            def __enter__(self) -> "_Response":
                return self

            def __exit__(self, *_: Any) -> None:
                return None

        return _Response()


def _proxy() -> tuple[ProxyAdapter, _Opener]:
    opener = _Opener()
    return ProxyAdapter(ProxySettings(base_url="https://proxy.example", token="tok"), opener=opener), opener


def test_the_proxy_post_carries_the_wire_form_of_the_v3_schema() -> None:
    request = _request(response_schema())
    adapter, opener = _proxy()
    adapter.complete(request)
    data: bytes = opener.sent.data
    for refused in REFUSED:
        assert refused not in data, refused
    sent = json.loads(data)["response_format"]
    assert sent["type"] == "json_schema" and sent["json_schema"]["strict"] is True
    assert sent["json_schema"]["schema"] == to_wire_schema(response_schema())
    assert b'"anyOf"' in data


def test_the_proxy_leaves_the_requests_own_body_and_checksum_alone() -> None:
    request = _request(response_schema())
    before_body, before_sha = copy.deepcopy(dict(request.body)), request.request_sha256
    adapter, _ = _proxy()
    adapter.complete(request)
    assert request.body == before_body
    assert request.request_sha256 == before_sha
    assert request.body["output_config"]["format"]["schema"] == response_schema(), "the sealed schema"


def test_the_v1_provider_body_is_byte_identical_to_what_it_was() -> None:
    request = _request(RESPONSE_SCHEMA)
    adapter, opener = _proxy()
    adapter.complete(request)
    # what the adapter sent before this task: the schema handed over as it was
    expected = {
        "model": "proxy",
        "messages": [{"role": "system", "content": "Система."},
                     {"role": "user", "content": "страница 1"}],
        "max_tokens": 4096,
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "text_observations", "schema": RESPONSE_SCHEMA, "strict": True}},
    }
    assert opener.sent.data == json.dumps(expected, ensure_ascii=False, sort_keys=True).encode("utf-8")


def test_the_proxy_sends_no_response_format_when_the_body_has_no_schema() -> None:
    body = {key: value for key, value in _body({}).items() if key != "output_config"}
    adapter, opener = _proxy()
    adapter.complete(ModelRequest(model_id="m", body=body))
    assert b"response_format" not in opener.sent.data


# -- the direct provider adapter ------------------------------------------------------------------------


class _Client:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="{}")], stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=5, output_tokens=2), model="claude-opus-5")


def test_the_direct_adapter_hands_the_sdk_the_wire_form_of_the_v3_schema() -> None:
    request = _request(response_schema())
    client = _Client()
    LiveAdapter(api_key=None, client=client).complete(request)
    (call,) = client.calls
    sent = call["output_config"]["format"]["schema"]
    assert sent == to_wire_schema(response_schema())
    serialised = json.dumps(call).encode()
    for refused in REFUSED:
        assert refused not in serialised, refused
    # everything else in the call is what the request carried
    assert {key: value for key, value in call.items() if key != "output_config"} == {
        key: value for key, value in request.body.items() if key != "output_config"}
    assert call["output_config"]["effort"] == "high"
    assert call["output_config"]["format"]["type"] == "json_schema"


def test_the_direct_adapter_leaves_the_requests_own_body_and_checksum_alone() -> None:
    request = _request(response_schema())
    before_body, before_sha = copy.deepcopy(dict(request.body)), request.request_sha256
    LiveAdapter(api_key=None, client=_Client()).complete(request)
    assert request.body == before_body and request.request_sha256 == before_sha


def test_the_direct_adapter_call_for_a_v1_section_is_unchanged() -> None:
    request = _request(RESPONSE_SCHEMA)
    client = _Client()
    LiveAdapter(api_key=None, client=client).complete(request)
    (call,) = client.calls
    assert call == dict(request.body)
    assert json.dumps(call, sort_keys=True) == json.dumps(dict(request.body), sort_keys=True)


@pytest.mark.parametrize("body", [
    {"model": "m", "max_tokens": 1, "messages": []},
    {"model": "m", "max_tokens": 1, "messages": [], "output_config": {"effort": "high"}},
])
def test_the_direct_adapter_passes_a_body_without_a_schema_as_it_is(body: dict[str, Any]) -> None:
    client = _Client()
    LiveAdapter(api_key=None, client=client).complete(ModelRequest(model_id="m", body=body))
    assert client.calls == [body]
