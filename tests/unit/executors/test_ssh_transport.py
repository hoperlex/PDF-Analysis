"""The SSH transport against a fake ``ssh`` on PATH (`EXEC-SSH-01`).

A small Python script named ``ssh`` (and one named ``ssh-keyscan``) is put first on PATH. It records
exactly what the transport handed it -- argv, the key file's mode *at call time*, the known-hosts
file, the environment, stdin -- and then behaves as configured: print, fail with an ssh-looking
message, sleep, flood stdout, or listen like a tunnel. No server, no network, no container.

Two small tests at the end use the real ``ssh`` / ``ssh-keygen`` binaries when they exist, for the
two facts a fake cannot prove: that the real client's own refusal text is classified, and that the
known-hosts line we write is one OpenSSH finds.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import textwrap
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from auditmanager.executors import ssh_transport as transport
from auditmanager.executors.ssh_transport import (
    HostKeyFormatError,
    SshEndpoint,
    SshFailure,
    build_ssh_argv,
    host_key_fingerprint,
    known_hosts_line,
    open_tunnel,
    private_key_file,
    run_command,
    scan_host_key,
    scrub_stderr,
    ssh_destination,
)

PEM = (
    "-----BEGIN OPENSSH PRIVATE KEY-----\n"
    "SENTINELBODYLINE0123456789abcdefSENTINEL\n"
    "SECONDLINEOFKEYMATERIAL9876543210zyxwvut\n"
    "-----END OPENSSH PRIVATE KEY-----\n"
)
SENTINELS = ("SENTINELBODYLINE0123456789abcdefSENTINEL", "SECONDLINEOFKEYMATERIAL9876543210zyxwvut")
ENDPOINT = SshEndpoint("remote.example.test", 2222, "runner")


def make_host_key(seed: bytes = b"a", key_type: str = "ssh-ed25519") -> str:
    name = key_type.encode()
    blob = struct.pack(">I", len(name)) + name + struct.pack(">I", 32) + hashlib.sha256(seed).digest()
    return f"{key_type} {base64.b64encode(blob).decode()}"


HOST_KEY = make_host_key()


# --------------------------------------------------------------------------------------------
# The fake ssh / ssh-keyscan
# --------------------------------------------------------------------------------------------

FAKE_SSH = textwrap.dedent(
    """\
    #!{python}
    import json, os, signal, socket, sys, time, hashlib

    here = os.path.dirname(os.path.abspath(__file__))
    config = json.load(open(os.path.join(here, "fake_ssh.json")))
    argv = sys.argv[1:]

    def option(name):
        for index, item in enumerate(argv):
            if item == "-o" and argv[index + 1].startswith(name + "="):
                return argv[index + 1].split("=", 1)[1]

    counter = os.path.join(here, "calls.count")
    n = (int(open(counter).read()) if os.path.exists(counter) else 0) + 1
    open(counter, "w").write(str(n))
    c = config["per_call"][n - 1] if "per_call" in config else config

    key = argv[argv.index("-i") + 1]
    known_hosts = option("UserKnownHostsFile")
    record = {{
        "n": n,
        "pid": os.getpid(),
        "argv": argv,
        "key_path": key,
        "key_mode": oct(os.stat(key).st_mode & 0o777),
        "key_dir_mode": oct(os.stat(os.path.dirname(key)).st_mode & 0o777),
        "key_text": open(key).read(),
        "known_hosts_path": known_hosts,
        "known_hosts": open(known_hosts).read(),
        "env": {{k: os.environ.get(k) for k in ("SSH_AUTH_SOCK", "LC_ALL", "LANG", "HOME", "PATH", "SECRET_IN_PARENT")}},
    }}
    tunnel = "-N" in argv
    stdin = b"" if tunnel else sys.stdin.buffer.read()
    record["stdin_sha256"] = hashlib.sha256(stdin).hexdigest()
    record["stdin_len"] = len(stdin)
    open(os.path.join(here, "stdin.%d.bin" % n), "wb").write(stdin)
    json.dump(record, open(os.path.join(here, "record.%d.json" % n), "w"))

    def say(text):
        sys.stderr.write(text)
        sys.stderr.flush()

    if c.get("stderr_key_file"):
        say(record["key_text"] + "\\nLoad key \\"" + key + "\\": error in libcrypto\\n")
    if c.get("stderr"):
        say(c["stderr"])

    if tunnel:
        if c.get("fail"):
            sys.exit(c.get("exit", 255))
        local_port = int(argv[argv.index("-L") + 1].split(":")[1])
        time.sleep(c.get("listen_delay", 0))
        if c.get("no_listen"):
            time.sleep(60)
            sys.exit(0)
        server = socket.socket()
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", local_port))
        server.listen(5)
        def on_term(signum, frame):
            open(os.path.join(here, "terminated"), "w").write(str(os.getpid()))
            os._exit(0)
        signal.signal(signal.SIGTERM, on_term)
        while True:
            conn, _ = server.accept()
            conn.close()

    if c.get("sleep"):
        time.sleep(c["sleep"])
    try:
        if c.get("stdout_size"):
            sys.stdout.buffer.write(b"y" * c["stdout_size"])
            sys.stdout.buffer.flush()
            if c.get("sleep_after"):
                time.sleep(c["sleep_after"])
        elif "stdout" in c:
            sys.stdout.buffer.write(c["stdout"].encode())
            sys.stdout.buffer.flush()
    except BrokenPipeError:
        pass
    sys.exit(c.get("exit", 0))
    """
)

FAKE_KEYSCAN = textwrap.dedent(
    """\
    #!{python}
    import json, os, sys
    here = os.path.dirname(os.path.abspath(__file__))
    json.dump(sys.argv[1:], open(os.path.join(here, "keyscan.argv.json"), "w"))
    config = json.load(open(os.path.join(here, "fake_keyscan.json")))
    sys.stdout.write(config.get("stdout", ""))
    sys.stderr.write(config.get("stderr", ""))
    sys.exit(config.get("exit", 0))
    """
)


class FakeSsh:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def configure(self, **config) -> None:
        (self.directory / "fake_ssh.json").write_text(json.dumps(config))

    def configure_keyscan(self, **config) -> None:
        (self.directory / "fake_keyscan.json").write_text(json.dumps(config))

    def calls(self) -> int:
        counter = self.directory / "calls.count"
        return int(counter.read_text()) if counter.exists() else 0

    def record(self, n: int = 1) -> dict:
        return json.loads((self.directory / f"record.{n}.json").read_text())

    def stdin(self, n: int = 1) -> bytes:
        return (self.directory / f"stdin.{n}.bin").read_bytes()


@pytest.fixture
def key_area(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A private stand-in for /dev/shm, so a test can see what the transport leaves behind."""
    area = tmp_path / "shm"
    area.mkdir()
    monkeypatch.setattr(transport, "TMPFS_DIR", area)
    return area


