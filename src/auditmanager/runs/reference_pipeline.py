"""Unserved W57b Run reference read under one caller-owned transaction.

The caller authenticates the user and owns transaction commit/rollback. This
read combines exact saved sources; it grants no authority to publish a result.
"""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.documents.public import DocumentRepository
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.norms.public import (
    ReferencePipelineResult,
    load_verified_catalogue,
    reference_pages_from_text_layer,
    run_reference_pipeline,
)
from auditmanager.runs.reference_text_input import load_saved_reference_text
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobStore


_RUN_PIN = text("""
    SELECT run_id, version_uid, norm_retrieval_set_id, norms_snapshot_id, state
      FROM audit_run WHERE run_id = :run_id
""")
_MAX_CATALOGUE_BYTES = 10_000_000  # The verified reader and canonical parser cap.


@dataclass(frozen=True, slots=True)
class ReferenceRunPins:
    run_id: str
    version_uid: str
    norm_retrieval_set_id: str
    norms_snapshot_id: str


@dataclass(frozen=True, slots=True)
class RunReferenceReport:
    pins: ReferenceRunPins
    catalogue_sha256: str
    result: ReferencePipelineResult


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="reference sources cannot be bound to the current run",
        stage_id="norm_verification",
        reason=reason,
    )


def _read_run_pin(session: Session, *, pins: ReferenceRunPins) -> dict[str, str]:
    rows = session.execute(_RUN_PIN, {"run_id": pins.run_id}).mappings().all()
    if len(rows) != 1:
        raise _refuse("run_pin_missing_or_duplicate")
    row = dict(rows[0])
    if (
        row.get("state") != "running"
        or row.get("run_id") != pins.run_id
        or row.get("version_uid") != pins.version_uid
        or row.get("norm_retrieval_set_id") != pins.norm_retrieval_set_id
        or row.get("norms_snapshot_id") != pins.norms_snapshot_id
    ):
        raise _refuse("run_pin_mismatch")
    return row


def _check_explicit_listing(
    listed_unparsed_slugs: tuple[str, ...], *, max_catalogue_bytes: int,
) -> None:
    if type(max_catalogue_bytes) is not int or not 1 <= max_catalogue_bytes <= _MAX_CATALOGUE_BYTES:
        raise _refuse("invalid_catalogue_byte_ceiling")
    if not isinstance(listed_unparsed_slugs, tuple):
        raise _refuse("explicit_unparsed_slug_tuple_required")
    # Each valid slug occurs at least once in the canonical catalogue JSON.
    # These are necessary size bounds, not authority to accept a listed slug.
    if len(listed_unparsed_slugs) > max_catalogue_bytes:
        raise _refuse("explicit_unparsed_slug_listing_too_large")
    seen: set[str] = set()
    encoded_bytes = 0
    for slug in listed_unparsed_slugs:
        if (not isinstance(slug, str) or not slug or len(slug) > max_catalogue_bytes
                or unicodedata.normalize("NFC", slug) != slug or slug in seen):
            raise _refuse("explicit_unparsed_slug_listing_invalid")
        try:
            encoded_bytes += len(slug.encode("utf-8"))
        except UnicodeError as exc:
            raise _refuse("explicit_unparsed_slug_listing_invalid") from exc
        if encoded_bytes > max_catalogue_bytes:
            raise _refuse("explicit_unparsed_slug_listing_too_large")
        seen.add(slug)


def read_run_references(
    session: Session,
    *,
    authority: AttemptAuthority,
    blob_store: BlobStore,
    pins: ReferenceRunPins,
    listed_unparsed_slugs: tuple[str, ...],
    max_text_bytes: int,
    max_catalogue_bytes: int,
    jobs: JobRepository | None = None,
    runs: RunRepository | None = None,
    documents: DocumentRepository | None = None,
) -> RunReferenceReport:
    """Return one read-only report from current saved PDF and catalogue bytes.

    Explicit pins and the slug tuple are required. In particular, no local
    candidate list becomes an implicit allowlist for unparsed catalogue slugs.
    """
    if not isinstance(pins, ReferenceRunPins) or any(
        type(value) is not str or not value
        for value in (
            pins.run_id, pins.version_uid,
            pins.norm_retrieval_set_id, pins.norms_snapshot_id,
        )
    ) or pins.run_id != authority.run_id:
        raise _refuse("invalid_explicit_run_pins")
    _check_explicit_listing(
        listed_unparsed_slugs, max_catalogue_bytes=max_catalogue_bytes,
    )

    job_repo = jobs or JobRepository()
    job_repo.require_current(session, authority)
    before = _read_run_pin(session, pins=pins)

    saved = load_saved_reference_text(
        session, authority=authority, blob_store=blob_store,
        max_input_bytes=max_text_bytes, runs=runs, jobs=job_repo,
        documents=documents,
    )
    if saved.version_uid != pins.version_uid:
        raise _refuse("saved_text_version_mismatch")

    catalogue = load_verified_catalogue(
        session, authority=authority, blob_store=blob_store,
        max_catalogue_bytes=max_catalogue_bytes, jobs=job_repo,
    )
    if (
        catalogue.run_id != pins.run_id
        or catalogue.norm_retrieval_set_id != pins.norm_retrieval_set_id
        or catalogue.expectation.snapshot_id != pins.norms_snapshot_id
    ):
        raise _refuse("verified_catalogue_pin_mismatch")
    if len(listed_unparsed_slugs) > catalogue.expectation.document_count:
        raise _refuse("explicit_unparsed_slug_listing_exceeds_snapshot")

    pages = reference_pages_from_text_layer(
        text_layer=saved.text_layer,
        version_uid=saved.version_uid,
        page_count=saved.page_count,
    )
    result = run_reference_pipeline(
        catalogue_blob=catalogue.data,
        expected_catalogue=catalogue.expectation,
        listed_unparsed_slugs=listed_unparsed_slugs,
        pages=pages,
    )
    job_repo.require_current(session, authority)
    if _read_run_pin(session, pins=pins) != before:
        raise _refuse("run_pin_changed_during_reference_read")
    return RunReferenceReport(
        pins=pins,
        catalogue_sha256=catalogue.expectation.catalogue_sha256,
        result=result,
    )


__all__ = ["ReferenceRunPins", "RunReferenceReport", "read_run_references"]
