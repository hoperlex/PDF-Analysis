"""`R-46` -- `infra/deploy/readiness.sh`, driven to both an OK and a FINDING on each of its
six checks, and (for the five that need no running stack) shown able to fail by DELETING
the check's own marked block, exactly the discipline `test_deploy_script_refusals.py`
already holds `deploy.sh`'s guards to.

**Why this suite exists at all, restated from the brief.** `W46-JUDGE-X`'s `X-1`/`X-2`
found guards and tests that were green on every input they were actually driven with. `G1`
of this brief says the same sentence about a readiness command in particular: *"a readiness
command that is green on every input is the thing seven waves were spent learning about."*
So every check below has a case that turns it red, a case that turns it clean (the control
-- without it a command that always found a problem would look identical to one doing its
job), and, where no running stack is needed, a mutant with the check's block deleted.

**`default-credential` is the one exception to "no running stack needed".** It runs
`src/auditmanager/access/check.py` inside the deployed api image, the same way `deploy.sh`'s
`migrations-at-head` guard runs `shared.db.check` -- so it needs `docker` on `PATH`, stubbed
here the same way `test_deploy_script_refusals.py` stubs it: it records nothing but answers
the one call `readiness.sh` makes, reaches no daemon, and starts no container. There is
deliberately no mutation-deletion case for it: deleting `# >>> check: default-credential`
would only prove the stub is reachable, not that the check reads `check.py`'s real
sentinels, which the OK/FINDING/UNKNOWN cases below already prove directly.

`provider-mode` and `cost-ceiling` run against THIS repository's real `.venv` and the real
`auditmanager.bootstrap.settings.load()` -- not a stub -- because that module IS the
composition root's own validation and the brief's point is to consult it rather than
re-derive it. No repository files are touched: `--env-file`/`--provider-env-file` point at
files under `tmp_path`, and the script itself is run in place.
"""

from __future__ import annotations

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
READINESS = ROOT / "infra/deploy/readiness.sh"

PG_USER = "the_configured_user"
PG_DB = "the_configured_database"
PG_PASSWORD = "an-edited-postgres-password"
#: `PROD-04`: the application role api and worker connect as, and its (second) password.
APP_ROLE = "the_application_role"
APP_PASSWORD = "an-edited-application-db-password-0001"
APP_URL = f"postgresql+psycopg://{APP_ROLE}:{APP_PASSWORD}@postgres:5432/{PG_DB}"
MINIO_USER = "an-edited-minio-root"
MINIO_PASSWORD = "an-edited-minio-password"


def _alpha_env(
    tmp_path: Path,
    *,
    name: str = "alpha.env",
    provider_mode: str = "recorded",
    bind_address: str | None = None,
    extra: tuple[str, ...] = (),
) -> Path:
    lines = [
        "ALPHA_INSTANCE=an-instance",
        "ALPHA_HTTP_PORT=18080",
        f"POSTGRES_DB={PG_DB}",
        f"POSTGRES_USER={PG_USER}",
        f"POSTGRES_PASSWORD={PG_PASSWORD}",
        "S3_BUCKET=the-configured-bucket",
        f"MINIO_ROOT_USER={MINIO_USER}",
        f"MINIO_ROOT_PASSWORD={MINIO_PASSWORD}",
        "S3_ENDPOINT_URL=http://s3:9000",
        "S3_REGION=us-east-1",
        f"S3_ACCESS_KEY_ID={MINIO_USER}",
        f"S3_SECRET_ACCESS_KEY={MINIO_PASSWORD}",
        f"ALPHA_APP_DB_USER={APP_ROLE}",
        f"ALPHA_APP_DB_PASSWORD={APP_PASSWORD}",
        f"DATABASE_URL={APP_URL}",
        f"MIGRATOR_DATABASE_URL=postgresql+psycopg://{PG_USER}:{PG_PASSWORD}@postgres:5432/{PG_DB}",
        "AUDITMANAGER_API_TOKEN=an-edited-token-that-authorizes-something",
        f"AUDITMANAGER_PROVIDER_MODE={provider_mode}",
    ]
    if bind_address is not None:
        lines.append(f"ALPHA_BIND_ADDRESS={bind_address}")
    lines.extend(extra)
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _provider_env(tmp_path: Path, *, name: str = "provider.env", **values: str) -> Path:
    path = tmp_path / name
    path.write_text(
        "\n".join(f"{k}={v}" for k, v in values.items()) + "\n", encoding="utf-8"
    )
    return path


# --- the `docker` `default-credential` reaches -----------------------------------------
#
# It records the call it is given and answers with whatever `access.py`-shaped text the
# case asks for. It never opens a socket, so even the OK case proves nothing about a real
# database -- what it proves is that `readiness.sh` reads `check.py`'s own sentinels
# correctly, which is the thing G1 asks this command to reuse rather than re-derive.

