"""The SSH transport of executor connections (`EXEC-SSH-01`, plan 2.1, 3, 4.1, T-6, T-7, T-9).

One standalone module that drives the **OpenSSH client binary** through ``subprocess``. There is
no ``paramiko`` and no ``asyncssh``; the standard library is the only dependency. It knows nothing
of connections, revisions, secrets or the database: a caller hands it an endpoint, the *unsealed*
private key and the pinned host key, and gets bytes (or a typed failure) back.

What it does, and the rule each part serves:

* ``run_command`` -- an ``ssh_command`` call. The task goes to the remote command's **stdin**, the
  answer comes back on **stdout**. Neither the key nor the task is ever on a command line (a command
  line is visible in the process list). The remote side is a forced command
  (``tools/executor-runner/ssh-forced-command.sh`` or a ``custom_command`` script): the client names
  no command at all, so a stolen admin session cannot choose what runs (plan T-6). A command that
  prints **heartbeat lines** on stderr (`AR-V3-LIVENESS-01`, see below) may run past ``timeout_s``.
* ``open_tunnel`` -- a short-lived ``ssh -N -L`` to the remote HTTP model for ``http_api`` over
  ``transport: ssh_tunnel``. Local end on ``127.0.0.1`` only, closed when the context exits.
* ``scan_host_key`` -- read the host key of a machine. **Probe only**: there is no TOFU in the call
  path. A call uses ``StrictHostKeyChecking=yes`` against a known-hosts file that holds exactly the
  pinned key, so a key that differs is refused (``host_key_changed``) and a missing pin is refused
  (``host_key_unpinned``).
* ``ssh_destination`` -- the associated-data destination string of plan 4.1 for sealing a key.

The private key lives on disk only inside a private (0700) directory on tmpfs (``/dev/shm``), as a
0600 file, for the length of one call, and is unlinked in a ``finally``.

Failure model. Every failure is an ``SshFailure(outcome, detail, sent)``:

=====================  ====================================================================  =====
outcome                meaning                                                               sent
=====================  ====================================================================  =====
``host_key_changed``   the server's key differs from the pin                                 False
``host_key_unpinned``  no usable pin (empty, malformed, or the host is not in the pin file)  False
``credential_refused`` the server refused the key (or the key file is unusable)              False
``unreachable``        no route, DNS failure, connection refused, or no key observed          False
``timeout``            connect phase timed out (sent False), or the call outlived its         both
                       deadline / the server stopped answering after connecting (sent True)
``stalled``            a live call (see below) was silent for longer than its stall window    True
``hard_cap``           a live call reached its absolute ceiling while still signalling         True
``protocol_error``     anything else: unrecognised ssh failure, non-zero remote exit status,   True
                       output over the bound
=====================  ====================================================================  =====

``sent`` is ``True`` once the remote command **may** have started. Per plan 3 an ``ssh_command``
already started that fails or times out is *outcome-unknown*: the model may have run and, for an
API key, spent. A caller must not retry it three times over. ``sent`` is ``False`` only when the
failure is one that ssh reports *before* authentication completed.

Signs of life (`AR-V3-LIVENESS-01`). Until now ``timeout_s`` bounded the whole call, so a model
that is thinking could not be told from one that hangs. With ``live_hard_cap_s`` given, a call
whose remote command writes a **heartbeat line** to stderr is *live* from the first such line:
``timeout_s`` stops applying, the call may run until ``live_hard_cap_s`` after it started, and it
ends as ``stalled`` when ``live_stall_s`` passes without another heartbeat. A heartbeat is
recognised **only** by :data:`HEARTBEAT_LINE` on a whole stderr line; any other byte of stderr
(an ssh warning, a remote error, text that merely looks alike) is not a sign of life. A command
that never prints one is bounded by ``timeout_s`` exactly as before, and so is every call made
without ``live_hard_cap_s``. Heartbeat lines are not kept in the returned stderr.

Classification is taken from ``ssh``'s exit status 255 and its stderr text. Exit status 255 is
ssh's own failure code; any other non-zero status is the remote command's and is never read as an
ssh diagnosis (a remote script that prints "Permission denied" and exits 1 is not a refused key).
ssh is run with ``LC_ALL=C`` so the messages are the English ones this module matches.
"""

from __future__ import annotations

import base64
import binascii
import contextlib
import hashlib
import ipaddress
import logging
import os
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

__all__ = [
    "HEARTBEAT_LINE",
    "OUTCOMES",
    "HostKeyFormatError",
    "SshEndpoint",
    "SshFailure",
    "build_ssh_argv",
    "host_key_fingerprint",
    "known_hosts_line",
    "normalise_host_key_line",
    "open_tunnel",
    "private_key_file",
    "run_command",
    "scan_host_key",
    "scrub_stderr",
    "ssh_destination",
]

LOGGER = logging.getLogger(__name__)

