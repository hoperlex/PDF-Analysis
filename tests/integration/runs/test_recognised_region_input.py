"""A saved OCR region needs exact dual-stage bytes and current Attempt custody."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import ArtifactRef, canonical_bytes, sha256_hex
from auditmanager.jobs.public import AttemptAuthority
from auditmanager.runs.recognised_region_input import load_saved_recognised_region
from auditmanager.runs.repository import StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import VersionUid
from auditmanager.storage.public import BlobIntegrityError


RUN = "run_01M2545JSD15ETSNNV904X991J"
PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
VERSION = "ver_01M2545JSD15ETSNNV904X991J"
BLOCK = "blk_" + "1" * 32
QUOTE = "плоская кровля"
AUTHORITY = AttemptAuthority(
    run_id=RUN,
    job_id="job_01M2545JSD15ETSNNV904X991J",
    attempt_id="att_01M2545JSD15ETSNNV904X991J",
    lease_id="lease_01M2545JSD15ETSNNV904X991J",
    execution_token="test-token",
)


def _ref(role: str, suffix: str, payload: bytes) -> ArtifactRef:
    return ArtifactRef(
        role=role,
        blob_id="blob_01M2545JSD15ETSNNV904X991" + suffix,
        sha256=sha256_hex(payload),
        size_bytes=len(payload),
        media_type="application/json",
    )


def _documents() -> tuple[dict, dict]:
    recognised = {
        "artifact_role": "prepared.recognised_text",
        "artifact_version": "1.0.0",
        "version_uid": VERSION,
        "results_sha256": "a" * 64,
        "entries": [{
            "portal_block_id": BLOCK,
            "page_number": 1,
            "kind": "recognised_text",
            "quote_source": "recognised",
            "text": f"АР: {QUOTE}; уклон 2%",
            "flags": [],
        }],
    }
    portal = {
        "artifact_role": "geometry.portal_blocks",
        "artifact_version": "1.0.0",
        "version_uid": VERSION,
        "blocks_sha256": "b" * 64,
        "pages": [{
            "page_number": 1, "width_px": 2000, "height_px": 1000,
            "rotation_deg": 0, "geometry": "ok",
        }],
        "blocks": [{
            "portal_block_id": BLOCK, "page_number": 1, "page_label": 1,
            "ordinal": 0, "block_type": "text", "status": "complete",
            "bbox_norm": [0.1, 0.2, 0.8, 0.7], "geometry": "ok",
        }],
    }
    return recognised, portal


class FakeRuns:
    def __init__(self, source: StageResultRow, geometry: StageResultRow):
        self.run = SimpleNamespace(
            run_id=RUN, project_uid=PROJECT, version_uid=VERSION, state="running",
        )
        self.source = source
        self.geometry = geometry
        self.get_calls: list[str] = []
        self.stage_calls: list[str] = []
        self.change_run = False
        self.change_source = False
        self.change_geometry = False
        self.duplicate_source = False

    def get(self, session: object, run_id: str):
        self.get_calls.append(run_id)
        if self.change_run and len(self.get_calls) > 1:
            return SimpleNamespace(
                run_id=RUN, project_uid=PROJECT, version_uid=VERSION, state="cancelled",
            )
        return self.run

    def stage_results(self, session: object, run_id: str):
        self.stage_calls.append(run_id)
        source, geometry = self.source, self.geometry
        if len(self.stage_calls) > 1:
            if self.change_source:
                source = replace(source, status="failed")
            if self.change_geometry:
                geometry = replace(geometry, artifacts=geometry.artifacts[:-1])
        return (source, source, geometry) if self.duplicate_source else (source, geometry)


class FakeDocuments:
    def __init__(self):
        self.version = SimpleNamespace(
            version_uid=VersionUid.parse(VERSION), project_uid=PROJECT,
            page_count=1, textless_pages=(1,),
        )
        self.calls: list[str] = []
        self.change_version = False

    def get_version(self, session: object, version_uid: VersionUid):
        self.calls.append(str(version_uid))
        if self.change_version and len(self.calls) > 1:
            return SimpleNamespace(
                version_uid=VersionUid.parse(VERSION), project_uid=PROJECT,
                page_count=1, textless_pages=(),
            )
        return self.version


class FakeJobs:
    def __init__(self):
        self.calls = 0
        self.stale_on_second = False

    def require_current(self, session: object, authority: AttemptAuthority) -> None:
        assert authority is AUTHORITY
        self.calls += 1
        if self.stale_on_second and self.calls == 2:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")


class FakeStore:
    def __init__(self, payloads: dict[str, bytes]):
        self.payloads = payloads
        self.calls: list[tuple[str, str, int]] = []
        self.closed = 0
        self.corrupt: str | None = None
        self.overrun: str | None = None

    def open_stream(self, blob_id, *, expected_sha256: str, expected_size: int):
        key = str(blob_id)
        self.calls.append((key, expected_sha256, expected_size))
        if key == self.corrupt:
            raise BlobIntegrityError()
        payload = self.payloads[key]
        if len(payload) != expected_size or sha256_hex(payload) != expected_sha256:
            raise BlobIntegrityError()

        def chunks():
            try:
                yield payload[:11]
                yield payload[11:] + (b"x" if key == self.overrun else b"")
            finally:
                self.closed += 1

        return chunks()


def _inputs():
    recognised, portal = _documents()
    recognised_bytes, portal_bytes = canonical_bytes(recognised), canonical_bytes(portal)
    recognised_ref = _ref("prepared.recognised_text", "J", recognised_bytes)
    portal_ref = _ref("geometry.portal_blocks", "K", portal_bytes)
    inventory_ref = _ref("prepared.page_inventory", "Q", b"{}")
    text_ref = _ref("prepared.text_layer", "M", b"{}")
    block_ref = _ref("geometry.block_index", "N", b"{}")
    crops_ref = _ref("geometry.page_crops", "P", b"{}")
    source = StageResultRow(
        stage_id="source_preparation", stage_version="1.0.0", status="succeeded",
        artifacts=tuple(ref.to_document() for ref in (
            inventory_ref, text_ref, recognised_ref,
        )), metrics={}, error=None,
    )
    geometry = StageResultRow(
        stage_id="page_geometry_extraction", stage_version="1.0.0", status="succeeded",
        artifacts=tuple(ref.to_document() for ref in (
            block_ref, crops_ref, portal_ref,
        )), metrics={}, error=None,
    )
    store = FakeStore({
        recognised_ref.blob_id: recognised_bytes,
        portal_ref.blob_id: portal_bytes,
    })
    return FakeRuns(source, geometry), FakeJobs(), FakeDocuments(), store, recognised_ref, portal_ref


def _load(runs, jobs, documents, store, *, max_bytes=10_000, **claim):
    fields = dict(portal_block_id=BLOCK, page_number=1, quote=QUOTE)
    fields.update(claim)
    return load_saved_recognised_region(
        object(), authority=AUTHORITY, blob_store=store,
        max_input_bytes=max_bytes, runs=runs, jobs=jobs,
        documents=documents, **fields,
    )


def test_exact_two_saved_artifacts_bind_one_textless_region_under_two_fences() -> None:
    runs, jobs, documents, store, recognised_ref, portal_ref = _inputs()

    result = _load(runs, jobs, documents, store)

    assert result.recognised_ref == recognised_ref
    assert result.portal_blocks_ref == portal_ref
    assert result.candidate.quote == QUOTE
    assert result.candidate.quote_source == "recognised"
    assert result.candidate.ocr_char_start == 4
    assert result.candidate.bbox_norm == (0.1, 0.2, 0.8, 0.7)
    assert store.calls == [
        (recognised_ref.blob_id, recognised_ref.sha256, recognised_ref.size_bytes),
        (portal_ref.blob_id, portal_ref.sha256, portal_ref.size_bytes),
    ]
    assert store.closed == 2
    assert jobs.calls == 2
    assert runs.get_calls == [RUN, RUN]
    assert runs.stage_calls == [RUN, RUN]
    assert documents.calls == [VERSION, VERSION]


def test_stale_second_attempt_refuses_after_both_reads() -> None:
    runs, jobs, documents, store, _, _ = _inputs()
    jobs.stale_on_second = True
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store)
    assert caught.value.code == ErrorCode.STALE_ATTEMPT
    assert store.closed == 2


@pytest.mark.parametrize("change", ["run", "version", "source", "geometry"])
def test_any_changed_saved_input_refuses_after_read(change: str) -> None:
    runs, jobs, documents, store, _, _ = _inputs()
    if change == "run":
        runs.change_run = True
    elif change == "version":
        documents.change_version = True
    elif change == "source":
        runs.change_source = True
    else:
        runs.change_geometry = True
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store)
    assert caught.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert jobs.calls == 2


def test_invalid_stage_and_ref_refuse_before_open() -> None:
    runs, jobs, documents, store, _, _ = _inputs()
    runs.duplicate_source = True
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert store.calls == []
    runs, jobs, documents, store, _, _ = _inputs()
    runs.geometry = replace(runs.geometry, status="partial")
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert store.calls == []
    runs, jobs, documents, store, _, _ = _inputs()
    refs = list(runs.source.artifacts)
    refs[-1] = {**refs[-1], "sha256": "z" * 64}
    runs.source = replace(runs.source, artifacts=tuple(refs))
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert store.calls == []


@pytest.mark.parametrize("limit", [0, True, 10])
def test_invalid_or_small_aggregate_byte_ceiling_refuses_before_open(limit: object) -> None:
    runs, jobs, documents, store, _, _ = _inputs()
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store, max_bytes=limit)
    assert caught.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert store.calls == []


def test_foreign_nonportal_or_nonrunning_run_refuses_before_open() -> None:
    runs, jobs, documents, store, _, _ = _inputs()
    documents.version.project_uid = "prj_01M2545JSD15ETSNNV904X991K"
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert store.calls == []
    runs, jobs, documents, store, _, _ = _inputs()
    documents.version.textless_pages = None
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert store.calls == []
    runs, jobs, documents, store, _, _ = _inputs()
    documents.version.textless_pages = (1, 2)
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert store.calls == []
    runs, jobs, documents, store, _, _ = _inputs()
    runs.run.state = "cancelled"
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert store.calls == []


def test_corrupt_or_overlong_blob_refuses_without_second_fence() -> None:
    runs, jobs, documents, store, _, portal_ref = _inputs()
    store.corrupt = portal_ref.blob_id
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert jobs.calls == 1
    runs, jobs, documents, store, recognised_ref, _ = _inputs()
    store.overrun = recognised_ref.blob_id
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert jobs.calls == 1
    assert store.closed == 1


def test_noncanonical_saved_document_refuses_after_exact_blob_read() -> None:
    runs, jobs, documents, store, _, portal_ref = _inputs()
    payload = b" " + store.payloads[portal_ref.blob_id]
    updated = _ref("geometry.portal_blocks", "K", payload)
    store.payloads[portal_ref.blob_id] = payload
    refs = list(runs.geometry.artifacts)
    refs[-1] = updated.to_document()
    runs.geometry = replace(runs.geometry, artifacts=tuple(refs))
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store)
    assert caught.value.detail_fields["reason"] == "saved_artifact_document_invalid"
    assert jobs.calls == 1
    assert store.closed == 2


def test_saved_portal_page_count_must_match_the_version() -> None:
    runs, jobs, documents, store, _, _ = _inputs()
    documents.version.page_count = 2
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store)
    assert caught.value.detail_fields["reason"] == "portal_page_count_mismatch"
    assert jobs.calls == 1


@pytest.mark.parametrize("claim", [
    {"page_number": 2},
    {"quote": "неизвестная цитата"},
])
def test_unbound_ocr_claim_refuses_without_second_fence(claim: dict) -> None:
    runs, jobs, documents, store, _, _ = _inputs()
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store, **claim)
    assert caught.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert jobs.calls == 1
