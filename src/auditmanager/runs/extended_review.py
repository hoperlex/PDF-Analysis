"""Bounded multimodal preliminary review under an ordinary Run's durable authority."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
import math
from typing import Any

from auditmanager.analysis.public import (ModelCallRecord, ModelRequest, ModelResponse, ProviderMode,
    build_extended_request, extended_digest, finalize_extended_items,
    parse_extended_reply, plan_extended_inputs, EXTENDED_REVIEW_ROLE, EXTENDED_REPLY_ROLE,
    pinned_models, request_cost_upper_usd, require_approved_model, extended_block_payload)
from auditmanager.documents.public import DocumentRepository
from auditmanager.executors.public import CropImage, attach_images
from auditmanager.jobs.public import extended_unit
from auditmanager.norms.public import search_norms
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId
from auditmanager.storage.public import parse_blob_id


FORMAT = "extended-review-v1"


def _refuse(reason: str):
    return DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason=reason)


def _response_payload(response: ModelResponse) -> dict:
    value = asdict(response)
    if (not isinstance(response.output_text, str) or len(response.output_text.encode()) > 2_097_152
            or any(type(getattr(response, k)) is not int or getattr(response, k) < 0
                   for k in ("input_tokens", "output_tokens", "latency_ms"))
            or response.reported_cost_usd is not None and (isinstance(response.reported_cost_usd, bool)
                or not isinstance(response.reported_cost_usd, (int, float))
                or not math.isfinite(response.reported_cost_usd) or response.reported_cost_usd < 0)):
        raise _refuse("extended_response_invalid")
    return value


def _saved_response(store, row: dict, request: ModelRequest, binding) -> ModelResponse:
    p = row["parameters"]
    try:
        raw = store.read(parse_blob_id(p["extended_reply_blob_id"]), verify=True)
        if (len(raw) != p["extended_reply_size"] or hashlib.sha256(raw).hexdigest() != p["extended_reply_sha256"]
                or row["request_sha256"] != request.request_sha256
                or row["model_identity"] != request.model_id
                or row["provider_mode"] != binding.adapter.provider_mode.value):
            raise ValueError()
        doc = json.loads(raw)
        response = ModelResponse(**doc["response"])
        _response_payload(response)
        if response.response_sha256 != row["response_sha256"] or doc["request_sha256"] != request.request_sha256:
            raise ValueError()
        return response
    except (KeyError, TypeError, ValueError):
        raise _refuse("extended_saved_reply_invalid") from None


def _call(session, *, run_id, authority, jobs, journal, binding, request, phase, source_sha256,
          meter, store, publish, checkpoint):
    checkpoint("extended_before_call")
    key = extended_digest({"format": FORMAT, "source": source_sha256, "phase": phase,
        "request": request.request_sha256, "model": request.model_id,
        "connection": None if binding.call is None else binding.call.connection_revision_id})
    saved = extended_unit(session, run_id=run_id, unit_key=key, source_sha256=source_sha256, phase=phase)
    session.commit()  # no read/authority lock survives external Blob I/O
    if saved is not None:
        return _saved_response(store, saved, request, binding), True
    pin = next((p for p in pinned_models() if p.model_id == request.model_id), None)
    if pin is None:
        raise _refuse("extended_model_price_unavailable")
    require_approved_model(binding.config, pin, binding.call)
    meter.check_before_call(pending_cost_usd=request_cost_upper_usd(pin, request))
    params = {**request.parameters, "extended_unit_key": key, "extended_source_sha256": source_sha256,
              "extended_phase": phase}
    # Re-use the standard journal callbacks, preserving the extra immutable unit
    # parameters both at intent and completion, without pretending this is a text window.
    provider = "anthropic" if binding.call is None else binding.call.provider_label
    jobs.require_current(session, authority)
    call_id = jobs.prepare_provider_call(session, authority, provider=provider,
        model_identity=request.model_id, provider_mode=binding.adapter.provider_mode.value,
        parameters=params, request_sha256=request.request_sha256,
        connection_revision_id=None if binding.call is None else binding.call.connection_revision_id,
        identity_basis=None if binding.call is None else binding.call.identity_basis)
    session.commit()
    checkpoint("extended_intent_committed")
    try:
        response = binding.adapter.complete(request)
    except Exception as error:
        dispatch = getattr(error, "dispatch_class", None)
        code = error if isinstance(error, DomainError) else _refuse("extended_provider_failed")
        if binding.adapter.provider_mode is ProviderMode.RECORDED or dispatch in {"not_sent", "rate_limited", "proxy_unavailable", "definite_refusal"}:
            journal.not_processed(call_id, code, "not_sent" if dispatch is None else dispatch)
        else:
            journal.outcome_unknown(call_id, code)
        raise code
    if not isinstance(response, ModelResponse):
        journal.outcome_unknown(call_id, _refuse("extended_response_invalid"))
        raise _refuse("extended_response_invalid")
    journal.response_received(call_id, response)
    response_payload = _response_payload(response)
    ref = publish(EXTENDED_REPLY_ROLE, {"format": FORMAT, "kind": "reply",
        "source_sha256": source_sha256, "unit_key": key,
        "request_sha256": request.request_sha256, "response": response_payload})
    params.update(extended_reply_blob_id=ref.blob_id, extended_reply_sha256=ref.sha256,
                  extended_reply_size=ref.size_bytes)
    unmetered = binding.call is not None and binding.call.unmetered
    cost = 0.0 if unmetered else (response.reported_cost_usd if response.reported_cost_usd is not None
        else pin.cost_usd(input_tokens=response.input_tokens, output_tokens=response.output_tokens))
    budget_error = None
    try:
        if unmetered:
            meter.record_unmetered()
        else:
            meter.charge(pin, input_tokens=response.input_tokens, output_tokens=response.output_tokens,
                reported_cost_usd=response.reported_cost_usd)
    except DomainError as error:
        budget_error = error
    journal.complete(ModelCallRecord(model_call_id=ModelCallId.parse(str(call_id)), provider=provider,
        model_id=request.model_id, provider_mode=binding.adapter.provider_mode, parameters=params,
        request_sha256=request.request_sha256, response_sha256=response.response_sha256,
        input_tokens=response.input_tokens, output_tokens=response.output_tokens, latency_ms=response.latency_ms,
        status="truncated" if response.truncated else "succeeded", cost_usd=float(cost),
        cost_basis="unmetered" if unmetered else "measured" if response.reported_cost_usd is not None else "estimated"))
    if budget_error is not None:
        raise budget_error
    if (binding.call is not None and binding.call.check_identity
            and response.model != binding.call.expected_model):
        raise _refuse("extended_model_identity_mismatch")
    return response, False


def _norms(session, observations: list[dict], snapshot_id: str | None) -> list[str]:
    # Candidate retrieval is deterministic corpus lookup, never edition validation.
    available = snapshot_id is not None
    cache: dict[str, list[dict]] = {}
    calls = 0
    warnings = []
    for item in observations:
        queries = item.pop("norm_queries", [])
        if not available or not queries:
            item["norm_status"] = "unavailable"
            item["norm_reason"] = "corpus_unavailable" if not available else "query_not_proposed"
            continue
        candidates = []
        try:
            for query in queries[:2]:
                key = " ".join(query.casefold().split())
                if key not in cache:
                    if calls >= 12:
                        item["norm_reason"] = "lookup_window_exhausted"
                        warnings.append("norm_lookup_window_exhausted")
                        break
                    calls += 1
                    page = search_norms(session, q=query, norms_snapshot_id=snapshot_id,
                        cursor=None, limit=3, timeout_ms=1200)
                    cache[key] = [{"snapshot_id": hit.norms_snapshot_id, "document_id": hit.norm_document_id,
                        "paragraph_id": hit.norm_paragraph_id, "designation": hit.designation,
                        "clause_number": hit.clause_number, "quote": hit.fragment.text[:2000],
                        "page_label": hit.page_label, "status": "candidate_not_verified"} for hit in page.items]
                for candidate in cache[key]:
                    if any(c["paragraph_id"] == candidate["paragraph_id"] for c in candidates):
                        continue
                    candidates.append(candidate)
            item["norm_status"] = "candidates" if candidates else "unavailable" if item.get("norm_reason") == "lookup_window_exhausted" else "not_found"
            item["norm_candidates"] = candidates[:6]
        except DomainError:
            session.rollback()
            item["norm_status"] = "unavailable"
            item["norm_reason"] = "lookup_unavailable"
    return sorted(set(warnings))


def run_extended_review(session, *, run, authority, jobs, journal, binding, outputs, store, meter,
                        publish, progress, checkpoint, observations_document, snapshot_id=None, profile_sha256=None,
                        policy=None, bind_native=None) -> dict:
    """At most two eight-image calls and one semantic merge; progress is caller-custodied."""
    if isinstance(policy, dict) and policy.get("plan_version") == "extended-review-v2":
        return _run_workflow_v2(session,run=run,authority=authority,jobs=jobs,journal=journal,binding=binding,
            outputs=outputs,store=store,meter=meter,publish=publish,progress=progress,checkpoint=checkpoint,
            observations_document=observations_document,snapshot_id=snapshot_id,profile_sha256=profile_sha256,
            bind_native=bind_native)
    from auditmanager.analysis.public import read_artifact
    state: dict[str, Any] = {"format": FORMAT, "preliminary": True, "section": "unknown",
        "observations": [], "sources": [], "warnings": [], "coverage": {
            "blocks_total": 0, "blocks_selected": 0, "blocks_processed": 0, "blocks_remaining": 0, "skipped": []}}
    def save(status):
        # Do not expose internal block contexts or model prompt material in the read DTO.
        public = {k: v for k, v in state.items() if k not in {"text_items", "context_sections"}}
        public["sources"] = [{k: v for k, v in source.items() if k != "context"} for source in state["sources"]]
        progress(status, public)
    try:
        doc = DocumentRepository().get_version(session, run.version_uid)
        section = doc.classification.section_code if doc.classification is not None else "unknown"
        state["section"] = section
        inputs = {}
        for key in ("geometry.portal_blocks", "geometry.page_crops", "prepared.text_layer", "context.document_graph"):
            ref = outputs.refs.get(key)
            if ref is None:
                state["warnings"].append("source_geometry_unavailable")
                save("unavailable")
                return state
            inputs[key], _ = read_artifact(store, parse_blob_id(ref.blob_id), expected_role=key)
        recognised = None
        recognised_ref = outputs.refs.get("prepared.recognised_text")
        if recognised_ref is not None:
            recognised, _ = read_artifact(store, parse_blob_id(recognised_ref.blob_id), expected_role="prepared.recognised_text")
        state = plan_extended_inputs(version_uid=run.version_uid, section=section,
            portal=inputs["geometry.portal_blocks"], manifest=inputs["geometry.page_crops"],
            text_layer=inputs["prepared.text_layer"], graph=inputs["context.document_graph"], observations=observations_document,
            recognised=recognised)
        state["source_sha256"] = extended_digest({"source": state["source_sha256"],
            "profile_sha256": profile_sha256, "norms_snapshot_id": snapshot_id, "analysis_profile_id": getattr(run, "analysis_profile_id", None),
            "prompt_bundle_id": getattr(run, "prompt_bundle_id", None), "run_input_digest": getattr(run, "frozen_input_digest", None)})
        state["model_id"] = binding.config.model_id
        state["provider_mode"] = binding.adapter.provider_mode.value
        save("running")
        images = [s for s in state["sources"] if s["kind"] == "image"]
        if not images:
            state["observations"] = finalize_extended_items(state["text_items"], state["sources"])
            state["warnings"].extend(_norms(session, state["observations"], snapshot_id))
            state["warnings"].append("no_image_blocks_available")
            save("unavailable")
            return state
        block_items = []
        for start in range(0, len(images), 8):
            batch = images[start:start+8]
            crops = []
            for source in batch:
                raw = store.read(parse_blob_id(source["blob_id"]), verify=True)
                if len(raw) != source["size_bytes"] or hashlib.sha256(raw).hexdigest() != source["crop_sha256"]:
                    raise _refuse("extended_crop_digest_invalid")
                crops.append(CropImage(source["source_id"], raw))
            payload, context_cut = extended_block_payload(section=section, batch=batch,
                sections=state["context_sections"], coverage=state["coverage"])
            if context_cut and "page_context_truncated" not in state["warnings"]:
                state["warnings"].append("page_context_truncated")
            request = attach_images(build_extended_request(model_id=binding.config.model_id, run_id=run.run_id,
                phase="blocks", section=section, payload=payload), crops)
            response, reused = _call(session, run_id=run.run_id, authority=authority, jobs=jobs, journal=journal,
                binding=binding, request=request, phase=f"blocks:{start//8}", source_sha256=state["source_sha256"],
                meter=meter, store=store, publish=publish, checkpoint=checkpoint)
            if response.truncated:
                raise _refuse("extended_response_truncated")
            block_items.extend(parse_extended_reply(response.output_text,
                allowed_sources={s["source_id"] for s in batch}))
            state["coverage"]["blocks_processed"] += len(batch)
            state["coverage"]["blocks_remaining"] = state["coverage"]["blocks_total"] - state["coverage"]["blocks_processed"]
            state["observations"] = finalize_extended_items(block_items, state["sources"])
            save("running")
        items = finalize_extended_items([*state["text_items"], *block_items], state["sources"])
        state["warnings"].extend(_norms(session, items, snapshot_id))
        # Search excerpts can differ by query for one paragraph. Freeze one real
        # excerpt per ID, shared by both the model context and its validation.
        norm_context = {}
        for item in items:
            item["norm_candidates"] = [norm_context.setdefault(c["paragraph_id"], c)
                for c in item["norm_candidates"]]
        # Persist the original source-bound observations before model review.
        # A malformed/failed merge must not erase either text or visual inputs.
        state["observations"] = items
        save("running")
        indexed = {"xmi_"+extended_digest({"ordinal": i, "observation": item})[:24]: item for i, item in enumerate(items)}
        if any(len(item["description"]) > 800 for item in items):
            state["warnings"].append("merge_context_truncated")
        request = build_extended_request(model_id=binding.config.model_id, run_id=run.run_id, phase="merge",
            section=section, payload={"observations": [{
                "title": item["title"], "description": item["description"][:800], "source_ids": item["source_ids"],
                "norm_candidate_ids": [c["paragraph_id"] for c in item["norm_candidates"]],
                "norm_status": item["norm_status"], "input_id": key} for key, item in indexed.items()],
                "norm_context": list(norm_context.values()), "norm_review_version": "quote-review-v1",
                "sources": [{k:v for k,v in s.items() if k != "context"}
                for s in state["sources"]], "source_sha256": state["source_sha256"]})
        response, reused = _call(session, run_id=run.run_id, authority=authority, jobs=jobs, journal=journal,
            binding=binding, request=request, phase="merge", source_sha256=state["source_sha256"],
            meter=meter, store=store, publish=publish, checkpoint=checkpoint)
        if response.truncated:
            raise _refuse("extended_response_truncated")
        merged = parse_extended_reply(response.output_text, allowed_sources={s["source_id"] for s in state["sources"]}, expected_inputs=indexed)
        represented = {k for item in merged for k in item["input_ids"]}
        # A semantic merge may consolidate but never silently lose an input observation.
        omitted = [item for key, item in indexed.items() if key not in represented]
        if omitted:
            state["warnings"].append("merge_omitted_sources_retained")
            merged.extend(omitted)
        for item in merged:
            ids = item.pop("input_ids", None)
            if ids is None:  # retained original observation after an omitted merge input
                continue
            candidates = {c["paragraph_id"]: c for key in ids for c in indexed[key]["norm_candidates"]}
            item["norm_candidates"] = list(candidates.values())
            item["norm_status"] = "candidates" if candidates else "unavailable"
            if not candidates:
                item["norm_reason"] = "no_candidate_context"
        state["observations"] = finalize_extended_items(merged, state["sources"])
        status = "partial" if state["coverage"]["blocks_remaining"] or state["warnings"] else "completed"
        save(status)
        return state
    except (DomainError, ValueError, KeyError, TypeError) as error:
        reason = error.detail_fields.get("reason") if isinstance(error, DomainError) else "extended_reply_or_source_invalid"
        state["warnings"].append(str(reason or "extended_review_failed"))
        # These remain explicit preliminary candidates, not canonical publication.
        for item in state.get("observations", []):
            item.pop("norm_queries", None)
        save("failed")
        return state


def read_extended_review(sessions, blob_store, run_id: str) -> dict:
    with sessions() as session:
        run = RunRepository().get(session, run_id)
        rows = RunRepository().stage_results(session, run_id)
        stage = next((s for s in rows if s.stage_id == "text_analysis"), None)
        refs = [] if stage is None else stage.artifacts
        ref = next((r for r in refs if r.get("role") == EXTENDED_REVIEW_ROLE), None)
        if ref is None:
            from auditmanager.runs.cost_policy import read_run_cost_policy
            policy = read_run_cost_policy(session,run_id=run_id,default_ceiling_usd=1.).extended_review
            if isinstance(policy,dict) and policy.get("plan_version")=="extended-review-v2":
                terminal = run.state in {"published","partial","failed","cancelled"}
                reason = "workflow_not_executed" if terminal else None
                if terminal and any(row.stage_id != "text_analysis" and row.status in {"failed","partial"} for row in rows):
                    reason = "source_preparation_failed"
                return {"run_id":run_id,"status":"unavailable" if terminal else "not_started",
                    "result":planned_workflow_result(reason=reason,terminal=terminal)}
            return {"run_id":run_id,"status":"unavailable","result":{
                "workflow_version":"extended-review-v1" if policy else None,"procedures":[],
                "reason":"legacy_policy_no_v2_workflow" if policy else "not_in_accepted_policy"}}

        version_uid = run.version_uid
    raw = blob_store.read(parse_blob_id(ref["blob_id"]), verify=True)
    if len(raw) != ref["size_bytes"] or hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role=EXTENDED_REVIEW_ROLE)
    try:
        doc = json.loads(raw)
        status = doc["status"]
        if (doc.get("artifact_role") != EXTENDED_REVIEW_ROLE or doc.get("version_uid") != version_uid
                or doc.get("run_id") != run_id or status not in {"running","completed","partial","failed","unavailable"}):
            raise ValueError()
        return {"run_id": run_id, "status": status, "result": doc["result"]}
    except (ValueError, KeyError, TypeError):
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role=EXTENDED_REVIEW_ROLE) from None


def planned_workflow_result(*, reason=None, terminal=False):
    from auditmanager.analysis.public import extended_workflow_procedures
    procedures = extended_workflow_procedures()
    if reason:
        for procedure in procedures:
            procedure.update(status="skipped" if terminal else "queued", reason=reason)
    return {"format":"extended-review-v2","workflow_version":"extended-review-v2","preliminary":True,
        "observations":[],"sources":[],"warnings":[],"procedures":procedures,"ocr_status":"not_performed",
        "reason":reason,"coverage":{"blocks_total":0,"blocks_selected":0,"blocks_processed":0,
            "blocks_remaining":0,"skipped":[]}}


def _run_workflow_v2(session, *, run, authority, jobs, journal, binding, outputs, store, meter,
        publish, progress, checkpoint, observations_document, snapshot_id, profile_sha256, bind_native=None):
    from auditmanager.analysis.public import (read_artifact, prepare_native_page_sources,
        build_comprehensive_request, deterministic_extended_merge,
        build_norm_review_request, parse_norm_review)
    state = planned_workflow_result()
    current = None
    def save(status):
        public = {k:v for k,v in state.items() if k not in {"text_items","context_sections"}}
        public["sources"] = [{k:v for k,v in s.items() if k != "context"} for s in state["sources"]]
        progress(status, public)
    def phase(identity, status, reason=None):
        nonlocal current
        current = identity
        procedure = next(p for p in state["procedures"] if p["id"] == identity)
        procedure.update(status=status)
        if reason: procedure["reason"] = reason
        save("running")
    def call(request, identity):
        response, _ = _call(session,run_id=run.run_id,authority=authority,jobs=jobs,journal=journal,
            binding=binding,request=request,phase="v2:"+identity,source_sha256=state["source_sha256"],
            meter=meter,store=store,publish=publish,checkpoint=checkpoint)
        if response.truncated: raise _refuse("extended_response_truncated")
        return response
    save("running")
    try:
        version = DocumentRepository().get_version(session,run.version_uid)
        section = version.classification.section_code if version.classification else "unknown"
        state["section"] = section
        checkpoint("extended_v2_inputs")
        data = {}
        for role in ("prepared.text_layer","context.document_graph","geometry.portal_blocks","geometry.page_crops","prepared.recognised_text"):
            ref = outputs.refs.get(role)
            if ref is not None:
                data[role], _ = read_artifact(store,parse_blob_id(ref.blob_id),expected_role=role)
        if "prepared.text_layer" not in data or "context.document_graph" not in data:
            raise _refuse("extended_prepared_inputs_unavailable")
        native = None
        portal = data.get("geometry.portal_blocks")
        manifest = data.get("geometry.page_crops")
        text_only_portal = False
        if portal is not None and manifest is not None:
            # Validate the saved portal cohort before considering native rendering.
            # Native pages supplement genuine TEXT-only input; they never conceal an
            # IMAGE refusal or a known page/region geometry mismatch.
            plan_extended_inputs(version_uid=run.version_uid,section=section,portal=portal,manifest=manifest,
                text_layer=data["prepared.text_layer"],graph=data["context.document_graph"],
                observations=None,plan_version="extended-review-v2")
            text_only_portal = (not manifest.get("crops") and bool(portal.get("blocks"))
                and all(block.get("block_type") == "text" and block.get("geometry") == "ok"
                    for block in portal["blocks"])
                and all(page.get("geometry") == "ok" for page in portal.get("pages", [])))
        if portal is None or text_only_portal:
            source = outputs.refs.get("source.document")
            if source is None: raise _refuse("extended_native_source_unavailable")
            native = prepare_native_page_sources(version_uid=run.version_uid,source_ref=source,
                blob_store=store,max_pages=16,checkpoint=checkpoint)
            if text_only_portal:
                native["warnings"].append("portal_text_only_native_page_visuals")
            if bind_native is not None: bind_native(native["artifacts"])
        planned = plan_extended_inputs(version_uid=run.version_uid,section=section,
            portal=data.get("geometry.portal_blocks",{}),manifest=data.get("geometry.page_crops",{}),
            text_layer=data["prepared.text_layer"],graph=data["context.document_graph"],
            observations=observations_document,recognised=data.get("prepared.recognised_text"),
            native_sources=native,plan_version="extended-review-v2")
        procedures = state["procedures"]
        state.update(planned,workflow_version="extended-review-v2",procedures=procedures,
            ocr_status="not_performed",model_id=binding.config.model_id,provider_mode=binding.adapter.provider_mode.value)
        state["source_sha256"] = extended_digest({"source":state["source_sha256"],"workflow_version":"extended-review-v2",
            "profile_sha256":profile_sha256,"norms_snapshot_id":snapshot_id,"run_input_digest":getattr(run,"frozen_input_digest",None)})
        pages = data["prepared.text_layer"].get("pages",[])
        by_page = {p["page_number"]:str(p.get("text","")) for p in pages}
        # Native visual crops use the same genuine page context as portal crops.
        for source in state["sources"]:
            if source.get("source_type") == "native_page":
                source["context"] = [{"page_number":n,"text":by_page[n][:6000],"recognised_context":"",
                    "context_truncated":len(by_page[n])>6000} for n in (source["page_number"]-1,source["page_number"],source["page_number"]+1) if n in by_page]
        images = [s for s in state["sources"] if s["kind"] == "image"]
        block_items = []
        if images:
            phase("block_analysis","running")
            for start in range(0,len(images),8):
                batch=images[start:start+8];crops=[]
                for source in batch:
                    raw=store.read(parse_blob_id(source["blob_id"]),verify=True)
                    if len(raw)!=source["size_bytes"] or hashlib.sha256(raw).hexdigest()!=source["crop_sha256"]:
                        raise _refuse("extended_crop_digest_invalid")
                    crops.append(CropImage(source["source_id"],raw))
                payload,cut=extended_block_payload(section=section,batch=batch,sections=state["context_sections"],coverage=state["coverage"])
                if cut: state["warnings"].append("page_context_truncated")
                request=attach_images(build_extended_request(model_id=binding.config.model_id,run_id=run.run_id,
                    phase="blocks",section=section,payload=payload),crops)
                response=call(request,"blocks:"+str(start//8))
                block_items.extend(parse_extended_reply(response.output_text,allowed_sources={s["source_id"] for s in batch}))
                state["coverage"]["blocks_processed"]+=len(batch)
                state["coverage"]["blocks_remaining"]=state["coverage"]["blocks_total"]-state["coverage"]["blocks_processed"]
                state["observations"]=finalize_extended_items([*state["text_items"],*block_items],state["sources"])
                save("running")
            phase("block_analysis","partial" if state["coverage"]["blocks_remaining"] else "completed")
        else:
            phase("block_analysis","unavailable","no_image_blocks_available")
        # Every page context has a real page/version source anchor, independent of text findings.
        contexts=[]
        for page in pages[:16]:
            number=page["page_number"];value=str(page.get("text",""))
            source_id="native_text_"+extended_digest({"version_uid":run.version_uid,"page":number,"text":value})[:24]
            state["sources"].append({"source_id":source_id,"kind":"text","source_type":"native_text",
                "page_number":number,"version_uid":run.version_uid,"quote":value[:2000],"text_sha256":hashlib.sha256(value.encode()).hexdigest()})
            contexts.append({"source_id":source_id,"page_number":number,"text":value})
        phase("comprehensive_analysis","running")
        request=build_comprehensive_request(model_id=binding.config.model_id,run_id=run.run_id,section=section,
            payload={"native_context":contexts,"visual_observations":block_items,"text_observations":state["text_items"],
                "sources":[{k:v for k,v in s.items() if k!="context"} for s in state["sources"]],
                "source_sha256":state["source_sha256"],"coverage":state["coverage"]})
        context_cut = json.loads(request.body["messages"][0]["content"])["context_coverage"]["truncated"]
        if context_cut: state["warnings"].append("page_context_truncated")
        comprehensive=parse_extended_reply(call(request,"comprehensive").output_text,
            allowed_sources={s["source_id"] for s in state["sources"]})
        phase("comprehensive_analysis","partial" if len(pages)>16 or context_cut else "completed")
        phase("finding_merge","running")
        items=deterministic_extended_merge([*state["text_items"],*block_items,*comprehensive])
        state["observations"]=finalize_extended_items(items,state["sources"])
        phase("finding_merge","completed")
        phase("norm_verification","running")
        window=state["observations"][:40]
        for item in state["observations"][40:]:
            item.update(norm_status="unavailable",norm_reason="outside_norm_review_window")
        state["warnings"].extend(_norms(session,window,snapshot_id))
        registry={}
        for item in window:
            item["norm_candidates"]=[registry.setdefault(c["paragraph_id"],c) for c in item.get("norm_candidates",[])]
        bounded=[];remaining_chars=16_000
        for item in window:
            size=len(item["title"])+len(item["description"])+sum(len(c["quote"]) for c in item.get("norm_candidates",[]))
            if size>remaining_chars:
                item.update(norm_status="unavailable",norm_reason="outside_norm_review_window")
                continue
            bounded.append(item);remaining_chars-=size
        window=bounded
        registry={c["paragraph_id"]:c for item in window for c in item.get("norm_candidates",[])}
        if not registry:
            reason="corpus_unavailable" if snapshot_id is None else "candidate_context_unavailable"
            phase("norm_verification","unavailable",reason)
        else:
            indexed={"xni_"+extended_digest({"ordinal":i,"item":item})[:24]:item for i,item in enumerate(window)}
            request=build_norm_review_request(model_id=binding.config.model_id,run_id=run.run_id,section=section,
                payload={"observations":[{"title":item["title"],"description":item["description"],
                    "source_ids":item["source_ids"],"input_id":key,
                    "norm_candidate_ids":[c["paragraph_id"] for c in item.get("norm_candidates",[])]} for key,item in indexed.items()],
                    "norm_context":list(registry.values()),"source_sha256":state["source_sha256"]})
            reviewed=parse_norm_review(call(request,"norm_verification").output_text,observations=indexed,
                allowed_sources={s["source_id"] for s in state["sources"]})
            # Parser requires exactly one assessment per original input; only annotations transfer.
            for reviewed_item in reviewed:
                target=indexed[reviewed_item["input_ids"][0]]
                target["norm_assessment"]=reviewed_item["norm_assessment"]
            phase("norm_verification","partial" if len(window)<len(state["observations"]) or any(not item.get("norm_candidates") for item in window) else "completed")
        degraded=any(p["status"] in {"failed","partial","unavailable","skipped"} for p in state["procedures"])
        save("partial" if degraded else "completed")
        return state
    except (DomainError,ValueError,TypeError,KeyError) as error:
        reason=error.detail_fields.get("reason") if isinstance(error,DomainError) else "extended_reply_or_source_invalid"
        reason=str(reason or "extended_workflow_failed")
        for procedure in state["procedures"]:
            if procedure["status"]=="running": procedure.update(status="failed",reason=reason)
            elif procedure["status"]=="queued": procedure.update(status="skipped",reason="dependency_failed")
        state["warnings"].append(reason)
        save("failed")
        return state
