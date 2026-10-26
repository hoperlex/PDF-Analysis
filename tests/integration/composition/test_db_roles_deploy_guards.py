"""`PROD-04-DB-ROLES-01` (`R-146n` item 1, `AD-02`; `ADR-0021` section 3) -- `deploy.sh`'s five database-role guards.

*"`api` and `worker` connect as a role that cannot change the schema; the owner migrates; the rights are applied
between `migrate` and `up`."* Five guards stand for it:

* ``grants-script-present`` and ``app-db-role-configured`` refuse **before anything is built**: the first when
  ``apply-grants.sh`` is not in the clone, the second when the settings of the two roles are wrong -- above all an
  unset second password, which is ``[app_db_password_unset]`` and never a quiet use of the owner role for the
  application;
* ``owner-migrated``, ``release-notes-loaded`` and ``grants-applied`` refuse **before ``up``**: the one-shots run as
  the owner to completion, the step applies and verifies the rights, and only then is anything started or replaced.

Every case is shown able to fail the repository's way: the invocation exits 3, names the word, and (for the first two)
makes no ``docker`` call at all, or (for the last three) leaves a log with no ``up`` in it; and the same invocation
against a copy of ``deploy.sh`` with exactly that guard block deleted no longer refuses and goes on. The order is a case
too: build, then the owner's ``migrate``, then ``release-notes``, then the step (apply, verify), then ``up``.

The harness is ``test_deploy_script_refusals.py``'s, loaded from that file; the additions to its stub ``docker`` are
three branches (the one-shot services' exit statuses and a ``psql`` that answers from the environment).
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]

_spec = importlib.util.spec_from_file_location(
    "deploy_refusals_harness_roles", ROOT / "tests/integration/composition/test_deploy_script_refusals.py"
)
assert _spec is not None and _spec.loader is not None
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)

serving = harness.serving
free_port = harness.free_port
REFUSED = harness.REFUSED
DEPLOY = harness.DEPLOY
APP_ROLE = harness.APP_ROLE
APP_PASSWORD = harness.APP_PASSWORD

RUN_ANCHOR = '    if sub == "run":\n        joined = " ".join(rest)\n'
RUN_BRANCH = '''        if rest[-1:] == ["migrate"]:
            sys.exit(int(setting("STUB_OWNER_MIGRATE_STATUS", "0")))
        if rest[-1:] == ["release-notes"]:
            sys.exit(int(setting("STUB_NOTES_STATUS", "0")))
'''
EXEC_ANCHOR = '    if sub == "ps":'
EXEC_BRANCH = '''    if sub == "exec" and "psql" in rest:
        # `apply-grants.sh`: the first call carries the password on stdin (apply), the second does not (verify).
        stdin = open(0).read() if not sys.stdin.isatty() else ""
        applying = "app_password" in stdin
        with open(setting("STUB_LOG") + ".psql", "a", encoding="utf-8") as handle:
            handle.write(("apply" if applying else "verify") + "\\n")
        sys.stdout.write(setting("STUB_VERIFY_OUT", "") if not applying else "")
        sys.stderr.write(setting("STUB_PSQL_ERR", "") if applying else "")
        sys.exit(int(setting("STUB_PSQL_STATUS", "0")) if applying else 0)
'''


@pytest.fixture(autouse=True)
def _docker_that_answers_the_roles_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = harness.DOCKER_STUB
    assert stub.count(RUN_ANCHOR) == 1 and stub.count(EXEC_ANCHOR) == 1, "the harness's docker stub changed shape"
    stub = stub.replace(RUN_ANCHOR, RUN_ANCHOR + RUN_BRANCH, 1).replace(EXEC_ANCHOR, EXEC_BRANCH + EXEC_ANCHOR, 1)
    monkeypatch.setattr(harness, "DOCKER_STUB", stub)


def _calls(log: Path) -> list[str]:
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def _sub(line: str) -> str:
    fields = line.split()
    return fields[5] if len(fields) > 5 else ""


def _ready(tmp_path: Path, port: int, *, env: str | None = None, script: Path | None = None, **staging: object) -> tuple[Path, Path]:
    env_file = tmp_path / "alpha.env"
    env_file.write_text(env if env is not None else harness._env_text(harness.EDITED_SECRETS, port=port), encoding="utf-8")
    return harness._stage(tmp_path / "ready", script=script, **staging), env_file  # type: ignore[arg-type]


def _env_without(port: int, *names: str, **replace: str) -> str:
    kept = []
    for line in harness._env_text(harness.EDITED_SECRETS, port=port).splitlines():
        name = line.split("=", 1)[0]
        if name in replace:
            kept.append(f"{name}={replace[name]}")
        elif name not in names:
            kept.append(line)
    return "\n".join(kept) + "\n"


# --- before anything is built --------------------------------------------------------------------------------


class TestTheSettingsAreRefusedBeforeAnythingIsBuilt:
    def test_a_clone_without_the_grants_script_is_a_sentence_and_not_a_missing_file(self, tmp_path: Path, free_port: int) -> None:
        script, env_file = _ready(tmp_path, free_port, with_grants=False)
        completed, log = harness._run(script, tmp_path=tmp_path, env_file=env_file)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "[grants_script_missing]" in completed.stderr, completed.stderr
        assert not log.exists(), "the refusal came after docker was touched"

    def test_a_grants_script_that_is_not_executable_is_refused_the_same_way(self, tmp_path: Path, free_port: int) -> None:
        script, env_file = _ready(tmp_path, free_port)
        (script.parent / "apply-grants.sh").chmod(0o644)
        completed, log = harness._run(script, tmp_path=tmp_path, env_file=env_file)
        assert completed.returncode == REFUSED and "[grants_script_missing]" in completed.stderr, completed.stderr
        assert not log.exists()

    def test_that_guard_is_shown_able_to_fail(self, tmp_path: Path, free_port: int) -> None:
        cut = harness._mutant(tmp_path, "grants-script-present")
        script, env_file = _ready(tmp_path, free_port, script=cut, with_grants=False)
        completed, log = harness._run(script, tmp_path=tmp_path, env_file=env_file)
        assert "[grants_script_missing]" not in completed.stderr, completed.stderr


@pytest.mark.parametrize(
    ("label", "env", "word"),
    [
        ("the second password is unset", lambda port: _env_without(port, "ALPHA_APP_DB_PASSWORD"), "[app_db_password_unset]"),
        ("the second password is empty", lambda port: _env_without(port, "ALPHA_APP_DB_PASSWORD", ALPHA_APP_DB_PASSWORD=""), "[app_db_password_unset]"),
        ("the role is not named", lambda port: _env_without(port, "ALPHA_APP_DB_USER"), "[app_db_role_invalid]"),
        ("the application role IS the owner", lambda port: _env_without(port, "ALPHA_APP_DB_USER", ALPHA_APP_DB_USER=harness.PG_USER), "[app_db_role_is_owner]"),
        ("the second password is the owner's", lambda port: _env_without(
            port, "ALPHA_APP_DB_PASSWORD", ALPHA_APP_DB_PASSWORD=harness.EDITED_SECRETS["POSTGRES_PASSWORD"]), "[app_db_password_is_owner_password]"),
        ("the second password is too weak", lambda port: _env_without(port, "ALPHA_APP_DB_PASSWORD", ALPHA_APP_DB_PASSWORD="short"), "[app_db_password_shape]"),
        ("DATABASE_URL still names the owner (every stack before this item)", lambda port: _env_without(
            port, "DATABASE_URL", DATABASE_URL=f"postgresql+psycopg://{harness.PG_USER}:{harness.EDITED_SECRETS['POSTGRES_PASSWORD']}@postgres:5432/{harness.DATABASE}"),
         "[database_urls_incoherent]"),
    ],
)
class TestEachWayTheTwoRolesCanBeMisconfigured:
    """Each case is an environment that is otherwise whole: the other guards pass, so the refusal is this one's."""

    def test_it_is_refused_with_its_word_before_docker_is_touched(
        self, label: str, env: object, word: str, tmp_path: Path, free_port: int
    ) -> None:
        script, env_file = _ready(tmp_path, free_port, env=env(free_port))  # type: ignore[operator]
        completed, log = harness._run(script, tmp_path=tmp_path, env_file=env_file)
        assert completed.returncode == REFUSED, (label, completed.stdout, completed.stderr)
        assert "the database roles are not configured" in completed.stderr, completed.stderr
        assert word in completed.stderr, (label, completed.stderr)
        assert not log.exists(), f"{label}: the refusal came after docker was touched"

    def test_with_the_guard_deleted_the_deploy_goes_on_to_build(
        self, label: str, env: object, word: str, tmp_path: Path, free_port: int
    ) -> None:
        """The mutation proof: without ``app-db-role-configured`` the same environment is built before anything
        says a word -- which is exactly what the guard exists to prevent."""
        cut = harness._mutant(tmp_path, "app-db-role-configured")
        script, env_file = _ready(tmp_path, free_port, env=env(free_port), script=cut)  # type: ignore[operator]
        completed, log = harness._run(script, tmp_path=tmp_path, env_file=env_file)
        assert "the database roles are not configured" not in completed.stderr, completed.stderr
        assert "build" in [_sub(line) for line in _calls(log)], (
            f"{label}: the mutant never reached the build, so this case was not testing that guard"
        )


