"""SELECT-only canonical evidence for a later W57a retrieval-set build.

The caller owns a consistent read transaction, reviewed map, qualification of
the embedding build and custody. This reader does not infer a legal designation
from a stored slug or turn a base corpus into a qualified normative source.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.norms.embedding.profile import require_snapshot_id
from auditmanager.norms.retrieval.catalogue import CatalogueDocument


_OPAQUE_DOCUMENT = re.compile(r"ndoc_[0-9A-HJKMNP-TV-Z]{26}\Z")
_OPAQUE_PARAGRAPH = re.compile(r"npar_[0-9A-HJKMNP-TV-Z]{26}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_KINDS = frozenset({"body", "heading", "table_row"})
_RELIABILITY = frozenset({"reliable", "unreliable"})

_SNAPSHOT = text("""
    SELECT norms_snapshot_id, content_key, content_digest, document_count,
           unreliable_count
    FROM norms_snapshot WHERE norms_snapshot_id = :snapshot_id
""")
_DOCUMENTS = text("""
    SELECT norm_document_id, slug, title, doc_type, designation_tokens,
           paragraph_count
    FROM norm_document WHERE norms_snapshot_id = :snapshot_id
    ORDER BY norm_document_id COLLATE "C"
""")
_PARAGRAPH_COUNTS = text("""
    SELECT count(*) AS paragraph_count,
           count(*) FILTER (WHERE text_reliability NOT IN ('reliable', 'unreliable'))
               AS unknown_reliability_count
    FROM norm_paragraph WHERE norms_snapshot_id = :snapshot_id
""")
_MAPPED_PARAGRAPHS = text("""
    SELECT d.norm_document_id, p.norm_paragraph_id, p.ordinal, p.page_label,
           p.kind, p.clause_number, p.text, p.text_reliability
    FROM norm_paragraph p
    JOIN norm_document d USING (norms_snapshot_id, norm_document_pk)
    WHERE p.norms_snapshot_id = :snapshot_id
      AND d.norm_document_id = ANY(CAST(:mapped_ids AS text[]))
    ORDER BY d.norm_document_id COLLATE "C", p.ordinal
""")


class SnapshotEvidenceRefused(ValueError):
    """Stored rows cannot be bound to the caller's exact snapshot expectation."""


@dataclass(frozen=True, slots=True)
class SnapshotFacts:
    snapshot_id: str
    content_key: str
    content_digest: str
    document_count: int
    unreliable_count: int  # W54 unrepaired blocks, not unreliable paragraphs.


@dataclass(frozen=True, slots=True)
class CanonicalParagraphEvidence:
    document_id: str
    paragraph_id: str
    ordinal: int
    page_label: int
    kind: str
    clause_number: str | None
    text: str
    text_reliability: str
    text_sha256: str


@dataclass(frozen=True, slots=True)
class SnapshotEvidence:
    snapshot: SnapshotFacts
    catalogue_documents: tuple[CatalogueDocument, ...]
    mapped_paragraphs: tuple[CanonicalParagraphEvidence, ...]


