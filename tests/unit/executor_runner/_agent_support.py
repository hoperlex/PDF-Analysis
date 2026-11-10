"""Fixtures shared by the `EXEC2-AGENT-01` tests (``test_agent_install``, ``test_agent_package``,
``test_agent_detect``, ``test_agent_health``): a stand that speaks the 1.15.0 enrollment, health and claim
operations, stand-ins for the ``codex`` and ``claude`` CLIs, and a small checker of a JSON document against a
schema of ``contracts/api/v1/openapi.json``. Standard library only.

Every server started here is a child of the test and is stopped through its own handle.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional

REPO = Path(__file__).resolve().parents[3]
RUNNER_DIR = REPO / "tools" / "executor-runner"
OPENAPI = REPO / "contracts" / "api" / "v1" / "openapi.json"

#: The shapes the stand mints and checks (ENROLL-01): ``ame_`` + 8 + ``_`` + 43, and a 56-character runner token.
SECRET = "ame_k3j9x2mq_" + ("Zx9" * 15)[:43]
OTHER_SECRET = "ame_p0o9i8u7_" + ("Qw3" * 15)[:43]
WORKING_TOKEN = "amr_" + hashlib.sha256(b"a working token").hexdigest()[:52]


def load_module(name: str, path: Path) -> Any:
    """A module from a path, registered under ``name`` (dataclasses resolve their annotations through it)."""
    sys.path.insert(0, str(RUNNER_DIR))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(RUNNER_DIR))


def envelope(code: str, message: str) -> dict:
    return {"contract_version": "1.50.0", "error_code": code, "message": message, "correlation_id": "corr-1",
            "retryable": False}


class Stand:
    """The runner side of the stand: ``POST /runner/enroll``, ``POST /runner/health`` and a claim that finds
    nothing. Behaviour follows the integrator's note on EXEC2-ENROLL-01: the enrollment secret is the bearer of
    the exchange; a repeat from the same ``runner_instance_id`` inside the window revokes the token minted before
    and returns a fresh one; another instance, or any repeat after the window, is 409.
    """

    def __init__(self, *, secret: str = SECRET, tokens: tuple[str, ...] = (WORKING_TOKEN,)) -> None:
        self.secret = secret
        self.valid_tokens = set(tokens)
        self.revoked_tokens: set[str] = set()
        self.requests: list[dict] = []
        self.window_open = True
        self.minted: list[str] = []
        self._instance: Optional[str] = None
        self._scripted: dict[str, list[tuple[int, Any]]] = {}
        self._lock = threading.Lock()
        stand = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                return

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw) if raw else None
                except ValueError:
                    body = {"_unparsable": True}
                record = {"path": self.path, "body": body, "authorization": self.headers.get("Authorization"),
                          "content_type": self.headers.get("Content-Type")}
                with stand._lock:
                    stand.requests.append(record)
                status, document = stand._decide(record)
                payload = b"" if document is None else json.dumps(document).encode("utf-8")
                self.send_response(status)
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

    def __enter__(self) -> "Stand":
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    # -- scripting and reading
    def script(self, operation: str, *replies: tuple[int, Any]) -> None:
        """The next answers of ``enroll``, ``health`` or ``claim``, used before the default behaviour."""
        with self._lock:
            self._scripted.setdefault(operation, []).extend(replies)

    def of(self, operation: str) -> list[dict]:
        suffix = {"enroll": "/api/v1/runner/enroll", "health": "/api/v1/runner/health",
                  "claim": "/api/v1/runner/tasks/claim"}[operation]
        with self._lock:
            return [r for r in self.requests if r["path"] == suffix]

    def wait_for(self, operation: str, count: int = 1, timeout: float = 15.0) -> list[dict]:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            found = self.of(operation)
            if len(found) >= count:
                return found
            time.sleep(0.02)
        raise AssertionError(f"timed out waiting for {count} x {operation}; saw {[r['path'] for r in self.requests]}")

    # -- behaviour
    def _mint(self) -> str:
        token = "amr_" + hashlib.sha256(f"minted {len(self.minted)}".encode()).hexdigest()[:52]
        self.minted.append(token)
        self.valid_tokens.add(token)
        return token

    def _bearer(self, record: dict) -> str:
        header = record["authorization"] or ""
        return header[len("Bearer "):] if header.startswith("Bearer ") else ""

    def _decide(self, record: dict) -> tuple[int, Any]:
        path = record["path"]
        operation = {"/api/v1/runner/enroll": "enroll", "/api/v1/runner/health": "health",
                     "/api/v1/runner/tasks/claim": "claim"}.get(path)
        if operation is None:
            return 404, envelope("not_found", "No such operation.")
        with self._lock:
            queue = self._scripted.get(operation)
            if queue:
                return queue.pop(0)
        bearer = self._bearer(record)
        if operation == "enroll":
            if bearer != self.secret:
                return 401, envelope("authentication_required", "A valid credential is required.")
            instance = (record["body"] or {}).get("runner_instance_id")
            with self._lock:
                if not self.window_open or (self._instance is not None and instance != self._instance):
                    return 409, envelope("conflict", "enrollment_redeemed")
                if self.minted:  # the idempotent repeat: the token minted before is revoked, a fresh one returned
                    old = self.minted[-1]
                    self.valid_tokens.discard(old)
                    self.revoked_tokens.add(old)
                self._instance = instance
                token = self._mint()
            return 201, {"token": token, "runner_token": {"token_id": "ert_0001", "token_prefix": token[:12]}}
        if bearer not in self.valid_tokens:
            return 401, envelope("authentication_required", "A valid runner token is required.")
        if operation == "health":
            return 200, {"recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        time.sleep(min(float((record["body"] or {}).get("wait_seconds", 0)), 0.5))
        return 204, None


# ------------------------------------------------------------------------------------ CLI stand-ins

# The stand-ins run with the PATH the agent gives a client: only the directories it searched. So they use
# nothing but shell built-ins -- ``${0%/*}`` is the directory, where ``dirname`` is a program that PATH does not
# hold and whose absence made the log land in ``/calls.log`` at the filesystem root.
_CODEX = """#!/bin/sh
echo "$@" >> "${{0%/*}}/calls.log"
case "$1" in
  --version) echo "codex-cli {version}"; exit 0 ;;
  login)
    if [ "$2" = status ]; then
      if [ -f "$HOME/.codex/auth.json" ]; then echo "Logged in using ChatGPT"; exit 0; fi
      echo "Not logged in"; exit 1
    fi ;;
