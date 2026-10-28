"""agent.py in both modes, as a real subprocess, against a fake runner API."""

from __future__ import annotations

import importlib.util
import base64
import hashlib
import json
import os
import shutil
import subprocess
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

STUB = r'''
import hashlib, json, os, sys, time
record_dir = sys.argv[1]
task = json.load(sys.stdin)
tid = task["task_id"]
open(os.path.join(record_dir, tid + ".in.json"), "w").write(json.dumps(task))
open(os.path.join(record_dir, tid + ".pid"), "w").write(str(os.getpid()))
if task.get("local_images"):
    image = task["local_images"][0]
    raw = open(image["path"], "rb").read()
    open(os.path.join(record_dir, tid + ".image.sha256"), "w").write(hashlib.sha256(raw).hexdigest())
if tid.startswith("ext_SLOW"):
    time.sleep(2.5)
elif tid.startswith("ext_LONG"):
    time.sleep(6)
elif tid.startswith("ext_PAR"):
    time.sleep(1.0)
elif tid.startswith("ext_VSLOW"):
    time.sleep(30)
elif tid.startswith("ext_EXIT1"):
    sys.exit(1)
elif tid.startswith("ext_EMPTY"):
    sys.exit(0)
elif tid.startswith("ext_NOTJSON"):
    print("this is not json")
    sys.exit(0)
print(json.dumps({"findings": [{"id": 1}]}))
'''


def _run(tmp_path, runner, tasks, *, max_tasks=None, declared="claude-opus-5", command_timeout=30.0, extra_runner="", timeout=40.0, accept_images=False):
    records = tmp_path / "records"
    records.mkdir(exist_ok=True)
    stub = S.write_stub(tmp_path / "stub.py", STUB)
    cfg = S.agent_config(
        tmp_path / "agent.toml", runner.origin, argv=[sys.executable, str(stub), str(records)],
        declared=declared, command_timeout=command_timeout, extra_runner=extra_runner,
        accept_images=accept_images,
    )
    for task in tasks:
        runner.add_task(task)
    proc = S.AgentProcess(cfg, "--max-tasks", str(max_tasks or len(tasks)))
    code = proc.wait(timeout=timeout)
    return proc, code, records


def _agent_module():
    sys.path.insert(0, str(S.RUNNER_DIR))
    try:
        spec = importlib.util.spec_from_file_location("exec_agent_under_test", S.AGENT)
        module = importlib.util.module_from_spec(spec)
        sys.modules["exec_agent_under_test"] = module  # dataclasses resolve string annotations through sys.modules
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(S.RUNNER_DIR))


def test_command_mode_answers_a_task_and_exits_at_max_tasks(tmp_path):
    with S.FakeRunner() as runner:
        proc, code, records = _run(tmp_path, runner, [S.make_task("ext_OK1")])
        assert code == 0, proc.stderr
        answer = runner.of_kind("answer")[0]
        assert answer["path"] == "/api/v1/runner/tasks/ext_OK1/answer" and answer["authorization"] == "Bearer " + S.TOKEN
        assert answer["body"]["model"] == "claude-opus-5"  # declared by the config
        assert json.loads(answer["body"]["output_text"]) == {"findings": [{"id": 1}]}
        seen = json.loads((records / "ext_OK1.in.json").read_text())  # the task JSON reached the command's stdin
        assert {"task_id", "model", "system", "user_text", "output_schema"} <= set(seen)
        assert seen["user_text"].startswith("Document text") and seen["output_schema"]["required"] == ["findings"]
        assert runner.of_kind("fail") == []


def test_image_is_fetched_verified_and_visible_to_the_command_only_while_it_runs(tmp_path):
    raw = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL7WQAAAABJRU5ErkJggg=="
    )
    digest = hashlib.sha256(raw).hexdigest()
    image = {"blob_id": "blob_01M2545JSD15ETSNNV904X991F",
             "portal_block_id": "blk_" + "a" * 32,
             "sha256": digest, "size_bytes": len(raw), "media_type": "image/png"}
    with S.FakeRunner() as runner:
        runner.add_image(image["blob_id"], raw)
        proc, code, records = _run(tmp_path, runner, [S.make_task("ext_IMG1", images=[image])],
                                   accept_images=True)
        assert code == 0, proc.stderr
        assert len(runner.of_kind("image")) == 1
        assert runner.of_kind("answer")
        assert (records / "ext_IMG1.image.sha256").read_text() == digest
        seen = json.loads((records / "ext_IMG1.in.json").read_text())
        assert not Path(seen["local_images"][0]["path"]).exists()


