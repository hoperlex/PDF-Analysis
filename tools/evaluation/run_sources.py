"""Read-only PDF source attestation for the offline AR v2 seeded evaluator.

The caller owns the database read transaction and supplies its Run and Version
read ports. Only the saved Version source Blob is attested here. The original
portal ZIP is not persisted with the Version and needs separate local fixture
validation before a measured evaluation can use this result.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Mapping, Protocol

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    AR_V2_RECORDED_BUNDLE_ID,
    AR_V2_RECORDED_PROFILE_ID,
    resolve_recorded_profile,
)
from auditmanager.documents.public import (
    MANIFEST_ROLE_SOURCE_DOCUMENT,
    DocumentVersionRecord,
)
from auditmanager.shared.identity import VersionUid
from auditmanager.storage.public import BlobStore, derive_blob_id, parse_blob_id


# The committed synthetic PDFs are much smaller. Keep the read bounded even
# when a forged Version reports a large source; enlarging this needs a new task.
MAX_SEEDED_PDF_BYTES = 2 * 1024 * 1024
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class SeededSourceError(ValueError):
    """A saved run cannot be attributed to the declared seeded PDF."""


class RunRecord(Protocol):
    run_id: str
    project_uid: str
    version_uid: str
    state: str
    analysis_profile_id: str
    prompt_bundle_id: str
    provider_mode: str


class RunReader(Protocol):
    def get(self, session: Session, run_id: str) -> RunRecord: ...


class VersionReader(Protocol):
    def get_version(self, session: Session, version_uid: VersionUid) -> DocumentVersionRecord: ...


@dataclass(frozen=True, slots=True)
class SeededPdfSourceAttestation:
    bundle_id: str
    run_id: str
    project_uid: str
    version_uid: str
    source_blob_id: str
    pdf_sha256: str
    pdf_byte_size: int


def _expected_pdf_digest(manifest: Mapping[str, object], bundle_id: str) -> str:
    if manifest.get("schema") != "ar-v2-seeded/1" or manifest.get("profile") != "ar_v2":
        raise SeededSourceError("seeded_manifest_version_mismatch")
    entries = manifest.get("bundles")
    if not isinstance(entries, list) or not entries:
        raise SeededSourceError("seeded_manifest_bundles_required")
    seen: set[str] = set()
    expected: str | None = None
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise SeededSourceError("seeded_manifest_bundle_invalid")
        identifier, digest = entry.get("id"), entry.get("pdf_sha256")
        if (
            not isinstance(identifier, str)
            or not identifier
            or identifier in seen
            or not isinstance(digest, str)
            or _SHA256.fullmatch(digest) is None
        ):
            raise SeededSourceError("seeded_manifest_bundle_invalid")
        seen.add(identifier)
        if identifier == bundle_id:
            expected = digest
    if expected is None:
        raise SeededSourceError("seeded_bundle_unknown")
    return expected


def attest_seeded_run_pdf(
    session: Session,
    *,
    run_id: str,
    bundle_id: str,
    manifest: Mapping[str, object],
    runs: RunReader,
    versions: VersionReader,
    blobs: BlobStore,
) -> SeededPdfSourceAttestation:
    """Attest one saved Run's exact source PDF through its immutable Version.

    No plan, recording, finding, original ZIP or model-quality result is read.
    Repository and storage exceptions propagate; this function makes no write.
    """
    if not isinstance(run_id, str) or not run_id or not isinstance(bundle_id, str) or not bundle_id:
        raise SeededSourceError("seeded_run_or_bundle_required")
    expected_digest = _expected_pdf_digest(manifest, bundle_id)
    resolve_recorded_profile(AR_V2_RECORDED_PROFILE_ID, AR_V2_RECORDED_BUNDLE_ID)

    run = runs.get(session, run_id)
    if (
        run.run_id != run_id
        or run.state != "published"
        or run.provider_mode != "recorded"
        or run.analysis_profile_id != str(AR_V2_RECORDED_PROFILE_ID)
        or run.prompt_bundle_id != str(AR_V2_RECORDED_BUNDLE_ID)
    ):
        raise SeededSourceError("seeded_run_identity_mismatch")
    try:
        version_uid = VersionUid.parse(run.version_uid)
    except (TypeError, ValueError):
        raise SeededSourceError("seeded_run_version_invalid") from None
    version = versions.get_version(session, version_uid)
    if (
        str(version.version_uid) != run.version_uid
        or str(version.project_uid) != run.project_uid
    ):
        raise SeededSourceError("seeded_run_version_mismatch")

    sources = tuple(item for item in version.manifest if item.role == MANIFEST_ROLE_SOURCE_DOCUMENT)
    if len(sources) != 1:
        raise SeededSourceError("seeded_source_entry_missing_or_duplicate")
    source = sources[0]
    if (
        source.media_type != "application/pdf"
        or version.media_type != "application/pdf"
        or type(source.size_bytes) is not int
        or not 0 < source.size_bytes <= MAX_SEEDED_PDF_BYTES
        or version.byte_size != source.size_bytes
        or not isinstance(source.sha256, str)
        or _SHA256.fullmatch(source.sha256) is None
        or version.sha256 != source.sha256
    ):
        raise SeededSourceError("seeded_source_manifest_invalid")
    if source.sha256 != expected_digest:
        raise SeededSourceError("seeded_bundle_pdf_mismatch")

    blob_id = parse_blob_id(source.blob_id)
    if blob_id != derive_blob_id(sha256=source.sha256, size=source.size_bytes):
        raise SeededSourceError("seeded_source_blob_identity_mismatch")
    stream = blobs.open_stream(
        blob_id, expected_sha256=source.sha256, expected_size=source.size_bytes,
    )
    size = 0
    digest = hashlib.sha256()
    try:
        for chunk in stream:
            if not isinstance(chunk, bytes) or not chunk:
                raise SeededSourceError("seeded_source_stream_invalid")
            size += len(chunk)
            if size > source.size_bytes or size > MAX_SEEDED_PDF_BYTES:
                raise SeededSourceError("seeded_source_size_mismatch")
            digest.update(chunk)
    finally:
        stream.close()
    if size != source.size_bytes or digest.hexdigest() != source.sha256:
        raise SeededSourceError("seeded_source_bytes_mismatch")
    return SeededPdfSourceAttestation(
        bundle_id=bundle_id,
        run_id=run_id,
        project_uid=run.project_uid,
        version_uid=run.version_uid,
        source_blob_id=str(blob_id),
        pdf_sha256=source.sha256,
        pdf_byte_size=size,
    )


__all__ = ["MAX_SEEDED_PDF_BYTES", "SeededPdfSourceAttestation", "SeededSourceError", "attest_seeded_run_pdf"]