esac
exit 2
"""

_CLAUDE = """#!/bin/sh
echo "$@" >> "${{0%/*}}/calls.log"
case "$1" in
  --version) echo "{version} (Claude Code)"; exit 0 ;;
  auth)
    if [ "$2" = status ]; then
      echo '{{"loggedIn": true, "email": "someone@example.com", "authMethod": "claude.ai"}}'
      if [ -f "$HOME/.claude/.credentials.json" ]; then exit 0; fi
      exit 1
    fi ;;
esac
exit 2
"""


def make_cli(directory: Path, name: str, version: str) -> Path:
    """A stand-in ``codex`` or ``claude`` in ``directory``. It logs every call to ``calls.log`` beside itself and
    reports itself logged in exactly when ``$HOME`` holds the file a real login would leave there."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text((_CODEX if name == "codex" else _CLAUDE).format(version=version))
    path.chmod(0o755)
    return path


def log_in(home: Path, name: str) -> None:
    marker = home / ".codex" / "auth.json" if name == "codex" else home / ".claude" / ".credentials.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("{}")


def calls(directory: Path) -> list[str]:
    log = directory / "calls.log"
    return log.read_text().splitlines() if log.exists() else []


# ----------------------------------------------------------------------------- the contract's schemas


def schema_errors(name: str, instance: Any) -> list[str]:
    """The ways ``instance`` violates the schema ``name`` of ``contracts/api/v1/openapi.json`` (empty when it
    conforms). Covers what these schemas use: ``$ref``, ``type``, ``enum``, ``pattern``, ``minLength``,
    ``maxLength``, ``minimum``, ``maximum``, ``items``, ``maxItems``, ``required``, ``properties`` and
    ``additionalProperties: false``."""
    document = json.loads(OPENAPI.read_text())
    errors: list[str] = []

    def resolve(schema: dict) -> dict:
        while "$ref" in schema:
            schema = document["components"]["schemas"][schema["$ref"].rsplit("/", 1)[1]]
        return schema

    def check(schema: dict, value: Any, where: str) -> None:
        schema = resolve(schema)
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{where}: {value!r} is not one of {schema['enum']}")
        kind = schema.get("type")
        if kind == "string":
            if not isinstance(value, str):
                errors.append(f"{where}: not a string")
                return
            if "pattern" in schema and re.search(schema["pattern"], value) is None:
                errors.append(f"{where}: {value!r} does not match {schema['pattern']}")
            if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", 1 << 30):
                errors.append(f"{where}: length {len(value)} is out of range")
        elif kind == "integer":
            if type(value) is not int:
                errors.append(f"{where}: not an integer")
            elif not schema.get("minimum", value) <= value <= schema.get("maximum", value):
                errors.append(f"{where}: {value} is out of range")
        elif kind == "boolean":
            if type(value) is not bool:
                errors.append(f"{where}: not a boolean")
        elif kind == "array":
            if not isinstance(value, list):
                errors.append(f"{where}: not an array")
                return
            if len(value) > schema.get("maxItems", 1 << 30):
                errors.append(f"{where}: more than {schema['maxItems']} items")
            for index, item in enumerate(value):
                check(schema["items"], item, f"{where}[{index}]")
        elif kind == "object":
            if not isinstance(value, dict):
                errors.append(f"{where}: not an object")
                return
            for required in schema.get("required", []):
                if required not in value:
                    errors.append(f"{where}: {required} is required")
            properties = schema.get("properties", {})
            for key, item in value.items():
                if key in properties:
                    check(properties[key], item, f"{where}.{key}")
                elif schema.get("additionalProperties") is False:
                    errors.append(f"{where}: {key} is not allowed")

    check({"$ref": f"#/components/schemas/{name}"}, instance, name)
    return errors
