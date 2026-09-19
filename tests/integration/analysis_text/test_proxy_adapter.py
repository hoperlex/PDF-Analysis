"""The proxy adapter, driven against a local stub rather than the network.

No call leaves this machine. The stub is the proxy's documented contract - an
OpenAI-compatible `POST /api/v1/chat/completions` answering the shapes its own guide names -
so what is proved here is the translation and the failure mapping, which is everything this
adapter does.
"""

from __future__ import annotations

import io
import json
import urllib.error
from typing import Any

import pytest

from auditmanager.analysis.text.adapter import ModelRequest
from auditmanager.analysis.text.config import DEPENDENCY_NAME
from auditmanager.analysis.text.proxy import ProxyAdapter, ProxySettings
from auditmanager.shared.errors import DomainError, ErrorCode

ANTHROPIC_BODY: dict[str, Any] = {
    "model": "claude-opus-5",
    "max_tokens": 4096,
    "system": "Ты проверяешь внутренние противоречия.",
    "messages": [{"role": "user", "content": "страница 1"}],
    "thinking": {"type": "enabled"},
    "output_config": {"effort": "high", "format": {"type": "json_schema", "schema": {"a": 1}}},
}


class _Captured:
    """Records what the adapter put on the wire and answers a canned response."""

    def __init__(self, status: int = 200, document: Any = None) -> None:
        self.status, self.document = status, document or _ok_document()
        self.request: Any = None

    def __call__(self, request: Any, timeout: int | None = None) -> Any:
        self.request = request
        payload = json.dumps(self.document).encode()
        return _Response(self.status, payload)


class _Response:
    def __init__(self, status: int, payload: bytes) -> None:
        self.status, self._payload = status, payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_: Any) -> None:
        return None


def _ok_document(finish: str = "stop") -> dict[str, Any]:
    return {
        "id": "chatcmpl-x",
        "model": "some/upstream-model",
        "choices": [{"message": {"role": "assistant", "content": "{}"}, "finish_reason": finish}],
        "usage": {"prompt_tokens": 1200, "completion_tokens": 340},
    }


def _adapter(opener: Any) -> ProxyAdapter:
    return ProxyAdapter(
        ProxySettings(base_url="https://proxy.example", token="tok"), opener=opener
    )


class TestWhatGoesOnTheWire:
    def test_the_system_prompt_becomes_a_message(self) -> None:
        """Anthropic carries `system` beside the messages; OpenAI carries it inside them."""
        capture = _Captured()
        _adapter(capture).complete(ModelRequest(model_id="claude-opus-5", body=ANTHROPIC_BODY))
        sent = json.loads(capture.request.data)
        assert sent["messages"][0] == {
            "role": "system",
            "content": "Ты проверяешь внутренние противоречия.",
        }
        assert sent["messages"][1]["content"] == "страница 1"

    def test_provider_specific_fields_are_dropped_not_forwarded(self) -> None:
        """Under variant A the upstream model is the operator's and may not be Anthropic.

        A provider-specific field sent to a model that does not know it is either an error
        or, worse, silently ignored.
        """
        capture = _Captured()
        _adapter(capture).complete(ModelRequest(model_id="claude-opus-5", body=ANTHROPIC_BODY))
        sent = json.loads(capture.request.data)
        for absent in ("thinking", "output_config", "system"):
            assert absent not in sent, f"{absent} was forwarded to an OpenAI-shaped endpoint"

    def test_the_json_schema_is_translated_rather_than_lost(self) -> None:
        capture = _Captured()
        _adapter(capture).complete(ModelRequest(model_id="claude-opus-5", body=ANTHROPIC_BODY))
        sent = json.loads(capture.request.data)
        assert sent["response_format"]["type"] == "json_schema"
        assert sent["response_format"]["json_schema"]["schema"] == {"a": 1}

    def test_streaming_is_never_requested(self) -> None:
        """The proxy answers 400 to it, so asking would fail every call."""
        capture = _Captured()
        _adapter(capture).complete(ModelRequest(model_id="m", body=ANTHROPIC_BODY))
        assert "stream" not in json.loads(capture.request.data)

    def test_the_configured_model_is_sent_not_the_requested_one(self) -> None:
        """The stub `proxy` means "I am not choosing"; the prompt's model_id is not a choice."""
        capture = _Captured()
        ProxyAdapter(
            ProxySettings(base_url="https://p", token="t", model="proxy"), opener=capture
        ).complete(ModelRequest(model_id="claude-opus-5", body=ANTHROPIC_BODY))
        assert json.loads(capture.request.data)["model"] == "proxy"

    def test_both_trace_headers_are_present(self) -> None:
        capture = _Captured()
        _adapter(capture).complete(ModelRequest(model_id="m", body=ANTHROPIC_BODY))
        headers = {k.lower(): v for k, v in capture.request.header_items()}
        assert headers["x-request-id"]
        assert headers["x-idempotency-key"]

    def test_the_idempotency_key_is_stable_per_task_and_differs_per_document(self) -> None:
        """Without a stable key every retry is a fresh paid upstream call."""
        first, second, other = _Captured(), _Captured(), _Captured()
        request = ModelRequest(model_id="m", body=ANTHROPIC_BODY)
        _adapter(first).complete(request)
        _adapter(second).complete(request)

        different = dict(ANTHROPIC_BODY, messages=[{"role": "user", "content": "страница 2"}])
        _adapter(other).complete(ModelRequest(model_id="m", body=different))

        key = lambda c: {k.lower(): v for k, v in c.request.header_items()}["x-idempotency-key"]
        assert key(first) == key(second), "a retry would not be deduplicated"
        assert key(first) != key(other), "two documents would collapse onto one call"


