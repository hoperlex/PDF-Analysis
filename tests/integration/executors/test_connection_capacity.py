"""`EXEC2-CAP-01` (ADR-0026 decisions 1 and 2) -- the capacity of a connection in the executors context, over real
PostgreSQL, one rolled-back transaction per test.

Written and **not run** in EXEC-2 (`R-149d`, D-292); each test would pass against PostgreSQL.

* the revision keeps ``max_active_runs`` and reads as one when it has none (the repository persists it);
* the coupled limits (decision 2) are refused as ``422 validation_failed`` and write no revision;
* ``occupancy`` and ``used_units`` / ``capacity_of`` count the Runs of the connection, derived at read time;
* ``queue_reason`` of a waiting Run: ``runner_offline`` first, for a pull connection no runner of which was seen
  recently, then ``executor_at_capacity``, otherwise nothing;
* the same through the served API: the request takes the setting, the connection shows its occupancy.

The Runs are made with the ``EXEC-PAR-QUEUE-01`` rows (``tests/integration/jobs/connection_limit_support.py``) through a
session factory that hands out this test's own session, whose ``commit`` the harness joins to the transaction it rolls
back, so no row outlives the test.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from auditmanager.executors.public import (
    RevisionSettings,
    create_connection,
    current_revision,
    issue_runner_token,
    pinned_models,
    revise_connection,
    revoke_runner_token,
)
from auditmanager.executors.queries import (
    Occupancy,
    capacity_of,
    occupancies,
    occupancy_of,
    run_queue_reason,
    used_units,
)
from auditmanager.jobs.public import JobRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.executors.conftest import ADMIN, driver

_SUPPORT_NAME = "exec2_cap_connection_capacity_support"
if _SUPPORT_NAME in sys.modules:
    cap: ModuleType = sys.modules[_SUPPORT_NAME]
else:
    _spec = importlib.util.spec_from_file_location(
        _SUPPORT_NAME, Path(__file__).resolve().parents[1] / "jobs" / "connection_capacity_support.py"
    )
    assert _spec is not None and _spec.loader is not None
    cap = importlib.util.module_from_spec(_spec)
    sys.modules[_SUPPORT_NAME] = cap
    _spec.loader.exec_module(cap)

Request, dispatch = driver.Request, driver.dispatch

ADMIN_ROLES = frozenset({"admin"})
PINS = {pin.model_id for pin in pinned_models()}

HTTP = RevisionSettings(
    pin_id="claude-opus-5", gateway_model="anthropic/claude-opus-5", billing="metered",
    allow_client_documents=False, timeout_seconds=60, api_flavour="openai_chat",
    base_url="https://proxy.test/agent/v1", transport="direct",
)
SSH = RevisionSettings(
    pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="metered",
    allow_client_documents=False, timeout_seconds=120, ssh_host="gpu.test", ssh_port=22,
    ssh_user="am", ssh_profile="claude_code_headless",
)
PULL = RevisionSettings(
    pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="not_metered",
    allow_client_documents=False, timeout_seconds=600, pull_client="claude_code_session",
    answer_deadline_seconds=600, max_claimed_tasks=1,
)
HTTP_BODY = {
    "pin_id": "claude-opus-5", "gateway_model": "anthropic/claude-opus-5", "billing": "metered",
    "allow_client_documents": False, "timeout_seconds": 60, "api_flavour": "openai_chat",
    "base_url": "https://proxy.test/agent/v1", "transport": "direct",
}
PULL_BODY = {
    "pin_id": "claude-sonnet-5", "gateway_model": "claude-sonnet-5", "billing": "not_metered",
    "allow_client_documents": False, "timeout_seconds": 600, "pull_client": "claude_code_session",
    "answer_deadline_seconds": 600, "max_claimed_tasks": 1,
}


def key() -> str:
    return f"exec-{uuid4().hex}"


def connection(session, kind: str = "http_api") -> str:
    return create_connection(
        session, kind=kind, display_name="capacity", roles=ADMIN_ROLES, idempotency_key=key(),
        actor_uid=ADMIN,
    ).connection_id


def revise(session, connection_id: str, settings: RevisionSettings):
    return revise_connection(
        session, connection_id=connection_id, settings=settings, pinned_model_ids=PINS,
        roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN,
    )


def revision_count(session, connection_id: str) -> int:
    return int(session.execute(text(
        "SELECT count(*) FROM executor_connection_revision WHERE connection_id = :c"
    ), {"c": connection_id}).scalar_one())


def factory(session):
    """A session factory that hands out the test's own session, for the helpers that take one."""
    return lambda: nullcontext(session)


