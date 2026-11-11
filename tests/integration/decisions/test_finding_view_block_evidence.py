"""`CRIT-SEAL-50` (contract 1.51.0), wired by `CRIT-CAPTURE-01` part B: the API view of a finding carries its blocks, its origin and its grounding.

On a real database, through the composition root's own ``FindingAdapter`` (the port the routers call) and the wire bodies the routers
render, with the findings really published (the suite's ``published`` fixture for the text findings, ``publish_candidate_groups`` for the
candidates). The bodies are also validated by the contract's own models.

* a block finding lists its canonical observation's blocks (place, box, crop digest, quote), ``origin = drawing`` and ``grounding_kind =
  portal_block``; a finding of a drawing and another source is ``cross_check``; a drawing group merged across windows is still ``drawing``
  (its stage is ``finding_merge``, its category is not ``cross_source``);
* a text finding's body is what it was: the three new members are **omitted** (the contract's "absent means text / text_span"), not empty;
* the detail read carries the same, and a merged member's blocks are not the finding's own.
"""

from __future__ import annotations

from typing import Any

import pydantic
import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.schemas import models
from auditmanager.api.schemas.findings import finding_body, finding_detail_body
from auditmanager.bootstrap.adapters import FindingAdapter
from auditmanager.findings import (
    BlockEvidenceItem,
    BlockGateInputs,
    CandidateGroup,
    CandidateMember,
    publish_candidate_groups,
)
from auditmanager.findings.artifacts import PAGE_CROPS_ROLE, PORTAL_BLOCKS_ROLE, RECOGNISED_TEXT_ROLE

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


def _member(ref: str, *blocks: str, quote: str | None = None, **extra: Any) -> CandidateMember:
    items = tuple(
        BlockEvidenceItem(
            evidence_ordinal=position, page_number=PAGES[block][0], portal_block_id=block, crop_sha256=PAGES[block][2],
            recognised_quote=quote if block == BLK_A else None,
        )
        for position, block in enumerate(blocks)
    )
    return CandidateMember(extended_observation_ref=ref, finding_text=f"Размер не совпадает с планом ({ref}).", block_evidence=items, **extra)


def _publish_blocks(session: Session, published: Any, *members: CandidateMember) -> Any:
    result = publish_candidate_groups(
        session, groups=[CandidateGroup("xgrp_1", members)],
        gate_inputs=BlockGateInputs.from_artifacts(version_uid=published.version_uid, **_documents(published.version_uid)),
        run_id=published.run_id, project_uid=published.project_uid, version_uid=published.version_uid,
        analysis_profile_id=published.analysis_profile_id, prompt_bundle_id=published.prompt_bundle_id, provider_mode="recorded",
    )
    (finding,) = result.published
    return finding


@pytest.fixture
def adapter(session: Session) -> FindingAdapter:
    connection = session.get_bind()
    return FindingAdapter(sessionmaker(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False))


def _contract_gaps(model: Any, body: dict[str, Any]) -> list[tuple[Any, ...]]:
    """What the contract's own model refuses in a body, as the locations of the refusals (empty: the body is conformant).

    A block finding has **no text evidence** (`F8-PUBLISH`: it stands on blocks), so its ``observation.evidence`` is ``[]``, and contract 1.51.0 said
    ``Evidence`` has ``minItems: 1``; 1.52.0 (D-683) lets a ``portal_block`` observation carry an empty ``evidence``, so a block finding's body
    is now conformant, and the tests pin that nothing is refused.
    """
    try:
        model.model_validate(body)
    except pydantic.ValidationError as error:
        assert all(item["type"] == "too_short" for item in error.errors()), error.errors()
        return [tuple(item["loc"]) for item in error.errors()]
    return []


def _by_uid(views: Any) -> dict[str, Any]:
    return {view.finding_uid: view for view in views}


