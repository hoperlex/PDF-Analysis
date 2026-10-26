"""`SECTION-CHUNKED-ANALYSIS-01`: the finished-window reader and the recovery rule, on real PostgreSQL.

Two things in ``jobs/repository.py`` decide whether a killed windowed run resumes:

* :meth:`JobRepository.completed_window_calls` returns the windows this Run has finished, each call
  cross-checked with its effect, and refuses (never skips) a row whose evidence disagrees with itself;
* :meth:`JobRepository.reclaim_expired` no longer counts a ``completed`` effect that carries a window's saved
  reply as an ambiguous provider effect, and **only** such an effect: a completed single call, a window still
  ``prepared`` and a window whose answer was received but not completed are exactly as ambiguous as before.

Each case is written through the repository's own journal methods inside the harness's rolled-back transaction.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.jobs.repository import JobRepository
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId

MODEL = "claude-opus-5"
SHA_A, SHA_B, SHA_C = "a" * 64, "b" * 64, "c" * 64
BLOB = "blob_" + "0" * 26


def _running_run(session: Session, seeded: Any, mode: str = "live"):
    run_id = str(RunId.new())
    runs, jobs = RunRepository(), JobRepository()
    runs.create(
        session, run_id=run_id, project_uid=seeded.project_uid, version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id, prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode=mode, frozen_input_digest="a" * 64, command_id=None,
    )
    runs.advance(session, run_id=run_id, from_state="created", to_state="queued")
    jobs.enqueue(session, run_id=run_id)
    authority = jobs.start_execution(session, run_id=run_id)
    runs.advance(session, run_id=run_id, from_state="queued", to_state="running")
    return run_id, authority


def _window_parameters(key: str, index: int, **overrides: Any) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "max_tokens": 16000,
        "text_window_key": key, "text_window_index": index, "text_window_count": 3,
        "text_window_first_page": 1 + 3 * index, "text_window_last_page": 3 + 3 * index,
        "text_window_reply_blob_id": BLOB, "text_window_reply_blob_sha256": SHA_C,
        "text_window_reply_blob_size": 512,
    }
    parameters.update(overrides)
    return parameters


def _call(jobs: JobRepository, session: Session, authority, *, parameters: dict[str, Any] | None,
          request_sha: str, response_sha: str, mode: str = "live", complete: bool = True,
          respond: bool = True):
    call_id = jobs.prepare_provider_call(
        session, authority, provider="anthropic", model_identity=MODEL, provider_mode=mode,
        parameters={"max_tokens": 16000}, request_sha256=request_sha,
    )
    if respond:
        jobs.record_provider_response(
            session, authority, model_call_id=call_id, response_sha256=response_sha,
            input_tokens=100, output_tokens=10, latency_ms=5,
        )
    if respond and complete:
        jobs.complete_provider_call(session, authority, call={
            "model_call_id": str(call_id), "provider": "anthropic", "model_id": MODEL,
            "provider_mode": mode, "parameters": parameters or {"max_tokens": 16000},
            "request_sha256": request_sha, "response_sha256": response_sha,
            "input_tokens": 100, "output_tokens": 10, "latency_ms": 5,
            "status": "succeeded", "cost_usd": 0.01, "cost_basis": "measured",
        })
    return call_id


def _state(session: Session, run_id: str) -> tuple[str, str]:
    return tuple(session.execute(text(
        "SELECT r.state, j.state FROM audit_run r JOIN job j ON j.run_id = r.run_id WHERE r.run_id = :r"
    ), {"r": run_id}).one())


# -- the reader ----------------------------------------------------------------------------------


def test_a_finished_window_is_returned_by_its_key_with_the_call_it_belongs_to(session, seeded) -> None:
    run_id, authority = _running_run(session, seeded)
    jobs = JobRepository()
    first = _call(jobs, session, authority, parameters=_window_parameters("1" * 64, 0),
                  request_sha=SHA_A, response_sha=SHA_B)
    second = _call(jobs, session, authority, parameters=_window_parameters("2" * 64, 1),
                   request_sha="d" * 64, response_sha="e" * 64)
    found = jobs.completed_window_calls(session, authority)
    assert set(found) == {"1" * 64, "2" * 64}
    one = found["1" * 64]
    assert (one.model_call_id, one.window_index, one.window_count) == (str(first), 0, 3)
    assert (one.first_page, one.last_page) == (1, 3) and one.status == "succeeded"
    assert (one.request_sha256, one.response_sha256) == (SHA_A, SHA_B)
    assert (one.reply_blob_id, one.reply_blob_sha256, one.reply_blob_size) == (BLOB, SHA_C, 512)
    assert one.provider_mode == "live" and one.cost_micros == 10_000 and one.run_id == run_id
    assert found["2" * 64].model_call_id == str(second)


def test_a_single_call_row_and_an_unfinished_window_are_not_finished_windows(session, seeded) -> None:
    _, authority = _running_run(session, seeded)
    jobs = JobRepository()
    _call(jobs, session, authority, parameters=None, request_sha=SHA_A, response_sha=SHA_B)
    _call(jobs, session, authority, parameters=_window_parameters("3" * 64, 2),
          request_sha="d" * 64, response_sha="e" * 64, complete=False)
    assert jobs.completed_window_calls(session, authority) == {}


def test_two_finished_calls_under_one_key_are_refused_not_picked_between(session, seeded) -> None:
    _, authority = _running_run(session, seeded)
    jobs = JobRepository()
    for request_sha, response_sha in ((SHA_A, SHA_B), ("d" * 64, "e" * 64)):
        _call(jobs, session, authority, parameters=_window_parameters("4" * 64, 0),
              request_sha=request_sha, response_sha=response_sha)
    with pytest.raises(DomainError) as refused:
        jobs.completed_window_calls(session, authority)
    assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert refused.value.detail_fields["reason"] == "window_call_duplicate"


@pytest.mark.parametrize("override", [
    {"text_window_reply_blob_id": "not-a-blob"},
    {"text_window_reply_blob_sha256": "xyz"},
    {"text_window_reply_blob_size": 0},
    {"text_window_index": 7},
    {"text_window_first_page": 5, "text_window_last_page": 2},
    {"text_window_key": "short"},
    {"text_window_count": "3"},
])
def test_a_finished_window_with_a_malformed_reference_is_refused(session, seeded, override) -> None:
    _, authority = _running_run(session, seeded)
    jobs = JobRepository()
    _call(jobs, session, authority, parameters=_window_parameters("5" * 64, 0, **override),
          request_sha=SHA_A, response_sha=SHA_B)
    with pytest.raises(DomainError) as refused:
        jobs.completed_window_calls(session, authority)
    assert refused.value.detail_fields["reason"] == "window_call_reference_invalid"


def test_a_window_call_whose_mode_is_not_the_runs_is_refused(session, seeded) -> None:
    _, authority = _running_run(session, seeded, mode="recorded")
    jobs = JobRepository()
    _call(jobs, session, authority, parameters=_window_parameters("6" * 64, 0),
          request_sha=SHA_A, response_sha=SHA_B, mode="live")
    with pytest.raises(DomainError) as refused:
        jobs.completed_window_calls(session, authority)
    assert refused.value.detail_fields["reason"] == "window_call_pair_invalid"


def test_the_read_needs_the_current_attempt(session, seeded) -> None:
    _, authority = _running_run(session, seeded)
    stranger = authority.__class__(
        authority.run_id, authority.job_id, "att_01M2545JSD15ETSNNV904X991J", authority.lease_id, authority.execution_token
    )
    with pytest.raises(DomainError) as refused:
        JobRepository().completed_window_calls(session, stranger)
    assert refused.value.code is ErrorCode.STALE_ATTEMPT


# -- the recovery rule ---------------------------------------------------------------------------------


def _lose(session: Session, jobs: JobRepository, authority) -> None:
    assert jobs.reclaim_expired(session, force_attempt_id=authority.attempt_id) == 1


def test_a_lost_attempt_whose_only_live_effect_is_a_finished_window_is_resumed(session, seeded) -> None:
    run_id, authority = _running_run(session, seeded)
    jobs = JobRepository()
    _call(jobs, session, authority, parameters=_window_parameters("7" * 64, 0),
          request_sha=SHA_A, response_sha=SHA_B)
    _lose(session, jobs, authority)
    assert _state(session, run_id) == ("running", "queued"), "resumable: queued again, not failed"


def test_a_lost_attempt_with_a_finished_single_call_is_still_ambiguous(session, seeded) -> None:
    """The exclusion is for a window's saved reply and nothing else: a completed call without one fails the run."""
    run_id, authority = _running_run(session, seeded)
    jobs = JobRepository()
    _call(jobs, session, authority, parameters=None, request_sha=SHA_A, response_sha=SHA_B)
    _lose(session, jobs, authority)
    assert _state(session, run_id)[0] == "failed"


