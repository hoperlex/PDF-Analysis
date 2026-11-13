"""Fresh-policy admission to the existing human ledger; grounding stays factual.

The original deterministic corrector keeps a meaningful question for the expert
when its source is incomplete. This adapter does the same without forging evidence.
Publication is serialized by run and replayed by stable member reference.
"""
from __future__ import annotations

from sqlalchemy import text

from auditmanager.findings.artifacts import BlockObservation, EvidenceItem, Observation
from auditmanager.findings.grounding import run_block_gate, run_grounding_gate
from auditmanager.findings.publication import (
    CandidatePublicationResult, PublishedCandidateFinding, _INSERT_BLOCK_EVIDENCE,
    _INSERT_CANDIDATE_OBSERVATION, _INSERT_EVIDENCE, _INSERT_FINDING, _SET_CANONICAL,
    _invalid_candidate, classify_group,
)
from auditmanager.shared.db import nested_transaction
from auditmanager.shared.identity import FindingObservationId, FindingUid


def native_evidence(member, text_layer):
    """Resolve only a unique literal quote on its declared page; no guessed span."""
    sources = member.native_sources
    if not sources or text_layer is None:
        return ()
    evidence = []
    for number, quote in sources:
        page = text_layer.page(number)
        if page is None or not quote or len(quote) > 2000:
            return ()
        page_text = text_layer.slice(page.char_start, page.char_end)
        offset = page_text.find(quote)
        if offset < 0 or page_text.find(quote, offset + 1) >= 0:
            return ()
        start = page.char_start + offset
        evidence.append(EvidenceItem(len(evidence), number, quote, start, start + len(quote)))
    return tuple(evidence)


