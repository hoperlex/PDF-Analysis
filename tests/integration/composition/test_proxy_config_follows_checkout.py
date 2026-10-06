"""`W49-FIX` / `B-1` -- the deployed proxy serves the configuration of the checkout it was
deployed from, and `verify-deployed.sh` refuses a deployment whose proxy does not.

**The defect, measured twice before this file existed.** `compose.server.yml` bind-mounts
`proxy/nginx.conf` into the proxy as a SINGLE FILE. A single-file bind mount is pinned to the
inode the file had when the container started. The auto-deploy updates the host with
`git checkout --detach`, and git does not rewrite a changed file in place: it writes a new
file and renames it over the path, so the path gets a NEW inode (`W49-JUDGE-Y` measured the git
half; `W49-JUDGE-X` §7.4 the docker half on the pinned image: inode 2132108 -> 2132118, and
after `nginx -s reload` the running proxy still answered from the old file). `reload-proxy.sh`
then tested the old file, reloaded the old file and reported success, and `verify-deployed.sh`
compared only the images and called the stack this tree -- so `W49-EDGE-01`'s registration
throttle would have been absent behind a green deploy.

**What is here.**

1. A gate-resident model of that mechanism. The `docker` stub keeps the proxy's view of each
   mounted file as a HARD LINK taken when the container (re)started. A hard link is the
   inode, not the path: when `git checkout` replaces the file, the link still holds the old
   bytes, exactly as the bind mount does, and an in-place write would show through it, exactly
   as it would through the mount. Only `restart` re-links. Nothing else in the stub can
   change what the proxy reads, so the stub cannot hand the scripts a repair they did not
   make. Git and the filesystem are real; only the daemon is stood in for.
2. An opt-in drive against REAL containers on a disposable stand, with the burst probe the
   deploy scripts must not carry (`verify-deployed.sh` runs on every production deploy, and a
   429 burst against the live stand is a side effect). Skipped unless asked for::

       AUDITMANAGER_PROXY_STAND=1 \\
       AUDITMANAGER_PROXY_STAND_DIR=<a directory the docker daemon can see, not under /tmp> \\
       AUDITMANAGER_PROXY_STAND_PORT=<a free loopback port this lane owns> \\
       AUDITMANAGER_PROXY_STAND_INSTANCE=<a compose project name this lane owns> \\
       .venv/bin/pytest tests/integration/composition/test_proxy_config_follows_checkout.py -s

   It runs the tree's own `deploy.sh`, `reload-proxy.sh` and `verify-deployed.sh` against a
   stand whose proxy is `compose.server.yml`'s (same pinned image, same mount line) and whose
   api, web, postgres and s3 are stand-ins built from that same image. The stand-in api answers
   the two questions `deploy.sh` asks the application image -- the database check and the
   conformance check -- with their success lines, because there is no application in it; what
   is measured is the proxy path, and nothing about the application is claimed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEPLOY_DIR = ROOT / "infra/deploy"
PROXY_INSIDE = "/etc/nginx/conf.d/default.conf"

AGREES = 0
INVALID = 5
DRIFT = 6

#: The step `W49-FIX` added, delimited so a mutant can delete exactly it.
RESTART_STEP = re.compile(
    r"^    # >>> step: restart-on-stale\n.*?^    # <<< step: restart-on-stale\n",
    re.DOTALL | re.MULTILINE,
)

CONF_A = "# version A -- the configuration the proxy was started with\nserver { listen 8080; }\n"
CONF_B = (
    "# version B -- what the deploy checked out\n"
    "server { listen 8080; location /api/v1/ { limit_req zone=guest_registration; } }\n"
)
CONF_BROKEN = "# version C -- BROKEN on purpose\nserver { listen 8080\n"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=w49@fix", "-c", "user.name=w49fix", *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _verbs(calls: str) -> list[str]:
    """The docker sub-command of each call -- its first word. Matching on the whole line
    would also match a temporary directory named after the test."""
    return [line.split()[0] for line in calls.splitlines() if line.strip()]


def _restart_removed(source: str) -> str:
    mutated, count = RESTART_STEP.subn("", source)
    assert count == 1, "reload-proxy.sh no longer carries exactly one restart-on-stale step"
    return mutated


# --- 1. the gate-resident model --------------------------------------------------------

#: A `docker` that holds the proxy's view of each mounted file as a hard link -- the inode --
#: taken at (re)start. `nginx -s reload` changes nothing it reads, which is X's second half.
DOCKER_STUB = r'''#!/usr/bin/env python3
"""A `docker` whose proxy reads hard links -- inodes -- and reaches no daemon."""
import hashlib, json, os, pathlib, sys

argv = sys.argv[1:]
line = " ".join(argv)
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as handle:
    handle.write(line + "\n")

STATE = pathlib.Path(os.environ["STUB_STATE"])
IMAGE = pathlib.Path(os.environ["STUB_IMAGE"])
PROXY = STATE / "proxy.json"
proxy = json.loads(PROXY.read_text(encoding="utf-8"))


def save():
    PROXY.write_text(json.dumps(proxy), encoding="utf-8")


def pin(index):
    return STATE / ("pinned-%d" % index)


def seen(destination):
    for index, (_, mounted_at) in enumerate(proxy["mounts"]):
        if mounted_at == destination:
            return pin(index)
    return None


if argv[:1] == ["compose"]:
    if "ps" in argv and "--quiet" in argv:
        print("container-" + argv[-1])
    sys.exit(0)

if argv[:1] == ["inspect"]:
    fmt = argv[2] if argv[1:2] == ["--format"] else ""
    if ".Mounts" in fmt:
        for source, destination in proxy["mounts"]:
            print("%s\t%s" % (source, destination))
    elif ".Networks" in fmt:
        print("an-instance-net")
    elif ".Image" in fmt:
        print("sha256:the-pinned-nginx")
    sys.exit(0)

if argv[:1] == ["restart"]:
    # THE ONE THING THAT RE-RESOLVES A BIND MOUNT: each pin is re-linked to the inode its
    # path names NOW.
    for index, (source, _) in enumerate(proxy["mounts"]):
        if pin(index).exists():
            pin(index).unlink()
        os.link(source, pin(index))
    proxy["starts"] += 1
    save()
    print(argv[-1])
    sys.exit(0)

if argv[:1] == ["run"]:
    # The throwaway container: it mounts the PATHS, so it reads what the checkout holds.
    sources = [argv[i + 1].split(":")[0] for i, word in enumerate(argv) if word == "-v"]
    broken = [s for s in sources if "BROKEN" in pathlib.Path(s).read_text(encoding="utf-8")]
    sys.exit(1 if broken else 0)

if argv[:1] == ["exec"]:
    container = argv[2] if argv[1] == "-i" else argv[1]
    if "nginx" in argv:
        if "-t" in argv:
            # The running proxy tests what IT reads, which is the pinned inode.
            pins = [pin(i) for i in range(len(proxy["mounts"]))]
            sys.exit(1 if any("BROKEN" in p.read_text(encoding="utf-8") for p in pins) else 0)
        proxy["reloads"] += 1
        save()
        sys.exit(0)
    if "sha256sum" in line:
        for raw in sys.stdin.buffer.read().split(b"\0"):
            path = raw.decode()
            if not path:
                continue
            if container == "container-proxy":
                staged = seen(path)
            else:
                staged = IMAGE / path.lstrip("/")
            if staged is not None and staged.is_file():
                print("%s  %s" % (hashlib.sha256(staged.read_bytes()).hexdigest(), path))
        sys.exit(0)
    if "find" in line:
        root = line.split("find '", 1)[1].split("'", 1)[0]
        staged = IMAGE / root.lstrip("/")
        for path in sorted(staged.rglob("*")) if staged.is_dir() else []:
            if path.is_file():
                print("/" + str(path.relative_to(IMAGE)))
        sys.exit(0)
    sys.exit(0)

sys.exit(0)
'''

CURL_STUB = "#!/bin/sh\nprintf 401\n"

FAKE_DOCKERFILE_API = """\
FROM python:3.12-slim AS build
FROM python:3.12-slim
COPY src/ /app/src/
"""

FAKE_DOCKERFILE_WEB = """\
FROM node:24-bookworm-slim AS build
WORKDIR /web
COPY web/ ./
FROM node:24-bookworm-slim
COPY --from=build /web /web
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class _Host:
    """A clone at version A with version B one checkout away, and a proxy started at A."""

    def __init__(self, root: Path, reload_script: str | None = None) -> None:
        self.root = root
        self.repo = root / "repo"
        self.deploy = self.repo / "infra/deploy"
        self.conf = self.deploy / "proxy/nginx.conf"
        self.state = root / "state"
        self.image = root / "image"
        self.log = root / "docker-calls.log"
        self.calls_seen = 0

        _write(self.repo / "src/app.py", "the application\n")
        _write(self.repo / "web/package.json", '{"name": "web"}\n')
        for name in ("verify-deployed.sh", "reload-proxy.sh"):
            _write(self.deploy / name, (DEPLOY_DIR / name).read_text(encoding="utf-8"))
        _write(self.deploy / "compose.server.yml", "# stub\n")
        _write(self.deploy / "Dockerfile.api", FAKE_DOCKERFILE_API)
        _write(self.deploy / "Dockerfile.web", FAKE_DOCKERFILE_WEB)
        _write(self.deploy / "env/alpha.env", "ALPHA_INSTANCE=an-instance\nALPHA_HTTP_PORT=31599\n")
        _write(self.conf, CONF_A)
        _git(self.repo, "init", "-q")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "A")
        self.commit_a = _git(self.repo, "rev-parse", "HEAD").strip()
        _write(self.conf, CONF_B)
        _git(self.repo, "commit", "-qam", "B")
        self.commit_b = _git(self.repo, "rev-parse", "HEAD").strip()
        _write(self.conf, CONF_BROKEN)
        _git(self.repo, "commit", "-qam", "C")
        self.commit_broken = _git(self.repo, "rev-parse", "HEAD").strip()
        self.checkout(self.commit_a)
        if reload_script is not None:
            (self.deploy / "reload-proxy.sh").write_text(reload_script, encoding="utf-8")

        # The images agree with the tree, so every disagreement below is the proxy's.
        _write(self.image / "app/src/app.py", "the application\n")
        _write(self.image / "web/package.json", '{"name": "web"}\n')

        # The proxy, started now: its view of nginx.conf is the inode the path names now.
        self.state.mkdir()
        os.link(self.conf, self.state / "pinned-0")
        (self.state / "proxy.json").write_text(
            json.dumps(
                {"mounts": [[str(self.conf), PROXY_INSIDE]], "starts": 1, "reloads": 0}
            ),
            encoding="utf-8",
        )

        self.bin = root / "bin"
        self.bin.mkdir()
        for name, body in (("docker", DOCKER_STUB), ("curl", CURL_STUB)):
            (self.bin / name).write_text(body, encoding="utf-8")
            (self.bin / name).chmod(0o755)

    def checkout(self, commit: str) -> None:
        _git(self.repo, "checkout", "-q", "--detach", commit)

    def inode(self) -> int:
        return self.conf.stat().st_ino

    def proxy_reads(self) -> str:
        return (self.state / "pinned-0").read_text(encoding="utf-8")

    def proxy(self) -> dict:
        return json.loads((self.state / "proxy.json").read_text(encoding="utf-8"))

    def run(self, script: str) -> tuple[subprocess.CompletedProcess[str], str]:
        """One script, and the docker calls it made (only its own, not earlier ones)."""
        environment = dict(os.environ)
        environment["PATH"] = f"{self.bin}{os.pathsep}{environment['PATH']}"
        environment["STUB_LOG"] = str(self.log)
        environment["STUB_STATE"] = str(self.state)
        environment["STUB_IMAGE"] = str(self.image)
        environment["ALPHA_ENV_FILE"] = str(self.deploy / "env/alpha.env")
        completed = subprocess.run(
            ["bash", str(self.deploy / script)],
            capture_output=True,
            text=True,
            env=environment,
            timeout=180,
        )
        lines = self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []
        calls = "\n".join(lines[self.calls_seen :])
        self.calls_seen = len(lines)
        return completed, calls


