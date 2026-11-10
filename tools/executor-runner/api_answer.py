#!/usr/bin/env python3
"""Direct API answerers of the host agent: Anthropic Messages, OpenAI Responses, OpenRouter chat completions.

``HOSTS-AGENT-01`` (``RUNNER_API.md`` section 10).  Used by ``host_mode.py`` for a provider whose key is in the
service's key file (owner answer R-153d); never started on its own.  Standard library only, and the same HTTP
approach as the rest of the agent: ``urllib.request`` with redirects refused (a redirect would carry the key to
another host), the system's CA store, ``https://`` unless the host is loopback.

One call is one streamed request.  The answer is the concatenated text of the stream, so a call that is working
shows signs of life (every chunk, keep-alive comments included, is reported to ``activity``) and one that hangs
shows none: the host agent extends the claim only while they arrive.  A read that is silent for ``idle_timeout``
seconds ends the call.  What each answerer sends:

* the requested ``model`` exactly, the requested ``effort`` in the provider's own parameter
  (``output_config.effort`` for Anthropic, ``reasoning.effort`` for OpenAI and OpenRouter) and
  ``max_output_tokens`` in the provider's parameter (``max_tokens`` / ``max_output_tokens`` / ``max_tokens``);
* the task's ``system`` text with the output schema appended as an instruction (OpenAI also gets the schema as a
  constrained ``json_schema`` format when the caller provides a strict copy) and the ``user_text`` as the user turn;
* nothing else: no tools, no stored conversation (``store: false`` at OpenAI), no sampling parameters.

What comes back is the answer as one compact JSON object, the model the provider itself reported (``reported_model``,
exactly as sent, checked against the requested id and the catalogue's ``accepted_reported``) and the token counts.

The key is a function argument: it is put in one request header, and it appears in no exception, message, log or
return value.  Failures are fixed words; the body of an error response is judged for its class and dropped.
"""

from __future__ import annotations

import base64
import json
import queue
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import ipaddress
from dataclasses import dataclass
from typing import Any, Optional, Sequence

PROVIDER_ANTHROPIC = "anthropic_api"
PROVIDER_OPENAI = "openai_api"
PROVIDER_OPENROUTER = "openrouter_api"
API_PROVIDERS = (PROVIDER_ANTHROPIC, PROVIDER_OPENAI, PROVIDER_OPENROUTER)
DEFAULT_BASE_URLS = {
    PROVIDER_ANTHROPIC: "https://api.anthropic.com",
    PROVIDER_OPENAI: "https://api.openai.com",
    PROVIDER_OPENROUTER: "https://openrouter.ai/api",
}
ANTHROPIC_VERSION = "2023-06-01"
_PATHS = {
    PROVIDER_ANTHROPIC: "/v1/messages",
    PROVIDER_OPENAI: "/v1/responses",
    PROVIDER_OPENROUTER: "/v1/chat/completions",
}
#: What each provider accepts as ``effort``; anything else is refused before a request is made.
EFFORTS = {
    PROVIDER_ANTHROPIC: ("low", "medium", "high", "xhigh", "max"),
    PROVIDER_OPENAI: ("minimal", "low", "medium", "high", "xhigh"),
    PROVIDER_OPENROUTER: ("minimal", "low", "medium", "high", "xhigh"),
}
MAX_LINE_BYTES = 8 << 20
MAX_ANSWER_BYTES = 16 << 20
MAX_ERROR_BYTES = 16 << 10
MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")

_AUTH_FAILURE = re.compile(r"invalid[ _-]?(x-)?api[ _-]?key|incorrect api key|authentication|unauthori[sz]ed|permission", re.I)
_MODEL_FAILURE = re.compile(
    r"model.{0,80}(not found|does not exist|not exist|not available|unavailable|invalid|unknown|not supported"
    r"|do not have access|no access)|(unknown|invalid|no such|unsupported) model|no endpoints found", re.I)
_QUOTA_FAILURE = re.compile(
    r"credit balance|insufficient[ _-]?(funds|credit|quota)|quota|billing|usage limit|rate[ _-]?limit|too many requests"
    r"|out of credits|payment required", re.I)


class ApiError(Exception):
    """The call failed.  ``code`` is a fixed word; ``kind`` is ``quota_exceeded``, ``auth_failed`` or
    ``model_not_found`` when it is the host's access that failed (the host agent then takes the model out of
    service), else ``None``."""

    def __init__(self, code: str, kind: Optional[str] = None) -> None:
        super().__init__(code)
        self.code = code
        self.kind = kind


class Interrupted(Exception):
    """The host agent asked the call to stop (lost claim, stalled, shutdown); the connection has been dropped."""


