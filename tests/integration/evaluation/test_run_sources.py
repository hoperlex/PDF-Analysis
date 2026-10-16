"""Saved Run/Version/PDF source attribution for the offline AR v2 evaluator."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import AR_V2_RECORDED_BUNDLE_ID, AR_V2_RECORDED_PROFILE_ID
from auditmanager.documents.public import MANIFEST_ROLE_SOURCE_DOCUMENT, ManifestEntry
from auditmanager.shared.identity import ProjectUid, VersionUid
from auditmanager.storage.public import derive_blob_id

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from evaluation.run_sources import (  # noqa: E402
    MAX_SEEDED_PDF_BYTES,
    SeededSourceError,
    attest_seeded_run_pdf,
)

MANIFEST = json.loads(
    (ROOT / "fixtures/evaluation/ar_v2/expected_issues.json").read_text(encoding="utf-8")
)
SESSION = object()


class _Runs:
    def __init__(self, row: object) -> None:
        self.row = row
        self.calls = 0

    def get(self, session: object, run_id: str) -> object:
        assert session is SESSION and run_id == "run-seeded-01"
        self.calls += 1
        return self.row


class _Versions:
    def __init__(self, row: object) -> None:
        self.row = row
        self.calls = 0

    def get_version(self, session: object, version_uid: VersionUid) -> object:
        assert session is SESSION and isinstance(version_uid, VersionUid)
        self.calls += 1
        return self.row


class _Blobs:
    def __init__(self, chunks: tuple[bytes, ...]) -> None:
        self.chunks = chunks
        self.calls = 0
        self.closed = 0
        self.expected: tuple[str, int] | None = None

    def open_stream(
        self, blob_id: str, *, expected_sha256: str, expected_size: int,
    ):
        self.calls += 1
        self.expected = (expected_sha256, expected_size)
        assert blob_id == derive_blob_id(sha256=expected_sha256, size=expected_size)
        try:
            yield from self.chunks
        finally:
            self.closed += 1


def _case(bundle_index: int = 0):
    bundle = MANIFEST["bundles"][bundle_index]
    payload = (ROOT / "fixtures/evaluation/ar_v2" / bundle["pdf"]).read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    assert digest == bundle["pdf_sha256"]
    version_uid, project_uid = VersionUid.new(), ProjectUid.new()
    source = ManifestEntry(
        role=MANIFEST_ROLE_SOURCE_DOCUMENT,
        blob_id=derive_blob_id(sha256=digest, size=len(payload)),
        sha256=digest,
        size_bytes=len(payload),
        media_type="application/pdf",
    )
    version = SimpleNamespace(
        version_uid=version_uid, project_uid=project_uid,
        manifest=(source,), media_type="application/pdf",
        sha256=digest, byte_size=len(payload),
    )
    run = SimpleNamespace(
        run_id="run-seeded-01", project_uid=str(project_uid),
        version_uid=str(version_uid), state="published", provider_mode="recorded",
        analysis_profile_id=str(AR_V2_RECORDED_PROFILE_ID),
        prompt_bundle_id=str(AR_V2_RECORDED_BUNDLE_ID),
    )
    return bundle, payload, _Runs(run), _Versions(version), _Blobs((payload[:100], payload[100:]))


def _attest(bundle: dict, runs: _Runs, versions: _Versions, blobs: _Blobs):
    return attest_seeded_run_pdf(
        SESSION, run_id="run-seeded-01", bundle_id=bundle["id"],
        manifest=MANIFEST, runs=runs, versions=versions, blobs=blobs,
    )


def test_attests_saved_run_version_and_actual_pdf_bytes() -> None:
    bundle, payload, runs, versions, blobs = _case()
    proof = _attest(bundle, runs, versions, blobs)
    assert proof.bundle_id == bundle["id"]
    assert proof.run_id == "run-seeded-01"
    assert proof.version_uid == str(versions.row.version_uid)
    assert proof.project_uid == str(versions.row.project_uid)
    assert proof.source_blob_id == str(versions.row.manifest[0].blob_id)
    assert proof.pdf_sha256 == bundle["pdf_sha256"]
    assert proof.pdf_byte_size == len(payload)
    assert (runs.calls, versions.calls, blobs.calls, blobs.closed) == (1, 1, 1, 1)
    assert blobs.expected == (bundle["pdf_sha256"], len(payload))
    assert _attest(bundle, runs, versions, blobs) == proof


@pytest.mark.parametrize("change", ["run_id", "run_version", "project", "state", "mode", "profile", "prompt"])
def test_wrong_run_or_version_identity_refuses_before_blob(change: str) -> None:
    bundle, _, runs, versions, blobs = _case()
    if change == "run_id":
        runs.row.run_id = "another-run"
    elif change == "run_version":
        runs.row.version_uid = str(VersionUid.new())
    elif change == "project":
        versions.row.project_uid = ProjectUid.new()
    elif change == "state":
        runs.row.state = "running"
    elif change == "mode":
        runs.row.provider_mode = "proxy"
    elif change == "profile":
        runs.row.analysis_profile_id = "ap_wrong"
    else:
        runs.row.prompt_bundle_id = "pb_wrong"
    with pytest.raises(SeededSourceError, match="seeded_run_(identity|version)_mismatch"):
        _attest(bundle, runs, versions, blobs)
    assert blobs.calls == 0


@pytest.mark.parametrize("change", ["missing", "duplicate", "not_pdf", "oversized"])
def test_missing_duplicate_or_invalid_source_manifest_refuses_before_blob(change: str) -> None:
    bundle, _, runs, versions, blobs = _case()
    source = versions.row.manifest[0]
    if change == "missing":
        versions.row.manifest = ()
    elif change == "duplicate":
        versions.row.manifest = (source, source)
    elif change == "not_pdf":
        versions.row.manifest = (replace(source, media_type="text/plain"),)
    else:
        versions.row.manifest = (replace(source, size_bytes=MAX_SEEDED_PDF_BYTES + 1),)
        versions.row.byte_size = MAX_SEEDED_PDF_BYTES + 1
    with pytest.raises(SeededSourceError, match="seeded_source_(entry_missing_or_duplicate|manifest_invalid)"):
        _attest(bundle, runs, versions, blobs)
    assert blobs.calls == 0


def test_swapped_pdf_or_bundle_refuses_before_blob() -> None:
    first, _, runs, versions, blobs = _case(0)
    second = MANIFEST["bundles"][1]
    with pytest.raises(SeededSourceError, match="seeded_bundle_pdf_mismatch"):
        _attest(second, runs, versions, blobs)
    assert blobs.calls == 0
    _, _, swapped_runs, swapped_versions, swapped_blobs = _case(1)
    with pytest.raises(SeededSourceError, match="seeded_bundle_pdf_mismatch"):
        _attest(first, swapped_runs, swapped_versions, swapped_blobs)
    assert swapped_blobs.calls == 0


def test_manifest_blob_identity_must_be_derived_from_declared_bytes() -> None:
    bundle, _, runs, versions, blobs = _case()
    source = versions.row.manifest[0]
    versions.row.manifest = (replace(
        source, blob_id=derive_blob_id(sha256="0" * 64, size=source.size_bytes),
    ),)
    with pytest.raises(SeededSourceError, match="seeded_source_blob_identity_mismatch"):
        _attest(bundle, runs, versions, blobs)
    assert blobs.calls == 0


@pytest.mark.parametrize("change", ["short", "long", "corrupt"])
def test_short_long_or_corrupt_blob_refuses_and_closes_stream(change: str) -> None:
    bundle, payload, runs, versions, blobs = _case()
    if change == "short":
        blobs.chunks = (payload[:-1],)
    elif change == "long":
        blobs.chunks = (payload, b"x")
    else:
        blobs.chunks = (b"X" + payload[1:],)
    with pytest.raises(SeededSourceError, match="seeded_source_(size|bytes)_mismatch"):
        _attest(bundle, runs, versions, blobs)
    assert blobs.calls == blobs.closed == 1


def test_unknown_or_duplicate_seeded_bundle_is_refused_before_run_read() -> None:
    bundle, _, runs, versions, blobs = _case()
    with pytest.raises(SeededSourceError, match="seeded_bundle_unknown"):
        attest_seeded_run_pdf(
            SESSION, run_id="run-seeded-01", bundle_id="unknown", manifest=MANIFEST,
            runs=runs, versions=versions, blobs=blobs,
        )
    altered = {**MANIFEST, "bundles": [*MANIFEST["bundles"], MANIFEST["bundles"][0]]}
    with pytest.raises(SeededSourceError, match="seeded_manifest_bundle_invalid"):
        attest_seeded_run_pdf(
            SESSION, run_id="run-seeded-01", bundle_id=bundle["id"], manifest=altered,
            runs=runs, versions=versions, blobs=blobs,
        )
    assert runs.calls == versions.calls == blobs.calls == 0
