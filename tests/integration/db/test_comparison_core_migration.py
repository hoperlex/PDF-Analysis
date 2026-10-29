"""`CMP-SEAL-C1`: ``0039_comparison_core`` on a populated ``0038`` database.

Seven tables, two columns of existing tables, and one data step: every **active** approval of
``comparison_sheet_link`` (``0035``) becomes a ``link`` edit with its ``0035`` ids in the provenance
(ADR-0025 decision 13, ``Q-CMP-8``). Against real PostgreSQL rows written through plain INSERTs, each rule shown
failing:

* **the data step** migrates the active approvals only, in the order they were made, never deletes or edits a
  ``0035`` row, and is idempotent (a second run adds nothing);
* **decision 15**: a sheet-pair result is unique by content within a project, and only within it;
* **decisions 3 and 14**: builds and edits are numbered without a gap, are immutable, and an edit has the shape
  its kind needs; an undo names one earlier edit, once, and never an undo;
* **decision 21**: a project has one live series per document; the series, transition and pair move only along
  their declared edges; a transition lists two versions of the series' document; a pair's pages are those of its
  transition;
* **decision 7**: every new table is reachable from ``project`` by foreign keys;
* **the new columns**: ``comparison_work.comparison_series_id`` and ``comparison_upload.compare_after_preparation``
  are frozen once written;
* **the downgrade** is refused while any row exists other than a migrated edit, and gives back the ``0038`` schema.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid, new_ulid
from tests.support.expected_facts import FACTS

THIS = "0039_comparison_core"
PREVIOUS = "0038_comparison_foundation"
ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SHA = "a" * 64
TABLES = (
    "comparison_matrix", "comparison_matrix_edit", "comparison_ai_link", "comparison_series",
    "comparison_transition", "comparison_sheet_pair_result", "comparison_sheet_pair",
)
MIGRATION = Path(__file__).resolve().parents[3] / "db/migrations/versions/20261028_0039_comparison_core.py"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _sqlstate(error: DBAPIError) -> str:
    return str(getattr(error.orig, "sqlstate", "") or "")


def _upgrade(foundation_command: Any, url: str, revision: str) -> None:
    done = foundation_command(_alembic("upgrade", revision), url)
    assert done.returncode == 0, done.describe()


def _refused(engine: Engine, write: Any, sqlstate: str = "AM001") -> None:
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            write(connection)
    assert _sqlstate(caught.value) == sqlstate, caught.value


def _count(engine: Engine, table: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


def _tables(engine: Engine) -> set[str]:
    with engine.connect() as connection:
        return {row[0] for row in connection.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' "
            "AND table_type = 'BASE TABLE'"))}


def _id(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def _project(connection: Any, pages: int = 5, versions: int = 3) -> dict[str, Any]:
    ids: dict[str, Any] = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()), "versions": []}
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'cmp')"), ids)
    connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                            "VALUES (:document, :project, 'D')"), ids)
    for number in range(1, versions + 1):
        version = str(VersionUid.new())
        ids["versions"].append(version)
        connection.execute(text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
            "byte_size, sha256, page_count) VALUES (:v, :document, :n, 'application/pdf', 1, :sha, :pages)"),
            {"v": version, "document": ids["document"], "n": number, "sha": SHA, "pages": pages})
    return ids


def _command(connection: Any, kind: str = "approve_sheet_pairing") -> str:
    command = _id("cmd")
    connection.execute(text(
        "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
        "VALUES (:c, :t, :k, :f)"), {"c": command, "t": kind, "k": _id("k")[:20], "f": SHA})
    return command


def _link_event(connection: Any, ids: dict[str, Any], *, comparison: str, revision: int, kind: str, link: str,
                source: int, target: int, pages: tuple[int, int], offset: int) -> None:
    connection.execute(text(
        "INSERT INTO comparison_sheet_link (comparison_id, link_revision, event_kind, sheet_link_id, project_uid, "
        "document_uid, source_version_uid, target_version_uid, source_page_number, target_page_number, "
        "source_page_text_sha256, target_page_text_sha256, suggestion_sha256, raw_evidence_seal_sha256, "
        "actor_user_uid, actor_label, command_id, decided_at) VALUES (:cmp, :rev, :kind, :link, :project, "
        ":document, :s, :t, :sp, :tp, :sha, :sha, :sha, :seal, :actor, 'Эксперт', :command, "
        "now() + make_interval(secs => :offset))"),
        {"cmp": comparison, "rev": revision, "kind": kind, "link": link, "project": ids["project"],
         "document": ids["document"], "s": ids["versions"][source], "t": ids["versions"][target],
         "sp": pages[0], "tp": pages[1], "sha": SHA, "seal": SHA if kind == "approved" else None,
         "actor": ACTOR, "command": _command(connection), "offset": offset})


@pytest.fixture
def at_previous(empty_database: Any, foundation_command: Any) -> Iterator[tuple[Engine, str]]:
    url = empty_database.url.render_as_string(hide_password=False)
    _upgrade(foundation_command, url, PREVIOUS)
    engine = create_database_engine(empty_database)
    try:
        yield engine, url
    finally:
        engine.dispose()


@pytest.fixture
def at_this(at_previous: tuple[Engine, str], foundation_command: Any) -> tuple[Engine, str]:
    engine, url = at_previous
    _upgrade(foundation_command, url, THIS)
    return engine, url


def _seed_approvals(engine: Engine) -> dict[str, Any]:
    """Three approvals, one of them withdrawn, over two pairs of versions of one document, plus one in another."""
    with engine.begin() as connection:
        ids = _project(connection)
        other = _project(connection)
        cmp_a, cmp_b, cmp_c = _id("cmp"), _id("cmp"), _id("cmp")
        links = [_id("sln") for _ in range(4)]
        _link_event(connection, ids, comparison=cmp_a, revision=1, kind="approved", link=links[0],
                    source=0, target=1, pages=(1, 1), offset=1)
        _link_event(connection, ids, comparison=cmp_a, revision=2, kind="approved", link=links[1],
                    source=0, target=1, pages=(2, 3), offset=2)
        _link_event(connection, ids, comparison=cmp_a, revision=3, kind="withdrawn", link=links[1],
                    source=0, target=1, pages=(2, 3), offset=3)
        _link_event(connection, ids, comparison=cmp_b, revision=1, kind="approved", link=links[2],
                    source=1, target=2, pages=(4, 4), offset=4)
        _link_event(connection, other, comparison=cmp_c, revision=1, kind="approved", link=links[3],
                    source=0, target=2, pages=(1, 5), offset=5)
    return {"ids": ids, "other": other, "links": links, "comparisons": (cmp_a, cmp_b, cmp_c)}


def _old_rows(engine: Engine) -> list[Any]:
    with engine.connect() as connection:
        return [tuple(row) for row in connection.execute(text(
            "SELECT * FROM comparison_sheet_link ORDER BY comparison_id, link_revision"))]


# -- the step -----------------------------------------------------------------------------------


def test_the_head_of_the_tree_is_this_revision_or_a_later_one() -> None:
    assert FACTS.migration_head >= THIS


def test_the_revision_id_fits_the_version_column() -> None:
    assert len(THIS) <= 32


def test_the_step_adds_the_objects_and_changes_no_stored_row(
    at_previous: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_previous
    with engine.begin() as connection:
        _project(connection)
    before = {table: _count(engine, table) for table in ("project", "document", "document_version")}
    assert not set(TABLES) & _tables(engine)
    _upgrade(foundation_command, url, THIS)
    assert set(TABLES) <= _tables(engine)
    assert {table: _count(engine, table) for table in before} == before
    assert all(_count(engine, table) == 0 for table in TABLES)
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT column_name, column_default FROM information_schema.columns WHERE table_name = 'comparison_upload' "
            "AND column_name = 'compare_after_preparation'")).one()[1] == "false"
        assert connection.execute(text(
            "SELECT is_nullable FROM information_schema.columns WHERE table_name = 'comparison_work' "
            "AND column_name = 'comparison_series_id'")).scalar_one() == "YES"


# -- the data step (ADR-0025 decision 13, Q-CMP-8) ---------------------------------------------------------


def test_every_active_approval_becomes_one_link_edit_with_its_0035_ids_and_no_0035_row_is_touched(
    at_previous: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_previous
    seeded = _seed_approvals(engine)
    old = _old_rows(engine)
    _upgrade(foundation_command, url, THIS)
    assert _old_rows(engine) == old, "a 0035 row was changed or deleted"
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT document_uid, edit_no, kind, source, page_version_uid, page_number, other_version_uid, "
            "other_page_number, provenance, actor_user_uid, actor_label, command_id, order_id "
            "FROM comparison_matrix_edit ORDER BY document_uid, edit_no")).mappings().all()
    ids, other = seeded["ids"], seeded["other"]
    cmp_a, cmp_b, cmp_c = seeded["comparisons"]
    by_document = {}
    for row in rows:
        by_document.setdefault(row["document_uid"], []).append(row)
    assert set(by_document) == {ids["document"], other["document"]}
    first, second = by_document[ids["document"]]
    assert [first["edit_no"], second["edit_no"]] == [1, 2]
    assert (first["kind"], first["source"], first["command_id"], first["order_id"]) == (
        "link", "migrated_sheet_link", None, None)
    assert (first["page_version_uid"], first["page_number"], first["other_version_uid"], first["other_page_number"]) \
        == (ids["versions"][0], 1, ids["versions"][1], 1)
    assert (second["page_version_uid"], second["page_number"], second["other_version_uid"],
            second["other_page_number"]) == (ids["versions"][1], 4, ids["versions"][2], 4)
    assert first["provenance"]["sheet_link_id"] == seeded["links"][0]
    assert first["provenance"]["comparison_id"] == cmp_a and first["provenance"]["link_revision"] == 1
    assert second["provenance"]["sheet_link_id"] == seeded["links"][2]
    assert second["provenance"]["comparison_id"] == cmp_b
    assert (first["actor_user_uid"], first["actor_label"]) == (ACTOR, "Эксперт")
    (third,) = by_document[other["document"]]
    assert third["edit_no"] == 1 and third["provenance"]["sheet_link_id"] == seeded["links"][3]
    assert third["provenance"]["comparison_id"] == cmp_c
    withdrawn = {row["provenance"]["sheet_link_id"] for row in rows}
    assert seeded["links"][1] not in withdrawn, "a withdrawn approval was migrated"


def test_the_data_step_is_idempotent_a_second_run_adds_nothing(
    at_previous: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_previous
    _seed_approvals(engine)
    _upgrade(foundation_command, url, THIS)
    assert _count(engine, "comparison_matrix_edit") == 3
    spec = importlib.util.spec_from_file_location("migration_0039", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            module._migrate_sheet_links()
    assert _count(engine, "comparison_matrix_edit") == 3


def test_a_migrated_approval_cannot_be_inserted_twice(at_previous: tuple[Engine, str], foundation_command: Any) -> None:
    """The unique index is the backstop of the idempotence: shown failing."""
    engine, url = at_previous
    _seed_approvals(engine)
    _upgrade(foundation_command, url, THIS)
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT project_uid, document_uid, page_version_uid, page_number, other_version_uid, other_page_number, "
            "provenance, actor_user_uid, actor_label FROM comparison_matrix_edit ORDER BY edit_no LIMIT 1")).mappings().one()

    def duplicate(connection: Any) -> None:
        connection.execute(text(
            "INSERT INTO comparison_matrix_edit (comparison_matrix_edit_id, project_uid, document_uid, edit_no, kind, "
            "source, page_version_uid, page_number, other_version_uid, other_page_number, provenance, actor_user_uid, "
            "actor_label) VALUES (:e, :p, :d, 99, 'link', 'migrated_sheet_link', :pv, :pn, :ov, :on, "
            "CAST(:prov AS jsonb), :a, :l)"),
            {"e": _id("cme"), "p": row["project_uid"], "d": row["document_uid"], "pv": row["page_version_uid"],
             "pn": row["page_number"], "ov": row["other_version_uid"], "on": row["other_page_number"],
             "prov": json.dumps(row["provenance"]), "a": row["actor_user_uid"], "l": row["actor_label"]})

    _refused(engine, duplicate, "AM001")  # the chain refuses edit_no 99 first; the index is shown below
    with engine.connect() as connection:
        number = int(connection.execute(text("SELECT max(edit_no) FROM comparison_matrix_edit WHERE document_uid = :d"),
                                        {"d": row["document_uid"]}).scalar_one())

    def duplicate_in_order(connection: Any) -> None:
        connection.execute(text(
            "INSERT INTO comparison_matrix_edit (comparison_matrix_edit_id, project_uid, document_uid, edit_no, kind, "
            "source, page_version_uid, page_number, other_version_uid, other_page_number, provenance, actor_user_uid, "
            "actor_label) VALUES (:e, :p, :d, :n, 'link', 'migrated_sheet_link', :pv, :pn, :ov, :on, "
            "CAST(:prov AS jsonb), :a, :l)"),
            {"e": _id("cme"), "p": row["project_uid"], "d": row["document_uid"], "n": number + 1,
             "pv": row["page_version_uid"], "pn": row["page_number"], "ov": row["other_version_uid"],
             "on": row["other_page_number"], "prov": json.dumps(row["provenance"]), "a": row["actor_user_uid"],
             "l": row["actor_label"]})

    _refused(engine, duplicate_in_order, "23505")


# -- builds and edits (decisions 3, 14) ----------------------------------------------------------------------


def _build(connection: Any, ids: dict[str, Any], number: int, *, signature: str | None = None,
           order: str | None = None) -> str:
    build = _id("cmx")
    connection.execute(text(
        "INSERT INTO comparison_matrix (comparison_matrix_id, project_uid, document_uid, build_no, order_id, "
        "profile_signature, rules_version, algo_version, rows) VALUES (:m, :p, :d, :n, :o, :s, 'v1.2', 'm1', '[]')"),
        {"m": build, "p": ids["project"], "d": ids["document"], "n": number, "o": order,
         "s": signature or (f"{number:x}" * 64)[:64]})
    return build


def _edit(connection: Any, ids: dict[str, Any], number: int, kind: str, **columns: Any) -> str:
    edit = _id("cme")
    values: dict[str, Any] = {
        "e": edit, "p": ids["project"], "d": ids["document"], "n": number, "k": kind,
        "pv": None, "pn": None, "ov": None, "on": None, "av": None, "u": None, "o": None}
    if kind == "link":
        values.update(pv=ids["versions"][0], pn=1, ov=ids["versions"][1], on=1)
    elif kind == "unlink":
        values.update(pv=ids["versions"][0], pn=2)
    elif kind == "mark_absent":
        values.update(pv=ids["versions"][0], pn=3, av=ids["versions"][2])
    elif kind == "undo":
        values.update(u=columns.pop("undoes"))
    values.update(columns)
    connection.execute(text(
        "INSERT INTO comparison_matrix_edit (comparison_matrix_edit_id, project_uid, document_uid, edit_no, kind, "
        "page_version_uid, page_number, other_version_uid, other_page_number, absent_version_uid, undoes_edit_id, "
        "order_id, actor_user_uid, actor_label, command_id) VALUES (:e, :p, :d, :n, :k, :pv, :pn, :ov, :on, :av, "
        ":u, :o, :a, 'Эксперт', :c)"),
        {**values, "a": ACTOR, "c": _command(connection, "apply_comparison_matrix_edits")})
    return edit


def test_builds_are_numbered_without_a_gap_are_immutable_and_one_input_set_is_built_once(
    at_this: tuple[Engine, str],
) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _project(connection)
        first = _build(connection, ids, 1)
    _refused(engine, lambda c: _build(c, ids, 3))
    _refused(engine, lambda c: _build(c, ids, 1, signature="b" * 64))
    _refused(engine, lambda c: _build(c, ids, 2, signature=("1" * 64)), "23505")
    with engine.begin() as connection:
        _build(connection, ids, 2)
    _refused(engine, lambda c: c.execute(text("UPDATE comparison_matrix SET rules_version = 'x' "
                                              "WHERE comparison_matrix_id = :m"), {"m": first}), "AM003")
    _refused(engine, lambda c: c.execute(text("DELETE FROM comparison_matrix WHERE comparison_matrix_id = :m"),
                                         {"m": first}), "AM003")


def test_a_build_names_the_order_revision_of_its_own_document_only(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids, other = _project(connection), _project(connection)
        order = _id("cvo")
        connection.execute(text(
            "INSERT INTO comparison_version_order (comparison_version_order_id, project_uid, document_uid, "
            "revision_no, version_uids, source, actor_user_uid, actor_label, command_id) VALUES (:o, :p, :d, 1, "
            "CAST(:v AS jsonb), 'expert', :a, 'A', :c)"),
            {"o": order, "p": other["project"], "d": other["document"], "v": json.dumps(other["versions"]),
             "a": ACTOR, "c": _command(connection, "append_comparison_version_order")})
    _refused(engine, lambda c: _build(c, ids, 1, order=order))
    with engine.begin() as connection:
        _build(connection, other, 1, order=order)


def test_an_edit_has_the_shape_its_kind_needs(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _project(connection)
        for number, kind in enumerate(("link", "unlink", "mark_absent"), start=1):
            _edit(connection, ids, number, kind)
    v = ids["versions"]
    bad = (
        ("link", {"ov": None, "on": None}),
        ("link", {"ov": v[0]}),
        ("unlink", {"ov": v[1], "on": 1}),
        ("mark_absent", {"av": None}),
        ("mark_absent", {"av": v[0]}),
        ("link", {"pn": 0}),
    )
    for kind, columns in bad:
        _refused(engine, lambda c, k=kind, x=columns: _edit(c, ids, 4, k, **x), "23514")
    # a page past the end of its version is the chain's refusal, which fires before the CHECKs
    _refused(engine, lambda c: _edit(c, ids, 4, "link", pn=6))


def test_edits_are_numbered_without_a_gap_name_versions_of_their_document_and_are_immutable(
    at_this: tuple[Engine, str],
) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids, other = _project(connection), _project(connection)
        first = _edit(connection, ids, 1, "link")
    _refused(engine, lambda c: _edit(c, ids, 3, "unlink"))
    _refused(engine, lambda c: _edit(c, ids, 2, "link", ov=other["versions"][1]))
    _refused(engine, lambda c: _edit(c, ids, 2, "unlink", pn=6))
    _refused(engine, lambda c: _edit(c, ids, 2, "unlink", o=_id("cvo")))  # an order revision that is not the document's
    _refused(engine, lambda c: c.execute(text("UPDATE comparison_matrix_edit SET actor_label = 'x' "
                                              "WHERE comparison_matrix_edit_id = :e"), {"e": first}), "AM003")
    _refused(engine, lambda c: c.execute(text("DELETE FROM comparison_matrix_edit WHERE comparison_matrix_edit_id = :e"),
                                         {"e": first}), "AM003")


def test_an_undo_names_one_earlier_edit_once_and_never_an_undo(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids, other = _project(connection), _project(connection)
        link = _edit(connection, ids, 1, "link")
        foreign = _edit(connection, other, 1, "link")
        undo = _edit(connection, ids, 2, "undo", undoes=link)
    _refused(engine, lambda c: _edit(c, ids, 3, "undo", undoes=link), "23505")
    _refused(engine, lambda c: _edit(c, ids, 3, "undo", undoes=undo))
    _refused(engine, lambda c: _edit(c, ids, 3, "undo", undoes=foreign))
    _refused(engine, lambda c: _edit(c, ids, 3, "undo", undoes=_id("cme")))  # an edit that does not exist


def test_an_accepted_ai_link_binds_a_build_of_its_document_and_pages_of_its_versions(
    at_this: tuple[Engine, str],
) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids, other = _project(connection), _project(connection)
        build = _build(connection, ids, 1)
        foreign = _build(connection, other, 1)

    def link(connection: Any, matrix: str, *, page: int = 1, state: str = "unmatched", confidence: str = "high") -> None:
        connection.execute(text(
            "INSERT INTO comparison_ai_link (comparison_ai_link_id, document_uid, comparison_matrix_id, "
            "page_version_uid, page_number, other_version_uid, other_page_number, answered_state, confidence) "
            "VALUES (:i, :d, :m, :pv, :pn, :ov, 2, :s, :c)"),
            {"i": _id("cak"), "d": ids["document"], "m": matrix, "pv": ids["versions"][0], "pn": page,
             "ov": ids["versions"][1], "s": state, "c": confidence})

    with engine.begin() as connection:
        link(connection, build)
    _refused(engine, lambda c: link(c, build), "23505")
    _refused(engine, lambda c: link(c, foreign, page=2), "23503")
    _refused(engine, lambda c: link(c, build, page=9), "AM001")
    _refused(engine, lambda c: link(c, build, page=3, state="matched"), "23514")
    _refused(engine, lambda c: link(c, build, page=3, confidence="medium"), "23514")
    _refused(engine, lambda c: c.execute(text("UPDATE comparison_ai_link SET answered_state = 'doubtful'")), "AM003")


# -- series, transitions, pairs (decisions 15, 21) -------------------------------------------------------------


def _profile(connection: Any, version: str, page: int, key: str | None = None) -> str:
    profile = _id("cpr")
    connection.execute(text(
        "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, page_number, content_key, "
        "algo_version, status) VALUES (:i, :v, :n, :k, 'p1', 'ready')"),
        {"i": profile, "v": version, "n": page, "k": key or hashlib.sha256(f"{version}:{page}".encode()).hexdigest()})
    return profile


def _series(connection: Any, ids: dict[str, Any], build: str, *, state: str = "queued", reason: str | None = None) -> str:
    series = _id("cser")
    connection.execute(text(
        "INSERT INTO comparison_series (comparison_series_id, project_uid, document_uid, state, comparison_matrix_id, "
        "matrix_edit_no, input_sha256, failure_reason, actor_user_uid, actor_label, command_id) VALUES (:s, :p, :d, "
        ":st, :m, 0, :sha, :r, :a, 'A', :c)"),
        {"s": series, "p": ids["project"], "d": ids["document"], "st": state, "m": build, "sha": SHA, "r": reason,
         "a": ACTOR, "c": _command(connection, "start_comparison_series")})
    return series


def _transition(connection: Any, series: str, number: int, source: str, target: str) -> str:
    transition = _id("ctn")
    connection.execute(text(
        "INSERT INTO comparison_transition (comparison_transition_id, comparison_series_id, transition_no, "
        "source_version_uid, target_version_uid) VALUES (:t, :s, :n, :a, :b)"),
        {"t": transition, "s": series, "n": number, "a": source, "b": target})
    return transition


def test_a_document_has_one_live_series_and_a_series_moves_only_along_its_edges(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _project(connection)
        build = _build(connection, ids, 1)
        series = _series(connection, ids, build)
    _refused(engine, lambda c: _series(c, ids, build), "23505")
    set_state = lambda c, to: c.execute(text(  # noqa: E731
        "UPDATE comparison_series SET state = :s, failure_reason = :r WHERE comparison_series_id = :i"),
        {"s": to, "i": series, "r": "x" if to == "failed" else None})
    _refused(engine, lambda c: set_state(c, "completed"))  # queued -> completed has no edge
    for state in ("running", "completed"):
        with engine.begin() as connection:
            set_state(connection, state)
    with engine.begin() as connection:
        assert _series(connection, ids, build)  # the first one is finished, so a new live one is allowed
    _refused(engine, lambda c: set_state(c, "queued"), "23505")  # a finish would make two live series
    _refused(engine, lambda c: c.execute(text("UPDATE comparison_series SET input_sha256 = :s "
                                              "WHERE comparison_series_id = :i"), {"s": "b" * 64, "i": series}), "AM003")
    _refused(engine, lambda c: _series(c, ids, build, state="failed"), "23514")


def test_a_transition_lists_two_different_versions_of_the_documents_series(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids, other = _project(connection), _project(connection)
        series = _series(connection, ids, _build(connection, ids, 1))
        _transition(connection, series, 1, ids["versions"][0], ids["versions"][1])
    v = ids["versions"]
    _refused(engine, lambda c: _transition(c, series, 2, v[1], v[1]), "23514")
    _refused(engine, lambda c: _transition(c, series, 2, v[0], other["versions"][0]))
    _refused(engine, lambda c: _transition(c, series, 1, v[1], v[2]), "23505")
    _refused(engine, lambda c: _transition(c, series, 2, v[0], v[1]), "23505")
    with engine.begin() as connection:
        _transition(connection, series, 2, v[1], v[2])


def _pair_setup(engine: Engine) -> dict[str, Any]:
    with engine.begin() as connection:
        ids = _project(connection)
        other = _project(connection)
        series = _series(connection, ids, _build(connection, ids, 1))
        transition = _transition(connection, series, 1, ids["versions"][0], ids["versions"][1])
        a, b = _profile(connection, ids["versions"][0], 1), _profile(connection, ids["versions"][1], 1)
        c = _profile(connection, ids["versions"][2], 1)
        foreign = _profile(connection, other["versions"][0], 1)
    return {"ids": ids, "other": other, "series": series, "transition": transition, "a": a, "b": b, "c": c,
            "foreign": foreign}


def _result(connection: Any, project: str, a: str, b: str, *, key: str = SHA, status: str = "different",
            mask: str | None = None) -> str:
    result = _id("csp")
    connection.execute(text(
        "INSERT INTO comparison_sheet_pair_result (comparison_sheet_pair_result_id, project_uid, content_key, "
        "algo_version, status, page_a_profile_id, page_b_profile_id, mask_blob_id) "
        "VALUES (:r, :p, :k, 'vc1', :s, :a, :b, :m)"),
        {"r": result, "p": project, "k": key, "s": status, "a": a, "b": b, "m": mask})
    return result


def test_a_result_is_unique_by_content_within_a_project_and_only_within_it(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    setup = _pair_setup(engine)
    ids, other = setup["ids"], setup["other"]
    with engine.begin() as connection:
        _result(connection, ids["project"], setup["a"], setup["b"])
        other_b = _profile(connection, other["versions"][1], 1)
        _result(connection, other["project"], setup["foreign"], other_b)  # the same content key in another project
    _refused(engine, lambda c: _result(c, ids["project"], setup["a"], setup["b"]), "23505")
    _refused(engine, lambda c: _result(c, ids["project"], setup["foreign"], setup["b"], key="c" * 64))
    _refused(engine, lambda c: _result(c, ids["project"], setup["a"], setup["b"], key="d" * 64, status="added"), "23514")


def test_a_result_is_frozen_apart_from_a_write_once_mask_that_a_same_pair_never_has(
    at_this: tuple[Engine, str],
) -> None:
    engine, _ = at_this
    setup = _pair_setup(engine)
    ids = setup["ids"]
    with engine.begin() as connection:
        result = _result(connection, ids["project"], setup["a"], setup["b"])
        same = _result(connection, ids["project"], setup["a"], setup["b"], key="e" * 64, status="same")
        blob = _id("blob")
        connection.execute(text("INSERT INTO blob (blob_id) VALUES (:b)"), {"b": blob})
        second = _id("blob")
        connection.execute(text("INSERT INTO blob (blob_id) VALUES (:b)"), {"b": second})
    set_mask = lambda c, i, b: c.execute(text(  # noqa: E731
        "UPDATE comparison_sheet_pair_result SET mask_blob_id = :b WHERE comparison_sheet_pair_result_id = :i"),
        {"i": i, "b": b})
    _refused(engine, lambda c: set_mask(c, same, blob), "23514")
    with engine.begin() as connection:
        set_mask(connection, result, blob)
    _refused(engine, lambda c: set_mask(c, result, second), "AM003")
    _refused(engine, lambda c: c.execute(text("UPDATE comparison_sheet_pair_result SET status = 'same' "
                                              "WHERE comparison_sheet_pair_result_id = :i"), {"i": result}), "AM003")


def _pair(connection: Any, transition: str, number: int, **columns: Any) -> str:
    pair = _id("ctp")
    values = {"i": pair, "t": transition, "n": number, "st": "queued", "s": None, "a": None, "b": None, "r": None,
              "f": None}
    values.update(columns)
    connection.execute(text(
        "INSERT INTO comparison_sheet_pair (comparison_sheet_pair_id, comparison_transition_id, pair_no, state, "
        "status, page_a_profile_id, page_b_profile_id, result_id, failure_reason) "
        "VALUES (:i, :t, :n, :st, :s, :a, :b, :r, :f)"), values)
    return pair


def test_a_sheet_pair_has_pages_of_its_transition_a_result_of_its_project_and_the_shape_its_status_needs(
    at_this: tuple[Engine, str],
) -> None:
    engine, _ = at_this
    setup = _pair_setup(engine)
    ids, transition = setup["ids"], setup["transition"]
    with engine.begin() as connection:
        result = _result(connection, ids["project"], setup["a"], setup["b"])
        _pair(connection, transition, 1, st="done", s="different", a=setup["a"], b=setup["b"], r=result)
        _pair(connection, transition, 2, st="done", s="added", b=setup["b"])
        _pair(connection, transition, 3, st="done", s="removed", a=setup["a"])
        _pair(connection, transition, 4, a=setup["a"], b=setup["b"])
    _refused(engine, lambda c: _pair(c, transition, 1, a=setup["a"], b=setup["b"]), "23505")
    _refused(engine, lambda c: _pair(c, transition, 5), "23514")  # no page at all
    _refused(engine, lambda c: _pair(c, transition, 5, a=setup["b"], b=setup["c"]))  # pages of other versions
    _refused(engine, lambda c: _pair(c, transition, 5, a=setup["foreign"], b=setup["b"]))
    _refused(engine, lambda c: _pair(c, transition, 5, st="done", s="different", a=setup["a"], b=setup["b"]), "23514")
    _refused(engine, lambda c: _pair(c, transition, 5, st="queued", r=result, a=setup["a"], b=setup["b"]), "23514")
    _refused(engine, lambda c: _pair(c, transition, 5, st="done", s="added", a=setup["a"], b=setup["b"]), "23514")
    _refused(engine, lambda c: _pair(c, transition, 5, st="done", s="same", b=setup["b"], r=result), "23514")
    _refused(engine, lambda c: _pair(c, transition, 5, st="failed", a=setup["a"], b=setup["b"]), "23514")
    other = setup["other"]
    with engine.begin() as connection:
        foreign_result = _result(connection, other["project"], setup["foreign"],
                                 _profile(connection, other["versions"][1], 2), key="f" * 64)
    _refused(engine, lambda c: _pair(c, transition, 5, st="done", s="different", a=setup["a"], b=setup["b"],
                                     r=foreign_result))


def test_a_pair_is_queued_again_but_a_finished_pair_never_is_and_its_identity_is_frozen(
    at_this: tuple[Engine, str],
) -> None:
    engine, _ = at_this
    setup = _pair_setup(engine)
    ids, transition = setup["ids"], setup["transition"]
    with engine.begin() as connection:
        pair = _pair(connection, transition, 1, a=setup["a"], b=setup["b"])
        result = _result(connection, ids["project"], setup["a"], setup["b"])
    move = lambda c, **v: c.execute(text(  # noqa: E731
        "UPDATE comparison_sheet_pair SET state = :st, status = :s, result_id = :r, failure_reason = :f "
        "WHERE comparison_sheet_pair_id = :i"), {"i": pair, "st": None, "s": None, "r": None, "f": None, **v})
    with engine.begin() as connection:
        move(connection, st="computing")
        move(connection, st="queued")
        move(connection, st="computing")
        move(connection, st="done", s="different", r=result)
    _refused(engine, lambda c: move(c, st="queued"))
    _refused(engine, lambda c: c.execute(text("UPDATE comparison_sheet_pair SET page_a_profile_id = :b "
                                              "WHERE comparison_sheet_pair_id = :i"), {"b": setup["b"], "i": pair}), "AM003")


# -- reachability, no queue entanglement, the new columns ----------------------------------------------------


_FOREIGN_KEYS = (
    "SELECT conrelid::regclass::text, confrelid::regclass::text FROM pg_constraint "
    "WHERE contype = 'f' AND connamespace = 'public'::regnamespace"
)


def _unreachable(engine: Engine, tables: tuple[str, ...]) -> list[str]:
    with engine.connect() as connection:
        rows = connection.execute(text(_FOREIGN_KEYS)).all()
    parents: dict[str, set[str]] = {}
    for source, target in rows:
        parents.setdefault(str(source), set()).add(str(target))

    def reaches(table: str, seen: frozenset[str] = frozenset()) -> bool:
        if table == "project":
            return True
        return any(reaches(parent, seen | {table}) for parent in parents.get(table, ()) if parent not in seen)

    return [table for table in tables if not reaches(table)]


def test_every_new_table_is_reachable_from_the_project_by_foreign_keys(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    assert _unreachable(engine, TABLES) == []


def test_that_check_fails_on_a_table_that_reaches_nothing(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE comparison_orphan (id text PRIMARY KEY)"))
    assert _unreachable(engine, (*TABLES, "comparison_orphan")) == ["comparison_orphan"]


def test_the_new_columns_are_frozen_once_written(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _project(connection)
        series = _series(connection, ids, _build(connection, ids, 1))
        upload = _id("cbt")
        connection.execute(text(
            "INSERT INTO comparison_upload (comparison_upload_id, project_uid, declared_files, declared_bytes, "
            "actor_user_uid, actor_label, command_id, compare_after_preparation) VALUES (:u, :p, 1, 10, :a, 'A', :c, true)"),
            {"u": upload, "p": ids["project"], "a": ACTOR, "c": _command(connection, "create_comparison_upload")})
        work = _id("cq")
        connection.execute(text(
            "INSERT INTO comparison_work (comparison_work_id, project_uid, module, kind, comparison_series_id) "
            "VALUES (:w, :p, 'versions', 'comparison_pair', :s)"), {"w": work, "p": ids["project"], "s": series})
    _refused(engine, lambda c: c.execute(text(
        "UPDATE comparison_upload SET compare_after_preparation = false WHERE comparison_upload_id = :u"),
        {"u": upload}), "AM003")
    _refused(engine, lambda c: c.execute(text(
        "UPDATE comparison_work SET comparison_series_id = NULL WHERE comparison_work_id = :w"), {"w": work}), "AM003")
    _refused(engine, lambda c: c.execute(text(
        "UPDATE comparison_work SET comparison_series_id = 'cser_01ARZ3NDEKTSV4RRFFQ69G5FAV' "
        "WHERE comparison_work_id = :w"), {"w": work}), "AM003")


# -- the downgrade ----------------------------------------------------------------------------------------


def test_the_downgrade_is_refused_while_a_row_other_than_a_migrated_edit_exists_and_gives_back_0038(
    at_previous: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_previous
    _seed_approvals(engine)
    old = _old_rows(engine)
    _upgrade(foundation_command, url, THIS)
    assert _count(engine, "comparison_matrix_edit") == 3
    with engine.begin() as connection:
        ids = _project(connection)
        build = _build(connection, ids, 1)
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0 and "0039 downgrade refused" in refused.describe()
    assert _count(engine, "comparison_matrix") == 1, "the refusal changed a row"
    # the migrated edits alone do not block it: the build is removed with its guard disabled, as an operator would
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE comparison_matrix DISABLE TRIGGER trg_comparison_matrix_immutable"))
        connection.execute(text("DELETE FROM comparison_matrix"))
        connection.execute(text("ALTER TABLE comparison_matrix ENABLE TRIGGER trg_comparison_matrix_immutable"))
    done = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert done.returncode == 0, done.describe()
    assert not set(TABLES) & _tables(engine)
    assert _old_rows(engine) == old, "the downgrade changed a 0035 row"
    with engine.connect() as connection:
        columns = {row[0] for row in connection.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name IN ('comparison_work', "
            "'comparison_upload')"))}
        assert not {"comparison_series_id", "compare_after_preparation"} & columns
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
    _upgrade(foundation_command, url, THIS)
    assert _count(engine, "comparison_matrix_edit") == 3, "the data step did not run again after a downgrade"


def test_an_expert_edit_blocks_the_downgrade(at_this: tuple[Engine, str], foundation_command: Any) -> None:
    engine, url = at_this
    with engine.begin() as connection:
        ids = _project(connection)
        _edit(connection, ids, 1, "link")
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0 and "0039 downgrade refused" in refused.describe()
    assert _count(engine, "comparison_matrix_edit") == 1
