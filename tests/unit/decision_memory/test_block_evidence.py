"""`F8-PUBLISH`, memory side: `dm-capture/2` -- the block evidence of a candidate case, its digest, and the crop taken by block.

No database. The rows themselves (``decision_memory_block_evidence``) are written and read back in
``tests/integration/findings/test_candidate_publication.py``, which captures a really published candidate finding.

Shown: a case without block evidence is what it always was (``dm-capture/1`` and the digest pinned below from the code before this change);
block evidence moves the digest and the version; the box does not move the digest (it is geometry, like the text evidence's); a block value the
table would refuse is refused here; and the crop of a block is the record whose block and digest are the evidence's, never a neighbour's.
"""

from __future__ import annotations

import pytest

from auditmanager.decision_memory.public import (
    CAPTURE_VERSION,
    CAPTURE_VERSION_BLOCK_EVIDENCE,
    CROP_CAP,
    SELECTION_RULE_BLOCK_CROP,
    SELECTION_RULE_PAGE_IMAGES,
    BlockEvidenceFact,
    CaseContent,
    EvidenceItem,
    capture_version_of,
    content_digest,
    select_block_crops,
    select_case_crops,
)
from auditmanager.shared.errors import DomainError

#: The digest of ``_content()`` below, computed by the code as it was before block evidence existed (``9fee8d1da``). A case that has none must
#: keep it: a stored case compares its digest with the one a later decision computes, and a changed body would read as a conflict.
DIGEST_BEFORE_BLOCK_EVIDENCE = "85330c54181cabd21ab35cd2b35cb70af91eee951ca5d09b564f8a2d4551e156"
SHA = "a" * 64


def _blob(seed: str = "a") -> str:
    from auditmanager.storage.public import derive_blob_id

    return str(derive_blob_id(sha256=seed * 64, size=1234))


def _content(**extra: object) -> CaseContent:
    values: dict[str, object] = dict(
        category="internal_contradiction", finding_text="Степень указана по-разному.",
        recommendation_text="Согласовать.", proposed_severity=None, required_value=None, stated_value=None,
        stage_id="text_analysis", analysis_profile_id="ap_01M5F21PBT7E8WRN3M61BDQFDD",
        prompt_bundle_id="pb_01M5F21PBT7E8WRN3M61BDQFDD", provider_mode="recorded",
        evidence=(EvidenceItem(ordinal=0, page_number=1, quote="Степень огнестойкости здания — II.", char_start=0, char_end=34),),
        norm_refs=(),
    )
    values.update(extra)
    return CaseContent(**values)  # type: ignore[arg-type]


def _fact(block: str = "a", ordinal: int = 0, **extra: object) -> BlockEvidenceFact:
    values: dict[str, object] = dict(ordinal=ordinal, page_number=2, portal_block_id="blk_" + block * 32, bbox=(0.1, 0.2, 0.6, 0.7), crop_sha256=SHA)
    values.update(extra)
    return BlockEvidenceFact(**values)  # type: ignore[arg-type]


def _record(block: str, page: int = 2, sha: str = SHA, **extra: object) -> dict[str, object]:
    return {
        "portal_block_id": "blk_" + block * 32, "page_number": page, "bbox_norm": [0.1, 0.2, 0.5, 0.6], "blob_id": _blob(block),
        "sha256": sha, "size_bytes": 1234, "width_px": 800, "height_px": 600, **extra,
    }


class TestACaseWithoutBlockEvidenceIsWhatItAlwaysWas:
    def test_its_digest_is_the_one_the_code_computed_before(self) -> None:
        assert content_digest(_content()) == DIGEST_BEFORE_BLOCK_EVIDENCE

    def test_it_is_dm_capture_1(self) -> None:
        assert capture_version_of(_content()) == CAPTURE_VERSION == "dm-capture/1"

    def test_block_evidence_is_empty_by_default(self) -> None:
        assert _content().block_evidence == ()


class TestBlockEvidenceMakesTheCaseDmCapture2:
    def test_the_version_follows_the_evidence(self) -> None:
        with_blocks = _content(evidence=(), block_evidence=(_fact(),))
        assert capture_version_of(with_blocks) == CAPTURE_VERSION_BLOCK_EVIDENCE == "dm-capture/2"

    def test_the_digest_moves_with_each_field_of_a_block(self) -> None:
        base = content_digest(_content(evidence=(), block_evidence=(_fact(),)))
        assert base != DIGEST_BEFORE_BLOCK_EVIDENCE
        for change in (
            {"ordinal": 1}, {"page_number": 3}, {"block": "b"}, {"crop_sha256": "b" * 64}, {"recognised_quote": "3000 мм"},
        ):
            assert content_digest(_content(evidence=(), block_evidence=(_fact(**change),))) != base, change

    def test_the_digest_moves_with_the_number_and_order_of_blocks(self) -> None:
        one = content_digest(_content(evidence=(), block_evidence=(_fact("a", 0),)))
        two = content_digest(_content(evidence=(), block_evidence=(_fact("a", 0), _fact("b", 1))))
        swapped = content_digest(_content(evidence=(), block_evidence=(_fact("b", 1), _fact("a", 0))))
        assert len({one, two, swapped}) == 3

    def test_the_box_is_geometry_and_does_not_move_the_digest(self) -> None:
        a = content_digest(_content(evidence=(), block_evidence=(_fact(bbox=(0.1, 0.2, 0.6, 0.7)),)))
        b = content_digest(_content(evidence=(), block_evidence=(_fact(bbox=(0.0, 0.0, 1.0, 1.0)),)))
        assert a == b

    def test_it_is_stable(self) -> None:
        content = _content(evidence=(), block_evidence=(_fact(),))
        assert content_digest(content) == content_digest(_content(evidence=(), block_evidence=(_fact(),)))


