"""SELECT-only audit of declared Blob references in an isolated restored DB.

This checks database rows, not S3 bytes. A recovery integration must separately
resolve canonical keys through the storage adapter and compare the object mirror.
The caller owns a stable, read-only transaction; this module never opens one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.storage.public import derive_blob_id

_HEAD = "0022_findings_v2"
_BLOB_ID = re.compile(r"blob_[0-9A-HJKMNP-TV-Z]{26}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")

# The registry is intentionally a closed set. An added source needs a new task.
_SOURCES = frozenset({
    ("public", "input_manifest_entry", "blob_id"),
    ("public", "analysis_artifact_publication", "blob_id"),
    ("public", "norm_custody_admission", "blob_id"),
    ("public", "norm_custody_binding", "blob_id"),
})
_CATALOG_EXPECTED = _SOURCES | {("public", "blob", "blob_id")}

_VERSION = text("SELECT version_num FROM public.alembic_version")
_CATALOG = text("""
    SELECT DISTINCT n.nspname AS schema_name, c.relname AS table_name,
           a.attname AS column_name
      FROM pg_catalog.pg_attribute a
      JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
      JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f')
       AND a.attnum > 0 AND NOT a.attisdropped
       AND n.nspname <> 'information_schema' AND n.nspname !~ '^pg_'
       AND (a.attname ~ '(^|_)blob_id$'
            OR EXISTS (
                SELECT 1 FROM pg_catalog.pg_constraint fk
                 WHERE fk.contype = 'f' AND fk.conrelid = c.oid
                   AND fk.confrelid = 'public.blob'::regclass
                   AND a.attnum = ANY(fk.conkey)))
     ORDER BY schema_name, table_name, column_name
""")
_BLOBS = text("""
    SELECT blob_id, state, sha256, size_bytes, media_type
      FROM public.blob ORDER BY blob_id COLLATE "C"
""")
_MANIFEST = text("""
    SELECT version_uid AS owner_id, role, blob_id, sha256, size_bytes, media_type
      FROM public.input_manifest_entry
     ORDER BY version_uid COLLATE "C", role COLLATE "C"
""")
_ARTIFACTS = text("""
    SELECT attempt_id AS owner_id, stage_id, blob_role, blob_id, state
      FROM public.analysis_artifact_publication
     ORDER BY attempt_id COLLATE "C", stage_id COLLATE "C", blob_id COLLATE "C"
""")
_ADMISSIONS = text("""
    SELECT norm_custody_admission_id AS owner_id, blob_id, state,
           declared_sha256, declared_size_bytes, media_type
      FROM public.norm_custody_admission
     ORDER BY norm_custody_admission_id COLLATE "C"
""")
_BINDINGS = text("""
    SELECT norm_custody_binding_id AS owner_id,
           norm_custody_admission_id AS admission_id, blob_id
      FROM public.norm_custody_binding
     ORDER BY norm_custody_binding_id COLLATE "C"
