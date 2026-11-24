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
echo "docker $* [profiles=${COMPOSE_PROFILES:-}]" >> "$STUB_STATE/docker.log"
case "$1" in
    info)
        if [ "${2:-}" = --format ]; then echo "$STUB_DOCKER_ROOT"; exit 0; fi
        [ ! -f "$STUB_STATE/docker.down" ] || exit 1
        exit 0 ;;
    version) cat "$STUB_STATE/docker.version" 2>/dev/null || echo 27.3.1; exit 0 ;;
    volume) [ -f "$STUB_STATE/volume.exists" ]; exit $? ;;
    inspect) echo running; exit 0 ;;
    stats) exit 0 ;;
    ps) cat "$STUB_STATE/docker.ps" 2>/dev/null || true; exit 0 ;;
    compose)
        if [ "${2:-}" = version ]; then cat "$STUB_STATE/compose.version" 2>/dev/null || echo v2.29.1; exit 0; fi
        case "$*" in
            *semantic_check*)
                echo "semantic_check $*" >> "$STUB_STATE/semantic.log"
                if [ -f "$STUB_STATE/semantic.low_mem" ]; then
                    original="$(cat "$FIRST_INSTALL_MEMINFO")"
                    printf 'MemTotal:  8000000 kB\nMemAvailable:  300000 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n' > "$FIRST_INSTALL_MEMINFO"
                    sleep 0.5
                    printf '%s\n' "$original" > "$FIRST_INSTALL_MEMINFO"
                fi
                if [ -f "$STUB_STATE/semantic.swap_grows" ]; then
                    printf 'MemTotal:  8000000 kB\nMemAvailable:  6000000 kB\nSwapTotal: 2097152 kB\nSwapFree: 1000000 kB\n' > "$FIRST_INSTALL_MEMINFO"
                fi
                cat "$STUB_STATE/semantic.out" 2>/dev/null || true
                exit "$(cat "$STUB_STATE/semantic.exit" 2>/dev/null || echo 0)" ;;
            *"up -d"*worker*)
                [ ! -f "$STUB_STATE/worker.fail" ] || { echo "worker could not start (stub)" >&2; exit 1; }
                exit 0 ;;
            *"ps --quiet worker"*) echo cid-worker; exit 0 ;;
            *"ps --quiet norm-embed"*) cat "$STUB_STATE/norm-embed.ps" 2>/dev/null || true; exit 0 ;;
            *logs*acme*) cat "$STUB_STATE/acme.log" 2>/dev/null || true; exit 0 ;;
        esac
        exit 0 ;;
esac
exit 0
"""
APT_STUB = r"""#!/usr/bin/env bash
echo "apt-get $*" >> "$STUB_STATE/apt.log"
[ ! -f "$STUB_STATE/apt.fail" ] || { echo "E: Unable to locate package (stub)" >&2; exit 100; }
for word in "$@"; do
    case "$word" in
        docker-compose-plugin) echo v2.29.1 > "$STUB_STATE/compose.version" ;;
        docker-ce) echo 27.3.1 > "$STUB_STATE/docker.version"; echo v2.29.1 > "$STUB_STATE/compose.version" ;;
    esac
done
exit 0
"""
SYSTEMCTL_STUB = r"""#!/usr/bin/env bash
echo "systemctl $*" >> "$STUB_STATE/systemctl.log"
# STUB_SYSTEMCTL_FAIL=<words>: a call whose arguments contain these words fails.
if [ -n "${STUB_SYSTEMCTL_FAIL:-}" ]; then case "$*" in *"$STUB_SYSTEMCTL_FAIL"*) exit 1 ;; esac; fi
if [ -f "$STUB_STATE/systemctl.fixes" ]; then rm -f "$STUB_STATE/docker.down"; fi
exit 0
"""
GPG_STUB = r"""#!/usr/bin/env bash
printf 'pub:-:4096:1:8D81803C0EBFCD88:1487788586:::-:::scESCA::::::23::0:\nfpr:::::::::%s:\n' "${STUB_GPG_FPR:-9DC858229FC7DD38854AE2D88D81803C0EBFCD88}"
"""
DPKG_STUB = '#!/usr/bin/env bash\necho amd64\n'
CURL_STUB = r"""#!/usr/bin/env bash
echo "curl $*" >> "$STUB_STATE/curl.log"
output=""
while [ "$#" -gt 0 ]; do case "$1" in -o) output="$2"; shift 2 ;; *) shift ;; esac; done
[ -z "$output" ] || echo "stub key" > "$output"
exit 0
"""
GIT_STUB = r"""#!/usr/bin/env bash
if [ -f "$STUB_STATE/git.clone_error" ]; then
    for word in "$@"; do
        if [ "$word" = clone ]; then cat "$STUB_STATE/git.clone_error" >&2; exit 128; fi
    done
fi
exec /usr/bin/git "$@"
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
[ ! -f "$state/deploy.setmem" ] || cp "$state/deploy.setmem" "$FIRST_INSTALL_MEMINFO"
# STUB_ON_DEPLOY: a command run from inside the install (the installer's locks are inherited), its output and status recorded
if [ -n "${STUB_ON_DEPLOY:-}" ]; then
    bash -c "$STUB_ON_DEPLOY" > "$state/on-deploy.out" 2>&1 && echo 0 > "$state/on-deploy.rc" || echo $? > "$state/on-deploy.rc"
fi
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
SEMANTIC_PASS = ('{"min_mean_inner_product": 0.97, "min_self_recall_at_10": 0.9, "mean_inner_product": 0.9812, "p05_inner_product": 0.95, '
                 '"self_recall_at_10": 0.934, "verdict": "PASS", "windows": 500}\n')
SEMANTIC_FAIL = SEMANTIC_PASS.replace('"mean_inner_product": 0.9812', '"mean_inner_product": 0.9311').replace('"PASS"', '"FAIL"')


class Rig:
    """One throw-away clone, its stubs, and the directories the script writes to."""

    def __init__(self, tmp_path: Path, *, as_deploy: bool = True) -> None:
        """`as_deploy`: the script is started in the deploy clone itself (`<root>/srv/auditmanager`, what an installation
        looks like once the installer has made it). With False it is started in a separate working copy, `<tmp>/dev`, and the
        deploy clone does not exist yet."""
        self.tmp = tmp_path
        self.as_deploy = as_deploy
        self.deploy_root = tmp_path / "srv"
        self.deploy = self.deploy_root / "auditmanager"
        self.dev = tmp_path / "dev"
        self.origin = tmp_path / "remote" / "acme-co" / "audit-install.git"
        self.repo = self.deploy if as_deploy else self.dev
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
        self.systemd_dir = tmp_path / "etc-systemd-system"
        self.host_key = tmp_path / "ssh_host_ed25519_key.pub"
        for directory in (self.bin, self.stub, self.state_root, self.log_dir, self.secret_dir, self.auth_home, self.proc_net):
            directory.mkdir(parents=True)
        self.meminfo.write_text("MemTotal:  8000000 kB\nMemAvailable:  6000000 kB\n")
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(tmp_path / "hostkey")], check=True)
        shutil.copy(tmp_path / "hostkey.pub", self.host_key)
        self._build_clone()
        for name, body in (("docker", DOCKER_STUB), ("df", DF_STUB), ("getent", GETENT_STUB), ("ip", IP_STUB), ("apt-get", APT_STUB),
                           ("systemctl", SYSTEMCTL_STUB), ("gpg", GPG_STUB), ("dpkg", DPKG_STUB), ("curl", CURL_STUB), ("git", GIT_STUB)):
            self._write(self.bin / name, body)
        (self.stub / "docker.ps").write_text("")
        (self.stub / "semantic.out").write_text(SEMANTIC_PASS)
        self.os_release = tmp_path / "os-release"
        self.os_release.write_text('ID=ubuntu\nVERSION_CODENAME=noble\n')
        self.keyrings = tmp_path / "keyrings"
        self.apt_sources = tmp_path / "apt-sources"
        self.apt_sources.mkdir()

    @staticmethod
    def _write(path: Path, body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        path.chmod(0o755)

    def _build_clone(self) -> None:
        seed = self.tmp / "seed"
        for relative in ("infra/deploy/first-install.sh", "infra/deploy/lib/first_install_env.py",
                         "infra/deploy/lib/first_install_api.py", "infra/deploy/lib/proxy-listeners.sh",
                         "infra/deploy/lib/forced-command.sh", "infra/deploy/receive-bundle.sh", "infra/deploy/copy-serve.sh",
                         "infra/deploy/push-bundle.sh", "infra/deploy/deploy-local.sh",
                         "infra/deploy/systemd/auditmanager-deploy-local.service", "infra/deploy/systemd/auditmanager-deploy-local.timer",
                         "infra/deploy/env/alpha.env.example", "infra/deploy/env/provider.env.example",
                         "infra/deploy/compose.server.yml", "infra/acme/client.pin", "infra/acme/compose.acme.yml"):
            target = seed / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        for name, body in (("deploy.sh", DEPLOY_STUB), ("verify-deployed.sh", VERIFY_STUB), ("local-agent.sh", AGENT_STUB),
                           ("reload-proxy.sh", RELOAD_STUB)):
            self._write(seed / "infra/deploy" / name, body)
        (seed / ".gitignore").write_text("infra/deploy/env/*.env\n")
        git = ["git", "-C", str(seed), "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "seed"], check=True)
        self.origin.parent.mkdir(parents=True)
        subprocess.run(["git", "clone", "-q", "--bare", str(seed), str(self.origin)], check=True)
        self.repo.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.repo)], check=True)

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

    def write_lock(self, text: str | None = None, *, tar_bytes: int = 5_400_000_000, parts: int = 3, part_bytes: int = 1_300_000_000) -> None:
        """`infra/norms/bundle-release.lock` in the clone, committed so that the clone stays clean."""
        digest = "7" * 64
        key = f"2026-07-23..2026-08-20+17d+121r.0a1bafe103ff+{digest}"
        lines = ["lock_version=1", "repo=acme-co/audit-install", "tag=norms-0a1bafe103ff-77777777", f"bundle={key}",
                 f"bundle_sums_sha256={digest}", f"tar_bytes={tar_bytes}", f"total_bytes={parts * part_bytes}", f"part_count={parts}"]
        lines += [f"part=norms-0a1bafe103ff-77777777.tar.zst.{n:03d} {part_bytes} {'ab' * 32} {1000 + n}" for n in range(parts)]
        path = self.repo / "infra/norms/bundle-release.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text if text is not None else "\n".join(lines) + "\n")
        git = ["git", "-C", str(self.repo), "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run([*git, "add", "-f", "infra/norms/bundle-release.lock"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "the lock"], check=True)

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
            "FIRST_INSTALL_DEPLOY_ROOT": str(self.deploy_root), "FIRST_INSTALL_OS_RELEASE": str(self.os_release),
            "FIRST_INSTALL_KEYRINGS_DIR": str(self.keyrings), "FIRST_INSTALL_APT_SOURCES_DIR": str(self.apt_sources),
            "FIRST_INSTALL_SAMPLE_SECONDS": "0.1", "FIRST_INSTALL_DOCKER_WAIT_SECONDS": "2",
            "FIRST_INSTALL_RELEASE_BASE": "http://127.0.0.1:9", "FIRST_INSTALL_RELEASE_API_BASE": "http://127.0.0.1:9",
            "FIRST_INSTALL_RELEASE_RETRIES": "1", "FIRST_INSTALL_RELEASE_RETRY_DELAY": "0",
            "FIRST_INSTALL_SYSTEMD_DIR": str(self.systemd_dir),
            "STUB_STATE": str(self.stub), "STUB_DOCKER_ROOT": str(self.tmp),
        }
        environment.update(extra)
        return environment

    def run(self, *args: str, env: dict[str, str] | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
        quiet = {"--print-codes", "--help", "-h", "--deploy-path"}
        if self.as_deploy and not quiet & set(args):
            args = (*args, "--deploy-path", str(self.repo))
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
def devrig(tmp_path: Path):
    """The installer started in the owner's working copy; the deploy clone does not exist yet."""
    return Rig(tmp_path, as_deploy=False)


@pytest.fixture()
def stack():
    state, stop = fake_stack.serve()
    yield state
    stop()


def _stops(result: subprocess.CompletedProcess[str]) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for m in (STOP_LINE.match(line) for line in result.stdout.splitlines()) if m]