def unpaused(session) -> None:
    JobRepository().set_paused(session, paused=False)


def seen(session, token_id: str, *, seconds_ago: float) -> None:
    session.execute(text(
        "UPDATE executor_runner_token SET last_seen_at = clock_timestamp() - make_interval(secs => :ago) "
        "WHERE token_id = :id"
    ), {"id": token_id, "ago": seconds_ago})


def token_of(session, connection_id: str) -> str:
    return issue_runner_token(
        session, connection_id=connection_id, expires_in_days=None, roles=ADMIN_ROLES,
        idempotency_key=key(), actor_uid=ADMIN,
    ).record.token_id


# --- the revision keeps the capacity ---------------------------------------------------------------------------------


def test_a_revision_keeps_the_capacity_it_was_written_with_and_one_without_it_reads_as_one(session) -> None:
    cid = connection(session)
    legacy = revise(session, cid, HTTP)
    assert legacy.settings.max_active_runs is None and capacity_of(session, cid) == 1
    three = revise(session, cid, replace(HTTP, max_active_runs=3))
    assert three.settings.max_active_runs == 3
    assert current_revision(session, cid).settings.max_active_runs == 3 and capacity_of(session, cid) == 3
    stored = session.execute(text(
        "SELECT revision_no, max_active_runs FROM executor_connection_revision "
        "WHERE connection_id = :c ORDER BY revision_no"
    ), {"c": cid}).all()
    assert [tuple(row) for row in stored] == [(1, None), (2, 3)]
    revise(session, cid, HTTP)                      # a full revision, never a patch: the setting is gone again
    assert capacity_of(session, cid) == 1


def test_the_same_request_with_a_different_capacity_is_a_different_request(session) -> None:
    cid = connection(session)
    shared = key()
    kwargs = dict(connection_id=cid, pinned_model_ids=PINS, roles=ADMIN_ROLES, idempotency_key=shared, actor_uid=ADMIN)
    first = revise_connection(session, settings=replace(HTTP, max_active_runs=2), **kwargs)
    assert revise_connection(session, settings=replace(HTTP, max_active_runs=2), **kwargs).revision_id == first.revision_id
    with pytest.raises(DomainError) as reused:
        revise_connection(session, settings=replace(HTTP, max_active_runs=3), **kwargs)
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    assert revision_count(session, cid) == 1


# --- the coupled limits -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("kind", "settings", "field", "constraint"), [
    ("http_api", replace(HTTP, max_parallel_calls=2, max_active_runs=3), "max_parallel_calls", "below_max_active_runs"),
    ("pull", replace(PULL, max_claimed_tasks=2, max_active_runs=3), "max_claimed_tasks", "below_max_active_runs"),
    ("ssh_command", replace(SSH, ssh_profile="custom_command", max_active_runs=2), "max_active_runs",
     "capacity_not_supported_for_kind"),
    ("http_api", replace(HTTP, max_active_runs=17), "max_active_runs", "range"),
    ("http_api", replace(HTTP, max_active_runs=0), "max_active_runs", "range"),
])
def test_a_revision_that_cannot_serve_its_capacity_is_refused_and_writes_no_revision(
    session, kind: str, settings: RevisionSettings, field: str, constraint: str,
) -> None:
    cid = connection(session, kind)
    with pytest.raises(DomainError) as refused:
        revise(session, cid, settings)
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    assert dict(refused.value.detail_fields) == {"field": field, "constraint": constraint}
    assert revision_count(session, cid) == 0 and current_revision(session, cid) is None


@pytest.mark.parametrize(("kind", "settings"), [
    ("http_api", replace(HTTP, max_parallel_calls=3, max_active_runs=3)),
    ("http_api", replace(HTTP, max_active_runs=16)),
    ("pull", replace(PULL, max_claimed_tasks=4, max_active_runs=3)),
    ("ssh_command", replace(SSH, max_active_runs=4)),
    ("ssh_command", replace(SSH, ssh_profile="custom_command", max_active_runs=1)),
])
def test_the_neighbouring_revision_that_can_serve_its_capacity_is_accepted(
    session, kind: str, settings: RevisionSettings,
) -> None:
    cid = connection(session, kind)
    written = revise(session, cid, settings)
    assert written.settings.max_active_runs == settings.max_active_runs and revision_count(session, cid) == 1


# --- occupancy, used units, capacity ---------------------------------------------------------------------------------------


