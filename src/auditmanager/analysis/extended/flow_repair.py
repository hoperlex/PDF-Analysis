"""Fresh-consent adapters of the original merge/verification rules.

No legacy request builder or quality bundle is edited. Relationships are advice
over immutable origins, and execution receipts do not assert that a claim is true.
Donors: PDF-proverka findings_merge_task.md and findings_verify/runner.py at dd974b2.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re

from .core import canonical, digest, parse_reply
from .review import _document, _validate, _numbers, _identifiers
from .finding_proposals import (build_proposal_review_request, parse_proposal_review_reply,
    proposal_review_schema)
from .substantive_review import (build_substantive_request, parse_substantive_reply, review_schema)

VERSION = "v2-flow-repair-v1"


def flow_policy():
    root = Path(__file__).resolve().parents[2]
    files = ("analysis/extended/flow_repair.py", "analysis/extended/workflow.py",
        "analysis/extended/core.py", "analysis/extended/review.py",
        "analysis/extended/substantive_review.py", "analysis/extended/finding_proposals.py",
        "analysis/extended/consolidation.py", "analysis/extended/related_context.py",
        "runs/v2_quality.py", "runs/extended_review.py", "runs/norm_queries.py",
        "runs/flow_norm_context.py", "runs/norm_context.py", "norms/paragraph_context.py",
        "precedents/candidate_context.py", "precedents/vectors/intents.py",
        "precedents/settings.py", "decision_memory/settings.py",
        "findings/publication.py", "jobs/extended_review.py")
    sha = hashlib.sha256()
    for name in files:
        sha.update(name.encode()); sha.update((root / name).read_bytes())
    return {"version": VERSION, "bundle_sha256": sha.hexdigest()}


def validate_flow_policy(value, *, compare_bundle=True):
    if (not isinstance(value, dict) or set(value) != {"version", "bundle_sha256"}
            or value.get("version") != VERSION or not isinstance(value.get("bundle_sha256"), str)
            or not re.fullmatch("[0-9a-f]{64}", value["bundle_sha256"])
            or compare_bundle and value != flow_policy()):
        raise ValueError("flow_repair_changed_requires_consent")
    return True


def origin_id(item, kind):
    return "xorigin_" + digest({"kind": kind, "observation": item})[:32]


def canonical_review_items(items, sources):
    """One authoritative input ID; expose each input's own admissible evidence."""
    registry = {source["source_id"]: source for source in sources}
    output = deepcopy(items)
    for item in output:
        checks = item.get("structural_checks")
        if isinstance(checks, dict):
            checks.pop("input_id", None)
            checks.pop("observation_id", None)
        admitted = item.get("evidence_source_ids", item["source_ids"])
        item["allowed_text_source_ids"] = sorted(ref for ref in admitted
            if registry.get(ref, {}).get("kind") == "text")
        item["allowed_image_source_ids"] = sorted(ref for ref in admitted
            if registry.get(ref, {}).get("kind") == "image")
    return output


def build_flow_review_request(*, proposals=False, **kwargs):
    kwargs = dict(kwargs)
    kwargs["items"] = canonical_review_items(kwargs["items"], kwargs["sources"])
    builder = build_proposal_review_request if proposals else build_substantive_request
    request = builder(**kwargs)
    body = deepcopy(request.body)
    schema = body["output_config"]["format"]["schema"]
    row = schema["properties"]["reviews"]["items"]
    row["properties"]["input_id"]["enum"] = [item["input_id"] for item in kwargs["items"]]
    body["system"] += (
        "\nЕдинственный идентификатор ответа — верхний input_id наблюдения. "
        "Для source_evidence разрешены ТОЛЬКО allowed_text_source_ids этого input_id и их дословные цитаты. "
        "Изображения никогда не цитируй в source_evidence: опиши видимое в visual_evidence, "
        "используя только allowed_image_source_ids этого входа и attached_image_ids. "
        "Неполнота дополнительного контекста другого наблюдения не делает этот вход неполным. "
        "Нормативная цитата supports не доказывает проектный факт. "
        "Утверждение об отсутствии проверяй по тому же объекту и режиму; без полного требуемого источника оставляй вопрос человеку.")
    return replace(request, body=body,
        idempotency_scope=f"{kwargs['run_id']}:{VERSION}:critic:{digest(body)}")


