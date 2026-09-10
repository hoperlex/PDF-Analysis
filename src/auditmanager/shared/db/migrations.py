"""Reading migration state. This module never *applies* a migration.

Applying is ``make migrate``, which runs Alembic directly. Keeping the two apart
is what makes "the second migration is a no-op" a checkable claim: a probe that
could upgrade would always find itself at head.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from auditmanager.shared.db.errors import DatabaseUnavailableError, MigrationStateError

#: Repository-relative location of the Alembic configuration. The reserved path in
#: ``docs/program/FOUNDATION_LOCK.json`` is ``db/migrations/alembic.ini``.
ALEMBIC_INI_RELATIVE: Final[str] = "db/migrations/alembic.ini"


def repository_root() -> Path:
    """The repository root, derived from this file's location.

    ``src/auditmanager/shared/db/migrations.py`` is four levels below ``src/``,
    which is one level below the root.
    """
    return Path(__file__).resolve().parents[4]


def alembic_config_path() -> Path:
    """Absolute path to ``db/migrations/alembic.ini``."""
    return repository_root() / ALEMBIC_INI_RELATIVE


def alembic_config() -> Config:
    """Load the Alembic configuration from its reserved path.

    ``script_location`` in the ini uses ``%(here)s``, so the script directory
    resolves from the ini's own location and the working directory does not matter.
    """
    path = alembic_config_path()
    if not path.is_file():
        raise MigrationStateError(f"Alembic configuration not found at {path}")
    return Config(str(path))


def script_directory() -> ScriptDirectory:
    """The Alembic script directory for this repository."""
    return ScriptDirectory.from_config(alembic_config())


def head_revision() -> str:
    """The single head revision declared by the migration scripts.

    A branched history is a defect for this repository: the plan gives the P02
    schema exactly one head, so more than one head is refused here rather than
    silently upgraded to one of them.
    """
    scripts = script_directory()
    heads = scripts.get_heads()
    if len(heads) != 1:
        raise MigrationStateError(
            f"expected exactly one migration head, found {len(heads)}: {sorted(heads)}. "
            "The P02 schema is delivered as one head; a branch must be merged before "
            "any database is migrated."
        )
    return heads[0]


def revision_walk() -> list[str]:
    """Every revision from base to head, in application order."""
    scripts = script_directory()
    return [revision.revision for revision in reversed(list(scripts.walk_revisions()))]


def current_revision(engine: Engine) -> str | None:
    """The revision stamped in the database, or ``None`` for an unmigrated one."""
    try:
        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError(
            f"could not read the migration state: {exc.__class__.__name__}: {exc}"
        ) from exc


@dataclass(frozen=True, slots=True)
class MigrationState:
    """What the code expects versus what the database carries."""

    expected_head: str
    current: str | None

    @property
    def is_at_head(self) -> bool:
        return self.current == self.expected_head

    @property
    def is_unmigrated(self) -> bool:
        return self.current is None

    def describe(self) -> str:
        if self.is_unmigrated:
            return f"unmigrated (expected head {self.expected_head})"
        if self.is_at_head:
            return f"at head {self.expected_head}"
        return f"at {self.current}, expected head {self.expected_head}"


def read_state(engine: Engine) -> MigrationState:
    """Read the migration state without changing it."""
    return MigrationState(expected_head=head_revision(), current=current_revision(engine))


def require_head(engine: Engine) -> MigrationState:
    """Fail closed unless the database is exactly at the expected head."""
    state = read_state(engine)
    if not state.is_at_head:
        raise MigrationStateError(
            f"database is {state.describe()}. Run `make migrate`. This process does "
            "not upgrade a database on connect."
        )
    return state
