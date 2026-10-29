"""A nonbinding suggestion never guesses through ambiguous documents."""

from __future__ import annotations

from auditmanager.comparison.stage.suggestions import (
    StageDocument,
    StageSuggestion,
    suggest_stage_pairs,
)


def doc(uid: str, stage: str, section: str, designation: str) -> StageDocument:
    return StageDocument(uid, stage, section, designation)  # type: ignore[arg-type]


def test_unique_section_and_designation_propose_one_pair() -> None:
    proposals = suggest_stage_pairs(
        (
            doc("doc_old", "P", "АР", " A-01  Корпус 1 "),
            doc("doc_new", "R", "АР", "a-01 корпус 1"),
            doc("doc_other_section", "R", "КР", "a-01 корпус 1"),
        ),
        bound_document_uids=frozenset(),
    )
    assert len(proposals) == 1
    assert proposals[0].left_document_uid == "doc_old"
    assert proposals[0].right_document_uid == "doc_new"
    assert proposals[0].reason == "section_title_hint_exact"
    assert proposals[0].score == 0.75


def test_ambiguous_or_already_bound_documents_are_not_suggested() -> None:
    documents = (
        doc("doc_p1", "P", "AR", "A-01"),
        doc("doc_p2", "P", "AR", "A-01"),
        doc("doc_r1", "R", "AR", "A-01"),
        doc("doc_p3", "P", "AR", "B-01"),
        doc("doc_r3", "R", "AR", "B-01"),
    )
    assert suggest_stage_pairs(documents, bound_document_uids=frozenset()) == (
        StageSuggestion("doc_p3", "doc_r3", "section_title_hint_exact", 0.75),
    )
    assert suggest_stage_pairs(documents, bound_document_uids=frozenset({"doc_r3"})) == ()


def test_empty_designation_never_guesses_from_section_alone() -> None:
    assert suggest_stage_pairs(
        (doc("doc_p", "P", "AR", " "), doc("doc_r", "R", "AR", " ")),
        bound_document_uids=frozenset(),
    ) == ()


def test_two_confirmed_designations_keep_full_exact_confidence() -> None:
    assert suggest_stage_pairs(
        (
            StageDocument("doc_p", "P", "AR", "AR-01", "confirmed"),
            StageDocument("doc_r", "R", "AR", "ar-01", "confirmed"),
        ),
        bound_document_uids=frozenset(),
    ) == (StageSuggestion("doc_p", "doc_r", "section_designation_exact", 1.0),)