""")


class BlobReferenceAuditRefused(ValueError):
    """The restored DB cannot pass the pinned DB-side reference audit."""


@dataclass(frozen=True, slots=True)
class BlobFact:
    blob_id: str
    sha256: str
    size_bytes: int
    media_type: str


@dataclass(frozen=True, slots=True)
class BlobReferenceAudit:
    source_counts: tuple[tuple[str, int], ...]
    available_blobs: tuple[BlobFact, ...]


def _rows(session: Session, statement: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in session.execute(statement).mappings()]


def _fact(row: dict[str, Any], *, required: bool) -> BlobFact | None:
    blob_id = row["blob_id"]
    if not isinstance(blob_id, str) or not _BLOB_ID.fullmatch(blob_id):
        raise BlobReferenceAuditRefused("invalid Blob identity")
    sha256, size, media = row["sha256"], row["size_bytes"], row["media_type"]
    if sha256 is not None and (not isinstance(sha256, str) or not _SHA256.fullmatch(sha256)):
        raise BlobReferenceAuditRefused(f"Blob {blob_id} has invalid SHA-256")
    if size is not None and (type(size) is not int or size < 0):
        raise BlobReferenceAuditRefused(f"Blob {blob_id} has invalid size")
    if media is not None and (not isinstance(media, str) or not media):
        raise BlobReferenceAuditRefused(f"Blob {blob_id} has invalid media type")
    if sha256 is not None and size is not None \
            and str(derive_blob_id(sha256=sha256, size=size)) != blob_id:
        raise BlobReferenceAuditRefused(f"Blob {blob_id} disagrees with content identity")
    if sha256 is None or size is None or media is None:
        if not required:
            return None
        raise BlobReferenceAuditRefused(f"Blob {blob_id} has incomplete metadata")
    return BlobFact(blob_id, sha256, size, media)


def _declared_fact(row: dict[str, Any], *, source: str) -> BlobFact:
    sha_key = "declared_sha256" if source == "norm_custody_admission" else "sha256"
    size_key = "declared_size_bytes" if source == "norm_custody_admission" else "size_bytes"
    return _fact({
        "blob_id": row["blob_id"], "sha256": row[sha_key],
        "size_bytes": row[size_key], "media_type": row["media_type"],
    }, required=True)  # type: ignore[return-value]


def _require_available(blobs: dict[str, tuple[str, BlobFact | None]], blob_id: str,
                       source: str) -> BlobFact:
    entry = blobs.get(blob_id)
    if entry is None or entry[0] != "available" or entry[1] is None:
        raise BlobReferenceAuditRefused(f"{source} names an unavailable Blob {blob_id}")
    return entry[1]


def audit_blob_references(session: Session) -> BlobReferenceAudit:
    """Inspect one consistent restored snapshot using SELECT statements only.

    The result is a DB-side requirement list, not an object-copy verdict. The
    caller must keep the restore isolated and transaction read-only throughout.
    """
    versions = [row["version_num"] for row in _rows(session, _VERSION)]
    if versions != [_HEAD]:
        raise BlobReferenceAuditRefused("migration head differs")

    catalog = {
        (row["schema_name"], row["table_name"], row["column_name"])
        for row in _rows(session, _CATALOG)
    }
    if catalog != _CATALOG_EXPECTED:
        raise BlobReferenceAuditRefused(
            f"Blob reference catalog differs: missing={sorted(_CATALOG_EXPECTED - catalog)}, "
            f"unknown={sorted(catalog - _CATALOG_EXPECTED)}"
        )

    blobs: dict[str, tuple[str, BlobFact | None]] = {}
    available: list[BlobFact] = []
    for row in _rows(session, _BLOBS):
        blob_id, state = row["blob_id"], row["state"]
        if blob_id in blobs or state not in (
            "temporary", "verifying", "available", "rejected", "erasure_pending", "erased"
        ):
            raise BlobReferenceAuditRefused("Blob row has duplicate identity or unknown state")
        fact = _fact(row, required=state == "available")
        blobs[blob_id] = (state, fact)
        if state == "available":
            assert fact is not None
            available.append(fact)

    counts: list[tuple[str, int]] = []
    manifest = _rows(session, _MANIFEST)
    for row in manifest:
        source = "input_manifest_entry"
        actual = _require_available(blobs, row["blob_id"], source)
        if _declared_fact(row, source=source) != actual:
            raise BlobReferenceAuditRefused(f"{source} facts differ for {row['blob_id']}")
    counts.append(("input_manifest_entry", len(manifest)))

    artifacts = _rows(session, _ARTIFACTS)
    for row in artifacts:
        state = row["state"]
        if state not in ("prepared", "bound", "abandoned"):
            raise BlobReferenceAuditRefused("analysis artifact state is unknown")
        if state == "bound":
            _require_available(blobs, row["blob_id"], "analysis_artifact_publication")
        elif row["blob_id"] not in blobs:
            raise BlobReferenceAuditRefused("analysis artifact intent lacks Blob row")
    counts.append(("analysis_artifact_publication", len(artifacts)))

    admissions = _rows(session, _ADMISSIONS)
    admission_by_id: dict[str, dict[str, Any]] = {}
    for row in admissions:
        state = row["state"]
        if state not in ("pending", "confirmed", "poisoned", "rejected"):
            raise BlobReferenceAuditRefused("custody admission state is unknown")
        declared = _declared_fact(row, source="norm_custody_admission")
        if state == "confirmed":
            if _require_available(blobs, row["blob_id"], "norm_custody_admission") != declared:
                raise BlobReferenceAuditRefused("confirmed custody facts differ from Blob")
        if row["owner_id"] in admission_by_id:
            raise BlobReferenceAuditRefused("duplicate custody admission")
        admission_by_id[row["owner_id"]] = row
    counts.append(("norm_custody_admission", len(admissions)))

    bindings = _rows(session, _BINDINGS)
    for row in bindings:
        admission = admission_by_id.get(row["admission_id"])
        if admission is None or admission["state"] != "confirmed" \
                or admission["blob_id"] != row["blob_id"]:
            raise BlobReferenceAuditRefused("custody binding lacks matching confirmed admission")
        _require_available(blobs, row["blob_id"], "norm_custody_binding")
    counts.append(("norm_custody_binding", len(bindings)))

    return BlobReferenceAudit(tuple(counts), tuple(sorted(available, key=lambda fact: fact.blob_id)))


__all__ = ["BlobFact", "BlobReferenceAudit", "BlobReferenceAuditRefused", "audit_blob_references"]
