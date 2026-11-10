"""`F8-GATE`: gate v2, a block as evidence, admitted only when verified (ADR-0029 decision 7).

A block link proves a place, not a content, so the gate proves the place and the crop on record and
leaves the claim to the expert. Every check here is built by breaking one thing in a block that
genuinely passes, and each test first shows that the unbroken block passes (the control), so a gate
that refused everything would fail it.

The tests are in four groups:

* the verdicts of ``check_block_evidence`` / ``run_block_gate``: a foreign ``blk_``, a crop whose digest
  differs, a quote that is not verbatim in the recognised text of that block, and what is not refused;
* the views over the run's saved documents (the version of the run, the shape, the empty view);
* the text gate is unchanged: a text observation is judged as before and is not judged by block records;
* the executor's read of the inputs (a ``text_only`` run reads none, a ``one_list`` run reads its own),
  and the vocabulary the gate and the database agree on (the last group runs on PostgreSQL).
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ROLE_BLOCK_INDEX,
    ROLE_PAGE_CROPS,
    ROLE_PORTAL_BLOCKS,
    ROLE_RECOGNISED_TEXT,
    ROLE_TEXT_LAYER,
    publish_artifact,
)
from auditmanager.findings import (
    UNGROUNDED_REASONS,
    BlockIndex,
    ObservationSet,
    TextLayer,
    UngroundedReason,
    run_grounding_gate,
)
from auditmanager.findings.artifacts import (
    GROUNDING_PORTAL_BLOCK,
    GROUNDING_TEXT_SPAN,
    MAX_BLOCK_QUOTE_CHARS,
    MAX_EXTENDED_OBSERVATION_REF_CHARS,
    PAGE_CROPS_ROLE,
    PORTAL_BLOCKS_ROLE,
    RECOGNISED_TEXT_ROLE,
    BlockEvidenceItem,
    BlockGateInputs,
    BlockObservation,
    CropManifest,
    PortalBlockGeometry,
    RecognisedText,
)
from auditmanager.findings.grounding import (
    BlockGateResult,
    check_block_evidence,
    run_block_gate,
)
from auditmanager.runs import executor as executor_module
from auditmanager.runs.executor import _publication_mode, _read_gate_inputs, _StageOutputs
from auditmanager.shared.db import nested_transaction
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import FindingObservationId
from auditmanager.storage.public import derive_blob_id

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MIGRATION_0064 = REPOSITORY_ROOT / "db" / "migrations" / "versions" / "20261110_0064_precedents_seal.py"

VERSION = "ver_01M2545JSD15ETSNNV904X991J"
OTHER_VERSION = "ver_01M2545JSD15ETSNNV904X991K"

#: Block ids are the portal's: ``blk_`` and 32 lowercase hexadecimal digits.
IMAGE_BLOCK = "blk_" + "1" * 32  # an IMAGE block of page 2: a crop, a portal description, no recognised text
TEXT_BLOCK = "blk_" + "2" * 32  # a block of page 3 with recognised text; given a crop record in these fixtures
OTHER_TEXT_BLOCK = "blk_" + "3" * 32  # a second block of page 3 with other recognised text
FOREIGN_BLOCK = "blk_" + "4" * 32  # a block of ANOTHER version's geometry

IMAGE_CROP = "a1" * 32
TEXT_CROP = "b2" * 32
OTHER_TEXT_CROP = "c3" * 32
FOREIGN_CROP = "d4" * 32

TEXT_OF_BLOCK = "Высота помещения: 3,0 м.\n- площадь 24,5 м2"
TEXT_OF_OTHER_BLOCK = "Класс бетона B25, арматура A500C"
DESCRIPTION_OF_IMAGE = "План этажа подземной автостоянки"


def _portal_blocks(blocks: list[tuple[str, int]], version: str = VERSION) -> dict[str, Any]:
    return {
        "artifact_role": PORTAL_BLOCKS_ROLE,
        "artifact_version": "1.0.0",
        "version_uid": version,
        "blocks_sha256": "e" * 64,
        "pages": [],
        "blocks": [
            {"portal_block_id": block, "page_number": page, "block_type": "text", "bbox_norm": [0.1, 0.2, 0.6, 0.7]}
            for block, page in blocks
        ],
    }


def _page_crops(crops: list[tuple[str, str]], version: str = VERSION) -> dict[str, Any]:
    return {
        "artifact_role": PAGE_CROPS_ROLE,
        "artifact_version": "1.0.0",
        "version_uid": version,
        "crop_policy": "portal_image_blocks",
        "crops": [{"portal_block_id": block, "page_number": 1, "sha256": digest} for block, digest in crops],
    }


def _recognised(entries: list[tuple[str, str, str]], version: str = VERSION) -> dict[str, Any]:
    return {
        "artifact_role": RECOGNISED_TEXT_ROLE,
        "artifact_version": "1.0.0",
        "version_uid": version,
        "results_sha256": "f" * 64,
        "entries": [
            {"portal_block_id": block, "page_number": 1, "kind": kind, "text": body} for block, kind, body in entries
        ],
    }


def _documents(version: str = VERSION) -> dict[str, dict[str, Any]]:
    """The saved documents of one run: two blocks on page 3 with recognised text, an image block on page 2."""
    return {
        "portal_blocks": _portal_blocks([(IMAGE_BLOCK, 2), (TEXT_BLOCK, 3), (OTHER_TEXT_BLOCK, 3)], version),
        "page_crops": _page_crops(
            [(IMAGE_BLOCK, IMAGE_CROP), (TEXT_BLOCK, TEXT_CROP), (OTHER_TEXT_BLOCK, OTHER_TEXT_CROP)], version
        ),
        "recognised_text": _recognised(
            [
                (TEXT_BLOCK, "recognised_text", TEXT_OF_BLOCK),
                (OTHER_TEXT_BLOCK, "recognised_text", TEXT_OF_OTHER_BLOCK),
                (IMAGE_BLOCK, "portal_description", DESCRIPTION_OF_IMAGE),
            ],
            version,
        ),
    }


@pytest.fixture(scope="module")
def this_run() -> BlockGateInputs:
    return BlockGateInputs.from_artifacts(version_uid=VERSION, **_documents())


@pytest.fixture(scope="module")
def another_run() -> BlockGateInputs:
    """Another version's geometry, which holds ``FOREIGN_BLOCK`` and none of this run's blocks."""
    return BlockGateInputs.from_artifacts(
        version_uid=OTHER_VERSION,
        portal_blocks=_portal_blocks([(FOREIGN_BLOCK, 2)], OTHER_VERSION),
        page_crops=_page_crops([(FOREIGN_BLOCK, FOREIGN_CROP)], OTHER_VERSION),
        recognised_text=_recognised([(FOREIGN_BLOCK, "recognised_text", "Чужой блок")], OTHER_VERSION),
    )


def _item(
    block: str = IMAGE_BLOCK,
    *,
    page: int = 2,
    crop: str = IMAGE_CROP,
    quote: str | None = None,
    ordinal: int = 0,
) -> BlockEvidenceItem:
    return BlockEvidenceItem(
        evidence_ordinal=ordinal, page_number=page, portal_block_id=block, crop_sha256=crop, recognised_quote=quote
    )


def _reason(item: BlockEvidenceItem, inputs: BlockGateInputs) -> str | None:
    verdict = check_block_evidence(item, inputs)
    return None if verdict.resolved else verdict.reason.value  # type: ignore[union-attr]


# --------------------------------------------------------------------------------------------
# The verdicts
# --------------------------------------------------------------------------------------------


class TestABlockThatIsVerifiedPasses:
    """The controls. Each refusal below is a perturbation of one of these."""

    def test_a_block_of_this_run_with_its_crop_passes(self, this_run: BlockGateInputs) -> None:
        assert _reason(_item(), this_run) is None

    def test_a_quote_verbatim_in_the_recognised_text_of_the_block_passes(self, this_run: BlockGateInputs) -> None:
        item = _item(TEXT_BLOCK, page=3, crop=TEXT_CROP, quote="Высота помещения: 3,0 м.")
        assert _reason(item, this_run) is None

    def test_the_quote_may_span_lines_and_markdown_exactly_as_stored(self, this_run: BlockGateInputs) -> None:
        item = _item(TEXT_BLOCK, page=3, crop=TEXT_CROP, quote="3,0 м.\n- площадь 24,5 м2")
        assert _reason(item, this_run) is None

    def test_a_block_observation_is_grounded_only_when_every_item_resolves(self, this_run: BlockGateInputs) -> None:
        good = BlockObservation(0, (_item(ordinal=0), _item(TEXT_BLOCK, page=3, crop=TEXT_CROP, ordinal=1)))
        result = run_block_gate([good], this_run)
        assert isinstance(result, BlockGateResult)
        assert [v.grounded for v in result.verdicts] == [True]
        assert result.reason_counts() == {}


class TestAForeignBlockIsRefused:
    def test_a_block_of_another_run_is_not_in_this_runs_geometry(
        self, this_run: BlockGateInputs, another_run: BlockGateInputs
    ) -> None:
        foreign = _item(FOREIGN_BLOCK, page=2, crop=FOREIGN_CROP)
        assert _reason(foreign, another_run) is None, "control: it is a real block, of the run that holds it"
        assert _reason(foreign, this_run) == "block_not_in_run_geometry"

    def test_the_refusal_does_not_depend_on_the_crop_or_the_quote_being_right(self, this_run: BlockGateInputs) -> None:
        foreign = _item(FOREIGN_BLOCK, page=2, crop=IMAGE_CROP, quote="Чужой блок")
        assert _reason(foreign, this_run) == "block_not_in_run_geometry"

    def test_a_block_under_a_page_it_does_not_stand_on_is_refused(self, this_run: BlockGateInputs) -> None:
        assert _reason(_item(IMAGE_BLOCK, page=3), this_run) == "block_not_in_run_geometry"

    @pytest.mark.parametrize(
        "block", ["", "blk_", "blk_" + "1" * 31, "blk_" + "1" * 33, "BLK_" + "1" * 32, "blk_" + "G" * 32, " " + IMAGE_BLOCK]
    )
    def test_a_malformed_identifier_is_not_in_the_geometry(self, this_run: BlockGateInputs, block: str) -> None:
        assert _reason(_item(block), this_run) == "block_not_in_run_geometry"

    def test_the_place_is_judged_before_the_crop(self, this_run: BlockGateInputs) -> None:
        both_wrong = _item(FOREIGN_BLOCK, page=2, crop="0" * 64)
        assert _reason(both_wrong, this_run) == "block_not_in_run_geometry"


class TestACropWhoseDigestDiffersIsRefused:
    def test_one_changed_digit_is_a_mismatch(self, this_run: BlockGateInputs) -> None:
        assert _reason(_item(crop=IMAGE_CROP), this_run) is None, "control"
        changed = IMAGE_CROP[:-1] + ("0" if IMAGE_CROP[-1] != "0" else "1")
        assert _reason(_item(crop=changed), this_run) == "block_crop_mismatch"

    def test_the_crop_of_another_block_is_a_mismatch(self, this_run: BlockGateInputs) -> None:
        assert _reason(_item(IMAGE_BLOCK, page=2, crop=TEXT_CROP), this_run) == "block_crop_mismatch"

    def test_the_digest_is_not_normalised(self, this_run: BlockGateInputs) -> None:
        assert _reason(_item(crop=IMAGE_CROP.upper()), this_run) == "block_crop_mismatch"
        assert _reason(_item(crop=" " + IMAGE_CROP), this_run) == "block_crop_mismatch"
        assert _reason(_item(crop=""), this_run) == "block_crop_mismatch"

    def test_a_block_with_no_crop_on_record_is_unverifiable_and_refused(self) -> None:
        documents = _documents()
        documents["page_crops"] = _page_crops([(TEXT_BLOCK, TEXT_CROP)])  # no crop of the image block
        inputs = BlockGateInputs.from_artifacts(version_uid=VERSION, **documents)
        assert _reason(_item(), inputs) == "block_crop_mismatch"

    def test_a_run_with_no_crop_manifest_refuses_every_block(self) -> None:
        documents = _documents()
        del documents["page_crops"]
        inputs = BlockGateInputs.from_artifacts(version_uid=VERSION, **documents)
        assert _reason(_item(), inputs) == "block_crop_mismatch"

    def test_the_crop_is_judged_before_the_quote(self, this_run: BlockGateInputs) -> None:
        item = _item(TEXT_BLOCK, page=3, crop="0" * 64, quote="такого текста нет")
        assert _reason(item, this_run) == "block_crop_mismatch"


class TestAQuoteNotVerbatimInTheRecognisedTextIsRefused:
    QUOTE = "Высота помещения: 3,0 м."

    def _text_item(self, quote: str | None) -> BlockEvidenceItem:
        return _item(TEXT_BLOCK, page=3, crop=TEXT_CROP, quote=quote)

    def test_a_quote_that_is_not_in_the_text_is_refused(self, this_run: BlockGateInputs) -> None:
        assert _reason(self._text_item(self.QUOTE), this_run) is None, "control"
        assert _reason(self._text_item("Высота помещения: 2,5 м."), this_run) == "block_quote_not_in_recognised"

    @pytest.mark.parametrize(
        "near_miss",
        [
            "высота помещения: 3,0 м.",  # case
            "Высота помещения:  3,0 м.",  # a doubled space
            "Высота помещения: 3,0 м. ",  # a trailing space
            " Высота помещения: 3,0 м.",  # a leading space
            "Высота помещения: 3,0 м.\r\n",  # a line ending the text does not have
            "Высота помещения: 3.0 м.",  # a decimal point for a comma
            "Высота помещения: 3,0 м.",  # a no-break space
            "Высота помещения: 3,0 м.".replace("и", "й"),  # a combining mark: NFD, not NFC
        ],
    )
    def test_the_comparison_is_exact_and_normalises_nothing(self, this_run: BlockGateInputs, near_miss: str) -> None:
        assert _reason(self._text_item(near_miss), this_run) == "block_quote_not_in_recognised"

    def test_a_part_of_the_text_is_verbatim_and_admitted(self, this_run: BlockGateInputs) -> None:
        """The gate checks that the quote IS in the text, not that it is the whole text."""
        assert _reason(self._text_item("Высота помещения: 3,0 м"), this_run) is None
        assert _reason(self._text_item("м.\n- пло"), this_run) is None

    def test_a_quote_that_belongs_to_another_block_of_the_page_is_refused(self, this_run: BlockGateInputs) -> None:
        """The recognised text is the block's own, not the page's: a quote of the neighbour proves nothing about this block."""
        assert _reason(_item(OTHER_TEXT_BLOCK, page=3, crop=OTHER_TEXT_CROP, quote="Класс бетона B25"), this_run) is None
        assert _reason(self._text_item("Класс бетона B25"), this_run) == "block_quote_not_in_recognised"

    def test_a_portal_description_is_not_recognised_text(self, this_run: BlockGateInputs) -> None:
        """An IMAGE block's description is a machine description, never an input of analysis (`R-117`)."""
        assert _reason(_item(quote=DESCRIPTION_OF_IMAGE), this_run) == "block_quote_not_in_recognised"

    def test_a_block_with_no_recognised_text_refuses_every_quote(self, this_run: BlockGateInputs) -> None:
        assert _reason(_item(quote="x"), this_run) == "block_quote_not_in_recognised"

    def test_a_run_without_recognised_text_refuses_a_quote_and_passes_no_quote(self) -> None:
        documents = _documents()
        del documents["recognised_text"]
        inputs = BlockGateInputs.from_artifacts(version_uid=VERSION, **documents)
        assert _reason(_item(TEXT_BLOCK, page=3, crop=TEXT_CROP), inputs) is None
        assert _reason(_item(TEXT_BLOCK, page=3, crop=TEXT_CROP, quote=self.QUOTE), inputs) == "block_quote_not_in_recognised"

    def test_an_empty_quote_is_refused_though_it_is_a_substring_of_everything(self, this_run: BlockGateInputs) -> None:
        assert "" in TEXT_OF_BLOCK
        assert _reason(self._text_item(""), this_run) == "block_quote_not_in_recognised"

    def test_a_quote_the_store_cannot_keep_is_refused(self) -> None:
        long_text = "а" * (MAX_BLOCK_QUOTE_CHARS + 1)
        documents = _documents()
        documents["recognised_text"] = _recognised([(TEXT_BLOCK, "recognised_text", long_text)])
        inputs = BlockGateInputs.from_artifacts(version_uid=VERSION, **documents)
        kept = _item(TEXT_BLOCK, page=3, crop=TEXT_CROP, quote=long_text[:MAX_BLOCK_QUOTE_CHARS])
        too_long = _item(TEXT_BLOCK, page=3, crop=TEXT_CROP, quote=long_text)
        assert _reason(kept, inputs) is None, "control: 2000 characters are kept"
        assert _reason(too_long, inputs) == "block_quote_not_in_recognised"

    def test_the_absence_of_a_quote_is_not_a_refusal(self, this_run: BlockGateInputs) -> None:
        assert _reason(self._text_item(None), this_run) is None