@pytest.fixture
def fake_ssh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key_area: Path) -> Iterator[FakeSsh]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("ssh", FAKE_SSH), ("ssh-keyscan", FAKE_KEYSCAN)):
        script = bin_dir / name
        script.write_text(body.format(python=sys.executable))
        script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/should-not-reach-ssh.sock")
    monkeypatch.setenv("SECRET_IN_PARENT", "parent-secret")
    fake = FakeSsh(bin_dir)
    fake.configure()
    yield fake
    # A failing test must not leave a fake tunnel listening: stop only the processes this test's
    # fake recorded (PID taken from its own record, command line checked against its own directory).
    for record_path in bin_dir.glob("record.*.json"):
        pid = json.loads(record_path.read_text())["pid"]
        try:
            command_line = Path(f"/proc/{pid}/cmdline").read_bytes()
        except OSError:
            continue
        if str(bin_dir).encode() in command_line:
            os.kill(pid, 9)


def left_behind(area: Path) -> list[str]:
    return sorted(path.name for path in area.iterdir())


def call(stdin: bytes = b'{"task":1}', *, timeout_s: float = 10, max_output: int = 1_000_000, host_key: str | None = HOST_KEY):
    return run_command(ENDPOINT, PEM, host_key, stdin, timeout_s, max_output)


# --------------------------------------------------------------------------------------------
# Endpoint, host keys, destination strings
# --------------------------------------------------------------------------------------------


def test_endpoint_accepts_ordinary_values_and_formats_the_address() -> None:
    assert SshEndpoint("10.0.0.5", 22, "runner").address == "10.0.0.5:22"
    assert SshEndpoint("gpu-box.lan", 2222, "svc_user").address == "gpu-box.lan:2222"
    assert SshEndpoint("::1", 2200, "u").address == "[::1]:2200"


@pytest.mark.parametrize(
    "host,port,user",
    [
        ("-oProxyCommand=evil", 22, "u"),
        ("", 22, "u"),
        ("host name", 22, "u"),
        ("*.example.test", 22, "u"),
        ("a,b", 22, "u"),
        ("host\nother", 22, "u"),
        ("not:ipv6", 22, "u"),
        ("host", 0, "u"),
        ("host", 65536, "u"),
        ("host", True, "u"),
        ("host", "22", "u"),
        ("host", 22, "-oProxyCommand=evil"),
        ("host", 22, ""),
        ("host", 22, "u@x"),
        ("host", 22, "a b"),
    ],
)
def test_endpoint_refuses_values_that_could_become_options_patterns_or_lines(host, port, user) -> None:
    with pytest.raises(ValueError):
        SshEndpoint(host, port, user)


def test_known_hosts_line_uses_the_bracketed_form_for_a_non_default_port() -> None:
    line = known_hosts_line(ENDPOINT, HOST_KEY)
    assert line == f"[remote.example.test]:2222 {HOST_KEY}"


def test_known_hosts_line_leaves_the_default_port_bare_because_openssh_files_it_that_way() -> None:
    line = known_hosts_line(SshEndpoint("remote.example.test", 22, "u"), HOST_KEY)
    assert line == f"remote.example.test {HOST_KEY}"