def test_a_block_finding_lists_its_blocks_its_origin_and_its_grounding(session: Session, published: Any, adapter: FindingAdapter) -> None:
    finding = _publish_blocks(session, published, _member("xobs_1", BLK_C, BLK_A, quote=RECOGNISED_A))

    view = _by_uid(adapter.list_run_findings(run_id=published.run_id))[finding.finding_uid]

    assert view.category == "drawing_discrepancy" and view.origin == "drawing"
    assert view.observation.grounding_kind == "portal_block"
    assert [(b.ordinal, b.page_number, b.portal_block_id, b.bbox_norm, b.crop_sha256, b.recognised_quote) for b in view.block_evidence or ()] == [
        (0, 3, BLK_C, BOX_C, CROP_C, None), (1, 2, BLK_A, BOX_A, CROP_A, RECOGNISED_A)]   # in the order of the evidence, as the publisher wrote it

    body = finding_body(view)
    assert body["origin"] == "drawing" and body["observation"]["grounding_kind"] == "portal_block"
    assert body["block_evidence"][1] == {
        "ordinal": 1, "page_number": 2, "portal_block_id": BLK_A, "bbox_norm": {"x0": 0.1, "y0": 0.2, "x1": 0.6, "y1": 0.7},
        "crop_sha256": CROP_A, "recognised_quote": RECOGNISED_A}
    assert "recognised_quote" not in body["block_evidence"][0]                                # absent, not null: the contract has no null here
    assert body["observation"]["evidence"] == []                                              # a block finding has no text evidence
    assert [models.FindingBlockEvidence.model_validate(item) for item in body["block_evidence"]]  # each block is conformant by itself
    assert _contract_gaps(models.Finding, body) == []                                          # 1.52.0 (D-683): a block observation may carry no text evidence


def test_a_text_findings_body_is_what_it_was_the_new_members_are_omitted_not_empty(
    session: Session, published: Any, adapter: FindingAdapter
) -> None:
    _publish_blocks(session, published, _member("xobs_1", BLK_A))                             # the run also holds a block finding

    views = _by_uid(adapter.list_run_findings(run_id=published.run_id))
    text_view = views[published.finding_uid]

    assert text_view.block_evidence is None and text_view.origin is None and text_view.observation.grounding_kind is None
    body = finding_body(text_view)
    assert "block_evidence" not in body and "origin" not in body and "grounding_kind" not in body["observation"]
    assert _contract_gaps(models.Finding, body) == []                                          # a text finding is conformant, as before
    assert {"block_evidence", "origin"} <= set(finding_body(next(v for v in views.values() if v.origin == "drawing")))   # the control: the same builder emits them


def test_a_finding_of_a_drawing_and_another_source_is_a_cross_check_and_a_cross_window_drawing_is_still_a_drawing(
    session: Session, published: Any, adapter: FindingAdapter
) -> None:
    mixed = _publish_blocks(session, published, _member("xobs_1", BLK_A, other_source_count=1))
    assert (mixed.category, mixed.stage_id) == ("cross_source", "finding_merge")
    assert _by_uid(adapter.list_run_findings(run_id=published.run_id))[mixed.finding_uid].origin == "cross_check"

    across = _publish_blocks(session, published, _member("xobs_2", BLK_B, cross_window=True))
    assert (across.category, across.stage_id) == ("drawing_discrepancy", "finding_merge")    # the stage alone would say cross_check
    view = _by_uid(adapter.list_run_findings(run_id=published.run_id))[across.finding_uid]
    assert view.origin == "drawing"
    assert _contract_gaps(models.Finding, finding_body(view)) == []  # 1.52.0 (D-683)


def test_the_detail_read_carries_the_canonicals_blocks_and_a_merged_members_are_not_the_findings_own(
    session: Session, published: Any, adapter: FindingAdapter
) -> None:
    finding = _publish_blocks(session, published, _member("xobs_1", BLK_A, BLK_C), _member("xobs_2", BLK_B))

    detail = adapter.get_finding(finding_uid=finding.finding_uid)

    assert detail.finding.origin == "drawing"
    assert [b.portal_block_id for b in detail.finding.block_evidence or ()] == [BLK_A, BLK_C]   # not B: that is the merged member's
    assert detail.finding.merged_observations is not None and len(detail.finding.merged_observations) == 1
    assert detail.finding.merged_observations[0].grounding_kind == "portal_block"
    body = finding_detail_body(detail)
    assert [b["portal_block_id"] for b in body["block_evidence"]] == [BLK_A, BLK_C] and body["merged_observations"][0]["grounding_kind"] == "portal_block"
    assert _contract_gaps(models.FindingDetail, body) == []  # 1.52.0 (D-683): neither the canonical nor a merged block observation is refused

    text_detail = adapter.get_finding(finding_uid=published.finding_uid)
    assert text_detail.finding.block_evidence is None and text_detail.finding.origin is None
    text_body = finding_detail_body(text_detail)
    assert "block_evidence" not in text_body and "origin" not in text_body