def parse_flow_review_reply(text, *, inputs, sources, attached_image_ids, rejected=None, proposals=False):
    # Reuse the source parser with an explicit per-input allowance for related
    # images. Its source_ids equality still binds the original observation.
    document = _document(text)
    schema = proposal_review_schema() if proposals else review_schema()
    envelope = deepcopy(schema); envelope["properties"]["reviews"]["items"] = {}
    _validate(document, envelope)
    registry = {source["source_id"]: source for source in sources}
    parser = parse_proposal_review_reply if proposals else parse_substantive_reply
    results, seen = [], set()
    for ordinal, row in enumerate(document["reviews"]):
        try:
            key = row.get("input_id") if isinstance(row, dict) else None
            if key not in inputs or key in seen:
                raise ValueError("substantive_review_input_binding_invalid")
            bound = deepcopy(inputs[key])
            allowed = set(bound.get("evidence_source_ids", bound["source_ids"]))
            original_sources = list(bound["source_ids"])
            adjusted = deepcopy(row)
            if len(adjusted.get("source_ids", [])) != len(set(adjusted.get("source_ids", []))):
                raise ValueError("substantive_review_input_binding_invalid")
            for evidence in adjusted.get("source_evidence", []):
                if registry.get(evidence.get("source_id"), {}).get("kind") != "text":
                    raise ValueError("substantive_review_visual_not_literal_text")
            for evidence in adjusted.get("visual_evidence", []):
                if (evidence.get("source_id") not in allowed
                        or registry.get(evidence.get("source_id"), {}).get("kind") != "image"):
                    raise ValueError("substantive_review_image_not_allowed_for_input")
            # Legacy parser permits only own visual sources. The new explicit
            # allowance has been checked above, so bind the same enlarged list
            # on both sides for its remaining strict validation.
            image_refs = [e["source_id"] for e in adjusted.get("visual_evidence", [])]
            bound["source_ids"] = list(dict.fromkeys([*original_sources, *image_refs]))
            adjusted["source_ids"] = list(dict.fromkeys([*adjusted.get("source_ids", []), *image_refs]))
            if set(row.get("source_ids", [])) != set(original_sources):
                raise ValueError("substantive_review_input_binding_invalid")
            parsed = parser(canonical({"reviews": [adjusted]}), inputs={key: bound},
                sources=sources, attached_image_ids=attached_image_ids)
            parsed[0]["source_ids"] = original_sources
            parsed[0]["policy"] = VERSION
            results.extend(parsed); seen.add(key)
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            if rejected is None:
                raise ValueError(str(error)) from None
            rejected.append({"reply_ordinal": ordinal, "reason": str(error), "record": deepcopy(row)})
    return results


def review_accounting(items, accepted, rejected):
    expected = [item["input_id"] for item in items]
    valid = {item["input_id"] for item in accepted}
    missing = [key for key in expected if key not in valid]
    return {"expected": len(expected), "valid": len(valid), "pending": len(missing), "refused": 0, "excluded": 0,
        "technical_refused_records": len(rejected), "missing_input_ids": missing,
        "complete": not missing}


