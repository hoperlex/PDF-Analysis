"""Fresh-consent severity and action proposals in v2's existing substantive review.

The old quality bundle and request schema stay byte-stable. These extra fields are
machine advice; neither a source observation nor an expert decision is rewritten.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path

from .core import canonical, digest
from .review import _document, _validate
from .substantive_review import build_substantive_request, parse_substantive_reply, review_schema

VERSION = "finding-proposals-v1"
SEVERITIES = ("critical", "economic", "operational", "recommendation", "check_adjacent")
_FIELDS = ("proposed_severity", "recommendation_text")


def proposal_policy():
    return {"version": VERSION, "bundle_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def validate_proposal_policy(value, *, compare_bundle=True):
    if (not isinstance(value, dict) or set(value) != {"version", "bundle_sha256"}
            or value["version"] != VERSION or not isinstance(value["bundle_sha256"], str)
            or len(value["bundle_sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in value["bundle_sha256"])
            or compare_bundle and value != proposal_policy()):
        raise ValueError("finding_proposals_changed_requires_consent")
    return True


def proposal_review_schema():
    schema = review_schema()
    row = schema["properties"]["reviews"]["items"]
    row["required"].extend(_FIELDS)
    row["properties"].update(
        proposed_severity={"type": "string", "enum": list(SEVERITIES)},
        recommendation_text={"type": "string", "minLength": 1, "maxLength": 4000, "pattern": "\\S"})
    return schema


def build_proposal_review_request(**kwargs):
    request = build_substantive_request(**kwargs)
    body = deepcopy(dict(request.body))
    body["output_config"]["format"]["schema"] = proposal_review_schema()
    body["system"] += (
        " Для каждого наблюдения отдельно предложи важность proposed_severity: critical — критическое, "
        "economic — экономическое, operational — эксплуатационное, recommendation — рекомендательное, "
        "check_adjacent — проверить по смежным. Это предложение модели, не решение эксперта. "
        "В recommendation_text укажи конкретное действие по проверке или исправлению именно этого вопроса. "
        "Не выдумывай новые размеры, номиналы, марки, нормы или требования. Если данных недостаточно, "
        "укажи, какие данные и где нужно проверить; не объявляй неопределённость нарушением. "
        "Сохрани исходное наблюдение и его источники; дополнительные поля не меняют экспертный вердикт.")
    if len(canonical(body).encode()) > 900_000:
        raise ValueError("finding_proposals_context_too_large")
    return replace(request, body=body,
        idempotency_scope=f"{kwargs['run_id']}:{VERSION}:{digest(body)}")


def parse_proposal_review_reply(text, *, inputs, sources, attached_image_ids, rejected=None):
    document = _document(text)
    schema = proposal_review_schema()
    envelope = deepcopy(schema)
    envelope["properties"]["reviews"]["items"] = {}
    _validate(document, envelope)
    stripped, positions = [], []
    for ordinal, row in enumerate(document["reviews"]):
        try:
            _validate(row, schema["properties"]["reviews"]["items"])
        except (ValueError, TypeError, KeyError) as error:
            if rejected is None:
                raise
            rejected.append({"reply_ordinal": ordinal, "reason": str(error), "record": deepcopy(row)})
            continue
        stripped.append({key: value for key, value in row.items() if key not in _FIELDS})
        positions.append(ordinal)
    source_refusals = []
    accepted = parse_substantive_reply(canonical({"reviews": stripped}), inputs=inputs,
        sources=sources, attached_image_ids=attached_image_ids,
        rejected=source_refusals if rejected is not None else None)
    if rejected is not None:
        for refusal in source_refusals:
            ordinal = positions[refusal["reply_ordinal"]]
            rejected.append({**refusal, "reply_ordinal": ordinal,
                "record": deepcopy(document["reviews"][ordinal])})
    refused_positions = {row["reply_ordinal"] for row in source_refusals}
    accepted_positions = [position for index, position in enumerate(positions) if index not in refused_positions]
    return [dict(row, **{field: document["reviews"][position][field] for field in _FIELDS}, proposal_policy=VERSION)
        for row, position in zip(accepted, accepted_positions, strict=True)]
