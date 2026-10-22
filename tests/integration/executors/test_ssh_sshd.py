"""The SSH transport against a real ``sshd`` in a container (`EXEC-SSH-01`).

Skipped unless ``EXEC_SSHD_PORT`` is set. Start the fixture first::

    eval "$(tests/fixtures/sshd/up.sh)"
    python3 -m pytest -q -p no:cacheprovider tests/integration/executors/test_ssh_sshd.py
    tests/fixtures/sshd/down.sh

The server accepts one key, with ``restrict,port-forwarding,permitopen="127.0.0.1:8080",command=...``;
its forced command echoes stdin as JSON and can sleep, fail, flood stdout or answer like
``claude -p``; a stub HTTP model listens on 127.0.0.1:8080 inside the container. See
``tests/fixtures/sshd/README.md``. The host-key rotation test needs the ``docker`` CLI and runs last.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from auditmanager.executors import ssh_transport as transport
from auditmanager.executors.claude_output import parse_claude_output
from auditmanager.executors.ssh_transport import (
    SshEndpoint,
    SshFailure,
    host_key_fingerprint,
    open_tunnel,
    run_command,
    scan_host_key,
)

PORT = os.environ.get("EXEC_SSHD_PORT")

pytestmark = pytest.mark.skipif(not PORT, reason="set EXEC_SSHD_PORT (tests/fixtures/sshd/up.sh starts the container)")


@pytest.fixture(scope="module")
def state_dir() -> Path:
    state = os.environ.get("EXEC_SSHD_STATE")
    if not state or not (Path(state) / "client_key").is_file() or not (Path(state) / "refused_key").is_file():
        pytest.fail("EXEC_SSHD_PORT is set but EXEC_SSHD_STATE does not hold client_key and refused_key")
    return Path(state)


@pytest.fixture
def endpoint() -> SshEndpoint:
    return SshEndpoint(os.environ.get("EXEC_SSHD_HOST", "127.0.0.1"), int(PORT), "runner")


@pytest.fixture
def client_key(state_dir: Path) -> str:
    return (state_dir / "client_key").read_text()


@pytest.fixture
def refused_key(state_dir: Path) -> str:
    return (state_dir / "refused_key").read_text()


@pytest.fixture
def pin(endpoint: SshEndpoint) -> str:
    """The probe's job: read the host key once and keep it. Calls then use only the pin."""
    return scan_host_key(endpoint, timeout=10)


def ask(endpoint, key, pin, task: dict, *, timeout_s: float = 20, max_output: int = 1_000_000):
    return run_command(endpoint, key, pin, json.dumps(task).encode(), timeout_s, max_output)


def key_files() -> set[str]:
    return {path.name for path in transport.TMPFS_DIR.glob("am-ssh-*")} if transport.TMPFS_DIR.is_dir() else set()


# --------------------------------------------------------------------------------------------
# The probe
# --------------------------------------------------------------------------------------------


def test_scan_reads_an_ed25519_host_key_and_shows_its_fingerprint(pin: str) -> None:
    key_type, blob = pin.split(" ")
    assert key_type == "ssh-ed25519"
    assert host_key_fingerprint(pin).startswith("SHA256:")


# --------------------------------------------------------------------------------------------
# ssh_command
# --------------------------------------------------------------------------------------------


def test_the_task_goes_to_stdin_and_the_answer_comes_back_on_stdout(endpoint, client_key, pin) -> None:
    task = {"model": "claude-sonnet-5", "user_text": "grüße 中文 " * 2000}
    before = key_files()
    stdout, stderr = ask(endpoint, client_key, pin, task)
    answer = json.loads(stdout)
    assert answer["ok"] is True
    assert answer["echo"] == task
    # The client named no command, and the forced command ran regardless.
    assert answer["ssh_original_command"] == ""
    assert stderr == ""
    assert key_files() == before  # the tmpfs key is gone after the call


def test_a_key_the_server_does_not_know_is_credential_refused_and_not_sent(endpoint, refused_key, pin) -> None:
    with pytest.raises(SshFailure) as raised:
        ask(endpoint, refused_key, pin, {"x": 1})
    assert raised.value.outcome == "credential_refused"
    assert raised.value.sent is False


def test_a_wrong_pin_is_a_changed_host_key(endpoint, client_key, tmp_path) -> None:
    # Pin the key of a host that is not this server: the real client refuses it as "changed".
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(tmp_path / "other")], check=True)
    other = " ".join((tmp_path / "other.pub").read_text().split()[:2])
    with pytest.raises(SshFailure) as raised:
        ask(endpoint, client_key, other, {"x": 1})
    assert raised.value.outcome == "host_key_changed"
    assert raised.value.sent is False


def test_no_pin_is_refused_without_connecting(endpoint, client_key) -> None:
    with pytest.raises(SshFailure) as raised:
        ask(endpoint, client_key, None, {"x": 1})
    assert raised.value.outcome == "host_key_unpinned"
    assert raised.value.sent is False


def test_a_command_that_outlives_its_timeout_is_outcome_unknown(endpoint, client_key, pin) -> None:
    started = time.monotonic()
    with pytest.raises(SshFailure) as raised:
        ask(endpoint, client_key, pin, {"sleep_s": 30}, timeout_s=3)
    assert time.monotonic() - started < 15
    assert raised.value.outcome == "timeout"
    assert raised.value.sent is True


