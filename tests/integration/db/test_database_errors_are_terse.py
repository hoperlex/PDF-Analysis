"""`SEC-DB-TERSE-ERRORS-01` / `F-12` (`EXPOSURE-REVIEW-02`): a database error raised through the
product's engine carries no row data -- not in ``str(exc)``, not in the exception it chains from,
not in the traceback a ``_log.exception`` sink writes.

The residual this closes (``docs/program/HARDEN-01.md``, "Needs your attention" 1):
``hide_parameters=True`` removes SQLAlchemy's ``[parameters: ...]``, but PostgreSQL's own message
travels in the same string. A refused row prints ``DETAIL:  Failing row contains (...)`` and a
unique or foreign-key refusal prints ``DETAIL:  Key (a)=(k1) already exists.``, so a column of the
row -- ``D-225``'s model output, a client document's text -- reached every log line that prints the
exception: the two ``_log.exception`` sinks (``runs/carrier.py``, ``workers/service.py``) and any
other.

**What is asserted.** On a real PostgreSQL database (a private, throw-away one from the suite's
``empty_database`` fixture), with a distinctive sentinel bound into the refused row, for each of a
unique, a CHECK, a NOT NULL and a foreign-key refusal:

* the sentinel is absent from ``str``/``repr`` of the SQLAlchemy exception, from ``str``/``repr``/
  ``args`` of the driver exception it wraps, and from the text a ``logger.exception`` call writes
  (which includes the chained driver exception, as both product sinks do);
* the words an operator needs stay: the exception class (the SQLSTATE class), the primary message
  (``... violates unique constraint "uq_doc_body"``) and the statement text;
* the structured fields the product reads stay: ``sqlstate``, ``diag.constraint_name`` and the
  product's own readers ``documents.sqlstate_of`` / ``constraint_name_of``.

**The control.** The same refusals through an engine built with ``hide_parameters=True`` and no
terse hook must show the sentinel and the ``DETAIL`` line. A test that only ever saw clean strings
would be green whether or not the hook did anything, and the control is also what a reader of the
previous lane's report measured.

**Every connection, every engine.** The setting is per libpq connection, so a pool that opened a
second connection, an engine rebuilt by ``dispose()``, and the process-wide ``get_engine()`` each
get their own case.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import IntegrityError

from auditmanager.documents.refusals import constraint_name_of, sqlstate_of
from auditmanager.shared.db import DatabaseSettings, create_database_engine, dispose_engine, get_engine

#: A value that cannot occur anywhere in an error message by accident.
SENTINEL = "client-text-9f3a1c7e-must-not-be-logged"

_DDL = (
    "create table parent (pid text primary key)",
    """create table doc (
         id text primary key,
         body text not null,
         kind text not null,
         parent text,
         constraint uq_doc_body unique (body),
         constraint ck_doc_kind check (kind <> 'forbidden'),
         constraint fk_doc_parent foreign key (parent) references parent (pid)
       )""",
)
_INSERT = text("insert into doc (id, body, kind, parent) values (:id, :body, :kind, :parent)")


def _row(id_: str, *, body: str | None, kind: str = "ok", parent: str | None = None) -> dict[str, Any]:
    return {"id": id_, "body": body, "kind": kind, "parent": parent}


#: name -> (row to insert after the seed row, SQLSTATE, constraint name, column name, primary message)
_CASES: dict[str, tuple[dict[str, Any], str, str | None, str | None, str]] = {
    "unique": (
        _row("d1", body=SENTINEL),
        "23505", "uq_doc_body", None,
        'duplicate key value violates unique constraint "uq_doc_body"',
    ),
    "check": (
        _row("d2", body=SENTINEL + "-check", kind="forbidden"),
        "23514", "ck_doc_kind", None,
        'new row for relation "doc" violates check constraint "ck_doc_kind"',
    ),
    "not_null": (
        _row("d3", body=None, kind=SENTINEL),
        "23502", None, "body",
        'null value in column "body" of relation "doc" violates not-null constraint',
    ),
    "foreign_key": (
        _row("d4", body="b4", parent=SENTINEL),
        "23503", "fk_doc_parent", None,
        'insert or update on table "doc" violates foreign key constraint "fk_doc_parent"',
    ),
}


def _prepare(engine: Engine) -> None:
    """Create the tables and seed the one row whose body the unique case collides with."""
    with engine.begin() as connection:
        for statement in _DDL:
            connection.execute(text(statement))
        connection.execute(_INSERT, _row("d0", body=SENTINEL))


def _refusal(engine: Engine, case: str) -> IntegrityError:
    with pytest.raises(IntegrityError) as caught:
        with engine.begin() as connection:
            connection.execute(_INSERT, _CASES[case][0])
    return caught.value


def _everything_a_log_line_could_print(refusal: IntegrityError, caplog: pytest.LogCaptureFixture) -> str:
    """Every rendering of the refusal a sink or a debugger could write, joined."""
    log = logging.getLogger("sec_db_terse_errors_probe")
    caplog.clear()
    with caplog.at_level(logging.ERROR, logger=log.name):
        try:
            raise refusal
        except IntegrityError:
            log.exception("probe sink")
    driver = refusal.orig
    parts = [
        str(refusal), repr(refusal), str(driver), repr(driver),
        " | ".join(str(argument) for argument in driver.args),
        caplog.text,
    ]
    return "\n".join(parts)


@pytest.fixture
def product_engine(empty_database: DatabaseSettings) -> Iterator[Engine]:
    engine = create_database_engine(empty_database)
    try:
        _prepare(engine)
        yield engine
    finally:
        engine.dispose()


@pytest.mark.parametrize("case", sorted(_CASES))
def test_the_control_an_engine_without_the_hook_prints_the_row(
    case: str, empty_database: DatabaseSettings, caplog: pytest.LogCaptureFixture
) -> None:
    """If this goes quiet the tests below prove nothing: the leak has to be visible to be absent."""
    engine = create_engine(
        empty_database.url.render_as_string(hide_password=False), hide_parameters=True
    )
    try:
        _prepare(engine)
        rendered = _everything_a_log_line_could_print(_refusal(engine, case), caplog)
    finally:
        engine.dispose()
    assert "DETAIL:" in rendered
    assert SENTINEL in rendered


@pytest.mark.parametrize("case", sorted(_CASES))
def test_a_refusal_through_the_product_engine_carries_no_row_data(
    case: str, product_engine: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    refusal = _refusal(product_engine, case)
    rendered = _everything_a_log_line_could_print(refusal, caplog)
    assert SENTINEL not in rendered
    assert "DETAIL:" not in rendered
    assert "Failing row contains" not in rendered
    assert "already exists" not in rendered
    assert "is not present in table" not in rendered
    # what an operator keeps: which statement, which class of refusal, which constraint
    _row_, sqlstate, constraint, _column, primary = _CASES[case]
    assert primary in str(refusal)
    assert "insert into doc (id, body, kind, parent) values" in str(refusal)
    assert type(refusal.orig).__name__ in str(refusal)
    assert primary in caplog.text, "the sink wrote no primary message, so it did not test the sink"


@pytest.mark.parametrize("case", sorted(_CASES))
def test_the_structured_fields_the_product_reads_survive(case: str, product_engine: Engine) -> None:
    """``constraint_name`` and SQLSTATE come from the driver's fields, not from the message."""
    refusal = _refusal(product_engine, case)
    _row_, sqlstate, constraint, column, _primary = _CASES[case]
    assert refusal.orig.sqlstate == sqlstate
    assert refusal.orig.diag.constraint_name == constraint
    if column is not None:
        assert refusal.orig.diag.column_name == column
    # the product's own readers (``documents.refusals``), which every unique-violation handler uses
    assert sqlstate_of(refusal) == sqlstate
    assert constraint_name_of(refusal) == constraint