@pytest.fixture()
def host(tmp_path: Path) -> _Host:
    return _Host(tmp_path)


class TestTheDefectIsReproducedFirst:
    """Both halves of `B-1`, before any repair is asked to do anything. Without these the
    green cases below could be green because the model never went stale."""

    def test_a_checkout_gives_the_mounted_file_a_new_inode(self, host: _Host) -> None:
        """The git half, on this filesystem with this git -- nothing stubbed."""
        before = host.inode()
        host.checkout(host.commit_b)
        assert host.inode() != before, "git rewrote the file in place; the premise is gone"
        assert host.conf.read_text(encoding="utf-8") == CONF_B

    def test_the_running_proxy_keeps_reading_the_old_file_through_a_reload(
        self, host: _Host
    ) -> None:
        """The docker half: the view is the inode, and a reload re-reads that inode."""
        host.checkout(host.commit_b)
        assert host.proxy_reads() == CONF_A
        mutant = _restart_removed((DEPLOY_DIR / "reload-proxy.sh").read_text(encoding="utf-8"))
        (host.deploy / "reload-proxy.sh").write_text(mutant, encoding="utf-8")
        host.run("reload-proxy.sh")
        assert host.proxy_reads() == CONF_A, "a reload changed what the proxy reads"

    def test_the_new_probe_names_the_stale_configuration(self, host: _Host) -> None:
        host.checkout(host.commit_b)
        completed, _ = host.run("verify-deployed.sh")
        assert completed.returncode == DRIFT, (completed.stdout, completed.stderr)
        assert f"{PROXY_INSIDE}  DIFFERENT BYTES" in completed.stdout, completed.stdout
        assert f"tree  {_sha(host.conf)}" in completed.stdout, completed.stdout
        assert "NOT serving this tree's configuration" in completed.stderr, completed.stderr

    def test_the_probe_is_green_on_a_proxy_started_from_this_checkout(
        self, host: _Host
    ) -> None:
        """The control. Without it, a probe that refused everything would look correct."""
        completed, _ = host.run("verify-deployed.sh")
        assert completed.returncode == AGREES, (completed.stdout, completed.stderr)
        assert "IS this tree" in completed.stdout, completed.stdout


