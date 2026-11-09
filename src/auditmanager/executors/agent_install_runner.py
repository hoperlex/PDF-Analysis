"""The worker's half of path A: install the universal agent on a host over SSH (`EXEC2-ENROLL-SSH-01`,
ADR-0026 decision 7, owner ruling `R-149b`).

The API records an install session (``agent_install.py``) and the worker that holds the private ring takes it
from there, after the pattern of ``probe_runner.py``: only the worker opens a sealed key, and the connection goes
over the worker's own network path. A session runs

``requested -> scanning -> awaiting_host_key -> (the administrator confirms) -> installing -> succeeded | failed``

and a session that is not finished :data:`~auditmanager.executors.agent_install.INSTALL_SESSION_SECONDS` after its
creation is ended by the API's own sweep (``no_worker`` / ``timed_out``); a late write of this module finds the
session ended and changes nothing.

The durable claim
-----------------
Nothing about who holds a session is kept in memory.

* ``requested -> scanning`` is one statement (``FOR UPDATE SKIP LOCKED``), and ``scanning`` is stored. A scan only
  reads a public key, so a session left ``scanning`` with no key for two minutes -- its worker is gone -- is
  scanned again by the next pass (``STALE_SCAN_SECONDS``).
* ``installing`` has no second state, so the claim of an install is the **enrollment grant itself**: the grant is
  issued by ``issue_executor_enrollment`` under the idempotency key ``agent-install:<install_id>``, and the command
  ledger's ``UNIQUE (command_type, idempotency_key)`` lets exactly one caller issue it. A worker that finds the key
  taken -- another worker, or this one before a restart -- **never installs**: it leaves the session alone (its
  grant may have been spent). The claim is committed *before* the install connection is made, and before it only
  read-only acts happen (the key is opened in memory, the host key is read again and compared). A worker that dies
  after its claim leaves the session ``installing``; it ends by its lifetime as ``timed_out``, and the grant's
  ledger row names the grant that was issued for it. An install is never started twice. (A command type of its own
  would have needed a classification in ``scripts/recovery/product_purge.py``, which this task does not own.)
  A small in-memory set of the sessions this process is working on only saves repeated reads; it decides nothing.
  A worker that has **not** won the grant never ends the session: the failure branches before the grant (the reads of
  :meth:`~AgentInstallRunner._ready`, the host-key comparison, a refused grant, an unexpected error) end it only after
  locking the session's row and finding no grant in the ledger, and :meth:`~AgentInstallRunner._grant` takes the same
  row lock before it issues the grant -- so a worker that lost the race for a session, or read it too early, cannot end
  a session whose install another worker is running, and an end and a grant never both succeed.

What the worker does, and in which order
----------------------------------------
``scanning``
    The target passes the **same** :class:`~auditmanager.executors.destinations.DestinationPolicy` as every
    executor destination (plan T-9) *before any connection*; the SSH client is then pointed at the validated
    address, never at the name again. A private range is refused (the ``ssh_command`` transport) unless the stand's
    administrator set ``AUDITMANAGER_AGENT_INSTALL_ALLOW_PRIVATE=1`` (`R-149g`), which asks the rules about the
    ``vpn`` transport instead, for the scan and the install alike; loopback, link-local, the compose network and
    service names are refused either way. The host key is read (``ssh-keyscan``), stored write-once and shown to the
    administrator as a fingerprint. Nothing is trusted on first use.
``installing``
    1. before the network and before any write: the confirmed fingerprint is checked against the stored key; the
       package is loaded from the image and must be the one the session recorded (version and sha256); the
       stand's public origin (``AUDITMANAGER_PUBLIC_ORIGIN``) must be configured -- if not, the session fails, an
       origin is **never guessed**; the destination is checked again; the sealed key is opened for the endpoint it
       was sealed for;
    2. the host key is read again and must equal the confirmed one (``host_key_changed`` otherwise);
    3. only then an **enrollment grant** is issued with ``issue_executor_enrollment`` for the session's
       connection, journaled as an administrator's issue would be and attributed to the session's creator, so
       that its fifteen minutes are spent on the install and a host that is not contacted gets no grant;
    4. one SSH call, pinned to the stored key with ``StrictHostKeyChecking=yes``, runs the fixed bootstrap
       (:data:`REMOTE_COMMAND`) with the payload on stdin, and the bootstrap runs the package's own ``install.sh``
       with ``sudo -n`` -- the very script, from the very bytes, that path B's copied command runs
       (``--package FILE --sha256 DIGEST`` makes ``install.sh`` verify the archive itself);
    5. the session ends and its sealed key is replaced; a success is believed only when the grant was redeemed.
       The bootstrap removes the stand's ``authorized_keys`` line (the ``auditmanager-install:<install_id>``
       comment) on the way out, whatever the outcome.

How the secret travels
----------------------
The enrollment secret is on **no argument vector**, local or remote. The remote command is constant text (the
bootstrap script, with no value interpolated into it). The secret, the stand's origin, the pinned model, the
package's digest and size and the key line's marker are the first seven lines of the call's **stdin**, the
package archive follows them byte for byte; the bootstrap reads the lines with ``read``, validates each, and hands
the secret to ``install.sh`` as an environment variable assigned in front of ``sudo`` (``--preserve-env`` names
variables and takes no value) -- the same way path B's command does.

Nothing here puts a key, a secret, a fingerprint, a command line or a host's output in an event, a log line or an
error detail; a failure is one value of ``ExecutorAgentInstallFailure`` and the log line names the session, that
value and nothing else. The remote bootstrap sends nothing to the stand but three fixed status lines
(:func:`key_line_state`).

Limits (stated, not hidden)
---------------------------
* The login shell of the SSH user must be a POSIX shell (bash, dash, zsh, ksh) and ``bash``, ``sudo`` without a
  password (``sudo -n``), ``tar``, ``sha256sum`` and the coreutils must be there (``unsupported_platform`` /
  ``sudo_password_required`` otherwise). ``sudo`` must let the user keep the three named variables, as path B's
  command needs too.
* ``authorized_keys`` is looked for at ``~/.ssh/authorized_keys``. A line elsewhere (``AuthorizedKeysFile``) is
  reported as remaining, in the journal; the private half is destroyed either way.
* The sealed ciphertext is a frozen column; "destroyed" is *replaced and no longer named by the session*.
* A worker that stops while it installs leaves a session that ends as ``timed_out``; the agent may already be
  installed and enrolled. Retrying issues a new grant and revokes the old one (``revoke_unredeemed``).
"""

from __future__ import annotations

