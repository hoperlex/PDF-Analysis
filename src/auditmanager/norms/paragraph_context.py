"""Read-only, identity-bound context for existing reliable corpus search hits.

Ranges refer to Unicode code points inside the stored paragraph, not PDF-page
offsets. Neighbor text provides context and never becomes a citation candidate.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import text

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import NormDocumentId, NormParagraphId, NormsSnapshotId

from .search import resolve_scope

VERSION = "norm-paragraph-context-v1"

_PRIMARY = text("""
    SELECT p.norm_paragraph_id, p.norm_document_pk, p.ordinal, p.page_label,
           p.block_ref, p.kind, p.clause_number, p.text_reliability,
           char_length(p.text) AS full_characters,
           strpos(p.text, :quote) AS quote_position,
           CASE WHEN char_length(p.text) <= :paragraph_characters THEN 0
                ELSE greatest(0, strpos(p.text, :quote) - 1 - 1000) END AS character_start,
           substring(p.text FROM ((CASE WHEN char_length(p.text) <= :paragraph_characters THEN 0
                                      ELSE greatest(0, strpos(p.text, :quote) - 1 - 1000) END) + 1)
                     FOR :paragraph_characters) AS context_text,
           d.source_attribution, d.title, d.drawn_on
      FROM norm_paragraph p
      JOIN norm_document d USING (norms_snapshot_id, norm_document_pk)
     WHERE p.norms_snapshot_id = :snapshot AND d.norm_document_id = :document
       AND p.norm_paragraph_id = :paragraph AND p.text_reliability = 'reliable'
""")
_NEIGHBORS = text("""
    SELECT p.norm_paragraph_id, p.ordinal, p.page_label, p.block_ref, p.kind,
           p.clause_number, p.text_reliability, char_length(p.text) AS full_characters,
           0 AS character_start, substring(p.text FROM 1 FOR :neighbor_characters) AS context_text
      FROM norm_paragraph p
     WHERE p.norms_snapshot_id = :snapshot AND p.norm_document_pk = :document_pk
       AND p.ordinal IN (
           (SELECT max(n.ordinal) FROM norm_paragraph n
             WHERE n.norms_snapshot_id = :snapshot AND n.norm_document_pk = :document_pk
               AND n.ordinal < :ordinal),
           (SELECT min(n.ordinal) FROM norm_paragraph n
             WHERE n.norms_snapshot_id = :snapshot AND n.norm_document_pk = :document_pk
               AND n.ordinal > :ordinal))
     ORDER BY p.ordinal
""")


def norm_paragraph_context_digest() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _piece(row) -> dict:
    value = str(row["context_text"])
    start, total = int(row["character_start"]), int(row["full_characters"])
    return {"paragraph_id": str(row["norm_paragraph_id"]), "ordinal": int(row["ordinal"]),
        "page_label": int(row["page_label"]), "block_ref": str(row["block_ref"]),
        "kind": str(row["kind"]), "clause_number": row["clause_number"],
        "text_reliability": str(row["text_reliability"]), "text": value,
        "paragraph_character_start": start, "paragraph_character_end": start + len(value),
        "full_paragraph_characters": total, "truncated": start > 0 or start + len(value) < total,
        "excerpt_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest()}


def read_norm_paragraph_context(session, *, snapshot_id: str, document_id: str,
        paragraph_id: str, quote: str, paragraph_characters: int = 6000,
        neighbor_characters: int = 1000) -> dict:
    """Only the immutable snapshot already qualified by ordinary corpus search."""
    snapshot = NormsSnapshotId.parse(snapshot_id).value
    document = NormDocumentId.parse(document_id).value
    paragraph = NormParagraphId.parse(paragraph_id).value
    if (not isinstance(quote, str) or not quote.strip() or len(quote) > 2000
            or type(paragraph_characters) is not int or not 2000 <= paragraph_characters <= 6000
            or type(neighbor_characters) is not int or not 1 <= neighbor_characters <= 1000):
        raise ValueError("norm_paragraph_context_input_invalid")
    resolve_scope(session, snapshot)
    row = session.execute(_PRIMARY, {"snapshot": snapshot, "document": document,
        "paragraph": paragraph, "quote": quote, "paragraph_characters": paragraph_characters}).mappings().one_or_none()
    if row is None:
        raise DomainError(ErrorCode.REQUIRED_NORM_UNAVAILABLE,
            reference_kind="norm_paragraph_context", reference_id=paragraph)
    neighbors = session.execute(_NEIGHBORS, {"snapshot": snapshot, "document_pk": row["norm_document_pk"],
        "ordinal": row["ordinal"], "neighbor_characters": neighbor_characters}).mappings().all()
    return {"version": VERSION, "snapshot_id": snapshot, "document_id": document,
        "paragraph_id": paragraph, "title": str(row["title"]),
        "drawn_on": None if row["drawn_on"] is None else row["drawn_on"].isoformat(),
        "source_attribution": str(row["source_attribution"]),
        "search_quote_literal_in_paragraph": int(row["quote_position"]) > 0,
        "search_quote_paragraph_character_start": int(row["quote_position"]) - 1 if int(row["quote_position"]) > 0 else None,
        "primary": _piece(row), "neighbors": [_piece(neighbor) for neighbor in neighbors],
        "edition_applicability_verified": False, "neighbor_citations_allowed": False}
