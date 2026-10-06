"""`W49-QA-01` -- fixtures for the independent API tests of the identity wave.

Two isolation modes, chosen per test by what the test has to prove:

* **the suite's rolled-back transaction** (``session``/``session_factory`` from
  ``tests/integration/api/conftest.py``) for every sequential claim -- fast, and nothing
  survives the test;
* **a fresh database migrated to head** (``migrated_engine``, re-exported here from the
  ``db`` suite exactly as ``tests/integration/access/conftest.py`` re-exports it) for the
  races. A race needs two transactions that really commit and really wait on each other's
  locks, which one rolled-back connection cannot provide. The database is dropped when the
  test ends.
"""

from __future__ import annotations

from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    empty_database,
    maintenance_engine,
    migrated_database,
    migrated_engine,
)