OUTCOMES: tuple[str, ...] = (
    "host_key_changed",
    "host_key_unpinned",
    "credential_refused",
    "unreachable",
    "timeout",
    "protocol_error",
    "stalled",
    "hard_cap",
)

#: Where a private key is written. tmpfs, so it never reaches a disk. A host without it (a
#: developer's laptop) falls back to the system temporary directory and says so in the log.
TMPFS_DIR = Path("/dev/shm")

#: Stored stderr is bounded: remote stderr is attacker-influenced text.
STDERR_LIMIT_CHARS = 500
_STDERR_CAPTURE_BYTES = 64 * 1024

#: The one stderr line that is a sign of life (`AR-V3-LIVENESS-01`, the frozen interface with
#: ``tools/executor-runner/claude_answer.py``): three non-negative integers -- elapsed seconds,
#: events read, output tokens -- and nothing else. Matched against a **whole** line without its
#: terminator; never a substring, never a prefix.
HEARTBEAT_LINE: Final = re.compile(rb"^pdf-analysis-forced-command: hb [0-9]+ [0-9]+ [0-9]+$")
#: A heartbeat line is under a hundred bytes. A line longer than this is never one, and is not
#: buffered whole while it is read.
_HEARTBEAT_MAX_LINE_BYTES = 1024
#: ``on_signal`` is called at most this often, however many heartbeat lines arrive.
_SIGNAL_CALLBACK_INTERVAL_S = 1.0
#: How often a live call looks at its limits while the process runs.
_LIVE_TICK_S = 0.25

_HOST_RE = re.compile(r"[A-Za-z0-9_](?:[A-Za-z0-9_.-]{0,251}[A-Za-z0-9_])?")
_USER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,63}")
_KEY_TYPE_RE = re.compile(r"(?:ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(?:256|384|521)|sk-ssh-ed25519@openssh\.com|sk-ecdsa-sha2-nistp256@openssh\.com)")
_SCAN_PREFERENCE = ("ssh-ed25519", "ecdsa-sha2-nistp256", "ecdsa-sha2-nistp384", "ecdsa-sha2-nistp521", "ssh-rsa")


class HostKeyFormatError(ValueError):
    """A pinned or observed host-key line is not ``keytype base64``."""


class SshFailure(Exception):
    """A typed SSH failure. ``detail`` is scrubbed text, safe to store; ``sent`` see the module doc."""

    def __init__(self, outcome: str, detail: str, sent: bool, exit_status: int | None = None) -> None:
        if outcome not in OUTCOMES:
            raise ValueError(f"unknown ssh outcome {outcome!r}")
        self.outcome = outcome
        self.detail = scrub_stderr(detail)
        self.sent = bool(sent)
        self.exit_status = exit_status
        super().__init__(self.outcome, self.detail, self.sent, exit_status)

    def __str__(self) -> str:
        return f"{self.outcome}: {self.detail}"


@dataclass(frozen=True)
class SshEndpoint:
    """``user@host:port``. Validated so that no field can become an option, a pattern or a line."""

    host: str
    port: int
    user: str

    def __post_init__(self) -> None:
        host = self.host
        if not isinstance(host, str) or not host:
            raise ValueError("ssh host must be a non-empty string")
        if ":" in host:
            try:
                ipaddress.IPv6Address(host)
            except ValueError as error:
                raise ValueError("ssh host with ':' must be an IPv6 literal") from error
        elif not _HOST_RE.fullmatch(host):
            raise ValueError("ssh host must be a hostname or an IP literal (no option, pattern or space)")
        if not isinstance(self.port, int) or isinstance(self.port, bool) or not 1 <= self.port <= 65535:
            raise ValueError("ssh port must be an integer in 1..65535")
        if not isinstance(self.user, str) or not _USER_RE.fullmatch(self.user):
            raise ValueError("ssh user must be a plain account name")

    @property
    def address(self) -> str:
        """``host:port`` (an IPv6 literal in brackets), the endpoint part of plan 4.1."""
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"{host}:{self.port}"


# --------------------------------------------------------------------------------------------
# Host keys
# --------------------------------------------------------------------------------------------


def normalise_host_key_line(line: str) -> str:
    """Reduce any known-hosts / ssh-keyscan style line to ``keytype base64``.

    Accepts ``keytype base64``, ``host keytype base64`` and either with a trailing comment. The
    key blob must be valid base64 and must announce the key type it is filed under, so a malformed
    pin is refused here instead of reaching ssh.
    """

    if not isinstance(line, str):
        raise HostKeyFormatError("host key line must be text")
    stripped = line.strip()
    if not stripped or "\n" in stripped or "\r" in stripped or "\0" in stripped:
        raise HostKeyFormatError("host key line must be one non-empty line")
    tokens = stripped.split()
    for index, token in enumerate(tokens):
        if _KEY_TYPE_RE.fullmatch(token):
            break
    else:
        raise HostKeyFormatError("no supported key type in the host key line")
    if index + 1 >= len(tokens):
        raise HostKeyFormatError("host key line has no key data")
    key_type, blob = token, tokens[index + 1]
    try:
        raw = base64.b64decode(blob, validate=True)
    except (binascii.Error, ValueError) as error:
        raise HostKeyFormatError("host key data is not base64") from error
    # The blob starts with a length-prefixed copy of the key type.
    if len(raw) < 4:
        raise HostKeyFormatError("host key data is too short")
    announced_length = int.from_bytes(raw[:4], "big")
    if raw[4 : 4 + announced_length] != key_type.encode("ascii"):
        raise HostKeyFormatError("host key data does not match its key type")
    return f"{key_type} {blob}"


