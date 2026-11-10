"""`ADR-0029` decision 10 (`MEM-COMMENTS-01`): the memory keeps an expert's ``comment`` events, with no database.

The repository's SQL is replaced by a small recording double of a session that answers the statements the way the table does (a unique
``source_decision_id``, ``ON CONFLICT DO NOTHING``), so what is shown here is the repository's own logic: which statements it sends, in
which order and under which conditions. The same behaviour on a real PostgreSQL, with the real forget guard, is
``tests/integration/decisions/test_decision_memory_comments.py``.

Shown: a comment is stored once, whatever the number of times the same ledger event is handed in; a comment of an observation with no case
waits and writes nothing; a comment of a FORGOTTEN case is not inserted (no ``INSERT`` is sent at all); carrying the earlier comments over
is idempotent, keeps one row per ledger event and stores them oldest first; and the value refuses what the table would refuse.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from auditmanager.decision_memory.public import (
    COMMENT_ALREADY_CAPTURED,
    COMMENT_CAPTURED,
    COMMENT_MAX_CHARS,
    COMMENT_REFUSED_CASE_FORGOTTEN,
    COMMENT_WAITS_FOR_CASE,
    CaptureSnapshot,
    CaseContent,
    CaseOrigin,
    CommentCaptureResult,
    CommentFact,
    DecisionFact,
    MemoryRepository,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DecisionId, DecisionMemoryCaseId

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)
OBSERVATION = "fobs_01M5F21PBT7E8WRN3M61BDQFDD"


def _fact(minutes: int = 0, comment: str = "Проверить по разделу КР.", source: str | None = None, **extra: Any) -> CommentFact:
    return CommentFact(
        source_decision_id=DecisionId.new().value if source is None else source, comment=comment, author_user_uid=None,
        decided_at=NOW + timedelta(minutes=minutes), **extra,
    )


@dataclass
class _Result:
    value: Any = None

    def scalar_one_or_none(self) -> Any:
        return self.value

    def first(self) -> Any:
        return self.value

    def mappings(self) -> "_Result":
        return self

    def one(self) -> Any:
        return self.value


@dataclass
class _Session:
    """What the comment statements of the repository see: one case at most, its standing and the comment rows."""

    case_id: str | None = None
    forgotten: bool = False
    comments: dict[str, dict[str, Any]] = field(default_factory=dict)   # by source_decision_id: the table's unique column
    statements: list[str] = field(default_factory=list)
    locks: list[str] = field(default_factory=list)

    def execute(self, statement: Any, parameters: Any = None) -> _Result:
        sql = " ".join(str(statement).split())
        if sql.startswith("SELECT pg_advisory_xact_lock"):
            self.locks.append(parameters["key"])
            return _Result()
        if sql.startswith("SELECT case_id FROM decision_memory_case WHERE origin_observation_id"):
            return _Result(self.case_id)
        if sql.startswith("SELECT 1 FROM decision_memory_status_event"):
            return _Result((1,) if self.forgotten else None)
        if sql.startswith("INSERT INTO decision_memory_comment"):
            self.statements.append("INSERT comment")
            if parameters["source_decision_id"] in self.comments:
                return _Result(None)                                       # ON CONFLICT DO NOTHING: no row returned
            self.comments[parameters["source_decision_id"]] = dict(parameters)
            return _Result(parameters["comment_id"])
        raise AssertionError(f"a statement the comment path should not send: {sql}")


@pytest.fixture
def repository() -> MemoryRepository:
    return MemoryRepository()


class TestTheValue:
    def test_it_takes_a_ledger_identity_and_words(self) -> None:
        fact = _fact()
        assert fact.comment == "Проверить по разделу КР." and fact.author_user_uid is None

    @pytest.mark.parametrize("source", ["", "dec_short", "fo_01M5F21PBT7E8WRN3M61BDQFDD", "not an id"])
    def test_a_source_that_is_not_a_decision_identity_is_refused(self, source: str) -> None:
        with pytest.raises(DomainError) as refused:
            _fact(source=source)
        assert refused.value.code is ErrorCode.VALIDATION_FAILED

    @pytest.mark.parametrize("words", ["", "   ", "\n\t"])
    def test_blank_words_are_refused(self, words: str) -> None:
        with pytest.raises(DomainError) as refused:
            _fact(comment=words)
        assert refused.value.code is ErrorCode.VALIDATION_FAILED

    def test_the_ceiling_is_the_tables(self) -> None:
        assert _fact(comment="а" * COMMENT_MAX_CHARS).comment.endswith("а")
        with pytest.raises(DomainError) as refused:
            _fact(comment="а" * (COMMENT_MAX_CHARS + 1))
        assert refused.value.code is ErrorCode.VALIDATION_FAILED

    def test_an_outcome_outside_the_closed_set_is_refused(self) -> None:
        with pytest.raises(DomainError):
            CommentCaptureResult(case_id=None, outcome="stored")
        assert CommentCaptureResult(case_id="x", outcome=COMMENT_CAPTURED).comment_created is True
        assert CommentCaptureResult(case_id="x", outcome=COMMENT_ALREADY_CAPTURED).comment_created is False


class TestCapturingAComment:
    def test_a_comment_of_a_case_is_stored_once_however_often_it_is_handed_in(self, repository: MemoryRepository) -> None:
        case_id = DecisionMemoryCaseId.new().value
        session = _Session(case_id=case_id)
        fact = _fact()
        first = repository.capture_comment(session, observation_id=OBSERVATION, comment=fact)  # type: ignore[arg-type]
        again = repository.capture_comment(session, observation_id=OBSERVATION, comment=fact)  # type: ignore[arg-type]
        assert (first.outcome, first.case_id) == (COMMENT_CAPTURED, case_id)
        assert (again.outcome, again.case_id) == (COMMENT_ALREADY_CAPTURED, case_id)
        assert list(session.comments) == [fact.source_decision_id] and session.statements == ["INSERT comment", "INSERT comment"]
        stored = session.comments[fact.source_decision_id]
        assert (stored["case_id"], stored["comment"], stored["decided_at"]) == (case_id, fact.comment, fact.decided_at)

    def test_a_comment_of_an_observation_with_no_case_waits_and_writes_nothing(self, repository: MemoryRepository) -> None:
        session = _Session(case_id=None)
        result = repository.capture_comment(session, observation_id=OBSERVATION, comment=_fact())  # type: ignore[arg-type]
        assert (result.outcome, result.case_id, result.comment_created) == (COMMENT_WAITS_FOR_CASE, None, False)
        assert session.statements == [] and session.comments == {}

    def test_a_comment_of_a_forgotten_case_is_not_inserted(self, repository: MemoryRepository) -> None:
        case_id = DecisionMemoryCaseId.new().value
        session = _Session(case_id=case_id, forgotten=True)
        result = repository.capture_comment(session, observation_id=OBSERVATION, comment=_fact())  # type: ignore[arg-type]
        assert (result.outcome, result.case_id) == (COMMENT_REFUSED_CASE_FORGOTTEN, case_id)
        assert session.statements == [] and session.comments == {}          # not even an INSERT was sent to be refused

    def test_the_observation_and_the_case_are_locked_before_anything_is_read(self, repository: MemoryRepository) -> None:
        """Both advisory locks: the observation's (a comment and a first decision must not miss each other) and the case's, the key the
        forget and the status guard take, so a forget in flight finishes before this comment is judged."""
        case_id = DecisionMemoryCaseId.new().value
        session = _Session(case_id=case_id)
        repository.capture_comment(session, observation_id=OBSERVATION, comment=_fact())  # type: ignore[arg-type]
        assert session.locks == ["decision_memory_comment_observation:" + OBSERVATION, "decision_memory_status:" + case_id]


class TestCarryingEarlierComments:
    def _carry(self, repository: MemoryRepository, session: _Session, facts: tuple[CommentFact, ...], *, created: bool) -> int:
        case_id = session.case_id or DecisionMemoryCaseId.new().value
        return repository._carry_comments(session, case_id, facts, case_created=created)  # type: ignore[arg-type]  # noqa: SLF001

    def test_carrying_is_idempotent_and_keeps_one_row_per_ledger_event(self, repository: MemoryRepository) -> None:
        session = _Session(case_id=DecisionMemoryCaseId.new().value)
        a, b = _fact(1), _fact(2)
        assert self._carry(repository, session, (b, a, a), created=True) == 2         # a handed in twice: one row
        assert self._carry(repository, session, (a, b), created=False) == 0           # a replay adds none
        assert self._carry(repository, session, (a, b), created=False) == 0
        assert sorted(session.comments) == sorted([a.source_decision_id, b.source_decision_id])

    def test_the_earlier_comments_are_stored_oldest_first(self, repository: MemoryRepository) -> None:
        session = _Session(case_id=DecisionMemoryCaseId.new().value)
        late, early = _fact(30, "позже"), _fact(5, "раньше")
        self._carry(repository, session, (late, early), created=True)
        assert [row["comment"] for row in session.comments.values()] == ["раньше", "позже"]

    def test_a_comment_handed_in_later_is_the_only_new_one(self, repository: MemoryRepository) -> None:
        session = _Session(case_id=DecisionMemoryCaseId.new().value)
        first, second = _fact(1), _fact(2)
        assert self._carry(repository, session, (first,), created=True) == 1
        assert self._carry(repository, session, (first, second), created=False) == 1

    def test_a_forgotten_case_takes_none_of_them(self, repository: MemoryRepository) -> None:
        session = _Session(case_id=DecisionMemoryCaseId.new().value, forgotten=True)
        assert self._carry(repository, session, (_fact(1), _fact(2)), created=False) == 0
        assert session.statements == [] and session.comments == {}

    def test_nothing_handed_in_sends_nothing(self, repository: MemoryRepository) -> None:
        session = _Session(case_id=DecisionMemoryCaseId.new().value)
        assert self._carry(repository, session, (), created=False) == 0
        assert session.locks == [] and session.statements == []


def test_a_snapshot_carries_its_earlier_comments_and_defaults_to_none() -> None:
    origin = CaseOrigin(
        observation_id=OBSERVATION, finding_uid="fnd_01M5F21PBT7E8WRN3M61BDQFDD", project_uid="prj_01M5F21PBT7E8WRN3M61BDQFDD",
        document_uid="doc_01M5F21PBT7E8WRN3M61BDQFDD", version_uid="ver_01M5F21PBT7E8WRN3M61BDQFDD", run_id="run_01M5F21PBT7E8WRN3M61BDQFDD",
    )
    decision = DecisionFact(
        source_decision_id=DecisionId.new().value, event_type="accept", severity=None, comment="ок", author_user_uid=None,
        origin_kind="direct", decided_at=NOW,
    )
    content = CaseContent(
        category="internal_contradiction", finding_text="Степень указана по-разному.", recommendation_text="Согласовать.",
        proposed_severity=None, required_value=None, stated_value=None, stage_id="text_analysis",
        analysis_profile_id="ap_01M5F21PBT7E8WRN3M61BDQFDD", prompt_bundle_id="pb_01M5F21PBT7E8WRN3M61BDQFDD",
        provider_mode="recorded", evidence=(), norm_refs=(),
    )
    bare = CaptureSnapshot(origin=origin, content=content, section_code=None, data_class="test", crops=(), decision=decision)
    assert bare.earlier_comments == ()
    fact = _fact()
    carrying = CaptureSnapshot(
        origin=origin, content=content, section_code=None, data_class="test", crops=(), decision=decision, earlier_comments=(fact,)
    )
    assert carrying.earlier_comments == (fact,)
