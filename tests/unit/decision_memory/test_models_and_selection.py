"""`ADR-0027` phase M1: the memory's values, the content digest and the crop selection rule, with no database."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from auditmanager.decision_memory.public import (
    CROP_CAP,
    DESCRIPTION_MAX_CHARS,
    SELECTION_RULE_PAGE_IMAGES,
    CaptureSnapshot,
    CaseContent,
    CaseOrigin,
    CropRef,
    DecisionFact,
    EvidenceItem,
    NormRef,
    content_digest,
    select_page_image_crops,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import BlobId

NOW = datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc)
SHA = "a" * 64


def _blob(seed: str = "a") -> str:
    from auditmanager.storage.public import derive_blob_id

    return str(derive_blob_id(sha256=seed * 64, size=1234))


def _evidence(ordinal: int = 0, page: int = 1, **extra: object) -> EvidenceItem:
    return EvidenceItem(ordinal=ordinal, page_number=page, quote="Степень огнестойкости здания — II.", char_start=0,
                        char_end=34, **extra)  # type: ignore[arg-type]


def _content(**extra: object) -> CaseContent:
    values: dict[str, object] = dict(
        category="internal_contradiction", finding_text="Степень указана по-разному.",
        recommendation_text="Согласовать.", proposed_severity=None, required_value=None, stated_value=None,
        stage_id="text_analysis", analysis_profile_id="ap_01M5F21PBT7E8WRN3M61BDQFDD",
        prompt_bundle_id="pb_01M5F21PBT7E8WRN3M61BDQFDD", provider_mode="recorded",
        evidence=(_evidence(),), norm_refs=(),
    )
    values.update(extra)
    return CaseContent(**values)  # type: ignore[arg-type]


def _record(block: str, page: int, **extra: object) -> dict[str, object]:
    return {
        "portal_block_id": "blk_" + block * 32, "page_number": page, "bbox_norm": [0.1, 0.2, 0.5, 0.6],
        "blob_id": _blob(block), "sha256": SHA, "size_bytes": 1234, "width_px": 800, "height_px": 600, **extra,
    }


class TestTheContentDigest:
    def test_it_is_a_hex_sha256_and_stable(self) -> None:
        digest = content_digest(_content())
        assert len(digest) == 64 and int(digest, 16) >= 0
        assert content_digest(_content()) == digest

    @pytest.mark.parametrize("change", [
        {"finding_text": "Другой текст."},
        {"recommendation_text": "Иная рекомендация."},
        {"category": "explicit_placeholder"},
        {"proposed_severity": "critical"},
        {"stage_id": "other_stage"},
        {"provider_mode": "live"},
        {"evidence": (_evidence(page=2),)},
        {"evidence": ()},
        {"required_value": "A", "stated_value": "B"},
    ])
    def test_it_moves_with_every_field_of_the_observation(self, change: dict[str, object]) -> None:
        assert content_digest(_content(**change)) != content_digest(_content())

    def test_it_does_not_move_with_what_comes_from_artifacts(self) -> None:
        """A box is read from the block index, which a newer run may have replaced between two decisions on one observation."""
        boxed = _evidence(block_ref="b_000001", bbox=(1.0, 2.0, 3.0, 4.0), bbox_unit="pt", bbox_origin="top_left")
        unboxed = _evidence(block_ref="b_000001")
        assert content_digest(_content(evidence=(boxed,))) == content_digest(_content(evidence=(unboxed,)))

    def test_it_covers_the_normative_references(self) -> None:
        ref = NormRef(
            ordinal=1, norms_snapshot_id="ns_01M5F21PBT7E8WRN3M61BDQFDD", norm_document_id="ndoc_01M5F21PBT7E8WRN3M61BDQFDD",
            norm_paragraph_id="npar_01M5F21PBT7E8WRN3M61BDQFDD", designation="СП 1.2", clause_number="4.1", page_label=3,
            quote="Двадцать символов и более.", citation_state="verified",
        )
        assert content_digest(_content(norm_refs=(ref,))) != content_digest(_content())


class TestTheValuesRefuseWhatTheTablesRefuse:
    def test_a_box_comes_with_its_unit_and_origin(self) -> None:
        with pytest.raises(DomainError) as refused:
            _evidence(bbox=(1.0, 2.0, 3.0, 4.0))
        assert refused.value.code is ErrorCode.VALIDATION_FAILED

    def test_a_comment_is_not_a_captured_decision(self) -> None:
        with pytest.raises(DomainError):
            DecisionFact("dec_01M5F21PBT7E8WRN3M61BDQFDD", "comment", None, "x", None, "direct", NOW)

    def test_an_unknown_origin_kind_is_refused(self) -> None:
        with pytest.raises(DomainError):
            DecisionFact("dec_01M5F21PBT7E8WRN3M61BDQFDD", "accept", None, None, None, "invented", NOW)

    @pytest.mark.parametrize(("event", "verdict"), [("accept", "accepted"), ("reject", "rejected")])
    def test_the_verdict_follows_the_event(self, event: str, verdict: str) -> None:
        assert DecisionFact("dec_01M5F21PBT7E8WRN3M61BDQFDD", event, None, None, None, "direct", NOW).verdict == verdict

    def test_a_crop_names_a_well_formed_blob_and_stays_within_the_cap(self) -> None:
        with pytest.raises(Exception):
            CropRef(1, None, SELECTION_RULE_PAGE_IMAGES, 1, (0, 0, 1, 1), "not-a-blob", SHA, 1, 1, 1, "blk_" + "a" * 32)
        with pytest.raises(DomainError):
            CropRef(CROP_CAP + 1, None, SELECTION_RULE_PAGE_IMAGES, 1, (0, 0, 1, 1), _blob(), SHA, 1, 1, 1, "blk_" + "a" * 32)

    def test_a_snapshot_has_a_known_data_class_and_at_most_the_cap_of_crops(self) -> None:
        origin = CaseOrigin(
            "fobs_01M5F21PBT7E8WRN3M61BDQFDD", "fnd_01M5F21PBT7E8WRN3M61BDQFDD", "prj_01M5F21PBT7E8WRN3M61BDQFDD",
            "doc_01M5F21PBT7E8WRN3M61BDQFDD", "ver_01M5F21PBT7E8WRN3M61BDQFDD", "run_01M5F21PBT7E8WRN3M61BDQFDD",
        )
        decision = DecisionFact("dec_01M5F21PBT7E8WRN3M61BDQFDD", "accept", None, None, None, "direct", NOW)
        with pytest.raises(DomainError):
            CaptureSnapshot(origin, _content(), None, "production", (), decision)
        assert CaptureSnapshot(origin, _content(), None, "test", (), decision).data_class == "test"
        assert BlobId  # the identity type the crop references are made of


class TestSelectionRulePageImages1:
    def test_it_takes_the_crops_of_the_pages_the_evidence_names_in_manifest_order(self) -> None:
        records = [_record("a", 2), _record("b", 1), _record("c", 3), _record("d", 1)]
        chosen = select_page_image_crops([_evidence(0, 1), _evidence(1, 2)], records)
        assert [c.source_ref for c in chosen] == ["blk_" + "b" * 32, "blk_" + "d" * 32, "blk_" + "a" * 32]
        assert [c.ordinal for c in chosen] == [1, 2, 3]
        assert [c.evidence_ordinal for c in chosen] == [0, 0, 1]
        assert {c.selection_rule for c in chosen} == {SELECTION_RULE_PAGE_IMAGES}

    def test_a_crop_is_taken_once_even_when_two_evidence_items_share_its_page(self) -> None:
        chosen = select_page_image_crops([_evidence(0, 1), _evidence(1, 1)], [_record("a", 1)])
        assert [(c.source_ref, c.evidence_ordinal) for c in chosen] == [("blk_" + "a" * 32, 0)]

    def test_it_stops_at_the_cap(self) -> None:
        records = [_record(letter, 1) for letter in "abcdefg"]
        assert len(select_page_image_crops([_evidence(0, 1)], records)) == CROP_CAP == 4

    def test_a_page_without_a_crop_gives_none_and_says_nothing_else(self) -> None:
        assert select_page_image_crops([_evidence(0, 5)], [_record("a", 1)]) == ()
        assert select_page_image_crops([], [_record("a", 1)]) == ()
        assert select_page_image_crops([_evidence(0, 1)], []) == ()

    def test_it_carries_the_box_the_blob_and_the_description(self) -> None:
        (crop,) = select_page_image_crops([_evidence(0, 1)], [_record("a", 1, portal_description="Фасад здания")])
        assert crop.bbox == (0.1, 0.2, 0.5, 0.6) and crop.blob_id == _blob("a")
        assert (crop.width_px, crop.height_px, crop.size_bytes, crop.sha256) == (800, 600, 1234, SHA)
        assert crop.portal_description == "Фасад здания" and crop.kind == "portal_image_block"

    def test_a_long_description_is_cut_at_the_documented_width(self) -> None:
        (crop,) = select_page_image_crops([_evidence(0, 1)], [_record("a", 1, portal_description="я" * 5000)])
        assert crop.portal_description is not None and len(crop.portal_description) == DESCRIPTION_MAX_CHARS