def host_key_fingerprint(host_key_line: str) -> str:
    """``SHA256:...`` as ``ssh-keygen -l`` prints it, for the administrator to confirm."""
    _, blob = normalise_host_key_line(host_key_line).split(" ")
    digest = hashlib.sha256(base64.b64decode(blob)).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


def known_hosts_line(endpoint: SshEndpoint, host_key_line: str) -> str:
    """The known-hosts line that pins ``host_key_line`` to ``endpoint``: ``[host]:port keytype base64``.

    OpenSSH files the default port under the bare host name -- ``[host]:22`` would never match --
    so for port 22 the host is not bracketed.
    """

    key = normalise_host_key_line(host_key_line)
    host = endpoint.host
    prefix = host if endpoint.port == 22 else f"[{host}]:{endpoint.port}"
    return f"{prefix} {key}"


# --------------------------------------------------------------------------------------------
# Files: the key on tmpfs for one call
# --------------------------------------------------------------------------------------------


def _key_base_directory() -> Path:
    if TMPFS_DIR.is_dir() and os.access(TMPFS_DIR, os.W_OK | os.X_OK):
        return TMPFS_DIR
    fallback = Path(tempfile.gettempdir())
    LOGGER.warning("ssh transport: %s is unavailable, the key file goes to %s", TMPFS_DIR, fallback)
    return fallback


@contextlib.contextmanager
def _private_directory() -> Iterator[Path]:
    directory = Path(tempfile.mkdtemp(prefix="am-ssh-", dir=_key_base_directory()))  # mode 0700
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def _write_private(path: Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(descriptor, view) :]
    finally:
        os.close(descriptor)


def _key_bytes(private_key_pem: str | bytes) -> bytes:
    data = private_key_pem.encode("utf-8") if isinstance(private_key_pem, str) else bytes(private_key_pem)
    data = data.replace(b"\r\n", b"\n")
    if not data.strip() or b"\0" in data:
        raise SshFailure("credential_refused", "the private key is empty or malformed", sent=False)
    # ssh refuses a key file without a final newline ("invalid format").
    return data if data.endswith(b"\n") else data + b"\n"


@contextlib.contextmanager
def private_key_file(private_key_pem: str | bytes) -> Iterator[Path]:
    """Write the key to a 0600 file in a private tmpfs directory; unlink it on exit, always."""
    data = _key_bytes(private_key_pem)
    with _private_directory() as directory:
        path = directory / "id"
        _write_private(path, data)
        yield path


@dataclass(frozen=True)
class _SessionFiles:
    key_path: Path
    known_hosts_path: Path


@contextlib.contextmanager
def _session_files(endpoint: SshEndpoint, private_key_pem: str | bytes, host_key_line: str | None) -> Iterator[_SessionFiles]:
    """Key file plus the pin file, validated *before* anything is written."""
    if host_key_line is None or not str(host_key_line).strip():
        raise SshFailure("host_key_unpinned", "the connection has no pinned host key", sent=False)
    try:
        pin = known_hosts_line(endpoint, host_key_line)
    except HostKeyFormatError as error:
        raise SshFailure("host_key_unpinned", f"the pinned host key is malformed ({error})", sent=False) from error
    data = _key_bytes(private_key_pem)
    with _private_directory() as directory:
        key_path = directory / "id"
        known_hosts_path = directory / "known_hosts"
        _write_private(key_path, data)
        _write_private(known_hosts_path, (pin + "\n").encode("ascii"))
        yield _SessionFiles(key_path, known_hosts_path)


# --------------------------------------------------------------------------------------------
# argv
# --------------------------------------------------------------------------------------------


def _path_option_value(path: Path) -> str:
    text = str(path)
    if any(ch.isspace() or ch in "\"'\\" for ch in text):
        raise ValueError("ssh file paths must not contain spaces or quotes")
    return text