def test_a_missing_owner_url_is_refused_by_the_derived_secrets_guard_before_this_one(tmp_path: Path, free_port: int) -> None:
    """``MIGRATOR_DATABASE_URL`` carries the owner's secrets, which is ``derived-secrets-coherent``'s question."""
    script, env_file = _ready(tmp_path, free_port, env=_env_without(free_port, "MIGRATOR_DATABASE_URL"))
    completed, log = harness._run(script, tmp_path=tmp_path, env_file=env_file)
    assert completed.returncode == REFUSED and "MIGRATOR_DATABASE_URL is unset or does not parse" in completed.stderr
    assert not log.exists()


def test_the_owner_role_is_never_used_for_the_application_when_the_password_is_unset(tmp_path: Path, free_port: int) -> None:
    """No fall-back: with the second password missing, nothing is built, nothing is migrated and the owner's url is
    never handed to a service as the application's."""
    script, env_file = _ready(tmp_path, free_port, env=_env_without(free_port, "ALPHA_APP_DB_PASSWORD"))
    completed, log = harness._run(script, tmp_path=tmp_path, env_file=env_file)
    assert completed.returncode == REFUSED and "[app_db_password_unset]" in completed.stderr
    assert not log.exists()
    assert not Path(str(log) + ".psql").exists(), "the step never ran"