DOCKER_STUB = r'''#!/usr/bin/env python3
import os
import sys

argv = sys.argv[1:]
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as handle:
    handle.write(" ".join(argv) + "\n")

if argv[:1] == ["compose"]:
    joined = " ".join(argv)
    if "auditmanager.access.check" in joined:
        sys.stdout.write(os.environ.get("STUB_ACCESS_OUTPUT", "access-check OK no default credentials\n"))
        sys.exit(int(os.environ.get("STUB_ACCESS_STATUS", "0")))
    if " exec -T api " in joined or " exec -T worker " in joined:
        # `PROD-04`: `db-roles` asks the running containers which user their DATABASE_URL names. Clean by default.
        name = "API" if " exec -T api " in joined else "WORKER"
        if os.environ.get("STUB_%s_DOWN" % name):
            sys.exit(1)
        sys.stdout.write(os.environ.get("STUB_%s_URL" % name, os.environ["STUB_APP_URL"]))
        sys.exit(0)
    if " exec -T postgres psql " in joined:
        if "from pg_roles" in joined:
            # the `ADR-0021` row 7 query, given in argv
            sys.stdout.write(os.environ.get("STUB_ROLE_FACTS", "f|f|f|t") + "\n")
            sys.exit(int(os.environ.get("STUB_ROLE_STATUS", "0")))
        # `apply-grants.sh --check`: its SQL arrives on stdin
        sys.stdin.read()
        sys.stdout.write(os.environ.get("STUB_GRANTS_CHECK_OUT", ""))
        sys.stderr.write(os.environ.get("STUB_GRANTS_CHECK_ERR", ""))
        sys.exit(int(os.environ.get("STUB_GRANTS_CHECK_STATUS", "0")))
    if "check-served.sh" in joined:
        # `PROD-01-TLS-ACME-01`: the one question `tls` asks of the acme image. The real script has its
        # own suite (`test_acme_client.py`); here it is a scripted answer, so what is tested is how
        # `readiness.sh` reads the exit status and the line.
        sys.stdout.write(os.environ.get("STUB_CERT_OUTPUT", "served-certificate: OK name=x mode=production\n"))
        sys.exit(int(os.environ.get("STUB_CERT_STATUS", "0")))
sys.exit(0)
'''


def _run(
    args: tuple[str, ...] = (),
    *,
    tmp_path: Path,
    script: Path | None = None,
    env: dict[str, str] | None = None,
    stub_docker: bool = False,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    environment = dict(os.environ)
    log = tmp_path / "docker-calls.log"
    if stub_docker:
        binary = tmp_path / "bin"
        binary.mkdir(exist_ok=True)
        docker = binary / "docker"
        docker.write_text(DOCKER_STUB, encoding="utf-8")
        docker.chmod(0o755)
        environment["PATH"] = f"{binary}{os.pathsep}{environment['PATH']}"
        environment["STUB_LOG"] = str(log)
        environment["STUB_APP_URL"] = APP_URL
    if env:
        environment.update(env)
    completed = subprocess.run(
        ["bash", str(script or READINESS), *args],
        capture_output=True,
        text=True,
        env=environment,
        timeout=120,
    )
    return completed, log


def _mutant(check: str) -> Path:
    """A copy of readiness.sh with exactly one `# >>> check: <name>` block deleted."""
    source = READINESS.read_text(encoding="utf-8")
    block = re.compile(
        rf"^# >>> check: {re.escape(check)}\n.*?^# <<< check: {re.escape(check)}\n",
        re.DOTALL | re.MULTILINE,
    )
    mutated, count = block.subn("", source)
    assert count == 1, f"the check markers for {check!r} are not a single block"
    assert mutated != source
    return mutated


def _write_mutant(tmp_path: Path, check: str) -> Path:
    cut = tmp_path / f"mutant-{check}.sh"
    cut.write_text(_mutant(check), encoding="utf-8")
    return cut


# --- the header, always present, so nobody mistakes this for a gate --------------------


def test_it_never_claims_to_gate_anything(tmp_path: Path) -> None:
    env_file = _alpha_env(tmp_path)
    completed, _ = _run(
        ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "no-provider.env")),
        tmp_path=tmp_path,
    )
    assert "REPORTS and REGISTERS" in completed.stdout, completed.stdout
    assert "blocks no deploy" in completed.stdout.replace("\n", " "), completed.stdout


class TestDefaultCredential:
    """Step 5 / G2. `check.py`'s own sentinels, consumed rather than re-derived."""

    def test_clean_is_read_as_ok(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path)
        completed, log = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path,
            stub_docker=True,
            env={"STUB_ACCESS_OUTPUT": "access-check OK no default credentials\n"},
        )
        assert "readiness OK      default-credential" in completed.stdout, completed.stdout
        assert "auditmanager.access.check" in log.read_text(encoding="utf-8")

    def test_a_finding_is_read_as_a_finding_and_quotes_the_check_s_own_lines(
        self, tmp_path: Path
    ) -> None:
        env_file = _alpha_env(tmp_path)
        access_output = (
            "access-check DEFAULT CREDENTIAL: login=admin user_uid=u-1 "
            "created_at=2026-01-01T00:00:00+00:00 password_unchanged_since=2026-01-01T00:00:00+00:00\n"
            "access-check: 1 account(s) still hold the seeded password. "
            "Anyone who has read the deployment notes can sign in as them.\n"
        )
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path,
            stub_docker=True,
            env={"STUB_ACCESS_OUTPUT": access_output},
        )
        assert "readiness FINDING default-credential" in completed.stdout, completed.stdout
        assert "login=admin" in completed.stdout, completed.stdout
        assert completed.returncode in (1, 2)

    def test_no_docker_on_path_is_unknown_not_ok(self, tmp_path: Path) -> None:
        """The one thing this must never do: report OK because it could not ask.

        `bash`, `sed` and everything else `readiness.sh` itself needs stay on `PATH` --
        only the directory `docker` resolves from is removed, so a failure here is about
        the `default-credential` check specifically and not about the script failing to
        run at all.
        """
        env_file = _alpha_env(tmp_path)
        assert shutil.which("docker"), "this test needs a real `docker` on PATH to remove"
        # Filtered by literal directory entry, not a resolved realpath: `/snap/bin/docker`
        # is a symlink to `/usr/bin/snap`, and resolving it would name the wrong directory
        # to drop.
        stripped_path = os.pathsep.join(
            p for p in os.environ["PATH"].split(os.pathsep)
            if not os.access(os.path.join(p, "docker"), os.X_OK)
        )
        assert shutil.which("docker", path=stripped_path) is None, stripped_path
        assert shutil.which("bash", path=stripped_path) is not None, stripped_path
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path,
            env={"PATH": stripped_path},
        )
        assert "readiness UNKNOWN default-credential" in completed.stdout, completed.stdout
        assert "readiness OK      default-credential" not in completed.stdout