def build_ssh_argv(
    endpoint: SshEndpoint,
    *,
    key_path: Path,
    known_hosts_path: Path,
    connect_timeout_s: float = 10,
    forward: tuple[int, str, int] | None = None,
    ssh_binary: str = "ssh",
) -> list[str]:
    """The argv of one ssh invocation. Pure: it reads nothing and starts nothing.

    The invocation is hermetic: ``-F /dev/null`` ignores the user's and the system's ssh config,
    the only identity is ``-i`` (``IdentitiesOnly``), the only known-hosts file is the pin, the
    agent is off, and only public-key authentication is tried (``BatchMode``: it never prompts).
    A command call names **no remote command**: the forced command on the server decides. With
    ``forward=(local_port, remote_host, remote_port)`` it is a tunnel: ``-N -L`` bound to
    ``127.0.0.1``.
    """

    connect_timeout = max(1, int(connect_timeout_s))
    argv = [
        ssh_binary,
        "-F", "/dev/null",
        "-i", _path_option_value(key_path),
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=yes",
        "-o", f"UserKnownHostsFile={_path_option_value(known_hosts_path)}",
        "-o", "GlobalKnownHostsFile=/dev/null",
        "-o", "IdentitiesOnly=yes",
        "-o", "IdentityAgent=none",
        "-o", "PreferredAuthentications=publickey",
        "-o", "PubkeyAuthentication=yes",
        "-o", "PasswordAuthentication=no",
        "-o", "KbdInteractiveAuthentication=no",
        "-o", "ForwardAgent=no",
        "-o", "ForwardX11=no",
        "-o", "PermitLocalCommand=no",
        "-o", "ProxyCommand=none",
        "-o", "ProxyJump=none",
        "-o", "ControlMaster=no",
        "-o", "ControlPath=none",
        "-o", "CheckHostIP=no",
        "-o", "VerifyHostKeyDNS=no",
        "-o", "UpdateHostKeys=no",
        "-o", "HashKnownHosts=no",
        "-o", "LogLevel=ERROR",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=3",
        "-o", f"ConnectTimeout={connect_timeout}",
        "-p", str(endpoint.port),
    ]
    if forward is None:
        argv += ["-T", "-o", "ClearAllForwardings=yes"]
    else:
        local_port, remote_host, remote_port = forward
        if not (1 <= int(local_port) <= 65535 and 1 <= int(remote_port) <= 65535):
            raise ValueError("forward ports must be in 1..65535")
        if ":" in remote_host:
            ipaddress.IPv6Address(remote_host)
            remote = f"[{remote_host}]"
        elif _HOST_RE.fullmatch(remote_host):
            remote = remote_host
        else:
            raise ValueError("forward target must be a hostname or an IP literal")
        argv += [
            "-N",
            "-o", "ExitOnForwardFailure=yes",
            "-L", f"127.0.0.1:{int(local_port)}:{remote}:{int(remote_port)}",
        ]
    argv.append(f"{endpoint.user}@{endpoint.host}")
    return argv


def _child_environment(home: Path | None = None) -> dict[str, str]:
    """A minimal environment: no agent socket, no proxy variables, English messages."""
    environment = {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "LC_ALL": "C", "LANG": "C"}
    if home is not None:
        environment["HOME"] = str(home)
    return environment


# --------------------------------------------------------------------------------------------
# stderr: scrub and classify
# --------------------------------------------------------------------------------------------


def scrub_stderr(text: str | bytes, secrets: Iterable[str] = ()) -> str:
    """Make remote/ssh stderr safe to store: no key material, bounded.

    Drops every line that mentions ``PRIVATE KEY``, redacts any ``secrets`` substring (the lines of
    the key actually in use, and its path), then truncates to 500 characters.
    """

    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    redactions = sorted({s for s in secrets if s and len(s) >= 8}, key=len, reverse=True)
    kept: list[str] = []
    for line in text.splitlines():
        if "PRIVATE KEY" in line.upper():
            continue
        for secret in redactions:
            line = line.replace(secret, "<redacted>")
        kept.append(line)
    cleaned = "\n".join(kept).strip()
    if len(cleaned) > STDERR_LIMIT_CHARS:
        cleaned = cleaned[: STDERR_LIMIT_CHARS - 3] + "..."
    return cleaned


def _key_secrets(private_key_pem: str | bytes, key_path: Path | None = None) -> list[str]:
    text = private_key_pem.decode("utf-8", errors="replace") if isinstance(private_key_pem, bytes) else private_key_pem
    secrets = [line.strip() for line in text.splitlines() if line.strip()]
    if key_path is not None:
        secrets += [str(key_path), str(key_path.parent)]
    return secrets


# Order matters: "changed" before "verification failed", which a changed key also prints.
_CLASSIFIERS: tuple[tuple[tuple[str, ...], str, bool], ...] = (
    (("REMOTE HOST IDENTIFICATION HAS CHANGED", "Host key for ", "POSSIBLE DNS SPOOFING"), "host_key_changed", False),
    (("Host key verification failed", "No host key is known", "host key is not known"), "host_key_unpinned", False),
    (("Permission denied", "Too many authentication failures", "Authentication failed"), "credential_refused", False),
    (("Load key ",), "credential_refused", False),
    # Mid-session silence: the command had started.
    (("Timeout, server", "not responding"), "timeout", True),
    (("timed out", "Timed out"), "timeout", False),
    (
        (
            "Connection refused",
            "Could not resolve hostname",
            "Name or service not known",
            "Temporary failure in name resolution",
            "No route to host",
            "Network is unreachable",
            "Host is down",
        ),
        "unreachable",
        False,
    ),
)


