"""HTTP client for the executor runner API (see RUNNER_API.md).

Standard library only. Shared by ``mcp_bridge.py`` and ``agent.py``; the one place that
holds the runner token while a request is built, so it is also the one place that scrubs it.

Rules enforced here, because both clients depend on them:

* the token travels only in the ``Authorization`` header, never in a URL or a body;
* every message that leaves this module (exception text included) has the token removed;
* redirects are refused (a redirect would carry the token to another host);
* ``http://`` is accepted only for a loopback host unless the caller opts in explicitly;
* the time left on a claim is computed against the server's clock (``Date`` header), never
  against the local clock alone.
"""

from __future__ import annotations

import calendar
import email.utils
import http.client
import ipaddress
import json
import random
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

API_PREFIX = "/api/v1/runner/tasks"
MAX_REQUEST_BYTES = 1 << 20
MAX_RESPONSE_BYTES = 16 << 20
MAX_WAIT_SECONDS = 25
DEFAULT_RETRY_AFTER = 30.0
MAX_RETRY_AFTER = 300.0
TASK_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
USER_AGENT = "pdf-analysis-runner-client/1"


class RunnerError(Exception):
    """Base class. ``str(error)`` is already scrubbed of the token."""

    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        error_code: Optional[str] = None,
        retry_after: Optional[float] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.error_code = error_code
        self.retry_after = retry_after
        self.correlation_id = correlation_id


class RunnerAuthError(RunnerError):
    """401: the token is missing, wrong, revoked or expired. Never retried."""


class RunnerNotFound(RunnerError):
    """404: unknown task, or one that belongs to another connection."""


class RunnerConflict(RunnerError):
    """409: the task is no longer this runner's to answer."""


class RunnerRejected(RunnerError):
    """400/422 and other 4xx: the request itself was refused (schema, model, bad body)."""


class RunnerThrottled(RunnerError):
    """429: ``retry_after`` seconds must pass before any further call."""


class RunnerUnavailable(RunnerError):
    """5xx, network failure, timeout, redirect or an unreadable response. Retried with backoff."""


def is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def normalize_origin(origin: str, *, allow_insecure_http: bool = False) -> str:
    """Return ``scheme://host[:port]`` or raise ValueError with a message for the operator."""
    parts = urllib.parse.urlsplit(origin.strip())
    if parts.scheme not in ("http", "https"):
        raise ValueError("origin must start with https:// (or http:// for a loopback host)")
    if not parts.hostname:
        raise ValueError("origin has no host")
    try:
        parts.port  # noqa: B018 - raises ValueError on a malformed port
    except ValueError as exc:
        raise ValueError("origin has an invalid port") from exc
    if parts.username or parts.password:
        raise ValueError("origin must not carry credentials")
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise ValueError("origin must be scheme://host[:port] only, with no path, query or fragment")
    if parts.scheme == "http" and not allow_insecure_http and not is_loopback_host(parts.hostname):
        raise ValueError(
            "refusing http:// for a non-loopback host: the runner token would cross the network in "
            "clear (use https://, or pass the explicit insecure flag for a closed test network)"
        )
    return f"{parts.scheme}://{parts.netloc}"


def parse_timestamp(value: str) -> float:
    """RFC 3339 UTC (``2026-10-22T07:30:15Z``, optional fraction) to epoch seconds."""
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})", value)
    if not match:
        raise ValueError(f"not an RFC 3339 timestamp: {value!r}")
    date_part, time_part, fraction, zone = match.groups()
    struct = time.strptime(f"{date_part}T{time_part}", "%Y-%m-%dT%H:%M:%S")
    epoch = float(calendar.timegm(struct)) + (float(fraction) if fraction else 0.0)
    if zone != "Z":
        sign = 1 if zone[0] == "+" else -1
        epoch -= sign * (int(zone[1:3]) * 3600 + int(zone[4:6]) * 60)
    return epoch


def parse_retry_after(value: Optional[str]) -> Optional[float]:
    """Seconds from a ``Retry-After`` header (integer seconds or HTTP-date), clamped."""
    if not value:
        return None
    value = value.strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            when = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        seconds = when.timestamp() - time.time()
    return max(0.0, min(seconds, MAX_RETRY_AFTER))