class TestTheVerdictOfAnObservation:
    def test_one_bad_item_ungrounds_the_observation_and_every_item_is_still_judged(
        self, this_run: BlockGateInputs
    ) -> None:
        observation = BlockObservation(
            4,
            (
                _item(ordinal=0),
                _item(FOREIGN_BLOCK, ordinal=1),
                _item(crop="0" * 64, ordinal=2),
                _item(TEXT_BLOCK, page=3, crop=TEXT_CROP, ordinal=3),
            ),
            extended_observation_ref="xobs_7",
        )
        (verdict,) = run_block_gate([observation], this_run).verdicts
        assert not verdict.grounded
        assert [v.resolved for v in verdict.evidence_verdicts] == [True, False, False, True]
        assert verdict.reason is UngroundedReason.BLOCK_NOT_IN_RUN_GEOMETRY, "the first failing item, in evidence order"
        assert verdict.failing_evidence_ordinal == 1
        assert verdict.observation is observation

    def test_the_block_gate_emits_only_its_three_reasons(self, this_run: BlockGateInputs) -> None:
        observations = [
            BlockObservation(0, (_item(FOREIGN_BLOCK),)),
            BlockObservation(1, (_item(crop="0" * 64),)),
            BlockObservation(2, (_item(TEXT_BLOCK, page=3, crop=TEXT_CROP, quote="нет такого"),)),
            BlockObservation(3, (_item(),)),
        ]
        result = run_block_gate(observations, this_run)
        assert result.reason_counts() == {
            "block_not_in_run_geometry": 1,
            "block_crop_mismatch": 1,
            "block_quote_not_in_recognised": 1,
        }
        # The text gate's refusal of a quote found only in recognised text is cancelled for block evidence:
        # a quote in the recognised text is what the third check admits, so it is never a reason here.
        assert UngroundedReason.QUOTE_IN_RECOGNISED_TEXT.value not in result.reason_counts()
        assert len(result.grounded) == 1 and len(result.ungrounded) == 3

    def test_the_grounding_kind_is_carried_by_the_verdict(self, this_run: BlockGateInputs) -> None:
        (verdict,) = run_block_gate([BlockObservation(0, (_item(),))], this_run).verdicts
        assert verdict.grounding_kind == "portal_block" == GROUNDING_PORTAL_BLOCK
        assert verdict.observation.grounding_kind == "portal_block"

    def test_a_refused_observation_keeps_its_kind(self, this_run: BlockGateInputs) -> None:
        (verdict,) = run_block_gate([BlockObservation(0, (_item(FOREIGN_BLOCK),))], this_run).verdicts
        assert not verdict.grounded and verdict.grounding_kind == "portal_block"


