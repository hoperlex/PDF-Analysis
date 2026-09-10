"""``make check-db`` — prove application connectivity and the current migration head.

Reserved path and invocation, from ``docs/program/FOUNDATION_LOCK.json``::

    PYTHONPATH=src .venv/bin/python -m auditmanager.shared.db.check

Success sentinel: ``FOUNDATION-CHECK OK check-db``, and the lock's rule is that the
sentinel must be the **last** actual output line. Everything this module prints is
therefore emitted before it, and the sentinel is printed exactly once, from exactly
one place, only after every check has passed. A zero exit without the sentinel is
refused by ``run_checked`` in the Makefile, so a check that silently does nothing
cannot pass.

Diagnostics go to stderr so a caller can capture stdout and still see the failure.
"""

from __future__ import annotations

import sys
from typing import Final

from sqlalchemy import Engine, text

from auditmanager.shared.db.config import DatabaseSettings, load_settings
from auditmanager.shared.db.engine import create_database_engine, verify_connectivity
from auditmanager.shared.db.errors import DatabaseError
from auditmanager.shared.db.migrations import MigrationState, read_state

SUCCESS_SENTINEL: Final[str] = "FOUNDATION-CHECK OK check-db"
FAILURE_PREFIX: Final[str] = "FOUNDATION-CHECK FAIL check-db"


def _report(message: str) -> None:
    print(message, flush=True)


def _fail(message: str) -> None:
    print(f"{FAILURE_PREFIX}: {message}", file=sys.stderr, flush=True)


def probe_application_write(engine: Engine) -> None:
    """Prove the application role can open a transaction and roll it back.

    Connectivity alone proves the socket, not the grant. This opens a real
    transaction, creates a temporary table, and rolls back — leaving no schema
    change behind, which is what makes it safe to run against a migrated database
    on every ``make foundation``.
    """
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text("CREATE TEMPORARY TABLE check_db_probe (probe integer)"))
            connection.execute(text("INSERT INTO check_db_probe (probe) VALUES (1)"))
            value = connection.execute(text("SELECT probe FROM check_db_probe")).scalar_one()
            if value != 1:
                raise DatabaseError("write probe read back an unexpected value")
        finally:
            transaction.rollback()


def describe_head(state: MigrationState) -> str:
    return state.describe()


def run_check(settings: DatabaseSettings | None = None) -> int:
    """Run every check. Return a process exit status."""
    engine: Engine | None = None
    try:
        resolved = settings if settings is not None else load_settings()
        _report(f"check-db: target      {resolved.render_safe()}")

        engine = create_database_engine(resolved)
        server_version = verify_connectivity(engine)
        _report(f"check-db: server      {server_version.split(' on ')[0]}")

        dialect = engine.dialect.name
        if dialect != "postgresql":
            _fail(f"connected to a {dialect!r} database; this foundation is PostgreSQL only")
            return 3
        _report(f"check-db: dialect     {dialect} via {engine.dialect.driver}")

        state = read_state(engine)
        _report(f"check-db: head        expected {state.expected_head}")
        _report(f"check-db: current     {state.current if state.current else '<none>'}")

        if state.is_unmigrated:
            _fail(
                "the database carries no migration revision. Run `make migrate`; "
                "this check never applies a migration itself."
            )
            return 4
        if not state.is_at_head:
            _fail(
                f"the database is {state.describe()}. Run `make migrate`. A database "
                "behind or ahead of the code is refused rather than served."
            )
            return 5

        probe_application_write(engine)
        _report("check-db: write probe transaction committed nothing and rolled back cleanly")

    except DatabaseError as exc:
        _fail(f"{type(exc).__name__}: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001 - the check reports, it does not raise
        _fail(f"unexpected {type(exc).__name__}: {exc}")
        return 2
    finally:
        if engine is not None:
            engine.dispose()

    # The sentinel is the last actual output line, printed once, only here.
    _report(SUCCESS_SENTINEL)
    return 0


def main() -> int:
    return run_check()


if __name__ == "__main__":
    raise SystemExit(main())