def _args(stack, *extra: str) -> list[str]:
    return ["--email", EMAIL, "--http-port", str(stack.port), "--no-ci-key", "--deploy-mode", "github", *extra]


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


#: The codes whose action begins `ASK THE OWNER`. Each is a fact only the owner holds: an e-mail address, the domain, a record at the
#: registrar, the provider's firewall, a subscription sign-in, a password he set, a bundle he chose, access to his repository, a
#: question of whether another site on the server may stop, or money. Never a technical question (owner, 2026-11-20).
OWNER_FACT_CODES = {
    "email_required", "email_invalid",            # his address
    "domain_invalid", "dns_missing", "dns_mismatch",   # his domain and its record at the registrar
    "acme_staging_failed", "acme_real_failed",    # the provider's firewall; a rate limit and the choice of another name
    "public_port_busy",                           # another site on the server may stop: his decision
    "executors_login_needed",                     # his subscription sign-in
    "admin_unknown_password",                     # a password only he holds
    "norms_bundle_invalid",                       # which bundle he means
    "clone_needs_access", "no_origin_url",        # access to, and the address of, his repository
    "disk_too_small", "ram_too_small", "norms_disk_too_small",   # money
}
#: The codes whose action begins `REPORT TO THE OWNER`: a failure with no safe automatic action. The reader shows the line and the
#: last 30 lines and stops. A short list on purpose: each entry is a case where retrying or improvising could do harm.
REPORT_CODES = {
    "docker_key_mismatch", "docker_down", "docker_old",     # a possibly tampered download; a daemon that will not start; other containers
    "deploy_clone_installed", "env_invalid_installed",      # an installation's secrets must not be replaced
    "deploy_refused", "https_not_published", "verify_failed",   # a refusal this installer has no remedy for
    "admin_failed", "norms_busy", "norms_refused", "norms_import_failed", "norms_report_differs", "norms_designate_failed",
    "norms_lock_invalid", "norms_release_missing", "norms_download_corrupt",   # the published release is not what the lock says
    "executors_not_connected", "semantic_quality_failed",
    "deploy_timer_failed",                                  # the last stage: the timer that deploys pushes could not be set up
    "unexpected",
}


def test_ask_the_owner_lines_are_only_owner_facts_and_report_lines_are_the_few_with_no_safe_action(rig: Rig) -> None:
    ask, report, do = set(), set(), {}
    for line in rig.run("--print-codes").stdout.splitlines():
        code, text = line.split("\t")
        assert text.strip() and "|" not in text, code
        if text.startswith("ASK THE OWNER"):
            ask.add(code)
        elif text.startswith("REPORT TO THE OWNER"):
            report.add(code)
        else:
            do[code] = text
    assert ask == OWNER_FACT_CODES, f"ASK THE OWNER codes differ from the owner-fact list: {sorted(ask ^ OWNER_FACT_CODES)}"
    assert report == REPORT_CODES, f"REPORT TO THE OWNER codes differ from the list: {sorted(report ^ REPORT_CODES)}"
    # Every other code is something the reader does: it neither asks nor reports, and it says what to run or to wait for.
    for code, text in do.items():
        assert "THE OWNER" not in text.upper(), f"{code} sends a doable action to the owner"
        assert re.search(r"\b(run|Run|Wait|Install|Fix|Update|Nothing to do)\b", text), f"{code} names no action"


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
    for stage in range(1, 13):
        assert f"[{stage}/12]" in done.stdout
    assert "DRY RUN" in done.stdout and "STOP" not in done.stdout and "DONE:" not in done.stdout
    assert sorted(str(p) for p in rig.tmp.rglob("*")) == before
    assert not (rig.stub / "calls.log").exists()


def test_the_installer_help_lists_every_option_the_prompt_may_use(rig: Rig) -> None:
    done = rig.run("--help")
    assert done.returncode == 0
    for option in ("--email", "--domain", "--norms-bundle", "--instance", "--dry-run", "--resume-stage", "--skip-executors", "--deploy-mode"):
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
    done = rig.run("--email", EMAIL, "--http-port", str(stack.port), "--deploy-mode", "github")
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
    rig.plan("verify", "6|the stack is not this tree", "6|still not this tree")
    done = rig.run(*_args(stack))
    code, text = _stops(done)[-1]
    assert code == "verify_failed" and "status 6" in text
    assert [c.split()[0] for c in rig.calls() if c.startswith(("verify", "reload"))] == ["verify", "reload-proxy", "verify"]
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


def test_a_dirty_deploy_clone_is_a_doable_fix_not_a_question(rig: Rig, stack) -> None:
    """The fix is the same command with --deploy-path at a free path: the installer makes a clean clone there itself."""
    (rig.repo / "scratch.txt").write_text("x")
    done = rig.run(*_args(stack))
    code, text = _stops(done)[-1]
    assert code == "checkout_dirty" and "scratch.txt" in text
    assert f"--deploy-path {rig.deploy_root}/auditmanager-2" in text and "ASK THE OWNER" not in text
    assert not (rig.repo / "infra/deploy/env/alpha.env").exists()


def test_a_dirty_deploy_clone_that_holds_an_installation_is_reported_not_replaced(rig: Rig, stack) -> None:
    rig.plan("deploy", "1|stop here")
    rig.run(*_args(stack))
    (rig.repo / "scratch.txt").write_text("x")
    done = rig.run(*_args(stack))
    code, text = _stops(done)[-1]
    assert code == "deploy_clone_installed" and text.startswith("REPORT TO THE OWNER")


def test_a_clone_without_origin_gets_the_command_that_adds_it(rig: Rig, stack) -> None:
    subprocess.run(["git", "-C", str(rig.repo), "remote", "rename", "origin", "fork"], check=True)
    code, text = _stops(rig.run(*_args(stack)))[-1]
    assert code == "no_origin" and f"git -C {rig.repo} remote add origin {rig.origin}" in text and "ASK THE OWNER" not in text


def test_a_clone_with_no_remote_at_all_asks_for_the_repository_address(rig: Rig, stack) -> None:
    subprocess.run(["git", "-C", str(rig.repo), "remote", "remove", "origin"], check=True)
    code, text = _stops(rig.run(*_args(stack)))[-1]
    assert code == "no_origin_url" and text.startswith("ASK THE OWNER for the repository's clone URL")


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


def test_docker_that_is_down_is_started_and_one_that_will_not_start_is_reported(rig: Rig, stack) -> None:
    (rig.stub / "docker.down").write_text("")
    (rig.stub / "systemctl.fixes").write_text("")
    rig.plan("deploy", "1|stop here")
    done = rig.run(*_args(stack))
    assert "Docker does not answer: starting it" in done.stdout and _stops(done)[-1][0] == "deploy_failed"
    assert "systemctl enable --now docker" in (rig.stub / "systemctl.log").read_text()
    (rig.stub / "docker.down").write_text("")
    (rig.stub / "systemctl.fixes").unlink()
    code, text = _stops(rig.run(*_args(stack), env=rig.env(FIRST_INSTALL_POLL_SECONDS="1")))[-1]
    assert code == "docker_down" and text.startswith("REPORT TO THE OWNER") and "journalctl -u docker" in text


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
    assert f"variable DEPLOY_HOST={DOMAIN}" in done.stdout
    assert f"variable DEPLOY_PATH={rig.repo}" in done.stdout


