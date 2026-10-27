"""ssh-forced-command.sh: syntax, and behaviour against a stub `claude` on PATH."""

from __future__ import annotations

import importlib.util
import json
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

_NAME = "executor_runner_support"
if _NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_NAME, Path(__file__).with_name("_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module
    _spec.loader.exec_module(_module)
S = sys.modules[_NAME]

SCRIPT = S.RUNNER_DIR / "ssh-forced-command.sh"
API_KEY = "sk-ant-api03-SENTINELKEY0042"
PAYLOAD = "SENTINEL-DOCUMENT-TEXT-3317"

STUB_CLAUDE = r'''#!/usr/bin/env python3
import json, os, sys
out = os.environ["STUB_OUT"]
system_path = sys.argv[sys.argv.index("--system-prompt-file") + 1]
record = {
    "argv": sys.argv[1:],
    "stdin": sys.stdin.read(),
    "system_file": open(system_path, encoding="utf-8").read(),
    "system_file_mode": oct(os.stat(system_path).st_mode & 0o777),
    "api_key": os.environ.get("ANTHROPIC_API_KEY"),
    "oauth": os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"),
    "auth_token": os.environ.get("ANTHROPIC_AUTH_TOKEN"),
    "ssh_original_command": os.environ.get("SSH_ORIGINAL_COMMAND"),
    "cwd_entries": sorted(os.listdir(".")) if os.path.isdir(".") else None,
}
open(out, "w").write(json.dumps(record))
sys.stderr.write(os.environ.get("STUB_STDERR", ""))
print(os.environ.get("STUB_STDOUT", json.dumps({
    "type": "result", "subtype": "success", "is_error": False, "result": "{\"findings\": []}",
    "total_cost_usd": 0.0123,
    "modelUsage": {"claude-opus-5": {"inputTokens": 11, "outputTokens": 7,
                                     "cacheReadInputTokens": 3, "cacheCreationInputTokens": 5}},
})))
sys.exit(int(os.environ.get("STUB_EXIT", "0")))
'''


def _setup(tmp_path: Path, *, env_text: str | None = None, env_mode: int = 0o600):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "claude"
    stub.write_text(STUB_CLAUDE)
    stub.chmod(0o755)
    home = tmp_path / "home"
    (home / ".config" / "pdf-analysis").mkdir(parents=True)
    env_file = home / ".config" / "pdf-analysis" / "claude.env"
    if env_text is None:
        env_text = f"# comment\nOTHER=1\nANTHROPIC_API_KEY={API_KEY}\n"
    env_file.write_text(env_text)
    env_file.chmod(env_mode)
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "HOME": str(home),
        "TMPDIR": str(tmp),
        "STUB_OUT": str(tmp_path / "record.json"),
    }
    return env, tmp_path / "record.json", tmp


def _task(**overrides) -> str:
    task = {"model": "claude-opus-5", "system": "You answer in JSON.", "user_text": f"Contract: {PAYLOAD}", "output_schema": {"type": "object"}}
    task.update(overrides)
    return json.dumps(task)


def _run(env: dict, stdin: str, extra_env: dict | None = None):
    return subprocess.run(["bash", str(SCRIPT)], input=stdin, capture_output=True, text=True, env={**env, **(extra_env or {})}, timeout=30)


