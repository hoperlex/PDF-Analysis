"""The memory's own SQL: insert a captured case idempotently, and answer the questions the capture and the sweep ask.

The caller owns the transaction. Nothing here commits, opens an engine or catches a database error: a refusal propagates, because a
capture that fails must fail the decision that asked for it (`ADR-0027` decision 4, AGENTS section 4: no silent fallback).

Idempotency is the database's: ``INSERT ... ON CONFLICT DO NOTHING`` on ``origin_observation_id`` (one case per reviewed observation)
and on ``source_decision_id`` (one memory decision per ledger event). A second decision on an observation that already has a case
adds a decision row and nothing else; a digest that differs from the stored one is a ``conflict``, never an overwrite.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from auditmanager.decision_memory.models import (
    CAPTURE_VERSION,
    CROP_STATE_NONE_AVAILABLE,
    CROP_STATE_REFERENCED,
    CaptureResult,
    CaptureSnapshot,
    content_digest,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    DecisionMemoryCaseId,
    DecisionMemoryCropId,
    DecisionMemoryDecisionId,
)

_INSERT_CASE = text(
    """
    INSERT INTO decision_memory_case (
        case_id, origin_observation_id, origin_finding_uid, origin_project_uid, origin_document_uid,
        origin_version_uid, origin_run_id, category, section_code, data_class, crop_state,
        capture_version, content_sha256
    ) VALUES (
        :case_id, :observation_id, :finding_uid, :project_uid, :document_uid,
        :version_uid, :run_id, :category, :section_code, :data_class, :crop_state,
        :capture_version, :content_sha256
    )
    ON CONFLICT (origin_observation_id) DO NOTHING
    RETURNING case_id
    """
)

_SELECT_CASE = text(
    "SELECT case_id, content_sha256 FROM decision_memory_case WHERE origin_observation_id = :observation_id"
)

_INSERT_CONTENT = text(
    """
    INSERT INTO decision_memory_content (
        case_id, revision, finding_text, recommendation_text, proposed_severity, required_value, stated_value,
        stage_id, analysis_profile_id, prompt_bundle_id, provider_mode
    ) VALUES (
        :case_id, 1, :finding_text, :recommendation_text, :proposed_severity, :required_value, :stated_value,
        :stage_id, :analysis_profile_id, :prompt_bundle_id, :provider_mode
    )
    """
)

_INSERT_EVIDENCE = text(
    """
    INSERT INTO decision_memory_evidence (
        case_id, revision, ordinal, page_number, quote, char_start, char_end, block_ref,
        bbox_x0, bbox_y0, bbox_x1, bbox_y1, bbox_unit, bbox_origin
    ) VALUES (
        :case_id, 1, :ordinal, :page_number, :quote, :char_start, :char_end, :block_ref,
        :bbox_x0, :bbox_y0, :bbox_x1, :bbox_y1, :bbox_unit, :bbox_origin
    )
    """
)

_INSERT_NORM_REF = text(
    """
    INSERT INTO decision_memory_norm_ref (
        case_id, revision, ordinal, norms_snapshot_id, norm_document_id, norm_paragraph_id,
        designation, clause_number, page_label, quote, citation_state
    ) VALUES (
        :case_id, 1, :ordinal, :norms_snapshot_id, :norm_document_id, :norm_paragraph_id,
        :designation, :clause_number, :page_label, :quote, :citation_state
    )
    """
)

_INSERT_CROP = text(
    """
    INSERT INTO decision_memory_crop (
        crop_id, case_id, revision, crop_ordinal, evidence_ordinal, kind, selection_rule, page_number,
        bbox_x0, bbox_y0, bbox_x1, bbox_y1, blob_id, sha256, size_bytes, media_type, width_px, height_px,
        source_ref, portal_description
    ) VALUES (
        :crop_id, :case_id, 1, :crop_ordinal, :evidence_ordinal, :kind, :selection_rule, :page_number,
        :bbox_x0, :bbox_y0, :bbox_x1, :bbox_y1, :blob_id, :sha256, :size_bytes, :media_type, :width_px, :height_px,
        :source_ref, :portal_description
    )
    """
)

_INSERT_DECISION = text(
    """
    INSERT INTO decision_memory_decision (
        memory_decision_id, case_id, source_decision_id, event_type, verdict, severity,
        author_user_uid, origin_kind, decided_at
    ) VALUES (
        :memory_decision_id, :case_id, :source_decision_id, :event_type, :verdict, :severity,
        :author_user_uid, :origin_kind, :decided_at
    )
    ON CONFLICT (source_decision_id) DO NOTHING
    RETURNING memory_decision_id
    """
)

_INSERT_DECISION_TEXT = text(
    "INSERT INTO decision_memory_decision_text (memory_decision_id, comment) VALUES (:memory_decision_id, :comment)"
)

_CASE_DIGEST = text(
    "SELECT content_sha256 FROM decision_memory_case WHERE origin_observation_id = :observation_id"
)

_CAPTURED_SOURCES = text(
    "SELECT source_decision_id FROM decision_memory_decision WHERE source_decision_id IN :ids"
).bindparams(bindparam("ids", expanding=True))


class MemoryRepository:
    """Typed reads and the one idempotent write of the capture. Stateless."""

    def case_content_digest(self, session: Session, observation_id: str) -> str | None:
        """The stored ``content_sha256`` of the case of this observation, or ``None`` when there is no case yet.

        The assembler asks before it reads any published artifact: a known case needs no geometry and no crops.
        """
        return session.execute(_CASE_DIGEST, {"observation_id": observation_id}).scalar_one_or_none()

    def captured_sources(self, session: Session, decision_ids: Sequence[str]) -> frozenset[str]:
        """Which of these ledger event identities already have a memory decision."""
        wanted = sorted({value for value in decision_ids if isinstance(value, str)})
        if not wanted:
            return frozenset()
        return frozenset(session.execute(_CAPTURED_SOURCES, {"ids": wanted}).scalars())

    def capture(self, session: Session, snapshot: CaptureSnapshot) -> CaptureResult:
        """Write the snapshot, idempotently, and say what was created.

        A new observation gets its case, content, evidence, normative references and crop references and then its decision. A known
        observation has its stored digest compared with the snapshot's -- a difference is ``conflict`` -- and gets only the decision.
        A decision that is already captured changes nothing.
        """
        origin, content, decision = snapshot.origin, snapshot.content, snapshot.decision
        digest = content_digest(content)
        case_id = DecisionMemoryCaseId.new().value
        inserted = session.execute(
            _INSERT_CASE,
            {
                "case_id": case_id,
                "observation_id": origin.observation_id,
                "finding_uid": origin.finding_uid,
                "project_uid": origin.project_uid,
                "document_uid": origin.document_uid,
                "version_uid": origin.version_uid,
                "run_id": origin.run_id,
                "category": content.category,
                "section_code": snapshot.section_code,
                "data_class": snapshot.data_class,
                "crop_state": CROP_STATE_REFERENCED if snapshot.crops else CROP_STATE_NONE_AVAILABLE,
                "capture_version": CAPTURE_VERSION,
                "content_sha256": digest,
            },
        ).scalar_one_or_none()

        case_created = inserted is not None
        if case_created:
            self._insert_content(session, case_id, snapshot)
        else:
            row = session.execute(_SELECT_CASE, {"observation_id": origin.observation_id}).mappings().one()
            case_id = row["case_id"]
            if row["content_sha256"] != digest:
                raise DomainError(
                    ErrorCode.CONFLICT,
                    message="the stored decision-memory case of this observation differs from what is being captured",
                )

        memory_decision_id = DecisionMemoryDecisionId.new().value
        created = session.execute(
            _INSERT_DECISION,
            {
                "memory_decision_id": memory_decision_id,
                "case_id": case_id,
                "source_decision_id": decision.source_decision_id,
                "event_type": decision.event_type,
                "verdict": decision.verdict,
                "severity": decision.severity,
                "author_user_uid": decision.author_user_uid,
                "origin_kind": decision.origin_kind,
                "decided_at": decision.decided_at,
            },
        ).scalar_one_or_none()
        if created is None:
            return CaptureResult(case_id=case_id, memory_decision_id=None, case_created=case_created, decision_created=False)
        session.execute(_INSERT_DECISION_TEXT, {"memory_decision_id": memory_decision_id, "comment": decision.comment})
        return CaptureResult(
            case_id=case_id, memory_decision_id=memory_decision_id, case_created=case_created, decision_created=True
        )

    @staticmethod
    def _insert_content(session: Session, case_id: str, snapshot: CaptureSnapshot) -> None:
        content = snapshot.content
        session.execute(
            _INSERT_CONTENT,
            {
                "case_id": case_id,
                "finding_text": content.finding_text,
                "recommendation_text": content.recommendation_text,
                "proposed_severity": content.proposed_severity,
                "required_value": content.required_value,
                "stated_value": content.stated_value,
                "stage_id": content.stage_id,
                "analysis_profile_id": content.analysis_profile_id,
                "prompt_bundle_id": content.prompt_bundle_id,
                "provider_mode": content.provider_mode,
            },
        )
        if content.evidence:
            session.execute(
                _INSERT_EVIDENCE,
                [
                    {
                        "case_id": case_id,
                        "ordinal": item.ordinal,
                        "page_number": item.page_number,
                        "quote": item.quote,
                        "char_start": item.char_start,
                        "char_end": item.char_end,
                        "block_ref": item.block_ref,
                        "bbox_x0": None if item.bbox is None else item.bbox[0],
                        "bbox_y0": None if item.bbox is None else item.bbox[1],
                        "bbox_x1": None if item.bbox is None else item.bbox[2],
                        "bbox_y1": None if item.bbox is None else item.bbox[3],
                        "bbox_unit": item.bbox_unit,
                        "bbox_origin": item.bbox_origin,
                    }
                    for item in content.evidence
                ],
            )
        if content.norm_refs:
            session.execute(
                _INSERT_NORM_REF,
                [
                    {
                        "case_id": case_id,
                        "ordinal": ref.ordinal,
                        "norms_snapshot_id": ref.norms_snapshot_id,
                        "norm_document_id": ref.norm_document_id,
                        "norm_paragraph_id": ref.norm_paragraph_id,
                        "designation": ref.designation,
                        "clause_number": ref.clause_number,
                        "page_label": ref.page_label,
                        "quote": ref.quote,
                        "citation_state": ref.citation_state,
                    }
                    for ref in content.norm_refs
                ],
            )
        if snapshot.crops:
            session.execute(
                _INSERT_CROP,
                [
                    {
                        "crop_id": DecisionMemoryCropId.new().value,
                        "case_id": case_id,
                        "crop_ordinal": crop.ordinal,
                        "evidence_ordinal": crop.evidence_ordinal,
                        "kind": crop.kind,
                        "selection_rule": crop.selection_rule,
                        "page_number": crop.page_number,
                        "bbox_x0": crop.bbox[0],
                        "bbox_y0": crop.bbox[1],
                        "bbox_x1": crop.bbox[2],
                        "bbox_y1": crop.bbox[3],
                        "blob_id": crop.blob_id,
                        "sha256": crop.sha256,
                        "size_bytes": crop.size_bytes,
                        "media_type": crop.media_type,
                        "width_px": crop.width_px,
                        "height_px": crop.height_px,
                        "source_ref": crop.source_ref,
                        "portal_description": crop.portal_description,
                    }
                    for crop in snapshot.crops
                ],
            )
