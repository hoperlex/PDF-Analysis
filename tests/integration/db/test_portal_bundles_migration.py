"""`W55B-SEAL-01`: migration ``0021_portal_bundles`` on an empty and on a populated database.

Plan `W55-PLAN.md` section B4, `W55B-SEAL-01`, requires a fresh upgrade, an upgrade from
``0020`` with rows and a refused downgrade. Beside them: the page ceiling really is 500 and
no more, the three text counts are all set or all NULL, the page list is a strictly ascending
1-based list inside the page count, and an old version keeps its NULLs.

HEAVY: every test here needs a real PostgreSQL (the lane's ``57410``), so it runs on the
lane's private stack (R-102). Every refusal has a control write that succeeds, so a refusal
cannot pass because the statement was malformed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid

HEAD = "0023_norm_citations"
PREVIOUS = "0020_norms_search"
MIGRATION = Path(__file__).resolve().parents[3] / "db/migrations/versions/20261013_0021_portal_bundles.py"
DIGEST = "a" * 64
CHECK_VIOLATION = "23514"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _head(connection) -> str:
    return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def _sqlstate(error: pytest.ExceptionInfo[DBAPIError]) -> str | None:
    return getattr(error.value.orig, "sqlstate", None)


def _document(connection) -> str:
    project, document = str(ProjectUid.new()), str(DocumentUid.new())
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'bundle')"), {"p": project})
    connection.execute(text(
        "INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'AR-1')"
    ), {"d": document, "p": project})
    return document


def _version(connection, document: str, ordinal: int, *, pages: int = 12, **counts) -> str:
    """One published version; ``counts`` are any of the three new columns."""
    version = str(VersionUid.new())
    columns = ["version_uid", "document_uid", "version_ordinal", "media_type", "byte_size", "sha256", "page_count"]
    values = [":v", ":d", ":o", "'application/pdf'", "1024", ":h", ":n"]
    parameters: dict[str, object] = {"v": version, "d": document, "o": ordinal, "h": DIGEST, "n": pages}
    for name, value in counts.items():
        columns.append(name)
        values.append(f":{name}")
        parameters[name] = value
    connection.execute(text(
        f"INSERT INTO document_version ({', '.join(columns)}) VALUES ({', '.join(values)})"
    ), parameters)
    return version


def _refused(connection, document: str, ordinal: int, *, pages: int = 12, **counts) -> None:
    with pytest.raises(DBAPIError) as refused:
        with connection.begin_nested():
            _version(connection, document, ordinal, pages=pages, **counts)
    assert _sqlstate(refused) == CHECK_VIOLATION, refused.value


# --- the migration lifecycle -------------------------------------------------------------


def test_a_fresh_upgrade_widens_the_page_ceiling_and_adds_three_nullable_columns(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.connect() as connection:
        assert _head(connection) == HEAD
        columns = {
            row.column_name: (row.data_type, row.is_nullable)
            for row in connection.execute(text(
                "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
                "WHERE table_name = 'document_version' AND column_name IN "
                "('text_character_count', 'textless_pages', 'recognised_character_count')"
            ))
        }
        assert columns == {
            "text_character_count": ("integer", "YES"),
            "textless_pages": ("ARRAY", "YES"),
            "recognised_character_count": ("integer", "YES"),
        }
        assert connection.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'ck_document_version_page_count'"
        )).scalar_one() == "CHECK (((page_count >= 1) AND (page_count <= 500)))"
        assert connection.execute(text(
            "SELECT provolatile FROM pg_proc WHERE proname = 'am_is_ascending_page_list'"
        )).scalar_one() == "i", "a CHECK may call only an IMMUTABLE function"


def test_the_ceiling_is_five_hundred_and_not_five_hundred_and_one(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        document = _document(connection)
        _version(connection, document, 1, pages=500)  # control: the new ceiling is accepted
        _version(connection, document, 2, pages=31)  # control: the old ceiling is gone
        _refused(connection, document, 3, pages=501)
        _refused(connection, document, 4, pages=0)


def test_the_three_counts_are_all_set_or_all_null(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        document = _document(connection)
        _version(connection, document, 1)  # control: none set
        _version(connection, document, 2, text_character_count=9000, textless_pages=[], recognised_character_count=0)
        _refused(connection, document, 3, text_character_count=9000)
        _refused(connection, document, 4, textless_pages=[])
        _refused(connection, document, 5, recognised_character_count=1)
        _refused(connection, document, 6, text_character_count=9000, textless_pages=[])
        _refused(connection, document, 7, text_character_count=-1, textless_pages=[], recognised_character_count=0)
        _refused(connection, document, 8, text_character_count=1, textless_pages=[], recognised_character_count=-1)


@pytest.mark.parametrize(
    ("pages", "page_count", "accepted"),
    [
        ([], 6, True),
        ([1], 1, True),
        ([1, 3, 6], 6, True),
        ([3, 2], 6, False),  # not ascending
        ([2, 2], 6, False),  # not strictly ascending
        ([0], 6, False),  # not 1-based
        ([-1, 2], 6, False),
        ([7], 6, False),  # past the page count
        ([1, 2, 3], 2, False),  # more pages than the document has
        ([1, None, 3], 6, False),  # a hole
    ],
)
def test_the_textless_page_list_is_one_based_strictly_ascending_and_inside_the_document(
    migrated_engine: Engine, pages: list[int | None], page_count: int, accepted: bool
) -> None:
    with migrated_engine.begin() as connection:
        document = _document(connection)
        _version(connection, document, 1, pages=6)  # control: the rest of the row is valid
        counts = {"text_character_count": 10, "textless_pages": pages, "recognised_character_count": 0}
        if accepted:
            _version(connection, document, 2, pages=page_count, **counts)
        else:
            _refused(connection, document, 2, pages=page_count, **counts)


def test_a_multidimensional_page_list_is_refused(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        document = _document(connection)
        with pytest.raises(DBAPIError) as refused:
            with connection.begin_nested():
                connection.execute(text(
                    "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                    "media_type, byte_size, sha256, page_count, text_character_count, "
                    "textless_pages, recognised_character_count) VALUES (:v, :d, 1, "
                    "'application/pdf', 1, :h, 6, 1, '{{1,2},{3,4}}', 0)"
                ), {"v": str(VersionUid.new()), "d": document, "h": DIGEST})
        assert _sqlstate(refused) == CHECK_VIOLATION


def test_a_populated_0020_upgrades_and_its_versions_keep_their_nulls(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    at_0020 = foundation_command(_alembic("upgrade", PREVIOUS), url)
    assert at_0020.returncode == 0, at_0020.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            document = _document(connection)
            old = _version(connection, document, 1, pages=30)
            with pytest.raises(DBAPIError) as refused:  # 0020's ceiling is still 30
                with connection.begin_nested():
                    _version(connection, document, 2, pages=31)
            assert _sqlstate(refused) == CHECK_VIOLATION
        upgraded = foundation_command(_alembic("upgrade", "head"), url)
        assert upgraded.returncode == 0, upgraded.describe()
        with engine.connect() as connection:
            assert _head(connection) == HEAD
            row = connection.execute(text(
                "SELECT page_count, text_character_count, textless_pages, recognised_character_count "
                "FROM document_version WHERE version_uid = :v"
            ), {"v": old}).one()
            assert tuple(row) == (30, None, None, None)
    finally:
        engine.dispose()


def test_a_retained_large_version_or_count_refuses_the_downgrade(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    up = foundation_command(_alembic("upgrade", "head"), url)
    assert up.returncode == 0, up.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            document = _document(connection)
            _version(connection, document, 1, pages=31)
        refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert refused.returncode != 0
        assert "refusing to downgrade 0021_portal_bundles" in refused.stderr
        assert "a version above 30 pages" in refused.stderr
        assert "a version carrying its text counts" not in refused.stderr
        with engine.connect() as connection:
            assert _head(connection) == HEAD
            assert connection.execute(text("SELECT count(*) FROM document_version")).scalar_one() == 1
    finally:
        engine.dispose()


def test_a_retained_count_alone_refuses_the_downgrade(empty_database, foundation_command) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    up = foundation_command(_alembic("upgrade", "head"), url)
    assert up.returncode == 0, up.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            document = _document(connection)
            _version(connection, document, 1, pages=6, text_character_count=5,
                     textless_pages=[], recognised_character_count=0)
        refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert refused.returncode != 0
        assert "a version carrying its text counts" in refused.stderr
        assert "a version above 30 pages" not in refused.stderr
    finally:
        engine.dispose()


def test_an_empty_0021_downgrades_to_the_old_ceiling_and_upgrades_again(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    up = foundation_command(_alembic("upgrade", "head"), url)
    assert up.returncode == 0, up.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:  # a version both ceilings accept does not block it
            _version(connection, _document(connection), 1, pages=30)
        down = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert down.returncode == 0, down.describe()
        with engine.connect() as connection:
            assert _head(connection) == PREVIOUS
            assert connection.execute(text(
                "SELECT count(*) FROM information_schema.columns WHERE table_name = 'document_version' "
                "AND column_name IN ('text_character_count', 'textless_pages', 'recognised_character_count')"
            )).scalar_one() == 0
            assert connection.execute(text(
                "SELECT to_regprocedure('am_is_ascending_page_list(integer[],integer)')"
            )).scalar_one() is None
            with pytest.raises(DBAPIError) as refused:
                with connection.begin_nested():
                    _version(connection, _document(connection), 1, pages=31)
            assert _sqlstate(refused) == CHECK_VIOLATION
        again = foundation_command(_alembic("upgrade", "head"), url)
        assert again.returncode == 0, again.describe()
    finally:
        engine.dispose()
