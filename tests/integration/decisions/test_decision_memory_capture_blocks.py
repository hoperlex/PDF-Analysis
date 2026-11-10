"""`ADR-0029` decision 7 (`CRIT-CAPTURE-01`, part B): the capture of a block finding is ``dm-capture/2``, through the ledger's port.

`F8-PUBLISH` proved the memory's side (``MemoryRepository.capture`` of a ``CaseContent`` with block evidence, ``select_case_crops``). What is
shown here is the WIRING, on a real database, with the composition root's own assembler registered as the ledger's port and only the
published artifacts (the portal crop manifest) replaced by a recording double:

* a ✓ on a candidate (block) finding writes a ``dm-capture/2`` case with its block evidence, no text evidence, and the crop **of the block**
  (rule ``block_crop/1``); the blocks of another member of the group, and of another finding of the run, are not its own;
* a second decision on the same finding is the same case and does not conflict -- and the control: the same second decision handed NO block
  evidence is the conflict the rule exists to prevent, so the test can fail;
* a text finding of the same run stays ``dm-capture/1`` with the digest of its content, whatever block findings the run holds;
* the sweep repairs a block finding decided without the port as ``dm-capture/2`` too.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.bootstrap.adapters import MemoryCaptureAssembler, MemoryCaptureSweep
from auditmanager.decision_memory.public import CAPTURE_VERSION, CAPTURE_VERSION_BLOCK_EVIDENCE, content_digest
from auditmanager.decisions import record_decision
from auditmanager.decisions.public import register_decision_recorded, registered_decision_recorded
from auditmanager.findings import (
    BlockEvidenceItem,
    BlockGateInputs,
    CandidateGroup,
    CandidateMember,
    publish_candidate_groups,
)
from auditmanager.findings.artifacts import PAGE_CROPS_ROLE, PORTAL_BLOCKS_ROLE, RECOGNISED_TEXT_ROLE
from auditmanager.shared.errors import DomainError, ErrorCode
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
PAGES = {BLK_A: (2, BOX_A, CROP_A), BLK_B: (2, BOX_B, CROP_B), BLK_C: (3, BOX_C, CROP_C)}


class _Geometry:
    """Stands for the object store: the portal crop manifest of the run, and how often the artifacts were asked."""

    def __init__(self) -> None:
        self.boxes_reads = 0
        self.crop_reads = 0
        self.crops: tuple[dict[str, Any], ...] = ()

    def evidence_boxes_in(self, session: Session, run_id: str) -> dict[str, Any]:
        self.boxes_reads += 1
        return {}

    def portal_crops_in(self, session: Session, run_id: str) -> tuple[dict[str, Any], ...]:
        self.crop_reads += 1
        return self.crops


@pytest.fixture
def memory(session: Session) -> Iterator[SimpleNamespace]:
    geometry = _Geometry()
    blob = str(derive_blob_id(sha256="b" * 64, size=4096))
    session.execute(text("INSERT INTO blob (blob_id) VALUES (:b)"), {"b": blob})
    geometry.crops = tuple(
        {"portal_block_id": block, "page_number": page, "bbox_norm": list(box), "blob_id": blob, "sha256": sha, "size_bytes": 4096,
         "width_px": 900, "height_px": 700, "portal_description": f"Чертёж {block[4:8]}"}
        for block, (page, box, sha) in PAGES.items()
    )
    assembler = MemoryCaptureAssembler(geometry=geometry)
    before = registered_decision_recorded()
    register_decision_recorded(assembler)
    try:
        yield SimpleNamespace(geometry=geometry, assembler=assembler)
    finally:
        register_decision_recorded(before)


def _documents(version: str) -> dict[str, dict[str, Any]]:
    return {
        "portal_blocks": {
            "artifact_role": PORTAL_BLOCKS_ROLE, "artifact_version": "1.0.0", "version_uid": version, "blocks_sha256": "e" * 64, "pages": [],
            "blocks": [{"portal_block_id": b, "page_number": p, "block_type": "image", "bbox_norm": list(box)} for b, (p, box, _) in PAGES.items()],
        },
        "page_crops": {
            "artifact_role": PAGE_CROPS_ROLE, "artifact_version": "1.0.0", "version_uid": version, "crop_policy": "portal_image_blocks",
            "crops": [{"portal_block_id": b, "page_number": p, "sha256": sha} for b, (p, _, sha) in PAGES.items()],
        },
        "recognised_text": {
            "artifact_role": RECOGNISED_TEXT_ROLE, "artifact_version": "1.0.0", "version_uid": version, "results_sha256": "f" * 64,
            "entries": [{"portal_block_id": BLK_A, "page_number": 2, "kind": "recognised_text", "text": RECOGNISED_A}],
        },
    }


def _member(ref: str, *blocks: str, quote: str | None = None) -> CandidateMember:
    items = tuple(
        BlockEvidenceItem(
            evidence_ordinal=position, page_number=PAGES[block][0], portal_block_id=block, crop_sha256=PAGES[block][2],
            recognised_quote=quote if block == BLK_A else None,
        )
        for position, block in enumerate(blocks)
    )
    return CandidateMember(extended_observation_ref=ref, finding_text=f"Размер не совпадает с планом ({ref}).", block_evidence=items)


def _publish_blocks(session: Session, published: Any, *members: CandidateMember) -> Any:
    """One candidate finding on the run the suite's ``published`` fixture already holds (two text findings and a diagnostic)."""
    result = publish_candidate_groups(
        session, groups=[CandidateGroup("xgrp_1", members)], gate_inputs=BlockGateInputs.from_artifacts(version_uid=published.version_uid, **_documents(published.version_uid)),
        run_id=published.run_id, project_uid=published.project_uid, version_uid=published.version_uid,
        analysis_profile_id=published.analysis_profile_id, prompt_bundle_id=published.prompt_bundle_id, provider_mode="recorded",
    )
    (finding,) = result.published
    return finding


