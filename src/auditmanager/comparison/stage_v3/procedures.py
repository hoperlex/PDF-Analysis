"""Bounded native-TEXT execution of copied original V3 procedures, without I/O."""
from __future__ import annotations

import math
import re
from copy import deepcopy
from pathlib import Path

from auditmanager.comparison.stage_ai.loop import CallStep
from auditmanager.comparison.stage_ai.requests import make_plan
from auditmanager.comparison.stage_ai.validation import StageAiValidationError, digest, parse_document
from auditmanager.comparison.stage_text.fragments import canonical_text
from .mode import ENGINE, ORIGINAL_SHA
from .original import schemas, validate, coverage, supplemental, dedupe, quality, verification

VERSION = "native-text-v3/1"
MAX_PAGES = 16
MAX_CHARACTERS = 80_000
MAX_FRAGMENTS = 400
MAX_REGIONS = 8
MAX_CHANGES = 64
MAX_PARAMETERS = 64
PROMPTS = {name: (Path(__file__).parent / "original" / "prompts" / f"{name}_PROMPT.txt").read_text()
           for name in ("MAPPER", "MINER", "UNMATCHED", "DEDUPE", "VERIFY")}
BUNDLE = digest({"version": VERSION, "original": ORIGINAL_SHA, "prompts": PROMPTS,
                 "schemas": [schemas.MAP_SCHEMA, schemas.MINER_SCHEMA, schemas.DEDUPE_SCHEMA, schemas.VERIFICATION_SCHEMA]})

_VALUE_TOKEN = re.compile(r"(?<!\w)[+\-±−]\s*\d+(?:[.,]\d+)*|\d+(?:[.,]\d+)*|[^\W\d_]+|[^\s]")


def _native_value_tokens(text):
    tokens = [re.sub(r"^([+\-±−])\s+", r"\1", token)
              for token in _VALUE_TOKEN.findall(canonical_text(text))]
    # A label can introduce a displayed measurement with a comma ("склад,
    # 12,4"). Decimal/grouping punctuation remains INSIDE its number token;
    # standalone separators between numbers and all signs/operators survive.
    return [token for index, token in enumerate(tokens) if not (
        token == "," and 0 < index < len(tokens) - 1 and tokens[index - 1].isalpha()
        and len(tokens[index - 1]) > 1 and tokens[index + 1][0].isdigit())]


def value_in_native_text(value, text):
    wanted, source = _native_value_tokens(value), _native_value_tokens(text)
    return bool(wanted) and any(
        not (offset and source[offset - 1] in {"+", "-", "±", "−"})
        and source[offset:offset + len(wanted)] == wanted
        for offset in range(len(source) - len(wanted) + 1))


def check_schema(value, schema):
    """Validate the copied closed JSON schema without an extra dependency."""
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict) or set(value) != set(schema["required"]):
            raise StageAiValidationError("v3_response_object_schema")
        for key, spec in schema["properties"].items():
            check_schema(value[key], spec)
    elif kind == "array":
        if (not isinstance(value, list) or len(value) > min(1000, schema.get("maxItems", 1000))
                or len(value) < schema.get("minItems", 0)):
            raise StageAiValidationError("v3_response_array_budget")
        for item in value:
            check_schema(item, schema["items"])
    elif kind == "string":
        if not isinstance(value, str) or len(value) > 20_000 or len(value) < schema.get("minLength", 0):
            raise StageAiValidationError("v3_response_text_schema")
    elif kind in {"number", "integer"}:
        if (type(value) not in ({int} if kind == "integer" else {int, float}) or not math.isfinite(value)
                or value < schema.get("minimum", -math.inf) or value > schema.get("maximum", math.inf)):
            raise StageAiValidationError("v3_response_number_schema")
    if "enum" in schema and value not in schema["enum"]:
        raise StageAiValidationError("v3_response_enum_schema")