class TestTheRepair:
    def test_reload_proxy_restarts_a_proxy_reading_a_replaced_file(self, host: _Host) -> None:
        host.checkout(host.commit_b)
        completed, calls = host.run("reload-proxy.sh")
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "was restarted" in completed.stdout, completed.stdout
        assert host.proxy_reads() == CONF_B
        assert host.proxy()["starts"] == 2
        # The new configuration was tested BEFORE the running proxy was touched, and the
        # upstreams were re-resolved after.
        order = _verbs(calls)
        assert order.index("run") < order.index("restart"), calls
        after_restart = calls.splitlines()[order.index("restart") + 1 :]
        assert any("nginx -s reload" in call for call in after_restart), calls

    def test_after_the_repair_the_probe_agrees(self, host: _Host) -> None:
        host.checkout(host.commit_b)
        host.run("reload-proxy.sh")
        completed, _ = host.run("verify-deployed.sh")
        assert completed.returncode == AGREES, (completed.stdout, completed.stderr)
        assert "infra/deploy/proxy/" in completed.stdout and "identical" in completed.stdout

    def test_without_the_restart_step_the_reload_fails_and_the_probe_stays_red(
        self, host: _Host
    ) -> None:
        """THE MUTATION `W49-FIX` REQUIRES. Delete the restart and what is left is the
        old `reload-proxy.sh` with eyes: it sees the stale file, cannot repair it, and
        refuses to report success -- and the probe stays red."""
        mutant = _restart_removed((DEPLOY_DIR / "reload-proxy.sh").read_text(encoding="utf-8"))
        (host.deploy / "reload-proxy.sh").write_text(mutant, encoding="utf-8")
        host.checkout(host.commit_b)
        completed, calls = host.run("reload-proxy.sh")
        assert completed.returncode == DRIFT, (completed.stdout, completed.stderr)
        assert "still does not read this checkout's configuration" in completed.stderr
        assert "restart" not in _verbs(calls), calls
        probe, _ = host.run("verify-deployed.sh")
        assert probe.returncode == DRIFT, (probe.stdout, probe.stderr)
        assert f"{PROXY_INSIDE}  DIFFERENT BYTES" in probe.stdout, probe.stdout