def test_known_hosts_line_accepts_scan_output_and_comments_and_normalises_them() -> None:
    expected = known_hosts_line(ENDPOINT, HOST_KEY)
    assert known_hosts_line(ENDPOINT, f"[other]:22 {HOST_KEY} some comment") == expected
    assert known_hosts_line(ENDPOINT, f"  {HOST_KEY}  ") == expected


@pytest.mark.parametrize(
    "line",
    [
        "",
        "   ",
        "ssh-ed25519",
        "ssh-ed25519 not*base64!",
        "nonsense AAAA",
        f"{HOST_KEY}\nssh-rsa AAAA",
        make_host_key(b"x").replace("ssh-ed25519", "ssh-rsa", 1),  # blob announces a different type
        "ssh-ed25519 AAAA",  # base64 but too short
    ],
)
def test_known_hosts_line_refuses_a_malformed_host_key(line: str) -> None:
    with pytest.raises(HostKeyFormatError):
        known_hosts_line(ENDPOINT, line)


def test_host_key_fingerprint_is_sha256_of_the_blob_in_ssh_keygens_form() -> None:
    blob = base64.b64decode(HOST_KEY.split()[1])
    expected = "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")
    assert host_key_fingerprint(HOST_KEY) == expected
    assert "=" not in host_key_fingerprint(HOST_KEY)


@pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="needs ssh-keygen")
def test_fingerprint_and_known_hosts_line_agree_with_the_real_openssh_tools(tmp_path: Path) -> None:
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(tmp_path / "hk")], check=True)
    public = (tmp_path / "hk.pub").read_text().split()
    key_line = " ".join(public[:2])
    shown = subprocess.run(["ssh-keygen", "-lf", str(tmp_path / "hk.pub")], capture_output=True, text=True, check=True)
    assert host_key_fingerprint(key_line) in shown.stdout
    for port, query in ((2222, "[remote.example.test]:2222"), (22, "remote.example.test")):
        known = tmp_path / f"known_hosts_{port}"
        known.write_text(known_hosts_line(SshEndpoint("remote.example.test", port, "u"), key_line) + "\n")
        found = subprocess.run(["ssh-keygen", "-F", query, "-f", str(known)], capture_output=True, text=True)
        assert found.returncode == 0, (port, found.stdout, found.stderr)


def test_destination_strings_are_exactly_the_plan_4_1_forms() -> None:
    assert ssh_destination("ssh_command", ENDPOINT) == "ssh_command|remote.example.test:2222|"
    assert (
        ssh_destination("ssh_tunnel", ENDPOINT, "http://localhost:11434")
        == "ssh_tunnel|remote.example.test:2222|http://localhost:11434"
    )
    # A changed SSH endpoint changes the destination even when the tunnelled origin stays the same.
    other = SshEndpoint("remote.example.test", 2223, "runner")
    assert ssh_destination("ssh_tunnel", other, "http://localhost:11434") != ssh_destination(
        "ssh_tunnel", ENDPOINT, "http://localhost:11434"
    )
    # The user is not part of the destination (plan 4.1 binds host:port).
    assert ssh_destination("ssh_command", SshEndpoint("remote.example.test", 2222, "someone-else")) == (
        "ssh_command|remote.example.test:2222|"
    )


@pytest.mark.parametrize(
    "transport_name,origin",
    [
        ("ssh_command", "http://x:1"),
        ("ssh_tunnel", ""),
        ("ssh_tunnel", "localhost:11434"),
        ("ssh_tunnel", "http://a|b:1"),
        ("direct", ""),
        ("vpn", "http://x:1"),
    ],
)
def test_destination_refuses_what_is_not_an_ssh_form(transport_name: str, origin: str) -> None:
    with pytest.raises(ValueError):
        ssh_destination(transport_name, ENDPOINT, origin)


# --------------------------------------------------------------------------------------------
# The key file
# --------------------------------------------------------------------------------------------


def test_private_key_file_is_0600_in_a_0700_directory_on_the_tmpfs_and_unlinked_on_exit(key_area: Path) -> None:
    with private_key_file(PEM) as path:
        assert path.parent.parent == key_area
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
        assert path.read_text() == PEM
    assert not path.exists()
    assert left_behind(key_area) == []


def test_private_key_file_is_unlinked_when_the_body_raises(key_area: Path) -> None:
    with pytest.raises(RuntimeError), private_key_file(PEM):
        raise RuntimeError("boom")
    assert left_behind(key_area) == []


def test_private_key_file_adds_the_final_newline_ssh_insists_on(key_area: Path) -> None:
    with private_key_file(PEM.rstrip("\n")) as path:
        assert path.read_text().endswith("-----END OPENSSH PRIVATE KEY-----\n")


def test_private_key_file_accepts_bytes_and_refuses_an_empty_key(key_area: Path) -> None:
    with private_key_file(PEM.encode()) as path:
        assert path.read_text() == PEM
    with pytest.raises(SshFailure) as raised:
        with private_key_file("  \n"):
            pass
    assert raised.value.outcome == "credential_refused"
    assert left_behind(key_area) == []


