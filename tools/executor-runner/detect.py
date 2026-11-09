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
    python3 detect.py --host     host mode: one line per provider the agent would report, and the state of the key file

``HOSTS-AGENT-01`` (host mode, ``RUNNER_API.md`` section 10) extends this module, and only the sources named
here are ever looked at:

* the two CLIs above, now also with the **access** they were signed in with: ``claude auth status`` prints a JSON
  document that names an account, and only its ``authMethod`` (and whether a ``subscriptionType`` is present) is
  read, the rest is dropped on the spot; ``codex login status`` says ``ChatGPT`` or ``API key``, and only that is
  read. A login method the agent does not recognise is ``auth_state: unknown``, never a guess;
* the key file (``/etc/pdf-analysis-agent/keys.env``, configurable), read **only** when it is a regular file, mode
  ``0600`` and owned by the user running this process; otherwise it is ignored and the reason is a fixed word. Of
  its lines only ``ANTHROPIC_API_KEY``, ``OPENAI_API_KEY`` and ``OPENROUTER_API_KEY`` are looked at. A key's value
  never leaves :func:`read_api_key` (it is handed to an API answerer and nowhere else); detection keeps a
  one-way fingerprint of it, in memory, to notice a rotated key, and reports only that the provider is there.

No environment variable, home directory or other user's file is scanned.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import signal
import stat
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


# ------------------------------------------------------------------ host mode (HOSTS-AGENT-01)

#: The providers of the host protocol (``RUNNER_API.md`` section 10), in report order.
PROVIDER_CLAUDE_CODE = "claude_code"
PROVIDER_CODEX = "codex"
PROVIDER_ANTHROPIC_API = "anthropic_api"
PROVIDER_OPENAI_API = "openai_api"
PROVIDER_OPENROUTER_API = "openrouter_api"
PROVIDERS = (PROVIDER_CLAUDE_CODE, PROVIDER_CODEX, PROVIDER_ANTHROPIC_API, PROVIDER_OPENAI_API, PROVIDER_OPENROUTER_API)
CLI_PROVIDER = {"claude": PROVIDER_CLAUDE_CODE, "codex": PROVIDER_CODEX}
#: The only three names ever read from the key file, and the provider each one gives.
KEY_PROVIDER = {
    "ANTHROPIC_API_KEY": PROVIDER_ANTHROPIC_API,
    "OPENAI_API_KEY": PROVIDER_OPENAI_API,
    "OPENROUTER_API_KEY": PROVIDER_OPENROUTER_API,
}
ACCESS_SUBSCRIPTION = "subscription"
ACCESS_API = "api"
DEFAULT_KEY_FILE = "/etc/pdf-analysis-agent/keys.env"
KEY_FILE_MAX_BYTES = 64 * 1024

_KEY_VALUE = re.compile(r"^[\x21-\x7e]{8,512}$")
_CHATGPT_LOGIN = re.compile(r"chatgpt", re.IGNORECASE)
_API_KEY_LOGIN = re.compile(r"api[\s_-]*key", re.IGNORECASE)
#: ``authMethod`` values of ``claude auth status``: the subscription login of claude.ai, and the API key.
_CLAUDE_SUBSCRIPTION_METHODS = frozenset({"claude.ai", "claudeai", "claude_ai", "oauth", "oauth_token", "subscription"})
_CLAUDE_API_METHODS = frozenset({"api_key", "apikey", "api-key", "console", "anthropic_api_key"})


@dataclass(frozen=True)
class CliDetails:
    """One client as host mode sees it: ``RunnerCliHealth`` plus the path (kept local unless the operator opts
    in) and the access of the login. ``access`` is ``None`` when it could not be told."""

    cli: str
    installed: bool
    path: Optional[str]
    version: Optional[str]
    auth_state: str
    access: Optional[str]

    def as_report(self) -> dict:
        return CliHealth(self.cli, self.installed, self.version, self.auth_state).as_report()


def classify_codex_login(output: bytes) -> Optional[str]:
    """``subscription`` for a ChatGPT login, ``api`` for an API-key login, else ``None``. The text is judged and
    dropped: with an API key the client may print a masked copy of it."""
    text = output.decode("utf-8", "replace")
    if _CHATGPT_LOGIN.search(text):
        return ACCESS_SUBSCRIPTION
    if _API_KEY_LOGIN.search(text):
        return ACCESS_API
    return None


