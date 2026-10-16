"""Real DB/S3 acceptance of the explicit offline recorded AR v2 executor bridge."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from auditmanager.analysis.public import (
    AR_V2_RECORDED_BUNDLE_ID,
    AR_V2_RECORDED_PROFILE_ID,
    ROLE_SOURCE_DOCUMENT,
    ROLE_TEXT_LAYER,
    RecordedGenerationSettings,
    StageStatus,
    prepare_recorded_v2_input,
    read_artifact,
    run_stage,
)
from auditmanager.analysis.text.recorded import RecordedAdapter, recording_document
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey
from auditmanager.storage.public import parse_blob_id
from tests.integration.runs.test_v2_recorded_executor_bridge import (
    _Documents, _Jobs, _Runs, _Session, _config, _run,
)


MODEL_ID = "fixture/ar-v2-recorded"
SETTINGS = RecordedGenerationSettings(4096, "high", {"type": "adaptive"})
FIVE_STAGES = (
    "source_preparation",
    "page_geometry_extraction",
    "document_context_build",
    "text_analysis",
    "finding_merge",
)


def _write_exact_recording(tmp_path: Path, *, seeded, blob_store) -> str:
    """Derive the fixture from the real deterministic source stage's bytes."""
    source = run_stage(
        "source_preparation",
        version_uid=seeded.version_uid,
        inputs={ROLE_SOURCE_DOCUMENT: parse_blob_id(seeded.source_blob_id)},
        blob_store=blob_store,
    )
    assert source.status is StageStatus.SUCCEEDED
    text_ref = next(ref for ref in source.artifacts if ref.role == ROLE_TEXT_LAYER)
    text_document, text_digest = read_artifact(
        blob_store, parse_blob_id(text_ref.blob_id), expected_role=ROLE_TEXT_LAYER,
    )
    assert text_digest == text_ref.sha256
    prepared = prepare_recorded_v2_input(
        version_uid=seeded.version_uid,
        textless_pages=None,
        text_layer_document=text_document,
        text_layer_ref=text_ref,
        text_layer_read_sha256=text_digest,
        recognised_document=None,
        recognised_ref=None,
        recognised_read_sha256=None,
        analysis_profile_id=AR_V2_RECORDED_PROFILE_ID,
        prompt_bundle_id=AR_V2_RECORDED_BUNDLE_ID,
        fixture_model_id=MODEL_ID,
        settings=SETTINGS,
    )
    first_page = prepared.text_layer.pages[0]
    quote = first_page.text.splitlines()[0].strip()
    assert len(quote) > 20 and prepared.text_layer.document_text.count(quote) == 1
    recording = recording_document(
        request=prepared.request,
        output_text=json.dumps({"observations": [{
            "category": "documentation",
            "finding_text": "Проверить согласованность титульного листа",
            "recommendation_text": "Сверить данные комплекта с другими листами",
            "proposed_severity": "recommendation",
            "evidence": [{"page_number": first_page.page_number, "quote": quote}],
        }]}, ensure_ascii=False),
        stop_reason="end_turn",
        input_tokens=100,
        output_tokens=40,
        latency_ms=5,
        note="offline executor DB/S3 acceptance",
    )
    (tmp_path / f"{prepared.request_sha256}.json").write_text(
        json.dumps(recording, ensure_ascii=False), encoding="utf-8",
    )
    return prepared.request_sha256


def _counts(session, run_id: str) -> tuple[int, int, int, int, int, int]:
    return tuple(session.execute(text(
        "SELECT "
        "(SELECT count(*) FROM stage_result WHERE run_id = :run_id), "
        "(SELECT count(*) FROM model_call WHERE run_id = :run_id), "
        "(SELECT count(*) FROM job WHERE run_id = :run_id), "
        "(SELECT count(*) FROM attempt a JOIN job j ON j.job_id = a.job_id "
        " WHERE j.run_id = :run_id), "
        "(SELECT count(*) FROM finding WHERE allocated_by_run_id = :run_id), "
        "(SELECT count(*) FROM finding_observation WHERE run_id = :run_id)"
    ), {"run_id": run_id}).one())


