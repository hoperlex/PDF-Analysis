"""Narrow host-operator controls for HOTFIX-RUN-COMPLETE-1106.

This module exposes no HTTP route and never accepts a user credential. Status is
read-only. Re-audit uses the application's normal command and fresh consent, and
refuses every metered route. Console output contains counts and controlled codes,
never document text, model answers, connection settings or exception messages.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import re

from sqlalchemy import text

from auditmanager.analysis.public import parse_extended_reply
from auditmanager.ingest.public import CommandRepository
from auditmanager.shared.db.session import get_session_factory
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import IdempotencyKey, RunId
from auditmanager.storage.public import S3BlobStore, S3StorageSettings, parse_blob_id

from .commands import reaudit_run
from .extended_review import read_extended_review
from .repository import RunRepository

TASK_KEY = "HOTFIX-RUN-COMPLETE-1106"
_TERMINAL = frozenset({"published", "partial", "failed", "cancelled"})
_CODE = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_WINDOW = re.compile(r"w[0-9]{3,10}\Z")
_OPERATOR_ERRORS = frozenset({"operator_task_key_invalid", "operator_run_control_unavailable",
    "operator_source_not_terminal", "operator_existing_consent_invalid", "operator_metered_route_refused"})
_REPLY_ERRORS = frozenset({"saved_reply_integrity_invalid", "saved_reply_request_binding_invalid",
    "reply_shape_invalid", "duplicate_key", "nonfinite"})
_COUNTS = frozenset({
    "blocks_total", "blocks_selected", "blocks_processed", "blocks_remaining",
    "pages_total", "pages_selected", "pages_processed", "pages_remaining", "pages_known",
    "characters_total", "characters_selected", "characters_processed", "characters_remaining",
    "characters_total_known", "characters_indexed", "facts_received", "facts_rejected",
    "facts_rejections_unresolved", "rejected_candidate_count", "repair_calls_completed", "calls_completed", "calls_partial", "calls_failed",
    "pieces_total", "pieces_selected", "pieces_processed", "pieces_remaining",
    "pieces_total_known", "pieces_indexed", "pieces_omitted_from_index", "pieces_not_selected",
    "source_records_total", "source_records_scanned", "source_records_not_scanned",
    "invalid_source_records", "windows_in_plan", "windows_indexed", "windows_selected",
    "pairs_possible_in_index", "candidate_pairs_considered", "candidate_pairs_eligible",
    "pairs_selected", "pairs_pending", "pairs_planned", "pairs_completed", "pairs_remaining",
    "batches_planned", "batches_completed", "source_pages_compared", "windows_compared",
    "processed_items", "total_items", "planned", "completed", "remaining", "limit",
    "completed_calls", "replayed", "piece_terms_omitted", "postings_omitted",
    "index_term_events_omitted", "candidate_pair_events_omitted", "unexpanded_terms",
})
_FLAGS = frozenset({"selection_complete", "complete_input_scan", "truncated",
    "all_pairs_complete", "all_indexed_pairs_planned", "global_semantic_complete",
    "complete_document_claim", "pending_manifest_truncated", "omitted_manifest_truncated"})


def _code(value):
    return value if isinstance(value, str) and _CODE.fullmatch(value) else "unclassified"


def _counts(value):
    if not isinstance(value, dict):
        return {}
    return {key: item for key, item in value.items()
        if key in _COUNTS and type(item) is int and item >= 0
        or key in _FLAGS and type(item) is bool}


def _reasons(rows):
    return dict(sorted(Counter(_code(row.get("error_code") or row.get("reason"))
        for row in rows if isinstance(row, dict) and (row.get("error_code") or row.get("reason"))).items()))


def _procedures(value):
    return [{"id": _code(row.get("id")), "status": _code(row.get("status")),
        **({"reason": _code(row.get("reason"))} if row.get("reason") else {})}
        for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _part(value):
    if not isinstance(value, dict):
        return {}
    refusals = value.get("reply_refusals", [])
    unresolved = [row for row in refusals if row.get("status") != "resolved"]
    return {"status": _code(value.get("status")), "coverage": _counts(value.get("coverage")),
        "procedures": _procedures(value.get("procedures")),
        "batch_reasons": _reasons(value.get("batches", [])),
        "reply_refusals": {"resolved": len(refusals) - len(unresolved), "unresolved": len(unresolved),
            "original_codes": _reasons([record for row in refusals for record in row.get("rejected_records", [])]),
            "unresolved_codes": _reasons([record for row in unresolved
                for record in row.get("repair_rejected_records", row.get("rejected_records", []))])},
        "reason": _code(value.get("reason")) if value.get("reason") else None}


def _receipt_index(result):
    rows = list(result.get("batches", []))
    for window in result.get("windows", []):
        if isinstance(window, dict):
            rows.extend(window.get("batches", []))
    global_state = result.get("global_cross_window", {})
    if isinstance(global_state, dict):
        rows.extend(global_state.get("batches", []))
    return {row["request_sha256"]: row for row in rows if isinstance(row, dict)
        and isinstance(row.get("request_sha256"), str) and _HASH.fullmatch(row["request_sha256"])}


def _raw_refusals(store, rows, receipts):
    """Re-run only the pure source-ID validator against already saved responses."""
    failures = []
    for row in rows:
        receipt = receipts.get(row["request_sha256"])
        if (receipt is None or receipt.get("procedure") not in {"block_analysis", "comprehensive_analysis"}
                or receipt.get("window_id") == "global-cross-window"
                or receipt.get("status") not in {"failed", "partial"} or not row["blob_id"]):
            continue
        item = {"request_sha256": row["request_sha256"], "procedure": _code(receipt.get("procedure"))}
        try:
            raw = store.read(parse_blob_id(row["blob_id"]), verify=True)
            if (len(raw) != row["size_bytes"] or hashlib.sha256(raw).hexdigest() != row["blob_sha256"]):
                raise ValueError("saved_reply_integrity_invalid")
            document = json.loads(raw)
            if document.get("request_sha256") != row["request_sha256"]:
                raise ValueError("saved_reply_request_binding_invalid")
            rejected = []
            accepted = parse_extended_reply(document["response"]["output_text"],
                allowed_sources=set(receipt.get("source_ids", [])), rejected=rejected)
            item.update(accepted_records=len(accepted), refused_records=len(rejected),
                refusal_codes=_reasons(rejected))
        except DomainError as error:
            item["error"] = error.code.value
        except (KeyError, TypeError, ValueError) as error:
            item["error"] = str(error) if str(error) in _REPLY_ERRORS else "saved_reply_validation_failed"
        except Exception:
            item["error"] = "saved_reply_read_failed"
        failures.append(item)
    return failures


def status(run_id):
    sessions = get_session_factory()
    repository = RunRepository()
    with sessions() as session:
        run = repository.get(session, run_id)
        stages = repository.stage_results(session, run_id)
        cost = repository.cost(session, run_id)
        children = [row for row in repository.list_for_version(session, run.version_uid)
            if row.reaudit_of_run_id == run_id]
        calls = session.execute(text("""
            SELECT status, count(*) AS count FROM model_call WHERE run_id=:run GROUP BY status
        """), {"run": run_id}).mappings().all()
        effects = session.execute(text("""
            SELECT state, count(*) AS count FROM provider_call_effect WHERE run_id=:run GROUP BY state
        """), {"run": run_id}).mappings().all()
        replies = session.execute(text("""
            SELECT request_sha256,
                parameters ->> 'extended_reply_blob_id' AS blob_id,
                parameters ->> 'extended_reply_sha256' AS blob_sha256,
                (parameters ->> 'extended_reply_size')::bigint AS size_bytes
            FROM model_call WHERE run_id=:run AND parameters ? 'extended_reply_blob_id'
            ORDER BY created_at,model_call_id
        """), {"run": run_id}).mappings().all()
        output = {"operation": "status", "run_id": run_id, "state": _code(run.state),
            "reaudit_of_run_id": run.reaudit_of_run_id,
            "reaudits": [{"run_id": row.run_id, "state": _code(row.state)} for row in children],
            "terminal_reason": _code(run.terminal_reason) if run.terminal_reason else None,
            "wait_reason": _code(run.wait_reason) if run.wait_reason else None,
            "stages": [{"id": _code(stage.stage_id), "status": _code(stage.status)} for stage in stages],
            "cost": None if cost is None else {"model_call_count": cost.model_call_count,
                "cost_micros": cost.cost_micros, "basis": _code(cost.basis)},
            "model_call_statuses": {_code(row["status"]): int(row["count"]) for row in calls},
            "provider_effect_states": {_code(row["state"]): int(row["count"]) for row in effects}}
    store = S3BlobStore(S3StorageSettings.from_env())
    try:
        saved = read_extended_review(sessions, store, run_id)
    except DomainError as error:
        output["review"] = {"status": "not_available", "error": error.code.value}
        return output
    result = saved["result"]
    output["review"] = {**_part(result), "artifact_status": _code(saved["status"]),
        "text_coverage": _counts(result.get("text_coverage")),
        "window_progress": _counts(result.get("window_progress")),
        "warnings": [_code(value) for value in result.get("warnings", [])],
        "windows": [{"window_id": row["window_id"], **_part(row)} for row in result.get("windows", [])
            if isinstance(row, dict) and isinstance(row.get("window_id"), str) and _WINDOW.fullmatch(row["window_id"])],
        "global_cross_window": _part(result.get("global_cross_window"))}
    parameters = result.get("project_parameters", {})
    output["review"]["project_parameters"] = {**_part(parameters),
        "rejection_codes": _reasons(parameters.get("rejected_facts", [])),
        "unresolved_rejection_codes": _reasons([row for row in parameters.get("rejected_facts", [])
            if not row.get("resolved_by_repair")]),
        "unresolved_rejection_fields": dict(Counter(_code(field)
            for row in parameters.get("rejected_facts", []) if not row.get("resolved_by_repair")
            for field in row.get("invalid_fields", []))),
        "reply_rejection_codes": _reasons(parameters.get("rejected_replies", []))}
    output["review"]["norm_lookup_reasons"] = _reasons(result.get("norm_lookup_receipts", []))
    output["review"]["saved_reply_validation"] = _raw_refusals(store, replies, _receipt_index(result))
    return output


def reaudit_unmetered(run_id, key):
    if key != TASK_KEY:
        raise ValueError("operator_task_key_invalid")
    from auditmanager.bootstrap.public import build_application

    application = build_application(environ={**os.environ, "EXECUTION_ROLE": "api"})
    control = application.run_control
    if control is None or control.cost_preflight is None:
        raise ValueError("operator_run_control_unavailable")
    profile, bundle, mode = control.current_configuration()
    explicit = ({"analysis_profile_id": profile, "prompt_bundle_id": bundle}
        if control.section_profiles is None else {"section_profiles": control.section_profiles})
    command_key = IdempotencyKey(f"{key}:{run_id}")
    with application.session_factory() as session:
        with session.begin():
            source = RunRepository().get(session, run_id)
            if source.state not in _TERMINAL:
                raise ValueError("operator_source_not_terminal")
            known = CommandRepository().find(session, command_type="reaudit_run", idempotency_key=command_key)
            if known is not None:
                approved = {} if known.outcome is None else known.outcome.get("cost_consent", {})
                if (not isinstance(approved, dict) or approved.get("billing") != "unmetered"
                        or approved.get("ceiling_micros") != 0):
                    raise ValueError("operator_existing_consent_invalid")
                consent = {"estimate_digest": approved["estimate_digest"], "ceiling_micros": 0, "confirmed": True}
            else:
                estimate = control.cost_preflight.estimate_reaudit(session, run_id=run_id)
                value = estimate.as_dict()
                if value.get("billing") != "unmetered" or value.get("estimated_cost_micros") != 0:
                    raise ValueError("operator_metered_route_refused")
                consent = {"estimate_digest": estimate.estimate_digest, "ceiling_micros": 0, "confirmed": True}
                # Approve now to make the restriction explicit; the command recomputes
                # this exact fresh authority again before recording or enqueueing work.
                estimate.approve(consent, actor_user_uid=None)
            started = reaudit_run(session, source_run_id=run_id, roles=frozenset({"admin"}),
                idempotency_key=str(command_key), provider_mode=mode,
                input_budget_characters=control.input_budget_characters,
                connection_route=control.route_freezer, cost_preflight=control.cost_preflight,
                cost_consent=consent, cost_actor_uid=None, started_by_user_uid=None,
                group_admitter=control.group_admitter,
                # `D-670` (`HOSTS-INT-WIRE-01`, ADR-0028 decision 14): the same layout reader the API's re-audit hands this command
                # (``ExecutionAdapter.reaudit_run``): with the layout on the new run takes today's plan, and the estimate the consent was
                # approved for is the plan's. Read straight off the run adapter, not through ``getattr(..., None)``: a control without
                # the seam would take the legacy route in silence.
                stage_plans=control.stage_plans, **explicit)
    # The Job was committed by the command. The API carrier makes no model call;
    # the existing worker claims it through the usual durable queue and cost fence.
    if not started.replayed:
        control.submit_existing(started.run_id)
    return {"operation": "reaudit_unmetered", "run_id": started.run_id,
        "reaudit_of_run_id": run_id, "replayed": started.replayed,
        "billing": "unmetered", "ceiling_micros": 0, "operator_task": TASK_KEY}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    read = commands.add_parser("status")
    read.add_argument("run_id")
    repeat = commands.add_parser("reaudit-unmetered")
    repeat.add_argument("run_id")
    repeat.add_argument("--key", required=True)
    arguments = parser.parse_args(argv)
    try:
        run_id = str(RunId.parse(arguments.run_id))
        result = status(run_id) if arguments.operation == "status" else reaudit_unmetered(run_id, arguments.key)
    except DomainError as error:
        result = {"operation": arguments.operation, "error": error.code.value,
            "reason": _code(error.detail_fields.get("reason")) if error.detail_fields.get("reason") else None}
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 1
    except Exception as error:  # No traceback can put storage or database credentials in workflow logs.
        print(json.dumps({"operation": arguments.operation,
            "error": str(error) if isinstance(error, ValueError) and str(error) in _OPERATOR_ERRORS
                else "operator_failed"}, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