class _Challenge(http.server.BaseHTTPRequestHandler):
    """Stands in for the proxy's challenge listener on public port 80 (`R-146s`). The answer is set per
    case through the fixture: a redirect to HTTPS is the right one; the application's own `401` is the
    wrong one, because it would mean port 80 reaches the application."""

    status = 301
    location = "https://rehearsal-host.sslip.io/api/v1/openapi.json"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's spelling
        self.send_response(type(self).status)
        if type(self).location:
            self.send_header("Location", type(self).location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *_: object) -> None:
        """Silence."""


@pytest.fixture()
def challenge_listener() -> Iterator[tuple[int, type[_Challenge]]]:
    handler = type("_Handler", (_Challenge,), {"status": 301, "location": _Challenge.location})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1], handler
    finally:
        server.shutdown()
        server.server_close()


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


#: `PROD-01-TLS-ACME-01` rewrote the `tls` check from "is a pair on disk at `proxy/tls/`" to "what does the
#: proxy's TLS listener serve", so `--tls-dir` is gone and the cases below drive the new questions. The
#: names are literals here (`OPERATING_CONSTRAINTS.md` section 12) and none of them is the live one.
CERT_NAME = "rehearsal-host.sslip.io"


def _path_without_docker() -> str:
    """`PATH` with every directory that holds a `docker` removed, as the existing case does."""
    assert shutil.which("docker"), "this test needs a real `docker` on PATH to remove"
    stripped = os.pathsep.join(
        p for p in os.environ["PATH"].split(os.pathsep) if not os.access(os.path.join(p, "docker"), os.X_OK)
    )
    assert shutil.which("docker", path=stripped) is None, stripped
    assert shutil.which("bash", path=stripped) is not None, stripped
    return stripped


def _tls_args(env_file: Path, tmp_path: Path) -> tuple[str, ...]:
    return ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env"))


class TestTls:
    """Four answers: no terminator in the stack, a name that cannot be used, the test endpoint, and what
    `check-served.sh` says about what is served. Each is a FINDING; only a served, trusted, unexpiring
    certificate is OK, and a question that could not be asked is UNKNOWN."""

    def test_no_name_is_a_finding_because_no_terminator_is_part_of_the_stack(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path)
        completed, _ = _run(_tls_args(env_file, tmp_path), tmp_path=tmp_path)
        assert "readiness FINDING tls " in completed.stdout, completed.stdout
        assert "ALPHA_CERT_NAME is not set" in completed.stdout

    def test_a_name_that_cannot_be_used_is_a_finding(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path, extra=("ALPHA_CERT_NAME=host.example.invalid", "ALPHA_ACME_STAGING=no"))
        completed, _ = _run(_tls_args(env_file, tmp_path), tmp_path=tmp_path, stub_docker=True)
        assert "readiness FINDING tls " in completed.stdout, completed.stdout
        assert "not a usable name" in completed.stdout

    def test_the_test_endpoint_is_a_finding_and_asks_nothing_of_the_acme_image(self, tmp_path: Path) -> None:
        """No `ALPHA_ACME_STAGING` line at all: the default is `yes`, and the default is a finding."""
        env_file = _alpha_env(tmp_path, extra=(f"ALPHA_CERT_NAME={CERT_NAME}",))
        completed, log = _run(_tls_args(env_file, tmp_path), tmp_path=tmp_path, stub_docker=True)
        assert "readiness FINDING tls " in completed.stdout, completed.stdout
        assert "TEST certificate" in completed.stdout
        calls = log.read_text(encoding="utf-8") if log.exists() else ""
        assert "check-served.sh" not in calls, calls

    def test_a_served_trusted_certificate_is_ok_and_the_question_is_the_right_one(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path, extra=(f"ALPHA_CERT_NAME={CERT_NAME}", "ALPHA_ACME_STAGING=no"))
        completed, log = _run(_tls_args(env_file, tmp_path), tmp_path=tmp_path, stub_docker=True)
        assert "readiness OK      tls " in completed.stdout, completed.stdout
        asked = [line for line in log.read_text(encoding="utf-8").splitlines() if "check-served.sh" in line]
        assert len(asked) == 1, asked
        # the acme overlay is among the files, the name goes in as SNI, the proxy's own TLS listener is the
        # target, 14 days is the margin, and production is the mode
        assert "compose.acme.yml" in asked[0], asked[0]
        assert asked[0].endswith(
            f"--entrypoint /usr/local/bin/check-served.sh acme {CERT_NAME} proxy:8443 14 production"
        ), asked[0]

    @pytest.mark.parametrize("status", [10, 11, 12, 13])
    def test_a_certificate_check_served_refuses_is_a_finding_that_quotes_its_line(
        self, status: int, tmp_path: Path
    ) -> None:
        env_file = _alpha_env(tmp_path, extra=(f"ALPHA_CERT_NAME={CERT_NAME}", "ALPHA_ACME_STAGING=no"))
        completed, _ = _run(
            _tls_args(env_file, tmp_path), tmp_path=tmp_path, stub_docker=True,
            env={"STUB_CERT_STATUS": str(status), "STUB_CERT_OUTPUT": f"served-certificate: WORD{status} -- the reason\n"},
        )
        assert "readiness FINDING tls " in completed.stdout, completed.stdout
        assert f"served-certificate: WORD{status}" in completed.stdout

    def test_a_question_that_could_not_be_asked_is_unknown_not_ok(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path, extra=(f"ALPHA_CERT_NAME={CERT_NAME}", "ALPHA_ACME_STAGING=no"))
        completed, _ = _run(
            _tls_args(env_file, tmp_path), tmp_path=tmp_path, stub_docker=True,
            env={"STUB_CERT_STATUS": "125", "STUB_CERT_OUTPUT": "docker: the daemon said no\n"},
        )
        assert "readiness UNKNOWN tls " in completed.stdout, completed.stdout
        assert "readiness OK      tls " not in completed.stdout

    def test_no_docker_is_unknown_not_ok(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path, extra=(f"ALPHA_CERT_NAME={CERT_NAME}", "ALPHA_ACME_STAGING=no"))
        completed, _ = _run(_tls_args(env_file, tmp_path), tmp_path=tmp_path, env={"PATH": _path_without_docker()})
        assert "readiness UNKNOWN tls " in completed.stdout, completed.stdout
        assert "readiness OK      tls " not in completed.stdout

    def test_the_check_is_shown_able_to_fail(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path)  # no name: the unmutated script reports a tls FINDING
        mutant = _write_mutant(tmp_path, "tls")
        completed, _ = _run(_tls_args(env_file, tmp_path), tmp_path=tmp_path, script=mutant)
        assert "tls" not in completed.stdout.replace("readiness.sh", ""), completed.stdout


