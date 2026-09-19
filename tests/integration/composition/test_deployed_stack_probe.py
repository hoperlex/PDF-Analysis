"""`D-27` -- the probe that answers "is the deployed stack this tree?", and every way it
is allowed to say no.

**The failure this row is about is a check nobody notices.** Three waves running,
"deployed does not equal repository" had to be re-measured by hand, and once a session was
told the stack was current when it was not -- it would have certified a defect that had
already been repaired. So the thing being guarded here is not really `verify-deployed.sh`'s
arithmetic. It is that there is no path through it that reports a healthy stack without
having compared bytes, including the paths where it is *confused*: a Dockerfile it cannot
parse, a container that is not there, a proxy that does not answer. Every one of those is a
non-zero exit with its own message.

**Nothing here touches a stack.** `docker` and `curl` are replaced on `PATH` by stubs that
record and answer from the fixture. The stubs are also the instrument: they are what lets a
stale image be put in front of the probe on purpose, which is otherwise a thing you can only
have by waiting for it to happen to you.

The live counterpart is in `docs/program/reviews/W22-OPS.md`: run against the real alpha
stack on 31500 at `313e753`, this probe's first execution found that the deployed web image
predated `89600f6` by eleven minutes, contradicting a brief that said the stack had been
rebuilt from current code.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "infra/deploy"
PROBE = DEPLOY / "verify-deployed.sh"
RELOAD = DEPLOY / "reload-proxy.sh"

#: `verify-deployed.sh`'s three answers. Exit 0 is the only success, and "I could not tell"
#: is deliberately not one -- see the module note.
AGREES = 0
UNANSWERABLE = 4
DRIFT = 6

ENV_FILE = """\
ALPHA_INSTANCE=an-instance
ALPHA_HTTP_PORT=31599
"""

#: A `docker` that answers from the staged fixture and reaches nothing. It serves three
#: shapes the probe uses -- `compose ps --quiet <service>`, `exec <id> sh -c '...sha256sum'`
#: fed a NUL-separated list on stdin, and `exec <id> sh -c 'find ...'` -- plus `nginx -t`
#: and `nginx -s reload` for `reload-proxy.sh`.
DOCKER_STUB = r'''#!/usr/bin/env python3
"""A `docker` that plays a container's filesystem out of a directory, and reaches nothing."""
import hashlib, os, pathlib, sys

argv = sys.argv[1:]
line = " ".join(argv)
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as handle:
    handle.write(line + "\n")

IMAGE = pathlib.Path(os.environ["STUB_IMAGE"])          # stands in for the container
OMIT = set(filter(None, os.environ.get("STUB_OMIT", "").split(":")))
CORRUPT = set(filter(None, os.environ.get("STUB_CORRUPT", "").split(":")))
EXTRA = set(filter(None, os.environ.get("STUB_EXTRA", "").split(":")))


def inside(container_path):
    """The staged file standing in for `container_path` inside the image."""
    return IMAGE / container_path.lstrip("/")


if "ps" in argv and "--quiet" in argv:
    if os.environ.get("STUB_NO_CONTAINER") == "yes":
        sys.exit(0)
    print("c0ffee" + argv[-1])
    sys.exit(0)

if "nginx" in argv:
    if "-t" in argv:
        sys.exit(int(os.environ.get("STUB_NGINX_T", "0")))
    print("reloaded")
    sys.exit(0)

if "sha256sum" in line:
    for raw in sys.stdin.buffer.read().split(b"\0"):
        path = raw.decode()
        if not path or path in OMIT:
            continue
        staged = inside(path)
        if not staged.is_file():
            continue
        digest = hashlib.sha256(staged.read_bytes()).hexdigest()
        if path in CORRUPT:
            digest = "0" * 64
        print("%s  %s" % (digest, path))
    sys.exit(0)