def _classify_ssh_error(stderr_text: str) -> tuple[str, bool] | None:
    for needles, outcome, sent in _CLASSIFIERS:
        if any(needle in stderr_text for needle in needles):
            return outcome, sent
    return None


# --------------------------------------------------------------------------------------------
# Running a process with bounded output and a deadline
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Completed:
    status: int
    stdout: bytes
    stderr: bytes
    timed_out: bool
    stdout_overflow: bool
    #: A live call (see :class:`_Liveness`) cut for silence / for reaching its ceiling.
    stalled: bool = False
    hard_capped: bool = False


class _Liveness:
    """The signs of life of one call and the two-phase deadline they govern.

    Until the first heartbeat line the call is bounded by ``timeout_s``, as it always was. From
    the first one it is bounded by ``hard_cap_s`` after the call started, and by ``stall_s`` after
    the latest heartbeat. :meth:`sign` is called by the stderr reader thread, :meth:`verdict` and
    :meth:`next_check` by the thread that waits for the process; one lock covers the three
    instants they share.
    """

    def __init__(
        self, *, started: float, timeout_s: float, hard_cap_s: float, stall_s: float | None,
        on_signal: Callable[[], None] | None,
    ) -> None:
        self._started = started
        self._timeout_s = timeout_s
        self._hard_cap_s = hard_cap_s
        self._stall_s = stall_s
        self._on_signal = on_signal
        self._lock = threading.Lock()
        self._last: float | None = None
        self._last_callback: float | None = None

    def sign(self) -> None:
        """A heartbeat line arrived. Calls ``on_signal`` at most once per interval."""
        now = time.monotonic()
        with self._lock:
            self._last = now
            call = self._on_signal is not None and (
                self._last_callback is None or now - self._last_callback >= _SIGNAL_CALLBACK_INTERVAL_S
            )
            if call:
                self._last_callback = now
        if call:
            assert self._on_signal is not None
            try:
                self._on_signal()
            except Exception:  # noqa: BLE001 -- a failing callback must not end the reader
                LOGGER.exception("ssh transport: the sign-of-life callback failed")

    def verdict(self, now: float) -> str | None:
        """``"timeout"``, ``"hard_cap"``, ``"stalled"`` or ``None`` (the call may go on)."""
        with self._lock:
            last = self._last
        if last is None:
            return "timeout" if now >= self._started + self._timeout_s else None
        if now >= self._started + self._hard_cap_s:
            return "hard_cap"
        if self._stall_s is not None and now - last > self._stall_s:
            return "stalled"
        return None

    def next_check(self, now: float) -> float:
        """Seconds until the nearest instant at which :meth:`verdict` could change."""
        with self._lock:
            last = self._last
        if last is None:
            return self._started + self._timeout_s - now
        nearest = self._started + self._hard_cap_s
        if self._stall_s is not None:
            nearest = min(nearest, last + self._stall_s)
        return nearest - now


def _drain(stream, sink: bytearray, cap: int, on_overflow) -> None:
    total = 0
    try:
        while True:
            chunk = stream.read(65536)
            if not chunk:
                return
            total += len(chunk)
            room = cap - len(sink)
            if room > 0:
                sink.extend(chunk[:room])
            if total > cap and on_overflow is not None:
                on_overflow()
                return
    except (OSError, ValueError):
        return


def _drain_with_heartbeats(stream, sink: bytearray, cap: int, liveness: _Liveness) -> None:
    """Read stderr as it arrives, line by line; a whole heartbeat line is a sign of life.

    Every other byte is kept (bounded by ``cap``, as :func:`_drain` keeps it) and is **not** a sign
    of life. A heartbeat line is dropped from ``sink``: over two hours there are hundreds of them,
    and they would push the lines that explain a failure out of the bounded text. A line that grows
    past :data:`_HEARTBEAT_MAX_LINE_BYTES` before its end is kept as it is and, with the rest of
    that line, never recognised. A last line without a terminator is not whole.
    """

    pending = bytearray()
    overlong = False

    def keep(data: bytes) -> None:
        room = cap - len(sink)
        if room > 0:
            sink.extend(data[:room])

    try:
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            rest = chunk
            while rest:
                end = rest.find(b"\n")
                if end < 0:
                    pending.extend(rest)
                    if len(pending) > _HEARTBEAT_MAX_LINE_BYTES:
                        keep(bytes(pending))
                        pending.clear()
                        overlong = True
                    break
                pending.extend(rest[:end])
                rest = rest[end + 1 :]
                line = bytes(pending)
                pending.clear()
                was_overlong, overlong = overlong, False
                if not was_overlong and HEARTBEAT_LINE.fullmatch(line):
                    liveness.sign()
                else:
                    keep(line + b"\n")
    except (OSError, ValueError):
        pass
    if pending:
        keep(bytes(pending))


