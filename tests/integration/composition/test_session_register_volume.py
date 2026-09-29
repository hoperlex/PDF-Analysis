"""`R-51`: the session register lives on a named volume the web container alone mounts.

The owner ruled this on 2026-09-29 (``docs/program/OWNER_RULINGS_2026-09-17.md`` §3.17),
over two alternatives that were both wider: giving the web tier its own database connection
(a ``DATABASE_URL`` in the compose file plus a client dependency in
``web/package-lock.json``, a root lockfile), and adding a contract operation to store
sessions through (a reseal). What it repairs is ``D-65``/`R-47`: the register was a ``Map``
in the Node process's memory and ``infra/deploy/deploy.sh`` recreates that container on
every run, so **every deploy signed every reviewer out**.

**What this file checks is the deployment, not the code.** The register's own behaviour --
that it writes, reloads after a restart, and reports a file it cannot read -- is
``web/tests/guards/session-durability.guard.test.ts``, driven against a real file. What
cannot be checked from inside ``web/`` is the half that makes it durable in the deployed
stack: that a volume exists, that it is named, that it is mounted where the image expects
it, and that **nothing but the web service mounts it**. A file the API container could also
read would be the credential leaving the one process `W15-AUTH` put it in.

Every expected value here is a **literal**, including the path. `OPERATING_CONSTRAINTS.md`
§12: a value read out of the thing it is checking cannot tell you the thing changed.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "infra" / "deploy" / "compose.server.yml"
DOCKERFILE = ROOT / "infra" / "deploy" / "Dockerfile.web"

#: The volume's key in the compose file. Written here, not read from there.
VOLUME = "web-sessions"

#: Where it is mounted, and the file inside it. Both literals, and both must agree with the
#: directory `Dockerfile.web` creates -- a mount point the image does not own is a volume
#: the process cannot write to.
MOUNT_POINT = "/var/lib/auditmanager/sessions"
REGISTER_FILE = "/var/lib/auditmanager/sessions/register.json"

#: The name the web container reads the path from. The same literal as
#: ``web/src/shared/config/session-store.ts``'s ``SESSION_STORE_VARIABLE``, spelled again
#: for this file's own reason: it is the day one of them changes that this catches.
STORE_VARIABLE = "AUDITMANAGER_SESSION_STORE"

#: The user `Dockerfile.web` runs as, and therefore the user that must own the mount point.
IMAGE_USER = "node"


def _service_blocks(text: str) -> dict[str, str]:
    """Every ``services:`` entry, by name, as its own block of text.

    Indentation rather than a YAML parser, because this repository's runtime venv has no
    YAML library and adding one to check a file would be a pin bought for a test. The
    compose file is two-space indented throughout and
    :func:`test_the_block_split_finds_the_services_this_stack_has` asserts this split really
    found the services rather than an empty dictionary.
    """
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.rstrip() == "services:")
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines[start + 1 :]:
        if line.strip() == "" or line.lstrip().startswith("#"):
            if current is not None:
                blocks[current].append(line)
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            break
        if indent == 2 and line.rstrip().endswith(":"):
            current = line.strip().rstrip(":")
            blocks[current] = []
            continue
        if current is not None:
            blocks[current].append(line)
    return {name: "\n".join(body) for name, body in blocks.items()}


def _mounts(block: str) -> list[str]:
    """The volume sources a service block mounts, bind mounts included."""
    found: list[str] = []
    in_volumes = False
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped == "volumes:":
            in_volumes = True
            continue
        if in_volumes:
            if stripped.startswith("- "):
                found.append(stripped[2:].split(":")[0])
                continue
            if stripped != "":
                in_volumes = False
    return found


def test_the_block_split_finds_the_services_this_stack_has() -> None:
    """The machinery, before anything is concluded from it.

    A split that returned nothing would make every assertion below vacuously true -- which
    is the shape `OPERATING_CONSTRAINTS.md` §12 names, and the reason this case exists.
    """
    blocks = _service_blocks(COMPOSE.read_text(encoding="utf-8"))
    assert set(blocks) == {"postgres", "s3", "s3-init", "migrate", "api", "web", "proxy"}
    # And the mount reader finds a mount this stack has had since wave 14, so "no mounts
    # anywhere" cannot pass for "only the web service mounts it".
    assert _mounts(blocks["postgres"]) == ["postgres-data"]


def test_the_register_volume_is_declared_and_named() -> None:
    """A named volume, so ``docker compose down`` does not take the sessions with it."""
    text = COMPOSE.read_text(encoding="utf-8")
    declared = re.search(
        rf"^volumes:\n(.*?)^services:", text, re.DOTALL | re.MULTILINE
    )
    assert declared is not None, "the compose file declares no top-level volumes block"
    assert f"\n  {VOLUME}:" in declared.group(1), (
        f"{VOLUME} is not declared as a top-level volume; a mount naming an undeclared "
        "volume is an anonymous one, and an anonymous volume is a new empty directory on "
        "every recreation -- which is the defect R-51 repairs, wearing a volume's clothes"
    )
    assert f"${{ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}}-{VOLUME}" in declared.group(1), (
        "the volume has no instance-scoped name, so two stands on one host would share "
        "one register"
    )


def test_exactly_one_service_mounts_it_and_that_service_is_web() -> None:
    """`R-51`'s own words: *a volume only the web container mounts*.

    The set comparison is the point. "web mounts it" would pass on a stack where the API
    container mounted it too -- and that is the case that matters, because the file holds
    the reviewers' credentials and `W15-AUTH`'s property is that they are in one process.
    """
    blocks = _service_blocks(COMPOSE.read_text(encoding="utf-8"))
    mounting = sorted(name for name, block in blocks.items() if VOLUME in _mounts(block))
    assert mounting == ["web"], (
        f"{VOLUME} is mounted by {mounting}. It holds the credential the web tier forwards "
        "on the reviewer's behalf; a second service that can read it is a second process "
        "holding a credential that is supposed to be in one."
    )
    assert f"- {VOLUME}:{MOUNT_POINT}" in blocks["web"], (
        f"the web service mounts {VOLUME} somewhere other than {MOUNT_POINT}, which is "
        "where the image creates the directory and where the register is configured to "
        "write"
    )


def test_the_web_service_is_told_where_the_register_goes() -> None:
    """And it is told a path inside the mount, not beside it.

    A register configured one directory up from the volume would write happily, report
    nothing, and lose every session on the next deploy -- the original defect, with a
    volume mounted beside it doing nothing.
    """
    blocks = _service_blocks(COMPOSE.read_text(encoding="utf-8"))
    assert f"{STORE_VARIABLE}: {REGISTER_FILE}" in blocks["web"], (
        f"the web service does not set {STORE_VARIABLE} to {REGISTER_FILE}"
    )
    assert REGISTER_FILE.startswith(f"{MOUNT_POINT}/"), (
        "the configured register file is not inside the mounted volume"
    )
    for name, block in blocks.items():
        if name == "web":
            continue
        assert STORE_VARIABLE not in block, (
            f"{name} is told where the session register is; only the container that mounts "
            "the volume has any business knowing"
        )


def test_the_image_owns_the_mount_point_so_the_process_can_write_to_it() -> None:
    """The half that is invisible until the first sign-in on a real stand.

    Docker seeds a fresh named volume from the image's own directory, ownership included.
    A mount point that did not exist in the image, or existed owned by root, produces a
    volume the unprivileged process cannot write to -- and the register then reports a
    write failure on every sign-in while appearing to work, because the session is live in
    memory either way. So the image creates it and gives it to the user it runs as.
    """
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert f"mkdir -p {MOUNT_POINT}" in text, (
        f"{MOUNT_POINT} is not created in the image, so the volume is seeded from nothing "
        "and belongs to root"
    )
    assert f"chown {IMAGE_USER}:{IMAGE_USER} {MOUNT_POINT}" in text
    # And the ownership is given before the image drops to that user: a `chown` after
    # `USER node` is a `chown` that cannot run.
    assert text.index(f"chown {IMAGE_USER}:{IMAGE_USER} {MOUNT_POINT}") < text.index(
        f"USER {IMAGE_USER}"
    ), "the mount point is chowned after the image drops privileges, which cannot work"