def test_https_waits_for_the_certificate_and_stops_with_the_authoritys_own_words_when_it_never_comes(rig: Rig, stack) -> None:
    arguments = _https_rig(rig, stack)
    rig.plan("verify", *["7|served-certificate: NOT SERVED"] * 20)
    (rig.stub / "acme.log").write_text("acme-1  | certbot: starting\nacme-1  | Timeout during connect (likely firewall problem)\n")
    done = rig.run(*arguments)
    code, text = _stops(done)[-1]
    assert code == "acme_staging_failed" and "Timeout during connect (likely firewall problem)" in text
    assert text.startswith("ASK THE OWNER to open public ports 80 and 443")


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
    arguments = ["--email", EMAIL, "--http-port", str(stack.port), "--no-ci-key", "--deploy-mode", "github", "--domain", DOMAIN]
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
    done = rig.run("--email", EMAIL, "--http-port", str(stack.port), "--deploy-mode", "github")
    assert done.returncode == 0, done.stdout[-1500:]
    out = done.stdout
    assert "variable DEPLOY_MODE=github" in out and "variable DEPLOY_HOST=" in out and f"variable DEPLOY_PATH={rig.repo}" in out
    assert re.search(r"variable DEPLOY_KNOWN_HOSTS=\S+ ssh-ed25519 [A-Za-z0-9+/=]+", out)
    assert "SHA256:" in out and "acme-co/audit-install" in out
    assert "secret   VPS_USER=root" in out and "sudoers" not in out
    key_file = rig.secret_dir / "auditmanager-deploy-key"
    assert stat.S_IMODE(key_file.stat().st_mode) == 0o600 and str(key_file) in out
    public = (rig.secret_dir / "auditmanager-deploy-key.pub").read_text().split()[1]
    assert public in (rig.auth_home / ".ssh" / "authorized_keys").read_text()
    assert stat.S_IMODE((rig.auth_home / ".ssh" / "authorized_keys").stat().st_mode) == 0o600


def test_a_rerun_keeps_the_deploy_key_and_does_not_authorize_it_twice(rig: Rig, stack) -> None:
    _happy_plan(rig)
    assert rig.run("--email", EMAIL, "--http-port", str(stack.port), "--deploy-mode", "github").returncode == 0
    key_before = (rig.secret_dir / "auditmanager-deploy-key").read_bytes()
    assert rig.run("--email", EMAIL, "--http-port", str(stack.port), "--deploy-mode", "github", "--resume-stage", "9").returncode == 0
    assert (rig.secret_dir / "auditmanager-deploy-key").read_bytes() == key_before
    authorized = (rig.auth_home / ".ssh" / "authorized_keys").read_text().splitlines()
    assert len(authorized) == 1


def test_a_non_root_deploy_user_gets_the_sudoers_line(rig: Rig) -> None:
    driver = (f'source "{rig.repo}/infra/deploy/first-install.sh"; OPT_DEPLOY_USER=nobody; OPT_NO_CI_KEY=yes; '
              f'REPO="{rig.repo}"; INSTANCE=auditmanager; OPT_DOMAIN=; stage_github')
    done = subprocess.run(["bash", "-c", driver], capture_output=True, text=True, env=rig.env())
    assert done.returncode == 0, done.stderr
    assert f"nobody ALL=(root) NOPASSWD: {rig.repo}/infra/deploy/local-agent.sh" in done.stdout
    assert "secret   VPS_USER=nobody" in done.stdout


# --------------------------------------------------------------------------------------------------- the script itself


def test_the_script_is_shellcheck_clean() -> None:
    if shutil.which("shellcheck") is None:
        pytest.skip("shellcheck is not installed")
    done = subprocess.run(["shellcheck", "-x", str(SCRIPT)], capture_output=True, text=True, cwd=ROOT)
    assert done.returncode == 0, done.stdout


def test_the_script_never_deletes_resets_or_cleans() -> None:
    text = SCRIPT.read_text()
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    code = code[:code.index('CODES_TABLE="$(cat')] + code[code.index("\nTABLE\n"):]
    for forbidden in ("rm -rf", "git clean", "git reset", "git checkout", "down --volumes", "--volumes", "docker volume rm",
                      "docker system prune", "docker rm", "pkill", "killall", "git push", "git stash"):
        assert forbidden not in code, forbidden
    # The only files it removes are its own temporary ones, and the one process it ends is its own background sampler.
    removals = re.findall(r"\brm (-\w+ )?([^;&|\n]+)", code)
    for _flags, target in removals:
        assert re.fullmatch(r'(\$\{?[a-z_]+\}?|"\$\{?[a-zA-Z_]+\}?"|"\$\{?[A-Za-z_]+\}?\.tmp")\s*(\|\|.*)?', target.strip()) \
            or (_flags + target).strip().startswith("-sf norm-embed"), f"unexpected rm of {target!r}"
    assert re.findall(r"\bkill ([^;&|\n]+)", code) == ['"$sampler" 2>/dev/null ']
    # The one service it removes is the embedder, the document's own rollback, and only when the owner turned it off.
    assert code.count("rm -sf norm-embed") == 1


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
    for pair in re.findall(r"\bescalate ([a-z_]+) ([a-z_]+)", code):
        used.update(pair)
    assert used <= table, f"stop codes used but not in the table: {sorted(used - table)}"
    unused = table - used - {"unexpected"}
    assert not unused, f"codes in the table that no stop uses: {sorted(unused)}"


def test_the_prompt_is_short_and_carries_the_rules_a_simple_agent_needs() -> None:
    text = PROMPT.read_text()
    prose = text[:text.index("<!-- STOP-CODES:BEGIN -->")]
    assert len(prose.strip().splitlines()) <= 60
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
    assert "first-install.sh" in head and "FIRST-INSTALL-PROMPT.md" in head and "/srv/<instance>" in head
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


# ------------------------------------------------------------------ tools and Docker: installed by the script, or one command


def _apt_log(rig: Rig) -> str:
    """What apt-get was asked, one line per call, without the lock-wait option every call carries."""
    path = rig.stub / "apt.log"
    return path.read_text().replace("-o DPkg::Lock::Timeout=300 ", "") if path.exists() else ""


def test_a_missing_tool_is_installed_with_apt_get_and_the_stop_prints_the_one_command_if_that_did_not_help(rig: Rig, stack) -> None:
    done = rig.run(*_args(stack), env=rig.env(FIRST_INSTALL_FAKE_MISSING="flock"))
    assert "apt-get -q -y install util-linux" in _apt_log(rig)
    code, text = _stops(done)[-1]
    assert code == "tool_missing" and "apt-get update && apt-get install -y util-linux" in text and "ASK" not in text


def test_a_missing_tool_on_another_distribution_is_one_printed_command_and_nothing_is_installed(rig: Rig, stack) -> None:
    done = rig.run(*_args(stack), env=rig.env(FIRST_INSTALL_FAKE_MISSING="flock ssh-keygen", FIRST_INSTALL_PKG_MANAGER="dnf"))
    code, text = _stops(done)[-1]
    assert code == "tool_missing" and "dnf install -y util-linux openssh-clients" in text
    assert _apt_log(rig) == ""


def test_docker_that_is_missing_is_installed_from_dockers_repository_after_the_pinned_fingerprint_matches(rig: Rig, stack) -> None:
    rig.plan("deploy", "1|stop here")
    done = rig.run(*_args(stack), env=rig.env(FIRST_INSTALL_FAKE_MISSING="docker"))
    assert _stops(done)[-1][0] == "deploy_failed", done.stdout[-1500:]
    log = _apt_log(rig)
    assert "-q -y install ca-certificates curl gnupg" in log
    assert "-q -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin" in log
    assert "https://download.docker.com/linux/ubuntu/gpg" in (rig.stub / "curl.log").read_text()
    assert (rig.keyrings / "docker.asc").is_file()
    listing = (rig.apt_sources / "docker.list").read_text()
    assert listing.strip() == f"deb [arch=amd64 signed-by={rig.keyrings}/docker.asc] https://download.docker.com/linux/ubuntu noble stable"
    assert "systemctl enable --now docker" in (rig.stub / "systemctl.log").read_text()


def test_on_debian_the_repository_is_debians_and_a_second_run_does_not_write_it_again(rig: Rig, stack) -> None:
    rig.os_release.write_text("ID=debian\nVERSION_CODENAME=bookworm\n")
    rig.plan("deploy", "1|stop here")
    rig.run(*_args(stack), env=rig.env(FIRST_INSTALL_FAKE_MISSING="docker"))
    assert "linux/debian bookworm stable" in (rig.apt_sources / "docker.list").read_text()
    before = (rig.apt_sources / "docker.list").stat().st_mtime_ns
    rig.plan("deploy", "1|stop here")
    rig.run(*_args(stack), env=rig.env(FIRST_INSTALL_FAKE_MISSING="docker"))
    assert (rig.apt_sources / "docker.list").stat().st_mtime_ns == before


def test_a_docker_key_with_another_fingerprint_installs_nothing_and_is_reported(rig: Rig, stack) -> None:
    done = rig.run(*_args(stack), env=rig.env(FIRST_INSTALL_FAKE_MISSING="docker", STUB_GPG_FPR="0" * 40))
    code, text = _stops(done)[-1]
    assert code == "docker_key_mismatch" and text.startswith("REPORT TO THE OWNER") and "0" * 40 in text
    assert "docker-ce" not in _apt_log(rig) and not (rig.apt_sources / "docker.list").exists() and not (rig.keyrings / "docker.asc").exists()


def test_docker_on_a_distribution_without_dockers_repository_is_one_printed_command(rig: Rig, stack) -> None:
    rig.os_release.write_text("ID=fedora\nVERSION_CODENAME=\n")
    done = rig.run(*_args(stack), env=rig.env(FIRST_INSTALL_FAKE_MISSING="docker", FIRST_INSTALL_PKG_MANAGER="dnf"))
    code, text = _stops(done)[-1]
    assert code == "docker_missing" and "curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sh /tmp/get-docker.sh" in text
    assert _apt_log(rig) == ""


def test_a_failing_package_install_is_a_run_again_not_a_question(rig: Rig, stack) -> None:
    (rig.stub / "apt.fail").write_text("")
    done = rig.run(*_args(stack), env=rig.env(FIRST_INSTALL_FAKE_MISSING="docker"))
    code, text = _stops(done)[-1]
    assert code == "docker_install_failed" and "ASK" not in text and "Unable to locate package" in text


