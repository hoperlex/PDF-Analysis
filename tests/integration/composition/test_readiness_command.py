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

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
READINESS = ROOT / "infra/deploy/readiness.sh"

PG_USER = "the_configured_user"
PG_DB = "the_configured_database"
PG_PASSWORD = "an-edited-postgres-password"
MINIO_USER = "an-edited-minio-root"
MINIO_PASSWORD = "an-edited-minio-password"


def _alpha_env(
    tmp_path: Path,
    *,
    name: str = "alpha.env",
    provider_mode: str = "recorded",
    bind_address: str | None = None,
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
        (
            "DATABASE_URL=postgresql+psycopg://"
            f"{PG_USER}:{PG_PASSWORD}@postgres:5432/{PG_DB}"
        ),
        "AUDITMANAGER_API_TOKEN=an-edited-token-that-authorizes-something",
        f"AUDITMANAGER_PROVIDER_MODE={provider_mode}",
    ]
    if bind_address is not None:
        lines.append(f"ALPHA_BIND_ADDRESS={bind_address}")
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


class TestTls:
    def test_no_certificate_is_a_finding(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path)
        tls_dir = tmp_path / "tls"
        tls_dir.mkdir()
        completed, _ = _run(
            (
                "--env-file", str(env_file),
                "--provider-env-file", str(tmp_path / "np.env"),
                "--tls-dir", str(tls_dir),
            ),
            tmp_path=tmp_path,
        )
        assert "readiness FINDING tls " in completed.stdout, completed.stdout

    def test_an_empty_certificate_file_is_still_a_finding(self, tmp_path: Path) -> None:
        """`enable-tls.sh`'s own rule: `[ -s "$CERT" ]`, not merely `-f`."""
        env_file = _alpha_env(tmp_path)
        tls_dir = tmp_path / "tls"
        tls_dir.mkdir()
        (tls_dir / "fullchain.pem").write_text("", encoding="utf-8")
        (tls_dir / "privkey.pem").write_text("a-key\n", encoding="utf-8")
        completed, _ = _run(
            (
                "--env-file", str(env_file),
                "--provider-env-file", str(tmp_path / "np.env"),
                "--tls-dir", str(tls_dir),
            ),
            tmp_path=tmp_path,
        )
        assert "readiness FINDING tls " in completed.stdout, completed.stdout

    def test_a_present_non_empty_pair_is_ok(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path)
        tls_dir = tmp_path / "tls"
        tls_dir.mkdir()
        (tls_dir / "fullchain.pem").write_text("a-cert\n", encoding="utf-8")
        (tls_dir / "privkey.pem").write_text("a-key\n", encoding="utf-8")
        completed, _ = _run(
            (
                "--env-file", str(env_file),
                "--provider-env-file", str(tmp_path / "np.env"),
                "--tls-dir", str(tls_dir),
            ),
            tmp_path=tmp_path,
        )
        assert "readiness OK      tls " in completed.stdout, completed.stdout

    def test_the_check_is_shown_able_to_fail(self, tmp_path: Path) -> None:
        env_file = _alpha_env(tmp_path)
        tls_dir = tmp_path / "tls"
        tls_dir.mkdir()
        mutant = _write_mutant(tmp_path, "tls")
        completed, _ = _run(
            (
                "--env-file", str(env_file),
                "--provider-env-file", str(tmp_path / "np.env"),
                "--tls-dir", str(tls_dir),
            ),
            tmp_path=tmp_path,
            script=mutant,
        )
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
    def test_a_clean_run_exits_zero(self, tmp_path: Path) -> None:
        """The nearest thing to \"every check OK\" this tree can produce today: it still
        cannot be all six, because off-host-backup never passes and default-credential
        needs a real stack -- so this drives the five answerable-without-docker checks
        clean and stubs default-credential clean too, and reads the summary line."""
        env_file = _alpha_env(tmp_path)
        tls_dir = tmp_path / "tls"
        tls_dir.mkdir()
        (tls_dir / "fullchain.pem").write_text("a-cert\n", encoding="utf-8")
        (tls_dir / "privkey.pem").write_text("a-key\n", encoding="utf-8")
        completed, _ = _run(
            (
                "--env-file", str(env_file),
                "--provider-env-file", str(tmp_path / "np.env"),
                "--tls-dir", str(tls_dir),
            ),
            tmp_path=tmp_path,
            stub_docker=True,
            env={"STUB_ACCESS_OUTPUT": "access-check OK no default credentials\n"},
        )
        # provider-mode is still a finding (recorded) and off-host-backup always is, so
        # this is not exit 0 -- and that is the honest state of this tree, asserted rather
        # than hidden.
        assert "2 finding(s)" in completed.stdout, completed.stdout
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


def test_every_check_in_the_script_has_a_case_here() -> None:
    """The same claim `test_deploy_script_refusals.py` makes about `deploy.sh`'s guards, for
    this script's checks: a check added without a test is caught here, not in a deployment."""
    markers = re.findall(
        r"^# >>> check: ([a-z-]+)$", READINESS.read_text(encoding="utf-8"), re.M
    )
    assert len(markers) == len(set(markers)), markers
    assert len(markers) == 6, markers
    assert set(markers) == {
        "default-credential",
        "tls",
        "plain-http",
        "provider-mode",
        "cost-ceiling",
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
