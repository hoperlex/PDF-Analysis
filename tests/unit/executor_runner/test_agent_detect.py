"""`EXEC2-AGENT-01` -- B2 section 11, test 4: detection of the ``codex`` and ``claude`` CLIs.

Installed and version come from the client run by its absolute path; the authentication state only from the
client's own status command, run as the user the process runs as; what comes back is the contract's closed
enumerations and nothing the client printed. The CLIs are stand-ins (``_agent_support.make_cli``) that log in
exactly when ``$HOME`` holds the file a real login leaves, which is how "signed in under another account" is
modelled: that account's home is a different directory.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import time
from pathlib import Path

import pytest

_SUPPORT = "executor_runner_agent_support"
if _SUPPORT not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_SUPPORT, Path(__file__).with_name("_agent_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_SUPPORT] = _module
    _spec.loader.exec_module(_module)
A = sys.modules[_SUPPORT]
detect = A.load_module("exec_detect_under_test", A.RUNNER_DIR / "detect.py")

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="the stand-in CLIs are POSIX shell scripts")

STATES = {"valid", "login_required", "unknown"}


def _env(home: Path, bin_dir: Path, **extra: str) -> dict:
    return {"HOME": str(home), detect.DIRS_ENV: str(bin_dir), "ANTHROPIC_API_KEY": "sk-must-not-reach-the-cli", **extra}


def _by_name(clis: list[dict]) -> dict:
    return {item["cli"]: item for item in clis}


def test_the_names_looked_for_are_the_contracts_and_nothing_else():
    assert detect.CLI_NAMES == ("claude", "codex")
    with pytest.raises(ValueError):
        detect.find_executable("bash", ["/usr/bin"])
    document = json.loads(A.OPENAPI.read_text())
    assert document["components"]["schemas"]["RunnerCliName"]["enum"] == sorted(detect.CLI_NAMES)


def test_installed_clis_are_found_by_absolute_path_with_their_version_and_login_state(tmp_path):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    A.make_cli(bin_dir, "codex", "0.46.0")
    A.make_cli(bin_dir, "claude", "2.1.310")
    A.log_in(home, "codex")
    A.log_in(home, "claude")
    clis = detect.detect_all(environ=_env(home, bin_dir))
    assert [item["cli"] for item in clis] == ["claude", "codex"]
    assert _by_name(clis) == {
        "claude": {"cli": "claude", "installed": True, "version": "2.1.310", "auth_state": "valid"},
        "codex": {"cli": "codex", "installed": True, "version": "0.46.0", "auth_state": "valid"},
    }
    assert A.schema_errors("ReportRunnerHealthRequest", {
        "agent_version": "1.2.3", "clis": clis, "concurrency": 1, "execution_profile": "command", "features": []}) == []


def test_a_login_that_exists_only_under_another_os_user_is_login_required_and_never_borrowed(tmp_path):
    """The service user's home has no login; another account's home has both. Detection runs as the first and
    reports ``login_required``: it never looks at the other home, so it cannot report that login as its own."""
    bin_dir = tmp_path / "bin"
    service_home, other_home = tmp_path / "var-lib-agent", tmp_path / "home-alice"
    service_home.mkdir()
    A.make_cli(bin_dir, "codex", "0.46.0")
    A.make_cli(bin_dir, "claude", "2.1.310")
    A.log_in(other_home, "codex")
    A.log_in(other_home, "claude")
    as_service = _by_name(detect.detect_all(environ=_env(service_home, bin_dir)))
    assert as_service["codex"]["auth_state"] == "login_required"
    assert as_service["claude"]["auth_state"] == "login_required"
    as_other = _by_name(detect.detect_all(environ=_env(other_home, bin_dir)))
    assert as_other["codex"]["auth_state"] == as_other["claude"]["auth_state"] == "valid"
    source = (A.RUNNER_DIR / "detect.py").read_text()
    for forbidden in ("/home", "getpwnam", "getpwall", "import pwd", "sudo", "runuser", "os.setuid", "shell=True"):
        assert forbidden not in source, forbidden


def test_a_client_that_is_not_installed_is_unknown_with_no_version(tmp_path):
    clis = _by_name(detect.detect_all(environ=_env(tmp_path, tmp_path / "empty")))
    for name in ("claude", "codex"):
        assert clis[name] == {"cli": name, "installed": False, "auth_state": "unknown"}  # no "version" member at all


def test_a_non_executable_file_and_a_relative_directory_are_not_a_client(tmp_path):
    bin_dir = tmp_path / "bin"
    path = A.make_cli(bin_dir, "codex", "0.46.0")
    path.chmod(0o644)
    assert detect.find_executable("codex", [str(bin_dir)]) is None
    path.chmod(0o755)
    assert detect.search_dirs({detect.DIRS_ENV: f"bin:.::{bin_dir}"}) == [str(bin_dir)]
    assert detect.find_executable("codex", detect.search_dirs({detect.DIRS_ENV: str(bin_dir)})) == str(bin_dir / "codex")


def test_the_default_search_list_is_fixed_and_the_homes_are_the_running_users_own():
    dirs = detect.search_dirs({"HOME": "/var/lib/pdf-analysis-agent"})
    assert dirs == ["/usr/local/bin", "/usr/bin", "/bin", "/snap/bin",
                    "/var/lib/pdf-analysis-agent/.local/bin", "/var/lib/pdf-analysis-agent/.npm-global/bin"]
    assert detect.search_dirs({"HOME": "relative/home"}) == list(detect.SYSTEM_DIRS)
    assert all(entry.startswith("/") for entry in dirs)


def test_the_status_commands_are_the_official_ones_and_nothing_else_is_asked(tmp_path):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    A.make_cli(bin_dir, "codex", "0.46.0")
    A.make_cli(bin_dir, "claude", "2.1.310")
    detect.detect_all(environ=_env(home, bin_dir))
    assert sorted(A.calls(bin_dir)) == sorted(["--version", "login status", "--version", "auth status"])


def test_a_claude_older_than_the_documented_status_command_is_not_asked_and_is_unknown(tmp_path):
    """``claude auth status`` is documented from 2.1.268; an older client could read the words as a prompt."""
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    A.log_in(home, "claude")
    A.make_cli(bin_dir, "claude", "2.0.5")
    claude = _by_name(detect.detect_all(environ=_env(home, bin_dir)))["claude"]
    assert claude == {"cli": "claude", "installed": True, "version": "2.0.5", "auth_state": "unknown"}
    assert A.calls(bin_dir) == ["--version"]


def test_a_client_whose_version_cannot_be_read_is_installed_with_no_version_and_unknown_claude_auth(tmp_path):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    path = A.make_cli(bin_dir, "claude", "x")
    path.write_text("#!/bin/sh\necho 'Claude Code, build of last week'\nexit 0\n")
    claude = _by_name(detect.detect_all(environ=_env(home, bin_dir)))["claude"]
    assert claude == {"cli": "claude", "installed": True, "auth_state": "unknown"}


def test_what_the_client_prints_never_reaches_the_report(tmp_path):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    A.make_cli(bin_dir, "codex", "0.46.0")
    A.make_cli(bin_dir, "claude", "2.1.310")
    A.log_in(home, "claude")
    clis = detect.detect_all(environ=_env(home, bin_dir))
    text = json.dumps(clis)
    for leaked in ("someone@example.com", "authMethod", "ChatGPT", "Logged in", "/", str(tmp_path), str(home)):
        assert leaked not in text, leaked
    for item in clis:
        assert set(item) <= {"cli", "installed", "version", "auth_state"} and item["auth_state"] in STATES


def test_an_unexpected_status_answer_is_unknown_not_a_guess(tmp_path):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    codex = A.make_cli(bin_dir, "codex", "0.46.0")
    codex.write_text('#!/bin/sh\ncase "$1" in --version) echo "codex-cli 0.46.0"; exit 0;; esac\n'
                     'echo "error: unrecognized subcommand"; exit 2\n')
    claude = A.make_cli(bin_dir, "claude", "2.1.310")
    claude.write_text('#!/bin/sh\ncase "$1" in --version) echo "2.1.310"; exit 0;; esac\nexit 3\n')
    clis = _by_name(detect.detect_all(environ=_env(home, bin_dir)))
    assert clis["codex"]["auth_state"] == "unknown" and clis["claude"]["auth_state"] == "unknown"


def test_codex_needs_both_a_failure_status_and_the_words_not_logged_in_to_say_login_required(tmp_path):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    codex = A.make_cli(bin_dir, "codex", "0.46.0")
    codex.write_text('#!/bin/sh\ncase "$1" in --version) echo "codex-cli 0.46.0"; exit 0;; esac\n'
                     'echo "Not logged in"; exit 0\n')
    assert _by_name(detect.detect_all(environ=_env(home, bin_dir)))["codex"]["auth_state"] == "login_required"


def test_a_client_that_hangs_is_killed_and_reported_unknown_within_the_limit(tmp_path):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    codex = A.make_cli(bin_dir, "codex", "0.46.0")
    codex.write_text('#!/bin/sh\ncase "$1" in --version) echo "codex-cli 0.46.0"; exit 0;; esac\nsleep 30\n')
    started = time.monotonic()
    clis = _by_name(detect.detect_all(environ=_env(home, bin_dir), timeout=0.5))
    assert time.monotonic() - started < 10
    assert clis["codex"] == {"cli": "codex", "installed": True, "version": "0.46.0", "auth_state": "unknown"}


def test_the_client_gets_a_reduced_environment_and_a_closed_stdin(tmp_path):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    probe = A.make_cli(bin_dir, "codex", "0.46.0")
    probe.write_text('#!/bin/sh\nenv > "$(dirname "$0")/env.txt"\nread line < /dev/stdin && echo "stdin:$line" >> "$(dirname "$0")/env.txt"\n'
                     'case "$1" in --version) echo "codex-cli 0.46.0";; esac\nexit 0\n')
    detect.detect_cli("codex", environ=_env(home, bin_dir, SECRET_THING="x", PDF_ANALYSIS_RUNNER_TOKEN="amr_nope"))
    seen = (bin_dir / "env.txt").read_text()
    assert "ANTHROPIC_API_KEY" not in seen and "SECRET_THING" not in seen and "PDF_ANALYSIS_RUNNER_TOKEN" not in seen
    assert f"HOME={home}" in seen and "stdin:" not in seen


@pytest.mark.parametrize("text,expected", [
    (b"codex-cli 0.46.0\n", "0.46.0"),
    (b"2.1.310 (Claude Code)\n", "2.1.310"),
    (b"claude 2.1.310-beta.1\n", "2.1.310-beta.1"),
    (b"no number here", None),
    (b"v1.2\n", None),
    (b"\xff\xfe 3.4.5", "3.4.5"),
    (b"x" * 5000 + b" 9.9.9", None),
])
def test_version_parsing_keeps_only_a_contract_shaped_version(text, expected):
    assert detect.parse_version(text[:detect.MAX_OUTPUT_BYTES]) == expected
    if expected is not None:
        assert re.fullmatch(r"^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$", expected)


def test_the_command_line_prints_one_line_per_client_and_json_on_request(tmp_path, capsys, monkeypatch):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    A.make_cli(bin_dir, "codex", "0.46.0")
    for name, value in _env(home, bin_dir).items():
        monkeypatch.setenv(name, value)
    assert detect.main([]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == ["claude installed=no version=- auth=unknown", "codex installed=yes version=0.46.0 auth=login_required"]
    assert detect.main(["--json"]) == 0
    assert json.loads(capsys.readouterr().out) == [
        {"cli": "claude", "installed": False, "auth_state": "unknown"},
        {"cli": "codex", "installed": True, "version": "0.46.0", "auth_state": "login_required"}]