def test_an_old_compose_gets_its_plugin_and_an_old_engine_is_upgraded_only_when_nothing_runs(rig: Rig, stack) -> None:
    (rig.stub / "compose.version").write_text("1.29.2")
    rig.plan("deploy", "1|stop here")
    assert _stops(rig.run(*_args(stack)))[-1][0] == "deploy_failed"
    assert "docker-compose-plugin" in _apt_log(rig) and "docker-ce " not in _apt_log(rig)
    (rig.stub / "docker.version").write_text("19.03.8")
    (rig.stub / "docker.ps").write_text("someone-elses-app-1\n")
    code, text = _stops(rig.run(*_args(stack)))[-1]
    assert code == "docker_old" and text.startswith("REPORT TO THE OWNER") and "Docker Engine 19 is installed" in text
    (rig.stub / "docker.ps").write_text("")
    rig.plan("deploy", "1|stop here")
    assert _stops(rig.run(*_args(stack)))[-1][0] == "deploy_failed"
    assert "docker-ce docker-ce-cli" in _apt_log(rig)


# -------------------------------------------------------------------------- shortages: do the first thing, then the owner's money


def test_a_disk_shortage_says_prune_the_first_time_and_asks_for_a_bigger_disk_the_second(rig: Rig, stack) -> None:
    low = rig.env(STUB_DF_BYTES=str(3 * 1024**3))
    first = _stops(rig.run(*_args(stack), env=low))[-1]
    assert first[0] == "disk_low" and "docker builder prune -af" in first[1] and "ASK" not in first[1]
    second = _stops(rig.run(*_args(stack), env=low))[-1]
    assert second[0] == "disk_too_small" and second[1].startswith("ASK THE OWNER for a larger disk")
    rig.plan("deploy", "1|stop here")
    assert _stops(rig.run(*_args(stack)))[-1][0] == "deploy_failed"     # enough disk now: the hint is cleared
    assert _stops(rig.run(*_args(stack), env=low))[-1][0] == "disk_low"


def test_a_memory_shortage_says_wait_the_first_time_and_asks_for_a_bigger_server_the_second(rig: Rig, stack) -> None:
    rig.meminfo.write_text("MemTotal:  2000000 kB\nMemAvailable:  500000 kB\n")
    first = _stops(rig.run(*_args(stack)))[-1]
    assert first[0] == "ram_low" and "Wait five minutes" in first[1]
    assert _stops(rig.run(*_args(stack)))[-1][0] == "ram_too_small"


def test_a_busy_default_port_is_replaced_by_a_free_one(rig: Rig, stack) -> None:
    (rig.proc_net / "tcp").write_text("  sl  local_address rem_address   st\n   0: 00000000:7B0C 00000000:0000 0A 0\n")   # 31500
    rig.plan("deploy", "1|stop here")
    done = rig.run("--email", EMAIL, "--no-ci-key", "--deploy-mode", "github")
    assert "port 31500 is in use: the application will use port 31501 instead" in done.stdout
    assert rig.alpha()["ALPHA_HTTP_PORT"] == "31501"


def test_a_busy_port_the_reader_chose_prints_a_free_one(rig: Rig, stack) -> None:
    (rig.proc_net / "tcp").write_text("  sl  local_address rem_address   st\n   0: 00000000:7B0C 00000000:0000 0A 0\n")
    code, text = _stops(rig.run("--email", EMAIL, "--http-port", "31500"))[-1]
    assert code == "http_port_busy" and "--http-port 31501" in text and "ASK" not in text


def test_a_broken_environment_with_nothing_deployed_gets_the_move_command_and_one_with_an_installation_is_reported(rig: Rig, stack) -> None:
    rig.plan("deploy", "1|stop here")
    rig.run(*_args(stack))
    alpha = rig.repo / "infra/deploy/env/alpha.env"
    alpha.write_text(fie.set_value(alpha.read_text(), "AUDITMANAGER_API_TOKEN", "change-me-this-example-token-authorizes-nothing"))
    # Nothing was deployed yet (the first deploy failed), so the files hold nothing in use: move them aside, and write new ones.
    code, text = _stops(rig.run(*_args(stack)))[-1]
    assert code == "env_invalid" and "mv " in text and "rejected-" in text and "-alpha.env" in text and "ASK" not in text
    assert "AUDITMANAGER_API_TOKEN" in text and "authorizes-nothing" not in text
    # With a database volume of this instance the same file must not be replaced: its passwords are in the volume.
    (rig.stub / "volume.exists").write_text("")
    code, text = _stops(rig.run(*_args(stack)))[-1]
    assert code == "env_invalid_installed" and text.startswith("REPORT TO THE OWNER")
    (rig.stub / "volume.exists").unlink()
    # The printed command works: the rejected file stays git-ignored, and the rerun writes new files.
    moved = text.split("Run this command: ")[1].split("   then run")[0] if "Run this command: " in text else None
    code, text = _stops(rig.run(*_args(stack)))[-1]
    moved = text.split("Run this command: ")[1].split("   then run")[0]
    subprocess.run(moved, shell=True, check=True)
    assert rig.clean()
    rig.plan("deploy", "1|stop here")
    assert _stops(rig.run(*_args(stack)))[-1][0] == "deploy_failed"
    assert fie.parse_env(alpha.read_text())["AUDITMANAGER_API_TOKEN"] != "change-me-this-example-token-authorizes-nothing"


def test_a_deploy_user_that_is_not_ready_gets_the_exact_command(rig: Rig, stack) -> None:
    code, text = _stops(rig.run(*_args(stack), "--deploy-user", "no-such-user-here"))[-1]
    assert code == "deploy_user_invalid" and "adduser --disabled-password --gecos '' no-such-user-here" in text
    code, text = _stops(rig.run(*_args(stack), "--deploy-user", "nobody"))[-1]
    assert code == "deploy_user_invalid" and "usermod -aG docker nobody" in text


def test_a_deploy_clone_older_than_the_pin_gets_the_two_git_commands(rig: Rig, stack) -> None:
    rig.unpin_acme_client()
    (rig.stub / f"dns-{DOMAIN}").write_text("203.0.113.7\n")
    rig.plan("deploy", f"3|{GATE}", "0|ok")
    (rig.stub / "agent.status").write_text(SUBSCRIPTION)
    code, text = _stops(rig.run(*_args(stack, "--domain", DOMAIN)))[-1]
    assert code == "acme_unpinned" and f"git -C {rig.repo} fetch origin && git -C {rig.repo} checkout --detach origin/HEAD" in text


# ------------------------------------------------------------------- the semantic norm lookup (NORM-VECTOR-TEMP-01), always on


def _norms_done(rig: Rig) -> None:
    """The norms stage made a snapshot current in an earlier run (the real import is `test_first_install_norms.py`'s)."""
    state = rig.state_root / "auditmanager"
    state.mkdir(parents=True, exist_ok=True)
    (state / "first-install.state").write_text("s5=ok\ns5.designated=ok\n")


def _url(rig: Rig) -> str:
    return rig.alpha()["AUDITMANAGER_NORM_EMBED_URL"]


def _docker_calls(rig: Rig) -> list[str]:
    path = rig.stub / "docker.log"
    return path.read_text().splitlines() if path.exists() else []


def _semantic_calls(rig: Rig) -> list[str]:
    path = rig.stub / "semantic.log"
    return path.read_text().splitlines() if path.exists() else []


def test_without_a_norms_bundle_the_lookup_waits_and_the_owner_is_told_how_it_turns_on(rig: Rig, stack) -> None:
    _happy_plan(rig)
    done = rig.run(*_args(stack))
    assert done.returncode == 0, done.stdout[-2000:]
    assert rig.alpha()["ALPHA_NORM_EMBED"] == "yes" and _url(rig) == ""       # the embedder is built, the address is empty
    assert "semantic norm lookup stays off for now" in done.stdout and _semantic_calls(rig) == []
    assert "it turns on by itself when the installer is run again with --norms-bundle" in done.stdout
    note = [line for line in done.stdout.splitlines() if line.startswith("  note")]
    assert len(note) == 1 and "--norms-bundle" in note[0]
    last = [line for line in done.stdout.splitlines() if line.strip()][-1]
    assert last.startswith("DONE:") and "Semantic norm lookup: off until the installer is run again with the norms bundle" in last
    state = (rig.state_root / "auditmanager" / "first-install.state").read_text()
    assert "s10=ok" not in state and "s8=ok" in state
    assert "stage_10_semantic=off until the installer is run again with the norms bundle" in (rig.state_root / "auditmanager" / "first-install.done").read_text()


def test_both_gates_passing_sets_the_address_restarts_the_worker_and_is_done_once(rig: Rig, stack) -> None:
    _happy_plan(rig)
    _norms_done(rig)
    done = rig.run(*_args(stack))
    assert done.returncode == 0, done.stdout[-2500:]
    assert _url(rig) == "http://norm-embed:8080"
    assert len(_semantic_calls(rig)) == 1
    assert "--url http://norm-embed:8080 --windows 500" in _semantic_calls(rig)[0] and "exec -T worker python -m auditmanager.norms.semantic_check" in _semantic_calls(rig)[0]
    restarts = [c for c in _docker_calls(rig) if "up -d --no-deps worker" in c]
    assert len(restarts) == 1 and "norm-embed" in restarts[0]          # the profile deploy.sh puts in every compose command
    assert "both gates passed" in done.stdout and "quality gate: PASS (mean inner product 0.9812" in done.stdout
    assert "Semantic norm lookup: on." in done.stdout
    assert "s10=ok" in (rig.state_root / "auditmanager" / "first-install.state").read_text()
    assert not [line for line in done.stdout.splitlines() if line.startswith("  note")]
    # a rerun after success does not run the gates again (the marker refuses; without it the stage is skipped as done)
    (rig.state_root / "auditmanager" / "first-install.done").unlink()
    again = rig.run(*_args(stack))
    assert again.returncode == 0 and again.stdout.count("done before: skipped") >= 5
    assert len(_semantic_calls(rig)) == 1 and _url(rig) == "http://norm-embed:8080"


