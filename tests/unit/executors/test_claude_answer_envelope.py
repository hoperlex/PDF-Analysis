"""The subscription forced command and the stand's SSH adapter agree on both ends of the wire.

The task is built by the stand's ``_task``, answered by ``claude_answer.py --ssh-envelope`` against
a fake CLI, and read back by the stand's ``_reply`` and identity check (no model call, no network).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from auditmanager.analysis.public import ModelRequest
from auditmanager.executors.identity import PROMPT, assess_identity
from auditmanager.executors.ssh_adapter import _reply, _task

SCRIPT = Path(__file__).resolve().parents[3] / "tools/executor-runner/claude_answer.py"
SPEC = importlib.util.spec_from_file_location("pdfa_claude_answer_wire", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
claude_answer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = claude_answer
SPEC.loader.exec_module(claude_answer)


def fake_claude(tmp_path: Path, *, structured: dict | None, text: str) -> str:
    path = tmp_path / "claude"
    report = {
        "type": "result", "subtype": "success", "is_error": False, "terminal_reason": "completed",
        "permission_denials": [], "result": text,
        "modelUsage": {"claude-opus-5": {"inputTokens": 9, "outputTokens": 4,
                                         "cacheReadInputTokens": 0, "cacheCreationInputTokens": 1}},
    }
    if structured is not None:
        report["structured_output"] = structured
    path.write_text(_stream_script(report), encoding="utf-8")
    path.chmod(0o700)
    return str(path)


def _stream_script(report: dict) -> str:
    """A fake ``claude -p`` that streams newline-delimited JSON ending with the ``result`` line."""
    return (
        f"#!{sys.executable}\nimport sys\n"
        "assert '--output-format' in sys.argv and sys.argv[sys.argv.index('--output-format') + 1] "
        "== 'stream-json'\n"
        "assert '--verbose' in sys.argv and '--include-partial-messages' in sys.argv\n"
        "sys.stdin.read()\n"
        "print('{\"type\":\"system\",\"subtype\":\"init\"}', flush=True)\n"
        "print('{\"type\":\"stream_event\",\"event\":{\"type\":\"message_delta\","
        "\"usage\":{\"output_tokens\":4}}}', flush=True)\n"
        f"print({json.dumps(report)!r})\n"
    )


def stand_task(*, schema: dict | None) -> bytes:
    body: dict = {"system": "Ответь кратко.", "messages": [{"role": "user", "content": PROMPT}],
                  "max_tokens": 16}
    if schema is not None:
        body["output_config"] = {"format": {"type": "json_schema", "schema": schema}}
    return _task(ModelRequest(model_id="claude-opus-5", body=body), "claude-opus-5")


def test_the_probe_task_is_answered_and_passes_the_stands_identity_check(tmp_path: Path) -> None:
    task = claude_answer.read_task(stand_task(schema=None), ssh=True)
    raw = claude_answer.ssh_reply(task, claude=fake_claude(tmp_path, structured=None, text="Привет."))
    answer = _reply(raw.encode(), 120)
    assert (answer.output_text, answer.model, answer.stop_reason) == ("Привет.", "claude-opus-5", "end_turn")
    assert (answer.input_tokens, answer.output_tokens, answer.reported_cost_usd) == (10, 4, None)
    assert assess_identity(answer.model, "claude-opus-5") == ("ok", "claude-opus-5")


def test_a_schema_task_returns_the_object_as_text_the_stage_can_parse(tmp_path: Path) -> None:
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
    task = claude_answer.read_task(stand_task(schema=schema), ssh=True)
    raw = claude_answer.ssh_reply(task, claude=fake_claude(tmp_path, structured={"ok": True}, text="{}"))
    assert json.loads(_reply(raw.encode(), 120).output_text) == {"ok": True}


@pytest.mark.parametrize("model", ["claude-opus-5-5", "claude-sonnet-5", ""])
def test_a_task_for_another_gateway_model_never_starts_the_cli(model: str) -> None:
    other = json.loads(stand_task(schema=None))
    other["model"] = model
    with pytest.raises(claude_answer.TaskError, match="^model_mismatch$"):
        claude_answer.read_task(json.dumps(other).encode(), ssh=True)


def test_the_sonnet_connection_wire_agrees_with_the_stand_end_to_end(tmp_path: Path) -> None:
    """A stand connection pinned to Sonnet: the stand's task, this command with ``--model``, the stand's
    reader and identity check."""
    def fake(model: str) -> str:
        path = tmp_path / "claude-sonnet"
        report = {
            "type": "result", "subtype": "success", "is_error": False, "terminal_reason": "completed",
            "permission_denials": [], "result": "да",
            "modelUsage": {model: {"inputTokens": 7, "outputTokens": 2,
                                   "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0}},
        }
        path.write_text(_stream_script(report), encoding="utf-8")
        path.chmod(0o700)
        return str(path)

    body = {"system": "Ответь кратко.", "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 16}
    task = claude_answer.read_task(
        _task(ModelRequest(model_id="claude-sonnet-5", body=body), "claude-sonnet-5"),
        ssh=True, model="claude-sonnet-5")
    raw = claude_answer.ssh_reply(task, claude=fake("claude-sonnet-5"), model="claude-sonnet-5")
    answer = _reply(raw.encode(), 100)
    assert (answer.model, answer.output_text, answer.reported_cost_usd) == ("claude-sonnet-5", "да", None)
    assert assess_identity(answer.model, "claude-sonnet-5") == ("ok", "claude-sonnet-5")
    # the same connection answered by the other model is not accepted
    with pytest.raises(claude_answer.TaskError, match="^claude_model_mismatch$"):
        claude_answer.ssh_reply(task, claude=fake("claude-opus-5"), model="claude-sonnet-5")