@dataclass(frozen=True)
class ApiReply:
    output_text: str
    reported_model: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


# --------------------------------------------------------------------------------------- helpers


def normalize_base_url(provider: str, base_url: Optional[str] = None) -> str:
    """``scheme://host[:port][/prefix]``: https, or http for a loopback host (a closed test network); no
    credentials, query or fragment."""
    text = (base_url or DEFAULT_BASE_URLS[provider]).strip()
    parts = urllib.parse.urlsplit(text)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("an API base URL starts with https:// and names a host")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("an API base URL carries no credentials, query or fragment")
    if parts.scheme == "http" and not _loopback(parts.hostname):
        raise ValueError("an API base URL is https:// outside a loopback host: the key would cross the network in clear")
    try:
        parts.port  # noqa: B018 - raises ValueError on a malformed port
    except ValueError:
        raise ValueError("an API base URL has an invalid port") from None
    return f"{parts.scheme}://{parts.netloc}{parts.path.rstrip('/')}"


def _loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _tokens(value: object) -> Optional[int]:
    return value if type(value) is int and value >= 0 else None


def _sum_tokens(*values: object) -> Optional[int]:
    counted = [v for v in values if type(v) is int and v >= 0]
    return sum(counted) if counted else None


def classify_http(status: int, body: bytes) -> ApiError:
    """The class of an error response.  The body is judged for its words and dropped."""
    text = body[:MAX_ERROR_BYTES].decode("utf-8", "replace")
    if status in (401, 403):
        return ApiError("api_auth_failed", "auth_failed")
    if status == 402:
        return ApiError("api_quota_exceeded", "quota_exceeded")
    if status == 404:
        return ApiError("api_model_not_found", "model_not_found")
    if status == 429:
        return ApiError("api_quota_exceeded", "quota_exceeded")
    if status == 400:
        if _QUOTA_FAILURE.search(text):
            return ApiError("api_quota_exceeded", "quota_exceeded")
        if _MODEL_FAILURE.search(text):
            return ApiError("api_model_not_found", "model_not_found")
        if _AUTH_FAILURE.search(text):
            return ApiError("api_auth_failed", "auth_failed")
        return ApiError("api_bad_request")
    if status == 413:
        return ApiError("api_request_too_large")
    if status in (408, 409) or status >= 500:
        return ApiError("api_unavailable")
    return ApiError("api_http_error")


def _stream_error(kind: object, code: object = None) -> ApiError:
    """An error event inside a stream (the HTTP status was 200)."""
    words = " ".join(str(item) for item in (kind, code) if isinstance(item, (str, int)))
    if re.search(r"authentication|permission|invalid_api_key|unauthori[sz]ed", words, re.I):
        return ApiError("api_auth_failed", "auth_failed")
    if re.search(r"rate_limit|quota|insufficient|billing|credit", words, re.I):
        return ApiError("api_quota_exceeded", "quota_exceeded")
    if re.search(r"not_found|model_not_found", words, re.I):
        return ApiError("api_model_not_found", "model_not_found")
    if re.search(r"overloaded|unavailable|timeout|server_error|api_error", words, re.I):
        return ApiError("api_unavailable")
    return ApiError("api_stream_error")


def answer_json(text: str) -> str:
    """The model's text as one compact JSON object: a code fence around it is removed, anything else that is not a
    JSON object is an error (the stand validates the object against the task's schema)."""
    stripped = text.strip()
    fenced = re.fullmatch(r"```[A-Za-z0-9_-]*\s*\n(.*?)\n?```", stripped, re.S)
    if fenced:
        stripped = fenced.group(1).strip()
    try:
        document = json.loads(stripped)
    except (ValueError, RecursionError):
        raise ApiError("answer_not_json") from None
    if not isinstance(document, dict):
        raise ApiError("answer_not_object")
    return json.dumps(document, ensure_ascii=False, separators=(",", ":"))


def schema_note(schema: dict) -> str:
    return ("\n\nReturn only one JSON object that validates against this JSON Schema, with no code fence and no "
            "commentary:\n" + json.dumps(schema, ensure_ascii=False, separators=(",", ":")))


