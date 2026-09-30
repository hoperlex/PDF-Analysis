"""PostgreSQL persistence for one immutable normative-corpus snapshot.

This is deliberately not a generic repository. It owns exactly four semantics: content-key
idempotency, immutable snapshot/document/paragraph insertion, replace-only chunk profiles and
count verification. Transaction lifetime belongs to the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import NormDocumentId, NormParagraphId, NormsSnapshotId

from .corpus_source import CorpusProjection, ProjectedCorpusDocument
from .segmentation import SEGMENTATION_PROFILE_VERSION

_INSERT_SNAPSHOT = text(
    """
    INSERT INTO norms_snapshot (
        norms_snapshot_id, content_key, base_content_key, content_digest,
        drawn_from, drawn_to, undated_documents, document_count, repair_count,
        segmentation_profile
    ) VALUES (
        :norms_snapshot_id, :content_key, :base_content_key, :content_digest,
        :drawn_from, :drawn_to, :undated_documents, :document_count, :repair_count,
        :segmentation_profile
    )
    ON CONFLICT (content_key) DO NOTHING
    RETURNING norms_snapshot_id
    """
)

_SELECT_SNAPSHOT = text(
    """
    SELECT norms_snapshot_id, content_key, base_content_key, content_digest,
           drawn_from, drawn_to, undated_documents, document_count, repair_count,
           segmentation_profile
    FROM norms_snapshot
    WHERE content_key = :content_key
    """
)

_INSERT_DOCUMENT = text(
    """
    INSERT INTO norm_document (
        norm_document_id, norms_snapshot_id, source_document_ref, slug, title,
        doc_type, drawn_on,
        source_attribution, pdf_page_count, block_count, page_heading_count,
        recognised_characters, paragraph_count
    ) VALUES (
        :norm_document_id, :norms_snapshot_id, :source_document_ref, :slug, :title,
        :doc_type, :drawn_on,
        :source_attribution, :pdf_page_count, :block_count, :page_heading_count,
        :recognised_characters, :paragraph_count
    )
    RETURNING norm_document_pk
    """
)

_INSERT_PARAGRAPH = text(
    """
    INSERT INTO norm_paragraph (
        norm_paragraph_id, norms_snapshot_id, norm_document_pk, ordinal,
        page_label, block_ref,
        char_offset, char_length, kind, clause_number, text
    ) VALUES (
        :norm_paragraph_id, :norms_snapshot_id, :norm_document_pk, :ordinal,
        :page_label, :block_ref,
        :char_offset, :char_length, :kind, :clause_number, :text
    )
    """
)

_INSERT_CHUNK = text(
    """
    INSERT INTO norm_chunk (
        norms_snapshot_id, norm_document_pk, chunking_profile, ordinal,
        page_first, page_last, char_offset, char_length,
        paragraph_ordinal_first, paragraph_ordinal_last, paragraph_count,
        clause_numbers, contains_clause, text, content_sha256
    ) VALUES (
        :norms_snapshot_id, :norm_document_pk, :chunking_profile, :ordinal,
        :page_first, :page_last, :char_offset, :char_length,
        :paragraph_ordinal_first, :paragraph_ordinal_last, :paragraph_count,
        :clause_numbers, :contains_clause, :text, :content_sha256
    )
    """
)

_INSERT_CHUNK_BUILD = text(
    """
    INSERT INTO norm_chunk_build (
        norms_snapshot_id, chunking_profile, target_characters, chunk_count
    ) VALUES (
        :norms_snapshot_id, :chunking_profile, :target_characters, :chunk_count
    )
    """
)

_COUNTS = text(
    """
    SELECT
        (SELECT count(*) FROM norm_document
          WHERE norms_snapshot_id = :norms_snapshot_id) AS documents,
        (SELECT count(*) FROM norm_paragraph
          WHERE norms_snapshot_id = :norms_snapshot_id) AS paragraphs,
        (SELECT count(*) FROM norm_chunk
          WHERE norms_snapshot_id = :norms_snapshot_id
            AND chunking_profile = :chunking_profile) AS chunks,
        (SELECT chunk_count FROM norm_chunk_build
          WHERE norms_snapshot_id = :norms_snapshot_id
            AND chunking_profile = :chunking_profile) AS recorded_chunks
    """
)


class NormsProjectionConflict(RuntimeError):
    """Stored rows and the deterministic source claim incompatible facts."""


@dataclass(frozen=True, slots=True)
class StoredCorpusCounts:
    documents: int
    paragraphs: int
    chunks: int


def _as_date(value: str | None) -> date | None:
    return None if value is None else date.fromisoformat(value)


def _batches(rows: list[dict[str, object]], size: int = 1000):
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


class NormsRepository:
    """The transaction-local write/read boundary for persisted corpus projections."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def ensure_snapshot(
        self, projection: CorpusProjection
    ) -> tuple[NormsSnapshotId, bool]:
        snapshot = projection.snapshot
        candidate = NormsSnapshotId.new()
        parameters = {
            "norms_snapshot_id": str(candidate),
            "content_key": snapshot.content_key,
            "base_content_key": projection.base_content_key,
            "content_digest": snapshot.content_digest,
            "drawn_from": _as_date(snapshot.drawn_from),
            "drawn_to": _as_date(snapshot.drawn_to),
            "undated_documents": snapshot.undated_documents,
            "document_count": snapshot.document_count,
            "repair_count": projection.repair_count,
            "segmentation_profile": SEGMENTATION_PROFILE_VERSION,
        }
        inserted = self._session.execute(_INSERT_SNAPSHOT, parameters).scalar_one_or_none()
        if inserted is not None:
            return NormsSnapshotId.parse(str(inserted)), True

        row = (
            self._session.execute(
                _SELECT_SNAPSHOT, {"content_key": snapshot.content_key}
            )
            .mappings()
            .one()
        )
        expected = {
            key: value
            for key, value in parameters.items()
            if key != "norms_snapshot_id"
        }
        mismatches = [
            f"{key}: stored={row[key]!r}, source={value!r}"
            for key, value in expected.items()
            if row[key] != value
        ]
        if mismatches:
            raise NormsProjectionConflict(
                f"content key {snapshot.content_key!r} already exists with conflicting "
                "metadata: " + "; ".join(mismatches)
            )
        return NormsSnapshotId.parse(str(row["norms_snapshot_id"])), False

    def insert_document(
        self,
        snapshot_id: NormsSnapshotId,
        projected: ProjectedCorpusDocument,
        chunking_profile: str,
    ) -> int:
        metadata = projected.metadata
        report = projected.report
        if len(projected.paragraphs) != report.substantive:
            raise NormsProjectionConflict(
                f"{metadata.slug}: report says {report.substantive} paragraphs, "
                f"projection carries {len(projected.paragraphs)}"
            )
        document_id = NormDocumentId.new()
        document_pk = int(
            self._session.execute(
                _INSERT_DOCUMENT,
                {
                    "norms_snapshot_id": str(snapshot_id),
                    "norm_document_id": str(document_id),
                    "source_document_ref": metadata.source_document_ref,
                    "slug": metadata.slug,
                    "title": metadata.title,
                    "doc_type": metadata.doc_type,
                    "drawn_on": _as_date(report.drawn_on),
                    "source_attribution": report.attribution.value,
                    "pdf_page_count": metadata.pdf_page_count,
                    "block_count": metadata.block_count,
                    "page_heading_count": report.page_headings,
                    "recognised_characters": report.recognised_characters,
                    "paragraph_count": len(projected.paragraphs),
                },
            ).scalar_one()
        )

        paragraph_rows = [
            {
                "norms_snapshot_id": str(snapshot_id),
                "norm_paragraph_id": str(NormParagraphId.new()),
                "norm_document_pk": document_pk,
                "ordinal": paragraph.ordinal,
                "page_label": paragraph.page_label,
                "block_ref": paragraph.block_id,
                "char_offset": paragraph.char_offset,
                "char_length": paragraph.char_length,
                "kind": paragraph.kind.value,
                "clause_number": paragraph.clause_number,
                "text": paragraph.text,
            }
            for paragraph in projected.paragraphs
        ]
        for batch in _batches(paragraph_rows):
            self._session.execute(_INSERT_PARAGRAPH, batch)

        chunk_rows: list[dict[str, object]] = []
        next_paragraph = 0
        for chunk in projected.chunks:
            first = next_paragraph
            last = first + chunk.paragraph_count - 1
            chunk_rows.append(
                {
                    "norms_snapshot_id": str(snapshot_id),
                    "norm_document_pk": document_pk,
                    "chunking_profile": chunking_profile,
                    "ordinal": chunk.ordinal,
                    "page_first": chunk.page_first,
                    "page_last": chunk.page_last,
                    "char_offset": chunk.char_offset,
                    "char_length": chunk.char_length,
                    "paragraph_ordinal_first": first,
                    "paragraph_ordinal_last": last,
                    "paragraph_count": chunk.paragraph_count,
                    "clause_numbers": list(chunk.clause_numbers),
                    "contains_clause": chunk.contains_clause,
                    "text": chunk.text,
                    "content_sha256": chunk.content_sha256,
                }
            )
            next_paragraph = last + 1
        if next_paragraph != len(projected.paragraphs):
            raise NormsProjectionConflict(
                f"{metadata.slug}: chunks cover {next_paragraph} paragraphs, "
                f"projection carries {len(projected.paragraphs)}"
            )
        for batch in _batches(chunk_rows):
            self._session.execute(_INSERT_CHUNK, batch)
        return len(chunk_rows)

    def finish_chunk_build(
        self,
        snapshot_id: NormsSnapshotId,
        chunking_profile: str,
        target_characters: int,
        chunk_count: int,
    ) -> None:
        self._session.execute(
            _INSERT_CHUNK_BUILD,
            {
                "norms_snapshot_id": str(snapshot_id),
                "chunking_profile": chunking_profile,
                "target_characters": target_characters,
                "chunk_count": chunk_count,
            },
        )

    def counts(
        self, snapshot_id: NormsSnapshotId, chunking_profile: str
    ) -> StoredCorpusCounts:
        row = (
            self._session.execute(
                _COUNTS,
                {
                    "norms_snapshot_id": str(snapshot_id),
                    "chunking_profile": chunking_profile,
                },
            )
            .mappings()
            .one()
        )
        if row["recorded_chunks"] is None:
            raise NormsProjectionConflict(
                f"snapshot {snapshot_id} has no complete build for {chunking_profile!r}"
            )
        if int(row["recorded_chunks"]) != int(row["chunks"]):
            raise NormsProjectionConflict(
                f"snapshot {snapshot_id} profile {chunking_profile!r} records "
                f"{row['recorded_chunks']} chunks but stores {row['chunks']}"
            )
        return StoredCorpusCounts(
            documents=int(row["documents"]),
            paragraphs=int(row["paragraphs"]),
            chunks=int(row["chunks"]),
        )
