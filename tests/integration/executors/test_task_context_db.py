"""`CTX-STAND` on real PostgreSQL: ``getExecutorTaskContext`` over the served application and real rows.

The run is started for real (``start_audit_run`` with a stage plan, plan v3 by the environment), so its consent is the one the estimate writes and
``read_run_cost_policy`` reads back: with the «контекст критику» switch journalled on it holds ``executor_context_policy``, without it it does not. The
task is a row of the pull channel with the payload the adapter writes; the runner is the real application (the seam, the envelope, the runner
adapter), wired the way the composition root wires it (`CRIT-CAPTURE-01` part D): the adapter's claim carries ``context_request`` and its method answers the
operation, and ``build_router(task_context=...)`` declares the route. ``WiredRunner`` below only adds what the stand does not have yet, a source that finds
cases (the encoder's move), and the first test after the fixtures drives the unmodified ``RunnerAdapter`` through an unmodified ``build_router``.

What each case shows, and what it would let through if its rule were missing:

* a run on the stage layout with the switch on: the claim carries the descriptor; the first request is ``unavailable / until_move`` and writes one
  journal row; a repeat is the same body and writes none; the second kind is its own request and the third request does not exist;
* the refusals, each its own start: a legacy run, a consent frozen with the switch off, the cell ``text:main``, a task of another connection's token, and a
  task that is not this token's live claim answer ``404`` or ``409`` and journal nothing;
* a delivered block (a source that finds cases) is remembered in the task, journalled by identity and digest with no word of it, and a repeat returns it
  without asking the source again;
* the journal survives the erase of the product data (the purge's own ``TRUNCATE`` of every PRODUCT table) and holds no text column.
"""

from __future__ import annotations

import json
from contextlib import nullcontext
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.api.routers import build_router
from auditmanager.api.schemas import models
from auditmanager.bootstrap.adapters import ExecutorAdapter
from auditmanager.bootstrap.runner import RunnerAdapter
from auditmanager.executors import public as ex
from auditmanager.executors.public import SourceCase, current_revision, get_task_context
from auditmanager.executors.runner_repository import RunnerRepository
from auditmanager.shared.identity import AttemptId, JobId
from scripts.recovery import product_purge as purge
from tests.integration.executors.conftest import driver
from tests.integration.executors.test_runner_channel import issue, make_connection, runner_call
from tests.integration.runs.test_publication_marker import journal, legacy_run, planned_start, world  # noqa: F401  (world is a fixture)

Request, dispatch = driver.Request, driver.dispatch
PLAN_ENV = "AUDITMANAGER_EXTENDED_ANALYSIS_PLAN"
MODEL = "claude-opus-5"
SCHEMA = {"type": "object", "properties": {"observations": {"type": "array"}}, "required": ["observations"], "additionalProperties": False}


class WiredRunner(RunnerAdapter):
    """``RunnerAdapter`` with a source handed in: the adapter now carries ``context_request`` and answers ``getExecutorTaskContext`` over
    ``executors.public.get_task_context`` itself (`CRIT-CAPTURE-01` part D), with the source of today; this subclass stands for the day the encoder moves
    and a source that finds cases is passed (none means the one of today)."""

    source: Any = None

    def claim_task(self, *, runner, wait_seconds, max_images=None, runner_instance_id=None):  # type: ignore[no-untyped-def]
        task = ex.claim_task(self._sessions, self._principal(runner), wait_seconds=wait_seconds, max_images=max_images,
                             runner_instance_id=runner_instance_id)
        if task is None:
            return None
        return models.ClaimedExecutorTask.model_validate({
            "task_id": task.task_id, "claim_expires_at": task.claim_expires_at, "deadline_at": task.deadline_at, "model": task.model,
            "system": task.system, "user_text": task.user_text, "output_schema": dict(task.output_schema),
            **({"images": list(task.images)} if task.images else {}), **self._host_members(task),
            **({"context_request": [dict(entry) for entry in task.context_request]} if task.context_request else {})})

    def get_task_context(self, *, runner, task_id, kind):  # type: ignore[no-untyped-def]
        def work(session: Session) -> models.ExecutorTaskContext:
            options = {} if self.source is None else {"source": self.source}
            answer = get_task_context(session, self._principal(runner), task_id, kind=kind, **options)
            return models.ExecutorTaskContext.model_validate(answer.wire())
        return self._write(work)


