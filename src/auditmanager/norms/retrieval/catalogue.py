"""Deterministic W57a catalogue from snapshot document rows supplied by a caller.

`designation_tokens` are copied from the stored SQL-generated column. This
module deliberately does not derive or repair them from a slug.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditmanager.norms.retrieval.artifact import (
    ArtifactRefused,
    CanonicalBlob,
    SnapshotBinding,
    _nfc,
    _validated_snapshot,
    canonical_blob,
)


CATALOGUE_VERSION = "norm-catalogue-prep-v1"


@dataclass(frozen=True, slots=True)
class CatalogueDocument:
    document_id: str
    slug: str
    designation_tokens: tuple[str, ...]
    title: str
    doc_type: str


def build_catalogue(
    *, snapshot: SnapshotBinding, documents: tuple[CatalogueDocument, ...]
) -> CanonicalBlob:
    """Encode all caller-supplied snapshot documents in stable identity order.

    `snapshot.document_count` is an independent totality assertion supplied by
    the DB reader. The pure builder cannot prove the database query was complete.
    """
    _validated_snapshot(snapshot)
    if len(documents) != snapshot.document_count:
        raise ArtifactRefused("catalogue document count differs from snapshot")
    ids: set[str] = set()
    slugs: set[str] = set()
    rows: list[dict[str, object]] = []
    for document in documents:
        for field in ("document_id", "slug", "title", "doc_type"):
            _nfc(getattr(document, field), field)
        if not document.document_id.startswith("ndoc_"):
            raise ArtifactRefused("invalid catalogue document id")
        if document.document_id in ids or document.slug in slugs:
            raise ArtifactRefused("duplicate catalogue document id or slug")
        ids.add(document.document_id)
        slugs.add(document.slug)
        if not isinstance(document.designation_tokens, tuple) or not document.designation_tokens:
            raise ArtifactRefused("missing stored designation tokens")
        for token in document.designation_tokens:
            _nfc(token, "designation token")
        rows.append(
            {
                "norm_document_id": document.document_id,
                "slug": document.slug,
                "designation_tokens": document.designation_tokens,
                "title": document.title,
                "doc_type": document.doc_type,
            }
        )
    return canonical_blob(
        {
            "catalogue_version": CATALOGUE_VERSION,
            "norms_snapshot_id": snapshot.snapshot_id,
            "content_key": snapshot.content_key,
            "snapshot_content_digest": snapshot.content_digest,
            "document_count": snapshot.document_count,
            "documents": sorted(rows, key=lambda row: row["norm_document_id"]),
        }
    )