def test_persisted_recorded_executor_saves_five_stages_one_call_and_one_terminal(
    sessions, blob_store, helpers, provider_config, tmp_path: Path,
) -> None:
    with sessions() as setup:
        assert setup.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0022_findings_v2"
        )
        seeded = helpers.seed_version(setup, blob_store)
        key = IdempotencyKey(f"w56a-bridge-{uuid.uuid4().hex}")
        started = start_audit_run(
            setup,
            version_uid=seeded.version_uid,
            analysis_profile_id=str(AR_V2_RECORDED_PROFILE_ID),
            prompt_bundle_id=str(AR_V2_RECORDED_BUNDLE_ID),
            provider_mode="recorded",
            idempotency_key=key,
        )
        assert started.replayed is False
        setup.commit()
    run_id = str(started.run_id)
    request_sha256 = _write_exact_recording(
        tmp_path, seeded=seeded, blob_store=blob_store,
    )
    adapter = RecordedAdapter(tmp_path)

    with sessions() as worker:
        result = execute_run(
            worker,
            run_id,
            blob_store=blob_store,
            adapter=adapter,
            provider_config=provider_config,
            recorded_fixture_model_id=MODEL_ID,
            recorded_generation_settings=SETTINGS,
        )
        assert result.terminal_state == "published"
        assert result.stage_statuses == dict.fromkeys(FIVE_STAGES, "succeeded")
        assert result.attempts == 1 and result.published_finding_count == 1
        assert result.diagnostic_count == 0 and result.gate_ran is True
        worker.commit()  # the gate's only final transaction boundary

    with sessions() as observer:
        rows = observer.execute(text(
            "SELECT stage_id, status, artifacts FROM stage_result WHERE run_id = :run_id"
        ), {"run_id": run_id}).mappings().all()
        stages = {str(row["stage_id"]): row for row in rows}
        assert len(rows) == 5 and set(stages) == set(FIVE_STAGES)
        assert all(row["status"] == "succeeded" for row in rows)
        call = observer.execute(text(
            "SELECT status, provider_mode, model_identity, request_sha256, "
            "response_sha256, cost_micros FROM model_call WHERE run_id = :run_id"
        ), {"run_id": run_id}).mappings().one()
        assert call["status"] == "succeeded"
        assert (call["provider_mode"], call["model_identity"]) == ("recorded", MODEL_ID)
        assert call["request_sha256"] == request_sha256
        assert call["response_sha256"] != request_sha256
        assert call["cost_micros"] is None
        terminal = observer.execute(text(
            "SELECT r.state, j.state AS job_state, a.state AS attempt_state, "
            "l.released_at IS NOT NULL AS lease_released "
            "FROM audit_run r JOIN job j ON j.run_id = r.run_id "
            "JOIN attempt a ON a.attempt_id = j.current_attempt_id "
            "JOIN lease l ON l.attempt_id = a.attempt_id WHERE r.run_id = :run_id"
        ), {"run_id": run_id}).one()
        assert tuple(terminal) == ("published", "succeeded", "succeeded", True)
        assert _counts(observer, run_id) == (5, 1, 1, 1, 1, 1)

        for stage_id, role in (
            ("source_preparation", "prepared.text_layer"),
            ("text_analysis", "analysis.text_observations"),
            ("finding_merge", "findings.merged"),
        ):
            refs = stages[stage_id]["artifacts"]
            ref = next(item for item in refs if item["role"] == role)
            payload = blob_store.read(parse_blob_id(ref["blob_id"]), verify=True)
            assert len(payload) == ref["size_bytes"]
            assert hashlib.sha256(payload).hexdigest() == ref["sha256"]
            assert json.loads(payload)["artifact_role"] == role

    with sessions() as retry:
        with pytest.raises(DomainError) as failure:
            execute_run(
                retry,
                run_id,
                blob_store=blob_store,
                adapter=adapter,
                provider_config=provider_config,
                recorded_fixture_model_id=MODEL_ID,
                recorded_generation_settings=SETTINGS,
            )
        assert failure.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
        retry.rollback()
    with sessions() as observer:
        assert _counts(observer, run_id) == (5, 1, 1, 1, 1, 1)


def test_recorded_source_read_starts_after_last_deterministic_bind_commit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """The final preparation Lease lock is released before the text port reads S3."""
    import auditmanager.runs.executor as executor
    import auditmanager.runs.recorded_v2_stage as recorded_text

    events: list[str] = []
    monkeypatch.setattr(executor, "start_attempt_lease_heartbeat", lambda *_a: None)
    monkeypatch.setattr(executor, "stop_attempt_lease_heartbeat", lambda: None)
    monkeypatch.setattr(executor, "_publication_store", lambda *_a, **_k: object())
    monkeypatch.setattr(executor, "_persist_and_bind", lambda *_a, **kw: (
        events.append(f"bind:{kw['result'].stage_id}")
    ))
    monkeypatch.setattr(executor, "run_stage", lambda stage_id, **_kw: SimpleNamespace(
        stage_id=stage_id, status=StageStatus.SUCCEEDED, artifacts=(),
    ))

    def source_read(_session, **_kwargs):
        assert events[-2:] == ["bind:document_context_build", "commit"]
        raise RuntimeError("source_read_boundary_reached")

    monkeypatch.setattr(recorded_text, "run_recorded_v2_stage", source_read)
    with pytest.raises(RuntimeError, match="source_read_boundary_reached"):
        execute_run(
            _Session(events), _run().run_id, blob_store=object(),
            adapter=RecordedAdapter(tmp_path), provider_config=_config(),
            runs=_Runs(_run(), events), jobs=_Jobs(events),
            documents=_Documents(), blob_metadata=object(),
            recorded_fixture_model_id=MODEL_ID,
            recorded_generation_settings=SETTINGS,
        )