def publish_reviewable_groups(session, *, groups, gate_inputs, run_id, project_uid, version_uid,
                              analysis_profile_id, prompt_bundle_id, provider_mode,
                              primary_findings=None, unread=(), text_layer=None):
    linked = dict(primary_findings or {})
    published, gaps = [], list(unread)
    with nested_transaction(session):
        binding = session.execute(text("SELECT project_uid, version_uid FROM audit_run WHERE run_id = :run FOR UPDATE"),
                                  {"run": run_id}).one_or_none()
        if binding is None or tuple(binding) != (project_uid, version_uid):
            raise _invalid_candidate("candidate publication does not belong to the run/version")
        if text_layer is not None and text_layer.version_uid != version_uid:
            raise _invalid_candidate("native sources do not belong to the run/version")
        for group in groups:
            kind = classify_group(group)
            existing = session.execute(text(
                "SELECT o.extended_observation_ref, o.finding_uid, o.finding_observation_id, o.finding_text, "
                "f.canonical_observation_id, f.category, f.version_uid "
                "FROM finding_observation o JOIN finding f ON f.finding_uid = o.finding_uid "
                "WHERE o.run_id = :run AND o.extended_observation_ref = ANY(CAST(:refs AS text[]))"
            ), {"run": run_id, "refs": [m.extended_observation_ref for m in group.members]}).mappings().all()
            by_ref = {row["extended_observation_ref"]: row for row in existing}
            if len(by_ref) != len(existing):
                raise _invalid_candidate("a source reference has multiple published observations")
            related_uids = {linked[n] for m in group.members for n in m.primary_text_ordinals if n in linked}
            # A citation of a primary issue is context, not an identity match.
            # Reuse requires the primary origin itself to be a member of the
            # validated semantic group (or an already published exact reference).
            uids = {linked[n] for m in group.members for n in m.primary_text_ordinals if n in linked
                    and not m.block_evidence and not m.other_source_count and not m.primary_text_unlinked
                    and len(m.primary_text_ordinals) == 1}
            uids.update(row["finding_uid"] for row in existing)
            # Never combine existing identities or overwrite their human decisions.
            if len(uids) > 1:
                gaps.append(f"identity_conflict:{group.group_id}")
            target = sorted(uids)[0] if uids else FindingUid.new().value
            head = session.execute(text("SELECT canonical_observation_id, category, version_uid FROM finding WHERE finding_uid = :uid"),
                                   {"uid": target}).mappings().one_or_none()
            if head is not None and head["version_uid"] != version_uid:
                raise _invalid_candidate("a primary finding belongs to a different version")
            category = kind.category if head is None else head["category"]
            if head is None:
                session.execute(_INSERT_FINDING, {"finding_uid": target, "project_uid": project_uid,
                    "version_uid": version_uid, "run_id": run_id, "category": category, "publication_policy": "reviewable-v1"})
            observations, evidence_count = [], 0
            for member in group.members:
                known = by_ref.get(member.extended_observation_ref)
                if known is not None:
                    if known["finding_text"] != member.finding_text:
                        raise _invalid_candidate("a published candidate reference changed its content")
                    if known["finding_uid"] == target:
                        observations.append(known["finding_observation_id"])
                    continue
                block_verdict = None
                if member.block_evidence:
                    block_verdict = run_block_gate([BlockObservation(0, member.block_evidence,
                        member.extended_observation_ref)], gate_inputs).verdicts[0]
                native = native_evidence(member, text_layer)
                native_ok = bool(native) and run_grounding_gate([Observation(0, category,
                    member.finding_text, member.recommendation_text, native)], text_layer).verdicts[0].grounded
                block_ok = block_verdict is not None and block_verdict.grounded
                grounded = block_ok or native_ok
                reason = None if grounded else (block_verdict.reason.value if block_verdict is not None else "source_binding_unverified")
                observation_id = FindingObservationId.new().value
                observations.append(observation_id)
                session.execute(_INSERT_CANDIDATE_OBSERVATION, {
                    "finding_observation_id": observation_id, "run_id": run_id, "finding_uid": target,
                    "stage_id": kind.stage_id, "category": category, "finding_text": member.finding_text,
                    "recommendation_text": member.recommendation_text, "grounded": grounded,
                    "ungrounded_reason": reason, "analysis_profile_id": analysis_profile_id,
                    "prompt_bundle_id": prompt_bundle_id, "provider_mode": provider_mode,
                    "grounding_kind": "portal_block" if block_ok else "text_span" if native_ok else "unverified",
                    "extended_observation_ref": member.extended_observation_ref,
                    "related_finding_uid": next((uid for uid in sorted(related_uids) if uid != target), None),
                    "proposed_severity": member.proposed_severity,
                })
                if block_ok:
                    for item in member.block_evidence:
                        place = gate_inputs.geometry.place(item.portal_block_id)
                        x0, y0, x1, y1 = place.bbox_norm
                        session.execute(_INSERT_BLOCK_EVIDENCE, {"finding_observation_id": observation_id,
                            "ordinal": item.evidence_ordinal, "page_number": place.page_number,
                            "portal_block_id": item.portal_block_id, "bbox_x0": x0, "bbox_y0": y0, "bbox_x1": x1, "bbox_y1": y1,
                            "crop_sha256": item.crop_sha256, "recognised_quote": item.recognised_quote})
                        evidence_count += 1
                elif native_ok:
                    for item in native:
                        session.execute(_INSERT_EVIDENCE, {"finding_observation_id": observation_id,
                            "evidence_ordinal": item.evidence_ordinal, "page_number": item.page_number,
                            "quote": item.quote, "char_start": item.char_start, "char_end": item.char_end, "block_id": None})
            canonical = head["canonical_observation_id"] if head else observations[0]
            if head is None:
                session.execute(_SET_CANONICAL, {"finding_uid": target, "canonical_observation_id": canonical})
            published.append(PublishedCandidateFinding(target, group.group_id, category, kind.stage_id,
                canonical, tuple(observations), next((uid for uid in sorted(related_uids) if uid != target), None), evidence_count))
    return CandidatePublicationResult(run_id, published=tuple(published), unread=tuple(gaps))