class TestTheGateFailsClosed:
    def test_a_run_with_no_inputs_refuses_every_block(self) -> None:
        """A ``text_only`` run builds no inputs; a version without a portal bundle has no geometry."""
        observation = BlockObservation(0, (_item(),))
        for inputs in (None, BlockGateInputs.empty()):
            (verdict,) = run_block_gate([observation], inputs).verdicts
            assert not verdict.grounded
            assert verdict.reason is UngroundedReason.BLOCK_NOT_IN_RUN_GEOMETRY

    def test_a_run_with_no_geometry_refuses_even_a_block_with_a_crop_and_text(self) -> None:
        documents = _documents()
        del documents["portal_blocks"]
        inputs = BlockGateInputs.from_artifacts(version_uid=VERSION, **documents)
        item = _item(TEXT_BLOCK, page=3, crop=TEXT_CROP, quote="Высота помещения: 3,0 м.")
        assert _reason(item, inputs) == "block_not_in_run_geometry"

    def test_no_observations_is_an_empty_result(self, this_run: BlockGateInputs) -> None:
        assert run_block_gate([], this_run).verdicts == ()


class TestMalformedBlockObservationsAreRefusedBeforeTheGate:
    def test_an_observation_with_no_evidence_is_malformed_not_ungrounded(self) -> None:
        with pytest.raises(DomainError) as caught:
            BlockObservation(0, ())
        assert caught.value.code is ErrorCode.ANALYSIS_INPUT_INVALID

    def test_a_repeated_evidence_ordinal_is_refused(self) -> None:
        with pytest.raises(DomainError):
            BlockObservation(0, (_item(ordinal=0), _item(TEXT_BLOCK, page=3, ordinal=0)))

    @pytest.mark.parametrize("ref", ["", "x" * (MAX_EXTENDED_OBSERVATION_REF_CHARS + 1)])
    def test_a_reference_the_column_cannot_hold_is_refused(self, ref: str) -> None:
        with pytest.raises(DomainError):
            BlockObservation(0, (_item(),), extended_observation_ref=ref)

    def test_an_item_of_the_wrong_type_is_refused(self) -> None:
        with pytest.raises(DomainError):
            BlockEvidenceItem(evidence_ordinal=True, page_number=2, portal_block_id=IMAGE_BLOCK, crop_sha256=IMAGE_CROP)
        with pytest.raises(DomainError):
            BlockEvidenceItem(evidence_ordinal=0, page_number=2, portal_block_id=IMAGE_BLOCK, crop_sha256=None)  # type: ignore[arg-type]
        with pytest.raises(DomainError):
            BlockEvidenceItem(0, 2, IMAGE_BLOCK, IMAGE_CROP, recognised_quote=7)  # type: ignore[arg-type]


