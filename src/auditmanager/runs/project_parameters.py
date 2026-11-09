"""Durable ordinary-Run parameter extraction; provider custody is injected by the Run."""
from __future__ import annotations

from copy import deepcopy

from auditmanager.analysis.public import (build_project_parameters_request, build_semantic_repair_request, parse_project_parameters_reply,
    plan_project_parameters, read_artifact, validate_project_parameters_policy)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import parse_blob_id


_GROUNDING_REFUSALS = {"project_parameters_value_not_in_quote", "project_parameters_quote_not_in_source"}
_REJECTED_CANDIDATE = "rejected_unsupported_candidate"


def _candidate_rejected(record):
    return (record.get("disposition") == _REJECTED_CANDIDATE
        and record.get("rejected_by_validator") is True)


def _refusal_accounted(record):
    return record.get("resolved_by_repair") is True or _candidate_rejected(record)


def _reject_unsupported(record, *, response_sha256):
    # The parser emits these codes only after the individual closed schema passed.
    # A malformed record/envelope, missing output or transport failure is never a
    # negative validation outcome and cannot take this terminal disposition.
    if record.get("reason") not in _GROUNDING_REFUSALS or not isinstance(record.get("record"), dict):
        return False
    record.update(disposition=_REJECTED_CANDIDATE, rejected_by_validator=True,
        validation_response_sha256=response_sha256, resolved_by_repair=False)
    return True


def planned_parameters(policy, *, reason=None, terminal=False):
    return {"version": policy["version"], "policy": deepcopy(policy),
        "status": "skipped" if terminal else "queued", "reason": reason,
        "source_sha256": None, "manifest_sha256": None, "coverage": {"complete_project_claim": False},
        "facts": [], "rejected_facts": [], "rejected_replies": [], "sources": [], "batches": [], "pieces": [], "pending": [], "omitted": [],
        "expert_decisions_written": False, "normative_verification": "not_performed"}