def classify_claude_status(output: bytes) -> Optional[str]:
    """The access of a ``claude auth status`` document: only ``authMethod`` and the presence of a
    ``subscriptionType`` are read. Anything the agent does not recognise is ``None``."""
    try:
        document = json.loads(output.decode("utf-8", "replace").strip())
    except (ValueError, RecursionError):
        return None
    if not isinstance(document, dict):
        return None
    method = document.get("authMethod")
    method = method.strip().lower() if isinstance(method, str) else ""
    if method in _CLAUDE_API_METHODS:
        return ACCESS_API
    if method in _CLAUDE_SUBSCRIPTION_METHODS:
        return ACCESS_SUBSCRIPTION
    return None


def detect_cli_details(
    name: str,
    *,
    environ: Optional[Mapping[str, str]] = None,
    dirs: Optional[Sequence[str]] = None,
    timeout: float = COMMAND_TIMEOUT_SECONDS,
    run: Runner = _run,
) -> CliDetails:
    """Detect one client for the user running this process, with the access of its login.

    A client that is logged in with a method this module does not recognise is ``unknown``: it is not served."""
    env = os.environ if environ is None else environ
    executable = find_executable(name, search_dirs(env) if dirs is None else dirs)
    if executable is None:
        return CliDetails(name, False, None, None, AUTH_UNKNOWN, None)
    reduced = cli_environment(env)
    status, output = run([executable, "--version"], reduced, timeout, True)
    version = parse_version(output) if status == 0 else None
    auth, access = AUTH_UNKNOWN, None
    if name == "codex":
        status, output = run([executable, "login", "status"], reduced, timeout, True)
        logged_out = status is not None and _NOT_LOGGED_IN.search(output.decode("utf-8", "replace")) is not None
        if status is None:
            auth = AUTH_UNKNOWN
        elif logged_out:
            auth = AUTH_LOGIN_REQUIRED
        elif status == 0:
            access = classify_codex_login(output)
            auth = AUTH_VALID if access is not None else AUTH_UNKNOWN
    else:
        known = version_tuple(version)
        if known is not None and known >= CLAUDE_AUTH_STATUS_MIN_VERSION:
            status, output = run([executable, "auth", "status"], reduced, timeout, True)
            if status == 0:
                access = classify_claude_status(output)
                auth = AUTH_VALID if access is not None else AUTH_UNKNOWN
            elif status == 1:
                auth = AUTH_LOGIN_REQUIRED
    return CliDetails(name, True, executable, version, auth, access)


def provider_access(auth_state: str, access: Optional[str]) -> str:
    """The access a provider is reported with. A login that was classified keeps its access. A client that is not
    signed in is reported as the subscription it is meant to be signed in with; one that is signed in by a method
    the agent cannot name is reported ``api`` (the metered side) with ``auth_state: unknown`` and no verified model,
    so nothing is ever run on a guessed subscription."""
    if access is not None:
        return access
    return ACCESS_SUBSCRIPTION if auth_state == AUTH_LOGIN_REQUIRED else ACCESS_API


# ------------------------------------------------------------------------------------ the key file


@dataclass(frozen=True)
class KeyFile:
    """What the key file gives, without a single key value.

    ``present`` is whether the file exists; ``reason`` a fixed word when it exists and is **ignored** (the file is
    only read when it is a regular file, mode 0600, owned by the process user); ``providers`` the providers whose
    key is there; ``fingerprints`` a one-way digest per provider, kept in memory only to notice a rotated key
    (never reported, never logged); ``rejected`` the NAMES of keys whose value was unusable."""

    path: str
    present: bool
    reason: Optional[str]
    providers: tuple
    fingerprints: tuple  # ((provider, digest), ...)
    rejected: tuple

    @property
    def usable(self) -> bool:
        return self.present and self.reason is None

    def describe(self) -> str:
        if not self.present:
            return "absent"
        if self.reason is not None:
            return f"ignored: {self.reason}"
        return "usable: " + (",".join(self.providers) or "no key in it")


