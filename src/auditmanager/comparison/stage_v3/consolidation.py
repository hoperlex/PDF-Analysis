"""Source-bound cross-batch global candidate consolidation, never expert acts."""
from __future__ import annotations

from copy import deepcopy
from itertools import combinations
from pathlib import Path
import hashlib

from auditmanager.comparison.stage_ai.requests import make_plan
from auditmanager.comparison.stage_ai.validation import StageAiValidationError, canonical_json, digest, parse_document
from auditmanager.comparison.stage_text.fragments import canonical_text
from . import procedures as legacy, windowed
from .original import schemas
from .original_consolidator.features import stems, jaccard, designations
from .policy import GLOBAL_VERSION, GLOBAL_LIMITS
from .report import card_display_metadata, merge_sources

ASSETS = Path(__file__).parent / "original_consolidator"
PROMPT = (ASSETS / "CONSOLIDATOR_PROMPT.txt").read_text(encoding="utf-8")
BUNDLE = digest({"plan_version": GLOBAL_VERSION, "limits": GLOBAL_LIMITS, "windowed": windowed.BUNDLE,
    "implementation": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "assets": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(ASSETS.iterdir())
               if path.is_file() and path.suffix in {".py", ".txt", ".json"}}})
MANIFEST_VERSION = "source-bound-global/1"
DECISIONS = ("DUPLICATE", "RELATED", "SEPARATE", "NEEDS_CONTEXT")
SCHEMA = schemas.obj(pair=schemas.PAIR_ID, decisions={"type": "array", "maxItems": 4,
    "items": schemas.obj(pair_id=schemas.S, event_ids={"type": "array", "minItems": 2, "maxItems": 2, "items": schemas.S},
        decision={"type": "string", "enum": list(DECISIONS)}, reason=schemas.S,
        source_evidence={"type": "array", "maxItems": 4, "items": schemas.obj(source_id=schemas.S, quote=schemas.S)})})


def _rebind(plan):
    payload = dict(plan.payload, plan_version=GLOBAL_VERSION, source_limits=GLOBAL_LIMITS)
    return make_plan(phase=plan.phase, group_id=plan.group_id, unit_key=plan.unit_key,
        source={"bundle": BUNDLE, "base_source_sha256": plan.source_sha256, "data": payload},
        payload=payload, schema=plan.response_schema, instructions=plan.instructions,
        version=BUNDLE, model=plan.model, output_tokens=plan.max_output_tokens)


def _refs(event): return {row["block_id"] for row in event["evidence_items"]}


def _candidate_pairs(snapshot, results, changes):
    raw, _hints = windowed.merged_changes(results)
    batches = {row["projectchange_id"]: ordinal for ordinal, batch in enumerate(windowed._dedupe_batches(raw)) for row in batch}
    features = {row["projectchange_id"]: set(stems((row["engineering_subject"] + " " + row["change_summary"])[:1000])) for row in changes}
    marks = {row["projectchange_id"]: designations((row["engineering_subject"] + " " + row["change_summary"])[:1000]) for row in changes}
    transitions = {row["projectchange_id"]: {(canonical_text(parameter["old_value"]), canonical_text(parameter["new_value"]))
        for parameter in row["changed_parameters"] if parameter["old_value"] and parameter["new_value"]
        and parameter["old_value"] != parameter["new_value"]} for row in changes}
    origins = {row["projectchange_id"]: {batches[key] for key in row.get("dedupe_lineage", [row["projectchange_id"]]) if key in batches} for row in changes}
    found = []
    for left, right in combinations(changes, 2):
        a, b = left["projectchange_id"], right["projectchange_id"]
        if origins[a] & origins[b]: continue  # their existing local call already compared them
        shared = len(_refs(left) & _refs(right))
        similarity = jaccard(features[a], features[b])
        both_pages = bool(set(left["old_pages"]) & set(right["old_pages"])) and bool(set(left["new_pages"]) & set(right["new_pages"]))
        cross_location = similarity >= .6 and bool(marks[a] & marks[b] or transitions[a] & transitions[b])
        if not shared and not (similarity >= .35 and both_pages) and not cross_location: continue
        ids = sorted((a, b))
        found.append({"pair_id": "vgp_" + digest(ids)[:24], "event_ids": ids,
            "rank": shared * 5 + similarity + (.25 if both_pages else 0),
            "candidate_reason": "shared_native_source" if shared else "cross_location_subject_and_transition" if cross_location else "cross_batch_subject_and_page_similarity"})
    ordered = sorted(found, key=lambda row: (-row["rank"], row["pair_id"]))
    selected = ordered[:GLOBAL_LIMITS["global_candidate_pairs"]]
    return selected, {"candidate_pairs": len(ordered), "planned_pairs": len(selected),
        "not_planned_pairs": len(ordered) - len(selected), "excluded_pair_ids_sha256": digest([row["pair_id"] for row in ordered[len(selected):]]),
        "candidate_policy": "all_cross_batch_source_or_subject_page_candidates", "feature_text_limit": 1000,
        "global_semantic_complete": False}


