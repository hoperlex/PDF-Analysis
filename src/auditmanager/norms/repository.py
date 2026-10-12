"""PostgreSQL persistence for one immutable normative-corpus snapshot.

This is deliberately not a generic repository. It owns exactly these semantics: content-key
idempotency, immutable snapshot/document/paragraph insertion (freshly minted ids, or the ids an
import carries), replace-only chunk profiles built from the projection or from the stored
canonical paragraphs, the `F-4` refusal of ``characters-v1`` over unreliable text, the
canonical row digest read back in canonical order, and count verification. Transaction
lifetime belongs to the caller.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import (
    NormDocumentId,
    NormParagraphId,
    NormsSnapshotId,
)

from .chunking import (
    CHUNKING_PROFILE_VERSION,
    RELIABLE_CHUNKING_PROFILE_VERSION,
    ChunkingRefused,
    chunk_paragraphs,
    parse_chunking_profile,
    verify_coverage,
)
from .corpus_source import CorpusProjection, ProjectedCorpusDocument
from .model import Chunk, Paragraph, ParagraphKind, TextReliability
from .snapshot import (
    BASE_SEGMENTATION_PROFILE,
    SEGMENTATION_TERM,
    DocumentRow,
    ParagraphRow,
    RowDigest,
    SnapshotRow,
    SnapshotRows,
)

_INSERT_SNAPSHOT = text(
    """
    INSERT INTO norms_snapshot (
        norms_snapshot_id, content_key, base_content_key, content_digest,
        drawn_from, drawn_to, undated_documents, document_count, repair_count,
        unreliable_count, segmentation_profile
    ) VALUES (
        :norms_snapshot_id, :content_key, :base_content_key, :content_digest,
        :drawn_from, :drawn_to, :undated_documents, :document_count, :repair_count,
        :unreliable_count, :segmentation_profile
    )
    ON CONFLICT DO NOTHING
    RETURNING norms_snapshot_id
    """
)

_SNAPSHOT_COLUMNS = """
    norms_snapshot_id, content_key, base_content_key, content_digest,
    drawn_from, drawn_to, undated_documents, document_count, repair_count,
    unreliable_count, segmentation_profile
