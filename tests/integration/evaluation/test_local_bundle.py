"""Local AR v2 PDF/ZIP bytes must join the saved Run source without scoring."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import AR_V2_RECORDED_BUNDLE_ID, AR_V2_RECORDED_PROFILE_ID
from auditmanager.documents.public import MANIFEST_ROLE_SOURCE_DOCUMENT, ManifestEntry
from auditmanager.shared.identity import ProjectUid, VersionUid
from auditmanager.storage.public import derive_blob_id

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/fixtures"))
from evaluation.local_bundle import (  # noqa: E402
    FROZEN_SEEDED_MANIFEST_SHA256,
    MAX_LOCAL_PORTAL_ZIP_BYTES,
    LocalBundleError,
    bind_seeded_local_bundle,
)
from evaluation.run_sources import SeededSourceError  # noqa: E402
from seeded.validate import CorpusError  # noqa: E402


class _Runs:
    def __init__(self, row: object, events: list[str]) -> None:
        self.row = row
        self.events = events

    def get(self, session: object, run_id: str) -> object:
        assert session is _SESSION and run_id == "run-seeded-local"
        self.events.append("run")
        return self.row


class _Versions:
    def __init__(self, row: object, events: list[str]) -> None:
        self.row = row
        self.events = events

    def get_version(self, session: object, version_uid: VersionUid) -> object:
        assert session is _SESSION and isinstance(version_uid, VersionUid)
        self.events.append("version")
        return self.row


class _Blobs:
    def __init__(self, payload: bytes, events: list[str]) -> None:
        self.payload = payload
        self.events = events

    def open_stream(self, blob_id: str, *, expected_sha256: str, expected_size: int):
        self.events.append("blob")
        assert blob_id == derive_blob_id(sha256=expected_sha256, size=expected_size)
        assert expected_size == len(self.payload)
        yield self.payload[:100]
        yield self.payload[100:]


_SESSION = object()


def _setup(tmp_path: Path, *, source_bundle_index: int = 0):
    fixture_root = tmp_path / "ar_v2"
    shutil.copytree(ROOT / "fixtures/evaluation/ar_v2", fixture_root)
    manifest = json.loads((fixture_root / "expected_issues.json").read_text(encoding="utf-8"))
    bundle = manifest["bundles"][source_bundle_index]
    payload = (fixture_root / bundle["pdf"]).read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    project_uid, version_uid = ProjectUid.new(), VersionUid.new()
    source = ManifestEntry(
        role=MANIFEST_ROLE_SOURCE_DOCUMENT,
        blob_id=derive_blob_id(sha256=digest, size=len(payload)),
        sha256=digest, size_bytes=len(payload), media_type="application/pdf",
    )
    version = SimpleNamespace(
        version_uid=version_uid, project_uid=project_uid, manifest=(source,),
        media_type="application/pdf", sha256=digest, byte_size=len(payload),
    )
    run = SimpleNamespace(
        run_id="run-seeded-local", project_uid=str(project_uid),
        version_uid=str(version_uid), state="published", provider_mode="recorded",
        analysis_profile_id=str(AR_V2_RECORDED_PROFILE_ID),
        prompt_bundle_id=str(AR_V2_RECORDED_BUNDLE_ID),
    )
    events: list[str] = []
    return fixture_root, manifest, _Runs(run, events), _Versions(version, events), _Blobs(payload, events), events


def _bind(root: Path, manifest: dict, runs: _Runs, versions: _Versions, blobs: _Blobs, *, index: int = 0):
    return bind_seeded_local_bundle(
        _SESSION, run_id="run-seeded-local", bundle_id=manifest["bundles"][index]["id"],
        fixture_root=root, runs=runs, versions=versions, blobs=blobs,
    )


def test_saved_pdf_is_joined_to_independently_checked_local_pdf_and_zip(tmp_path: Path) -> None:
    root, manifest, runs, versions, blobs, events = _setup(tmp_path)
    result = _bind(root, manifest, runs, versions, blobs)
    bundle = manifest["bundles"][0]
    local_zip = (root / bundle["portal_bundle"]).read_bytes()
    assert result.source.bundle_id == bundle["id"]
    assert result.source.run_id == "run-seeded-local"
    assert result.source.pdf_sha256 == bundle["pdf_sha256"]
    assert result.manifest_sha256 == FROZEN_SEEDED_MANIFEST_SHA256
    assert result.local_portal_bundle_sha256 == bundle["portal_bundle_sha256"]
    assert result.local_portal_bundle_byte_size == len(local_zip)
    assert events == ["run", "version", "blob"]
    assert _bind(root, manifest, runs, versions, blobs) == result


@pytest.mark.parametrize("changed", ["pdf", "portal_bundle"])
def test_changed_local_pdf_or_zip_refuses_before_saved_read(tmp_path: Path, changed: str) -> None:
    root, manifest, runs, versions, blobs, events = _setup(tmp_path)
    path = root / manifest["bundles"][0][changed]
    payload = path.read_bytes()
    path.write_bytes(b"X" + payload[1:])
    with pytest.raises(CorpusError, match="digest mismatch"):
        _bind(root, manifest, runs, versions, blobs)
    assert events == []


def test_changed_manifest_refuses_before_any_fixture_or_saved_read(tmp_path: Path) -> None:
    root, manifest, runs, versions, blobs, events = _setup(tmp_path)
    path = root / "expected_issues.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(LocalBundleError, match="seeded_local_manifest_changed"):
        _bind(root, manifest, runs, versions, blobs)
    assert events == []


@pytest.mark.parametrize("changed", ["missing", "symlink", "oversized"])
def test_missing_symlinked_or_oversized_zip_refuses_bounded_read(tmp_path: Path, changed: str) -> None:
    root, manifest, runs, versions, blobs, events = _setup(tmp_path)
    path = root / manifest["bundles"][0]["portal_bundle"]
    path.unlink()
    if changed == "symlink":
        path.symlink_to(ROOT / "fixtures/evaluation/ar_v2" / manifest["bundles"][0]["portal_bundle"])
    elif changed == "oversized":
        path.write_bytes(b"x" * (MAX_LOCAL_PORTAL_ZIP_BYTES + 1))
    with pytest.raises(LocalBundleError, match="seeded_local_file_(missing_or_symlinked|too_large)"):
        _bind(root, manifest, runs, versions, blobs)
    assert events == []


def test_other_saved_pdf_cannot_claim_a_valid_local_bundle(tmp_path: Path) -> None:
    root, manifest, runs, versions, blobs, events = _setup(tmp_path, source_bundle_index=1)
    with pytest.raises(SeededSourceError, match="seeded_bundle_pdf_mismatch"):
        _bind(root, manifest, runs, versions, blobs, index=0)
    assert events == ["run", "version"]


def test_unknown_bundle_refuses_before_saved_read(tmp_path: Path) -> None:
    root, _, runs, versions, blobs, events = _setup(tmp_path)
    with pytest.raises(LocalBundleError, match="seeded_local_bundle_unknown"):
        bind_seeded_local_bundle(
            _SESSION, run_id="run-seeded-local", bundle_id="unknown",
            fixture_root=root, runs=runs, versions=versions, blobs=blobs,
        )
    assert events == []
