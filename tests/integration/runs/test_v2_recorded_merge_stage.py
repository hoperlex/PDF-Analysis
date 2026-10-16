"""Saved AR v2 text evidence becomes one durable deterministic merge stage."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from auditmanager.analysis.engine.result import ArtifactRef, StageStatus
from auditmanager.analysis.engine.serialization import canonical_bytes, sha256_hex
from auditmanager.analysis.public import AR_V2_RECORDED_BUNDLE_ID, AR_V2_RECORDED_PROFILE_ID
from auditmanager.jobs.public import AttemptAuthority
from auditmanager.runs import recorded_v2_merge as merge_stage
from auditmanager.runs.repository import StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import derive_blob_id
from tests.integration.analysis.test_ar_v2_recorded_artifact import (
    RUN, VERSION, _build, _prepared, _replay,
)


class _Session:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def commit(self) -> None:
        self.events.append("commit")


class _Runs:
    def __init__(self, events: list[str], reference: ArtifactRef,
                 source_reference: ArtifactRef,
                 recognised_reference: ArtifactRef | None = None,
                 *, already_merged: bool = False) -> None:
        self.events = events
        self.row = SimpleNamespace(
            state="running", provider_mode="recorded", version_uid=VERSION,
            analysis_profile_id=str(AR_V2_RECORDED_PROFILE_ID),
            prompt_bundle_id=str(AR_V2_RECORDED_BUNDLE_ID),
        )
        self.results = (StageResultRow(
            stage_id="source_preparation", stage_version="1.0.0", status="succeeded",
            artifacts=(source_reference.to_document(),) + (
                () if recognised_reference is None else (recognised_reference.to_document(),)
            ), metrics={}, error=None,
        ), StageResultRow(
            stage_id="text_analysis", stage_version="1.0.0", status="succeeded",
            artifacts=(reference.to_document(),), metrics={}, error=None,
        ))
        if already_merged:
            self.results += (StageResultRow(
                stage_id="finding_merge", stage_version="1.0.0", status="succeeded",
                artifacts=(), metrics={}, error=None,
            ),)

    def get(self, _session: _Session, _run_id: str):
        return self.row

    def stage_results(self, _session: _Session, _run_id: str):
        return self.results

    def stage_started(self, _session: _Session, *, run_id: str, stage_id: str) -> None:
        assert (run_id, stage_id) == (RUN, "finding_merge")
        self.events.append("stage_started")


class _Jobs:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def require_current(self, _session: _Session, _authority: AttemptAuthority) -> None:
        self.events.append("authority_checked")


class _Store:
    def __init__(self, events: list[str], text_payload: bytes, *, bad_readback: bool = False) -> None:
        self.events = events
        self.text_payload = text_payload
        self.merge_payload: bytes | None = None
        self.bad_readback = bad_readback

    def read(self, _blob_id, *, verify: bool = True) -> bytes:
        assert verify
        if self.merge_payload is None:
            self.events.append("text_read")
            return self.text_payload
        self.events.append("merge_readback")
        return b"wrong" if self.bad_readback else self.merge_payload

    def put_blob(self, payload: bytes, *, declared_sha256: str, declared_size: int,
                 role: str, media_type: str):
        assert role == "findings_merged" and media_type == "application/json"
        assert sha256_hex(payload) == declared_sha256 and len(payload) == declared_size
        self.events.append("merge_published")
        self.merge_payload = payload
        return SimpleNamespace(
            blob_id=derive_blob_id(sha256=declared_sha256, size=declared_size),
            sha256=declared_sha256, size=declared_size, media_type=media_type,
        )


def _exercise(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *,
              bad_readback: bool = False, already_merged: bool = False,
              payload_override: bytes | None = None, ocr_only: bool = False):
    prepared = _prepared(with_ocr=ocr_only)
    replay = _replay(tmp_path, prepared, ocr_only=ocr_only)
    built = _build(prepared, replay)
    # The stage must work from saved Blob evidence after the only recording is gone.
    (tmp_path / f"{prepared.request_sha256}.json").unlink()
    payload = built.payload if payload_override is None else payload_override
    reference = ArtifactRef(
        role=built.role,
        blob_id=str(derive_blob_id(sha256=sha256_hex(payload), size=len(payload))),
        sha256=sha256_hex(payload), size_bytes=len(payload),
        media_type=built.media_type,
    )
    events: list[str] = []
    runs = _Runs(events, reference, prepared.text_layer_ref, prepared.recognised_ref,
                 already_merged=already_merged)
    jobs = _Jobs(events)
    store = _Store(events, payload, bad_readback=bad_readback)
    session = _Session(events)
    monkeypatch.setattr(merge_stage, "_publication_store", lambda *_args, **_kw: store)
    bound: list[object] = []
    monkeypatch.setattr(merge_stage, "_persist_and_bind", lambda *_args, **kwargs: (
        events.append("merge_bound"), bound.append(kwargs["result"])
    ))
    first = datetime(2026, 10, 16, 8, 0, tzinfo=timezone.utc)
    times = iter((first, first + timedelta(seconds=1)))
    authority = AttemptAuthority(RUN, "job_1", "att_1", "lease_1", "token")

    def execute():
        return merge_stage.run_recorded_v2_merge_stage(
            session, authority=authority, blob_store=store,
            runs=runs, jobs=jobs, blobs=object(), clock=lambda: next(times),
        )

    return execute, events, bound, store, runs


def test_merge_uses_saved_text_blob_and_binds_only_after_exact_readback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    execute, events, bound, store, _runs = _exercise(monkeypatch, tmp_path)
    result = execute()
    assert result.status is StageStatus.SUCCEEDED
    assert result.stage_id == "finding_merge"
    assert result.artifacts[0].role == "findings.merged"
    assert result.metrics["group_count"] == 1
    assert result.metrics["observation_count"] == 1
    assert json.loads(store.merge_payload or b"{}")["groups"] == [{
        "observation_ordinals": [0], "canonical_ordinal": 0,
        "merge_rule_version": "1.0.0",
    }]
    assert events.index("text_read") < events.index("authority_checked")
    assert events.index("authority_checked") < events.index("stage_started")
    assert events.index("merge_published") < events.index("merge_readback")
    assert events.index("merge_readback") < events.index("merge_bound")
    assert events[-1] == "commit" and bound == [result]


def test_wrong_merge_readback_cannot_commit_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    execute, events, bound, _store, _runs = _exercise(monkeypatch, tmp_path, bad_readback=True)
    with pytest.raises(DomainError) as failure:
        execute()
    assert failure.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert "merge_published" in events and "merge_bound" not in events and not bound


def test_ocr_only_diagnostic_has_empty_successful_merge(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    execute, _events, _bound, store, _runs = _exercise(
        monkeypatch, tmp_path, ocr_only=True,
    )
    result = execute()
    assert result.status is StageStatus.SUCCEEDED
    assert result.metrics["group_count"] == 0
    assert result.metrics["observation_count"] == 0
    assert json.loads(store.merge_payload or b"{}")["groups"] == []


def test_saved_source_reference_mismatch_refuses_before_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    execute, events, bound, _store, runs = _exercise(monkeypatch, tmp_path)
    wrong = dict(runs.results[0].artifacts[0])
    wrong["sha256"] = "0" * 64
    runs.results = (StageResultRow(
        stage_id="source_preparation", stage_version="1.0.0", status="succeeded",
        artifacts=(wrong,), metrics={}, error=None,
    ), *runs.results[1:])
    with pytest.raises(DomainError) as failure:
        execute()
    assert failure.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert "stage_started" not in events and not bound


def test_text_blob_bytes_must_match_saved_reference(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    execute, events, bound, store, _runs = _exercise(monkeypatch, tmp_path)
    store.text_payload += b" "
    with pytest.raises(DomainError) as failure:
        execute()
    assert failure.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert "stage_started" not in events and "merge_published" not in events and not bound


def test_unreadable_saved_blob_is_a_typed_refusal_before_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    execute, events, bound, store, _runs = _exercise(monkeypatch, tmp_path)

    def unavailable(*_args, **_kwargs):
        raise OSError("unavailable")

    monkeypatch.setattr(store, "read", unavailable)
    with pytest.raises(DomainError) as failure:
        execute()
    assert failure.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert "stage_started" not in events and "merge_published" not in events and not bound


def test_duplicate_stage_refuses_before_read_or_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    execute, events, bound, _store, _runs = _exercise(monkeypatch, tmp_path, already_merged=True)
    with pytest.raises(DomainError) as failure:
        execute()
    assert failure.value.code is ErrorCode.CONFLICT
    assert "text_read" not in events and "merge_published" not in events and not bound


@pytest.mark.parametrize("change", ["truncated", "sparse_ordinal", "wrong_run"])
def test_invalid_saved_text_refuses_before_merge_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, change: str,
) -> None:
    prepared = _prepared()
    built = _build(prepared, _replay(tmp_path, prepared))
    document = json.loads(built.payload)
    if change == "truncated":
        document["diagnostics"]["truncated"] = True
    elif change == "sparse_ordinal":
        document["observations"][0]["observation_ordinal"] = 2
    else:
        document["run_id"] = "run_" + "0" * 26
    execute, events, bound, _store, _runs = _exercise(
        monkeypatch, tmp_path, payload_override=canonical_bytes(document),
    )
    with pytest.raises(DomainError) as failure:
        execute()
    assert failure.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert "stage_started" not in events and "merge_published" not in events and not bound
