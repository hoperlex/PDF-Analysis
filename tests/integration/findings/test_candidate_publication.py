"""`F8-PUBLISH` on real PostgreSQL: N observations make one finding, and the readers take it (ADR-0029 decision 7, plan-v5 section 4).

Four groups:

* the publisher of groups: a group of N is one finding whose canonical observation is the first that passed gate v2, with one category,
  the block evidence of each observation from the run's own geometry, ``grounding_kind`` and ``extended_observation_ref``; a mixed group is
  ``cross_source`` and names the text finding it is related to; a group wholly of primary texts writes nothing; the members the gate
  refuses split the group and are written as diagnostics;
* the readers: ``published_findings`` / ``group_published_findings`` / ``finding_by_uid`` and the decision ledger take such a group, and a
  broken one (no canonical, two categories) is refused with ``STORAGE_INTEGRITY_ERROR`` -- the control that shows the assertion can fail;
* the executor: ``_read_gate_inputs`` and ``_run_evidence_gate`` publish candidates for a ``one_list`` run after its text findings, and a
  ``text_only`` run publishes exactly as before and does not even read the review;
* the memory: a block finding's case is ``dm-capture/2`` with its block evidence and the crop of its block.

Isolation is by rollback (the suite's ``session`` fixture), as the rows cannot be deleted.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ROLE_BLOCK_INDEX,
    ROLE_PAGE_CROPS,
    ROLE_PORTAL_BLOCKS,
    ROLE_RECOGNISED_TEXT,
    ROLE_TEXT_LAYER,
    extended_artifact_envelope,
    publish_artifact,
)
from auditmanager.decision_memory.public import (
    CAPTURE_VERSION_BLOCK_EVIDENCE,
    BlockEvidenceFact,
    CaptureSnapshot,
    CaseContent,
    CaseOrigin,
    DecisionFact,
    MemoryRepository,
    select_case_crops,
)
from auditmanager.decisions import current_verdict, record_decision
from auditmanager.findings import (
    BlockGateInputs,
    CandidateGroup,
    CandidateMember,
    BlockEvidenceItem,
    finding_by_uid,
    finding_exists,
    group_published_findings,
    observation_belongs_to_finding,
    publish_candidate_groups,
    publish_gate_result,
    published_finding_block_evidence,
    published_finding_count,
    published_findings,
    run_grounding_gate,
)
from auditmanager.findings.artifacts import (
    PAGE_CROPS_ROLE,
    PORTAL_BLOCKS_ROLE,
    RECOGNISED_TEXT_ROLE,
)
from auditmanager.findings.publication import (
    CATEGORY_CROSS_SOURCE,
    CATEGORY_DRAWING_DISCREPANCY,
    RECOMMENDATION_CHECK_THE_SOURCE,
    SKIP_PRIMARY_TEXT_ONLY,
    STAGE_BLOCK_ANALYSIS,
    STAGE_FINDING_MERGE,
)
from auditmanager.runs.executor import _read_gate_inputs, _run_evidence_gate, _StageOutputs
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import FindingObservationId, FindingUid
from auditmanager.storage.public import derive_blob_id

BLK_A = "blk_" + "a" * 32
BLK_B = "blk_" + "b" * 32
BLK_C = "blk_" + "c" * 32
CROP_A = "a1" * 32
CROP_B = "b2" * 32
CROP_C = "c3" * 32
BOX_A = (0.1, 0.2, 0.6, 0.7)
BOX_B = (0.2, 0.2, 0.4, 0.3)
BOX_C = (0.5, 0.5, 0.9, 0.9)
RECOGNISED_A = "Размер 3000 мм"


def _geometry(version: str) -> BlockGateInputs:
    """The geometry of one run: three image blocks of pages 2 and 3, the crop of each on record, and recognised text for the first."""
    return BlockGateInputs.from_artifacts(version_uid=version, **_documents(version))


def _documents(version: str) -> dict[str, dict[str, Any]]:
    blocks = [(BLK_A, 2, BOX_A, CROP_A), (BLK_B, 2, BOX_B, CROP_B), (BLK_C, 3, BOX_C, CROP_C)]
    return {
        "portal_blocks": {
            "artifact_role": PORTAL_BLOCKS_ROLE, "artifact_version": "1.0.0", "version_uid": version, "blocks_sha256": "e" * 64, "pages": [],
            "blocks": [{"portal_block_id": b, "page_number": p, "block_type": "image", "bbox_norm": list(box)} for b, p, box, _ in blocks],
        },
        "page_crops": {
            "artifact_role": PAGE_CROPS_ROLE, "artifact_version": "1.0.0", "version_uid": version, "crop_policy": "portal_image_blocks",
            "crops": [{"portal_block_id": b, "page_number": p, "sha256": sha} for b, p, _, sha in blocks],
        },
        "recognised_text": {
            "artifact_role": RECOGNISED_TEXT_ROLE, "artifact_version": "1.0.0", "version_uid": version, "results_sha256": "f" * 64,
            "entries": [{"portal_block_id": BLK_A, "page_number": 2, "kind": "recognised_text", "text": RECOGNISED_A}],
        },
    }


def _item(block: str = BLK_A, *, ordinal: int = 0, quote: str | None = None, crop: str | None = None) -> BlockEvidenceItem:
    pages = {BLK_A: (2, CROP_A), BLK_B: (2, CROP_B), BLK_C: (3, CROP_C)}
    page, sha = pages[block]
    return BlockEvidenceItem(evidence_ordinal=ordinal, page_number=page, portal_block_id=block, crop_sha256=crop or sha, recognised_quote=quote)


def _member(ref: str, *blocks: str, **extra: Any) -> CandidateMember:
    values: dict[str, Any] = {
        "extended_observation_ref": ref,
        "finding_text": f"Размер не совпадает с планом ({ref}).",
        "block_evidence": tuple(_item(block, ordinal=position) for position, block in enumerate(blocks or (BLK_A,))),
    }
    values.update(extra)
    return CandidateMember(**values)


def _publish(session: Session, seeded: Any, groups: list[CandidateGroup], *, inputs: BlockGateInputs | None = ..., **extra: Any):  # type: ignore[assignment]
    return publish_candidate_groups(
        session, groups=groups, gate_inputs=_geometry(seeded.version_uid) if inputs is ... else inputs,
        run_id=seeded.run_id, project_uid=seeded.project_uid, version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id, prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="recorded", **extra,
    )


def _rows(session: Session, sql: str, **parameters: Any) -> list[Any]:
    return list(session.execute(text(sql), parameters).mappings().all())


# --------------------------------------------------------------------------------------------
# The publisher of groups
# --------------------------------------------------------------------------------------------


class TestAGroupOfNIsOneFinding:
    def test_three_candidates_are_one_finding_with_the_first_as_canonical_and_every_reader_takes_it(self, session: Session, seeded: Any) -> None:
        group = CandidateGroup("xgrp_1", (_member("xobs_1", BLK_A), _member("xobs_2", BLK_A, BLK_B), _member("xobs_3", BLK_B)))
        result = _publish(session, seeded, [group])

        (finding,) = result.published
        assert (result.published_count, result.observation_count, result.diagnostic_count) == (1, 3, 0)
        assert finding.canonical_observation_id == finding.observation_ids[0], "the first member that passed is the canonical one"
        assert (finding.category, finding.stage_id) == (CATEGORY_DRAWING_DISCREPANCY, STAGE_BLOCK_ANALYSIS)

        # the readers: one finding identity, three observations, no refusal
        rows = published_findings(session, seeded.run_id)
        assert len(rows) == 3 and {row.finding_uid for row in rows} == {finding.finding_uid}
        (grouped,) = group_published_findings(rows)
        assert grouped.canonical.finding_observation_id == finding.canonical_observation_id
        assert [m.finding_observation_id for m in grouped.merged] == list(finding.observation_ids[1:])
        assert published_finding_count(session, seeded.run_id) == 1
        head = finding_by_uid(session, finding.finding_uid)
        assert head is not None and head.finding_observation_id == finding.canonical_observation_id
        assert finding_exists(session, finding.finding_uid)
        assert all(observation_belongs_to_finding(session, finding_uid=finding.finding_uid, finding_observation_id=i) for i in finding.observation_ids)

    def test_the_control_a_group_broken_by_hand_is_refused_by_the_same_reader(self, session: Session, seeded: Any) -> None:
        """The reader is the one that refuses: take the canonical away, or give one member another category, and it raises."""
        group = CandidateGroup("xgrp_1", (_member("xobs_1", BLK_A), _member("xobs_2", BLK_B)))
        (finding,) = _publish(session, seeded, [group]).published
        group_published_findings(published_findings(session, seeded.run_id))  # the control: it reads

        session.execute(text("UPDATE finding SET canonical_observation_id = NULL WHERE finding_uid = :f"), {"f": finding.finding_uid})
        with pytest.raises(DomainError) as no_canonical:
            group_published_findings(published_findings(session, seeded.run_id))
        assert no_canonical.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR

        session.execute(text("UPDATE finding SET canonical_observation_id = :o WHERE finding_uid = :f"),
                        {"o": finding.canonical_observation_id, "f": finding.finding_uid})
        group_published_findings(published_findings(session, seeded.run_id))
        session.execute(
            text(
                "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, finding_text, "
                "recommendation_text, grounded, ungrounded_reason, analysis_profile_id, prompt_bundle_id, provider_mode) "
                "VALUES (:o, :r, :f, 'block_analysis', 'cross_source', 'x', 'y', true, NULL, :ap, :pb, 'recorded')"
            ),
            {"o": FindingObservationId.new().value, "r": seeded.run_id, "f": finding.finding_uid,
             "ap": seeded.analysis_profile_id, "pb": seeded.prompt_bundle_id},
        )
        with pytest.raises(DomainError) as two_categories:
            group_published_findings(published_findings(session, seeded.run_id))
        assert two_categories.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR

    def test_each_observation_carries_its_reference_its_grounding_and_the_recommendation_of_its_corrector(self, session: Session, seeded: Any) -> None:
        group = CandidateGroup("xgrp_1", (_member("xobs_1", BLK_A, refined_recommendation="Уточнить размер по плану."), _member("xobs_2", BLK_B)))
        (finding,) = _publish(session, seeded, [group]).published
        rows = {row["extended_observation_ref"]: row for row in _rows(
            session, "SELECT * FROM finding_observation WHERE finding_uid = :f", f=finding.finding_uid)}
        assert set(rows) == {"xobs_1", "xobs_2"}
        assert {row["grounding_kind"] for row in rows.values()} == {"portal_block"}
        assert {row["grounded"] for row in rows.values()} == {True}
        assert rows["xobs_1"]["recommendation_text"] == "Уточнить размер по плану."
        assert rows["xobs_2"]["recommendation_text"] == RECOMMENDATION_CHECK_THE_SOURCE
        assert rows["xobs_1"]["finding_observation_id"] == finding.canonical_observation_id
        assert {row["stage_id"] for row in rows.values()} == {STAGE_BLOCK_ANALYSIS}
        assert {row["related_finding_uid"] for row in rows.values()} == {None}
        assert all(row["model_call_id"] is None for row in rows.values()), "a candidate names no model call row, and none is made up"

    def test_the_box_of_a_block_is_the_geometrys_and_the_crop_is_the_one_on_record(self, session: Session, seeded: Any) -> None:
        group = CandidateGroup("xgrp_1", (_member("xobs_1", BLK_A, BLK_C),))
        (finding,) = _publish(session, seeded, [group]).published
        evidence = published_finding_block_evidence(session, seeded.run_id)
        assert [(e.ordinal, e.portal_block_id, e.page_number, e.bbox_norm, e.crop_sha256, e.recognised_quote) for e in evidence] == [
            (0, BLK_A, 2, BOX_A, CROP_A, None),
            (1, BLK_C, 3, BOX_C, CROP_C, None),
        ]
        assert {e.finding_observation_id for e in evidence} == {finding.canonical_observation_id}
        assert finding.block_evidence_count == 2

    def test_a_quote_that_is_verbatim_in_the_recognised_text_is_kept_with_its_block(self, session: Session, seeded: Any) -> None:
        member = CandidateMember("xobs_1", "Размер 3000 мм не сходится.", block_evidence=(_item(BLK_A, quote="3000 мм"),))
        _publish(session, seeded, [CandidateGroup("xgrp_1", (member,))])
        (evidence,) = published_finding_block_evidence(session, seeded.run_id)
        assert evidence.recognised_quote == "3000 мм"


class TestAMixedGroupIsCrossSource:
    def test_blocks_and_a_primary_text_are_one_cross_source_finding_that_names_the_text_finding_it_is_related_to(self, session: Session, seeded: Any) -> None:
        text_finding = FindingUid.new().value
        mixed = CandidateGroup("xgrp_1", (_member("xobs_1", BLK_A, primary_text_ordinals=(3,)), _member("xobs_2", BLK_B)))
        result = _publish(session, seeded, [mixed], primary_findings={3: text_finding})
        (finding,) = result.published
        assert (finding.category, finding.stage_id) == (CATEGORY_CROSS_SOURCE, STAGE_FINDING_MERGE)
        assert finding.related_finding_uid == text_finding
        rows = _rows(session, "SELECT category, stage_id, related_finding_uid FROM finding_observation WHERE finding_uid = :f", f=finding.finding_uid)
        assert {(r["category"], r["stage_id"], r["related_finding_uid"]) for r in rows} == {(CATEGORY_CROSS_SOURCE, STAGE_FINDING_MERGE, text_finding)}
        assert _rows(session, "SELECT category FROM finding WHERE finding_uid = :f", f=finding.finding_uid) == [{"category": CATEGORY_CROSS_SOURCE}]
        group_published_findings(published_findings(session, seeded.run_id))  # one category: the reader takes it

    def test_the_control_the_same_blocks_without_the_text_are_a_drawing_discrepancy(self, session: Session, seeded: Any) -> None:
        (finding,) = _publish(session, seeded, [CandidateGroup("xgrp_1", (_member("xobs_1", BLK_A), _member("xobs_2", BLK_B)))]).published
        assert finding.category == CATEGORY_DRAWING_DISCREPANCY and finding.related_finding_uid is None

    def test_a_primary_text_whose_finding_was_not_published_leaves_the_link_empty_and_still_publishes_the_group(self, session: Session, seeded: Any) -> None:
        mixed = CandidateGroup("xgrp_1", (_member("xobs_1", BLK_A, primary_text_ordinals=(3,)),))
        (finding,) = _publish(session, seeded, [mixed], primary_findings={9: FindingUid.new().value}).published
        assert finding.category == CATEGORY_CROSS_SOURCE and finding.related_finding_uid is None

    def test_a_group_of_blocks_and_another_source_is_cross_source_with_no_link(self, session: Session, seeded: Any) -> None:
        (finding,) = _publish(session, seeded, [CandidateGroup("xgrp_1", (_member("xobs_1", BLK_A, other_source_count=1),))]).published
        assert finding.category == CATEGORY_CROSS_SOURCE and finding.stage_id == STAGE_FINDING_MERGE and finding.related_finding_uid is None


class TestAGroupWhollyOfPrimaryTextsIsNotPublished:
    def test_nothing_is_written_for_it(self, session: Session, seeded: Any) -> None:
        text_path = CandidateGroup("xgrp_1", (CandidateMember("xobs_1", "Высота 3 м.", primary_text_ordinals=(0,)),))
        result = _publish(session, seeded, [text_path], primary_findings={0: FindingUid.new().value})
        assert result.published == () and result.diagnostics == ()
        assert [(s.group_id, s.reason) for s in result.skipped] == [("xgrp_1", SKIP_PRIMARY_TEXT_ONLY)]
        assert published_findings(session, seeded.run_id) == ()
        assert _rows(session, "SELECT count(*) AS n FROM finding_observation WHERE run_id = :r", r=seeded.run_id) == [{"n": 0}]
        assert _rows(session, "SELECT count(*) AS n FROM finding WHERE allocated_by_run_id = :r", r=seeded.run_id) == [{"n": 0}]

    def test_the_control_with_a_block_the_same_group_is_published(self, session: Session, seeded: Any) -> None:
        member = CandidateMember("xobs_1", "Высота 3 м.", block_evidence=(_item(BLK_A),), primary_text_ordinals=(0,))
        result = _publish(session, seeded, [CandidateGroup("xgrp_1", (member,))])
        assert result.published_count == 1 and result.skipped == ()


class TestTheGateDecidesPerObservationSoAGroupIsSplit:
    def test_a_member_the_gate_refuses_is_a_diagnostic_beside_the_finding_not_a_member_of_it(self, session: Session, seeded: Any) -> None:
        bad = _member("xobs_2", BLK_B)
        bad = CandidateMember("xobs_2", bad.finding_text, block_evidence=(_item(BLK_B, crop="0f" * 32),))
        group = CandidateGroup("xgrp_1", (_member("xobs_1", BLK_A), bad, _member("xobs_3", BLK_C)))
        result = _publish(session, seeded, [group])

        (finding,) = result.published
        assert len(finding.observation_ids) == 2
        (diagnostic,) = result.diagnostics
        assert diagnostic.ungrounded_reason == "block_crop_mismatch"
        refused = _rows(session, "SELECT * FROM finding_observation WHERE finding_observation_id = :o", o=diagnostic.finding_observation_id)[0]
        assert refused["finding_uid"] is None and refused["grounded"] is False and refused["extended_observation_ref"] == "xobs_2"
        assert (refused["grounding_kind"], refused["ungrounded_reason"]) == ("portal_block", "block_crop_mismatch")
        # the readers never see it as a finding or as a member; the diagnostic read does
        assert [row.finding_observation_id for row in published_findings(session, seeded.run_id)] == sorted(finding.observation_ids)
        assert published_finding_count(session, seeded.run_id) == 1
        assert _rows(session, "SELECT count(*) AS n FROM finding_block_evidence WHERE finding_observation_id = :o", o=diagnostic.finding_observation_id) == [{"n": 0}]
        group_published_findings(published_findings(session, seeded.run_id))

    def test_when_the_first_member_is_refused_the_next_one_that_passed_is_canonical(self, session: Session, seeded: Any) -> None:
        first = CandidateMember("xobs_1", "Размер не совпадает.", block_evidence=(_item(BLK_A, crop="0f" * 32),))
        second = _member("xobs_2", BLK_B)
        (finding,) = _publish(session, seeded, [CandidateGroup("xgrp_1", (first, second))]).published
        (kept,) = _rows(session, "SELECT finding_observation_id FROM finding_observation WHERE finding_uid = :f", f=finding.finding_uid)
        assert finding.canonical_observation_id == kept["finding_observation_id"] == finding.observation_ids[0]
        assert _rows(session, "SELECT extended_observation_ref FROM finding_observation WHERE finding_observation_id = :o",
                     o=finding.canonical_observation_id) == [{"extended_observation_ref": "xobs_2"}]

    def test_a_group_none_of_whose_members_passes_writes_diagnostics_and_no_finding(self, session: Session, seeded: Any) -> None:
        members = (
            CandidateMember("xobs_1", "Размер.", block_evidence=(_item(BLK_A, crop="0f" * 32),)),
            CandidateMember("xobs_2", "Размер.", block_evidence=(_item(BLK_B, quote="нет такого текста"),)),
        )
        result = _publish(session, seeded, [CandidateGroup("xgrp_1", members)])
        assert result.published == ()
        assert sorted(d.ungrounded_reason for d in result.diagnostics) == ["block_crop_mismatch", "block_quote_not_in_recognised"]
        assert published_findings(session, seeded.run_id) == ()
        assert _rows(session, "SELECT count(*) AS n FROM finding WHERE allocated_by_run_id = :r", r=seeded.run_id) == [{"n": 0}]

    def test_a_block_that_is_not_in_the_runs_geometry_is_refused_and_a_run_with_no_geometry_publishes_nothing(self, session: Session, seeded: Any) -> None:
        group = CandidateGroup("xgrp_1", (_member("xobs_1", BLK_A),))
        assert _publish(session, seeded, [group]).published_count == 1, "the control: the geometry holds the block"
        for inputs in (None, BlockGateInputs.empty()):
            result = _publish(session, seeded, [group], inputs=inputs)
            assert result.published == () and [d.ungrounded_reason for d in result.diagnostics] == ["block_not_in_run_geometry"]

    def test_a_geometry_of_another_version_is_not_this_runs(self, session: Session, seeded: Any, version_uid: str) -> None:
        group = CandidateGroup("xgrp_1", (_member("xobs_1", BLK_A),))
        assert _publish(session, seeded, [group], inputs=_geometry(version_uid)).published_count == 1
        # the views are refused at their own door: another version's document is not built into this run's inputs
        with pytest.raises(DomainError):
            BlockGateInputs.from_artifacts(version_uid=version_uid, **_documents("ver_01M2545JSD15ETSNNV904X991K"))

    def test_a_savepoint_discards_the_whole_call_when_the_database_refuses_a_row(self, session: Session, seeded: Any) -> None:
        good = CandidateGroup("xgrp_1", (_member("xobs_1", BLK_A),))
        # past the constructor's own check, to reach the database's: a text longer than the column holds
        too_long = CandidateMember("xobs_2", "ok", block_evidence=(_item(BLK_B),))
        object.__setattr__(too_long, "finding_text", "я" * 4001)
        with pytest.raises(DomainError):
            _publish(session, seeded, [good, CandidateGroup("xgrp_2", (too_long,))])
        assert published_findings(session, seeded.run_id) == (), "the first group was written in the same savepoint and is gone with it"
        assert _rows(session, "SELECT count(*) AS n FROM finding WHERE allocated_by_run_id = :r", r=seeded.run_id) == [{"n": 0}]


# --------------------------------------------------------------------------------------------
# The decision ledger and the memory
# --------------------------------------------------------------------------------------------


class TestAnExpertDecidesACandidateFinding:
    def test_the_ledger_takes_a_decision_on_its_canonical_observation(self, session: Session, seeded: Any) -> None:
        (finding,) = _publish(session, seeded, [CandidateGroup("xgrp_1", (_member("xobs_1", BLK_A), _member("xobs_2", BLK_B)))]).published
        event = record_decision(
            session, finding_uid=finding.finding_uid, finding_observation_id=finding.canonical_observation_id, event_type="accept",
            comment="Подтверждаю.", author_label="Петрова А.", author_user_uid=None,
        )
        assert event.finding_uid == finding.finding_uid
        assert current_verdict(session, finding.finding_uid).current_verdict == "accepted"


class TestTheMemoryCapturesABlockFinding:
    def test_the_case_is_dm_capture_2_with_the_block_evidence_and_the_crop_of_the_block(self, session: Session, seeded: Any) -> None:
        group = CandidateGroup("xgrp_1", (_member("xobs_1", BLK_A, BLK_C, refined_recommendation="Уточнить по плану."),))
        (finding,) = _publish(session, seeded, [group]).published
        event = record_decision(
            session, finding_uid=finding.finding_uid, finding_observation_id=finding.canonical_observation_id, event_type="accept",
            comment="ок", author_label="Петрова А.", author_user_uid=None,
        )
        head = finding_by_uid(session, finding.finding_uid)
        assert head is not None
        facts = tuple(
            BlockEvidenceFact(ordinal=e.ordinal, page_number=e.page_number, portal_block_id=e.portal_block_id, bbox=e.bbox_norm,
                              crop_sha256=e.crop_sha256, recognised_quote=e.recognised_quote)
            for e in published_finding_block_evidence(session, seeded.run_id)
        )
        blob = str(derive_blob_id(sha256="b" * 64, size=4096))
        session.execute(text("INSERT INTO blob (blob_id) VALUES (:b)"), {"b": blob})
        records = [
            {"portal_block_id": block, "page_number": page, "bbox_norm": list(box), "blob_id": blob, "sha256": sha, "size_bytes": 4096,
             "width_px": 900, "height_px": 700}
            for block, page, box, sha in ((BLK_A, 2, BOX_A, CROP_A), (BLK_B, 2, BOX_B, CROP_B), (BLK_C, 3, BOX_C, CROP_C))
        ]
        crops = select_case_crops((), facts, records)
        assert [(c.source_ref, c.evidence_ordinal, c.selection_rule) for c in crops] == [(BLK_A, 0, "block_crop/1"), (BLK_C, 1, "block_crop/1")]

        content = CaseContent(
            category=head.category, finding_text=head.finding_text, recommendation_text=head.recommendation_text, proposed_severity=None,
            required_value=None, stated_value=None, stage_id=head.stage_id, analysis_profile_id=head.analysis_profile_id,
            prompt_bundle_id=head.prompt_bundle_id, provider_mode=head.provider_mode, evidence=(), norm_refs=(), block_evidence=facts,
        )
        snapshot = CaptureSnapshot(
            origin=CaseOrigin(observation_id=head.finding_observation_id, finding_uid=head.finding_uid, project_uid=head.project_uid,
                              document_uid=seeded.document_uid, version_uid=head.version_uid, run_id=head.run_id),
            content=content, section_code=None, data_class="test", crops=crops,
            decision=DecisionFact(source_decision_id=event.decision_id, event_type="accept", severity=None, comment="ок", author_user_uid=None,
                                  origin_kind="direct", decided_at=event.recorded_at),
        )
        result = MemoryRepository().capture(session, snapshot)
        assert result.case_created and result.decision_created

        case = _rows(session, "SELECT * FROM decision_memory_case WHERE case_id = :c", c=result.case_id)[0]
        assert case["capture_version"] == CAPTURE_VERSION_BLOCK_EVIDENCE == "dm-capture/2"
        assert case["category"] == CATEGORY_DRAWING_DISCREPANCY and case["crop_state"] == "referenced"
        stored = _rows(session, "SELECT * FROM decision_memory_block_evidence WHERE case_id = :c ORDER BY ordinal", c=result.case_id)
        assert [(r["ordinal"], r["page_number"], r["portal_block_id"], (r["bbox_x0"], r["bbox_y0"], r["bbox_x1"], r["bbox_y1"]), r["crop_sha256"])
                for r in stored] == [(0, 2, BLK_A, BOX_A, CROP_A), (1, 3, BLK_C, BOX_C, CROP_C)]
        assert _rows(session, "SELECT count(*) AS n FROM decision_memory_evidence WHERE case_id = :c", c=result.case_id) == [{"n": 0}]
        stored_crops = _rows(session, "SELECT source_ref, selection_rule FROM decision_memory_crop WHERE case_id = :c ORDER BY crop_ordinal", c=result.case_id)
        assert [(r["source_ref"], r["selection_rule"]) for r in stored_crops] == [(BLK_A, "block_crop/1"), (BLK_C, "block_crop/1")]

        # a replay is idempotent, and a later decision handed the same block evidence is the same case (no conflict)
        again = MemoryRepository().capture(session, snapshot)
        assert not again.case_created and not again.decision_created and again.case_id == result.case_id

    def test_the_control_a_text_finding_is_still_dm_capture_1_and_has_no_block_evidence(self, session: Session, seeded: Any) -> None:
        # the same repository, a case without block evidence: the old version and the old rows
        content = CaseContent(
            category="internal_contradiction", finding_text="Текст", recommendation_text="Рекомендация", proposed_severity=None,
            required_value=None, stated_value=None, stage_id="text_analysis", analysis_profile_id=seeded.analysis_profile_id,
            prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="recorded", evidence=(), norm_refs=(),
        )
        from auditmanager.shared.identity import DecisionId

        snapshot = CaptureSnapshot(
            origin=CaseOrigin(observation_id=FindingObservationId.new().value, finding_uid=FindingUid.new().value,
                              project_uid=seeded.project_uid, document_uid=seeded.document_uid, version_uid=seeded.version_uid, run_id=seeded.run_id),
            content=content, section_code=None, data_class="test", crops=(),
            decision=DecisionFact(source_decision_id=DecisionId.new().value, event_type="accept", severity=None, comment=None,
                                  author_user_uid=None, origin_kind="direct", decided_at=_now()),
        )
        result = MemoryRepository().capture(session, snapshot)
        assert _rows(session, "SELECT capture_version FROM decision_memory_case WHERE case_id = :c", c=result.case_id) == [{"capture_version": "dm-capture/1"}]
        assert _rows(session, "SELECT count(*) AS n FROM decision_memory_block_evidence WHERE case_id = :c", c=result.case_id) == [{"n": 0}]


def _now():  # type: ignore[no-untyped-def]
    from datetime import datetime, timezone

    return datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------------------------
# The executor: a one_list run publishes its candidates after its text findings; a text_only run does not
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


def _executor_world(corpus: Any, seeded: Any) -> tuple[_Store, _StageOutputs, dict[str, str]]:
    """A run's saved artifacts: the corpus text layer and block index, the three geometry documents and a v2 extended review."""
    store, outputs, blobs = _Store(), _StageOutputs(), {}
    saved = _documents(seeded.version_uid)
    documents = {
        ROLE_TEXT_LAYER: corpus.text_layer_artifact, ROLE_BLOCK_INDEX: corpus.block_index_artifact,
        ROLE_PORTAL_BLOCKS: saved["portal_blocks"], ROLE_PAGE_CROPS: saved["page_crops"], ROLE_RECOGNISED_TEXT: saved["recognised_text"],
    }
    sources = [
        {"source_id": BLK_A, "kind": "image", "page_number": 2, "bbox_norm": list(BOX_A), "crop_sha256": CROP_A},
        {"source_id": BLK_B, "kind": "image", "page_number": 2, "bbox_norm": list(BOX_B), "crop_sha256": CROP_B},
        {"source_id": BLK_C, "kind": "image", "page_number": 3, "bbox_norm": list(BOX_C), "crop_sha256": CROP_C},
        {"source_id": "text:0", "kind": "text", "page_number": 1, "quote": "x"},
    ]

    def candidate(ref: str, source_ids: list[str], description: str) -> dict[str, Any]:
        return {"observation_id": ref, "title": "Размер", "description": description, "source_ids": source_ids, "norm_queries": []}

    review = extended_artifact_envelope(
        "analysis.extended_review", seeded.version_uid, run_id=seeded.run_id, status="completed",
        result={"workflow_version": "extended-review-v2", "version_uid": seeded.version_uid, "sources": sources, "observations": [
            candidate("xobs_1", [BLK_A], "Размер не совпадает с планом."),
            candidate("xobs_2", [BLK_A, BLK_B], "Размер не совпадает с планом."),     # one group with xobs_1: the same words, a shared block
            candidate("xobs_3", [BLK_C, "text:0"], "Высота не совпадает."),           # blocks and a primary text: a mixed group
            candidate("xobs_4", ["text:0"], "Степень огнестойкости."),                # the text path's own: not published again
        ]},
    )
    documents["analysis.extended_review"] = review
    for role, document in documents.items():
        reference, _ = publish_artifact(store, role, document)
        outputs.refs[role] = reference
        blobs[role] = str(reference.blob_id)
    return store, outputs, blobs