"""

_SELECT_SNAPSHOT = text(
    f"SELECT {_SNAPSHOT_COLUMNS} FROM norms_snapshot WHERE content_key = :content_key"
)

_SELECT_SNAPSHOT_BY_ID = text(
    f"SELECT {_SNAPSHOT_COLUMNS} FROM norms_snapshot "
    "WHERE norms_snapshot_id = :norms_snapshot_id"
)

_SELECT_DOCUMENTS = text(
    """
    SELECT norm_document_id, source_document_ref, slug, title, doc_type, drawn_on,
           source_attribution, pdf_page_count, block_count, page_heading_count,
           recognised_characters, paragraph_count
    FROM norm_document
    WHERE norms_snapshot_id = :norms_snapshot_id
    ORDER BY norm_document_id COLLATE "C"
    """
)

_SELECT_PARAGRAPH_ROWS = text(
    """
    SELECT p.norm_paragraph_id, d.norm_document_id, p.ordinal, p.page_label, p.block_ref,
           p.char_offset, p.char_length, p.kind, p.clause_number, p.text, p.text_reliability
    FROM norm_paragraph p
    JOIN norm_document d USING (norms_snapshot_id, norm_document_pk)
    WHERE p.norms_snapshot_id = :norms_snapshot_id
    ORDER BY d.norm_document_id COLLATE "C", p.ordinal
    """
)

_SELECT_STORED_PARAGRAPHS = text(
    """
    SELECT d.norm_document_pk, d.slug, p.ordinal, p.page_label, p.block_ref, p.char_offset,
           p.char_length, p.kind, p.clause_number, p.text, p.text_reliability
    FROM norm_paragraph p
    JOIN norm_document d USING (norms_snapshot_id, norm_document_pk)
    WHERE p.norms_snapshot_id = :norms_snapshot_id
    ORDER BY d.norm_document_pk, p.ordinal
    """
)

_SELECT_DOCUMENT_PKS = text(
    "SELECT norm_document_pk FROM norm_document WHERE norms_snapshot_id = :norms_snapshot_id "
    "ORDER BY norm_document_pk"
)

_SELECT_UNRELIABLE_COUNT = text(
    "SELECT unreliable_count FROM norms_snapshot WHERE norms_snapshot_id = :norms_snapshot_id"
)

_SELECT_BUILD = text(
    "SELECT target_characters, chunk_count FROM norm_chunk_build "
    "WHERE norms_snapshot_id = :norms_snapshot_id AND chunking_profile = :chunking_profile"
)

_EXISTING_DOCUMENT_IDS = text(
    "SELECT norm_document_id, norms_snapshot_id FROM norm_document "
    "WHERE norm_document_id IN :ids"
).bindparams(bindparam("ids", expanding=True))

_EXISTING_PARAGRAPH_IDS = text(
    "SELECT norm_paragraph_id, norms_snapshot_id FROM norm_paragraph "
    "WHERE norm_paragraph_id IN :ids"
).bindparams(bindparam("ids", expanding=True))

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
        char_offset, char_length, kind, clause_number, text, text_reliability
    ) VALUES (
        :norm_paragraph_id, :norms_snapshot_id, :norm_document_pk, :ordinal,
        :page_label, :block_ref,
        :char_offset, :char_length, :kind, :clause_number, :text, :text_reliability
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


class SnapshotImportConflict(NormsProjectionConflict):
    """An import names a key or an id the database already holds with other rows.

    Exact replay — the same snapshot id, the same key and the same row digest — is not a
    conflict; it is a no-op. The same key under another id, the same id under another key,
    a child id that belongs to another snapshot, or equal ids with other rows are refused.
    """


class SnapshotRowsInvalid(ValueError):
    """Rows offered for import are not one well-formed snapshot; nothing was written."""


@dataclass(frozen=True, slots=True)
class StoredCorpusCounts:
    documents: int
    paragraphs: int
    chunks: int


def _as_date(value: str | None) -> date | None:
    return None if value is None else date.fromisoformat(value)


def _iso(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def _snapshot_row(row) -> SnapshotRow:
    return SnapshotRow(
        norms_snapshot_id=str(row["norms_snapshot_id"]),
        content_key=str(row["content_key"]),
        base_content_key=str(row["base_content_key"]),
        content_digest=str(row["content_digest"]),
        drawn_from=_iso(row["drawn_from"]),
        drawn_to=_iso(row["drawn_to"]),
        undated_documents=int(row["undated_documents"]),
        document_count=int(row["document_count"]),
        repair_count=int(row["repair_count"]),
        unreliable_count=int(row["unreliable_count"]),
        segmentation_profile=str(row["segmentation_profile"]),
    )


def _document_row(row) -> DocumentRow:
    return DocumentRow(
        norm_document_id=str(row["norm_document_id"]),
        source_document_ref=str(row["source_document_ref"]),
        slug=str(row["slug"]),
        title=str(row["title"]),
        doc_type=str(row["doc_type"]),
        drawn_on=_iso(row["drawn_on"]),
        source_attribution=str(row["source_attribution"]),
        pdf_page_count=int(row["pdf_page_count"]),
        block_count=int(row["block_count"]),
        page_heading_count=int(row["page_heading_count"]),
        recognised_characters=int(row["recognised_characters"]),
        paragraph_count=int(row["paragraph_count"]),
    )


def _paragraph_row(row) -> ParagraphRow:
    return ParagraphRow(
        norm_paragraph_id=str(row["norm_paragraph_id"]),
        norm_document_id=str(row["norm_document_id"]),
        ordinal=int(row["ordinal"]),
        page_label=int(row["page_label"]),
        block_ref=str(row["block_ref"]),
        char_offset=int(row["char_offset"]),
        char_length=int(row["char_length"]),
        kind=str(row["kind"]),
        clause_number=None if row["clause_number"] is None else str(row["clause_number"]),
        text=str(row["text"]),
        text_reliability=str(row["text_reliability"]),
    )


def _id_batches(ids: list[str], size: int = 10_000) -> Iterator[list[str]]:
    for start in range(0, len(ids), size):
        yield ids[start : start + size]


_RELIABILITY_VALUES = frozenset(value.value for value in TextReliability)
_KIND_VALUES = frozenset(value.value for value in ParagraphKind)


def validate_snapshot_rows(rows: SnapshotRows) -> None:
    """Refuse rows that are not one well-formed snapshot, before anything is read or written.

    Checks the shapes the database cannot see as a whole: every id parses as its contract
    type and is unique; slugs and source references are unique; the document count, each
    document's paragraph count and its ordinals ``0..n-1`` agree with the rows; every
    paragraph names a document in the set; vocabularies are the stored ones; an unreliable
    paragraph implies ``unreliable_count > 0``; and the key carries the segmentation profile
    exactly as `D-126` mints it. The repaired-key equivalence is ``ck_norms_snapshot_raw_key``'s.
    """
    snapshot = rows.snapshot
    try:
        NormsSnapshotId.parse(snapshot.norms_snapshot_id)
        for document in rows.documents:
            NormDocumentId.parse(document.norm_document_id)
        for paragraph in rows.paragraphs:
            NormParagraphId.parse(paragraph.norm_paragraph_id)
    except ValueError as exc:
        raise SnapshotRowsInvalid(str(exc)) from exc

    profile = snapshot.segmentation_profile
    term = f"{SEGMENTATION_TERM}{profile}"
    for name in ("content_key", "base_content_key"):
        key = getattr(snapshot, name)
        if profile == BASE_SEGMENTATION_PROFILE:
            if SEGMENTATION_TERM in key:
                raise SnapshotRowsInvalid(f"{name} {key!r} names a profile; {profile} adds none")
        elif not key.endswith(term) or key.count(SEGMENTATION_TERM) != 1:
            raise SnapshotRowsInvalid(f"{name} {key!r} does not end with {term!r} (D-126)")

    if snapshot.document_count != len(rows.documents):
        raise SnapshotRowsInvalid(
            f"snapshot claims {snapshot.document_count} documents, rows carry "
            f"{len(rows.documents)}"
        )
    for attribute in ("norm_document_id", "slug", "source_document_ref"):
        values = [getattr(document, attribute) for document in rows.documents]
        if len(set(values)) != len(values):
            raise SnapshotRowsInvalid(f"two documents share one {attribute}")
    paragraph_ids = [paragraph.norm_paragraph_id for paragraph in rows.paragraphs]
    if len(set(paragraph_ids)) != len(paragraph_ids):
        raise SnapshotRowsInvalid("two paragraphs share one norm_paragraph_id")

    ordinals: dict[str, list[int]] = defaultdict(list)
    unreliable = 0
    for paragraph in rows.paragraphs:
        ordinals[paragraph.norm_document_id].append(paragraph.ordinal)
        if paragraph.text_reliability not in _RELIABILITY_VALUES:
            raise SnapshotRowsInvalid(
                f"{paragraph.norm_paragraph_id}: text_reliability "
                f"{paragraph.text_reliability!r}"
            )
        if paragraph.kind not in _KIND_VALUES:
            raise SnapshotRowsInvalid(f"{paragraph.norm_paragraph_id}: kind {paragraph.kind!r}")
        unreliable += paragraph.text_reliability == TextReliability.UNRELIABLE.value
    documents = {document.norm_document_id: document for document in rows.documents}
    strangers = sorted(set(ordinals) - set(documents))
    if strangers:
        raise SnapshotRowsInvalid(f"paragraphs name absent document {strangers[0]}")
    for document_id, document in documents.items():
        if sorted(ordinals.get(document_id, ())) != list(range(document.paragraph_count)):
            raise SnapshotRowsInvalid(
                f"{document_id}: paragraph ordinals are not 0..{document.paragraph_count - 1}"
            )
    if unreliable and snapshot.unreliable_count == 0:
        raise SnapshotRowsInvalid(
            f"{unreliable} unreliable paragraph(s) under a snapshot with unreliable_count = 0"
        )


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
            "unreliable_count": projection.unreliable_count,
            "segmentation_profile": projection.segmentation_profile,
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
                "text_reliability": paragraph.text_reliability.value,
            }
            for paragraph in projected.paragraphs
        ]
        for batch in _batches(paragraph_rows):
            self._session.execute(_INSERT_PARAGRAPH, batch)

        return self._insert_chunks(
            snapshot_id,
            document_pk,
            chunking_profile,
            projected.paragraphs,
            projected.chunks,
            label=metadata.slug,
        )

    def _insert_chunks(
        self,
        snapshot_id: NormsSnapshotId,
        document_pk: int,
        chunking_profile: str,
        paragraphs: Sequence[Paragraph],
        chunks: Sequence[Chunk],
        *,
        label: str,
    ) -> int:
        version, _target = parse_chunking_profile(chunking_profile)
        try:
            verify_coverage(paragraphs, chunks, version=version)
        except ChunkingRefused as exc:
            raise NormsProjectionConflict(f"{label}: {exc}") from exc
        chunk_rows = [
            {
                "norms_snapshot_id": str(snapshot_id),
                "norm_document_pk": document_pk,
                "chunking_profile": chunking_profile,
                "ordinal": chunk.ordinal,
                "page_first": chunk.page_first,
                "page_last": chunk.page_last,
                "char_offset": chunk.char_offset,
                "char_length": chunk.char_length,
                "paragraph_ordinal_first": chunk.paragraph_ordinal_first,
                "paragraph_ordinal_last": chunk.paragraph_ordinal_last,
                "paragraph_count": chunk.paragraph_count,
                "clause_numbers": list(chunk.clause_numbers),
                "contains_clause": chunk.contains_clause,
                "text": chunk.text,
                "content_sha256": chunk.content_sha256,
            }
            for chunk in chunks
        ]
        for batch in _batches(chunk_rows):
            self._session.execute(_INSERT_CHUNK, batch)
        return len(chunk_rows)

    def admit_chunking_profile(
        self, snapshot_id: NormsSnapshotId, chunking_profile: str
    ) -> None:
        """Refuse ``characters-v1`` over a stored snapshot with ``unreliable_count > 0`` (`F-4`).

        The database boundary's own check, so a build that bypasses the projection — a
        rebuild or an import — is refused on the stored count, not on what a caller believed.
        """
        version, _target = parse_chunking_profile(chunking_profile)
        unreliable = self._session.execute(
            _SELECT_UNRELIABLE_COUNT, {"norms_snapshot_id": str(snapshot_id)}
        ).scalar_one_or_none()
        if unreliable is None:
            raise NormsProjectionConflict(f"snapshot {snapshot_id} is not stored")
        if version == CHUNKING_PROFILE_VERSION and int(unreliable) > 0:
            raise ChunkingRefused(
                f"{chunking_profile} over snapshot {snapshot_id} is refused: it carries "
                f"{int(unreliable)} unreliable block(s); build "
                f"{RELIABLE_CHUNKING_PROFILE_VERSION} instead"
            )

    def has_chunk_build(self, snapshot_id: NormsSnapshotId, chunking_profile: str) -> bool:
        return (
            self._session.execute(
                _SELECT_BUILD,
                {"norms_snapshot_id": str(snapshot_id), "chunking_profile": chunking_profile},
            ).first()
            is not None
        )

    def build_chunks_from_stored(
        self, snapshot_id: NormsSnapshotId, content_key: str, chunking_profile: str
    ) -> int:
        """Build one complete chunk profile from the stored canonical paragraphs.

        The rebuild path `NORM_CORPUS_PERSISTENCE.md` names, and the importer's: the chunks
        are a deterministic function of the canonical rows, so they are derived on arrival
        rather than carried. Refused for ``characters-v1`` over unreliable text; the build
        row is written last, with the count.
        """
        self.admit_chunking_profile(snapshot_id, chunking_profile)
        version, target = parse_chunking_profile(chunking_profile)
        by_document: dict[int, list[Paragraph]] = defaultdict(list)
        slugs: dict[int, str] = {}
        rows = (
            self._session.execute(
                _SELECT_STORED_PARAGRAPHS, {"norms_snapshot_id": str(snapshot_id)}
            )
            .mappings()
        )
        for row in rows:
            document_pk = int(row["norm_document_pk"])
            slugs[document_pk] = str(row["slug"])
            by_document[document_pk].append(
                Paragraph(
                    document_slug=str(row["slug"]),
                    page_label=int(row["page_label"]),
                    block_id=str(row["block_ref"]),
                    ordinal=int(row["ordinal"]),
                    char_offset=int(row["char_offset"]),
                    char_length=int(row["char_length"]),
                    kind=ParagraphKind(row["kind"]),
                    clause_number=row["clause_number"],
                    text=str(row["text"]),
                    text_reliability=TextReliability(row["text_reliability"]),
                )
            )
        chunks = 0
        for document_pk in self._session.execute(
            _SELECT_DOCUMENT_PKS, {"norms_snapshot_id": str(snapshot_id)}
        ).scalars():
            paragraphs = by_document.get(int(document_pk), [])
            built = chunk_paragraphs(paragraphs, content_key, target, version=version)
            chunks += self._insert_chunks(
                snapshot_id,
                int(document_pk),
                chunking_profile,
                paragraphs,
                built,
                label=slugs.get(int(document_pk), str(document_pk)),
            )
        self.finish_chunk_build(snapshot_id, chunking_profile, target, chunks)
        return chunks

    # --- rows with ids: read back, digest, import ----------------------------------------

    def snapshot_row(self, snapshot_id: NormsSnapshotId) -> SnapshotRow | None:
        row = (
            self._session.execute(
                _SELECT_SNAPSHOT_BY_ID, {"norms_snapshot_id": str(snapshot_id)}
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else _snapshot_row(row)

    def snapshot_row_by_key(self, content_key: str) -> SnapshotRow | None:
        row = (
            self._session.execute(_SELECT_SNAPSHOT, {"content_key": content_key})
            .mappings()
            .one_or_none()
        )
        return None if row is None else _snapshot_row(row)

    def read_snapshot_rows(self, snapshot_id: NormsSnapshotId) -> SnapshotRows:
        """Every canonical row of one stored snapshot, with its ids, in canonical order."""
        snapshot = self.snapshot_row(snapshot_id)
        if snapshot is None:
            raise NormsProjectionConflict(f"snapshot {snapshot_id} is not stored")
        parameters = {"norms_snapshot_id": str(snapshot_id)}
        documents = tuple(
            _document_row(row)
            for row in self._session.execute(_SELECT_DOCUMENTS, parameters).mappings()
        )
        paragraphs = tuple(
            _paragraph_row(row)
            for row in self._session.execute(_SELECT_PARAGRAPH_ROWS, parameters).mappings()
        )
        return SnapshotRows(snapshot=snapshot, documents=documents, paragraphs=paragraphs)

    def stored_row_digest(self, snapshot_id: NormsSnapshotId) -> str:
        """The row digest recomputed from the database, streamed in canonical order.

        Rows are hashed as they arrive; :class:`RowDigest` refuses any out of order, so the
        digest equals :func:`snapshot.row_digest` over :meth:`read_snapshot_rows` without
        holding the snapshot's text in memory.
        """
        snapshot = self.snapshot_row(snapshot_id)
        if snapshot is None:
            raise NormsProjectionConflict(f"snapshot {snapshot_id} is not stored")
        digest = RowDigest()
        digest.snapshot(snapshot)
        parameters = {"norms_snapshot_id": str(snapshot_id)}
        for row in self._session.execute(_SELECT_DOCUMENTS, parameters).mappings():
            digest.document(_document_row(row))
        result = self._session.execute(
            _SELECT_PARAGRAPH_ROWS,
            parameters,
            execution_options={"stream_results": True, "yield_per": 2000},
        )
        for row in result.mappings():
            digest.paragraph(_paragraph_row(row))
        return digest.hexdigest()

    def foreign_child_ids(self, rows: SnapshotRows) -> list[str]:
        """Document or paragraph ids of ``rows`` already stored under another snapshot."""
        own = rows.snapshot.norms_snapshot_id
        clashes: list[str] = []
        for statement, ids in (
            (_EXISTING_DOCUMENT_IDS, [row.norm_document_id for row in rows.documents]),
            (_EXISTING_PARAGRAPH_IDS, [row.norm_paragraph_id for row in rows.paragraphs]),
        ):
            for batch in _id_batches(ids):
                for identity, holder in self._session.execute(statement, {"ids": batch}):
                    if str(holder) != own:
                        clashes.append(f"{identity} (held by {holder})")
        return clashes

    def insert_snapshot_rows(self, rows: SnapshotRows) -> None:
        """Insert one snapshot's canonical rows **with the ids they carry**.

        Private keys are the database's: each document's ``norm_document_pk`` is minted here
        and paragraphs are remapped to it by the document's opaque id. The caller has
        validated the rows and checked for replay and conflicts; an id or key taken since is
        refused by the unique constraints and reported as a conflict.
        """
        snapshot = rows.snapshot
        inserted = self._session.execute(
            _INSERT_SNAPSHOT,
            {
                "norms_snapshot_id": snapshot.norms_snapshot_id,
                "content_key": snapshot.content_key,
                "base_content_key": snapshot.base_content_key,
                "content_digest": snapshot.content_digest,
                "drawn_from": _as_date(snapshot.drawn_from),
                "drawn_to": _as_date(snapshot.drawn_to),
                "undated_documents": snapshot.undated_documents,
                "document_count": snapshot.document_count,
                "repair_count": snapshot.repair_count,
                "unreliable_count": snapshot.unreliable_count,
                "segmentation_profile": snapshot.segmentation_profile,
            },
        ).scalar_one_or_none()
        if inserted is None:
            raise SnapshotImportConflict(
                f"snapshot {snapshot.norms_snapshot_id} or key {snapshot.content_key!r} was "
                "stored concurrently"
            )
        pk_by_id: dict[str, int] = {}
        for document in sorted(rows.documents, key=lambda row: row.norm_document_id):
            pk_by_id[document.norm_document_id] = int(
                self._session.execute(
                    _INSERT_DOCUMENT,
                    {
                        "norm_document_id": document.norm_document_id,
                        "norms_snapshot_id": snapshot.norms_snapshot_id,
                        "source_document_ref": document.source_document_ref,
                        "slug": document.slug,
                        "title": document.title,
                        "doc_type": document.doc_type,
                        "drawn_on": _as_date(document.drawn_on),
                        "source_attribution": document.source_attribution,
                        "pdf_page_count": document.pdf_page_count,
                        "block_count": document.block_count,
                        "page_heading_count": document.page_heading_count,
                        "recognised_characters": document.recognised_characters,
                        "paragraph_count": document.paragraph_count,
                    },
                ).scalar_one()
            )
        paragraph_rows = [
            {
                "norm_paragraph_id": paragraph.norm_paragraph_id,
                "norms_snapshot_id": snapshot.norms_snapshot_id,
                "norm_document_pk": pk_by_id[paragraph.norm_document_id],
                "ordinal": paragraph.ordinal,
                "page_label": paragraph.page_label,
                "block_ref": paragraph.block_ref,
                "char_offset": paragraph.char_offset,
                "char_length": paragraph.char_length,
                "kind": paragraph.kind,
                "clause_number": paragraph.clause_number,
                "text": paragraph.text,
                "text_reliability": paragraph.text_reliability,
            }
            for paragraph in sorted(
                rows.paragraphs, key=lambda row: (row.norm_document_id, row.ordinal)
            )
        ]
        for batch in _batches(paragraph_rows):
            self._session.execute(_INSERT_PARAGRAPH, batch)

    def finish_chunk_build(
        self,
        snapshot_id: NormsSnapshotId,
        chunking_profile: str,
        target_characters: int,
        chunk_count: int,
    ) -> None:
        self.admit_chunking_profile(snapshot_id, chunking_profile)
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