def _accept(session: Session, finding_uid: str, observation_id: str, event_type: str = "accept", comment: str | None = "ок") -> Any:
    return record_decision(
        session, finding_uid=finding_uid, finding_observation_id=observation_id, event_type=event_type, comment=comment,
        author_label="Петрова А.", author_user_uid=None,
    )


def _count(session: Session, table: str, where: str = "true", **parameters: Any) -> int:
    return int(session.execute(text(f"SELECT count(*) FROM {table} WHERE {where}"), parameters).scalar_one())


def test_a_check_on_a_block_finding_writes_a_dm_capture_2_case_with_its_block_evidence_and_the_crop_of_its_block(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    # Two members: the canonical stands on A and C, the merged one on B. The decision is on the canonical observation.
    finding = _publish_blocks(session, published, _member("xobs_1", BLK_A, BLK_C, quote=RECOGNISED_A), _member("xobs_2", BLK_B))
    assert len(finding.observation_ids) == 2

    event = _accept(session, finding.finding_uid, finding.canonical_observation_id)

    case = session.execute(text("SELECT * FROM decision_memory_case")).mappings().one()
    assert case["origin_observation_id"] == finding.canonical_observation_id and case["origin_finding_uid"] == finding.finding_uid
    assert case["capture_version"] == CAPTURE_VERSION_BLOCK_EVIDENCE == "dm-capture/2"
    assert case["category"] == "drawing_discrepancy" and case["crop_state"] == "referenced"

    stored = session.execute(
        text("SELECT ordinal, page_number, portal_block_id, bbox_x0, bbox_y0, bbox_x1, bbox_y1, crop_sha256, recognised_quote "
             "FROM decision_memory_block_evidence ORDER BY ordinal")
    ).all()
    assert [(r.ordinal, r.page_number, r.portal_block_id, (r.bbox_x0, r.bbox_y0, r.bbox_x1, r.bbox_y1), r.crop_sha256, r.recognised_quote) for r in stored] == [
        (0, 2, BLK_A, BOX_A, CROP_A, RECOGNISED_A), (1, 3, BLK_C, BOX_C, CROP_C, None)]   # the canonical's own blocks: not B, the merged member's
    assert _count(session, "decision_memory_evidence") == 0                              # a block finding has no text evidence

    crops = session.execute(text("SELECT crop_ordinal, evidence_ordinal, source_ref, selection_rule, page_number, portal_description "
                                 "FROM decision_memory_crop ORDER BY crop_ordinal")).all()
    assert [tuple(r) for r in crops] == [(1, 0, BLK_A, "block_crop/1", 2, "Чертёж aaaa"), (2, 1, BLK_C, "block_crop/1", 3, "Чертёж cccc")]

    decision = session.execute(text("SELECT source_decision_id, verdict, origin_kind FROM decision_memory_decision")).one()
    assert tuple(decision) == (event.decision_id, "accepted", "direct")
    assert (memory.geometry.crop_reads, memory.geometry.boxes_reads) == (1, 0)           # the crops are read once; no block index (no text anchor)


def test_a_second_decision_on_the_same_block_finding_is_the_same_case_and_does_not_conflict(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    finding = _publish_blocks(session, published, _member("xobs_1", BLK_A, BLK_C))
    first = _accept(session, finding.finding_uid, finding.canonical_observation_id, "accept")
    reads = (memory.geometry.crop_reads, memory.geometry.boxes_reads)

    second = _accept(session, finding.finding_uid, finding.canonical_observation_id, "reject", "пересмотрено")   # no CONFLICT

    assert _count(session, "decision_memory_case") == 1 and _count(session, "decision_memory_decision") == 2
    assert _count(session, "decision_memory_block_evidence") == 2 and _count(session, "decision_memory_crop") == 2   # the first capture's, not doubled
    verdicts = session.execute(text("SELECT source_decision_id, verdict FROM decision_memory_decision ORDER BY captured_at")).all()
    assert [tuple(r) for r in verdicts] == [(first.decision_id, "accepted"), (second.decision_id, "rejected")]
    assert (memory.geometry.crop_reads, memory.geometry.boxes_reads) == reads            # a known case reads no artifact
    assert session.execute(text("SELECT capture_version FROM decision_memory_case")).scalar_one() == "dm-capture/2"


def test_the_control_a_later_decision_handed_no_block_evidence_is_a_conflict(
    session: Session, published: Any, memory: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Why the assembler hands the block evidence on EVERY capture: without it the digest differs from the stored one. This is the failure
    the previous test would show if the wiring only handed it with a new case."""
    import auditmanager.findings as findings_module

    finding = _publish_blocks(session, published, _member("xobs_1", BLK_A, BLK_C))
    _accept(session, finding.finding_uid, finding.canonical_observation_id, "accept")

    monkeypatch.setattr(findings_module, "published_finding_block_evidence", lambda s, run_id: ())
    savepoint = session.begin_nested()
    with pytest.raises(DomainError) as refused:
        _accept(session, finding.finding_uid, finding.canonical_observation_id, "reject", "пересмотрено")
    savepoint.rollback()
    assert refused.value.code is ErrorCode.CONFLICT
    assert _count(session, "decision_memory_decision") == 1 and _count(session, "expert_decision_event") == 1   # the decision failed with it


def test_a_text_finding_of_the_same_run_stays_dm_capture_1_with_the_digest_of_its_content(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    """The run holds a block finding, so ``published_finding_block_evidence(run)`` is not empty; the text finding must not take any of it."""
    block_finding = _publish_blocks(session, published, _member("xobs_1", BLK_A))
    assert _count(session, "finding_block_evidence") == 1

    event = _accept(session, published.finding_uid, published.finding_observation_id)

    case = session.execute(text("SELECT * FROM decision_memory_case")).mappings().one()
    assert case["origin_observation_id"] == published.finding_observation_id != block_finding.canonical_observation_id
    assert case["capture_version"] == CAPTURE_VERSION == "dm-capture/1"
    assert _count(session, "decision_memory_block_evidence") == 0 and _count(session, "decision_memory_evidence") == 2
    snapshot = memory.assembler.assemble(session, event, "direct")
    assert snapshot.content.block_evidence == ()
    assert case["content_sha256"] == content_digest(snapshot.content)                    # the digest of the content alone, as before
    rules = {row.selection_rule for row in session.execute(text("SELECT selection_rule FROM decision_memory_crop"))}
    assert rules == {"page_images/1"}                                                    # the old rule, never the block's


def test_the_sweep_repairs_a_block_finding_decided_without_the_port_as_dm_capture_2(
    session: Session, published: Any, memory: SimpleNamespace
) -> None:
    register_decision_recorded(None)                                                     # the `memory` fixture puts the port back afterwards
    finding = _publish_blocks(session, published, _member("xobs_1", BLK_A, BLK_C))
    event = _accept(session, finding.finding_uid, finding.canonical_observation_id)
    assert _count(session, "decision_memory_case") == 0

    connection = session.get_bind()
    factory = lambda: Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)  # noqa: E731
    sweep = MemoryCaptureSweep(factory, MemoryCaptureAssembler(geometry=memory.geometry), batch=500)
    report = sweep.run_once()
    assert report.captured >= 1 and report.failed == 0

    case = session.execute(
        text("SELECT c.capture_version, c.case_id FROM decision_memory_case c WHERE c.origin_observation_id = :o"),
        {"o": finding.canonical_observation_id},
    ).one()
    assert case.capture_version == "dm-capture/2"
    blocks = session.execute(text("SELECT portal_block_id FROM decision_memory_block_evidence WHERE case_id = :c ORDER BY ordinal"), {"c": case.case_id}).all()
    assert [r.portal_block_id for r in blocks] == [BLK_A, BLK_C]
    assert _count(session, "decision_memory_decision", "source_decision_id = :d", d=event.decision_id) == 1
    crops = session.execute(text("SELECT source_ref, selection_rule FROM decision_memory_crop WHERE case_id = :c ORDER BY crop_ordinal"), {"c": case.case_id}).all()
    assert [tuple(r) for r in crops] == [(BLK_A, "block_crop/1"), (BLK_C, "block_crop/1")]
