"""Pure projection of read snapshot rows into W57a retrieval inputs.

The caller owns the reviewed map and designation decisions, snapshot/build
qualification, ranking windows and custody. This projection proves only that
the supplied rows agree with those exact inputs; it does not qualify a corpus.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass

from auditmanager.norms.embedding.profile import require_snapshot_id
from auditmanager.norms.retrieval.artifact import (
    SET_BUILDER_VERSION,
    SetIdentity,
    SnapshotBinding,
    SourceParagraph,
    canonical_json_bytes,
)
from auditmanager.norms.retrieval.ranking import RetrievalParagraph
from auditmanager.norms.retrieval.source_reader import SnapshotEvidence
from auditmanager.norms.retrieval.targets import TargetParagraph


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_DOCUMENT = re.compile(r"ndoc_[0-9A-HJKMNP-TV-Z]{26}\Z")
_PARAGRAPH = re.compile(r"npar_[0-9A-HJKMNP-TV-Z]{26}\Z")
_KINDS = frozenset({"body", "heading", "table_row"})


class EvidenceBridgeRefused(ValueError):
    """Read evidence disagrees with the caller's exact reviewed inputs."""


@dataclass(frozen=True, slots=True)
class ReviewedDesignation:
    """A caller-reviewed label bound to the snapshot's stored document slug."""

    document_id: str
    slug: str
    designation: str


@dataclass(frozen=True, slots=True)
class RetrievalSourceInputs:
    snapshot: SnapshotBinding
    source_paragraphs: tuple[SourceParagraph, ...]
    target_paragraphs: tuple[TargetParagraph, ...]


