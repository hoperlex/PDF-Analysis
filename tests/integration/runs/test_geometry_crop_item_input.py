"""Current-Attempt Run read opens only one checked IMAGE crop PNG."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from auditmanager.runs.geometry_crop_item_input import load_saved_image_crop_item
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.runs.test_geometry_crop_input import (
    AUTHORITY,
    FakeDocuments,
    FakeJobs,
    FakeStore,
    _inputs,
)


def _block(runs, store, *, index=0) -> str:
    ref = next(
        raw for raw in runs.stage.artifacts if raw["role"] == "geometry.page_crops"
    )
    return json.loads(store.payloads[ref["blob_id"]])["crops"][index]["portal_block_id"]


def _load(runs, jobs, store, *, block=None, documents=None, metadata_cap=5_000_000,
          crop_cap=5_000_000):
    return load_saved_image_crop_item(
        object(), authority=AUTHORITY, blob_store=store,
        portal_block_id=block or _block(runs, store),
        max_metadata_bytes=metadata_cap, max_crop_bytes=crop_cap,
        runs=runs, jobs=jobs, documents=documents or FakeDocuments(),
    )


def test_reads_complete_metadata_and_only_selected_png_under_two_fences() -> None:
    runs, jobs, store = _inputs()
    documents = FakeDocuments()
    result = _load(runs, jobs, store, documents=documents)
    selected = result.checked.prepared.crop
    assert len(result.checked.prepared.cohort.crops) == 2
    assert store.read_ids == [
        result.portal_blocks_ref.blob_id,
        result.crop_manifest_ref.blob_id,
        selected.blob.blob_id,
    ]
    assert result.png_bytes == store.payloads[selected.blob.blob_id]
    assert result.checked.checked_blob_sha256 == (
        selected.blob.blob_id, hashlib.sha256(result.png_bytes).hexdigest(),
    )
    assert (jobs.calls, documents.calls) == (2, 2)
    assert runs.get_calls == [AUTHORITY.run_id, AUTHORITY.run_id]
    assert runs.stage_calls == [AUTHORITY.run_id, AUTHORITY.run_id]


def test_second_block_reads_only_its_png() -> None:
    runs, jobs, store = _inputs()
    block = _block(runs, store, index=1)
    result = _load(runs, jobs, store, block=block)
    assert result.checked.prepared.crop.portal_block_id == block
    assert len(store.read_ids) == 3
    assert store.read_ids[-1] == result.checked.prepared.crop.blob.blob_id


def test_unknown_block_and_wrong_version_source_digest_refuse_before_png() -> None:
    runs, jobs, store = _inputs()
    with pytest.raises(DomainError) as error:
        _load(runs, jobs, store, block="blk_" + "0" * 32)
    assert error.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert len(store.read_ids) == 2

    runs, jobs, store = _inputs()
    documents = FakeDocuments()
    documents.version.manifest = (replace(documents.entry, sha256="f" * 64),)
    with pytest.raises(DomainError) as error:
        _load(runs, jobs, store, documents=documents)
    assert error.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert len(store.read_ids) == 2


@pytest.mark.parametrize("change", ["missing", "extra"])
def test_missing_or_extra_saved_png_ref_refuses_without_png_read(change: str) -> None:
    runs, jobs, store = _inputs()
    artifacts = list(runs.stage.artifacts)
    crop_refs = [raw for raw in artifacts if raw["role"] == "geometry.crop_image"]
    if change == "missing":
        artifacts.remove(crop_refs[1])
    else:
        artifacts.append({**crop_refs[0], "blob_id": "blob_" + "9" * 26})
    runs.stage = runs.stage.__class__(
        stage_id=runs.stage.stage_id, stage_version=runs.stage.stage_version,
        status=runs.stage.status, artifacts=tuple(artifacts),
        metrics=runs.stage.metrics, error=runs.stage.error,
    )
    with pytest.raises(DomainError) as error:
        _load(runs, jobs, store)
    assert error.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert len(store.read_ids) == 2


def test_caps_refuse_before_metadata_or_selected_png_read() -> None:
    runs, jobs, store = _inputs()
    with pytest.raises(DomainError):
        _load(runs, jobs, store, metadata_cap=1)
    assert store.read_ids == []

    runs, jobs, store = _inputs()
    with pytest.raises(DomainError):
        _load(runs, jobs, store, crop_cap=1)
    assert len(store.read_ids) == 2


def test_corrupt_selected_bytes_and_final_stale_attempt_refuse() -> None:
    runs, jobs, store = _inputs()

    class LyingStore(FakeStore):
        def open_stream(self, blob_id, *, expected_sha256, expected_size, **kwargs):
            self.read_ids.append(blob_id)
            payload = self.payloads[blob_id]
            if blob_id == selected_id:
                yield payload[:-1] + b"x"
            else:
                yield payload

    selected_id = next(
        raw["blob_id"] for raw in runs.stage.artifacts
        if raw["role"] == "geometry.crop_image"
    )
    lying = LyingStore(store.payloads)
    with pytest.raises(DomainError) as error:
        _load(runs, jobs, lying)
    assert error.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert lying.read_ids[-1] == selected_id

    runs, jobs, store = _inputs()
    jobs.stale_on_recheck = True
    with pytest.raises(DomainError) as error:
        _load(runs, jobs, store)
    assert error.value.code is ErrorCode.STALE_ATTEMPT
    assert len(store.read_ids) == 3


def test_changed_stage_and_version_at_final_fence_refuse() -> None:
    runs, jobs, store = _inputs()
    runs.change_stage_after_first_read = True
    with pytest.raises(DomainError):
        _load(runs, jobs, store)
    assert len(store.read_ids) == 3

    runs, jobs, store = _inputs()
    documents = FakeDocuments()
    documents.change_manifest_after_first_read = True
    with pytest.raises(DomainError):
        _load(runs, jobs, store, documents=documents)
    assert len(store.read_ids) == 3
