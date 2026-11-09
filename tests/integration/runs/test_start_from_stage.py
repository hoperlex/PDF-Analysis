"""`R-151i` (`UI-A-60`, `D-301`): a run started from a stage reuses the earlier run's stage outputs, on the real services.

The source run is executed for real (recorded provider, the corpus PDF), then ``start_run_from_stage`` starts a new run from a
later stage and the executor runs it. What is measured:

* the new run takes the stages before the chosen one **by reference** -- the same artifact references, marked
  ``reused_from_run_id`` -- and publishes no blob for them, while the chosen stage and the later ones are computed;
* the source run is unchanged (its rows are byte-for-byte what they were), and it is linked by ``started_from_run_id`` and
  ``start_stage_id``, never by ``reaudit_of_run_id``;
* the findings the new run publishes are the findings a full run publishes (the recorded provider answers the same question);
* the key replays; another stage under the same key is refused; a second run in flight from the same source and stage is a
  conflict;
* every refusal of the reuse rule is typed and writes nothing, and the executor asks the rule again.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from auditmanager.findings import published_finding_count
from auditmanager.runs import PC01_STAGES, execute_run, start_audit_run
from auditmanager.runs.commands import start_run_from_stage
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.stage_reuse import REASONS, REUSED_FROM_METRIC
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId
from tests.support.v1_reference_profile import resolve_reference_profile

EXPERT = frozenset({"expert"})


def _execute(session, run_id, blob_store, recorded_adapter, provider_config):
    return execute_run(
        session, run_id, blob_store=blob_store, adapter=recorded_adapter,
        provider_config=provider_config, text_profiles=resolve_reference_profile,
    )


@pytest.fixture
def source(session, seeded, blob_store, recorded_adapter, provider_config, new_key):
    started = start_audit_run(
        session, version_uid=seeded.version_uid, analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="recorded", idempotency_key=new_key("from-stage-source"),
    )
    result = _execute(session, started.run_id, blob_store, recorded_adapter, provider_config)
    assert result.terminal_state == "published"
    return started.run_id


def _from_stage(session, seeded, source_run_id, stage_id, key, **extra):
    return start_run_from_stage(
        session, source_run_id=source_run_id, start_stage_id=stage_id, roles=EXPERT, idempotency_key=str(key),
        analysis_profile_id=seeded.analysis_profile_id, prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded", **extra,
    )


def _rows(session, run_id):
    return {
        row.stage_id: row for row in RunRepository().stage_results(session, run_id)
    }


def _source_snapshot(session, run_id):
    return (
        session.execute(text("SELECT to_jsonb(r) FROM audit_run r WHERE run_id = :r"), {"r": run_id}).scalar_one(),
        session.execute(text(
            "SELECT jsonb_agg(to_jsonb(s) ORDER BY stage_id) FROM stage_result s WHERE run_id = :r"), {"r": run_id}).scalar_one(),
        session.execute(text(
            "SELECT count(*) FROM analysis_artifact_publication WHERE run_id = :r"), {"r": run_id}).scalar_one(),
    )


def test_a_start_from_text_analysis_takes_the_three_earlier_stages_by_reference(
    session, seeded, blob_store, recorded_adapter, provider_config, new_key, source
):
    before = _source_snapshot(session, source)
    started = _from_stage(session, seeded, source, "text_analysis", new_key("from-text"))
    assert started.replayed is False
    run = RunRepository().get(session, started.run_id)
    assert (run.started_from_run_id, run.start_stage_id) == (source, "text_analysis")
    assert run.reaudit_of_run_id is None and run.state == "queued"

    result = _execute(session, started.run_id, blob_store, recorded_adapter, provider_config)
    assert result.terminal_state == "published" and set(result.stage_statuses) == set(PC01_STAGES)

    old, new = _rows(session, source), _rows(session, started.run_id)
    for stage_id in PC01_STAGES[:3]:
        assert new[stage_id].status == "succeeded"
        assert new[stage_id].artifacts == old[stage_id].artifacts, "the reused stage must hold the same artifact references"
        assert new[stage_id].metrics[REUSED_FROM_METRIC] == source
        assert REUSED_FROM_METRIC not in old[stage_id].metrics
    assert REUSED_FROM_METRIC not in new["text_analysis"].metrics
    # Only the computed stage published blobs under the new run's Attempt; the reused ones bound none.
    stages = set(session.execute(text(
        "SELECT DISTINCT stage_id FROM analysis_artifact_publication WHERE run_id = :r"), {"r": started.run_id}).scalars())
    assert stages == {"text_analysis"}
    # The source is exactly what it was, and the findings are the full run's.
    assert _source_snapshot(session, source) == before
    assert published_finding_count(session, started.run_id) == published_finding_count(session, source) > 0


def test_a_start_from_the_second_stage_takes_only_the_first(
    session, seeded, blob_store, recorded_adapter, provider_config, new_key, source
):
    started = _from_stage(session, seeded, source, "page_geometry_extraction", new_key("from-geometry"))
    result = _execute(session, started.run_id, blob_store, recorded_adapter, provider_config)
    assert result.terminal_state == "published"
    new = _rows(session, started.run_id)
    assert REUSED_FROM_METRIC in new["source_preparation"].metrics
    for stage_id in PC01_STAGES[1:]:
        assert REUSED_FROM_METRIC not in new[stage_id].metrics, stage_id


def test_the_key_replays_another_stage_under_it_is_refused_and_a_run_in_flight_blocks_a_second(
    session, seeded, new_key, source
):
    key = new_key("from-stage-key")
    first = _from_stage(session, seeded, source, "text_analysis", key)
    again = _from_stage(session, seeded, source, "text_analysis", key)
    assert again.replayed is True and again.run_id == first.run_id
    with pytest.raises(DomainError) as reuse:
        _from_stage(session, seeded, source, "document_context_build", key)
    assert reuse.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    with pytest.raises(DomainError) as busy:
        _from_stage(session, seeded, source, "text_analysis", new_key("from-stage-second"))
    assert busy.value.code is ErrorCode.CONFLICT
    # Another stage of the same source is another decision and is not blocked.
    _from_stage(session, seeded, source, "document_context_build", new_key("from-stage-other"))


@pytest.mark.parametrize("stage_id, constraint", [
    ("source_preparation", "nothing_to_reuse"), ("block_analysis", "stage_not_startable"), ("nonsense", "stage_not_startable"),
])
def test_a_stage_that_cannot_be_started_from_is_refused_before_anything_is_read(
    session, seeded, new_key, source, stage_id, constraint
):
    with pytest.raises(DomainError) as refusal:
        _from_stage(session, seeded, source, stage_id, new_key("from-bad-stage"))
    assert refusal.value.code is ErrorCode.VALIDATION_FAILED
    assert refusal.value.detail_fields["constraint"] == constraint


def test_a_source_that_has_not_ended_has_nothing_to_take(session, seeded, new_key):
    run_id = str(RunId.new())
    repository = RunRepository()
    repository.create(
        session, run_id=run_id, project_uid=seeded.project_uid, version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id, prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded", frozen_input_digest="a" * 64, command_id=None,
    )
    repository.advance(session, run_id=run_id, from_state="created", to_state="queued")
    with pytest.raises(DomainError) as refusal:
        _from_stage(session, seeded, run_id, "text_analysis", new_key("from-open-run"))
    assert refusal.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED


def _tamper(session, run_id, stage_id, **columns):
    sets = ", ".join(f"{name} = {expression}" for name, expression in columns.items())
    session.execute(text(f"UPDATE stage_result SET {sets} WHERE run_id = :r AND stage_id = :s"), {"r": run_id, "s": stage_id})


@pytest.mark.parametrize("stage_id, tamper, reason", [
    ("page_geometry_extraction", {"stage_version": "'0.9.0'"}, "source_stage_version_changed"),
    ("source_preparation", {"artifacts": "'[]'::jsonb"}, "source_stage_output_incomplete"),
    ("document_context_build", {"artifacts": "jsonb_set(artifacts, '{0,sha256}', to_jsonb(repeat('0', 64)))"},
     "source_artifact_changed"),
])
def test_every_unusable_output_is_a_typed_refusal_that_writes_nothing(
    session, seeded, new_key, source, stage_id, tamper, reason
):
    _tamper(session, source, stage_id, **tamper)
    runs_before = session.execute(text("SELECT count(*) FROM audit_run")).scalar_one()
    with pytest.raises(DomainError) as refusal:
        _from_stage(session, seeded, source, "text_analysis", new_key("from-tampered"))
    assert refusal.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert (refusal.value.detail_fields["stage_id"], refusal.value.detail_fields["reason"]) == (stage_id, reason)
    assert reason in REASONS
    assert session.execute(text("SELECT count(*) FROM audit_run")).scalar_one() == runs_before


def test_a_stage_the_source_never_completed_is_refused(session, seeded, new_key, source):
    session.execute(text("DELETE FROM stage_result WHERE run_id = :r AND stage_id = 'page_geometry_extraction'"), {"r": source})
    with pytest.raises(DomainError) as refusal:
        _from_stage(session, seeded, source, "document_context_build", new_key("from-missing"))
    assert refusal.value.detail_fields["reason"] == "source_stage_not_completed"
    assert refusal.value.detail_fields["stage_id"] == "page_geometry_extraction"


def test_the_executor_asks_the_rule_again_and_does_not_recompute(
    session, seeded, blob_store, recorded_adapter, provider_config, new_key, source
):
    """The start was accepted; then the source's output stopped being usable. The run fails; nothing is computed in place."""
    started = _from_stage(session, seeded, source, "text_analysis", new_key("from-changed-after"))
    _tamper(session, source, "source_preparation", stage_version="'0.9.0'")
    with pytest.raises(DomainError) as refusal:
        _execute(session, started.run_id, blob_store, recorded_adapter, provider_config)
    assert refusal.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert refusal.value.detail_fields["reason"] == "source_stage_version_changed"
    assert _rows(session, started.run_id) == {}, "a refused reuse must leave no stage row"