def _verification_map(ledger):
    return {(work["projectchange_id"], work["parameter_ordinal"]): work.get("result") for work in ledger["verification_work_items"]}


def _typed_parameters(event, verified):
    output = []
    for ordinal, parameter in enumerate(event["changed_parameters"], 1):
        result = verified.get((event["projectchange_id"], ordinal))
        effective = result if result and result["verdict"] in {"CONFIRMED", "CORRECTED"} else parameter
        output.append({"parameter_ordinal": ordinal, "name": parameter["name"], "location": parameter["location"],
            "original": deepcopy(parameter), "verification": deepcopy(result),
            "old_value": effective["old_value"], "new_value": effective["new_value"], "unit": effective["unit"]})
    return output


def _typed_conflicts(left, right, verified):
    conflicts = []
    for a in _typed_parameters(left, verified):
        for b in _typed_parameters(right, verified):
            key_a = (canonical_text(a["name"]), canonical_text(a["location"]))
            key_b = (canonical_text(b["name"]), canonical_text(b["location"]))
            if key_a == key_b and any(canonical_text(a[field]) != canonical_text(b[field]) for field in ("old_value", "new_value", "unit")):
                conflicts.append({"parameter_key": list(key_a), "left": a, "right": b})
    return conflicts


def _hint_conflicts(events, hints):
    refs = set().union(*(_refs(event) for event in events))
    return [hint["hint_id"] for hint in hints if hint["kind"] == "SOURCE_CONFLICT" and _refs(hint) & refs]


def _event_payload(event, verified):
    cuts = []
    def bounded(value, maximum, field):
        if len(value) > maximum: cuts.append(field)
        return value[:maximum]
    return {"event_id": event["projectchange_id"],
        **{field: bounded(event[field], 1200, field) for field in
           ("engineering_subject", "change_summary", "old_state", "new_state", "scope")},
        "parameters": [{"ordinal": row["parameter_ordinal"], "name": bounded(row["name"], 200, "parameter.name"),
            "location": bounded(row["location"], 300, "parameter.location"),
            "old_value": bounded(row["old_value"], 300, "parameter.old_value"),
            "new_value": bounded(row["new_value"], 300, "parameter.new_value"),
            "unit": bounded(row["unit"], 100, "parameter.unit"),
            "original_old_value": bounded(row["original"]["old_value"], 300, "parameter.original_old_value"),
            "original_new_value": bounded(row["original"]["new_value"], 300, "parameter.original_new_value"),
            "original_unit": bounded(row["original"]["unit"], 100, "parameter.original_unit"),
            "verification_verdict": None if row["verification"] is None else row["verification"]["verdict"]}
            for row in _typed_parameters(event, verified)],
        "source_ids": sorted(_refs(event)), "input_truncated": cuts}


def _payload_pair(pair, events, hints, verified):
    members = [events[identity] for identity in pair["event_ids"]]
    passages = []
    for member in members:
        for evidence in member["evidence_items"]:
            row = {"source_id": evidence["block_id"], "side": evidence["side"],
                "physical_page": evidence["physical_page"], "quote": evidence["relevant_fragment"][:800],
                "quote_excerpt": len(evidence["relevant_fragment"]) > 800}
            if row not in passages: passages.append(row)
    related = [hint for hint in hints if _refs(hint) & set().union(*(_refs(event) for event in members))]
    conflicts = _typed_conflicts(*members, verified)
    return {**pair, "events": [_event_payload(event, verified) for event in members], "source_passages": passages,
        "hints": [{"hint_id": hint["hint_id"], "kind": hint["kind"],
            "text": hint["missing_proof_or_conflict"][:800], "source_ids": sorted(_refs(hint))} for hint in related[:4]],
        "hint_coverage": {"related": len(related), "provided": min(4, len(related)), "all_originals_retained": True},
        "typed_conflicts": conflicts[:8], "typed_conflict_count": len(conflicts),
        "typed_conflicts_truncated": len(conflicts) > 8,
        "source_conflict_hint_ids": _hint_conflicts(members, hints)}


