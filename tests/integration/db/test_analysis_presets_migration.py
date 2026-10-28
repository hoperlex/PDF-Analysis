"""`ANALYSIS-PRESETS-01`: ``0037_analysis_presets`` on a populated ``0036`` database.

``analysis_preset_revision`` is an append-only history of the revisions of named presets, and
``audit_run.preset_revision_id`` records the one a run started with. Against real PostgreSQL rows,
written through plain INSERTs, each rule shown failing:

* **the step adds the table and the column and changes no stored row**;
* **the database holds the rules, not only the command**: UPDATE and DELETE are refused (``AM003``),
  revision n needs n - 1, a preset is the id of its first revision, nothing follows an archive, an
  archive repeats the name and the connection, a name is unique among active presets without regard
  to case, an active revision needs a connection that is not archived, at most 100 presets exist, and
  the writers of the family are serialised by one advisory lock (proved with two real connections);
* **the shape**: formats, the name rule, the state vocabulary, an archive never opens a chain;
* **the run's record**: a run with a preset also froze an executor revision, that revision belongs to
  the connection the preset revision names, and the column cannot be moved afterwards;
* **the downgrade is refused while any row exists, and only then**.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId,
    AuditEventId,
    DocumentUid,
    ExecutorConnectionId,
    ExecutorConnectionRevisionId,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)
from tests.support.expected_facts import FACTS

THIS = "0037_analysis_presets"
PREVIOUS = "0036_cite_partition_v3"
ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
MAX_PRESETS = 100


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _sqlstate(error: DBAPIError) -> str:
    return str(getattr(error.orig, "sqlstate", "") or "")


def _upgrade(foundation_command: Any, url: str, revision: str) -> None:
    done = foundation_command(_alembic("upgrade", revision), url)
    assert done.returncode == 0, done.describe()


def _connection(connection: Any, *, archived: bool = False) -> str:
    connection_id = str(ExecutorConnectionId.new())
    connection.execute(text(
        "INSERT INTO executor_connection (connection_id, kind, display_name, created_by) "
        "VALUES (:id, 'http_api', 'test', :actor)"), {"id": connection_id, "actor": ACTOR})
    if archived:
        connection.execute(text(
            "UPDATE executor_connection SET archived_at = clock_timestamp(), archived_by = :actor "
            "WHERE connection_id = :id"), {"id": connection_id, "actor": ACTOR})
    return connection_id


def _executor_revision(connection: Any, connection_id: str) -> str:
    revision_id = str(ExecutorConnectionRevisionId.new())
    connection.execute(text(
        "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, "
        "created_by, pin_id, gateway_model, billing, allow_client_documents, timeout_seconds, "
        "api_flavour, base_url, transport) VALUES (:id, :c, 1, :actor, 'claude-opus-5', "
        "'anthropic/claude-opus-5', 'metered', false, 60, 'openai_chat', 'https://proxy.test', "
        "'direct')"), {"id": revision_id, "c": connection_id, "actor": ACTOR})
    return revision_id


def _preset(connection: Any, connection_id: str, *, revision_no: int = 1, preset_id: str | None = None,
            state: str = "active", name: str = "Основной", revision_id: str | None = None) -> tuple[str, str]:
    """One INSERT; returns (preset_id, revision_id). The first revision's id is the preset's."""
    revision_id = revision_id or str(AuditEventId.new())
    if preset_id is None:
        preset_id = revision_id
    connection.execute(text(
        "INSERT INTO analysis_preset_revision (preset_revision_id, preset_id, revision_no, state, name, "
        "executor_connection_id, created_by) VALUES (:rev, :preset, :n, :state, :name, :c, :actor)"
    ), {"rev": revision_id, "preset": preset_id, "n": revision_no, "state": state, "name": name,
        "c": connection_id, "actor": ACTOR})
    return preset_id, revision_id


def _run(connection: Any, *, connection_revision: str | None, preset_revision: str | None) -> str:
    ids = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
           "version": str(VersionUid.new()), "run": str(RunId.new())}
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'presets')"), ids)
    connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                            "VALUES (:document, :project, 'D')"), ids)
    connection.execute(text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                            "media_type, byte_size, sha256, page_count) VALUES (:version, :document, 1, "
                            "'application/pdf', 1, :sha, 1)"), {**ids, "sha": "a" * 64})
    connection.execute(text(
        "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, "
        "prompt_bundle_id, provider_mode, frozen_input_digest, connection_revision_id, "
        "preset_revision_id) VALUES (:run, :project, :version, :profile, :bundle, 'recorded', :digest, "
        ":crev, :prev)"),
        {**ids, "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()),
         "digest": "b" * 64, "crev": connection_revision, "prev": preset_revision})
    return ids["run"]


def _refused(engine: Engine, write: Any, sqlstate: str = "AM001") -> None:
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            write(connection)
    assert _sqlstate(caught.value) == sqlstate, caught.value


def _count(engine: Engine, table: str = "analysis_preset_revision") -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


def _version(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one())


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


@pytest.fixture
def live(at_this: tuple[Engine, str]) -> Iterator[tuple[Engine, str]]:
    """A migrated database with one live executor connection; yields (engine, connection id)."""
    engine, _ = at_this
    with engine.begin() as connection:
        connection_id = _connection(connection)
    yield engine, connection_id


# -- the step -----------------------------------------------------------------------------------


def test_the_head_of_the_tree_is_this_revision_or_a_later_one() -> None:
    assert FACTS.migration_head >= THIS


def test_the_revision_id_fits_the_version_column() -> None:
    assert len(THIS) <= 32


def test_the_step_adds_the_table_and_the_column_and_changes_no_stored_row(
    at_previous: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_previous
    with engine.begin() as connection:
        connection_id = _connection(connection)
        _executor_revision(connection, connection_id)
    tables = ("executor_connection", "executor_connection_revision", "command_record", "audit_event")
    before = {table: _count(engine, table) for table in tables}
    with engine.connect() as connection:
        assert connection.execute(text("SELECT to_regclass('public.analysis_preset_revision')")).scalar_one() is None
    _upgrade(foundation_command, url, THIS)
    assert _version(engine) == THIS
    assert {table: _count(engine, table) for table in tables} == before
    assert _count(engine) == 0


def test_the_frozen_guard_of_the_run_names_the_new_column_and_keeps_the_old_ones(
    at_this: tuple[Engine, str],
) -> None:
    engine, _ = at_this
    with engine.connect() as connection:
        definition = connection.execute(text(
            "SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname = 'trg_audit_run_frozen_guard'"
        )).scalar_one()
    for column in ("preset_revision_id", "connection_revision_id", "norm_retrieval_set_id", "run_id"):
        assert f"'{column}'" in definition, definition


# -- the history --------------------------------------------------------------------------------


def test_a_revision_a_revision_and_an_archive_are_numbered_without_a_gap(
    live: tuple[Engine, str],
) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        preset, _ = _preset(connection, connection_id, name="Основной")
        _preset(connection, connection_id, revision_no=2, preset_id=preset, name="Основной, быстрый")
        _preset(connection, connection_id, revision_no=3, preset_id=preset, state="archived",
                name="Основной, быстрый")
    assert _count(engine) == 3


@pytest.mark.parametrize("number", [2, 3])
def test_the_first_row_of_a_preset_is_revision_one(live: tuple[Engine, str], number: int) -> None:
    engine, connection_id = live
    _refused(engine, lambda c: _preset(c, connection_id, revision_no=number, preset_id=str(AuditEventId.new())))


def test_a_revision_may_not_skip_a_number(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        preset, _ = _preset(connection, connection_id)
    _refused(engine, lambda c: _preset(c, connection_id, revision_no=3, preset_id=preset, name="Другой"))


def test_a_revision_may_not_repeat_a_number(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        preset, _ = _preset(connection, connection_id)
    _refused(engine, lambda c: _preset(c, connection_id, revision_no=1, preset_id=preset, name="Другой"))


def test_a_preset_is_the_id_of_its_first_revision(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    _refused(engine, lambda c: _preset(c, connection_id, preset_id=str(AuditEventId.new())), "23514")


def test_a_later_revision_is_not_the_preset_id(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        preset, _ = _preset(connection, connection_id)
    _refused(engine, lambda c: _preset(c, connection_id, revision_no=2, preset_id=preset,
                                       revision_id=preset, name="Другой"), "23514")


def test_nothing_follows_an_archive(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        preset, _ = _preset(connection, connection_id)
        _preset(connection, connection_id, revision_no=2, preset_id=preset, state="archived")
    _refused(engine, lambda c: _preset(c, connection_id, revision_no=3, preset_id=preset))
    _refused(engine, lambda c: _preset(c, connection_id, revision_no=3, preset_id=preset, state="archived"))


def test_an_archive_cannot_open_a_chain(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    _refused(engine, lambda c: _preset(c, connection_id, state="archived"), "23514")


def test_an_archive_repeats_the_name_and_the_connection_of_the_revision_before(
    live: tuple[Engine, str],
) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        other = _connection(connection)
        preset, _ = _preset(connection, connection_id, name="Основной")
    _refused(engine, lambda c: _preset(c, connection_id, revision_no=2, preset_id=preset,
                                       state="archived", name="Переименован"))
    _refused(engine, lambda c: _preset(c, other, revision_no=2, preset_id=preset,
                                       state="archived", name="Основной"))


# -- names --------------------------------------------------------------------------------------


def test_an_active_name_is_held_by_one_preset_without_regard_to_case(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        _preset(connection, connection_id, name="Чертежи")
    _refused(engine, lambda c: _preset(c, connection_id, name="чертежи"))
    _refused(engine, lambda c: _preset(c, connection_id, name="ЧЕРТЕЖИ"))


def test_the_same_preset_may_keep_its_own_name_in_a_new_revision(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        other = _connection(connection)
        preset, _ = _preset(connection, connection_id, name="Чертежи")
        _preset(connection, other, revision_no=2, preset_id=preset, name="Чертежи")
    assert _count(engine) == 2


def test_an_archive_frees_the_name_and_an_old_revision_does_not_hold_it(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        first, _ = _preset(connection, connection_id, name="Старое имя")
        _preset(connection, connection_id, revision_no=2, preset_id=first, name="Новое имя")
        # revision 1 of `first` was named «Старое имя», but its latest revision is «Новое имя»
        second, _ = _preset(connection, connection_id, name="Старое имя")
        _preset(connection, connection_id, revision_no=2, preset_id=second, state="archived",
                name="Старое имя")
        _preset(connection, connection_id, name="Старое имя")  # the archive freed it
    assert _count(engine) == 5


@pytest.mark.parametrize("name", ["", " Чертежи", "Чертежи ", "А" * 121, "А\tБ", "А\nБ", "А\x85Б"])
def test_a_name_is_trimmed_printable_and_at_most_120_characters(live: tuple[Engine, str], name: str) -> None:
    engine, connection_id = live
    _refused(engine, lambda c: _preset(c, connection_id, name=name), "23514")


def test_a_name_of_exactly_120_characters_is_accepted(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        _preset(connection, connection_id, name="А" * 120)
    assert _count(engine) == 1


# -- connections --------------------------------------------------------------------------------


def test_an_active_revision_needs_a_connection_that_is_not_archived(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        archived = _connection(connection, archived=True)
        preset, _ = _preset(connection, connection_id, name="Основной")
    _refused(engine, lambda c: _preset(c, archived, name="В архиве"))
    _refused(engine, lambda c: _preset(c, archived, revision_no=2, preset_id=preset, name="Основной"))


def test_a_preset_whose_connection_was_archived_can_still_be_archived(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        preset, _ = _preset(connection, connection_id, name="Основной")
        connection.execute(text(
            "UPDATE executor_connection SET archived_at = clock_timestamp(), archived_by = :actor "
            "WHERE connection_id = :id"), {"id": connection_id, "actor": ACTOR})
    with engine.begin() as connection:
        _preset(connection, connection_id, revision_no=2, preset_id=preset, state="archived",
                name="Основной")
    assert _count(engine) == 2


def test_a_connection_must_exist(live: tuple[Engine, str]) -> None:
    engine, _ = live
    _refused(engine, lambda c: _preset(c, str(ExecutorConnectionId.new())), "23503")


# -- the bound ----------------------------------------------------------------------------------


def test_at_most_a_hundred_presets_exist_and_an_archive_is_not_a_deletion(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        first = ""
        for number in range(MAX_PRESETS):
            preset, _ = _preset(connection, connection_id, name=f"Пресет {number:03d}")
            first = first or preset
        _preset(connection, connection_id, revision_no=2, preset_id=first, state="archived",
                name="Пресет 000")
    assert _count(engine) == MAX_PRESETS + 1
    _refused(engine, lambda c: _preset(c, connection_id, name="Сотый и один"))


# -- append-only --------------------------------------------------------------------------------


def test_a_revision_can_be_neither_updated_nor_deleted(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        _, revision = _preset(connection, connection_id)
    _refused(engine, lambda c: c.execute(text(
        "UPDATE analysis_preset_revision SET name = 'Иначе' WHERE preset_revision_id = :r"), {"r": revision}), "AM003")
    _refused(engine, lambda c: c.execute(text(
        "UPDATE analysis_preset_revision SET state = 'archived' WHERE preset_revision_id = :r"),
        {"r": revision}), "AM003")
    _refused(engine, lambda c: c.execute(text(
        "DELETE FROM analysis_preset_revision WHERE preset_revision_id = :r"), {"r": revision}), "AM003")
    assert _count(engine) == 1


@pytest.mark.parametrize("column", ["preset_revision_id", "preset_id", "executor_connection_id", "created_by"])
def test_a_malformed_identity_is_refused(live: tuple[Engine, str], column: str) -> None:
    engine, connection_id = live

    def insert(connection: Any) -> None:
        values = {"rev": str(AuditEventId.new()), "c": connection_id, "actor": ACTOR}
        values["preset"] = values["rev"]
        key = {"preset_revision_id": "rev", "preset_id": "preset", "executor_connection_id": "c",
               "created_by": "actor"}[column]
        values[key] = "not-an-identity"
        connection.execute(text(
            "INSERT INTO analysis_preset_revision (preset_revision_id, preset_id, revision_no, state, name, "
            "executor_connection_id, created_by) VALUES (:rev, :preset, 1, 'active', 'А', :c, :actor)"),
            values)

    # a CHECK is evaluated before any foreign key, so a malformed id never reaches the key
    _refused(engine, insert, "23514")


def test_a_state_outside_the_vocabulary_is_refused(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    _refused(engine, lambda c: _preset(c, connection_id, state="deleted"), "23514")


# -- the family is serialised -------------------------------------------------------------------


def test_two_writers_of_one_name_are_serialised_by_the_family_lock(live: tuple[Engine, str]) -> None:
    """Without the lock the second writer cannot see the first's uncommitted row, both commit and the
    name is held twice. With it the second waits for the first and is then refused."""
    engine, connection_id = live
    first_inserted, may_commit = threading.Event(), threading.Event()
    outcome: dict[str, Any] = {}

    def holder() -> None:
        with engine.connect() as connection:
            with connection.begin():
                _preset(connection, connection_id, name="Одно имя")
                first_inserted.set()
                may_commit.wait(timeout=20)

    def competitor() -> None:
        try:
            with engine.begin() as connection:
                connection.execute(text("SET LOCAL lock_timeout = '10s'"))
                _preset(connection, connection_id, name="одно ИМЯ")
            outcome["result"] = "committed"
        except DBAPIError as error:
            outcome["result"] = _sqlstate(error)

    first = threading.Thread(target=holder)
    first.start()
    assert first_inserted.wait(timeout=20)
    second = threading.Thread(target=competitor)
    second.start()
    second.join(timeout=1.5)
    assert second.is_alive(), "the second writer must wait for the first, not run past it"
    may_commit.set()
    first.join(timeout=20)
    second.join(timeout=20)
    assert outcome == {"result": "AM001"}
    assert _count(engine) == 1


# -- the run's record ---------------------------------------------------------------------------


def test_a_run_may_record_the_preset_revision_of_the_executor_it_froze(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        revision = _executor_revision(connection, connection_id)
        _, preset_revision = _preset(connection, connection_id)
        run = _run(connection, connection_revision=revision, preset_revision=preset_revision)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT preset_revision_id FROM audit_run WHERE run_id = :r"),
                                  {"r": run}).scalar_one() == preset_revision


def test_a_run_without_a_preset_is_what_it_was(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        revision = _executor_revision(connection, connection_id)
        with_executor = _run(connection, connection_revision=revision, preset_revision=None)
        without = _run(connection, connection_revision=None, preset_revision=None)
    with engine.connect() as connection:
        found = connection.execute(text(
            "SELECT run_id, preset_revision_id FROM audit_run WHERE run_id IN (:a, :b)"),
            {"a": with_executor, "b": without}).all()
    assert sorted(row[1] for row in found if row[1] is not None) == []


def test_a_run_with_a_preset_also_froze_an_executor_revision(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        _, preset_revision = _preset(connection, connection_id)
    _refused(engine, lambda c: _run(c, connection_revision=None, preset_revision=preset_revision))


def test_a_run_cannot_claim_a_preset_whose_executor_it_did_not_use(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        other = _connection(connection)
        other_revision = _executor_revision(connection, other)
        _, preset_revision = _preset(connection, connection_id)
    _refused(engine, lambda c: _run(c, connection_revision=other_revision, preset_revision=preset_revision))


def test_a_run_cannot_name_a_preset_revision_that_does_not_exist(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        revision = _executor_revision(connection, connection_id)
    _refused(engine, lambda c: _run(c, connection_revision=revision,
                                    preset_revision=str(AuditEventId.new())))


def test_the_preset_of_a_run_cannot_be_changed_or_added_afterwards(live: tuple[Engine, str]) -> None:
    engine, connection_id = live
    with engine.begin() as connection:
        revision = _executor_revision(connection, connection_id)
        _, first = _preset(connection, connection_id, name="Первый")
        _, second = _preset(connection, connection_id, name="Второй")
        with_preset = _run(connection, connection_revision=revision, preset_revision=first)
        without = _run(connection, connection_revision=revision, preset_revision=None)
    _refused(engine, lambda c: c.execute(text(
        "UPDATE audit_run SET preset_revision_id = :p WHERE run_id = :r"), {"p": second, "r": with_preset}),
        "AM003")
    _refused(engine, lambda c: c.execute(text(
        "UPDATE audit_run SET preset_revision_id = :p WHERE run_id = :r"), {"p": first, "r": without}),
        "AM003")


# -- the downgrade ------------------------------------------------------------------------------


def test_the_downgrade_is_refused_while_a_revision_exists_and_only_then(
    live: tuple[Engine, str], at_this: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, connection_id = live
    _, url = at_this
    with engine.begin() as connection:
        _preset(connection, connection_id)
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0, refused.describe()
    assert "0037 downgrade refused: 1 preset revision(s) and 0 run(s)" in refused.stderr, refused.stderr
    assert _version(engine) == THIS and _count(engine) == 1  # a refusal changes nothing


def test_the_downgrade_is_refused_while_a_run_records_a_preset(
    live: tuple[Engine, str], at_this: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, connection_id = live
    _, url = at_this
    with engine.begin() as connection:
        revision = _executor_revision(connection, connection_id)
        _, preset_revision = _preset(connection, connection_id)
        _run(connection, connection_revision=revision, preset_revision=preset_revision)
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0, refused.describe()
    assert "1 preset revision(s) and 1 run(s)" in refused.stderr, refused.stderr


def test_without_a_row_the_downgrade_restores_the_guard_and_the_upgrade_runs_again(
    at_this: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_this
    down = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert down.returncode == 0, down.describe()
    assert _version(engine) == PREVIOUS
    with engine.connect() as connection:
        assert connection.execute(text("SELECT to_regclass('public.analysis_preset_revision')")).scalar_one() is None
        assert connection.execute(text(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name = 'audit_run' AND column_name = 'preset_revision_id'")).scalar_one() == 0
        assert connection.execute(text(
            "SELECT count(*) FROM pg_proc WHERE proname IN "
            "('am_check_analysis_preset_chain', 'am_check_audit_run_preset')")).scalar_one() == 0
        definition = connection.execute(text(
            "SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname = 'trg_audit_run_frozen_guard'"
        )).scalar_one()
    assert "'preset_revision_id'" not in definition and "'connection_revision_id'" in definition, definition
    _upgrade(foundation_command, url, THIS)
    with engine.begin() as connection:
        _preset(connection, _connection(connection))
    assert _count(engine) == 1
