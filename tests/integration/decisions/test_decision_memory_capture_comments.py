"""`ADR-0029` decision 10 (`CRIT-CAPTURE-01`, part A): the experts' ``comment`` events reach the decision memory through the ledger's port.

On a real database, with the composition root's own assembler registered as the port (as `test_decision_memory_capture.py` does) and only
the published artifacts replaced by a recording double. `MEM-COMMENTS-01` proved the memory's side (``capture_comment``, the carry-over
of ``earlier_comments``, the locks); what is shown here is the WIRING:

* a ``comment`` event of a finding that has a case is kept in the same transaction -- it leaves with the event when the unit of work is
  rolled back -- with its words, author and time, and changes no vote;
* a comment written before the case waits (no case is made by it), and the first ✓/✕ carries over, in the order they were written, the
  comments of its own observation recorded before it -- not another observation's, not twice;
* the assembler takes the observation's comment lock BEFORE it asks whether the case exists and before it reads the ledger, and a known
  case reads the ledger no more;
* the memory's refusals are not swallowed: an error of the capture fails the comment's decision, while "no case yet" and "forgotten case"
  are answers, not errors;
* the sweep repairs the comments of cases that exist (a process without the port), and leaves a comment of a case-less observation alone.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.bootstrap.adapters import MemoryCaptureAssembler, MemoryCaptureSweep
from auditmanager.decision_memory.public import MemoryReader
from auditmanager.decisions import append_decision_under_key, record_decision
from auditmanager.decisions import public as decisions_public
from auditmanager.decisions.public import register_decision_recorded, registered_decision_recorded
from auditmanager.shared.identity import DecisionMemoryStatusEventId, FindingObservationId


class _Geometry:
    def __init__(self) -> None:
        self.reads = 0

    def evidence_boxes_in(self, session: Session, run_id: str) -> dict[str, Any]:
        self.reads += 1
        return {}

    def portal_crops_in(self, session: Session, run_id: str) -> tuple[dict[str, Any], ...]:
        self.reads += 1
        return ()


@pytest.fixture
def memory() -> Iterator[SimpleNamespace]:
    geometry = _Geometry()
    assembler = MemoryCaptureAssembler(geometry=geometry)
    before = registered_decision_recorded()
    register_decision_recorded(assembler)
    try:
        yield SimpleNamespace(geometry=geometry, assembler=assembler)
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


def _observation(published: Any, second: bool = False) -> str:
    return str(published.second_finding_observation_id if second else published.finding_observation_id)


def _comments(session: Session) -> list[tuple[str, str]]:
    """(source ledger event, words) of every memory comment, in the order they were captured."""
    return [
        (row.source_decision_id, row.comment)
        for row in session.execute(text("SELECT source_decision_id, comment FROM decision_memory_comment ORDER BY captured_at, comment_id"))
    ]


def _forget(session: Session, observation_id: str) -> None:
    """What the operator tool does for one case, inside the caller's transaction (the forget event, then the content)."""
    case_id = session.execute(
        text("SELECT case_id FROM decision_memory_case WHERE origin_observation_id = :o"), {"o": observation_id}).scalar_one()
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


