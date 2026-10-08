"""``0015_accounts_roles_registration``: shape, register, lifecycle guard, upgrade paths.

`W49-ACCESS-01a`. Everything here is asserted against a live database built by the literal
migration command (``conftest.MIGRATE_ARGV``), never against the migration's source text:
grepping a revision for a constraint name also matches the comment explaining it.

The required cases of ``docs/program/tasks/W49-ACCESS-01.md``:

* a fresh upgrade to ``0015`` and a downgrade on an empty tree -- ``TestFreshUpgrade`` and
  ``TestTheDowngrade``;
* an upgrade from a ``0014`` database holding the seeded ``admin`` with a changed password,
  and from one holding a legacy non-e-mail login -- ``TestUpgradeFromA0014Database``;
* the guard trigger refusing a second decision, a password-column write after the
  decision and a manual ``created_user_uid`` UPDATE -- ``TestTheRegistrationGuard``;
* the partial unique indexes, each proven by two rows -- ``TestThePartialUniqueIndexes``;
* the reference register equal to the schema's foreign keys to ``app_user`` --
  ``test_the_reference_register_equals_the_schema_foreign_keys_to_app_user``.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.access import models
from auditmanager.access.passwords import StoredPassword, hash_password, verify_password
from auditmanager.access.references import ACCOUNT_REFERENCES
from auditmanager.access.repository import UserRepository
from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.migrations import head_revision
from tests.integration.db.conftest import (  # type: ignore[import-not-found]
    MIGRATE_ARGV,
    REPOSITORY_ROOT,
    clear_the_role_backfill,
    run_foundation_command,
)

REVISION = "0015_accounts_roles_registration"
PREVIOUS = "0014_durable_analysis_effects"
MIGRATION_FILE = (
    REPOSITORY_ROOT
    / "db"
    / "migrations"
    / "versions"
    / "20261005_0015_accounts_roles_registration.py"
)

#: Written out, not imported: a test that imports the value it checks passes whatever the
#: code decides.
SEED_LOGIN = "admin"
SEED_PASSWORD = "password"  # noqa: S105 - the published 0006 default
CHANGED_PASSWORD = "a-changed-owner-password"  # noqa: S105 - a test literal

SALT = "0" * 32
DIGEST = "0" * 64

USR_A = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAA"
USR_B = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAB"
REG_A = "reg_01ARZ3NDEKTSV4RRFFQ69G5FAA"
REG_B = "reg_01ARZ3NDEKTSV4RRFFQ69G5FAB"


def _argv(*tail: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", *tail]


def _url(settings: DatabaseSettings) -> str:
    return settings.url.render_as_string(hide_password=False)


def _sqlstate(error: DBAPIError) -> str:
    return str(getattr(error.orig, "sqlstate", "") or "")


def _refused(engine: Engine, statement: str, params: dict | None = None) -> str:
    """Run ``statement`` in its own transaction; return the SQLSTATE it was refused with."""
    with pytest.raises(DBAPIError) as caught, engine.begin() as connection:
        connection.execute(text(statement), params or {})
    return _sqlstate(caught.value)


def _seed_uid(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT user_uid FROM app_user WHERE login = :login"), {"login": SEED_LOGIN}
        ).scalar_one()


def _insert_user(
    connection, user_uid: str, login: str, *, completed: bool = False, archived_by=None
) -> None:
    connection.execute(
        text(
            "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, "
            "password_salt, password_hash, last_name, first_name, profile_completed_at, "
            "archived_at, archived_by) VALUES (:uid, :login, 'pbkdf2_sha256', 600000, "
            ":salt, :digest, :last, :first, :completed, :archived_at, :archived_by)"
        ),
        {
            "uid": user_uid,
            "login": login,
            "salt": SALT,
            "digest": DIGEST,
            "last": "Петрова" if completed else None,
            "first": "Анна" if completed else None,
            "completed": "now" if completed else None,
            "archived_at": "now" if archived_by else None,
            "archived_by": archived_by,
        },
    )


def _insert_request(connection, request_id: str, login: str) -> None:
    connection.execute(
        text(
            "INSERT INTO registration_request (request_id, login, last_name, first_name, "
            "password_algorithm, password_iterations, password_salt, password_hash) "
            "VALUES (:rid, :login, 'Петрова', 'Анна', 'pbkdf2_sha256', 600000, :salt, :digest)"
        ),
        {"rid": request_id, "login": login, "salt": SALT, "digest": DIGEST},
    )


_REJECT = (
    "UPDATE registration_request SET status = 'rejected', decided_at = now(), "
    "decided_by = :by, rejection_reason = 'not this time', password_algorithm = NULL, "
    "password_iterations = NULL, password_salt = NULL, password_hash = NULL "
    "WHERE request_id = :rid"
)
_APPROVE = (
    "UPDATE registration_request SET status = 'approved', decided_at = now(), "
    "decided_by = :by, created_user_uid = :created, password_algorithm = NULL, "
    "password_iterations = NULL, password_salt = NULL, password_hash = NULL "
    "WHERE request_id = :rid"
)


def _migration_module():
    spec = importlib.util.spec_from_file_location("migration_0015_under_test", MIGRATION_FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def database_at_0014(
    empty_database: DatabaseSettings,
) -> Iterator[tuple[DatabaseSettings, Engine]]:
    """An empty database migrated to ``0014`` exactly, by the literal command."""
    result = run_foundation_command(_argv("upgrade", PREVIOUS), _url(empty_database))
    assert result.returncode == 0, result.describe()
    engine = create_database_engine(empty_database)
    try:
        yield empty_database, engine
    finally:
        engine.dispose()


# =======================================================================================
# The literals the migration restates are the boundary's.
# =======================================================================================


def test_the_migration_restates_the_boundary_patterns_exactly() -> None:
    migration = _migration_module()
    assert migration.revision == REVISION
    assert migration.down_revision == PREVIOUS
    assert migration.EMAIL_LOGIN_PATTERN == models.EMAIL_LOGIN_PATTERN
    assert migration.LEGACY_LOGIN_PATTERN == models.LOGIN_PATTERN
    assert migration.PERSON_NAME_PATTERN == models.PERSON_NAME_PATTERN
    assert migration.REGISTRATION_ID_PATTERN == models.REGISTRATION_ID_PATTERN
    assert migration.USER_UID_PATTERN == models.USER_UID_PATTERN
    assert migration.MAX_EMAIL_LENGTH == models.MAX_EMAIL_LENGTH
    assert migration.MAX_PERSON_NAME_LENGTH == models.MAX_PERSON_NAME_LENGTH
    assert set(migration.ROLES) == models.ROLES


def test_this_revision_precedes_the_release_head() -> None:
    assert head_revision() == "0016_release_notes"


# =======================================================================================
# A fresh upgrade.
# =======================================================================================


class TestFreshUpgrade:
    def test_the_backfill_gives_the_seed_both_roles_and_leaves_it_a_legacy_account(
        self, migrated_engine: Engine
    ) -> None:
        with migrated_engine.connect() as connection:
            roles = connection.execute(
                text(
                    "SELECT u.login, r.role, r.granted_by FROM app_user u "
                    "JOIN app_user_role r USING (user_uid) ORDER BY r.role"
                )
            ).all()
            profile = connection.execute(
                text(
                    "SELECT profile_completed_at, last_name, first_name, middle_name, "
                    "archived_at, archived_by FROM app_user"
                )
            ).one()
        assert [tuple(row) for row in roles] == [
            (SEED_LOGIN, "admin", None),
            (SEED_LOGIN, "expert", None),
        ]
        assert tuple(profile) == (None, None, None, None, None, None), (
            "every account that exists at upgrade is a legacy account until it completes "
            "its profile; no seed constant is hard-coded"
        )

    def test_the_deployment_log_names_who_holds_admin(
        self, empty_database: DatabaseSettings
    ) -> None:
        result = run_foundation_command(MIGRATE_ARGV, _url(empty_database))
        assert result.returncode == 0, result.describe()
        output = result.stdout + result.stderr
        assert "0015_accounts_roles_registration: 1 existing account(s)" in output
        assert "the account 'admin' also holds the role 'admin'" in output
        assert "python -m auditmanager.access.profile" in output

    def test_every_account_identity_column_carries_its_format_check(
        self, migrated_engine: Engine
    ) -> None:
        """``usr`` and ``reg`` are outside the contract catalog until the seal, so
        ``test_schema_shape.py`` cannot resolve these columns; they are asserted here."""
        expected = {
            ("app_user", "archived_by"): "usr_[0-9A-HJKMNP-TV-Z]{26}",
            ("app_user_role", "user_uid"): "usr_[0-9A-HJKMNP-TV-Z]{26}",
            ("app_user_role", "granted_by"): "usr_[0-9A-HJKMNP-TV-Z]{26}",
            ("registration_request", "request_id"): "reg_[0-9A-HJKMNP-TV-Z]{26}",
            ("registration_request", "decided_by"): "usr_[0-9A-HJKMNP-TV-Z]{26}",
            ("registration_request", "created_user_uid"): "usr_[0-9A-HJKMNP-TV-Z]{26}",
            ("expert_decision_event", "author_user_uid"): "usr_[0-9A-HJKMNP-TV-Z]{26}",
        }
        with migrated_engine.connect() as connection:
            definitions = connection.execute(
                text(
                    "SELECT t.relname, pg_get_constraintdef(c.oid) FROM pg_constraint c "
                    "JOIN pg_class t ON t.oid = c.conrelid WHERE c.contype = 'c'"
                )
            ).all()
        missing = [
            f"{table}.{column}"
            for (table, column), needle in expected.items()
            if not any(
                relname == table and column in definition and needle in definition
                for relname, definition in definitions
            )
        ]
        assert missing == []

    def test_the_new_columns_exist_with_their_nullability(self, migrated_engine: Engine) -> None:
        with migrated_engine.connect() as connection:
            rows = {
                (row[0], row[1]): row[2]
                for row in connection.execute(
                    text(
                        "SELECT table_name, column_name, is_nullable "
                        "FROM information_schema.columns WHERE table_schema = 'public' "
                        "AND table_name IN ('app_user', 'expert_decision_event')"
                    )
                )
            }
        for column in (
            "last_name",
            "first_name",
            "middle_name",
            "profile_completed_at",
            "archived_at",
            "archived_by",
        ):
            assert rows[("app_user", column)] == "YES", column
        assert rows[("expert_decision_event", "author_user_uid")] == "YES"


def test_the_reference_register_equals_the_schema_foreign_keys_to_app_user(
    migrated_engine: Engine,
) -> None:
    """`R-61`, `W49-PLAN.md` §3.1: the register in ``access`` is the database's truth.

    Every foreign key whose target is ``app_user`` is read from ``pg_constraint``, with
    its delete action, and compared with ``ACCOUNT_REFERENCES`` in both directions. A
    column that names an account without being registered -- or a register entry the
    schema does not back -- is red here, so a purge can never be allowed by the register
    and then refused (or worse, allowed) by the schema.
    """
    actions = {"r": "RESTRICT", "n": "SET NULL", "c": "CASCADE", "a": "NO ACTION", "d": "SET DEFAULT"}
    with migrated_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT src.relname, a.attname, c.confdeltype "
                "FROM pg_constraint c "
                "JOIN pg_class src ON src.oid = c.conrelid "
                "JOIN pg_class dst ON dst.oid = c.confrelid "
                "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey) "
                "WHERE c.contype = 'f' AND dst.relname = 'app_user'"
            )
        ).all()
    schema = {(table, column, actions[str(kind)]) for table, column, kind in rows}
    register = {(entry.table, entry.column, entry.on_delete) for entry in ACCOUNT_REFERENCES}
    assert len(register) == len(ACCOUNT_REFERENCES), "the register lists a column twice"
    assert schema == register, (
        f"schema-only: {sorted(schema - register)}; register-only: {sorted(register - schema)}"
    )


# =======================================================================================
# The login, the names, the archive pair.
# =======================================================================================


class TestTheAccountChecks:
    def test_an_email_login_is_accepted_complete_or_not(self, migrated_engine: Engine) -> None:
        with migrated_engine.begin() as connection:
            _insert_user(connection, USR_A, "anna@example.com", completed=True)
            _insert_user(connection, USR_B, "boris@example.com", completed=False)

    def test_a_legacy_login_is_accepted_only_while_the_profile_is_incomplete(
        self, migrated_engine: Engine
    ) -> None:
        with migrated_engine.begin() as connection:
            _insert_user(connection, USR_A, "clara.jones", completed=False)
        assert (
            _refused(
                migrated_engine,
                "UPDATE app_user SET last_name = 'Джонс', first_name = 'Клара', "
                "profile_completed_at = now() WHERE user_uid = :uid",
                {"uid": USR_A},
            )
            == "23514"
        ), "a complete profile kept a legacy login"

    @pytest.mark.parametrize(
        "login",
        ["Admin", "Anna@Example.com", " anna@example.com", "anna@example", "a" * 65 + "@x.ru",
         "anna@" + "b" * 250 + ".ru", "анна@пример.рф"],
    )
    def test_a_login_the_boundary_would_refuse_is_refused_by_the_table(
        self, migrated_engine: Engine, login: str
    ) -> None:
        state = _refused(
            migrated_engine,
            "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, "
            "password_salt, password_hash) VALUES (:uid, :login, 'pbkdf2_sha256', 600000, "
            ":salt, :digest)",
            {"uid": USR_A, "login": login, "salt": SALT, "digest": DIGEST},
        )
        assert state == "23514"

    def test_a_complete_profile_without_names_is_refused(self, migrated_engine: Engine) -> None:
        assert (
            _refused(
                migrated_engine,
                "UPDATE app_user SET login = 'owner@example.com', profile_completed_at = now() "
                "WHERE login = 'admin'",
            )
            == "23514"
        )

    @pytest.mark.parametrize(
        "statement",
        [
            "UPDATE app_user SET archived_at = now() WHERE login = 'admin'",
            "UPDATE app_user SET archived_by = user_uid, archived_at = now() "
            "WHERE login = 'admin'",
        ],
        ids=["archived-without-an-archiver", "archived-by-itself"],
    )
    def test_the_archive_pair_is_whole_and_never_self(
        self, migrated_engine: Engine, statement: str
    ) -> None:
        assert _refused(migrated_engine, statement) == "23514"

    def test_the_two_engines_agree_on_every_sample(self, migrated_engine: Engine) -> None:
        """The same pattern text, read by PostgreSQL and by Python, over the same samples.

        A pattern that one engine reads differently -- a range, an escape, an anchor --
        would let a value through one door that the other refuses.
        """
        emails = [
            "anna@example.com", "a.b+c@sub.example.org", "o'brien@example.ie",
            "x@y.z", "Anna@example.com", "anna@example", "anna@-x.com", "anna@x-.com",
            "an na@x.com", "anna@@x.com", "a" * 64 + "@x.ru", "a" * 65 + "@x.ru",
            "анна@x.ru", "anna@x.ru\n",
        ]
        names = [
            "Петрова", "Петрова-Водкина", "О'Нил", "д’Артаньян", "де ла Фуэнте",
            "Müller", "Smith", "Ёжиков", "a", "Петрова ", " Петрова", "Пет  рова",
            "-Петрова", "Петрова-", "Петров2", "日本", "Иван̆", "A'",
        ]
        with migrated_engine.connect() as connection:
            for value in emails:
                in_database = connection.execute(
                    text("SELECT :v ~ :p AND char_length(:v) <= 254"),
                    {"v": value, "p": models.EMAIL_LOGIN_PATTERN},
                ).scalar_one()
                assert bool(in_database) == models.is_email_login(value), value
            for value in names:
                in_database = connection.execute(
                    text("SELECT :v ~ :p"), {"v": value, "p": models.PERSON_NAME_PATTERN}
                ).scalar_one()
                in_python = models._PERSON_NAME_RE.fullmatch(value) is not None
                assert bool(in_database) == in_python, value


class TestThePartialUniqueIndexes:
    def test_two_active_accounts_cannot_share_a_login(self, migrated_engine: Engine) -> None:
        with migrated_engine.begin() as connection:
            _insert_user(connection, USR_A, "anna@example.com", completed=True)
        state = _refused(
            migrated_engine,
            "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, "
            "password_salt, password_hash) VALUES (:uid, 'anna@example.com', "
            "'pbkdf2_sha256', 600000, :salt, :digest)",
            {"uid": USR_B, "salt": SALT, "digest": DIGEST},
        )
        assert state == "23505"

    def test_an_archived_account_and_an_active_one_may_share_a_login(
        self, migrated_engine: Engine
    ) -> None:
        seed = _seed_uid(migrated_engine)
        with migrated_engine.begin() as connection:
            _insert_user(connection, USR_A, "anna@example.com", completed=True, archived_by=seed)
            _insert_user(connection, USR_B, "anna@example.com", completed=True)
            count = connection.execute(
                text("SELECT count(*) FROM app_user WHERE login = 'anna@example.com'")
            ).scalar_one()
        assert count == 2

    def test_one_pending_request_per_login(self, migrated_engine: Engine) -> None:
        with migrated_engine.begin() as connection:
            _insert_request(connection, REG_A, "anna@example.com")
        state = _refused(
            migrated_engine,
            "INSERT INTO registration_request (request_id, login, last_name, first_name, "
            "password_algorithm, password_iterations, password_salt, password_hash) VALUES "
            "(:rid, 'anna@example.com', 'Петрова', 'Анна', 'pbkdf2_sha256', 600000, :s, :d)",
            {"rid": REG_B, "s": SALT, "d": DIGEST},
        )
        assert state == "23505"

    def test_a_decided_request_and_a_pending_one_may_share_a_login(
        self, migrated_engine: Engine
    ) -> None:
        seed = _seed_uid(migrated_engine)
        with migrated_engine.begin() as connection:
            _insert_request(connection, REG_A, "anna@example.com")
            connection.execute(text(_REJECT), {"by": seed, "rid": REG_A})
            _insert_request(connection, REG_B, "anna@example.com")
            count = connection.execute(
                text("SELECT count(*) FROM registration_request WHERE login = 'anna@example.com'")
            ).scalar_one()
        assert count == 2


# =======================================================================================
# trg_registration_request_guard
# =======================================================================================


@pytest.fixture
def decided(migrated_engine: Engine) -> dict[str, str]:
    """One approved request (with its created account) and one rejected request."""
    seed = _seed_uid(migrated_engine)
    with migrated_engine.begin() as connection:
        _insert_request(connection, REG_A, "anna@example.com")
        _insert_user(connection, USR_A, "anna@example.com", completed=True)
        connection.execute(text(_APPROVE), {"by": seed, "created": USR_A, "rid": REG_A})
        _insert_request(connection, REG_B, "boris@example.com")
        connection.execute(text(_REJECT), {"by": seed, "rid": REG_B})
    return {"seed": seed, "approved": REG_A, "rejected": REG_B, "created": USR_A}


class TestTheRegistrationGuard:
    def test_a_request_is_created_pending_only(self, migrated_engine: Engine) -> None:
        state = _refused(
            migrated_engine,
            "INSERT INTO registration_request (request_id, login, last_name, first_name, "
            "status) VALUES (:rid, 'anna@example.com', 'Петрова', 'Анна', 'rejected')",
            {"rid": REG_A},
        )
        assert state == "AM001"

    def test_the_decision_nulls_the_password_columns(self, decided, migrated_engine) -> None:
        with migrated_engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT password_algorithm, password_iterations, password_salt, "
                    "password_hash FROM registration_request"
                )
            ).all()
        assert [tuple(row) for row in rows] == [(None, None, None, None)] * 2

    def test_a_decision_that_keeps_the_password_is_refused(self, migrated_engine) -> None:
        seed = _seed_uid(migrated_engine)
        with migrated_engine.begin() as connection:
            _insert_request(connection, REG_A, "anna@example.com")
        state = _refused(
            migrated_engine,
            "UPDATE registration_request SET status = 'rejected', decided_at = now(), "
            "decided_by = :by, rejection_reason = 'no' WHERE request_id = :rid",
            {"by": seed, "rid": REG_A},
        )
        assert state == "AM003"

    def test_a_decision_may_not_rewrite_the_request(self, migrated_engine) -> None:
        seed = _seed_uid(migrated_engine)
        with migrated_engine.begin() as connection:
            _insert_request(connection, REG_A, "anna@example.com")
        state = _refused(
            migrated_engine,
            _REJECT.replace("SET status", "SET login = 'mallory@example.com', status"),
            {"by": seed, "rid": REG_A},
        )
        assert state == "AM003"

    @pytest.mark.parametrize(
        "statement",
        [
            "UPDATE registration_request SET status = 'approved', rejection_reason = NULL, "
            "created_user_uid = :created WHERE request_id = :rejected",
            "UPDATE registration_request SET status = 'rejected', created_user_uid = NULL, "
            "rejection_reason = 'changed my mind' WHERE request_id = :approved",
            "UPDATE registration_request SET status = 'pending', decided_at = NULL, "
            "decided_by = NULL, rejection_reason = NULL WHERE request_id = :rejected",
        ],
        ids=["rejected-then-approved", "approved-then-rejected", "back-to-pending"],
    )
    def test_a_second_decision_is_refused(self, decided, migrated_engine, statement) -> None:
        state = _refused(migrated_engine, statement, decided)
        assert state == "AM001"

    @pytest.mark.parametrize("which", ["approved", "rejected"])
    def test_a_password_column_write_after_the_decision_is_refused(
        self, decided, migrated_engine, which
    ) -> None:
        state = _refused(
            migrated_engine,
            "UPDATE registration_request SET password_algorithm = 'pbkdf2_sha256', "
            "password_iterations = 600000, password_salt = :salt, password_hash = :digest "
            "WHERE request_id = :rid",
            {"salt": SALT, "digest": DIGEST, "rid": decided[which]},
        )
        assert state == "AM003"

    @pytest.mark.parametrize("value", [None, USR_B], ids=["to-null", "to-another-account"])
    def test_a_manual_created_user_uid_update_is_refused(
        self, decided, migrated_engine, value
    ) -> None:
        if value is not None:
            with migrated_engine.begin() as connection:
                _insert_user(connection, USR_B, "boris@example.com", completed=True)
        state = _refused(
            migrated_engine,
            "UPDATE registration_request SET created_user_uid = :value WHERE request_id = :rid",
            {"value": value, "rid": decided["approved"]},
        )
        assert state == "AM003"

    def test_the_purge_cascade_may_null_created_user_uid(self, decided, migrated_engine) -> None:
        """The one write after the decision the guard permits, and only from the cascade."""
        with migrated_engine.begin() as connection:
            connection.execute(text("DELETE FROM app_user_role WHERE user_uid = :u"), {"u": USR_A})
            connection.execute(text("DELETE FROM app_user WHERE user_uid = :u"), {"u": USR_A})
        with migrated_engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT status, created_user_uid, decided_by FROM registration_request "
                    "WHERE request_id = :rid"
                ),
                {"rid": decided["approved"]},
            ).one()
        assert tuple(row) == ("approved", None, decided["seed"]), (
            "the request that created the account is history and survives its purge"
        )

    def test_a_request_is_never_deleted(self, decided, migrated_engine) -> None:
        state = _refused(
            migrated_engine,
            "DELETE FROM registration_request WHERE request_id = :rid",
            {"rid": decided["rejected"]},
        )
        assert state == "AM003"

    def test_the_status_read_brake_moves_in_any_state(self, decided, migrated_engine) -> None:
        with migrated_engine.begin() as connection:
            moved = connection.execute(
                text(
                    "UPDATE registration_request SET failed_sign_ins = failed_sign_ins + 1, "
                    "last_failed_sign_in_at = now() WHERE request_id IN (:approved, :rejected)"
                ),
                decided,
            ).rowcount
        assert moved == 2

    @pytest.mark.parametrize(
        "column", ["archived_by", "granted_by", "decided_by", "author_user_uid"]
    )
    def test_each_restricting_reference_alone_makes_an_account_undeletable(
        self, migrated_engine: Engine, column: str
    ) -> None:
        """One RESTRICT reference at a time, on an account that has no other.

        The subject is a fresh account (``USR_A``) with no roles, so the only row that
        names it is the one this case writes -- the refusal cannot come from another.
        """
        seed = _seed_uid(migrated_engine)
        with migrated_engine.begin() as connection:
            _insert_user(connection, USR_A, "anna@example.com", completed=True)
            if column == "archived_by":
                _insert_user(connection, USR_B, "boris@example.com", archived_by=USR_A)
            elif column == "granted_by":
                connection.execute(
                    text(
                        "INSERT INTO app_user_role (user_uid, role, granted_by) "
                        "VALUES (:seed, 'expert', :by) ON CONFLICT (user_uid, role) "
                        "DO UPDATE SET granted_by = EXCLUDED.granted_by"
                    ),
                    {"seed": seed, "by": USR_A},
                )
            elif column == "decided_by":
                _insert_request(connection, REG_A, "boris@example.com")
                connection.execute(text(_REJECT), {"by": USR_A, "rid": REG_A})
            else:
                # A decision event needs a finding and an observation, i.e. a whole run;
                # the subject here is only the author column. So this one INSERT skips
                # foreign-key enforcement (`replica` mode, this transaction only, lane
                # superuser); the DELETE below runs in a normal transaction and is what is
                # measured.
                connection.execute(text("SET LOCAL session_replication_role = replica"))
                connection.execute(
                    text(
                        "INSERT INTO expert_decision_event (decision_id, finding_uid, "
                        "finding_observation_id, event_type, verdict, author_label, "
                        "author_user_uid) VALUES ('dec_01ARZ3NDEKTSV4RRFFQ69G5FAA', "
                        "'fnd_01ARZ3NDEKTSV4RRFFQ69G5FAA', 'fobs_01ARZ3NDEKTSV4RRFFQ69G5FAA', "
                        "'accept', 'accepted', 'Петрова А.', :uid)"
                    ),
                    {"uid": USR_A},
                )
        state = _refused(
            migrated_engine, "DELETE FROM app_user WHERE user_uid = :uid", {"uid": USR_A}
        )
        assert state == "23503", column

    def test_an_unreferenced_account_is_deleted_with_its_own_roles(
        self, migrated_engine: Engine
    ) -> None:
        """The CASCADE arm: an account's own roles are not a reference."""
        with migrated_engine.begin() as connection:
            _insert_user(connection, USR_A, "anna@example.com", completed=True)
            connection.execute(
                text("INSERT INTO app_user_role (user_uid, role) VALUES (:u, 'expert')"),
                {"u": USR_A},
            )
            connection.execute(text("DELETE FROM app_user WHERE user_uid = :u"), {"u": USR_A})
            left = connection.execute(
                text("SELECT count(*) FROM app_user_role WHERE user_uid = :u"), {"u": USR_A}
            ).scalar_one()
        assert left == 0

    def test_the_rejection_reason_is_bounded(self, migrated_engine) -> None:
        seed = _seed_uid(migrated_engine)
        with migrated_engine.begin() as connection:
            _insert_request(connection, REG_A, "anna@example.com")
        state = _refused(
            migrated_engine,
            _REJECT.replace("'not this time'", ":reason"),
            {"by": seed, "rid": REG_A, "reason": "x" * 257},
        )
        assert state == "23514"


