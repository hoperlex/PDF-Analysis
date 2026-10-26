"""The subscription Claude command's fixed boundary, with a fake CLI (no model call)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[3] / "tools/executor-runner/claude_answer.py"
SPEC = importlib.util.spec_from_file_location("pdfa_claude_answer", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
claude_answer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = claude_answer
SPEC.loader.exec_module(claude_answer)


TASK = {
    "model": "claude-opus-5", "system": "Return JSON.", "user_text": "A page of data.",
    "output_schema": {"type": "object", "properties": {"ok": {"type": "boolean"}},
                      "required": ["ok"], "additionalProperties": False},
}


def fake_claude(tmp_path: Path, case: str = "ok", model: str = "claude-opus-5") -> str:
    """A stand-in for ``claude -p`` that asserts the fixed boundary and prints one result."""
    path = tmp_path / "claude"
    path.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "args = sys.argv[1:]\n"
        "for flag in ('-p', '--no-session-persistence', '--strict-mcp-config', "
        "'--disable-slash-commands'):\n"
        " assert flag in args, flag\n"
        f"MODEL = {model!r}\n"
        "OTHER = 'claude-sonnet-5' if MODEL == 'claude-opus-5' else 'claude-opus-5'\n"
        "assert args[args.index('--model') + 1] == MODEL\n"
        "assert args[args.index('--output-format') + 1] == 'json'\n"
        "assert args[args.index('--tools') + 1] == ''\n"
        "assert args[args.index('--setting-sources') + 1] == ''\n"
        "if '--json-schema' in args:\n"
        " assert json.loads(args[args.index('--json-schema') + 1])['required'] == ['ok']\n"
        f"json.dump(args, open({str(tmp_path / 'args.json')!r}, 'w'))\n"
        "assert 'bare' not in ' '.join(args)\n"
        "assert os.getenv('ANTHROPIC_API_KEY') is None\n"
        "assert os.getenv('ANTHROPIC_AUTH_TOKEN') is None\n"
        "assert os.getenv('CLAUDE_CODE_OAUTH_TOKEN') is None\n"
        "assert os.getenv('PDF_ANALYSIS_RUNNER_TOKEN') is None\n"
        "assert os.getenv('CLAUDECODE') is None\n"
        "assert os.getenv('CLAUDE_CODE_DISABLE_CLAUDE_MDS') == '1'\n"
        "assert os.getenv('CLAUDE_CODE_DISABLE_AUTO_MEMORY') == '1'\n"
        "assert os.getcwd() != os.environ.get('HOME')\n"
        "prompt = sys.stdin.read()\n"
        "doc = json.loads(prompt)\n"
        "assert doc['system'] and doc['user_text'] == 'A page of data.'\n"
        "assert doc['system'] not in ' '.join(args) and doc['user_text'] not in ' '.join(args)\n"
        f"case = {case!r}\n"
        "report = {'type': 'result', 'subtype': 'success', 'is_error': False,\n"
        "          'terminal_reason': 'completed', 'permission_denials': [],\n"
        "          'structured_output': {'ok': True}, 'result': '{\"ok\":true}',\n"
        "          'modelUsage': {MODEL: {'inputTokens': 12, 'outputTokens': 3,\n"
        "                                           'cacheReadInputTokens': 5,\n"
        "                                           'cacheCreationInputTokens': 7}},\n"
        "          'total_cost_usd': 0.0153}\n"
        "if case == 'other_model':\n"
        " report['modelUsage'] = {OTHER: {}}\n"
        "if case == 'extra_model':\n"
        " report['modelUsage']['claude-haiku-5-5'] = {}\n"
        "if case == 'no_usage':\n"
        " del report['modelUsage']\n"
        "if case == 'error':\n"
        " report.update(subtype='error_during_execution', is_error=True)\n"
        "if case == 'plain':\n"
        " del report['structured_output']; report['result'] = 'Всё в порядке.'\n"
        "if case == 'plain_empty':\n"
        " del report['structured_output']; report['result'] = '  '\n"
        "if case == 'bad_usage':\n"
        " report['modelUsage'][MODEL]['outputTokens'] = 'many'\n"
        "if case == 'flag_only':\n"
        " report['is_error'] = True\n"
        "if case == 'denied':\n"
        " report['permission_denials'] = [{'tool_name': 'Bash'}]\n"
        "if case == 'not_completed':\n"
        " report['terminal_reason'] = 'max_turns'\n"
        "if case == 'no_answer':\n"
        " del report['structured_output']\n"
        "if case == 'not_object':\n"
        " report['structured_output'] = [1]\n"
        "if case == 'wrong_type':\n"
        " report['type'] = 'system'\n"
        "if case == 'garbage':\n"
        " print('not json'); sys.exit(0)\n"
        "if case == 'exit_nonzero':\n"
        " sys.exit(3)\n"
        "print(json.dumps(report))\n",
        encoding="utf-8",
    )
    path.chmod(0o700)
    return str(path)


def test_pinned_subscription_task_returns_only_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN",
                 "PDF_ANALYSIS_RUNNER_TOKEN", "CLAUDECODE"):
        monkeypatch.setenv(name, "must-not-reach-claude")
    task = claude_answer.read_task(json.dumps(TASK).encode())
    assert claude_answer.answer(task, claude=fake_claude(tmp_path)) == '{"ok":true}'


def test_the_stored_login_location_reaches_the_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "runner-profile"))
    environment = claude_answer._environment()
    assert environment["CLAUDE_CONFIG_DIR"] == str(tmp_path / "runner-profile")
    assert not {"ANTHROPIC_API_KEY", "CLAUDECODE", "PDF_ANALYSIS_RUNNER_TOKEN"} & set(environment)


@pytest.mark.parametrize("case,reason", [
    ("other_model", "claude_model_mismatch"),
    ("extra_model", "claude_model_mismatch"),
    ("no_usage", "claude_model_mismatch"),
    ("error", "claude_turn_failed"),
    ("flag_only", "claude_turn_failed"),
    ("not_completed", "claude_turn_failed"),
    ("denied", "claude_tool_denied"),
    ("no_answer", "claude_answer_missing"),
    ("not_object", "claude_answer_not_object"),
    ("wrong_type", "unknown_claude_output"),
    ("garbage", "invalid_claude_output"),
    ("exit_nonzero", "claude_failed"),
])
def test_unusable_claude_turn_fails_closed(tmp_path: Path, case: str, reason: str) -> None:
    with pytest.raises(claude_answer.TaskError, match=f"^{reason}$"):
        claude_answer.answer(TASK, claude=fake_claude(tmp_path, case))


def test_a_missing_cli_is_a_typed_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "/nonexistent")
    with pytest.raises(claude_answer.TaskError, match="^claude_cli_missing$"):
        claude_answer.answer(TASK)


def test_wrong_model_and_malformed_tasks_never_start_claude() -> None:
    def refused(task: object, reason: str) -> None:
        with pytest.raises(claude_answer.TaskError, match=f"^{reason}$"):
            claude_answer.read_task(json.dumps(task).encode())

    refused({**TASK, "model": "gpt-6-sol"}, "model_mismatch")
    refused({**TASK, "model": "claude-sonnet-5"}, "model_mismatch")
    refused({**TASK, "output_schema": None}, "missing_object_schema")
    refused({**TASK, "output_schema": {"type": "array"}}, "missing_object_schema")
    refused({**TASK, "system": " "}, "missing_prompt")
    refused({**TASK, "user_text": None}, "missing_prompt")
    refused([TASK], "invalid_task_shape")
    refused({**TASK, "output_schema": {"type": "object", "description": "x" * 200_000}},
            "schema_too_large")
    with pytest.raises(claude_answer.TaskError, match="^invalid_task_json$"):
        claude_answer.read_task(b"{")
    with pytest.raises(claude_answer.TaskError, match="^task_too_large$"):
        claude_answer.read_task(b"x" * (claude_answer.MAX_TASK_BYTES + 1))


def test_an_image_task_is_refused_because_the_cli_has_no_tool_to_open_it() -> None:
    image = {"blob_id": "b", "portal_block_id": "blk_" + "a" * 32, "sha256": "0" * 64,
             "size_bytes": 1, "media_type": "image/png"}
    for extra in ({"images": [image]}, {"local_images": [{**image, "path": "/x.png"}]}):
        with pytest.raises(claude_answer.TaskError, match="^image_input_unsupported$"):
            claude_answer.read_task(json.dumps({**TASK, **extra}).encode())
    assert claude_answer.read_task(json.dumps({**TASK, "images": [], "local_images": []}).encode())


def test_the_command_line_prints_the_answer_and_never_the_task(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                                              monkeypatch: pytest.MonkeyPatch) -> None:
    class Stdin:
        buffer = __import__("io").BytesIO(json.dumps(TASK).encode())

    monkeypatch.setattr(sys, "stdin", Stdin)
    assert claude_answer.main(["--claude", fake_claude(tmp_path)]) == 0
    assert capsys.readouterr().out == '{"ok":true}\n'

    Stdin.buffer = __import__("io").BytesIO(json.dumps({**TASK, "model": "other"}).encode())
    assert claude_answer.main(["--claude", fake_claude(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "claude_answer: model_mismatch\n"
    assert "A page of data." not in captured.err

    assert claude_answer.main(["--unknown"]) == 2
    assert claude_answer.main(["--claude"]) == 2


def test_the_fixed_boundary_is_in_the_source() -> None:
    source = SCRIPT.read_text()
    assert '"--bare"' not in source  # --bare would read only an API key and never the login
    assert 'ALLOWED_MODELS = ("claude-opus-5", "claude-sonnet-5")' in source
    assert "DEFAULT_MODEL = ALLOWED_MODELS[0]" in source
    assert os.access(SCRIPT, os.R_OK)


SSH_TASK = {"model": "claude-opus-5", "system": "Answer briefly.", "user_text": "A page of data.",
            "max_tokens": 16}


def test_ssh_envelope_with_a_schema_carries_the_structured_answer_and_no_cost(tmp_path: Path) -> None:
    task = claude_answer.read_task(json.dumps(TASK).encode(), ssh=True)
    envelope = json.loads(claude_answer.ssh_reply(task, claude=fake_claude(tmp_path)))
    assert envelope == {
        "model": "claude-opus-5", "output_text": '{"ok":true}', "stop_reason": "end_turn",
        "input_tokens": 24, "output_tokens": 3, "reported_cost_usd": None,
    }


def test_ssh_envelope_without_a_schema_is_the_probe_shape_and_sends_no_schema_flag(tmp_path: Path) -> None:
    task = claude_answer.read_task(json.dumps(SSH_TASK).encode(), ssh=True)
    envelope = json.loads(claude_answer.ssh_reply(task, claude=fake_claude(tmp_path, "plain")))
    assert envelope["output_text"] == "Всё в порядке." and envelope["reported_cost_usd"] is None
    args = json.loads((tmp_path / "args.json").read_text())
    assert "--json-schema" not in args
    assert args[args.index("--system-prompt") + 1] == claude_answer.PLAIN_SYSTEM_PROMPT
    assert "JSON object" not in claude_answer.PLAIN_SYSTEM_PROMPT


@pytest.mark.parametrize("case,reason", [
    ("plain_empty", "claude_answer_missing"),
    ("bad_usage", "claude_usage_invalid"),
    ("other_model", "claude_model_mismatch"),
    ("denied", "claude_tool_denied"),
])
def test_ssh_envelope_fails_closed(tmp_path: Path, case: str, reason: str) -> None:
    task = claude_answer.read_task(json.dumps(SSH_TASK).encode(), ssh=True)
    with pytest.raises(claude_answer.TaskError, match=f"^{reason}$"):
        claude_answer.ssh_reply(task, claude=fake_claude(tmp_path, case))


def test_ssh_mode_refuses_the_stands_image_envelope_and_the_pull_mode_still_needs_a_schema() -> None:
    image = {"media_type": "image/png", "data": "iVBORw0KGgo="}
    with pytest.raises(claude_answer.TaskError, match="^image_input_unsupported$"):
        claude_answer.read_task(json.dumps({**SSH_TASK, "image": image}).encode(), ssh=True)
    with pytest.raises(claude_answer.TaskError, match="^missing_object_schema$"):
        claude_answer.read_task(json.dumps(SSH_TASK).encode())
    with pytest.raises(claude_answer.TaskError, match="^missing_object_schema$"):
        claude_answer.read_task(json.dumps({**SSH_TASK, "output_schema": []}).encode(), ssh=True)


def test_ssh_mode_takes_the_stands_larger_task_and_pull_mode_does_not() -> None:
    big = {**SSH_TASK, "user_text": "x" * (2 * claude_answer.MAX_TASK_BYTES)}
    assert claude_answer.read_task(json.dumps(big).encode(), ssh=True)["user_text"]
    with pytest.raises(claude_answer.TaskError, match="^task_too_large$"):
        claude_answer.read_task(json.dumps(big).encode())


def test_the_ssh_command_line_prints_one_json_line(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    class Stdin:
        buffer = __import__("io").BytesIO(json.dumps(SSH_TASK).encode())

    monkeypatch.setattr(sys, "stdin", Stdin)
    assert claude_answer.main(["--ssh-envelope", "--claude", fake_claude(tmp_path, "plain")]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 1 and json.loads(out)["model"] == "claude-opus-5"
    for bad in (["--ssh-envelope", "--ssh-envelope"], ["--claude", "a", "--claude", "b"], ["--x"]):
        assert claude_answer.main(bad) == 2


SONNET = "claude-sonnet-5"
SONNET_TASK = {**TASK, "model": SONNET}
SONNET_SSH_TASK = {**SSH_TASK, "model": SONNET}


def test_sonnet_is_served_when_it_is_asked_for_by_name(tmp_path: Path) -> None:
    task = claude_answer.read_task(json.dumps(SONNET_TASK).encode(), model=SONNET)
    cli = fake_claude(tmp_path, model=SONNET)
    assert claude_answer.answer(task, claude=cli, model=SONNET) == '{"ok":true}'
    ssh_task = claude_answer.read_task(json.dumps(SONNET_SSH_TASK).encode(), ssh=True, model=SONNET)
    envelope = json.loads(claude_answer.ssh_reply(ssh_task, claude=cli, model=SONNET))
    assert envelope["model"] == SONNET and envelope["reported_cost_usd"] is None


def test_the_model_is_never_inferred_from_the_task(tmp_path: Path) -> None:
    # A Sonnet task to a command that serves Opus (the default), and an Opus task to a command that
    # serves Sonnet, are refused before any CLI starts.
    with pytest.raises(claude_answer.TaskError, match="^model_mismatch$"):
        claude_answer.read_task(json.dumps(SONNET_TASK).encode())
    with pytest.raises(claude_answer.TaskError, match="^model_mismatch$"):
        claude_answer.read_task(json.dumps(TASK).encode(), model=SONNET)


@pytest.mark.parametrize("served,reported", [("claude-opus-5", SONNET), (SONNET, "claude-opus-5")])
def test_a_cli_that_reports_the_other_model_is_refused(tmp_path: Path, served: str, reported: str) -> None:
    task = {**TASK, "model": served}
    with pytest.raises(claude_answer.TaskError, match="^claude_model_mismatch$"):
        claude_answer.answer(task, claude=fake_claude(tmp_path, "other_model", model=served), model=served)


def test_the_cli_is_started_with_the_model_that_was_asked_for(tmp_path: Path) -> None:
    claude_answer.answer(SONNET_TASK, claude=fake_claude(tmp_path, model=SONNET), model=SONNET)
    args = json.loads((tmp_path / "args.json").read_text())
    assert args[args.index("--model") + 1] == SONNET


def test_the_command_line_takes_the_model_once_from_the_two_pins_and_defaults_to_opus(
        tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    class Stdin:
        buffer = io.BytesIO(json.dumps(SONNET_SSH_TASK).encode())

    monkeypatch.setattr(sys, "stdin", Stdin)
    assert claude_answer.main(["--ssh-envelope", "--model", SONNET, "--claude",
                               fake_claude(tmp_path, "plain", model=SONNET)]) == 0
    assert json.loads(capsys.readouterr().out)["model"] == SONNET

    # no --model: Opus, so a Sonnet task is refused by name and nothing else is said
    Stdin.buffer = io.BytesIO(json.dumps(SONNET_SSH_TASK).encode())
    assert claude_answer.main(["--ssh-envelope", "--claude", fake_claude(tmp_path, "plain")]) == 1
    assert capsys.readouterr().err == "claude_answer: model_mismatch\n"

    for bad in (["--model"], ["--model", "claude-haiku-5"], ["--model", "gpt-6-sol"],
                ["--model", SONNET, "--model", SONNET], ["--model", "claude-opus-5", "--model", SONNET]):
        assert claude_answer.main(bad) == 2
    assert "claude-opus-5|claude-sonnet-5" in capsys.readouterr().err