def _nfc(value: object, label: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value or unicodedata.normalize("NFC", value) != value:
        raise EvidenceBridgeRefused(f"{label} must be nonempty NFC text")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise EvidenceBridgeRefused(f"{label} must be lowercase SHA-256")
    return value


def _opaque(value: object, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise EvidenceBridgeRefused(f"invalid {label}")
    return value


def _reviewed_map(identity: SetIdentity, map_bytes: bytes) -> tuple[str, ...]:
    _digest(identity.map_sha256, "reviewed map digest")
    if not isinstance(map_bytes, bytes) or len(map_bytes) > 10_000_000:
        raise EvidenceBridgeRefused("reviewed map must be bounded bytes")
    if hashlib.sha256(map_bytes).hexdigest() != identity.map_sha256:
        raise EvidenceBridgeRefused("reviewed map digest mismatch")
    try:
        mapping = json.loads(map_bytes.decode("utf-8"))
        canonical = canonical_json_bytes(mapping)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise EvidenceBridgeRefused("reviewed map is not canonical JSON") from exc
    if not isinstance(mapping, dict) or canonical != map_bytes:
        raise EvidenceBridgeRefused("reviewed map is not canonical JSON")
    if (
        mapping.get("norms_snapshot_id") != identity.snapshot_id
        or mapping.get("reviewed_content_key") != identity.reviewed_content_key
        or mapping.get("embedding_build") != identity.embedding_build
    ):
        raise EvidenceBridgeRefused("reviewed map identity mismatch")
    mapped = mapping.get("mapped_document_ids")
    if not isinstance(mapped, list) or not mapped:
        raise EvidenceBridgeRefused("reviewed map has no mapped documents")
    for document_id in mapped:
        _opaque(document_id, _DOCUMENT, "mapped document id")
    if len(set(mapped)) != len(mapped):
        raise EvidenceBridgeRefused("duplicate mapped document id")
    return tuple(mapped)


def project_snapshot_evidence(
    evidence: SnapshotEvidence,
    *,
    identity: SetIdentity,
    map_bytes: bytes,
    reviewed_designations: tuple[ReviewedDesignation, ...],
) -> RetrievalSourceInputs:
    """Bind complete mapped paragraphs to exact map and reviewed labels.

    `SourceParagraph` feeds the pure set builder; its embedded
    `RetrievalParagraph` feeds ranking. `TargetParagraph` feeds pure target
    resolution. Prompt selection needs separately read windows and vectors.
    A matching `embedding_build` string is an identity check, not proof that
    the snapshot has a complete qualified build.
    """
    if not isinstance(evidence, SnapshotEvidence) or not isinstance(identity, SetIdentity):
        raise EvidenceBridgeRefused("snapshot evidence and set identity are required")
    try:
        require_snapshot_id(identity.snapshot_id)
    except (TypeError, ValueError) as exc:
        raise EvidenceBridgeRefused("invalid set snapshot id") from exc
    _nfc(identity.reviewed_content_key, "reviewed content key")
    _nfc(identity.embedding_build, "embedding build")
    if identity.builder_version != SET_BUILDER_VERSION:
        raise EvidenceBridgeRefused("unknown set builder version")
    mapped_ids = _reviewed_map(identity, map_bytes)
    snapshot = evidence.snapshot
    if (
        snapshot.snapshot_id != identity.snapshot_id
        or snapshot.content_key != identity.reviewed_content_key
    ):
        raise EvidenceBridgeRefused("snapshot differs from reviewed map")
    _digest(snapshot.content_digest, "snapshot content digest")
    if type(snapshot.document_count) is not int or snapshot.document_count <= 0:
        raise EvidenceBridgeRefused("invalid snapshot document count")
    if type(snapshot.unreliable_count) is not int or snapshot.unreliable_count < 0:
        raise EvidenceBridgeRefused("invalid snapshot unreliable block count")
    if len(evidence.catalogue_documents) != snapshot.document_count:
        raise EvidenceBridgeRefused("snapshot catalogue count mismatch")

    catalogue = {}
    slugs: set[str] = set()
    for document in evidence.catalogue_documents:
        document_id = _opaque(document.document_id, _DOCUMENT, "catalogue document id")
        slug = _nfc(document.slug, "catalogue slug")
        _nfc(document.title, "catalogue title")
        if document_id in catalogue or slug in slugs:
            raise EvidenceBridgeRefused("duplicate catalogue document or slug")
        catalogue[document_id] = document
        slugs.add(slug)
    if not set(mapped_ids) <= catalogue.keys():
        raise EvidenceBridgeRefused("mapped document absent from catalogue")
    if (
        not isinstance(reviewed_designations, tuple)
        or len(reviewed_designations) != len(mapped_ids)
    ):
        raise EvidenceBridgeRefused("reviewed designations must cover mapped documents exactly")
    labels: dict[str, str] = {}
    for reviewed in reviewed_designations:
        if not isinstance(reviewed, ReviewedDesignation):
            raise EvidenceBridgeRefused("invalid reviewed designation")
        document_id = _opaque(reviewed.document_id, _DOCUMENT, "reviewed document id")
        if document_id not in mapped_ids or document_id in labels:
            raise EvidenceBridgeRefused("reviewed designation document mismatch")
        if reviewed.slug != catalogue[document_id].slug:
            raise EvidenceBridgeRefused("reviewed designation slug mismatch")
        labels[document_id] = _nfc(reviewed.designation, "reviewed designation")
    if set(labels) != set(mapped_ids):
        raise EvidenceBridgeRefused("reviewed designations must cover mapped documents exactly")

    ordinals = {document_id: 0 for document_id in mapped_ids}
    paragraph_ids: set[str] = set()
    source_rows: list[SourceParagraph] = []
    target_rows: list[TargetParagraph] = []
    for row in evidence.mapped_paragraphs:
        document_id = row.document_id
        if document_id not in ordinals:
            raise EvidenceBridgeRefused("unmapped paragraph document")
        paragraph_id = _opaque(row.paragraph_id, _PARAGRAPH, "paragraph id")
        if (
            paragraph_id in paragraph_ids
            or type(row.ordinal) is not int
            or row.ordinal != ordinals[document_id]
        ):
            raise EvidenceBridgeRefused("paragraph identity or ordinal mismatch")
        paragraph_ids.add(paragraph_id)
        ordinals[document_id] += 1
        if type(row.page_label) is not int or row.page_label < 1:
            raise EvidenceBridgeRefused("invalid page label")
        if row.kind not in _KINDS or row.text_reliability not in {"reliable", "unreliable"}:
            raise EvidenceBridgeRefused("unknown paragraph kind or reliability")
        _nfc(row.clause_number, "clause number", optional=True)
        body = _nfc(row.text, "paragraph text")
        _digest(row.text_sha256, "paragraph text digest")
        if hashlib.sha256(body.encode("utf-8")).hexdigest() != row.text_sha256:
            raise EvidenceBridgeRefused("paragraph text digest mismatch")
        reliable = row.text_reliability == "reliable"
        source_rows.append(SourceParagraph(
            RetrievalParagraph(
                document_id=document_id,
                paragraph_id=paragraph_id,
                designation=labels[document_id],
                title=catalogue[document_id].title,
                ordinal=row.ordinal,
                clause_number=row.clause_number,
                page_label=str(row.page_label),
                text=body,
                reliable=reliable,
            ),
            row.text_sha256,
        ))
        target_rows.append(TargetParagraph(
            document_id=document_id,
            paragraph_id=paragraph_id,
            ordinal=row.ordinal,
            text=body,
            kind=row.kind,
            clause_number=row.clause_number,
            reliable=reliable,
        ))
    if not source_rows or any(count == 0 for count in ordinals.values()):
        raise EvidenceBridgeRefused("mapped document has no paragraphs")
    return RetrievalSourceInputs(
        snapshot=SnapshotBinding(
            snapshot_id=snapshot.snapshot_id,
            content_key=snapshot.content_key,
            content_digest=snapshot.content_digest,
            embedding_build=identity.embedding_build,
            document_count=snapshot.document_count,
        ),
        source_paragraphs=tuple(source_rows),
        target_paragraphs=tuple(target_rows),
    )


__all__ = [
    "EvidenceBridgeRefused",
    "RetrievalSourceInputs",
    "ReviewedDesignation",
    "project_snapshot_evidence",
]
