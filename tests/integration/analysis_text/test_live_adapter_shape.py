"""The live adapter's request shape, validated against the pinned SDK with no network.

``OD-13`` forbids a live call in automated acceptance, but "the live path is untested
until someone spends money on it" is a bad place to leave a stage. These tests drive
the real ``anthropic==1.4.0`` client through an in-memory transport, so the SDK does
all of its own parameter validation and serialization and nothing leaves the process.

What that actually proves, and could not be proved by inspection:

* every key in the request body is one ``messages.create`` accepts - a rejected kwarg
  is a ``TypeError`` here rather than a 400 on the one live run;
* the body the SDK puts on the wire is **byte-identical** to the body the request
  checksum covers, so a recording keyed by that checksum really is keyed by what was
  sent;
* the adapter maps the response - text blocks, ``stop_reason``, usage - the way the
  cost meter and the artifact builder expect.

The suite-wide socket guard is active throughout: ``httpx2.MockTransport`` never opens
one.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic
import httpx2
import pytest

from auditmanager.analysis.text import (
    AR_TEXT_PROFILE,
    DEPENDENCY_NAME,
    LiveAdapter,
    ProviderMode,
    build_request,
    load_text_layer,
    provider_lock,
)
from auditmanager.shared.errors import DomainError, ErrorCode

EMPTY_REPLY = '{"observations": []}'


def _message_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5",
        "content": [{"type": "text", "text": EMPTY_REPLY}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 2180, "output_tokens": 940},
    }
    payload.update(overrides)
    return payload


def _client(handler: Any) -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key="test-key-never-leaves-this-process",
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)),
    )


@pytest.fixture()
def request_for_corpus(text_layer_document):
    return build_request(
        model_id=provider_lock().primary_model_id,
        bundle=AR_TEXT_PROFILE.prompt_bundle,
        text_layer=load_text_layer(text_layer_document),
    )


def test_the_sdk_accepts_the_request_and_sends_exactly_the_hashed_body(request_for_corpus):
    sent: dict[str, Any] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent["body"] = json.loads(request.content.decode("utf-8"))
        sent["path"] = request.url.path
        return httpx2.Response(200, json=_message_payload())

    adapter = LiveAdapter(api_key=None, client=_client(handler))
    adapter.complete(request_for_corpus)

    assert sent["path"] == "/v1/messages"
    # The checksum is worthless if the SDK adds, drops or rewrites a field.
    assert sent["body"] == dict(request_for_corpus.body)
    assert set(sent["body"]) == {
        "model",
        "max_tokens",
        "system",
        "messages",
        "thinking",
        "output_config",
    }
    assert "temperature" not in sent["body"]
    assert "top_p" not in sent["body"]


def test_the_adapter_maps_the_response_the_meter_and_builder_expect(request_for_corpus):
    adapter = LiveAdapter(
        api_key=None,
        client=_client(lambda _: httpx2.Response(200, json=_message_payload())),
    )
    response = adapter.complete(request_for_corpus)

    assert adapter.provider_mode is ProviderMode.LIVE
    assert response.output_text == EMPTY_REPLY
    assert response.stop_reason == "end_turn"
    assert response.truncated is False
    assert response.input_tokens == 2180
    assert response.output_tokens == 940
    assert response.latency_ms >= 0
    assert len(response.response_sha256) == 64


def test_a_truncated_live_reply_is_recognised(request_for_corpus):
    adapter = LiveAdapter(
        api_key=None,
        client=_client(
            lambda _: httpx2.Response(200, json=_message_payload(stop_reason="max_tokens"))
        ),
    )
    assert adapter.complete(request_for_corpus).truncated is True


def test_cache_tokens_fold_into_the_input_count(request_for_corpus):
    """The lock declares no cache rate, so they are priced at the input rate."""
    usage = {
        "input_tokens": 100,
        "output_tokens": 40,
        "cache_creation_input_tokens": 7,
        "cache_read_input_tokens": 3,
    }
    adapter = LiveAdapter(
        api_key=None,
        client=_client(lambda _: httpx2.Response(200, json=_message_payload(usage=usage))),
    )
    assert adapter.complete(request_for_corpus).input_tokens == 110


def test_a_provider_failure_maps_to_the_catalog_and_leaks_nothing(request_for_corpus):
    """The provider's own message can carry an endpoint or an echoed prompt."""

    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            503,
            json={
                "type": "error",
                "error": {
                    "type": "overloaded_error",
                    "message": "upstream https://api.anthropic.com/v1/messages is overloaded",
                },
            },
        )

    adapter = LiveAdapter(api_key=None, client=_client(handler))
    with pytest.raises(DomainError) as raised:
        adapter.complete(request_for_corpus)

    assert raised.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    envelope = raised.value.envelope("corr-b3-live").as_dict()
    assert envelope["details"] == {"dependency": DEPENDENCY_NAME}
    assert "://" not in envelope["message"]
    assert "api.anthropic.com" not in envelope["message"]
    assert "Степень" not in envelope["message"]