def test_script_is_syntactically_valid_and_executable():
    result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert SCRIPT.stat().st_mode & stat.S_IXUSR


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck is not installed")
def test_script_is_shellcheck_clean():
    result = subprocess.run(["shellcheck", "-s", "bash", str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


def test_runs_claude_with_no_tools_the_task_prompt_and_the_key_from_the_file(tmp_path):
    env, record_path, tmp = _setup(tmp_path)
    result = _run(env, _task())
    assert result.returncode == 0, result.stderr
    # The script answers with the stand's envelope, built from the CLI's own report: the reported model,
    # the answer, and the token counts summed from `modelUsage` (11 + 3 + 5 in, 7 out) and the cost.
    assert json.loads(result.stdout) == {
        "model": "claude-opus-5", "output_text": '{"findings": []}', "stop_reason": "end_turn",
        "input_tokens": 19, "output_tokens": 7, "reported_cost_usd": 0.0123,
    }
    record = json.loads(record_path.read_text())
    argv = record["argv"]
    # The task carries an output schema, so the script passes it as `--json-schema` (after the output format).
    assert argv[:13] == ["-p", "--bare", "--tools", "", "--disallowedTools", "mcp__*", "--output-format", "json",
                         "--json-schema", '{"type":"object"}', "--max-turns", "1", "--model"]
    assert argv[13] == "claude-opus-5" and argv[14] == "--system-prompt-file" and argv[16] == "--no-session-persistence" and len(argv) == 17
    assert record["stdin"] == f"Contract: {PAYLOAD}" and record["system_file"] == "You answer in JSON."
    assert record["system_file_mode"] == "0o600"
    assert record["api_key"] == API_KEY
    # model, the schema the task carried, the prompt files, the task itself, and `result.json`, where the
    # script collects the CLI's stdout before it answers.
    assert record["cwd_entries"] == ["model", "result.json", "schema.json", "system.txt", "task.json", "user.txt"]  # a private directory, not the user's home or a repository
    assert list(tmp.iterdir()) == []  # the private working directory is removed on exit


def test_the_payload_and_the_key_never_reach_argv_or_the_scripts_own_output(tmp_path):
    env, record_path, _ = _setup(tmp_path)
    result = _run(env, _task(), {"STUB_STDOUT": "{}"})
    record = json.loads(record_path.read_text())
    assert PAYLOAD not in " ".join(record["argv"]) and API_KEY not in " ".join(record["argv"])
    assert API_KEY not in result.stdout + result.stderr


def test_ssh_original_command_is_ignored_and_unset(tmp_path):
    env, record_path, _ = _setup(tmp_path)
    marker = tmp_path / "pwned"
    result = _run(env, _task(), {"SSH_ORIGINAL_COMMAND": f"touch {marker}; claude --dangerously-skip-permissions"})
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    record = json.loads(record_path.read_text())
    assert record["ssh_original_command"] is None
    assert "--dangerously-skip-permissions" not in record["argv"]


def test_oauth_and_auth_token_variables_are_not_passed_on(tmp_path):
    env, record_path, _ = _setup(tmp_path)
    _run(env, _task(), {"CLAUDE_CODE_OAUTH_TOKEN": "oauth-xyz", "ANTHROPIC_AUTH_TOKEN": "auth-xyz"})
    record = json.loads(record_path.read_text())
    assert record["oauth"] is None and record["auth_token"] is None and record["api_key"] == API_KEY


@pytest.mark.parametrize("line", [f'ANTHROPIC_API_KEY="{API_KEY}"', f"ANTHROPIC_API_KEY='{API_KEY}'", f"ANTHROPIC_API_KEY={API_KEY}"])
def test_quoted_and_bare_key_lines_are_accepted(tmp_path, line):
    env, record_path, _ = _setup(tmp_path, env_text=line + "\n")
    assert _run(env, _task()).returncode == 0
    assert json.loads(record_path.read_text())["api_key"] == API_KEY


_USAGE = {"claude-opus-5": {"inputTokens": 1, "outputTokens": 1}}


def _report(**over) -> str:
    return json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "ok",
                       "modelUsage": _USAGE, **over})


@pytest.mark.parametrize("stdout", [
    "{}",
    "not json",
    _report(modelUsage={}),
    _report(modelUsage={"claude-opus-5": {"inputTokens": 1, "outputTokens": 1}, "claude-haiku-5": {"inputTokens": 1, "outputTokens": 1}}),
    _report(is_error=True),
    _report(subtype="error_max_turns"),
    _report(modelUsage={"claude-opus-5": {"inputTokens": 1, "outputTokens": "many"}}),
    _report(modelUsage={"claude-opus-5": {"inputTokens": 1}}),
    _report(total_cost_usd=-1),
    _report(structured_output=["not", "an", "object"]),
    _report(result=""),
])
def test_a_reply_that_does_not_name_exactly_one_model_with_whole_counts_is_refused(tmp_path, stdout):
    # `R-133`: the stand compares the model the CLI reports with the pinned one, so the script never
    # answers on a report that is incomplete, names two models, or says the turn failed.
    env, _, _ = _setup(tmp_path)
    result = _run(env, _task(), {"STUB_STDOUT": stdout})
    assert result.returncode == 65 and result.stdout == ""
    assert "incomplete answer" in result.stderr


def test_a_structured_answer_is_returned_as_the_envelopes_text(tmp_path):
    env, _, _ = _setup(tmp_path)
    result = _run(env, _task(), {"STUB_STDOUT": _report(structured_output={"findings": [1]}, result="ignored")})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["output_text"] == '{"findings":[1]}'


def test_claudes_exit_status_and_stderr_propagate(tmp_path):
    env, _, _ = _setup(tmp_path)
    result = _run(env, _task(), {"STUB_EXIT": "3", "STUB_STDERR": "boom\n"})
    assert result.returncode == 3 and "boom" in result.stderr