# --------------------------------------------------------------------------------------------
# The views over the run's saved documents
# --------------------------------------------------------------------------------------------


class TestTheViewsAreOfThisRunsVersionAndOfTheShapeDeclared:
    def test_a_document_of_another_version_is_refused(self) -> None:
        documents = _documents(OTHER_VERSION)
        for key, view in (
            ("portal_blocks", PortalBlockGeometry),
            ("page_crops", CropManifest),
            ("recognised_text", RecognisedText),
        ):
            with pytest.raises(DomainError) as caught:
                view.from_artifact(documents[key], version_uid=VERSION)
            assert caught.value.code is ErrorCode.ANALYSIS_INPUT_INVALID, key
        # ... and each is accepted for the version it describes: the refusal is the version, not the document
        assert len(PortalBlockGeometry.from_artifact(documents["portal_blocks"], version_uid=OTHER_VERSION)) == 3

    def test_one_foreign_document_among_three_refuses_the_set(self) -> None:
        documents = _documents()
        documents["page_crops"] = _page_crops([(IMAGE_BLOCK, IMAGE_CROP)], OTHER_VERSION)
        with pytest.raises(DomainError):
            BlockGateInputs.from_artifacts(version_uid=VERSION, **documents)

    def test_a_document_under_another_role_is_refused(self) -> None:
        documents = _documents()
        with pytest.raises(DomainError):
            PortalBlockGeometry.from_artifact(documents["page_crops"], version_uid=VERSION)
        with pytest.raises(DomainError):
            CropManifest.from_artifact(documents["recognised_text"], version_uid=VERSION)
        with pytest.raises(DomainError):
            RecognisedText.from_artifact(documents["portal_blocks"], version_uid=VERSION)

    def test_a_repeated_block_is_refused_not_resolved_by_the_last_one(self) -> None:
        with pytest.raises(DomainError):
            PortalBlockGeometry.from_artifact(_portal_blocks([(IMAGE_BLOCK, 2), (IMAGE_BLOCK, 3)]), version_uid=VERSION)
        with pytest.raises(DomainError):
            CropManifest.from_artifact(_page_crops([(IMAGE_BLOCK, IMAGE_CROP), (IMAGE_BLOCK, TEXT_CROP)]), version_uid=VERSION)

    @pytest.mark.parametrize("digest", ["", "A" * 64, "a" * 63, "a" * 65, "g" * 64])
    def test_a_crop_digest_that_is_not_a_digest_is_refused(self, digest: str) -> None:
        with pytest.raises(DomainError):
            CropManifest.from_artifact(_page_crops([(IMAGE_BLOCK, digest)]), version_uid=VERSION)

    @pytest.mark.parametrize(
        "box", [None, [0.1, 0.2, 0.3], [0.1, 0.2, 0.3, 1.5], [0.5, 0.2, 0.3, 0.9], [0.1, 0.5, 0.3, 0.5], "abcd", [True, 0, 1, 1]]
    )
    def test_a_box_the_database_would_refuse_is_refused_here(self, box: Any) -> None:
        document = _portal_blocks([(IMAGE_BLOCK, 2)])
        document["blocks"][0]["bbox_norm"] = box
        with pytest.raises(DomainError):
            PortalBlockGeometry.from_artifact(document, version_uid=VERSION)

    def test_a_page_that_is_a_boolean_is_refused(self) -> None:
        document = _portal_blocks([(IMAGE_BLOCK, 2)])
        document["blocks"][0]["page_number"] = True
        with pytest.raises(DomainError):
            PortalBlockGeometry.from_artifact(document, version_uid=VERSION)

    def test_the_geometry_keeps_the_box_the_publisher_will_write(self, this_run: BlockGateInputs) -> None:
        place = this_run.geometry.place(IMAGE_BLOCK)
        assert place is not None and place.page_number == 2 and place.bbox_norm == (0.1, 0.2, 0.6, 0.7)

    def test_only_recognised_text_entries_are_kept(self, this_run: BlockGateInputs) -> None:
        assert this_run.recognised.texts(IMAGE_BLOCK) == ()
        assert this_run.recognised.texts(TEXT_BLOCK) == (TEXT_OF_BLOCK,)
        assert len(this_run.recognised) == 2

    def test_absent_documents_are_empty_views(self) -> None:
        inputs = BlockGateInputs.from_artifacts(version_uid=VERSION)
        assert len(inputs.geometry) == len(inputs.crops) == len(inputs.recognised) == 0