class TestAnUnchangedConfigurationRestartsNothing:
    """`W24-IDEM`'s rule, for the step `W49-FIX` added. The comparison is the only thing
    that decides a restart."""

    def test_a_proxy_already_reading_the_checkout_is_only_reloaded(self, host: _Host) -> None:
        completed, calls = host.run("reload-proxy.sh")
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "restart" not in _verbs(calls) and "run" not in _verbs(calls), calls
        assert "nginx -s reload" in calls, calls
        assert host.proxy()["starts"] == 1

    def test_a_second_run_after_the_repair_restarts_nothing(self, host: _Host) -> None:
        host.checkout(host.commit_b)
        host.run("reload-proxy.sh")
        assert host.proxy()["starts"] == 2
        completed, calls = host.run("reload-proxy.sh")
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "restart" not in _verbs(calls), calls
        assert host.proxy()["starts"] == 2

    def test_an_in_place_edit_is_seen_without_a_restart(self, host: _Host) -> None:
        """The model is the mount, not a rule about checkouts: a write to the same inode
        shows through, and then there is nothing to restart for."""
        with host.conf.open("w", encoding="utf-8") as handle:
            handle.write(CONF_B)
        assert host.proxy_reads() == CONF_B
        completed, calls = host.run("reload-proxy.sh")
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "restart" not in _verbs(calls), calls


