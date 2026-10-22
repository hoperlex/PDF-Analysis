"""Fixtures shared by the executor-runner tests: a fake runner API server, a fake OpenAI-compatible
endpoint, and a driver for the stdio MCP bridge. Standard library only.

Every process started here is a child of the test and is stopped through its own handle
(never by name or pattern).
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional

REPO = Path(__file__).resolve().parents[3]
RUNNER_DIR = REPO / "tools" / "executor-runner"
BRIDGE = RUNNER_DIR / "mcp_bridge.py"
AGENT = RUNNER_DIR / "agent.py"
TOKEN = "amr_TESTTOKEN_0123456789abcdef"


def stamp(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def make_task(task_id: str = "ext_TASK1", model: str = "claude-opus-5", lease: int = 3, window: int = 120, **overrides: Any) -> dict:
    now = time.time()
    task = {
        "task_id": task_id,
        "claim_expires_at": stamp(now + lease),
        "deadline_at": stamp(now + window),
        "model": model,
        "system": "You extract findings. Reply with JSON only.",
        "user_text": "Document text: the contract term is 12 months.",
        "output_schema": {"type": "object", "properties": {"findings": {"type": "array"}}, "required": ["findings"]},
    }
    task.update(overrides)
    return task


@dataclass
class Reply:
    status: int = 200
    body: Optional[Any] = None
    headers: dict = field(default_factory=dict)


def envelope(code: str, message: str, retryable: bool = False) -> dict:
    return {"contract_version": "1.0.0", "error_code": code, "message": message, "correlation_id": "corr-1", "retryable": retryable}


class FakeRunner:
    """The runner API of RUNNER_API.md with a scripted behaviour."""

    def __init__(self, token: str = TOKEN, lease: int = 3) -> None:
        self.token = token
        self.lease = lease
        self.revoked = False
        self.requests: list[dict] = []
        self._tasks: "queue.Queue[dict]" = queue.Queue()
        self._overrides: dict[str, "queue.Queue[Reply]"] = {}
        self._lock = threading.Lock()
        runner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:  # noqa: D401
                return

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw) if raw else None
                except ValueError:
                    body = {"_unparsable": raw.decode("utf-8", "replace")}
                kind, task_id = runner._classify(self.path)
                record = {
                    "t": time.monotonic(),
                    "path": self.path,
                    "kind": kind,
                    "task_id": task_id,
                    "body": body,
                    "authorization": self.headers.get("Authorization"),
                    "content_type": self.headers.get("Content-Type"),
                }
                with runner._lock:
                    runner.requests.append(record)
                reply = runner._decide(kind, record)
                payload = b"" if reply.body is None else json.dumps(reply.body).encode("utf-8")
                self.send_response(reply.status)
                for name, value in reply.headers.items():
                    self.send_header(name, value)
                if payload:
                    self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                if payload:
                    self.wfile.write(payload)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.origin = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self._thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)

    # -- lifecycle
    def __enter__(self) -> "FakeRunner":
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    # -- scripting
    def add_task(self, task: dict) -> None:
        self._tasks.put(task)

    def override(self, kind: str, *replies: Reply) -> None:
        with self._lock:
            q = self._overrides.setdefault(kind, queue.Queue())
            for reply in replies:
                q.put(reply)

    def of_kind(self, kind: str) -> list[dict]:
        with self._lock:
            return [r for r in self.requests if r["kind"] == kind]

    def wait_for(self, kind: str, count: int = 1, timeout: float = 10.0) -> list[dict]:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            found = self.of_kind(kind)
            if len(found) >= count:
                return found
            time.sleep(0.02)
        raise AssertionError(f"timed out waiting for {count} x {kind}; saw {[r['kind'] for r in self.requests]}")

    # -- behaviour
    @staticmethod
    def _classify(path: str) -> tuple[str, Optional[str]]:
        prefix = "/api/v1/runner/tasks/"
        if not path.startswith(prefix):
            return "other", None
        rest = path[len(prefix):]
        if rest == "claim":
            return "claim", None
        task_id, _, action = rest.partition("/")
        return (action if action in ("extend", "answer", "fail") else "other"), task_id

    def _decide(self, kind: str, record: dict) -> Reply:
        if self.revoked or record["authorization"] != "Bearer " + self.token:
            return Reply(401, envelope("authentication_required", "A valid runner token is required."))
        with self._lock:
            q = self._overrides.get(kind)
        if q is not None:
            try:
                return q.get_nowait()
            except queue.Empty:
                pass
        if kind == "claim":
            wait = (record["body"] or {}).get("wait_seconds", 0)
            end = time.monotonic() + float(wait)
            while True:
                try:
                    task = self._tasks.get(timeout=0.05)
                    task = dict(task)
                    if task.get("claim_expires_at") is None:
                        task["claim_expires_at"] = stamp(time.time() + self.lease)
                    return Reply(200, task)
                except queue.Empty:
                    if time.monotonic() >= end:
                        return Reply(204)
        if kind == "extend":
            return Reply(200, {"claim_expires_at": stamp(time.time() + self.lease)})
        if kind == "answer":
            return Reply(200, {"task_id": record["task_id"], "state": "answered"})
        if kind == "fail":
            return Reply(200, {"task_id": record["task_id"], "state": "cancelled"})
        return Reply(404, envelope("not_found", "No such operation."))


class FakeOpenAI:
    """A local OpenAI-compatible /v1/chat/completions endpoint."""

    def __init__(self, content: str = '{"findings": []}', status: int = 200, finish_reason: str = "stop") -> None:
        self.content = content
        self.status = status
        self.finish_reason = finish_reason
        self.requests: list[dict] = []
        endpoint = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                return

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length))
                endpoint.requests.append({"path": self.path, "body": body, "authorization": self.headers.get("Authorization")})
                if endpoint.status != 200:
                    payload = json.dumps({"error": {"message": "echo of the prompt: " + body["messages"][1]["content"]}}).encode()
                    self.send_response(endpoint.status)
                else:
                    payload = json.dumps(
                        {
                            "choices": [{"index": 0, "message": {"role": "assistant", "content": endpoint.content}, "finish_reason": endpoint.finish_reason}],
                            "usage": {"prompt_tokens": 11, "completion_tokens": 7},
                        }
                    ).encode()
                    self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1/chat/completions"
        self._thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)

    def __enter__(self) -> "FakeOpenAI":
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


def clean_env(**extra: str) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.upper().endswith("_PROXY")}
    env.pop("PDF_ANALYSIS_RUNNER_TOKEN", None)
    env.update(extra)
    return env


class McpSession:
    """Drives mcp_bridge.py over its stdio like a client would."""

    def __init__(self, origin: str, token: Optional[str] = TOKEN, extra_args: tuple = ()) -> None:
        env = clean_env()
        if token is not None:
            env["PDF_ANALYSIS_RUNNER_TOKEN"] = token
        self.proc = subprocess.Popen(
            [sys.executable, str(BRIDGE), "--origin", origin, *extra_args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        self.lines: "queue.Queue[bytes]" = queue.Queue()
        self.raw_stdout: list[bytes] = []
        self.stderr_chunks: list[bytes] = []
        self._next_id = 1
        threading.Thread(target=self._pump_out, daemon=True).start()
        threading.Thread(target=self._pump_err, daemon=True).start()

    def _pump_out(self) -> None:
        for line in self.proc.stdout:  # type: ignore[union-attr]
            self.raw_stdout.append(line)
            self.lines.put(line)

    def _pump_err(self) -> None:
        for line in self.proc.stderr:  # type: ignore[union-attr]
            self.stderr_chunks.append(line)

    @property
    def stderr(self) -> str:
        return b"".join(self.stderr_chunks).decode("utf-8", "replace")

    def send(self, message: dict) -> None:
        self.proc.stdin.write(json.dumps(message).encode() + b"\n")  # type: ignore[union-attr]
        self.proc.stdin.flush()  # type: ignore[union-attr]

    def read(self, timeout: float = 15.0) -> dict:
        return json.loads(self.lines.get(timeout=timeout))

    def request(self, method: str, params: Optional[dict] = None, timeout: float = 15.0) -> dict:
        msg_id = self._next_id
        self._next_id += 1
        message: dict = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)
        while True:
            reply = self.read(timeout)
            if reply.get("id") == msg_id:
                return reply

    def notify(self, method: str, params: Optional[dict] = None) -> None:
        message: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)

    def initialize(self) -> dict:
        reply = self.request(
            "initialize",
            {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "0"}},
        )
        self.notify("notifications/initialized")
        return reply

    def call(self, name: str, arguments: Optional[dict] = None, timeout: float = 30.0) -> dict:
        reply = self.request("tools/call", {"name": name, "arguments": arguments or {}}, timeout)
        return reply["result"]

    @staticmethod
    def text(result: dict) -> str:
        return result["content"][0]["text"]

    def payload(self, result: dict) -> dict:
        return json.loads(self.text(result))

    def close(self) -> int:
        try:
            self.proc.stdin.close()  # type: ignore[union-attr]
        except OSError:
            pass
        try:
            return self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            return self.proc.wait()

    def __enter__(self) -> "McpSession":
        return self

    def __exit__(self, *exc: Any) -> None:
        if self.proc.poll() is None:
            self.close()


def write_stub(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env python3\n" + body)
    path.chmod(0o755)
    return path


def agent_config(
    path: Path,
    origin: str,
    *,
    mode: str = "command",
    declared: str = "claude-opus-5",
    argv: Optional[list] = None,
    endpoint_url: str = "",
    extra_runner: str = "",
    extra_endpoint: str = "",
    command_timeout: float = 30.0,
    drain_seconds: int = 5,
) -> Path:
    lines = [
        "[runner]",
        f'origin = "{origin}"',
        "wait_seconds = 1",
        "backoff_min_seconds = 0.2",
        "backoff_max_seconds = 1.0",
        "extend_floor_seconds = 0.5",
        f"drain_seconds = {drain_seconds}",
        extra_runner,
        "[model]",
        f'declared = "{declared}"',
        "[executor]",
        f'mode = "{mode}"',
    ]
    if mode == "command":
        lines += ["[command]", "argv = " + json.dumps(argv or []), f"timeout_seconds = {command_timeout}"]
    else:
        lines += ["[endpoint]", f'url = "{endpoint_url}"', 'model = "local-model"', extra_endpoint]
    path.write_text("\n".join(lines) + "\n")
    return path


class AgentProcess:
    def __init__(self, config: Path, *args: str, token: Optional[str] = TOKEN, env: Optional[dict] = None) -> None:
        full_env = clean_env()
        if token is not None:
            full_env["PDF_ANALYSIS_RUNNER_TOKEN"] = token
        full_env.update(env or {})
        self.proc = subprocess.Popen(
            [sys.executable, str(AGENT), "--config", str(config), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=full_env,
        )
        self.out_chunks: list[bytes] = []
        self.err_chunks: list[bytes] = []
        self._threads = [
            threading.Thread(target=self._drain, args=(self.proc.stdout, self.out_chunks), daemon=True),
            threading.Thread(target=self._drain, args=(self.proc.stderr, self.err_chunks), daemon=True),
        ]
        for t in self._threads:
            t.start()

    @staticmethod
    def _drain(stream: Any, sink: list) -> None:
        for line in stream:
            sink.append(line)

    @property
    def stderr(self) -> str:
        return b"".join(self.err_chunks).decode("utf-8", "replace")

    @property
    def stdout(self) -> str:
        return b"".join(self.out_chunks).decode("utf-8", "replace")

    def wait(self, timeout: float = 30.0) -> int:
        try:
            code = self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
            raise AssertionError(f"agent did not exit within {timeout}s; stderr so far:\n{self.stderr}") from None
        for t in self._threads:
            t.join(timeout=2)
        return code

    def terminate(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()

    def __enter__(self) -> "AgentProcess":
        return self

    def __exit__(self, *exc: Any) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
