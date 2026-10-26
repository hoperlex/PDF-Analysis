"""`HARDEN-01` / `F-12` (`EXPOSURE-REVIEW-02`, `D-240`): an engine built by this codebase never prints
the parameters of a statement that failed.

The finding: ``shared/db/engine.py`` built the engine with no ``hide_parameters``, so a SQLAlchemy
exception rendered as ``... [SQL: insert into t(a) values (?)] [parameters: ('x',)]`` and the sinks
that call ``_log.exception`` (``runs/carrier.py``, ``workers/service.py``) wrote the bound values --
client text, model output -- to the container log. ``D-225`` was exactly such a failure: a CHECK
refusing a ``stage_result`` insert that carries the model output.

**What is asserted, and why on SQLite.** The engine is built through the one constructor the
product uses, ``create_database_engine``, from a ``DatabaseSettings`` whose URL is a throw-away
SQLite file. ``parse_database_url`` (which insists on PostgreSQL) is the settings *loader*; the
constructor itself takes any URL, and the rendering of an exception is SQLAlchemy's, not the
dialect's, so this needs no database and no container. Two sinks are driven: the string of the
exception (what ``_log.exception`` writes) and the statement log (``DatabaseSettings.echo``,
off by default, which also prints parameters unless they are hidden).

**The control.** The same statement through an engine built *without* the flag is run first and
must show the value: a test that only ever saw a clean string would be green whether or not the
flag did anything.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from auditmanager.shared.db import DatabaseSettings, create_database_engine

#: A value that cannot occur anywhere in an error message by accident.
SENTINEL = "client-text-9f3a1c7e-must-not-be-logged"

_DDL = "create table t (a text primary key)"
_INSERT = text("insert into t(a) values (:a)")


def _settings(tmp_path: Path, *, echo: bool = False) -> DatabaseSettings:
    return DatabaseSettings(url=make_url(f"sqlite+pysqlite:///{tmp_path / 'engine.db'}"), echo=echo)


def _violate(engine) -> IntegrityError:  # type: ignore[no-untyped-def]
    """Insert the same primary key twice and return the refusal."""
    with engine.begin() as connection:
        connection.execute(text(_DDL))
        connection.execute(_INSERT, {"a": SENTINEL})
    with pytest.raises(IntegrityError) as caught:
        with engine.begin() as connection:
            connection.execute(_INSERT, {"a": SENTINEL})
    return caught.value


def test_the_control_an_engine_without_the_flag_prints_the_parameter(tmp_path: Path) -> None:
    """If this goes quiet the test below proves nothing: the leak must be visible to be absent."""
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'control.db'}")
    try:
        refusal = _violate(engine)
    finally:
        engine.dispose()
    assert "[parameters:" in str(refusal)
    assert SENTINEL in str(refusal)


def test_the_engine_hides_parameters_by_construction(tmp_path: Path) -> None:
    engine = create_database_engine(_settings(tmp_path))
    try:
        assert engine.hide_parameters is True
    finally:
        engine.dispose()


def test_a_refused_statement_carries_no_parameter_in_its_string_or_repr(tmp_path: Path) -> None:
    engine = create_database_engine(_settings(tmp_path))
    try:
        refusal = _violate(engine)
    finally:
        engine.dispose()
    rendered = str(refusal)
    assert "IntegrityError" in type(refusal).__name__
    assert SENTINEL not in rendered
    assert SENTINEL not in repr(refusal)
    assert "[parameters:" not in rendered
    assert "hidden due to hide_parameters=True" in rendered
    # the statement text stays: an operator needs to know which statement failed
    assert "insert into t(a) values" in rendered


def test_the_statement_log_prints_no_parameter_when_echo_is_on(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``DatabaseSettings.echo`` is off by default; if an operator turns it on, values still stay out."""
    engine = create_database_engine(_settings(tmp_path, echo=True))
    try:
        _violate(engine)
    finally:
        engine.dispose()
    captured = capsys.readouterr()
    logged = captured.out + captured.err
    assert "insert into t(a) values" in logged, "echo printed nothing, so this case did not test the sink"
    assert SENTINEL not in logged
