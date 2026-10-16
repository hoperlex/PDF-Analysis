"""Run/Attempt fencing and real BlobStore-port reads for saved IMAGE crops."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from auditmanager.jobs.public import AttemptAuthority
from auditmanager.runs.geometry_crop_input import load_saved_image_crops
from auditmanager.runs.repository import StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobIntegrityError
from tests.integration.analysis.geometry.test_saved_crop_custody import RUN, VERSION, _fixture


AUTHORITY = AttemptAuthority(
    run_id=RUN,
    job_id="job_01ARZ3NDEKTSV4RRFFQ69G5FAV",
    attempt_id="att_01ARZ3NDEKTSV4RRFFQ69G5FAV",
    lease_id="lease_01ARZ3NDEKTSV4RRFFQ69G5FAV",
    execution_token="test-token",
)


class FakeRuns:
    def __init__(self, stage: StageResultRow):
        self.run = SimpleNamespace(run_id=RUN, version_uid=VERSION, state="running")
        self.stage = stage
        self.get_calls: list[str] = []
        self.stage_calls: list[str] = []
        self.change_stage_after_first_read = False
        self.change_run_after_first_read = False
        self.duplicate_stage = False

    def get(self, session: object, run_id: str):
        self.get_calls.append(run_id)
        if self.change_run_after_first_read and len(self.get_calls) > 1:
            return SimpleNamespace(run_id=RUN, version_uid=VERSION, state="cancelled")
        return self.run

    def stage_results(self, session: object, run_id: str):
        self.stage_calls.append(run_id)
        if self.change_stage_after_first_read and len(self.stage_calls) > 1:
            return (replace(self.stage, status="failed"),)
        if self.duplicate_stage:
            return (self.stage, self.stage)
        return (self.stage,)


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
    def __init__(self, payloads: dict[str, bytes]):
        self.payloads = payloads
        self.read_ids: list[str] = []

    def open_stream(
        self, blob_id: str, *, expected_sha256: str, expected_size: int,
        window: object = None, chunk_size: int = 0,
    ):
        self.read_ids.append(blob_id)
        payload = self.payloads.get(blob_id)
        if payload is None:
            raise BlobIntegrityError()
        # The fake uses the same external declaration check that the BlobStore
        # port promises; the pure verifier independently hashes each payload.
        import hashlib
        if len(payload) != expected_size or hashlib.sha256(payload).hexdigest() != expected_sha256:
            raise BlobIntegrityError()
        yield payload[:17]
        yield payload[17:]


def _inputs():
    stage, payloads = _fixture()
    row = StageResultRow(
        stage_id=stage.stage_id, stage_version=stage.stage_version,
        status=stage.status, artifacts=stage.artifacts,
        metrics={}, error=None,
    )
    return FakeRuns(row), FakeJobs(), FakeStore(payloads)


def _load(runs: FakeRuns, jobs: FakeJobs, store: FakeStore, *, ceiling: int = 5_000_000):
    return load_saved_image_crops(
        object(), authority=AUTHORITY, blob_store=store,
        max_input_bytes=ceiling, runs=runs, jobs=jobs,
    )


def test_reads_exact_saved_refs_and_returns_checked_crop_bytes() -> None:
    runs, jobs, store = _inputs()
    result = _load(runs, jobs, store)
    assert jobs.calls == 2
    assert runs.get_calls == [RUN, RUN]
    assert runs.stage_calls == [RUN, RUN]
    assert len(store.read_ids) == 4  # two JSON artifacts and two PNG crops
    assert set(store.read_ids) == set(store.payloads) - {
        next(
            raw["blob_id"] for raw in runs.stage.artifacts
            if raw["role"] == "geometry.block_index"
        )
    }
    assert len(result.crop_bytes) == len(result.checked.cohort.crops) == 2
    assert {blob_id for blob_id, _ in result.crop_bytes} == {
        crop.blob.blob_id for crop in result.checked.cohort.crops
    }


def test_stale_attempt_on_final_recheck_refuses_after_read() -> None:
    runs, jobs, store = _inputs()
    jobs.stale_on_recheck = True
    with pytest.raises(DomainError) as error:
        _load(runs, jobs, store)
    assert error.value.code == ErrorCode.STALE_ATTEMPT
    assert jobs.calls == 2


def test_changed_saved_stage_refuses_after_read() -> None:
    runs, jobs, store = _inputs()
    runs.change_stage_after_first_read = True
    with pytest.raises(DomainError) as error:
        _load(runs, jobs, store)
    assert error.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert jobs.calls == 2


def test_changed_run_refuses_after_read() -> None:
    runs, jobs, store = _inputs()
    runs.change_run_after_first_read = True
    with pytest.raises(DomainError) as error:
        _load(runs, jobs, store)
    assert error.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert jobs.calls == 2


def test_foreign_version_and_nonrunning_run_refuse_before_blob_read() -> None:
    runs, jobs, store = _inputs()
    runs.run.version_uid = "ver_" + "0" * 26
    with pytest.raises(DomainError) as error:
        _load(runs, jobs, store)
    assert error.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert jobs.calls == 1
    runs, jobs, store = _inputs()
    runs.run.state = "cancelled"
    with pytest.raises(DomainError) as error:
        _load(runs, jobs, store)
    assert error.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert store.read_ids == []


def test_explicit_byte_ceiling_refuses_before_any_blob_read() -> None:
    runs, jobs, store = _inputs()
    with pytest.raises(DomainError) as error:
        _load(runs, jobs, store, ceiling=50)
    assert error.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert store.read_ids == []


def test_corrupt_blob_refuses_whole_cohort() -> None:
    runs, jobs, store = _inputs()
    first_png = next(
        raw["blob_id"] for raw in runs.stage.artifacts
        if raw["role"] == "geometry.crop_image"
    )
    store.payloads[first_png] = store.payloads[first_png][:-1] + b"x"
    with pytest.raises(DomainError) as error:
        _load(runs, jobs, store)
    assert error.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert jobs.calls == 1


def test_missing_or_duplicate_stage_refuses_before_blob_read() -> None:
    runs, jobs, store = _inputs()
    runs.stage = replace(runs.stage, stage_id="source_preparation")
    with pytest.raises(DomainError) as error:
        _load(runs, jobs, store)
    assert error.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert store.read_ids == []
    runs, jobs, store = _inputs()
    runs.duplicate_stage = True
    with pytest.raises(DomainError) as error:
        _load(runs, jobs, store)
    assert error.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert store.read_ids == []
