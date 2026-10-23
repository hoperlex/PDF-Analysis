"""The ``http_api`` connection kind as a model adapter: two flavours, one destination rule.

`EXEC-HTTP-01` (`R-143`, plan section 2.1). A revision names the flavour:

* ``openai_chat`` -- the chat-completions dialect the proxy, OpenRouter, Ollama and vLLM speak.
  The existing :class:`~auditmanager.analysis.public.ProxyAdapter` already parses it, classifies
  its failures into the dispatch classes the call journal needs and (since `MODEL-IDENTITY-CHECK-01`)
  holds a pinned reply to its model; this module only gives it a different *transport*;
* ``anthropic_messages`` -- the Anthropic SDK pointed at the revision's base URL.

Both are built by :func:`build_http_adapter` from a revision and the **opened** key, for one
Attempt, and both go out through the same pinned connection layer
(:mod:`auditmanager.executors.destinations`): the name is resolved, every address is classified
(plan T-9) and the socket is made to the validated address, so a connection that was edited to
point at ``postgres`` or at link-local metadata is refused *in the call*, not only in the probe. No
redirect is followed and no proxy from the environment is used.

The revision's ``gateway_model`` is what is sent and what the reply must report; the pin id
only gives tariffs and the budget (plan section 3). The timeout of each call is the revision's,
cut to what the Attempt's watchdog has left (:class:`~auditmanager.jobs.public.AttemptContext`).
"""

from __future__ import annotations

import dataclasses
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any, Final

from auditmanager.analysis.public import (
    ModelRequest,
    ModelResponse,
    ProviderMode,
    ProxyAdapter,
    ProxyDispatchError,
    ProxySettings,
)
from auditmanager.executors.destinations import (
    DestinationPolicy,
    DestinationRefused,
    DestinationUnresolvable,
    build_opener,
    refusal_of,
)
from auditmanager.executors.image_input import add_anthropic_image, add_openai_image, checked_png
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "DEADLINE_MARGIN_SECONDS",
    "PORTAL_PATH",
    "AnthropicMessagesAdapter",
    "build_http_adapter",
    "cause_of",
    "completions_url",
    "effective_timeout",
    "http_modules",
    "pinned_transport",
]

#: What the watchdog must keep in hand beyond one call: the evidence gate and the terminal.
DEADLINE_MARGIN_SECONDS: Final[int] = 60
PORTAL_PATH: Final[str] = "/api/v1/chat/completions"
_COMPLETIONS_PATH: Final[str] = "/chat/completions"
_DEPENDENCY_DESTINATION: Final[str] = "executor_destination_refused"
_DEPENDENCY_DEADLINE: Final[str] = "executor_deadline"
_DEPENDENCY_NAME: Final[str] = "model_provider"


def completions_url(base_url: str) -> str:
    """The URL a chat completion is POSTed to: ``R-67``, the same rule as ``proxy.py``.

    No path (or ``/``): ``<origin>/api/v1/chat/completions``; any other path:
    ``<base>/chat/completions``. A test holds this equal to the adapter's own."""
    base = base_url.rstrip("/")
    if not urllib.parse.urlsplit(base_url).path.strip("/"):
        return base + PORTAL_PATH
    return base + _COMPLETIONS_PATH


def effective_timeout(
    revision_timeout_seconds: int, context: Any | None, *, margin: int = DEADLINE_MARGIN_SECONDS
) -> float | None:
    """The seconds one call may take: the revision's, cut to the Attempt's remaining watchdog
    minus ``margin``. ``None`` when less than one second is left, which the caller refuses."""
    timeout = float(revision_timeout_seconds)
    if context is not None:
        timeout = min(timeout, float(context.remaining_seconds()) - margin)
    return None if timeout < 1.0 else timeout


def _refused_destination() -> ProxyDispatchError:
    return ProxyDispatchError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, dispatch_class="not_sent", retry_safe=False,
        message="the connection's address is not one the worker may send a key to",
        details={"dependency": _DEPENDENCY_DESTINATION},
    )


def _no_time_left() -> ProxyDispatchError:
    return ProxyDispatchError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, dispatch_class="not_sent", retry_safe=False,
        message="the attempt has too little time left for a model call",
        details={"dependency": _DEPENDENCY_DEADLINE},
    )