def image_data_url(raw: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


# ------------------------------------------------------------------------------------ the requests


def build_request(provider: str, *, model: str, effort: str, max_output_tokens: int, system: str, user_text: str,
                  output_schema: dict, images: Sequence[bytes] = (), strict_schema: Optional[dict] = None) -> dict:
    """The JSON body of one streamed request."""
    instruction = system + schema_note(output_schema)
    if provider == PROVIDER_ANTHROPIC:
        content: Any = user_text
        if images:
            content = [*({"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                      "data": base64.b64encode(raw).decode("ascii")}} for raw in images),
                       {"type": "text", "text": user_text}]
        return {"model": model, "max_tokens": max_output_tokens, "stream": True, "system": instruction,
                "messages": [{"role": "user", "content": content}], "output_config": {"effort": effort}}
    if provider == PROVIDER_OPENAI:
        content = [{"type": "input_text", "text": user_text},
                   *({"type": "input_image", "image_url": image_data_url(raw)} for raw in images)]
        body: dict = {"model": model, "max_output_tokens": max_output_tokens, "stream": True, "store": False,
                      "instructions": instruction, "reasoning": {"effort": effort},
                      "input": [{"role": "user", "content": content}]}
        if strict_schema is not None:
            body["text"] = {"format": {"type": "json_schema", "name": "answer", "schema": strict_schema, "strict": True}}
        return body
    if provider == PROVIDER_OPENROUTER:
        content = user_text
        if images:
            content = [{"type": "text", "text": user_text},
                       *({"type": "image_url", "image_url": {"url": image_data_url(raw)}} for raw in images)]
        return {"model": model, "max_tokens": max_output_tokens, "stream": True, "usage": {"include": True},
                "reasoning": {"effort": effort},
                # a document must not be routed to a provider that keeps it or trains on it
                "provider": {"data_collection": "deny"},
                "messages": [{"role": "system", "content": instruction}, {"role": "user", "content": content}]}
    raise ValueError("not an API provider")


def request_headers(provider: str, api_key: str) -> dict:
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream", "User-Agent": "pdf-analysis-agent/host"}
    if provider == PROVIDER_ANTHROPIC:
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = ANTHROPIC_VERSION
    else:
        headers["Authorization"] = "Bearer " + api_key
    return headers


# ------------------------------------------------------------------------------- the stream readers


class _Sse:
    """Server-sent events, fed chunk by chunk.  ``feed`` returns ``(event name, data text)`` pairs; a comment line
    (a keep-alive) is returned as ``(":", "")`` so that it counts as a sign of life."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._event: Optional[str] = None
        self._data: list = []

    def feed(self, chunk: bytes) -> list:
        self._buffer += chunk
        events: list = []
        while True:
            cut = self._buffer.find(b"\n")
            if cut < 0:
                if len(self._buffer) > MAX_LINE_BYTES:
                    raise ApiError("api_stream_too_large")
                return events
            line = bytes(self._buffer[:cut]).rstrip(b"\r")
            del self._buffer[:cut + 1]
            self._line(line, events)

    def _line(self, line: bytes, events: list) -> None:
        if not line:
            if self._data:
                events.append((self._event, "\n".join(self._data)))
            self._event, self._data = None, []
        elif line.startswith(b":"):
            events.append((":", ""))
        else:
            field, _, value = line.partition(b":")
            if value.startswith(b" "):
                value = value[1:]
            if field == b"event":
                self._event = value.decode("utf-8", "replace")
            elif field == b"data":
                self._data.append(value.decode("utf-8", "replace"))

    def finish(self) -> list:
        events: list = []
        if self._buffer:
            self._line(bytes(self._buffer).rstrip(b"\r"), events)
            self._buffer.clear()
        if self._data:
            events.append((self._event, "\n".join(self._data)))
            self._data = []
        return events


class _Reader:
    """Collects a streamed answer.  ``on_event`` raises :class:`ApiError` for an error event or a refusal."""

    def __init__(self) -> None:
        self.parts: list = []
        self.size = 0
        self.model: Optional[str] = None
        self.tokens_in: Optional[int] = None
        self.tokens_out: Optional[int] = None
        self.done = False

    def add_text(self, text: object) -> None:
        if isinstance(text, str) and text:
            self.size += len(text)
            if self.size > MAX_ANSWER_BYTES:
                raise ApiError("api_answer_too_large")
            self.parts.append(text)

    def on_event(self, name: Optional[str], data: str) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def result(self) -> ApiReply:
        if not self.done:
            raise ApiError("api_stream_ended_early")
        if not self.model:
            raise ApiError("api_no_reported_model")
        text = "".join(self.parts)
        if not text.strip():
            raise ApiError("api_empty_answer")
        return ApiReply(answer_json(text), self.model, self.tokens_in, self.tokens_out)


def _json(data: str) -> Optional[dict]:
    try:
        document = json.loads(data)
    except (ValueError, RecursionError):
        return None
    return document if isinstance(document, dict) else None


class _AnthropicReader(_Reader):
    def on_event(self, name: Optional[str], data: str) -> None:
        document = _json(data)
        if document is None:
            return
        kind = document.get("type") or name
        if kind == "message_start":
            message = document.get("message") if isinstance(document.get("message"), dict) else {}
            model = message.get("model")
            self.model = model if isinstance(model, str) and model else self.model
            usage = message.get("usage") if isinstance(message.get("usage"), dict) else {}
            self.tokens_in = _sum_tokens(usage.get("input_tokens"), usage.get("cache_creation_input_tokens"),
                                         usage.get("cache_read_input_tokens"))
            self.tokens_out = _tokens(usage.get("output_tokens"))
        elif kind == "content_block_delta":
            delta = document.get("delta") if isinstance(document.get("delta"), dict) else {}
            if delta.get("type") == "text_delta":
                self.add_text(delta.get("text"))
        elif kind == "message_delta":
            usage = document.get("usage") if isinstance(document.get("usage"), dict) else {}
            if _tokens(usage.get("output_tokens")) is not None:
                self.tokens_out = usage["output_tokens"]
            delta = document.get("delta") if isinstance(document.get("delta"), dict) else {}
            stop = delta.get("stop_reason")
            if stop == "max_tokens":
                raise ApiError("output_truncated")
            if stop == "refusal":
                raise ApiError("model_refused")
            if stop not in (None, "end_turn", "stop_sequence"):
                raise ApiError("api_unexpected_stop")
        elif kind == "message_stop":
            self.done = True
        elif kind == "error":
            error = document.get("error") if isinstance(document.get("error"), dict) else {}
            raise _stream_error(error.get("type"))


class _OpenAIReader(_Reader):
    def on_event(self, name: Optional[str], data: str) -> None:
        document = _json(data)
        if document is None:
            return
        kind = document.get("type") or name
        response = document.get("response") if isinstance(document.get("response"), dict) else {}
        if kind in ("response.created", "response.in_progress"):
            model = response.get("model")
            self.model = model if isinstance(model, str) and model else self.model
        elif kind == "response.output_text.delta":
            self.add_text(document.get("delta"))
        elif kind == "response.completed":
            model = response.get("model")
            self.model = model if isinstance(model, str) and model else self.model
            usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
            self.tokens_in = _tokens(usage.get("input_tokens"))
            self.tokens_out = _tokens(usage.get("output_tokens"))
            if not self.parts:  # a response whose text arrived whole
                for item in response.get("output") or []:
                    if isinstance(item, dict) and item.get("type") == "message":
                        for part in item.get("content") or []:
                            if isinstance(part, dict) and part.get("type") == "output_text":
                                self.add_text(part.get("text"))
                            elif isinstance(part, dict) and part.get("type") == "refusal":
                                raise ApiError("model_refused")
            self.done = True
        elif kind == "response.incomplete":
            details = response.get("incomplete_details") if isinstance(response.get("incomplete_details"), dict) else {}
            raise ApiError("output_truncated" if details.get("reason") == "max_output_tokens" else "api_incomplete")
        elif kind == "response.refusal.delta":
            raise ApiError("model_refused")
        elif kind in ("response.failed", "error"):
            error = response.get("error") if isinstance(response.get("error"), dict) else document.get("error")
            error = error if isinstance(error, dict) else document
            raise _stream_error(error.get("type"), error.get("code"))


class _ChatReader(_Reader):
    def on_event(self, name: Optional[str], data: str) -> None:
        if data.strip() == "[DONE]":
            self.done = self.done or bool(self.parts)
            return
        document = _json(data)
        if document is None:
            return
        if isinstance(document.get("error"), dict):
            error = document["error"]
            raise _stream_error(error.get("type"), error.get("code"))
        model = document.get("model")
        self.model = model if isinstance(model, str) and model else self.model
        usage = document.get("usage") if isinstance(document.get("usage"), dict) else None
        if usage is not None:
            self.tokens_in = _tokens(usage.get("prompt_tokens"))
            self.tokens_out = _tokens(usage.get("completion_tokens"))
        for choice in document.get("choices") or []:
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta") if isinstance(choice.get("delta"), dict) else {}
            self.add_text(delta.get("content"))
            finish = choice.get("finish_reason")
            if finish == "length":
                raise ApiError("output_truncated")
            if finish == "content_filter":
                raise ApiError("model_refused")
            if finish == "error":
                raise ApiError("api_stream_error")
            if finish in ("stop", "end_turn"):
                self.done = True


_READERS = {PROVIDER_ANTHROPIC: _AnthropicReader, PROVIDER_OPENAI: _OpenAIReader, PROVIDER_OPENROUTER: _ChatReader}


# ---------------------------------------------------------------------------------------- the call


def _pump(response: Any, sink: "queue.Queue") -> None:
    try:
        while True:
            chunk = response.read1(1 << 16)
            if not chunk:
                break
            sink.put(chunk)
    except BaseException as error:  # noqa: BLE001 - handed to the caller, which maps it
        sink.put(error)
    finally:
        sink.put(None)


def _drop(response: Any) -> None:
    """End the connection without waiting for the reader thread: a blocked read holds the response's lock, so a
    plain ``close()`` would wait for it.  The socket is shut down first (which wakes the read) and the close is done
    off this thread."""
    try:
        sock = response.fp.raw._sock  # the one private attribute used: a fallback follows if it is not there
        sock.shutdown(socket.SHUT_RDWR)
    except (AttributeError, OSError):
        pass
    threading.Thread(target=lambda: _quiet_close(response), daemon=True).start()


def _quiet_close(response: Any) -> None:
    try:
        response.close()
    except (OSError, ValueError):
        pass


def call(provider: str, *, api_key: str, model: str, effort: str, max_output_tokens: int, timeout: float,
         system: str, user_text: str, output_schema: dict, base_url: Optional[str] = None,
         idle_timeout: float = 120.0, images: Sequence[bytes] = (), strict_schema: Optional[dict] = None,
         accepted: Sequence[str] = (), activity: object = None, should_stop: object = None) -> ApiReply:
    """One streamed request; the answer, the reported model and the token counts.

    Raises :class:`ApiError` (``kind`` set when the host's access is what failed) or :class:`Interrupted`.
    ``timeout`` bounds the whole call, ``idle_timeout`` a silence on the connection."""
    if provider not in API_PROVIDERS:
        raise ValueError("not an API provider")
    if not isinstance(model, str) or MODEL_ID_RE.fullmatch(model) is None:
        raise ApiError("invalid_model")
    if effort not in EFFORTS[provider]:
        raise ApiError("invalid_effort")
    if type(max_output_tokens) is not int or max_output_tokens < 1:
        raise ApiError("invalid_max_output_tokens")
    if not api_key:
        raise ApiError("api_auth_failed", "auth_failed")
    base = normalize_base_url(provider, base_url)
    body = build_request(provider, model=model, effort=effort, max_output_tokens=max_output_tokens, system=system,
                         user_text=user_text, output_schema=output_schema, images=images, strict_schema=strict_schema)
    payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(base + _PATHS[provider], data=payload, method="POST",
                                     headers=request_headers(provider, api_key))
    handlers: list = [_NoRedirect()]
    if _loopback(urllib.parse.urlsplit(base).hostname or ""):
        handlers.append(urllib.request.ProxyHandler({}))
    opener = urllib.request.build_opener(*handlers)
    started = time.monotonic()
    if should_stop is not None and should_stop():
        raise Interrupted(should_stop())
    if activity is not None:
        activity.touch()
    try:
        response = opener.open(request, timeout=max(1.0, min(idle_timeout, timeout)))
    except urllib.error.HTTPError as error:
        try:
            raw = error.read(MAX_ERROR_BYTES)
        except OSError:
            raw = b""
        if 300 <= error.code < 400:
            raise ApiError("api_redirect_refused") from None
        raise classify_http(error.code, raw) from None
    except (socket.timeout, TimeoutError):
        raise ApiError("timeout") from None
    except (urllib.error.URLError, OSError, ValueError):
        raise ApiError("network_error") from None
    reader = _READERS[provider]()
    sse = _Sse()
    sink: "queue.Queue" = queue.Queue()
    threading.Thread(target=_pump, args=(response, sink), daemon=True).start()
    try:
        while True:
            try:
                item = sink.get(timeout=0.2)
            except queue.Empty:
                item = False
            if item is False:
                pass
            elif item is None:
                for name, data in sse.finish():
                    reader.on_event(name, data)
                break
            elif isinstance(item, BaseException):
                if isinstance(item, (socket.timeout, TimeoutError)):
                    raise ApiError("api_stalled") from None
                raise ApiError("network_error") from None
            else:
                if activity is not None:
                    activity.touch()
                for name, data in sse.feed(item):
                    if name != ":":
                        reader.on_event(name, data)
            if should_stop is not None:
                reason = should_stop()
                if reason:
                    raise Interrupted(reason)
            if time.monotonic() - started >= timeout:
                raise ApiError("timeout")
    finally:
        _drop(response)
    reply = reader.result()
    allowed = {model, *accepted}
    if reply.reported_model not in allowed:
        raise ApiError("reported_model_mismatch")
    return reply