# --------------------------------------------------------------------------------------------
# The text gate is unchanged
# --------------------------------------------------------------------------------------------


def _text_observations(items: list[dict[str, Any]]) -> ObservationSet:
    observations = []
    for ordinal, anchor in enumerate(items):
        entry = {
            "evidence_ordinal": 0,
            "page_number": anchor["page_number"],
            "quote": anchor["quote"],
            "char_start": anchor["char_start"],
            "char_end": anchor["char_end"],
        }
        if anchor.get("block_id") is not None:
            entry["block_id"] = anchor["block_id"]
        observations.append(
            {
                "observation_ordinal": ordinal,
                "category": "internal_contradiction",
                "finding_text": "Расхождение.",
                "recommendation_text": "Согласовать значения между разделами.",
                "evidence": [entry],
            }
        )
    return ObservationSet.from_artifact(
        {
            "artifact_role": "analysis.text_observations",
            "artifact_version": "1.0.0",
            "run_id": "run_01M2545JSD15ETSNNV904X991J",
            "stage_id": "text_analysis",
            "analysis_profile_id": "ap_x",
            "prompt_bundle_id": "pb_x",
            "provider_mode": "recorded",
            "pages_analysed": [1],
            "observations": observations,
        }
    )


class TestTheTextGateIsUnchanged:
    def test_a_text_quote_that_resolves_is_grounded_and_is_a_text_span(
        self, corpus, text_layer: TextLayer, block_index: BlockIndex
    ) -> None:
        anchors = corpus.seeded_anchors()
        result = run_grounding_gate(_text_observations(anchors), text_layer, block_index)
        assert result.ungrounded_count == 0 and result.grounded_count == len(anchors)
        assert {verdict.grounding_kind for verdict in result.verdicts} == {"text_span"} == {GROUNDING_TEXT_SPAN}

    def test_a_quote_found_only_in_recognised_text_is_refused_as_before(
        self, corpus, text_layer: TextLayer, block_index: BlockIndex
    ) -> None:
        """The quote of a text observation must be in the text layer. The gate has no access to recognised text, so
        a block record holding the quote cannot ground a text observation: it is refused exactly as it was."""
        anchor = dict(corpus.seeded_anchors()[0])
        recognised_only = "Только в распознанном тексте: 12,5 м"
        assert recognised_only not in text_layer.sequence
        anchor["quote"] = recognised_only
        anchor["char_end"] = anchor["char_start"] + len(recognised_only)
        anchor["block_id"] = None
        holder = RecognisedText.from_artifact(
            _recognised([(TEXT_BLOCK, "recognised_text", recognised_only)]), version_uid=VERSION
        )
        assert holder.texts(TEXT_BLOCK) == (recognised_only,), "control: the quote IS in a recognised text"
        result = run_grounding_gate(_text_observations([anchor]), text_layer, block_index)
        (verdict,) = result.verdicts
        assert not verdict.grounded
        assert verdict.reason is UngroundedReason.QUOTATION_ABSENT
        assert verdict.grounding_kind == "text_span"

    def test_the_text_gate_still_emits_only_its_own_reasons(
        self, corpus, text_layer: TextLayer, block_index: BlockIndex
    ) -> None:
        anchor = dict(corpus.seeded_anchors()[0])
        anchor["char_end"] += 1  # the declared interval no longer holds the quote
        result = run_grounding_gate(_text_observations([anchor]), text_layer, block_index)
        assert set(result.reason_counts()) == {"span_length_mismatch"}
        block_reasons = {"block_not_in_run_geometry", "block_crop_mismatch", "block_quote_not_in_recognised"}
        assert not set(result.reason_counts()) & block_reasons

    def test_the_text_gate_takes_no_block_input(self) -> None:
        import inspect

        parameters = inspect.signature(run_grounding_gate).parameters
        assert list(parameters) == ["observations", "text_layer", "block_index"]


