"""CITE reads only one self-consistent completed AR v3 call/effect pair."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from auditmanager.jobs.public import AttemptAuthority, JobRepository, V3CompletedCall
from auditmanager.shared.errors import DomainError, ErrorCode


AUTHORITY = AttemptAuthority("run_v3", "job_v3", "att_current", "lease_current", "secret")
_EFFECT_PARAMS = {
    "max_tokens": 4096, "thinking": {"type": "adaptive"},
    "output_config": {"effort": "high", "format": {
        "type": "json_schema", "schema": {"type": "object"},
    }},
    "ar_v3_candidate_sha256": "a" * 64,
    "ar_v3_scope_id": "F1",
    "ar_v3_set_sha256": "b" * 64,
}
_CALL_PARAMS = {
    **_EFFECT_PARAMS,
    "ar_v3_reply_blob_id": "blob_" + "A" * 26,
    "ar_v3_reply_blob_sha256": "c" * 64,
    "ar_v3_reply_blob_size": 1234,
    "call_status": "succeeded",
}


def _row():
    return {
        "model_call_id": "mc_test", "provider": "http_api",
        "model_identity": "pin_test", "provider_mode": "live",
        "call_parameters": deepcopy(_CALL_PARAMS),
        "request_sha256": "d" * 64, "response_sha256": "e" * 64,
        "input_tokens": 100, "output_tokens": 40, "latency_ms": 500,
        "cost_micros": 4200, "cost_basis": "measured",
        "status": "succeeded", "call_error": None,
        "call_revision": "excr_test", "call_basis": "reported",
        "job_id": AUTHORITY.job_id, "attempt_id": "att_prior",
        "effect_stage": "text_analysis", "effect_provider": "http_api",
        "effect_model": "pin_test", "effect_mode": "live",
        "effect_parameters": deepcopy(_EFFECT_PARAMS),
        "effect_request": "d" * 64, "effect_response": "e" * 64,
        "effect_input_tokens": 100, "effect_output_tokens": 40,
        "effect_latency_ms": 500, "effect_state": "completed",
        "effect_error": None, "final_model_call_id": "mc_test",
        "effect_revision": "excr_test", "effect_basis": "reported",
        "run_state": "running", "run_mode": "live",
        "run_revision": "excr_test",
    }


class QuerySession:
    def __init__(self, rows):
        self.rows = rows
        self.query = None
        self.params = None

    def execute(self, query, params):
        self.query, self.params = str(query), params
        return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: self.rows))


class CurrentJobs(JobRepository):
    def __init__(self):
        super().__init__()
        self.current_checks = 0
        self.unlocked_checks = 0

    def require_current(self, session, authority):
        assert authority == AUTHORITY
        self.current_checks += 1

    def check_current_unlocked(self, session, authority):
        assert authority == AUTHORITY
        self.unlocked_checks += 1


def test_completed_call_can_be_read_by_a_new_current_attempt_of_same_job():
    session = QuerySession([_row()])
    jobs = CurrentJobs()
    result = jobs.completed_v3_call(session, AUTHORITY)
    assert isinstance(result, V3CompletedCall)
    assert result.attempt_id == "att_prior"
    assert result.job_id == AUTHORITY.job_id
    assert result.candidate_sha256 == "a" * 64
    assert result.scope_id == "F1"
    assert result.set_sha256 == "b" * 64
    assert result.max_output_tokens == 4096
    assert result.effort == "high"
    assert result.request_sha256 == "d" * 64
    assert result.response_sha256 == "e" * 64
    assert result.reply_blob_id == "blob_" + "A" * 26
    assert result.reply_blob_size == 1234
    assert result.connection_revision_id == "excr_test"
    assert jobs.current_checks == 2
    assert session.params == {"run_id": AUTHORITY.run_id}
    assert "LEFT JOIN provider_call_effect" in session.query


def test_provisional_completed_call_uses_only_unlocked_checks():
    jobs = CurrentJobs()
    result = jobs.completed_v3_call(
        QuerySession([_row()]), AUTHORITY, lock_authority=False,
    )
    assert result.model_call_id == "mc_test"
    assert jobs.unlocked_checks == 2
    assert jobs.current_checks == 0


@pytest.mark.parametrize("mutate", [
    lambda p: p.pop("max_tokens"),
    lambda p: p.update(max_tokens=True),
    lambda p: p.update(max_tokens=16_001),
    lambda p: p.update(thinking={"type": "disabled"}),
    lambda p: p.update(output_config={"effort": "high"}),
    lambda p: p.update(output_config={"effort": "ultra", "format": {
        "type": "json_schema", "schema": {},
    }}),
    lambda p: p.update(extra_setting="drift"),
])
def test_malformed_saved_generation_settings_refuse(mutate):
    row = _row()
    mutate(row["effect_parameters"])
    row["call_parameters"] = {
        **row["effect_parameters"],
        "ar_v3_reply_blob_id": "blob_" + "A" * 26,
        "ar_v3_reply_blob_sha256": "c" * 64,
        "ar_v3_reply_blob_size": 1234,
        "call_status": "succeeded",
    }
    with pytest.raises(DomainError) as invalid:
        CurrentJobs().completed_v3_call(QuerySession([row]), AUTHORITY)
    assert invalid.value.detail_fields["reason"] == "v3_call_pair_invalid"


@pytest.mark.parametrize("rows", ([], [_row(), _row()]))
def test_missing_or_duplicate_canonical_calls_refuse(rows):
    with pytest.raises(DomainError) as invalid:
        CurrentJobs().completed_v3_call(QuerySession(rows), AUTHORITY)
    assert invalid.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert invalid.value.detail_fields["reason"] == "v3_call_missing_or_duplicate"


@pytest.mark.parametrize("field,value", [
    ("job_id", "job_other"),
    ("run_state", "failed"),
    ("effect_state", "response_received"),
    ("final_model_call_id", None),
    ("effect_stage", "finding_merge"),
    ("status", "failed"),
    ("call_error", "analysis_failed"),
    ("provider_mode", "recorded"),
    ("effect_provider", "other"),
    ("effect_model", "other"),
    ("effect_request", "f" * 64),
    ("effect_response", "f" * 64),
    ("effect_output_tokens", 41),
    ("run_revision", "excr_other"),
    ("effect_basis", "declared"),
    ("cost_micros", -1),
    ("cost_basis", "unknown"),
])
def test_changed_call_or_effect_facts_refuse(field, value):
    row = _row()
    row[field] = value
    with pytest.raises(DomainError) as invalid:
        CurrentJobs().completed_v3_call(QuerySession([row]), AUTHORITY)
    assert invalid.value.detail_fields["reason"] == "v3_call_pair_invalid"


@pytest.mark.parametrize("key,value", [
    ("ar_v3_candidate_sha256", "short"),
    ("ar_v3_scope_id", ""),
    ("ar_v3_set_sha256", "short"),
])
def test_effect_binding_parameters_must_be_valid(key, value):
    row = _row()
    row["effect_parameters"][key] = value
    with pytest.raises(DomainError):
        CurrentJobs().completed_v3_call(QuerySession([row]), AUTHORITY)


@pytest.mark.parametrize("key,value", [
    ("ar_v3_reply_blob_id", "file:///tmp/answer"),
    ("ar_v3_reply_blob_sha256", "not-a-sha"),
    ("ar_v3_reply_blob_size", True),
    ("call_status", "truncated"),
])
def test_reply_reference_and_call_parameters_must_match_effect(key, value):
    row = _row()
    row["call_parameters"][key] = value
    with pytest.raises(DomainError):
        CurrentJobs().completed_v3_call(QuerySession([row]), AUTHORITY)


def test_recorded_call_and_truncated_call_are_allowed_when_facts_agree():
    row = _row()
    row.update({
        "provider_mode": "recorded", "effect_mode": "recorded", "run_mode": "recorded",
        "call_revision": None, "effect_revision": None, "run_revision": None,
        "call_basis": None, "effect_basis": None,
        "status": "truncated", "cost_micros": None, "cost_basis": "estimated",
    })
    row["call_parameters"]["call_status"] = "truncated"
    result = CurrentJobs().completed_v3_call(QuerySession([row]), AUTHORITY)
    assert result.provider_mode == "recorded"
    assert result.status == "truncated"
    assert result.cost_micros is None