def test_a_failing_remote_command_reports_its_exit_status_and_scrubbed_stderr(endpoint, client_key, pin) -> None:
    task = {"exit_status": 7, "stderr_text": "boom\n-----BEGIN OPENSSH PRIVATE KEY-----\nleaked line"}
    with pytest.raises(SshFailure) as raised:
        ask(endpoint, client_key, pin, task)
    assert raised.value.outcome == "protocol_error"
    assert raised.value.sent is True
    assert raised.value.exit_status == 7
    assert "boom" in raised.value.detail
    assert "PRIVATE KEY" not in raised.value.detail


def test_remote_stderr_is_bounded_and_scrubbed_on_success_too(endpoint, client_key, pin) -> None:
    task = {"stderr_text": "-----BEGIN OPENSSH PRIVATE KEY-----\n" + "e" * 5000}
    _, stderr = ask(endpoint, client_key, pin, task)
    assert "PRIVATE KEY" not in stderr
    assert len(stderr) <= 500


def test_output_over_the_bound_is_cut_off(endpoint, client_key, pin) -> None:
    with pytest.raises(SshFailure) as raised:
        ask(endpoint, client_key, pin, {"stdout_bytes": 200_000}, max_output=1_000)
    assert raised.value.outcome == "protocol_error"
    assert raised.value.sent is True


def test_the_private_key_never_appears_in_an_answer_an_error_or_a_leftover_file(endpoint, client_key, pin) -> None:
    body_lines = [line for line in client_key.splitlines() if "KEY" not in line and len(line) > 20]
    assert body_lines
    before = key_files()
    stdout, stderr = ask(endpoint, client_key, pin, {"stderr_text": "hello"})
    with pytest.raises(SshFailure) as raised:
        ask(endpoint, client_key, pin, {"exit_status": 3, "stderr_text": "failing"})
    shown = stdout.decode() + stderr + str(raised.value) + raised.value.detail
    assert all(line not in shown for line in body_lines)
    assert key_files() == before


def test_a_stub_claude_with_the_right_model_parses_and_the_wrong_one_is_visible(endpoint, client_key, pin) -> None:
    stdout, _ = ask(endpoint, client_key, pin, {"claude_model": "claude-sonnet-5"})
    assert parse_claude_output(stdout) == ("stub answer", "claude-sonnet-5")
    stdout, _ = ask(endpoint, client_key, pin, {"claude_model": "claude-opus-5"})
    assert parse_claude_output(stdout).reported_model == "claude-opus-5"  # the caller compares with its pin


# --------------------------------------------------------------------------------------------
# ssh_tunnel
# --------------------------------------------------------------------------------------------


def fetch(port: int, path: str = "/ok.json") -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as response:
        return json.loads(response.read())


def port_is_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def test_a_tunnel_reaches_the_stub_http_model_and_closes_afterwards(endpoint, client_key, pin) -> None:
    before = key_files()
    with open_tunnel(endpoint, client_key, pin, "127.0.0.1", 8080, timeout_s=20) as port:
        assert fetch(port) == {"model": "stub-model", "ok": True}
    assert not port_is_open(port)
    assert key_files() == before


def test_the_key_only_opens_the_forward_its_authorized_keys_line_permits(endpoint, client_key, pin) -> None:
    with open_tunnel(endpoint, client_key, pin, "127.0.0.1", 9, timeout_s=20) as port:
        with pytest.raises((urllib.error.URLError, ConnectionError, OSError)):
            fetch(port)  # permitopen: the server closes the channel


def test_a_tunnel_with_a_refused_key_is_credential_refused(endpoint, refused_key, pin) -> None:
    with pytest.raises(SshFailure) as raised:
        with open_tunnel(endpoint, refused_key, pin, "127.0.0.1", 8080, timeout_s=20):
            pytest.fail("the tunnel must not open")
    assert raised.value.outcome == "credential_refused"
    assert raised.value.sent is False


# --------------------------------------------------------------------------------------------
# A changed host key (last: it changes the container)
# --------------------------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("docker") is None, reason="rotating the host key needs the docker CLI")
def test_a_rotated_host_key_is_refused_until_the_new_one_is_pinned(endpoint, client_key, pin) -> None:
    container = os.environ.get("EXEC_SSHD_CONTAINER", "exec-ssh-sshd")
    ask(endpoint, client_key, pin, {"x": 1})  # the pin works
    subprocess.run(["docker", "exec", container, "rotate-host-key"], check=True, capture_output=True, timeout=60)
    with pytest.raises(SshFailure) as raised:
        ask(endpoint, client_key, pin, {"x": 1})
    assert (raised.value.outcome, raised.value.sent) == ("host_key_changed", False)
    with pytest.raises(SshFailure) as raised:
        with open_tunnel(endpoint, client_key, pin, "127.0.0.1", 8080, timeout_s=20):
            pytest.fail("the tunnel must not open")
    assert (raised.value.outcome, raised.value.sent) == ("host_key_changed", False)
    new_pin = scan_host_key(endpoint, timeout=10)
    assert new_pin != pin
    stdout, _ = ask(endpoint, client_key, new_pin, {"x": 2})
    assert json.loads(stdout)["echo"] == {"x": 2}
