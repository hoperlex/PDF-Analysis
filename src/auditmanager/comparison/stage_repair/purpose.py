"""Stored title normalisation and deterministic sheet-purpose precheck."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from .types import PurposeCheck

_TYPES = (
    ("single_line", re.compile(r"\bоднолинейн\w*\b")),
    ("plan", re.compile(r"\bплан\w*\b")),
    ("scheme", re.compile(r"\bсхем\w*\b")),
    ("node", re.compile(r"\bуз(?:ел|лы|ла|лов)\b")),
    ("explication", re.compile(r"\bэкспликаци\w*\b")),
    ("section", re.compile(r"\bразрез\w*\b")),
    ("facade", re.compile(r"\bфасад\w*\b")),
)
_STOP = frozenset({"план", "схема", "схемы", "узел", "узлы", "разрез", "фасад",
                   "лист", "страница", "на", "в", "по", "и", "с", "для", "из", "к", "от"})


def normalize_title(title: str) -> str:
    value = unicodedata.normalize("NFKC", title).casefold().replace("ё", "е")
    return " ".join(re.sub(r"[^\w]+", " ", value, flags=re.UNICODE).replace("_", " ").split())


def purpose_family(title: str) -> str | None:
    plain = normalize_title(title)
    return next((kind for kind, pattern in _TYPES if pattern.search(plain)), None)


def subject_tokens(title: str) -> frozenset[str]:
    return frozenset(token for token in normalize_title(title).split()
                     if len(token) > 1 and token not in _STOP)


def specific_title(title: str) -> bool:
    plain = normalize_title(title)
    return (len(plain.split()) >= 2
            and not re.fullmatch(r"(?:лист|страница)\s*\d+", plain)
            and plain not in {"общие данные", "общие указания", "общий вид", "содержание проекта"})


def precheck_purpose(left_titles: Sequence[str], right_titles: Sequence[str]) -> PurposeCheck:
    left = tuple(normalize_title(value) for value in left_titles if normalize_title(value))
    right = tuple(normalize_title(value) for value in right_titles if normalize_title(value))
    if not left or not right:
        return PurposeCheck("PAIR_OK", "low", "purpose_title_unavailable_no_conflict_detected")
    left_types = {purpose_family(value) for value in left} - {None}
    right_types = {purpose_family(value) for value in right} - {None}
    if left_types & right_types:
        return PurposeCheck("PAIR_OK", "high", "shared_sheet_purpose_family")
    a = set(" ".join(left).split())
    b = set(" ".join(right).split())
    if a and b and len(a & b) / min(len(a), len(b)) >= 0.35:
        return PurposeCheck("PAIR_OK", "medium", "sheet_purpose_title_overlap")
    return PurposeCheck("PAIR_REVIEW_REQUIRED", "high", "sheet_purpose_conflict")
