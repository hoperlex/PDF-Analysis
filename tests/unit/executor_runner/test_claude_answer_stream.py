"""The subscription Claude command streams the CLI and judges a call by its signs of life.

``AR-V3-LIVENESS-01`` lane A: a fake ``claude`` writes newline-delimited JSON over time; the tests
check the heartbeat lines on stderr (frozen format, no task text), that a stream that keeps writing is
not cut by any short deadline, that a silent CLI is cut as ``claude_stalled``, that the hard cap cuts a
CLI that never stops, the optional ``effort`` and the result checks on the last ``result`` line.  No
model call, no network.  The periods are module constants, shrunk here so the suite stays fast.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import time
import types
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "tools/executor-runner/claude_answer.py"
SPEC = importlib.util.spec_from_file_location("pdfa_claude_answer_stream", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
claude_answer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = claude_answer
SPEC.loader.exec_module(claude_answer)

HEARTBEAT = re.compile(r"^pdf-analysis-forced-command: hb [0-9]+ [0-9]+ [0-9]+$")
TASK_SECRET = "SENTINEL-TASK-TEXT-7781"
MODEL_SECRET = "SENTINEL-MODEL-OUTPUT-4412"
MODEL = "claude-opus-5"
SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"],
          "additionalProperties": False, "description": TASK_SECRET}
TASK = {"model": MODEL, "system": f"Return JSON. {TASK_SECRET}", "user_text": f"A page. {TASK_SECRET}",
        "output_schema": SCHEMA}


def init() -> dict:
    return {"type": "system", "subtype": "init", "model": MODEL}


def delta(text: str = "") -> dict:
    return {"type": "stream_event", "event": {"type": "content_block_delta",
                                              "delta": {"type": "thinking_delta", "thinking": text}}}


def message_delta(tokens: int) -> dict:
    return {"type": "stream_event", "event": {"type": "message_delta", "delta": {},
                                              "usage": {"output_tokens": tokens}}}


def result(model: str = MODEL, **overrides: object) -> dict:
    report: dict = {
        "type": "result", "subtype": "success", "is_error": False, "terminal_reason": "completed",
        "permission_denials": [], "structured_output": {"ok": True}, "result": '{"ok":true}',
        "modelUsage": {model: {"inputTokens": 12, "outputTokens": 3, "cacheReadInputTokens": 5,
                               "cacheCreationInputTokens": 7}},
    }
    report.update(overrides)
    return report


class Fake:
    """A stand-in for ``claude -p --output-format stream-json`` driven by a list of steps."""

    def __init__(self, tmp_path: Path, steps: list[list], *, alarm: int = 12) -> None:
        self.args_path = tmp_path / "args.json"
        self.pid_path = tmp_path / "pid"
        self.path = tmp_path / "claude"
        self.path.write_text(
            f"#!{sys.executable}\n"
            "import json, os, signal, sys, time\n"
            f"signal.alarm({alarm})  # a fake never outlives its test\n"
            "args = sys.argv[1:]\n"
            f"json.dump(args, open({str(self.args_path)!r}, 'w'))\n"
            f"open({str(self.pid_path)!r}, 'w').write(str(os.getpid()))\n"
            "for flag in ('-p', '--verbose', '--include-partial-messages', '--no-session-persistence'):\n"
            " assert flag in args, flag\n"
            "assert args[args.index('--output-format') + 1] == 'stream-json'\n"
            "sys.stdin.read()\n"
            f"STEPS = json.loads({json.dumps(json.dumps(steps))})\n"
            "def emit(text):\n"
            " sys.stdout.write(text); sys.stdout.flush()\n"
            "for step in STEPS:\n"
            " kind = step[0]\n"
            " if kind == 'sleep':\n"
            "  time.sleep(step[1])\n"
            " elif kind == 'line':\n"
            "  emit(json.dumps(step[1]) + '\\n')\n"
            " elif kind == 'raw':\n"
            "  emit(step[1])\n"
            " elif kind == 'flood':\n"
            "  line = json.dumps({'type': 'stream_event', 'event': {'type': 'content_block_delta',\n"
            "                     'delta': {'type': 'thinking_delta', 'thinking': 'x' * step[2]}}}) + '\\n'\n"
            "  for _ in range(step[1]):\n"
            "   emit(line)\n"
            " elif kind == 'forever':\n"
            "  while True:\n"
            "   emit(json.dumps(step[2]) + '\\n'); time.sleep(step[1])\n"
            " elif kind == 'exit':\n"
            "  sys.exit(step[1])\n",
            encoding="utf-8",
        )
        self.path.chmod(0o700)

    def __str__(self) -> str:
        return str(self.path)

    @property
    def args(self) -> list[str]:
        return json.loads(self.args_path.read_text())

    def assert_dead(self) -> None:
        pid = int(self.pid_path.read_text())
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)


def ssh_task(**extra: object) -> dict:
    return claude_answer.read_task(json.dumps({**TASK, **extra}).encode(), ssh=True)


@pytest.fixture(autouse=True)
def fast_poll(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(claude_answer, "POLL_SECONDS", 0.02)


def test_the_periods_and_caps_are_the_frozen_ones() -> None:
    assert (claude_answer.HEARTBEAT_SECONDS, claude_answer.STALL_SECONDS,
            claude_answer.SSH_HARD_CAP_SECONDS) == (30, 600, 7140)
    assert claude_answer.TIMEOUT_SECONDS == 510  # the pull channel keeps its deadline
    assert claude_answer.MAX_STREAM_BYTES == 64 * 1024 * 1024
    assert claude_answer.MAX_OUTPUT_BYTES == 8 * 1024 * 1024
    assert not hasattr(claude_answer, "SSH_TIMEOUT_SECONDS")  # one 840 s deadline no longer exists
    assert claude_answer.HEARTBEAT_PREFIX == "pdf-analysis-forced-command: hb"
    assert claude_answer.EFFORTS == ("low", "medium", "high", "xhigh", "max")


def test_heartbeat_lines_have_the_frozen_format_and_carry_no_task_text(
        tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(claude_answer, "HEARTBEAT_SECONDS", 0.1)
    fake = Fake(tmp_path, [["line", init()], ["line", delta(MODEL_SECRET)], ["line", message_delta(7)],
                           ["sleep", 0.6], ["line", delta(MODEL_SECRET)], ["line", result()]])
    reply = json.loads(claude_answer.ssh_reply(ssh_task(), claude=str(fake)))
    assert reply["output_text"] == '{"ok":true}'
    captured = capsys.readouterr()
    lines = captured.err.splitlines()
    assert len(lines) >= 4 and all(HEARTBEAT.fullmatch(line) for line in lines), lines
    assert lines[0] == "pdf-analysis-forced-command: hb 0 0 0"  # one at the start, before any line
    numbers = [[int(part) for part in line.split()[-3:]] for line in lines]
    events = [n[1] for n in numbers]
    assert events == sorted(events) and events[-1] >= 3  # init, delta, message_delta were counted
    assert {n[2] for n in numbers} <= {0, 7} and numbers[-1][2] == 7  # latest message_delta tokens
    for secret in (TASK_SECRET, MODEL_SECRET):
        assert secret not in captured.err and secret not in captured.out


def test_the_heartbeat_repeats_no_faster_than_its_period(
        tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """The real 30 s period on a clock that runs 100 times faster: 0.9 s of CLI is 90 s."""
    started = time.monotonic()
    monkeypatch.setattr(claude_answer, "time",
                        types.SimpleNamespace(monotonic=lambda: (time.monotonic() - started) * 100))
    fake = Fake(tmp_path, [["line", init()], ["sleep", 0.9], ["line", result()]])
    claude_answer.ssh_reply(ssh_task(), claude=str(fake))
    elapsed = [int(line.split()[-3]) for line in capsys.readouterr().err.splitlines()]
    assert claude_answer.HEARTBEAT_SECONDS == 30
    assert elapsed[0] == 0 and len(elapsed) >= 3
    assert all(later - earlier >= 30 for earlier, later in zip(elapsed, elapsed[1:])), elapsed
    assert elapsed[-1] >= 60


def test_the_command_line_writes_heartbeats_in_ssh_mode_only(tmp_path: Path) -> None:
    fake = Fake(tmp_path, [["line", init()], ["line", message_delta(5)], ["line", result()]])

    def run(*flags: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), *flags, "--claude", str(fake)],
                              input=json.dumps(TASK), capture_output=True, text=True, timeout=60)

    ssh = run("--ssh-envelope")
    assert ssh.returncode == 0 and ssh.stdout.count("\n") == 1
    assert json.loads(ssh.stdout)["output_text"] == '{"ok":true}'
    lines = ssh.stderr.splitlines()
    assert lines and all(HEARTBEAT.fullmatch(line) for line in lines)
    assert lines[0] == "pdf-analysis-forced-command: hb 0 0 0"
    assert TASK_SECRET not in ssh.stderr

    pull = run()
    assert pull.returncode == 0 and pull.stdout == '{"ok":true}\n' and pull.stderr == ""


def test_a_cli_that_keeps_writing_is_never_cut_by_a_short_deadline(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The old command stopped a call at one wall-clock deadline.  Now the silence window is measured
    from the last byte: 3 s of streaming survive a 1 s window."""
    monkeypatch.setattr(claude_answer, "STALL_SECONDS", 1.0)
    monkeypatch.setattr(claude_answer, "SSH_HARD_CAP_SECONDS", 60)
    steps = [["line", init()]]
    for _ in range(30):
        steps += [["line", delta()], ["sleep", 0.1]]
    steps += [["line", result()]]
    started = time.monotonic()
    reply = json.loads(claude_answer.ssh_reply(ssh_task(), claude=str(Fake(tmp_path, steps))))
    assert time.monotonic() - started >= 2.5 > 2 * claude_answer.STALL_SECONDS  # it did outlive the window
    assert reply["output_text"] == '{"ok":true}'