# =======================================================================================
# The downgrade.
# =======================================================================================


class TestTheDowngrade:
    def test_it_refuses_while_the_backfill_is_there(self, migrated_database, migrated_engine):
        """Every real database: the backfill gives every account a role."""
        result = run_foundation_command(_argv("downgrade", PREVIOUS), _url(migrated_database))
        assert result.returncode != 0
        assert "refusing to downgrade 0015_accounts_roles_registration" in result.stderr
        assert "app_user_role=2" in result.stderr
        with migrated_engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == "0016_release_notes"

    @pytest.mark.parametrize(
        "occupy",
        [
            "INSERT INTO registration_request (request_id, login, last_name, first_name, "
            "password_algorithm, password_iterations, password_salt, password_hash) VALUES "
            f"('{REG_A}', 'anna@example.com', 'Петрова', 'Анна', 'pbkdf2_sha256', 600000, "
            f"'{SALT}', '{DIGEST}')",
            "UPDATE app_user SET last_name = 'Петрова'",
            "UPDATE app_user SET login = 'owner@example.com'",
        ],
        ids=["a-request", "a-name", "an-email-login"],
    )
    def test_it_refuses_while_anything_the_0014_shape_cannot_hold_exists(
        self, migrated_database, migrated_engine, occupy
    ) -> None:
        url = _url(migrated_database)
        clear_the_role_backfill(url)
        with migrated_engine.begin() as connection:
            connection.execute(text(occupy))
        result = run_foundation_command(_argv("downgrade", PREVIOUS), url)
        assert result.returncode != 0
        assert "refusing to downgrade 0015_accounts_roles_registration" in result.stderr

    def test_on_an_empty_tree_it_runs_and_upgrades_back(
        self, migrated_database, migrated_engine
    ) -> None:
        url = _url(migrated_database)
        assert clear_the_role_backfill(url) == 2
        down = run_foundation_command(_argv("downgrade", PREVIOUS), url)
        assert down.returncode == 0, down.describe()
        with migrated_engine.connect() as connection:
            tables = set(
                connection.execute(
                    text(
                        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                        "AND tablename IN ('app_user_role', 'registration_request')"
                    )
                ).scalars()
            )
            columns = set(
                connection.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name IN ('app_user', 'expert_decision_event') "
                        "AND column_name IN ('last_name', 'archived_at', 'author_user_uid', "
                        "'profile_completed_at')"
                    )
                ).scalars()
            )
            unique = connection.execute(
                text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conname = 'uq_app_user_login'"
                )
            ).scalar()
            login_check = connection.execute(
                text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conname = 'ck_app_user_login_format'"
                )
            ).scalar_one()
            stamped = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert tables == set()
        assert columns == set()
        assert unique == "UNIQUE (login)", "the 0006 UNIQUE constraint was not restored"
        assert "@" not in login_check and "a-z0-9._-" in login_check
        assert stamped == PREVIOUS

        up = run_foundation_command(MIGRATE_ARGV, url)
        assert up.returncode == 0, up.describe()
        with migrated_engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM app_user_role")).scalar_one() == 2