def test_key_falls_back_to_the_system_temporary_directory_without_tmpfs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fallback = tmp_path / "fallback"
    fallback.mkdir()
    monkeypatch.setattr(transport, "TMPFS_DIR", tmp_path / "no-such-tmpfs")
    monkeypatch.setattr(tempfile, "tempdir", str(fallback))
    with private_key_file(PEM) as path:
        assert path.parent.parent == fallback
    assert list(fallback.iterdir()) == []


# --------------------------------------------------------------------------------------------
# argv
# --------------------------------------------------------------------------------------------


def option_values(argv: list[str]) -> list[str]:
    return [argv[i + 1] for i, item in enumerate(argv) if item == "-o"]


def test_argv_shape_for_a_command_call() -> None:
    argv = build_ssh_argv(ENDPOINT, key_path=Path("/dev/shm/k/id"), known_hosts_path=Path("/dev/shm/k/known_hosts"), connect_timeout_s=7)
    assert argv[0] == "ssh"
    assert argv[argv.index("-i") + 1] == "/dev/shm/k/id"
    assert argv[argv.index("-p") + 1] == "2222"
    assert argv[argv.index("-F") + 1] == "/dev/null"  # no user or system ssh config
    assert argv[-1] == "runner@remote.example.test"  # and no remote command after it
    options = option_values(argv)
    for required in (
        "BatchMode=yes",
        "StrictHostKeyChecking=yes",
        "UserKnownHostsFile=/dev/shm/k/known_hosts",
        "GlobalKnownHostsFile=/dev/null",
        "IdentitiesOnly=yes",
        "IdentityAgent=none",
        "ForwardAgent=no",
        "PasswordAuthentication=no",
        "KbdInteractiveAuthentication=no",
        "PreferredAuthentications=publickey",
        "ClearAllForwardings=yes",
        "ConnectTimeout=7",
    ):
        assert required in options, required
    assert "-T" in argv and "-N" not in argv and "-L" not in argv and "-A" not in argv
    assert not any(value in ("StrictHostKeyChecking=no", "StrictHostKeyChecking=accept-new", "ForwardAgent=yes") for value in options)


def test_argv_shape_for_a_tunnel() -> None:
    argv = build_ssh_argv(
        ENDPOINT,
        key_path=Path("/dev/shm/k/id"),
        known_hosts_path=Path("/dev/shm/k/known_hosts"),
        forward=(40123, "localhost", 11434),
    )
    assert "-N" in argv and "-T" not in argv
    assert argv[argv.index("-L") + 1] == "127.0.0.1:40123:localhost:11434"
    assert "ExitOnForwardFailure=yes" in option_values(argv)
    assert "ClearAllForwardings=yes" not in option_values(argv)
    assert argv[-1] == "runner@remote.example.test"


def test_argv_brackets_an_ipv6_forward_target_and_refuses_a_bad_one() -> None:
    kwargs = dict(key_path=Path("/k/id"), known_hosts_path=Path("/k/kh"))
    argv = build_ssh_argv(ENDPOINT, forward=(40123, "::1", 8080), **kwargs)
    assert argv[argv.index("-L") + 1] == "127.0.0.1:40123:[::1]:8080"
    for bad in ("-oProxyCommand=x", "a:b:c", "host name", ""):
        with pytest.raises(ValueError):
            build_ssh_argv(ENDPOINT, forward=(40123, bad, 8080), **kwargs)
    with pytest.raises(ValueError):
        build_ssh_argv(ENDPOINT, forward=(40123, "localhost", 70000), **kwargs)


def test_argv_refuses_a_path_that_ssh_would_split() -> None:
    with pytest.raises(ValueError):
        build_ssh_argv(ENDPOINT, key_path=Path("/tmp/a b/id"), known_hosts_path=Path("/tmp/kh"))


# --------------------------------------------------------------------------------------------
# run_command: what reaches ssh
# --------------------------------------------------------------------------------------------


def test_run_command_sends_the_task_on_stdin_and_returns_stdout(fake_ssh: FakeSsh) -> None:
    task = os.urandom(300_000)  # larger than a pipe buffer: stdin and stdout must not deadlock
    fake_ssh.configure(stdout='{"ok": true}')
    stdout, stderr = call(task)
    assert stdout == b'{"ok": true}'
    assert stderr == ""
    record = fake_ssh.record()
    assert fake_ssh.stdin() == task
    assert record["stdin_sha256"] == hashlib.sha256(task).hexdigest()


def test_run_command_returns_binary_stdout_unchanged(fake_ssh: FakeSsh) -> None:
    fake_ssh.configure(stdout="café ✓")
    stdout, _ = call()
    assert stdout.decode("utf-8") == "café ✓"