def test_image_task_without_explicit_command_support_fails_before_fetch(tmp_path):
    image = {"blob_id": "blob_01M2545JSD15ETSNNV904X991F",
             "portal_block_id": "blk_" + "a" * 32,
             "sha256": "a" * 64, "size_bytes": 12, "media_type": "image/png"}
    with S.FakeRunner() as runner:
        proc, code, records = _run(tmp_path, runner, [S.make_task("ext_IMG2", images=[image])])
        assert code == 0, proc.stderr
        assert runner.of_kind("fail")[0]["body"]["reason"] == "image_input_unsupported"
        assert runner.of_kind("image") == []
        assert not list(records.glob("*.in.json"))


def test_changed_image_bytes_fail_before_command_and_are_not_logged(tmp_path):
    image = {"blob_id": "blob_01M2545JSD15ETSNNV904X991F",
             "portal_block_id": "blk_" + "a" * 32,
             "sha256": "a" * 64, "size_bytes": 8, "media_type": "image/png"}
    with S.FakeRunner() as runner:
        runner.add_image(image["blob_id"], b"not a PNG")
        proc, code, records = _run(tmp_path, runner, [S.make_task("ext_IMG3", images=[image])],
                                   accept_images=True)
        assert code == 0, proc.stderr
        assert runner.of_kind("fail")[0]["body"]["reason"] == "image_delivery_failed"
        assert not list(records.glob("*.in.json"))
        assert image["sha256"] not in proc.stderr and S.TOKEN not in proc.stderr


def test_endpoint_mode_asks_a_local_openai_server_and_reports_its_usage(tmp_path):
    with S.FakeRunner() as runner, S.FakeOpenAI(content='{"findings": []}') as endpoint:
        cfg = S.agent_config(tmp_path / "agent.toml", runner.origin, mode="endpoint", endpoint_url=endpoint.url)
        runner.add_task(S.make_task("ext_EP1"))
        proc = S.AgentProcess(cfg, "--max-tasks", "1")
        assert proc.wait() == 0, proc.stderr
        request = endpoint.requests[0]["body"]
        assert request["model"] == "local-model" and request["stream"] is False
        assert [m["role"] for m in request["messages"]] == ["system", "user"]
        assert request["messages"][1]["content"].startswith("Document text") and "response_format" not in request
        answer = runner.of_kind("answer")[0]["body"]
        assert answer == {"output_text": '{"findings": []}', "model": "claude-opus-5", "input_tokens": 11, "output_tokens": 7}


def test_endpoint_json_schema_mode_passes_the_task_schema(tmp_path):
    with S.FakeRunner() as runner, S.FakeOpenAI() as endpoint:
        cfg = S.agent_config(tmp_path / "agent.toml", runner.origin, mode="endpoint", endpoint_url=endpoint.url, extra_endpoint='response_format = "json_schema"')
        runner.add_task(S.make_task("ext_EP2"))
        proc = S.AgentProcess(cfg, "--max-tasks", "1")
        assert proc.wait() == 0, proc.stderr
        rf = endpoint.requests[0]["body"]["response_format"]
        assert rf["type"] == "json_schema" and rf["json_schema"]["schema"]["required"] == ["findings"]


def test_endpoint_image_is_verified_and_sent_as_openai_image_content(tmp_path):
    raw = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL7WQAAAABJRU5ErkJggg=="
    )
    image = {"blob_id": "blob_01M2545JSD15ETSNNV904X991F",
             "portal_block_id": "blk_" + "a" * 32,
             "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw),
             "media_type": "image/png"}
    with S.FakeRunner() as runner, S.FakeOpenAI() as endpoint:
        cfg = S.agent_config(tmp_path / "agent.toml", runner.origin, mode="endpoint",
                             endpoint_url=endpoint.url, extra_endpoint="accept_images = true")
        runner.add_image(image["blob_id"], raw)
        runner.add_task(S.make_task("ext_EPI", images=[image]))
        proc = S.AgentProcess(cfg, "--max-tasks", "1")
        assert proc.wait() == 0, proc.stderr
        content = endpoint.requests[0]["body"]["messages"][-1]["content"]
        assert content[0]["type"] == "text"
        assert base64.b64decode(content[1]["image_url"]["url"].split(",", 1)[1]) == raw
        assert len(runner.of_kind("image")) == 1 and runner.of_kind("answer")


