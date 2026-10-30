"""Independent preliminary parameter hints for existing comprehensive/review calls."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from .core import canonical, digest

VERSION = "preliminary-parameter-review-context-v1"
SCOPES = ["comprehensive_analysis", "finding_review", "finding_correction"]


def policy(parameters_policy):
    return {"version": VERSION, "bundle_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "parameter_bundle_sha256": parameters_policy["bundle_sha256"], "scopes": list(SCOPES),
        "windows": "local_and_global", "max_facts": 16, "max_characters": 16_000,
        "input_tokens_per_call": 70_000}


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
        raise ValueError("project_parameter_review_context_changed_requires_consent")
    return True


def attach(request, *, parameters, accepted, parameters_policy, procedure):
    if not validate_policy(accepted, parameters_policy=parameters_policy) or procedure not in accepted["scopes"]:
        raise ValueError("project_parameter_review_context_policy_required")
    body = deepcopy(dict(request.body))
    payload = json.loads(body["messages"][0]["content"])
    sources = payload.get("sources")
    if (not isinstance(sources, list) or not sources or any(not isinstance(source, dict)
            or not isinstance(source.get("source_id"), str) or not source["source_id"] for source in sources)):
        raise ValueError("project_parameter_review_context_sources_invalid")
    allowed = sorted({source["source_id"] for source in sources})
    pages = {source["page_number"] for source in sources if type(source.get("page_number")) is int}
    if (not isinstance(parameters, dict) or parameters.get("policy") != parameters_policy
            or not isinstance(parameters.get("facts"), list)):
        raise ValueError("project_parameter_review_context_saved_parameters_invalid")
    facts = parameters["facts"]
    for fact in facts:
        if (not isinstance(fact, dict) or not isinstance(fact.get("fact_id"), str)
                or not isinstance(fact.get("source_evidence"), list)
                or any(not isinstance(row, dict) or not isinstance(row.get("source_id"), str)
                    for row in fact["source_evidence"])):
            raise ValueError("project_parameter_review_context_fact_invalid")
    ordered = sorted(enumerate(facts), key=lambda entry: (
        not any(row.get("page_number") in pages for row in entry[1]["source_evidence"]), entry[0]))
    context = {"version": VERSION, "procedure": procedure, "parameter_status": parameters.get("status"),
        "parameter_source_sha256": parameters.get("source_sha256"), "parameter_manifest_sha256": parameters.get("manifest_sha256"),
        "facts": [], "candidates_received": len(facts), "facts_provided": 0, "facts_not_provided": len(facts),
        "complete_project_claim": False, "expert_confirmed": False,
        "original_source_allowlist_sha256": digest(allowed), "original_source_count": len(allowed)}
    selected = []
    for _, fact in ordered:
        if len(selected) >= accepted["max_facts"]:
            break
        supplied = {"context_fact_id": fact["fact_id"], "name": fact.get("name"), "parameter_type": fact.get("parameter_type"),
            "value": fact.get("value"), "unit": fact.get("unit"), "subject": fact.get("subject"),
            "source_quotes": [{**{key: deepcopy(value) for key, value in row.items() if key != "source_id"},
                "context_source_id": row["source_id"]} for row in fact["source_evidence"]]}
        proposed = {**context, "facts": [*context["facts"], supplied], "facts_provided": len(selected) + 1,
            "facts_not_provided": len(facts) - len(selected) - 1}
        if len(canonical(proposed)) > accepted["max_characters"]:
            continue
        selected.append(fact["fact_id"]); context = proposed
    if len(canonical(context)) > accepted["max_characters"]:
        raise ValueError("project_parameter_review_context_character_limit")
    payload["project_parameter_review_context"] = context
    body["messages"][0]["content"] = canonical(payload)
    body["system"] += ("\nproject_parameter_review_context — предварительные кандидаты параметров этого проекта "
        "с собственным ограниченным текстовым происхождением. Используй для понимания типа объекта, условий "
        "и сопоставимости значений; разные объекты/режимы могут иметь разные корректные значения. Это не нормативные "
        "требования, не утверждённый паспорт, не экспертное решение и не доказательство ошибки в текущем пакете. "
        "Ответ, source_ids, source_evidence и proposed_source_ids ограничены ТОЛЬКО исходными sources этого запроса. "
        "context_fact_id/context_source_id не расширяют разрешённые идентичности и не заменяют цитаты реально "
        "переданного исходного пакета. Сохрани оригиналы/закрытую схему и оговорки охвата; при недостатке "
        "проверяемого контекста запроси ручную сверку, не придумывай нарушение или исправление.")
    context_sha = digest(context)
    receipt = {"version": VERSION, "procedure": procedure, "context_sha256": context_sha, "context": context,
        "provided_fact_ids": selected, "allowed_original_source_ids": allowed,
        "parameter_status": parameters.get("status"), "candidates_received": len(facts),
        "facts_provided": len(selected), "facts_not_provided": len(facts) - len(selected),
        "encoded_context_characters": len(canonical(context)), "provided_only": True,
        "expert_confirmation_claimed": False}
    return replace(request, body=body,
        idempotency_scope=f"{request.idempotency_scope}:parameter-review-context:{context_sha}"), receipt