def source(snapshot):
    """All pinned native fragments, including exact exclusions and unpaired pages."""
    profiles = sorted(snapshot["all_profiles"], key=lambda r: (r["side"], r["version_uid"], r["page_number"]))
    if not 2 <= len(profiles) <= MAX_PAGES or len(snapshot["fragments"]) > MAX_FRAGMENTS:
        raise StageAiValidationError("v3_native_source_budget")
    pages, records = [], {}
    ordinals = {"OLD": 0, "NEW": 0}
    for profile in profiles:
        side = "OLD" if profile["side"] == "left" else "NEW"
        ordinals[side] += 1
        fragments = [f for f in snapshot["fragments"] if f["page_profile_id"] == profile["profile_id"]]
        if not fragments:
            raise StageAiValidationError("v3_native_page_without_text")
        blocks = [{"block_id": f["stage_text_fragment_id"], "modality": "TEXT", "block_type": "TEXT",
                   "structured_md": f["normalised_text"], "tables": [],
                   "bbox": [f["box_anchor"][k] for k in ("x0", "top", "x1", "bottom")],
                   "source_pdf": profile["version_uid"]} for f in fragments]
        page = {"side": side, "physical_page": ordinals[side], "blocks": blocks,
                "source_pdf": profile["version_uid"], "profile_id": profile["profile_id"],
                "original_page_number": profile["page_number"]}
        pages.append(page)
        records[(side, ordinals[side])] = page
    if any(count == 0 for count in ordinals.values()) or sum(len(b["structured_md"]) for p in pages for b in p["blocks"]) > MAX_CHARACTERS:
        raise StageAiValidationError("v3_native_source_budget")
    return pages, records


def plan(procedure, *, phase, group_id, pair_id, payload, model, metadata=None):
    name = {"mapper": "MAPPER", "miner": "MINER", "unmatched": "UNMATCHED", "dedupe": "DEDUPE", "verify": "VERIFY"}[procedure]
    schema = {"mapper": schemas.MAP_SCHEMA, "miner": schemas.MINER_SCHEMA, "unmatched": schemas.MINER_SCHEMA,
              "dedupe": schemas.DEDUPE_SCHEMA, "verify": schemas.VERIFICATION_SCHEMA}[procedure]
    body = dict(payload, pair=pair_id)
    return make_plan(phase=phase, group_id=group_id, unit_key=group_id,
        source={"engine": ENGINE, "version": BUNDLE, "data": body, "validation": metadata or {}},
        payload=body | {"_experimental_procedure": procedure, "_validation": metadata or {}},
        schema=schema, instructions=PROMPTS[name] + "\nЭксперимент: только native TEXT PDF. Не делай выводов о графике, нормах или полноте распознанных таблиц.",
        version=BUNDLE, model=model, output_tokens=8_000 if procedure in {"miner", "unmatched"} else 4_000)


def parse(plan, row, snapshot):
    if row["stop_reason"] != "end_turn":
        raise StageAiValidationError("v3_response_not_complete")
    try:
        answer = parse_document(row["output_text"])
        check_schema(answer, plan.response_schema)
        procedure = plan.payload["_experimental_procedure"]
        pages, records = source(snapshot)
        metadata = plan.payload["_validation"]
        pair = snapshot["stage_pair_id"]
        if answer.get("pair") != pair:
            raise ValueError("wrong pair")
        if procedure == "mapper":
            validate.validate_map(pair, answer, pages)
            if len(answer["regions"]) > MAX_REGIONS or any(len(r["region_id"]) > 64 for r in answer["regions"]):
                raise ValueError("region budget")
        elif procedure in {"miner", "unmatched"}:
            region = metadata["region"]
            validate.validate_miner(pair, region, answer, records)
            known = validate.known_blocks_for_region(region, records)
            # The copied validator checks event coordinates; native TEXT also
            # requires exact source quotes, including unresolved observations.
            for item in answer["projectchanges"] + answer["unresolved_hints"]:
                for evidence in item["evidence_items"]:
                    key = (evidence["side"], evidence["physical_page"], evidence["block_id"])
                    block = known.get(key)
                    if (block is None or evidence["block_type"] != "TEXT" or evidence["bbox"] != block["bbox"]
                            or evidence["source_pdf"] != records[key[:2]]["source_pdf"]
                            or evidence["crop_ref"] or not evidence["relevant_fragment"]
                            or evidence["relevant_fragment"] not in block["structured_md"]):
                        raise ValueError("untraceable native text quotation")
            if procedure == "unmatched":
                batch = dict(metadata["batch"], primary_keys=[tuple(key) for key in metadata["batch"]["primary_keys"]])
                supplemental.validate_supplemental_answer(batch, answer)
            if len(answer["projectchanges"]) > MAX_CHANGES or sum(len(c["changed_parameters"]) for c in answer["projectchanges"]) > MAX_PARAMETERS:
                raise ValueError("parameter budget")
            if any(len(item[key]) > 128 for rows, key in
                   ((answer["projectchanges"], "projectchange_id"), (answer["unresolved_hints"], "hint_id")) for item in rows):
                raise ValueError("event identity budget")
        elif procedure == "verify":
            verification.validate_verification_answer(pair_id=pair, batch=metadata["batch"], answer=answer)
            items = {item["work_item_id"]: item for item in metadata["batch"]["data"]["items"]}
            for result in answer["results"]:
                if result["verdict"] not in {"CONFIRMED", "CORRECTED"}:
                    continue
                item = items[result["work_item_id"]]
                if result["verdict"] == "CONFIRMED" and any(result[key] != item["parameter"][key]
                                                            for key in ("old_value", "new_value", "unit")):
                    raise ValueError("confirmation changes the proposed parameter")
                cited = {(ref["side"], ref["physical_page"], ref["block_id"]) for ref in result["evidence_refs"]}
                for side, field in (("OLD", "old_value"), ("NEW", "new_value")):
                    value = result[field]
                    text = "\n".join(src["structured_md"] for src in item["sources"]
                        if src["side"] == side and (side, src["physical_page"], src["block_id"]) in cited)
                    if value and not value_in_native_text(value, text):
                        raise ValueError("verified parameter absent from cited native text")
        elif procedure == "dedupe":
            dedupe.apply_dedupe(pair, metadata["changes"], answer, lossless=True)
        return answer
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise StageAiValidationError("v3_source_bound_response_invalid") from exc


