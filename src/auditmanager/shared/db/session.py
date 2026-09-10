"""Session and transaction construction.

One factory, two context managers, and nothing else:

``session_scope()``
    One unit of work. Commits on clean exit, rolls back on any exception, and
    always closes. A caller never writes ``try/except/rollback`` itself.

``nested_transaction(session)``
    A SAVEPOINT inside an open unit of work, for the case where one step may fail
    without discarding the whole command.

There is no base repository, no generic CRUD service and no automatic retry: the
task's non-goals rule all three out, and a retry that is not aware of the command's
idempotency record is a duplicate-writing bug rather than a convenience.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.db.engine import get_engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a session factory bound to one engine.

    ``expire_on_commit=False`` so objects read inside a unit of work stay usable
    after it commits; the alternative is a lazy refresh against a closed session,
    which fails at the point of *use* rather than at the point of the mistake.
    """
    return sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=True,
        autobegin=True,
        future=True,
    )


_default_factory: sessionmaker[Session] | None = None


def get_session_factory() -> sessionmaker[Session]:
    """The process-wide session factory, bound to the process-wide engine."""
    global _default_factory
    if _default_factory is None:
        _default_factory = create_session_factory(get_engine())
    return _default_factory


def reset_session_factory() -> None:
    """Forget the process-wide factory. Used when the engine is disposed."""
    global _default_factory
    _default_factory = None


@contextmanager
def session_scope(
    factory: sessionmaker[Session] | None = None,
) -> Iterator[Session]:
    """One unit of work: commit on success, roll back on any exception.

    The rollback is unconditional on the exception path, including for
    ``KeyboardInterrupt`` and ``SystemExit``, because a half-applied command must
    never be left visible to a concurrent reader.
    """
    session = (factory or get_session_factory())()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def nested_transaction(session: Session) -> Iterator[Session]:
    """A SAVEPOINT within an already-open unit of work.

    On an exception the savepoint is rolled back and the exception propagates; the
    enclosing transaction is left intact and is still the caller's to commit or
    abandon.
    """
    with session.begin_nested():
        yield session


@contextmanager
def connection_scope(engine: Engine | None = None) -> Iterator[object]:
    """A Core connection inside one transaction, for DDL-free statement work.

    Used by the migration-state probe and by tests that assert on raw SQL. Business
    code uses :func:`session_scope`.
    """
    target = engine or get_engine()
    with target.begin() as connection:
        yield connection
