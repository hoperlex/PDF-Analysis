"""`EXEC2-PULL-01` (ADR-0026 decision 3): the agent's registry of tasks in work, its name in every claim,
and the free local slot it claims with.

In process. ``agent.Agent`` runs for real, its claim loop and its worker threads included; two things are
stood in for: the stand (a scripted client that hands out task ids in a fixed order, so that handing the
same id out twice *is* a redelivery) and the local command (``run_command``, which counts how often each
task was started and can hold a task until the test lets it go). The wire and the subprocess are in
``test_agent.py`` and ``test_agent_concurrency_wire.py``.

Nothing here is a stopwatch on the green side: the test waits for the events it needs and gives each wait a
generous bound.
"""

from __future__ import annotations

import importlib.util
import io
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

import pytest

_NAME = "executor_runner_support"
if _NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_NAME, Path(__file__).with_name("_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module
    _spec.loader.exec_module(_module)
S = sys.modules[_NAME]

INSTANCE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def _agent_module():
    sys.path.insert(0, str(S.RUNNER_DIR))
    try:
        spec = importlib.util.spec_from_file_location("exec_agent_concurrency_under_test", S.AGENT)
        module = importlib.util.module_from_spec(spec)
        sys.modules["exec_agent_concurrency_under_test"] = module  # dataclasses resolve annotations through it
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(S.RUNNER_DIR))


@pytest.fixture
def agent(monkeypatch: pytest.MonkeyPatch):
    module = _agent_module()
    monkeypatch.setattr(module, "DUPLICATE_DELIVERY_PAUSE_SECONDS", 0.01)
    return module


class FakeClient:
    """The stand, as far as the agent can tell. ``script`` is the task ids it hands out, in order; an id
    that appears twice is handed out twice, as a token with a limit of one is handed its held task again."""

    origin = "http://127.0.0.1:1"

    def __init__(self, script: list[str], *, answer_error: Exception | None = None,
                 model: str = "claude-opus-5") -> None:
        self._script = list(script)
        self._answer_error = answer_error
        self._model = model
        self._lock = threading.Lock()
        self.instances: list[str | None] = []
        self.timeline: list[tuple[str, str | None]] = []
        self.answers: list[str] = []
        self.fails: list[tuple[str, str]] = []

    def scrub(self, text: str) -> str:
        return text

    def seconds_until(self, stamp: str) -> float:
        return 600.0

    def claim(self, wait_seconds: int, max_images: int = 1, runner_instance_id: str | None = None):
        with self._lock:
            self.instances.append(runner_instance_id)
            task_id = self._script.pop(0) if self._script else None
            self.timeline.append(("claim", task_id))
        if task_id is None:
            time.sleep(0.02)  # a 204 after a short wait: the loop must not spin
            return None
        return S.make_task(task_id, model=self._model, lease=120, window=600)

    def extend(self, task_id: str) -> dict:
        return {"claim_expires_at": S.stamp(time.time() + 120)}

    def answer(self, task_id: str, output_text: str, model: str, input_tokens=None, output_tokens=None) -> dict:
        with self._lock:
            self.timeline.append(("answer", task_id))
            self.answers.append(task_id)
        if self._answer_error is not None:
            raise self._answer_error
        return {"task_id": task_id, "state": "answered"}

    def fail(self, task_id: str, reason: str) -> dict:
        with self._lock:
            self.timeline.append(("fail", task_id))
            self.fails.append((task_id, reason))
        return {"task_id": task_id, "state": "failed"}


class Work:
    """The local command, replaced. ``started`` counts how often each task id was started; a task in
    ``hold`` stays in work until its gate is set. ``mode`` makes the command misbehave."""

    def __init__(self, agent_module: Any, *, hold: tuple[str, ...] = (), mode: str = "answer") -> None:
        self._agent = agent_module
        self.gates = {task_id: threading.Event() for task_id in hold}
        self.started: dict[str, int] = {}
        self._mode = mode
        self._lock = threading.Lock()

    def __call__(self, cfg: Any, task: dict, budget: float, should_stop: Callable[[], str]):
        task_id = task["task_id"]
        with self._lock:
            self.started[task_id] = self.started.get(task_id, 0) + 1
        gate = self.gates.get(task_id)
        if gate is not None and not gate.wait(30):
            raise self._agent.ExecutorFailure("timeout", "the test never released the task")
        if self._mode == "failure":
            raise self._agent.ExecutorFailure("command_failed", "exit status 1")
        if self._mode == "not_json":
            return self._agent.Answer("this is not json")
        return self._agent.Answer('{"findings": []}')