import contextlib
import logging
import os
import re
import subprocess
import threading
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final, Protocol

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.executors.agent_install import (
    INSTALL_SESSION_SECONDS,
    install_destination,
    install_marker,
    observed_fingerprint,
)
from auditmanager.executors.agent_install_repository import AgentInstallRepository, InstallRecord
from auditmanager.executors.agent_package import (
    AgentPackage,
    load_package,
    package_directory,
    resolve_origin,
)
from auditmanager.executors.destinations import (
    DestinationPolicy,
    DestinationRefused,
    DestinationUnresolvable,
)
from auditmanager.executors.enrollment import issue_executor_enrollment
from auditmanager.executors.host_commands import issue_host_grant
from auditmanager.executors.host_repository import HostRepository
from auditmanager.executors.enrollment_repository import EnrollmentRepository
from auditmanager.executors.model import CONFLICT_ENROLLMENT_SHOWN_ONCE, host_key_fingerprint
from auditmanager.executors.public import SecretUnreadableError, open_secret
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.sealing import PrivateRing
from auditmanager.executors.ssh_transport import (
    HostKeyFormatError,
    SshEndpoint,
    SshFailure,
    build_ssh_argv,
    known_hosts_line,
    normalise_host_key_line,
    private_key_file,
    scan_host_key,
)
from auditmanager.ingest.public import CommandRepository
from auditmanager.jobs.public import append_execution_event
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey

__all__ = [
    "ALLOW_PRIVATE_ENV",
    "EXIT_FAILURES",
    "FAILURES",
    "GRANT_COMMAND_TYPE",
    "INSTALL_THREADS",
    "INSTALL_TRANSPORT",
    "PRIVATE_INSTALL_TRANSPORT",
    "PUBLIC_ORIGIN_ENV",
    "REMOTE_COMMAND",
    "AgentInstallRunner",
    "InstallTransport",
    "RemoteResult",
    "SshInstallTransport",
    "allow_private_targets",
    "build_payload",
    "failure_for",
    "grant_key",
    "install_runner_for",
    "key_line_state",
]

_log = logging.getLogger(__name__)

_AGGREGATE_INSTALL: Final[str] = "ExecutorAgentInstall"
#: The environment variable the API reads for the same value (``composition.PUBLIC_ORIGIN_ENV``): the stand's
#: public origin. The worker needs it too, because it issues the grant and tells ``install.sh`` where the stand is.
PUBLIC_ORIGIN_ENV: Final[str] = "AUDITMANAGER_PUBLIC_ORIGIN"
#: The ledger's command type of an enrollment grant (``enrollment.issue_executor_enrollment`` begins it) and the
#: idempotency key under which the worker issues the grant of one session: the claim of the install.
GRANT_COMMAND_TYPE: Final[str] = "issue_executor_enrollment"


def grant_key(install_id: str) -> str:
    """The idempotency key of the grant that claims ``install_id``'s install."""
    return f"agent-install:{install_id}"


#: What the destination rules call this connection: the transport of an ``ssh_command`` connection. A private
#: range is therefore refused, as it is for a model's SSH endpoint; ``vpn`` would allow it. This is the default.
INSTALL_TRANSPORT: Final[str] = "ssh_command"
#: `R-149g`. The one stand setting that lets path A reach a private range (RFC 1918, unique-local, shared address
#: space): ``1`` or ``0``, unset is ``0``. It is read once, when the runner is built, so the scan and the install of
#: every session make the same choice. Only the worker reads it (``compose.server.yml`` forwards it to that service).
ALLOW_PRIVATE_ENV: Final[str] = "AUDITMANAGER_AGENT_INSTALL_ALLOW_PRIVATE"
#: What the destination rules are asked when the setting is ``1``: the ``vpn`` transport, the only one that accepts a
#: private range. Loopback, link-local (the metadata address included), unspecified, multicast and reserved
#: addresses, the compose network and a single-label or local name stay refused for it as for every transport, and
#: ``AUDITMANAGER_EXECUTOR_ALLOWED_HOSTS`` still narrows.
PRIVATE_INSTALL_TRANSPORT: Final[str] = "vpn"


def allow_private_targets(environ: Mapping[str, str]) -> bool:
    """:data:`ALLOW_PRIVATE_ENV`: ``1`` allows a private-range target, ``0`` or unset or blank refuses it.

    Anything else is **not** read as a yes: the stand then behaves as if the setting were ``0`` -- the narrower
    rule -- and says so in the log, naming the variable and never its value. (A relaxation that a typo could
    switch on, or a worker that a typo could stop, would both be worse than a refused target.)"""
    raw = environ.get(ALLOW_PRIVATE_ENV, "").strip()
    if raw == "1":
        return True
    if raw not in ("", "0"):
        _log.warning("%s is neither 1 nor 0; private-range targets stay refused for agent installs",
                     ALLOW_PRIVATE_ENV)
    return False


#: Sessions worked on at the same time (one thread each). An install takes minutes; the probe loop that calls
#: the runner must not wait for it.
INSTALL_THREADS: Final[int] = 4
#: Sessions the runner takes in one pass, and how many ``installing`` rows it looks at to find one it can claim.
CLAIM_BATCH: Final[int] = 4
CANDIDATES: Final[int] = 8
SCAN_TIMEOUT_SECONDS: Final[float] = 10.0
#: The longest one install call may take (upload, ``install.sh``'s own settle time, the enrollment exchange), and
#: the least time left in the session's life for which it is started at all.
INSTALL_CALL_SECONDS: Final[float] = 480.0
MIN_INSTALL_SECONDS: Final[float] = 60.0
_OUTPUT_LIMIT: Final[int] = 4096

# -- the failure reasons (``ExecutorAgentInstallFailure``) ---------------------------------------------

FAILURE_HOST_UNREACHABLE: Final[str] = "host_unreachable"
FAILURE_SSH_REFUSED: Final[str] = "ssh_refused"
FAILURE_HOST_KEY_CHANGED: Final[str] = "host_key_changed"
FAILURE_HOST_KEY_NOT_CONFIRMED: Final[str] = "host_key_not_confirmed"
FAILURE_SUDO_PASSWORD: Final[str] = "sudo_password_required"
FAILURE_UNSUPPORTED_PLATFORM: Final[str] = "unsupported_platform"
FAILURE_PACKAGE_UNAVAILABLE: Final[str] = "package_unavailable"
FAILURE_INSTALL_FAILED: Final[str] = "install_failed"
FAILURE_ENROLLMENT_FAILED: Final[str] = "enrollment_failed"
FAILURE_SECRET_UNREADABLE: Final[str] = "secret_unreadable"
FAILURE_TIMED_OUT: Final[str] = "timed_out"
#: The reasons this module can end a session with (``no_worker`` is the API sweep's alone).
FAILURES: Final[tuple[str, ...]] = (
    FAILURE_HOST_UNREACHABLE, FAILURE_SSH_REFUSED, FAILURE_HOST_KEY_CHANGED, FAILURE_HOST_KEY_NOT_CONFIRMED,
    FAILURE_SUDO_PASSWORD, FAILURE_UNSUPPORTED_PLATFORM, FAILURE_PACKAGE_UNAVAILABLE, FAILURE_INSTALL_FAILED,
    FAILURE_ENROLLMENT_FAILED, FAILURE_SECRET_UNREADABLE, FAILURE_TIMED_OUT,
)

