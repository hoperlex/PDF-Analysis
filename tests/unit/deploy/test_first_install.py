"""`infra/deploy/first-install.sh`: the one command that installs the stack on a fresh server, driven end to end against stubs.

**Nothing here reaches docker, a network or a host.** The script runs from a throw-away clone (a copy of the script, its helpers
and the example files, in a fresh git repository whose `origin` is a GitHub-shaped URL), with `FIRST_INSTALL_TEST_MODE=1`, which
redirects every path the script would write outside the clone (`/var/lib`, `/root`, `/var/log`, `/srv/...`) into the test's
directory. `docker`, `df`, `getent` and `ip` are stubs at the head of `PATH`; `deploy.sh`, `verify-deployed.sh`, `local-agent.sh`
and `reload-proxy.sh` inside the clone are stubs that follow a plan (the exit status and the line each call prints) and log what
the environment file said at the time of the call. The administrator stage talks to the stand-in API of `fake_stack.py` on a
loopback port.

What is held:

* the output contract: every stop is one line `STOP [code]: <action>` for a code in the one table, and a non-zero exit; success
  ends with `DONE:`; `--print-codes` is the table; `--dry-run` changes nothing;
* idempotency: a rerun after a stop continues (the environment file is not touched, finished stages are skipped); a finished
  installation refuses a second run, and `--resume-stage` is the explicit way past that;
* the stages' decisions: the expected `[default_credential]` first deploy, the order of the HTTPS deploys and what the
  environment file said at each, the DNS and port checks, the executors stop, the verification exit code;
* **no secret leaves**: not the generated passwords and token, not the administrator's password, not the deploy key.

What this cannot prove, because the stubs stand in for it: that the real `deploy.sh` builds and starts the stack, that the real
certificate authority issues, and that a real server has what the preflight asks for. Those are the first run on a server.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "infra" / "deploy"
SCRIPT = DEPLOY / "first-install.sh"
PROMPT = DEPLOY / "FIRST-INSTALL-PROMPT.md"
STOP_LINE = re.compile(r"^STOP \[([a-z_]+)\]: (\S.*)$")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fie = _load("first_install_env_for_script_tests", DEPLOY / "lib" / "first_install_env.py")
fake_stack = _load("first_install_fake_stack_for_script_tests", Path(__file__).with_name("fake_stack.py"))

DOMAIN = "audit.auditco.net"
EMAIL = "owner@auditco.net"
GATE = r"deploy.sh: REFUSED: [default_credential] the published admin/password pair is valid: admin still accepts it."

DOCKER_STUB = r"""#!/usr/bin/env bash
echo "docker $*" >> "$STUB_STATE/docker.log"
case "$1" in
    info)
        if [ "${2:-}" = --format ]; then echo "$STUB_DOCKER_ROOT"; exit 0; fi
        [ ! -f "$STUB_STATE/docker.down" ] || exit 1
        exit 0 ;;
    version) cat "$STUB_STATE/docker.version" 2>/dev/null || echo 27.3.1; exit 0 ;;
    compose) if [ "${2:-}" = version ]; then cat "$STUB_STATE/compose.version" 2>/dev/null || echo v2.29.1; fi; exit 0 ;;
    ps) cat "$STUB_STATE/docker.ps" 2>/dev/null || true; exit 0 ;;
esac
exit 0
"""
DF_STUB = r"""#!/usr/bin/env bash
printf 'Avail\n%s\n' "${STUB_DF_BYTES:-200000000000}"
"""
GETENT_STUB = r"""#!/usr/bin/env bash
if [ "$1" = ahostsv4 ]; then
    [ -f "$STUB_STATE/dns-$2" ] || exit 2
    while read -r address; do echo "$address STREAM $2"; done < "$STUB_STATE/dns-$2"
    exit 0
fi
exec /usr/bin/getent "$@"
"""
IP_STUB = r"""#!/usr/bin/env bash
printf '2: eth0    inet %s/24 scope global eth0\n' "${STUB_IP:-203.0.113.7}"
"""
# A deploy.sh / verify-deployed.sh: pops the next `status|text` of its plan (no plan: 0), prints the text and logs what the
# environment file said, which is what the HTTPS order is about.
DEPLOY_STUB = r"""#!/usr/bin/env bash
state="$STUB_STATE"
env_file=""
while [ "$#" -gt 0 ]; do case "$1" in --env-file) env_file="$2"; shift 2 ;; *) shift ;; esac; done
get() { sed -n "s/^$1=//p" "$env_file" | tail -n 1; }
printf 'deploy cert=%s staging=%s publish=%s email=%s\n' "$(get ALPHA_CERT_NAME)" "$(get ALPHA_ACME_STAGING)" \
    "$(get ALPHA_PUBLISH_HTTPS)" "$(get ALPHA_ACME_EMAIL)" >> "$state/calls.log"
