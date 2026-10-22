"""A local OpenAI-compatible (and Anthropic-shaped) gateway for the executor tests.

`EXEC-HTTP-01`. No paid call is ever made: every test that needs a "provider" starts one of
these on 127.0.0.1 and reaches it through a :class:`DestinationPolicy` whose resolver answers a
public documentation-style address and whose ``dial`` maps it to this server. That keeps the
destination rules honest -- a test that wants them refused simply uses the default policy.

The module is loaded by explicit path (``--import-mode=importlib`` gives it no package).
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from auditmanager.executors.destinations import DestinationPolicy

#: A public address (not a documentation range, which ``ipaddress`` treats as non-global).
PUBLIC_ADDRESS = "93.184.216.34"
HOST = "gateway.example.test"

OBSERVATIONS = json.dumps({"observations": []})


class FakeGateway:
    """``behaviour`` picks the answer; every request is recorded in :attr:`requests`."""

    def __init__(
        self, *, behaviour: str = "ok", model: str = "anthropic/claude-opus-5",
        cost: float | None = 0.0402, content: str = OBSERVATIONS,
        input_tokens: int = 1200, output_tokens: int = 340, delay: float = 0.0,
    ) -> None:
        self.behaviour = behaviour
        self.model = model
        self.cost = cost
        self.content = content
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.delay = delay
        self.requests: list[dict[str, Any]] = []
        gateway = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: Any) -> None:  # silence
                return

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                try:
                    body = json.loads(raw or b"{}")
                except ValueError:
                    body = {}
                gateway.requests.append({
                    "path": self.path, "authorization": self.headers.get("Authorization"),
                    "x_api_key": self.headers.get("x-api-key"), "body": body,
                    "host": self.headers.get("Host"),
                })
                if gateway.delay:
                    time.sleep(gateway.delay)
                status, ctype, payload = gateway.answer(self.path, body)
                self.send_response(status)
                if gateway.behaviour == "redirect":
                    self.send_header("Location", "http://127.0.0.1:1/elsewhere")
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    # -- answers --------------------------------------------------------------------------
    def answer(self, path: str, body: dict[str, Any]) -> tuple[int, str, bytes]:
        behaviour = self.behaviour
        if behaviour == "html403":
            return 403, "text/html", b"<html><head><title>403 Forbidden</title></head></html>"
        if behaviour == "json401":
            return 401, "application/json", b'{"error": {"code": "invalid_api_key"}}'
        if behaviour == "json403":
            return 403, "application/json", b'{"error": {"code": "forbidden"}}'
        if behaviour == "http500":
            return 500, "application/json", b'{"error": {"code": "boom"}}'
        if behaviour == "bad_json":
            return 200, "application/json", b"not json at all"
        if behaviour == "redirect":
            return 302, "application/json", b"{}"
        if path.endswith("/v1/messages"):
            return 200, "application/json", json.dumps({
                "id": "msg_1", "type": "message", "role": "assistant", "model": self._reported(),
                "content": [{"type": "text", "text": self.content}],
                "stop_reason": "end_turn", "stop_sequence": None,
                "usage": {"input_tokens": self.input_tokens, "output_tokens": self.output_tokens},
            }).encode()
        document: dict[str, Any] = {
            "id": "chatcmpl-1",
            "choices": [{"message": {"role": "assistant", "content": self.content},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": self.input_tokens, "completion_tokens": self.output_tokens},
        }
        if self.cost is not None:
            document["usage"]["cost"] = self.cost
        reported = self._reported()
        if reported is not None:
            document["model"] = reported
        return 200, "application/json", json.dumps(document).encode()

    def _reported(self) -> str | None:
        if self.behaviour == "wrong_model":
            return "openai/gpt-5-mini"
        if self.behaviour == "no_model":
            return None
        if self.behaviour == "stub_model":
            return "proxy"
        return self.model

    # -- lifecycle ------------------------------------------------------------------------
    def start(self) -> FakeGateway:
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def base_url(self, path: str = "/agent/v1", scheme: str = "http") -> str:
        """The address a connection names; it is never the loopback address the server has."""
        return f"{scheme}://{HOST}:{self.port}{path}"

    def policy(self, **overrides: Any) -> DestinationPolicy:
        """A policy under which ``HOST`` resolves to a public address that is dialled as this
        server. The compose-network rule sees no networks, so it cannot interfere."""
        port = self.port
        options: dict[str, Any] = {
            "resolver": lambda host, _port: [PUBLIC_ADDRESS],
            "dial": lambda address, _port: ("127.0.0.1", port),
            "networks": lambda: (),
        }
        options.update(overrides)
        return DestinationPolicy(**options)