# --------------------------------------------------------------------------------------------
# The executor's read of the inputs: a text_only run reads none, a one_list run reads its own
# --------------------------------------------------------------------------------------------


class _Store:
    """The blob store of the artifacts, in memory, recording what was read."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.reads: list[str] = []

    def put_blob(self, payload: bytes, *, declared_sha256: str, declared_size: int, role: str, media_type: str) -> Any:
        blob_id = str(derive_blob_id(sha256=declared_sha256, size=declared_size))
        self.objects[blob_id] = payload
        return SimpleNamespace(blob_id=blob_id, sha256=declared_sha256, size=declared_size, media_type=media_type)

    def read(self, blob_id: Any, *, verify: bool) -> bytes:
        assert verify is True
        self.reads.append(str(blob_id))
        return self.objects[str(blob_id)]


def _gate_world(*, geometry: bool = True) -> tuple[_Store, _StageOutputs, dict[str, Any], dict[str, str]]:
    """A store holding a run's text layer, block index and (optionally) its three geometry documents."""
    store, outputs = _Store(), _StageOutputs()
    page = "Страница с текстом."
    text_layer = {
        "artifact_role": ROLE_TEXT_LAYER,
        "artifact_version": "1.0.0",
        "version_uid": VERSION,
        "normalization": {"id": "nfc_v1", "description": "NFC"},
        "total_char_count": len(page),
        "pages": [{"page_number": 1, "char_start": 0, "char_end": len(page), "text": page}],
    }
    block_index = {
        "artifact_role": ROLE_BLOCK_INDEX,
        "artifact_version": "1.0.0",
        "version_uid": VERSION,
        "blocks": [],
    }
    documents = {ROLE_TEXT_LAYER: text_layer, ROLE_BLOCK_INDEX: block_index}
    if geometry:
        saved = _documents()
        documents[ROLE_PORTAL_BLOCKS] = saved["portal_blocks"]
        documents[ROLE_PAGE_CROPS] = saved["page_crops"]
        documents[ROLE_RECOGNISED_TEXT] = saved["recognised_text"]
    blob_ids: dict[str, str] = {}
    for role, document in documents.items():
        reference, _ = publish_artifact(store, role, document)
        outputs.refs[role] = reference
        blob_ids[role] = str(reference.blob_id)
    observations = {
        "artifact_role": "analysis.text_observations",
        "artifact_version": "1.0.0",
        "run_id": "run_01M2545JSD15ETSNNV904X991J",
        "stage_id": "text_analysis",
        "analysis_profile_id": "ap_x",
        "prompt_bundle_id": "pb_x",
        "provider_mode": "recorded",
        "pages_analysed": [1],
        "observations": [],
    }
    return store, outputs, observations, blob_ids