@pytest.mark.parametrize("mode", [0o640, 0o604, 0o644, 0o660])
def test_an_environment_file_open_to_group_or_others_is_refused(tmp_path, mode):
    env, record_path, _ = _setup(tmp_path, env_mode=mode)
    result = _run(env, _task())
    assert result.returncode == 78 and "must not be accessible by group or others" in result.stderr
    assert not record_path.exists() and API_KEY not in result.stderr


def test_missing_or_keyless_environment_file_is_refused(tmp_path):
    env, record_path, _ = _setup(tmp_path, env_text="OTHER=1\nANTHROPIC_API_KEY=\n")
    result = _run(env, _task())
    assert result.returncode == 78 and "no usable ANTHROPIC_API_KEY" in result.stderr and not record_path.exists()
    (tmp_path / "second").mkdir()
    env2, record2, _ = _setup(tmp_path / "second")
    result = _run(env2, _task(), {"PDF_ANALYSIS_CLAUDE_ENV_FILE": str(tmp_path / "nowhere.env")})
    assert result.returncode == 78 and "not found" in result.stderr and not record2.exists()


@pytest.mark.parametrize(
    "stdin",
    [
        "not json at all",
        "[]",
        json.dumps({"model": "claude-opus-5", "system": "s"}),  # user_text missing
        json.dumps({"model": "", "system": "s", "user_text": "u"}),
        json.dumps({"model": "claude-opus-5", "system": 5, "user_text": "u"}),
    ],
)
def test_malformed_tasks_are_refused_before_claude_runs(tmp_path, stdin):
    env, record_path, tmp = _setup(tmp_path)
    result = _run(env, stdin)
    assert result.returncode == 64 and not record_path.exists() and list(tmp.iterdir()) == []


@pytest.mark.parametrize("model", ["--dangerously-skip-permissions", "-x", "opus; touch /tmp/x", "claude opus", "$(id)", "a" * 101, "claude-opus-5\n--tools=Bash"])
def test_a_model_that_could_act_as_an_option_or_shell_syntax_is_refused(tmp_path, model):
    env, record_path, _ = _setup(tmp_path)
    result = _run(env, _task(model=model, user_text=PAYLOAD))
    assert result.returncode == 64 and not record_path.exists()
    assert PAYLOAD not in result.stderr  # a refusal names the field, never the content


def test_an_oversized_task_is_refused(tmp_path):
    env, record_path, _ = _setup(tmp_path)
    result = _run(env, _task(user_text="x" * 5000), {"PDF_ANALYSIS_MAX_TASK_BYTES": "1000"})
    assert result.returncode == 64 and "larger than 1000 bytes" in result.stderr and not record_path.exists()


def test_claude_missing_from_path_is_reported(tmp_path):
    env, _, _ = _setup(tmp_path)
    (tmp_path / "bin" / "claude").unlink()
    result = _run({**env, "HOME": env["HOME"]}, _task())
    assert result.returncode == 127 and "claude is not on PATH" in result.stderr


# -- several images, `CMP-EXEC-IMAGES-01` --------------------------------------------------------

import base64  # noqa: E402

FROZEN_ONE_IMAGE_SCRIPT = Path(__file__).with_name("frozen_ssh_forced_command_one_image.sh")


def _envelope(label: str, pad: int = 0) -> tuple[dict, bytes]:
    raw = b"\x89PNG\r\n\x1a\n" + label.encode() + b"." * pad
    return {"media_type": "image/png", "data": base64.b64encode(raw).decode()}, raw


def _fresh(tmp_path: Path, name: str):
    """A second, independent ``_setup`` under the same test directory."""
    (tmp_path / name).mkdir()
    return _setup(tmp_path / name)


def _blocks(record_path: Path) -> list[dict]:
    event = json.loads(json.loads(record_path.read_text())["stdin"])
    return event["message"]["content"]


def test_one_image_object_is_one_image_block_as_before(tmp_path):
    env, record_path, _ = _setup(tmp_path)
    envelope, raw = _envelope("only")
    result = _run(env, _task(image=envelope))
    assert result.returncode == 0, result.stderr
    content = _blocks(record_path)
    assert [block["type"] for block in content] == ["text", "image"]
    assert base64.b64decode(content[1]["source"]["data"]) == raw
    assert "--input-format" in json.loads(record_path.read_text())["argv"]