def _wait_live(process: subprocess.Popen, liveness: _Liveness) -> str | None:
    """Wait for ``process`` to exit or for the first limit of ``liveness``; kill it at a limit.

    Returns which limit cut the call (``"timeout"``, ``"stalled"``, ``"hard_cap"``) or ``None``.
    """

    while True:
        now = time.monotonic()
        cut = liveness.verdict(now)
        if cut is not None:
            with contextlib.suppress(OSError):
                process.kill()
            process.wait()
            return cut
        try:
            process.wait(timeout=max(0.001, min(_LIVE_TICK_S, liveness.next_check(now))))
        except subprocess.TimeoutExpired:
            continue
        return None


def _run_bounded(
    argv: Sequence[str],
    *,
    stdin_bytes: bytes,
    timeout_s: float,
    max_stdout_bytes: int,
    environment: dict[str, str],
    liveness: _Liveness | None = None,
) -> _Completed:
    try:
        process = subprocess.Popen(  # noqa: S603 -- argv is built from validated parts, shell is not used
            list(argv),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            bufsize=0,
            close_fds=True,
            start_new_session=True,
        )
    except FileNotFoundError as error:
        raise SshFailure("protocol_error", f"{argv[0]} is not installed", sent=False) from error
    except OSError as error:
        raise SshFailure("protocol_error", f"cannot start {argv[0]}: {type(error).__name__}", sent=False) from error

    stdout_sink, stderr_sink = bytearray(), bytearray()
    overflow = threading.Event()

    def stop_on_overflow() -> None:
        overflow.set()
        with contextlib.suppress(OSError):
            process.kill()

    def feed() -> None:
        try:
            if stdin_bytes:
                view = memoryview(stdin_bytes)
                while view:
                    view = view[os.write(process.stdin.fileno(), view) :]
        except OSError:
            pass  # the remote closed its stdin early; the exit status tells the rest
        finally:
            with contextlib.suppress(OSError):
                process.stdin.close()

    if liveness is None:
        stderr_thread = threading.Thread(
            target=_drain, args=(process.stderr, stderr_sink, _STDERR_CAPTURE_BYTES, None), daemon=True,
        )
    else:
        stderr_thread = threading.Thread(
            target=_drain_with_heartbeats, args=(process.stderr, stderr_sink, _STDERR_CAPTURE_BYTES, liveness),
            daemon=True,
        )
    threads = [
        threading.Thread(target=feed, daemon=True),
        threading.Thread(target=_drain, args=(process.stdout, stdout_sink, max_stdout_bytes, stop_on_overflow), daemon=True),
        stderr_thread,
    ]
    timed_out = False
    cut: str | None = None
    try:
        for thread in threads:
            thread.start()
        if liveness is None:
            try:
                process.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                with contextlib.suppress(OSError):
                    process.kill()
                process.wait()
        else:
            cut = _wait_live(process, liveness)
            timed_out = cut == "timeout"
    finally:
        if process.poll() is None:  # an exception (KeyboardInterrupt): never leave our child behind
            with contextlib.suppress(OSError):
                process.kill()
            process.wait()
        for thread in threads:
            thread.join(timeout=5)
        for stream in (process.stdout, process.stderr):
            with contextlib.suppress(OSError):
                stream.close()
    return _Completed(
        process.returncode, bytes(stdout_sink), bytes(stderr_sink), timed_out, overflow.is_set(),
        stalled=cut == "stalled", hard_capped=cut == "hard_cap",
    )


# --------------------------------------------------------------------------------------------
# ssh_command
# --------------------------------------------------------------------------------------------


def _connect_timeout(timeout_s: float) -> int:
    """ssh's own connect/handshake bound: below the call deadline, so a stuck connect is ssh's
    typed "timed out" (nothing sent) and not our wall-clock kill (command may have run)."""
    return min(10, max(1, int(timeout_s) - 1))