#: What the remote exit status means. ``install.sh``'s own codes (its header): 64 usage, 65 package missing or its
#: digest wrong, 66 a prerequisite missing, 69 the stand could not be reached, 77 not root, 78 the secret or the
#: origin refused, 1 anything else. The bootstrap's own are 81 to 87 (:data:`_BOOTSTRAP`), chosen not to meet them.
EXIT_FAILURES: Final[Mapping[int, str]] = {
    64: FAILURE_INSTALL_FAILED,
    65: FAILURE_PACKAGE_UNAVAILABLE,
    66: FAILURE_UNSUPPORTED_PLATFORM,
    69: FAILURE_ENROLLMENT_FAILED,
    77: FAILURE_INSTALL_FAILED,
    78: FAILURE_ENROLLMENT_FAILED,
    # the bootstrap: input malformed, upload short, digest wrong on the host, archive does not unpack, a tool is
    # missing, sudo needs a password, sudo will not keep the named variables.
    81: FAILURE_INSTALL_FAILED,
    82: FAILURE_INSTALL_FAILED,
    83: FAILURE_PACKAGE_UNAVAILABLE,
    84: FAILURE_PACKAGE_UNAVAILABLE,
    85: FAILURE_UNSUPPORTED_PLATFORM,
    86: FAILURE_SUDO_PASSWORD,
    87: FAILURE_INSTALL_FAILED,
}


def failure_for(exit_status: int | None) -> str:
    """The sanitised reason for a remote exit status: the table, and ``install_failed`` for any other."""
    return EXIT_FAILURES.get(-1 if exit_status is None else exit_status, FAILURE_INSTALL_FAILED)


# -- the remote bootstrap ---------------------------------------------------------------------------
#
# Constant text. It is the *remote command*: nothing from the UI, the database or the call is interpolated into
# it. It holds no single quote (it is handed to the login shell inside single quotes, so it cannot contain one),
# and it is read by the login shell of the SSH user, which must be a POSIX shell. Every value it works on is read
# from stdin and validated before use.

_BOOTSTRAP: Final[str] = r"""
set -u
umask 077
{ set +x; set +v; } 2>/dev/null
export LC_ALL=C

say() { printf "am-install: %s\n" "$1"; }
rd() { IFS= read -r "$1" || exit 81; }

rd magic
[ "$magic" = "AM-INSTALL/1" ] || exit 81
rd secret
rd origin
rd model
rd sha
rd size
rd marker
[[ $marker =~ ^(-|auditmanager-install:exai_[0-9A-HJKMNP-TV-Z]{26})$ ]] || exit 81

work=""
status=0

drop_line() {
  local f d tmp n left
  [ "$marker" = "-" ] && return 0
  if [ -z "${HOME:-}" ]; then say "key-line not-removed"; return 0; fi
  f=$(readlink -f -- "$HOME/.ssh/authorized_keys" 2>/dev/null) || f=""
  if [ -z "$f" ] || [ ! -f "$f" ]; then say "key-line absent"; return 0; fi
  n=$(awk -v m="$marker" "\$NF == m { c++ } END { print c + 0 }" "$f" 2>/dev/null) || n=""
  case "$n" in
    0) say "key-line absent"; return 0 ;;
    "" | *[!0-9]*) say "key-line not-removed"; return 0 ;;
  esac
  d="${f%/*}"
  tmp=$(mktemp "$d/.am-install.XXXXXX" 2>/dev/null) || { say "key-line not-removed"; return 0; }
  if awk -v m="$marker" "\$NF != m" "$f" > "$tmp" 2>/dev/null; then
    chmod --reference="$f" -- "$tmp" 2>/dev/null
    if mv -f -- "$tmp" "$f" 2>/dev/null; then
      left=$(awk -v m="$marker" "\$NF == m { c++ } END { print c + 0 }" "$f" 2>/dev/null) || left=""
      if [ "$left" = "0" ]; then say "key-line removed"; return 0; fi
    fi
  fi
  rm -f -- "$tmp" 2>/dev/null
  say "key-line not-removed"
  return 0
}

finish() {
  status=$?
  trap - EXIT
  if [ -n "$work" ]; then cd / 2>/dev/null; rm -rf -- "$work" 2>/dev/null; fi
  drop_line
  exit "$status"
}
on_signal() { exit 129; }
trap finish EXIT
trap on_signal HUP INT TERM

[[ $secret =~ ^ame_[0-9a-z]{8}_[A-Za-z0-9_-]{43}$ ]] || exit 81
[[ $origin =~ ^https?://[A-Za-z0-9.-]+(:[0-9]{1,5})?$ ]] || exit 81
[[ $model =~ ^[A-Za-z0-9._-]{1,64}$ ]] || exit 81  # "-" is no model: a host agent (`HOSTS-BACKEND-01`, ADR-0028 decision 1)
[[ $sha =~ ^[0-9a-f]{64}$ ]] || exit 81
[[ $size =~ ^[0-9]{1,8}$ ]] || exit 81
[ "$size" -gt 0 ] && [ "$size" -le 33554432 ] || exit 81

for tool in awk bash head mktemp readlink rm sha256sum sudo tar wc; do
  command -v "$tool" >/dev/null 2>&1 || exit 85
done
sudo -n true </dev/null >/dev/null 2>&1 || exit 86
AUDITMANAGER_STAND_ORIGIN=$origin sudo -n --preserve-env=AUDITMANAGER_STAND_ORIGIN true </dev/null >/dev/null 2>&1 || exit 87

work=$(mktemp -d 2>/dev/null) || exit 85
cd "$work" || exit 85
head -c "$size" > agent.tar.gz || exit 82
[ "$(wc -c < agent.tar.gz)" -eq "$size" ] || exit 82
printf "%s  agent.tar.gz\n" "$sha" | sha256sum -c - >/dev/null 2>&1 || exit 83
tar -xzf agent.tar.gz </dev/null >/dev/null 2>&1 || exit 84
[ -f install.sh ] || exit 84

if [ "$model" = "-" ]; then
  AUDITMANAGER_ENROLLMENT_SECRET=$secret AUDITMANAGER_STAND_ORIGIN=$origin \
    sudo -n --preserve-env=AUDITMANAGER_ENROLLMENT_SECRET,AUDITMANAGER_STAND_ORIGIN \
    bash install.sh --package agent.tar.gz --sha256 "$sha" </dev/null >/dev/null 2>&1
else
  AUDITMANAGER_ENROLLMENT_SECRET=$secret AUDITMANAGER_STAND_ORIGIN=$origin AUDITMANAGER_AGENT_MODEL=$model \
    sudo -n --preserve-env=AUDITMANAGER_ENROLLMENT_SECRET,AUDITMANAGER_STAND_ORIGIN,AUDITMANAGER_AGENT_MODEL \
    bash install.sh --package agent.tar.gz --sha256 "$sha" </dev/null >/dev/null 2>&1
fi
rc=$?
secret=""
if [ "$rc" -eq 0 ]; then say "installed"; fi
exit "$rc"
"""

