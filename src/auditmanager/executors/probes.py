"""«Проверить»: the smallest completion, read into one outcome (plan section 4.1, T-9).

`EXEC-HTTP-01` (`R-143`). A probe runs **on the worker**, so it goes over the network path real
calls take: the container's egress, the VPN route. It sends one request with ``max_tokens: 16``
and maps the result to the outcome vocabulary that ``executor_probe`` stores:

==========================  =====================================================================
``destination_refused``      the address is one the worker may not send a key to (T-9)
``unreachable``              the name does not resolve, the connection is refused or reset, TLS fails
``timeout``                  no answer within the revision's timeout
``ip_refused``               HTTP 403 whose body is HTML: the gateway's front door, not its API
``credential_refused``       HTTP 401 or 403 otherwise
``protocol_error``           any other status, or a 200 that is not a chat completion
``model_mismatch``           the answer names no model, a placeholder or another model than the
                             revision's *gateway name*
``rate_mismatch``            a ``metered`` revision whose gateway reports a cost off the pin's rates
``ok``                       none of the above
==========================  =====================================================================

**A probe never keeps a body, a header or an address.** The stored detail is a fixed phrase, and
the only values that reach it are a status code and a destination category. A provider's error body
can echo the key it was sent, so none is read into a detail.
"""

from __future__ import annotations

import json
import socket
import ssl
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any, Final

from auditmanager.executors.destinations import (
    DestinationPolicy,
    DestinationRefused,
    DestinationUnresolvable,
    build_opener,
    refusal_of,
)
from auditmanager.executors.http_adapter import (
    cause_of,
    completions_url,
    http_modules,
    pinned_transport,
)
from auditmanager.executors.identity import (
    PROMPT,
    Assessment,
    assess_chat_completion,
    assess_identity,
)
from auditmanager.executors.model import RevisionSettings

__all__ = ["MAX_OUTPUT_TOKENS", "ProbeResult", "classify_status", "probe_http_api", "scrub"]

MAX_OUTPUT_TOKENS: Final[int] = 16
_MAX_RESPONSE_BYTES: Final[int] = 65_536
_ERROR_BODY_BYTES: Final[int] = 512
_DETAIL_LIMIT: Final[int] = 500


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """What ``record_probe_result`` stores. ``detail`` is scrubbed and at most 500 characters."""

    outcome: str
    detail: str | None = None
    reported_model: str | None = None
    identity_basis: str | None = None
    latency_ms: int | None = None
    http_status: int | None = None
    rate_check: str | None = None
    observed_host_key: str | None = None


def scrub(text: str | None, *secrets: str) -> str | None:
    """``text`` with every given secret removed, cut to the stored limit."""
    if text is None:
        return None
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[removed]")
    return text[:_DETAIL_LIMIT]


def _looks_like_html(content_type: str, head: bytes) -> bool:
    start = head.lstrip()[:256].lower()
    return ("text/html" in content_type.lower() or start.startswith(b"<!doctype html")
            or start.startswith(b"<html") or b"<html" in start)


def classify_status(status: int, content_type: str, head: bytes) -> ProbeResult:
    """The outcome of a non-200 answer, from the status and the *shape* of the body only."""
    if status == 403 and _looks_like_html(content_type, head):
        return ProbeResult("ip_refused", "the gateway's front door refused this host (HTTP 403)",
                           http_status=status)
    if status in (401, 403):
        return ProbeResult("credential_refused", f"the gateway refused the key (HTTP {status})",
                           http_status=status)
    if status == 429:
        return ProbeResult("protocol_error", "the gateway is saturated (HTTP 429)",
                           http_status=status)
    return ProbeResult("protocol_error", f"the gateway answered HTTP {status}", http_status=status)


def _transport_failure(failure: BaseException, secret: str) -> ProbeResult:
    """Map an exception raised before or during the exchange to an outcome."""
    refused = refusal_of(failure)
    if refused is None and cause_of(failure, (DestinationRefused,)):
        refused = DestinationRefused("reserved")
    if refused is not None:
        return ProbeResult("destination_refused",
                           f"the address is not permitted ({refused.category})")
    if cause_of(failure, (DestinationUnresolvable, socket.gaierror)):
        return ProbeResult("unreachable", "the address does not resolve")
    if cause_of(failure, (TimeoutError, socket.timeout)):
        return ProbeResult("timeout", "no answer within the connection's timeout")
    if cause_of(failure, (ssl.SSLError,)):
        return ProbeResult("unreachable", "the TLS handshake failed")
    if cause_of(failure, (ConnectionError, OSError)):
        return ProbeResult("unreachable", "the connection could not be made")
    return ProbeResult("protocol_error", scrub(f"the exchange failed ({type(failure).__name__})", secret))


def _finish(assessment: Assessment, *, latency_ms: int, status: int | None,
            identity_basis: str = "reported") -> ProbeResult:
    return ProbeResult(
        assessment.outcome, assessment.detail, assessment.reported_model, identity_basis,
        latency_ms, status, assessment.rate_check,
    )


