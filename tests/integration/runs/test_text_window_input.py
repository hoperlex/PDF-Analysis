"""Saved W56b TEXT reads are fenced twice and use only the exact Blob ref."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import ArtifactRef, canonical_bytes, sha256_hex
from auditmanager.jobs.public import AttemptAuthority
from auditmanager.runs.repository import StageResultRow
from auditmanager.runs.text_window_input import load_saved_text_windows
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import VersionUid
from auditmanager.storage.public import BlobIntegrityError


RUN = "run_01M2545JSD15ETSNNV904X991J"
PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
VERSION = "ver_01M2545JSD15ETSNNV904X991J"
AUTHORITY = AttemptAuthority(
    run_id=RUN,
    job_id="job_01M2545JSD15ETSNNV904X991J",
    attempt_id="att_01M2545JSD15ETSNNV904X991J",
    lease_id="lease_01M2545JSD15ETSNNV904X991J",
    execution_token="test-token",
)


def _artifact(role: str, suffix: str, payload: bytes) -> ArtifactRef:
    return ArtifactRef(
        role=role,
        blob_id="blob_01M2545JSD15ETSNNV904X991" + suffix,
        sha256=sha256_hex(payload),
        size_bytes=len(payload),
        media_type="application/json",
    )


def _text_payload(*texts: str) -> bytes:
    pages = []
    offset = 0
    for number, body in enumerate(texts, start=1):
        pages.append({
            "page_number": number,
            "char_start": offset,
            "char_end": offset + len(body),
            "text": body,
        })
        offset += len(body)
    return canonical_bytes({
        "artifact_role": "prepared.text_layer",
        "artifact_version": "1.0.0",
        "version_uid": VERSION,
        "extractor": {
            "name": "fixture", "version": "1.0.0", "options_sha256": "a" * 64,
        },
        "normalization": {"id": "nfc_v1", "description": "NFC"},
        "total_char_count": offset,
        "pages": pages,
    })


class FakeRuns:
    def __init__(self, stage: StageResultRow):
        self.run = SimpleNamespace(
            run_id=RUN, version_uid=VERSION, project_uid=PROJECT, state="running"
        )
        self.stage = stage
        self.get_calls: list[str] = []
        self.stage_calls: list[str] = []
        self.change_run_after_read = False
        self.change_stage_after_read = False
        self.change_stage_ref_after_read = False
        self.duplicate_stage = False

    def get(self, session: object, run_id: str):
        self.get_calls.append(run_id)
        if self.change_run_after_read and len(self.get_calls) > 1:
            return SimpleNamespace(
                run_id=RUN, version_uid=VERSION, project_uid=PROJECT, state="cancelled"
            )
        return self.run

    def stage_results(self, session: object, run_id: str):
        self.stage_calls.append(run_id)
        if self.change_stage_after_read and len(self.stage_calls) > 1:
            return (replace(self.stage, status="failed"),)
        if self.change_stage_ref_after_read and len(self.stage_calls) > 1:
            inventory, text = self.stage.artifacts
            return (replace(
                self.stage,
                artifacts=(inventory, {**text, "sha256": "b" * 64}),
            ),)
        if self.duplicate_stage:
            return (self.stage, self.stage)
        return (self.stage,)


class FakeDocuments:
    def __init__(self):
        self.version = SimpleNamespace(
            version_uid=VersionUid.parse(VERSION), project_uid=PROJECT, page_count=3
        )
        self.calls: list[str] = []
        self.change_after_read = False

    def get_version(self, session: object, version_uid: VersionUid):
        self.calls.append(str(version_uid))
        if self.change_after_read and len(self.calls) > 1:
            return SimpleNamespace(
                version_uid=VersionUid.parse(VERSION), project_uid=PROJECT,
                page_count=4,
            )
        return self.version


class FakeJobs:
    def __init__(self):
        self.calls = 0
        self.stale_on_recheck = False

    def require_current(self, session: object, authority: AttemptAuthority) -> None:
        assert authority is AUTHORITY
        self.calls += 1
        if self.stale_on_recheck and self.calls == 2:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")


class FakeStore:
    def __init__(self, blob_id: str, payload: bytes):
        self.blob_id = blob_id
        self.payload = payload
        self.calls: list[tuple[str, str, int]] = []
        self.closed = False
        self.fail_integrity = False
        self.overrun = False

    def open_stream(self, blob_id, *, expected_sha256: str, expected_size: int):
        self.calls.append((str(blob_id), expected_sha256, expected_size))
        if self.fail_integrity or str(blob_id) != self.blob_id:
            raise BlobIntegrityError()
        if not self.overrun and (
            len(self.payload) != expected_size
            or sha256_hex(self.payload) != expected_sha256
        ):
            raise BlobIntegrityError()

        def chunks():
            try:
                yield self.payload[:17]
                yield self.payload[17:] + (b"x" if self.overrun else b"")
            finally:
                self.closed = True

        return chunks()


def _inputs(*texts: str):
    payload = _text_payload(*(texts or ("А😀", "", "БВ")))
    text_ref = _artifact("prepared.text_layer", "J", payload)
    inventory_ref = _artifact("prepared.page_inventory", "K", b"{}")
    stage = StageResultRow(
        stage_id="source_preparation", stage_version="1.0.0",
        status="succeeded",
        artifacts=(inventory_ref.to_document(), text_ref.to_document()),
        metrics={}, error=None,
    )
    return FakeRuns(stage), FakeJobs(), FakeDocuments(), FakeStore(text_ref.blob_id, payload), text_ref


def _load(runs, jobs, documents, store, *, byte_limit=50_000, text_limit=2):
    return load_saved_text_windows(
        object(), authority=AUTHORITY, blob_store=store,
        max_input_bytes=byte_limit, max_chunk_characters=text_limit,
        runs=runs, jobs=jobs, documents=documents,
    )


def test_exact_saved_blob_is_read_once_under_two_fences_and_checked() -> None:
    runs, jobs, documents, store, ref = _inputs()

    result = _load(runs, jobs, documents, store)

    assert jobs.calls == 2
    assert runs.get_calls == [RUN, RUN]
    assert runs.stage_calls == [RUN, RUN]
    assert documents.calls == [VERSION, VERSION]
    assert store.calls == [(ref.blob_id, ref.sha256, ref.size_bytes)]
    assert store.closed
    assert result.checked.source.text_layer.document_text == "А😀БВ"
    assert [(w.first_page, w.last_page, w.char_start, w.char_end)
            for w in result.checked.source.windows] == [(1, 2, 0, 2), (3, 3, 2, 4)]


def test_stale_attempt_on_second_fence_refuses_after_read() -> None:
    runs, jobs, documents, store, _ = _inputs()
    jobs.stale_on_recheck = True
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store)
    assert caught.value.code == ErrorCode.STALE_ATTEMPT
    assert jobs.calls == 2
    assert store.closed


@pytest.mark.parametrize("change", ["run", "version", "stage", "stage_ref"])
def test_changed_saved_input_refuses_after_read(change: str) -> None:
    runs, jobs, documents, store, _ = _inputs()
    if change == "run":
        runs.change_run_after_read = True
    elif change == "version":
        documents.change_after_read = True
    elif change == "stage_ref":
        runs.change_stage_ref_after_read = True
    else:
        runs.change_stage_after_read = True
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store)
    assert caught.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert jobs.calls == 2
    assert store.closed


def test_duplicate_or_unsuccessful_stage_refuses_before_blob_open() -> None:
    runs, jobs, documents, store, _ = _inputs()
    runs.duplicate_stage = True
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert store.calls == []
    runs, jobs, documents, store, _ = _inputs()
    runs.stage = replace(runs.stage, status="partial")
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert store.calls == []


def test_foreign_version_or_nonrunning_run_refuses_before_blob_open() -> None:
    runs, jobs, documents, store, _ = _inputs()
    documents.version.project_uid = "prj_01M2545JSD15ETSNNV904X991K"
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert store.calls == []
    runs, jobs, documents, store, _ = _inputs()
    runs.run.state = "cancelled"
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert store.calls == []


@pytest.mark.parametrize("limit", [0, True, 20])
def test_invalid_or_too_small_byte_ceiling_refuses_before_blob_open(limit: object) -> None:
    runs, jobs, documents, store, _ = _inputs()
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store, byte_limit=limit)
    assert caught.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert store.calls == []


@pytest.mark.parametrize("limit", [0, True])
def test_invalid_text_ceiling_refuses_before_blob_open(limit: object) -> None:
    runs, jobs, documents, store, _ = _inputs()
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store, text_limit=limit)
    assert caught.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert store.calls == []


def test_corrupt_or_overlong_stream_refuses_and_closes() -> None:
    runs, jobs, documents, store, _ = _inputs()
    store.fail_integrity = True
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert jobs.calls == 1
    runs, jobs, documents, store, _ = _inputs()
    store.overrun = True
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store)
    assert caught.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert jobs.calls == 1
    assert store.closed


def test_oversized_later_page_refuses_without_second_fence() -> None:
    runs, jobs, documents, store, _ = _inputs("А😀", "", "БВГ")
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store)
    assert caught.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert caught.value.detail_fields["reason"] == "page_exceeds_limit"
    assert jobs.calls == 1