#: The remote command: ``bash`` runs the bootstrap, which reads its work from stdin. Nothing is interpolated.
REMOTE_COMMAND: Final[str] = "bash --noprofile --norc -c '" + _BOOTSTRAP + "'"

_MAGIC: Final[str] = "AM-INSTALL/1"
#: The three status lines the bootstrap may print about the stand's key line, and nothing else it prints is read.
_KEY_LINE_STATES: Final[Mapping[bytes, str]] = {
    b"am-install: key-line removed": "host_line_removed",
    b"am-install: key-line absent": "host_line_remains",
    b"am-install: key-line not-removed": "host_line_remains",
}

_SECRET_SHAPE: Final[re.Pattern[str]] = re.compile(r"ame_[0-9a-z]{8}_[A-Za-z0-9_-]{43}")
#: What ``install.sh`` accepts as an origin (its header). Narrower than ``agent_package.normalise_origin``: a
#: bracketed IPv6 origin passes the stand's check and not the script's, so it is refused here, before a grant.
_SCRIPT_ORIGIN: Final[re.Pattern[str]] = re.compile(r"https?://[A-Za-z0-9.-]+(:[0-9]{1,5})?")
_MODEL: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9._-]{1,64}")
_DIGEST: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")
_MARKER: Final[re.Pattern[str]] = re.compile(r"-|auditmanager-install:exai_[0-9A-HJKMNP-TV-Z]{26}")
_MAX_ARCHIVE_BYTES: Final[int] = 32 * 1024 * 1024


def build_payload(
    *, secret: str, origin: str, model: str, sha256: str, archive: bytes, marker: str
) -> bytes:
    """The call's stdin: seven lines -- magic, secret, origin, model, digest, size, marker -- then the archive.

    Every field is checked against the shape the bootstrap checks, so a value the bootstrap would refuse is
    refused here, before anything leaves the stand. ``marker`` is ``-`` for a pasted key (the administrator's own
    line, which the stand does not remove) and :func:`install_marker` for a generated one. ``ValueError`` names
    the field and never the value."""
    for name, pattern, value in (
        ("secret", _SECRET_SHAPE, secret), ("origin", _SCRIPT_ORIGIN, origin), ("model", _MODEL, model),
        ("sha256", _DIGEST, sha256), ("marker", _MARKER, marker),
    ):
        if pattern.fullmatch(value) is None:
            raise ValueError(f"the install payload's {name} is not of the declared form")
    if not 0 < len(archive) <= _MAX_ARCHIVE_BYTES:
        raise ValueError("the install payload's archive is empty or too large")
    header = "\n".join((_MAGIC, secret, origin, model, sha256, str(len(archive)), marker)) + "\n"
    return header.encode("ascii") + archive


def key_line_state(stdout: bytes) -> str | None:
    """What the bootstrap said about the stand's ``authorized_keys`` line: ``host_line_removed``,
    ``host_line_remains`` or ``None`` (it said nothing: it never got that far, or the key is the administrator's
    own). Only the three fixed status lines are read; any other byte of the output is ignored."""
    seen: str | None = None
    for line in stdout.splitlines():
        state = _KEY_LINE_STATES.get(line.strip())
        if state is not None:
            seen = state
    return seen


# -- the SSH seam ----------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RemoteResult:
    """What one install call came to. ``outcome`` is ``completed`` (the remote command ran and exited: read
    ``exit_status``), or why it did not: ``host_key_changed``, ``refused`` (the key was refused),
    ``unreachable``, ``timed_out`` (the command may have run), ``broken`` (anything else)."""

    outcome: str
    exit_status: int | None = None
    stdout: bytes = field(default=b"", repr=False)


class InstallTransport(Protocol):
    """The two network acts of an install. A test substitutes a scripted host; production is
    :class:`SshInstallTransport`."""

    def scan(self, endpoint: SshEndpoint) -> str:
        """The host key as ``keytype base64``; raises :class:`SshFailure` when none is observed."""
        ...

    def execute(
        self, endpoint: SshEndpoint, private_key: str, host_key: str, payload: bytes, *, timeout_s: float
    ) -> RemoteResult:
        """Run :data:`REMOTE_COMMAND` with ``payload`` on stdin, pinned to ``host_key``."""
        ...


#: Order matters: a changed key before the verification failure a changed key also prints. The needles are the
#: OpenSSH client's, as ``ssh_transport`` classifies them (its classifier is private to that module).
_SSH_REFUSALS: Final[tuple[tuple[tuple[str, ...], str], ...]] = (
    (("REMOTE HOST IDENTIFICATION HAS CHANGED", "Host key for ", "POSSIBLE DNS SPOOFING",
      "Host key verification failed", "No host key is known", "host key is not known"), "host_key_changed"),
    (("Permission denied", "Too many authentication failures", "Authentication failed", "Load key "), "refused"),
    (("Connection refused", "Could not resolve hostname", "Name or service not known",
      "Temporary failure in name resolution", "No route to host", "Network is unreachable", "Host is down",
      "timed out", "Timed out"), "unreachable"),
)


@dataclass(frozen=True, slots=True)
class _Process:
    status: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool


def _environment(home: Path) -> dict[str, str]:
    """A minimal environment: no agent socket, no proxy variables, English messages."""
    return {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "LC_ALL": "C", "LANG": "C",
            "HOME": str(home)}


