"""W57b Run reference reads under one caller-owned transaction.

Two reads live here. :func:`read_run_references` is the unserved, attempt-bound read of a
*running* Run over its verified retrieval-set custody. :func:`read_run_norm_references`
(`NORM-REFS-RUN-01`) is the per-request, read-only listing for any stored Run: the citations
in its saved text, each resolved against the norms snapshot the Run pinned.

The caller authenticates the user and owns transaction commit/rollback. These
reads combine exact saved sources; they grant no authority to publish a result.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import re
from typing import Final, Protocol, runtime_checkable
import unicodedata

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.documents.public import DocumentRepository
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.norms.public import (
    ReferencePipelineResult,
    ReferenceReadModel,
    ReferenceRefused,
    TooManyCitations,
    build_reference_read_model,
    load_verified_catalogue,
    read_snapshot_catalogue,
    reference_pages_from_text_layer,
    run_reference_pipeline,
)
from auditmanager.runs.reference_text_input import load_saved_reference_text
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdentityError, RunId, VersionUid
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


# --- the per-request listing of a stored Run's cited norms (`NORM-REFS-RUN-01`) --------------

STATE_READY: Final[str] = "ready"
#: The Run pinned no norms snapshot (none was current when it was created, CD-6).
STATE_SNAPSHOT_NOT_PINNED: Final[str] = "snapshot_not_pinned"
#: The Run has no saved ``prepared.text_layer`` (``source_preparation`` did not succeed).
STATE_TEXT_UNAVAILABLE: Final[str] = "text_unavailable"
#: The text cites more distinct designations than one answer carries.
STATE_TOO_MANY_CITATIONS: Final[str] = "too_many_citations"
#: In the order the preconditions are checked.
STATES: Final[tuple[str, ...]] = (
    STATE_READY,
    STATE_SNAPSHOT_NOT_PINNED,
    STATE_TEXT_UNAVAILABLE,
    STATE_TOO_MANY_CITATIONS,
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True, slots=True)
class SavedRunPageText:
    """The verified ``prepared.text_layer`` of one Run as page number to page text."""

    run_id: str
    text_layer_sha256: str
    pages: Mapping[int, str]


@runtime_checkable
class SavedRunTextReader(Protocol):
    """The Run's saved page text (implemented by the composition root over the object store)."""

    def saved_page_text(
        self, session: Session, *, run_id: str, version_uid: str, page_count: int
    ) -> SavedRunPageText | None:
        """The Run's verified text layer for every page, or ``None`` when it has none.

        A layer that exists but fails its recorded digest or shape must raise, never
        answer ``None``.
        """


@dataclass(frozen=True, slots=True)
class RunNormReferences:
    """The norms a Run's text cites, or the explicit reason that cannot be said.

    ``references`` is set exactly when ``state`` is ``ready``.
    """

    run_id: str
    version_uid: str
    state: str
    page_count: int
    norms_snapshot_id: str | None
    text_layer_sha256: str | None
    references: ReferenceReadModel | None


def _integrity(message: str) -> DomainError:
    return DomainError(ErrorCode.INTERNAL_ERROR, message=message)


def _checked_text(
    text_layer: object, *, run_id: str, page_count: int
) -> SavedRunPageText:
    if (
        not isinstance(text_layer, SavedRunPageText)
        or text_layer.run_id != run_id
        or not isinstance(text_layer.text_layer_sha256, str)
        or _SHA256.fullmatch(text_layer.text_layer_sha256) is None
        or not isinstance(text_layer.pages, Mapping)
        or set(text_layer.pages) != set(range(1, page_count + 1))
        or any(not isinstance(value, str) for value in text_layer.pages.values())
    ):
        raise _integrity("the saved page text does not match its run and version")
    return text_layer


def read_run_norm_references(
    session: Session,
    *,
    run_id: str,
    reader: SavedRunTextReader,
    runs: RunRepository | None = None,
    documents: DocumentRepository | None = None,
) -> RunNormReferences:
    """The Run's cited norms, each resolved against the Run's own pinned norms snapshot.

    Per request, read-only and deterministic: no finding, no severity, no model call. An
    unknown Run is ``not_found`` (``AuditRun``). A precondition that fails is an explicit
    :data:`STATES` value with the facts read so far -- never an empty list, never another
    run's text or another snapshot. A stored fact or port answer that contradicts its own
    constraints (a version that is not the run's, a text that does not match, a snapshot
    whose documents differ from what it declares, a catalogue the resolver refuses) is
    ``internal_error``.
    """
    try:
        RunId.parse(run_id)
    except (IdentityError, TypeError):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="run_id", constraint="pattern") from None
    run_repo = runs or RunRepository()
    document_repo = documents or DocumentRepository()

    run = run_repo.get(session, run_id)
    try:
        parsed_version = VersionUid.parse(run.version_uid)
    except IdentityError:
        raise _integrity("the run's version identity is invalid") from None
    version = document_repo.get_version(session, parsed_version)
    if (
        run.run_id != run_id
        or str(version.version_uid) != run.version_uid
        or str(version.project_uid) != run.project_uid
        or type(version.page_count) is not int
        or version.page_count < 1
    ):
        raise _integrity("the run's version does not match the run")

    answer = RunNormReferences(
        run_id=run.run_id,
        version_uid=run.version_uid,
        state=STATE_READY,
        page_count=version.page_count,
        norms_snapshot_id=run.norms_snapshot_id,
        text_layer_sha256=None,
        references=None,
    )
    if run.norms_snapshot_id is None:
        return replace(answer, state=STATE_SNAPSHOT_NOT_PINNED)

    supplied = reader.saved_page_text(
        session, run_id=run.run_id, version_uid=run.version_uid, page_count=version.page_count
    )
    if supplied is None:
        return replace(answer, state=STATE_TEXT_UNAVAILABLE)
    text_layer = _checked_text(supplied, run_id=run.run_id, page_count=version.page_count)
    answer = replace(answer, text_layer_sha256=text_layer.text_layer_sha256)

    try:
        catalogue = read_snapshot_catalogue(session, snapshot_id=run.norms_snapshot_id)
        model = build_reference_read_model(
            pages=text_layer.pages,
            catalogue=catalogue,
            pinned_snapshot_id=run.norms_snapshot_id,
        )
    except TooManyCitations:
        return replace(answer, state=STATE_TOO_MANY_CITATIONS)
    except ReferenceRefused as exc:
        raise _integrity("the run's norm references cannot be bound to its pinned snapshot") from exc
    return replace(answer, references=model)


__all__ = [
    "ReferenceRunPins",
    "RunNormReferences",
    "RunReferenceReport",
    "STATES",
    "STATE_READY",
    "STATE_SNAPSHOT_NOT_PINNED",
    "STATE_TEXT_UNAVAILABLE",
    "STATE_TOO_MANY_CITATIONS",
    "SavedRunPageText",
    "SavedRunTextReader",
    "read_run_norm_references",
    "read_run_references",
]
