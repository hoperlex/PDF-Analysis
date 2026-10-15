"""Pure W57a clause, table and explicit-range target resolution.

The caller supplies every canonical paragraph of one selected document in
ordinal order. This module does not select an edition, assert legal status or
decide whether a norm applies to an object.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from auditmanager.norms.retrieval.ranking import TargetSpan


_CLAUSE = re.compile(r"^(\d+(?:\.\d+)*)(?:\*\*|__)?\.?[ \t\u00a0]+\S")
_TABLE = re.compile(r"^таблица[ \t\u00a0]+(\d+(?:\.\d+)*)\b", re.IGNORECASE)


class TargetRefused(ValueError):
    """A proposed map target has no unique, reliable canonical resolution."""


@dataclass(frozen=True, slots=True)
class TargetParagraph:
    document_id: str
    paragraph_id: str
    ordinal: int
    text: str
    kind: str  # body | heading | table_row, as produced by segmentation
    clause_number: str | None
    reliable: bool = True


@dataclass(frozen=True, slots=True)
class ResolvedTarget:
    document_id: str
    spans: tuple[TargetSpan, ...]
    paragraph_ids: tuple[str, ...]
    excluded_unreliable: tuple[str, ...]


def _visible_start(text: str) -> str:
    """Strip leading markdown emphasis and heading markers for anchor matching."""
    visible = text.lstrip()
    while True:
        before = visible
        visible = visible.lstrip("#").lstrip()
        if visible.startswith(("**", "__")):
            visible = visible[2:].lstrip()
        if visible == before:
            return visible


def _clause_number(paragraph: TargetParagraph) -> str | None:
    if paragraph.clause_number is not None:
        return paragraph.clause_number
    if paragraph.kind == "table_row":
        return None
    match = _CLAUSE.match(_visible_start(paragraph.text))
    return match.group(1) if match else None


def _validated(paragraphs: tuple[TargetParagraph, ...]) -> tuple[TargetParagraph, ...]:
    if not paragraphs:
        raise TargetRefused("document has no canonical paragraphs")
    doc_id = paragraphs[0].document_id
    if any(p.document_id != doc_id for p in paragraphs):
        raise TargetRefused("paragraphs cross document identities")
    if [p.ordinal for p in paragraphs] != list(range(len(paragraphs))):
        raise TargetRefused("document paragraph ordinals are not complete and ordered")
    if len({p.paragraph_id for p in paragraphs}) != len(paragraphs):
        raise TargetRefused("duplicate paragraph identity")
    if any(p.kind not in {"body", "heading", "table_row"} for p in paragraphs):
        raise TargetRefused("unknown canonical paragraph kind")
    return paragraphs


def _result(paragraphs: tuple[TargetParagraph, ...], start: int, end: int) -> ResolvedTarget:
    if not paragraphs[start].reliable:
        raise TargetRefused("anchor paragraph is unreliable")
    selected = paragraphs[start:end]
    reliable = tuple(p for p in selected if p.reliable)
    if not reliable:
        raise TargetRefused("target contains no reliable paragraph")
    spans: list[TargetSpan] = []
    first = last = reliable[0].ordinal
    for paragraph in reliable[1:]:
        if paragraph.ordinal != last + 1:
            spans.append(TargetSpan(paragraphs[0].document_id, first, last))
            first = paragraph.ordinal
        last = paragraph.ordinal
    spans.append(TargetSpan(paragraphs[0].document_id, first, last))
    return ResolvedTarget(
        document_id=paragraphs[0].document_id,
        spans=tuple(spans),
        paragraph_ids=tuple(p.paragraph_id for p in reliable),
        excluded_unreliable=tuple(p.paragraph_id for p in selected if not p.reliable),
    )


def resolve_clause(paragraphs: tuple[TargetParagraph, ...], clause: str) -> ResolvedTarget:
    """Exact numbered clause plus descendants, stopping at the next boundary."""
    ordered = _validated(paragraphs)
    if not re.fullmatch(r"\d+(?:\.\d+)*", clause):
        raise TargetRefused("malformed numeric clause anchor; use explicit range")
    anchors = [index for index, p in enumerate(ordered) if _clause_number(p) == clause]
    if len(anchors) != 1:
        raise TargetRefused("clause anchor is absent or ambiguous")
    start = anchors[0]
    end = len(ordered)
    for index in range(start + 1, len(ordered)):
        paragraph = ordered[index]
        number = _clause_number(paragraph)
        if paragraph.kind == "heading" or (
            number is not None and number != clause and not number.startswith(clause + ".")
        ):
            end = index
            break
    return _result(ordered, start, end)


def resolve_table(paragraphs: tuple[TargetParagraph, ...], caption: str) -> ResolvedTarget:
    """Caption through rows and notes, stopping at a new heading or clause."""
    ordered = _validated(paragraphs)
    requested = _TABLE.match(_visible_start(caption))
    if requested is None:
        raise TargetRefused("malformed table caption anchor")
    number = requested.group(1)
    anchors = [
        index
        for index, paragraph in enumerate(ordered)
        if (found := _TABLE.match(_visible_start(paragraph.text))) is not None
        and found.group(1) == number
    ]
    if len(anchors) != 1:
        raise TargetRefused("table caption is absent or ambiguous")
    start = anchors[0]
    end = len(ordered)
    for index in range(start + 1, len(ordered)):
        paragraph = ordered[index]
        if paragraph.kind == "heading" or _clause_number(paragraph) is not None:
            end = index
            break
    return _result(ordered, start, end)


def resolve_range(
    paragraphs: tuple[TargetParagraph, ...], first_paragraph_id: str, last_paragraph_id: str
) -> ResolvedTarget:
    """Resolve owner-picked canonical `npar_` endpoints without inference."""
    ordered = _validated(paragraphs)
    by_id = {paragraph.paragraph_id: index for index, paragraph in enumerate(ordered)}
    first, last = by_id.get(first_paragraph_id), by_id.get(last_paragraph_id)
    if first is None or last is None or first > last:
        raise TargetRefused("explicit paragraph range is absent or reversed")
    return _result(ordered, first, last + 1)
