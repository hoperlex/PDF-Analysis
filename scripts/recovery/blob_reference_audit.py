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
from scripts.recovery.schema_coverage import HEAD as _HEAD
_BLOB_ID = re.compile(r"blob_[0-9A-HJKMNP-TV-Z]{26}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")

# The registry is intentionally a closed set. An added source needs a new task.
_SOURCES = frozenset({
    ("public", "input_manifest_entry", "blob_id"),
    ("public", "analysis_artifact_publication", "blob_id"),
    ("public", "norm_custody_admission", "blob_id"),
    ("public", "norm_custody_binding", "blob_id"),
    ("public", "norm_retrieval_set", "set_blob_id"),
    ("public", "norm_retrieval_set", "catalogue_blob_id"),
    # `0026_price_lists`: a price-list revision is bound to its uploaded file's Blob.
    ("public", "price_list_revision", "blob_id"),
    # `0038_comparison_foundation`: the verified object of an uploaded comparison file, and the
    # stored profile, preview and thumbnail of a page profile.
    ("public", "comparison_upload_file", "blob_id"),
    ("public", "comparison_page_profile", "profile_blob_id"),
    ("public", "comparison_page_profile", "preview_blob_id"),
    ("public", "comparison_page_profile", "thumbnail_blob_id"),
    # `0039_comparison_core`: the bit-packed difference mask of a sheet-pair result (not stored for a `same` pair).
    ("public", "comparison_sheet_pair_result", "mask_blob_id"),
    # `0040_comparison_ai_reports`: a stored file of a report (the PDF, the exact MD, the report text).
    ("public", "comparison_report_artifact", "blob_id"),
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
_RETRIEVAL_SETS = text("""
    SELECT norm_retrieval_set_id AS owner_id, state,
           set_blob_id, set_size_bytes, observed_set_sha256,
           catalogue_blob_id, catalogue_size_bytes, observed_catalogue_sha256
      FROM public.norm_retrieval_set
     ORDER BY norm_retrieval_set_id COLLATE "C"
""")
_PRICE_LISTS = text("""
    SELECT price_list_id AS owner_id, blob_id, sha256, size_bytes, media_type
      FROM public.price_list_revision ORDER BY price_list_id COLLATE "C"
""")


_COMPARISON_FILES = text("""
    SELECT comparison_upload_file_id AS owner_id, state, blob_id
      FROM public.comparison_upload_file WHERE blob_id IS NOT NULL
     ORDER BY comparison_upload_file_id COLLATE "C"
""")
_PAGE_PROFILES = text("""
    SELECT comparison_page_profile_id AS owner_id,
           profile_blob_id, preview_blob_id, thumbnail_blob_id
      FROM public.comparison_page_profile ORDER BY comparison_page_profile_id COLLATE "C"
""")


_PAIR_MASKS = text("""
    SELECT comparison_sheet_pair_result_id AS owner_id, mask_blob_id
      FROM public.comparison_sheet_pair_result WHERE mask_blob_id IS NOT NULL
     ORDER BY comparison_sheet_pair_result_id COLLATE "C"
""")


_REPORT_ARTIFACTS = text("""
    SELECT comparison_report_artifact_id AS owner_id, blob_id
      FROM public.comparison_report_artifact
     ORDER BY comparison_report_artifact_id COLLATE "C"
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


def _require_pinned_schema(session: Session) -> None:
    """The head is the pinned one and the set of blob-referencing columns is the closed set above."""
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


def audit_blob_references(session: Session) -> BlobReferenceAudit:
    """Inspect one consistent restored snapshot using SELECT statements only.

    The result is a DB-side requirement list, not an object-copy verdict. The
    caller must keep the restore isolated and transaction read-only throughout.
    """
    _require_pinned_schema(session)

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

    retrieval_sets = _rows(session, _RETRIEVAL_SETS)
    for row in retrieval_sets:
        if row["state"] == "rejected":
            if any(row[name] is not None for name in (
                "set_blob_id", "set_size_bytes", "catalogue_blob_id", "catalogue_size_bytes"
            )):
                raise BlobReferenceAuditRefused("rejected retrieval set has a Blob reference")
            continue
        if row["state"] != "verified":
            raise BlobReferenceAuditRefused("retrieval set state is unknown")
        for role in ("set", "catalogue"):
            blob_id = row[f"{role}_blob_id"]
            if not isinstance(blob_id, str):
                raise BlobReferenceAuditRefused(f"verified retrieval set lacks {role} Blob")
            actual = _require_available(blobs, blob_id, "norm_retrieval_set")
            if (row[f"observed_{role}_sha256"], row[f"{role}_size_bytes"]) != (
                actual.sha256, actual.size_bytes
            ):
                raise BlobReferenceAuditRefused(f"verified retrieval set {role} Blob facts differ")
    counts.append(("norm_retrieval_set", len(retrieval_sets)))

    price_lists = _rows(session, _PRICE_LISTS)
    for row in price_lists:
        source = "price_list_revision"
        actual = _require_available(blobs, row["blob_id"], source)
        if _declared_fact(row, source=source) != actual:
            raise BlobReferenceAuditRefused(f"{source} facts differ for {row['blob_id']}")
    counts.append(("price_list_revision", len(price_lists)))

    comparison_files = _rows(session, _COMPARISON_FILES)
    for row in comparison_files:
        if row["state"] != "verified":
            raise BlobReferenceAuditRefused("a comparison upload file holds a Blob before it is verified")
        _require_available(blobs, row["blob_id"], "comparison_upload_file")
    counts.append(("comparison_upload_file", len(comparison_files)))

    page_profiles = _rows(session, _PAGE_PROFILES)
    for row in page_profiles:
        for column in ("profile_blob_id", "preview_blob_id", "thumbnail_blob_id"):
            if row[column] is not None:
                _require_available(blobs, row[column], "comparison_page_profile")
    counts.append(("comparison_page_profile", len(page_profiles)))

    pair_masks = _rows(session, _PAIR_MASKS)
    for row in pair_masks:
        _require_available(blobs, row["mask_blob_id"], "comparison_sheet_pair_result")
    counts.append(("comparison_sheet_pair_result", len(pair_masks)))

    report_artifacts = _rows(session, _REPORT_ARTIFACTS)
    for row in report_artifacts:
        _require_available(blobs, row["blob_id"], "comparison_report_artifact")
    counts.append(("comparison_report_artifact", len(report_artifacts)))

    return BlobReferenceAudit(tuple(counts), tuple(sorted(available, key=lambda fact: fact.blob_id)))


# --- the other direction: published bytes that no table names -------------------------------------
#
# `CMP-STORAGE-PARTS-01`. `audit_blob_references` starts from the references and asks whether each
# Blob is there. A comparison upload makes the opposite fault possible: the multipart object is
# verified and published (`blob` is `available`) and the process dies before `comparison_upload_file.blob_id`
# is written, so the bytes exist and nothing names them. The storage port has no delete of a published
# blob (ADR-0025 decision 9: no eviction), so such bytes are made visible here rather than removed.

_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]*\Z")


def _unreferenced_statement() -> Any:
    """``SELECT`` of the available Blobs that none of the closed `_SOURCES` columns names.

    The identifiers come from the closed constant set above (checked against a plain pattern, never
    from input); the catalog check that precedes every use of this statement proves that no other
    column references `public.blob`, so "no source names it" means "no table names it".
    """
    clauses = []
    for schema, table, column in sorted(_SOURCES):
        if not all(_IDENTIFIER.match(part) for part in (schema, table, column)):
            raise BlobReferenceAuditRefused("a registered Blob source is not a plain identifier")
        clauses.append(
            f"NOT EXISTS (SELECT 1 FROM {schema}.{table} r WHERE r.{column} = b.blob_id)"
        )
    return text(
        "SELECT b.blob_id, b.sha256, b.size_bytes, b.media_type FROM public.blob b "
        "WHERE b.state = 'available' AND " + " AND ".join(clauses) + ' ORDER BY b.blob_id COLLATE "C"'
    )


_OPEN_COMPARISON_FILES = text("""
    SELECT comparison_upload_file_id AS owner_id, declared_sha256, declared_size_bytes
      FROM public.comparison_upload_file WHERE blob_id IS NULL
     ORDER BY comparison_upload_file_id COLLATE "C"
""")


@dataclass(frozen=True, slots=True)
class UnreferencedBlob:
    """One available Blob no table names.

    ``comparison_upload_file_ids`` are the files that hold no Blob yet and declared exactly these
    bytes (the Blob identity is derived from the declared SHA-256 and size): empty when nothing in
    the database explains the Blob.
    """

    blob_id: str
    sha256: str
    size_bytes: int
    media_type: str
    comparison_upload_file_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UnreferencedBlobReport:
    """Available Blobs that no table names, split by whether an open comparison file explains them.

    ``attributed`` -- the Blob has the identity of the declared bytes of one or more comparison upload
    files that hold no Blob: a completion killed between publication and the write of `blob_id`. The
    file may be completed again (publication is idempotent by content). ``unattributed`` -- nothing in
    the database explains the Blob. Neither is evidence of loss; both are stored bytes that no row
    accounts for, listed so they are not invisible.
    """

    attributed: tuple[UnreferencedBlob, ...]
    unattributed: tuple[UnreferencedBlob, ...]

    @property
    def total_bytes(self) -> int:
        return sum(blob.size_bytes for blob in self.attributed + self.unattributed)


def report_unreferenced_comparison_blobs(session: Session) -> UnreferencedBlobReport:
    """List the available Blobs that no table names, by SELECT statements only.

    Refuses (like `audit_blob_references`) unless the head is the pinned one and the set of columns
    that reference a Blob is the closed set, so a newly added reference cannot make a referenced Blob
    look orphaned. A restore that is being written to would show an in-flight publication as an
    orphan; run it on the isolated snapshot, as the audit above.
    """
    _require_pinned_schema(session)

    declared: dict[str, list[str]] = {}
    for row in _rows(session, _OPEN_COMPARISON_FILES):
        identity = str(derive_blob_id(sha256=row["declared_sha256"], size=row["declared_size_bytes"]))
        declared.setdefault(identity, []).append(row["owner_id"])

    attributed: list[UnreferencedBlob] = []
    unattributed: list[UnreferencedBlob] = []
    for row in _rows(session, _unreferenced_statement()):
        fact = _fact(row, required=True)
        assert fact is not None
        files = tuple(declared.get(fact.blob_id, ()))
        blob = UnreferencedBlob(fact.blob_id, fact.sha256, fact.size_bytes, fact.media_type, files)
        (attributed if files else unattributed).append(blob)
    return UnreferencedBlobReport(tuple(attributed), tuple(unattributed))


__all__ = [
    "BlobFact",
    "BlobReferenceAudit",
    "BlobReferenceAuditRefused",
    "UnreferencedBlob",
    "UnreferencedBlobReport",
    "audit_blob_references",
    "report_unreferenced_comparison_blobs",
]