def run_command(
    endpoint: SshEndpoint,
    private_key_pem: str | bytes,
    host_key_line: str | None,
    stdin_bytes: bytes,
    timeout_s: float,
    max_output_bytes: int,
    *,
    live_hard_cap_s: float | None = None,
    live_stall_s: float | None = None,
    on_signal: Callable[[], None] | None = None,
) -> tuple[bytes, str]:
    """Run the forced command once: ``stdin_bytes`` in, ``(stdout, scrubbed stderr)`` out.

    ``timeout_s`` bounds the whole call (connect, command, answer). Output beyond
    ``max_output_bytes`` kills the connection. Raises ``SshFailure``; see the module doc for
    ``outcome`` and ``sent``.

    The three keyword parameters switch on the signs of life (`AR-V3-LIVENESS-01`; see the module
    doc). With ``live_hard_cap_s`` the call is *live* from the first heartbeat line on stderr:
    ``timeout_s`` no longer bounds it, it is cut as ``hard_cap`` ``live_hard_cap_s`` seconds after
    it started, and -- when ``live_stall_s`` is given -- as ``stalled`` once more than
    ``live_stall_s`` seconds pass since the latest heartbeat. ``on_signal`` is called for the
    heartbeats, at most once a second, from the thread that reads stderr; it must be quick and
    must not raise (a raise is logged and ignored). Without ``live_hard_cap_s`` the other two are
    not read and the call is exactly what it was.
    """

    if timeout_s <= 0 or max_output_bytes <= 0:
        raise ValueError("timeout_s and max_output_bytes must be positive")
    if live_hard_cap_s is not None and live_hard_cap_s < 0:
        raise ValueError("live_hard_cap_s must not be negative")
    if live_stall_s is not None and live_stall_s <= 0:
        raise ValueError("live_stall_s must be positive")
    with _session_files(endpoint, private_key_pem, host_key_line) as files:
        argv = build_ssh_argv(
            endpoint,
            key_path=files.key_path,
            known_hosts_path=files.known_hosts_path,
            connect_timeout_s=_connect_timeout(timeout_s),
        )
        secrets = _key_secrets(private_key_pem, files.key_path)
        liveness = None if live_hard_cap_s is None else _Liveness(
            started=time.monotonic(), timeout_s=timeout_s, hard_cap_s=live_hard_cap_s,
            stall_s=live_stall_s, on_signal=on_signal,
        )
        completed = _run_bounded(
            argv,
            stdin_bytes=bytes(stdin_bytes),
            timeout_s=timeout_s,
            max_stdout_bytes=max_output_bytes,
            environment=_child_environment(files.key_path.parent),
            liveness=liveness,
        )
    stderr = scrub_stderr(completed.stderr, secrets)
    if completed.timed_out:
        raise SshFailure("timeout", f"no answer within {timeout_s:g} s; the command may have run. {stderr}", sent=True)
    if completed.stalled:
        raise SshFailure(
            "stalled", f"no sign of life for more than {live_stall_s:g} s; the command may have run. {stderr}", sent=True,
        )
    if completed.hard_capped:
        raise SshFailure(
            "hard_cap", f"the call reached its ceiling of {live_hard_cap_s:g} s; the command may have run. {stderr}",
            sent=True,
        )
    if completed.stdout_overflow:
        raise SshFailure("protocol_error", f"stdout exceeded {max_output_bytes} bytes. {stderr}", sent=True)
    if completed.status == 0:
        return completed.stdout, stderr
    if completed.status == 255:
        classified = _classify_ssh_error(completed.stderr.decode("utf-8", errors="replace"))
        if classified is not None:
            outcome, sent = classified
            raise SshFailure(outcome, stderr, sent=sent, exit_status=255)
        # ssh failed in a way we do not recognise: the command may or may not have started.
        raise SshFailure("protocol_error", f"ssh exited 255. {stderr}", sent=True, exit_status=255)
    raise SshFailure(
        "protocol_error",
        f"remote command exit status {completed.status}. {stderr}",
        sent=True,
        exit_status=completed.status,
    )


# --------------------------------------------------------------------------------------------
# Host-key scan (probe only)
# --------------------------------------------------------------------------------------------


def scan_host_key(endpoint: SshEndpoint, timeout: float = 10) -> str:
    """Read the host key with ``ssh-keyscan``. Probe only: never call it on a call path.

    Returns the observed key as ``keytype base64`` (the form that goes into a revision's
    ``host_key``); ``host_key_fingerprint`` gives the value to show. Prefers ed25519, then
    ecdsa, then rsa. Raises ``SshFailure`` (``unreachable`` or ``timeout``, ``sent=False``)
    when no key is returned.
    """

    if timeout <= 0:
        raise ValueError("timeout must be positive")
    argv = [
        "ssh-keyscan",
        "-T", str(max(1, int(timeout))),
        "-p", str(endpoint.port),
        "-t", "ed25519,ecdsa,rsa",
        endpoint.host,
    ]
    completed = _run_bounded(
        argv, stdin_bytes=b"", timeout_s=timeout * 3 + 2, max_stdout_bytes=64 * 1024, environment=_child_environment()
    )
    if completed.timed_out:
        raise SshFailure("timeout", "host key scan timed out", sent=False)
    found: dict[str, str] = {}
    for raw_line in completed.stdout.decode("utf-8", errors="replace").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        try:
            normalised = normalise_host_key_line(raw_line)
        except HostKeyFormatError:
            continue
        found.setdefault(normalised.split(" ", 1)[0], normalised)
    for key_type in _SCAN_PREFERENCE:
        if key_type in found:
            return found[key_type]
    if found:
        return next(iter(found.values()))
    stderr_text = completed.stderr.decode("utf-8", errors="replace")
    classified = _classify_ssh_error(stderr_text)
    outcome = classified[0] if classified and classified[0] in ("timeout", "unreachable") else "unreachable"
    raise SshFailure(outcome, f"no host key observed. {scrub_stderr(stderr_text)}", sent=False)