def _nfc(value: object, label: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value or unicodedata.normalize("NFC", value) != value:
        raise SnapshotEvidenceRefused(f"{label} must be nonempty NFC text")
    return value


def _integer(value: object, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise SnapshotEvidenceRefused(f"{label} must be an integer >= {minimum}")
    return value


def _opaque(value: object, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise SnapshotEvidenceRefused(f"invalid {label}")
    return value


def read_snapshot_evidence(
    session: Session,
    *,
    snapshot_id: str,
    expected_content_key: str,
    mapped_document_ids: tuple[str, ...],
) -> SnapshotEvidence:
    """Read raw rows under the caller's transaction; execute SELECTs only.

    All catalogue documents and the full paragraph stream for mapped documents
    are checked against independently stored counts. The returned reliability
    remains explicit; no unreliable text is silently promoted to reliable.
    """
    try:
        require_snapshot_id(snapshot_id)
    except (TypeError, ValueError) as exc:
        raise SnapshotEvidenceRefused("invalid snapshot id") from exc
    _nfc(expected_content_key, "expected content key")
    if (
        not isinstance(mapped_document_ids, tuple)
        or not mapped_document_ids
    ):
        raise SnapshotEvidenceRefused("mapped document ids must be a unique nonempty tuple")
    for document_id in mapped_document_ids:
        _opaque(document_id, _OPAQUE_DOCUMENT, "mapped document id")
    if len(set(mapped_document_ids)) != len(mapped_document_ids):
        raise SnapshotEvidenceRefused("mapped document ids must be a unique nonempty tuple")

    parameters = {"snapshot_id": snapshot_id}
    row = session.execute(_SNAPSHOT, parameters).mappings().one_or_none()
    if row is None or row["norms_snapshot_id"] != snapshot_id:
        raise SnapshotEvidenceRefused("expected snapshot is absent")
    if row["content_key"] != expected_content_key:
        raise SnapshotEvidenceRefused("snapshot content key differs from reviewed map")
    digest = row["content_digest"]
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        raise SnapshotEvidenceRefused("invalid snapshot content digest")
    snapshot = SnapshotFacts(
        snapshot_id=snapshot_id,
        content_key=expected_content_key,
        content_digest=digest,
        document_count=_integer(row["document_count"], "document count", minimum=1),
        unreliable_count=_integer(row["unreliable_count"], "unreliable count"),
    )

    documents: list[CatalogueDocument] = []
    paragraph_counts: dict[str, int] = {}
    slugs: set[str] = set()
    last_document_id: str | None = None
    for row in session.execute(_DOCUMENTS, parameters).mappings():
        document_id = _opaque(row["norm_document_id"], _OPAQUE_DOCUMENT, "document id")
        slug = _nfc(row["slug"], "document slug")
        title = _nfc(row["title"], "document title")
        doc_type = _nfc(row["doc_type"], "document type")
        tokens = row["designation_tokens"]
        if (
            document_id in paragraph_counts
            or slug in slugs
            or not isinstance(tokens, (tuple, list))
            or not tokens
        ):
            raise SnapshotEvidenceRefused("duplicate document or missing designation tokens")
        if last_document_id is not None and document_id <= last_document_id:
            raise SnapshotEvidenceRefused("catalogue documents are out of canonical order")
        last_document_id = document_id
        slugs.add(slug)
        paragraph_counts[document_id] = _integer(row["paragraph_count"], "document paragraph count")
        documents.append(
            CatalogueDocument(
                document_id=document_id,
                slug=slug,
                designation_tokens=tuple(_nfc(token, "designation token") for token in tokens),
                title=title,
                doc_type=doc_type,
            )
        )
    if len(documents) != snapshot.document_count:
        raise SnapshotEvidenceRefused("snapshot document count mismatch")
    if not set(mapped_document_ids) <= paragraph_counts.keys():
        raise SnapshotEvidenceRefused("mapped document is absent from snapshot")

    counts = session.execute(_PARAGRAPH_COUNTS, parameters).mappings().one()
    if (
        _integer(counts["paragraph_count"], "stored paragraph count")
        != sum(paragraph_counts.values())
        or _integer(counts["unknown_reliability_count"], "unknown reliability count")
    ):
        raise SnapshotEvidenceRefused("snapshot paragraph or reliability count mismatch")

    paragraphs: list[CanonicalParagraphEvidence] = []
    ordinals = {document_id: 0 for document_id in mapped_document_ids}
    paragraph_ids: set[str] = set()
    last_paragraph_key: tuple[str, int] | None = None
    for row in session.execute(
        _MAPPED_PARAGRAPHS,
        parameters | {"mapped_ids": list(mapped_document_ids)},
        execution_options={"stream_results": True, "yield_per": 2000},
    ).mappings():
        document_id = row["norm_document_id"]
        if document_id not in ordinals:
            raise SnapshotEvidenceRefused("foreign mapped paragraph")
        ordinal = _integer(row["ordinal"], "paragraph ordinal")
        paragraph_id = _opaque(row["norm_paragraph_id"], _OPAQUE_PARAGRAPH, "paragraph id")
        if ordinal != ordinals[document_id] or paragraph_id in paragraph_ids:
            raise SnapshotEvidenceRefused("mapped paragraph order or identity mismatch")
        key = (document_id, ordinal)
        if last_paragraph_key is not None and key <= last_paragraph_key:
            raise SnapshotEvidenceRefused("mapped paragraphs are out of canonical order")
        last_paragraph_key = key
        ordinals[document_id] += 1
        paragraph_ids.add(paragraph_id)
        kind = row["kind"]
        reliability = row["text_reliability"]
        if kind not in _KINDS or reliability not in _RELIABILITY:
            raise SnapshotEvidenceRefused("unknown paragraph kind or reliability")
        body = _nfc(row["text"], "paragraph text")
        paragraphs.append(
            CanonicalParagraphEvidence(
                document_id=document_id,
                paragraph_id=paragraph_id,
                ordinal=ordinal,
                page_label=_integer(row["page_label"], "page label", minimum=1),
                kind=kind,
                clause_number=_nfc(row["clause_number"], "clause number", optional=True),
                text=body,
                text_reliability=reliability,
                text_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
            )
        )
    if any(ordinals[document_id] != paragraph_counts[document_id] for document_id in mapped_document_ids):
        raise SnapshotEvidenceRefused("mapped document paragraphs are incomplete")
    if any(ordinals[document_id] == 0 for document_id in mapped_document_ids):
        raise SnapshotEvidenceRefused("mapped document has no paragraph text")
    return SnapshotEvidence(snapshot, tuple(documents), tuple(paragraphs))


__all__ = [
    "CanonicalParagraphEvidence",
    "SnapshotEvidence",
    "SnapshotEvidenceRefused",
    "SnapshotFacts",
    "read_snapshot_evidence",
]
