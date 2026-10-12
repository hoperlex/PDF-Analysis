"""The promotion database's scripts, with ``docker``, ``df`` and ``free`` stubbed on ``PATH``.

No container starts here. The stubs log every ``docker`` argv, so each refusal is proved to
come before any docker call, and the happy paths are proved to touch only the promotion
project and a disposable instance removed by its own name.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.integration.norms.repair.support import REPOSITORY_ROOT

SCRIPTS = REPOSITORY_ROOT / "scripts" / "promotion"
COMPOSE = REPOSITORY_ROOT / "infra" / "promotion" / "compose.yml"
PASSWORD = "Pr0motion-passw0rd_long"
FINGERPRINT = "alembic_version|1|abc\nnorm_repair_call|3|def"

DOCKER_STUB = r"""#!/usr/bin/env bash
printf '%s\n' "$*" >> "${STUB_LOG}"
case "$*" in
  *"pg_tables"*) printf '%s\n' "${STUB_TABLES:-0}" ;;
  *"exec -T postgres pg_restore"*) cat > /dev/null ;;
  *"exec -T postgres psql"*)
    count=$(cat "${STUB_DIR}/fp_count" 2>/dev/null || echo 0)
    count=$((count + 1)); echo "${count}" > "${STUB_DIR}/fp_count"
    cat > /dev/null
    if [ -n "${STUB_FP_DRIFT:-}" ] && [ "${count}" -gt 1 ]; then printf 'drifted\n'; else printf '%s\n' "${STUB_FP}"; fi ;;
  *"exec -T postgres pg_dump"*) printf 'PGDMP fake custom-format dump\n' ;;
  *"exec -i"*"pg_restore"*) cat > /dev/null ;;
  *"exec -i"*"psql"*) cat > /dev/null; printf '%s\n' "${STUB_RESTORED_FP:-${STUB_FP}}" ;;
  *) : ;;
