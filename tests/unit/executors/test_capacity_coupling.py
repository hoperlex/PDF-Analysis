"""`EXEC2-CAP-01` (ADR-0026 decision 2): the limits that must agree with ``max_active_runs``. Pure, no database.

* a ``pull`` revision's ``max_claimed_tasks`` and an ``http_api`` revision's set ``max_parallel_calls`` may not
  be below the capacity (``below_max_active_runs``, on the smaller field);
* an ``ssh_command`` revision goes above one only where the remote command is one this repository ships and has
  read for isolation (``claude_code_headless``); a ``custom_command`` answers ``capacity_not_supported_for_kind``;
* the default capacity of one is never refused, and a refusal names a field and a constraint and never a value;
* the ledger payload of a revision gains ``max_active_runs`` only when it is set, so a key issued before the
  setting existed still replays.

Every refusal test is paired with the neighbouring value that is accepted, so the guard is shown able to fail in
both directions.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from auditmanager.analysis.public import pinned_models
from auditmanager.executors.commands import _fingerprinted, refuse_uncoupled_capacity
from auditmanager.executors.model import (
    CONSTRAINT_BELOW_MAX_ACTIVE_RUNS,
    CONSTRAINT_CAPACITY_NOT_SUPPORTED_FOR_KIND,
    CONSTRAINT_RANGE,
    DEFAULT_MAX_ACTIVE_RUNS,
    RevisionSettings,
    validate_settings,
)
from auditmanager.shared.errors import DomainError, ErrorCode

PINS = {pin.model_id for pin in pinned_models()}
BASE = dict(pin_id="claude-opus-5", gateway_model="anthropic/claude-opus-5", billing="metered",
            allow_client_documents=False, timeout_seconds=60)
HTTP = RevisionSettings(**BASE, api_flavour="openai_chat", base_url="https://proxy.test/agent/v1",
                        transport="direct")
SSH = RevisionSettings(**BASE, ssh_host="gpu.test", ssh_port=2222, ssh_user="am",
                       ssh_profile="claude_code_headless")
PULL = RevisionSettings(**BASE, pull_client="claude_code_session", answer_deadline_seconds=600,
                        max_claimed_tasks=1)


def _refusal(kind: str, settings: RevisionSettings) -> dict[str, object]:
    with pytest.raises(DomainError) as refused:
        refuse_uncoupled_capacity(kind, settings)
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    return dict(refused.value.detail_fields)


def test_the_default_capacity_is_one() -> None:
    assert DEFAULT_MAX_ACTIVE_RUNS == 1


@pytest.mark.parametrize(("kind", "settings"), [
    ("http_api", replace(HTTP, max_parallel_calls=1)),
    ("pull", PULL),
    ("ssh_command", replace(SSH, ssh_profile="custom_command")),
])
@pytest.mark.parametrize("capacity", [None, 1])
def test_the_default_capacity_is_never_refused_whatever_the_other_limits_are(
    kind: str, settings: RevisionSettings, capacity: int | None,
) -> None:
    refuse_uncoupled_capacity(kind, replace(settings, max_active_runs=capacity))


# --- pull: max_claimed_tasks ---------------------------------------------------------------------


def test_a_pull_revision_whose_claim_limit_is_below_its_capacity_is_refused_on_the_smaller_field() -> None:
    assert _refusal("pull", replace(PULL, max_claimed_tasks=2, max_active_runs=3)) == {
        "field": "max_claimed_tasks", "constraint": CONSTRAINT_BELOW_MAX_ACTIVE_RUNS,
    }


@pytest.mark.parametrize("claimed", [3, 4, 16])
def test_a_pull_revision_whose_claim_limit_reaches_its_capacity_is_accepted(claimed: int) -> None:
    refuse_uncoupled_capacity("pull", replace(PULL, max_claimed_tasks=claimed, max_active_runs=3))


def test_the_default_claim_limit_of_one_cannot_back_a_larger_capacity() -> None:
    assert _refusal("pull", replace(PULL, max_active_runs=2))["field"] == "max_claimed_tasks"


# --- http_api: max_parallel_calls ----------------------------------------------------------------


def test_an_http_revision_whose_set_parallel_calls_are_below_its_capacity_is_refused_on_the_smaller_field() -> None:
    assert _refusal("http_api", replace(HTTP, max_parallel_calls=2, max_active_runs=3)) == {
        "field": "max_parallel_calls", "constraint": CONSTRAINT_BELOW_MAX_ACTIVE_RUNS,
    }


@pytest.mark.parametrize("parallel", [3, 8, 16])
def test_an_http_revision_whose_parallel_calls_reach_its_capacity_is_accepted(parallel: int) -> None:
    refuse_uncoupled_capacity("http_api", replace(HTTP, max_parallel_calls=parallel, max_active_runs=3))


def test_an_http_revision_with_no_parallel_calls_limit_is_unbounded_and_accepted() -> None:
    refuse_uncoupled_capacity("http_api", replace(HTTP, max_parallel_calls=None, max_active_runs=16))


def test_the_ssh_tunnel_transport_does_not_change_the_http_rule() -> None:
    tunnel = replace(HTTP, base_url="http://localhost:11434", transport="ssh_tunnel", ssh_host="gpu.test",
                     ssh_port=22, ssh_user="am", max_parallel_calls=1, max_active_runs=2)
    assert _refusal("http_api", tunnel)["field"] == "max_parallel_calls"
    refuse_uncoupled_capacity("http_api", replace(tunnel, max_parallel_calls=2))


# --- ssh_command: the wrappers ----------------------------------------------------------------------


def test_an_ssh_revision_of_the_shipped_profile_may_go_above_one() -> None:
    """`claude_answer.py --ssh-envelope` and `ssh-forced-command.sh` each make their own temporary directory,
    read their task from their own stdin, keep no lock file or module state and run the CLI with no saved
    session; each invocation is its own process tree under its own sshd session (read for `EXEC2-CAP-01`;
    recorded in `executors/README.md`)."""
    refuse_uncoupled_capacity("ssh_command", replace(SSH, max_active_runs=16))


def test_an_ssh_revision_of_a_custom_command_is_refused_above_one_and_accepted_at_one() -> None:
    custom = replace(SSH, ssh_profile="custom_command")
    assert _refusal("ssh_command", replace(custom, max_active_runs=2)) == {
        "field": "max_active_runs", "constraint": CONSTRAINT_CAPACITY_NOT_SUPPORTED_FOR_KIND,
    }
    refuse_uncoupled_capacity("ssh_command", replace(custom, max_active_runs=1))


# --- what a refusal says --------------------------------------------------------------------------------


@pytest.mark.parametrize("settings", [
    replace(PULL, max_claimed_tasks=2, max_active_runs=5),
    replace(HTTP, max_parallel_calls=2, max_active_runs=5),
    replace(SSH, ssh_profile="custom_command", max_active_runs=5),
])
def test_a_refusal_carries_a_field_and_a_constraint_and_no_value(settings: RevisionSettings) -> None:
    kind = "pull" if settings.pull_client else "http_api" if settings.api_flavour else "ssh_command"
    with pytest.raises(DomainError) as refused:
        refuse_uncoupled_capacity(kind, settings)
    assert set(refused.value.detail_fields) == {"field", "constraint"}
    assert all(isinstance(value, str) for value in refused.value.detail_fields.values())
    assert "gpu.test" not in repr(refused.value.detail_fields) + str(refused.value)


def test_the_range_is_refused_by_the_settings_rules_before_the_coupling_is_asked() -> None:
    for outside in (0, 17):
        with pytest.raises(DomainError) as refused:
            validate_settings("http_api", replace(HTTP, max_active_runs=outside), pinned_model_ids=PINS)
        assert refused.value.detail_fields == {"field": "max_active_runs", "constraint": CONSTRAINT_RANGE}
    for inside in (1, 16):
        validate_settings("http_api", replace(HTTP, max_active_runs=inside), pinned_model_ids=PINS)


def test_the_two_new_constraint_values_are_the_ones_the_contract_documents() -> None:
    assert CONSTRAINT_BELOW_MAX_ACTIVE_RUNS == "below_max_active_runs"
    assert CONSTRAINT_CAPACITY_NOT_SUPPORTED_FOR_KIND == "capacity_not_supported_for_kind"


# --- the ledger payload ---------------------------------------------------------------------------------


def test_the_ledger_payload_of_a_revision_without_a_capacity_is_the_one_written_before_the_setting_existed() -> None:
    payload = _fingerprinted(HTTP)
    assert "max_active_runs" not in payload
    assert payload == {name: getattr(HTTP, name) for name in HTTP.__slots__ if name != "max_active_runs"}


def test_a_capacity_is_part_of_the_ledger_payload_so_a_changed_capacity_is_a_different_request() -> None:
    three, four = _fingerprinted(replace(HTTP, max_active_runs=3)), _fingerprinted(replace(HTTP, max_active_runs=4))
    assert three["max_active_runs"] == 3 and four["max_active_runs"] == 4 and three != four
    assert three != _fingerprinted(HTTP)
