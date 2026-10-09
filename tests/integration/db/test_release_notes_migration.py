"""The 0016 database boundary on a fresh real PostgreSQL migration."""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.access.references import ACCOUNT_REFERENCES
from auditmanager.releases.public import canonical_semver_sort_key
from auditmanager.shared.db.migrations import head_revision
from tests.integration.db.conftest import MIGRATE_ARGV, run_foundation_command


def _refused(engine: Engine, statement: str, **parameters: object) -> str:
    with engine.connect() as connection:
        with pytest.raises(DBAPIError) as caught:
            with connection.begin():
                connection.execute(text(statement), parameters)
    return caught.value.orig.sqlstate


def test_release_schema_is_the_single_head_and_mark_is_a_cascading_account_row(
    migrated_engine: Engine,
) -> None:
    assert head_revision() == "0017_execution_queue"
    assert any(
        reference.table == "account_release_mark"
        and reference.column == "user_uid"
        and reference.on_delete == "CASCADE"
        for reference in ACCOUNT_REFERENCES
    )
    with migrated_engine.connect() as connection:
        collation = connection.execute(
            text("SELECT collation_name FROM information_schema.columns "
                 "WHERE table_name = 'release' AND column_name = 'sort_key'")
        ).scalar_one()
    assert collation == "C", "SemVer sort keys require byte order, not locale order"


def test_release_rows_are_append_only_and_account_mark_only_rises(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.begin() as connection:
        account = connection.execute(text("SELECT user_uid FROM app_user LIMIT 1")).scalar_one()
        low = connection.execute(
            text("INSERT INTO release(version, sort_key, is_archive) "
                 "VALUES (:version, :sort_key, false) RETURNING pk"),
            {"version": "0.9.0", "sort_key": canonical_semver_sort_key("0.9.0")},
        ).scalar_one()
        high = connection.execute(
            text("INSERT INTO release(version, sort_key, is_archive) "
                 "VALUES (:version, :sort_key, false) RETURNING pk"),
            {"version": "0.10.0", "sort_key": canonical_semver_sort_key("0.10.0")},
        ).scalar_one()
        connection.execute(
            text("INSERT INTO release_revision "
                 "(release_pk, revision, released_on, title, content, content_sha256) "
                 "VALUES (:release_pk, 1, DATE '2026-10-08', 'First note', "
                 "'{}'::jsonb, :digest)"),
            {"release_pk": low, "digest": "a" * 64},
        )
        connection.execute(
            text("INSERT INTO account_release_mark(user_uid, read_through_release_pk) "
                 "VALUES (:user_uid, :release_pk)"),
            {"user_uid": account, "release_pk": high},
        )

    for statement, params in (
        ("UPDATE release SET version='0.9.1' WHERE pk=:pk", {"pk": low}),
        ("DELETE FROM release WHERE pk=:pk", {"pk": low}),
        ("UPDATE release_revision SET title='Changed' WHERE release_pk=:pk", {"pk": low}),
        ("DELETE FROM release_revision WHERE release_pk=:pk", {"pk": low}),
    ):
        assert _refused(migrated_engine, statement, **params) == "AM003"

    with migrated_engine.begin() as connection:
        # A lower known mark is a no-op. Its timestamp and release both remain fixed.
        before = connection.execute(
            text("SELECT read_through_release_pk, marked_at FROM account_release_mark "
                 "WHERE user_uid=:uid"), {"uid": account}
        ).one()
        result = connection.execute(
            text("UPDATE account_release_mark SET read_through_release_pk=:pk "
                 "WHERE user_uid=:uid"), {"pk": low, "uid": account}
        )
        after = connection.execute(
            text("SELECT read_through_release_pk, marked_at FROM account_release_mark "
                 "WHERE user_uid=:uid"), {"uid": account}
        ).one()
        assert result.rowcount == 0
        assert after == before

    assert _refused(
        migrated_engine,
        "UPDATE account_release_mark SET read_through_release_pk=:pk WHERE user_uid=:uid",
        pk=high + 10000,
        uid=account,
    ) in {"AM003", "23503"}


def test_a_purged_account_cascades_its_own_mark(migrated_engine: Engine) -> None:
    uid = "usr_" + "8" * 26
    with migrated_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO app_user (user_uid, login, password_algorithm, "
                "password_iterations, password_salt, password_hash, is_default_credential) "
                "SELECT :uid, 'release-cascade-test', password_algorithm, "
                "password_iterations, password_salt, password_hash, false "
                "FROM app_user LIMIT 1"
            ),
            {"uid": uid},
        )
        release_pk = connection.execute(
            text("INSERT INTO release(version, sort_key, is_archive) "
                 "VALUES ('0.3.0', :sort_key, false) RETURNING pk"),
            {"sort_key": canonical_semver_sort_key("0.3.0")},
        ).scalar_one()
        connection.execute(
            text("INSERT INTO account_release_mark(user_uid, read_through_release_pk) "
                 "VALUES (:uid, :pk)"),
            {"uid": uid, "pk": release_pk},
        )
        connection.execute(text("DELETE FROM app_user WHERE user_uid=:uid"), {"uid": uid})
        assert connection.execute(
            text("SELECT count(*) FROM account_release_mark WHERE user_uid=:uid"),
            {"uid": uid},
        ).scalar_one() == 0


def test_downgrade_is_only_allowed_before_release_history_exists(
    migrated_database, migrated_engine: Engine
) -> None:
    url = migrated_database.url.render_as_string(hide_password=False)
    down = run_foundation_command(
        [*MIGRATE_ARGV[:-2], "downgrade", "0015_accounts_roles_registration"], url
    )
    assert down.returncode == 0, down.describe()
    with migrated_engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0015_accounts_roles_registration"
        )
    up = run_foundation_command(MIGRATE_ARGV, url)
    assert up.returncode == 0, up.describe()
    with migrated_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO release(version, sort_key, is_archive) "
                 "VALUES ('0.3.0', :sort_key, false)"),
            {"sort_key": canonical_semver_sort_key("0.3.0")},
        )
    refused = run_foundation_command(
        [*MIGRATE_ARGV[:-2], "downgrade", "0015_accounts_roles_registration"], url
    )
    assert refused.returncode != 0
    assert "refusing to downgrade 0016_release_notes" in refused.stderr
    with migrated_engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0017_execution_queue"
        )
