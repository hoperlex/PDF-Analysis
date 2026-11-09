"""`DECISION-MEMORY-01` phase M2 over cases that were really captured: withdraw, restore, the read model, a forgotten case and the settings.

The findings go through the grounding gate and the publication (the suite's ``published`` fixture) and the decisions through
``record_decision`` with the composition root's own assembler registered as the ledger's port -- the same path ``test_decision_memory_capture``
proves. Only the object store's artifacts are replaced by a double. Every test rolls back, because the memory is append-only.

Shown: a withdraw and a restore change the standing and append a status event each, never edit the case, and are refused (typed, with no event
written) when the case is already in that state; a malformed identity, an unknown case and a free-text reason are validation or not-found;
the read model lists, filters and pages cases and answers one case with its content and history; a FORGOTTEN case (the content removed in the
same transaction as its forget event, as the operator tool does) answers its tombstone only, takes no status event (``conflict``,
``memory_case_forgotten``) and, when the expert decides again, gets the new decision row WITHOUT words; and ``data_class`` is the installation
setting read at every capture (nothing journalled: ``test``).
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.bootstrap.adapters import MemoryCaptureAssembler
from auditmanager.decision_memory.public import (
    MemoryReader,
    restore_case,
    withdraw_case,
)
from auditmanager.decisions import record_decision
from auditmanager.decisions.public import register_decision_recorded, registered_decision_recorded
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DecisionMemoryCaseId, DecisionMemoryStatusEventId


class _Geometry:
    def evidence_boxes_in(self, session: Session, run_id: str) -> dict[str, Any]:
        return {}

    def portal_crops_in(self, session: Session, run_id: str) -> tuple[dict[str, Any], ...]:
        return ()


@pytest.fixture
def memory() -> Iterator[SimpleNamespace]:
    assembler = MemoryCaptureAssembler(geometry=_Geometry())
    before = registered_decision_recorded()
    register_decision_recorded(assembler)
    try:
        yield SimpleNamespace(assembler=assembler)
    finally:
        register_decision_recorded(before)


def _count(session: Session, table: str, where: str = "true", **parameters: Any) -> int:
    return int(session.execute(text(f"SELECT count(*) FROM {table} WHERE {where}"), parameters).scalar_one())


def _admin(session: Session) -> str:
    return str(session.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())


def _decide(session: Session, published: Any, event_type: str = "accept", *, second: bool = False, **extra: Any) -> Any:
    options: dict[str, Any] = dict(
        finding_uid=published.second_finding_uid if second else published.finding_uid,
        finding_observation_id=published.second_finding_observation_id if second else published.finding_observation_id,
        event_type=event_type, comment="подтверждено по странице", author_label="Петрова А.", author_user_uid=None,
    )
    options.update(extra)
    return record_decision(session, **options)


def _case_id(session: Session, observation_id: str) -> str:
    return str(session.execute(
        text("SELECT case_id FROM decision_memory_case WHERE origin_observation_id = :o"), {"o": observation_id}).scalar_one())


def _refused(call: Any, code: ErrorCode, **details: Any) -> DomainError:
    with pytest.raises(DomainError) as raised:
        call()
    assert raised.value.code is code, raised.value
    for key, value in details.items():
        assert raised.value.detail_fields[key] == value, raised.value.detail_fields
    return raised.value


def test_a_withdraw_and_a_restore_move_the_standing_append_an_event_each_and_never_touch_the_case(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    _decide(session, published)
    case_id = _case_id(session, published.finding_observation_id)
    actor, reader = _admin(session), MemoryReader()
    before = {t: _count(session, t) for t in ("decision_memory_case", "decision_memory_decision", "decision_memory_content",
                                              "decision_memory_evidence", "decision_memory_decision_text")}
    digest = session.execute(text("SELECT content_sha256 FROM decision_memory_case WHERE case_id = :c"), {"c": case_id}).scalar_one()

    assert reader.case_summary(session, case_id).status == "active"          # type: ignore[union-attr]
    withdrawn = withdraw_case(session, case_id=case_id, actor_user_uid=actor, reason_code="wrong_decision")
    assert (withdrawn.status, withdrawn.kind, withdrawn.reason_code) == ("withdrawn", "withdraw", "wrong_decision")
    summary = reader.case_summary(session, case_id)
    assert summary is not None and summary.status == "withdrawn" and summary.status_reason_code == "wrong_decision"
    assert summary.status_event_id == withdrawn.status_event_id and summary.current_verdict == "accepted"

    # already withdrawn: typed refusal, and nothing was appended
    _refused(lambda: withdraw_case(session, case_id=case_id, actor_user_uid=actor, reason_code="other"),
             ErrorCode.STATE_TRANSITION_NOT_ALLOWED, machine="decision_memory_case", current_state="withdrawn")
    assert _count(session, "decision_memory_status_event", "case_id = :c", c=case_id) == 1

    restored = restore_case(session, case_id=case_id, actor_user_uid=actor, reason_code="other")
    assert (restored.status, restored.kind) == ("active", "restore")
    assert reader.case_summary(session, case_id).status == "active"          # type: ignore[union-attr]
    _refused(lambda: restore_case(session, case_id=case_id, actor_user_uid=actor, reason_code="other"),
             ErrorCode.STATE_TRANSITION_NOT_ALLOWED, current_state="active")
    assert withdraw_case(session, case_id=case_id, actor_user_uid=actor, reason_code="test_data").status == "withdrawn"  # again, after a restore

    events = session.execute(text(
        "SELECT kind, reason_code, actor_user_uid, command_id FROM decision_memory_status_event WHERE case_id = :c "
        "ORDER BY created_at"), {"c": case_id}).all()
    assert [(e.kind, e.reason_code) for e in events] == [("withdraw", "wrong_decision"), ("restore", "other"), ("withdraw", "test_data")]
    assert {e.actor_user_uid for e in events} == {actor} and {e.command_id for e in events} == {None}
    assert before == {t: _count(session, t) for t in before}                  # not one row of the case itself moved
    assert session.execute(text("SELECT content_sha256 FROM decision_memory_case WHERE case_id = :c"), {"c": case_id}).scalar_one() == digest


def test_a_malformed_identity_an_unknown_case_and_a_free_text_reason_are_refused_before_anything_is_written(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    _decide(session, published)
    case_id = _case_id(session, published.finding_observation_id)
    actor = _admin(session)
    _refused(lambda: withdraw_case(session, case_id="not-a-case", actor_user_uid=actor, reason_code="other"), ErrorCode.VALIDATION_FAILED, field="case_id")
    _refused(lambda: withdraw_case(session, case_id=DecisionMemoryCaseId.new().value, actor_user_uid=actor, reason_code="other"), ErrorCode.NOT_FOUND)
    for reason in ("because I said so", "", "Other"):
        _refused(lambda reason=reason: withdraw_case(session, case_id=case_id, actor_user_uid=actor, reason_code=reason),
                 ErrorCode.VALIDATION_FAILED, field="reason_code")
    assert _count(session, "decision_memory_status_event") == 0


def test_the_read_model_lists_filters_pages_and_answers_one_case_with_its_history(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    _decide(session, published)
    _decide(session, published, "reject", comment="передумал")                   # a second decision on the SAME observation
    _decide(session, published, second=True)
    first = _case_id(session, published.finding_observation_id)
    second = _case_id(session, published.second_finding_observation_id)
    reader, actor = MemoryReader(), _admin(session)
    withdraw_case(session, case_id=second, actor_user_uid=actor, reason_code="capture_defect")

    mine = {"origin_project_uid": published.project_uid}
    everything = reader.list_cases(session, **mine)
    assert {c.case_id for c in everything.items} == {first, second} and everything.next_after is None
    by_id = {c.case_id: c for c in everything.items}
    assert by_id[first].decision_count == 2 and by_id[first].current_verdict == "rejected"   # the latest decision is current
    assert by_id[second].decision_count == 1 and by_id[second].current_verdict == "accepted"
    assert [c.case_id for c in reader.list_cases(session, status="withdrawn", **mine).items] == [second]
    assert [c.case_id for c in reader.list_cases(session, status="active", **mine).items] == [first]
    assert [c.case_id for c in reader.list_cases(session, category="explicit_placeholder", **mine).items] == [second]
    assert [c.case_id for c in reader.list_cases(session, verdict="rejected", **mine).items] == [first]
    assert [c.case_id for c in reader.list_cases(session, data_class="real", **mine).items] == []
    assert reader.list_cases(session, origin_project_uid="prj_01ARZ3NDEKTSV4RRFFQ69G5FAV").items == ()

    page = reader.list_cases(session, limit=1, **mine)
    assert len(page.items) == 1 and page.next_after is not None
    rest = reader.list_cases(session, limit=1, after=page.next_after, **mine)
    assert {page.items[0].case_id, rest.items[0].case_id} == {first, second} and rest.next_after is None
    _refused(lambda: reader.list_cases(session, status="gone"), ErrorCode.VALIDATION_FAILED, field="status")
    _refused(lambda: reader.list_cases(session, limit=0), ErrorCode.VALIDATION_FAILED, field="limit")

    detail = reader.get_case(session, first)
    assert detail is not None and detail.summary.status == "active"
    assert detail.content is not None and detail.content["finding_text"] == "Степень огнестойкости указана по-разному."
    assert [e["quote"] for e in detail.evidence] == ["Степень огнестойкости здания — II.", "Степень огнестойкости здания — III."]
    assert [(d["event_type"], d["comment"]) for d in detail.decisions] == [("accept", "подтверждено по странице"), ("reject", "передумал")]
    assert detail.status_events == () and detail.norm_refs == () and detail.crops == ()
    withdrawn = reader.get_case(session, second)
    assert withdrawn is not None and [e["kind"] for e in withdrawn.status_events] == ["withdraw"]
    assert reader.get_case(session, DecisionMemoryCaseId.new().value) is None

    counts = reader.counts(session)
    assert counts.cases >= 2 and counts.decisions >= 3
    assert ("withdrawn", "test") in {(status, klass) for status, klass, _ in counts.by_status_and_class}


def _forget(session: Session, case_id: str, actor: str) -> None:
    """What the operator tool does for one case, inside the caller's transaction: the forget event, then the content."""
    session.execute(text(
        "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid, owner_permission_ref, "
        "forgotten_content_sha256) SELECT :id, case_id, 'forget', 'client_request', :actor, 'owner message', content_sha256 "
        "FROM decision_memory_case WHERE case_id = :c"),
        {"id": DecisionMemoryStatusEventId.new().value, "c": case_id, "actor": actor})
    for table in ("decision_memory_crop", "decision_memory_evidence", "decision_memory_norm_ref"):
        session.execute(text(f"DELETE FROM {table} WHERE case_id = :c"), {"c": case_id})
    session.execute(text(
        "DELETE FROM decision_memory_decision_text WHERE memory_decision_id IN "
        "(SELECT memory_decision_id FROM decision_memory_decision WHERE case_id = :c)"), {"c": case_id})
    session.execute(text("DELETE FROM decision_memory_content WHERE case_id = :c"), {"c": case_id})


