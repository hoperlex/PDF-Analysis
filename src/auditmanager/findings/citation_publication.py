"""Unserved, transaction-scoped writer for one already grounded AR v3 finding.

The caller reads the retrieval-set Blob through its custody-aware port, runs
the pure document and norm gates, then supplies their result and the exact set
bytes here. A matching digest binds those bytes to the immutable, verified DB
set; the caller still owns the outer transaction and its deferred 0023 checks.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.norms.public import GroundedNormCitation
from auditmanager.shared.identity import FindingObservationId, FindingUid


class CitationPublicationRefused(ValueError):
    """The supplied grounded candidate or persisted publication authority drifted."""


NORMATIVE_CATEGORIES = frozenset({
    "evacuation", "fire_safety", "accessibility", "insulation", "sound",
})

#: The stages whose succeeded StageResult may certify a published citation partition.
#: ``norm_verification`` is the v1/v2 stage, written in the Attempt that made the call;
#: ``ar_v3_citation_review`` is the AR v3 beta CITE stage (``0036`` admits it in the database),
#: whose call and stage may belong to an earlier Attempt of the same Job: the worker replays
#: saved call/effect evidence through CITE without a second provider call, so a Run resumed
#: after a crash between CITE and the terminal still publishes.
CITE_STAGE_IDS = frozenset({"norm_verification", "ar_v3_citation_review"})
V3_BETA_CITE_STAGE_ID = "ar_v3_citation_review"


@dataclass(frozen=True, slots=True)
class CitationEvidence:
    page_number: int
    quote: str
    char_start: int
    char_end: int
    block_id: str | None = None


@dataclass(frozen=True, slots=True)
class V3PublicationCandidate:
    """The adapter boundary after both pure gates, with no model authority."""

    category: str
    finding_text: str
    recommendation_text: str
    proposed_severity: str
    evidence: tuple[CitationEvidence, ...]
    norm_citations: tuple[GroundedNormCitation, ...]
    required_value: str
    stated_value: str


@dataclass(frozen=True, slots=True)
class PublishedV3CitationFinding:
    finding_uid: str
    finding_observation_id: str
    citation_count: int


_AUTHORITY = text("""
    SELECT r.project_uid, r.version_uid, r.analysis_profile_id,
           r.prompt_bundle_id, r.provider_mode, r.norms_snapshot_id,
           r.norm_retrieval_set_id, r.state AS run_state,
           j.state AS job_state, a.state AS attempt_state,
           a.execution_token,
           s.state AS set_state, s.observed_set_sha256, s.set_size_bytes,
           s.map_sha256, s.reviewed_content_key,
           mc.status AS call_status, mc.provider_mode AS call_mode,
           mc.request_sha256 AS call_request_sha256,
           mc.response_sha256 AS call_response_sha256,
           pe.state AS effect_state, pe.attempt_id AS effect_attempt_id,
           pe.provider_mode AS effect_mode,
           pe.request_sha256 AS effect_request_sha256,
           pe.response_sha256 AS effect_response_sha256,
           st.status AS cite_status
      FROM audit_run r
      JOIN job j ON j.run_id = r.run_id
      JOIN attempt a ON a.attempt_id = j.current_attempt_id
      JOIN norm_retrieval_set s ON s.norm_retrieval_set_id = r.norm_retrieval_set_id
       AND s.norms_snapshot_id = r.norms_snapshot_id
      JOIN model_call mc ON mc.model_call_id = :model_call_id
       AND mc.run_id = r.run_id AND mc.stage_id = 'text_analysis'
      JOIN provider_call_effect pe ON pe.model_call_id = mc.model_call_id
       AND pe.run_id = r.run_id AND pe.job_id = j.job_id
       AND (NOT :same_attempt OR pe.attempt_id = a.attempt_id)
       AND pe.stage_id = 'text_analysis'
      JOIN stage_result st ON st.run_id = r.run_id
       AND st.stage_id = :cite_stage_id
       AND (NOT :same_attempt OR st.created_at >= a.created_at)
     WHERE r.run_id = :run_id AND j.job_id = :job_id
       AND a.attempt_id = :attempt_id
       AND j.current_attempt_id = :attempt_id
       AND EXISTS (
           SELECT 1 FROM norm_custody_binding cb
           JOIN blob b ON b.blob_id = cb.blob_id
           WHERE cb.target_kind = 'norm_retrieval_set'
             AND cb.target_id = s.norm_retrieval_set_id
             AND cb.role = 'norm_retrieval_set'
             AND cb.blob_id = s.set_blob_id
             AND b.state = 'available'
             AND b.sha256 = s.observed_set_sha256
             AND b.size_bytes = s.set_size_bytes
       )
     FOR UPDATE OF r, j, a
