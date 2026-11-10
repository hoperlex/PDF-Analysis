"""`HOSTS-SEAL-1`: the host mode of the runner protocol, as the contract's models read it.

The text is `tools/executor-runner/RUNNER_API.md` section 10 (the agent lane's `HOSTS-AGENT-01`), written into the contract of 1.45.0. Each
example below is the document that section shows; the tests prove the models accept it, refuse what it forbids, and leave the wire of a
token bound to a connection exactly what it was.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from auditmanager.api.schemas import models

HOST = "exh_01ARZ3NDEKTSV4RRFFQ69G5FAV"
TOKEN = "ern_01ARZ3NDEKTSV4RRFFQ69G5FAV"
NOW = "2026-11-09T12:00:00Z"

CATALOGUE = [
    {"provider": "claude_code", "model_id": "claude-opus-5-5", "efforts": ["medium", "high"],
     "accepted_reported": ["claude-opus-5-5", "claude-opus-5-5[1m]"]},
    {"provider": "openrouter_api", "model_id": "gpt-6.1-sol", "efforts": ["low"], "accepted_reported": ["openai/gpt-6.1-sol"]},
]

HOST_HEALTH = {
    "agent_version": "0.21.0",
    "clis": [{"cli": "claude", "installed": True, "version": "2.1.310", "auth_state": "valid"}],
    "concurrency": 3,
    "execution_profile": "command",
    "features": [],
    "runner_instance_id": "Qx7abcdefgh",
    "providers": [
        {"provider": "claude_code", "access": "subscription", "cli_version": "2.1.310", "auth_state": "valid", "accept_images": False,
         "models": [{"model_id": "claude-opus-5-5", "state": "verified", "checked_at": NOW},
                    {"model_id": "claude-sonnet-5-5", "state": "failed", "checked_at": NOW, "failure_code": "quota_exceeded"}]},
        {"provider": "anthropic_api", "access": "api", "auth_state": "valid", "models": []},
    ],
    "slots": {"claude_code": 1, "anthropic_api": 2},
    "key_file": {"state": "ignored", "reason": "mode_is_not_0600"},
}


def test_a_host_health_report_of_the_runner_api_parses_and_round_trips_without_loss() -> None:
    report = models.ReportRunnerHealthRequest.model_validate(HOST_HEALTH)
    assert report.slots.claude_code == 1 and report.slots.codex is None
    assert report.providers[0].models[1].failure_code == "quota_exceeded"
    assert report.key_file.reason == "mode_is_not_0600"
    assert report.model_dump(mode="json", exclude_unset=True)["providers"][0]["accept_images"] is False


def test_a_connection_token_report_without_the_host_members_is_what_it_was() -> None:
    old = {key: HOST_HEALTH[key] for key in ("agent_version", "clis", "concurrency", "execution_profile", "features")}
    report = models.ReportRunnerHealthRequest.model_validate(old)
    assert report.providers is None and report.slots is None and report.key_file is None


@pytest.mark.parametrize("change", [
    {"execution_profile": "host"},                      # no new profile value: a host agent sends `command`
    {"slots": {"claude_code": 0}},                      # a slot is 1 to 16
    {"slots": {"gemini": 1}},                           # a provider of the closed set
    {"providers": [{"provider": "claude_code", "access": "subscription", "auth_state": "valid", "models": [
        {"model_id": "m", "state": "failed", "checked_at": NOW, "failure_code": "Quota-Exceeded"}]}]},  # a code is lower case
    {"key_file": {"state": "present"}},
    {"unexpected": True},
])
def test_what_the_protocol_forbids_is_refused(change: dict) -> None:
    with pytest.raises(ValidationError):
        models.ReportRunnerHealthRequest.model_validate({**HOST_HEALTH, **change})


def test_clis_stays_required_of_a_host_agent() -> None:
    without = {key: value for key, value in HOST_HEALTH.items() if key != "clis"}
    with pytest.raises(ValidationError):
        models.ReportRunnerHealthRequest.model_validate(without)


def test_the_acknowledgement_carries_the_catalogue_and_the_switch_for_a_host_and_neither_for_a_connection() -> None:
    host = models.RunnerHealthAck.model_validate({"recorded_at": NOW, "catalogue": CATALOGUE, "enabled": False})
    assert host.enabled is False and host.catalogue[0].accepted_reported[1] == "claude-opus-5-5[1m]"
    assert models.RunnerHealthAck.model_validate({"recorded_at": NOW}).catalogue is None


def test_a_host_enrollment_answer_has_a_token_a_host_and_a_catalogue_and_may_omit_the_token_metadata() -> None:
    answer = models.IssuedRunnerToken.model_validate({"token": "amr_" + "a" * 52, "host_id": HOST, "catalogue": CATALOGUE})
    assert answer.runner_token is None and answer.host_id == HOST
    dumped = answer.model_dump(mode="json", exclude_unset=True)
    assert set(dumped) == {"token", "host_id", "catalogue"}


def test_the_token_metadata_of_a_host_names_the_host_and_no_connection() -> None:
    metadata = models.RunnerTokenMetadata.model_validate({
        "token_id": TOKEN, "host_id": HOST, "token_prefix": "amr_abcdefgh", "created_at": NOW,
        "created_by": "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV", "expires_at": "2026-12-09T12:00:00Z"})
    assert metadata.connection_id is None and metadata.host_id == HOST


def test_a_host_task_carries_all_seven_members_and_the_old_task_none_of_them() -> None:
    base = {"task_id": "ext_01ARZ3NDEKTSV4RRFFQ69G5FAV", "claim_expires_at": NOW, "deadline_at": NOW, "model": "claude-opus-5-5",
            "system": "s", "user_text": "u", "output_schema": {"type": "object"}}
    host = models.ClaimedExecutorTask.model_validate({
        **base, "provider": "claude_code", "access": "subscription", "model_id": "claude-opus-5-5", "effort": "medium",
        "max_output_tokens": 16000, "timeout_seconds": 600, "cell_key": "blocks:leg1"})
    assert host.model == host.model_id
    assert models.ClaimedExecutorTask.model_validate(base).provider is None
    with pytest.raises(ValidationError):
        models.ClaimedExecutorTask.model_validate({**base, "effort": "xhigh"})  # never offered
    with pytest.raises(ValidationError):
        models.ClaimedExecutorTask.model_validate({**base, "cell_key": "blocks"})  # a cell key is `row:role`


def test_a_host_answer_names_the_exact_reported_model_and_sends_no_top_level_tokens() -> None:
    answer = models.SubmitExecutorTaskAnswerRequest.model_validate({
        "output_text": "{}", "model": "claude-opus-5-5", "provider": "claude_code", "access": "subscription",
        "reported_model": "claude-opus-5-5-20261001", "usage": {"input_tokens": 1234, "output_tokens": 321}})
    assert answer.reported_model == "claude-opus-5-5-20261001" and answer.input_tokens is None
    with pytest.raises(ValidationError):
        models.SubmitExecutorTaskAnswerRequest.model_validate({"output_text": "{}", "model": "m", "usage": {"input_tokens": -1, "output_tokens": 0}})


def test_the_consent_body_is_the_one_of_every_route_and_its_examples_validate() -> None:
    schema = models.RunCostConsent.model_json_schema()
    assert schema["examples"], "the consent body carries its examples"
    for example in schema["examples"]:
        assert models.RunCostConsent.model_validate(example).confirmed is True
    subscription = models.RunCostConsent.model_validate(schema["examples"][0])
    assert subscription.ceiling_micros == 0  # all cells on a subscription: the press of the button is the consent


def test_the_estimate_may_be_mixed_and_carries_a_line_per_model() -> None:
    base = {"estimate_digest": "a" * 64, "scope": "run", "version_uid": "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", "provider_mode": "live",
            "billing": "mixed", "model_id": "claude-opus-5-5", "text_characters": 1, "page_count": 1, "windows": 1, "calls": 2,
            "input_tokens": 1, "output_tokens": 1, "estimated_cost_micros": 5, "recommended_ceiling_micros": 10, "currency": "USD",
            "relaxed_limits": False, "stage_plan_digest": "b" * 64,
            "models": [{"model_id": "claude-opus-5-5", "access": "subscription", "rate_sha256": "c" * 64, "calls": 1, "input_tokens": 1,
                        "output_tokens": 1, "estimated_cost_micros": 0},
                       {"model_id": "gpt-6-astra", "access": "api", "rate_sha256": "d" * 64, "calls": 1, "input_tokens": 1,
                        "output_tokens": 1, "estimated_cost_micros": 5}]}
    assert models.RunCostEstimate.model_validate(base).billing == "mixed"
    with pytest.raises(ValidationError):
        models.RunCostEstimate.model_validate({**base, "billing": "free"})


def test_the_new_wait_reason_and_member_issues_exist_and_nothing_else_moved() -> None:
    assert [reason.value for reason in models.RunQueueReason] == [
        "executor_at_capacity", "runner_offline", "needs_reconsent", "model_unavailable"]
    assert [issue.value for issue in models.ExecutorGroupMemberIssue][-3:] == ["host_disabled", "model_not_verified", "model_cooling_down"]
