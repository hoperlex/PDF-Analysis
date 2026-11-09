"""`DECISION-MEMORY-01` phase M2: the operator tool ``scripts/recovery/memory_setting.py`` shows and journals the installation settings.

On a clone of the migrated schema, as the owner. Shown: nothing journalled reads as the defaults (``test``, ``off``); a change journals one
row with the next revision, the admin's ``usr_`` identity (never the login) and the owner's permission when given; the same value again records
nothing; ``training_use = on`` is refused without the owner's permission before the database is touched (and the table's CHECK would refuse it
too); an expert's login, an unknown name or value and a mistyped database are refused; and every guard is shown able to fail on a copy of the
source with the block deleted. The capture reading the journal is ``test_decision_memory_status``.
"""

from __future__ import annotations

import contextlib
import io
import re
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.shared.db.engine import create_database_engine
from scripts.recovery import memory_setting as tool

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "scripts/recovery/memory_setting.py"
REF = "owner message 2026-11-09, settings test"


@pytest.fixture
def clone(migrated_database_factory: Any, monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    settings = migrated_database_factory()
    monkeypatch.setenv("DATABASE_URL", settings.url.render_as_string(hide_password=False))
    engine = create_database_engine(settings)
    try:
        yield types.SimpleNamespace(engine=engine, database=str(settings.url.database))
    finally:
        engine.dispose()


def run(module: types.ModuleType, clone: Any, *argv: str, database: str | None = None) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err):
        code = module.run(["--database", database or clone.database, *argv], out=out)
    return code, out.getvalue(), err.getvalue()


def journal(clone: Any) -> list[tuple[Any, ...]]:
    with clone.engine.connect() as connection:
        return [tuple(row) for row in connection.execute(text(
            "SELECT setting_name, revision, value, actor_user_uid, owner_permission_ref FROM decision_memory_setting_event "
            "ORDER BY setting_name, revision"))]


_BLOCK = r"^[ \t]*# >>> guard: {name}\n.*?^[ \t]*# <<< guard: {name}\n"
_MUTANTS = iter(range(10**6))


def mutant(*guards: str) -> types.ModuleType:
    source = SOURCE.read_text(encoding="utf-8")
    for name in guards:
        source, matched = re.subn(_BLOCK.format(name=re.escape(name)), "", source, flags=re.DOTALL | re.MULTILINE)
        assert matched == 1, f"the guard markers for {name!r} are not a single block"
    module = types.ModuleType(f"scripts.recovery.memory_setting_mutant_{next(_MUTANTS)}")
    module.__file__ = str(SOURCE)
    sys.modules[module.__name__] = module
    exec(compile(source, f"<memory_setting without {guards}>", "exec"), module.__dict__)  # noqa: S102
    return module


def test_nothing_journalled_reads_as_the_safe_defaults(clone: Any) -> None:
    code, out, err = run(tool, clone, "show")
    assert code == 0 and err == "", (out, err)
    assert "data_class: test (default; default test)" in out and "training_use: off (default; default off)" in out
    assert journal(clone) == []


def test_a_change_is_journalled_once_with_the_admins_identity_and_the_same_value_again_records_nothing(clone: Any) -> None:
    admin = str(clone.engine.connect().execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())
    code, out, err = run(tool, clone, "set", "data_class", "real", "--actor", "admin")
    assert code == 0, (out, err)
    assert "test -> real (revision 1)" in out and "keep the class they were captured with" in out
    assert journal(clone) == [("data_class", 1, "real", admin, None)]          # the identity, never the login

    code, out, _ = run(tool, clone, "set", "data_class", "real", "--actor", "admin")
    assert code == 0 and "already real; nothing to do" in out and len(journal(clone)) == 1

    assert run(tool, clone, "set", "data_class", "test", "--actor", "admin")[0] == 0
    code, out, _ = run(tool, clone, "set", "training_use", "on", "--actor", "admin", "--owner-permission-ref", REF)
    assert code == 0 and "off -> on (revision 1)" in out, out
    assert journal(clone) == [("data_class", 1, "real", admin, None), ("data_class", 2, "test", admin, None),
                              ("training_use", 1, "on", admin, REF)]
    shown = run(tool, clone, "show")[1]
    assert "data_class: test (revision 2; default test)" in shown and "training_use: on (revision 1; default off)" in shown


def test_the_refusals_change_nothing(clone: Any) -> None:
    for argv, says in [
        (["set", "training_use", "on", "--actor", "admin"], "--owner-permission-ref"),            # an on releases content off the host
        (["set", "data_class", "production", "--actor", "admin"], "admits ['test', 'real']"),
        (["set", "retention", "forever", "--actor", "admin"], "admits []"),
        (["set", "training_use", "real", "--actor", "admin"], "admits ['off', 'on']"),
        (["set", "data_class", "real", "--actor", "nobody"], "--actor must be the login of an active"),
        (["set", "data_class", "real", "--actor", "admin", "--owner-permission-ref", "x" * 201], "one line of at most 200"),
        (["set", "data_class", "real", "--actor", "admin", "--owner-permission-ref", "two\nlines"], "one line of at most 200"),
    ]:
        code, out, err = run(tool, clone, *argv)
        assert code == tool.EXIT_REFUSED and says in err, (argv, code, out, err)
    code, out, err = run(tool, clone, "show", database="some_other_database")
    assert code == tool.EXIT_REFUSED and "not the connected database" in err
    assert journal(clone) == []


def test_the_guards_are_shown_able_to_fail(clone: Any) -> None:
    on_without_permission = ["set", "training_use", "on", "--actor", "admin"]
    assert run(tool, clone, *on_without_permission)[0] == tool.EXIT_REFUSED
    code, out, err = run(mutant("training-needs-permission"), clone, *on_without_permission)
    assert code == tool.EXIT_FAILED and "ck_decision_memory_setting_event_on_needs_permission" in err   # only the table's CHECK is left
    assert journal(clone) == []

    code, out, err = run(mutant("value-in-list"), clone, "set", "data_class", "production", "--actor", "admin")
    assert code == tool.EXIT_FAILED and "ck_decision_memory_setting_event_value" in err                  # likewise
    code, out, err = run(mutant("names-match"), clone, "show", database="some_other_database")
    assert code == 0, (out, err)                                                                         # without the guard it reads another name's data
    code, out, err = run(mutant("reference-shape"), clone, "set", "data_class", "real", "--actor", "admin",
                         "--owner-permission-ref", "two\nlines")
    assert code == 0 or "one line of at most 200" not in err, err
    mutant("head-is-declared")                                                                           # deletes to a module that compiles


def test_a_libpq_variable_that_could_redirect_the_connection_is_refused(clone: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PGHOSTADDR", "203.0.113.9")
    code, out, err = run(tool, clone, "show")
    assert code == tool.EXIT_REFUSED and "PGHOSTADDR" in err and "can redirect the connection" in err
    # the copy without the guard is NOT run here: with the variable set it would connect to the address the variable names
    source = SOURCE.read_text(encoding="utf-8")
    assert re.search(_BLOCK.format(name="no-ambient-libpq"), source, flags=re.DOTALL | re.MULTILINE)
    mutant("no-ambient-libpq")