def test_the_occupancy_counts_the_runs_of_the_connection_and_only_its_active_ones(session) -> None:
    unpaused(session)
    sessions = factory(session)
    cid = connection(session)
    revision = revise(session, cid, replace(HTTP, max_active_runs=3)).revision_id
    other = connection(session)
    other_revision = revise(session, other, HTTP).revision_id
    runs = [cap.queue_run(sessions, revision) for _ in range(3)]
    elsewhere = cap.queue_run(sessions, other_revision)

    assert occupancy_of(session, cid) == Occupancy(3, 0, 0)
    first = cap.claim(sessions, runs[0])
    cap.claim(sessions, runs[1])
    cap.claim(sessions, elsewhere)
    assert occupancy_of(session, cid) == Occupancy(3, 2, 0)
    assert (used_units(session, cid), capacity_of(session, cid)) == (2, 3)
    assert occupancies(session, [cid, other]) == {cid: Occupancy(3, 2, 0), other: Occupancy(1, 1, 0)}
    cap.finish(sessions, first)
    assert occupancy_of(session, cid) == Occupancy(3, 1, 0), "an ended Run still counted"


def test_a_lowered_capacity_shows_more_in_use_than_the_capacity_and_nothing_is_stopped(session) -> None:
    unpaused(session)
    sessions = factory(session)
    cid = connection(session)
    revision = revise(session, cid, replace(HTTP, max_active_runs=3)).revision_id
    for _ in range(3):
        cap.claim(sessions, cap.queue_run(sessions, revision))
    revise(session, cid, replace(HTTP, max_active_runs=1))
    occupancy = occupancy_of(session, cid)
    assert occupancy == Occupancy(1, 3, 0) and occupancy.has_free_unit is False


def test_a_connection_with_no_revision_has_the_default_capacity_and_nothing_in_use(session) -> None:
    cid = connection(session)
    assert occupancy_of(session, cid) == Occupancy(1, 0, 0)


def test_an_unknown_connection_is_not_found(session) -> None:
    for read in (used_units, capacity_of, occupancy_of):
        with pytest.raises(DomainError) as refused:
            read(session, f"exc_{'0' * 26}")
        assert refused.value.code is ErrorCode.NOT_FOUND


# --- why a Run waits ----------------------------------------------------------------------------------------------------------


def test_a_queued_run_waits_at_capacity_exactly_when_its_connection_has_no_unit_free(session) -> None:
    unpaused(session)
    sessions = factory(session)
    cid = connection(session)
    revision = revise(session, cid, replace(HTTP, max_active_runs=2)).revision_id
    a, b, waiting = (cap.queue_run(sessions, revision) for _ in range(3))
    assert run_queue_reason(session, waiting) is None, "two units free"
    cap.claim(sessions, a)
    assert run_queue_reason(session, waiting) is None, "one unit free"
    cap.claim(sessions, b)
    assert run_queue_reason(session, waiting) == "executor_at_capacity"
    assert run_queue_reason(session, a) is None and run_queue_reason(session, b) is None, "a running Run is not waiting"
    cap.cancel(sessions, a)
    assert run_queue_reason(session, waiting) is None, "a unit was released"
    assert run_queue_reason(session, a) is None, "a cancelled Run is not waiting"


def test_a_run_of_the_environment_source_has_no_queue_reason(session) -> None:
    sessions = factory(session)
    assert run_queue_reason(session, cap.queue_run(sessions, None)) is None


def test_a_waiting_pull_run_is_runner_offline_until_a_runner_was_seen_recently(session) -> None:
    sessions = factory(session)
    cid = connection(session, "pull")
    revision = revise(session, cid, replace(PULL, max_claimed_tasks=2, max_active_runs=2)).revision_id
    run = cap.queue_run(sessions, revision)
    assert run_queue_reason(session, run) == "runner_offline", "no runner token at all"
    token = token_of(session, cid)
    assert run_queue_reason(session, run) == "runner_offline", "a token that was never seen"
    seen(session, token, seconds_ago=5)
    assert run_queue_reason(session, run) is None
    seen(session, token, seconds_ago=3600)
    assert run_queue_reason(session, run) == "runner_offline", "a runner last seen an hour ago"
    seen(session, token, seconds_ago=5)
    revoke_runner_token(session, connection_id=cid, token_id=token, roles=ADMIN_ROLES, idempotency_key=key(),
                        actor_uid=ADMIN)
    assert run_queue_reason(session, run) == "runner_offline", "a revoked token is not a runner"


