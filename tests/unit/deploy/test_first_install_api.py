"""`first_install_api.py`: finishing the administrator's account and designating the norms snapshot, against a stand-in for
the stack's loopback API that follows `contracts/api/v1/openapi.json` (the published `admin` / `password` pair, the
`is_default_credential` flag, the `403 profile_completed` refusal, the compare-and-set of `setCurrentNormSnapshot`).

What is held:

* a fresh stack ends with the password changed, the profile complete, the login the owner's e-mail, and the password in a
  mode-600 file that holds it and **nothing else prints it**;
* every interrupted shape reruns to the same end: file written but nothing changed; password changed but the profile not;
  everything done;
* a password that is neither the published one nor the file's is a stop (exit 21), never a guess;
* the designation picks the qualified snapshot (or the one the bundle names), is a no-op when it is already current, and
  reports a stale belief and an absent snapshot with their own exit codes.

No docker, no real network: the server is a thread on 127.0.0.1.
"""

from __future__ import annotations

import importlib.util
import json
import re
import stat
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "infra" / "deploy" / "lib" / "first_install_api.py"


def _load():
    spec = importlib.util.spec_from_file_location("first_install_api_under_test", HELPER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fia = _load()
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


@pytest.fixture()
def stack():
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
    yield state
    server.shutdown()
    server.server_close()


def _client(stack: Stack) -> "fia.Client":
    return fia.Client(stack.base, timeout=5, sleep=lambda _seconds: None)


def _run_admin(stack: Stack, password_file: Path, email: str = "owner@example.org") -> tuple[int, list[str]]:
    lines: list[str] = []
    return fia.admin(_client(stack), password_file, email, lines.append), lines


def _password_in(path: Path) -> str:
    return fia.read_credentials(path)[1]


def test_a_fresh_stack_gets_a_new_password_a_complete_profile_and_the_owners_login(stack: Stack, tmp_path: Path) -> None:
    password_file = tmp_path / "admin.txt"
    status, lines = _run_admin(stack, password_file)
    assert status == 0, lines
    assert stack.password != "password" and stack.profile_complete and stack.login == "owner@example.org"
    assert fia.read_credentials(password_file) == ("owner@example.org", stack.password)
    assert stat.S_IMODE(password_file.stat().st_mode) == 0o600
    assert len(stack.password) >= 32
    assert all(stack.password not in line for line in lines)


def test_the_published_pair_no_longer_signs_in_afterwards(stack: Stack, tmp_path: Path) -> None:
    _run_admin(stack, tmp_path / "admin.txt")
    assert _client(stack).sign_in("admin", "password") is None


def test_a_rerun_after_success_changes_nothing(stack: Stack, tmp_path: Path) -> None:
    password_file = tmp_path / "admin.txt"
    _run_admin(stack, password_file)
    before = (password_file.read_bytes(), stack.password, stack.login, stack.counter)
    status, lines = _run_admin(stack, password_file)
    assert status == 0, lines
    assert (password_file.read_bytes(), stack.password, stack.login) == before[:3]


def test_a_run_that_died_after_writing_the_file_reuses_that_password(stack: Stack, tmp_path: Path) -> None:
    password_file = tmp_path / "admin.txt"
    fia.ensure_credentials(password_file, lambda: "pre-written-password-0123456789abcdef")
    status, _ = _run_admin(stack, password_file)
    assert status == 0
    assert stack.password == "pre-written-password-0123456789abcdef"


def test_a_run_that_died_after_the_change_completes_the_profile(stack: Stack, tmp_path: Path) -> None:
    password_file = tmp_path / "admin.txt"
    fia.ensure_credentials(password_file, lambda: "changed-but-not-profiled-0123456789")
    stack.password = "changed-but-not-profiled-0123456789"
    status, lines = _run_admin(stack, password_file)
    assert status == 0, lines
    assert stack.profile_complete and stack.login == "owner@example.org"
    assert fia.read_credentials(password_file)[0] == "owner@example.org"


def test_a_foreign_password_is_a_stop_and_changes_nothing(stack: Stack, tmp_path: Path) -> None:
    stack.password = "somebody-elses-password-0123456789"
    password_file = tmp_path / "admin.txt"
    status, lines = _run_admin(stack, password_file)
    assert status == 21
    assert stack.password == "somebody-elses-password-0123456789" and not stack.profile_complete
    assert all("somebody-elses" not in line for line in lines)


def test_a_taken_email_is_reported_with_its_reason(stack: Stack, tmp_path: Path) -> None:
    stack.profile_conflict = True
    status, lines = _run_admin(stack, tmp_path / "admin.txt")
    assert status == 22
    assert any("conflict" in line and "login_taken" in line for line in lines), lines


def test_the_edge_rate_limit_is_waited_out(stack: Stack, tmp_path: Path) -> None:
    stack.rate_limit_next = 2
    status, lines = _run_admin(stack, tmp_path / "admin.txt")
    assert status == 0, lines


def test_a_rate_limit_that_does_not_lift_is_its_own_exit(stack: Stack, tmp_path: Path) -> None:
    stack.rate_limit_next = 99
    status, _ = _run_admin(stack, tmp_path / "admin.txt")
    assert status == 23


def test_a_stack_that_does_not_answer_is_exit_20(tmp_path: Path) -> None:
    client = fia.Client("http://127.0.0.1:9/api/v1", timeout=1, sleep=lambda _seconds: None)
    lines: list[str] = []
    assert fia.admin(client, tmp_path / "admin.txt", "owner@example.org", lines.append) == 20


def test_no_output_carries_the_password_and_the_body_never_reaches_a_line(stack: Stack, tmp_path: Path, capsys) -> None:
    password_file = tmp_path / "admin.txt"
    status = fia.main(["admin", "--base", stack.base, "--password-file", str(password_file), "--email", "owner@example.org"])
    assert status == 0
    captured = capsys.readouterr()
    assert stack.password not in captured.out + captured.err


def test_designation_picks_the_qualified_snapshot_and_a_second_call_is_a_no_op(stack: Stack, tmp_path: Path) -> None:
    password_file = tmp_path / "admin.txt"
    _run_admin(stack, password_file)
    lines: list[str] = []
    assert fia.designate(_client(stack), password_file, CONTENT_KEY, lines.append) == 0, lines
    assert stack.snapshots[0]["current"] is True
    lines.clear()
    assert fia.designate(_client(stack), password_file, None, lines.append) == 0
    assert "already the current" in lines[0]


def test_designation_before_the_profile_is_complete_is_refused_with_the_capability(stack: Stack, tmp_path: Path) -> None:
    password_file = tmp_path / "admin.txt"
    fia.ensure_credentials(password_file, lambda: "changed-but-not-profiled-0123456789")
    stack.password = "changed-but-not-profiled-0123456789"
    lines: list[str] = []
    assert fia.designate(_client(stack), password_file, None, lines.append) == 22
    assert any("profile_completed" in line for line in lines)


def test_designation_with_no_matching_snapshot_is_exit_30(stack: Stack, tmp_path: Path) -> None:
    password_file = tmp_path / "admin.txt"
    _run_admin(stack, password_file)
    lines: list[str] = []
    assert fia.designate(_client(stack), password_file, "undated+1d.000000000000", lines.append) == 30
    stack.snapshots[0]["qualified"] = False
    stack.snapshots[0]["build_state"] = "running"
    assert fia.designate(_client(stack), password_file, None, lines.append) == 30


def test_two_qualified_snapshots_without_a_named_key_are_ambiguous(stack: Stack, tmp_path: Path) -> None:
    password_file = tmp_path / "admin.txt"
    _run_admin(stack, password_file)
    stack.snapshots.append(dict(stack.snapshots[0], norms_snapshot_id=OTHER, content_key="other+1d.111111111111"))
    assert fia.designate(_client(stack), password_file, None, [].append) == 31
    assert fia.designate(_client(stack), password_file, CONTENT_KEY, [].append) == 0


def test_designation_expects_the_snapshot_that_is_current_and_reports_a_race(stack: Stack, tmp_path: Path) -> None:
    password_file = tmp_path / "admin.txt"
    _run_admin(stack, password_file)
    stack.snapshots.append(dict(stack.snapshots[0], norms_snapshot_id=OTHER, content_key="other+1d.111111111111",
                                current=True))
    stack.snapshots[0]["current"] = False
    lines: list[str] = []
    # The belief the helper sends is the live current snapshot, so a change of hands is a compare-and-set success;
    # a stale belief is reported with its own exit.
    assert fia.designate(_client(stack), password_file, CONTENT_KEY, lines.append) == 0, lines
    assert [s["current"] for s in stack.snapshots] == [True, False]

    class Racing(fia.Client):
        def request(self, method, path, body=None, token=None):
            if method == "PUT":
                for snapshot in stack.snapshots:
                    snapshot["current"] = snapshot["norms_snapshot_id"] == OTHER
            return super().request(method, path, body, token)

    stack.snapshots[0]["current"] = False
    stack.snapshots[1]["current"] = False
    assert fia.designate(Racing(stack.base, timeout=5, sleep=lambda _s: None), password_file, CONTENT_KEY, [].append) == 32


def test_wait_returns_when_the_stack_answers_401(stack: Stack) -> None:
    assert fia.wait_for_stack(_client(stack), 5) is True
    dead = fia.Client("http://127.0.0.1:9/api/v1", timeout=1, sleep=lambda _seconds: None)
    assert fia.wait_for_stack(dead, 0) is False


def test_the_password_file_is_exclusive_and_private(tmp_path: Path) -> None:
    path = tmp_path / "admin.txt"
    first = fia.ensure_credentials(path, fia.generate_password)
    second = fia.ensure_credentials(path, lambda: "never-used-0123456789abcdefghij")
    assert first == second
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", first[1])