def test_a_list_of_images_is_one_block_each_in_the_order_given(tmp_path):
    env, record_path, _ = _setup(tmp_path)
    made = [_envelope(label) for label in ("left", "right", "detail")]
    result = _run(env, _task(image=[envelope for envelope, _ in made]))
    assert result.returncode == 0, result.stderr
    content = _blocks(record_path)
    assert [block["type"] for block in content] == ["text", "image", "image", "image"]
    assert content[0]["text"] == f"Contract: {PAYLOAD}"
    assert [base64.b64decode(block["source"]["data"]) for block in content[1:]] == [raw for _, raw in made]
    assert all(block["source"]["media_type"] == "image/png" for block in content[1:])


def test_a_list_of_one_is_one_image_and_eight_is_the_most(tmp_path):
    env, record_path, _ = _setup(tmp_path)
    assert _run(env, _task(image=[_envelope("one")[0]])).returncode == 0
    assert len(_blocks(record_path)) == 2
    env, record_path, _ = _fresh(tmp_path, "eight")
    assert _run(env, _task(image=[_envelope(str(i))[0] for i in range(8)])).returncode == 0
    assert len(_blocks(record_path)) == 9


@pytest.mark.parametrize("name,image", [
    ("nine", [_envelope(str(i))[0] for i in range(9)]),
    ("empty list", []),
    ("a member that is not an object", [_envelope("a")[0], "not-an-object"]),
    ("an extra member", [{**_envelope("a")[0], "name": "x"}]),
    ("a wrong media type", [{**_envelope("a")[0], "media_type": "image/jpeg"}]),
    ("bytes that are not base64", [{"media_type": "image/png", "data": "!!not base64!!"}]),
    ("one that is not a PNG", [_envelope("a")[0], {"media_type": "image/png", "data": base64.b64encode(b"GIF89a").decode()}]),
    ("a string", "iVBORw0KGgo="),
    ("a number", 3),
])
def test_a_list_outside_the_rules_is_refused_and_claude_never_runs(tmp_path, name, image):
    env, record_path, _ = _setup(tmp_path)
    result = _run(env, _task(image=image))
    assert result.returncode == 64 and not record_path.exists(), (name, result.stderr)
    assert PAYLOAD not in result.stderr and API_KEY not in result.stderr


def test_the_images_of_a_task_may_not_exceed_32_mib_together(tmp_path):
    env, record_path, _ = _setup(tmp_path)
    big = [_envelope(f"big{index}", pad=12 << 20)[0] for index in range(3)]  # 36 MiB of PNG, 48 MiB as base64
    result = _run(env, _task(image=big), {"PDF_ANALYSIS_MAX_TASK_BYTES": str(80 << 20)})
    assert result.returncode == 64 and "32 MiB together" in result.stderr and not record_path.exists()
    env, record_path, _ = _fresh(tmp_path, "ok")
    allowed = [_envelope(f"ok{index}", pad=12 << 20)[0] for index in range(2)]  # 24 MiB of PNG
    result = _run(env, _task(image=allowed), {"PDF_ANALYSIS_MAX_TASK_BYTES": str(80 << 20)})
    assert result.returncode == 0, result.stderr


def test_the_task_size_cap_now_covers_the_images_of_several_crops():
    text = SCRIPT.read_text()
    assert "PDF_ANALYSIS_MAX_TASK_BYTES:-50331648" in text, "48 MiB: 32 MiB of PNG is about 43 MiB as base64"


def _run_frozen(env: dict, stdin: str):
    return subprocess.run(["bash", str(FROZEN_ONE_IMAGE_SCRIPT)], input=stdin, capture_output=True,
                          text=True, env=env, timeout=30)


def test_a_command_installed_before_several_images_refuses_a_list_and_serves_one_image(tmp_path):
    """The task the stand sends for several crops cannot be served from the text alone, or from
    one crop of several, by a remote command that predates them: it checks the member for an
    object and refuses a list. The script under test is the one the repository had before."""
    env, record_path, _ = _setup(tmp_path)
    one = _run_frozen(env, _task(image=_envelope("one")[0]))
    assert one.returncode == 0, one.stderr
    assert len(_blocks(record_path)) == 2, "one image: the old command serves it, as ever"
    env, record_path, _ = _fresh(tmp_path, "list")
    several = _run_frozen(env, _task(image=[_envelope("a")[0], _envelope("b")[0]]))
    assert several.returncode == 64 and "invalid image envelope" in several.stderr
    assert not record_path.exists(), "claude never started"
    env, record_path, _ = _fresh(tmp_path, "plain")
    assert _run_frozen(env, _task(images=[_envelope("a")[0], _envelope("b")[0]])).returncode == 0, \
        "a list under a NEW member name would be ignored and answered from the text alone: it is never sent"
