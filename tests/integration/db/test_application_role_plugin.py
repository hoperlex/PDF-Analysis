"""PROD-04-DB-ROLES-01: the plugin that runs a suite AS the application role does what it says it does.

``application_role_plugin.py`` is the instrument behind the claim "the integration directories pass as the application
role" -- so it is itself held to a test. A tiny suite is run in a SUBPROCESS with the plugin on:

* the engine for a migrated clone is the application role's (``current_user`` is the plugin's session role, the role cannot
  create a table, and it has the rights the classification gives it);
* the engine for the maintenance database stays the owner's;
* the terminal summary says how many engines were which;
* the session role is gone from the cluster afterwards;
* without ``AM_TEST_AS_APPLICATION_ROLE=1`` the plugin changes nothing (the engine is the owner's even for a clone).

The mutation proof is the last case: a suite that builds its engine AROUND the factory (a bare ``sqlalchemy.create_engine``)
is the owner's, and the summary does not count it -- which is exactly how a hollow green would show.
"""

from __future__ import annotations

import os
import re
import subprocess
import textwrap
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.engine import make_url

from auditmanager.shared.db.config import DatabaseSettings

ROOT = Path(__file__).resolve().parents[3]

SUITE = '''
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.db.engine import create_database_engine

CLONE = os.environ["PLUGIN_TEST_DATABASE"]
OWNER_URL = make_url(os.environ["DATABASE_URL"])


def _user(engine):
    with engine.connect() as connection:
        return connection.execute(text("SELECT current_user")).scalar_one()


def test_a_clone_gets_the_application_role():
    engine = create_database_engine(DatabaseSettings(url=OWNER_URL.set(database=CLONE)))
    assert _user(engine).startswith("prod04_plug_"), _user(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM project")).scalar_one() == 0
    engine.dispose()


def test_the_application_role_cannot_change_the_schema_or_truncate():
    engine = create_database_engine(DatabaseSettings(url=OWNER_URL.set(database=CLONE)))
    for statement in ("CREATE TABLE zz_plugin (a int)", "TRUNCATE TABLE project", "ALTER TABLE project ADD COLUMN zz int"):
        with engine.connect() as connection:
            try:
                connection.execute(text(statement))
            except Exception as refused:
                assert "permission denied" in str(refused) or "must be owner" in str(refused), refused
            else:
                raise AssertionError(statement + " was allowed")
    engine.dispose()


def test_the_maintenance_database_stays_the_owners():
    engine = create_database_engine(DatabaseSettings(url=OWNER_URL.set(database="postgres")))
    assert _user(engine) == OWNER_URL.username
    engine.dispose()


def test_an_engine_built_around_the_factory_is_the_owners_and_is_not_counted():
    engine = create_engine(OWNER_URL.set(database=CLONE))
    assert _user(engine) == OWNER_URL.username
    engine.dispose()
'''


def _run(tmp_path: Path, owner_url: str, clone: str, *, plugin: bool) -> subprocess.CompletedProcess[str]:
    suite = tmp_path / "test_plugin_suite.py"
    suite.write_text(textwrap.dedent(SUITE), encoding="utf-8")
    environment = dict(os.environ)
    environment.update(DATABASE_URL=owner_url, PLUGIN_TEST_DATABASE=clone, PYTHONPATH="src")
    if plugin:
        environment["AM_TEST_AS_APPLICATION_ROLE"] = "1"
    else:
        environment.pop("AM_TEST_AS_APPLICATION_ROLE", None)
    command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-c", "pyproject.toml", "--rootdir", str(ROOT), "-q",
               "-p", "no:cacheprovider", "--tb=short", "-p", "tests.integration.db.application_role_plugin", str(suite)]
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, env=environment, timeout=300, check=False)


def _roles_like_the_plugin(owner_url: str) -> list[str]:
    done = subprocess.run(
        ["psql", "-h", str(make_url(owner_url).host), "-p", str(make_url(owner_url).port), "-U", str(make_url(owner_url).username),
         "-d", "postgres", "-X", "-q", "-At", "-c", "SELECT rolname FROM pg_roles WHERE rolname LIKE 'prod04\\_plug\\_%'"],
        capture_output=True, text=True, env=dict(os.environ, PGPASSWORD=str(make_url(owner_url).password)), check=True,
    )
    return done.stdout.split()


def test_with_the_plugin_on_a_clone_is_the_application_role_and_the_role_is_gone_afterwards(
    tmp_path: Path, configured_settings: DatabaseSettings, migrated_database_factory: Callable[[], DatabaseSettings],
) -> None:
    clone = str(migrated_database_factory().url.database)
    owner_url = configured_settings.url.render_as_string(hide_password=False)
    before = _roles_like_the_plugin(owner_url)
    done = _run(tmp_path, owner_url, clone, plugin=True)
    # The fourth case builds an engine around the factory: it is the owner's, and the three others are not affected.
    assert done.returncode == 0, (done.stdout, done.stderr)
    assert "4 passed" in done.stdout
    summary = re.search(r"engines built as the application role (prod04_plug_[0-9a-f]+): (\d+) \(databases granted: (\d+)\); "
                        r"engines built as the owner: (\d+)", done.stdout)
    assert summary is not None, done.stdout
    assert (int(summary.group(2)), int(summary.group(3)), int(summary.group(4))) == (2, 1, 1), summary.group(0)
    assert _roles_like_the_plugin(owner_url) == before, "the session role was left in the cluster"


def test_without_the_opt_in_the_plugin_changes_nothing(
    tmp_path: Path, configured_settings: DatabaseSettings, migrated_database_factory: Callable[[], DatabaseSettings],
) -> None:
    clone = str(migrated_database_factory().url.database)
    owner_url = configured_settings.url.render_as_string(hide_password=False)
    done = _run(tmp_path, owner_url, clone, plugin=False)
    # Without the plugin the clone engine is the owner's, so the application-role assertions of the suite must FAIL: the
    # instrument is shown to be what turns the role on.
    assert done.returncode == 1, (done.stdout, done.stderr)
    assert re.search(r"\b[12] failed\b", done.stdout), done.stdout
    assert "engines built as the application role" not in done.stdout


def test_the_plugin_refuses_to_start_without_the_owners_url(tmp_path: Path) -> None:
    suite = tmp_path / "test_nothing.py"
    suite.write_text("def test_nothing():\n    pass\n", encoding="utf-8")
    environment = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    environment.update(AM_TEST_AS_APPLICATION_ROLE="1", PYTHONPATH="src")
    done = subprocess.run(
        [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-c", "pyproject.toml", "--rootdir", str(ROOT), "-q", "-p", "no:cacheprovider",
         "-p", "tests.integration.db.application_role_plugin", str(suite)],
        cwd=ROOT, capture_output=True, text=True, env=environment, timeout=120, check=False,
    )
    assert done.returncode != 0 and "needs DATABASE_URL" in done.stderr + done.stdout, (done.stdout, done.stderr)