def test_the_credential_never_appears_in_a_mapped_failure(request_for_corpus):
    secret = "sk-ant-test-do-not-log-me"

    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(401, json={"type": "error", "error": {"type": "x", "message": secret}})

    client = anthropic.Anthropic(
        api_key=secret,
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)),
    )
    with pytest.raises(DomainError) as raised:
        LiveAdapter(api_key=None, client=client).complete(request_for_corpus)

    envelope = raised.value.envelope("corr-b3-live").as_dict()
    assert secret not in json.dumps(envelope, ensure_ascii=False)
    assert secret not in str(raised.value)


def test_the_installed_sdk_is_the_version_the_lock_pins():
    assert anthropic.__version__ == provider_lock().sdk_version


def test_every_construction_refusal_is_one_no_second_attempt_could_answer(monkeypatch):
    """Three ways this adapter refuses to be built, none of them retryable.

    A missing credential, an absent SDK and an SDK at the wrong version are all facts
    about the deployment this process is running in. None of them changes while the
    process runs, so none may carry a code the executor's retry policy would ladder.
    The absent-SDK case reported ``dependency_unavailable`` until ``W29-RETRY`` — the
    same shape the recorded adapter's missing-recording path had, on the same reasoning
    — while the two refusals either side of it in the same constructor already reported
    ``analysis_input_invalid``.

    ``import anthropic`` is defeated through ``builtins.__import__`` rather than by
    deleting the module, because the SDK is installed in every lane and the branch is
    otherwise unreachable here.
    """
    import builtins

    real_import = builtins.__import__

    def no_anthropic(name, *args, **kwargs):
        if name == "anthropic":
            raise ImportError("no module named anthropic")
        return real_import(name, *args, **kwargs)

    refusals: dict[str, DomainError] = {}

    with pytest.raises(DomainError) as raised:
        LiveAdapter(api_key=None)
    refusals["provider_credential_missing"] = raised.value

    monkeypatch.setattr(builtins, "__import__", no_anthropic)
    with pytest.raises(DomainError) as raised:
        LiveAdapter(api_key="not-a-real-key")
    refusals["provider_sdk_not_importable"] = raised.value
    monkeypatch.undo()

    monkeypatch.setattr(anthropic, "__version__", "0.0.0-not-the-pin")
    with pytest.raises(DomainError) as raised:
        LiveAdapter(api_key="not-a-real-key")
    refusals["provider_sdk_version_mismatch"] = raised.value

    for reason, error in refusals.items():
        assert error.detail_fields.get("reason") == reason
        assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID
        # Against the catalog, not a literal: `retryable` is what the policy reads.
        assert error.code.retryable is False, (
            f"{reason} reports {error.code.value}, which the catalog marks retryable, "
            "so the executor would spend the attempt budget on a deployment fault"
        )
