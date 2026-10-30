"""Fresh windowed-v1 native V3: compact catalogue, full bounded source packs.

Mapper receives explicit representative excerpts of every page. Miner receives
every native block through bounded Cartesian packs inside each mapped region.
Unmatched candidate scope is deliberately bounded and reported as such.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import product
from pathlib import Path
import hashlib

from auditmanager.comparison.stage_ai.requests import make_plan
from auditmanager.comparison.stage_ai.validation import StageAiValidationError, canonical_json, digest, parse_document
from . import procedures as legacy
from .original import coverage, dedupe, quality, schemas, supplemental, validate, verification
from .policy import LIMITS, VERSION
from .report import card_display_metadata

BUNDLE = digest({"plan_version": VERSION, "limits": LIMITS, "legacy_prompts": legacy.BUNDLE,
    "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "dependency_sha256": {str(path.relative_to(Path(__file__).parent)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [Path(__file__).with_name(name) for name in ("procedures.py", "report.py", "policy.py")]
        + sorted((Path(__file__).parent / "original").glob("*.py"))}})
MAPPER_GROUP = "v3:mapper:catalogue"


def source(snapshot):
    profiles = sorted(snapshot["all_profiles"], key=lambda row: (row["side"], row["version_uid"], row["page_number"]))
    fragments = snapshot["fragments"]
    if not 2 <= len(profiles) <= LIMITS["pages"] or len(fragments) > LIMITS["fragments"]:
        raise StageAiValidationError("v3_windowed_source_budget")
    pages, records, ordinals = [], {}, {"OLD": 0, "NEW": 0}
    for profile in profiles:
        side = "OLD" if profile["side"] == "left" else "NEW"
        ordinals[side] += 1
        selected = sorted((fragment for fragment in fragments if fragment["page_profile_id"] == profile["profile_id"]),
                          key=lambda row: (row["box_anchor"]["top"], row["box_anchor"]["x0"], row["stage_text_fragment_id"]))
        if not selected:
            raise StageAiValidationError("v3_native_page_without_text")
        blocks = [{"block_id": row["stage_text_fragment_id"], "modality": "TEXT", "block_type": "TEXT",
            "structured_md": row["normalised_text"], "tables": [], "source_pdf": profile["version_uid"],
            "bbox": [row["box_anchor"][key] for key in ("x0", "top", "x1", "bottom")]} for row in selected]
        page = {"side": side, "physical_page": ordinals[side], "blocks": blocks,
            "source_pdf": profile["version_uid"], "profile_id": profile["profile_id"],
            "original_page_number": profile["page_number"]}
        pages.append(page); records[(side, ordinals[side])] = page
    if not all(ordinals.values()) or sum(len(block["structured_md"]) for page in pages for block in page["blocks"]) > LIMITS["characters"]:
        raise StageAiValidationError("v3_windowed_source_budget")
    return pages, records


def catalogue(pages):
    output = []
    for page in pages:
        selected = page["blocks"][:LIMITS["catalogue_blocks_per_page"]]
        blocks = [dict(block, structured_md=block["structured_md"][:LIMITS["catalogue_snippet_characters"]],
            excerpt_truncated=len(block["structured_md"]) > LIMITS["catalogue_snippet_characters"]) for block in selected]
        output.append(dict(page, blocks=blocks, catalogue_only=True, full_block_count=len(page["blocks"]),
            omitted_block_count=len(page["blocks"]) - len(selected)))
    return output


def _plan(procedure, *, phase, group_id, pair, payload, model, metadata=None):
    name = {"mapper": "MAPPER", "miner": "MINER", "unmatched": "UNMATCHED", "dedupe": "DEDUPE", "verify": "VERIFY"}[procedure]
    schema = {"mapper": schemas.MAP_SCHEMA, "miner": schemas.MINER_SCHEMA, "unmatched": schemas.MINER_SCHEMA,
              "dedupe": schemas.DEDUPE_SCHEMA, "verify": schemas.VERIFICATION_SCHEMA}[procedure]
    body = dict(payload, pair=pair, plan_version=VERSION, source_limits=LIMITS,
        _experimental_procedure=procedure, _validation=metadata or {})
    # This counts the final envelope, including validation IDs. No hidden text
    # copy is put into validation metadata; shared make_plan checks again.
    if len(canonical_json(body)) + 100 > LIMITS["request_characters"]:
        raise StageAiValidationError("v3_windowed_encoded_request_budget")
    instructions = legacy.PROMPTS[name] + (
        "\nОГРАНИЧЕННЫЙ NATIVE-TEXT ПРОХОД windowed-v1. Графика и нормы не проверяются. "
        "Mapper видит каталог ВСЕХ страниц, но только явно усечённые репрезентативные выдержки, не полный текст. "
        "Miner получает конкретные source_pack: запрещены ссылки на блоки, которых нет в этом запросе. "
        "Не делай выводов об отсутствии по части источников. На событие не более 8 evidence_items; "
        "при нехватке контекста сохрани unresolved_hint. Полнота парных сравнений ограничена scope_coverage. "
        "Источник с реальным block_id и bbox обязателен; это предварительное наблюдение, не решение эксперта.")
    return make_plan(phase=phase, group_id=group_id, unit_key=group_id,
        source={"engine": "v3_native_text_experimental", "bundle": BUNDLE, "data": body},
        payload=body, schema=schema, instructions=instructions, version=BUNDLE, model=model,
        output_tokens=8000 if procedure in {"mapper", "miner", "unmatched"} else 4000)


def _packs(pages):
    packs, current, length = [], [], 0
    for page in pages:
        for block in page["blocks"]:
            size = len(canonical_json(block)) + 250
            if size > LIMITS["pack_characters"]:
                raise StageAiValidationError("v3_windowed_single_block_budget")
            if current and (length + size > LIMITS["pack_characters"] or len(current) >= LIMITS["pack_blocks"]):
                packs.append(current); current, length = [], 0
            current.append((page, block)); length += size
    if current: packs.append(current)
    output = []
    for rows in packs:
        grouped = {}
        for page, block in rows:
            key = (page["side"], page["physical_page"])
            grouped.setdefault(key, dict(page, blocks=[]))["blocks"].append(block)
        output.append(list(grouped.values()))
    return output


def _region_plans(mapping, records, pair, model):
    output = []
    for region in mapping["regions"]:
        old = _packs([records[("OLD", page)] for page in region["old_pages"]])
        new = _packs([records[("NEW", page)] for page in region["new_pages"]])
        for left, right in product(old, new):
            pages = [*left, *right]
            key = digest({"region": region["region_id"], "blocks": [block["block_id"] for page in pages for block in page["blocks"]]})[:24]
            scoped = dict(region, old_pages=[page["physical_page"] for page in left], new_pages=[page["physical_page"] for page in right])
            output.append(_plan("miner", phase="classify", group_id="v3:miner:" + key, pair=pair, model=model,
                payload={"region": scoped, "pages": pages, "source_pack": key,
                    "scope_coverage": {"region_id": region["region_id"], "old_packs": len(old), "new_packs": len(new),
                        "comparison": "bounded_cartesian_source_packs", "full_region_in_single_request": len(old) == len(new) == 1}},
                metadata={"region": scoped, "parent_region_id": region["region_id"],
                    "block_ids": [block["block_id"] for page in pages for block in page["blocks"]]}))
    # Unmatched review considers at most two deterministic opposite candidates;
    # every primary unmatched block is still retained and reviewed in a pack.
    batches = supplemental.build_supplemental_batches(semantic_map=mapping, page_records=records,
        max_primary_pages=1, candidate_pages_per_primary=2)
    present = {tuple(key) for batch in batches for key in batch["primary_keys"]}
    for side, field in (("OLD", "unmatched_old"), ("NEW", "unmatched_new")):
        for number in mapping[field]:
            if (side, number) in present: continue
            # Genuine one-sided observation, never a fabricated counterpart.
            batches.append({"batch_id": f"ONE-{side}-{number}", "primary_keys": [(side, number)],
                "region": {"region_id": f"ONE-{side}-{number}",
                    "old_pages": [number] if side == "OLD" else [], "new_pages": [number] if side == "NEW" else [],
                    "engineering_domain": "Unmatched native source", "scope": "One-sided source review; no counterpart",
                    "locations": [], "reason_for_correspondence": "No lexical counterpart candidate is available.",
                    "important_text_blocks": [], "important_table_blocks": [], "important_graphic_blocks": [], "confidence": 0}})
    for batch in batches:
        region = batch["region"]
        primary = set(tuple(key) for key in batch["primary_keys"])
        primary_pages = [records[key] for key in sorted(primary)]
        candidate_pages = [records[(side, page)] for side, field in (("OLD", "old_pages"), ("NEW", "new_pages"))
                           for page in region[field] if (side, page) not in primary]
        candidates = _packs(candidate_pages)
        for primary_pack in _packs(primary_pages):
            for candidate_pack in candidates or [[]]:
                pages = [*primary_pack, *candidate_pack]
                key = digest({"batch": batch["batch_id"], "blocks": [block["block_id"] for page in pages for block in page["blocks"]]})[:24]
                scoped = dict(region, old_pages=sorted({page["physical_page"] for page in pages if page["side"] == "OLD"}),
                    new_pages=sorted({page["physical_page"] for page in pages if page["side"] == "NEW"}))
                output.append(_plan("unmatched", phase="classify", group_id="v3:unmatched:" + key, pair=pair, model=model,
                    payload={"region": scoped, "pages": pages, "source_pack": key,
                        "scope_coverage": {"candidate_pages_per_primary": 2, "candidate_selection": "bounded_original_supplemental", "global_candidate_search_complete": False}},
                    metadata={"region": scoped, "block_ids": [block["block_id"] for page in pages for block in page["blocks"]],
                        "primary_keys": [list(key) for key in sorted(primary)]}))
    if len(output) > LIMITS["classification_units"]:
        raise StageAiValidationError("v3_windowed_classification_unit_budget")
    return output


def merged_changes(results):
    changes, hints = [], []
    for group, answer in sorted(results.items()):
        if not group.startswith(("v3:miner:", "v3:unmatched:")): continue
        for original in answer.get("projectchanges", []):
            changes.append(deepcopy(original) | {"projectchange_id": group + ":" + original["projectchange_id"]})
        for original in answer.get("unresolved_hints", []):
            hints.append(deepcopy(original) | {"hint_id": group + ":" + original["hint_id"]})
    if len(changes) > LIMITS["events"] or sum(len(row["changed_parameters"]) for row in changes) > LIMITS["parameters"] or len(hints) > 1024:
        raise StageAiValidationError("v3_windowed_result_budget")
    return changes, hints


def _dedupe_batches(changes):
    output, rows, length = [], [], 0
    for change in changes:
        size = len(canonical_json(dedupe.compact_change(change)))
        if size > 120_000: raise StageAiValidationError("v3_windowed_dedupe_item_budget")
        if rows and (len(rows) >= 8 or length + size > 120_000): output.append(rows); rows, length = [], 0
        rows.append(change); length += size
    if rows: output.append(rows)
    return output


def reviewed(snapshot, results):
    pages, records = source(snapshot)
    mapping = results[MAPPER_GROUP]
    work = _region_plans(mapping, records, snapshot["stage_pair_id"], "deterministic-planning")
    analysed = [region["region_id"] for region in mapping["regions"]
        if all(plan.group_id in results for plan in work if plan.payload["_validation"].get("parent_region_id") == region["region_id"])]
    primary = {tuple(key) for plan in work for key in plan.payload["_validation"].get("primary_keys", [])}
    reviewed_keys = [key for key in primary if all(plan.group_id in results for plan in work
        if list(key) in plan.payload["_validation"].get("primary_keys", []))]
    cov = coverage.build_page_coverage(pair_id=snapshot["stage_pair_id"], run_id="native-windowed-experiment",
        structure=pages, semantic_map=mapping, analysed_region_ids=analysed, reviewed_unmatched_pages=reviewed_keys, page_records=records)
    changes, hints = merged_changes(results)
    merged = []
    for batch in _dedupe_batches(changes):
        group = "v3:dedupe:" + digest([row["projectchange_id"] for row in batch])[:24]
        merged.extend(dedupe.apply_dedupe(snapshot["stage_pair_id"], batch, results[group], lossless=True) if group in results else batch)
    ledger = quality.build_quality_ledger(pair_id=snapshot["stage_pair_id"], run_id="native-windowed-experiment",
        projectchanges=merged, unresolved_hints=hints,
        hint_identities=[{"key": digest(hint), "region_id": hint["hint_id"], "hint_id": hint["hint_id"]} for hint in hints],
        coverage=cov, page_records=records, review_all_parameters=True)
    verified = [row for group, answer in sorted(results.items()) if group.startswith("v3:verify:") for row in answer["results"]]
    verification.apply_verification_results(ledger, verified)
    cov["summary"].update(native_text_plan=VERSION, catalogue_complete=True,
        unmatched_candidate_search_complete=not bool(primary), semantic_comparison_complete=False)
    return merged, hints, ledger, cov, records


def plans_for(phase, snapshot, results, model):
    pages, records = source(snapshot); pair = snapshot["stage_pair_id"]
    if phase == "review":
        return [_plan("mapper", phase=phase, group_id=MAPPER_GROUP, pair=pair, model=model,
            payload={"pages": catalogue(pages), "catalogue_coverage": {"all_pages": len(pages),
                "all_source_text_provided": False, "representative_blocks_per_page": LIMITS["catalogue_blocks_per_page"],
                "full_native_source_retained": True}})]
    mapping = results.get(MAPPER_GROUP)
    if mapping is None: raise StageAiValidationError("v3_mapper_missing")
    if phase == "classify": return _region_plans(mapping, records, pair, model)
    changes, _hints = merged_changes(results)
    dedupe_plans = []
    for batch in _dedupe_batches(changes):
        group = "v3:dedupe:" + digest([row["projectchange_id"] for row in batch])[:24]
        dedupe_plans.append(_plan("dedupe", phase=phase, group_id=group, pair=pair, model=model,
            payload={"projectchanges": [dedupe.compact_change(row) for row in batch],
                "scope_coverage": {"dedupe_scope": "bounded_batch", "global_semantic_dedupe_complete": False}},
            metadata={"change_ids": [row["projectchange_id"] for row in batch]}))
    if any(plan.group_id not in results for plan in dedupe_plans): return dedupe_plans
    changes, _hints, ledger, _cov, records = reviewed(snapshot, results)
    batches = verification.build_verification_batches(work_items=ledger["verification_work_items"],
        projectchanges=changes, page_records=records, max_items_per_batch=1)
    for batch in batches:
        for item in batch["data"]["items"]:
            all_sources = item["sources"]
            chosen = []
            for side, field in (("OLD", "old_value"), ("NEW", "new_value")):
                available = [row for row in all_sources if row["side"] == side]
                matching = [row for row in available if item["parameter"][field]
                    and legacy.value_in_native_text(item["parameter"][field], row["structured_md"])]
                if available:
                    chosen.append(min(matching or available, key=lambda row: (len(canonical_json(row)), row["block_id"])))
            item["sources"] = chosen
            item["source_selection"] = {"scope": "bounded_parameter_value_sources",
                "available_source_count": len(all_sources), "provided_source_count": len(chosen),
                "omitted_source_ids": [row["block_id"] for row in all_sources if row not in chosen],
                "full_event_context_provided": len(chosen) == len(all_sources)}
    return [_plan("verify", phase=phase, group_id="v3:verify:" + batch["batch_id"], pair=pair, model=model,
        payload=batch["data"], metadata={"work_item_ids": [row["work_item_id"] for row in batch["data"]["items"]]}) for batch in batches]


def parse(plan, row, snapshot):
    if row["stop_reason"] != "end_turn": raise StageAiValidationError("v3_response_not_complete")
    try:
        answer = parse_document(row["output_text"]); legacy.check_schema(answer, plan.response_schema)
        pages, records = source(snapshot); procedure = plan.payload["_experimental_procedure"]
        if answer.get("pair") != snapshot["stage_pair_id"]: raise ValueError("wrong pair")
        metadata = plan.payload["_validation"]
        if procedure == "mapper":
            validate.validate_map(snapshot["stage_pair_id"], answer, catalogue(pages))
            if len(answer["regions"]) > 64 or any(len(region["region_id"]) > 64 for region in answer["regions"]): raise ValueError("region budget")
            # One page may participate in one region in this bounded policy;
            # overlapping mappings would otherwise multiply paid cross-products.
            for side in ("old_pages", "new_pages"):
                listed = [page for region in answer["regions"] for page in region[side]]
                if len(listed) != len(set(listed)): raise ValueError("overlapping windowed regions")
            shown = {(page["side"], page["physical_page"], block["block_id"])
                for page in catalogue(pages) for block in page["blocks"]}
            for region in answer["regions"]:
                for field in ("important_text_blocks", "important_table_blocks", "important_graphic_blocks"):
                    for reference in region[field]:
                        if ((reference["side"], reference["physical_page"], reference["block_id"]) not in shown
                                or reference["block_type"] != "TEXT"):
                            raise ValueError("mapper cites unavailable catalogue block")
        elif procedure in {"miner", "unmatched"}:
            selected = set(metadata["block_ids"])
            scoped = {key: dict(page, blocks=[block for block in page["blocks"] if block["block_id"] in selected]) for key, page in records.items()}
            validate.validate_miner(snapshot["stage_pair_id"], metadata["region"], answer, scoped)
            known = validate.known_blocks_for_region(metadata["region"], scoped)
            for item in answer["projectchanges"] + answer["unresolved_hints"]:
                if len(item["evidence_items"]) > 8: raise ValueError("event evidence budget")
                for evidence in item["evidence_items"]:
                    key = (evidence["side"], evidence["physical_page"], evidence["block_id"])
                    block = known.get(key)
                    if (block is None or evidence["block_type"] != "TEXT" or evidence["bbox"] != block["bbox"]
                            or evidence["source_pdf"] != records[key[:2]]["source_pdf"] or evidence["crop_ref"]
                            or not evidence["relevant_fragment"] or evidence["relevant_fragment"] not in block["structured_md"]):
                        raise ValueError("untraceable source-pack quotation")
            for items, key in ((answer["projectchanges"], "projectchange_id"), (answer["unresolved_hints"], "hint_id")):
                if any(not item[key] or len(item[key]) > 128 for item in items): raise ValueError("event identity budget")
            for hint in answer["unresolved_hints"]:
                if (not set(hint["old_pages"]) <= set(metadata["region"]["old_pages"])
                        or not set(hint["new_pages"]) <= set(metadata["region"]["new_pages"])):
                    raise ValueError("hint outside source pack")
            if len(answer["projectchanges"]) > 64 or sum(len(change["changed_parameters"]) for change in answer["projectchanges"]) > 64:
                raise ValueError("unit result budget")
            if procedure == "unmatched":
                primary = {tuple(key) for key in metadata["primary_keys"]}
                for item in answer["projectchanges"] + answer["unresolved_hints"]:
                    if not any((evidence["side"], evidence["physical_page"]) in primary for evidence in item["evidence_items"]):
                        raise ValueError("unmatched result without primary source")
                supplemental.validate_supplemental_answer({"primary_keys": sorted(primary)}, answer)
        elif procedure == "dedupe":
            ids = metadata["change_ids"]
            listed = [identity for decision in answer["decisions"] for identity in decision["projectchange_ids"]]
            if len(listed) != len(set(listed)) or set(listed) != set(ids): raise ValueError("dedupe partition")
            by_id = {change["projectchange_id"]: change for change in plan.payload["projectchanges"]}
            # Structural application is repeated later over the full immutable
            # changes. This checks the answer's action/cardinality now.
            for decision in answer["decisions"]:
                count = len(decision["projectchange_ids"])
                if ((decision["decision"] == "KEEP_SEPARATE" and count != 1)
                        or decision["decision"] == "MERGE_DUPLICATES" and count < 2
                        or any(identity not in by_id for identity in decision["projectchange_ids"])):
                    raise ValueError("dedupe action invalid")
        elif procedure == "verify":
            items = {item["work_item_id"]: item for item in plan.payload["items"]}
            ids = [result["work_item_id"] for result in answer["results"]]
            if len(ids) != len(set(ids)) or set(ids) != set(items): raise ValueError("verification partition")
            for result in answer["results"]:
                item = items[result["work_item_id"]]
                actual = {(source["side"], source["physical_page"], source["block_id"]): source for source in item["sources"]}
                cited = {(ref["side"], ref["physical_page"], ref["block_id"]) for ref in result["evidence_refs"]}
                if not cited or not cited <= set(actual): raise ValueError("verification source binding")
                if result["verdict"] == "CONFIRMED" and any(result[field] != item["parameter"][field] for field in ("old_value", "new_value", "unit")):
                    raise ValueError("confirmation changed values")
                if result["verdict"] in {"CONFIRMED", "CORRECTED"}:
                    for side, field in (("OLD", "old_value"), ("NEW", "new_value")):
                        text = "\n".join(actual[key]["structured_md"] for key in cited if key[0] == side)
                        if result[field] and not legacy.value_in_native_text(result[field], text): raise ValueError("value absent from cited source")
        return answer
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise StageAiValidationError("v3_windowed_source_bound_response_invalid") from exc


def canonical_cards(snapshot, results):
    cards = legacy.canonical_cards(snapshot, results, reviewed_data=reviewed(snapshot, results))
    for card in cards:
        card["experimental"].update(plan_version=VERSION, limits=deepcopy(LIMITS),
            display_text=card_display_metadata(card),
            scope_coverage={"mapper": "all_page_catalogue_representative_excerpts",
                "miner": "bounded_cartesian_region_source_packs", "unmatched_candidates_per_primary": 2,
                "dedupe": "within_bounded_batches", "semantic_comparison_complete": False})
    return cards
