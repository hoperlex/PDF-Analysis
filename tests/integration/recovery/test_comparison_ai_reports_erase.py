"""`CMP-SEAL-C2` (ADR-0025 decision 7): a project with an AI job, a question, a sheet item, a specification comparison, a
report or a launch-queue entry in flight is not erased, and a project whose AI work is finished goes with every row it
owns.

The tables of `0040_comparison_ai_reports` have non-terminal states, and the tool refuses an erase while any row is in one,
the way it does for the comparison queue and the series. Built here the way the lanes will write the rows, and measured with
the test's own counts. Each guard is shown failing: with the tables out of ``NON_TERMINAL_STATES`` an AI job in flight no
longer stops the erase.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.recovery import project_erase as tool
from auditmanager.shared.identity import new_ulid
from tests.integration.recovery.purge_stand import (  # noqa: F401  (the fixtures are used by name)
    Stand, _line, invoke, seeded, stand,
)
from tests.integration.recovery.test_project_erase import apply_flags, count, events, sql

SHA = "a" * 64
ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
AI_TABLES = (
    "comparison_ai_job", "comparison_ai_pair_answer", "comparison_ai_pair_question",
    "comparison_sheet_description", "comparison_ai_sheet_item", "comparison_spec_extraction",
    "comparison_spec_comparison", "comparison_report", "comparison_report_part", "comparison_launch_queue",
    "comparison_launch_entry",
)
#: ``table -> (UPDATE that puts its one row back in a non-terminal state, the key of the row)``.
IN_FLIGHT: dict[str, tuple[str, str]] = {
    "comparison_ai_job": ("state = 'paused', pause_reason = 'user', finished_at = NULL", "comparison_ai_job_id = :job"),
    "comparison_ai_pair_question": ("state = 'queued', decision = NULL, answer_id = NULL, comparison_ai_link_id = NULL",
                                    "comparison_ai_pair_question_id = :question"),
    "comparison_ai_sheet_item": ("state = 'running', comparison_sheet_description_id = NULL",
                                 "comparison_ai_sheet_item_id = :item"),
    "comparison_spec_comparison": ("state = 'running'", "comparison_spec_comparison_id = :spec"),
    "comparison_report": ("state = 'paused', finished_at = NULL", "comparison_report_id = :report"),
    "comparison_launch_entry": ("state = 'waiting'", "comparison_launch_entry_id = :entry"),
}


#: The receipt each method's start leaves: product command types, as `product_purge.PRODUCT_COMMAND_TYPES` names them.
START_COMMANDS = {
    "pair_check": "start_comparison_ai_pair_check", "sheet_changes": "start_comparison_ai_sheet_changes",
    "spec": "start_comparison_specification", "report": "start_comparison_report",
}


#: Rows of a table that one `_ai_project` writes, where it is not one: a job of each of the four methods, an extraction of each
#: of the two versions.
PER_PROJECT = {"comparison_ai_job": 4, "comparison_spec_extraction": 2}


def _id(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def _command(stand: Stand, kind: str) -> str:
    command = _id("cmd")
    sql(stand, "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
               "VALUES (:c, :t, :k, :sha)", c=command, t=kind, k=f"k-{new_ulid()}", sha=SHA)
    return command


def _job(stand: Stand, ids: dict[str, str], method: str, **scope: str) -> str:
    job = _id("cai")
    sql(stand, "INSERT INTO comparison_ai_job (comparison_ai_job_id, project_uid, document_uid, method, comparison_matrix_id, "
               "comparison_series_id, comparison_transition_id, connection_revision_id, pinned_model, provider_mode, estimate, "
               "estimate_digest, estimate_micros, ceiling_micros, consented_by_user_uid, command_id) "
               "VALUES (:j, :p, :d, :m, :cmx, :cser, :ctn, :rev, 'claude-opus-5', 'live', CAST(:e AS jsonb), :sha, 1, 10, :a, :c)",
        j=job, p=ids["p"], d=ids["d"], m=method, cmx=scope.get("matrix"), cser=scope.get("series"), ctn=scope.get("transition"),
        rev=ids["rev"], e=json.dumps({"estimate_digest": SHA}), sha=SHA, a=ACTOR, c=_command(stand, START_COMMANDS[method]))
    for state in ("running", "completed"):
        extra = ", finished_at = now()" if state == "completed" else ""
        sql(stand, f"UPDATE comparison_ai_job SET state = '{state}'{extra} WHERE comparison_ai_job_id = :j", j=job)
    return job


def _ai_project(stand: Stand) -> dict[str, str]:
    """A project whose AI work is finished: one row in each of the tables of ``0040`` but the report file."""
    ids = {k: _id(p) for k, p in (("p", "prj"), ("d", "doc"), ("v1", "ver"), ("v2", "ver"), ("m", "cmx"), ("s", "cser"),
                                  ("t", "ctn"), ("r", "csp"), ("x", "ctp"), ("pa", "cpr"), ("pb", "cpr"), ("conn", "exc"),
                                  ("rev", "excr"))}
    sql(stand, "INSERT INTO project (project_uid, name) VALUES (:p, 'ai erase')", **ids)
    sql(stand, "INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'D')", **ids)
    for number, key in ((1, "v1"), (2, "v2")):
        sql(stand, "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
                   "sha256, page_count) VALUES (:v, :d, :n, 'application/pdf', 1, :sha, 3)", v=ids[key], d=ids["d"], n=number, sha=SHA)
    for profile, version, key in (("pa", "v1", "1" * 64), ("pb", "v2", "2" * 64)):
        sql(stand, "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, page_number, content_key, "
                   "algo_version, status) VALUES (:i, :v, 1, :k, 'p1', 'ready')", i=ids[profile], v=ids[version], k=key)
    sql(stand, "INSERT INTO comparison_matrix (comparison_matrix_id, project_uid, document_uid, build_no, profile_signature, "
               "rules_version, algo_version, rows) VALUES (:m, :p, :d, 1, :sha, 'v1.2', 'm1', '[]')", sha=SHA, **ids)
    sql(stand, "INSERT INTO comparison_series (comparison_series_id, project_uid, document_uid, comparison_matrix_id, "
               "matrix_edit_no, input_sha256, actor_user_uid, actor_label, command_id) VALUES (:s, :p, :d, :m, 0, :sha, :a, 'A', :c)",
        sha=SHA, a=ACTOR, c=_command(stand, "start_comparison_series"), **ids)
    sql(stand, "INSERT INTO comparison_transition (comparison_transition_id, comparison_series_id, transition_no, source_version_uid, "
               "target_version_uid) VALUES (:t, :s, 1, :v1, :v2)", **ids)
    sql(stand, "INSERT INTO comparison_sheet_pair_result (comparison_sheet_pair_result_id, project_uid, content_key, algo_version, "
               "status, page_a_profile_id, page_b_profile_id) VALUES (:r, :p, :sha, 'vc1', 'different', :pa, :pb)", sha=SHA, **ids)
    sql(stand, "INSERT INTO comparison_sheet_pair (comparison_sheet_pair_id, comparison_transition_id, pair_no, page_a_profile_id, "
               "page_b_profile_id) VALUES (:x, :t, 1, :pa, :pb)", **ids)
    # the comparison itself is finished: a done pair, a completed transition and series (the erase refuses a live one)
    sql(stand, "UPDATE comparison_sheet_pair SET state = 'computing' WHERE comparison_sheet_pair_id = :x", **ids)
    sql(stand, "UPDATE comparison_sheet_pair SET state = 'done', status = 'different', result_id = :r "
               "WHERE comparison_sheet_pair_id = :x", **ids)
    sql(stand, "UPDATE comparison_transition SET state = 'running' WHERE comparison_transition_id = :t", **ids)
    sql(stand, "UPDATE comparison_transition SET state = 'completed', summary = '{}'::jsonb, verdict = '[]'::jsonb "
               "WHERE comparison_transition_id = :t", **ids)
    sql(stand, "UPDATE comparison_series SET state = 'running' WHERE comparison_series_id = :s", **ids)
    sql(stand, "UPDATE comparison_series SET state = 'completed' WHERE comparison_series_id = :s", **ids)
    sql(stand, "INSERT INTO executor_connection (connection_id, kind, display_name, created_by) VALUES (:conn, 'http_api', 'e', :a)",
        a=ACTOR, **ids)
    sql(stand, "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, created_by, pin_id, gateway_model, "
               "billing, allow_client_documents, timeout_seconds, api_flavour, base_url, transport) VALUES (:rev, :conn, 1, :a, "
               "'claude-opus-5', 'anthropic/claude-opus-5', 'metered', false, 60, 'openai_chat', 'https://proxy.test', 'direct')",
        a=ACTOR, **ids)
    # the pair check: one answer, one answered question
    ids["answer"], ids["question"] = _id("cpa"), _id("cpq")
    pair_job = _job(stand, ids, "pair_check", matrix=ids["m"])
    sql(stand, "INSERT INTO comparison_ai_pair_answer (comparison_ai_pair_answer_id, project_uid, content_key, question_kind, "
               "prompt_version, model_identity, confidence, answer) VALUES (:i, :p, :sha, 'no_pair', 'p1', 'm', 'high', '{}'::jsonb)",
        i=ids["answer"], p=ids["p"], sha=SHA)
    sql(stand, "INSERT INTO comparison_ai_pair_question (comparison_ai_pair_question_id, comparison_ai_job_id, project_uid, "
               "document_uid, comparison_matrix_id, kind, page_version_uid, page_number, version_uid) "
               "VALUES (:q, :j, :p, :d, :m, 'no_pair', :v1, 1, :v2)", q=ids["question"], j=pair_job, **ids)
    sql(stand, "UPDATE comparison_ai_pair_question SET state = 'answered', answer_id = :a, decision = 'none' "
               "WHERE comparison_ai_pair_question_id = :q", a=ids["answer"], q=ids["question"])
    # the sheet descriptions: one description, one done item
    ids["description"], ids["item"] = _id("csd"), _id("csi")
    sheet_job = _job(stand, ids, "sheet_changes", series=ids["s"])
    ids["job"] = sheet_job
    sql(stand, "INSERT INTO comparison_sheet_description (comparison_sheet_description_id, project_uid, content_key, result_id, "
               "state, prompt_version, model_identity, description) VALUES (:i, :p, :sha, :r, 'done', 'p1', 'm', '{}'::jsonb)",
        i=ids["description"], p=ids["p"], sha=SHA, r=ids["r"])
    sql(stand, "INSERT INTO comparison_ai_sheet_item (comparison_ai_sheet_item_id, comparison_ai_job_id, project_uid, "
               "comparison_sheet_pair_id) VALUES (:i, :j, :p, :x)", i=ids["item"], j=sheet_job, p=ids["p"], x=ids["x"])
    for state in ("running",):
        sql(stand, f"UPDATE comparison_ai_sheet_item SET state = '{state}' WHERE comparison_ai_sheet_item_id = :i", i=ids["item"])
    sql(stand, "UPDATE comparison_ai_sheet_item SET state = 'done', comparison_sheet_description_id = :d "
               "WHERE comparison_ai_sheet_item_id = :i", d=ids["description"], i=ids["item"])
    # the specifications: two extractions and a cancelled whole comparison
    ids["spec"], ids["ea"], ids["eb"] = _id("cscp"), _id("cse"), _id("cse")
    spec_job = _job(stand, ids, "spec", transition=ids["t"])
    for extraction, version, key in (("ea", "v1", "1" * 64), ("eb", "v2", "2" * 64)):
        sql(stand, "INSERT INTO comparison_spec_extraction (comparison_spec_extraction_id, project_uid, version_uid, content_key, "
                   "state, prompt_version, model_identity, source_sha256, positions, coverage) VALUES (:i, :p, :v, :k, 'complete', "
                   "'p1', 'm', :sha, '[]'::jsonb, '{}'::jsonb)", i=ids[extraction], p=ids["p"], v=ids[version], k=key, sha=SHA)
    sql(stand, "INSERT INTO comparison_spec_comparison (comparison_spec_comparison_id, project_uid, document_uid, "
               "comparison_transition_id, source, comparison_ai_job_id, extraction_a_id, extraction_b_id) "
               "VALUES (:spec, :p, :d, :t, 'whole', :j, :ea, :eb)", j=spec_job, **ids)
    sql(stand, "UPDATE comparison_spec_comparison SET state = 'cancelled' WHERE comparison_spec_comparison_id = :spec", **ids)
    # the report: a finished one with a part
    ids["report"] = _id("crt")
    report_job = _job(stand, ids, "report", series=ids["s"])
    sql(stand, "INSERT INTO comparison_report (comparison_report_id, project_uid, document_uid, comparison_series_id, kind, source, "
               "estimate, estimate_digest, source_sha256, actor_user_uid, actor_label, command_id) VALUES (:report, :p, :d, :s, "
               "'client', 'series_summary', CAST(:e AS jsonb), :sha, :sha, :a, 'A', :c)",
        e=json.dumps({"estimate_digest": SHA}), sha=SHA, a=ACTOR, c=_command(stand, "create_comparison_report"), **ids)
    sql(stand, "UPDATE comparison_report SET state = 'queued', comparison_ai_job_id = :j WHERE comparison_report_id = :report",
        j=report_job, **ids)
    for state in ("running", "completed"):
        extra = ", finished_at = now()" if state == "completed" else ""
        sql(stand, f"UPDATE comparison_report SET state = '{state}'{extra} WHERE comparison_report_id = :report", **ids)
    sql(stand, "INSERT INTO comparison_report_part (comparison_report_part_id, comparison_report_id, comparison_transition_id) "
               "VALUES (:i, :report, :t)", i=_id("crpt"), **ids)
    # the launch queue: one skipped entry
    ids["entry"] = _id("cle")
    sql(stand, "INSERT INTO comparison_launch_queue (project_uid) VALUES (:p)", **ids)
    sql(stand, "INSERT INTO comparison_launch_entry (comparison_launch_entry_id, project_uid, document_uid, step, position, "
               "actor_user_uid, actor_label, command_id) VALUES (:entry, :p, :d, 'series', 1, :a, 'A', :c)",
        a=ACTOR, c=_command(stand, "enqueue_comparison_launch"), **ids)
    sql(stand, "UPDATE comparison_launch_entry SET state = 'skipped' WHERE comparison_launch_entry_id = :entry", **ids)
    return ids


def _refused_for(stand: Stand, project: str) -> str:
    code, out, err = invoke(tool, stand, "--project", project)
    assert code == tool.EXIT_REFUSED, (code, out, err)
    return err


def _put_in_flight(stand: Stand, ids: dict[str, str], table: str) -> None:
    change, key = IN_FLIGHT[table]
    sql(stand, f"ALTER TABLE {table} DISABLE TRIGGER USER")
    try:
        sql(stand, f"UPDATE {table} SET {change} WHERE {key}", **ids)
    finally:
        sql(stand, f"ALTER TABLE {table} ENABLE TRIGGER USER")


@pytest.mark.parametrize("table", sorted(IN_FLIGHT))
def test_a_row_in_flight_stops_the_erase(stand: Stand, table: str) -> None:
    ids = _ai_project(stand)
    _put_in_flight(stand, ids, table)
    assert f"'{table}': 1" in _refused_for(stand, ids["p"]), table
    assert count(stand, "project", "project_uid = :p", p=ids["p"]) == 1


def test_a_finished_project_is_erased_with_every_row_of_the_ai_tables(stand: Stand, tmp_path: Path) -> None:
    ids = _ai_project(stand)
    other = _ai_project(stand)
    before = {t: count(stand, t) for t in AI_TABLES}
    code, out, err = invoke(tool, stand, "--project", ids["p"])
    assert code == 0, err
    for table in AI_TABLES:
        expected = PER_PROJECT.get(table, 1)
        assert f"  {table}  ({expected} rows)" in out, (table, out)
    sha = _line(out, "plan-sha256")
    code, out, err = invoke(tool, stand, *apply_flags(ids["p"], sha, tmp_path / "dump"))
    assert code == 0, (out, err)
    for table in AI_TABLES:
        removed = PER_PROJECT.get(table, 1)
        assert count(stand, table) == before[table] - removed, table
    assert count(stand, "project", "project_uid = :p", p=ids["p"]) == 0
    assert count(stand, "comparison_ai_job", "project_uid = :p", p=other["p"]) == PER_PROJECT["comparison_ai_job"]
    assert [e[0] for e in events(stand)][-2:] == ["erasure.requested", "erasure.completed"]


def test_the_in_flight_guard_loses_the_ai_tables_without_them(stand: Stand, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: with the tables out of ``NON_TERMINAL_STATES`` a paused AI job no longer stops the erase."""
    ids = _ai_project(stand)
    _put_in_flight(stand, ids, "comparison_ai_job")
    assert _refused_for(stand, ids["p"])
    trimmed = {k: v for k, v in tool.NON_TERMINAL_STATES.items() if k not in IN_FLIGHT}
    monkeypatch.setattr(tool, "NON_TERMINAL_STATES", trimmed)
    code, out, err = invoke(tool, stand, "--project", ids["p"])
    assert code == 0, (out, err)  # the erase plan is made: nothing stops it any more