def test_run_command_puts_neither_the_key_nor_the_task_on_the_command_line(fake_ssh: FakeSsh) -> None:
    call(b'{"user_text": "TASK-SENTINEL-DO-NOT-LEAK"}')
    argv = fake_ssh.record()["argv"]
    joined = "\0".join(argv)
    assert "TASK-SENTINEL" not in joined
    assert not any(sentinel in joined for sentinel in SENTINELS)
    assert "PRIVATE KEY" not in joined
    assert argv[-1] == "runner@remote.example.test"
    assert argv[argv.index("-i") + 1] == fake_ssh.record()["key_path"]


def test_the_key_file_is_0600_while_ssh_runs_and_gone_afterwards(fake_ssh: FakeSsh, key_area: Path) -> None:
    call()
    record = fake_ssh.record()
    assert record["key_mode"] == "0o600"
    assert record["key_dir_mode"] == "0o700"
    assert record["key_text"] == PEM
    assert record["key_path"].startswith(str(key_area) + os.sep)
    assert not Path(record["key_path"]).exists()
    assert left_behind(key_area) == []


def test_the_known_hosts_file_holds_exactly_the_pin(fake_ssh: FakeSsh) -> None:
    call()
    record = fake_ssh.record()
    assert record["known_hosts"] == f"[remote.example.test]:2222 {HOST_KEY}\n"
    assert "GlobalKnownHostsFile=/dev/null" in option_values(record["argv"])


def test_ssh_gets_a_minimal_environment_without_the_agent_or_parent_secrets(fake_ssh: FakeSsh) -> None:
    call()
    env = fake_ssh.record()["env"]
    assert env["SSH_AUTH_SOCK"] is None
    assert env["SECRET_IN_PARENT"] is None
    assert env["LC_ALL"] == "C"
    assert env["HOME"] == str(Path(fake_ssh.record()["key_path"]).parent)


def test_files_are_removed_even_when_the_call_fails(fake_ssh: FakeSsh, key_area: Path) -> None:
    fake_ssh.configure(exit=255, stderr="Permission denied (publickey).\n")
    with pytest.raises(SshFailure):
        call()
    assert left_behind(key_area) == []


# --------------------------------------------------------------------------------------------
# run_command: every outcome
# --------------------------------------------------------------------------------------------

CHANGED = (
    "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n"
    "@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @\n"
    "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n"
    "IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!\n"
    "Offending ED25519 key in /dev/shm/am-ssh-x/known_hosts:1\n"
    "Host key for [remote.example.test]:2222 has changed and you have requested strict checking.\n"
    "Host key verification failed.\n"
)

CLASSIFIED = [
    pytest.param(CHANGED, "host_key_changed", False, id="changed-key"),
    pytest.param("Host key verification failed.\n", "host_key_unpinned", False, id="no-pin"),
    pytest.param(
        "No ED25519 host key is known for [remote.example.test]:2222 and you have requested strict checking.\n"
        "Host key verification failed.\n",
        "host_key_unpinned",
        False,
        id="no-key-for-host",
    ),
    pytest.param("runner@remote.example.test: Permission denied (publickey).\n", "credential_refused", False, id="refused-key"),
    pytest.param(
        'Load key "/dev/shm/am-ssh-x/id": invalid format\nrunner@remote.example.test: Permission denied (publickey).\n',
        "credential_refused",
        False,
        id="unusable-key",
    ),
    pytest.param("ssh: connect to host remote.example.test port 2222: Connection refused\n", "unreachable", False, id="refused-connection"),
    pytest.param("ssh: Could not resolve hostname nowhere.invalid: Name or service not known\n", "unreachable", False, id="no-dns"),
    pytest.param("ssh: connect to host 10.0.0.9 port 22: No route to host\n", "unreachable", False, id="no-route"),
    pytest.param("ssh: connect to host 10.0.0.9 port 22: Network is unreachable\n", "unreachable", False, id="no-network"),
    pytest.param("ssh: connect to host 10.0.0.9 port 22: Connection timed out\n", "timeout", False, id="connect-timeout"),
    pytest.param("Connection timed out during banner exchange\n", "timeout", False, id="banner-timeout"),
    pytest.param("Timeout, server remote.example.test not responding.\n", "timeout", True, id="went-silent"),
    pytest.param("kex_exchange_identification: read: Connection reset by peer\n", "protocol_error", True, id="unrecognised-255"),
    pytest.param("", "protocol_error", True, id="silent-255"),
]


@pytest.mark.parametrize("stderr,outcome,sent", CLASSIFIED)
def test_ssh_exit_255_is_classified_from_its_stderr(fake_ssh: FakeSsh, stderr: str, outcome: str, sent: bool) -> None:
    fake_ssh.configure(exit=255, stderr=stderr)
    with pytest.raises(SshFailure) as raised:
        call()
    assert raised.value.outcome == outcome
    assert raised.value.sent is sent
    assert raised.value.exit_status == 255


def test_changed_wins_over_the_verification_failed_line_it_comes_with(fake_ssh: FakeSsh) -> None:
    fake_ssh.configure(exit=255, stderr=CHANGED)
    with pytest.raises(SshFailure) as raised:
        call()
    assert raised.value.outcome == "host_key_changed"