def build_flow_repair_request(request, *, missing_input_ids=None, origin_request_sha256=None,
        required_pairs=None, accepted_relationships=None, **kwargs):
    from .core import build_semantic_repair_request
    repaired = build_semantic_repair_request(request, **kwargs)
    body = deepcopy(repaired.body)
    if required_pairs is not None:
        feedback = json.loads(body["messages"][-1]["content"])
        feedback["required_pairs"] = deepcopy(required_pairs)
        feedback["accepted_relationships"] = deepcopy(accepted_relationships or [])
        body["messages"][-1]["content"] = canonical(feedback)
        body["system"] += " Адресное уточнение отношений: верни только required_pairs последнего сообщения; принятые отношения не повторяй."
    if origin_request_sha256 is not None:
        if not isinstance(origin_request_sha256, str) or not re.fullmatch("[0-9a-f]{64}", origin_request_sha256):
            raise ValueError("flow_repair_origin_hash_invalid")
        feedback = json.loads(body["messages"][-1]["content"])
        feedback["semantic_repair"]["origin_request_sha256"] = origin_request_sha256
        body["messages"][-1]["content"] = canonical(feedback)
    body["system"] += (
        "\nАдресное уточнение: ранее принятые сервером записи не возвращай и не переписывай. "
        "Верни только исправления отказавших записей и ответы по отсутствующим input_id/required_pairs. "
        "При недостатке источника сохрани осмысленный вопрос человеку с явной неопределённостью.")
    if missing_input_ids is not None:
        allowed = sorted(missing_input_ids)
        body["system"] += " Разрешённые input_id этого уточнения: " + canonical(allowed) + "."
        schema = body["output_config"]["format"]["schema"]
        if "reviews" in schema["properties"]:
            rows = schema["properties"]["reviews"]
            rows["maxItems"] = len(allowed)
            rows["items"]["properties"]["input_id"]["enum"] = allowed
        elif "observations" in schema["properties"]:
            rows = schema["properties"]["observations"]
            rows["maxItems"] = len(allowed)
            if "input_ids" in rows["items"]["properties"]:
                rows["items"]["properties"]["input_ids"]["items"]["enum"] = allowed
    return replace(repaired, body=body)


def relevant_quote(text, items, *, limit=2000):
    """A literal native window near the issue's designation, with no fabricated range."""
    if len(text) <= limit:
        return text
    tokens = [token for item in items for token in re.findall(r"[\w./-]{4,}",
        item.get("title", "") + " " + item.get("description", ""))]
    folded = text.casefold()
    hits = [(folded.find(token.casefold()), token) for token in tokens]
    hits = [hit for hit in hits if hit[0] >= 0]
    # Prefer a literal mixed alphanumeric equipment designation over generic text.
    hits.sort(key=lambda hit: (not (any(c.isdigit() for c in hit[1])
        or "-" in hit[1]), -len(hit[1]), hit[0]))
    if not hits:
        return ""
    start = max(0, hits[0][0] - 300)
    return text[start:start+limit]


def build_flow_comprehensive_request(**kwargs):
    from .workflow import build_comprehensive_request
    request = build_comprehensive_request(**kwargs)
    body = deepcopy(request.body)
    payload = json.loads(body["messages"][0]["content"])
    origins = [*payload.get("text_observations", []), *payload.get("visual_observations", [])]
    refs = sorted({row["origin_id"] for row in origins})
    schema = body["output_config"]["format"]["schema"]
    schema["required"].append("relationships")
    schema["properties"]["relationships"] = {"type": "array", "maxItems": 160,
        "items": {"type": "object", "additionalProperties": False,
            "required": ["left_origin_id", "right_origin_id", "relation", "explanation"],
            "properties": {"left_origin_id": {"type": "string", **({"enum": refs} if refs else {})},
                "right_origin_id": {"type": "string", **({"enum": refs} if refs else {})},
                "relation": {"type": "string", "enum": ["match", "extension", "disputed", "unrelated"]},
                "explanation": {"type": "string", "minLength": 1, "maxLength": 1500}}}}
    body["system"] = body["system"].replace(
        "Это новый независимый поиск межисточниковых расхождений, а не пересказ или свод прежних замечаний.",
        "Сохрани независимый поиск новых расхождений в observations. Дополнительно выполни смысловой свод исходных замечаний в relationships.")
    body["system"] += (
        "\nПравила оригинала pdf-proverka: одна и та же проблема текста и чертежа с разными формулировками — match; "
        "дополняющие детали одной проблемы — extension; противоречащие версии — disputed, обе сохраняются человеку; "
        "разные объекты или режимы — unrelated. Используй только переданные точные origin_id, никаких новых ID. "
        "Для каждой required_pair верни ровно одно отношение. Отсутствие совпадения не удаляет исходное замечание. "
        "Не выдавай отсутствие элемента по неполному фрагменту за опровержение. Новый независимый вывод оставь в observations. "
        "Повышение важности и уточнение — только последующие предложения, решение всегда принимает эксперт.")
    return replace(request, body=body,
        idempotency_scope=f"{kwargs['run_id']}:{VERSION}:comprehensive:{digest(body)}")