def test_endpoint_image_is_refused_without_opt_in(tmp_path):
    image = {"blob_id": "blob_01M2545JSD15ETSNNV904X991F",
             "portal_block_id": "blk_" + "a" * 32, "sha256": "a" * 64,
             "size_bytes": 8, "media_type": "image/png"}
    with S.FakeRunner() as runner, S.FakeOpenAI() as endpoint:
        cfg = S.agent_config(tmp_path / "agent.toml", runner.origin, mode="endpoint",
                             endpoint_url=endpoint.url)
        runner.add_task(S.make_task("ext_EPN", images=[image]))
        proc = S.AgentProcess(cfg, "--max-tasks", "1")
        assert proc.wait() == 0, proc.stderr
        assert runner.of_kind("fail")[0]["body"]["reason"] == "image_input_unsupported"
        assert runner.of_kind("image") == [] and endpoint.requests == []


def test_endpoint_failure_and_truncation_become_typed_failures_without_leaking_the_prompt(tmp_path):
    secret = "SENTINEL-DOCUMENT-TEXT-8841"
    with S.FakeRunner() as runner, S.FakeOpenAI(status=500) as endpoint:
        cfg = S.agent_config(tmp_path / "agent.toml", runner.origin, mode="endpoint", endpoint_url=endpoint.url)
        runner.add_task(S.make_task("ext_EP3", user_text=secret))
        proc = S.AgentProcess(cfg, "--max-tasks", "1")
        assert proc.wait() == 0
        reason = runner.of_kind("fail")[0]["body"]["reason"]
        assert reason == "endpoint_failed: HTTP 500"  # the endpoint's error body echoed the prompt; it is not forwarded
        assert secret not in proc.stderr and secret not in json.dumps(runner.requests[-1])
    with S.FakeRunner() as runner, S.FakeOpenAI(finish_reason="length") as endpoint:
        cfg = S.agent_config(tmp_path / "agent2.toml", runner.origin, mode="endpoint", endpoint_url=endpoint.url)
        runner.add_task(S.make_task("ext_EP4"))
        proc = S.AgentProcess(cfg, "--max-tasks", "1")
        assert proc.wait() == 0
        assert runner.of_kind("fail")[0]["body"]["reason"].startswith("output_truncated")
        assert runner.of_kind("answer") == []


def test_idle_agent_keeps_claiming_and_stops_cleanly_on_sigterm(tmp_path):
    with S.FakeRunner() as runner:
        cfg = S.agent_config(tmp_path / "agent.toml", runner.origin, argv=["/bin/true"])
        with S.AgentProcess(cfg) as proc:
            claims = runner.wait_for("claim", 3, timeout=10)  # 204 after each 1 s wait, then claim again
            assert all(c["body"] == {"wait_seconds": 1} for c in claims[:3])
            proc.terminate()
            assert proc.wait(timeout=10) == 0
            assert "stopped" in proc.stderr


def test_401_exits_with_a_clear_message_and_never_retries(tmp_path):
    with S.FakeRunner() as runner:
        runner.revoked = True
        cfg = S.agent_config(tmp_path / "agent.toml", runner.origin, argv=["/bin/true"])
        with S.AgentProcess(cfg) as proc:
            assert proc.wait(timeout=15) == 3
        assert "rejected the runner token" in proc.stderr and "revoked" in proc.stderr
        assert len(runner.of_kind("claim")) == 1


def test_lost_claim_on_extend_submits_nothing_and_the_agent_carries_on(tmp_path):
    with S.FakeRunner(lease=3) as runner:
        runner.override("extend", S.Reply(409, S.envelope("state_transition_not_allowed", "The claim is lost.")))
        long_task, fast = S.make_task("ext_LONG1", lease=3), S.make_task("ext_OK2", lease=3)
        started = time.monotonic()
        proc, code, records = _run(tmp_path, runner, [long_task, fast], max_tasks=2)
        assert code == 0, proc.stderr
        answers = runner.of_kind("answer")
        assert [r["task_id"] for r in answers] == ["ext_OK2"]
        assert runner.of_kind("fail") == []
        assert "claim lost" in proc.stderr
        # the abandoned 6 s command was stopped as soon as the claim was lost, not waited for
        assert answers[0]["t"] - started < 4.5
        with pytest.raises(ProcessLookupError):
            os.kill(int((records / "ext_LONG1.pid").read_text()), 0)


def test_the_claim_is_extended_while_the_command_works(tmp_path):
    with S.FakeRunner(lease=3) as runner:
        proc, code, _ = _run(tmp_path, runner, [S.make_task("ext_SLOW2", lease=3)])
        assert code == 0, proc.stderr
        extends = runner.of_kind("extend")
        assert len(extends) >= 2 and all(e["task_id"] == "ext_SLOW2" for e in extends)
        assert [r["task_id"] for r in runner.of_kind("answer")] == ["ext_SLOW2"]


