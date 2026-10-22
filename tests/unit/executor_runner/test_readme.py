"""The README's setup command and the files it promises must agree with the code."""

from __future__ import annotations

import importlib.util
import re
import shlex
import sys
from pathlib import Path

_NAME = "executor_runner_support"
if _NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_NAME, Path(__file__).with_name("_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module
    _spec.loader.exec_module(_module)
S = sys.modules[_NAME]

README = (S.RUNNER_DIR / "README.md").read_text()


def _mcp_add_commands() -> list[list[str]]:
    flat = README.replace("\\\n", " ")
    commands = []
    for line in flat.splitlines():
        line = line.strip()
        if line.startswith("claude mcp add "):
            commands.append(shlex.split(line))
    return commands


def test_the_general_form_is_documented_verbatim():
    assert (
        "`claude mcp add --env PDF_ANALYSIS_RUNNER_TOKEN=… --transport stdio pdf-analysis-runner -- python3 <path>/mcp_bridge.py --origin <stand>`"
        in README
    )


def test_every_documented_add_command_puts_an_option_between_env_and_the_name_and_the_server_after_dashes():
    commands = _mcp_add_commands()
    assert commands, "no concrete claude mcp add command in the README"
    for argv in commands:
        env_at = argv.index("--env")
        assert argv[env_at + 1].startswith("PDF_ANALYSIS_RUNNER_TOKEN=")
        assert argv[env_at + 2].startswith("-"), "an option must sit between --env's pair and the server name"
        dashes = argv.index("--")
        name = argv[dashes - 1]
        assert name == "pdf-analysis-runner" and name not in argv[:dashes - 1]
        assert argv[dashes + 1] == "python3" and argv[dashes + 2].endswith("/mcp_bridge.py") and argv[dashes + 3] == "--origin"
        assert "--scope" in argv and argv[argv.index("--scope") + 1] == "local"
        assert "--transport" in argv and argv[argv.index("--transport") + 1] == "stdio"


def test_server_name_in_the_readme_is_the_bridges_and_the_workspaces():
    source = (S.RUNNER_DIR / "mcp_bridge.py").read_text()
    server = re.search(r'^SERVER_NAME = "([^"]+)"', source, re.M).group(1)
    assert server == "pdf-analysis-runner"
    assert f"mcp__{server}__*" in (S.RUNNER_DIR / "workspace" / ".claude" / "settings.json").read_text()


def test_the_readme_carries_the_warnings_and_checks_the_task_requires():
    for needle in (
        "stored in clear",
        "~/.claude.json",
        "does not write the project-trust flag",
        "trust dialog",
        "Bash",
        "Read",
        "must be unavailable or denied",
        "Revoke",
        "claude mcp remove",
        "outside any git repository",
        "--scope local",
    ):
        assert needle in README, needle


def test_every_file_of_the_directory_is_listed_and_every_listed_file_exists():
    pieces = set()
    for line in README.splitlines():
        if line.startswith("| `"):
            pieces.update(re.findall(r"`([^`]+)`", line.split("|")[1]))
    present = {p.name + ("/" if p.is_dir() else "") for p in S.RUNNER_DIR.iterdir() if p.name not in {"__pycache__", "README.md"}}
    assert present == pieces, (present ^ pieces)