def parse_flow_comprehensive_reply(text, *, allowed_sources, origins, required_pairs, rejected=None):
    value = _document(text)
    if not isinstance(value, dict) or set(value) != {"observations", "relationships"}:
        raise ValueError("flow_comprehensive_reply_shape_invalid")
    refused = rejected if rejected is not None else []
    observations = parse_reply(canonical({"observations": value["observations"]}),
        allowed_sources=allowed_sources, rejected=refused)
    links, covered = [], set()
    if not isinstance(value["relationships"], list) or len(value["relationships"]) > 160:
        raise ValueError("flow_relationships_invalid")
    for ordinal, row in enumerate(value["relationships"]):
        try:
            if (not isinstance(row, dict) or set(row) != {"left_origin_id", "right_origin_id", "relation", "explanation"}
                    or row["left_origin_id"] not in origins or row["right_origin_id"] not in origins
                    or row["left_origin_id"] == row["right_origin_id"]
                    or row["relation"] not in {"match", "extension", "disputed", "unrelated"}
                    or not isinstance(row["explanation"], str) or not 1 <= len(row["explanation"]) <= 1500):
                raise ValueError("flow_relationship_binding_invalid")
            pair = tuple(sorted((row["left_origin_id"], row["right_origin_id"])))
            if pair in covered:
                raise ValueError("flow_relationship_duplicate")
            covered.add(pair); links.append(deepcopy(row))
        except (ValueError, KeyError, TypeError) as error:
            refused.append({"relationship_ordinal": ordinal, "reason": str(error), "record": deepcopy(row)})
    missing = [list(pair) for pair in required_pairs if tuple(sorted(pair)) not in covered]
    if missing:
        refused.append({"reason": "flow_required_pairs_missing", "missing_pairs": missing})
    if rejected is None and refused:
        raise ValueError(refused[0]["reason"])
    return observations, links, missing