class TestTheExecutorReadsTheBlockInputsOnlyForAOneListRun:
    def test_a_text_only_run_reads_none_of_the_three_artifacts(self) -> None:
        store, outputs, observations, blob_ids = _gate_world()
        inputs = _read_gate_inputs(
            observations_document=observations, outputs=outputs, blob_store=store, publication_mode="text_only"
        )
        assert inputs is not None and inputs.block_documents is None
        block_blobs = {blob_ids[role] for role in (ROLE_PORTAL_BLOCKS, ROLE_PAGE_CROPS, ROLE_RECOGNISED_TEXT)}
        assert block_blobs.isdisjoint(store.reads), "a text_only run never reaches the block branch"
        assert set(store.reads) == {blob_ids[ROLE_TEXT_LAYER], blob_ids[ROLE_BLOCK_INDEX]}

    def test_the_default_is_text_only(self) -> None:
        store, outputs, observations, _ = _gate_world()
        inputs = _read_gate_inputs(observations_document=observations, outputs=outputs, blob_store=store)
        assert inputs is not None and inputs.block_documents is None

    def test_a_one_list_run_reads_its_own_three_documents(self) -> None:
        store, outputs, observations, blob_ids = _gate_world()
        inputs = _read_gate_inputs(
            observations_document=observations, outputs=outputs, blob_store=store, publication_mode="one_list"
        )
        assert inputs is not None and inputs.block_documents is not None
        saved = _documents()
        assert dict(inputs.block_documents) == {
            ROLE_PORTAL_BLOCKS: saved["portal_blocks"],
            ROLE_PAGE_CROPS: saved["page_crops"],
            ROLE_RECOGNISED_TEXT: saved["recognised_text"],
        }
        assert {blob_ids[role] for role in inputs.block_documents} <= set(store.reads)

    def test_the_documents_read_make_a_working_gate(self) -> None:
        store, outputs, observations, _ = _gate_world()
        inputs = _read_gate_inputs(
            observations_document=observations, outputs=outputs, blob_store=store, publication_mode="one_list"
        )
        assert inputs is not None and inputs.block_documents is not None
        documents = inputs.block_documents
        gate_inputs = BlockGateInputs.from_artifacts(
            version_uid=VERSION,
            portal_blocks=documents[ROLE_PORTAL_BLOCKS],
            page_crops=documents[ROLE_PAGE_CROPS],
            recognised_text=documents[ROLE_RECOGNISED_TEXT],
        )
        good = BlockObservation(0, (_item(),))
        foreign = BlockObservation(1, (_item(FOREIGN_BLOCK),))
        result = run_block_gate([good, foreign], gate_inputs)
        assert [v.grounded for v in result.verdicts] == [True, False]

    def test_a_one_list_run_over_a_version_without_a_bundle_has_no_documents_and_the_gate_refuses(self) -> None:
        store, outputs, observations, _ = _gate_world(geometry=False)
        inputs = _read_gate_inputs(
            observations_document=observations, outputs=outputs, blob_store=store, publication_mode="one_list"
        )
        assert inputs is not None and inputs.block_documents == {}
        gate_inputs = BlockGateInputs.from_artifacts(version_uid=VERSION, **{})
        (verdict,) = run_block_gate([BlockObservation(0, (_item(),))], gate_inputs).verdicts
        assert verdict.reason is UngroundedReason.BLOCK_NOT_IN_RUN_GEOMETRY

    def test_the_text_inputs_are_read_the_same_in_both_modes(self) -> None:
        store, outputs, observations, _ = _gate_world()
        legacy = _read_gate_inputs(
            observations_document=observations, outputs=outputs, blob_store=store, publication_mode="text_only"
        )
        one_list = _read_gate_inputs(
            observations_document=observations, outputs=outputs, blob_store=store, publication_mode="one_list"
        )
        assert legacy is not None and one_list is not None
        assert legacy.text_layer.sequence == one_list.text_layer.sequence
        assert legacy.observation_set == one_list.observation_set

    def test_nothing_to_ground_is_still_none(self) -> None:
        store, outputs, _, _ = _gate_world()
        assert _read_gate_inputs(
            observations_document=None, outputs=outputs, blob_store=store, publication_mode="one_list"
        ) is None
        assert store.reads == []


class TestThePublicationModeOfARun:
    def test_the_marker_of_the_row_is_read(self) -> None:
        assert _publication_mode(SimpleNamespace(publication_mode="one_list")) == "one_list"
        assert _publication_mode(SimpleNamespace(publication_mode="text_only")) == "text_only"

    def test_a_row_without_the_column_is_a_text_only_run(self) -> None:
        assert _publication_mode(SimpleNamespace()) == "text_only"

    @pytest.mark.parametrize("value", ["", "ONE_LIST", "one-list", None, 1, "both"])
    def test_a_value_the_database_would_refuse_is_refused_not_read_as_text_only(self, value: Any) -> None:
        with pytest.raises(DomainError) as caught:
            _publication_mode(SimpleNamespace(publication_mode=value))
        assert caught.value.code is ErrorCode.ANALYSIS_INPUT_INVALID

    def test_the_executors_literals_are_the_databases(self) -> None:
        source = MIGRATION_0064.read_text(encoding="utf-8")
        match = re.search(r"ck_audit_run_publication_mode\s*\"\s*\"CHECK \(publication_mode IN \(([^)]*)\)\)", source)
        assert match is not None, "the migration no longer declares ck_audit_run_publication_mode"
        assert set(re.findall(r"'([a-z_]+)'", match.group(1))) == {
            executor_module._PUBLICATION_TEXT_ONLY,
            executor_module._PUBLICATION_ONE_LIST,
        }

    def test_the_roles_the_executor_reads_are_the_roles_the_views_check(self) -> None:
        assert executor_module._BLOCK_GATE_ROLES == (PORTAL_BLOCKS_ROLE, PAGE_CROPS_ROLE, RECOGNISED_TEXT_ROLE)
        assert (ROLE_PORTAL_BLOCKS, ROLE_PAGE_CROPS, ROLE_RECOGNISED_TEXT) == executor_module._BLOCK_GATE_ROLES


