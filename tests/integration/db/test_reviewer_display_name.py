"""`R-37` / ``0009_reviewer_display_name``: the column, its CHECK, its round trip and its rollback.

Asserted against a live database rather than against the revision's source, for the reason
``test_app_user_migration.py`` gives: grepping a revision for a constraint name also matches
the comment that explains it, so a source test proves a docstring exists. ``pg_constraint``
describes what was actually created.

**The rollback is the half that matters most here**, because the brief's own policy is that
the migration must roll back and because this revision is deliberately *not* one of the two
that refuse to. ``0004`` and ``0006`` refuse a downgrade that would destroy data recoverable
from nowhere else; this one loses a **label**, every account keeps working on the login
fallback, and the honest thing is to proceed loudly rather than to stop.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.access.models import MAX_DISPLAY_NAME_LENGTH
from auditmanager.access.repository import UserRepository
from tests.integration.db.conftest import (  # type: ignore[import-not-found]
    MIGRATE_ARGV,
    run_foundation_command,
)

#: Down to the revision *before* this one, so the column and its CHECK both go.
DOWNGRADE_ARGV = [
    ".venv/bin/python",
    "-m",
    "alembic",
    "--config",
    "db/migrations/alembic.ini",
    "downgrade",
    "0008_sign_in_throttle",
]

#: The bound, written out rather than imported from the value under test.
#: ``OPERATING_CONSTRAINTS.md`` §12: a test that builds its expectation out of the constant
#: it is checking moves both sides of the comparison together and can never fail.
#:
#: It is 128 because that is ``DecisionEvent.author_label``'s ``maxLength`` in the frozen
#: contract, and a column that admitted a longer name would let an account be given one
#: that cannot be recorded against a decision.
EXPECTED_MAX = 128


def _constraint(session: Session, name: str) -> str | None:
    return session.execute(
        text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n"),
        {"n": name},
    ).scalar()


def _column_type(session: Session, table: str, column: str) -> str | None:
    return session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).scalar()


class TestTheColumn:
    def test_it_exists_and_is_nullable(self, migrated_engine: Engine) -> None:
        """Nullable is the decision, not an oversight. See the revision's docstring.

        A ``NOT NULL`` backfilled from ``login`` would destroy, in data and irreversibly,
        the difference between *has not chosen a name* and *chose their own login*. The
        NULL is what makes the fallback a query an operator can run rather than a piece of
        folklore, which is ``0006``'s own argument for ``is_default_credential``.
        """
        with Session(migrated_engine) as session:
            nullable = session.execute(
                text(
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_name = 'app_user' AND column_name = 'display_name'"
                )
            ).scalar()
        assert nullable == "YES", (
            "app_user.display_name is NOT NULL. A backfilled column cannot tell an "
            "account that chose no name from one that chose its login, and the fallback "
            "stops being visible the moment it is applied."
        )
        with Session(migrated_engine) as session:
            assert _column_type(session, "app_user", "display_name") == "text"

    def test_the_seeded_account_has_none(self, migrated_engine: Engine) -> None:
        """A clean install names nobody, and that is not a broken state.

        ``0006`` seeds ``admin`` and this revision does not name it, because inventing a
        name is the one thing `R-37` rules out by name. The account records decisions under
        its login until an operator says otherwise.
        """
        with Session(migrated_engine) as session:
            value = session.execute(
                text("SELECT display_name FROM app_user WHERE login = 'admin'")
            ).scalar()
        assert value is None

    def test_it_is_not_unique(self, migrated_engine: Engine) -> None:
        """Two reviewers may genuinely be called the same thing.

        Identity is ``user_uid`` and the addressable name is ``login``; both are already
        unique. A UNIQUE here would be this table asserting a fact about people that is not
        true.
        """
        with Session(migrated_engine) as session:
            constraints = session.execute(
                text(
                    "SELECT conname FROM pg_constraint c "
                    "JOIN pg_class t ON t.oid = c.conrelid "
                    "WHERE t.relname = 'app_user' AND c.contype IN ('u', 'p')"
                )
            ).scalars().all()
        assert "uq_app_user_display_name" not in constraints
        with Session(migrated_engine) as session:
            indexes = session.execute(
                text(
                    "SELECT indexdef FROM pg_indexes WHERE tablename = 'app_user'"
                )
            ).scalars().all()
        assert not any(
            "UNIQUE" in definition and "display_name" in definition
            for definition in indexes
        ), indexes


class TestTheCheckRefusesWhatTheBoundaryWouldRefuse:
    """Raw SQL must not be able to write a value ``normalize_display_name`` refuses.

    The same rule ``0006`` applies to the login, and the same reason: a boundary is a
    promise about one code path, and a CHECK is a promise about the table.
    """

    def test_the_constraint_exists_and_names_the_contract_bound(
        self, migrated_engine: Engine
    ) -> None:
        with Session(migrated_engine) as session:
            definition = _constraint(session, "ck_app_user_display_name")
        assert definition is not None, "app_user.display_name has no CHECK"
        assert str(EXPECTED_MAX) in definition, definition
        assert MAX_DISPLAY_NAME_LENGTH == EXPECTED_MAX, (
            "the value type and the database disagree about how long a display name may "
            "be, and the number they must agree on is author_label's maxLength"
        )

    @pytest.mark.parametrize(
        ("label", "value"),
        [
            ("empty", ""),
            ("blank", "   "),
            ("leading whitespace", " Анна"),
            ("trailing whitespace", "Анна "),
            ("one character too long", "x" * (EXPECTED_MAX + 1)),
        ],
    )
    def test_a_value_the_boundary_would_refuse_is_refused_by_the_table(
        self, migrated_engine: Engine, label: str, value: str
    ) -> None:
        with Session(migrated_engine) as session:
            with pytest.raises(DBAPIError):
                session.execute(
                    text("UPDATE app_user SET display_name = :v WHERE login = 'admin'"),
                    {"v": value},
                )
            session.rollback()

    @pytest.mark.parametrize(
        ("label", "value"),
        [
            ("a Russian name", "Анна Петрова"),
            ("exactly the bound", "x" * EXPECTED_MAX),
            ("one character", "А"),
            ("cleared again", None),
        ],
    )
    def test_a_value_the_boundary_accepts_is_accepted(
        self, migrated_engine: Engine, label: str, value: str | None
    ) -> None:
        with Session(migrated_engine) as session:
            session.execute(
                text("UPDATE app_user SET display_name = :v WHERE login = 'admin'"),
                {"v": value},
            )
            stored = session.execute(
                text("SELECT display_name FROM app_user WHERE login = 'admin'")
            ).scalar()
            assert stored == value
            session.rollback()


class TestTheRepositoryRoundTrip:
    """What the operator command writes, and what ``display_label`` then answers."""

    def test_naming_an_account_changes_its_label_and_nothing_else(
        self, migrated_engine: Engine
    ) -> None:
        repository = UserRepository()
        with Session(migrated_engine) as session:
            before = repository.find_by_login(session, "admin")
            assert before is not None
            assert before.display_name is None
            assert before.display_label == "admin", (
                "an account with no display name must fall back to its login"
            )

            named = repository.set_display_name(
                session, login="admin", display_name="  Анна Петрова  "
            )
            assert named is not None
            assert named.display_name == "Анна Петрова", "it is stripped, not folded"
            assert named.display_label == "Анна Петрова"
            # A rename is not a revocation and not a password change.
            assert named.token_epoch == before.token_epoch
            assert named.password_updated_at == before.password_updated_at
            assert named.is_default_credential == before.is_default_credential
            assert named.sign_in_blocked_until == before.sign_in_blocked_until
            session.rollback()

    def test_clearing_returns_the_account_to_the_fallback(
        self, migrated_engine: Engine
    ) -> None:
        repository = UserRepository()
        with Session(migrated_engine) as session:
            repository.set_display_name(session, login="admin", display_name="Кто-то")
            cleared = repository.set_display_name(
                session, login="admin", display_name=None
            )
            assert cleared is not None
            assert cleared.display_name is None
            assert cleared.display_label == "admin"
            session.rollback()

    def test_an_account_nobody_holds_is_none_and_not_a_raise(
        self, migrated_engine: Engine
    ) -> None:
        with Session(migrated_engine) as session:
            assert (
                UserRepository().set_display_name(
                    session, login="nobody-at-all", display_name="X"
                )
                is None
            )
            session.rollback()

    def test_the_unnamed_query_is_what_makes_the_fallback_visible(
        self, migrated_engine: Engine
    ) -> None:
        """The whole reason the column is nullable, asserted as behaviour.

        Without this query an operator cannot tell which accounts are on the fallback, and
        a fallback nobody can see is the silent fallback ``AGENTS.md`` §4 forbids.
        """
        repository = UserRepository()
        with Session(migrated_engine) as session:
            unnamed = {u.login for u in repository.accounts_without_a_display_name(session)}
            assert "admin" in unnamed

            repository.set_display_name(session, login="admin", display_name="Анна")
            after = {u.login for u in repository.accounts_without_a_display_name(session)}
            assert "admin" not in after
            session.rollback()


class TestTheRollback:
    """`R-11` cost a whole wave. This revision has to come back off on its own."""

    def test_it_downgrades_and_upgrades_again(self, migrated_database) -> None:
        url = migrated_database.url.render_as_string(hide_password=False)

        down = run_foundation_command(DOWNGRADE_ARGV, url)
        assert down.returncode == 0, down.describe()

        engine_settings = migrated_database
        from auditmanager.shared.db.engine import create_database_engine

        engine = create_database_engine(engine_settings)
        try:
            with Session(engine) as session:
                assert _column_type(session, "app_user", "display_name") is None, (
                    "the column survived its own downgrade"
                )
                assert _constraint(session, "ck_app_user_display_name") is None
                # The rest of the table is untouched: a downgrade that took the account
                # with it would be a different and much worse thing.
                assert session.execute(
                    text("SELECT count(*) FROM app_user WHERE login = 'admin'")
                ).scalar() == 1

            up = run_foundation_command(MIGRATE_ARGV, url)
            assert up.returncode == 0, up.describe()
            with Session(engine) as session:
                assert _column_type(session, "app_user", "display_name") == "text"
                assert _constraint(session, "ck_app_user_display_name") is not None
        finally:
            engine.dispose()

    def test_the_downgrade_names_the_accounts_whose_names_it_destroys(
        self, migrated_database
    ) -> None:
        """Loud, because the names exist nowhere else.

        Nobody can be asked to retype what they were not told was gone. The revision does
        not *refuse* -- what it loses is a label and every account keeps working on the
        login fallback -- so the whole of the protection is that it says so.
        """
        url = migrated_database.url.render_as_string(hide_password=False)
        from auditmanager.shared.db.engine import create_database_engine

        engine = create_database_engine(migrated_database)
        try:
            with Session(engine) as session:
                UserRepository().set_display_name(
                    session, login="admin", display_name="Анна Петрова"
                )
                session.commit()
        finally:
            engine.dispose()

        down = run_foundation_command(DOWNGRADE_ARGV, url)
        assert down.returncode == 0, down.describe()
        printed = down.describe()
        assert "admin" in printed, printed
        assert "Анна Петрова" in printed, printed
