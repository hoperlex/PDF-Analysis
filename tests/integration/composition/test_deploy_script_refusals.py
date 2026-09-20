"""`PA-01` criterion 1 -- every refusal `infra/deploy/deploy.sh` makes, shown able to fail.

`ALPHA_ROADMAP.md` §4 gives `infra/deploy/deploy.sh` to `W14-OPS`, a stream that was never
dispatched; `W21-CERT.md`'s criterion 1 records the consequence in one sentence -- *"there
is nothing to run"*. This suite is what makes the thing that now exists worth running.

**The shape of each case, and why it is this shape.** It is `reset.sh`'s, deliberately and
not by coincidence: this programme has one form for an operational script and a second one
would be a second thing to learn. For every guard:

1. an invocation that should trip it exits 3, names the reason, and -- for the guards that
   run before any `docker` call -- makes **no `docker` call at all**. That last part is
   what distinguishes "refused" from "refused after starting";
2. the same invocation against a **mutant copy with exactly that guard block deleted** no
   longer produces that refusal. That is the "shown able to fail" half, and it is done by
   deleting the guard rather than by asserting a message, because a message can be produced
   by a guard that happens to be unreachable.

**Nothing here can build, start or replace anything**, and not by hoping. `docker` is
replaced on `PATH` by a stub that records its arguments and answers the reads from the
environment. It opens no socket, pulls nothing and runs no container, so even a mutant that
runs to the end reaches no daemon. The stub is also the instrument: for the six guards that
sit before the first `docker` call, **an empty call log is the evidence the refusal came
first**, and for the two that sit before `up`, the evidence is a log with no `up` in it.

`reload-proxy.sh` is staged as a stub that exits 0. It is a separate script with its own
behaviour and `deploy.sh` reuses it rather than copying it; what is under test here is
`deploy.sh`'s guards, and a real reload would need a real proxy.

**The one thing here that is real is a TCP port.** `port-not-foreign` asks bash's own
`/dev/tcp` whether something is listening, and no stub can answer that -- so the cases bind
an actual socket on an ephemeral port, and the passing case uses a port nothing holds. A
loopback socket the test opened and closes is not a thing that can be destroyed.

This suite needs no running stack, which is the point -- it is the part of criterion 1 a
gate can hold. The clean-clone drive against real containers is recorded in
`docs/program/reviews/W23-DEPLOY.md`.
"""

from __future__ import annotations

import http.server
import json
import os
import re
import socket
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "infra/deploy/deploy.sh"
DOCKERFILE_API = ROOT / "infra/deploy/Dockerfile.api"
DOCKERFILE_WEB = ROOT / "infra/deploy/Dockerfile.web"
ENGINE = "tests/contract/api_v1/openapi_conformance.py"

#: `refuse()`'s exit status, the same one `reset.sh` uses. One code for every refusal; the
#: *reason* is asserted on the message, because twelve guards sharing an exit code must
#: still be told apart.
REFUSED = 3

#: Literals. The configured instance these cases are written against, spelled out rather
#: than read from `infra/deploy/env/alpha.env.example` -- `OPERATING_CONSTRAINTS.md` §12.
INSTANCE = "an-instance"
DATABASE = "the_configured_database"
BUCKET = "the-configured-bucket"

#: The placeholder values the staged `alpha.env.example` ships, and which
#: `placeholder-secrets` refuses by identity. They are this file's own literals for the
#: same reason -- the guard's claim is "you did not edit the file you copied", and a test
#: that read the real example to build both sides could not tell the two files apart.
EXAMPLE_SECRETS = {
    "POSTGRES_PASSWORD": "change-me-disposable-postgres-password",
    "MINIO_ROOT_USER": "change-me-disposable-minio-root",
    "MINIO_ROOT_PASSWORD": "change-me-disposable-minio-password",
    "AUDITMANAGER_API_TOKEN": "change-me-this-example-token-authorizes-nothing",
}

EDITED_SECRETS = {
    "POSTGRES_PASSWORD": "an-edited-postgres-password",
    "MINIO_ROOT_USER": "an-edited-minio-root",
    "MINIO_ROOT_PASSWORD": "an-edited-minio-password",
    "AUDITMANAGER_API_TOKEN": "an-edited-token-that-authorizes-something",
}


def _env_text(secrets: dict[str, str], *, instance: str | None = INSTANCE, port: int) -> str:
    lines = [
        f"ALPHA_HTTP_PORT={port}",
        f"POSTGRES_DB={DATABASE}",
        f"S3_BUCKET={BUCKET}",
    ]
    if instance is not None:
        lines.insert(0, f"ALPHA_INSTANCE={instance}")
    lines += [f"{name}={value}" for name, value in sorted(secrets.items())]
    return "\n".join(lines) + "\n"


