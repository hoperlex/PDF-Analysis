"""`ADR-0029` decision 10 (`MEM-COMMENTS-01`) on a real database: the experts' ``comment`` events kept in ``decision_memory_comment``.

The findings go through the grounding gate and the publication (the suite's ``published`` fixture), the events through ``record_decision``
and the case through the composition root's own assembler (``assemble``). What this lane does NOT do is wire the capture into the
composition root (`CRIT-CAPTURE-01`), so the ledger's port stays unregistered here and each test hands the memory exactly what the wiring
will hand it: ``MemoryRepository.capture_comment`` for a comment event, ``CaptureSnapshot.earlier_comments`` for the first ✓/✕.

Shown: a comment of a case is kept once, with its words, author and time, and changes no vote; a comment written before the case waits and
is carried over by the first ✓/✕, and carrying again adds nothing; a comment of a FORGOTTEN case is not inserted (and the database would
refuse it: the guard is proved, so the check is not vacuous), nor is an earlier comment carried into one; a database refusal other than
that one propagates, so a capture that fails fails the decision; the read answers a case's comments oldest first and a forgotten case's
none; and the locks that keep a comment and a first decision from missing each other are the ones other sessions contend on.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.bootstrap.adapters import MemoryCaptureAssembler
from auditmanager.decision_memory.public import (
    COMMENT_ALREADY_CAPTURED,
    COMMENT_CAPTURED,
    COMMENT_REFUSED_CASE_FORGOTTEN,
    COMMENT_WAITS_FOR_CASE,
    CommentFact,
    MemoryReader,
    MemoryRepository,
)
from auditmanager.decisions import record_decision
from auditmanager.decisions.public import register_decision_recorded, registered_decision_recorded
from auditmanager.shared.identity import DecisionMemoryStatusEventId


class _Geometry:
    def evidence_boxes_in(self, session: Session, run_id: str) -> dict[str, Any]:
        return {}

    def portal_crops_in(self, session: Session, run_id: str) -> tuple[dict[str, Any], ...]:
        return ()


@pytest.fixture
def memory() -> Iterator[SimpleNamespace]:
    """The ledger's port is NOT registered: the wiring is the integrator's. The assembler only builds snapshots."""
    before = registered_decision_recorded()
    register_decision_recorded(None)
    try:
        yield SimpleNamespace(assembler=MemoryCaptureAssembler(geometry=_Geometry()), repository=MemoryRepository())
    finally:
        register_decision_recorded(before)


def _count(session: Session, table: str, where: str = "true", **parameters: Any) -> int:
    return int(session.execute(text(f"SELECT count(*) FROM {table} WHERE {where}"), parameters).scalar_one())


def _event(session: Session, published: Any, event_type: str, comment: str | None, *, second: bool = False, **extra: Any) -> Any:
    options: dict[str, Any] = dict(
        finding_uid=published.second_finding_uid if second else published.finding_uid,
        finding_observation_id=published.second_finding_observation_id if second else published.finding_observation_id,
        event_type=event_type, comment=comment, author_label="Петрова А.", author_user_uid=None,
    )
    options.update(extra)
    return record_decision(session, **options)


def _fact(event: Any, *, author: str | None = None) -> CommentFact:
    return CommentFact(
        source_decision_id=event.decision_id, comment=event.comment, author_user_uid=author, decided_at=event.recorded_at,
    )


def _decide(session: Session, memory: SimpleNamespace, published: Any, event_type: str = "accept", earlier: tuple[CommentFact, ...] = (),
            *, second: bool = False) -> Any:
    """A ✓/✕ and its capture, as the wiring will do it: the snapshot of the assembler, the earlier comments of the observation added."""
    event = _event(session, published, event_type, "по странице", second=second)
    snapshot = dataclasses.replace(memory.assembler.assemble(session, event, "direct"), earlier_comments=earlier)
    return memory.repository.capture(session, snapshot)


def _observation(published: Any, second: bool = False) -> str:
    return str(published.second_finding_observation_id if second else published.finding_observation_id)


def _case_id(session: Session, observation_id: str) -> str:
    return str(session.execute(
        text("SELECT case_id FROM decision_memory_case WHERE origin_observation_id = :o"), {"o": observation_id}).scalar_one())


def _forget(session: Session, case_id: str) -> None:
    """What the operator tool does for one case, inside the caller's transaction: the forget event, then the content (comments among it)."""
    actor = session.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one()
    session.execute(text(
        "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid, owner_permission_ref, "
        "forgotten_content_sha256) SELECT :id, case_id, 'forget', 'client_request', :actor, 'owner message', content_sha256 "
        "FROM decision_memory_case WHERE case_id = :c"),
        {"id": DecisionMemoryStatusEventId.new().value, "c": case_id, "actor": actor})
    for table in ("decision_memory_comment", "decision_memory_crop", "decision_memory_evidence", "decision_memory_norm_ref"):
        session.execute(text(f"DELETE FROM {table} WHERE case_id = :c"), {"c": case_id})
    session.execute(text(
        "DELETE FROM decision_memory_decision_text WHERE memory_decision_id IN "
        "(SELECT memory_decision_id FROM decision_memory_decision WHERE case_id = :c)"), {"c": case_id})
    session.execute(text("DELETE FROM decision_memory_content WHERE case_id = :c"), {"c": case_id})


