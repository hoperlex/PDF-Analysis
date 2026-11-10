"""`UI-B-12`: ``0056_optimisation_decisions`` widens the verdict of a proposal decision, and refuses to go back over history.

On a clone of the migrated schema, against real PostgreSQL:

* ``revoke`` is a stored verdict, and the vocabulary stays closed: ``pending`` is not one (the CHECK keeps its name);
* the downgrade REFUSES while a withdrawal exists -- the test proves the guard can fail by writing one -- and leaves the head
  where it was;
* with no withdrawal left the downgrade restores the three-verdict CHECK (a ``revoke`` is refused again), and the revision
  upgrades once more.

The rows reference a proposal, an account and a command that do not exist: ``session_replication_role = replica`` switches
off the foreign keys and the immutability trigger for the statements that plant and remove them, as a superuser (the lane's
database user is one). The CHECK is not a trigger and stays in force.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine

HEAD = "0062_hosts_stage_models"  # the head the fixture migrates to; 0056 is six steps below it
PREVIOUS = "0055_work_schedule"
CHECK = "ck_optimisation_proposal_decision_verdict"

PROPOSAL = "opr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
COMMAND = "cmd_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


@contextmanager
def _planting(engine: Engine) -> Iterator[Connection]:
    """One transaction in which the foreign keys and the immutability trigger are off."""
    with engine.begin() as connection:
        assert connection.execute(text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")).scalar_one(), (
            "this test plants rows that reference nothing; it needs the superuser of the lane's database"
        )
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        yield connection


def _insert(connection: Connection, verdict: str, *, decision: str = "opd_01ARZ3NDEKTSV4RRFFQ69G5FAV") -> None:
    connection.execute(
        text(
            "INSERT INTO optimisation_proposal_decision (proposal_decision_id, optimisation_proposal_id, seq, verdict, "
            "comment, actor_user_uid, command_id) VALUES (:id, :proposal, 1, :verdict, :comment, :actor, :command)"
        ),
        {
            "id": decision, "proposal": PROPOSAL, "verdict": verdict, "actor": ACTOR, "command": COMMAND,
            "comment": "уточнить" if verdict == "revise" else None,  # ``revise`` carries one, by its own CHECK
        },
    )


def _head(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one())


def _refused_by_the_check(engine: Engine, verdict: str) -> bool:
    try:
        with _planting(engine) as connection:
            _insert(connection, verdict)
    except DBAPIError as error:
        assert CHECK in str(error.orig), error
        return True
    return False


@pytest.fixture
def at_head(migrated_database: Any) -> Iterator[tuple[Engine, str]]:
    engine = create_database_engine(migrated_database)
    try:
        yield engine, migrated_database.url.render_as_string(hide_password=False)
    finally:
        engine.dispose()


def test_a_withdrawal_is_a_stored_verdict_and_the_vocabulary_stays_closed(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    assert _head(engine) == HEAD
    for verdict in ("accept", "reject", "revise", "revoke"):
        assert not _refused_by_the_check(engine, verdict), verdict
        with _planting(engine) as connection:
            connection.execute(text("DELETE FROM optimisation_proposal_decision"))
    for verdict in ("pending", "revoked", ""):
        assert _refused_by_the_check(engine, verdict), verdict


def test_the_downgrade_refuses_over_a_withdrawal_and_restores_the_old_vocabulary_without_one(
    at_head: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_head
    with _planting(engine) as connection:
        _insert(connection, "revoke")

    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0, refused.describe()
    assert "withdrawals" in (refused.stdout + refused.stderr), refused.describe()
    assert _head(engine) == HEAD  # the refusal rolled the whole downgrade back, with the withdrawal still in it
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM optimisation_proposal_decision WHERE verdict = 'revoke'")
        ).scalar_one() == 1

    with _planting(engine) as connection:
        connection.execute(text("DELETE FROM optimisation_proposal_decision"))
    downgraded = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert downgraded.returncode == 0, downgraded.describe()
    assert _head(engine) == PREVIOUS
    assert _refused_by_the_check(engine, "revoke")  # the three-verdict CHECK is back
    assert not _refused_by_the_check(engine, "accept")
    with _planting(engine) as connection:
        connection.execute(text("DELETE FROM optimisation_proposal_decision"))

    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()
    assert _head(engine) == HEAD
    assert not _refused_by_the_check(engine, "revoke")