def _global_plans(snapshot, results, model, state=None):
    changes, hints, ledger, _cov, _records = state or windowed.reviewed(snapshot, results)
    candidates, _coverage = _candidate_pairs(snapshot, results, changes)
    events = {event["projectchange_id"]: event for event in changes}; verified = _verification_map(ledger)
    output, batch, length = [], [], 0
    def append(rows):
        identity = digest([row["pair_id"] for row in rows])[:24]
        body = {"pair": snapshot["stage_pair_id"], "plan_version": GLOBAL_VERSION,
            "pairs": rows, "_experimental_procedure": "consolidate",
            "_validation": {"pair_ids": [row["pair_id"] for row in rows]},
            "scope_coverage": {"global_semantic_complete": False, "all_original_records_retained": True}}
        output.append(make_plan(phase="synthesize", group_id="v3:consolidate:" + identity,
            unit_key="v3:consolidate:" + identity, source={"bundle": BUNDLE, "data": body}, payload=body,
            schema=SCHEMA, instructions=PROMPT + "\nАДАПТАЦИЯ: верни объект {pair,decisions} по закрытой схеме. "
                "Для каждого pairs[].pair_id ровно одно решение; event_ids точно повторяют вход. "
                "DUPLICATE означает предварительную рекомендацию, что это одно событие; RELATED — связанные самостоятельные события; "
                "SEPARATE — разные события; NEEDS_CONTEXT — недостаток источников. Не пиши пересборку, groups или recompositions. "
                "Для DUPLICATE нужны непустые source_evidence: ДОСЛОВНЫЕ quote из source_passages, относящиеся к обоим событиям. "
                "Учти независимую машинную сверку, typed_conflicts, source_conflict_hint_ids и input_truncated; "
                "конфликтующие значения не превращай в одно подтверждённое значение. Исходные события/подсказки не удаляются. "
                "Никакого экспертного решения, нормативного заключения или утверждения глобальной семантической полноты.",
            version=BUNDLE, model=model, output_tokens=6000))
    for candidate in candidates:
        row = _payload_pair(candidate, events, hints, verified); size = len(canonical_json(row))
        if size > 180_000: raise StageAiValidationError("v3_global_candidate_payload_budget")
        if batch and (len(batch) >= GLOBAL_LIMITS["global_pairs_per_call"] or length + size > 180_000):
            append(batch); batch, length = [], 0
        batch.append(row); length += size
    if batch: append(batch)
    return output


def plans_for(phase, snapshot, results, model):
    plans = windowed.plans_for(phase, snapshot, results, model)
    if phase != "synthesize" or any(plan.group_id not in results for plan in plans):
        return [_rebind(plan) for plan in plans]
    return _global_plans(snapshot, results, model)


def parse(plan, row, snapshot):
    if plan.payload["_experimental_procedure"] != "consolidate": return windowed.parse(plan, row, snapshot)
    if row["stop_reason"] != "end_turn": raise StageAiValidationError("v3_global_response_incomplete")
    answer = parse_document(row["output_text"]); legacy.check_schema(answer, SCHEMA)
    if answer["pair"] != snapshot["stage_pair_id"]: raise StageAiValidationError("v3_global_pair_mismatch")
    expected = {pair["pair_id"]: pair for pair in plan.payload["pairs"]}; seen = set()
    for decision in answer["decisions"]:
        key = decision["pair_id"]
        if key not in expected or key in seen or decision["event_ids"] != expected[key]["event_ids"]:
            raise StageAiValidationError("v3_global_partition_invalid")
        if not decision["reason"].strip() or len(decision["reason"]) > 1600: raise StageAiValidationError("v3_global_reason_invalid")
        supplied = expected[key]["source_passages"]
        for evidence in decision["source_evidence"]:
            if not evidence["quote"] or not any(evidence["source_id"] == source["source_id"] and evidence["quote"] in source["quote"] for source in supplied):
                raise StageAiValidationError("v3_global_quote_not_in_input")
        if decision["decision"] == "DUPLICATE":
            cited = {evidence["source_id"] for evidence in decision["source_evidence"]}
            if not cited or any(not cited.intersection(event["source_ids"]) for event in expected[key]["events"]):
                raise StageAiValidationError("v3_global_duplicate_without_bilateral_event_proof")
        seen.add(key)
    if seen != set(expected): raise StageAiValidationError("v3_global_partition_invalid")
    return answer


