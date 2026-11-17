"""A nonbinding suggestion never guesses through ambiguous documents."""

from __future__ import annotations

from auditmanager.comparison.stage.suggestions import (
    StageDocument,
    StageSuggestion,
    UnpairedCounts,
    count_unpaired,
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


# --- how many documents have no pair (`UIP-S16-02`) --------------------------------------------------------------------------


def test_unpaired_counts_are_the_documents_no_confirmed_pair_binds_by_stage() -> None:
    classified = (("doc_p1", "P"), ("doc_p2", "P"), ("doc_p3", "P"), ("doc_r1", "R"), ("doc_r2", "R"))
    assert count_unpaired(classified, bound_document_uids=frozenset()) == UnpairedCounts(stage_p=3, stage_r=2)
    assert count_unpaired(classified, bound_document_uids=frozenset({"doc_p1", "doc_r1"})) == UnpairedCounts(stage_p=2, stage_r=1)
    assert count_unpaired(
        classified, bound_document_uids=frozenset({"doc_p1", "doc_p2", "doc_p3", "doc_r1", "doc_r2"}),
    ) == UnpairedCounts(stage_p=0, stage_r=0)


def test_a_document_nobody_could_suggest_a_partner_for_is_still_without_a_pair() -> None:
    documents = (
        doc("doc_p1", "P", "AR", "A-01"),
        doc("doc_p2", "P", "AR", "A-01"),  # two П with one designation: ambiguous
        doc("doc_r1", "R", "AR", "A-01"),
        doc("doc_p3", "P", "AR", " "),  # no designation at all
    )
    assert suggest_stage_pairs(documents, bound_document_uids=frozenset()) == (), "nothing here can be suggested"
    classified = tuple((document.document_uid, document.stage) for document in documents)
    assert count_unpaired(classified, bound_document_uids=frozenset()) == UnpairedCounts(stage_p=3, stage_r=1)


def test_a_document_listed_twice_counts_once_a_bound_one_never_and_an_unknown_stage_for_neither() -> None:
    assert count_unpaired(
        (("doc_a", "P"), ("doc_a", "P"), ("doc_b", "R"), ("doc_b", "R"), ("doc_x", "X")), bound_document_uids=frozenset(),
    ) == UnpairedCounts(stage_p=1, stage_r=1)
    assert count_unpaired(
        (("doc_a", "P"), ("doc_a", "P")), bound_document_uids=frozenset({"doc_a"}),
    ) == UnpairedCounts(stage_p=0, stage_r=0)
    assert count_unpaired((), bound_document_uids=frozenset()) == UnpairedCounts(stage_p=0, stage_r=0)