def test_429_is_honoured_before_the_next_claim(tmp_path):
    with S.FakeRunner() as runner:
        runner.override("claim", S.Reply(429, S.envelope("rate_limited", "Slow down.", True), {"Retry-After": "1"}))
        proc, code, _ = _run(tmp_path, runner, [S.make_task("ext_OK3")])
        assert code == 0, proc.stderr
        first, second = runner.of_kind("claim")[:2]
        assert second["t"] - first["t"] >= 1.0
        assert "throttled" in proc.stderr and len(runner.of_kind("answer")) == 1


def test_5xx_on_claim_backs_off_and_recovers(tmp_path):
    with S.FakeRunner() as runner:
        runner.override("claim", S.Reply(503, S.envelope("dependency_unavailable", "Restarting.", True)), S.Reply(502, None))
        proc, code, _ = _run(tmp_path, runner, [S.make_task("ext_OK4")])
        assert code == 0, proc.stderr
        times = [c["t"] for c in runner.of_kind("claim")]
        assert len(times) >= 3 and times[1] - times[0] >= 0.2 and times[2] - times[1] >= 0.4  # 0.2 s then 0.4 s (+ jitter)
        assert len(runner.of_kind("answer")) == 1


def test_a_503_on_submit_is_retried_with_the_same_body(tmp_path):
    with S.FakeRunner() as runner:
        runner.override("answer", S.Reply(503, S.envelope("dependency_unavailable", "Restarting.", True)))
        proc, code, _ = _run(tmp_path, runner, [S.make_task("ext_OK5")])
        assert code == 0, proc.stderr
        answers = runner.of_kind("answer")
        assert len(answers) == 2 and answers[0]["body"] == answers[1]["body"]


def test_schema_refusal_422_fails_the_task_with_a_typed_reason_and_is_not_retried(tmp_path):
    with S.FakeRunner() as runner:
        runner.override("answer", S.Reply(422, S.envelope("validation_failed", "findings[0].id: 'id' must be a string.")))
        proc, code, _ = _run(tmp_path, runner, [S.make_task("ext_OK6")])
        assert code == 0, proc.stderr
        assert len(runner.of_kind("answer")) == 1  # no silent retry
        reason = runner.of_kind("fail")[0]["body"]["reason"]
        assert reason == "schema_invalid_answer: findings[0].id: 'id' must be a string."
        assert "HTTP 422 validation_failed" in proc.stderr  # surfaced in the agent's log too


def test_model_identity_refusal_is_reported_as_such(tmp_path):
    with S.FakeRunner() as runner:
        runner.override("answer", S.Reply(422, S.envelope("model_identity_mismatch", "The declared model is not the pinned one.")))
        proc, code, _ = _run(tmp_path, runner, [S.make_task("ext_OK7")])
        assert code == 0
        assert runner.of_kind("fail")[0]["body"]["reason"].startswith("model_identity_mismatch:")


def test_409_on_submit_drops_the_task_without_a_fail_call(tmp_path):
    with S.FakeRunner() as runner:
        runner.override("answer", S.Reply(409, S.envelope("conflict", "Another answer was accepted.")))
        proc, code, _ = _run(tmp_path, runner, [S.make_task("ext_OK8")])
        assert code == 0
        assert len(runner.of_kind("answer")) == 1 and runner.of_kind("fail") == []
        assert "no longer accepts" in proc.stderr


def test_a_task_pinning_another_model_is_failed_before_any_work(tmp_path):
    with S.FakeRunner() as runner:
        proc, code, records = _run(tmp_path, runner, [S.make_task("ext_OK9", model="claude-sonnet-5")], declared="claude-opus-5")
        assert code == 0
        assert runner.of_kind("fail")[0]["body"]["reason"].startswith("model_mismatch:")
        assert runner.of_kind("answer") == [] and not list(records.iterdir())  # the command never ran


def test_command_failures_become_typed_reasons(tmp_path):
    with S.FakeRunner() as runner:
        tasks = [S.make_task(tid) for tid in ("ext_EXIT1a", "ext_EMPTYa", "ext_NOTJSONa")]
        proc, code, _ = _run(tmp_path, runner, tasks, max_tasks=3)
        assert code == 0, proc.stderr
        reasons = {f["task_id"]: f["body"]["reason"] for f in runner.of_kind("fail")}
        assert reasons["ext_EXIT1a"] == "command_failed: exit status 1"
        assert reasons["ext_EMPTYa"].startswith("command_bad_output")
        assert reasons["ext_NOTJSONa"].startswith("answer_not_json")
        assert runner.of_kind("answer") == []


