"""Typed engine construction. Callers never build a connection themselves.

This is the only place in the codebase that calls ``create_engine``. A module that
needs the database asks for an engine or, far more often, for a session from
:mod:`auditmanager.shared.db.session`.
"""

from __future__ import annotations

import ctypes
import os
import re
import threading
from collections.abc import Iterable
from functools import cache
from typing import Any, Final

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.exc import SQLAlchemyError

from auditmanager.shared.db.config import DatabaseSettings, load_settings
from auditmanager.shared.db.errors import DatabaseConfigurationError, DatabaseUnavailableError

_lock = threading.Lock()
_default_engine: Engine | None = None

#: ``PGVerbosity`` of ``libpq-fe.h``: ``PQERRORS_TERSE`` keeps the severity, the primary message and
#: the position, and drops ``DETAIL``, ``HINT``, ``QUERY`` and ``CONTEXT``. The next value up,
#: ``PQERRORS_DEFAULT`` (1), is what a connection starts with. ``PQERRORS_SQLSTATE`` (3) would also
#: drop the primary message, which names the constraint an operator needs.
_PQERRORS_TERSE: Final = 0

#: The file names libpq ships under: ``libpq.so.5.17`` (system) and ``libpq-e9b5c9ac.so.5.18`` (the
#: psycopg wheel's bundled copy). ``libpqxx`` and friends are other libraries.
_LIBPQ_FILE = re.compile(r"libpq(?:-\w+)?\.so(?:\.|$)")


def _loaded_libpq_paths(maps_lines: Iterable[str]) -> frozenset[str]:
    """The distinct libpq files in the lines of ``/proc/<pid>/maps``."""
    paths: set[str] = set()
    for line in maps_lines:
        fields = line.split(maxsplit=5)
        if len(fields) < 6:
            continue
        path = fields[5].strip().removesuffix(" (deleted)")
        if _LIBPQ_FILE.match(os.path.basename(path)):
            paths.add(os.path.realpath(path))
    return frozenset(paths)


@cache
def _driver_libpq() -> ctypes.CDLL:
    """The one libpq this process loaded for psycopg, ready to take ``PQsetErrorVerbosity``.

    psycopg 3 has no wrapper for ``PQsetErrorVerbosity`` (3.3.5: ``PGconn`` has ``error_message`` and
    nothing that sets the verbosity), but it documents ``PGconn.pgconn_ptr`` as the way to hand the
    connection to a libpq function it does not wrap. The function has to be the *loaded* library's:
    the wheel bundles its own libpq next to the extension, a system libpq of another version has a
    different ``PGconn`` layout, and a call through the wrong one writes into the wrong memory. So
    the library is found by what the process has mapped, not by what the system has installed, and
    it is refused unless it is exactly one file whose ``PQlibVersion`` equals the one psycopg
    reports. Anything else raises: a connection that cannot be made terse is not served verbose.
    """
    import psycopg.pq  # the lock pins psycopg; imported here so the module stays importable without a driver

    try:
        with open("/proc/self/maps", encoding="utf-8") as maps:
            paths = _loaded_libpq_paths(maps)
    except OSError as exc:
        raise DatabaseConfigurationError(
            "cannot tell which libpq psycopg loaded (/proc/self/maps is unreadable), so the "
            f"connection cannot be set to terse error messages: {exc.__class__.__name__}"
        ) from exc
    if len(paths) != 1:
        raise DatabaseConfigurationError(
            f"expected exactly one libpq mapped into the process, found {len(paths)}; refusing to "
            "call PQsetErrorVerbosity through a library that may not be psycopg's"
        )
    library = ctypes.CDLL(next(iter(paths)))
    library.PQlibVersion.argtypes = []
    library.PQlibVersion.restype = ctypes.c_int
    if int(library.PQlibVersion()) != int(psycopg.pq.version()):
        raise DatabaseConfigurationError(
            f"the mapped libpq reports version {library.PQlibVersion()} but psycopg reports "
            f"{psycopg.pq.version()}; refusing to call PQsetErrorVerbosity across versions"
        )
    library.PQsetErrorVerbosity.argtypes = [ctypes.c_void_p, ctypes.c_int]
    library.PQsetErrorVerbosity.restype = ctypes.c_int
    return library


