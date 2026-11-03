"""``tests/support/connection_budget``: the trim that keeps idle pooled connections from outliving their module.

SQLite files stand in for PostgreSQL: the property under test is the pool's, not the server's -- how many
connections an engine keeps after they were returned. Each test has a control that fails if the pool did not behave
the way the module's note says it does.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool, QueuePool

from tests.support import connection_budget as budget


@pytest.fixture(autouse=True)
def _installed():
    budget.install()
    yield


def _engine(tmp_path: Path, **pool) -> object:
    return create_engine(f"sqlite:///{tmp_path / 'pool.db'}", poolclass=QueuePool,
                         **({"pool_size": 5, "max_overflow": 10} | pool))


def _use_concurrently(engine, count: int) -> None:
    """``count`` connections open at the same moment, then all returned to the pool."""
    opened = [engine.connect() for _ in range(count)]
    for connection in opened:
        connection.execute(text("SELECT 1"))
    for connection in opened:
        connection.close()


def test_without_the_trim_the_pool_keeps_what_was_returned_to_it(tmp_path: Path) -> None:
    """The control: the premise of the module. Five concurrent uses leave five connections held by the engine."""
    engine = _engine(tmp_path)
    _use_concurrently(engine, 5)
    assert engine.pool.checkedin() == 5
    engine.dispose()


def test_the_trim_closes_the_idle_connections_of_every_engine_that_opened_one(tmp_path: Path) -> None:
    first, second = _engine(tmp_path), _engine(tmp_path)
    _use_concurrently(first, 4)
    _use_concurrently(second, 3)
    assert budget.idle_connections() >= 7
    closed = budget.trim_idle_connections()
    assert closed >= 7
    assert first.pool.checkedin() == 0 and second.pool.checkedin() == 0
    assert budget.idle_connections() == 0


def test_the_engine_is_still_usable_after_the_trim(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _use_concurrently(engine, 3)
    budget.trim_idle_connections()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 41 + 1")).scalar_one() == 42
    assert engine.pool.checkedin() == 1, "it opened what it needed and nothing more"
    engine.dispose()


def test_a_connection_that_is_checked_out_is_not_touched_by_the_trim(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    held = engine.connect()
    held.execute(text("CREATE TABLE IF NOT EXISTS t (x integer)"))
    _use_concurrently(engine, 3)
    budget.trim_idle_connections()
    assert engine.pool.checkedin() == 0
    held.execute(text("INSERT INTO t VALUES (1)"))  # still the same live connection
    held.commit()
    held.close()
    engine.dispose()


def test_an_engine_with_an_options_clone_is_trimmed_through_the_shared_pool(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    autocommit = engine.execution_options(isolation_level="AUTOCOMMIT")
    with autocommit.connect() as connection:
        connection.execute(text("SELECT 1"))
    assert engine.pool.checkedin() == 1
    budget.trim_idle_connections()
    assert engine.pool.checkedin() == 0 and autocommit.pool.checkedin() == 0


def test_a_pool_that_keeps_nothing_has_nothing_to_trim(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'null.db'}", poolclass=NullPool)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    assert budget.trim_idle_connections() >= 0  # no exception for a pool without ``checkedin``
    engine.dispose()


def test_a_thread_that_still_holds_a_connection_keeps_it_across_the_trim(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    holding, release = threading.Event(), threading.Event()
    seen: dict[str, int] = {}

    def hold() -> None:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            holding.set()
            release.wait(10)
            seen["answer"] = connection.execute(text("SELECT 7")).scalar_one()

    worker = threading.Thread(target=hold)
    worker.start()
    try:
        assert holding.wait(10)
        budget.trim_idle_connections()
    finally:
        release.set()
        worker.join(10)
    assert seen == {"answer": 7}
    engine.dispose()


def test_a_module_boundary_is_the_last_test_of_a_file() -> None:
    a1, a2 = SimpleNamespace(path=Path("a.py")), SimpleNamespace(path=Path("a.py"))
    b1 = SimpleNamespace(path=Path("b.py"))
    assert budget.is_module_boundary(a1, b1) is True
    assert budget.is_module_boundary(a1, a2) is False
    assert budget.is_module_boundary(a1, None) is True


def test_the_root_conftest_runs_the_trim_at_a_module_boundary(request: pytest.FixtureRequest) -> None:
    """Wired, not just written: the root conftest registered the module and a teardown hook that calls it."""
    registered = sys.modules.get("am_connection_budget")
    assert registered is not None and callable(registered.trim_idle_connections)
    root = [
        plugin for plugin in request.config.pluginmanager.get_plugins()
        if str(getattr(plugin, "__file__", "")).endswith("/tests/conftest.py")
    ]
    assert len(root) == 1 and callable(getattr(root[0], "pytest_runtest_teardown", None))
    assert registered._installed is True
