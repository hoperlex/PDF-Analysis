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

**Model identity** (`MODEL-IDENTITY-CHECK-01`, `R-133`). Which model answers is the gateway's
decision, so the only evidence of what produced an answer is the reply's own ``model`` string.
For a *pinned* configured model that string must equal the configured name or a listed alias;
any other name, or none, is the typed refusal ``model_identity_mismatch`` and nothing is
published. A placeholder configuration (:data:`_UNPINNED_MODEL_NAMES`) cannot be held to a name,
so the check is not applied and :attr:`ProxyAdapter.identity_pinned` reports that it was not.
"""

from __future__ import annotations

import hashlib
import json
import logging
from http.client import HTTPException
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
from auditmanager.analysis.text.wire_schema import to_wire_schema
from auditmanager.shared.errors import DomainError, ErrorCode

#: The values the proxy reads as "I am not choosing a model". Any other string is a real
#: choice that changes routing and billing, and under the proxy's variant A it is ignored
#: entirely - so a wrong slug here is silent rather than refused.
MODEL_STUBS: Final[frozenset[str]] = frozenset({"proxy", "default", "auto"})

#: The two configured names that are placeholders rather than a pinned model, so a reply cannot
#: be held to them (`MODEL-IDENTITY-CHECK-01`, `R-133`). The identity check is not applied for
#: either, and :attr:`ProxyAdapter.identity_pinned` says so out loud.
#:
#: * ``proxy`` - the stub that `bootstrap/settings.py` falls back to when `PROXY_LLM_MODEL` is
#:   unset and that `infra/deploy/env/provider.env.example` ships. It says "I am not choosing a
#:   model"; the gateway picks, and a reply from whatever it picked is the expected answer.
#: * ``replay`` - what `norms/__main__.py:read_proxy_answer` configures to parse a checkpointed
#:   body offline. Nothing is dispatched there, so there is no identity left to verify.
#:
#: `W56A-MODEL-PIN-01` is the day a placeholder stops being tolerated: refusing `proxy` at
#: start-up belongs to the owner of the bootstrap settings, not to this module, and when it
#: lands this set shrinks to ``replay`` or goes away. Exact names only: any other string,
#: ``default`` and ``auto`` included, is treated as a pinned name and held to it.
_UNPINNED_MODEL_NAMES: Final[frozenset[str]] = frozenset({"proxy", "replay"})

#: Appended to an origin-only base URL: the proxy's portal endpoint, which is the path every
#: installation called before `W48-PROXY-01` and still calls when it names no path.
_PORTAL_PATH: Final[str] = "/api/v1/chat/completions"
#: Appended to a base URL that names its own API prefix, such as the agent gateway's
#: `https://<proxy>/agent/v1` -- the OpenAI `base_url` convention the proxy's client guide
#: documents for that gateway.
_COMPLETIONS_PATH: Final[str] = "/chat/completions"
_TIMEOUT_SECONDS: Final[int] = 200  # the proxy's own deadline is ~190s
_ERROR_BODY_LIMIT: Final[int] = 4096
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ReceivedResponse:
    """What is known of a complete HTTP answer whose body could not be used.

    The provider was reached and answered, so the call may have been paid for. When the
    answer's usage block is readable, this is the evidence a call journal records as
    ``response_received``: the checksum of the exact bytes received, the provider's own
    token counts and the latency. It never carries the body itself.
    """

    response_sha256: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class ProxyDispatchError(DomainError):
    """A catalog error with transport evidence kept outside envelope details."""

    __slots__ = ("dispatch_class", "retry_safe", "retry_after_seconds", "received",
                 "http_status", "provider_failure_kind")

    def __init__(
        self, code: ErrorCode, *, dispatch_class: str, retry_safe: bool,
        retry_after_seconds: float = 0.0, message: str | None = None,
        details: Mapping[str, Any] | None = None,
        received: ReceivedResponse | None = None,
        http_status: int | None = None, provider_failure_kind: str | None = None,
    ) -> None:
        super().__init__(code, message=message, **dict(details or {}))
        self.dispatch_class = dispatch_class
        self.retry_safe = retry_safe
        self.retry_after_seconds = retry_after_seconds
        #: Set only for an unusable answer that arrived with a readable usage block.
        self.received = received
        self.http_status = http_status
        self.provider_failure_kind = provider_failure_kind


class _UnusableAnswer(ValueError):
    """A 200 body that is not the documented chat-completions shape."""


@dataclass(frozen=True, slots=True)
class ProxySettings:
    """Everything the adapter needs, resolved by the composition root."""

    base_url: str
    token: str
    model: str = "proxy"
    #: Further names the gateway may report for ``model``, such as a dated variant it echoes
    #: (`MODEL-IDENTITY-CHECK-01`). Empty by default, matched exactly like ``model`` (no prefix,
    #: no case folding) and consulted only when ``model`` is pinned.
    model_aliases: tuple[str, ...] = ()

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
        # `MODEL-IDENTITY-CHECK-01`. An alias is an allow-list entry, so a blank one would
        # accept a reply that names an empty model, and a list or a bare string would be
        # iterated into characters. The model name itself is not validated here: refusing a
        # placeholder at start-up is `W56A-MODEL-PIN-01`'s, and the bootstrap owner's, to do.
        if not isinstance(self.model_aliases, tuple) or any(
            not isinstance(alias, str) or not alias.strip() for alias in self.model_aliases
        ):
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                message=(
                    "the proxy model aliases must be a tuple of non-empty model names; a "
                    "blank alias would accept a reply that names no model"
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

    @property
    def identity_pinned(self) -> bool:
        """Whether replies are held to the configured model (`R-133`).

        ``False`` only for a placeholder name in :data:`_UNPINNED_MODEL_NAMES`: the check is then
        not applied, and this property is how a caller can see that it was not, rather than
        having it pass silently. Read-only, and derived from the settings, so it cannot be set
        to claim a pin the configuration does not hold.
        """
        return self._settings.model not in _UNPINNED_MODEL_NAMES

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
        # From here on an answer was received, so the model call may have been paid for:
        # every refusal is `outcome_unknown` and never retry-safe. `W53C-EXEC-01` C-04: a
        # body of any shape is classified here, so no `AttributeError`/`TypeError` from
        # an unexpected shape escapes the effect journal.
        try:
            document = json.loads(raw)
        except (ValueError, UnicodeError):
            raise _unusable_answer(
                raw, latency_ms, None, "the model proxy returned an invalid answer",
            ) from None
        try:
            response = _from_openai_response(document, latency_ms)
        except _UnusableAnswer as unusable:
            raise _unusable_answer(raw, latency_ms, document, str(unusable)) from None
        except (ValueError, TypeError, AttributeError, KeyError, IndexError,
                OverflowError):
            raise _unusable_answer(
                raw, latency_ms, document, "the model proxy returned an invalid answer",
            ) from None
        # `MODEL-IDENTITY-CHECK-01` (`R-133`). Outside the `try` above, so the typed refusal
        # is not itself caught and re-labelled as an unusable answer. Applied only to a pinned
        # model; `identity_pinned` is the visible record of when it is not.
        if self.identity_pinned and not _is_configured_model(response.model, self._settings):
            raise _identity_mismatch(raw, latency_ms, document, response.model)
        return response


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
    quota = status == 402
    if status == 429:
        try:
            body = json.loads(raw)
            detail = body.get("error", {}) if isinstance(body, dict) else {}
            quota = isinstance(detail, dict) and any(detail.get(key) in (
                "insufficient_quota", "quota_exceeded", "billing_hard_limit_reached",
            ) for key in ("code", "type"))
        except (ValueError, UnicodeError):
            pass
    if quota:
        return ProxyDispatchError(
            mapped.code, dispatch_class="definite_refusal", retry_safe=False,
            message=mapped.custom_message, details=mapped.detail_fields,
            http_status=status, provider_failure_kind="quota",
        )
    if status == 429:
        return ProxyDispatchError(
            mapped.code, dispatch_class="rate_limited", retry_safe=True,
            retry_after_seconds=_retry_after(headers), message=mapped.custom_message,
            details=mapped.detail_fields,
            http_status=status, provider_failure_kind="rate_limit",
        )
    if status in (400, 401, 403, 413):
        return ProxyDispatchError(
            mapped.code, dispatch_class="definite_refusal", retry_safe=False,
            message=mapped.custom_message, details=mapped.detail_fields,
            http_status=status, provider_failure_kind=("auth" if status in (401, 403) else "request"),
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
        # The provider is told the wire form (`AR-V3-WIRE-SCHEMA-01`): the request's own body, and so its
        # checksum, keep the sealed schema; the local parser still checks what the wire form no longer says.
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "text_observations", "schema": to_wire_schema(schema), "strict": True,
            },
        }
    return {k: v for k, v in body.items() if v is not None}


def _unusable_answer(
    raw: bytes, latency_ms: int, document: Any, message: str
) -> ProxyDispatchError:
    """The typed refusal for a complete answer that cannot be used.

    ``received`` carries the usage evidence when the body is an object whose usage
    block holds two readable token counts; otherwise the journal can only say the
    outcome is unknown.
    """
    return ProxyDispatchError(
        ErrorCode.ANALYSIS_FAILED, dispatch_class="outcome_unknown", retry_safe=False,
        message=message, received=_received_evidence(raw, latency_ms, document),
    )


def _received_evidence(
    raw: bytes, latency_ms: int, document: Any
) -> ReceivedResponse | None:
    """The usage evidence of a complete answer, or ``None`` when its counts are unreadable."""
    tokens = _usage_tokens(document)
    if tokens is None:
        return None
    return ReceivedResponse(
        response_sha256=hashlib.sha256(raw).hexdigest(),
        input_tokens=tokens[0],
        output_tokens=tokens[1],
        latency_ms=latency_ms,
    )


def _is_configured_model(reported: str | None, settings: ProxySettings) -> bool:
    """Exact match of the reply's model against the configured name or a listed alias.

    A reply that names no model is not a match: the check fails closed, and a gateway's name
    for a model is never guessed from what it did not say (``R-133``).
    """
    return reported is not None and (
        reported == settings.model or reported in settings.model_aliases
    )


def _identity_mismatch(
    raw: bytes, latency_ms: int, document: Any, reported: str | None
) -> ProxyDispatchError:
    """The typed refusal for an answer from another model than the configured one.

    The answer arrived, so the call may have been paid for: it is ``outcome_unknown``, never
    retry-safe, and it carries the usage evidence exactly as an unusable answer does. The
    message names no model, no endpoint and no credential, as the catalog entry requires; the
    reported name goes to the server-side log only, bounded and escaped, so an operator can
    tell a foreign model from a dated variant that belongs in ``model_aliases``.
    """
    _LOGGER.warning(
        "model proxy identity mismatch: reported=%.80r", reported,
    )
    return ProxyDispatchError(
        ErrorCode.MODEL_IDENTITY_MISMATCH, dispatch_class="outcome_unknown",
        retry_safe=False,
        message=(
            "the model proxy answered with a model other than the configured one, or "
            "named none; the answer is not published"
        ),
        received=_received_evidence(raw, latency_ms, document),
    )


def _token_count(value: Any) -> int:
    """One usage count: absent means zero, anything but a non-negative integer is refused."""
    if value is None:
        return 0
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _UnusableAnswer("the model proxy returned a usage count that is not a count")
    return value


def _usage_tokens(document: Any) -> tuple[int, int] | None:
    """The provider's two token counts, or ``None`` when they cannot be read."""
    if not isinstance(document, Mapping):
        return None
    usage = document.get("usage")
    if not isinstance(usage, Mapping):
        return None
    try:
        return (
            _token_count(usage.get("prompt_tokens")),
            _token_count(usage.get("completion_tokens")),
        )
    except _UnusableAnswer:
        return None