def test_an_offline_runner_is_named_before_a_full_pull_connection(session) -> None:
    unpaused(session)
    sessions = factory(session)
    cid = connection(session, "pull")
    revision = revise(session, cid, PULL).revision_id          # capacity one, no runner ever seen
    held, waiting = cap.queue_run(sessions, revision), cap.queue_run(sessions, revision)
    assert run_queue_reason(session, waiting) == "runner_offline"
    cap.claim(sessions, held)
    assert run_queue_reason(session, waiting) == "runner_offline", "full, but the runner is the cause to act on"
    seen(session, token_of(session, cid), seconds_ago=5)
    assert run_queue_reason(session, waiting) == "executor_at_capacity", "the runner is back; the unit is what is missing"


def test_an_http_connection_is_never_runner_offline(session) -> None:
    sessions = factory(session)
    cid = connection(session)
    revision = revise(session, cid, HTTP).revision_id
    assert run_queue_reason(session, cap.queue_run(sessions, revision)) is None


# --- through the served API ----------------------------------------------------------------------------------------------------


def call(surface, method: str, path: str, body: Any = None, *, keyed: bool = True):
    headers = {"Content-Type": "application/json"}
    if keyed:
        headers["Idempotency-Key"] = f"exec-{uuid4().hex}"
    payload = b"" if body is None else json.dumps(body).encode()
    return dispatch(surface, Request.build(method, path, headers=headers, body=payload))


def made(surface, kind: str = "http_api", settings: dict[str, Any] | None = None) -> str:
    created = call(surface, "POST", "/executor-connections", {"kind": kind, "display_name": "n"})
    assert created.status == 201, created.body
    assert "occupancy" not in created.json(), "no revision yet, so no capacity to show"
    connection_id = created.json()["connection_id"]
    revised = call(surface, "POST", f"/executor-connections/{connection_id}/revisions", settings or HTTP_BODY)
    assert revised.status == 201, revised.body
    return connection_id


def test_the_api_takes_the_capacity_on_a_revision_and_shows_it_back(surface) -> None:
    cid = made(surface, settings={**HTTP_BODY, "max_active_runs": 3})
    detail = call(surface, "GET", f"/executor-connections/{cid}", keyed=False).json()
    assert detail["revisions"][0]["max_active_runs"] == 3
    assert detail["connection"]["occupancy"] == {"capacity": 3, "active_runs": 0, "active_calls": 0}


def test_a_revision_without_a_capacity_shows_none_and_the_connection_still_shows_one(surface) -> None:
    cid = made(surface)
    detail = call(surface, "GET", f"/executor-connections/{cid}", keyed=False).json()
    assert "max_active_runs" not in detail["revisions"][0]
    assert detail["connection"]["occupancy"] == {"capacity": 1, "active_runs": 0, "active_calls": 0}


def test_the_api_shows_the_runs_a_connection_is_serving_in_the_list_and_in_the_detail(surface, session) -> None:
    unpaused(session)
    sessions = factory(session)
    cid = made(surface, settings={**HTTP_BODY, "max_active_runs": 3})
    revision = call(surface, "GET", f"/executor-connections/{cid}", keyed=False).json()["connection"]["current_revision_id"]
    for _ in range(2):
        cap.claim(sessions, cap.queue_run(sessions, revision))
    expected = {"capacity": 3, "active_runs": 2, "active_calls": 0}
    detail = call(surface, "GET", f"/executor-connections/{cid}", keyed=False).json()
    assert detail["connection"]["occupancy"] == expected
    listed = call(surface, "GET", "/executor-connections", keyed=False).json()["items"]
    assert [item["occupancy"] for item in listed if item["connection_id"] == cid] == [expected]


@pytest.mark.parametrize(("kind", "body", "field", "constraint"), [
    ("http_api", {**HTTP_BODY, "max_parallel_calls": 2, "max_active_runs": 3}, "max_parallel_calls", "below_max_active_runs"),
    ("pull", {**PULL_BODY, "max_claimed_tasks": 2, "max_active_runs": 3}, "max_claimed_tasks", "below_max_active_runs"),
    ("http_api", {**HTTP_BODY, "max_active_runs": 17}, "max_active_runs", "range"),
])
def test_a_revision_that_cannot_serve_its_capacity_is_a_422_with_a_field_and_a_constraint(
    surface, kind: str, body: dict[str, Any], field: str, constraint: str,
) -> None:
    created = call(surface, "POST", "/executor-connections", {"kind": kind, "display_name": "n"})
    cid = created.json()["connection_id"]
    answer = call(surface, "POST", f"/executor-connections/{cid}/revisions", body)
    assert answer.status == 422, answer.body
    assert answer.json()["error_code"] == "validation_failed"
    assert answer.json()["details"] == {"field": field, "constraint": constraint}
    listed = call(surface, "GET", f"/executor-connections/{cid}", keyed=False).json()
    assert listed["revisions"] == [] and "occupancy" not in listed["connection"]
