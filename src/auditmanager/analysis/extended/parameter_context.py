"""Bounded preliminary parameter hints for visual requests, never new evidence authority."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from .core import canonical, digest

VERSION = "preliminary-project-parameter-context-v1"


def policy(parameters_policy):
    return {"version": VERSION, "bundle_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "parameter_bundle_sha256": parameters_policy["bundle_sha256"], "scope": "visual_blocks",
        "max_facts": 16, "max_characters": 16_000, "input_tokens_per_call": 70_000}


def validate_policy(value, *, parameters_policy, compare_bundle=True):
    if value is None:
        return False
    expected = policy(parameters_policy)
    if not compare_bundle and isinstance(value, dict):
        expected["bundle_sha256"] = value.get("bundle_sha256")
    if (not isinstance(value, dict) or set(value) != set(expected) or value != expected
            or not isinstance(value.get("bundle_sha256"), str) or len(value["bundle_sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in value["bundle_sha256"])
            or any(type(value[key]) is not int for key in ("max_facts", "max_characters", "input_tokens_per_call"))):
        raise ValueError("project_parameter_context_changed_requires_consent")
    return True


def attach(request, *, parameters, accepted, parameters_policy):
    if not validate_policy(accepted, parameters_policy=parameters_policy):
        raise ValueError("project_parameter_context_policy_required")
    body = deepcopy(dict(request.body))
    content = body["messages"][0]["content"]
    if not isinstance(content, str):
        raise ValueError("project_parameter_context_visual_payload_invalid")
    payload = json.loads(content)
    allowed = [source["source_id"] for source in payload["sources"]]
    pages = {source["page_number"] for source in payload["sources"]}
    if not isinstance(parameters, dict) or not isinstance(parameters.get("facts"), list):
        raise ValueError("project_parameter_context_saved_parameters_invalid")
    facts = parameters["facts"]
    for fact in facts:
        if (not isinstance(fact, dict) or not isinstance(fact.get("fact_id"), str)
                or not isinstance(fact.get("source_evidence"), list)
                or any(not isinstance(row, dict) for row in fact["source_evidence"])):
            raise ValueError("project_parameter_context_fact_shape_invalid")
    ordered = sorted(enumerate(facts), key=lambda entry: (
        not any(row.get("page_number") in pages for row in entry[1]["source_evidence"]), entry[0]))
    context = {"version": VERSION, "parameter_status": parameters.get("status"),
        "parameter_source_sha256": parameters.get("source_sha256"), "parameter_manifest_sha256": parameters.get("manifest_sha256"),
        "facts": [], "candidates_received": len(facts), "facts_provided": 0, "facts_not_provided": len(facts),
        "complete_project_claim": False, "expert_confirmed": False,
        "allowed_visual_source_ids": allowed}
    selected_ids = []
    for _, fact in ordered:
        if len(context["facts"]) >= accepted["max_facts"]:
            break
        supplied = {"context_fact_id": fact["fact_id"], "name": fact.get("name"), "value": fact.get("value"),
            "unit": fact.get("unit"), "subject": fact.get("subject"), "parameter_type": fact.get("parameter_type"),
            "source_quotes": [{key: deepcopy(row[key]) for key in
                ("quote", "page_number", "character_field", "character_start", "character_end", "entry_ordinal") if key in row}
                for row in fact["source_evidence"]]}
        proposed = {**context, "facts": [*context["facts"], supplied], "facts_provided": len(selected_ids) + 1,
            "facts_not_provided": len(facts) - len(selected_ids) - 1}
        if len(canonical(proposed)) > accepted["max_characters"]:
            continue
        context = proposed
        selected_ids.append(fact["fact_id"])
    context_sha = digest(context)
    if len(canonical(context)) > accepted["max_characters"]:
        raise ValueError("project_parameter_context_character_limit")
    payload["project_parameter_context"] = context
    body["messages"][0]["content"] = canonical(payload)
    body["system"] += ("\n\nproject_parameter_context — предварительные значения из текста этого проекта, "
        "не экспертный паспорт, не нормативное требование и не визуальное подтверждение. Используй для понимания "
        "объекта и проверки читаемых обозначений/размеров изображения. Значения могут относиться к разным условиям; "
        "проверяй собственный источник. Не выдумывай отсутствующие параметры и не превращай подсказку в нарушение. "
        "source_ids ответа допускаются ТОЛЬКО из allowed_visual_source_ids исходного визуального пакета. "
        "context_fact_id не является разрешённым source_id. Обрезанный охват не доказывает отсутствие данных.")
    receipt = {"version": VERSION, "context_sha256": context_sha, "provided_fact_ids": selected_ids,
        "parameter_status": parameters.get("status"), "candidates_received": len(facts),
        "facts_provided": len(selected_ids), "facts_not_provided": len(facts) - len(selected_ids),
        "encoded_context_characters": len(canonical(context)), "context": context,
        "provided_only": True, "visual_confirmation_claimed": False}
    # Replacement preserves both single-image and ordered multi-image custody bytes.
    return replace(request, body=body,
        idempotency_scope=f"{request.idempotency_scope}:parameter-context:{context_sha}"), receipt