# =======================================================================================
# Upgrading a 0014 database that has lived.
# =======================================================================================


class TestUpgradeFromA0014Database:
    def test_the_seeded_admin_with_a_changed_password_keeps_it_and_gets_both_roles(
        self, database_at_0014
    ) -> None:
        settings, engine = database_at_0014
        replacement = hash_password(CHANGED_PASSWORD)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE app_user SET password_salt = :salt, password_hash = :digest, "
                    "password_iterations = :iterations, is_default_credential = false, "
                    "password_updated_at = now(), token_epoch = token_epoch + 1 "
                    "WHERE login = :login"
                ),
                {
                    "salt": replacement.salt,
                    "digest": replacement.digest,
                    "iterations": replacement.iterations,
                    "login": SEED_LOGIN,
                },
            )
            before = connection.execute(
                text(
                    "SELECT user_uid, password_hash, token_epoch, is_default_credential "
                    "FROM app_user"
                )
            ).one()

        result = run_foundation_command(MIGRATE_ARGV, _url(settings))
        assert result.returncode == 0, result.describe()

        with engine.connect() as connection:
            after = connection.execute(
                text(
                    "SELECT user_uid, password_hash, token_epoch, is_default_credential "
                    "FROM app_user"
                )
            ).one()
            roles = connection.execute(
                text("SELECT role FROM app_user_role ORDER BY role")
            ).scalars().all()
            stored = connection.execute(
                text(
                    "SELECT password_algorithm, password_iterations, password_salt, "
                    "password_hash, profile_completed_at FROM app_user"
                )
            ).one()
        assert tuple(after) == tuple(before), "the upgrade touched the account's credential"
        assert roles == ["admin", "expert"]
        assert stored[4] is None
        assert verify_password(
            StoredPassword(stored[0], int(stored[1]), stored[2], stored[3]), CHANGED_PASSWORD
        )
        with Session(engine) as session:
            signed_in = UserRepository().authenticate(session, SEED_LOGIN, CHANGED_PASSWORD)
            session.commit()
        assert signed_in is not None and signed_in.login == SEED_LOGIN

    def test_a_legacy_non_email_login_stays_a_legacy_expert(self, database_at_0014) -> None:
        settings, engine = database_at_0014
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO app_user (user_uid, login, password_algorithm, "
                    "password_iterations, password_salt, password_hash, display_name) VALUES "
                    "(:uid, 'clara.jones', 'pbkdf2_sha256', 600000, :salt, :digest, "
                    "'Clara Jones')"
                ),
                {"uid": USR_A, "salt": SALT, "digest": DIGEST},
            )
        result = run_foundation_command(MIGRATE_ARGV, _url(settings))
        assert result.returncode == 0, result.describe()
        assert "2 existing account(s)" in result.stdout + result.stderr
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT u.login, u.profile_completed_at, u.display_name, "
                    "array_agg(r.role ORDER BY r.role) FROM app_user u "
                    "JOIN app_user_role r USING (user_uid) GROUP BY u.user_uid ORDER BY u.login"
                )
            ).all()
        assert [tuple(row) for row in rows] == [
            (SEED_LOGIN, None, None, ["admin", "expert"]),
            ("clara.jones", None, "Clara Jones", ["expert"]),
        ]
        with Session(engine) as session:
            found = UserRepository().find_by_login(session, "Clara.Jones")
        assert found is not None and found.display_label == "Clara Jones"

    def test_without_the_seed_the_upgrade_succeeds_and_says_nobody_is_admin(
        self, database_at_0014
    ) -> None:
        settings, engine = database_at_0014
        with engine.begin() as connection:
            connection.execute(text("UPDATE app_user SET login = 'owner' WHERE login = 'admin'"))
        result = run_foundation_command(MIGRATE_ARGV, _url(settings))
        assert result.returncode == 0, result.describe()
        assert "NO ACCOUNT HOLDS THE ROLE 'admin'" in result.stdout + result.stderr
        assert "python -m auditmanager.access.grant" in result.stdout + result.stderr
        with engine.connect() as connection:
            roles = connection.execute(text("SELECT role FROM app_user_role")).scalars().all()
        assert roles == ["expert"]


def test_a_second_upgrade_at_head_changes_no_role(migrated_database, migrated_engine) -> None:
    """Re-running the migration at head is a no-op; the backfill is not repeated."""
    result = run_foundation_command(MIGRATE_ARGV, _url(migrated_database))
    assert result.returncode == 0, result.describe()
    with migrated_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM app_user_role")).scalar_one() == 2