""")

_INSERT_FINDING = text("""
    INSERT INTO finding (
        finding_uid, project_uid, version_uid, allocated_by_run_id, category
    ) VALUES (:finding_uid, :project_uid, :version_uid, :run_id, :category)
""")
_INSERT_OBSERVATION = text("""
    INSERT INTO finding_observation (
        finding_observation_id, run_id, finding_uid, stage_id, category,
        finding_text, recommendation_text, grounded, ungrounded_reason,
        analysis_profile_id, prompt_bundle_id, model_call_id, provider_mode,
        proposed_severity, required_value, stated_value, norm_citation_count
    ) VALUES (
        :observation_id, :run_id, :finding_uid, 'text_analysis', :category,
        :finding_text, :recommendation_text, true, NULL,
        :analysis_profile_id, :prompt_bundle_id, :model_call_id, :provider_mode,
        :proposed_severity, :required_value, :stated_value, :citation_count
    )
""")
_INSERT_EVIDENCE = text("""
    INSERT INTO finding_evidence (
        finding_observation_id, evidence_ordinal, page_number, quote,
        char_start, char_end, block_id
    ) VALUES (
        :observation_id, :ordinal, :page_number, :quote,
        :char_start, :char_end, :block_id
    )
""")
_INSERT_CITATION = text("""
    INSERT INTO finding_observation_norm_citation (
        finding_observation_id, citation_ordinal, run_id, norms_snapshot_id,
        norm_retrieval_set_id, norm_document_id, norm_paragraph_id,
        quote, char_start, char_length, state
    ) VALUES (
        :observation_id, :ordinal, :run_id, :snapshot_id,
        :set_id, :document_id, :paragraph_id,
        :quote, :char_start, :char_length, :state
    )
""")
_SET_CANONICAL = text("""
    UPDATE finding SET canonical_observation_id = :observation_id
     WHERE finding_uid = :finding_uid AND canonical_observation_id IS NULL
