"""`CMP-SEAL-C0` (ADR-0025 decision 7): a project with comparison work in flight is not erased, and one
without it goes with every comparison row it owns.

``comparison_work`` and ``comparison_work_attempt`` have non-terminal states (queued, leased, running,
retry wait, paused, awaiting a person after a possible paid call), and the tool refuses an erase while
any row is in one. Built here the way the queue's own code will write the rows, and measured with the
test's own counts, as in ``test_project_erase_shapes.py``. Each guard is shown failing: with the tables
out of ``NON_TERMINAL_STATES`` a leased item no longer stops the erase.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.recovery import project_erase as tool
from auditmanager.shared.identity import new_ulid
from tests.integration.recovery.purge_stand import (  # noqa: F401  (the fixtures are used by name)
    Stand, _line, invoke, seeded, stand,
)
from tests.integration.recovery.test_project_erase import apply_flags, count, events, rows, sql

SHA = "a" * 64
COMPARISON_TABLES = (
    "comparison_upload", "comparison_upload_set", "comparison_upload_file", "comparison_upload_part",
    "comparison_version_order", "comparison_work", "comparison_work_attempt", "comparison_model_call",
)


def _id(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def _comparison_project(stand: Stand, *, work_state: str) -> dict[str, str]:
    """A project with a document of two versions and one row in each comparison table that can be
    built without bytes; the work item is in ``work_state``."""
    ids = {"p": _id("prj"), "d": _id("doc"), "v1": _id("ver"), "v2": _id("ver"), "w": _id("cq"), "a": _id("cqa"),
           "c": _id("cmd"), "c2": _id("cmd"), "u": _id("cbt"), "s": _id("cus"), "f": _id("cuf"), "o": _id("cvo"),
           "m": _id("cmc")}
    sql(stand, "INSERT INTO project (project_uid, name) VALUES (:p, 'cmp erase')", **ids)
    sql(stand, "INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'D')", **ids)
    for number, key in ((1, "v1"), (2, "v2")):
        sql(stand, "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
                   "sha256, page_count) VALUES (:v, :d, :n, 'application/pdf', 1, :sha, 1)",
            v=ids[key], d=ids["d"], n=number, sha=SHA)
    for command in ("c", "c2"):
        sql(stand, "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
                   "VALUES (:c, 'create_comparison_upload', :k, :sha)", c=ids[command], k=f"k-{command}-{new_ulid()}", sha=SHA)
    actor = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    sql(stand, "INSERT INTO comparison_upload (comparison_upload_id, project_uid, declared_files, declared_bytes, "
               "actor_user_uid, actor_label, command_id) VALUES (:u, :p, 1, 10, :act, 'A', :c)", act=actor, **ids)
    sql(stand, "INSERT INTO comparison_upload_set (comparison_upload_set_id, comparison_upload_id) VALUES (:s, :u)", **ids)
    sql(stand, "INSERT INTO comparison_upload_file (comparison_upload_file_id, comparison_upload_id, set_id, "
               "display_name, declared_size_bytes, declared_sha256, multipart_token) "
               "VALUES (:f, :u, :s, 'a.pdf', 10, :sha, 'token')", sha=SHA, **ids)
    sql(stand, "INSERT INTO comparison_upload_part (comparison_upload_file_id, part_number) VALUES (:f, 1)", **ids)
    sql(stand, "INSERT INTO comparison_version_order (comparison_version_order_id, project_uid, document_uid, "
               "revision_no, version_uids, source, actor_user_uid, actor_label, command_id) VALUES "
               "(:o, :p, :d, 1, CAST(:vs AS jsonb), 'expert', :act, 'A', :c2)",
        vs=f'["{ids["v1"]}", "{ids["v2"]}"]', act=actor, **ids)
    sql(stand, "INSERT INTO comparison_work (comparison_work_id, project_uid, module, kind) "
               "VALUES (:w, :p, 'versions', 'profile_page')", **ids)
    sql(stand, "INSERT INTO comparison_work_attempt (comparison_work_attempt_id, comparison_work_id, attempt_no, "
               "execution_token) VALUES (:a, :w, 1, :t)", t=new_ulid(), **ids)
    sql(stand, "INSERT INTO comparison_model_call (comparison_model_call_id, comparison_work_id, "
               "comparison_work_attempt_id, work_kind, provider_mode, model_identity, request_sha256, "
               "estimate_micros) VALUES (:m, :w, :a, 'comparison_pair_check', 'recorded', 'recorded', :sha, 1)",
        sha=SHA, **ids)
    for state in {"queued": (), "leased": ("leased",), "running": ("leased", "running"),
                  "retry_wait": ("leased", "running", "retry_wait"), "paused": ("paused",),
                  "spend_unknown": ("leased", "spend_unknown"),
                  "cancelled": ("cancelled",), "succeeded": ("leased", "running", "succeeded")}[work_state]:
        extra = ", terminal_at = clock_timestamp()" if state in ("cancelled", "succeeded") else ""
        sql(stand, f"UPDATE comparison_work SET state = '{state}'{extra} WHERE comparison_work_id = :w", w=ids["w"])
    # the attempt ends with the work: a live attempt of a terminal item would be a second claim
    if work_state in ("cancelled", "succeeded"):
        sql(stand, "UPDATE comparison_work_attempt SET state = 'cancelled', terminal_at = clock_timestamp() "
                   "WHERE comparison_work_attempt_id = :a", a=ids["a"])
    return ids


def _refused_for(stand: Stand, project: str) -> str:
    code, out, err = invoke(tool, stand, "--project", project)
    assert code == tool.EXIT_REFUSED, (code, out, err)
    return err


@pytest.mark.parametrize("state", ["queued", "leased", "running", "retry_wait", "paused", "spend_unknown"])
def test_comparison_work_in_flight_stops_the_erase(stand: Stand, state: str) -> None:
    ids = _comparison_project(stand, work_state=state)
    assert "work of this project is not terminal: {'comparison_work': 1}" in _refused_for(stand, ids["p"]) \
        or "'comparison_work': 1" in _refused_for(stand, ids["p"])
    assert count(stand, "project", "project_uid = :p", p=ids["p"]) == 1


def test_a_live_attempt_alone_stops_the_erase(stand: Stand) -> None:
    ids = _comparison_project(stand, work_state="cancelled")
    sql(stand, "ALTER TABLE comparison_work_attempt DISABLE TRIGGER USER")
    try:
        sql(stand, "UPDATE comparison_work_attempt SET state = 'created', terminal_at = NULL WHERE comparison_work_attempt_id = :a",
            a=ids["a"])
    finally:
        sql(stand, "ALTER TABLE comparison_work_attempt ENABLE TRIGGER USER")
    assert "'comparison_work_attempt': 1" in _refused_for(stand, ids["p"])


def test_a_terminal_project_is_erased_with_every_comparison_row(stand: Stand, tmp_path: Path) -> None:
    ids = _comparison_project(stand, work_state="succeeded")
    other = _comparison_project(stand, work_state="succeeded")
    before = {t: count(stand, t) for t in COMPARISON_TABLES}
    code, out, err = invoke(tool, stand, "--project", ids["p"])
    assert code == 0, err
    for table in COMPARISON_TABLES:
        assert f"  {table}  (1 rows)" in out, (table, out)
    sha = _line(out, "plan-sha256")
    code, out, err = invoke(tool, stand, *apply_flags(ids["p"], sha, tmp_path / "dump"))
    assert code == 0, (out, err)
    for table in COMPARISON_TABLES:
        assert count(stand, table) == before[table] - 1, table
    assert count(stand, "project", "project_uid = :p", p=ids["p"]) == 0
    assert count(stand, "comparison_work", "project_uid = :p", p=other["p"]) == 1  # the other project is untouched
    assert [e[0] for e in events(stand)][-2:] == ["erasure.requested", "erasure.completed"]


def test_the_in_flight_guard_loses_the_comparison_tables_without_them(
    stand: Stand, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation: with the two tables out of ``NON_TERMINAL_STATES`` a leased item no longer stops the erase."""
    ids = _comparison_project(stand, work_state="leased")
    assert _refused_for(stand, ids["p"])
    monkeypatch.setattr(tool, "NON_TERMINAL_STATES", {k: v for k, v in tool.NON_TERMINAL_STATES.items()
                                                       if not k.startswith("comparison_")})
    code, out, err = invoke(tool, stand, "--project", ids["p"])
    assert code == 0, err  # the mutated table lets the project through while an item is still leased
