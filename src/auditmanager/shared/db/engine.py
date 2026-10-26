"""Typed engine construction. Callers never build a connection themselves.

This is the only place in the codebase that calls ``create_engine``. A module that
needs the database asks for an engine or, far more often, for a session from
:mod:`auditmanager.shared.db.session`.
"""

from __future__ import annotations

import threading

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from auditmanager.shared.db.config import DatabaseSettings, load_settings
from auditmanager.shared.db.errors import DatabaseUnavailableError

_lock = threading.Lock()
_default_engine: Engine | None = None


def create_database_engine(settings: DatabaseSettings) -> Engine:
    """Build an :class:`~sqlalchemy.Engine` from validated settings.

    ``pool_pre_ping`` is on: a connection recycled by the server between requests
    is discovered and replaced rather than surfacing as a random operational error
    in the middle of a transaction.

    ``hide_parameters`` is on (``EXPOSURE-REVIEW-02`` ``F-12``): without it a SQLAlchemy
    exception renders ``[parameters: (...)]`` after the statement, and the sinks that log an
    exception (the run carrier, the worker) would write bound values -- client text, model
    output -- into the container log. The statement text stays in the message; the values do
    not, in the exception string and in the statement log that ``echo`` turns on. This does
    **not** remove the database server's own ``DETAIL`` line (``Failing row contains (...)``,
    ``Key (...)=(...) already exists``), which the driver puts in the same string; that is a
    separate, open follow-up (``docs/program/HARDEN-01.md``).
    """
    return create_engine(
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