def test_every_pooled_connection_is_terse(empty_database: DatabaseSettings, caplog: pytest.LogCaptureFixture) -> None:
    """The setting belongs to one libpq connection; a hook that ran once would leave the rest verbose."""
    settings = DatabaseSettings(url=empty_database.url, pool_size=2, max_overflow=2)
    engine = create_database_engine(settings)
    try:
        _prepare(engine)
        connections = [engine.connect() for _ in range(3)]
        try:
            assert len({id(c.connection.dbapi_connection) for c in connections}) == 3
            for connection in connections:
                with pytest.raises(IntegrityError) as caught:
                    connection.execute(_INSERT, _CASES["unique"][0])
                connection.rollback()
                assert SENTINEL not in _everything_a_log_line_could_print(caught.value, caplog)
        finally:
            for connection in connections:
                connection.close()
        # dispose() rebuilds the pool; connections it opens afterwards are new libpq connections
        engine.dispose()
        assert SENTINEL not in _everything_a_log_line_could_print(_refusal(engine, "unique"), caplog)
    finally:
        engine.dispose()


def test_the_process_wide_engine_is_terse(
    empty_database: DatabaseSettings, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """``get_engine()`` is what the served application uses; it must not be the engine left out."""
    monkeypatch.setenv("DATABASE_URL", empty_database.url.render_as_string(hide_password=False))
    dispose_engine()
    try:
        engine = get_engine()
        _prepare(engine)
        rendered = _everything_a_log_line_could_print(_refusal(engine, "unique"), caplog)
    finally:
        dispose_engine()
    assert SENTINEL not in rendered
    assert "DETAIL:" not in rendered
