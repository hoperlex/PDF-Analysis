"""`F8-PUBLISH`: what a group of candidates is, and how the saved review is read into groups (ADR-0029 decision 7, plan-v5 section 4).

No database. Two halves:

* ``classify_group`` -- the rule of items 1 and 2 as one pure function: a group of blocks is ``drawing_discrepancy`` / ``block_analysis``;
  a group that also stands on a text or another source is mixed, ``cross_source`` / ``finding_merge``; a group wholly of primary texts is
  not published (the text path already did it); a group that stands on no block has nothing to prove;
* ``read_candidate_groups`` -- the saved ``analysis.extended_review`` document as groups of the strict consolidation: the evidence of a
  member is the blocks of its own sources with the page and crop digest the review saved (never a box); a primary-text source becomes the
  ordinal of the text observation it restates; a document of another run, or one whose review did not complete, is not read as candidates.

Each rule is proved by breaking one thing in a case that passes, so a reader that published everything (or nothing) would fail here.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.findings.artifacts import BlockEvidenceItem
from auditmanager.findings.publication import (
    CATEGORY_CROSS_SOURCE,
    CATEGORY_DRAWING_DISCREPANCY,
    RECOMMENDATION_CHECK_THE_SOURCE,
    SKIP_NO_BLOCK_EVIDENCE,
    SKIP_PRIMARY_TEXT_ONLY,
    STAGE_BLOCK_ANALYSIS,
    STAGE_FINDING_MERGE,
    CandidateGroup,
    CandidateMember,
    classify_group,
)
from auditmanager.runs.extended_review import read_candidate_groups
from auditmanager.shared.errors import DomainError, ErrorCode

RUN = "run_01M2545JSD15ETSNNV904X991J"
VERSION = "ver_01M2545JSD15ETSNNV904X991J"
BLK_A = "blk_" + "a" * 32
BLK_B = "blk_" + "b" * 32
BLK_C = "blk_" + "c" * 32
CROP_A = "a1" * 32
CROP_B = "b2" * 32
CROP_C = "c3" * 32


def _item(block: str = BLK_A, crop: str = CROP_A, page: int = 2, ordinal: int = 0) -> BlockEvidenceItem:
    return BlockEvidenceItem(evidence_ordinal=ordinal, page_number=page, portal_block_id=block, crop_sha256=crop)


def _member(ref: str = "xobs_1", **extra: Any) -> CandidateMember:
    values: dict[str, Any] = {"extended_observation_ref": ref, "finding_text": "Размер не совпадает с планом.", "block_evidence": (_item(),)}
    values.update(extra)
    return CandidateMember(**values)


def _group(*members: CandidateMember, group_id: str = "xgrp_1") -> CandidateGroup:
    return CandidateGroup(group_id=group_id, members=members or (_member(),))


# --------------------------------------------------------------------------------------------
# The rule
# --------------------------------------------------------------------------------------------


class TestAGroupOfBlocksIsADrawingDiscrepancy:
    def test_the_control(self) -> None:
        kind = classify_group(_group(_member("xobs_1"), _member("xobs_2")))
        assert kind.publishable and not kind.mixed and kind.skip_reason is None
        assert (kind.category, kind.stage_id) == (CATEGORY_DRAWING_DISCREPANCY, STAGE_BLOCK_ANALYSIS)

    def test_the_same_window_stays_block_analysis_and_two_windows_are_a_merge(self) -> None:
        one = classify_group(_group(_member("xobs_1", window_id="w0"), _member("xobs_2", window_id="w0")))
        two = classify_group(_group(_member("xobs_1", window_id="w0"), _member("xobs_2", window_id="w1")))
        assert one.stage_id == STAGE_BLOCK_ANALYSIS
        assert two.stage_id == STAGE_FINDING_MERGE
        assert two.category == CATEGORY_DRAWING_DISCREPANCY, "a merge across windows is not a mixed group"

    def test_a_candidate_of_the_cross_window_pass_makes_a_merge(self) -> None:
        kind = classify_group(_group(_member("xobs_1"), _member("xobs_2", cross_window=True)))
        assert kind.stage_id == STAGE_FINDING_MERGE and kind.category == CATEGORY_DRAWING_DISCREPANCY


class TestAMixedGroupIsCrossSource:
    @pytest.mark.parametrize(
        "extra",
        [
            {"primary_text_ordinals": (0,)},
            {"primary_text_unlinked": 1},
            {"other_source_count": 1},
        ],
        ids=["a primary text it can name", "a primary text it cannot name", "another source"],
    )
    def test_blocks_and_any_other_source_make_one_category_and_a_merge(self, extra: dict[str, Any]) -> None:
        kind = classify_group(_group(_member("xobs_1", **extra)))
        assert kind.publishable and kind.mixed
        assert (kind.category, kind.stage_id) == (CATEGORY_CROSS_SOURCE, STAGE_FINDING_MERGE)

    def test_the_other_source_may_belong_to_another_member_of_the_group(self) -> None:
        blocks = _member("xobs_1")
        text_member = _member("xobs_2", block_evidence=(), primary_text_ordinals=(0,))
        kind = classify_group(_group(blocks, text_member))
        assert kind.mixed and kind.category == CATEGORY_CROSS_SOURCE


class TestAGroupThatStandsOnNoBlockIsNotPublished:
    def test_a_group_wholly_of_primary_texts_is_the_text_paths_own(self) -> None:
        kind = classify_group(_group(_member("xobs_1", block_evidence=(), primary_text_ordinals=(0,))))
        assert not kind.publishable and kind.skip_reason == SKIP_PRIMARY_TEXT_ONLY

    def test_an_unnamed_primary_text_is_still_never_published_twice(self) -> None:
        kind = classify_group(_group(_member("xobs_1", block_evidence=(), primary_text_unlinked=2)))
        assert not kind.publishable and kind.skip_reason == SKIP_PRIMARY_TEXT_ONLY

    def test_the_control_one_block_makes_the_same_group_publishable(self) -> None:
        kind = classify_group(_group(_member("xobs_1", primary_text_ordinals=(0,))))
        assert kind.publishable

    def test_a_group_of_a_primary_text_and_another_source_has_no_block_to_prove(self) -> None:
        kind = classify_group(_group(_member("xobs_1", block_evidence=(), primary_text_ordinals=(0,), other_source_count=1)))
        assert not kind.publishable and kind.skip_reason == SKIP_NO_BLOCK_EVIDENCE

    def test_a_group_of_other_sources_only_has_no_block_to_prove(self) -> None:
        kind = classify_group(_group(_member("xobs_1", block_evidence=(), other_source_count=3)))
        assert not kind.publishable and kind.skip_reason == SKIP_NO_BLOCK_EVIDENCE


class TestAMemberIsWhatTheColumnsCanHold:
    def test_the_recommendation_is_the_correctors_or_the_stock_phrase(self) -> None:
        assert _member().recommendation_text == RECOMMENDATION_CHECK_THE_SOURCE
        assert _member(refined_recommendation="Уточнить размер по плану.").recommendation_text == "Уточнить размер по плану."

    @pytest.mark.parametrize(
        "extra",
        [
            {"extended_observation_ref": ""},
            {"extended_observation_ref": "x" * 129},
            {"finding_text": "   "},
            {"finding_text": "я" * 4001},
            {"refined_recommendation": " "},
            {"refined_recommendation": "я" * 4001},
            {"other_source_count": -1},
        ],
    )
    def test_a_value_the_database_would_refuse_is_refused_here(self, extra: dict[str, Any]) -> None:
        with pytest.raises(DomainError) as caught:
            _member(**extra)
        assert caught.value.code is ErrorCode.ANALYSIS_INPUT_INVALID

    def test_a_group_has_an_identity_and_a_member(self) -> None:
        with pytest.raises(DomainError):
            CandidateGroup(group_id="xgrp_1", members=())
        with pytest.raises(DomainError):
            CandidateGroup(group_id="", members=(_member(),))


# --------------------------------------------------------------------------------------------
# The saved review, read as groups
# --------------------------------------------------------------------------------------------


def _sources() -> list[dict[str, Any]]:
    return [
        {"source_id": BLK_A, "kind": "image", "page_number": 2, "bbox_norm": [0.1, 0.2, 0.6, 0.7], "crop_sha256": CROP_A, "blob_id": "blob_x"},
        {"source_id": BLK_B, "kind": "image", "page_number": 2, "bbox_norm": [0.2, 0.2, 0.4, 0.3], "crop_sha256": CROP_B, "blob_id": "blob_x"},
        {"source_id": BLK_C, "kind": "image", "page_number": 3, "bbox_norm": [0.5, 0.5, 0.9, 0.9], "crop_sha256": CROP_C, "blob_id": "blob_x"},
        {"source_id": "text:0", "kind": "text", "page_number": 1, "quote": "Степень огнестойкости II"},
        {"source_id": "native_" + "e" * 32, "kind": "image", "source_type": "native_page", "page_number": 1, "crop_sha256": "e" * 64},
    ]


def _candidate(ref: str, source_ids: list[str], *, title: str = "Размер", description: str = "Размер не совпадает с планом.", **extra: Any) -> dict[str, Any]:
    return {"observation_id": ref, "title": title, "description": description, "source_ids": source_ids, "norm_queries": [], **extra}


def _document(observations: list[dict[str, Any]], *, status: str = "completed", **result: Any) -> dict[str, Any]:
    return {
        "artifact_role": "analysis.extended_review",
        "artifact_version": "1.0.0",
        "version_uid": VERSION,
        "run_id": RUN,
        "status": status,
        "result": {"workflow_version": "extended-review-v2", "version_uid": VERSION, "sources": _sources(), "observations": observations, **result},
    }


TEXT_OBSERVATIONS = {"observations": [{"observation_ordinal": 7, "category": "dimensions"}]}


def _read(document: dict[str, Any], text_observations: Any = TEXT_OBSERVATIONS):
    return read_candidate_groups(document, run_id=RUN, version_uid=VERSION, text_observations=text_observations)


class TestTheSavedReviewIsReadAsGroups:
    def test_two_candidates_of_one_wording_that_share_a_block_are_one_group_in_the_saved_order(self) -> None:
        groups, unread = _read(_document([_candidate("xobs_1", [BLK_A]), _candidate("xobs_2", [BLK_A, BLK_B])]))
        assert unread == ()
        (group,) = groups
        assert [member.extended_observation_ref for member in group.members] == ["xobs_1", "xobs_2"]
        assert group.group_id.startswith("xgrp_")

    def test_candidates_of_other_wording_or_other_sources_are_groups_of_their_own(self) -> None:
        groups, _ = _read(_document([
            _candidate("xobs_1", [BLK_A]),
            _candidate("xobs_2", [BLK_B]),                                   # the same words, another source
            _candidate("xobs_3", [BLK_A], description="Высота не совпадает."),   # the same source, other words
        ]))
        assert [[m.extended_observation_ref for m in g.members] for g in groups] == [["xobs_1"], ["xobs_2"], ["xobs_3"]]

    def test_the_evidence_of_a_member_is_the_blocks_of_its_sources_with_the_page_and_the_digest_the_review_saved(self) -> None:
        (group,), _ = _read(_document([_candidate("xobs_1", [BLK_B, BLK_A, BLK_B])]))
        (member,) = group.members
        assert [(e.evidence_ordinal, e.portal_block_id, e.page_number, e.crop_sha256, e.recognised_quote) for e in member.block_evidence] == [
            (0, BLK_B, 2, CROP_B, None),
            (1, BLK_A, 2, CROP_A, None),
        ], "in the candidate's own order, each block once, and no quote: the review's quotes are the model's, not recognised text"
        assert member.other_source_count == 0 and member.primary_text_ordinals == ()

    def test_a_native_page_and_a_block_the_review_does_not_hold_are_other_sources_never_evidence(self) -> None:
        unknown = "blk_" + "9" * 32
        (group,), _ = _read(_document([_candidate("xobs_1", [BLK_A, "native_" + "e" * 32, unknown])]))
        (member,) = group.members
        assert [e.portal_block_id for e in member.block_evidence] == [BLK_A]
        assert member.other_source_count == 2
        assert classify_group(group).category == CATEGORY_CROSS_SOURCE

    def test_a_block_id_that_is_not_an_image_source_is_not_evidence(self) -> None:
        sources = _sources()
        sources[0] = {**sources[0], "kind": "text"}
        (group,), _ = _read(_document([_candidate("xobs_1", [BLK_A])], sources=sources))
        (member,) = group.members
        assert member.block_evidence == () and member.other_source_count == 1

    def test_a_source_saved_under_two_shapes_is_not_evidence(self) -> None:
        # a window's own row of the block differs from the result's: nothing says which is true, so neither is taken as proof
        window = {"sources": [{**_sources()[0], "crop_sha256": "f" * 64}]}
        (group,), _ = _read(_document([_candidate("xobs_1", [BLK_A])], windows=[window]))
        (member,) = group.members
        assert member.block_evidence == ()

    def test_a_primary_text_source_names_the_text_observation_it_restates(self) -> None:
        (group,), _ = _read(_document([_candidate("xobs_1", [BLK_C, "text:0"])]))
        (member,) = group.members
        assert member.primary_text_ordinals == (7,) and member.primary_text_unlinked == 0
        assert classify_group(group).mixed

    def test_a_primary_text_source_it_cannot_name_is_still_a_primary_source(self) -> None:
        (group,), _ = _read(_document([_candidate("xobs_1", [BLK_C, "text:0"])]), text_observations=None)
        (member,) = group.members
        assert member.primary_text_ordinals == () and member.primary_text_unlinked == 1

    def test_a_plan_v3_primary_text_source_is_named_through_the_candidate_that_carries_its_key(self) -> None:
        key = "0123456789abcdef01234567"
        sources = [*_sources(), {"source_id": "primary_text_" + key, "kind": "text", "source_type": "primary_text_proposal", "page_number": 1}]
        primary = _candidate("xobs_p", ["primary_text_" + key], title="dimensions", description="Высота 3 м.",
                             primary_observation_key=key, original_primary_observation={"observation_ordinal": 4, "category": "dimensions"})
        (group, text_group), _ = _read(_document([_candidate("xobs_1", [BLK_A, "primary_text_" + key]), primary], sources=sources),
                                       text_observations=None)
        assert group.members[0].primary_text_ordinals == (4,)
        assert classify_group(text_group).skip_reason == SKIP_PRIMARY_TEXT_ONLY, "the primary candidate itself is never published twice"

    def test_the_correctors_revision_is_the_recommendation_and_a_request_for_context_is_not(self) -> None:
        revised = {"action": "propose_revision", "candidate": {"description": "Размер не совпадает с планом. Уточнить по стр. 2."}}
        asked = {"action": "needs_context", "candidate": None}
        (a, b), _ = _read(_document([
            _candidate("xobs_1", [BLK_A], correction=revised),
            _candidate("xobs_2", [BLK_B], correction=asked),
        ]))
        assert a.members[0].recommendation_text == "Размер не совпадает с планом. Уточнить по стр. 2."
        assert b.members[0].recommendation_text == RECOMMENDATION_CHECK_THE_SOURCE

    def test_the_text_of_a_member_is_the_title_over_the_description(self) -> None:
        (group,), _ = _read(_document([_candidate("xobs_1", [BLK_A], title="Размер", description="Не совпадает с планом.")]))
        assert group.members[0].finding_text == "Размер\n\nНе совпадает с планом."

    def test_a_candidate_of_the_global_cross_window_pass_says_so(self) -> None:
        (group,), _ = _read(_document([_candidate("xobs_1", [BLK_A], window_id="global-cross-window", origin_scope="global_cross_window")]))
        assert group.members[0].cross_window and classify_group(group).stage_id == STAGE_FINDING_MERGE


class TestTheReviewIsReadOnlyWhenItIsTheRuns:
    def test_a_review_that_did_not_complete_is_not_candidates(self) -> None:
        document = _document([_candidate("xobs_1", [BLK_A])])
        assert _read(document)[0], "the control: the same review, completed, is read"
        for status in ("failed", "unavailable", "running"):
            groups, unread = _read({**document, "status": status})
            assert groups == () and unread == ("extended_review_not_complete",)

    def test_a_partial_review_is_read(self) -> None:
        groups, _ = _read(_document([_candidate("xobs_1", [BLK_A])], status="partial"))
        assert len(groups) == 1

    @pytest.mark.parametrize("change", [{"run_id": "run_01M2545JSD15ETSNNV904X991K"}, {"version_uid": "ver_01M2545JSD15ETSNNV904X991K"},
                                        {"artifact_role": "analysis.text_observations"}, {"result": None}])
    def test_a_document_of_another_run_version_or_role_is_corruption(self, change: dict[str, Any]) -> None:
        with pytest.raises(DomainError) as caught:
            _read({**_document([_candidate("xobs_1", [BLK_A])]), **change})
        assert caught.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR

    def test_saved_candidates_that_cannot_be_consolidated_are_said_not_dropped(self) -> None:
        broken = {"observation_id": "xobs_2", "title": 5, "description": "x", "source_ids": [BLK_A]}
        groups, unread = _read(_document([_candidate("xobs_1", [BLK_A]), broken]))
        assert groups == () and unread == ("consolidation_unavailable",)

    def test_a_candidate_with_no_identity_or_words_is_left_out_and_counted(self) -> None:
        nameless = _candidate("", [BLK_A], description="Нет имени.")
        wordless = _candidate("xobs_3", [BLK_B], title="", description="")
        groups, unread = _read(_document([nameless, _candidate("xobs_2", [BLK_A]), wordless]))
        assert [[m.extended_observation_ref for m in g.members] for g in groups] == [["xobs_2"]]
        assert unread.count("candidate_invalid") == 2

    def test_the_groups_the_saved_result_carries_are_used_as_they_are(self) -> None:
        document = _document([_candidate("xobs_1", [BLK_A])])
        computed, _ = _read(document)
        saved = {
            "consolidation": {"version": "strict-cross-window-v1", "complete": True},
            "consolidated_observations": [{"group_id": "xgrp_saved", "origin_records": [{"raw_index": 0}]}],
        }
        used, _ = _read({**document, "result": {**document["result"], **saved}})
        assert computed[0].group_id != "xgrp_saved" and used[0].group_id == "xgrp_saved"