def _load_key_file(path: str, expected_uid: Optional[int]) -> "tuple[bool, Optional[str], dict, tuple]":
    """``(present, reason, {provider: value}, rejected_names)``. The values are returned to the two callers in this
    module and to nothing else."""
    uid = os.geteuid() if expected_uid is None else expected_uid
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0))
    except FileNotFoundError:
        return False, None, {}, ()
    except NotADirectoryError:
        return False, None, {}, ()
    except OSError as error:
        # ELOOP: a symbolic link (O_NOFOLLOW); anything else: not readable by this user
        return True, ("not_a_regular_file" if error.errno == errno.ELOOP else "unreadable"), {}, ()
    try:
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode):
            return True, "not_a_regular_file", {}, ()
        if details.st_uid != uid:
            return True, "not_owned_by_the_service_user", {}, ()
        if stat.S_IMODE(details.st_mode) != 0o600:
            return True, "mode_is_not_0600", {}, ()
        if details.st_size > KEY_FILE_MAX_BYTES:
            return True, "too_large", {}, ()
        raw = os.read(descriptor, KEY_FILE_MAX_BYTES + 1)
    except OSError:
        return True, "unreadable", {}, ()
    finally:
        os.close(descriptor)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return True, "not_utf8", {}, ()
    values: dict = {}
    rejected: list = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or name not in KEY_PROVIDER:
            continue  # any other line is not ours: not read, not kept, not reported
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        provider = KEY_PROVIDER[name]
        if _KEY_VALUE.fullmatch(value):
            values[provider] = value
            if name in rejected:
                rejected.remove(name)
        else:
            values.pop(provider, None)
            if name not in rejected:
                rejected.append(name)
    return True, None, values, tuple(rejected)


def read_key_file(path: str = DEFAULT_KEY_FILE, *, expected_uid: Optional[int] = None) -> KeyFile:
    """Which providers the key file gives, or why it is ignored. Holds no value."""
    present, reason, values, rejected = _load_key_file(path, expected_uid)
    ordered = [provider for provider in PROVIDERS if provider in values]
    prints = tuple((provider, hashlib.sha256(values[provider].encode("ascii")).hexdigest()[:16]) for provider in ordered)
    return KeyFile(path, present, reason, tuple(ordered), prints, rejected)


def read_api_key(provider: str, path: str = DEFAULT_KEY_FILE, *, expected_uid: Optional[int] = None) -> Optional[str]:
    """The key of one API provider, read afresh (a rotated key is used at once), under the same checks as
    :func:`read_key_file`; ``None`` when the file is ignored or holds none. The only function that returns a value;
    its caller hands it to an API answerer."""
    if provider not in KEY_PROVIDER.values():
        raise ValueError("not an API provider")
    present, reason, values, _ = _load_key_file(path, expected_uid)
    return values.get(provider) if present and reason is None else None


# ------------------------------------------------------------------------------- host detection


@dataclass(frozen=True)
class ProviderFacts:
    """What cheap detection knows of one provider. ``credential`` is a fingerprint, never reported."""

    provider: str
    access: str
    auth_state: str
    cli_path: Optional[str]
    cli_version: Optional[str]
    credential: str


@dataclass(frozen=True)
class HostDetection:
    clis: tuple          # the contract's ``clis`` array (RunnerCliHealth dicts), as for any agent
    providers: tuple     # ProviderFacts, in PROVIDERS order
    key_file: KeyFile


def detect_host(
    *,
    environ: Optional[Mapping[str, str]] = None,
    dirs: Optional[Sequence[str]] = None,
    timeout: float = COMMAND_TIMEOUT_SECONDS,
    run: Runner = _run,
    key_file: str = DEFAULT_KEY_FILE,
    expected_uid: Optional[int] = None,
) -> HostDetection:
    """Cheap detection of everything host mode serves: two CLIs and the key file. No model is called."""
    details = [detect_cli_details(name, environ=environ, dirs=dirs, timeout=timeout, run=run) for name in CLI_NAMES]
    providers: list = []
    for item in details:
        if item.installed:
            providers.append(ProviderFacts(
                CLI_PROVIDER[item.cli], provider_access(item.auth_state, item.access), item.auth_state,
                item.path, item.version, ""))
    keys = read_key_file(key_file, expected_uid=expected_uid)
    prints = dict(keys.fingerprints)
    for provider in keys.providers:
        providers.append(ProviderFacts(provider, ACCESS_API, AUTH_UNKNOWN, None, None, prints[provider]))
    providers.sort(key=lambda facts: PROVIDERS.index(facts.provider))
    return HostDetection(tuple(item.as_report() for item in details), tuple(providers), keys)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="detect.py", description="Detect the codex and claude command-line clients.")
    parser.add_argument("--json", action="store_true", help="print the contract's clis array")
    parser.add_argument("--host", action="store_true",
                        help="host mode: the providers the agent would report and the state of the key file")
    parser.add_argument("--key-file", default=DEFAULT_KEY_FILE, help="the key file --host looks at")
    args = parser.parse_args(argv)
    if args.host:
        found = detect_host(key_file=args.key_file)
        for facts in found.providers:
            print(f"{facts.provider} access={facts.access} auth={facts.auth_state} version={facts.cli_version or '-'}")
        print(f"keys file={found.key_file.path} state={found.key_file.describe()}")
        for name in found.key_file.rejected:
            print(f"keys {name} has an unusable value and is ignored")
        return 0
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
