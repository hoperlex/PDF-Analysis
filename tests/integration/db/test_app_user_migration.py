"""``0006_app_user``: the table it creates, the account it seeds, the drop it refuses.

Asserted against the live database rather than against the migration source. Grepping
the revision for a constraint name also matches the comment explaining it, so a source
test proves a docstring exists; ``pg_constraint`` describes what was actually created.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.access.models import USER_UID_PATTERN
from auditmanager.access.passwords import ALGORITHM, StoredPassword, verify_password
from auditmanager.shared.db.config import DatabaseSettings
from tests.integration.db.conftest import (  # type: ignore[import-not-found]
    MIGRATE_ARGV,
    run_foundation_command,
)

DOWNGRADE_ARGV = [
    ".venv/bin/python",
    "-m",
    "alembic",
    "--config",
    "db/migrations/alembic.ini",
    "downgrade",
    "0005_truncated_call_status",
]

#: The account the revision seeds, and the password it seeds it with. Written out here
#: rather than imported from the migration: a test that imports the value it is checking
#: passes whatever the migration decides to write, which is the one thing it must not do.
SEED_LOGIN = "admin"
SEED_PASSWORD = "password"  # noqa: S105 - the documented default this test exists to pin


def _constraint(session: Session, name: str) -> str | None:
    return session.execute(
        text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n"),
        {"n": name},
    ).scalar()


class TestTheTableIsShapedTheWayTheRevisionClaims:
    def test_the_identity_column_carries_the_contract_shaped_format_check(
        self, migrated_engine: Engine
    ) -> None:
        """``user_uid`` is excluded from the schema-shape suite's identity sweep, because
        ``usr`` is not a prefix in the frozen PC-01 catalog. The CHECK it would have
        asserted is asserted here instead, so nothing is lost by the exclusion."""
        with Session(migrated_engine) as session:
            definition = _constraint(session, "ck_app_user_user_uid_format")
        assert definition is not None, "app_user.user_uid has no format CHECK"
        assert "usr_[0-9A-HJKMNP-TV-Z]{26}" in definition
        assert USER_UID_PATTERN == r"^usr_[0-9A-HJKMNP-TV-Z]{26}$", (
            "the value type and the database disagree about what a user identity is"
        )

    def test_a_malformed_identity_is_refused_by_the_database(
        self, migrated_engine: Engine
    ) -> None:
        with Session(migrated_engine) as session, pytest.raises(DBAPIError):
            session.execute(
                text(
                    "INSERT INTO app_user (user_uid, login, password_algorithm, "
                    "password_iterations, password_salt, password_hash) VALUES "
                    "('42', 'someone', 'pbkdf2_sha256', 600000, :salt, :digest)"
                ),
                {"salt": "0" * 32, "digest": "0" * 64},
            )
            session.flush()

    def test_a_login_that_is_not_folded_is_refused(self, migrated_engine: Engine) -> None:
        """Without this CHECK, ``Admin`` inserts beside ``admin`` through raw SQL and the
        UNIQUE constraint stops meaning "one account per name"."""
        with Session(migrated_engine) as session, pytest.raises(DBAPIError):
            session.execute(
                text(
                    "INSERT INTO app_user (user_uid, login, password_algorithm, "
                    "password_iterations, password_salt, password_hash) VALUES "
                    "('usr_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'Admin', 'pbkdf2_sha256', "
                    "600000, :salt, :digest)"
                ),
                {"salt": "0" * 32, "digest": "0" * 64},
            )
            session.flush()

    def test_a_derisory_iteration_count_is_refused(self, migrated_engine: Engine) -> None:
        """A row written with one iteration verifies perfectly and protects nothing. The
        CHECK is the only thing that makes the cost an invariant rather than a habit."""
        with Session(migrated_engine) as session, pytest.raises(DBAPIError):
            session.execute(
                text(
                    "INSERT INTO app_user (user_uid, login, password_algorithm, "
                    "password_iterations, password_salt, password_hash) VALUES "
                    "('usr_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'cheap', 'pbkdf2_sha256', 1, "
                    ":salt, :digest)"
                ),
                {"salt": "0" * 32, "digest": "0" * 64},
            )
            session.flush()

    def test_an_unknown_algorithm_is_refused(self, migrated_engine: Engine) -> None:
        with Session(migrated_engine) as session, pytest.raises(DBAPIError):
            session.execute(
                text(
                    "INSERT INTO app_user (user_uid, login, password_algorithm, "
                    "password_iterations, password_salt, password_hash) VALUES "
                    "('usr_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'md5fan', 'md5', 600000, "
                    ":salt, :digest)"
                ),
                {"salt": "0" * 32, "digest": "0" * 64},
            )
            session.flush()

    def test_no_column_holds_a_plaintext_password(self, migrated_engine: Engine) -> None:
        """The shape claim that matters: whatever else this table stores, not that.

        Asserted as data rather than as a column-name rule -- a column called
        ``password_hash`` holding the plaintext would satisfy any naming convention.
        """
        with Session(migrated_engine) as session:
            columns = [
                row[0]
                for row in session.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = 'app_user'"
                    )
                )
            ]
            for column in columns:
                values = [
                    str(row[0])
                    for row in session.execute(text(f'SELECT "{column}" FROM app_user'))  # noqa: S608
                ]
                assert SEED_PASSWORD not in values, (
                    f"app_user.{column} holds the plaintext seeded password"
                )


class TestTheSeededAccount:
    def test_exactly_one_account_exists_and_it_is_the_seeded_one(
        self, migrated_engine: Engine
    ) -> None:
        with Session(migrated_engine) as session:
            rows = session.execute(
                text("SELECT login, is_default_credential FROM app_user")
            ).all()
        assert [(row[0], row[1]) for row in rows] == [(SEED_LOGIN, True)]

    def test_the_seeded_digest_verifies_against_the_documented_password(
        self, migrated_engine: Engine
    ) -> None:
        """The claim the whole seed rests on, and the one that catches a drift between
        what the migration wrote and what the application verifies with."""
        with Session(migrated_engine) as session:
            algorithm, iterations, salt, digest = session.execute(
                text(
                    "SELECT password_algorithm, password_iterations, password_salt, "
                    "password_hash FROM app_user WHERE login = :login"
                ),
                {"login": SEED_LOGIN},
            ).one()
        stored = StoredPassword(
            algorithm=algorithm, iterations=int(iterations), salt=salt, digest=digest
        )
        assert stored.algorithm == ALGORITHM
        assert verify_password(stored, SEED_PASSWORD) is True
        assert verify_password(stored, SEED_PASSWORD + " ") is False

    def test_the_salt_is_not_a_constant_of_the_revision(
        self, empty_database: DatabaseSettings, migrated_engine: Engine, maintenance_engine
    ) -> None:
        """Two installations must not share the seeded digest.

        A fixed salt in the migration would make one leaked digest the digest of every
        deployment's admin account, which is exactly the property a salt exists to deny.
        """
        import secrets

        from auditmanager.shared.db.engine import create_database_engine

        name = f"a1_seed_{secrets.token_hex(6)}"
        with maintenance_engine.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        second = DatabaseSettings(url=empty_database.url.set(database=name))
        url = second.url.render_as_string(hide_password=False)
        try:
            result = run_foundation_command(MIGRATE_ARGV, url)
            assert "0006_app_user" in (result.stdout + result.stderr), result.describe()
            engine = create_database_engine(second)
            try:
                with Session(engine) as session:
                    other = session.execute(
                        text("SELECT password_salt, password_hash, user_uid FROM app_user")
                    ).one()
            finally:
                engine.dispose()
            with Session(migrated_engine) as session:
                mine = session.execute(
                    text("SELECT password_salt, password_hash, user_uid FROM app_user")
                ).one()
            assert other[0] != mine[0], "the seeded salt is the same in two databases"
            assert other[1] != mine[1], "the seeded digest is the same in two databases"
            assert other[2] != mine[2], "the seeded identity is the same in two databases"
        finally:
            with maintenance_engine.connect() as connection:
                connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = :name AND pid <> pg_backend_pid()"
                    ),
                    {"name": name},
                )
                connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))

    def test_the_deployment_log_names_the_default_password(
        self, empty_database_url: str, foundation_command, migrate_argv: list[str]
    ) -> None:
        """The visibility requirement, asserted on the literal command's own output.

        An operator who runs the migration and reads nothing else must still learn that
        this installation has a known password in it.
        """
        result = foundation_command(migrate_argv, empty_database_url)
        output = result.stdout + result.stderr
        assert "0006_app_user" in output, result.describe()
        assert "DEFAULT PASSWORD" in output, result.describe()
        assert SEED_LOGIN in output, result.describe()
        assert "is_default_credential" in output, result.describe()


class TestTheDowngradeRefusesToDeleteTheOnlyCopy:
    def test_it_drops_the_table_when_only_the_untouched_seed_is_there(
        self, migrated_database: DatabaseSettings, migrated_engine: Engine
    ) -> None:
        url = migrated_database.url.render_as_string(hide_password=False)
        result = run_foundation_command(DOWNGRADE_ARGV, url)
        assert "Running downgrade 0006_app_user" in (result.stdout + result.stderr), (
            result.describe()
        )
        with Session(migrated_engine) as session:
            present = session.execute(
                text("SELECT count(*) FROM pg_tables WHERE tablename = 'app_user'")
            ).scalar_one()
        assert present == 0, "the downgrade left the table behind"

    def test_it_refuses_when_a_real_account_would_be_lost(
        self, migrated_database: DatabaseSettings, migrated_engine: Engine
    ) -> None:
        """A password digest exists in this table and nowhere else. Dropping it is not a
        reversible schema change; it is deletion of the only copy."""
        with Session(migrated_engine) as session:
            session.execute(
                text(
                    "INSERT INTO app_user (user_uid, login, password_algorithm, "
                    "password_iterations, password_salt, password_hash) VALUES "
                    "('usr_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'auditor', 'pbkdf2_sha256', "
                    "600000, :salt, :digest)"
                ),
                {"salt": "0" * 32, "digest": "0" * 64},
            )
            session.commit()

        url = migrated_database.url.render_as_string(hide_password=False)
        result = run_foundation_command(DOWNGRADE_ARGV, url)
        combined = result.stdout + result.stderr
        assert "refusing to downgrade 0006_app_user" in combined, result.describe()

        with Session(migrated_engine) as session:
            survivors = session.execute(
                text("SELECT login FROM app_user ORDER BY login")
            ).scalars().all()
        assert survivors == ["admin", "auditor"], "the refusal still lost a row"
