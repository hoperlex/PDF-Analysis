"""`first_install_env.py`: the environment files of a first install are complete, coherent, private and never overwritten.

What is held, each by a test below:

* every name `deploy.sh` and `apply-grants.sh` read is set, no secret is empty or still the example's, and **every secret is
  equal in each place it is written** (the second copies inside the two database URLs and the two S3 names);
* the files are mode 600, and a second `create` changes **no byte** of either (the rerun of an interrupted install);
* the X25519 pair is a pair: the standard-library implementation is pinned to the RFC 7748 vectors and, where the
  `cryptography` package exists, to the package, and the public half in `alpha.env` is the pair of the private half in
  `provider.env`;
* the repository's own validators accept the generated file: `apply-grants.sh --config-only` and `deploy.sh`'s guards that
  run before docker is touched (docker is a stub that must not be reached before them);
* nothing a command prints carries a secret.

No docker, no network, no daemon.
"""

from __future__ import annotations

import base64
import importlib.util
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "infra" / "deploy"
HELPER = DEPLOY / "lib" / "first_install_env.py"


def _load():
    spec = importlib.util.spec_from_file_location("first_install_env_under_test", HELPER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fie = _load()


@pytest.fixture()
def env_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "env"
    directory.mkdir()
    for name in ("alpha.env.example", "provider.env.example"):
        shutil.copy(DEPLOY / "env" / name, directory / name)
    return directory


def _create(env_dir: Path, instance: str = "my-audit", port: int = 31500, extra=None) -> str:
    return fie.create(env_dir, instance, port, extra or {}, date="20261120")


def test_x25519_matches_the_rfc_7748_vectors() -> None:
    alice = bytes.fromhex("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a")
    bob = bytes.fromhex("5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb")
    assert fie.x25519_public(alice).hex() == "8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a"
    assert fie.x25519_public(bob).hex() == "de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f"
    shared = "4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742"
    assert fie.x25519(alice, fie.x25519_public(bob)).hex() == shared
    assert fie.x25519(bob, fie.x25519_public(alice)).hex() == shared


def test_x25519_matches_the_cryptography_package_when_it_is_installed() -> None:
    primitives = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.x25519")
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    for _ in range(5):
        private = os.urandom(32)
        key = primitives.X25519PrivateKey.from_private_bytes(private)
        expected = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        assert fie.x25519_public(private) == expected


def test_create_writes_both_files_private_and_complete(env_dir: Path) -> None:
    assert _create(env_dir) == "created"
    for name in ("alpha.env", "provider.env"):
        assert stat.S_IMODE((env_dir / name).stat().st_mode) == 0o600
    values = fie.parse_env((env_dir / "alpha.env").read_text())
    for name in fie.REQUIRED_NAMES:
        assert values.get(name), f"{name} must be set and non-empty"
    assert values["ALPHA_INSTANCE"] == "my-audit"
    assert values["ALPHA_HTTP_PORT"] == "31500"
    assert values["S3_BUCKET"] == "my-audit"
    assert values["POSTGRES_DB"] == "my_audit"
    assert values["AUDITMANAGER_PROVIDER_MODE"] == "live"
    assert values["AUDITMANAGER_PROVIDER_SOURCE"] == "database"
    assert values["ALPHA_LOCAL_AGENT"] == "auto"
    assert fie.check(env_dir / "alpha.env", env_dir / "provider.env", env_dir / "alpha.env.example") == []


def test_no_secret_is_empty_or_the_examples_and_duplicates_are_equal(env_dir: Path) -> None:
    _create(env_dir)
    values = fie.parse_env((env_dir / "alpha.env").read_text())
    example = fie.parse_env((env_dir / "alpha.env.example").read_text())
    for name in fie.PLACEHOLDER_NAMES + ("ALPHA_APP_DB_PASSWORD", "AUDITMANAGER_SECRETS_PUBLIC_KEYS"):
        assert values[name], name
        assert values[name] != example.get(name), f"{name} is still the example's"
    migrator = fie.URL_PATTERN.match(values["MIGRATOR_DATABASE_URL"])
    application = fie.URL_PATTERN.match(values["DATABASE_URL"])
    assert migrator and application
    assert (migrator.group(1), migrator.group(2), migrator.group(5)) == (
        values["POSTGRES_USER"], values["POSTGRES_PASSWORD"], values["POSTGRES_DB"])
    assert (application.group(1), application.group(2), application.group(5)) == (
        values["ALPHA_APP_DB_USER"], values["ALPHA_APP_DB_PASSWORD"], values["POSTGRES_DB"])
    assert values["S3_ACCESS_KEY_ID"] == values["MINIO_ROOT_USER"]
    assert values["S3_SECRET_ACCESS_KEY"] == values["MINIO_ROOT_PASSWORD"]
    assert values["ALPHA_APP_DB_PASSWORD"] != values["POSTGRES_PASSWORD"]
    assert fie.APP_PASSWORD_PATTERN.fullmatch(values["ALPHA_APP_DB_PASSWORD"])
    # The secrets of the example file are gone from the text altogether, not only from the live lines.
    text = (env_dir / "alpha.env").read_text()
    assert "change-me" not in "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def test_two_creations_draw_different_secrets(env_dir: Path, tmp_path: Path) -> None:
    other = tmp_path / "other"
    other.mkdir()
    for name in ("alpha.env.example", "provider.env.example"):
        shutil.copy(DEPLOY / "env" / name, other / name)
    _create(env_dir)
    _create(other)
    first = fie.parse_env((env_dir / "alpha.env").read_text())
    second = fie.parse_env((other / "alpha.env").read_text())
    for name in ("POSTGRES_PASSWORD", "ALPHA_APP_DB_PASSWORD", "MINIO_ROOT_PASSWORD", "AUDITMANAGER_API_TOKEN",
                 "AUDITMANAGER_SECRETS_PUBLIC_KEYS"):
        assert first[name] != second[name]


def test_the_public_key_in_alpha_is_the_pair_of_the_private_key_in_provider(env_dir: Path) -> None:
    _create(env_dir)
    values = fie.parse_env((env_dir / "alpha.env").read_text())
    private_ring = fie.parse_env((env_dir / "provider.env").read_text())["AUDITMANAGER_SECRETS_KEYS"]
    kid = values["AUDITMANAGER_SECRETS_ACTIVE_KID"]
    public_kid, _, public_b64 = values["AUDITMANAGER_SECRETS_PUBLIC_KEYS"].partition(":")
    private_kid, _, private_b64 = private_ring.partition(":")
    assert public_kid == private_kid == kid
    assert fie.x25519_public(base64.b64decode(private_b64, validate=True)) == base64.b64decode(public_b64, validate=True)


def test_a_mismatched_pair_is_reported_without_printing_a_key(env_dir: Path) -> None:
    _create(env_dir)
    provider = env_dir / "provider.env"
    kid = fie.parse_env((env_dir / "alpha.env").read_text())["AUDITMANAGER_SECRETS_ACTIVE_KID"]
    wrong = base64.b64encode(os.urandom(32)).decode()
    provider.write_text(fie.set_value(provider.read_text(), "AUDITMANAGER_SECRETS_KEYS", f"{kid}:{wrong}"))
    problems = fie.check(env_dir / "alpha.env", provider, env_dir / "alpha.env.example")
    assert problems and all(wrong not in problem for problem in problems)


def test_a_rerun_does_not_touch_either_file(env_dir: Path) -> None:
    assert _create(env_dir) == "created"
    before = {name: (env_dir / name).read_bytes() for name in ("alpha.env", "provider.env")}
    inode = {name: (env_dir / name).stat().st_ino for name in before}
    assert _create(env_dir, instance="another-name", port=8081) == "exists"
    for name, content in before.items():
        assert (env_dir / name).read_bytes() == content
        assert (env_dir / name).stat().st_ino == inode[name]


def test_an_existing_provider_without_alpha_is_refused_and_left_alone(env_dir: Path) -> None:
    (env_dir / "provider.env").write_text("ANTHROPIC_API_KEY=\n")
    with pytest.raises(ValueError):
        _create(env_dir)
    assert (env_dir / "provider.env").read_text() == "ANTHROPIC_API_KEY=\n"
    assert not (env_dir / "alpha.env").exists()


def test_no_temporary_file_is_left_behind(env_dir: Path) -> None:
    _create(env_dir)
    _create(env_dir)
    assert sorted(path.name for path in env_dir.iterdir()) == [
        "alpha.env", "alpha.env.example", "provider.env", "provider.env.example"]


@pytest.mark.parametrize("bad", ["Ab", "a", "-abc", "abc-", "a_b_c", "x" * 41, "has space", "UPPER"])
def test_a_bad_instance_name_is_refused(env_dir: Path, bad: str) -> None:
    with pytest.raises(ValueError):
        _create(env_dir, instance=bad)
    assert not (env_dir / "alpha.env").exists()


def test_set_option_is_limited_to_names_the_example_mentions_and_never_a_generated_one(env_dir: Path) -> None:
    with pytest.raises(ValueError):
        _create(env_dir, extra={"NOT_A_NAME_IN_THE_EXAMPLE": "1"})
    with pytest.raises(ValueError):
        _create(env_dir, extra={"POSTGRES_PASSWORD": "weak"})
    with pytest.raises(ValueError):
        _create(env_dir, extra={"ALPHA_NORM_EMBED": "yes please"})
    assert _create(env_dir, extra={"ALPHA_NORM_EMBED": "yes", "ALPHA_MEM_LIMIT_NORM_EMBED": "1200m"}) == "created"
    values = fie.parse_env((env_dir / "alpha.env").read_text())
    assert values["ALPHA_NORM_EMBED"] == "yes" and values["ALPHA_MEM_LIMIT_NORM_EMBED"] == "1200m"


def test_set_value_replaces_the_last_live_line_or_fills_the_template() -> None:
    text = "A=1\n#B=\n# comment\nC=3\n"
    assert fie.set_value(text, "A", "9") == "A=9\n#B=\n# comment\nC=3\n"
    assert fie.set_value(text, "B", "2") == "A=1\n#B=\nB=2\n# comment\nC=3\n"
    assert fie.set_value(text, "Z", "7") == text + "Z=7\n"
    assert fie.set_value("A=1", "Z", "7") == "A=1\nZ=7\n"


def test_command_line_set_get_and_check(env_dir: Path) -> None:
    _create(env_dir)
    env = str(env_dir / "alpha.env")
    run = lambda *args: subprocess.run([sys.executable, str(HELPER), *args], capture_output=True, text=True)  # noqa: E731
    done = run("set", "--env", env, "ALPHA_CERT_NAME=audit.example.org", "ALPHA_ACME_STAGING=yes")
    assert done.returncode == 0, done.stdout + done.stderr
    assert stat.S_IMODE((env_dir / "alpha.env").stat().st_mode) == 0o600
    assert run("get", "--env", env, "ALPHA_CERT_NAME").stdout.strip() == "audit.example.org"
    refused = run("get", "--env", env, "POSTGRES_PASSWORD")
    assert refused.returncode == 2
    secret = fie.parse_env((env_dir / "alpha.env").read_text())["POSTGRES_PASSWORD"]
    assert secret not in refused.stdout + refused.stderr
    assert run("set", "--env", env, "ALPHA_CERT_NAME=has space").returncode == 3
    checked = run("check", "--env", env, "--provider", str(env_dir / "provider.env"),
                  "--example", str(env_dir / "alpha.env.example"))
    assert checked.returncode == 0, checked.stdout


def test_check_names_a_loose_mode_and_a_placeholder_without_printing_a_value(env_dir: Path) -> None:
    _create(env_dir)
    alpha = env_dir / "alpha.env"
    alpha.chmod(0o644)
    text = fie.set_value(alpha.read_text(), "AUDITMANAGER_API_TOKEN", "change-me-this-example-token-authorizes-nothing")
    alpha.write_text(text)
    done = subprocess.run(
        [sys.executable, str(HELPER), "check", "--env", str(alpha), "--provider", str(env_dir / "provider.env"),
         "--example", str(env_dir / "alpha.env.example")], capture_output=True, text=True)
    assert done.returncode == 3
    assert "AUDITMANAGER_API_TOKEN" in done.stdout and "must be 600" in done.stdout
    assert "authorizes-nothing" not in done.stdout


def test_create_prints_no_value(env_dir: Path) -> None:
    done = subprocess.run(
        [sys.executable, str(HELPER), "create", "--env-dir", str(env_dir), "--instance", "my-audit", "--http-port", "31500"],
        capture_output=True, text=True)
    assert done.returncode == 0
    values = fie.parse_env((env_dir / "alpha.env").read_text())
    out = done.stdout + done.stderr
    for name in ("POSTGRES_PASSWORD", "ALPHA_APP_DB_PASSWORD", "MINIO_ROOT_PASSWORD", "AUDITMANAGER_API_TOKEN"):
        assert values[name] not in out
    again = subprocess.run(
        [sys.executable, str(HELPER), "create", "--env-dir", str(env_dir), "--instance", "my-audit", "--http-port", "31500"],
        capture_output=True, text=True)
    assert again.returncode == 4


# ---- the repository's own validators accept what was generated --------------------------------------------------------


def test_apply_grants_config_check_accepts_the_generated_file(env_dir: Path) -> None:
    _create(env_dir)
    done = subprocess.run(
        [str(DEPLOY / "apply-grants.sh"), "--env-file", str(env_dir / "alpha.env"), "--config-only"],
        capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr


def test_deploy_sh_guards_before_docker_accept_the_generated_file(env_dir: Path, tmp_path: Path) -> None:
    """`deploy.sh` prints `deploy.sh: instance ...` only after every guard that answers before docker is touched
    (`placeholder-secrets`, `derived-secrets-coherent`, `app-db-role-configured`, the TLS settings, the build context). A
    `docker` stub that fails every call stops it right after, and the test reads where it stopped."""
    _create(env_dir)
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    (stub_dir / "docker").write_text("#!/bin/sh\necho \"stub docker: $*\" >&2\nexit 1\n")
    (stub_dir / "docker").chmod(0o755)
    environment = dict(os.environ, PATH=f"{stub_dir}:{os.environ['PATH']}", STAND_COPY_RECORD=str(tmp_path / "none" / "record.json"),
                       BUNDLE_STAGING=str(tmp_path / "none" / "bundles"))
    done = subprocess.run(
        [str(DEPLOY / "deploy.sh"), "--env-file", str(env_dir / "alpha.env")],
        capture_output=True, text=True, env=environment, cwd=ROOT, timeout=120)
    output = done.stdout + done.stderr
    assert "REFUSED" not in output.split("deploy.sh: instance")[0], output[-1500:]
    assert re.search(r"^deploy\.sh: instance +my-audit$", output, re.M), output[-1500:]
    secrets = fie.parse_env((env_dir / "alpha.env").read_text())
    for name in ("POSTGRES_PASSWORD", "ALPHA_APP_DB_PASSWORD", "AUDITMANAGER_API_TOKEN"):
        assert secrets[name] not in output


def test_the_recorded_environment_mode_can_be_asked_for_and_still_checks_clean(env_dir: Path) -> None:
    """`--set AUDITMANAGER_PROVIDER_MODE=recorded --set AUDITMANAGER_PROVIDER_SOURCE=environment` is the owner's way to a
    stand that replays fixtures and needs no executor connection; the key ring is generated either way."""
    extra = {"AUDITMANAGER_PROVIDER_MODE": "recorded", "AUDITMANAGER_PROVIDER_SOURCE": "environment"}
    assert _create(env_dir, extra=extra) == "created"
    values = fie.parse_env((env_dir / "alpha.env").read_text())
    assert values["AUDITMANAGER_PROVIDER_MODE"] == "recorded" and values["AUDITMANAGER_PROVIDER_SOURCE"] == "environment"
    assert fie.check(env_dir / "alpha.env", env_dir / "provider.env", env_dir / "alpha.env.example") == []
