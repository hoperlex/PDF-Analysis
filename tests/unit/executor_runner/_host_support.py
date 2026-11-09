"""Fixtures of the `HOSTS-AGENT-01` tests: stand-ins for the `claude` and `codex` CLIs that can be told how to behave
while the agent runs (logged in or not, a model present or absent, a quota error, a call that hangs or drips output),
a fake API server that speaks the streamed form of Anthropic Messages, OpenAI Responses and OpenRouter chat
completions, and a fake stand that speaks the host protocol (`RUNNER_API.md` section 10).

No model is called and nothing leaves the machine: every server listens on loopback and every process is a child of
the test, stopped through its own handle.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional

_NAME = "executor_runner_support"
if _NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_NAME, Path(__file__).with_name("_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module
    _spec.loader.exec_module(_module)
S = sys.modules[_NAME]
RUNNER_DIR = S.RUNNER_DIR

HOST_ID = "exh_01J9ZZZZZZZZZZZZZZZZZZZZZZ"
HOST_SECRET = "ame_h0stk3y9_" + ("Hq7" * 15)[:43]
TASK_SCHEMA = {"type": "object", "properties": {"findings": {"type": "array"}}, "required": ["findings"]}

CATALOGUE = [
    {"provider": "claude_code", "model_id": "claude-opus-5-5", "efforts": ["medium", "high"],
     "accepted_reported": ["claude-opus-5-5-20261001"]},
    {"provider": "claude_code", "model_id": "claude-sonnet-5-5", "efforts": ["low", "medium", "high"], "accepted_reported": []},
    {"provider": "codex", "model_id": "gpt-6.1-sol", "efforts": ["low", "medium", "high"], "accepted_reported": []},
    {"provider": "codex", "model_id": "gpt-6-astra", "efforts": ["low", "medium", "high"], "accepted_reported": []},
    {"provider": "anthropic_api", "model_id": "claude-opus-5-5", "efforts": ["medium", "high"],
     "accepted_reported": ["claude-opus-5-5-20261001"]},
    {"provider": "openai_api", "model_id": "gpt-6.1-sol", "efforts": ["low", "medium", "high"],
     "accepted_reported": ["gpt-6.1-sol-2026-10-01"]},
    {"provider": "openrouter_api", "model_id": "anthropic/claude-opus-5-5", "efforts": ["medium", "high"],
     "accepted_reported": []},
]


# ------------------------------------------------------------------------------------- fake CLIs

_FAKE_CLAUDE = r'''#!{python}
import json, os, pathlib, sys, time
d = pathlib.Path(__file__).resolve().parent
cfg = json.loads((d / "fake.json").read_text())
args = sys.argv[1:]
with open(d / "calls.log", "a") as handle:
    handle.write(" ".join(args) + "\n")
if args[:1] == ["--version"]:
    print(cfg.get("version", "2.1.310") + " (Claude Code)")
    sys.exit(0)
if args[:2] == ["auth", "status"]:
    mode = cfg.get("auth", "subscription")
    if mode == "out":
        print(json.dumps({"loggedIn": False}))
        sys.exit(1)
    method = {"subscription": "claude.ai", "api": "api_key", "weird": "bedrock"}[mode]
    print(json.dumps({"loggedIn": True, "email": "someone@example.com", "authMethod": method}))
    sys.exit(0)
model = args[args.index("--model") + 1]
(d / "last_env.json").write_text(json.dumps(sorted(os.environ)))
(d / "last_env_values.json").write_text(json.dumps(dict(os.environ)))
running = d / "running"
running.mkdir(exist_ok=True)
mine = running / str(os.getpid())
mine.write_text("1")
peak = max(len(list(running.iterdir())), int((d / "peak.txt").read_text()) if (d / "peak.txt").exists() else 0)
(d / "peak.txt").write_text(str(peak))
sys.stdin.read()
def emit(event):
    print(json.dumps(event), flush=True)
try:
    emit({"type": "system", "subtype": "init", "model": model})
    behavior = cfg.get("behavior", "ok")
    schema = json.loads(args[args.index("--json-schema") + 1]) if "--json-schema" in args else {}
    answer = {"ok": True} if "ok" in schema.get("properties", {}) else cfg.get("answer", {"findings": []})
    if model not in cfg.get("models", [model]):
        emit({"type": "result", "subtype": "success", "is_error": True,
               "result": "There's an issue with the selected model (" + model + "). It may not exist or you may not have access to it."})
        sys.exit(1)
    if behavior == "quota":
        emit({"type": "result", "subtype": "success", "is_error": True, "result": "Claude AI usage limit reached|1760000000"})
        sys.exit(1)
    if behavior == "auth_error":
        emit({"type": "result", "subtype": "success", "is_error": True, "result": "Invalid API key - Please run /login"})
        sys.exit(1)
    if behavior == "hang":
        time.sleep(600)
    if behavior == "drip":
        end = time.monotonic() + float(cfg.get("drip_seconds", 2))
        while time.monotonic() < end:
            emit({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "thinking_delta"}}})
            time.sleep(0.2)
    if behavior == "slow":
        time.sleep(float(cfg.get("delay", 1)))
    reported = cfg.get("reported", model)
    usage = {reported: {"inputTokens": 12, "outputTokens": 3, "cacheReadInputTokens": 5, "cacheCreationInputTokens": 7}}
    if cfg.get("extra_usage"):
        usage["claude-haiku-5-5"] = {}
    emit({"type": "result", "subtype": "success", "is_error": False, "terminal_reason": "completed",
           "permission_denials": [], "structured_output": answer, "result": json.dumps(answer), "modelUsage": usage})
finally:
    try:
        mine.unlink()
    except OSError:
        pass
'''

_FAKE_CODEX = r'''#!{python}
import json, os, pathlib, sys, time
d = pathlib.Path(__file__).resolve().parent
cfg = json.loads((d / "fake.json").read_text())
args = sys.argv[1:]
with open(d / "calls.log", "a") as handle:
    handle.write(" ".join(args) + "\n")
if args[:1] == ["--version"]:
    print("codex-cli " + cfg.get("version", "0.46.0"))
    sys.exit(0)
if args[:2] == ["login", "status"]:
    mode = cfg.get("login", "chatgpt")
    if mode == "out":
        print("Not logged in")
        sys.exit(1)
    print("Logged in using ChatGPT" if mode == "chatgpt" else "Logged in using an API key - sk-***abcd" if mode == "apikey" else "Logged in somehow")
    sys.exit(0)
assert args[0] == "exec"
model = args[args.index("--model") + 1]
(d / "last_env_values.json").write_text(json.dumps(dict(os.environ)))
efforts = [args[i + 1] for i, a in enumerate(args) if a == "-c" and args[i + 1].startswith("model_reasoning_effort")]
(d / "last_effort.txt").write_text(efforts[0] if efforts else "")
answer_path = pathlib.Path(args[args.index("--output-last-message") + 1])
schema = json.loads(pathlib.Path(args[args.index("--output-schema") + 1]).read_text())
sys.stdin.read()
running = d / "running"
running.mkdir(exist_ok=True)
mine = running / str(os.getpid())
mine.write_text("1")
peak = max(len(list(running.iterdir())), int((d / "peak.txt").read_text()) if (d / "peak.txt").exists() else 0)
(d / "peak.txt").write_text(str(peak))
def event(**fields):
    print(json.dumps(fields), flush=True)
try:
    event(type="thread.started", thread_id="local")
    event(type="turn.started")
    behavior = cfg.get("behavior", "ok")
    if model not in cfg.get("models", [model]):
        event(type="error", message="The model `" + model + "` does not exist or you do not have access to it.")
        event(type="turn.failed")
        sys.exit(1)
    if behavior == "quota":
        event(type="error", message="You've hit your usage limit. Try again later.")
        event(type="turn.failed")
        sys.exit(1)
    if behavior == "hang":
        time.sleep(600)
    if behavior == "drip":
        end = time.monotonic() + float(cfg.get("drip_seconds", 2))
        while time.monotonic() < end:
            sys.stderr.write("progress\n")
            sys.stderr.flush()
            time.sleep(0.2)
    if behavior == "slow":
        time.sleep(float(cfg.get("delay", 1)))
    answer = {"ok": True} if "ok" in schema.get("properties", {}) else cfg.get("answer", {"findings": []})
    answer_path.write_text(json.dumps(answer))
    extra = {"model": cfg["event_model"]} if cfg.get("event_model") else {}
    event(type="turn.completed", usage={"input_tokens": 21, "output_tokens": 4}, **extra)
finally:
    try:
        mine.unlink()
    except OSError:
        pass
'''


def make_fake(directory: Path, name: str, **settings: Any) -> Path:
    """A stand-in ``claude`` or ``codex`` in ``directory`` whose behaviour is read from ``fake.json`` beside it at
    every call: change it with :func:`configure` while the agent runs."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text((_FAKE_CLAUDE if name == "claude" else _FAKE_CODEX).replace("{python}", sys.executable))
    path.chmod(0o755)
    configure(directory, name, **settings)
    return path


