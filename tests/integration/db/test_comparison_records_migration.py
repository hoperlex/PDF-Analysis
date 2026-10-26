"""`COMPARE-PERSISTED-SUMMARY-01`: ``0035_comparison_records`` on a populated ``0034`` database.

``comparison_sheet_link`` is an append-only history of the approvals and withdrawals of sheet
pairings. Against real PostgreSQL rows, written through plain INSERTs:

* **the step adds the table and changes no stored row**: a populated ``0034`` database keeps every
  row of the tables it had;
* **the database holds the rules, not only the command**: UPDATE and DELETE are refused
  (``AM003``), revision n needs n - 1, a pair has one comparison identity, the pair is an older and
  a newer version of one document of the project with both pages inside them, a page belongs to at
  most one active link, at most 32 links are active, and a withdrawal ends exactly the approval it
  repeats and only once;
* **the shape**: formats, the event vocabulary, an approval carries its seal;
* **the downgrade is refused while any row exists, and only then**; without a row it drops the
  table and the upgrade runs again.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    CommandId,
    ComparisonId,
    DocumentUid,
    ProjectUid,
    SheetLinkId,
    VersionUid,
)
from tests.support.expected_facts import FACTS

THIS = "0035_comparison_records"
PREVIOUS = "0034_pass_scope_all_sections"
PAGES = 100
SHA_A, SHA_B, SHA_C, SEAL = "a" * 64, "b" * 64, "c" * 64, "d" * 64
USER = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _sqlstate(error: DBAPIError) -> str:
    return str(getattr(error.orig, "sqlstate", "") or "")


def _seed(connection: Any) -> dict[str, str]:
    """Two projects; in the first one a document with three versions and one of another document."""
    ids: dict[str, str] = {
        "project": str(ProjectUid.new()), "other_project": str(ProjectUid.new()),
        "document": str(DocumentUid.new()), "other_document": str(DocumentUid.new()),
        "foreign_document": str(DocumentUid.new()),
        "v1": str(VersionUid.new()), "v2": str(VersionUid.new()), "v3": str(VersionUid.new()),
        "v_other": str(VersionUid.new()), "v_foreign": str(VersionUid.new()),
    }
    for key in ("project", "other_project"):
        connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Школа')"),
                           {"p": ids[key]})
    for key, project in (("document", "project"), ("other_document", "project"),
                         ("foreign_document", "other_project")):
        connection.execute(
            text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'К')"),
            {"d": ids[key], "p": ids[project]},
        )
    for key, document, ordinal in (("v1", "document", 1), ("v2", "document", 2), ("v3", "document", 3),
                                   ("v_other", "other_document", 1), ("v_foreign", "foreign_document", 1)):
        connection.execute(
            text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
                 "byte_size, sha256, page_count) VALUES (:v, :d, :o, 'application/pdf', 1024, :s, :n)"),
            {"v": ids[key], "d": ids[document], "o": ordinal, "s": SHA_C, "n": PAGES},
        )
    return ids


def _command(connection: Any) -> str:
    command = str(CommandId.new())
    connection.execute(
        text("INSERT INTO command_record (command_id, command_type, idempotency_key, "
             "payload_fingerprint) VALUES (:c, 'approve_sheet_pairing', :k, :f)"),
        {"c": command, "k": command.lower().replace("_", "-"), "f": SHA_A},
    )
    return command


def _link(connection: Any, ids: dict[str, str], comparison: str, revision: int, *,
          kind: str = "approved", link: str | None = None, source: int = 1, target: int = 1,
          source_version: str = "v1", target_version: str = "v2", document: str = "document",
          project: str = "project", seal: str | None = SEAL, source_sha: str = SHA_A,
          target_sha: str = SHA_B, suggestion: str = SHA_C, label: str = "Иванов И.") -> str:
    link = link or str(SheetLinkId.new())
    connection.execute(
        text("INSERT INTO comparison_sheet_link (comparison_id, link_revision, event_kind, "
             "sheet_link_id, project_uid, document_uid, source_version_uid, target_version_uid, "
             "source_page_number, target_page_number, source_page_text_sha256, "
             "target_page_text_sha256, suggestion_sha256, raw_evidence_seal_sha256, "
             "actor_user_uid, actor_label, command_id) VALUES (:cmp, :rev, :kind, :link, :project, "
             ":document, :sv, :tv, :sp, :tp, :ssha, :tsha, :sug, :seal, :user, :label, :cmd)"),
        {"cmp": comparison, "rev": revision, "kind": kind, "link": link,
         "project": ids[project], "document": ids[document], "sv": ids[source_version],
         "tv": ids[target_version], "sp": source, "tp": target, "ssha": source_sha,
         "tsha": target_sha, "sug": suggestion, "seal": seal, "user": USER, "label": label,
         "cmd": _command(connection)},
    )
    return link


def _refused(engine: Engine, write: Any, sqlstate: str = "AM001") -> None:
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            write(connection)
    assert _sqlstate(caught.value) == sqlstate, caught.value


def _count(engine: Engine, table: str = "comparison_sheet_link") -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


def _version(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one())


def _upgrade(foundation_command: Any, url: str, revision: str) -> None:
    done = foundation_command(_alembic("upgrade", revision), url)
    assert done.returncode == 0, done.describe()


@pytest.fixture
def at_previous(empty_database: Any, foundation_command: Any) -> Iterator[tuple[Engine, str, dict[str, str]]]:
    url = empty_database.url.render_as_string(hide_password=False)
    _upgrade(foundation_command, url, PREVIOUS)
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            ids = _seed(connection)
        yield engine, url, ids
    finally:
        engine.dispose()


@pytest.fixture
def at_this(at_previous: tuple[Engine, str, dict[str, str]], foundation_command: Any):
    engine, url, ids = at_previous
    _upgrade(foundation_command, url, THIS)
    return engine, url, ids


# -- the step -----------------------------------------------------------------------------------


def test_the_head_of_the_tree_is_this_revision_or_a_later_one() -> None:
    assert FACTS.migration_head >= THIS


def test_the_step_adds_the_table_and_changes_no_stored_row(
    at_previous: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> None:
    engine, url, _ = at_previous
    tables = ("project", "document", "document_version", "command_record", "audit_event")
    before = {table: _count(engine, table) for table in tables}
    with engine.connect() as connection:
        assert connection.execute(text("SELECT to_regclass('public.comparison_sheet_link')")).scalar_one() is None
    _upgrade(foundation_command, url, THIS)
    assert _version(engine) == THIS
    assert {table: _count(engine, table) for table in tables} == before
    assert _count(engine) == 0


# -- the history --------------------------------------------------------------------------------


def test_an_approval_a_second_link_and_a_withdrawal_are_numbered_without_a_gap(
    at_this: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_this
    comparison = str(ComparisonId.new())
    with engine.begin() as connection:
        first = _link(connection, ids, comparison, 1, source=1, target=1)
        _link(connection, ids, comparison, 2, source=2, target=2)
        _link(connection, ids, comparison, 3, kind="withdrawn", link=first, source=1, target=1)
        # the freed pages take a new link
        _link(connection, ids, comparison, 4, source=1, target=1)
    assert _count(engine) == 4


@pytest.mark.parametrize("revision", [2, 5])
def test_the_first_row_of_a_comparison_is_revision_one(
    at_this: tuple[Engine, str, dict[str, str]], revision: int
) -> None:
    engine, _, ids = at_this
    _refused(engine, lambda c: _link(c, ids, str(ComparisonId.new()), revision))


def test_revision_n_needs_n_minus_one(at_this: tuple[Engine, str, dict[str, str]]) -> None:
    engine, _, ids = at_this
    comparison = str(ComparisonId.new())
    with engine.begin() as connection:
        _link(connection, ids, comparison, 1)
    _refused(engine, lambda c: _link(c, ids, comparison, 3, source=2, target=2))   # a gap
    _refused(engine, lambda c: _link(c, ids, comparison, 1, source=2, target=2))   # a repeat
    assert _count(engine) == 1


def test_one_pair_of_versions_has_one_comparison_identity(
    at_this: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_this
    with engine.begin() as connection:
        _link(connection, ids, str(ComparisonId.new()), 1)
    _refused(engine, lambda c: _link(c, ids, str(ComparisonId.new()), 1, source=2, target=2))
    with engine.begin() as connection:  # another pair is another comparison
        _link(connection, ids, str(ComparisonId.new()), 1, source_version="v2", target_version="v3")


def test_every_row_of_a_comparison_names_the_pair_its_first_row_named(
    at_this: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_this
    comparison = str(ComparisonId.new())
    with engine.begin() as connection:
        _link(connection, ids, comparison, 1)
    _refused(engine, lambda c: _link(c, ids, comparison, 2, source=2, target=2,
                                     source_version="v2", target_version="v3"))


@pytest.mark.parametrize(
    ("changes", "why"),
    [
        ({"source_version": "v2", "target_version": "v1"}, "the source is the newer version"),
        ({"source_version": "v_other", "target_version": "v2"}, "a version of another document"),
        ({"project": "other_project"}, "the document is not of that project"),
        ({"source": PAGES + 1}, "a source page beyond the version"),
        ({"target": PAGES + 1}, "a target page beyond the version"),
    ],
)
def test_the_pair_must_be_two_versions_of_one_document_of_the_project(
    at_this: tuple[Engine, str, dict[str, str]], changes: dict[str, Any], why: str
) -> None:
    engine, _, ids = at_this
    _refused(engine, lambda c: _link(c, ids, str(ComparisonId.new()), 1, **changes))
    assert _count(engine) == 0, why


def test_a_version_pair_with_a_foreign_project_document_is_refused(
    at_this: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_this
    _refused(engine, lambda c: _link(c, ids, str(ComparisonId.new()), 1, source_version="v_foreign",
                                     target_version="v2"))


def test_a_page_belongs_to_at_most_one_active_link(at_this: tuple[Engine, str, dict[str, str]]) -> None:
    engine, _, ids = at_this
    comparison = str(ComparisonId.new())
    with engine.begin() as connection:
        _link(connection, ids, comparison, 1, source=3, target=4)
    _refused(engine, lambda c: _link(c, ids, comparison, 2, source=3, target=5))   # source held
    _refused(engine, lambda c: _link(c, ids, comparison, 2, source=6, target=4))   # target held
    with engine.begin() as connection:
        _link(connection, ids, comparison, 2, source=6, target=5)
    assert _count(engine) == 2


def test_the_thirty_third_active_link_is_refused_and_a_withdrawal_frees_a_place(
    at_this: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_this
    comparison = str(ComparisonId.new())
    links: list[str] = []
    with engine.begin() as connection:
        for page in range(1, 33):
            links.append(_link(connection, ids, comparison, page, source=page, target=page))
    _refused(engine, lambda c: _link(c, ids, comparison, 33, source=33, target=33))
    with engine.begin() as connection:
        _link(connection, ids, comparison, 33, kind="withdrawn", link=links[0], source=1, target=1)
        _link(connection, ids, comparison, 34, source=33, target=33)
    assert _count(engine) == 34


def test_a_withdrawal_ends_exactly_the_approval_it_repeats_and_only_once(
    at_this: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_this
    comparison = str(ComparisonId.new())
    with engine.begin() as connection:
        link = _link(connection, ids, comparison, 1, source=4, target=4)
    unknown = str(SheetLinkId.new())
    _refused(engine, lambda c: _link(c, ids, comparison, 2, kind="withdrawn", link=unknown, source=4, target=4))
    for changes in ({"source": 5}, {"target": 5}, {"source_sha": SHA_B}, {"target_sha": SHA_A},
                    {"suggestion": SHA_A}):
        _refused(engine, lambda c, ch=changes: _link(
            c, ids, comparison, 2, kind="withdrawn", link=link, **{"source": 4, "target": 4} | ch))
    with engine.begin() as connection:
        _link(connection, ids, comparison, 2, kind="withdrawn", link=link, source=4, target=4, seal=None)
    _refused(engine, lambda c: _link(c, ids, comparison, 3, kind="withdrawn", link=link,
                                     source=4, target=4), "23505")
    # the same link cannot be approved twice either
    _refused(engine, lambda c: _link(c, ids, comparison, 3, link=link, source=4, target=4), "23505")


# -- append-only --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE comparison_sheet_link SET actor_label = 'Другой'",
        "UPDATE comparison_sheet_link SET event_kind = 'withdrawn'",
        "UPDATE comparison_sheet_link SET raw_evidence_seal_sha256 = NULL",
        "DELETE FROM comparison_sheet_link",
    ],
)
def test_a_stored_row_cannot_be_updated_or_deleted(
    at_this: tuple[Engine, str, dict[str, str]], statement: str
) -> None:
    engine, _, ids = at_this
    with engine.begin() as connection:
        _link(connection, ids, str(ComparisonId.new()), 1)
    _refused(engine, lambda c: c.execute(text(statement)), "AM003")
    assert _count(engine) == 1


# -- the shape ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "sqlstate"),
    [
        ({"kind": "approved", "seal": None}, "23514"),       # an approval carries its seal
        ({"seal": "D" * 64}, "23514"), ({"seal": "d" * 63}, "23514"),
        ({"source_sha": "z" * 64}, "23514"), ({"target_sha": "b" * 63}, "23514"),
        ({"suggestion": ""}, "23514"),
        ({"label": ""}, "23514"), ({"label": " Иванов"}, "23514"), ({"label": "И" * 129}, "23514"),
        ({"source": 0}, "23514"), ({"target": 0}, "23514"),
        # The chain trigger fires before the CHECKs, and it refuses these first.
        ({"kind": "retracted"}, "AM001"),                    # no approval to withdraw
        ({"source": 501}, "AM001"),                          # beyond the version
    ],
)
def test_the_shape_is_checked_by_the_database(
    at_this: tuple[Engine, str, dict[str, str]], changes: dict[str, Any], sqlstate: str
) -> None:
    engine, _, ids = at_this
    _refused(engine, lambda c: _link(c, ids, str(ComparisonId.new()), 1, **changes), sqlstate)
    assert _count(engine) == 0


def test_the_event_vocabulary_is_closed_by_a_check_as_well(
    at_this: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, _ = at_this
    with engine.connect() as connection:
        definition = connection.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'ck_comparison_sheet_link_event_kind'")).scalar_one()
    assert "approved" in definition and "withdrawn" in definition and "retracted" not in definition


@pytest.mark.parametrize("column", ["comparison_id", "sheet_link_id", "actor_user_uid", "command_id"])
def test_an_identity_must_have_its_prefix_and_a_ulid(
    at_this: tuple[Engine, str, dict[str, str]], column: str
) -> None:
    engine, _, ids = at_this

    bad = {"comparison_id": "cmp_x", "sheet_link_id": "sln_x", "actor_user_uid": "usr_x",
           "command_id": "cmd_x"}[column]

    def insert(connection: Any) -> None:
        command = _command(connection)
        values = {
            "comparison_id": str(ComparisonId.new()), "sheet_link_id": str(SheetLinkId.new()),
            "actor_user_uid": USER, "command_id": command,
        }
        values[column] = bad
        connection.execute(
            text("INSERT INTO comparison_sheet_link (comparison_id, link_revision, event_kind, "
                 "sheet_link_id, project_uid, document_uid, source_version_uid, target_version_uid, "
                 "source_page_number, target_page_number, source_page_text_sha256, "
                 "target_page_text_sha256, suggestion_sha256, raw_evidence_seal_sha256, "
                 "actor_user_uid, actor_label, command_id) VALUES (:comparison_id, 1, 'approved', "
                 ":sheet_link_id, :p, :d, :sv, :tv, 1, 1, :a, :b, :c, :d2, :actor_user_uid, 'И', "
                 ":command_id)"),
            values | {"p": ids["project"], "d": ids["document"], "sv": ids["v1"], "tv": ids["v2"],
                      "a": SHA_A, "b": SHA_B, "c": SHA_C, "d2": SEAL},
        )

    # command_id is also a foreign key: a bad value is refused by the CHECK first (23514) or, for
    # an unknown well-formed id, by the key; the others only by the CHECK.
    _refused(engine, insert, "23514")


# -- the downgrade ------------------------------------------------------------------------------


def test_the_downgrade_is_refused_while_a_row_exists_and_only_then(
    at_this: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> None:
    engine, url, ids = at_this
    comparison = str(ComparisonId.new())
    with engine.begin() as connection:
        _link(connection, ids, comparison, 1)

    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0, refused.describe()
    assert "0035 downgrade refused: 1 sheet link event(s)" in refused.stderr, refused.stderr
    assert _version(engine) == THIS and _count(engine) == 1  # a refusal changes nothing


def test_without_a_row_the_downgrade_drops_the_table_and_the_upgrade_runs_again(
    at_this: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> None:
    engine, url, ids = at_this
    down = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert down.returncode == 0, down.describe()
    assert _version(engine) == PREVIOUS
    with engine.connect() as connection:
        assert connection.execute(text("SELECT to_regclass('public.comparison_sheet_link')")).scalar_one() is None
        assert connection.execute(text(
            "SELECT count(*) FROM pg_proc WHERE proname = 'am_check_comparison_sheet_link_chain'"
        )).scalar_one() == 0
    _upgrade(foundation_command, url, THIS)
    with engine.begin() as connection:
        _link(connection, ids, str(ComparisonId.new()), 1)
    assert _count(engine) == 1
