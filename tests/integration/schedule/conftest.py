"""Database fixtures for the ``schedule`` suite: the ``dispatch`` suite's people, scope and fresh database.

«График работ» reads the experts and places «Диспетчер»'s assignments, so its cast is the dispatcher's: an administrator,
two experts, an administrator who is also an expert, an account with no role, and two projects with a document each.
"""

from __future__ import annotations

from tests.integration.dispatch.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    Cast,
    cast,
    configured_settings,
    empty_database,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
    session,
)