line="$(head -n 1 "$state/deploy.plan" 2>/dev/null || true)"
if [ -n "$line" ]; then sed -i 1d "$state/deploy.plan"; else line="0|deploy.sh: stub deploy ok"; fi
printf '%b\n' "${line#*|}"
exit "${line%%|*}"
"""
VERIFY_STUB = r"""#!/usr/bin/env bash
state="$STUB_STATE"
echo "verify $*" >> "$state/calls.log"
line="$(head -n 1 "$state/verify.plan" 2>/dev/null || true)"
if [ -n "$line" ]; then sed -i 1d "$state/verify.plan"; else line="0|verify ok"; fi
printf '%b\n' "${line#*|}"
exit "${line%%|*}"
"""
AGENT_STUB = r"""#!/usr/bin/env bash
state="$STUB_STATE"
command=""
for word in "$@"; do case "$word" in status|connect) command="$word" ;; esac; done
echo "local-agent $command" >> "$state/calls.log"
if [ "$command" = status ]; then cat "$state/agent.status" 2>/dev/null || true; exit 0; fi
exit "$(cat "$state/agent.connect" 2>/dev/null || echo 0)"
"""
RELOAD_STUB = '#!/usr/bin/env bash\necho "reload-proxy $*" >> "$STUB_STATE/calls.log"\n'
SUBSCRIPTION = "  claude_code installed access=subscription auth=valid\n"


class Rig:
    """One throw-away clone, its stubs, and the directories the script writes to."""

    def __init__(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.repo = tmp_path / "clone"
        self.bin = tmp_path / "bin"
        self.stub = tmp_path / "stubstate"
        self.state_root = tmp_path / "var-lib"
        self.log_dir = tmp_path / "var-log"
        self.secret_dir = tmp_path / "root-home"
        self.copy_dir = tmp_path / "srv-copy"
        self.staging = tmp_path / "srv-bundles"
        self.auth_home = tmp_path / "auth-home"
        self.proc_net = tmp_path / "proc-net"
        self.meminfo = tmp_path / "meminfo"
        self.host_key = tmp_path / "ssh_host_ed25519_key.pub"
        for directory in (self.bin, self.stub, self.state_root, self.log_dir, self.secret_dir, self.auth_home, self.proc_net):
            directory.mkdir(parents=True)
        self.meminfo.write_text("MemTotal:  8000000 kB\nMemAvailable:  6000000 kB\n")
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(tmp_path / "hostkey")], check=True)
        shutil.copy(tmp_path / "hostkey.pub", self.host_key)
        self._build_clone()
        for name, body in (("docker", DOCKER_STUB), ("df", DF_STUB), ("getent", GETENT_STUB), ("ip", IP_STUB)):
            self._write(self.bin / name, body)
        (self.stub / "docker.ps").write_text("")

    @staticmethod
    def _write(path: Path, body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        path.chmod(0o755)

    def _build_clone(self) -> None:
        for relative in ("infra/deploy/first-install.sh", "infra/deploy/lib/first_install_env.py",
                         "infra/deploy/lib/first_install_api.py", "infra/deploy/lib/proxy-listeners.sh",
                         "infra/deploy/env/alpha.env.example", "infra/deploy/env/provider.env.example",
                         "infra/deploy/compose.server.yml", "infra/acme/client.pin", "infra/acme/compose.acme.yml"):
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        for name, body in (("deploy.sh", DEPLOY_STUB), ("verify-deployed.sh", VERIFY_STUB), ("local-agent.sh", AGENT_STUB),
                           ("reload-proxy.sh", RELOAD_STUB)):
            self._write(self.repo / "infra/deploy" / name, body)
        (self.repo / ".gitignore").write_text("infra/deploy/env/*.env\n")
        git = ["git", "-C", str(self.repo), "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "clone"], check=True)
        subprocess.run([*git, "remote", "add", "origin", "https://github.com/acme-co/audit-install.git"], check=True)

    def _set_acme_pin(self, value: str) -> None:
        """The clone's pin says ``value``, committed so the clone stays clean. Independent of what the real file holds."""
        pin = self.repo / "infra/acme/client.pin"
        text = pin.read_text()
        lines = [f"ACME_CLIENT_APK_VERSION={value}" if line.startswith("ACME_CLIENT_APK_VERSION=") else line
                 for line in text.splitlines()]
        changed = "\n".join(lines) + "\n"
        if changed != text:
            pin.write_text(changed)
            subprocess.run(["git", "-C", str(self.repo), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-am",
                            f"pin {value}"], check=True)

    def pin_acme_client(self) -> None:
        self._set_acme_pin("4.1.1-r0")

    def unpin_acme_client(self) -> None:
        self._set_acme_pin("UNRESOLVED")

    def plan(self, name: str, *lines: str) -> None:
        (self.stub / f"{name}.plan").write_text("".join(f"{line}\n" for line in lines))

    def env(self, **extra: str) -> dict[str, str]:
        environment = {
            "PATH": f"{self.bin}:/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": str(self.tmp), "LC_ALL": "C.UTF-8",
            "FIRST_INSTALL_TEST_MODE": "1",
            "FIRST_INSTALL_STATE_ROOT": str(self.state_root), "FIRST_INSTALL_LOG_DIR": str(self.log_dir),
            "FIRST_INSTALL_SECRET_DIR": str(self.secret_dir), "FIRST_INSTALL_COPY_DIR": str(self.copy_dir),
            "FIRST_INSTALL_STAGING": str(self.staging), "FIRST_INSTALL_PROC_NET": str(self.proc_net),
            "FIRST_INSTALL_MEMINFO": str(self.meminfo), "FIRST_INSTALL_HOST_KEY_PUB": str(self.host_key),
            "FIRST_INSTALL_AUTH_HOME": str(self.auth_home), "FIRST_INSTALL_POLL_SECONDS": "1",
            "FIRST_INSTALL_CERT_WAIT_SECONDS": "3", "FIRST_INSTALL_ADMIN_WAIT_SECONDS": "5",
            "STUB_STATE": str(self.stub), "STUB_DOCKER_ROOT": str(self.tmp),
        }
        environment.update(extra)
        return environment

    def run(self, *args: str, env: dict[str, str] | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(self.repo / "infra/deploy/first-install.sh"), *args], capture_output=True, text=True,
                              cwd=self.repo, env=env or self.env(), timeout=timeout)

    def calls(self) -> list[str]:
        path = self.stub / "calls.log"
        return path.read_text().splitlines() if path.exists() else []

    def alpha(self) -> dict[str, str]:
        return fie.parse_env((self.repo / "infra/deploy/env/alpha.env").read_text())

    def secrets(self) -> list[str]:
        values = self.alpha()
        found = [values[name] for name in ("POSTGRES_PASSWORD", "ALPHA_APP_DB_PASSWORD", "MINIO_ROOT_PASSWORD",
                                           "AUDITMANAGER_API_TOKEN")]
        provider = fie.parse_env((self.repo / "infra/deploy/env/provider.env").read_text())
        found.append(provider["AUDITMANAGER_SECRETS_KEYS"].partition(":")[2])
        return found

    def clean(self) -> bool:
        status = subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain", "--untracked-files=all"],
                                capture_output=True, text=True, check=True).stdout
        return status == ""


