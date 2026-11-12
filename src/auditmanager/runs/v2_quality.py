"""The substantive pass inside v2's existing critic; all calls use the ordinary Run custody."""
from __future__ import annotations

from copy import deepcopy

from auditmanager.analysis.public import (build_substantive_review_request,
    parse_substantive_review_reply, plan_substantive_review_batches,
    select_related_review_context, verify_review_passport_crop)
from auditmanager.storage.public import parse_blob_id
from auditmanager.executors.public import CropImage, attach_images


def run_substantive_critic(*, state, run, model_id, settings, store, pages, related_index, call, phase,
        proposal_policy=None):
    builder, parser = build_substantive_review_request, parse_substantive_review_reply
    if proposal_policy is not None:
        from auditmanager.analysis.public import (validate_finding_proposal_policy,
            build_finding_proposal_review_request, parse_finding_proposal_review_reply)
        validate_finding_proposal_policy(proposal_policy)
        builder, parser = build_finding_proposal_review_request, parse_finding_proposal_review_reply
    observations = state["observations"]
    for item in observations:
        item["structural_critic"] = deepcopy(item.get("critic", {}))
        item["critic"] = {"mode": "substantive", "model_called": False, "original_verdict": "not_reviewed",
            "llm_decision": "needs_human", "evidence_checked": False,
            "source_dependency": "needs_more_context", "source_evidence": [], "visual_evidence": [],
            "explanation": "Содержательная проверка ещё не выполнена.", "expert_decision": False}
        item["review_status"] = "not_reviewed"
    registry = {source["source_id"]: source for source in state["sources"]}
    batches = plan_substantive_review_batches(observations, groups=state.get("consolidated_observations", []),
        sources=state["sources"])
    gap = False
    receipts = state.setdefault("substantive_review", {"version": "substantive-v2-v1", "batches": [],
        "model_called": False, "expert_decisions_written": False})
    for number, items in enumerate(batches):
        used_ids = {ref for item in items for ref in item["source_ids"]}
        selected = [dict(registry[ref]) for ref in sorted(used_ids) if ref in registry]
        page_numbers = {source.get("page_number") for source in selected}
        related = select_related_review_context(related_index,
            texts=[item["title"] + " " + item["description"] for item in items], page_numbers=page_numbers)
        for source in related["sources"]:
            if source["source_id"] not in registry:
                registry[source["source_id"]] = source
                state["sources"].append(source)
        selected.extend(source for source in related["sources"] if source["source_id"] not in used_ids)
        images = []
        for source in selected:
            if source["kind"] == "image":
                raw = store.read(parse_blob_id(source["blob_id"]), verify=True)
                verify_review_passport_crop(state["input_passport"], source, raw)
                images.append(CropImage(source["source_id"], raw))
            elif not isinstance(source.get("quote", ""), str) or source.get("quote", "") not in pages.get(source.get("page_number"), ""):
                # A model's earlier proposed quotation is not promoted to a literal source.
                source["quote"] = ""
        for item in items:
            item_pages = {registry[ref].get("page_number") for ref in item["source_ids"] if ref in registry}
            item["evidence_source_ids"] = sorted(set(item["source_ids"]) | {
                source["source_id"] for source in related["sources"] if source["page_number"] in item_pages
                or any(key in source["object_keys"] for key in related_index_keys(item))})
            item["context_complete"] = not related["omitted_source_ids"] and all(ref in registry for ref in item["source_ids"])
        identity = f"finding_review:substantive:{number}"
        response = None
        rejected = []
        try:
            request = builder(model_id=model_id, settings=settings, run_id=run.run_id,
                section=state["section"], items=items, sources=selected, context=related,
                image_ids={image.crop_id for image in images})
            request = attach_images(request, images)
            response = call(request, identity)
            receipts["model_called"] = True
            next(p for p in state["procedures"] if p["id"] == "finding_review")["model_called"] = True
            indexed = {item["input_id"]: item for item in items}
            parsed = parser(response.output_text, inputs=indexed, sources=selected,
                attached_image_ids={image.crop_id for image in images}, rejected=rejected)
            if response.truncated:
                rejected.append({"reason": "extended_response_truncated"})
        except (ValueError, TypeError, KeyError) as error:
            parsed = []
            rejected.append({"reason": str(error)})
        accepted = {row["input_id"]: row for row in parsed}
        for item in observations:
            key = item["observation_id"]
            if key in accepted:
                item.update(critic=accepted[key], review_status="reviewed")
                if proposal_policy is not None:
                    item["proposed_severity"] = accepted[key]["proposed_severity"]
                    item["recommendation_text"] = accepted[key]["recommendation_text"]
                item.pop("review_reason", None)
            elif key in {row["input_id"] for row in items}:
                item["review_reason"] = "substantive_review_reply_refused"
        missing = [item["input_id"] for item in items if item["input_id"] not in accepted]
        gap |= bool(rejected or missing)
        receipt = {"identity": identity, "input_ids": [item["input_id"] for item in items],
            "accepted": len(accepted), "missing_input_ids": missing, "rejected_records": rejected,
            "context_complete": related["complete"], "omitted_context_source_ids": related["omitted_source_ids"],
            "request_sha256": request.request_sha256 if response is not None else None,
            "response_sha256": response.response_sha256 if response is not None else None}
        receipts["batches"].append(receipt)
        phase("finding_review", "running")
    receipts.update(reviewed=sum(item["review_status"] == "reviewed" for item in observations),
        passed=sum(item["critic"].get("original_verdict") == "pass" for item in observations),
        requires_context=sum(item["critic"].get("llm_decision") == "needs_human" for item in observations))
    return gap


def related_index_keys(item):
    # The public selector performs the literal designation matching; reuse it with an empty index.
    empty = {"by_object": {}, "excerpts": []}
    return select_related_review_context(empty, texts=[item["title"] + " " + item["description"]], page_numbers=set())["object_keys"]
