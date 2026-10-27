"""The model-adapter seam: one request shape, one response shape, two adapters.

``provider_mode`` is a **class constant on the adapter**, exposed read-only. It is not
a constructor argument, not a field a caller can set and not something derived from
configuration. That is the mechanism behind the ``PC-01`` acceptance criterion that a
recorded run must never be presentable as a live one: the mode written into a model
call record comes from the object that actually produced the response, so relabelling
the configuration, the recording file or the artifact cannot change it.

Requests are built once and hashed once. The checksum covers the JSON body,
including any selected image descriptor with its byte digest. A prompt edit,
schema edit, parameter change, document or selected crop therefore changes the
key; recorded responses cannot replay against another question. Direct
transports turn the descriptor's separately verified PNG into an API image block.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from auditmanager.analysis.text.config import ProviderMode
from auditmanager.analysis.text.prompt import PromptBundle, canonical_json, render_document
from auditmanager.analysis.text.recognised_input import RecognisedPage
from auditmanager.analysis.text.textlayer import TextLayer

#: The provider this stage calls. ``OD-02``: Anthropic first-party API.
PROVIDER: str = "anthropic"


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """Exactly the body that goes to the provider, plus its checksum."""

    model_id: str
    body: Mapping[str, Any]
    # Transport-only scope. It never changes the deterministic request checksum or
    # recorded-response lookup; the proxy may use it to deduplicate one logical run.
    idempotency_scope: str | None = None
    # Selected saved crop bytes for direct model transports. The body holds their
    # digest/size descriptor, so the request checksum binds the bytes without
    # copying a PNG into the call journal. Pull transports fetch by descriptor.
    image_bytes: bytes | None = field(default=None, repr=False, compare=False)

    @property
    def request_sha256(self) -> str:
        return hashlib.sha256(canonical_json(self.body).encode("utf-8")).hexdigest()

    @property
    def parameters(self) -> Mapping[str, Any]:
        """The generation parameters, for the call record. Never the document text."""
        return {
            "max_tokens": self.body.get("max_tokens"),
            "output_config": self.body.get("output_config"),
            "thinking": self.body.get("thinking"),
        }


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """What an adapter returns. Identical in shape for live and recorded."""

    output_text: str
    stop_reason: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    #: What the transport says the call actually cost, when it says anything. The direct
    #: provider adapter leaves it ``None`` and the meter falls back to the pinned rate
    #: table. The LLM proxy reports a real figure, and under `OD-02`'s revision the model
    #: is selectable, so no fixed rate table can cover it - a measurement must beat an
    #: estimate whenever one exists.
    reported_cost_usd: float | None = None
    #: The model name the transport's reply itself carries, exactly as it arrived, or ``None``
    #: when the adapter reads none (the recorded and the direct provider adapters) or the
    #: reply named none. It is evidence for the identity check in ``proxy.py`` (``R-133``) and
    #: nothing else: it is not part of ``response_sha256``, so a recorded replay and a proxied
    #: answer to the same question keep one checksum, and it never decides a configured model.
    model: str | None = None

    @property
    def response_sha256(self) -> str:
        return hashlib.sha256(
            canonical_json(
                {
                    "output_text": self.output_text,
                    "stop_reason": self.stop_reason,
                    "input_tokens": self.input_tokens,
                    "output_tokens": self.output_tokens,
                }
            ).encode("utf-8")
        ).hexdigest()

    @property
    def truncated(self) -> bool:
        """The provider stopped at the output ceiling, so the report is incomplete."""
        return self.stop_reason == "max_tokens"


@runtime_checkable
class ModelAdapter(Protocol):
    """The seam both adapters satisfy.

    ``provider_mode`` is a property and never a settable attribute. An implementation
    that made it writable would defeat the whole provenance guarantee, so the stage
    also re-reads it from the adapter for every call rather than caching a copy.
    """

    @property
    def provider_mode(self) -> ProviderMode: ...

    def complete(self, request: ModelRequest) -> ModelResponse: ...


def build_request(
    *, model_id: str, bundle: PromptBundle, text_layer: TextLayer,
    idempotency_scope: str | None = None, user_content: str | None = None,
    recognised: Sequence[RecognisedPage] = (),
) -> ModelRequest:
    """Build the one request this stage makes for a document.

    Nothing time-varying, random or identity-bearing enters the body: no run
    identity, no profile ULID, no timestamp. Two replays of the same document with the
    same bundle therefore produce byte-identical bodies and identical checksums, which
    is what makes the recorded adapter deterministic.

    ``user_content`` (`SECTION-CHUNKED-ANALYSIS-01`) replaces the rendered document as the
    user message and is given only by the windowed analysis, which renders a fragment of the
    text layer. ``None`` is every other caller, and the body is then byte-for-byte what it
    always was.

    ``recognised`` (`SECTION-CATEGORY-OCR-01`) are the recognised-text blocks of text-less pages, rendered
    into the user message as marked context; none is every version without a scanned page, and the body is
    then byte-for-byte what it was. It is meaningless with ``user_content`` (a window renders its own).
    """
    if user_content is not None and recognised:
        raise ValueError("recognised pages are rendered by the caller of a windowed request")
    body: dict[str, Any] = {
        "model": model_id,
        "max_tokens": bundle.max_output_tokens,
        "system": bundle.system_prompt,
        "messages": [
            {
                "role": "user",
                "content": (
                    render_document(text_layer, recognised) if user_content is None else user_content
                ),
            },
        ],
        "thinking": dict(bundle.thinking),
        "output_config": {
            "effort": bundle.effort,
            "format": {"type": "json_schema", "schema": bundle.response_schema},
        },
    }
    return ModelRequest(model_id=model_id, body=body,
                        idempotency_scope=idempotency_scope)