# --------------------------------------------------------------------------------------------
# ssh_tunnel
# --------------------------------------------------------------------------------------------


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _port_accepts(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def _terminate(process: subprocess.Popen) -> None:
    """Stop our own child: SIGTERM, then SIGKILL after five seconds. Never by pattern."""
    if process.poll() is None:
        with contextlib.suppress(OSError):
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(OSError):
                process.kill()
            process.wait()


@contextlib.contextmanager
def open_tunnel(
    endpoint: SshEndpoint,
    private_key_pem: str | bytes,
    host_key_line: str | None,
    remote_host: str,
    remote_port: int,
    timeout_s: float = 15,
) -> Iterator[int]:
    """Hold ``ssh -N -L 127.0.0.1:<port>:remote_host:remote_port`` open and yield ``<port>``.

    Ready means a TCP connect to the local port succeeds (ssh listens only after it has
    authenticated against the pinned key). The readiness connect reaches the remote target and
    closes at once; that is harmless for an HTTP server. On exit the ssh process this call started
    is terminated by PID. A failure to establish raises ``SshFailure`` with ``sent=False``: no
    request travelled. The tunnel dying later shows as a refused connection to the caller.
    """

    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    with _session_files(endpoint, private_key_pem, host_key_line) as files:
        secrets = _key_secrets(private_key_pem, files.key_path)
        environment = _child_environment(files.key_path.parent)
        deadline = time.monotonic() + timeout_s
        process: subprocess.Popen | None = None
        local_port = 0
        stderr_sink = bytearray()
        drain: threading.Thread | None = None
        try:
            for _attempt in range(3):
                local_port = _free_loopback_port()
                argv = build_ssh_argv(
                    endpoint,
                    key_path=files.key_path,
                    known_hosts_path=files.known_hosts_path,
                    connect_timeout_s=_connect_timeout(timeout_s),
                    forward=(local_port, remote_host, remote_port),
                )
                stderr_sink = bytearray()
                try:
                    process = subprocess.Popen(  # noqa: S603 -- validated argv, no shell
                        argv,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        env=environment,
                        bufsize=0,
                        close_fds=True,
                        start_new_session=True,
                    )
                except OSError as error:
                    raise SshFailure("protocol_error", f"cannot start ssh: {type(error).__name__}", sent=False) from error
                drain = threading.Thread(
                    target=_drain, args=(process.stderr, stderr_sink, _STDERR_CAPTURE_BYTES, None), daemon=True
                )
                drain.start()
                port_taken = False
                while True:
                    if process.poll() is not None:
                        drain.join(timeout=5)
                        text = bytes(stderr_sink).decode("utf-8", errors="replace")
                        if "Address already in use" in text or "cannot listen to port" in text:
                            port_taken = True
                            break
                        classified = _classify_ssh_error(text)
                        outcome = classified[0] if classified else "protocol_error"
                        raise SshFailure(
                            outcome, f"the tunnel did not open. {scrub_stderr(text, secrets)}", sent=False,
                            exit_status=process.returncode,
                        )
                    if _port_accepts(local_port):
                        break
                    if time.monotonic() >= deadline:
                        raise SshFailure("timeout", f"the tunnel was not ready within {timeout_s:g} s", sent=False)
                    time.sleep(0.05)
                if not port_taken:
                    break
                with contextlib.suppress(OSError):
                    process.stderr.close()
                process = None
            else:
                raise SshFailure("protocol_error", "no free local port for the tunnel", sent=False)
            yield local_port
        finally:
            if process is not None:
                _terminate(process)
                if drain is not None:
                    drain.join(timeout=5)
                with contextlib.suppress(OSError):
                    process.stderr.close()


# --------------------------------------------------------------------------------------------
# The sealing destination (plan 4.1)
# --------------------------------------------------------------------------------------------


def ssh_destination(transport: str, endpoint: SshEndpoint, origin: str = "") -> str:
    """The associated-data destination, ``transport|ssh_endpoint|origin`` (plan 4.1).

    ``ssh_command|host:port|`` for SSH, and ``ssh_tunnel|host:port|scheme://host:port`` for a
    tunnelled ``http_api``, so a changed SSH endpoint unbinds the key even when the tunnelled
    origin stays ``http://localhost:11434``.
    """

    if transport == "ssh_command":
        if origin:
            raise ValueError("an ssh_command destination has no origin")
        return f"ssh_command|{endpoint.address}|"
    if transport == "ssh_tunnel":
        if not origin or "|" in origin or not re.fullmatch(r"[a-z][a-z0-9+.-]*://\S+", origin):
            raise ValueError("an ssh_tunnel destination needs an origin of the form scheme://host:port")
        return f"ssh_tunnel|{endpoint.address}|{origin}"
    raise ValueError(f"not an ssh transport: {transport!r}")
