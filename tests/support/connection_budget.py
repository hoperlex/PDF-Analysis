"""Connections that outlive the test that opened them must not outlive its module.

**What was measured** (`EXEC2-FIX-BACKEND`, the first full database battery of the common cross-wave run): the suite
died of ``FATAL: sorry, too many clients already`` -- 2464 times, in 162 test sections, from ``norms/search`` onward and
for the rest of the run -- against a PostgreSQL with ``max_connections = 100``. No test holds a hundred connections at
once. What the suite holds is the sum, over the roughly forty directories before that point, of connections nobody
closed, and ``pg_stat_activity`` plus a census of the live engines (sampled after every test, with this trim switched
off) shows two sources:

* **A function-scoped fixture that composes a whole application per test.** ``create_app()`` builds an engine of its own
  and nothing in the product closes it (a server process ends instead); the application then sits in a reference
  cycle until the collector reaches it. ``ingest/comparison_batch/test_http.py`` was measured at **one more open
  connection after each of its fourteen tests** (the suite's database 2 -> 16), none given back while the rest of the
  directory ran, and ``ingest/comparison_pdf/test_http.py`` the same (28 -> 32 across its first five).
* **Session-scoped engines.** Almost every directory has a session-scoped ``engine`` fixture (thirty-odd: the run-suite
  harness bound by eight conftests, ``ingest``, ``auth``, ``decisions``, ``findings``, ``api``, each ``comparison/*``
  and ``norms/*`` directory ...), and a session-scoped fixture lives to the end of the **whole** session however early
  its last test ran. Each engine has the product's default pool (``pool_size`` 5), and a test that uses two connections
  at once leaves the pool holding them. Measured, with the directories run alone: executors ends holding 12, jobs adds
  5, workers 4, runs 1; ``characterization`` to ``api`` 13; composition peaks at 24 and falls back to 5 once its
  applications are collected.

Neither is a leak in one test, and no single directory is large; it is that none of it was ever given back, so the
total passed the server's limit around ``norms/search``.

**What this does.** Every engine that has handed out a connection is remembered (weakly). At the end of each test
module -- the last test of a file, when the next test belongs to another file -- :func:`trim_idle_connections` collects
garbage (freeing the applications and engines that were dropped inside a cycle) and disposes the pool of every
remembered engine that still has checked-in connections. ``Engine.dispose()`` closes the checked-in connections of the
old pool and gives the engine a fresh one, so the engine stays usable by the next module that needs it (it opens what
it uses); a connection that is still *checked out* is not touched: it goes back to the discarded pool and is closed when
its owner returns it. :func:`dispose_application` is the same for one composed application and is what a function-scoped
fixture that builds one calls in its ``finally``.

**What it does not do.** It does not raise ``max_connections``, shrink the product's pool, or close a connection a test
still holds: the peak the suite needs is unchanged, and a test that opens many and keeps them still fails on its own.
``tests/unit/shared/test_connection_budget.py`` proves each of those properties, including that without the trim the
pool really keeps what was returned to it.
"""

from __future__ import annotations

import gc
import weakref
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

_engines: "weakref.WeakSet[Engine]" = weakref.WeakSet()
_installed = False


def _remember(connection: Any) -> None:
    _engines.add(connection.engine)


def install() -> None:
    """Remember every engine that opens a connection from now on. Idempotent."""
    global _installed
    if not _installed:
        event.listen(Engine, "engine_connect", _remember)
        _installed = True


def remembered() -> list[Engine]:
    return list(_engines)


def idle_connections() -> int:
    """Checked-in connections held by the pools of the remembered engines (those that report it)."""
    total = 0
    for engine in remembered():
        checked_in = getattr(engine.pool, "checkedin", None)
        if callable(checked_in):
            total += int(checked_in())
    return total


def trim_idle_connections() -> int:
    """Dispose the pool of every remembered engine that holds checked-in connections; returns how many were closed.

    A collection first: an application or a fixture that was dropped but sits in a reference cycle (an engine, its pool,
    the connection records that point back at both) is still holding its connections until the collector reaches it, and
    nothing guarantees that happens before the next module needs them.
    """
    gc.collect()
    closed = 0
    for engine in remembered():
        checked_in = getattr(engine.pool, "checkedin", None)
        idle = int(checked_in()) if callable(checked_in) else 0
        if idle:
            engine.dispose()
            closed += idle
    return closed


def is_module_boundary(item: Any, nextitem: Any) -> bool:
    """``True`` after the last test of a file: there is no next test, or it lives in another file."""
    return nextitem is None or getattr(nextitem, "path", None) != getattr(item, "path", None)


def dispose_application(application: Any) -> None:
    """Release what one composed application (``create_app`` / ``build_application``) holds: its run carrier's pool and
    its engine's connections.

    The composition root builds an engine of its own for every application and nothing in the product closes it (a
    server process ends instead). A *function-scoped* fixture that builds one per test therefore leaves a connection
    per test open until the collector reaches the cycle the application is in: ``ingest/comparison_batch/test_http.py``
    was measured at one more connection after each of its fourteen tests. Such a fixture yields the client and calls
    this in its ``finally``.
    """
    carrier = getattr(application, "carrier", None)
    if carrier is not None:
        carrier.shutdown()
    bind = application.session_factory.kw.get("bind")
    if bind is not None:
        bind.dispose()
