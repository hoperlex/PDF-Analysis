"""`SEC-DB-TERSE-ERRORS-01` / `F-12`: the guards around the terse-error hook, with no database.

The behaviour itself (a refusal through the product engine carries no row data) is measured on a
real PostgreSQL in ``tests/integration/db/test_database_errors_are_terse.py``. What is pinned here
is what that test cannot see without a server, and what makes it fail *closed*:

* a PostgreSQL engine built by the one constructor carries the ``connect`` hook, and a SQLite one
  (reachable only from tests) does not;
* no module of ``src`` builds an engine or a connection of its own, so there is no second door the
  hook does not guard (``scripts/`` is named in the report, not scanned here);
* the libpq the hook calls is the one the process loaded, exactly one file, of the version psycopg
  reports -- any doubt raises, because a call through another libpq writes into the wrong layout;
* a connection the hook cannot configure is closed and the error propagates; it is never handed out
  verbose.

Each guard has its failing case beside it; the report lists the mutation that turns each red.
"""

from __future__ import annotations

import ctypes
import re
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import event
from sqlalchemy.engine import make_url

from auditmanager.shared.db import DatabaseSettings, create_database_engine
from auditmanager.shared.db import engine as engine_module
from auditmanager.shared.db.errors import DatabaseConfigurationError

_SRC = Path(__file__).resolve().parents[3] / "src" / "auditmanager"

#: Constructions that open a database connection without going through ``create_database_engine``.
_OWN_CONNECTION = re.compile(
    r"\b(create_engine|create_async_engine|engine_from_config)\(|\bpsycopg\.(?:connect|Connection\.connect)\("
)


def _postgres_engine():  # type: ignore[no-untyped-def]
    """An engine on an address nothing listens on: construction never connects."""
    return create_database_engine(DatabaseSettings(url=make_url("postgresql+psycopg://u:p@127.0.0.1:1/x")))


# --- the hook is installed ----------------------------------------------------------------------


def test_a_postgresql_engine_carries_the_terse_hook() -> None:
    engine = _postgres_engine()
    try:
        assert event.contains(engine, "connect", engine_module._set_terse_error_verbosity)
    finally:
        engine.dispose()


def test_a_sqlite_engine_does_not(tmp_path: Path) -> None:
    """The scope is stated by a test: SQLite has no libpq, and the existing SQLite tests keep working."""
    engine = create_database_engine(DatabaseSettings(url=make_url(f"sqlite+pysqlite:///{tmp_path / 'x.db'}")))
    try:
        assert not event.contains(engine, "connect", engine_module._set_terse_error_verbosity)
    finally:
        engine.dispose()


# --- no second door -----------------------------------------------------------------------------


def _own_connections(root: Path) -> list[str]:
    found = []
    for path in sorted(root.rglob("*.py")):
        if path.relative_to(root).as_posix() == "shared/db/engine.py":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _OWN_CONNECTION.search(line):
                found.append(f"{path.relative_to(root).as_posix()}:{number}: {line.strip()}")
    return found


def test_no_module_of_src_opens_a_connection_of_its_own() -> None:
    assert _own_connections(_SRC) == []


