"""Real PostgreSQL/MinIO proof of the unactivated recorded publication gate."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from auditmanager.analysis.public import (
    AR_V2_RECORDED_BUNDLE_ID, AR_V2_RECORDED_PROFILE_ID, ArtifactRef,
    RecordedGenerationSettings, StageError, StageResult, StageStatus, blob_role_for,
    build_recorded_observation_artifact, canonical_bytes, default_registry,
    prepare_recorded_v2_input, replay_recorded_response, sha256_hex,
)
from auditmanager.analysis.text.recorded import RecordedAdapter, recording_document
from auditmanager.jobs.public import JobRepository
from auditmanager.runs.recorded_v2_publication import (
    _stages, _terminal_without_plan, publish_recorded_v2_run,
)
from auditmanager.runs.repository import RunRepository, RunRow, StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import FindingObservationId, FindingUid, ModelCallId, RunId
from tests.support.expected_facts import FACTS


def test_saved_stage_statuses_choose_a_failure_without_blob_access() -> None:
    plan = tuple((
        "source_preparation", "page_geometry_extraction",
        "document_context_build", "text_analysis", "finding_merge",
    ))
    source = StageResultRow(
        "source_preparation", default_registry().stage("source_preparation").stage_version,
        "succeeded", (), {}, None,
    )
    stages = _stages((source,), plan)
    selected = _terminal_without_plan(stages, plan)
    assert selected is not None and selected.state == "failed"
    assert selected.degradation_set == plan[1:]

    failed = StageResultRow(
        "text_analysis", default_registry().stage("text_analysis").stage_version,
        "failed", (), {}, {"code": "analysis_failed"},
    )
    complete = tuple(
        failed if stage == "text_analysis" else StageResultRow(
            stage, default_registry().stage(stage).stage_version,
            "succeeded", (), {}, None,
        )
        for stage in plan
    )
    stages = _stages(complete, plan)
    selected = _terminal_without_plan(stages, plan)
    assert selected is not None and selected.state == "failed"
    assert selected.degradation_set == ("text_analysis",)


def test_blob_plan_precedes_run_lock_and_lease_finish_follows_publication(
    monkeypatch,
) -> None:
    import auditmanager.runs.recorded_v2_publication as gate

    events: list[str] = []
    run_id = str(RunId.new())
    source = RunRow(
        run_id, "prj_01M2545JSD15ETSNNV904X991J",
        "ver_01M2545JSD15ETSNNV904X991J", "running",
        str(AR_V2_RECORDED_PROFILE_ID), str(AR_V2_RECORDED_BUNDLE_ID),
        None, "recorded", "a" * 64, None, None, None, None, (),
        datetime.now(timezone.utc), None,
    )
    authority = SimpleNamespace(run_id=run_id, job_id="job_1")
    refs = {
        "source_preparation": ArtifactRef(
            "prepared.text_layer", "blob_" + "0" * 26, "a" * 64, 1, "application/json",
        ),
        "text_analysis": ArtifactRef(
            "analysis.text_observations", "blob_" + "1" * 26,
            "b" * 64, 1, "application/json",
        ),
        "finding_merge": ArtifactRef(
            "findings.merged", "blob_" + "2" * 26,
            "c" * 64, 1, "application/json",
        ),
    }
    rows = tuple(StageResultRow(
        stage, default_registry().stage(stage).stage_version,
        "succeeded", () if stage not in refs else (refs[stage].to_document(),),
        ({"provider_mode": "recorded", "model_call_count": 1}
         if stage == "text_analysis" else
         {"text_artifact_sha256": "b" * 64} if stage == "finding_merge" else {}),
        None,
    ) for stage in (
        "source_preparation", "page_geometry_extraction",
        "document_context_build", "text_analysis", "finding_merge",
    ))

    class Runs:
        state = "running"

        def get(self, _session, _run_id):
            return replace(source, state=self.state)

        def stage_results(self, _session, _run_id):
            return rows

        def advance(self, _session, **_kwargs):
            events.append("run_lock")
            self.state = "validating"

        def terminate(self, _session, **_kwargs):
            events.append("terminate")

    class Jobs:
        def completed_recorded_call(self, _session, **_kwargs):
            return SimpleNamespace(
                model_call_id="mc_01M2545JSD15ETSNNV904X991J",
                model_id="fixture/ar-v2-recorded",
                request_sha256="d" * 64, response_sha256="e" * 64,
            )

        def finish_execution(self, _session, *_args, **_kwargs):
            events.append("lease_finish")

    monkeypatch.setattr(gate, "plan_recorded_saved_publication", lambda *_a, **_k: (
        events.append("blob_read"), SimpleNamespace(plan=object())
    )[1])
    monkeypatch.setattr(gate, "publication_rows_exist", lambda *_a: False)
    monkeypatch.setattr(gate, "publish_v2_merge_plan", lambda *_a, **_k: (
        events.append("finding_write"), SimpleNamespace(
            finding_count=0, observation_count=0, rejected=(),
        )
    )[1])
    result = gate.publish_recorded_v2_run(
        object(), authority=authority, blob_store=object(),
        runs=Runs(), jobs=Jobs(),
        documents=SimpleNamespace(get_version=lambda *_a: SimpleNamespace(
            project_uid=source.project_uid, textless_pages=None,
        )),
    )
    assert result.selection.state == "published" and result.finding_count == 0
    assert events == ["blob_read", "run_lock", "finding_write", "terminate", "lease_finish"]


def _publish(blob_store, *, role: str, document: dict) -> ArtifactRef:
    payload = canonical_bytes(document)
    published = blob_store.put_blob(
        payload, declared_sha256=sha256_hex(payload), declared_size=len(payload),
        role=blob_role_for(role), media_type="application/json",
    )
    return ArtifactRef(
        role=role, blob_id=str(published.blob_id), sha256=published.sha256,
        size_bytes=published.size, media_type="application/json",
    )


def _stage(session, runs: RunRepository, run_id: str, stage_id: str, *,
           artifacts: tuple[ArtifactRef, ...] = (), metrics: dict | None = None,
           status: StageStatus = StageStatus.SUCCEEDED) -> None:
    result = StageResult(
        stage_id, default_registry().stage(stage_id).stage_version, status,
        artifacts, metrics or {},
    )
    runs.record_stage_result(session, run_id=run_id, document=result.to_document())


def _case(sessions, blob_store, helpers, tmp_path: Path, *, finding: bool,
          tamper: str | None = None):
    with sessions() as session:
        assert session.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            FACTS.migration_head
        )
        seeded = helpers.seed_version(session, blob_store)
        run_id = str(RunId.new())
        runs = RunRepository()
        jobs = JobRepository()
        runs.create(
            session, run_id=run_id, project_uid=seeded.project_uid,
            version_uid=seeded.version_uid,
            analysis_profile_id=str(AR_V2_RECORDED_PROFILE_ID),
            prompt_bundle_id=str(AR_V2_RECORDED_BUNDLE_ID),
            provider_mode="recorded", frozen_input_digest="a" * 64,
            command_id=None,
        )
        runs.advance(session, run_id=run_id, from_state="created", to_state="queued")
        jobs.enqueue(session, run_id=run_id)
        session.commit()
        authority = jobs.start_execution(session, run_id=run_id)
        runs.advance(session, run_id=run_id, from_state="queued", to_state="running")
        session.commit()

        source_text = "Стена: 200 мм"
        text_document = {
            "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0",
            "version_uid": seeded.version_uid, "normalization": {"id": "NFC"},
            "pages": [{"page_number": 1, "char_start": 0,
                       "char_end": len(source_text), "text": source_text}],
            "total_char_count": len(source_text),
        }
        text_ref = _publish(blob_store, role="prepared.text_layer", document=text_document)
        settings = RecordedGenerationSettings(4096, "high", {"type": "adaptive"})
        model_id = "fixture/ar-v2-recorded"
        prepared = prepare_recorded_v2_input(
            version_uid=seeded.version_uid, textless_pages=None,
            text_layer_document=text_document, text_layer_ref=text_ref,
            text_layer_read_sha256=text_ref.sha256,
            recognised_document=None, recognised_ref=None,
            recognised_read_sha256=None,
            analysis_profile_id=AR_V2_RECORDED_PROFILE_ID,
            prompt_bundle_id=AR_V2_RECORDED_BUNDLE_ID,
            fixture_model_id=model_id, settings=settings,
        )
        proposals = []
        if finding:
            proposals = [{
                "category": "dimensions", "finding_text": "Размер стены",
                "recommendation_text": "Проверить", "proposed_severity": "operational",
                "evidence": [{"page_number": 1, "quote": source_text}],
            }]
        recording = recording_document(
            request=prepared.request,
            output_text=json.dumps({"observations": proposals}, ensure_ascii=False),
            stop_reason="end_turn", input_tokens=100, output_tokens=40,
            latency_ms=5, note="offline gate test",
        )
        (tmp_path / f"{prepared.request_sha256}.json").write_text(
            json.dumps(recording, ensure_ascii=False), encoding="utf-8",
        )
        replay = replay_recorded_response(
            prepared=prepared, adapter=RecordedAdapter(tmp_path),
            expected_request_sha256=prepared.request_sha256,
            expected_model_id=model_id,
            expected_source_binding_sha256=prepared.source_binding_sha256,
        )
        call_id = jobs.prepare_provider_call(
            session, authority, provider="anthropic", model_identity=model_id,
            provider_mode="recorded", parameters={},
            request_sha256=prepared.request_sha256,
        )
        session.commit()
        jobs.record_provider_response(
            session, authority, model_call_id=call_id,
            response_sha256=replay.response_sha256,
            input_tokens=100, output_tokens=40, latency_ms=5,
        )
        jobs.complete_provider_call(session, authority, call={
            "model_call_id": str(call_id), "provider": "anthropic",
            "model_id": model_id, "provider_mode": "recorded", "parameters": {},
            "request_sha256": prepared.request_sha256,
            "response_sha256": replay.response_sha256,
            "input_tokens": 100, "output_tokens": 40, "latency_ms": 5,
            "status": "succeeded", "cost_usd": None, "cost_basis": "estimated",
        })
        session.commit()
        built = build_recorded_observation_artifact(
            prepared=prepared, replay=replay, run_id=run_id,
            model_call_id=str(call_id),
            analysis_profile_id=str(AR_V2_RECORDED_PROFILE_ID),
            prompt_bundle_id=str(AR_V2_RECORDED_BUNDLE_ID),
        )
        observation_document = json.loads(built.payload)
        if tamper == "model_id":
            observation_document["model_id"] = "fixture/other-recorded-model"
        elif tamper == "model_call_id":
            observation_document["model_call_id"] = str(ModelCallId.new())
        elif tamper == "source_binding_sha256":
            observation_document["source_binding_sha256"] = "f" * 64
        elif tamper is not None:
            raise AssertionError(f"unknown tamper case: {tamper}")
        observation_ref = _publish(
            blob_store, role=built.role, document=observation_document,
        )
        merge_document = replay.finished.merge.artifact
        merge_ref = _publish(blob_store, role="findings.merged", document=merge_document)
        _stage(session, runs, run_id, "source_preparation", artifacts=(text_ref,))
        _stage(session, runs, run_id, "page_geometry_extraction")
        _stage(session, runs, run_id, "document_context_build")
        _stage(session, runs, run_id, "text_analysis", artifacts=(observation_ref,),
               metrics={"provider_mode": "recorded", "model_call_count": 1})
        _stage(session, runs, run_id, "finding_merge", artifacts=(merge_ref,),
               metrics={"text_artifact_sha256": observation_ref.sha256,
                        "observation_count": len(replay.finished.grounding.accepted),
                        "group_count": len(merge_document["groups"])})
        session.commit()
    return run_id, authority


@pytest.mark.parametrize("finding", [False, True])
def test_committed_gate_is_once_only_including_zero_findings(
    sessions, blob_store, helpers, tmp_path, finding,
) -> None:
    run_id, authority = _case(sessions, blob_store, helpers, tmp_path, finding=finding)
    with sessions() as session:
        result = publish_recorded_v2_run(
            session, authority=authority, blob_store=blob_store,
        )
        assert result.selection.state == "published"
        assert result.finding_count == int(finding)
        session.commit()
    with sessions() as observer:
        row = observer.execute(text(
            "SELECT r.state, j.state, a.state, l.released_at IS NOT NULL "
            "FROM audit_run r JOIN job j ON j.run_id = r.run_id "
            "JOIN attempt a ON a.attempt_id = j.current_attempt_id "
            "JOIN lease l ON l.attempt_id = a.attempt_id WHERE r.run_id = :run_id"
        ), {"run_id": run_id}).one()
        assert tuple(row) == ("published", "succeeded", "succeeded", True)
        counts = observer.execute(text(
            "SELECT (SELECT count(*) FROM finding WHERE allocated_by_run_id = :run_id), "
            "(SELECT count(*) FROM finding_observation WHERE run_id = :run_id)"
        ), {"run_id": run_id}).one()
        assert tuple(counts) == (int(finding), int(finding))
        with pytest.raises(DomainError):
            publish_recorded_v2_run(observer, authority=authority, blob_store=blob_store)
        observer.rollback()
    with sessions() as observer:
        assert observer.execute(text(
            "SELECT count(*) FROM finding WHERE allocated_by_run_id = :run_id"
        ), {"run_id": run_id}).scalar_one() == int(finding)


def test_rollback_before_commit_leaves_running_run_and_no_findings(
    sessions, blob_store, helpers, tmp_path,
) -> None:
    run_id, authority = _case(sessions, blob_store, helpers, tmp_path, finding=True)
    with sessions() as session:
        result = publish_recorded_v2_run(
            session, authority=authority, blob_store=blob_store,
        )
        assert result.finding_count == 1
        session.rollback()  # process loss before the final commit
    with sessions() as observer:
        state = observer.execute(text(
            "SELECT state FROM audit_run WHERE run_id = :run_id"
        ), {"run_id": run_id}).scalar_one()
        count = observer.execute(text(
            "SELECT count(*) FROM finding WHERE allocated_by_run_id = :run_id"
        ), {"run_id": run_id}).scalar_one()
        assert (state, count) == ("running", 0)
        replayed = publish_recorded_v2_run(
            observer, authority=authority, blob_store=blob_store,
        )
        assert replayed.finding_count == 1
        observer.commit()


def test_stale_attempt_rolls_back_transient_finding_rows(
    sessions, blob_store, helpers, tmp_path,
) -> None:
    run_id, stale = _case(sessions, blob_store, helpers, tmp_path, finding=True)
    with sessions() as session:
        session.execute(text(
            "UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' "
            "WHERE lease_id = :lease_id"
        ), {"lease_id": stale.lease_id})
        jobs = JobRepository()
        assert jobs.reclaim_expired(session) >= 1
        session.commit()
        current = jobs.start_execution(session, run_id=run_id)
        session.commit()
    with sessions() as session:
        with pytest.raises(DomainError):
            publish_recorded_v2_run(
                session, authority=stale, blob_store=blob_store,
            )
        session.rollback()
    with sessions() as session:
        assert session.execute(text(
            "SELECT state FROM audit_run WHERE run_id = :run_id"
        ), {"run_id": run_id}).scalar_one() == "running"
        assert session.execute(text(
            "SELECT count(*) FROM finding WHERE allocated_by_run_id = :run_id"
        ), {"run_id": run_id}).scalar_one() == 0
        result = publish_recorded_v2_run(
            session, authority=current, blob_store=blob_store,
        )
        assert result.finding_count == 1
        session.commit()


def test_preexisting_running_finding_refuses_before_publication(
    sessions, blob_store, helpers, tmp_path,
) -> None:
    run_id, authority = _case(sessions, blob_store, helpers, tmp_path, finding=True)
    with sessions() as session:
        run = RunRepository().get(session, run_id)
        session.execute(text(
            "INSERT INTO finding (finding_uid, project_uid, version_uid, "
            "allocated_by_run_id, category) VALUES "
            "(:uid, :project_uid, :version_uid, :run_id, 'dimensions')"
        ), {"uid": str(FindingUid.new()), "project_uid": run.project_uid,
            "version_uid": run.version_uid, "run_id": run_id})
        with pytest.raises(DomainError):
            publish_recorded_v2_run(
                session, authority=authority, blob_store=blob_store,
            )
        session.rollback()
    with sessions() as observer:
        assert observer.execute(text(
            "SELECT state FROM audit_run WHERE run_id = :run_id"
        ), {"run_id": run_id}).scalar_one() == "running"


def test_failed_saved_stage_finishes_run_job_and_attempt_without_blob_read(
    sessions, blob_store, helpers, tmp_path,
) -> None:
    run_id, authority = _case(sessions, blob_store, helpers, tmp_path, finding=True)
    with sessions() as session:
        failed = StageResult(
            "text_analysis", default_registry().stage("text_analysis").stage_version,
            StageStatus.FAILED, error=StageError.from_domain_error(
                DomainError(ErrorCode.ANALYSIS_FAILED, message="saved stage failed")
            ),
        )
        RunRepository().record_stage_result(
            session, run_id=run_id, document=failed.to_document(),
        )
        session.commit()
    with sessions() as session:
        result = publish_recorded_v2_run(
            session, authority=authority, blob_store=object(),
        )
        assert result.selection.state == "failed"
        assert (result.finding_count, result.observation_count) == (0, 0)
        session.commit()
    with sessions() as session:
        row = session.execute(text(
            "SELECT r.state, r.terminal_reason, j.state, a.state, "
            "l.released_at IS NOT NULL "
            "FROM audit_run r JOIN job j ON j.run_id = r.run_id "
            "JOIN attempt a ON a.attempt_id = j.current_attempt_id "
            "JOIN lease l ON l.attempt_id = a.attempt_id WHERE r.run_id = :run_id"
        ), {"run_id": run_id}).one()
        assert tuple(row) == ("failed", "analysis_failed", "failed", "failed", True)
        assert session.execute(text(
            "SELECT count(*) FROM finding_observation WHERE run_id = :run_id"
        ), {"run_id": run_id}).scalar_one() == 0


def test_preexisting_observation_without_finding_refuses_publication(
    sessions, blob_store, helpers, tmp_path,
) -> None:
    run_id, authority = _case(sessions, blob_store, helpers, tmp_path, finding=True)
    with sessions() as session:
        session.execute(text(
            "INSERT INTO finding_observation (finding_observation_id, run_id, "
            "finding_uid, stage_id, category, finding_text, recommendation_text, "
            "grounded, ungrounded_reason, analysis_profile_id, prompt_bundle_id, "
            "provider_mode) VALUES (:observation_id, :run_id, NULL, "
            "'text_analysis', 'explicit_placeholder', 'TBD found', "
            "'Complete the field', false, 'quotation_absent', :profile_id, "
            ":bundle_id, 'recorded')"
        ), {"observation_id": str(FindingObservationId.new()), "run_id": run_id,
            "profile_id": str(AR_V2_RECORDED_PROFILE_ID),
            "bundle_id": str(AR_V2_RECORDED_BUNDLE_ID)})
        session.commit()
    with sessions() as session:
        with pytest.raises(DomainError):
            publish_recorded_v2_run(
                session, authority=authority, blob_store=blob_store,
            )
        session.rollback()
    with sessions() as observer:
        assert observer.execute(text(
            "SELECT state FROM audit_run WHERE run_id = :run_id"
        ), {"run_id": run_id}).scalar_one() == "running"
        assert observer.execute(text(
            "SELECT count(*) FROM finding WHERE allocated_by_run_id = :run_id"
        ), {"run_id": run_id}).scalar_one() == 0


@pytest.mark.parametrize("tamper", ["model_id", "model_call_id", "source_binding_sha256"])
def test_saved_call_and_source_provenance_mismatch_refuses_before_run_lock(
    sessions, blob_store, helpers, tmp_path, tamper,
) -> None:
    run_id, authority = _case(
        sessions, blob_store, helpers, tmp_path, finding=False, tamper=tamper,
    )
    with sessions() as session:
        with pytest.raises(DomainError):
            publish_recorded_v2_run(
                session, authority=authority, blob_store=blob_store,
            )
        session.rollback()
    with sessions() as observer:
        assert observer.execute(text(
            "SELECT state FROM audit_run WHERE run_id = :run_id"
        ), {"run_id": run_id}).scalar_one() == "running"
        assert observer.execute(text(
            "SELECT count(*) FROM finding_observation WHERE run_id = :run_id"
        ), {"run_id": run_id}).scalar_one() == 0


def test_stage_result_committed_during_blob_read_is_rechecked_under_run_lock(
    sessions, blob_store, helpers, tmp_path, monkeypatch,
) -> None:
    import auditmanager.runs.recorded_v2_publication as gate

    run_id, authority = _case(sessions, blob_store, helpers, tmp_path, finding=True)
    original = gate.plan_recorded_saved_publication

    def plan_then_commit_stage_change(*args, **kwargs):
        planned = original(*args, **kwargs)
        # A second transaction commits while the first transaction has read
        # its DB snapshot and Blobs, but before it acquires the Run lock.
        with sessions() as writer:
            _stage(writer, RunRepository(), run_id, "page_geometry_extraction",
                   metrics={"changed_during_blob_read": True})
            writer.commit()
        return planned

    monkeypatch.setattr(gate, "plan_recorded_saved_publication", plan_then_commit_stage_change)
    with sessions() as session:
        with pytest.raises(DomainError):
            publish_recorded_v2_run(
                session, authority=authority, blob_store=blob_store,
            )
        session.rollback()
    with sessions() as observer:
        assert observer.execute(text(
            "SELECT state FROM audit_run WHERE run_id = :run_id"
        ), {"run_id": run_id}).scalar_one() == "running"
        assert observer.execute(text(
            "SELECT count(*) FROM finding WHERE allocated_by_run_id = :run_id"
        ), {"run_id": run_id}).scalar_one() == 0


def test_concurrent_zero_finding_gates_commit_only_one_terminal(
    sessions, blob_store, helpers, tmp_path,
) -> None:
    run_id, authority = _case(sessions, blob_store, helpers, tmp_path, finding=False)
    contender_at_cas = Event()

    class ContendingRuns(RunRepository):
        def advance(self, session, **kwargs):
            contender_at_cas.set()
            return super().advance(session, **kwargs)

    def contend() -> bool:
        with sessions() as session:
            try:
                publish_recorded_v2_run(
                    session, authority=authority, blob_store=blob_store,
                    runs=ContendingRuns(),
                )
            except DomainError:
                session.rollback()
                return False
            session.commit()
            return True

    with sessions() as first, ThreadPoolExecutor(max_workers=1) as pool:
        assert publish_recorded_v2_run(
            first, authority=authority, blob_store=blob_store,
        ).selection.state == "published"
        future = pool.submit(contend)
        assert contender_at_cas.wait(timeout=10)
        first.commit()
        assert future.result(timeout=10) is False
    with sessions() as observer:
        assert observer.execute(text(
            "SELECT state FROM audit_run WHERE run_id = :run_id"
        ), {"run_id": run_id}).scalar_one() == "published"
        assert observer.execute(text(
            "SELECT count(*) FROM finding WHERE allocated_by_run_id = :run_id"
        ), {"run_id": run_id}).scalar_one() == 0


def test_exception_after_finding_insert_rolls_back_whole_gate(
    sessions, blob_store, helpers, tmp_path, monkeypatch,
) -> None:
    run_id, authority = _case(sessions, blob_store, helpers, tmp_path, finding=True)

    def crash_before_terminal(*_args, **_kwargs):
        raise RuntimeError("injected_before_terminal")

    with monkeypatch.context() as patch:
        patch.setattr(RunRepository, "terminate", crash_before_terminal)
        with sessions() as session:
            with pytest.raises(RuntimeError, match="injected_before_terminal"):
                publish_recorded_v2_run(
                    session, authority=authority, blob_store=blob_store,
                )
            session.rollback()
    with sessions() as session:
        state, findings = session.execute(text(
            "SELECT r.state, (SELECT count(*) FROM finding f "
            "WHERE f.allocated_by_run_id = r.run_id) "
            "FROM audit_run r WHERE r.run_id = :run_id"
        ), {"run_id": run_id}).one()
        assert (state, findings) == ("running", 0)
        assert publish_recorded_v2_run(
            session, authority=authority, blob_store=blob_store,
        ).finding_count == 1
        session.commit()