def _manifest(snapshot, results, state):
    changes, hints, ledger, _cov, _records = state
    candidates, scope = _candidate_pairs(snapshot, results, changes)
    index = {row["projectchange_id"]: row for row in changes}; verified = _verification_map(ledger)
    decisions = {row["pair_id"]: row for group, answer in sorted(results.items()) if group.startswith("v3:consolidate:") for row in answer["decisions"]}
    parent = {identity: identity for identity in index}
    def root(identity):
        while parent[identity] != identity: identity = parent[identity]
        return identity
    applied = []
    for candidate in sorted(candidates, key=lambda row: row["pair_id"]):
        decision = decisions.get(candidate["pair_id"])
        if decision is None: continue
        left, right = candidate["event_ids"]
        members = [event for identity, event in index.items() if root(identity) in {root(left), root(right)}]
        conflicts, conflict_count = [], 0
        for a, b in combinations(members, 2):
            found = _typed_conflicts(a, b, verified); conflict_count += len(found)
            conflicts.extend(found[:max(0, 64 - len(conflicts))])
        hint_conflicts = _hint_conflicts(members, hints)
        truncated = any(row["input_truncated"] for row in (_event_payload(index[left], verified), _event_payload(index[right], verified)))
        effective = decision["decision"]
        if effective == "DUPLICATE" and (conflict_count or hint_conflicts): effective = "RELATED_CONFLICT"
        elif effective == "DUPLICATE" and truncated: effective = "NEEDS_CONTEXT"
        if effective == "DUPLICATE": parent[root(right)] = root(left)
        applied.append({"pair_id": candidate["pair_id"], "event_ids": candidate["event_ids"],
            "model_decision": decision["decision"], "applied_decision": effective, "reason": decision["reason"],
            "source_evidence": deepcopy(decision["source_evidence"]), "typed_conflicts": conflicts,
            "typed_conflict_count": conflict_count, "typed_conflicts_truncated": conflict_count > len(conflicts),
            "source_conflict_hint_ids": hint_conflicts, "input_truncated": truncated})
    grouped = {}
    for identity in index: grouped.setdefault(root(identity), []).append(identity)
    groups = [{"group_id": "vgg_" + digest(sorted(ids))[:24], "event_ids": sorted(ids)} for ids in grouped.values() if len(ids) > 1]
    raw_events, raw_hints = windowed.merged_changes(results)
    scope.update(compared_pairs=len(applied), not_compared_pairs=scope["candidate_pairs"] - len(applied))
    manifest = {"version": MANIFEST_VERSION, "coverage": scope, "groups": groups, "decisions": applied,
        "original_events": raw_events, "original_hints": raw_hints,
        "parameter_verifications": deepcopy(ledger["verification_work_items"])}
    manifest["manifest_sha256"] = digest(manifest)
    return manifest


def reviewed(snapshot, results):
    state = windowed.reviewed(snapshot, results)
    manifest = _manifest(snapshot, results, state)
    state[3]["summary"].update(native_text_plan=GLOBAL_VERSION,
        global_consolidation=manifest["coverage"], semantic_comparison_complete=False)
    return state


def final_report_metadata(snapshot, results):
    return {"global_consolidation": _manifest(snapshot, results, windowed.reviewed(snapshot, results))}


def _event_ids(metadata):
    values = {metadata["event_id"]} if "event_id" in metadata else set()
    for related in metadata.get("related_events", []): values.update(_event_ids(related))
    return values


def canonical_cards(snapshot, results):
    state = windowed.reviewed(snapshot, results); manifest = _manifest(snapshot, results, state)
    if manifest["coverage"]["compared_pairs"] != manifest["coverage"]["planned_pairs"]:
        raise StageAiValidationError("v3_global_consolidation_incomplete")
    cards = legacy.canonical_cards(snapshot, results, reviewed_data=state)
    for group in manifest["groups"]:
        touched = [card for card in cards if _event_ids(card["experimental"]) & set(group["event_ids"])]
        if len(touched) < 2: continue
        target = touched[0]
        for other in touched[1:]:
            target["experimental"].setdefault("related_events", []).append(other["experimental"])
            target["experimental"]["parameters"].extend(other["experimental"].get("parameters", []))
            merge_sources(target["experimental"], other["experimental"])
            target["evidence_ids"] = sorted(set(target["evidence_ids"]) | set(other["evidence_ids"]))
            cards.remove(other)
    known_events = {event["projectchange_id"] for event in state[0]}
    for card in cards:
        metadata = card["experimental"]; refs = set(card["evidence_ids"]); events = _event_ids(metadata) & known_events
        metadata.update(plan_version=GLOBAL_VERSION, limits=deepcopy(GLOBAL_LIMITS),
            display_text=card_display_metadata(card),
            original_events=[deepcopy(event) for event in manifest["original_events"] if _refs(event) & refs],
            original_hints=[deepcopy(hint) for hint in manifest["original_hints"] if _refs(hint) & refs],
            global_consolidation={"manifest_sha256": manifest["manifest_sha256"],
                "group_ids": [group["group_id"] for group in manifest["groups"] if set(group["event_ids"]) & events],
                "event_ids": sorted(events), "coverage": manifest["coverage"]})
    return cards
