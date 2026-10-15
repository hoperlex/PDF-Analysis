"""Pure W57a retrieval-set and catalogue candidate assembly.

The caller owns map approval, query-vector provenance, snapshot/embedding
qualification, expected artifact digests and custody. This module joins the
already read evidence and emits candidate bytes only; it performs no DB write.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from auditmanager.norms.retrieval.artifact import (
    ArtifactRefused,
    CanonicalBlob,
    SetIdentity,
    build_retrieval_set,
)
from auditmanager.norms.retrieval.catalogue import build_catalogue
from auditmanager.norms.retrieval.evidence_bridge import (
    EvidenceBridgeRefused,
    ReviewedDesignation,
    project_snapshot_evidence,
)
from auditmanager.norms.retrieval.ranking import (
    MAX_CANDIDATE_WINDOWS,
    PromptSelection,
    RankingRefused,
    RetrievalItem,
    RetrievalWindow,
    TargetSpan,
    select_prompt_part,
)
from auditmanager.norms.retrieval.source_reader import SnapshotEvidence
from auditmanager.norms.retrieval.window_reader import WindowEvidence


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class CandidateRefused(ValueError):
    """The supplied source, map, query items or windows do not form one candidate."""


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    retrieval_set: CanonicalBlob
    catalogue: CanonicalBlob
    selection: PromptSelection
    embedding_set_sha256: str


def _mapped_and_items(map_bytes: bytes) -> tuple[tuple[str, ...], tuple[str, ...]]:
    # The evidence bridge has already checked canonical bytes, map SHA and
    # snapshot identity. Only fields needed by this assembly are projected.
    mapping = json.loads(map_bytes)
    mapped = tuple(mapping["mapped_document_ids"])
    items = mapping.get("items")
    if (
        not isinstance(items, list)
        or not items
        or any(not isinstance(item, dict) for item in items)
    ):
        raise CandidateRefused("reviewed map has no valid items")
    ids = tuple(item.get("id") for item in items)
    if any(not isinstance(item_id, str) or not item_id for item_id in ids):
        raise CandidateRefused("reviewed map has invalid item ids")
    if len(set(ids)) != len(ids):
        raise CandidateRefused("reviewed map has duplicate item ids")
    return mapped, ids


def _windows_for_map(
    windows: WindowEvidence,
    identity: SetIdentity,
    mapped_ids: tuple[str, ...],
) -> tuple[RetrievalWindow, ...]:
    if not isinstance(windows, WindowEvidence):
        raise CandidateRefused("window evidence is required")
    if (
        windows.snapshot_id != identity.snapshot_id
        or windows.embedding_build != identity.embedding_build
    ):
        raise CandidateRefused("window snapshot or embedding build differs from map")
    if (
        not isinstance(windows.embedding_set_sha256, str)
        or _SHA256.fullmatch(windows.embedding_set_sha256) is None
    ):
        raise CandidateRefused("invalid embedding set digest")
    if (
        type(windows.build_chunk_count) is not int
        or windows.build_chunk_count < 1
        or type(windows.build_window_count) is not int
        or windows.build_window_count < windows.build_chunk_count
    ):
        raise CandidateRefused("invalid embedding build counts")
    rows = windows.windows
    if not isinstance(rows, tuple) or not 1 <= len(rows) <= MAX_CANDIDATE_WINDOWS:
        raise CandidateRefused("mapped windows are empty or exceed the cap")
    if len(rows) > windows.build_window_count:
        raise CandidateRefused("mapped windows exceed build window count")
    allowed = set(mapped_ids)
    seen: set[tuple[str, int, int]] = set()
    documents: set[str] = set()
    for row in rows:
        if not isinstance(row, RetrievalWindow) or row.document_id not in allowed:
            raise CandidateRefused("window belongs to an unmapped document")
        if (
            type(row.chunk_ordinal) is not int
            or row.chunk_ordinal < 0
            or type(row.window_ordinal) is not int
            or row.window_ordinal < 0
        ):
            raise CandidateRefused("invalid mapped window ordinal")
        key = (row.document_id, row.chunk_ordinal, row.window_ordinal)
        if key in seen:
            raise CandidateRefused("duplicate mapped window key")
        seen.add(key)
        documents.add(row.document_id)
    if documents != allowed:
        raise CandidateRefused("mapped documents lack windows")
    return rows


def assemble_retrieval_candidate(
    *,
    evidence: SnapshotEvidence,
    windows: WindowEvidence,
    identity: SetIdentity,
    map_bytes: bytes,
    reviewed_designations: tuple[ReviewedDesignation, ...],
    items: tuple[RetrievalItem, ...],
) -> RetrievalCandidate:
    """Join exact source/window identities into candidate set and catalogue bytes.

    The window reader must have received this map's reviewed content key; its
    returned DTO does not repeat that field. Query-vector digests and the
    reviewed target choices must be checked by the caller against the map.
    """
    try:
        source = project_snapshot_evidence(
            evidence, identity=identity, map_bytes=map_bytes,
            reviewed_designations=reviewed_designations,
        )
        mapped_ids, item_ids = _mapped_and_items(map_bytes)
        selected_windows = _windows_for_map(windows, identity, mapped_ids)
        if (
            not isinstance(items, tuple)
            or any(not isinstance(item, RetrievalItem) for item in items)
            or tuple(item.item_id for item in items) != item_ids
        ):
            raise CandidateRefused("query items differ from reviewed map ids")
        if any(
            not isinstance(item.targets, tuple)
            or any(not isinstance(span, TargetSpan) for span in item.targets)
            for item in items
        ):
            raise CandidateRefused("query target spans are invalid")
        if set(span.document_id for item in items for span in item.targets) != set(mapped_ids):
            raise CandidateRefused("query target documents differ from reviewed map")
        selection = select_prompt_part(
            items,
            tuple(row.paragraph for row in source.source_paragraphs),
            selected_windows,
        )
        retrieval_set = build_retrieval_set(
            identity=identity, map_bytes=map_bytes,
            snapshot=source.snapshot, selection=selection,
            paragraphs=source.source_paragraphs,
        )
        catalogue = build_catalogue(
            snapshot=source.snapshot, documents=evidence.catalogue_documents,
        )
    except (ArtifactRefused, EvidenceBridgeRefused, RankingRefused) as exc:
        raise CandidateRefused(str(exc)) from exc
    return RetrievalCandidate(
        retrieval_set=retrieval_set,
        catalogue=catalogue,
        selection=selection,
        embedding_set_sha256=windows.embedding_set_sha256,
    )


__all__ = ["CandidateRefused", "RetrievalCandidate", "assemble_retrieval_candidate"]
