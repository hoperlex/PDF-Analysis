"""`LOCAL-AGENT-01`: ``infra/deploy/local_agent_clis.py`` finds the deploy server's ``claude`` and ``codex`` and writes the wrappers.

Everything happens in a temporary home and a temporary output directory; the "system" directories are temporary too.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

HELPER = Path(__file__).resolve().parents[3] / "infra" / "deploy" / "local_agent_clis.py"
_spec = importlib.util.spec_from_file_location("local_agent_clis_under_test", HELPER)
clis = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = clis
_spec.loader.exec_module(clis)

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX paths and modes")


def _binary(path: Path, text: str = "#!/bin/sh\necho real\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)
    return path


def _claude_ext(home: Path, version: str) -> Path:
    return _binary(home / f".vscode-server/extensions/anthropic.claude-code-{version}-linux-x64/resources/native-binary/claude",
                   f"#!/bin/sh\necho claude {version} \"$@\"\n")


def _codex_ext(home: Path, version: str) -> Path:
    return _binary(home / f".vscode-server/extensions/openai.chatgpt-{version}-linux-x64/bin/linux-x86_64/codex",
                   f"#!/bin/sh\necho codex {version} \"$@\"\n")


def test_the_newest_extension_binary_is_found_by_version_not_by_name_order(tmp_path):
    home = tmp_path / "home"
    _claude_ext(home, "2.1.99")
    newest = _claude_ext(home, "2.1.328")
    _claude_ext(home, "2.1.310")
    found = clis.find("claude", str(home), [])
    assert found.kind == "extension" and found.path == str(newest)


def test_an_extension_binary_wins_over_one_in_the_usual_directories(tmp_path):
    home = tmp_path / "home"
    _binary(home / ".local/bin/codex")
    ext = _codex_ext(home, "26.1111.21308")
    assert clis.find("codex", str(home), []).path == str(ext)


def test_without_an_extension_the_usual_directories_are_searched_in_detect_order(tmp_path):
    home = tmp_path / "home"
    system = tmp_path / "usr-local-bin"
    _binary(system / "claude")
    assert clis.find("claude", str(home), [str(system)]) == clis.Found("claude", "usual", str(system / "claude"))
    own = _binary(home / ".local/bin/claude")
    assert clis.find("claude", str(home), [str(system)]).path == str(own), "the account's own directory comes first"
    assert clis.find("codex", str(home), [str(system)]).kind == "missing"


def test_a_file_that_is_not_executable_is_not_a_client(tmp_path):
    home = tmp_path / "home"
    _claude_ext(home, "2.1.328").chmod(0o644)
    assert clis.find("claude", str(home), []).kind == "missing"


def test_the_wrapper_runs_the_newest_binary_at_call_time_so_an_update_needs_nothing(tmp_path):
    home, out = tmp_path / "home", tmp_path / "bin"
    _claude_ext(home, "2.1.310")
    changes = clis.apply(out, [clis.find("claude", str(home), [])])
    assert changes == [f"wrote {out / 'claude'}"]
    wrapper = out / "claude"
    assert os.access(wrapper, os.X_OK) and clis.MARKER in wrapper.read_text()
    assert subprocess.run([str(wrapper), "-p"], capture_output=True, text=True).stdout == "claude 2.1.310 -p\n"
    _claude_ext(home, "2.1.400")  # the extension updates itself
    assert subprocess.run([str(wrapper)], capture_output=True, text=True).stdout == "claude 2.1.400\n"
    assert clis.apply(out, [clis.find("claude", str(home), [])]) == [], "a second run changes nothing"


def test_a_wrapper_of_ours_is_removed_when_the_extension_is_gone_and_a_foreign_file_is_never_touched(tmp_path):
    home, out = tmp_path / "home", tmp_path / "bin"
    ext = _codex_ext(home, "26.1.1")
    clis.apply(out, [clis.find("codex", str(home), [])])
    ext.unlink()
    assert clis.apply(out, [clis.find("codex", str(home), [])]) == [f"removed {out / 'codex'}"]
    assert not (out / "codex").exists()
    foreign = _binary(out / "claude", "#!/bin/sh\n# the operator's own wrapper\n")
    _claude_ext(home, "2.1.328")
    assert clis.apply(out, [clis.find("claude", str(home), [])]) == [f"kept {foreign} (not ours)"]
    assert foreign.read_text() == "#!/bin/sh\n# the operator's own wrapper\n"


def test_dry_run_writes_nothing(tmp_path):
    home, out = tmp_path / "home", tmp_path / "bin"
    _claude_ext(home, "2.1.328")
    assert clis.apply(out, [clis.find("claude", str(home), [])], dry_run=True) == [f"wrote {out / 'claude'}"]
    assert not out.exists()


def test_the_command_line_prints_one_line_per_client_and_refuses_a_home_that_is_not_plain(tmp_path):
    home, out = tmp_path / "home", tmp_path / "bin"
    _claude_ext(home, "2.1.328")
    done = subprocess.run([sys.executable, "-I", str(HELPER), "--home", str(home), "--out", str(out), "--system-dirs", ""],
                          capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    lines = done.stdout.splitlines()
    assert lines[0].startswith("claude extension ") and lines[1] == "codex missing -" and lines[2] == f"wrote {out / 'claude'}"
    bad = subprocess.run([sys.executable, "-I", str(HELPER), "--home", "/root/$(id)", "--out", str(out)],
                         capture_output=True, text=True, timeout=30)
    assert bad.returncode == 2 and "not a plain absolute path" in bad.stderr
