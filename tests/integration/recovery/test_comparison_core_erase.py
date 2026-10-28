"""`CMP-SEAL-C1` (ADR-0025 decision 7): a project with a comparison series in flight is not erased, and a
project whose series are finished goes with every comparison row it owns.

A series, its transitions and its sheet pairs have non-terminal states (queued, running, paused, computing),
and the tool refuses an erase while any row is in one, the way it does for the comparison queue. Built here the
way the lanes will write the rows, and measured with the test's own counts. Each guard is shown failing: with the
three tables out of ``NON_TERMINAL_STATES`` a running series no longer stops the erase.
"""

from __future__ import annotations

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
CORE_TABLES = (
    "comparison_matrix", "comparison_matrix_edit", "comparison_ai_link", "comparison_series",
    "comparison_transition", "comparison_sheet_pair_result", "comparison_sheet_pair",
)


def _id(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def _core_project(stand: Stand, *, series_state: str, pair_state: str = "done") -> dict[str, str]:
    """A project with a document of two versions and one row in each table of the core."""
    ids = {k: _id(p) for k, p in (("p", "prj"), ("d", "doc"), ("v1", "ver"), ("v2", "ver"), ("m", "cmx"),
                                  ("e", "cme"), ("k", "cak"), ("s", "cser"), ("t", "ctn"), ("r", "csp"),
                                  ("x", "ctp"), ("a", "cpr"), ("b", "cpr"), ("c1", "cmd"), ("c2", "cmd"))}
    sql(stand, "INSERT INTO project (project_uid, name) VALUES (:p, 'core erase')", **ids)
    sql(stand, "INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'D')", **ids)
    for number, key in ((1, "v1"), (2, "v2")):
        sql(stand, "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
                   "sha256, page_count) VALUES (:v, :d, :n, 'application/pdf', 1, :sha, 2)",
            v=ids[key], d=ids["d"], n=number, sha=SHA)
    for command in ("c1", "c2"):
        sql(stand, "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
                   "VALUES (:c, 'apply_comparison_matrix_edits', :k, :sha)", c=ids[command],
            k=f"k-{command}-{new_ulid()}", sha=SHA)
    for profile, version, key in (("a", "v1", "1" * 64), ("b", "v2", "2" * 64)):
        sql(stand, "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, page_number, "
                   "content_key, algo_version, status) VALUES (:i, :v, 1, :k, 'p1', 'ready')",
            i=ids[profile], v=ids[version], k=key)
    sql(stand, "INSERT INTO comparison_matrix (comparison_matrix_id, project_uid, document_uid, build_no, "
               "profile_signature, rules_version, algo_version, rows) VALUES (:m, :p, :d, 1, :sha, 'v1.2', 'm1', '[]')",
        sha=SHA, **ids)
    sql(stand, "INSERT INTO comparison_matrix_edit (comparison_matrix_edit_id, project_uid, document_uid, edit_no, "
               "kind, page_version_uid, page_number, other_version_uid, other_page_number, actor_user_uid, "
               "actor_label, command_id) VALUES (:e, :p, :d, 1, 'link', :v1, 1, :v2, 1, :act, 'A', :c1)",
        act=ACTOR, **ids)
    sql(stand, "INSERT INTO comparison_ai_link (comparison_ai_link_id, document_uid, comparison_matrix_id, "
               "page_version_uid, page_number, other_version_uid, other_page_number, answered_state) "
               "VALUES (:k, :d, :m, :v1, 2, :v2, 2, 'unmatched')", **ids)
    sql(stand, "INSERT INTO comparison_series (comparison_series_id, project_uid, document_uid, comparison_matrix_id, "
               "matrix_edit_no, input_sha256, actor_user_uid, actor_label, command_id) "
               "VALUES (:s, :p, :d, :m, 1, :sha, :act, 'A', :c2)", sha=SHA, act=ACTOR, **ids)
    sql(stand, "INSERT INTO comparison_transition (comparison_transition_id, comparison_series_id, transition_no, "
               "source_version_uid, target_version_uid) VALUES (:t, :s, 1, :v1, :v2)", **ids)
    sql(stand, "INSERT INTO comparison_sheet_pair_result (comparison_sheet_pair_result_id, project_uid, content_key, "
               "algo_version, status, page_a_profile_id, page_b_profile_id) VALUES (:r, :p, :sha, 'vc1', 'different', "
               ":a, :b)", sha=SHA, **ids)
    sql(stand, "INSERT INTO comparison_sheet_pair (comparison_sheet_pair_id, comparison_transition_id, pair_no, "
               "page_a_profile_id, page_b_profile_id) VALUES (:x, :t, 1, :a, :b)", **ids)
    if pair_state == "done":
        for step in ("computing",):
            sql(stand, f"UPDATE comparison_sheet_pair SET state = '{step}' WHERE comparison_sheet_pair_id = :x", x=ids["x"])
        sql(stand, "UPDATE comparison_sheet_pair SET state = 'done', status = 'different', result_id = :r "
                   "WHERE comparison_sheet_pair_id = :x", r=ids["r"], x=ids["x"])
    elif pair_state == "computing":
        sql(stand, "UPDATE comparison_sheet_pair SET state = 'computing' WHERE comparison_sheet_pair_id = :x", x=ids["x"])
    path = {"queued": (), "running": ("running",), "paused": ("running", "paused"),
            "completed": ("running", "completed")}[series_state]
    for state in path:
        sql(stand, f"UPDATE comparison_series SET state = '{state}' WHERE comparison_series_id = :s", s=ids["s"])
    transition = "completed" if series_state == "completed" else "queued"
    if transition == "completed":
        sql(stand, "UPDATE comparison_transition SET state = 'running' WHERE comparison_transition_id = :t", t=ids["t"])
        sql(stand, "UPDATE comparison_transition SET state = 'completed', summary = '{}'::jsonb, verdict = '[]'::jsonb "
                   "WHERE comparison_transition_id = :t", t=ids["t"])
    return ids


def _refused_for(stand: Stand, project: str) -> str:
    code, out, err = invoke(tool, stand, "--project", project)
    assert code == tool.EXIT_REFUSED, (code, out, err)
    return err


@pytest.mark.parametrize("state", ["queued", "running", "paused"])
def test_a_series_in_flight_stops_the_erase(stand: Stand, state: str) -> None:
    ids = _core_project(stand, series_state=state)
    assert "'comparison_series': 1" in _refused_for(stand, ids["p"])
    assert count(stand, "project", "project_uid = :p", p=ids["p"]) == 1


def test_a_transition_or_a_pair_in_flight_alone_stops_the_erase(stand: Stand) -> None:
    ids = _core_project(stand, series_state="completed", pair_state="computing")
    sql(stand, "ALTER TABLE comparison_transition DISABLE TRIGGER USER")
    try:
        sql(stand, "UPDATE comparison_transition SET state = 'queued' WHERE comparison_transition_id = :t", t=ids["t"])
    finally:
        sql(stand, "ALTER TABLE comparison_transition ENABLE TRIGGER USER")
    refused = _refused_for(stand, ids["p"])
    assert "'comparison_transition': 1" in refused and "'comparison_sheet_pair': 1" in refused


def test_a_finished_project_is_erased_with_every_row_of_the_core(stand: Stand, tmp_path: Path) -> None:
    ids = _core_project(stand, series_state="completed")
    other = _core_project(stand, series_state="completed")
    before = {t: count(stand, t) for t in CORE_TABLES}
    code, out, err = invoke(tool, stand, "--project", ids["p"])
    assert code == 0, err
    for table in CORE_TABLES:
        assert f"  {table}  (1 rows)" in out, (table, out)
    sha = _line(out, "plan-sha256")
    code, out, err = invoke(tool, stand, *apply_flags(ids["p"], sha, tmp_path / "dump"))
    assert code == 0, (out, err)
    for table in CORE_TABLES:
        assert count(stand, table) == before[table] - 1, table
    assert count(stand, "project", "project_uid = :p", p=ids["p"]) == 0
    assert count(stand, "comparison_series", "project_uid = :p", p=other["p"]) == 1
    assert [e[0] for e in events(stand)][-2:] == ["erasure.requested", "erasure.completed"]


def test_the_in_flight_guard_loses_the_core_tables_without_them(
    stand: Stand, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation: with the three tables out of ``NON_TERMINAL_STATES`` a running series no longer stops the erase."""
    ids = _core_project(stand, series_state="running", pair_state="computing")
    assert _refused_for(stand, ids["p"])
    kept = {k: v for k, v in tool.NON_TERMINAL_STATES.items()
            if k not in ("comparison_series", "comparison_transition", "comparison_sheet_pair")}
    monkeypatch.setattr(tool, "NON_TERMINAL_STATES", kept)
    code, out, err = invoke(tool, stand, "--project", ids["p"])
    assert code == 0, err