def _example_text() -> str:
    return "\n".join(f"{name}={value}" for name, value in sorted(EXAMPLE_SECRETS.items())) + "\n"


# --- the `docker` that reaches nothing ------------------------------------------------
#
# It records every call and answers the five reads `deploy.sh` makes, from values the case
# chooses. It never connects to a daemon, so a mutant that runs past every guard still
# builds no image and starts no container.
#
# The compose sub-command is read positionally rather than by searching the arguments:
# `deploy.sh` always spells it `docker compose --env-file F --file C <sub> ...`, so the
# sub-command is argv[5]. Searching for the word `up` in a list that also holds two paths
# is the kind of accident this programme has already paid for once in a `grep` guard.

DOCKER_STUB = r'''#!/usr/bin/env python3
"""A `docker` that records, answers the reads, and reaches nothing."""
import os
import sys

argv = sys.argv[1:]
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as handle:
    handle.write(" ".join(argv) + "\n")


def setting(name, default=""):
    return os.environ.get(name, default)


if argv[:2] == ["image", "inspect"]:
    sys.exit(0 if setting("STUB_IMAGES_EXIST", "1") == "1" else 1)

if argv[:1] == ["inspect"]:
    sys.stdout.write(setting("STUB_STATE", "running/healthy") + "\n")
    sys.exit(0)

if argv[:1] == ["compose"]:
    sub = argv[5] if len(argv) > 5 else ""
    rest = argv[6:]
    if sub == "build":
        sys.exit(int(setting("STUB_BUILD_STATUS", "0")))
    if sub == "up":
        sys.exit(int(setting("STUB_UP_STATUS", "0")))
    if sub == "ps":
        service = rest[-1]
        if service == "proxy" and setting("STUB_OWN_PROXY", "1") != "1":
            sys.exit(0)
        if service in setting("STUB_MISSING_SERVICES").split(","):
            sys.exit(0)
        sys.stdout.write("container-of-%s\n" % service)
        sys.exit(0)
    if sub == "run":
        joined = " ".join(rest)
        if "auditmanager.shared.db.check" in joined:
            sys.stdout.write(setting("STUB_CHECK_OUTPUT", "FOUNDATION-CHECK OK check-db") + "\n")
            sys.exit(0)
        if "openapi_conformance.py" in joined:
            # The served document arrives on STDIN, not as a mount -- see the comment on
            # this guard in deploy.sh. Copying it out here is what lets a case prove that
            # the bytes the proxy served are the bytes the check was given.
            with open(setting("STUB_LOG") + ".served", "wb") as out:
                out.write(sys.stdin.buffer.read())
            sys.stdout.write(setting("STUB_CONFORMANCE_OUTPUT", "differences: 0") + "\n")
            sys.exit(int(setting("STUB_CONFORMANCE_STATUS", "0")))
        sys.exit(0)

sys.exit(0)
'''


# --- a served document, because `proxy-answers` uses a real curl ----------------------


class _Served(http.server.BaseHTTPRequestHandler):
    status = 200
    body = b'{"openapi": "3.1.0"}'

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's spelling
        self.send_response(type(self).status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(type(self).body)))
        self.end_headers()
        self.wfile.write(type(self).body)

    def log_message(self, *_: object) -> None:
        """Silence. The test's output is the assertion, not an access log."""


