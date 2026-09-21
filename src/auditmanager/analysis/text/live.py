"""The live adapter, against the pinned Anthropic SDK.

Live is opt-in per environment and is **never a fallback**. Nothing in this package
constructs this class on a failure path: the recorded adapter reports
``analysis_input_invalid`` and stops, and the stage does not then try a real call.

``ANTHROPIC_API_KEY`` is an injected secret. It is read from the process environment,
never from the lane ``.env``, never written to a file in this repository, and never
placed in a log line, an exception message or an error-envelope detail. The construct
below fails **at construction** when the key is absent, so a live run that was going
to fail fails before it has built a prompt, and the key itself never travels further
than the SDK client.
"""

from __future__ import annotations

import time
from typing import Any, Final

from auditmanager.analysis.text.adapter import ModelRequest, ModelResponse
from auditmanager.analysis.text.config import DEPENDENCY_NAME, ProviderMode
from auditmanager.analysis.text.lock import STAGE_ID, provider_lock
from auditmanager.shared.errors import DomainError, ErrorCode


class LiveAdapter:
    """Calls the provider once per request. No retry and no fallback model."""

    #: Read-only class constant, the counterpart of the recorded adapter's.
    _PROVIDER_MODE: Final[ProviderMode] = ProviderMode.LIVE

    __slots__ = ("_client",)

    def __init__(self, *, api_key: str | None, client: Any | None = None) -> None:
        if client is not None:
            self._client = client
            return
        if not api_key:
            # At construction, not at call time: a live run with no credential is a
            # configuration failure, and it should not first render a document.
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message="live provider mode requires an injected provider credential",
                stage_id=STAGE_ID,
                reason="provider_credential_missing",
            )
        try:
            import anthropic
        except ImportError:
            # Not a transport failure: the SDK is absent from this interpreter and a
            # second attempt would import the same absence. It joins the two
            # construction refusals either side of it -- a missing credential and a
            # version mismatch -- rather than reporting a retryable outage for a
            # deployment fault that no wait can clear.
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message="the pinned provider SDK is not importable",
                stage_id=STAGE_ID,
                reason="provider_sdk_not_importable",
            ) from None
        expected = provider_lock().sdk_version
        installed = getattr(anthropic, "__version__", "")
        if installed != expected:
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message="the installed provider SDK is not the version the P02 lock pins",
                stage_id=STAGE_ID,
                reason="provider_sdk_version_mismatch",
            )
        self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def provider_mode(self) -> ProviderMode:
        return type(self)._PROVIDER_MODE

    def complete(self, request: ModelRequest) -> ModelResponse:
        started = time.monotonic()
        try:
            message = self._client.messages.create(**dict(request.body))
        except Exception as exc:  # noqa: BLE001 - mapped to the catalog below
            raise self._map_provider_failure(exc) from None
        latency_ms = int((time.monotonic() - started) * 1000)

        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        usage = message.usage
        return ModelResponse(
            output_text=text,
            stop_reason=str(message.stop_reason or ""),
            # The lock declares one input rate and no cache rate, so cache tokens are
            # folded into the input count rather than priced at an invented third one.
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0)
            + int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
            + int(getattr(usage, "cache_read_input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            latency_ms=latency_ms,
        )

    @staticmethod
    def _map_provider_failure(exc: Exception) -> DomainError:
        """Map an SDK failure onto the catalog.

        The provider's own message is deliberately dropped: it can carry an endpoint,
        a request URL or an echoed prompt fragment, and every one of those is a shape
        the envelope screen refuses. The catalog code and the stable dependency class
        name are what a caller is entitled to.
        """
        if isinstance(exc, DomainError):
            return exc
        return DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="the model provider did not return a usable response",
            dependency=DEPENDENCY_NAME,
        )