def test_the_scan_sees_a_stray_engine(tmp_path: Path) -> None:
    """A guard that cannot fail is not one: plant each form in a throw-away tree and expect it found."""
    (tmp_path / "shared" / "db").mkdir(parents=True)
    (tmp_path / "shared" / "db" / "engine.py").write_text("create_engine(url)\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("engine = create_engine(url)\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("conn = psycopg.connect(dsn)\n", encoding="utf-8")
    (tmp_path / "c.py").write_text("e = create_async_engine(url)\n", encoding="utf-8")
    (tmp_path / "d.py").write_text("e = create_database_engine(settings)\n", encoding="utf-8")
    found = _own_connections(tmp_path)
    assert [entry.split(":")[0] for entry in found] == ["a.py", "b.py", "c.py"]


# --- the libpq the hook calls is psycopg's ------------------------------------------------------

_MAPS = """\
7f0000000000-7f0000100000 r-xp 00000000 fd:03 100 /usr/lib/python3.12/lib-dynload/_ctypes.so
7f0000200000-7f0000300000 r-xp 00000000 fd:03 101 /venv/psycopg_binary.libs/libpq-e9b5c9ac.so.5.18
7f0000300000-7f0000400000 r--p 00100000 fd:03 101 /venv/psycopg_binary.libs/libpq-e9b5c9ac.so.5.18
7f0000500000-7f0000600000 r-xp 00000000 fd:03 102 /usr/lib/x86_64-linux-gnu/libpqxx-7.so
7f0000700000-7f0000800000 r-xp 00000000 fd:03 103 /venv/psycopg_binary.libs/libssl-1f2e3d4c.so.3
7f0000900000-7f0000a00000 r-xp 00000000 fd:03 104 /tmp/libpq.so.5.17 (deleted)
7f0000b00000-7f0000c00000 rw-p 00000000 00:00 0
"""


def test_the_libpq_files_are_read_from_the_maps() -> None:
    found = engine_module._loaded_libpq_paths(_MAPS.splitlines())
    assert found == {"/venv/psycopg_binary.libs/libpq-e9b5c9ac.so.5.18", "/tmp/libpq.so.5.17"}


def test_the_driver_libpq_is_the_one_the_process_loaded() -> None:
    """The control for the refusals below: unpatched, the lookup succeeds and gives a usable library."""
    library = engine_module._driver_libpq.__wrapped__()
    assert isinstance(library, ctypes.CDLL)


@pytest.mark.parametrize(
    "paths",
    [frozenset(), frozenset({"/a/libpq.so.5.17", "/b/libpq-1234.so.5.18"})],
    ids=["none mapped", "two different libpq files mapped"],
)
def test_anything_but_exactly_one_libpq_is_refused(paths: frozenset[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine_module, "_loaded_libpq_paths", lambda _lines: paths)
    with pytest.raises(DatabaseConfigurationError, match="exactly one libpq"):
        engine_module._driver_libpq.__wrapped__()


def test_a_libpq_of_another_version_than_psycopgs_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    import psycopg.pq

    real = psycopg.pq.version()
    monkeypatch.setattr(psycopg.pq, "version", lambda: real + 1)
    with pytest.raises(DatabaseConfigurationError, match="across versions"):
        engine_module._driver_libpq.__wrapped__()


# --- a connection that cannot be made terse is not handed out ----------------------------------


class _Pgconn:
    def __init__(self, pointer: int | None) -> None:
        self.pgconn_ptr = pointer


class _Connection:
    def __init__(self, pointer: int | None) -> None:
        self.pgconn = _Pgconn(pointer)
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _Library:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, int]] = []

    def PQsetErrorVerbosity(self, pointer: Any, level: int) -> int:  # noqa: N802 - libpq's name
        self.calls.append((pointer.value, level))
        return 1


def test_the_hook_asks_libpq_for_terse_on_the_connections_own_pointer(monkeypatch: pytest.MonkeyPatch) -> None:
    library = _Library()
    monkeypatch.setattr(engine_module, "_driver_libpq", lambda: library)
    connection = _Connection(4242)
    engine_module._set_terse_error_verbosity(connection, None)
    assert library.calls == [(4242, 0)], "PQERRORS_TERSE is 0 in libpq-fe.h"
    assert connection.closed is False


def test_a_connection_without_a_libpq_handle_is_closed_and_refused() -> None:
    connection = _Connection(None)
    with pytest.raises(DatabaseConfigurationError, match="no libpq handle"):
        engine_module._set_terse_error_verbosity(connection, None)
    assert connection.closed is True


def test_a_libpq_that_cannot_be_trusted_closes_the_connection_and_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse() -> None:
        raise DatabaseConfigurationError("expected exactly one libpq")

    monkeypatch.setattr(engine_module, "_driver_libpq", refuse)
    connection = _Connection(4242)
    with pytest.raises(DatabaseConfigurationError):
        engine_module._set_terse_error_verbosity(connection, None)
    assert connection.closed is True