def _build(agent_module, script: list[str], *, concurrency: int = 1, instance_id: str | None = None,
           answer_error: Exception | None = None, model: str = "claude-opus-5"):
    cfg = agent_module.Config(
        origin="https://stand.example.org", declared_model="claude-opus-5", command_argv=["unused"],
        concurrency=concurrency, wait_seconds=1, drain_seconds=5.0)
    client = FakeClient(script, answer_error=answer_error, model=model)
    log = io.StringIO()
    return agent_module.Agent(cfg, client, "", log, instance_id=instance_id), client, log


def _wait_until(predicate: Callable[[], bool], what: str, timeout: float = 10.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError(f"timed out waiting for {what}")


def _run_in_thread(agent_obj: Any, max_tasks: int) -> tuple[threading.Thread, dict]:
    result: dict = {}
    thread = threading.Thread(target=lambda: result.update(code=agent_obj.run(max_tasks)), daemon=True)
    thread.start()
    return thread, result


# -- the agent names itself -------------------------------------------------------------------------


def test_every_claim_names_this_process_and_a_new_process_names_itself_anew(agent, monkeypatch) -> None:
    monkeypatch.setattr(agent, "run_command", Work(agent))
    first, client, log = _build(agent, ["ext_A", "ext_B"])
    assert first.run(2) == 0
    assert len(client.instances) >= 2 and set(client.instances) == {first.instance_id}
    assert INSTANCE_PATTERN.fullmatch(first.instance_id), "the wire's pattern, 8 to 64 characters"
    assert f"instance={first.instance_id}" in log.getvalue()
    second, _, _ = _build(agent, [])
    assert second.instance_id != first.instance_id, "a restarted agent is a different instance"
    ids = {agent.new_instance_id() for _ in range(200)}
    assert len(ids) == 200 and all(INSTANCE_PATTERN.fullmatch(i) for i in ids)


def test_an_instance_id_that_is_handed_in_is_the_one_sent(agent, monkeypatch) -> None:
    monkeypatch.setattr(agent, "run_command", Work(agent))
    fixed, client, _ = _build(agent, ["ext_A"], instance_id="fixed-instance-0001")
    assert fixed.run(1) == 0
    assert set(client.instances) == {"fixed-instance-0001"}


# -- the registry -----------------------------------------------------------------------------------


def test_a_task_delivered_again_while_in_work_is_not_started_twice(agent, monkeypatch) -> None:
    """A token whose limit is one is handed its held task by every claim. The agent has two slots, so the
    second claim finds a free one and is handed ``ext_A`` again: it must not start it a second time."""
    work = Work(agent, hold=("ext_A",))
    monkeypatch.setattr(agent, "run_command", work)
    obj, client, log = _build(agent, ["ext_A", "ext_A", "ext_A", "ext_B"], concurrency=2)
    thread, result = _run_in_thread(obj, 2)
    _wait_until(lambda: "ext_B" in client.answers, "the task behind the redeliveries to be answered")
    _wait_until(lambda: obj.in_work() == frozenset({"ext_A"}), "ext_B to leave the registry, ext_A still in it")
    work.gates["ext_A"].set()
    thread.join(15)
    assert not thread.is_alive() and result == {"code": 0}
    assert work.started == {"ext_A": 1, "ext_B": 1}, "the redelivered id was started once"
    assert sorted(client.answers) == ["ext_A", "ext_B"] and client.fails == []
    assert log.getvalue().count("delivered again while still in work") == 2
    assert obj.in_work() == frozenset()


def test_a_redelivery_is_not_a_task_claimed_for_the_max_tasks_count(agent, monkeypatch) -> None:
    """``--max-tasks N`` stops after N tasks *claimed*; a redelivery of a task in work is not another."""
    work = Work(agent, hold=("ext_A",))
    monkeypatch.setattr(agent, "run_command", work)
    obj, client, _ = _build(agent, ["ext_A", "ext_A", "ext_A"], concurrency=2)
    thread, result = _run_in_thread(obj, 2)
    _wait_until(lambda: len(client.instances) >= 6, "the agent to go on claiming past the redeliveries")
    assert thread.is_alive(), "two redeliveries of one task are one task: the agent is not done"
    obj.stop.set()
    work.gates["ext_A"].set()
    thread.join(15)
    assert not thread.is_alive() and work.started == {"ext_A": 1}


def test_the_registry_admits_one_of_many_racing_deliveries_of_one_id(agent) -> None:
    obj, _, _ = _build(agent, [])
    start = threading.Barrier(8)
    admitted: list[bool] = []
    lock = threading.Lock()

    def deliver() -> None:
        start.wait(timeout=10)
        won = obj._enter_work("ext_RACE")
        with lock:
            admitted.append(won)

    threads = [threading.Thread(target=deliver) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)
    assert admitted.count(True) == 1 and admitted.count(False) == 7
    assert obj.in_work() == frozenset({"ext_RACE"})
    obj._leave_work("ext_RACE")
    assert obj.in_work() == frozenset() and obj._enter_work("ext_RACE") is True, "an id that ended can come back"


@pytest.mark.parametrize("mode", ["answer", "failure", "not_json"])
def test_the_registry_is_cleared_on_every_way_a_task_can_end(agent, monkeypatch, mode: str) -> None:
    monkeypatch.setattr(agent, "run_command", Work(agent, mode=mode))
    obj, client, _ = _build(agent, ["ext_A"])
    assert obj.run(1) == 0
    assert obj.in_work() == frozenset()
    assert (len(client.answers), len(client.fails)) == ((1, 0) if mode == "answer" else (0, 1))


def test_a_task_that_pins_another_model_is_failed_and_leaves_no_trace_in_the_registry(agent, monkeypatch) -> None:
    work = Work(agent)
    monkeypatch.setattr(agent, "run_command", work)
    obj, client, _ = _build(agent, ["ext_A"], model="claude-sonnet-5")
    assert obj.run(1) == 0
    assert work.started == {} and obj.in_work() == frozenset()
    assert client.fails[0][1].startswith("model_mismatch")


# -- a free local slot ------------------------------------------------------------------------------


def test_the_agent_claims_only_when_a_local_slot_is_free(agent, monkeypatch) -> None:
    work = Work(agent, hold=("ext_A", "ext_B"))
    monkeypatch.setattr(agent, "run_command", work)
    obj, client, _ = _build(agent, ["ext_A", "ext_B", "ext_C"], concurrency=2)
    thread, result = _run_in_thread(obj, 3)
    _wait_until(lambda: set(work.started) == {"ext_A", "ext_B"}, "both slots to be taken")
    time.sleep(1.3)  # the loop looks for a free slot every half second: it would have claimed by now
    assert len(client.instances) == 2, "a claim was made with no free slot"
    work.gates["ext_A"].set()
    _wait_until(lambda: "ext_C" in work.started, "the freed slot to claim the third task")
    assert len(client.instances) >= 3
    work.gates["ext_B"].set()
    thread.join(15)
    assert not thread.is_alive() and result == {"code": 0}
    assert sorted(client.answers) == ["ext_A", "ext_B", "ext_C"]


def test_a_sequential_agent_claims_answers_and_claims_again_as_before(agent, monkeypatch) -> None:
    """`concurrency = 1`, the default and every agent deployed before: one slot, so a claim is made only after
    the previous task's answer, in the order the stand handed the tasks out."""
    monkeypatch.setattr(agent, "run_command", Work(agent))
    obj, client, _ = _build(agent, ["ext_A", "ext_B", "ext_C"])
    assert obj.cfg.concurrency == 1 and obj.run(3) == 0
    assert client.timeline == [
        ("claim", "ext_A"), ("answer", "ext_A"), ("claim", "ext_B"), ("answer", "ext_B"),
        ("claim", "ext_C"), ("answer", "ext_C")]
    assert client.fails == [] and obj.in_work() == frozenset()


# -- a 409 aborts the submission --------------------------------------------------------------------


@pytest.mark.parametrize("status, error_class", [(409, "RunnerConflict"), (404, "RunnerNotFound")])
def test_a_refusal_of_the_answer_aborts_the_submission_without_a_retry_or_a_fail(
    agent, monkeypatch, status: int, error_class: str,
) -> None:
    """The task is no longer this runner's to answer: the answer is sent once, nothing is sent after it,
    and the task id leaves the registry (so a later delivery of that id would be worked on afresh)."""
    monkeypatch.setattr(agent, "run_command", Work(agent))
    error = getattr(agent, error_class)("the claim is lost", status=status, error_code="conflict")
    obj, client, log = _build(agent, ["ext_A"], answer_error=error)
    assert obj.run(1) == 0
    assert client.answers == ["ext_A"], "the answer was sent once"
    assert client.fails == [] and obj.in_work() == frozenset()
    assert "no longer accepts" in log.getvalue()