def consolidate_flow(observations, *, sources, version_uid, relationships, ensemble_batches=None):
    from .consolidation import consolidate_observations
    derived = consolidate_observations(observations, sources=sources, version_uid=version_uid,
        ensemble_batches=ensemble_batches)
    groups = derived["consolidated_observations"]
    disputed = {row.get(key) for row in relationships if row.get("relation") == "disputed"
        for key in ("left_origin_id", "right_origin_id")}
    # A new disputed assessment takes precedence over exact-word deduplication.
    # Preserve the original raw hashes while splitting only the affected group.
    split_groups = []
    for group in groups:
        if group["origin_count"] > 1 and any(observations[origin["raw_index"]].get("origin_id") in disputed
                for origin in group["origin_records"]):
            for origin in group["origin_records"]:
                item = observations[origin["raw_index"]]
                copied = deepcopy(group)
                copied.update(origin_records=[deepcopy(origin)], origin_count=1,
                    title=item["title"], description=item["description"], source_ids=list(item["source_ids"]),
                    source_count=len(item["source_ids"]), group_id="xgrp_"+digest({"version": VERSION,
                        "version_uid": version_uid, "origin": item.get("origin_id"), "raw_index": origin["raw_index"]})[:32])
                split_groups.append(copied)
        else:
            split_groups.append(group)
    groups = split_groups
    owners = {origin.get("origin_id"): index for index, origin in enumerate(observations) if origin.get("origin_id")}
    index_group = {origin["raw_index"]: index for index, group in enumerate(groups) for origin in group["origin_records"]}
    parents = list(range(len(groups)))
    def find(index):
        while parents[index] != index:
            index = parents[index]
        return index
    for row in relationships:
        left, right = owners.get(row.get("left_origin_id")), owners.get(row.get("right_origin_id"))
        if left is None or right is None or row.get("relation") not in {"match", "extension"}:
            continue
        a, b = find(index_group[left]), find(index_group[right])
        would_join = {observations[origin["raw_index"]].get("origin_id")
            for index, group in enumerate(groups) if find(index) in {a, b} for origin in group["origin_records"]}
        if any(link.get("relation") == "disputed" and link.get("left_origin_id") in would_join
                and link.get("right_origin_id") in would_join for link in relationships):
            continue
        if a != b:
            parents[max(a, b)] = min(a, b)
    merged = {}
    for index, group in enumerate(groups):
        key = find(index)
        if key not in merged:
            merged[key] = deepcopy(group)
        else:
            target = merged[key]
            target["origin_records"].extend(deepcopy(group["origin_records"]))
            target["source_ids"] = sorted(set(target["source_ids"]) | set(group["source_ids"]))
            target["origin_count"] += group["origin_count"]
            target["source_count"] = len(target["source_ids"])
    final = list(merged.values())
    for group in final:
        member_ids = {observations[o["raw_index"]].get("origin_id") for o in group["origin_records"]}
        links = [row for row in relationships if row.get("left_origin_id") in member_ids or row.get("right_origin_id") in member_ids]
        if links:
            group.update(relationships=deepcopy(links), grouping_status="semantic_origin_relationship",
                group_id="xgrp_" + digest({"version": VERSION, "version_uid": version_uid,
                    "members": sorted(value for value in member_ids if value)})[:32])
            for origin in group["origin_records"]:
                item = observations[origin["raw_index"]]
                origin.update(title=item["title"], description=item["description"])
    count = len(final); combined = sum(group["origin_count"] > 1 for group in final)
    derived["consolidated_observations"] = final
    derived["consolidation"].update(version=VERSION, method="validated_semantic_origin_relationships",
        group_count=count, coalesced_count=len(observations)-count, merged_group_count=combined, ungrouped_count=count-combined)
    return derived


def current_corrections(observations):
    """Moderate, additive response to the current critic, never an editing call."""
    corrections = []
    for item in observations:
        critic = item.get("critic", {})
        fix = critic.get("suggested_fix")
        fix = fix.strip() if isinstance(fix, str) else ""
        needs_context = critic.get("source_dependency") == "needs_more_context"
        if not (fix or critic.get("needs_correction") or needs_context):
            continue
        supplied = item.get("title", "") + "\n" + item.get("description", "")
        supplied += "\n" + "\n".join(entry.get("quote", "") for entry in critic.get("source_evidence", [])
            if isinstance(entry, dict))
        unsupported_detail = bool(_numbers(fix) - _numbers(supplied) or _identifiers(fix) - _identifiers(supplied))
        needs_context = needs_context or unsupported_detail
        row = {"input_id": item["observation_id"], "observation_id": item["observation_id"],
            "original": {key: deepcopy(item.get(key)) for key in ("title", "description", "source_ids")},
            "candidate": None, "action": "needs_context" if needs_context or not fix else "propose_revision",
            "source_ids": deepcopy(item.get("source_ids", [])), "reason": fix or
                "Уточнить источник, объект и режим проверки; исходное замечание сохранено.",
            "required_context": [fix or "Источник по тому же объекту и режиму"] if needs_context or not fix else [],
            "status": "requires_expert_review", "expert_decision": False,
            "mode": "deterministic", "model_called": False, "policy": VERSION}
        if unsupported_detail:
            row["required_context"] = ["Подтверждение предложенных чисел и марок по источнику того же объекта и режима"]
            row["reason"] = "Предложенная конкретизация требует подтверждения источником: " + fix
        if row["action"] == "propose_revision":
            row["candidate"] = {"title": item["title"], "description": fix[:3000],
                "source_ids": deepcopy(item["source_ids"]), "status": "proposed_requires_expert_review"}
        item["correction"] = row; corrections.append(row)
    return corrections
