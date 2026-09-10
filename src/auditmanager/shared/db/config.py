"""Database configuration read from the frozen environment contract.

``DATABASE_URL`` is one of the fifteen names FF-01 freezes and ``.env.example``
declares. The driver is fixed by the root lock: psycopg 3 through SQLAlchemy, so
the URL must carry ``postgresql+psycopg``. A bare ``postgresql://`` would silently
select psycopg2, which is not in the lock, and ``sqlite://`` would make the whole
PostgreSQL-only test contract vacuous. Both are refused here rather than at first
query.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

from auditmanager.shared.db.errors import DatabaseConfigurationError

#: The only accepted SQLAlchemy driver name, pinned by ``pyproject.toml``.
REQUIRED_DRIVERNAME: Final[str] = "postgresql+psycopg"

#: The environment variable carrying the application-facing database value.
DATABASE_URL_VAR: Final[str] = "DATABASE_URL"


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """Everything the boundary needs to build an engine. Constructed, never global.

    ``url`` is a SQLAlchemy :class:`~sqlalchemy.engine.URL`, which renders its
    password as ``***`` in ``str()`` and ``repr()``. That is deliberate: this object
    is safe to log.
    """

    url: URL
    #: Connections kept open in the pool.
    pool_size: int = 5
    #: Connections the pool may open beyond ``pool_size`` under load.
    max_overflow: int = 5
    #: Seconds to wait for a pooled connection before failing.
    pool_timeout: int = 30
    #: Seconds after which an idle pooled connection is discarded.
    pool_recycle: int = 1800
    #: Emit SQL to the logger. Never enabled by default: statements can carry data.
    echo: bool = False

    @property
    def database(self) -> str:
        """The database name, for diagnostics."""
        return self.url.database or ""

    def render_safe(self) -> str:
        """The URL with the password obscured, safe for logs and check output."""
        return self.url.render_as_string(hide_password=True)


def parse_database_url(raw_url: str) -> URL:
    """Parse and validate one ``DATABASE_URL`` value.

    Raises :class:`DatabaseConfigurationError` for an unparseable value, for any
    driver other than :data:`REQUIRED_DRIVERNAME`, and for a URL with no database
    name.
    """
    if not raw_url or not raw_url.strip():
        raise DatabaseConfigurationError(
            f"{DATABASE_URL_VAR} is set but empty. It must be a "
            f"{REQUIRED_DRIVERNAME} URL naming a database."
        )
    try:
        url = make_url(raw_url.strip())
    except ArgumentError as exc:
        # The message from make_url can echo the raw value, which carries a
        # password. Report the fault without the value.
        raise DatabaseConfigurationError(
            f"{DATABASE_URL_VAR} is not a parseable SQLAlchemy URL "
            f"({type(exc).__name__}). Expected {REQUIRED_DRIVERNAME}://..."
        ) from None
    if url.drivername != REQUIRED_DRIVERNAME:
        raise DatabaseConfigurationError(
            f"{DATABASE_URL_VAR} names driver {url.drivername!r}; this foundation "
            f"supports {REQUIRED_DRIVERNAME!r} only. The root lock pins psycopg 3 and "
            "the migration and test contract is PostgreSQL, never SQLite."
        )
    if not url.database:
        raise DatabaseConfigurationError(
            f"{DATABASE_URL_VAR} carries no database name."
        )
    return url


def load_settings(environ: dict[str, str] | None = None) -> DatabaseSettings:
    """Build :class:`DatabaseSettings` from the process environment.

    Passing ``environ`` explicitly keeps tests from mutating global state.
    """
    source = os.environ if environ is None else environ
    raw_url = source.get(DATABASE_URL_VAR)
    if raw_url is None:
        raise DatabaseConfigurationError(
            f"{DATABASE_URL_VAR} is not set. It is one of the fifteen names frozen by "
            "FF-01; copy .env.example to .env and give this lane its own instance "
            "values. No default connection is assumed."
        )
    return DatabaseSettings(url=parse_database_url(raw_url))
