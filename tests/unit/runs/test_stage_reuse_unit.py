"""`R-151i` (`UI-A-60`): the reuse rule, run on stand-ins for the rows it reads.

Each refusal is shown once with the one fact that causes it changed and every other fact in order, and the plan that none of
them stops is shown to hold exactly the stages before the chosen one. A rule that refused nothing would pass a suite of
only the good case, so the planted differences come first.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from auditmanager.analysis.public import StageStatus, default_registry
from auditmanager.runs import stage_reuse
from auditmanager.runs.repository import PC01_STAGES, StageResultRow
from auditmanager.runs.stage_reuse import (
    REASONS,
    REUSED_FROM_METRIC,
    STARTABLE_STAGES,
    plan_stage_reuse,
    require_startable_stage,
    visual_only_pages_allowed,
)
from auditmanager.shared.errors import DomainError, ErrorCode

SOURCE = "run_01M5M28ZCDD8VPSP1BTAEW92YF"
SHA = "a" * 64


def _blob_id(index: int) -> str:
    return "blob_" + f"{index:026d}"


def _row(stage_id: str, index: int, *, status="succeeded", version=None, drop_role=None) -> StageResultRow:
    definition = default_registry().stage(stage_id)
    roles = [role for role in definition.required_output_roles if role != drop_role]
    return StageResultRow(
        stage_id=stage_id, stage_version=version or definition.stage_version, status=status,
        artifacts=tuple(
            {"role": role, "blob_id": _blob_id(index * 10 + n + 1), "sha256": SHA, "size_bytes": 7,
             "media_type": "application/json"} for n, role in enumerate(roles)),
        metrics={"pages": 3, "nested": {"dropped": True}, "note": "x"}, error=None,
        started_at=datetime(2026, 11, 9, tzinfo=timezone.utc), finished_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
    )


@dataclass
class _Runs:
    rows: dict[str, StageResultRow]

    def get(self, session, run_id):
        return object()

    def stage_results(self, session, run_id):
        return tuple(self.rows.values())


@dataclass
class _Record:
    sha256: str
    size_bytes: int
    is_available: bool = True


class _Blobs:
    def __init__(self, **overrides):
        self.overrides = overrides

    def get(self, session, blob_id):
        if "missing" in self.overrides:
            return None
        return _Record(self.overrides.get("sha256", SHA), self.overrides.get("size_bytes", 7),
                       self.overrides.get("available", True))


@pytest.fixture(autouse=True)
def _flag(monkeypatch):
    monkeypatch.setattr(stage_reuse, "run_visual_only_pages", lambda session, run_id, runs=None: False)


def _rows(**changes):
    rows = {stage_id: _row(stage_id, index) for index, stage_id in enumerate(PC01_STAGES)}
    rows.update(changes)
    return rows


def _plan(start, rows=None, blobs=None, visual=False):
    return plan_stage_reuse(
        None, source_run_id=SOURCE, start_stage_id=start, visual_only_pages=visual,
        runs=_Runs(rows or _rows()), blobs=blobs or _Blobs())


def _reason(**kwargs):
    with pytest.raises(DomainError) as refusal:
        _plan(**kwargs)
    assert refusal.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    return refusal.value.detail_fields["stage_id"], refusal.value.detail_fields["reason"]


def test_the_startable_stages_are_the_chain_after_its_first_stage():
    assert STARTABLE_STAGES == PC01_STAGES[1:] == (
        "page_geometry_extraction", "document_context_build", "text_analysis")


@pytest.mark.parametrize("stage_id, constraint", [
    ("source_preparation", "nothing_to_reuse"), ("block_analysis", "stage_not_startable"),
    ("finding_merge", "stage_not_startable"), ("", "stage_not_startable"), (None, "stage_not_startable"),
])
def test_a_stage_that_is_not_startable_is_a_validation_failure_on_stage_id(stage_id, constraint):
    with pytest.raises(DomainError) as refusal:
        require_startable_stage(stage_id)
    assert refusal.value.code is ErrorCode.VALIDATION_FAILED
    assert refusal.value.detail_fields == {"field": "stage_id", "constraint": constraint}


@pytest.mark.parametrize("start, taken", [
    ("page_geometry_extraction", ("source_preparation",)),
    ("document_context_build", ("source_preparation", "page_geometry_extraction")),
    ("text_analysis", ("source_preparation", "page_geometry_extraction", "document_context_build")),
])
def test_a_start_takes_exactly_the_stages_before_it_and_computes_the_rest(start, taken):
    plan = _plan(start)
    assert plan.reused_stage_ids == taken
    assert plan.computed_stage_ids == PC01_STAGES[len(taken):]
    assert set(plan.reused_stage_ids).isdisjoint(plan.computed_stage_ids)
    assert set(plan.reused_stage_ids) | set(plan.computed_stage_ids) == set(PC01_STAGES)


def test_a_reused_stage_is_a_succeeded_result_with_the_same_artifacts_marked_as_reused():
    reused = _plan("text_analysis").reused[1]
    at = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
    result = reused.as_stage_result(source_run_id=SOURCE, at=at)
    assert result.status is StageStatus.SUCCEEDED and result.error is None
    assert tuple(ref.to_document() for ref in result.artifacts) == tuple(_rows()[reused.stage_id].artifacts)
    assert result.metrics == {"pages": 3, "note": "x", REUSED_FROM_METRIC: SOURCE}, "scalars carry, nesting does not"
    assert result.started_at == result.finished_at == at


def test_a_stage_that_is_not_succeeded_is_not_taken_and_the_first_such_stage_is_named():
    for status in ("partial", "failed", "skipped"):
        assert _reason(start="text_analysis", rows=_rows(page_geometry_extraction=_row(
            "page_geometry_extraction", 1, status=status))) == ("page_geometry_extraction", "source_stage_not_completed")


def test_a_stage_the_source_never_wrote_is_not_taken():
    rows = _rows()
    del rows["document_context_build"]
    assert _reason(start="text_analysis", rows=rows) == ("document_context_build", "source_stage_not_completed")
    # ... and a stage at or after the chosen one is none of the rule's business.
    assert _plan("document_context_build", rows=rows).reused_stage_ids == PC01_STAGES[:2]


def test_an_output_of_another_stage_version_is_not_taken():
    assert _reason(start="document_context_build", rows=_rows(source_preparation=_row(
        "source_preparation", 0, version="0.9.0"))) == ("source_preparation", "source_stage_version_changed")


def test_an_output_without_a_required_role_is_not_taken():
    rows = _rows(page_geometry_extraction=_row("page_geometry_extraction", 1, drop_role="geometry.block_index"))
    assert _reason(start="text_analysis", rows=rows) == ("page_geometry_extraction", "source_stage_output_incomplete")


def test_a_malformed_artifact_reference_is_a_changed_artifact():
    good = _row("source_preparation", 0)
    broken = StageResultRow(
        stage_id=good.stage_id, stage_version=good.stage_version, status=good.status,
        artifacts=({"role": "prepared.text_layer", "blob_id": "not-a-blob"},), metrics={}, error=None)
    assert _reason(start="page_geometry_extraction", rows=_rows(source_preparation=broken)) == (
        "source_preparation", "source_artifact_changed")


@pytest.mark.parametrize("blobs, reason", [
    (dict(missing=True), "source_artifact_unavailable"),
    (dict(available=False), "source_artifact_unavailable"),
    (dict(sha256="b" * 64), "source_artifact_changed"),
    (dict(size_bytes=8), "source_artifact_changed"),
])
def test_an_artifact_that_is_gone_or_is_not_what_was_recorded_is_not_taken(blobs, reason):
    assert _reason(start="page_geometry_extraction", blobs=_Blobs(**blobs)) == ("source_preparation", reason)


@pytest.mark.parametrize("source_flag, new_flag, refused", [
    (False, False, False), (True, True, False), (False, True, True), (True, False, True)])
def test_the_one_input_beside_the_versions_bytes_must_be_the_same(monkeypatch, source_flag, new_flag, refused):
    monkeypatch.setattr(stage_reuse, "run_visual_only_pages", lambda session, run_id, runs=None: source_flag)
    if not refused:
        assert _plan("text_analysis", visual=new_flag).reused_stage_ids == PC01_STAGES[:3]
    else:
        assert _reason(start="text_analysis", visual=new_flag) == ("source_preparation", "source_stage_inputs_changed")


def test_every_reason_the_rule_can_give_has_a_planted_case_above():
    seen = {"source_stage_not_completed", "source_stage_version_changed", "source_stage_output_incomplete",
            "source_artifact_unavailable", "source_artifact_changed", "source_stage_inputs_changed"}
    assert seen == set(REASONS)


def test_the_flag_is_the_extended_review_v3_plan_and_nothing_else():
    assert visual_only_pages_allowed({"enabled": True, "plan_version": "extended-review-v3"}) is True
    assert visual_only_pages_allowed({"enabled": True, "plan_version": "extended-review-v2"}) is False
    assert visual_only_pages_allowed({}) is False
    assert visual_only_pages_allowed(None) is False
    assert visual_only_pages_allowed("extended-review-v3") is False