class _Opener:
    """What ``ProxyAdapter`` calls as ``opener(request, timeout=...)``: the pinned opener, with
    the call's own timeout and a refused destination turned into its typed, not-sent error."""

    __slots__ = ("_director", "_timeout_seconds", "_context")

    def __init__(self, director: urllib.request.OpenerDirector, timeout_seconds: int,
                 context: Any | None) -> None:
        self._director = director
        self._timeout_seconds = timeout_seconds
        self._context = context

    def __call__(self, request: urllib.request.Request, timeout: float | None = None) -> Any:
        allowed = effective_timeout(self._timeout_seconds, self._context)
        if allowed is None:
            raise _no_time_left()
        try:
            return self._director.open(request, timeout=allowed)
        except urllib.error.URLError as failure:
            if refusal_of(failure) is not None:
                raise _refused_destination() from None
            raise


def _with_reported_model(response: ModelResponse, name: str | None) -> ModelResponse:
    """Attach the model name the reply carried, once ``ModelResponse`` has the field
    (`MODEL-IDENTITY-CHECK-01`). Until the two lanes meet it is a no-op."""
    if "model" in {field.name for field in dataclasses.fields(response)}:
        return dataclasses.replace(response, model=name)  # type: ignore[call-arg]
    return response


def cause_of(failure: BaseException, kinds: tuple[type[BaseException], ...]) -> bool:
    seen: set[int] = set()
    current: BaseException | None = failure
    while current is not None and id(current) not in seen:
        if isinstance(current, kinds):
            return True
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return False


class AnthropicMessagesAdapter:
    """The Anthropic Messages API through the SDK, against a revision's base URL.

    Like ``LiveAdapter``: one call per request, no retry (``max_retries=0``), the provider's own
    message dropped. Unlike it: the model sent is the revision's gateway name, every connection
    is pinned to a validated address, and the SDK's ``model`` is kept as the reported model.
    """

    __slots__ = ("_client", "_gateway_model", "_timeout_seconds", "_context")

    def __init__(
        self, *, base_url: str, api_key: str, gateway_model: str, timeout_seconds: int,
        policy: DestinationPolicy, transport: str, context: Any | None = None,
        client: Any | None = None,
    ) -> None:
        self._gateway_model = gateway_model
        self._timeout_seconds = timeout_seconds
        self._context = context
        if client is not None:
            self._client = client
            return
        import anthropic

        httpx, _ = http_modules()
        self._client = anthropic.Anthropic(
            api_key=api_key, base_url=base_url, max_retries=0,
            http_client=httpx.Client(
                transport=pinned_transport(policy, transport), follow_redirects=False,
                trust_env=False,
            ),
        )

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.LIVE

    def complete(self, request: ModelRequest) -> ModelResponse:
        image = checked_png(request)
        allowed = effective_timeout(self._timeout_seconds, self._context)
        if allowed is None:
            raise _no_time_left()
        body = {**dict(request.body), "model": self._gateway_model}
        body.pop("images", None)
        if image is not None:
            add_anthropic_image(body, image)
        started = time.monotonic()
        try:
            message = self._client.messages.create(**body, timeout=allowed)
        except Exception as failure:  # noqa: BLE001 - mapped to the catalog below
            raise self._map(failure) from None
        latency_ms = int((time.monotonic() - started) * 1000)
        blocks = getattr(message, "content", None) or ()
        text = "".join(block.text for block in blocks if getattr(block, "type", "") == "text")
        usage = getattr(message, "usage", None)
        reported = getattr(message, "model", None)
        response = ModelResponse(
            output_text=text,
            stop_reason=str(getattr(message, "stop_reason", "") or ""),
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0)
            + int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
            + int(getattr(usage, "cache_read_input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            latency_ms=latency_ms,
        )
        return _with_reported_model(response, reported if isinstance(reported, str) else None)

    @staticmethod
    def _map(failure: Exception) -> DomainError:
        """The SDK failure as a dispatch error: what was proven about whether the request left."""
        if isinstance(failure, DomainError):
            return failure
        if cause_of(failure, (DestinationRefused,)):
            return _refused_destination()
        status = getattr(failure, "status_code", None)
        if isinstance(status, int):
            if status in (401, 403):
                return ProxyDispatchError(
                    ErrorCode.DEPENDENCY_CREDENTIAL_REFUSED, dispatch_class="definite_refusal",
                    retry_safe=False,
                    message="the model provider refused the connection's credential",
                    details={"dependency": _DEPENDENCY_NAME},
                )
            if status in (400, 413):
                return ProxyDispatchError(
                    ErrorCode.ANALYSIS_INPUT_INVALID, dispatch_class="definite_refusal",
                    retry_safe=False, message="the model provider refused the request",
                )
            if status == 429:
                return ProxyDispatchError(
                    ErrorCode.DEPENDENCY_UNAVAILABLE, dispatch_class="rate_limited",
                    retry_safe=True, message="the model provider is saturated; the call was not made",
                )
            return ProxyDispatchError(
                ErrorCode.DEPENDENCY_UNAVAILABLE, dispatch_class="outcome_unknown",
                retry_safe=False,
                message="the model provider answered with an error; the outcome is unknown",
            )
        before_send = cause_of(failure, (DestinationUnresolvable, ConnectionRefusedError))
        return ProxyDispatchError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            dispatch_class="not_sent" if before_send else "outcome_unknown",
            retry_safe=before_send,
            message="the model provider could not be reached",
        )