class TestABrokenConfigurationIsNeverRestartedInto:
    """A reload with a broken file was refused by nginx and the old workers kept serving.
    A restart has no such safety, so the checkout's configuration is tested first, in a
    throwaway container, and a failure leaves the running proxy alone."""

    def test_it_is_refused_before_the_restart(self, host: _Host) -> None:
        host.checkout(host.commit_broken)
        completed, calls = host.run("reload-proxy.sh")
        assert completed.returncode == INVALID, (completed.stdout, completed.stderr)
        assert "not valid" in completed.stderr, completed.stderr
        assert "was NOT restarted" in completed.stderr, completed.stderr
        assert "restart" not in _verbs(calls) and "nginx -s reload" not in calls, calls
        assert host.proxy_reads() == CONF_A, "the running proxy was touched"


def test_the_restart_step_is_one_marked_block() -> None:
    """What the mutation above deletes exists, once, and is the `docker restart`."""
    source = (DEPLOY_DIR / "reload-proxy.sh").read_text(encoding="utf-8")
    block = RESTART_STEP.search(source)
    assert block is not None
    assert 'docker restart "$PROXY"' in block.group(0)
    assert 'docker restart "$PROXY"' not in _restart_removed(source)


def test_deploy_still_hands_the_proxy_to_reload_proxy() -> None:
    """`deploy.sh` picks up a changed `proxy/**` only through `reload-proxy.sh`."""
    script = (DEPLOY_DIR / "deploy.sh").read_text(encoding="utf-8")
    assert '"$HERE/reload-proxy.sh" --env-file "$ENV_FILE"' in script


# --- 2. the disposable stand, opt-in ---------------------------------------------------

STAND_FLAG = "AUDITMANAGER_PROXY_STAND"


def _stand_settings() -> tuple[Path, int, str]:
    if os.environ.get(STAND_FLAG) != "1":
        pytest.skip(
            f"the disposable proxy stand is opt-in: set {STAND_FLAG}=1 with "
            f"{STAND_FLAG}_DIR, {STAND_FLAG}_PORT and {STAND_FLAG}_INSTANCE. It starts "
            "real containers."
        )
    missing = [
        name
        for name in (f"{STAND_FLAG}_DIR", f"{STAND_FLAG}_PORT", f"{STAND_FLAG}_INSTANCE")
        if not os.environ.get(name)
    ]
    assert not missing, f"the stand needs {missing}; nothing was started"
    directory = Path(os.environ[f"{STAND_FLAG}_DIR"]).resolve()
    # `OPERATING_CONSTRAINTS.md` section 1: the snap daemon cannot see /tmp, and a bind source
    # it cannot see becomes an empty directory rather than an error.
    assert not str(directory).startswith("/tmp"), f"{directory} is under /tmp"
    return directory, int(os.environ[f"{STAND_FLAG}_PORT"]), os.environ[f"{STAND_FLAG}_INSTANCE"]


def _pinned_nginx() -> str:
    text = (DEPLOY_DIR / "compose.server.yml").read_text(encoding="utf-8")
    found = re.findall(r"image: (nginx:[^\s]+@sha256:[0-9a-f]{64})", text)
    assert len(found) == 1, found
    return found[0]


