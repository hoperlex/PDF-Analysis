"""`W53C-EXEC-01` C-04 and C-05: every provider answer and replay failure is classified.

C-04. A complete ``200`` answer whose body is not the documented chat-completions shape
used to escape the proxy as a bare ``AttributeError`` or ``TypeError`` (a JSON array, a
non-object ``choices[0]``, a non-integer usage count) or as a plain ``DomainError`` (no
choices). The stage catches only ``DomainError``, so the first two left the provider
effect ``prepared`` and crashed the run; the third was journalled ``outcome_unknown``
without the usage the provider had reported. Each shape must now be one typed
``ProxyDispatchError`` -- ``outcome_unknown``, never retry-safe -- carrying the usage
evidence when the body has a readable usage block, and the stage must journal that
evidence as ``response_received``.

C-05. A recorded replay reads a committed file and dispatches nothing, so its failure
can never be a possibly-paid ``outcome_unknown``: it is ``not_processed``/``not_sent``.

Everything here is container-free: the proxy is the real adapter over a local stub, the
stage is the real stage, and the journal is a recording double.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Self

import pytest

from auditmanager.analysis.text.adapter import ModelRequest
from auditmanager.analysis.text.config import ProviderConfig, ProviderMode
from auditmanager.analysis.text.proxy import (
    ProxyAdapter,
    ProxyDispatchError,
    ProxySettings,
    ReceivedResponse,
)
from auditmanager.analysis.text.stage import STATUS_FAILED, run_text_analysis
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId, RunId

MODEL_ID = "claude-opus-5"
_USAGE = {"prompt_tokens": 1200, "completion_tokens": 340}
_GOOD_CHOICE = {"message": {"role": "assistant", "content": "{}"}, "finish_reason": "stop"}


class _Response:
    def __init__(self, payload: bytes) -> None:
        self.status, self._payload = 200, payload

    def read(self, size: int = -1) -> bytes:
        return self._payload if size < 0 else self._payload[:size]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def _adapter(raw: bytes) -> ProxyAdapter:
    def answer(_request: Any, timeout: int | None = None) -> _Response:
        return _Response(raw)

    return ProxyAdapter(
        ProxySettings(base_url="https://proxy.example", token="tok"), opener=answer
    )


def _body(document: Any) -> bytes:
    return json.dumps(document).encode("utf-8")


#: (label, raw body, whether the usage evidence is readable)
_UNUSABLE_ANSWERS: list[tuple[str, bytes, bool]] = [
    ("json array", _body([{"choices": [_GOOD_CHOICE]}]), False),
    ("json string", _body("ok"), False),
    ("json null", b"null", False),
    ("not json", b"<html>gateway</html>", False),
    ("choice is a string", _body({"choices": ["x"], "usage": _USAGE}), True),
    ("choice is null", _body({"choices": [None], "usage": _USAGE}), True),
    ("choices is an object", _body({"choices": {"0": _GOOD_CHOICE}, "usage": _USAGE}), True),
    ("message is a list", _body({"choices": [{"message": ["x"]}], "usage": _USAGE}), True),
    ("content is a list", _body({
        "choices": [{"message": {"content": [{"type": "text"}]}}], "usage": _USAGE,
    }), True),
    ("finish reason is a number", _body({
        "choices": [{**_GOOD_CHOICE, "finish_reason": 3}], "usage": _USAGE,
    }), True),
    ("empty choices with usage", _body({"choices": [], "usage": _USAGE}), True),
    ("empty choices without usage", _body({"choices": [], "usage": {}}), True),
    ("no choices key", _body({"usage": _USAGE}), True),
    ("usage count is text", _body({
        "choices": [_GOOD_CHOICE], "usage": {"prompt_tokens": "many", "completion_tokens": 3},
    }), False),
    ("usage count is an object", _body({
        "choices": [_GOOD_CHOICE], "usage": {"prompt_tokens": {}, "completion_tokens": 3},
    }), False),
    ("usage count is a boolean", _body({
        "choices": [_GOOD_CHOICE], "usage": {"prompt_tokens": True, "completion_tokens": 3},
    }), False),
    ("usage count is negative", _body({
        "choices": [_GOOD_CHOICE], "usage": {"prompt_tokens": -1, "completion_tokens": 3},
    }), False),
    ("usage is a list", _body({"choices": [_GOOD_CHOICE], "usage": [1, 2]}), False),
]


@pytest.mark.parametrize(
    ("label", "raw", "has_usage"), _UNUSABLE_ANSWERS, ids=[a[0] for a in _UNUSABLE_ANSWERS]
)
def test_every_unusable_answer_is_one_typed_ambiguous_refusal(
    label: str, raw: bytes, has_usage: bool
) -> None:
    # A bare AttributeError/TypeError escaping here -- the defect -- errors this test.
    with pytest.raises(ProxyDispatchError) as caught:
        _adapter(raw).complete(ModelRequest(model_id="m", body={"messages": []}))

    failure = caught.value
    assert failure.code is ErrorCode.ANALYSIS_FAILED
    # An answer arrived, so the call may have been paid: never "not processed" and
    # never safe to repeat automatically.
    assert failure.dispatch_class == "outcome_unknown"
    assert failure.retry_safe is False
    if has_usage:
        expected = (0, 0) if b'"usage": {}' in raw else (1200, 340)
        assert isinstance(failure.received, ReceivedResponse)
        assert (failure.received.input_tokens, failure.received.output_tokens) == expected
        assert failure.received.response_sha256 == hashlib.sha256(raw).hexdigest()
        assert failure.received.latency_ms >= 0
    else:
        assert failure.received is None


def test_the_documented_shape_still_reads_through() -> None:
    """Anti-vacuity: the validation refuses shapes, not answers."""
    response = _adapter(_body({
        "choices": [_GOOD_CHOICE],
        "usage": {"prompt_tokens": 1200, "completion_tokens": 340.0, "cost": 0.01},
    })).complete(ModelRequest(model_id="m", body={"messages": []}))
    assert (response.output_text, response.stop_reason) == ("{}", "end_turn")
    assert (response.input_tokens, response.output_tokens) == (1200, 340)
    assert response.reported_cost_usd == 0.01


# --- the stage journals what the evidence proves -----------------------------


def _text_layer_document() -> dict[str, Any]:
    text = "Отчёт за год. Выручка выросла.\n"
    return {
        "artifact_role": "prepared.text_layer",
        "artifact_version": "1.0.0",
        "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
        "normalization": {"id": "nfc_v1", "description": "NFC"},
        "total_char_count": len(text),
        "pages": [{"page_number": 1, "char_start": 0, "char_end": len(text), "text": text}],
    }


class _RecordingJournal:
    def __init__(self) -> None:
        self.model_call_id = ModelCallId.new()
        self.calls: list[tuple[str, Any]] = []

    def prepare(self, request: Any, *, mode: ProviderMode) -> ModelCallId:
        self.calls.append(("prepare", mode))
        return self.model_call_id

    def response_received(self, model_call_id: ModelCallId, response: Any) -> None:
        self.calls.append(("response_received", response))

    def complete(self, call: Any) -> None:
        self.calls.append(("complete", call))

    def outcome_unknown(self, model_call_id: ModelCallId, error: Any) -> None:
        self.calls.append(("outcome_unknown", error))

    def not_processed(
        self, model_call_id: ModelCallId, error: Any, dispatch_class: str
    ) -> None:
        self.calls.append(("not_processed", dispatch_class))


def _config(mode: ProviderMode) -> ProviderConfig:
    return ProviderConfig(
        mode=mode, model_id=MODEL_ID, run_cost_ceiling_usd=1.00, api_key=None,
        ceiling_is_explicit=True,
    )


def _stage(adapter: Any, mode: ProviderMode) -> tuple[Any, _RecordingJournal]:
    journal = _RecordingJournal()
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=_text_layer_document(),
        adapter=adapter, config=_config(mode), call_journal=journal,
    )
    return outcome, journal


def test_an_unusable_answer_with_usage_is_journalled_as_received() -> None:
    raw = _body({"choices": [], "usage": _USAGE})
    outcome, journal = _stage(_adapter(raw), ProviderMode.LIVE)

    assert [name for name, _ in journal.calls] == ["prepare", "response_received"]
    evidence = journal.calls[1][1]
    assert (evidence.input_tokens, evidence.output_tokens) == (1200, 340)
    assert evidence.response_sha256 == hashlib.sha256(raw).hexdigest()
    assert outcome.status == STATUS_FAILED
    assert outcome.error.code is ErrorCode.ANALYSIS_FAILED
    assert outcome.provider_effect_uncertain is True
    assert outcome.provider_retry_allowed is False


def test_an_unusable_answer_without_usage_is_outcome_unknown() -> None:
    outcome, journal = _stage(_adapter(_body([1, 2])), ProviderMode.LIVE)

    assert [name for name, _ in journal.calls] == ["prepare", "outcome_unknown"]
    assert outcome.status == STATUS_FAILED
    assert outcome.provider_effect_uncertain is True


class _FailingReplay:
    """A recorded adapter whose replay fails, the way a missing recording does."""

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.RECORDED

    def complete(self, request: Any) -> Any:
        raise DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE, message="no recording for this request"
        )


def test_a_failed_replay_is_never_journalled_as_possibly_paid() -> None:
    outcome, journal = _stage(_FailingReplay(), ProviderMode.RECORDED)

    assert journal.calls == [("prepare", ProviderMode.RECORDED), ("not_processed", "not_sent")]
    assert outcome.status == STATUS_FAILED
    assert outcome.provider_effect_uncertain is False
