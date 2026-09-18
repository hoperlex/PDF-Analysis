"""The LLM-proxy adapter: a real model call that does not go straight to a provider.

``OD-02`` pinned the Anthropic first-party API. The owner revised it on 2026-09-14 to an
already-operated LLM proxy, which is OpenAI-compatible and hides the upstream key. That is a
**transport** change, not a provenance one:

* ``provider_mode`` is ``live``. The declared vocabulary is live-or-recorded and the question
  it answers is "did a model actually produce this, or was it replayed". Through a proxy a
  model actually produced it. Introducing a third mode would make every consumer - the CSV's
  column 6, the run badge, the API - re-learn a distinction that does not exist for them;
* the proxy's own identity is recorded in the request provenance instead, so an operator can
  still tell one transport from another.

No HTTP client is pinned in ``P02_LOCK.json`` and none was added. ``urllib.request`` carries
a JSON POST, which is the whole protocol here - the same call `B6` made for the API server.

Two constraints from the proxy that shape this file:

* **streaming is refused** with HTTP 400, so nothing here sets ``stream``;
* ``model``, ``models``, ``provider``, ``route``, ``transforms``, ``plugins``,
  ``stream_options`` and ``debug`` are stripped from the body by the proxy. Sending them is
  not an error, it is a silent no-op - which is worse, so they are not sent.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any, Final, Mapping

from auditmanager.analysis.text.adapter import (
    ModelAdapter,
    ModelRequest,
    ModelResponse,
    ProviderMode,
)
from auditmanager.analysis.text.config import DEPENDENCY_NAME
from auditmanager.shared.errors import DomainError, ErrorCode

#: The values the proxy reads as "I am not choosing a model". Any other string is a real
#: choice that changes routing and billing, and under the proxy's variant A it is ignored
#: entirely - so a wrong slug here is silent rather than refused.
MODEL_STUBS: Final[frozenset[str]] = frozenset({"proxy", "default", "auto"})

_PATH: Final[str] = "/api/v1/chat/completions"
_TIMEOUT_SECONDS: Final[int] = 200  # the proxy's own deadline is ~190s


@dataclass(frozen=True, slots=True)
class ProxySettings:
    """Everything the adapter needs, resolved by the composition root."""

    base_url: str
    token: str
    model: str = "proxy"

    def __post_init__(self) -> None:
        if not self.base_url.startswith(("http://", "https://")):
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                message="the proxy base URL is not an absolute http or https address",
            )
        if not self.token:
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                message=(
                    "the proxy token is empty; the proxy authenticates every call and a "
                    "blank token is refused before the body is read"
                ),
            )


class ProxyAdapter(ModelAdapter):
    """Calls the proxy. Satisfies the same seam as the live and recorded adapters."""

    __slots__ = ("_settings", "_opener")

    def __init__(self, settings: ProxySettings, *, opener: Any | None = None) -> None:
        self._settings = settings
        # Injected for tests, which drive a local stub rather than the network.
        self._opener = opener or urllib.request.urlopen

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.LIVE

    def complete(self, request: ModelRequest) -> ModelResponse:
        body = _to_openai_body(request, self._settings.model)
        payload = json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")

        http = urllib.request.Request(
            self._settings.base_url.rstrip("/") + _PATH,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._settings.token}",
                "Content-Type": "application/json",
                # New per attempt, by the proxy's own rule.
                "X-Request-Id": str(uuid.uuid4()),
                # Stable per logical task: the body is a pure function of the document and
                # the prompt bundle - no run id, no timestamp - so hashing it gives a key
                # that survives a retry and differs between documents. Without this every
                # retry is a fresh paid upstream call rather than a deduplicated one.
                "X-Idempotency-Key": _idempotency_key(payload, self._settings.model),
            },
        )

        started = time.monotonic()
        try:
            with self._opener(http, timeout=_TIMEOUT_SECONDS) as response:
                raw = response.read()
                status = response.status
        except urllib.error.HTTPError as exc:  # noqa: PERF203 - each status means something
            raise _map_http_failure(exc, self._settings.model) from None
        except urllib.error.URLError as exc:
            raise DomainError(
                ErrorCode.DEPENDENCY_UNAVAILABLE,
                message="the model proxy could not be reached",
            ) from None
        latency_ms = int((time.monotonic() - started) * 1000)

        if status != 200:
            raise DomainError(
                ErrorCode.ANALYSIS_FAILED,
                message=f"the model proxy answered with an unexpected status {status}",
            )
        return _from_openai_response(json.loads(raw), latency_ms)


def _idempotency_key(payload: bytes, model: str) -> str:
    import hashlib

    # The model slug is part of the key. Without it, repeating one document after switching
    # models would collapse onto the earlier call and return the older model's answer.
    return hashlib.sha256(model.encode("utf-8") + b"\0" + payload).hexdigest()


def _to_openai_body(request: ModelRequest, model: str) -> dict[str, Any]:
    """Translate the Anthropic-shaped body the prompt module builds.

    The Anthropic-only keys are dropped rather than forwarded. Under the proxy's variant A
    the upstream model is the operator's choice and may not be an Anthropic one, and a
    provider-specific field sent to a model that does not know it is either an error or,
    worse, silently ignored.
    """
    source: Mapping[str, Any] = request.body
    messages: list[dict[str, Any]] = []
    system = source.get("system")
    if system:
        messages.append({"role": "system", "content": system})
    messages.extend(dict(m) for m in source.get("messages", ()))

    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": source.get("max_tokens"),
    }

    schema = (
        source.get("output_config", {}).get("format", {}).get("schema")
        if isinstance(source.get("output_config"), Mapping)
        else None
    )
    if schema is not None:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "text_observations", "schema": schema, "strict": True},
        }
    return {k: v for k, v in body.items() if v is not None}


def _from_openai_response(document: Mapping[str, Any], latency_ms: int) -> ModelResponse:
    choices = document.get("choices") or []
    if not choices:
        raise DomainError(
            ErrorCode.ANALYSIS_FAILED,
            message="the model proxy returned no choices, so there is nothing to publish",
        )
    message = choices[0].get("message") or {}
    usage = document.get("usage") or {}
    return ModelResponse(
        output_text=message.get("content") or "",
        # OpenAI's `length` is the truncation stop; the provenance vocabulary calls it
        # `truncated`, which the migration 0003 CHECK now admits.
        stop_reason=_stop_reason(choices[0].get("finish_reason")),
        input_tokens=int(usage.get("prompt_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or 0),
        latency_ms=latency_ms,
        # The proxy returns the real spend for the call, including whatever the upstream
        # actually charged. It is the only number here that is measured rather than derived.
        reported_cost_usd=_reported_cost(usage),
    )


def _reported_cost(usage: Mapping[str, Any]) -> float | None:
    value = usage.get("cost")
    return float(value) if isinstance(value, (int, float)) else None


def _stop_reason(finish_reason: str | None) -> str:
    return {"stop": "end_turn", "length": "truncated"}.get(
        finish_reason or "stop", finish_reason or "end_turn"
    )


def _map_http_failure(exc: urllib.error.HTTPError, model: str) -> DomainError:
    """Map the proxy's documented statuses onto the frozen catalog.

    The proxy answers its own failures as ``{"error": {"code": ...}}`` and passes upstream
    failures through unchanged, so the status is the reliable signal and the code is read
    only when it is there.
    """
    try:
        detail = json.loads(exc.read() or b"{}")
    except ValueError:
        detail = {}
    code = (detail.get("error") or {}).get("code", "")

    if exc.code == 401:
        # `dependency_unavailable` is `retryable: true`, so this mapping used to tell a
        # caller to retry a rejected credential -- an operation that cannot succeed until
        # an operator changes something, presented as one that will. That is the `D-7`
        # defect in a second place: `R-3` added `dependency_credential_refused` (500, not
        # retryable) for exactly this scenario, and the proxy refusing our token is it.
        # `dependency` carries the stable class name the sibling adapters already use, so
        # an operator reads *which* credential was refused from one vocabulary.
        return DomainError(
            ErrorCode.DEPENDENCY_CREDENTIAL_REFUSED,
            message="the model proxy refused the configured credential",
            dependency=DEPENDENCY_NAME,
        )
    if exc.code == 400 and code == "model_not_allowed":
        # Configuration, not a fault: the proxy names the permitted set and retrying cannot
        # change it. The requested slug is named because a wrong value in configuration is
        # otherwise hours of diagnosis.
        return DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message=(
                "the model proxy does not permit the configured model for this client; "
                "the configured value is not one the operator allows"
            ),
        )
    if exc.code == 400:
        return DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the model proxy refused the request body",
        )
    if exc.code == 413:
        return DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the request exceeds the model proxy's body limit",
        )
    if exc.code in (429, 503):
        return DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="the model proxy is saturated; the call was not made",
        )
    if exc.code == 504:
        return DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="the model proxy exceeded its deadline before answering",
        )
    return DomainError(
        ErrorCode.ANALYSIS_FAILED,
        message=f"the model proxy answered with status {exc.code}",
    )
