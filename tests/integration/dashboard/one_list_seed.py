"""Seeds of a ``one_list`` run for the counters and the Excel export (`F8-COUNT-XLSX`).

A run of either mode is inserted straight into ``audit_run`` (the marker is written at INSERT and frozen by the database), a text finding
is a ``finding`` with one grounded observation, and a candidate finding is written by the **real publisher**
(:func:`auditmanager.findings.publish_candidate_groups`) over a small geometry, so the rows the counters and the workbook read are the
rows `F8-PUBLISH` writes: one ``finding``, N observations of ``grounding_kind = portal_block``, their ``finding_block_evidence``.

Nothing here is a test; it is imported by ``test_one_list_counters.py`` and by ``tests/integration/exports/test_xlsx_one_list_export.py``.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.findings import (
    BlockEvidenceItem,
    BlockGateInputs,
    CandidateGroup,
    CandidateMember,
    publish_candidate_groups,
)
from auditmanager.findings.artifacts import PAGE_CROPS_ROLE, PORTAL_BLOCKS_ROLE, RECOGNISED_TEXT_ROLE
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DecisionId,
    FindingObservationId,
    FindingUid,
    PromptBundleId,
    RunId,
    StageLayoutRevisionId,
)

BLK_A = "blk_" + "a" * 32
BLK_B = "blk_" + "b" * 32
BLK_C = "blk_" + "c" * 32
#: ``block -> (page, crop sha256, box)`` of the geometry below.
BLOCKS = {
    BLK_A: (2, "a1" * 32, (0.1, 0.2, 0.6, 0.7)),
    BLK_B: (2, "b2" * 32, (0.2, 0.2, 0.4, 0.3)),
    BLK_C: (3, "c3" * 32, (0.5, 0.5, 0.9, 0.9)),
}

#: The edges ``contract_state_transition`` declares; a run is walked along them and never written at its target.
_PATH = {
    "published": ("queued", "running", "validating", "published"),
    "partial": ("queued", "running", "validating", "partial"),
    "failed": ("queued", "failed"),
    "running": ("queued", "running"),
}
_TERMINAL = {"published", "partial", "failed", "cancelled"}


def insert_run(
    session: Session, project_uid: str, version_uid: str, *, mode: str | None = "text_only", state: str = "published", age: int = 0,
    run_id: str | None = None,
) -> str:
    """One run on a version, created ``age`` seconds ago, walked to ``state``. ``mode=None`` leaves the marker out of the INSERT (the default)."""
    run_id = run_id or str(RunId.new())
    planned = mode == "one_list"
    plan = json.dumps({"layout_revision_id": str(StageLayoutRevisionId.new()), "cells": [
        {"cell_key": "review:main", "model_id": "claude-opus-5-5", "effort": "medium", "access": "subscription"}]})
    column, value = ("", "") if mode is None else (", publication_mode", ", :mode")
    session.execute(
        text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, provider_mode, "
            f"frozen_input_digest, binding_state, stage_plan, created_at{column}) "
            "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s, :binding, CAST(:plan AS jsonb), "
            f"now() - make_interval(secs => CAST(:age AS double precision)){value})"
        ),
        {
            "r": run_id, "p": project_uid, "v": version_uid, "ap": str(AnalysisProfileId.new()), "pb": str(PromptBundleId.new()),
            "s": hashlib.sha256(f"one-list-{run_id}".encode()).hexdigest(), "age": age, "mode": mode,
            "binding": "pending" if planned else "frozen_at_start", "plan": plan if planned else None,
        },
    )
    for step in _PATH[state]:
        session.execute(
            text(
                "UPDATE audit_run SET state = :s, terminal_at = CASE WHEN :t THEN now() ELSE NULL END, "
                "terminal_reason = CASE WHEN :s = 'failed' THEN 'analysis_failed' ELSE NULL END, "
                "degradation_set = CASE WHEN :s = 'partial' THEN '[\"block_analysis\"]'::jsonb "
                "WHEN :s = 'published' THEN '[]'::jsonb ELSE degradation_set END WHERE run_id = :r"
            ),
            {"s": step, "t": step in _TERMINAL, "r": run_id},
        )
    return run_id


def mode_of(session: Session, run_id: str) -> str:
    return str(session.execute(text("SELECT publication_mode FROM audit_run WHERE run_id = :r"), {"r": run_id}).scalar_one())


def decide(session: Session, finding_uid: str, observation_id: str, kind: str) -> None:
    """Give a finding the verdict ``kind`` names: ``pending`` (nothing), ``accepted`` or ``rejected``."""
    if kind == "pending":
        return
    event, verdict = {"accepted": ("accept", "accepted"), "rejected": ("reject", "rejected")}[kind]
    session.execute(
        text(
            "INSERT INTO expert_decision_event (decision_id, finding_uid, finding_observation_id, event_type, verdict, comment, "
            "author_label) VALUES (:d, :f, :o, :e, :v, NULL, 'one-list suite')"
        ),
        {"d": str(DecisionId.new()), "f": finding_uid, "o": observation_id, "e": event, "v": verdict},
    )


def text_finding(session: Session, project_uid: str, version_uid: str, run_id: str, kind: str = "pending", *, category: str = "layout") -> str:
    """One finding of the text path: a ``finding`` and the grounded ``text_span`` observation that publishes it, with its verdict."""
    finding_uid, observation_id = str(FindingUid.new()), str(FindingObservationId.new())
    session.execute(
        text("INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category) VALUES (:f, :p, :v, :r, :c)"),
        {"f": finding_uid, "p": project_uid, "v": version_uid, "r": run_id, "c": category},
    )
    session.execute(
        text(
            "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, finding_text, "
            "recommendation_text, grounded, analysis_profile_id, prompt_bundle_id, provider_mode) "
            "VALUES (:o, :r, :f, 'text_analysis', :c, 'Текстовое замечание', 'Исправить', true, :ap, :pb, 'recorded')"
        ),
        {"o": observation_id, "r": run_id, "f": finding_uid, "c": category, "ap": str(AnalysisProfileId.new()), "pb": str(PromptBundleId.new())},
    )
    session.execute(
        text(
            "INSERT INTO finding_evidence (finding_observation_id, evidence_ordinal, page_number, quote, char_start, char_end) "
            "VALUES (:o, 0, 1, 'x', 0, 1)"
        ),
        {"o": observation_id},
    )
    decide(session, finding_uid, observation_id, kind)
    return finding_uid


def geometry(version_uid: str) -> BlockGateInputs:
    """The geometry of a run: three image blocks of pages 2 and 3, the crop of each on record, recognised text for the first."""
    ordered = list(BLOCKS.items())
    return BlockGateInputs.from_artifacts(
        version_uid=version_uid,
        portal_blocks={
            "artifact_role": PORTAL_BLOCKS_ROLE, "artifact_version": "1.0.0", "version_uid": version_uid, "blocks_sha256": "e" * 64, "pages": [],
            "blocks": [{"portal_block_id": b, "page_number": p, "block_type": "image", "bbox_norm": list(box)} for b, (p, _, box) in ordered],
        },
        page_crops={
            "artifact_role": PAGE_CROPS_ROLE, "artifact_version": "1.0.0", "version_uid": version_uid, "crop_policy": "portal_image_blocks",
            "crops": [{"portal_block_id": b, "page_number": p, "sha256": sha} for b, (p, sha, _) in ordered],
        },
        recognised_text={
            "artifact_role": RECOGNISED_TEXT_ROLE, "artifact_version": "1.0.0", "version_uid": version_uid, "results_sha256": "f" * 64,
            "entries": [{"portal_block_id": BLK_A, "page_number": 2, "kind": "recognised_text", "text": "Размер 3000 мм"}],
        },
    )


def block_member(ref: str, *blocks: str, **extra: Any) -> CandidateMember:
    page_of = {block: (page, sha) for block, (page, sha, _) in BLOCKS.items()}
    items = tuple(
        BlockEvidenceItem(evidence_ordinal=position, page_number=page_of[block][0], portal_block_id=block, crop_sha256=page_of[block][1])
        for position, block in enumerate(blocks or (BLK_A,))
    )
    values: dict[str, Any] = {"extended_observation_ref": ref, "finding_text": f"Размер не совпадает с планом ({ref}).", "block_evidence": items}
    values.update(extra)
    return CandidateMember(**values)


def block_finding(
    session: Session, project_uid: str, version_uid: str, run_id: str, kind: str = "pending", *, members: tuple[tuple[str, ...], ...] = ((BLK_A,),),
    group_id: str = "xgrp_1", **member_extra: Any,
) -> Any:
    """One candidate finding published by the real publisher: a group of ``len(members)`` candidates, each standing on the blocks given.

    ``member_extra`` is passed to every :class:`~auditmanager.findings.CandidateMember` (``other_source_count=1`` makes the group a
    cross-check). Returns the :class:`~auditmanager.findings.PublishedCandidateFinding`; its verdict is ``kind``.
    """
    group = CandidateGroup(
        group_id, tuple(block_member(f"{group_id}_{position}", *blocks, **member_extra) for position, blocks in enumerate(members))
    )
    result = publish_candidate_groups(
        session, groups=[group], gate_inputs=geometry(version_uid), run_id=run_id, project_uid=project_uid, version_uid=version_uid,
        analysis_profile_id=str(AnalysisProfileId.new()), prompt_bundle_id=str(PromptBundleId.new()), provider_mode="recorded",
    )
    (published,) = result.published
    decide(session, published.finding_uid, published.canonical_observation_id, kind)
    return published
