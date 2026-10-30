"""Deterministic report projection over saved native-text V3 evidence.

This module adds no model work and does not reinterpret a verification verdict.
The source catalogue is built from pinned fragments, not model-provided boxes.
"""
from __future__ import annotations

from copy import deepcopy

from auditmanager.comparison.stage_ai.validation import StageAiValidationError, digest

REPORT_VERSION = "stage-v3-source-report/1"


def source_catalogue(snapshot, records):
    fragments = {row["stage_text_fragment_id"]: row for row in snapshot["fragments"]}
    profiles = {row["profile_id"]: row for row in snapshot["all_profiles"]}
    sources = {}
    for (side, physical_page), page in sorted(records.items()):
        for block in page["blocks"]:
            fragment = fragments[block["block_id"]]
            if fragment["page_profile_id"] != page["profile_id"]:
                raise StageAiValidationError("v3_report_source_binding_invalid")
            sources[block["block_id"]] = {
                "source_id": block["block_id"], "side": "left" if side == "OLD" else "right",
                "original_side": side, "physical_page": physical_page,
                "profile_id": page["profile_id"], "version_uid": page["source_pdf"],
                "page_number": page["original_page_number"],
                "box_anchor": deepcopy(fragment["box_anchor"]),
                "content_key": fragment["content_key"],
                "page_content_key": profiles[page["profile_id"]]["content_key"],
                "quote": fragment["normalised_text"], "quote_source": "saved_native_fragment",
            }
    return sources


def parameter_projection(*, event, parameter, ordinal, work, catalogue):
    event_refs = sorted({row["block_id"] for row in event["evidence_items"]})
    if any(reference not in catalogue for reference in event_refs):
        raise StageAiValidationError("v3_report_event_source_unavailable")
    result = None if work is None else work.get("result")
    verification_refs = []
    if result is not None:
        for reference in result["evidence_refs"]:
            actual = catalogue.get(reference["block_id"])
            if (actual is None or actual["original_side"] != reference["side"]
                    or actual["physical_page"] != reference["physical_page"]):
                raise StageAiValidationError("v3_report_verification_source_invalid")
            verification_refs.append(reference["block_id"])
    return deepcopy(parameter) | {
        "parameter_id": "v3p_" + digest({"event_id": event["projectchange_id"],
            "ordinal": ordinal, "parameter": parameter, "event_source_ids": event_refs})[:32],
        "event_id": event["projectchange_id"], "ordinal": ordinal,
        "verification_work_item_id": None if work is None else work["work_item_id"],
        "verification": deepcopy(result), "event_source_ids": event_refs,
        "verification_source_ids": sorted(set(verification_refs)),
    }


def event_projection(event, catalogue):
    refs = sorted({row["block_id"] for row in event["evidence_items"]})
    if any(reference not in catalogue for reference in refs):
        raise StageAiValidationError("v3_report_event_source_unavailable")
    return {
        "report_version": REPORT_VERSION,
        "scope": event["scope"], "locations": deepcopy(event["locations"]),
        "old_state": event["old_state"], "new_state": event["new_state"],
        "modalities": deepcopy(event["modalities"]), "model_confidence": event["confidence"],
        "why_one_event": event["why_one_event"],
        "event_evidence": deepcopy(event["evidence_items"]),
        "sources": [deepcopy(catalogue[reference]) for reference in refs],
    }


def merge_sources(target, incoming):
    """Union actual anchors when the existing card partition joins events."""
    sources = {source["source_id"]: source for source in target.get("sources", [])}
    for source in incoming.get("sources", []):
        previous = sources.get(source["source_id"])
        if previous is not None and previous != source:
            raise StageAiValidationError("v3_report_source_identity_conflict")
        sources[source["source_id"]] = deepcopy(source)
    target["sources"] = [sources[key] for key in sorted(sources)]


def source_report(snapshot, records, coverage, quality):
    """Include every admitted pinned fragment, also when no event was found."""
    catalogue = source_catalogue(snapshot, records)
    pages = []
    for original in coverage["pages"]:
        page = records[(original["side"], original["physical_page"])]
        pages.append(deepcopy(original) | {"side": "left" if original["side"] == "OLD" else "right",
            "original_side": original["side"], "profile_id": page["profile_id"],
            "version_uid": page["source_pdf"], "page_number": page["original_page_number"]})
    return {"report_version": REPORT_VERSION,
        "stage_pair_id": snapshot["stage_pair_id"], "stage_link_revision_id": snapshot["stage_link_revision_id"],
        "source_sha256": digest([catalogue[key] for key in sorted(catalogue)]),
        "source_catalogue": [catalogue[key] for key in sorted(catalogue)],
        "coverage": {"summary": deepcopy(coverage["summary"]), "pages": pages},
        "quality": deepcopy(quality["summary"]), "native_text_only": True, "norms_status": "not_checked"}