@pytest.mark.parametrize("status", [1, 2, 64, 78, 127])
def test_a_remote_exit_status_is_never_read_as_an_ssh_diagnosis(fake_ssh: FakeSsh, status: int) -> None:
    # The remote script may print anything; only ssh's own status 255 is an ssh diagnosis.
    fake_ssh.configure(exit=status, stderr="Permission denied (publickey). Connection refused. Host key verification failed.\n")
    with pytest.raises(SshFailure) as raised:
        call()
    assert raised.value.outcome == "protocol_error"
    assert raised.value.sent is True
    assert raised.value.exit_status == status
    assert f"exit status {status}" in raised.value.detail


def test_a_call_that_outlives_its_deadline_is_a_timeout_that_may_have_run(fake_ssh: FakeSsh) -> None:
    fake_ssh.configure(sleep=30)
    started = time.monotonic()
    with pytest.raises(SshFailure) as raised:
        call(timeout_s=1)
    assert time.monotonic() - started < 10
    assert raised.value.outcome == "timeout"
    assert raised.value.sent is True  # plan 3: outcome-unknown, not retry-safe
    pid = fake_ssh.record()["pid"]
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)  # our own child was killed and reaped


def test_the_connect_phase_gets_a_deadline_shorter_than_the_call(fake_ssh: FakeSsh) -> None:
    call(timeout_s=5)
    assert "ConnectTimeout=4" in option_values(fake_ssh.record()["argv"])
    call(timeout_s=600)
    assert "ConnectTimeout=10" in option_values(fake_ssh.record(2)["argv"])


def test_stdout_over_the_bound_kills_the_call(fake_ssh: FakeSsh) -> None:
    fake_ssh.configure(stdout_size=50_000, sleep_after=30)
    started = time.monotonic()
    with pytest.raises(SshFailure) as raised:
        call(max_output=1_000)
    assert time.monotonic() - started < 10
    assert raised.value.outcome == "protocol_error"
    assert raised.value.sent is True
    assert "exceeded 1000 bytes" in raised.value.detail
    with pytest.raises(ProcessLookupError):
        os.kill(fake_ssh.record()["pid"], 0)


def test_stdout_exactly_at_the_bound_is_accepted(fake_ssh: FakeSsh) -> None:
    fake_ssh.configure(stdout_size=1_000)
    stdout, _ = call(max_output=1_000)
    assert len(stdout) == 1_000


def test_no_pin_means_no_ssh_at_all(fake_ssh: FakeSsh, key_area: Path) -> None:
    for pin in (None, "", "   ", "ssh-ed25519 !!!", "garbage"):
        with pytest.raises(SshFailure) as raised:
            call(host_key=pin)
        assert raised.value.outcome == "host_key_unpinned"
        assert raised.value.sent is False
    assert fake_ssh.calls() == 0  # nothing was started: there is no TOFU in the call path
    assert left_behind(key_area) == []


def test_an_empty_key_means_no_ssh_at_all(fake_ssh: FakeSsh) -> None:
    with pytest.raises(SshFailure) as raised:
        run_command(ENDPOINT, "", HOST_KEY, b"{}", 5, 100)
    assert raised.value.outcome == "credential_refused"
    assert raised.value.sent is False
    assert fake_ssh.calls() == 0


def test_a_missing_ssh_binary_is_a_typed_failure_that_sent_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key_area: Path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    with pytest.raises(SshFailure) as raised:
        call()
    assert raised.value.outcome == "protocol_error"
    assert raised.value.sent is False
    assert left_behind(key_area) == []


def test_bad_arguments_are_a_programming_error_not_a_failure(fake_ssh: FakeSsh) -> None:
    with pytest.raises(ValueError):
        call(timeout_s=0)
    with pytest.raises(ValueError):
        call(max_output=0)


# --------------------------------------------------------------------------------------------
# stderr
# --------------------------------------------------------------------------------------------


def test_scrub_drops_private_key_lines_and_truncates_to_500() -> None:
    text = "before\n-----BEGIN OPENSSH PRIVATE KEY-----\nbody\nan unprotected private key line\nafter\n"
    assert scrub_stderr(text) == "before\nbody\nafter"
    assert len(scrub_stderr("x" * 5000)) == 500
    assert scrub_stderr("x" * 5000).endswith("...")
    assert scrub_stderr(b"bytes \xff ok") == "bytes � ok"
    assert scrub_stderr("") == ""


def test_scrub_redacts_the_secrets_it_is_given() -> None:
    assert scrub_stderr("see /dev/shm/am-ssh-1/id now", ["/dev/shm/am-ssh-1/id"]) == "see <redacted> now"
    assert scrub_stderr("tiny", ["ti"]) == "tiny"  # too short to be a meaningful secret


def test_a_failure_detail_is_scrubbed_by_construction() -> None:
    failure = SshFailure("protocol_error", "ok\n-----BEGIN OPENSSH PRIVATE KEY-----\n" + "z" * 900, sent=True)
    assert "PRIVATE KEY" not in failure.detail
    assert len(failure.detail) <= 500
    with pytest.raises(ValueError):
        SshFailure("made_up", "x", sent=False)