""")


def _object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CitationPublicationRefused("set_json_duplicate_key")
        result[key] = value
    return result


def _set_membership(
    set_bytes: bytes, *, expected_digest: str, expected_size: int,
    snapshot_id: str, map_digest: str, reviewed_key: str,
    candidate: V3PublicationCandidate,
) -> None:
    if (not isinstance(set_bytes, bytes) or len(set_bytes) != expected_size
            or len(set_bytes) > 10_000_000
            or hashlib.sha256(set_bytes).hexdigest() != expected_digest):
        raise CitationPublicationRefused("set_bytes_differ_from_custody")
    try:
        payload = json.loads(set_bytes.decode("utf-8"), object_pairs_hook=_object_pairs)
    except (UnicodeError, ValueError) as exc:
        raise CitationPublicationRefused("set_bytes_invalid") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("identity"), dict):
        raise CitationPublicationRefused("set_identity_invalid")
    identity = payload["identity"]
    if (identity.get("norms_snapshot_id") != snapshot_id
            or identity.get("map_sha256") != map_digest
            or identity.get("reviewed_content_key") != reviewed_key):
        raise CitationPublicationRefused("set_identity_mismatch")
    try:
        prompt = json.loads(payload["prompt_part"], object_pairs_hook=_object_pairs)
        selected = prompt["paragraphs"]
        paragraphs = payload["rebinding_paragraphs"]
    except (KeyError, TypeError, ValueError) as exc:
        raise CitationPublicationRefused("set_paragraphs_invalid") from exc
    if not isinstance(selected, list) or not isinstance(paragraphs, list):
        raise CitationPublicationRefused("set_paragraphs_invalid")
    labels: dict[str, tuple[str, str]] = {}
    full: dict[str, tuple[str, str]] = {}
    for row in paragraphs:
        if not isinstance(row, dict):
            raise CitationPublicationRefused("set_paragraphs_invalid")
        document, paragraph, content = (
            row.get("norm_document_id"), row.get("norm_paragraph_id"), row.get("text")
        )
        if not all(isinstance(value, str) for value in (document, paragraph, content)):
            raise CitationPublicationRefused("set_paragraphs_invalid")
        if (paragraph in full or hashlib.sha256(content.encode("utf-8")).hexdigest()
                != row.get("text_sha256")):
            raise CitationPublicationRefused("set_paragraphs_invalid")
        full[paragraph] = (document, content)
    for row in selected:
        if not isinstance(row, dict):
            raise CitationPublicationRefused("set_labels_invalid")
        label, document, paragraph = (
            row.get("label"), row.get("norm_document_id"), row.get("norm_paragraph_id")
        )
        if (not isinstance(label, str) or label in labels or not isinstance(paragraph, str)
                or full.get(paragraph, (None,))[0] != document
                or row.get("text") != full[paragraph][1]):
            raise CitationPublicationRefused("set_labels_invalid")
        labels[label] = (document, paragraph)
    for index, citation in enumerate(candidate.norm_citations):
        if (citation.label not in labels or citation.state not in {"verified", "rebound"}
                or citation.document_id != labels[citation.label][0]
                or citation.paragraph_id not in full
                or full[citation.paragraph_id][0] != citation.document_id):
            raise CitationPublicationRefused("citation_outside_selected_set")
        if (citation.state == "verified") != (citation.paragraph_id == labels[citation.label][1]):
            raise CitationPublicationRefused("citation_rebinding_state_invalid")
        content = full[citation.paragraph_id][1]
        if (type(citation.raw_offset) is not int or citation.raw_offset < 0
                or not isinstance(citation.raw_quote, str)
                or not 20 <= len(citation.raw_quote) <= 4000
                or content[citation.raw_offset:citation.raw_offset + len(citation.raw_quote)]
                != citation.raw_quote):
            raise CitationPublicationRefused(f"citation_raw_span_invalid:{index}")


def publish_grounded_v3_finding(
    session: Session, *, run_id: str, job_id: str, attempt_id: str,
    execution_token: str, model_call_id: str, set_bytes: bytes,
    candidate: V3PublicationCandidate,
    cite_stage_id: str = "norm_verification",
) -> PublishedV3CitationFinding:
    """Insert a normative finding and all its citations in the caller's transaction.

    The caller must have obtained ``set_bytes`` from the custody-checked Blob,
    executed the pure PDF/norm gates, and inserted a succeeded CITE StageResult
    in this same transaction. No commit occurs here: 0023's deferred partition
    and canonical quote checks run only when the outer transaction commits.

    ``cite_stage_id`` names the succeeded stage that certifies the partition (see
    :data:`CITE_STAGE_IDS`). For the default stage the call effect and the stage row must belong
    to the current Attempt, as before; for the AR v3 beta stage they must belong to the same Job
    and Run, which the caller's ``completed_v3_call`` and the final fence prove, because the
    call may have been completed by an earlier Attempt.
    """
    if cite_stage_id not in CITE_STAGE_IDS:
        raise CitationPublicationRefused("cite_stage_unknown")
    same_attempt = cite_stage_id != V3_BETA_CITE_STAGE_ID
    if (not isinstance(candidate, V3PublicationCandidate)
            or candidate.category not in NORMATIVE_CATEGORIES
            or not 1 <= len(candidate.norm_citations) <= 5
            or not candidate.evidence
            or not candidate.required_value or not candidate.stated_value):
        raise CitationPublicationRefused("grounded_normative_candidate_required")
    row = session.execute(_AUTHORITY, {
        "run_id": run_id, "job_id": job_id, "attempt_id": attempt_id,
        "model_call_id": model_call_id, "cite_stage_id": cite_stage_id,
        "same_attempt": same_attempt,
    }).mappings().one_or_none()
    if row is None or (
        row["run_state"] != "validating"
        or row["job_state"] != "running"
        or row["attempt_state"] != "running"
        or row["execution_token"] != execution_token
        or row["set_state"] != "verified"
        or row["call_status"] != "succeeded"
        or row["call_mode"] != row["provider_mode"]
        or row["effect_state"] != "completed"
        or (same_attempt and row["effect_attempt_id"] != attempt_id)
        or row["effect_mode"] != row["call_mode"]
        or row["effect_request_sha256"] != row["call_request_sha256"]
        or row["effect_response_sha256"] != row["call_response_sha256"]
        or row["cite_status"] != "succeeded"
    ):
        raise CitationPublicationRefused("publication_authority_invalid")
    _set_membership(
        set_bytes, expected_digest=row["observed_set_sha256"],
        expected_size=row["set_size_bytes"], snapshot_id=row["norms_snapshot_id"],
        map_digest=row["map_sha256"], reviewed_key=row["reviewed_content_key"],
        candidate=candidate,
    )
    finding_uid = FindingUid.new().value
    observation_id = FindingObservationId.new().value
    session.execute(_INSERT_FINDING, {
        "finding_uid": finding_uid, "project_uid": row["project_uid"],
        "version_uid": row["version_uid"], "run_id": run_id,
        "category": candidate.category,
    })
    session.execute(_INSERT_OBSERVATION, {
        "observation_id": observation_id, "run_id": run_id,
        "finding_uid": finding_uid, "category": candidate.category,
        "finding_text": candidate.finding_text,
        "recommendation_text": candidate.recommendation_text,
        "analysis_profile_id": row["analysis_profile_id"],
        "prompt_bundle_id": row["prompt_bundle_id"],
        "model_call_id": model_call_id, "provider_mode": row["provider_mode"],
        "proposed_severity": candidate.proposed_severity,
        "required_value": candidate.required_value,
        "stated_value": candidate.stated_value,
        "citation_count": len(candidate.norm_citations),
    })
    for ordinal, evidence in enumerate(candidate.evidence):
        session.execute(_INSERT_EVIDENCE, {
            "observation_id": observation_id, "ordinal": ordinal,
            "page_number": evidence.page_number, "quote": evidence.quote,
            "char_start": evidence.char_start, "char_end": evidence.char_end,
            "block_id": evidence.block_id,
        })
    for ordinal, citation in enumerate(candidate.norm_citations, 1):
        session.execute(_INSERT_CITATION, {
            "observation_id": observation_id, "ordinal": ordinal,
            "run_id": run_id, "snapshot_id": row["norms_snapshot_id"],
            "set_id": row["norm_retrieval_set_id"],
            "document_id": citation.document_id,
            "paragraph_id": citation.paragraph_id,
            "quote": citation.raw_quote, "char_start": citation.raw_offset,
            "char_length": len(citation.raw_quote), "state": citation.state,
        })
    if session.execute(_SET_CANONICAL, {
        "finding_uid": finding_uid, "observation_id": observation_id,
    }).rowcount != 1:
        raise CitationPublicationRefused("canonical_finding_assignment_failed")
    return PublishedV3CitationFinding(finding_uid, observation_id, len(candidate.norm_citations))