if "find" in line:
    root = line.split("find '", 1)[1].split("'", 1)[0]
    staged = inside(root)
    for path in sorted(staged.rglob("*")) if staged.is_dir() else []:
        if path.is_file() and "__pycache__" not in path.parts:
            print("/" + str(path.relative_to(IMAGE)))
    for path in sorted(EXTRA):
        if path.startswith(root.rstrip("/") + "/"):
            print(path)
    sys.exit(0)

sys.exit(0)
'''

#: A `curl` that answers with the fixture's status. It exits NON-ZERO when it could not
#: connect, because the real one does -- and it prints `000` as well as failing, which is
#: how `verify-deployed.sh` came to report "the proxy answered 000000" until this stub was
#: made to behave like the tool it stands in for.
CURL_STUB = """#!/bin/sh
printf '%s' "$STUB_HTTP_CODE"
[ "$STUB_HTTP_CODE" = 000 ] && exit 7
exit 0
"""

#: A two-stage `Dockerfile.api` in the shape the real one has: a build stage whose COPYs
#: never ship, and a runtime stage whose COPYs do.
FAKE_DOCKERFILE_API = """\
FROM python:3.12-slim AS build
COPY Makefile /tmp/Makefile
COPY pyproject.toml uv.lock .python-version ./

FROM python:3.12-slim
COPY --from=build /app/.venv /app/.venv
COPY src/ /app/src/
COPY contracts/ /app/contracts/
COPY infra/deploy/serve.py /app/serve.py
"""

FAKE_DOCKERFILE_WEB = """\
FROM node:24-bookworm-slim AS build
WORKDIR /web
COPY web/package.json web/package-lock.json ./
COPY web/ ./

FROM node:24-bookworm-slim
WORKDIR /web
COPY --from=build /web /web
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def world(tmp_path: Path):
    """A small git repository, a staged `infra/deploy`, and an image that agrees with it.

    Small on purpose: the shapes under test are "a file is missing", "a file's bytes
    differ", "there is something here that is not in the tree". None of them needs four
    hundred files, and a gate pays for every one of them on every run. The *real*
    Dockerfiles are read by their own case below.
    """
    repo = tmp_path / "repo"
    _write(repo / "src/auditmanager/api/app.py", "the surface\n")
    _write(repo / "src/auditmanager/runs/carrier.py", "what W20-EXEC added\n")
    _write(repo / "contracts/api/v1/openapi.json", '{"openapi": "3.1.0"}\n')
    _write(repo / "infra/deploy/serve.py", "one application, two ports\n")
    _write(repo / "web/package.json", '{"name": "web"}\n')
    _write(repo / "web/app/page.tsx", "export default function () {}\n")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=w22@ops", "-c", "user.name=w22", "commit", "-qm", "base"],
        cwd=repo,
        check=True,
    )

    deploy = tmp_path / "staged"
    deploy.mkdir()
    (deploy / "verify-deployed.sh").write_text(PROBE.read_text(encoding="utf-8"), "utf-8")
    (deploy / "reload-proxy.sh").write_text(RELOAD.read_text(encoding="utf-8"), "utf-8")
    (deploy / "compose.server.yml").write_text("# stub\n", encoding="utf-8")
    (deploy / "Dockerfile.api").write_text(FAKE_DOCKERFILE_API, encoding="utf-8")
    (deploy / "Dockerfile.web").write_text(FAKE_DOCKERFILE_WEB, encoding="utf-8")
    _write(deploy / "env/alpha.env", ENV_FILE)

    # The image: what the Dockerfiles above say goes into it, and it agrees to begin with.
    image = tmp_path / "image"
    for source, destination in (
        ("src", "app/src"),
        ("contracts", "app/contracts"),
        ("web", "web"),
    ):
        for path in sorted((repo / source).rglob("*")):
            if path.is_file():
                _write(image / destination / path.relative_to(repo / source), path.read_text())
    _write(image / "app/serve.py", (repo / "infra/deploy/serve.py").read_text())
    # A build product that was never in the tree: the reason `/web` is not extras-checked.
    _write(image / "web/node_modules/left-pad/index.js", "//\n")

    return repo, deploy, image


def _run(
    script: Path,
    *args: str,
    tmp_path: Path,
    repo: Path | None = None,
    env_file: Path | None = None,
    code: str = "200",
    **stub_environment: str,
) -> tuple[subprocess.CompletedProcess[str], str]:
    binary = tmp_path / "bin"
    binary.mkdir(exist_ok=True)
    log = tmp_path / "docker-calls.log"
    for name, body in (("docker", DOCKER_STUB), ("curl", CURL_STUB)):
        stub = binary / name
        stub.write_text(body, encoding="utf-8")
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    environment = dict(os.environ)
    environment["PATH"] = f"{binary}{os.pathsep}{environment['PATH']}"
    environment["STUB_LOG"] = str(log)
    environment["STUB_HTTP_CODE"] = code
    environment.update(stub_environment)
    if env_file is not None:
        environment["ALPHA_ENV_FILE"] = str(env_file)
    invocation = ["bash", str(script), *args]
    if repo is not None:
        invocation += ["--repo", str(repo)]
    completed = subprocess.run(
        invocation, capture_output=True, text=True, env=environment, timeout=180
    )
    return completed, (log.read_text(encoding="utf-8") if log.exists() else "")


class TestItSaysYesOnlyAfterComparingBytes:
    def test_a_stack_that_is_the_tree_is_a_pass(self, world, tmp_path: Path) -> None:
        """The control. Without it, a probe that refused everything would look correct."""
        repo, deploy, image = world
        completed, calls = _run(
            deploy / "verify-deployed.sh",
            tmp_path=tmp_path,
            repo=repo,
            STUB_IMAGE=str(image),
        )
        assert completed.returncode == AGREES, (completed.stdout, completed.stderr)
        assert "IS this tree" in completed.stdout, completed.stdout
        # It did not conclude that by reading the Dockerfiles alone.
        assert "sha256sum" in calls, calls

    def test_a_file_the_image_does_not_have_is_named(self, world, tmp_path: Path) -> None:
        """`D-27` exactly: `carrier.py` was in the tree and not in the deployed image.

        Reported by name, because "1 file differs" sends an operator looking and a path
        sends them to the file.
        """
        repo, deploy, image = world
        completed, _ = _run(
            deploy / "verify-deployed.sh",
            tmp_path=tmp_path,
            repo=repo,
            STUB_IMAGE=str(image),
            STUB_OMIT="/app/src/auditmanager/runs/carrier.py",
        )
        assert completed.returncode == DRIFT, (completed.stdout, completed.stderr)
        assert "carrier.py  MISSING FROM THE IMAGE" in completed.stdout, completed.stdout
        assert "is NOT this tree" in completed.stderr, completed.stderr

    def test_a_file_whose_bytes_differ_is_named_with_both_digests(
        self, world, tmp_path: Path
    ) -> None:
        """The shape the live run found: the same path, built from an older commit."""
        repo, deploy, image = world
        completed, _ = _run(
            deploy / "verify-deployed.sh",
            tmp_path=tmp_path,
            repo=repo,
            STUB_IMAGE=str(image),
            STUB_CORRUPT="/web/package.json",
        )
        assert completed.returncode == DRIFT, (completed.stdout, completed.stderr)
        assert "package.json  DIFFERENT BYTES" in completed.stdout, completed.stdout
        assert "tree  " in completed.stdout and "image " in completed.stdout

    def test_a_file_in_the_image_that_is_not_in_the_tree_is_reported(
        self, world, tmp_path: Path
    ) -> None:
        """A hand-patched container is drift too, and in the direction nobody looks."""
        repo, deploy, image = world
        completed, _ = _run(
            deploy / "verify-deployed.sh",
            tmp_path=tmp_path,
            repo=repo,
            STUB_IMAGE=str(image),
            STUB_EXTRA="/app/src/auditmanager/hotfix.py",
        )
        assert completed.returncode == DRIFT, (completed.stdout, completed.stderr)
        assert "hotfix.py  IN THE IMAGE AND NOT IN THE TREE" in completed.stdout

    def test_the_web_images_build_products_are_not_drift(
        self, world, tmp_path: Path
    ) -> None:
        """`/web` holds `node_modules`, which was never in the tree. The control above
        already passes with it present; this says out loud that that is the reason `/web`
        is the one root whose extra files are not an error."""
        repo, deploy, image = world
        assert (image / "web/node_modules/left-pad/index.js").is_file()
        completed, _ = _run(
            deploy / "verify-deployed.sh", tmp_path=tmp_path, repo=repo, STUB_IMAGE=str(image)
        )
        assert completed.returncode == AGREES, completed.stderr


class TestEveryWayItCannotTellIsAFailure:
    """The row is about a check nobody notices. A probe that shrugs is that check."""

    def test_a_502_through_the_proxy_fails_and_names_the_repair(
        self, world, tmp_path: Path
    ) -> None:
        """The second face of `D-27`: after a rebuild replaced the containers, nginx held
        the dead upstream and everything through the proxy answered 502 while both new
        containers were healthy."""
        repo, deploy, image = world
        completed, _ = _run(
            deploy / "verify-deployed.sh",
            tmp_path=tmp_path,
            repo=repo,
            code="502",
            STUB_IMAGE=str(image),
        )
        assert completed.returncode == DRIFT, (completed.stdout, completed.stderr)
        assert "answered 502" in completed.stderr, completed.stderr
        assert "reload-proxy.sh" in completed.stderr, completed.stderr

    def test_a_proxy_that_does_not_answer_at_all_is_not_a_pass(
        self, world, tmp_path: Path
    ) -> None:
        repo, deploy, image = world
        completed, _ = _run(
            deploy / "verify-deployed.sh",
            tmp_path=tmp_path,
            repo=repo,
            code="000",
            STUB_IMAGE=str(image),
        )
        assert completed.returncode == UNANSWERABLE, (completed.stdout, completed.stderr)
        assert "Nothing was compared" in completed.stderr, completed.stderr
        assert "answered 000 on" in completed.stderr, completed.stderr

    def test_no_container_is_not_a_pass(self, world, tmp_path: Path) -> None:
        repo, deploy, image = world
        completed, _ = _run(
            deploy / "verify-deployed.sh",
            tmp_path=tmp_path,
            repo=repo,
            STUB_IMAGE=str(image),
            STUB_NO_CONTAINER="yes",
        )
        assert completed.returncode == UNANSWERABLE, (completed.stdout, completed.stderr)
        assert "no running container" in completed.stderr, completed.stderr

    def test_a_dockerfile_it_cannot_parse_is_not_a_pass(self, world, tmp_path: Path) -> None:
        """**The case this whole file exists for.** The probe derives what it checks from
        the Dockerfiles' own `COPY` lines, which is what keeps a newly copied path covered
        without anybody remembering. The cost of that is that a parse which finds nothing
        would otherwise compare nothing and report a perfect stack -- a green that means
        the opposite of what it says. So it refuses instead."""
        repo, deploy, image = world
        (deploy / "Dockerfile.api").write_text(
            "FROM python:3.12-slim AS build\nFROM python:3.12-slim\n", encoding="utf-8"
        )
        completed, calls = _run(
            deploy / "verify-deployed.sh",
            tmp_path=tmp_path,
            repo=repo,
            STUB_IMAGE=str(image),
        )
        assert completed.returncode == UNANSWERABLE, (completed.stdout, completed.stderr)
        assert "could not be read" in completed.stderr, completed.stderr
        assert "do not trust this green" in completed.stderr, completed.stderr
        assert "sha256sum" not in calls, "it compared something and then refused"

    def test_a_web_dockerfile_that_stops_copying_the_tree_is_not_a_pass(
        self, world, tmp_path: Path
    ) -> None:
        repo, deploy, image = world
        (deploy / "Dockerfile.web").write_text(
            "FROM node:24-bookworm-slim\nWORKDIR /web\n", encoding="utf-8"
        )
        completed, _ = _run(
            deploy / "verify-deployed.sh",
            tmp_path=tmp_path,
            repo=repo,
            STUB_IMAGE=str(image),
        )
        assert completed.returncode == UNANSWERABLE, (completed.stdout, completed.stderr)
        assert "does not know" in completed.stderr, completed.stderr

    def test_a_missing_environment_is_not_a_pass(self, world, tmp_path: Path) -> None:
        repo, deploy, image = world
        (deploy / "env/alpha.env").unlink()
        completed, _ = _run(
            deploy / "verify-deployed.sh",
            tmp_path=tmp_path,
            repo=repo,
            STUB_IMAGE=str(image),
        )
        assert completed.returncode == UNANSWERABLE, (completed.stdout, completed.stderr)


class TestItReadsTheRealDockerfiles:
    """The cases above run against small stand-ins, so this is what ties the probe to the
    Dockerfiles that are actually shipped. A path added to either image without a row here
    reddens the gate rather than quietly falling outside what the probe compares."""

    def test_the_api_image_is_made_of_exactly_these_tracked_paths(self) -> None:
        runtime = (DEPLOY / "Dockerfile.api").read_text(encoding="utf-8").split("\nFROM ")[-1]
        copied = {
            line.split()[1]
            for line in runtime.splitlines()
            if line.startswith("COPY ") and "--from" not in line and len(line.split()) == 3
        }
        assert copied == {
            "src/",
            "db/",
            "contracts/",
            "fixtures/recorded/",
            "docs/program/P02_LOCK.json",
            "infra/deploy/serve.py",
        }, copied

    def test_the_web_image_is_made_of_the_web_tree(self) -> None:
        text = (DEPLOY / "Dockerfile.web").read_text(encoding="utf-8")
        assert "\nCOPY web/ ./\n" in text, (
            "the probe maps `web/` onto `/web`; Dockerfile.web no longer says so"
        )
        assert "COPY --from=build /web /web" in text

    def test_no_tracked_path_contains_a_space(self) -> None:
        """The probe joins its two sides on the path, which is why. Checked rather than
        assumed, and this is the assumption's tripwire."""
        listed = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        assert not [path for path in listed if " " in path]


class TestTheProxyReload:
    """`reload-proxy.sh`. A rebuild is not finished when the images are."""

    def test_it_reloads_rather_than_restarting(self, world, tmp_path: Path) -> None:
        repo, deploy, image = world
        completed, calls = _run(
            deploy / "reload-proxy.sh",
            tmp_path=tmp_path,
            env_file=deploy / "env/alpha.env",
            STUB_IMAGE=str(image),
        )
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "nginx -s reload" in calls, calls
        assert "restart" not in calls, calls

    def test_it_tests_the_configuration_first(self, world, tmp_path: Path) -> None:
        """A reload with a broken configuration is refused by nginx and the old workers
        keep serving -- so the command would "succeed" at leaving the 502 in place."""
        repo, deploy, image = world
        completed, calls = _run(
            deploy / "reload-proxy.sh",
            tmp_path=tmp_path,
            env_file=deploy / "env/alpha.env",
            STUB_IMAGE=str(image),
            STUB_NGINX_T="1",
        )
        assert completed.returncode == 5, (completed.stdout, completed.stderr)
        assert "not valid" in completed.stderr, completed.stderr
        assert "nginx -s reload" not in calls, calls

    def test_no_proxy_container_is_not_a_success(self, world, tmp_path: Path) -> None:
        repo, deploy, image = world
        completed, _ = _run(
            deploy / "reload-proxy.sh",
            tmp_path=tmp_path,
            env_file=deploy / "env/alpha.env",
            STUB_IMAGE=str(image),
            STUB_NO_CONTAINER="yes",
        )
        assert completed.returncode == UNANSWERABLE, (completed.stdout, completed.stderr)
        assert "nothing to reload" in completed.stderr, completed.stderr