def test_a_comment_of_a_case_is_kept_once_with_its_words_and_changes_no_vote(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    _decide(session, memory, published, "reject")
    case_id = _case_id(session, _observation(published))
    before = MemoryReader().case_summary(session, case_id)
    note = _event(session, published, "comment", "Согласовать с разделом АР, лист 12.")

    first = memory.repository.capture_comment(session, observation_id=_observation(published), comment=_fact(note))
    assert (first.outcome, first.case_id, first.comment_created) == (COMMENT_CAPTURED, case_id, True)
    row = session.execute(text("SELECT * FROM decision_memory_comment")).mappings().one()
    assert row["case_id"] == case_id and row["source_decision_id"] == note.decision_id
    assert row["comment"] == "Согласовать с разделом АР, лист 12." and row["author_user_uid"] is None
    assert row["decided_at"] == note.recorded_at and row["comment_id"].startswith("dmk_")

    again = memory.repository.capture_comment(session, observation_id=_observation(published), comment=_fact(note))
    assert (again.outcome, again.case_id) == (COMMENT_ALREADY_CAPTURED, case_id)
    assert _count(session, "decision_memory_comment") == 1                     # the same ledger event: one row
    # the sweep's question: which comment events of the ledger already have a row
    assert memory.repository.captured_comment_sources(session, [note.decision_id, "dec_01M5F21PBT7E8WRN3M61BDQFDD"]) == {note.decision_id}
    assert memory.repository.captured_comment_sources(session, []) == frozenset()

    # a comment is not a decision: the case's vote, its decisions and its standing are exactly what they were
    after = MemoryReader().case_summary(session, case_id)
    assert after == before and after is not None
    assert (after.current_verdict, after.decision_count) == ("rejected", 1)
    assert _count(session, "decision_memory_decision") == 1 and _count(session, "decision_memory_case") == 1


def test_a_comment_written_before_the_case_waits_and_the_first_decision_carries_it_over(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    note = _event(session, published, "comment", "Сначала заметка эксперта.")
    waiting = memory.repository.capture_comment(session, observation_id=_observation(published), comment=_fact(note))
    assert (waiting.outcome, waiting.case_id) == (COMMENT_WAITS_FOR_CASE, None)
    assert _count(session, "decision_memory_comment") == 0 and _count(session, "decision_memory_case") == 0   # a comment makes no case

    result = _decide(session, memory, published, "accept", earlier=(_fact(note),))
    assert result.case_created and result.decision_created and result.comments_carried == 1
    row = session.execute(text("SELECT case_id, source_decision_id, comment FROM decision_memory_comment")).mappings().one()
    assert (row["case_id"], row["source_decision_id"], row["comment"]) == (
        _case_id(session, _observation(published)), note.decision_id, "Сначала заметка эксперта.")


def test_carrying_the_earlier_comments_over_is_idempotent(session: Session, published: Any, memory: SimpleNamespace) -> None:
    older = _event(session, published, "comment", "Первая заметка.")
    newer = _event(session, published, "comment", "Вторая заметка.")
    earlier = (_fact(newer), _fact(older), _fact(older))                       # out of order and with a duplicate
    event = _event(session, published, "accept", "ок")
    snapshot = dataclasses.replace(memory.assembler.assemble(session, event, "direct"), earlier_comments=earlier)

    first = memory.repository.capture(session, snapshot)
    assert first.comments_carried == 2 and _count(session, "decision_memory_comment") == 2

    replay = memory.repository.capture(session, snapshot)                      # the very same capture again
    assert (replay.decision_created, replay.comments_carried) == (False, 0)
    assert _count(session, "decision_memory_comment") == 2

    # the expert decides again and the assembler hands in the same earlier comments: still two rows, nothing new
    again = _decide(session, memory, published, "reject", earlier=earlier)
    assert (again.case_created, again.decision_created, again.comments_carried) == (False, True, 0)
    assert _count(session, "decision_memory_comment") == 2 and _count(session, "decision_memory_decision") == 2

    # the carry preserved the order the expert wrote them in
    words = session.execute(text("SELECT comment FROM decision_memory_comment ORDER BY captured_at, comment_id")).scalars().all()
    assert words == ["Первая заметка.", "Вторая заметка."]
    # and a comment that arrives after the case is the only new row
    third = _event(session, published, "comment", "Третья, уже после решения.")
    assert memory.repository.capture_comment(
        session, observation_id=_observation(published), comment=_fact(third)).outcome == COMMENT_CAPTURED
    assert _count(session, "decision_memory_comment") == 3


def test_a_comment_of_a_forgotten_case_is_not_inserted(session: Session, published: Any, memory: SimpleNamespace) -> None:
    _decide(session, memory, published, "accept")
    case_id = _case_id(session, _observation(published))
    kept = _event(session, published, "comment", "Заметка до забвения.")
    memory.repository.capture_comment(session, observation_id=_observation(published), comment=_fact(kept))
    assert _count(session, "decision_memory_comment") == 1

    _forget(session, case_id)
    assert _count(session, "decision_memory_comment") == 0                     # the forget took the comment with the rest

    late = _event(session, published, "comment", "Заметка после забвения.")
    result = memory.repository.capture_comment(session, observation_id=_observation(published), comment=_fact(late))
    assert (result.outcome, result.case_id, result.comment_created) == (COMMENT_REFUSED_CASE_FORGOTTEN, case_id, False)
    assert _count(session, "decision_memory_comment") == 0

    # the check is not vacuous: the database refuses the very row the repository declined to send
    savepoint = session.begin_nested()
    with pytest.raises(DBAPIError) as refused:
        session.execute(text(
            "INSERT INTO decision_memory_comment (comment_id, case_id, source_decision_id, comment, decided_at) "
            "VALUES ('dmk_01M5F21PBT7E8WRN3M61BDQFDD', :c, :s, 'x', clock_timestamp())"), {"c": case_id, "s": late.decision_id})
    assert getattr(refused.value.orig, "sqlstate", None) == "AM003"
    savepoint.rollback()


def test_the_earlier_comments_of_a_forgotten_case_are_not_carried_into_it(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    _decide(session, memory, published, "accept")
    case_id = _case_id(session, _observation(published))
    _forget(session, case_id)
    note = _event(session, published, "comment", "Заметка, написанная до решения.")

    result = _decide(session, memory, published, "reject", earlier=(_fact(note),))   # the expert decides again on the forgotten case
    assert (result.case_created, result.decision_created, result.comments_carried) == (False, True, 0)
    assert _count(session, "decision_memory_comment") == 0                     # the decision is recorded; the words are not
    assert _count(session, "decision_memory_decision", "case_id = :c", c=case_id) == 2

    # the replay of the same capture (a decision already kept) carries nothing either
    event = _event(session, published, "reject", "ещё раз")
    snapshot = dataclasses.replace(memory.assembler.assemble(session, event, "direct"), earlier_comments=(_fact(note),))
    memory.repository.capture(session, snapshot)
    assert memory.repository.capture(session, snapshot).comments_carried == 0
    assert _count(session, "decision_memory_comment") == 0


def test_a_database_refusal_other_than_a_forgotten_case_propagates_and_fails_the_capture(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    """No silent fallback (`ADR-0027` decision 4): a comment the table refuses is an error for the caller, not a skipped row."""
    _decide(session, memory, published, "accept")
    note = _event(session, published, "comment", "Заметка.")
    broken = dataclasses.replace(_fact(note), author_user_uid="not-an-account")
    savepoint = session.begin_nested()
    with pytest.raises(DBAPIError) as refused:
        memory.repository.capture_comment(session, observation_id=_observation(published), comment=broken)
    assert getattr(refused.value.orig, "sqlstate", None) == "23514"            # the author's identity format CHECK
    savepoint.rollback()
    assert _count(session, "decision_memory_comment") == 0


def test_the_read_answers_a_cases_comments_oldest_first_and_a_forgotten_case_none(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    reader = MemoryReader()
    _decide(session, memory, published, "accept")
    _decide(session, memory, published, "reject", second=True)
    first_case = _case_id(session, _observation(published))
    second_case = _case_id(session, _observation(published, True))
    notes = [_event(session, published, "comment", f"Заметка {i}.") for i in range(3)]
    other = _event(session, published, "comment", "Заметка к другому делу.", second=True)
    for note in notes:
        memory.repository.capture_comment(session, observation_id=_observation(published), comment=_fact(note, author="usr_" + "0" * 26))
    memory.repository.capture_comment(session, observation_id=_observation(published, True), comment=_fact(other))

    detail = reader.get_case(session, first_case)
    assert detail is not None
    assert [c["comment"] for c in detail.comments] == ["Заметка 0.", "Заметка 1.", "Заметка 2."]
    assert set(detail.comments[0]) == {"comment_id", "author_user_uid", "comment", "decided_at"}
    assert detail.comments[0]["author_user_uid"] == "usr_" + "0" * 26
    batch = reader.comments_for_cases(session, [first_case, second_case, "dmc_01M5F21PBT7E8WRN3M61BDQFDD"])
    assert set(batch) == {first_case, second_case} and [c["comment"] for c in batch[second_case]] == ["Заметка к другому делу."]
    assert reader.comments_for_cases(session, []) == {}
    # a comment is not a decision: the case's decisions are untouched by the three comments
    assert [d["event_type"] for d in detail.decisions] == ["accept"]

    _forget(session, first_case)
    forgotten = reader.get_case(session, first_case)
    assert forgotten is not None and forgotten.summary.status == "forgotten" and forgotten.comments == ()
    assert first_case not in reader.comments_for_cases(session, [first_case])
    other_detail = reader.get_case(session, second_case)
    assert other_detail is not None and len(other_detail.comments) == 1        # another case's comment is not touched


def test_a_comment_and_a_first_decision_contend_on_the_locks_the_repository_documents(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    """While this transaction holds the observation's comment lock and the case's status lock, another session cannot take either:
    so a comment and a first ✓/✕ (and a forget) of one observation are serialised, not interleaved."""
    _decide(session, memory, published, "accept")
    note = _event(session, published, "comment", "Заметка.")
    memory.repository.capture_comment(session, observation_id=_observation(published), comment=_fact(note))
    case_id = _case_id(session, _observation(published))
    engine = session.get_bind().engine                                         # type: ignore[union-attr]
    with engine.connect() as other:
        for key in ("decision_memory_comment_observation:" + _observation(published), "decision_memory_status:" + case_id):
            free = other.execute(text("SELECT pg_try_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": key}).scalar_one()
            assert free is False, key
        stranger = other.execute(
            text("SELECT pg_try_advisory_xact_lock(hashtextextended('decision_memory_comment_observation:fobs_other', 0))")
        ).scalar_one()
        assert stranger is True                                                # another observation's lock is free: no global serialisation
        other.rollback()