class TestPlainHttp:
    def test_the_loopback_default_is_ok(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path)  # no ALPHA_BIND_ADDRESS -- D-49's safe default
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path,
        )
        assert "readiness OK      plain-http " in completed.stdout, completed.stdout

    def test_an_explicit_loopback_is_also_ok(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path, bind_address="127.0.0.1")
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path,
        )
        assert "readiness OK      plain-http " in completed.stdout, completed.stdout

    def test_a_public_bind_address_is_a_finding(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path, bind_address="0.0.0.0")
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path,
        )
        assert "readiness FINDING plain-http " in completed.stdout, completed.stdout
        assert "0.0.0.0" in completed.stdout

    def test_the_check_is_shown_able_to_fail(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path, bind_address="0.0.0.0")
        mutant = _write_mutant(tmp_path, "plain-http")
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path,
            script=mutant,
        )
        assert "plain-http" not in completed.stdout

    # --- with a certificate name: the challenge listener on public port 80 (`R-146s`) -------------
    def _acme_plain(self, tmp_path: Path, port: int, **kw: object) -> tuple[subprocess.CompletedProcess[str], Path]:
        env_file = _alpha_env(
            tmp_path, extra=(f"ALPHA_CERT_NAME={CERT_NAME}", "ALPHA_ACME_STAGING=no", f"ALPHA_ACME_HTTP_PORT={port}"), **kw  # type: ignore[arg-type]
        )
        return _run(_tls_args(env_file, tmp_path), tmp_path=tmp_path)

    def test_a_redirect_to_https_on_the_challenge_port_is_ok(
        self, tmp_path: Path, challenge_listener: tuple[int, type[_Challenge]]
    ) -> None:
        port, _ = challenge_listener
        completed, _ = self._acme_plain(tmp_path, port)
        assert "readiness OK      plain-http " in completed.stdout, completed.stdout
        assert "redirect to HTTPS" in completed.stdout

    def test_an_application_answer_on_the_challenge_port_is_a_finding(
        self, tmp_path: Path, challenge_listener: tuple[int, type[_Challenge]]
    ) -> None:
        """The application answers `401` to this path (`deploy.sh`'s `proxy-answers`). Seeing it on port 80
        means port 80 reaches the application, which is exactly what `R-146s` says it must not."""
        port, handler = challenge_listener
        handler.status, handler.location = 401, ""
        completed, _ = self._acme_plain(tmp_path, port)
        assert "readiness FINDING plain-http " in completed.stdout, completed.stdout
        assert "reach no application route" in completed.stdout

    def test_a_redirect_that_leaves_for_plain_http_is_a_finding(
        self, tmp_path: Path, challenge_listener: tuple[int, type[_Challenge]]
    ) -> None:
        port, handler = challenge_listener
        handler.location = "http://elsewhere.example/"
        completed, _ = self._acme_plain(tmp_path, port)
        assert "readiness FINDING plain-http " in completed.stdout, completed.stdout

    def test_nothing_listening_is_unknown_not_ok(self, tmp_path: Path) -> None:
        completed, _ = self._acme_plain(tmp_path, _free_port())
        assert "readiness UNKNOWN plain-http " in completed.stdout, completed.stdout
        assert "readiness OK      plain-http " not in completed.stdout

    def test_a_public_application_listener_is_a_finding_even_when_port_80_is_right(
        self, tmp_path: Path, challenge_listener: tuple[int, type[_Challenge]]
    ) -> None:
        port, _ = challenge_listener
        completed, _ = self._acme_plain(tmp_path, port, bind_address="0.0.0.0")
        assert "readiness FINDING plain-http " in completed.stdout, completed.stdout
        assert "plain APPLICATION listener" in completed.stdout


