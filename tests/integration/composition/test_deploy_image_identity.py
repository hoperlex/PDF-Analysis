"""`D-36` -- a second `infra/deploy/deploy.sh` against an unchanged tree replaces nothing.

**What was measured, and what this file pins.** `W23-DEPLOY` ran its own script twice from
a clean clone and disproved its own header comment: no layer rebuilds, no data is touched,
`postgres`, `s3` and `proxy` keep their container IDs -- and `api`, `web` and `migrate` are
recreated anyway, because a fully cached `compose build` still yields a NEW image ID.
BuildKit writes a fresh `created` into the image config even when every step reports
`CACHED`, and `compose up -d` recreates a service whose image id moved. `SOURCE_DATE_EPOCH`
was tried there and does not fix it on this compose/BuildKit.

`W24-IDEM` leaves the build alone and moves the TAG: after the build, if what was produced
has the same CONTENT as the image the name pointed at before it, the name is pointed back
at the old image and the new one is discarded. The container then starts from an image
whose id never moved, and compose has nothing to recreate.

**The failure mode a mechanism like this has is an image that keeps an old identity after
its content genuinely changed**, which would make `verify-deployed.sh` report a stale
stack as this tree. Two things stand against it and both are tested here: the fingerprint
is built from the layer diffIDs -- the sha256 of each layer's uncompressed tar -- so a
changed byte cannot present itself as identical without colliding a sha256; and the
runtime configuration is compared alongside them, so a Dockerfile that changed only `CMD`,
`ENV`, `USER`, `EXPOSE` or a label is a changed image too. The probe half of that argument
is driven against real containers in `docs/program/reviews/W24-IDEM.md` §4.

**Why `docker` is a stub here and not the daemon.** Same reason as
`test_deploy_script_refusals.py`, which this file is the sibling of: the suite may not
build an image, start a container or reach a daemon. The stub is a small image store --
tags point at ids, ids carry a content fingerprint -- so a build, a retag and a removal
are all observable, and a case chooses whether the build produced identical content or
not. What it cannot show is that a REAL cached rebuild produces an identical fingerprint;
that is a fact about BuildKit, it is measured in the review, and
`test_the_fingerprint_is_built_from_the_layer_digests_and_not_from_a_timestamp` pins the
one property of the fingerprint that fact depends on.
"""

from __future__ import annotations

import http.server
import json
import os
import re
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

REFUSED = 3

INSTANCE = "an-instance"
DATABASE = "the_configured_database"
BUCKET = "the-configured-bucket"

#: Spelled out rather than read from the example file -- `OPERATING_CONSTRAINTS.md` §12 --
#: and different from the example's values, so `placeholder-secrets` lets these cases past.
EDITED_SECRETS = {
    "POSTGRES_PASSWORD": "an-edited-postgres-password",
    "MINIO_ROOT_USER": "an-edited-minio-root",
    "MINIO_ROOT_PASSWORD": "an-edited-minio-password",
    "AUDITMANAGER_API_TOKEN": "an-edited-token-that-authorizes-something",
}
EXAMPLE_SECRETS = {
    "POSTGRES_PASSWORD": "change-me-disposable-postgres-password",
    "MINIO_ROOT_USER": "change-me-disposable-minio-root",
    "MINIO_ROOT_PASSWORD": "change-me-disposable-minio-password",
    "AUDITMANAGER_API_TOKEN": "change-me-this-example-token-authorizes-nothing",
}


# --- a `docker` that is a small image store -------------------------------------------
#
# It answers the reads `deploy.sh` makes and it MODELS THE ONE THING THE MECHANISM IS
# ABOUT: a tag points at an id, an id carries a fingerprintable content, and `compose
# build` mints a new id every time -- which is BuildKit's behaviour and the defect.
# Whether the new id's CONTENT differs is the case's choice, through STUB_BUILT_CONTENT.

