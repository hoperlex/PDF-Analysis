"""`PROD-01-TLS-ACME-01` -- the five guards `deploy.sh` gained for the TLS terminator, each shown able to fail.

`ADR-0021` section 2 / `R-146a` / `R-146s` put the TLS terminator and its certificate renewal in the stack.
With `ALPHA_CERT_NAME` set, `deploy.sh` adds an ACME overlay (a client, and public port 80 for the challenge)
and, for a deploy that is cleared to publish and has a certificate, a second overlay (public port 443). The
guards, in the order the script asks them:

* ``acme-files-present`` -- a clone missing any file the terminator is built from is refused, and the
  refusal makes no ``docker`` call;
* ``acme-settings-well-formed`` -- the name, the yes/no values, the contact address, the ports, and the
  rule that the plain application listener stays on loopback once a name is set;
* ``acme-client-pinned`` -- ``infra/acme/client.pin`` must name a package version; the shipped word
  ``UNRESOLVED`` is refused here, in our words, before a build fails in apk's;
* ``public-ports-free`` -- the host's own nginx (or anything else) holding port 80, or 443 when this deploy
  would publish it, **on any address of the host** (``D-229`` item 1: a connect to 127.0.0.1 never saw a
  listener bound to the host's own address), is a sentence before the build and not a bind error after it;
* ``acme-pair-answerable`` -- whether the certificate volume holds a pair is asked of the volume through the
  acme image, and an unanswerable question refuses instead of reading as "no pair".

A sixth guard, ``trusted-proxies-empty-with-name`` (``JUDGE-FIXES-F2-01``, ``D-229`` item 4), is tested in
:class:`TestTrustedProxiesEmptyWithName`: a certificate name and a non-empty trust list are refused together.

**The shape of each case is ``test_deploy_script_refusals.py``'s, deliberately.** An invocation that should
trip a guard exits 3 and says why; for the guards that sit before the first ``docker`` call the evidence is
that the call log does not exist; and the same invocation against a **mutant copy with exactly that guard
block deleted** no longer produces that refusal. ``docker`` is a stub that records its arguments, answers the
reads from the environment and reaches nothing; the stub also understands a compose file LIST, because the
whole point of the lane is that ``--file`` is repeated.

**What this file does not prove**, said where it is true: that an overlay merges the way compose merges it,
that the acme image builds, that a certificate authority answers. The first is a property of docker and is
read off the files in ``test_acme_overlay.py``; the other two are the owner's staging rehearsal
(``DEPLOYMENT_RUNBOOK.md`` section 6), which this lane could not run without a network.
"""

from __future__ import annotations

import contextlib
import http.server
import os
import re
import shutil
import socket
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEPLOY_DIR = ROOT / "infra/deploy"
ACME_DIR = ROOT / "infra/acme"
DEPLOY = DEPLOY_DIR / "deploy.sh"
ENGINE = "tests/contract/api_v1/openapi_conformance.py"

REFUSED = 3

INSTANCE = "an-instance"
DATABASE = "the_configured_database"
BUCKET = "the-configured-bucket"
PG_USER = "the_configured_user"
EDITED = {
    "POSTGRES_PASSWORD": "an-edited-postgres-password",
    "MINIO_ROOT_USER": "an-edited-minio-root",
    "MINIO_ROOT_PASSWORD": "an-edited-minio-password",
    "AUDITMANAGER_API_TOKEN": "an-edited-token-that-authorizes-something",
}
#: A name no one owns and the guard accepts: not reserved, two labels, lower case. Not the live name.
NAME = "rehearsal-host.sslip.io"
#: A package version of the shape `apk policy` prints. It names nothing real; the staged tree needs only
#: its SHAPE to pass `acme-client-pinned`, and the real file keeps the word UNRESOLVED.
PINNED = "ACME_CLIENT_APK_VERSION=9.9.9-r0\n"

ACME_GUARDS = (
    "acme-files-present",
    "acme-settings-well-formed",
    "acme-client-pinned",
    "public-ports-free",
    "acme-pair-answerable",
)

#: Every file `acme-files-present` demands, relative to `infra/`. Spelled out here, not read from the script.
NEEDED = (
    "deploy/lib/proxy-listeners.sh",
    "acme/compose.acme.yml",
    "acme/Dockerfile",
    "acme/client.pin",
    "acme/entrypoint.sh",
    "acme/export-pair.sh",
    "acme/check-served.sh",
    "deploy/proxy/acme-challenge.conf",
    "deploy/proxy/tls-server.conf",
    "deploy/proxy/enable-tls.sh",
    "deploy/proxy/watch-certificate.sh",
    "deploy/proxy/compose.tls.yml",
)

# --- the `docker` this suite's script reaches ----------------------------------------------------------------
#
# `compose` is called with `--env-file E` and then one `--file F` per member of the compose file list, so the
# sub-command is the first word after the last `--file F`. The stub says which `--file`s it saw by logging the
# whole line; the cases read that line.