class TestProviderMode:
    def test_recorded_is_a_finding(self, tmp_path: Path) -> None:
        """Not a bug in `recorded` -- a true statement that step 7 has not happened."""
        env_file = _alpha_env(tmp_path, provider_mode="recorded")
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path,
        )
        assert "readiness FINDING provider-mode " in completed.stdout, completed.stdout

    def test_live_with_a_credential_is_ok(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path, provider_mode="live")
        provider_env = _provider_env(tmp_path, ANTHROPIC_API_KEY="a-real-looking-key")
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(provider_env)),
            tmp_path=tmp_path,
        )
        assert "readiness OK      provider-mode " in completed.stdout, completed.stdout

    def test_live_without_a_credential_is_a_finding_from_the_settings_loader_itself(
        self, tmp_path: Path
    ) -> None:
        env_file = _alpha_env(tmp_path, provider_mode="live")
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path,
        )
        assert "readiness FINDING provider-mode " in completed.stdout, completed.stdout
        assert "ANTHROPIC_API_KEY is unset" in completed.stdout, completed.stdout

    def test_an_undeclared_mode_is_a_finding_from_the_settings_loader_itself(
        self, tmp_path: Path
    ) -> None:
        env_file = _alpha_env(tmp_path, provider_mode="not-a-real-mode")
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path,
        )
        assert "readiness FINDING provider-mode " in completed.stdout, completed.stdout
        assert "the declared modes are" in completed.stdout, completed.stdout

    def test_the_check_is_shown_able_to_fail(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path, provider_mode="recorded")
        mutant = _write_mutant(tmp_path, "provider-mode")
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path,
            script=mutant,
        )
        assert "provider-mode" not in completed.stdout


class TestCostCeiling:
    def test_the_unset_default_resolves_and_is_ok(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path)
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path,
        )
        assert "readiness OK      cost-ceiling " in completed.stdout, completed.stdout
        # `OD-03`'s default, quoted from AppSettings.load() itself, not repeated by hand.
        assert "$1.0" in completed.stdout, completed.stdout

    def test_an_explicit_ceiling_is_read_and_is_ok(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path)
        provider_env = _provider_env(tmp_path, AUDITMANAGER_RUN_COST_CEILING_USD="5.00")
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(provider_env)),
            tmp_path=tmp_path,
        )
        assert "readiness OK      cost-ceiling " in completed.stdout, completed.stdout
        assert "$5.0" in completed.stdout, completed.stdout

    def test_an_unparseable_ceiling_is_a_finding_from_the_settings_loader_itself(
        self, tmp_path: Path
    ) -> None:
        env_file = _alpha_env(tmp_path)
        provider_env = _provider_env(
            tmp_path, AUDITMANAGER_RUN_COST_CEILING_USD="not-a-number"
        )
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(provider_env)),
            tmp_path=tmp_path,
        )
        assert "readiness FINDING cost-ceiling " in completed.stdout, completed.stdout
        assert "is not a number" in completed.stdout, completed.stdout

    def test_a_non_positive_ceiling_is_a_finding(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path)
        provider_env = _provider_env(tmp_path, AUDITMANAGER_RUN_COST_CEILING_USD="0")
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(provider_env)),
            tmp_path=tmp_path,
        )
        assert "readiness FINDING cost-ceiling " in completed.stdout, completed.stdout
        assert "must be positive" in completed.stdout, completed.stdout

    def test_the_check_is_shown_able_to_fail(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path)
        provider_env = _provider_env(
            tmp_path, AUDITMANAGER_RUN_COST_CEILING_USD="not-a-number"
        )
        mutant = _write_mutant(tmp_path, "cost-ceiling")
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(provider_env)),
            tmp_path=tmp_path,
            script=mutant,
        )
        assert "cost-ceiling" not in completed.stdout


class TestOffHostBackup:
    """No configuration in this repository can make this check pass today -- that is the
    honest state of the tree, not a bug in the check. The point being pinned is narrower:
    the finding comes from the marked block and not from some other, unremovable source."""

    def test_it_is_always_a_finding(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path)
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path,
        )
        assert "readiness FINDING off-host-backup " in completed.stdout, completed.stdout
        assert "owner's" in completed.stdout

    def test_the_check_is_shown_able_to_fail(self, tmp_path: Path) -> None:
        """Delete the block, and the finding is gone -- so it really was this block
        producing it, not some unremovable fallback text."""
        env_file = _alpha_env(tmp_path)
        mutant = _write_mutant(tmp_path, "off-host-backup")
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path,
            script=mutant,
        )
        assert "off-host-backup" not in completed.stdout


