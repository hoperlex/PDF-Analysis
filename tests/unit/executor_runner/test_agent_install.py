"""`EXEC2-AGENT-01` -- B2 section 11, tests 3 and 5: ``install.sh``.

Every run happens under a temporary root (``AUDITMANAGER_INSTALL_ROOT``): the files go below it and the commands
that would change the real host -- ``useradd``, ``systemctl``, ``getent``, ``runuser``, ``journalctl`` -- are
shell stand-ins in a directory of their own that log what they were asked and what their environment held. The
enrollment is real: ``agent.py --enroll-only`` talks to ``_agent_support.Stand`` over loopback. Nothing here
touches the real system, starts a service or reads another account's home.
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
from pathlib import Path

import pytest

for _name, _file in (("executor_runner_support", "_support.py"), ("executor_runner_agent_support", "_agent_support.py")):
    if _name not in sys.modules:
        _spec = importlib.util.spec_from_file_location(_name, Path(__file__).with_name(_file))
        _module = importlib.util.module_from_spec(_spec)
        sys.modules[_name] = _module
        _spec.loader.exec_module(_module)
A = sys.modules["executor_runner_agent_support"]
agent = A.load_module("exec_agent_install_under_test", A.RUNNER_DIR / "agent.py")

pytestmark = pytest.mark.skipif(sys.platform == "win32" or shutil.which("bash") is None, reason="needs bash and a POSIX host")

SECRET, OTHER_SECRET = A.SECRET, A.OTHER_SECRET
VERSION = "0.9.0"
INSTALL = A.RUNNER_DIR / "install.sh"

_STUB = r"""#!/bin/sh
d=$(dirname "$0")
name=$(basename "$0")
echo "$name $*" >> "$d/log"
if env | grep -q '^AUDITMANAGER_ENROLLMENT_SECRET='; then echo "$name" >> "$d/leaks"; fi
case "$name" in
  systemctl)
    case "$1" in
      is-active) [ -f "$d/active" ]; exit $? ;;
      enable) touch "$d/active" ;;
      disable) rm -f "$d/active" ;;
    esac ;;
  useradd) touch "$d/user" ;;
  getent)
    [ -f "$d/user" ] || exit 2
    echo "$2:x:998:998::/var/lib/pdf-analysis-agent:/usr/sbin/nologin" ;;
  runuser) cat "$d/detect.out" 2>/dev/null || true ;;
  journalctl) echo "a log line of the service" ;;