def test_a_lost_attempt_with_a_window_in_flight_is_still_ambiguous(session, seeded) -> None:
    run_id, authority = _running_run(session, seeded)
    jobs = JobRepository()
    _call(jobs, session, authority, parameters=_window_parameters("8" * 64, 0),
          request_sha=SHA_A, response_sha=SHA_B)
    _call(jobs, session, authority, parameters=None, request_sha="d" * 64, response_sha="e" * 64,
          respond=False)  # window two: intent committed, no answer
    _lose(session, jobs, authority)
    assert _state(session, run_id)[0] == "failed"
    assert session.execute(text(
        "SELECT count(*) FROM provider_call_effect WHERE run_id = :r AND state = 'outcome_unknown'"
    ), {"r": run_id}).scalar_one() == 1


def test_a_lost_attempt_with_an_answer_received_but_not_completed_is_still_ambiguous(session, seeded) -> None:
    run_id, authority = _running_run(session, seeded)
    jobs = JobRepository()
    _call(jobs, session, authority, parameters=_window_parameters("9" * 64, 0),
          request_sha=SHA_A, response_sha=SHA_B, complete=False)
    _lose(session, jobs, authority)
    assert _state(session, run_id)[0] == "failed"


# -- every arm of the call/effect agreement -----------------------------------------------------------------