STAND_COMPOSE = """\
# A DISPOSABLE STAND for W49-FIX. The proxy is compose.server.yml's: the same pinned image and
# the same single-file mount line. Everything else is a stand-in built from that image.
name: ${{ALPHA_INSTANCE:?unset}}
networks:
  alpha:
    name: ${{ALPHA_INSTANCE:?unset}}-net
services:
  postgres:
    image: {image}
    networks: [alpha]
  s3:
    image: {image}
    networks: [alpha]
  api:
    build:
      context: ../..
      dockerfile: infra/deploy/Dockerfile.api
    image: ${{ALPHA_INSTANCE:?unset}}-api
    networks: [alpha]
  web:
    build:
      context: ../..
      dockerfile: infra/deploy/Dockerfile.web
    image: ${{ALPHA_INSTANCE:?unset}}-web
    networks: [alpha]
  proxy:
    image: {image}
    networks: [alpha]
    restart: unless-stopped
    depends_on: [api, web]
    volumes:
      - ./proxy/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "127.0.0.1:${{ALPHA_HTTP_PORT:?unset}}:8080"
"""

STAND_DOCKERFILE_API = """\
FROM {image} AS build
FROM {image}
COPY src/ /app/src/
COPY infra/deploy/stand/api.conf /etc/nginx/conf.d/default.conf
COPY infra/deploy/stand/python /usr/local/bin/python
"""

STAND_DOCKERFILE_WEB = """\
FROM {image} AS build
WORKDIR /web
COPY web/ ./
FROM {image}
COPY --from=build /web /web
COPY infra/deploy/stand/web.conf /etc/nginx/conf.d/default.conf
"""

#: The stand-in api answers 401 to everything, which is what the real one answers on the
#: two paths the stand asks: `/openapi.json` without a credential, and the status read.
STAND_API_CONF = """\
server {
    listen 8000;
    default_type application/json;
    location / { return 401 '{"error_code":"authentication_required","stand":"api"}'; }
}
"""

STAND_WEB_CONF = """\
server {
    listen 3000;
    location / { return 200 'stand web'; }
}
"""

#: NOT AN APPLICATION. `deploy.sh` asks the api image two things -- the database check and
#: the conformance check -- and there is no application here to answer them. This answers
#: both with their success lines so the drive reaches the proxy step; nothing about the
#: application is claimed by a stand run. It never reads its standard input: `deploy.sh`
#: pipes nothing into the conformance check since `R-31`, and a read would wait forever on
#: whatever stdin the drive was started with.
STAND_PYTHON = """\
#!/bin/sh
case "$*" in
    *auditmanager.shared.db.check*) echo "FOUNDATION-CHECK OK check-db" ;;
    *) echo "differences: 0 (stand-in: there is no application here)" ;;
esac
"""

STAND_SECRETS = {
    "POSTGRES_PASSWORD": "stand-postgres-password",
    "MINIO_ROOT_USER": "stand-minio-root",
    "MINIO_ROOT_PASSWORD": "stand-minio-password",
    "AUDITMANAGER_API_TOKEN": "stand-token-that-reaches-nothing",
}