esac
exit 0
"""


class Host:
    """A temporary root, the unpacked package and the stand-in system commands."""

    def __init__(self, base: Path, unpacked: Path) -> None:
        self.base = base
        self.root = base / "root"
        self.syscmd = base / "syscmd"
        self.unpacked = unpacked
        self.syscmd.mkdir(parents=True)
        for name in ("systemctl", "useradd", "getent", "runuser", "journalctl"):
            (self.syscmd / name).write_text(_STUB)
            (self.syscmd / name).chmod(0o755)

    def path(self, absolute: str) -> Path:
        return self.root / absolute.lstrip("/")

    @property
    def env_file(self) -> Path:
        return self.path("/etc/pdf-analysis-agent/agent.env")

    @property
    def config(self) -> Path:
        return self.path("/etc/pdf-analysis-agent/agent.toml")

    @property
    def unit(self) -> Path:
        return self.path("/etc/systemd/system/pdf-analysis-agent.service")

    @property
    def app(self) -> Path:
        return self.path("/opt/pdf-analysis-agent")

    @property
    def state(self) -> Path:
        return self.path("/var/lib/pdf-analysis-agent")

    def commands(self, name: str) -> list[str]:
        log = self.syscmd / "log"
        lines = log.read_text().splitlines() if log.exists() else []
        return [line for line in lines if line.split(" ", 1)[0] == name]

    def detected(self, text: str) -> None:
        (self.syscmd / "detect.out").write_text(text)

    @property
    def leaks(self) -> list[str]:
        leaks = self.syscmd / "leaks"
        return leaks.read_text().split() if leaks.exists() else []

    def token(self) -> str:
        if not self.env_file.exists():
            return ""
        match = re.search(r"^PDF_ANALYSIS_RUNNER_TOKEN=(\S+)$", self.env_file.read_text(), re.M)
        return match.group(1) if match else ""

    def run(self, stand, *args: str, secret: str | None = SECRET, origin: bool = True, model: str | None = "claude-opus-5",
            shell: tuple = (), env: dict | None = None) -> subprocess.CompletedProcess:
        environment = {k: v for k, v in os.environ.items() if not k.startswith("AUDITMANAGER_")}
        environment.update({
            "AUDITMANAGER_INSTALL_ROOT": str(self.root),
            "AUDITMANAGER_INSTALL_SYSCMD_DIR": str(self.syscmd),
            "AUDITMANAGER_PYTHON": sys.executable,
        })
        if origin:
            environment["AUDITMANAGER_STAND_ORIGIN"] = stand.origin
        if secret is not None:
            environment["AUDITMANAGER_ENROLLMENT_SECRET"] = secret
        if model is not None:
            environment["AUDITMANAGER_AGENT_MODEL"] = model  # the stand's command carries the connection's model
        environment.update(env or {})
        return subprocess.run(["bash", *shell, "install.sh", *args], cwd=self.unpacked, env=environment,
                              capture_output=True, text=True, timeout=120)


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    out = tmp_path_factory.mktemp("package")
    built = subprocess.run([sys.executable, str(A.RUNNER_DIR / "package.py"), "--version", VERSION, "--out", str(out / "pkg")],
                           capture_output=True, text=True, timeout=60)
    assert built.returncode == 0, built.stderr
    archive = out / "pkg" / f"auditmanager-agent-{VERSION}.tar.gz"
    unpacked = out / "unpacked"
    unpacked.mkdir()
    with tarfile.open(archive, "r:gz") as handle:
        handle.extractall(unpacked, filter="data")
    return {"archive": archive, "unpacked": unpacked, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}


@pytest.fixture
def host(tmp_path, package):
    return Host(tmp_path, package["unpacked"])


def _everything_under(root: Path) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}


# ------------------------------------------------------------------------------ a fresh install


def test_a_fresh_install_lays_down_the_agent_enrolls_and_starts_the_service(host):
    with A.Stand() as stand:
        done = host.run(stand)
        assert done.returncode == 0, done.stdout + done.stderr
        token = host.token()
        assert token == stand.minted[0]
    # the files, their modes, the unit as packaged
    assert stat.S_IMODE(host.env_file.stat().st_mode) == 0o600
    assert host.env_file.read_text() == f"PDF_ANALYSIS_RUNNER_TOKEN={token}\n"
    assert stat.S_IMODE(host.config.stat().st_mode) == 0o644 and stat.S_IMODE(host.state.stat().st_mode) == 0o700
    for name in ("agent.py", "runner_client.py", "detect.py", "codex_answer.py", "claude_answer.py", "VERSION"):
        assert (host.app / name).is_file() and stat.S_IMODE((host.app / name).stat().st_mode) == 0o644, name
    assert (host.app / "VERSION").read_text() == VERSION + "\n"
    assert stat.S_IMODE((host.app / "install.sh").stat().st_mode) == 0o755
    assert host.unit.read_text() == (A.RUNNER_DIR / "pdf-analysis-agent.service").read_text()
    assert not (host.app / "mcp_bridge.py").exists() and not (host.app / "workspace").exists()
    # the service user: system account, no login shell, the home the CLI logins live in
    assert host.commands("useradd") == [
        "useradd --system --user-group --create-home --home-dir /var/lib/pdf-analysis-agent --shell /usr/sbin/nologin pdf-agent"]
    # systemd: reload, enable and start once
    systemctl = host.commands("systemctl")
    assert "systemctl daemon-reload" in systemctl and systemctl.count("systemctl enable --now pdf-analysis-agent.service") == 1
    assert not [line for line in systemctl if " restart " in line]
    # the config
    cfg = agent.load_config(str(host.config))
    assert cfg.concurrency == 1 and cfg.origin == stand.origin and cfg.mode == "command" and cfg.token_env == "PDF_ANALYSIS_RUNNER_TOKEN"
    assert re.search(r"^concurrency = 1$", host.config.read_text(), re.M)
    assert cfg.declared_model == "claude-opus-5" and cfg.command_argv[1:] == ["/opt/pdf-analysis-agent/claude_answer.py", "--model", "claude-opus-5"]
    # it ends by telling the administrator the one step that is theirs
    assert "sudo -u pdf-agent -H claude auth login" in done.stdout and "codex login" not in done.stdout
    assert "login_required" in done.stdout


def test_the_secret_and_the_token_reach_no_file_but_the_environment_file_and_no_output(host):
    with A.Stand() as stand:
        done = host.run(stand)
    assert done.returncode == 0, done.stderr
    token = host.token()
    for path, content in _everything_under(host.base).items():
        assert SECRET.encode() not in content, path
        if path != host.env_file:
            assert token.encode() not in content, path
    for stream in (done.stdout, done.stderr):
        assert SECRET not in stream and token not in stream
    assert host.leaks == [], "the secret was still in the environment of a command the installer ran"
    assert SECRET not in "\n".join((host.syscmd / "log").read_text().splitlines())


@pytest.mark.parametrize("flags", [("-x",), ("-xv",)])
def test_a_shell_trace_never_shows_the_secret_or_the_token(host, flags):
    with A.Stand() as stand:
        done = host.run(stand, shell=flags, env={"SHELLOPTS": "xtrace"})
    assert done.returncode == 0, done.stderr
    token = host.token()
    assert SECRET not in done.stdout + done.stderr and token not in done.stdout + done.stderr


def test_the_secret_is_refused_on_the_command_line_and_never_echoed(host):
    with A.Stand() as stand:
        for argument in ("--secret", f"--secret={SECRET}", "--token", f"--token={SECRET}", f"--enrollment-secret={SECRET}"):
            done = host.run(stand, argument, secret=None)
            assert done.returncode == 64 and SECRET not in done.stdout + done.stderr
            assert "AUDITMANAGER_ENROLLMENT_SECRET" in done.stderr
        stray = host.run(stand, SECRET, secret=None)
        assert stray.returncode == 64 and SECRET not in stray.stdout + stray.stderr
        garbage = host.run(stand, secret="not-a-secret-garbage-value")
        assert garbage.returncode == 78 and "not-a-secret-garbage-value" not in garbage.stdout + garbage.stderr
        assert stand.requests == [] and not host.root.exists()


def test_without_a_secret_or_an_installed_token_there_is_nothing_to_enroll_with(host):
    with A.Stand() as stand:
        done = host.run(stand, secret=None)
    assert done.returncode == 78 and "AUDITMANAGER_ENROLLMENT_SECRET" in done.stderr
    assert not host.root.exists() and host.commands("systemctl") == [] and host.commands("useradd") == []


# --------------------------------------------------------------------------------------- the rerun


def test_a_rerun_on_a_working_install_keeps_the_runner_token_the_config_and_the_running_service(host):
    with A.Stand() as stand:
        assert host.run(stand).returncode == 0
        token = host.token()
        host.config.write_text(host.config.read_text() + "# the administrator's note\n")
        before = _everything_under(host.root)
        again = host.run(stand, secret=None)
        assert again.returncode == 0, again.stderr
        assert host.token() == token and len(stand.of("enroll")) == 1, "no second exchange"
    assert _everything_under(host.root) == before, "nothing on disk changed"
    assert "kept the existing" in again.stdout and "nothing changed" in again.stdout
    systemctl = host.commands("systemctl")
    assert systemctl.count("systemctl enable --now pdf-analysis-agent.service") == 1 and not [line for line in systemctl if " restart " in line]
    assert len(host.commands("useradd")) == 1, "the service user is reused"
    assert "reusing the service user" in again.stdout


def test_the_same_secret_again_inside_the_window_stores_only_the_fresh_token_and_restarts(host):
    with A.Stand() as stand:
        assert host.run(stand).returncode == 0
        first = host.token()
        again = host.run(stand)
        assert again.returncode == 0, again.stderr
        second = host.token()
        assert first != second and stand.revoked_tokens == {first}
    assert host.env_file.read_text() == f"PDF_ANALYSIS_RUNNER_TOKEN={second}\n"
    assert "systemctl restart pdf-analysis-agent.service" in host.commands("systemctl")


def test_a_secret_the_stand_already_spent_keeps_the_installed_token_and_says_so(host):
    with A.Stand() as stand:
        assert host.run(stand).returncode == 0
        token = host.token()
        stand.window_open = False
        late = host.run(stand)
        assert late.returncode == 0, late.stderr
    assert host.token() == token
    assert "was not accepted" in late.stderr and "already installed was kept" in late.stderr and "refused the enrollment secret" in late.stderr
    assert SECRET not in late.stdout + late.stderr
    assert "systemctl restart pdf-analysis-agent.service" not in host.commands("systemctl")


def test_a_command_pasted_on_a_second_host_does_not_take_the_first_hosts_token(tmp_path, package):
    with A.Stand() as stand:
        first, second = Host(tmp_path / "a", package["unpacked"]), Host(tmp_path / "b", package["unpacked"])
        assert first.run(stand).returncode == 0
        refused = second.run(stand)
        assert refused.returncode == 78 and "already redeemed" in refused.stderr
        assert second.token() == "" and "enable" not in " ".join(second.commands("systemctl"))
        assert stand.revoked_tokens == set() and first.token() == stand.minted[0]


def test_a_refused_secret_on_a_fresh_host_starts_nothing(host):
    with A.Stand() as stand:
        done = host.run(stand, secret=OTHER_SECRET)
    assert done.returncode == 78 and "refused the enrollment secret" in done.stderr
    assert OTHER_SECRET not in done.stdout + done.stderr
    assert host.token() == "" and not [line for line in host.commands("systemctl") if "enable" in line or "start" in line]


def test_a_stand_that_cannot_be_reached_is_exit_69_and_says_to_run_it_again(host):
    stand = A.Stand()
    origin = stand.origin
    stand.httpd.server_close()
    done = host.run(stand, env={"AUDITMANAGER_STAND_ORIGIN": origin})
    assert done.returncode == 69 and "again within 15 minutes" in done.stderr and host.token() == ""


# -------------------------------------------------------------------------------------------- config


def test_a_fresh_install_without_a_model_is_a_host_agent_and_a_missing_model_is_no_longer_a_refusal(host):
    """`HOSTS-AGENT-01`: the model is not asked at install. No model anywhere installs the host agent; the old
    refusal (exit 64, `no default`) belongs to nothing any more. A model still installs the single-model agent
    (the tests around this one)."""
    with A.Stand() as stand:
        done = host.run(stand, model=None)
        assert done.returncode == 0, done.stdout + done.stderr
        also_empty_env = host.run(stand, secret=None, env={"AUDITMANAGER_AGENT_MODEL": ""})
    assert also_empty_env.returncode == 0, also_empty_env.stderr
    cfg = agent.load_config(str(host.config))
    assert cfg.mode == "host" and cfg.declared_model == "" and cfg.host.key_file == "/etc/pdf-analysis-agent/keys.env"
    assert "no default" not in done.stderr and "AUDITMANAGER_AGENT_MODEL" not in done.stderr


@pytest.mark.parametrize("model,cli,declared_tail", [
    ("claude-opus-5", "claude", ["claude_answer.py", "--model", "claude-opus-5"]),
    ("claude-sonnet-5", "claude", ["claude_answer.py", "--model", "claude-sonnet-5"]),
    ("gpt-6-sol", "codex", ["codex_answer.py"]),
])
def test_the_cli_follows_from_the_model_whether_it_comes_from_the_environment_or_the_flag(tmp_path, package, model, cli, declared_tail):
    for how in ("environment", "flag"):
        host = Host(tmp_path / how, package["unpacked"])
        with A.Stand() as stand:
            done = host.run(stand, model=None, env={"AUDITMANAGER_AGENT_MODEL": model}) if how == "environment" \
                else host.run(stand, "--model", model, model=None)
            assert done.returncode == 0, done.stderr
        cfg = agent.load_config(str(host.config))
        assert cfg.declared_model == model and cfg.concurrency == 1
        assert [Path(part).name if part.endswith(".py") else part for part in cfg.command_argv[1:]] == declared_tail
        assert f"{cli}, answering as {model}" in done.stdout


def test_the_flag_wins_over_the_environment_and_a_cli_may_only_confirm_the_model(host):
    with A.Stand() as stand:
        done = host.run(stand, "--model", "gpt-6-sol", "--cli", "codex")  # the environment says claude-opus-5
        assert done.returncode == 0, done.stderr
    assert agent.load_config(str(host.config)).declared_model == "gpt-6-sol"


@pytest.mark.parametrize("args,env", [
    (("--cli", "codex"), {}),                                                   # claude-opus-5 from the environment
    (("--cli", "claude", "--model", "gpt-6-sol"), {}),
    ((), {"AUDITMANAGER_AGENT_CLI": "codex"}),
    (("--model", "claude-sonnet-5"), {"AUDITMANAGER_AGENT_CLI": "codex"}),
])
def test_a_cli_that_contradicts_the_model_is_refused_before_anything_changes(host, args, env):
    with A.Stand() as stand:
        done = host.run(stand, *args, env=env)
    assert done.returncode == 64 and "contradicts the model" in done.stderr, done.stderr
    assert not host.root.exists() and stand.requests == []


@pytest.mark.parametrize("model,needle", [
    ("gpt-5", "is not a model this agent can answer as"),
    ("o3-mini", "is not a model this agent can answer as"),
    ("claude-haiku-9", "claude_answer.py serves claude-opus-5 claude-sonnet-5, not claude-haiku-9"),
    ("claude-opus-5-20260101", "claude_answer.py serves"),
    ("Claude-Opus-5", "is not a model this agent can answer as"),
    ("claude-opus-5; touch /tmp/x", "not a model id"),
    ("x" * 70, "not a model id"),
    ("$(id)", "not a model id"),
])
def test_a_model_no_answer_command_serves_is_refused_and_nothing_is_guessed(host, model, needle):
    with A.Stand() as stand:
        done = host.run(stand, model=None, env={"AUDITMANAGER_AGENT_MODEL": model})
    assert done.returncode == 64 and needle in done.stderr, done.stderr
    assert not host.root.exists() and stand.requests == []


def test_the_models_the_installer_serves_are_the_answer_commands_own():
    script = (A.RUNNER_DIR / "install.sh").read_text()
    claude = re.search(r"^CLAUDE_MODELS=\(([^)]*)\)", script, re.M).group(1).split()
    codex = re.search(r"^CODEX_MODELS=\(([^)]*)\)", script, re.M).group(1).split()
    allowed = re.search(r"^ALLOWED_MODELS = \(([^)]*)\)", (A.RUNNER_DIR / "claude_answer.py").read_text(), re.M).group(1)
    pinned = re.search(r'^MODEL = "([^"]+)"', (A.RUNNER_DIR / "codex_answer.py").read_text(), re.M).group(1)
    assert claude == re.findall(r'"([^"]+)"', allowed) and codex == [pinned]


def test_a_rerun_without_a_model_keeps_the_configured_one_and_says_nothing_about_it(host):
    with A.Stand() as stand:
        assert host.run(stand, "--model", "gpt-6-sol", model=None).returncode == 0
        again = host.run(stand, secret=None, model=None)
        assert again.returncode == 0, again.stderr
    assert agent.load_config(str(host.config)).declared_model == "gpt-6-sol"
    assert "NOT changed" not in again.stderr and "kept the existing" in again.stdout


def test_a_rerun_with_another_model_keeps_the_config_says_so_and_applies_it_only_with_reconfigure(host):
    with A.Stand() as stand:
        assert host.run(stand, "--model", "claude-opus-5", model=None).returncode == 0
        same = host.run(stand, secret=None, model="claude-opus-5")
        assert "NOT changed" not in same.stderr
        different = host.run(stand, secret=None, model="gpt-6-sol")
        assert different.returncode == 0, different.stderr
        assert "declares the model 'claude-opus-5' but this run asks for 'gpt-6-sol'" in different.stderr
        assert "NOT changed" in different.stderr and "--reconfigure" in different.stderr
        assert agent.load_config(str(host.config)).declared_model == "claude-opus-5"
        applied = host.run(stand, "--reconfigure", secret=None, model="gpt-6-sol")
        assert applied.returncode == 0, applied.stderr
        assert "NOT changed" not in applied.stderr
        assert agent.load_config(str(host.config)).declared_model == "gpt-6-sol"
        kept = host.run(stand, "--reconfigure", secret=None, model=None)  # no model given: the configured one stays
        assert kept.returncode == 0, kept.stderr
    cfg = agent.load_config(str(host.config))
    assert cfg.declared_model == "gpt-6-sol" and Path(cfg.command_argv[1]).name == "codex_answer.py"


def test_a_model_that_is_given_is_checked_even_when_the_config_is_kept(host):
    with A.Stand() as stand:
        assert host.run(stand).returncode == 0
        refused = host.run(stand, secret=None, model="gpt-9")
    assert refused.returncode == 64 and "not a model this agent can answer as" in refused.stderr


def test_a_cli_the_user_does_not_have_does_not_stop_the_install_and_the_step_is_printed(host):
    host.detected("claude installed=no version=- auth=unknown\ncodex installed=no version=- auth=unknown\n")
    with A.Stand() as stand:
        done = host.run(stand)
    assert done.returncode == 0, done.stderr
    assert "Claude Code, which answers as claude-opus-5, is NOT installed for pdf-agent" in done.stdout
    assert "reports it to" in done.stdout and "sudo -u pdf-agent -H claude auth login" in done.stdout
    assert "systemctl enable --now pdf-analysis-agent.service" in host.commands("systemctl")  # the agent runs regardless


def test_an_installed_cli_that_is_not_signed_in_gets_only_the_login_step(host):
    host.detected("claude installed=no version=- auth=unknown\ncodex installed=yes version=0.46.0 auth=login_required\n")
    with A.Stand() as stand:
        done = host.run(stand, "--model", "gpt-6-sol")
    assert done.returncode == 0, done.stderr
    assert "NOT installed" not in done.stdout and "sign Codex in AS THE SERVICE USER" in done.stdout
    assert "sudo -u pdf-agent -H codex login --device-auth" in done.stdout and "claude auth login" not in done.stdout


@pytest.mark.parametrize("args", [("--cli", "gemini"), ("--cli", "auto"), ("--model", "gpt-9"), ("--service-user", "Root User"),
                                  ("--origin", "https://stand.example.org/api"), ("--origin", "ftp://stand"), ("--bogus",), ("--origin",)])
def test_wrong_options_are_refused_before_anything_changes(host, args):
    with A.Stand() as stand:
        done = host.run(stand, *args)
    assert done.returncode == 64, done.stderr
    assert not host.root.exists() and stand.requests == []


def test_an_existing_config_is_the_administrators_until_reconfigure_is_asked_for(host):
    with A.Stand() as stand:
        assert host.run(stand).returncode == 0
        host.config.write_text(host.config.read_text() + "# the administrator's note\n")
        assert "the administrator's note" in host.config.read_text()
        assert host.run(stand, secret=None).returncode == 0
        assert "the administrator's note" in host.config.read_text()
        other = host.run(stand, secret=None, env={"AUDITMANAGER_STAND_ORIGIN": "https://another.example.org"})
        assert other.returncode == 78 and "--reconfigure" in other.stderr
        redone = host.run(stand, "--reconfigure", "--model", "gpt-6-sol", secret=None)
        assert redone.returncode == 0, redone.stderr
    text = host.config.read_text()
    assert "the administrator's note" not in text and re.search(r"^concurrency = 1$", text, re.M)
    assert agent.load_config(str(host.config)).declared_model == "gpt-6-sol"


def test_the_origin_of_a_rerun_comes_from_the_config_when_none_is_given(host):
    with A.Stand() as stand:
        assert host.run(stand).returncode == 0
        assert host.run(stand, secret=None, origin=False).returncode == 0


def test_no_origin_anywhere_is_an_error_that_names_the_variable(host):
    with A.Stand() as stand:
        done = host.run(stand, origin=False)
    assert done.returncode == 78 and "AUDITMANAGER_STAND_ORIGIN" in done.stderr and not host.root.exists()


def test_a_service_user_of_another_name_is_in_the_unit_and_the_useradd(host):
    with A.Stand() as stand:
        assert host.run(stand, "--service-user", "agent-two").returncode == 0
    unit = host.unit.read_text()
    assert re.search(r"^User=agent-two$", unit, re.M) and re.search(r"^Group=agent-two$", unit, re.M)
    assert host.commands("useradd")[0].endswith("--shell /usr/sbin/nologin agent-two")


# ----------------------------------------------------------------- the package and the prerequisites


def test_the_archive_is_verified_against_the_digest_before_anything_is_installed(host, package):
    archive, digest = str(package["archive"]), package["sha256"]
    with A.Stand() as stand:
        wrong = host.run(stand, "--package", archive, "--sha256", "0" * 64)
        assert wrong.returncode == 65 and not host.root.exists() and stand.requests == []
        only_digest = host.run(stand, "--sha256", digest)
        assert only_digest.returncode == 64 and not host.root.exists()
        only_archive = host.run(stand, "--package", archive)
        assert only_archive.returncode == 64 and not host.root.exists()
        junk = host.run(stand, "--package", archive, "--sha256", "abc")
        assert junk.returncode == 64
        right = host.run(stand, "--package", archive, "--sha256", digest.upper())
        assert right.returncode == 0, right.stderr
    assert "package sha256 verified" in right.stdout


def test_a_python_older_than_3_11_is_refused_before_anything_is_installed(host, tmp_path):
    old = tmp_path / "python3"
    old.write_text("#!/bin/sh\nexit 1\n")
    old.chmod(0o755)
    with A.Stand() as stand:
        done = host.run(stand, env={"AUDITMANAGER_PYTHON": str(old)})
    assert done.returncode == 66 and "3.11" in done.stderr and not host.root.exists()


def test_it_must_run_from_the_unpacked_package(host, tmp_path):
    lonely = tmp_path / "lonely"
    lonely.mkdir()
    shutil.copy(INSTALL, lonely / "install.sh")
    with A.Stand() as stand:
        host.unpacked = lonely
        done = host.run(stand)
    assert done.returncode == 65 and "unpacked" in done.stderr and not host.root.exists()


def test_help_needs_no_secret_and_no_root(host):
    with A.Stand() as stand:
        done = host.run(stand, "--help", secret=None, origin=False)
    assert done.returncode == 0 and "AUDITMANAGER_ENROLLMENT_SECRET" in done.stdout and "--uninstall" in done.stdout
    assert not host.root.exists()


# ---------------------------------------------------------------------------------------- uninstall


def test_uninstall_removes_the_agent_and_never_touches_a_cli_or_a_login(host):
    other_logins = {
        host.path("/root/.codex/auth.json"): b"root's codex login",
        host.path("/home/alice/.claude/.credentials.json"): b"alice's claude login",
        host.state / ".codex" / "auth.json": b"the service user's own codex login",
        host.state / ".claude" / ".credentials.json": b"the service user's own claude login",
        host.path("/usr/local/bin/codex"): b"#!/bin/sh\n",
        host.path("/usr/bin/claude"): b"#!/bin/sh\n",
        host.path("/var/lib/pdf-analysis-agent/.npm-global/bin/codex"): b"#!/bin/sh\n",
    }
    with A.Stand() as stand:
        assert host.run(stand).returncode == 0
        for path, content in other_logins.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        done = host.run(stand, "--uninstall", secret=None, origin=False)
        assert done.returncode == 0, done.stderr
    assert not host.app.exists() and not host.unit.exists() and not host.env_file.exists() and not host.config.exists()
    assert not host.env_file.parent.exists(), "the configuration directory goes when it is empty"
    for path, content in other_logins.items():
        assert path.read_bytes() == content, f"{path} was touched"
    assert host.state.is_dir(), "the service user's home stays"
    systemctl = host.commands("systemctl")
    assert "systemctl disable --now pdf-analysis-agent.service" in systemctl and systemctl[-1] == "systemctl daemon-reload"
    assert host.commands("userdel") == [] and host.commands("deluser") == []
    assert "left in place on purpose" in done.stdout and "revoke the runner token" in done.stdout


def test_uninstall_is_repeatable_and_needs_no_secret_or_origin_and_runs_from_the_installed_copy(host):
    package_dir = host.unpacked
    with A.Stand() as stand:
        assert host.run(stand).returncode == 0
        installed_copy = host.app / "install.sh"
        host.unpacked = host.app  # the copy the installer left behind removes the agent from where it lives
        first = host.run(stand, "--uninstall", secret=None, origin=False)
        assert first.returncode == 0, first.stderr
        host.unpacked = package_dir
        second = host.run(stand, "--uninstall", secret=None, origin=False)
        assert second.returncode == 0, second.stderr
    assert not installed_copy.exists() and not host.app.exists()


def test_no_credential_is_ever_copied_into_the_service_users_home(host):
    with A.Stand() as stand:
        for path in (host.path("/root/.codex/auth.json"), host.path("/home/alice/.claude/.credentials.json")):
            path.parent.mkdir(parents=True)
            path.write_text("a login that must stay where it is")
        assert host.run(stand).returncode == 0
    assert list(host.state.rglob("*")) == []


# ------------------------------------------------------------------------------- what it says in code


def test_the_script_is_valid_bash_and_strict():
    script = INSTALL.read_text()
    assert script.startswith("#!/usr/bin/env bash\n") and "\nset -euo pipefail\n" in script
    assert subprocess.run(["bash", "-n", str(INSTALL)], capture_output=True, text=True).returncode == 0
    assert os.access(INSTALL, os.X_OK)


def test_the_script_fetches_nothing_evaluates_nothing_and_hardcodes_no_account_path():
    script = INSTALL.read_text()
    for forbidden in ("curl ", "wget ", "eval ", "bash -c", "sh -c", "chmod 777", "chmod -R", "rm -rf /",
                      "/home/", "/root/", ".codex", ".claude", "auth.json", ".credentials", "cp -r", "rsync"):
        assert forbidden not in script, forbidden
    assert "AUDITMANAGER_ENROLLMENT_SECRET" in script


def test_the_secret_variable_is_read_unset_checked_and_passed_in_the_environment_of_one_command_only():
    allowed = {
        'GRANT="${AUDITMANAGER_ENROLLMENT_SECRET-}"',
        "unset AUDITMANAGER_ENROLLMENT_SECRET",
        'if [ -n "$GRANT" ]; then',
        'if ! [[ "$GRANT" =~ ^ame_[0-9a-z]{8}_[A-Za-z0-9_-]{43}$ ]]; then',
        'GRANT=""',
        'if [ -z "$GRANT" ] && [ "$HAD_TOKEN" -eq 0 ]; then',
        'AUDITMANAGER_ENROLLMENT_SECRET="$GRANT" "$PYTHON" "$APP_DIR/agent.py" \\',
    }
    seen = set()
    for number, line in enumerate(INSTALL.read_text().splitlines(), 1):
        text = line.strip()
        if text.startswith("#") or ("GRANT" not in text and "AUDITMANAGER_ENROLLMENT_SECRET" not in text):
            continue
        if text.startswith("die "):  # a refusal that names the variable and never its value
            assert "$GRANT" not in text and "${GRANT" not in text, (number, line)
            continue
        assert text in allowed, (number, line)
        seen.add(text)
    assert seen == allowed, allowed - seen


def test_the_installed_unit_keeps_the_exit_code_semantics_the_agent_relies_on(host):
    with A.Stand() as stand:
        assert host.run(stand).returncode == 0
    lines = [line.strip() for line in host.unit.read_text().splitlines() if line.strip() and not line.startswith("#")]
    assert "RestartPreventExitStatus=2 3" in lines and "Restart=on-failure" in lines
    assert "EnvironmentFile=/etc/pdf-analysis-agent/agent.env" in lines and "NoNewPrivileges=true" in lines
    assert not [line for line in lines if line.startswith("ExecStart=") and ("--env-file" in line or "--enroll-only" in line)]
    assert "StateDirectory=pdf-analysis-agent" in lines and "StateDirectoryMode=0700" in lines
    assert [line for line in lines if line.startswith("Environment=PATH=")]
