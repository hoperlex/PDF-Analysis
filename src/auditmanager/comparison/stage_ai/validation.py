"""Small strict JSON validators; rejected answers produce no partial result."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any


class StageAiValidationError(ValueError):
    """A whole source group/chunk response is invalid or insufficiently grounded."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    answer = {}
    for key, value in pairs:
        if key in answer:
            raise StageAiValidationError("duplicate_json_key")
        answer[key] = value
    return answer


def parse_document(value: str | bytes | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, bytes):
        if len(value) > 2_000_000:
            raise StageAiValidationError("response_too_large")
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            raise StageAiValidationError("response_not_utf8") from None
    if isinstance(value, str):
        if len(value) > 2_000_000:
            raise StageAiValidationError("response_too_large")
        try:
            value = json.loads(value, object_pairs_hook=_unique_pairs,
                               parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()))
        except (ValueError, TypeError):
            raise StageAiValidationError("response_not_strict_json") from None
    if not isinstance(value, Mapping):
        raise StageAiValidationError("response_not_object")
    return dict(value)


def exact_object(value: Any, keys: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise StageAiValidationError(code)
    return value


def strings(value: Any, *, nonempty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 800 or any(not isinstance(item, str) for item in value):
        raise StageAiValidationError("identity_array_invalid")
    if len(value) != len(set(value)) or (nonempty and not value):
        raise StageAiValidationError("identity_array_duplicate_or_empty")
    return tuple(value)


def nonempty_text(value: Any, maximum: int = 320) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise StageAiValidationError("claim_text_invalid")
    return value.strip()


_NUMBER = re.compile(r"(?<!\w)[+±-]?\d+(?:[.,]\d+)*(?!\w)")
_IDENTIFIER = re.compile(r"\b(?=[\w./-]*\d)(?=[\w./-]*[A-Za-zА-Яа-яЁё])[\w]+(?:[./-][\w]+)*\b")
_AUDIT = ("соответствует норм", "нарушение норм", "не соответствует норм", "требованиям гост", "критичность", "стоимость работ")


def supported_claim(claim: str, source: str) -> bool:
    source_low = source.casefold().replace("ё", "е")
    source_numbers = set(_NUMBER.findall(source.replace("−", "-")))
    if any(token not in source_numbers for token in _NUMBER.findall(claim.replace("−", "-"))):
        return False
    source_identifiers = {token.casefold().replace("ё", "е") for token in _IDENTIFIER.findall(source)}
    if any(token.casefold().replace("ё", "е") not in source_identifiers for token in _IDENTIFIER.findall(claim)):
        return False
    return not any(phrase in claim.casefold() and phrase not in source_low for phrase in _AUDIT)


def require_group_id(value: str) -> None:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError("group_id_invalid")