def _run_process(argv: list[str], stdin: bytes, timeout_s: float, environment: dict[str, str]) -> _Process:
    """Run ``argv`` with ``stdin``, at most ``timeout_s`` seconds, keeping a bounded amount of its output."""
    try:
        process = subprocess.Popen(  # noqa: S603 - argv is built from validated parts; no shell
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
            bufsize=0, close_fds=True, start_new_session=True,
        )
    except OSError:
        return _Process(None, b"", b"", False)
    pipe_in, pipe_out, pipe_err = process.stdin, process.stdout, process.stderr
    assert pipe_in is not None and pipe_out is not None and pipe_err is not None
    stdout, stderr = bytearray(), bytearray()

    def feed() -> None:
        try:
            view = memoryview(stdin)
            while view:
                view = view[os.write(pipe_in.fileno(), view):]
        except OSError:
            pass  # the remote closed its stdin early; the exit status tells the rest
        finally:
            with contextlib.suppress(OSError):
                pipe_in.close()

    def drain(stream: Any, sink: bytearray) -> None:
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    return
                room = _OUTPUT_LIMIT - len(sink)
                if room > 0:
                    sink.extend(chunk[:room])
        except (OSError, ValueError):
            return

    threads = [threading.Thread(target=feed, daemon=True),
               threading.Thread(target=drain, args=(pipe_out, stdout), daemon=True),
               threading.Thread(target=drain, args=(pipe_err, stderr), daemon=True)]
    timed_out = False
    try:
        for thread in threads:
            thread.start()
        try:
            process.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            with contextlib.suppress(OSError):
                process.kill()
            process.wait()
    finally:
        if process.poll() is None:  # an exception: never leave our child behind
            with contextlib.suppress(OSError):
                process.kill()
            process.wait()
        for thread in threads:
            thread.join(timeout=5)
        for stream in (pipe_out, pipe_err):
            with contextlib.suppress(OSError):
                stream.close()
    return _Process(process.returncode, bytes(stdout), bytes(stderr), timed_out)


def _write_private(path: Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, data)
    finally:
        os.close(descriptor)


class SshInstallTransport:
    """The production transport: the OpenSSH client, driven through ``ssh_transport``'s public functions.

    ``ssh_transport.run_command`` names no remote command (a forced command decides there), and an install must
    name one, so this builds the invocation with :func:`build_ssh_argv` -- the same hermetic options: no config
    file, one identity, one pinned known-hosts line, ``StrictHostKeyChecking=yes``, public-key only, no
    forwarding -- and appends :data:`REMOTE_COMMAND`. The key lives in a private tmpfs directory for the length of
    the call (:func:`private_key_file`). Neither the key, the payload nor the remote's output is logged."""

    def scan(self, endpoint: SshEndpoint) -> str:
        return scan_host_key(endpoint, timeout=SCAN_TIMEOUT_SECONDS)

    def execute(
        self, endpoint: SshEndpoint, private_key: str, host_key: str, payload: bytes, *, timeout_s: float
    ) -> RemoteResult:
        try:
            pin = known_hosts_line(endpoint, host_key)
            with private_key_file(private_key) as key_path:
                known_hosts = key_path.parent / "known_hosts"
                _write_private(known_hosts, (pin + "\n").encode("ascii"))
                argv = build_ssh_argv(
                    endpoint, key_path=key_path, known_hosts_path=known_hosts,
                    connect_timeout_s=min(10.0, timeout_s),
                )
                argv.append(REMOTE_COMMAND)
                run = _run_process(argv, payload, timeout_s, _environment(key_path.parent))
        except HostKeyFormatError:
            return RemoteResult("broken")  # a stored key that is not a key: nothing can be pinned to it
        except SshFailure as failure:
            return RemoteResult("refused" if failure.outcome == "credential_refused" else "broken")
        except OSError:
            return RemoteResult("broken")
        if run.timed_out:
            return RemoteResult("timed_out")
        if run.status is None:
            return RemoteResult("broken")
        if run.status != 255:
            return RemoteResult("completed", exit_status=run.status, stdout=run.stdout)
        text = run.stderr.decode("utf-8", errors="replace")
        for needles, outcome in _SSH_REFUSALS:
            if any(needle in text for needle in needles):
                return RemoteResult(outcome)
        return RemoteResult("broken")


# -- the runner -----------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Work:
    kind: str  # "scan" or "install"
    record: InstallRecord

    @property
    def from_state(self) -> str:
        return "scanning" if self.kind == "scan" else "installing"


#: What :meth:`AgentInstallRunner._grant` answers besides a prepared install or a failure reason: the session is
#: no longer ``installing``, or its grant was issued by another caller. Neither is a value of
#: ``ExecutorAgentInstallFailure``, and neither ends the session.
_GONE: Final[str] = "gone"
_TAKEN: Final[str] = "taken"


@dataclass(frozen=True, slots=True)
class _Ready:
    """What an install needs from the database and the image before the network: the session as it now stands,
    the one validated address, the package, the stand's origin and the opened key (a secret: no repr, and it lives for
    the length of one install). The pinned model is **not** here: it is read again in the transaction that issues the
    grant (:meth:`AgentInstallRunner._grant`), so the payload never names a model older than the grant."""

    record: InstallRecord
    address: str
    package: AgentPackage
    archive: bytes = field(repr=False)
    origin: str
    configured: str | None
    key: str = field(repr=False)


@dataclass(slots=True)
class _Held:
    """Whether the thread working on a session has won its grant. Confined to that thread and never stored: it only
    tells the end of an unexpected failure whether the claim is this worker's (then the session is ended) or still
    unknown (then the ledger and the row lock say whether somebody else holds it)."""

    granted: bool = False


@dataclass(frozen=True, slots=True)
class _Prepared:
    """A :class:`_Ready` install with its grant issued and its payload built. The key and the payload are
    secrets: they have no repr."""

    record: InstallRecord
    endpoint: SshEndpoint
    enrollment_id: str
    key: str = field(repr=False)
    payload: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class _Outcome:
    """How the network part came out: the failure reason (``None`` for the remote command's success) and what
    became of the stand's ``authorized_keys`` line."""

    reason: str | None
    key_line: str | None = None


