"""ssh-forced-command.sh: syntax, and behaviour against a stub `claude` on PATH."""

from __future__ import annotations

import importlib.util
import json
import os
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
print(os.environ.get("STUB_STDOUT", json.dumps({"type": "result", "result": "{\"findings\": []}", "modelUsage": {"claude-opus-5": {}}})))
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
    assert json.loads(result.stdout)["modelUsage"] == {"claude-opus-5": {}}  # the CLI's JSON passes through untouched
    record = json.loads(record_path.read_text())
    argv = record["argv"]
    assert argv[:11] == ["-p", "--bare", "--tools", "", "--disallowedTools", "mcp__*", "--output-format", "json", "--max-turns", "1", "--model"]
    assert argv[11] == "claude-opus-5" and argv[12] == "--system-prompt-file" and argv[14] == "--no-session-persistence" and len(argv) == 15
    assert record["stdin"] == f"Contract: {PAYLOAD}" and record["system_file"] == "You answer in JSON."
    assert record["system_file_mode"] == "0o600"
    assert record["api_key"] == API_KEY
    assert record["cwd_entries"] == ["model", "system.txt", "task.json", "user.txt"]  # a private directory, not the user's home or a repository
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
