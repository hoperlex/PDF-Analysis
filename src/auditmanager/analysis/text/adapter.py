"""The model-adapter seam: one request shape, one response shape, two adapters.

``provider_mode`` is a **class constant on the adapter**, exposed read-only. It is not
a constructor argument, not a field a caller can set and not something derived from
configuration. That is the mechanism behind the ``PC-01`` acceptance criterion that a
recorded run must never be presentable as a live one: the mode written into a model
call record comes from the object that actually produced the response, so relabelling
the configuration, the recording file or the artifact cannot change it.

Requests are built once and hashed once. The checksum covers the exact JSON body that
would go to the provider, so a prompt edit, a schema edit, a parameter change or a
different document all produce a different key - and the recorded adapter, which is
keyed by that checksum, then correctly reports that it has no recording rather than
replaying a response to a different question.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable

from auditmanager.analysis.text.config import ProviderMode
from auditmanager.analysis.text.prompt import PromptBundle, canonical_json, render_document
from auditmanager.analysis.text.textlayer import TextLayer

#: The provider this stage calls. ``OD-02``: Anthropic first-party API.
PROVIDER: str = "anthropic"


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """Exactly the body that goes to the provider, plus its checksum."""

    model_id: str
    body: Mapping[str, Any]

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
    *, model_id: str, bundle: PromptBundle, text_layer: TextLayer
) -> ModelRequest:
    """Build the one request this stage makes for a document.

    Nothing time-varying, random or identity-bearing enters the body: no run
    identity, no profile ULID, no timestamp. Two replays of the same document with the
    same bundle therefore produce byte-identical bodies and identical checksums, which
    is what makes the recorded adapter deterministic.
    """
    body: dict[str, Any] = {
        "model": model_id,
        "max_tokens": bundle.max_output_tokens,
        "system": bundle.system_prompt,
        "messages": [
            {"role": "user", "content": render_document(text_layer)},
        ],
        "thinking": dict(bundle.thinking),
        "output_config": {
            "effort": bundle.effort,
            "format": {"type": "json_schema", "schema": bundle.response_schema},
        },
    }
    return ModelRequest(model_id=model_id, body=body)