def run_project_parameters(*, run, model_id, outputs, store, state, accepted, durable_call, checkpoint, aggregate, save, settings=None):
    section = state["section"]
    body = state["project_parameters"]
    source_sha = state["source_sha256"]
    def persist():
        aggregate(); save("running")
    try:
        if not validate_project_parameters_policy(accepted, section=section):
            raise ValueError("project_parameters_policy_required")
        candidate_refusals = accepted.get("candidate_refusals") == "reject-unsupported-v1"
        if body.get("source_sha256") not in {None, source_sha} or body.get("policy") != accepted:
            raise ValueError("project_parameters_saved_inputs_changed")
        if body.get("status") in {"completed", "partial", "unavailable"} and body.get("manifest_sha256"):
            body["reused_saved_result"] = True; persist(); return
        body.update(status="running", source_sha256=source_sha)
        persist(); checkpoint("project_parameters_source_plan")
        text_ref = outputs.refs.get("prepared.text_layer")
        if text_ref is None:
            raise ValueError("project_parameters_text_source_unavailable")
        text_layer, _ = read_artifact(store, parse_blob_id(text_ref.blob_id), expected_role="prepared.text_layer")
        recognised_ref = outputs.refs.get("prepared.recognised_text")
        recognised = None
        if recognised_ref is not None:
            recognised, _ = read_artifact(store, parse_blob_id(recognised_ref.blob_id), expected_role="prepared.recognised_text")
        plan = plan_project_parameters(version_uid=run.version_uid, text_layer=text_layer, recognised=recognised,
            text_layer_sha256=text_ref.sha256, recognised_sha256=None if recognised_ref is None else recognised_ref.sha256,
            source_sha256=source_sha, accepted=accepted, section=section)
        if body.get("manifest_sha256") not in {None, plan["manifest_sha256"]}:
            raise ValueError("project_parameters_saved_manifest_changed")
        body.update({key: deepcopy(value) for key, value in plan.items() if key != "batches"})
        def sources_for(batch):
            return batch["sources"] if "sources" in batch else [batch["source"]]
        body["batches"] = [{"batch_key": batch["batch_key"], "index": batch["index"], "status": "queued",
            **({"rejected_candidate_count": 0} if candidate_refusals else {}),
            **({"source_ids": [row["source_id"] for row in sources_for(batch)],
                "page_numbers": sorted({row["page_number"] for row in sources_for(batch)})} if "sources" in batch else
                {"source_id": batch["source"]["source_id"], "page_number": batch["source"]["page_number"]}),
            "input_characters": sum(len(row["quote"]) for row in sources_for(batch))} for batch in plan["batches"]]
        body["rejected_facts"] = []
        body["rejected_replies"] = []
        body["coverage"].update(calls_completed=0, calls_partial=0, calls_failed=0,
            facts_received=len(body["facts"]), facts_rejected=0, facts_rejections_unresolved=0,
            repair_calls_completed=0)
        if candidate_refusals:
            body["coverage"]["rejected_candidate_count"] = 0
        persist()
        if not plan["batches"]:
            body.update(status="unavailable", reason="no_reliable_text_sources"); persist(); return
        source_sized = accepted.get("source_sized_calls") is True
        if not source_sized and len(plan["batches"]) > accepted["max_calls"]:
            raise ValueError("project_parameters_approved_call_limit")
        def received(response, batch):
            rejected = []
            try:
                if response.truncated:
                    raise ValueError("project_parameters_response_truncated")
                return parse_project_parameters_reply(response.output_text, batch=batch, rejected=rejected), rejected, None
            except ValueError as error:
                reason = str(error)
                if not reason.startswith("project_parameters_") or not reason.isidentifier():
                    reason = "project_parameters_reply_invalid"
                return [], rejected, reason
        for batch in plan["batches"]:
            checkpoint("project_parameters_batch")
            receipt = body["batches"][batch["index"]]
            request = build_project_parameters_request(model_id=model_id, run_id=run.run_id,
                section=section, batch=batch, accepted=accepted, source_sha256=source_sha, settings=settings)
            receipt.update(status="running", request_sha256=request.request_sha256); persist()
            response, replayed = durable_call(request, batch["index"])
            receipt.update(response_received=True, response_sha256=response.response_sha256, replayed=replayed)
            persist()
            parsed, rejected, invalid_reply = received(response, batch)
            for record in rejected:
                record.update(attempt=0, resolved_by_repair=False)
            body["rejected_facts"].extend(rejected)
            reply_receipt = None
            if invalid_reply:
                reply_receipt = {"batch_key": batch["batch_key"], "reason": invalid_reply,
                    "request_sha256": request.request_sha256, "response_sha256": response.response_sha256,
                    "attempt": 0, "resolved_by_repair": False}
                body["rejected_replies"].append(reply_receipt)
            receipt.update(status="failed" if invalid_reply else "partial" if rejected else "completed",
                fact_count=len(parsed), rejected_fact_count=len(rejected))
            if invalid_reply or rejected:
                receipt["reason"] = invalid_reply or "project_parameters_facts_rejected"
            else:
                receipt.pop("reason", None)
            # Save every valid first response before the separately journalled repair.
            # Unknown transport outcomes still leave through the outer custody fence.
            body["facts"] = [fact for fact in body["facts"] if fact["batch_key"] != batch["batch_key"]] + parsed
            persist()
            if (invalid_reply or rejected) and source_sized and accepted.get("semantic_repair_attempts") == 1:
                checkpoint("project_parameters_semantic_repair")
                repair_request = build_semantic_repair_request(request,
                    rejected=rejected or [{"reason": invalid_reply}], reply_sha256=response.response_sha256,
                    procedure="project_parameters", attempt=1)
                repair_index = len(plan["batches"]) + batch["index"]
                repair = {"index": repair_index, "status": "running", "request_sha256": repair_request.request_sha256,
                    **({"rejected_candidate_count": 0} if candidate_refusals else {})}
                receipt["repair"] = repair
                persist()
                repaired, repair_replayed = durable_call(repair_request, repair_index)
                repair.update(response_received=True, response_sha256=repaired.response_sha256,
                    replayed=repair_replayed)
                persist()
                repaired_facts, repair_rejected, repair_invalid = received(repaired, batch)
                for record in repair_rejected:
                    record.update(attempt=1, resolved_by_repair=False)
                body["rejected_facts"].extend(repair_rejected)
                repair.update(status="failed" if repair_invalid else "partial" if repair_rejected else "completed",
                    fact_count=len(repaired_facts), rejected_fact_count=len(repair_rejected))
                if repair_invalid:
                    repair["reason"] = repair_invalid
                    body["rejected_replies"].append({"batch_key": batch["batch_key"], "reason": repair_invalid,
                        "request_sha256": repair_request.request_sha256, "response_sha256": repaired.response_sha256,
                        "attempt": 1, "resolved_by_repair": False})
                elif repair_rejected:
                    repair["reason"] = "project_parameters_facts_rejected"
                if not repair_invalid and (not repair_rejected or candidate_refusals):
                    # A repair may withdraw an unsupported candidate, but cannot erase
                    # a separately accepted fact. Ordinals identify response locations,
                    # not distinct evidence, so deduplicate on the validated content.
                    def content(fact):
                        return {key: value for key, value in fact.items() if key not in {"fact_id", "reply_ordinal"}}
                    known = [content(fact) for fact in parsed]
                    for fact in repaired_facts:
                        identity = content(fact)
                        if identity not in known:
                            parsed.append(fact); known.append(identity)
                    body["facts"] = [fact for fact in body["facts"] if fact["batch_key"] != batch["batch_key"]] + parsed
                    receipt["fact_count"] = len(parsed)
                if not repair_invalid and not repair_rejected:
                    for record in rejected:
                        if not candidate_refusals or not _reject_unsupported(record, response_sha256=response.response_sha256):
                            record.update(resolved_by_repair=True, resolution="replaced_by_validated_full_reply",
                                repair_response_sha256=repaired.response_sha256)
                    if reply_receipt is not None:
                        reply_receipt.update(resolved_by_repair=True,
                            resolution="replaced_by_validated_full_reply", repair_response_sha256=repaired.response_sha256)
                    receipt.update(status="completed", fact_count=len(parsed), rejected_fact_count=0)
                    receipt.pop("reason", None)
                elif candidate_refusals and not repair_invalid:
                    # Fresh v3 consent distinguishes a completed negative check of
                    # an unsupported candidate from an incomplete source procedure.
                    # The original invalid rows remain here; none enter facts.
                    for record in rejected:
                        _reject_unsupported(record, response_sha256=response.response_sha256)
                    for record in repair_rejected:
                        _reject_unsupported(record, response_sha256=repaired.response_sha256)
                    if all(_refusal_accounted(record) for record in repair_rejected):
                        repair.update(status="completed", outcome="validated_with_candidate_rejections")
                        repair.pop("reason", None)
                    if invalid_reply is None and all(_refusal_accounted(record) for record in [*rejected, *repair_rejected]):
                        receipt.update(status="completed", outcome="validated_with_candidate_rejections")
                        receipt.pop("reason", None)
                if candidate_refusals:
                    batch_rejections = [*rejected, *repair_rejected]
                    receipt.update(rejected_candidate_count=sum(_candidate_rejected(record) for record in batch_rejections),
                        rejected_fact_count=sum(not _refusal_accounted(record) for record in batch_rejections))
                    repair["rejected_candidate_count"] = sum(_candidate_rejected(record) for record in repair_rejected)
            body["coverage"].update(calls_completed=sum(row["status"] == "completed" for row in body["batches"]),
                calls_partial=sum(row["status"] == "partial" for row in body["batches"]),
                calls_failed=sum(row["status"] == "failed" for row in body["batches"]),
                facts_received=len(body["facts"]), facts_rejected=len(body["rejected_facts"]),
                facts_rejections_unresolved=sum(not _refusal_accounted(row) for row in body["rejected_facts"]),
                repair_calls_completed=sum(row.get("repair", {}).get("status") == "completed" for row in body["batches"]))
            if candidate_refusals:
                body["coverage"]["rejected_candidate_count"] = sum(_candidate_rejected(row) for row in body["rejected_facts"])
            persist()
        rejected_reply = any(row["status"] in {"partial", "failed"} for row in body["batches"])
        complete = body["coverage"]["selection_complete"] and not rejected_reply
        body.update(status="completed" if complete else "partial",
            reason="project_parameters_reply_partially_rejected" if rejected_reply else
                None if complete else "accepted_input_selection_limit")
        persist()
    except (DomainError, ValueError, TypeError, KeyError) as error:
        if isinstance(error, DomainError) and error.code in {ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID}:
            raise
        reason = (error.detail_fields.get("reason") if isinstance(error, DomainError) else str(error)) or "project_parameters_failed"
        # Only known local refusal codes are exposed; arbitrary external exception text is not persisted here.
        if not reason.startswith("project_parameters_") and reason not in {"extended_provider_outcome_unknown", "cost_budget_exceeded"}:
            reason = "project_parameters_input_or_reply_invalid"
        body.update(status="failed", reason=reason)
        for receipt in body.get("batches", []):
            if receipt["status"] == "running": receipt.update(status="failed", reason=reason)
            elif receipt["status"] == "queued": receipt.update(status="skipped", reason="dependency_failed")
            if receipt.get("repair", {}).get("status") == "running":
                receipt["repair"].update(status="failed", reason=reason)
        state["warnings"].append(reason)
        persist()