def test_sentinel_private_key_never_reaches_a_result_an_error_or_a_log(
    fake_ssh: FakeSsh, caplog: pytest.LogCaptureFixture
) -> None:
    # The worst case: ssh itself echoes the key file to stderr (as a hostile wrapper could).
    caplog.set_level("DEBUG")
    fake_ssh.configure(stderr_key_file=True, stdout="done")
    stdout, stderr = call()
    assert stdout == b"done"
    for sentinel in SENTINELS:
        assert sentinel not in stderr
    assert "PRIVATE KEY" not in stderr

    fake_ssh.configure(stderr_key_file=True, exit=255)
    with pytest.raises(SshFailure) as raised:
        call()
    rendered = f"{raised.value} {raised.value.detail} {raised.value!r}"
    key_path = fake_ssh.record(2)["key_path"]
    for forbidden in (*SENTINELS, "PRIVATE KEY", key_path):
        assert forbidden not in rendered
        assert forbidden not in caplog.text


def test_remote_stderr_is_bounded_in_the_returned_value(fake_ssh: FakeSsh) -> None:
    fake_ssh.configure(stderr="e" * 200_000, stdout="x")
    _, stderr = call()
    assert len(stderr) == 500


# --------------------------------------------------------------------------------------------
# scan_host_key
# --------------------------------------------------------------------------------------------


def test_scan_host_key_returns_the_ed25519_key_in_canonical_form(fake_ssh: FakeSsh) -> None:
    rsa = make_host_key(b"r", "ssh-rsa")
    ecdsa = make_host_key(b"e", "ecdsa-sha2-nistp256")
    fake_ssh.configure_keyscan(
        stdout=(
            "# remote.example.test:2222 SSH-2.0-OpenSSH_9.6\n"
            f"[remote.example.test]:2222 {rsa}\n"
            f"[remote.example.test]:2222 {ecdsa}\n"
            f"[remote.example.test]:2222 {HOST_KEY}\n"
        )
    )
    assert scan_host_key(ENDPOINT, timeout=5) == HOST_KEY
    argv = json.loads((fake_ssh.directory / "keyscan.argv.json").read_text())
    assert argv[argv.index("-p") + 1] == "2222"
    assert argv[argv.index("-T") + 1] == "5"
    assert argv[-1] == "remote.example.test"


def test_scan_host_key_falls_back_to_the_best_key_the_server_has(fake_ssh: FakeSsh) -> None:
    rsa = make_host_key(b"r", "ssh-rsa")
    fake_ssh.configure_keyscan(stdout=f"remote.example.test {rsa}\n")
    assert scan_host_key(ENDPOINT) == rsa


@pytest.mark.parametrize(
    "stderr,outcome",
    [
        ("# remote.example.test:2222 SSH-2.0-x\nssh_connect: Connection refused\n", "unreachable"),
        ("getaddrinfo remote.example.test: Name or service not known\n", "unreachable"),
        ("ssh_connect: Connection timed out\n", "timeout"),
        ("", "unreachable"),
    ],
)
def test_scan_host_key_without_a_key_is_unreachable_or_timeout_and_sent_nothing(fake_ssh: FakeSsh, stderr: str, outcome: str) -> None:
    fake_ssh.configure_keyscan(stdout="# only a comment\n", stderr=stderr)
    with pytest.raises(SshFailure) as raised:
        scan_host_key(ENDPOINT)
    assert raised.value.outcome == outcome
    assert raised.value.sent is False


def test_scan_ignores_malformed_lines(fake_ssh: FakeSsh) -> None:
    fake_ssh.configure_keyscan(stdout=f"junk line\nssh-ed25519 AAAA\n{HOST_KEY}\n")
    assert scan_host_key(ENDPOINT) == HOST_KEY


# --------------------------------------------------------------------------------------------
# open_tunnel
# --------------------------------------------------------------------------------------------


def port_is_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def test_open_tunnel_yields_a_ready_loopback_port_and_terminates_its_own_process(fake_ssh: FakeSsh, key_area: Path) -> None:
    with open_tunnel(ENDPOINT, PEM, HOST_KEY, "localhost", 11434, timeout_s=10) as port:
        assert port_is_open(port)
        record = fake_ssh.record()
        argv = record["argv"]
        assert argv[argv.index("-L") + 1] == f"127.0.0.1:{port}:localhost:11434"
        assert "-N" in argv
        assert record["key_mode"] == "0o600"
        assert record["known_hosts"] == f"[remote.example.test]:2222 {HOST_KEY}\n"
        assert Path(record["key_path"]).exists()
        pid = record["pid"]
        os.kill(pid, 0)  # alive while the tunnel is open
    # closed: the process we started got SIGTERM, is gone, the port is closed and the key is unlinked
    assert (fake_ssh.directory / "terminated").read_text() == str(pid)
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
    assert not port_is_open(port)
    assert left_behind(key_area) == []


