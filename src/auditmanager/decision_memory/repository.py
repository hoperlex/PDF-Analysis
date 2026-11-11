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
    COMMENT_ALREADY_CAPTURED,
    COMMENT_CAPTURED,
    COMMENT_REFUSED_CASE_FORGOTTEN,
    COMMENT_WAITS_FOR_CASE,
    CROP_STATE_NONE_AVAILABLE,
    CROP_STATE_REFERENCED,
    CaptureResult,
    CaptureSnapshot,
    CommentCaptureResult,
    CommentFact,
    capture_version_of,
    content_digest,
)
from auditmanager.decision_memory.service import STATUS_LOCK_PREFIX
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    DecisionMemoryCaseId,
    DecisionMemoryCommentId,
    DecisionMemoryCropId,
    DecisionMemoryDecisionId,
)

#: The advisory-lock key prefix of the comments of one observation. A comment written before its observation has a case and the first
#: ✓/✕ that makes the case must not pass each other unseen (see :meth:`MemoryRepository.lock_observation_comments`).
COMMENT_LOCK_PREFIX = "decision_memory_comment_observation:"

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

_INSERT_BLOCK_EVIDENCE = text(
    """
    INSERT INTO decision_memory_block_evidence (
        case_id, revision, ordinal, page_number, portal_block_id,
        bbox_x0, bbox_y0, bbox_x1, bbox_y1, crop_sha256, recognised_quote
    ) VALUES (
        :case_id, 1, :ordinal, :page_number, :portal_block_id,
        :bbox_x0, :bbox_y0, :bbox_x1, :bbox_y1, :crop_sha256, :recognised_quote
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
        author_user_uid, origin_kind, decided_at,
        precedent_label_at_decision, precedent_revision, precedent_history_verdict_shown
    ) VALUES (
        :memory_decision_id, :case_id, :source_decision_id, :event_type, :verdict, :severity,
        :author_user_uid, :origin_kind, :decided_at,
        :precedent_label_at_decision, :precedent_revision, :precedent_history_verdict_shown
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

_FORGOTTEN = text(
    "SELECT 1 FROM decision_memory_status_event WHERE case_id = :case_id AND kind = 'forget' LIMIT 1"
)

_LOCK = text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))")

_CASE_OF_OBSERVATION = text("SELECT case_id FROM decision_memory_case WHERE origin_observation_id = :observation_id")

_INSERT_COMMENT = text(
    """
    INSERT INTO decision_memory_comment (comment_id, case_id, source_decision_id, author_user_uid, comment, decided_at)
    VALUES (:comment_id, :case_id, :source_decision_id, :author_user_uid, :comment, :decided_at)
    ON CONFLICT (source_decision_id) DO NOTHING
    RETURNING comment_id
    """
)

_CAPTURED_COMMENT_SOURCES = text(
    "SELECT source_decision_id FROM decision_memory_comment WHERE source_decision_id IN :ids"
).bindparams(bindparam("ids", expanding=True))

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

    def captured_comment_sources(self, session: Session, decision_ids: Sequence[str]) -> frozenset[str]:
        """Which of these ledger ``comment`` event identities already have a memory comment (the sweep's anti-join)."""
        wanted = sorted({value for value in decision_ids if isinstance(value, str)})
        if not wanted:
            return frozenset()
        return frozenset(session.execute(_CAPTURED_COMMENT_SOURCES, {"ids": wanted}).scalars())

    def lock_observation_comments(self, session: Session, observation_id: str) -> None:
        """Take the transaction-scoped lock of this observation's comments; released at commit or rollback.

        :meth:`capture_comment` and :meth:`capture` take it themselves. A caller that **reads the ledger for the observation's earlier
        comments** before it calls :meth:`capture` must take it first: then a comment written by a concurrent transaction is either
        committed and read (this transaction waited for it) or waits for this one and finds the case already made. Without it a comment
        and a first ✓/✕ that overlap in time can each miss the other.
        """
        session.execute(_LOCK, {"key": COMMENT_LOCK_PREFIX + observation_id})

    def capture_comment(self, session: Session, *, observation_id: str, comment: CommentFact) -> CommentCaptureResult:
        """Keep an expert's ``comment`` event in the case of its observation, idempotently (``ADR-0029`` decision 10).

        * no case yet: ``waits_for_case`` and nothing is written -- the capture of the case's first ✓/✕ carries the comment over;
        * a forgotten case: ``case_forgotten`` and nothing is written, because a forgotten case takes no words back (the database
          refuses the row as well, with ``AM003``; this answer keeps that refusal from failing the expert's decision);
        * otherwise one row, once: the same ledger event again is ``already_captured``.

        A database refusal other than that one propagates: a capture that fails must fail the decision that asked for it (`ADR-0027`
        decision 4). A comment never makes a case, never touches a decision row and never changes a vote.
        """
        self.lock_observation_comments(session, observation_id)
        case_id = session.execute(_CASE_OF_OBSERVATION, {"observation_id": observation_id}).scalar_one_or_none()
        if case_id is None:
            return CommentCaptureResult(case_id=None, outcome=COMMENT_WAITS_FOR_CASE)
        session.execute(_LOCK, {"key": STATUS_LOCK_PREFIX + case_id})   # a forget of this case in flight finishes first
        if session.execute(_FORGOTTEN, {"case_id": case_id}).first() is not None:
            return CommentCaptureResult(case_id=case_id, outcome=COMMENT_REFUSED_CASE_FORGOTTEN)
        created = self._insert_comment(session, case_id, comment)
        return CommentCaptureResult(case_id=case_id, outcome=COMMENT_CAPTURED if created else COMMENT_ALREADY_CAPTURED)

    @staticmethod
    def _insert_comment(session: Session, case_id: str, comment: CommentFact) -> bool:
        return session.execute(
            _INSERT_COMMENT,
            {
                "comment_id": DecisionMemoryCommentId.new().value,
                "case_id": case_id,
                "source_decision_id": comment.source_decision_id,
                "author_user_uid": comment.author_user_uid,
                "comment": comment.comment,
                "decided_at": comment.decided_at,
            },
        ).scalar_one_or_none() is not None

    def _carry_comments(self, session: Session, case_id: str, comments: Sequence[CommentFact], *, case_created: bool) -> int:
        """Store the earlier comments of a case, each once; how many were new. A forgotten case takes none."""
        if not comments:
            return 0
        if not case_created:
            session.execute(_LOCK, {"key": STATUS_LOCK_PREFIX + case_id})
            if session.execute(_FORGOTTEN, {"case_id": case_id}).first() is not None:
                return 0
        once = {fact.source_decision_id: fact for fact in comments}.values()
        ordered = sorted(once, key=lambda fact: (fact.decided_at, fact.source_decision_id))
        return sum(1 for fact in ordered if self._insert_comment(session, case_id, fact))

    def capture(self, session: Session, snapshot: CaptureSnapshot) -> CaptureResult:
        """Write the snapshot, idempotently, and say what was created.

        A new observation gets its case, content, evidence, normative references and crop references and then its decision. A known
        observation has its stored digest compared with the snapshot's -- a difference is ``conflict`` -- and gets only the decision.
        A decision that is already captured changes nothing.

        The snapshot's ``earlier_comments`` are carried over into the case, each once (``ADR-0029`` decision 10): the first ✓/✕ carries
        the notes written before it, and a replay, or a later decision handed the same comments, adds none. A forgotten case takes none.
        """
        origin, content, decision = snapshot.origin, snapshot.content, snapshot.decision
        self.lock_observation_comments(session, origin.observation_id)
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
                "capture_version": capture_version_of(content),
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
                "precedent_label_at_decision": decision.precedent_label_at_decision,
                "precedent_revision": decision.precedent_revision,
                "precedent_history_verdict_shown": decision.precedent_history_verdict_shown,
            },
        ).scalar_one_or_none()
        if created is None:
            carried = self._carry_comments(session, case_id, snapshot.earlier_comments, case_created=case_created)
            return CaptureResult(
                case_id=case_id, memory_decision_id=None, case_created=case_created, decision_created=False, comments_carried=carried
            )
        if not case_created and session.execute(_FORGOTTEN, {"case_id": case_id}).first() is not None:
            # A forgotten case is a tombstone (`DECISION-MEMORY-01` section 4.5): its content was removed on the owner's order and
            # it accepts none back. The decision row is still recorded -- its verdict, severity and time hold no words of the
            # expert, and without it the ledger event would stay "uncaptured" for ever (guard G1, the sweep) -- but not the comment.
            return CaptureResult(
                case_id=case_id, memory_decision_id=memory_decision_id, case_created=False, decision_created=True
            )
        session.execute(_INSERT_DECISION_TEXT, {"memory_decision_id": memory_decision_id, "comment": decision.comment})
        carried = self._carry_comments(session, case_id, snapshot.earlier_comments, case_created=case_created)
        return CaptureResult(
            case_id=case_id, memory_decision_id=memory_decision_id, case_created=case_created, decision_created=True,
            comments_carried=carried,
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
        if content.block_evidence:
            session.execute(
                _INSERT_BLOCK_EVIDENCE,
                [
                    {
                        "case_id": case_id,
                        "ordinal": item.ordinal,
                        "page_number": item.page_number,
                        "portal_block_id": item.portal_block_id,
                        "bbox_x0": item.bbox[0],
                        "bbox_y0": item.bbox[1],
                        "bbox_x1": item.bbox[2],
                        "bbox_y1": item.bbox[3],
                        "crop_sha256": item.crop_sha256,
                        "recognised_quote": item.recognised_quote,
                    }
                    for item in content.block_evidence
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
