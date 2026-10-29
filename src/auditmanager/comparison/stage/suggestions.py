"""Conservative, nonbinding П→Р document-pair suggestions.

The database supplies confirmed classifications and designations from one
project. A suggestion is useful only when its normalized section/designation
is unique on both sides; ambiguity stays for the expert's workbench. No result
from this module writes a pair or changes an expert's act.
"""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

__all__ = ["StageDocument", "StageSuggestion", "suggest_stage_pairs"]


@dataclass(frozen=True, slots=True)
class StageDocument:
    document_uid: str
    stage: Literal["P", "R"]
    section_code: str
    designation: str
    hint_source: Literal["confirmed", "title"] = "title"


@dataclass(frozen=True, slots=True)
class StageSuggestion:
    left_document_uid: str
    right_document_uid: str
    reason: str
    score: float


def _key(document: StageDocument) -> tuple[str, str] | None:
    section = unicodedata.normalize("NFKC", document.section_code).strip().upper()
    designation = " ".join(
        unicodedata.normalize("NFKC", document.designation).casefold().split()
    )
    if not section or not designation:
        return None
    return section, designation


def suggest_stage_pairs(
    documents: tuple[StageDocument, ...], *, bound_document_uids: frozenset[str]
) -> tuple[StageSuggestion, ...]:
    """Suggest only unique exact keys among currently unbound documents.

    A caller reads one project under its normal visibility policy. A unique
    designation is a hint, never proof of the right association: the expert
    must confirm the two opaque document identities through the keyed command.
    """
    left: dict[tuple[str, str], list[StageDocument]] = defaultdict(list)
    right: dict[tuple[str, str], list[StageDocument]] = defaultdict(list)
    for document in documents:
        if document.document_uid in bound_document_uids:
            continue
        key = _key(document)
        if key is None:
            continue
        (left if document.stage == "P" else right)[key].append(document)
    return tuple(
        StageSuggestion(
            left_document_uid=left[key][0].document_uid,
            right_document_uid=right[key][0].document_uid,
            reason=(
                "section_designation_exact"
                if left[key][0].hint_source == right[key][0].hint_source == "confirmed"
                else "section_title_hint_exact"
            ),
            score=(
                1.0 if left[key][0].hint_source == right[key][0].hint_source == "confirmed"
                else 0.75
            ),
        )
        for key in sorted(left.keys() & right.keys())
        if len(left[key]) == len(right[key]) == 1
    )
