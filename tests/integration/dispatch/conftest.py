"""Database fixtures for the ``dispatch`` suite: the ``db`` suite's, re-exported.

Each test gets its own clone of a session-local database migrated to head by the literal
command (``tests/integration/db/conftest.py``), dropped afterwards -- the assignment tables
refuse DELETE, so a shared database could not be cleaned. The people and the scope every
test needs are built through the ``access`` and ``documents`` boundaries, never by INSERT.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from auditmanager.access.public import AccountRepository, UserRepository
from auditmanager.documents.public import DocumentRepository
from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    empty_database,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
)

PASSWORD = "a-long-enough-password"  # noqa: S105 - a test literal

users = UserRepository()
accounts = AccountRepository()
documents = DocumentRepository()


@dataclass(frozen=True, slots=True)
class Cast:
    """Who is who, and what they work on. Every value is an opaque identity string."""

    admin: str  # admin only (the seeded account holds both roles; this one does not)
    expert: str  # expert only
    other_expert: str  # expert only
    admin_expert: str  # both roles
    nobody: str  # an active account with no role
    project: str
    document: str
    other_project: str
    other_document: str  # a document of other_project


def _person(session: Session, email: str, roles: tuple[str, ...]) -> str:
    uid = str(users.create_user(session, email, PASSWORD).user_uid)
    accounts.complete_profile(
        session, user_uid=uid, email=None, last_name="Петрова", first_name="Анна"
    )
    for role in roles:
        accounts.grant_role(session, user_uid=uid, role=role, granted_by=None)
    return uid


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    """A session on the fresh database. The test commits what it means to keep."""
    with Session(migrated_engine) as opened:
        yield opened


@pytest.fixture
def cast(session: Session) -> Cast:
    project = documents.create_project(session, "Школа на 550 мест")
    other_project = documents.create_project(session, "Детский сад")
    built = Cast(
        admin=_person(session, "admin.only@example.com", ("admin",)),
        expert=_person(session, "anna@example.com", ("expert",)),
        other_expert=_person(session, "boris@example.com", ("expert",)),
        admin_expert=_person(session, "vera@example.com", ("admin", "expert")),
        nobody=_person(session, "gleb@example.com", ()),
        project=str(project.project_uid),
        document=str(documents.create_document(session, project.project_uid, "КЖ-1")),
        other_project=str(other_project.project_uid),
        other_document=str(documents.create_document(session, other_project.project_uid, "АР-1")),
    )
    session.commit()
    return built
