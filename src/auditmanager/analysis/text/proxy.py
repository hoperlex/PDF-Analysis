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
import logging
from http.client import HTTPException
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
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

#: Appended to an origin-only base URL: the proxy's portal endpoint, which is the path every
#: installation called before `W48-PROXY-01` and still calls when it names no path.
_PORTAL_PATH: Final[str] = "/api/v1/chat/completions"
#: Appended to a base URL that names its own API prefix, such as the agent gateway's
#: `https://<proxy>/agent/v1` -- the OpenAI `base_url` convention the proxy's client guide
#: documents for that gateway.
_COMPLETIONS_PATH: Final[str] = "/chat/completions"
_TIMEOUT_SECONDS: Final[int] = 200  # the proxy's own deadline is ~190s
_ERROR_BODY_LIMIT: Final[int] = 4096
_ERROR_LOG_LIMIT: Final[int] = 512
_LOGGER = logging.getLogger(__name__)
_SENSITIVE_ERROR_TEXT = re.compile(
    r"(?i)\bbearer\s+[^\s\"']+|https?://[^\s\"']+|"
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|"
    r"(?<![A-Za-z0-9])(?:sk|pk|tok|key|secret)[-_][A-Za-z0-9._=-]{6,}|"
    r"(?<![A-Za-z0-9])[A-Za-z0-9+/_=.\-]{24,}(?![A-Za-z0-9])"
)


class ProxyDispatchError(DomainError):
    """A catalog error with transport evidence kept outside envelope details."""

    __slots__ = ("dispatch_class", "retry_safe", "retry_after_seconds")

    def __init__(
        self, code: ErrorCode, *, dispatch_class: str, retry_safe: bool,
        retry_after_seconds: float = 0.0, message: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(code, message=message, **dict(details or {}))
        self.dispatch_class = dispatch_class
        self.retry_safe = retry_safe
        self.retry_after_seconds = retry_after_seconds


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
        # `D-72`. Before the host check, the prefix check accepted `http://:59990` -- a URL
        # with a port and no host -- because it starts with `http://`. At call time `urllib`
        # then reported `dependency_unavailable`, a retryable provider outage for a
        # configuration error. The historical `D-70` incident exposed this shape; this
        # comment makes no claim about the current deployment configuration.
        #
        # `urlsplit().hostname` rather than a second string test: it is the same parse
        # `urllib.request` will perform on this string a moment later, so what is refused
        # here is what the transport would have found missing. It raises `ValueError` on a
        # malformed authority -- an unbracketed IPv6 literal, a non-numeric port -- and that
        # is the same defect arriving by another route, so it is caught and refused with it
        # rather than escaping as an unclassified 500.
        try:
            host = urllib.parse.urlsplit(self.base_url).hostname
        except ValueError:
            host = None
        if not host:
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                message=(
                    "the proxy base URL names no host; a URL of the form "
                    "'http://:<port>' is a lane pointed at nothing and its failures are "
                    "indistinguishable from a provider outage"
                ),
            )
        # `W48-PROXY-01`. The call path is appended to this string, so a query or a fragment
        # would swallow it: `https://<proxy>/agent/v1/chat/completions?x=` reaches the agent
        # gateway with `/api/v1/chat/completions` riding in the query, and works only for as
        # long as the gateway ignores what it is sent. The character test rather than
        # `urlsplit().query`, because a bare trailing `?` parses as an empty query and still
        # swallows the path.
        if "?" in self.base_url or "#" in self.base_url:
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                message=(
                    "the proxy base URL carries a query or a fragment; the call path is "
                    "appended to the base URL, so a base URL must end in its path"
                ),
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
            _completions_url(self._settings.base_url),
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
                "X-Idempotency-Key": _idempotency_key(
                    payload, self._settings.model, request.idempotency_scope
                ),
            },
        )

        started = time.monotonic()
        try:
            with self._opener(http, timeout=_TIMEOUT_SECONDS) as response:
                status = response.status
                raw = response.read() if status == 200 else response.read(_ERROR_BODY_LIMIT + 1)
        except urllib.error.HTTPError as exc:  # noqa: PERF203 - each status means something
            raise _classified_http_failure(
                exc.code, exc.read(_ERROR_BODY_LIMIT + 1), headers=exc.headers
            ) from None
        except urllib.error.URLError as exc:
            # URLError alone says nothing about whether request bytes were written.
            # Only DNS, refused TCP connect and certificate verification prove a
            # pre-dispatch failure. A reset or timeout remains ambiguous.
            before_send = isinstance(
                exc.reason, (socket.gaierror, ConnectionRefusedError,
                             ssl.SSLCertVerificationError)
            )
            raise ProxyDispatchError(
                ErrorCode.DEPENDENCY_UNAVAILABLE, dispatch_class=(
                    "not_sent" if before_send else "outcome_unknown"
                ), retry_safe=before_send,
                message="the model proxy could not be reached",
            ) from None
        except OSError:
            raise ProxyDispatchError(
                ErrorCode.DEPENDENCY_UNAVAILABLE, dispatch_class="outcome_unknown",
                retry_safe=False, message="the proxy connection ended without a complete answer",
            ) from None
        except HTTPException:
            raise ProxyDispatchError(
                ErrorCode.DEPENDENCY_UNAVAILABLE, dispatch_class="outcome_unknown",
                retry_safe=False, message="the proxy response ended before completion",
            ) from None
        latency_ms = int((time.monotonic() - started) * 1000)

        if status != 200:
            raise _classified_http_failure(
                status, raw, headers=getattr(response, "headers", None)
            )
        try:
            return _from_openai_response(json.loads(raw), latency_ms)
        except (ValueError, UnicodeError):
            raise ProxyDispatchError(
                ErrorCode.ANALYSIS_FAILED, dispatch_class="outcome_unknown",
                retry_safe=False, message="the model proxy returned an invalid answer",
            ) from None