class TestWhatComesBack:
    def test_the_answer_is_translated(self) -> None:
        response = _adapter(_Captured()).complete(
            ModelRequest(model_id="m", body=ANTHROPIC_BODY)
        )
        assert response.output_text == "{}"
        assert response.input_tokens == 1200
        assert response.output_tokens == 340
        assert response.stop_reason == "end_turn"

    def test_a_length_stop_becomes_truncated(self) -> None:
        """OpenAI calls it `length`; the provenance vocabulary calls it `truncated`."""
        capture = _Captured(document=_ok_document(finish="length"))
        response = _adapter(capture).complete(ModelRequest(model_id="m", body=ANTHROPIC_BODY))
        assert response.stop_reason == "truncated"

    def test_a_length_stop_makes_the_response_report_itself_truncated(self) -> None:
        """The property that decides `partial`, asserted on the property itself.

        `stop_reason` is a *field*; `ModelResponse.truncated` is the *decision* every
        consumer reads - `stage.py` chooses `CALL_TRUNCATED`, the salvage branch of
        `parse_response`, the coverage note and ultimately the `partial` run terminal
        from it, and from nothing else. A test that pins only the string leaves the
        decision unguarded, which is how a proxy reply cut short at the output ceiling
        came to be recorded as a complete one.
        """
        capture = _Captured(document=_ok_document(finish="length"))
        response = _adapter(capture).complete(ModelRequest(model_id="m", body=ANTHROPIC_BODY))
        assert response.truncated is True, (
            "a proxied reply cut short at the output ceiling does not report itself "
            "truncated, so the stage records the call as succeeded and publishes a "
            "partial analysis as a complete one"
        )

    def test_a_normal_stop_does_not_report_itself_truncated(self) -> None:
        """The anti-vacuity half: an adapter that returned True always would pass above."""
        response = _adapter(_Captured()).complete(
            ModelRequest(model_id="m", body=ANTHROPIC_BODY)
        )
        assert response.truncated is False

    def test_an_empty_choice_list_is_a_failure_not_an_empty_finding_set(self) -> None:
        """Publishing nothing because the proxy said nothing would be a silent success."""
        capture = _Captured(document={"choices": [], "usage": {}})
        with pytest.raises(DomainError) as caught:
            _adapter(capture).complete(ModelRequest(model_id="m", body=ANTHROPIC_BODY))
        assert caught.value.code is ErrorCode.ANALYSIS_FAILED


