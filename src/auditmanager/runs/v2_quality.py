"""The substantive pass inside v2's existing critic; all calls use the ordinary Run custody."""
from __future__ import annotations

from copy import deepcopy
import re

from auditmanager.analysis.public import (build_substantive_review_request,
    parse_substantive_review_reply, plan_substantive_review_batches,
    select_related_review_context, verify_review_passport_crop)
from auditmanager.storage.public import parse_blob_id
from auditmanager.executors.public import CropImage, attach_images


def run_substantive_critic(*, state, run, model_id, settings, store, pages, related_index, call, phase,
        proposal_policy=None, flow_policy=None):
    if flow_policy is not None:
        return _run_flow_critic(state=state, run=run, model_id=model_id, settings=settings, store=store,
            pages=pages, related_index=related_index, call=call, phase=phase,
            proposal_policy=proposal_policy, flow_policy=flow_policy)
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


def _run_flow_critic(*, state, run, model_id, settings, store, pages, related_index, call, phase,
        proposal_policy, flow_policy):
    from auditmanager.analysis.public import validate_flow_repair_policy, flow_repair_helper
    from auditmanager.findings.public import CandidateGroup, classify_group
    from .extended_review import _candidate_member, _candidate_words
    validate_flow_repair_policy(flow_policy)
    observations = state["observations"]
    for item in observations:
        item["structural_critic"] = deepcopy(item.get("critic", {}))
        item["critic"] = {"mode": "substantive", "model_called": False, "original_verdict": "not_reviewed",
            "llm_decision": "needs_human", "evidence_checked": False,
            "source_dependency": "needs_more_context", "source_evidence": [], "visual_evidence": [],
            "explanation": "Содержательная проверка ещё не выполнена.", "expert_decision": False}
        item["review_status"] = "not_reviewed"
    registry = {source["source_id"]: source for source in state["sources"]}
    primary_ordinals = {ref: int(ref.split(":", 1)[1]) for ref in registry
        if ref.startswith("text:") and ref.split(":", 1)[1].isdigit()}
    query_categories = {}
    for group in state.get("consolidated_observations", []):
        raw_members = [observations[origin["raw_index"]] for origin in group["origin_records"]]
        members = [_candidate_member(item, registry=registry, conflicts=set(), ordinals=primary_ordinals, reviewable=True)
            for item in raw_members]
        members = [member for member in members if member is not None]
        if not members:
            continue
        category = classify_group(CandidateGroup(group["group_id"], tuple(members))).category
        primary = {ordinal for member in members for ordinal in member.primary_text_ordinals}
        if len(primary) == 1:
            originals = [item.get("original_primary_observation", {}) for item in raw_members
                if item.get("original_primary_observation")]
            if originals and isinstance(originals[0].get("category"), str):
                category = originals[0]["category"]
        query_categories.update({item["observation_id"]: category for item in raw_members})
    receipts = state.setdefault("substantive_review", {"version": "v2-flow-repair-v1", "batches": [],
        "model_called": False, "expert_decisions_written": False})
    batches = plan_substantive_review_batches(observations, groups=state.get("consolidated_observations", []),
        sources=state["sources"])
    gap = False
    for number, items in enumerate(batches):
        used = {ref for item in items for ref in item["source_ids"]}
        selected = [deepcopy(registry[ref]) for ref in sorted(used) if ref in registry]
        related = select_related_review_context(related_index,
            texts=[item["title"] + " " + item["description"] for item in items],
            page_numbers={source.get("page_number") for source in selected})
        for source in related["sources"]:
            if source["source_id"] not in registry:
                registry[source["source_id"]] = source; state["sources"].append(source)
            if source["source_id"] not in used:
                selected.append(deepcopy(source))
        images = []
        for source in selected:
            if source["kind"] == "image":
                raw = store.read(parse_blob_id(source["blob_id"]), verify=True)
                verify_review_passport_crop(state["input_passport"], source, raw)
                images.append(CropImage(source["source_id"], raw))
            elif source.get("quote", "") not in pages.get(source.get("page_number"), ""):
                source["quote"] = ""
            elif source.get("source_type") == "native_text":
                source["quote"] = flow_repair_helper("relevant_quote", source.get("quote", ""), items)
        for item in items:
            original = next(row for row in observations if row["observation_id"] == item["input_id"])
            item["normative_context"] = deepcopy(original.get("normative_context"))
            member = _candidate_member(original, registry=registry, conflicts=set(), ordinals=primary_ordinals, reviewable=True)
            primary_original = original.get("original_primary_observation", {})
            item.update(category=query_categories.get(item["input_id"], "drawing_discrepancy"),
                finding_text=primary_original.get("finding_text") or _candidate_words(original),
                recommendation_text=primary_original.get("recommendation_text") or
                    (member.recommendation_text if member is not None else "Требуется проверка эксперта по источнику"))
            item_pages = {registry[ref].get("page_number") for ref in item["source_ids"] if ref in registry}
            item["evidence_source_ids"] = sorted(set(item["source_ids"]) | {
                source["source_id"] for source in related["sources"] if source.get("page_number") in item_pages
                or set(source.get("object_keys", [])) & set(related_index_keys(item))})
            # Additional omitted sources are not mandatory for every other claim.
            item["context_complete"] = all(ref in registry and (registry[ref].get("kind") == "image"
                or bool(registry[ref].get("quote"))) for ref in item["source_ids"])
            item["required_source_ids"] = list(item["source_ids"])
            absent = re.search(r"\b(?:отсутств\w*|нет|не\s+(?:предусмотр\w*|указан\w*|показан\w*|привед\w*))\b",
                item["title"] + " " + item["description"], re.I) is not None
            if absent:
                own_keys = set(related_index_keys(item))
                essential = {source["source_id"] for source in related_index.get("excerpts", [])
                    if own_keys & set(source.get("object_keys", []))}
                omitted = sorted(essential & set(related["omitted_source_ids"]))
                item["absence_guard"] = {"required_related_source_ids": sorted(essential),
                    "missing_required_source_ids": omitted,
                    "complete_document_claim": False, "outcome": "requires_human_source_check"}
                # A bounded fragment never proves a document-wide absence. This
                # is evidence uncertainty, not an execution gap or an exclusion.
                item["context_complete"] = False
        identity = f"finding_review:substantive:{number}"
        indexed = {item["input_id"]: item for item in items}
        rejected = []; accepted = []; response = None
        request = flow_repair_helper("build_flow_review_request", proposals=proposal_policy is not None,
            model_id=model_id, settings=settings, run_id=run.run_id, section=state["section"],
            items=items, sources=selected, context=related, image_ids={image.crop_id for image in images})
        request = attach_images(request, images)
        def parse(text, collector):
            try:
                return flow_repair_helper("parse_flow_review_reply", text, inputs=indexed, sources=selected,
                    attached_image_ids={image.crop_id for image in images}, rejected=collector,
                    proposals=proposal_policy is not None)
            except (ValueError, TypeError, KeyError) as error:
                collector.append({"reason": str(error) if str(error).isidentifier() else "reply_unreadable"})
                return []
        response = call(request, identity)
        dispatched = getattr(call, "dispatch_receipts", {}).get(identity, {})
        actual_request_sha256 = dispatched.get("request_sha256", request.request_sha256)
        receipts["model_called"] = True
        next(p for p in state["procedures"] if p["id"] == "finding_review")["model_called"] = True
        accepted = parse(response.output_text, rejected)
        if response.truncated:
            rejected.append({"reason": "extended_response_truncated"})
        original_refusals = deepcopy(rejected)
        valid = {row["input_id"] for row in accepted}
        missing = [key for key in indexed if key not in valid]
        repair = None
        if missing:
            # A second provider call must not be the first durable save of the
            # valid first response. Unknown repair outcomes retain these rows.
            first_valid = {row["input_id"]: row for row in accepted}
            for original in observations:
                if original["observation_id"] in first_valid:
                    row = first_valid[original["observation_id"]]
                    original.update(critic=row, review_status="reviewed")
                    if proposal_policy is not None:
                        original.update(proposed_severity=row["proposed_severity"],
                            recommendation_text=row["recommendation_text"])
            if first_valid:
                phase("finding_review", "running")
            feedback = [*rejected, *({"reason": "review_input_missing", "input_id": key} for key in missing)]
            # Already validated records remain authoritative; repair only missing
            # records and preserve their exact original sources and attachments.
            repaired_request = flow_repair_helper("build_flow_repair_request", request,
                rejected=feedback[:128], accepted_records=accepted,
                reply_sha256=response.response_sha256, procedure="finding_review", missing_input_ids=missing,
                origin_request_sha256=actual_request_sha256)
            repaired_response = call(repaired_request, identity + ":repair:1")
            rejected = []
            repaired = parse(repaired_response.output_text, rejected)
            accepted.extend(row for row in repaired if row["input_id"] not in valid)
            if repaired_response.truncated:
                rejected.append({"reason": "extended_response_truncated"})
            repair = {"attempt": 1, "request_sha256": repaired_request.request_sha256,
                "response_sha256": repaired_response.response_sha256, "rejected_records": deepcopy(rejected)}
            repair["request_sha256"] = getattr(call, "dispatch_receipts", {}).get(identity + ":repair:1", {}).get(
                "request_sha256", repaired_request.request_sha256)
        accepted_by_id = {row["input_id"]: row for row in accepted}
        for item in observations:
            key = item["observation_id"]
            if key in accepted_by_id:
                item.update(critic=accepted_by_id[key], review_status="reviewed")
                if proposal_policy is not None:
                    item.update(proposed_severity=accepted_by_id[key]["proposed_severity"],
                        recommendation_text=accepted_by_id[key]["recommendation_text"])
                item.pop("review_reason", None)
            elif key in indexed:
                item["review_reason"] = "substantive_review_reply_refused"
        accounting = flow_repair_helper("review_accounting", items, accepted, rejected)
        gap |= not accounting["complete"]
        receipts["batches"].append({"identity": identity, "input_ids": list(indexed),
            "accepted": len(accepted_by_id), **accounting, "rejected_records": original_refusals,
            "context_complete": all(item["context_complete"] for item in items),
            "omitted_context_source_ids": related["omitted_source_ids"],
            "request_sha256": actual_request_sha256, "response_sha256": response.response_sha256,
            "human_reference_receipt": dispatched.get("human_reference_receipt", {}),
            **({"repair": repair} if repair else {})})
        phase("finding_review", "running")
    receipts.update(reviewed=sum(item["review_status"] == "reviewed" for item in observations),
        passed=sum(item["critic"].get("original_verdict") == "pass" for item in observations),
        requires_context=sum(item["critic"].get("llm_decision") == "needs_human" for item in observations))
    next(p for p in state["procedures"] if p["id"] == "finding_review")["input_accounting"] = {
        "expected": len(observations), "valid": receipts["reviewed"],
        "pending": len(observations)-receipts["reviewed"], "refused": 0, "excluded": 0}
    return gap
