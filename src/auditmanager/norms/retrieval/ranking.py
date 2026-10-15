"""Deterministic W57a prompt-part selection over reviewed target spans.

Inputs are already resolved `ndoc_`/`npar_` rows and complete float32 vectors.
This module never discovers legal editions, reads the corpus or publishes a set.
The later builder must pin a reviewed map and qualified snapshot before using it.
"""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from array import array
from dataclasses import dataclass

from auditmanager.norms.embedding.profile import DIMENSIONS, UNIT_NORM_TOLERANCE


BUILDER_VERSION = "norm-ranking-prep-v1"
PROMPT_CHAR_CAP = 22_000
MAX_CANDIDATE_WINDOWS = 50_000


class RankingRefused(ValueError):
    """The set could not be selected reproducibly from qualified inputs."""


@dataclass(frozen=True, slots=True)
class TargetSpan:
    document_id: str
    ordinal_first: int
    ordinal_last: int


@dataclass(frozen=True, slots=True)
class RetrievalItem:
    item_id: str
    query_vector: array
    targets: tuple[TargetSpan, ...]


@dataclass(frozen=True, slots=True)
class RetrievalParagraph:
    document_id: str
    paragraph_id: str
    designation: str
    title: str
    ordinal: int
    clause_number: str | None
    page_label: str | None
    text: str
    reliable: bool = True


@dataclass(frozen=True, slots=True)
class RetrievalWindow:
    document_id: str
    chunk_ordinal: int
    window_ordinal: int
    paragraph_ordinal_first: int
    paragraph_ordinal_last: int
    vector: array


@dataclass(frozen=True, slots=True)
class PromptRow:
    item_id: str
    label: str
    document_id: str
    paragraph_id: str
    designation: str
    title: str
    ordinal: int
    clause_number: str | None
    page_label: str | None
    text: str
    text_sha256: str


@dataclass(frozen=True, slots=True)
class PromptSelection:
    rows: tuple[PromptRow, ...]
    prompt_part: str
    windows_per_item: int
    inside_target_windows_dropped: bool


def _require_vector(vector: array) -> None:
    if not isinstance(vector, array) or vector.typecode != "f" or len(vector) != DIMENSIONS:
        raise RankingRefused("vector must be a complete float32 array")
    if not all(math.isfinite(value) for value in vector):
        raise RankingRefused("vector contains a non-finite value")
    norm = math.sqrt(math.fsum(value * value for value in vector))
    if abs(norm - 1.0) > UNIT_NORM_TOLERANCE:
        raise RankingRefused("vector is not unit normalized")


def exact_inner_product(left: array, right: array) -> float:
    """Score stored float32 operands in a stable order with `math.fsum`."""
    _require_vector(left)
    _require_vector(right)
    return math.fsum(a * b for a, b in zip(left, right, strict=True))


def _rows_for_item(
    item: RetrievalItem,
    selected_windows: tuple[RetrievalWindow, ...],
    paragraphs: dict[tuple[str, int], RetrievalParagraph],
) -> tuple[RetrievalParagraph, ...]:
    keys: set[tuple[str, int]] = set()
    for span in item.targets:
        keys.update(
            (span.document_id, ordinal)
            for ordinal in range(span.ordinal_first, span.ordinal_last + 1)
        )
    for window in selected_windows:
        keys.update(
            (window.document_id, ordinal)
            for ordinal in range(window.paragraph_ordinal_first, window.paragraph_ordinal_last + 1)
        )
    rows: list[RetrievalParagraph] = []
    for key in keys:
        paragraph = paragraphs.get(key)
        if paragraph is None or not paragraph.reliable:
            raise RankingRefused("target or window includes a missing or unreliable paragraph")
        if unicodedata.normalize("NFC", paragraph.text) != paragraph.text:
            raise RankingRefused("target or window includes a non-NFC paragraph")
        rows.append(paragraph)
    return tuple(sorted(rows, key=lambda row: (row.designation, row.ordinal, row.document_id)))


def _inside_targets(window: RetrievalWindow, targets: tuple[TargetSpan, ...]) -> bool:
    covered = {
        ordinal
        for target in targets
        if target.document_id == window.document_id
        for ordinal in range(target.ordinal_first, target.ordinal_last + 1)
    }
    return all(
        ordinal in covered
        for ordinal in range(window.paragraph_ordinal_first, window.paragraph_ordinal_last + 1)
    )