# --------------------------------------------------------------------------------------------
# The vocabulary the gate and the database agree on
# --------------------------------------------------------------------------------------------

BLOCK_REASONS = frozenset({"block_not_in_run_geometry", "block_crop_mismatch", "block_quote_not_in_recognised"})


class TestTheGatesVocabularyIsTheDatabasesVocabulary:
    def test_the_three_reasons_are_in_the_gates_vocabulary(self) -> None:
        assert BLOCK_REASONS <= UNGROUNDED_REASONS
        assert len(UNGROUNDED_REASONS) == 15
        assert "quote_in_recognised_text" in UNGROUNDED_REASONS, "the text gate's reason stays in the vocabulary"

    def test_the_gates_vocabulary_is_the_checks_vocabulary_of_0064(self) -> None:
        source = MIGRATION_0064.read_text(encoding="utf-8")
        old = re.search(r"_REASONS_0023 = \((.*?)\n\)", source, re.S)
        new = re.search(r"_NEW_REASONS = \((.*?)\)", source, re.S)
        assert old is not None and new is not None
        declared = set(re.findall(r'"([a-z_]+)"', old.group(1))) | set(re.findall(r'"([a-z_]+)"', new.group(1)))
        assert declared == set(UNGROUNDED_REASONS)

    def test_the_limits_and_kinds_are_the_columns_of_0064(self) -> None:
        source = MIGRATION_0064.read_text(encoding="utf-8")
        assert f"char_length(recognised_quote) BETWEEN 1 AND {MAX_BLOCK_QUOTE_CHARS}" in source
        assert f"char_length(extended_observation_ref) BETWEEN 1 AND {MAX_EXTENDED_OBSERVATION_REF_CHARS}" in source
        assert f"grounding_kind IN ('{GROUNDING_TEXT_SPAN}', '{GROUNDING_PORTAL_BLOCK}')" in source


class TestTheGatesVerdictsAreWritableToTheDatabase:
    """On PostgreSQL: a refused block observation is recorded with its kind and the reason the gate gave."""

    _INSERT = text(
        "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, "
        "finding_text, recommendation_text, grounded, ungrounded_reason, analysis_profile_id, prompt_bundle_id, "
        "provider_mode, grounding_kind, extended_observation_ref) VALUES (:id, :run, NULL, 'block_analysis', "
        "'drawing_discrepancy', 'т', 'т', false, :reason, :ap, :pb, 'recorded', :kind, :ref)"
    )

    def _record(self, session: Session, seeded, verdict, *, reason: str | None = None, kind: str | None = None) -> None:
        with nested_transaction(session):
            session.execute(
                self._INSERT,
                {
                    "id": FindingObservationId.new().value,
                    "run": seeded.run_id,
                    "reason": reason if reason is not None else verdict.reason.value,
                    "ap": seeded.analysis_profile_id,
                    "pb": seeded.prompt_bundle_id,
                    "kind": kind if kind is not None else verdict.grounding_kind,
                    "ref": verdict.observation.extended_observation_ref,
                },
            )

    @pytest.mark.parametrize(
        ("name", "item"),
        [
            ("block_not_in_run_geometry", _item(FOREIGN_BLOCK)),
            ("block_crop_mismatch", _item(crop="0" * 64)),
            ("block_quote_not_in_recognised", _item(TEXT_BLOCK, page=3, crop=TEXT_CROP, quote="нет такого")),
        ],
    )
    def test_each_refusal_the_gate_gives_is_recorded_as_a_portal_block_observation(
        self, session: Session, seeded, this_run: BlockGateInputs, name: str, item: BlockEvidenceItem
    ) -> None:
        (verdict,) = run_block_gate([BlockObservation(0, (item,), extended_observation_ref="xobs_1")], this_run).verdicts
        assert verdict.reason is not None and verdict.reason.value == name
        self._record(session, seeded, verdict)
        stored = session.execute(
            text(
                "SELECT ungrounded_reason, grounding_kind, extended_observation_ref FROM finding_observation "
                "WHERE run_id = :run AND ungrounded_reason = :reason"
            ),
            {"run": seeded.run_id, "reason": name},
        ).one()
        assert tuple(stored) == (name, "portal_block", "xobs_1")

    def test_a_kind_outside_the_two_is_refused_by_the_database(self, session: Session, seeded, this_run: BlockGateInputs) -> None:
        (verdict,) = run_block_gate([BlockObservation(0, (_item(FOREIGN_BLOCK),))], this_run).verdicts
        with pytest.raises(IntegrityError) as caught:
            self._record(session, seeded, verdict, kind="block")
        assert "ck_finding_observation_grounding_kind" in str(caught.value.orig)
