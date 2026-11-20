"""A stand-in for the stack's loopback API, for the first-install tests.

It follows `contracts/api/v1/openapi.json` for the slice the installer uses: the published `admin` / `password` pair and the
`is_default_credential` flag, `changePassword` (which revokes every credential), `getMe` / `updateMyProfile` (the e-mail becomes
the login), the `403 profile_completed` refusal on the norms operations, and the compare-and-set of `setCurrentNormSnapshot`.
`GET /openapi.json` answers 401, as the real proxy does for a credential-less caller.

Loaded by path from the test modules (the suite runs with `--import-mode=importlib`).
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"
OTHER = "ns_01M59N8QNBVN91ACA2HCE6VE75"
CONTENT_KEY = "2026-07-23..2026-08-20+17d+121r.0a1bafe103ff"


class Stack:
    """The slice of the API the helper uses, as one account's state."""

    def __init__(self) -> None:
        self.login = "admin"
        self.password = "password"
        self.profile_complete = False
        self.tokens: dict[str, str] = {}
        self.counter = 0
        self.rate_limit_next = 0
        self.seen_bodies: list[str] = []
        self.snapshots = [{
            "norms_snapshot_id": SNAPSHOT, "content_key": CONTENT_KEY, "document_count": 674, "paragraph_count": 350194,
            "unreliable_count": 0, "build_state": "complete", "qualified": True, "current": False,
            "created_at": "2026-10-21T10:00:00Z"}]
        self.profile_conflict = False

    def mint(self) -> str:
        self.counter += 1
        token = f"tok-{self.counter}"
        self.tokens[token] = self.login
        return token

    def revoke_all(self) -> None:
        self.tokens.clear()


def serve():
    """Start the stand-in on 127.0.0.1 (a free port) and return (state, stop)."""
    state = Stack()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # noqa: D401 - silence
            return

        def _send(self, status: int, body=None, code: str | None = None, details=None) -> None:
            if code:
                body = {"contract_version": "1.0.0", "error_code": code, "message": f"{code} message",
                        "correlation_id": "c" * 8, "retryable": False, "details": details or {}}
            payload = json.dumps(body).encode() if body is not None else b""
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode() if length else ""
            state.seen_bodies.append(raw)
            return json.loads(raw) if raw else {}

        def _subject(self):
            header = self.headers.get("Authorization", "")
            return state.tokens.get(header.removeprefix("Bearer ").strip()) if header.startswith("Bearer ") else None

        def _account(self):
            return {"user_uid": "usr_x", "login": state.login, "display_label": "x", "last_name": None, "first_name": None,
                    "middle_name": None, "roles": ["admin"], "profile_complete": state.profile_complete,
                    "is_default_credential": state.password == "password", "archived_at": None, "last_sign_in_at": None}

        def do_GET(self):  # noqa: N802
            path = self.path.split("?")[0]
            if path == "/api/v1/openapi.json":
                return self._send(401, code="authentication_required")
            if self._subject() is None:
                return self._send(401, code="authentication_required")
            if path == "/api/v1/me":
                return self._send(200, self._account())
            if path == "/api/v1/norms/snapshots":
                if not state.profile_complete:
                    return self._send(403, code="permission_denied", details={"required_capability": "profile_completed"})
                return self._send(200, {"items": state.snapshots, "page": {"next_cursor": None}})
            return self._send(404, code="not_found")

        def do_POST(self):  # noqa: N802
            body = self._body()
            path = self.path
            if path == "/api/v1/auth/token":
                if state.rate_limit_next:
                    state.rate_limit_next -= 1
                    return self._send(429, code="rate_limited")
                if body.get("login") == state.login and body.get("password") == state.password:
                    return self._send(200, {"token": state.mint(), "expires_in": 3600,
                                            "is_default_credential": state.password == "password"})
                return self._send(401, code="authentication_required")
            if self._subject() is None:
                return self._send(401, code="authentication_required")
            if path == "/api/v1/auth/password":
                if body.get("current_password") != state.password:
                    return self._send(401, code="authentication_required")
                if len(body.get("new_password", "")) < 8 or body["new_password"].casefold() == "password":
                    return self._send(422, code="validation_failed")
                state.password = body["new_password"]
                state.revoke_all()
                return self._send(200, {"token": state.mint(), "expires_in": 3600, "is_default_credential": False})
            return self._send(404, code="not_found")

        def do_PATCH(self):  # noqa: N802
            body = self._body()
            if self._subject() is None:
                return self._send(401, code="authentication_required")
            if self.path == "/api/v1/me":
                if state.profile_conflict:
                    return self._send(409, code="conflict", details={"conflict_reason": "login_taken"})
                state.login = body["email"]
                state.profile_complete = True
                return self._send(200, self._account())
            return self._send(404, code="not_found")

        def do_PUT(self):  # noqa: N802
            body = self._body()
            if self._subject() is None:
                return self._send(401, code="authentication_required")
            if self.path == "/api/v1/norms/snapshots/current":
                current = next((s["norms_snapshot_id"] for s in state.snapshots if s["current"]), None)
                if body["expected_current"] != current:
                    return self._send(409, code="conflict", details={"conflict_reason": "stale_current_snapshot"})
                for snapshot in state.snapshots:
                    snapshot["current"] = snapshot["norms_snapshot_id"] == body["norms_snapshot_id"]
                return self._send(200, {"norms_snapshot_id": body["norms_snapshot_id"], "designated_at": "2026-11-20T00:00:00Z",
                                        "designated_by": "usr_x"})
            return self._send(404, code="not_found")

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    state.base = f"http://127.0.0.1:{server.server_address[1]}/api/v1"
    state.port = server.server_address[1]

    def stop() -> None:
        server.shutdown()
        server.server_close()

    return state, stop