esac
exit 0
"""
DF_STUB = "#!/usr/bin/env bash\nprintf 'Avail\\n%s\\n' \"${STUB_DF}\"\n"
FREE_STUB = (
    "#!/usr/bin/env bash\n"
    "printf '               total        used        free      shared  buff/cache   available\\n'\n"
    "printf 'Mem:     100 1 1 1 1 %s\\n' \"${STUB_FREE}\"\n"
)
GIB = 1024**3


@pytest.fixture
def stubs(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("docker", DOCKER_STUB), ("df", DF_STUB), ("free", FREE_STUB)):
        path = bin_dir / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
    env_file = tmp_path / "promotion.env"
    env_file.write_text(
        "POSTGRES_DB=promotion\nPOSTGRES_USER=promotion\n"
        f"POSTGRES_PASSWORD={PASSWORD}\nPROMOTION_POSTGRES_PORT=57190\n",
        encoding="utf-8",
    )
    return {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "HOME": str(tmp_path),
        "STUB_LOG": str(tmp_path / "docker.log"),
        "STUB_DIR": str(tmp_path),
        "STUB_FP": FINGERPRINT,
        "STUB_DF": str(50 * GIB),
        "STUB_FREE": str(8 * GIB),
        "PROMOTION_ENV": str(env_file),
        "PROMOTION_DUMPS": str(tmp_path / "dumps"),
    }


def _run(script: str, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPTS / script), *args], env=env, capture_output=True, text=True,
        timeout=60, check=False,
    )


def _docker_calls(env: dict[str, str]) -> list[str]:
    log = Path(env["STUB_LOG"])
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def test_shellcheck_finds_nothing() -> None:
    if shutil.which("shellcheck") is None:
        pytest.skip("shellcheck is not installed on this host")
    completed = subprocess.run(
        ["shellcheck", "-x", *(str(p.relative_to(REPOSITORY_ROOT)) for p in sorted(SCRIPTS.glob("*.sh")))],
        cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_no_script_can_remove_the_volume() -> None:
    for script in SCRIPTS.glob("*.sh"):
        text = script.read_text(encoding="utf-8")
        assert "--volumes" not in text or "docker rm --force --volumes \"${name}\"" in text, script
        assert not re.search(r"\bdown\b.*-v\b", text), script
        assert "pkill" not in text and "killall" not in text, script


def test_the_compose_file_is_its_own_small_project_on_loopback() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    assert re.search(r"(?m)^name: auditmanager-promotion$", text)
    assert "name: auditmanager-promotion-data" in text
    assert re.search(r"(?m)^    mem_limit: 1g$", text)
    assert "shared_buffers=128MB" in text
    assert '"127.0.0.1:${PROMOTION_POSTGRES_PORT:?' in text
    assert ":-" not in text.split("ports:")[1].split("volumes:")[0], "the port has a default"


def test_a_missing_env_file_refuses_before_docker(stubs: dict[str, str], tmp_path: Path) -> None:
    stubs["PROMOTION_ENV"] = str(tmp_path / "absent.env")
    for script, args in (("dump.sh", ()), ("verify-dump.sh", ()), ("restore.sh", ()), ("stack.sh", ("up",))):
        completed = _run(script, stubs, *args)
        assert completed.returncode == 3, (script, completed.stderr)
        assert "no env file" in completed.stderr
    assert _docker_calls(stubs) == []


def test_a_weak_password_refuses_and_is_never_printed(stubs: dict[str, str], tmp_path: Path) -> None:
    env_file = Path(stubs["PROMOTION_ENV"])
    env_file.write_text(env_file.read_text().replace(PASSWORD, "shortpw"), encoding="utf-8")
    completed = _run("stack.sh", stubs, "up")
    assert completed.returncode == 3
    assert "POSTGRES_PASSWORD must be" in completed.stderr
    assert "shortpw" not in completed.stderr + completed.stdout
    assert _docker_calls(stubs) == []


def test_the_disk_floor_refuses_a_dump_before_docker(stubs: dict[str, str]) -> None:
    stubs["STUB_DF"] = str(3 * GIB)  # a dump needs 1 + 3 GiB
    completed = _run("dump.sh", stubs)
    assert completed.returncode == 3
    assert "disk floor" in completed.stderr
    assert _docker_calls(stubs) == []


def test_the_memory_floor_refuses_a_dump_before_docker(stubs: dict[str, str]) -> None:
    stubs["STUB_FREE"] = str(5 * GIB)
    completed = _run("dump.sh", stubs)
    assert completed.returncode == 3
    assert "memory floor" in completed.stderr
    assert _docker_calls(stubs) == []


def _dump(stubs: dict[str, str]) -> Path:
    completed = _run("dump.sh", stubs)
    assert completed.returncode == 0, completed.stderr
    return Path(completed.stdout.splitlines()[0].removeprefix("dump: "))


def test_a_dump_is_atomic_checksummed_and_fingerprinted(stubs: dict[str, str]) -> None:
    dump = _dump(stubs)
    import hashlib

    assert dump.read_bytes() == b"PGDMP fake custom-format dump\n"
    assert dump.with_name(dump.name + ".sha256").read_text().split()[0] == hashlib.sha256(
        dump.read_bytes()
    ).hexdigest()
    assert dump.with_name(dump.name + ".fingerprint").read_text().strip() == FINGERPRINT
    assert not list(dump.parent.glob("*.partial"))
    calls = _docker_calls(stubs)
    assert all("--project-name auditmanager-promotion" in call for call in calls)
    assert PASSWORD not in "\n".join(calls)


def test_a_database_written_during_the_dump_keeps_no_dump(stubs: dict[str, str]) -> None:
    stubs["STUB_FP_DRIFT"] = "1"
    completed = _run("dump.sh", stubs)
    assert completed.returncode == 3
    assert "changed while it was dumped" in completed.stderr
    assert not list(Path(stubs["PROMOTION_DUMPS"]).glob("promotion-*"))


def test_verify_restores_into_a_disposable_instance_and_keeps_one_dump(
    stubs: dict[str, str], tmp_path: Path
) -> None:
    dumps = Path(stubs["PROMOTION_DUMPS"])
    older = _dump(stubs)
    renamed = dumps / "promotion-20000101T000000Z.dump"
    for suffix in ("", ".sha256", ".fingerprint"):
        Path(str(older) + suffix).rename(str(renamed) + suffix)
    sums = Path(str(renamed) + ".sha256")
    sums.write_text(sums.read_text().replace(older.name, renamed.name))
    latest = _dump(stubs)
    Path(stubs["STUB_LOG"]).unlink()

    completed = _run("verify-dump.sh", stubs)
    assert completed.returncode == 0, completed.stderr
    assert sorted(p.name for p in dumps.iterdir()) == sorted(
        [latest.name, latest.name + ".sha256", latest.name + ".fingerprint", latest.name + ".verified"]
    )
    calls = _docker_calls(stubs)
    (run,) = [call for call in calls if call.startswith("run ")]
    assert "--network none" in run and "--publish" not in run and " -p " not in run
    name = re.search(r"--name (\S+)", run).group(1)
    assert name.startswith("auditmanager-promotion-verify-")
    assert calls[-1] == f"rm --force --volumes {name}"


def test_verify_refuses_a_dump_that_fails_its_sha_before_docker(stubs: dict[str, str]) -> None:
    dump = _dump(stubs)
    Path(stubs["STUB_LOG"]).unlink()
    dump.write_bytes(b"tampered")
    completed = _run("verify-dump.sh", stubs, str(dump))
    assert completed.returncode == 3
    assert "fails its SHA-256" in completed.stderr
    assert _docker_calls(stubs) == []


def test_verify_refuses_a_restore_that_does_not_reproduce_the_fingerprint(stubs: dict[str, str]) -> None:
    dump = _dump(stubs)
    Path(stubs["STUB_LOG"]).unlink()
    stubs["STUB_RESTORED_FP"] = "norm_repair_call|2|zzz"
    completed = _run("verify-dump.sh", stubs, str(dump))
    assert completed.returncode == 3
    assert "does not reproduce" in completed.stderr
    assert not Path(str(dump) + ".verified").exists()
    assert _docker_calls(stubs)[-1].startswith("rm --force --volumes auditmanager-promotion-verify-")


def test_run_hands_the_url_to_one_command_without_printing_it(stubs: dict[str, str]) -> None:
    completed = _run(
        "stack.sh", stubs, "run", "--", "bash", "-c",
        'case "$DATABASE_URL" in postgresql+psycopg://promotion:*@127.0.0.1:57190/promotion) exit 0;; *) exit 9;; esac',
    )
    assert completed.returncode == 0, completed.stderr
    assert PASSWORD not in completed.stdout + completed.stderr


def test_an_unknown_verb_is_a_usage_error(stubs: dict[str, str]) -> None:
    completed = _run("stack.sh", stubs, "destroy")
    assert completed.returncode == 2
    assert _docker_calls(stubs) == []


def _verified_dump(stubs: dict[str, str]) -> Path:
    dump = _dump(stubs)
    assert _run("verify-dump.sh", stubs, str(dump)).returncode == 0
    Path(stubs["STUB_LOG"]).unlink()
    return dump


def test_restore_refuses_a_dump_that_was_never_verified_before_docker(stubs: dict[str, str]) -> None:
    dump = _dump(stubs)
    Path(stubs["STUB_LOG"]).unlink()
    completed = _run("restore.sh", stubs, str(dump))
    assert completed.returncode == 3
    assert "never restore-verified" in completed.stderr
    assert _docker_calls(stubs) == []


def test_restore_never_writes_over_a_database_that_holds_tables(stubs: dict[str, str]) -> None:
    _verified_dump(stubs)
    stubs["STUB_TABLES"] = "17"
    completed = _run("restore.sh", stubs)
    assert completed.returncode == 3
    assert "not empty" in completed.stderr
    assert not any("pg_restore" in call for call in _docker_calls(stubs))


def test_restore_loads_the_latest_verified_dump_into_an_empty_database(stubs: dict[str, str]) -> None:
    dump = _verified_dump(stubs)
    completed = _run("restore.sh", stubs)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith(f"restored: {dump}")
    calls = _docker_calls(stubs)
    assert any("exec -T postgres pg_restore --exit-on-error" in call for call in calls)
    assert all("--project-name auditmanager-promotion" in call for call in calls)
