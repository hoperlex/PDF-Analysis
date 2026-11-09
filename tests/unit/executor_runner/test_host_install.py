"""`HOSTS-AGENT-01`: ``install.sh`` without a model (the host agent) and ``--upgrade`` (single-model agent to host mode).

Every run happens under a temporary root with stand-in system commands, exactly as in ``test_agent_install``; the
enrollment is real (``agent.py --enroll-only`` against a fake stand over loopback).  Nothing here touches the real system.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path

import pytest

_NAME = "executor_runner_host_support"
if _NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_NAME, Path(__file__).with_name("_host_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module
    _spec.loader.exec_module(_module)
H = sys.modules[_NAME]
_INSTALL = "executor_runner_install_tests"
if _INSTALL not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_INSTALL, Path(__file__).with_name("test_agent_install.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_INSTALL] = _module
    _spec.loader.exec_module(_module)
TI = sys.modules[_INSTALL]
agent = TI.agent

pytestmark = pytest.mark.skipif(sys.platform == "win32" or shutil.which("bash") is None, reason="needs bash and a POSIX host")

SECRET = H.HOST_SECRET


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    out = tmp_path_factory.mktemp("hostpackage")
    built = subprocess.run([sys.executable, str(H.RUNNER_DIR / "package.py"), "--version", TI.VERSION, "--out", str(out / "pkg")],
                           capture_output=True, text=True, timeout=60)
    assert built.returncode == 0, built.stderr
    archive = out / "pkg" / f"auditmanager-agent-{TI.VERSION}.tar.gz"
    unpacked = out / "unpacked"
    unpacked.mkdir()
    with tarfile.open(archive, "r:gz") as handle:
        handle.extractall(unpacked, filter="data")
    return {"archive": archive, "unpacked": unpacked, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}


@pytest.fixture
def host(tmp_path, package):
    return TI.Host(tmp_path, package["unpacked"])


def _run(host, stand, *args, model=None, secret=SECRET, **kwargs):
    return host.run(stand, *args, model=model, secret=secret, **kwargs)


# ------------------------------------------------------------------------------------ a fresh host install


def test_a_fresh_install_with_no_model_is_a_host_agent_with_no_model_in_its_config(host):
    with H.HostStand() as stand:
        done = _run(host, stand)
        assert done.returncode == 0, done.stdout + done.stderr
        token = host.token()
        assert token.startswith("amr_enr01_") and len(token) == 56
    text = host.config.read_text()
    document = tomllib.loads(text)
    assert document["executor"] == {"mode": "host"} and set(document) == {"runner", "executor", "host"}, "no [model], no [command]"
    assert "concurrency" not in document["runner"], "the slots, not a fixed number, bound the calls"
    assert 'key_file = "/etc/pdf-analysis-agent/keys.env"' in text
    cfg = agent.load_config(str(host.config))
    assert cfg.mode == "host" and cfg.origin == stand.origin and cfg.declared_model == "" and cfg.host.slots == {}
    # the files, including the two modules host mode imports
    for name in ("agent.py", "runner_client.py", "detect.py", "host_mode.py", "api_answer.py", "codex_answer.py", "claude_answer.py", "VERSION"):
        assert (host.app / name).is_file() and stat.S_IMODE((host.app / name).stat().st_mode) == 0o644, name
    assert stat.S_IMODE(host.env_file.stat().st_mode) == 0o600 and host.env_file.read_text() == f"PDF_ANALYSIS_RUNNER_TOKEN={token}\n"
    assert host.unit.read_text() == (H.RUNNER_DIR / "pdf-analysis-agent.service").read_text()
    assert "systemctl enable --now pdf-analysis-agent.service" in host.commands("systemctl")
    # the installer never creates, reads or fills the key file
    assert not (host.root / "etc/pdf-analysis-agent/keys.env").exists()
    assert host.leaks == []


def test_the_installer_ends_by_naming_the_steps_that_are_the_administrators_for_a_host(host):
    with H.HostStand() as stand:
        host.detected("claude_code access=subscription auth=valid version=2.1.310\nkeys file=/etc/pdf-analysis-agent/keys.env state=absent\n")
        done = _run(host, stand)
    out = done.stdout
    assert "as a host agent (no model declared)" in out
    assert "claude auth login" in out and "codex login --device-auth" in out, "both CLIs: the agent serves what it finds"
    assert "install -m 0600 -o pdf-agent -g pdf-agent /dev/null /etc/pdf-analysis-agent/keys.env" in out
    assert "ANTHROPIC_API_KEY" in out and "sends the document text to that API" in out
    assert "claude_code access=subscription auth=valid" in out, "the detection listing is printed"
    detect_calls = [line for line in host.commands("runuser") if "detect.py" in line]
    assert detect_calls and "detect.py --host --key-file /etc/pdf-analysis-agent/keys.env" in detect_calls[-1]
    assert "authorised for this integration" not in out, "that step belongs to the single-model agent's connection"


def test_a_cli_option_without_a_model_is_refused_before_anything_changes(host):
    with H.HostStand() as stand:
        for args, env in (( ("--cli", "claude"), {}), ((), {"AUDITMANAGER_AGENT_CLI": "codex"})):
            done = _run(host, stand, *args, env=env)
            assert done.returncode == 64 and "--cli belongs to a single-model agent" in done.stderr, done.stderr
        assert not host.root.exists() and stand.requests == []


def test_a_rerun_on_a_host_install_keeps_the_token_the_config_and_the_running_service(host):
    with H.HostStand() as stand:
        assert _run(host, stand).returncode == 0
        token, config = host.token(), host.config.read_text()
        before = host.commands("systemctl")
        again = _run(host, stand, secret=None)
        assert again.returncode == 0, again.stderr
    assert host.token() == token and host.config.read_text() == config
    assert "kept the existing" in again.stdout and "the service is running and nothing changed" in again.stdout
    assert not [line for line in host.commands("systemctl")[len(before):] if " restart " in line]


def test_a_model_on_a_kept_host_config_is_ignored_with_a_warning_and_reconfigure_installs_the_single_model_agent(host):
    with H.HostStand() as stand:
        assert _run(host, stand).returncode == 0
        kept = _run(host, stand, secret=None, model="claude-opus-5")
        assert kept.returncode == 0 and "is a host agent" in kept.stderr and "--reconfigure" in kept.stderr
        assert agent.load_config(str(host.config)).mode == "host"
        single = _run(host, stand, "--reconfigure", secret=None, model="claude-opus-5")
        assert single.returncode == 0, single.stderr
    cfg = agent.load_config(str(host.config))
    assert cfg.mode == "command" and cfg.declared_model == "claude-opus-5"


def test_a_single_model_install_with_a_model_is_what_it_always_was(host):
    with H.HostStand() as stand:
        done = _run(host, stand, model="claude-sonnet-5")
        assert done.returncode == 0, done.stderr
    cfg = agent.load_config(str(host.config))
    assert cfg.mode == "command" and cfg.declared_model == "claude-sonnet-5" and cfg.concurrency == 1 and cfg.host is None
    assert "authorised for this integration" in done.stdout and "as a host agent" not in done.stdout


# ------------------------------------------------------------------------------------------- --upgrade


def _legacy(host, stand):
    done = _run(host, stand, model="claude-opus-5")
    assert done.returncode == 0, done.stderr
    return host.token(), host.config.read_text()


def test_upgrade_converts_a_single_model_agent_to_host_mode_keeping_the_user_the_paths_and_the_origin(host):
    with H.HostStand() as stand:
        old_token, old_config = _legacy(host, stand)
        useradds = len(host.commands("useradd"))
        assert agent.load_config(str(host.config)).mode == "command"
        done = _run(host, stand, "--upgrade")
        assert done.returncode == 0, done.stdout + done.stderr
        new_token = host.token()
    cfg = agent.load_config(str(host.config))
    assert cfg.mode == "host" and cfg.origin == stand.origin and cfg.declared_model == ""
    assert new_token != old_token and new_token.startswith("amr_enr02_")
    assert host.env_file.read_text() == f"PDF_ANALYSIS_RUNNER_TOKEN={new_token}\n", "one token line: the connection's token is gone"
    backup = host.config.with_name("agent.toml.pre-host")
    assert backup.read_text() == old_config, "the single-model configuration is kept for a way back"
    assert len(host.commands("useradd")) == useradds, "the service user is the same one"
    assert "systemctl restart pdf-analysis-agent.service" in host.commands("systemctl")
    assert "converted the single-model agent to host mode" in done.stdout
    assert stat.S_IMODE(host.config.stat().st_mode) == 0o644 and host.leaks == []
    assert "--service-user" not in done.stdout


def test_upgrade_without_a_new_secret_or_without_an_install_or_with_a_model_changes_nothing(host):
    with H.HostStand() as stand:
        nothing = _run(host, stand, "--upgrade", secret=None)
        assert nothing.returncode == 64 and "no agent is installed here" in nothing.stderr and not host.root.exists()
        old_token, old_config = _legacy(host, stand)
        files = TI._everything_under(host.root)
        requests = len(stand.requests)
        for args, secret, code, needle in (
            (("--upgrade",), None, 78, "needs a NEW enrollment secret"),
            (("--upgrade", "--model", "claude-opus-5"), SECRET, 64, "takes no model"),
            (("--upgrade", "--cli", "claude"), SECRET, 64, "serves every CLI"),
        ):
            done = _run(host, stand, *args, secret=secret)
            assert done.returncode == code and needle in done.stderr, done.stderr
        assert TI._everything_under(host.root) == files and len(stand.requests) == requests
    assert host.token() == old_token and host.config.read_text() == old_config


def test_upgrade_whose_enrollment_is_refused_leaves_the_single_model_agent_as_it_was(host):
    with H.HostStand() as stand:
        old_token, old_config = _legacy(host, stand)
        other = "ame_zzzzzzzz_" + "Q" * 43
        done = _run(host, stand, "--upgrade", secret=other)
        assert done.returncode == 78 and "left as it was" in done.stderr, done.stderr
        assert host.token() == old_token and host.config.read_text() == old_config, "a refusal changes nothing"
        proof = _run(host, stand, "--upgrade")
        assert proof.returncode == 0, proof.stderr  # the right secret: the refusal above had left the way open
    assert agent.load_config(str(host.config)).mode == "host"
    assert old_token != host.token() and host.config.with_name("agent.toml.pre-host").read_text() == old_config


def test_upgrade_whose_stand_cannot_be_reached_keeps_the_token_and_the_config(host):
    with H.HostStand() as stand:
        old_token, old_config = _legacy(host, stand)
        origin = stand.origin
    done = _run(host, stand, "--upgrade", env={"AUDITMANAGER_STAND_ORIGIN": origin})
    assert done.returncode == 69 and "left as it was" in done.stderr, done.stderr
    assert host.token() == old_token and host.config.read_text() == old_config
    assert not host.config.with_name("agent.toml.pre-host").exists()


def test_upgrade_of_an_agent_that_is_already_a_host_agent_is_a_rerun_that_refreshes_the_files(host):
    with H.HostStand() as stand:
        assert _run(host, stand).returncode == 0
        token, config = host.token(), host.config.read_text()
        (host.app / "host_mode.py").write_text("# stale\n")
        done = _run(host, stand, "--upgrade", secret=None)
        assert done.returncode == 0, done.stderr
    assert host.token() == token and host.config.read_text() == config
    assert (host.app / "host_mode.py").read_text() == (H.RUNNER_DIR / "host_mode.py").read_text()
    assert not host.config.with_name("agent.toml.pre-host").exists()


def test_upgrade_cannot_change_the_stand_the_agent_talks_to(host):
    with H.HostStand() as stand:
        _legacy(host, stand)
        done = _run(host, stand, "--upgrade", env={"AUDITMANAGER_STAND_ORIGIN": "http://127.0.0.1:9"})
        assert done.returncode == 78 and "another origin" in done.stderr


# --------------------------------------------------------------------------------------------- uninstall


def test_uninstall_removes_the_pre_host_copy_and_never_touches_the_key_file(host):
    with H.HostStand() as stand:
        _legacy(host, stand)
        assert _run(host, stand, "--upgrade").returncode == 0
    keys = host.root / "etc/pdf-analysis-agent/keys.env"
    keys.write_text("ANTHROPIC_API_KEY=sk-ant-api03-" + "A" * 40 + "\n")
    keys.chmod(0o600)
    done = subprocess.run(["bash", str(host.app / "install.sh"), "--uninstall"], capture_output=True, text=True, timeout=60,
                          env={**os.environ, "AUDITMANAGER_INSTALL_ROOT": str(host.root),
                               "AUDITMANAGER_INSTALL_SYSCMD_DIR": str(host.syscmd), "AUDITMANAGER_PYTHON": sys.executable})
    assert done.returncode == 0, done.stderr
    assert keys.read_text().startswith("ANTHROPIC_API_KEY=") and "left in place on purpose" in done.stdout and "keys.env" in done.stdout
    assert not host.config.exists() and not host.env_file.exists() and not host.config.with_name("agent.toml.pre-host").exists()
    assert not host.app.exists()


def test_the_installer_header_documents_host_mode_upgrade_and_the_key_file(host):
    usage = subprocess.run(["bash", str(H.RUNNER_DIR / "install.sh"), "--help"], capture_output=True, text=True, timeout=30)
    assert usage.returncode == 0
    for needle in ("HOST MODE", "--upgrade", "keys.env", "mode 0600", "SINGLE-MODEL"):
        assert needle in usage.stdout, needle
    assert "A fresh install without a model is refused" not in usage.stdout


def test_the_script_is_valid_bash_and_every_app_file_it_copies_is_in_the_package():
    assert subprocess.run(["bash", "-n", str(H.RUNNER_DIR / "install.sh")], capture_output=True).returncode == 0
    script = (H.RUNNER_DIR / "install.sh").read_text()
    listed = re.search(r"^APP_FILES=\(([^)]*)\)", script, re.M).group(1).split()
    assert {"host_mode.py", "api_answer.py"} <= set(listed)
    for name in listed:
        assert (H.RUNNER_DIR / name).is_file(), name
