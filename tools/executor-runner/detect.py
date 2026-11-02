#!/usr/bin/env python3
"""Detect the official command-line clients this OS user can use, and report them as enumerations.

``codex`` and ``claude`` are the only names ever looked for (``RunnerCliName`` of the contract). Each is
looked up in a fixed list of directories by absolute path and run without a shell, with a reduced
environment, a closed stdin and a time limit. What comes back is exactly the members of the contract's
``RunnerCliHealth``: ``cli``, ``installed``, ``version`` (when one was read) and ``auth_state``, one of
``valid``, ``login_required`` or ``unknown``. A path, a token, an account name or a line of the client's
own output never leaves this module (``ADR-0026`` decisions 5 and 8).

Authentication is read only through the client's own documented command, as the user running this
process; a login that exists only under another OS user is never looked for, never read and never
borrowed, so it reports ``login_required``:

* ``codex login status`` -- documented to "exit with 0 when credentials are present". Its output for the
  logged-out case is not documented, so ``login_required`` needs an exit status other than 0 **and** the
  words "not logged in" in what the client printed; any other failure is ``unknown``.
* ``claude auth status`` -- documented (code.claude.com, CLI reference) to exit 0 when logged in and 1
  when not. Its JSON output names an account and is discarded unread. Only run for a client whose version
  is at least :data:`CLAUDE_AUTH_STATUS_MIN_VERSION`: an older client could read the words as a prompt
  instead of a subcommand, so it is not asked and reports ``unknown`` (the status then has to come from a
  real probe of the connection on the stand).

A client that is not installed is ``unknown`` too (the contract's ``unknown`` covers "not installed, or
no official way to tell"). Standard library only; runs on any Python 3.9+.

    python3 detect.py            one line per client: ``claude installed=yes version=2.1.310 auth=valid``
    python3 detect.py --json     the contract's ``clis`` array
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Sequence

#: ``RunnerCliName`` of the contract, in report order. Nothing else is ever executed.
CLI_NAMES = ("claude", "codex")

AUTH_VALID = "valid"
AUTH_LOGIN_REQUIRED = "login_required"
AUTH_UNKNOWN = "unknown"

#: The directories searched, in order, after the optional override. ``<home>`` entries are the running
#: user's own: the native Claude Code installer and a per-user npm prefix put their binaries there.
SYSTEM_DIRS = ("/usr/local/bin", "/usr/bin", "/bin", "/snap/bin")
HOME_SUBDIRS = (".local/bin", ".npm-global/bin")
#: An operator with another prefix (a node version manager) names the directories here, absolute and
#: colon-separated. They replace the whole list, so a test can search nothing but a directory of its own.
DIRS_ENV = "PDF_ANALYSIS_CLI_DIRS"

COMMAND_TIMEOUT_SECONDS = 15.0
MAX_OUTPUT_BYTES = 4096
#: ``claude auth status`` is documented as a command of the CLI reference at this version (the field
#: ``configDirectory`` of its JSON "requires v2.1.268 or later"); older clients are not asked.
CLAUDE_AUTH_STATUS_MIN_VERSION = (2, 1, 268)

#: What a client may be told of this process's environment: the names the answer wrappers pass on
#: (``codex_answer.py``, ``claude_answer.py``), so detection sees the login the wrappers will use. An API
#: key or token inherited from the agent is never one of them.
ENV_ALLOWED = (
    "HOME", "LANG", "LC_ALL", "CODEX_HOME", "CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME",
    "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "SSL_CERT_FILE", "SSL_CERT_DIR",
)

_VERSION_TOKEN = re.compile(r"(?<![0-9A-Za-z.])([0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.+-]*)?)(?![0-9A-Za-z])")
#: ``RunnerCliHealth.version`` of the contract.
_VERSION_CONTRACT = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$")
_NOT_LOGGED_IN = re.compile(r"not\s+logged\s+in", re.IGNORECASE)

Runner = Callable[[Sequence[str], Mapping[str, str], float, bool], "tuple[Optional[int], bytes]"]


@dataclass(frozen=True)
class CliHealth:
    """One client's sanitised health: the members of the contract's ``RunnerCliHealth``."""

    cli: str
    installed: bool
    version: Optional[str]
    auth_state: str

    def as_report(self) -> dict:
        report: dict = {"cli": self.cli, "installed": self.installed}
        if self.version is not None:
            report["version"] = self.version
        report["auth_state"] = self.auth_state
        return report


# ------------------------------------------------------------------------------------ lookup


def search_dirs(environ: Optional[Mapping[str, str]] = None) -> list[str]:
    """The absolute directories to look in. A relative entry is dropped, never resolved against a cwd."""
    env = os.environ if environ is None else environ
    override = env.get(DIRS_ENV, "")
    if override:
        candidates = override.split(":")
    else:
        candidates = list(SYSTEM_DIRS)
        home = env.get("HOME", "")
        if home.startswith("/"):
            candidates += [os.path.join(home, part) for part in HOME_SUBDIRS]
    seen: list[str] = []
    for entry in candidates:
        if entry.startswith("/") and entry not in seen:
            seen.append(entry)
    return seen


def find_executable(name: str, dirs: Sequence[str]) -> Optional[str]:
    """The absolute path of the first executable regular file called ``name`` in ``dirs``."""
    if name not in CLI_NAMES:
        raise ValueError("only the fixed client names are looked up")
    for directory in dirs:
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def cli_environment(environ: Optional[Mapping[str, str]] = None) -> dict[str, str]:
    env = os.environ if environ is None else environ
    reduced = {name: env[name] for name in ENV_ALLOWED if name in env}
    reduced["PATH"] = ":".join(search_dirs(env))
    return reduced


def _run(argv: Sequence[str], env: Mapping[str, str], timeout: float, capture: bool) -> "tuple[Optional[int], bytes]":
    """Run ``argv`` (an absolute path and fixed words) without a shell; ``(status, output)``.

    ``status`` is ``None`` when the process could not be started or did not end in time -- it is then
    killed through its own process group, by the PID this function started. ``output`` is at most
    :data:`MAX_OUTPUT_BYTES` of stdout and stderr together, and empty unless ``capture``."""
    sink = subprocess.PIPE if capture else subprocess.DEVNULL
    try:
        process = subprocess.Popen(
            list(argv), stdin=subprocess.DEVNULL, stdout=sink, stderr=subprocess.STDOUT if capture else subprocess.DEVNULL,
            env=dict(env), cwd="/", shell=False, close_fds=True, start_new_session=True,
        )
    except (OSError, ValueError):
        return None, b""
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            process.kill()
        try:
            process.communicate(timeout=5.0)
        except (subprocess.TimeoutExpired, OSError, ValueError):
            pass
        return None, b""
    return process.returncode, (output or b"")[:MAX_OUTPUT_BYTES]


# --------------------------------------------------------------------------------- the readings


def parse_version(output: bytes) -> Optional[str]:
    """The first dotted version number in a ``--version`` line that fits the contract, else ``None``."""
    match = _VERSION_TOKEN.search(output.decode("utf-8", "replace"))
    if match is None:
        return None
    token = match.group(1)
    return token if _VERSION_CONTRACT.fullmatch(token) else None


def version_tuple(version: Optional[str]) -> Optional[tuple[int, int, int]]:
    if version is None:
        return None
    match = re.match(r"([0-9]+)\.([0-9]+)\.([0-9]+)", version)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3))) if match else None


def _codex_auth(executable: str, env: Mapping[str, str], timeout: float, run: Runner) -> str:
    status, output = run([executable, "login", "status"], env, timeout, True)
    if status is None:
        return AUTH_UNKNOWN
    text_says_logged_out = _NOT_LOGGED_IN.search(output.decode("utf-8", "replace")) is not None
    if status == 0:
        return AUTH_LOGIN_REQUIRED if text_says_logged_out else AUTH_VALID
    return AUTH_LOGIN_REQUIRED if text_says_logged_out else AUTH_UNKNOWN


def _claude_auth(executable: str, version: Optional[str], env: Mapping[str, str], timeout: float, run: Runner) -> str:
    known = version_tuple(version)
    if known is None or known < CLAUDE_AUTH_STATUS_MIN_VERSION:
        return AUTH_UNKNOWN
    status, _ = run([executable, "auth", "status"], env, timeout, False)  # the JSON names an account: unread
    if status == 0:
        return AUTH_VALID
    if status == 1:
        return AUTH_LOGIN_REQUIRED
    return AUTH_UNKNOWN


def detect_cli(
    name: str,
    *,
    environ: Optional[Mapping[str, str]] = None,
    dirs: Optional[Sequence[str]] = None,
    timeout: float = COMMAND_TIMEOUT_SECONDS,
    run: Runner = _run,
) -> CliHealth:
    """Detect one client for the user running this process."""
    env = os.environ if environ is None else environ
    executable = find_executable(name, search_dirs(env) if dirs is None else dirs)
    if executable is None:
        return CliHealth(name, False, None, AUTH_UNKNOWN)
    reduced = cli_environment(env)
    status, output = run([executable, "--version"], reduced, timeout, True)
    version = parse_version(output) if status == 0 else None
    if name == "codex":
        auth = _codex_auth(executable, reduced, timeout, run)
    else:
        auth = _claude_auth(executable, version, reduced, timeout, run)
    return CliHealth(name, True, version, auth)


def detect_all(
    *,
    environ: Optional[Mapping[str, str]] = None,
    dirs: Optional[Sequence[str]] = None,
    timeout: float = COMMAND_TIMEOUT_SECONDS,
    run: Runner = _run,
) -> list[dict]:
    """The contract's ``clis`` array, in :data:`CLI_NAMES` order."""
    return [detect_cli(name, environ=environ, dirs=dirs, timeout=timeout, run=run).as_report() for name in CLI_NAMES]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="detect.py", description="Detect the codex and claude command-line clients.")
    parser.add_argument("--json", action="store_true", help="print the contract's clis array")
    args = parser.parse_args(argv)
    clis = detect_all()
    if args.json:
        print(json.dumps(clis, separators=(",", ":")))
        return 0
    for item in clis:
        print(f"{item['cli']} installed={'yes' if item['installed'] else 'no'} "
              f"version={item.get('version', '-')} auth={item['auth_state']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