def _set_terse_error_verbosity(dbapi_connection: Any, connection_record: Any) -> None:
    """``connect`` event: ask libpq for terse error messages on this one connection.

    ``EXPOSURE-REVIEW-02`` ``F-12``. The server's ``DETAIL`` line carries the refused row
    (``Failing row contains (...)``, ``Key (a)=(k1) already exists``) and libpq formats it into the
    message psycopg puts in ``str(exc)``; a sink that logs the exception then writes client text. The
    verbosity is a property of the libpq connection and applies to every result built after it is
    set, so it is set here, before the pool hands the connection out. SQLSTATE, the primary message
    (which names the constraint) and the structured ``diag`` fields are unaffected.

    Raises rather than leaving the connection verbose; the half-opened connection is closed first.
    """
    try:
        pointer = dbapi_connection.pgconn.pgconn_ptr
        if not pointer:
            raise DatabaseConfigurationError("the new connection has no libpq handle to configure")
        _driver_libpq().PQsetErrorVerbosity(ctypes.c_void_p(pointer), _PQERRORS_TERSE)
    except BaseException:
        dbapi_connection.close()
        raise


def create_database_engine(settings: DatabaseSettings) -> Engine:
    """Build an :class:`~sqlalchemy.Engine` from validated settings.

    ``pool_pre_ping`` is on: a connection recycled by the server between requests
    is discovered and replaced rather than surfacing as a random operational error
    in the middle of a transaction.

    ``hide_parameters`` is on (``EXPOSURE-REVIEW-02`` ``F-12``): without it a SQLAlchemy
    exception renders ``[parameters: (...)]`` after the statement, and the sinks that log an
    exception (the run carrier, the worker) would write bound values -- client text, model
    output -- into the container log. The statement text stays in the message; the values do
    not, in the exception string and in the statement log that ``echo`` turns on. That flag
    alone does **not** remove the database server's own ``DETAIL`` line (``Failing row contains
    (...)``, ``Key (...)=(...) already exists``), which the driver puts in the same string; the
    terse verbosity below does.

    Every new PostgreSQL connection is also set to **terse** libpq error verbosity
    (``SEC-DB-TERSE-ERRORS-01``, the other half of ``F-12``): the message in an exception string
    keeps the severity and the primary text (``duplicate key value violates unique constraint
    "uq_x"``) and loses the server's ``DETAIL``/``HINT``/``CONTEXT``, so no row data is in it. An
    operator who wants the detail reads the server's own log, or ``exc.orig.diag.message_detail``
    in a debugger; nothing in the product prints it. The hook is installed only for the
    ``psycopg`` driver (the only one ``parse_database_url`` admits); a throw-away SQLite engine
    built through this constructor has no such message to tame.
    """
    engine = create_engine(
        settings.url,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout,
        pool_recycle=settings.pool_recycle,
        pool_pre_ping=True,
        echo=settings.echo,
        hide_parameters=True,
        future=True,
    )
    if engine.dialect.driver == "psycopg":
        event.listen(engine, "connect", _set_terse_error_verbosity)
    return engine


def get_engine() -> Engine:
    """The process-wide engine, built once from the environment on first use.

    Reused across calls because a connection pool is a process resource. Tests that
    need isolation call :func:`create_database_engine` with their own settings
    instead of touching this one.
    """
    global _default_engine
    if _default_engine is None:
        with _lock:
            if _default_engine is None:
                _default_engine = create_database_engine(load_settings())
    return _default_engine


def dispose_engine() -> None:
    """Close the process-wide engine's pool and forget it."""
    global _default_engine
    with _lock:
        if _default_engine is not None:
            _default_engine.dispose()
            _default_engine = None


def verify_connectivity(engine: Engine) -> str:
    """Open one connection and return the server version string.

    Raises :class:`DatabaseUnavailableError` when the database cannot be reached.
    The driver's message is included because an operator needs the reason, and it
    is a connection fault rather than caller data; it is not returned to a caller
    and not placed in an error envelope.
    """
    try:
        with engine.connect() as connection:
            return str(connection.execute(text("SELECT version()")).scalar_one())
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError(
            f"could not connect to the configured database: {exc.__class__.__name__}: {exc}"
        ) from exc