class TestABlockTheTableWouldRefuseIsRefusedHere:
    def test_the_control(self) -> None:
        assert _fact().portal_block_id == "blk_" + "a" * 32

    @pytest.mark.parametrize(
        "change",
        [
            {"ordinal": -1}, {"page_number": 0}, {"portal_block_id": "b_000001"}, {"portal_block_id": "blk_" + "A" * 32},
            {"crop_sha256": "short"}, {"bbox": (0.5, 0.2, 0.5, 0.7)}, {"bbox": (0.1, 0.7, 0.6, 0.2)}, {"bbox": (-0.1, 0.2, 0.6, 0.7)},
            {"bbox": (0.1, 0.2, 1.5, 0.7)}, {"recognised_quote": ""}, {"recognised_quote": "я" * 2001},
        ],
    )
    def test_each_value_the_check_constraints_refuse(self, change: dict[str, object]) -> None:
        with pytest.raises(DomainError):
            _fact(**change)

    def test_the_longest_quote_the_column_holds_is_taken(self) -> None:
        assert _fact(recognised_quote="я" * 2000).recognised_quote == "я" * 2000


class TestTheCropIsTakenByBlock:
    def test_each_block_takes_the_record_of_its_own_block_and_digest(self) -> None:
        records = [_record("c", page=3, sha="c" * 64), _record("a", sha=SHA), _record("b", sha="b" * 64)]
        facts = (_fact("a", 0), _fact("b", 1, crop_sha256="b" * 64))
        crops = select_block_crops(facts, records)
        assert [(c.source_ref, c.evidence_ordinal, c.ordinal, c.selection_rule) for c in crops] == [
            ("blk_" + "a" * 32, 0, 1, SELECTION_RULE_BLOCK_CROP),
            ("blk_" + "b" * 32, 1, 2, SELECTION_RULE_BLOCK_CROP),
        ]
        assert crops[0].page_number == 2 and crops[0].bbox == (0.1, 0.2, 0.5, 0.6) and crops[0].blob_id == _blob("a")

    def test_the_page_of_a_block_is_not_enough_a_neighbour_on_the_same_page_is_not_taken(self) -> None:
        # page_images/1 would take every image crop of the page; block_crop/1 takes the named block only
        records = [_record("b", page=2), _record("a", page=2)]
        by_page = select_case_crops((EvidenceItem(ordinal=0, page_number=2, quote="x", char_start=0, char_end=1),), (), records)
        by_block = select_case_crops((), (_fact("a"),), records)
        assert [c.source_ref[4] for c in by_page] == ["b", "a"] and {c.selection_rule for c in by_page} == {SELECTION_RULE_PAGE_IMAGES}
        assert [c.source_ref[4] for c in by_block] == ["a"] and {c.selection_rule for c in by_block} == {SELECTION_RULE_BLOCK_CROP}

    def test_a_record_whose_digest_is_not_the_one_the_evidence_recorded_is_not_substituted(self) -> None:
        records = [_record("a", sha="f" * 64)]
        assert select_block_crops((_fact("a", crop_sha256=SHA),), records) == ()
        assert len(select_block_crops((_fact("a", crop_sha256="f" * 64),), records)) == 1, "the control: the same record with its own digest is taken"

    def test_a_block_is_taken_once_and_at_most_the_cap(self) -> None:
        letters = "abcdef"
        records = [_record(letter) for letter in letters]
        facts = (_fact("a", 0), _fact("a", 1)) + tuple(_fact(letter, 2 + n) for n, letter in enumerate(letters[1:]))
        crops = select_block_crops(facts, records)
        assert [c.source_ref[4] for c in crops] == list("abcd")[:CROP_CAP] and len(crops) == CROP_CAP

    def test_the_evidence_is_read_in_its_own_order_not_the_given_one(self) -> None:
        records = [_record("a"), _record("b")]
        crops = select_block_crops((_fact("b", 1), _fact("a", 0)), records)
        assert [c.source_ref[4] for c in crops] == ["a", "b"]

    def test_a_long_portal_description_is_cut_as_in_the_other_rule(self) -> None:
        (crop,) = select_block_crops((_fact("a"),), [_record("a", portal_description="я" * 5000)])
        assert crop.portal_description is not None and len(crop.portal_description) == 4000

    def test_a_case_without_block_evidence_takes_the_page_images_exactly_as_before(self) -> None:
        records = [_record("a", page=2)]
        evidence = (EvidenceItem(ordinal=0, page_number=2, quote="x", char_start=0, char_end=1),)
        assert select_case_crops(evidence, (), records)[0].selection_rule == SELECTION_RULE_PAGE_IMAGES