@pytest.fixture()
def rig(tmp_path: Path):
    return Rig(tmp_path)


@pytest.fixture()
def stack():
    state, stop = fake_stack.serve()
    yield state
    stop()


def _stops(result: subprocess.CompletedProcess[str]) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for m in (STOP_LINE.match(line) for line in result.stdout.splitlines()) if m]


def _args(stack, *extra: str) -> list[str]:
    return ["--email", EMAIL, "--http-port", str(stack.port), "--no-ci-key", *extra]


def _happy_plan(rig: Rig) -> None:
    rig.plan("deploy", f"3|{GATE}", "0|deploy.sh: second deploy ok")
    (rig.stub / "agent.status").write_text(SUBSCRIPTION)


# ---------------------------------------------------------------------------------------------- the output contract


def test_every_stop_is_one_line_for_a_code_in_the_table_and_a_non_zero_exit(rig: Rig) -> None:
    table = rig.run("--print-codes").stdout.splitlines()
    codes = [line.split("\t")[0] for line in table]
    assert len(codes) == len(set(codes)) and "usage" in codes and "unexpected" in codes
    for code in codes:
        driver = f'source "{rig.repo}/infra/deploy/first-install.sh"; stop {code} "alpha beta" "gamma" "delta" "epsilon"'
        done = subprocess.run(["bash", "-c", driver], capture_output=True, text=True, env=rig.env())
        assert done.returncode in (2, 10), (code, done.returncode)
        lines = done.stdout.splitlines()
        assert len(lines) == 1 and STOP_LINE.match(lines[0]) and STOP_LINE.match(lines[0]).group(1) == code, (code, done.stdout)


def test_the_table_text_is_the_whole_action_and_an_owner_line_says_so(rig: Rig) -> None:
    for line in rig.run("--print-codes").stdout.splitlines():
        code, text = line.split("\t")
        assert text.strip() and "|" not in text, code
        assert "ASK THE OWNER" in text or text.split()[0] in {"Fix", "Run", "Install", "Start", "Free", "Port", "Nothing", "The", "An"}, code


def test_print_codes_markdown_is_a_table_with_every_code(rig: Rig) -> None:
    plain = [line.split("\t")[0] for line in rig.run("--print-codes").stdout.splitlines()]
    markdown = rig.run("--print-codes", "--markdown").stdout.splitlines()
    assert markdown[0].startswith("| Code") and markdown[1].startswith("| ---")
    assert [re.match(r"\| `([a-z_]+)` \|", row).group(1) for row in markdown[2:]] == plain


def test_an_unknown_option_is_a_usage_stop_with_exit_2(rig: Rig) -> None:
    done = rig.run("--no-such-option")
    assert done.returncode == 2
    assert _stops(done)[-1][0] == "usage" and done.stdout.splitlines()[-1].startswith("STOP [usage]")


@pytest.mark.parametrize("args, code", [
    (["--instance", "Bad_Name"], "instance_invalid"),
    (["--domain", "not a name"], "domain_invalid"),
    (["--domain", "audit.example.org"], "domain_invalid"),
    (["--email", "not-an-address"], "email_invalid"),
    (["--norms-bundle", "/no/such/dir"], "norms_bundle_invalid"),
])
def test_bad_arguments_are_named_stops_before_anything_runs(rig: Rig, args: list[str], code: str) -> None:
    done = rig.run(*args)
    assert done.returncode == 10 and _stops(done)[0][0] == code, done.stdout
    assert not any(rig.state_root.iterdir()) and not (rig.repo / "infra/deploy/env/alpha.env").exists()


def test_a_bad_port_and_a_missing_value_are_usage_errors(rig: Rig) -> None:
    assert rig.run("--http-port", "80").returncode == 2
    assert rig.run("--email").returncode == 2
    assert rig.run("--resume-stage", "12").returncode == 2


