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
          meter, store, publish, checkpoint, global_unknown_fence=False):
    checkpoint("extended_before_call")
    key = extended_digest({"format": FORMAT, "source": source_sha256, "phase": phase,
        "request": request.request_sha256, "model": request.model_id,
        "connection": None if binding.call is None else binding.call.connection_revision_id})
    saved = extended_unit(session, run_id=run_id, unit_key=key, source_sha256=source_sha256, phase=phase)
    session.commit()  # no read/authority lock survives external Blob I/O
    if saved is not None:
        return _saved_response(store, saved, request, binding), True
    if global_unknown_fence:
        from auditmanager.jobs.public import has_ambiguous_provider_effect
        if has_ambiguous_provider_effect(session,run_id=run_id):
            session.commit()
            raise _refuse("extended_provider_outcome_unknown")
        session.commit()
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
    if global_unknown_fence:
        bind_current=getattr(journal,"bind_current_call",None)
        if callable(bind_current):bind_current(call_id)
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
                        policy=None, bind_native=None, resume_state=None, visual_only=False) -> dict:
    """Dispatch the immutable accepted v1/v2 plan or the fresh windowed v3 workflow."""
    if isinstance(policy, dict) and policy.get("plan_version") == "extended-review-v3":
        return _run_workflow_v3(session,run=run,authority=authority,jobs=jobs,journal=journal,binding=binding,
            outputs=outputs,store=store,meter=meter,publish=publish,progress=progress,checkpoint=checkpoint,
            observations_document=observations_document,snapshot_id=snapshot_id,profile_sha256=profile_sha256,
            bind_native=bind_native,policy=policy,resume_state=resume_state,visual_only=visual_only)
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
            if isinstance(policy,dict) and policy.get("plan_version") in {"extended-review-v2","extended-review-v3"}:
                terminal = run.state in {"published","partial","failed","cancelled"}
                reason = "workflow_not_executed" if terminal else None
                if terminal and any(row.stage_id != "text_analysis" and row.status in {"failed","partial"} for row in rows):
                    reason = "source_preparation_failed"
                return {"run_id":run_id,"status":"unavailable" if terminal else "not_started",
                    "result":planned_workflow_result(reason=reason,terminal=terminal,policy=policy)}
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


def planned_workflow_result(*, reason=None, terminal=False, policy=None):
    from auditmanager.analysis.public import extended_workflow_procedures
    v3=isinstance(policy,dict) and policy.get("plan_version")=="extended-review-v3"
    if v3:
        from auditmanager.analysis.public import extended_workflow_procedures_v3
        procedures=extended_workflow_procedures_v3()
    else:
        procedures = extended_workflow_procedures()
    if reason:
        for procedure in procedures:
            procedure.update(status="skipped" if terminal else "queued", reason=reason)
    version="extended-review-v3" if v3 else "extended-review-v2"
    return {"format":version,"workflow_version":version,"preliminary":True,
        **({"windows":[],"window_progress":{"completed":0,"total":policy["max_windows"],"current":None,"window_size":16},
            "rules_sha256":policy["rules_sha256"],"section":policy.get("section_code"),"primary_text_status":"pending"} if v3 else {}),
        "observations":[],"sources":[],"warnings":[],"procedures":procedures,"ocr_status":"not_performed",
        "reason":reason,"coverage":{"blocks_total":0,"blocks_selected":0,"blocks_processed":0,
            "blocks_remaining":0,"skipped":[]}}


