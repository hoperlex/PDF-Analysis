"""`W60-PRICE-LIST-01`: ``0026_price_lists`` on a populated ``0025`` database.

Against real PostgreSQL rows written at ``0025`` -- two accounts, a project with a document and
a published version, an available Blob and a work assignment:

* the upgrade creates four empty tables beside them and changes no existing row;
* all four tables refuse UPDATE and DELETE (``AM003``);
* a revision whose positions are not all written, or a vendor-list revision whose entries are
  not all written, is refused at COMMIT (``AM001``);
* a revision naming a Blob that is not ``available`` with the recorded digest and size is
  refused at INSERT (``AM001``);
* the CHECKs hold: identity formats (``prl_``, ``prp_``, ``vnl_`` included), the fifteen
  sections, positive exact prices with at most six decimals, ISO currencies, the format and
  media-type pairs, the row counts, the scope/project and inherit shapes, the revision numbers;
* both account columns are RESTRICT references: an account named by either alone cannot be
  deleted, and the project cannot be deleted under a price list;
* the downgrade drops exactly the four tables and the three functions, keeps every ``0025``
  row and the Blob, and the revision upgrades again.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.access.public import UserUid
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import AuditEventId, DocumentUid, ProjectUid, VersionUid
from auditmanager.storage.models import derive_blob_id

HEAD = "0026_price_lists"  # this revision; every upgrade here targets it
PREVIOUS = "0025_work_assignments"

PRICE_LIST = "prl_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_PRICE_LIST = "prl_01ARZ3NDEKTSV4RRFFQ69G5FAW"
POSITION = "prp_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_POSITION = "prp_01ARZ3NDEKTSV4RRFFQ69G5FAW"
VENDOR_LIST = "vnl_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_VENDOR_LIST = "vnl_01ARZ3NDEKTSV4RRFFQ69G5FAW"
SHA = "d" * 64
SIZE = 2048
CSV = "text/csv"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TABLES = ("price_list_revision", "price_list_position", "vendor_list_revision", "vendor_list_entry")
FUNCTIONS = (
    "am_check_price_list_blob",
    "am_require_price_list_positions",
    "am_require_vendor_list_entries",
)


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _sqlstate(error: DBAPIError) -> str:
    return str(getattr(error.orig, "sqlstate", "") or "")


def _user(connection: Any) -> str:
    user = str(UserUid.new())
    connection.execute(
        text(
            "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, "
            "password_salt, password_hash) VALUES (:u, :login, 'pbkdf2_sha256', 100000, :salt, :hash)"
        ),
        {"u": user, "login": user.lower(), "salt": "0" * 32, "hash": "0" * 64},
    )
    return user


def _blob(connection: Any, *, sha: str = SHA, size: int = SIZE, media: str = CSV, available: bool = True) -> str:
    blob = str(derive_blob_id(sha256=sha, size=size))
    connection.execute(text("INSERT INTO blob (blob_id) VALUES (:blob)"), {"blob": blob})
    connection.execute(text("UPDATE blob SET state = 'verifying' WHERE blob_id = :blob"), {"blob": blob})
    if available:
        connection.execute(
            text(
                "UPDATE blob SET state = 'available', sha256 = :sha, size_bytes = :size, "
                "media_type = :media WHERE blob_id = :blob"
            ),
            {"blob": blob, "sha": sha, "size": size, "media": media},
        )
    return blob


def _seed_0025(connection: Any) -> dict[str, str]:
    ids = {
        "project": str(ProjectUid.new()),
        "document": str(DocumentUid.new()),
        "version": str(VersionUid.new()),
        "expert": _user(connection),
        "admin": _user(connection),
    }
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'Школа')"), ids)
    connection.execute(
        text(
            "INSERT INTO document (document_uid, project_uid, display_title, section) "
            "VALUES (:document, :project, 'АР-1', 'AR')"
        ),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
            "source_filename, media_type, byte_size, sha256, page_count) "
            "VALUES (:version, :document, 1, 'АР-1.pdf', 'application/pdf', 1024, :sha, 1)"
        ),
        {**ids, "sha": "c" * 64},
    )
    connection.execute(
        text(
            "INSERT INTO work_assignment (assignment_uid, project_uid, document_uid, "
            "assignee_user_uid, created_by_user_uid) "
            "VALUES ('asg_01ARZ3NDEKTSV4RRFFQ69G5FAV', :project, NULL, :expert, :admin)"
        ),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO work_assignment_event (event_id, assignment_uid, seq, kind, actor_user_uid) "
            "VALUES (:event, 'asg_01ARZ3NDEKTSV4RRFFQ69G5FAV', 1, 'assigned', :admin)"
        ),
        {**ids, "event": str(AuditEventId.new())},
    )
    ids["blob"] = _blob(connection)
    return ids


def _price_list(
    connection: Any,
    ids: dict[str, str],
    uid: str = PRICE_LIST,
    *,
    number: int = 1,
    accepted: int = 1,
    skipped: int = 0,
    **overrides: Any,
) -> None:
    values = {
        "id": uid,
        "project": ids["project"],
        "number": number,
        "user": ids["expert"],
        "blob": ids["blob"],
        "sha": SHA,
        "size": SIZE,
        "media": CSV,
        "format": "csv",
        "filename": "прайс.csv",
        "currency": "RUB",
        "report": '{"report_version": 1}',
        "data": accepted + skipped,
        "accepted": accepted,
        "skipped": skipped,
    }
    values.update(overrides)
    connection.execute(
        text(
            "INSERT INTO price_list_revision (price_list_id, project_uid, revision_number, "
            "uploaded_by_user_uid, blob_id, sha256, size_bytes, media_type, source_format, "
            "source_filename, default_currency, parse_report, data_row_count, "
            "accepted_row_count, skipped_row_count) VALUES (:id, :project, :number, :user, :blob, "
            ":sha, :size, :media, :format, :filename, :currency, CAST(:report AS jsonb), :data, "
            ":accepted, :skipped)"
        ),
        values,
    )


def _position(connection: Any, price_list: str = PRICE_LIST, uid: str = POSITION, **overrides: Any) -> None:
    values = {
        "id": uid,
        "list": price_list,
        "row": 2,
        "code": "К-1",
        "name": "Кабель ВВГнг-LS 3х2,5",
        "mark": None,
        "unit": "м",
        "price": "125.5",
        "currency": "RUB",
        "vendor": None,
        "section": "EOM",
    }
    values.update(overrides)
    connection.execute(
        text(
            "INSERT INTO price_list_position (price_list_position_id, price_list_id, row_number, "
            "code, name, mark, unit, unit_price, currency, vendor, section_code) VALUES (:id, "
            ":list, :row, :code, :name, :mark, :unit, CAST(:price AS numeric), :currency, :vendor, "
            ":section)"
        ),
        values,
    )


def _vendor_list(
    connection: Any,
    ids: dict[str, str],
    uid: str = VENDOR_LIST,
    *,
    entries: int = 1,
    **overrides: Any,
) -> None:
    values = {
        "id": uid,
        "scope": "global",
        "project": None,
        "section": "EOM",
        "mode": "list",
        "number": 1,
        "count": entries,
        "user": ids["admin"],
    }
    values.update(overrides)
    connection.execute(
        text(
            "INSERT INTO vendor_list_revision (vendor_list_id, scope, project_uid, section_code, "
            "mode, revision_number, entry_count, set_by_user_uid) VALUES (:id, :scope, :project, "
            ":section, :mode, :number, :count, :user)"
        ),
        values,
    )
    for ordinal in range(1, entries + 1):
        connection.execute(
            text(
                "INSERT INTO vendor_list_entry (vendor_list_id, ordinal, material, vendor) "
                "VALUES (:id, :ordinal, 'Кабель силовой', :vendor)"
            ),
            {"id": uid, "ordinal": ordinal, "vendor": f"Завод {ordinal}"},
        )


def _refused(engine: Engine, write: Any, *, sqlstate: str) -> None:
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            write(connection)
    assert _sqlstate(caught.value) == sqlstate, caught.value


@pytest.fixture
def at_previous(
    empty_database: Any, foundation_command: Any
) -> Iterator[tuple[Engine, str, dict[str, str]]]:
    url = empty_database.url.render_as_string(hide_password=False)
    upgraded = foundation_command(_alembic("upgrade", PREVIOUS), url)
    assert upgraded.returncode == 0, upgraded.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            ids = _seed_0025(connection)
        yield engine, url, ids
    finally:
        engine.dispose()


@pytest.fixture
def at_head(
    at_previous: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> tuple[Engine, str, dict[str, str]]:
    engine, url, ids = at_previous
    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()
    return engine, url, ids


_SNAPSHOT = (
    "SELECT p.name, d.display_title, d.section, v.sha256, a.assignee_user_uid, "
    "(SELECT count(*) FROM work_assignment_event), b.state, b.sha256, b.size_bytes "
    "FROM project p JOIN document d USING (project_uid) JOIN document_version v USING (document_uid) "
    "JOIN work_assignment a ON a.project_uid = p.project_uid CROSS JOIN blob b"
)


def test_populated_0025_upgrades_and_no_existing_row_changes(
    at_previous: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> None:
    engine, url, ids = at_previous
    with engine.connect() as connection:
        for table in TABLES:
            assert connection.execute(text(f"SELECT to_regclass('{table}')")).scalar_one() is None
        before = tuple(connection.execute(text(_SNAPSHOT)).one())

    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()

    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
        for table in TABLES:
            assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
        after = tuple(connection.execute(text(_SNAPSHOT)).one())
    assert after == before
    assert before[:5] == ("Школа", "АР-1", "AR", "c" * 64, ids["expert"])
    assert before[6:] == ("available", SHA, SIZE)


def test_a_complete_revision_commits_and_every_table_refuses_update_and_delete(
    at_head: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_head
    with engine.begin() as connection:
        _price_list(connection, ids)
        _position(connection)
        _vendor_list(connection, ids)
    for statement in (
        "UPDATE price_list_revision SET source_filename = 'другой.csv'",
        "DELETE FROM price_list_revision",
        "UPDATE price_list_position SET unit_price = 1",
        "DELETE FROM price_list_position",
        "UPDATE vendor_list_revision SET mode = 'list'",
        "DELETE FROM vendor_list_revision",
        "UPDATE vendor_list_entry SET vendor = 'Другой'",
        "DELETE FROM vendor_list_entry",
    ):
        _refused(engine, lambda connection, s=statement: connection.execute(text(s)), sqlstate="AM003")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT unit_price::text, currency, section_code FROM price_list_position")
        ).one() == ("125.5", "RUB", "EOM")


def test_a_revision_without_all_its_positions_is_refused_at_commit(
    at_head: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_head

    def short(connection: Any) -> None:
        _price_list(connection, ids, accepted=2)
        _position(connection)

    def none(connection: Any) -> None:
        _price_list(connection, ids)

    _refused(engine, short, sqlstate="AM001")
    _refused(engine, none, sqlstate="AM001")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM price_list_revision")).scalar_one() == 0


def test_a_vendor_list_without_all_its_entries_is_refused_at_commit(
    at_head: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_head

    def short(connection: Any) -> None:
        _vendor_list(connection, ids, entries=1, count=2)

    _refused(engine, short, sqlstate="AM001")
    with engine.begin() as connection:
        _vendor_list(connection, ids, entries=0)  # an explicit empty list is a valid revision


def test_a_revision_is_bound_only_to_an_available_blob_with_its_digest_and_size(
    at_head: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_head
    with engine.begin() as connection:
        verifying = _blob(connection, sha="e" * 64, size=10, available=False)

    def bind(**overrides: Any) -> Any:
        def write(connection: Any) -> None:
            _price_list(connection, ids, **overrides)
            _position(connection)

        return write

    _refused(engine, bind(blob=verifying, sha="e" * 64, size=10), sqlstate="AM001")
    _refused(engine, bind(sha="f" * 64), sqlstate="AM001")
    _refused(engine, bind(size=SIZE + 1), sqlstate="AM001")
    with engine.begin() as connection:
        bind()(connection)


@pytest.mark.parametrize(
    ("table", "overrides"),
    [
        ("revision", {"id": "prl_short"}),
        ("revision", {"id": "plr_01ARZ3NDEKTSV4RRFFQ69G5FAV"}),
        ("revision", {"project": "prj_bad"}),
        ("revision", {"user": "usr_bad"}),
        ("revision", {"number": 0}),
        ("revision", {"sha": "D" * 64}),
        ("revision", {"media": "application/pdf"}),
        ("revision", {"format": "xls"}),
        ("revision", {"format": "xlsx"}),  # a CSV media type with the XLSX format
        ("revision", {"filename": ""}),
        ("revision", {"filename": "a/b.csv"}),
        ("revision", {"filename": "a\\b.csv"}),
        ("revision", {"filename": "x" * 256}),
        ("revision", {"currency": "rub"}),
        ("revision", {"currency": "RUBL"}),
        ("revision", {"report": "[]"}),
        ("revision", {"data": 3}),
        ("revision", {"accepted": 0, "data": 0}),
        ("revision", {"skipped": -1, "data": 0}),
        ("revision", {"accepted": 20001, "data": 20001}),
        ("position", {"id": "prp_bad"}),
        ("position", {"row": 0}),
        ("position", {"code": ""}),
        ("position", {"name": ""}),
        ("position", {"name": "я" * 2001}),
        ("position", {"unit": ""}),
        ("position", {"unit": "м" * 51}),
        ("position", {"price": "0"}),
        ("position", {"price": "-1"}),
        ("position", {"price": "0.0000001"}),
        ("position", {"price": "100000000000000"}),
        ("position", {"currency": "руб"}),
        ("position", {"section": "XX"}),
        ("position", {"vendor": ""}),
        ("vendor", {"id": "vnl_bad"}),
        ("vendor", {"scope": "team"}),
        ("vendor", {"scope": "global", "project": "PROJECT"}),
        ("vendor", {"scope": "project"}),  # a project scope with no project
        ("vendor", {"section": "XX"}),
        ("vendor", {"mode": "replace"}),
        ("vendor", {"mode": "inherit"}),  # a global revision may not inherit
        ("vendor", {"number": 0}),
    ],
)
def test_the_checks_refuse_malformed_rows(
    at_head: tuple[Engine, str, dict[str, str]], table: str, overrides: dict[str, Any]
) -> None:
    engine, _, ids = at_head
    resolved = {key: ids["project"] if value == "PROJECT" else value for key, value in overrides.items()}

    def write(connection: Any) -> None:
        if table == "revision":
            _price_list(connection, ids, **resolved)
            _position(connection)
        elif table == "position":
            _price_list(connection, ids)
            _position(connection, **resolved)
        else:
            entries = 0 if resolved.get("mode") == "inherit" else 1
            _vendor_list(connection, ids, entries=entries, **resolved)

    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            write(connection)
    assert _sqlstate(caught.value) in {"23514", "AM001", "23503"}, caught.value


def test_well_formed_rows_at_their_bounds_are_admitted(at_head: tuple[Engine, str, dict[str, str]]) -> None:
    engine, _, ids = at_head
    with engine.begin() as connection:
        xlsx_blob = _blob(connection, sha="a" * 64, size=4096, media=XLSX)
        _price_list(
            connection,
            ids,
            OTHER_PRICE_LIST,
            blob=xlsx_blob,
            sha="a" * 64,
            size=4096,
            media=XLSX,
            format="xlsx",
            filename="x" * 255,
            currency=None,
            accepted=2,
            skipped=19998,
        )
        _position(
            connection, OTHER_PRICE_LIST, POSITION, price="99999999999999.999999", name="я" * 2000,
            unit="м" * 50, section=None, code=None,
        )
        _position(connection, OTHER_PRICE_LIST, OTHER_POSITION, row=3, price="0.000001", currency="USD")
        _vendor_list(
            connection, ids, OTHER_VENDOR_LIST, entries=0, scope="project", project=ids["project"],
            mode="inherit",
        )
    with engine.connect() as connection:
        prices = connection.execute(
            text("SELECT unit_price::text FROM price_list_position ORDER BY row_number")
        ).scalars().all()
    assert prices == ["99999999999999.999999", "0.000001"]


def test_revision_numbers_are_unique_per_scope(at_head: tuple[Engine, str, dict[str, str]]) -> None:
    engine, _, ids = at_head
    with engine.begin() as connection:
        _price_list(connection, ids)
        _position(connection)
        _vendor_list(connection, ids)
        _vendor_list(
            connection, ids, OTHER_VENDOR_LIST, scope="project", project=ids["project"],
        )  # the same number in another scope

    def second_price_list(connection: Any) -> None:
        _price_list(connection, ids, OTHER_PRICE_LIST)
        _position(connection, OTHER_PRICE_LIST, OTHER_POSITION)

    def second_global(connection: Any) -> None:
        _vendor_list(connection, ids, "vnl_01ARZ3NDEKTSV4RRFFQ69G5FAX")

    _refused(engine, second_price_list, sqlstate="23505")
    _refused(engine, second_global, sqlstate="23505")


@pytest.mark.parametrize("column", ["uploaded_by_user_uid", "set_by_user_uid"])
def test_each_account_column_alone_blocks_deleting_the_account(
    at_head: tuple[Engine, str, dict[str, str]], column: str
) -> None:
    engine, _, ids = at_head
    with engine.begin() as connection:
        holder = _user(connection)
        if column == "uploaded_by_user_uid":
            _price_list(connection, ids, user=holder)
            _position(connection)
        else:
            _vendor_list(connection, ids, user=holder)
    _refused(
        engine,
        lambda connection: connection.execute(
            text("DELETE FROM app_user WHERE user_uid = :u"), {"u": holder}
        ),
        sqlstate="23503",
    )


def test_the_project_and_the_blob_cannot_be_deleted_under_a_price_list(
    at_head: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_head
    with engine.begin() as connection:
        lone_project = str(ProjectUid.new())
        connection.execute(
            text("INSERT INTO project (project_uid, name) VALUES (:p, 'Склад')"), {"p": lone_project}
        )
        lone_blob = _blob(connection, sha="b" * 64, size=77)
        _price_list(connection, ids, project=lone_project, blob=lone_blob, sha="b" * 64, size=77)
        _position(connection)
    _refused(
        engine,
        lambda connection: connection.execute(
            text("DELETE FROM project WHERE project_uid = :p"), {"p": lone_project}
        ),
        sqlstate="23503",
    )
    _refused(
        engine,
        lambda connection: connection.execute(
            text("DELETE FROM blob WHERE blob_id = :b"), {"b": lone_blob}
        ),
        sqlstate="23503",
    )


def test_the_downgrade_drops_only_this_revision_and_the_head_upgrades_again(
    at_head: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> None:
    engine, url, ids = at_head
    with engine.begin() as connection:
        _price_list(connection, ids)
        _position(connection)
        _vendor_list(connection, ids)
        before = tuple(connection.execute(text(_SNAPSHOT)).one())

    downgraded = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert downgraded.returncode == 0, downgraded.describe()
    assert "exist nowhere else and are dropped" in downgraded.stderr + downgraded.stdout

    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
        for table in TABLES:
            assert connection.execute(text(f"SELECT to_regclass('{table}')")).scalar_one() is None
        for function in FUNCTIONS:
            assert connection.execute(
                text("SELECT count(*) FROM pg_proc WHERE proname = :f"), {"f": function}
            ).scalar_one() == 0
        assert connection.execute(
            text("SELECT count(*) FROM pg_proc WHERE proname = 'am_immutable_row'")
        ).scalar_one() == 1
        assert tuple(connection.execute(text(_SNAPSHOT)).one()) == before

    reupgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert reupgraded.returncode == 0, reupgraded.describe()
    with engine.connect() as connection:
        for table in TABLES:
            assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