def probe_http_api(
    settings: RevisionSettings, api_key: str, *, policy: DestinationPolicy,
    input_per_mtok_usd: float | None = None, output_per_mtok_usd: float | None = None,
) -> ProbeResult:
    """Probe one ``http_api`` revision with its opened key. Never raises for a network cause."""
    if settings.transport == "ssh_tunnel":
        return ProbeResult("kind_not_served", "the SSH tunnel transport is not served yet")
    assert settings.base_url is not None and settings.transport is not None
    if settings.api_flavour == "anthropic_messages":
        return _probe_anthropic(settings, api_key, policy=policy)
    if settings.api_flavour != "openai_chat":
        return ProbeResult("kind_not_served", "this API flavour is not served")
    body = json.dumps({
        "model": settings.gateway_model,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": MAX_OUTPUT_TOKENS,
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        completions_url(settings.base_url), data=body, method="POST", headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Request-Id": str(uuid.uuid4()),
            "X-Idempotency-Key": str(uuid.uuid4()),
        },
    )
    director = build_opener(policy, transport=settings.transport)
    started = time.monotonic()
    try:
        with director.open(request, timeout=float(settings.timeout_seconds)) as response:
            status = response.status
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as failure:
        head = failure.read(_ERROR_BODY_BYTES)
        content_type = failure.headers.get("Content-Type", "") if failure.headers else ""
        return _with_latency(classify_status(failure.code, content_type, head), started)
    except (urllib.error.URLError, OSError, ssl.SSLError) as failure:
        return _with_latency(_transport_failure(failure, api_key), started)
    except Exception as failure:  # noqa: BLE001 - http.client and friends; never a body or header
        return _with_latency(_transport_failure(failure, api_key), started)
    latency_ms = int((time.monotonic() - started) * 1000)
    if status != 200:
        return _with_latency(classify_status(status, "", raw[:_ERROR_BODY_BYTES]), started)
    if len(raw) > _MAX_RESPONSE_BYTES:
        return ProbeResult("protocol_error", "the answer is larger than a probe expects",
                           latency_ms=latency_ms, http_status=status)
    try:
        payload = json.loads(raw)
    except (UnicodeError, ValueError):
        return ProbeResult("protocol_error", "the answer is not JSON", latency_ms=latency_ms,
                           http_status=status)
    if input_per_mtok_usd is None or output_per_mtok_usd is None:
        assessment = _without_pin(payload, settings)
    else:
        assessment = assess_chat_completion(
            payload, expected_gateway_model=settings.gateway_model, billing=settings.billing,
            input_per_mtok_usd=input_per_mtok_usd, output_per_mtok_usd=output_per_mtok_usd,
        )
    return _finish(assessment, latency_ms=latency_ms, status=status)


def _without_pin(payload: Any, settings: RevisionSettings) -> Assessment:
    """A revision whose pin the lock no longer lists: identity is still checked, the rate
    cannot be, and is recorded as not reported rather than guessed."""
    base = assess_chat_completion(
        payload, expected_gateway_model=settings.gateway_model, billing="not_metered",
        input_per_mtok_usd=0.0, output_per_mtok_usd=0.0,
    )
    rate = "not_metered" if settings.billing != "metered" else "not_reported"
    return Assessment(base.outcome, base.reported_model, rate, base.detail)


def _with_latency(result: ProbeResult, started: float) -> ProbeResult:
    return ProbeResult(
        result.outcome, result.detail, result.reported_model, result.identity_basis,
        int((time.monotonic() - started) * 1000), result.http_status, result.rate_check,
    )


def _probe_anthropic(
    settings: RevisionSettings, api_key: str, *, policy: DestinationPolicy,
) -> ProbeResult:
    import anthropic

    httpx, _ = http_modules()
    assert settings.base_url is not None and settings.transport is not None
    client = anthropic.Anthropic(
        api_key=api_key, base_url=settings.base_url, max_retries=0,
        http_client=httpx.Client(
            transport=pinned_transport(policy, settings.transport), follow_redirects=False,
            trust_env=False,
        ),
    )
    started = time.monotonic()
    try:
        message = client.messages.create(
            model=settings.gateway_model, max_tokens=MAX_OUTPUT_TOKENS,
            messages=[{"role": "user", "content": PROMPT}],
            timeout=float(settings.timeout_seconds),
        )
    except anthropic.APITimeoutError:
        return _with_latency(ProbeResult("timeout", "no answer within the connection's timeout"), started)
    except anthropic.APIStatusError as failure:
        response = failure.response
        content_type = response.headers.get("content-type", "")
        return _with_latency(
            classify_status(response.status_code, content_type, response.content[:_ERROR_BODY_BYTES]),
            started,
        )
    except Exception as failure:  # noqa: BLE001 - connection errors carry the cause chain
        return _with_latency(_transport_failure(failure, api_key), started)
    latency_ms = int((time.monotonic() - started) * 1000)
    text = "".join(getattr(block, "text", "") for block in (message.content or ())
                   if getattr(block, "type", "") == "text")
    if not text.strip():
        return ProbeResult("protocol_error", "the answer carries no text", latency_ms=latency_ms,
                           http_status=200)
    outcome, reported = assess_identity(getattr(message, "model", None), settings.gateway_model)
    rate = "not_metered" if settings.billing != "metered" else "not_reported"
    detail = None if outcome == "ok" else (
        "the answer names no usable model" if reported is None
        else "the answer names another model than the revision's")
    return ProbeResult(outcome, detail, reported, "reported", latency_ms, 200, rate)