class TestFailuresMapToTheCatalog:
    @pytest.mark.parametrize(
        ("status", "payload", "expected"),
        [
            (401, {}, ErrorCode.DEPENDENCY_CREDENTIAL_REFUSED),
            (400, {"error": {"code": "model_not_allowed"}}, ErrorCode.ANALYSIS_INPUT_INVALID),
            (400, {"error": {"code": "invalid_request"}}, ErrorCode.ANALYSIS_INPUT_INVALID),
            (413, {}, ErrorCode.ANALYSIS_INPUT_INVALID),
            (503, {"error": {"code": "queue_full"}}, ErrorCode.DEPENDENCY_UNAVAILABLE),
            (504, {"error": {"code": "deadline_exceeded"}}, ErrorCode.DEPENDENCY_UNAVAILABLE),
        ],
    )
    def test_each_documented_status_lands_on_its_code(
        self, status: int, payload: dict[str, Any], expected: ErrorCode
    ) -> None:
        def raising(request: Any, timeout: int | None = None) -> Any:
            raise urllib.error.HTTPError(
                "https://proxy.example",
                status,
                "",
                {},  # type: ignore[arg-type]
                io.BytesIO(json.dumps(payload).encode()),
            )

        with pytest.raises(DomainError) as caught:
            _adapter(raising).complete(ModelRequest(model_id="m", body=ANTHROPIC_BODY))
        assert caught.value.code is expected

    def test_an_unreachable_proxy_is_a_dependency_failure(self) -> None:
        def unreachable(request: Any, timeout: int | None = None) -> Any:
            raise urllib.error.URLError("no route to host")

        with pytest.raises(DomainError) as caught:
            _adapter(unreachable).complete(ModelRequest(model_id="m", body=ANTHROPIC_BODY))
        assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE

    def test_a_refused_credential_never_tells_the_caller_to_retry(self) -> None:
        """The `D-7` defect in its second place, and the bytes that prove it is gone.

        Asserting the *code* is not enough: the code is a name and the lie was the
        `retryable` flag beside it. `dependency_unavailable` is pinned `retryable: true`,
        so a 401 from the proxy used to answer "retry this" for a rejected credential --
        an operation that cannot succeed until an operator repairs the configuration.
        This pins the envelope a caller actually reads, and it is the assertion that goes
        red if the mapping is put back.
        """

        def refusing(request: Any, timeout: int | None = None) -> Any:
            raise urllib.error.HTTPError(
                "https://proxy.example",
                401,
                "",
                {},  # type: ignore[arg-type]
                io.BytesIO(b"{}"),
            )

        with pytest.raises(DomainError) as caught:
            _adapter(refusing).complete(ModelRequest(model_id="m", body=ANTHROPIC_BODY))
        envelope = caught.value.envelope("11111111-1111-4111-8111-111111111111")
        assert envelope.error_code is ErrorCode.DEPENDENCY_CREDENTIAL_REFUSED
        assert envelope.retryable is False, "a rejected credential is never retryable"
        assert envelope.http_status == 500, "the fault is the server's, not the caller's"
        # The stable dependency class name, so an operator reading this envelope can tell
        # which credential was refused -- the blob store's or the model proxy's.
        assert dict(envelope.details) == {"dependency": DEPENDENCY_NAME}

    def test_no_failure_message_leaks_the_token_or_the_url(self) -> None:
        """The envelope screen refuses a URL, so a leak here is a hard failure not a review."""
        def raising(request: Any, timeout: int | None = None) -> Any:
            raise urllib.error.HTTPError(
                "https://proxy.example", 500, "", {}, io.BytesIO(b"{}")  # type: ignore[arg-type]
            )

        with pytest.raises(DomainError) as caught:
            _adapter(raising).complete(ModelRequest(model_id="m", body=ANTHROPIC_BODY))
        rendered = caught.value.envelope("cid").as_dict()["message"]
        assert "tok" not in rendered
        assert "proxy.example" not in rendered