def test_dry_run_prints_every_stage_and_changes_nothing(rig: Rig, stack) -> None:
    before = sorted(str(p) for p in rig.tmp.rglob("*"))
    done = rig.run(*_args(stack, "--domain", DOMAIN, "--norms-bundle", str(rig.tmp), "--dry-run"))
    assert done.returncode == 0, done.stdout
    for stage in range(1, 11):
        assert f"[{stage}/10]" in done.stdout
    assert "DRY RUN" in done.stdout and "STOP" not in done.stdout and "DONE:" not in done.stdout
    assert sorted(str(p) for p in rig.tmp.rglob("*")) == before
    assert not (rig.stub / "calls.log").exists()


def test_the_installer_help_lists_every_option_the_prompt_may_use(rig: Rig) -> None:
    done = rig.run("--help")
    assert done.returncode == 0
    for option in ("--email", "--domain", "--norms-bundle", "--instance", "--dry-run", "--resume-stage", "--skip-executors"):
        assert option in done.stdout


# --------------------------------------------------------------------------------------------------------- the run


def test_the_happy_path_installs_marks_and_prints_done_last(rig: Rig, stack) -> None:
    _happy_plan(rig)
    done = rig.run(*_args(stack))
    assert done.returncode == 0, done.stdout[-2500:]
    last = [line for line in done.stdout.splitlines() if line.strip()][-1]
    assert last.startswith("DONE: auditmanager is installed")
    assert not _stops(done)
    # the stages ran in order, and the second deploy came after the administrator was finished
    assert [line.split()[0] for line in rig.calls()] == ["deploy", "deploy", "local-agent", "local-agent", "verify"]
    assert stack.password != "password" and stack.profile_complete and stack.login == EMAIL
    # the files
    for name in ("alpha.env", "provider.env"):
        assert stat.S_IMODE((rig.repo / "infra/deploy/env" / name).stat().st_mode) == 0o600
    password_file = rig.secret_dir / "auditmanager-admin-password.txt"
    assert stat.S_IMODE(password_file.stat().st_mode) == 0o600
    marker = rig.state_root / "auditmanager" / "first-install.done"
    text = marker.read_text()
    head = subprocess.run(["git", "-C", str(rig.repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert f"sha={head}" in text and "date=" in text and "stage_8_verify=ok" in text and "stage_5_norms=skipped" in text
    assert (rig.log_dir / "auditmanager-first-install.log").exists()
    # the clone is as clean as it was: only the two ignored files were added
    assert rig.clean()


def test_no_secret_reaches_the_output_or_the_log(rig: Rig, stack) -> None:
    _happy_plan(rig)
    done = rig.run("--email", EMAIL, "--http-port", str(stack.port))
    assert done.returncode == 0, done.stdout[-2500:]
    log = (rig.log_dir / "auditmanager-first-install.log").read_text()
    private_key = (rig.secret_dir / "auditmanager-deploy-key").read_text()
    body = next(line for line in private_key.splitlines() if line and not line.startswith("-----"))
    for secret in [*rig.secrets(), stack.password, body]:
        assert secret not in done.stdout + done.stderr + log
    assert "-----BEGIN" not in done.stdout + log
    assert str(rig.secret_dir / "auditmanager-deploy-key") in done.stdout


def test_a_finished_installation_refuses_a_second_run_and_resume_stage_is_the_way_past(rig: Rig, stack) -> None:
    _happy_plan(rig)
    assert rig.run(*_args(stack)).returncode == 0
    again = rig.run(*_args(stack))
    assert again.returncode == 10
    assert _stops(again)[0][0] == "already_installed" and len(again.stdout.strip().splitlines()) == 1
    verifies = [c for c in rig.calls() if c.startswith("verify")]
    redo = rig.run(*_args(stack, "--resume-stage", "8"))
    assert redo.returncode == 0, redo.stdout[-1500:]
    assert len([c for c in rig.calls() if c.startswith("verify")]) == len(verifies) + 1
    assert "done before: skipped" in redo.stdout


def test_a_failed_deploy_stops_and_the_rerun_continues_without_touching_the_environment(rig: Rig, stack) -> None:
    rig.plan("deploy", "1|build failed: network")
    first = rig.run(*_args(stack, "--skip-executors"))
    assert first.returncode == 10 and _stops(first)[-1][0] == "deploy_failed", first.stdout[-1500:]
    env_bytes = {n: (rig.repo / "infra/deploy/env" / n).read_bytes() for n in ("alpha.env", "provider.env")}
    rig.plan("deploy", f"3|{GATE}", "0|ok")
    second = rig.run(*_args(stack, "--skip-executors"))
    assert second.returncode == 0, second.stdout[-1500:]
    assert {n: (rig.repo / "infra/deploy/env" / n).read_bytes() for n in env_bytes} == env_bytes
    assert "done before: skipped" not in second.stdout.split("[3/10]")[0]  # the environment is checked again, never skipped
    assert "alpha.env already exists: kept as it is" in second.stdout


def test_the_expected_default_credential_refusal_is_not_a_stop_but_any_other_refusal_is(rig: Rig, stack) -> None:
    rig.plan("deploy", "3|deploy.sh: REFUSED: something nobody expected\\n  detail")
    done = rig.run(*_args(stack, "--skip-executors"))
    assert _stops(done)[-1][0] == "deploy_refused" and "something nobody expected" in done.stdout.splitlines()[-1]


@pytest.mark.parametrize("message, code", [
    ("deploy.sh: REFUSED: public port 80 is already in use, and not by auditmanager's proxy.", "public_port_busy"),
    ("deploy.sh: REFUSED: port 31500 is already in use, and not by auditmanager.", "http_port_busy"),
    ("deploy.sh: REFUSED: [build_overload] the host is overloaded", "host_overloaded"),
    ("deploy.sh: REFUSED: the ACME client is not pinned: x", "acme_unpinned"),
])
def test_known_deploy_refusals_map_to_their_own_stops(rig: Rig, stack, message: str, code: str) -> None:
    rig.plan("deploy", f"3|{message}")
    assert _stops(rig.run(*_args(stack)))[-1][0] == code


def test_a_gate_that_survives_the_password_change_is_an_admin_stop(rig: Rig, stack) -> None:
    rig.plan("deploy", f"3|{GATE}", f"3|{GATE}")
    done = rig.run(*_args(stack))
    assert _stops(done)[-1][0] == "admin_failed"


def test_a_foreign_administrator_password_is_a_stop_that_names_the_file_and_not_the_password(rig: Rig, stack) -> None:
    stack.password = "somebody-elses-password-0123456789"
    rig.plan("deploy", f"3|{GATE}")
    done = rig.run(*_args(stack))
    code, text = _stops(done)[-1]
    assert code == "admin_unknown_password" and "auditmanager-admin-password.txt" in text
    assert "somebody-elses" not in done.stdout


def test_verification_failure_is_a_stop_with_the_exit_status(rig: Rig, stack) -> None:
    _happy_plan(rig)
    rig.plan("verify", "6|the stack is not this tree")
    done = rig.run(*_args(stack))
    code, text = _stops(done)[-1]
    assert code == "verify_failed" and "status 6" in text
    assert not (rig.state_root / "auditmanager" / "first-install.done").exists()


# ---------------------------------------------------------------------------------------------------- the executors


def test_no_subscription_is_a_stop_and_skip_executors_is_the_owners_way_past_it(rig: Rig, stack) -> None:
    rig.plan("deploy", f"3|{GATE}", "0|ok")
    (rig.stub / "agent.status").write_text("  claude_code installed access=none auth=none\n")
    done = rig.run(*_args(stack))
    assert _stops(done)[-1][0] == "executors_login_needed" and "--skip-executors" in done.stdout.splitlines()[-1]
    rig.plan("deploy")
    skipped = rig.run(*_args(stack, "--skip-executors"))
    assert skipped.returncode == 0, skipped.stdout[-1500:]
    assert "skipped: --skip-executors" in skipped.stdout


def test_a_subscription_that_cannot_be_connected_is_a_stop(rig: Rig, stack) -> None:
    _happy_plan(rig)
    (rig.stub / "agent.connect").write_text("4")
    done = rig.run(*_args(stack))
    assert _stops(done)[-1][0] == "executors_not_connected"


# ---------------------------------------------------------------------------------------------------- the preflight


def test_a_dirty_clone_is_refused_before_anything_is_written(rig: Rig, stack) -> None:
    (rig.repo / "scratch.txt").write_text("x")
    done = rig.run(*_args(stack))
    assert _stops(done)[-1][0] == "checkout_dirty" and "scratch.txt" in done.stdout
    assert not (rig.repo / "infra/deploy/env/alpha.env").exists()


def test_a_clone_without_origin_is_refused(rig: Rig, stack) -> None:
    subprocess.run(["git", "-C", str(rig.repo), "remote", "remove", "origin"], check=True)
    assert _stops(rig.run(*_args(stack)))[-1][0] == "no_origin"


def test_too_little_disk_and_too_little_memory_are_stops_with_the_figures(rig: Rig, stack) -> None:
    low_disk = rig.run(*_args(stack), env=rig.env(STUB_DF_BYTES=str(3 * 1024**3)))
    code, text = _stops(low_disk)[-1]
    assert code == "disk_low" and "3 GiB" in text and "8 GiB" in text
    rig.meminfo.write_text("MemTotal:  2000000 kB\nMemAvailable:  500000 kB\n")
    low_ram = rig.run(*_args(stack))
    assert _stops(low_ram)[-1][0] == "ram_low"


def test_a_small_server_is_warned_not_stopped(rig: Rig, stack) -> None:
    rig.meminfo.write_text("MemTotal:  3000000 kB\nMemAvailable:  2500000 kB\n")
    _happy_plan(rig)
    done = rig.run(*_args(stack))
    assert done.returncode == 0 and "WARNING: this server has" in done.stdout


def test_docker_down_and_an_old_compose_are_stops(rig: Rig, stack) -> None:
    (rig.stub / "docker.down").write_text("")
    assert _stops(rig.run(*_args(stack)))[-1][0] == "docker_down"
    (rig.stub / "docker.down").unlink()
    (rig.stub / "compose.version").write_text("1.29.2")
    assert _stops(rig.run(*_args(stack)))[-1][0] == "docker_old"


def test_a_busy_application_port_is_a_stop_only_before_the_environment_exists(rig: Rig, stack) -> None:
    (rig.proc_net / "tcp").write_text("  sl  local_address rem_address   st\n   0: 00000000:%04X 00000000:0000 0A 0\n" % stack.port)
    assert _stops(rig.run(*_args(stack)))[-1][0] == "http_port_busy"
    assert not (rig.repo / "infra/deploy/env/alpha.env").exists()


def test_the_email_is_required_until_the_administrator_is_finished(rig: Rig, stack) -> None:
    done = rig.run("--http-port", str(stack.port))
    assert _stops(done)[-1][0] == "email_required"


def test_an_existing_environment_decides_the_instance_and_a_wrong_instance_is_refused(rig: Rig, stack) -> None:
    rig.plan("deploy", "1|stop here")
    rig.run(*_args(stack, "--instance", "first-name"))
    assert rig.alpha()["ALPHA_INSTANCE"] == "first-name"
    again = rig.run(*_args(stack, "--instance", "other-name"))
    assert _stops(again)[-1][0] == "instance_mismatch" and "first-name" in again.stdout
    plain = rig.run(*_args(stack))
    assert "instance first-name" in plain.stdout


def test_an_existing_but_broken_environment_is_a_stop_that_names_the_variable_and_changes_nothing(rig: Rig, stack) -> None:
    rig.plan("deploy", "1|stop here")
    rig.run(*_args(stack))
    alpha = rig.repo / "infra/deploy/env/alpha.env"
    broken = fie.set_value(alpha.read_text(), "AUDITMANAGER_API_TOKEN", "change-me-this-example-token-authorizes-nothing")
    alpha.write_text(broken)
    done = rig.run(*_args(stack))
    code, text = _stops(done)[-1]
    assert code == "env_invalid" and "AUDITMANAGER_API_TOKEN" in text and "authorizes-nothing" not in text
    assert alpha.read_text() == broken


def test_a_loose_mode_is_repaired_not_refused(rig: Rig, stack) -> None:
    rig.plan("deploy", "1|stop here")
    rig.run(*_args(stack))
    (rig.repo / "infra/deploy/env/alpha.env").chmod(0o644)
    rig.plan("deploy", f"3|{GATE}", "0|ok")
    (rig.stub / "agent.status").write_text(SUBSCRIPTION)
    done = rig.run(*_args(stack))
    assert "mode set to 600" in done.stdout and done.returncode == 0, done.stdout[-1500:]
    assert stat.S_IMODE((rig.repo / "infra/deploy/env/alpha.env").stat().st_mode) == 0o600


def test_set_goes_into_a_new_environment_only(rig: Rig, stack) -> None:
    rig.plan("deploy", "1|stop here")
    rig.run(*_args(stack, "--set", "ALPHA_NORM_EMBED=yes", "--set", "ALPHA_MEM_LIMIT_NORM_EMBED=1200m"))
    assert rig.alpha()["ALPHA_NORM_EMBED"] == "yes"
    bad = rig.run(*_args(stack, "--set", "POSTGRES_PASSWORD=weak"))
    assert bad.returncode == 10 and rig.alpha()["POSTGRES_PASSWORD"] != "weak"


# ------------------------------------------------------------------------------------------------------------ HTTPS


def _https_rig(rig: Rig, stack, *, a_record: str | None = "203.0.113.7") -> list[str]:
    rig.pin_acme_client()
    if a_record is not None:
        (rig.stub / f"dns-{DOMAIN}").write_text(a_record + "\n")
    rig.plan("deploy", f"3|{GATE}", "0|ok", "0|staging deployed", "0|real deployed", "0|published\\ndeploy.sh: published on port 443 (the credential gate is clean).")
    (rig.stub / "agent.status").write_text(SUBSCRIPTION)
    return _args(stack, "--domain", DOMAIN)


def test_https_runs_staging_then_real_then_publishes_in_that_order(rig: Rig, stack) -> None:
    arguments = _https_rig(rig, stack)
    rig.plan("verify", "7|served-certificate: NOT SERVED", "0|ok", "0|ok", "0|ok")
    done = rig.run(*arguments)
    assert done.returncode == 0, done.stdout[-2500:]
    deploys = [c for c in rig.calls() if c.startswith("deploy")]
    assert deploys == [
        "deploy cert= staging= publish= email=",
        "deploy cert= staging= publish= email=",
        f"deploy cert={DOMAIN} staging=yes publish= email={EMAIL}",
        f"deploy cert={DOMAIN} staging=no publish= email={EMAIL}",
        f"deploy cert={DOMAIN} staging=no publish=yes email={EMAIL}",
    ]
    verifies = [c for c in rig.calls() if c.startswith("verify")]
    assert verifies[0].endswith("--acme-rehearsal") and verifies[1].endswith("--acme-rehearsal")
    assert not verifies[2].endswith("--acme-rehearsal")
    assert f"Open https://{DOMAIN}." in done.stdout
    assert f"variable DEPLOY_HOST        {DOMAIN}" in done.stdout


def test_https_waits_for_the_certificate_and_stops_with_the_log_command_when_it_never_comes(rig: Rig, stack) -> None:
    arguments = _https_rig(rig, stack)
    rig.plan("verify", *["7|served-certificate: NOT SERVED"] * 20)
    done = rig.run(*arguments)
    code, text = _stops(done)[-1]
    assert code == "acme_staging_failed" and "logs acme" in text and "compose.acme.yml" in text


def test_https_rerun_skips_the_stages_it_finished(rig: Rig, stack) -> None:
    arguments = _https_rig(rig, stack)
    rig.plan("verify", "0|ok", "7|real certificate missing", "7|x", "7|x", "7|x", "7|x", "7|x")
    first = rig.run(*arguments)
    assert _stops(first)[-1][0] == "acme_real_failed"
    rig.plan("deploy", "0|real deployed", "0|published\\ndeploy.sh: published on port 443 (the credential gate is clean).")
    rig.plan("verify", "0|ok", "0|ok")
    second = rig.run(*arguments)
    assert second.returncode == 0, second.stdout[-2000:]
    staging_deploys = [c for c in rig.calls() if "staging=yes" in c]
    assert len(staging_deploys) == 1


def test_dns_missing_and_mismatch_are_stops_that_say_what_to_create(rig: Rig, stack) -> None:
    missing = _https_rig(rig, stack, a_record=None)
    done = rig.run(*missing)
    code, text = _stops(done)[-1]
    assert code == "dns_missing" and DOMAIN in text and "A record" in text
    (rig.stub / f"dns-{DOMAIN}").write_text("198.51.100.9\n")
    rig.plan("deploy")
    done = rig.run(*missing)
    code, text = _stops(done)[-1]
    assert code == "dns_mismatch" and "198.51.100.9" in text and "203.0.113.7" in text


def test_an_unpinned_acme_client_is_a_stop_before_the_environment_is_touched(rig: Rig, stack) -> None:
    rig.unpin_acme_client()
    (rig.stub / f"dns-{DOMAIN}").write_text("203.0.113.7\n")
    rig.plan("deploy", f"3|{GATE}", "0|ok")
    (rig.stub / "agent.status").write_text(SUBSCRIPTION)
    done = rig.run(*_args(stack, "--domain", DOMAIN))
    assert _stops(done)[-1][0] == "acme_unpinned"
    assert "ALPHA_CERT_NAME" not in "\n".join(line for line in (rig.repo / "infra/deploy/env/alpha.env").read_text().splitlines()
                                              if line.startswith("ALPHA_CERT_NAME"))


def test_a_public_port_held_by_another_program_is_a_stop_but_our_own_proxy_is_not(rig: Rig, stack) -> None:
    rig.pin_acme_client()
    (rig.proc_net / "tcp").write_text("  sl  local_address rem_address   st\n   0: 00000000:0050 00000000:0000 0A 0\n")
    arguments = ["--email", EMAIL, "--http-port", str(stack.port), "--no-ci-key", "--domain", DOMAIN]
    held = rig.run(*arguments)
    code, text = _stops(held)[-1]
    assert code == "public_port_busy" and "80" in text
    (rig.stub / "docker.ps").write_text("auditmanager-proxy-1 0.0.0.0:80->80/tcp, 127.0.0.1:31500->8080/tcp\n")
    (rig.stub / f"dns-{DOMAIN}").write_text("203.0.113.7\n")
    rig.plan("deploy", "1|stop at the deploy")
    ours = rig.run(*arguments)
    assert _stops(ours)[-1][0] == "deploy_failed"


# --------------------------------------------------------------------------------------------------- the GitHub block


def test_the_github_block_has_the_values_the_workflow_reads_and_no_private_key(rig: Rig, stack) -> None:
    _happy_plan(rig)
    done = rig.run("--email", EMAIL, "--http-port", str(stack.port))
    assert done.returncode == 0, done.stdout[-1500:]
    out = done.stdout
    assert "variable DEPLOY_HOST" in out and "variable DEPLOY_PATH        " + str(rig.repo) in out
    assert re.search(r"variable DEPLOY_KNOWN_HOSTS \S+ ssh-ed25519 [A-Za-z0-9+/=]+", out)
    assert "SHA256:" in out and "acme-co/audit-install" in out
    assert "secret   VPS_USER           root" in out and "sudoers" not in out
    key_file = rig.secret_dir / "auditmanager-deploy-key"
    assert stat.S_IMODE(key_file.stat().st_mode) == 0o600 and str(key_file) in out
    public = (rig.secret_dir / "auditmanager-deploy-key.pub").read_text().split()[1]
    assert public in (rig.auth_home / ".ssh" / "authorized_keys").read_text()
    assert stat.S_IMODE((rig.auth_home / ".ssh" / "authorized_keys").stat().st_mode) == 0o600


def test_a_rerun_keeps_the_deploy_key_and_does_not_authorize_it_twice(rig: Rig, stack) -> None:
    _happy_plan(rig)
    assert rig.run("--email", EMAIL, "--http-port", str(stack.port)).returncode == 0
    key_before = (rig.secret_dir / "auditmanager-deploy-key").read_bytes()
    assert rig.run("--email", EMAIL, "--http-port", str(stack.port), "--resume-stage", "9").returncode == 0
    assert (rig.secret_dir / "auditmanager-deploy-key").read_bytes() == key_before
    authorized = (rig.auth_home / ".ssh" / "authorized_keys").read_text().splitlines()
    assert len(authorized) == 1


def test_a_non_root_deploy_user_gets_the_sudoers_line(rig: Rig) -> None:
    driver = (f'source "{rig.repo}/infra/deploy/first-install.sh"; OPT_DEPLOY_USER=nobody; OPT_NO_CI_KEY=yes; '
              f'REPO="{rig.repo}"; INSTANCE=auditmanager; OPT_DOMAIN=; stage_github')
    done = subprocess.run(["bash", "-c", driver], capture_output=True, text=True, env=rig.env())
    assert done.returncode == 0, done.stderr
    assert f"nobody ALL=(root) NOPASSWD: {rig.repo}/infra/deploy/local-agent.sh" in done.stdout
    assert "secret   VPS_USER           nobody" in done.stdout


# --------------------------------------------------------------------------------------------------- the script itself


def test_the_script_is_shellcheck_clean() -> None:
    if shutil.which("shellcheck") is None:
        pytest.skip("shellcheck is not installed")
    done = subprocess.run(["shellcheck", "-x", str(SCRIPT)], capture_output=True, text=True, cwd=ROOT)
    assert done.returncode == 0, done.stdout


def test_the_script_never_deletes_resets_or_cleans() -> None:
    text = SCRIPT.read_text()
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    for forbidden in ("rm -rf", "rm -f", "git clean", "git reset", "git checkout", "down --volumes", "--volumes", "docker volume",
                      "docker system prune", "docker rm", "kill ", "pkill", "git push"):
        assert forbidden not in code, forbidden


def test_the_script_writes_nothing_in_the_clone_but_the_two_environment_files() -> None:
    """Every path the script writes is under a state, secret, log, copy or staging directory, or is the helper's pair of
    environment files; `git status` of the clone after a run is the proof (the happy-path test asserts it clean)."""
    code = "\n".join(line for line in SCRIPT.read_text().splitlines() if not line.lstrip().startswith("#"))
    assert "> \"$REPO" not in code and ">> \"$REPO" not in code and "tee \"$REPO" not in code


def test_the_on_host_tar_is_the_tar_push_bundle_sends() -> None:
    def tar_line(path: Path, marker: str) -> str:
        text = path.read_text()
        start = text.index(marker)
        body = text[start:text.index("}", start)]
        return re.sub(r"\s+", " ", " ".join(line for line in body.splitlines() if "tar --create" in line or "--hard-dereference" in line)
                      .replace("\\", " ")).strip()

    assert tar_line(SCRIPT, "bundle_tar()") .replace('"$1"', "X").replace('"$2"', "Y") == \
        tar_line(DEPLOY / "push-bundle.sh", "bundle_tar()").replace('"$PARENT"', "X").replace('"$KEY"', "Y")


# ------------------------------------------------------------------------------------- the prompt for a simple agent


def _prompt_table() -> str:
    text = PROMPT.read_text()
    begin, end = "<!-- STOP-CODES:BEGIN -->\n", "<!-- STOP-CODES:END -->"
    assert begin in text and end in text, "the prompt lost its STOP-CODES markers"
    return text[text.index(begin) + len(begin):text.index(end)]


def test_the_prompt_carries_the_scripts_stop_table_verbatim(rig: Rig) -> None:
    """The one table is in the script; the prompt's copy is generated from it. Regenerate with:
    infra/deploy/first-install.sh --print-codes --markdown, between the two markers of the prompt."""
    assert _prompt_table() == rig.run("--print-codes", "--markdown").stdout


def test_every_code_the_script_can_print_is_in_the_table() -> None:
    table = {line.split("\t")[0] for line in subprocess.run(
        [str(SCRIPT), "--print-codes"], capture_output=True, text=True, check=True).stdout.splitlines()}
    # Comment lines and the dry run's sentences (one says "; stop with a printed instruction") are not call sites.
    lines = [line for line in SCRIPT.read_text().splitlines() if not line.lstrip().startswith("#") and 'echo "' not in line]
    code = "\n".join(lines)
    code = code[:code.index('CODES_TABLE="$(cat')] + code[code.index("\nTABLE\n"):]
    used = set(re.findall(r"(?:^|[;&|{)]|\bthen|\belse|\|\|)\s*stop ([a-z_]+)", code, re.M))
    assert used <= table, f"stop codes used but not in the table: {sorted(used - table)}"
    unused = table - used - {"unexpected"}
    assert not unused, f"codes in the table that no stop uses: {sorted(unused)}"


def test_the_prompt_is_short_and_carries_the_rules_a_simple_agent_needs() -> None:
    text = PROMPT.read_text()
    prose = text[:text.index("<!-- STOP-CODES:BEGIN -->")]
    assert len(prose.strip().splitlines()) <= 50
    for must in ("sudo infra/deploy/first-install.sh", "STOP [code]", "DONE:", "ASK THE OWNER", "last 30 lines",
                 "Never kill a process by name", "Never push", "main", "Never edit", "password", "run the same command again"):
        assert must in prose, must
    for option in ("--email", "--domain", "--norms-bundle", "--skip-executors", "--resume-stage", "--set"):
        assert option in prose, option
    # it names no file path of a secret except by pattern, and holds no value that looks like one
    assert not re.search(r"[A-Za-z0-9_-]{40,}", prose)


def test_the_readmes_carry_the_two_commands_and_the_prompt_pointer() -> None:
    deploy_readme = (DEPLOY / "README.md").read_text()
    head = "\n".join(deploy_readme.splitlines()[:8])
    assert "git clone" in head and "first-install.sh" in head and "FIRST-INSTALL-PROMPT.md" in head
    assert "first-install.sh" in (ROOT / "README.md").read_text() and "FIRST-INSTALL-PROMPT.md" in (ROOT / "README.md").read_text()


def test_a_second_run_while_the_first_still_works_is_refused_not_started(rig: Rig, stack) -> None:
    """An agent whose tool timed out may start the command again while the first process lives on."""
    import fcntl

    state = rig.state_root / "auditmanager"
    state.mkdir(parents=True)
    with open(state / "first-install.lock", "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        done = rig.run(*_args(stack))
    assert done.returncode == 10 and _stops(done)[-1][0] == "already_running", done.stdout[-800:]
    assert "first-install.log" in done.stdout and not (rig.repo / "infra/deploy/env/alpha.env").exists()
    rig.plan("deploy", "1|stop here")
    assert _stops(rig.run(*_args(stack)))[-1][0] == "deploy_failed"  # the lock was released when the holder let go
