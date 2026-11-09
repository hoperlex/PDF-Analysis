"""Rows of the decision memory for tests that need a case without capturing one (`DECISION-MEMORY-01` phase M2).

A case is normally made by ``record_decision`` through the composition root's assembler; the migration, the guard and the forget tool are about
the TABLES, so their tests write the rows directly -- with every trigger ON, so the guards under test are the ones that answer.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Connection, text

from auditmanager.shared.identity import (
    DecisionId,
    DecisionMemoryCaseId,
    DecisionMemoryCropId,
    DecisionMemoryDecisionId,
    FindingObservationId,
)

SHA = "a" * 64


def ensure_blob(connection: Connection, blob_id: str) -> None:
    """A bare ``blob`` row (state ``temporary``): enough for a crop's foreign key, not for a forget that must delete an object."""
    connection.execute(text("INSERT INTO blob (blob_id) VALUES (:b) ON CONFLICT DO NOTHING"), {"b": blob_id})


def seed_case(connection: Connection, *, observation: str | None = None, project: str = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV",
              blob: str | None = None, verdicts: tuple[str, ...] = ("accept",), source_ref: str = "blk_" + "a" * 32) -> dict[str, Any]:
    """One case with content, evidence, a norm reference, a crop of ``blob`` (when given), decisions and the expert's comment."""
    case_id = DecisionMemoryCaseId.new().value
    connection.execute(text(
        "INSERT INTO decision_memory_case (case_id, origin_observation_id, origin_finding_uid, origin_project_uid, "
        "origin_document_uid, origin_version_uid, origin_run_id, category, section_code, data_class, crop_state, capture_version, "
        "content_sha256) VALUES (:c, :o, 'fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV', :p, "
        "'doc_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'ver_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'run_01ARZ3NDEKTSV4RRFFQ69G5FAV', "
        "'internal_contradiction', 'AR', 'test', :crop_state, 'dm-capture/1', :sha)"),
        {"c": case_id, "o": observation or FindingObservationId.new().value, "p": project,
         "crop_state": "referenced" if blob else "none_available", "sha": SHA})
    connection.execute(text(
        "INSERT INTO decision_memory_content (case_id, revision, finding_text, recommendation_text, stage_id, analysis_profile_id, "
        "prompt_bundle_id, provider_mode) VALUES (:c, 1, 'finding', 'recommendation', 'text_analysis', "
        "'ap_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'pb_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'recorded')"), {"c": case_id})
    connection.execute(text(
        "INSERT INTO decision_memory_evidence (case_id, revision, ordinal, page_number, quote, char_start, char_end) "
        "VALUES (:c, 1, 0, 1, 'quote', 0, 5)"), {"c": case_id})
    connection.execute(text(
        "INSERT INTO decision_memory_norm_ref (case_id, revision, ordinal, norms_snapshot_id, norm_document_id, norm_paragraph_id, "
        "designation, clause_number, page_label, quote, citation_state) VALUES (:c, 1, 1, 'ns_01ARZ3NDEKTSV4RRFFQ69G5FAV', "
        "'ndoc_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'npar_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'SP 1', '1.1', 1, :quote, 'verified')"),
        {"c": case_id, "quote": "q" * 30})
    if blob:
        connection.execute(text(
            "INSERT INTO decision_memory_crop (crop_id, case_id, revision, crop_ordinal, evidence_ordinal, kind, selection_rule, "
            "page_number, bbox_x0, bbox_y0, bbox_x1, bbox_y1, blob_id, sha256, size_bytes, media_type, width_px, height_px, source_ref) "
            "VALUES (:crop, :c, 1, 1, 0, 'portal_image_block', 'page_images/1', 1, 0.1, 0.1, 0.5, 0.5, :b, :sha, 10, 'image/png', "
            "800, 600, :source)"),
            {"crop": DecisionMemoryCropId.new().value, "c": case_id, "b": blob, "sha": SHA, "source": source_ref})
    decisions = []
    for index, event in enumerate(verdicts):
        decision_id = DecisionMemoryDecisionId.new().value
        connection.execute(text(
            "INSERT INTO decision_memory_decision (memory_decision_id, case_id, source_decision_id, event_type, verdict, severity, "
            "author_user_uid, origin_kind, decided_at) VALUES (:d, :c, :s, :e, :v, NULL, NULL, 'direct', now() + (:i || ' seconds')::interval)"),
            {"d": decision_id, "c": case_id, "s": DecisionId.new().value,
             "e": event, "v": "accepted" if event == "accept" else "rejected", "i": str(index)})
        connection.execute(text("INSERT INTO decision_memory_decision_text (memory_decision_id, comment) VALUES (:d, 'the expert wrote this')"),
                           {"d": decision_id})
        decisions.append(decision_id)
    return {"case_id": case_id, "decisions": decisions}