def _completions_url(base_url: str) -> str:
    """The URL a call is POSTed to, read off the shape of the configured base URL.

    The proxy serves the same contract at two addresses. Its portal endpoint lives under
    `/api/`, which the proxy's nginx IP-allowlists; its agent gateway lives at
    `/agent/v1/chat/completions` and authenticates by key alone. An installation names the
    first by its origin and the second by its prefix, so the rule is the path:

    * no path (or a bare `/`) - `<origin>/api/v1/chat/completions`, exactly what every
      installation called before `W48-PROXY-01`;
    * any other path - `<base>/chat/completions`, the OpenAI `base_url` convention.

    `W48-PROXY-01`: the stand's IP is not on the portal's allowlist, and the only key it holds
    is an agent-gateway key, so before this rule nothing the stand could configure reached a
    model.
    """
    base = base_url.rstrip("/")
    if not urllib.parse.urlsplit(base_url).path.strip("/"):
        return base + _PORTAL_PATH
    return base + _COMPLETIONS_PATH


def _idempotency_key(payload: bytes, model: str, scope: str | None = None) -> str:
    import hashlib

    # The model slug is part of the key. Without it, repeating one document after switching
    # models would collapse onto the earlier call and return the older model's answer.
    prefix = b"" if scope is None else scope.encode("utf-8") + b"\0"
    return hashlib.sha256(prefix + model.encode("utf-8") + b"\0" + payload).hexdigest()


def _retry_after(headers: Any) -> float:
    if headers is None:
        return 0.0
    raw = headers.get("Retry-After")
    if raw is None:
        return 0.0
    try:
        return max(0.0, min(60.0, float(raw)))
    except (TypeError, ValueError):
        return 0.0


