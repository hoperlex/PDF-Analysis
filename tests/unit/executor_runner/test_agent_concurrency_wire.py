"""`EXEC2-PULL-01`: the wire of ``runner_instance_id``, and an agent with ``concurrency = 3`` as a real
subprocess against the fake runner API.

The in-process behaviour of the agent (registry, free slot, a 409) is ``test_agent_concurrency.py``. Here:
the client sends the member only when it is given one, a name outside the stand's pattern is refused before
anything is sent, the stdio bridge sends none, and one agent process that works three tasks at once names
itself the same way in every claim and starts each task once.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import time
from pathlib import Path

import pytest

_NAME = "executor_runner_support"
if _NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_NAME, Path(__file__).with_name("_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module
    _spec.loader.exec_module(_module)
S = sys.modules[_NAME]

_CLIENT = "runner_client_under_test"
if _CLIENT not in sys.modules:
    _cspec = importlib.util.spec_from_file_location(_CLIENT, S.RUNNER_DIR / "runner_client.py")
    _cmod = importlib.util.module_from_spec(_cspec)
    sys.modules[_CLIENT] = _cmod
    _cspec.loader.exec_module(_cmod)
rc = sys.modules[_CLIENT]

NAME = "agent-instance-aaaa"
PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

COUNTING_STUB = r'''
import json, os, sys, time
record_dir = sys.argv[1]
task = json.load(sys.stdin)
with open(os.path.join(record_dir, "runs.log"), "a") as handle:
    handle.write(task["task_id"] + "\n")
time.sleep(1.0)
print(json.dumps({"findings": [{"id": 1}]}))
'''


# -- the client -------------------------------------------------------------------------------------


def test_the_claim_carries_the_instance_only_when_it_is_given_one() -> None:
    with S.FakeRunner() as runner:
        client = rc.RunnerClient(runner.origin, S.TOKEN)
        client.claim(0)
        client.claim(0, 1, runner_instance_id=NAME)
        client.claim(0, 4, runner_instance_id="A" * 64)
        client.claim(0, 1, None)
        assert [r["body"] for r in runner.of_kind("claim")] == [
            {"wait_seconds": 0},
            {"wait_seconds": 0, "runner_instance_id": NAME},
            {"wait_seconds": 0, "max_images": 4, "runner_instance_id": "A" * 64},
            {"wait_seconds": 0}]


@pytest.mark.parametrize("bad", ["", "short", "x" * 65, "has space inside", "slash/in-name", "ключ-агента-1",
                                 "trailing-newline\n", 12345678, b"agent-instance-aaaa"])
def test_a_name_the_stand_would_refuse_is_refused_before_anything_is_sent(bad) -> None:
    with S.FakeRunner() as runner:
        client = rc.RunnerClient(runner.origin, S.TOKEN)
        with pytest.raises(rc.RunnerRejected):
            client.claim(0, 1, runner_instance_id=bad)
        assert runner.of_kind("claim") == []


def test_the_stdio_bridge_names_no_instance() -> None:
    """A Claude Code session behind the bridge is not an agent process: its claim is the one it always was."""
    assert "runner_instance_id" not in (S.RUNNER_DIR / "mcp_bridge.py").read_text()


# -- one agent process, three tasks at once ----------------------------------------------------------


def test_one_agent_with_concurrency_three_works_three_tasks_at_once_and_starts_each_once(tmp_path) -> None:
    records = tmp_path / "records"
    records.mkdir()
    stub = S.write_stub(tmp_path / "stub.py", COUNTING_STUB)
    with S.FakeRunner() as runner:
        for task_id in ("ext_PAR1", "ext_PAR2", "ext_PAR3"):
            runner.add_task(S.make_task(task_id))
        cfg = S.agent_config(
            tmp_path / "agent.toml", runner.origin, argv=[sys.executable, str(stub), str(records)],
            extra_runner="concurrency = 3")
        started = time.monotonic()
        proc = S.AgentProcess(cfg, "--max-tasks", "3")
        code = proc.wait(timeout=40)
        elapsed = time.monotonic() - started
        assert code == 0, proc.stderr
        assert elapsed < 2.4, "three 1 s commands side by side, not one after the other"
        assert sorted(r["task_id"] for r in runner.of_kind("answer")) == ["ext_PAR1", "ext_PAR2", "ext_PAR3"]
        assert runner.of_kind("fail") == []
        assert sorted((records / "runs.log").read_text().split()) == ["ext_PAR1", "ext_PAR2", "ext_PAR3"], (
            "each task was started once")
        names = {r["body"]["runner_instance_id"] for r in runner.of_kind("claim")}
        assert len(names) == 1 and PATTERN.fullmatch(names.pop()), "one process, one name, in every claim"


def test_two_agent_processes_name_themselves_differently(tmp_path) -> None:
    names = []
    for index in range(2):
        with S.FakeRunner() as runner:
            cfg = S.agent_config(tmp_path / f"agent{index}.toml", runner.origin, argv=["/bin/true"])
            with S.AgentProcess(cfg) as proc:
                runner.wait_for("claim", 1, timeout=10)
                names.append(runner.of_kind("claim")[0]["body"]["runner_instance_id"])
                proc.terminate()
                assert proc.wait(timeout=10) == 0
    assert names[0] != names[1] and all(PATTERN.fullmatch(name) for name in names)
