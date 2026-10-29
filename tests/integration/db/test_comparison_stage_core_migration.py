"""C3 stage storage on real PostgreSQL: scope, immutability and rollback."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
import json

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import new_ulid
from scripts.recovery import project_erase
from scripts.recovery.schema_coverage import TABLES as ALL_TABLES
from tests.support.expected_facts import FACTS

THIS = "0041_comparison_stage_core"
PREVIOUS = "0040_comparison_ai_reports"
STAGE_TABLES = frozenset({
    "stage_upload", "stage_upload_file", "stage_upload_part", "stage_upload_candidate",
    "stage_assembly", "stage_assembly_member", "stage_pair", "stage_link_revision",
    "stage_link_item", "stage_text_fragment", "stage_text_exclusion", "stage_text_difference",
    "stage_text_hint", "stage_chain_run", "stage_chain_step",
})
SHA = "a" * 64
ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _id(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _upgrade(command: Any, url: str, target: str) -> None:
    done = command(_alembic("upgrade", target), url)
    assert done.returncode == 0, done.describe()


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


def _world(connection: Any) -> tuple[str, str, str, str]:
    first, second = _id("prj"), _id("prj")
    left, outside = _id("doc"), _id("doc")
    for project in (first, second):
        connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'stage')"), {"p": project})
    for document, project in ((left, first), (outside, second)):
        connection.execute(text(
            "INSERT INTO document (document_uid, project_uid, display_title) "
            "VALUES (:d, :p, 'D')"), {"d": document, "p": project})
    return first, second, left, outside


def _upload(connection: Any, project: str) -> tuple[str, str, str]:
    upload, file_id, candidate = _id("stu"), _id("suf"), _id("suc")
    command = _id("cmd")
    connection.execute(text(
        "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
        "VALUES (:c, 'create_stage_upload', :k, :sha)"),
        {"c": command, "k": _id("k")[:20], "sha": SHA})
    connection.execute(text(
        "INSERT INTO stage_upload (stage_upload_id, project_uid, declared_files, declared_bytes, "
        "actor_user_uid, command_id) VALUES (:u, :p, 1, 10, :a, :c)"),
        {"u": upload, "p": project, "a": ACTOR, "c": command})
    connection.execute(text(
        "INSERT INTO stage_upload_file (stage_upload_file_id, stage_upload_id, media_kind, "
        "display_name, declared_size_bytes, declared_sha256) "
        "VALUES (:f, :u, 'zip', 'bundle.zip', 10, :sha)"),
        {"f": file_id, "u": upload, "sha": SHA})
    connection.execute(text(
        "INSERT INTO stage_upload_candidate (stage_upload_candidate_id, stage_upload_file_id, "
        "member_number, display_name) VALUES (:c, :f, 1, 'sheet.pdf')"),
        {"c": candidate, "f": file_id})
    return upload, file_id, candidate


def _command(connection: Any, kind: str) -> str:
    command = _id("cmd")
    connection.execute(text(
        "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
        "VALUES (:c, :t, :k, :sha)"),
        {"c": command, "t": kind, "k": _id("k")[:20], "sha": SHA})
    return command


def _refused(engine: Engine, statement: str, values: dict[str, str], state: str = "AM001") -> None:
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            connection.execute(text(statement), values)
    assert getattr(caught.value.orig, "sqlstate", None) == state, caught.value


def test_0041_adds_only_its_fifteen_project_reachable_tables(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    assert FACTS.migration_head == THIS
    with engine.connect() as connection:
        tables = {row[0] for row in connection.execute(text(
            "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"))}
        links = [(source, parent) for source, parent in connection.execute(text("""
            SELECT child.relname, parent.relname
              FROM pg_constraint fk JOIN pg_class child ON child.oid = fk.conrelid
              JOIN pg_class parent ON parent.oid = fk.confrelid
             WHERE fk.contype = 'f'
        """))]
    assert tables == ALL_TABLES
    parents: dict[str, set[str]] = {}
    for source, parent in links:
        parents.setdefault(source, set()).add(parent)

    def reaches(table: str, seen: frozenset[str] = frozenset()) -> bool:
        if table == "project":
            return True
        return any(reaches(parent, seen | {table}) for parent in parents.get(table, ()) if parent not in seen)

    assert all(reaches(table) for table in STAGE_TABLES)
    assert not any(parent in {"job", "attempt", "audit_run"} for source, parent in links if source in STAGE_TABLES)


def test_candidate_cannot_publish_a_document_from_another_project(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        project, _other_project, left, outside = _world(connection)
        _upload_id, _file_id, candidate = _upload(connection, project)
    _refused(engine,
             "UPDATE stage_upload_candidate SET document_uid = :d WHERE stage_upload_candidate_id = :c",
             {"d": outside, "c": candidate})
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE stage_upload_candidate SET document_uid = :d WHERE stage_upload_candidate_id = :c"),
            {"d": left, "c": candidate})
    _refused(engine,
             "UPDATE stage_upload_candidate SET document_uid = :d WHERE stage_upload_candidate_id = :c",
             {"d": outside, "c": candidate})


def test_chain_run_pins_real_versions_of_both_sides_of_its_pair(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        project, _other_project, left, outside = _world(connection)
        right = _id("doc")
        connection.execute(text(
            "INSERT INTO document (document_uid, project_uid, display_title) "
            "VALUES (:d, :p, 'R')"), {"d": right, "p": project})
        versions = {}
        for document in (left, right, outside):
            version = _id("ver")
            versions[document] = version
            connection.execute(text(
                "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                "media_type, byte_size, sha256, page_count) "
                "VALUES (:v, :d, 1, 'application/pdf', 1, :sha, 1)"),
                {"v": version, "d": document, "sha": SHA})
        pair, revision = _id("stp"), _id("slk")
        connection.execute(text(
            "INSERT INTO stage_pair (stage_pair_id, project_uid, left_document_uid, "
            "right_document_uid, state, confirmed_by_user_uid, confirmed_at, command_id) "
            "VALUES (:pair, :p, :left, :right, 'confirmed', :actor, now(), :command)"),
            {"pair": pair, "p": project, "left": left, "right": right,
             "actor": ACTOR, "command": _command(connection, "confirm_stage_pair")})
        connection.execute(text(
            "INSERT INTO stage_link_revision (stage_link_revision_id, stage_pair_id, "
            "revision_no, source, input_sha256, actor_user_uid, command_id) "
            "VALUES (:revision, :pair, 1, 'expert', :sha, :actor, :command)"),
            {"revision": revision, "pair": pair, "sha": SHA, "actor": ACTOR,
             "command": _command(connection, "apply_stage_sheet_map")})
        command = _command(connection, "start_stage_chain_run")
    run = _id("crn")
    statement = (
        "INSERT INTO stage_chain_run (stage_chain_run_id, stage_pair_id, stage_link_revision_id, "
        "input_sha256, pinned_version_uids, actor_user_uid, command_id) "
        "VALUES (:run, :pair, :revision, :sha, CAST(:versions AS jsonb), :actor, :command)"
    )
    base = {"run": run, "pair": pair, "revision": revision, "sha": SHA,
            "actor": ACTOR, "command": command}
    _refused(engine, statement,
             {**base, "versions": json.dumps([versions[left], versions[outside]])})
    with engine.begin() as connection:
        connection.execute(text(statement),
                           {**base, "versions": json.dumps([versions[left], versions[right]])})


def test_project_erase_deletes_a_nonempty_stage_graph_and_keeps_the_other_project(
    at_this: tuple[Engine, str],
) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        project, other_project, left, outside = _world(connection)
        right = _id("doc")
        connection.execute(text(
            "INSERT INTO document (document_uid, project_uid, display_title) "
            "VALUES (:d, :p, 'R')"), {"d": right, "p": project})
        versions = []
        for document in (left, right):
            version = _id("ver")
            versions.append(version)
            connection.execute(text(
                "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                "media_type, byte_size, sha256, page_count) "
                "VALUES (:v, :d, 1, 'application/pdf', 1, :sha, 1)"),
                {"v": version, "d": document, "sha": SHA})
        upload, _file, _candidate = _upload(connection, project)
        connection.execute(text(
            "UPDATE stage_upload SET state = 'completed' WHERE stage_upload_id = :u"), {"u": upload})
        assembly, member, pair, revision, run, step = (
            _id(prefix) for prefix in ("sas", "sam", "stp", "slk", "crn", "cst")
        )
        connection.execute(text(
            "INSERT INTO stage_assembly (stage_assembly_id, project_uid, label, actor_user_uid, "
            "command_id) VALUES (:a, :p, 'R sheets', :actor, :command)"),
            {"a": assembly, "p": project, "actor": ACTOR,
             "command": _command(connection, "create_stage_assembly")})
        connection.execute(text(
            "INSERT INTO stage_assembly_member (stage_assembly_member_id, stage_assembly_id, "
            "member_no, document_uid, action, actor_user_uid, command_id) "
            "VALUES (:m, :a, 1, :d, 'add', :actor, :command)"),
            {"m": member, "a": assembly, "d": right, "actor": ACTOR,
             "command": _command(connection, "revise_stage_assembly")})
        connection.execute(text(
            "INSERT INTO stage_pair (stage_pair_id, project_uid, left_document_uid, "
            "stage_assembly_id, state, confirmed_by_user_uid, confirmed_at, command_id) "
            "VALUES (:pair, :p, :left, :assembly, 'confirmed', :actor, now(), :command)"),
            {"pair": pair, "p": project, "left": left, "assembly": assembly,
             "actor": ACTOR, "command": _command(connection, "confirm_stage_pair")})
        connection.execute(text(
            "INSERT INTO stage_link_revision (stage_link_revision_id, stage_pair_id, "
            "revision_no, source, input_sha256, actor_user_uid, command_id) "
            "VALUES (:revision, :pair, 1, 'expert', :sha, :actor, :command)"),
            {"revision": revision, "pair": pair, "sha": SHA, "actor": ACTOR,
             "command": _command(connection, "apply_stage_sheet_map")})
        connection.execute(text(
            "INSERT INTO stage_chain_run (stage_chain_run_id, stage_pair_id, "
            "stage_link_revision_id, input_sha256, pinned_version_uids, state, "
            "actor_user_uid, command_id) "
            "VALUES (:run, :pair, :revision, :sha, CAST(:versions AS jsonb), "
            "'completed', :actor, :command)"),
            {"run": run, "pair": pair, "revision": revision, "sha": SHA,
             "versions": json.dumps(versions), "actor": ACTOR,
             "command": _command(connection, "start_stage_chain_run")})
        connection.execute(text(
            "INSERT INTO stage_chain_step (stage_chain_step_id, stage_chain_run_id, step_no, state) "
            "VALUES (:step, :run, 1, 'completed')"), {"step": step, "run": run})

    populated = {
        "stage_upload", "stage_upload_file", "stage_upload_candidate", "stage_assembly",
        "stage_assembly_member", "stage_pair", "stage_link_revision", "stage_chain_run",
        "stage_chain_step",
    }
    with engine.begin() as connection:
        _head, closure = project_erase.check_schema(connection)
        scope, outside_scope = project_erase.derive_scope(connection, closure, project)
        assert not outside_scope
        assert all(len(scope[table]) == 1 for table in populated)
        assert not any(scope[table] for table in STAGE_TABLES - populated)
        receipts = project_erase.derive_receipts(connection, closure, scope)
        deleted = project_erase.delete_scope(connection, closure, scope)
        assert all(deleted[table] == 1 for table in populated)
        connection.execute(text(
            "DELETE FROM command_record WHERE command_id = ANY(CAST(:ids AS text[]))"),
            {"ids": list(receipts)})
        assert connection.execute(text(
            "SELECT count(*) FROM project WHERE project_uid = :p"), {"p": project}).scalar_one() == 0
        assert connection.execute(text(
            "SELECT count(*) FROM project WHERE project_uid = :p"), {"p": other_project}).scalar_one() == 1
        assert connection.execute(text(
            "SELECT count(*) FROM document WHERE document_uid = :d"), {"d": outside}).scalar_one() == 1


def test_upload_ownership_is_frozen_and_downgrade_refuses_data(
    at_previous: tuple[Engine, str], foundation_command: Any,
) -> None:
    engine, url = at_previous
    _upgrade(foundation_command, url, THIS)
    with engine.begin() as connection:
        project, other_project, _left, _outside = _world(connection)
        upload, file_id, candidate = _upload(connection, project)
    _refused(engine, "UPDATE stage_upload SET project_uid = :p WHERE stage_upload_id = :u",
             {"p": other_project, "u": upload}, "AM003")
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0 and "0041 downgrade refused" in refused.describe()
    with engine.begin() as connection:
        for table, key, value in (
            ("stage_upload_candidate", "stage_upload_candidate_id", candidate),
            ("stage_upload_file", "stage_upload_file_id", file_id),
            ("stage_upload", "stage_upload_id", upload),
        ):
            connection.execute(text(f"DELETE FROM {table} WHERE {key} = :id"), {"id": value})
    done = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert done.returncode == 0, done.describe()
    _upgrade(foundation_command, url, THIS)