def test_resuming_the_stage_asks_the_gates_again_and_leaves_the_address_as_it_was(rig: Rig, stack) -> None:
    _happy_plan(rig)
    _norms_done(rig)
    assert rig.run(*_args(stack)).returncode == 0
    again = rig.run(*_args(stack, "--resume-stage", "10"))
    assert again.returncode == 0, again.stdout[-1500:]
    assert len(_semantic_calls(rig)) == 2 and _url(rig) == "http://norm-embed:8080"


def test_the_memory_gate_at_rest_stops_with_a_wait_and_the_address_stays_empty(rig: Rig, stack) -> None:
    _happy_plan(rig)
    _norms_done(rig)
    (rig.stub / "deploy.setmem").write_text("MemTotal:  8000000 kB\nMemAvailable:  400000 kB\n")   # what the host has after the build
    done = rig.run(*_args(stack))
    code, text = _stops(done)[-1]
    assert code == "semantic_memory_low" and "only 390 MiB of memory are available at rest" in text
    assert "Wait ten minutes" in text and "ASK" not in text and _url(rig) == ""
    assert _semantic_calls(rig) == []                  # the quality gate is not started on a host that fails the memory gate


def test_the_memory_gate_under_load_stops_even_when_the_quality_gate_passes(rig: Rig, stack) -> None:
    _happy_plan(rig)
    _norms_done(rig)
    (rig.stub / "semantic.low_mem").write_text("")
    done = rig.run(*_args(stack))
    code, text = _stops(done)[-1]
    assert code == "semantic_memory_low" and "fell to" in text and "while the embedder worked" in text
    assert _url(rig) == "" and not [c for c in _docker_calls(rig) if "up -d --no-deps worker" in c]


def test_swap_that_grows_fails_the_memory_gate(rig: Rig, stack) -> None:
    _happy_plan(rig)
    _norms_done(rig)
    (rig.stub / "semantic.swap_grows").write_text("")
    code, text = _stops(rig.run(*_args(stack)))[-1]
    assert code == "semantic_memory_low" and "swap grew" in text and _url(rig) == ""


def test_the_quality_gate_failing_reports_with_the_exact_command_for_word_search_only(rig: Rig, stack) -> None:
    _happy_plan(rig)
    _norms_done(rig)
    (rig.stub / "semantic.out").write_text(SEMANTIC_FAIL)
    (rig.stub / "semantic.exit").write_text("1")
    done = rig.run(*_args(stack))
    code, text = _stops(done)[-1]
    assert code == "semantic_quality_failed" and text.startswith("REPORT TO THE OWNER")
    assert "mean inner product 0.9311 (it must be 0.97 or more)" in text and "self-recall@10 0.934 (0.90 or more)" in text
    assert "stays OFF" in text and "word search" in text
    assert f"--set ALPHA_NORM_EMBED=no" in text and "sudo infra/deploy/first-install.sh --email" in text
    assert _url(rig) == "" and not (rig.state_root / "auditmanager" / "first-install.done").exists()
    # everything else was installed: only the last-but-one stage is open
    state = (rig.state_root / "auditmanager" / "first-install.state").read_text()
    assert "s8=ok" in state and "s10=ok" not in state


def test_the_printed_command_for_word_search_only_finishes_the_installation(rig: Rig, stack) -> None:
    _happy_plan(rig)
    _norms_done(rig)
    (rig.stub / "semantic.out").write_text(SEMANTIC_FAIL)
    (rig.stub / "semantic.exit").write_text("1")
    first = _stops(rig.run(*_args(stack)))[-1][1]
    assert "--set ALPHA_NORM_EMBED=no" in first
    (rig.stub / "norm-embed.ps").write_text("cid-norm-embed\n")
    done = rig.run(*_args(stack, "--set", "ALPHA_NORM_EMBED=no"))
    assert done.returncode == 0, done.stdout[-2000:]
    assert rig.alpha()["ALPHA_NORM_EMBED"] == "no" and _url(rig) == ""
    assert "the owner's choice ALPHA_NORM_EMBED=no is applied to the existing alpha.env" in done.stdout
    assert any("rm -sf norm-embed" in c for c in _docker_calls(rig))      # the document's rollback, once, on the service only
    assert "Semantic norm lookup: off (the owner's choice)." in done.stdout
    assert len(_semantic_calls(rig)) == 1                                  # no second run of the gates


def test_a_quality_check_that_cannot_run_is_run_again_and_not_a_verdict(rig: Rig, stack) -> None:
    _happy_plan(rig)
    _norms_done(rig)
    (rig.stub / "semantic.out").write_text("Traceback (most recent call last):\nConnectionError: norm-embed is not reachable\n")
    (rig.stub / "semantic.exit").write_text("1")
    code, text = _stops(rig.run(*_args(stack)))[-1]
    assert code == "semantic_check_failed" and "ConnectionError" in text and "Run the same command once more" in text and _url(rig) == ""


def test_a_worker_that_does_not_restart_has_the_address_taken_out_again(rig: Rig, stack) -> None:
    _happy_plan(rig)
    _norms_done(rig)
    (rig.stub / "worker.fail").write_text("")
    code, text = _stops(rig.run(*_args(stack)))[-1]
    assert code == "semantic_worker_failed" and "worker could not start" in text and _url(rig) == ""
    assert len([c for c in _docker_calls(rig) if "up -d --no-deps worker" in c]) == 2     # the restart, then the restart after the rollback


def test_an_address_set_earlier_is_taken_out_when_a_later_gate_fails(rig: Rig, stack) -> None:
    rig.plan("deploy", "1|stop here")
    rig.run(*_args(stack))
    subprocess.run([sys.executable, str(DEPLOY / "lib/first_install_env.py"), "set", "--env",
                    str(rig.repo / "infra/deploy/env/alpha.env"), "AUDITMANAGER_NORM_EMBED_URL=http://norm-embed:8080"], check=True)
    _happy_plan(rig)
    _norms_done(rig)
    (rig.stub / "semantic.out").write_text(SEMANTIC_FAIL)
    (rig.stub / "semantic.exit").write_text("1")
    assert _stops(rig.run(*_args(stack)))[-1][0] == "semantic_quality_failed"
    assert _url(rig) == ""
    assert any("up -d --no-deps worker" in c for c in _docker_calls(rig))             # the worker was restarted on the empty address


def test_the_owners_choice_at_creation_means_no_embedder_gates_and_no_note(rig: Rig, stack) -> None:
    _happy_plan(rig)
    _norms_done(rig)
    done = rig.run(*_args(stack, "--set", "ALPHA_NORM_EMBED=no"))
    assert done.returncode == 0, done.stdout[-2000:]
    assert rig.alpha()["ALPHA_NORM_EMBED"] == "no" and _url(rig) == "" and _semantic_calls(rig) == []
    assert "Semantic norm lookup: off (the owner's choice)." in done.stdout
    assert not [line for line in done.stdout.splitlines() if line.startswith("  note")]


def test_an_installation_without_a_bundle_is_finished_by_running_it_again_with_one(rig: Rig, stack, tmp_path: Path) -> None:
    """The re-run path: the marker exists, the owner brings the bundle later, and the installer does not refuse."""
    _happy_plan(rig)
    assert rig.run(*_args(stack)).returncode == 0
    assert _stops(rig.run(*_args(stack)))[-1][0] == "already_installed"
    bundle = tmp_path / "not-a-bundle"
    bundle.mkdir()
    again = rig.run(*_args(stack, "--norms-bundle", str(bundle)))
    codes = [code for code, _ in _stops(again)]
    assert "already_installed" not in codes and codes[-1] == "norms_bundle_invalid", again.stdout[-1500:]
    assert "this server was installed without the norms: adding them" in again.stdout and "[5/12]" in again.stdout
    assert "done before: skipped" in again.stdout                        # the stages that were finished are not run again
    # and once the norms were designated and the semantic stage done, the bundle is no reason to run again
    _norms_done(rig)
    state = rig.state_root / "auditmanager" / "first-install.state"
    state.write_text(state.read_text() + "s10=ok\n")
    assert _stops(rig.run(*_args(stack, "--norms-bundle", str(bundle))))[-1][0] == "already_installed"


# ------------------------------------------------------- the deploy clone: the working copy it was started in is never installed from


def _tree(path: Path) -> list[str]:
    return sorted(str(p.relative_to(path)) for p in path.rglob("*") if ".git" not in p.relative_to(path).parts)


def _head(path: Path) -> str:
    return subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()


def _dev_args(stack, *extra: str) -> list[str]:
    return ["--email", EMAIL, "--http-port", str(stack.port), "--no-ci-key", "--deploy-mode", "github", *extra]


