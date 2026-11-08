"""`ADR-0027`, phase M1: a decision on a really published finding leaves a case, on a real database.

The findings here go through the grounding gate and the publication (the suite's ``published`` fixture), and the decisions through
``record_decision`` and ``append_decision_under_key``, with the composition root's own assembler registered as the ledger's port.
Only the published artifacts (the block index and the portal crop manifest) are replaced, by a recording double, because they live
in the object store; the box and crop mapping is proved in ``tests/unit/decision_memory`` and by the drill seed's real
``BlockAdapter``.

Shown: decide -> the case, its content, its evidence and its decision exist; a replay captures nothing new; a second decision on the
same observation adds a decision to the same case and reads no artifact; a comment is not captured; a carried and an imported
decision keep their ``origin_kind``; a capture that fails fails the decision; and the sweep captures what was decided before there
was a memory, once, and leaves a comment alone.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.bootstrap.adapters import MemoryCaptureAssembler, MemoryCaptureSweep
from auditmanager.decisions import append_decision_under_key, record_decision
from auditmanager.decisions.public import register_decision_recorded, registered_decision_recorded
from auditmanager.shared.errors import DomainError, ErrorCode


class _Geometry:
    """Stands for the object store: what the block index and the portal crop manifest would answer, and how often it was asked."""

    def __init__(self) -> None:
        self.boxes: dict[str, Any] = {}
        self.crops: tuple[dict[str, Any], ...] = ()
        self.box_reads = 0
        self.crop_reads = 0

    def evidence_boxes_in(self, session: Session, version_uid: str) -> dict[str, Any]:
        self.box_reads += 1
        return self.boxes

    def portal_crops_in(self, session: Session, version_uid: str) -> tuple[dict[str, Any], ...]:
        self.crop_reads += 1
        return self.crops


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


def _decide(session: Session, published: Any, event_type: str = "accept", **extra: Any) -> Any:
    options: dict[str, Any] = dict(
        finding_uid=published.finding_uid, finding_observation_id=published.finding_observation_id, event_type=event_type,
        comment="подтверждено по странице" if event_type != "comment" else "заметка", author_label="Петрова А.", author_user_uid=None,
    )
    options.update(extra)
    return record_decision(session, **options)


def test_a_decision_leaves_a_case_with_what_the_expert_saw_and_said(session: Session, published: Any, memory: SimpleNamespace) -> None:
    event = _decide(session, published)
    case = session.execute(text("SELECT * FROM decision_memory_case")).mappings().one()
    assert case["origin_observation_id"] == published.finding_observation_id
    assert case["origin_finding_uid"] == published.finding_uid
    assert (case["origin_project_uid"], case["origin_document_uid"], case["origin_version_uid"], case["origin_run_id"]) == (
        published.project_uid, published.document_uid, published.version_uid, published.run_id)
    assert case["category"] == "internal_contradiction" and case["data_class"] == "test"
    assert case["section_code"] is None and case["crop_state"] == "none_available"
    assert case["capture_version"] == "dm-capture/1" and len(case["content_sha256"]) == 64

    content = session.execute(text("SELECT * FROM decision_memory_content")).mappings().one()
    assert content["case_id"] == case["case_id"] and content["revision"] == 1
    assert content["finding_text"] == "Степень огнестойкости указана по-разному."
    assert content["recommendation_text"] == "Согласовать степень огнестойкости."
    assert (content["analysis_profile_id"], content["prompt_bundle_id"]) == (published.analysis_profile_id, published.prompt_bundle_id)
    assert content["provider_mode"] == "recorded" and content["stage_id"] == "text_analysis"

    evidence = session.execute(text("SELECT ordinal, page_number, quote, char_start, char_end, bbox_x0 FROM decision_memory_evidence ORDER BY ordinal")).all()
    assert [(row.ordinal, row.page_number, row.quote) for row in evidence] == [
        (0, 1, "Степень огнестойкости здания — II."), (1, 2, "Степень огнестойкости здания — III.")]
    assert all(row.bbox_x0 is None for row in evidence)      # the doubled gate never had a block index: no box, said as NULL
    assert _count(session, "decision_memory_norm_ref") == 0 and _count(session, "decision_memory_crop") == 0

    decision = session.execute(text("SELECT * FROM decision_memory_decision")).mappings().one()
    assert decision["case_id"] == case["case_id"] and decision["source_decision_id"] == event.decision_id
    assert (decision["event_type"], decision["verdict"], decision["origin_kind"]) == ("accept", "accepted", "direct")
    assert decision["author_user_uid"] is None and decision["decided_at"] == event.recorded_at
    assert session.execute(text("SELECT comment FROM decision_memory_decision_text")).scalar_one() == "подтверждено по странице"
    assert memory.geometry.crop_reads == 1 and memory.geometry.box_reads == 0   # no evidence names a block, so no index was read


def test_a_crop_and_a_box_the_artifacts_name_are_referenced_not_copied(session: Session, published: Any, memory: SimpleNamespace) -> None:
    from auditmanager.storage.public import derive_blob_id

    blob = str(derive_blob_id(sha256="b" * 64, size=4096))
    session.execute(text("INSERT INTO blob (blob_id) VALUES (:b)"), {"b": blob})
    memory.geometry.crops = (
        {"portal_block_id": "blk_" + "c" * 32, "page_number": 2, "bbox_norm": [0.1, 0.1, 0.9, 0.5], "blob_id": blob,
         "sha256": "b" * 64, "size_bytes": 4096, "width_px": 900, "height_px": 700, "portal_description": "Схема этажа"},
        {"portal_block_id": "blk_" + "d" * 32, "page_number": 9, "bbox_norm": [0.1, 0.1, 0.9, 0.5], "blob_id": blob,
         "sha256": "b" * 64, "size_bytes": 4096, "width_px": 900, "height_px": 700},
    )
    _decide(session, published)
    assert session.execute(text("SELECT crop_state FROM decision_memory_case")).scalar_one() == "referenced"
    crop = session.execute(text("SELECT * FROM decision_memory_crop")).mappings().one()
    assert (crop["blob_id"], crop["page_number"], crop["evidence_ordinal"], crop["crop_ordinal"]) == (blob, 2, 1, 1)
    assert crop["selection_rule"] == "page_images/1" and crop["portal_description"] == "Схема этажа"
    assert (crop["bbox_x0"], crop["bbox_y1"]) == (0.1, 0.5)
    assert _count(session, "blob", "blob_id = :b", b=blob) == 1          # the Blob is the same row: a binding, not a copy


def test_a_second_decision_on_the_same_observation_adds_a_decision_to_the_same_case(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    first = _decide(session, published, "accept")
    reads = (memory.geometry.box_reads, memory.geometry.crop_reads)
    second = _decide(session, published, "reject", comment="пересмотрено")
    assert _count(session, "decision_memory_case") == 1 and _count(session, "decision_memory_decision") == 2
    assert _count(session, "decision_memory_content") == 1 and _count(session, "decision_memory_evidence") == 2
    assert (memory.geometry.box_reads, memory.geometry.crop_reads) == reads    # a known case reads no artifact
    rows = session.execute(text("SELECT source_decision_id, verdict FROM decision_memory_decision ORDER BY captured_at")).all()
    assert [(r.source_decision_id, r.verdict) for r in rows] == [(first.decision_id, "accepted"), (second.decision_id, "rejected")]


def test_a_replay_under_the_same_key_captures_nothing_new(session: Session, published: Any, memory: SimpleNamespace) -> None:
    options = dict(
        finding_uid=published.finding_uid, finding_observation_id=published.finding_observation_id, event_type="accept",
        idempotency_key="memory-replay-1", author_label="Петрова А.", author_user_uid=None, comment="ок",
    )
    event, replayed = append_decision_under_key(session, **options)
    assert replayed is False
    again, replayed_again = append_decision_under_key(session, **options)
    assert replayed_again is True and again.decision_id == event.decision_id
    assert (_count(session, "decision_memory_case"), _count(session, "decision_memory_decision")) == (1, 1)


def test_a_comment_is_not_a_decision_and_is_not_captured(session: Session, published: Any, memory: SimpleNamespace) -> None:
    _decide(session, published, "comment")
    assert _count(session, "expert_decision_event") == 1
    assert (_count(session, "decision_memory_case"), _count(session, "decision_memory_decision")) == (0, 0)
    assert memory.geometry.crop_reads == 0                                       # nothing was even assembled


def test_a_carried_and_an_imported_decision_keep_their_origin(session: Session, published: Any, memory: SimpleNamespace) -> None:
    source = _decide(session, published, "accept")
    carried = record_decision(
        session, finding_uid=published.second_finding_uid, finding_observation_id=published.second_finding_observation_id,
        event_type="accept", comment=None, author_label="Петрова А.", author_user_uid=None, carried_from_decision_id=source.decision_id)
    imported = _decide(session, published, "reject", origin_kind="imported", comment="из книги")
    kinds = dict(session.execute(text("SELECT source_decision_id, origin_kind FROM decision_memory_decision")).all())
    assert kinds == {source.decision_id: "direct", carried.decision_id: "carried", imported.decision_id: "imported"}
    assert _count(session, "decision_memory_case") == 2
    with pytest.raises(DomainError) as refused:
        _decide(session, published, "reject", origin_kind="carried")           # carried without the decision it carries over
    assert refused.value.code is ErrorCode.VALIDATION_FAILED


def test_a_capture_that_fails_fails_the_decision_and_leaves_no_event(session: Session, published: Any, memory: SimpleNamespace) -> None:
    def broken(session: Session, event: Any, origin_kind: str) -> None:
        raise RuntimeError("the memory could not be written")

    register_decision_recorded(broken)
    savepoint = session.begin_nested()
    with pytest.raises(RuntimeError, match="could not be written"):
        _decide(session, published)
    savepoint.rollback()
    assert _count(session, "expert_decision_event") == 0 and _count(session, "decision_memory_case") == 0


def test_a_process_without_the_port_captures_nothing_and_the_sweep_repairs_it_once(session: Session, published: Any) -> None:
    register_decision_recorded(None)
    accepted = _decide(session, published, "accept")
    _decide(session, published, "comment")
    rejected = record_decision(
        session, finding_uid=published.second_finding_uid, finding_observation_id=published.second_finding_observation_id,
        event_type="reject", comment="другой объект", author_label="Петрова А.", author_user_uid=None)
    assert _count(session, "decision_memory_decision") == 0

    connection = session.get_bind()
    factory = lambda: Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)  # noqa: E731
    sweep = MemoryCaptureSweep(factory, MemoryCaptureAssembler(geometry=_Geometry()), batch=500)
    first = sweep.run_once()
    # at least these two: a lane's database may hold other, committed decisions, which the sweep captures as well
    assert first.captured >= 2
    captured = dict(session.execute(text("SELECT source_decision_id, verdict FROM decision_memory_decision")).all())
    assert captured[accepted.decision_id] == "accepted" and captured[rejected.decision_id] == "rejected"
    assert len(captured) == first.captured and _count(session, "decision_memory_case") == first.captured  # the comment is not among them
    assert _count(session, "decision_memory_decision", "source_decision_id IN (SELECT decision_id FROM expert_decision_event "
                                                       "WHERE event_type = 'comment')") == 0
    again = sweep.run_once()
    assert again.captured == 0                                                   # the anti-join is the state: nothing is done twice
    assert _count(session, "decision_memory_decision") == first.captured