@pytest.fixture(autouse=True)
def plan_v3(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("AUDITMANAGER_EXTENDED_ANALYSIS", "AUDITMANAGER_EXTENDED_COVERAGE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(PLAN_ENV, "v3")


@pytest.fixture
def surface(session: Session, admin_account: str, rings):  # type: ignore[no-untyped-def]
    wired = WiredRunner(lambda: nullcontext(session))  # type: ignore[arg-type,return-value]
    router = build_router(
        projects=None, documents=None, runs=None, findings=None, decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=driver.SuiteCredentialAdapter(roles=frozenset({"admin"})), accounts=driver.SuiteAccountAdapter(),
        registrations=driver.SuiteRegistrationAdapter(), executors=ExecutorAdapter(lambda: nullcontext(session), ring=rings.public),  # type: ignore[arg-type]
        runner=wired, task_context=wired)
    return driver.Surface(router)


@pytest.fixture
def wired_surface(session: Session, admin_account: str, rings):  # type: ignore[no-untyped-def]
    """The composition root's own wiring of the route: ONE unmodified ``RunnerAdapter`` is both ``runner=`` and ``task_context=``, no route is moved by hand
    and no method is added by the test."""
    adapter = RunnerAdapter(lambda: nullcontext(session))  # type: ignore[arg-type,return-value]
    router = build_router(
        projects=None, documents=None, runs=None, findings=None, decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=driver.SuiteCredentialAdapter(roles=frozenset({"admin"})), accounts=driver.SuiteAccountAdapter(),
        registrations=driver.SuiteRegistrationAdapter(), executors=ExecutorAdapter(lambda: nullcontext(session), ring=rings.public),  # type: ignore[arg-type]
        runner=adapter, task_context=adapter)
    return driver.Surface(router)


def seed_attempt(session: Session, run_id: str) -> str:
    """The run's job with a running current Attempt: the Attempt a pull task waits in."""
    job = session.execute(text("SELECT job_id FROM job WHERE run_id = :r"), {"r": run_id}).scalar_one_or_none()
    ids = {"job": job or str(JobId.new()), "attempt": str(AttemptId.new()), "run": run_id}
    if job is None:
        session.execute(text("INSERT INTO job (job_id, run_id) VALUES (:job, :run)"), ids)
    session.execute(text("INSERT INTO attempt (attempt_id, job_id, execution_token) VALUES (:attempt, :job, :token)"),
                    {**ids, "token": f"tok-{ids['attempt']}"})
    session.execute(text("UPDATE attempt SET state = 'leased' WHERE attempt_id = :attempt"), ids)
    session.execute(text("UPDATE attempt SET state = 'running' WHERE attempt_id = :attempt"), ids)
    session.execute(text("UPDATE job SET state = 'leased', current_attempt_id = :attempt WHERE job_id = :job"), ids)
    session.execute(text("UPDATE job SET state = 'running' WHERE job_id = :job"), ids)
    return ids["attempt"]


def critic_payload(cell: str = "review:main", ids: tuple[str, ...] = ("xri_1", "xri_2"), section: str = "AI") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "system": "SYSTEM", "output_schema": SCHEMA,
        "user_text": json.dumps({"observations": [{"input_id": identity, "title": f"Т{identity}", "description": f"Описание {identity}"}
                                                    for identity in ids]}, ensure_ascii=False),
        "host": {"provider": "claude_code", "access": "subscription", "model_id": MODEL, "effort": "medium", "timeout_seconds": 600,
                 "cell_key": cell}}
    if ids:
        from auditmanager.executors.task_context import context_request_of

        payload["context_request"] = context_request_of(payload["user_text"], section=section)
    return payload


class Stand:
    """A connection with a token, and the means to write a task on it."""

    def __init__(self, session: Session, surface: Any) -> None:
        self.session, self.surface = session, surface
        self.connection_id = make_connection(surface)
        self.token, self.meta = issue(surface, self.connection_id)

    def task(self, run_id: str, payload: dict[str, Any], *, attempt: str | None = None) -> str:
        revision = current_revision(self.session, self.connection_id)
        assert revision is not None
        record = RunnerRepository().insert_task(
            self.session, connection_id=self.connection_id, revision_id=revision.revision_id, origin="run_call", run_id=run_id,
            attempt_id=attempt or seed_attempt(self.session, run_id), model_call_id=None, probe_id=None, expected_model=MODEL,
            payload=payload, deadline_seconds=600)
        return record.task_id

    def claim(self) -> dict[str, Any]:
        answer = runner_call(self.surface, self.token, "/runner/tasks/claim", {"wait_seconds": 0})
        assert answer.status == 200, answer.body
        return answer.json()

    def context(self, task_id: str, kind: str = "similar_cases", token: str | None = None):  # type: ignore[no-untyped-def]
        return runner_call(self.surface, token or self.token, f"/runner/tasks/{task_id}/context", {"kind": kind})

    def journal_count(self, task_id: str | None = None) -> int:
        query = "SELECT count(*) FROM executor_task_context_delivery" + (" WHERE task_id = :t" if task_id else "")
        return int(self.session.execute(text(query), {"t": task_id}).scalar_one())


def planned_run(session: Session, scene: dict[str, Any], *, switch: bool) -> str:
    """The real start of a run on the stage layout, with the «контекст критику» switch journalled on first or not."""
    if switch:
        journal(session, scene, True, name="critic_context")
    return planned_start(session, scene).run_id


# -- a run on the stage layout, the switch on ---------------------------------------------------------------------


def test_the_claim_carries_the_descriptor_and_the_first_request_is_unavailable_until_move_and_journalled_once(session, surface, world) -> None:  # type: ignore[no-untyped-def]
    run = planned_run(session, world, switch=True)
    stand = Stand(session, surface)
    task = stand.task(run, critic_payload())
    claimed = stand.claim()
    assert claimed["task_id"] == task
    assert [entry["input_id"] for entry in claimed["context_request"]] == ["xri_1", "xri_2"] and {e["section"] for e in claimed["context_request"]} == {"AI"}
    models.ClaimedExecutorTask.model_validate(claimed)

    first = stand.context(task)
    assert first.status == 200, first.body
    assert first.json() == {"kind": "similar_cases", "status": "unavailable", "reason": "until_move", "items": [], "not_fitted": 0}
    rows = session.execute(text("SELECT kind, status, reason, case_ids, characters, block_sha256, run_id, task_id FROM executor_task_context_delivery "
                                "WHERE task_id = :t"), {"t": task}).all()
    assert [tuple(row) for row in rows] == [("similar_cases", "unavailable", "until_move", [], 0, None, run, task)]

    again = stand.context(task)
    assert again.status == 200 and again.json() == first.json() and again.body == first.body, "the same answer, byte for byte"
    assert stand.journal_count(task) == 1, "a repeat spends nothing"

    patterns = stand.context(task, "patterns")
    assert patterns.status == 200 and patterns.json()["reason"] == "patterns_not_available" and stand.journal_count(task) == 2
    assert stand.context(task, "patterns").json() == patterns.json() and stand.journal_count(task) == 2, "two requests a task, whatever the repeats"
    assert stand.context(task, "norm_excerpts").status == 422 and stand.journal_count(task) == 2


def test_the_wired_route_answers_through_the_real_adapter_unavailable_until_move(session, wired_surface, world) -> None:  # type: ignore[no-untyped-def]
    """`CRIT-CAPTURE-01` part D. The route as the composition root builds it: the claim carries the descriptor (the adapter maps ``context_request``), the ask
    is answered by the adapter's own method and its answer is ``unavailable / until_move`` (no source that searches is handed in), journalled once.
    Were the adapter's ``context_request`` mapping missing the claim would carry none; were ``task_context=`` not passed the route would answer ``503``."""
    run = planned_run(session, world, switch=True)
    stand = Stand(session, wired_surface)
    task = stand.task(run, critic_payload())
    claimed = stand.claim()
    assert [entry["input_id"] for entry in claimed["context_request"]] == ["xri_1", "xri_2"]
    answer = stand.context(task)
    assert answer.status == 200, answer.body
    assert answer.json() == {"kind": "similar_cases", "status": "unavailable", "reason": "until_move", "items": [], "not_fitted": 0}
    assert stand.journal_count(task) == 1
    assert stand.context(task).body == answer.body and stand.journal_count(task) == 1


def test_a_task_without_a_descriptor_claims_without_the_member_through_the_real_adapter(session, wired_surface, world) -> None:  # type: ignore[no-untyped-def]
    run = planned_run(session, world, switch=True)
    stand = Stand(session, wired_surface)
    stand.task(run, critic_payload(ids=()))
    assert "context_request" not in stand.claim(), "absent for any other task, never an empty list"


# -- the refusals ---------------------------------------------------------------------------------------------------


def test_a_legacy_run_is_not_offered_reference_data(session, surface, world) -> None:  # type: ignore[no-untyped-def]
    journal(session, world, True, name="critic_context")
    run = legacy_run(session, world)
    stand = Stand(session, surface)
    task = stand.task(run, critic_payload())
    assert "context_request" in stand.claim(), "the descriptor is in the payload by hand here; the stand does not look at it for a legacy run"
    answer = stand.context(task)
    assert answer.status == 404 and answer.json()["error_code"] == "not_found" and stand.journal_count() == 0


def test_a_consent_frozen_with_the_switch_off_is_not_offered_reference_data_even_if_the_switch_is_on_now(session, surface, world) -> None:  # type: ignore[no-untyped-def]
    run = planned_run(session, world, switch=False)
    journal(session, world, True, name="critic_context")  # the switch is turned on after the start: the consent holds no policy
    stand = Stand(session, surface)
    task = stand.task(run, critic_payload())
    stand.claim()
    answer = stand.context(task)
    assert answer.status == 404 and answer.json()["error_code"] == "not_found" and stand.journal_count() == 0


@pytest.mark.parametrize("cell", ["text:main", "blocks:main", "correction:main"])
def test_no_other_cell_is_offered_reference_data(session, surface, world, cell: str) -> None:  # type: ignore[no-untyped-def]
    run = planned_run(session, world, switch=True)
    stand = Stand(session, surface)
    task = stand.task(run, critic_payload(cell=cell))
    stand.claim()
    answer = stand.context(task)
    assert answer.status == 404 and stand.journal_count() == 0


def test_a_task_without_a_descriptor_is_not_offered_reference_data(session, surface, world) -> None:  # type: ignore[no-untyped-def]
    run = planned_run(session, world, switch=True)
    stand = Stand(session, surface)
    task = stand.task(run, critic_payload(ids=()))
    assert "context_request" not in stand.claim()
    assert stand.context(task).status == 404 and stand.journal_count() == 0


def test_a_token_of_another_connection_reads_nothing_and_an_unclaimed_or_finished_task_is_a_conflict(session, surface, world) -> None:  # type: ignore[no-untyped-def]
    run = planned_run(session, world, switch=True)
    stand, stranger = Stand(session, surface), Stand(session, surface)
    open_task = stand.task(run, critic_payload())
    # not claimed yet: the claim is not this token's
    unclaimed = stand.context(open_task)
    assert unclaimed.status == 409 and unclaimed.json()["error_code"] == "conflict" and unclaimed.json()["details"]["conflict_reason"] == "claim_lost"
    stand.claim()
    # the claim is held, but by another connection's token it is nobody's: 404, as for a task that does not exist
    foreign = stand.context(open_task, token=stranger.token)
    assert foreign.status == 404 and foreign.json()["error_code"] == "not_found"
    assert stand.context("ext_01M2545JSD15ETSNNV904X991K").status == 404
    assert stand.journal_count() == 0, "nothing was read, nothing was journalled"
    # finished: answered tasks are terminal
    done = runner_call(stand.surface, stand.token, f"/runner/tasks/{open_task}/answer", {"output_text": '{"observations": []}', "model": MODEL})
    assert done.status == 200, done.body
    finished = stand.context(open_task)
    assert finished.status == 409 and finished.json()["details"]["conflict_reason"] == "task_terminal" and stand.journal_count() == 0


def test_a_lapsed_claim_is_a_conflict_not_a_read(session, surface, world) -> None:  # type: ignore[no-untyped-def]
    run = planned_run(session, world, switch=True)
    stand = Stand(session, surface)
    task = stand.task(run, critic_payload())
    stand.claim()
    session.execute(text("UPDATE executor_task SET claim_expires_at = clock_timestamp() - interval '1 second' WHERE task_id = :t"), {"t": task})
    lapsed = stand.context(task)
    assert lapsed.status == 409 and lapsed.json()["details"]["conflict_reason"] == "claim_lost" and stand.journal_count() == 0


# -- a block that is delivered -----------------------------------------------------------------------------------------


class Finds:
    """A source that finds cases and counts its questions."""

    def __init__(self) -> None:
        self.asked = 0

    def read(self, session: Any, *, run_id: str, kind: str, inputs: Any) -> Any:
        self.asked += 1
        return {entry.input_id: [SourceCase(f"dmc_{n:026d}", "rejected", "dimensions", 0.91, f"Находка {entry.input_id} {n}", f"Рекомендация {n}")
                                 for n in (1, 2)] for entry in inputs}


def test_a_delivered_block_is_remembered_in_the_task_journalled_without_a_word_of_it_and_returned_again_without_asking(session, surface, world, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    run = planned_run(session, world, switch=True)
    stand = Stand(session, surface)
    source = Finds()
    monkeypatch.setattr(WiredRunner, "source", source)      # the encoder's move: from here the adapter hands the function a source that finds cases
    task = stand.task(run, critic_payload())
    stand.claim()
    first = stand.context(task)
    assert first.status == 200, first.body
    body = first.json()
    assert body["status"] == "available" and "reason" not in body and body["not_fitted"] == 0 and len(body["context_sha256"]) == 64
    assert [item["input_id"] for item in body["items"]] == ["xri_1", "xri_2"] and all(len(item["cases"]) == 2 for item in body["items"])
    models.ExecutorTaskContext.model_validate(body)
    row = session.execute(text("SELECT status, reason, case_ids, characters, block_sha256 FROM executor_task_context_delivery WHERE task_id = :t"),
                          {"t": task}).one()
    assert (row.status, row.reason, row.block_sha256) == ("delivered", None, body["context_sha256"])
    assert row.case_ids == [f"dmc_{n:026d}" for _ in range(2) for n in (1, 2)] and row.characters > 0
    # the journal holds identities and a digest; no word of the cases is anywhere in it
    kept = json.dumps(list(row), default=str, ensure_ascii=False)
    assert "Находка" not in kept and "Рекомендация" not in kept
    # the block is in the task's own payload (a PRODUCT row), under the kind
    payload = session.execute(text("SELECT payload FROM executor_task WHERE task_id = :t"), {"t": task}).scalar_one()
    assert payload["context_answers"]["similar_cases"]["items"] == body["items"]
    assert {"system", "output_schema", "user_text", "host", "context_request"} <= set(payload), "the task's own members are as they were"

    again = stand.context(task)
    assert again.body == first.body and source.asked == 1 and stand.journal_count(task) == 1, "a repeat asks nothing and spends nothing"


# -- the journal outlives the erase ----------------------------------------------------------------------------------------


def test_the_journal_survives_the_purge_of_every_product_table_and_has_no_text_column(session, surface, world) -> None:  # type: ignore[no-untyped-def]
    run = planned_run(session, world, switch=True)
    stand = Stand(session, surface)
    task = stand.task(run, critic_payload())
    stand.claim()
    assert stand.context(task).status == 200 and stand.journal_count(task) == 1
    assert "executor_task_context_delivery" in purge.KEEP_TABLES and "executor_task_context_delivery" not in purge.PRODUCT_TABLES
    # what the product purge does to the product data: one TRUNCATE of every PRODUCT table (a foreign key from the journal would refuse it)
    session.execute(text("TRUNCATE TABLE " + ", ".join(sorted(purge.PRODUCT_TABLES))))
    assert session.execute(text("SELECT count(*) FROM executor_task WHERE task_id = :t"), {"t": task}).scalar_one() == 0
    assert session.execute(text("SELECT count(*) FROM audit_run WHERE run_id = :r"), {"r": run}).scalar_one() == 0
    survivor = session.execute(text("SELECT task_id, run_id, kind, status, reason FROM executor_task_context_delivery WHERE task_id = :t"), {"t": task}).one()
    assert tuple(survivor) == (task, run, "similar_cases", "unavailable", "until_move")
    columns = {row[0]: row[1] for row in session.execute(text(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'executor_task_context_delivery'"))}
    assert set(columns) == {"delivery_id", "task_id", "run_id", "model_call_id", "kind", "status", "reason", "case_ids", "characters",
                            "block_sha256", "delivered_at"}, "identities, a digest and counts: the table has no place for a case's words"