class TestTheSummaryAndExitStatus:
    def test_a_clean_run_exits_zero(
        self, tmp_path: Path, challenge_listener: tuple[int, type[_Challenge]]
    ) -> None:
        """The nearest thing to \"every check OK\" this tree can produce today: it still
        cannot be all seven, because off-host-backup never passes and default-credential
        needs a real stack -- so this drives the checks answerable without a stack clean and
        stubs default-credential clean too, and reads the summary line. `tls` is clean through
        a stubbed `check-served.sh` and `plain-http` through a real listener answering a redirect
        (`PROD-01-TLS-ACME-01`; both used to be answered from a directory and a bind address)."""
        port, _ = challenge_listener
        env_file = _alpha_env(
            tmp_path,
            extra=(f"ALPHA_CERT_NAME={CERT_NAME}", "ALPHA_ACME_STAGING=no", f"ALPHA_ACME_HTTP_PORT={port}"),
        )
        completed, _ = _run(
            _tls_args(env_file, tmp_path),
            tmp_path=tmp_path,
            stub_docker=True,
            env={"STUB_ACCESS_OUTPUT": "access-check OK no default credentials\n"},
        )
        # provider-mode is still a finding (recorded) and off-host-backup always is, so
        # this is not exit 0 -- and that is the honest state of this tree, asserted rather
        # than hidden.
        assert "readiness OK      tls " in completed.stdout, completed.stdout
        assert "readiness OK      plain-http " in completed.stdout, completed.stdout
        assert "readiness OK      db-roles " in completed.stdout, completed.stdout
        assert "2 finding(s)" in completed.stdout, completed.stdout
        assert "8 checks" in completed.stdout, completed.stdout
        assert completed.returncode == 1

    def test_missing_env_file_makes_every_file_dependent_check_unknown_not_ok(
        self, tmp_path: Path
    ) -> None:
        completed, _ = _run(
            (
                "--env-file", str(tmp_path / "does-not-exist.env"),
                "--provider-env-file", str(tmp_path / "np.env"),
            ),
            tmp_path=tmp_path,
        )
        assert "readiness UNKNOWN default-credential" in completed.stdout, completed.stdout
        assert "readiness UNKNOWN provider-mode" in completed.stdout, completed.stdout
        assert "readiness UNKNOWN cost-ceiling" in completed.stdout, completed.stdout
        assert completed.returncode == 2
        assert "OK      default-credential" not in completed.stdout
        assert "OK      provider-mode" not in completed.stdout
        assert "OK      cost-ceiling" not in completed.stdout


def _keypair() -> tuple[str, str]:
    """A fresh X25519 pair as ``(private, public)`` base64, for the key-ring checks."""
    import base64

    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
    )

    key = X25519PrivateKey.generate()
    return (
        base64.b64encode(key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())).decode(),
        base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode(),
    )


def _with_lines(path: Path, *lines: str) -> Path:
    path.write_text(path.read_text(encoding="utf-8") + "\n".join(lines) + "\n", encoding="utf-8")
    return path