def test_a_command_over_its_time_budget_is_killed_and_the_task_failed(tmp_path):
    with S.FakeRunner() as runner:
        proc, code, records = _run(tmp_path, runner, [S.make_task("ext_VSLOW1")], command_timeout=1.0)
        assert code == 0, proc.stderr
        assert runner.of_kind("fail")[0]["body"]["reason"].startswith("timeout:")
        with pytest.raises(ProcessLookupError):
            os.kill(int((records / "ext_VSLOW1.pid").read_text()), 0)


def test_too_little_time_before_the_deadline_fails_the_task_without_starting_work(tmp_path):
    with S.FakeRunner() as runner:
        proc, code, records = _run(tmp_path, runner, [S.make_task("ext_OK10", window=3)])
        assert code == 0
        assert runner.of_kind("fail")[0]["body"]["reason"].startswith("deadline_exceeded:")
        assert not list(records.iterdir())


def test_two_tasks_run_at_once_with_concurrency_two(tmp_path):
    with S.FakeRunner() as runner:
        started = time.monotonic()
        proc, code, _ = _run(tmp_path, runner, [S.make_task("ext_PAR1"), S.make_task("ext_PAR2")], extra_runner="concurrency = 2")
        elapsed = time.monotonic() - started
        assert code == 0, proc.stderr
        assert sorted(r["task_id"] for r in runner.of_kind("answer")) == ["ext_PAR1", "ext_PAR2"]
        assert elapsed < 2.4  # two 1 s commands in parallel, not one after the other


def test_sigterm_mid_task_fails_it_as_agent_shutdown_after_the_drain_time(tmp_path):
    with S.FakeRunner() as runner:
        records = tmp_path / "records"
        records.mkdir()
        stub = S.write_stub(tmp_path / "stub.py", STUB)
        cfg = S.agent_config(tmp_path / "agent.toml", runner.origin, argv=[sys.executable, str(stub), str(records)], drain_seconds=1)
        runner.add_task(S.make_task("ext_VSLOW2"))
        with S.AgentProcess(cfg) as proc:
            runner.wait_for("claim", 1)
            while not (records / "ext_VSLOW2.pid").exists():
                time.sleep(0.05)
            proc.terminate()
            assert proc.wait(timeout=15) == 0
        assert runner.of_kind("fail")[0]["body"]["reason"].startswith("agent_shutdown:")
        with pytest.raises(ProcessLookupError):
            os.kill(int((records / "ext_VSLOW2.pid").read_text()), 0)


def test_a_killed_agent_stops_extending_so_the_claim_can_lapse(tmp_path):
    with S.FakeRunner(lease=3) as runner:
        records = tmp_path / "records"
        records.mkdir()
        stub = S.write_stub(tmp_path / "stub.py", STUB)
        cfg = S.agent_config(tmp_path / "agent.toml", runner.origin, argv=[sys.executable, str(stub), str(records)])
        runner.add_task(S.make_task("ext_VSLOW3", lease=3))
        with S.AgentProcess(cfg) as proc:
            runner.wait_for("extend", 1, timeout=10)
            proc.proc.kill()  # the agent's own handle; no answer, no fail, no goodbye
            proc.proc.wait()
            seen = len(runner.requests)
            time.sleep(1.5)
            assert len(runner.requests) == seen
        os.kill(int((records / "ext_VSLOW3.pid").read_text()), 9) if (records / "ext_VSLOW3.pid").exists() else None


def test_neither_the_token_nor_the_payload_is_ever_logged(tmp_path):
    token, secret = "amr_SENTINEL_tok_5521", "SENTINEL-PAYLOAD-9917"
    with S.FakeRunner(token=token) as runner:
        runner.override("answer", S.Reply(422, S.envelope("validation_failed", f"echo {token}")))
        records = tmp_path / "records"
        records.mkdir()
        stub = S.write_stub(tmp_path / "stub.py", STUB)
        cfg = S.agent_config(tmp_path / "agent.toml", runner.origin, argv=[sys.executable, str(stub), str(records)])
        runner.add_task(S.make_task("ext_OK11", system=secret, user_text=secret))
        proc = S.AgentProcess(cfg, "--max-tasks", "1", token=token)
        assert proc.wait() == 0
        assert token not in proc.stderr + proc.stdout and secret not in proc.stderr + proc.stdout
        assert token not in runner.of_kind("fail")[0]["body"]["reason"]