def _valid_row(authority) -> dict[str, Any]:
    return {
        "model_call_id": "mc_01M2545JSD15ETSNNV904X991J", "provider": "anthropic", "model_identity": MODEL,
        "provider_mode": "live", "call_parameters": _window_parameters("a" * 64, 0),
        "request_sha256": SHA_A, "response_sha256": SHA_B, "input_tokens": 100, "output_tokens": 10,
        "latency_ms": 5, "cost_micros": 10_000, "cost_basis": "measured", "status": "succeeded",
        "call_error": None, "job_id": authority.job_id, "attempt_id": authority.attempt_id,
        "effect_stage": "text_analysis", "effect_provider": "anthropic", "effect_model": MODEL,
        "effect_mode": "live", "effect_request": SHA_A, "effect_response": SHA_B,
        "effect_state": "completed", "effect_error": None,
        "final_model_call_id": "mc_01M2545JSD15ETSNNV904X991J", "run_mode": "live",
    }


def test_the_reader_accepts_the_valid_row_it_will_be_mutated_from() -> None:
    from auditmanager.jobs.public import AttemptAuthority

    authority = AttemptAuthority(
        "run_01M2545JSD15ETSNNV904X991J", "job_01M2545JSD15ETSNNV904X991J",
        "att_01M2545JSD15ETSNNV904X991J", "lease_01M2545JSD15ETSNNV904X991J", "t",
    )
    call = JobRepository()._window_call_of(_valid_row(authority), authority)
    assert call.key == "a" * 64 and call.window_count == 3


@pytest.mark.parametrize("field,value", [
    ("job_id", "job_01M2545JSD15ETSNNV904X991K"),        # another Job's call
    ("effect_stage", "page_geometry_extraction"),
    ("effect_state", "response_received"),
    ("final_model_call_id", "mc_01M2545JSD15ETSNNV904X991K"),
    ("call_error", "analysis_failed"),
    ("effect_error", "analysis_failed"),
    ("status", "failed"),
    ("provider_mode", "mock"),
    ("effect_mode", "recorded"),
    ("run_mode", "recorded"),
    ("effect_provider", "another"),
    ("effect_model", "another-model"),
    ("effect_request", "9" * 64),
    ("effect_response", "9" * 64),
    ("response_sha256", "short"),
    ("input_tokens", -1),
    ("latency_ms", "5"),
    ("cost_basis", "guess"),
    ("cost_micros", -5),
    ("call_parameters", None),
])
def test_a_row_where_call_and_effect_disagree_is_refused(field: str, value: Any) -> None:
    from auditmanager.jobs.public import AttemptAuthority

    authority = AttemptAuthority(
        "run_01M2545JSD15ETSNNV904X991J", "job_01M2545JSD15ETSNNV904X991J",
        "att_01M2545JSD15ETSNNV904X991J", "lease_01M2545JSD15ETSNNV904X991J", "t",
    )
    row = _valid_row(authority)
    row[field] = value
    with pytest.raises(DomainError) as refused:
        JobRepository()._window_call_of(row, authority)
    assert refused.value.detail_fields["reason"] == "window_call_pair_invalid", field