class Stand:
    """A git clone with the proxy configuration at A (no throttle) and B (the tree's), and a
    compose project that `deploy.sh` brings up exactly as it brings up the alpha stack.

    `scripts` is where `deploy.sh` and `reload-proxy.sh` come from (the tree's by default);
    `probe` is the `verify-deployed.sh` that is asked. Both are parameters so the same stand
    can be driven with the scripts as they were before the repair.
    """

    def __init__(
        self,
        directory: Path,
        port: int,
        instance: str,
        scripts: Path = DEPLOY_DIR,
        probe: Path = DEPLOY_DIR / "verify-deployed.sh",
    ) -> None:
        self.root = directory / f"stand-{instance}"
        self.repo = self.root / "repo"
        self.deploy = self.repo / "infra/deploy"
        self.conf = self.deploy / "proxy/nginx.conf"
        self.env = self.deploy / "env/alpha.env"
        self.port = port
        self.instance = instance
        self.scripts = scripts
        self.probe = probe

    # -- building -------------------------------------------------------------------
    def build(self) -> None:
        assert not self.root.exists(), f"{self.root} exists; a stand is never reused"
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", self.port)) != 0, (
                f"port {self.port} is in use; this stand takes no port it does not own"
            )
        image = _pinned_nginx()
        conf_b = (DEPLOY_DIR / "proxy/nginx.conf").read_text(encoding="utf-8")
        throttle = "        limit_req zone=guest_registration burst=10 nodelay;\n"
        assert conf_b.count(throttle) == 1, "the throttle line moved; the stand cannot make A"
        conf_a = conf_b.replace(throttle, "")

        _write(self.repo / ".gitignore", "infra/deploy/env/alpha.env\n")
        _write(self.repo / "src/stand.txt", "the stand-in api image carries this file\n")
        _write(self.repo / "web/package.json", '{"name": "stand-web"}\n')
        _write(self.repo / "tests/contract/api_v1/openapi_conformance.py", "# stand\n")
        for name in ("deploy.sh", "reload-proxy.sh"):
            _write(self.deploy / name, (self.scripts / name).read_text(encoding="utf-8"))
        _write(self.deploy / "verify-deployed.sh", self.probe.read_text(encoding="utf-8"))
        for name in ("deploy.sh", "reload-proxy.sh", "verify-deployed.sh"):
            (self.deploy / name).chmod(0o755)
        _write(self.deploy / "compose.server.yml", STAND_COMPOSE.format(image=image))
        _write(self.deploy / "Dockerfile.api", STAND_DOCKERFILE_API.format(image=image))
        _write(self.deploy / "Dockerfile.web", STAND_DOCKERFILE_WEB.format(image=image))
        _write(self.deploy / "stand/api.conf", STAND_API_CONF)
        _write(self.deploy / "stand/web.conf", STAND_WEB_CONF)
        _write(self.deploy / "stand/python", STAND_PYTHON)
        (self.deploy / "stand/python").chmod(0o755)
        _write(
            self.deploy / "env/alpha.env.example",
            "\n".join(f"{name}=change-me-{name.lower()}" for name in STAND_SECRETS) + "\n",
        )
        _write(
            self.env,
            "\n".join(
                [
                    f"ALPHA_INSTANCE={self.instance}",
                    f"ALPHA_HTTP_PORT={self.port}",
                    "POSTGRES_DB=stand",
                    "POSTGRES_USER=stand",
                    "S3_BUCKET=stand",
                    *(f"{name}={value}" for name, value in STAND_SECRETS.items()),
                    "DATABASE_URL=postgresql+psycopg://stand:"
                    f"{STAND_SECRETS['POSTGRES_PASSWORD']}@postgres:5432/stand",
                    f"S3_ACCESS_KEY_ID={STAND_SECRETS['MINIO_ROOT_USER']}",
                    f"S3_SECRET_ACCESS_KEY={STAND_SECRETS['MINIO_ROOT_PASSWORD']}",
                ]
            )
            + "\n",
        )
        _write(self.conf, conf_a)
        _git(self.repo, "init", "-q")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "A: the proxy configuration without the throttle")
        self.commit_a = _git(self.repo, "rev-parse", "HEAD").strip()
        _write(self.conf, conf_b)
        _git(self.repo, "commit", "-qam", "B: the tree's proxy configuration")
        self.commit_b = _git(self.repo, "rev-parse", "HEAD").strip()
        self.checkout(self.commit_a)

    def checkout(self, commit: str) -> None:
        _git(self.repo, "checkout", "-q", "--detach", commit)

    # -- driving --------------------------------------------------------------------
    def _script(self, path: Path) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            ["bash", str(path), "--env-file", str(self.env)],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=900,
        )
        print(f"\n$ {path.name}  -> exit {completed.returncode}")
        print(completed.stdout[-4000:])
        print(completed.stderr[-4000:])
        return completed

    def deploy_now(self) -> subprocess.CompletedProcess[str]:
        return self._script(self.deploy / "deploy.sh")

    def verify(self) -> subprocess.CompletedProcess[str]:
        return self._script(self.deploy / "verify-deployed.sh")

    def docker(self, *args: str) -> str:
        return subprocess.run(
            ["docker", *args], capture_output=True, text=True, check=True, timeout=120
        ).stdout.strip()

    def compose(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "docker", "compose", "--env-file", str(self.env),
                "--file", str(self.deploy / "compose.server.yml"), *args,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

    def proxy(self) -> str:
        found = self.compose("ps", "--quiet", "proxy").stdout.strip()
        assert found, "the stand has no proxy container"
        return found

    def proxy_state(self) -> tuple[str, str]:
        container = self.proxy()
        return container, self.docker("inspect", "--format", "{{.State.StartedAt}}", container)

    def proxy_reads(self) -> str:
        return self.docker(
            "exec", self.proxy(), "sha256sum", PROXY_INSIDE
        ).split()[0]

    def containers(self) -> dict[str, str]:
        return {
            service: self.compose("ps", "--quiet", service).stdout.strip()
            for service in ("postgres", "s3", "api", "web", "proxy")
        }

    def burst(self, count: int = 12) -> list[tuple[int, str]]:
        """`count` status reads, back to back, through the published port."""
        answers = []
        for _ in range(count):
            request = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/api/v1/registrations/status",
                data=b'{"login": "stand@example.org", "password": "not-a-password"}',
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    answers.append((response.status, response.read().decode()))
            except urllib.error.HTTPError as refused:
                answers.append((refused.code, refused.read().decode()))
        print(f"burst of {count}: {[code for code, _ in answers]}")
        return answers

    def wait_for_port(self) -> None:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=2)
                return
            except urllib.error.HTTPError:
                return
            except OSError:
                time.sleep(1)
        raise AssertionError("the stand's proxy never answered")

    def teardown(self) -> None:
        """This stand's containers, network and two images, by exact name, then the
        directory it was built in -- and nothing it did not create."""
        if self.env.exists():
            self.compose("down", "--remove-orphans", "--timeout", "5")
        for image in (f"{self.instance}-api", f"{self.instance}-web"):
            for tag in (image, f"{image}:deploy-previous"):
                subprocess.run(["docker", "image", "rm", tag], capture_output=True, check=False)
        if self.root.is_dir():
            shutil.rmtree(self.root)