def _classified_http_failure(status: int, raw: bytes, *, headers: Any) -> DomainError:
    mapped = _map_http_failure(status, raw)
    if status == 429:
        return ProxyDispatchError(
            mapped.code, dispatch_class="rate_limited", retry_safe=True,
            retry_after_seconds=_retry_after(headers), message=mapped.custom_message,
            details=mapped.detail_fields,
        )
    if status in (400, 401, 403, 413):
        return ProxyDispatchError(
            mapped.code, dispatch_class="definite_refusal", retry_safe=False,
            message=mapped.custom_message, details=mapped.detail_fields,
        )
    # A 503 is retryable only for the proxy's own measured envelope. No such
    # discriminator is frozen yet; foreign 503 and 504 remain ambiguous.
    return ProxyDispatchError(
        mapped.code, dispatch_class="outcome_unknown", retry_safe=False,
        message=mapped.custom_message, details=mapped.detail_fields,
    )


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
        # OpenAI's `length` is the truncation stop. It is translated into the *stop
        # reason* vocabulary the seam speaks, not into the call-status vocabulary.
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
    """OpenAI's `finish_reason` in the stop-reason vocabulary the seam reads.

    **Two vocabularies, and this function belongs to the first one.**

    * `ModelResponse.stop_reason` is what the *provider* said it stopped for, in the
      Anthropic words `end_turn` and `max_tokens`. `live.py` passes those through
      unchanged and every recording under `fixtures/recorded/text_analysis` is written
      in them. `ModelResponse.truncated` — the single decision that reaches
      `CALL_TRUNCATED`, the salvage branch of `parse_response`, `_pages_analysed` and
      the `partial` run terminal — is `stop_reason == "max_tokens"` and nothing else.
    * `truncated` is a **call status** from `provenance.py`, beside `succeeded` and
      `failed`. It is what `stage.py` *derives*; it is never a stop reason.

    This returned the call-status word `"truncated"` for `length`, so a proxied reply
    cut short at the output ceiling reported `truncated` as `False`: the call was
    recorded `succeeded`, `pages_analysed` claimed the whole document, and the run
    terminated `published` instead of `partial`. The mapping was pinned by a test that
    asserted the string rather than the decision, which is how it survived. `W23-PARTIAL`.

    An unrecognised `finish_reason` is passed through rather than guessed at: it is not
    `max_tokens`, so it cannot silently manufacture a `partial`, and it stays visible in
    the model call record for whoever has to read it.
    """
    return {"stop": "end_turn", "length": "max_tokens"}.get(
        finish_reason or "stop", finish_reason or "end_turn"
    )


def _redacted_error_body(raw: bytes) -> str:
    """Keep one bounded diagnostic line; no raw proxy body reaches the log or API."""
    text = raw[:_ERROR_BODY_LIMIT].decode("utf-8", errors="replace")
    text = _SENSITIVE_ERROR_TEXT.sub("[redacted]", text)
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    return text[:_ERROR_LOG_LIMIT]


def _map_http_failure(status: int, raw: bytes) -> DomainError:
    """Map a bounded proxy refusal to the existing catalog without guessing a model answer.

    The proxy answers its own failures as ``{"error": {"code": ...}}`` and passes upstream
    failures through unchanged, so the status is the reliable signal and the code is read
    only when it is there.
    """
    truncated = len(raw) > _ERROR_BODY_LIMIT
    body = raw[:_ERROR_BODY_LIMIT]
    _LOGGER.warning(
        "model proxy HTTP refusal: status=%s body=%s truncated=%s",
        status,
        _redacted_error_body(body),
        truncated,
    )
    try:
        detail = json.loads(body or b"{}")
    except (ValueError, UnicodeError):
        detail = {}
    error = detail.get("error") if isinstance(detail, dict) else None
    code = error.get("code", "") if isinstance(error, dict) else ""

    if status in (401, 403):
        # `dependency_unavailable` is `retryable: true`, so this mapping used to tell a
        # caller to retry a rejected credential -- an operation that cannot succeed until
        # an operator changes something, presented as one that will. That is the `D-7`
        # defect in a second place: `R-3` added `dependency_credential_refused` (500, not
        # retryable) for exactly this scenario, and the proxy refusing our token is it.
        # `dependency` carries the stable class name the sibling adapters already use, so
        # an operator reads *which* credential was refused from one vocabulary.
        return DomainError(
            ErrorCode.DEPENDENCY_CREDENTIAL_REFUSED,
            message="the model proxy refused its configured credential or access policy",
            dependency=DEPENDENCY_NAME,
        )
    if status == 400 and code == "model_not_allowed":
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
    if status == 400:
        return DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the model proxy refused the request body",
        )
    if status == 413:
        return DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the request exceeds the model proxy's body limit",
        )
    if status in (429, 503):
        return DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="the model proxy is saturated; the call was not made",
        )
    if status == 504:
        return DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="the model proxy exceeded its deadline before answering",
        )
    # 402 (credit), 404 (base path) and other 5xx need operator investigation;
    # an upstream call may already have run. Retrying them is not known to be safe.
    return DomainError(
        ErrorCode.INTERNAL_ERROR,
        message=f"the model proxy returned status {status} before a confirmed model answer",
    )