def test_config_guards(tmp_path):
    def attempt(text: str, token: str | None = S.TOKEN) -> tuple[int, str]:
        path = tmp_path / "bad.toml"
        path.write_text(text)
        with S.AgentProcess(path, token=token) as proc:
            return proc.wait(timeout=15), proc.stderr

    good = '[runner]\norigin = "https://stand.example.org"\n[model]\ndeclared = "claude-opus-5"\n[executor]\nmode = "command"\n[command]\nargv = ["/bin/true"]\n'
    code, err = attempt(good, token=None)
    assert code == 2 and "PDF_ANALYSIS_RUNNER_TOKEN is not set" in err
    code, err = attempt(good.replace("[model]", 'token = "amr_abc"\n[model]'))
    assert code == 2 and "secrets belong in environment variables" in err
    code, err = attempt(good + 'api_key = "x"\n')
    assert code == 2 and "api_key" in err
    code, err = attempt(good.replace('declared = "claude-opus-5"', 'declard = "claude-opus-5"'))
    assert code == 2 and "declard" in err
    code, err = attempt(good.replace('declared = "claude-opus-5"\n', ""))
    assert code == 2 and "declared is required" in err
    code, err = attempt(good.replace('argv = ["/bin/true"]', "argv = []"))
    assert code == 2 and "argv" in err
    code, err = attempt(good.replace("https://stand.example.org", "http://stand.example.org"))
    assert code == 2 and "refusing http://" in err
    code, err = attempt(good.replace('mode = "command"', 'mode = "ssh"'))
    assert code == 2 and "mode" in err
    code, err = attempt("not [toml")
    assert code == 2 and "cannot read config" in err


def test_the_shipped_example_config_loads_and_is_secret_free():
    agent = _agent_module()
    cfg = agent.load_config(str(S.RUNNER_DIR / "agent.example.toml"))
    assert cfg.origin.startswith("https://") and cfg.mode == "command" and cfg.declared_model == "claude-sonnet-5"
    assert cfg.token_env == "PDF_ANALYSIS_RUNNER_TOKEN"
    text = (S.RUNNER_DIR / "agent.example.toml").read_text()
    assert "amr_" not in text and 'token = "' not in text


def test_systemd_unit_keeps_the_token_off_the_command_line_and_stops_restart_loops():
    unit = (S.RUNNER_DIR / "pdf-analysis-agent.service").read_text()
    lines = [line.strip() for line in unit.splitlines() if line.strip() and not line.startswith("#")]
    assert "EnvironmentFile=/etc/pdf-analysis-agent/agent.env" in lines
    assert "RestartPreventExitStatus=2 3" in lines and "NoNewPrivileges=true" in lines
    exec_start = next(line for line in lines if line.startswith("ExecStart="))
    assert "TOKEN" not in exec_start.upper() and "--token" not in exec_start
    assert not any(line.startswith("Environment=") and "TOKEN" in line.upper() for line in lines)
    assert "0600" in unit  # the install steps create the env file with mode 0600
    if shutil.which("systemd-analyze"):
        result = subprocess.run(["systemd-analyze", "verify", str(S.RUNNER_DIR / "pdf-analysis-agent.service")], capture_output=True, text=True, timeout=30)
        problems = [line for line in result.stderr.splitlines() if "pdf-analysis-agent.service" in line and "not executable" not in line and "No such file" not in line and "User" not in line]
        assert not problems, result.stderr


# -- several images, `CMP-EXEC-IMAGES-01` --------------------------------------------------------

import hashlib as _hashlib  # noqa: E402

LIST_STUB = r'''
import hashlib, json, os, sys
record_dir = sys.argv[1]
task = json.load(sys.stdin)
seen = [{"crop_id": image.get("crop_id"), "portal_block_id": image.get("portal_block_id"),
         "sha256": hashlib.sha256(open(image["path"], "rb").read()).hexdigest(),
         "mode": oct(os.stat(image["path"]).st_mode & 0o777), "path": image["path"]}
        for image in task.get("local_images", [])]
open(os.path.join(record_dir, task["task_id"] + ".images.json"), "w").write(json.dumps(seen))
print(json.dumps({"findings": [{"id": len(seen)}]}))
'''


def _list_run(tmp_path, runner, tasks, *, accept_images=True, max_images=None, max_tasks=None):
    records = tmp_path / "records"
    records.mkdir(exist_ok=True)
    stub = S.write_stub(tmp_path / "list_stub.py", LIST_STUB)
    cfg = S.agent_config(tmp_path / "agent.toml", runner.origin, argv=[sys.executable, str(stub), str(records)],
                         accept_images=accept_images, max_images=max_images)
    for task in tasks:
        runner.add_task(task)
    proc = S.AgentProcess(cfg, "--max-tasks", str(max_tasks or len(tasks)))
    return proc, proc.wait(timeout=40.0), records


