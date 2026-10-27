"""`COMPARE-PERSISTED-SUMMARY-01` (B2): ``comparison_summary`` of ``0035_comparison_records`` against real rows.

The summary table is append-only like the history it describes, and the database holds what makes a
stored summary honest, not only the command:

* **it describes the latest approved set**: the revision must be the comparison's newest, in the
  comparison's project, with the seal that revision stored (``AM001`` otherwise), so a summary of a
  superseded set, of another project's evidence or under a seal nobody computed cannot be written;
* **the shape**: a ``ready`` row has between one and twenty statements and no rejection reason, a
  ``rejected`` row has a reason from the closed vocabulary and none, the cost is ``unmetered`` only
  for the recorded binding, and a recorded row is unmetered and says so;
* **one ready summary** per (comparison, revision, input digest, prompt version): an exact repeat is
  refused by the database as well as answered by the command;
* UPDATE and DELETE are refused (``AM003``);
* the downgrade is refused while a summary exists, and says so.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import Engine, text

from auditmanager.shared.identity import AuditEventId, ComparisonId
from tests.integration.db.test_comparison_records_migration import (  # noqa: F401  (fixtures by name)
    SEAL,
    SHA_A,
    SHA_B,
    SHA_C,
    USER,
    _alembic,
    _command,
    _count,
    _link,
    _refused,
    _version,
    at_previous,
    at_this,
)

LINK_ID = "sln_01ARZ3NDEKTSV4RRFFQ69G5FAV"
STATEMENTS = [{"text": "Размер изменён.", "hunk_ids": [f"{LINK_ID}:0"]}]


def _summary(connection: Any, ids: dict[str, str], comparison: str, revision: int, **overrides: Any) -> str:
    values: dict[str, Any] = {
        "id": str(AuditEventId.new()), "cmp": comparison, "rev": revision, "project": ids["project"],
        "seal": SEAL, "input": SHA_A, "request": SHA_B, "prompt": "comparison-summary-v1",
        "mode": "recorded", "model": "recorded", "state": "ready", "reason": None,
        "statements": json.dumps(STATEMENTS, ensure_ascii=False), "basis": "unmetered", "micros": 0,
        "user": USER, "label": "Иванов И.", "command": _command(connection),
    } | overrides
    connection.execute(
        text("INSERT INTO comparison_summary (summary_id, comparison_id, link_revision, project_uid, "
             "raw_evidence_seal_sha256, input_sha256, request_sha256, prompt_version, provider_mode, "
             "model_identity, state, rejection_reason, statements, cost_basis, cost_micros, "
             "actor_user_uid, actor_label, command_id) VALUES (:id, :cmp, :rev, :project, :seal, :input, "
             ":request, :prompt, :mode, :model, :state, :reason, CAST(:statements AS jsonb), :basis, "
             ":micros, :user, :label, :command)"),
        values,
    )
    return str(values["id"])


@pytest.fixture
def approved(at_this: tuple[Engine, str, dict[str, str]]):
    engine, url, ids = at_this
    comparison = str(ComparisonId.new())
    with engine.begin() as connection:
        _link(connection, ids, comparison, 1)
    return engine, url, ids, comparison


def test_a_summary_of_the_latest_approved_set_is_written(approved) -> None:
    engine, _, ids, comparison = approved
    with engine.begin() as connection:
        _summary(connection, ids, comparison, 1)
    assert _count(engine, "comparison_summary") == 1


@pytest.mark.parametrize(
    ("changes", "why"),
    [
        ({"seal": "e" * 64}, "a seal that revision never stored"),
        ({"rev": 2}, "a revision that does not exist"),
        ({"cmp": "cmp_01ARZ3NDEKTSV4RRFFQ69G5FAV"}, "a comparison that does not exist"),
    ],
)
def test_a_summary_must_describe_a_stored_revision_with_its_seal(approved, changes: dict[str, Any], why: str) -> None:
    engine, _, ids, comparison = approved
    _refused(engine, lambda c: _summary(c, ids, changes.get("cmp", comparison), changes.get("rev", 1),
                                        **{k: v for k, v in changes.items() if k not in ("cmp", "rev")}))
    assert _count(engine, "comparison_summary") == 0, why


def test_a_summary_of_a_superseded_set_cannot_be_written(approved) -> None:
    engine, _, ids, comparison = approved
    with engine.begin() as connection:
        _summary(connection, ids, comparison, 1)
        _link(connection, ids, comparison, 2, source=2, target=2)   # the set moved on
    _refused(engine, lambda c: _summary(c, ids, comparison, 1, input=SHA_C))
    with engine.begin() as connection:
        _summary(connection, ids, comparison, 2, input=SHA_C)       # the new set may be summarised
    assert _count(engine, "comparison_summary") == 2


def test_a_summary_of_another_projects_comparison_is_refused(approved) -> None:
    engine, _, ids, comparison = approved
    _refused(engine, lambda c: _summary(c, ids, comparison, 1, project=ids["other_project"]))


@pytest.mark.parametrize(
    "changes",
    [
        {"statements": "[]"},                                                    # ready, nothing to read
        {"statements": json.dumps(STATEMENTS * 21, ensure_ascii=False)},         # more than twenty
        {"reason": "unknown_hunk_reference"},                                    # ready with a rejection
        {"state": "rejected", "statements": "[]", "reason": None},               # rejected without a reason
        {"state": "rejected", "statements": "[]", "reason": "something_else"},
        {"state": "rejected", "reason": "unknown_hunk_reference"},               # rejected with statements
        {"state": "pending"},
        {"statements": json.dumps({"statements": []})},                          # not an array
        {"basis": "unmetered", "mode": "live", "model": "gpt"},                  # unmetered is the recorded binding's alone
        {"basis": "measured", "mode": "recorded"},                               # a recorded row is unmetered
        {"model": "gpt"},                                                        # a recorded row names no model
        {"micros": 5},                                                           # unmetered costs nothing
        {"micros": -1, "basis": "measured", "mode": "live", "model": "gpt"},
        {"mode": "proxy"},
        {"input": "z" * 64}, {"request": "a" * 63}, {"seal": "D" * 64},
        {"prompt": "V1"}, {"label": ""}, {"label": " x"},
    ],
)
def test_the_shape_of_a_summary_is_checked_by_the_database(approved, changes: dict[str, Any]) -> None:
    engine, _, ids, comparison = approved
    sqlstate = "AM001" if changes.get("seal") == "D" * 64 else "23514"
    _refused(engine, lambda c: _summary(c, ids, comparison, 1, **changes), sqlstate)
    assert _count(engine, "comparison_summary") == 0


def test_a_live_summary_may_carry_a_measured_cost_but_never_an_unmetered_one(approved) -> None:
    engine, _, ids, comparison = approved
    with engine.begin() as connection:
        _summary(connection, ids, comparison, 1, mode="live", model="provider/model-1", basis="measured",
                 micros=1234)
    _refused(engine, lambda c: _summary(c, ids, comparison, 1, input=SHA_C, mode="live", model="x",
                                        basis="unmetered", micros=0), "23514")


def test_one_ready_summary_per_input_and_a_rejected_one_may_repeat(approved) -> None:
    engine, _, ids, comparison = approved
    with engine.begin() as connection:
        _summary(connection, ids, comparison, 1)
    _refused(engine, lambda c: _summary(c, ids, comparison, 1), "23505")
    rejected = {"state": "rejected", "statements": "[]", "reason": "reply_shape_invalid"}
    with engine.begin() as connection:
        _summary(connection, ids, comparison, 1, **rejected)
        _summary(connection, ids, comparison, 1, **rejected)
        _summary(connection, ids, comparison, 1, input=SHA_C)      # another input is another summary
    assert _count(engine, "comparison_summary") == 4


@pytest.mark.parametrize("statement", [
    "UPDATE comparison_summary SET state = 'rejected'",
    "UPDATE comparison_summary SET statements = '[]'::jsonb",
    "DELETE FROM comparison_summary",
])
def test_a_stored_summary_cannot_be_updated_or_deleted(approved, statement: str) -> None:
    engine, _, ids, comparison = approved
    with engine.begin() as connection:
        _summary(connection, ids, comparison, 1)
    _refused(engine, lambda c: c.execute(text(statement)), "AM003")
    assert _count(engine, "comparison_summary") == 1


def test_the_downgrade_is_refused_while_a_summary_exists(approved, foundation_command: Any) -> None:
    engine, url, ids, comparison = approved
    with engine.begin() as connection:
        _summary(connection, ids, comparison, 1)
        connection.execute(text("SELECT 1"))
    refused = foundation_command(_alembic("downgrade", "0034_pass_scope_all_sections"), url)
    assert refused.returncode != 0, refused.describe()
    assert "0035 downgrade refused: 1 sheet link event(s) and 1 summary row(s)" in refused.stderr, refused.stderr
    assert _version(engine) == "0035_comparison_records" and _count(engine, "comparison_summary") == 1