@pytest.fixture()
def serving() -> Iterator[tuple[int, type[_Served]]]:
    """An HTTP server on an ephemeral port, standing in for the published proxy port."""
    handler = type("_Handler", (_Served,), {"status": 200, "body": _Served.body})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1], handler
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture()
def free_port() -> int:
    """A port nothing is listening on, so `port-not-foreign` sees it free."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    return port


# --- staging --------------------------------------------------------------------------


def _context_paths() -> list[str]:
    """Every host path the two Dockerfiles `COPY`, read the way the guard reads them."""
    paths: list[str] = []
    for dockerfile in (DOCKERFILE_API, DOCKERFILE_WEB):
        for line in dockerfile.read_text(encoding="utf-8").splitlines():
            fields = line.split()
            if len(fields) >= 3 and fields[0].lower() == "copy" and not fields[1].startswith("--"):
                paths.extend(fields[1:-1])
    return sorted(set(paths))


def _stage(
    tmp_path: Path,
    *,
    script: Path | None = None,
    with_compose: bool = True,
    drop_context: str | None = None,
    with_engine: bool = True,
    with_example: bool = True,
    dockerfiles: bool = True,
) -> Path:
    """A clone-shaped directory: `<repo>/infra/deploy/deploy.sh` and what it reads.

    `deploy.sh` finds its repository from its own location, so the script must sit two
    levels below the root. The `COPY` paths are created from the real Dockerfiles rather
    than listed here, so this staging stays true to what the build actually needs.
    """
    repo = tmp_path / "repo"
    deploy = repo / "infra/deploy"
    deploy.mkdir(parents=True, exist_ok=True)

    (deploy / "deploy.sh").write_text(
        (script or DEPLOY).read_text(encoding="utf-8"), encoding="utf-8"
    )
    if dockerfiles:
        for name, source in (("Dockerfile.api", DOCKERFILE_API), ("Dockerfile.web", DOCKERFILE_WEB)):
            (deploy / name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    if with_compose:
        # Only its presence is checked, and `docker` is a stub, so its contents never run.
        (deploy / "compose.server.yml").write_text("# stub\n", encoding="utf-8")
    if with_example:
        (deploy / "env").mkdir(exist_ok=True)
        (deploy / "env/alpha.env.example").write_text(_example_text(), encoding="utf-8")

    reload_proxy = deploy / "reload-proxy.sh"
    reload_proxy.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    reload_proxy.chmod(0o755)

    for path in _context_paths():
        if drop_context is not None and path == drop_context:
            continue
        target = repo / path
        if path.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# staged\n", encoding="utf-8")
    if with_engine:
        engine = repo / ENGINE
        engine.parent.mkdir(parents=True, exist_ok=True)
        engine.write_text("# staged\n", encoding="utf-8")

    return deploy / "deploy.sh"


def _mutant(tmp_path: Path, guard: str) -> Path:
    """A copy of deploy.sh with exactly one guard block deleted, in place in a staging."""
    source = DEPLOY.read_text(encoding="utf-8")
    block = re.compile(
        rf"^# >>> guard: {re.escape(guard)}\n.*?^# <<< guard: {re.escape(guard)}\n",
        re.DOTALL | re.MULTILINE,
    )
    mutated, count = block.subn("", source)
    assert count == 1, f"the guard markers for {guard!r} are not a single block"
    assert mutated != source
    cut = tmp_path / "mutant.sh"
    cut.write_text(mutated, encoding="utf-8")
    return cut


def _run(
    script: Path,
    args: tuple[str, ...] = (),
    *,
    tmp_path: Path,
    env_file: Path | None,
    stub: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    binary = tmp_path / "bin"
    binary.mkdir(exist_ok=True)
    log = tmp_path / "docker-calls.log"
    docker = binary / "docker"
    docker.write_text(DOCKER_STUB, encoding="utf-8")
    docker.chmod(0o755)

    environment = dict(os.environ)
    environment["PATH"] = f"{binary}{os.pathsep}{environment['PATH']}"
    environment["STUB_LOG"] = str(log)
    if env_file is not None:
        environment["ALPHA_ENV_FILE"] = str(env_file)
    environment.update(stub or {})

    completed = subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        text=True,
        env=environment,
        timeout=180,
    )
    return completed, log


# --- the six that run before docker is touched at all ---------------------------------
#
# For every one of these the evidence is the same and it is the strongest this suite has:
# the call log does not exist, so the refusal happened before the first `docker`.


def _before_docker_cases(tmp_path: Path, port: int) -> dict[str, tuple[Path, tuple[str, ...], Path | None, str]]:
    """(script, args, env_file, expected words) for each pre-`docker` guard."""
    good = tmp_path / "alpha.env"
    good.write_text(_env_text(EDITED_SECRETS, port=port), encoding="utf-8")

    half = tmp_path / "half.env"
    half.write_text(_env_text(EDITED_SECRETS, instance=None, port=port), encoding="utf-8")

    stale = tmp_path / "stale.env"
    stale.write_text(_env_text(EXAMPLE_SECRETS, port=port), encoding="utf-8")

    return {
        "known-options": (
            _stage(tmp_path / "known"), ("--dryrun",), good,
            "unrecognised option: --dryrun",
        ),
        "env-file-present": (
            _stage(tmp_path / "envfile"), (), tmp_path / "not-there.env",
            "missing or unreadable",
        ),
        "instance-configured": (
            _stage(tmp_path / "instance"), (), half,
            "does not configure an instance",
        ),
        "placeholder-secrets": (
            _stage(tmp_path / "secrets"), (), stale,
            "still the value shipped in alpha.env.example",
        ),
        "compose-file-present": (
            _stage(tmp_path / "compose", with_compose=False), (), good,
            "compose.server.yml is missing",
        ),
        "build-context-complete": (
            _stage(tmp_path / "context", drop_context="src/"), (), good,
            "missing paths the two Dockerfiles copy",
        ),
    }


BEFORE_DOCKER = (
    "known-options",
    "env-file-present",
    "instance-configured",
    "placeholder-secrets",
    "compose-file-present",
    "build-context-complete",
)


class TestTheGuardsThatRefuseBeforeDockerIsTouched:
    @pytest.mark.parametrize("guard", BEFORE_DOCKER)
    def test_it_refuses_and_says_why(self, guard: str, tmp_path: Path, free_port: int) -> None:
        script, args, env_file, says = _before_docker_cases(tmp_path, free_port)[guard]
        completed, log = _run(script, args, tmp_path=tmp_path, env_file=env_file)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert says in completed.stderr, completed.stderr
        assert not log.exists(), (
            f"{guard} refused, but only after running docker: {log.read_text()}"
        )

    @pytest.mark.parametrize("guard", BEFORE_DOCKER)
    def test_deleting_the_guard_removes_the_refusal(
        self, guard: str, tmp_path: Path, free_port: int
    ) -> None:
        """Delete the guard, and the refusal is gone. Nothing else in the file changes."""
        _, args, env_file, says = _before_docker_cases(tmp_path, free_port)[guard]
        cut = _mutant(tmp_path, guard)
        # The mutant is staged the same way its intact case was, so the only difference
        # between the two runs is the deleted block.
        staging = {
            "compose-file-present": {"with_compose": False},
            "build-context-complete": {"drop_context": "src/"},
        }.get(guard, {})
        mutant = _stage(tmp_path / f"mutant-{guard}", script=cut, **staging)  # type: ignore[arg-type]
        completed, _ = _run(mutant, args, tmp_path=tmp_path, env_file=env_file)
        assert says not in completed.stderr, (
            f"the {guard} guard was deleted and the refusal happened anyway, so this case "
            "was never testing that guard"
        )


class TestTheParseThatFoundNothingIsNotACompleteClone:
    """`build-context-complete`'s own blind spot, and it is the one `verify-deployed.sh`
    names too: a probe that derives what it checks from a file it could not parse would
    report a perfect clone. `src/` is asked for by name rather than counted, because a
    threshold is a number to argue with."""

    def test_dockerfiles_it_cannot_parse_are_refused(
        self, tmp_path: Path, free_port: int
    ) -> None:
        env_file = tmp_path / "alpha.env"
        env_file.write_text(_env_text(EDITED_SECRETS, port=free_port), encoding="utf-8")
        script = _stage(tmp_path / "unparseable", dockerfiles=False)
        for name in ("Dockerfile.api", "Dockerfile.web"):
            (script.parent / name).write_text("FROM scratch\n", encoding="utf-8")
        completed, log = _run(script, tmp_path=tmp_path, env_file=env_file)
        assert completed.returncode == REFUSED, completed.stderr
        assert "COPY lines could not be read" in completed.stderr, completed.stderr
        assert not log.exists()


# --- the two that refuse before anything is brought up --------------------------------
#
# Here an empty log would be the wrong evidence: both sit after the first `docker` call.
# The evidence is a log that contains no `up`, which is the only call in this script that
# replaces a running container.


def _ready(tmp_path: Path, port: int, **staging: object) -> tuple[Path, Path]:
    env_file = tmp_path / "alpha.env"
    env_file.write_text(_env_text(EDITED_SECRETS, port=port), encoding="utf-8")
    return _stage(tmp_path / "ready", **staging), env_file  # type: ignore[arg-type]


def _up_calls(log: Path) -> list[str]:
    if not log.exists():
        return []
    return [
        line
        for line in log.read_text(encoding="utf-8").splitlines()
        if line.split()[5:6] == ["up"]
    ]


class TestNothingIsBroughtUpUntilTheImagesExist:
    """`images-built`, and it is the nearest thing to a rollback this script can own.

    `docker compose up -d --build` is one command and would have been shorter. It is
    deliberately two, because the property worth having is an ORDER: nothing that is
    serving is replaced until the images that would replace it exist. That is testable
    here; "the previous version keeps serving" is not, because there is no host with a
    previous version on it (`R-1`).
    """

    def test_a_failed_build_starts_nothing(self, tmp_path: Path, free_port: int) -> None:
        script, env_file = _ready(tmp_path, free_port)
        completed, log = _run(
            script, tmp_path=tmp_path, env_file=env_file, stub={"STUB_BUILD_STATUS": "1"}
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "the image build failed" in completed.stderr, completed.stderr
        # It got as far as building -- so the refusal is this guard and not an earlier one
        # -- and no further.
        calls = log.read_text(encoding="utf-8")
        assert "build" in calls, "it refused before even trying to build"
        assert _up_calls(log) == [], calls

    def test_a_build_that_exits_zero_and_made_no_image_starts_nothing(
        self, tmp_path: Path, free_port: int
    ) -> None:
        """The build failure that would otherwise reach the containers: a zero that built
        nothing. `run_checked` in the Makefile makes the same argument about sentinels."""
        script, env_file = _ready(tmp_path, free_port)
        completed, log = _run(
            script, tmp_path=tmp_path, env_file=env_file, stub={"STUB_IMAGES_EXIST": "0"}
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "there is no image called" in completed.stderr, completed.stderr
        assert _up_calls(log) == [], log.read_text(encoding="utf-8")

    def test_that_guard_is_shown_able_to_fail(self, tmp_path: Path, free_port: int) -> None:
        """Delete it and the same failed build is followed by an `up`. That is the case
        the two-step order exists to prevent."""
        cut = _mutant(tmp_path, "images-built")
        script = _stage(tmp_path / "mutant-images", script=cut)
        env_file = tmp_path / "alpha.env"
        env_file.write_text(_env_text(EDITED_SECRETS, port=free_port), encoding="utf-8")
        completed, log = _run(
            script, tmp_path=tmp_path, env_file=env_file, stub={"STUB_BUILD_STATUS": "1"}
        )
        assert "the image build failed" not in completed.stderr
        assert _up_calls(log) != [], (
            "the mutant did not reach the `up`, so this case was not testing that guard"
        )


class TestAnotherInstancesPortIsNotTakenQuietly:
    """`port-not-foreign`. `ALPHA_HTTP_PORT` is the one published port, so on a host that
    already runs an instance it is the one thing two of them can collide on. Taking it
    means an unrelated stack stops answering while this one reports success.

    The own-proxy case is the idempotent one, and it is why this is not simply "the port
    must be free": on a second run the port is held by this instance's own proxy.
    """

    def test_a_port_another_stack_holds_is_refused(
        self, tmp_path: Path, serving: tuple[int, type], free_port: int
    ) -> None:
        port, _ = serving
        script, env_file = _ready(tmp_path, port)
        completed, log = _run(
            script, tmp_path=tmp_path, env_file=env_file, stub={"STUB_OWN_PROXY": "0"}
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert f"port {port} is already in use, and not by" in completed.stderr, completed.stderr
        calls = log.read_text(encoding="utf-8") if log.exists() else ""
        assert "ps" in calls, "it refused before even asking whether the proxy is ours"
        assert "build" not in calls, calls
        assert _up_calls(log) == [], calls

    def test_the_same_port_held_by_our_own_proxy_is_the_idempotent_case(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        """The control. Without it, a guard that refused every busy port would look
        correct and would make a second run impossible."""
        port, _ = serving
        script, env_file = _ready(tmp_path, port)
        completed, _ = _run(
            script, tmp_path=tmp_path, env_file=env_file, stub={"STUB_OWN_PROXY": "1"}
        )
        assert "already in use" not in completed.stderr, completed.stderr
        assert completed.returncode == 0, (completed.stdout, completed.stderr)

    def test_that_guard_is_shown_able_to_fail(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        port, _ = serving
        cut = _mutant(tmp_path, "port-not-foreign")
        script = _stage(tmp_path / "mutant-port", script=cut)
        env_file = tmp_path / "alpha.env"
        env_file.write_text(_env_text(EDITED_SECRETS, port=port), encoding="utf-8")
        completed, log = _run(
            script, tmp_path=tmp_path, env_file=env_file, stub={"STUB_OWN_PROXY": "0"}
        )
        assert "already in use" not in completed.stderr
        assert _up_calls(log) != [], (
            "the mutant did not reach the `up`, so this case was not testing that guard"
        )


# --- the four that ask the running stack ----------------------------------------------


class TestTheRunningStackIsAskedAndMayFail:
    """`services-healthy`, `migrations-at-head`, `proxy-answers`, `schema-conforms`.

    These sit after the `up`, so neither an empty log nor an absent `up` is the evidence
    for them. What they claim is narrower and it is what the criterion asks for: the stack
    is up and the script still refuses to call it deployed.
    """

    def test_a_service_that_is_not_healthy_is_refused(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        port, _ = serving
        script, env_file = _ready(tmp_path, port)
        completed, _ = _run(
            script, tmp_path=tmp_path, env_file=env_file,
            stub={"STUB_STATE": "running/unhealthy"},
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "is running/unhealthy" in completed.stderr, completed.stderr

    def test_a_service_with_no_container_is_refused(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        """`up --wait` is not this claim and that is why the guard exists: a container
        that became healthy and then exited satisfied `--wait` on its way past."""
        port, _ = serving
        script, env_file = _ready(tmp_path, port)
        completed, _ = _run(
            script, tmp_path=tmp_path, env_file=env_file,
            stub={"STUB_MISSING_SERVICES": "web"},
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "the 'web' service of" in completed.stderr, completed.stderr
        assert "has no container" in completed.stderr, completed.stderr

    def test_services_healthy_is_shown_able_to_fail(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        port, _ = serving
        cut = _mutant(tmp_path, "services-healthy")
        script = _stage(tmp_path / "mutant-healthy", script=cut)
        env_file = tmp_path / "alpha.env"
        env_file.write_text(_env_text(EDITED_SECRETS, port=port), encoding="utf-8")
        completed, _ = _run(
            script, tmp_path=tmp_path, env_file=env_file,
            stub={"STUB_STATE": "running/unhealthy"},
        )
        assert "running/unhealthy" not in completed.stderr
        assert completed.returncode == 0, (completed.stdout, completed.stderr)

    def test_a_database_that_is_not_at_head_is_refused(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        """THE SENTINEL IS THE EVIDENCE, NOT THE EXIT CODE, and that is the check module's
        own rule. Here the stub exits 0 and prints the module's *failure* line, which is
        exactly the shape a check that could not read the schema produces."""
        port, _ = serving
        script, env_file = _ready(tmp_path, port)
        completed, _ = _run(
            script, tmp_path=tmp_path, env_file=env_file,
            stub={
                "STUB_CHECK_OUTPUT":
                    "FOUNDATION-CHECK FAIL check-db: the database is behind the code",
            },
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "did not answer the application's own check" in completed.stderr, completed.stderr
        # The failure the operator needs is reproduced, not swallowed.
        assert "the database is behind the code" in completed.stdout, completed.stdout

    def test_migrations_at_head_is_shown_able_to_fail(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        port, _ = serving
        cut = _mutant(tmp_path, "migrations-at-head")
        script = _stage(tmp_path / "mutant-head", script=cut)
        env_file = tmp_path / "alpha.env"
        env_file.write_text(_env_text(EDITED_SECRETS, port=port), encoding="utf-8")
        completed, _ = _run(
            script, tmp_path=tmp_path, env_file=env_file,
            stub={"STUB_CHECK_OUTPUT": "FOUNDATION-CHECK FAIL check-db: nowhere near head"},
        )
        assert "did not answer the application's own check" not in completed.stderr
        assert completed.returncode == 0, (completed.stdout, completed.stderr)

    @pytest.mark.parametrize("status", (502, 503, 504), ids=("502", "503", "504"))
    def test_a_proxy_holding_a_dead_upstream_is_refused(
        self, status: int, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        """The shape a rebuild leaves behind: nginx holding an upstream that is no longer
        there, both new containers healthy, and compose saying nothing is wrong."""
        port, handler = serving
        handler.status = status
        script, env_file = _ready(tmp_path, port)
        completed, _ = _run(script, tmp_path=tmp_path, env_file=env_file)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert f"the proxy answered {status}" in completed.stderr, completed.stderr

    def test_any_other_answer_from_the_published_port_is_refused(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        port, handler = serving
        handler.status = 404
        script, env_file = _ready(tmp_path, port)
        completed, _ = _run(script, tmp_path=tmp_path, env_file=env_file)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "answered 404, not 200" in completed.stderr, completed.stderr

    def test_proxy_answers_is_shown_able_to_fail(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        port, handler = serving
        handler.status = 502
        cut = _mutant(tmp_path, "proxy-answers")
        script = _stage(tmp_path / "mutant-proxy", script=cut)
        env_file = tmp_path / "alpha.env"
        env_file.write_text(_env_text(EDITED_SECRETS, port=port), encoding="utf-8")
        completed, _ = _run(script, tmp_path=tmp_path, env_file=env_file)
        assert "the proxy answered 502" not in completed.stderr
        assert completed.returncode == 0, (completed.stdout, completed.stderr)

    def test_a_served_document_that_does_not_conform_is_refused(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        """`PA-01` criterion 1's second clause. The engine is the gate's own; what is
        stubbed here is the container it runs in, not the comparison it makes."""
        port, _ = serving
        script, env_file = _ready(tmp_path, port)
        completed, _ = _run(
            script, tmp_path=tmp_path, env_file=env_file,
            stub={
                "STUB_CONFORMANCE_STATUS": "1",
                "STUB_CONFORMANCE_OUTPUT":
                    "differences: 1\n  paths./projects.post.operationId: plantedDifference",
            },
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "does not conform to the frozen contract" in completed.stderr, completed.stderr
        assert "plantedDifference" in completed.stdout, completed.stdout

    def test_a_clone_without_the_engine_is_refused_rather_than_skipped(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        """A deploy that could not find the engine and carried on would report a
        conformance it never made. The criterion asks for the gate's own check; without
        it there is no check to re-run."""
        port, _ = serving
        script, env_file = _ready(tmp_path, port, with_engine=False)
        completed, _ = _run(script, tmp_path=tmp_path, env_file=env_file)
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "conformance engine is not in this clone" in completed.stderr, completed.stderr

    def test_schema_conforms_is_shown_able_to_fail(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        port, _ = serving
        cut = _mutant(tmp_path, "schema-conforms")
        script = _stage(tmp_path / "mutant-schema", script=cut)
        env_file = tmp_path / "alpha.env"
        env_file.write_text(_env_text(EDITED_SECRETS, port=port), encoding="utf-8")
        completed, _ = _run(
            script, tmp_path=tmp_path, env_file=env_file,
            stub={"STUB_CONFORMANCE_STATUS": "1"},
        )
        assert "does not conform to the frozen contract" not in completed.stderr
        assert completed.returncode == 0, (completed.stdout, completed.stderr)


class TestTheControl:
    """Without this, a script that refused everything would pass every case above."""

    def test_a_good_deployment_runs_to_the_end(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        port, _ = serving
        script, env_file = _ready(tmp_path, port)
        completed, log = _run(script, tmp_path=tmp_path, env_file=env_file)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        assert "REFUSED" not in completed.stderr, completed.stderr
        assert f"is up at http://127.0.0.1:{port}" in completed.stdout, completed.stdout
        # Every step the script claims to take was taken, in the order it claims.
        subcommands = [
            line.split()[5]
            for line in log.read_text(encoding="utf-8").splitlines()
            if line.split()[:1] == ["compose"] and len(line.split()) > 5
        ]
        assert subcommands.index("build") < subcommands.index("up"), subcommands
        assert "run" in subcommands[subcommands.index("up"):], subcommands

    def test_the_served_document_reaches_the_conformance_check(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        """The bytes the proxy served are what the engine is given -- not a build artefact
        and not a second fetch. The criterion's words are "against the deployed process"."""
        port, handler = serving
        handler.body = b'{"openapi": "3.1.0", "x-served-by": "the-proxy"}'
        script, env_file = _ready(tmp_path, port)
        completed, log = _run(script, tmp_path=tmp_path, env_file=env_file)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        captured = Path(str(log) + ".served")
        assert captured.exists(), "the served document never reached the conformance check"
        assert json.loads(captured.read_text(encoding="utf-8"))["x-served-by"] == "the-proxy"

    def test_the_served_document_is_not_bind_mounted(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        """MEASURED, NOT PREFERRED. This guard was first written with
        `-v "$SERVED:/served.json:ro"` and driven from a clean clone, and the container
        answered `IsADirectoryError: Is a directory: '/served.json'`.

        `$SERVED` comes from `mktemp`, so it is under `/tmp`, and the snap docker daemon's
        mount namespace has `/tmp/snap-private-tmp/snap.docker/tmp` mounted over `/tmp`. A
        bind source the daemon cannot resolve is not an error: docker creates an empty
        DIRECTORY at the destination and starts the container. It is `reset.sh`'s
        relative-path finding again -- **a `-v` source is resolved by the daemon, not by
        the shell that typed it** -- and both fail by producing something plausible.

        A `mktemp -p` elsewhere would have fixed the one path and left the class open, so
        this pins the shape rather than the directory: the served document is piped in.
        """
        port, _ = serving
        script, env_file = _ready(tmp_path, port)
        completed, log = _run(script, tmp_path=tmp_path, env_file=env_file)
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        for line in log.read_text(encoding="utf-8").splitlines():
            for word in line.split():
                assert not word.endswith(":/served.json:ro"), (
                    f"the served document is bind-mounted again: {word!r}. Under a daemon "
                    "whose /tmp is not the operator's it arrives as an empty directory."
                )
        # And what IS mounted comes from the repository, which the daemon does resolve --
        # the same place reset.sh mounts object_attrs.py from.
        engine_mounts = [
            word
            for line in log.read_text(encoding="utf-8").splitlines()
            for word in line.split()
            if word.endswith(":/engine/openapi_conformance.py:ro")
        ]
        assert engine_mounts, "the conformance engine is no longer mounted"
        for mount in engine_mounts:
            source = Path(mount[: -len(":/engine/openapi_conformance.py:ro")])
            assert source.is_absolute(), mount
            assert source.exists(), f"{source} is not a path the daemon could resolve"

    def test_a_published_port_that_serves_something_other_than_json_says_so(
        self, tmp_path: Path, serving: tuple[int, type]
    ) -> None:
        """"Could not be read" and "does not conform" are two different things to tell an
        operator, and the first reported as the second sends somebody to look at the
        contract when the fault is in the fetch."""
        port, _ = serving
        script, env_file = _ready(tmp_path, port)
        completed, _ = _run(
            script, tmp_path=tmp_path, env_file=env_file,
            stub={
                "STUB_CONFORMANCE_STATUS": "2",
                "STUB_CONFORMANCE_OUTPUT":
                    "the document served at /api/v1/openapi.json is not JSON: line 1",
            },
        )
        assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
        assert "answered 200 and did not serve a document" in completed.stderr, completed.stderr
        assert "does not conform to the frozen contract" not in completed.stderr


def test_every_guard_in_the_script_has_a_case_here() -> None:
    """A guard added without a test is caught here rather than in a deployment.

    The count is a literal for the same reason every other figure in this file is. It was
    12 until `W24-IDEM` added `identity-policy-known`, whose case lives in
    `test_deploy_image_identity.py` beside this file and is named in the set below.
    """
    markers = re.findall(r"^# >>> guard: ([a-z-]+)$", DEPLOY.read_text(encoding="utf-8"), re.M)
    assert len(markers) == len(set(markers)), markers
    assert len(markers) == 13, markers
    covered = set(BEFORE_DOCKER) | {
        "port-not-foreign",
        "images-built",
        "services-healthy",
        "migrations-at-head",
        "proxy-answers",
        "schema-conforms",
        # `W24-IDEM`, and its case is in the file beside this one:
        # `test_deploy_image_identity.py`. Named here rather than left out, because the
        # claim this test makes is that every guard has a case SOMEWHERE, and a guard
        # silently excluded from the set would be a guard nobody tests.
        "identity-policy-known",
    }
    assert set(markers) == covered, set(markers) ^ covered
    identity_suite = ROOT / "tests/integration/composition/test_deploy_image_identity.py"
    assert "identity-policy-known" in identity_suite.read_text(encoding="utf-8"), (
        "identity-policy-known is excused here against a file that no longer names it"
    )


def test_the_script_is_executable_and_runnable_by_its_documented_path() -> None:
    """`README.md` and the roadmap both name `infra/deploy/deploy.sh`. A deliverable that
    has to be invoked as `bash <path>` is not the command either of them documents."""
    assert DEPLOY.exists(), "infra/deploy/deploy.sh is missing"
    assert os.access(DEPLOY, os.X_OK), "infra/deploy/deploy.sh is not executable"
    assert DEPLOY.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash\n")


def test_it_runs_the_gates_own_conformance_engine_and_not_a_second_one() -> None:
    """The objection revision 1 of `ALPHA_ROADMAP.md` raised against FastAPI was a *second*
    schema authority. A deploy script that reimplemented the comparison would be a third.

    So this pins the engine's path and the two functions called, against the module that
    defines them: a rename there reddens here rather than in a deployment.
    """
    script = DEPLOY.read_text(encoding="utf-8")
    assert f'CONFORMANCE_ENGINE="$REPO/{ENGINE}"' in script, (
        "deploy.sh no longer mounts the gate's conformance engine"
    )
    engine = (ROOT / ENGINE).read_text(encoding="utf-8")
    for function in ("surface", "differences", "operation_index"):
        assert f"def {function}(" in engine, f"{ENGINE} no longer defines {function}()"
        assert function in script, f"deploy.sh no longer calls {function}()"
    # And the frozen contract it compares against is the one the gate calls the authority.
    assert (ROOT / "contracts/api/v1/openapi.json").exists()
    assert "/app/contracts/api/v1/openapi.json" in script
