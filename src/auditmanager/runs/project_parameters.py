"""Durable ordinary-Run parameter extraction; provider custody is injected by the Run."""
from __future__ import annotations

from copy import deepcopy

from auditmanager.analysis.public import (build_project_parameters_request, parse_project_parameters_reply,
    plan_project_parameters, read_artifact, validate_project_parameters_policy)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import parse_blob_id


def planned_parameters(policy, *, reason=None, terminal=False):
    return {"version": policy["version"], "policy": deepcopy(policy),
        "status": "skipped" if terminal else "queued", "reason": reason,
        "source_sha256": None, "manifest_sha256": None, "coverage": {"complete_project_claim": False},
        "facts": [], "sources": [], "batches": [], "pieces": [], "pending": [], "omitted": [],
        "expert_decisions_written": False, "normative_verification": "not_performed"}


def run_project_parameters(*, run, model_id, outputs, store, state, accepted, durable_call, checkpoint, aggregate, save):
    section = state["section"]
    body = state["project_parameters"]
    source_sha = state["source_sha256"]
    def persist():
        aggregate(); save("running")
    try:
        if not validate_project_parameters_policy(accepted, section=section):
            raise ValueError("project_parameters_policy_required")
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
        body["batches"] = [{"batch_key": batch["batch_key"], "index": batch["index"], "status": "queued",
            "source_id": batch["source"]["source_id"], "page_number": batch["source"]["page_number"],
            "input_characters": len(batch["source"]["quote"])} for batch in plan["batches"]]
        body["coverage"].update(calls_completed=0, facts_received=len(body["facts"]))
        persist()
        if not plan["batches"]:
            body.update(status="unavailable", reason="no_reliable_text_sources"); persist(); return
        if len(plan["batches"]) > accepted["max_calls"]:
            raise ValueError("project_parameters_approved_call_limit")
        for batch in plan["batches"]:
            checkpoint("project_parameters_batch")
            receipt = body["batches"][batch["index"]]
            request = build_project_parameters_request(model_id=model_id, run_id=run.run_id,
                section=section, batch=batch, accepted=accepted, source_sha256=source_sha)
            receipt.update(status="running", request_sha256=request.request_sha256); persist()
            response, replayed = durable_call(request, batch["index"])
            receipt.update(response_received=True, response_sha256=response.response_sha256, replayed=replayed)
            persist()
            if response.truncated:
                raise ValueError("project_parameters_response_truncated")
            parsed = parse_project_parameters_reply(response.output_text, batch=batch)
            previous = [fact for fact in body["facts"] if fact["batch_key"] == batch["batch_key"]]
            if previous and previous != parsed:
                raise ValueError("project_parameters_saved_facts_changed")
            body["facts"] = [fact for fact in body["facts"] if fact["batch_key"] != batch["batch_key"]] + parsed
            receipt.update(status="completed", fact_count=len(parsed))
            body["coverage"].update(calls_completed=sum(row["status"] == "completed" for row in body["batches"]),
                facts_received=len(body["facts"]))
            persist()
        body.update(status="completed" if body["coverage"]["selection_complete"] else "partial",
            reason=None if body["coverage"]["selection_complete"] else "accepted_input_selection_limit")
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
        state["warnings"].append(reason)
        persist()