DOCKER_STUB = r'''#!/usr/bin/env python3
"""A `docker` that keeps an image store in a JSON file and reaches no daemon."""
import json
import os
import sys

argv = sys.argv[1:]
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as handle:
    handle.write(" ".join(argv) + "\n")

STORE = os.environ["STUB_STORE"]


def setting(name, default=""):
    return os.environ.get(name, default)


def load():
    with open(STORE, encoding="utf-8") as handle:
        return json.load(handle)


def save(store):
    with open(STORE, "w", encoding="utf-8") as handle:
        json.dump(store, handle)


def resolve(store, ref):
    """A tag or an id, to an id. Unknown refs resolve to nothing, as docker's do."""
    if ref in store["tags"]:
        return store["tags"][ref]
    if ref in store["images"]:
        return ref
    return None


store = load()

if argv[:2] == ["image", "inspect"]:
    rest = argv[2:]
    fmt = ""
    if rest[:1] == ["--format"]:
        fmt = rest[1]
        rest = rest[2:]
    target = resolve(store, rest[-1]) if rest else None
    if target is None:
        sys.stderr.write("Error: No such image\n")
        sys.exit(1)
    if fmt == "{{.Id}}":
        sys.stdout.write(target + "\n")
    elif fmt:
        # Every other --format this script uses is the content fingerprint. The stub
        # answers it with the stored content, which is the same contract: equal content,
        # equal string.
        sys.stdout.write(store["images"][target] + "\n")
    sys.exit(0)

if argv[:1] == ["tag"]:
    source, destination = argv[1], argv[2]
    # The PIN taken before the build and the RETAG taken after it fail independently:
    # they are two different things to be unable to do, and a case that could only fail
    # both at once could not tell their two messages apart.
    pinning = destination.endswith(":deploy-previous")
    if pinning and setting("STUB_PIN_FAILS") == "1":
        sys.stderr.write("Error response from daemon: no\n")
        sys.exit(1)
    if not pinning and setting("STUB_TAG_FAILS") == "1":
        sys.stderr.write("Error response from daemon: no\n")
        sys.exit(1)
    target = resolve(store, source)
    if target is None:
        sys.stderr.write("Error: No such image\n")
        sys.exit(1)
    store["tags"][destination] = target
    save(store)
    sys.exit(0)

if argv[:2] == ["image", "rm"]:
    if setting("STUB_RM_FAILS") == "1":
        sys.stderr.write("Error response from daemon: conflict\n")
        sys.exit(1)
    ref = argv[2]
    target = resolve(store, ref)
    if target is None:
        sys.stderr.write("Error: No such image\n")
        sys.exit(1)
    if ref in store["tags"]:
        # A NAME: docker untags it, and deletes the image only if that was its last tag.
        del store["tags"][ref]
    elif target in store["tags"].values():
        sys.stderr.write("Error: image is referenced by a tag\n")
        sys.exit(1)
    if target not in store["tags"].values():
        store["images"].pop(target, None)
    save(store)
    sys.exit(0)

if argv[:1] == ["inspect"]:
    sys.stdout.write(setting("STUB_STATE", "running/healthy") + "\n")
    sys.exit(0)

if argv[:1] == ["compose"]:
    sub = argv[5] if len(argv) > 5 else ""
    rest = argv[6:]
    if sub == "build":
        # What the build was actually given, not what the script says it gives it.
        with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as handle:
            handle.write(
                "environment BUILDX_NO_DEFAULT_ATTESTATIONS=%s\n"
                % setting("BUILDX_NO_DEFAULT_ATTESTATIONS", "<unset>")
            )
        if setting("STUB_BUILD_STATUS", "0") != "0":
            sys.exit(int(setting("STUB_BUILD_STATUS")))
        # THE DEFECT, MODELLED: a build always mints a new id, whatever it produced.
        serial = store["serial"] = store["serial"] + 1
        for kind in ("api", "web"):
            name = "%s-%s" % (setting("STUB_INSTANCE"), kind)
            content = setting("STUB_BUILT_%s" % kind.upper(), "the-original-%s" % kind)
            fresh = "sha256:%s%02d" % (kind * 20, serial)
            displaced = store["tags"].get(name)
            store["images"][fresh] = content
            store["tags"][name] = fresh
            # AND THIS HOST'S DOCKER DELETES THE IMAGE THE TAG MOVED OFF, at once, even
            # while containers run on it -- measured, and recorded in `# --- 1.` of
            # deploy.sh. It is modelled rather than left out, because it is the whole
            # reason the pin exists: without a second tag there is nothing left to
            # compare the new image against.
            if displaced is not None and displaced not in store["tags"].values():
                store["images"].pop(displaced, None)
        save(store)
        sys.exit(0)
    if sub == "up":
        sys.exit(int(setting("STUB_UP_STATUS", "0")))
    if sub == "ps":
        service = rest[-1]
        if service == "proxy" and setting("STUB_OWN_PROXY", "1") != "1":
            sys.exit(0)
        sys.stdout.write("container-of-%s\n" % service)
        sys.exit(0)
    if sub == "run":
        joined = " ".join(rest)
        if "auditmanager.shared.db.check" in joined:
            sys.stdout.write("FOUNDATION-CHECK OK check-db\n")
            sys.exit(0)
        if "openapi_conformance.py" in joined:
            sys.stdin.buffer.read()
            sys.stdout.write("differences: 0\n")
            sys.exit(0)
        sys.exit(0)

sys.exit(0)
'''