def test_a_comment_event_of_a_finding_with_a_case_is_kept_in_the_same_transaction(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    _event(session, published, "accept", "ок")
    case_id = session.execute(text("SELECT case_id FROM decision_memory_case")).scalar_one()
    before = MemoryReader().case_summary(session, case_id)
    author = session.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one()

    note = _event(session, published, "comment", "Согласовать с разделом АР, лист 12.", author_user_uid=author)
    row = session.execute(text("SELECT * FROM decision_memory_comment")).mappings().one()
    assert row["case_id"] == case_id and row["source_decision_id"] == note.decision_id
    assert row["comment"] == "Согласовать с разделом АР, лист 12."
    assert row["author_user_uid"] == author and row["decided_at"] == note.recorded_at

    # a comment is not a decision: no decision row, no new case, the vote and the count are what they were
    after = MemoryReader().case_summary(session, case_id)
    assert after == before and after is not None and (after.current_verdict, after.decision_count) == ("accepted", 1)
    assert (_count(session, "decision_memory_case"), _count(session, "decision_memory_decision")) == (1, 1)

    # a replay under the same key is answered from the ledger before the port is reached: still one row
    options: dict[str, Any] = dict(
        finding_uid=published.finding_uid, finding_observation_id=published.finding_observation_id, event_type="comment",
        idempotency_key="comment-replay-1", author_label="Петрова А.", author_user_uid=None, comment="Ещё одна.",
    )
    event, replayed = append_decision_under_key(session, **options)
    again, replayed_again = append_decision_under_key(session, **options)
    assert (replayed, replayed_again, again.decision_id) == (False, True, event.decision_id)
    assert _count(session, "decision_memory_comment") == 2

    # in the SAME transaction: the comment leaves with its event when the unit of work is rolled back
    savepoint = session.begin_nested()
    _event(session, published, "comment", "Эта заметка будет отменена.")
    assert _count(session, "decision_memory_comment") == 3
    savepoint.rollback()
    assert _count(session, "decision_memory_comment") == 2
    assert _count(session, "expert_decision_event", "event_type = 'comment'") == 2


def test_a_comment_before_the_case_waits_and_the_first_decision_carries_over_its_own_observations_comments_once(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    first = _event(session, published, "comment", "Первая заметка.")
    second = _event(session, published, "comment", "Вторая заметка.")
    elsewhere = _event(session, published, "comment", "Заметка к другому наблюдению.", second=True)
    assert _count(session, "decision_memory_comment") == 0 and _count(session, "decision_memory_case") == 0   # a comment makes no case
    assert memory.geometry.reads == 0                                          # and nothing was even assembled

    _event(session, published, "accept", "ок")
    assert _comments(session) == [(first.decision_id, "Первая заметка."), (second.decision_id, "Вторая заметка.")]   # in the order written
    assert _count(session, "decision_memory_case") == 1                        # the other observation is still without a case
    assert elsewhere.decision_id not in [source for source, _ in _comments(session)]

    # a note after the case is kept as it is written; the second decision carries over nothing twice
    third = _event(session, published, "comment", "Третья, уже после решения.")
    _event(session, published, "reject", "пересмотрено")
    assert [source for source, _ in _comments(session)] == [first.decision_id, second.decision_id, third.decision_id]
    assert _count(session, "decision_memory_decision") == 2

    # the other observation's own first decision carries its own comment, and only that one
    _event(session, published, "reject", "иное", second=True)
    assert (elsewhere.decision_id, "Заметка к другому наблюдению.") in _comments(session) and len(_comments(session)) == 4


def test_the_first_decision_carries_only_the_comments_of_its_own_observation_when_a_finding_has_two(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    """A finding identity outlives a run: a later run's observation carries the same ``finding_uid`` (the ledger's history is read by
    finding), but a case is one reviewed OBSERVATION, so a note on the other observation is not this case's."""
    other = FindingObservationId.new().value
    session.execute(text(
        "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, finding_text, "
        "recommendation_text, grounded, ungrounded_reason, analysis_profile_id, prompt_bundle_id, model_call_id, provider_mode) "
        "SELECT :new, run_id, finding_uid, stage_id, category, finding_text, recommendation_text, grounded, ungrounded_reason, "
        "analysis_profile_id, prompt_bundle_id, model_call_id, provider_mode FROM finding_observation "
        "WHERE finding_observation_id = :old"), {"new": other, "old": published.finding_observation_id})
    mine = _event(session, published, "comment", "Заметка к этому наблюдению.")
    _event(session, published, "comment", "Заметка к другому наблюдению того же замечания.", finding_observation_id=other)
    _event(session, published, "accept", "ок")
    assert _comments(session) == [(mine.decision_id, "Заметка к этому наблюдению.")]


def test_the_assembler_takes_the_comment_lock_before_it_asks_for_the_case_and_before_it_reads_the_ledger(
    session: Session, published: Any, memory: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    repository = memory.assembler._repository
    lock, has_case, history = repository.lock_observation_comments, repository.case_content_digest, decisions_public.decision_history

    def locked(session: Session, observation_id: str) -> None:
        calls.append("lock")
        lock(session, observation_id)

    def asked(session: Session, observation_id: str) -> Any:
        calls.append("case?")
        return has_case(session, observation_id)

    def read(session: Session, finding_uid: str) -> Any:
        calls.append("ledger")
        return history(session, finding_uid)

    monkeypatch.setattr(repository, "lock_observation_comments", locked)
    monkeypatch.setattr(repository, "case_content_digest", asked)
    monkeypatch.setattr(decisions_public, "decision_history", read)

    _event(session, published, "comment", "Заметка.")
    assert calls == ["lock"]                                                   # a comment takes the lock (its capture) and reads no ledger
    calls.clear()
    _event(session, published, "accept", "ок")
    assert calls.index("lock") < calls.index("case?") and calls.index("lock") < calls.index("ledger")
    calls.clear()
    _event(session, published, "reject", "пересмотрено")
    assert "ledger" not in calls and "lock" in calls                           # a known case reads no ledger; it still takes the lock

    # the lock outlives the call: it is held to the end of the decision's transaction (another session cannot take it)
    engine = session.get_bind().engine                                         # type: ignore[union-attr]
    with engine.connect() as other:
        free = other.execute(
            text("SELECT pg_try_advisory_xact_lock(hashtextextended(:k, 0))"),
            {"k": "decision_memory_comment_observation:" + _observation(published)}).scalar_one()
        other.rollback()
    assert free is False


def test_an_error_of_the_comment_capture_fails_the_comments_decision(
    session: Session, published: Any, memory: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ADR-0027` decision 4: a comment the memory cannot keep is not skipped; the event is not left in the ledger either."""
    _event(session, published, "accept", "ок")

    def refused(*_: Any, **__: Any) -> None:
        raise RuntimeError("the memory could not be written")

    monkeypatch.setattr(memory.assembler._repository, "capture_comment", refused)
    savepoint = session.begin_nested()
    with pytest.raises(RuntimeError, match="could not be written"):
        _event(session, published, "comment", "Заметка, которую память не приняла.")
    savepoint.rollback()
    assert _count(session, "expert_decision_event", "event_type = 'comment'") == 0 and _count(session, "decision_memory_comment") == 0


def test_a_case_less_comment_and_a_comment_of_a_forgotten_case_are_answers_not_errors(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    waiting = _event(session, published, "comment", "Заметка до решения.")             # waits_for_case
    _event(session, published, "accept", "ок")
    _forget(session, _observation(published))
    late = _event(session, published, "comment", "Заметка после забвения.")             # case_forgotten
    assert _count(session, "expert_decision_event", "event_type = 'comment'") == 2     # both decisions were recorded
    assert _count(session, "decision_memory_comment") == 0                             # and the forgotten case took no words back
    # the check is not vacuous: without the forget the very same comment is kept
    other = _event(session, published, "comment", "Заметка к другому делу.", second=True)
    _event(session, published, "accept", "ок", second=True)
    assert [source for source, _ in _comments(session)] == [other.decision_id]
    assert waiting.decision_id != late.decision_id


def test_the_sweep_repairs_the_comments_of_existing_cases_and_leaves_a_case_less_one_alone(
    session: Session, published: Any
) -> None:
    before = registered_decision_recorded()
    register_decision_recorded(None)                                                   # a process that decided without the port
    try:
        early = _event(session, published, "comment", "До решения.")
        _event(session, published, "accept", "ок")
        late = _event(session, published, "comment", "После решения.")
        unreached = _event(session, published, "comment", "К наблюдению без решения.", second=True)
    finally:
        register_decision_recorded(before)
    assert _count(session, "decision_memory_comment") == 0 and _count(session, "decision_memory_case") == 0

    connection = session.get_bind()
    factory = lambda: Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)  # noqa: E731
    sweep = MemoryCaptureSweep(factory, MemoryCaptureAssembler(geometry=_Geometry()), batch=500)
    first = sweep.run_once()
    assert first.captured >= 1 and first.comments_failed == 0
    # the case's first ✓ (captured by the sweep) carried the earlier note; the comment pass repaired the one that followed it
    kept = [source for source, _ in _comments(session)]
    assert early.decision_id in kept and late.decision_id in kept and unreached.decision_id not in kept
    assert first.comments_captured >= 1                                                # at least `late` (others may be committed)
    assert _count(session, "decision_memory_case", "origin_observation_id = :o", o=_observation(published, True)) == 0

    again = sweep.run_once()
    assert (again.captured, again.comments_captured, again.comments_failed) == (0, 0, 0)   # the memory's answer is the state: nothing twice
    assert [source for source, _ in _comments(session)] == kept