@pytest.mark.parametrize("steps", [
    [["line", init()], ["sleep", 30]],  # a CLI that wrote, then went silent
    [["sleep", 30]],  # a CLI that never wrote a byte
], ids=["silent_after_init", "never_wrote"])
def test_a_silent_cli_is_cut_as_stalled_and_stopped(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, steps: list[list]) -> None:
    monkeypatch.setattr(claude_answer, "STALL_SECONDS", 0.4)
    monkeypatch.setattr(claude_answer, "SSH_HARD_CAP_SECONDS", 60)
    fake = Fake(tmp_path, steps)
    started = time.monotonic()
    with pytest.raises(claude_answer.TaskError, match="^claude_stalled$"):
        claude_answer.ssh_reply(ssh_task(), claude=str(fake))
    assert 0.35 <= time.monotonic() - started < 6
    fake.assert_dead()


def test_the_hard_cap_cuts_a_cli_that_streams_forever_and_stops_it(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(claude_answer, "STALL_SECONDS", 60)
    monkeypatch.setattr(claude_answer, "SSH_HARD_CAP_SECONDS", 0.6)
    fake = Fake(tmp_path, [["line", init()], ["forever", 0.05, delta()]])
    started = time.monotonic()
    with pytest.raises(claude_answer.TaskError, match="^claude_timeout$"):
        claude_answer.ssh_reply(ssh_task(), claude=str(fake))
    assert 0.55 <= time.monotonic() - started < 6
    fake.assert_dead()


def test_the_pull_channel_keeps_its_deadline_and_has_no_heartbeat_and_no_stall_window(
        tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    ok = Fake(tmp_path, [["line", init()], ["line", result()]])
    assert claude_answer.answer(TASK, claude=str(ok)) == '{"ok":true}'
    assert capsys.readouterr().err == ""

    monkeypatch.setattr(claude_answer, "TIMEOUT_SECONDS", 0.6)
    monkeypatch.setattr(claude_answer, "STALL_SECONDS", 0.1)  # would cut a silent CLI in SSH mode
    quiet = Fake(tmp_path, [["line", init()], ["sleep", 30]])
    started = time.monotonic()
    with pytest.raises(claude_answer.TaskError, match="^claude_timeout$"):
        claude_answer.answer(TASK, claude=str(quiet))
    assert time.monotonic() - started >= 0.55
    quiet.assert_dead()
    assert capsys.readouterr().err == ""


def test_a_hung_up_stand_stops_the_cli(
        tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """A heartbeat that cannot be written means the stand is gone: the CLI must not run on for hours."""
    class Closed(io.StringIO):
        def write(self, text: str) -> int:
            if not self.getvalue():  # the start heartbeat gets through, then the stand hangs up
                return super().write(text)
            raise BrokenPipeError

    class Stdin:
        buffer = io.BytesIO(json.dumps(TASK).encode())

    monkeypatch.setattr(sys, "stdin", Stdin)
    monkeypatch.setattr(sys, "stderr", Closed())
    monkeypatch.setattr(claude_answer, "HEARTBEAT_SECONDS", 0.5)
    fake = Fake(tmp_path, [["line", init()], ["sleep", 30]])
    started = time.monotonic()
    assert claude_answer.main(["--ssh-envelope", "--claude", str(fake)]) == 1
    assert time.monotonic() - started < 6  # stopped by the failed write, not by the fake's own alarm
    assert capsys.readouterr().out == ""
    fake.assert_dead()


def test_failures_print_a_fixed_word_after_the_heartbeat_lines(
        tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    class Stdin:
        buffer = io.BytesIO(json.dumps(TASK).encode())

    monkeypatch.setattr(sys, "stdin", Stdin)
    monkeypatch.setattr(claude_answer, "STALL_SECONDS", 0.3)
    fake = Fake(tmp_path, [["line", delta(MODEL_SECRET)], ["sleep", 30]])
    assert claude_answer.main(["--ssh-envelope", "--claude", str(fake)]) == 1
    captured = capsys.readouterr()
    *beats, last = captured.err.splitlines()
    assert last == "claude_answer: claude_stalled" and beats
    assert all(HEARTBEAT.fullmatch(line) for line in beats) and captured.out == ""
    assert TASK_SECRET not in captured.err and MODEL_SECRET not in captured.err


@pytest.mark.parametrize("effort", ["low", "medium", "high", "xhigh", "max"])
def test_effort_is_passed_to_the_cli_and_nothing_else_limits_it(tmp_path: Path, effort: str) -> None:
    fake = Fake(tmp_path, [["line", init()], ["line", result()]])
    task = ssh_task(effort=effort)
    claude_answer.ssh_reply(task, claude=str(fake))
    args = fake.args
    assert args[args.index("--effort") + 1] == effort and args.count("--effort") == 1
    for banned in ("--max-turns", "--max-budget-usd", "--max-thinking-tokens", "--thinking"):
        assert banned not in args
    claude_answer.answer({**TASK, "effort": effort}, claude=str(fake))  # the pull channel passes it too
    assert fake.args[fake.args.index("--effort") + 1] == effort


def test_without_an_effort_the_cli_gets_no_effort_flag(tmp_path: Path) -> None:
    fake = Fake(tmp_path, [["line", init()], ["line", result()]])
    claude_answer.ssh_reply(ssh_task(), claude=str(fake))
    assert "--effort" not in fake.args


@pytest.mark.parametrize("effort", ["", "HIGH", " high", "extreme", "none", "minimal", None, 5, True, ["high"]])
def test_an_unknown_effort_is_refused_before_any_cli_starts(tmp_path: Path, effort: object) -> None:
    fake = Fake(tmp_path, [["line", init()], ["line", result()]])
    with pytest.raises(claude_answer.TaskError, match="^invalid_effort$"):
        claude_answer.read_task(json.dumps({**TASK, "effort": effort}).encode(), ssh=True)
    for call in (lambda: claude_answer.answer({**TASK, "effort": effort}, claude=str(fake)),
                 lambda: claude_answer.ssh_reply({**TASK, "effort": effort}, claude=str(fake))):
        with pytest.raises(claude_answer.TaskError, match="^invalid_effort$"):
            call()
    assert not fake.args_path.exists()  # the CLI was never started


@pytest.mark.parametrize("override,reason", [
    ({"modelUsage": {"claude-sonnet-5": {}}}, "claude_model_mismatch"),
    ({"modelUsage": {MODEL: {}, "claude-haiku-5-5": {}}}, "claude_model_mismatch"),
    ({"modelUsage": None}, "claude_model_mismatch"),
    ({"permission_denials": [{"tool_name": "Bash"}]}, "claude_tool_denied"),
    ({"is_error": True, "subtype": "error_during_execution"}, "claude_turn_failed"),
    ({"is_error": True}, "claude_turn_failed"),
    ({"subtype": "error_max_turns"}, "claude_turn_failed"),
    ({"terminal_reason": "max_turns"}, "claude_turn_failed"),
    ({"structured_output": None}, "claude_answer_missing"),
    ({"structured_output": [1]}, "claude_answer_not_object"),
    ({"modelUsage": {MODEL: {"inputTokens": 1, "outputTokens": "many"}}}, "claude_usage_invalid"),
    ({"modelUsage": {MODEL: {"inputTokens": 1, "outputTokens": -1}}}, "claude_usage_invalid"),
])
def test_the_final_result_line_is_checked_exactly_as_before(
        tmp_path: Path, override: dict, reason: str) -> None:
    fake = Fake(tmp_path, [["line", init()], ["line", delta()], ["line", result(**override)]])
    with pytest.raises(claude_answer.TaskError, match=f"^{reason}$"):
        claude_answer.ssh_reply(ssh_task(), claude=str(fake))


def test_the_report_is_the_last_result_line_and_an_earlier_one_never_masks_it(tmp_path: Path) -> None:
    good, bad = result(), result(is_error=True, subtype="error_during_execution")
    task = ssh_task()
    refused = Fake(tmp_path, [["line", good], ["line", delta()], ["line", bad]])
    with pytest.raises(claude_answer.TaskError, match="^claude_turn_failed$"):
        claude_answer.ssh_reply(task, claude=str(refused))
    accepted = Fake(tmp_path, [["line", bad], ["line", delta()], ["line", good]])
    assert json.loads(claude_answer.ssh_reply(task, claude=str(accepted)))["output_text"] == '{"ok":true}'


@pytest.mark.parametrize("steps", [
    [["line", init()], ["line", delta()]],  # a stream that simply ends
    [["line", init()], ["raw", "not json at all\n"], ["raw", "[1, 2]\n"], ["raw", '"result"\n'], ["raw", "7\n"]],
    [["line", {"type": "assistant", "message": {"type": "result", "subtype": "success"}}]],
    [["line", init()], ["raw", json.dumps(result())[:-5]]],  # a result line cut in the middle
    [["line", init()], ["raw", json.dumps(result())[:-1] + "\n"]],  # a result line that is not valid JSON
], ids=["ends", "malformed_lines", "nested_type_result", "cut_result", "broken_result"])
def test_a_stream_without_a_result_line_is_a_typed_refusal(tmp_path: Path, steps: list[list]) -> None:
    for call in (lambda fake: claude_answer.ssh_reply(ssh_task(), claude=fake),
                 lambda fake: claude_answer.answer(TASK, claude=fake)):
        with pytest.raises(claude_answer.TaskError, match="^claude_no_result$"):
            call(str(Fake(tmp_path, steps)))


def test_a_result_line_without_a_final_newline_is_read(tmp_path: Path) -> None:
    fake = Fake(tmp_path, [["line", init()], ["raw", json.dumps(result())]])
    assert claude_answer.answer(TASK, claude=str(fake)) == '{"ok":true}'


def test_a_nonzero_exit_is_a_failure_even_when_a_result_was_streamed(tmp_path: Path) -> None:
    fake = Fake(tmp_path, [["line", init()], ["line", result()], ["exit", 3]])
    with pytest.raises(claude_answer.TaskError, match="^claude_failed$"):
        claude_answer.ssh_reply(ssh_task(), claude=str(fake))


def test_the_stream_file_and_the_result_have_their_own_caps(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    flood = [["line", init()], ["flood", 60, 900], ["sleep", 30]]
    monkeypatch.setattr(claude_answer, "MAX_STREAM_BYTES", 20_000)
    fake = Fake(tmp_path, flood)
    started = time.monotonic()
    with pytest.raises(claude_answer.TaskError, match="^claude_output_too_large$"):
        claude_answer.ssh_reply(ssh_task(), claude=str(fake))
    assert time.monotonic() - started < 6  # cut while the CLI was still running
    fake.assert_dead()
    monkeypatch.setattr(claude_answer, "MAX_STREAM_BYTES", 64 << 20)
    monkeypatch.setattr(claude_answer, "MAX_OUTPUT_BYTES", 2_000)
    big = Fake(tmp_path, [["line", init()], ["line", result(result="y" * 5_000)]])
    with pytest.raises(claude_answer.TaskError, match="^claude_output_too_large$"):
        claude_answer.ssh_reply(ssh_task(), claude=str(big))
    endless = Fake(tmp_path, [["line", init()], ["raw", "z" * 5_000], ["sleep", 30]])
    with pytest.raises(claude_answer.TaskError, match="^claude_output_too_large$"):
        claude_answer.ssh_reply(ssh_task(), claude=str(endless))
    endless.assert_dead()


def test_a_stream_far_larger_than_the_result_cap_is_accepted(tmp_path: Path) -> None:
    """Thinking deltas make the stream big; only the result line is held to the 8 MiB cap."""
    fake = Fake(tmp_path, [["line", init()], ["flood", 2600, 4000], ["line", result()]])
    assert claude_answer.answer(TASK, claude=str(fake)) == '{"ok":true}'
    assert fake.args  # it ran; the stream was 10 MB, above the 8 MiB result cap


def test_report_still_refuses_a_line_that_is_not_a_result() -> None:
    """The report check keeps its own refusals even though the stream reader never offers such a line."""
    with pytest.raises(claude_answer.TaskError, match="^invalid_claude_output$"):
        claude_answer._report(b"not json", MODEL)
    with pytest.raises(claude_answer.TaskError, match="^unknown_claude_output$"):
        claude_answer._report(json.dumps({"type": "system"}).encode(), MODEL)