# --- a served document, because `proxy-answers` uses a real curl ----------------------
#
# The same shape as `test_deploy_script_refusals.py`'s, and duplicated rather than
# imported: `tests/integration/composition/` is not a package, and a conftest fixture
# shared by two files would put half of each file's staging somewhere neither names.


class _Served(http.server.BaseHTTPRequestHandler):
    body = b'{"openapi": "3.1.0"}'

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's spelling
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_: object) -> None:
        """Silence. The test's output is the assertion, not an access log."""


@pytest.fixture()
def serving() -> Iterator[int]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Served)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


# --- staging --------------------------------------------------------------------------


def _env_text(port: int, *, secrets: dict[str, str] = EDITED_SECRETS, policy: str | None = None) -> str:
    lines = [
        f"ALPHA_INSTANCE={INSTANCE}",
        f"ALPHA_HTTP_PORT={port}",
        f"POSTGRES_DB={DATABASE}",
        f"S3_BUCKET={BUCKET}",
    ]
    if policy is not None:
        lines.append(f"ALPHA_PRESERVE_IMAGE_IDENTITY={policy}")
    lines += [f"{name}={value}" for name, value in sorted(secrets.items())]
    return "\n".join(lines) + "\n"


def _context_paths() -> list[str]:
    """Every host path the two Dockerfiles `COPY`, read the way the guard reads them."""
    paths: list[str] = []
    for dockerfile in (DOCKERFILE_API, DOCKERFILE_WEB):
        for line in dockerfile.read_text(encoding="utf-8").splitlines():
            fields = line.split()
            if len(fields) >= 3 and fields[0].lower() == "copy" and not fields[1].startswith("--"):
                paths.extend(fields[1:-1])
    return sorted(set(paths))


