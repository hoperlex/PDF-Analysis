"""Complete saved specification rows in the report's existing read-only snapshot.

Content-keyed extractions may originate from another version of the SAME project.
The saved comparison supplies the actual binding; origin identity is never relabelled.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from auditmanager.shared.errors import DomainError, ErrorCode

MAX_EXTRACTIONS = 4096
MAX_POSITIONS = 100_000


def _refuse(reason):
    return DomainError(ErrorCode.VALIDATION_FAILED, field="format", constraint=reason)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))


def _batch_ids(coverage):
    if coverage is None:
        return set()
    if not isinstance(coverage, dict):
        raise _refuse("comparison_technical_spec_coverage_invalid")
    batches = coverage.get("batches", [])
    if not isinstance(batches, list):
        raise _refuse("comparison_technical_spec_batches_invalid")
    ids = set()
    for batch in batches:
        if not isinstance(batch, dict):
            raise _refuse("comparison_technical_spec_batch_invalid")
        identity = batch.get("extraction_id")
        if identity is not None:
            if not isinstance(identity, str):
                raise _refuse("comparison_technical_spec_batch_identity_invalid")
            ids.add(identity)
    return ids


def collect_saved_specifications(session: Any, *, project_uid: str, document_uid: str,
        transitions: list[dict], comparisons: list[dict], max_bytes: int) -> dict:
    by_transition = {row["transition_id"]: row for row in transitions}
    requested = set(); bindings = []
    for comparison in comparisons:
        if comparison.get("project_uid") != project_uid or comparison.get("document_uid") != document_uid:
            raise _refuse("comparison_technical_spec_scope_mismatch")
        transition = by_transition.get(comparison["transition_id"])
        if transition is None:
            raise _refuse("comparison_technical_spec_transition_unavailable")
        for side, version_field in (("a", "source_version_uid"), ("b", "target_version_uid")):
            extraction_id = comparison.get(f"extraction_{side}_id")
            if extraction_id is not None:
                requested.add(extraction_id)
            coverage = comparison.get(f"coverage_{side}")
            checked_ids = _batch_ids(coverage)
            requested.update(checked_ids)
            bindings.append({"comparison_id": comparison.get("specification_id"),
                "transition_id": comparison["transition_id"], "method": comparison.get("source"),
                "side": side, "bound_version_uid": transition[version_field],
                "comparison_state": comparison["state"], "extraction_id": extraction_id,
                "saved_extraction_present": extraction_id is not None, "coverage": coverage,
                "checked_batch_extraction_ids": sorted(checked_ids)})
    budget = len(_json(bindings).encode())
    records = {}; positions = 0
    def load(identities):
        nonlocal budget, positions
        identities = set(identities) - set(records)
        if not identities:
            return
        if len(records) + len(identities) > MAX_EXTRACTIONS:
            raise _refuse("comparison_technical_spec_max_4096_extractions")
        # Count decompressed JSON text before fetching large positions/coverage values.
        metadata = list(session.execute(text(
            "SELECT comparison_spec_extraction_id AS extraction_id, "
            "octet_length(positions::text)+octet_length(coverage::text) AS payload_bytes "
            "FROM comparison_spec_extraction WHERE project_uid=:project AND "
            "comparison_spec_extraction_id=ANY(CAST(:ids AS text[])) ORDER BY comparison_spec_extraction_id"
        ), {"project": project_uid, "ids": sorted(identities)}).mappings())
        if {row["extraction_id"] for row in metadata} != identities:
            raise _refuse("comparison_technical_spec_linked_extraction_unavailable")
        if budget + sum(row["payload_bytes"] for row in metadata) > max_bytes:
            raise _refuse("comparison_technical_export_max_64_mib")
        rows = session.execute(text(
            "SELECT comparison_spec_extraction_id AS extraction_id, version_uid AS origin_version_uid, "
            "content_key,state,prompt_version,model_identity,recorded,source_sha256,positions,coverage, "
            "comparison_model_call_id AS model_call_id,created_at FROM comparison_spec_extraction "
            "WHERE project_uid=:project AND comparison_spec_extraction_id=ANY(CAST(:ids AS text[])) "
            "ORDER BY comparison_spec_extraction_id"
        ), {"project": project_uid, "ids": sorted(identities)}).mappings()
        for row in rows:
            record = dict(row)
            if not isinstance(record["positions"], list) or not isinstance(record["coverage"], dict):
                raise _refuse("comparison_technical_spec_extraction_invalid")
            candidates = record["coverage"].get("candidate_positions", [])
            if (not isinstance(candidates, list) or any(not isinstance(position, dict)
                    for position in [*record["positions"], *candidates])):
                raise _refuse("comparison_technical_spec_positions_invalid")
            if any(not isinstance(position.get("fields", {}), dict) for position in [*record["positions"], *candidates]):
                raise _refuse("comparison_technical_spec_fields_invalid")
            if record["coverage"].get("record_kind") == "raw_reply" or record["prompt_version"].endswith("/raw"):
                raise _refuse("comparison_technical_spec_raw_reply_not_exportable")
            positions += len(record["positions"]) + len(record["coverage"].get("candidate_positions", []))
            if positions > MAX_POSITIONS:
                raise _refuse("comparison_technical_spec_max_100000_positions")
            budget += len(_json(record).encode())
            if budget > max_bytes:
                raise _refuse("comparison_technical_export_max_64_mib")
            records[record["extraction_id"]] = record
    load(requested)
    child_ids = set().union(*(_batch_ids(row["coverage"]) for row in records.values())) if records else set()
    load(child_ids)
    # Expected relationship is aggregate -> checked batch, not an unbounded graph.
    if any(_batch_ids(row["coverage"]) - set(records) for row in records.values()):
        raise _refuse("comparison_technical_spec_nested_batch_reference_unsupported")
    for binding in bindings:
        aggregate = records.get(binding["extraction_id"])
        if aggregate is not None:
            binding["checked_batch_extraction_ids"] = sorted(set(binding["checked_batch_extraction_ids"]) |
                _batch_ids(aggregate["coverage"]))
    return {"format": "saved-whole-specifications/1", "project_uid": project_uid, "document_uid": document_uid,
        "bindings": bindings, "extractions": [records[key] for key in sorted(records)],
        "counts": {"bound_sides": len(bindings), "extractions": len(records), "position_records": positions},
        "provider_replies_included": False, "reextraction_performed": False, "model_calls": 0,
        "limitations": [
            "Сохранённые позиции включают неизменённые строки и полные поля, без сокращения публичной проекции изменений.",
            "Частичные извлечения и candidate_positions остаются предварительными; отсутствующая сторона не считается пустой.",
            "Origin version извлечения и bound version сравнения различаются при допустимом повторном использовании одинакового текста внутри проекта.",
            "Агрегат и проверенные части сохраняются отдельно; повтор записи между ними не является новой физической позицией.",
            "Новые вызовы модели, разбор PDF, пересчёт сравнения и экспертные решения не выполнялись."]}
