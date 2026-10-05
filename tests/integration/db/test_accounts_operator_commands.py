"""``python -m auditmanager.access.profile`` and ``python -m auditmanager.access.grant``.

`W49-ACCESS-01a`, `W49-PLAN.md` §3.1-§3.2. Both are run as the operator runs them -- a
subprocess with ``PYTHONPATH=src`` and the lane's ``DATABASE_URL`` pointing at a throwaway
database migrated by the literal command -- and their effect is read back from the table,
not from what they print.
"""

from __future__ import annotations

from sqlalchemy import Engine, text

from auditmanager.access.passwords import StoredPassword, verify_password
from auditmanager.shared.db.config import DatabaseSettings
from tests.integration.db.conftest import (  # type: ignore[import-not-found]
    run_foundation_command,
)

PROFILE = [".venv/bin/python", "-m", "auditmanager.access.profile"]
GRANT = [".venv/bin/python", "-m", "auditmanager.access.grant"]
SEED_PASSWORD = "password"  # noqa: S105 - the published 0006 default
USR_B = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAB"


def _url(settings: DatabaseSettings) -> str:
    return settings.url.render_as_string(hide_password=False)


def _row(engine: Engine, login_or_uid: str):
    with engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT user_uid, login, last_name, first_name, middle_name, "
                "profile_completed_at, token_epoch, password_algorithm, "
                "password_iterations, password_salt, password_hash FROM app_user "
                "WHERE login = :v OR user_uid = :v"
            ),
            {"v": login_or_uid},
        ).one_or_none()


def _complete(url: str, *extra: str):
    return run_foundation_command(
        [
            *PROFILE,
            "--login",
            "admin",
            "--email",
            " Owner@Example.COM ",
            "--last-name",
            "Петрова",
            "--first-name",
            "Анна",
            *extra,
        ],
        url,
    )


class TestTheProfileCommand:
    def test_it_completes_the_seed_in_one_statement_and_changes_nothing_else(
        self, migrated_database: DatabaseSettings, migrated_engine: Engine
    ) -> None:
        before = _row(migrated_engine, "admin")
        result = _complete(_url(migrated_database), "--middle-name", "Сергеевна")
        assert result.returncode == 0, result.describe()
        assert "access-profile COMPLETED: login=owner@example.com" in result.stdout
        assert "label='Петрова А. С.'" in result.stdout

        after = _row(migrated_engine, before.user_uid)
        assert after.login == "owner@example.com"
        assert (after.last_name, after.first_name, after.middle_name) == (
            "Петрова",
            "Анна",
            "Сергеевна",
        )
        assert after.profile_completed_at is not None
        assert after.token_epoch == before.token_epoch, "completion is not a revocation"
        assert after.password_hash == before.password_hash
        assert verify_password(
            StoredPassword(
                after.password_algorithm,
                int(after.password_iterations),
                after.password_salt,
                after.password_hash,
            ),
            SEED_PASSWORD,
        )

    def test_a_complete_profile_is_refused_a_second_completion(
        self, migrated_database: DatabaseSettings, migrated_engine: Engine
    ) -> None:
        url = _url(migrated_database)
        assert _complete(url).returncode == 0
        again = run_foundation_command(
            [
                *PROFILE,
                "--login",
                "owner@example.com",
                "--email",
                "other@example.com",
                "--last-name",
                "Иванова",
                "--first-name",
                "Мария",
            ],
            url,
        )
        assert again.returncode == 2, again.describe()
        assert "access-profile FAILED" in again.stderr
        assert _row(migrated_engine, "owner@example.com").last_name == "Петрова"

    def test_an_unknown_login_is_status_one(self, migrated_database: DatabaseSettings) -> None:
        result = run_foundation_command(
            [
                *PROFILE,
                "--login",
                "nobody",
                "--email",
                "x@example.com",
                "--last-name",
                "Петрова",
                "--first-name",
                "Анна",
            ],
            _url(migrated_database),
        )
        assert result.returncode == 1, result.describe()
        assert "access-profile: no active account has that login" in result.stdout

    def test_a_refused_name_writes_nothing(
        self, migrated_database: DatabaseSettings, migrated_engine: Engine
    ) -> None:
        result = run_foundation_command(
            [
                *PROFILE,
                "--login",
                "admin",
                "--email",
                "owner@example.com",
                "--last-name",
                "Петрoва",  # a Latin "o" inside a Cyrillic word
                "--first-name",
                "Анна",
            ],
            _url(migrated_database),
        )
        assert result.returncode == 2, result.describe()
        assert "mixes Cyrillic and Latin" in result.stderr
        assert _row(migrated_engine, "admin").profile_completed_at is None

    def test_an_email_another_active_account_holds_is_refused(
        self, migrated_database: DatabaseSettings, migrated_engine: Engine
    ) -> None:
        with migrated_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO app_user (user_uid, login, password_algorithm, "
                    "password_iterations, password_salt, password_hash) VALUES "
                    "(:uid, 'owner@example.com', 'pbkdf2_sha256', 600000, :s, :d)"
                ),
                {"uid": USR_B, "s": "0" * 32, "d": "0" * 64},
            )
        result = _complete(_url(migrated_database))
        assert result.returncode == 2, result.describe()
        assert "already holds this login" in result.stderr
        assert _row(migrated_engine, "admin").profile_completed_at is None


class TestTheGrantCommand:
    def test_a_grant_that_changes_the_set_revokes_and_one_that_does_not_does_not(
        self, migrated_database: DatabaseSettings, migrated_engine: Engine
    ) -> None:
        url = _url(migrated_database)
        with migrated_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO app_user (user_uid, login, password_algorithm, "
                    "password_iterations, password_salt, password_hash) VALUES "
                    "(:uid, 'clara.jones', 'pbkdf2_sha256', 600000, :s, :d)"
                ),
                {"uid": USR_B, "s": "0" * 32, "d": "0" * 64},
            )
        before = _row(migrated_engine, USR_B).token_epoch

        granted = run_foundation_command([*GRANT, "--login", "Clara.Jones", "--role", "admin"], url)
        assert granted.returncode == 0, granted.describe()
        assert "access-grant GRANTED: login=clara.jones" in granted.stdout
        assert "roles=admin" in granted.stdout
        assert _row(migrated_engine, USR_B).token_epoch == before + 1

        again = run_foundation_command([*GRANT, "--login", "clara.jones", "--role", "admin"], url)
        assert again.returncode == 0, again.describe()
        assert "access-grant UNCHANGED" in again.stdout
        assert _row(migrated_engine, USR_B).token_epoch == before + 1

        with migrated_engine.connect() as connection:
            roles = connection.execute(
                text("SELECT role, granted_by FROM app_user_role WHERE user_uid = :u"),
                {"u": USR_B},
            ).all()
        assert [tuple(row) for row in roles] == [("admin", None)]

    def test_an_unknown_login_is_status_one_and_an_unknown_role_status_two(
        self, migrated_database: DatabaseSettings
    ) -> None:
        url = _url(migrated_database)
        missing = run_foundation_command([*GRANT, "--login", "nobody", "--role", "expert"], url)
        assert missing.returncode == 1, missing.describe()
        assert "access-grant: no active account has that login" in missing.stdout
        bogus = run_foundation_command([*GRANT, "--login", "admin", "--role", "root"], url)
        assert bogus.returncode == 2, bogus.describe()