def test_a_forgotten_case_answers_its_tombstone_takes_no_status_event_and_a_new_decision_gets_no_words(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    _decide(session, published, comment="слова эксперта")
    case_id = _case_id(session, published.finding_observation_id)
    actor, reader = _admin(session), MemoryReader()
    digest = session.execute(text("SELECT content_sha256 FROM decision_memory_case WHERE case_id = :c"), {"c": case_id}).scalar_one()

    _forget(session, case_id, actor)

    detail = reader.get_case(session, case_id)
    assert detail is not None and detail.summary.status == "forgotten"
    assert detail.content is None and detail.evidence == () and detail.norm_refs == () and detail.crops == ()
    assert [(d["event_type"], d["verdict"], d["comment"]) for d in detail.decisions] == [("accept", "accepted", None)]   # no words survive
    (tombstone,) = detail.status_events
    assert tombstone["kind"] == "forget" and tombstone["forgotten_content_sha256"] == digest
    assert tombstone["owner_permission_ref"] == "owner message" and tombstone["actor_user_uid"] == actor
    assert [c.case_id for c in reader.list_cases(session, status="forgotten", origin_project_uid=published.project_uid).items] == [case_id]

    for call in (withdraw_case, restore_case):
        _refused(lambda call=call: call(session, case_id=case_id, actor_user_uid=actor, reason_code="other"),
                 ErrorCode.CONFLICT, conflict_reason="memory_case_forgotten")

    # the expert decides AGAIN on the observation whose case was forgotten: the decision is recorded, the words are not
    event = _decide(session, published, "reject", comment="новые слова эксперта")
    decisions = session.execute(text(
        "SELECT d.source_decision_id, d.verdict, t.comment FROM decision_memory_decision d "
        "LEFT JOIN decision_memory_decision_text t ON t.memory_decision_id = d.memory_decision_id WHERE d.case_id = :c ORDER BY d.decided_at"),
        {"c": case_id}).all()
    assert [(row.verdict, row.comment) for row in decisions] == [("accepted", None), ("rejected", None)]
    assert decisions[1].source_decision_id == event.decision_id                # captured, so guard G1 and the sweep see it done
    assert _count(session, "decision_memory_content", "case_id = :c", c=case_id) == 0
    assert _count(session, "decision_memory_decision_text", "memory_decision_id IN (SELECT memory_decision_id FROM "
                  "decision_memory_decision WHERE case_id = :c)", c=case_id) == 0
    assert session.execute(text("SELECT content_sha256 FROM decision_memory_case WHERE case_id = :c"), {"c": case_id}).scalar_one() == digest


def test_the_data_class_is_the_installation_setting_read_at_every_capture(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    reader, actor = MemoryReader(), _admin(session)
    settings = reader.settings(session)
    assert (settings.data_class, settings.training_use, settings.data_class_revision) == ("test", "off", 0)   # nothing journalled

    def journal(revision: int, value: str, name: str = "data_class") -> None:
        session.execute(text(
            "INSERT INTO decision_memory_setting_event (setting_name, revision, value, actor_user_uid, owner_permission_ref) "
            "VALUES (:n, :r, :v, :a, NULL)"), {"n": name, "r": revision, "v": value, "a": actor})

    _decide(session, published)                                               # captured before the switch: test
    journal(1, "real")
    assert reader.settings(session).data_class == "real" and reader.settings(session).data_class_revision == 1
    _decide(session, published, second=True)                                  # captured after: real
    first = _case_id(session, published.finding_observation_id)
    second = _case_id(session, published.second_finding_observation_id)
    klass = {row.case_id: row.data_class for row in session.execute(text("SELECT case_id, data_class FROM decision_memory_case"))}
    assert (klass[first], klass[second]) == ("test", "real")                  # a case keeps the class it was captured with
    # a later decision on the first observation does not reclassify it
    _decide(session, published, "reject")
    assert session.execute(text("SELECT data_class FROM decision_memory_case WHERE case_id = :c"), {"c": first}).scalar_one() == "test"
    assert [c.case_id for c in reader.list_cases(session, data_class="real", origin_project_uid=published.project_uid).items] == [second]

    journal(2, "test")
    assert reader.settings(session).data_class == "test"                      # the latest revision wins
    journal(1, "off", "training_use")
    assert reader.settings(session).training_use == "off" and not reader.settings(session).training_enabled

    # an assembler built with a pinned class (the tests' way) ignores the journal
    pinned = MemoryCaptureAssembler(geometry=_Geometry(), data_class="real")
    assert pinned._pinned_data_class == "real"                                # noqa: SLF001
    with pytest.raises(ValueError):
        MemoryCaptureAssembler(geometry=_Geometry(), data_class="production")