class OpenAIImageAdapter(ProxyAdapter):
    """A pinned proxy call with the selected PNG in the user message."""

    def complete(self, request: ModelRequest) -> ModelResponse:
        image = checked_png(request)
        if image is None:
            return super().complete(request)
        body = add_openai_image(dict(request.body), image)
        body.pop("images", None)
        return super().complete(ModelRequest(
            model_id=request.model_id, body=body,
            idempotency_scope=request.idempotency_scope,
        ))


def http_modules() -> tuple[Any, Any]:
    """The ``(httpx, httpcore)`` pair the installed Anthropic SDK uses. SDK 1.x depends on the
    ``httpx2`` / ``httpcore2`` packages and refuses an ``httpx`` object, so the transport has to be
    built from the same family; an SDK that still uses ``httpx`` gets that one."""
    try:
        import httpcore2 as httpcore
        import httpx2 as httpx
    except ImportError:  # pragma: no cover - an SDK on the older family
        import httpcore
        import httpx
    return httpx, httpcore


def pinned_transport(policy: DestinationPolicy, transport: str) -> Any:
    """An ``httpx`` transport whose every TCP connection is pinned to a validated address."""
    httpx, httpcore = http_modules()

    class _Backend(httpcore.NetworkBackend):
        def __init__(self) -> None:
            self._inner = httpcore.SyncBackend()

        def connect_tcp(self, host: str, port: int, timeout: float | None = None,
                        local_address: str | None = None,
                        socket_options: Any = None) -> Any:
            failure: Exception | None = None
            for address in policy.check(host, port, transport=transport):
                target, target_port = policy.dial(address, port)
                try:
                    return self._inner.connect_tcp(
                        target, target_port, timeout=timeout, local_address=local_address,
                        socket_options=socket_options,
                    )
                except httpcore.ConnectError as exc:
                    failure = exc
            assert failure is not None
            raise failure

        def connect_unix_socket(self, path: str, timeout: float | None = None,
                                socket_options: Any = None) -> Any:
            raise DestinationRefused("reserved")

        def sleep(self, seconds: float) -> None:
            self._inner.sleep(seconds)

    class _Transport(httpx.HTTPTransport):
        def __init__(self) -> None:
            super().__init__(trust_env=False, retries=0)
            self._pool = httpcore.ConnectionPool(
                ssl_context=httpx.create_ssl_context(trust_env=False),
                network_backend=_Backend(), http1=True, http2=False, retries=0,
            )

    return _Transport()


#: kind-agnostic factory signature: ``(settings, api_key, policy, transport, context) -> adapter``.
AdapterBuilder = Callable[..., Any]


def build_http_adapter(
    *, api_flavour: str, base_url: str, api_key: str, gateway_model: str,
    timeout_seconds: int, transport: str, policy: DestinationPolicy, context: Any | None = None,
) -> Any:
    """The adapter of one ``http_api`` revision for one Attempt, or ``validation_failed``
    (``constraint: kind_not_served``) for a flavour or a transport this slice does not serve."""
    if transport == "ssh_tunnel":
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="this transport is not served yet",
            field="transport", constraint="kind_not_served",
        )
    if api_flavour == "openai_chat":
        director = build_opener(policy, transport=transport)
        return OpenAIImageAdapter(
            ProxySettings(base_url=base_url, token=api_key, model=gateway_model),
            opener=_Opener(director, timeout_seconds, context),
        )
    if api_flavour == "anthropic_messages":
        return AnthropicMessagesAdapter(
            base_url=base_url, api_key=api_key, gateway_model=gateway_model,
            timeout_seconds=timeout_seconds, policy=policy, transport=transport, context=context,
        )
    raise DomainError(
        ErrorCode.VALIDATION_FAILED, message="this API flavour is not served",
        field="api_flavour", constraint="kind_not_served",
    )
