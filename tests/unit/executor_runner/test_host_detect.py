"""`HOSTS-AGENT-01`: what host mode detects -- the two CLIs with the access of their login, and the key file.

Cheap detection only (no model is called).  The CLIs are stand-ins (`_host_support.make_fake`); the key file is a file
in a temporary directory.  The rules under test: the access comes from the CLI's own status command and from nothing
else; the key file is read only when it is a regular file, mode 0600 and owned by the user running the process, and
only for three names; no key value is ever in a result, a repr or a printed line.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

import pytest

_NAME = "executor_runner_host_support"
if _NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_NAME, Path(__file__).with_name("_host_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module
    _spec.loader.exec_module(_module)
H = sys.modules[_NAME]
detect = None


def _load():
    global detect
    if detect is None:
        sys.path.insert(0, str(H.RUNNER_DIR))
        try:
            spec = importlib.util.spec_from_file_location("exec_host_detect_under_test", H.RUNNER_DIR / "detect.py")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(str(H.RUNNER_DIR))
        detect = module
    return detect


detect = _load()

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes and shell stand-ins")

KEY_A = "sk-ant-api03-" + "A" * 40
KEY_O = "sk-proj-" + "B" * 40
KEY_R = "sk-or-v1-" + "C" * 40


def _env(home: Path, bin_dir: Path) -> dict:
    return {"HOME": str(home), detect.DIRS_ENV: str(bin_dir), "LANG": "C.UTF-8"}


def _write_keys(path: Path, text: str, mode: int = 0o600) -> Path:
    path.write_text(text)
    path.chmod(mode)
    return path


# ------------------------------------------------------------------------------------------ the CLIs


@pytest.mark.parametrize("auth,access,state", [
    ("subscription", "subscription", "valid"),
    ("api", "api", "valid"),
    ("out", "subscription", "login_required"),
    ("weird", "api", "unknown"),
])
def test_claude_access_comes_from_its_status_document_and_an_unknown_method_is_not_guessed(tmp_path, auth, access, state):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    H.make_fake(bin_dir, "claude", auth=auth)
    found = detect.detect_host(environ=_env(home, bin_dir), key_file=str(tmp_path / "none.env"))
    [claude] = [p for p in found.providers if p.provider == "claude_code"]
    assert (claude.access, claude.auth_state, claude.cli_version) == (access, state, "2.1.310")
    assert claude.cli_path == str(bin_dir / "claude")
    # the contract's `clis` array is what any agent reports: the account and the method are not in it
    text = json.dumps(found.clis)
    assert "someone@example.com" not in text and "authMethod" not in text and str(tmp_path) not in text


@pytest.mark.parametrize("login,access,state", [
    ("chatgpt", "subscription", "valid"),
    ("apikey", "api", "valid"),
    ("out", "subscription", "login_required"),
    ("other", "api", "unknown"),
])
def test_codex_access_comes_from_its_login_status_and_an_unknown_login_is_not_guessed(tmp_path, login, access, state):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    H.make_fake(bin_dir, "codex", login=login)
    found = detect.detect_host(environ=_env(home, bin_dir), key_file=str(tmp_path / "none.env"))
    [codex] = [p for p in found.providers if p.provider == "codex"]
    assert (codex.access, codex.auth_state) == (access, state)
    assert "sk-" not in json.dumps(found.clis) and "***" not in repr(found)


def test_a_cli_that_is_not_installed_is_no_provider_and_a_too_old_claude_is_unknown(tmp_path):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    H.make_fake(bin_dir, "claude", version="2.0.5")
    found = detect.detect_host(environ=_env(home, bin_dir), key_file=str(tmp_path / "none.env"))
    assert [p.provider for p in found.providers] == ["claude_code"]
    assert found.providers[0].auth_state == "unknown"
    assert H.model_calls(bin_dir) == []  # detection never calls a model


def test_the_clis_get_a_reduced_environment_without_any_key_or_token(tmp_path):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    probe = bin_dir / "codex"
    bin_dir.mkdir()
    probe.write_text('#!/bin/sh\n/usr/bin/env > "${0%/*}/env.txt"\ncase "$1" in --version) echo "codex-cli 0.46.0";; '
                     'login) echo "Logged in using ChatGPT";; esac\nexit 0\n')
    probe.chmod(0o755)
    env = {**_env(home, bin_dir), "ANTHROPIC_API_KEY": KEY_A, "OPENAI_API_KEY": KEY_O, "OPENROUTER_API_KEY": KEY_R,
           "PDF_ANALYSIS_RUNNER_TOKEN": "amr_x", "CODEX_API_KEY": "k"}
    detect.detect_host(environ=env, key_file=str(tmp_path / "none.env"))
    seen = (bin_dir / "env.txt").read_text()
    for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "PDF_ANALYSIS_RUNNER_TOKEN", "CODEX_API_KEY"):
        assert name not in seen, name
    assert KEY_A not in seen and KEY_O not in seen and KEY_R not in seen


# ------------------------------------------------------------------------------------------ the key file


def test_a_key_file_gives_its_providers_and_never_a_value(tmp_path):
    path = _write_keys(tmp_path / "keys.env", f"# keys\nANTHROPIC_API_KEY={KEY_A}\nexport OPENAI_API_KEY='{KEY_O}'\n"
                                              f"OPENROUTER_API_KEY=\"{KEY_R}\"\n")
    keys = detect.read_key_file(str(path))
    assert keys.usable and keys.reason is None
    assert keys.providers == ("anthropic_api", "openai_api", "openrouter_api")
    shown = repr(keys) + keys.describe() + json.dumps(list(keys.fingerprints))
    for value in (KEY_A, KEY_O, KEY_R):
        assert value not in shown
    assert detect.read_api_key("anthropic_api", str(path)) == KEY_A
    assert detect.read_api_key("openai_api", str(path)) == KEY_O
    assert detect.read_api_key("openrouter_api", str(path)) == KEY_R


def test_only_the_three_names_are_read_and_nothing_else_of_the_file_is_kept(tmp_path):
    path = _write_keys(tmp_path / "keys.env", f"SOME_OTHER_SECRET=hunter2hunter2\nGITHUB_TOKEN=ghp_{'x' * 30}\n"
                                              f"ANTHROPIC_API_KEY={KEY_A}\nDATABASE_URL=postgres://u:p@h/db\n")
    keys = detect.read_key_file(str(path))
    assert keys.providers == ("anthropic_api",)
    assert "hunter2" not in repr(keys) and "ghp_" not in repr(keys) and "postgres" not in repr(keys)
    with pytest.raises(ValueError):
        detect.read_api_key("codex", str(path))  # a CLI provider has no key


@pytest.mark.parametrize("mode,reason", [(0o644, "mode_is_not_0600"), (0o640, "mode_is_not_0600"), (0o666, "mode_is_not_0600"),
                                         (0o400, "mode_is_not_0600"), (0o700, "mode_is_not_0600")])
def test_a_key_file_of_another_mode_is_ignored_with_a_reason_and_yields_no_key(tmp_path, mode, reason):
    path = _write_keys(tmp_path / "keys.env", f"ANTHROPIC_API_KEY={KEY_A}\n", mode)
    keys = detect.read_key_file(str(path))
    assert keys.present and not keys.usable and keys.reason == reason and keys.providers == ()
    assert detect.read_api_key("anthropic_api", str(path)) is None
    assert reason in keys.describe()


def test_a_key_file_owned_by_another_user_is_ignored(tmp_path):
    path = _write_keys(tmp_path / "keys.env", f"ANTHROPIC_API_KEY={KEY_A}\n")
    other = os.geteuid() + 1
    keys = detect.read_key_file(str(path), expected_uid=other)
    assert not keys.usable and keys.reason == "not_owned_by_the_service_user" and keys.providers == ()
    assert detect.read_api_key("anthropic_api", str(path), expected_uid=other) is None
    assert detect.read_key_file(str(path), expected_uid=os.geteuid()).usable


def test_a_symbolic_link_a_directory_and_a_missing_file_are_not_read(tmp_path):
    real = _write_keys(tmp_path / "real.env", f"ANTHROPIC_API_KEY={KEY_A}\n")
    link = tmp_path / "keys.env"
    link.symlink_to(real)
    assert detect.read_key_file(str(link)).reason == "not_a_regular_file"
    assert detect.read_api_key("anthropic_api", str(link)) is None
    (tmp_path / "dir.env").mkdir()
    assert detect.read_key_file(str(tmp_path / "dir.env")).reason in ("not_a_regular_file", "unreadable")
    missing = detect.read_key_file(str(tmp_path / "absent.env"))
    assert not missing.present and missing.reason is None and not missing.usable and missing.describe() == "absent"


def test_an_unusable_value_is_ignored_by_name_and_the_last_good_line_wins(tmp_path):
    path = _write_keys(tmp_path / "keys.env", f"ANTHROPIC_API_KEY=short\nOPENAI_API_KEY={KEY_O}\nOPENAI_API_KEY=has space inside\n"
                                              f"OPENROUTER_API_KEY=first-{'x' * 12}\nOPENROUTER_API_KEY={KEY_R}\n")
    keys = detect.read_key_file(str(path))
    assert keys.providers == ("openrouter_api",)
    assert sorted(keys.rejected) == ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
    assert detect.read_api_key("openrouter_api", str(path)) == KEY_R


def test_a_rotated_key_changes_the_fingerprint_and_an_untouched_one_does_not(tmp_path):
    path = _write_keys(tmp_path / "keys.env", f"ANTHROPIC_API_KEY={KEY_A}\nOPENAI_API_KEY={KEY_O}\n")
    before = dict(detect.read_key_file(str(path)).fingerprints)
    _write_keys(path, f"ANTHROPIC_API_KEY={KEY_A}\nOPENAI_API_KEY={KEY_O[:-3]}xyz\n")
    after = dict(detect.read_key_file(str(path)).fingerprints)
    assert before["anthropic_api"] == after["anthropic_api"] and before["openai_api"] != after["openai_api"]
    assert all(len(v) == 16 and KEY_A not in v for v in after.values())


def test_detection_adds_one_api_provider_per_key_with_access_api_and_orders_them(tmp_path):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    H.make_fake(bin_dir, "codex")
    keys = _write_keys(tmp_path / "keys.env", f"OPENROUTER_API_KEY={KEY_R}\nANTHROPIC_API_KEY={KEY_A}\n")
    found = detect.detect_host(environ=_env(home, bin_dir), key_file=str(keys))
    assert [p.provider for p in found.providers] == ["codex", "anthropic_api", "openrouter_api"]
    api = [p for p in found.providers if p.provider.endswith("_api")]
    assert all(p.access == "api" and p.cli_path is None and p.credential for p in api)
    assert KEY_A not in repr(found) and KEY_R not in repr(found)
    # a key file that is ignored gives no API provider, and says why
    keys.chmod(0o644)
    ignored = detect.detect_host(environ=_env(home, bin_dir), key_file=str(keys))
    assert [p.provider for p in ignored.providers] == ["codex"] and ignored.key_file.reason == "mode_is_not_0600"


def test_the_command_line_prints_the_providers_and_the_key_file_state_without_a_key(tmp_path, capsys, monkeypatch):
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    home.mkdir()
    H.make_fake(bin_dir, "claude", auth="api")
    keys = _write_keys(tmp_path / "keys.env", f"OPENAI_API_KEY={KEY_O}\n", 0o644)
    for name, value in _env(home, bin_dir).items():
        monkeypatch.setenv(name, value)
    assert detect.main(["--host", "--key-file", str(keys)]) == 0
    out = capsys.readouterr().out
    assert "claude_code access=api auth=valid version=2.1.310" in out
    assert "ignored: mode_is_not_0600" in out and KEY_O not in out
    # without --host the output is what it always was
    assert detect.main([]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "claude installed=yes version=2.1.310 auth=valid", "codex installed=no version=- auth=unknown"]