def next_step(plan, row, snapshot):
    if row is None:
        return CallStep(plan, "v3", plan.content_key)
    parse(plan, row, snapshot)
    return None


def merged_changes(results):
    changes, hints = [], []
    for gid, answer in sorted(results.items()):
        if not gid.startswith(("v3:miner:", "v3:unmatched:")):
            continue
        for original in answer.get("projectchanges", []):
            copy = deepcopy(original)
            copy["projectchange_id"] = gid + ":" + copy["projectchange_id"]
            changes.append(copy)
        for original in answer.get("unresolved_hints", []):
            copy = deepcopy(original)
            copy["hint_id"] = gid + ":" + copy["hint_id"]
            hints.append(copy)
    if len(changes) > MAX_CHANGES or sum(len(c["changed_parameters"]) for c in changes) > MAX_PARAMETERS:
        raise StageAiValidationError("v3_native_result_budget")
    return changes, hints


def reviewed(snapshot, results):
    pages, records = source(snapshot)
    mapping = results["v3:mapper:all"]
    analysed = [r["region_id"] for r in mapping["regions"]]
    unmatched = supplemental.build_supplemental_batches(semantic_map=mapping, page_records=records,
                                                      max_primary_pages=8, candidate_pages_per_primary=2)
    reviewed_keys = [key for b in unmatched if "v3:unmatched:" + b["batch_id"] in results for key in b["primary_keys"]]
    cov = coverage.build_page_coverage(pair_id=snapshot["stage_pair_id"], run_id="native-text-experiment", structure=pages, semantic_map=mapping,
        analysed_region_ids=analysed, reviewed_unmatched_pages=reviewed_keys, page_records=records)
    changes, hints = merged_changes(results)
    if "v3:dedupe:all" in results:
        changes = dedupe.apply_dedupe(snapshot["stage_pair_id"], changes, results["v3:dedupe:all"], lossless=True)
    ledger = quality.build_quality_ledger(pair_id=snapshot["stage_pair_id"], run_id="native-text-experiment",
        projectchanges=changes, unresolved_hints=hints, hint_identities=[{"key": digest(h), "region_id": h["hint_id"].split(":")[-2], "hint_id": h["hint_id"]} for h in hints],
        coverage=cov, page_records=records, review_all_parameters=True)
    verified = [item for gid, answer in sorted(results.items()) if gid.startswith("v3:verify:") for item in answer["results"]]
    verification.apply_verification_results(ledger, verified)
    return changes, hints, ledger, cov, records