class TestExecutorSource:
    """`EXEC-HTTP-01`: the provider source and the key ring, each driven to both answers."""

    def _result(self, tmp_path: Path, alpha: Path, provider: Path | None = None) -> str:
        completed, _ = _run(
            ("--env-file", str(alpha), "--provider-env-file", str(provider or tmp_path / "np.env")),
            tmp_path=tmp_path,
        )
        return completed.stdout

    def test_the_environment_source_with_a_recorded_process_is_ok(self, tmp_path: Path) -> None:
        out = self._result(tmp_path, _alpha_env(tmp_path))
        assert "readiness OK      executor-source " in out, out

    def test_a_proxy_stub_model_is_a_finding_because_every_run_fails_closed(
        self, tmp_path: Path
    ) -> None:
        alpha = _alpha_env(tmp_path, provider_mode="proxy")
        stub = _provider_env(tmp_path, PROXY_LLM_BASE_URL="https://p.example/agent/v1",
                             PROXY_LLM_TOKEN="t")
        out = self._result(tmp_path, alpha, stub)
        assert "readiness FINDING executor-source " in out, out
        assert "fails closed" in out and "R-133" in out, out
        explicit = _provider_env(
            tmp_path, name="explicit.env", PROXY_LLM_BASE_URL="https://p.example/agent/v1",
            PROXY_LLM_TOKEN="t", PROXY_LLM_MODEL="anthropic/claude-opus-5")
        assert "readiness OK      executor-source " in self._result(tmp_path, alpha, explicit)

    def test_the_database_source_needs_the_private_ring_and_a_public_key_that_matches_it(
        self, tmp_path: Path
    ) -> None:
        private, public = _keypair()
        _other_private, other_public = _keypair()
        base = ("AUDITMANAGER_PROVIDER_SOURCE=database", "AUDITMANAGER_PROVIDER_MODE=live")

        def alpha(name: str, *lines: str) -> Path:
            path = _alpha_env(tmp_path, name=name, provider_mode="live")
            return _with_lines(path, *base, *lines)

        no_ring = self._result(tmp_path, alpha("a1.env", f"AUDITMANAGER_SECRETS_PUBLIC_KEYS=k1:{public}",
                                               "AUDITMANAGER_SECRETS_ACTIVE_KID=k1"))
        assert "readiness FINDING executor-source " in no_ring and "private ring" in no_ring, no_ring
        ring = _provider_env(tmp_path, name="ring.env", AUDITMANAGER_SECRETS_KEYS=f"k1:{private}")
        no_public = self._result(tmp_path, alpha("a2.env"), ring)
        assert "readiness FINDING executor-source " in no_public, no_public
        mismatched = self._result(
            tmp_path, alpha("a3.env", f"AUDITMANAGER_SECRETS_PUBLIC_KEYS=k1:{other_public}",
                            "AUDITMANAGER_SECRETS_ACTIVE_KID=k1"), ring)
        assert "readiness FINDING executor-source " in mismatched, mismatched
        assert "no matching private key" in mismatched, mismatched
        whole = self._result(
            tmp_path, alpha("a4.env", f"AUDITMANAGER_SECRETS_PUBLIC_KEYS=k1:{public}",
                            "AUDITMANAGER_SECRETS_ACTIVE_KID=k1"), ring)
        assert "readiness OK      executor-source " in whole, whole
        assert private not in whole and public not in whole, "the ring is never printed"

    def test_the_database_source_accepts_a_complete_baseline_and_rejects_an_incomplete_one(self, tmp_path: Path) -> None:
        private, public = _keypair()
        alpha = _with_lines(
            _alpha_env(tmp_path, provider_mode="live"), "AUDITMANAGER_PROVIDER_SOURCE=database",
            f"AUDITMANAGER_SECRETS_PUBLIC_KEYS=k1:{public}", "AUDITMANAGER_SECRETS_ACTIVE_KID=k1")
        provider = _provider_env(tmp_path, AUDITMANAGER_SECRETS_KEYS=f"k1:{private}",
                                 PROXY_LLM_BASE_URL="https://p.example")
        out = self._result(tmp_path, alpha, provider)
        assert "readiness FINDING executor-source " in out and "triplet" in out, out
        complete = _provider_env(
            tmp_path, name="complete.env", AUDITMANAGER_SECRETS_KEYS=f"k1:{private}",
            PROXY_LLM_BASE_URL="https://openrouter.ai/api/v1", PROXY_LLM_TOKEN="test-token",
            PROXY_LLM_MODEL="anthropic/claude-opus-5",
        )
        accepted = self._result(tmp_path, alpha, complete)
        assert "readiness OK      executor-source " in accepted, accepted
        stub = _provider_env(
            tmp_path, name="stub.env", AUDITMANAGER_SECRETS_KEYS=f"k1:{private}",
            PROXY_LLM_BASE_URL="https://openrouter.ai/api/v1", PROXY_LLM_TOKEN="test-token",
            PROXY_LLM_MODEL="proxy",
        )
        refused = self._result(tmp_path, alpha, stub)
        assert "readiness FINDING executor-source " in refused and "gateway stub" in refused, refused

    def test_the_check_is_shown_able_to_fail(self, tmp_path: Path) -> None:
        mutant = _write_mutant(tmp_path, "executor-source")
        completed, _ = _run(
            ("--env-file", str(_alpha_env(tmp_path)), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path, script=mutant,
        )
        assert "executor-source" not in completed.stdout


class TestDbRoles:
    """`PROD-04`. Which role api and worker connect as, and whether it is the restricted one. The docker is the
    stub above: it answers what the running containers' `DATABASE_URL` names, what `ADR-0021` row 7's query returns
    and what `apply-grants.sh --check` finds. Every case has a clean control; the check is shown able to fail by
    deleting its block."""

    @staticmethod
    def _out(tmp_path: Path, stub: dict[str, str] | None = None, **alpha: object) -> tuple[str, subprocess.CompletedProcess[str]]:
        env_file = _alpha_env(tmp_path, **alpha)  # type: ignore[arg-type]
        completed, _ = _run(
            ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path, stub_docker=True, env=stub,
        )
        line = next((raw for raw in completed.stdout.splitlines() if " db-roles " in raw), "")
        return line, completed

    def test_both_services_on_the_restricted_role_and_a_matching_database_is_ok(self, tmp_path: Path) -> None:
        line, completed = self._out(tmp_path)
        assert line.startswith("readiness OK      db-roles "), completed.stdout
        assert f"api={APP_ROLE} worker={APP_ROLE}" in line and "f|f|f|t" in line, line

    def test_it_says_which_role_each_connects_as_and_never_prints_a_password(self, tmp_path: Path) -> None:
        line, completed = self._out(tmp_path)
        assert APP_PASSWORD not in completed.stdout + completed.stderr and PG_PASSWORD not in completed.stdout

    @pytest.mark.parametrize("service", ["API", "WORKER"])
    def test_a_service_still_on_the_owner_role_is_a_finding(self, tmp_path: Path, service: str) -> None:
        owner_url = f"postgresql+psycopg://{PG_USER}:{PG_PASSWORD}@postgres:5432/{PG_DB}"
        line, completed = self._out(tmp_path, {f"STUB_{service}_URL": owner_url})
        assert line.startswith("readiness FINDING db-roles "), completed.stdout
        assert f"{service.lower()} connects as the OWNER role '{PG_USER}'" in line, line
        assert PG_PASSWORD not in completed.stdout

    def test_a_service_on_some_other_role_is_a_finding(self, tmp_path: Path) -> None:
        line, _ = self._out(tmp_path, {"STUB_API_URL": f"postgresql+psycopg://someone_else:x@postgres:5432/{PG_DB}"})
        assert line.startswith("readiness FINDING db-roles ") and "api connects as 'someone_else', not as ALPHA_APP_DB_USER" in line, line

    @pytest.mark.parametrize("facts", ["t|t|t|t", "f|t|f|t", "f|f|t|t", "f|f|f|f"])
    def test_a_role_that_can_do_more_than_the_application_may_is_a_finding(self, tmp_path: Path, facts: str) -> None:
        line, _ = self._out(tmp_path, {"STUB_ROLE_FACTS": facts})
        assert line.startswith("readiness FINDING db-roles ") and f"= {facts}, not f|f|f|t" in line, line

    def test_a_role_the_database_does_not_have_is_a_finding(self, tmp_path: Path) -> None:
        line, _ = self._out(tmp_path, {"STUB_ROLE_FACTS": ""})
        assert line.startswith("readiness FINDING db-roles ") and f"has no role '{APP_ROLE}'" in line, line

    def test_rights_that_differ_from_the_classification_are_a_finding(self, tmp_path: Path) -> None:
        line, _ = self._out(tmp_path, {"STUB_GRANTS_CHECK_OUT": "table audit_event: the role holds TRUNCATE\n"})
        assert line.startswith("readiness FINDING db-roles "), line
        assert "the rights differ from the classification" in line and "the role holds TRUNCATE" in line, line

    def test_no_application_role_configured_is_a_finding(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path)
        text = env_file.read_text(encoding="utf-8").replace(f"ALPHA_APP_DB_USER={APP_ROLE}\n", "")
        env_file.write_text(text, encoding="utf-8")
        completed, _ = _run(("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
                            tmp_path=tmp_path, stub_docker=True)
        assert "readiness FINDING db-roles" in completed.stdout and "ALPHA_APP_DB_USER is '<unset>'" in completed.stdout

    @pytest.mark.parametrize("down", ["STUB_API_DOWN", "STUB_WORKER_DOWN"])
    def test_a_service_that_is_not_running_is_unknown_and_never_ok(self, tmp_path: Path, down: str) -> None:
        line, completed = self._out(tmp_path, {down: "1"})
        assert line.startswith("readiness UNKNOWN db-roles ") and "is not running" in line, line
        assert "OK      db-roles" not in completed.stdout

    def test_a_check_that_could_not_be_run_is_unknown(self, tmp_path: Path) -> None:
        line, _ = self._out(tmp_path, {"STUB_GRANTS_CHECK_STATUS": "2", "STUB_GRANTS_CHECK_ERR": "psql: connection refused\n"})
        assert line.startswith("readiness UNKNOWN db-roles ") and "could not be run" in line, line

    def test_a_finding_outranks_an_unknown(self, tmp_path: Path) -> None:
        line, _ = self._out(tmp_path, {"STUB_API_DOWN": "1", "STUB_ROLE_FACTS": "t|f|f|t"})
        assert line.startswith("readiness FINDING db-roles "), line

    def test_no_docker_on_path_is_unknown_not_ok(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path)
        bare = tmp_path / "bare"
        bare.mkdir()
        for tool in ("bash", "sed", "tr", "cat", "head", "grep", "env", "dirname", "mktemp", "rm", "wc", "awk", "date", "sort", "uniq", "printf", "tail"):
            found = shutil.which(tool)
            if found:
                (bare / tool).symlink_to(found)
        completed, _ = _run(("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
                            tmp_path=tmp_path, env={"PATH": str(bare)})
        assert "readiness UNKNOWN db-roles" in completed.stdout and "no docker on PATH" in completed.stdout, completed.stdout

    def test_the_check_is_shown_able_to_fail(self, tmp_path: Path) -> None:
        mutant = _write_mutant(tmp_path, "db-roles")
        owner_url = f"postgresql+psycopg://{PG_USER}:{PG_PASSWORD}@postgres:5432/{PG_DB}"
        completed, _ = _run(
            ("--env-file", str(_alpha_env(tmp_path)), "--provider-env-file", str(tmp_path / "np.env")),
            tmp_path=tmp_path, script=mutant, stub_docker=True, env={"STUB_API_URL": owner_url},
        )
        assert "db-roles" not in completed.stdout


def test_every_check_in_the_script_has_a_case_here() -> None:
    """The same claim `test_deploy_script_refusals.py` makes about `deploy.sh`'s guards, for
    this script's checks: a check added without a test is caught here, not in a deployment."""
    markers = re.findall(
        r"^# >>> check: ([a-z-]+)$", READINESS.read_text(encoding="utf-8"), re.M
    )
    assert len(markers) == len(set(markers)), markers
    assert len(markers) == 8, markers
    assert set(markers) == {
        "default-credential",
        "db-roles",
        "tls",
        "plain-http",
        "provider-mode",
        "cost-ceiling",
        "executor-source",
        "off-host-backup",
    }, markers


def test_the_script_is_executable_and_runnable_by_its_documented_path() -> None:
    assert READINESS.exists(), "infra/deploy/readiness.sh is missing"
    assert os.access(READINESS, os.X_OK), "infra/deploy/readiness.sh is not executable"
    assert READINESS.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash\n")


def test_it_never_writes_into_the_owner_s_env_directory(tmp_path: Path) -> None:
    """`forbidden_hotspots`: `infra/deploy/env/*.env` is read-only. This does not prove the
    script cannot write there -- it proves the normal path never does, by running it
    against real-shaped inputs and checking the directory `readiness.sh` defaults to is
    untouched when explicit paths are given instead."""
    env_dir = ROOT / "infra/deploy/env"
    before = {p: p.stat().st_mtime_ns for p in env_dir.glob("*.env")}
    env_file = _alpha_env(tmp_path)
    _run(
        ("--env-file", str(env_file), "--provider-env-file", str(tmp_path / "np.env")),
        tmp_path=tmp_path,
    )
    after = {p: p.stat().st_mtime_ns for p in env_dir.glob("*.env")}
    assert before == after
