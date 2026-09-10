"""Alembic environment for the AuditManager migration head.

The connection value comes from ``DATABASE_URL`` through
:mod:`auditmanager.shared.db.config`, so the runner and the application validate it
identically: the same driver check, the same explicit failure when it is missing.
``alembic.ini`` carries no URL.

Autogenerate is deliberately unwired. Every P02 table is written as explicit DDL in
the revision module, because the invariants that matter here — append-only ledgers,
immutable published rows, declared state topology — are triggers and CHECK
constraints that autogenerate neither produces nor notices going missing. A model
tree that only existed to feed autogenerate would be a second description of the
schema for nobody to use.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context

# When Alembic is driven through its Python API the ini's prepend_sys_path has
# already run; when this file is imported some other way it may not have. Both paths
# end at the same repository ``src``.
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from auditmanager.shared.db.config import load_settings  # noqa: E402
from auditmanager.shared.db.engine import create_database_engine  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# No declarative metadata: see the module docstring.
target_metadata = None


def _settings():
    """Resolve database settings, allowing a caller to override the URL.

    ``alembic -x database_url=...`` is honoured so a test can migrate a throwaway
    database without mutating ``os.environ`` for the whole process. It is an
    explicit override on the command line, not a silent fallback.
    """
    override = context.get_x_argument(as_dictionary=True).get("database_url")
    if override:
        return load_settings({"DATABASE_URL": override})
    return load_settings()


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting."""
    settings = _settings()
    context.configure(
        url=settings.url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against a live connection.

    The whole upgrade runs inside one transaction. PostgreSQL has transactional
    DDL, so a migration that fails halfway leaves the database exactly where it
    started rather than in an unnamed intermediate schema.
    """
    settings = _settings()
    connectable = create_database_engine(settings)
    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                transaction_per_migration=False,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