def test_started_in_a_working_copy_it_makes_the_deploy_clone_and_continues_in_it(devrig: Rig, stack) -> None:
    _happy_plan(devrig)
    before = (_head(devrig.dev), _tree(devrig.dev))
    assert not devrig.deploy.exists()
    done = devrig.run(*_dev_args(stack))
    assert done.returncode == 0, done.stdout[-3000:]
    # the clone is made from the working copy's origin, detached at the working copy's commit, as every auto-deploy leaves it
    assert (devrig.deploy / ".git").is_dir() and _head(devrig.deploy) == _head(devrig.dev)
    detached = subprocess.run(["git", "-C", str(devrig.deploy), "symbolic-ref", "-q", "HEAD"], capture_output=True)
    assert detached.returncode != 0
    assert (subprocess.run(["git", "-C", str(devrig.deploy), "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
            == str(devrig.origin))
    # it says so in one line, the stages run once, in the deploy clone, and the installation lives there
    assert done.stdout.count("making the deploy clone") == 1 and f"continuing in {devrig.deploy}" in done.stdout
    assert done.stdout.count("[1/12]") == 1 and done.stdout.rstrip().splitlines()[-1].startswith(f"DONE: auditmanager is installed at {devrig.deploy} ")
    assert (devrig.deploy / "infra/deploy/env/alpha.env").is_file()
    assert f"variable DEPLOY_PATH={devrig.deploy}" in done.stdout
    assert f"repo={devrig.deploy}" in (devrig.state_root / "auditmanager" / "first-install.done").read_text()
    # the owner's working copy is not touched: same commit, same files, no environment file, nothing to commit
    assert (_head(devrig.dev), _tree(devrig.dev)) == before
    assert not (devrig.dev / "infra/deploy/env/alpha.env").exists() and devrig.clean()
    # the stages' output is in the one log
    assert "making the deploy clone" in (devrig.log_dir / "auditmanager-first-install.log").read_text()


def test_an_existing_clean_deploy_clone_with_the_same_origin_is_reused_and_a_rerun_from_either_clone_converges(devrig: Rig, stack) -> None:
    devrig.plan("deploy", "1|stop here")
    first = devrig.run(*_dev_args(stack))
    assert _stops(first)[-1][0] == "deploy_failed" and "making the deploy clone" in first.stdout
    env_bytes = (devrig.deploy / "infra/deploy/env/alpha.env").read_bytes()
    deploy_head = _head(devrig.deploy)
    _happy_plan(devrig)
    # from the working copy again: reused, not cloned a second time
    second = devrig.run(*_dev_args(stack))
    assert "making the deploy clone" not in second.stdout and "exists, is clean and has the same origin: used as it is" in second.stdout
    assert second.returncode == 0, second.stdout[-2500:]
    assert (devrig.deploy / "infra/deploy/env/alpha.env").read_bytes() == env_bytes and _head(devrig.deploy) == deploy_head
    # and from inside the deploy clone itself, with a bundle-less rerun after the marker: refused as installed, no clone, no re-exec
    inside = subprocess.run([str(devrig.deploy / "infra/deploy/first-install.sh"), *_dev_args(stack)], capture_output=True, text=True,
                            cwd=devrig.deploy, env=devrig.env())
    assert _stops(inside)[-1][0] == "already_installed" and "making the deploy clone" not in inside.stdout


def test_started_inside_the_deploy_clone_nothing_is_cloned_and_nothing_is_re_executed(rig: Rig, stack) -> None:
    _happy_plan(rig)
    done = rig.run(*_args(stack))
    assert done.returncode == 0, done.stdout[-2000:]
    assert "making the deploy clone" not in done.stdout and "continuing in" not in done.stdout
    assert [p.name for p in rig.deploy_root.iterdir()] == ["auditmanager"]


def test_a_deploy_path_that_is_empty_is_filled(devrig: Rig, stack) -> None:
    devrig.deploy.mkdir(parents=True)
    _happy_plan(devrig)
    done = devrig.run(*_dev_args(stack))
    assert done.returncode == 0 and "making the deploy clone" in done.stdout and _head(devrig.deploy) == _head(devrig.dev)


def test_a_dirty_deploy_clone_without_an_installation_gets_a_command_with_a_free_path_and_that_command_works(devrig: Rig, stack) -> None:
    import shlex

    devrig.plan("deploy", "1|stop here")
    subprocess.run(["git", "clone", "-q", str(devrig.origin), str(devrig.deploy)], check=True)
    (devrig.deploy / "scratch.txt").write_text("x")
    done = devrig.run(*_dev_args(stack))
    code, text = _stops(done)[-1]
    assert code == "deploy_path_unusable" and "it has local changes (?? scratch.txt)" in text and "ASK" not in text
    command = text.split("(it uses a free path; nothing at the old path is touched): ")[1]
    assert f"--deploy-path {devrig.deploy_root}/auditmanager-2" in command
    assert (devrig.deploy / "scratch.txt").exists()                      # nothing at the old path was touched
    _happy_plan(devrig)
    arguments = shlex.split(command)[2:]
    fixed = devrig.run(*arguments)
    assert fixed.returncode == 0, fixed.stdout[-2000:]
    assert (devrig.deploy_root / "auditmanager-2" / "infra/deploy/env/alpha.env").is_file()
    assert f"variable DEPLOY_PATH={devrig.deploy_root}/auditmanager-2" in fixed.stdout


def test_a_dirty_deploy_clone_that_holds_an_installation_is_reported_never_replaced(devrig: Rig, stack) -> None:
    devrig.plan("deploy", "1|stop here")
    devrig.run(*_dev_args(stack))
    (devrig.deploy / "scratch.txt").write_text("x")
    code, text = _stops(devrig.run(*_dev_args(stack)))[-1]
    assert code == "deploy_clone_installed" and text.startswith("REPORT TO THE OWNER") and "local changes" in text
    assert not (devrig.deploy_root / "auditmanager-2").exists()


def test_a_deploy_path_holding_another_repository_is_refused_with_the_names_of_both(devrig: Rig, stack, tmp_path: Path) -> None:
    other = tmp_path / "remote" / "other-co" / "other.git"
    other.parent.mkdir(parents=True)
    subprocess.run(["git", "clone", "-q", "--bare", str(devrig.origin), str(other)], check=True)
    subprocess.run(["git", "clone", "-q", str(other), str(devrig.deploy)], check=True)
    code, text = _stops(devrig.run(*_dev_args(stack)))[-1]
    assert code == "deploy_path_unusable" and "its origin is other-co/other, not acme-co/audit-install" in text


def test_a_deploy_path_that_is_not_a_clone_is_refused(devrig: Rig, stack) -> None:
    devrig.deploy.mkdir(parents=True)
    (devrig.deploy / "something").write_text("x")
    code, text = _stops(devrig.run(*_dev_args(stack)))[-1]
    assert code == "deploy_path_unusable" and "is not a clone of a repository" in text and (devrig.deploy / "something").exists()


def test_origin_names_are_compared_the_way_auto_deploy_compares_them(devrig: Rig, stack) -> None:
    """https, git@, ssh:// and a path are the same repository; the case of the owner and the name is ignored."""
    for address in ("https://github.com/Acme-Co/Audit-Install.git", "git@github.com:acme-co/audit-install", "ssh://git@github.com/acme-co/audit-install.git/"):
        done = subprocess.run(
            ["bash", "-c", f'source "{devrig.dev}/infra/deploy/first-install.sh"; repo_slug "{address}"'],
            capture_output=True, text=True, env=devrig.env())
        assert done.stdout.strip() == "acme-co/audit-install", address


def test_a_repository_the_server_cannot_read_is_an_owner_fact_and_other_clone_failures_are_a_run_again(devrig: Rig, stack) -> None:
    (devrig.stub / "git.clone_error").write_text("fatal: could not read Username for 'https://github.com': terminal prompts disabled\n")
    code, text = _stops(devrig.run(*_dev_args(stack)))[-1]
    assert code == "clone_needs_access" and text.startswith("ASK THE OWNER to give this server read access to the repository")
    assert "deploy key" in text and "access token" in text and not devrig.deploy.exists()
    (devrig.stub / "git.clone_error").write_text("fatal: unable to access 'https://github.com/x/y.git/': Could not resolve host: github.com\n")
    code, text = _stops(devrig.run(*_dev_args(stack)))[-1]
    assert code == "clone_failed" and "Could not resolve host" in text and "ASK" not in text


def test_a_working_copy_without_origin_uses_its_other_remote_and_one_without_any_remote_asks_for_the_address(devrig: Rig, stack) -> None:
    subprocess.run(["git", "-C", str(devrig.dev), "remote", "rename", "origin", "fork"], check=True)
    _happy_plan(devrig)
    done = devrig.run(*_dev_args(stack))
    assert done.returncode == 0, done.stdout[-1500:]
    assert "this clone has no 'origin': the address of its remote 'fork' is used" in done.stdout
    assert (subprocess.run(["git", "-C", str(devrig.deploy), "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
            == str(devrig.origin))
    shutil.rmtree(devrig.deploy)
    subprocess.run(["git", "-C", str(devrig.dev), "remote", "remove", "fork"], check=True)
    (devrig.state_root / "auditmanager" / "first-install.done").unlink()
    code, text = _stops(devrig.run(*_dev_args(stack)))[-1]
    assert code == "no_origin_url" and text.startswith("ASK THE OWNER for the repository's clone URL") and not devrig.deploy.exists()


def test_a_commit_that_is_not_on_origin_falls_back_to_the_branch_tip_there_and_says_so(devrig: Rig, stack) -> None:
    (devrig.dev / "local-only.txt").write_text("not pushed")
    git = ["git", "-C", str(devrig.dev), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "unpublished"], check=True)
    unpublished = _head(devrig.dev)
    published = subprocess.run(["git", "-C", str(devrig.origin), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    devrig.plan("deploy", "1|stop here")
    done = devrig.run(*_dev_args(stack))
    assert _head(devrig.deploy) == published != unpublished
    assert f"the commit {unpublished[:8]} of the starting clone is not on origin" in done.stdout
    assert not (devrig.deploy / "local-only.txt").exists()


def test_a_dry_run_in_a_working_copy_says_what_it_would_make_and_makes_nothing(devrig: Rig, stack) -> None:
    done = devrig.run(*_dev_args(stack, "--dry-run"))
    assert done.returncode == 0 and f"{devrig.deploy} would be made from the origin of this clone at its commit" in done.stdout
    assert not devrig.deploy.exists() and not (devrig.state_root / "auditmanager").exists()
    devrig.deploy.mkdir(parents=True)
    (devrig.deploy / "x").write_text("x")
    again = devrig.run(*_dev_args(stack, "--dry-run"))
    assert f"{devrig.deploy} exists: it would be checked" in again.stdout


def test_the_deploy_path_option_is_validated_like_deploy_path_and_respected(devrig: Rig, stack) -> None:
    for bad in ("relative/path", "/srv/has space", "/srv/../etc", "/srv/./x"):
        assert devrig.run(*_dev_args(stack), "--deploy-path", bad).returncode == 2, bad
    _happy_plan(devrig)
    custom = devrig.tmp / "somewhere" / "checkout"
    done = devrig.run(*_dev_args(stack), "--deploy-path", str(custom))
    assert done.returncode == 0 and (custom / "infra/deploy/env/alpha.env").is_file() and not devrig.deploy.exists()
    assert f"variable DEPLOY_PATH={custom}" in done.stdout


def test_a_run_that_is_already_working_stops_a_second_before_it_makes_a_clone(devrig: Rig, stack) -> None:
    import fcntl

    state = devrig.state_root / "auditmanager"
    state.mkdir(parents=True)
    with open(state / "first-install.lock", "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        done = devrig.run(*_dev_args(stack))
    assert _stops(done)[-1][0] == "already_running" and not devrig.deploy.exists()


def test_an_installation_made_in_place_stays_where_it_is(rig: Rig, stack, tmp_path: Path) -> None:
    """A clone that already holds an installation is the deploy clone whatever its path, so a second stack is never started."""
    rig.plan("deploy", "1|stop here")
    first = rig.run(*_args(stack))
    assert _stops(first)[-1][0] == "deploy_failed"
    _happy_plan(rig)
    done = subprocess.run([str(rig.repo / "infra/deploy/first-install.sh"), "--email", EMAIL, "--http-port", str(stack.port), "--no-ci-key", "--deploy-mode", "github"],
                          capture_output=True, text=True, cwd=rig.repo, env=rig.env(FIRST_INSTALL_DEPLOY_ROOT=str(tmp_path / "elsewhere")))
    assert done.returncode == 0, done.stdout[-1500:]
    assert "making the deploy clone" not in done.stdout and not (tmp_path / "elsewhere").exists()


# ----------------------------------------------------- the bundle comes from the repository's release when it publishes one (FIRST-INSTALL-02)


def test_a_repository_that_publishes_no_bundle_skips_the_stage_with_one_owner_note(rig: Rig, stack) -> None:
    _happy_plan(rig)
    done = rig.run(*_args(stack))
    assert done.returncode == 0, done.stdout[-1500:]
    assert "skipped: no --norms-bundle, and the repository publishes none (no infra/norms/bundle-release.lock)" in done.stdout
    note = [line for line in done.stdout.splitlines() if line.startswith("  note")]
    assert len(note) == 1 and "no infra/norms/bundle-release.lock" in note[0] and "--norms-bundle DIRECTORY" in note[0]
    assert "s5=ok" not in (rig.state_root / "auditmanager" / "first-install.state").read_text()


def test_a_lock_that_does_not_hold_together_is_a_report_in_the_preflight_before_anything_is_built(rig: Rig, stack) -> None:
    rig.write_lock("lock_version=1\nrepo=acme-co/audit-install\ntag=norms-x\nbundle=not-a-bundle-name\n")
    code, text = _stops(rig.run(*_args(stack)))[-1]
    assert code == "norms_lock_invalid" and text.startswith("REPORT TO THE OWNER") and "bundle is not a bundle directory name" in text
    assert rig.calls() == []                                              # not a single deploy


def test_the_download_is_part_of_the_disk_the_preflight_asks_for_and_the_first_shortage_says_prune(rig: Rig, stack) -> None:
    rig.write_lock()
    low = rig.env(STUB_DF_BYTES=str(20 * 1024**3))
    first = _stops(rig.run(*_args(stack), env=low))[-1]
    assert first[0] == "norms_disk_low" and "docker builder prune -af" in first[1] and "ASK" not in first[1]
    needed = int(re.search(r"about (\d+) GiB are needed", first[1]).group(1))
    assert needed > 30                      # the images (8), the tar twice, the volumes' growth and the 3.9 GB that is downloaded
    second = _stops(rig.run(*_args(stack), env=low))[-1]
    assert second[0] == "norms_disk_too_small" and second[1].startswith("ASK THE OWNER for a larger disk")
    rig.plan("deploy", "1|stop here")
    assert _stops(rig.run(*_args(stack)))[-1][0] == "deploy_failed"       # with the room the install goes on


def test_zstd_is_one_of_the_tools_the_script_installs(rig: Rig, stack) -> None:
    done = rig.run(*_args(stack), env=rig.env(FIRST_INSTALL_FAKE_MISSING="zstd"))
    assert "apt-get -q -y install zstd" in _apt_log(rig)
    code, text = _stops(done)[-1]
    assert code == "tool_missing" and "apt-get update && apt-get install -y zstd" in text


def test_a_lock_that_arrives_after_the_installation_is_picked_up_by_running_the_installer_again(rig: Rig, stack) -> None:
    """Installed with nothing published; the owner publishes, the lock reaches the deploy clone, and no option is needed."""
    _happy_plan(rig)
    assert rig.run(*_args(stack)).returncode == 0
    assert _stops(rig.run(*_args(stack)))[-1][0] == "already_installed"
    rig.write_lock()
    again = rig.run(*_args(stack))
    codes = [code for code, _ in _stops(again)]
    assert "already_installed" not in codes, again.stdout[-1200:]
    assert "this server was installed without the norms: adding them" in again.stdout and "[5/12]" in again.stdout
    assert "norms: the release norms-0a1bafe103ff-77777777 of acme-co/audit-install" in again.stdout
    assert codes[-1] == "norms_download_failed"            # nothing listens where the stand-in release would be: a run again, not a report
    assert "done before: skipped" in again.stdout


def test_dry_run_says_where_the_norms_come_from(rig: Rig, stack) -> None:
    assert "skipped (no --norms-bundle, and the repository publishes none)" in rig.run(*_args(stack, "--dry-run")).stdout
    rig.write_lock()
    plan = rig.run(*_args(stack, "--dry-run")).stdout
    assert "download the parts of the release infra/norms/bundle-release.lock names" in plan and "delete the parts" in plan
    assert "run the two gates of NORM-VECTOR-TEMP-01" in plan
    assert "verify /x" in rig.run(*_args(stack, "--dry-run", "--norms-bundle", str(rig.tmp))).stdout.replace(str(rig.tmp), "/x")


# ------------------------------------------------------------------------------------- --deploy-mode: how pushes to main arrive

UNIT = "auditmanager-deploy-local"


def _local_args(stack, *extra: str) -> list[str]:
    """The default mode (local): no --deploy-mode, and no --no-ci-key either, which proves no key is made."""
    return ["--email", EMAIL, "--http-port", str(stack.port), *extra]


def _systemctl(rig: Rig) -> list[str]:
    path = rig.stub / "systemctl.log"
    return path.read_text().splitlines() if path.exists() else []


def _marker(rig: Rig) -> dict[str, str]:
    text = (rig.state_root / "auditmanager" / "first-install.done").read_text()
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


def test_local_is_the_default_mode_it_writes_the_units_outside_the_checkout_and_enables_the_timer_last(rig: Rig, stack) -> None:
    _happy_plan(rig)
    done = rig.run(*_local_args(stack))
    assert done.returncode == 0, done.stdout[-2500:]
    out = done.stdout
    # the units: this instance, this checkout, in the systemd directory, not in the clone
    service = (rig.systemd_dir / f"{UNIT}.service").read_text()
    timer = (rig.systemd_dir / f"{UNIT}.timer").read_text()
    assert f"ExecStart={rig.repo}/infra/deploy/deploy-local.sh --if-moved --deploy-path {rig.repo}" in service
    assert "Type=oneshot" in service and "@" not in service + timer
    assert "OnCalendar=*:0/5" in timer and "Persistent=true" in timer and f"Unit={UNIT}.service" in timer
    assert stat.S_IMODE((rig.systemd_dir / f"{UNIT}.timer").stat().st_mode) == 0o644
    assert rig.clean() and not list(rig.repo.rglob("*.timer.*"))
    # systemd was told, in this order, and the timer is enabled and started
    log = _systemctl(rig)
    assert [c for c in log if "deploy-local" in c or c == "systemctl daemon-reload"] == [
        "systemctl daemon-reload", f"systemctl enable --now {UNIT}.timer", f"systemctl is-active --quiet {UNIT}.timer"]
    # the owner block: how deploys happen, no GitHub step at all (its SSH deploy is opt-in), and nothing of the CI key
    assert "how this server deploys" in out and "push to main of acme-co/audit-install" in out and "within 5 minutes" in out
    assert f"sudo {rig.repo}/infra/deploy/deploy-local.sh" in out and f"DEPLOY_PATH={rig.repo}" in out
    assert "GitHub      nothing: this server needs no variable, secret or key in GitHub" in out and "STOP" not in out
    for absent in ("DEPLOY_KNOWN_HOSTS", "VPS_SSH_KEY", "VPS_USER", "variable DEPLOY_HOST", "DEPLOY_MODE", "set the repository variable"):
        assert absent not in out
    assert not (rig.secret_dir / "auditmanager-deploy-key").exists() and not (rig.auth_home / ".ssh").exists()
    # the timer is the last thing enabled: after the semantic stage, and before the marker
    assert out.index("[10/12]") < out.index("[11/12]") < out.index(f"the deploy timer {UNIT}.timer is enabled") < out.index("[12/12]")
    assert out.index(f"the deploy timer {UNIT}.timer is enabled") < out.index("marker written")
    last = [line for line in out.splitlines() if line.strip()][-1]
    assert last.startswith("DONE: auditmanager is installed") and "within 5 minutes" in last and "nothing is needed in GitHub" in last and "DEPLOY_MODE" not in last
    # what the timer will accept is recorded outside the checkout, and the marker says the mode
    assert (rig.state_root / "auditmanager" / "deploy-local.source").read_text().strip() == "acme-co/audit-install"
    marker = _marker(rig)
    assert marker["deploy_mode"] == "local" and marker["stage_11_timer"] == "enabled"


def test_the_rendered_units_are_what_systemd_accepts(rig: Rig, stack) -> None:
    if shutil.which("systemd-analyze") is None:
        pytest.skip("systemd-analyze is not installed")
    _happy_plan(rig)
    assert rig.run(*_local_args(stack)).returncode == 0
    calendar = subprocess.run(["systemd-analyze", "calendar", "*:0/5"], capture_output=True, text=True)
    assert calendar.returncode == 0 and "Normalized form: *-*-* *:00/5:00" in calendar.stdout, calendar.stdout + calendar.stderr
    # the service file parses and its program exists; the units named in After= belong to the real host, not to this one
    verify = subprocess.run(["systemd-analyze", "verify", "--man=no", str(rig.systemd_dir / f"{UNIT}.service")],
                            capture_output=True, text=True)
    complaints = [line for line in (verify.stdout + verify.stderr).splitlines()
                  if line.strip() and "docker.service" not in line and "network-online" not in line]
    assert not complaints, complaints


def test_github_mode_is_the_earlier_behaviour_and_no_timer_is_made(rig: Rig, stack) -> None:
    _happy_plan(rig)
    done = rig.run(*_args(stack))
    assert done.returncode == 0, done.stdout[-2500:]
    assert "variable DEPLOY_HOST=" in done.stdout and "secret   VPS_SSH_KEY=" in done.stdout
    # the opt-in comes first, with the values and the secrets it goes with
    assert done.stdout.index("variable DEPLOY_MODE=github") < done.stdout.index("variable DEPLOY_HOST=")
    assert "DEPLOY_* variables below and the VPS_* secrets" in done.stdout
    assert "how this server deploys" not in done.stdout and "DEPLOY_MODE=local" not in done.stdout
    assert not rig.systemd_dir.exists() or not any(rig.systemd_dir.iterdir())
    assert not any(UNIT in line for line in _systemctl(rig))
    assert not (rig.state_root / "auditmanager" / "deploy-local.source").exists()
    marker = _marker(rig)
    assert marker["deploy_mode"] == "github" and marker["stage_11_timer"] == "disabled"
    last = [line for line in done.stdout.splitlines() if line.strip()][-1]
    assert last.startswith("DONE:") and "GitHub's workflow" in last and "DEPLOY_MODE=github" in last and "VPS_* secrets" in last


def test_a_bad_deploy_mode_is_a_usage_error_and_the_dry_run_names_the_mode(rig: Rig, stack) -> None:
    assert rig.run(*_local_args(stack, "--deploy-mode", "both")).returncode == 2
    assert rig.run(*_local_args(stack, "--deploy-mode")).returncode == 2
    before = sorted(str(p) for p in rig.tmp.rglob("*"))
    local = rig.run(*_local_args(stack, "--dry-run")).stdout
    assert "deploy mode      local" in local and f"{UNIT}.timer" in local and "nothing is needed in GitHub" in local and "DEPLOY_MODE" not in local
    github = rig.run(*_args(stack, "--dry-run")).stdout
    assert "deploy mode      github" in github and "no timer is enabled in github mode" in github and "DEPLOY_KNOWN_HOSTS" in github
    assert "DEPLOY_MODE=github (the opt-in)" in github
    assert sorted(str(p) for p in rig.tmp.rglob("*")) == before


def test_a_rerun_converges_and_the_mode_switches_both_ways(rig: Rig, stack) -> None:
    _happy_plan(rig)
    assert rig.run(*_local_args(stack)).returncode == 0
    units = {n: (rig.systemd_dir / f"{UNIT}.{n}").read_bytes() for n in ("service", "timer")}
    reloads = [c for c in _systemctl(rig) if c == "systemctl daemon-reload"]
    deploys = len(rig.calls())
    # the same mode again: a finished installation refuses, as ever; the stage that follows the mode, run alone, changes nothing
    assert _stops(rig.run(*_local_args(stack)))[-1][0] == "already_installed"
    assert rig.run(*_local_args(stack, "--resume-stage", "9")).returncode == 0
    assert {n: (rig.systemd_dir / f"{UNIT}.{n}").read_bytes() for n in ("service", "timer")} == units
    assert [c for c in _systemctl(rig) if c == "systemctl daemon-reload"] == reloads, "an unchanged unit must not be reloaded"
    # a stale unit file is brought back, and only then is systemd told
    (rig.systemd_dir / f"{UNIT}.timer").write_text("[Timer]\nOnCalendar=daily\n")
    assert rig.run(*_local_args(stack, "--resume-stage", "9")).returncode == 0
    assert (rig.systemd_dir / f"{UNIT}.timer").read_bytes() == units["timer"]
    assert len([c for c in _systemctl(rig) if c == "systemctl daemon-reload"]) == len(reloads) + 1
    # local -> github: asked for explicitly, the timer is disabled, its files stay, the GitHub values and a key come; nothing is redeployed
    to_github = rig.run(*_local_args(stack, "--deploy-mode", "github"))
    assert to_github.returncode == 0, to_github.stdout[-2000:]
    assert "installed with --deploy-mode local: switching to github" in to_github.stdout
    assert _systemctl(rig)[-1] == f"systemctl disable --now {UNIT}.timer"
    assert (rig.systemd_dir / f"{UNIT}.timer").exists() and "variable DEPLOY_HOST=" in to_github.stdout
    assert "variable DEPLOY_MODE=github" in to_github.stdout
    assert (rig.secret_dir / "auditmanager-deploy-key").exists()
    assert _marker(rig)["deploy_mode"] == "github" and _marker(rig)["stage_11_timer"] == "disabled"
    assert len(rig.calls()) == deploys, "switching the mode must not run the deploy or the verification again"
    assert _stops(rig.run(*_local_args(stack, "--deploy-mode", "github")))[-1][0] == "already_installed"
    assert _stops(rig.run(*_local_args(stack)))[-1][0] == "already_installed"  # no option: the recorded mode (github) stands
    # github -> local: the timer is enabled again, the key of the earlier mode is left and named
    to_local = rig.run(*_local_args(stack, "--deploy-mode", "local"))
    assert to_local.returncode == 0, to_local.stdout[-2000:]
    assert "installed with --deploy-mode github: switching to local" in to_local.stdout
    assert _systemctl(rig)[-2:] == [f"systemctl enable --now {UNIT}.timer", f"systemctl is-active --quiet {UNIT}.timer"]
    assert "a deploy key from an earlier GitHub-mode run is left in place" in to_local.stdout
    assert (rig.secret_dir / "auditmanager-deploy-key").exists()
    assert _marker(rig)["deploy_mode"] == "local" and len(rig.calls()) == deploys


def test_a_marker_from_before_the_modes_means_github_and_is_switched_only_when_asked(rig: Rig, stack) -> None:
    _happy_plan(rig)
    assert rig.run(*_args(stack)).returncode == 0
    marker = rig.state_root / "auditmanager" / "first-install.done"
    marker.write_text("".join(line + "\n" for line in marker.read_text().splitlines()
                              if not line.startswith(("deploy_mode=", "stage_11_timer=", "stage_9_deploy_info="))))
    assert _stops(rig.run(*_local_args(stack)))[-1][0] == "already_installed"      # nothing asked: the old installation stays as it is
    assert not (rig.systemd_dir / f"{UNIT}.timer").exists()
    switched = rig.run(*_local_args(stack, "--deploy-mode", "local"))
    assert switched.returncode == 0 and "installed with --deploy-mode github: switching to local" in switched.stdout
    assert (rig.systemd_dir / f"{UNIT}.timer").exists() and _marker(rig)["deploy_mode"] == "local"


def test_a_timer_that_cannot_be_enabled_is_the_last_stop_and_the_rerun_finishes(rig: Rig, stack) -> None:
    _happy_plan(rig)
    failed = rig.run(*_local_args(stack), env=rig.env(STUB_SYSTEMCTL_FAIL=f"enable --now {UNIT}.timer"))
    code, text = _stops(failed)[-1]
    assert failed.returncode == 10 and code == "deploy_timer_failed" and text.startswith("REPORT TO THE OWNER"), failed.stdout[-1500:]
    assert f"systemctl enable --now {UNIT}.timer failed" in text
    assert not (rig.state_root / "auditmanager" / "first-install.done").exists() and "DONE:" not in failed.stdout
    again = rig.run(*_local_args(stack))
    assert again.returncode == 0 and "DONE:" in again.stdout and _marker(rig)["stage_11_timer"] == "enabled"
    assert "done before: skipped" in again.stdout and len([c for c in rig.calls() if c.startswith("deploy")]) == 2


def test_the_installer_refuses_while_a_timer_deploy_runs_and_a_deploy_started_inside_it_is_refused(rig: Rig, stack) -> None:
    import fcntl

    state = rig.state_root / "auditmanager"
    state.mkdir(parents=True)
    with open(state / "deploy-local.lock", "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        busy = rig.run(*_local_args(stack))
    code, text = _stops(busy)[-1]
    assert busy.returncode == 10 and code == "deploy_local_running" and "auditmanager-deploy-local.log" in text, busy.stdout[-800:]
    assert not rig.calls() and not (rig.repo / "infra/deploy/env/alpha.env").exists()
    # the other way round: deploy-local.sh, started by hand while the installer works (here from inside its deploy stage), waits its turn
    _happy_plan(rig)
    hook = (f'DEPLOY_LOCAL_TEST_MODE=1 DEPLOY_LOCAL_STATE_ROOT="{rig.state_root}" DEPLOY_LOCAL_LOG_DIR="{rig.log_dir}" '
            f'"{rig.repo}/infra/deploy/deploy-local.sh" --deploy-path "{rig.repo}"')
    done = rig.run(*_local_args(stack), env=rig.env(STUB_ON_DEPLOY=hook))
    assert done.returncode == 0, done.stdout[-1500:]
    assert (rig.stub / "on-deploy.rc").read_text().strip() == "75"
    assert "busy:" in (rig.stub / "on-deploy.out").read_text()


def test_started_in_a_working_copy_the_timer_belongs_to_the_deploy_clone_and_the_locks_cross_the_exec(devrig: Rig, stack) -> None:
    _happy_plan(devrig)
    done = devrig.run(*_local_args(stack))
    assert done.returncode == 0, done.stdout[-3000:]
    service = (devrig.systemd_dir / f"{UNIT}.service").read_text()
    assert f"ExecStart={devrig.deploy}/infra/deploy/deploy-local.sh --if-moved --deploy-path {devrig.deploy}" in service
    assert str(devrig.dev) not in service and devrig.clean()
    assert f"DEPLOY_PATH={devrig.deploy}" in done.stdout and f"sudo {devrig.deploy}/infra/deploy/deploy-local.sh" in done.stdout
    assert (devrig.state_root / "auditmanager" / "deploy-local.source").read_text().strip() == "acme-co/audit-install"