def configure(directory: Path, name: str, **settings: Any) -> None:
    """Change what the stand-in does, merged into the earlier settings of that CLI."""
    target = directory / "fake.json"
    current = json.loads(target.read_text()) if target.exists() else {}
    current.update(settings)
    tmp = directory / "fake.json.tmp"
    tmp.write_text(json.dumps(current))
    os.replace(tmp, target)


def model_calls(directory: Path) -> list[str]:
    """The calls of the stand-in that were model calls (not ``--version`` and not a login/auth status)."""
    log = directory / "calls.log"
    lines = log.read_text().splitlines() if log.exists() else []
    return [line for line in lines if "--model" in line]


def peak(directory: Path) -> int:
    target = directory / "peak.txt"
    return int(target.read_text()) if target.exists() else 0


# ---------------------------------------------------------------------------------------- fake API


class FakeApi:
    """A loopback server for the three API shapes.  ``behavior`` is the next response for every request until it is
    changed: ``ok``, ``401``, ``403``, ``404``, ``429``, ``400_quota``, ``400_schema``, ``hang`` (headers, then
    silence), ``keepalive`` (comments and pings for ``keepalive_seconds``, then the answer), ``error_event``,
    ``truncated`` (the stream ends before its last event), ``max_tokens``, ``redirect``.  ``reported`` is the model
    the stream names (default: the requested one)."""

    def __init__(self) -> None:
        self.behavior = "ok"
        self.reported: Optional[str] = None
        self.keepalive_seconds = 1.0
        self.answer: Any = None  # the answer object; None: {"ok": true} for the probe, {"findings": []} otherwise
        self.requests: list[dict] = []
        self.inflight = 0
        self.peak_inflight = 0
        self._lock = threading.Lock()
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                return

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length)
                body = json.loads(raw)
                record = {"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body,
                          "raw": raw}
                with api._lock:
                    api.requests.append(record)
                    api.inflight += 1
                    api.peak_inflight = max(api.peak_inflight, api.inflight)
                try:
                    api._respond(self, record)
                finally:
                    with api._lock:
                        api.inflight -= 1

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self._thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)

    def __enter__(self) -> "FakeApi":
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    # ---- behaviour

    def _answer_text(self, body: dict) -> str:
        text = json.dumps(body)
        if self.answer is not None:
            return json.dumps(self.answer)
        return json.dumps({"ok": True} if "connectivity check" in text else {"findings": []})

    def _respond(self, handler: BaseHTTPRequestHandler, record: dict) -> None:
        behavior = self.behavior
        status = {"401": 401, "403": 403, "404": 404, "429": 429, "400_quota": 400, "400_schema": 400, "redirect": 302}.get(behavior)
        if status is not None:
            payload = json.dumps({"error": {"message": {
                "400_quota": "Your credit balance is too low to access the API.",
                "400_schema": "invalid schema",
                "404": "model: not found"}.get(behavior, "nope with the key sk-LEAK"), "type": "x"}}).encode()
            handler.send_response(status)
            if status == 302:
                handler.send_header("Location", "http://127.0.0.1:1/elsewhere")
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", str(len(payload)))
            handler.end_headers()
            handler.wfile.write(payload)
            return
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Connection", "close")
        handler.end_headers()
        write = lambda text: (handler.wfile.write(text.encode()), handler.wfile.flush())  # noqa: E731
        try:
            if behavior == "hang":
                time.sleep(30)
                return
            self._stream(handler, record, write)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _stream(self, handler: BaseHTTPRequestHandler, record: dict, write: Any) -> None:
        body = record["body"]
        model = body["model"]
        reported = self.reported or model
        text = self._answer_text(body)
        cut = max(1, len(text) // 2)
        parts = [text[:cut], text[cut:]]
        path = record["path"]
        behavior = self.behavior

        def pause_keepalive(line: str) -> None:
            end = time.monotonic() + self.keepalive_seconds
            while time.monotonic() < end:
                write(line)
                time.sleep(0.15)

        if path == "/v1/messages":
            write("event: message_start\ndata: " + json.dumps({"type": "message_start", "message": {
                "id": "msg_1", "model": reported, "usage": {"input_tokens": 30, "output_tokens": 1}}}) + "\n\n")
            if behavior == "keepalive":
                pause_keepalive("event: ping\ndata: {\"type\": \"ping\"}\n\n")
            if behavior == "error_event":
                write("event: error\ndata: " + json.dumps({"type": "error", "error": {"type": "overloaded_error", "message": "x"}}) + "\n\n")
                return
            write("event: content_block_start\ndata: " + json.dumps({"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}) + "\n\n")
            for part in parts:
                write("event: content_block_delta\ndata: " + json.dumps({"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": part}}) + "\n\n")
            if behavior == "truncated":
                return
            stop = "max_tokens" if behavior == "max_tokens" else "end_turn"
            write("event: message_delta\ndata: " + json.dumps({"type": "message_delta", "delta": {"stop_reason": stop}, "usage": {"output_tokens": 9}}) + "\n\n")
            write("event: message_stop\ndata: {\"type\": \"message_stop\"}\n\n")
        elif path == "/v1/responses":
            write("event: response.created\ndata: " + json.dumps({"type": "response.created", "response": {"model": reported}}) + "\n\n")
            if behavior == "keepalive":
                pause_keepalive(": keep-alive\n\n")
            if behavior == "error_event":
                write("event: error\ndata: " + json.dumps({"type": "error", "code": "server_error", "message": "x"}) + "\n\n")
                return
            for part in parts:
                write("event: response.output_text.delta\ndata: " + json.dumps({"type": "response.output_text.delta", "delta": part}) + "\n\n")
            if behavior == "truncated":
                return
            if behavior == "max_tokens":
                write("event: response.incomplete\ndata: " + json.dumps({"type": "response.incomplete", "response": {"incomplete_details": {"reason": "max_output_tokens"}}}) + "\n\n")
                return
            write("event: response.completed\ndata: " + json.dumps({"type": "response.completed", "response": {
                "model": reported, "status": "completed", "usage": {"input_tokens": 31, "output_tokens": 8}}}) + "\n\n")
        elif path == "/v1/chat/completions":
            write(": OPENROUTER PROCESSING\n\n")
            if behavior == "keepalive":
                pause_keepalive(": OPENROUTER PROCESSING\n\n")
            if behavior == "error_event":
                write("data: " + json.dumps({"error": {"code": 502, "message": "x"}}) + "\n\n")
                return
            for part in parts:
                write("data: " + json.dumps({"model": reported, "choices": [{"delta": {"content": part}}]}) + "\n\n")
            if behavior == "truncated":
                return
            finish = "length" if behavior == "max_tokens" else "stop"
            write("data: " + json.dumps({"model": reported, "choices": [{"delta": {}, "finish_reason": finish}]}) + "\n\n")
            write("data: " + json.dumps({"model": reported, "choices": [], "usage": {"prompt_tokens": 33, "completion_tokens": 7}}) + "\n\n")
            write("data: [DONE]\n\n")

    def of(self, path: str) -> list[dict]:
        with self._lock:
            return [r for r in self.requests if r["path"] == path]


# ---------------------------------------------------------------------------------------- fake stand


class HostStand(S.FakeRunner):
    """The runner API of RUNNER_API.md with the host operations: ``POST /runner/enroll`` (a host document),
    ``POST /runner/health`` (answered with the current catalogue and the host's switch) and the task operations of
    the base class.  ``catalogue`` and ``enabled`` can be changed while the agent runs."""

    def __init__(self, catalogue: Optional[list] = None, lease: int = 3) -> None:
        super().__init__(S.TOKEN, lease)
        self.catalogue = list(CATALOGUE if catalogue is None else catalogue)
        self.enabled = True
        self.send_catalogue = True
        self.enrollments = 0

    @staticmethod
    def _classify(path: str) -> tuple[str, Optional[str]]:
        if path == "/api/v1/runner/health":
            return "health", None
        if path == "/api/v1/runner/enroll":
            return "enroll", None
        return S.FakeRunner._classify(path)

    def _decide(self, kind: str, record: dict) -> Any:
        if kind == "enroll":
            if record["authorization"] != "Bearer " + HOST_SECRET:
                return S.Reply(401, S.envelope("authentication_required", "A valid credential is required."))
            self.enrollments += 1
            token = f"amr_enr{self.enrollments:02d}_".ljust(56, "x")
            return S.Reply(201, {"token": token, "runner_token": {"token_id": "ert_1"},
                                 "host_id": HOST_ID, "catalogue": self.catalogue})
        if kind == "health":
            if self.revoked or record["authorization"] != "Bearer " + self.token:
                return S.Reply(401, S.envelope("authentication_required", "A valid runner token is required."))
            document: dict = {"recorded_at": S.stamp(time.time()), "enabled": self.enabled}
            if self.send_catalogue:
                document["catalogue"] = self.catalogue
            return S.Reply(200, document)
        return super()._decide(kind, record)

    def health_reports(self) -> list[dict]:
        return [r["body"] for r in self.of_kind("health")]

    def wait_report(self, predicate: Any, timeout: float = 20.0, fresh: bool = False) -> dict:
        """The first health report for which ``predicate`` is true; with ``fresh`` only the reports that arrive after
        this call (for a state the host was in before and has just returned to)."""
        end = time.monotonic() + timeout
        seen = len(self.health_reports()) if fresh else 0
        while time.monotonic() < end:
            reports = self.health_reports()
            for report in reports[seen:]:
                if predicate(report):
                    return report
            seen = len(reports)
            time.sleep(0.05)
        raise AssertionError(f"no health report matched; the last was {json.dumps(self.health_reports()[-1:] or None)[:600]}")

    def host_task(self, task_id: str, provider: str, model_id: str, *, access: str = "subscription", effort: str = "medium",
                  timeout_seconds: int = 20, window: int = 60, lease: int = 3, **overrides: Any) -> dict:
        task = S.make_task(task_id, model_id, lease=lease, window=window, output_schema=TASK_SCHEMA)
        task.update({"provider": provider, "access": access, "model_id": model_id, "effort": effort,
                     "max_output_tokens": 4000, "timeout_seconds": timeout_seconds, "cell_key": "text:main"})
        task.update(overrides)
        return task


def provider_entry(report: dict, provider: str) -> Optional[dict]:
    return next((p for p in report.get("providers", []) if p["provider"] == provider), None)


def model_state(report: dict, provider: str, model_id: str) -> Optional[str]:
    entry = provider_entry(report, provider)
    if entry is None:
        return None
    return next((m["state"] for m in entry["models"] if m["model_id"] == model_id), None)


def eventually(predicate: Any, timeout: float = 15.0, interval: float = 0.03) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(interval)
    return bool(predicate())