def test_an_agent_that_declared_three_images_fetches_all_of_them_in_order_and_cleans_up(tmp_path):
    made = [S.make_image(label) for label in ("left", "right", "detail")]
    with S.FakeRunner() as runner:
        for image, raw in made:
            runner.add_image(image["blob_id"], raw)
        proc, code, records = _list_run(
            tmp_path, runner, [S.make_task("ext_L3", images=[image for image, _ in made])], max_images=3)
        assert code == 0, proc.stderr
        assert runner.of_kind("claim")[0]["body"]["max_images"] == 3
        assert len(runner.of_kind("image")) == 3 and runner.of_kind("answer") and not runner.of_kind("fail")
        seen = json.loads((records / "ext_L3.images.json").read_text())
        assert [item["crop_id"] for item in seen] == ["crop-left", "crop-right", "crop-detail"]
        assert [item["sha256"] for item in seen] == [_hashlib.sha256(raw).hexdigest() for _, raw in made]
        assert {item["mode"] for item in seen} == {"0o600"}
        assert not any(Path(item["path"]).exists() for item in seen), "the files live only while the command runs"


def test_two_crops_with_the_same_bytes_are_fetched_once_and_both_reach_the_command(tmp_path):
    first, raw = S.make_image("blank")
    second = {**first, "crop_id": "crop-blank-b"}
    with S.FakeRunner() as runner:
        runner.add_image(first["blob_id"], raw)
        proc, code, records = _list_run(tmp_path, runner, [S.make_task("ext_LD", images=[first, second])],
                                        max_images=2)
        assert code == 0, proc.stderr
        assert len(runner.of_kind("image")) == 1
        seen = json.loads((records / "ext_LD.images.json").read_text())
        assert [item["crop_id"] for item in seen] == ["crop-blank", "crop-blank-b"]


def test_an_agent_that_declares_nothing_sends_the_old_claim_and_refuses_what_it_is_handed(tmp_path):
    made = [S.make_image(label) for label in ("a", "b")]
    with S.FakeRunner() as runner:
        proc, code, records = _list_run(tmp_path, runner, [S.make_task("ext_L2", images=[i for i, _ in made])],
                                        max_images=None)
        assert code == 0, proc.stderr
        assert runner.of_kind("claim")[0]["body"] == {"wait_seconds": 1}, "the wire every agent has always spoken"
        assert runner.of_kind("fail")[0]["body"]["reason"] == "image_input_unsupported"
        assert runner.of_kind("image") == [] and runner.of_kind("answer") == []
        assert not list(records.glob("*.images.json")), "the command never ran"


def test_a_task_wider_than_the_declaration_is_failed_whole_before_any_fetch(tmp_path):
    made = [S.make_image(label) for label in ("a", "b", "c")]
    with S.FakeRunner() as runner:
        for image, raw in made:
            runner.add_image(image["blob_id"], raw)
        proc, code, records = _list_run(tmp_path, runner, [S.make_task("ext_W3", images=[i for i, _ in made])],
                                        max_images=2)
        assert code == 0, proc.stderr
        assert runner.of_kind("claim")[0]["body"]["max_images"] == 2
        assert runner.of_kind("fail")[0]["body"]["reason"] == "image_input_unsupported"
        assert runner.of_kind("image") == [] and runner.of_kind("answer") == []
        assert not list(records.glob("*.images.json"))


def test_one_bad_image_among_several_fails_the_task_and_the_command_never_runs(tmp_path):
    made = [S.make_image(label) for label in ("a", "b", "c")]
    with S.FakeRunner() as runner:
        runner.add_image(made[0][0]["blob_id"], made[0][1])
        runner.add_image(made[1][0]["blob_id"], b"\x89PNG\r\n\x1a\nchanged-bytes")
        runner.add_image(made[2][0]["blob_id"], made[2][1])
        proc, code, records = _list_run(tmp_path, runner, [S.make_task("ext_BAD3", images=[i for i, _ in made])],
                                        max_images=3)
        assert code == 0, proc.stderr
        assert runner.of_kind("fail")[0]["body"]["reason"] == "image_delivery_failed"
        assert runner.of_kind("answer") == [] and not list(records.glob("*.images.json"))
        assert made[1][0]["sha256"] not in proc.stderr and S.TOKEN not in proc.stderr