def _text_observations(corpus: Any, seeded: Any) -> dict[str, Any]:
    """``analysis.text_observations`` with one grounded text observation: the first seeded anchor of the corpus, verbatim."""
    anchor = corpus.seeded_anchors()[0]
    evidence = {"evidence_ordinal": 0, "page_number": anchor["page_number"], "quote": anchor["quote"],
                "char_start": anchor["char_start"], "char_end": anchor["char_end"]}
    if anchor.get("block_id") is not None:
        evidence["block_id"] = anchor["block_id"]
    return {
        "artifact_role": "analysis.text_observations", "artifact_version": "1.0.0", "run_id": seeded.run_id, "stage_id": "text_analysis",
        "analysis_profile_id": seeded.analysis_profile_id, "prompt_bundle_id": seeded.prompt_bundle_id, "provider_mode": "recorded",
        "pages_analysed": [1],
        "observations": [{"observation_ordinal": 0, "category": anchor["category"], "finding_text": "Степень огнестойкости указана по-разному.",
                          "recommendation_text": "Согласовать.", "model_call_id": None, "evidence": [evidence]}],
    }


def _run_row(seeded: Any) -> Any:
    return SimpleNamespace(
        run_id=seeded.run_id, project_uid=seeded.project_uid, version_uid=seeded.version_uid, analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="recorded",
    )