def plans_for(phase, snapshot, results, model):
    pages, records = source(snapshot)
    pair = snapshot["stage_pair_id"]
    if phase == "review":
        return [plan("mapper", phase=phase, group_id="v3:mapper:all", pair_id=pair, payload={"pages": pages}, model=model)]
    mapping = results.get("v3:mapper:all")
    if mapping is None:
        raise StageAiValidationError("v3_mapper_missing")
    if phase == "classify":
        plans = []
        for region in mapping["regions"]:
            chosen = [records[(side, page)] for side, field in (("OLD", "old_pages"), ("NEW", "new_pages")) for page in region[field]]
            plans.append(plan("miner", phase=phase, group_id="v3:miner:" + region["region_id"], pair_id=pair,
                payload={"region": region, "pages": chosen}, model=model, metadata={"region": region}))
        batches = supplemental.build_supplemental_batches(semantic_map=mapping, page_records=records,
                                                          max_primary_pages=8, candidate_pages_per_primary=2)
        if len(batches) > 4:
            raise StageAiValidationError("v3_unmatched_budget")
        for batch in batches:
            region = batch["region"]
            chosen = [records[(side, page)] for side, field in (("OLD", "old_pages"), ("NEW", "new_pages")) for page in region[field]]
            plans.append(plan("unmatched", phase=phase, group_id="v3:unmatched:" + batch["batch_id"], pair_id=pair,
                payload={"region": region, "pages": chosen}, model=model, metadata={"region": region, "batch": batch}))
        return plans
    changes, _hints = merged_changes(results)
    if changes and "v3:dedupe:all" not in results:
        return [plan("dedupe", phase=phase, group_id="v3:dedupe:all", pair_id=pair,
            payload={"projectchanges": [dedupe.compact_change(c) for c in changes]}, model=model,
            metadata={"changes": changes})]
    changes, hints, ledger, cov, records = reviewed(snapshot, results)
    batches = verification.build_verification_batches(work_items=ledger["verification_work_items"],
        projectchanges=changes, page_records=records, max_items_per_batch=8)
    if len(batches) > 8:
        raise StageAiValidationError("v3_verification_budget")
    return [plan("verify", phase=phase, group_id="v3:verify:" + batch["batch_id"], pair_id=pair,
                 payload=batch["data"], model=model, metadata={"batch": batch}) for batch in batches]


def canonical_cards(snapshot, results):
    changes, hints, ledger, cov, _records = reviewed(snapshot, results)
    if ledger["summary"].get("source_verification_pending"):
        raise StageAiValidationError("v3_verification_incomplete")
    cards = []
    for change in changes:
        refs = sorted({e["block_id"] for e in change["evidence_items"]})
        if not refs:
            raise StageAiValidationError("v3_event_without_evidence")
        parameters = []
        for ordinal, parameter in enumerate(change["changed_parameters"], 1):
            work = next((w for w in ledger["verification_work_items"] if w["projectchange_id"] == change["projectchange_id"] and w["parameter_ordinal"] == ordinal), None)
            parameters.append(dict(parameter, verification=None if work is None else work.get("result")))
        summary = change["change_summary"]
        title = summary if len(summary) <= 260 else "Изменение V3: полный текст в данных эксперимента"
        cards.append({"class_name": "REVIEW", "model_class": "REVIEW", "category": "uncertain", "system": "unknown",
            "title": title, "evidence_ids": refs, "materiality": "unknown", "importance": "unknown", "detail_increased": False,
            "experimental": {"engine": ENGINE, "source_version": ORIGINAL_SHA, "event_id": change["projectchange_id"],
                "engineering_subject": change["engineering_subject"], "change_summary": summary,
                "parameters": parameters, "quality": ledger["summary"], "coverage": cov["summary"],
                "source_sha256": digest([{key: fragment.get(key) for key in
                    ("stage_text_fragment_id", "content_key", "normalised_text", "box_anchor")}
                    for fragment in snapshot["fragments"]]),
                "norms_status": "not_checked", "native_text_only": True}})
    for hint in hints:
        refs = sorted({e["block_id"] for e in hint["evidence_items"]})
        if refs:
            cards.append({"class_name": "REVIEW", "category": "uncertain", "system": "unknown",
                "title": "Неподтверждённое наблюдение V3", "evidence_ids": refs,
                "experimental": {"engine": ENGINE, "event_id": hint["hint_id"], "parameters": [],
                    "observation": hint, "quality": ledger["summary"], "norms_status": "not_checked", "native_text_only": True}})
    # Distinct events can cite the same source: the existing card contract requires
    # an exact partition. Merge those cards explicitly, retaining event metadata.
    merged = []
    for card in cards:
        touched = [c for c in merged if set(c["evidence_ids"]) & set(card["evidence_ids"])]
        if not touched:
            merged.append(card)
            continue
        target = touched[0]
        target["experimental"].setdefault("related_events", []).append(card["experimental"])
        target["experimental"]["parameters"].extend(card["experimental"].get("parameters", []))
        target["evidence_ids"] = sorted(set(target["evidence_ids"]) | set(card["evidence_ids"]))
        for other in touched[1:]:
            target["experimental"]["related_events"].append(other["experimental"])
            target["experimental"]["parameters"].extend(other["experimental"].get("parameters", []))
            target["evidence_ids"] = sorted(set(target["evidence_ids"]) | set(other["evidence_ids"]))
            merged.remove(other)
    return merged
