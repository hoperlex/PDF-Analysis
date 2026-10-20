"""`W60-OPT-PROPOSALS-01` phase A: expert decisions on proposals, and the CSV export.

Decisions are appended, never changed: the latest is current, the history stays, the counts
by decision are the proposals' own. Only an expert decides (an account holding only
``admin`` is refused); a key replays its decision. The export is computed from the stored
rows, formula-escaped and separate from the findings export.
"""

from __future__ import annotations

import csv
import io
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.optimisation.proposals.public import (
    PROPOSAL_CSV_COLUMNS,
    PROPOSAL_CSV_CONTENT_TYPE,
    decide_optimisation_proposal,
    export_optimisation_proposals_csv,
    get_optimisation_pass,
    list_optimisation_proposals,
    list_proposal_decisions,
    start_optimisation_pass,
)
from auditmanager.shared.db.session import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

from .conftest import HOSTILE_VENDOR, World, published_reader


def _refused(code: ErrorCode, call: Any, *args: Any, **kwargs: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    assert caught.value.code is code, (caught.value.code, dict(caught.value.detail_fields))
    return caught.value


@pytest.fixture
def started(unit, cast, ready: World) -> dict[str, Any]:
    record = unit(
        start_optimisation_pass,
        project_uid=ready.project,
        document_uid=ready.document,
        idempotency_key="pass-1",
        actor_uid=cast.expert,
        reader=published_reader(ready),
    ).optimisation_pass
    page = unit(
        list_optimisation_proposals,
        optimisation_pass_id=record.optimisation_pass_id,
        actor_roles=frozenset({"expert"}),
    )
    return {"pass": record, "proposals": [item.optimisation_proposal_id for item in page.items]}


def _decide(unit, cast, proposal: str, verdict: str, key: str, comment: str | None = None, **extra):
    arguments: dict[str, Any] = {
        "proposal_id": proposal,
        "verdict": verdict,
        "comment": comment,
        "idempotency_key": key,
        "actor_uid": cast.expert,
    }
    arguments.update(extra)
    return unit(decide_optimisation_proposal, **arguments)


def _decision_rows(factory: sessionmaker[Session]) -> int:
    with session_scope(factory) as session:
        return int(session.execute(text("SELECT count(*) FROM optimisation_proposal_decision")).scalar_one())


def test_decisions_append_and_the_latest_is_current(unit, factory, cast, started) -> None:
    door, window, anchor, tape = started["proposals"]
    accepted = _decide(unit, cast, door, "accept", "d-1")
    assert (accepted.replayed, accepted.decision.verdict, accepted.decision.seq) == (False, "accept", 1)
    assert accepted.proposal.current_verdict == "accept"
    assert accepted.decision.actor_user_uid == cast.expert and accepted.decision.comment is None
    revised = _decide(unit, cast, door, "revise", "d-2", "  уточнить   марку\n двери ",
                      actor_uid=cast.other_expert)
    assert (revised.decision.seq, revised.decision.comment) == (2, "уточнить марку двери")
    assert revised.proposal.current_decision == revised.decision
    _decide(unit, cast, window, "reject", "d-3", "аналог хуже по теплотехнике")
    _decide(unit, cast, anchor, "accept", "d-4", actor_uid=cast.admin_expert)

    history = unit(list_proposal_decisions, optimisation_proposal_id=door, actor_roles=frozenset({"admin"}))
    assert [(entry.seq, entry.verdict) for entry in history] == [(1, "accept"), (2, "revise")]
    record = unit(get_optimisation_pass, optimisation_pass_id=started["pass"].optimisation_pass_id,
                  actor_roles=frozenset({"admin"}))
    assert dict(record.decision_counts) == {"pending": 1, "accept": 1, "reject": 1, "revise": 1}

    for decision, expected in (("pending", [tape]), ("accept", [anchor]), ("revise", [door]),
                               ("reject", [window])):
        page = unit(list_optimisation_proposals, optimisation_pass_id=record.optimisation_pass_id,
                    actor_roles=frozenset({"expert"}), decision=decision)
        assert [item.optimisation_proposal_id for item in page.items] == expected
        assert page.total == 1 and page.optimisation_pass.decision_counts == record.decision_counts


def test_a_key_replays_its_decision_and_refuses_another_payload(unit, factory, cast, started) -> None:
    door = started["proposals"][0]
    first = _decide(unit, cast, door, "reject", "d-1", "дороже монтаж")
    replay = _decide(unit, cast, door, "reject", "d-1", "дороже  монтаж")  # same once normalised
    assert replay.replayed and replay.decision == first.decision
    assert _decision_rows(factory) == 1
    for changed in ({"verdict": "accept", "comment": None}, {"comment": "другое"},
                    {"actor_uid": cast.other_expert}):
        arguments = {"verdict": "reject", "comment": "дороже монтаж", **changed}
        reused = _refused(ErrorCode.IDEMPOTENCY_KEY_REUSE, _decide, unit, cast, door,
                          key="d-1", **arguments)
        assert reused.detail_fields["command_type"] == "decide_optimisation_proposal"
    # A new key is a new event, even with the same verdict: the history is the record.
    _decide(unit, cast, door, "reject", "d-2", "дороже монтаж")
    assert _decision_rows(factory) == 2


def test_only_an_expert_decides_and_refusals_write_nothing(unit, factory, cast, started) -> None:
    door = started["proposals"][0]
    with session_scope(factory) as session:
        commands = int(session.execute(text("SELECT count(*) FROM command_record")).scalar_one())
    for actor in (cast.admin, cast.nobody):
        denied = _refused(ErrorCode.PERMISSION_DENIED, _decide, unit, cast, door, "accept", "d-x",
                          actor_uid=actor)
        assert denied.detail_fields["required_capability"] == "role:expert"
        assert denied.detail_fields["aggregate_type"] == "OptimisationProposal"
    required = _refused(ErrorCode.VALIDATION_FAILED, _decide, unit, cast, door, "revise", "d-x", "  ")
    assert (required.detail_fields["field"], required.detail_fields["constraint"]) == ("comment", "required")
    for verdict in ("pending", "accepted", ""):
        refused = _refused(ErrorCode.VALIDATION_FAILED, _decide, unit, cast, door, verdict, "d-x")
        assert refused.detail_fields["field"] == "verdict"
    too_long = _refused(ErrorCode.VALIDATION_FAILED, _decide, unit, cast, door, "accept", "d-x", "я" * 2001)
    assert too_long.detail_fields["constraint"] == "max_length"
    malformed = _refused(ErrorCode.VALIDATION_FAILED, _decide, unit, cast, "opp_01M2545JSD15ETSNNV904XA001",
                         "accept", "d-x")
    assert malformed.detail_fields["field"] == "optimisation_proposal_id"
    _refused(ErrorCode.NOT_FOUND, _decide, unit, cast, "opr_01M2545JSD15ETSNNV904XA001", "accept", "d-x")
    _refused(ErrorCode.VALIDATION_FAILED, _decide, unit, cast, door, "accept", "")
    assert _decision_rows(factory) == 0
    with session_scope(factory) as session:
        assert int(session.execute(text("SELECT count(*) FROM command_record")).scalar_one()) == commands


@pytest.mark.parametrize(
    ("table", "statement"),
    [
        ("optimisation_proposal_decision", "UPDATE optimisation_proposal_decision SET verdict = 'reject'"),
        ("optimisation_proposal_decision", "DELETE FROM optimisation_proposal_decision"),
        ("optimisation_proposal", "UPDATE optimisation_proposal SET saving = NULL, quantity = NULL"),
        ("optimisation_proposal", "DELETE FROM optimisation_proposal"),
        ("optimisation_pass", "UPDATE optimisation_pass SET proposal_count = proposal_count"),
        ("optimisation_pass", "DELETE FROM optimisation_pass"),
    ],
)
def test_stored_rows_are_never_updated_or_deleted(
    unit, factory, cast, started, table: str, statement: str
) -> None:
    _decide(unit, cast, started["proposals"][0], "accept", "d-1")
    with session_scope(factory) as session:
        assert int(session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()) >= 1
    with pytest.raises(DBAPIError) as caught:
        with session_scope(factory) as session:
            session.execute(text(statement))
    assert getattr(caught.value.orig, "sqlstate", "") == "AM003", statement


def test_reading_decisions_needs_a_role_and_an_existing_proposal(unit, cast, started) -> None:
    _refused(ErrorCode.PERMISSION_DENIED, unit, list_proposal_decisions,
             optimisation_proposal_id=started["proposals"][0], actor_roles=frozenset())
    _refused(ErrorCode.NOT_FOUND, unit, list_proposal_decisions,
             optimisation_proposal_id="opr_01M2545JSD15ETSNNV904XA001", actor_roles=frozenset({"admin"}))
    assert unit(list_proposal_decisions, optimisation_proposal_id=started["proposals"][1],
                actor_roles=frozenset({"expert"})) == ()


# -- the CSV export ------------------------------------------------------------------------


def _rows(content: bytes) -> list[dict[str, str]]:
    assert content.startswith(b"\xef\xbb\xbf")
    return list(csv.DictReader(io.StringIO(content[3:].decode("utf-8"), newline="")))


def test_the_export_is_escaped_complete_and_separate_from_findings(unit, factory, cast, started) -> None:
    door, _window, anchor, tape = started["proposals"]
    _decide(unit, cast, door, "revise", "d-1", "=уточнить у поставщика")
    exported = unit(export_optimisation_proposals_csv,
                    optimisation_pass_id=started["pass"].optimisation_pass_id,
                    actor_roles=frozenset({"admin"}))
    assert exported.content_type == PROPOSAL_CSV_CONTENT_TYPE == "text/csv; charset=utf-8"
    rows = _rows(exported.content)
    assert [row["optimisation_proposal_id"] for row in rows] == started["proposals"]
    assert tuple(rows[0]) == PROPOSAL_CSV_COLUMNS
    by_id = {row["optimisation_proposal_id"]: row for row in rows}
    assert by_id[anchor]["proposed_vendor"] == "'" + HOSTILE_VENDOR
    assert by_id[anchor]["saving"] == "650" and by_id[anchor]["currency"] == "EUR"
    assert (by_id[door]["current_decision"], by_id[door]["decision_comment"]) == (
        "revise", "'=уточнить у поставщика",
    )
    assert by_id[door]["saving"] == "16000" and by_id[door]["current_unit_price"] == "25000"
    assert (by_id[tape]["saving"], by_id[tape]["quantity"], by_id[tape]["quantity_text"]) == ("", "", "'-")
    assert by_id[tape]["current_decision"] == "pending"
    assert all(row["optimisation_pass_id"] == started["pass"].optimisation_pass_id for row in rows)
    # Recomputed, not remembered: the same bytes again, with no row written.
    again = unit(export_optimisation_proposals_csv,
                 optimisation_pass_id=started["pass"].optimisation_pass_id,
                 actor_roles=frozenset({"expert"}))
    assert again.content == exported.content
    _refused(ErrorCode.PERMISSION_DENIED, unit, export_optimisation_proposals_csv,
             optimisation_pass_id=started["pass"].optimisation_pass_id, actor_roles=frozenset())
    _refused(ErrorCode.NOT_FOUND, unit, export_optimisation_proposals_csv,
             optimisation_pass_id="opp_01M2545JSD15ETSNNV904XA001", actor_roles=frozenset({"admin"}))
