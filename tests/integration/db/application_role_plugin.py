"""A pytest plugin: run a suite that builds its own databases AS the application role.

`PROD-04-DB-ROLES-01` asks that "the integration directories of the contexts pass as the application role".
Many suites create a private database with the owner's rights (`CREATE DATABASE`, then `alembic upgrade head`) and then
hand the SAME url to the code under test, so pointing `DATABASE_URL` at the application role would stop them at
`CREATE DATABASE`. This plugin keeps the two apart without changing a line of any suite:

* nothing happens unless `AM_TEST_AS_APPLICATION_ROLE=1` is in the environment (the default run is untouched), and
  `DATABASE_URL` must then name the OWNER (the lane's role, which may create databases);
* the database layer's one engine factory (`auditmanager.shared.db.engine.create_engine`, "the only place in the
  codebase that calls create_engine") is wrapped: an engine for any database other than `postgres`, a template, or the
  database `DATABASE_URL` itself names is built with the application role's name and password instead of the owner's.
  Everything that creates and migrates databases (the maintenance engine, the `alembic` subprocess) stays the owner's;
* before an engine is handed out for such a database that has been migrated (`alembic_version` exists), the database is
  given its rights by the SAME SQL `apply-grants.sh` embeds (`scripts.recovery.grant_classification.render_sql("apply")`,
  run with `psql`), once per database;
* the role is created for the session under a unique name and dropped when the session ends (after the fixtures have
  dropped their databases), and the terminal summary says how many engines ran as which role -- so a green run states
  what it was green AS, and a suite that built an engine around the factory would show up as engines that never were the
  application's.

    AM_TEST_AS_APPLICATION_ROLE=1 python -m pytest -p tests.integration.db.application_role_plugin \\
        tests/integration/access

A test that needs the owner (to seed with an UPDATE on an append-only table, to TRUNCATE, to disable a trigger, to run DDL)
fails here with `permission denied`; the right answer is to list it, never to loosen the role.
"""

from __future__ import annotations

import os
import secrets
import subprocess
from typing import Any

import pytest
from sqlalchemy.engine import URL, make_url

ENABLED = os.environ.get("AM_TEST_AS_APPLICATION_ROLE") == "1"
MAINTENANCE_DATABASES = frozenset(("postgres", "template0", "template1"))

_state: dict[str, Any] = {
    "role": "", "password": "", "as_application": 0, "as_owner": 0, "granted": set(), "owner": None, "lane": "",
}


def _psql(owner: URL, database: str, script: str, *variables: str) -> subprocess.CompletedProcess[str]:
    arguments = ["psql", "-h", str(owner.host), "-p", str(owner.port), "-U", str(owner.username), "-d", database, "-X", "-q",
                 "-At", "-v", "ON_ERROR_STOP=1", *variables]
    return subprocess.run(arguments, input=script, capture_output=True, text=True,
                          env=dict(os.environ, PGPASSWORD=str(owner.password)), timeout=120, check=False)


def _grant(owner: URL, database: str) -> None:
    """Apply the classification to one migrated database, as the owner, with the SQL the shipped script embeds."""
    from scripts.recovery import grant_classification as grants

    if database in _state["granted"]:
        return
    probe = _psql(owner, database, "SELECT to_regclass('public.alembic_version') IS NOT NULL;")
    if probe.returncode != 0 or probe.stdout.strip() != "t":
        return  # not migrated yet: the suite is still building it, and will ask again
    script = f"\\set app_password '{_state['password']}'\n{grants.render_sql('apply')}"
    done = _psql(owner, database, script, "-v", f"app_role={_state['role']}")
    if done.returncode != 0:
        raise RuntimeError(f"the grants could not be applied to {database}: {done.stderr.strip()[:400]}")
    _state["granted"].add(database)


def pytest_configure(config: pytest.Config) -> None:
    if not ENABLED:
        return
    import auditmanager.shared.db.engine as engine_module

    raw = os.environ.get("DATABASE_URL")
    if not raw:
        raise pytest.UsageError("AM_TEST_AS_APPLICATION_ROLE=1 needs DATABASE_URL (the owner's) in the environment")
    owner = make_url(raw)
    _state.update(role=f"prod04_plug_{secrets.token_hex(4)}", password=secrets.token_hex(16), owner=owner,
                  lane=str(owner.database))
    created = _psql(owner, "postgres",
                    f"CREATE ROLE \"{_state['role']}\" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '{_state['password']}';")
    if created.returncode != 0:
        raise pytest.UsageError(f"the application role could not be created: {created.stderr.strip()[:300]}")
    original = engine_module.create_engine

    def create_engine(url: Any, *args: Any, **kwargs: Any) -> Any:
        parsed = make_url(url)
        database = str(parsed.database)
        if database in MAINTENANCE_DATABASES or database == _state["lane"]:
            _state["as_owner"] += 1
            return original(parsed, *args, **kwargs)
        _grant(parsed.set(username=owner.username, password=owner.password), database)
        _state["as_application"] += 1
        return original(parsed.set(username=_state["role"], password=_state["password"]), *args, **kwargs)

    config._am_original_create_engine = original  # type: ignore[attr-defined]
    engine_module.create_engine = create_engine  # type: ignore[assignment]


def pytest_unconfigure(config: pytest.Config) -> None:
    if not ENABLED or not _state["role"]:
        return
    import auditmanager.shared.db.engine as engine_module

    engine_module.create_engine = config._am_original_create_engine  # type: ignore[attr-defined]
    # A role cannot be dropped while it holds a privilege anywhere: take them out of every database that was granted and
    # still exists (a suite normally dropped its databases already, and `DROP OWNED` is then simply not reached).
    for database in sorted(_state["granted"]):
        _psql(_state["owner"], database, f'DROP OWNED BY "{_state["role"]}";')
    _psql(_state["owner"], "postgres", f'DROP ROLE IF EXISTS "{_state["role"]}";')


def pytest_terminal_summary(terminalreporter: Any) -> None:
    if not ENABLED:
        return
    terminalreporter.write_sep("-", "application role")
    terminalreporter.write_line(
        f"engines built as the application role {_state['role']}: {_state['as_application']} "
        f"(databases granted: {len(_state['granted'])}); engines built as the owner: {_state['as_owner']}"
    )
