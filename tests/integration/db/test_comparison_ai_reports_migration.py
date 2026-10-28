"""`CMP-SEAL-C2`: ``0040_comparison_ai_reports`` on a ``0039`` database.

Twelve tables, one column of ``comparison_work`` and a widened ``ck_executor_route_work_kind``. Against real
PostgreSQL rows written through plain INSERTs, each rule shown failing:

* **decision 15**: the pair-check answers, the sheet descriptions and the specification extractions are unique by
  content **within a project** (``UNIQUE (project_uid, content_key)``) and only within it, and are immutable;
* **decision 19**: a job holds the estimate it consented to; the consent columns change only together and only by one
  consent number; at most one live job per scope; a job moves only along its declared edges;
* **decisions 3 and 20**: a question names a build and pages of its own document, points at the accepted link only when
  it was accepted, and an answered question has an answer; a sheet item is done only with a description;
* **a report** is a draft without a job and a started one with it, a client report is prepared from an analytic report of
  the same series, its files are append-only;
* **the launch queue** keeps one live entry per set and step, and only an AI step carries a consent;
* **decision 17**: the executor route accepts the four ``comparison_*`` work kinds beside ``text_analysis`` and nothing
  else (``comparison_stage_review`` is `CMP-SEAL-C4`'s);
* **decision 7**: every new table is reachable from ``project`` by foreign keys;
* **the new column**: ``comparison_work.comparison_ai_job_id`` is frozen once written and equals the item's payload
  ``ai_job_id`` (the key `CMP-SPEND-01` sums for the ceilings);
* **the downgrade** is refused while any row exists, and gives back the ``0039`` schema.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid, new_ulid
from tests.support.expected_facts import FACTS

THIS = "0040_comparison_ai_reports"
PREVIOUS = "0039_comparison_core"
ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SHA = "a" * 64
TABLES = (
    "comparison_ai_job", "comparison_ai_pair_answer", "comparison_ai_pair_question",
    "comparison_sheet_description", "comparison_ai_sheet_item", "comparison_spec_extraction",
    "comparison_spec_comparison", "comparison_report", "comparison_report_part", "comparison_report_artifact",
    "comparison_launch_queue", "comparison_launch_entry",
)
KINDS_NOW = ("text_analysis", "comparison_pair_check", "comparison_sheet_changes", "comparison_spec", "comparison_report")


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


def _x(connection: Any, sql: str, **values: Any) -> None:
    connection.execute(text(sql), values)


def _command(connection: Any, kind: str = "start_comparison_ai_pair_check") -> str:
    command = _id("cmd")
    _x(connection, "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
                   "VALUES (:c, :t, :k, :f)", c=command, t=kind, k=_id("k")[:20], f=SHA)
    return command


def _world(connection: Any, versions: int = 3) -> dict[str, Any]:
    """A project with a document of ``versions`` versions, a build, a series with a transition, two page profiles, a
    sheet pair with its result, and an executor connection revision."""
    ids: dict[str, Any] = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()), "versions": []}
    _x(connection, "INSERT INTO project (project_uid, name) VALUES (:project, 'ai')", **ids)
    _x(connection, "INSERT INTO document (document_uid, project_uid, display_title) VALUES (:document, :project, 'D')", **ids)
    for number in range(1, versions + 1):
        version = str(VersionUid.new())
        ids["versions"].append(version)
        _x(connection, "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
                       "byte_size, sha256, page_count) VALUES (:v, :document, :n, 'application/pdf', 1, :sha, 5)",
           v=version, document=ids["document"], n=number, sha=SHA)
    ids["build"] = _id("cmx")
    _x(connection, "INSERT INTO comparison_matrix (comparison_matrix_id, project_uid, document_uid, build_no, "
                   "profile_signature, rules_version, algo_version, rows) VALUES (:m, :p, :d, 1, :s, 'v1.2', 'm1', '[]')",
       m=ids["build"], p=ids["project"], d=ids["document"], s=SHA)
    ids["series"], ids["transition"] = _id("cser"), _id("ctn")
    _x(connection, "INSERT INTO comparison_series (comparison_series_id, project_uid, document_uid, comparison_matrix_id, "
                   "matrix_edit_no, input_sha256, actor_user_uid, actor_label, command_id) "
                   "VALUES (:s, :p, :d, :m, 0, :sha, :a, 'A', :c)", s=ids["series"], p=ids["project"],
       d=ids["document"], m=ids["build"], sha=SHA, a=ACTOR, c=_command(connection, "start_comparison_series"))
    _x(connection, "INSERT INTO comparison_transition (comparison_transition_id, comparison_series_id, transition_no, "
                   "source_version_uid, target_version_uid) VALUES (:t, :s, 1, :v1, :v2)",
       t=ids["transition"], s=ids["series"], v1=ids["versions"][0], v2=ids["versions"][1])
    ids["page_a"], ids["page_b"] = _id("cpr"), _id("cpr")
    for profile, version, key in ((ids["page_a"], ids["versions"][0], "1" * 64), (ids["page_b"], ids["versions"][1], "2" * 64)):
        _x(connection, "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, page_number, "
                       "content_key, algo_version, status) VALUES (:i, :v, 1, :k, 'p1', 'ready')", i=profile, v=version, k=key)
    ids["result"], ids["pair"] = _id("csp"), _id("ctp")
    _x(connection, "INSERT INTO comparison_sheet_pair_result (comparison_sheet_pair_result_id, project_uid, content_key, "
                   "algo_version, status, page_a_profile_id, page_b_profile_id) VALUES (:r, :p, :k, 'vc1', 'different', :a, :b)",
       r=ids["result"], p=ids["project"], k=SHA, a=ids["page_a"], b=ids["page_b"])
    _x(connection, "INSERT INTO comparison_sheet_pair (comparison_sheet_pair_id, comparison_transition_id, pair_no, "
                   "page_a_profile_id, page_b_profile_id) VALUES (:x, :t, 1, :a, :b)",
       x=ids["pair"], t=ids["transition"], a=ids["page_a"], b=ids["page_b"])
    ids["connection"], ids["revision"] = _id("exc"), _id("excr")
    _x(connection, "INSERT INTO executor_connection (connection_id, kind, display_name, created_by) "
                   "VALUES (:id, 'http_api', 'test', :a)", id=ids["connection"], a=ACTOR)
    _x(connection, "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, created_by, pin_id, "
                   "gateway_model, billing, allow_client_documents, timeout_seconds, api_flavour, base_url, transport) "
                   "VALUES (:r, :c, 1, :a, 'claude-opus-5', 'anthropic/claude-opus-5', 'metered', false, 60, "
                   "'openai_chat', 'https://proxy.test', 'direct')", r=ids["revision"], c=ids["connection"], a=ACTOR)
    return ids


def _job(connection: Any, ids: dict[str, Any], method: str, **scope: Any) -> str:
    """One job of ``method`` with the scope the method needs, unless ``scope`` says otherwise."""
    default = {
        "pair_check": {"matrix": ids["build"]}, "sheet_changes": {"series": ids["series"]},
        "spec": {"transition": ids["transition"]}, "report": {"series": ids["series"]},
    }[method]
    scope = {} if "none" in scope else {**default, **scope}
    job = _id("cai")
    _x(connection,
       "INSERT INTO comparison_ai_job (comparison_ai_job_id, project_uid, document_uid, method, comparison_matrix_id, "
       "comparison_series_id, comparison_transition_id, comparison_sheet_pair_id, connection_revision_id, pinned_model, "
       "provider_mode, estimate, estimate_digest, estimate_micros, ceiling_micros, consented_by_user_uid, command_id) "
       "VALUES (:j, :p, :d, :m, :cmx, :cser, :ctn, :ctp, :rev, 'claude-opus-5', 'live', CAST(:est AS jsonb), :dig, 1000000, "
       "10000000, :a, :c)",
       j=job, p=ids["project"], d=ids["document"], m=method, cmx=scope.get("matrix"), cser=scope.get("series"),
       ctn=scope.get("transition"), ctp=scope.get("pair"), rev=ids["revision"],
       est=json.dumps({"estimate_digest": SHA, "units": 3}), dig=SHA, a=ACTOR,
       c=_command(connection, f"start_comparison_{method}"))
    return job


def _walk(connection: Any, job: str, *states: str) -> None:
    for state in states:
        extra = ", pause_reason = 'user'" if state == "paused" else ""
        extra += ", failure_reason = 'some_reason'" if state == "failed" else ""
        extra += ", finished_at = now()" if state in ("completed", "failed", "cancelled") else ""
        _x(connection, f"UPDATE comparison_ai_job SET state = '{state}'{extra} WHERE comparison_ai_job_id = :j", j=job)


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


# -- the step -----------------------------------------------------------------------------------------


def test_the_head_of_the_tree_is_this_revision_or_a_later_one() -> None:
    assert FACTS.migration_head >= THIS


def test_the_revision_id_fits_the_version_column() -> None:
    assert len(THIS) <= 32


def test_the_step_adds_the_objects_and_changes_no_stored_row(
    at_previous: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_previous
    with engine.begin() as connection:
        _world(connection)
    before = {table: _count(engine, table) for table in ("project", "document", "document_version", "comparison_series")}
    assert not set(TABLES) & _tables(engine)
    _upgrade(foundation_command, url, THIS)
    assert set(TABLES) <= _tables(engine)
    assert {table: _count(engine, table) for table in before} == before
    assert all(_count(engine, table) == 0 for table in TABLES)
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT is_nullable FROM information_schema.columns WHERE table_name = 'comparison_work' "
            "AND column_name = 'comparison_ai_job_id'")).scalar_one() == "YES"


# -- decision 17: the executor work kinds -----------------------------------------------------------------


def _route(connection: Any, kind: str, number: int = 1) -> None:
    primary = _id("exc")
    _x(connection, "INSERT INTO executor_connection (connection_id, kind, display_name, created_by) "
                   "VALUES (:id, 'http_api', 'route', :a)", id=primary, a=ACTOR)
    _x(connection, "INSERT INTO executor_route_event (route_event_id, work_kind, route_no, primary_connection_id, set_by) "
                   "VALUES (:e, :k, :n, :c, :a)", e=_id("ert"), k=kind, n=number, c=primary, a=ACTOR)


def test_the_executor_route_accepts_the_four_comparison_kinds_and_nothing_else(
    at_previous: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_previous
    _refused(engine, lambda c: _route(c, "comparison_pair_check"), "23514")  # the single kind of 0039
    _upgrade(foundation_command, url, THIS)
    with engine.begin() as connection:
        for kind in KINDS_NOW:
            _route(connection, kind, 1)
    for bad in ("comparison_stage_review", "comparison_", "other", ""):
        _refused(engine, lambda c, k=bad: _route(c, k, 2), "23514")


# -- decision 15: content keys include the project -------------------------------------------------------


def _answer(connection: Any, project: str, key: str = SHA, kind: str = "no_pair") -> str:
    answer = _id("cpa")
    _x(connection, "INSERT INTO comparison_ai_pair_answer (comparison_ai_pair_answer_id, project_uid, content_key, "
                   "question_kind, prompt_version, model_identity, confidence, answer) "
                   "VALUES (:i, :p, :k, :q, 'vcsm-p3', 'claude-opus-5', 'high', CAST(:a AS jsonb))",
       i=answer, p=project, k=key, q=kind, a=json.dumps({"choice": 1, "page": 3}))
    return answer


def _description(connection: Any, ids: dict[str, Any], key: str = SHA, *, result: str | None = "default",
                 page: str | None = None) -> str:
    description = _id("csd")
    _x(connection, "INSERT INTO comparison_sheet_description (comparison_sheet_description_id, project_uid, content_key, "
                   "result_id, page_profile_id, state, prompt_version, model_identity, description) "
                   "VALUES (:i, :p, :k, :r, :pg, 'done', 'sc-p1', 'claude-opus-5', CAST(:d AS jsonb))",
       i=description, p=ids["project"], k=key, r=ids["result"] if result == "default" else result, pg=page,
       d=json.dumps({"changes": []}))
    return description


def _extraction(connection: Any, ids: dict[str, Any], key: str = SHA, version: int = 0) -> str:
    extraction = _id("cse")
    _x(connection, "INSERT INTO comparison_spec_extraction (comparison_spec_extraction_id, project_uid, version_uid, content_key, "
                   "state, prompt_version, model_identity, source_sha256, positions, coverage) "
                   "VALUES (:i, :p, :v, :k, 'complete', 'ws-1', 'claude-opus-5', :sha, '[]'::jsonb, '{}'::jsonb)",
       i=extraction, p=ids["project"], v=ids["versions"][version], k=key, sha=SHA)
    return extraction


def test_a_content_key_is_unique_within_a_project_and_only_within_it(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        first, second = _world(connection), _world(connection)
        _answer(connection, first["project"])
        _description(connection, first)
        _extraction(connection, first)
    _refused(engine, lambda c: _answer(c, first["project"]), "23505")
    _refused(engine, lambda c: _description(c, first), "23505")
    _refused(engine, lambda c: _extraction(c, first), "23505")
    with engine.begin() as connection:  # the same content in another project is another row
        _answer(connection, second["project"])
        _description(connection, second)
        _extraction(connection, second)
        _answer(connection, first["project"], key="b" * 64)
    assert (_count(engine, "comparison_ai_pair_answer"), _count(engine, "comparison_sheet_description"),
            _count(engine, "comparison_spec_extraction")) == (3, 2, 2)


def test_the_stored_answers_descriptions_extractions_and_files_are_immutable(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _world(connection)
        answer = _answer(connection, ids["project"])
        description = _description(connection, ids)
        extraction = _extraction(connection, ids)
    for table, key, ident, column in (
        ("comparison_ai_pair_answer", "comparison_ai_pair_answer_id", answer, "prompt_version"),
        ("comparison_sheet_description", "comparison_sheet_description_id", description, "prompt_version"),
        ("comparison_spec_extraction", "comparison_spec_extraction_id", extraction, "prompt_version"),
    ):
        _refused(engine, lambda c, t=table, k=key, i=ident, col=column: c.execute(
            text(f"UPDATE {t} SET {col} = 'x' WHERE {k} = :i"), {"i": i}), "AM003")
        _refused(engine, lambda c, t=table, k=key, i=ident: c.execute(
            text(f"DELETE FROM {t} WHERE {k} = :i"), {"i": i}), "AM003")


def test_a_description_describes_one_subject_of_its_own_project(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids, other = _world(connection), _world(connection)
    _refused(engine, lambda c: _description(c, ids, "1" * 64, result=None), "23514")  # neither a result nor a page
    _refused(engine, lambda c: _description(c, ids, "2" * 64, page=ids["page_a"]), "23514")  # both
    _refused(engine, lambda c: _description(c, other, "3" * 64, result=ids["result"]))  # a result of another project
    _refused(engine, lambda c: _description(c, other, "4" * 64, result=None, page=ids["page_a"]))  # a page of another
    with engine.begin() as connection:  # an added or removed sheet is described by its page
        _description(connection, ids, "5" * 64, result=None, page=ids["page_b"])


def test_an_extraction_is_of_a_version_of_its_own_project(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids, other = _world(connection), _world(connection)
    _refused(engine, lambda c: _extraction(c, {**other, "versions": ids["versions"]}))


# -- decision 19: the consented job ----------------------------------------------------------------------


def test_a_job_has_the_scope_its_method_needs(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _world(connection)
    for method, bad in (
        ("pair_check", {"none": True}), ("pair_check", {"matrix": ids["build"], "series": ids["series"]}),
        ("sheet_changes", {"none": True}), ("sheet_changes", {"series": ids["series"], "pair": ids["pair"]}),
        ("spec", {"none": True}), ("spec", {"transition": ids["transition"], "series": ids["series"]}),
        ("report", {"none": True}), ("report", {"series": ids["series"], "transition": ids["transition"]}),
    ):
        _refused(engine, lambda c, m=method, s=bad: _job(c, ids, m, **s), "23514")
    with engine.begin() as connection:
        for method in ("pair_check", "sheet_changes", "spec", "report"):
            _walk(connection, _job(connection, ids, method), "running", "completed")
        _walk(connection, _job(connection, ids, "sheet_changes", series=None, pair=ids["pair"]), "running", "completed")
    assert _count(engine, "comparison_ai_job") == 5


def test_a_job_names_a_scope_of_its_own_document(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids, other = _world(connection), _world(connection)
    _refused(engine, lambda c: _job(c, ids, "pair_check", matrix=other["build"]))
    _refused(engine, lambda c: _job(c, ids, "sheet_changes", series=other["series"]))
    _refused(engine, lambda c: _job(c, ids, "spec", transition=other["transition"]))
    _refused(engine, lambda c: _job(c, ids, "sheet_changes", series=None, pair=other["pair"]))


def test_a_document_has_one_live_job_per_scope_and_a_finished_job_makes_room(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _world(connection)
        first = _job(connection, ids, "pair_check")
        _job(connection, ids, "sheet_changes")
        _job(connection, ids, "spec")
        _job(connection, ids, "sheet_changes", series=None, pair=ids["pair"])
    _refused(engine, lambda c: _job(c, ids, "pair_check"), "23505")
    _refused(engine, lambda c: _job(c, ids, "sheet_changes"), "23505")
    _refused(engine, lambda c: _job(c, ids, "spec"), "23505")
    _refused(engine, lambda c: _job(c, ids, "sheet_changes", series=None, pair=ids["pair"]), "23505")
    with engine.begin() as connection:
        _walk(connection, first, "running", "completed")
        _job(connection, ids, "pair_check")
        _job(connection, ids, "report")
        _job(connection, ids, "report")  # reports are not limited by a job index: the report row owns its job


def test_a_job_moves_only_along_its_declared_edges_and_a_pause_names_its_reason(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _world(connection)
        job = _job(connection, ids, "spec")
    _refused(engine, lambda c: _walk(c, job, "completed"))  # queued -> completed
    _refused(engine, lambda c: _x(c, "UPDATE comparison_ai_job SET state = 'paused' WHERE comparison_ai_job_id = :j", j=job),
            "23514")  # a pause without its reason
    with engine.begin() as connection:
        _walk(connection, job, "running", "paused")
        _x(connection, "UPDATE comparison_ai_job SET state = 'queued', pause_reason = NULL WHERE comparison_ai_job_id = :j", j=job)
        _walk(connection, job, "running", "completed")
        _x(connection, "UPDATE comparison_ai_job SET state = 'queued', finished_at = NULL WHERE comparison_ai_job_id = :j", j=job)
    _refused(engine, lambda c: _x(c, "UPDATE comparison_ai_job SET state = 'failed', finished_at = now() "
                                     "WHERE comparison_ai_job_id = :j", j=job), "23514")  # failed holds its reason


def test_the_consented_estimate_changes_only_with_a_new_consent(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _world(connection)
        job = _job(connection, ids, "pair_check")

    def change(connection: Any, consent_no: int, digest: str = "b" * 64) -> None:
        _x(connection, "UPDATE comparison_ai_job SET estimate = CAST(:e AS jsonb), estimate_digest = :d, estimate_micros = 2000000, "
                       "consent_no = :n WHERE comparison_ai_job_id = :j", e=json.dumps({"estimate_digest": digest, "units": 4}),
           d=digest, n=consent_no, j=job)

    _refused(engine, lambda c: change(c, 1))  # the same consent number
    _refused(engine, lambda c: change(c, 3))  # a jump
    _refused(engine, lambda c: change(c, 0))  # backwards
    _refused(engine, lambda c: _x(
        c, "UPDATE comparison_ai_job SET estimate_digest = :d, consent_no = 2 WHERE comparison_ai_job_id = :j",
        d="c" * 64, j=job), "23514")  # the digest must be the estimate's own
    with engine.begin() as connection:
        change(connection, 2)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT consent_no, estimate_digest FROM comparison_ai_job WHERE comparison_ai_job_id = :j"),
                                  {"j": job}).one() == (2, "b" * 64)
    _refused(engine, lambda c: _x(c, "UPDATE comparison_ai_job SET method = 'spec' WHERE comparison_ai_job_id = :j", j=job), "AM003")
    _refused(engine, lambda c: _x(c, "UPDATE comparison_ai_job SET command_id = :c WHERE comparison_ai_job_id = :j",
                                  c=_command(c), j=job), "AM003")


# -- the pair check ---------------------------------------------------------------------------------------


def _question(connection: Any, ids: dict[str, Any], job: str, *, page: int = 1, version: int = 1, **columns: Any) -> str:
    question = _id("cpq")
    values = {"i": question, "j": job, "p": ids["project"], "d": ids["document"], "m": ids["build"],
              "pv": ids["versions"][0], "pn": page, "v": ids["versions"][version]}
    values.update(columns)
    _x(connection, "INSERT INTO comparison_ai_pair_question (comparison_ai_pair_question_id, comparison_ai_job_id, project_uid, "
                   "document_uid, comparison_matrix_id, kind, page_version_uid, page_number, version_uid) "
                   "VALUES (:i, :j, :p, :d, :m, 'no_pair', :pv, :pn, :v)", **values)
    return question


def test_a_question_belongs_to_a_pair_check_of_its_build_and_names_pages_of_its_document(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids, other = _world(connection), _world(connection)
        job = _job(connection, ids, "pair_check")
        sheets = _job(connection, ids, "sheet_changes")
        _question(connection, ids, job)
    _refused(engine, lambda c: _question(c, ids, job), "23505")  # one question per cell per job
    _refused(engine, lambda c: _question(c, ids, sheets, page=2))  # a job of another method
    _refused(engine, lambda c: _question(c, ids, job, page=6))  # page 6 of a five-page version
    _refused(engine, lambda c: _question(c, ids, job, page=2, v=other["versions"][1]))  # a version of another document
    _refused(engine, lambda c: _question(c, ids, job, page=2, version=0), "23514")  # a cell of its own version
    _refused(engine, lambda c: _question(c, ids, job, page=2, m=other["build"]))  # a build of another document


def test_a_question_is_answered_with_an_answer_and_links_only_what_was_accepted(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _world(connection)
        job = _job(connection, ids, "pair_check")
        question = _question(connection, ids, job)
        answer = _answer(connection, ids["project"])
        link = _id("cak")
        _x(connection, "INSERT INTO comparison_ai_link (comparison_ai_link_id, document_uid, comparison_matrix_id, page_version_uid, "
                       "page_number, other_version_uid, other_page_number, answered_state) "
                       "VALUES (:k, :d, :m, :v1, 1, :v2, 3, 'unmatched')", k=link, d=ids["document"], m=ids["build"],
           v1=ids["versions"][0], v2=ids["versions"][1])
    answered = "UPDATE comparison_ai_pair_question SET state = 'answered', answer_id = :a, decision = :dec{extra} WHERE comparison_ai_pair_question_id = :q"
    _refused(engine, lambda c: _x(c, answered.format(extra=""), a=None, dec="none", q=question), "23514")  # answered without an answer
    _refused(engine, lambda c: _x(c, "UPDATE comparison_ai_pair_question SET state = 'answered', answer_id = :a WHERE "
                                     "comparison_ai_pair_question_id = :q", a=answer, q=question), "23514")  # without a decision
    _refused(engine, lambda c: _x(c, answered.format(extra=", comparison_ai_link_id = :l"), a=answer, dec="hint_table",
                                  q=question, l=link), "23514")  # a link only for an accepted decision
    with engine.begin() as connection:
        _x(connection, answered.format(extra=", comparison_ai_link_id = :l, hint_version_uid = :hv, hint_page_number = 3"),
           a=answer, dec="link_accepted", q=question, l=link, hv=ids["versions"][1])
    _refused(engine, lambda c: _x(c, "UPDATE comparison_ai_pair_question SET state = 'queued' WHERE "
                                     "comparison_ai_pair_question_id = :q", q=question))  # an answered question is final
    _refused(engine, lambda c: _x(c, "UPDATE comparison_ai_pair_question SET page_number = 2 WHERE "
                                     "comparison_ai_pair_question_id = :q", q=question), "AM003")


# -- the sheet descriptions -------------------------------------------------------------------------------


def test_a_sheet_item_is_done_only_with_a_description_and_once_per_job(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _world(connection)
        job = _job(connection, ids, "sheet_changes")
        pair_check = _job(connection, ids, "pair_check")
        description = _description(connection, ids)
        item = _id("csi")
        _x(connection, "INSERT INTO comparison_ai_sheet_item (comparison_ai_sheet_item_id, comparison_ai_job_id, project_uid, "
                       "comparison_sheet_pair_id) VALUES (:i, :j, :p, :x)", i=item, j=job, p=ids["project"], x=ids["pair"])

    def insert(connection: Any, job_id: str, pair: str) -> None:
        _x(connection, "INSERT INTO comparison_ai_sheet_item (comparison_ai_sheet_item_id, comparison_ai_job_id, project_uid, "
                       "comparison_sheet_pair_id) VALUES (:i, :j, :p, :x)", i=_id("csi"), j=job_id, p=ids["project"], x=pair)

    _refused(engine, lambda c: insert(c, job, ids["pair"]), "23505")
    _refused(engine, lambda c: insert(c, pair_check, ids["pair"]))  # a job of another method
    _x_done = "UPDATE comparison_ai_sheet_item SET state = 'done'{extra} WHERE comparison_ai_sheet_item_id = :i"
    with engine.begin() as connection:
        _x(connection, "UPDATE comparison_ai_sheet_item SET state = 'running' WHERE comparison_ai_sheet_item_id = :i", i=item)
    _refused(engine, lambda c: _x(c, _x_done.format(extra=""), i=item), "23514")
    with engine.begin() as connection:
        _x(connection, _x_done.format(extra=", comparison_sheet_description_id = :d"), i=item, d=description)
    _refused(engine, lambda c: _x(c, "UPDATE comparison_ai_sheet_item SET state = 'queued' WHERE "
                                     "comparison_ai_sheet_item_id = :i", i=item))  # a finished item is never queued again


# -- specifications ---------------------------------------------------------------------------------------


def _spec(connection: Any, ids: dict[str, Any], source: str, **columns: Any) -> str:
    comparison = _id("cscp")
    values = {"i": comparison, "p": ids["project"], "d": ids["document"], "t": ids["transition"], "s": source,
              "j": None, "ea": None, "eb": None}
    values.update(columns)
    _x(connection, "INSERT INTO comparison_spec_comparison (comparison_spec_comparison_id, project_uid, document_uid, "
                   "comparison_transition_id, source, comparison_ai_job_id, extraction_a_id, extraction_b_id) "
                   "VALUES (:i, :p, :d, :t, :s, :j, :ea, :eb)", **values)
    return comparison


def test_a_specification_comparison_has_the_shape_its_source_needs_and_is_unique_per_transition_and_source(
    at_this: tuple[Engine, str],
) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids, other = _world(connection), _world(connection)
        job = _job(connection, ids, "spec")
        older, newer = _extraction(connection, ids, "1" * 64, 0), _extraction(connection, ids, "2" * 64, 1)
        _spec(connection, ids, "positions")
        whole = _spec(connection, ids, "whole", j=job, ea=older, eb=newer)
        wrong_job = _job(connection, ids, "pair_check")
    _refused(engine, lambda c: _spec(c, ids, "positions"), "23505")
    _refused(engine, lambda c: _spec(c, ids, "whole", j=job), "23505")
    _refused(engine, lambda c: _spec(c, ids, "positions", j=job), "23514")  # deterministic: no job, no extraction
    _refused(engine, lambda c: _spec(c, ids, "whole"), "23514")  # a whole comparison needs its job
    _refused(engine, lambda c: _spec(c, other, "whole", j=job))  # a job of another transition
    _refused(engine, lambda c: _spec(c, ids, "whole", j=wrong_job))  # a job of another method
    _refused(engine, lambda c: _x(c, "UPDATE comparison_spec_comparison SET state = 'completed' WHERE "
                                     "comparison_spec_comparison_id = :i", i=whole))  # queued -> completed

    def fail_without_a_reason(connection: Any) -> None:
        _x(connection, "UPDATE comparison_spec_comparison SET state = 'running' WHERE comparison_spec_comparison_id = :i", i=whole)
        _x(connection, "UPDATE comparison_spec_comparison SET state = 'failed' WHERE comparison_spec_comparison_id = :i", i=whole)

    _refused(engine, fail_without_a_reason, "23514")  # a failure names its reason


def test_a_comparison_names_extractions_of_the_two_versions_of_its_transition(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _world(connection)
        job = _job(connection, ids, "spec")
        older, newer = _extraction(connection, ids, "1" * 64, 0), _extraction(connection, ids, "2" * 64, 1)
    _refused(engine, lambda c: _spec(c, ids, "whole", j=job, ea=newer, eb=older))  # swapped sides


# -- reports ----------------------------------------------------------------------------------------------


def _report(connection: Any, ids: dict[str, Any], *, kind: str = "client", job: str | None = None, state: str = "draft",
            prepared_from: str | None = None, digest: str = SHA) -> str:
    report = _id("crt")
    _x(connection, "INSERT INTO comparison_report (comparison_report_id, project_uid, document_uid, comparison_series_id, kind, "
                   "source, state, comparison_ai_job_id, estimate, estimate_digest, source_sha256, prepared_from_report_id, "
                   "actor_user_uid, actor_label, command_id) VALUES (:r, :p, :d, :s, :k, 'series_summary', :st, :j, "
                   "CAST(:e AS jsonb), :dig, :sha, :pf, :a, 'A', :c)",
       r=report, p=ids["project"], d=ids["document"], s=ids["series"], k=kind, st=state, j=job,
       e=json.dumps({"estimate_digest": digest}), dig=digest, sha=SHA, pf=prepared_from, a=ACTOR,
       c=_command(connection, "create_comparison_report"))
    return report


def test_a_report_is_a_draft_without_a_job_and_a_started_one_with_it(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids, other = _world(connection), _world(connection)
        job = _job(connection, ids, "report")
        analytic = _report(connection, ids, kind="analytic")
        _x(connection, "UPDATE comparison_report SET state = 'queued', comparison_ai_job_id = :j WHERE comparison_report_id = :r",
           j=job, r=analytic)
    _refused(engine, lambda c: _report(c, ids, job=job), "23514")  # a draft with a job
    _refused(engine, lambda c: _report(c, ids, state="queued"), "23514")  # a started one without
    _refused(engine, lambda c: _x(
        c, "UPDATE comparison_report SET estimate_digest = :d WHERE comparison_report_id = :r", d="c" * 64, r=analytic), "AM003")
    _refused(engine, lambda c: _report(c, ids, state="queued", job=_job(c, ids, "pair_check")))  # a job of another method
    _refused(engine, lambda c: _report(c, other, state="queued", job=job))  # a job of another series
    with engine.begin() as connection:
        client = _report(connection, ids, prepared_from=analytic)
    _refused(engine, lambda c: _report(c, ids, kind="analytic", prepared_from=analytic), "23514")  # prepared is a client
    _refused(engine, lambda c: _report(c, ids, prepared_from=client))  # from an analytic report only
    _refused(engine, lambda c: _report(c, ids, prepared_from=_report(c, other, kind="analytic")))  # of its own series
    _refused(engine, lambda c: _x(c, "UPDATE comparison_report SET state = 'completed' WHERE comparison_report_id = :r",
                                  r=client))  # draft -> completed


def test_a_report_part_names_a_transition_of_its_series_and_a_file_is_append_only(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids, other = _world(connection), _world(connection)
        report = _report(connection, ids)
        _x(connection, "INSERT INTO comparison_report_part (comparison_report_part_id, comparison_report_id, "
                       "comparison_transition_id, analysis) VALUES (:i, :r, :t, 'running')",
           i=_id("crpt"), r=report, t=ids["transition"])
    _refused(engine, lambda c: _x(c, "INSERT INTO comparison_report_part (comparison_report_part_id, comparison_report_id, "
                                     "comparison_transition_id) VALUES (:i, :r, :t)", i=_id("crpt"), r=report,
                                  t=other["transition"]))
    part = ("INSERT INTO comparison_report_part (comparison_report_part_id, comparison_report_id, comparison_transition_id, "
            "analysis) VALUES (:i, :r, :t, :a)")
    _refused(engine, lambda c: _x(c, part, i=_id("crpt"), r=report, t=ids["transition"], a="maybe"), "23514")
    _refused(engine, lambda c: _x(c, part, i=_id("crpt"), r=report, t=ids["transition"], a="done"), "23505")  # once per transition
    _refused(engine, lambda c: _x(c, "INSERT INTO comparison_report_artifact (comparison_report_artifact_id, comparison_report_id, "
                                     "kind, blob_id, sha256, size_bytes) VALUES (:i, :r, 'report_pdf', :b, :sha, 1)",
                                  i=_id("cra"), r=report, b=_id("blob"), sha=SHA), "23503")  # a blob that does not exist


# -- the launch queue -------------------------------------------------------------------------------------


def _entry(connection: Any, ids: dict[str, Any], step: str, **columns: Any) -> str:
    entry = _id("cle")
    values = {"i": entry, "p": ids["project"], "d": ids["document"], "s": step, "pos": 1, "dig": None,
              "a": ACTOR, "c": _command(connection, "enqueue_comparison_launch")}
    values.update(columns)
    _x(connection, "INSERT INTO comparison_launch_entry (comparison_launch_entry_id, project_uid, document_uid, step, position, "
                   "consent_digest, actor_user_uid, actor_label, command_id) VALUES (:i, :p, :d, :s, :pos, :dig, :a, 'A', :c)",
       **values)
    return entry


def test_the_launch_queue_keeps_one_live_entry_per_set_and_step_and_consent_only_for_an_ai_step(
    at_this: tuple[Engine, str],
) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids, other = _world(connection), _world(connection)
        _x(connection, "INSERT INTO comparison_launch_queue (project_uid) VALUES (:p)", p=ids["project"])
        first = _entry(connection, ids, "series")
        _entry(connection, ids, "ai_changes", dig=SHA, pos=2)
    _refused(engine, lambda c: _entry(c, ids, "series", pos=3), "23505")
    _refused(engine, lambda c: _entry(c, ids, "upload"), "23514")  # the upload step cannot be queued
    _refused(engine, lambda c: _entry(c, ids, "matrix", dig=SHA), "23514")  # a consent on a step that is not an AI step
    _refused(engine, lambda c: _entry(c, ids, "matrix", pos=0), "23514")
    _refused(engine, lambda c: _entry(c, other, "series"), "23503")  # its project has no queue row
    _refused(engine, lambda c: _entry(c, {**ids, "document": other["document"]}, "series", pos=4))  # a document of another project
    with engine.begin() as connection:
        _x(connection, "UPDATE comparison_launch_entry SET state = 'running' WHERE comparison_launch_entry_id = :i", i=first)
        _x(connection, "UPDATE comparison_launch_entry SET state = 'done' WHERE comparison_launch_entry_id = :i", i=first)
        _entry(connection, ids, "series", pos=3)  # a finished entry makes room
    _refused(engine, lambda c: _x(c, "UPDATE comparison_launch_entry SET state = 'waiting' WHERE comparison_launch_entry_id = :i",
                                  i=first))  # done is final
    _refused(engine, lambda c: _x(c, "UPDATE comparison_launch_entry SET step = 'matrix' WHERE comparison_launch_entry_id = :i",
                                  i=first), "AM003")


# -- decision 7, the new column ---------------------------------------------------------------------------


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


def test_no_new_table_is_entangled_with_the_run_queue(at_this: tuple[Engine, str]) -> None:
    """A Job is a Run (ADR-0025 decision 4): nothing here may reference ``job``, ``attempt`` or ``audit_run``."""
    engine, _ = at_this
    with engine.connect() as connection:
        rows = connection.execute(text(_FOREIGN_KEYS)).all()
    assert [(s, t) for s, t in rows if str(s) in TABLES and str(t) in ("job", "attempt", "audit_run")] == []


def test_a_work_item_names_its_job_once_in_the_column_and_in_the_payload(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        ids = _world(connection)
        job = _job(connection, ids, "pair_check")
    insert = ("INSERT INTO comparison_work (comparison_work_id, project_uid, module, kind, payload, comparison_ai_job_id) "
              "VALUES (:w, :p, 'versions', 'comparison_pair_question', CAST(:pl AS jsonb), :j)")
    _refused(engine, lambda c: _x(c, insert, w=_id("cq"), p=ids["project"], pl="{}", j=job), "23514")
    _refused(engine, lambda c: _x(c, insert, w=_id("cq"), p=ids["project"], pl=json.dumps({"ai_job_id": _id("cai")}), j=job), "23514")
    work = _id("cq")
    with engine.begin() as connection:
        _x(connection, insert, w=work, p=ids["project"], pl=json.dumps({"ai_job_id": job}), j=job)
        _x(connection, insert.replace(", :j)", ", NULL)"), w=_id("cq"), p=ids["project"], pl="{}", j=None)
    _refused(engine, lambda c: _x(c, "UPDATE comparison_work SET comparison_ai_job_id = NULL WHERE comparison_work_id = :w",
                                  w=work), "AM003")


# -- the downgrade ----------------------------------------------------------------------------------------


def test_the_downgrade_is_refused_while_any_row_exists_and_gives_back_0039(
    at_previous: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_previous
    _upgrade(foundation_command, url, THIS)
    with engine.begin() as connection:
        ids = _world(connection)
        _answer(connection, ids["project"])
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0 and "0040 downgrade refused" in refused.describe()
    assert _count(engine, "comparison_ai_pair_answer") == 1, "the refusal changed a row"
    with engine.begin() as connection:  # the operator's way: guards off, the rows removed
        connection.execute(text("ALTER TABLE comparison_ai_pair_answer DISABLE TRIGGER trg_comparison_ai_pair_answer_immutable"))
        connection.execute(text("DELETE FROM comparison_ai_pair_answer"))
    done = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert done.returncode == 0, done.describe()
    assert not set(TABLES) & _tables(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
        columns = {row[0] for row in connection.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'comparison_work'"))}
        assert "comparison_ai_job_id" not in columns
    _refused(engine, lambda c: _route(c, "comparison_pair_check"), "23514")  # the single work kind is back
    _upgrade(foundation_command, url, THIS)
    assert set(TABLES) <= _tables(engine)


def test_a_route_of_a_comparison_kind_blocks_the_downgrade(at_this: tuple[Engine, str], foundation_command: Any) -> None:
    engine, url = at_this
    with engine.begin() as connection:
        _route(connection, "comparison_report")
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0 and "0040 downgrade refused" in refused.describe()
    assert _count(engine, "executor_route_event") == 1


def test_the_migration_file_is_where_the_report_says() -> None:
    assert (Path(__file__).resolve().parents[3] / "db/migrations/versions/20261029_0040_comparison_ai_reports.py").is_file()
