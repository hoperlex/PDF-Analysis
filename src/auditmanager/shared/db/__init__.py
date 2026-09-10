"""The database boundary. Every connection in the codebase is opened from here.

Callers do not execute connection setup themselves::

    from auditmanager.shared.db import session_scope

    with session_scope() as session:
        session.execute(...)          # committed on clean exit, rolled back on error

What this boundary deliberately does **not** provide, per the task's non-goals: a
generic base repository, a CRUD service, an automatic retry and a transactional
outbox. A retry that does not consult the command's idempotency record writes
duplicates, and an outbox belongs to the module that owns the side effect.

The check that ``make check-db`` forwards to lives in
:mod:`auditmanager.shared.db.check`. It is intentionally not re-exported here: it
is a process entry point, not a library call.
"""

from __future__ import annotations

from auditmanager.shared.db.config import (
    DATABASE_URL_VAR,
    REQUIRED_DRIVERNAME,
    DatabaseSettings,
    load_settings,
    parse_database_url,
)
from auditmanager.shared.db.engine import (
    create_database_engine,
    dispose_engine,
    get_engine,
    verify_connectivity,
)
from auditmanager.shared.db.errors import (
    DatabaseConfigurationError,
    DatabaseError,
    DatabaseUnavailableError,
    MigrationStateError,
)
from auditmanager.shared.db.migrations import (
    MigrationState,
    current_revision,
    head_revision,
    read_state,
    require_head,
    revision_walk,
)
from auditmanager.shared.db.schema import (
    NAMING_CONVENTION,
    SQLSTATE_APPEND_ONLY_VIOLATION,
    SQLSTATE_IMMUTABLE_ROW_VIOLATION,
    SQLSTATE_TO_CATALOG_CODE,
    SQLSTATE_UNDECLARED_TRANSITION,
    metadata,
)
from auditmanager.shared.db.session import (
    connection_scope,
    create_session_factory,
    get_session_factory,
    nested_transaction,
    reset_session_factory,
    session_scope,
)

__all__ = [
    "DATABASE_URL_VAR",
    "NAMING_CONVENTION",
    "REQUIRED_DRIVERNAME",
    "SQLSTATE_APPEND_ONLY_VIOLATION",
    "SQLSTATE_IMMUTABLE_ROW_VIOLATION",
    "SQLSTATE_TO_CATALOG_CODE",
    "SQLSTATE_UNDECLARED_TRANSITION",
    "DatabaseConfigurationError",
    "DatabaseError",
    "DatabaseSettings",
    "DatabaseUnavailableError",
    "MigrationState",
    "MigrationStateError",
    "connection_scope",
    "create_database_engine",
    "create_session_factory",
    "current_revision",
    "dispose_engine",
    "get_engine",
    "get_session_factory",
    "head_revision",
    "load_settings",
    "metadata",
    "nested_transaction",
    "parse_database_url",
    "read_state",
    "require_head",
    "reset_session_factory",
    "revision_walk",
    "session_scope",
    "verify_connectivity",
]
