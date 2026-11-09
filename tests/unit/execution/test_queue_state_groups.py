"""`D-370` (contract 1.43.0): the queue's three groups of states, container-free.

``listExecutionQueue`` takes ``state_group`` and lists every job in any state of the group. The groups are the original's
«Активные / Завершённые / Ошибки»; this file holds that they cover the job state machine exactly once (so the three groups
add up to the whole queue and a group's press lists the rows its count adds up), and that the contract's names are the ones
the server holds.
"""

from __future__ import annotations

import json
from pathlib import Path

from auditmanager.api.routers.declarations import QUEUE_JOB_STATES, QUEUE_STATE_GROUP_NAMES
from auditmanager.execution.public import QUEUE_STATE_GROUPS, _state_set

ROOT = Path(__file__).resolve().parents[3]


def _job_states() -> set[str]:
    machine = json.loads((ROOT / "contracts/domain/v1/state-machines.json").read_text(encoding="utf-8"))["machines"]["job"]
    return set(machine["transitions"]) | {target for targets in machine["transitions"].values() for target in targets}


def test_every_job_state_is_in_exactly_one_group() -> None:
    grouped = [state for states in QUEUE_STATE_GROUPS.values() for state in states]
    assert sorted(grouped) == sorted(set(grouped)), "a state is in two groups"
    assert set(grouped) == _job_states() == set(QUEUE_JOB_STATES)


def test_the_groups_are_the_originals_three_and_the_contract_names_them() -> None:
    assert tuple(QUEUE_STATE_GROUPS) == QUEUE_STATE_GROUP_NAMES == ("active", "completed", "errors")
    assert QUEUE_STATE_GROUPS["errors"] == ("failed", "dead_letter")
    assert QUEUE_STATE_GROUPS["completed"] == ("succeeded", "cancelled")
    assert set(QUEUE_STATE_GROUPS["active"]) == {"queued", "leased", "running", "retry_wait"}
    contract = json.loads((ROOT / "contracts/api/v1/openapi.json").read_text(encoding="utf-8"))
    parameter = next(p for p in contract["paths"]["/execution/queue"]["get"]["parameters"] if p.get("name") == "state_group")
    assert parameter["schema"]["enum"] == list(QUEUE_STATE_GROUPS) and parameter["required"] is False


def test_a_state_and_a_set_narrow_each_other_and_none_is_every_state() -> None:
    assert _state_set(None, None) is None
    assert _state_set("failed", None) == ["failed"]
    assert _state_set(None, QUEUE_STATE_GROUPS["errors"]) == ["failed", "dead_letter"]
    assert _state_set("failed", QUEUE_STATE_GROUPS["errors"]) == ["failed"]
    assert _state_set("queued", QUEUE_STATE_GROUPS["errors"]) == []
