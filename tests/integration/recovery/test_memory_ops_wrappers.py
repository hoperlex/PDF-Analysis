"""`D-511`: `infra/deploy/memory-setting.sh` and `memory-forget.sh`, run for real against a lane's PostgreSQL and bucket.

`tests/integration/composition/test_memory_setting_script.py` and `test_memory_forget_script.py` drive each wrapper's order, arguments and exit
codes against a scripted `docker`. `test_memory_setting.py` and `test_memory_forget.py` drive the Python halves against the database. This is where
they meet: the wrapper itself, with a `docker` shim (`docker_run_shim.py`) that runs the one-off `api` container as a sandbox holding ONLY the files
the wrapper mounted, with the container's environment (the owner's url from the compose process, `S3_*` from the env file, no `PG*`). The SQL, the
transaction, the locks, the ledger, the bucket and the files on disk are real; only the compose plumbing is translated.

What is proved here that the other two cannot: the operator's exact commands work end to end; the five mounted files really are the module's import
closure (a wrapper that forgets one fails in the sandbox the way it fails in the image); the owner's url, not the application's, is what connects;
the tool's refusals reach the operator with their own words and exit 3; a stop after the commit is finished by the command the wrapper prints;
and the files the wrapper tells the operator to keep are the ones the database holds.

What is NOT proved (the real `docker compose run`, the real `api` image with its `/app/src`, the operator's uid reading the mounts) needs the
production compose and its images; the runbook (sections 20 and 21) says so and puts the rehearsal on a restored copy before the first real use.
"""

from __future__ import annotations

import io
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
import types
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.decisions.public import register_decision_recorded, registered_decision_recorded
from scripts.recovery import memory_setting
from tests.integration.recovery.purge_seed import digest_of
from tests.integration.recovery.purge_stand import Stand, _line
from tests.integration.recovery.test_memory_forget import (  # noqa: F401  (the fixtures are used by name)
    PROJECT_A,
    Memory,
    count,
    memory,
    object_exists,
    stand,
    state_of,
)
from tests.integration.recovery.test_memory_setting import Ledger, _decision_in_flight
from tests.support.memory_seed import seed_case

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "infra/deploy"
SHIM = ROOT / "tests/integration/recovery/docker_run_shim.py"
SETTING, FORGET = "memory-setting.sh", "memory-forget.sh"
REFERENCE = "owner message 2026-11-09, wrapper stand test"
REFUSED, FAILED = 3, 4
APPLICATION_ROLE_URL = "postgresql+psycopg://the_application_role:an-application-password@127.0.0.1:1/unreachable"