DOCKER_STUB = r'''#!/usr/bin/env python3
"""A `docker` that records, answers the reads, and reaches nothing."""
import os
import sys

argv = sys.argv[1:]
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as handle:
    handle.write(" ".join(argv) + "\n")


def setting(name, default=""):
    return os.environ.get(name, default)


if argv[:2] == ["image", "inspect"]:
    for suffix in [s for s in setting("STUB_MISSING_IMAGES").split(",") if s]:
        if argv[-1].endswith(suffix):
            sys.exit(1)
    sys.exit(0)

if argv[:1] == ["port"]:
    sys.stdout.write(setting("STUB_PORT_OUT"))
    sys.exit(0)

if argv[:1] == ["inspect"]:
    if argv[-1] in ("container-of-s3-init", "container-of-migrate", "container-of-release-notes"):
        sys.stdout.write("exited/0\n")
        sys.exit(0)
    if argv[-1] == "container-of-acme":
        sys.stdout.write(setting("STUB_ACME_STATE", "running/healthy") + "\n")
        sys.exit(0)
    sys.stdout.write("running/healthy\n")
    sys.exit(0)

if argv[:1] == ["compose"]:
    index = 1
    while index < len(argv):
        if argv[index] == "--env-file":
            index += 2
        elif argv[index] == "--file":
            index += 2
        else:
            break
    sub = argv[index] if index < len(argv) else ""
    rest = argv[index + 1:]
    if sub in ("build", "up"):
        sys.exit(0)
    if sub == "ps":
        service = rest[-1]
        if service == "proxy" and setting("STUB_OWN_PROXY", "1") != "1":
            sys.exit(0)
        sys.stdout.write("container-of-%s\n" % service)
        sys.exit(0)
    if sub == "run":
        joined = " ".join(rest)
        if "/export/fullchain.pem" in joined:
            sys.stdout.write(setting("STUB_PAIR", "pair-absent") + "\n")
            sys.exit(int(setting("STUB_PAIR_STATUS", "0")))
        if "auditmanager.shared.db.check" in joined:
            sys.stdout.write("FOUNDATION-CHECK OK check-db\n")
            sys.exit(0)
        if "auditmanager.access.check" in joined:
            # `PROD-02`: the credential gate, clean unless a case says otherwise. The cases about the gate
            # itself are in `test_default_credential_gate.py`.
            sys.stdout.write(setting("STUB_GATE_OUTPUT", "access-check GATE OK no published credential") + "\n")
            sys.exit(int(setting("STUB_GATE_STATUS", "0")))
        if "openapi_conformance.py" in joined:
            sys.stdin.buffer.read()
            sys.stdout.write("differences: 0\n")
            sys.exit(0)
        sys.exit(0)

sys.exit(0)
'''


class _Served(http.server.BaseHTTPRequestHandler):
    """Stands in for the published application port: `401`, as the API answers since `R-31`."""

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's spelling
        self.send_response(401)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *_: object) -> None:
        """Silence."""


@pytest.fixture()
def serving() -> Iterator[int]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Served)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def _free_port() -> int:
    """A port no socket of this host listens on, on ANY address: the wildcard bind is refused by the kernel
    while a listener holds the port on a single address, and the guard under test asks the same question."""
    with socket.socket() as probe:
        probe.bind(("0.0.0.0", 0))
        return probe.getsockname()[1]


@pytest.fixture()
def held_port() -> Iterator[int]:
    """A port something IS listening on, standing in for the host nginx that holds 80 today."""
    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    holder.listen(4)
    try:
        yield holder.getsockname()[1]
    finally:
        holder.close()


