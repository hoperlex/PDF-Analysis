"""PROD-04-DB-ROLES-01: every refusal `infra/deploy/apply-grants.sh` makes, shown able to fail, and the
protocol it speaks to `psql`.

The shape of each case is the one `deploy.sh` and `reset.sh` are held to: an invocation that should trip a guard
exits 3, names the reason by its typed word, and makes **no `docker` call at all** (an empty call log is the
evidence the refusal came first); and the same invocation against a **mutant copy with exactly that guard block
deleted** no longer produces that refusal. `docker` is a stub on `PATH` that records `argv` and standard input
and answers from the environment; it reaches no daemon.

What the stub lets this file say that the real-database test (`tests/integration/db/
test_application_role_grants.py`) cannot: the password reaches `psql` on standard input and on no command
line; `--check` sends the verification and nothing that changes anything; a `psql` failure is exit 4 and a
`[grants_unclassified]` raised by the SQL is exit 3; nothing the script prints contains the password.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "infra/deploy/apply-grants.sh"
COMPOSE = ROOT / "infra/deploy/compose.server.yml"

REFUSED = 3
FAILED = 4

OWNER = "the_owner_role"
OWNER_PASSWORD = "an-owner-password-that-is-not-the-app-one"
APP_ROLE = "the_app_role"
APP_PASSWORD = "an-application-password-0123456789"
DATABASE = "the_configured_database"

DOCKER = r'''#!/usr/bin/env python3
"""A `docker` that records argv and stdin, answers the psql the script runs, and reaches nothing."""
import json
import os
import sys

argv = sys.argv[1:]
stdin = ""
is_psql = argv[5:6] == ["exec"] and "psql" in argv
if is_psql:
    stdin = sys.stdin.read()
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"argv": argv, "stdin": stdin}) + "\n")
if not is_psql:
    sys.exit(0)
applying = "\\set app_password" in stdin
prefix = "STUB_APPLY" if applying else "STUB_CHECK"
sys.stdout.write(os.environ.get(prefix + "_OUT", ""))
sys.stderr.write(os.environ.get(prefix + "_ERR", ""))
sys.exit(int(os.environ.get(prefix + "_STATUS", "0")))
'''


def _env_text(**overrides: str | None) -> str:
    values: dict[str, str | None] = {
        "ALPHA_INSTANCE": "an-instance",
        "POSTGRES_DB": DATABASE,
        "POSTGRES_USER": OWNER,
        "POSTGRES_PASSWORD": OWNER_PASSWORD,
        "ALPHA_APP_DB_USER": APP_ROLE,
        "ALPHA_APP_DB_PASSWORD": APP_PASSWORD,
        "DATABASE_URL": f"postgresql+psycopg://{APP_ROLE}:{APP_PASSWORD}@postgres:5432/{DATABASE}",
        "MIGRATOR_DATABASE_URL": f"postgresql+psycopg://{OWNER}:{OWNER_PASSWORD}@postgres:5432/{DATABASE}",
    }
    values.update(overrides)
    return "".join(f"{name}={value}\n" for name, value in values.items() if value is not None)


def _stage(tmp_path: Path, *, script: Path = SCRIPT, with_compose: bool = True, env: str | None = None,
           with_env: bool = True) -> tuple[Path, Path]:
    deploy = tmp_path / "repo/infra/deploy"
    (deploy / "env").mkdir(parents=True, exist_ok=True)
    staged = deploy / "apply-grants.sh"
    staged.write_text(script.read_text(encoding="utf-8"), encoding="utf-8")
    staged.chmod(0o755)
    if with_compose:
        shutil.copy2(COMPOSE, deploy / "compose.server.yml")
    env_file = deploy / "env/alpha.env"
    if with_env:
        env_file.write_text(env if env is not None else _env_text(), encoding="utf-8")
    return staged, env_file


def _run(staged: Path, env_file: Path, *args: str, tmp_path: Path, stub: dict[str, str] | None = None,
         with_env_flag: bool = True) -> tuple[subprocess.CompletedProcess[str], list[dict[str, object]]]:
    binary = tmp_path / "bin"
    binary.mkdir(exist_ok=True)
    docker = binary / "docker"
    docker.write_text(DOCKER, encoding="utf-8")
    docker.chmod(0o755)
    log = tmp_path / "docker.log"
    log.write_text("", encoding="utf-8")
    environment = dict(os.environ)
    environment["PATH"] = f"{binary}{os.pathsep}{environment['PATH']}"
    environment["STUB_LOG"] = str(log)
    environment.pop("ALPHA_ENV_FILE", None)
    environment.update(stub or {})
    command = [str(staged), *(["--env-file", str(env_file)] if with_env_flag else []), *args]
    done = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=60, check=False)
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]
    return done, calls


def _mutant(tmp_path: Path, guard: str) -> Path:
    source = SCRIPT.read_text(encoding="utf-8")
    block = re.compile(
        rf"^# >>> guard: {re.escape(guard)}\n.*?^# <<< guard: {re.escape(guard)}\n", re.DOTALL | re.MULTILINE,
    )
    mutated, count = block.subn("", source)
    assert count == 1, f"the guard markers for {guard!r} are not a single block"
    cut = tmp_path / "mutant.sh"
    cut.write_text(mutated, encoding="utf-8")
    return cut


# --- every guard: refuses, names its word, touches no docker; its deletion stops the refusal ------------------

#: guard name -> (the invocation that trips it, the word or phrase the refusal carries)
_CASES: dict[str, tuple[dict[str, object], str]] = {
    "known-options": ({"args": ("--chek",)}, "unrecognised option: --chek"),
    "env-file-present": ({"with_env": False}, "is missing or unreadable"),
    "owner-configured": ({"env": _env_text(POSTGRES_USER=None)}, "names no POSTGRES_USER"),
    "app-role-well-formed": ({"env": _env_text(ALPHA_APP_DB_USER="Bad-Name")}, "[app_db_role_invalid]"),
    "app-role-not-owner": ({"env": _env_text(ALPHA_APP_DB_USER=OWNER)}, "[app_db_role_is_owner]"),
    "app-password-set": ({"env": _env_text(ALPHA_APP_DB_PASSWORD=None)}, "[app_db_password_unset]"),
    "app-password-shape": ({"env": _env_text(ALPHA_APP_DB_PASSWORD="short")}, "[app_db_password_shape]"),
    "app-password-differs": (
        {"env": _env_text(ALPHA_APP_DB_PASSWORD=OWNER_PASSWORD,
                          DATABASE_URL=f"postgresql+psycopg://{APP_ROLE}:{OWNER_PASSWORD}@postgres:5432/{DATABASE}")},
        "[app_db_password_is_owner_password]"),
    "database-urls-coherent": (
        {"env": _env_text(DATABASE_URL=f"postgresql+psycopg://{OWNER}:{OWNER_PASSWORD}@postgres:5432/{DATABASE}")},
        "[database_urls_incoherent]"),
    "compose-file-present": ({"with_compose": False}, "compose.server.yml is missing"),
}


@pytest.mark.parametrize("guard", sorted(_CASES))
def test_each_guard_refuses_before_docker_is_touched(tmp_path: Path, guard: str) -> None:
    options, expected = _CASES[guard]
    staged, env_file = _stage(
        tmp_path, with_compose=bool(options.get("with_compose", True)), env=options.get("env"),  # type: ignore[arg-type]
        with_env=bool(options.get("with_env", True)),
    )
    done, calls = _run(staged, env_file, *options.get("args", ()), tmp_path=tmp_path)  # type: ignore[arg-type]
    assert done.returncode == REFUSED, (done.stdout, done.stderr)
    assert expected in done.stderr, done.stderr
    assert calls == [], "a refusal that came after docker was touched is not a refusal"


@pytest.mark.parametrize("guard", sorted(_CASES))
def test_each_guard_is_shown_able_to_fail_by_deleting_it(tmp_path: Path, guard: str) -> None:
    options, expected = _CASES[guard]
    mutant = _mutant(tmp_path, guard)
    staged, env_file = _stage(
        tmp_path, script=mutant, with_compose=bool(options.get("with_compose", True)),
        env=options.get("env"), with_env=bool(options.get("with_env", True)),  # type: ignore[arg-type]
    )
    done, _ = _run(staged, env_file, *options.get("args", ()), tmp_path=tmp_path)  # type: ignore[arg-type]
    assert expected not in done.stderr, f"with the guard {guard!r} deleted the refusal is still produced:\n{done.stderr}"


def test_every_guard_in_the_script_has_a_case_here() -> None:
    names = re.findall(r"^# >>> guard: (\S+)$", SCRIPT.read_text(encoding="utf-8"), re.MULTILINE)
    assert sorted(names) == sorted(_CASES), "a guard added to apply-grants.sh needs a case in _CASES (and so a deletion proof)"
    assert len(names) == len(set(names))


def test_the_url_guard_names_each_incoherence(tmp_path: Path) -> None:
    for override, fragment in (
        ({"DATABASE_URL": f"postgresql+psycopg://other:{APP_PASSWORD}@postgres:5432/{DATABASE}"}, "DATABASE_URL's user is 'other'"),
        ({"DATABASE_URL": f"postgresql+psycopg://{APP_ROLE}:wrong@postgres:5432/{DATABASE}"}, "DATABASE_URL's password does not match ALPHA_APP_DB_PASSWORD"),
        ({"DATABASE_URL": f"postgresql+psycopg://{APP_ROLE}:{APP_PASSWORD}@postgres:5432/elsewhere"}, "DATABASE_URL's database is 'elsewhere'"),
        ({"DATABASE_URL": "not a url"}, "DATABASE_URL does not parse"),
        ({"MIGRATOR_DATABASE_URL": None}, "MIGRATOR_DATABASE_URL is unset or does not parse"),
        ({"MIGRATOR_DATABASE_URL": f"postgresql+psycopg://{APP_ROLE}:{APP_PASSWORD}@postgres:5432/{DATABASE}"}, "MIGRATOR_DATABASE_URL's user is"),
        ({"MIGRATOR_DATABASE_URL": f"postgresql+psycopg://{OWNER}:wrong@postgres:5432/{DATABASE}"}, "MIGRATOR_DATABASE_URL's password does not match POSTGRES_PASSWORD"),
    ):
        staged, env_file = _stage(tmp_path, env=_env_text(**override))
        done, calls = _run(staged, env_file, tmp_path=tmp_path)
        assert done.returncode == REFUSED and fragment in done.stderr, (override, done.stderr)
        assert calls == []


def test_a_url_in_the_old_shape_is_refused_that_is_the_state_of_every_stack_before_this_item(tmp_path: Path) -> None:
    """DATABASE_URL naming the owner role, no ALPHA_APP_DB_* at all: the stack as it stood. Refused, not defaulted."""
    old = (f"ALPHA_INSTANCE=i\nPOSTGRES_DB={DATABASE}\nPOSTGRES_USER={OWNER}\nPOSTGRES_PASSWORD={OWNER_PASSWORD}\n"
           f"DATABASE_URL=postgresql+psycopg://{OWNER}:{OWNER_PASSWORD}@postgres:5432/{DATABASE}\n")
    staged, env_file = _stage(tmp_path, env=old)
    done, calls = _run(staged, env_file, tmp_path=tmp_path)
    assert done.returncode == REFUSED and "[app_db_role_invalid]" in done.stderr and calls == []


# --- the modes ---------------------------------------------------------------------------------------------------


def test_config_only_touches_no_docker_and_exits_zero(tmp_path: Path) -> None:
    staged, env_file = _stage(tmp_path, with_compose=False)
    done, calls = _run(staged, env_file, "--config-only", tmp_path=tmp_path)
    assert done.returncode == 0 and "the settings are coherent" in done.stdout and calls == []


def test_the_env_file_may_come_from_the_environment_variable_the_other_scripts_use(tmp_path: Path) -> None:
    staged, env_file = _stage(tmp_path)
    done, calls = _run(staged, env_file, "--config-only", tmp_path=tmp_path, with_env_flag=False,
                       stub={"ALPHA_ENV_FILE": str(env_file)})
    assert done.returncode == 0, done.stderr


def test_apply_speaks_the_protocol_the_comment_promises(tmp_path: Path) -> None:
    staged, env_file = _stage(tmp_path)
    done, calls = _run(staged, env_file, tmp_path=tmp_path)
    assert done.returncode == 0, (done.stdout, done.stderr)
    assert f"grants-ok: {APP_ROLE} on {DATABASE} matches the classification" in done.stdout
    assert len(calls) == 2, "one apply, one verification"
    apply_call, check_call = calls
    expected_prefix = ["compose", "--env-file", str(env_file), "--file", str(env_file.parent.parent / "compose.server.yml"),
                       "exec", "-T", "postgres", "psql"]
    for call in (apply_call, check_call):
        argv = call["argv"]
        assert argv[: len(expected_prefix)] == expected_prefix, argv
        assert ["--username", OWNER, "--dbname", DATABASE] == argv[argv.index("--username"): argv.index("--dbname") + 2]
        assert "-v" in argv and f"app_role={APP_ROLE}" in argv
        joined = " ".join(argv)
        assert APP_PASSWORD not in joined and OWNER_PASSWORD not in joined, "a password on a command line"
    stdin = str(apply_call["stdin"])
    assert stdin.startswith(f"\\set app_password '{APP_PASSWORD}'\n"), "the password is the first thing on stdin"
    assert "CREATE ROLE" in stdin and "REVOKE ALL ON ALL TABLES IN SCHEMA public" in stdin and "COMMIT;" in stdin
    assert not re.search(r"GRANT[^;\n]*\bTRUNCATE\b", stdin), "the apply SQL grants no TRUNCATE"
    check_stdin = str(check_call["stdin"])
    assert "app_password" not in check_stdin, "the verification never sees the password"
    assert not re.search(r"\b(GRANT|REVOKE|CREATE ROLE|ALTER ROLE|DROP)\b", check_stdin), "the verification changes nothing"
    assert APP_PASSWORD not in done.stdout + done.stderr and OWNER_PASSWORD not in done.stdout + done.stderr


def test_check_sends_only_the_verification(tmp_path: Path) -> None:
    staged, env_file = _stage(tmp_path)
    done, calls = _run(staged, env_file, "--check", tmp_path=tmp_path)
    assert done.returncode == 0 and "grants-ok" in done.stdout
    assert len(calls) == 1
    assert "app_password" not in str(calls[0]["stdin"]) and not re.search(r"\b(GRANT|REVOKE|CREATE ROLE|ALTER ROLE)\b", str(calls[0]["stdin"]))


def test_a_difference_is_exit_1_for_check_and_exit_4_after_an_apply(tmp_path: Path) -> None:
    staged, env_file = _stage(tmp_path)
    stub = {"STUB_CHECK_OUT": "table audit_event: the role holds TRUNCATE\n"}
    checked, _ = _run(staged, env_file, "--check", tmp_path=tmp_path, stub=stub)
    assert checked.returncode == 1 and "[grants_drift]" in checked.stderr and "the role holds TRUNCATE" in checked.stderr
    assert "grants-ok" not in checked.stdout
    applied, calls = _run(staged, env_file, tmp_path=tmp_path, stub=stub)
    assert applied.returncode == FAILED and "found a difference" in applied.stderr
    assert "grants-ok" not in applied.stdout and len(calls) == 2


def test_an_unclassified_relation_is_a_refusal_and_not_a_failure(tmp_path: Path) -> None:
    staged, env_file = _stage(tmp_path)
    stub = {"STUB_APPLY_STATUS": "3", "STUB_APPLY_ERR":
            "ERROR:  [grants_unclassified] no grant classification for: table public.zz\nHINT:  add it\n"}
    done, calls = _run(staged, env_file, tmp_path=tmp_path, stub=stub)
    assert done.returncode == REFUSED, (done.stdout, done.stderr)
    assert "[grants_unclassified] no grant classification for: table public.zz" in done.stderr
    assert "rolled back" in done.stderr and "grants-ok" not in done.stdout
    assert len(calls) == 1, "the verification is not asked after a refusal"


def test_a_psql_failure_is_exit_4_and_never_echoes_a_password(tmp_path: Path) -> None:
    staged, env_file = _stage(tmp_path)
    stub = {"STUB_APPLY_STATUS": "3",
            "STUB_APPLY_ERR": f"ERROR:  something failed\nSTATEMENT:  ALTER ROLE x PASSWORD '{APP_PASSWORD}'\nLINE 1: password text\n"}
    done, _ = _run(staged, env_file, tmp_path=tmp_path, stub=stub)
    assert done.returncode == FAILED and "could not be applied (status 3)" in done.stderr
    assert APP_PASSWORD not in done.stdout + done.stderr, "a server message that quoted the statement must not reach the screen"
    assert "something failed" in done.stderr


def test_a_verification_that_cannot_run_is_exit_4(tmp_path: Path) -> None:
    staged, env_file = _stage(tmp_path)
    done, _ = _run(staged, env_file, "--check", tmp_path=tmp_path, stub={"STUB_CHECK_STATUS": "2", "STUB_CHECK_ERR": "psql: connection refused\n"})
    assert done.returncode == FAILED and "the verification could not be run" in done.stderr and "ps postgres" in done.stderr


def test_the_script_is_executable_and_uses_no_python() -> None:
    assert SCRIPT.stat().st_mode & 0o111, "install it with its mode"
    text = SCRIPT.read_text(encoding="utf-8")
    assert "python" not in re.sub(r"#.*", "", text), "the host is promised bash, docker, curl, sed and git"
    assert text.startswith("#!/usr/bin/env bash\n")
