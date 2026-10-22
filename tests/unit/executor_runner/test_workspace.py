"""The dedicated workspace: its permission rules must leave only the bridge's MCP tools (plan T-7)."""

from __future__ import annotations

import fnmatch
import importlib.util
import json
import re
import sys
from pathlib import Path

_NAME = "executor_runner_support"
if _NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_NAME, Path(__file__).with_name("_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module
    _spec.loader.exec_module(_module)
S = sys.modules[_NAME]

WORKSPACE = S.RUNNER_DIR / "workspace"
SETTINGS = WORKSPACE / ".claude" / "settings.json"
SKILL = WORKSPACE / ".claude" / "skills" / "pdf-analysis-runner" / "SKILL.md"

# Every built-in tool in the Claude Code tools reference (code.claude.com/docs/en/tools-reference,
# read 2026-10-22) except the four deliberately left available, which are asserted separately.
BUILTINS_THAT_MUST_BE_DENIED = {
    "Agent", "Artifact", "AskUserQuestion", "Bash", "CronCreate", "CronDelete", "CronList", "Edit",
    "EnterPlanMode", "EnterWorktree", "ExitPlanMode", "ExitWorktree", "Glob", "Grep", "ListAgents",
    "ListMcpResourcesTool", "LSP", "Monitor", "NotebookEdit", "PowerShell", "PushNotification", "Read",
    "ReadMcpResourceTool", "RemoteTrigger", "ReportFindings", "ScheduleWakeup", "SendFeedback",
    "SendMessage", "SendUserFile", "ShareOnboardingGuide", "TaskCreate", "TaskGet", "TaskList",
    "TaskStop", "TaskUpdate", "TodoWrite", "WebFetch", "WebSearch", "Workflow", "Write",
}
DELIBERATELY_AVAILABLE = {"Skill", "ToolSearch", "WaitForMcpServers", "EndConversation"}


def _bridge_constant(name: str) -> str:
    source = (S.RUNNER_DIR / "mcp_bridge.py").read_text()
    return re.search(rf'^{name} = "([^"]+)"', source, re.M).group(1)


def _frontmatter(text: str) -> dict:
    lines = text.splitlines()
    assert lines[0] == "---"
    end = lines.index("---", 1)
    fields: dict = {}
    key = None
    for line in lines[1:end]:
        if line.startswith("  - ") and key:
            fields[key].append(line[4:].strip())
        elif ":" in line:
            key, _, value = line.partition(":")
            fields[key] = value.strip() if value.strip() else []
    return fields


def _settings() -> dict:
    return json.loads(SETTINGS.read_text())


def test_every_builtin_tool_is_denied_by_a_bare_rule():
    deny = _settings()["permissions"]["deny"]
    assert BUILTINS_THAT_MUST_BE_DENIED <= set(deny)
    # a scoped rule such as Bash(rm *) would leave the tool available; every built-in rule must be bare
    assert all("(" not in rule for rule in deny)


def test_no_deny_rule_removes_the_bridge_tools_and_the_allow_rule_names_them():
    server = _bridge_constant("SERVER_NAME")
    settings = _settings()["permissions"]
    bridge_tools = {f"mcp__{server}__{tool}" for tool in ("claim_task", "submit_answer", "report_failure")}
    for tool in bridge_tools:
        assert not [rule for rule in settings["deny"] if fnmatch.fnmatchcase(tool, rule)], tool
    assert settings["allow"] == [f"mcp__{server}__*"]
    assert DELIBERATELY_AVAILABLE.isdisjoint(settings["deny"])


def test_other_mcp_families_are_denied():
    deny = _settings()["permissions"]["deny"]
    assert "mcp__claude_ai_*" in deny and "mcp__plugin_*" in deny


def test_settings_set_nothing_that_could_run_code_or_widen_access():
    settings = _settings()
    assert set(settings) <= {"$schema", "permissions"}
    assert set(settings["permissions"]) == {"defaultMode", "allow", "deny"}
    assert settings["permissions"]["defaultMode"] == "dontAsk"


def test_the_workspace_holds_exactly_the_settings_and_the_skill():
    files = sorted(str(p.relative_to(WORKSPACE)) for p in WORKSPACE.rglob("*") if p.is_file())
    assert files == [".claude/settings.json", ".claude/skills/pdf-analysis-runner/SKILL.md"]


def test_skill_frontmatter_and_loop_match_the_bridge_and_the_pins():
    text = SKILL.read_text()
    meta = _frontmatter(text)
    server = _bridge_constant("SERVER_NAME")
    assert meta["name"] == "pdf-analysis-runner" == SKILL.parent.name == server
    assert meta["description"] and meta["disable-model-invocation"] == "true"
    assert meta["allowed-tools"] == [f"mcp__{server}__{tool}" for tool in ("claim_task", "submit_answer", "report_failure")]
    for needle in ("claude-opus-5", "claude-sonnet-5", "wait_seconds", "report_failure", "output_schema", "/model", "idle"):
        assert needle in text, needle
    lock = json.loads((S.REPO / "docs" / "program" / "P02_LOCK.json").read_text())
    pinned = set()

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("model_id"), str):
                pinned.add(node["model_id"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(lock)
    assert {"claude-opus-5", "claude-sonnet-5"} <= pinned


def test_skill_tool_names_are_the_bridges_tools_list():
    with S.FakeRunner() as runner, S.McpSession(runner.origin) as mcp:
        mcp.initialize()
        names = [tool["name"] for tool in mcp.request("tools/list")["result"]["tools"]]
    text = SKILL.read_text()
    for name in names:
        assert f"mcp__pdf-analysis-runner__{name}" in text