class TestTheModeIsLiveBecauseAModelReallyAnswered:
    def test_provider_mode_is_live(self) -> None:
        """A proxy is a transport, not a third provenance mode.

        The declared vocabulary answers "did a model produce this, or was it replayed".
        Through a proxy a model produced it. A third value would make the CSV's column 6,
        the run badge and the API each re-learn a distinction that does not exist for them.
        """
        assert _adapter(_Captured()).provider_mode.value == "live"

    def test_provider_mode_cannot_be_reassigned(self) -> None:
        adapter = _adapter(_Captured())
        with pytest.raises(AttributeError):
            adapter.provider_mode = "recorded"  # type: ignore[misc]


class TestItRefusesToBeBuiltWrong:
    def test_an_empty_token_is_refused_at_construction(self) -> None:
        with pytest.raises(DomainError):
            ProxySettings(base_url="https://p", token="")

    def test_a_relative_base_url_is_refused(self) -> None:
        with pytest.raises(DomainError):
            ProxySettings(base_url="proxy.example", token="t")


class TestTheMeasuredCostBeatsTheEstimate:
    """`OD-02`'s revision makes the model selectable, so no rate table can cover it.

    The pinned table is a rate card for one model. Under the proxy the model is chosen at
    configuration time and may not be in the table at all - in which case the estimate is not
    merely imprecise, it is absent. The proxy returns what the call actually cost, and the
    `OD-03` ceiling should hold against a measurement rather than a derivation.
    """

    def test_the_reported_cost_is_carried_off_the_response(self) -> None:
        document = _ok_document()
        document["usage"]["cost"] = 0.000175
        response = _adapter(_Captured(document=document)).complete(
            ModelRequest(model_id="m", body=ANTHROPIC_BODY)
        )
        assert response.reported_cost_usd == pytest.approx(0.000175)

    def test_a_response_without_a_cost_leaves_it_none(self) -> None:
        """Then the meter falls back to the pinned table, as it always did."""
        response = _adapter(_Captured()).complete(
            ModelRequest(model_id="m", body=ANTHROPIC_BODY)
        )
        assert response.reported_cost_usd is None

    def test_a_non_numeric_cost_is_ignored_rather_than_trusted(self) -> None:
        document = _ok_document()
        document["usage"]["cost"] = "free"
        response = _adapter(_Captured(document=document)).complete(
            ModelRequest(model_id="m", body=ANTHROPIC_BODY)
        )
        assert response.reported_cost_usd is None

    def test_the_meter_charges_the_reported_figure_when_there_is_one(self) -> None:
        from auditmanager.analysis.text.cost import CostMeter
        from auditmanager.analysis.text.lock import ModelPin

        pin = ModelPin(model_id="m", input_per_mtok_usd=5.0, output_per_mtok_usd=25.0)
        meter = CostMeter(ceiling_usd=1.0)
        estimated = pin.cost_usd(input_tokens=1000, output_tokens=1000)
        charged = meter.charge(
            pin, input_tokens=1000, output_tokens=1000, reported_cost_usd=0.5
        )
        assert charged == pytest.approx(0.5)
        assert charged != pytest.approx(estimated), (
            "the fixture no longer discriminates: pick a reported value the table cannot "
            "coincidentally produce"
        )

    def test_the_ceiling_still_halts_on_the_reported_figure(self) -> None:
        from auditmanager.analysis.text.cost import CostMeter
        from auditmanager.analysis.text.lock import ModelPin

        pin = ModelPin(model_id="m", input_per_mtok_usd=5.0, output_per_mtok_usd=25.0)
        meter = CostMeter(ceiling_usd=0.10)
        with pytest.raises(DomainError) as caught:
            meter.charge(pin, input_tokens=1, output_tokens=1, reported_cost_usd=0.25)
        assert caught.value.code is ErrorCode.COST_BUDGET_EXCEEDED