class Backoff:
    """Exponential backoff with jitter: 1 s, 2 s, 4 s ... capped, reset on success."""

    def __init__(self, minimum: float = 1.0, maximum: float = 60.0) -> None:
        self.minimum = minimum
        self.maximum = maximum
        self._current = 0.0

    def next_delay(self) -> float:
        self._current = self.minimum if self._current == 0.0 else min(self._current * 2, self.maximum)
        return self._current * (1.0 + random.uniform(0.0, 0.1))

    def reset(self) -> None:
        self._current = 0.0


def throttle_delay(error: RunnerThrottled) -> float:
    """The wait a 429 asks for (Retry-After, default 30 s) plus up to 10 % jitter."""
    base = error.retry_after if error.retry_after is not None else DEFAULT_RETRY_AFTER
    return base * (1.0 + random.uniform(0.0, 0.1))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401, ANN001
        return None


class RunnerClient:
    def __init__(
        self,
        origin: str,
        token: str,
        *,
        timeout: float = 30.0,
        allow_insecure_http: bool = False,
        ca_file: Optional[str] = None,
    ) -> None:
        if not token or any(ch in token for ch in "\r\n \t"):
            raise ValueError("the runner token is empty or contains whitespace")
        self.origin = normalize_origin(origin, allow_insecure_http=allow_insecure_http)
        self._token = token
        self.timeout = timeout
        #: server clock minus local clock, in seconds, from the last response with a Date header
        self.clock_skew = 0.0
        host = urllib.parse.urlsplit(self.origin).hostname or ""
        handlers: list[Any] = [_NoRedirect()]
        if is_loopback_host(host):
            handlers.append(urllib.request.ProxyHandler({}))
        if self.origin.startswith("https://"):
            handlers.append(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca_file)))
        self._opener = urllib.request.build_opener(*handlers)

    # ------------------------------------------------------------------ helpers

    def scrub(self, text: str) -> str:
        """Remove the token from any string that is about to be logged or shown."""
        return text.replace(self._token, "***") if text else text

    def server_now(self) -> float:
        return time.time() + self.clock_skew

    def seconds_until(self, timestamp: str) -> float:
        """Seconds from the server's now to an RFC 3339 timestamp from the server."""
        return parse_timestamp(timestamp) - self.server_now()

    def _note_date(self, headers: Any) -> None:
        raw = headers.get("Date") if headers is not None else None
        if not raw:
            return
        try:
            self.clock_skew = email.utils.parsedate_to_datetime(raw).timestamp() - time.time()
        except (TypeError, ValueError):
            return

    def _call(self, path: str, body: Optional[dict], timeout: float) -> tuple[int, Any]:
        url = self.origin + path
        headers = {
            "Authorization": "Bearer " + self._token,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            if len(data) > MAX_REQUEST_BYTES:
                raise RunnerRejected("request body is larger than 1 MiB", status=422, error_code="validation_failed")
            headers["Content-Type"] = "application/json; charset=utf-8"
        request = urllib.request.Request(url, data=data, method="POST", headers=headers)
        try:
            with self._opener.open(request, timeout=timeout) as response:
                status, raw, response_headers = response.status, response.read(MAX_RESPONSE_BYTES + 1), response.headers
        except urllib.error.HTTPError as error:
            status, raw, response_headers = error.code, error.read(MAX_RESPONSE_BYTES + 1), error.headers
            if 300 <= status < 400:
                raise RunnerUnavailable(
                    self.scrub(f"redirect refused (HTTP {status}); check the origin (is it https and the final host?)"),
                    status=status,
                ) from None
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, http.client.HTTPException, ssl.SSLError, OSError) as error:
            reason = getattr(error, "reason", error)
            raise RunnerUnavailable(self.scrub(f"network error: {type(reason).__name__}: {reason}")) from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RunnerUnavailable("response is larger than 16 MiB", status=status)
        self._note_date(response_headers)
        if 200 <= status < 300:
            if status == 204 or not raw:
                return status, None
            try:
                return status, json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                raise RunnerUnavailable("the stand answered 2xx with a body that is not JSON", status=status) from None
        raise self._error_for(status, raw, response_headers)

    def _error_for(self, status: int, raw: bytes, headers: Any) -> RunnerError:
        error_code = None
        message = ""
        correlation_id = headers.get("X-Correlation-Id") if headers is not None else None
        try:
            document = json.loads(raw.decode("utf-8")) if raw else None
        except (ValueError, UnicodeDecodeError):
            document = None
        if isinstance(document, dict):
            code = document.get("error_code")
            error_code = code if isinstance(code, str) else None
            text = document.get("message")
            message = text if isinstance(text, str) else ""
            cid = document.get("correlation_id")
            if isinstance(cid, str):
                correlation_id = cid
        message = self.scrub(message)[:512] or f"HTTP {status}"
        retry_after = parse_retry_after(headers.get("Retry-After") if headers is not None else None)
        kwargs = dict(status=status, error_code=error_code, retry_after=retry_after, correlation_id=correlation_id)
        if status == 401:
            return RunnerAuthError(message, **kwargs)
        if status == 404:
            return RunnerNotFound(message, **kwargs)
        if status == 409:
            return RunnerConflict(message, **kwargs)
        if status == 429:
            kwargs["retry_after"] = retry_after if retry_after is not None else DEFAULT_RETRY_AFTER
            return RunnerThrottled(message, **kwargs)
        if status >= 500:
            return RunnerUnavailable(message, **kwargs)
        return RunnerRejected(message, **kwargs)

    @staticmethod
    def _task_path(task_id: str, action: str) -> str:
        if not isinstance(task_id, str) or not TASK_ID_RE.match(task_id):
            raise RunnerRejected("task_id must match [A-Za-z0-9_-]{1,64}", status=400, error_code="validation_failed")
        return f"{API_PREFIX}/{urllib.parse.quote(task_id, safe='')}/{action}"

    # --------------------------------------------------------------- operations

    def claim(self, wait_seconds: int) -> Optional[dict]:
        """claimExecutorTask. Returns the task document, or None on 204 (nothing arrived)."""
        if not isinstance(wait_seconds, int) or isinstance(wait_seconds, bool) or not 0 <= wait_seconds <= MAX_WAIT_SECONDS:
            raise RunnerRejected("wait_seconds must be an integer in 0..25", status=422, error_code="validation_failed")
        _, document = self._call(f"{API_PREFIX}/claim", {"wait_seconds": wait_seconds}, wait_seconds + 20.0)
        if document is None:
            return None
        required = {
            "task_id": str,
            "claim_expires_at": str,
            "deadline_at": str,
            "model": str,
            "system": str,
            "user_text": str,
            "output_schema": dict,
        }
        if not isinstance(document, dict) or any(not isinstance(document.get(key), kind) for key, kind in required.items()):
            raise RunnerUnavailable("the stand answered a claim with a malformed task document", status=200)
        if not TASK_ID_RE.match(document["task_id"]):
            raise RunnerUnavailable("the stand answered a claim with a task_id of an unexpected shape", status=200)
        try:
            parse_timestamp(document["claim_expires_at"])
            parse_timestamp(document["deadline_at"])
        except ValueError:
            raise RunnerUnavailable("the stand answered a claim with a malformed timestamp", status=200) from None
        return document

    def extend(self, task_id: str) -> dict:
        """extendExecutorTaskClaim. Returns ``{"claim_expires_at": ...}``."""
        _, document = self._call(self._task_path(task_id, "extend"), {}, self.timeout)
        if not isinstance(document, dict) or not isinstance(document.get("claim_expires_at"), str):
            raise RunnerUnavailable("the stand answered an extension with a malformed document", status=200)
        return document

    def answer(
        self,
        task_id: str,
        output_text: str,
        model: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> dict:
        """submitExecutorTaskAnswer."""
        body: dict[str, Any] = {"output_text": output_text, "model": model}
        if input_tokens is not None:
            body["input_tokens"] = input_tokens
        if output_tokens is not None:
            body["output_tokens"] = output_tokens
        _, document = self._call(self._task_path(task_id, "answer"), body, self.timeout)
        return document if isinstance(document, dict) else {}

    def fail(self, task_id: str, reason: str) -> dict:
        """failExecutorTask. ``reason`` is cut to 512 characters."""
        text = (reason or "unspecified")[:512]
        _, document = self._call(self._task_path(task_id, "fail"), {"reason": text}, self.timeout)
        return document if isinstance(document, dict) else {}