def test_the_single_portal_block_image_path_is_what_it_was(tmp_path):
    image, raw = S.make_image("block", crop=False)
    with S.FakeRunner() as runner:
        runner.add_image(image["blob_id"], raw)
        proc, code, records = _list_run(tmp_path, runner, [S.make_task("ext_ONE", images=[image])])
        assert code == 0, proc.stderr
        assert runner.of_kind("claim")[0]["body"] == {"wait_seconds": 1}
        seen = json.loads((records / "ext_ONE.images.json").read_text())
        assert seen[0]["portal_block_id"] == image["portal_block_id"] and seen[0]["crop_id"] is None
        assert runner.of_kind("answer")


def test_the_endpoint_gets_every_image_in_order_after_the_text(tmp_path):
    made = [S.make_image(label) for label in ("a", "b", "c")]
    with S.FakeRunner() as runner, S.FakeOpenAI() as endpoint:
        cfg = S.agent_config(tmp_path / "agent.toml", runner.origin, mode="endpoint", endpoint_url=endpoint.url,
                             extra_endpoint="accept_images = true", max_images=3)
        for image, raw in made:
            runner.add_image(image["blob_id"], raw)
        runner.add_task(S.make_task("ext_EP3", images=[i for i, _ in made]))
        proc = S.AgentProcess(cfg, "--max-tasks", "1")
        assert proc.wait() == 0, proc.stderr
        content = endpoint.requests[0]["body"]["messages"][-1]["content"]
        assert content[0]["type"] == "text" and [block["type"] for block in content[1:]] == ["image_url"] * 3
        sent = [base64.b64decode(block["image_url"]["url"].split(",", 1)[1]) for block in content[1:]]
        assert sent == [raw for _, raw in made], "all of them, and not the last one alone"
        assert runner.of_kind("claim")[0]["body"]["max_images"] == 3 and runner.of_kind("answer")


def test_the_endpoint_refuses_rather_than_answer_from_part_of_the_images(tmp_path):
    made = [S.make_image(label) for label in ("a", "b")]
    with S.FakeRunner() as runner, S.FakeOpenAI() as endpoint:
        cfg = S.agent_config(tmp_path / "agent.toml", runner.origin, mode="endpoint", endpoint_url=endpoint.url,
                             extra_endpoint="accept_images = true")  # declares one
        runner.add_task(S.make_task("ext_EP2", images=[i for i, _ in made]))
        proc = S.AgentProcess(cfg, "--max-tasks", "1")
        assert proc.wait() == 0, proc.stderr
        assert runner.of_kind("fail")[0]["body"]["reason"] == "image_input_unsupported"
        assert runner.of_kind("image") == [] and endpoint.requests == [] and runner.of_kind("answer") == []


def test_max_images_config_is_checked(tmp_path):
    def attempt(text: str) -> tuple[int, str]:
        path = tmp_path / "bad.toml"
        path.write_text(text)
        with S.AgentProcess(path) as proc:
            return proc.wait(timeout=15), proc.stderr

    base = ('[runner]\norigin = "https://stand.example.org"\n[model]\ndeclared = "claude-opus-5"\n'
            '[executor]\nmode = "command"\n[command]\nargv = ["/bin/true"]\n')
    for bad in ("0", "9", "true", '"2"', "1.5"):
        code, err = attempt(base + f"accept_images = true\nmax_images = {bad}\n")
        assert code == 2 and "max_images must be an integer in 1..8" in err, (bad, err)
    code, err = attempt(base + "max_images = 3\n")
    assert code == 2 and "needs accept_images = true" in err
    endpoint = base.replace("command", "endpoint", 1).replace('argv = ["/bin/true"]', 'url = "http://127.0.0.1:1/v1"\nmodel = "m"')
    endpoint = endpoint.replace("[command]", "[endpoint]")
    code, err = attempt(endpoint + "max_images = 2\n")
    assert code == 2 and "[endpoint] max_images above 1 needs accept_images" in err


def test_the_declared_count_is_what_the_config_says_only_when_images_are_accepted():
    agent = _agent_module()
    cfg = agent.Config(origin="https://s.example.org", declared_model="m", command_argv=["x"],
                       command_accept_images=True, command_max_images=5)
    assert cfg.declared_max_images == 5
    cfg.command_accept_images = False
    assert cfg.declared_max_images == 1 and not cfg.accept_images
    endpoint = agent.Config(origin="https://s.example.org", declared_model="m", mode="endpoint",
                            endpoint_url="http://x/v1", endpoint_model="m", endpoint_accept_images=True,
                            endpoint_max_images=8)
    assert endpoint.declared_max_images == 8