def _outward_address() -> str | None:
    """The address this host would use to reach a non-loopback destination, or ``None`` if it has none. A
    datagram ``connect`` only picks a route; no packet is sent."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 9))
            address = probe.getsockname()[0]
    except OSError:
        return None
    return None if address.startswith("127.") else address


@contextlib.contextmanager
def _listening_on(address: str) -> Iterator[int]:
    """A TCP listener bound to ONE address of this host, on a port the kernel picked. Skips the case where the
    host cannot bind that address (no IPv6, say)."""
    holder = socket.socket(socket.AF_INET6 if ":" in address else socket.AF_INET)
    try:
        holder.bind((address, 0))
        holder.listen(4)
    except OSError as exc:
        holder.close()
        pytest.skip(f"this host cannot listen on {address}: {exc}")
    try:
        yield holder.getsockname()[1]
    finally:
        holder.close()


# --- staging ----------------------------------------------------------------------------------------------------


def _dockerfile_context_paths() -> list[str]:
    paths: list[str] = []
    for name in ("Dockerfile.api", "Dockerfile.web"):
        for line in (DEPLOY_DIR / name).read_text(encoding="utf-8").splitlines():
            fields = line.split()
            if len(fields) >= 3 and fields[0].lower() == "copy" and not fields[1].startswith("--"):
                paths.extend(fields[1:-1])
    return sorted(set(paths))


def _stage(
    tmp_path: Path,
    *,
    script: Path | None = None,
    pin: str | None = PINNED,
    drop: str | None = None,
) -> Path:
    """A clone-shaped directory holding the REAL `infra/deploy` and `infra/acme` trees (so the overlay files,
    the library and the proxy files are the ones that ship), with `reload-proxy.sh` stood in for, the pin
    rewritten to a well-formed version unless the case says otherwise, and one file dropped on request."""
    repo = tmp_path / "repo"
    shutil.copytree(
        DEPLOY_DIR, repo / "infra/deploy", ignore=shutil.ignore_patterns("dumps", "alpha.env", "provider.env", "tls")
    )
    shutil.copytree(ACME_DIR, repo / "infra/acme")
    (repo / "infra/deploy/proxy/tls").mkdir(exist_ok=True)
    deploy = repo / "infra/deploy"
    if script is not None:
        (deploy / "deploy.sh").write_text(script.read_text(encoding="utf-8"), encoding="utf-8")
    if pin is not None:
        (repo / "infra/acme/client.pin").write_text(pin, encoding="utf-8")
    if drop is not None:
        (repo / "infra" / drop).unlink()
    reload_proxy = deploy / "reload-proxy.sh"
    reload_proxy.write_text('#!/bin/sh\nexit 0\n', encoding="utf-8")
    reload_proxy.chmod(0o755)
    for path in _dockerfile_context_paths():
        target = repo / path
        if path.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# staged\n", encoding="utf-8")
    engine = repo / ENGINE
    engine.parent.mkdir(parents=True, exist_ok=True)
    engine.write_text("# staged\n", encoding="utf-8")
    return deploy / "deploy.sh"


def _env(tmp_path: Path, http_port: int, **settings: str) -> Path:
    lines = [
        f"ALPHA_INSTANCE={INSTANCE}",
        f"ALPHA_HTTP_PORT={http_port}",
        f"POSTGRES_DB={DATABASE}",
        f"POSTGRES_USER={PG_USER}",
        f"S3_BUCKET={BUCKET}",
        *(f"{key}={value}" for key, value in sorted(EDITED.items())),
        f"DATABASE_URL=postgresql+psycopg://{PG_USER}:{EDITED['POSTGRES_PASSWORD']}@postgres:5432/{DATABASE}",
        f"S3_ACCESS_KEY_ID={EDITED['MINIO_ROOT_USER']}",
        f"S3_SECRET_ACCESS_KEY={EDITED['MINIO_ROOT_PASSWORD']}",
        *(f"{key}={value}" for key, value in settings.items()),
    ]
    path = tmp_path / "alpha.env"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _acme_settings(http_port: int | None = None, https_port: int | None = None, **more: str) -> dict[str, str]:
    """A configuration that passes every guard here, on ports nothing holds."""
    settings = {
        "ALPHA_CERT_NAME": NAME,
        "ALPHA_ACME_STAGING": "no",
        "ALPHA_ACME_HTTP_PORT": str(http_port or _free_port()),
        "ALPHA_HTTPS_PORT": str(https_port or _free_port()),
    }
    settings.update(more)
    return settings


def _run(
    script: Path, env_file: Path, tmp_path: Path, stub: dict[str, str] | None = None
) -> tuple[subprocess.CompletedProcess[str], Path]:
    binary = tmp_path / "bin"
    binary.mkdir(exist_ok=True)
    log = tmp_path / "docker-calls.log"
    docker = binary / "docker"
    docker.write_text(DOCKER_STUB, encoding="utf-8")
    docker.chmod(0o755)
    environment = dict(os.environ)
    environment["PATH"] = f"{binary}{os.pathsep}{environment['PATH']}"
    environment["STUB_LOG"] = str(log)
    environment["ALPHA_ENV_FILE"] = str(env_file)
    environment["STAND_COPY_RECORD"] = str(tmp_path / "stand-copy" / "record.json")
    environment["BUNDLE_STAGING"] = str(tmp_path / "stand-staging")
    environment.update(stub or {})
    completed = subprocess.run(
        ["bash", str(script)], capture_output=True, text=True, env=environment, timeout=180
    )
    return completed, log


def _mutant(tmp_path: Path, guard: str) -> Path:
    """A copy of deploy.sh with exactly one guard block deleted, staged in place."""
    source = DEPLOY.read_text(encoding="utf-8")
    block = re.compile(
        rf"^# >>> guard: {re.escape(guard)}\n.*?^# <<< guard: {re.escape(guard)}\n", re.DOTALL | re.MULTILINE
    )
    mutated, count = block.subn("", source)
    assert count == 1, f"the guard markers for {guard!r} are not a single block"
    assert mutated != source
    cut = tmp_path / "mutant.sh"
    cut.write_text(mutated, encoding="utf-8")
    return cut


def _calls(log: Path) -> list[str]:
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def _compose_calls(log: Path, sub: str) -> list[str]:
    """The `docker compose ...` lines whose sub-command (the word after the last `--file F`) is `sub`."""
    found = []
    for line in _calls(log):
        words = line.split()
        if words[:1] != ["compose"]:
            continue
        index = 1
        while index < len(words) and words[index] in ("--env-file", "--file"):
            index += 2
        if words[index : index + 1] == [sub]:
            found.append(line)
    return found


# --- acme-files-present ---------------------------------------------------------------------------------------


class TestAcmeFilesPresent:
    @pytest.mark.parametrize("missing", NEEDED)
    def test_a_clone_missing_a_terminator_file_is_refused_before_docker_is_touched(
        self, missing: str, tmp_path: Path
    ) -> None:
        script = _stage(tmp_path, drop=missing)
        completed, log = _run(script, _env(tmp_path, _free_port(), **_acme_settings()), tmp_path)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "missing files the TLS terminator is built from" in completed.stderr, completed.stderr
        assert missing.rsplit("/", 1)[1] in completed.stderr, completed.stderr
        assert not log.exists(), _calls(log)

    def test_without_a_name_the_same_clone_is_the_stack_it_always_was(self, tmp_path: Path, serving: int) -> None:
        """The condition is the name: a clone without `infra/acme/` deploys exactly as before when no name is
        set, which is the rollback and the reason the guard is conditional."""
        script = _stage(tmp_path, drop="acme/compose.acme.yml")
        completed, _ = _run(script, _env(tmp_path, serving), tmp_path)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)

    def test_that_guard_is_shown_able_to_fail(self, tmp_path: Path) -> None:
        cut = _mutant(tmp_path, "acme-files-present")
        script = _stage(tmp_path, script=cut, drop="deploy/proxy/watch-certificate.sh")
        completed, _ = _run(script, _env(tmp_path, _free_port(), **_acme_settings()), tmp_path)
        assert "missing files the TLS terminator is built from" not in completed.stderr, completed.stderr


# --- acme-settings-well-formed -------------------------------------------------------------------------------------

#: (settings, the words the refusal must contain). `{port}` is the case's own ALPHA_HTTP_PORT.
BAD_SETTINGS = {
    "a placeholder name": ({"ALPHA_CERT_NAME": "host.example.invalid"}, "reserved or documentation name"),
    "an upper-case name": ({"ALPHA_CERT_NAME": "Rehearsal.Sslip.io"}, "lower case only"),
    "an IP address": ({"ALPHA_CERT_NAME": "203.0.113.7"}, "IP address and not a name"),
    "a wildcard": ({"ALPHA_CERT_NAME": "*.sslip.io"}, "lower case only"),
    "a single label": ({"ALPHA_CERT_NAME": "localhost"}, "single label"),
    "staging neither yes nor no": ({"ALPHA_ACME_STAGING": "maybe"}, "ALPHA_ACME_STAGING is 'maybe'"),
    "publish neither yes nor no": ({"ALPHA_PUBLISH_HTTPS": "true"}, "ALPHA_PUBLISH_HTTPS is 'true'"),
    "a contact that is not an address": ({"ALPHA_ACME_EMAIL": "not an address"}, "ALPHA_ACME_EMAIL is not an address"),
    "a public plain listener": ({"ALPHA_BIND_ADDRESS": "0.0.0.0"}, "must stay on loopback"),
    "a challenge port that is not a port": ({"ALPHA_ACME_HTTP_PORT": "eighty"}, "ALPHA_ACME_HTTP_PORT is 'eighty'"),
    "an https port out of range": ({"ALPHA_HTTPS_PORT": "70000"}, "ALPHA_HTTPS_PORT is '70000'"),
}


class TestAcmeSettingsWellFormed:
    @pytest.mark.parametrize("case", sorted(BAD_SETTINGS))
    def test_a_bad_setting_is_refused_before_docker_is_touched(self, case: str, tmp_path: Path) -> None:
        overrides, says = BAD_SETTINGS[case]
        script = _stage(tmp_path)
        completed, log = _run(
            script, _env(tmp_path, _free_port(), **_acme_settings(**overrides)), tmp_path
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "TLS settings" in completed.stderr and "not usable" in completed.stderr, completed.stderr
        assert says in completed.stderr, completed.stderr
        assert not log.exists(), _calls(log)

    def test_the_challenge_port_may_not_be_the_application_port(self, tmp_path: Path) -> None:
        port = _free_port()
        script = _stage(tmp_path)
        completed, log = _run(script, _env(tmp_path, port, **_acme_settings(http_port=port)), tmp_path)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert f"same port as ALPHA_HTTP_PORT ({port})" in completed.stderr, completed.stderr
        assert not log.exists()

    @pytest.mark.parametrize(
        "setting", ["ALPHA_PUBLISH_HTTPS=yes", "ALPHA_ACME_EMAIL=ops@sslip.io", "ALPHA_ACME_STAGING=no"]
    )
    def test_a_tls_setting_without_a_name_is_refused_and_not_ignored(self, setting: str, tmp_path: Path) -> None:
        key, value = setting.split("=")
        script = _stage(tmp_path)
        completed, log = _run(script, _env(tmp_path, _free_port(), **{key: value}), tmp_path)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "and ALPHA_CERT_NAME is not" in completed.stderr, completed.stderr
        assert not log.exists()

    def test_a_good_configuration_is_not_refused_here(self, tmp_path: Path, serving: int) -> None:
        script = _stage(tmp_path)
        completed, _ = _run(script, _env(tmp_path, serving, **_acme_settings()), tmp_path)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "not usable" not in completed.stderr

    @pytest.mark.parametrize("case", sorted(BAD_SETTINGS))
    def test_that_guard_is_shown_able_to_fail(self, case: str, tmp_path: Path) -> None:
        cut = _mutant(tmp_path, "acme-settings-well-formed")
        overrides, _ = BAD_SETTINGS[case]
        script = _stage(tmp_path, script=cut)
        completed, _ = _run(script, _env(tmp_path, _free_port(), **_acme_settings(**overrides)), tmp_path)
        assert "not usable" not in completed.stderr, completed.stderr


# --- trusted-proxies-empty-with-name (D-229 item 4) -----------------------------------------------------------------


class TestTrustedProxiesEmptyWithName:
    """`ALPHA_TRUSTED_PROXY_CIDRS` names the peers the proxy believes about `X-Forwarded-For`, for a host whose
    TLS is terminated by ANOTHER nginx in front. Once this stack terminates TLS itself there is no such nginx,
    the client address arrives on the connection, and a peer left in the list can name its own bucket for the
    guest throttle. The runbook said "remove it"; nothing refused it. Now the deploy does, before anything is
    built."""

    LIST = "172.20.0.1/32"

    def _refused(self, tmp_path: Path, value: str) -> subprocess.CompletedProcess[str]:
        script = _stage(tmp_path)
        completed, log = _run(
            script,
            _env(tmp_path, _free_port(), **_acme_settings(), ALPHA_TRUSTED_PROXY_CIDRS=value),
            tmp_path,
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert not log.exists(), _calls(log)
        return completed

    def test_a_list_with_a_name_is_refused_before_docker_is_touched(self, tmp_path: Path) -> None:
        completed = self._refused(tmp_path, self.LIST)
        assert "ALPHA_TRUSTED_PROXY_CIDRS is set" in completed.stderr, completed.stderr
        assert "ALPHA_CERT_NAME is set too" in completed.stderr, completed.stderr
        assert "Nothing was built" in completed.stderr, completed.stderr
        assert "DEPLOYMENT_RUNBOOK.md section 6" in completed.stderr, completed.stderr

    @pytest.mark.parametrize(
        "value",
        [
            "172.20.0.1/32, 10.0.0.0/8",
            "172.20.0.1/32 10.0.0.0/8",
            '"172.20.0.1/32"',
            "'172.20.0.1/32'",
            "172.20.0.1",
            "::1",
        ],
    )
    def test_every_spelling_of_a_non_empty_list_is_refused(self, value: str, tmp_path: Path) -> None:
        self._refused(tmp_path, value)

    def test_the_refusal_names_what_the_list_would_have_trusted(self, tmp_path: Path) -> None:
        completed = self._refused(tmp_path, "172.20.0.1/32, 10.0.0.0/8")
        assert "172.20.0.1/32" in completed.stderr and "10.0.0.0/8" in completed.stderr, completed.stderr

    @pytest.mark.parametrize("value", ["", ", ,", " \t "])
    def test_a_value_with_no_entry_is_the_empty_list_and_is_not_refused(
        self, value: str, tmp_path: Path, serving: int
    ) -> None:
        """`trusted-proxies.sh` reads a value of only separators as "trust nobody"; so does this guard."""
        script = _stage(tmp_path)
        completed, _ = _run(
            script, _env(tmp_path, serving, **_acme_settings(), ALPHA_TRUSTED_PROXY_CIDRS=value), tmp_path
        )
        assert completed.returncode == 0, (completed.stdout, completed.stderr)

    def test_without_a_name_the_list_is_the_host_nginx_configuration_and_is_left_alone(
        self, tmp_path: Path, serving: int
    ) -> None:
        """The control: the guard is gated on the name. A host still behind its own nginx keeps the list."""
        script = _stage(tmp_path)
        completed, _ = _run(
            script, _env(tmp_path, serving, ALPHA_TRUSTED_PROXY_CIDRS=self.LIST), tmp_path
        )
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "ALPHA_CERT_NAME is set too" not in completed.stderr

    def test_a_list_the_proxy_would_refuse_is_still_refused_with_a_name(self, tmp_path: Path) -> None:
        """Two guards can speak about one value; either way the deploy stops before docker."""
        self._refused(tmp_path, "0.0.0.0/0")

    def test_that_guard_is_shown_able_to_fail(self, tmp_path: Path) -> None:
        cut = _mutant(tmp_path, "trusted-proxies-empty-with-name")
        script = _stage(tmp_path, script=cut)
        completed, log = _run(
            script,
            _env(tmp_path, _free_port(), **_acme_settings(), ALPHA_TRUSTED_PROXY_CIDRS=self.LIST),
            tmp_path,
        )
        assert "ALPHA_CERT_NAME is set too" not in completed.stderr, completed.stderr
        assert _compose_calls(log, "build") != [], "the mutant did not reach the build, so this case was not testing that guard"


# --- acme-client-pinned ---------------------------------------------------------------------------------------------


class TestAcmeClientPinned:
    def test_the_shipped_word_is_refused_in_our_words_before_docker(self, tmp_path: Path) -> None:
        """The REAL file's content, not a staged stand-in: this is the state the lane ships in."""
        shipped = (ACME_DIR / "client.pin").read_text(encoding="utf-8")
        assert re.search(r"^ACME_CLIENT_APK_VERSION=UNRESOLVED$", shipped, re.M), (
            "infra/acme/client.pin no longer says UNRESOLVED; if someone resolved it, this case and the "
            "lane's report need to say so"
        )
        script = _stage(tmp_path, pin=shipped)
        completed, log = _run(script, _env(tmp_path, _free_port(), **_acme_settings()), tmp_path)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "the ACME client is not pinned" in completed.stderr, completed.stderr
        assert "step 1" in completed.stderr
        assert not log.exists()

    @pytest.mark.parametrize(
        "pin", ["ACME_CLIENT_APK_VERSION=\n", "# nothing\n", "ACME_CLIENT_APK_VERSION=4.1.1\n", "ACME_CLIENT_APK_VERSION=4.1.1-r\n"]
    )
    def test_an_absent_or_malformed_version_is_refused(self, pin: str, tmp_path: Path) -> None:
        script = _stage(tmp_path, pin=pin)
        completed, log = _run(script, _env(tmp_path, _free_port(), **_acme_settings()), tmp_path)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "pin" in completed.stderr.lower(), completed.stderr
        assert not log.exists()

    def test_a_package_version_passes_and_the_deploy_goes_on(self, tmp_path: Path, serving: int) -> None:
        script = _stage(tmp_path, pin="ACME_CLIENT_APK_VERSION=4.1.1-r0\n")
        completed, _ = _run(script, _env(tmp_path, serving, **_acme_settings()), tmp_path)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)

    def test_without_a_name_the_pin_is_not_read(self, tmp_path: Path, serving: int) -> None:
        script = _stage(tmp_path, pin="ACME_CLIENT_APK_VERSION=UNRESOLVED\n")
        completed, _ = _run(script, _env(tmp_path, serving), tmp_path)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)

    def test_that_guard_is_shown_able_to_fail(self, tmp_path: Path) -> None:
        cut = _mutant(tmp_path, "acme-client-pinned")
        script = _stage(tmp_path, script=cut, pin="ACME_CLIENT_APK_VERSION=UNRESOLVED\n")
        completed, _ = _run(script, _env(tmp_path, _free_port(), **_acme_settings()), tmp_path)
        assert "the ACME client is not pinned" not in completed.stderr, completed.stderr