def _run_workflow_v2(session, *, run, authority, jobs, journal, binding, outputs, store, meter,
        publish, progress, checkpoint, observations_document, snapshot_id, profile_sha256, bind_native=None,
        window_context=None):
    from auditmanager.analysis.public import (read_artifact, prepare_native_page_sources,
        build_comprehensive_request, deterministic_extended_merge,
        build_norm_review_request, parse_norm_review)
    v3=window_context is not None
    state = planned_workflow_result(policy=None if not v3 else window_context["policy"])
    if v3:
        state["window_id"]=window_context["window_id"]
        state["primary_text_status"]=window_context.get("primary_text_status","pending")
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
            binding=binding,request=request,phase=("v3:"+window_context["window_id"]+":" if v3 else "v2:")+identity,
            source_sha256=state["source_sha256"],meter=meter,store=store,publish=publish,checkpoint=checkpoint,
            global_unknown_fence=v3)
        if response.truncated: raise _refuse("extended_response_truncated")
        return response
    save("running")
    try:
        if v3:
            section=window_context["policy"]["section_code"]
        else:
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
            saved_visual=window_context.get("saved_visual") if v3 else None
            if v3 and window_context["offset"] >= window_context["policy"]["max_blocks"]:
                native={"sources":[],"artifacts":(),"warnings":[],
                    "coverage":{"blocks_total":window_context["page_count"],"skipped":[]},
                    "source_sha256":extended_digest({"source_sha256":source.sha256,"text_only_window":window_context["offset"]}),
                    "source_window":{"slots":0}}
            elif saved_visual is not None:
                saved_sources=[item for item in saved_visual.get("sources",[]) if item.get("kind")=="image"]
                if any(item.get("source_type")!="native_page" or item.get("version_uid")!=run.version_uid
                        or item.get("source_sha256")!=source.sha256 for item in saved_sources):
                    raise _refuse("extended_saved_native_source_changed")
                native={"sources":saved_sources,"artifacts":(),"warnings":["native_pdf_page_render_no_ocr"],
                    "coverage":{"blocks_total":saved_visual["source_window_total"],
                        "skipped":saved_visual["coverage"].get("skipped",[])},
                    "source_sha256":extended_digest({"sources":saved_sources,"source_sha256":source.sha256}),
                    "source_window":{"slots":saved_visual["coverage"]["blocks_total"]}}
            else:
                native = prepare_native_page_sources(version_uid=run.version_uid,source_ref=source,
                    blob_store=store,max_pages=16,checkpoint=checkpoint,
                    **({"window_offset":window_context["offset"],"max_sources":window_context["policy"]["max_blocks"]} if v3 else {}))
            if text_only_portal:
                native["warnings"].append("portal_text_only_native_page_visuals")
            if bind_native is not None: bind_native(native["artifacts"])
        planned = plan_extended_inputs(version_uid=run.version_uid,section=section,
            portal=data.get("geometry.portal_blocks",{}),manifest=data.get("geometry.page_crops",{}),
            text_layer=data["prepared.text_layer"],graph=data["context.document_graph"],
            observations=observations_document,recognised=data.get("prepared.recognised_text"),
            native_sources=native,plan_version="extended-review-v3" if v3 else "extended-review-v2",
            **({"source_offset":window_context["offset"],"max_sources":window_context["policy"]["max_blocks"]} if v3 else {}))
        if v3:
            window_total=(native["source_window"]["slots"] if native is not None else len([s for s in planned["sources"] if s["kind"]=="image"]))
            planned["source_window_total"]=planned["coverage"]["blocks_total"]
            planned["coverage"]={**planned["coverage"],"blocks_total":window_total,"blocks_remaining":window_total,
                "skipped":native["coverage"]["skipped"] if native is not None else []}
        procedures = state["procedures"]
        state.update(planned,workflow_version="extended-review-v3" if v3 else "extended-review-v2",procedures=procedures,
            ocr_status="not_performed",model_id=binding.config.model_id,provider_mode=binding.adapter.provider_mode.value)
        state["source_sha256"] = extended_digest({"source":state["source_sha256"],"workflow_version":"extended-review-v2",
            "profile_sha256":profile_sha256,"norms_snapshot_id":snapshot_id,"run_input_digest":getattr(run,"frozen_input_digest",None)})
        if v3: state["source_sha256"]=window_context["global_sha256"]
        pages = data["prepared.text_layer"].get("pages",[])
        by_page = {p["page_number"]:str(p.get("text","")) for p in pages}
        recognised_by_page={}
        recognised_artifact_sha=None
        if v3 and data.get("prepared.recognised_text") is not None:
            recognised_artifact_sha=outputs.refs["prepared.recognised_text"].sha256
            for entry in data["prepared.recognised_text"].get("entries",[]):
                if entry.get("kind")=="recognised_text" and isinstance(entry.get("text"),str):
                    recognised_by_page.setdefault(entry["page_number"],[]).append(entry["text"])
        # Native visual crops use the same genuine page context as portal crops.
        for source in state["sources"]:
            if source.get("source_type") == "native_page":
                source["context"] = [{"page_number":n,"text":by_page[n][:6000],
                    "recognised_context":"\n".join(recognised_by_page.get(n,[]))[:4000],
                    "context_truncated":len(by_page[n])>6000 or len("\n".join(recognised_by_page.get(n,[])))>4000} for n in (source["page_number"]-1,source["page_number"],source["page_number"]+1) if n in by_page]
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
                builder=build_extended_request
                extra={}
                if v3:
                    from auditmanager.analysis.public import build_extended_request_v3
                    builder=build_extended_request_v3;extra={"window_id":window_context["window_id"]}
                request=attach_images(builder(model_id=binding.config.model_id,run_id=run.run_id,
                    phase="blocks",section=section,payload=payload,**extra),crops)
                response=call(request,"blocks:"+str(start//8))
                block_items.extend(parse_extended_reply(response.output_text,allowed_sources={s["source_id"] for s in batch}))
                state["coverage"]["blocks_processed"]+=len(batch)
                state["coverage"]["blocks_remaining"]=state["coverage"]["blocks_total"]-state["coverage"]["blocks_processed"]
                state["observations"]=finalize_extended_items([*state["text_items"],*block_items],state["sources"])
                save("running")
            phase("block_analysis","partial" if state["coverage"]["blocks_remaining"] else "completed")
        else:
            legitimate_text_window=(v3 and not window_context.get("known_visual_refusals")
                and not (native or {}).get("coverage",{}).get("skipped"))
            phase("block_analysis","completed" if legitimate_text_window else "unavailable",
                "no_visual_sources_in_window" if legitimate_text_window else "no_image_blocks_available")
        if v3:
            state["visual_phase_complete"]=True
        if v3 and window_context.get("visual_only"):
            state["primary_text_status"]="pending"
            save("running")
            return state
        # Every page context has a real page/version source anchor, independent of text findings.
        contexts=[]
        context_pages=pages[:16]
        if v3:
            numbers={source["page_number"]+delta for source in images for delta in (-1,0,1)}
            numbers.update(range(window_context["offset"]+1,min(window_context["offset"]+16,
                window_context["policy"]["text_page_limit"])+1))
            context_pages=[page for page in pages if page["page_number"] in numbers]
            if not context_pages:
                context_pages=pages[window_context["offset"]:window_context["offset"]+16]
        for page in context_pages:
            number=page["page_number"];value=str(page.get("text",""))
            source_id="native_text_"+extended_digest({"version_uid":run.version_uid,"page":number,"text":value})[:24]
            state["sources"].append({"source_id":source_id,"kind":"text","source_type":"native_text",
                "page_number":number,"version_uid":run.version_uid,"quote":value[:2000],"text_sha256":hashlib.sha256(value.encode()).hexdigest()})
            contexts.append({"source_id":source_id,"page_number":number,"text":value})
            if v3 and recognised_by_page.get(number):
                recognised="\n".join(recognised_by_page[number])
                recognised_id="recognised_"+extended_digest({"version_uid":run.version_uid,"page":number,
                    "artifact_sha256":recognised_artifact_sha,"text":recognised})[:24]
                state["sources"].append({"source_id":recognised_id,"kind":"text","source_type":"recognised_text",
                    "quote_source":"recognised","page_number":number,"version_uid":run.version_uid,
                    "quote":recognised[:2000],"artifact_sha256":recognised_artifact_sha,
                    "text_sha256":hashlib.sha256(recognised.encode()).hexdigest()})
                contexts.append({"source_id":recognised_id,"page_number":number,"text":"",
                    "recognised_context":recognised,"source_type":"recognised_text","quote_source":"recognised"})
        phase("comprehensive_analysis","running")
        builder=build_comprehensive_request
        extra={}
        if v3:
            from auditmanager.analysis.public import build_comprehensive_request_v3
            builder=build_comprehensive_request_v3;extra={"window_id":window_context["window_id"]}
        request=builder(model_id=binding.config.model_id,run_id=run.run_id,section=section,
            **extra,payload={"native_context":contexts,"visual_observations":block_items,
                "text_observations":([{k:item[k] for k in ("title","description","source_ids","norm_queries")}
                    for item in state["text_items"]] if v3 else state["text_items"]),
                "sources":[{k:v for k,v in s.items() if k!="context"} for s in state["sources"]],
                "source_sha256":state["source_sha256"],"coverage":state["coverage"]})
        context_payload=json.loads(request.body["messages"][0]["content"])
        context_cut = context_payload["context_coverage"]["truncated"]
        if v3:
            state["context_page_numbers"]=[page["page_number"] for page in context_pages]
            state["comprehensive_context_coverage"]=context_payload["context_coverage"]
        if context_cut: state["warnings"].append("page_context_truncated")
        if v3 and not images and not any(row.get("text","").strip() or row.get("recognised_context","").strip() for row in contexts):
            comprehensive=[]
            phase("comprehensive_analysis","unavailable","no_reliable_window_sources")
        else:
            comprehensive=parse_extended_reply(call(request,"comprehensive").output_text,
                allowed_sources={s["source_id"] for s in state["sources"]})
            phase("comprehensive_analysis","partial" if (not v3 and len(pages)>16) or context_cut else "completed")
        phase("finding_merge","running")
        items=deterministic_extended_merge([*state["text_items"],*block_items,*comprehensive])
        state["observations"]=finalize_extended_items(items,state["sources"])
        phase("finding_merge","completed")
        phase("norm_verification","running")
        window=state["observations"][:40]
        if v3:
            for item in window:
                if len(item["source_ids"])>16:
                    item.update(norm_status="unavailable",norm_reason="norm_source_reference_window_exceeded")
            window=[item for item in window if len(item["source_ids"])<=16]
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
            builder=build_norm_review_request
            extra={}
            if v3:
                from auditmanager.analysis.public import build_norm_review_request_v3
                builder=build_norm_review_request_v3;extra={"window_id":window_context["window_id"]}
            request=builder(model_id=binding.config.model_id,run_id=run.run_id,section=section,
                **extra,payload={"observations":[{"title":item["title"],"description":item["description"],
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
        if v3:
            _review_window_v3(session=session,run=run,binding=binding,state=state,phase=phase,call=call,
                window_id=window_context["window_id"],section=section,contexts=contexts)
        degraded=any(p["status"] in {"failed","partial","unavailable","skipped"}
            and p.get("reason") not in {"no_corrections_requested","no_observations"} for p in state["procedures"])
        save("partial" if degraded else "completed")
        return state
    except (DomainError,ValueError,TypeError,KeyError) as error:
        reason=(error.detail_fields.get("reason") or (error.code.value if v3 else None)) if isinstance(error,DomainError) else "extended_reply_or_source_invalid"
        reason=str(reason or "extended_workflow_failed")
        for procedure in state["procedures"]:
            if procedure["status"]=="running": procedure.update(status="failed",reason=reason)
            elif procedure["status"]=="queued": procedure.update(status="skipped",reason="dependency_failed")
        state["warnings"].append(reason)
        save("failed")
        return state


def _review_window_v3(*, session, run, binding, state, phase, call, window_id, section, contexts):
    """Real critic/corrector calls annotate immutable candidates; neither decides for the expert."""
    from auditmanager.analysis.public import (build_critic_request,parse_critic_reply,
        build_corrector_request,parse_corrector_reply)
    selected=[];remaining=16_000
    for item in state["observations"]:
        size=len(item["title"])+len(item["description"])+len(json.dumps(item.get("norm_assessment"),ensure_ascii=False))
        if len(selected)>=40 or size>remaining:
            item.update(review_status="not_reviewed",review_reason="outside_critic_window")
            continue
        selected.append(item);remaining-=size
    if not selected:
        if state["observations"]:
            phase("finding_review","partial","outside_critic_window")
            phase("finding_correction","unavailable","critic_inputs_unavailable")
        else:
            phase("finding_review","completed","no_observations")
            phase("finding_correction","completed","no_observations")
    else:
        indexed={"xri_"+extended_digest({"window_id":window_id,"ordinal":i,"observation":item})[:24]:item
            for i,item in enumerate(selected)}
        references={source for item in selected for source in item["source_ids"]}
        sources=[source for source in state["sources"] if source["source_id"] in references]
        context={"coverage":state["coverage"],"window_id":window_id,
            "source_sha256":state["source_sha256"],"ocr_status":"not_performed",
            "native_context":[row for row in contexts if row["source_id"] in references]}
        phase("finding_review","running")
        request=build_critic_request(model_id=binding.config.model_id,run_id=run.run_id,section=section,
            observations=indexed,sources=sources,window_id=window_id,context=context)
        critic_payload=json.loads(request.body["messages"][0]["content"])
        critic_cut=any(critic_payload.get(key,{}).get("truncated",False)
            for key in ("context_coverage","norm_context_coverage"))
        reviews=parse_critic_reply(call(request,"critic").output_text,observations=indexed,sources=sources,
            allowed_sources=references,context=context)
        state["reviews"]=reviews
        state["critiques"]=reviews
        for review in reviews:
            indexed[review["input_id"]].update(critic=review,review_status="reviewed")
        phase("finding_review","partial" if len(selected)<len(state["observations"]) or critic_cut else "completed",
            "context_window_truncated" if critic_cut else None)
        request=build_corrector_request(model_id=binding.config.model_id,run_id=run.run_id,section=section,
            observations=indexed,critiques=reviews,sources=sources,window_id=window_id,context=context)
        if request is None:
            phase("finding_correction","completed","no_corrections_requested")
            state["corrections"]=[]
        else:
            phase("finding_correction","running")
            correction_payload=json.loads(request.body["messages"][0]["content"])
            correction_cut=any(correction_payload.get(key,{}).get("truncated",False)
                for key in ("context_coverage","norm_context_coverage"))
            corrections=parse_corrector_reply(call(request,"corrector").output_text,observations=indexed,
                critiques=reviews,sources=sources,allowed_sources=references,context=context)
            state["corrections"]=corrections
            for correction in corrections:
                indexed[correction["input_id"]]["correction"]=correction
            phase("finding_correction","partial" if correction_cut or any(c["action"]=="needs_context" for c in corrections) else "completed",
                "context_window_truncated" if correction_cut else None)
    phase("report_generation","running")
    state["report"]=_section_report_v3(state,window_id=window_id)
    phase("report_generation","completed")


def _section_report_v3(state, *, window_id=None):
    """Deterministic report over saved observations and actual coverage, without another call."""
    coverage=state.get("coverage",{})
    lines=[f"# Анализ раздела {state.get('section','unknown')}",
        "Предварительные наблюдения. Решение по каждому принимает эксперт.",
        f"Охват: обработано {coverage.get('blocks_processed',0)} из {coverage.get('blocks_total',0)}; "
        f"не исследовано {coverage.get('blocks_remaining',0)}.",
        "OCR не выполнялся. Отсутствие native текста не считается его распознаванием.",
        "Распознанный текст портала, если предоставлен, помечен отдельно от native цитат."]
    for number,item in enumerate(state.get("observations",[]),start=1):
        lines.extend([f"\n## {number}. {item['title']}",item['description'],
            "Источники: "+", ".join(item["source_ids"]),
            "Нормативная сверка: "+str(item.get("norm_status","unavailable"))])
        if item.get("norm_assessment"):
            lines.append("Модельная сверка по цитате: "+item["norm_assessment"]["explanation"])
        if item.get("critic"):
            lines.append("Критик: "+item["critic"]["explanation"])
        candidate=(item.get("correction") or {}).get("candidate")
        if candidate:
            lines.extend(["Предложенная редакция (оригинал сохранён): "+candidate["title"],candidate["description"]])
    return {"format":"section-review-report-v3","section":state.get("section"),"window_id":window_id,
        "coverage":coverage,"observation_count":len(state.get("observations",[])),
        "expert_review_required":True,"markdown":"\n\n".join(lines)}


def load_saved_workflow(session, *, store, run):
    """Read a custody-bound v3 receipt before the caller replaces its pending stage row."""
    rows=RunRepository().stage_results(session,run.run_id)
    stage=next((row for row in rows if row.stage_id=="text_analysis"),None)
    ref=None if stage is None else next((r for r in stage.artifacts if r.get("role")==EXTENDED_REVIEW_ROLE),None)
    session.commit()
    if ref is None:return None
    raw=store.read(parse_blob_id(ref["blob_id"]),verify=True)
    if len(raw)!=ref["size_bytes"] or hashlib.sha256(raw).hexdigest()!=ref["sha256"]:
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR,role=EXTENDED_REVIEW_ROLE)
    try:
        doc=json.loads(raw)
        if doc.get("run_id")!=run.run_id or doc.get("version_uid")!=run.version_uid or doc.get("artifact_role")!=EXTENDED_REVIEW_ROLE:
            raise ValueError()
        result=doc["result"]
        return result if isinstance(result,dict) and result.get("workflow_version")=="extended-review-v3" else None
    except (ValueError,TypeError,KeyError):
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR,role=EXTENDED_REVIEW_ROLE) from None


def _run_workflow_v3(session, *, run, authority, jobs, journal, binding, outputs, store, meter,
        publish, progress, checkpoint, observations_document, snapshot_id, profile_sha256,
        bind_native, policy, resume_state=None, visual_only=False):
    from auditmanager.analysis.public import (read_artifact,extended_review_enabled,
        extended_review_bundle_digest,extended_workflow_procedures_v3)
    from auditmanager.jobs.public import has_ambiguous_provider_effect
    state=planned_workflow_result(policy=policy)
    state["primary_text_status"]=("pending" if visual_only else "unavailable" if
        isinstance(observations_document,dict) and observations_document.get("input_disposition")=="image_only_no_native_text"
        else "completed" if observations_document is not None else "failed")
    def save(status):
        state["status"]=status
        progress(status,state)
    def aggregate():
        records=state["windows"]
        source_index={}
        observations=[]
        for record in records:
            for source in record.get("sources",[]):source_index[source["source_id"]]=source
            for observation in record.get("observations",[]):
                observations.append({**observation,"window_id":record["window_id"]})
        state["sources"]=list(source_index.values())
        state["observations"]=observations
        processed=sum(record.get("coverage",{}).get("blocks_processed",0) for record in records)
        state["coverage"]["blocks_processed"]=processed
        state["coverage"]["blocks_remaining"]=max(0,state["coverage"]["blocks_total"]-processed)
        complete=sum(record.get("status") not in {"queued","running"} for record in records)
        current=next((record["window_id"] for record in records if record.get("status")=="running"),None)
        state["window_progress"]={"completed":complete,"total":len(records),"current":current,"window_size":16}
        if state.get("text_coverage") is not None:
            covered=set()
            for record in records:
                comp=next((p for p in record.get("procedures",[]) if p["id"]=="comprehensive_analysis"),None)
                if comp and comp["status"]=="completed":
                    covered.update(page for page in record.get("context_page_numbers",[]) if 0<page<=policy["text_page_limit"])
            state["text_coverage"]["pages_processed"]=len(covered)
            state["text_coverage"]["pages_remaining"]=max(0,state["text_coverage"]["pages_total"]-len(covered))
        for procedure in state["procedures"]:
            values=[next((p for p in record.get("procedures",[]) if p["id"]==procedure["id"]),
                {"status":"queued"}) for record in records]
            statuses=[p["status"] for p in values]
            if not values or all(value=="queued" for value in statuses):status="queued"
            elif "running" in statuses or "queued" in statuses:status="running"
            elif all(value=="completed" for value in statuses):status="completed"
            elif all(value=="skipped" for value in statuses):status="skipped"
            elif all(value=="unavailable" for value in statuses):status="unavailable"
            elif all(value=="failed" for value in statuses):status="failed"
            elif all(p["status"]=="completed" or p.get("reason") in {"no_observations","no_corrections_requested"} for p in values):status="completed"
            else:status="partial"
            procedure["status"]=status
            reasons=list(dict.fromkeys(p.get("reason") for p in values if p.get("reason")))
            if reasons:procedure["reason"]=reasons[0]
    save("running")
    try:
        if not extended_review_enabled(policy):raise _refuse("extended_v3_authority_invalid")
        version=DocumentRepository().get_version(session,run.version_uid)
        section=policy["section_code"]
        actual_rules=extended_review_bundle_digest(section)
        if actual_rules!=policy["rules_sha256"]:raise _refuse("extended_rules_changed_requires_consent")
        refs={role:{"blob_id":ref.blob_id,"sha256":ref.sha256,"size_bytes":ref.size_bytes}
            for role,ref in sorted(outputs.refs.items()) if role in {"source.document","prepared.text_layer",
                "geometry.portal_blocks","geometry.page_crops","context.document_graph","prepared.recognised_text"}}
        global_sha=extended_digest({"workflow_version":"extended-review-v3","version_uid":run.version_uid,
            "refs":refs,"policy":policy,"profile_sha256":profile_sha256,"norms_snapshot_id":snapshot_id,
            "run_input_digest":getattr(run,"frozen_input_digest",None)})
        state.update(section=section,rules_sha256=actual_rules,source_sha256=global_sha,
            source_provenance={"workflow":"extended-review-v3","rules_bundle_sha256":actual_rules,
                "source_sha256":global_sha,"original_repository":"SU10KAZ/PDF-proverka",
                "original_commit":"3c99481719218b9cfa7560886529916646c61939"})
        total=version.page_count;selected=0;global_skipped=[];page_to_window={};known_visual_refusals=False
        portal_ref=outputs.refs.get("geometry.portal_blocks")
        if portal_ref is not None:
            portal,_=read_artifact(store,parse_blob_id(portal_ref.blob_id),expected_role="geometry.portal_blocks")
            manifest_ref=outputs.refs.get("geometry.page_crops")
            if manifest_ref is None:raise _refuse("extended_prepared_inputs_unavailable")
            manifest,_=read_artifact(store,parse_blob_id(manifest_ref.blob_id),expected_role="geometry.page_crops")
            known_visual_refusals=(any(page.get("geometry")!="ok" for page in portal.get("pages",[]))
                or any(block.get("geometry")!="ok" for block in portal.get("blocks",[])))
            image_blocks=[block for block in portal.get("blocks",[]) if block.get("block_type")=="image"]
            if image_blocks:
                total=len(image_blocks)
                reliable_ids={crop["portal_block_id"] for crop in manifest.get("crops",[])}
                selected=min(policy["max_blocks"],len(reliable_ids))
                ordered=sorted((block for block in image_blocks if block["portal_block_id"] in reliable_ids),
                    key=lambda block:(block["page_number"],block["portal_block_id"]))[:policy["max_blocks"]]
                for ordinal,block in enumerate(ordered):page_to_window.setdefault(block["page_number"],ordinal//16)
                global_skipped=[{"block_id":block["portal_block_id"],"page_number":block["page_number"],
                    "reason":"portal_image_unavailable"} for block in image_blocks if block["portal_block_id"] not in reliable_ids]
                known_visual_refusals=known_visual_refusals or bool(global_skipped)
            else:selected=min(policy["max_blocks"],total)
        else:selected=min(policy["max_blocks"],total)
        count=policy["max_windows"]
        state["text_coverage"]={"pages_total":version.page_count,"pages_selected":policy["text_page_limit"],
            "pages_processed":0,"pages_remaining":version.page_count,"complete_document_claim":False}
        state["coverage"]={"blocks_total":total,"blocks_selected":selected,"blocks_processed":0,
            "blocks_remaining":total,"skipped":global_skipped}
        if total>policy["max_blocks"]:
            state["warnings"].append("remaining_blocks_not_reviewed")
        saved_windows={};visual_windows={}
        if resume_state is not None:
            if resume_state.get("source_sha256")!=global_sha or resume_state.get("rules_sha256")!=actual_rules:
                raise _refuse("extended_saved_workflow_source_changed")
            saved_windows={record["window_id"]:record for record in resume_state.get("windows",[])
                if record.get("status") in {"completed","partial","failed","unavailable"}
                    and not (record.get("visual_phase_complete") and any(p["status"]=="queued" for p in record.get("procedures",[]))) }
            visual_windows={record["window_id"]:record for record in resume_state.get("windows",[])
                if record.get("visual_phase_complete") and record.get("source_window_total") is not None}
        state["windows"]=[{"window_id":f"w{index:03d}","index":index,"total":count,"status":"queued",
            "procedures":extended_workflow_procedures_v3(),"observations":[],"sources":[]}
            for index in range(count)]
        aggregate();save("running")
        for index,record in enumerate(state["windows"]):
            checkpoint("extended_v3_window")
            window_id=record["window_id"]
            if window_id in saved_windows:
                record.update(saved_windows[window_id],index=index,total=count,replayed=True)
                aggregate();save("running")
                continue
            session.commit()
            record["status"]="running";aggregate();save("running")
            window_observations=observations_document
            if observations_document is not None:
                selected_primary=[]
                for primary_index,observation in enumerate(observations_document.get("observations",[])):
                    evidence=observation.get("evidence",[])
                    page=evidence[0].get("page_number") if evidence else None
                    assigned=((page-1)//16 if type(page) is int and 0<page<=policy["text_page_limit"]
                        else page_to_window.get(page,-1))
                    if assigned==index:selected_primary.append({**observation,"_extended_primary_index":primary_index})
                window_observations={**observations_document,"observations":selected_primary}
            def window_progress(status,result):
                record.update(result,status=status,window_id=window_id,index=index,total=count)
                aggregate();save("running")
            _run_workflow_v2(session,run=run,authority=authority,jobs=jobs,journal=journal,binding=binding,
                outputs=outputs,store=store,meter=meter,publish=publish,progress=window_progress,
                checkpoint=checkpoint,observations_document=window_observations,snapshot_id=snapshot_id,
                profile_sha256=profile_sha256,bind_native=bind_native,window_context={"window_id":window_id,
                    "offset":index*16,"policy":policy,"global_sha256":global_sha,"visual_only":visual_only,
                    "primary_text_status":state["primary_text_status"],"saved_visual":visual_windows.get(window_id),
                    "page_count":version.page_count,"known_visual_refusals":known_visual_refusals})
            budget_exhausted=any("cost_budget_exceeded" in str(warning) for warning in record.get("warnings",[]))
            if budget_exhausted:
                for pending in state["windows"][index+1:]:
                    pending.update(status="skipped",reason="cost_budget_exceeded")
                    for procedure in pending["procedures"]:procedure.update(status="skipped",reason="cost_budget_exceeded")
                state["warnings"].append("cost_budget_exceeded")
                break
            if has_ambiguous_provider_effect(session,run_id=run.run_id):
                session.commit()
                for pending in state["windows"][index+1:]:
                    pending.update(status="skipped",reason="provider_outcome_unknown")
                    for procedure in pending["procedures"]:procedure.update(status="skipped",reason="provider_outcome_unknown")
                state["warnings"].append("extended_provider_outcome_unknown")
                break
            session.commit()
        aggregate()
        state["window_progress"]["current"]=None
        if visual_only:
            state["visual_phase_complete"]=all(record.get("visual_phase_complete") for record in state["windows"])
            state["window_progress"]["visual_completed"]=sum(record.get("visual_phase_complete",False) for record in state["windows"])
            save("failed" if "extended_provider_outcome_unknown" in state["warnings"] else "running")
            return state
        _retain_primary_observations_v3(state,observations_document=observations_document)
        for procedure in state["procedures"]:
            if procedure["status"] in {"queued","running"}:
                procedure.update(status="partial",reason="incomplete_window_procedures")
        state["report"]=_section_report_v3(state)
        state["report"]["windows"]=len(state["windows"])
        next(p for p in state["procedures"] if p["id"]=="report_generation").update(status="completed")
        degraded=(state["coverage"]["blocks_remaining"]>0 or state["text_coverage"]["pages_remaining"]>0
            or any(record["status"]!="completed" for record in state["windows"])
            or bool(state.get("unreviewed_primary_observations")))
        state["report"]["status"]="partial" if degraded else "completed"
        save("partial" if degraded else "completed")
        return state
    except (DomainError,ValueError,TypeError,KeyError) as error:
        reason=error.detail_fields.get("reason") if isinstance(error,DomainError) else "extended_v3_input_or_reply_invalid"
        reason=str(reason or "extended_v3_failed")
        state["warnings"].append(reason)
        for procedure in state["procedures"]:
            if procedure["status"] in {"queued","running"}:procedure.update(status="failed",reason=reason)
        state["report"]=_section_report_v3(state)
        save("failed")
        return state


def _retain_primary_observations_v3(state, *, observations_document):
    """Retain every late primary-text proposal, including ones outside paid review windows."""
    if not isinstance(observations_document,dict):return
    seen={item.get("primary_observation_key") for item in state["observations"] if item.get("primary_observation_key")}
    retained=[]
    for index,original in enumerate(observations_document.get("observations",[])):
        key=extended_digest({"index":index,"observation":original})[:24]
        if key in seen:continue
        evidence=original.get("evidence",[])
        page=evidence[0].get("page_number") if evidence else None
        source_id="primary_text_"+key
        source={"source_id":source_id,"kind":"text","source_type":"primary_text_proposal",
            "page_number":page,"quote_source":"unverified_proposal","primary_observation_key":key}
        if not any(s["source_id"]==source_id for s in state["sources"]):state["sources"].append(source)
        item={"observation_id":"xobs_"+key,"primary_observation_key":key,
            "title":str(original.get("category","Текстовое наблюдение"))[:200],
            "description":str(original.get("finding_text",""))[:3000],"source_ids":[source_id],
            "source_kind":"text","status":"requires_expert_review","original_primary_observation":original,
            "review_status":"not_reviewed","review_reason":"outside_processed_review_window",
            "norm_status":"unavailable","norm_reason":"outside_processed_review_window","norm_candidates":[],
            "window_id":None}
        state["observations"].append(item);retained.append(item)
    state["unreviewed_primary_observations"]=retained
    if retained:
        state["warnings"].append("primary_text_observations_outside_review_window")
        next(p for p in state["procedures"] if p["id"]=="finding_review").update(
            status="partial",reason="primary_text_observations_outside_review_window")