class AgentInstallRunner:
    """Callable by the worker service: ``runner()`` takes what is waiting and returns how many sessions it took.

    Each session is worked on in a thread of its own (at most :data:`INSTALL_THREADS` at once), so the loop that
    calls the runner goes on with probes. Transactions are short and none is open during a network call."""

    def __init__(
        self, session_factory: sessionmaker[Session], *, ring: PrivateRing | None, policy: DestinationPolicy,
        environ: Mapping[str, str], transport: InstallTransport | None = None,
        installs: AgentInstallRepository | None = None, executors: ExecutorRepository | None = None,
        enrollments: EnrollmentRepository | None = None, commands: CommandRepository | None = None,
        journal: Callable[..., None] = append_execution_event,
        issue_grant: Callable[..., Any] = issue_executor_enrollment,
        open_key: Callable[..., str] = open_secret,
        load: Callable[..., tuple[AgentPackage, bytes]] = load_package,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        batch: int = CLAIM_BATCH,
    ) -> None:
        self._sessions: Callable[[], AbstractContextManager[Session]] = session_factory
        self._ring = ring
        self._policy = policy
        self._environ = dict(environ)
        #: `R-149g`: the transport the destination rules are asked about, for the scan and the install alike.
        self._destination_transport: str = (
            PRIVATE_INSTALL_TRANSPORT if allow_private_targets(self._environ) else INSTALL_TRANSPORT)
        self._transport: InstallTransport = transport or SshInstallTransport()
        self._installs = installs or AgentInstallRepository()
        self._executors = executors or ExecutorRepository()
        self._enrollments = enrollments or EnrollmentRepository()
        self._commands = commands or CommandRepository()
        self._journal = journal
        self._issue_grant = issue_grant
        self._open_key = open_key
        self._load = load
        self._clock = clock
        self._batch = batch
        self._threads: set[threading.Thread] = set()
        #: The sessions this process is working on: saves repeated reads, decides nothing (see the module note).
        self._working: set[str] = set()
        self._lock = threading.Lock()

    def __call__(self) -> int:
        return self.run_pending()

    # -- taking work ------------------------------------------------------------------------
    def run_pending(self) -> int:
        taken = 0
        for _ in range(self._batch):
            if self._free_threads() <= 0:
                break
            work = self._claim()
            if work is None:
                break
            self._start(work)
            taken += 1
        return taken

    def join(self, timeout: float | None = None) -> None:
        """Wait for the sessions in flight (a test, or an orderly stop)."""
        with self._lock:
            threads = list(self._threads)
        for thread in threads:
            thread.join(timeout)

    def _free_threads(self) -> int:
        with self._lock:
            self._threads = {thread for thread in self._threads if thread.is_alive()}
            return INSTALL_THREADS - len(self._threads)

    def _start(self, work: _Work) -> None:
        thread = threading.Thread(
            target=self._guarded, args=(work,), name=f"auditmanager-agent-install-{work.record.install_id}",
            daemon=True,
        )
        with self._lock:
            self._threads.add(thread)
            self._working.add(work.record.install_id)
        thread.start()

    def _claim(self) -> _Work | None:
        """One short transaction: a ``requested`` session moves to ``scanning`` (the durable claim of a scan), or
        an ``installing`` session that nobody has claimed is picked (its claim is the grant, made later, by
        :meth:`_grant`). The scan's claim is committed before anything is done with it."""
        with self._sessions() as session:
            record = self._installs.claim_requested(session, seconds=INSTALL_SESSION_SECONDS)
            if record is not None:
                session.commit()
                return _Work("scan", record)
            for candidate in self._installs.installing(
                session, seconds=INSTALL_SESSION_SECONDS, limit=CANDIDATES,
            ):
                if self._unclaimed(session, candidate):
                    return _Work("install", candidate)
        return None

    def _unclaimed(self, session: Session, record: InstallRecord) -> bool:
        """``False`` when the session is being worked on here, or its grant -- the claim -- has been issued."""
        with self._lock:
            if record.install_id in self._working:
                return False
        found = self._commands.find(
            session, command_type=GRANT_COMMAND_TYPE, idempotency_key=IdempotencyKey(grant_key(record.install_id)))
        return found is None

    # -- one session ------------------------------------------------------------------------
    def _guarded(self, work: _Work) -> None:
        held = _Held()
        try:
            if work.kind == "scan":
                self._scan(work)
            else:
                self._install(work, held)
        except Exception as failure:  # noqa: BLE001 - recorded, never raised into the loop
            # The class name only: a message can carry anything, a key included.
            _log.error("agent install %s failed unexpectedly (%s)", work.record.install_id,
                       type(failure).__name__)
            try:
                # An install that has not won the grant may be another worker's: it ends the session only if nobody
                # holds the claim. A scan is claimed by its stored state, so its worker always ends it.
                self._end(work, work.record, FAILURE_INSTALL_FAILED,
                          unless_claimed=work.kind == "install" and not held.granted)
            except Exception as again:  # noqa: BLE001
                _log.error("agent install %s could not be ended (%s)", work.record.install_id,
                           type(again).__name__)
        finally:
            with self._lock:
                self._working.discard(work.record.install_id)

    def _address(self, record: InstallRecord) -> str | None:
        """The one validated address to connect to, or ``None`` when the destination rules refuse the target
        (or it does not resolve). The name is resolved and every address classified; the connection is then made
        to the address, never to the name again (``DestinationPolicy.check``). The transport it asks about is
        :data:`INSTALL_TRANSPORT`, or :data:`PRIVATE_INSTALL_TRANSPORT` when the stand allows private targets
        (:data:`ALLOW_PRIVATE_ENV`); the scan and the install both come through here, so they cannot differ. The
        log carries the refusal's closed category and nothing else."""
        try:
            addresses = self._policy.check(
                record.ssh_host, record.ssh_port, transport=self._destination_transport)
        except DestinationRefused as refused:
            _log.warning("agent install %s: destination refused (%s)", record.install_id, refused.category)
            return None
        except (DestinationUnresolvable, ValueError, OSError):
            _log.warning("agent install %s: destination does not resolve", record.install_id)
            return None
        return addresses[0] if addresses else None

    def _remaining(self, record: InstallRecord) -> float:
        """Seconds left in the session's life (:data:`INSTALL_SESSION_SECONDS` from its creation)."""
        return (record.created_at + timedelta(seconds=INSTALL_SESSION_SECONDS) - self._clock()).total_seconds()

    # -- scanning ---------------------------------------------------------------------------
    def _scan(self, work: _Work) -> None:
        """``scanning -> awaiting_host_key``: check the destination, read the host key, store it."""
        record = work.record
        address = self._address(record)
        if address is None:
            self._end(work, record, FAILURE_HOST_UNREACHABLE)
            return
        try:
            endpoint = SshEndpoint(address, record.ssh_port, record.ssh_user)
            observed = normalise_host_key_line(self._transport.scan(endpoint))
        except (SshFailure, HostKeyFormatError, ValueError):
            self._end(work, record, FAILURE_HOST_UNREACHABLE)
            return
        with self._sessions() as session:
            moved = self._installs.record_observed_host_key(session, record.install_id, host_key=observed)
            if moved:
                self._journal(
                    session, event_type="executor.agent_install_host_key_observed",
                    aggregate_type=_AGGREGATE_INSTALL, aggregate_id=record.install_id,
                    payload={**_owner(record), "state": "awaiting_host_key"},
                )
            session.commit()
        _log.info("agent install %s: %s", record.install_id,
                  "awaiting the host key's confirmation" if moved else "already ended")

    # -- installing -------------------------------------------------------------------------
    def _install(self, work: _Work, held: _Held | None = None) -> None:
        """``installing``, in four steps with a transaction around each database step and none around a network
        one: everything the database and the image must say (:meth:`_ready`); the host key read again and
        compared (:meth:`_verify_host`); the grant -- the claim -- issued as late as possible so that its fifteen
        minutes are spent on the install (:meth:`_grant`); the install itself (:meth:`_execute`).

        Until the grant is won this worker holds nothing: every failure before it ends the session only when no
        other worker holds the grant (``unless_claimed``). ``held`` is told when the grant is won."""
        ready = self._ready(work)
        if ready is None:  # no longer installing: somebody ended it
            _log.info("agent install %s: already ended", work.record.install_id)
            return
        if isinstance(ready, str):
            self._end(work, work.record, ready, unless_claimed=True)
            return
        endpoint, failure = self._verify_host(ready)
        if failure is not None or endpoint is None:
            self._end(work, ready.record, failure or FAILURE_HOST_UNREACHABLE, unless_claimed=True)
            return
        prepared = self._grant(ready, endpoint)
        record = ready.record
        del ready
        if isinstance(prepared, str):
            if prepared in (_GONE, _TAKEN):  # nothing to end: somebody else ended it, or holds the claim
                _log.info("agent install %s: %s", record.install_id,
                          "already ended" if prepared == _GONE else "claimed by another worker")
            else:
                self._end(work, record, prepared, unless_claimed=True)  # the grant was not committed: not ours
            return
        if held is not None:
            held.granted = True
        enrollment_id = prepared.enrollment_id
        outcome = self._execute(prepared)
        del prepared  # the key and the payload end with the call
        self._end(work, record, outcome.reason, key_line=outcome.key_line, enrollment_id=enrollment_id)

    def _ready(self, work: _Work) -> _Ready | str | None:
        """Read what the install needs and refuse what it cannot do, before any network and before any write.

        Returns the :class:`_Ready` install, the failure reason that ends the session, or ``None`` when the
        session is no longer ``installing``. Nothing is written: the session closes without a commit."""
        with self._sessions() as session:
            record = self._installs.get_install(session, work.record.install_id)
            if record is None or record.state != "installing":
                return None
            if (record.observed_host_key is None or record.confirmed_host_key_fingerprint is None
                    or observed_fingerprint(record) != record.confirmed_host_key_fingerprint):
                return FAILURE_HOST_KEY_NOT_CONFIRMED
            if self._remaining(record) < MIN_INSTALL_SECONDS:
                return FAILURE_TIMED_OUT
            if record.package_version is None or record.package_sha256 is None:
                return FAILURE_PACKAGE_UNAVAILABLE
            try:
                package, archive = self._load(
                    record.package_version, directory=package_directory(self._environ))
            except DomainError:
                return FAILURE_PACKAGE_UNAVAILABLE
            if package.sha256 != record.package_sha256:
                return FAILURE_PACKAGE_UNAVAILABLE  # the image changed since the session was recorded
            configured = self._environ.get(PUBLIC_ORIGIN_ENV) or None
            try:
                origin = resolve_origin(configured)
            except DomainError:
                # Never a guess: a command that names no reachable stand is no command.
                _log.warning("agent install %s: the stand's public origin is not configured", record.install_id)
                return FAILURE_ENROLLMENT_FAILED
            if _SCRIPT_ORIGIN.fullmatch(origin) is None:
                return FAILURE_ENROLLMENT_FAILED
            if record.host_id is not None:
                # A host install asks for no model (`HOSTS-BACKEND-01`): only that the host is still there.
                host = HostRepository().get_host(session, record.host_id)
                if host is None or host.archived_at is not None:
                    return FAILURE_ENROLLMENT_FAILED
            else:
                connection = self._executors.get_connection(session, record.connection_id)
                revision = self._executors.current_revisions(session, [record.connection_id]).get(
                    record.connection_id)
                if (connection is None or connection.archived_at is not None or connection.kind != "pull"
                        or revision is None or _MODEL.fullmatch(revision.settings.gateway_model) is None):
                    return FAILURE_ENROLLMENT_FAILED
            address = self._address(record)
            if address is None:
                return FAILURE_HOST_UNREACHABLE
            if record.key_secret_id is None:
                return FAILURE_SECRET_UNREADABLE
            try:
                key = self._open_key(
                    session, self._ring, secret_id=record.key_secret_id,
                    destination=install_destination(
                        ssh_host=record.ssh_host, ssh_port=record.ssh_port, ssh_user=record.ssh_user),
                    repository=self._executors,
                )
            except SecretUnreadableError:
                return FAILURE_SECRET_UNREADABLE
            return _Ready(
                record=record, address=address, package=package, archive=archive, origin=origin,
                configured=configured, key=key,
            )

    def _verify_host(self, ready: _Ready) -> tuple[SshEndpoint | None, str | None]:
        """Read the host key again, now, and require it to be the one the administrator confirmed. Returns the
        endpoint to connect to, or the failure reason. No trust is placed in what is read: it is only compared."""
        record = ready.record
        try:
            endpoint = SshEndpoint(ready.address, record.ssh_port, record.ssh_user)
            seen = normalise_host_key_line(self._transport.scan(endpoint))
        except (SshFailure, HostKeyFormatError, ValueError):
            return None, FAILURE_HOST_UNREACHABLE
        if host_key_fingerprint(seen) != record.confirmed_host_key_fingerprint:
            return None, FAILURE_HOST_KEY_CHANGED
        return endpoint, None

    def _grant(self, ready: _Ready, endpoint: SshEndpoint) -> _Prepared | str:
        """Issue the enrollment grant -- the claim of the install -- and build the payload, in one transaction
        that commits both.

        The grant is ``issue_executor_enrollment`` -- the rules, the journal and the one-grant-per-connection
        revocation of an administrator's issue -- attributed to the session's creator, under the idempotency key
        of the session (:func:`grant_key`). A key already taken is ``conflict`` / ``enrollment_shown_once``: the
        session is another worker's (:data:`_TAKEN`). Returns the prepared install, the failure reason, or
        :data:`_GONE` when the session is no longer ``installing``.

        The session's row is locked first (:meth:`_claimed_elsewhere` takes the same lock before it reads the
        ledger), so a worker that gave up before the grant cannot end the session between this worker's read of
        the state and its commit of the grant. The model the payload names is read **here**, after the grant
        has locked the connection and in the same transaction, so a revision of the connection cannot slip in
        between the model and the grant: the payload never carries a model older than the grant."""
        with self._sessions() as session:
            record = self._installs.get_install(session, ready.record.install_id, lock=True)
            if record is None or record.state != "installing":
                return _GONE
            try:
                if record.host_id is not None:
                    issued = issue_host_grant(
                        session, host_id=record.host_id, roles=("admin",),
                        idempotency_key=grant_key(record.install_id), actor_uid=record.created_by,
                        configured_origin=ready.configured, grants=self._enrollments, commands=self._commands,
                        package_source=lambda: ready.package, journal=self._journal,
                    )
                    model = "-"  # no model: the bootstrap installs a host agent
                else:
                    issued = self._issue_grant(
                        session, connection_id=record.connection_id, roles=("admin",),
                        idempotency_key=grant_key(record.install_id), actor_uid=record.created_by,
                        configured_origin=ready.configured, executors=self._executors,
                        repository=self._enrollments, commands=self._commands,
                        package_source=lambda: ready.package, journal=self._journal,
                    )
                    current = self._executors.current_revisions(session, [record.connection_id]).get(
                        record.connection_id)
                    if current is None or _MODEL.fullmatch(current.settings.gateway_model) is None:
                        return FAILURE_ENROLLMENT_FAILED  # not committed: the grant is rolled back with it
                    model = current.settings.gateway_model
                payload = build_payload(
                    secret=issued.secret, origin=ready.origin, model=model,
                    sha256=ready.package.sha256, archive=ready.archive,
                    marker=install_marker(record.install_id) if record.access == "generated_key" else "-",
                )
            except DomainError as refused:
                if (refused.code == ErrorCode.CONFLICT
                        and refused.detail_fields.get("conflict_reason") == CONFLICT_ENROLLMENT_SHOWN_ONCE):
                    return _TAKEN
                return FAILURE_ENROLLMENT_FAILED
            except ValueError:
                return FAILURE_ENROLLMENT_FAILED
            self._journal(
                session, event_type="executor.agent_install_started", aggregate_type=_AGGREGATE_INSTALL,
                aggregate_id=record.install_id,
                payload={**_owner(record), "state": "installing", "actor_uid": record.created_by},
            )
            session.commit()
            return _Prepared(
                record=record, endpoint=endpoint, enrollment_id=issued.record.enrollment_id, key=ready.key,
                payload=payload,
            )

    def _execute(self, prepared: _Prepared) -> _Outcome:
        """The install call, pinned to the stored host key. No database transaction is open."""
        record = prepared.record
        observed = record.observed_host_key
        remaining = self._remaining(record)
        if observed is None:
            return _Outcome(FAILURE_HOST_KEY_NOT_CONFIRMED)
        if remaining < MIN_INSTALL_SECONDS:
            return _Outcome(FAILURE_TIMED_OUT)
        result = self._transport.execute(
            prepared.endpoint, prepared.key, observed, prepared.payload,
            timeout_s=min(INSTALL_CALL_SECONDS, remaining - 5.0),
        )
        key_line = key_line_state(result.stdout)
        if result.outcome == "completed":
            return _Outcome(None if result.exit_status == 0 else failure_for(result.exit_status), key_line)
        reasons = {
            "host_key_changed": FAILURE_HOST_KEY_CHANGED, "refused": FAILURE_SSH_REFUSED,
            "unreachable": FAILURE_HOST_UNREACHABLE, "timed_out": FAILURE_TIMED_OUT,
        }
        return _Outcome(reasons.get(result.outcome, FAILURE_INSTALL_FAILED), key_line)

    # -- the end ----------------------------------------------------------------------------
    def _claimed_elsewhere(self, session: Session, record: InstallRecord) -> bool:
        """Has another worker won the grant of this session? Locks the session's row first and then reads the
        ledger: :meth:`_grant` holds the same row lock while it issues the grant, so a grant in flight is waited for
        and then seen, and a grant not yet begun finds the session ended. Used only by a worker that has **not** won
        the grant itself -- it must never end a session whose install somebody else is running."""
        self._installs.get_install(session, record.install_id, lock=True)
        return self._commands.find(
            session, command_type=GRANT_COMMAND_TYPE, idempotency_key=IdempotencyKey(grant_key(record.install_id)),
        ) is not None

    def _end(
        self, work: _Work, record: InstallRecord, reason: str | None, *, key_line: str | None = None,
        enrollment_id: str | None = None, unless_claimed: bool = False,
    ) -> None:
        """End the session -- ``failed`` with ``reason``, ``succeeded`` when ``reason`` is ``None`` -- replace
        its key and journal it, in one transaction.

        A success is believed only when the grant the call carried was **redeemed**: ``install.sh`` can exit 0
        on a host that already holds a token while it refuses the new secret. A session somebody else already
        ended (the API's sweep) is left as it was written: the update names the state it moves the session from.

        ``unless_claimed`` is for a worker that has not won the grant (see :meth:`_claimed_elsewhere`): when the
        ledger holds the session's grant it is another worker's install, and this one leaves it alone."""
        state = "succeeded" if reason is None else "failed"
        with self._sessions() as session:
            if unless_claimed and self._claimed_elsewhere(session, record):
                _log.info("agent install %s: claimed by another worker", record.install_id)
                return
            if reason is None and enrollment_id is not None:
                grant = self._enrollments.get_enrollment(session, enrollment_id)
                if grant is None or grant.redeemed_at is None:
                    reason, state = FAILURE_ENROLLMENT_FAILED, "failed"
            ended = self._installs.finish_install(
                session, install_id=record.install_id, connection_id=record.connection_id,
                from_state=work.from_state, state=state, reason=reason,
                **({} if record.host_id is None else {"host_id": record.host_id}),
            )
            if ended:
                self._journal_end(session, record, state, reason, work.from_state, key_line)
            session.commit()
        if ended:
            _log.info("agent install %s: %s%s", record.install_id, state,
                      "" if reason is None else f" ({reason})")
        else:
            _log.info("agent install %s: already ended", record.install_id)

    def _journal_end(
        self, session: Session, record: InstallRecord, state: str, reason: str | None, from_state: str,
        key_line: str | None,
    ) -> None:
        """The event of the end, and of the key's end: identities and controlled values only."""
        payload: dict[str, str | int | bool | None] = {
            **_owner(record), "from_state": from_state, "to_state": state,
        }
        if record.key_secret_id is not None:
            payload["secret_id"] = record.key_secret_id
        if reason is not None:
            payload["reason"] = reason
        self._journal(
            session, event_type=f"executor.agent_install_{state}", aggregate_type=_AGGREGATE_INSTALL,
            aggregate_id=record.install_id, payload=payload,
        )
        if record.key_secret_id is None:
            return
        # Whether the stand's line is off the host: only a generated key has a line of the stand's.
        removal = (key_line or "host_line_remains") if record.access == "generated_key" else "not_applicable"
        self._journal(
            session, event_type="executor.agent_install_key_removed", aggregate_type=_AGGREGATE_INSTALL,
            aggregate_id=record.install_id,
            payload={**_owner(record), "secret_id": record.key_secret_id,
                     "purpose": "agent_install_key", "reason": removal},
        )


def _owner(record: InstallRecord) -> dict[str, str]:
    """The identity an install session belongs to, as a journal payload: its connection, or -- `HOSTS-BACKEND-01` -- its host."""
    return {"host_id": record.host_id} if record.host_id is not None else {"connection_id": str(record.connection_id)}


def install_runner_for(
    session_factory: sessionmaker[Session], *, ring: Any, environ: Mapping[str, str],
) -> AgentInstallRunner:
    """The runner the composition root wires: the private ring and the environment's allowed hosts, the public
    origin and the package directory the environment names."""
    return AgentInstallRunner(
        session_factory, ring=ring, policy=DestinationPolicy.from_environment(dict(environ)), environ=environ,
    )
