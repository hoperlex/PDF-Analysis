"""`CMP-SEAL-C0`: ``0038_comparison_foundation`` on a populated ``0037`` database.

Nine tables, one column of ``document_version`` and the origin of ``executor_task`` -- and no row
written. Against real PostgreSQL rows, written through plain INSERTs, each rule shown failing:

* **the step adds the objects and changes no stored row**, and every version already stored says
  ``portal_bundle``;
* **ADR-0025 decision 4, the verification row 2**: ``comparison_work``, ``comparison_work_attempt`` and
  ``comparison_model_call`` have no foreign key to ``job``, ``attempt`` or ``audit_run`` (the check is
  shown failing on a database in which one is added);
* **decision 7**: every new table is reachable from ``project`` by foreign keys, so the erase keeps its
  closure (shown failing on a table that is not);
* **decision 5, the spend journal**: a row can only be inserted ``prepared``, goes ``prepared -> sent ->
  completed | failed | unknown`` and nowhere else, and a terminal row never moves;
* **decision 10**: a part is refused for a file that holds no multipart token, and the token is write-once;
* **decisions 14 and 16**: the order revisions are numbered without a gap, list only versions of the
  document, and are immutable;
* **decision 4**: the work item and the attempt move only along the declared edges, and the frozen columns
  stay;
* **the executor task** accepts the origin ``comparison_call`` with its attempt and refuses it without;
* **the downgrade is refused while any row exists, and only then**, and gives back the ``0037`` schema.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    DocumentUid,
    ExecutorConnectionId,
    ExecutorConnectionRevisionId,
    ProjectUid,
    VersionUid,
    new_ulid,
)
from tests.support.expected_facts import FACTS

THIS = "0038_comparison_foundation"
PREVIOUS = "0037_analysis_presets"
ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
TABLES = (
    "comparison_upload", "comparison_upload_set", "comparison_upload_file", "comparison_upload_part",
    "comparison_version_order", "comparison_page_profile", "comparison_work",
    "comparison_work_attempt", "comparison_model_call",
)
QUEUE_TABLES = ("comparison_work", "comparison_work_attempt", "comparison_model_call")
SHA = "a" * 64


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _sqlstate(error: DBAPIError) -> str:
    return str(getattr(error.orig, "sqlstate", "") or "")


def _run(foundation_command: Any, url: str, action: str, revision: str) -> Any:
    return foundation_command(_alembic(action, revision), url)


def _upgrade(foundation_command: Any, url: str, revision: str) -> None:
    done = _run(foundation_command, url, "upgrade", revision)
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


def _project(connection: Any) -> dict[str, str]:
    ids = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
           "version": str(VersionUid.new()), "version2": str(VersionUid.new())}
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'cmp')"), ids)
    connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                            "VALUES (:document, :project, 'D')"), ids)
    for number, key in ((1, "version"), (2, "version2")):
        connection.execute(text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
            "byte_size, sha256, page_count) VALUES (:v, :document, :n, 'application/pdf', 1, :sha, 3)"),
            {"v": ids[key], "document": ids["document"], "n": number, "sha": SHA})
    return ids


def _command(connection: Any) -> str:
    command = _id("cmd")
    connection.execute(text(
        "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
        "VALUES (:c, 'create_comparison_upload', :k, :f)"), {"c": command, "k": _id("k")[:20], "f": SHA})
    return command


def _work(connection: Any, project: str, *, state: str = "queued") -> str:
    work = _id("cq")
    connection.execute(text(
        "INSERT INTO comparison_work (comparison_work_id, project_uid, module, kind, state) "
        "VALUES (:w, :p, 'versions', 'profile_page', :s)"), {"w": work, "p": project, "s": state})
    return work


def _attempt(connection: Any, work: str, *, number: int = 1) -> str:
    attempt = _id("cqa")
    connection.execute(text(
        "INSERT INTO comparison_work_attempt (comparison_work_attempt_id, comparison_work_id, attempt_no, "
        "execution_token) VALUES (:a, :w, :n, :t)"), {"a": attempt, "w": work, "n": number, "t": new_ulid()})
    return attempt


def _call(connection: Any, work: str, attempt: str, *, state: str = "prepared") -> str:
    call = _id("cmc")
    connection.execute(text(
        "INSERT INTO comparison_model_call (comparison_model_call_id, comparison_work_id, "
        "comparison_work_attempt_id, work_kind, state, provider_mode, model_identity, request_sha256, "
        "estimate_micros) VALUES (:c, :w, :a, 'comparison_pair_check', :s, 'recorded', 'recorded', :sha, 10)"),
        {"c": call, "w": work, "a": attempt, "s": state, "sha": SHA})
    return call


def _file(connection: Any, project: str, *, token: str | None = None) -> tuple[str, str]:
    upload, file = _id("cbt"), _id("cuf")
    command = _command(connection)
    connection.execute(text(
        "INSERT INTO comparison_upload (comparison_upload_id, project_uid, declared_files, declared_bytes, "
        "actor_user_uid, actor_label, command_id) VALUES (:u, :p, 1, 10, :a, 'A', :c)"),
        {"u": upload, "p": project, "a": ACTOR, "c": command})
    connection.execute(text(
        "INSERT INTO comparison_upload_file (comparison_upload_file_id, comparison_upload_id, display_name, "
        "declared_size_bytes, declared_sha256, multipart_token) VALUES (:f, :u, 'a.pdf', 10, :sha, :t)"),
        {"f": file, "u": upload, "sha": SHA, "t": token})
    return upload, file


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
        kinds = connection.execute(text("SELECT DISTINCT upload_kind FROM document_version")).scalars().all()
    assert kinds == ["portal_bundle"]


def test_a_version_may_be_a_comparison_pdf_and_then_holds_no_bundle_counts(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _project(connection)
    version = str(VersionUid.new())

    def insert(connection: Any, **extra: Any) -> None:
        connection.execute(text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
            "sha256, page_count, upload_kind, text_character_count, textless_pages, recognised_character_count) "
            "VALUES (:v, :d, 3, 'application/pdf', 1, :sha, 3, :kind, :t, :l, :r)"),
            {"v": version, "d": ids["document"], "sha": SHA, "kind": "comparison_pdf", "t": None, "l": None,
             "r": None, **extra})

    _refused(engine, lambda c: insert(c, kind="plain"), "23514")
    _refused(engine, lambda c: insert(c, t=10, l=[], r=0), "23514")
    with engine.begin() as connection:
        insert(connection)
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT upload_kind FROM document_version WHERE version_uid = :v"), {"v": version}).scalar_one() \
            == "comparison_pdf"


# -- decisions 4 and 7: no foreign key to the run's machinery, and every table reaches the project ---


_FOREIGN_KEYS = (
    "SELECT conrelid::regclass::text, confrelid::regclass::text FROM pg_constraint "
    "WHERE contype = 'f' AND connamespace = 'public'::regnamespace"
)


def _forbidden_references(engine: Engine) -> list[tuple[str, str]]:
    with engine.connect() as connection:
        rows = connection.execute(text(_FOREIGN_KEYS)).all()
    return sorted(
        (str(source), str(target)) for source, target in rows
        if source in QUEUE_TABLES and target in ("job", "attempt", "audit_run", "lease")
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


def test_the_comparison_queue_has_no_foreign_key_to_job_attempt_or_audit_run(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    assert _forbidden_references(engine) == []


def test_that_check_fails_on_a_database_in_which_a_foreign_key_to_job_is_added(at_this: tuple[Engine, str]) -> None:
    """Mutation: one foreign key from the journal to ``job`` and the check above is red."""
    engine, _ = at_this
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE comparison_model_call ADD COLUMN job_id text"))
        connection.execute(text(
            "ALTER TABLE comparison_model_call ADD CONSTRAINT fk_mutation FOREIGN KEY (job_id) "
            "REFERENCES job (job_id)"))
    assert _forbidden_references(engine) == [("comparison_model_call", "job")]


def test_every_new_table_is_reachable_from_the_project_by_foreign_keys(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    assert _unreachable(engine, TABLES) == []


def test_that_check_fails_on_a_table_that_reaches_nothing(at_this: tuple[Engine, str]) -> None:
    """Mutation: a table with no foreign key is reported, so the reachability test can fail."""
    engine, _ = at_this
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE comparison_orphan (id text PRIMARY KEY)"))
    assert _unreachable(engine, (*TABLES, "comparison_orphan")) == ["comparison_orphan"]


# -- decision 5: the spend journal --------------------------------------------------------------


def _journal(engine: Engine) -> tuple[str, str, str]:
    with engine.begin() as connection:
        project = _project(connection)["project"]
        work = _work(connection, project, state="running")
        attempt = _attempt(connection, work)
        return work, attempt, _call(connection, work, attempt)


@pytest.mark.parametrize("state", ["sent", "completed", "failed", "unknown"])
def test_a_journal_row_can_only_be_inserted_prepared(at_this: tuple[Engine, str], state: str) -> None:
    """The ``prepared`` row exists before any provider call: nothing else can be written first."""
    engine, _ = at_this
    with engine.begin() as connection:
        project = _project(connection)["project"]
        work = _work(connection, project, state="running")
        attempt = _attempt(connection, work)
    _refused(engine, lambda c: _call(c, work, attempt, state=state))


def test_a_call_goes_prepared_sent_completed_and_a_terminal_row_never_moves(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    work, attempt, call = _journal(engine)
    move = "UPDATE comparison_model_call SET {} WHERE comparison_model_call_id = :c"
    with engine.begin() as connection:
        connection.execute(text(move.format("state = 'sent', sent_at = clock_timestamp()")), {"c": call})
    with engine.begin() as connection:
        connection.execute(text(move.format(
            "state = 'completed', terminal_at = clock_timestamp(), response_sha256 = '" + SHA + "', "
            "input_tokens = 1, output_tokens = 1, latency_ms = 1, cost_basis = 'unmetered', cost_micros = 0, "
            "model_identity = model_identity")), {"c": call})
    for target in ("prepared", "sent", "unknown", "failed"):
        _refused(engine, lambda c: c.execute(text(move.format(f"state = '{target}'")), {"c": call}))


def test_a_call_that_may_have_been_sent_ends_unknown_and_is_never_sent_again(at_this: tuple[Engine, str]) -> None:
    """The reclaim path: ``prepared`` or ``sent`` without a completion becomes ``unknown``, and from there
    nothing moves (a person's «Повторить» is a new row)."""
    engine, _ = at_this
    work, attempt, call = _journal(engine)
    with engine.begin() as connection:
        second = _call(connection, work, attempt)
        connection.execute(text(
            "UPDATE comparison_model_call SET state = 'sent', sent_at = clock_timestamp() "
            "WHERE comparison_model_call_id = :c"), {"c": call})
    for row in (call, second):
        with engine.begin() as connection:
            connection.execute(text(
                "UPDATE comparison_model_call SET state = 'unknown', terminal_at = clock_timestamp() "
                "WHERE comparison_model_call_id = :c"), {"c": row})
        _refused(engine, lambda c: c.execute(text(
            "UPDATE comparison_model_call SET state = 'sent', sent_at = clock_timestamp() "
            "WHERE comparison_model_call_id = :c"), {"c": row}))
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT count(*) FROM comparison_model_call WHERE state = 'unknown'")).scalar_one() == 2


def test_the_journal_freezes_what_was_prepared(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    work, attempt, call = _journal(engine)
    for column, value in (("request_sha256", "'" + "b" * 64 + "'"), ("model_identity", "'other'"),
                          ("estimate_micros", "99"), ("provider_mode", "'live'")):
        _refused(engine, lambda c: c.execute(text(
            f"UPDATE comparison_model_call SET {column} = {value} WHERE comparison_model_call_id = :c"),
            {"c": call}), "AM003")


def test_a_completed_row_needs_its_response_tokens_and_cost(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    work, attempt, call = _journal(engine)
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE comparison_model_call SET state = 'sent', sent_at = clock_timestamp() "
            "WHERE comparison_model_call_id = :c"), {"c": call})
    _refused(engine, lambda c: c.execute(text(
        "UPDATE comparison_model_call SET state = 'completed', terminal_at = clock_timestamp() "
        "WHERE comparison_model_call_id = :c"), {"c": call}), "23514")


# -- decision 10: the part and its token -----------------------------------------------------------


def test_a_part_is_refused_for_a_file_with_no_multipart_token_and_the_token_is_write_once(
    at_this: tuple[Engine, str],
) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        project = _project(connection)["project"]
        _, bare = _file(connection, project)
        _, held = _file(connection, project, token="opaque-upload-id")
    insert = ("INSERT INTO comparison_upload_part (comparison_upload_file_id, part_number) VALUES (:f, 1)")
    _refused(engine, lambda c: c.execute(text(insert), {"f": bare}))
    with engine.begin() as connection:
        connection.execute(text(insert), {"f": held})
    _refused(engine, lambda c: c.execute(text(
        "UPDATE comparison_upload_file SET multipart_token = 'another' WHERE comparison_upload_file_id = :f"),
        {"f": held}), "AM003")
    # a part is inserted declared, and staging it needs its facts
    _refused(engine, lambda c: c.execute(text(
        "INSERT INTO comparison_upload_part (comparison_upload_file_id, part_number, state) "
        "VALUES (:f, 2, 'staged')"), {"f": held}))
    _refused(engine, lambda c: c.execute(text(
        "UPDATE comparison_upload_part SET state = 'staged' WHERE comparison_upload_file_id = :f"),
        {"f": held}), "23514")


def test_a_file_is_not_verified_without_its_blob_and_a_part_number_stays_in_range(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        project = _project(connection)["project"]
        _, file = _file(connection, project, token="t")
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE comparison_upload_file SET state = 'uploading' WHERE comparison_upload_file_id = :f"),
            {"f": file})
    _refused(engine, lambda c: c.execute(text(
        "UPDATE comparison_upload_file SET state = 'verified' WHERE comparison_upload_file_id = :f"),
        {"f": file}), "23514")
    for number in (0, 10001):
        _refused(engine, lambda c: c.execute(text(
            "INSERT INTO comparison_upload_part (comparison_upload_file_id, part_number) VALUES (:f, :n)"),
            {"f": file, "n": number}), "23514")


# -- decisions 14 and 16: the order revisions ------------------------------------------------------


def _order(connection: Any, ids: dict[str, str], *, number: int, versions: list[str]) -> None:
    import json
    connection.execute(text(
        "INSERT INTO comparison_version_order (comparison_version_order_id, project_uid, document_uid, "
        "revision_no, version_uids, source, actor_user_uid, actor_label, command_id) "
        "VALUES (:o, :p, :d, :n, CAST(:v AS jsonb), 'expert', :a, 'A', :c)"),
        {"o": _id("cvo"), "p": ids["project"], "d": ids["document"], "n": number, "v": json.dumps(versions),
         "a": ACTOR, "c": _command(connection)})


def test_the_order_revisions_are_numbered_without_a_gap_and_list_only_the_documents_versions(
    at_this: tuple[Engine, str],
) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _project(connection)
        _order(connection, ids, number=1, versions=[ids["version"], ids["version2"]])
        _order(connection, ids, number=2, versions=[ids["version2"], ids["version"]])
    _refused(engine, lambda c: _order(c, ids, number=4, versions=[ids["version"]]))
    _refused(engine, lambda c: _order(c, ids, number=2, versions=[ids["version"]]))  # a repeated number
    _refused(engine, lambda c: _order(c, ids, number=3, versions=[ids["version"], ids["version"]]))
    _refused(engine, lambda c: _order(c, ids, number=3, versions=[str(VersionUid.new())]))
    _refused(engine, lambda c: _order(c, ids, number=3, versions=[]), "23514")
    with engine.begin() as connection:
        other = _project(connection)
    _refused(engine, lambda c: _order(c, {**ids, "project": other["project"]}, number=3, versions=[ids["version"]]))


def test_an_order_revision_is_never_updated_or_deleted(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _project(connection)
        _order(connection, ids, number=1, versions=[ids["version"]])
    _refused(engine, lambda c: c.execute(text("UPDATE comparison_version_order SET source = 'proposal'")), "AM003")
    _refused(engine, lambda c: c.execute(text("DELETE FROM comparison_version_order")), "AM003")


def test_a_page_profile_needs_a_page_of_its_version_and_keeps_its_content_key(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _project(connection)

    def profile(connection: Any, *, page: int, key: str = SHA, algo: str = "v1") -> str:
        identity = _id("cpr")
        connection.execute(text(
            "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, page_number, "
            "content_key, algo_version, status) VALUES (:i, :v, :p, :k, :a, 'ready')"),
            {"i": identity, "v": ids["version"], "p": page, "k": key, "a": algo})
        return identity

    with engine.begin() as connection:
        identity = profile(connection, page=3)
    _refused(engine, lambda c: profile(c, page=4, key="c" * 64))  # the version has three pages
    _refused(engine, lambda c: profile(c, page=2), "23505")        # the same content key twice in one version
    _refused(engine, lambda c: profile(c, page=3, key="d" * 64), "23505")  # the same page and algorithm twice
    _refused(engine, lambda c: c.execute(text(
        "UPDATE comparison_page_profile SET content_key = :k WHERE comparison_page_profile_id = :i"),
        {"k": "e" * 64, "i": identity}), "AM003")


# -- decision 4: the queue ------------------------------------------------------------------------


def test_a_work_item_moves_only_along_the_declared_edges(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        project = _project(connection)["project"]
        work = _work(connection, project)
    update = "UPDATE comparison_work SET {} WHERE comparison_work_id = :w"
    _refused(engine, lambda c: c.execute(text(update.format("state = 'running'")), {"w": work}))
    _refused(engine, lambda c: c.execute(text(update.format("state = 'succeeded', terminal_at = now()")), {"w": work}))
    with engine.begin() as connection:
        connection.execute(text(update.format("state = 'leased'")), {"w": work})
        connection.execute(text(update.format("state = 'running'")), {"w": work})
        connection.execute(text(update.format("state = 'spend_unknown'")), {"w": work})
        connection.execute(text(update.format("state = 'queued'")), {"w": work})
    with engine.begin() as connection:
        connection.execute(text(update.format("state = 'cancelled', terminal_at = now()")), {"w": work})
    for target in ("queued", "leased", "running"):
        _refused(engine, lambda c: c.execute(text(update.format(f"state = '{target}'")), {"w": work}))


def test_a_terminal_state_carries_its_time_and_a_failure_its_reason(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        project = _project(connection)["project"]
        work = _work(connection, project, state="running")
    update = "UPDATE comparison_work SET {} WHERE comparison_work_id = :w"
    _refused(engine, lambda c: c.execute(text(update.format("state = 'succeeded'")), {"w": work}), "23514")
    _refused(engine, lambda c: c.execute(text(update.format("state = 'failed', terminal_at = now()")), {"w": work}),
             "23514")


def test_the_identity_of_a_work_item_and_of_an_attempt_is_frozen_and_a_live_attempt_needs_a_lease(
    at_this: tuple[Engine, str],
) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        project = _project(connection)["project"]
        work = _work(connection, project)
        attempt = _attempt(connection, work)
    _refused(engine, lambda c: c.execute(text(
        "UPDATE comparison_work SET kind = 'other_kind' WHERE comparison_work_id = :w"), {"w": work}), "AM003")
    _refused(engine, lambda c: c.execute(text(
        "UPDATE comparison_work_attempt SET execution_token = 'x' WHERE comparison_work_attempt_id = :a"),
        {"a": attempt}), "AM003")
    _refused(engine, lambda c: c.execute(text(
        "UPDATE comparison_work_attempt SET state = 'leased' WHERE comparison_work_attempt_id = :a"),
        {"a": attempt}), "23514")
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE comparison_work_attempt SET state = 'leased', lease_expires_at = now() + interval '60 s', "
            "heartbeat_at = now() WHERE comparison_work_attempt_id = :a"), {"a": attempt})


def test_a_second_live_item_with_the_same_dedupe_key_is_refused_until_the_first_is_terminal(
    at_this: tuple[Engine, str],
) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        project = _project(connection)["project"]
        first = _work(connection, project)
        connection.execute(text("UPDATE comparison_work SET state = state WHERE comparison_work_id = :w"), {"w": first})
    insert = ("INSERT INTO comparison_work (comparison_work_id, project_uid, module, kind, dedupe_key) "
              "VALUES (:w, :p, 'versions', 'profile_page', 'page-1')")
    with engine.begin() as connection:
        connection.execute(text(insert), {"w": _id("cq"), "p": project})
    _refused(engine, lambda c: c.execute(text(insert), {"w": _id("cq"), "p": project}), "23505")


# -- the executor task --------------------------------------------------------------------------------


def _task(connection: Any, *, origin: str, comparison_attempt: str | None, run: bool = False) -> str:
    connection_id, revision = str(ExecutorConnectionId.new()), str(ExecutorConnectionRevisionId.new())
    connection.execute(text(
        "INSERT INTO executor_connection (connection_id, kind, display_name, created_by) "
        "VALUES (:id, 'http_api', 'test', :actor)"), {"id": connection_id, "actor": ACTOR})
    connection.execute(text(
        "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, created_by, "
        "pin_id, gateway_model, billing, allow_client_documents, timeout_seconds, api_flavour, base_url, "
        "transport) VALUES (:r, :c, 1, :actor, 'claude-opus-5', 'anthropic/claude-opus-5', 'metered', false, 60, "
        "'openai_chat', 'https://proxy.test', 'direct')"), {"r": revision, "c": connection_id, "actor": ACTOR})
    task = _id("ext")
    connection.execute(text(
        "INSERT INTO executor_task (task_id, connection_id, revision_id, origin, comparison_attempt_id, "
        "expected_model, payload, deadline_at) VALUES (:t, :c, :r, :o, :a, 'anthropic/claude-opus-5', "
        "'{}'::jsonb, now() + interval '5 minutes')"),
        {"t": task, "c": connection_id, "r": revision, "o": origin, "a": comparison_attempt})
    return task


def test_an_executor_task_of_origin_comparison_call_names_its_attempt_and_only_that(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        project = _project(connection)["project"]
        work = _work(connection, project, state="running")
        attempt = _attempt(connection, work)
    with engine.begin() as connection:
        task = _task(connection, origin="comparison_call", comparison_attempt=attempt)
    _refused(engine, lambda c: _task(c, origin="comparison_call", comparison_attempt=None), "23514")
    _refused(engine, lambda c: _task(c, origin="probe", comparison_attempt=attempt), "23514")
    _refused(engine, lambda c: _task(c, origin="run_call", comparison_attempt=attempt), "23514")
    _refused(engine, lambda c: _task(c, origin="elsewhere", comparison_attempt=None), "23514")
    _refused(engine, lambda c: c.execute(text(
        "UPDATE executor_task SET comparison_attempt_id = NULL WHERE task_id = :t"), {"t": task}), "AM003")


def test_the_frozen_guard_of_the_task_names_the_new_column_and_keeps_the_old_ones(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.connect() as connection:
        definition = connection.execute(text(
            "SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname = 'trg_executor_task_frozen_guard'"
        )).scalar_one()
    for column in ("comparison_attempt_id", "attempt_id", "origin", "probe_id", "task_id"):
        assert f"'{column}'" in definition, definition


# -- the downgrade --------------------------------------------------------------------------------------


def test_the_downgrade_is_refused_while_any_row_exists_and_only_then_and_gives_back_0037(
    at_this: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_this
    after = _tables(engine)
    with engine.begin() as connection:
        project = _project(connection)["project"]
        work = _work(connection, project)
    refused = _run(foundation_command, url, "downgrade", PREVIOUS)
    assert refused.returncode != 0 and "0038 downgrade refused" in refused.describe()
    assert "comparison_work=1" in refused.describe()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM comparison_work WHERE comparison_work_id = :w"), {"w": work})
    done = _run(foundation_command, url, "downgrade", PREVIOUS)
    assert done.returncode == 0, done.describe()
    assert _tables(engine) == after - set(TABLES)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
        assert connection.execute(text(
            "SELECT count(*) FROM information_schema.columns WHERE table_name = 'document_version' "
            "AND column_name = 'upload_kind'")).scalar_one() == 0
        assert connection.execute(text(
            "SELECT count(*) FROM information_schema.columns WHERE table_name = 'executor_task' "
            "AND column_name = 'comparison_attempt_id'")).scalar_one() == 0
        origin = connection.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'ck_executor_task_origin'"
        )).scalar_one()
    assert "comparison_call" not in origin
    _upgrade(foundation_command, url, THIS)
    assert set(TABLES) <= _tables(engine)


def test_a_comparison_pdf_version_or_a_comparison_task_also_blocks_the_downgrade(
    at_this: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_this
    with engine.begin() as connection:
        ids = _project(connection)
        connection.execute(text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
            "sha256, page_count, upload_kind) VALUES (:v, :d, 3, 'application/pdf', 1, :sha, 1, 'comparison_pdf')"),
            {"v": str(VersionUid.new()), "d": ids["document"], "sha": SHA})
    refused = _run(foundation_command, url, "downgrade", PREVIOUS)
    assert refused.returncode != 0 and "document_version (comparison_pdf)=1" in refused.describe()