def test_open_tunnel_tears_down_when_the_body_raises(fake_ssh: FakeSsh, key_area: Path) -> None:
    with pytest.raises(RuntimeError), open_tunnel(ENDPOINT, PEM, HOST_KEY, "localhost", 11434, timeout_s=10) as port:
        raise RuntimeError("the http call failed")
    with pytest.raises(ProcessLookupError):
        os.kill(fake_ssh.record()["pid"], 0)
    assert not port_is_open(port)
    assert left_behind(key_area) == []


def test_open_tunnel_waits_for_a_slow_listener(fake_ssh: FakeSsh) -> None:
    fake_ssh.configure(listen_delay=0.6)
    started = time.monotonic()
    with open_tunnel(ENDPOINT, PEM, HOST_KEY, "localhost", 11434, timeout_s=10) as port:
        assert time.monotonic() - started >= 0.5
        assert port_is_open(port)


@pytest.mark.parametrize(
    "stderr,outcome",
    [pytest.param(c.values[0], c.values[1], id=c.id) for c in CLASSIFIED[:9]],
)
def test_open_tunnel_that_ssh_refuses_is_a_typed_failure_with_nothing_sent(
    fake_ssh: FakeSsh, key_area: Path, stderr: str, outcome: str
) -> None:
    fake_ssh.configure(fail=True, exit=255, stderr=stderr)
    with pytest.raises(SshFailure) as raised:
        with open_tunnel(ENDPOINT, PEM, HOST_KEY, "localhost", 11434, timeout_s=10):
            pytest.fail("the tunnel must not open")
    assert raised.value.outcome == outcome
    assert raised.value.sent is False
    with pytest.raises(ProcessLookupError):
        os.kill(fake_ssh.record()["pid"], 0)
    assert left_behind(key_area) == []


def test_open_tunnel_that_never_listens_times_out_and_kills_ssh(fake_ssh: FakeSsh, key_area: Path) -> None:
    fake_ssh.configure(no_listen=True)
    started = time.monotonic()
    with pytest.raises(SshFailure) as raised:
        with open_tunnel(ENDPOINT, PEM, HOST_KEY, "localhost", 11434, timeout_s=1):
            pytest.fail("the tunnel must not open")
    assert time.monotonic() - started < 10
    assert raised.value.outcome == "timeout"
    assert raised.value.sent is False
    with pytest.raises(ProcessLookupError):
        os.kill(fake_ssh.record()["pid"], 0)
    assert left_behind(key_area) == []


def test_open_tunnel_retries_with_another_port_when_the_chosen_one_was_taken(fake_ssh: FakeSsh) -> None:
    taken = (
        "bind [127.0.0.1]:1: Address already in use\n"
        "channel_setup_fwd_listener_tcpip: cannot listen to port: 1\n"
        "Could not request local forwarding.\n"
    )
    fake_ssh.configure(per_call=[{"fail": True, "exit": 255, "stderr": taken}, {}])
    with open_tunnel(ENDPOINT, PEM, HOST_KEY, "localhost", 11434, timeout_s=10) as port:
        assert port_is_open(port)
    assert fake_ssh.calls() == 2


def test_open_tunnel_without_a_pin_starts_nothing(fake_ssh: FakeSsh) -> None:
    with pytest.raises(SshFailure) as raised:
        with open_tunnel(ENDPOINT, PEM, None, "localhost", 11434):
            pytest.fail("the tunnel must not open")
    assert raised.value.outcome == "host_key_unpinned"
    assert fake_ssh.calls() == 0


def test_open_tunnel_with_a_bad_target_starts_nothing_and_leaves_no_key(fake_ssh: FakeSsh, key_area: Path) -> None:
    with pytest.raises(ValueError):
        with open_tunnel(ENDPOINT, PEM, HOST_KEY, "-oProxyCommand=x", 11434):
            pytest.fail("the tunnel must not open")
    assert fake_ssh.calls() == 0
    assert left_behind(key_area) == []


def test_tunnel_stderr_never_carries_the_key(fake_ssh: FakeSsh) -> None:
    fake_ssh.configure(fail=True, exit=255, stderr_key_file=True)
    with pytest.raises(SshFailure) as raised:
        with open_tunnel(ENDPOINT, PEM, HOST_KEY, "localhost", 11434, timeout_s=10):
            pytest.fail("the tunnel must not open")
    for forbidden in (*SENTINELS, "PRIVATE KEY"):
        assert forbidden not in str(raised.value)


# --------------------------------------------------------------------------------------------
# The real client, no server: its own refusal text is what the classifier reads
# --------------------------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("ssh") is None, reason="needs the OpenSSH client")
def test_the_real_client_refusing_a_closed_port_is_unreachable() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        closed_port = probe.getsockname()[1]  # nothing listens once the socket is closed below
    endpoint = SshEndpoint("127.0.0.1", closed_port, "runner")
    with pytest.raises(SshFailure) as raised:
        run_command(endpoint, PEM, HOST_KEY, b"{}", 15, 1000)
    assert raised.value.outcome == "unreachable"
    assert raised.value.sent is False