class Operator:
    """The deployment directory an operator would have, wired to one cloned stand."""

    def __init__(self, stand_: Stand, tmp: Path) -> None:
        self.stand, self.tmp = stand_, tmp
        self.deploy = tmp / "deploy"
        self.deploy.mkdir()
        for name in (SETTING, FORGET):
            shutil.copy(DEPLOY / name, self.deploy / name)
        (self.deploy / "compose.server.yml").write_text("services:\n  api:\n    image: x\n  worker:\n    image: x\n", encoding="utf-8")
        values = stand_.values
        owner_url = stand_.settings.url.render_as_string(hide_password=False)
        (tmp / "alpha.env").write_text(
            f"ALPHA_INSTANCE=an-instance\nPOSTGRES_DB={stand_.database}\nPOSTGRES_USER={stand_.settings.url.username}\n"
            f"S3_BUCKET={stand_.bucket}\nS3_ENDPOINT_URL={values['S3_ENDPOINT_URL']}\nS3_REGION={values['S3_REGION']}\n"
            f"S3_ACCESS_KEY_ID={values['S3_ACCESS_KEY_ID']}\nS3_SECRET_ACCESS_KEY={values['S3_SECRET_ACCESS_KEY']}\n"
            f"DATABASE_URL={APPLICATION_ROLE_URL}\nMIGRATOR_DATABASE_URL={owner_url}\n", encoding="utf-8")
        self.bin = tmp / "bin"
        self.bin.mkdir()
        shim = self.bin / "docker"
        shim.write_text(SHIM.read_text(encoding="utf-8").replace("#!/usr/bin/env python3", f"#!{sys.executable}", 1), encoding="utf-8")
        shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
        self.log = tmp / "docker.log"
        self.dumps = tmp / "dumps"
        self.env = {
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}", "ALPHA_ENV_FILE": str(tmp / "alpha.env"),
            "ALPHA_DUMP_ROOT": str(self.dumps), "ALPHA_MEMORY_MODULE_DIR": str(ROOT / "scripts/recovery"),
            "SHIM_LOG": str(self.log), "SHIM_PYTHON": sys.executable, "SHIM_REPOSITORY": str(ROOT), "SHIM_RUNNING": "",
        }

    def run(self, script: str, *args: str, typed: str = "", **extra: str) -> subprocess.CompletedProcess[str]:
        database = ("--database", self.stand.database)
        bucket = ("--bucket", self.stand.bucket) if script == FORGET else ()
        return subprocess.run(["bash", str(self.deploy / script), *database, *bucket, *args], input=typed, capture_output=True, text=True,
                              env={**os.environ, **self.env, **extra}, timeout=600)

    def run_script(self, script: str, source: str, *args: str, typed: str = "") -> subprocess.CompletedProcess[str]:
        """The same, around a copy of the script whose text is ``source``."""
        (self.deploy / script).write_text(source, encoding="utf-8")
        return self.run(script, *args, typed=typed)

    @property
    def calls(self) -> list[str]:
        if not self.log.exists():
            return []
        return [" ".join(json.loads(line)["argv"]) for line in self.log.read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def operator(stand: Stand, tmp_path: Path) -> Operator:
    return Operator(stand, tmp_path)


@pytest.fixture
def ledger(stand: Stand) -> Any:
    before = registered_decision_recorded()
    try:
        yield Ledger(stand.engine)
    finally:
        register_decision_recorded(before)


def journal(stand_: Stand) -> list[tuple[Any, ...]]:
    with stand_.engine.connect() as connection:
        return [tuple(row) for row in connection.execute(text(
            "SELECT setting_name, revision, value, owner_permission_ref FROM decision_memory_setting_event ORDER BY setting_name, revision"))]


# --- memory-setting.sh ------------------------------------------------------------------------


def modules_own_screen(operator: Operator) -> list[str]:
    """What `memory_setting show` (the text screen of the module itself, run in this process) prints for the stand's database."""
    out = io.StringIO()
    memory_setting.show(operator.stand.engine, out)
    return out.getvalue().splitlines()


def test_show_prints_what_the_module_prints_and_connects_as_the_owner(operator: Operator) -> None:
    """`D-517`: the wrapper reads the module's `show --json` and prints the screen from it; the screen is word for word the module's own."""
    completed = operator.run(SETTING, "show")
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert completed.stdout.splitlines()[2:] == modules_own_screen(operator)
    assert "data_class: test (default; default test)" in completed.stdout and "uncaptured-decisions: 0" in completed.stdout
    assert len(operator.calls) == 1 and operator.calls[0].endswith(f"-m scripts.recovery.memory_setting --database {operator.stand.database} show --json")
    assert journal(operator.stand) == []


def test_the_screen_of_the_wrapper_is_the_modules_after_changes_too(operator: Operator) -> None:
    """Revisions, a default that is not the value, the backlog: the two screens are the same for every state the journal can be in."""
    for argv in (("set", "data_class", "real", "--actor", "admin"), ("set", "data_class", "test", "--actor", "admin"),
                 ("set", "training_use", "on", "--actor", "admin", "--owner-permission-ref", REFERENCE)):
        assert operator.run(SETTING, *argv, typed=argv[2] + "\n").returncode == 0
    completed = operator.run(SETTING, "show")
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert completed.stdout.splitlines()[2:] == modules_own_screen(operator)
    assert "data_class: test (revision 2; default test)" in completed.stdout and "training_use: on (revision 1; default off)" in completed.stdout


def test_the_lock_timeout_the_operator_sets_reaches_the_module_through_the_wrapper_and_the_pass_through_can_fail(
    operator: Operator, ledger: Ledger
) -> None:
    """`D-515`: a decision is in flight and holds the ledger. With `MEMORY_SETTING_LOCK_TIMEOUT=1s` the module gives up after one second and
    says so with that number; a copy of the wrapper that does not pass the variable waits for the module's own 15s and says 15s."""
    inflight = _decision_in_flight(types.SimpleNamespace(engine=operator.stand.engine), ledger)
    try:
        started = time.monotonic()
        completed = operator.run(SETTING, "set", "data_class", "real", "--actor", "admin", typed="real\n", MEMORY_SETTING_LOCK_TIMEOUT="1s")
        assert completed.returncode == REFUSED and "could not lock within 1s" in completed.stderr, (completed.stdout, completed.stderr)
        assert time.monotonic() - started < 14 and journal(operator.stand) == []
        source = (DEPLOY / SETTING).read_text(encoding="utf-8").replace('"${LOCK_TIMEOUT_ENV[@]+"${LOCK_TIMEOUT_ENV[@]}"}" ', "")
        completed = operator.run_script(SETTING, source, "set", "data_class", "real", "--actor", "admin", typed="real\n",
                                        MEMORY_SETTING_LOCK_TIMEOUT="1s")
        assert completed.returncode == REFUSED and "could not lock within 15s" in completed.stderr, (completed.stdout, completed.stderr)
    finally:
        inflight.rollback()
        inflight.close()
        (operator.deploy / SETTING).write_text((DEPLOY / SETTING).read_text(encoding="utf-8"), encoding="utf-8")


def test_a_set_looks_asks_writes_and_reads_it_back_against_the_real_journal(operator: Operator) -> None:
    admin = scalar(operator.stand, "SELECT user_uid FROM app_user WHERE login = 'admin'")
    completed = operator.run(SETTING, "set", "data_class", "real", "--actor", "admin", typed="real\n")
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert journal(operator.stand) == [("data_class", 1, "real", None)]
    assert scalar(operator.stand, "SELECT actor_user_uid FROM decision_memory_setting_event") == admin, "the identity, never the login"
    out = completed.stdout
    assert out.index("in force now") < out.index("retype the new value") < out.index("memory-setting: data_class: test -> real (revision 1).")
    assert "data_class: real (revision 1; default test)" in out.split("done. data_class is now real", 1)[1]
    assert len(operator.calls) == 3, "look, write, look again"

    again = operator.run(SETTING, "set", "data_class", "real", "--actor", "admin")
    assert again.returncode == 0 and "already real; nothing to do" in again.stdout and len(journal(operator.stand)) == 1


def test_training_use_on_needs_the_permission_and_records_it(operator: Operator) -> None:
    refused = operator.run(SETTING, "set", "training_use", "on", "--actor", "admin", typed="on\n")
    assert refused.returncode == REFUSED and "--owner-permission-ref is required" in refused.stderr and not operator.log.exists()
    done = operator.run(SETTING, "set", "training_use", "on", "--actor", "admin", "--owner-permission-ref", REFERENCE, typed="on\n")
    assert done.returncode == 0, (done.stdout, done.stderr)
    assert journal(operator.stand) == [("training_use", 1, "on", REFERENCE)]


def test_a_wrong_retype_writes_nothing(operator: Operator) -> None:
    completed = operator.run(SETTING, "set", "data_class", "real", "--actor", "admin", typed="yes\n")
    assert completed.returncode == REFUSED and "what was retyped is not the new value" in completed.stderr
    assert journal(operator.stand) == [] and len(operator.calls) == 1


def test_the_tools_own_refusal_of_an_unknown_actor_reaches_the_operator_with_exit_3(operator: Operator) -> None:
    completed = operator.run(SETTING, "set", "data_class", "real", "--actor", "nobody", typed="real\n")
    assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
    assert "--actor must be the login of an active" in completed.stderr and "the change was refused (reason above)" in completed.stderr
    assert journal(operator.stand) == []


def test_the_backlog_refusal_stands_through_the_wrapper_until_the_sweep_has_finished(operator: Operator, ledger: Ledger) -> None:
    """`D-496` through the operator's door: the count is on the screen before the answer is asked for, the module refuses with exit 3 and no
    override exists, and after the real sweep the same command goes through."""
    ledger.decide("accept", 2)
    ledger.decide("reject", 2)
    refused = operator.run(SETTING, "set", "data_class", "real", "--actor", "admin", typed="real\n")
    assert refused.returncode == REFUSED, (refused.stdout, refused.stderr)
    assert "uncaptured-decisions: 2" in refused.stdout, "the operator saw the number before typing"
    assert "accept/reject decision(s) of the ledger are not captured" in refused.stderr and "There is no override" in refused.stderr
    assert journal(operator.stand) == []
    assert ledger.sweep().captured == 2
    done = operator.run(SETTING, "set", "data_class", "real", "--actor", "admin", typed="real\n")
    assert done.returncode == 0, (done.stdout, done.stderr)
    assert journal(operator.stand) == [("data_class", 1, "real", None)]


def test_the_application_roles_url_is_never_what_connects(operator: Operator) -> None:
    """alpha.env carries an unreachable application url next to the owner's; every step above worked, so the owner's is what the container got."""
    assert APPLICATION_ROLE_URL in (operator.tmp / "alpha.env").read_text(encoding="utf-8")
    assert operator.run(SETTING, "show").returncode == 0
    swapped = (operator.tmp / "alpha.env").read_text(encoding="utf-8").replace(
        operator.stand.settings.url.render_as_string(hide_password=False), APPLICATION_ROLE_URL)
    (operator.tmp / "alpha.env").write_text(swapped, encoding="utf-8")
    completed = operator.run(SETTING, "show")
    assert completed.returncode == FAILED, "with the application's url in the owner's place nothing connects: the test above could not have passed"


# --- memory-forget.sh -------------------------------------------------------------------------


def scalar(stand_: Stand, statement: str, **parameters: Any) -> Any:
    with stand_.engine.connect() as connection:
        return connection.execute(text(statement), parameters).scalar_one()


A_PROJECT = ("--origin-project", PROJECT_A)


def dry_run_digest(operator: Operator) -> str:
    completed = operator.run(FORGET, *A_PROJECT)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    return _line(completed.stdout, "plan-sha256")


def apply_args(sha: str, **over: str) -> list[str]:
    options = {"--actor": "admin", "--reason": "client_request", "--owner-permission-ref": REFERENCE, "--plan-sha256": sha}
    options.update(over)
    return [*A_PROJECT, "--apply", *(item for pair in options.items() for item in pair)]


def test_the_dry_run_prints_the_plan_and_changes_nothing(operator: Operator, memory: Memory) -> None:
    before = state_of(operator.stand)
    completed = operator.run(FORGET, *A_PROJECT)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert state_of(operator.stand) == before and not operator.dumps.exists()
    assert _line(completed.stdout, "cases") == "3" and "dry run. NOTHING ABOVE WAS CHANGED" in completed.stdout
    assert "  needed: 4 (3 cases, one lock each, and one that says a forget is running)" in completed.stdout, "`D-516` through the wrapper"
    assert "server lock table: max_locks_per_transaction" in completed.stdout and "WARNING" not in completed.stdout
    assert len(operator.calls) == 1


def test_the_script_forgets_for_real_and_keeps_the_record_it_verified(operator: Operator, memory: Memory) -> None:
    stand_ = operator.stand
    sha = dry_run_digest(operator)
    operator.log.unlink()
    identity = {t: digest_of(stand_.engine, t) for t in ("decision_memory_case", "decision_memory_decision")}
    completed = operator.run(FORGET, *apply_args(sha), "--stop-services", typed=f"3\n{sha}\n", SHIM_RUNNING="postgres,api,worker,web")
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    forget_id = re.search(r"forgotten as (era_[0-9A-HJKMNP-TV-Z]{26})\.", completed.stdout).group(1)  # type: ignore[union-attr]
    # the services: listed, stopped, the write, started again -- and nothing else was stopped
    indexes = [next(i for i, c in enumerate(operator.calls) if needle in c) for needle in
               ("ps --status running --services", "stop api worker", "--apply", "up -d --no-deps api worker")]
    assert indexes == sorted(indexes) and not any(" web" in c for c in operator.calls if " stop " in c or " up " in c)
    # the content is gone and the identity side is whole
    for table in ("decision_memory_content", "decision_memory_evidence", "decision_memory_norm_ref", "decision_memory_crop"):
        assert count(stand_, table, "case_id = ANY(:c)", c=memory.a_cases) == 0, table
    assert {t: digest_of(stand_.engine, t) for t in identity} == identity
    assert count(stand_, "decision_memory_status_event", "kind = 'forget'") == 3
    assert not object_exists(stand_, memory.only_a) and object_exists(stand_, memory.shared_ab) and object_exists(stand_, memory.live)
    # the record: the files are the operator's, 0700 / 0600, and the wrapper hashed the manifest against the journal
    directory = operator.dumps / "forgets" / forget_id
    assert stat.S_IMODE((operator.dumps / "forgets").stat().st_mode) == 0o700
    manifest_sha = _line(completed.stdout, "manifest-sha256")
    assert f"manifest-sha256 {manifest_sha} (verified against the file)" in completed.stdout
    journalled = scalar(stand_, "SELECT payload->>'manifest_sha256' FROM audit_event WHERE event_type = 'memory.forget_completed'")
    assert journalled == manifest_sha and (directory / "plan.json").is_file() and (directory / "manifest.json").is_file()
    # the three queries the wrapper prints give the numbers it says they give
    assert scalar(stand_, "SELECT count(*) FROM blob WHERE state = 'erasure_pending'") == 0
    assert scalar(stand_, "SELECT count(*) FROM decision_memory_content c WHERE EXISTS (SELECT 1 FROM decision_memory_status_event e "
                          "WHERE e.case_id = c.case_id AND e.kind = 'forget')") == 0
    assert scalar(stand_, "SELECT count(*) FROM audit_event WHERE event_type = 'memory.forget_completed' AND aggregate_id = :i",
                  i=forget_id) == 1
    again = operator.run(FORGET, *A_PROJECT, typed=f"3\n{sha}\n")
    assert again.returncode == 0 and "nothing to do. Nothing was changed." in again.stdout


def test_a_stop_after_the_commit_is_finished_by_the_command_the_wrapper_prints(operator: Operator, memory: Memory) -> None:
    stand_ = operator.stand
    sha = dry_run_digest(operator)
    crash = "def boom(*a, **k):\n    raise RuntimeError('simulated crash in delete_objects')\nm.delete_objects = boom"
    completed = operator.run(FORGET, *apply_args(sha), typed=f"3\n{sha}\n", SHIM_PRELUDE=crash)
    assert completed.returncode == FAILED, (completed.stdout, completed.stderr)
    assert "THE DATABASE PART OF THE FORGET IS COMMITTED" in completed.stderr
    assert scalar(stand_, "SELECT count(*) FROM blob WHERE state = 'erasure_pending'") == 1, "the exclusive crop waits in erasure_pending"
    assert object_exists(stand_, memory.only_a)
    line = next(raw.strip() for raw in completed.stderr.splitlines() if "--resume" in raw and raw.strip().startswith(("ALPHA_DUMP_ROOT", "/")))
    tokens = shlex.split(line)
    env = dict(token.split("=", 1) for token in tokens[:1] if re.match(r"^[A-Z_]+=", token))
    resumed = subprocess.run(["bash", str(operator.deploy / FORGET), *tokens[len(env) + 1:]], capture_output=True, text=True, timeout=600,
                             env={**os.environ, **operator.env, **env})
    assert resumed.returncode == 0, (resumed.stdout, resumed.stderr)
    assert "(verified against the file)" in resumed.stdout
    assert scalar(stand_, "SELECT count(*) FROM blob WHERE state = 'erasure_pending'") == 0 and not object_exists(stand_, memory.only_a)
    assert scalar(stand_, "SELECT count(*) FROM audit_event WHERE event_type = 'memory.forget_completed'") == 1


def test_the_tools_own_refusals_reach_the_operator_with_exit_3_and_change_nothing(operator: Operator, memory: Memory) -> None:
    sha = dry_run_digest(operator)
    before = state_of(operator.stand)
    unknown_actor = operator.run(FORGET, *apply_args(sha, **{"--actor": "nobody"}), typed=f"3\n{sha}\n")
    assert unknown_actor.returncode == REFUSED and "--actor must be the login of an active" in unknown_actor.stderr, unknown_actor.stderr
    assert "Nothing was changed" in unknown_actor.stderr
    calls_before = len(operator.calls)
    other = operator.run(FORGET, "--origin-project", "prj_" + "a" * 26)
    assert other.returncode == REFUSED and "never a name" in other.stderr and len(operator.calls) == calls_before, "refused before docker"
    assert state_of(operator.stand) == before


def test_a_plan_that_changed_since_the_dry_run_is_refused_before_anything_is_asked(operator: Operator, memory: Memory) -> None:
    sha = dry_run_digest(operator)
    with operator.stand.engine.begin() as connection:  # a new case of project A: the memory the plan described is not the memory now
        seed_case(connection, project=PROJECT_A, blob=None)
    completed = operator.run(FORGET, *apply_args(sha), typed=f"3\n{sha}\n")
    assert completed.returncode == REFUSED and "not the plan you approved" in completed.stderr and "retype" not in completed.stdout
    assert count(operator.stand, "decision_memory_status_event", "kind = 'forget'") == 0


# --- the mounted list is the import closure, shown on the real modules ------------------------------


@pytest.mark.parametrize(("script", "modules", "args"), (
    (SETTING, "MODULES=(memory_setting project_erase product_purge schema_coverage blob_reference_audit)", ("show",)),
    (FORGET, "MODULES=(memory_forget project_erase product_purge schema_coverage blob_reference_audit)", A_PROJECT),
), ids=["memory-setting", "memory-forget"])
def test_a_wrapper_that_forgets_to_mount_a_file_of_the_closure_fails_where_the_container_would(
    operator: Operator, script: str, modules: str, args: tuple[str, ...]
) -> None:
    text_ = (DEPLOY / script).read_text(encoding="utf-8")
    assert operator.run(script, *args).returncode == 0, "the list as written imports cleanly in the sandbox"
    assert text_.count(modules) == 1
    for dropped in ("blob_reference_audit", "schema_coverage"):
        if dropped not in modules:
            continue
        cut = text_.replace(modules, modules.replace(f" {dropped}", ""))
        completed = operator.run_script(script, cut, *args)
        assert completed.returncode == FAILED, (dropped, completed.stdout, completed.stderr)
        assert "ModuleNotFoundError" in completed.stderr or "No module named" in completed.stderr, completed.stderr
    operator.run_script(script, text_)