def _stage(tmp_path: Path, *, script: Path | None = None) -> Path:
    """A clone-shaped directory, the same one the refusals suite builds."""
    repo = tmp_path / "repo"
    deploy = repo / "infra/deploy"
    deploy.mkdir(parents=True, exist_ok=True)
    (deploy / "deploy.sh").write_text(
        (script or DEPLOY).read_text(encoding="utf-8"), encoding="utf-8"
    )
    for name, source in (("Dockerfile.api", DOCKERFILE_API), ("Dockerfile.web", DOCKERFILE_WEB)):
        (deploy / name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (deploy / "compose.server.yml").write_text("# stub\n", encoding="utf-8")
    (deploy / "env").mkdir(exist_ok=True)
    (deploy / "env/alpha.env.example").write_text(
        "\n".join(f"{n}={v}" for n, v in sorted(EXAMPLE_SECRETS.items())) + "\n",
        encoding="utf-8",
    )
    reload_proxy = deploy / "reload-proxy.sh"
    reload_proxy.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    reload_proxy.chmod(0o755)
    for path in _context_paths():
        target = repo / path
        if path.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# staged\n", encoding="utf-8")
    engine = repo / ENGINE
    engine.parent.mkdir(parents=True, exist_ok=True)
    engine.write_text("# staged\n", encoding="utf-8")
    return deploy / "deploy.sh"


def _mutant(tmp_path: Path, guard: str) -> Path:
    """A copy of deploy.sh with exactly one guard block deleted."""
    source = DEPLOY.read_text(encoding="utf-8")
    block = re.compile(
        rf"^# >>> guard: {re.escape(guard)}\n.*?^# <<< guard: {re.escape(guard)}\n",
        re.DOTALL | re.MULTILINE,
    )
    mutated, count = block.subn("", source)
    assert count == 1, f"the guard markers for {guard!r} are not a single block"
    cut = tmp_path / "mutant.sh"
    cut.write_text(mutated, encoding="utf-8")
    return cut


class _Run:
    """One `deploy.sh`, plus the image store it left behind and every docker call."""

    def __init__(self, completed: subprocess.CompletedProcess[str], store: Path, log: Path) -> None:
        self.completed = completed
        self._store = store
        self._log = log

    @property
    def calls(self) -> list[list[str]]:
        if not self._log.exists():
            return []
        return [line.split() for line in self._log.read_text(encoding="utf-8").splitlines()]

    @property
    def images(self) -> dict[str, str]:
        """The two names compose resolves, without the pin `deploy-previous` tag, which
        is scaffolding and is expected to move every run."""
        tags = json.loads(self._store.read_text(encoding="utf-8"))["tags"]
        return {name: value for name, value in tags.items() if ":" not in name}

    @property
    def store(self) -> dict[str, dict[str, str]]:
        return json.loads(self._store.read_text(encoding="utf-8"))


def _deploy(
    tmp_path: Path,
    *,
    port: int,
    store: Path,
    run: int,
    script: Path | None = None,
    env_file: Path | None = None,
    stub: dict[str, str] | None = None,
) -> _Run:
    """One invocation against a persistent image store, so a second run sees the first."""
    workspace = tmp_path / f"run{run}"
    workspace.mkdir()
    deploy = _stage(workspace, script=script)
    if env_file is None:
        env_file = workspace / "alpha.env"
        env_file.write_text(_env_text(port), encoding="utf-8")

    binary = workspace / "bin"
    binary.mkdir()
    docker = binary / "docker"
    docker.write_text(DOCKER_STUB, encoding="utf-8")
    docker.chmod(0o755)
    log = workspace / "docker-calls.log"

    environment = dict(os.environ)
    environment["PATH"] = f"{binary}{os.pathsep}{environment['PATH']}"
    environment["STUB_LOG"] = str(log)
    environment["STUB_STORE"] = str(store)
    environment["STUB_INSTANCE"] = INSTANCE
    environment["ALPHA_ENV_FILE"] = str(env_file)
    environment.update(stub or {})

    completed = subprocess.run(
        ["bash", str(deploy)], capture_output=True, text=True, env=environment, timeout=180
    )
    return _Run(completed, store, log)


@pytest.fixture()
def store(tmp_path: Path) -> Path:
    """An empty image store: a host that has never built these images."""
    path = tmp_path / "images.json"
    path.write_text(json.dumps({"tags": {}, "images": {}, "serial": 0}), encoding="utf-8")
    return path


# --- the property ---------------------------------------------------------------------


class TestASecondRunAgainstAnUnchangedTreeReplacesNothing:
    """`D-36`. The roadmap's "run it twice and the second changes nothing"."""

    def test_the_second_run_leaves_both_image_ids_where_the_first_left_them(
        self, tmp_path: Path, serving: int, store: Path
    ) -> None:
        first = _deploy(tmp_path, port=serving, store=store, run=1)
        assert first.completed.returncode == 0, (first.completed.stdout, first.completed.stderr)
        after_first = first.images

        second = _deploy(tmp_path, port=serving, store=store, run=2)
        assert second.completed.returncode == 0, (second.completed.stdout, second.completed.stderr)

        assert second.images == after_first, (
            "the second run moved an image id although the build produced identical "
            f"content: {after_first} -> {second.images}"
        )
        assert "identical content; kept" in second.completed.stdout, second.completed.stdout

    def test_the_build_still_mints_a_new_id_so_the_case_is_not_vacuous(
        self, tmp_path: Path, serving: int, store: Path
    ) -> None:
        """Without this, a stub whose build did nothing would pass the case above and
        prove nothing. The point of the mechanism is that the build DOES mint a new id --
        BuildKit's fresh `created` -- and the tag is moved back afterwards."""
        first = _deploy(tmp_path, port=serving, store=store, run=1)
        assert first.completed.returncode == 0
        before = first.images[f"{INSTANCE}-api"]

        second = _deploy(tmp_path, port=serving, store=store, run=2)
        assert second.completed.returncode == 0
        tags = [call for call in second.calls if call[:1] == ["tag"]]
        assert tags, "nothing was retagged, so the build cannot have produced a new id"
        assert [before] == [call[1] for call in tags if call[2] == f"{INSTANCE}-api"], tags

    def test_the_duplicate_the_build_made_is_not_left_behind(
        self, tmp_path: Path, serving: int, store: Path
    ) -> None:
        """One dangling image per run would accumulate. It costs no space -- every layer
        is shared with the image that kept the tag -- and it is still removed."""
        _deploy(tmp_path, port=serving, store=store, run=1)
        second = _deploy(tmp_path, port=serving, store=store, run=2)
        assert second.completed.returncode == 0
        assert len(second.store["images"]) == 2, second.store["images"]


class TestAnImageWhoseContentChangedNeverKeepsAnOldIdentity:
    """The failure mode this mechanism would have, and the reason it does not have it.

    An image that kept its identity after its content moved would leave the old container
    running and make `verify-deployed.sh` report the deployed stack as this tree. That
    probe compares the bytes INSIDE the running container against the working tree, and
    `docs/program/reviews/W24-IDEM.md` §4 drives it against exactly that stack.
    """

    @pytest.mark.parametrize("kind", ["api", "web"])
    def test_a_changed_image_replaces_the_old_one(
        self, kind: str, tmp_path: Path, serving: int, store: Path
    ) -> None:
        first = _deploy(tmp_path, port=serving, store=store, run=1)
        assert first.completed.returncode == 0
        before = dict(first.images)

        changed = {f"STUB_BUILT_{kind.upper()}": "a-byte-under-src-moved"}
        second = _deploy(tmp_path, port=serving, store=store, run=2, stub=changed)
        assert second.completed.returncode == 0, second.completed.stderr

        name = f"{INSTANCE}-{kind}"
        assert second.images[name] != before[name], (
            f"{name}'s content changed and the old identity was kept anyway"
        )
        assert "CONTENT CHANGED" in second.completed.stdout, second.completed.stdout
        other = f"{INSTANCE}-{'web' if kind == 'api' else 'api'}"
        assert second.images[other] == before[other], (
            f"{other} did not change and was replaced anyway"
        )

    def test_a_previous_image_that_can_no_longer_be_read_is_not_claimed_identical(
        self, tmp_path: Path, serving: int, store: Path
    ) -> None:
        """Two unreadable fingerprints are both the empty string, and a comparison that
        only asked whether they were equal would call them identical. `unreadable` is not
        `identical`, and it is the silent-fallback shape `AGENTS.md` §4 refuses.

        It is reached the way it is actually reached: the pin could not be taken, so the
        build deleted the image it displaced and there is nothing left to compare.
        """
        first = _deploy(tmp_path, port=serving, store=store, run=1)
        assert first.completed.returncode == 0

        second = _deploy(
            tmp_path, port=serving, store=store, run=2, stub={"STUB_PIN_FAILS": "1"}
        )
        assert second.completed.returncode == 0, second.completed.stderr
        assert "could no longer be read" in second.completed.stdout, second.completed.stdout
        assert "could not be pinned before the build" in second.completed.stderr
        assert not [
            call for call in second.calls
            if call[:1] == ["tag"] and not call[2].endswith(":deploy-previous")
        ], "an image nobody could read was presented as identical to the new one"

    def test_the_pin_is_taken_before_the_build_or_there_is_nothing_to_compare(
        self, tmp_path: Path, serving: int, store: Path
    ) -> None:
        """The order is the mechanism. This host's docker deletes the image a tag moved
        off -- the stub models it -- so a pin taken after the build would pin nothing."""
        _deploy(tmp_path, port=serving, store=store, run=1)
        second = _deploy(tmp_path, port=serving, store=store, run=2)
        calls = second.calls
        pins = [i for i, call in enumerate(calls)
                if call[:1] == ["tag"] and call[2].endswith(":deploy-previous")]
        builds = [i for i, call in enumerate(calls)
                  if call[:1] == ["compose"] and call[5:6] == ["build"]]
        assert len(pins) == 2, calls
        assert builds, calls
        assert max(pins) < min(builds), calls


class TestTheFirstRunOnAHostThatHasNeverBuiltThese:
    """`R-1`'s host, and the only one this programme has: nothing to preserve, and that
    must not read as an error or as a preserved identity."""

    def test_nothing_is_retagged_and_the_run_succeeds(
        self, tmp_path: Path, serving: int, store: Path
    ) -> None:
        first = _deploy(tmp_path, port=serving, store=store, run=1)
        assert first.completed.returncode == 0, (first.completed.stdout, first.completed.stderr)
        assert "there was no previous image to keep" in first.completed.stdout
        assert not [call for call in first.calls if call[:1] == ["tag"]], first.calls


class TestTheTagThatCouldNotBeMoved:
    """A `docker tag` that fails costs the three stateless containers a restart, which is
    what happened before this mechanism existed. It is SAID rather than swallowed --
    `AGENTS.md` §4 forbids a silent fallback -- and it does not fail the deployment,
    because the deployment is fine."""

    def test_it_says_so_and_deploys_anyway(
        self, tmp_path: Path, serving: int, store: Path
    ) -> None:
        _deploy(tmp_path, port=serving, store=store, run=1)
        second = _deploy(
            tmp_path, port=serving, store=store, run=2, stub={"STUB_TAG_FAILS": "1"}
        )
        assert second.completed.returncode == 0, second.completed.stderr
        assert "could NOT be moved back" in second.completed.stdout, second.completed.stdout


class TestTheOperatorCanTurnItOff:
    """The rollback lever. `no` is the behaviour `W23-DEPLOY` measured and `D-36` recorded:
    every build's image is new, and `api`, `web` and `migrate` are recreated."""

    def test_no_preserves_nothing_and_says_which_services_that_costs(
        self, tmp_path: Path, serving: int, store: Path
    ) -> None:
        workspace = tmp_path / "env"
        workspace.mkdir()
        off = workspace / "alpha.env"
        off.write_text(_env_text(serving, policy="no"), encoding="utf-8")

        first = _deploy(tmp_path, port=serving, store=store, run=1, env_file=off)
        assert first.completed.returncode == 0
        before = dict(first.images)
        second = _deploy(tmp_path, port=serving, store=store, run=2, env_file=off)
        assert second.completed.returncode == 0
        assert second.images != before, "the switch is off and identity was preserved anyway"
        assert not [call for call in second.calls if call[:1] == ["tag"]], second.calls
        assert "api, web and migrate will be recreated" in second.completed.stdout

    def test_yes_is_the_default_and_needs_no_line_in_the_environment(
        self, tmp_path: Path, serving: int, store: Path
    ) -> None:
        first = _deploy(tmp_path, port=serving, store=store, run=1)
        second = _deploy(tmp_path, port=serving, store=store, run=2)
        assert second.completed.returncode == 0
        assert second.images == first.images, second.completed.stdout


class TestAValueNobodyRecognisesIsRefusedRatherThanReadAsTheDefault:
    """`known-options` one layer along. An operator who wrote `false` meaning "off" and
    was quietly given `yes` would draw a conclusion about their stack from a switch that
    did nothing."""

    @pytest.mark.parametrize("value", ["false", "0", "off", "Yes", "true"])
    def test_it_refuses_before_anything_is_built(
        self, value: str, tmp_path: Path, serving: int, store: Path
    ) -> None:
        workspace = tmp_path / f"env-{value}"
        workspace.mkdir()
        env_file = workspace / "alpha.env"
        env_file.write_text(_env_text(serving, policy=value), encoding="utf-8")
        run = _deploy(tmp_path, port=serving, store=store, run=1, env_file=env_file)
        assert run.completed.returncode == REFUSED, (run.completed.stdout, run.completed.stderr)
        assert "which is neither yes nor no" in run.completed.stderr, run.completed.stderr
        assert run.calls == [], f"it refused, but only after running docker: {run.calls}"

    def test_that_guard_is_shown_able_to_fail(
        self, tmp_path: Path, serving: int, store: Path
    ) -> None:
        """Deletion, not a message: a guard that was never shown able to fail had never
        fired at all -- `D-17`, and this programme has paid for it once."""
        workspace = tmp_path / "env-mutant"
        workspace.mkdir()
        env_file = workspace / "alpha.env"
        env_file.write_text(_env_text(serving, policy="false"), encoding="utf-8")
        cut = _mutant(tmp_path, "identity-policy-known")
        run = _deploy(tmp_path, port=serving, store=store, run=1, script=cut, env_file=env_file)
        assert "which is neither yes nor no" not in run.completed.stderr, (
            "the guard was deleted and the refusal happened anyway, so this case was "
            "never testing that guard"
        )


# --- what the fingerprint is made of --------------------------------------------------


def test_the_fingerprint_is_built_from_the_layer_digests_and_not_from_a_timestamp() -> None:
    """The safety argument in one assertion, read out of the script's own bytes.

    `.RootFS.Layers` is the list of diffIDs -- the sha256 of each layer's uncompressed
    tar -- so content that genuinely changed cannot present itself as identical without
    colliding a sha256. `.Created` is the field BuildKit rewrites on every build and is
    the one thing this comparison must NOT contain; a fingerprint that carried it would
    never match and the mechanism would silently do nothing, which is the defect `D-17`
    describes and the reason this is pinned rather than assumed.
    """
    script = DEPLOY.read_text(encoding="utf-8")
    fingerprint = re.search(
        r"^fingerprint_of\(\) \{\n(.*?)^\}\n", script, re.DOTALL | re.MULTILINE
    )
    assert fingerprint, "deploy.sh no longer defines fingerprint_of()"
    body = fingerprint.group(1)
    assert ".RootFS.Layers" in body, body
    assert ".Created" not in body, (
        "the content fingerprint carries the build timestamp, so no two builds can ever "
        "match and the mechanism does nothing at all"
    )
    # The runtime configuration a changed Dockerfile moves without moving a layer.
    for field in (
        ".Config.Env",
        ".Config.Cmd",
        ".Config.Entrypoint",
        ".Config.WorkingDir",
        ".Config.User",
        ".Config.ExposedPorts",
        ".Config.Labels",
        ".Config.Volumes",
    ):
        assert field in body, f"{field} is not compared, so a change to it would be kept"


def test_the_identity_step_runs_after_the_build_and_before_the_stack_is_brought_up() -> None:
    """ORDER, and it is the same argument `images-built` makes. A tag moved after `up`
    would reach nothing: compose has already decided what to recreate."""
    script = DEPLOY.read_text(encoding="utf-8")

    def at(pattern: str) -> int:
        found = re.search(pattern, script, re.MULTILINE)
        assert found, f"deploy.sh no longer contains {pattern!r}"
        return found.start()

    # The COMMANDS, anchored at the start of a line: `compose build` and `compose up -d`
    # both appear in this script's own header comment, and a search that found those
    # would report an order nothing executes.
    build = at(r"^compose build \|\| BUILD_STATUS=")
    identity = at(r"^    keep_identity_if_unchanged \"\$INSTANCE-api\"")
    up = at(r"^compose up -d \|\| UP_STATUS=")
    assert build < identity < up, (build, identity, up)


class TestTheDefaultAttestationsAreOffForTheBuild:
    """The FIRST half of the fix, and the cause `D-36` misnamed.

    Two consecutive fully cached builds of an untouched tree produce images whose
    `.Created`, `.RootFS.Layers` and entire `.Config` are byte-identical -- and whose ids
    differ, because BuildKit attaches a provenance attestation carrying the time the build
    ran and the id is the digest of the manifest that holds it. `SOURCE_DATE_EPOCH` never
    touched that, which is why trying it changed nothing. The figures are in
    `docs/program/reviews/W24-IDEM.md` §3; what is pinned here is that the build is
    actually given the setting, read out of the build's own environment rather than out of
    a line in the script that might sit after it or inside an `if`.
    """

    def test_the_build_is_run_with_it(self, tmp_path: Path, serving: int, store: Path) -> None:
        run = _deploy(tmp_path, port=serving, store=store, run=1)
        assert run.completed.returncode == 0, run.completed.stderr
        given = [call for call in run.calls if call[:1] == ["environment"]]
        assert given, "no build was run"
        for call in given:
            assert call[1] == "BUILDX_NO_DEFAULT_ATTESTATIONS=1", call

    def test_it_is_still_on_when_the_operator_turned_the_retag_off(
        self, tmp_path: Path, serving: int, store: Path
    ) -> None:
        """The two halves are independent. `ALPHA_PRESERVE_IMAGE_IDENTITY=no` turns off
        the comparison and the retag; it is not a switch for how the image is built."""
        workspace = tmp_path / "env-off"
        workspace.mkdir()
        off = workspace / "alpha.env"
        off.write_text(_env_text(serving, policy="no"), encoding="utf-8")
        run = _deploy(tmp_path, port=serving, store=store, run=1, env_file=off)
        assert run.completed.returncode == 0, run.completed.stderr
        assert ["environment", "BUILDX_NO_DEFAULT_ATTESTATIONS=1"] in run.calls, run.calls


class TestThePinComesOffAfterTheStackIsUp:
    """`# --- 2a.`, and the order is measured rather than preferred: while the old
    container is still running, this host's docker REFUSES to untag the image it runs
    (`conflict: ... container <id> is using its referenced image`). A pin removed before
    `up` would therefore fail on exactly the runs where the content did change."""

    def test_it_is_removed_and_only_after_up(
        self, tmp_path: Path, serving: int, store: Path
    ) -> None:
        _deploy(tmp_path, port=serving, store=store, run=1)
        second = _deploy(tmp_path, port=serving, store=store, run=2)
        assert second.completed.returncode == 0, second.completed.stderr
        calls = second.calls
        removals = [i for i, call in enumerate(calls)
                    if call[:2] == ["image", "rm"] and call[2].endswith(":deploy-previous")]
        ups = [i for i, call in enumerate(calls)
               if call[:1] == ["compose"] and call[5:6] == ["up"]]
        assert len(removals) == 2, calls
        assert ups, calls
        assert min(removals) > min(ups), calls
        assert not [name for name in second.store["tags"] if name.endswith(":deploy-previous")], (
            second.store["tags"]
        )

    def test_a_pin_that_will_not_come_off_is_said_and_does_not_fail_the_deployment(
        self, tmp_path: Path, serving: int, store: Path
    ) -> None:
        """It names the image this run replaced, the next run re-points it, and no
        deployment is failed over a tag."""
        _deploy(tmp_path, port=serving, store=store, run=1)
        second = _deploy(
            tmp_path, port=serving, store=store, run=2, stub={"STUB_RM_FAILS": "1"}
        )
        assert second.completed.returncode == 0, second.completed.stderr
        assert "the next run re-points it" in second.completed.stdout, second.completed.stdout