def _render(rows: tuple[PromptRow, ...]) -> str:
    payload = {
        "builder_version": BUILDER_VERSION,
        "paragraphs": [
            {
                "item_id": row.item_id,
                "label": row.label,
                "norm_document_id": row.document_id,
                "norm_paragraph_id": row.paragraph_id,
                "designation": row.designation,
                "title": row.title,
                "ordinal": row.ordinal,
                "clause_number": row.clause_number,
                "page_label": row.page_label,
                "text": row.text,
                "text_sha256": row.text_sha256,
            }
            for row in rows
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def select_prompt_part(
    items: tuple[RetrievalItem, ...],
    paragraphs: tuple[RetrievalParagraph, ...],
    windows: tuple[RetrievalWindow, ...],
    *,
    char_cap: int = PROMPT_CHAR_CAP,
) -> PromptSelection:
    """Select target rows and top windows, then apply W57a's reduction order.

    The returned string is the exact serialized prompt part whose length is
    checked. No paragraph is truncated, and labels are assigned after the
    final selection so they are dense and stable.
    """
    if not items or char_cap <= 0:
        raise RankingRefused("items and positive character cap are required")
    if len({item.item_id for item in items}) != len(items):
        raise RankingRefused("duplicate retrieval item id")
    by_key = {(p.document_id, p.ordinal): p for p in paragraphs}
    if len(by_key) != len(paragraphs) or len(
        {p.paragraph_id for p in paragraphs}
    ) != len(paragraphs):
        raise RankingRefused("duplicate paragraph identity")
    mapped_documents: set[str] = set()
    for item in items:
        _require_vector(item.query_vector)
        if not item.targets:
            raise RankingRefused("item has no reviewed target span")
        for span in item.targets:
            if span.ordinal_first < 0 or span.ordinal_last < span.ordinal_first:
                raise RankingRefused("invalid target span")
            mapped_documents.add(span.document_id)
    mapped_windows = tuple(window for window in windows if window.document_id in mapped_documents)
    if len(mapped_windows) > MAX_CANDIDATE_WINDOWS:
        raise RankingRefused("too many candidate windows")
    identities = {(w.document_id, w.chunk_ordinal, w.window_ordinal) for w in mapped_windows}
    if len(identities) != len(mapped_windows):
        raise RankingRefused("duplicate window identity")
    for window in mapped_windows:
        _require_vector(window.vector)
        if (
            window.chunk_ordinal < 0
            or window.window_ordinal < 0
            or window.paragraph_ordinal_first < 0
            or window.paragraph_ordinal_last < window.paragraph_ordinal_first
        ):
            raise RankingRefused("invalid window span or ordinal")

    ranked: dict[str, tuple[RetrievalWindow, ...]] = {}
    for item in items:
        target_docs = {span.document_id for span in item.targets}
        scores = (
            (
                -math.fsum(a * b for a, b in zip(item.query_vector, window.vector, strict=True)),
                window.document_id,
                window.chunk_ordinal,
                window.window_ordinal,
                window,
            )
            for window in mapped_windows
            if window.document_id in target_docs
        )
        ranked[item.item_id] = tuple(entry[4] for entry in sorted(scores)[:3])

    def materialize(limit: int, drop_inside: bool) -> PromptSelection:
        selected: list[tuple[str, tuple[RetrievalParagraph, ...]]] = []
        for item in items:
            choices = ranked[item.item_id]
            if drop_inside:
                choices = tuple(w for w in choices if not _inside_targets(w, item.targets))
            selected.append((item.item_id, _rows_for_item(item, choices[:limit], by_key)))
        rows: list[PromptRow] = []
        for item_id, source_rows in selected:
            for paragraph in source_rows:
                rows.append(
                    PromptRow(
                        item_id=item_id,
                        label=f"N{len(rows) + 1}",
                        document_id=paragraph.document_id,
                        paragraph_id=paragraph.paragraph_id,
                        designation=paragraph.designation,
                        title=paragraph.title,
                        ordinal=paragraph.ordinal,
                        clause_number=paragraph.clause_number,
                        page_label=paragraph.page_label,
                        text=paragraph.text,
                        text_sha256=hashlib.sha256(paragraph.text.encode("utf-8")).hexdigest(),
                    )
                )
        frozen_rows = tuple(rows)
        return PromptSelection(frozen_rows, _render(frozen_rows), limit, drop_inside)

    first = materialize(3, False)
    if len(first.prompt_part) <= char_cap:
        return first
    for limit in (3, 2, 1, 0):
        candidate = materialize(limit, True)
        if len(candidate.prompt_part) <= char_cap:
            return candidate
    raise RankingRefused("prompt part remains above character cap with target rows alone")