@pytest.fixture()
def stand() -> Stand:
    directory, port, instance = _stand_settings()
    built = Stand(directory, port, instance)
    try:
        built.build()
        yield built
    finally:
        built.teardown()


class TestOnADisposableStand:
    def test_a_deploy_that_changes_the_proxy_configuration_serves_it(self, stand: Stand) -> None:
        # Deployed at A, which has no throttle: twelve status reads, no 429.
        first = stand.deploy_now()
        assert first.returncode == 0, first.stderr
        assert stand.verify().returncode == AGREES
        assert 429 not in [code for code, _ in stand.burst()]

        # THE TWO HALVES OF B-1, measured on real containers before anything repairs them.
        inode_a = stand.conf.stat().st_ino
        stand.checkout(stand.commit_b)
        inode_b = stand.conf.stat().st_ino
        print(f"inode at A {inode_a}, after the checkout of B {inode_b}")
        assert inode_a != inode_b
        stand.docker("exec", stand.proxy(), "nginx", "-s", "reload")
        assert stand.proxy_reads() != _sha(stand.conf), "the proxy already reads B"
        assert 429 not in [code for code, _ in stand.burst()], "B's throttle is served"

        # The mutant: the restart step deleted. It refuses, and the probe stays red.
        repaired = (stand.deploy / "reload-proxy.sh").read_text(encoding="utf-8")
        (stand.deploy / "reload-proxy.sh").write_text(_restart_removed(repaired), "utf-8")
        mutant = stand.deploy_now()
        assert mutant.returncode == DRIFT, mutant.stderr
        probe = stand.verify()
        assert probe.returncode == DRIFT, probe.stderr
        assert f"{PROXY_INSIDE}  DIFFERENT BYTES" in probe.stdout
        (stand.deploy / "reload-proxy.sh").write_text(repaired, "utf-8")

        # The repair: deploy.sh, as the auto-deploy runs it after its checkout.
        before = stand.proxy_state()
        second = stand.deploy_now()
        assert second.returncode == 0, second.stderr
        assert "was restarted" in second.stdout
        after = stand.proxy_state()
        assert after[0] == before[0] and after[1] != before[1], (before, after)
        assert stand.proxy_reads() == _sha(stand.conf)
        assert stand.verify().returncode == AGREES
        stand.wait_for_port()
        answers = stand.burst()
        limited = [body for code, body in answers if code == 429]
        assert limited, [code for code, _ in answers]
        assert '"error_code":"rate_limited"' in limited[0], limited[0]

        # And again with nothing changed: nothing is restarted or recreated.
        containers = stand.containers()
        third = stand.deploy_now()
        assert third.returncode == 0, third.stderr
        assert "was restarted" not in third.stdout
        assert stand.proxy_state() == after
        assert stand.containers() == containers
        assert stand.verify().returncode == AGREES
