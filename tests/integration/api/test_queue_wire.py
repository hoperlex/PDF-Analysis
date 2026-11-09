"""``listExecutionQueue`` over the wire, through the shipped adapter (`UI-PARITY-QUEUE-A`).

The SQL is asserted in ``tests/integration/execution/test_queue_readable.py``. This module is the edge: the body of an item
(the work it names, a property it does not have omitted and never ``null``), each filter reaching the database, a malformed
value refused as ``validation_failed`` rather than ignored, an empty parameter being the absent one, and a cursor refused
under other filters. The suite shares a long-lived database, so every assertion is about the jobs this test made.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from w13_api_driver import Surface

from auditmanager.api.routers import Router
from auditmanager.api.routers.execution import build_execution_routes
from auditmanager.bootstrap.adapters import ExecutionAdapter
from auditmanager.jobs.public import JobRepository
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.identity import RunId

from .test_query_surface import MixedRun, get, ok

QUEUE = "/execution/queue"


@pytest.fixture
def mixed_run(session: Session) -> MixedRun:
    """The same seeded run the query-surface census drives; a fixture of another module is not visible here."""
    return MixedRun(session)


@pytest.fixture
def queue_surface(shipped_router: Surface, session_factory: sessionmaker[Session]) -> Surface:
    router = Router(credentials=shipped_router.router.credentials)
    build_execution_routes(router, ExecutionAdapter(session_factory, runs=None))  # type: ignore[arg-type]
    return Surface(router)


def _jobs(session: Session, mixed: MixedRun, count: int) -> tuple[list[str], list[datetime]]:
    """``count`` queued jobs of the mixed run's version and the creation instants the database gave them.

    ``job.created_at`` is frozen by ``trg_job_frozen_guard`` and defaults to ``clock_timestamp()``, so the jobs of one
    test have distinct instants in creation order; a period is bounded by them."""
    ids = []
    repo, jobs = RunRepository(), JobRepository()
    for _ in range(count):
        run_id = str(RunId.new())
        repo.create(
            session, run_id=run_id, project_uid=mixed.run.project_uid, version_uid=mixed.run.version_uid,
            analysis_profile_id=mixed.run.analysis_profile_id, prompt_bundle_id=mixed.run.prompt_bundle_id,
            provider_mode="recorded", frozen_input_digest="a" * 64, command_id=None,
        )
        repo.advance(session, run_id=run_id, from_state="created", to_state="queued")
        ids.append(jobs.enqueue(session, run_id=run_id))
    at = [session.execute(text("SELECT created_at FROM job WHERE job_id = :job"), {"job": job}).scalar_one()
          for job in ids]
    assert at == sorted(set(at)), "the test needs jobs created at distinct, increasing instants"
    return ids, at


def _mine(body: dict[str, Any], ids: list[str]) -> list[str]:
    return [item["job_id"] for item in body["items"] if item["job_id"] in ids]


def _z(moment: datetime) -> str:
    return quote(moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"))


def _bounds(at: list[datetime]) -> str:
    """The period that holds exactly the jobs created at these instants (the upper bound is not included)."""
    return f"created_from={_z(at[0])}&created_to={_z(at[-1] + timedelta(microseconds=1))}"


def test_an_item_names_its_work_and_omits_what_the_job_does_not_have(
    queue_surface: Surface, session: Session, mixed_run: MixedRun
) -> None:
    ids, at = _jobs(session, mixed_run, 1)
    body = ok(get(queue_surface, f"{QUEUE}?limit=200&{_bounds(at)}"))
    (item,) = [i for i in body["items"] if i["job_id"] == ids[0]]
    assert item["project_uid"] == mixed_run.run.project_uid
    assert item["version_uid"] == mixed_run.run.version_uid
    assert item["project_name"] and item["document_name"] and item["version_ordinal"] >= 1
    assert item["document_uid"].startswith("doc_")
    # Not null: absent. The contract declares none of these nullable.
    for absent in ("started_at", "finished_at", "error_code", "interrupted_reason", "binding_state", "wait_reason"):
        assert absent not in item, f"{absent} is sent as null"
    assert None not in item.values()


def test_the_state_filter_reaches_the_database_and_a_state_nobody_is_in_is_an_empty_page(
    queue_surface: Surface, session: Session, mixed_run: MixedRun
) -> None:
    ids, at = _jobs(session, mixed_run, 2)
    queued = ok(get(queue_surface, f"{QUEUE}?state=queued&{_bounds(at)}&limit=200"))
    assert _mine(queued, ids) == ids and {i["state"] for i in queued["items"]} == {"queued"}
    for other in ("running", "succeeded", "failed", "cancelled", "dead_letter", "leased", "retry_wait"):
        page = ok(get(queue_surface, f"{QUEUE}?state={other}&{_bounds(at)}&limit=200"))
        assert _mine(page, ids) == [], other


def test_a_state_outside_the_eight_is_refused_not_ignored(queue_surface: Surface) -> None:
    for bad in ("nonsense", "Queued", "completed", "succeeded,failed"):
        answer = get(queue_surface, f"{QUEUE}?state={quote(bad)}")
        assert answer.status == 422, (bad, answer.body)
        assert json.loads(answer.body)["error_code"] == "validation_failed"


def test_a_group_reaches_the_database_and_a_name_outside_the_three_is_refused(
    queue_surface: Surface, session: Session, mixed_run: MixedRun
) -> None:
    """`D-370` (contract 1.43.0): `state_group` lists every job of the group; the empty string is the absent parameter."""
    ids, at = _jobs(session, mixed_run, 2)
    active = ok(get(queue_surface, f"{QUEUE}?state_group=active&{_bounds(at)}&limit=200"))
    assert _mine(active, ids) == ids and {i["state"] for i in active["items"]} <= {"queued", "leased", "running", "retry_wait"}
    for other in ("completed", "errors"):
        assert _mine(ok(get(queue_surface, f"{QUEUE}?state_group={other}&{_bounds(at)}&limit=200")), ids) == [], other
    # The page's counts are the same whatever the group, and the live failures ride every page.
    assert active["overview"] and isinstance(active["live_failure_count"], int)
    whole = ok(get(queue_surface, f"{QUEUE}?limit=200"))
    empty = ok(get(queue_surface, f"{QUEUE}?limit=200&state_group="))
    assert [i["job_id"] for i in empty["items"]] == [i["job_id"] for i in whole["items"]]
    for bad in ("nonsense", "Active", "failed", "active,errors"):
        answer = get(queue_surface, f"{QUEUE}?state_group={quote(bad)}")
        assert answer.status == 422, (bad, answer.body)
        assert json.loads(answer.body)["error_code"] == "validation_failed"


def test_a_state_and_a_group_together_are_refused_with_the_constraint_named(queue_surface: Surface) -> None:
    for query in ("state=failed&state_group=errors", "state=queued&state_group=errors"):
        answer = get(queue_surface, f"{QUEUE}?{query}")
        assert answer.status == 422, (query, answer.body)
        envelope = json.loads(answer.body)
        assert envelope["error_code"] == "validation_failed"
        assert envelope["details"] == {"field": "state_group", "constraint": "conflicts_with_state"}


def test_a_period_without_an_offset_or_not_a_time_is_refused(queue_surface: Surface) -> None:
    for name in ("created_from", "created_to"):
        for bad in ("2032-05-01T00:00:00", "2032-05-01", "yesterday", "1"):
            answer = get(queue_surface, f"{QUEUE}?{name}={quote(bad)}")
            assert answer.status == 422, (name, bad, answer.body)
            assert json.loads(answer.body)["error_code"] == "validation_failed"


def test_the_period_selects_by_creation_and_an_empty_parameter_is_the_absent_one(
    queue_surface: Surface, session: Session, mixed_run: MixedRun
) -> None:
    ids, at = _jobs(session, mixed_run, 3)
    first_two = ok(get(queue_surface, f"{QUEUE}?created_from={_z(at[0])}&created_to={_z(at[2])}&limit=200"))
    assert _mine(first_two, ids) == ids[:2], "the upper bound is not included"
    last = ok(get(queue_surface, f"{QUEUE}?created_from={_z(at[2])}&limit=200"))
    assert _mine(last, ids) == [ids[2]], "the lower bound is included"
    # `?state=&created_from=` change nothing: the empty string is the absent parameter.
    whole = ok(get(queue_surface, f"{QUEUE}?limit=200"))
    empty = ok(get(queue_surface, f"{QUEUE}?limit=200&state=&created_from=&created_to="))
    assert [i["job_id"] for i in empty["items"]] == [i["job_id"] for i in whole["items"]]


def test_a_cursor_is_refused_under_other_filters_and_resumes_under_its_own(
    queue_surface: Surface, session: Session, mixed_run: MixedRun
) -> None:
    ids, at = _jobs(session, mixed_run, 3)
    window = _bounds(at)
    first = ok(get(queue_surface, f"{QUEUE}?state=queued&{window}&limit=1"))
    cursor = first["page"]["next_cursor"]
    assert cursor and [i["job_id"] for i in first["items"]] == [ids[0]]
    second = ok(get(queue_surface, f"{QUEUE}?state=queued&{window}&limit=1&cursor={cursor}"))
    assert [i["job_id"] for i in second["items"]] == [ids[1]]
    for other in (f"{QUEUE}?limit=1&cursor={cursor}", f"{QUEUE}?state=running&{window}&limit=1&cursor={cursor}",
                  f"{QUEUE}?state=queued&limit=1&cursor={cursor}"):
        answer = get(queue_surface, other)
        assert answer.status == 422, (other, answer.body)
        envelope = json.loads(answer.body)
        assert envelope["error_code"] == "validation_failed"
        assert envelope["details"] == {"field": "cursor", "constraint": "scope"}


def test_the_unfiltered_cursor_still_resumes_where_it_always_did(
    queue_surface: Surface, session: Session, mixed_run: MixedRun
) -> None:
    _jobs(session, mixed_run, 2)
    first = ok(get(queue_surface, f"{QUEUE}?limit=1"))
    cursor = first["page"]["next_cursor"]
    assert cursor
    second = ok(get(queue_surface, f"{QUEUE}?limit=1&cursor={cursor}"))
    assert second["items"] and second["items"][0]["job_id"] != first["items"][0]["job_id"]