# --- public-ports-free ----------------------------------------------------------------------------------------------


class TestPublicPortsFree:
    def test_a_held_challenge_port_is_refused_before_the_build(self, tmp_path: Path, held_port: int) -> None:
        script = _stage(tmp_path)
        completed, log = _run(
            script, _env(tmp_path, _free_port(), **_acme_settings(http_port=held_port)), tmp_path
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert f"public port {held_port} is already in use" in completed.stderr, completed.stderr
        assert "DEPLOYMENT_RUNBOOK.md section 6" in completed.stderr
        assert _compose_calls(log, "build") == [] and _compose_calls(log, "up") == [], _calls(log)

    def test_the_https_port_is_asked_only_when_this_deploy_would_publish_it(
        self, tmp_path: Path, held_port: int
    ) -> None:
        settings = _acme_settings(https_port=held_port)
        quiet_dir = tmp_path / "quiet"
        quiet_dir.mkdir()
        quiet, _ = _run(_stage(quiet_dir), _env(quiet_dir, _free_port(), **settings), quiet_dir)
        # not published -> the held 443 is not this deploy's business, and the run is not refused by this guard
        assert "already in use" not in quiet.stderr, quiet.stderr
        loud_dir = tmp_path / "loud"
        loud_dir.mkdir()
        loud, log = _run(
            _stage(loud_dir), _env(loud_dir, _free_port(), **settings, ALPHA_PUBLISH_HTTPS="yes"), loud_dir
        )
        assert loud.returncode == REFUSED, (loud.stdout, loud.stderr)
        assert f"public port {held_port} is already in use" in loud.stderr, loud.stderr
        assert _compose_calls(log, "build") == []

    def test_a_port_this_instances_proxy_already_publishes_is_not_foreign(
        self, tmp_path: Path, held_port: int, serving: int
    ) -> None:
        """The idempotent case: the second deploy finds its own proxy on port 80 and must go on."""
        script = _stage(tmp_path)
        completed, _ = _run(
            script,
            _env(tmp_path, serving, **_acme_settings(http_port=held_port)),
            tmp_path,
            stub={"STUB_PORT_OUT": f"0.0.0.0:{held_port}\n[::]:{held_port}\n"},
        )
        assert completed.returncode == 0, (completed.stdout, completed.stderr)

    def test_a_proxy_that_does_not_publish_that_port_does_not_excuse_it(
        self, tmp_path: Path, held_port: int
    ) -> None:
        """A proxy exists but lacks the new port: whatever holds it is somebody else's."""
        script = _stage(tmp_path)
        completed, _ = _run(
            script,
            _env(tmp_path, _free_port(), **_acme_settings(http_port=held_port)),
            tmp_path,
            stub={"STUB_PORT_OUT": ""},
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "already in use" in completed.stderr

    # --- D-229 item 1: a holder bound to the host's OWN address, not to loopback -----------------------------
    #
    # The judge measured it: a host nginx with `listen <ip>:80;` is not seen by a connect to 127.0.0.1, while
    # Docker's default publish (`0.0.0.0:80`) collides with it, so `compose up` fails on the bind AFTER the
    # build -- and has by then recreated the `proxy`, the only owner of the loopback port the host nginx
    # forwards to. The guard therefore asks the kernel's table of listeners, not one address.

    ADDRESSES = ("127.0.0.2", "OUTWARD", "0.0.0.0", "::1", "::")

    @staticmethod
    def _address(name: str) -> str:
        if name != "OUTWARD":
            return name
        address = _outward_address()
        if address is None:
            pytest.skip("this host has no non-loopback IPv4 address")
        return address

    @pytest.mark.parametrize("name", ADDRESSES)
    def test_a_holder_on_any_address_of_the_host_is_refused_before_the_build(self, name: str, tmp_path: Path) -> None:
        with _listening_on(self._address(name)) as port:
            script = _stage(tmp_path)
            completed, log = _run(script, _env(tmp_path, _free_port(), **_acme_settings(http_port=port)), tmp_path)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert f"public port {port} is already in use, and not by {INSTANCE}'s proxy" in completed.stderr, completed.stderr
        assert f"listening on port {port}" in completed.stderr, completed.stderr
        assert "DEPLOYMENT_RUNBOOK.md section 6" in completed.stderr
        assert _compose_calls(log, "build") == [] and _compose_calls(log, "up") == [], _calls(log)

    @pytest.mark.parametrize("name", ("127.0.0.2", "OUTWARD"))
    def test_the_old_loopback_connect_would_have_called_that_port_free(self, name: str) -> None:
        """The premise of the finding, kept as a fact of this host: while a socket listens on another address,
        a connect to 127.0.0.1 on the same port is refused -- which is all the guard used to ask."""
        with _listening_on(self._address(name)) as port, socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0

    @pytest.mark.parametrize("name", ("0.0.0.0", "127.0.0.2"))
    def test_https_is_checked_across_addresses_too_when_this_deploy_would_publish_it(
        self, name: str, tmp_path: Path
    ) -> None:
        with _listening_on(self._address(name)) as port:
            script = _stage(tmp_path)
            settings = _acme_settings(https_port=port, ALPHA_PUBLISH_HTTPS="yes")
            completed, log = _run(script, _env(tmp_path, _free_port(), **settings), tmp_path)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert f"public port {port} is already in use" in completed.stderr, completed.stderr
        assert _compose_calls(log, "build") == []

    def test_a_port_this_instances_proxy_publishes_on_every_address_is_still_not_foreign(
        self, tmp_path: Path, serving: int
    ) -> None:
        """The idempotent case against the real shape of Docker's publish: a listener on `0.0.0.0`, which the
        proxy's own `docker port` answer excuses."""
        with _listening_on("0.0.0.0") as port:
            script = _stage(tmp_path)
            completed, _ = _run(
                script,
                _env(tmp_path, serving, **_acme_settings(http_port=port)),
                tmp_path,
                stub={"STUB_PORT_OUT": f"0.0.0.0:{port}\n[::]:{port}\n"},
            )
        assert completed.returncode == 0, (completed.stdout, completed.stderr)

    def test_a_host_that_holds_nothing_on_the_port_is_not_refused(self, tmp_path: Path, serving: int) -> None:
        """The guard must not refuse for a listener elsewhere: another port on the same address is nothing."""
        with _listening_on("127.0.0.2"):
            script = _stage(tmp_path)
            completed, _ = _run(script, _env(tmp_path, serving, **_acme_settings()), tmp_path)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "already in use" not in completed.stderr and "NOTE" not in completed.stderr, completed.stderr

    def test_a_connected_socket_on_that_port_is_not_a_listener(self, tmp_path: Path, serving: int) -> None:
        """The table also lists connections. One whose LOCAL port is the challenge port does not stop Docker
        binding it (a bind is refused only by a socket in the LISTEN state), so it must not stop the deploy."""
        with socket.socket() as server:
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            with socket.socket() as client:
                client.bind(("127.0.0.1", 0))
                client.connect(server.getsockname())
                port = client.getsockname()[1]
                script = _stage(tmp_path)
                completed, _ = _run(script, _env(tmp_path, serving, **_acme_settings(http_port=port)), tmp_path)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "already in use" not in completed.stderr, completed.stderr

    # --- the fallback: a host whose listener table cannot be read ---------------------------------------------

    @staticmethod
    def _without_a_listener_table(tmp_path: Path) -> Path:
        """A copy of deploy.sh whose table of listeners is a path that does not exist (a host without /proc)."""
        source = DEPLOY.read_text(encoding="utf-8")
        line = 'LISTENER_TABLES="/proc/net/tcp /proc/net/tcp6"'
        assert source.count(line) == 1, "the guard no longer names its tables in one place"
        cut = tmp_path / "no-table.sh"
        cut.write_text(source.replace(line, 'LISTENER_TABLES="/nonexistent/net/tcp /nonexistent/net/tcp6"'), encoding="utf-8")
        return cut

    def test_without_a_table_a_loopback_holder_is_still_refused(self, tmp_path: Path, held_port: int) -> None:
        script = _stage(tmp_path, script=self._without_a_listener_table(tmp_path))
        completed, log = _run(
            script, _env(tmp_path, _free_port(), **_acme_settings(http_port=held_port)), tmp_path
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert f"public port {held_port} is already in use" in completed.stderr
        assert _compose_calls(log, "build") == []

    def test_without_a_table_the_limit_is_said_and_not_hidden(self, tmp_path: Path, serving: int) -> None:
        """No silent fallback (`AGENTS.md` section 4): the loopback-only question is answered AND the operator is
        told that it is the only question that could be asked. A holder on another address goes unseen here,
        and this test records that this is the stated limit and not an oversight."""
        with _listening_on("127.0.0.2") as port:
            script = _stage(tmp_path, script=self._without_a_listener_table(tmp_path))
            completed, _ = _run(script, _env(tmp_path, serving, **_acme_settings(http_port=port)), tmp_path)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "NOTE" in completed.stderr and "127.0.0.1 only" in completed.stderr, completed.stderr
        assert f"{port}" in completed.stderr

    def test_that_guard_is_shown_able_to_fail(self, tmp_path: Path, held_port: int) -> None:
        cut = _mutant(tmp_path, "public-ports-free")
        script = _stage(tmp_path, script=cut)
        completed, log = _run(
            script, _env(tmp_path, _free_port(), **_acme_settings(http_port=held_port)), tmp_path
        )
        assert "already in use" not in completed.stderr, completed.stderr
        assert _compose_calls(log, "build") != [], "the mutant did not reach the build, so this case was not testing that guard"

    @pytest.mark.parametrize("name", ("127.0.0.2", "0.0.0.0"))
    def test_the_deletion_also_lets_a_holder_on_another_address_through(self, name: str, tmp_path: Path) -> None:
        with _listening_on(self._address(name)) as port:
            cut = _mutant(tmp_path, "public-ports-free")
            script = _stage(tmp_path, script=cut)
            completed, log = _run(script, _env(tmp_path, _free_port(), **_acme_settings(http_port=port)), tmp_path)
        assert "already in use" not in completed.stderr, completed.stderr
        assert _compose_calls(log, "build") != []


# --- acme-pair-answerable and the listener decision ----------------------------------------------------------------


def _up_line(log: Path) -> str:
    """The ONE full `up` of a deploy. Since `PROD-02` the proxy may be brought up a second time, alone
    (`up -d --no-deps proxy`), by `default-credential-gate`; that call is `_proxy_up_lines`."""
    ups = [line for line in _compose_calls(log, "up") if "--no-deps proxy" not in line]
    assert len(ups) == 1, ups
    return ups[0]


def _proxy_up_lines(log: Path) -> list[str]:
    return [line for line in _compose_calls(log, "up") if line.endswith("up -d --no-deps proxy")]


class TestAcmePairAnswerable:
    @pytest.mark.parametrize(
        "stub",
        [
            {"STUB_PAIR": "something else"},
            {"STUB_PAIR": ""},
            {"STUB_PAIR": "pair-present", "STUB_PAIR_STATUS": "1"},
            {"STUB_PAIR": "pair-absent", "STUB_PAIR_STATUS": "125"},
        ],
    )
    def test_an_unanswerable_question_refuses_and_starts_nothing(self, stub: dict[str, str], tmp_path: Path) -> None:
        script = _stage(tmp_path)
        completed, log = _run(script, _env(tmp_path, _free_port(), **_acme_settings()), tmp_path, stub=stub)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "could not be asked" in completed.stderr, completed.stderr
        assert _compose_calls(log, "up") == [], _calls(log)

    def test_the_question_is_asked_of_the_acme_service_with_its_overlay(self, tmp_path: Path, serving: int) -> None:
        script = _stage(tmp_path)
        completed, log = _run(script, _env(tmp_path, serving, **_acme_settings()), tmp_path)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        asked = [line for line in _compose_calls(log, "run") if "/export/fullchain.pem" in line]
        assert len(asked) == 1, asked
        assert "compose.acme.yml" in asked[0] and "--no-deps" in asked[0] and " acme " in asked[0], asked[0]

    def test_that_guard_is_shown_able_to_fail(self, tmp_path: Path) -> None:
        cut = _mutant(tmp_path, "acme-pair-answerable")
        script = _stage(tmp_path, script=cut)
        completed, log = _run(
            script, _env(tmp_path, _free_port(), **_acme_settings()), tmp_path, stub={"STUB_PAIR": "garbage"}
        )
        assert "could not be asked" not in completed.stderr, completed.stderr
        assert _compose_calls(log, "up") != [], "the mutant did not reach `up`, so this case was not testing that guard"


class TestTheListenersADeployHas:
    """`R-146s`: the decision table, driven end to end. The rows are `listeners_overlay_files`' and the
    cases below read them off the `up` line the script actually issues."""

    def _deploy(self, tmp_path: Path, serving: int, *, publish: str, pair: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        script = _stage(tmp_path)
        return _run(
            script,
            _env(tmp_path, serving, **_acme_settings(ALPHA_PUBLISH_HTTPS=publish)),
            tmp_path,
            stub={"STUB_PAIR": pair},
        )

    def test_no_pair_and_not_cleared_publishes_only_the_challenge_port(self, tmp_path: Path, serving: int) -> None:
        completed, log = self._deploy(tmp_path, serving, publish="no", pair="pair-absent")
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        up = _up_line(log)
        assert "compose.acme.yml" in up and "compose.tls.yml" not in up, up
        assert "application listener (TLS) : NOT published" in completed.stdout, completed.stdout
        assert "credential gate is not satisfied" in completed.stdout

    def test_cleared_but_no_pair_yet_keeps_443_closed_and_says_to_run_again(self, tmp_path: Path, serving: int) -> None:
        completed, log = self._deploy(tmp_path, serving, publish="yes", pair="pair-absent")
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "compose.tls.yml" not in _up_line(log)
        assert "no certificate pair exists yet" in completed.stdout
        assert "run this script again" in completed.stdout

    def test_a_pair_but_not_cleared_keeps_443_closed(self, tmp_path: Path, serving: int) -> None:
        """`R-146s`: a certificate alone never opens the application. This is the row a restore that brings
        the default credential back must land in once `PROD-02` supplies the gate."""
        completed, log = self._deploy(tmp_path, serving, publish="no", pair="pair-present")
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "compose.tls.yml" not in _up_line(log)
        assert _proxy_up_lines(log) == [], "the proxy was recreated although 443 was not to change"
        assert "credential gate is not satisfied" in completed.stdout

    def test_cleared_and_a_pair_publishes_443_after_the_acme_overlay(self, tmp_path: Path, serving: int) -> None:
        """BEFORE `PROD-02` this asserted that the ONE `up` carried the acme overlay and then the 443 overlay.
        NOW the full `up` never opens 443 on a proxy that does not already publish it (the credential gate has
        not been asked yet: the database does not exist before `up`); 443 is opened by the proxy-only `up`
        that `default-credential-gate` issues after a clean gate, with the same two overlays in the same order."""
        completed, log = self._deploy(tmp_path, serving, publish="yes", pair="pair-present")
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        full = _up_line(log)
        assert "compose.acme.yml" in full and "compose.tls.yml" not in full, full
        proxy_ups = _proxy_up_lines(log)
        assert len(proxy_ups) == 1, proxy_ups
        assert re.search(
            r"compose\.server\.yml --file \S+compose\.acme\.yml --file \S+compose\.tls\.yml up -d --no-deps proxy$",
            proxy_ups[0],
        ), proxy_ups[0]
        assert "published on port" in completed.stdout and "(the credential gate is clean)" in completed.stdout

    def test_the_build_sees_the_acme_service_and_only_the_acme_overlay(self, tmp_path: Path, serving: int) -> None:
        completed, log = self._deploy(tmp_path, serving, publish="yes", pair="pair-present")
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        built = _compose_calls(log, "build")
        assert len(built) == 1 and "compose.acme.yml" in built[0] and "compose.tls.yml" not in built[0], built

    def test_the_acme_image_must_exist_after_the_build(self, tmp_path: Path, serving: int) -> None:
        script = _stage(tmp_path)
        completed, log = _run(
            script,
            _env(tmp_path, serving, **_acme_settings()),
            tmp_path,
            stub={"STUB_MISSING_IMAGES": f"{INSTANCE}-acme"},
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert f"there is no image called {INSTANCE}-acme" in completed.stderr, completed.stderr
        assert _compose_calls(log, "up") == []

    def test_a_deploy_whose_certificate_was_not_issued_is_refused_by_name(self, tmp_path: Path, serving: int) -> None:
        script = _stage(tmp_path)
        completed, _ = _run(
            script,
            _env(tmp_path, serving, **_acme_settings()),
            tmp_path,
            stub={"STUB_ACME_STATE": "running/unhealthy"},
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "the 'acme' service" in completed.stderr and "running/unhealthy" in completed.stderr, completed.stderr

    def test_the_staging_endpoint_is_said_on_every_run(self, tmp_path: Path, serving: int) -> None:
        script = _stage(tmp_path)
        completed, _ = _run(
            script, _env(tmp_path, serving, **_acme_settings(ALPHA_ACME_STAGING="yes")), tmp_path
        )
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "STAGING, rehearsal only" in completed.stdout
        assert "TEST one, trusted by no browser" in completed.stdout


class TestNoNameChangesNothing:
    """The rollback is a property: with the name empty every `docker compose` call is the call it was before
    the lane -- one `--file`, the base -- and no acme anything is built, asked or waited for."""

    def test_every_compose_call_names_exactly_the_base_file(self, tmp_path: Path, serving: int) -> None:
        script = _stage(tmp_path)
        completed, log = _run(script, _env(tmp_path, serving), tmp_path)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        compose_lines = [line for line in _calls(log) if line.startswith("compose ")]
        assert compose_lines, _calls(log)
        for line in compose_lines:
            assert line.count("--file") == 1 and "compose.server.yml" in line, line
        everything = "\n".join(_calls(log)).replace(str(tmp_path), "<tmp>")
        assert "acme" not in everything, everything
        assert "tls" not in everything.lower(), everything
        assert "the listeners this deploy has" not in completed.stdout