class TestTheExecutorPublishesCandidatesOnlyForAOneListRun:
    def test_a_one_list_run_publishes_its_text_finding_and_then_its_candidates(self, session: Session, seeded: Any, corpus: Any) -> None:
        store, outputs, _ = _executor_world(corpus, seeded)
        observations = _text_observations(corpus, seeded)
        inputs = _read_gate_inputs(
            observations_document=observations, outputs=outputs, blob_store=store, publication_mode="one_list",
            run_id=seeded.run_id, version_uid=seeded.version_uid,
        )
        assert inputs is not None and inputs.block_inputs is not None
        assert [len(g.members) for g in inputs.candidate_groups] == [2, 1, 1] and inputs.candidates_unread == ()

        gate_ran, publication = _run_evidence_gate(session, run=_run_row(seeded), inputs=inputs)
        assert gate_ran and publication is not None and publication.candidates is not None
        (text_finding,) = publication.published
        candidates = publication.candidates
        assert publication.published_count == 3 == len(publication.finding_uids), "the run's count is the text finding and the two candidate findings"
        assert [(f.category, f.stage_id, len(f.observation_ids)) for f in candidates.published] == [
            (CATEGORY_DRAWING_DISCREPANCY, STAGE_BLOCK_ANALYSIS, 2),
            (CATEGORY_CROSS_SOURCE, STAGE_FINDING_MERGE, 1),
        ]
        mixed = candidates.published[1]
        assert mixed.related_finding_uid == text_finding.finding_uid, "the text observation `text:0` is the run's own text finding"
        assert [(s.group_id[:5], s.reason) for s in candidates.skipped] == [("xgrp_", SKIP_PRIMARY_TEXT_ONLY)]

        # one run, three findings, and every reader takes them
        rows = published_findings(session, seeded.run_id)
        assert {row.finding_uid for row in rows} == set(publication.finding_uids)
        assert len(group_published_findings(rows)) == 3 and published_finding_count(session, seeded.run_id) == 3
        assert {row.category for row in rows} >= {CATEGORY_DRAWING_DISCREPANCY, CATEGORY_CROSS_SOURCE}

    def test_a_text_only_run_publishes_exactly_as_before_and_does_not_read_the_review(self, session: Session, seeded: Any, corpus: Any) -> None:
        store, outputs, blobs = _executor_world(corpus, seeded)
        observations = _text_observations(corpus, seeded)
        inputs = _read_gate_inputs(observations_document=observations, outputs=outputs, blob_store=store, publication_mode="text_only")
        assert inputs is not None and inputs.block_inputs is None and inputs.candidate_groups == () and inputs.block_documents is None
        assert blobs["analysis.extended_review"] not in store.reads, "a text_only run never opens the saved review"

        _, publication = _run_evidence_gate(session, run=_run_row(seeded), inputs=inputs)
        assert publication is not None and publication.candidates is None
        assert publication.published_count == 1 and len(published_findings(session, seeded.run_id)) == 1
        assert _rows(session, "SELECT count(*) AS n FROM finding_block_evidence") == [{"n": 0}]
        assert _rows(session, "SELECT DISTINCT grounding_kind FROM finding_observation WHERE run_id = :r", r=seeded.run_id) == [{"grounding_kind": "text_span"}]

    def test_the_text_publication_of_a_text_only_run_is_the_one_publish_gate_result_makes(
        self, session: Session, seeded: Any, corpus: Any, text_layer: Any, block_index: Any, observations_builder: Any
    ) -> None:
        anchor = corpus.seeded_anchors()[0]
        item = {"category": anchor["category"], "finding_text": "Степень огнестойкости указана по-разному.", "evidence": [anchor]}
        observation_set = observations_builder(seeded, [item])
        direct = publish_gate_result(
            session, gate_result=run_grounding_gate(observation_set, text_layer, block_index), observation_set=observation_set,
            run_id=seeded.run_id, project_uid=seeded.project_uid, version_uid=seeded.version_uid,
        )
        assert direct.candidates is None and direct.published_count == len(direct.published) == 1
        assert direct.diagnostic_count == len(direct.diagnostics) and direct.finding_uids == tuple(p.finding_uid for p in direct.published)

    def test_a_one_list_run_with_no_text_observations_still_reaches_the_block_gate(self, session: Session, seeded: Any, corpus: Any) -> None:
        store, outputs, _ = _executor_world(corpus, seeded)
        empty = {**_text_observations(corpus, seeded), "observations": []}
        inputs = _read_gate_inputs(
            observations_document=empty, outputs=outputs, blob_store=store, publication_mode="one_list",
            run_id=seeded.run_id, version_uid=seeded.version_uid,
        )
        assert inputs is not None
        gate_ran, publication = _run_evidence_gate(session, run=_run_row(seeded), inputs=inputs)
        assert gate_ran and publication is not None and publication.published == ()
        assert publication.candidates is not None and publication.candidates.published_count == 2
        assert all(f.related_finding_uid is None for f in publication.candidates.published)

    def test_a_one_list_run_whose_review_was_not_saved_says_so_and_publishes_only_its_text(self, session: Session, seeded: Any, corpus: Any) -> None:
        store, outputs, _ = _executor_world(corpus, seeded)
        del outputs.refs["analysis.extended_review"]
        inputs = _read_gate_inputs(
            observations_document=_text_observations(corpus, seeded), outputs=outputs, blob_store=store, publication_mode="one_list",
            run_id=seeded.run_id, version_uid=seeded.version_uid,
        )
        assert inputs is not None and inputs.candidate_groups == () and inputs.candidates_unread == ("extended_review_absent",)
        _, publication = _run_evidence_gate(session, run=_run_row(seeded), inputs=inputs)
        assert publication is not None and publication.candidates is not None
        assert publication.candidates.unread == ("extended_review_absent",) and publication.published_count == 1

    def test_a_one_list_run_is_read_with_its_run_and_version_and_not_without(self, corpus: Any, seeded: Any) -> None:
        store, outputs, _ = _executor_world(corpus, seeded)
        with pytest.raises(ValueError):
            _read_gate_inputs(observations_document=_text_observations(corpus, seeded), outputs=outputs, blob_store=store, publication_mode="one_list")

    def test_a_geometry_of_another_version_fails_before_any_lock(self, corpus: Any, seeded: Any) -> None:
        store, outputs, _ = _executor_world(corpus, seeded)
        with pytest.raises(DomainError) as caught:
            _read_gate_inputs(
                observations_document=_text_observations(corpus, seeded), outputs=outputs, blob_store=store, publication_mode="one_list",
                run_id=seeded.run_id, version_uid="ver_01M2545JSD15ETSNNV904X991K",
            )
        assert caught.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