def _from_openai_response(document: Any, latency_ms: int) -> ModelResponse:
    """Read the documented chat-completions shape, refusing anything else by name."""
    if not isinstance(document, Mapping):
        raise _UnusableAnswer("the model proxy returned an answer that is not an object")
    choices = document.get("choices")
    if choices is None:
        choices = []
    if not isinstance(choices, list):
        raise _UnusableAnswer("the model proxy returned choices that are not a list")
    if not choices:
        raise _UnusableAnswer(
            "the model proxy returned no choices, so there is nothing to publish"
        )
    choice = choices[0]
    if not isinstance(choice, Mapping):
        raise _UnusableAnswer("the model proxy returned a choice that is not an object")
    message = choice.get("message")
    if message is None:
        message = {}
    if not isinstance(message, Mapping):
        raise _UnusableAnswer("the model proxy returned a message that is not an object")
    content = message.get("content")
    if content is not None and not isinstance(content, str):
        raise _UnusableAnswer("the model proxy returned message content that is not text")
    finish_reason = choice.get("finish_reason")
    if finish_reason is not None and not isinstance(finish_reason, str):
        raise _UnusableAnswer("the model proxy returned a finish reason that is not text")
    usage = document.get("usage")
    if usage is None:
        usage = {}
    if not isinstance(usage, Mapping):
        raise _UnusableAnswer("the model proxy returned usage that is not an object")
    return ModelResponse(
        output_text=content or "",
        # OpenAI's `length` is the truncation stop. It is translated into the *stop
        # reason* vocabulary the seam speaks, not into the call-status vocabulary.
        stop_reason=_stop_reason(finish_reason),
        input_tokens=_token_count(usage.get("prompt_tokens")),
        output_tokens=_token_count(usage.get("completion_tokens")),
        latency_ms=latency_ms,
        # The proxy returns the real spend for the call, including whatever the upstream
        # actually charged. It is the only number here that is measured rather than derived.
        reported_cost_usd=_reported_cost(usage),
        model=_reported_model(document),
    )


def _reported_model(document: Mapping[str, Any]) -> str | None:
    """The reply's own ``model`` string. Absent, null or not text all read as none named."""
    value = document.get("model")
    return value if isinstance(value, str) else None


def _reported_cost(usage: Mapping[str, Any]) -> float | None:
    value = usage.get("cost")
    if isinstance(value, bool):
        return None
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


def _map_http_failure(status: int, raw: bytes) -> DomainError:
    """Map a bounded proxy refusal to the existing catalog without guessing a model answer.

    The proxy answers its own failures as ``{"error": {"code": ...}}`` and passes upstream
    failures through unchanged, so the status is the reliable signal and the code is read
    only when it is there.
    """
    truncated = len(raw) > _ERROR_BODY_LIMIT
    body = raw[:_ERROR_BODY_LIMIT]
    # An upstream error body can contain the entire prompt or a credential. Even a
    # bounded, regex-redacted excerpt is unsafe: arbitrary private prose survives it.
    _LOGGER.warning("model proxy HTTP refusal: status=%s truncated=%s", status, truncated)
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
    if status == 429:
        return DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="the model proxy is saturated; the call was not made",
        )
    if status == 503:
        return DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="the model proxy returned status 503; the model call outcome is unknown",
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
