"""A proxied reply cut short at the output ceiling must reach the ``partial`` terminal.

`W21-CERT` recorded `PA-01` criterion 4 as holding "with a named exception": `partial`
was not driven, because *"it needs a truncated provider call and nothing in the
operator's surface picks a model or output ceiling"*. That names a **limit**. What this
file establishes is that on the transport `W21-CERT` itself ran - `proxy` - there was
also a **defect** underneath the limit, and the two are not the same thing.

`ModelResponse.truncated` is the single decision the whole chain hangs on:

    stop_reason -> ModelResponse.truncated -> CALL_TRUNCATED, the salvage branch of
    parse_response, the coverage note, STATUS_PARTIAL, and select_terminal's `partial`

`adapter.py:84` computes it as ``stop_reason == "max_tokens"`` - the Anthropic stop
vocabulary, which `live.py` passes through unchanged and every recording in
`fixtures/recorded/text_analysis` is written in. The proxy adapter alone translated
OpenAI's `length` into the string ``"truncated"``, which is a *call-status* word from
`provenance.py`, not a stop reason. Nothing then recognised it. The consequence is not
only that `partial` was unreachable: the call was recorded `succeeded`, the coverage
note claimed the whole document had been read, and a cut-short analysis published as a
complete one.

Nothing is mocked that is under test. The `ProxyAdapter` here is the real one, driven
against a local stub of the proxy's own documented OpenAI-compatible contract - the same
arrangement `test_proxy_adapter.py` uses - and the stage is the real stage.
"""

from __future__ import annotations

import json
from typing import Any

from auditmanager.analysis.text.config import ProviderConfig, ProviderMode
from auditmanager.analysis.text.proxy import ProxyAdapter, ProxySettings
from auditmanager.analysis.text.stage import (
    STATUS_PARTIAL,
    STATUS_SUCCEEDED,
    run_text_analysis,
)
from auditmanager.shared.errors import ErrorCode
from auditmanager.shared.identity import RunId

MODEL_ID = "claude-opus-5"
PAGE_ONE = "Отчёт за год. Выручка выросла.\n"
PAGE_TWO = "Выручка упала за тот же год.\n"
PAGE_THREE = "Прочие сведения приведены далее.\n"


def _text_layer_document() -> dict[str, Any]:
    pages, out, cursor = [PAGE_ONE, PAGE_TWO, PAGE_THREE], [], 0
    for number, text in enumerate(pages, start=1):
        out.append(
            {
                "page_number": number,
                "char_start": cursor,
                "char_end": cursor + len(text),
                "text": text,
            }
        )
        cursor += len(text)
    return {
        "artifact_role": "prepared.text_layer",
        "artifact_version": "1.0.0",
        "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
        "normalization": {"id": "nfc_v1", "description": "NFC"},
        "total_char_count": cursor,
        "pages": out,
    }


#: One grounded observation on page 1 only. Pages 2 and 3 are never reached, which is
#: exactly what `partial` asserts: usable output over a strict subset of the input.
_USABLE_REPLY = json.dumps(
    {
        "observations": [
            {
                "category": "internal_contradiction",
                "finding_text": "Две формулировки о выручке не сходятся.",
                "recommendation_text": "Сверить показатели.",
                "evidence": [{"page_number": 1, "quote": "Выручка выросла"}],
            }
        ]
    },
    ensure_ascii=False,
)


class _StubProxy:
    """The proxy's documented `POST /api/v1/chat/completions`, answering locally."""

    def __init__(self, finish_reason: str) -> None:
        self._finish_reason = finish_reason

    def __call__(self, request: Any, timeout: int | None = None) -> Any:
        document = {
            "id": "chatcmpl-w23",
            "model": "some/upstream-model",
            "choices": [
                {
                    "message": {"role": "assistant", "content": _USABLE_REPLY},
                    "finish_reason": self._finish_reason,
                }
            ],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 16000, "cost": 0.0402},
        }
        return _Response(json.dumps(document).encode("utf-8"))


class _Response:
    def __init__(self, payload: bytes) -> None:
        self.status, self._payload = 200, payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_: Any) -> None:
        return None


def _run(finish_reason: str) -> Any:
    adapter = ProxyAdapter(
        ProxySettings(base_url="https://proxy.example", token="tok"),
        opener=_StubProxy(finish_reason),
    )
    return run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=_text_layer_document(),
        adapter=adapter,
        # `proxy` is a transport; the provenance the run records is `live`, which is what
        # `bootstrap/composition.py:_provenance_mode` hands the stage.
        config=ProviderConfig(
            mode=ProviderMode.LIVE,
            model_id=MODEL_ID,
            run_cost_ceiling_usd=1.00,
            api_key=None,
            ceiling_is_explicit=False,
        ),
    )


def test_a_proxied_length_stop_makes_the_stage_partial() -> None:
    """The guard. Before the repair this returned `succeeded` and published."""
    outcome = _run("length")

    assert outcome.status == STATUS_PARTIAL, (
        "a proxied reply cut short at the output ceiling was not recognised as "
        "truncated, so the stage reported "
        f"{outcome.status!r} and a partial analysis publishes as a complete one"
    )
    assert outcome.metrics["call_status"] == "truncated"
    assert outcome.error is not None
    assert outcome.error.code is ErrorCode.PARTIAL_RESULT_NOT_PUBLISHABLE
    # The artifact exists - `partial` is usable output, not an absence of output - and
    # `pages_analysed` must be the strict subset section 4.7 requires. The reply cited
    # page 1 and stopped, so pages 2 and 3 were never reported on.
    assert outcome.artifact is not None
    assert outcome.artifact["pages_analysed"] == [1]


def test_a_proxied_normal_stop_is_still_a_complete_success() -> None:
    """Anti-vacuity. A translation that reported every call truncated would pass above."""
    outcome = _run("stop")

    assert outcome.status == STATUS_SUCCEEDED
    assert outcome.metrics["call_status"] == "succeeded"
    assert outcome.error is None
    assert outcome.artifact is not None
    assert outcome.artifact["pages_analysed"] == [1, 2, 3]