# --- before `up` -----------------------------------------------------------------------------------------------------


def _ups(log: Path) -> list[str]:
    return [line for line in _calls(log) if _sub(line) == "up"]


class TestTheOneShotsAndTheStepRunBeforeUp:
    def test_the_order_is_build_then_owner_migrate_then_notes_then_apply_then_verify_then_up(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        script, env_file = _ready(tmp_path, serving[0])
        completed, log = harness._run(script, tmp_path=tmp_path, env_file=env_file)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        lines = _calls(log)
        first = {sub: next((i for i, line in enumerate(lines) if _sub(line) == sub), None)
                 for sub in ("build", "run", "exec", "up")}
        migrate = next(i for i, line in enumerate(lines) if _sub(line) == "run" and line.split()[-1] == "migrate")
        notes = next(i for i, line in enumerate(lines) if _sub(line) == "run" and line.split()[-1] == "release-notes")
        execs = [i for i, line in enumerate(lines) if _sub(line) == "exec"]
        up = first["up"]
        assert first["build"] is not None and up is not None
        assert first["build"] < migrate < notes < execs[0] < execs[1] < up, lines
        assert len(execs) == 2, "one apply, one verification"
        assert Path(str(log) + ".psql").read_text(encoding="utf-8").split() == ["apply", "verify"]
        assert "giving the application role its rights" in completed.stdout
        assert f"grants-ok: {APP_ROLE} on {harness.DATABASE}" in completed.stdout

    def test_the_migrate_the_deploy_runs_is_a_one_off_container_and_not_a_second_up(
        self, tmp_path: Path, free_port: int
    ) -> None:
        script, env_file = _ready(tmp_path, free_port)
        _, log = harness._run(script, tmp_path=tmp_path, env_file=env_file)
        runs = [line for line in _calls(log) if _sub(line) == "run" and line.split()[-1] in ("migrate", "release-notes")]
        assert len(runs) == 2 and all(" --rm " in f" {line} " for line in runs), runs
        assert len(_ups(log)) == 1, "the only `up` is the one that starts the stack"

    def test_no_password_is_on_any_docker_command_line(self, tmp_path: Path, free_port: int) -> None:
        script, env_file = _ready(tmp_path, free_port)
        completed, log = harness._run(script, tmp_path=tmp_path, env_file=env_file)
        text = log.read_text(encoding="utf-8")
        assert APP_PASSWORD not in text and harness.EDITED_SECRETS["POSTGRES_PASSWORD"] not in text
        assert APP_PASSWORD not in completed.stdout + completed.stderr

    def test_the_apply_call_names_the_application_role_and_the_owner(self, tmp_path: Path, free_port: int) -> None:
        script, env_file = _ready(tmp_path, free_port)
        _, log = harness._run(script, tmp_path=tmp_path, env_file=env_file)
        execs = [line for line in _calls(log) if _sub(line) == "exec"]
        assert all(f"app_role={APP_ROLE}" in line and f"--username {harness.PG_USER}" in line
                   and f"--dbname {harness.DATABASE}" in line for line in execs), execs


class TestAFailureBeforeUpStartsNothing:
    def test_a_failed_owner_migrate_is_a_refusal_and_nothing_is_started(self, tmp_path: Path, free_port: int) -> None:
        script, env_file = _ready(tmp_path, free_port)
        completed, log = harness._run(script, tmp_path=tmp_path, env_file=env_file, stub={"STUB_OWNER_MIGRATE_STATUS": "1"})
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "[migrate_failed]" in completed.stderr and "exited 1" in completed.stderr
        assert _ups(log) == [] and not Path(str(log) + ".psql").exists(), "no rights were applied after a failed migrate"
        assert "build" in [_sub(line) for line in _calls(log)], "it refused after the build, before up"

    def test_a_failed_release_notes_load_is_a_refusal_and_nothing_is_started(self, tmp_path: Path, free_port: int) -> None:
        script, env_file = _ready(tmp_path, free_port)
        completed, log = harness._run(script, tmp_path=tmp_path, env_file=env_file, stub={"STUB_NOTES_STATUS": "2"})
        assert completed.returncode == REFUSED and "[release_notes_failed]" in completed.stderr, completed.stderr
        assert _ups(log) == [] and not Path(str(log) + ".psql").exists()

    def test_a_step_that_failed_is_a_refusal_and_nothing_is_started(self, tmp_path: Path, free_port: int) -> None:
        script, env_file = _ready(tmp_path, free_port)
        completed, log = harness._run(
            script, tmp_path=tmp_path, env_file=env_file,
            stub={"STUB_PSQL_STATUS": "3", "STUB_PSQL_ERR": "ERROR:  [grants_unclassified] no grant classification for: table public.zz\n"},
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "[grants_not_applied]" in completed.stderr and "exited 3" in completed.stderr
        assert "[grants_unclassified] no grant classification for: table public.zz" in completed.stderr, "the step's own reason is shown"
        assert _ups(log) == [], "api and worker were neither started nor replaced"

    def test_a_verification_that_found_a_difference_is_a_refusal_and_nothing_is_started(self, tmp_path: Path, free_port: int) -> None:
        script, env_file = _ready(tmp_path, free_port)
        completed, log = harness._run(script, tmp_path=tmp_path, env_file=env_file,
                                      stub={"STUB_VERIFY_OUT": "table audit_event: the role holds TRUNCATE\n"})
        assert completed.returncode == REFUSED and "[grants_not_applied]" in completed.stderr and "exited 4" in completed.stderr
        assert _ups(log) == []


@pytest.mark.parametrize(
    ("guard", "stub", "word"),
    [
        ("owner-migrated", {"STUB_OWNER_MIGRATE_STATUS": "1"}, "[migrate_failed]"),
        ("release-notes-loaded", {"STUB_NOTES_STATUS": "2"}, "[release_notes_failed]"),
        ("grants-applied", {"STUB_PSQL_STATUS": "3"}, "[grants_not_applied]"),
    ],
)
def test_each_pre_up_guard_is_shown_able_to_fail_by_deleting_it(
    guard: str, stub: dict[str, str], word: str, tmp_path: Path, free_port: int
) -> None:
    """Delete the block and the same failure is followed by the `up` that replaces the running containers."""
    cut = harness._mutant(tmp_path, guard)
    script, env_file = _ready(tmp_path, free_port, script=cut)
    completed, log = harness._run(script, tmp_path=tmp_path, env_file=env_file, stub=stub)
    assert word not in completed.stderr, completed.stderr
    assert _ups(log) != [], f"the mutant did not reach `up`, so this case was not testing {guard}"


def test_the_five_guards_are_the_ones_the_script_marks() -> None:
    markers = re.findall(r"^# >>> guard: ([a-z-]+)$", DEPLOY.read_text(encoding="utf-8"), re.M)
    for guard in harness.DB_ROLE_GUARDS:
        assert guard in markers, guard


# --- the compose file hands each URL to the right services only -------------------------------------------------


def _url_wiring(compose_text: str) -> dict[str, dict[str, str]]:
    """service -> {environment name: the value as written}, for the two database variables only."""
    wiring: dict[str, dict[str, str]] = {}
    service: str | None = None
    in_services = False
    for line in compose_text.splitlines():
        if re.match(r"^services:\s*$", line):
            in_services = True
            continue
        if in_services and re.match(r"^\S", line):
            in_services = False
        match = re.match(r"^  ([a-z0-9-]+):\s*$", line) if in_services else None
        if match:
            service = match.group(1)
            continue
        found = re.match(r"^      DATABASE_URL: (.*)$", line)
        if found and service:
            wiring.setdefault(service, {})["DATABASE_URL"] = found.group(1).strip()
    return wiring


def test_the_application_gets_its_url_and_only_the_one_shots_get_the_owners() -> None:
    wiring = _url_wiring((ROOT / "infra/deploy/compose.server.yml").read_text(encoding="utf-8"))
    application = {name for name, env in wiring.items() if env["DATABASE_URL"].startswith("${DATABASE_URL:?")}
    owner = {name for name, env in wiring.items() if env["DATABASE_URL"].startswith("${MIGRATOR_DATABASE_URL:?")}
    assert application == {"api", "worker"}, wiring
    assert owner == {"migrate", "release-notes"}, wiring
    assert set(wiring) == application | owner, "a service reads some other database url"
    assert "MIGRATOR_DATABASE_URL" not in "".join(
        line for line in (ROOT / "infra/deploy/compose.server.yml").read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#") and "      DATABASE_URL: ${MIGRATOR_DATABASE_URL" not in line
    ), "the owner's url is named somewhere other than the two one-shots' DATABASE_URL"


@pytest.mark.parametrize(("old", "new"), [
    ("      DATABASE_URL: ${DATABASE_URL:?DATABASE_URL is unset. It is the application role's",
     "      DATABASE_URL: ${MIGRATOR_DATABASE_URL:?DATABASE_URL is unset. It is the application role's"),
    ("      DATABASE_URL: ${MIGRATOR_DATABASE_URL:?MIGRATOR_DATABASE_URL is unset. It is the owner role's url (POSTGRES_USER); see infra/deploy/env/alpha.env.example.}\n    working_dir: /app\n    command: [\"alembic\"",
     "      DATABASE_URL: ${DATABASE_URL:?x}\n    working_dir: /app\n    command: [\"alembic\""),
])
def test_the_wiring_check_is_shown_able_to_fail(old: str, new: str) -> None:
    text = (ROOT / "infra/deploy/compose.server.yml").read_text(encoding="utf-8")
    assert old in text, "the line the mutation edits moved"
    wiring = _url_wiring(text.replace(old, new, 1))
    application = {name for name, env in wiring.items() if env["DATABASE_URL"].startswith("${DATABASE_URL:?")}
    owner = {name for name, env in wiring.items() if env["DATABASE_URL"].startswith("${MIGRATOR_DATABASE_URL:?")}
    assert (application, owner) != ({"api", "worker"}, {"migrate", "release-notes"})


def test_every_variable_the_compose_file_requires_is_in_the_example() -> None:
    """`docker compose config` fails on an unset `${NAME:?...}`; this is the static half of that, so a new required name
    that the example does not carry is found without a daemon. (`PROD-04` added `MIGRATOR_DATABASE_URL`.)"""
    compose = (ROOT / "infra/deploy/compose.server.yml").read_text(encoding="utf-8")
    example = (ROOT / "infra/deploy/env/alpha.env.example").read_text(encoding="utf-8")
    required = set(re.findall(r"\$\{([A-Z0-9_]+):\?", compose))
    defined = {m.group(1) for m in re.finditer(r"^([A-Z0-9_]+)=", example, re.M)}
    assert required <= defined, sorted(required - defined)
    assert {"DATABASE_URL", "MIGRATOR_DATABASE_URL"} <= required


def test_the_example_carries_no_password_for_the_application_role() -> None:
    """`R-146n`: the second password is the owner's, written on the host. The repository holds none -- not as a value, not
    as a default -- and `deploy.sh` refuses it unset."""
    example = (ROOT / "infra/deploy/env/alpha.env.example").read_text(encoding="utf-8")
    assert re.search(r"^ALPHA_APP_DB_PASSWORD=$", example, re.M), "the example must ship the name with no value"
    url = next(line for line in example.splitlines() if line.startswith("DATABASE_URL="))
    assert "replace-with-ALPHA_APP_DB_PASSWORD" in url, url
    assert "change-me" not in url, "the application url must not borrow the owner's disposable password"
