"""Bind a saved AR v2 Run's PDF to independently checked local seed bytes.

This is an offline tool, not a runtime route. ``tools`` and ``tools/fixtures``
are its import roots, as for the existing seeded generator. The original ZIP
is local fixture evidence only: a published Version does not retain that ZIP.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from sqlalchemy.orm import Session

from auditmanager.storage.public import BlobStore
from evaluation.run_sources import (
    MAX_SEEDED_PDF_BYTES,
    RunReader,
    SeededPdfSourceAttestation,
    VersionReader,
    attest_seeded_run_pdf,
)
from seeded.validate import validate_bytes


FROZEN_SEEDED_MANIFEST_SHA256 = "95e07c2919d46a600cb9ffead41c883fd38d141699c6857a4700126d6dae6fb7"
MAX_LOCAL_MANIFEST_BYTES = 128 * 1024
MAX_LOCAL_PORTAL_ZIP_BYTES = 4 * 1024 * 1024


class LocalBundleError(ValueError):
    """The frozen local seed bytes cannot be joined to a saved Run."""


@dataclass(frozen=True, slots=True)
class VerifiedSeededLocalBundle:
    source: SeededPdfSourceAttestation
    manifest_sha256: str
    local_portal_bundle_sha256: str
    local_portal_bundle_byte_size: int


def _read_bounded(path: Path, *, limit: int, root: Path) -> bytes:
    if root.is_symlink() or path.parent.is_symlink() or path.is_symlink() or not path.is_file():
        raise LocalBundleError("seeded_local_file_missing_or_symlinked")
    with path.open("rb") as stream:
        payload = stream.read(limit + 1)
    if len(payload) > limit:
        raise LocalBundleError("seeded_local_file_too_large")
    return payload


def _bundle_file(root: Path, raw: object, *, suffix: str) -> Path:
    if not isinstance(raw, str):
        raise LocalBundleError("seeded_local_path_invalid")
    relative = PurePosixPath(raw)
    if (
        relative.is_absolute()
        or len(relative.parts) != 2
        or relative.parts[0] != "bundles"
        or relative.parts[1] in {".", ".."}
        or relative.suffix != suffix
        or str(relative) != raw
    ):
        raise LocalBundleError("seeded_local_path_invalid")
    return root / relative.parts[0] / relative.parts[1]


def bind_seeded_local_bundle(
    session: Session,
    *,
    run_id: str,
    bundle_id: str,
    fixture_root: Path,
    runs: RunReader,
    versions: VersionReader,
    blobs: BlobStore,
) -> VerifiedSeededLocalBundle:
    """Verify full local seed bytes, then attest one saved Run's matching PDF.

    No plan, recording, scored finding or original ZIP custody is inferred.
    The caller owns the database read transaction; this function makes no write.
    """
    if not isinstance(fixture_root, Path) or not fixture_root.is_dir() or fixture_root.is_symlink():
        raise LocalBundleError("seeded_local_root_invalid")
    raw_manifest = _read_bounded(
        fixture_root / "expected_issues.json", limit=MAX_LOCAL_MANIFEST_BYTES,
        root=fixture_root,
    )
    manifest_sha256 = hashlib.sha256(raw_manifest).hexdigest()
    if manifest_sha256 != FROZEN_SEEDED_MANIFEST_SHA256:
        raise LocalBundleError("seeded_local_manifest_changed")
    manifest = json.loads(raw_manifest)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("bundles"), list):
        raise LocalBundleError("seeded_local_manifest_invalid")
    entries = manifest["bundles"]
    if len(entries) != 10:
        raise LocalBundleError("seeded_local_manifest_invalid")

    files: dict[str, bytes] = {}
    selected: dict | None = None
    for entry in entries:
        if not isinstance(entry, dict):
            raise LocalBundleError("seeded_local_manifest_invalid")
        if entry.get("id") == bundle_id:
            selected = entry
        for key, suffix, limit in (
            ("pdf", ".pdf", MAX_SEEDED_PDF_BYTES),
            ("portal_bundle", ".zip", MAX_LOCAL_PORTAL_ZIP_BYTES),
        ):
            raw_path = entry.get(key)
            path = _bundle_file(fixture_root, raw_path, suffix=suffix)
            if raw_path in files:
                raise LocalBundleError("seeded_local_path_duplicate")
            files[raw_path] = _read_bounded(path, limit=limit, root=fixture_root)
    validate_bytes(manifest, files, require_full=True)
    if selected is None:
        raise LocalBundleError("seeded_local_bundle_unknown")

    source = attest_seeded_run_pdf(
        session, run_id=run_id, bundle_id=bundle_id, manifest=manifest,
        runs=runs, versions=versions, blobs=blobs,
    )
    local_pdf = files[selected["pdf"]]
    if (
        source.pdf_sha256 != hashlib.sha256(local_pdf).hexdigest()
        or source.pdf_byte_size != len(local_pdf)
    ):
        raise LocalBundleError("seeded_local_pdf_source_mismatch")
    local_zip = files[selected["portal_bundle"]]
    return VerifiedSeededLocalBundle(
        source=source,
        manifest_sha256=manifest_sha256,
        local_portal_bundle_sha256=hashlib.sha256(local_zip).hexdigest(),
        local_portal_bundle_byte_size=len(local_zip),
    )


__all__ = [
    "FROZEN_SEEDED_MANIFEST_SHA256",
    "LocalBundleError",
    "VerifiedSeededLocalBundle",
    "bind_seeded_local_bundle",
]
